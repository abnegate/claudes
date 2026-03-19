---
name: implement
description: Full TDD implementation of a feature with review cycles
argument-hint: <feature description>
---

# Implement Feature (TDD)

Complete end-to-end implementation of a feature using Test-Driven Development with code review cycles.

**YOU MUST NOT STOP UNTIL THE ENTIRE PLAN IS IMPLEMENTED. NO TODOS. NO PARTIAL WORK.**

## Arguments

- `$ARGUMENTS` - Feature, fix, or chore description

## Phase 0: Understanding & Planning

### 0.1 Clarify Requirements

Ask questions until you have COMPLETE understanding:

- What exactly should this feature do?
- What are the edge cases?
- What are the acceptance criteria?
- Are there existing patterns to follow?
- What modules/files will be affected?
- Are there any constraints or requirements?

Use `AskUserQuestion` to gather any missing information. Do NOT proceed with ambiguity.

### 0.2 Create Implementation Plan

Break down into small, incremental phases. Each phase should be:
- Self-contained and testable
- Small enough to implement in one focused session
- Building on previous phases

**Write the plan to `.claude/plans/PLAN-<feature-slug>.md`:**

```markdown
# Implementation Plan: [Feature Name]

**Status:** In Progress
**Created:** [date]
**Description:** [brief description]

## Phases

### Phase 1: [Foundation]
- **Status:** [ ] Pending
- **What:** [specific deliverable]
- **Tests:** [what tests to write]
- **Files:** [files to create/modify]

### Phase 2: [Core Logic]
- **Status:** [ ] Pending
- **What:** [specific deliverable]
- **Tests:** [what tests to write]
- **Files:** [files to create/modify]
- **Depends on:** Phase 1

### Phase 3: [Integration]
- **Status:** [ ] Pending
...

### Phase N: [Final Polish]
- **Status:** [ ] Pending
...

## Progress Log

<!-- Updated as phases complete -->
```

Create the plans directory if needed:
```bash
mkdir -p .claude/plans
```

## Phase Loop: For Each Implementation Phase

### Step 1: Write Tests First (TDD Red)

Use **elite-fullstack-architect** to write tests BEFORE implementation:

```
Write failing tests for Phase N:
- Unit tests for new functions/classes
- Integration tests for API endpoints (if applicable)
- Edge case tests
- Error handling tests

Follow project test patterns (discover via existing tests).
```

Run tests to confirm they fail using the project's test command (e.g., `npm test`, `pytest`, `./gradlew test`, `cargo test`, etc.).

Tests MUST fail at this point (red phase).

### Step 2: Implement Code (TDD Green)

Use **elite-fullstack-architect** to implement minimal code to pass tests:

```
Implement Phase N:
- Write the minimum code to make tests pass
- Follow project patterns and conventions
- No premature optimization
- No extra features beyond what tests require
```

Run the project's test command.

If tests fail:
- Analyze failure
- Fix implementation
- Re-run tests
- Repeat until ALL tests pass

### Step 3: Code Review

Use **code-griller** to review the phase implementation:

```
Review the changes for Phase N:
- git diff from before phase started
- Focus on: security, correctness, maintainability, performance
- Check test quality and coverage
- Verify project patterns followed strictly
```

### Step 4: Address Review Findings

Use **elite-fullstack-architect** to fix review issues:

```
Address code-griller findings:
1. Verify each issue (skip false positives)
2. Fix all critical issues
3. Fix all warnings
4. Apply reasonable suggestions
```

### Step 5: Verify Tests Still Pass

Run the project's full test suite.

If any test fails:
- Fix the issue
- Re-run tests
- Do NOT proceed until green

### Step 6: Refactor (TDD Refactor)

Use **elite-fullstack-architect** for cleanup:

```
Refactor Phase N code:
- Improve readability
- Remove duplication
- Optimize if needed
- Keep tests passing
```

Run tests again after refactoring.

### Step 7: Commit Phase

```bash
git add -A
git commit -m "$(cat <<'EOF'
(feat): [phase description]
EOF
)"
```

### Step 8: Update Plan File

Update `.claude/plans/PLAN-<feature-slug>.md`:

1. Change phase status from `[ ] Pending` to `[x] Complete`
2. Add entry to Progress Log:

```markdown
## Progress Log

### Phase 1 - [timestamp]
- **Status:** Complete
- **Tests added:** [count]
- **Files changed:** [list]
- **Review issues fixed:** [count]
- **Commit:** [hash]
```

3. If all phases complete, update top status to `**Status:** Complete`

### Step 9: Next Phase

Move to next phase. Repeat until all phases marked `[x] Complete`.

## Completion Criteria

**DO NOT STOP UNTIL:**

1. ALL phases in plan file are marked `[x] Complete`
2. ALL tests pass (test suite is green)
3. Code is reviewed and issues addressed
4. No TODOs or placeholders in code
5. No "will implement later" comments
6. Feature works end-to-end
7. Plan file status is `**Status:** Complete`

## Final Verification

After all phases, run the project's standard verification commands:

1. **Full test suite** - Run all tests (e.g., `npm test`, `pytest`, `./gradlew test`, `cargo test`)
2. **Lint check** - Run project linter if configured (e.g., `npm run lint`, `ruff check`, `./gradlew ktlintCheck`, `cargo clippy`)
3. **Build verification** - Run full build (e.g., `npm run build`, `./gradlew build`, `cargo build`)

If anything fails, fix it before declaring complete.

## Summary Report

Update the plan file with final summary:

```markdown
# Implementation Plan: [Feature Name]

**Status:** Complete
**Created:** [date]
**Completed:** [date]
**Description:** [brief description]

## Phases

### Phase 1: [Foundation]
- **Status:** [x] Complete
...

## Progress Log
[all phase entries]

## Final Summary

### Tests Added
- X unit tests
- Y integration tests
- Z edge case tests

### Files Changed
- [list of files]

### Commits
- [commit hashes and messages]

### Verification
- [x] All tests pass
- [x] Lint passes
- [x] Build succeeds
- [x] No TODOs remaining
- [x] Plan file complete
```

## Hard Rules

1. **NO STOPPING MID-FEATURE** - Complete the entire plan
2. **NO SKIPPING TESTS** - TDD is mandatory
3. **NO SKIPPING REVIEWS** - Every phase gets reviewed
4. **NO PLACEHOLDERS** - Implement fully or don't start
5. **NO BROKEN TESTS** - Fix before moving on
6. **ASK QUESTIONS EARLY** - Don't guess requirements
7. **NO "PRE-EXISTING" EXCUSES** - There is no such thing as a "pre-existing" test failure. If any test fails, fix it. The task always completes with completely passing tests.
