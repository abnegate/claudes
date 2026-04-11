#!/usr/bin/env python3
"""
Collect comprehensive developer profile data from git repos and Claude Code sessions.

Usage: python collect.py <base_dir> [--author <name>] [--since <date>] [--format csv|json]

Outputs JSON (default) or CSV with rich commit metadata and Claude usage data.
"""

import argparse
import glob as globmod
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def find_repos(base_dir, max_depth=3):
    """Find all git repositories under base_dir."""
    repos = []
    base = Path(base_dir).resolve()
    for root, dirs, files in os.walk(base):
        depth = len(Path(root).relative_to(base).parts)
        if depth >= max_depth:
            dirs.clear()
            continue
        if '.git' in dirs:
            repos.append(root)
            dirs.remove('.git')
    return sorted(repos)


def detect_author(repos):
    """Detect the git author from repo config."""
    for repo in repos:
        try:
            name = subprocess.check_output(
                ['git', '-C', repo, 'config', 'user.name'],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            if name:
                return name
        except subprocess.CalledProcessError:
            continue
    return None


def collect_commits(repo_path, author, since):
    """Collect commits from a single repo with rich metadata."""
    fmt = '%H%x00%aI%x00%aN%x00%aE%x00%s'
    try:
        args = ['git', '-C', repo_path, 'log', f'--author={author}',
                f'--since={since}', f'--format={fmt}', '--all']
        output = subprocess.check_output(args, stderr=subprocess.DEVNULL, text=True)
    except subprocess.CalledProcessError:
        return []

    commits = []
    for line in output.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\x00')
        if len(parts) < 5:
            continue
        hash_, date_iso, name, email, subject = parts[0], parts[1], parts[2], parts[3], parts[4]
        try:
            dt = datetime.fromisoformat(date_iso)
        except ValueError:
            continue
        commits.append({
            'hash': hash_[:8],
            'datetime': date_iso,
            'date': dt.strftime('%Y-%m-%d'),
            'time': dt.strftime('%H:%M'),
            'hour': dt.hour,
            'weekday': dt.strftime('%A'),
            'weekday_num': dt.isoweekday(),
            'week': dt.strftime('%Y-W%V'),
            'month': dt.strftime('%Y-%m'),
            'subject': subject,
        })
    return commits


def collect_repo_context(repo_path):
    """Collect qualitative context: branch, recent subjects, uncommitted work."""
    context = {}

    try:
        branch = subprocess.check_output(
            ['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        context['branch'] = branch
    except subprocess.CalledProcessError:
        context['branch'] = None

    try:
        status = subprocess.check_output(
            ['git', '-C', repo_path, 'status', '--porcelain'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if status:
            lines = status.split('\n')
            modified = [l[3:] for l in lines if l[:2] in (' M', 'M ', 'MM')]
            added = [l[3:] for l in lines if l[:2] in ('A ', 'AM')]
            untracked = [l[3:] for l in lines if l[:2] == '??']
            context['uncommitted'] = {}
            if modified:
                context['uncommitted']['modified'] = modified
            if added:
                context['uncommitted']['added'] = added
            if untracked:
                context['uncommitted']['untracked'] = untracked
    except subprocess.CalledProcessError:
        pass

    try:
        output = subprocess.check_output(
            ['git', '-C', repo_path, 'log', '-20', '--format=%s', '--all'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if output:
            context['recent_subjects'] = output.split('\n')
    except subprocess.CalledProcessError:
        pass

    return context


def classify_commit(subject):
    """Classify a commit message by conventional commit type."""
    lower = subject.lower().strip()
    prefixes = [
        'feat', 'fix', 'refactor', 'chore', 'docs', 'test',
        'style', 'perf', 'ci', 'build', 'revert', 'wip'
    ]
    for prefix in prefixes:
        if lower.startswith(prefix + ':') or lower.startswith(prefix + '('):
            return prefix
    if lower.startswith('merge'):
        return 'merge'
    if lower.startswith('add') or lower.startswith('implement') or lower.startswith('create'):
        return 'feat'
    if lower.startswith('fix') or lower.startswith('bug') or lower.startswith('patch'):
        return 'fix'
    if lower.startswith('update') or lower.startswith('improve') or lower.startswith('enhance'):
        return 'improvement'
    if lower.startswith('remove') or lower.startswith('delete') or lower.startswith('clean'):
        return 'cleanup'
    if lower.startswith('refactor') or lower.startswith('restructure') or lower.startswith('reorgani'):
        return 'refactor'
    return 'other'


def compute_streaks(dates):
    """Compute commit streaks from a sorted list of date strings."""
    if not dates:
        return {'current': 0, 'longest': 0, 'longest_start': None, 'longest_end': None}

    unique_dates = sorted(set(dates))
    parsed = [datetime.strptime(d, '%Y-%m-%d') for d in unique_dates]

    streaks = []
    start = parsed[0]
    prev = parsed[0]
    for d in parsed[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            streaks.append((start, prev))
            start = d
            prev = d
    streaks.append((start, prev))

    longest = max(streaks, key=lambda s: (s[1] - s[0]).days + 1)
    longest_len = (longest[1] - longest[0]).days + 1

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    last_streak = streaks[-1]
    if (today - last_streak[1]).days <= 1:
        current = (last_streak[1] - last_streak[0]).days + 1
    else:
        current = 0

    return {
        'current': current,
        'longest': longest_len,
        'longest_start': longest[0].strftime('%Y-%m-%d'),
        'longest_end': longest[1].strftime('%Y-%m-%d'),
    }


def parse_timestamp(ts):
    """Parse a timestamp that may be an ISO string or numeric epoch."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None
    return None


# Approximate Claude API pricing per million tokens (as of early 2026).
# Used to estimate cost from token usage when sessions don't record cost directly.
MODEL_PRICING = {
    'opus': {'input': 15.0, 'output': 75.0, 'cache_write': 18.75, 'cache_read': 1.5},
    'sonnet': {'input': 3.0, 'output': 15.0, 'cache_write': 3.75, 'cache_read': 0.3},
    'haiku': {'input': 1.0, 'output': 5.0, 'cache_write': 1.25, 'cache_read': 0.1},
}


def estimate_cost(model, usage):
    """Estimate USD cost from model name and usage dict."""
    if not usage or not model:
        return 0.0
    tier = 'sonnet'
    model_lower = model.lower()
    if 'opus' in model_lower:
        tier = 'opus'
    elif 'haiku' in model_lower:
        tier = 'haiku'
    price = MODEL_PRICING[tier]
    inp = usage.get('input_tokens', 0) or 0
    out = usage.get('output_tokens', 0) or 0
    cache_write = usage.get('cache_creation_input_tokens', 0) or 0
    cache_read = usage.get('cache_read_input_tokens', 0) or 0
    return (
        inp * price['input']
        + out * price['output']
        + cache_write * price['cache_write']
        + cache_read * price['cache_read']
    ) / 1_000_000


def collect_claude_sessions(since_date):
    """Collect Claude Code session data from ~/.claude/projects/**/*.jsonl.

    Groups main session files and their subagent files into single logical sessions
    keyed by the sessionId field inside the JSONL entries. This is required because
    Claude Code periodically cleans up main session .jsonl files but leaves
    subagents/ subdirs intact, so many older sessions only survive as subagent data.
    """
    projects_dir = Path.home() / '.claude' / 'projects'
    if not projects_dir.exists():
        return []

    since_dt = datetime.fromisoformat(since_date) if isinstance(since_date, str) else since_date

    # Keyed by sessionId (falls back to parent-dir uuid for subagents without sessionId)
    sessions = {}

    for path in projects_dir.rglob('*.jsonl'):
        is_subagent = 'subagents' in path.parts

        # Derive the parent session ID from the path:
        # - main file:  projects/<proj>/<sid>.jsonl  -> sid
        # - subagent:   projects/<proj>/<sid>/subagents/agent-XXX.jsonl  -> sid
        if is_subagent:
            try:
                sid_from_path = path.parent.parent.name
            except IndexError:
                sid_from_path = path.stem
        else:
            sid_from_path = path.stem

        try:
            file_contents = open(path).readlines()
        except OSError:
            continue

        for line in file_contents:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get('type')
            if entry_type not in ('user', 'assistant'):
                continue

            sid = entry.get('sessionId') or sid_from_path
            timestamp = parse_timestamp(entry.get('timestamp'))
            if timestamp is None:
                continue
            if timestamp < since_dt:
                continue

            if sid not in sessions:
                sessions[sid] = {
                    'id': sid,
                    'first_timestamp': timestamp,
                    'last_timestamp': timestamp,
                    'user_messages': 0,
                    'assistant_messages': 0,
                    'tool_calls': [],
                    'skills_used': [],
                    'models': set(),
                    'cost': 0.0,
                    'cwd': entry.get('cwd', ''),
                    'project': os.path.basename(entry.get('cwd', '')) if entry.get('cwd') else '',
                    'git_branches': set(),
                    'has_subagent_data': False,
                    'has_main_data': False,
                }

            session = sessions[sid]
            if is_subagent:
                session['has_subagent_data'] = True
            else:
                session['has_main_data'] = True

            if timestamp < session['first_timestamp']:
                session['first_timestamp'] = timestamp
            if timestamp > session['last_timestamp']:
                session['last_timestamp'] = timestamp

            if entry.get('cwd') and not session['cwd']:
                session['cwd'] = entry['cwd']
                session['project'] = os.path.basename(entry['cwd'])
            if entry.get('gitBranch'):
                session['git_branches'].add(entry['gitBranch'])

            if entry_type == 'user':
                session['user_messages'] += 1
            else:
                session['assistant_messages'] += 1

            message = entry.get('message', {})
            if not isinstance(message, dict):
                continue

            model = message.get('model')
            if model:
                session['models'].add(model)

            usage = message.get('usage', {})
            if usage:
                session['cost'] += estimate_cost(model or '', usage)

            content = message.get('content', [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use':
                    tool_name = block.get('name', '')
                    session['tool_calls'].append(tool_name)
                    if tool_name == 'Skill':
                        skill = (block.get('input') or {}).get('skill', '')
                        if skill:
                            session['skills_used'].append(skill)

    # Finalize sessions into the expected shape
    result = []
    for session in sessions.values():
        created_dt = session['first_timestamp']
        last_dt = session['last_timestamp']
        duration_minutes = round((last_dt - created_dt).total_seconds() / 60, 1)

        result.append({
            'id': session['id'],
            'created': created_dt.isoformat(),
            'date': created_dt.strftime('%Y-%m-%d'),
            'hour': created_dt.hour,
            'weekday': created_dt.strftime('%A'),
            'week': created_dt.strftime('%Y-W%V'),
            'month': created_dt.strftime('%Y-%m'),
            'model': next(iter(session['models'])) if session['models'] else 'unknown',
            'models': sorted(session['models']),
            'cost': round(session['cost'], 4),
            'turns': session['user_messages'],
            'user_messages': session['user_messages'],
            'assistant_messages': session['assistant_messages'],
            'tool_calls': session['tool_calls'],
            'tool_count': len(session['tool_calls']),
            'skills_used': session['skills_used'],
            'project': session['project'],
            'git_branches': sorted(session['git_branches']),
            'title': '',
            'duration_minutes': duration_minutes,
            'source': 'main+subagent' if (session['has_main_data'] and session['has_subagent_data'])
                     else 'subagent-only' if session['has_subagent_data']
                     else 'main-only',
        })

    return sorted(result, key=lambda s: s['created'])


def analyze_claude_sessions(sessions):
    """Produce aggregate analysis from Claude session data."""
    if not sessions:
        return None

    total = len(sessions)
    total_cost = sum(s['cost'] for s in sessions)
    total_turns = sum(s['turns'] for s in sessions)
    total_tools = sum(s['tool_count'] for s in sessions)

    dates = [s['date'] for s in sessions]
    min_date = min(dates)
    max_date = max(dates)
    unique_days = len(set(dates))

    # Tool usage across all sessions
    all_tools = []
    for s in sessions:
        all_tools.extend(s['tool_calls'])
    tool_counts = dict(Counter(all_tools).most_common(30))

    # Skills used
    all_skills = []
    for s in sessions:
        all_skills.extend(s['skills_used'])
    skill_counts = dict(Counter(all_skills).most_common(20))

    # Model usage (each session can span multiple models, so count by 'models' list)
    model_counts = Counter()
    for s in sessions:
        for model in s.get('models') or [s['model']]:
            model_counts[model] += 1
    model_counts = dict(model_counts.most_common())

    # Data source breakdown (main+subagent / subagent-only / main-only)
    source_counts = dict(Counter(s.get('source', 'unknown') for s in sessions).most_common())

    # Per-project breakdown
    project_counts = Counter(s['project'] for s in sessions if s['project'])
    project_stats = {}
    for project, count in project_counts.most_common():
        project_sessions = [s for s in sessions if s['project'] == project]
        project_stats[project] = {
            'sessions': count,
            'cost': round(sum(s['cost'] for s in project_sessions), 4),
            'turns': sum(s['turns'] for s in project_sessions),
            'tools': sum(s['tool_count'] for s in project_sessions),
        }

    # Hourly distribution
    hourly = Counter(s['hour'] for s in sessions)
    hourly_full = {h: hourly.get(h, 0) for h in range(24)}

    # Day of week
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily = Counter(s['weekday'] for s in sessions)
    daily_sorted = {d: daily.get(d, 0) for d in day_order}

    # Weekly trend
    weekly = Counter(s['week'] for s in sessions)
    weekly_sorted = dict(sorted(weekly.items()))

    # Monthly trend
    monthly = Counter(s['month'] for s in sessions)
    monthly_sorted = dict(sorted(monthly.items()))

    # Daily session counts
    daily_counts = Counter(dates)
    daily_sorted_counts = dict(sorted(daily_counts.items()))

    # Sessions with durations
    durations = [s['duration_minutes'] for s in sessions if s['duration_minutes'] is not None and s['duration_minutes'] > 0]
    duration_stats = None
    if durations:
        durations_sorted = sorted(durations)
        duration_stats = {
            'median_minutes': round(durations_sorted[len(durations_sorted) // 2], 1),
            'average_minutes': round(sum(durations) / len(durations), 1),
            'max_minutes': round(max(durations), 1),
            'total_hours': round(sum(durations) / 60, 1),
        }

    # Cost by week
    cost_by_week = defaultdict(float)
    for s in sessions:
        cost_by_week[s['week']] += s['cost']
    cost_by_week = {k: round(v, 4) for k, v in sorted(cost_by_week.items())}

    # Per-project hourly patterns
    project_hours = {}
    for project in list(project_counts.keys())[:10]:
        project_sessions = [s for s in sessions if s['project'] == project]
        project_hours[project] = dict(Counter(s['hour'] for s in project_sessions))

    # Title/theme extraction from session titles
    title_words = Counter()
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'to', 'in', 'for', 'of', 'on',
        'with', 'is', 'it', 'from', 'by', 'at', 'as', 'this', 'that',
        'me', 'my', 'i', 'can', 'you', 'how', 'what', 'we', 'do', 'not',
        'all', 'but', 'so', 'if', 'be', 'are', 'was', 'has', 'have',
    }
    for s in sessions:
        title = s.get('title', '')
        if title:
            for word in re.split(r'[\s/\\.,;:!?()\[\]{}"\'-]+', title.lower()):
                if len(word) > 2 and word not in stop_words:
                    title_words[word] += 1
    top_session_words = dict(title_words.most_common(30))

    return {
        'summary': {
            'total_sessions': total,
            'total_cost_usd': round(total_cost, 2),
            'average_cost_per_session': round(total_cost / total, 4) if total else 0,
            'total_turns': total_turns,
            'average_turns_per_session': round(total_turns / total, 1) if total else 0,
            'total_tool_calls': total_tools,
            'average_tools_per_session': round(total_tools / total, 1) if total else 0,
            'date_range': f'{min_date} to {max_date}',
            'unique_active_days': unique_days,
            'sessions_per_active_day': round(total / unique_days, 1) if unique_days else 0,
        },
        'duration': duration_stats,
        'models': model_counts,
        'data_sources': source_counts,
        'tools': tool_counts,
        'skills': skill_counts,
        'by_project': project_stats,
        'by_project_hour': project_hours,
        'by_hour': hourly_full,
        'by_day_of_week': daily_sorted,
        'by_week': weekly_sorted,
        'by_month': monthly_sorted,
        'cost_by_week': cost_by_week,
        'daily_counts': daily_sorted_counts,
        'top_session_words': top_session_words,
    }


def analyze(all_commits, repos_data):
    """Produce aggregate analysis from collected commits."""
    if not all_commits:
        return {'error': 'No commits found'}

    total = len(all_commits)
    dates = [c['date'] for c in all_commits]
    min_date = min(dates)
    max_date = max(dates)
    unique_days = len(set(dates))
    date_range_days = (datetime.strptime(max_date, '%Y-%m-%d') - datetime.strptime(min_date, '%Y-%m-%d')).days + 1

    repo_totals = {repo: len(commits) for repo, commits in repos_data.items() if commits}
    repo_totals = dict(sorted(repo_totals.items(), key=lambda x: -x[1]))

    weekly = Counter(c['week'] for c in all_commits)
    weekly_sorted = dict(sorted(weekly.items()))

    monthly = Counter(c['month'] for c in all_commits)
    monthly_sorted = dict(sorted(monthly.items()))

    hourly = Counter(c['hour'] for c in all_commits)
    hourly_full = {h: hourly.get(h, 0) for h in range(24)}

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily = Counter(c['weekday'] for c in all_commits)
    daily_sorted = {d: daily.get(d, 0) for d in day_order}

    def time_bucket(hour):
        if 5 <= hour < 9:
            return 'early_morning'
        if 9 <= hour < 12:
            return 'morning'
        if 12 <= hour < 14:
            return 'lunch'
        if 14 <= hour < 17:
            return 'afternoon'
        if 17 <= hour < 21:
            return 'evening'
        return 'night'

    buckets = Counter(time_bucket(c['hour']) for c in all_commits)

    types = Counter(classify_commit(c['subject']) for c in all_commits)
    types_sorted = dict(sorted(types.items(), key=lambda x: -x[1]))

    repo_weekly = {}
    for repo, commits in repos_data.items():
        if commits:
            repo_weekly[repo] = dict(Counter(c['week'] for c in commits))

    streaks = compute_streaks(dates)

    daily_counts = Counter(dates)
    daily_counts_sorted = dict(sorted(daily_counts.items()))

    per_active_day = round(total / unique_days, 1) if unique_days else 0

    weekend = sum(1 for c in all_commits if c['weekday'] in ('Saturday', 'Sunday'))
    weekday = total - weekend

    repo_hours = {}
    for repo, commits in repos_data.items():
        if commits:
            repo_hours[repo] = dict(Counter(c['hour'] for c in commits))

    stop_words = {'the', 'a', 'an', 'and', 'or', 'to', 'in', 'for', 'of', 'on', 'with', 'is', 'it', 'from', 'by', 'at', 'as', 'this', 'that'}
    words = Counter()
    for c in all_commits:
        for word in c['subject'].lower().split():
            clean = word.strip('()[]{}.,;:!?"\'-')
            if len(clean) > 2 and clean not in stop_words:
                words[clean] += 1
    top_words = dict(words.most_common(30))

    busiest_day = max(daily_counts.items(), key=lambda x: x[1])

    repo_types = {}
    for repo, commits in repos_data.items():
        if commits:
            repo_types[repo] = dict(Counter(classify_commit(c['subject']) for c in commits))

    return {
        'summary': {
            'total_commits': total,
            'repos_active': len(repo_totals),
            'date_range': f'{min_date} to {max_date}',
            'date_range_days': date_range_days,
            'unique_active_days': unique_days,
            'commits_per_active_day': per_active_day,
            'commits_per_calendar_day': round(total / date_range_days, 1) if date_range_days else 0,
            'weekday_commits': weekday,
            'weekend_commits': weekend,
            'weekend_percentage': round(weekend / total * 100, 1) if total else 0,
            'busiest_day': {'date': busiest_day[0], 'count': busiest_day[1]},
        },
        'streaks': streaks,
        'by_repo': repo_totals,
        'by_week': weekly_sorted,
        'by_month': monthly_sorted,
        'by_hour': hourly_full,
        'by_day_of_week': daily_sorted,
        'by_time_bucket': dict(buckets),
        'by_type': types_sorted,
        'by_repo_week': repo_weekly,
        'by_repo_hour': repo_hours,
        'by_repo_type': repo_types,
        'daily_counts': daily_counts_sorted,
        'top_words': top_words,
    }


def to_csv(analysis):
    """Convert the repo-weekly breakdown to CSV."""
    repo_weekly = analysis.get('by_repo_week', {})
    all_weeks = sorted(set(w for rw in repo_weekly.values() for w in rw))
    repos = sorted(analysis['by_repo'].keys(), key=lambda r: -analysis['by_repo'][r])

    lines = ['Week,' + ','.join(repos) + ',Total']
    for week in all_weeks:
        vals = [str(repo_weekly.get(r, {}).get(week, 0)) for r in repos]
        total = sum(int(v) for v in vals)
        short = week.split('-')[1]
        lines.append(f'{short},' + ','.join(vals) + f',{total}')

    totals = [str(analysis['by_repo'][r]) for r in repos]
    grand = sum(analysis['by_repo'].values())
    lines.append('Total,' + ','.join(totals) + f',{grand}')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Collect developer profile data from git repos and Claude sessions')
    parser.add_argument('base_dir', help='Base directory containing git repos')
    parser.add_argument('--author', help='Git author name (auto-detected if omitted)')
    parser.add_argument('--since', help='Start date (ISO format, default: 3 months ago)')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
    args = parser.parse_args()

    if not args.since:
        three_months_ago = datetime.now() - timedelta(days=90)
        args.since = three_months_ago.strftime('%Y-%m-%d')

    repos = find_repos(args.base_dir)
    if not repos:
        print(json.dumps({'error': f'No git repos found in {args.base_dir}'}))
        sys.exit(1)

    if not args.author:
        args.author = detect_author(repos)
        if not args.author:
            print(json.dumps({'error': 'Could not detect git author. Use --author.'}))
            sys.exit(1)

    repos_data = {}
    repos_context = {}
    all_commits = []
    for repo_path in repos:
        repo_name = os.path.basename(repo_path)
        commits = collect_commits(repo_path, args.author, args.since)
        if commits:
            repos_data[repo_name] = commits
            all_commits.extend(commits)
            repos_context[repo_name] = collect_repo_context(repo_path)

    result = {}

    # Git analysis
    git_analysis = analyze(all_commits, repos_data)
    git_analysis['repo_context'] = repos_context
    result['git'] = git_analysis

    # Claude session analysis
    claude_sessions = collect_claude_sessions(args.since)
    claude_analysis = analyze_claude_sessions(claude_sessions)
    if claude_analysis:
        result['claude'] = claude_analysis

    if args.format == 'csv':
        print(to_csv(git_analysis))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
