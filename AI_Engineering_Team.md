# AI Engineering Team

**Project Context & Living Specification**

Last updated: 23 November 2026

**Status:** Canonical charter, proposed revision 3 (documentation clarity pass — `PROPOSAL — HUMAN APPROVAL REQUIRED`). Phase 1 is in progress: M0 closeout is recorded, M1–M3 implementation is present with formal closeout `UNVERIFIED`, M4 is completed, reviewed and merged into `main` at `9c11b6a`, and Phase 1 is not accepted.

## 1. Project Vision

Build a personal AI Engineering Team that can take instructions, plan work, delegate tasks to specialised AI agents, execute projects, verify results and report back.

The goal is not simply to have an AI coding assistant. It is to build a reusable system that can manage real engineering work with a reasonable level of autonomy.

The system is for personal use, not initially intended as a commercial product.

### Initial test project

Build a simple Snake game to test the complete workflow:

1. User describes what they want.
2. AI analyses the request and creates tasks.
3. Developer Agent implements the project.
4. Independent QA Agent tests the result.
5. The workflow system manages failures and retries.
6. User receives the final result or is asked to make a decision.

The Snake game is a test of the team infrastructure, not the main product.

### Future applications

The same infrastructure should eventually support:

- Unreal Engine profiling and assisted optimisation tools.
- Other software and engineering projects.
- A private AI-powered investment research system.
- Other projects that may require different specialist agents.

The architecture should be reusable without being unnecessarily complicated.

---

## 2. Core Principles

These are the main principles behind the project. They guide design decisions but should not prevent future improvements.

### 2.1 Independent Agents

Agents should have their own responsibilities, instructions, tools and working contexts.

A Developer and a QA Agent should not simply be the same AI switching roles in one conversation.

Agents do not need to run continuously. Their identities, instructions and work records should persist, while separate sessions can be started whenever needed.

### 2.2 Clear Responsibilities

Each agent should have a clear purpose and boundaries.

Possible roles include:

- Chief of Staff / Orchestrator
- Developer
- QA / Verifier
- Researcher
- Environment Manager
- Profiling Specialist
- Gardening Agent
- Independent Consultant / Reviewer

These are examples, not a fixed list. New roles can be introduced when they provide real value.

### 2.3 Independent Verification

An agent completing a task does not automatically mean the task is successful.

QA should independently inspect and test the actual result, rather than simply accepting the Developer's report.

Verification should include relevant execution results, test evidence and acceptance criteria.

### 2.4 Context Management

Agents should receive the information they need, not the entire conversation history.

Task handoffs should contain relevant requirements, context, interfaces, acceptance criteria and previous results.

The system should preserve important project knowledge without allowing individual agent contexts to grow indefinitely.

### 2.5 Human Control

The user remains the final decision-maker.

Agents can propose plans, changes and improvements, but important decisions should remain under user control.

Autonomy should increase gradually as the system demonstrates reliability.

### 2.6 Practical Over Complexity

Use scripts and deterministic tools for predictable tasks. Use AI where reasoning, judgement or interpretation is required.

Avoid building infrastructure that does not solve an actual problem.

### 2.7 Controlled Self-Improvement

The team should improve its own capabilities over time through a controlled, measurable and independently verified process.

The system should eventually be able to:

- Analyse task outcomes, failures, retries, costs and QA results.
- Identify recurring weaknesses and inefficiencies.
- Propose improvements to agent prompts, workflows, tools and architecture.
- Delegate approved improvements to development agents.
- Use independent QA to verify changes.
- Evaluate whether the changes actually improve performance.
- Retain successful improvements and support rollback when necessary.

Improvements should be accepted on evidence rather than confidence. The team must not weaken its own security rules, approval requirements, budget limits or verification standards without explicit human approval.

Self-improvement is a long-term design principle. Phase 1 does not implement it.

### 2.8 Governance of the Team's Own Rules

The human remains the ultimate authority.

Agents may analyse, recommend, plan and execute permitted work. They may not change the rules that govern them, including architecture boundaries, security rules, permission policies, approval requirements, verification standards or financial limits, without explicit human approval.

A system that can lower its own guardrails is not autonomous, it is uncontrolled.

---

## 3. System Overview

The system can be understood as several cooperating parts.

### User

Provides goals, requirements, budget limits and approval for important decisions.

### Chief of Staff / Orchestrator

Understands the user's request, plans the work, delegates tasks and coordinates agents.

It should focus on project-level reasoning rather than doing every specialist task itself.

### Specialist Agents

Independent agents responsible for specific work.

They should have suitable tools, permissions and isolated working contexts.

### Independent Consultant / Reviewer — future role

A possible future role that reviews work rather than producing it.

Its responsibilities may include:

- Independently reviewing architecture and implementation decisions.
- Inspecting project files, Git history, execution records and QA reports.
- Identifying weaknesses and challenging existing assumptions.
- Recommending improvements.
- Producing independent technical review reports.

The Consultant must have a separate session and context from the Orchestrator and Developer. It should not automatically implement or approve its own recommendations. Implementation remains with the Developer and verification remains with QA, both under the Workflow Engine's control.

This role is not a Phase 1 requirement.

### Agents, roles and model providers

An agent is a role with its own instructions, context, tools and permissions. A model provider such as DeepSeek is the technology that powers a role.

The same provider may power several independent roles without making those roles the same agent. Role definitions and provider configuration stay separate, so a provider can be replaced without changing who does what.

### Python Workflow Engine

The deterministic control layer of the system.

Its responsibilities may include:

- Managing tasks and workflow states.
- Starting and coordinating agent sessions.
- Tracking progress and results.
- Managing retries and failure handling.
- Maintaining project records.
- Enforcing permissions and cost limits.

The Python system should own workflow state. It should not depend on an AI agent remembering everything correctly.

### Shared Engineering Environment

The environment where actual work happens.

Possible components include:

- Git and isolated working branches.
- Project files and workspaces.
- Command-line tools and scripts.
- Automated tests and verification.
- Development environments and dependencies.

The exact tools and architecture can evolve.

---

## 4. Operating Principles

### 4.1 Task Workflow

A typical workflow:

**Request → Plan → Delegate → Execute → Verify → Report**

The workflow should be flexible enough to support different project types and levels of complexity.

Not every task needs every agent.

### 4.2 Failure Handling

When a task fails:

1. Capture the error and relevant evidence.
2. Allow a limited number of retries or corrections.
3. Stop when the failure limit is reached.
4. Report the problem and possible solutions to the user.
5. Let the user decide what happens next.

The system should not enter endless retry loops.

### 4.3 Permissions and Safety

Agents should only have the permissions necessary for their responsibilities.

Routine actions inside an approved project environment may be automated.

Actions with wider system impact, security implications or significant risk should require user approval.

Examples include system-level software installation, driver changes, registry modifications and administrative operations.

The boundary between routine and sensitive action is defined by the current phase plan and may be tightened by the human at any time. Agents cannot widen their own permissions.

### 4.4 Environment Management

The team should be able to inspect project environments, identify missing dependencies and handle routine setup where permitted.

Installation and configuration should be recorded and verified.

Uncertain or risky system changes should be escalated to the user.

Setup is limited by the current phase plan. Phase 1 permits no package installation at all; missing dependencies are reported to the user as manual actions.

### 4.5 Cost Management

AI usage should be measurable and controllable.

The system should be able to track costs by task and agent, enforce budgets, limit retries and stop work when agreed limits are reached.

Provider-specific pricing and limits should not be hardcoded into the overall architecture.

### 4.6 Controlled Self-Improvement

A future Gardening Agent may analyse recurring failures, duplicated work, retry costs and QA results.

It should help improve shared instructions, tools, tests and workflows rather than relying only on agents remembering past mistakes.

Any proposed improvement follows the same path as ordinary work:

1. Evidence is collected from task outcomes, failures, retries, costs and QA reports.
2. A weakness or inefficiency is identified and described.
3. An improvement is proposed, scoped and tied to the evidence that motivated it.
4. The proposal is approved by the human where it affects architecture, security, permissions, approvals, budgets or verification standards.
5. Approved work is delegated to development agents.
6. Independent QA verifies the change.
7. The change is evaluated against the previous behaviour.
8. Successful changes are retained; failed changes are rolled back.

The team must never weaken its own security rules, approval requirements, budget limits or verification standards without explicit human approval.

### 4.7 Governance and Human Authority

The human remains the ultimate authority.

Agents may analyse, recommend, plan and execute permitted work. Changes to core architecture, security boundaries, permission policies, approval requirements, verification standards and financial limits remain subject to explicit human control.

The Orchestrator and any other agent must not be able to modify the rules that govern their own operation. Changes of that kind are human actions, or require recorded human approval before taking effect.

### 4.8 Document Change and Review Governance

Document changes follow a three-role separation. No role may substitute for another.

| Role | Actor | Owns | Must not |
|---|---|---|---|
| **Merge Executor (Worker)** | Zoo Code | Executing document edits, running the required checks, the Git operations on a review branch, and executing the merge only after explicit approval from the Approver | Approve a merge; execute a merge without explicit approval from the Approver; treat its own summary as review evidence |
| **Reviewer** | ChatGPT | Independently inspecting the actual files and the Git diff, for example on GitHub, and raising corrections | Rely on the Worker's summary instead of the repository; approve a merge; execute a merge |
| **Merge Approver** | User | Holding the only merge approval authority: deciding whether to merge a review branch into `main`, accepting or rejecting the change, and authorizing the next stage of work. The User may execute the approved merge personally or delegate execution to Zoo Code | — |

Mandatory workflow:

1. The Worker makes every document change on a separate review branch. `main` is never edited directly.
2. When the change is complete, the Worker runs the required checks, commits the change and pushes the review branch.
3. The Reviewer independently inspects the actual documents and the Git diff, for example on GitHub. A summary from the Worker is not evidence.
4. If the Reviewer finds problems, the Worker corrects them and resubmits for review. Review and correction repeat until the Reviewer has no material objection.
5. Merge approval and merge execution:
   - The User is the only Merge Approver. The User may execute the merge personally, or authorize Zoo Code to execute it.
   - Zoo Code is the Merge Executor. It executes a merge only after the User explicitly approves it and instructs it to do so.
   - No person or agent may merge without the User's explicit approval.
   - The Reviewer (ChatGPT) does not execute merges. A successful review is not merge approval.
6. Approval to merge a document change does not authorize the next stage of work. Further work needs its own explicit approval.

Protection rule: unapproved changes and pre-existing uncommitted changes must never be swept into a review branch or a merge. A review branch contains only the change under review, and the Worker states explicitly which files are in scope.

Git requirements for the Worker:

- Base every review branch on the current `main`.
- Keep the commit limited to the files in scope.
- Preserve unrelated uncommitted work in the working tree. Never stage, commit or merge it without approval.
- Do not modify, rewrite or merge an existing review branch that is already under review.
- Push the review branch; do not merge it.

These rules govern documents and review. They do not replace the technical controls on workflow state, approvals, budgets and verification defined elsewhere in this charter and in the phase plans.

---

## 5. Development Roadmap

This is an indicative development direction, not a fixed implementation plan.

The phase names describe capability order, not a one-to-one mapping to implementation plan milestones. A phase plan may combine several early capabilities into one vertical slice, provided the principles in this charter are preserved.

### Phase 1 — Foundation

- Build the basic Python Workflow Engine.
- Establish task tracking and persistent records.
- Connect an AI model provider.
- Create the initial Orchestrator workflow.

### Phase 2 — First Agent Team

- Introduce a Developer Agent.
- Introduce an independent QA Agent.
- Establish task handoffs and context separation.
- Implement basic failure handling and retry limits.

### Phase 3 — Snake Game Test

- Ask the team to build a Snake game.
- Run the complete development and verification workflow.
- Evaluate whether agents can work independently.
- Identify weaknesses in coordination, testing and context management.

### Phase 4 — Reliability and Control

Gradually introduce:

- Git-based work isolation.
- Permission management.
- Cost monitoring.
- Environment management.
- Better logging and recovery.
- Shared tools and reusable agent skills.
- Recorded, human-approved improvements to prompts, tools and workflows based on evidence.

### Phase 5 — Expansion

Explore additional specialist agents and more complex workflows.

Potential future features:

- Gardening Agent.
- Independent Consultant / Reviewer.
- Controlled self-improvement loop with evaluation and rollback.
- Proactive project monitoring.
- Mobile control interface.
- Voice commands and voice responses.
- Human approval through a mobile device.

These features should be added when the foundation is reliable, not all at once. None of them are Phase 1 requirements.

---

## 6. Current Setup & Progress

### Development Environment

Verification status:

- **Verified**: confirmed in the current environment.
- **Previously confirmed**: established in earlier project discussions but not rechecked in this workspace.
- **Not yet confirmed**: information that still needs checking.

| Item | Current status | Verification |
| --- | --- | --- |
| Operating system | Windows 11 | Verified |
| IDE | VS Code | Verified |
| Coding assistant | Zoo Code | Verified |
| Main project directory | `C:\AIProjects\AIEngineeringTeam` | Verified |
| Python | 3.12.16 | Verified in `ai-team` (2026-11-23) |
| Python environment | Conda: `ai-team` | Verified |
| Second Python environment | Conda: `local-agent` | Previously confirmed |
| Python distribution | Miniconda | Previously confirmed |
| pip | Available in `ai-team` | Verified in M0 |
| Version control | Git | Verified 2026-11-23; branch `main`, HEAD `b78eaed` (the previously recorded `2433660` is obsolete) |
| OpenAI SDK | 3.57.0 installed in `ai-team` | Verified 2026-11-23 |
| tiktoken | 0.14.0 installed in `ai-team` | Verified 2026-11-23 |
| pytest | 9.2.0 installed in `ai-team` | Verified 2026-11-23; full offline suite 294 passed, 5 skipped |
| tkinter | Tk 8.6 present | Verified in M0; not required for headless acceptance |
| Git repository in this workspace | Branch `main` at `b78eaed`, synced with `origin/main` and the public remote | Verified 2026-11-23 |

Zoo Code is currently installed and being used in VS Code. The choice of coding assistant remains revisable.

The live provider is DeepSeek through the OpenAI-compatible SDK adapter, with model `deepseek-flash` and an explicit endpoint in `config/aiteam.toml`. The provider adapter remains replaceable. Phase 1 uses no Agent Framework, as recorded in [`plans/adr-001-hybrid-architecture.md`](plans/adr-001-hybrid-architecture.md).

`C:\AIProjects\UnrealAIEngineering` is a separate Unreal Engine project. It is not part of this AI Engineering Team workspace.

### Current Stage

The approved architecture is Hybrid: this project builds the decisions, while provider SDKs and commodity components may be adopted. The Python Workflow Engine remains the sole authority over workflow state, execution, permissions, approvals, budgets, retries, evidence validation and final acceptance. The local workspace remains the current implementation, and no generic Workspace Protocol is introduced without a real second implementation.

#### Milestone status (M0–M8)

The Phase 1 plan is the canonical milestone record. Three completion states are kept separate: implementation present is not formal closeout, and formal closeout is not Human acceptance.

| Milestone | Implementation | Formal closeout | Human acceptance | Evidence |
|---|---|---|---|---|
| M0 Environment and repository verification | Completed | Recorded — report PASS | Not separately recorded | `records/m0-environment-report.md` |
| M1 FakeProvider walking skeleton | Present | `UNVERIFIED` — no closeout artefact | `UNVERIFIED` | source and tests exist; no closeout record |
| M2 QA execution, evidence and approval | Present | `UNVERIFIED` — no closeout artefact | `UNVERIFIED` | source and scenario tests exist; no closeout record |
| M3 Cost accounting and budget enforcement | Present | `UNVERIFIED` — no closeout artefact | `UNVERIFIED` | cost modules and tests exist; no closeout record |
| M4 Retry and escalation | Completed and merged | Recorded — reviewed and merged at `9c11b6a` | Merge approved by the Human 2026-11-24 | `tests/scenarios/test_retry_then_pass.py`, `tests/scenarios/test_retry_exhausted.py`, `tests/test_m4_retry.py` |
| M5 Live provider validation | Diagnostic only | Not recorded | Not recorded | run `20261123T110208Z-97bc01`; formal acceptance explicitly not recorded |
| M6 Snake specification | Not started | Not started | Not started | no `projects/snake` artefact |
| M7 Snake live end-to-end run | Not started | Not started | Not started | — |
| M8 Documentation and progress | Not started | Not started | Not started | — |

Status notes:

- The DeepSeek Live E2E diagnostic succeeded on `projects/diagnostic` (run `20261123T110208Z-97bc01`): the task completed, the engine accepted the QA evidence, 7 API calls were recorded, and actual cost was USD 0.004748 with no outstanding or uncertain reservation. It created a `hello.txt` file and is not the Snake Game acceptance run.
- An earlier revision of this section described M0–M3 as implementation closeout complete. Under the three-state separation above that wording overstated the evidence for M1–M3: implementation is present, but no M1–M3 closeout artefacts exist in the repository. This correction is `PROPOSAL — HUMAN APPROVAL REQUIRED`.
- M4 retry and escalation are completed and merged (`9c11b6a`). Only an engine-confirmed QA failure backed by verified non-zero execution evidence retries once; exhausted attempts escalate. `BudgetError`, provider, engine and infrastructure failures never retry. The status and evidence wording for M4 was updated in documentation commit `85d6c90`.
- Phase 1 is not accepted. Acceptance requires the Snake run and the recorded human spot check defined in the Phase 1 plan.

#### Milestone dependencies

- M0 → M1 → M2 → M3 → M4 → M5 → M6 are sequential.
- M5 is the next milestone; M6 begins only after M5 is completed.
- M7 requires completed M5 and M6.
- M8 runs only after M7 is complete and accepted.

These dependencies are recorded in `plans/phase1-architecture-plan.md` and restated here for visibility; they are not a new decision.

#### Outstanding work

- M5 formal live-provider milestone acceptance and closeout.
- M6 Snake specification with criterion IDs and a negative test.
- M7 Snake live end-to-end run and the human QA test-file spot check.
- M8 progress and backlog closeout.

#### Current position and next required milestone

- [FACT] Current position: Phase 1, implementation present through the M4 scope, M5 diagnostic only, Phase 1 not accepted.
- [FACT] M4 was completed, independently reviewed and merged into `main` at `9c11b6a` on 2026-11-24 with explicit Human merge approval.
- [FACT] The documented dependency order makes M5 the next valid milestone; M6 follows once M5 is completed, then M7 and M8 in turn.
- `NO TASK AUTHORISED`: neither M5 nor M6 work is authorised by this charter. Each needs its own explicit Human authorization.
- The operational snapshot for continuation sessions is [`PROJECT_STATE.md`](PROJECT_STATE.md). It is a derived summary only, not an independent authority: this charter remains authoritative for principles, governance and decisions, and the Phase 1 plan remains the canonical milestone record. On any conflict those documents win.

The Phase 1 blueprint is kept in `plans/phase1-architecture-plan.md` and is subordinate to this charter and to ADR-001.

---

## 7. Open Decisions

### Decided and no longer open

- Hybrid architecture: build the decisions, adopt the mechanics; the Python Workflow Engine keeps sole authority (ADR-001).
- No Agent Framework in Phase 1. Any future framework or execution runtime requires a separate evidence-based decision.
- The local workspace remains the implementation. No generic Workspace Protocol is added without a real second implementation.
- The live provider is DeepSeek through the OpenAI-compatible adapter, using `deepseek-flash`; provider, model and pricing live in `config/aiteam.toml`.
- Independent per-role sessions and scoped handoff bundles are implemented, and every generated-code execution needs its own human approval.
- Existing choices are not automatically refactored to match recommendations in the Architecture Decision Review.
- Zoo Code orchestration issues are recorded as OD-001 in `plans/operations-decisions.md` and are not Python Workflow Engine defects.

### Still open

- Whether to assign a different model, or add a second provider, per role; and how to compare cost, speed and quality.
- When, if ever, to adopt an agent framework or an external execution substrate, subject to evidence and a new ADR.
- Whether and when to add stronger isolation such as Docker, WSL2, an OpenHands-class runtime or Git worktrees.
- Mobile and voice control, including remote approval.
- Which additional specialist agents are worth creating, and when to introduce the Independent Consultant / Reviewer and to whom it reports.
- Which measures define a genuine improvement for controlled self-improvement, and how rollback decisions are governed.
- How human approval should govern future changes to policies, prompts and budgets as the system gains autonomy.

New technologies and better approaches can be considered at any stage.

The system should not be locked into a particular provider, framework or fixed number of agents without a good reason.

---

## 8. How to Use This Document

This document is the shared project context for future conversations and AI sessions.

When continuing the project:

1. Read this document before making recommendations or implementation changes.
2. Respect the difference between established principles and open decisions.
3. Avoid asking the user to repeat information already documented here.
4. Suggest improvements when there is a clear practical benefit.
5. Update this document when important decisions, architecture or project progress change.
6. Treat this document as authoritative when it conflicts with an implementation plan or with code. Resolve the conflict in favour of this charter, or update the charter deliberately first.

**This is a living document, not a rigid technical contract.**

Its purpose is to keep the project direction clear while leaving enough freedom to discover better solutions.