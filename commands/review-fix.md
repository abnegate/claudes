---
description: Review code and fix issues in cycles
argument-hint: "[cycles=1]"
---

# Review and Fix

Perform code review cycles where parallel code-griller agents review and parallel elite-fullstack-architect agents fix issues.

## Arguments

- `$ARGUMENTS` - Number of review/fix cycles (default: 1)

Parse cycles from arguments:
- `/review-fix` -> 1 cycle
- `/review-fix 3` -> 3 cycles

## Workflow

For each cycle (1 to N):

### Step 1: Gather Context (Parallel)

Launch these agents in parallel to collect all review inputs simultaneously:

**Agent 1 — Base Branch & Changed Files:**
```bash
if git remote -v | grep -q "appwrite"; then BASE="1.8.x"; else BASE="main"; fi
echo "BASE=$BASE"
git diff $BASE...HEAD --name-only
git diff $BASE...HEAD --stat
```

**Agent 2 — Full Diff:**
```bash
git diff $BASE...HEAD
```

**Agent 3 — Commit History:**
```bash
git log $BASE..HEAD --oneline
```

### Step 2: Parallel Code Griller Review

Launch four **code-griller** agents in parallel, each reviewing the same diff but focused on a different dimension. Every agent receives the full diff and file list from Step 1.

**Agent A — Security & Data Integrity:**
- Security vulnerabilities (injection, auth bypass, data exposure)
- Data corruption risks
- Breaking changes to public APIs
- Resource leaks

**Agent B — Logic & Correctness:**
- Logic errors and edge cases
- Error handling gaps
- Race conditions
- Proper naming conventions
- DRY violations

**Agent C — Performance & Testing:**
- N+1 queries, unnecessary allocations, missing indexes
- Inefficient algorithms
- Missing test coverage, inadequate edge case testing, flaky test patterns

**Agent D — Project Standards:**
- KtLint compliance
- Proper use of Exposed ORM patterns
- Correct serialization annotations
- MVI pattern adherence (client code)
- Code clarity and readability

Each agent outputs a prioritized list of issues with `file:line` references and severity (critical / warning / suggestion).

### Step 3: Merge & Deduplicate

Combine findings from all four review agents into a single prioritized issue list. Remove duplicates where multiple agents flagged the same line. Group by severity:
1. Critical issues
2. Warnings
3. Suggestions

### Step 4: Parallel Fixes (Consolidation Pattern)

Partition the deduplicated issue list into groups by area/theme. Use the **consolidation pattern** — launch each fix group as a parallel worktree-isolated agent (`isolation: "worktree"`). Agents can freely edit overlapping files; the consolidator handles merges.

**Per worktree agent:**
1. Verify each assigned issue is valid (not a false positive)
2. Fix confirmed issues with minimal, focused changes
3. Ensure fixes do not introduce new issues
4. Commit all changes before finishing

**After all worktree agents complete**, launch the **consolidator** agent (`subagent_type: "consolidator"`) to merge all branches and resolve any overlapping edits.

### Step 5: Verify

Launch a **verifier** agent (`subagent_type: "verifier"`) in post-verification mode to confirm tests pass and lint is clean. If it fails, fix and re-verify.

### Step 6: Commit Fixes

After all fixes pass verification, delegate to the `skills:commit` command:

```
Skill(skill="skills:commit", args="fix: address code review findings")
```

### Step 7: Next Cycle (if cycles > 1)

If more cycles remain:
- Return to Step 1 and repeat on the updated code
- Each cycle should find fewer issues
- Track what was already addressed to avoid fixing the same issue twice

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
