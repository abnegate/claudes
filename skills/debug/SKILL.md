---
name: debug
description: Debug and fix failing tests or errors
argument-hint: "<test-name|error-description|stack-trace>"
---

# Debug and Fix

Systematically debug and fix failing tests, build errors, or runtime issues.

**DO NOT STOP UNTIL THE ISSUE IS FIXED AND TESTS PASS.**

## Arguments

- `$ARGUMENTS` - Test name, error message, or description of the issue

## Phase 1: Reproduce and Understand

### 1.1 Reproduce the Issue

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

If runtime error:
- Get full stack trace
- Identify the failing component

### 1.2 Capture Error Details

Collect:
- Full error message
- Stack trace
- Test name and class
- File and line number
- Input that caused failure

### 1.3 Identify Scope

Determine:
- Is this a single test or multiple?
- Is it flaky (intermittent)?
- Is it a regression (worked before)?
- What was recently changed?

```bash
# Check recent changes
git log --oneline -10
git diff HEAD~5 --name-only
```

## Phase 2: Root Cause Analysis

### 2.1 Analyze Stack Trace

- Find the actual failure point (not just the assertion)
- Trace back through the call stack
- Identify the root cause vs symptoms

### 2.2 Read Relevant Code

Use **elite-fullstack-architect** to analyze:
- The failing test
- The code under test
- Related dependencies
- Recent changes to these files

### 2.3 Form Hypothesis

Document:
- What you think is wrong
- Why it would cause this error
- How to verify the hypothesis

## Phase 3: Fix

### 3.1 Implement Fix

Make minimal, targeted fix:
- Fix the root cause, not symptoms
- Don't change unrelated code
- Preserve existing behavior for passing cases

### 3.2 Verify Fix

```bash
# Run the specific failing test
./gradlew test --tests "*FailingTestName*"

# Run related tests
./gradlew test --tests "*RelatedModule*"

# Run full test suite
./gradlew test
```

### 3.3 Check for Regressions

```bash
# Ensure no new failures
./gradlew test
./gradlew build
```

## Phase 4: Validate

### 4.1 Code Review

Use **code-griller** to review the fix:
- Is it the right fix?
- Does it handle edge cases?
- Could it cause other issues?

### 4.2 Add Test Coverage

If the bug wasn't caught by tests:
- Add test for this specific case
- Add tests for related edge cases
- Ensure this bug can't recur

### 4.3 Commit Fix

```bash
git add -A
git commit -m "$(cat <<'EOF'
(fix): [description of what was fixed]

Root cause: [brief explanation]
EOF
)"
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

**IMPORTANT:** There is no such thing as a "pre-existing" test failure. If any test fails - whether it appears related to your changes or not - you must fix it. The task always completes with completely passing tests.

## Completion Criteria

- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Original failing test passes
- [ ] ALL tests pass (no exceptions for "pre-existing" failures)
- [ ] No regressions introduced
- [ ] Fix reviewed
- [ ] Committed with clear message
