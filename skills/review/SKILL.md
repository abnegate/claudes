---
name: review
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
BASE="main"
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

Launch these **reviewer** agents in parallel, each reviewing the same diff but focused on a different dimension:

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
- Compliance with the detected stack's lint and format config
- The rules of the matching house skill, loaded with the Skill tool (for example `Skill(skill="skills:php-expert")`)
- The user's and the project's CLAUDE.md rules
- Correct serialization annotations
- Code clarity and readability

Detect the stacks the diff touches from the manifests at the repository root and the changed file types, and give Agent D each stack's config files and house skill. Examples:

| Stack | Lint and format config | House skill |
|---|---|---|
| Gradle | ktlint through Spotless or the ktlint plugin (`.editorconfig`), detekt (`detekt.yml`) | kotlin-expert; android-expert for Android and Compose code |
| Maven | Checkstyle, PMD or Spotless configured in `pom.xml` | kotlin-expert for Kotlin code |
| PHP | Pint (`pint.json`) or PHP-CS-Fixer, PHPStan (`phpstan.neon`) | php-expert; swoole-expert for Swoole code |
| Node | ESLint (`eslint.config.*`), Prettier (`.prettierrc`), `tsconfig.json` | react-best-practices for React code |
| Rust | `rustfmt.toml`, Clippy (`clippy.toml`, `[lints]` in `Cargo.toml`) | — |
| Go | gofmt, golangci-lint (`.golangci.yml`) | — |
| Python | Ruff and mypy (`[tool.ruff]` and `[tool.mypy]` in `pyproject.toml`) | — |
| Docker | hadolint (`.hadolint.yaml`) if configured | docker-expert |

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
