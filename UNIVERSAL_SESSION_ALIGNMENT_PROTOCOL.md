# Universal Session Alignment Protocol

- **Version:** Draft 1 (initial draft — not yet V1.0)
- **Purpose:** Start a new AI session and confirm that it understands the project before any work begins.
- **Applies to:** any project, any repository-capable coding agent (for example Zoo Code), and any chat-based assistant (for example ChatGPT).
- **Human trigger phrase:** "Read this document and follow its steps to start the Alignment Test."

This document has two parts:

1. **Part 1 — Project Configuration.** The only part edited per project.
2. **Part 2 — Universal Protocol.** Do not edit. It is identical for every project.

If a rule here conflicts with the project's own governing documents, the project documents win for project facts, and this protocol wins only for the *process* of alignment. Report the conflict; do not silently resolve it.

---

## Part 1 — Project Configuration

> Edit only this table. Replace every `<...>` placeholder.
> Use `NOT CONFIGURED` for a field that does not apply. Never invent a path.
> Paths are relative to the project root unless written as absolute.

| Field | Value |
|---|---|
| Project name | `<PROJECT_NAME>` |
| Project root | `<PROJECT_ROOT>` |
| Primary entry document | `<PATH>` |
| Architecture / design documents | `<PATH>, <PATH>` |
| Decision records | `<PATH>, <PATH>` |
| Status / progress documents | `<PATH>` |
| Technical specifications | `<PATH>, <PATH>` |
| Tests / evidence / logs | `<PATH>, <PATH>` |
| Git repository (URL or local path) | `<GIT_URL_OR_PATH>` |
| Current branch | `<BRANCH>` |
| Current milestone / phase | `<MILESTONE>` |
| Current task | `<TASK>` |
| Document authority order (optional) | `<HIGHEST>, ..., <LOWEST>` |
| Project-specific restrictions | `<RESTRICTIONS>` |

Configuration rules:

1. The **primary entry document** is the single document every participant must read first.
2. Paths listed here are *candidates*, not a reading list. Part 2 decides what to read.
3. A path that does not exist is reported as `MISSING` and never recreated or guessed.
4. Project-specific restrictions are mandatory constraints for every stage, including read-only ones.

---

## Part 2 — Universal Protocol

### 0. Operating rules (all stages)

1. **The human is the final decision-maker.** Recommendations are not decisions.
2. **Alignment is not authorization.** A completed alignment test authorizes nothing.
3. **Read-only during alignment.** Stages 1–6 must not modify, create, delete, stage, commit, push or deploy anything.
4. **No destructive or remote action** without explicit human authorization, in this session, for that action.
5. **Approved decisions cannot be silently changed.** Any proposed change is labelled `[PROPOSAL]` and waits for human approval.
6. **Material discrepancies must be resolved before proceeding**, not carried forward silently.
7. **AI memory is supplementary, not authoritative.** Only cited documents and verified evidence count.
8. **Missing sources are reported, never invented.** State `MISSING` or `UNVERIFIED` instead of filling gaps.
9. **Every factual claim cites evidence**: document path plus section, heading or line range.
10. **Never claim to have read something** that was not provided or accessible.

### 1. Access capabilities

Different participants have different access. Do not design or assume a shared filesystem.

| Participant | Can do | Cannot do |
|---|---|---|
| Repository-capable agent (e.g. Zoo Code) | List and read files inside the configured workspace; run read-only commands such as `git status`, `git log`, `git diff` | Read outside the workspace; access another machine; act without approval for writes |
| Chat-based assistant (e.g. ChatGPT) | Analyse documents the human pastes or uploads, or that arrive through an authorized connector | Open arbitrary local paths just because they appear in this document |
| Human | Supply files, copy reports between sessions, authorize or refuse actions | — (is the decision authority) |

Evidence modes — every report must state which one applies:

| Mode | Meaning | Effect on the result |
|---|---|---|
| `FULL REPOSITORY` | Repository-capable access to the configured root | Evidence can be complete |
| `PARTIAL (human-supplied)` | Some documents supplied by the human, repository not directly readable | Unsupplied items are `UNVERIFIED` |
| `LIMITED (chat only)` | Only the primary entry document is available | Implementation-state claims are `UNVERIFIED`; overall result capped at `CONDITIONAL` |

If a chat-based assistant is used, the human must paste or attach the primary entry document and any supporting files needed. The assistant must say so rather than assume access.

### 2. Token-efficient retrieval model

Three layers. Read upward only when required.

| Layer | Contents | When |
|---|---|---|
| **Layer 1 — Essential** | Primary entry document, plus any document it explicitly says to read first | Always, first |
| **Layer 2 — Task-specific** | Architecture / design, decision records, status / progress, specifications relevant to the configured milestone and task | After Layer 1, selected by relevance to the current milestone and task |
| **Layer 3 — Evidence** | Source code, tests, logs, run artefacts, commit history | Only to verify a specific claim, check implementation status, or resolve a discrepancy |

Retrieval rules:

1. Do **not** read the whole repository.
2. Do **not** read all historical conversations, archived research or superseded plans unless the current task depends on them.
3. Read a Layer 2 document only if it can change an answer in the report.
4. Read a Layer 3 file only with a stated purpose ("verify X").
5. Stop when each report claim has evidence or is labelled `UNVERIFIED`.
6. List what was **not** read and why it was not needed.

### 3. Stages

Each stage has a goal, actions, an output, and a gate. Do not skip a gate.

#### Stage 1 — READ

- **Goal:** Establish the same starting point for every participant.
- **Do:** Read the configured primary entry document fully. Follow only explicit "read this first" pointers inside it. Do not branch out yet.
- **Output:** Short statement of what was read; evidence mode; any `MISSING` primary document (if missing, stop and report).
- **Gate:** Primary entry document read, or the session stops and reports that alignment cannot start.

#### Stage 2 — RECALL

- **Goal:** Reconstruct the project from evidence, not from memory.
- **Do:** From Layer 1 only, state: purpose, scope, current milestone, current task, stated status, stated next step, explicit prohibitions.
- **Output:** Draft notes labelled `[FACT]`, `[DECISION]` or `[UNVERIFIED]`.
- **Gate:** Notes drafted with evidence references or explicit `UNVERIFIED` marks.

#### Stage 3 — DISCOVER

- **Goal:** Fill the gaps identified in Stage 2 selectively.
- **Do:** Pick Layer 2 documents relevant to the current milestone and task. Add Layer 3 only for claims that must be verified (for example "is this feature implemented?"). If the project defines an authority order, apply it.
- **Output:** Reading list actually used, with one line per document: why it was read.
- **Gate:** Every planned report section has enough evidence, or a documented gap.

#### Stage 4 — ALIGNMENT TEST

- **Goal:** Each participant independently states its understanding in the same structure.
- **Do:**
  1. Work **independently**; do not see or request the other participant's report before finishing.
  2. Use the report template in **Output A** exactly.
  3. Label every statement `[FACT]`, `[DECISION]`, `[PROPOSAL]`, `[ASSUMPTION]`, `[QUESTION]` or `[UNVERIFIED]`.
  4. Cover all required items: purpose; architecture and responsibilities; core principles and restrictions; approved decisions; current implementation state; outstanding work; current next step; actions not yet authorized; uncertainties and conflicts.
  5. Cite path plus section for each factual or decision claim.
- **Output:** One completed Alignment Report per participant.
- **Gate:** Report complete, self-checked, and submitted to the human before comparison.

#### Stage 5 — COMPARE

- **Goal:** Expose where understanding differs.
- **Do:** The human copies one report into the other session. Each participant then fills the comparison table in **Output B** without editing its earlier report. Classify each difference as `ALIGNED`, `UNCERTAIN` or `MISALIGNED`, and assign severity.
- **Output:** Completed comparison table.
- **Gate:** Every row classified; `MISALIGNED` rows have a severity.

**Agreement is not proof.** Two participants agreeing on a wrong statement is still wrong. Authoritative documents and verified evidence remain the source of truth.

#### Stage 6 — CORRECT

- **Goal:** Resolve material discrepancies before any work.
- **Do:** For each `MISALIGNED` or high-severity `UNCERTAIN` item, investigate the authoritative source, then complete **Output C**. If authority is silent or contradictory, escalate to the human. If implementation contradicts documentation, report both; do not silently "fix" either.
- **Output:** One Discrepancy Resolution Record per open item.
- **Gate:** No unresolved high-severity discrepancy.

#### Stage 7 — PROCEED

- **Goal:** Start work only with explicit authorization.
- **Do:** State the overall result (`PASS`, `CONDITIONAL`, `FAIL`), the agreed next step, and exactly what is authorized. Wait for human confirmation.
- **Output:** Authorization statement and completion checklist (**Output E**).
- **Gate:** Human explicitly authorizes the next step, including its scope.

### 4. Status and result definitions

Per item:

| Status | Meaning | Required action |
|---|---|---|
| `ALIGNED` | Both reports state the same thing and cite compatible evidence | None |
| `UNCERTAIN` | One report is incomplete, unverified, or evidence is insufficient | Verify or mark as open |
| `MISALIGNED` | The reports state materially different things | Resolve in Stage 6 |

Overall:

| Result | Condition |
|---|---|
| `PASS` | All items `ALIGNED`; no open high-severity issue; evidence mode sufficient for the claims made |
| `CONDITIONAL` | Only low/medium discrepancies or evidence gaps remain, each recorded with an owner; no authorization-affecting disagreement |
| `FAIL` | Any high-severity `MISALIGNED` item (purpose, architecture, approved decision, authorization boundary, or next step), or the primary entry document is missing |

Severity:

- **High** — changes purpose, architecture, approvals, security boundaries, or the next step.
- **Medium** — changes status, scope detail, or milestone sequence.
- **Low** — wording or emphasis only.

### 5. Missing or conflicting sources

1. If a configured path does not exist: report `MISSING: <path>` and continue with the rest.
2. If two documents conflict: apply the configured authority order; if none is configured, report the conflict and ask the human.
3. If the code contradicts a document: report both, with evidence, and treat the document as governing until the human decides otherwise.
4. Never synthesise a plausible path, section name, or requirement.

### 6. Standard outputs

#### A. Alignment Report template

```markdown
# Alignment Report — <PROJECT_NAME>

- Participant: <tool or model name>
- Date (UTC): <YYYY-MM-DD>
- Evidence mode: FULL REPOSITORY | PARTIAL | LIMITED
- Primary entry document read: <path>
- Layer 2 documents read: <paths, or none>
- Layer 3 evidence read: <paths, or none>
- Documents unavailable: <paths or "none">
- Branch / commit (if known): <branch @ hash | UNKNOWN>

## 1. Project purpose
- [FACT] <statement> — evidence: `<path>` § <section>

## 2. Architecture and responsibilities
- [FACT] <component: responsibility and boundary> — evidence: `<path>` § <section>

## 3. Core principles and restrictions
- [DECISION] <rule> — evidence: `<path>` § <section>

## 4. Approved decisions
- [DECISION] <decision, status, date> — evidence: `<path>` § <section>

## 5. Current implementation state
- [FACT] <what exists> — evidence: `<path>` or `<test name>`
- [UNVERIFIED] <what could not be checked> — reason: <reason>

## 6. Outstanding work
- [FACT] <item> — evidence: `<path>` § <section>

## 7. Current next step
- [DECISION] <next step> — evidence: `<path>` § <section>

## 8. Actions not yet authorized
- [FACT] <action and its authorization requirement> — evidence: `<path>` § <section>

## 9. Uncertainties and conflicts
- [QUESTION] <open question>
- [ASSUMPTION] <assumption and what would confirm it>

## 10. Self-check
- [ ] Every factual or decision claim cites evidence
- [ ] Nothing was modified, staged, committed or pushed
- [ ] Unavailable sources are listed, not guessed
- [ ] Overall result stated: PASS | CONDITIONAL | FAIL
```

#### B. Cross-AI comparison table

```markdown
| # | Report item | Participant A | Participant B | Status | Severity | Note |
|---|---|---|---|---|---|---|
| 1 | Project purpose | | | ALIGNED / UNCERTAIN / MISALIGNED | High / Medium / Low | |
| 2 | Architecture and responsibilities | | | | | |
| 3 | Core principles and restrictions | | | | | |
| 4 | Approved decisions | | | | | |
| 5 | Current implementation state | | | | | |
| 6 | Outstanding work | | | | | |
| 7 | Current next step | | | | | |
| 8 | Actions not yet authorized | | | | | |
| 9 | Uncertainties and conflicts | | | | | |

Overall result: PASS | CONDITIONAL | FAIL
Reason:
```

#### C. Discrepancy Resolution Record

```markdown
## DR-<NN>

- Item:
- Participant A statement:
- Participant B statement:
- Authoritative source: `<path>` § <section>
- What the source actually says:
- Resolution:
- Type: DOCUMENTATION GAP | STALE DOCUMENT | IMPLEMENTATION GAP | MISREADING | OPEN
- Decided by: <human>
- Follow-up action (not performed until authorized):
- Status: OPEN | RESOLVED | DEFERRED
```

#### D. New Session Starter Command

```text
Read UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md and follow its steps to start the Alignment Test.

Project: <PROJECT_NAME>
Primary entry document: <PATH>
Current milestone / task: <MILESTONE / TASK>
Evidence mode available to you: <FULL REPOSITORY | PARTIAL | LIMITED>

Rules for this session:
- Do not modify, create, delete, stage, commit or push anything.
- Report your evidence mode and any MISSING documents first.
- Produce your Alignment Report before seeing any other participant's report.
```

For chat-based assistants add: "The human will paste the primary entry document. State clearly which documents you have and which you do not."

#### E. Session Initialization Completion Checklist

```markdown
- [ ] Part 1 configuration filled; no `<...>` placeholders remain
- [ ] Primary entry document read by every participant
- [ ] Evidence mode recorded by every participant
- [ ] Missing documents reported, not invented
- [ ] Layer 2 / Layer 3 documents chosen by relevance, not completeness
- [ ] Each report produced independently, before comparison
- [ ] All reports use Output A and the statement labels
- [ ] Every claim cites evidence or is marked UNVERIFIED
- [ ] Comparison table (Output B) completed for all items
- [ ] Every high-severity discrepancy resolved (Output C)
- [ ] Overall result recorded: PASS | CONDITIONAL | FAIL
- [ ] Human explicitly authorized the next step, with scope
- [ ] No file or Git state was modified during alignment
```

### 7. Prohibited behaviours

1. Reading the whole repository "to be safe".
2. Treating another AI's agreement as confirmation.
3. Presenting a proposal or assumption as an approved decision.
4. Filling a documentation gap with a plausible invention.
5. Proceeding to implementation, commits, pushes or deployments without explicit authorization.
6. Editing a document during alignment to make the reports agree.
7. Silently weakening or reinterpreting a project restriction.
8. Claiming repository access that the participant does not have.

---

## Status of this document

Draft 1 for human review. Known follow-ups before V1.0: confirm the report template covers every project type in use, confirm the `CONDITIONAL` cap rule for `LIMITED` evidence mode, and decide whether a machine-readable configuration variant is worth adding.
