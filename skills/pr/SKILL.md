---
name: pr
description: Create a pull request with proper description
argument-hint: "[title]"
disable-model-invocation: true
allowed-tools: Bash, Read, Grep
---

# Create Pull Request

Create a GitHub pull request with comprehensive description.

## Step 1: Gather Context (Parallel)

Launch FOUR parallel agents simultaneously to collect all information at once:

**Agent 1 — Git Status**:
```bash
git status
```
Capture working tree state, staged files, untracked files.

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

## Step 2: Analyze and Sync (Parallel)

Once Step 1 completes, launch TWO parallel agents:

**Agent 1 — Check Remote Sync**:
```bash
git rev-list --left-right --count origin/main...HEAD
```
Determine if the branch needs pushing and whether it has diverged from origin/main.

**Agent 2 — Analyze Changes for PR Description**:
Using the commit history and diff from Step 1, produce:
- A concise summary (2-4 bullet points) of what changed and why
- A detailed changes list grouped by area (backend, frontend, tests, config)
- Appropriate PR title in conventional commit style if `$ARGUMENTS` was not provided
- Test plan based on what was modified

## Step 3: Push and Create PR (Parallel, then Sequential)

Launch TWO parallel agents:

**Agent 1 — Push Branch**:
```bash
git push -u origin $(git branch --show-current)
```
Push the branch to remote (skip if already up to date from Step 2 analysis).

**Agent 2 — Prepare PR Body**:
Format the final PR body from the analysis in Step 2, incorporating:
- Summary section
- Changes section
- Test plan section

Once both agents complete, create the PR:

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
