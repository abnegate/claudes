---
description: Implement a Linear issue end-to-end
argument-hint: <issue-id>
---

# Implement Linear Issue

Take a Linear issue and implement it completely using the full TDD workflow.

**YOU MUST NOT STOP UNTIL THE ISSUE IS FULLY RESOLVED.**

## Arguments

- `$ARGUMENTS` - Linear issue ID (e.g., `PLOT-123`)

## Phase 0: Issue Analysis (Parallel)

Launch THREE parallel agents simultaneously to gather all context at once:

**Agent 1 — Fetch Issue Details** (via Linear MCP):
- Title, description, labels, priority, assignee
- Parent issue (if sub-task)
- Related issues and comments
- Extract: what needs to be done, acceptance criteria, priority level, discussion context

**Agent 2 — Explore Codebase**:
- Use Glob and Grep to map the project structure
- Identify relevant source directories, test directories, and configuration files
- Find existing patterns, naming conventions, and architectural style
- Locate modules most likely to be affected based on common keywords from the issue ID prefix

**Agent 3 — Check Recent History**:
- `git log --oneline -20` for recent changes
- `git log --oneline --all --since="2 weeks ago"` for broader context
- Identify if anyone has worked on related areas recently
- Check for any in-flight branches that might conflict

### 0.1 Synthesize Results

Once all three agents complete, combine their outputs to form a unified understanding of:
- What the issue requires
- Where in the codebase the work will happen
- What recent changes might be relevant or conflicting

### 0.2 Update Issue Status

Move issue to "In Progress" state via Linear MCP.

### 0.3 Create Branch

```bash
ISSUE_ID="$ARGUMENTS"
ISSUE_TITLE=$(echo "[title from Linear]" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
git checkout -b "${ISSUE_ID}-${ISSUE_TITLE}"
```

### 0.4 Clarify If Needed

If the issue is ambiguous:
- Check comments for clarification
- Use `AskUserQuestion` to get missing details
- Add clarification as comment to Linear issue
- Do NOT proceed with assumptions

## Phase 1: Plan Implementation (Parallel Exploration)

Before creating the plan, launch parallel exploration agents for each module or area that will be affected:

**For each affected module**, launch a parallel agent to:
- Read the key files in that module
- Understand its public API and internal structure
- Identify test patterns already in use
- Note dependencies and coupling points

Once all exploration agents complete, synthesize findings into the implementation plan:

1. Create implementation plan based on issue requirements and exploration results
2. Write plan to `.claude/plans/PLAN-${ISSUE_ID}.md`
3. Break into phases with tests, informed by actual codebase patterns discovered

## Phase 2: Execute Plan

Delegate to `/implement` workflow which handles its own parallelization:
- TDD for each phase
- Code review with code-griller
- Fix all issues
- Update plan file as phases complete

## Phase 3: Finalize (Parallel Verification + PR)

Launch FOUR parallel agents simultaneously:

**Agent 1 — Run Tests**:
```bash
./gradlew test
```
Report pass/fail status and any failures.

**Agent 2 — Run Lint**:
```bash
./gradlew ktlintCheck
```
Report any lint violations.

**Agent 3 — Run Build**:
```bash
./gradlew build
```
Report build success or failure.

**Agent 4 — Prepare PR Content**:
While verification runs, draft the PR title, body, and summary by:
- Reviewing all commits on the branch vs main
- Summarizing changes made
- Listing test coverage additions
- Formatting the PR body with issue link

### 3.1 Handle Verification Failures

If any verification agent reports failures, fix them before proceeding. Re-run only the failed checks after fixing.

### 3.2 Create PR Linked to Issue

Using the PR content prepared by Agent 4 (adjusted if fixes were needed):

```bash
gh pr create --title "(feat): ${ISSUE_TITLE}" --body "$(cat <<EOF
## Summary
Implements ${ISSUE_ID}

## Changes
- [list changes]

## Test Plan
- [x] Unit tests added
- [x] All tests pass
- [ ] Manual testing

Linear: ${ISSUE_ID}
EOF
)"
```

### 3.3 Update Linear Issue

Via Linear MCP:
1. Add comment with PR link
2. Update status to "In Review"
3. Link the PR to the issue

## Phase 4: Post-Merge

After PR is merged:
1. Move Linear issue to "Done"
2. Add final comment summarizing what was implemented

## Completion Criteria

- [ ] Issue requirements fully implemented
- [ ] All tests pass
- [ ] Code reviewed and issues fixed
- [ ] PR created and linked to issue
- [ ] Plan file marked complete
- [ ] Linear issue updated with progress
