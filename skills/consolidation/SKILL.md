---
name: consolidation
description: The full parallel execution cycle for non-trivial tasks. Orchestrator decomposes work via the planner, validates via the verifier, executes in parallel worktrees via architect agents, merges via the consolidator, reviews via reviewer, and confirms via final verification. Use for any multi-part implementation, refactor, or batch operation. Triggers on phrases like "do this in parallel", "consolidate", "implement this feature", or any task that benefits from structured decomposition.
---

# Consolidation

The structured cycle for executing non-trivial tasks with maximum parallelism and quality.

## The agent cycle

```
orchestrator
  -> planner        (decompose task into subtasks)
  -> verifier       (validate plan correctness + efficiency)
  -> architects     (parallel worktree execution)
  -> consolidator   (merge all branches)
  -> reviewer       (review merged output)
  -> verifier       (confirm acceptance criteria met)
```

Each agent has a single responsibility. The **orchestrator** coordinates. See `agents/` for each agent's full definition.

## When to use the full cycle

- Multi-file feature implementations
- Large refactors spanning multiple modules
- Batch operations across the codebase
- Any task with 2+ independent units of work

## When to use a partial cycle

- **Skip reviewer**: trivial changes, docs, config
- **Skip worktrees**: single subtask (no parallelism benefit)
- **Planner + verifier only**: when you need a plan but the user will execute manually

## When NOT to use

- Single-file edits that finish in seconds
- Pure research/analysis tasks (no code changes)

## Quick reference

### Spawning the cycle

For any qualifying task, spawn the orchestrator:

```
Agent({
  description: "Orchestrate: [task summary]",
  subagent_type: "orchestrator",
  prompt: "[full task description with context]"
})
```

The orchestrator handles everything from there — planning, verification, parallel execution, consolidation, review, and final checks.

### Manual cycle (when you need finer control)

If you need to run stages individually:

**1. Plan:**
```
Agent({
  description: "Plan: [task]",
  subagent_type: "planner",
  prompt: "[task + codebase context]"
})
```

**2. Verify plan:**
```
Agent({
  description: "Verify plan",
  subagent_type: "verifier",
  prompt: "[plan output + original task]"
})
```

**3. Execute (parallel worktrees):**
```
Agent({
  description: "Subtask 1: [name]",
  subagent_type: "architect",
  isolation: "worktree",
  prompt: "[subtask details from plan]"
})
// ... launch all wave-1 subtasks simultaneously
```

**4. Consolidate:**
```
Agent({
  description: "Consolidate branches",
  subagent_type: "consolidator",
  prompt: "[branch list + overlap map + wiring work]"
})
```

**5. Review:**
```
Agent({
  description: "Review changes",
  subagent_type: "reviewer",
  prompt: "[diff + task description]"
})
```

**6. Final verify:**
```
Agent({
  description: "Final verification",
  subagent_type: "verifier",
  prompt: "[plan acceptance criteria + verification commands]"
})
```

## Edge cases

**Planner-verifier loop**: max 2 revision rounds. If the plan still has critical issues, ask the user.

**Subtask agent fails**: don't block consolidation of successful branches. Retry the failed subtask in a fresh worktree.

**Code-griller finds critical issues**: fix them (in worktrees if multi-file), re-review. Max 2 review cycles.

**Verifier fails post-execution**: fix specific failures and re-verify. Don't re-run the full cycle.

## Performance guidelines

- **Maximize wave 1** — the more parallel work in the first wave, the faster overall execution. No upper limit on subtask count.
- **Front-load reading** in the planner so architect prompts are precise
- **Tests are subtasks** — write them in parallel with implementation, not after
