#!/usr/bin/env python3
"""
Collect comprehensive developer profile data from git repos and Claude Code sessions.

Usage: python collect.py <base_directory> [--author <name>] [--since <date>] [--format csv|json] [--config-dir <path>]...

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
from collections.abc import Iterable
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
UTC_DESIGNATOR = 'Z'
UTC_OFFSET = '+00:00'
MILLISECOND_TIMESTAMPS_FROM = 10_000_000_000
MILLISECONDS_PER_SECOND = 1000
MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
WEEKEND = ('Saturday', 'Sunday')
TIME_BUCKETS = ((5, 9, 'early_morning'), (9, 12, 'morning'), (12, 14, 'lunch'), (14, 17, 'afternoon'), (17, 21, 'evening'))
NIGHT_BUCKET = 'night'
BUSIEST_PROJECTS = 10
TOP_TOOLS = 30
TOP_SKILLS = 20
TOP_WORDS = 30
MINIMUM_WORD_LENGTH = 3

GIT_DIRECTORY = '.git'
REPOSITORY_SEARCH_DEPTH = 3
RECENT_SUBJECTS = 20
COMMIT_LOG_FORMAT = '%H%x00%aI%x00%ae%x00%s'
SUBJECT_LOG_FORMAT = '%s'
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
CONVENTIONAL_SUBJECT = re.compile(r'^(?P<type>[a-z]+)(?:\((?P<scope>[^()\r\n]+)\))?(?P<breaking>!)?: ')
LEGACY_SUBJECT = re.compile(r'^\((?P<type>[a-z]+)\): ')
COMMIT_TYPES = ('feat', 'fix', 'refactor', 'chore', 'docs', 'test', 'style', 'perf', 'ci', 'build', 'revert', 'wip')
KEYWORD_TYPES = (
    (('merge',), 'merge'),
    (('add', 'implement', 'create'), 'feat'),
    (('fix', 'bug', 'patch'), 'fix'),
    (('update', 'improve', 'enhance'), 'improvement'),
    (('remove', 'delete', 'clean'), 'cleanup'),
    (('refactor', 'restructure', 'reorgani'), 'refactor'),
)
OTHER_TYPE = 'other'
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
MODEL_ALIASES = {'claude-opus-4': 'claude-opus-4-0', 'claude-sonnet-4': 'claude-sonnet-4-0'}
MODEL_SUFFIX = re.compile(r'\[[^\]]*\]$')
MODEL_DATE = re.compile(r'-\d{8}$')

DEFAULT_PROFILE = '.claude'
PROFILE_PATTERN = '.claude-*'
CONFIG_DIRECTORY_VARIABLE = 'CLAUDE_CONFIG_DIR'
PROJECTS_DIRECTORY = 'projects'
SUBAGENTS_DIRECTORY = 'subagents'
SESSION_FILE_PATTERN = '*.jsonl'
WORKTREE_SEGMENT = re.compile(r'/\.claude/worktrees/[^/]+')

USER_ENTRY = 'user'
ASSISTANT_ENTRY = 'assistant'
MESSAGE_ENTRIES = (USER_ENTRY, ASSISTANT_ENTRY)
TITLE_ENTRY = 'custom-title'
RELEVANT_ENTRY = re.compile(rb'"type"\s*:\s*"(?:user|assistant|custom-title)"')
TYPE_FIELD = 'type'
UUID_FIELD = 'uuid'
SESSION_ID_FIELD = 'sessionId'
TIMESTAMP_FIELD = 'timestamp'
WORKING_DIRECTORY_FIELD = 'cwd'
GIT_BRANCH_FIELD = 'gitBranch'
CUSTOM_TITLE_FIELD = 'customTitle'
META_FIELD = 'isMeta'
COMPACT_SUMMARY_FIELD = 'isCompactSummary'
PROMPT_SOURCE_FIELD = 'promptSource'
SDK_PROMPT_SOURCE = 'sdk'
ORIGIN_FIELD = 'origin'
ORIGIN_KIND_FIELD = 'kind'
HUMAN_ORIGIN = 'human'
MESSAGE_FIELD = 'message'
MESSAGE_ID_FIELD = 'id'
MODEL_FIELD = 'model'
USAGE_FIELD = 'usage'
CONTENT_FIELD = 'content'
TEXT_FIELD = 'text'
TOOL_NAME_FIELD = 'name'
TOOL_INPUT_FIELD = 'input'
SKILL_FIELD = 'skill'
INPUT_TOKENS_FIELD = 'input_tokens'
OUTPUT_TOKENS_FIELD = 'output_tokens'
CACHE_READ_TOKENS_FIELD = 'cache_read_input_tokens'
CACHE_WRITE_TOKENS_FIELD = 'cache_creation_input_tokens'
CACHE_WRITE_BREAKDOWN_FIELD = 'cache_creation'
FIVE_MINUTE_CACHE_WRITES_FIELD = 'ephemeral_5m_input_tokens'
ONE_HOUR_CACHE_WRITES_FIELD = 'ephemeral_1h_input_tokens'
SPEED_FIELD = 'speed'
INFERENCE_GEO_FIELD = 'inference_geo'
TOOL_USE_BLOCK = 'tool_use'
TOOL_RESULT_BLOCK = 'tool_result'
TEXT_BLOCK = 'text'
HARNESS_PREFIXES = ('<task-notification>', '<local-command-stdout>', '<ci-monitor-event>', '<bash-stdout>', '[Request interrupted')
ACTIVE_GAP_CAP = timedelta(minutes=15)
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


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace(UTC_DESIGNATOR, UTC_OFFSET))


def local_datetime(moment: datetime) -> datetime:
    return moment.astimezone().replace(tzinfo=None) if moment.tzinfo else moment


def window_start(since: str) -> datetime:
    return local_datetime(parse_iso(since)).replace(hour=0, minute=0, second=0, microsecond=0)


def parse_timestamp(value: Any) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            seconds = value / MILLISECONDS_PER_SECOND if value > MILLISECOND_TIMESTAMPS_FROM else value
            return datetime.fromtimestamp(seconds)
        if isinstance(value, str):
            return local_datetime(parse_iso(value))
    except (OverflowError, OSError, ValueError):
        return None
    return None


def find_repositories(base_directory: str, depth: int = REPOSITORY_SEARCH_DEPTH) -> list[str]:
    repositories: list[str] = []
    base = Path(base_directory).resolve()
    for root, directories, _ in os.walk(base):
        if len(Path(root).relative_to(base).parts) >= depth:
            directories.clear()
            continue
        if GIT_DIRECTORY in directories:
            repositories.append(root)
            directories.remove(GIT_DIRECTORY)
    return sorted(repositories)


def detect_author(repositories: Sequence[str]) -> str | None:
    for repository in repositories:
        try:
            name = subprocess.check_output(
                ['git', '-C', repository, 'config', 'user.name'],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            if name:
                return name
        except subprocess.CalledProcessError:
            continue
    return None


def analyze_repositories(repositories: Sequence[str], author: str, since: str) -> dict[str, Any]:
    commits_by_repository: dict[str, list[dict[str, Any]]] = {}
    contexts: dict[str, dict[str, Any]] = {}
    all_commits: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for repository in repositories:
        found = collect_commits(repository, author, since)
        commits = unique_commits(found, seen_hashes)
        seen_hashes.update(commit['hash'] for commit in found)
        if not commits:
            continue
        name = os.path.basename(repository)
        commits_by_repository.setdefault(name, []).extend(commits)
        all_commits.extend(commits)
        if name not in contexts:
            contexts[name] = collect_repository_context(repository)
    return {**analyze(all_commits, commits_by_repository), 'repo_context': contexts}


def collect_commits(repository: str, author: str, since: str) -> list[dict[str, Any]]:
    start = window_start(since)
    try:
        arguments = ['git', '-C', repository, 'log', f'--author={author}', f'--since={start.astimezone().isoformat()}',
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


def collect_repository_context(repository: str) -> dict[str, Any]:
    context: dict[str, Any] = {}

    try:
        branch = subprocess.check_output(
            ['git', '-C', repository, 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        context['branch'] = branch
    except subprocess.CalledProcessError:
        context['branch'] = None

    try:
        status = subprocess.check_output(
            ['git', '-C', repository, 'status', '--porcelain', '-z'],
            stderr=subprocess.DEVNULL, text=True
        )
        uncommitted = uncommitted_paths(status)
        if uncommitted:
            context['uncommitted'] = uncommitted
    except subprocess.CalledProcessError:
        pass

    try:
        output = subprocess.check_output(
            ['git', '-C', repository, 'log', f'-{RECENT_SUBJECTS}', f'--format={SUBJECT_LOG_FORMAT}',
             f'--exclude={STASH_REFERENCE}', '--all'],
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


def classify_commit(subject: str) -> str:
    lowered = subject.lower().strip()
    match = CONVENTIONAL_SUBJECT.match(lowered) or LEGACY_SUBJECT.match(lowered)
    if match and match['type'] in COMMIT_TYPES:
        return match['type']
    return next((commit_type for keywords, commit_type in KEYWORD_TYPES if lowered.startswith(keywords)), OTHER_TYPE)


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


def time_bucket(hour: int) -> str:
    return next((name for start, end, name in TIME_BUCKETS if start <= hour < end), NIGHT_BUCKET)


def analyze(all_commits: list[dict[str, Any]], commits_by_repository: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if not all_commits:
        return {ERROR_KEY: NO_COMMITS_ERROR}

    total = len(all_commits)
    dates = [commit['date'] for commit in all_commits]
    first_date = min(dates)
    last_date = max(dates)
    unique_days = len(set(dates))
    date_range_days = (datetime.strptime(last_date, DATE_FORMAT) - datetime.strptime(first_date, DATE_FORMAT)).days + 1

    active_repositories = {repository: commits for repository, commits in commits_by_repository.items() if commits}
    repository_totals = dict(sorted(
        ((repository, len(commits)) for repository, commits in active_repositories.items()),
        key=lambda item: -item[1],
    ))

    weekly_sorted = dict(sorted(Counter(commit['week'] for commit in all_commits).items()))
    monthly_sorted = dict(sorted(Counter(commit['month'] for commit in all_commits).items()))

    hourly = Counter(commit['hour'] for commit in all_commits)
    hourly_full = {hour: hourly.get(hour, 0) for hour in range(24)}

    daily = Counter(commit['weekday'] for commit in all_commits)
    daily_sorted = {day: daily.get(day, 0) for day in WEEKDAYS}

    buckets = Counter(time_bucket(commit['hour']) for commit in all_commits)

    types = Counter(classify_commit(commit['subject']) for commit in all_commits)
    types_sorted = dict(sorted(types.items(), key=lambda item: -item[1]))

    repository_weeks = {
        repository: dict(Counter(commit['week'] for commit in commits)) for repository, commits in active_repositories.items()
    }

    streaks = compute_streaks(dates)

    daily_counts = Counter(dates)
    daily_counts_sorted = dict(sorted(daily_counts.items()))

    per_active_day = round(total / unique_days, 1) if unique_days else 0

    weekend = sum(1 for commit in all_commits if commit['weekday'] in WEEKEND)
    weekday = total - weekend

    repository_hours = {
        repository: dict(Counter(commit['hour'] for commit in commits)) for repository, commits in active_repositories.items()
    }

    words: Counter[str] = Counter()
    for commit in all_commits:
        for word in commit['subject'].lower().split():
            clean = word.strip(SUBJECT_PUNCTUATION)
            if len(clean) >= MINIMUM_WORD_LENGTH and clean not in SUBJECT_STOP_WORDS:
                words[clean] += 1
    top_words = dict(words.most_common(TOP_WORDS))

    busiest_day = max(daily_counts.items(), key=lambda item: item[1])

    repository_types = {
        repository: dict(Counter(classify_commit(commit['subject']) for commit in commits))
        for repository, commits in active_repositories.items()
    }

    return {
        'summary': {
            'total_commits': total,
            'repos_active': len(repository_totals),
            'date_range': f'{first_date} to {last_date}',
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
        'by_repo': repository_totals,
        'by_week': weekly_sorted,
        'by_month': monthly_sorted,
        'by_hour': hourly_full,
        'by_day_of_week': daily_sorted,
        'by_time_bucket': dict(buckets),
        'by_type': types_sorted,
        'by_repo_week': repository_weeks,
        'by_repo_hour': repository_hours,
        'by_repo_type': repository_types,
        'daily_counts': daily_counts_sorted,
        'top_words': top_words,
    }


def to_csv(analysis: dict[str, Any]) -> str:
    repository_weeks: dict[str, dict[str, int]] = analysis.get('by_repo_week', {})
    repository_totals: dict[str, int] = analysis['by_repo']
    all_weeks = sorted({week for weeks in repository_weeks.values() for week in weeks})
    repositories = sorted(repository_totals, key=lambda repository: -repository_totals[repository])

    lines = ['Week,' + ','.join(repositories) + ',Total']
    for week in all_weeks:
        counts = [repository_weeks.get(repository, {}).get(week, 0) for repository in repositories]
        lines.append(f'{week},' + ','.join(str(count) for count in counts) + f',{sum(counts)}')

    totals = [str(repository_totals[repository]) for repository in repositories]
    lines.append('Total,' + ','.join(totals) + f',{sum(repository_totals.values())}')
    return '\n'.join(lines)


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
    if usage.get(SPEED_FIELD) == FAST_SPEED:
        pricing = FAST_MODE_PRICING.get(canonical, pricing)
    cache_write_5m, cache_write_1h = cache_write_tokens(usage)
    cost = (
        token_count(usage, INPUT_TOKENS_FIELD) * pricing.input
        + token_count(usage, OUTPUT_TOKENS_FIELD) * pricing.output
        + cache_write_5m * pricing.cache_write_5m
        + cache_write_1h * pricing.cache_write_1h
        + token_count(usage, CACHE_READ_TOKENS_FIELD) * pricing.cache_read
    ) / TOKENS_PER_MILLION
    if usage.get(INFERENCE_GEO_FIELD) == US_INFERENCE_GEO:
        return cost * US_INFERENCE_MULTIPLIER
    return cost


def cache_write_tokens(usage: Mapping[str, Any]) -> tuple[float, float]:
    breakdown = usage.get(CACHE_WRITE_BREAKDOWN_FIELD)
    if isinstance(breakdown, Mapping) and (FIVE_MINUTE_CACHE_WRITES_FIELD in breakdown or ONE_HOUR_CACHE_WRITES_FIELD in breakdown):
        return token_count(breakdown, FIVE_MINUTE_CACHE_WRITES_FIELD), token_count(breakdown, ONE_HOUR_CACHE_WRITES_FIELD)
    return token_count(usage, CACHE_WRITE_TOKENS_FIELD), 0


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
                session_id = entry.get(SESSION_ID_FIELD) or path_session_id
                if entry.get(TYPE_FIELD) == TITLE_ENTRY:
                    if isinstance(entry.get(CUSTOM_TITLE_FIELD), str):
                        copy_titles[session_id] = entry[CUSTOM_TITLE_FIELD]
                    continue
                entry_uuid = entry.get(UUID_FIELD)
                if entry.get(TYPE_FIELD) not in MESSAGE_ENTRIES or entry_uuid in seen_entries:
                    continue
                timestamp = parse_timestamp(entry.get(TIMESTAMP_FIELD))
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
        'prompts': 0,
        'assistant_messages': 0,
        'activity': [],
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
    record_activity(session['activity'], timestamp)
    if is_subagent:
        session['has_subagent_data'] = True
    else:
        session['has_main_data'] = True
    if entry.get(WORKING_DIRECTORY_FIELD) and not session['cwd']:
        session['cwd'] = entry[WORKING_DIRECTORY_FIELD]
    if entry.get(GIT_BRANCH_FIELD):
        session['git_branches'].add(entry[GIT_BRANCH_FIELD])
    if entry.get(TYPE_FIELD) == USER_ENTRY:
        session['user_messages'] += 1
        if not is_subagent and is_prompt(entry):
            session['prompts'] += 1
        return
    session['assistant_messages'] += 1
    message = entry.get(MESSAGE_FIELD)
    if isinstance(message, dict):
        record_usage(session, entry, message, responses)
        record_tools(session, message)


def record_activity(activity: list[list[datetime]], timestamp: datetime) -> None:
    if activity and activity[-1][0] <= timestamp <= activity[-1][1]:
        activity[-1][1] = max(activity[-1][1], timestamp + ACTIVE_GAP_CAP)
    else:
        activity.append([timestamp, timestamp + ACTIVE_GAP_CAP])


def merge_intervals(intervals: Iterable[Sequence[datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted((interval[0], interval[1]) for interval in intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def active_intervals(activity: list[list[datetime]], last: datetime) -> list[tuple[datetime, datetime]]:
    return [(start, min(end, last)) for start, end in merge_intervals(activity) if start < last]


def active_time(intervals: Iterable[tuple[datetime, datetime]]) -> timedelta:
    return sum((end - start for start, end in intervals), timedelta())


def is_prompt(entry: Mapping[str, Any]) -> bool:
    if entry.get(META_FIELD) or entry.get(COMPACT_SUMMARY_FIELD) or is_sent_by_program(entry):
        return False
    message = entry.get(MESSAGE_FIELD)
    content = message.get(CONTENT_FIELD) if isinstance(message, Mapping) else None
    if isinstance(content, list):
        blocks = [block for block in content if isinstance(block, Mapping)]
        if any(block.get(TYPE_FIELD) == TOOL_RESULT_BLOCK for block in blocks):
            return False
        content = next((block.get(TEXT_FIELD) for block in blocks if block.get(TYPE_FIELD) == TEXT_BLOCK), '')
    return isinstance(content, str) and not content.lstrip().startswith(HARNESS_PREFIXES)


def is_sent_by_program(entry: Mapping[str, Any]) -> bool:
    origin = entry.get(ORIGIN_FIELD)
    typed = isinstance(origin, Mapping) and origin.get(ORIGIN_KIND_FIELD) == HUMAN_ORIGIN
    return entry.get(PROMPT_SOURCE_FIELD) == SDK_PROMPT_SOURCE and not typed


def record_usage(
    session: dict[str, Any],
    entry: Mapping[str, Any],
    message: Mapping[str, Any],
    responses: dict[str, tuple[str, str, float, float]],
) -> None:
    model = message.get(MODEL_FIELD)
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
    usage = message.get(USAGE_FIELD)
    if not isinstance(usage, Mapping):
        return
    cost = estimate_cost(model, usage) or 0.0
    response_key = message.get(MESSAGE_ID_FIELD) or entry.get(UUID_FIELD)
    if not response_key:
        session['cost_by_model'][canonical] += cost
        return
    output_tokens = token_count(usage, OUTPUT_TOKENS_FIELD)
    previous = responses.get(response_key)
    if previous is None or output_tokens >= previous[2]:
        responses[response_key] = (session['id'], canonical, output_tokens, cost)


def record_tools(session: dict[str, Any], message: Mapping[str, Any]) -> None:
    content = message.get(CONTENT_FIELD)
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict) or block.get(TYPE_FIELD) != TOOL_USE_BLOCK:
            continue
        tool_name = block.get(TOOL_NAME_FIELD, '')
        session['tool_calls'].append(tool_name)
        tool_input = block.get(TOOL_INPUT_FIELD)
        if tool_name == SKILL_TOOL and isinstance(tool_input, dict) and tool_input.get(SKILL_FIELD):
            session['skills_used'].append(tool_input[SKILL_FIELD])


def finish_session(session: dict[str, Any], title: str) -> dict[str, Any]:
    created: datetime = session['first_timestamp']
    active = active_intervals(session['activity'], session['last_timestamp'])
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
        'turns': session['prompts'],
        'user_messages': session['user_messages'],
        'assistant_messages': session['assistant_messages'],
        'tool_calls': session['tool_calls'],
        'tool_count': len(session['tool_calls']),
        'skills_used': session['skills_used'],
        'project': project_name(session['cwd']),
        'git_branches': sorted(session['git_branches']),
        'title': title,
        'duration_minutes': round(active_time(active) / MINUTE, 1),
        'active_intervals': active,
        'source': session_source(session),
    }


def project_name(directory: str) -> str:
    return Path(WORKTREE_SEGMENT.sub('', directory)).name if directory else ''


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
    first_date = min(dates)
    last_date = max(dates)
    unique_days = len(set(dates))

    tool_counts = dict(Counter(tool for session in sessions for tool in session['tool_calls']).most_common(TOP_TOOLS))
    skill_counts = dict(Counter(skill for session in sessions for skill in session['skills_used']).most_common(TOP_SKILLS))
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

    durations = [session['duration_minutes'] for session in sessions if session['duration_minutes'] > 0]
    duration_stats = None
    if durations:
        durations_sorted = sorted(durations)
        active = merge_intervals(interval for session in sessions for interval in session['active_intervals'])
        duration_stats = {
            'median_minutes': round(durations_sorted[len(durations_sorted) // 2], 1),
            'average_minutes': round(sum(durations) / len(durations), 1),
            'max_minutes': round(max(durations), 1),
            'total_hours': round(active_time(active) / HOUR, 1),
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
            if len(word) >= MINIMUM_WORD_LENGTH and word not in TITLE_STOP_WORDS:
                title_words[word] += 1
    top_session_words = dict(title_words.most_common(TOP_WORDS))

    return {
        'summary': {
            'total_sessions': total,
            'total_cost_usd': round(total_cost, 2),
            'average_cost_per_session': round(total_cost / total, 4) if total else 0,
            'total_turns': total_turns,
            'average_turns_per_session': round(total_turns / total, 1) if total else 0,
            'total_tool_calls': total_tools,
            'average_tools_per_session': round(total_tools / total, 1) if total else 0,
            'date_range': f'{first_date} to {last_date}',
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
        description='Collect developer profile data from git repositories and Claude sessions',
        epilog=f'Claude costs are estimated from the list prices at {PRICING_SOURCE}',
    )
    parser.add_argument('base_directory', help='Base directory containing git repositories')
    parser.add_argument('--author', help='Git author name (auto-detected if omitted)')
    parser.add_argument(
        '--since',
        type=since_date,
        help=f'Start date in ISO format; the window starts at local midnight (default: {DEFAULT_WINDOW_DAYS} days ago)',
    )
    parser.add_argument('--format', choices=[JSON_FORMAT, CSV_FORMAT], default=JSON_FORMAT, help='Output format')
    parser.add_argument(
        '--config-dir',
        dest='config_directories',
        action='append',
        type=config_directory,
        metavar='PATH',
        help='Claude config directory to scan; repeatable (default: ~/.claude, every ~/.claude-* and $CLAUDE_CONFIG_DIR)',
    )
    arguments = parser.parse_args()

    since = arguments.since or (datetime.now() - timedelta(days=DEFAULT_WINDOW_DAYS)).strftime(DATE_FORMAT)

    repositories = find_repositories(arguments.base_directory)
    if not repositories:
        fail(f'No git repos found in {arguments.base_directory}')

    author = arguments.author or detect_author(repositories)
    if not author:
        fail('Could not detect git author. Use --author.')

    config_directories = arguments.config_directories or ()
    for directory in config_directories:
        if not (directory / PROJECTS_DIRECTORY).is_dir():
            print(f'Skipping --config-dir {directory}: it has no {PROJECTS_DIRECTORY}/ directory', file=sys.stderr)
    profiles = discover_profiles(config_directories)

    git_analysis = analyze_repositories(repositories, author, since)
    if arguments.format == CSV_FORMAT:
        if ERROR_KEY in git_analysis:
            fail(git_analysis[ERROR_KEY])
        print(to_csv(git_analysis))
        return

    claude_analysis = analyze_claude_sessions(collect_claude_sessions(since, profiles)) or {}
    result = {'git': git_analysis, 'claude': {**claude_analysis, 'profiles_scanned': [str(profile) for profile in profiles]}}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
