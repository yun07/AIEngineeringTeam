# Project State — AI Engineering Team

- **Purpose:** short operational snapshot for Continuation Alignment. Read it after the README §1.1 Project Configuration section.
- **Status:** a derived snapshot. It is never an authority and never proof that code or tests work.
- **Baseline recorded:** `main` at `615f20039cc37cefee2e032b1ca920ad4a520199` when this snapshot was last reviewed. This is a historical reference, not the current `main` HEAD: verify the current remote `main` independently during alignment, and report `CURRENT HEAD UNVERIFIED` when that is not possible. The SHA is not refreshed for ordinary documentation commits.

## 1. Authority

Canonical milestone status, scope and evidence are recorded in `plans/phase1-architecture-plan.md`; this file never copies them. Principles and governance are in `AI_Engineering_Team.md`, architecture in `plans/adr-001-hybrid-architecture.md`, workflow and approval rules in `AGENTS.md`, the alignment process in `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md`, and project values in `README.md` §1.1. If this file disagrees with any of them, they win and this file is corrected.

## 2. Where the project stands

- Phase 1 is in progress and is not accepted. M4 is complete, reviewed and merged into `main` (implementation merge `9c11b6a`).
- **M5 is the next milestone**; M6 follows M5, then M7, then M8. M8 follows M7's completion and the Human acceptance that closes M7, because M7 carries Phase 1 acceptance.
- No M5–M8 work is authorised by this snapshot.
- Per-milestone status, including the M1–M3 "present but not formally closed" position, is recorded only in the Phase 1 plan.

## 3. Decisions that shape current work

- Hybrid architecture; Phase 1 uses no agent framework (ADR-001).
- The live provider is DeepSeek through the OpenAI-compatible adapter; provider, model and pricing are in `config/aiteam.toml`.
- Roles run as independent sessions with bounded handoffs, and every generated-code execution needs its own Human approval.
- Retry semantics: only an engine-confirmed QA failure backed by verified non-zero execution evidence retries; `max_attempts = 2` counts the initial attempt; exhausted attempts escalate; `BudgetError`, `LimitExceeded`, provider, engine and infrastructure failures never retry.
- Workflow coordination follows `AGENTS.md` §9. The WP2 Revision 1 target architecture is an accepted architecture baseline; its observability, governance and evolution steps (A1–A4) are not authorised.

## 4. Outstanding Human decisions

- When to authorise M5, the next milestone.

## 5. Evidence pointers

- M4: implementation merge `9c11b6ab0842280b51fdd0c4bcec5db1f078c1ca`, branch head `432a776098777c3be5faa16232c53a63c2431c0b`, review fixes `78d6e9c` and `432a776`; full suite 328 tests, 0 failed, 5 skipped at `78d6e9c`; independent review PASS; Human merge approval 2026-11-24.
- M0: `records/m0-environment-report.md` (PASS).
- M5 diagnostic only: `projects/diagnostic`, run `20261123T110208Z-97bc01`, 7 API calls, actual USD 0.004748 — not a Snake acceptance run.

## 6. Update rule

Update this file in the same work package that changes a milestone status, and keep it short. Never copy milestone tables, plan sections or governance rules here; point to the authoritative document instead.
