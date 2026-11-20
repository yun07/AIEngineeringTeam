"""Bounded, role-specific handoff bundles.

Bundles are built from state only. No transcript, no reasoning and no secret
ever enters a bundle.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Sequence

from aiteam.models import Task

MAX_MANIFEST_ENTRIES = 200


def file_manifest(root: str | Path) -> list[dict[str, Any]]:
    """Return relative path, sha256 and size for every file in the workspace."""
    root_path = Path(root)
    entries: list[dict[str, Any]] = []
    if not root_path.is_dir():
        return entries

    for path in sorted(root_path.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        if ".env" in path.name.lower():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(
            {
                "path": path.relative_to(root_path).as_posix(),
                "sha256": digest,
                "size_bytes": path.stat().st_size,
            }
        )
        if len(entries) >= MAX_MANIFEST_ENTRIES:
            entries.append(
                {
                    "path": "(manifest truncated)",
                    "sha256": "",
                    "size_bytes": 0,
                }
            )
            break
    return entries


def _format_manifest(manifest: Sequence[dict[str, Any]]) -> str:
    if not manifest:
        return "(the workspace is empty)"
    return "\n".join(
        f"- {entry['path']} ({entry['size_bytes']} bytes, sha256 {entry['sha256'][:12]})"
        for entry in manifest
    )


def _format_criteria(task: Task) -> str:
    return "\n".join(
        f"- {criterion.id}: {criterion.text}"
        for criterion in task.acceptance_criteria
    )


def orchestrator_prompt(
    *,
    request: str,
    project_slug: str,
    budget_usd: float | None,
    max_tasks: int,
) -> str:
    budget_line = (
        f"Run budget: {budget_usd:.2f} USD." if budget_usd is not None else "Run budget: not set."
    )
    return (
        f"Project: {project_slug}\n"
        f"User request:\n{request.strip()}\n\n"
        f"{budget_line}\n"
        f"Maximum tasks allowed: {max_tasks}\n\n"
        "Return only the JSON plan described in your instructions."
    )


def developer_bundle(
    *,
    request: str,
    task: Task,
    manifest: Sequence[dict[str, Any]],
) -> str:
    constraints = (
        "\n".join(f"- {item}" for item in task.constraints)
        if task.constraints
        else "(none)"
    )
    return (
        "Overall user request:\n"
        f"{request.strip()}\n\n"
        f"Your task ({task.id}):\n"
        f"{task.description}\n\n"
        "Acceptance criteria you must satisfy:\n"
        f"{_format_criteria(task)}\n\n"
        "Technology constraints:\n"
        f"{constraints}\n\n"
        "Current project files:\n"
        f"{_format_manifest(manifest)}\n\n"
        "Write the files needed for this task using the write_file tool, then "
        "reply with a short summary that lists the files you wrote."
    )


def qa_bundle(
    *,
    request: str,
    task: Task,
    manifest: Sequence[dict[str, Any]],
) -> str:
    """Handoff for QA: request, criteria ids, manifest and conventions only."""
    return (
        "Overall user request:\n"
        f"{request.strip()}\n\n"
        f"Task to verify ({task.id}):\n"
        f"{task.description}\n\n"
        "Acceptance criteria you must cover. Every id below needs at least one\n"
        "check, and at least one check must be marked negative:\n"
        f"{_format_criteria(task)}\n\n"
        "Current project files, with hashes for change detection:\n"
        f"{_format_manifest(manifest)}\n\n"
        "Testing conventions:\n"
        "- pytest only, no other test framework.\n"
        "- Write test files only under qa_tests/.\n"
        "- Do not modify or create any other file.\n"
        "- Request execution with the exact argument vector\n"
        '  ["python", "-m", "pytest", "qa_tests", "-q"].\n'
        "- Each execution needs its own human approval; a denial is reported,\n"
        "  not worked around.\n"
        "- Every run_command result prints `execution_id=...`. Echo that exact\n"
        "  value in each check; the engine verifies it against its own audit.\n"
        "- Reply with the verdict JSON described in your instructions.\n"
    )
