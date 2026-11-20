"""Success scenario: Developer write, QA execution, engine validation, done."""

from __future__ import annotations

from aiteam.models import RunState, TaskState
from aiteam.tools.shell import RunResult
from tests.fakes import ScriptedRunner, event_kinds, qa_script, run_demo


def test_developer_qa_and_engine_validation_complete(tmp_path):
    runner = ScriptedRunner([RunResult(exit_code=0, stdout="2 passed in 0.02s")])

    engine, store, run, result = run_demo(
        tmp_path, qa_script_responses=qa_script(), runner=runner
    )

    assert result.state is RunState.COMPLETED
    assert result.tasks[0].state is TaskState.DONE

    project = tmp_path / "repo" / "projects" / "demo"
    assert (project / "notes.md").is_file()
    assert (project / "qa_tests" / "test_demo.py").is_file()

    kinds = event_kinds(store, run.id)
    for expected in (
        "task_dev_done",
        "task_qa_started",
        "task_qa_passed",
        "run_completed",
        "report_written",
    ):
        assert expected in kinds
    assert (
        kinds.index("task_dev_done")
        < kinds.index("task_qa_started")
        < kinds.index("task_qa_passed")
    )

    approvals = store.read_approvals(run.id)
    assert len(approvals) == 1
    assert approvals[0]["decision"] == "approved"
    assert approvals[0]["task_id"] == "T1"

    assert len(runner.calls) == 1
    assert runner.calls[0]["cwd"] == str(project.resolve())
    assert "OPENAI_API_KEY" not in runner.calls[0]["env"]
    assert runner.calls[0]["env"]["PYTHONUTF8"] == "1"

    report = (store.run_dir(run.id) / "report.md").read_text(encoding="utf-8")
    for expected in (
        "## QA evidence",
        "## QA test files",
        "## Approvals",
        "## Command executions",
        "qa_tests/test_demo.py",
        "python -m pytest qa_tests -q",
        "Engine result: accepted",
    ):
        assert expected in report

    developer = [s for s in engine.sessions if s.role == "developer"][0]
    qa = [s for s in engine.sessions if s.role == "qa"][0]
    assert {spec.name for spec in developer.tool_specs} == {
        "read_file",
        "write_file",
        "list_files",
    }
    assert "run_command" in {spec.name for spec in qa.tool_specs}
    assert developer.session_id != qa.session_id
    assert developer.transcript_path != qa.transcript_path

    stored = store.load_run(run.id)
    assert stored is not None
    assert stored.state is RunState.COMPLETED
    assert stored.tasks[0].qa_verdict is not None
