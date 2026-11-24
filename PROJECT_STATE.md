# Project State — AI Engineering Team

- **Purpose:** short operational snapshot for Continuation Alignment.
- **Scope:** Phase 1 progress for `yun07/AIEngineeringTeam`.
- **main HEAD when written:** `6844cfa9606c6bebc82806e41dbb69bc2b1e6640` (the workflow-optimization documentation merge; the M4 implementation merge is `9c11b6a`).
- **Status of this file:** a derived snapshot, never proof and never an authority. It records derived status only; the canonical documents listed in §1 always win. It never proves that code or tests work.

## 1. Which document is authoritative

| Information | Authoritative source |
|---|---|
| Vision, principles, governance, Human authority | `AI_Engineering_Team.md` (project charter) |
| Architecture decision (hybrid; no agent framework in Phase 1) | `plans/adr-001-hybrid-architecture.md` |
| Phase 1 scope and the **canonical milestone record** | `plans/phase1-architecture-plan.md` |
| Operation-layer decisions (OD-nnn) | `plans/operations-decisions.md` |
| Workflow, evidence, review and approval rules | `AGENTS.md` |
| Alignment process | `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md` |
| Project configuration values | `README.md` §1.1 |
| Compact operational snapshot for session continuation | This file — derived summary only, not an independent authority, and it does not override any document above |

## 2. Project purpose (brief)

A personal AI engineering team. One Python Workflow Engine owns state, permissions, budget, evidence validation and acceptance. Orchestrator, Developer and independent QA run as separate sessions and exchange bounded handoff bundles only.

## 3. Milestone status

Derived from `plans/phase1-architecture-plan.md`, which remains the canonical milestone record. If this table differs from the plan, the plan wins and this file is corrected.

| Milestone | Implementation | Formal closeout | Human acceptance |
|---|---|---|---|
| M0 Environment and repository | Completed | Recorded PASS (`plans/m0-environment-report.md`) | As recorded in that report |
| M1 FakeProvider walking skeleton | Present | `UNVERIFIED` — no closeout artefact | `UNVERIFIED` |
| M2 QA execution, evidence, approvals | Present | `UNVERIFIED` — no closeout artefact | `UNVERIFIED` |
| M3 Cost accounting and budget | Present | `UNVERIFIED` — no closeout artefact | `UNVERIFIED` |
| M4 Retry and escalation | Completed and merged into `main` at `9c11b6a` | Completion evidence recorded in the Phase 1 plan | Merge approved by the Human 2026-11-24 |
| M5 Live provider validation | Diagnostic only | Not recorded | Not recorded |
| M6 Snake specification | Not started | Not started | Not started |
| M7 Snake live end-to-end run | Not started | Not started | Not started |
| M8 Documentation and progress | Not started | Not started | Not started |

M1–M3 are present in code but are **not** formally closed. "Present" does not mean closed or accepted.

## 4. Current position and next valid milestones

- Phase 1 is in progress. Phase 1 is **not** accepted.
- M4 is complete, so **M5 and M6** are the next valid milestones and may run in parallel.
- No M5, M6, M7 or M8 work is authorised by this snapshot.

## 5. Dependencies

`M0 → M1 → M2 → M3 → M4`; then M5 and M6 may proceed in parallel; M7 requires both; M8 follows M7.

## 6. Decisions that matter for current work

- Hybrid architecture: this project owns the decisions; Phase 1 uses no agent framework (ADR-001).
- The live provider is DeepSeek through the OpenAI-compatible adapter; provider, model and pricing live in `config/aiteam.toml`.
- Roles run as independent sessions with bounded handoffs, and every generated-code execution needs its own human approval.
- M4 semantics: only an engine-confirmed QA failure backed by verified non-zero execution evidence retries; `max_attempts = 2` counts the initial attempt; exhausted attempts escalate; `BudgetError`, `LimitExceeded`, provider, engine and infrastructure failures never retry.
- Workflow coordination follows `AGENTS.md` §9 and `plans/operations-decisions.md` OD-002.

## 7. Outstanding Human decisions

- Whether M5 and M6 start together or sequentially, and which is authorised first.
- Whether M1–M3 need retroactive closeout artefacts before M5 acceptance is recorded.
- Any change to the milestone dependency order.

## 8. Latest verified evidence

| Evidence | Reference |
|---|---|
| M4 implementation merged into `main` | **implementation merge commit `9c11b6ab0842280b51fdd0c4bcec5db1f078c1ca`**; branch head `432a776098777c3be5faa16232c53a63c2431c0b`; review fixes `78d6e9c` and `432a776` |
| M4 status and evidence wording recorded | documentation commit `85d6c90ad3bc16adaa8e2842774240d7a80c3599` on `review/m4-status-reconciliation` — documentation only, not the implementation merge |
| M4 test evidence | full suite 328 tests, 0 failed, 0 errors, 5 skipped (skips are Windows symlink privilege only) at `78d6e9c`; focused 32 tests, 0 failed at `432a776`; scenario tests `tests/scenarios/test_retry_then_pass.py` and `tests/scenarios/test_retry_exhausted.py` |
| M4 review outcome | Independent review PASS; Human merge approval recorded 2026-11-24 |
| Workflow optimization principles recorded | documentation merge `6844cfa9606c6bebc82806e41dbb69bc2b1e6640` (source `73cf8eb0f6bc90022890b584d4acc6fda51294b5`) — documentation only, not the M4 implementation |
| M0 environment | `plans/m0-environment-report.md` (PASS) |
| M5 diagnostic run | `projects/diagnostic`, run `20261123T110208Z-97bc01`, 7 API calls, actual USD 0.004748 — not a Snake acceptance run |

## 9. Update rule

Update this file in the same work package that records a milestone status change, and keep it to roughly two pages. It never duplicates the Charter or the Phase 1 plan, it is never the authority for principles, architecture, scope, milestone status or workflow rules, and it never becomes proof that code or tests work.
