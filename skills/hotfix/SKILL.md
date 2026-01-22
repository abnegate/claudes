---
name: hotfix
description: Emergency hotfix workflow for production issues
argument-hint: "<issue-description>"
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Task, AskUserQuestion
---

# Emergency Hotfix

Rapid response workflow for critical production issues.

**PRIORITY: Fix the issue with minimal changes. Speed matters.**

## Arguments

- `$ARGUMENTS` - Description of the production issue

## Phase 0: Triage

### 0.1 Understand Severity

Ask if not clear:
- Is this blocking users?
- Is data being corrupted?
- Is there a security vulnerability?
- What's the blast radius?

### 0.2 Get Context

```bash
# Check current production state
git fetch origin
git log origin/main --oneline -5

# Check recent deployments
gh run list --limit 5
```

## Phase 1: Create Hotfix Branch

```bash
# Branch from main (or current release branch)
git checkout main
git pull origin main
git checkout -b hotfix/$(date +%Y%m%d)-brief-description
```

## Phase 2: Reproduce & Diagnose

### 2.1 Reproduce Locally

If possible:
- Replicate the exact conditions
- Capture error logs/stack traces
- Identify the failing code path

### 2.2 Root Cause (Quick)

Find the issue fast:
- Check recent commits that could have caused this
- Look at the stack trace
- Identify the minimal fix

```bash
# Find recent changes to affected area
git log --oneline -20 -- path/to/affected/code
```

## Phase 3: Minimal Fix

### 3.1 Implement Fix

**RULES:**
- Smallest possible change
- No refactoring
- No "while we're here" improvements
- Just fix the bug

### 3.2 Add Regression Test

Write ONE test that:
- Reproduces the exact bug
- Verifies the fix works
- Prevents regression

```bash
# Run the new test
./gradlew test --tests "*HotfixTestName*"
```

### 3.3 Verify No Breakage

```bash
# Run full test suite - must pass
./gradlew test

# Build must succeed
./gradlew build
```

## Phase 4: Quick Review

Use **code-griller** for focused review:
- Is the fix correct?
- Could it cause other issues?
- Is it the minimal change needed?

Fix any critical issues found. Skip suggestions - this is a hotfix.

## Phase 5: Create PR

```bash
git add -A
git commit -m "$(cat <<'EOF'
(hotfix): [brief description]

Issue: [what was broken]
Fix: [what this changes]
EOF
)"

git push -u origin HEAD

gh pr create --title "(hotfix): [description]" --body "$(cat <<EOF
## Emergency Hotfix

### Issue
[What was broken in production]

### Root Cause
[Why it broke]

### Fix
[What this PR changes]

### Testing
- [x] Regression test added
- [x] All tests pass
- [x] Minimal change verified

### Rollback Plan
[How to rollback if needed]
EOF
)"
```

## Phase 6: Deployment Checklist

Provide deployment instructions:

```markdown
## Deployment Steps

1. [ ] PR approved
2. [ ] Merge to main
3. [ ] Monitor CI/CD pipeline
4. [ ] Verify deployment successful
5. [ ] Monitor for 15 minutes post-deploy
6. [ ] Confirm issue resolved in production

## Rollback Command
[Specific rollback instructions]

## Post-Mortem
Schedule follow-up to:
- [ ] Investigate root cause fully
- [ ] Add more comprehensive fix if needed
- [ ] Update monitoring/alerting
```

## Test Failure Policy

**IMPORTANT:** There is no such thing as a "pre-existing" test failure. If any test fails - whether it appears related to the hotfix or not - you must fix it. The task always completes with completely passing tests.

## Completion Criteria

- [ ] Issue reproduced and understood
- [ ] Minimal fix implemented
- [ ] Regression test added
- [ ] ALL tests pass (no exceptions for "pre-existing" failures)
- [ ] PR created with context
- [ ] Deployment instructions provided
