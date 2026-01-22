---
name: refactor
description: Safe refactoring with comprehensive test coverage
argument-hint: "<what-to-refactor>"
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Task
---

# Safe Refactoring

Refactor code safely with tests as a safety net.

**RULE: All tests must pass before AND after. No behavior changes.**

## Arguments

- `$ARGUMENTS` - What to refactor (file, module, pattern, etc.)

## Phase 0: Preparation

### 0.1 Identify Scope

Determine what's being refactored:
- Single file
- Multiple related files
- Entire module
- Cross-cutting pattern

### 0.2 Verify Test Coverage

```bash
# Generate coverage for affected area
./gradlew koverReport

# Check coverage percentage
open build/reports/kover/html/index.html
```

If coverage is low (<80%):
- Write tests FIRST before refactoring
- Cover the current behavior
- Tests become your safety net

### 0.3 Document Current Behavior

Note:
- Public API surface
- Expected inputs/outputs
- Edge cases
- Integration points

### 0.4 Run Baseline Tests

```bash
# All tests must pass before starting
./gradlew test
```

**DO NOT PROCEED IF TESTS FAIL.**

## Phase 1: Add Missing Tests

If coverage is insufficient:

### 1.1 Identify Untested Paths

Use **elite-fullstack-architect** to analyze:
- Uncovered branches
- Edge cases
- Error paths

### 1.2 Write Characterization Tests

Tests that capture CURRENT behavior (even if it's wrong):
- Test what the code DOES, not what it SHOULD do
- These tests lock in behavior during refactor

```bash
# Verify new tests pass
./gradlew test
```

## Phase 2: Plan Refactoring

### 2.1 Define Goals

What are we improving?
- Readability
- Performance
- Maintainability
- Removing duplication
- Better abstractions

### 2.2 Plan Steps

Break into small, safe steps:
- Each step should be committable
- Each step should keep tests green
- Prefer many small changes over few big ones

Write plan to `.claude/plans/PLAN-refactor-<slug>.md`

## Phase 3: Incremental Refactoring

For each step:

### 3.1 Make One Change

Single, focused change:
- Rename
- Extract method/class
- Move code
- Simplify logic
- Remove duplication

### 3.2 Run Tests

```bash
./gradlew test
```

**STOP IF TESTS FAIL.** Fix or revert before continuing.

### 3.3 Commit

```bash
git add -A
git commit -m "(refactor): [specific change made]"
```

### 3.4 Repeat

Continue with next step until refactoring complete.

## Phase 4: Review

### 4.1 Code Review

Use **code-griller** to review:
- Is behavior preserved?
- Is the code actually better?
- Any accidental changes?

### 4.2 Compare Before/After

```bash
# See full diff from start
git diff main...HEAD
```

Verify:
- No public API changes (unless intended)
- No behavior changes
- Tests still cover the same scenarios

## Phase 5: Final Verification

```bash
# Full test suite
./gradlew test

# Lint
./gradlew ktlintFormat
./gradlew ktlintCheck

# Build
./gradlew build
```

## Common Refactoring Patterns

### Extract Method
```kotlin
// Before
fun process() {
    // 20 lines of validation
    // 20 lines of processing
}

// After
fun process() {
    validate()
    doProcessing()
}
```

### Extract Class
When a class has too many responsibilities.

### Rename for Clarity
When names don't reflect purpose.

### Remove Duplication
Extract shared logic to helper/utility.

### Simplify Conditionals
Replace complex if/else with when, early returns, or polymorphism.

### Replace Magic Values
Extract constants with meaningful names.

## Completion Criteria

- [ ] Adequate test coverage before starting
- [ ] All tests pass after each step
- [ ] Refactoring improves code quality
- [ ] No behavior changes
- [ ] Code reviewed
- [ ] Final tests pass
- [ ] Committed with clear messages
