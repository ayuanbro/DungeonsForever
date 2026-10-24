"""All-vendor affiliations can be reproduced without caches, browsers or ID lists."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import update_vendor_factions as REFRESH
sys.path.remove(str(ROOT / 'scripts'))
TOOLS = ROOT / 'df-data-pipeline/_temp'
sys.path.insert(0, str(TOOLS))
import fc_prof_items as ITEMS
import fc_pipeline as PIPELINE
sys.path.remove(str(TOOLS))


def csv_bytes(fields, values):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(fields)
    writer.writerows(values)
    return stream.getvalue().encode('utf-8')


def payload(npc, faction=None):
    html = '<table><tr><td>Seller %d</td></tr><tr><td>Level 40 Humanoid (Normal)</td></tr>' % npc
    if faction:
        html += '<tr><td>%s</td></tr>' % faction
    html += '</table>'
    return REFRESH.encoded({'name': 'Seller %d' % npc, 'tooltip': html})


class VendorFactionRefreshTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / '.pipeline-runtime/tmp'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='全商人 重放-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name)
        self.bundle = self.stage / 'source'
        self.output = self.stage / 'result'
        self.vendor = csv_bytes(['item_id', 'npc_id', 'side', 'cost_copper'],
                                [[1, 9001, 'h', 123], [2, 9002, '', 1], [3, 9003, 'n', 9], [4, 9001, 'a', 44]])
        self.vendor_path = self.stage / 'vendors.csv'
        self.vendor_path.write_bytes(self.vendor)
        factions = csv_bytes(['ID', 'Name_enUS', 'Name_zhCN', 'Name_zhTW'],
                             [[21, 'Test Clan', '测试组织', '測試組織']])
        client_manifest = {'files': {'factions.csv': {'sha256': REFRESH.digest(factions), 'bytes': len(factions)}}}
        self.files = {'vendors.csv': self.vendor, 'nether/9001.json': payload(9001, 'Test Clan'),
                      'nether/9002.json': payload(9002, 'Unmapped Society'), 'nether/9003.json': payload(9003),
                      'client/factions.csv': factions, 'client/manifest.json': REFRESH.encoded(client_manifest)}

    def freeze(self, files=None):
        files = files or self.files
        manifest = {'schemaVersion': 1, 'targets': REFRESH.targets(self.vendor),
                    'files': {key: {'sha256': REFRESH.digest(value), 'bytes': len(value)}
                              for key, value in files.items()}}
        for key, value in {**files, 'manifest.json': REFRESH.encoded(manifest)}.items():
            path = self.bundle / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        return manifest, REFRESH.encoded(manifest)

    def args(self):
        return SimpleNamespace(vendors_csv=self.vendor_path, collect=False, capture_cache=False,
                               snapshot_dir=self.bundle, output_dir=self.output, install_input=False)

    def binding(self, files, content):
        files['client/npc-factions.csv'] = content
        manifest = json.loads(files['client/manifest.json'])
        manifest['files']['npc-factions.csv'] = {'sha256': REFRESH.digest(content), 'bytes': len(content)}
        files['client/manifest.json'] = REFRESH.encoded(manifest)

    def test_dynamic_complete_npc_set_keeps_name_only_and_missing_affiliations(self):
        manifest, content = self.freeze()
        original = dict(self.files)
        data, audit = REFRESH.build(manifest, content, self.files, self.vendor)
        self.assertEqual(audit['targets'], 3)
        self.assertEqual(set(audit['npcs']), {'9001', '9002', '9003'})
        self.assertEqual(data['npcs']['9001']['factionID'], 21)
        self.assertEqual(data['npcs']['9001']['names']['zhTW'], '測試組織')
        self.assertNotIn('factionID', data['npcs']['9002'])
        self.assertEqual(audit['npcs']['9003']['status'], 'no-affiliation')
        self.assertNotIn('side', data['npcs']['9001'])
        self.assertEqual(self.files, original)

    def test_missing_raw_payload_remains_in_coverage_ledger(self):
        del self.files['nether/9003.json']
        manifest, content = self.freeze()
        _, audit = REFRESH.build(manifest, content, self.files, self.vendor)
        self.assertEqual(audit['npcs']['9003']['status'], 'missing-payload')
        self.assertEqual(audit['targets'], 3)

    def test_incomplete_cache_can_be_audited_but_cannot_replace_installed_inputs(self):
        del self.files['nether/9001.json']
        self.freeze()
        self.output.mkdir()
        previous = self.output / 'npc-factions.json'
        previous.write_bytes(b'previous successful JSON')
        args = self.args()
        args.install_input = True
        with mock.patch.object(REFRESH, 'DEFAULT_INPUT', self.stage / 'not-installed.json'):
            with self.assertRaisesRegex(ValueError, 'missing NPC evidence prevents'):
                REFRESH.run(args)
        self.assertEqual(previous.read_bytes(), b'previous successful JSON')
        self.assertFalse((self.stage / 'not-installed.json').exists())
        audit = json.loads((self.output / 'audit.json').read_bytes())
        self.assertEqual(audit['npcs']['9001']['status'], 'missing-payload')

    def test_new_npc_requires_new_snapshot_and_cannot_silently_disappear(self):
        manifest, content = self.freeze()
        changed = self.vendor + b'5,9004,a,10\r\n'
        with self.assertRaisesRegex(ValueError, 'NPC set differs'):
            REFRESH.build(manifest, content, self.files, changed)

    def test_offline_verifies_every_frozen_byte_before_use(self):
        self.freeze()
        (self.bundle / 'nether/9001.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            REFRESH.frozen(self.bundle)

    def test_export_manifest_tampering_is_rejected_even_with_outer_snapshot_hash(self):
        self.files['client/factions.csv'] += b'99,Injected Clan,,\r\n'
        manifest, content = self.freeze()
        with self.assertRaisesRegex(ValueError, 'client export hash mismatch'):
            REFRESH.build(manifest, content, self.files, self.vendor)

    def test_client_tooltip_id_conflict_preserves_previous_output(self):
        self.files['nether/9001.json'] = payload(9001, '<a href="/forever/faction=22">Other Clan</a>')
        binding = csv_bytes(['npc_id', 'faction_id', 'status'], [[9001, 21, 'resolved']])
        self.binding(self.files, binding)
        self.freeze()
        self.output.mkdir()
        prior = self.output / 'npc-factions.json'
        prior.write_bytes(b'previous successful JSON')
        with self.assertRaisesRegex(ValueError, 'conflicting affiliations'):
            REFRESH.run(self.args())
        self.assertEqual(prior.read_bytes(), b'previous successful JSON')
        audit = json.loads((self.output / 'audit.json').read_bytes())
        self.assertEqual(audit['conflicts'], [9001])

    def test_client_partial_or_conflicting_chains_never_establish_a_faction(self):
        for status in ('missing-template', 'missing-faction', 'no-faction', 'conflict'):
            with self.subTest(status=status):
                files = dict(self.files)
                self.binding(files, csv_bytes(['npc_id', 'faction_id', 'status'], [[9003, '', status]]))
                manifest, content = self.freeze(files)
                data, audit = REFRESH.build(manifest, content, files, self.vendor)
                self.assertNotIn('9003', data['npcs'])
                self.assertEqual(audit['npcs']['9003']['clientStatus'], status)

    def test_two_offline_cli_runs_from_other_working_directories_are_identical(self):
        self.freeze()
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.bundle.rglob('*') if p.is_file()}
        for name, cwd in (('result-a', self.stage), ('result-b', ROOT / 'tests')):
            output = self.stage / name
            command = [sys.executable, '-B', str(ROOT / 'scripts/update_vendor_factions.py'), '--offline',
                       '--vendors-csv', str(self.vendor_path), '--snapshot-dir', str(self.bundle),
                       '--output-dir', str(output)]
            result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        for name in ('npc-factions.json', 'audit.json', 'faction-sources/manifest.json'):
            self.assertEqual((self.stage / 'result-a' / name).read_bytes(), (self.stage / 'result-b' / name).read_bytes())
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}, before)

    def test_replay_never_calls_a_network_collector(self):
        self.freeze()
        with mock.patch.object(REFRESH.collector, 'NpcNether', side_effect=AssertionError('network')):
            REFRESH.run(self.args())

    def test_cache_capture_error_keeps_previous_output(self):
        self.output.mkdir()
        prior = self.output / 'npc-factions.json'
        prior.write_bytes(b'previous successful JSON')
        args = self.args()
        args.capture_cache, args.cache_dir, args.client_dir = True, self.stage / 'cache', None
        files = {'vendors.csv': self.vendor,
                 'locales/zhCN.lua': (ROOT / 'Core/Data/Data_Factions.lua').read_bytes(),
                 'locales/zhTW.lua': (ROOT / 'Core/Data/zhTW/Data_Factions.lua').read_bytes()}
        manifest = {'schemaVersion': 1, 'targets': REFRESH.targets(self.vendor),
                    'collection': {'9001:enUS': {'status': 'error', 'diagnostics': []}}}
        with mock.patch.object(REFRESH, 'capture', return_value=(manifest, REFRESH.encoded(manifest), files)):
            with self.assertRaisesRegex(ValueError, 'collection failed'):
                REFRESH.run(args)
        self.assertEqual(prior.read_bytes(), b'previous successful JSON')
        self.assertTrue((self.output / 'audit.json').is_file())

    def test_output_collision_cannot_overwrite_vendor_input(self):
        self.freeze()
        self.output.mkdir()
        args = self.args()
        args.vendors_csv = self.output / 'audit.json'
        args.vendors_csv.write_bytes(self.vendor)
        with self.assertRaisesRegex(ValueError, 'overwrite a source input'):
            REFRESH.run(args)
        self.assertEqual(args.vendors_csv.read_bytes(), self.vendor)

    def test_vendor_changes_during_generation_keep_previous_output(self):
        self.freeze()
        self.output.mkdir()
        prior = self.output / 'npc-factions.json'
        prior.write_bytes(b'previous successful JSON')
        original = REFRESH.build

        def changed(*args):
            result = original(*args)
            self.vendor_path.write_bytes(self.vendor + b'5,9004,a,10\r\n')
            return result

        with mock.patch.object(REFRESH, 'build', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'file changed during update'):
                REFRESH.run(self.args())
        self.assertEqual(prior.read_bytes(), b'previous successful JSON')
        self.assertFalse((self.output / 'audit.json').exists())

    def test_failed_input_install_keeps_output_and_manifest_as_one_transaction(self):
        self.freeze()
        self.output.mkdir()
        prior = self.output / 'npc-factions.json'
        prior.write_bytes(b'previous successful JSON')
        inputs = self.stage / 'inputs'
        canonical = inputs / 'vendors/faction-sources'
        (canonical / 'vendors.csv').mkdir(parents=True)
        manifest_path = inputs / 'manifest.json'
        manifest_content = REFRESH.encoded({'schemaVersion': 1, 'files': {}})
        manifest_path.write_bytes(manifest_content)
        args = self.args()
        args.install_input = True
        with mock.patch.object(REFRESH, 'INPUTS', inputs), \
                mock.patch.object(REFRESH, 'DEFAULT_BUNDLE', canonical), \
                mock.patch.object(REFRESH, 'DEFAULT_INPUT', inputs / 'vendors/npc-factions.json'):
            with self.assertRaisesRegex(ValueError, 'not a file'):
                REFRESH.run(args)
        self.assertEqual(prior.read_bytes(), b'previous successful JSON')
        self.assertEqual(manifest_path.read_bytes(), manifest_content)
        self.assertFalse((self.output / 'audit.json').exists())

    def test_manifest_duplicate_keys_and_noncanonical_paths_are_rejected(self):
        self.bundle.mkdir()
        (self.bundle / 'manifest.json').write_bytes(
            b'{"schemaVersion":1,"schemaVersion":1,"files":{}}')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            REFRESH.frozen(self.bundle)
        for relative in ('../outside', './vendors.csv', 'nether/../vendors.csv',
                         'nether//9001.json', '/vendors.csv', 'C:/vendors.csv'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                REFRESH.bundle_path(self.bundle, relative)

    def test_partial_client_bundle_cannot_supply_unmanifested_bindings(self):
        files = dict(self.files)
        del files['client/factions.csv']
        manifest, content = self.freeze(files)
        with self.assertRaisesRegex(ValueError, 'must manifest factions.csv'):
            REFRESH.build(manifest, content, files, self.vendor)

    def test_pipeline_forwards_explicit_affiliation_input(self):
        value = self.stage / 'npc-factions.json'
        args = PIPELINE.parser().parse_args(['--vendor-factions-json', str(value)])
        self.assertEqual(PIPELINE.item_options(args).vendor_factions_json, value)

    def test_pipeline_rejects_tampered_source_bundle(self):
        self.freeze()
        REFRESH.run(self.args())
        (self.output / 'faction-sources/nether/9001.json').write_bytes(b'tampered')
        args = SimpleNamespace(items_lua=self.stage / 'Data_ProfItems.lua',
                               vendors_lua=ROOT / 'Core/Data/Data_ProfVendors.lua',
                               output_csv=self.stage / 'items.csv', vendor_factions_json=self.output / 'npc-factions.json')
        with self.assertRaisesRegex(ValueError, 'evidence hash mismatch'):
            ITEMS.build_batch(args)

    def test_bundled_all_vendor_snapshot_rebuilds_the_canonical_json(self):
        directory = REFRESH.DEFAULT_BUNDLE
        if not directory.is_dir():
            self.fail('the reproducible source snapshot must ship with the repository')
        manifest, content, files = REFRESH.frozen(directory)
        vendor = REFRESH.DEFAULT_VENDORS.read_bytes()
        data, audit = REFRESH.build(manifest, content, files, vendor)
        self.assertEqual(REFRESH.encoded(data), REFRESH.DEFAULT_INPUT.read_bytes())
        self.assertEqual(audit['targets'], len(REFRESH.targets(vendor)))
        self.assertEqual(set(audit['npcs']), {str(n) for n in REFRESH.targets(vendor)})
        self.assertFalse(audit['conflicts'])
        self.assertGreater(audit['resolved'], 2)


if __name__ == '__main__':
    unittest.main()
