# consolidation

Parallel execution engine for multi-part tasks. Decomposes work into subtasks, runs them simultaneously in git worktree-isolated subagents, and merges all results into a single clean output.

## Core idea

Git worktrees give every agent its own complete copy of the repo. Multiple agents can freely edit the same files at the same time without corruption. A dedicated consolidator agent merges everything at the end, armed with full context of what every subtask intended — so conflicts are resolved by understanding code, not by picking sides.

## What it covers

- **Task decomposition** — breaking a request into concurrent subtasks and mapping file overlaps
- **Worktree-isolated parallel execution** — launching multiple subagents simultaneously, each in its own git worktree
- **The consolidator** — a concrete agent role definition with merge protocol, conflict resolution framework, post-merge verification checklist, and clear boundaries on what it does and does not do
- **Edge case handling** — failed subtasks, auto-merged but semantically wrong output, subtask dependencies
- **Post-merge verification** — tests, linting, type-checks to confirm the consolidated result is correct

## When to use

- Multi-part features where components can be built concurrently
- Large refactors spanning multiple modules (even when modules share files)
- Batch operations across the codebase
- Any task where serial execution wastes time

## When NOT to use

- Trivial single-file changes that finish in seconds
- Tasks with strict sequential dependencies where each step needs the previous step's output
