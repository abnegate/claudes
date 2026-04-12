---
description: Fix failing CI checks on a pull request
argument-hint: <url> [comments=true|false] [checks=true|false]
---

# Fix Failing PR Checks

Fix failing CI checks on a GitHub pull request, iterating until all checks pass. Uses parallel agents extensively to analyze failures and apply fixes simultaneously.

## Arguments

- `$ARGUMENTS` - PR URL or number (e.g., `https://github.com/owner/repo/pull/123` or `123`)
- `checks` (optional) - Whether to analyze and fix failing checks (default: true)
- `comments` (optional) - Whether to address comments in the PR (default: false)

## Parsing Arguments

Extract from `$ARGUMENTS`:
- **PR reference** — the URL or number (first positional value)
- **checks** — `checks=true` or `checks=false` (default: `true`)
- **comments** — `comments=true` or `comments=false` (default: `false`)

Example: `/pr-fix https://github.com/owner/repo/pull/123 comments=true checks=false`

## Workflow

### 1. Checkout the PR

```bash
gh pr checkout <pr-ref>
```

### 2. Gather PR Context (Parallel)

Launch these agents in parallel to collect all PR information simultaneously:

**Agent 1 — PR Details:**
```bash
gh pr view <pr-ref> --json number,headRefName,baseRefName,statusCheckRollup,url,title,body
```

**Agent 2 — Check Status:**
```bash
gh pr checks <pr-ref>
```

**Agent 3 — PR Diff:**
```bash
gh pr diff <pr-ref>
```

**Agent 4 — Review Comments (when comments=true):**
```bash
gh pr view <pr-ref> --json reviews,comments
gh api repos/{owner}/{repo}/pulls/{number}/comments
```

### 3. Fix Failing Checks (when checks=true)

#### 3a. Parallel Failure Analysis

For each failing check, launch a separate analysis agent in parallel:

**Agent per failing check:**
```bash
gh run view <run-id> --log-failed
```

Each agent:
1. Downloads and reads the failure logs for its check
2. Identifies the root cause
3. Determines which files need changes
4. Outputs a structured diagnosis: `{check_name, root_cause, files_to_change, proposed_fix}`

#### 3b. Parallel Fixes (Consolidation Pattern)

Partition diagnosed failures into groups by root cause. Use the **consolidation pattern** — launch each fix group as a parallel worktree-isolated agent (`isolation: "worktree"`). Agents can freely edit overlapping files; the consolidator handles merges.

**Per worktree agent:**
1. Apply the proposed fix from the analysis
2. Verify the fix makes sense in context (read surrounding code)
3. Make minimal, focused changes
4. Commit before finishing

**After all worktree agents complete**, launch the **consolidator** agent (`subagent_type: "consolidator"`) to merge all branches.

#### 3c. Commit and Push

After all fix agents complete, delegate to the `skills:commit` command with a descriptive message, then push:

```
Skill(skill="skills:commit", args="fix: <description of what was fixed>")
```

```bash
git push
```

#### 3d. Monitor Checks

```bash
sleep 10
gh pr checks <pr-ref> --watch
```

If checks still fail, repeat from 3a (up to 5 attempts).

### 4. Address PR Comments (when comments=true)

#### 4a. Parallel Comment Analysis

Group review comments by file. Launch a separate agent per file (or per independent comment group) in parallel:

**Agent per file/group:**
1. Read the referenced code and the reviewer's feedback
2. Determine what change is needed
3. Output a structured plan: `{file, line, comment_summary, proposed_change}`

#### 4b. Parallel Comment Fixes (Consolidation Pattern)

Launch each comment group as a parallel worktree-isolated agent (`isolation: "worktree"`). Agents can freely edit overlapping files; the consolidator handles merges.

**Per worktree agent:**
1. Apply the requested change (or closest reasonable interpretation)
2. Respect the reviewer's intent — don't make superficial changes
3. Verify the fix is consistent with surrounding code
4. Commit before finishing

**After all worktree agents complete**, launch the **consolidator** agent (`subagent_type: "consolidator"`) to merge all branches.

#### 4c. Commit and Push

Delegate to the `skills:commit` command, then push:

```
Skill(skill="skills:commit", args="fix: address review comments")
```

```bash
git push
```

#### 4d. Monitor Checks

```bash
sleep 10
gh pr checks <pr-ref> --watch
```

If fixing comments introduces new check failures, loop back to step 3.

### 5. Iterate If Needed

Continue iterating until:
- All enabled checks pass
- All comments are addressed (if comments=true)
- Or you have exhausted reasonable attempts (max 5 iterations — then escalate to user)

## Important Notes

- Read failure logs carefully — the error message usually contains the fix
- Common check failures:
  - **tests**: Check test output, fix code or test
  - **build**: Check compilation errors
- When addressing comments, respect the reviewer's intent — don't just make superficial changes
- After each fix, commit with: `fix: <description of what was fixed>`

## Test Failure Policy

**IMPORTANT:** There is no such thing as a "pre-existing" test failure. If any test fails - whether it appears related to the PR changes or not - you must fix it. The task always completes with completely passing tests. Do not dismiss failures as "unrelated to this PR."

## Exit Conditions

Stop iterating when:
- All checks pass (required - no exceptions)
- 5 fix attempts have been made without resolution (escalate to user, do not give up)
