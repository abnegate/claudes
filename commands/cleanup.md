---
description: Find and remove dead code, unused imports, and technical debt
argument-hint: "[module|all]"
---

# Code Cleanup

Systematic cleanup of dead code, unused imports, and technical debt.

**RULE: All tests must pass after cleanup. No behavior changes.**

## Arguments

- `$ARGUMENTS` - Module to clean up, or `all` for entire codebase

## Phase 0: Baseline (Parallel)

**Launch these agents in parallel:**

**Agent A** (`elite-fullstack-architect`): Run the full test suite and capture the output.
```bash
./gradlew test
```
Report pass/fail status and any existing failures. If tests do not pass, STOP. Do not proceed until all tests are green.

**Agent B** (`elite-fullstack-architect`): Run static analysis tools and capture current warning counts.
```bash
./gradlew detekt
./gradlew ktlintCheck
```
Report the total warning count and error count for each tool. These are the baseline numbers.

**Wait for both agents to complete.** If Agent A reports test failures, fix them before continuing. Record Agent B's baseline counts for comparison in the final summary.

## Phase 1: Detection Sweep (Parallel)

All detection work is read-only analysis. **Launch these agents in parallel:**

**Agent A - Unused Imports** (`Explore`): Scan all `.kt` files in the target module(s) for unused imports. Use IDE-style analysis: for each import statement, search the file body for usage of the imported symbol. Produce a list of files with unused imports and the specific import lines.

**Agent B - Dead Code** (`Explore`): Search for dead code across the target module(s). Look for:
- Unused private functions (private functions with zero call sites)
- Unused private classes (private classes never referenced)
- Unused parameters (parameters never read in the function body)
- Unreachable code (code after unconditional return/throw)
- Commented-out code blocks (3+ consecutive commented lines that look like code)
- `TODO`/`FIXME`/`HACK`/`XXX` comments

For each finding, note the file path, line number, symbol name, and why it appears dead.

**Agent C - Deprecated Code** (`Explore`): Search for all deprecation markers across the target module(s):
- `@Deprecated` annotations
- `@deprecated` KDoc tags
- Calls to functions/classes that are annotated `@Deprecated`

For each finding, note the file, the deprecated symbol, and whether a replacement is specified.

**Agent D - Technical Debt** (`Explore`): Search for technical debt indicators across the target module(s):
- `@Suppress` annotations (note what warning is suppressed)
- TODO/FIXME comments with context
- Known workarounds (comments mentioning "workaround", "hack", "temporary")
- Outdated patterns (e.g., deprecated Kotlin idioms, old coroutine patterns)

For each finding, assess severity (High/Medium/Low) and estimated effort (Low/Medium/High).

**Agent E - Code Style** (`Explore`): Analyze code style consistency across the target module(s):
- Naming convention violations (inconsistent casing, abbreviations, Hungarian notation)
- Inconsistent error handling patterns (mixed try-catch vs Result vs runCatching)
- Inconsistent logging patterns (mixed logger frameworks, inconsistent log levels)
- Section-header comments (`// ---`, `// ===`, `// ****`) that should be removed

**Agent F - Stale Documentation** (`Explore`): Scan for documentation issues across the target module(s):
- Comments that restate the code (e.g., `// increment counter` above `counter++`)
- Outdated comments that reference renamed/removed symbols
- TODO comments that reference completed work
- Public API functions/classes missing KDoc
- KDoc with `@param`/`@return` tags that don't match the current signature

**Wait for all six agents to complete.** Collect all findings into a unified cleanup manifest organized by file. This prevents conflicting edits when multiple issues exist in the same file.

## Phase 2: Automated Fixes (Sequential)

These steps modify code and must run sequentially to avoid conflicts.

### 2.1 Unused Imports

```bash
./gradlew ktlintFormat
```

This handles the bulk of import cleanup automatically.

### 2.2 Verify Imports

```bash
./gradlew test
```

## Phase 3: Manual Cleanup (Parallel by File Group)

Using the unified manifest from Phase 1, partition the affected files into independent groups (files that don't import each other). **Launch parallel agents per group:**

**Each Agent** (`elite-fullstack-architect`): For its assigned file group, apply all queued fixes from the manifest:

1. **Dead code removal**: Delete confirmed unused private functions, classes, parameters. Remove commented-out code blocks. Clean up or remove stale TODO comments.
2. **Deprecated code migration**: Where a replacement is specified in the `@Deprecated` annotation, migrate callers to the replacement. Where we own the deprecated symbol and it has zero external callers, remove it.
3. **Technical debt quick wins**: Fix items that are High severity + Low effort or Low severity + Low effort. For High effort items, add a `// TODO(cleanup): [description]` or create a GitHub issue.
4. **Code style normalization**: Fix naming violations, remove section-header comments (`// ---`, `// ===`), standardize error handling within each file.
5. **Documentation cleanup**: Remove stale/obvious comments. Add KDoc to public APIs that are missing it. Fix mismatched `@param`/`@return` tags.

After all edits in the group, run a targeted compile check:
```bash
./gradlew compileKotlin
```

**Wait for all file-group agents to complete.**

### 3.1 Integration Verify

```bash
./gradlew test
```

If tests fail, identify which file group introduced the failure and fix it before proceeding.

## Phase 4: Final Formatting

```bash
./gradlew ktlintFormat
```

## Phase 5: Final Verification (Parallel)

**Launch these agents in parallel:**

**Agent A** (`elite-fullstack-architect`): Run the full test suite.
```bash
./gradlew test
```

**Agent B** (`elite-fullstack-architect`): Run lint checks.
```bash
./gradlew ktlintCheck
```

**Agent C** (`elite-fullstack-architect`): Run detekt analysis.
```bash
./gradlew detekt
```

**Agent D** (`elite-fullstack-architect`): Run a full build.
```bash
./gradlew build
```

**Wait for all four agents to complete.** All must pass. If any fail, fix the issues and re-run only the failing checks. Compare detekt/ktlint warning counts against the Phase 0 baseline to quantify improvement.

## Phase 6: Summary

Create cleanup report:

```markdown
# Cleanup Report: [Module/All]

## Summary
- Files modified: X
- Lines removed: Y
- Warnings fixed: Z (before: B, after: A)

## Changes Made

### Unused Imports Removed
- X files had unused imports removed

### Dead Code Removed
- [file:symbol] - [why it was dead]

### Deprecated Code Migrated
- [file:symbol] - migrated to [replacement]

### Technical Debt Addressed
- [item] - [what was done]

### Code Style Fixed
- [description of patterns normalized]

### Documentation Cleaned
- [stale comments removed, KDoc added]

### Issues Created for High-Effort Items
- #NNN - [tech debt item]

## Remaining Items
- [items that need future attention]
```

## Commit Strategy

Delegate to the `skills:commit-all` command to produce atomic, logically-grouped commits from the cleanup changes:

```
Skill(skill="skills:commit-all")
```

`skills:commit-all` will partition the diff into groups like unused imports, dead code removal, deprecation migration, style normalization, etc. and commit each group with a `(chore): ...` message.

## Completion Criteria

- [ ] All unused imports removed
- [ ] Dead code removed
- [ ] Deprecations addressed or documented
- [ ] Quick-win tech debt fixed
- [ ] Code formatted and style consistent
- [ ] Stale documentation cleaned
- [ ] All tests pass
- [ ] Detekt/ktlint warning count reduced from baseline
- [ ] Cleanup report created
