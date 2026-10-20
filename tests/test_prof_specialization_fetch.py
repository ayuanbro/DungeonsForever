"""Offline fixtures for the bounded Wowhead specialization reader."""

from hashlib import sha256
from email.utils import formatdate
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest import mock
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "df-data-pipeline/_temp/fc_specialization_fetch.py"
sys.path.insert(0, str(SCRIPT.parent))
import fc_pipeline_common as common
SPEC = importlib.util.spec_from_file_location("fc_specialization_fetch", SCRIPT)
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)

SKILL_URL = fetch.ORIGIN + "/forever/skill%3D202/engineering"
SPELL_URL = fetch.ORIGIN + "/forever/spell%3D12716/goblin-mortar"
STAMP = 1792500000.0


def page(kind="skill", entity_id=202, rows=None, npc_ids=None, env=16,
         recipe_tab=True, patch="1.60.1", taught_ids=None):
    meta = {
        "page": "%s%%3D%s" % (kind, entity_id),
        "dataEnv": {"env": env, "tree": env, "versions": {"16": patch}},
        "serverTime": "2026-10-20T14:00:00Z",
        "activeDbChanged": {"16": 1792500090},
    }
    lists = []
    if kind == "skill":
        if recipe_tab:
            lists.append("new Listview({template:'spell', id:\"recipes\", "
                         "visibleCols:['source'], data:%s});" % json.dumps(rows or []))
        else:
            lists.append("new Listview({template:'spell',id:'spells',data:[]});")
        # Deliberately conflicting item requirements must never be read.
        lists.append("new Listview({template:'item',id:'recipe-items',"
                     "data:[{\"id\":10646,\"reqspell\":999,\"specialization\":999}]});")
    elif kind == "spell" and npc_ids is not None:
        lists.append("new Listview({template:'npc',id:'taught-by-npc',data:%s});" %
                     json.dumps([{"id": key, "name": "Trainer"} for key in npc_ids]))
    elif kind == "item" and taught_ids is not None:
        lists.append("new Listview({template:'spell',id:'teaches',data:%s});" %
                     json.dumps([{"id": key, "name": "Recipe"} for key in taught_ids]))
    return (
        '<html><script type="application/json" id="data.pageMeta">' +
        json.dumps(meta) + "</script><script>" + "\n".join(lists) +
        '</script><p>Requires <a href="/forever/spell=999">Wrong item condition</a></p></html>'
    )


def recipe(spell=12760, ability=20222, source=(6,), name="Goblin Sapper Charge"):
    result = {"id": spell, "name": name, "skill": [202], "learnedat": 205,
              "creates": [10646, 1, 1], "reagents": [[10505, 3]], "cat": 11}
    if ability is not None:
        result["specialization"] = ability
    if source is not None:
        result["source"] = list(source)
    return result


def response(body="", status=200, headers=None, url=None):
    value = {"status": status, "body": body.encode("utf-8"), "headers": headers or {}}
    if url:
        value["url"] = url
    return value


class SpecializationFetchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="df-spec-fetch-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.cache = self.directory / "cache"
        self.policy = self.directory / "policy"
        self.clock = STAMP
        for patcher in (
            mock.patch.object(common, 'REPO', self.directory),
            mock.patch.object(fetch, "POLICY_DIR", self.policy),
            mock.patch.object(fetch, "_now", side_effect=lambda: self.clock),
            mock.patch.object(fetch.time, "sleep", side_effect=self.sleep),
            mock.patch.object(fetch.random, "uniform", return_value=0),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.transport = mock.patch.object(fetch, "_transport",
                                           side_effect=AssertionError("Unexpected network request"))
        self.mock_transport = self.transport.start()
        self.addCleanup(self.transport.stop)

    def sleep(self, seconds):
        self.clock += seconds

    def collect(self, **kwargs):
        return fetch.collect_trainers(self.cache, skills=[202], **kwargs)

    def test_cache_outside_repository_is_rejected_before_network(self):
        outside = self.directory.parent / (self.directory.name + '-outside')
        with self.assertRaises(ValueError):
            fetch.collect_trainers(outside, skills=[202])
        self.mock_transport.assert_not_called()
        self.assertFalse(outside.exists())

    def cached(self, url, html, age_days=0, **changes):
        value = {
            "version": fetch.CACHE_VERSION, "url": url, "html": html,
            "sha256": sha256(html.encode("utf-8")).hexdigest(),
            "fetched_at": fetch._iso(self.clock - age_days * 86400),
            "checked_at": fetch._iso(self.clock - age_days * 86400),
            "etag": '"fixture"', "last_modified": "Tue, 20 Oct 2026 10:00:00 GMT",
        }
        value.update(changes)
        path = fetch._Client(self.cache, True, False, 7)._cache_path(url)
        fetch._atomic_json(path, value)
        return path

    def robots(self, text="User-agent: *\nDisallow:\n"):
        fetch._atomic_json(self.policy / "robots.json", {
            "checked_at": self.clock, "body": text,
        })

    def test_balanced_json_preserves_strings_and_nested_arrays(self):
        row = recipe(name='Goblin "test ] }, [ \\\\ " recipe')
        parsed = fetch.parse_page(page(rows=[row]), "skill", 202)
        self.assertEqual(parsed["recipes"], [row])
        self.assertEqual(parsed["patch"], "1.60.1")
        self.assertEqual(parsed["build"], "")

    def test_wrong_environment_identity_and_bad_ids_are_rejected(self):
        for html in (
            page(rows=[recipe()], env=4),
            page(rows=[recipe()], patch="1.15.8"),
            page(rows=[recipe()], patch="1.61.0"),
            page(entity_id=164, rows=[recipe()]),
            page(rows=[recipe(spell=True)]),
            page(rows=[recipe(ability=-1)]),
            page(rows=[recipe(), recipe()]),
            page(rows=[dict(recipe(), skill=[164])]),
        ):
            with self.subTest(html=html[:100]), self.assertRaises(fetch.ValidationError):
                fetch.parse_page(html, "skill", 202)

    def test_javascript_data_is_not_executed(self):
        html = page(rows=[]).replace(
            "data:[]", "data:JSON.parse(window.secret)", 1)
        with self.assertRaises(fetch.ValidationError):
            fetch.parse_page(html, "skill", 202)

    def test_missing_recipe_tab_requires_parsed_spells_tab(self):
        self.assertEqual(fetch.parse_page(page(recipe_tab=False), "skill", 202)["recipes"], [])
        html = page(recipe_tab=False).replace("id:'spells'", "id:'comments'")
        with self.assertRaises(fetch.ValidationError):
            fetch.parse_page(html, "skill", 202)

    def test_item_page_only_accepts_explicit_teaches_listview(self):
        parsed = fetch.parse_page(
            page("item", 251426, taught_ids=[1252323]), "item", 251426)
        self.assertTrue(parsed["teaches_list_present"])
        self.assertEqual(parsed["taught_spell_ids"], [1252323])
        absent = fetch.parse_page(page("item", 251426), "item", 251426)
        self.assertFalse(absent["teaches_list_present"])
        self.assertEqual(absent["taught_spell_ids"], [])
        with self.assertRaises(fetch.ValidationError):
            fetch.parse_page(page("item", 251426, taught_ids=[True]), "item", 251426)
        with self.assertRaises(fetch.ValidationError):
            fetch.parse_page(page("item", 251427, taught_ids=[1252323]), "item", 251426)

    def test_validated_item_cache_keeps_hash_patch_and_taught_spell_ids(self):
        url = fetch.ORIGIN + "/forever/item%3D251426/plans-prefects-waistguard"
        html = page("item", 251426, taught_ids=[1252323])
        self.cached(url, html)
        parsed, source = fetch._Client(self.cache, True, False, 7).page(url, "item", 251426)
        self.assertEqual(parsed["taught_spell_ids"], [1252323])
        self.assertEqual(source["Kind"], "item")
        self.assertEqual(source["SourceSHA256"], sha256(html.encode("utf-8")).hexdigest())
        self.assertEqual(source["SourcePatch"], "1.60.1")
        self.assertEqual(source["SourceBuild"], "")
        self.assertEqual(source["RowCount"], 1)
        self.mock_transport.assert_not_called()

    def test_item_spell_modifiers_and_flavor_text_are_not_teaching_evidence(self):
        # Structure observed on Forever item 251426. A modifier can reference a
        # recipe spell while the item effect still is not a learning effect.
        html = page("item", 251426).replace("</html>", """
            <p>"Teaches you how to craft Prefect's Waistguard."</p>
            <script>new Listview({template:'item',id:'creates',data:[{}]});</script>
            <script type="application/json" id="data.page.wow.item.tooltip">
            {"id":251426,"spellModifiers":[402265,1252323]}
            </script></html>""")
        parsed = fetch.parse_page(html, "item", 251426)
        self.assertFalse(parsed["teaches_list_present"])
        self.assertEqual(parsed["taught_spell_ids"], [])

    def test_offline_keeps_unknowns_and_never_infers_from_names_or_items(self):
        self.cached(SKILL_URL, page(rows=[
            recipe(), recipe(12906, 20219, name="Gnomish Battle Chicken"),
            recipe(100, None, name="Goblin Engineer Uncertain"),
            recipe(101, 0, name="Gnomish Engineer Uncertain"),
            recipe(102, 20222, source=(2,), name="Other recipe"),
        ]), age_days=50)
        result = self.collect(offline=True)
        rows = {row["RecipeSpellID"]: row for row in result["records"]}
        self.assertEqual(rows[12760]["RequiredAbility"], 20222)
        self.assertEqual(rows[12906]["RequiredAbility"], 20219)
        for key in (100, 101, 102):
            self.assertEqual(rows[key]["Status"], "pending")
        self.assertFalse(rows[102]["TrainerObserved"])
        self.assertEqual(rows[102]["RequiredAbility"], 20222)
        self.assertEqual(result["coverage"]["supplemental_spell_pages"], 0)
        self.assertEqual(rows[12760]["SourceBuild"], "")
        self.assertEqual(rows[12760]["NPCIDs"], [])
        self.mock_transport.assert_not_called()

    def test_only_specialization_without_source_gets_supplemental_npc_page(self):
        self.cached(SKILL_URL, page(rows=[
            recipe(12716, source=None, name="Goblin Mortar"),
            recipe(200, source=(2,), name="Drop"),
            recipe(201, ability=None, source=None, name="Goblin Name Alone"),
        ]))
        self.cached(SPELL_URL, page("spell", 12716, npc_ids=[8126, 8738, 8126]))
        result = self.collect(offline=True)
        rows = {row["RecipeSpellID"]: row for row in result["records"]}
        self.assertEqual(set(rows), {12716, 200})
        self.assertEqual(rows[12716]["Status"], "confirmed")
        self.assertEqual(rows[12716]["NPCIDs"], [8126, 8738])
        self.assertEqual(rows[12716]["SourceURL"], SKILL_URL)
        self.assertEqual(rows[12716]["TrainerSourceURL"], SPELL_URL)
        self.assertEqual(rows[12716]["TrainerSourcePatch"], "1.60.1")
        self.assertEqual(rows[12716]["TrainerSourceBuild"], "")
        self.assertEqual(rows[12716]["SourceBuild"], "")
        self.assertEqual(result["coverage"]["supplemental_spell_pages"], 1)

    def test_different_patch_supplemental_trainer_evidence_remains_pending(self):
        self.cached(SKILL_URL, page(rows=[recipe(12716, source=None, name="Goblin Mortar")]))
        self.cached(SPELL_URL, page("spell", 12716, npc_ids=[8126], patch="1.60.2"))
        result = self.collect(offline=True)
        row = result["records"][0]
        self.assertEqual(row["Status"], "pending")
        self.assertEqual(row["Reason"], "trainer_source_patch_mismatch")
        self.assertEqual(row["SourcePatch"], "1.60.1")
        self.assertEqual(row["TrainerSourcePatch"], "1.60.2")
        self.assertEqual(row["SourceBuild"], "")
        self.assertEqual(row["TrainerSourceBuild"], "")
        self.assertEqual(row["NPCIDs"], [8126])
        self.assertTrue(row["TrainerObserved"])
        self.assertEqual(row["RequiredAbility"], 20222)
        self.assertEqual(result["coverage"]["confirmed_records"], 0)
        self.assertEqual(result["coverage"]["pending_records"], 1)

    def test_offline_missing_page_and_missing_trainer_cache_stay_pending(self):
        empty = self.collect(offline=True)
        self.assertEqual(empty["records"], [])
        self.assertEqual(empty["coverage"]["missing_pages"], [SKILL_URL])
        self.cached(SKILL_URL, page(rows=[recipe(12716, source=None, name="Goblin Mortar")]))
        result = self.collect(offline=True)
        self.assertEqual(result["records"][0]["Status"], "pending")
        self.assertEqual(result["coverage"]["missing_pages"], [SPELL_URL])
        self.assertEqual(result["records"][0]["Reason"], "trainer_page_cache_missing")
        self.mock_transport.assert_not_called()

    def test_empty_taught_by_does_not_establish_no_requirement(self):
        self.cached(SKILL_URL, page(rows=[recipe(12716, source=None, name="Goblin Mortar")]))
        self.cached(SPELL_URL, page("spell", 12716, npc_ids=[]))
        result = self.collect(offline=True)
        self.assertEqual(result["records"][0]["Status"], "pending")
        self.assertEqual(result["records"][0]["RequiredAbility"], 20222)

    def test_hash_corruption_is_missing_offline_and_never_accepted(self):
        self.cached(SKILL_URL, page(rows=[recipe()]), sha256="bad")
        result = self.collect(offline=True)
        self.assertEqual(result["coverage"]["missing_pages"], [SKILL_URL])

    def test_fresh_cache_avoids_all_network_including_robots(self):
        self.cached(SKILL_URL, page(rows=[recipe()]))
        result = self.collect()
        self.assertEqual(result["sources"][0]["Status"], "fresh")
        self.mock_transport.assert_not_called()

    def test_network_request_reads_actual_user_agent_policy_then_validates_page(self):
        self.mock_transport.side_effect = [
            response("User-agent: *\nDisallow:\n"),
            response(page(rows=[recipe()]), headers={"etag": '"v1"'}),
        ]
        result = self.collect()
        calls = self.mock_transport.call_args_list
        self.assertEqual(calls[0].args[0], fetch.ORIGIN + "/robots.txt")
        self.assertEqual(calls[1].args[0], SKILL_URL)
        self.assertTrue(all(call.args[1]["User-Agent"] == fetch.USER_AGENT for call in calls))
        self.assertGreaterEqual(self.clock - STAMP, 3)
        self.assertEqual(result["records"][0]["Status"], "confirmed")
        self.assertEqual(result["sources"][0]["Status"], "fetched")
        self.assertTrue(fetch._Client(self.cache, True, False, 7)._cache_path(SKILL_URL).exists())

    def test_robots_denial_is_not_retried_with_another_identity_or_url(self):
        self.mock_transport.side_effect = [
            response("User-agent: DungeonsForeverDataPipeline\nDisallow: /forever/\n"
                     "User-agent: *\nDisallow:\n"),
        ]
        with self.assertRaisesRegex(fetch.FetchError, "robots.txt disallows"):
            self.collect()
        self.assertEqual(self.mock_transport.call_count, 1)
        self.assertFalse(self.cache.exists())

    def test_revalidation_uses_conditional_headers_and_preserves_content_fetch_date(self):
        path = self.cached(SKILL_URL, page(rows=[recipe()]), age_days=8)
        before = fetch._read_json(path)
        self.robots()
        self.mock_transport.side_effect = [response(status=304)]
        result = self.collect()
        headers = self.mock_transport.call_args.args[1]
        self.assertEqual(headers["If-None-Match"], '"fixture"')
        self.assertEqual(headers["If-Modified-Since"], before["last_modified"])
        after = fetch._read_json(path)
        self.assertEqual(after["fetched_at"], before["fetched_at"])
        self.assertGreater(after["checked_at"], before["checked_at"])
        self.assertEqual(result["sources"][0]["Status"], "revalidated")

    def test_429_sets_persistent_shared_cooldown_and_preserves_valid_cache(self):
        path = self.cached(SKILL_URL, page(rows=[recipe()]), age_days=8)
        before = path.read_bytes()
        self.robots()
        self.mock_transport.side_effect = [response(status=429, headers={"retry-after": "3600"})]
        with self.assertRaises(fetch.CooldownError):
            self.collect()
        self.assertEqual(path.read_bytes(), before)
        state = fetch._read_json(self.policy / "cooldown.json")
        self.assertEqual(state["until"], self.clock + 3600)
        with self.assertRaises(fetch.CooldownError):
            fetch.collect_trainers(self.directory / "other-cache", skills=[202])
        self.assertEqual(self.mock_transport.call_count, 1)

    def test_403_202_and_challenge_have_default_cooldown_without_retry(self):
        for failed in (
            response(status=403), response(status=202),
            response("<html>Verify you are human</html>"),
            response("<html>Verify that you're not a robot</html>"),
            response("<html>Verify that you’re not a robot</html>"),
            response("<script>window.gokuProps = {};</script>"),
            response("<html>Javascript is disabled</html>"),
            response("<html>Access denied</html>"),
            response("<html>Complete the CAPTCHA</html>"),
        ):
            with self.subTest(status=failed["status"], body=failed["body"]):
                (self.policy / "cooldown.json").unlink(missing_ok=True)
                self.robots()
                self.mock_transport.reset_mock()
                self.mock_transport.side_effect = [failed]
                with self.assertRaises(fetch.CooldownError):
                    self.collect()
                state = fetch._read_json(self.policy / "cooldown.json")
                self.assertEqual(state["until"], self.clock + 86400)
                self.assertEqual(self.mock_transport.call_count, 1)

    def test_timeout_and_5xx_get_only_two_retries(self):
        self.robots()
        self.mock_transport.side_effect = [
            urllib.error.URLError("timed out"), response(status=503),
            response(page(rows=[recipe()])),
        ]
        result = self.collect()
        self.assertEqual(self.mock_transport.call_count, 3)
        self.assertEqual(len(result["records"]), 1)
        self.assertGreaterEqual(self.clock - STAMP, 18)

    def test_http_date_retry_after_is_honored(self):
        self.robots()
        self.mock_transport.side_effect = [
            response(status=429, headers={"retry-after": formatdate(self.clock + 7200, usegmt=True)}),
        ]
        with self.assertRaises(fetch.CooldownError):
            self.collect()
        self.assertEqual(fetch._read_json(self.policy / "cooldown.json")["until"], STAMP + 7200)

    def test_redirect_is_followed_explicitly_with_pacing_and_same_identity(self):
        self.robots()
        target = fetch.ORIGIN + "/forever/skill=202/engineering"
        self.mock_transport.side_effect = [
            response(status=301, headers={"location": target}),
            response(page(rows=[recipe()]), url=target),
        ]
        result = self.collect()
        self.assertEqual(self.mock_transport.call_args_list[1].args[0], target)
        self.assertGreaterEqual(self.clock - STAMP, 3)
        self.assertEqual(result["records"][0]["RequiredAbility"], 20222)

    def test_redirect_has_robots_and_entity_checks_and_three_redirect_limit(self):
        for target, robots, count in (
            (fetch.ORIGIN + "/forever/skill=164/blacksmithing", "User-agent: *\nDisallow:\n", 1),
            ("https://example.com/forever/skill=202", "User-agent: *\nDisallow:\n", 1),
            (fetch.ORIGIN + "/forever/skill=202/blocked",
             "User-agent: *\nDisallow: /forever/skill=202/blocked\n", 1),
            (SKILL_URL, "User-agent: *\nDisallow:\n", 4),
        ):
            with self.subTest(target=target):
                self.robots(robots)
                self.mock_transport.reset_mock()
                self.mock_transport.side_effect = [
                    response(status=302, headers={"location": target}),
                ] * 4
                with self.assertRaises(fetch.FetchError):
                    self.collect()
                self.assertEqual(self.mock_transport.call_count, count)
                self.assertFalse(self.cache.exists())

    def test_urllib_redirect_handler_does_not_make_hidden_requests(self):
        handler = fetch._NoAutomaticRedirect()
        self.assertIsNone(handler.redirect_request(
            None, None, 301, "Moved", {}, SKILL_URL))

    def test_exhausted_retries_or_invalid_page_do_not_replace_cache(self):
        path = self.cached(SKILL_URL, page(rows=[recipe()]), age_days=8)
        before = path.read_bytes()
        self.robots()
        self.mock_transport.side_effect = [response(status=503)] * 3
        with self.assertRaises(fetch.FetchError):
            self.collect()
        self.assertEqual(path.read_bytes(), before)
        self.mock_transport.side_effect = [response(page(rows=[recipe()], env=4))]
        with self.assertRaises(fetch.ValidationError):
            self.collect()
        self.assertEqual(path.read_bytes(), before)

    def test_off_origin_request_or_response_is_rejected(self):
        with self.assertRaises(fetch.FetchError):
            fetch._validate_url("https://example.com/forever/skill=202")
        self.robots()
        self.mock_transport.side_effect = [
            response(page(rows=[recipe()]), url="https://example.com/forever/skill=202"),
        ]
        with self.assertRaises(fetch.FetchError):
            self.collect()
        self.assertFalse(self.cache.exists())

    def test_global_lock_rejects_another_fetch_and_releases_on_failure(self):
        self.robots()
        with fetch._network_lock():
            with self.assertRaises(fetch.FetchError):
                self.collect()
        self.mock_transport.side_effect = [response(page(rows=[recipe()]))]
        self.assertEqual(len(self.collect()["records"]), 1)


if __name__ == "__main__":
    unittest.main()
