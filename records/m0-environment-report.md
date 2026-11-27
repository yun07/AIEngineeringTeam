# M0 Environment and Repository Verification Report

**Milestone:** M0 Environment and repository verification
**Date:** 2026-11-20
**Scope:** Verify the `ai-team` conda environment and the Git repository, extend `.gitignore`, add `.env.example`.
**Status:** PASS, with two missing packages recorded as manual user actions and one pre-existing uncommitted change noted.

No packages were installed, no API was called, no system setting was modified and no M1 work was started.

---

## 1. Conda environment `ai-team`

The environment exists at `%USERPROFILE%\.conda\envs\ai-team` and is listed in `%USERPROFILE%\.conda\environments.txt`.

Checks were run with the environment's own interpreter, `%USERPROFILE%\.conda\envs\ai-team\python.exe`, because `conda` is not on the `PATH` of a non-interactive shell. This is a shell-path observation, not a broken installation.

| Item | Expected | Observed | Status |
|---|---|---|---|
| Conda environment `ai-team` | exists | `%USERPROFILE%\.conda\envs\ai-team` | present |
| Python version | 3.12.16 | 3.12.16 | present |
| pip | available | pip 26.2.2 (python 3.12) | present |
| `openai` | available | `ModuleNotFoundError: No module named 'openai'` | **missing** |
| `pytest` | available | `ModuleNotFoundError: No module named 'pytest'` | **missing** |
| `tkinter` | available or absent (Snake must pass without it) | Tk 8.6 | present |
| `tomllib` (stdlib, Python 3.12) | available | importable | present |
| `sqlite3` (stdlib) | available | SQLite 3.54.1 | present |

Installed distributions reported by `pip list` inside `ai-team`: `packaging 26.3`, `pip 26.2.2`, `setuptools 84.2.1`, `wheel 0.48.0`.

Reproduction commands:

```text
"%USERPROFILE%\.conda\envs\ai-team\python.exe" --version
"%USERPROFILE%\.conda\envs\ai-team\python.exe" -m pip --version
"%USERPROFILE%\.conda\envs\ai-team\python.exe" -c "import openai"
"%USERPROFILE%\.conda\envs\ai-team\python.exe" -c "import pytest"
"%USERPROFILE%\.conda\envs\ai-team\python.exe" -c "import tkinter; print(tkinter.TkVersion)"
```

In PowerShell, substitute `$env:USERPROFILE` for `%USERPROFILE%`.

### Manual user actions

Both packages below are manual user actions. The agent team performs no installation, in line with the Phase 1 policy that installation is denied at every tool call. They are needed at different milestones, so they are not installed together.

#### `pytest` — install before M1

`pytest` is required for the engine's own test suite from M1 onward. Install it manually before M1 begins:

```powershell
conda activate ai-team
python -m pip install pytest
python -m pytest --version
```

#### `openai` — deferred until before M5

`openai` is **not** needed now and must not be installed at this point. M1 through M4 run entirely on the fake provider. Install it in `ai-team` from a normal shell only before M5 live provider validation starts; until then it remains a pending action.

Phase 1 impact:

- `pytest` blocks M1 test work, so it is the only package to install at this stage.
- `openai` is needed only from M5 live provider validation onward, so its absence does not block M1 through M4.
- `tkinter` is present, but the Snake fixture must still pass headless. No UI dependency may be assumed by QA.

## 2. Git repository

| Item | Observed |
|---|---|
| Repository root | `C:/AIProjects/AIEngineeringTeam` |
| Current branch | `main` |
| Latest commit | `26a4f08 Modify plan and Add AGENTS.md` |
| Working tree at inspection time, before the M0 edits | one modified file, `AGENTS.md` (+24 lines), uncommitted |
| Stashes | none |

The `AGENTS.md` modification predates M0 and was not caused by this milestone. The tree is therefore **not clean**. Per the plan, the tree should be clean before M1 begins, so this change should be reviewed and committed by the user.

## 3. Files created or modified by M0

| File | Change |
|---|---|
| `.gitignore` | `state/` and `runs/` ignored; `projects/*` ignored by default while `projects/snake/` is re-included so the fixture source and QA tests stay in Git; all existing rules and the file's UTF-8 BOM preserved |
| `.env.example` | new, key names only with empty values, no secrets |
| `records/m0-environment-report.md` | this report |

`.env` itself remains ignored, and the `.env.*` pattern with the `!.env.example` exception already allowed the example file. Verified with `git check-ignore -v`: `.env` matches `.gitignore:2` and `.env.example` matches the negation rule at `.gitignore:4`.

Git prints a line-ending notice for `.gitignore` (LF in the working copy may be normalised to CRLF on checkout). `git diff --check` reports no whitespace errors, and the file's UTF-8 BOM is intact.

## 4. M0 exit criterion

The plan requires a short environment report that records every item as present or missing, reports missing packages as manual user actions, and attempts no installation. All three conditions are met, so M0 is complete on the verification and repository-configuration side.

Open items carried into M1:

1. Install `pytest` manually into `ai-team` before M1. `openai` stays uninstalled until M5.
2. Commit or otherwise resolve the outstanding `AGENTS.md` modification so M1 starts from a clean tree.

## 5. Next step

M1: build the FakeProvider walking skeleton, covering `models.py`, minimal `config.py`, `state/store.py`, `providers/base.py`, `providers/fake.py`, `agents/base.py`, the Orchestrator and Developer prompts, minimal `engine/handoff.py`, `engine/workflow.py` for the plan and Developer stages, `cli.py run`, report writing, and the deterministic execution limits.
