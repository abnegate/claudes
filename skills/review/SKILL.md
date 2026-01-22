---
name: review
description: Thorough code review of current branch against main
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Task
---

# Code Review

Perform a thorough code review of the current branch against the base branch using the code-griller agent.

## Workflow

### 1. Determine Base Branch

```bash
# Get current branch
CURRENT=$(git branch --show-current)

# Check if this is appwrite (uses 1.8.x) or other project (uses main)
if git remote -v | grep -q "appwrite"; then
    BASE="1.8.x"
else
    BASE="main"
fi

echo "Reviewing $CURRENT against $BASE"
```

### 2. Get Changes

```bash
# See what files changed
git diff $BASE...HEAD --name-only

# Get full diff for review
git diff $BASE...HEAD
```

### 3. Invoke Code Griller

Use the **code-griller** subagent to perform a comprehensive review:

- Pass the diff and changed files to the code-griller agent
- Request a thorough, uncompromising review

### 4. Review Focus Areas

The code-griller should examine:

**Critical Issues**
- Security vulnerabilities (injection, auth bypass, data exposure)
- Data corruption risks
- Breaking changes to public APIs

**Code Quality**
- Logic errors and edge cases
- Error handling gaps
- Resource leaks
- Race conditions

**Maintainability**
- Code clarity and readability
- Proper naming conventions
- DRY violations
- Overly complex logic

**Performance**
- N+1 queries
- Unnecessary allocations
- Missing indexes (for DB changes)
- Inefficient algorithms

**Testing**
- Missing test coverage
- Inadequate edge case testing
- Flaky test patterns

**Project Standards**
- KtLint compliance
- Proper use of Exposed ORM patterns
- Correct serialization annotations
- MVI pattern adherence (client code)

### 5. Output Format

Provide a structured report:

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
