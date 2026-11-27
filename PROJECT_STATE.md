# Project State — AI Engineering Team

- **Purpose:** short operational snapshot for Continuation Alignment. Read it after the README §1.1 Project Configuration section.
- **Status:** a derived snapshot. It is never an authority and never proof that code or tests work.
- **Baseline recorded:** `main` at `615f20039cc37cefee2e032b1ca920ad4a520199` when this snapshot was last reviewed. This is a historical reference, not the current `main` HEAD: verify the current remote `main` independently during alignment, and report `CURRENT HEAD UNVERIFIED` when that is not possible. The SHA is not refreshed for ordinary documentation commits.

## 1. Authority

Canonical milestone status, scope and evidence are recorded in `plans/phase1-architecture-plan.md`; this file never copies them. Principles and governance are in `AI_Engineering_Team.md`, architecture in `plans/adr-001-hybrid-architecture.md`, workflow and approval rules in `AGENTS.md`, the alignment process in `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md`, and project values in `README.md` §1.1. If this file disagrees with any of them, they win and this file is corrected.

## 2. Where the project stands

- Phase 1 is in progress and is not accepted. M4 is complete, reviewed and merged into `main` (implementation merge `9c11b6a`). M5 live validation is complete; its closeout record awaits review and merge.
- **M6 is the next milestone**; M7 follows M6, then M8. M8 follows M7's completion and the Human acceptance that closes M7, because M7 carries Phase 1 acceptance.
- No M6–M8 work is authorised by this snapshot.
- The WP2 Revision 1 target architecture is an accepted architecture baseline; its observability, governance and evolution steps (A1–A4) are not authorised.
- Per-milestone status, including the M1–M3 "present but not formally closed" position, is recorded only in the Phase 1 plan.

## 3. Where the rules live

Architecture and accepted decisions are recorded in `plans/adr-001-hybrid-architecture.md` and `AI_Engineering_Team.md` §7. Retry, budget, scope and evidence rules are in `plans/phase1-architecture-plan.md`. Workflow, authorisation and approval rules are in `AGENTS.md`. This snapshot does not restate any of them.

## 4. Outstanding Human decisions

- When to authorise M6, the next milestone.
- Broader open project and design decisions are listed in [AI_Engineering_Team.md](AI_Engineering_Team.md) §7 ("Still open"). They are not prerequisites for M6, and remain unresolved rather than approved decisions.

## 5. Evidence pointers

- M4: implementation merge `9c11b6ab0842280b51fdd0c4bcec5db1f078c1ca`, branch head `432a776098777c3be5faa16232c53a63c2431c0b`, review fixes `78d6e9c` and `432a776`; full suite 328 tests, 0 failed, 5 skipped at `78d6e9c`; independent review PASS; Human merge approval 2026-11-24.
- M0: `records/m0-environment-report.md` (PASS).
- M5: live validation run `20261127T194853Z-f66a68` (project `m5-validation`), one approved QA execution with exit code 0, actual USD 0.047871. Two earlier attempts failed closed (`20261127T194106Z-6aae04`, `20261127T194603Z-0c1f5e`). The run ended `blocked` on T2 `max_turns_per_session`. The earlier diagnostic run `20261123T110208Z-97bc01` remains historical evidence only.

## 6. Update rule

Update this file in the same work package that changes a milestone status, and keep it short. Never copy milestone tables, plan sections or governance rules here; point to the authoritative document instead.
