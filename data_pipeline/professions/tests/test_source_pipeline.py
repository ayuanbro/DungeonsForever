"""Offline acquisition contracts and source failures, independent of old addon data."""
from __future__ import annotations

import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import zipfile

from data_pipeline.professions.build import build, mask_ids, normalize
from data_pipeline.professions.fetch import WowheadTransport, fetch, snapshot_archive
from data_pipeline.professions.model import (TABLES, SourceError, classify_response, discover,
    integer, load_tables, parse_csv, parse_page, sha256, write_json)

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None


VERSION = "1.60.1.70001"
BUILD = {"product": "wowf", "version": VERSION, "build_config": "a" * 32}


def temporary_directory():
    # Keep verification artifacts in the writable workspace, including under
    # Windows managed environments whose default temp directory has a narrow ACL.
    return tempfile.TemporaryDirectory(prefix=".pipeline-test-", dir=Path(__file__).resolve().parent)


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue().encode()


def fixture_tables():
    tables = {name: [{"ID": "1"}] for name in TABLES}
    tables.update({
        "SkillLineAbility": [
            {"ID": "1", "SkillLine": "171", "Spell": "1000", "ClassMask": "0", "RaceMasks_0": "0", "RaceMasks_1": "0", "TrivialSkillLineRankHigh": "50"},
            {"ID": "2", "SkillLine": "171", "Spell": "1001", "ClassMask": "8", "RaceMasks_0": "0", "RaceMasks_1": "0", "TrivialSkillLineRankHigh": "50"},
            {"ID": "3", "SkillLine": "171", "Spell": "1002", "ClassMask": "0", "RaceMasks_0": "0", "RaceMasks_1": "0", "TrivialSkillLineRankHigh": "0"}],
        "ItemXItemEffect": [{"ID": "1", "ItemID": "2000", "ItemEffectID": "1"}, {"ID": "2", "ItemID": "2001", "ItemEffectID": "2"}],
        "ItemEffect": [{"ID": "1", "TriggerType": "6", "SpellID": "1000", "PlayerConditionID": "0"},
                       {"ID": "2", "TriggerType": "6", "SpellID": "1001", "PlayerConditionID": "0"}],
        "ItemSparse": [{"ID": "2000", "RequiredSkill": "171", "RequiredSkillRank": "10", "RequiredLevel": "5", "AllowableClass": "-1",
                        "RequiredAbility": "0", "MinFactionID": "529", "MinReputation": "6", "AllowableRace_0": "-1", "AllowableRace_1": "-1",
                        "Bonding": "1", "VendorStackCount": "5"}],
        "SpellEffect": [{"ID": "1", "SpellID": "1000", "Effect": "24", "EffectTriggerSpell": "0"},
                        {"ID": "2", "SpellID": "1001", "Effect": "24", "EffectTriggerSpell": "0"}],
        "SpellReagents": [{"ID": "1", "SpellID": "1000", "Reagent_0": "10"}],
        "SpellLearnSpell": [{"ID": "1", "SpellID": "1000", "LearnSpellID": "0"}],
        "ChrRaces": [{"ID": "1", "PlayableRaceBit": "0"}, {"ID": "95", "PlayableRaceBit": "32"}],
        "ChrClasses": [{"ID": "1"}, {"ID": "4"}],
    })
    return tables


def page_bytes(kind, entity, views, markup=()):
    label = "NPC" if kind == "npc" else kind.title()
    text = f"<html><title>Example - {label} - Forever</title><script>"
    for name, rows in views.items():
        text += "new Listview({id:'" + name + "',data:" + json.dumps(rows) + "});"
    for value in markup:
        text += "WH.markup.printHtml(" + json.dumps(value) + ",'target');"
    return (text + "</script></html>").encode()


def snapshot(root, with_web=True):
    responses = []
    for name, rows in fixture_tables().items():
        data = csv_bytes(rows); relative = f"responses/db2-{name}.csv"
        (root / "responses").mkdir(exist_ok=True)
        (root / relative).write_bytes(data)
        responses.append({"key": "db2:" + name, "status": "verified", "path": relative,
            "sha256": sha256(data), "url": f"https://wago.tools/db2/{name}/csv?build={VERSION}&locale=enUS"})
    if with_web:
        for kind, entity, views in [
            ("spell", 1000, {"recipes": [{"id": 1000, "learnedat": 10, "trainingcost": 25}], "taught-by-npc": [{"id": 3000}]}),
            ("item", 2000, {"sold-by": [{"id": 3000, "cost": [[75]], "stock": -1}]}),
        ]:
            data = page_bytes(kind, entity, views); relative = f"responses/web-{kind}-{entity}.html"
            (root / relative).write_bytes(data)
            responses.append({"key": f"web:{kind}:{entity}", "status": "verified", "path": relative, "sha256": sha256(data),
                "url": f"https://www.wowhead.com/forever/{kind}={entity}", "finalUrl": f"https://www.wowhead.com/forever/{kind}={entity}/example"})
    manifest = {"schema": 1, "product": "wowf", "build": VERSION, "buildInfo": BUILD,
                "latestAfter": BUILD, "fetchComplete": True, "responses": responses}
    write_json(root / "manifest.json", manifest)
    return manifest


class ParserContracts(unittest.TestCase):
    def test_exact_integer_and_unmapped_masks(self):
        self.assertEqual(integer("18446744073709551615"), 2**64 - 1)
        with self.assertRaises(SourceError):
            integer(float(2**54))
        self.assertEqual(mask_ids(1 << 32, fixture_tables()["ChrRaces"], race=True), [95])
        with self.assertRaises(SourceError):
            mask_ids((1 << 32) | (1 << 50), fixture_tables()["ChrRaces"], race=True)

    def test_malformed_tables_and_challenges_do_not_become_empty_success(self):
        for bad in (b"<html>challenge</html>", b"ID,ID\n1,1\n", b"ID,Spell\n1\n", b"ID\n1\n1\n"):
            with self.subTest(bad=bad), self.assertRaises(SourceError):
                parse_csv(bad, "SpellName")
        for status in (202, 403, 429):
            self.assertEqual(classify_response(status, b""), "sourceBlocked")
        self.assertEqual(classify_response(200, b"window.gokuProps={};"), "sourceBlocked")
        self.assertEqual(classify_response(404, b'{"error":"Entity not found"}'), "sourceMissing")

    def test_literal_json_only_and_identity_guards(self):
        page = page_bytes("spell", 1000, {"recipes": [{"id": 1000}]})
        parsed = parse_page(page, "spell", 1000, "https://www.wowhead.com/forever/spell=1000/test")
        self.assertEqual(parsed["listviews"]["recipes"][0]["id"], 1000)
        for url in ("https://www.wowhead.com/forever/items?notFound=1000", "https://www.wowhead.com/classic/spell=1000"):
            with self.subTest(url=url), self.assertRaises(SourceError):
                parse_page(page, "spell", 1000, url)

    def test_discovery_does_not_turn_rank_abilities_into_crafting(self):
        members, teaching = discover(fixture_tables())
        self.assertIn(("alchemy", 1000), members)
        self.assertNotIn(("alchemy", 1002), members)
        self.assertIn(2000, teaching[1000])


class BuildContracts(unittest.TestCase):
    def test_missing_item_does_not_confirm_an_empty_condition_list(self):
        with temporary_directory() as temp:
            root = Path(temp); manifest = snapshot(root)
            facts, _ = normalize(root, manifest)
            self.assertTrue(facts["alchemy"][1000]["routes"][0]["conditionsKnown"])
            item = next(r for r in facts["alchemy"][1000]["routes"] if r["kind"] == "item")
            self.assertIn({"kind": "reputation", "factionID": 529, "value": 6}, item["conditions"])
            self.assertEqual(item["acquisition"]["vendors"][0]["quantity"], 5)
            self.assertEqual(item["acquisition"]["status"], "unknown")
            self.assertFalse(item["acquisition"]["conditionsKnown"])
            missing = facts["alchemy"][1001]
            self.assertIn("itemDetailsMissing", missing["missingReasons"])
            self.assertFalse(missing["routes"][0]["conditionsKnown"])

    def test_unknown_player_condition_stays_unknown(self):
        with temporary_directory() as temp:
            root = Path(temp); manifest = snapshot(root)
            row = next(r for r in manifest["responses"] if r["key"] == "db2:ItemEffect")
            data = (root / row["path"]).read_bytes().replace(b"1000,0", b"1000,999")
            (root / row["path"]).write_bytes(data); row["sha256"] = sha256(data)
            facts, _ = normalize(root, manifest)
            item = next(r for r in facts["alchemy"][1000]["routes"] if r["kind"] == "item")
            self.assertFalse(item["conditionsKnown"])
            self.assertIn("unsupportedPlayerCondition", facts["alchemy"][1000]["missingReasons"])

    def test_checksum_version_failure_leaves_formal_output_untouched(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            lua, report = root / "sources.lua", root / "audit.json"
            lua.write_bytes(b"keep"); report.write_bytes(b"keep-report")
            (raw / manifest["responses"][0]["path"]).write_bytes(b"truncated")
            with self.assertRaises(SourceError):
                build(raw, lua, report)
            self.assertEqual(lua.read_bytes(), b"keep")
            self.assertEqual(report.read_bytes(), b"keep-report")

    def test_offline_archive_rebuild_check_and_semantic_fingerprint(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            lua, report = root / "sources.lua", root / "audit.json"
            build(raw, lua, report); first = lua.read_bytes()
            archive = root / "raw.zip"; snapshot_archive(raw, archive)
            build(archive, lua, report, check=True)
            # Evidence fetch timestamps are audit data, not runtime identity.
            manifest["responses"][0]["fetchedAt"] = "later"
            write_json(raw / "manifest.json", manifest)
            build(raw, lua, report)
            self.assertEqual(first, lua.read_bytes())
            lua.write_bytes(b"tampered")
            with self.assertRaises(SourceError):
                build(raw, lua, report, check=True)

    def test_cross_build_table_and_zip_escape_are_rejected(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            manifest["responses"][0]["url"] = manifest["responses"][0]["url"].replace(VERSION, "1.60.1.69999")
            with self.assertRaises(SourceError):
                load_tables(raw, manifest)
            archive = root / "evil.zip"
            with zipfile.ZipFile(archive, "w") as out:
                out.writestr("../escape", b"bad")
            with self.assertRaises(SourceError):
                build(archive, root / "out.lua", root / "report.json")

    def test_archive_contains_only_manifest_references_and_all_are_verified(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            (raw / "responses" / "obsolete-failure.html").write_bytes(b"old response without current evidence")
            archive = root / "raw.zip"; snapshot_archive(raw, archive)
            with zipfile.ZipFile(archive) as locked:
                referenced = {"manifest.json"} | {r["path"] for r in manifest["responses"] if "path" in r}
                self.assertEqual(set(locked.namelist()), referenced)
                self.assertIsNone(locked.testzip())
                for record in manifest["responses"]:
                    if "path" in record:
                        self.assertEqual(sha256(locked.read(record["path"])), record["sha256"])

    def test_archive_rejects_escaping_or_corrupt_inputs_before_replacement(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            archive = root / "raw.zip"; archive.write_bytes(b"keep previous archive")
            row = manifest["responses"][0]
            original = copy.deepcopy(row)
            row["path"] = "../outside.csv"
            write_json(raw / "manifest.json", manifest)
            with self.assertRaises(SourceError):
                snapshot_archive(raw, archive)
            self.assertEqual(archive.read_bytes(), b"keep previous archive")
            row.clear(); row.update(original)
            write_json(raw / "manifest.json", manifest)
            (raw / row["path"]).write_bytes(b"corrupt response")
            with self.assertRaises(SourceError):
                snapshot_archive(raw, archive)
            self.assertEqual(archive.read_bytes(), b"keep previous archive")

    @unittest.skipIf(LuaRuntime is None, "install requirements-dev.lock for Lua5.1 codec test")
    def test_lazy_lua_materialization_keeps_negative_values_and_named_contract(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); snapshot(raw)
            lua_path, report = root / "sources.lua", root / "audit.json"; build(raw, lua_path, report)
            vm = LuaRuntime(unpack_returned_tuples=True); vm.execute("ns={IsForever=true}")
            vm.execute("assert(loadstring(...,'@test-sources'))('DungeonsForever',ns)", lua_path.read_text(encoding="utf8"))
            vm.execute("""
                local provider=ns.ProfLearningSources
                local view=provider.ForProfession('alchemy')
                local record=view[1000];assert(record.spell==1000 and record.profession=='alchemy')
                assert(not pcall(function()record.routes={}end))
                local plain=provider.Materialize(record)
                assert(getmetatable(plain)==nil and plain.routes[1].kind=='trainer')
                local item=plain.routes[2];assert(item.trainingCost==nil)
                assert(item.acquisition.vendors[1].stock==-1)
                assert(item.acquisition.vendors[1].quantity==5)
                assert(provider.Get('first-aid',1000)==nil)
                assert(provider.Get('alchemy',1001).routes[1].conditionsKnown==false)
            """)


class AcquisitionContracts(unittest.TestCase):
    def test_latest_change_restarts_and_never_mixes_tables(self):
        with temporary_directory() as temp:
            root = Path(temp); out = root / "raw"; tables = fixture_tables()
            newer = dict(BUILD, version="1.60.1.70002", build_config="b" * 32)
            def get(url, retries=3):
                parts = urlsplit(url); table = parts.path.split("/")[-2]; version = parse_qs(parts.query)["build"][0]
                return 200, csv_bytes(tables[table]), {"Content-Type": "text/csv", "Content-Disposition": f'attachment; filename="{table}.{version}.csv"'}, url
            with patch("data_pipeline.professions.fetch.latest", side_effect=[BUILD, newer, newer, newer]), patch("data_pipeline.professions.fetch.ordinary_get", side_effect=get):
                fetch(out, web_limit=0, log=lambda *a, **k: None)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["build"], newer["version"])
            self.assertTrue(manifest["fetchComplete"])
            self.assertFalse(manifest["sourceCoverageComplete"])
            load_tables(out, manifest)
            self.assertTrue((root / ("raw.partial.changed-" + VERSION)).exists())

    def test_host_circuit_prevents_thousands_of_blocked_network_requests(self):
        transport = WowheadTransport(interval=0)
        class Response:
            status_code = 403; content = b"blocked"; headers = {}; url = "https://www.wowhead.com/forever/spell=1000"
        with patch.object(transport, "session") as session, patch.object(transport, "bootstrap", return_value=False):
            session.return_value.get.return_value = Response()
            transport.get(Response.url); transport.get(Response.url)
            with self.assertRaises(SourceError):
                transport.get(Response.url)
            self.assertEqual(session.return_value.get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
