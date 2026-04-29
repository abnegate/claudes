# consolidation

The structured cycle for executing non-trivial tasks with maximum parallelism and quality.

## The cycle

```
[top-level agent — you, with this skill loaded]
  -> planner        (decompose task into subtasks)
  -> verifier       (validate plan correctness + efficiency)
  -> architects     (parallel worktree execution)
  -> consolidator   (merge all branches)
  -> reviewer       (review merged output)
  -> verifier       (confirm acceptance criteria met)
```

## Core idea

Subagents in Claude Code cannot spawn further subagents. So the cycle has to be conducted from the top-level agent's context. This skill loads the procedural cycle into your context — you become the conductor, dispatching specialized subagents stage by stage.

Git worktrees give every architect agent its own complete copy of the repo. Multiple architects can freely edit the same files simultaneously. The consolidator merges everything at the end using full context of every subtask's intent. The planner optimizes for maximum parallelism, the verifier catches mistakes before and after execution.

## Agents

| Agent | Role | When |
|---|---|---|
| **planner** | Decomposes tasks, maps dependencies and parallelism | Stage 1 |
| **verifier** | Validates plans pre-execution, confirms outcomes post-execution | Stages 2 and 6 |
| **architect** | Implements code in worktree isolation | Stage 3 |
| **consolidator** | Merges worktree branches with conflict resolution | Stage 4 |
| **reviewer** | Reviews merged output for quality issues | Stage 5 |

The conducting role lives in `SKILL.md` — load that into your context (auto-triggered by the skill description, or invoked manually) and execute the stages in order.

## When to use

- Multi-file feature implementations
- Large refactors spanning multiple modules
- Batch operations across the codebase
- Any task with 2+ independent units of work
