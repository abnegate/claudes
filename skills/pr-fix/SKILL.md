---
name: pr-fix
description: Fix failing CI checks on a pull request
argument-hint: <pr-url-or-number>
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# Fix Failing PR Checks

Fix failing CI checks on a GitHub pull request, iterating until all checks pass.

## Arguments

- `$ARGUMENTS` - PR URL or number (e.g., `https://github.com/owner/repo/pull/123` or `123`)

## Workflow

### 1. Get PR Information

```bash
# Get PR details
gh pr view $ARGUMENTS --json number,headRefName,statusCheckRollup,url

# Get failing checks
gh pr checks $ARGUMENTS
```

### 2. Analyze Failures

For each failing check:
```bash
# Get check run details and logs
gh run view <run-id> --log-failed
```

### 3. Fix Issues

Based on the failure logs:
- Identify the root cause
- Make necessary code changes
- Commit with descriptive message

### 4. Push and Wait

```bash
# Push the fix
git push

# Wait for checks to start (give CI time to pick up the push)
sleep 10

# Poll check status until complete or timeout (10 minutes max)
gh pr checks $ARGUMENTS --watch
```

### 5. Iterate If Needed

If checks still fail:
- Analyze new failures
- Apply fixes
- Push and wait again
- Repeat until all checks pass or you've exhausted reasonable attempts (max 3 iterations)

## Important Notes

- Always checkout the PR branch first: `gh pr checkout $ARGUMENTS`
- Read failure logs carefully - the error message contains the fix
- Common failures in this project:
  - **ktlint**: Run `./gradlew ktlintFormat`
  - **tests**: Check test output, fix code or test
  - **build**: Check compilation errors
  - **detekt**: Check static analysis issues
- After each fix, commit with: `fix: <description of what was fixed>`

## Test Failure Policy

**IMPORTANT:** There is no such thing as a "pre-existing" test failure. If any test fails - whether it appears related to the PR changes or not - you must fix it. The task always completes with completely passing tests. Do not dismiss failures as "unrelated to this PR."

## Exit Conditions

Stop iterating when:
- All checks pass (required - no exceptions)
- 3 fix attempts have been made without resolution (escalate to user, do not give up)
