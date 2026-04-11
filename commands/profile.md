---
name: profile
description: Build a comprehensive developer profile from git activity and Claude Code session history. Covers commit patterns, velocity, streaks, time-of-day habits, repo focus, tool usage, AI spend, model preferences, and session themes. Use whenever the user asks about their stats, coding patterns, what they've been working on, their Claude usage, or anything related to their developer profile.
---

# Developer Profile

Build a comprehensive developer profile by combining git commit activity with Claude Code session data. The result paints a full picture: what you build, when you build it, how you use AI assistance, and where your focus goes.

## How it works

A collection script at `scripts/collect.py` in the plugin/repo root scans git repos for commit metadata and reads Claude Code session files from `~/.claude/sessions/`. It outputs a single JSON payload with two top-level sections: `git` and `claude`.

## Step 1: Collect the data

Locate the script. It lives at `scripts/collect.py` relative to the plugin root (sibling to `commands/`). If the path isn't obvious, use Glob with `**/scripts/collect.py` under `~/.claude/plugins/cache/claudes/` or the repo checkout to find it.

Run it. The base directory defaults to `~/Local/` unless the user specifies otherwise. The script auto-detects the git author and defaults to the last 90 days.

```bash
python3 <plugin-root>/scripts/collect.py ~/Local/ --format json
```

Override if the user asks for a different time range or author:

```bash
python3 <plugin-root>/scripts/collect.py ~/Local/ --since 2025-01-01 --author "Someone Else"
```

## Step 2: Interpret and present

The JSON output has two top-level keys: `git` and `claude`. Use **both** to build a unified profile. Cross-reference them — the most interesting insights come from correlating the two (e.g., "You use Claude most heavily on the repos where you commit the most fixes" or "Your Claude sessions peak at 22:00, exactly when your commit volume spikes").

### Git section (`git`)

#### Summary
- Total commits, active repos, date range, commits per day
- Weekend vs weekday split — surface this if skewed
- Busiest single day — call it out with context

#### Streaks
- Current streak and longest streak
- If the current streak is strong, celebrate it. If it broke recently, note when.

#### Repo breakdown (`by_repo`)
- Rank by commit volume. Group into tiers: heavy focus, moderate, light touch.
- Call out repos that appeared suddenly (new projects) or went silent.

#### Weekly/monthly trends (`by_week`, `by_month`)
- Spot acceleration or deceleration. Which weeks were peak output?
- Correlate spikes with specific repos using `by_repo_week`.

#### Time-of-day patterns (`by_hour`, `by_time_bucket`)
- Early bird or night owl?
- Distinct work sessions (morning burst, evening push)?
- Use `by_repo_hour` to see if different repos get worked on at different times.

#### Day-of-week patterns (`by_day_of_week`)
- Which days are heaviest? Weekend work?
- Surprising gaps?

#### Commit types (`by_type`)
- Features vs fixes vs refactors vs chores?
- Use `by_repo_type` to show how work type varies by project.

#### Vocabulary (`top_words`)
- Domain themes from commit messages.

#### Repo context (`repo_context`)
- **branch**: Current branch name — reveals active work.
- **recent_subjects**: Last 20 commit subjects — summarize themes in plain language.
- **uncommitted**: Modified/untracked files — hints at active WIP.

### Claude section (`claude`)

#### Summary
- Total sessions, **estimated cost** (pay-as-you-go rates, not actual spend on flat-rate plans — note this when presenting)
- Total turns, average turns per session
- Total tool calls, average tools per session
- Active days and sessions per active day

#### Duration (`duration`)
- Median, average, and max session length in minutes
- Total hours spent in Claude Code

#### Data sources (`data_sources`)
Each session is tagged with how its data survived:
- **main+subagent** — both parent session file and subagent data present (recent sessions)
- **main-only** — only the parent session file
- **subagent-only** — parent was cleaned up by Claude Code's retention, only subagent data survived

A high `subagent-only` count for older periods (Jan–Feb 2026 and earlier) is **expected** — Claude Code silently cleans up older `projects/*.jsonl` files but leaves `subagents/` subdirs alone. For periods before the subagent feature started persisting (~Jan 9, 2026), neither survives, which is why you may see gaps in Nov–Dec 2025 even though `history.jsonl` has entries for that range.

If the user asks about gaps in the timeline, explain this cleanup behavior. Don't pretend the gap is because they weren't using Claude — they were, the data just got purged.

#### Models (`models`)
- Which models are used and how often. Is the user an Opus user, a Sonnet user, or do they switch based on context?
- `<synthetic>` entries are Claude Code's internal messages (hooks, system events) — not real API calls. Note their share but don't attribute cost to them.

#### Tool usage (`tools`)
- Ranked tool counts. Which tools dominate (Bash, Read, Edit, Grep, Glob, Agent, etc.)?
- High Bash usage suggests scripting-heavy workflows; high Agent usage suggests delegation patterns; high Edit vs Write suggests iterative refinement.

#### Skills (`skills`)
- Which slash commands / skills are invoked. Shows workflow preferences.

#### By project (`by_project`)
- Sessions, cost, turns, and tool calls per project.
- Cross-reference with git `by_repo` — which repos get the most AI assistance relative to their commit volume? A repo with many commits but few Claude sessions is "manual" work; one with few commits but many sessions is "AI-assisted" or exploratory.

#### By project hour (`by_project_hour`)
- Do different projects get Claude help at different times?

#### Hourly / daily / weekly patterns (`by_hour`, `by_day_of_week`, `by_week`)
- Compare with git patterns. Do Claude sessions happen at the same hours as commits, or different?
- Claude-heavy weeks vs commit-heavy weeks — do they correlate or alternate?

#### Cost trends (`cost_by_week`)
- Spending trajectory. Increasing, stable, or decreasing?
- Correlate spikes with specific projects or high-commit weeks.

#### Session vocabulary (`top_session_words`)
- What themes emerge from session titles? Domain terms, action words.
- Compare with git commit vocabulary — are the same themes present, or does Claude get used for different work than what gets committed?

## Presentation guidelines

Lead with 3-5 bold headline insights. The best insights **cross-reference** git and Claude data:
- "You spent $X on Claude this month, mostly on [project] — which is also your highest-commit repo"
- "Your Claude sessions peak at 1am but your commits peak at 10pm — you research late, commit earlier"
- "You use Opus for [project] but Sonnet for [project] — the complex backend gets the big model"
- "[Project] has 3x more Claude sessions per commit than any other repo — heavy AI assistance there"

After the headlines, present two detailed sections (Git Activity, Claude Usage) with tables and plain language analysis. Then a combined "Cross-reference" section that ties the two together.

If the user asks for CSV output, run the script with `--format csv` instead — this outputs the git repo-weekly grid only.

Keep it concrete. Reference specific repos, weeks, numbers, and dollar amounts. Avoid filler.
