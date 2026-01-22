---
name: issue
description: Implement a Linear issue end-to-end
argument-hint: <issue-id>
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Task, AskUserQuestion, mcp__linear__*
---

# Implement Linear Issue

Take a Linear issue and implement it completely using the full TDD workflow.

**YOU MUST NOT STOP UNTIL THE ISSUE IS FULLY RESOLVED.**

## Arguments

- `$ARGUMENTS` - Linear issue ID (e.g., `PLOT-123`)

## Phase 0: Issue Analysis

### 0.1 Fetch Issue Details

Use Linear MCP server to get issue details:
- Title
- Description
- Labels
- Priority
- Assignee
- Parent issue (if sub-task)
- Related issues
- Comments

### 0.2 Understand Requirements

Extract from the issue:
- What needs to be done
- Acceptance criteria (if specified)
- Related issues
- Priority level
- Any discussion in comments

### 0.3 Update Issue Status

Move issue to "In Progress" state via Linear MCP.

### 0.4 Create Branch

```bash
# Use issue ID for branch name
ISSUE_ID="$ARGUMENTS"
ISSUE_TITLE=$(echo "[title from Linear]" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)

# Create branch
git checkout -b "${ISSUE_ID}-${ISSUE_TITLE}"
```

### 0.5 Clarify If Needed

If the issue is ambiguous:
- Check comments for clarification
- Use `AskUserQuestion` to get missing details
- Add clarification as comment to Linear issue
- Do NOT proceed with assumptions

## Phase 1: Plan Implementation

Use `/implement` workflow:

1. Create implementation plan based on issue requirements
2. Write plan to `.claude/plans/PLAN-${ISSUE_ID}.md`
3. Break into phases with tests

## Phase 2: Execute Plan

Follow full `/implement` workflow:
- TDD for each phase
- Code review with code-griller
- Fix all issues
- Update plan file as phases complete

## Phase 3: Finalize

### 3.1 Verify All Tests Pass

```bash
./gradlew test
./gradlew ktlintCheck
./gradlew build
```

### 3.2 Create PR Linked to Issue

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
