"""Offline acquisition contracts and source failures, independent of old addon data."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit
import zipfile

from data_pipeline.professions.build import build, mask_ids, normalize
from data_pipeline.professions.browser_transport import BrowserClosed, BrowserTransport
from data_pipeline.professions.fetch import (HostCircuitOpen, WowheadTransport, fetch,
    entity_url, fresh_route_names, referenced_entities, response_evidence, response_record,
    retain_response_evidence, route_slug, snapshot_archive)
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


def snapshot(root, with_web=True, tables=None):
    responses = []
    for name, rows in (fixture_tables() if tables is None else tables).items():
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

    def test_name_slug_is_only_a_safe_route_hint_with_id_primary(self):
        cases = {"Rough Bronze Bracers": "rough-bronze-bracers",
                 "Formula: Enchant Bracer - Healing": "formula-enchant-bracer-healing",
                 "Mithril Engineer's Hammer": "mithril-engineers-hammer",
                 "Élan’s &amp; Arcane (Rank 2)": "elans-arcane-rank-2"}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(route_slug(name), expected)
        for unknown in (None, "", "   ", "术", "<script>payload</script>", "x" * 201):
            self.assertEqual(route_slug(unknown), "")
            self.assertEqual(entity_url("item", 5577, {("item", 5577): unknown}),
                             "https://www.wowhead.com/forever/item=5577")
        with self.assertRaises(SourceError):
            entity_url("spell/../../", 2671)
        with self.assertRaises(SourceError):
            entity_url("spell", "2671/other")

    def test_fresh_db2_and_supported_list_names_feed_urls_without_becoming_facts(self):
        tables = {"SpellName": [{"ID": "2671", "Name_lang": "Rough Bronze Bracers"}],
                  "ItemSparse": [{"ID": "19447", "Display_lang": "Formula: Enchant Bracer - Healing"},
                                 {"ID": "5577", "Display_lang": ""}]}
        names = fresh_route_names(tables)
        parsed = {"listviews": {
            "taught-by-npc": [{"id": 3967, "name": "Aayndia Floralwind"}],
            "taught-by-item": [{"id": 19447, "name": "A conflicting label"}, {"id": 5577, "name": "Plans: Rough Bronze Bracers"}],
            "reward-from-q": [{"id": 4000, "name": "Bob's Supplies"}],
            "see-also": [{"id": 9999, "name": "Unrelated"}]}}
        self.assertEqual(referenced_entities(parsed, names), {
            ("npc", 3967), ("item", 19447), ("item", 5577), ("quest", 4000)})
        self.assertEqual(entity_url("spell", 2671, names), "https://www.wowhead.com/forever/spell=2671/rough-bronze-bracers")
        self.assertEqual(entity_url("item", 19447, names), "https://www.wowhead.com/forever/item=19447/formula-enchant-bracer-healing")
        self.assertEqual(entity_url("item", 5577, names), "https://www.wowhead.com/forever/item=5577/plans-rough-bronze-bracers")
        self.assertEqual(entity_url("npc", 3967, names), "https://www.wowhead.com/forever/npc=3967/aayndia-floralwind")
        self.assertEqual(entity_url("quest", 4000, names), "https://www.wowhead.com/forever/quest=4000/bobs-supplies")
        self.assertNotIn(("npc", 9999), names)
        self.assertEqual(tables["ItemSparse"][1]["Display_lang"], "")


class BuildContracts(unittest.TestCase):
    def test_missing_item_does_not_confirm_an_empty_condition_list(self):
        with temporary_directory() as temp:
            root = Path(temp); manifest = snapshot(root)
            facts, _ = normalize(root, manifest)
            self.assertTrue(facts["alchemy"][1000]["routes"][0]["conditionsKnown"])
            item = next(r for r in facts["alchemy"][1000]["routes"] if r["kind"] == "item")
            self.assertIn({"kind": "reputation", "factionID": 529, "value": 7}, item["conditions"])
            self.assertEqual(item["acquisition"]["vendors"][0]["quantity"], 5)
            self.assertEqual(item["acquisition"]["status"], "unknown")
            self.assertFalse(item["acquisition"]["conditionsKnown"])
            missing = facts["alchemy"][1001]
            self.assertIn("itemDetailsMissing", missing["missingReasons"])
            self.assertFalse(missing["routes"][0]["conditionsKnown"])

    def test_item_reputation_uses_client_ranks_and_invalid_values_stay_unknown(self):
        # The raw enum is Hated=0..Exalted=7, while client reactions are 1..8.
        # None/empty/missing are separate cases: none may become implicit zero.
        cases = [(str(rank), rank + 1) for rank in range(8)] + [
            (None, None), ("", None), ("missing", None), ("-1", None),
            ("8", None), ("6.5", None), ("invalid", None)]
        for raw_rank, expected in cases:
            with self.subTest(raw_rank=raw_rank), temporary_directory() as temp:
                tables = fixture_tables(); item = tables["ItemSparse"][0]
                if raw_rank == "missing":
                    del item["MinReputation"]
                else:
                    item["MinReputation"] = raw_rank
                root = Path(temp); manifest = snapshot(root, with_web=False, tables=tables)
                facts, _ = normalize(root, manifest)
                record = facts["alchemy"][1000]
                route = next(r for r in record["routes"] if r["kind"] == "item")
                reputations = [c for c in route["conditions"] if c["kind"] == "reputation"]
                if expected is None:
                    self.assertEqual(reputations, [])
                    self.assertFalse(route["conditionsKnown"])
                    self.assertEqual(route["status"], "unknown")
                    self.assertIn("learningRequirementsUnknown", record["missingReasons"])
                else:
                    self.assertEqual(reputations, [{"kind": "reputation", "factionID": 529, "value": expected}])
                    self.assertTrue(route["conditionsKnown"])

    @unittest.skipIf(LuaRuntime is None, "Lua 5.1 test extra is not installed")
    def test_real_revered_identity_source_to_generated_lua_and_runtime(self):
        # This minimal source fixture retains the actual build-70658 identity:
        # ItemSparse[19447], MinFactionID=529, MinReputation=6 teaches 23802.
        # Official Forever tooltip dataEnv=16 calls that requirement Revered.
        # Native addon files below are the consumer under test, never inputs to
        # normalize/build or fallback data for the source fixture.
        from validation.test_prof_native_data import native_runtime

        tables = fixture_tables()
        tables["SkillLineAbility"] = [dict(tables["SkillLineAbility"][0], SkillLine="333", Spell="23802")]
        tables["ItemXItemEffect"] = [{"ID": "1", "ItemID": "19447", "ItemEffectID": "1"}]
        tables["ItemEffect"] = [{"ID": "1", "TriggerType": "6", "SpellID": "23802", "PlayerConditionID": "0"}]
        tables["ItemSparse"] = [dict(tables["ItemSparse"][0], ID="19447", RequiredSkill="333", RequiredSkillRank="300", RequiredLevel="0")]
        tables["SpellEffect"] = [{"ID": "1", "SpellID": "23802", "Effect": "24", "EffectTriggerSpell": "0"}]
        tables["SpellReagents"] = [{"ID": "1", "SpellID": "23802", "Reagent_0": "10"}]
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir()
            manifest = snapshot(raw, with_web=False, tables=tables)
            self.assertEqual(load_tables(raw, manifest)["ItemSparse"][0]["MinReputation"], "6")
            lua, report = root / "sources.lua", root / "audit.json"
            build(raw, lua, report)
            vm = native_runtime(); vm.execute("ns.IsForever=true")
            vm.execute("assert(loadstring(...,'@reputation-source-test'))('DungeonsForever',ns)", lua.read_text(encoding="utf8"))
            vm.execute("""
                assert(ns.ProfLearningSources.meta.rules==2)
                local route=ns.ProfLearningSources.Get('enchanting',23802).routes[1]
                local reputation
                for _,condition in ipairs(route.conditions)do
                    if condition.kind=='reputation'then reputation=condition end
                end
                assert(reputation.factionID==529 and reputation.value==7)
                local E=ns.ProfEconomy
                local recipe=assert(E.FindRecipe('enchanting',23802))
                local input={known={},professions={enchanting={cur=300,max=300}},
                    level=60,classID=4,raceID=1,faction='A',ownedTeachingItems={[19447]=1},
                    reputations={[529]=6},specializationAbilities={},completedQuests={},
                    prices={},formulaOffers={},offers={},nonAuctionable={}}
                local allowed,reason=E.RouteRecipeEligibility(recipe,input)
                assert(not allowed and reason=='reputationRequired')
                for _,rank in ipairs({7,8})do
                    input.reputations[529]=rank
                    local ok,_,detail=E.RouteRecipeEligibility(recipe,input)
                    assert(ok and detail.routeId=='item:23802:19447')
                end
            """)

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
        factory = MagicMock()
        transport = WowheadTransport(interval=0, browser_factory=factory)
        class Response:
            status_code = 403; content = b"blocked"; headers = {}; url = "https://www.wowhead.com/forever/spell=1000"
        with transport, patch.object(transport, "session") as session:
            session.return_value.get.return_value = Response()
            transport.get(Response.url); transport.get(Response.url)
            with self.assertRaises(HostCircuitOpen):
                transport.get(Response.url)
            self.assertEqual(session.return_value.get.call_count, 2)
            factory.assert_not_called()  # A plain 403 is not a JS challenge.

    def test_js_challenge_switches_to_browser_without_cookie_round_trip(self):
        url = "https://www.wowhead.com/forever/spell=1000"
        browser = MagicMock()
        browser.get.side_effect = [(200, b"entity", {}, url), (404, b"Entity not found", {}, url)]
        factory = MagicMock(return_value=browser)
        with WowheadTransport(interval=0, browser_factory=factory) as transport:
            with patch.object(transport, "session") as session:
                session.return_value.get.return_value = SimpleNamespace(
                    status_code=202, content=b"challenge", headers={}, url=url)
                self.assertEqual(transport.get(url)[0], 200)
                self.assertEqual(transport.get(url)[0], 404)
                session.return_value.get.assert_called_once_with(url, timeout=35)
                self.assertEqual(browser.get.call_count, 2)
                factory.assert_called_once_with()
        browser.close.assert_called_once_with()
        transport.close()
        with self.assertRaises(SourceError):
            transport.get(url)

    def test_explicit_browser_mode_never_starts_direct_http(self):
        url = "https://www.wowhead.com/forever/spell=2671"
        browser = MagicMock()
        browser.get.side_effect = [(200, b"entity", {}, url), (404, b"Entity not found", {}, url)]
        factory = MagicMock(return_value=browser)
        with WowheadTransport(interval=0, browser_factory=factory, mode="browser") as transport:
            with patch.object(transport, "session", side_effect=AssertionError("HTTP must not start")) as session:
                self.assertEqual(transport.get(url)[0], 200)
                self.assertEqual(transport.last_transport, "browser")
                self.assertEqual(transport.get(url)[0], 404)
                self.assertEqual(transport.last_transport, "browser")
                session.assert_not_called()
                factory.assert_called_once_with()
        browser.close.assert_called_once_with()

    def test_http_profile_owns_its_headers_and_resources_are_closed(self):
        url = "https://www.wowhead.com/forever/spell=1000"
        session = MagicMock()
        session.get.return_value = SimpleNamespace(status_code=200, content=b"entity", headers={}, url=url)
        requests = SimpleNamespace(Session=MagicMock(return_value=session))
        with patch.dict("sys.modules", {"curl_cffi": SimpleNamespace(requests=requests)}):
            with WowheadTransport(interval=0) as transport:
                self.assertEqual(transport.get(url)[0], 200)
            requests.Session.assert_called_once_with(impersonate="chrome", use_thread_local_curl=False)
            session.get.assert_called_once_with(url, timeout=35)
            session.close.assert_called_once_with()

    def test_close_releases_other_sessions_after_an_individual_close_failure(self):
        transport = WowheadTransport(interval=0)
        transport._browser = MagicMock()
        transport._browser.close.side_effect = RuntimeError("browser close failed")
        first, second = MagicMock(), MagicMock()
        first.close.side_effect = RuntimeError("HTTP close failed")
        transport._sessions = [first, second]
        with self.assertRaisesRegex(RuntimeError, "browser close failed"):
            transport.close()
        first.close.assert_called_once_with()
        second.close.assert_called_once_with()
        transport.close()

    def test_unsent_circuit_retry_preserves_real_response_evidence(self):
        with temporary_directory() as temp:
            root = Path(temp)
            key, url = "web:spell:1000", "https://www.wowhead.com/forever/spell=1000"
            previous = response_record(root, key, url, lambda _: (403, b"origin denied", {}, url))
            def unsent(_):
                raise HostCircuitOpen("not requested")
            skipped = response_record(root, key, url, unsent)
            self.assertEqual(skipped["status"], "notFetched")
            self.assertFalse(skipped["attempted"])
            self.assertEqual(skipped["errorCode"], "hostCircuitOpen")
            self.assertNotIn("httpStatus", skipped)
            kept = retain_response_evidence(previous, skipped)
            self.assertEqual(kept["httpStatus"], 403)
            self.assertEqual(kept["sha256"], sha256(b"origin denied"))
            self.assertEqual((root / kept["path"]).read_bytes(), b"origin denied")
            self.assertFalse(kept["lastAttempt"]["attempted"])
            later = response_record(root, key, url, lambda _: (403, b"new denial", {}, url))
            self.assertNotEqual(later["path"], previous["path"])
            self.assertEqual((root / previous["path"]).read_bytes(), b"origin denied")

    def test_fetch_closes_transport_before_final_version_probe_failure(self):
        with temporary_directory() as temp:
            root = Path(temp); tables = fixture_tables()
            def get(url, retries=3):
                name = urlsplit(url).path.split("/")[-2]
                return 200, csv_bytes(tables[name]), {"Content-Type": "text/csv",
                    "Content-Disposition": f'attachment; filename="{name}.{VERSION}.csv"'}, url
            with patch("data_pipeline.professions.fetch.latest", side_effect=[BUILD, RuntimeError("version unavailable")]), \
                 patch("data_pipeline.professions.fetch.ordinary_get", side_effect=get), \
                 patch.object(WowheadTransport, "close", autospec=True) as close:
                with self.assertRaises(RuntimeError):
                    fetch(root / "raw", web_limit=0, log=lambda *a, **k: None)
                close.assert_called_once()


class RefreshRunContracts(unittest.TestCase):
    @staticmethod
    def page_response(url, retries=3):
        kind, entity = urlsplit(url).path.rsplit("/", 1)[1].split("=")
        entity = int(entity)
        views = {"recipes": [{"id": entity}]} if kind == "spell" else {}
        return 200, page_bytes(kind, entity, views), {}, url

    def test_fetch_requests_fresh_name_urls_and_still_rejects_wrong_entity(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); tables = fixture_tables()
            tables["SpellName"] = [{"ID": "1000", "Name_lang": "Rough Bronze Bracers"},
                                   {"ID": "1001", "Name_lang": "Queen's Axe"}]
            tables["ItemSparse"][0]["Display_lang"] = "Formula: Enchant Bracer - Healing"
            snapshot(raw, with_web=False, tables=tables)
            def get(url, retries=3):
                kind, number = urlsplit(url).path.split("/")[2].split("="); entity = int(number)
                views = {"recipes": [{"id": entity}]} if kind == "spell" else {}
                if kind == "spell" and entity == 1000:
                    views["taught-by-npc"] = [{"id": 3000, "name": "Artisan Bob"}]
                if kind == "item" and entity == 2000:
                    views["reward-from-q"] = [{"id": 4000, "name": "Bob's Supplies"}]
                return 200, page_bytes(kind, entity, views), {}, url
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = get
                fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
                urls = {call.args[0] for call in transport.get.call_args_list}
            self.assertIn("https://www.wowhead.com/forever/spell=1000/rough-bronze-bracers", urls)
            self.assertIn("https://www.wowhead.com/forever/spell=1001/queens-axe", urls)
            self.assertIn("https://www.wowhead.com/forever/item=2000/formula-enchant-bracer-healing", urls)
            self.assertIn("https://www.wowhead.com/forever/item=2001", urls)
            self.assertIn("https://www.wowhead.com/forever/npc=3000/artisan-bob", urls)
            self.assertIn("https://www.wowhead.com/forever/quest=4000/bobs-supplies", urls)
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["segments"][-1]["urlRouting"], "fresh-name-slug-v1")
            self.assertTrue(all(r["url"] in urls for r in current["responses"] if r["key"].startswith("web:")))
            requested = "https://www.wowhead.com/forever/spell=1000/rough-bronze-bracers"
            wrong = "https://www.wowhead.com/forever/spell=1001/other"
            record = response_record(raw, "web:spell:1000", requested,
                lambda _: (200, page_bytes("spell", 1001, {"recipes": [{"id": 1001}]}), {}, wrong),
                entity=("spell", 1000))
            self.assertEqual(record["url"], requested)
            self.assertEqual(record["status"], "parseError")

    def test_full_refresh_retries_verified_and_historical404_without_refetching_db2(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            missing_url = "https://www.wowhead.com/forever/item=9999"
            manifest["responses"].append(response_record(raw, "web:item:9999", missing_url,
                lambda _: (404, b"Entity not found", {}, missing_url)))
            write_json(raw / "manifest.json", manifest)
            old_spell = next(r for r in manifest["responses"] if r["key"] == "web:spell:1000")
            def get(url, retries=3):
                if url == missing_url:
                    return 404, b"Entity still not found", {}, url
                return self.page_response(url, retries)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.ordinary_get") as db2, \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = get
                fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
                db2.assert_not_called()
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertIn(missing_url, urls)
            self.assertIn("https://www.wowhead.com/forever/spell=1000", urls)
            self.assertIn("https://www.wowhead.com/forever/item=2000", urls)
            self.assertEqual(len(urls), len(set(urls)))
            current = json.loads((raw / "manifest.json").read_text())
            self.assertTrue(current["requestCoverageComplete"])
            self.assertFalse(current["sourceCoverageComplete"])
            self.assertEqual(current["webRun"]["statuses"]["sourceMissing"], 1)
            self.assertEqual(current["webRun"]["notAttempted"], 0)
            spell = next(r for r in current["responses"] if r["key"] == old_spell["key"])
            self.assertEqual(spell["attemptHistory"][0]["sha256"], old_spell["sha256"])
            self.assertNotIn("attemptHistory", spell["attemptHistory"][0])
            with zipfile.ZipFile(raw.with_suffix(".zip")) as archive:
                names = set(archive.namelist())
            self.assertIn(old_spell["path"], names)
            expected = {r["path"] for r in response_evidence(current["responses"]) if "path" in r}
            self.assertEqual(names, expected | {"manifest.json"})
            facts, _ = normalize(raw, current)
            self.assertFalse(any(r["kind"] == "trainer" for r in facts["alchemy"][1000]["routes"]))
            # Historical evidence is checked, but never used as a fact fallback.
            (raw / old_spell["path"]).write_bytes(b"corrupt old evidence")
            with self.assertRaises(SourceError):
                normalize(raw, current)
            with self.assertRaises(SourceError):
                snapshot_archive(raw, root / "bad.zip")

    def test_retry_failed_includes_historical404(self):
        with temporary_directory() as temp:
            raw = Path(temp) / "raw"; raw.mkdir(); manifest = snapshot(raw)
            url = "https://www.wowhead.com/forever/item=9999"
            manifest["responses"].append(response_record(raw, "web:item:9999", url,
                lambda _: (404, b"Entity not found", {}, url)))
            write_json(raw / "manifest.json", manifest)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = self.page_response
                fetch(raw, resume=True, retry_failed=True, log=lambda *a, **k: None)
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertIn(url, urls)
            self.assertNotIn("https://www.wowhead.com/forever/spell=1000", urls)

    def test_refresh_resume_skips_same_run_completed_pages_and404(self):
        with temporary_directory() as temp:
            root = Path(temp); work = root / "raw.partial"; work.mkdir(); manifest = snapshot(work)
            run_id = "interrupted-refresh"
            manifest.update(fetchComplete=False, webRun={"id": run_id, "mode": "refresh", "targets": []})
            spell = next(r for r in manifest["responses"] if r["key"] == "web:spell:1000")
            spell.update(webRunID=run_id, attempted=True)
            url = "https://www.wowhead.com/forever/item=9999"
            missing = response_record(work, "web:item:9999", url, lambda _: (404, b"Entity not found", {}, url))
            missing["webRunID"] = run_id; manifest["responses"].append(missing)
            write_json(work / "manifest.json", manifest)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = self.page_response
                fetch(root / "raw", resume=True, refresh_web=True, log=lambda *a, **k: None)
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertNotIn("https://www.wowhead.com/forever/spell=1000", urls)
            self.assertNotIn(url, urls)
            current = json.loads((root / "raw" / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["id"], run_id)
            self.assertTrue(current["webRun"]["requestCoverageComplete"])
            self.assertEqual(current["webRun"]["statuses"]["sourceMissing"], 1)

    def test_refresh_circuit_skip_is_incomplete_and_cannot_use_old_verified_page(self):
        with temporary_directory() as temp:
            raw = Path(temp) / "raw"; raw.mkdir(); snapshot(raw)
            item_url = "https://www.wowhead.com/forever/item=2000"
            def get(url, retries=3):
                if url == item_url:
                    raise HostCircuitOpen("not sent")
                return self.page_response(url, retries)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = get
                fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
            manifest = json.loads((raw / "manifest.json").read_text())
            self.assertTrue(manifest["fetchComplete"])
            self.assertFalse(manifest["requestCoverageComplete"])
            self.assertFalse(manifest["sourceCoverageComplete"])
            self.assertEqual(manifest["webRun"]["skippedReasons"], {"hostCircuitOpen": 1})
            item = next(r for r in manifest["responses"] if r["key"] == "web:item:2000")
            self.assertEqual(item["status"], "notFetched")
            self.assertFalse(item["attempted"])
            self.assertEqual(item["attemptHistory"][0]["status"], "verified")
            facts, _ = normalize(raw, manifest)
            route = next(r for r in facts["alchemy"][1000]["routes"] if r["kind"] == "item")
            self.assertEqual(route["acquisition"]["vendors"], [])

    def test_closed_incomplete_refresh_resumes_same_round_successes_and404(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            run_id = "closed-incomplete-refresh"
            manifest.update(fetchComplete=True, requestCoverageComplete=False,
                webRun={"id": run_id, "mode": "refresh", "requestCoverageComplete": False,
                        "closedAt": "previous-close", "targets": []})
            spell = next(r for r in manifest["responses"] if r["key"] == "web:spell:1000")
            spell.update(webRunID=run_id, attempted=True)
            missing_url = "https://www.wowhead.com/forever/item=9999"
            missing = response_record(raw, "web:item:9999", missing_url,
                lambda _: (404, b"Entity not found", {}, missing_url))
            missing["webRunID"] = run_id; manifest["responses"].append(missing)
            write_json(raw / "manifest.json", manifest)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = self.page_response
                fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertNotIn(spell["url"], urls)
            self.assertNotIn(missing_url, urls)
            self.assertIn("https://www.wowhead.com/forever/item=2000", urls)
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["id"], run_id)
            self.assertTrue(current["requestCoverageComplete"])
            self.assertFalse(current["sourceCoverageComplete"])

    def test_same_round_resume_can_change_transport_and_audits_segments(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest = snapshot(raw)
            run_id = "resume-auto-as-browser"
            manifest.update(fetchComplete=True, requestCoverageComplete=False,
                webRun={"id": run_id, "mode": "refresh", "requestCoverageComplete": False,
                        "targets": [], "segments": [{"transport": "auto", "workers": 2, "interval": 1.0}]})
            spell = next(r for r in manifest["responses"] if r["key"] == "web:spell:1000")
            spell.update(webRunID=run_id, attempted=True)
            write_json(raw / "manifest.json", manifest)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = self.page_response
                transport.last_transport = "browser"
                fetch(raw, resume=True, refresh_web=True, workers=1, web_interval=2,
                      web_transport="browser", log=lambda *a, **k: None)
                cls.assert_called_once_with(interval=2, mode="browser")
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertNotIn(spell["url"], urls)
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["id"], run_id)
            segments = current["webRun"]["segments"]
            self.assertEqual(len(segments), 2)
            self.assertEqual(segments[0]["transport"], "auto")
            self.assertEqual(segments[1]["transport"], "browser")
            self.assertEqual(segments[1]["workers"], 1)
            self.assertEqual(segments[1]["interval"], 2)
            self.assertEqual(segments[1]["attemptedAtStart"], 1)
            self.assertEqual(segments[1]["attempted"], len(urls))
            self.assertIn("finishedAt", segments[1])
            attempted = [r for r in current["responses"] if r.get("attempted") and r["url"] in urls]
            self.assertTrue(all(r["transport"] == "browser" for r in attempted))

    def test_unsent_backlog_emits_one_state_transition_not_repeated_progress(self):
        with temporary_directory() as temp:
            raw = Path(temp) / "raw"; raw.mkdir(); manifest = snapshot(raw, with_web=False)
            manifest["responses"].extend({"key": f"web:item:{entity}", "status": "notFetched",
                "attempted": False, "url": f"https://www.wowhead.com/forever/item={entity}"}
                for entity in range(4000, 4100))
            write_json(raw / "manifest.json", manifest)
            def get(url, retries=3):
                if url.endswith("spell=1000"):
                    return self.page_response(url, retries)
                raise HostCircuitOpen("not sent")
            logs = []
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = get
                fetch(raw, resume=True, refresh_web=True, log=lambda value, **kwargs: logs.append(value))
            progress = [line for line in logs if line.startswith("web attempted=")]
            self.assertEqual(len(progress), 1)
            self.assertIn("state=hostCircuitOpen", progress[0])
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["attempted"], 1)
            self.assertEqual(current["webRun"]["notAttempted"], 103)
            self.assertFalse(current["requestCoverageComplete"])

    def test_supported_reference_closure_is_not_cut_at_four_levels(self):
        with temporary_directory() as temp:
            raw = Path(temp) / "raw"; raw.mkdir(); snapshot(raw, with_web=False)
            def get(url, retries=3):
                kind, entity = urlsplit(url).path.rsplit("/", 1)[1].split("="); entity = int(entity)
                if kind == "item" and entity == 2000:
                    return 200, page_bytes(kind, entity, {"reward-from-q": [{"id": 3000}]}), {}, url
                if kind == "quest" and 3000 <= entity < 3006:
                    return 200, page_bytes(kind, entity, {"reward-from-q": [{"id": entity + 1}]}), {}, url
                return self.page_response(url, retries)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = get
                fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertIn("https://www.wowhead.com/forever/quest=3006", urls)
            manifest = json.loads((raw / "manifest.json").read_text())
            self.assertTrue(manifest["requestCoverageComplete"])
            self.assertFalse(manifest["webRun"]["referenceDepthLimited"])
            self.assertFalse(any(r.get("errorCode") == "referenceDepthLimit" for r in manifest["responses"]))

    def test_interrupt_checkpoints_completed_results_and_resume_keeps_run(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); snapshot(raw, with_web=False)
            def interrupt(futures):
                yield futures[0]
                raise KeyboardInterrupt()
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls, \
                 patch("data_pipeline.professions.fetch.concurrent.futures.as_completed", side_effect=interrupt):
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = self.page_response
                with self.assertRaises(KeyboardInterrupt):
                    fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
            work = root / "raw.partial"
            manifest = json.loads((work / "manifest.json").read_text())
            self.assertFalse(manifest["fetchComplete"])
            self.assertGreater(manifest["webRun"]["attempted"], 0)
            completed = {r["url"] for r in manifest["responses"] if r.get("webRunID") == manifest["webRun"]["id"] and r.get("attempted")}
            run_id = manifest["webRun"]["id"]
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = self.page_response
                fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
                urls = {call.args[0] for call in transport.get.call_args_list}
            self.assertTrue(completed.isdisjoint(urls))
            manifest = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(manifest["webRun"]["id"], run_id)
            self.assertTrue(manifest["requestCoverageComplete"])


class CurrentHttpRetryContracts(unittest.TestCase):
    @staticmethod
    def full_snapshot(raw, blocked_code=403):
        manifest = snapshot(raw, with_web=False)
        run_id = "completed-full-current-run"
        blocked = [("spell", 1000), ("spell", 1001), ("item", 2000), ("item", 2001)]
        for kind, entity in blocked:
            url = f"https://www.wowhead.com/forever/{kind}={entity}"
            record = response_record(raw, f"web:{kind}:{entity}", url,
                lambda _, u=url: (blocked_code, b"original blocked response", {}, u))
            if entity == 2000:
                old = response_record(raw, record["key"], url,
                    lambda _, u=url: (200, page_bytes("item", 2000, {"sold-by": [{"id": 999, "cost": [[1]]}]}), {}, u),
                    entity=(kind, entity))
                record = retain_response_evidence(old, record, refresh=True)
            manifest["responses"].append(record)
        for kind, entity in [("spell", 2002), ("npc", 8888)]:
            url = f"https://www.wowhead.com/forever/{kind}={entity}"
            manifest["responses"].append(response_record(raw, f"web:{kind}:{entity}", url,
                lambda u: RefreshRunContracts.page_response(u), entity=(kind, entity)))
        missing_url = "https://www.wowhead.com/forever/item=9999"
        manifest["responses"].append(response_record(raw, "web:item:9999", missing_url,
            lambda u: (404, b"Entity not found", {}, u)))
        malformed_url = "https://www.wowhead.com/forever/spell=16001"
        manifest["responses"].append(response_record(raw, "web:spell:16001", malformed_url,
            lambda u: (200, page_bytes("spell", 16001, {}), {}, u), entity=("spell", 16001)))
        other_code = 429 if blocked_code != 429 else 202
        other_url = "https://www.wowhead.com/forever/item=7777"
        manifest["responses"].append(response_record(raw, "web:item:7777", other_url,
            lambda u: (other_code, b"other blocked code", {}, u)))
        # A same-code record whose top-level status is not sourceBlocked must
        # not be selected, even when its recorded HTTP number happens to match.
        excluded_url = "https://www.wowhead.com/forever/item=7778"
        excluded = response_record(raw, "web:item:7778", excluded_url,
            lambda u: (blocked_code, b"excluded parse status", {}, u))
        excluded["status"] = "parseError"; manifest["responses"].append(excluded)
        web = [record for record in manifest["responses"] if record["key"].startswith("web:")]
        for record in web:
            record.update(webRunID=run_id, attempted=True)
        keys = sorted(record["key"] for record in web)
        manifest.update(fetchComplete=True, requestCoverageComplete=True, sourceCoverageComplete=False,
            webRun={"id": run_id, "mode": "refresh", "targets": keys,
                    "targetCount": len(keys), "attempted": len(keys), "requestCoverageComplete": True,
                    "segments": [{"transport": "browser", "workers": 1, "interval": 3.0}]})
        write_json(raw / "manifest.json", manifest)
        snapshot_archive(raw, raw.with_suffix(".zip"))
        return manifest, {f"web:{kind}:{entity}" for kind, entity in blocked}

    def test_targeted_retry_only_selects_four_blocked_records_and_preserves_evidence(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); before, selected = self.full_snapshot(raw)
            originals = {record["key"]: copy.deepcopy(record) for record in before["responses"]}
            bytes_before = {record["path"]: (raw / record["path"]).read_bytes()
                            for record in response_evidence(before["responses"]) if "path" in record}
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls, \
                 patch("data_pipeline.professions.fetch.ordinary_get") as db2:
                transport = cls.return_value.__enter__.return_value
                transport.get.side_effect = RefreshRunContracts.page_response
                fetch(raw, resume=True, retry_current_http=403, web_transport="browser", log=lambda *a, **k: None)
                called = {"web:" + urlsplit(call.args[0]).path.split("/")[2].replace("=", ":")
                          for call in transport.get.call_args_list}
                db2.assert_not_called()
            self.assertEqual(called, selected)
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["id"], before["webRun"]["id"])
            self.assertEqual(current["webRun"]["attempted"], before["webRun"]["attempted"])
            self.assertTrue(current["requestCoverageComplete"])
            plan = current["webRun"]["currentHttpRetry"]
            self.assertEqual(set(plan["selectedKeys"]), selected)
            self.assertEqual(set(plan["completedKeys"]), selected)
            self.assertTrue(plan["complete"])
            for record in current["responses"]:
                if record["key"] not in selected:
                    self.assertEqual(record, originals[record["key"]])
                else:
                    self.assertEqual(record["status"], "verified")
                    self.assertEqual(record["attemptHistory"][-1]["sha256"], originals[record["key"]]["sha256"])
                    self.assertTrue(all("attemptHistory" not in h for h in record["attemptHistory"]))
            for path, data in bytes_before.items():
                self.assertEqual((raw / path).read_bytes(), data)
            with zipfile.ZipFile(raw.with_suffix(".zip")) as archive:
                self.assertTrue(set(bytes_before).issubset(archive.namelist()))
            lua, report = root / "source.lua", root / "report.json"
            build(raw, lua, report); build(raw.with_suffix(".zip"), lua, report, check=True)

    def test_allowed_codes_are403429202_and_other_scopes_are_rejected(self):
        for code in (429, 202):
            with self.subTest(code=code), temporary_directory() as temp:
                raw = Path(temp) / "raw"; raw.mkdir(); _, selected = self.full_snapshot(raw, code)
                with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                     patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                    cls.return_value.__enter__.return_value.get.side_effect = RefreshRunContracts.page_response
                    fetch(raw, resume=True, retry_current_http=code, log=lambda *a, **k: None)
                current = json.loads((raw / "manifest.json").read_text())
                self.assertEqual(set(current["webRun"]["currentHttpRetry"]["completedKeys"]), selected)
        for options in ({"retry_current_http": 404, "resume": True},
                        {"retry_current_http": 200, "resume": True},
                        {"retry_current_http": 403, "resume": False},
                        {"retry_current_http": 403, "resume": True, "refresh_web": True},
                        {"retry_current_http": 403, "resume": True, "retry_failed": True}):
            with self.subTest(options=options), patch("data_pipeline.professions.fetch.latest") as latest_probe:
                with self.assertRaises(SourceError):
                    fetch(Path("not-created"), **options)
                latest_probe.assert_not_called()

    def test_latest_drift_and_incomplete_full_input_leave_original_snapshot_unchanged(self):
        scenarios = [dict(BUILD, version="1.60.1.70002"), dict(BUILD, build_config="b" * 32), None]
        for changed in scenarios:
            with self.subTest(changed=changed), temporary_directory() as temp:
                root = Path(temp); raw = root / "raw"; raw.mkdir(); manifest, _ = self.full_snapshot(raw)
                if changed is None:
                    manifest["requestCoverageComplete"] = False
                    manifest["webRun"]["requestCoverageComplete"] = False
                    write_json(raw / "manifest.json", manifest)
                original_manifest = (raw / "manifest.json").read_bytes()
                original_archive = raw.with_suffix(".zip").read_bytes()
                with patch("data_pipeline.professions.fetch.latest", return_value=changed or BUILD), \
                     patch("data_pipeline.professions.fetch.WowheadTransport") as transport:
                    with self.assertRaises(SourceError):
                        fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
                    transport.assert_not_called()
                self.assertTrue(raw.exists()); self.assertFalse((root / "raw.partial").exists())
                self.assertEqual((raw / "manifest.json").read_bytes(), original_manifest)
                self.assertEqual(raw.with_suffix(".zip").read_bytes(), original_archive)

    def test_targeted_circuit_keeps_full_coverage_and_resumes_only_unattempted_selection(self):
        with temporary_directory() as temp:
            raw = Path(temp) / "raw"; raw.mkdir(); before, selected = self.full_snapshot(raw)
            def get(url, retries=3):
                if "/spell=" in url:
                    return 403, b"still blocked", {}, url
                raise HostCircuitOpen("not sent")
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                cls.return_value.__enter__.return_value.get.side_effect = get
                fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
            first = json.loads((raw / "manifest.json").read_text())
            plan = first["webRun"]["currentHttpRetry"]
            self.assertFalse(plan["complete"])
            self.assertTrue(first["requestCoverageComplete"])
            self.assertEqual(first["webRun"]["attempted"], before["webRun"]["attempted"])
            unattempted = selected - set(plan["completedKeys"])
            self.assertEqual(unattempted, {"web:item:2000", "web:item:2001"})
            for record in first["responses"]:
                if record["key"] in unattempted:
                    self.assertEqual(record["httpStatus"], 403)
                    self.assertEqual(record["status"], "sourceBlocked")
                    self.assertFalse(record["lastAttempt"]["attempted"])
            operation_id = plan["id"]
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = RefreshRunContracts.page_response
                fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
                called = {"web:" + urlsplit(call.args[0]).path.split("/")[2].replace("=", ":")
                          for call in transport.get.call_args_list}
            self.assertEqual(called, unattempted)
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["currentHttpRetry"]["id"], operation_id)
            self.assertEqual(current["webRun"]["id"], before["webRun"]["id"])
            self.assertTrue(current["webRun"]["currentHttpRetry"]["complete"])
            self.assertTrue(current["requestCoverageComplete"])

    def test_new_links_are_first_fetched_without_regrabbing_existing_success(self):
        with temporary_directory() as temp:
            raw = Path(temp) / "raw"; raw.mkdir(); before, selected = self.full_snapshot(raw)
            def get(url, retries=3):
                kind, number = urlsplit(url).path.split("/")[2].split("="); entity = int(number)
                views = {"recipes": [{"id": entity}]} if kind == "spell" else {}
                if kind == "spell":
                    views["taught-by-npc"] = [{"id": 8888, "name": "Existing Trainer"},
                                              {"id": 3333, "name": "New Trainer"}]
                return 200, page_bytes(kind, entity, views), {}, url
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value; transport.get.side_effect = get
                fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertEqual(len(urls), len(selected) + 1)
            self.assertIn("https://www.wowhead.com/forever/npc=3333/new-trainer", urls)
            self.assertFalse(any("npc=8888" in url for url in urls))
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["currentHttpRetry"]["additionalKeys"], ["web:npc:3333"])
            self.assertEqual(current["webRun"]["targetCount"], before["webRun"]["targetCount"] + 1)
            self.assertTrue(current["requestCoverageComplete"])
            self.assertTrue(current["webRun"]["currentHttpRetry"]["complete"])

    def test_completed_targeted_requests_resume_only_final_latest_after_probe_failure(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); before, selected = self.full_snapshot(raw)
            with patch("data_pipeline.professions.fetch.latest", side_effect=[BUILD, RuntimeError("final latest unavailable")]), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                cls.return_value.__enter__.return_value.get.side_effect = RefreshRunContracts.page_response
                with self.assertRaisesRegex(RuntimeError, "final latest unavailable"):
                    fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
            work = root / "raw.partial"
            pending = json.loads((work / "manifest.json").read_text())
            self.assertFalse(pending["fetchComplete"])
            self.assertTrue(pending["webRun"]["currentHttpRetry"]["complete"])
            operation_id = pending["webRun"]["currentHttpRetry"]["id"]
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                transport = cls.return_value.__enter__.return_value
                fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
                transport.get.assert_not_called()
            current = json.loads((raw / "manifest.json").read_text())
            self.assertTrue(current["fetchComplete"])
            self.assertTrue(current["requestCoverageComplete"])
            self.assertEqual(current["webRun"]["id"], before["webRun"]["id"])
            self.assertEqual(current["webRun"]["currentHttpRetry"]["id"], operation_id)
            self.assertEqual(set(current["webRun"]["currentHttpRetry"]["completedKeys"]), selected)
            self.assertEqual(current["webRun"]["segments"][-1]["attempted"], 0)

    def test_targeted_closed_partial_resumes_publication_without_repeating_http(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); before, _ = self.full_snapshot(raw)
            work = root / "raw.partial"
            rename = Path.rename
            def fail_publication(path, target):
                if path == work and target == raw:
                    raise OSError("publication interrupted")
                return rename(path, target)
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls, \
                 patch.object(Path, "rename", fail_publication):
                cls.return_value.__enter__.return_value.get.side_effect = RefreshRunContracts.page_response
                with self.assertRaisesRegex(OSError, "publication interrupted"):
                    fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
            pending = json.loads((work / "manifest.json").read_text())
            self.assertTrue(pending["fetchComplete"])
            self.assertTrue(pending["webRun"]["currentHttpRetry"]["complete"])
            operation_id = pending["webRun"]["currentHttpRetry"]["id"]
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
                cls.return_value.__enter__.return_value.get.assert_not_called()
            current = json.loads((raw / "manifest.json").read_text())
            self.assertEqual(current["webRun"]["id"], before["webRun"]["id"])
            self.assertEqual(current["webRun"]["currentHttpRetry"]["id"], operation_id)
            self.assertTrue(raw.with_suffix(".zip").exists())

    def test_closed_refresh_partial_finalizes_but_closed_output_starts_new_explicit_round(self):
        for existing_partial in (True, False):
            with self.subTest(existing_partial=existing_partial), temporary_directory() as temp:
                root = Path(temp); raw = root / "raw"; raw.mkdir(); before, _ = self.full_snapshot(raw)
                if existing_partial:
                    raw.rename(root / "raw.partial")
                with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                     patch("data_pipeline.professions.fetch.WowheadTransport") as cls:
                    transport = cls.return_value.__enter__.return_value
                    transport.get.side_effect = RefreshRunContracts.page_response
                    fetch(raw, resume=True, refresh_web=True, log=lambda *a, **k: None)
                    if existing_partial:
                        transport.get.assert_not_called()
                    else:
                        self.assertGreater(transport.get.call_count, 0)
                current = json.loads((raw / "manifest.json").read_text())
                if existing_partial:
                    self.assertEqual(current["webRun"]["id"], before["webRun"]["id"])
                    self.assertEqual(current["webRun"]["segments"][-1]["attempted"], 0)
                else:
                    self.assertNotEqual(current["webRun"]["id"], before["webRun"]["id"])

    def test_archive_failure_after_rename_is_repaired_offline_without_fetch(self):
        with temporary_directory() as temp:
            root = Path(temp); raw = root / "raw"; raw.mkdir(); self.full_snapshot(raw)
            old_archive = raw.with_suffix(".zip").read_bytes()
            with patch("data_pipeline.professions.fetch.latest", return_value=BUILD), \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as cls, \
                 patch("data_pipeline.professions.fetch.snapshot_archive", side_effect=OSError("archive interrupted")):
                cls.return_value.__enter__.return_value.get.side_effect = RefreshRunContracts.page_response
                with self.assertRaisesRegex(OSError, "archive interrupted"):
                    fetch(raw, resume=True, retry_current_http=403, log=lambda *a, **k: None)
            self.assertTrue(raw.exists())
            self.assertTrue(json.loads((raw / "manifest.json").read_text())["fetchComplete"])
            self.assertEqual(raw.with_suffix(".zip").read_bytes(), old_archive)
            with patch("data_pipeline.professions.fetch.latest") as latest_probe, \
                 patch("data_pipeline.professions.fetch.WowheadTransport") as transport:
                snapshot_archive(raw, raw.with_suffix(".zip"))
                latest_probe.assert_not_called(); transport.assert_not_called()
            with zipfile.ZipFile(raw.with_suffix(".zip")) as archive:
                self.assertEqual(archive.read("manifest.json"), (raw / "manifest.json").read_bytes())


class BrowserOwnerContracts(unittest.TestCase):
    def browser_fixture(self, scenarios, interrupted=False, advance_during_body=False, body_gate=None):
        events = []
        def event(name):
            events.append((name, threading.get_ident()))
        class Page:
            main_frame = object()
            advance = advance_during_body
            def on(self, name, handler):
                event("on"); self.handler = handler
            def emit(self):
                status, body, url = self.pending.pop(0)
                response = SimpleNamespace(status=status, url=url,
                    request=SimpleNamespace(is_navigation_request=lambda: True, frame=self.main_frame))
                def response_body():
                    event("body")
                    if body_gate is not None and status == 200:
                        started, release = body_gate
                        started.set()
                        if not release.wait(2):
                            raise RuntimeError("test did not finish the main response body")
                    if self.advance and self.pending:
                        self.advance = False
                        self.emit()
                    return body
                response.body = response_body
                response.all_headers = lambda: {"content-type": "text/html"}
                self.handler(response)
            def goto(self, url, **kwargs):
                event("goto:" + str(kwargs.get("wait_until")))
                self.pending = list(scenarios[url]); self.emit()
                if interrupted:
                    raise RuntimeError("navigation replaced during challenge")
            def wait_for_timeout(self, delay):
                event("wait")
                if self.pending:
                    self.emit()
        page = Page()
        def new_page():
            event("page"); return page
        def context_close():
            event("context.close")
        context = SimpleNamespace(new_page=new_page, close=context_close)
        context_options = []
        def new_context(**kwargs):
            event("context"); context_options.append(kwargs); return context
        def browser_close():
            event("browser.close")
        browser = SimpleNamespace(version="156.0.8078.4", new_context=new_context, close=browser_close)
        def launch(**kwargs):
            event("launch"); return browser
        def stop():
            event("stop")
        playwright = SimpleNamespace(chromium=SimpleNamespace(launch=launch), stop=stop)
        def start():
            event("start"); return playwright
        def factory():
            event("factory"); return SimpleNamespace(start=start)
        return factory, events, context_options

    def test_native_navigation_and_cleanup_have_one_owner_thread(self):
        spell = "https://www.wowhead.com/forever/spell=2671"
        item = "https://www.wowhead.com/forever/item=5577"
        factory, events, options = self.browser_fixture({
            spell: [(202, b"challenge", spell), (301, b"", spell), (200, b"recipe", spell + "/rough-bronze-bracers")],
            item: [(404, b"Entity not found", item)]}, interrupted=True)
        owner = BrowserTransport(factory=factory)
        with owner, ThreadPoolExecutor(max_workers=2) as callers:
            results = list(callers.map(owner.get, [spell, item]))
        self.assertEqual([r[0] for r in results], [200, 404])
        self.assertEqual(results[0][1], b"recipe")
        self.assertEqual(len({thread for _, thread in events}), 1)
        self.assertNotEqual(events[0][1], threading.get_ident())
        self.assertEqual([name for name, _ in events].count("launch"), 1)
        self.assertEqual([name for name, _ in events].count("context"), 1)
        self.assertEqual([name for name, _ in events][-3:], ["context.close", "browser.close", "stop"])
        self.assertIn("Chrome/156.0.8078.4", options[0]["user_agent"])
        self.assertNotIn("146", options[0]["user_agent"])
        self.assertEqual([name for name, _ in events].count("goto:commit"), 2)
        owner.close()
        with self.assertRaises(BrowserClosed):
            owner.get(spell)

    def test_interactive_captcha_is_returned_without_attempting_interaction(self):
        url = "https://www.wowhead.com/forever/spell=2671"
        factory, events, _ = self.browser_fixture({url: [(202, b'<div class="g-recaptcha">', url)]})
        with BrowserTransport(factory=factory) as owner:
            self.assertEqual(owner.get(url)[0], 202)
        self.assertNotIn("wait", [name for name, _ in events])

    def test_body_event_pump_cannot_accept_an_outdated_main_document(self):
        url = "https://www.wowhead.com/forever/spell=2671"
        final = url + "/rough-bronze-bracers"
        factory, _, _ = self.browser_fixture({url: [
            (200, b"old document", url), (200, b"final recipe", final)]}, advance_during_body=True)
        with BrowserTransport(factory=factory) as owner:
            result = owner.get(url)
        self.assertEqual(result[1], b"final recipe")
        self.assertEqual(result[3], final)

    def test_commit_waits_for_complete200_body_and_not_for_dom_lifecycle(self):
        url = "https://www.wowhead.com/forever/spell=2671"
        body = b"<html><script>complete source payload</script></html>"
        started, release = threading.Event(), threading.Event()
        factory, events, _ = self.browser_fixture({url: [(200, body, url)]}, body_gate=(started, release))
        with BrowserTransport(factory=factory) as owner, ThreadPoolExecutor(max_workers=1) as caller:
            future = caller.submit(owner.get, url)
            try:
                self.assertTrue(started.wait(2), "main response body was not read")
                self.assertFalse(future.done(), "headers/commit were mistaken for a completed200 document")
            finally:
                release.set()
            result = future.result(timeout=2)
        self.assertEqual(result[0], 200)
        self.assertEqual(result[1], body)
        self.assertIn("goto:commit", [name for name, _ in events])
        self.assertNotIn("goto:domcontentloaded", [name for name, _ in events])

    def test_commit202_keeps_executing_until_final_navigation200(self):
        url = "https://www.wowhead.com/forever/spell=2671"
        final = url + "/rough-bronze-bracers"
        factory, events, _ = self.browser_fixture({url: [
            (202, b"window.gokuProps={};", url), (301, b"redirect", url), (200, b"final document", final)]})
        with BrowserTransport(factory=factory) as owner:
            result = owner.get(url)
        self.assertEqual(result, (200, b"final document", {"content-type": "text/html"}, final))
        names = [name for name, _ in events]
        self.assertIn("goto:commit", names)
        self.assertGreaterEqual(names.count("wait"), 2)

    def test_partial_startup_stops_playwright_on_the_owner_thread(self):
        events = []
        def launch(**kwargs):
            events.append(("launch", threading.get_ident()))
            raise RuntimeError("Chromium unavailable")
        def stop():
            events.append(("stop", threading.get_ident()))
        def factory():
            events.append(("factory", threading.get_ident()))
            return SimpleNamespace(start=lambda: SimpleNamespace(
                chromium=SimpleNamespace(launch=launch), stop=stop))
        with BrowserTransport(factory=factory) as owner:
            with self.assertRaisesRegex(RuntimeError, "Chromium unavailable"):
                owner.get("https://www.wowhead.com/forever/spell=2671")
        self.assertEqual([name for name, _ in events], ["factory", "launch", "stop"])
        self.assertEqual(len({thread for _, thread in events}), 1)
        self.assertNotEqual(events[0][1], threading.get_ident())


if __name__ == "__main__":
    unittest.main()
