from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from collections.abc import Mapping
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import collect

SINCE = '2020-01-01'
STALE_MODIFICATION_TIME = datetime(2019, 1, 1).timestamp()
TIMESTAMP = '2026-09-01T10:00:00.000Z'
MILLION = 1_000_000
PLACES = 6
PROJECTS = 'projects'
PROJECT = '-p'
MOVED_PROJECT = '-q'
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

    def user(self, session_id: str, uuid: str) -> dict[str, Any]:
        return {
            'type': USER,
            'uuid': uuid,
            'sessionId': session_id,
            'timestamp': TIMESTAMP,
            'cwd': WORKING_DIRECTORY,
            'message': {'role': USER, 'content': 'go'},
        }

    def assistant(
        self,
        session_id: str,
        uuid: str,
        model: str = OPUS,
        usage: Mapping[str, int] = INPUT_USAGE,
    ) -> dict[str, Any]:
        return {
            'type': ASSISTANT,
            'uuid': uuid,
            'sessionId': session_id,
            'timestamp': TIMESTAMP,
            'cwd': WORKING_DIRECTORY,
            'message': {
                'id': f'message-{uuid}',
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

    def collect_sessions(self, *profiles: Path) -> dict[str, dict[str, Any]]:
        sessions = collect.collect_claude_sessions(SINCE, list(profiles))
        counts = Counter(session['id'] for session in sessions)
        repeated = [session_id for session_id, count in counts.items() if count > 1]
        self.assertEqual(repeated, [], 'a session is reported more than once')
        return {session['id']: session for session in sessions}

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

    def test_content_blocks_of_one_response_are_priced_once(self) -> None:
        response = self.assistant('S13', 'a1')
        next_block = {**response, 'uuid': 'a2'}
        self.write(self.default_profile, PROJECT, 'S13', [self.user('S13', 'u1'), response, next_block])
        session = self.collect_sessions(self.default_profile)['S13']
        self.assertEqual(session['assistant_messages'], 2)
        self.assertAlmostEqual(session['cost_by_model'][OPUS], 4.0, places=PLACES)

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
        analysis = collect.analyze_claude_sessions(collect.collect_claude_sessions(SINCE, [self.default_profile]))
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
        repository = self.root / 'code' / 'repository'
        repository.mkdir(parents=True)
        subprocess.run(
            ['git', 'init', '--quiet', str(repository)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        arguments = [
            'collect.py', str(repository.parent), '--author', 'Nobody', '--since', SINCE,
            '--config-dir', str(self.default_profile), '--config-dir', str(self.work_profile),
        ]
        output = io.StringIO()
        command_line = mock.patch.object(sys, 'argv', arguments)
        with command_line, contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            collect.main()
        claude = json.loads(output.getvalue())['claude']
        scanned = [Path(profile) for profile in claude['profiles_scanned']]
        self.assertEqual(self.resolved(scanned), self.resolved([self.default_profile, self.work_profile]))
        self.assertEqual(claude['summary']['total_sessions'], 2)
        self.assertEqual(claude['cost_by_model'], {OPUS: 4.0, HAIKU_KEY: 1.0})


if __name__ == '__main__':
    unittest.main()
