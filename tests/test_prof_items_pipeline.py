"""Exercise the CSV-to-Lua profession importer through its public CLI only."""

import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "df-data-pipeline/_temp/fc_prof_items.py"
VENDOR_FIELDS = [
    "item_id", "npc_id", "zone_id", "side", "name_en", "name_locale",
    "cost_copper", "cost_text", "currency_kind", "currency_id",
    "currency_amount", "stock",
]
NPC_FIELDS = ["npc_id", "name_en", "name_locale", "zone_id", "ui_map_id", "x", "y"]
PRICE_FIELDS = [
    "ItemID", "Name_enUS", "Name_zhTW", "Name_zhCN", "BuyPriceCopper",
    "VendorStackCount", "PriceStatus", "Build", "HotfixBuild",
]
COST_FIELDS = ["cost_copper", "cost_text", "currency_kind", "currency_id", "currency_amount"]
OUTPUT_FIELDS = [
    "item_id", "npc_id", "name_en", "zone_id", "side", "cost_copper",
    "cost_text", "currency_kind", "currency_id", "currency_amount", "stock",
    "Name_enUS", "Name_zhTW", "Name_zhCN", "VendorStackCount", "PriceStatus",
    "Build", "HotfixBuild", "price_source",
]
ITEM_FIELDS = [
    "item_id", "Name_enUS", "Name_zhTW", "Name_zhCN", "VendorStackCount",
    "PriceStatus", "Build", "HotfixBuild", "offers",
]
OFFER_FIELDS = [
    "npc_id", "name_en", "zone_id", "side", "cost_copper", "cost_text",
    "currency_kind", "currency_id", "currency_amount", "stock", "price_source",
]
NPC_LOCS = """-- Preserve this unrelated table and its formatting verbatim.
ns.ProfNPCLocs = {
    [909] = { { 9, 99, 4.5, 6.7 } }, -- legacy point
}
"""
VENDORS_LUA = """local _, ns = ...

ns.ProfVendors = {
    [10] = { 1, 100, 11, 22 },
    [20] = { 2, 200, 33, 44 },
    [999] = { 9, 900, 55, 66 },
}

""" + NPC_LOCS

sys.path.insert(0, str(Path.home() / "AppData/Local/Temp/df-lua-runtime"))
sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None


def vendor(item=100, npc=10, **values):
    row = dict.fromkeys(VENDOR_FIELDS, "")
    row.update(item_id=str(item), npc_id=str(npc), zone_id="1", side="a",
               name_en="NPC English", name_locale="商人名称", stock="-1")
    row.update(values)
    return row


def price(item=100, **values):
    row = dict.fromkeys(PRICE_FIELDS, "")
    row.update(ItemID=str(item), Name_enUS="Recipe English", Name_zhTW="圖紙名稱",
               Name_zhCN="图纸名称", BuyPriceCopper="12345", VendorStackCount="5",
               PriceStatus="priced", Build="1.60.1.70450", HotfixBuild="70450")
    row.update(values)
    return row


def npc(npc_id=10, **values):
    row = dict.fromkeys(NPC_FIELDS, "")
    row.update(npc_id=str(npc_id), name_en="Updated NPC", name_locale="更新商人",
               zone_id="12", ui_map_id="1429", x="41.8", y="67.0")
    row.update(values)
    return row


def merged_row(item=100, npc_id=10, **values):
    row = dict.fromkeys(OUTPUT_FIELDS, "")
    row.update(item_id=str(item), npc_id=str(npc_id), name_en="NPC English", zone_id="1",
               side="a", cost_copper="12345", cost_text="1g23s45c", stock="-1",
               Name_enUS="Recipe English", Name_zhTW="圖紙名稱", Name_zhCN="图纸名称",
               VendorStackCount="5", PriceStatus="priced", Build="1.60.1.70450",
               HotfixBuild="70450", price_source="client")
    row.update(values)
    return row


class ProfItemsPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="df-prof-items-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        scripts = self.directory / 'df-data-pipeline/_temp'
        scripts.mkdir(parents=True)
        for name in ('fc_prof_items.py', 'fc_pipeline_common.py', 'fc_pipeline_paths.py'):
            shutil.copyfile(SCRIPT.parent / name, scripts / name)
        self.script = scripts / 'fc_prof_items.py'
        self.vendors = self.directory / "vendors.csv"
        self.npcs = self.directory / "npcs.csv"
        self.prices = self.directory / "prices.csv"
        self.output = self.directory / "data/DataProfItems.csv"
        self.items_lua = self.directory / "Data_ProfItems.lua"
        self.vendors_lua = self.directory / "Data_ProfVendors.lua"
        self.vendors_lua.write_text(VENDORS_LUA, encoding="utf-8")
        self.inputs()

    def write_csv(self, path, fields, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def inputs(self, vendors=None, npcs=None, prices=None, extra_vendor_fields=()):
        self.write_csv(self.vendors, VENDOR_FIELDS + list(extra_vendor_fields),
                       [vendor()] if vendors is None else vendors)
        self.write_csv(self.npcs, NPC_FIELDS, [npc()] if npcs is None else npcs)
        self.write_csv(self.prices, PRICE_FIELDS, [price()] if prices is None else prices)

    def run_cli(self, *extra, success=True):
        result = subprocess.run(
            [sys.executable, "-B", str(self.script), "--vendors-csv", str(self.vendors),
             "--npcs-csv", str(self.npcs), "--prices-csv", str(self.prices),
             "--output-csv", str(self.output), "--items-lua", str(self.items_lua),
             "--vendors-lua", str(self.vendors_lua), *extra],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        return result

    def rows(self):
        with self.output.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def stats(self, result):
        line = next(line for line in result.stdout.splitlines() if line.startswith("[OK] "))
        return json.loads(line[len("[OK] "):])

    def run_from_csv(self, *extra, success=True):
        return self.run_cli("--from-csv", str(self.output), *extra, success=success)

    def merged_input(self, rows, fields=None):
        self.output.parent.mkdir(exist_ok=True)
        self.write_csv(self.output, OUTPUT_FIELDS if fields is None else fields, rows)

    def load_lua(self, path):
        if LuaRuntime is None:
            self.skipTest("lupa.lua51 is required for generated Lua assertions")
        lua = LuaRuntime(unpack_returned_tuples=True)
        namespace = lua.table()
        lua.execute(path.read_text(encoding="utf-8-sig"), "Fixture", namespace)
        return namespace

    def old_outputs(self):
        self.output.parent.mkdir(exist_ok=True)
        self.output.write_bytes(b"previous csv\n")
        self.items_lua.write_bytes(b"previous items\n")
        return {path: path.read_bytes() for path in
                (self.output, self.items_lua, self.vendors_lua)}

    def assert_outputs_unchanged(self, expected):
        for path, content in expected.items():
            self.assertEqual(path.read_bytes(), content, str(path))

    def test_prepare_uses_staged_price_and_vendor_inputs_without_publishing(self):
        sys.path.insert(0, str(SCRIPT.parent))
        self.addCleanup(lambda: sys.path.remove(str(SCRIPT.parent)))
        import fc_pipeline_common as common
        spec = importlib.util.spec_from_file_location('df_items_prepared_test', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old_price = self.prices.read_bytes()
        self.inputs(prices=[price(BuyPriceCopper='23456')])
        new_price = self.prices.read_bytes()
        self.prices.write_bytes(old_price)
        original_vendor = self.vendors_lua.read_bytes()
        faction_input = self.directory / 'npc-factions.json'
        faction_input.write_text('{"schemaVersion":1,"npcs":{}}', encoding='utf-8')
        args = SimpleNamespace(
            vendors_csv=self.vendors, npcs_csv=self.npcs, prices_csv=self.prices,
            output_csv=self.output, items_lua=self.items_lua, vendors_lua=self.vendors_lua,
            from_csv=None, verified_at='', vendor_factions_json=faction_input, input_overrides={
                self.prices: new_price, self.vendors_lua: original_vendor + b'ns.Preserved = 123\n',
            },
        )
        with mock.patch.object(common, 'REPO', self.directory):
            outputs, expected = module.build_batch(args)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.items_lua.exists())
        self.assertEqual(self.prices.read_bytes(), old_price)
        self.assertEqual(self.vendors_lua.read_bytes(), original_vendor)
        rows = module.items_csv_rows(outputs[self.output])
        self.assertEqual(rows[0]['cost_copper'], '23456')
        self.assertIn(b'ns.Preserved = 123', outputs[self.vendors_lua])
        self.assertEqual(expected[self.prices], module.sha(old_price))
        self.assertEqual(expected[faction_input], module.sha(faction_input.read_bytes()))
        self.assertFalse((self.directory / '.implementation-backup').exists())

    def test_repeated_identical_generation_retains_bytes_and_mtimes(self):
        self.run_cli()
        paths = (self.output, self.items_lua, self.vendors_lua)
        original = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        self.run_cli()
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}, original)

    def test_repeated_generation_preserves_existing_lf_and_crlf_vendor_bytes(self):
        self.run_cli()
        canonical = self.vendors_lua.read_bytes().replace(b'\r\n', b'\n')
        for newline in (b'\n', b'\r\n'):
            with self.subTest(newline=newline):
                expected = canonical.replace(b'\n', newline)
                self.vendors_lua.write_bytes(expected)
                mtime = self.vendors_lua.stat().st_mtime_ns
                self.run_cli()
                self.assertEqual(self.vendors_lua.read_bytes(), expected)
                self.assertEqual(self.vendors_lua.stat().st_mtime_ns, mtime)

    def test_vendor_location_update_and_appended_details_keep_source_line_endings(self):
        for newline in (b'\n', b'\r\n'):
            with self.subTest(newline=newline):
                self.vendors_lua.write_bytes(VENDORS_LUA.encode('utf-8').replace(b'\n', newline))
                self.run_cli()
                updated = self.vendors_lua.read_bytes()
                self.assertIn(NPC_LOCS.encode('utf-8').replace(b'\n', newline), updated)
                if newline == b'\r\n':
                    self.assertNotIn(b'\n', updated.replace(b'\r\n', b''))
                else:
                    self.assertNotIn(b'\r', updated)
                namespace = self.load_lua(self.vendors_lua)
                self.assertEqual([namespace.ProfVendors[10][index] for index in range(1, 5)],
                                 [12, 1429, 41.8, 67])
                self.assertEqual(namespace.ProfVendorDetails[10].name_en, 'Updated NPC')

    def test_source_replacement_between_observation_and_freeze_is_rejected(self):
        sys.path.insert(0, str(SCRIPT.parent))
        self.addCleanup(lambda: sys.path.remove(str(SCRIPT.parent)))
        spec = importlib.util.spec_from_file_location('df_items_freeze_test', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(module, 'fingerprint', return_value=module.sha(b'previous snapshot')):
            with self.assertRaises(module.DataError):
                module._snapshot(self.prices, {}, {})

    def test_cli_refuses_output_outside_its_repository(self):
        outside = self.directory.parent / (self.directory.name + '-outside.csv')
        self.run_cli('--output-csv', str(outside), success=False)
        self.assertFalse(outside.exists())
        self.assertFalse(self.items_lua.exists())

    def test_join_keeps_npc_name_separate_from_item_names_and_whole_pack_price(self):
        self.run_cli()
        rows = self.rows()
        self.assertEqual(len(rows), 2, 'NPC quotation plus independent client base quote')
        row = rows[0]
        self.assertEqual(list(row), OUTPUT_FIELDS)
        self.assertEqual(row["name_en"], "NPC English")
        self.assertEqual(row["Name_enUS"], "Recipe English")
        self.assertEqual(row["Name_zhTW"], "圖紙名稱")
        self.assertEqual(row["Name_zhCN"], "图纸名称")
        self.assertEqual(row["cost_copper"], "12345")
        self.assertEqual("".join(row["cost_text"].split()), "1g23s45c")
        self.assertEqual(row["VendorStackCount"], "5")
        self.assertEqual(row["price_source"], "client")
        ns = self.load_lua(self.items_lua)
        item = ns.ProfItems[100]
        self.assertEqual(set(item.keys()), set(ITEM_FIELDS) | {'cost_copper', 'cost_text', 'price_source'})
        self.assertEqual(item.item_id, 100)
        self.assertEqual(item.Name_enUS, "Recipe English")
        self.assertEqual(item.Name_zhCN, "图纸名称")
        self.assertEqual(item.VendorStackCount, 5)
        self.assertEqual(item.PriceStatus, "priced")
        self.assertEqual(item.Build, "1.60.1.70450")
        self.assertEqual(item.HotfixBuild, "70450")
        offer = item.offers[10]
        self.assertTrue(set(offer.keys()).issubset(OFFER_FIELDS))
        self.assertEqual(offer.npc_id, 10)
        self.assertEqual(offer.name_en, "NPC English")
        self.assertEqual(offer.zone_id, 1)
        self.assertEqual(offer.cost_copper, 12345, "the group price must not be divided or multiplied")
        self.assertEqual(offer.cost_text, "1g23s45c")
        self.assertEqual(offer.stock, -1)
        self.assertEqual(offer.side, "a")
        self.assertEqual(offer.price_source, "client")
        self.assertIsNone(item.basePriceCopper)
        self.assertIsNone(offer.costKind)
        self.assertIsNone(offer.verifiedAt)
        self.assertIsNotNone(ns.ProfItemsMeta)
        self.assertEqual(ns.ProfItemsMeta.schemaVersion, 2)

    def test_each_nonempty_cost_column_including_zero_prevents_fallback(self):
        fixtures = []
        for index, (field, value) in enumerate(zip(COST_FIELDS, ("0", "0", "item", "77", "0"))):
            fixtures.append(vendor(100 + index, **{field: value}))
        fixtures.append(vendor(105, cost_text="unparsed page number 99"))
        self.inputs(vendors=fixtures, prices=[price(100 + index) for index in range(6)])
        self.run_cli()
        for original, result in zip(fixtures, self.rows()):
            for field in COST_FIELDS:
                self.assertEqual(result[field], original[field], (original["item_id"], field))

    def test_whitespace_only_cost_fields_allow_fill(self):
        self.inputs(vendors=[vendor(**dict.fromkeys(COST_FIELDS, "  \t "))])
        self.run_cli()
        self.assertEqual(self.rows()[0]["cost_copper"], "12345")
        self.assertTrue(self.rows()[0]["cost_text"].strip())

    def test_currency_item_and_mixed_offers_keep_costs_without_old_derived_properties(self):
        fixtures = [
            vendor(100, currency_kind="currency", currency_id="77", currency_amount="3", stock="2"),
            vendor(101, currency_kind="item", currency_id="88", currency_amount="4", stock="1"),
            vendor(102, cost_copper="50", cost_text="50c + token", currency_kind="item",
                   currency_id="99", currency_amount="2"),
        ]
        for row in fixtures:
            row.update(buy_count="2", conditions='声望 "尊敬"\n任务完成', source="fixture-page",
                       price_source="fixture-page-price", price_basis="npc-shelf",
                       quantity_source="fixture-page-pack", verified_at="2026-10-18",
                       custom_debug_note="must stay outside CSV")
        extras = ["buy_count", "conditions", "source", "price_source", "price_basis",
                  "quantity_source", "verified_at", "custom_debug_note"]
        self.inputs(vendors=fixtures, prices=[price(i) for i in range(100, 103)],
                    extra_vendor_fields=extras)
        result = self.run_cli()
        stats = self.stats(result)
        self.assertEqual(stats["mixedCostRows"], 1)
        self.assertEqual(stats["mixedCostItems"], 1)
        ns = self.load_lua(self.items_lua)
        for fixture, output in zip(fixtures, self.rows()):
            self.assertEqual(list(output), OUTPUT_FIELDS)
            self.assertNotIn("custom_debug_note", output)
            self.assertEqual(output["VendorStackCount"], "5")
            for field in COST_FIELDS:
                self.assertEqual(output[field], fixture[field])
            offer = ns.ProfItems[int(fixture["item_id"])].offers[10]
            self.assertTrue(set(offer.keys()).issubset(OFFER_FIELDS))
            self.assertEqual(offer.currency_kind, fixture["currency_kind"])
            self.assertEqual(offer.currency_id, int(fixture["currency_id"]))
            self.assertEqual(offer.currency_amount, int(fixture["currency_amount"]))
            self.assertEqual(offer.cost_copper, int(fixture["cost_copper"]) if fixture["cost_copper"] else None)
            self.assertEqual(ns.ProfItems[int(fixture["item_id"])].VendorStackCount, 5)
            self.assertEqual(offer.price_source, "fixture-page-price")
            for removed in ("buyCount", "conditions", "source", "priceSource", "priceBasis",
                            "quantitySource", "verifiedAt", "costKind", "costs", "npcName_locale"):
                self.assertIsNone(offer[removed], removed)

    def test_mixed_cost_stats_count_rows_and_distinct_items_without_treating_zero_as_empty(self):
        self.inputs(vendors=[
            vendor(100, 10, cost_text="50c + token", currency_kind="item"),
            vendor(100, 20, cost_copper="0", currency_amount="0"),
            vendor(101, cost_copper=" \t ", cost_text="  ", currency_kind="currency"),
            vendor(102, cost_copper="0", currency_kind="  ", currency_id=" \t ",
                   currency_amount=" "),
            vendor(103, cost_text="99", currency_id="0"),
            vendor(104, **dict.fromkeys(COST_FIELDS, "  \t ")),
        ], prices=[])
        stats = self.stats(self.run_cli())
        self.assertEqual(stats["mixedCostRows"], 3)
        self.assertEqual(stats["mixedCostItems"], 2)

    def test_missing_and_zero_prices_remain_unknown_instead_of_free(self):
        self.inputs(vendors=[vendor(100), vendor(101), vendor(102)],
                    prices=[price(100, BuyPriceCopper="0", PriceStatus="zero"),
                            price(101, BuyPriceCopper="", VendorStackCount="",
                                  PriceStatus="missing_item_sparse")])
        self.run_cli()
        for row in self.rows():
            self.assertEqual(row["cost_copper"], "")
            self.assertEqual(row["cost_text"], "")
        ns = self.load_lua(self.items_lua)
        for item_id in (100, 101, 102):
            offer = ns.ProfItems[item_id].offers[10]
            self.assertIsNone(offer.cost_copper)
            self.assertIsNone(offer.cost_text)
            self.assertIsNone(offer.costKind)

    def test_all_price_only_items_are_appended_with_no_fabricated_vendor(self):
        self.inputs(prices=[price(), price(200),
                            price(201, BuyPriceCopper="", PriceStatus="missing_item_sparse")])
        self.run_cli()
        rows = {row["item_id"]: row for row in self.rows()}
        self.assertEqual(set(rows), {"100", "200", "201"})
        for item_id in ("200", "201"):
            self.assertEqual(rows[item_id]["npc_id"], "")
            self.assertEqual(rows[item_id]["name_en"], "")
            self.assertEqual(rows[item_id]["Name_zhCN"], "图纸名称")
        ns = self.load_lua(self.items_lua)
        self.assertEqual(len(list(ns.ProfItems[200].offers.items())), 0)
        self.assertEqual(ns.ProfItems[200].item_id, 200)
        self.assertEqual(ns.ProfItems[200].cost_copper, 12345)
        self.assertEqual(ns.ProfItems[200].cost_text, "1g23s45c")
        self.assertEqual(ns.ProfItems[200].price_source, "client")
        self.assertEqual(ns.ProfItems[200].VendorStackCount, 5)
        self.assertIsNone(ns.ProfItems[200].npc_id)
        self.assertIsNone(ns.ProfItems[200].offers[0])
        self.assertEqual(len(list(ns.ProfItems[201].offers.items())), 0)
        self.assertIsNone(ns.ProfItems[201].cost_copper)

    def test_multiple_npcs_for_one_item_do_not_overwrite_each_other(self):
        self.inputs(vendors=[vendor(100, 10, cost_copper="50", cost_text="50c"),
                             vendor(100, 20, cost_copper="60", cost_text="60c", side="h")])
        self.run_cli()
        ns = self.load_lua(self.items_lua)
        self.assertEqual(ns.ProfItems[100].offers[10].cost_copper, 50)
        self.assertEqual(ns.ProfItems[100].offers[20].cost_copper, 60)
        self.assertEqual(ns.ProfItems[100].offers[20].side, "h")

    def test_unicode_quotes_backslashes_and_newlines_round_trip_through_lua(self):
        value = '图纸 "符文"\\路径\n下一行'
        self.inputs(prices=[price(Name_enUS=value, Name_zhTW=value, Name_zhCN=value)],
                    npcs=[npc(name_en=value, name_locale=value)])
        self.run_cli()
        self.assertEqual(self.rows()[0]["Name_zhCN"], value)
        items = self.load_lua(self.items_lua)
        self.assertEqual(items.ProfItems[100].Name_zhCN, value)
        vendors = self.load_lua(self.vendors_lua)
        self.assertEqual(vendors.ProfVendorDetails[10].name_locale, value)

    def test_npc_missing_fields_keep_old_values_zero_coordinate_is_valid_and_all_locations_remain(self):
        self.inputs(npcs=[npc(zone_id="1", ui_map_id="100", x="0", y=""),
                          npc(npc_id=20, zone_id="", ui_map_id="", x="", y=""),
                          npc(npc_id=30, zone_id="12", ui_map_id="1429", x="10", y="20"),
                          npc(npc_id=30, zone_id="12", ui_map_id="1429", x="30", y="40")])
        self.run_cli()
        source = self.vendors_lua.read_text(encoding="utf-8-sig")
        self.assertIn(NPC_LOCS, source)
        ns = self.load_lua(self.vendors_lua)
        self.assertEqual([ns.ProfVendors[10][i] for i in range(1, 5)], [1, 100, 0, 22])
        self.assertEqual([ns.ProfVendors[20][i] for i in range(1, 5)], [2, 200, 33, 44])
        self.assertEqual([ns.ProfVendors[999][i] for i in range(1, 5)], [9, 900, 55, 66])
        self.assertEqual([ns.ProfVendors[30][i] for i in range(1, 5)], [12, 1429, 10, 20])
        self.assertEqual(len(ns.ProfVendorDetails[30].locations), 2)
        self.assertEqual(ns.ProfVendorDetails[10].name_en, "Updated NPC")

    def test_changed_map_without_complete_coordinates_keeps_old_main_location(self):
        self.inputs(npcs=[npc(zone_id="1", ui_map_id="101", x="10", y=""),
                          npc(npc_id=20, zone_id="3", ui_map_id="", x="", y="")])
        self.run_cli()
        ns = self.load_lua(self.vendors_lua)
        self.assertEqual([ns.ProfVendors[10][i] for i in range(1, 5)], [1, 100, 11, 22])
        self.assertEqual([ns.ProfVendors[20][i] for i in range(1, 5)], [2, 200, 33, 44])
        detail = ns.ProfVendorDetails[10].locations[1]
        self.assertEqual([detail[i] for i in range(1, 5)], [1, 101, 10, None])

    def test_changed_zone_with_complete_coordinates_does_not_borrow_old_map_id(self):
        self.inputs(npcs=[npc(zone_id="12", ui_map_id="", x="0", y="50")])
        self.run_cli()
        ns = self.load_lua(self.vendors_lua)
        self.assertEqual([ns.ProfVendors[10][i] for i in range(1, 5)], [12, None, 0, 50])
        detail = ns.ProfVendorDetails[10].locations[1]
        self.assertEqual([detail[i] for i in range(1, 5)], [12, None, 0, 50])

    def test_maintained_vendor_sparse_and_explicit_positions_are_preserved(self):
        self.vendors_lua.write_text('''local _, ns = ...
ns.ProfVendors = {
    [1318] = {[1]=1519,[3]=62.6,[4]=70.8},
    [999] = {[4]=66,[2]=900,[1]=9,[3]=55},
    [998] = {[1]=9,[2]=nil,[4]=0},
}
ns.Preserved = 42
''', encoding='utf-8')
        self.inputs(npcs=[])
        self.run_cli()
        ns = self.load_lua(self.vendors_lua)
        self.assertEqual([ns.ProfVendors[1318][i] for i in range(1, 5)], [1519, None, 62.6, 70.8])
        self.assertEqual([ns.ProfVendors[999][i] for i in range(1, 5)], [9, 900, 55, 66])
        self.assertEqual([ns.ProfVendors[998][i] for i in range(1, 5)], [9, None, None, 0])
        self.assertEqual(ns.Preserved, 42)

    def test_maintained_vendor_unknown_duplicate_or_mixed_positions_are_rejected(self):
        for body in ('[1]=9,[5]=55', '[1]=9,[1]=10', '[1]=9,900,55,66',
                     '[1]=9,[2]=900,[3]=function() end', 'name="unknown"'):
            with self.subTest(body=body):
                text = 'local _, ns = ...\nns.ProfVendors = {[999] = {' + body + '}}\n'
                self.vendors_lua.write_text(text, encoding='utf-8')
                self.inputs(npcs=[])
                self.run_cli(success=False)
                self.assertEqual(self.vendors_lua.read_text(encoding='utf-8'), text)

    def test_explicit_verification_date_does_not_add_properties_outside_csv_schema(self):
        self.run_cli("--verified-at", "2026-10-20")
        self.assertEqual(list(self.rows()[0]), OUTPUT_FIELDS)
        ns = self.load_lua(self.items_lua)
        self.assertIsNone(ns.ProfItems[100].verifiedAt)
        self.assertIsNone(ns.ProfItems[100].offers[10].verifiedAt)

    def test_from_csv_uses_existing_rows_and_only_writes_items_without_original_inputs(self):
        self.merged_input([merged_row(cost_copper="387", cost_text="3s87c", VendorStackCount="7",
                                      Name_zhCN='CSV "名称"\\路径\n下一行',
                                      Build="007.60", HotfixBuild="0070450", price_source="csv-reference")])
        for path in (self.vendors, self.npcs, self.prices):
            path.unlink()
        before = {path: path.read_bytes() for path in (self.output, self.vendors_lua)}
        self.items_lua.write_bytes(b"previous items\n")
        self.run_from_csv()
        self.assert_outputs_unchanged(before)
        self.assertTrue(all(not path.exists() for path in (self.vendors, self.npcs, self.prices)))
        ns = self.load_lua(self.items_lua)
        self.assertEqual(ns.ProfItemsMeta.schemaVersion, 2)
        item = ns.ProfItems[100]
        self.assertEqual(set(item.keys()), set(ITEM_FIELDS))
        self.assertEqual(item.item_id, 100)
        self.assertEqual(item.Name_zhCN, 'CSV "名称"\\路径\n下一行')
        self.assertEqual(item.VendorStackCount, 7)
        self.assertEqual(item.Build, "007.60")
        self.assertEqual(item.HotfixBuild, "0070450")
        offer = item.offers[10]
        self.assertEqual(offer.npc_id, 10)
        self.assertEqual(offer.cost_copper, 387)
        self.assertEqual(offer.cost_text, "3s87c")
        self.assertEqual(offer.price_source, "csv-reference")

    def test_from_csv_no_npc_keeps_root_exchange_price_without_inventing_supplier(self):
        self.merged_input([merged_row(200, npc_id="", name_en="", zone_id="", side="",
                                      cost_copper="0", cost_text="0c + 3 tokens", currency_kind="item",
                                      currency_id="77", currency_amount="3", stock="", price_source="wowhead"),
                           merged_row(201, npc_id="", name_en="", zone_id="", side="", cost_copper="",
                                      cost_text="", stock="", VendorStackCount="", price_source="")])
        self.run_from_csv()
        ns = self.load_lua(self.items_lua)
        item = ns.ProfItems[200]
        self.assertEqual(item.item_id, 200)
        self.assertEqual(item.cost_copper, 0)
        self.assertEqual(item.cost_text, "0c + 3 tokens")
        self.assertEqual(item.currency_kind, "item")
        self.assertEqual(item.currency_id, 77)
        self.assertEqual(item.currency_amount, 3)
        self.assertEqual(item.price_source, "wowhead")
        self.assertEqual(len(list(item.offers.items())), 0)
        self.assertIsNone(item.npc_id)
        self.assertIsNone(item.offers[0])
        empty = ns.ProfItems[201]
        for field in ("cost_copper", "cost_text", "VendorStackCount", "stock", "price_source"):
            self.assertIsNone(empty[field], field)
        self.assertTrue(set(item.keys()).issubset(set(ITEM_FIELDS + OFFER_FIELDS)))

    def test_from_csv_dry_run_preserves_existing_outputs_and_does_not_require_original_inputs(self):
        self.merged_input([merged_row()])
        for path in (self.vendors, self.npcs, self.prices):
            path.unlink()
        self.items_lua.write_bytes(b"previous items\n")
        before = {path: path.read_bytes() for path in (self.output, self.items_lua, self.vendors_lua)}
        self.run_from_csv("--dry-run")
        self.assert_outputs_unchanged(before)

    def test_from_csv_requires_exact_column_names_and_order_without_partial_update(self):
        self.items_lua.write_bytes(b"previous items\n")
        original = merged_row()
        for columns in (OUTPUT_FIELDS[::-1], OUTPUT_FIELDS + ["custom_debug_note"], OUTPUT_FIELDS[:-1]):
            with self.subTest(columns=columns):
                self.merged_input([{field: original.get(field, "extra") for field in columns}], fields=columns)
                before = {path: path.read_bytes() for path in (self.output, self.items_lua, self.vendors_lua)}
                self.run_from_csv(success=False)
                self.assert_outputs_unchanged(before)

    def test_from_csv_rejects_duplicate_item_npc_pairs_even_if_rows_are_identical(self):
        self.items_lua.write_bytes(b"previous items\n")
        for rows in ([merged_row(), merged_row()],
                     [merged_row(), merged_row(cost_copper="99")],
                     [merged_row(npc_id=""), merged_row(npc_id="")]):
            with self.subTest(npc=rows[0]["npc_id"], price=rows[1]["cost_copper"]):
                self.merged_input(rows)
                before = {path: path.read_bytes() for path in (self.output, self.items_lua, self.vendors_lua)}
                self.run_from_csv(success=False)
                self.assert_outputs_unchanged(before)

    def test_from_csv_rejects_conflicting_shared_item_properties_across_suppliers(self):
        self.items_lua.write_bytes(b"previous items\n")
        for field in ("Name_enUS", "Name_zhTW", "Name_zhCN", "VendorStackCount", "PriceStatus", "Build", "HotfixBuild"):
            with self.subTest(field=field):
                other = merged_row(npc_id=20, **{field: "7" if field == "VendorStackCount" else "different"})
                self.merged_input([merged_row(), other])
                before = {path: path.read_bytes() for path in (self.output, self.items_lua, self.vendors_lua)}
                self.run_from_csv(success=False)
                self.assert_outputs_unchanged(before)

    def test_dry_run_does_not_create_outputs_or_change_vendor_lua(self):
        before = self.vendors_lua.read_bytes()
        self.run_cli("--dry-run")
        self.assertFalse(self.output.exists())
        self.assertFalse(self.items_lua.exists())
        self.assertEqual(self.vendors_lua.read_bytes(), before)

    def test_dry_run_preserves_all_existing_outputs_byte_for_byte(self):
        before = self.old_outputs()
        self.run_cli("--dry-run")
        self.assert_outputs_unchanged(before)

    def test_missing_input_fails_without_partial_updates(self):
        before = self.old_outputs()
        self.prices.unlink()
        self.run_cli(success=False)
        self.assert_outputs_unchanged(before)

    def test_conflicting_duplicate_item_prices_fail_without_partial_updates(self):
        self.inputs(prices=[price(), price(BuyPriceCopper="999")])
        before = self.old_outputs()
        self.run_cli(success=False)
        self.assert_outputs_unchanged(before)

    def test_conflicting_duplicate_item_npc_pair_fails_without_partial_updates(self):
        self.inputs(vendors=[vendor(cost_copper="50"), vendor(cost_copper="60")])
        before = self.old_outputs()
        self.run_cli(success=False)
        self.assert_outputs_unchanged(before)

    def test_output_directory_collision_fails_without_replacing_other_outputs(self):
        self.output.parent.mkdir(exist_ok=True)
        self.output.write_bytes(b"previous csv\n")
        before = {path: path.read_bytes() for path in (self.output, self.vendors_lua)}
        self.items_lua.mkdir()
        marker = self.items_lua / "keep.txt"
        marker.write_bytes(b"keep directory contents\n")
        self.run_cli(success=False)
        self.assert_outputs_unchanged(before)
        self.assertEqual(marker.read_bytes(), b"keep directory contents\n")

    def test_invalid_verification_date_fails_without_partial_updates(self):
        before = self.old_outputs()
        for invalid in ("2026-02-30", "20261020", "2026-W43-2"):
            with self.subTest(date=invalid):
                self.run_cli("--verified-at", invalid, success=False)
                self.assert_outputs_unchanged(before)


if __name__ == "__main__":
    unittest.main()
