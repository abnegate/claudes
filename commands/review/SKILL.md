---
description: Thorough code review of current branch against main
---

# Code Review

Perform a thorough code review of the current branch against the base branch using parallel agents for speed.

## Workflow

### 1. Gather Context (Parallel)

Launch these in parallel:

**Agent 1 — Branch & Diff Info:**
```bash
CURRENT=$(git branch --show-current)
if git remote -v | grep -q "appwrite"; then BASE="1.8.x"; else BASE="main"; fi
echo "Reviewing $CURRENT against $BASE"
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

### 2. Parallel Code Review

Launch these **code-griller** agents in parallel, each reviewing the same diff but focused on a different dimension:

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
- N+1 queries
- Unnecessary allocations
- Missing indexes (for DB changes)
- Inefficient algorithms
- Missing test coverage
- Inadequate edge case testing
- Flaky test patterns

**Agent D — Project Standards:**
- KtLint compliance
- Proper use of Exposed ORM patterns
- Correct serialization annotations
- MVI pattern adherence (client code)
- Code clarity and readability

### 3. Merge & Report

Combine findings from all agents into a single structured report:

```
## Review Summary
- Files reviewed: X
- Issues found: Y (X critical, Y warnings, Z suggestions)

## Critical Issues (Must Fix)
1. [file:line] Description of issue
   - Why it's critical
   - Suggested fix

## Warnings (Should Fix)
1. [file:line] Description
   - Impact
   - Suggested fix

## Suggestions (Consider)
1. [file:line] Description
   - Rationale

## Positive Notes
- Things done well
```

Deduplicate findings across agents. Prioritize by severity.
