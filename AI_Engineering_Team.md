# AI Engineering Team

**Project Context & Living Specification**

Last updated: 18 November 2026

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

### 4.4 Environment Management

The team should be able to inspect project environments, identify missing dependencies and handle routine setup where permitted.

Installation and configuration should be recorded and verified.

Uncertain or risky system changes should be escalated to the user.

### 4.5 Cost Management

AI usage should be measurable and controllable.

The system should be able to track costs by task and agent, enforce budgets, limit retries and stop work when agreed limits are reached.

Provider-specific pricing and limits should not be hardcoded into the overall architecture.

### 4.6 Continuous Improvement

A future Gardening Agent may analyse recurring failures, duplicated work and common mistakes.

It should help improve shared instructions, tools, tests and workflows rather than relying only on agents remembering past mistakes.

---

## 5. Development Roadmap

This is an indicative development direction, not a fixed implementation plan.

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

### Phase 5 — Expansion

Explore additional specialist agents and more complex workflows.

Potential future features:

- Gardening Agent.
- Proactive project monitoring.
- Mobile control interface.
- Voice commands and voice responses.
- Human approval through a mobile device.

These features should be added when the foundation is reliable, not all at once.

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
| Python | 3.12.16 | Previously confirmed |
| Python environment | Conda: `local-agent` | Previously confirmed |
| Python distribution | Miniconda | Previously confirmed |
| Version control | Git | Previously confirmed |
| OpenAI SDK | Installed | Previously confirmed |
| Git repository in this workspace | Not yet checked | Not yet confirmed |

Zoo Code is currently installed and being used in VS Code. The choice of coding assistant remains revisable.

`C:\AIProjects\UnrealAIEngineering` is a separate Unreal Engine project. It is not part of this AI Engineering Team workspace.

### Current Stage

The project is at the architecture and foundation planning stage.

The immediate objective is to build a working basic system, not to implement every future feature.

---

## 7. Open Decisions

The following areas remain flexible and should be evaluated as the project develops:

- Which AI model providers to use.
- Which coding assistant and agent execution framework to adopt.
- How to create and manage independent agent sessions.
- How agents should communicate and exchange task information.
- How much autonomy each agent should receive.
- How to balance model cost, speed and quality.
- How to provide mobile and voice control.
- Which additional specialist agents are worth creating.

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

**This is a living document, not a rigid technical contract.**

Its purpose is to keep the project direction clear while leaving enough freedom to discover better solutions.