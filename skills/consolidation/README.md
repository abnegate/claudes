# consolidation

The structured agent cycle for executing non-trivial tasks with maximum parallelism and quality.

## The cycle

```
orchestrator
  -> planner        (decompose task into subtasks)
  -> verifier       (validate plan correctness + efficiency)
  -> architects     (parallel worktree execution)
  -> consolidator   (merge all branches)
  -> code-griller   (review merged output)
  -> verifier       (confirm acceptance criteria met)
```

## Core idea

Git worktrees give every agent its own complete copy of the repo. Multiple agents can freely edit the same files simultaneously. The consolidator merges everything at the end using full context of every subtask's intent. The planner optimizes for maximum parallelism, the verifier catches mistakes before and after execution.

## Agents

| Agent | Role | When |
|---|---|---|
| **orchestrator** | Conducts the full cycle | Entry point for non-trivial tasks |
| **planner** | Decomposes tasks, maps dependencies and parallelism | Stage 1 |
| **verifier** | Validates plans pre-execution, confirms outcomes post-execution | Stages 2 and 6 |
| **elite-fullstack-architect** | Implements code in worktree isolation | Stage 3 |
| **consolidator** | Merges worktree branches with conflict resolution | Stage 4 |
| **code-griller** | Reviews merged output for quality issues | Stage 5 |

## When to use

- Multi-file feature implementations
- Large refactors spanning multiple modules
- Batch operations across the codebase
- Any task with 2+ independent units of work
