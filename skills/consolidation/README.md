# consolidation

The structured cycle for executing non-trivial tasks with maximum parallelism and quality.

## The cycle

```
[top-level conductor — you, with this skill loaded]
  -> planner        (decompose task into subtasks, optionally workstreams)
  -> verifier       (validate plan correctness + efficiency)
  -> architects     (parallel worktree execution)
     or conductors  (optional: one per workstream, each running this
                     whole cycle on its own ws-<workstream> branch)
  -> consolidator   (merge all branches)
  -> reviewer       (review merged output)
  -> verifier       (confirm acceptance criteria met)
```

## Core idea

This skill loads the procedural cycle into the conducting agent's context. The top-level conductor (the user-facing session) conducts by default, dispatching the stage agents stage by stage. When nesting is warranted, it delegates each independent workstream to a `conductor` subagent that runs the same cycle on its own `ws-<workstream>` integration branch and hands back a Workstream report. By default subagents nest up to depth 3 (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`) and at most 20 run at once across the whole session (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), so conductors split that concurrency budget and launch larger waves in batches.

Git worktrees give every architect agent its own complete copy of the repo, branched from BASE (the integration branch HEAD at wave start). Multiple architects can freely edit the same files simultaneously. The consolidator merges everything at the end using full context of every subtask's intent. The planner optimizes for maximum parallelism, the verifier catches mistakes before and after execution.

## Agents

| Agent | Role | When |
|---|---|---|
| **planner** | Decomposes tasks, maps dependencies, parallelism and workstreams | Stage 1 |
| **verifier** | Validates plans pre-execution, confirms outcomes post-execution | Stages 2 and 6 |
| **architect** | Implements code in its own worktree | Stage 3 |
| **conductor** | Runs the whole cycle for one workstream and hands back a Workstream report | Stage 3 of a nested run |
| **consolidator** | Merges worktree branches with conflict resolution | Stage 4 |
| **reviewer** | Reviews merged output for quality issues | Stage 5 |

The conducting role lives in `SKILL.md`. The top-level conductor loads it (auto-triggered by the skill description, or invoked manually) and executes the stages in order; each `conductor` agent preloads it and does the same for its workstream.

## When to use

- Multi-file feature implementations
- Large refactors spanning multiple modules
- Batch operations across the codebase
- Any task with 2+ independent units of work
- Multi-repo tasks, or tasks that split into independent workstreams (nested conductors)
