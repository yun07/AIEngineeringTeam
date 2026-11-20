"""Command line entry point: python -m aiteam run ..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from aiteam.config import (
    DEFAULT_CONFIG_PATH,
    FAKE_CONFIG_PATH,
    ConfigError,
    load_config,
)
from aiteam.engine.policy import ApprovalGate
from aiteam.engine.workflow import WorkflowEngine
from aiteam.models import RunState
from aiteam.providers.fake import FakeProvider, demo_by_role
from aiteam.state.store import StateStore


def build_approval_gate() -> ApprovalGate:
    """Interactive TTY approver. Non-interactive input always denies.

    Only the exact lowercase ``y`` approves. Every other answer, an empty
    answer, and an EOF all deny. Default is No.
    """

    def _approve(prompt: str) -> bool:
        print(prompt, end="", flush=True)
        answer = input().strip()
        return answer == "y"

    return ApprovalGate(approver=_approve, interactive=sys.stdin.isatty())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aiteam",
        description="Deterministic AI engineering team workflow engine.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="start one workflow run")
    run_parser.add_argument("--project", required=True, help="project slug")
    run_parser.add_argument("--request", required=True, help="user request")
    run_parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="run budget in USD; recorded now and enforced from M3",
    )
    run_parser.add_argument(
        "--plan-only",
        action="store_true",
        help="stop after the plan is accepted",
    )
    run_parser.add_argument(
        "--fake",
        action="store_true",
        help="use the scripted fake provider",
    )
    run_parser.add_argument(
        "--config",
        default=None,
        help="path to a TOML configuration file",
    )
    run_parser.add_argument(
        "--root",
        default=".",
        help="repository root that holds state/, runs/ and projects/",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.config:
        config_path = Path(args.config)
    elif args.fake:
        config_path = FAKE_CONFIG_PATH
    else:
        config_path = DEFAULT_CONFIG_PATH

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    if args.fake and config.provider.name != "fake":
        print(
            f"configuration error: --fake needs provider.name = \"fake\", "
            f"got {config.provider.name!r}",
            file=sys.stderr,
        )
        return 2
    if not args.fake:
        print(
            "live provider mode arrives at M5. Use --fake for the walking skeleton.",
            file=sys.stderr,
        )
        return 2

    provider = FakeProvider(by_role=demo_by_role(config.models))
    store = StateStore(root)
    project_root = root / "projects" / args.project
    engine = WorkflowEngine(
        config=config,
        provider=provider,
        store=store,
        project_root=project_root,
        project_slug=args.project,
        approval_gate=build_approval_gate(),
    )

    run = engine.start(args.request, budget_usd=args.budget)
    run = engine.execute(plan_only=args.plan_only)

    report_path = store.run_dir(run.id) / "report.md"
    print(f"run id: {run.id}")
    print(f"state: {run.state.value}")
    if run.block_reason:
        print(f"blocked: {run.block_reason}")
    print(f"tasks: {len(run.tasks)}")
    print(f"approvals recorded: {len(store.read_approvals(run.id))}")
    print(f"project: {project_root.as_posix()}")
    print(f"report: {report_path.as_posix()}")
    return 0 if run.state is RunState.COMPLETED else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
