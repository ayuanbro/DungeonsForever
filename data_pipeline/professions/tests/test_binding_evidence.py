"""Binding evidence uses the item's tooltip, never missing text or comments."""
import json
from pathlib import Path
import unittest

from data_pipeline.professions.model import parse_page
from data_pipeline.professions.model import sha256
from data_pipeline.professions.build import normalize
from data_pipeline.professions.tests.test_source_pipeline import (
    fixture_tables, snapshot, temporary_directory,
)


class BindingEvidenceTests(unittest.TestCase):
    def test_real_forever_tooltips_fill_only_confirmed_binding(self):
        rows = json.loads((Path(__file__).parent / 'fixtures/formula_bindings_20261030.json').read_text(encoding='utf-8'))
        for row in rows:
            with self.subTest(item=row['item']):
                html = '<title>' + row['title'] + '</title><script>g_items[' + str(row['item']) + '].tooltip_enus = ' + json.dumps(row['tooltip']) + ';</script>'
                page = parse_page(html.encode(), 'item', row['item'], row['url'])
                self.assertEqual(page['bindingType'], 1)
                wrong_id = html.replace('g_items[' + str(row['item']) + ']', 'g_items[999]')
                self.assertNotIn('bindingType', parse_page(wrong_id.encode(), 'item', row['item'], row['url']))

    def test_absent_or_unsupported_binding_never_becomes_unbound(self):
        for tooltip in ('no binding label', '<!--bo--><br>Binds to account<!--ue-->', '<!--bo--><!--ue-->'):
            html = '<title>Book - Item - Forever</title><script>g_items[1].tooltip_enus = ' + json.dumps(tooltip) + ';</script><p>Comment: Binds when picked up</p>'
            self.assertNotIn('bindingType', parse_page(html.encode(), 'item', 1, 'https://www.wowhead.com/forever/item=1'))

    def test_raw_binding_enums_are_preserved_separately_from_auctionability(self):
        for binding in range(6):
            with self.subTest(binding=binding), temporary_directory() as folder:
                root = Path(folder)
                tables = fixture_tables();tables['ItemSparse'][0]['Bonding'] = str(binding)
                manifest = snapshot(root, tables=tables)
                result = normalize(root, manifest)
                facts = result[0]
                route = next(r for r in facts['alchemy'][1000]['routes'] if r['kind'] == 'item')
                a = route['acquisition']
                self.assertEqual(a['bindingType'], binding)
                self.assertEqual(a['bindingSource'], 'ItemSparse')
                self.assertEqual(a['bindOnPickup'], binding == 1)
                self.assertEqual(a['nonAuctionable'], binding in (1, 4, 5))

    def test_tooltip_fallback_flows_through_normalizer_without_replacing_db2(self):
        for db2_binding in (None, '0'):
            with self.subTest(db2_binding=db2_binding), temporary_directory() as folder:
                root = Path(folder);tables = fixture_tables()
                if db2_binding is None:
                    del tables['ItemSparse'][0]['Bonding']
                else:
                    tables['ItemSparse'][0]['Bonding'] = db2_binding
                manifest = snapshot(root, tables=tables)
                record = next(r for r in manifest['responses'] if r['key'] == 'web:item:2000')
                path = root / record['path']
                data = path.read_bytes() + b'<script>g_items[2000].tooltip_enus = "<!--bo--><br>Binds when picked up<!--ue-->";</script>'
                path.write_bytes(data);record['sha256'] = sha256(data)
                facts = normalize(root, manifest)[0]
                a = next(r for r in facts['alchemy'][1000]['routes'] if r['kind'] == 'item')['acquisition']
                self.assertEqual(a['bindingType'], 1 if db2_binding is None else 0)
                self.assertEqual(a['bindingSource'], 'wowhead:item-tooltip' if db2_binding is None else 'ItemSparse')


if __name__ == '__main__':
    unittest.main()
