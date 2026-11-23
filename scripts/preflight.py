#!/usr/bin/env python3
"""Preflight validation for a review branch.

This is not a Git hook and this script does not install one. Run it from
anywhere inside the repository before committing:

    python scripts/preflight.py

Exit code 0 means PASS; exit code 1 means FAIL with reasons.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ACTIVE_DOCS = (
    "AGENTS.md",
    "README.md",
    "AI_Engineering_Team.md",
    "UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md",
    "plans/phase1-architecture-plan.md",
)
STALE_STATUS = re.compile(
    r"^\*\*Status:\*\*.*no implementation(?: has)? started",
    re.IGNORECASE | re.MULTILINE,
)
PASTE_INSTRUCTION = re.compile(
    r"the human will (?:paste|upload) the primary", re.IGNORECASE
)
PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9_]*>")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def git(*args: str) -> str:
    result = run(*args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    try:
        root = Path(git("rev-parse", "--show-toplevel"))
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
        head = git("rev-parse", "--short", "HEAD")
    except RuntimeError as exc:
        print("FAIL")
        print(f"- cannot read repository: {exc}")
        return 1

    try:
        git_dir = Path(git("rev-parse", "--git-dir"))
        if not git_dir.is_absolute():
            git_dir = (root / git_dir).resolve()
        for marker, label in (
            ("MERGE_HEAD", "merge"),
            ("rebase-merge", "rebase"),
            ("rebase-apply", "rebase"),
        ):
            if (git_dir / marker).exists():
                failures.append(f"{label} in progress")
    except RuntimeError as exc:
        failures.append(f"cannot inspect Git state: {exc}")

    base_result = run("rev-parse", "origin/main")
    base = base_result.stdout.strip() if base_result.returncode == 0 else None
    if base is None:
        failures.append("origin/main not found; fetch it before running preflight")

    diff_check = run("diff", "--check")
    if diff_check.returncode != 0:
        detail = (diff_check.stdout or diff_check.stderr).strip()
        failures.append("git diff --check failed" + (f": {detail}" if detail else ""))

    if branch == "main":
        failures.append("current branch is main; use a review branch")

    status_lines: list[str] = []
    try:
        status_lines = git("status", "--porcelain").splitlines()
    except RuntimeError as exc:
        failures.append(f"cannot read working tree status: {exc}")

    changed: list[str] = []
    if base:
        try:
            committed = set(git("diff", "--name-only", f"{base}...HEAD").splitlines())
            working = set(git("diff", "--name-only", base).splitlines())
            untracked = set(
                git("ls-files", "--others", "--exclude-standard").splitlines()
            )
            changed = sorted(item for item in committed | working | untracked if item)
        except RuntimeError as exc:
            failures.append(f"cannot compute change scope: {exc}")
        if not changed:
            notes.append("no changes relative to origin/main")

    for relative in ACTIVE_DOCS:
        path = root / relative
        if not path.is_file():
            failures.append(f"missing document: {relative}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if STALE_STATUS.search(text):
            failures.append(f"{relative}: stale Status header")
        if PASTE_INSTRUCTION.search(text):
            failures.append(f"{relative}: stale Human paste/upload instruction")

    protocol = root / "UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md"
    if protocol.is_file():
        text = protocol.read_text(encoding="utf-8", errors="replace")
        part1 = text.split("## Part 1", 1)[-1].split("## Part 2", 1)[0]
        for line in part1.splitlines():
            if line.startswith("|") and PLACEHOLDER.search(line):
                failures.append(
                    "protocol Part 1 still contains an unfilled placeholder: "
                    + line.strip()[:80]
                )
        if "Read `AGENTS.md` first" not in text:
            failures.append("protocol bootstrap does not start with AGENTS.md")
        if (
            "Read AGENTS.md first, then follow its Mandatory Session Bootstrap"
            not in text
        ):
            failures.append("protocol starter command does not start with AGENTS.md")

    agents = root / "AGENTS.md"
    if agents.is_file():
        if "Mandatory Session Bootstrap" not in agents.read_text(
            encoding="utf-8", errors="replace"
        ):
            failures.append("AGENTS.md is missing the Mandatory Session Bootstrap section")

    print("Preflight validation (not a Git hook)")
    print(f"repo: {root}")
    print(f"branch: {branch}  HEAD: {head}")
    print(f"base: origin/main {base or 'MISSING'}")
    print(f"working tree: {len(status_lines)} change(s)")
    print(
        f"changed files ({len(changed)}): "
        + (", ".join(changed) if changed else "none")
    )
    for note in notes:
        print(f"note: {note}")

    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("PASS")
    print(
        "Docs-only changes do not require pytest. Code changes must report "
        "the actual test command, exit code and pass/fail count."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
