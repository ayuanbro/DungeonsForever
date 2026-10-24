"""Offline sold-by parsing preserves hidden-tab prices and source boundaries."""
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vendor_collector", ROOT / "scripts/gen_vendors.py")
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)

# Compact frozen source data shared by the cached 251370/251375/251380 pages.
# The latter two pages rendered Dropped by first and left Sold by empty.
FROZEN_SELLERS = r'''[{"classification":0,"displayName":"Gor'mak","displayNames":[],"id":248197,"location":[17],"maxlevel":60,"minlevel":60,"name":"Gor'mak","names":[],"react":[null,0],"tag":"Blacksmith","type":7,"envChange":{"status":"new","labels":[],"lines":[]},"stock":-1,"cost":[[0,[[3402,30]],[]]],"popularity":331},{"classification":0,"displayName":"Stondry Darkhammer","displayNames":[],"id":256730,"location":[44],"maxlevel":60,"minlevel":60,"name":"Stondry Darkhammer","names":[],"react":[0,null],"tag":"Blacksmith","type":7,"envChange":{"status":"new","labels":[],"lines":[]},"stock":-1,"cost":[[0,[[3402,30]],[]]],"popularity":243}]'''


def source_html(rows, template="npc", listview="sold-by"):
    return "<script>new Listview({template: '%s', id: '%s', data: %s,});</script>" % (
        template, listview, json.dumps(rows))


def seller(**values):
    row = {"id": 7, "name": "Seller", "location": [12], "react": [1, 1], "stock": -1}
    row.update(values)
    return row


class SoldByParserTests(unittest.TestCase):
    def test_frozen_helm_leggings_and_shirt_have_both_token_sellers(self):
        for item, dropped in ((251380, 5), (251375, 15), (251370, 0)):
            with self.subTest(item=item):
                html = '''<script type="application/json">{"entityId":%d}</script>
                <button role="tab" data-href="#dropped-by">Dropped by (%d)</button>
                <button role="tab" data-href="#sold-by">Sold by (2)</button>
                <div id="tab-sold-by" data-template="npc" style="display:none;"></div>
                <script>new Listview({template:'npc',id:'dropped-by',data:[{"id":639}]});
                new Listview({template:'npc',id:'sold-by',extraCols:['stock','cost'],
                  data:%s,});</script>''' % (item, dropped, FROZEN_SELLERS)
                rows = COLLECTOR.parse_sold_by(html)
                self.assertEqual([r["npc"] for r in rows], [248197, 256730])
                self.assertEqual([r["side"] for r in rows], ["h", "a"])
                self.assertEqual([r["zone"] for r in rows], [17, 44])
                for row in rows:
                    self.assertIsNone(row["cost"])
                    self.assertEqual((row["currency_kind"], row["currency_id"], row["currency_amount"]),
                                     ("currency", 3402, 30))
                    self.assertEqual(row["stock"], -1)

    def test_rendered_html_fallback_stays_inside_sold_by_panel(self):
        html = '''<div id="tab-sold-by"><div><table><tr class="listview-row">
          <td>New</td><td><a href="/forever/npc=7/seller" data-wowhead="map">Seller</a></td>
          <td><a href="/forever/zone=12/elwynn">Elwynn</a></td><td><span class="q">A</span></td>
          <td>∞</td><td><a href="/forever/currency=3402/favor">30</a></td></tr></table></div></div>
          <div id="tab-dropped-by"><tr class="listview-row"><td>
          <a href="/forever/npc=999/unrelated" data-wowhead="map">Unrelated</a></td></tr></div>'''
        rows = COLLECTOR.parse_sold_by(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["npc"], rows[0]["zone"], rows[0]["side"]), (7, 12, "a"))
        self.assertEqual((rows[0]["currency_id"], rows[0]["currency_amount"], rows[0]["stock"]),
                         (3402, 30, -1))

    def test_unrelated_listviews_and_nested_keys_do_not_supply_sellers(self):
        self.assertEqual(COLLECTOR.parse_sold_by(source_html([seller()], listview="dropped-by")), [])
        self.assertEqual(COLLECTOR.parse_sold_by(source_html([seller()], template="item")), [])
        row = seller(name='A "quoted", ] } \\ vendor',
                     metadata={"id": "sold-by", "data": [1, {"x": "}, new Listview({"}]})
        html = source_html([row], listview="unrelated") + source_html([row])
        parsed = COLLECTOR.parse_sold_by(html)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["name"], row["name"])

    def test_rendered_gold_fragments_sum_only_the_cost_cell(self):
        cases = (('<span class="moneysilver">31</span><span class="moneycopper">57</span>', 3157),
                 ('<span class="moneygold">1</span>', 10000),
                 ('<span class="moneygold">1</span><span class="moneysilver">23</span>', 12300),
                 ('<span class="moneycopper">0</span>', 0), ('', None),
                 ('<span class="moneygold">1</span><span class="moneysilver">23</span>'
                  '<span class="moneycopper">45</span>', 12345))
        for cell, expected in cases:
            with self.subTest(cell=cell):
                html = '''<div id="tab-sold-by"><table><tr class="listview-row">
                <td>New</td><td><a href="/forever/npc=7/seller" data-wowhead="map">Seller</a></td>
                <td></td><td></td><td>∞</td><td>%s</td>
                <td><span class="moneygold">99</span><a href="/item=999/fake">999</a></td>
                </tr></table></div>''' % cell
                row = COLLECTOR.parse_sold_by(html)[0]
                self.assertEqual(row['cost'], expected)
                self.assertIsNone(row['currency_id'])

    def test_explicit_empty_source_is_authoritative_and_json_is_never_evaluated(self):
        self.assertEqual(COLLECTOR.parse_sold_by(source_html([])), [])
        for data in ('notJSON()', '[{"id":7,"cost":someCode()}]', '{}'):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'sold-by|Sold-by'):
                COLLECTOR.parse_sold_by(
                    "<script>new Listview({template:'npc',id:'sold-by',data:%s});</script>" % data)

    def test_comments_and_quoted_fake_listviews_are_ignored(self):
        fake = "new Listview({template:'npc',id:'sold-by',data:[{\"id\":999}]});"
        html = '<script>var note=%s;/*%s*/\n//%s\n</script>' % (json.dumps(fake), fake, fake)
        html += source_html([seller(cost=[[10]])])
        self.assertEqual([row['npc'] for row in COLLECTOR.parse_sold_by(html)], [7])

    def test_canonical_names_preserve_quotes_for_existing_localization_keys(self):
        names = ((217689, 'Ziri "The Wrench" Littlesprocket'),
                 (222261, 'Maximillian "The Greaser"'))
        for npc, name in names:
            encoded = name.replace('"', '&quot;')
            for raw_name in (name, encoded, '  ', None):
                with self.subTest(npc=npc, raw_name=raw_name):
                    row = seller(id=npc, name=raw_name, displayName=encoded)
                    self.assertEqual(COLLECTOR.parse_sold_by(source_html([row]))[0]['name'], name)

    def test_gold_item_currency_and_missing_cost_remain_distinct(self):
        cases = (([[3157]], (3157, None, None, None)),
                 ([[0]], (0, None, None, None)),
                 ([[0, [[3402, 30]], []]], (None, "currency", 3402, 30)),
                 ([[0, [], [[263439, 10]]]], (None, "item", 263439, 10)),
                 ([[125, [[3402, 3]], []]], (125, "currency", 3402, 3)),
                 (None, (None, None, None, None)), ([], (None, None, None, None)))
        for cost, expected in cases:
            with self.subTest(cost=cost):
                row = COLLECTOR.parse_sold_by(source_html([seller(cost=cost)]))[0]
                self.assertEqual(tuple(row[k] for k in ("cost", "currency_kind", "currency_id", "currency_amount")),
                                 expected)
        self.assertIsNone(COLLECTOR.parse_sold_by(source_html([seller()]))[0]["cost"])

    def test_unsupported_alternatives_and_multiple_requirements_are_reported(self):
        for cost in ([[10], [20]], [[0, [[1, 2], [3, 4]], []]],
                     [[0, [], [[1, 2], [3, 4]]]], [[0, [[1, 2]], [[3, 4]]]],
                     [[-1]], [[True]], [[0, [[0, 2]], []]], [[0, [[1, -2]], []]]):
            with self.subTest(cost=cost), self.assertRaisesRegex(ValueError, 'Unsupported sold-by cost for NPC 7'):
                COLLECTOR.parse_sold_by(source_html([seller(cost=cost)]))

    def test_reaction_sides_distinguish_both_factions_hostile_and_unknown(self):
        for react, side in (([1, 1], "n"), ([0, 0], "n"), ([1, -1], "a"),
                            ([-1, 1], "h"), ([None, 0], "h"), ([0, None], "a"),
                            ([-1, -1], None), (None, None)):
            with self.subTest(react=react):
                self.assertEqual(COLLECTOR.parse_sold_by(source_html([seller(react=react)]))[0]["side"], side)


if __name__ == "__main__":
    unittest.main()
