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
from collections.abc import Mapping
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import collect

AUTHOR = 'Tester'
EMAIL = 'tester@example.com'
ZONE = 'Pacific/Auckland'
BRANCH = 'main'
MIDDAY_IN_ZONE = datetime(2026, 9, 27, 23, tzinfo=timezone.utc)
CONFIG_DIRECTORY_VARIABLE = 'CLAUDE_CONFIG_DIR'
TIME_FIELDS = ('date', 'time', 'hour', 'weekday', 'week', 'month')
YEAR_BOUNDARY_DAYS = ('2026-12-31', '2027-01-01', '2027-01-04')
ISO_WEEKS = {'2026-W53': 2, '2027-W01': 1}


class GitTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        configuration = self.root / 'gitconfig'
        configuration.write_text('', encoding='utf-8')
        self.addCleanup(time.tzset)
        environment = mock.patch.dict(os.environ, {
            'HOME': str(self.root),
            'TZ': ZONE,
            'GIT_CONFIG_GLOBAL': str(configuration),
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_AUTHOR_NAME': AUTHOR,
            'GIT_AUTHOR_EMAIL': EMAIL,
            'GIT_COMMITTER_NAME': AUTHOR,
            'GIT_COMMITTER_EMAIL': EMAIL,
            'GIT_TEST_DATE_NOW': str(int(MIDDAY_IN_ZONE.timestamp())),
        })
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(CONFIG_DIRECTORY_VARIABLE, None)
        time.tzset()

    def git(self, repository: Path, *arguments: str, environment: Mapping[str, str] | None = None) -> str:
        return subprocess.run(
            ['git', '-C', str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **(environment or {})},
        ).stdout

    def repository(self, name: str) -> Path:
        path = self.root / 'code' / name
        path.mkdir(parents=True)
        self.git(path, 'init', '--quiet', f'--initial-branch={BRANCH}')
        return path

    def commit(self, repository: Path, subject: str, authored: str, committed: str | None = None) -> None:
        dates = {'GIT_AUTHOR_DATE': authored, 'GIT_COMMITTER_DATE': committed or authored}
        self.git(repository, 'commit', '--quiet', '--allow-empty', '--message', subject, environment=dates)

    def invoke(self, *arguments: str) -> tuple[object, str, str]:
        command_line = mock.patch.object(sys, 'argv', ['collect.py', str(self.root / 'code'), '--author', AUTHOR, *arguments])
        output = io.StringIO()
        errors = io.StringIO()
        code: object = 0
        with command_line, contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                collect.main()
            except SystemExit as stop:
                code = stop.code
        return code, output.getvalue(), errors.getvalue()

    def main(self, *arguments: str) -> dict[str, Any]:
        code, output, errors = self.invoke(*arguments)
        self.assertEqual(code, 0, errors)
        result: dict[str, Any] = json.loads(output)
        return result

    def subjects(self, commits: list[dict[str, Any]]) -> list[str]:
        return sorted(commit['subject'] for commit in commits)

    def times(self, commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{field: commit[field] for field in TIME_FIELDS} for commit in commits]

    def test_commit_times_are_local(self) -> None:
        repository = self.repository('zone')
        self.commit(repository, 'feat: late night', '2026-09-01T13:30:00+00:00')
        commits = collect.collect_commits(str(repository), AUTHOR, '2026-08-01')
        self.assertEqual(self.times(commits), [{
            'date': '2026-09-02',
            'time': '01:30',
            'hour': 1,
            'weekday': 'Wednesday',
            'week': '2026-W36',
            'month': '2026-09',
        }])

    def test_window_starts_at_local_midnight(self) -> None:
        repository = self.repository('zone')
        self.commit(repository, 'feat: before midnight', '2026-09-20T23:59:59')
        self.commit(repository, 'feat: after midnight', '2026-09-21T00:00:01')
        commits = collect.collect_commits(str(repository), AUTHOR, '2026-09-21')
        self.assertEqual(self.subjects(commits), ['feat: after midnight'])

    def test_rebased_commit_is_dated_by_its_author_date(self) -> None:
        repository = self.repository('zone')
        self.commit(repository, 'fix: written before the window', '2026-09-01T12:00:00', '2026-09-25T12:00:00')
        self.commit(repository, 'fix: written in the window', '2026-09-22T12:00:00', '2026-09-25T12:00:00')
        commits = collect.collect_commits(str(repository), AUTHOR, '2026-09-21')
        self.assertEqual([(commit['subject'], commit['date']) for commit in commits], [('fix: written in the window', '2026-09-22')])

    def cherry_pick(self, repository: Path, branch: str, base: str, commit: str, committed: str) -> None:
        self.git(repository, 'checkout', '--quiet', '-b', branch, base)
        self.git(repository, 'cherry-pick', '--allow-empty', commit, environment={'GIT_COMMITTER_DATE': committed})
        self.git(repository, 'checkout', '--quiet', BRANCH)

    def test_clones_and_rebased_copies_count_once(self) -> None:
        alpha = self.repository('alpha')
        self.commit(alpha, 'chore: start', '2026-09-21T10:00:00')
        self.commit(alpha, 'feat: one', '2026-09-22T10:00:00')
        self.commit(alpha, 'fix: two', '2026-09-23T10:00:00')
        beta = self.root / 'code' / 'beta'
        self.git(self.root, 'clone', '--quiet', str(alpha), str(beta))
        self.cherry_pick(alpha, 'rebased-two', 'HEAD~1', BRANCH, '2026-09-24T10:00:00')
        self.cherry_pick(beta, 'rebased-one', 'HEAD~2', f'{BRANCH}~1', '2026-09-25T10:00:00')
        self.commit(beta, 'docs: three', '2026-09-24T12:00:00')
        git = self.main('--since', '2026-09-01')['git']
        self.assertEqual(git['summary']['total_commits'], 4)
        self.assertEqual(git['by_repo'], {'alpha': 3, 'beta': 1})

    def test_stash_is_not_counted(self) -> None:
        repository = self.repository('zone')
        (repository / 'notes.txt').write_text('first\n', encoding='utf-8')
        self.git(repository, 'add', 'notes.txt')
        self.commit(repository, 'docs: add notes', '2026-09-22T10:00:00')
        (repository / 'notes.txt').write_text('second\n', encoding='utf-8')
        self.git(repository, 'stash', '--quiet')
        commits = collect.collect_commits(str(repository), AUTHOR, '2026-09-01')
        self.assertEqual(self.subjects(commits), ['docs: add notes'])
        self.assertEqual(collect.collect_repository_context(str(repository))['recent_subjects'], ['docs: add notes'])

    def test_repositories_sharing_a_name_are_counted_together(self) -> None:
        first = self.repository('one/tool')
        second = self.repository('two/tool')
        self.commit(first, 'feat: first tool', '2026-09-22T10:00:00')
        self.commit(second, 'feat: second tool', '2026-09-23T10:00:00')
        git = self.main('--since', '2026-09-01')['git']
        self.assertEqual(git['summary']['total_commits'], 2)
        self.assertEqual(git['by_repo'], {'tool': 2})

    def test_uncommitted_paths_keep_every_status(self) -> None:
        repository = self.repository('zone')
        for name in ('f1', 'f2', 'f3', 'kept.txt', 'old name'):
            (repository / name).write_text(f'{name}\n', encoding='utf-8')
        self.git(repository, 'add', '--all')
        self.commit(repository, 'chore: add files', '2026-09-22T10:00:00')
        for name in ('f1', 'f2', 'kept.txt'):
            (repository / name).write_text('changed\n', encoding='utf-8')
        self.git(repository, 'add', 'kept.txt')
        (repository / 'f3').unlink()
        self.git(repository, 'mv', 'old name', 'new name')
        (repository / 'fresh.txt').write_text('fresh\n', encoding='utf-8')
        self.git(repository, 'add', 'fresh.txt')
        (repository / 'loose.txt').write_text('loose\n', encoding='utf-8')
        self.assertEqual(collect.collect_repository_context(str(repository))['uncommitted'], {
            'modified': ['f1', 'f2', 'kept.txt'],
            'added': ['fresh.txt'],
            'deleted': ['f3'],
            'renamed': ['new name'],
            'untracked': ['loose.txt'],
        })

    def test_clean_repository_has_no_uncommitted_paths(self) -> None:
        repository = self.repository('zone')
        self.commit(repository, 'chore: start', '2026-09-22T10:00:00')
        self.assertNotIn('uncommitted', collect.collect_repository_context(str(repository)))

    def test_weeks_are_keyed_by_iso_year(self) -> None:
        repository = self.repository('zone')
        for day in YEAR_BOUNDARY_DAYS:
            self.commit(repository, f'feat: work on {day}', f'{day}T12:00:00')
        commits = collect.collect_commits(str(repository), AUTHOR, '2026-12-01')
        analysis = collect.analyze(commits, {'zone': commits})
        self.assertEqual(analysis['by_week'], ISO_WEEKS)
        self.assertEqual(analysis['by_repo_week'], {'zone': ISO_WEEKS})
        rows = collect.to_csv(analysis).splitlines()
        self.assertEqual(rows, ['Week,zone,Total', '2026-W53,2,2', '2027-W01,1,1', 'Total,3,3'])

    def test_since_must_be_an_iso_date(self) -> None:
        self.commit(self.repository('zone'), 'feat: start', '2026-09-22T10:00:00')
        code, output, errors = self.invoke('--since', '3 months ago')
        self.assertEqual(code, 2)
        self.assertEqual(output, '')
        self.assertIn("argument --since: expected an ISO date such as 2026-01-31, got '3 months ago'", errors)

    def test_since_with_an_offset_starts_at_that_local_day(self) -> None:
        repository = self.repository('zone')
        self.commit(repository, 'feat: day before', '2026-08-30T23:30:00')
        self.commit(repository, 'feat: same local day', '2026-08-31T23:30:00')
        session = self.root / '.claude' / 'projects' / '-p' / 'S1.jsonl'
        session.parent.mkdir(parents=True)
        entry = {'type': 'user', 'uuid': 'u1', 'sessionId': 'S1', 'timestamp': '2026-09-01T00:00:00.000Z', 'cwd': '/p'}
        session.write_text(json.dumps(entry) + '\n', encoding='utf-8')
        result = self.main('--since', '2026-09-01T00:00:00+13:00')
        self.assertEqual(result['git']['summary']['date_range'], '2026-08-31 to 2026-08-31')
        self.assertEqual(result['claude']['summary']['total_sessions'], 1)

    def test_csv_without_commits_is_a_clean_error(self) -> None:
        self.commit(self.repository('zone'), 'feat: old', '2026-01-05T10:00:00')
        code, output, errors = self.invoke('--since', '2026-09-01', '--format', 'csv')
        self.assertEqual(code, 1, errors)
        self.assertEqual(json.loads(output), {'error': 'No commits found'})

    def test_analysis_summarises_commits(self) -> None:
        repository = self.repository('zone')
        self.commit(repository, 'feat(api): add login', '2026-09-26T09:30:00')
        self.commit(repository, 'fix: login redirect', '2026-09-26T22:00:00')
        self.commit(repository, 'Merge branch main', '2026-09-28T13:00:00')
        commits = collect.collect_commits(str(repository), AUTHOR, '2026-09-01')
        analysis = collect.analyze(commits, {'zone': commits})
        self.assertEqual(analysis['summary'], {
            'total_commits': 3,
            'repos_active': 1,
            'date_range': '2026-09-26 to 2026-09-28',
            'date_range_days': 3,
            'unique_active_days': 2,
            'commits_per_active_day': 1.5,
            'commits_per_calendar_day': 1.0,
            'weekday_commits': 1,
            'weekend_commits': 2,
            'weekend_percentage': 66.7,
            'busiest_day': {'date': '2026-09-26', 'count': 2},
        })
        self.assertEqual(analysis['by_type'], {'feat': 1, 'fix': 1, 'merge': 1})
        self.assertEqual(analysis['by_time_bucket'], {'morning': 1, 'night': 1, 'lunch': 1})
        self.assertEqual(analysis['by_day_of_week']['Saturday'], 2)
        self.assertEqual(analysis['by_hour'][22], 1)
        self.assertEqual(analysis['by_repo_type'], {'zone': {'feat': 1, 'fix': 1, 'merge': 1}})
        self.assertEqual(analysis['top_words']['login'], 2)

    def test_streaks(self) -> None:
        today = date.today()
        days = [(today - timedelta(days=offset)).isoformat() for offset in (0, 0, 1, 2, 5, 6, 7, 8, 20)]
        self.assertEqual(collect.compute_streaks(days), {
            'current': 3,
            'longest': 4,
            'longest_start': (today - timedelta(days=8)).isoformat(),
            'longest_end': (today - timedelta(days=5)).isoformat(),
        })
        until_yesterday = [(today - timedelta(days=offset)).isoformat() for offset in (1, 2)]
        self.assertEqual(collect.compute_streaks(until_yesterday)['current'], 2)
        stale = [(today - timedelta(days=offset)).isoformat() for offset in (3, 4)]
        self.assertEqual(collect.compute_streaks(stale)['current'], 0)
        self.assertEqual(collect.compute_streaks([]), {'current': 0, 'longest': 0, 'longest_start': None, 'longest_end': None})


if __name__ == '__main__':
    unittest.main()
