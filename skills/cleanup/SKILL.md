---
name: cleanup
description: Find and remove dead code, unused imports, and technical debt
argument-hint: "[module|all]"
---

# Code Cleanup

Systematic cleanup of dead code, unused imports, and technical debt.

**RULE: All tests must pass after cleanup. No behavior changes.**

## Arguments

- `$ARGUMENTS` - Module to clean up, or `all` for entire codebase

## Phase 0: Baseline

### 0.1 Run Tests

```bash
# All tests must pass before starting
./gradlew test
```

### 0.2 Run Static Analysis

```bash
# Get current state
./gradlew detekt
./gradlew ktlintCheck
```

Note current warnings/errors for comparison.

## Phase 1: Unused Imports

### 1.1 Find and Remove

```bash
# KtLint handles unused imports
./gradlew ktlintFormat
```

### 1.2 Verify

```bash
./gradlew test
```

## Phase 2: Dead Code Detection

### 2.1 Find Unused Code

Look for:
- Unused private functions
- Unused private classes
- Unused parameters
- Unreachable code
- Commented-out code

```bash
# Use detekt for dead code detection
./gradlew detekt

# Search for TODO/FIXME comments
grep -r "TODO\|FIXME\|HACK\|XXX" --include="*.kt"
```

### 2.2 Analyze Each Finding

For each potential dead code:
1. Verify it's truly unused (search for references)
2. Check if it's used via reflection
3. Check if it's a public API
4. Determine if safe to remove

### 2.3 Remove Dead Code

Remove confirmed dead code:
- Delete unused functions
- Delete unused classes
- Remove commented-out code
- Clean up TODO comments (fix or remove)

### 2.4 Verify After Each Removal

```bash
./gradlew test
```

## Phase 3: Deprecated Code

### 3.1 Find Deprecations

```bash
# Find deprecated usages
grep -r "@Deprecated\|@deprecated" --include="*.kt"
```

### 3.2 Update or Remove

For each deprecation:
- If replacement exists, migrate to it
- If owned by us, consider removal timeline
- Document why if keeping

## Phase 4: Technical Debt

### 4.1 Identify Debt

Look for:
- Suppressed warnings (`@Suppress`)
- TODO comments
- Known workarounds
- Outdated patterns
- Inconsistent code

### 4.2 Prioritize

Create list of tech debt items:

| Item | Severity | Effort | Action |
|------|----------|--------|--------|
| [Item 1] | High | Low | Fix now |
| [Item 2] | Medium | High | Create issue |
| [Item 3] | Low | Low | Fix now |

### 4.3 Quick Wins

Fix items that are:
- High severity + Low effort
- Low severity + Low effort

Create issues for high-effort items.

## Phase 5: Code Style

### 5.1 Format

```bash
./gradlew ktlintFormat
```

### 5.2 Consistent Patterns

Look for inconsistencies:
- Naming conventions
- Error handling patterns
- Logging patterns
- Comment styles

Standardize where possible.

## Phase 6: Documentation

### 6.1 Remove Stale Comments

Comments that:
- Describe obvious code
- Are outdated
- Repeat the code
- Are TODOs that won't be done

### 6.2 Add Missing Documentation

For public APIs:
- Add KDoc where missing
- Update outdated docs

## Phase 7: Final Verification

```bash
# All tests pass
./gradlew test

# Lint is clean
./gradlew ktlintCheck

# Detekt passes
./gradlew detekt

# Build succeeds
./gradlew build
```

## Phase 8: Summary

Create cleanup report:

```markdown
# Cleanup Report: [Module/All]

## Summary
- Files modified: X
- Lines removed: Y
- Warnings fixed: Z

## Changes Made

### Unused Code Removed
- [file:function] - [reason]

### Imports Cleaned
- X files had unused imports removed

### Dead Code Removed
- [description]

### Tech Debt Addressed
- [item] - [what was done]

### Issues Created
- #123 - [tech debt item]
- #124 - [tech debt item]

## Remaining Items
- [items that need future attention]
```

## Commit Strategy

Make atomic commits:
```bash
git commit -m "(chore): Remove unused imports"
git commit -m "(chore): Remove dead code in [module]"
git commit -m "(chore): Fix detekt warnings"
```

## Completion Criteria

- [ ] All unused imports removed
- [ ] Dead code removed
- [ ] Deprecations addressed
- [ ] Quick-win tech debt fixed
- [ ] Code formatted
- [ ] All tests pass
- [ ] Cleanup report created
