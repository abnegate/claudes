#!/usr/bin/env python3
"""
Collect comprehensive developer profile data from git repos and Claude Code sessions.

Usage: python collect.py <base_dir> [--author <name>] [--since <date>] [--format csv|json] [--config-dir <path>]...

Outputs JSON (default) or CSV with rich commit metadata and Claude usage data.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections import defaultdict
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from functools import cache
from pathlib import Path
from typing import Any
from typing import NoReturn

DEFAULT_WINDOW_DAYS = 90
ERROR_KEY = 'error'
NO_COMMITS_ERROR = 'No commits found'
JSON_FORMAT = 'json'
CSV_FORMAT = 'csv'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
WEEKDAY_FORMAT = '%A'
WEEK_FORMAT = '%G-W%V'
MONTH_FORMAT = '%Y-%m'
MILLISECOND_TIMESTAMPS_FROM = 10_000_000_000
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
WEEKEND = ('Saturday', 'Sunday')
TIME_BUCKETS = ((5, 9, 'early_morning'), (9, 12, 'morning'), (12, 14, 'lunch'), (14, 17, 'afternoon'), (17, 21, 'evening'))
NIGHT_BUCKET = 'night'
BUSIEST_PROJECTS = 10

GIT_DIRECTORY = '.git'
COMMIT_LOG_FORMAT = '%H%x00%aI%x00%ae%x00%s'
STASH_REFERENCE = 'refs/stash'
COMMIT_FIELD_SEPARATOR = '\x00'
STATUS_RECORD_SEPARATOR = '\x00'
UNTRACKED_STATUS = '??'
ORIGINAL_PATH_STATUSES = ('R', 'C')
MODIFIED_CATEGORY = 'modified'
ADDED_CATEGORY = 'added'
DELETED_CATEGORY = 'deleted'
RENAMED_CATEGORY = 'renamed'
UNTRACKED_CATEGORY = 'untracked'
STATUS_CATEGORIES = (('R', RENAMED_CATEGORY), ('C', ADDED_CATEGORY), ('A', ADDED_CATEGORY), ('D', DELETED_CATEGORY))
UNCOMMITTED_CATEGORIES = (MODIFIED_CATEGORY, ADDED_CATEGORY, DELETED_CATEGORY, RENAMED_CATEGORY, UNTRACKED_CATEGORY)
SUBJECT_PUNCTUATION = '()[]{}.,;:!?"\'-'
SUBJECT_STOP_WORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'to', 'in', 'for', 'of', 'on', 'with', 'is', 'it', 'from', 'by', 'at', 'as', 'this', 'that',
})
TITLE_WORD_SEPARATORS = re.compile(r'[\s/\\.,;:!?()\[\]{}"\'-]+')
TITLE_STOP_WORDS = SUBJECT_STOP_WORDS | {
    'me', 'my', 'i', 'can', 'you', 'how', 'what', 'we', 'do', 'not',
    'all', 'but', 'so', 'if', 'be', 'are', 'was', 'has', 'have',
}

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
TITLE_ENTRY = 'custom-title'
RELEVANT_ENTRY = re.compile(rb'"type"\s*:\s*"(?:user|assistant|custom-title)"')
TOOL_USE_BLOCK = 'tool_use'
SKILL_TOOL = 'Skill'
MAIN_AND_SUBAGENT_SOURCE = 'main+subagent'
SUBAGENT_ONLY_SOURCE = 'subagent-only'
MAIN_ONLY_SOURCE = 'main-only'
UNKNOWN_SOURCE = 'unknown'


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


def find_repos(base_dir: str, max_depth: int = 3) -> list[str]:
    repos: list[str] = []
    base = Path(base_dir).resolve()
    for root, directories, _ in os.walk(base):
        depth = len(Path(root).relative_to(base).parts)
        if depth >= max_depth:
            directories.clear()
            continue
        if GIT_DIRECTORY in directories:
            repos.append(root)
            directories.remove(GIT_DIRECTORY)
    return sorted(repos)


def detect_author(repos: Sequence[str]) -> str | None:
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


def collect_commits(repo_path: str, author: str, since: str) -> list[dict[str, Any]]:
    start = window_start(since)
    try:
        arguments = ['git', '-C', repo_path, 'log', f'--author={author}', f'--since={start.astimezone().isoformat()}',
                     f'--format={COMMIT_LOG_FORMAT}', f'--exclude={STASH_REFERENCE}', '--all']
        output = subprocess.check_output(arguments, stderr=subprocess.DEVNULL, text=True)
    except subprocess.CalledProcessError:
        return []

    commits: list[dict[str, Any]] = []
    for line in output.splitlines():
        fields = line.split(COMMIT_FIELD_SEPARATOR, 3)
        if len(fields) < 4:
            continue
        commit_hash, date_iso, email, subject = fields
        authored = parse_timestamp(date_iso)
        if authored is None or authored < start:
            continue
        commits.append({
            'hash': commit_hash,
            'email': email,
            'datetime': date_iso,
            'date': authored.strftime(DATE_FORMAT),
            'time': authored.strftime(TIME_FORMAT),
            'hour': authored.hour,
            'weekday': authored.strftime(WEEKDAY_FORMAT),
            'weekday_num': authored.isoweekday(),
            'week': authored.strftime(WEEK_FORMAT),
            'month': authored.strftime(MONTH_FORMAT),
            'subject': subject,
        })
    return commits


def unique_commits(commits: list[dict[str, Any]], seen_hashes: set[str]) -> list[dict[str, Any]]:
    copies: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for commit in commits:
        copies.setdefault((commit['email'], commit['datetime'], commit['subject']), []).append(commit)
    return [group[0] for group in copies.values() if not any(commit['hash'] in seen_hashes for commit in group)]


def collect_repo_context(repo_path: str) -> dict[str, Any]:
    context: dict[str, Any] = {}

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
            ['git', '-C', repo_path, 'status', '--porcelain', '-z'],
            stderr=subprocess.DEVNULL, text=True
        )
        uncommitted = uncommitted_paths(status)
        if uncommitted:
            context['uncommitted'] = uncommitted
    except subprocess.CalledProcessError:
        pass

    try:
        output = subprocess.check_output(
            ['git', '-C', repo_path, 'log', '-20', '--format=%s', f'--exclude={STASH_REFERENCE}', '--all'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if output:
            context['recent_subjects'] = output.split('\n')
    except subprocess.CalledProcessError:
        pass

    return context


def uncommitted_paths(status: str) -> dict[str, list[str]]:
    paths: defaultdict[str, list[str]] = defaultdict(list)
    records = iter(status.split(STATUS_RECORD_SEPARATOR))
    for record in records:
        code, path = record[:2], record[3:]
        if not path:
            continue
        if any(marker in code for marker in ORIGINAL_PATH_STATUSES):
            next(records, None)
        paths[status_category(code)].append(path)
    return {category: paths[category] for category in UNCOMMITTED_CATEGORIES if category in paths}


def status_category(code: str) -> str:
    if code == UNTRACKED_STATUS:
        return UNTRACKED_CATEGORY
    return next((category for marker, category in STATUS_CATEGORIES if marker in code), MODIFIED_CATEGORY)


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


def compute_streaks(dates: list[str]) -> dict[str, Any]:
    if not dates:
        return {'current': 0, 'longest': 0, 'longest_start': None, 'longest_end': None}

    days = [datetime.strptime(date, DATE_FORMAT) for date in sorted(set(dates))]

    streaks: list[tuple[datetime, datetime]] = []
    start = days[0]
    previous = days[0]
    for day in days[1:]:
        if (day - previous).days == 1:
            previous = day
        else:
            streaks.append((start, previous))
            start = day
            previous = day
    streaks.append((start, previous))

    longest = max(streaks, key=lambda streak: (streak[1] - streak[0]).days + 1)
    longest_length = (longest[1] - longest[0]).days + 1

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    last_streak = streaks[-1]
    if (today - last_streak[1]).days <= 1:
        current = (last_streak[1] - last_streak[0]).days + 1
    else:
        current = 0

    return {
        'current': current,
        'longest': longest_length,
        'longest_start': longest[0].strftime(DATE_FORMAT),
        'longest_end': longest[1].strftime(DATE_FORMAT),
    }


def local_datetime(moment: datetime) -> datetime:
    return moment.astimezone().replace(tzinfo=None) if moment.tzinfo else moment


def window_start(since: str) -> datetime:
    start = local_datetime(datetime.fromisoformat(since.replace('Z', '+00:00')))
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_timestamp(value: Any) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > MILLISECOND_TIMESTAMPS_FROM else value)
        if isinstance(value, str):
            return local_datetime(datetime.fromisoformat(value.replace('Z', '+00:00')))
    except (OverflowError, OSError, ValueError):
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
    since = window_start(since_date)
    sessions: dict[str, dict[str, Any]] = {}
    titles: dict[str, str] = {}
    seen_entries: set[str] = set()
    responses: dict[str, tuple[str, str, float, float]] = {}
    for relative, paths in find_session_files(profiles, since):
        is_subagent = SUBAGENTS_DIRECTORY in relative.parts
        path_session_id = relative.parts[1] if len(relative.parts) > 2 else relative.stem
        for path in paths:
            copy_titles: dict[str, str] = {}
            for entry in read_entries(path):
                session_id = entry.get('sessionId') or path_session_id
                if entry.get('type') == TITLE_ENTRY:
                    if isinstance(entry.get('customTitle'), str):
                        copy_titles[session_id] = entry['customTitle']
                    continue
                entry_uuid = entry.get('uuid')
                if entry.get('type') not in MESSAGE_ENTRIES or entry_uuid in seen_entries:
                    continue
                timestamp = parse_timestamp(entry.get('timestamp'))
                if timestamp is None or timestamp < since:
                    continue
                if entry_uuid:
                    seen_entries.add(entry_uuid)
                session = sessions.get(session_id)
                if session is None:
                    session = sessions[session_id] = start_session(session_id, timestamp)
                record_entry(session, entry, timestamp, is_subagent, responses)
            for session_id, title in copy_titles.items():
                titles.setdefault(session_id, title)
    for session_id, model, _, cost in responses.values():
        sessions[session_id]['cost_by_model'][model] += cost
    finished = [finish_session(session, titles.get(session['id'], '')) for session in sessions.values()]
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
    responses: dict[str, tuple[str, str, float, float]],
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
        record_usage(session, entry, message, responses)
        record_tools(session, message)


def record_usage(
    session: dict[str, Any],
    entry: Mapping[str, Any],
    message: Mapping[str, Any],
    responses: dict[str, tuple[str, str, float, float]],
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
    if not isinstance(usage, Mapping):
        return
    cost = estimate_cost(model, usage) or 0.0
    response_key = message.get('id') or entry.get('uuid')
    if not response_key:
        session['cost_by_model'][canonical] += cost
        return
    output_tokens = token_count(usage, 'output_tokens')
    previous = responses.get(response_key)
    if previous is None or output_tokens >= previous[2]:
        responses[response_key] = (session['id'], canonical, output_tokens, cost)


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
        'date': created.strftime(DATE_FORMAT),
        'hour': created.hour,
        'weekday': created.strftime(WEEKDAY_FORMAT),
        'week': created.strftime(WEEK_FORMAT),
        'month': created.strftime(MONTH_FORMAT),
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


def analyze_claude_sessions(sessions: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not sessions:
        return None

    total = len(sessions)
    total_cost = sum(session['cost'] for session in sessions)
    total_turns = sum(session['turns'] for session in sessions)
    total_tools = sum(session['tool_count'] for session in sessions)

    dates = [session['date'] for session in sessions]
    min_date = min(dates)
    max_date = max(dates)
    unique_days = len(set(dates))

    tool_counts = dict(Counter(tool for session in sessions for tool in session['tool_calls']).most_common(30))
    skill_counts = dict(Counter(skill for session in sessions for skill in session['skills_used']).most_common(20))
    model_counts = dict(
        Counter(model for session in sessions for model in session.get('models') or [session['model']]).most_common()
    )

    cost_by_model: defaultdict[str, float] = defaultdict(float)
    unpriced_models: Counter[str] = Counter()
    for session in sessions:
        for model, cost in session.get('cost_by_model', {}).items():
            cost_by_model[model] += cost
        unpriced_models.update(session.get('unpriced_models', {}))
    cost_by_model_sorted = {
        model: round(cost, 4) for model, cost in sorted(cost_by_model.items(), key=lambda item: item[1], reverse=True)
    }

    source_counts = dict(Counter(session.get('source', UNKNOWN_SOURCE) for session in sessions).most_common())

    project_counts = Counter(session['project'] for session in sessions if session['project'])
    sessions_by_project: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        sessions_by_project[session['project']].append(session)
    project_stats = {
        project: {
            'sessions': count,
            'cost': round(sum(session['cost'] for session in sessions_by_project[project]), 4),
            'turns': sum(session['turns'] for session in sessions_by_project[project]),
            'tools': sum(session['tool_count'] for session in sessions_by_project[project]),
        }
        for project, count in project_counts.most_common()
    }

    hourly = Counter(session['hour'] for session in sessions)
    hourly_full = {hour: hourly.get(hour, 0) for hour in range(24)}

    daily = Counter(session['weekday'] for session in sessions)
    daily_sorted = {day: daily.get(day, 0) for day in WEEKDAYS}

    weekly_sorted = dict(sorted(Counter(session['week'] for session in sessions).items()))
    monthly_sorted = dict(sorted(Counter(session['month'] for session in sessions).items()))
    daily_sorted_counts = dict(sorted(Counter(dates).items()))

    durations = [
        session['duration_minutes'] for session in sessions
        if session['duration_minutes'] is not None and session['duration_minutes'] > 0
    ]
    duration_stats = None
    if durations:
        durations_sorted = sorted(durations)
        duration_stats = {
            'median_minutes': round(durations_sorted[len(durations_sorted) // 2], 1),
            'average_minutes': round(sum(durations) / len(durations), 1),
            'max_minutes': round(max(durations), 1),
            'total_hours': round(sum(durations) / 60, 1),
        }

    cost_by_week: defaultdict[str, float] = defaultdict(float)
    for session in sessions:
        cost_by_week[session['week']] += session['cost']
    cost_by_week_sorted = {week: round(cost, 4) for week, cost in sorted(cost_by_week.items())}

    project_hours = {
        project: dict(Counter(session['hour'] for session in sessions_by_project[project]))
        for project, _ in project_counts.most_common(BUSIEST_PROJECTS)
    }

    title_words: Counter[str] = Counter()
    for session in sessions:
        for word in TITLE_WORD_SEPARATORS.split((session.get('title') or '').lower()):
            if len(word) > 2 and word not in TITLE_STOP_WORDS:
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
        'cost_by_week': cost_by_week_sorted,
        'daily_counts': daily_sorted_counts,
        'top_session_words': top_session_words,
    }


def time_bucket(hour: int) -> str:
    return next((name for start, end, name in TIME_BUCKETS if start <= hour < end), NIGHT_BUCKET)


def analyze(all_commits: list[dict[str, Any]], repos_data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if not all_commits:
        return {ERROR_KEY: NO_COMMITS_ERROR}

    total = len(all_commits)
    dates = [commit['date'] for commit in all_commits]
    min_date = min(dates)
    max_date = max(dates)
    unique_days = len(set(dates))
    date_range_days = (datetime.strptime(max_date, DATE_FORMAT) - datetime.strptime(min_date, DATE_FORMAT)).days + 1

    active_repos = {repo: commits for repo, commits in repos_data.items() if commits}
    repo_totals = dict(sorted(((repo, len(commits)) for repo, commits in active_repos.items()), key=lambda item: -item[1]))

    weekly_sorted = dict(sorted(Counter(commit['week'] for commit in all_commits).items()))
    monthly_sorted = dict(sorted(Counter(commit['month'] for commit in all_commits).items()))

    hourly = Counter(commit['hour'] for commit in all_commits)
    hourly_full = {hour: hourly.get(hour, 0) for hour in range(24)}

    daily = Counter(commit['weekday'] for commit in all_commits)
    daily_sorted = {day: daily.get(day, 0) for day in WEEKDAYS}

    buckets = Counter(time_bucket(commit['hour']) for commit in all_commits)

    types = Counter(classify_commit(commit['subject']) for commit in all_commits)
    types_sorted = dict(sorted(types.items(), key=lambda item: -item[1]))

    repo_weekly = {repo: dict(Counter(commit['week'] for commit in commits)) for repo, commits in active_repos.items()}

    streaks = compute_streaks(dates)

    daily_counts = Counter(dates)
    daily_counts_sorted = dict(sorted(daily_counts.items()))

    per_active_day = round(total / unique_days, 1) if unique_days else 0

    weekend = sum(1 for commit in all_commits if commit['weekday'] in WEEKEND)
    weekday = total - weekend

    repo_hours = {repo: dict(Counter(commit['hour'] for commit in commits)) for repo, commits in active_repos.items()}

    words: Counter[str] = Counter()
    for commit in all_commits:
        for word in commit['subject'].lower().split():
            clean = word.strip(SUBJECT_PUNCTUATION)
            if len(clean) > 2 and clean not in SUBJECT_STOP_WORDS:
                words[clean] += 1
    top_words = dict(words.most_common(30))

    busiest_day = max(daily_counts.items(), key=lambda item: item[1])

    repo_types = {
        repo: dict(Counter(classify_commit(commit['subject']) for commit in commits)) for repo, commits in active_repos.items()
    }

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


def to_csv(analysis: dict[str, Any]) -> str:
    repo_weekly: dict[str, dict[str, int]] = analysis.get('by_repo_week', {})
    repo_totals: dict[str, int] = analysis['by_repo']
    all_weeks = sorted({week for weeks in repo_weekly.values() for week in weeks})
    repos = sorted(repo_totals, key=lambda repo: -repo_totals[repo])

    lines = ['Week,' + ','.join(repos) + ',Total']
    for week in all_weeks:
        counts = [repo_weekly.get(repo, {}).get(week, 0) for repo in repos]
        lines.append(f'{week},' + ','.join(str(count) for count in counts) + f',{sum(counts)}')

    totals = [str(repo_totals[repo]) for repo in repos]
    lines.append('Total,' + ','.join(totals) + f',{sum(repo_totals.values())}')
    return '\n'.join(lines)


def since_date(value: str) -> str:
    try:
        return window_start(value).strftime(DATE_FORMAT)
    except ValueError:
        raise argparse.ArgumentTypeError(f'expected an ISO date such as 2026-01-31, got {value!r}') from None


def config_directory(value: str) -> Path:
    return Path(value).expanduser()


def fail(message: str) -> NoReturn:
    print(json.dumps({ERROR_KEY: message}))
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Collect developer profile data from git repos and Claude sessions',
        epilog=f'Claude costs are estimated from the list prices at {PRICING_SOURCE}',
    )
    parser.add_argument('base_dir', help='Base directory containing git repos')
    parser.add_argument('--author', help='Git author name (auto-detected if omitted)')
    parser.add_argument(
        '--since',
        type=since_date,
        help=f'Start date in ISO format; the window starts at local midnight (default: {DEFAULT_WINDOW_DAYS} days ago)',
    )
    parser.add_argument('--format', choices=[JSON_FORMAT, CSV_FORMAT], default=JSON_FORMAT, help='Output format')
    parser.add_argument(
        '--config-dir',
        action='append',
        type=config_directory,
        metavar='PATH',
        help='Claude config directory to scan; repeatable (default: ~/.claude, every ~/.claude-* and $CLAUDE_CONFIG_DIR)',
    )
    args = parser.parse_args()

    since = args.since or (datetime.now() - timedelta(days=DEFAULT_WINDOW_DAYS)).strftime(DATE_FORMAT)

    repos = find_repos(args.base_dir)
    if not repos:
        fail(f'No git repos found in {args.base_dir}')

    author = args.author or detect_author(repos)
    if not author:
        fail('Could not detect git author. Use --author.')

    config_directories = args.config_dir or ()
    for directory in config_directories:
        if not (directory / PROJECTS_DIRECTORY).is_dir():
            print(f'Skipping --config-dir {directory}: it has no {PROJECTS_DIRECTORY}/ directory', file=sys.stderr)
    profiles = discover_profiles(config_directories)

    repos_data: dict[str, list[dict[str, Any]]] = {}
    repos_context: dict[str, dict[str, Any]] = {}
    all_commits: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for repo_path in repos:
        repo_name = os.path.basename(repo_path)
        repository_commits = collect_commits(repo_path, author, since)
        commits = unique_commits(repository_commits, seen_hashes)
        seen_hashes.update(commit['hash'] for commit in repository_commits)
        if commits:
            repos_data.setdefault(repo_name, []).extend(commits)
            all_commits.extend(commits)
            if repo_name not in repos_context:
                repos_context[repo_name] = collect_repo_context(repo_path)

    git_analysis = analyze(all_commits, repos_data)
    git_analysis['repo_context'] = repos_context
    result: dict[str, Any] = {'git': git_analysis}

    claude_analysis = analyze_claude_sessions(collect_claude_sessions(since, profiles)) or {}
    result['claude'] = {**claude_analysis, 'profiles_scanned': [str(profile) for profile in profiles]}

    if args.format == CSV_FORMAT:
        if ERROR_KEY in git_analysis:
            fail(git_analysis[ERROR_KEY])
        print(to_csv(git_analysis))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
