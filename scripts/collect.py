#!/usr/bin/env python3
"""
Collect comprehensive developer profile data from git repos and Claude Code sessions.

Usage: python collect.py <base_dir> [--author <name>] [--since <date>] [--format csv|json] [--config-dir <path>]...

Outputs JSON (default) or CSV with rich commit metadata and Claude usage data.
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

PRICING_SOURCE = 'https://platform.claude.com/docs/en/about-claude/pricing.md'
US_INFERENCE_MULTIPLIER = 1.1
US_INFERENCE_GEO = 'us'
FAST_SPEED = 'fast'
SYNTHETIC_MODEL = '<synthetic>'
UNKNOWN_MODEL = 'unknown'
TOKENS_PER_MILLION = 1_000_000
FIVE_MINUTE_CACHE_WRITES = 'ephemeral_5m_input_tokens'
ONE_HOUR_CACHE_WRITES = 'ephemeral_1h_input_tokens'
MODEL_ALIASES = {'claude-opus-4': 'claude-opus-4-0', 'claude-sonnet-4': 'claude-sonnet-4-0'}
MODEL_SUFFIX = re.compile(r'\[[^\]]*\]$')
MODEL_DATE = re.compile(r'-\d{8}$')

DEFAULT_PROFILE = '.claude'
PROFILE_PATTERN = '.claude-*'
CONFIG_DIRECTORY_VARIABLE = 'CLAUDE_CONFIG_DIR'
PROJECTS_DIRECTORY = 'projects'
SUBAGENTS_DIRECTORY = 'subagents'
SESSION_FILE_PATTERN = '*.jsonl'

USER_ENTRY = 'user'
ASSISTANT_ENTRY = 'assistant'
MESSAGE_ENTRIES = (USER_ENTRY, ASSISTANT_ENTRY)
RELEVANT_ENTRY = re.compile(rb'"type"\s*:\s*"(?:user|assistant)"')
TOOL_USE_BLOCK = 'tool_use'
SKILL_TOOL = 'Skill'
MAIN_AND_SUBAGENT_SOURCE = 'main+subagent'
SUBAGENT_ONLY_SOURCE = 'subagent-only'
MAIN_ONLY_SOURCE = 'main-only'


@dataclass(frozen=True)
class Pricing:
    input: float
    output: float
    cache_write_5m: float
    cache_write_1h: float
    cache_read: float


MODEL_PRICING: dict[str, Pricing] = {
    model: pricing
    for models, pricing in (
        (('claude-fable-5-1', 'claude-mythos-5-1'), Pricing(input=10, output=50, cache_write_5m=12.5, cache_write_1h=20, cache_read=0.25)),
        (('claude-fable-5', 'claude-mythos-5'), Pricing(input=10, output=50, cache_write_5m=12.5, cache_write_1h=20, cache_read=1)),
        (('claude-opus-5-5',), Pricing(input=4, output=20, cache_write_5m=5, cache_write_1h=8, cache_read=0.2)),
        (
            ('claude-opus-5', 'claude-opus-4-8', 'claude-opus-4-7', 'claude-opus-4-6', 'claude-opus-4-5'),
            Pricing(input=5, output=25, cache_write_5m=6.25, cache_write_1h=10, cache_read=0.5),
        ),
        (('claude-opus-4-1', 'claude-opus-4-0'), Pricing(input=15, output=75, cache_write_5m=18.75, cache_write_1h=30, cache_read=1.5)),
        (('claude-sonnet-5',), Pricing(input=2, output=10, cache_write_5m=2.5, cache_write_1h=4, cache_read=0.2)),
        (('claude-sonnet-4-6', 'claude-sonnet-4-5', 'claude-sonnet-4-0'), Pricing(input=3, output=15, cache_write_5m=3.75, cache_write_1h=6, cache_read=0.3)),
        (('claude-haiku-4-5',), Pricing(input=1, output=5, cache_write_5m=1.25, cache_write_1h=2, cache_read=0.1)),
        (('claude-3-5-haiku',), Pricing(input=0.8, output=4, cache_write_5m=1, cache_write_1h=1.6, cache_read=0.08)),
    )
    for model in models
}

FAST_MODE_PRICING: dict[str, Pricing] = {
    model: pricing
    for models, pricing in (
        (('claude-opus-5-5',), Pricing(input=8, output=40, cache_write_5m=10, cache_write_1h=16, cache_read=0.4)),
        (('claude-opus-5', 'claude-opus-4-8'), Pricing(input=10, output=50, cache_write_5m=12.5, cache_write_1h=20, cache_read=1)),
    )
    for model in models
}


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


CONVENTIONAL_SUBJECT = r'^(?P<type>[a-z]+)(?:\((?P<scope>[^()\r\n]+)\))?(?P<breaking>!)?: '
LEGACY_SUBJECT = r'^\((?P<type>[a-z]+)\): '
COMMIT_TYPES = ('feat', 'fix', 'refactor', 'chore', 'docs', 'test', 'style', 'perf', 'ci', 'build', 'revert', 'wip')


def classify_commit(subject: str) -> str:
    lowered = subject.lower().strip()
    match = re.match(CONVENTIONAL_SUBJECT, lowered) or re.match(LEGACY_SUBJECT, lowered)
    if match and match['type'] in COMMIT_TYPES:
        return match['type']
    if lowered.startswith('merge'):
        return 'merge'
    if lowered.startswith(('add', 'implement', 'create')):
        return 'feat'
    if lowered.startswith(('fix', 'bug', 'patch')):
        return 'fix'
    if lowered.startswith(('update', 'improve', 'enhance')):
        return 'improvement'
    if lowered.startswith(('remove', 'delete', 'clean')):
        return 'cleanup'
    if lowered.startswith(('refactor', 'restructure', 'reorgani')):
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


@cache
def canonical_model(model: str) -> str | None:
    name = MODEL_DATE.sub('', MODEL_SUFFIX.sub('', model))
    name = MODEL_ALIASES.get(name, name)
    return name if name in MODEL_PRICING else None


def estimate_cost(model: str, usage: Mapping[str, Any]) -> float | None:
    if model == SYNTHETIC_MODEL:
        return 0.0
    canonical = canonical_model(model)
    if canonical is None:
        return None
    pricing = MODEL_PRICING[canonical]
    if usage.get('speed') == FAST_SPEED:
        pricing = FAST_MODE_PRICING.get(canonical, pricing)
    cache_write_5m, cache_write_1h = cache_write_tokens(usage)
    cost = (
        token_count(usage, 'input_tokens') * pricing.input
        + token_count(usage, 'output_tokens') * pricing.output
        + cache_write_5m * pricing.cache_write_5m
        + cache_write_1h * pricing.cache_write_1h
        + token_count(usage, 'cache_read_input_tokens') * pricing.cache_read
    ) / TOKENS_PER_MILLION
    if usage.get('inference_geo') == US_INFERENCE_GEO:
        return cost * US_INFERENCE_MULTIPLIER
    return cost


def cache_write_tokens(usage: Mapping[str, Any]) -> tuple[float, float]:
    breakdown = usage.get('cache_creation')
    if isinstance(breakdown, Mapping) and (FIVE_MINUTE_CACHE_WRITES in breakdown or ONE_HOUR_CACHE_WRITES in breakdown):
        return token_count(breakdown, FIVE_MINUTE_CACHE_WRITES), token_count(breakdown, ONE_HOUR_CACHE_WRITES)
    return token_count(usage, 'cache_creation_input_tokens'), 0


def token_count(usage: Mapping[str, Any], key: str) -> float:
    value = usage.get(key)
    return value if isinstance(value, (int, float)) else 0


def discover_profiles(explicit: Sequence[Path] = ()) -> list[Path]:
    candidates = [Path(path) for path in explicit] if explicit else default_profiles()
    profiles: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if not (candidate / PROJECTS_DIRECTORY).is_dir():
            continue
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            profiles.append(candidate)
    return profiles


def default_profiles() -> list[Path]:
    home = Path.home()
    others = list(home.glob(PROFILE_PATTERN))
    configured = os.environ.get(CONFIG_DIRECTORY_VARIABLE)
    if configured:
        others.append(Path(configured))
    return [home / DEFAULT_PROFILE, *sorted(others)]


def collect_claude_sessions(since_date: str, profiles: Sequence[Path]) -> list[dict[str, Any]]:
    since = datetime.fromisoformat(since_date)
    sessions: dict[str, dict[str, Any]] = {}
    seen_entries: set[str] = set()
    seen_messages: set[str] = set()
    for relative, paths in find_session_files(profiles, since):
        is_subagent = SUBAGENTS_DIRECTORY in relative.parts
        path_session_id = relative.parts[1] if len(relative.parts) > 2 else relative.stem
        for path in paths:
            for entry in read_entries(path):
                entry_uuid = entry.get('uuid')
                if entry.get('type') not in MESSAGE_ENTRIES or entry_uuid in seen_entries:
                    continue
                timestamp = parse_timestamp(entry.get('timestamp'))
                if timestamp is None or timestamp < since:
                    continue
                if entry_uuid:
                    seen_entries.add(entry_uuid)
                session_id = entry.get('sessionId') or path_session_id
                session = sessions.get(session_id)
                if session is None:
                    session = sessions[session_id] = start_session(session_id, timestamp)
                record_entry(session, entry, timestamp, is_subagent, seen_messages)
    finished = [finish_session(session, '') for session in sessions.values()]
    return sorted(finished, key=lambda session: session['created'])


def find_session_files(profiles: Sequence[Path], since: datetime) -> list[tuple[Path, list[Path]]]:
    oldest = since.timestamp()
    copies: defaultdict[Path, list[tuple[int, int, Path]]] = defaultdict(list)
    for order, profile in enumerate(profiles):
        projects = profile / PROJECTS_DIRECTORY
        for path in projects.rglob(SESSION_FILE_PATTERN):
            try:
                status = path.stat()
            except OSError:
                continue
            if status.st_mtime >= oldest:
                copies[path.relative_to(projects)].append((status.st_size, order, path))
    ordered = sorted(copies, key=lambda relative: (len(relative.parts), relative))
    return [(relative, copies_to_read(copies[relative])) for relative in ordered]


def copies_to_read(copies: list[tuple[int, int, Path]]) -> list[Path]:
    read_sizes: set[int] = set()
    paths: list[Path] = []
    for size, _, path in sorted(copies, key=lambda copy: (-copy[0], copy[1])):
        if size not in read_sizes:
            read_sizes.add(size)
            paths.append(path)
    return paths


def read_entries(path: Path) -> Iterator[dict[str, Any]]:
    try:
        with path.open('rb') as handle:
            for line in handle:
                if RELEVANT_ENTRY.search(line) is None:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


def start_session(session_id: str, timestamp: datetime) -> dict[str, Any]:
    return {
        'id': session_id,
        'first_timestamp': timestamp,
        'last_timestamp': timestamp,
        'user_messages': 0,
        'assistant_messages': 0,
        'tool_calls': [],
        'skills_used': [],
        'models': set(),
        'model_counts': Counter(),
        'cost_by_model': defaultdict(float),
        'unpriced_models': Counter(),
        'cwd': '',
        'git_branches': set(),
        'has_subagent_data': False,
        'has_main_data': False,
    }


def record_entry(
    session: dict[str, Any],
    entry: Mapping[str, Any],
    timestamp: datetime,
    is_subagent: bool,
    seen_messages: set[str],
) -> None:
    session['first_timestamp'] = min(session['first_timestamp'], timestamp)
    session['last_timestamp'] = max(session['last_timestamp'], timestamp)
    if is_subagent:
        session['has_subagent_data'] = True
    else:
        session['has_main_data'] = True
    if entry.get('cwd') and not session['cwd']:
        session['cwd'] = entry['cwd']
    if entry.get('gitBranch'):
        session['git_branches'].add(entry['gitBranch'])
    if entry.get('type') == USER_ENTRY:
        session['user_messages'] += 1
        return
    session['assistant_messages'] += 1
    message = entry.get('message')
    if isinstance(message, dict):
        record_usage(session, entry, message, seen_messages)
        record_tools(session, message)


def record_usage(
    session: dict[str, Any],
    entry: Mapping[str, Any],
    message: Mapping[str, Any],
    seen_messages: set[str],
) -> None:
    model = message.get('model')
    if not isinstance(model, str) or not model:
        return
    session['models'].add(model)
    if model == SYNTHETIC_MODEL:
        return
    session['model_counts'][model] += 1
    canonical = canonical_model(model)
    if canonical is None:
        session['unpriced_models'][model] += 1
        return
    usage = message.get('usage')
    message_key = message.get('id') or entry.get('uuid')
    if not isinstance(usage, Mapping) or message_key in seen_messages:
        return
    if message_key:
        seen_messages.add(message_key)
    session['cost_by_model'][canonical] += estimate_cost(model, usage) or 0.0


def record_tools(session: dict[str, Any], message: Mapping[str, Any]) -> None:
    content = message.get('content')
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict) or block.get('type') != TOOL_USE_BLOCK:
            continue
        tool_name = block.get('name', '')
        session['tool_calls'].append(tool_name)
        tool_input = block.get('input')
        if tool_name == SKILL_TOOL and isinstance(tool_input, dict) and tool_input.get('skill'):
            session['skills_used'].append(tool_input['skill'])


def finish_session(session: dict[str, Any], title: str) -> dict[str, Any]:
    created: datetime = session['first_timestamp']
    model_counts: Counter[str] = session['model_counts']
    cost_by_model = dict(session['cost_by_model'])
    return {
        'id': session['id'],
        'created': created.isoformat(),
        'date': created.strftime('%Y-%m-%d'),
        'hour': created.hour,
        'weekday': created.strftime('%A'),
        'week': created.strftime('%Y-W%V'),
        'month': created.strftime('%Y-%m'),
        'model': model_counts.most_common(1)[0][0] if model_counts else UNKNOWN_MODEL,
        'models': sorted(session['models']),
        'cost': round(sum(cost_by_model.values()), 4),
        'cost_by_model': cost_by_model,
        'unpriced_models': dict(session['unpriced_models']),
        'turns': session['user_messages'],
        'user_messages': session['user_messages'],
        'assistant_messages': session['assistant_messages'],
        'tool_calls': session['tool_calls'],
        'tool_count': len(session['tool_calls']),
        'skills_used': session['skills_used'],
        'project': Path(session['cwd']).name if session['cwd'] else '',
        'git_branches': sorted(session['git_branches']),
        'title': title,
        'duration_minutes': round((session['last_timestamp'] - created).total_seconds() / 60, 1),
        'source': session_source(session),
    }


def session_source(session: dict[str, Any]) -> str:
    if session['has_main_data'] and session['has_subagent_data']:
        return MAIN_AND_SUBAGENT_SOURCE
    return SUBAGENT_ONLY_SOURCE if session['has_subagent_data'] else MAIN_ONLY_SOURCE


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

    cost_by_model: defaultdict[str, float] = defaultdict(float)
    unpriced_models: Counter[str] = Counter()
    for session in sessions:
        for model, cost in session.get('cost_by_model', {}).items():
            cost_by_model[model] += cost
        unpriced_models.update(session.get('unpriced_models', {}))
    cost_by_model_sorted = {
        model: round(cost, 4) for model, cost in sorted(cost_by_model.items(), key=lambda item: item[1], reverse=True)
    }

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
        'cost_by_model': cost_by_model_sorted,
        'unpriced_models': dict(unpriced_models.most_common()),
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
    parser = argparse.ArgumentParser(
        description='Collect developer profile data from git repos and Claude sessions',
        epilog=f'Claude costs are estimated from the list prices at {PRICING_SOURCE}',
    )
    parser.add_argument('base_dir', help='Base directory containing git repos')
    parser.add_argument('--author', help='Git author name (auto-detected if omitted)')
    parser.add_argument('--since', help='Start date (ISO format, default: 3 months ago)')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
    parser.add_argument(
        '--config-dir',
        action='append',
        type=Path,
        metavar='PATH',
        help='Claude config directory to scan; repeatable (default: ~/.claude, every ~/.claude-* and $CLAUDE_CONFIG_DIR)',
    )
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
    profiles = discover_profiles(args.config_dir or ())
    claude_sessions = collect_claude_sessions(args.since, profiles)
    claude_analysis = analyze_claude_sessions(claude_sessions)
    if claude_analysis:
        claude_analysis['profiles_scanned'] = [str(profile) for profile in profiles]
        result['claude'] = claude_analysis

    if args.format == 'csv':
        print(to_csv(git_analysis))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
