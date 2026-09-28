from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from collections.abc import Mapping
from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import collect

SINCE = '2020-01-01'
STALE_MODIFICATION_TIME = datetime(2019, 1, 1).timestamp()
TIMESTAMP = '2026-09-01T10:00:00.000Z'
AUCKLAND = 'Pacific/Auckland'
NEW_YORK = 'America/New_York'
UTC = 'UTC'
YEAR_BOUNDARY_DAYS = ('2026-12-31', '2027-01-01', '2027-01-04')
ISO_WEEKS = {'2026-W53': 2, '2027-W01': 1}
AUCKLAND_MORNING = '2026-09-01T13:30:00.000Z'
NEW_YORK_EVENING = '2026-09-01T02:00:00.000Z'
NEW_YORK_NIGHT = '2026-09-01T05:00:00.000Z'
NEW_YORK_EVENING_MODIFICATION_TIME = datetime(2026, 9, 1, 3, tzinfo=timezone.utc).timestamp()
MILLION = 1_000_000
PLACES = 6
PROJECTS = 'projects'
PROJECT = '-p'
MOVED_PROJECT = '-q'
OLD_TIMESTAMP = '2019-06-01T10:00:00.000Z'
WORKING_DIRECTORY = '/Users/me/p'
USER = 'user'
ASSISTANT = 'assistant'
CUSTOM_TITLE = 'custom-title'
CONFIG_DIRECTORY_VARIABLE = 'CLAUDE_CONFIG_DIR'
OPUS = 'claude-opus-5-5'
SONNET = 'claude-sonnet-5'
HAIKU = 'claude-haiku-4-5-20251001'
HAIKU_KEY = 'claude-haiku-4-5'
UNKNOWN_MODEL = 'gpt-4'
SYNTHETIC_MODEL = '<synthetic>'
INPUT_USAGE = {'input_tokens': MILLION}
PARTIAL_USAGE = {'input_tokens': MILLION, 'output_tokens': 1}
FINAL_FAST_USAGE = {'input_tokens': MILLION, 'output_tokens': MILLION, 'speed': 'fast'}
FINAL_FAST_COST = 48.0
PADDING = 'x' * 2000
TOOL_RESULT = [{'type': 'tool_result', 'tool_use_id': 't1', 'content': 'ok'}]
SESSION_KEYS = frozenset({
    'id', 'created', 'date', 'hour', 'weekday', 'week', 'month', 'model', 'models', 'cost', 'cost_by_model',
    'unpriced_models', 'turns', 'user_messages', 'assistant_messages', 'tool_calls', 'tool_count', 'skills_used',
    'project', 'git_branches', 'title', 'duration_minutes', 'source',
})


class SessionsTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        environment = mock.patch.dict(os.environ, {'HOME': str(self.home)})
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(CONFIG_DIRECTORY_VARIABLE, None)
        self.default_profile = self.home / '.claude'
        self.work_profile = self.home / '.claude-work'

    def use_time_zone(self, zone: str) -> None:
        self.addCleanup(time.tzset)
        environment = mock.patch.dict(os.environ, {'TZ': zone})
        environment.start()
        self.addCleanup(environment.stop)
        time.tzset()

    def user(
        self,
        session_id: str,
        uuid: str,
        content: object = 'go',
        timestamp: str = TIMESTAMP,
        cwd: str = WORKING_DIRECTORY,
    ) -> dict[str, Any]:
        return {
            'type': USER,
            'uuid': uuid,
            'sessionId': session_id,
            'timestamp': timestamp,
            'cwd': cwd,
            'message': {'role': USER, 'content': content},
        }

    def assistant(
        self,
        session_id: str,
        uuid: str,
        model: str = OPUS,
        usage: Mapping[str, object] = INPUT_USAGE,
        message_id: str | None = None,
        timestamp: str = TIMESTAMP,
    ) -> dict[str, Any]:
        return {
            'type': ASSISTANT,
            'uuid': uuid,
            'sessionId': session_id,
            'timestamp': timestamp,
            'cwd': WORKING_DIRECTORY,
            'message': {
                'id': message_id or f'message-{uuid}',
                'role': ASSISTANT,
                'model': model,
                'usage': dict(usage),
                'content': [{'type': 'text', 'text': 'done'}],
            },
        }

    def custom_title(self, session_id: str, title: str) -> dict[str, Any]:
        return {'type': CUSTOM_TITLE, 'customTitle': title, 'sessionId': session_id}

    def write(self, profile: Path, project: str, session_id: str, entries: Sequence[Mapping[str, Any]]) -> Path:
        path = profile / PROJECTS / project / f'{session_id}.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(entry) + '\n' for entry in entries), encoding='utf-8')
        return path

    def profile(self, path: Path) -> Path:
        (path / PROJECTS).mkdir(parents=True, exist_ok=True)
        return path

    def collect_sessions(self, *profiles: Path, since: str = SINCE) -> dict[str, dict[str, Any]]:
        sessions = collect.collect_claude_sessions(since, list(profiles))
        counts = Counter(session['id'] for session in sessions)
        repeated = [session_id for session_id, count in counts.items() if count > 1]
        self.assertEqual(repeated, [], 'a session is reported more than once')
        return {session['id']: session for session in sessions}

    def analyze(self, *profiles: Path) -> dict[str, Any]:
        analysis = collect.analyze_claude_sessions(collect.collect_claude_sessions(SINCE, list(profiles)))
        if analysis is None:
            self.fail('no sessions were analysed')
        return analysis

    def main(self, *arguments: str) -> tuple[dict[str, Any], str]:
        repository = self.root / 'code' / 'repository'
        repository.mkdir(parents=True)
        subprocess.run(
            ['git', 'init', '--quiet', str(repository)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        command_line = mock.patch.object(
            sys, 'argv', ['collect.py', str(repository.parent), '--author', 'Nobody', '--since', SINCE, *arguments],
        )
        output = io.StringIO()
        errors = io.StringIO()
        with command_line, contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            collect.main()
        result: dict[str, Any] = json.loads(output.getvalue())
        return result, errors.getvalue()

    def resolved(self, paths: Sequence[Path]) -> list[Path]:
        return [path.resolve() for path in paths]

    def test_identical_copies_are_counted_once(self) -> None:
        entries = [self.user('S1', 'u1'), self.assistant('S1', 'a1'), self.user('S1', 'u2'), self.assistant('S1', 'a2')]
        self.write(self.default_profile, PROJECT, 'S1', entries)
        self.write(self.work_profile, PROJECT, 'S1', entries)
        sessions = self.collect_sessions(self.default_profile, self.work_profile)
        self.assertEqual(list(sessions), ['S1'])
        self.assertEqual(sessions['S1']['user_messages'], 2)
        self.assertEqual(sessions['S1']['assistant_messages'], 2)
        self.assertAlmostEqual(sessions['S1']['cost_by_model'][OPUS], 8.0, places=PLACES)

    def test_diverged_copies_count_the_union_of_entries(self) -> None:
        shared = [self.user('S2', 'u1'), self.assistant('S2', 'a1')]
        smaller = self.write(self.default_profile, PROJECT, 'S2', [
            *shared,
            self.user('S2', 'u2'),
            self.assistant('S2', 'a2'),
        ])
        larger = self.write(self.work_profile, PROJECT, 'S2', [
            *shared,
            self.user('S2', 'u3'),
            self.assistant('S2', 'a3'),
            self.user('S2', 'u4'),
            self.assistant('S2', 'a4'),
        ])
        self.assertNotEqual(smaller.stat().st_size, larger.stat().st_size, 'the fixture copies must differ in size')
        sessions = self.collect_sessions(self.default_profile, self.work_profile)
        self.assertEqual(list(sessions), ['S2'])
        self.assertEqual(sessions['S2']['user_messages'], 4)
        self.assertEqual(sessions['S2']['assistant_messages'], 4)
        self.assertAlmostEqual(sessions['S2']['cost_by_model'][OPUS], 16.0, places=PLACES)

    def test_session_only_in_a_later_profile_is_included(self) -> None:
        self.write(self.default_profile, PROJECT, 'S1', [self.user('S1', 'u1'), self.assistant('S1', 'a1')])
        self.write(self.work_profile, PROJECT, 'S3', [self.user('S3', 'u3'), self.assistant('S3', 'a3')])
        sessions = self.collect_sessions(self.default_profile, self.work_profile)
        self.assertEqual(sorted(sessions), ['S1', 'S3'])
        self.assertEqual(sessions['S3']['user_messages'], 1)
        self.assertEqual(sessions['S3']['assistant_messages'], 1)

    def test_same_entries_under_another_path_are_counted_once(self) -> None:
        entries = [self.user('S4', 'u1'), self.assistant('S4', 'a1'), self.user('S4', 'u2'), self.assistant('S4', 'a2')]
        self.write(self.default_profile, PROJECT, 'S4', entries)
        self.write(self.default_profile, MOVED_PROJECT, 'S4', entries)
        sessions = self.collect_sessions(self.default_profile)
        self.assertEqual(list(sessions), ['S4'])
        self.assertEqual(sessions['S4']['user_messages'], 2)
        self.assertEqual(sessions['S4']['assistant_messages'], 2)
        self.assertAlmostEqual(sessions['S4']['cost_by_model'][OPUS], 8.0, places=PLACES)

    def test_copy_modified_before_since_is_dropped(self) -> None:
        shared = [self.user('S5', 'u1'), self.assistant('S5', 'a1')]
        stale = self.write(self.default_profile, PROJECT, 'S5', [
            *shared,
            self.user('S5', 'u2'),
            self.assistant('S5', 'a2'),
        ])
        os.utime(stale, (STALE_MODIFICATION_TIME, STALE_MODIFICATION_TIME))
        self.write(self.work_profile, PROJECT, 'S5', shared)
        session = self.collect_sessions(self.default_profile, self.work_profile)['S5']
        self.assertEqual(session['user_messages'], 1)
        self.assertEqual(session['assistant_messages'], 1)

    def test_last_custom_title_wins(self) -> None:
        self.write(self.default_profile, PROJECT, 'S6', [
            self.custom_title('S6', 'Original'),
            self.user('S6', 'u1'),
            self.assistant('S6', 'a1'),
            self.custom_title('S6', 'Renamed'),
            self.user('S6', 'u2'),
        ])
        self.assertEqual(self.collect_sessions(self.default_profile)['S6']['title'], 'Renamed')

    def test_largest_copy_title_wins(self) -> None:
        shared = [self.user('S7', 'u1'), self.assistant('S7', 'a1')]
        smaller = self.write(self.default_profile, PROJECT, 'S7', [*shared, self.custom_title('S7', 'Smaller')])
        larger = self.write(self.work_profile, PROJECT, 'S7', [
            *shared,
            self.user('S7', 'u2'),
            self.assistant('S7', 'a2'),
            self.custom_title('S7', 'Larger'),
        ])
        self.assertGreater(larger.stat().st_size, smaller.stat().st_size, 'the fixture copies must differ in size')
        self.assertEqual(self.collect_sessions(self.default_profile, self.work_profile)['S7']['title'], 'Larger')

    def test_model_is_the_most_frequent_non_synthetic_model(self) -> None:
        self.write(self.default_profile, PROJECT, 'S8', [
            self.user('S8', 'u1'),
            self.assistant('S8', 'a1', SONNET),
            self.assistant('S8', 'a2', OPUS),
            self.assistant('S8', 'a3', OPUS),
            self.assistant('S8', 'a4', SYNTHETIC_MODEL),
            self.assistant('S8', 'a5', SYNTHETIC_MODEL),
            self.assistant('S8', 'a6', SYNTHETIC_MODEL),
        ])
        self.assertEqual(self.collect_sessions(self.default_profile)['S8']['model'], OPUS)

    def test_model_tie_goes_to_the_first_seen(self) -> None:
        self.write(self.default_profile, PROJECT, 'S9', [
            self.user('S9', 'u1'),
            self.assistant('S9', 'a1', SONNET),
            self.assistant('S9', 'a2', OPUS),
        ])
        self.assertEqual(self.collect_sessions(self.default_profile)['S9']['model'], SONNET)

    def test_unknown_model_is_reported_unpriced(self) -> None:
        self.write(self.default_profile, PROJECT, 'S10', [
            self.user('S10', 'u1'),
            self.assistant('S10', 'a1', UNKNOWN_MODEL),
            self.assistant('S10', 'a2', UNKNOWN_MODEL),
            self.assistant('S10', 'a3', OPUS),
        ])
        session = self.collect_sessions(self.default_profile)['S10']
        self.assertEqual(session['unpriced_models'], {UNKNOWN_MODEL: 2})
        self.assertEqual(set(session['cost_by_model']), {OPUS})
        self.assertAlmostEqual(session['cost'], 4.0, places=PLACES)

    def test_synthetic_model_is_not_priced(self) -> None:
        self.write(self.default_profile, PROJECT, 'S11', [
            self.user('S11', 'u1'),
            self.assistant('S11', 'a1', SYNTHETIC_MODEL),
            self.assistant('S11', 'a2', HAIKU),
        ])
        session = self.collect_sessions(self.default_profile)['S11']
        self.assertNotIn(SYNTHETIC_MODEL, session['cost_by_model'])
        self.assertNotIn(SYNTHETIC_MODEL, session['unpriced_models'])
        self.assertEqual(set(session['cost_by_model']), {HAIKU_KEY})

    def test_cost_by_model_uses_canonical_keys(self) -> None:
        self.write(self.default_profile, PROJECT, 'S12', [
            self.user('S12', 'u1'),
            self.assistant('S12', 'a1', HAIKU),
            self.assistant('S12', 'a2', f'{OPUS}[1m]'),
        ])
        session = self.collect_sessions(self.default_profile)['S12']
        self.assertEqual(set(session['cost_by_model']), {HAIKU_KEY, OPUS})
        self.assertAlmostEqual(session['cost_by_model'][HAIKU_KEY], 1.0, places=PLACES)
        self.assertAlmostEqual(session['cost_by_model'][OPUS], 4.0, places=PLACES)
        self.assertEqual(session['unpriced_models'], {})

    def test_response_is_priced_once_from_its_final_usage_entry(self) -> None:
        self.write(self.default_profile, PROJECT, 'S13', [
            self.user('S13', 'u1'),
            self.assistant('S13', 'a1', usage=PARTIAL_USAGE, message_id='m1'),
            self.assistant('S13', 'a2', usage=FINAL_FAST_USAGE, message_id='m1'),
        ])
        session = self.collect_sessions(self.default_profile)['S13']
        self.assertEqual(session['assistant_messages'], 2)
        self.assertAlmostEqual(session['cost_by_model'][OPUS], FINAL_FAST_COST, places=PLACES)

    def test_tied_usage_entries_are_priced_from_the_later_one(self) -> None:
        tied = {'input_tokens': MILLION, 'output_tokens': MILLION}
        self.write(self.default_profile, PROJECT, 'S70', [
            self.user('S70', 'u1'),
            self.assistant('S70', 'a1', usage=tied, message_id='m3'),
            self.assistant('S70', 'a2', usage={**tied, 'speed': 'fast'}, message_id='m3'),
        ])
        self.assertAlmostEqual(self.collect_sessions(self.default_profile)['S70']['cost'], FINAL_FAST_COST, places=PLACES)

    def test_response_without_any_identifier_is_still_priced(self) -> None:
        anonymous = {**self.assistant('S71', 'a1'), 'uuid': None}
        anonymous['message']['id'] = None
        self.write(self.default_profile, PROJECT, 'S71', [self.user('S71', 'u1'), anonymous])
        self.assertAlmostEqual(self.collect_sessions(self.default_profile)['S71']['cost'], 4.0, places=PLACES)

    def test_final_usage_entry_from_a_smaller_copy_wins(self) -> None:
        partial = self.assistant('S20', 'a1', usage=PARTIAL_USAGE, message_id='m2')
        larger = self.write(self.default_profile, PROJECT, 'S20', [
            self.user('S20', 'u1'),
            partial,
            self.user('S20', 'u2', PADDING),
        ])
        smaller = self.write(self.work_profile, PROJECT, 'S20', [
            self.user('S20', 'u1'),
            partial,
            self.assistant('S20', 'a2', usage=FINAL_FAST_USAGE, message_id='m2'),
        ])
        self.assertGreater(larger.stat().st_size, smaller.stat().st_size, 'the partial-only copy must be the largest')
        session = self.collect_sessions(self.default_profile, self.work_profile)['S20']
        self.assertEqual(session['assistant_messages'], 2)
        self.assertAlmostEqual(session['cost_by_model'][OPUS], FINAL_FAST_COST, places=PLACES)

    def test_session_times_are_local(self) -> None:
        self.use_time_zone(AUCKLAND)
        self.write(self.default_profile, PROJECT, 'S21', [
            self.user('S21', 'u1', timestamp=AUCKLAND_MORNING),
            self.assistant('S21', 'a1', timestamp=AUCKLAND_MORNING),
        ])
        session = self.collect_sessions(self.default_profile)['S21']
        fields = {key: session[key] for key in ('created', 'date', 'hour', 'weekday', 'week', 'month')}
        self.assertEqual(fields, {
            'created': '2026-09-02T01:30:00',
            'date': '2026-09-02',
            'hour': 1,
            'weekday': 'Wednesday',
            'week': '2026-W36',
            'month': '2026-09',
        })
        self.assertEqual(list(self.collect_sessions(self.default_profile, since='2026-09-02')), ['S21'])

    def test_entry_filter_agrees_with_the_modification_time_filter(self) -> None:
        self.use_time_zone(NEW_YORK)
        stale = self.write(self.default_profile, PROJECT, 'S22', [self.user('S22', 'u1', timestamp=NEW_YORK_EVENING)])
        os.utime(stale, (NEW_YORK_EVENING_MODIFICATION_TIME, NEW_YORK_EVENING_MODIFICATION_TIME))
        self.write(self.default_profile, PROJECT, 'S23', [self.user('S23', 'u2', timestamp=NEW_YORK_EVENING)])
        self.write(self.default_profile, PROJECT, 'S24', [self.user('S24', 'u3', timestamp=NEW_YORK_NIGHT)])
        self.assertEqual(list(self.collect_sessions(self.default_profile, since='2026-09-01')), ['S24'])

    def test_since_with_a_time_and_offset_starts_at_that_local_midnight(self) -> None:
        self.use_time_zone(AUCKLAND)
        self.write(self.default_profile, PROJECT, 'S25', [self.user('S25', 'u1', timestamp='2026-08-30T11:30:00.000Z')])
        self.write(self.default_profile, PROJECT, 'S26', [self.user('S26', 'u2', timestamp='2026-08-31T11:30:00.000Z')])
        self.assertEqual(list(self.collect_sessions(self.default_profile, since='2026-09-01T00:00:00+13:00')), ['S26'])

    def test_timestamps_of_one_instant_agree_in_every_format(self) -> None:
        self.use_time_zone(AUCKLAND)
        instant = datetime(2026, 9, 1, 13, 30, tzinfo=timezone.utc)
        values: tuple[object, ...] = (
            '2026-09-01T13:30:00Z',
            AUCKLAND_MORNING,
            '2026-09-02T01:30:00+12:00',
            instant.timestamp(),
            int(instant.timestamp() * 1000),
        )
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(collect.parse_timestamp(value), datetime(2026, 9, 2, 1, 30))
        invalid_values: tuple[object, ...] = (None, 'yesterday', 1e30, [], {})
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                self.assertIsNone(collect.parse_timestamp(invalid))

    def test_weeks_are_keyed_by_iso_year(self) -> None:
        self.use_time_zone(UTC)
        for number, day in enumerate(YEAR_BOUNDARY_DAYS):
            session_id = f'S3{number}'
            self.write(self.default_profile, PROJECT, session_id, [
                self.user(session_id, f'u3{number}', timestamp=f'{day}T12:00:00.000Z'),
                self.assistant(session_id, f'a3{number}', timestamp=f'{day}T12:00:00.000Z'),
            ])
        analysis = self.analyze(self.default_profile)
        self.assertEqual(analysis['by_week'], ISO_WEEKS)
        self.assertEqual(list(analysis['cost_by_week']), list(ISO_WEEKS))

    def test_project_hours_cover_the_busiest_projects(self) -> None:
        sessions_per_project = {'p00': 1, **{f'p{number:02d}': 2 for number in range(1, 10)}, 'p10': 3}
        minute = 0
        for project, count in sessions_per_project.items():
            for _ in range(count):
                session_id = f'S-{project}-{minute}'
                timestamp = f'2026-09-01T10:{minute:02d}:00.000Z'
                self.write(self.default_profile, PROJECT, session_id, [
                    self.user(session_id, f'u{minute}', timestamp=timestamp, cwd=f'/u/Local/{project}'),
                ])
                minute += 1
        busiest = sorted(project for project in sessions_per_project if project != 'p00')
        self.assertEqual(sorted(self.analyze(self.default_profile)['by_project_hour']), busiest)

    def test_worktree_sessions_belong_to_their_repository(self) -> None:
        directories = (
            '/u/Local/zone/.claude/worktrees/brave-fox-1a2b',
            '/u/Local/zone/.claude/worktrees/calm-owl-3c4d/src',
            '/u/Local/zone',
        )
        for number, directory in enumerate(directories):
            session_id = f'S4{number}'
            self.write(self.default_profile, PROJECT, session_id, [self.user(session_id, f'u4{number}', cwd=directory)])
        sessions = self.collect_sessions(self.default_profile)
        self.assertEqual({session_id: session['project'] for session_id, session in sessions.items()}, {
            'S40': 'zone',
            'S41': 'src',
            'S42': 'zone',
        })

    def test_turns_count_prompts_not_tool_results_or_meta_entries(self) -> None:
        self.write(self.default_profile, PROJECT, 'S50', [
            self.user('S50', 'u1', 'fix the login bug'),
            self.assistant('S50', 'a1'),
            self.user('S50', 'u2', TOOL_RESULT),
            self.user('S50', 'u3', TOOL_RESULT),
            self.user('S50', 'u4', TOOL_RESULT),
            {**self.user('S50', 'u5', 'caveat'), 'isMeta': True},
            {**self.user('S50', 'u6', 'summary of the conversation'), 'isCompactSummary': True},
            self.user('S50', 'u7', [{'type': 'text', 'text': 'and this screenshot?'}, {'type': 'image', 'source': {}}]),
        ])
        session = self.collect_sessions(self.default_profile)['S50']
        self.assertEqual(session['user_messages'], 7)
        self.assertEqual(session['turns'], 2)

    def test_turns_skip_harness_messages_and_subagent_prompts(self) -> None:
        self.write(self.default_profile, PROJECT, 'S51', [
            self.user('S51', 'u1', '<command-name>/review</command-name>'),
            self.user('S51', 'u2', '<task-notification>done</task-notification>'),
            self.user('S51', 'u3', '<local-command-stdout>ok</local-command-stdout>'),
            self.user('S51', 'u4', '<ci-monitor-event>green</ci-monitor-event>'),
            self.user('S51', 'u5', '<bash-stdout>ok</bash-stdout><bash-stderr></bash-stderr>'),
            self.user('S51', 'u6', [{'type': 'text', 'text': '[Request interrupted by user]'}]),
        ])
        self.write(self.default_profile, f'{PROJECT}/S51/subagents', 'agent-1', [self.user('S51', 'u7', 'review the diff')])
        session = self.collect_sessions(self.default_profile)['S51']
        self.assertEqual(session['user_messages'], 7)
        self.assertEqual(session['turns'], 1)

    def test_active_time_caps_idle_gaps_and_counts_subagent_work(self) -> None:
        self.write(self.default_profile, PROJECT, 'S52', [
            self.user('S52', 'u1', timestamp='2026-09-01T10:00:00.000Z'),
            self.assistant('S52', 'a1', timestamp='2026-09-01T10:01:00.000Z'),
            self.user('S52', 'u2', timestamp='2026-09-01T12:01:00.000Z'),
        ])
        self.write(self.default_profile, PROJECT, 'S53', [
            self.user('S53', 'u3', timestamp='2026-09-01T14:00:00.000Z'),
            self.assistant('S53', 'a3', timestamp='2026-09-01T14:40:00.000Z'),
        ])
        self.write(self.default_profile, f'{PROJECT}/S53/subagents', 'agent-1', [
            self.assistant('S53', f'a4{minute}', timestamp=f'2026-09-01T14:{minute}:00.000Z') for minute in (10, 20, 30)
        ])
        sessions = self.collect_sessions(self.default_profile)
        self.assertEqual(sessions['S52']['duration_minutes'], 16.0)
        self.assertEqual(sessions['S53']['duration_minutes'], 40.0)

    def test_total_hours_count_parallel_sessions_once(self) -> None:
        for session_id in ('S54', 'S55'):
            self.write(self.default_profile, PROJECT, session_id, [
                self.user(session_id, f'{session_id}-{minute}', timestamp=f'2026-09-01T10:{minute:02d}:00.000Z')
                for minute in range(0, 60, 5)
            ] + [self.user(session_id, f'{session_id}-end', timestamp='2026-09-01T11:00:00.000Z')])
        duration = self.analyze(self.default_profile)['duration']
        self.assertEqual(duration['max_minutes'], 60.0)
        self.assertEqual(duration['total_hours'], 1.0)

    def without_session_id(self, entry: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in entry.items() if key != 'sessionId'}

    def test_entries_before_since_are_ignored(self) -> None:
        self.write(self.default_profile, PROJECT, 'S60', [
            self.user('S60', 'u1', timestamp=OLD_TIMESTAMP),
            self.assistant('S60', 'a1', timestamp=OLD_TIMESTAMP),
            self.user('S60', 'u2'),
            self.assistant('S60', 'a2'),
        ])
        session = self.collect_sessions(self.default_profile)['S60']
        self.assertEqual((session['user_messages'], session['assistant_messages']), (1, 1))
        self.assertAlmostEqual(session['cost'], 4.0, places=PLACES)

    def test_same_size_copy_with_other_content_is_ignored(self) -> None:
        first = self.write(self.default_profile, PROJECT, 'S61', [self.user('S61', 'u1'), self.assistant('S61', 'a1')])
        second = self.write(self.work_profile, PROJECT, 'S61', [
            self.user('S61', 'u9', cwd='/Users/me/q'),
            self.assistant('S61', 'a9'),
        ])
        self.assertEqual(first.stat().st_size, second.stat().st_size, 'the fixture copies must be the same size')
        session = self.collect_sessions(self.default_profile, self.work_profile)['S61']
        self.assertEqual((session['user_messages'], session['assistant_messages']), (1, 1))
        self.assertEqual(session['project'], 'p')

    def test_session_source_reflects_where_data_survived(self) -> None:
        self.write(self.default_profile, PROJECT, 'S62', [self.user('S62', 'u1')])
        self.write(self.default_profile, f'{PROJECT}/S62/subagents', 'agent-1', [self.user('S62', 'u2')])
        self.write(self.default_profile, PROJECT, 'S63', [self.user('S63', 'u3')])
        self.write(self.default_profile, f'{PROJECT}/S64/subagents', 'agent-2', [self.user('S64', 'u4')])
        sources = {session_id: session['source'] for session_id, session in self.collect_sessions(self.default_profile).items()}
        self.assertEqual(sources, {'S62': 'main+subagent', 'S63': 'main-only', 'S64': 'subagent-only'})
        self.assertEqual(self.analyze(self.default_profile)['data_sources'], {'main+subagent': 1, 'main-only': 1, 'subagent-only': 1})

    def test_files_without_session_ids_belong_to_the_session_in_their_path(self) -> None:
        workflow = f'{PROJECT}/S65/subagents/workflows/wf_1'
        self.write(self.default_profile, workflow, 'agent-1', [self.without_session_id(self.user('S65', 'u1'))])
        self.write(self.default_profile, f'{PROJECT}/S65/subagents', 'agent-2', [self.without_session_id(self.user('S65', 'u2'))])
        self.write(self.default_profile, PROJECT, 'S66', [self.without_session_id(self.user('S66', 'u3'))])
        sessions = self.collect_sessions(self.default_profile)
        self.assertEqual(sorted(sessions), ['S65', 'S66'])
        self.assertEqual(sessions['S65']['user_messages'], 2)

    def test_first_working_directory_names_the_project(self) -> None:
        self.write(self.default_profile, PROJECT, 'S67', [
            self.user('S67', 'u1', cwd='/u/Local/first'),
            self.user('S67', 'u2', cwd='/u/Local/second'),
        ])
        self.assertEqual(self.collect_sessions(self.default_profile)['S67']['project'], 'first')

    def test_tool_calls_and_skills_are_counted(self) -> None:
        response = self.assistant('S68', 'a1')
        response['message']['content'] = [
            {'type': 'text', 'text': 'running'},
            {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'ls'}},
            {'type': 'tool_use', 'name': 'Skill', 'input': {'skill': 'skills:commit'}},
        ]
        follow_up = self.assistant('S68', 'a2')
        follow_up['message']['content'] = [{'type': 'tool_use', 'name': 'Bash', 'input': {}}]
        self.write(self.default_profile, PROJECT, 'S68', [self.user('S68', 'u1'), response, follow_up])
        session = self.collect_sessions(self.default_profile)['S68']
        self.assertEqual(session['tool_calls'], ['Bash', 'Skill', 'Bash'])
        self.assertEqual(session['tool_count'], 3)
        self.assertEqual(session['skills_used'], ['skills:commit'])
        analysis = self.analyze(self.default_profile)
        self.assertEqual(analysis['tools'], {'Bash': 2, 'Skill': 1})
        self.assertEqual(analysis['skills'], {'skills:commit': 1})
        self.assertEqual(analysis['summary']['total_tool_calls'], 3)

    def test_malformed_lines_are_skipped(self) -> None:
        path = self.default_profile / PROJECTS / PROJECT / 'S69.jsonl'
        path.parent.mkdir(parents=True)
        without_timestamp = {key: value for key, value in self.user('S69', 'u4').items() if key != 'timestamp'}
        lines = [
            json.dumps(self.user('S69', 'u1'), separators=(',', ':')).encode(),
            json.dumps(self.assistant('S69', 'a1')).encode(),
            b'[]',
            json.dumps([self.user('S69', 'u2')]).encode(),
            json.dumps(self.user('S69', 'u3', 'caf\u00e9'), ensure_ascii=False).encode().replace('caf\u00e9'.encode(), b'caf\xff'),
            json.dumps(without_timestamp).encode(),
            json.dumps(self.user('S69', 'u5', timestamp='not a time')).encode(),
            json.dumps(self.user('S69', 'u6'))[:60].encode(),
        ]
        path.write_bytes(b'\n'.join(lines))
        session = self.collect_sessions(self.default_profile)['S69']
        self.assertEqual((session['user_messages'], session['assistant_messages']), (1, 1))

    def test_session_keeps_existing_keys(self) -> None:
        self.write(self.default_profile, PROJECT, 'S14', [self.user('S14', 'u1'), self.assistant('S14', 'a1')])
        session = self.collect_sessions(self.default_profile)['S14']
        self.assertEqual(sorted(SESSION_KEYS - set(session)), [])

    def test_analysis_totals_cost_by_model(self) -> None:
        self.write(self.default_profile, PROJECT, 'S15', [
            self.custom_title('S15', 'Pricing overhaul'),
            self.user('S15', 'u1'),
            self.assistant('S15', 'a1', SONNET, {'input_tokens': 1234}),
            self.assistant('S15', 'a2', HAIKU),
            self.assistant('S15', 'a3', UNKNOWN_MODEL),
        ])
        self.write(self.default_profile, PROJECT, 'S16', [
            self.user('S16', 'u2'),
            self.assistant('S16', 'a4', OPUS),
            self.assistant('S16', 'a5', OPUS, {'output_tokens': MILLION}),
            self.assistant('S16', 'a6', UNKNOWN_MODEL),
        ])
        analysis = self.analyze(self.default_profile)
        expected = [(OPUS, 24.0), (HAIKU_KEY, 1.0), (SONNET, 0.0025)]
        self.assertEqual(list(analysis['cost_by_model'].items()), expected)
        self.assertEqual(analysis['unpriced_models'], {UNKNOWN_MODEL: 2})
        self.assertIn('overhaul', analysis['top_session_words'])

    def test_discover_profiles_puts_the_default_first_and_sorts_the_rest(self) -> None:
        default = self.profile(self.default_profile)
        work = self.profile(self.work_profile)
        backup = self.profile(self.home / '.claude-backup')
        configured = self.profile(self.root / 'configured')
        self.profile(self.home / '.claude_old')
        (self.home / '.claude-empty').mkdir()
        (self.home / '.claude-notes').write_text('', encoding='utf-8')
        (self.home / '.claude.json').write_text('{}', encoding='utf-8')
        (self.home / '.claude.json.backup').write_text('{}', encoding='utf-8')
        os.environ[CONFIG_DIRECTORY_VARIABLE] = str(configured)
        expected = [default, *sorted([work, backup, configured])]
        self.assertEqual(self.resolved(collect.discover_profiles()), self.resolved(expected))

    def test_config_dir_that_is_also_a_profile_is_listed_once(self) -> None:
        default = self.profile(self.default_profile)
        work = self.profile(self.work_profile)
        link = self.root / 'work-link'
        link.symlink_to(work, target_is_directory=True)
        for configured in (str(work), f'{work}/', str(link)):
            with self.subTest(configured=configured):
                os.environ[CONFIG_DIRECTORY_VARIABLE] = configured
                self.assertEqual(self.resolved(collect.discover_profiles()), self.resolved([default, work]))

    def test_explicit_profiles_replace_discovery(self) -> None:
        self.profile(self.default_profile)
        self.profile(self.work_profile)
        os.environ[CONFIG_DIRECTORY_VARIABLE] = str(self.profile(self.root / 'configured'))
        alpha = self.profile(self.root / 'alpha')
        without_projects = self.root / 'beta'
        without_projects.mkdir()
        gamma = self.profile(self.root / 'gamma')
        discovered = collect.discover_profiles([alpha, without_projects, gamma, alpha])
        self.assertEqual(self.resolved(discovered), self.resolved([alpha, gamma]))

    def test_main_scans_only_the_given_config_dirs(self) -> None:
        self.write(self.default_profile, PROJECT, 'S17', [self.user('S17', 'u1'), self.assistant('S17', 'a1')])
        self.write(self.work_profile, PROJECT, 'S18', [self.user('S18', 'u2'), self.assistant('S18', 'a2', HAIKU)])
        self.write(self.home / '.claude-other', PROJECT, 'S19', [self.user('S19', 'u3'), self.assistant('S19', 'a3')])
        result, _ = self.main('--config-dir', str(self.default_profile), '--config-dir', str(self.work_profile))
        claude = result['claude']
        scanned = [Path(profile) for profile in claude['profiles_scanned']]
        self.assertEqual(self.resolved(scanned), self.resolved([self.default_profile, self.work_profile]))
        self.assertEqual(claude['summary']['total_sessions'], 2)
        self.assertEqual(claude['cost_by_model'], {OPUS: 4.0, HAIKU_KEY: 1.0})

    def test_main_reports_scanned_profiles_even_without_sessions(self) -> None:
        empty = self.profile(self.root / 'empty')
        tilde = self.profile(self.home / '.claude-tilde')
        missing = self.root / 'missing'
        missing.mkdir()
        result, errors = self.main(
            '--config-dir', str(empty), '--config-dir', str(missing), '--config-dir', '~/.claude-tilde',
        )
        claude = result['claude']
        self.assertEqual(list(claude), ['profiles_scanned'])
        scanned = [Path(profile) for profile in claude['profiles_scanned']]
        self.assertEqual(self.resolved(scanned), self.resolved([empty, tilde]))
        self.assertIn(f'Skipping --config-dir {missing}: it has no projects/ directory', errors)


if __name__ == '__main__':
    unittest.main()
