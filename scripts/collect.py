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


def collect_claude_sessions(since_date):
    """Collect Claude Code session metadata from ~/.claude/sessions/."""
    sessions_dir = Path.home() / '.claude' / 'sessions'
    if not sessions_dir.exists():
        return []

    since_dt = datetime.fromisoformat(since_date) if isinstance(since_date, str) else since_date
    sessions = []

    for path in sessions_dir.glob('*.json'):
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        metadata = data.get('metadata', {})
        messages = data.get('messages', [])

        created = metadata.get('createdAt')
        if not created:
            continue

        try:
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00')).replace(tzinfo=None)
        except (ValueError, AttributeError):
            continue

        if created_dt < since_dt:
            continue

        tool_calls = []
        assistant_tokens = 0
        user_messages = 0
        assistant_messages = 0
        skills_used = []

        for message in messages:
            role = message.get('role', '')
            if role == 'user':
                user_messages += 1
            elif role == 'assistant':
                assistant_messages += 1

            content = message.get('content', [])
            if isinstance(content, str):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use':
                    tool_name = block.get('name', '')
                    tool_calls.append(tool_name)
                    if tool_name == 'Skill':
                        skill = block.get('input', {}).get('skill', '')
                        if skill:
                            skills_used.append(skill)

        # Extract project from cwd
        cwd = metadata.get('cwd', '')
        project = os.path.basename(cwd) if cwd else ''

        updated = metadata.get('updatedAt')
        duration_minutes = None
        if created and updated:
            try:
                updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00')).replace(tzinfo=None)
                duration_minutes = round((updated_dt - created_dt).total_seconds() / 60, 1)
            except (ValueError, AttributeError):
                pass

        sessions.append({
            'id': metadata.get('id', path.stem),
            'created': created,
            'date': created_dt.strftime('%Y-%m-%d'),
            'hour': created_dt.hour,
            'weekday': created_dt.strftime('%A'),
            'week': created_dt.strftime('%Y-W%V'),
            'month': created_dt.strftime('%Y-%m'),
            'model': metadata.get('model', 'unknown'),
            'cost': metadata.get('totalCostUsd', 0) or 0,
            'turns': metadata.get('turnCount', 0) or 0,
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'tool_calls': tool_calls,
            'tool_count': len(tool_calls),
            'skills_used': skills_used,
            'project': project,
            'title': metadata.get('title', ''),
            'duration_minutes': duration_minutes,
        })

    return sorted(sessions, key=lambda s: s['created'])


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

    # Model usage
    model_counts = dict(Counter(s['model'] for s in sessions).most_common())

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
