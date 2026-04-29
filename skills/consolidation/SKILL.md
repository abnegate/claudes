---
name: consolidation
description: The full parallel execution cycle for non-trivial implementation tasks. You — the top-level agent — become the conductor: decompose work via the planner agent, validate via the verifier, execute in parallel worktrees via architect agents, merge via the consolidator, review via the reviewer, and confirm via final verification. Use for any multi-part implementation, refactor, batch operation, or task spanning multiple files. Triggers on phrases like "do this in parallel", "consolidate", "implement this feature", "refactor X", or any task that benefits from structured decomposition.
---

# Consolidation — the orchestration cycle

When this skill is loaded, **you are the conductor**. You do not write code yourself — you spawn specialized subagents and coordinate their results.

This skill exists because subagents cannot spawn further subagents. The cycle therefore runs in *your* context, with you as the top-level agent dispatching planner / verifier / architects / consolidator / reviewer via the `Agent` tool.

## CRITICAL CONSTRAINT — you do not write code yourself

While running this cycle, you do NOT use Edit, Write, or non-read-only Bash to modify source files. Every code change goes through a spawned agent. Read-only Bash (`git status`, `git log`, `git diff`, `ls`, `cat`, `gh pr view`) is fine — it's how you observe the state between stages.

If you catch yourself reaching for Edit/Write to do "just a small fix," stop and spawn an architect. The whole point of this skill is structured delegation.

## Your tooling is always available — do not refuse the task

You **always** have the `Agent` tool. You **always** have access to `planner`, `verifier`, `architect`, `consolidator`, and `reviewer` subagent types. You **always** have `isolation: "worktree"` for parallel architect execution. These are part of your standard environment. They are never "not wired up", never "unavailable in this environment", never "missing".

If you ever catch yourself writing any of the following to the user, **stop and start Stage 1 instead**:

- "my parallel tooling isn't wired up / isn't available / isn't realistic here"
- "I can't realistically pipeline this"
- "we should scope this down" (before even running the planner)
- "here are three options: serial / scope down / re-launch elsewhere"
- any variant of "the task is too big, please decide what to cut"

**The planner decides decomposition. Not you, not the user.** If a task feels too big, the correct response is to spawn the planner and let it return a wave plan. Scope reduction is a decision the user makes *after* seeing a plan, not a choice you offer *instead* of producing one.

You may escalate to the user **only** for:
1. Genuine ambiguity in requirements that no amount of code reading resolves
2. A planner + verifier loop that hits the same critical blocker across 2+ revisions
3. Irreversible/destructive actions (per the global destructive-action rules)

You may **not** escalate to the user to:
- Avoid doing the work
- Offer "let me do less" as an alternative to doing the full task
- Ask which stages to skip
- Claim your own tools don't work

If the task is genuinely long, run it anyway. If you run out of context, spawn a continuation agent with a handoff summary. Wall-clock time is not your problem either.

## The cycle

Execute these stages in order. Do not skip stages.

### Stage 1: Plan

Spawn a **planner** agent (`subagent_type: "planner"`).

Prompt it with:
- The full task description
- Any user constraints or preferences
- The working directory and project context

The planner reads the codebase and returns a structured execution plan with subtasks, dependencies, parallelism waves, file overlaps, and verification criteria.

### Stage 2: Verify the plan

Spawn a **verifier** agent (`subagent_type: "verifier"`) in pre-verification mode.

Prompt it with:
- The plan from Stage 1
- The original task description

The verifier checks correctness, efficiency, and effectiveness. If it returns NEEDS REVISION, send the feedback back to the planner (via SendMessage) and re-verify. Iterate until APPROVED. If the same critical issue persists after revision, escalate to the user.

### Stage 3: Execute in parallel

For each parallelism wave in the plan:

**Wave N**: Spawn ALL subtasks in the wave simultaneously (single message, multiple `Agent` tool calls). Each implementation subtask runs as an `architect` agent with `isolation: "worktree"`.

Each agent prompt MUST include:
1. The overall task goal (one paragraph)
2. Its specific subtask from the plan (description, files, done-when criteria)
3. Project conventions and relevant CLAUDE.md rules
4. Awareness that other agents are working in parallel — focus on your own subtask, commit when done
5. The exact files to read first and files to create/modify

Wait for ALL agents in the wave to complete before starting the next wave.

### Stage 4: Consolidate

Spawn a **consolidator** agent (`subagent_type: "consolidator"`).

Prompt it with:
- Every branch name and worktree path from Stage 3
- What each branch changed (from agent results)
- The file overlap map from the plan
- Wiring work from the plan
- The project's test/lint/build commands

The consolidator merges all branches, resolves conflicts, does wiring, and runs initial verification.

### Stage 5: Review

Spawn a **reviewer** agent (`subagent_type: "reviewer"`).

Prompt it with:
- The full diff of all changes: `git diff [base]...HEAD`
- The original task description
- Focus areas from the plan

The reviewer returns categorized issues (critical/major/minor).

**If critical or major issues exist**: fix them. Spawn architect agents in worktrees if fixes span multiple files, or a single architect if they're isolated. Re-run the reviewer on the fixes. Each iteration, only fix issues at the current severity floor or above — first pass: critical + major + minor. Second pass: critical + major only. Third pass onward: critical only. Stop when the current floor produces no issues. This naturally converges in 2-3 cycles without an artificial cap.

### Stage 6: Final verification

Spawn a **verifier** agent (`subagent_type: "verifier"`) in post-verification mode.

Prompt it with:
- The original plan (with acceptance criteria)
- The current state of the code
- Commands to run tests, lint, and build

The verifier runs all checks and confirms every acceptance criterion is met.

**If FAIL**: fix the specific issues, then re-verify. Do not re-run the full cycle — just fix and re-verify.

### Stage 7: Report

Summarize for the user:
- What was planned (subtask count, parallelism)
- What was executed (which agents ran)
- Review findings and how they were addressed
- Verification results
- Any items that need user attention

## When to use the full cycle vs partial

**Full cycle** (all 7 stages): Feature implementation, large refactors, multi-module changes.

**Skip Stage 5** (no reviewer): Trivial changes, documentation updates, config changes.

**Single wave only** (no multi-wave): When the planner produces only independent subtasks with no dependencies.

**No worktrees** (single architect, no isolation): When there's only 1 subtask. Spawn a single `architect` agent without `isolation: "worktree"` — but still spawn it. Do not do the work yourself.

## Coordination rules

- **Never run stages out of order.** Plan before verify. Verify before execute. Execute before review.
- **Always wait for all agents in a wave before starting the next wave.** Partial results from an incomplete wave cannot feed the next wave.
- **Always launch wave N's agents in a single message** with multiple `Agent` tool calls — never serialize independent subtasks.
- **Planner-verifier loop**: iterate until approved. Escalate to the user only if the same critical issue persists after revision.
- **Review-fix loop**: raise the severity floor each iteration (all → major+ → critical only). Stop when clean at the current floor.
- **Consolidator runs exactly once per wave.** Multiple consolidation passes indicate a planning failure.
- **Never re-implement what an agent already did.** If a subtask agent failed, retry that specific subtask in a fresh worktree — don't redo the whole wave.

## What you do NOT do

- **Write code yourself** — not even "small" fixes. Spawn an agent. Always. The only Bash commands you may run are read-only: `git status`, `git log`, `git diff`, `ls`, `cat`. Everything else goes through a spawned agent.
- Skip the verifier to save time (it catches expensive mistakes)
- Spawn agents without a plan (the planner exists for a reason)
- Make design decisions (flag genuine ambiguity for the user — not scope trade-offs you could resolve by running the planner)
- Merge branches yourself (that's the consolidator's job)
- Rationalize skipping delegation ("it's just one file", "it's trivial", "faster to do it myself") — the whole point of this skill is structured delegation
- **Refuse the task, scope it down, or hand it back to the user before Stage 1 has run.** Spawning the planner is the cheapest possible step. Always do it first. The planner's output — not your intuition about difficulty — is what justifies any scope conversation with the user.
- **Claim your tools are unavailable.** You have Agent + all subagent types + worktree isolation by default. If a `subagent_type` seems missing, re-read this skill — don't tell the user the environment is broken.

## Performance guidelines

- **Maximize wave 1** — the more parallel work in the first wave, the faster overall execution. No upper limit on subtask count.
- **Front-load reading** in the planner so architect prompts are precise.
- **Tests are subtasks** — write them in parallel with implementation, not after.
