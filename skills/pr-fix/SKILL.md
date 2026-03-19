---
name: pr-fix
description: Fix failing CI checks on a pull request
argument-hint: <url> [comments=true|false] [checks=true|false]
disable-model-invocation: false
---

# Fix Failing PR Checks

Fix failing CI checks on a GitHub pull request, iterating until all checks pass.

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

### 2. Get PR Information

```bash
# Get PR details
gh pr view <pr-ref> --json number,headRefName,statusCheckRollup,url
```

### 3. Fix Failing Checks (when checks=true)

#### 3a. Identify Failures

```bash
gh pr checks <pr-ref>
```

#### 3b. Analyze Each Failure

```bash
# Get check run details and logs
gh run view <run-id> --log-failed
```

#### 3c. Fix, Commit, Push, and Wait

- Identify the root cause from the logs
- Make necessary code changes
- Commit with: `fix: <description of what was fixed>`
- Push and wait for CI:

```bash
git push
sleep 10
gh pr checks <pr-ref> --watch
```

- If checks still fail, repeat from 3a (up to 5 attempts)

### 4. Address PR Comments (when comments=true)

#### 4a. Fetch Review Comments

```bash
gh pr view <pr-ref> --json reviews,comments
# For detailed inline comments:
gh api repos/{owner}/{repo}/pulls/{number}/comments
```

#### 4b. Address Each Comment

For each unresolved review comment:
- Read the referenced code and the reviewer's feedback
- Make the requested change (or the closest reasonable interpretation)
- Commit with: `fix: address review — <summary of change>`

#### 4c. Push and Wait

```bash
git push
sleep 10
gh pr checks <pr-ref> --watch
```

If fixing comments introduces new check failures, loop back to step 3.

### 5. Iterate If Needed

Continue iterating until:
- All enabled checks pass
- All comments are addressed (if comments=true)
- Or you've exhausted reasonable attempts (max 5 iterations — then escalate to user)

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
