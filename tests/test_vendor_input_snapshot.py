"""Versioned sold-by repairs preserve the original imported CSV evidence."""
import csv
import hashlib
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
INPUTS = TOOLS / '_fc/inputs'
SNAPSHOT = INPUTS / 'vendors/vendors-soldby-json-20261021.csv'
ORIGINALS = {
    'client/item-buy-prices.csv': 'b489082f3bab36c4dc0c87dc24b5eaf78097ce29802d38df829d24e8fa8062dd',
    'client/item.csv': 'e3d96deb190e6d7807f690ae71c6f67ab0ea35044cec402a0cb5ccb990e1868a',
    'client/recipe-item-specializations.csv': '54bc36be2d32511c9111d8e1e6307fff333ad5b115debcf53c8c2f87f1cdec77',
    'vendors/vendors.csv': '704c1a8121cd54cf732d06539e646850720ffea37a70fdbcbc967c58ade53802',
    'vendors/npcs.csv': 'fe2cfba8f09f881c96e80212c3249f19e9d9ea570a5383b018b1e18ffc107e6b',
}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


class VendorInputSnapshotTests(unittest.TestCase):
    def load_paths(self):
        sys.path.insert(0, str(TOOLS))
        self.addCleanup(lambda: sys.path.remove(str(TOOLS)))
        import fc_pipeline_paths
        return fc_pipeline_paths.CSV_INPUTS

    def test_five_active_roles_use_the_manifested_repaired_vendor_snapshot(self):
        paths = self.load_paths()
        self.assertEqual(set(paths), {
            'prices_csv', 'item_csv', 'recipe_items_csv', 'vendors_csv', 'npcs_csv',
        })
        self.assertEqual(paths['vendors_csv'], SNAPSHOT)
        manifest = json.loads((INPUTS / 'manifest.json').read_bytes())
        relative = SNAPSHOT.relative_to(INPUTS).as_posix()
        entry = manifest['files'][relative]
        content = SNAPSHOT.read_bytes()
        self.assertEqual(entry['sha256'], digest(content))
        self.assertEqual(entry['bytes'], len(content))
        self.assertEqual(paths['npcs_csv'], INPUTS / 'vendors/npcs.csv')
        self.assertEqual(paths['prices_csv'], INPUTS / 'client/item-buy-prices.csv')
        self.assertEqual(paths['item_csv'], INPUTS / 'client/item.csv')
        self.assertEqual(paths['recipe_items_csv'], INPUTS / 'client/recipe-item-specializations.csv')

    def test_original_five_snapshots_keep_their_recorded_bytes_and_hashes(self):
        manifest = json.loads((INPUTS / 'manifest.json').read_bytes())
        for relative, expected in ORIGINALS.items():
            with self.subTest(path=relative):
                content = (INPUTS / relative).read_bytes()
                entry = manifest['files'][relative]
                self.assertEqual(entry['sha256'], expected)
                self.assertEqual(digest(content), expected)
                self.assertEqual(entry['bytes'], len(content))

    def test_repair_retains_pairs_and_restores_both_factions_currency_cost(self):
        original = read_rows(INPUTS / 'vendors/vendors.csv')
        rows = read_rows(SNAPSHOT)
        pairs = {(row['item_id'], row['npc_id']) for row in rows}
        self.assertEqual(len(pairs), len(rows), 'snapshot duplicated an item/NPC pair')
        self.assertTrue({(row['item_id'], row['npc_id']) for row in original} <= pairs)
        npcs = {row['npc_id']: row for row in read_rows(INPUTS / 'vendors/npcs.csv')}
        for item in ('251380', '251375'):
            selected = {row['npc_id']: row for row in rows if row['item_id'] == item}
            self.assertEqual(set(selected), {'248197', '256730'})
            for npc, side, zone in (('248197', 'h', '17'), ('256730', 'a', '44')):
                with self.subTest(item=item, npc=npc):
                    row = selected[npc]
                    self.assertEqual(row['currency_kind'], 'currency')
                    self.assertEqual(row['currency_id'], '3402')
                    self.assertEqual(row['currency_amount'], '30')
                    self.assertIn(row['cost_copper'], ('', '0'))
                    self.assertEqual(row['side'].lower(), side)
                    self.assertEqual(row['zone_id'], zone)
                    self.assertEqual(row['name_en'], npcs[npc]['name_en'])

    def test_narrow_generation_and_publication_preserve_original_inputs_and_vendor_lua(self):
        paths = self.load_paths()
        import fc_pipeline_common as common
        spec = importlib.util.spec_from_file_location('vendor_snapshot_items_test', TOOLS / 'fc_prof_items.py')
        items = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(items)
        vendor_lua = ROOT / 'Core/Data/Data_ProfVendors.lua'
        protected = [INPUTS / relative for relative in ORIGINALS] + [vendor_lua]
        before = {path: (digest(path.read_bytes()), path.stat().st_mtime_ns) for path in protected}
        temporary_root = ROOT / '.pipeline-runtime/tmp'
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='vendor-snapshot-', dir=temporary_root) as directory:
            stage = Path(directory).resolve()
            args = SimpleNamespace(
                from_csv=None, vendors_csv=paths['vendors_csv'], npcs_csv=paths['npcs_csv'],
                prices_csv=paths['prices_csv'], output_csv=stage / 'DataProfItems.csv',
                items_lua=stage / 'Data_ProfItems.lua', vendors_lua=vendor_lua, verified_at='',
            )
            outputs, expected = items.build_batch(args)
            self.assertEqual(outputs[vendor_lua], vendor_lua.read_bytes())
            self.assertEqual(set(outputs), {args.output_csv, args.items_lua, vendor_lua})
            self.assertFalse(args.output_csv.exists())
            self.assertFalse(args.items_lua.exists())
            selected = {path: content for path, content in outputs.items() if path != vendor_lua}
            with mock.patch.object(common, 'REPO', stage):
                common.publish_batch(selected, expected)
            self.assertEqual(args.output_csv.read_bytes(), selected[args.output_csv])
            self.assertEqual(args.items_lua.read_bytes(), selected[args.items_lua])
        self.assertEqual({path: (digest(path.read_bytes()), path.stat().st_mtime_ns) for path in protected}, before)


if __name__ == '__main__':
    unittest.main()
