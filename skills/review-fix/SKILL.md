---
name: review-fix
description: Review code and fix issues in cycles
argument-hint: "[cycles=1]"
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Task
---

# Review and Fix

Perform code review cycles where code-griller reviews and elite-fullstack-architect fixes issues.

## Arguments

- `$ARGUMENTS` - Number of review/fix cycles (default: 1)

Parse cycles from arguments:
- `/review-fix` → 1 cycle
- `/review-fix 3` → 3 cycles

## Workflow

For each cycle (1 to N):

### Step 1: Code Griller Review

Determine base branch:
```bash
if git remote -v | grep -q "appwrite"; then
    BASE="1.8.x"
else
    BASE="main"
fi
```

Use **code-griller** subagent to review `git diff $BASE...HEAD`:

Focus on:
- Critical: Security, data corruption, breaking changes
- Warnings: Logic errors, error handling, resource leaks
- Quality: Readability, DRY, complexity

Output a prioritized list of issues with file:line references.

### Step 2: Elite Architect Fixes

Pass the code-griller report to **elite-fullstack-architect** subagent.

The architect should:
1. Verify each issue is valid (not false positive)
2. Fix confirmed issues in priority order:
   - All critical issues
   - All warnings
   - Suggestions if time permits
3. For each fix:
   - Make minimal, focused changes
   - Ensure fix doesn't introduce new issues
   - Run relevant tests if quick

### Step 3: Commit Fixes

After fixes are applied:
```bash
git add -A
git commit -m "$(cat <<'EOF'
fix: address code review findings

- [list key fixes made]
EOF
)"
```

### Step 4: Next Cycle (if cycles > 1)

If more cycles remain:
- Run code-griller again on updated code
- Repeat fix process
- Each cycle should find fewer issues

## Cycle Summary

After all cycles, report:

```
## Review-Fix Summary

### Cycle 1
- Issues found: X
- Issues fixed: Y
- Remaining: Z

### Cycle 2
- Issues found: X (down from previous)
- Issues fixed: Y
- Remaining: Z

...

### Final State
- Total issues fixed: N
- Remaining issues: M (with explanation if any)
- Commits created: K
```

## Exit Conditions

Stop early if:
- No issues found (code is clean)
- Same issues persist after 2 attempts (may need human input)
- Only suggestions remain (no critical/warnings)

## Test Failure Policy

**IMPORTANT:** There is no such thing as a "pre-existing" test failure. If any test fails - whether it appears related to the reviewed changes or not - you must fix it. The task always completes with completely passing tests.

## Notes

- Max recommended cycles: 3 (diminishing returns after)
- Each cycle builds on previous fixes
- Don't fix the same issue twice - track what's been addressed
- ALL tests must pass before completing - no exceptions for "pre-existing" failures
