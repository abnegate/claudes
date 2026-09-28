from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import collect

COMMIT_TYPES = ('feat', 'fix', 'refactor', 'chore', 'docs', 'test', 'style', 'perf', 'ci', 'build', 'revert', 'wip')
FEAT = 'feat'
FIX = 'fix'
REFACTOR = 'refactor'
CHORE = 'chore'
MERGE = 'merge'
OTHER = 'other'


class ClassifyTest(unittest.TestCase):
    def test_commit_types(self) -> None:
        self.assertEqual(collect.COMMIT_TYPES, COMMIT_TYPES)

    def test_conventional_pattern_captures_type_scope_and_breaking_marker(self) -> None:
        cases = (
            ('feat(api)!: remove v1 routes', {'type': FEAT, 'scope': 'api', 'breaking': '!'}),
            ('fix(skills/pr): wait for checks', {'type': FIX, 'scope': 'skills/pr', 'breaking': None}),
            ('chore!: drop python 3.8', {'type': CHORE, 'scope': None, 'breaking': '!'}),
            ('docs: explain profiles', {'type': 'docs', 'scope': None, 'breaking': None}),
        )
        for subject, groups in cases:
            with self.subTest(subject=subject):
                match = collect.CONVENTIONAL_SUBJECT.match(subject)
                if match is None:
                    self.fail(f'{subject!r} does not match')
                self.assertEqual(match.groupdict(), groups)

    def test_conventional_pattern_rejects_other_subjects(self) -> None:
        for subject in ('(refactor): x', 'Merge branch x', 'feat x', 'feat(api) x', 'random'):
            with self.subTest(subject=subject):
                self.assertIsNone(collect.CONVENTIONAL_SUBJECT.match(subject))

    def test_legacy_pattern_captures_type(self) -> None:
        match = collect.LEGACY_SUBJECT.match('(refactor): x')
        if match is None:
            self.fail('the legacy subject does not match')
        self.assertEqual(match['type'], REFACTOR)
        self.assertIsNone(collect.LEGACY_SUBJECT.match('refactor: x'))

    def test_scoped_breaking_subject(self) -> None:
        self.assertEqual(collect.classify_commit('feat(api)!: x'), FEAT)

    def test_breaking_subject_without_scope(self) -> None:
        self.assertEqual(collect.classify_commit('feat!: x'), FEAT)

    def test_breaking_fix_without_scope(self) -> None:
        self.assertEqual(collect.classify_commit('fix!: x'), FIX)

    def test_legacy_subject(self) -> None:
        self.assertEqual(collect.classify_commit('(refactor): x'), REFACTOR)

    def test_scoped_subject(self) -> None:
        self.assertEqual(collect.classify_commit('chore(release): x'), CHORE)

    def test_merge_subject(self) -> None:
        self.assertEqual(collect.classify_commit('Merge branch x'), MERGE)

    def test_keyword_subject(self) -> None:
        self.assertEqual(collect.classify_commit('Add x'), FEAT)

    def test_unmatched_subject(self) -> None:
        self.assertEqual(collect.classify_commit('random'), OTHER)

    def test_every_commit_type_in_every_form(self) -> None:
        for commit_type in COMMIT_TYPES:
            subjects = (
                f'{commit_type}: x',
                f'{commit_type}(scope): x',
                f'{commit_type}!: x',
                f'{commit_type}(scope)!: x',
                f'({commit_type}): x',
            )
            for subject in subjects:
                with self.subTest(subject=subject):
                    self.assertEqual(collect.classify_commit(subject), commit_type)

    def test_subject_case_is_ignored(self) -> None:
        self.assertEqual(collect.classify_commit('Feat(API)!: X'), FEAT)
        self.assertEqual(collect.classify_commit('(FIX): x'), FIX)

    def test_unknown_type_falls_back_to_keywords(self) -> None:
        self.assertEqual(collect.classify_commit('fixup: x'), FIX)
        self.assertEqual(collect.classify_commit('hotfix(api): x'), OTHER)


if __name__ == '__main__':
    unittest.main()
