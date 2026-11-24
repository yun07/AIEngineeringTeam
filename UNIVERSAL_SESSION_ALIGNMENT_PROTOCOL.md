# Universal Session Alignment Protocol

- **Version:** Draft 1 (initial draft — not yet V1.0)
- **Documentation clarity revision:** `PROPOSAL — HUMAN APPROVAL REQUIRED` (2026-11-23). This revision clarifies evidence modes, stage ownership, authorization boundaries and uncertainty labels. It is not an approved rule until the Human accepts it.
- **Generic workflow revision:** `PROPOSAL — HUMAN APPROVAL REQUIRED` (2026-11-23). Moves project-specific values out of this protocol and into the project README. The protocol remains unapproved until the Human accepts it.
- **Purpose:** Start a new AI session and confirm that it understands the project before any work begins.
- **Applies to:** any project, any repository-capable coding agent (for example Zoo Code), and any chat-based assistant (for example ChatGPT).
- **Human trigger phrase:** "Read this document and follow its steps to start the Alignment Test."

This document has two parts:

1. **Part 1 — Project Configuration Schema.** A generic list of configuration fields. Values live in the project README.
2. **Part 2 — Universal Protocol.** The generic alignment and collaboration process. It contains no project-specific values.

If a rule here conflicts with the project's own governing documents, the project documents win for project facts, and this protocol wins only for the *process* of alignment. Report the conflict; do not silently resolve it.

---

## Part 1 — Project Configuration Schema

This protocol stores no project values. The project README must define them once, in a Project Configuration section. Do not duplicate project values here.

| Field | Purpose |
|---|---|
| Project name | Human-readable identity of the project |
| Project root | Repository or workspace root |
| Primary entry document | The authoritative project document to read during Stage 1 |
| Working-rules entry point | Agent instruction file, normally `AGENTS.md` |
| Architecture / design documents | Design sources for Layer 2 |
| Decision records | Approved decisions and their authority order |
| Status / progress documents | Current status and milestone records |
| Technical specifications | Specifications relevant to the task |
| Tests / evidence / logs | Where verification evidence is stored |
| Git repository and baseline branch | Remote or local repository and the committed review baseline |
| Current milestone / phase | Declared project position, not verified status |
| Current task | Declared task, not verified status |
| Configured communication language | Language the Human wants participants to use |
| Preflight command | The single command used before commit |
| Project-specific restrictions | Mandatory project constraints |
| Documentation index and reading order | Where each document type is described |
| Project limitations | Features not implemented or not approved |

Resolution rules:

1. Read the project README Project Configuration section before Stage 1.
2. Record the configuration source as `README` or `HUMAN-SUPPLIED`.
3. A missing field is reported as `NOT CONFIGURED`; never invent a value or path.
4. If the primary entry document is missing, stop and report that alignment cannot start.
5. Project-specific restrictions are mandatory constraints at every stage, including read-only stages.
6. Configuration may be supplied per session by the Human when the README cannot be read. State that source.
7. Changing project configuration is a project document change. It requires the project's document-change process and Human approval; it is not part of an alignment session.

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
11. **Communication language.** All conversational responses, status updates, questions, explanations, handoffs and reports directed to the Human use Cantonese in Traditional Chinese. English technical terms, code, identifiers, file names, commands and API names may remain in English. This rule does not require translating source code, technical specifications or project documents.

### 0.1 Authorization boundary (independent grants)

Alignment is not authorization, and each grant below is separate. Approving one grant never approves another.

| Grant | Covers | Does not cover |
|---|---|---|
| Document read | Reading the configured documents and evidence sources | Any write |
| Document modify | Editing the named documents on an approved review branch | Code, configuration or Git history |
| Code modify | Editing source, tests or configuration files | Running the code |
| Test / execute | Running tests, commands or generated code, within a stated scope | Committing or merging results |
| Git stage / commit | Creating commits on a named review branch | Pushing |
| Git push | Publishing a named review branch to the remote | Merging |
| Git merge | Merging an approved change into a protected branch | The next stage of project work |

Rules:

1. The Human states the grant, its scope and its duration. Ambiguous approval is treated as no approval.
2. Stages 1–6 operate under **document read** only. Reading a document never authorises editing it.
3. A review-package instruction authorises only the files it names, on a review branch or worktree. It does not authorise commit, push or merge unless those are named.
4. Approval to merge a document change does not authorise the next stage of work.

### 0.2 Statement and uncertainty labels

| Label | Meaning | May it be treated as an approved rule? |
|---|---|---|
| `[FACT]` | Verified from a cited document or command output | No; it is evidence, not a decision |
| `[DECISION]` | An approved decision with a cited approval record | Yes, within its recorded scope |
| `[INFERENCE]` | A conclusion the participant derived from evidence | No; it must be confirmed |
| `[ASSUMPTION]` | An unstated premise the participant is using | No |
| `[UNVERIFIED]` | A claim that could not be checked | No |
| `[PROPOSAL]` | A recommended change or rule awaiting Human approval | No |
| `[QUESTION]` | An open question for the Human | No |

Rules:

1. Only `[DECISION]` with a cited approval record counts as an approved rule.
2. An `[INFERENCE]` must name the evidence it rests on and what would confirm it.
3. An AI must not resolve a policy conflict that requires Human authority. It records the conflict and escalates it.

### 0.3 Session bootstrap, workflow modes and document discovery

Bootstrap order for every new session:

1. Read `AGENTS.md` first. When the Human supplies only the `AGENTS.md` link, that link is the session entry point.
2. Follow `AGENTS.md` to read this protocol's Part 1 schema and bootstrap instructions.
3. Read the project `README.md` for Project Configuration and project context.
4. Read the primary entry document named by the README Project Configuration in full.
5. Select Layer 2 documents by relevance to the current task.

If `AGENTS.md` or `README.md` is unavailable, mark it `MISSING` and continue with the available sources. Never invent their content.

This mandatory bootstrap order takes precedence over the general task-specific retrieval order in `AGENTS.md`. After bootstrap, apply the token-efficient retrieval rules in `AGENTS.md` and §2 of this protocol; ordinary tasks must not read the entire repository.

Document discovery:

1. When a participant has repository access, whether `FULL REPOSITORY` or `REMOTE DOCUMENT ACCESS`, it locates the configured documents and the task-relevant documents itself. The Human is not required to re-paste documents that are already accessible.
2. Discovery stays bounded by §2: do not read the whole repository, and read only documents that can change an answer in the report.
3. A participant with only human-supplied documents must say so and request exactly what it needs.
4. A search that uses repository access must state which branch or commit it read, and whether the local working tree or only the remote was visible.

Workflow modes:

| Mode | Goal | Typical actions | Required authorization |
|---|---|---|---|
| Alignment | Establish a shared understanding | Stages 1–7, read-only | Document read |
| Documentation | Amend named documents | Review branch or worktree, edit only named files, run checks, commit and push the review branch when granted | Document modify, plus commit and push grants |
| Development | Change code | Edit source and tests, run tests, commit and push a review branch | Code modify, test/execute, and commit/push grants; merge is separate |

Rules:

1. A session states its mode before acting.
2. Entering Documentation or Development mode is never inherited from Alignment.
3. Merge is always a separate grant and is never implied by commit or push.
4. Operational checks, the evidence package and the review handoff for Documentation and Development are defined once in `AGENTS.md` §Development Workflow and the project README's configured preflight command; this protocol does not duplicate them.

### 1. Access capabilities

Different participants have different access. Do not design or assume a shared filesystem.

| Participant | Can do | Cannot do |
|---|---|---|
| Repository-capable agent (e.g. Zoo Code) | List and read files inside the configured workspace; run read-only commands such as `git status`, `git log`, `git diff` | Read outside the workspace; access another machine; act without approval for writes |
| Chat-based assistant (e.g. ChatGPT) | Analyse documents the Human pastes or uploads; read documents published on the public repository or supplied through an authorised connector, including a pushed review branch and its diff | Read the local working tree or uncommitted changes; open arbitrary local paths just because they appear in this document |
| Human | Supply files or access, authorize or refuse actions; act as the exchange channel when no shared remote is available | — (is the decision authority) |

Evidence modes — every report must state which one applies:

| Mode | Meaning | Effect on the result |
|---|---|---|
| `FULL REPOSITORY` | Repository-capable access to the configured root, including the local working tree and read-only Git commands | Evidence can be complete |
| `REMOTE DOCUMENT ACCESS` | Access only to documents published on the remote repository (for example GitHub web or API), not to the local working tree | Remote committed content may be verified; local uncommitted changes, local Git state and execution evidence are `UNVERIFIED`; overall result capped at `CONDITIONAL` |
| `PARTIAL (human-supplied)` | Some documents supplied by the human, repository not directly readable | Unsupplied items are `UNVERIFIED` |
| `LIMITED (chat only)` | Only the primary entry document is available | Implementation-state claims are `UNVERIFIED`; overall result capped at `CONDITIONAL` |

Evidence sources are not interchangeable. Every report must say which sources it actually used:

| Source | What it can prove | What it cannot prove |
|---|---|---|
| Public GitHub documents | The committed content of the remote branch | The local working tree, uncommitted changes, or local Git state |
| Local committed working tree | The committed content of the local branch | Uncommitted edits, other machines, other branches |
| Uncommitted working-tree changes | Ungoverned local edits | That the change was approved, committed or published |
| Git status and history | Branch, HEAD, remotes, commit graph, diff of tracked files | Execution results or test outcomes |
| Execution evidence (tests, runs, logs) | Behaviour actually observed at that time | That the behaviour persists after later changes |

Reading public documents never equals a full repository check. Reading a document never equals verifying the implementation state.

When a participant has `REMOTE DOCUMENT ACCESS` to the public repository or an authorised connector, it reads the accessible documents, pushed review branches and diffs directly. It does not ask the Human to paste or attach documents that are already accessible. The Human supplies files only when the required source is genuinely inaccessible. The participant must state which sources it has and which it does not.

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
- **Inputs:** The configured primary entry document, and the configuration source (`FILE` or `HUMAN-SUPPLIED`).
- **Owner:** Every participant performs this stage independently. The Human supplies any missing document.
- **Do:** Read the configured primary entry document fully. Follow only explicit "read this first" pointers inside it. Do not branch out yet.
- **Output:** Short statement of what was read; evidence mode and configuration source; any `MISSING` primary document (if missing, stop and report).
- **Gate:** Primary entry document read, or the session stops and reports that alignment cannot start.

#### Stage 2 — RECALL

- **Goal:** Reconstruct the project from evidence, not from memory.
- **Inputs:** Layer 1 only.
- **Owner:** Each participant independently; the Human does not pre-answer.
- **Do:** From Layer 1 only, state: purpose, scope, current milestone, current task, stated status, stated next step, explicit prohibitions.
- **Output:** Draft notes labelled `[FACT]`, `[DECISION]`, `[INFERENCE]` or `[UNVERIFIED]`, each with a citation.
- **Gate:** Notes drafted with evidence references or explicit `UNVERIFIED` marks.

#### Stage 3 — DISCOVER

- **Goal:** Fill the gaps identified in Stage 2 selectively.
- **Inputs:** Stage 2 notes and the configured authority order.
- **Owner:** Each participant selects its own Layer 2 and Layer 3 sources and records why.
- **Do:** Pick Layer 2 documents relevant to the current milestone and task. Add Layer 3 only for claims that must be verified (for example "is this feature implemented?"). If the project defines an authority order, apply it and cite it when documents conflict.
- **Output:** Reading list actually used, with one line per document: why it was read, and which claim it supports.
- **Gate:** Every planned report section has enough evidence, or a documented gap.

#### Stage 4 — ALIGNMENT TEST

- **Goal:** Each participant independently states its understanding in the same structure.
- **Inputs:** The participant's own Stage 1–3 evidence only.
- **Owner:** Each participant writes its own **Output A**; the Human never merges the two reports at this stage. If the Human authorises a shared review path, a report may be published there; publishing a report never authorises editing project documents.
- **Do:**
  1. Work **independently**; do not see or request the other participant's report before finishing.
  2. Use the report template in **Output A** exactly.
  3. Label every statement `[FACT]`, `[DECISION]`, `[INFERENCE]`, `[PROPOSAL]`, `[ASSUMPTION]`, `[QUESTION]` or `[UNVERIFIED]`.
  4. Cover all required items: purpose; architecture and responsibilities; core principles and restrictions; approved decisions; current implementation state; outstanding work; current next step; actions not yet authorized; uncertainties and conflicts.
  5. Cite path plus section for each factual or decision claim. Mark AI-derived conclusions as `[INFERENCE]`, not `[FACT]` or `[DECISION]`.
- **Output:** One completed Alignment Report per participant.
- **Gate:** Report complete, self-checked, and submitted to the human before comparison.

#### Stage 5 — COMPARE

- **Goal:** Expose where understanding differs.
- **Inputs:** Both completed Output A reports. They are either supplied by the Human, or, when both participants have authorised access to the same remote and a shared review path exists, read directly from that path.
- **Owner:** Each participant fills **Output B** independently, without editing its earlier Output A. Where remote access exists, the Human does not need to copy and paste the reports; where it does not, the Human is the exchange channel.
- **Do:**
  1. Compare item by item against the same report-item list.
  2. Classify each difference as `ALIGNED`, `UNCERTAIN` or `MISALIGNED`, and assign severity.
  3. Record whether the two reports used different evidence modes or evidence sources, and treat unsupported agreement as `UNCERTAIN`, not `ALIGNED`.
  4. Do not edit Output A to make the reports agree.
- **Output:** One completed comparison table per participant.
- **Gate:** Every row classified; `MISALIGNED` rows have a severity.

**Agreement is not proof.** Two participants agreeing on a wrong statement is still wrong. Authoritative documents and verified evidence remain the source of truth.

#### Stage 6 — CORRECT

- **Goal:** Resolve material discrepancies before any work.
- **Inputs:** Stage 5 comparison tables, the authoritative documents, and read-only evidence.
- **Owner:** The designated Worker drafts the records; the Reviewer inspects them independently; the Human decides anything that requires authority. When the Worker pushes a review branch, the Reviewer reads the actual branch files and diff on the remote; a Worker summary is not evidence.
- **Do:**
  1. For each `MISALIGNED` or high-severity `UNCERTAIN` item, investigate the authoritative source, then complete **Output C**.
  2. If the evidence is insufficient, record the gap and mark it `UNVERIFIED`; do not fill it with an inference.
  3. If authority is silent or contradictory, escalate to the Human and leave the record `OPEN`.
  4. If implementation contradicts documentation, report both; do not silently "fix" either.
  5. Do not treat a resolution record as permission to edit files, code or Git state.
- **Output:** One Discrepancy Resolution Record per open item.
- **Gate:** No unresolved high-severity discrepancy.

#### Stage 7 — PROCEED

- **Goal:** Start work only with explicit authorization.
- **Inputs:** The completed records and the Human's decision.
- **Owner:** The Human authorises; the participant records the authorisation verbatim. A written record is placed only in a file and path the Human has authorised.
- **Do:**
  1. State the overall result (`PASS`, `CONDITIONAL`, `FAIL`), the agreed next step, and exactly what is authorised.
  2. Name the grant from the authorization boundary (document modify, code modify, test/execute, commit, push, merge) and its scope.
  3. Wait for explicit Human confirmation.
  4. Where a review branch is pushed, state its name and commit hash so the Reviewer can inspect the real branch and diff rather than a summary.
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
- Evidence mode: FULL REPOSITORY | REMOTE DOCUMENT ACCESS | PARTIAL | LIMITED
- Configuration source: FILE | HUMAN-SUPPLIED
- Evidence sources actually used: <public remote / local committed tree / uncommitted changes / git state / execution evidence>
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
Read AGENTS.md first, then follow its Mandatory Session Bootstrap: read UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md and follow its steps to start the Alignment Test.

Project: <PROJECT_NAME>
Primary entry document: <PATH>
Current milestone / task: <MILESTONE / TASK>
Evidence mode available to you: <FULL REPOSITORY | PARTIAL | LIMITED>

Rules for this session:
- Do not modify, create, delete, stage, commit or push anything.
- Report your evidence mode and any MISSING documents first.
- Produce your Alignment Report before seeing any other participant's report.
```

For chat-based assistants with REMOTE DOCUMENT ACCESS: read the primary entry document directly from the configured public repository. Ask the Human to paste or upload it only when the required source is genuinely inaccessible.

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

Draft 1 for human review. The 2026-11-23 documentation-clarity revision is a `PROPOSAL — HUMAN APPROVAL REQUIRED`; it adds the `REMOTE DOCUMENT ACCESS` mode, the authorization boundary, the statement-label table, stage ownership and the per-session configuration rule. The 2026-11-23 generic-workflow revision is also a proposal: Part 1 becomes a schema and project values move to the README. Neither revision becomes a rule until the Human approves it.

Known follow-ups before V1.0: confirm the report template covers every project type in use, confirm the `CONDITIONAL` cap rule for `LIMITED` and `REMOTE DOCUMENT ACCESS` evidence modes, and decide whether a machine-readable configuration variant is worth adding.
