"""Deterministic workflow engine.

Control flow lives here and nowhere else. next_action() is a pure function of
run state, so every routing rule is testable offline with the fake provider.
M1 covers the plan stage, the Developer write stage, execution limits and the
run report. QA, approvals, retries and cost accounting arrive later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from aiteam.agents.base import AgentSession, LimitExceeded
from aiteam.agents.roles import FORBIDDEN_ROLE_TOOLS, get_role, model_for_role
from aiteam.config import Config
from aiteam.engine.handoff import (
    developer_bundle,
    file_manifest,
    orchestrator_prompt,
)
from aiteam.models import (
    TERMINAL_RUN_STATES,
    AcceptanceCriterion,
    Action,
    Run,
    RunState,
    Task,
    TaskState,
)
from aiteam.providers.base import LLMProvider, ToolSpec
from aiteam.state.store import StateStore
from aiteam.tools.filesystem import FileTools, Workspace

MAX_ROUTING_STEPS = 100


class PlanError(ValueError):
    """Raised when the Orchestrator reply is not a valid plan."""


class PlanLimitError(PlanError):
    """Raised when a valid-looking plan breaches max_tasks_per_plan."""


def next_action(run: Run, tasks: Sequence[Task] | None = None) -> Action:
    """Pure routing function: the only place that decides what happens next."""
    if run.state is RunState.PLANNING:
        return Action.ORCHESTRATE_PLAN

    task_list = list(run.tasks if tasks is None else tasks)
    if run.state is RunState.EXECUTING:
        if all(
            task.state in (TaskState.DONE, TaskState.QA_PASSED) for task in task_list
        ):
            return Action.FINALIZE
        return Action.RUN_DEVELOPER

    return Action.FINALIZE


def parse_plan(text: str, *, max_tasks: int) -> list[Task]:
    """Validate an Orchestrator reply and convert it into tasks."""
    payload = _load_json(text)
    if not isinstance(payload, dict):
        raise PlanError("plan must be a JSON object")

    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise PlanError("plan.tasks must be a non-empty list")
    if len(raw_tasks) > max_tasks:
        raise PlanLimitError(
            f"max_tasks_per_plan is {max_tasks} but the plan contains "
            f"{len(raw_tasks)} tasks"
        )

    tasks: list[Task] = []
    seen_task_ids: set[str] = set()
    for index, raw_task in enumerate(raw_tasks, start=1):
        if not isinstance(raw_task, dict):
            raise PlanError(f"task {index} must be an object")

        description = raw_task.get("description")
        if not isinstance(description, str) or not description.strip():
            raise PlanError(f"task {index} needs a non-empty description")

        task_id = str(raw_task.get("id") or f"T{index}").strip()
        if task_id in seen_task_ids:
            raise PlanError(f"duplicate task id: {task_id}")
        seen_task_ids.add(task_id)

        raw_criteria = raw_task.get("acceptance_criteria")
        if not isinstance(raw_criteria, list) or not raw_criteria:
            raise PlanError(f"task {task_id} needs at least one acceptance criterion")

        criteria: list[AcceptanceCriterion] = []
        seen_criteria: set[str] = set()
        for criterion_index, raw_criterion in enumerate(raw_criteria, start=1):
            if not isinstance(raw_criterion, dict):
                raise PlanError(
                    f"acceptance criterion {criterion_index} of {task_id} must be an object"
                )
            criterion_id = str(
                raw_criterion.get("id") or f"C{criterion_index}"
            ).strip()
            criterion_text = raw_criterion.get("text")
            if not isinstance(criterion_text, str) or not criterion_text.strip():
                raise PlanError(
                    f"acceptance criterion {criterion_id} of {task_id} needs non-empty text"
                )
            if criterion_id in seen_criteria:
                raise PlanError(
                    f"duplicate acceptance criterion id {criterion_id} in {task_id}"
                )
            seen_criteria.add(criterion_id)
            criteria.append(
                AcceptanceCriterion(id=criterion_id, text=criterion_text.strip())
            )

        raw_constraints = raw_task.get("constraints") or []
        if not isinstance(raw_constraints, list) or not all(
            isinstance(item, str) for item in raw_constraints
        ):
            raise PlanError(f"task {task_id} constraints must be a list of strings")

        tasks.append(
            Task(
                id=task_id,
                description=description.strip(),
                acceptance_criteria=criteria,
                constraints=[item.strip() for item in raw_constraints],
            )
        )
    return tasks


def _load_json(text: str) -> Any:
    if not isinstance(text, str) or not text.strip():
        raise PlanError("plan reply is empty")
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1] if "\n" in body else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[: -len("```")]
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PlanError(f"plan is not valid JSON: {exc}") from exc


class WorkflowEngine:
    def __init__(
        self,
        *,
        config: Config,
        provider: LLMProvider,
        store: StateStore,
        project_root: str | Path,
        project_slug: str,
    ) -> None:
        self._config = config
        self._provider = provider
        self._store = store
        self._project_slug = project_slug
        self._workspace = Workspace(project_root, write_deny_subpaths=("qa_tests",))
        self._file_tools = FileTools(self._workspace)
        self.run: Run | None = None
        self.sessions: list[AgentSession] = []
        self._steps = 0

    @property
    def workspace_root(self) -> Path:
        return self._workspace.root

    def start(self, request: str, *, budget_usd: float | None = None) -> Run:
        run = Run(
            id=self._store.new_run_id(),
            project_slug=self._project_slug,
            project_root=str(self._workspace.root),
            request=request,
            provider=self._config.provider.name,
            budget_usd=budget_usd,
        )
        self._store.save(run)
        self._store.append_event(
            run.id,
            "run_created",
            {
                "project": self._project_slug,
                "provider": self._config.provider.name,
                "budget_usd": budget_usd,
            },
        )
        self.run = run
        return run

    def execute(self, *, plan_only: bool = False) -> Run:
        run = self._require_run()
        while run.state not in TERMINAL_RUN_STATES:
            self._steps += 1
            if self._steps > MAX_ROUTING_STEPS:
                raise RuntimeError("routing did not reach a terminal state")

            action = next_action(run)
            if action is Action.ORCHESTRATE_PLAN:
                self._handle_plan()
                if plan_only and run.state not in TERMINAL_RUN_STATES:
                    self._block("plan_only: execution skipped at the user's request")
            elif action is Action.RUN_DEVELOPER:
                self._handle_developer()
            elif action is Action.FINALIZE:
                self._finalize()
            else:
                raise RuntimeError(f"action not available in M1: {action.value}")
        return run

    def _handle_plan(self) -> None:
        run = self._require_run()
        self._store.append_event(run.id, "plan_started", {})
        role = get_role("orchestrator")
        session = self._new_session(
            role_name=role.name,
            tools=(),
            handlers={},
            transcript_name="orchestrator.session.jsonl",
        )
        prompt = orchestrator_prompt(
            request=run.request,
            project_slug=self._project_slug,
            budget_usd=run.budget_usd,
            max_tasks=self._config.limits.max_tasks_per_plan,
        )

        try:
            tasks = parse_plan(
                session.send(prompt),
                max_tasks=self._config.limits.max_tasks_per_plan,
            )
        except LimitExceeded as exc:
            self._block(f"{exc.limit} breached while planning")
            return
        except PlanLimitError as exc:
            self._block(str(exc))
            return
        except PlanError as exc:
            self._store.append_event(run.id, "plan_invalid", {"error": str(exc)})
            repair_prompt = (
                f"Your previous reply was rejected: {exc}. "
                "Return only the JSON plan object described in your instructions."
            )
            try:
                tasks = parse_plan(
                    session.send(repair_prompt),
                    max_tasks=self._config.limits.max_tasks_per_plan,
                )
            except LimitExceeded as repair_limit:
                self._block(f"{repair_limit.limit} breached while repairing the plan")
                return
            except PlanLimitError as repair_error:
                self._block(str(repair_error))
                return
            except PlanError as repair_plan_error:
                self._block(f"plan_invalid: {repair_plan_error}")
                return
            except Exception as repair_provider_error:
                self._provider_error(
                    stage="planning (repair)", session=session, exc=repair_provider_error
                )
                return
        except Exception as exc:  # provider or transport failure while planning
            self._provider_error(stage="planning", session=session, exc=exc)
            return

        run.tasks = tasks
        run.state = RunState.EXECUTING
        self._store.save(run)
        self._store.write_plan(
            run.id, {"tasks": [task.to_dict() for task in tasks]}
        )
        self._store.append_event(
            run.id,
            "plan_accepted",
            {
                "tasks": [
                    {
                        "id": task.id,
                        "criteria": [
                            criterion.id for criterion in task.acceptance_criteria
                        ],
                    }
                    for task in tasks
                ],
                "session_id": session.session_id,
                "llm_calls": session.llm_calls,
                "turns": session.turns,
            },
        )

    def _handle_developer(self) -> None:
        run = self._require_run()
        task = next(
            (item for item in run.tasks if item.state is TaskState.PENDING), None
        )
        if task is None:
            return

        task.state = TaskState.DEV_RUNNING
        self._store.save(run)
        self._store.append_event(
            run.id,
            "task_dev_started",
            {"task": task.id, "attempt": task.attempt},
        )

        remaining_calls = (
            self._config.limits.max_llm_calls_per_task - task.llm_calls
        )
        if remaining_calls < 1:
            self._block(
                f"max_llm_calls_per_task={self._config.limits.max_llm_calls_per_task} "
                f"reached before task {task.id}"
            )
            return

        role = get_role("developer")
        index = run.tasks.index(task) + 1
        session = self._new_session(
            role_name=role.name,
            tools=self._file_tools.tool_specs(),
            handlers=self._file_tools.handlers(),
            transcript_name=f"task-{index}.developer.a{task.attempt}.session.jsonl",
            max_llm_calls=remaining_calls,
        )

        try:
            summary = session.send(
                developer_bundle(
                    request=run.request,
                    task=task,
                    manifest=file_manifest(self._workspace.root),
                )
            )
        except LimitExceeded as exc:
            task.llm_calls += session.llm_calls
            task.turns += session.turns
            task.files_written = self._written_paths(session)
            task.state = TaskState.BLOCKED
            task.block_reason = (
                f"{exc.limit} breached while running the developer for task {task.id}"
            )
            self._block(task.block_reason)
            return
        except Exception as exc:  # provider or transport failure
            task.llm_calls += session.llm_calls
            task.turns += session.turns
            task.files_written = self._written_paths(session)
            task.state = TaskState.BLOCKED
            task.block_reason = f"provider_error: {self._safe_error(exc)}"
            self._provider_error(
                stage=f"developer task {task.id}", session=session, exc=exc
            )
            return

        task.llm_calls += session.llm_calls
        task.turns += session.turns
        task.files_written = self._written_paths(session)
        task.summary = summary.strip()
        task.state = TaskState.DONE
        self._store.save(run)
        self._store.append_event(
            run.id,
            "task_dev_done",
            {
                "task": task.id,
                "files_written": list(task.files_written),
                "session_id": session.session_id,
                "llm_calls": session.llm_calls,
                "turns": session.turns,
            },
        )

    def _finalize(self) -> None:
        run = self._require_run()
        run.state = RunState.COMPLETED
        run.block_reason = None
        self._store.save(run)
        self._store.append_event(run.id, "run_completed", {})
        report_path = self._write_report()
        self._store.append_event(
            run.id, "report_written", {"path": str(report_path)}
        )

    def _block(self, reason: str) -> None:
        run = self._require_run()
        run.state = RunState.BLOCKED
        run.block_reason = reason
        self._store.save(run)
        self._store.append_event(run.id, "run_blocked", {"reason": reason})
        self._write_report()

    def _new_session(
        self,
        *,
        role_name: str,
        tools: Sequence[ToolSpec],
        handlers: Mapping[str, Any],
        transcript_name: str,
        max_llm_calls: int | None = None,
    ) -> AgentSession:
        run = self._require_run()
        role = get_role(role_name)

        # The role definition, not the caller, decides which tools exist.
        forbidden = set(role.tools) & set(FORBIDDEN_ROLE_TOOLS)
        if forbidden:
            raise RuntimeError(
                f"role {role.name} declares forbidden tools: {sorted(forbidden)}"
            )
        spec_by_name = {spec.name: spec for spec in tools}
        handler_by_name = dict(handlers)
        missing = [
            name
            for name in role.tools
            if name not in spec_by_name or name not in handler_by_name
        ]
        if missing:
            raise RuntimeError(
                f"role {role.name} is missing registered tools: {sorted(missing)}"
            )

        session = AgentSession(
            role=role.name,
            model=model_for_role(self._config, role.name),
            provider=self._provider,
            system_prompt=role.load_prompt(),
            transcript_path=self._store.transcript_path(run.id, transcript_name),
            allowed_tools=frozenset(role.tools),
            max_tool_output_chars=self._config.limits.max_tool_output_chars,
            tool_specs=tuple(spec_by_name[name] for name in role.tools),
            tool_handlers={name: handler_by_name[name] for name in role.tools},
            max_turns=self._config.limits.max_turns_per_session,
            max_llm_calls=(
                max_llm_calls
                if max_llm_calls is not None
                else self._config.limits.max_llm_calls_per_task
            ),
        )
        self.sessions.append(session)
        return session

    @staticmethod
    def _written_paths(session: AgentSession) -> list[str]:
        return [
            str(invocation.arguments.get("path", ""))
            for invocation in session.tool_invocations
            if invocation.name == "write_file" and invocation.error is None
        ]

    def _provider_error(
        self, *, stage: str, session: AgentSession, exc: Exception
    ) -> None:
        """Close the run deterministically when the provider fails.

        Only Exception reaches this handler; BaseException such as
        KeyboardInterrupt and SystemExit keep propagating.
        """
        run = self._require_run()
        self._store.append_event(
            run.id,
            "provider_error",
            {
                "stage": stage,
                "error_type": type(exc).__name__,
                "message": self._safe_error(exc, include_type=False),
                "session_id": session.session_id,
                "llm_calls": session.llm_calls,
                "turns": session.turns,
            },
        )
        self._block(f"provider_error: {self._safe_error(exc)} (while {stage})")

    @staticmethod
    def _safe_error(exc: Exception, *, include_type: bool = True) -> str:
        message = " ".join(str(exc).split())
        if len(message) > 200:
            message = message[:200] + "..."
        if not include_type:
            return message or type(exc).__name__
        return f"{type(exc).__name__}: {message}" if message else type(exc).__name__

    def _write_report(self) -> Path:
        run = self._require_run()
        limits = self._config.limits
        lines: list[str] = [
            f"# Run report {run.id}",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Project | `{run.project_slug}` |",
            f"| Project root | `{run.project_root}` |",
            f"| Provider | `{run.provider}` |",
            f"| Run state | `{run.state.value}` |",
            f"| Created | {run.created_at} |",
            f"| Budget | {run.budget_usd if run.budget_usd is not None else 'not set'} |",
            "",
            "## Request",
            "",
            "```text",
            run.request.strip(),
            "```",
            "",
        ]

        if run.block_reason:
            lines.extend(
                [
                    "## Blocked",
                    "",
                    f"{run.block_reason}",
                    "",
                ]
            )

        lines.extend(["## Plan", "", "| Task | Description | Criteria | Constraints |", "|---|---|---|---|"])
        if run.tasks:
            for task in run.tasks:
                criteria = ", ".join(
                    f"{criterion.id}: {criterion.text}"
                    for criterion in task.acceptance_criteria
                )
                constraints = "; ".join(task.constraints) or "-"
                lines.append(
                    f"| {task.id} | {task.description} | {criteria} | {constraints} |"
                )
        else:
            lines.append("| - | no plan stored | - | - |")

        lines.extend(
            [
                "",
                "## Execution",
                "",
                "| Task | State | Attempt | LLM calls | Turns | Files written |",
                "|---|---|---|---|---|---|",
            ]
        )
        if run.tasks:
            for task in run.tasks:
                files = ", ".join(task.files_written) or "-"
                lines.append(
                    f"| {task.id} | {task.state.value} | {task.attempt} | "
                    f"{task.llm_calls} | {task.turns} | {files} |"
                )
        else:
            lines.append("| - | - | - | - | - | - |")

        lines.extend(
            [
                "",
                "## Sessions",
                "",
                "| Role | Session | Model | LLM calls | Turns | Transcript |",
                "|---|---|---|---|---|---|",
            ]
        )
        if self.sessions:
            for session in self.sessions:
                transcript = session.transcript_path.name
                lines.append(
                    f"| {session.role} | {session.session_id} | {session.model} | "
                    f"{session.llm_calls} | {session.turns} | `{transcript}` |"
                )
        else:
            lines.append("| - | - | - | - | - | - |")

        lines.extend(
            [
                "",
                "## Limits in effect",
                "",
                f"- max_tasks_per_plan = {limits.max_tasks_per_plan}",
                f"- max_turns_per_session = {limits.max_turns_per_session}",
                f"- max_llm_calls_per_task = {limits.max_llm_calls_per_task}",
                f"- max_attempts = {limits.max_attempts} (enforced from M4)",
                "",
                "## Not in this milestone",
                "",
                "QA execution, approvals, retries, token accounting and USD cost "
                "arrive in M2 to M4. This report contains no cost figures on purpose.",
                "",
            ]
        )
        return self._store.write_report(run.id, "\n".join(lines))

    def _require_run(self) -> Run:
        if self.run is None:
            raise RuntimeError("start() must be called before execute()")
        return self.run
