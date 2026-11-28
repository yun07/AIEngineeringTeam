# Phase 1 Backlog — Deferred Work and Comparison Plan

- **Purpose:** register the work that Phase 1 deliberately deferred, derived from `plans/phase1-architecture-plan.md` section G.
- **Status:** a derived register. It is never an authority and never an authorisation. The plan owns milestone scope, dependencies, completion criteria and acceptance; the charter owns principles.
- **Derived from:** `plans/phase1-architecture-plan.md` section G as merged at `497772b`.
- **Rule:** nothing in this file is authorised work. Every item still needs its own explicit Human authorisation before it is designed or built.

## 1. Deferred capabilities (section G.1 "Deferred" column)

Each row pairs the Phase 1 essential with what was deferred, keeping the plan's wording as the source.

| # | Deferred item | Phase 1 position (the kept essential) | Revisit trigger |
|---|---|---|---|
| 1 | Parallel tasks and multi-run scheduling | Deterministic engine with explicit states, retry counting and escalation, run one task sequence at a time | Any need for unattended or parallel work, or execution of untrusted code (section G #1) |
| 2 | Researcher, Environment Manager, Gardening, Independent Consultant / Reviewer and other specialists; Developer shell execution only if a future review justifies it | Three roles with separate sessions, prompts, tool sets and transcripts | Repeated cases where the Developer cannot proceed without execution (section G #17); recurring bugs in QA-passed work (section G #5) |
| 3 | Full permission policy language, signed approvals, OS sandbox, containers, worktrees | QA-only command execution, exact-command allowlist, CONFIRM for QA runs, DENY for installs and secrets | Any proposal to run without approval (section G #2); Phase 4 worktrees and branches (section G #15) |
| 4 | Mutation testing, coverage tooling, multi-model QA | QA criterion mapping, a required negative check and the human spot check | Recurring bugs in QA-passed work; a QA miss that a different model would catch (section G #18) |
| 5 | Secret brokers or per-agent credential scopes | Scrubbed child environment; only the engine reads the configured secret | No revisit trigger recorded in section G |
| 6 | Cost forecasting, provider routing, dashboards | Token and USD tracking with hard stops | Any billing-relevant decision (section G #12) |
| 7 | SQLite, event replay, recovery tooling | Snapshot state plus append-only audit logs, no replay | Concurrency or recovery requirements appear (section G #7) |
| 8 | Resumable approvals, `approve` and `resume` commands, remote approval | Interactive approval per execution; non-TTY means deny | Unattended or long-running operation (section G #8) |
| 9 | Controlled self-improvement, evaluation and rollback, and any agent-proposed change to its own rules | Policy and limits owned by the human | No revisit trigger recorded in section G; governance is in `AI_Engineering_Team.md` §2.7 and §2.8 |
| 10 | Web interface, mobile and voice control | CLI plus markdown report | No revisit trigger recorded in section G |
| 11 | Unreal Engine tooling and other production projects | Snake as the end-to-end fixture | No revisit trigger recorded in section G; `C:\AIProjects\UnrealAIEngineering` remains a separate project (charter §6) |

## 2. Revisit triggers carried from section G

Section G records one revisit trigger per design decision. They are the conditions under which a Phase 1 choice is reconsidered; they are not approvals.

| # | Decision area | Revisit trigger |
|---|---|---|
| 1 | Isolation level | Any need for unattended or parallel work, or execution of untrusted code |
| 2 | Path checks | Any proposal to run without approval |
| 3 | Executing generated code | Prompt fatigue observed in practice |
| 4 | Package installation | First project that genuinely needs a third-party package |
| 5 | QA independence | Recurring bugs in QA-passed work |
| 6 | Report authorship | Reports judged insufficient |
| 7 | State persistence | Concurrency or recovery requirements appear |
| 8 | Approval resumability | Unattended or long-running operation |
| 9 | Plan size | Larger projects need more tasks |
| 10 | Retry semantics | Observed misclassification |
| 11 | Provider strategy | Adding a provider without native tool calls |
| 12 | Pricing source | Any billing-relevant decision |
| 13 | Snake technology | If a real UI is required as a gate |
| 14 | Generated work location | First time a rollback is needed |
| 15 | Git strategy | Phase 4 worktrees and branches |
| 16 | Context growth | Agents failing for missing information |
| 17 | Developer tool restriction | Repeated cases where the Developer cannot proceed without execution |
| 18 | QA model choice | QA misses a defect that a different model would catch |

## 3. Open and partly resolved decisions (section G.2)

- **Item 3 — partly resolved.** Model choice is configured; the run budget for a live run remains a Human decision at that run (M5 used USD 0.10, M7 used USD 0.50).
- **Item 4 — open.** Whether project slugs other than the Snake fixture stay git ignored after Phase 1. The plan's recommendation is to keep them ignored until Git isolation exists.
- **Item 7 — partly resolved.** QA used the same model as the Developer in Phase 1. Whether to assign a different model or a second provider per role, and how to compare cost, speed and quality, remains open.
- The charter's own open list is [`AI_Engineering_Team.md`](../AI_Engineering_Team.md) §7 "Still open"; it is pointed to here, not copied.

## 4. Three-role versus two-role comparison

Recorded per the plan's "After Phase 1 — architecture comparison" section and the M8 checklist entry. Recording the plan is documentation only; it changes no code.

- **Question:** does the Orchestrator earn its cost, compared with a Developer plus Independent QA pipeline and no Orchestrator?
- **Baseline data source:** M7 run `20261127T232029Z-30ab3e` (project `snake`, provider `deepseek`, model `deepseek-flash`, budget USD 0.50): 3/3 tasks `done`, 3/3 QA verdicts `pass`, final QA suite 56 tests with exit code 0, nine per-execution approvals all granted, actual USD 0.294202.
- **Metrics, using the recorded run data only:**

| Metric | Definition | Where the baseline value comes from |
|---|---|---|
| Cost | Total USD, and USD per agent | Run report and usage records for `20261127T232029Z-30ab3e` |
| Attempts | `task.attempt` per task and number of retries actually started | Run report and event log |
| Defects found by QA | Failed QA checks mapped to criterion IDs before the pass verdict | QA verdict records in the run |
| Defects missed | Defects not caught by QA that the human spot check or a later run revealed | Recorded human spot check and later run evidence |
| Human interventions | Number of per-execution approvals, denials and escalations | Approvals log for the run |

- **Method:** a two-role pipeline needs its own run with the Orchestrator removed and the plan supplied directly. That is a configuration change outside Phase 1 scope, so it is not run here; the comparison stays an evaluation of the same system.

### 4.1 Measured result from the M7 run

Measured on the three-role run only. No two-role run was executed. The figures come from `runs/20261127T232029Z-30ab3e/report.md`; the two-role figure is stated as a bound, not a measurement.

| Metric | Three-role value (measured) | Source |
|---|---|---|
| Total cost | USD 0.294202 of a USD 0.50 budget | Run report, Cost table |
| Cost per agent | developer USD 0.041077 (14 calls), orchestrator USD 0.003216 (1 call), QA USD 0.249909 (48 calls) | Run report, Cost table |
| Orchestrator share | 1.1% of cost and 1 of 63 calls (1.6%) | Derived from the Cost table |
| Attempts | 3 tasks, each at attempt 1, no retry started | Run report, Execution table |
| Defects found by QA | No product defect reported. Three failed QA executions were faults in QA's own test oracles (T1 two, T2 one, T3 one) and were fixed inside QA | QA evidence summaries; 9 recorded command executions |
| Defects missed | None recorded after the pass verdict, and the human spot check accepted the suite. A single run cannot bound this | QA evidence; recorded spot check |
| Human interventions | 9 per-execution approvals, all granted; 0 denials; 0 escalations; 1 post-run QA test file spot check; 2 earlier attempts blocked by token limits | Approvals table; Phase 1 plan §E M7 status |

- **Two-role projection:** removing the Orchestrator saves at most USD 0.003216, about 1.1% of this run, and only if the plan is supplied at no cost. If the Developer must produce the plan, its cost rises by an unmeasured amount. Attempts, QA defect detection and human intervention under two roles are unmeasured.
- **Conclusion:** on this run the Orchestrator cost about 1% of the total and produced a three-task plan whose criteria mapped one-to-one to QA checks. The measured upside of removing it is small and the quality risk is unmeasured, so this evidence does not justify a two-role pipeline. The evaluation changed no code and no engine behaviour.
- **Status:** authorised by the Human on 2026-11-28 and the result recorded on the same date from the three-role baseline. No two-role run was executed and none is planned.

## 5. Other recorded deferrals (pointers outside section G)

These are already recorded elsewhere; they are listed here for completeness and are not restated as new requirements.

- `README.md` §5 deliberate non-goals for the engine and execution layer: Docker isolation, Git worktree isolation for generated work, SQLite, checkpoint resume, parallel tasks, external monitoring, self-improvement, a Consultant role, and mobile or voice approval. Review worktrees remain a tooling operation, not Phase 1 engine isolation.
- `README.md` §1.1 Project limitations: no Git hook and no CI are installed, and preflight is manual.
- `plans/phase1-architecture-plan.md` checklist: the M1–M3 formal closeout was recorded on 2026-11-28 from existing test evidence, so this item is closed.
- `PROJECT_STATE.md` §2: the WP2 Revision 1 observability, governance and evolution steps A1–A4 are not authorised.

## 6. Update rule

Add an item only when the authoritative plan or charter defers it, and cite the source section. Record a status change in the same work package that changes the source document. Never mark an item here as authorised, accepted or complete.
