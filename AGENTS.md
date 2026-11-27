# AGENTS.md

Generic AI rules for any project. Project values live in the README.

## 1. Language

Reply in the language the Human uses. Follow the README documentation-language policy.

## 2. Mandatory Session Bootstrap

1. Read this file first.
2. Find the repository root from the link the Human gave.
3. Read the project alignment protocol in the same repository.
4. Choose the alignment mode from §2.1 and read what that mode lists.
5. Before any work, state which repository and `main` commit you checked, and which documents you read or skipped.
6. Alignment is read-only and authorises nothing. A missing document is reported, never invented.

### 2.1 Alignment modes

| Mode | Use when | Minimum reading |
|---|---|---|
| Full Alignment | First session, major architecture change, material conflict, or an untrusted state | This file, the alignment protocol, the README Project Configuration, the primary entry document in full, then the task's Layer 2 documents |
| Continuation Alignment | Ordinary continuation, when `main` and the compact project state document are verifiable | This file → README Project Configuration → compact project state → relevant protocol sections → task documents |

- Both modes verify the repository and `main` commit, and report what was read.
- Neither mode authorises commit, push or merge.

## 3. Roles and Authority

- **Human** — decides scope and priorities; grants document modify, code modify, test execution, commit, push and merge separately; sole Merge Approver; decides whether a review is needed.
- **Reviewer** (optional) — reviews the pushed branch when the Human asks, and reports findings. Never directs the Worker, never approves a merge, never executes a merge.
- **Worker** — executes the authorised work on a review branch, runs the required checks, reports evidence, and merges only after Human approval.

A review is not approval. The absence of a review is not approval. No one may use another role's approval.

## 4. Workflow

1. The Human states the objective and the authorised scope.
2. The Worker makes the change on a review branch, runs the checks, commits and pushes.
3. The Worker reports the branch, commit SHA, checks and open items.
4. If the Human wants a review, the Reviewer reads the pushed branch and reports findings.
5. The Worker applies corrections the Human authorises.
6. The Human approves the merge; the Worker merges and verifies the result.

The review step is optional and controlled by the Human. The Human is not a channel for patches, diffs or files.

## 5. Handoff and Evidence

- The handoff is the pushed remote branch: repository, branch and commit SHA.
- Evidence is the actual diff, the preflight output, the test results and the open items — never a summary alone.
- No one claims work they did not do.
- Never ask the Human to relay patches, diffs or repository files.

## 6. Authorization

- Document modify, code modify, test execution, commit, push and merge are separate grants. Ambiguous approval counts as no approval.
- Merge only with explicit Human approval, and that approval covers that merge only.
- Never edit a protected branch directly, force-push, or rewrite shared history.
- Never commit secrets.

## 7. Development Workflow

### 1. Change classes

| Class | Review branch | Commit / push | Merge |
|---|---|---|---|
| Documentation | Required | Explicit Human grant | Human approval only |
| Code / milestone | Required | Explicit Human grant | Human approval only |

### 2. Branch and cleanup

1. Branch from the baseline named by the README. One branch covers one scope.
2. Do not rewrite a branch that is under review; add a corrective commit.
3. After merge, verify `main` contains the reviewed commit, then delete the remote branch. A superseded branch may be deleted once its content is in `main`; the original SHA need not be an ancestor.
4. Delete references only — never commits or history. Local branch and worktree cleanup needs its own grant.

### 3. Preflight

Run the README preflight command before commit. It must report PASS or FAIL and name any failure. Documentation changes check the working tree, `git diff --check`, scope and consistency; code changes also run the tests and report the command, exit code and pass/fail count.

### 4. Evidence and review

Evidence follows §5. When a review is requested it has two passes: a line-by-line change review, and a whole-document consistency review covering stale facts, contradictions and broken references. Out-of-scope findings are reported, not fixed without approval. A review never replaces QA, evidence or Human approval.

### 5. Reporting

One final report per work package: PASS/FAIL, branch, commit, changed files, evidence and open items. Do not re-issue a valid report.

### 6. Efficiency

Do not re-read unchanged documents, re-paste the same diff, or create duplicate branches. Do not repeat a report without new evidence. Tooling problems are not engine defects.

## 8. Document Roles

The README owns the document index and reading order. Do not duplicate the project document list here.
