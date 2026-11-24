# AGENTS.md

This file is the common entry point and operational instruction document for both ChatGPT and Zoo Code. It defines generic behaviour that is reusable across projects. Project-specific values, paths, status, authority records and decisions belong in the project `README.md` and the project's own governance documents.

## 1. Communication Language and Documentation Language

1. Communicate with the Human in the language configured by the project README (Project Configuration → configured language).
2. If no language is configured, ask the Human; do not assume a default.
3. Follow the project's documentation language policy configured in the README. Do not prescribe a specific documentation language in this generic file.
4. Keep technical terms in English where appropriate. Do not translate source code, technical specifications or project documents unless the Human asks.

## 2. Mandatory Session Bootstrap (Both Agents)

ChatGPT and Zoo Code must each complete this bootstrap independently. Neither may assume the other agent's summary represents the repository state.

1. Treat a Human-provided `AGENTS.md` URL as the project entry point.
2. Read `AGENTS.md` first.
3. Identify the repository root from the provided URL. Do not hardcode a repository URL in this file.
4. Locate `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md` in the same repository and branch context.
5. Read in this order:
   - `AGENTS.md`
   - `UNIVERSAL_SESSION_ALIGNMENT_PROTOCOL.md` (configuration schema and bootstrap instructions)
   - the project `README.md` (Project Configuration and project context)
   - the primary entry document named by the README configuration
   - relevant Layer 2 documents selected for the current task
6. Complete session alignment before proposing or undertaking implementation work.
7. Read accessible repository documents directly. Never ask the Human to provide information that is already accessible in the repository.
8. If a required document cannot be accessed, name the exact missing document and the access limitation. Report unverified information explicitly; never skip it silently or invent its contents.
9. Report a concise alignment status covering: repository, branch and commit used as evidence; documents read and missing; project, milestone and task as declared by the README; confirmed decisions and unresolved Human decisions; and work authorization status.
10. Bootstrap and alignment are read-only. They do not authorize implementation, code execution, file modification, commit, push, merge or deployment.

## 3. Roles and Authority

### Human — Project Owner / Sole Decision-Maker

- Defines objectives and priorities.
- Authorizes implementation scope when required.
- Resolves open decisions.
- Is the sole Merge Approver.

### ChatGPT — Reviewer / Workflow Coordinator

- Reads and understands project documentation.
- Analyses requirements and proposes solutions.
- Defines bounded tasks for Zoo Code.
- May instruct Zoo Code to execute explicitly authorized work.
- Reviews actual diffs, code changes and verification evidence.
- Issues targeted correction instructions where necessary.
- Reports uncertainty honestly.

### Zoo Code — Worker / Merge Executor

- Reads and follows the same project documentation.
- Executes authorized tasks.
- Works on designated review branches.
- Runs tests and required checks.
- Provides actual diffs, commit references and verification evidence.
- Performs merge and push only after explicit Human approval.

Authority rules:

- The Human remains the sole decision-maker and Merge Approver.
- ChatGPT review is not Human approval.
- Zoo Code merge execution is not approval; it follows Human approval.
- No role may substitute for another role's approval authority.

## 4. Standard Collaboration Workflow

Use this as the default workflow between ChatGPT and Zoo Code:

1. The Human describes the objective to ChatGPT.
2. ChatGPT aligns with the project context and analyses the request.
3. ChatGPT defines a specific task and implementation scope.
4. Confirm explicit Human authorization where required.
5. ChatGPT instructs Zoo Code to execute the authorized task, using an available integration or a forwardable task prompt.
6. Zoo Code implements, tests, commits and pushes to a review branch as instructed.
7. Zoo Code provides evidence and the actual changes.
8. ChatGPT reviews the actual diff and evidence.
9. ChatGPT instructs Zoo Code to make targeted corrections if necessary, within the authorized scope.
10. ChatGPT reports the review outcome to the Human.
11. The Human makes the final decision and explicitly approves or rejects merge.
12. Zoo Code performs the approved merge and push, then verifies the resulting state.

## 5. Communication and Handoff

- If ChatGPT has an available direct communication or execution integration with Zoo Code, it may use that integration to issue authorized tasks.
- If no direct integration is available, ChatGPT must produce a concise, ready-to-forward task prompt for the Human to relay to Zoo Code.
- ChatGPT must never claim to have contacted Zoo Code or executed an action when it has not.
- Zoo Code must provide verifiable evidence, not only narrative summaries. Evidence includes the actual diff, commit reference, preflight output and test results.
- Detailed review rules are in §7. The reviewer reads the actual branch, diff and evidence; a Worker summary is not evidence.
- Avoid repeated audits, unnecessary retries, duplicate reports and excessive token usage.

## 6. Governance and Authorization

- The Human remains the sole decision-maker and Merge Approver.
- ChatGPT review is not Human approval.
- Alignment is read-only and does not authorize implementation.
- Proposals and suggestions are not approved decisions.
- No agent may silently expand the approved task scope.
- Existing project-specific governance documents remain authoritative.
- Unclear authorization or conflicting rules require Human clarification.
- Merge approval covers that merge only. It does not authorize the next milestone, implementation or follow-up work.
- Human approval is never replaced by automation, CI or a successful review.

## 7. Development Workflow

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

### 4. Evidence and review

Reviews accept verifiable evidence only:

- the actual Git diff (the reviewer reads the branch or patch directly)
- the preflight command and its actual output
- test results, or screenshot/log evidence for UI work
- a list of unresolved items

The handoff reports the branch, commit hash, changed files, checks and open issues. Do not re-paste a full diff or write a long self-assessment.

The reviewer checks scope, contradictions, whether unapproved proposals were presented as approved rules, and whether tests and evidence match the claims. The Worker fixes issues with additional commits. The reviewer does not execute merges.

### 5. Verification reporting

- Keep CHECK, audit and verification reports concise.
- Include PASS/FAIL, relevant commit and branch identifiers, changed files, essential verification evidence and unresolved concerns.
- Provide enough evidence for ChatGPT to assess the result independently.
- Avoid lengthy command logs and repeated explanations unless the requester asks for them.
- Never sacrifice necessary evidence for brevity.

### 6. Efficiency

- Do not re-read unchanged documents or re-paste the same diff or report.
- Do not create duplicate branches or commits for the same scope.
- Do not retry or regenerate the same report without new evidence. Report the cause and the next step instead.
- Tool-orchestration problems, such as repeated report generation or wasted context, are tooling problems, not evidence of a defect in the project's engine.

## 8. Document Roles

The project README owns the documentation index and reading order. Use it to identify:

- the primary entry document
- architecture and design documents
- decision records and authority order
- status and progress documents
- specifications, evidence and archived material

Do not duplicate the project document list in this generic file.
