# AI Engineering Team

**Project Context & Living Specification**

Last updated: 23 November 2026

**Status:** Canonical charter, proposed revision 3 (documentation clarity pass — `PROPOSAL — HUMAN APPROVAL REQUIRED`). Phase 1 is in progress and is not accepted. Milestone status, evidence and acceptance are recorded in the Phase 1 plan; the current position is in `PROJECT_STATE.md`.

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

Operating detail for AI sessions — bootstrap, review procedure, evidence and Git rules — is defined in `AGENTS.md`. This section states this project's principles only.

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

The User is the only Merge Approver. Every document or code change goes through a separate review branch, an independent review of the actual files and diff by the Reviewer, and explicit Human approval before merge. A successful review is not merge approval, and approval to merge one change never authorises the next stage of work.

The operating detail — branch creation, change scope, preflight, evidence package, review handoff, blocked cases and post-merge cleanup — is defined once in `AGENTS.md` §7. These rules do not replace the technical controls on workflow state, command approvals, budgets and verification defined in §4.3 and in the Phase 1 plan.

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

## 6. Current Setup

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
| Version control | Git | Verified 2026-11-23; branch `main`. No HEAD SHA is stored here; run `git rev-parse HEAD` and compare with `origin/main` when alignment needs it |
| OpenAI SDK | 3.57.0 installed in `ai-team` | Verified 2026-11-23 |
| tiktoken | 0.14.0 installed in `ai-team` | Verified 2026-11-23 |
| pytest | 9.2.0 installed in `ai-team` | Verified 2026-11-23; current suite results are recorded in the Phase 1 plan, not here |
| tkinter | Tk 8.6 present | Verified in M0; not required for headless acceptance |
| Git repository in this workspace | Branch `main`, synced with `origin/main` | Verified 2026-11-23; re-verify rather than storing a SHA |

Zoo Code is currently installed and being used in VS Code. The choice of coding assistant remains revisable.

The live provider is DeepSeek through the OpenAI-compatible SDK adapter, with model `deepseek-flash` and an explicit endpoint in `config/aiteam.toml`. The provider adapter remains replaceable. Phase 1 uses no Agent Framework, as recorded in [`plans/adr-001-hybrid-architecture.md`](plans/adr-001-hybrid-architecture.md).

`C:\AIProjects\UnrealAIEngineering` is a separate Unreal Engine project. It is not part of this AI Engineering Team workspace.

### Current Stage

The approved architecture is Hybrid: this project builds the decisions, while provider SDKs and commodity components may be adopted. The Python Workflow Engine remains the sole authority over workflow state, execution, permissions, approvals, budgets, retries, evidence validation and final acceptance. The local workspace remains the current implementation, and no generic Workspace Protocol is introduced without a real second implementation.

#### Where progress is recorded

Implementation present, formal closeout and Human acceptance are three separate states. The Phase 1 plan is the canonical milestone record: milestones, dependencies, completion criteria, required evidence and acceptance are recorded there and nowhere else. [`PROJECT_STATE.md`](PROJECT_STATE.md) is the compact continuation snapshot; it records the current position and which work is authorised. This charter states no milestone status of its own.

`NO TASK AUTHORISED`: neither M5 nor M6 work is authorised by this charter. Each requires its own explicit Human authorization.

The Phase 1 blueprint is kept in `plans/phase1-architecture-plan.md` and is subordinate to this charter and to ADR-001.

---

## 7. Open Decisions

### Decided and no longer open

- Hybrid architecture: build the decisions, adopt the mechanics; the Python Workflow Engine keeps sole authority (ADR-001).
- No Agent Framework in Phase 1. Any future framework or execution runtime requires a separate evidence-based decision.
- The local workspace remains the implementation. No generic Workspace Protocol is added without a real second implementation.
- The live provider is DeepSeek through the OpenAI-compatible adapter, using `deepseek-flash`; provider, model and pricing live in `config/aiteam.toml`.
- Independent per-role sessions and scoped handoff bundles are implemented, and every generated-code execution needs its own human approval.
- Existing implementation choices are not automatically changed solely to align with past review recommendations.
- Zoo Code orchestration issues are not Python Workflow Engine defects; see AGENTS.md §7.6.

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