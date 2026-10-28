"""Lightweight source-provenance regressions; no timing or memory benchmark."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark_delivery as benchmark


class PerformanceBaselineSourcesTests(unittest.TestCase):
    def setUp(self):
        # Keep disposable repositories in the writable task tree on restricted
        # Windows hosts; the platform TEMP may permit files but deny children.
        scratch = benchmark.ROOT / '.pipeline-runtime'
        scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='baseline-source-', dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / 'repository'
        self.repository.mkdir()
        self.git('init', '-q')
        self.write(self.repository, 'Core/Data/Fixture.lua', "ns.fixtureData='recorded-data'\n")
        self.write(self.repository, 'Core/Fixture.lua', "ns.fixtureDomain='recorded-domain'\n")
        self.git('add', 'Core')
        self.git('-c', 'user.name=Baseline Test', '-c', 'user.email=baseline@example.invalid',
                 'commit', '-qm', 'Recorded baseline')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.snapshot = self.root / 'snapshot'
        self.snapshot.mkdir()
        (self.snapshot / 'manifest.json').write_text(json.dumps({'head': self.head}), encoding='utf8')
        self.write(self.snapshot / 'files', 'Core/Fixture.lua', "ns.fixtureDomain='saved-dirty-domain'\n")
        self.write(self.repository, 'Core/Data/Fixture.lua', "ns.fixtureData='current-data'\n")
        self.write(self.repository, 'Core/Fixture.lua', "ns.fixtureDomain='current-domain'\n")
        self.write(self.repository, 'Core/New.lua', "ns.newFile='must-not-enter-baseline'\n")
        self.write(self.repository, 'Core/Data/Data_ProfLearningSources.lua', 'ns.ProfLearningSources={}\n')
        self.git('add', 'Core')
        self.git('-c', 'user.name=Baseline Test', '-c', 'user.email=baseline@example.invalid',
                 'commit', '-qm', 'New current sources')

    @staticmethod
    def write(root, path, text):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf8', newline='\n')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repository,
                                       stderr=subprocess.PIPE).decode('utf8')

    def test_saved_dirty_source_takes_precedence_over_both_commits(self):
        source = benchmark.BaselineSources(self.snapshot, self.repository)
        self.assertEqual(source.read(Path('Core/Fixture.lua')), "ns.fixtureDomain='saved-dirty-domain'\n")
        self.assertEqual(source.origins['Core/Fixture.lua'], 'pre-implementation snapshot')

    def test_unsaved_clean_source_uses_recorded_head_even_after_head_changes(self):
        source = benchmark.BaselineSources(self.snapshot, self.repository)
        self.assertNotEqual(self.git('rev-parse', 'HEAD').strip(), self.head)
        self.assertEqual(source.read(Path('Core/Data/Fixture.lua')), "ns.fixtureData='recorded-data'\n")
        self.assertEqual(source.origins['Core/Data/Fixture.lua'], 'recorded clean HEAD')

    def test_new_current_file_missing_in_recorded_head_is_an_error(self):
        source = benchmark.BaselineSources(self.snapshot, self.repository)
        with self.assertRaises(subprocess.CalledProcessError):
            source.read(Path('Core/New.lua'))

    def test_native_baseline_uses_the_same_resolver_for_data_and_domain(self):
        with patch.object(benchmark, 'FILES', ('Fixture.lua',)), \
                patch.object(benchmark, 'DOMAIN', ('Fixture.lua',)):
            lua = benchmark.native(self.snapshot / 'files', source_root=self.repository,
                                   baseline_repository=self.repository)
        self.assertEqual(lua.globals().ns['fixtureData'], 'recorded-data')
        self.assertEqual(lua.globals().ns['fixtureDomain'], 'saved-dirty-domain')
        self.assertIsNone(lua.globals().ns['ProfLearningSources'])

    def test_native_without_baseline_uses_only_the_explicit_current_tree(self):
        with patch.object(benchmark, 'FILES', ('Fixture.lua',)), \
                patch.object(benchmark, 'DOMAIN', ('Fixture.lua',)):
            lua = benchmark.native(source_root=self.repository)
        self.assertEqual(lua.globals().ns['fixtureData'], 'current-data')
        self.assertEqual(lua.globals().ns['fixtureDomain'], 'current-domain')
        self.assertIsNotNone(lua.globals().ns['ProfLearningSources'])


if __name__ == '__main__':
    unittest.main()
