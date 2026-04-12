---
name: consolidation
description: Decompose a task into independent subtasks and execute them in parallel using git worktree-isolated subagents, then consolidate all changes into a single clean merge. Each agent works in its own worktree so multiple agents can freely edit the same files without collision — a dedicated consolidation agent merges everything at the end using full context of every subtask's intent. Use for large refactors, multi-part features, batch operations, or any task that decomposes into concurrent work. Triggers on phrases like "do this in parallel", "consolidate", "split this up", or any multi-part task.
---

# Consolidation

Parallel execution engine for multi-part tasks. Decomposes work into subtasks, runs them simultaneously in isolated git worktrees, and merges all results into a single clean output.

Git worktrees give every agent its own complete copy of the repo. Multiple agents can edit the same files simultaneously without corruption. The consolidation agent at the end has full context of what every subtask intended, so it resolves conflicts by understanding code, not by picking sides.

## When to use

- Multi-part features where components can be built concurrently
- Large refactors spanning multiple modules (even when modules share files)
- Batch operations across the codebase
- Any task where serial execution wastes time

## When NOT to use

- Trivial single-file changes that finish in seconds
- Tasks with strict sequential dependencies where each step needs the previous step's output

## Execution protocol

Follow these phases exactly. Do not skip or reorder them.

### Phase 1: Analyze and decompose

Study the task and codebase before launching anything:

1. **Read the relevant code.** Understand file structure, dependencies, conventions. Build a mental map.
2. **Identify subtasks.** Break the request into concurrent units. Each subtask must be self-contained enough that an agent can complete it from the current repo state alone, with clear completion criteria.
3. **Map file overlaps.** Identify which files will be touched by multiple subtasks. This is expected, not a problem.
4. **Plan the consolidation.** For each overlapping file, describe what each subtask will change and how those changes combine. Identify cross-cutting wiring work (barrel exports, route registrations, config entries).

Present the decomposition:

```
Subtask 1: [description] — files: [list]
Subtask 2: [description] — files: [list]
...
Overlapping files: [file] (subtasks 1, 3), [file] (subtasks 2, 4)
Consolidation plan: [how overlaps merge + wiring work]
```

### Phase 2: Launch parallel worktree agents

Launch ALL subtasks simultaneously in a single message using multiple `Agent` tool calls. Every agent MUST use `isolation: "worktree"`.

Each agent prompt must be self-contained:

1. **Full context** — the agent has never seen this conversation. Explain the overall goal, specific subtask, and why it matters.
2. **Exact file paths** — which files to read first and which to create or modify.
3. **Conventions** — paste or reference style rules, naming conventions, relevant CLAUDE.md rules.
4. **Completion criteria** — what "done" looks like. The agent must commit its changes before finishing.
5. **Parallel awareness** — tell the agent others are working concurrently. It should focus only on its own subtask. A consolidation agent will merge everything afterwards.

### Phase 3: Collect results

When all agents complete, record for each:
- `branch`: the branch name containing the agent's commits
- `worktree_path`: the filesystem path of the worktree
- A summary of what changed

Note any failures or agents that made no changes.

### Phase 4: Consolidate

Launch a single consolidation agent on the main working tree (NOT `isolation: "worktree"`).

The consolidation agent prompt MUST include:
1. Every branch name from Phase 3
2. A detailed summary of what each branch changed (specific files, specific edits, intent)
3. The overlap map from Phase 1, updated with actual changes from Phase 3
4. Wiring work needed after all branches merge
5. Verification commands for the project

Instruct the agent to follow "The Consolidator" protocol defined below.

### Phase 5: Report

Summarize for the user: how many subtasks ran, what each accomplished, how overlapping edits were resolved, verification results, and any follow-up items.

## The Consolidator

This section defines what the consolidation agent IS and how it operates. Paste this into the consolidation agent's prompt.

### Identity

You are the consolidator. You have full context of every parallel subtask's intent, files changed, and expected output. Your job is to produce a single coherent codebase state that incorporates ALL successful subtask changes. You are not a mechanical merge tool. You understand the code. You resolve conflicts by understanding intent, not by picking sides.

### Merge protocol

Execute in this order:

1. Run `git log --oneline -5` to confirm current branch state.
2. For each worktree branch (in the order provided):
   a. `git diff main...[branch] --stat` to see what changed.
   b. `git merge [branch] --no-edit`.
   c. If clean: move to next branch.
   d. If conflict: read BOTH sides, consult the intent description for that branch, write the correct unified version. Use `git checkout --theirs`/`--ours` only when one side is clearly right. For real overlaps, manually edit.
3. After all merges, review EVERY file touched by 2+ branches — even if git merged it cleanly. Auto-merges can be syntactically valid but semantically wrong (duplicate imports, conflicting logic, redundant code).
4. Do wiring work: imports, barrel exports, route registrations, config entries, anything that ties the subtasks together.
5. Run verification: tests, linters, type-checks. Fix failures.
6. Commit: `(chore): consolidate parallel changes — [summary]`.
7. Clean up worktree branches: `git worktree remove [path] && git branch -d [branch]` for each.

### Conflict resolution framework

**Additive changes to the same file** (both branches added new functions/classes/imports): keep both, deduplicate, ensure consistent ordering.

**Both branches modified the same function**: understand what each was trying to do. If complementary (one fixed a bug, other added a feature), combine both. If contradictory, prefer the one aligned with the overall task goal.

**Import/dependency conflicts**: union of all imports, deduplicated, alphabetically sorted.

**Config/schema changes**: merge all additions. If two branches set the same key to different values, prefer the one from the subtask with higher specificity to that config area.

**Type definition overlaps**: union of all type members/fields. If two branches defined the same type differently, produce the superset that satisfies both consumers.

**When genuinely ambiguous**: do NOT guess. Stop and report the conflict with both sides shown, ask the user.

### Post-merge checklist

- Every file touched by 2+ branches: manually reviewed for semantic correctness
- No duplicate imports, function definitions, or type declarations
- All new symbols properly exported/imported where needed
- Tests pass (or are noted as pre-existing failures)
- Linter passes
- Type-checker passes

### What the consolidator does NOT do

- Add new features or refactor beyond what's needed for the merge
- "Improve" the subtask agents' code
- Reformat files beyond what the linter requires
- Make architectural decisions — those were made during decomposition

## Edge cases

**Subtask agent fails.** Do not block consolidation of successful branches. Merge what succeeded, report the failure, offer to retry in a fresh worktree.

**Auto-merged but semantically wrong.** Git may merge cleanly but produce broken code (duplicate imports, conflicting signatures, incompatible logic). The consolidator must review every file touched by multiple branches and fix semantic issues before committing.

**Subtask depends on another subtask's output.** These cannot run in parallel. Either merge them into one subtask or run the dependency first, merge its branch, then launch the dependent subtask in a second wave.

## Performance guidelines

- **2-6 subtasks** is the sweet spot. More than 8 adds coordination overhead.
- **Prefer fewer, larger subtasks** over many tiny ones. Each worktree has setup cost.
- **Front-load the reading.** Do all codebase analysis in Phase 1 so agent prompts are precise. Vague prompts cause agents to waste time exploring.
- **Be thorough in the overlap map.** The consolidator's effectiveness is directly proportional to how well you describe the overlaps and intended merge behavior.

## Example

User asks: "Refactor the auth system to use JWT tokens instead of sessions. Update the middleware, user model, login/register endpoints, and tests."

```
Subtask 1: Auth middleware
  Files: src/middleware/auth.ts, src/lib/jwt.ts (new), src/types/auth.ts
  Changes: Replace session checks with JWT verification, add JWT utility lib

Subtask 2: User model + login/register
  Files: src/models/user.ts, src/routes/auth.ts, src/types/auth.ts
  Changes: Remove session methods, add token generation, update endpoints

Subtask 3: Tests
  Files: tests/auth.test.ts, tests/middleware.test.ts, tests/helpers/auth.ts
  Changes: Rewrite all auth tests for JWT flow

Overlapping files:
  src/types/auth.ts — subtasks 1 and 2 both add JWT-related types.
    Subtask 1 adds TokenPayload and VerifyOptions.
    Subtask 2 adds LoginResponse and RegisterResponse with token fields.
    Merge: include all four types.

Consolidation wiring:
  - Update src/app.ts to use new JWT middleware
  - Update src/routes/index.ts if route signatures changed
  - Ensure test helpers reference the new JWT utility
```

All three subtasks launch simultaneously. The consolidator merges all branches, combines the overlapping `auth.ts` types, does the wiring, and runs tests.
