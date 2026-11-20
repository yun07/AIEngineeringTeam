"""State store: authoritative index.json plus an append-only event log.

index.json is the authority for projects and runs. events.jsonl is an audit and
reporting trail only: Phase 1 never replays it and never reconstructs state
from it.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from aiteam.models import ApprovalRecord, Event, Run, UsageRecord, utc_now_iso


class StateStore:
    def __init__(
        self,
        root: str | Path,
        *,
        redactor: Callable[[str], str] | None = None,
    ) -> None:
        self.root = Path(root)
        self.state_dir = self.root / "state"
        self.runs_dir = self.root / "runs"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.redactor: Callable[[str], str] = redactor or (lambda text: text)

    @property
    def index_path(self) -> Path:
        return self.state_dir / "index.json"

    @property
    def events_path(self) -> Path:
        return self.state_dir / "events.jsonl"

    @property
    def approvals_path(self) -> Path:
        return self.state_dir / "approvals.jsonl"

    @property
    def usage_path(self) -> Path:
        return self.state_dir / "usage.jsonl"

    def new_run_id(self, now: datetime | None = None) -> str:
        stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
        return f"{stamp}-{uuid.uuid4().hex[:6]}"

    def save(self, run: Run) -> None:
        """Persist the whole run snapshot atomically."""
        index = self._read_index()
        index["projects"][run.project_slug] = {
            "slug": run.project_slug,
            "root": run.project_root,
        }
        index["runs"][run.id] = run.to_dict()
        payload = self.redactor(json.dumps(index, indent=2, ensure_ascii=False))
        self._atomic_write(self.index_path, payload)

    def load_run(self, run_id: str) -> Run | None:
        raw = self._read_index()["runs"].get(run_id)
        if raw is None:
            return None
        return Run.from_dict(raw)

    def append_event(
        self, run_id: str, kind: str, data: dict[str, Any] | None = None
    ) -> Event:
        event = Event(ts=utc_now_iso(), run_id=run_id, kind=kind, data=data or {})
        line = self.redactor(json.dumps(event.to_dict(), ensure_ascii=False))
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        return event

    def read_events(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if not self.events_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if run_id is None or payload.get("run_id") == run_id:
                    events.append(payload)
        return events

    def append_approval(self, record: ApprovalRecord) -> None:
        """Append one approval decision before any command is executed."""
        line = self.redactor(json.dumps(record.to_dict(), ensure_ascii=False))
        with self.approvals_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")

    def read_approvals(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if not self.approvals_path.is_file():
            return []
        approvals: list[dict[str, Any]] = []
        with self.approvals_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if run_id is None or payload.get("run_id") == run_id:
                    approvals.append(payload)
        return approvals

    def append_usage(self, record: UsageRecord) -> None:
        """Append one actual-usage record for a completed provider call."""
        line = self.redactor(json.dumps(record.to_dict(), ensure_ascii=False))
        with self.usage_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")

    def read_usage(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if not self.usage_path.is_file():
            return []
        records: list[dict[str, Any]] = []
        with self.usage_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if run_id is None or payload.get("run_id") == run_id:
                    records.append(payload)
        return records

    def run_dir(self, run_id: str) -> Path:
        path = self.runs_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def transcript_path(self, run_id: str, filename: str) -> Path:
        path = self.run_dir(run_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_plan(self, run_id: str, plan: dict[str, Any]) -> Path:
        path = self.run_dir(run_id) / "plan.json"
        text = self.redactor(json.dumps(plan, indent=2, ensure_ascii=False))
        self._atomic_write(path, text)
        return path

    def write_report(self, run_id: str, text: str) -> Path:
        path = self.run_dir(run_id) / "report.md"
        self._atomic_write(path, self.redactor(text))
        return path

    def write_context_artifacts(
        self,
        run_id: str,
        manifest: dict[str, Any],
        copies: list[tuple[str, str]],
    ) -> Path:
        """Write the context manifest and the exact text that was injected.

        Engine-owned manifest data is redacted. The copies are the exact text
        that entered the prompt and are deliberately not rewritten; a run that
        contains a known secret is refused before this method is called.
        """
        context_dir = self.run_dir(run_id) / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write(
            context_dir / "manifest.json",
            self.redactor(json.dumps(manifest, indent=2, ensure_ascii=False)),
        )
        for filename, text in copies:
            self._atomic_write(context_dir / filename, text)
        return context_dir

    def _read_index(self) -> dict[str, Any]:
        if not self.index_path.is_file():
            return {"version": 1, "projects": {}, "runs": {}}
        with self.index_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload.setdefault("version", 1)
        payload.setdefault("projects", {})
        payload.setdefault("runs", {})
        return payload

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        tmp_path = path.with_name(f".{path.name}.tmp")
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
