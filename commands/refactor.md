---
description: Safe refactoring with comprehensive test coverage
argument-hint: "<what-to-refactor>"
---

# Safe Refactoring

Refactor code safely with tests as a safety net.

**RULE: All tests must pass before AND after. No behavior changes.**

## Arguments

- `$ARGUMENTS` - What to refactor (file, module, pattern, etc.)

## Phase 0: Preparation

### 0.1 Parallel Discovery

Launch **three agents in parallel** to gather all baseline information simultaneously:

**Agent A: Coverage Report**
```
Task: Generate the test coverage report for the affected area.
Run `./gradlew koverReport` and read the coverage output.
Report the coverage percentage for every file in the refactoring scope.
Flag any file below 80% coverage.
```

**Agent B: Baseline Tests**
```
Task: Run the full test suite and report results.
Run `./gradlew test`.
Report pass/fail counts and list any failures with their full stack traces.
```

**Agent C: Scope Analysis**
```
Task: Analyze the refactoring scope for `$ARGUMENTS`.
Determine what is being refactored: single file, multiple related files, entire module, or cross-cutting pattern.
Identify and list:
- Every public API surface (public functions, classes, interfaces, data classes)
- Expected inputs and outputs for each public entry point
- Edge cases and error paths
- Integration points with other modules
- All direct dependents (files that import or reference the target)
Write findings to `.claude/plans/PLAN-refactor-scope.md`.
```

**Wait for all three agents to complete before continuing.**

### 0.2 Evaluate Results

Review the outputs from all three agents:
- If Agent B reported test failures: **STOP. Fix failures before proceeding.**
- If Agent A reported coverage below 80% for any file in scope: proceed to Phase 1.
- If coverage is adequate (>=80%): skip Phase 1, proceed to Phase 2.

## Phase 1: Add Missing Tests

### 1.1 Parallel Gap Analysis

Launch **parallel agents per dimension** to identify every untested path. Create one agent per category:

**Agent: Branch Coverage**
```
Task: Analyze the coverage report and source code for `$ARGUMENTS`.
List every uncovered branch (if/else, when, try/catch) with file path and line numbers.
For each uncovered branch, write a one-line description of what condition triggers it.
```

**Agent: Edge Cases**
```
Task: Analyze the source code for `$ARGUMENTS`.
List every edge case that lacks a test: null inputs, empty collections, boundary values,
overflow conditions, concurrent access, and type coercion scenarios.
For each, specify the function and the exact edge condition.
```

**Agent: Error Paths**
```
Task: Analyze the source code for `$ARGUMENTS`.
List every error/exception path that lacks a test: thrown exceptions, error returns,
fallback branches, retry logic, timeout handling, and resource cleanup paths.
For each, specify the function, the error condition, and expected behavior.
```

**Wait for all agents to complete.** Merge their findings into a single prioritized list.

### 1.2 Write Characterization Tests

Tests that capture CURRENT behavior (even if it seems wrong):
- Test what the code DOES, not what it SHOULD do
- These tests lock in behavior during refactoring
- Work through the merged list from 1.1, highest-priority gaps first

```bash
# Verify new tests pass
./gradlew test
```

**STOP IF TESTS FAIL.** Fix tests until green.

## Phase 2: Plan Refactoring

### 2.1 Parallel Goals and Research

Launch **two agents in parallel** to build the refactoring plan:

**Agent: Goals Analysis**
```
Task: Given the scope analysis from Phase 0 and the refactoring request `$ARGUMENTS`,
determine and rank the refactoring goals by impact:
- Readability improvements
- Performance gains
- Maintainability wins
- Duplication removal
- Abstraction improvements
For each goal, cite specific locations in the code and explain the expected improvement.
```

**Agent: Pattern Research**
```
Task: Read all files in the refactoring scope for `$ARGUMENTS`.
Identify which standard refactoring patterns apply:
- Extract Method/Class opportunities (functions >20 lines, classes with >1 responsibility)
- Rename candidates (names that don't reflect purpose)
- Duplication (repeated logic across files)
- Conditional simplification (complex if/else or when chains)
- Magic value extraction (hard-coded literals)
For each, specify the exact file, line range, and recommended pattern.
```

**Wait for both agents to complete.**

### 2.2 Build Step Plan

Using the outputs from both agents, break the refactoring into small, safe steps:
- Each step must be independently committable
- Each step must keep tests green
- Prefer many small changes over few large ones
- Order steps so that renames and moves come before structural changes

Write plan to `.claude/plans/PLAN-refactor-<slug>.md`

## Phase 3: Incremental Refactoring

For each step in the plan:

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

Delegate to the `commit` skill:

```
Skill(skill="commit", args="(refactor): [specific change made]")
```

### 3.4 Repeat

Continue with next step until refactoring complete.

## Phase 4: Parallel Review

Launch **three agents in parallel** for comprehensive review:

**Agent: Code Review**
```
Task: Review all changes made during this refactoring session using `git diff main...HEAD`.
Evaluate:
- Is all original behavior preserved?
- Is the code measurably better (readability, structure, performance)?
- Are there any accidental behavioral changes?
- Do all public APIs remain unchanged (unless the change was intentional)?
- Are there any regressions in code quality?
Report issues as a numbered list with file path, line number, and description.
```

**Agent: Test Suite**
```
Task: Run the full test suite.
Run `./gradlew test`.
Report pass/fail counts and list any failures with full stack traces.
Confirm test count has not decreased compared to the baseline from Phase 0.
```

**Agent: Lint**
```
Task: Run lint and format checks.
Run `./gradlew ktlintFormat` then `./gradlew ktlintCheck`.
Report any remaining lint violations with file path and description.
```

**Wait for all three agents to complete.**

If any agent reports failures or issues:
- Fix every reported problem
- Re-run the failing agent's checks to confirm resolution
- Repeat until all three agents report clean

### 4.1 Compare Before/After

```bash
# See full diff from start
git diff main...HEAD
```

Verify:
- No public API changes (unless intended)
- No behavior changes
- Tests still cover the same scenarios

## Phase 5: Parallel Final Verification

Launch **three agents in parallel** for final confirmation:

**Agent: Final Tests**
```
Task: Run the full test suite one final time.
Run `./gradlew test`.
Report pass/fail counts. ALL tests must pass.
```

**Agent: Final Lint**
```
Task: Run final lint verification.
Run `./gradlew ktlintFormat` then `./gradlew ktlintCheck`.
Confirm zero violations.
```

**Agent: Final Build**
```
Task: Run a clean build to verify compilation.
Run `./gradlew build`.
Report success or failure with any error details.
```

**Wait for all three agents to complete. ALL must report success.**

If any agent fails, fix the issue and re-run all three agents in parallel again.

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
