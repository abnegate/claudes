---
description: Debug and fix failing tests or errors
argument-hint: "<test-name|error-description|stack-trace>"
---

# Debug and Fix

Systematically debug and fix failing tests, build errors, or runtime issues using aggressive parallelization at every phase.

**DO NOT STOP UNTIL THE ISSUE IS FIXED AND TESTS PASS.**

## Arguments

- `$ARGUMENTS` - Test name, error message, or description of the issue

## Phase 1: Reproduce and Gather Context

Launch **three parallel agents** simultaneously to maximize information gathering speed.

**Agent 1 - Reproduce the failure:**

If test failure:
```bash
# Run specific test
./gradlew test --tests "*$ARGUMENTS*" --info

# Or run all tests to find failures
./gradlew test
```

If build error:
```bash
./gradlew build --stacktrace
```

If runtime error, get the full stack trace and identify the failing component.

Capture all error details: full error message, stack trace, test name and class, file and line number, input that caused the failure.

**Agent 2 - Check recent changes:**

```bash
git diff HEAD~5 --name-only
git diff HEAD~5 -- <relevant paths>
```

Identify what files changed recently that could be related to the failure. Summarize which changes are most likely to have introduced the bug.

**Agent 3 - Check git history:**

```bash
git log --oneline -15
git log --oneline -5 -- <files related to $ARGUMENTS>
```

Determine if this is a regression by finding when the relevant code last changed and who changed it.

**Wait for all three agents to complete.** Synthesize their findings to determine:
- Is this a single test failure or multiple?
- Is it flaky (intermittent)?
- Is it a regression (worked before)?
- What is the scope of the problem?

## Phase 2: Root Cause Analysis

Using the error details from Phase 1, launch **three parallel agents** to analyze all relevant code simultaneously.

**Agent 1 - Analyze the failing test** (use `Explore` or read directly):

Read and understand the failing test file completely. Document:
- What the test expects
- What setup and mocks it uses
- What assertions are failing and why
- Whether the test itself is correct or buggy

**Agent 2 - Analyze the code under test** (use `Explore` or read directly):

Read the production code that the test exercises. Document:
- The relevant function or method signatures
- The control flow path that leads to the failure
- Any recent changes to this code (cross-reference with Phase 1 Agent 2 results)
- Potential bugs: null references, wrong logic, missing error handling, race conditions

**Agent 3 - Analyze related dependencies** (use `Explore` or read directly):

Read related files: interfaces, shared utilities, configuration, DI modules, database schemas, or mocks that the code under test depends on. Document:
- Whether any dependencies changed recently
- Whether mocks match current interfaces
- Whether configuration or DI wiring is correct
- Whether database state assumptions still hold

**Wait for all three agents to complete.** Synthesize their findings into a root cause hypothesis:
- What is wrong
- Why it causes this specific error
- What the minimal fix should be

## Phase 3: Fix and Verify

### 3.1 Implement Fix

Use **elite-fullstack-architect** to implement the fix:
- Fix the root cause, not symptoms
- Make the minimal targeted change
- Preserve existing behavior for passing cases
- Do not change unrelated code

### 3.2 Parallel Verification

After implementing the fix, launch **two parallel agents** to verify simultaneously.

**Agent 1 - Run the specific failing test:**

```bash
./gradlew test --tests "*FailingTestName*" --info
```

Confirm the original failure is resolved. If it still fails, report the new error details.

**Agent 2 - Run related tests:**

```bash
./gradlew test --tests "*RelatedModule*"
```

Confirm no closely related tests have broken as a side effect of the fix.

**Wait for both agents to complete.** If either agent reports a failure, return to Phase 2 with the new information and repeat. Do not proceed until both pass.

## Phase 4: Full Validation

Launch **two parallel agents** for final validation.

**Agent 1 - Code review** (use **code-griller**):

Review the fix for:
- Correctness: is this the right fix for the root cause?
- Edge cases: does it handle all boundary conditions?
- Side effects: could it cause other issues?
- Quality: does it follow project conventions and naming standards?

If the review finds issues, fix them before proceeding.

**Agent 2 - Full test suite:**

```bash
./gradlew test
./gradlew build
```

Run the entire test suite and build to catch any regressions anywhere in the codebase.

**Wait for both agents to complete.** If the full suite has failures, fix every one of them (there are no "pre-existing" failures). If the code review raised issues, address them and re-run verification.

### 4.1 Add Test Coverage

If the bug was not caught by existing tests:
- Add a test for this specific case
- Add tests for related edge cases
- Ensure this bug cannot recur

Run the new tests to confirm they pass:
```bash
./gradlew test --tests "*NewTestName*"
```

### 4.2 Commit Fix

Delegate to the `commit` skill:

```
Skill(skill="commit", args="(fix): [description of what was fixed]")
```

## Debug Techniques

### For Test Failures
```bash
# Run with debug output
./gradlew test --tests "*TestName*" --info

# Run single test class
./gradlew :module:test --tests "com.example.TestClass"
```

### For Null Pointer / Missing Data
- Check test setup and mocks
- Verify DI is configured correctly
- Check database state for integration tests

### For Async / Timing Issues
- Check coroutine scopes
- Look for race conditions
- Verify test uses proper async testing utilities

### For Flaky Tests
```bash
# Run multiple times
for i in {1..10}; do ./gradlew test --tests "*FlakyTest*" || break; done
```

## Test Failure Policy

**IMPORTANT:** There is no such thing as a "pre-existing" test failure. If any test fails, whether it appears related to your changes or not, you must fix it. The task always completes with completely passing tests.

## Completion Criteria

- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Original failing test passes
- [ ] ALL tests pass (no exceptions for "pre-existing" failures)
- [ ] No regressions introduced
- [ ] Fix reviewed via code-griller
- [ ] Committed with clear message
