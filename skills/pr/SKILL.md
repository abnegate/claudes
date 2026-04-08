---
name: pr
description: Commit pending changes, push, and create a pull request with proper description
argument-hint: "[title]"
disable-model-invocation: true
allowed-tools: Bash, Read, Grep
---

# Create Pull Request

Commit any pending changes in logical groups, push the branch, then create a GitHub pull request with comprehensive description.

## Step 1: Commit All Pending Changes

Follow the `commit-all` workflow to turn any uncommitted work into logically grouped commits before proceeding.

### Commit Message Format

```
(<type>): <description>
```
- No body
- No multi-line string
- No co-authors

### Types

| Type | Use For |
|------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `refactor` | Code restructuring |
| `docs` | Documentation |
| `test` | Tests |
| `chore` | Maintenance |
| `perf` | Performance |
| `style` | Formatting |

### Execution

1. Run `git status` to see changes (never use `-uall`)
2. Run `git diff --staged` and `git diff` to understand changes
3. Run `git log --oneline -5` to see recent commit style
4. Determine logical groups of changes in the current diff
5. For each group:
   - Stage only the relevant files with `git add <paths>` (never `git add -A` / `.`)
   - Commit with HEREDOC format:
     ```bash
     git commit -m "$(cat <<'EOF'
     (type): description
     EOF
     )"
     ```
6. Run `git status` to verify the working tree is clean

### Safety Rules

- NEVER commit `.env` or credential files
- NEVER use `--amend` unless explicitly requested
- NEVER skip hooks with `--no-verify`
- If there are no pending changes, skip straight to Step 2

## Step 2: Gather PR Context (Parallel)

Launch FOUR parallel agents simultaneously to collect all information at once:

**Agent 1 — Git Status**:
```bash
git status
```
Confirm the working tree is clean after Step 1.

**Agent 2 — Commit History**:
```bash
git log main..HEAD --oneline
git log main..HEAD --format="%h %s%n%b"
```
Capture all commits that will be in the PR with their full messages.

**Agent 3 — Diff Summary**:
```bash
git diff main...HEAD --stat
git diff main...HEAD
```
Capture the full diff and file-level summary of all changes.

**Agent 4 — Fetch Remote**:
```bash
git fetch origin
```
Ensure remote refs are up to date for comparison.

## Step 3: Analyze and Sync (Parallel)

Once Step 2 completes, launch TWO parallel agents:

**Agent 1 — Check Remote Sync**:
```bash
git rev-list --left-right --count origin/main...HEAD
```
Determine whether the branch has diverged from origin/main.

**Agent 2 — Analyze Changes for PR Description**:
Using the commit history and diff from Step 2, produce:
- A concise summary (2-4 bullet points) of what changed and why
- A detailed changes list grouped by area (backend, frontend, tests, config)
- Appropriate PR title in conventional commit style if `$ARGUMENTS` was not provided
- Test plan based on what was modified

## Step 4: Push and Create PR

Push the branch to remote:

```bash
git push -u origin $(git branch --show-current)
```

Then create the PR:

```bash
gh pr create --title "$TITLE" --body "$(cat <<'EOF'
## Summary
- Bullet point summary of changes

## Changes
- Detailed list of what changed

## Test plan
- [ ] Tests pass locally
- [ ] Manual testing completed
- [ ] No regressions

## Screenshots (if UI changes)
N/A
EOF
)"
```

## PR Title Format

Use conventional commit style:
- `feat: Add new feature`
- `fix: Resolve bug in X`
- `refactor: Improve Y structure`

## If `$ARGUMENTS` Provided

Use as PR title. Otherwise, generate from commits.

## Output

Return the PR URL when complete.

## Checklist Before PR

- [ ] All tests pass
- [ ] Code is formatted (`./gradlew ktlintFormat`)
- [ ] No secrets in code
- [ ] SDK regenerated if API changed
