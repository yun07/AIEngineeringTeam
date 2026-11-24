# AGENTS.md

This file defines generic behaviour for an AI coding agent working with a Human and an independent reviewing assistant. It is reusable across projects. Project-specific values, paths, status and decisions belong in the project `README.md`.

## Communication Language

1. Communicate with the Human in the language configured by the project README (Project Configuration → configured language).
2. If no language is configured, ask the Human; do not assume a default.
3. English technical terms, code, identifiers, file names, commands and API names may remain in English.
4. Do not translate source code, technical specifications or project documents unless the Human asks.

## Mandatory Session Bootstrap

1. When the Human supplies this `AGENTS.md` link as the session entry point, treat that link as the project entry point and start the bootstrap and alignment flow.
2. Locate `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md` from the same repository and branch context.
3. Read in this order:
   - `AGENTS.md`
   - `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md` (configuration schema and bootstrap instructions)
   - the project `README.md` (Project Configuration and project context)
   - the primary entry document named by the README configuration
   - relevant Layer 2 documents selected for the current task
4. Read accessible repository documents directly. Do not ask the Human to paste or upload a document that is already accessible.
5. If a required document cannot be accessed, name the exact missing document and the access limitation. Never skip it silently or assume its contents.
6. After bootstrap, report a concise alignment status covering:
   - repository, branch and commit used as evidence
   - documents read and any missing documents
   - project, milestone and task as declared by the README
   - confirmed decisions and unresolved Human decisions
   - work authorization status
7. Bootstrap and alignment are read-only. They do not authorize implementation, code execution, file modification, commit, merge or deployment.
8. Use the communication language configured by the README.

## Token-efficient Context Management

1. After bootstrap, start a new task by reading the code, tests and configuration directly relevant to that task, not every project document.
2. Keep this file generic; project specifics belong in the README and project documents.
3. Read project documents by relevance, following the document index in the README.
4. Do not re-read a document that is already in context and has not changed.
5. Do not read unrelated files just to become familiar with the whole project.
6. If a real documentation conflict affects the task, identify the conflicting files and sections; do not re-read every document.
7. Do not repeat a full project summary on every task.
8. Finish a task with a concise report in the configured language: what changed, what tests or checks ran, the results, and any unresolved issues.
9. Read archived research, superseded plans or historical decision records only when the task depends on them or the Human asks.

## Development Workflow

Project governance and authority live in the project's own documents; the README states where they are. This section defines the generic operating rules.

### 1. Change classes and authorization

| Class | Examples | Review branch | Commit / push | Merge |
|---|---|---|---|---|
| Documentation | README, protocol, agent instructions, plans | Required | Allowed after required checks, unless the project says otherwise | Human approval only |
| Code / milestone | Source, tests, configuration | Required | Each step requires explicit Human approval unless the project grants a different grant | Human approval only |

- Approval of one class or step never implies approval of another: document edit, code edit, test execution, commit, push and merge are separate grants.
- Never edit a protected branch directly, force-push, `reset --hard`, or clean unapproved work.
- Never add `.env`, API keys, passwords or other secrets to Git.

### 2. Branch and scope

1. Create the review branch from the latest committed baseline named by the project README.
2. One branch covers one scope; commits contain only files in that scope.
3. Preserve unrelated uncommitted work in the working tree. Do not stage, overwrite, reset or sweep it into the change.
4. Once a review branch is under review, do not rewrite its history; add a corrective commit instead.

### 3. Preflight validation

The README defines the project's preflight command. Run that single command before commit.

- Preflight is a manual validation step run by the Worker. It is not a Git hook. A hook or CI job exists only if the project explicitly says it is installed.
- Preflight must report PASS or FAIL and name the failing item. It must not silently pass when a check cannot run.
- For documentation changes, at minimum check the working tree, `git diff --check`, the change scope relative to the baseline, and document consistency.
- For code changes, also run the project's test command and report the actual command, exit code and pass/fail count. Do not report "tests pass" without evidence.
- UI work must include a screenshot or recording; headless work does not.

### 4. Evidence package

Reviews accept verifiable evidence only:

- the actual Git diff (the reviewer reads the branch or patch directly)
- the preflight command and its actual output
- test results, or screenshot/log evidence for UI work
- a list of unresolved items

The handoff reports the branch, commit hash, changed files, checks and open issues. Do not re-paste a full diff or write a long self-assessment.

### 5. Independent review

- The reviewer reads the actual branch, diff and test evidence. The Worker's summary is not evidence.
- The reviewer checks scope, contradictions, whether unapproved proposals were presented as approved rules, and whether tests and evidence match the claims.
- The Worker fixes issues with additional commits. The reviewer does not execute merges.

### 6. Human approval

- The Human is the sole merge approver. Merge only after explicit approval.
- Merge approval covers that merge only. It does not authorize the next milestone, implementation or any follow-up work.
- Human approval is never replaced by automation, CI or a successful review.

### 7. Efficiency

- Do not re-read unchanged documents or re-paste the same diff or report.
- Do not create duplicate branches or commits for the same scope.
- Do not retry or regenerate the same report without new evidence. Report the cause and the next step instead.
- Tool-orchestration problems, such as repeated report generation or wasted context, are tooling problems, not evidence of a defect in the project's engine.

## Document Roles

The project README owns the documentation index and reading order. Use it to identify:

- the primary entry document
- architecture and design documents
- decision records and authority order
- status and progress documents
- specifications, evidence and archived material

Do not duplicate the project document list in this generic file.
