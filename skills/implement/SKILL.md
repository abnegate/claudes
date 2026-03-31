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

### 0.2 Parallel Codebase Exploration

**Launch THREE parallel agents simultaneously** to explore the codebase. Do NOT run these sequentially.

**Agent 1 - Pattern Discovery:**
```
Explore the codebase to find existing patterns relevant to this feature:
- Architecture patterns (layering, module structure, dependency flow)
- Naming conventions and code style
- Error handling patterns
- Configuration and environment patterns
- How similar features are structured
Report back with a summary of patterns to follow.
```

**Agent 2 - Affected Module Analysis:**
```
Analyze all modules and files that will be affected by this feature:
- Map the dependency graph of affected areas
- Identify public APIs that will change
- Find all callers/consumers of code that will be modified
- Identify shared utilities or helpers relevant to the feature
- Flag any areas with high coupling that need careful handling
Report back with a map of affected modules and their relationships.
```

**Agent 3 - Test Pattern Discovery:**
```
Find and analyze the project's testing patterns:
- Test framework and runner in use
- Test file naming and location conventions
- Test helper utilities and fixtures
- Mocking/stubbing patterns
- Integration test setup patterns
- How test data is managed
- The exact commands to run tests, lint, and build
Report back with a testing guide for this project.
```

**Wait for all three agents to complete.** Synthesize their findings before proceeding.

### 0.3 Create Implementation Plan

Break down into small, incremental phases. Each phase should be:
- Self-contained and testable
- Small enough to implement in one focused session
- Building on previous phases

Incorporate findings from all three exploration agents into the plan.

**Write the plan to `.claude/plans/PLAN-<feature-slug>.md`:**

```markdown
# Implementation Plan: [Feature Name]

**Status:** In Progress
**Created:** [date]
**Description:** [brief description]

## Codebase Context
- **Patterns:** [summary from Agent 1]
- **Affected Modules:** [summary from Agent 2]
- **Test Approach:** [summary from Agent 3]
- **Test Command:** [exact test command]
- **Lint Command:** [exact lint command]
- **Build Command:** [exact build command]

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

Follow project test patterns (discovered in Phase 0.2).
```

Run tests to confirm they fail using the project's test command.

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

### Step 3: Parallel Review + Test Verification

**Launch TWO parallel agents simultaneously.** Do NOT run these sequentially.

**Agent A - Code Review:**
```
Use code-griller to review the changes for Phase N:
- git diff from before phase started
- Focus on: security, correctness, maintainability, performance
- Check test quality and coverage
- Verify project patterns followed strictly
- Report all findings categorized as critical/warning/suggestion
```

**Agent B - Full Test Suite:**
```
Run the project's FULL test suite (not just the new tests).
Report: pass/fail status, any failures with details, total test count.
```

**Wait for both agents to complete.** Collect the review findings and test results.

### Step 4: Address Review Findings

Use **elite-fullstack-architect** to fix review issues:

```
Address code-griller findings:
1. Verify each issue (skip false positives)
2. Fix all critical issues
3. Fix all warnings
4. Apply reasonable suggestions
```

### Step 5: Parallel Test Verification + Refactor Analysis

**Launch TWO parallel agents simultaneously.** Do NOT run these sequentially.

**Agent A - Test Verification:**
```
Run the project's full test suite.
Confirm all tests pass after review fixes.
Report: pass/fail status, any failures with details.
```

**Agent B - Refactor Analysis:**
```
Analyze the Phase N code for refactoring opportunities:
- Duplicated code that can be extracted
- Overly complex methods that should be split
- Naming improvements
- Unnecessary abstractions or missing abstractions
- Performance improvements that don't sacrifice readability
Report a prioritized list of refactoring actions.
```

**Wait for both agents to complete.**

If Agent A reports test failures:
- Fix the issues immediately
- Re-run tests
- Do NOT proceed until green

### Step 6: Refactor (TDD Refactor)

Apply the refactoring actions identified by Agent B in Step 5:

```
Refactor Phase N code:
- Apply the prioritized refactoring actions from the analysis
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

**Launch THREE parallel agents simultaneously** for final verification. Do NOT run these sequentially.

**Agent 1 - Full Test Suite:**
```
Run all tests (e.g., npm test, pytest, ./gradlew test, cargo test).
Report: pass/fail, failure details, total count.
```

**Agent 2 - Lint Check:**
```
Run project linter if configured (e.g., npm run lint, ruff check, ./gradlew ktlintCheck, cargo clippy).
Report: pass/fail, all violations with file locations.
```

**Agent 3 - Build Verification:**
```
Run full build (e.g., npm run build, ./gradlew build, cargo build).
Report: pass/fail, any errors or warnings.
```

**Wait for all three agents to complete.**

If ANY agent reports failure, fix the issue and re-run the failing verification. Do not re-run passing verifications unless the fix could have affected them.

## Summary Report

Update the plan file with final summary:

```markdown
# Implementation Plan: [Feature Name]

**Status:** Complete
**Created:** [date]
**Completed:** [date]
**Description:** [brief description]

## Codebase Context
- **Patterns:** [summary]
- **Affected Modules:** [summary]
- **Test Approach:** [summary]

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
8. **PARALLEL AGENTS ARE MANDATORY** - When this skill says "launch parallel agents simultaneously", you MUST use parallel tool calls. Running them sequentially defeats the purpose and wastes time. Independent work streams must always run concurrently.
