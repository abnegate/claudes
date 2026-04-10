#!/usr/bin/env python3
"""
Collect comprehensive git commit data across all repos in a directory.

Usage: python collect.py <base_dir> [--author <name>] [--since <date>] [--format csv|json]

Outputs JSON (default) or CSV with rich commit metadata for analysis.
"""

import argparse
import json
import os
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

    # Current branch
    try:
        branch = subprocess.check_output(
            ['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        context['branch'] = branch
    except subprocess.CalledProcessError:
        context['branch'] = None

    # Uncommitted changes (staged + unstaged + untracked)
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

    # Recent commit subjects (last 20, all authors) for theme extraction
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
    # Heuristic fallback
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

    # Per-repo counts
    repo_totals = {repo: len(commits) for repo, commits in repos_data.items() if commits}
    repo_totals = dict(sorted(repo_totals.items(), key=lambda x: -x[1]))

    # Weekly totals
    weekly = Counter(c['week'] for c in all_commits)
    weekly_sorted = dict(sorted(weekly.items()))

    # Monthly totals
    monthly = Counter(c['month'] for c in all_commits)
    monthly_sorted = dict(sorted(monthly.items()))

    # Hour distribution
    hourly = Counter(c['hour'] for c in all_commits)
    hourly_full = {h: hourly.get(h, 0) for h in range(24)}

    # Day of week distribution
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily = Counter(c['weekday'] for c in all_commits)
    daily_sorted = {d: daily.get(d, 0) for d in day_order}

    # Time buckets
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

    # Commit types
    types = Counter(classify_commit(c['subject']) for c in all_commits)
    types_sorted = dict(sorted(types.items(), key=lambda x: -x[1]))

    # Per-repo weekly breakdown (for CSV)
    repo_weekly = {}
    for repo, commits in repos_data.items():
        if commits:
            repo_weekly[repo] = dict(Counter(c['week'] for c in commits))

    # Streaks
    streaks = compute_streaks(dates)

    # Daily commit counts for velocity
    daily_counts = Counter(dates)
    daily_counts_sorted = dict(sorted(daily_counts.items()))

    # Commits per active day
    per_active_day = round(total / unique_days, 1) if unique_days else 0

    # Weekend vs weekday
    weekend = sum(1 for c in all_commits if c['weekday'] in ('Saturday', 'Sunday'))
    weekday = total - weekend

    # Per-repo per-hour (to find repo-specific patterns)
    repo_hours = {}
    for repo, commits in repos_data.items():
        if commits:
            repo_hours[repo] = dict(Counter(c['hour'] for c in commits))

    # Most common commit words (excluding stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'to', 'in', 'for', 'of', 'on', 'with', 'is', 'it', 'from', 'by', 'at', 'as', 'this', 'that'}
    words = Counter()
    for c in all_commits:
        for word in c['subject'].lower().split():
            clean = word.strip('()[]{}.,;:!?"\'-')
            if len(clean) > 2 and clean not in stop_words:
                words[clean] += 1
    top_words = dict(words.most_common(30))

    # Busiest single day
    busiest_day = max(daily_counts.items(), key=lambda x: x[1])

    # Per-repo commit types
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
    parser = argparse.ArgumentParser(description='Collect git commit stats across repos')
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

    analysis = analyze(all_commits, repos_data)
    analysis['repo_context'] = repos_context

    if args.format == 'csv':
        print(to_csv(analysis))
    else:
        print(json.dumps(analysis, indent=2))


if __name__ == '__main__':
    main()
