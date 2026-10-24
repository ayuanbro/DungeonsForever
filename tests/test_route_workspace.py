"""The route editor saves existing baselines without external imports or deployment."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'df-data-pipeline/_temp'
SCRIPTS = ('_route_paths.py', '_route_gen.py', '_route_serve.py', '_route_faction.py',
           '_route_write_pins.py', '_route_qicons.py', '_route_make_tune.py', 'gen_route_lua.py')


def snapshot(paths):
    return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in paths if p.is_file()}


class RouteWorkspaceTests(unittest.TestCase):
    def setUp(self):
        runtime = ROOT / '.pipeline-runtime'
        runtime.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='route-save-', dir=runtime)
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.scripts = self.repo / 'df-data-pipeline/_temp'
        self.scripts.mkdir(parents=True)
        for name in SCRIPTS:
            shutil.copy2(SOURCE / name, self.scripts / name)
        shutil.copytree(SOURCE / '_route_plan', self.scripts / '_route_plan')
        for path in SOURCE.glob('_route_*.json'):
            shutil.copy2(path, self.scripts / path.name)
        self.data = self.scripts.parent / 'Core/Data'
        shutil.copytree(ROOT / 'Core/Data', self.data)

    def save(self, payload):
        result = subprocess.run(
            [sys.executable, '-B', '-c',
             "import json,sys,_route_serve; print(json.dumps(_route_serve.do_save(sys.stdin.buffer.read())))"],
            input=json.dumps(payload).encode('utf-8'), cwd=self.scripts,
            capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        return json.loads(result.stdout)

    def test_save_replays_baseline_and_preserves_other_overrides(self):
        official = list((ROOT / 'Core/Data').rglob('*.lua'))
        official_before = snapshot(official)
        baselines = list((self.scripts / '_route_plan/data').glob('*.json'))
        baseline_before = snapshot(baselines)
        overrides_path = self.scripts / '_route_override.json'
        original = json.loads(overrides_path.read_text(encoding='utf-8'))
        floors = original['blackfathom']
        floors['221']['segs']['1']['pts'] = [[11.1, 22.2], [33.3, 44.4]]
        payload = {'dungeon': 'blackfathom_deeps', 'fdr': 'blackfathom',
                   'data': {'floors': floors, 'qicons': {'6561': [31.2, 42.3, 1]},
                            'qtips': {'6561': '测试提示'}, 'qhide': {'6561': 1}}}
        result = self.save(payload)
        self.assertTrue(result['ok'], result)
        self.assertEqual(set(result), {'ok', 'log', 'brief', 'where'})
        self.assertIn('df-data-pipeline/Core/Data', result['log'])
        self.assertNotIn('同步客户端', result['log'])
        current = json.loads(overrides_path.read_text(encoding='utf-8'))
        self.assertEqual(current['ragefire'], original['ragefire'])
        self.assertEqual(current['blackfathom'], floors)
        self.assertIn('{ 11.1, 22.2 }, { 33.3, 44.4 }',
                      (self.data / 'Data_Route.lua').read_text(encoding='utf-8'))
        self.assertIn('{ 31.2, 42.3, 6561, 1 }',
                      (self.data / 'Data_MapPins.lua').read_text(encoding='utf-8'))
        html = (self.scripts / '_route_plan/tune.html').read_text(encoding='utf-8')
        self.assertIn('测试提示', html)
        # loadDungeon() merges this injected OVR over DATA when the page reloads.
        page_overrides = json.loads(re.search(r'^const OVR = (.*);$', html, re.M).group(1))
        self.assertEqual(page_overrides['blackfathom_deeps']['221']['segs']['1']['pts'],
                         [[11.1, 22.2], [33.3, 44.4]])
        self.assertEqual(snapshot(baselines), baseline_before)
        self.assertEqual(snapshot(official), official_before)

    def test_missing_workspace_fails_before_saving(self):
        (self.data / 'Data_MapPins.lua').unlink()
        overrides = list(self.scripts.glob('_route_*.json'))
        before = snapshot(overrides)
        result = self.save({'dungeon': 'blackfathom_deeps', 'data': {'qtips': {'6561': 'new'}}})
        self.assertFalse(result['ok'])
        self.assertIn('prepare_workspace.py', result['err'])
        self.assertEqual(snapshot(overrides), before)

    def test_amplitude_changes_reach_page_and_lua_without_changing_baseline(self):
        official_before = snapshot((ROOT / 'Core/Data').rglob('*.lua'))
        baseline_before = snapshot((self.scripts / '_route_plan/data').glob('*.json'))
        overrides_path = self.scripts / '_route_override.json'
        original = json.loads(overrides_path.read_text(encoding='utf-8'))
        floors = json.loads(json.dumps(original['blackfathom']))
        # Let this existing segment use automatic geometry; other manual segments stay intact.
        del floors['221']['segs']['1']
        results = []
        for amplitude in (2.0, 8.0, 2.0):
            floors['221']['amp'] = {'1': amplitude}
            result = self.save({'dungeon': 'blackfathom_deeps', 'fdr': 'blackfathom',
                                'data': {'floors': floors}})
            self.assertTrue(result['ok'], result)
            html = (self.scripts / '_route_plan/tune.html').read_text(encoding='utf-8')
            page = json.loads(re.search(r'^const DATA = (.*);$', html, re.M).group(1))
            dungeon = next(row for row in page['dungeons'] if row['id'] == 'blackfathom_deeps')
            floor = next(row for row in dungeon['floors'] if row['ui'] == '221')
            points = floor['segs'][0]['pts']
            self.assertFalse(floor['segs'][0]['ovr'])
            lua = (self.data / 'Data_Route.lua').read_text(encoding='utf-8')
            body = re.search(r'\["blackfathom_deeps"\] = \{\s*\[1\] = \{\s*\{'
                             r'.*?pts = \{(.*?)\n {16}\},', lua, re.S).group(1)
            lua_points = [[float(x), float(y)] for x, y in
                          re.findall(r'\{ ([\d.-]+), ([\d.-]+) \}', body)]
            self.assertEqual(lua_points, [[float('%.1f' % x), float('%.1f' % y)] for x, y in points])
            results.append(points)
            current = json.loads(overrides_path.read_text(encoding='utf-8'))
            self.assertEqual(current['blackfathom'], floors)
            self.assertEqual(current['ragefire'], original['ragefire'])
        self.assertNotEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][-1], results[1][-1])
        self.assertEqual(snapshot((self.scripts / '_route_plan/data').glob('*.json')), baseline_before)
        self.assertEqual(snapshot((ROOT / 'Core/Data').rglob('*.lua')), official_before)

    def test_amplitude_without_raw_source_fails_before_any_write(self):
        for filename in ('blackfathom_deeps.json', 'index.json'):
            with self.subTest(filename=filename):
                path = self.scripts / '_route_plan/data' / filename
                original = path.read_text(encoding='utf-8')
                baseline = json.loads(original)
                if filename == 'index.json':
                    dungeon = next(row for row in baseline['dungeons'] if row['id'] == 'blackfathom_deeps')
                    next(row for row in dungeon['floors'] if row['ui'] == '221')['raw'] = []
                else:
                    baseline['221']['raw'] = []
                path.write_text(json.dumps(baseline), encoding='utf-8')
                paths = list(self.scripts.rglob('*')) + list(self.data.rglob('*'))
                before = snapshot(paths)
                result = self.save({'dungeon': 'blackfathom_deeps', 'fdr': 'blackfathom',
                                    'data': {'floors': {'221': {'amp': {'1': 8.0}}}}})
                self.assertFalse(result['ok'], result)
                self.assertIn('amp', result['err'])
                self.assertEqual(snapshot(paths), before)
                path.write_text(original, encoding='utf-8')

    def test_amplitude_replay_preserves_baseline_and_repeated_segment_numbers(self):
        spec = importlib.util.spec_from_file_location('route_geometry_test', self.scripts / '_route_gen.py')
        geometry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(geometry)
        index = json.loads((self.scripts / '_route_plan/data/index.json').read_text(encoding='utf-8'))
        verified, repeated = 0, 0
        repeated_floor = None
        for dungeon in index['dungeons']:
            for floor in dungeon['floors']:
                automatic = [s for s in floor['segs'] if not s.get('ovr')]
                if not automatic:
                    continue
                original = json.loads(json.dumps(floor))
                rebuilt = geometry.replay_amplitudes(floor, {'amp': {str(s['n']): 4.2 for s in automatic}})
                self.assertEqual(floor, original)
                for before, after in zip(floor['segs'], rebuilt):
                    if not before.get('ovr'):
                        self.assertEqual(after['pts'], before['pts'])
                        verified += 1
                numbers = [s['n'] for s in floor['segs']]
                if len(numbers) != len(set(numbers)):
                    repeated += 1
                    for number in numbers:
                        matches = [s for s in floor['segs'] if s['n'] == number]
                        if len(matches) > 1 and all(len(s['pts']) > 4 for s in matches):
                            repeated_floor = floor, number
        self.assertGreaterEqual(verified, 168)
        self.assertGreaterEqual(repeated, 7)
        self.assertIsNotNone(repeated_floor)
        floor, number = repeated_floor
        changed = geometry.replay_amplitudes(floor, {'amp': {str(number): 8.0}})
        for before, after in zip(floor['segs'], changed):
            if before['n'] == number:
                self.assertNotEqual(after['pts'], before['pts'])
            else:
                self.assertEqual(after, before)

    def test_path_like_dungeon_is_rejected_before_saving(self):
        before = snapshot(self.scripts.glob('_route_*.json'))
        result = self.save({'dungeon': '../../outside', 'data': {'qtips': {'1': 'new'}}})
        self.assertFalse(result['ok'])
        self.assertEqual(snapshot(self.scripts.glob('_route_*.json')), before)

    def test_linked_data_directory_is_rejected_before_saving(self):
        real_data = self.data.with_name('Data-original')
        self.data.rename(real_data)
        try:
            self.data.symlink_to(real_data, target_is_directory=True)
        except OSError as error:
            if os.name != 'nt':
                self.skipTest('Directory symlinks are not available: %s' % error)
            # Junctions need no Windows symlink privilege and exercise the same boundary.
            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-Command',
                 'New-Item -ItemType Junction -Path $env:DF_ROUTE_TEST_LINK '
                 '-Target $env:DF_ROUTE_TEST_TARGET -ErrorAction Stop | Out-Null'],
                env=dict(os.environ, DF_ROUTE_TEST_LINK=str(self.data),
                         DF_ROUTE_TEST_TARGET=str(real_data)), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
            self.addCleanup(self.data.rmdir)
        else:
            self.addCleanup(self.data.unlink)
        before = snapshot(self.scripts.glob('_route_*.json'))
        data_before = snapshot(real_data.rglob('*.lua'))
        result = self.save({'dungeon': 'blackfathom_deeps', 'data': {'qtips': {'6561': 'new'}}})
        self.assertFalse(result['ok'])
        self.assertIn('symlinks or junctions', result['err'])
        self.assertEqual(snapshot(self.scripts.glob('_route_*.json')), before)
        self.assertEqual(snapshot(real_data.rglob('*.lua')), data_before)


if __name__ == '__main__':
    unittest.main()
