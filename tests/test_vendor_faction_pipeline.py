"""Explicit NPC affiliations survive collection/import without inventing A/H/N."""
import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'df-data-pipeline/_temp'
sys.path.insert(0, str(TOOLS))
try:
    import fc_prof_items as ITEMS
finally:
    sys.path.remove(str(TOOLS))
SPEC = importlib.util.spec_from_file_location('vendor_faction_collector', ROOT / 'scripts/gen_vendors.py')
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


def evidence():
    return {'schemaVersion': 1, 'npcs': {'253139': {
        'factionID': 93, 'names': {'enUS': 'Magram Clan Centaur', 'zhCN': '玛格拉姆半人马'},
        'sources': [{'type': 'wowhead-npc-tooltip',
                     'url': 'https://nether.wowhead.com/forever/tooltip/npc/253139'}],
    }}}


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


def tooltip(name='Gorhak', faction='Magram Clan Centaur'):
    return ('<table><tr><td><b>%s</b></td></tr>'
            '<tr><td>Magram Clan Quartermaster</td></tr>'
            '<tr><td>Level 40 Humanoid (Normal)</td></tr>'
            '<tr><td>%s</td></tr></table>') % (name, faction)


class NpcFactionCollectorTests(unittest.TestCase):
    def test_affiliation_is_separate_from_npc_name_and_reaction(self):
        self.assertEqual(COLLECTOR.parse_npc_faction(tooltip()), {'name': 'Magram Clan Centaur'})
        self.assertEqual(COLLECTOR.parse_npc_faction(tooltip('Molkar', 'Gelkis Clan Centaur')),
                         {'name': 'Gelkis Clan Centaur'})
        # A title, the NPC name, and a creature type are not affiliations.
        pexmit = ('<table><tr><td><b>Pexmit</b></td></tr><tr><td>Someone\'s Minion</td></tr>'
                  '<tr><td>Demon (Rare)</td></tr></table>')
        self.assertIsNone(COLLECTOR.parse_npc_faction(pexmit))
        self.assertIsNone(COLLECTOR.parse_npc_faction(
            '<table><tr><td>Magram Clan Centaur</td></tr></table>'))

    def test_explicit_faction_link_preserves_id_and_decodes_name(self):
        html = '<table><tr><td><a href="/forever/faction=93">Clan &amp; Friends</a></td></tr></table>'
        self.assertEqual(COLLECTOR.parse_npc_faction(html),
                         {'name': 'Clan & Friends', 'factionID': 93})

    def test_nether_cached_tooltip_keeps_affiliation_without_request_or_side(self):
        with tempfile.TemporaryDirectory(prefix='npc-tooltip-mock-') as directory, \
                mock.patch.object(COLLECTOR, 'load_cached', return_value=json.dumps({
                'name': 'Gorhak', 'tooltip': tooltip(),
                'map': {'zone': 405, 'coords': {'0': [[66.2, 79.4]]}}})), \
                mock.patch.object(COLLECTOR, 'http_json', side_effect=AssertionError('offline')):
            info = COLLECTOR.NpcNether(cache_dir=directory)._info(253139)
        self.assertEqual(info['name'], 'Gorhak')
        self.assertEqual(info['coords'], [(405, 66.2, 79.4)])
        self.assertEqual(info['faction']['names'], {'enUS': 'Magram Clan Centaur'})
        self.assertNotIn('side', info)
        record = COLLECTOR.build_npc_factions({253139: info})['npcs']['253139']
        self.assertNotIn('factionID', record)
        self.assertEqual(len(record['sources'][0]['sha256']), 64)

    def test_exact_client_names_supply_id_and_languages_without_fuzzy_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Faction.csv'
            path.write_text('ID,Name_enUS,Name_zhCN,Name_zhTW\n'
                            '93,Magram Clan Centaur,玛格拉姆半人马,瑪格拉姆半人馬\n', encoding='utf-8-sig')
            names, source = COLLECTOR.load_faction_names(str(path))
        info = {253139: {'name': 'Gorhak', 'faction': {
            'names': {'enUS': 'Magram Clan Centaur'},
            'sources': evidence()['npcs']['253139']['sources']}}}
        result = COLLECTOR.build_npc_factions(info, names, source)
        row = result['npcs']['253139']
        self.assertEqual(row['factionID'], 93)
        self.assertEqual(row['names']['zhTW'], '瑪格拉姆半人馬')
        self.assertEqual(row['sources'][-1]['type'], 'client-faction-csv')
        info[253139]['faction']['names']['enUS'] = 'magram clan centaur'
        fallback = COLLECTOR.build_npc_factions(info, names, source)['npcs']['253139']
        self.assertNotIn('factionID', fallback)
        self.assertEqual(fallback['names'], {'enUS': 'magram clan centaur'})

    def test_missing_evidence_or_translation_never_creates_affiliation(self):
        info = {1: {'name': 'Magram Clan Centaur'},
                2: {'faction': {'names': {'enUS': 'Magram Clan Centaur'}}},
                3: {'faction': {'names': {'zhCN': '玛格拉姆半人马'},
                                'sources': evidence()['npcs']['253139']['sources']}}}
        self.assertEqual(COLLECTOR.build_npc_factions(info)['npcs'], {})

    def test_duplicate_client_names_do_not_imply_an_arbitrary_faction_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Faction.csv'
            path.write_text('ID,Name_enUS\n1,Same Name\n2,Same Name\n93,Magram Clan Centaur\n',
                            encoding='utf-8')
            names, _ = COLLECTOR.load_faction_names(str(path))
        self.assertNotIn('Same Name', names)
        self.assertEqual(names['Magram Clan Centaur']['factionID'], 93)


class NpcFactionImportTests(unittest.TestCase):
    def test_metadata_validation_and_optional_faction_id(self):
        record = ITEMS.vendor_factions(encoded(evidence()))[253139]
        self.assertEqual(record['factionID'], 93)
        data = evidence()
        del data['npcs']['253139']['factionID']
        record = ITEMS.vendor_factions(encoded(data))[253139]
        self.assertEqual(record['names']['enUS'], 'Magram Clan Centaur')
        self.assertNotIn('factionID', record)

    def test_bad_evidence_and_access_side_injection_are_rejected(self):
        for field, value in (('factionID', 0), ('factionID', True), ('factionID', '93'),
                             ('sources', []), ('sources', [{}]), ('names', {}),
                             ('names', {'enUS': ''}), ('names', {'xxXX': 'Test'}),
                             ('side', 'N')):
            with self.subTest(field=field, value=value):
                data = evidence()
                data['npcs']['253139'][field] = value
                with self.assertRaises(ITEMS.DataError):
                    ITEMS.vendor_factions(encoded(data))
        with self.assertRaises(ITEMS.DataError):
            ITEMS.vendor_factions(b'{"schemaVersion":1,"schemaVersion":1,"npcs":{}}')

    def fixture(self, stage):
        def write(path, fields, rows):
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        args = SimpleNamespace(
            from_csv=None, vendors_csv=stage / 'vendors.csv', npcs_csv=stage / 'npcs.csv',
            prices_csv=stage / 'prices.csv', output_csv=stage / 'DataProfItems.csv',
            items_lua=stage / 'Data_ProfItems.lua', vendors_lua=stage / 'Data_ProfVendors.lua',
            vendor_factions_json=stage / 'npc-factions.json', verified_at='')
        vendor = dict.fromkeys(ITEMS.VENDOR_FIELDS, '')
        vendor.update(item_id='9', npc_id='253139', name_en='Gorhak', zone_id='405',
                      currency_kind='currency', currency_id='3402', currency_amount='30', stock='-1')
        price = dict.fromkeys(ITEMS.PRICE_FIELDS, '')
        price.update(ItemID='9', Name_enUS='Recipe', VendorStackCount='1', BuyPriceCopper='5',
                     PriceStatus='priced', Build='70450')
        write(args.vendors_csv, ITEMS.VENDOR_FIELDS, [vendor])
        write(args.npcs_csv, ITEMS.NPC_FIELDS, [])
        write(args.prices_csv, ITEMS.PRICE_FIELDS, [price])
        vendor_lua, _ = ITEMS.update_vendors('local _, ns = ...\nns.ProfVendors = {}\n', [])
        args.vendors_lua.write_bytes(vendor_lua.encode('utf-8'))
        args.vendor_factions_json.write_bytes(encoded(evidence()))
        return args

    def test_normal_and_from_csv_keep_19_columns_prices_and_separate_faction_table(self):
        temporary = ROOT / '.pipeline-runtime/tmp'
        temporary.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='vendor-factions-', dir=temporary) as directory:
            args = self.fixture(Path(directory))
            originals = {path: path.read_bytes() for path in Path(directory).iterdir()}
            outputs, expected = ITEMS.build_batch(args)
            rows = ITEMS.items_csv_rows(outputs[args.output_csv])
            self.assertEqual(len(ITEMS.CSV_FIELDS), 19)
            self.assertEqual(rows[0]['side'], '')
            self.assertEqual(rows[0]['currency_amount'], '30')
            self.assertEqual(rows[1]['cost_copper'], '5')
            self.assertEqual(outputs[args.vendors_lua], originals[args.vendors_lua])
            text = outputs[args.items_lua].decode('utf-8')
            self.assertIn('ns.ProfVendorFactions = {', text)
            self.assertIn('[253139] = {', text)
            self.assertIn('factionID=93', text)
            self.assertIn('vendorFactions={file="npc-factions.json",sha256=', text)
            self.assertIn(args.vendor_factions_json, expected)
            self.assertEqual({path: path.read_bytes() for path in originals}, originals)
            args.output_csv.write_bytes(outputs[args.output_csv])
            args.from_csv = args.output_csv
            rebuilt, _ = ITEMS.build_batch(args)
            self.assertEqual(set(rebuilt), {args.items_lua})
            self.assertEqual(rebuilt[args.items_lua].decode('utf-8').split('ns.ProfVendorFactions')[1],
                             text.split('ns.ProfVendorFactions')[1])

    def test_missing_default_is_optional_but_explicit_missing_input_fails(self):
        temporary = ROOT / '.pipeline-runtime/tmp'
        temporary.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='vendor-factions-', dir=temporary) as directory:
            args = self.fixture(Path(directory))
            args.vendor_factions_json = None
            missing = Path(directory) / 'missing.json'
            with mock.patch.object(ITEMS, 'DEFAULT_VENDOR_FACTIONS', missing):
                outputs, _ = ITEMS.build_batch(args)
                self.assertIn(b'ns.ProfVendorFactions = {\n}', outputs[args.items_lua])
            args.vendor_factions_json = missing
            with self.assertRaises(OSError):
                ITEMS.build_batch(args)


class VendorFactionSourceBundleTests(unittest.TestCase):
    fixture = NpcFactionImportTests.fixture

    def setUp(self):
        temporary = ROOT / '.pipeline-runtime/tmp'
        temporary.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='faction-bundle-', dir=temporary)
        self.addCleanup(self.directory.cleanup)
        self.args = self.fixture(Path(self.directory.name))
        self.bundle = Path(self.directory.name) / 'faction-sources'
        self.source = self.bundle / 'nether/253139.json'
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'{"name":"Example Merchant","tooltip":"frozen affiliation evidence"}')
        self.manifest = {'schemaVersion': 1, 'files': {'nether/253139.json': {
            'sha256': ITEMS.sha(self.source.read_bytes()), 'bytes': self.source.stat().st_size}}}
        self.data = evidence()
        self.data['npcs']['253139']['sources'][0].update(
            file='faction-sources/nether/253139.json', sha256=ITEMS.sha(self.source.read_bytes()))
        self.rewrite()

    def rewrite(self, data=None, manifest=None, manifest_content=None):
        data = json.loads(encoded(self.data if data is None else data))
        content = manifest_content if manifest_content is not None else encoded(
            self.manifest if manifest is None else manifest)
        (self.bundle / 'manifest.json').write_bytes(content)
        data['sourceBundle'] = {'directory': 'faction-sources', 'manifestSHA256': ITEMS.sha(content)}
        self.args.vendor_factions_json.write_bytes(encoded(data))

    def test_normal_and_from_csv_verify_and_watch_each_frozen_file(self):
        outputs, expected = ITEMS.build_batch(self.args)
        self.assertIn(self.source, expected)
        self.assertIn(self.bundle / 'manifest.json', expected)
        self.assertIn(b'factionID=93', outputs[self.args.items_lua])
        self.args.output_csv.write_bytes(outputs[self.args.output_csv])
        self.args.from_csv = self.args.output_csv
        rebuilt, observed = ITEMS.build_batch(self.args)
        self.assertIn(self.source, observed)
        self.assertEqual(rebuilt[self.args.items_lua].split(b'ns.ProfVendorFactions')[1],
                         outputs[self.args.items_lua].split(b'ns.ProfVendorFactions')[1])

    def test_every_npc_source_must_bind_a_manifested_file_and_exact_hash(self):
        for field, value in (('file', 'faction-sources/nether/not-listed.json'),
                             ('file', None), ('sha256', None), ('sha256', '0' * 64),
                             ('sha256', False)):
            with self.subTest(field=field, value=value):
                data = json.loads(encoded(self.data))
                source = data['npcs']['253139']['sources'][0]
                if value is None:
                    del source[field]
                else:
                    source[field] = value
                self.rewrite(data=data)
                with self.assertRaises(ITEMS.DataError):
                    ITEMS.build_batch(self.args)
        self.rewrite(manifest={'schemaVersion': 1, 'files': {}})
        with self.assertRaisesRegex(ITEMS.DataError, 'absent from'):
            ITEMS.build_batch(self.args)

    def test_source_paths_cannot_escape_or_use_absolute_or_noncanonical_forms(self):
        for name in ('../outside.json', '/absolute.json', 'C:/absolute.json',
                     '\\\\host\\share\\file.json', 'faction-sources/nether/../file.json',
                     'faction-sources/nether//file.json', 'faction-sources/nether/./file.json',
                     'other-directory/nether/253139.json'):
            with self.subTest(name=name):
                data = json.loads(encoded(self.data))
                data['npcs']['253139']['sources'][0]['file'] = name
                self.rewrite(data=data)
                with self.assertRaises(ITEMS.DataError):
                    ITEMS.build_batch(self.args)

    def test_manifest_paths_cannot_escape_or_self_reference(self):
        for name in ('../outside.json', '/absolute.json', 'C:/absolute.json',
                     'nether\\file.json', 'nether//file.json', 'nether/./file.json', 'manifest.json'):
            with self.subTest(name=name):
                manifest = {'schemaVersion': 1, 'files': {name: self.manifest['files']['nether/253139.json']}}
                self.rewrite(manifest=manifest)
                with self.assertRaises(ITEMS.DataError):
                    ITEMS.build_batch(self.args)

    def test_manifest_types_hashes_and_sizes_are_strict(self):
        for field, value in (('bytes', True), ('bytes', -1), ('bytes', 1.0),
                             ('bytes', '1'), ('sha256', True), ('sha256', 'z' * 64),
                             ('sha256', 'short')):
            with self.subTest(field=field, value=value):
                manifest = json.loads(encoded(self.manifest))
                manifest['files']['nether/253139.json'][field] = value
                self.rewrite(manifest=manifest)
                with self.assertRaises(ITEMS.DataError):
                    ITEMS.build_batch(self.args)
        for manifest in ([], {'schemaVersion': True, 'files': {}},
                         {'schemaVersion': 1, 'files': []},
                         {'schemaVersion': 1, 'files': {'nether/253139.json': []}}):
            with self.subTest(manifest=manifest):
                self.rewrite(manifest=manifest)
                with self.assertRaises(ITEMS.DataError):
                    ITEMS.build_batch(self.args)
        self.rewrite(manifest_content=b'{"schemaVersion":1,"files":{},"files":{}}')
        with self.assertRaisesRegex(ITEMS.DataError, 'duplicate'):
            ITEMS.build_batch(self.args)

    def test_corrupt_evidence_or_manifest_never_builds_a_publishable_result(self):
        outputs, _ = ITEMS.build_batch(self.args)
        self.args.output_csv.write_bytes(outputs[self.args.output_csv])
        self.source.write_bytes(self.source.read_bytes() + b'changed')
        for from_csv in (None, self.args.output_csv):
            with self.subTest(from_csv=from_csv):
                self.args.from_csv = from_csv
                with self.assertRaisesRegex(ITEMS.DataError, 'evidence hash mismatch'):
                    ITEMS.build_batch(self.args)
        self.rewrite()
        (self.bundle / 'manifest.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ITEMS.DataError, 'manifest hash mismatch'):
            ITEMS.build_batch(self.args)
        self.assertFalse(self.args.items_lua.exists())

    def test_unified_entry_passes_custom_affiliation_path_to_the_items_step(self):
        sys.path.insert(0, str(TOOLS))
        self.addCleanup(lambda: sys.path.remove(str(TOOLS)))
        import fc_pipeline
        options = fc_pipeline.parser().parse_args([
            '--from-csv', str(self.args.output_csv),
            '--vendor-factions-json', str(self.args.vendor_factions_json)])
        forwarded = fc_pipeline.item_options(options)
        self.assertEqual(forwarded.vendor_factions_json, self.args.vendor_factions_json)


if __name__ == '__main__':
    unittest.main()
