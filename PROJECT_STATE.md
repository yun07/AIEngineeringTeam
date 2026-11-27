# Project State — AI Engineering Team

- **Purpose:** short operational snapshot for Continuation Alignment. Read it after the README §1.1 Project Configuration section.
- **Status:** a derived snapshot. It is never an authority and never proof that code or tests work.
- **Baseline recorded:** `main` at `615f20039cc37cefee2e032b1ca920ad4a520199` when this snapshot was last reviewed. This is a historical reference, not the current `main` HEAD: verify the current remote `main` independently during alignment, and report `CURRENT HEAD UNVERIFIED` when that is not possible. The SHA is not refreshed for ordinary documentation commits.

## 1. Authority

Canonical milestone status, scope and evidence are recorded in `plans/phase1-architecture-plan.md`; this file never copies them. Principles and governance are in `AI_Engineering_Team.md`, architecture in `plans/adr-001-hybrid-architecture.md`, workflow and approval rules in `AGENTS.md`, the alignment process in `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md`, and project values in `README.md` §1.1. If this file disagrees with any of them, they win and this file is corrected.

## 2. Where the project stands

- Phase 1 is in progress and is not accepted. M4 is complete, reviewed and merged into `main` (implementation merge `9c11b6a`). M5 live validation and its closeout record are merged at `3e48fa7`. M6 is complete: the Snake specification `plans/snake-spec.md` was reviewed by the Human, three findings were corrected, and it is merged into `main`.
- M7 is complete: live run `20261127T232029Z-30ab3e` finished `completed` with 3/3 tasks done, 3/3 QA pass and 56 passing tests, at an actual cost of USD 0.294202; the Human accepted the QA test file spot check on 2026-11-27, and the M7 implementation and fixture are merged into `main` at `1b48396`.
- **M8 is complete**: the deferred backlog is written in `plans/phase1-backlog.md`, the charter and plan are refreshed, and documentation commit `bdbeb4f` is merged into `main` by fast-forward with the M8 closeout record; Human merge approval 2026-11-27.
- No further work is authorised by this snapshot.
- The WP2 Revision 1 target architecture is an accepted architecture baseline; its observability, governance and evolution steps (A1–A4) are not authorised.
- Per-milestone status, including the M1–M3 "present but not formally closed" position, is recorded only in the Phase 1 plan.

## 3. Where the rules live

Architecture and accepted decisions are recorded in `plans/adr-001-hybrid-architecture.md` and `AI_Engineering_Team.md` §7. Retry, budget, scope and evidence rules are in `plans/phase1-architecture-plan.md`. Workflow, authorisation and approval rules are in `AGENTS.md`. This snapshot does not restate any of them.

## 4. Outstanding Human decisions

- Whether and when to record Phase 1 acceptance, and when to authorise the three-role versus two-role comparison.
- Broader open project and design decisions are listed in [AI_Engineering_Team.md](AI_Engineering_Team.md) §7 ("Still open"). They are not prerequisites for M8, and remain unresolved rather than approved decisions.

## 5. Evidence pointers

- M4: implementation merge `9c11b6ab0842280b51fdd0c4bcec5db1f078c1ca`, branch head `432a776098777c3be5faa16232c53a63c2431c0b`, review fixes `78d6e9c` and `432a776`; full suite 328 tests, 0 failed, 5 skipped at `78d6e9c`; independent review PASS; Human merge approval 2026-11-24.
- M0: `records/m0-environment-report.md` (PASS).
- M5: live validation run `20261127T194853Z-f66a68` (project `m5-validation`), one approved QA execution with exit code 0, actual USD 0.047871. Two earlier attempts failed closed (`20261127T194106Z-6aae04`, `20261127T194603Z-0c1f5e`). The run ended `blocked` on T2 `max_turns_per_session`. The earlier diagnostic run `20261123T110208Z-97bc01` remains historical evidence only. Closeout record merged at `3e48fa7`.
- M6: specification `plans/snake-spec.md`; commits `3e36ce6` (specification) and `438a5b5` (review corrections). Human review on 2026-11-27 raised three findings — the initial-state formula, the absence of a public way to build test states, and missing CLI negative coverage — all corrected before merge. Merged into `main` by fast-forward in the M6 closeout work package.
- M7: live run `20261127T232029Z-30ab3e` (project `snake`, provider `deepseek`, model `deepseek-flash`, budget USD 0.50): 3/3 tasks done, 3/3 QA pass, final QA suite 56 tests with exit code 0, nine per-execution approvals all granted, actual USD 0.294202 with USD 0.205798 remaining. Human QA test file spot check accepted 2026-11-27. Implementation and fixture merged at `1b48396`. Two earlier attempts blocked before completion — `20261127T225541Z-73d0a6` on `max_output_tokens` and `20261127T230551Z-89ff83` on `max_context_tokens` — and remain evidence only.

- M8: deferred register `plans/phase1-backlog.md`; documentation commit `bdbeb4f`, merged into `main` by fast-forward with the M8 closeout commit in the same work package; Human merge approval 2026-11-27.

## 6. Update rule

Update this file in the same work package that changes a milestone status, and keep it short. Never copy milestone tables, plan sections or governance rules here; point to the authoritative document instead.
