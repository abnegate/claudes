from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import collect

AUTHOR = 'Tester'
EMAIL = 'tester@example.com'
ZONE = 'Pacific/Auckland'
CONFIG_DIRECTORY_VARIABLE = 'CLAUDE_CONFIG_DIR'
TIME_FIELDS = ('date', 'time', 'hour', 'weekday', 'week', 'month')


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
        self.git(path, 'init', '--quiet')
        return path

    def commit(self, repository: Path, subject: str, authored: str, committed: str | None = None) -> None:
        dates = {'GIT_AUTHOR_DATE': authored, 'GIT_COMMITTER_DATE': committed or authored}
        self.git(repository, 'commit', '--quiet', '--allow-empty', '--message', subject, environment=dates)

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


if __name__ == '__main__':
    unittest.main()
