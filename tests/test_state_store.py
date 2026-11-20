"""State store: atomic snapshot writes and append-only events."""

from __future__ import annotations

from aiteam.models import AcceptanceCriterion, Run, RunState, Task
from aiteam.state.store import StateStore


def _run(store: StateStore) -> Run:
    return Run(
        id=store.new_run_id(),
        project_slug="demo",
        project_root="projects/demo",
        request="build a demo",
        provider="fake",
    )


def test_save_and_load_round_trip(tmp_path):
    store = StateStore(tmp_path)
    run = _run(store)
    run.tasks.append(
        Task(
            id="T1",
            description="create notes",
            acceptance_criteria=[AcceptanceCriterion(id="C1", text="notes exist")],
        )
    )

    store.save(run)
    loaded = store.load_run(run.id)

    assert loaded is not None
    assert loaded.id == run.id
    assert loaded.state is RunState.PLANNING
    assert loaded.project_slug == "demo"
    assert [task.id for task in loaded.tasks] == ["T1"]
    assert loaded.tasks[0].acceptance_criteria[0].id == "C1"


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    store = StateStore(tmp_path)
    run = _run(store)
    store.save(run)
    store.save(run)

    assert [path.name for path in store.state_dir.iterdir()] == ["index.json"]


def test_events_are_append_only_and_filterable(tmp_path):
    store = StateStore(tmp_path)
    first = _run(store)
    second = _run(store)

    store.append_event(first.id, "run_created", {"project": "demo"})
    store.append_event(second.id, "run_created", {"project": "demo"})
    store.append_event(first.id, "run_completed", {})

    all_events = store.read_events()
    first_events = store.read_events(first.id)

    assert [event["kind"] for event in all_events] == [
        "run_created",
        "run_created",
        "run_completed",
    ]
    assert [event["kind"] for event in first_events] == [
        "run_created",
        "run_completed",
    ]


def test_run_scoped_artifacts_live_under_runs(tmp_path):
    store = StateStore(tmp_path)
    run = _run(store)

    plan_path = store.write_plan(run.id, {"tasks": []})
    report_path = store.write_report(run.id, "# report\n")
    transcript = store.transcript_path(run.id, "orchestrator.session.jsonl")
    transcript.write_text("", encoding="utf-8")

    assert plan_path.parent == store.runs_dir / run.id
    assert report_path.read_text(encoding="utf-8") == "# report\n"
    assert transcript.exists()
