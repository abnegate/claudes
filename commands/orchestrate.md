---
description: End-to-end feature workflow - branch, implement, review-fix, PR, wait, pr-fix
argument-hint: <feature description>
---

# Orchestrate Feature

Full end-to-end pipeline: sync the base branch, cut a new working branch, implement the feature, run review-fix cycles, open a PR, then auto-fix CI once checks have had time to run.

## Arguments

- `$ARGUMENTS` - Feature, fix, or chore description. This doubles as the branch name source and the input to the implementation step.

## Step 1: Detect Base Branch and Sync

The base branch is NOT always `main`. Ask GitHub for the repo's configured default branch:

```bash
BASE=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
echo "BASE=$BASE"
```

If `gh` is not authenticated or the repo has no remote on GitHub, fall back to the local `origin/HEAD` symref:

```bash
if [ -z "$BASE" ]; then
  BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
fi
```

If both fail, STOP and ask the user which branch to base the work on — do NOT guess.

Sync the base branch:

```bash
git fetch origin
git checkout "$BASE"
git pull --ff-only origin "$BASE"
```

If the working tree is dirty when this runs, STOP and ask the user how to proceed (do NOT stash or discard their changes).

## Step 2: Create Feature Branch

Derive a slug from `$ARGUMENTS`:
- lowercase
- spaces and non-alphanumeric characters → `-`
- trim leading/trailing `-`
- truncate to ~50 chars

Prefix based on intent parsed from `$ARGUMENTS`:
- `fix/` for bug fixes
- `feat/` for features
- `refactor/` for refactors
- `chore/` for maintenance
- `docs/` for docs

```bash
SLUG=<computed slug>
BRANCH="feat/$SLUG"   # or fix/, refactor/, etc.
git checkout -b "$BRANCH"
```

## Step 3: Assess Complexity

Based on `$ARGUMENTS` and a quick scan of the affected areas, classify the work into ONE of these buckets and record the cycle count:

| Complexity | Signals | Cycles |
|---|---|---|
| Small fix | One-line/trivial bug fix, typo, copy change, single file | 1 |
| Small feature | New small endpoint, isolated utility, simple UI component | 2 |
| Medium feature | Multi-file change, touches a domain, new integration | 3 |
| Big feature | Cross-cutting, new subsystem, migrations, API changes, many files | 4 |
| Huge feature | Architecture-level, multiple domains, data model changes | 5 |

If the description is ambiguous, pick the HIGHER bucket - extra review cycles are cheaper than missed issues.

Record the choice as `CYCLES=N` and state the rationale in one sentence before proceeding.

## Step 4: Implement the Feature

Delegate implementation to an **elite-fullstack-architect** agent. Pass:
- The full `$ARGUMENTS` description
- The base branch name
- Project conventions from any nearby `CLAUDE.md`
- Instruction to follow TDD where the project has tests
- Instruction to commit logically-grouped changes as it works

The agent must implement fully - no TODOs, no placeholders, no "will add later".

After the architect returns, verify:
```bash
git status
git log "$BASE"..HEAD --oneline
```

If the working tree is dirty (uncommitted changes), commit them before moving on - `review-fix` reviews the diff vs base, not the worktree.

## Step 5: Run review-fix

Invoke the `review-fix` skill with the computed cycle count:

```
/review-fix $CYCLES
```

Use the Skill tool:
```
Skill(skill="review-fix", args="$CYCLES")
```

Wait for it to complete. It will create additional commits on the current branch.

## Step 6: Run pr

Invoke the `pr` skill to commit anything still pending, push, and open the PR:

```
Skill(skill="pr")
```

**Capture the PR URL from the skill's output.** Store it as `PR_URL`. If the skill output does not include a URL, run `gh pr view --json url -q .url` on the current branch to fetch it.

## Step 7: Wait 5 Minutes for CI

CI needs time to start and report results. Sleep for 5 minutes before running pr-fix:

```bash
sleep 300
```

Do NOT skip this wait - running pr-fix immediately races CI and sees no failures to fix.

While waiting, you may summarize progress to the user, but do not start new work that modifies the branch.

## Step 8: Run pr-fix

Invoke the `pr-fix` skill with the captured PR URL and both flags enabled:

```
Skill(skill="pr-fix", args="$PR_URL checks=true comments=true")
```

This will iterate on failing checks and address any review comments already posted.

## Step 9: Final Report

After pr-fix completes, report:

```
## Orchestrate Summary

- **Feature:** <description>
- **Base branch:** <BASE>
- **Feature branch:** <BRANCH>
- **Complexity:** <bucket> (<CYCLES> review cycles)
- **PR:** <PR_URL>
- **Review cycles run:** <CYCLES>
- **PR-fix iterations:** <count from pr-fix>
- **Final CI state:** <pass/fail>
```

## Hard Rules

1. **DO NOT STOP MID-WORKFLOW** - Run all steps through to pr-fix completion unless a hard blocker appears.
2. **DO NOT SKIP THE 5-MINUTE WAIT** - pr-fix is useless without CI results to analyze.
3. **DO NOT DESTROY USER WORK** - If the working tree is dirty at Step 1, stop and ask.
4. **DO NOT GUESS THE BASE BRANCH** - Use the detection logic; ask if it fails.
5. **ROUND COMPLEXITY UP, NOT DOWN** - Extra review cycles are cheap insurance.
6. **USE THE Skill TOOL FOR SUB-SKILLS** - Do not inline review-fix / pr / pr-fix logic; call them so their own updates are automatically picked up.
