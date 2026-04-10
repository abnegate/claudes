---
name: insights
description: Analyze git commit activity across all repos in a directory. Generates comprehensive stats (commit counts, time-of-day patterns, velocity, streaks, commit types, top keywords) and surfaces highlights and insights. Use this skill whenever the user asks about their git activity, commit history, coding patterns, productivity stats, repo breakdown, or weekly/monthly commit summaries — even if they just say something like "what have I been working on" or "show me my stats".
---

# Repo Stats

Analyze git commit activity across all local repos and present insights about coding patterns, velocity, and focus areas.

## How it works

There is a data collection script at `scripts/collect.py` (relative to this skill file) that scans all git repos under a base directory, extracts commit metadata, and outputs a JSON payload with aggregated stats. Run the script, then interpret the results and present highlights.

## Step 1: Collect the data

Run the collection script. The base directory defaults to `~/Local/` unless the user specifies otherwise. The script auto-detects the git author and defaults to the last 90 days.

```bash
python3 <skill-dir>/scripts/collect.py ~/Local/ --format json
```

Override if the user asks for a different time range or author:

```bash
python3 <skill-dir>/scripts/collect.py ~/Local/ --since 2025-01-01 --author "Someone Else"
```

## Step 2: Interpret and present

The JSON output contains these sections — use all of them to build a complete picture:

### Summary section
- Total commits, active repos, date range, commits per day
- Weekend vs weekday split — surface this if skewed
- Busiest single day — call it out with context

### Streaks
- Current streak and longest streak — people love streak data
- If the current streak is strong, celebrate it. If it broke recently, note when.

### Repo breakdown (`by_repo`)
- Rank by commit volume. Group into tiers: heavy focus, moderate, light touch.
- Call out any repos that appeared suddenly (new projects) or went silent.

### Weekly/monthly trends (`by_week`, `by_month`)
- Spot acceleration or deceleration. Which weeks were peak output?
- Correlate spikes with specific repos if possible using `by_repo_week`.

### Time-of-day patterns (`by_hour`, `by_time_bucket`)
- When is the user most productive? Early bird or night owl?
- Are there distinct work sessions (e.g., morning burst, evening push)?
- Use `by_repo_hour` to see if different repos get worked on at different times.

### Day-of-week patterns (`by_day_of_week`)
- Which days are heaviest? Does the user work weekends?
- Any surprising gaps (e.g., zero commits on a weekday)?

### Commit types (`by_type`)
- What kind of work dominates: features, fixes, refactors, chores?
- Use `by_repo_type` to show how work type varies by project.

### Vocabulary (`top_words`)
- What themes emerge from commit messages? Domain-specific terms reveal focus areas.

### Repo context (`repo_context`)
Each active repo includes qualitative context that adds depth beyond the numbers:
- **branch**: The current branch name. Branch names often reveal what's actively being worked on (e.g., `feat-dedicated-db`, `fix-multi-vcs-deploy`). Group repos by shared branch names to surface cross-repo features.
- **recent_subjects**: The last 20 commit subjects. Skim these to identify themes and summarize what each repo has been focused on in plain language (e.g., "database adapter refactoring and backup/restore work" rather than listing commit messages).
- **uncommitted**: Any modified, added, or untracked files. This shows work-in-progress that hasn't been committed yet. Call out notable uncommitted work — it hints at what the user is actively touching right now.

Use this context to add a "What's happening in each repo" section that goes beyond commit counts and explains the actual work.

## Presentation guidelines

Lead with 3-5 bold headline insights — the things that would surprise or interest the user most. Not generic stats, but patterns: "You're a night owl on plotpals but a morning person on appwrite" or "Your commit velocity doubled after W11".

After the headlines, present the detailed breakdown. Use tables for the repo-by-week grid and commit type distributions. Use plain language for trend analysis.

If the user asks for CSV output, run the script with `--format csv` instead and output the raw CSV.

Keep it concrete. Reference specific repos, weeks, and numbers. Avoid filler like "you've been busy!" — let the data speak.
