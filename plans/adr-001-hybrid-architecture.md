# ADR-001: Hybrid Architecture — Build the Decisions, Adopt the Mechanics

- **Status:** Accepted
- **Decision date:** 2026-11-23
- **Decision owner:** Human
- **Related:** [`AI_Engineering_Team.md`](../AI_Engineering_Team.md) (charter), [`plans/architecture-decision-review.md`](architecture-decision-review.md) (evidence record, not authority)

## Context

The project needed a position on how much to build itself versus how much to adopt from existing agent frameworks and runtimes. The Architecture Decision Review evaluated fully custom, framework-based and hybrid options. Its recommendation is Option C, Hybrid, and the human has now accepted that recommendation.

This ADR records the decision itself. It does not reproduce the review's reasoning and it does not authorize implementation changes.

## Decision

1. **Build the decisions, adopt the mechanics.** The parts that carry authority, policy, state and acceptance are built in this project. Commodity transport and infrastructure may be adopted.
2. **The Python Workflow Engine retains sole authority** over workflow state, execution, permissions, approvals, budgets, retries, evidence validation and final acceptance.
3. **Provider SDKs and commodity components may be adopted.** The provider SDK is transport. It returns data to the engine; it does not decide anything.
4. **No Agent Framework is required for Phase 1.** The three-agent-role pipeline, coordinated by the Python Workflow Engine, does not earn the weight of a framework today.
5. **Future frameworks and execution runtimes remain subject to separate evidence-based decisions.** Adopting one later requires its own decision record and evidence, not preference.
6. **The local workspace remains the current implementation.** The workspace is a local project directory with guarded tools.
7. **Do not introduce a generic Workspace Protocol without a real second implementation.** A seam with one implementation is premature abstraction; add it only when a second backend is actually being built.
8. **Existing implementation choices must not be automatically refactored** to match recommendations in the Architecture Decision Review. Recommendations are inputs to future decisions, not retroactive mandates.

## Consequences

- Agents propose plans, edits, reports and verdicts; they never transition tasks, approve actions, change budgets or accept their own work.
- Provider adapters and tool layers are replaceable mechanisms below the engine. They may fail, but they cannot decide.
- Framework or runtime adoption stays deferred behind narrow boundaries until a concrete second implementation justifies it.
- The architecture remains small enough to inspect and test, at the cost of maintaining a custom engine.
- Phase 1 acceptance is still governed by the Snake end-to-end run and the human QA spot check. This ADR does not accept Phase 1.

## Guardrails

This ADR is **not** authorization to change source code, weaken approvals, relax budgets, bypass evidence validation, or introduce a framework. Any such change requires its own approved proposal and, where architectural, a separate ADR.

Policy, approval requirements, budget rules and verification standards remain human-owned and cannot be relaxed by any agent, including the Orchestrator.
