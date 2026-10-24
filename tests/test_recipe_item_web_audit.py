"""Verified-cache-only replay tests; no network or main mapping changes."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

import test_recipe_item_audit as fixtures


sys.path.insert(0, str(fixtures.PIPELINE))
try:
    SPEC = importlib.util.spec_from_file_location(
        "df_recipe_item_web_audit_test", fixtures.PIPELINE / "fc_recipe_item_web_audit.py")
    WEB = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(WEB)
finally:
    sys.path.pop(0)


def page(kind, entity_id, lists, patch="1.60.1"):
    metadata = {"page": "%s=%d" % (kind, entity_id),
                "dataEnv": {"env": 16, "tree": 16, "versions": {"16": patch}}}
    scripts = ["new Listview({template:%s,id:%s,data:%s});" %
               (json.dumps(template), json.dumps(name), json.dumps(rows))
               for template, name, rows in lists]
    return ('<script id="data.pageMeta" type="application/json">' +
            json.dumps(metadata) + "</script><script>" + "".join(scripts) + "</script>")


class RecipeItemWebAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RecipeItemAuditTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.cache = self.fixture.root / "webcache"
        self.cache.mkdir()
        self.output = self.fixture.root / "web-audit.json"
        self.network = mock.patch("urllib.request.build_opener",
                                  side_effect=AssertionError("network is forbidden in replay"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def cached(self, kind, entity_id, lists, patch="1.60.1", **changes):
        url = "https://www.wowhead.com/forever/%s%%3D%d" % (kind, entity_id)
        html = page(kind, entity_id, lists, patch)
        content = {
            "version": 1, "url": url, "html": html,
            "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "fetched_at": "2026-10-20T10:00:00Z", "checked_at": "2026-10-21T10:00:00Z",
        }
        content.update(changes)
        path = self.cache / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    def audit(self):
        return WEB.audit(self.fixture.recipes, self.fixture.db2, self.cache)

    def run_cli(self, *extra):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = WEB.main([
                "--recipe-items-csv", str(self.fixture.recipes),
                "--db2-dir", str(self.fixture.db2), "--cache-dir", str(self.cache),
                "--output-json", str(self.output), *extra,
            ])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_dynamic_candidates_and_explicit_teaching_are_separate_from_list_membership(self):
        self.cached("skill", 202, [
            ("spell", "recipes", [{"id": 201, "skill": [202]},
                                  {"id": 800, "skill": [202]}, {"id": 901, "skill": [202]}]),
            ("item", "recipe-items", [{"id": 7}, {"id": 8}]),
        ])
        self.cached("spell", 300, [("item", "taught-by-item", [{"id": 3}])])
        self.cached("item", 7, [("spell", "teaches", [{"id": 700}])])
        report = self.audit()
        rows = {row["RecipeItemID"]: row for row in report["Items"]}
        self.assertEqual(set(rows), set(range(1, 14)))
        self.assertEqual(rows[2]["SkillRecipeIdentityMatches"][0]["RecipeSpellID"], 201)
        self.assertEqual(rows[9]["SkillRecipeIdentityMatches"][0]["RecipeSpellID"], 901)
        self.assertEqual(rows[3]["ExplicitWebTeachingEvidence"][0]["RecipeSpellID"], 300)
        self.assertEqual(rows[7]["ExplicitWebTeachingEvidence"][0]["RecipeSpellID"], 700)
        self.assertEqual(rows[8]["LocalTaughtSpellIDs"], [])
        self.assertEqual(rows[8]["SkillRecipeIdentityMatches"], [])
        self.assertEqual(rows[8]["Status"], "pending")
        self.assertEqual(report["Findings"]["RecipeItemsListHitIDs"], [7, 8])
        self.assertNotIn(800, report["Findings"]["CandidateSpellIDsChecked"])
        self.assertEqual(report["Findings"]["NewMappingsAdded"], 0)
        source = rows[7]["ExplicitWebTeachingEvidence"][0]["Source"]
        self.assertEqual(source["SourceBuild"], "")
        self.assertEqual(source["SourcePatch"], "1.60.1")
        self.assertEqual(source["SourceCheckedAt"], "2026-10-21T10:00:00Z")
        self.assertEqual(len(source["SourceSHA256"]), 64)

    def test_removed_current_candidates_are_not_retained_from_prior_web_report(self):
        self.cached("item", 7, [("spell", "teaches", [{"id": 700}])])
        first = self.audit()
        self.assertIn(7, first["Findings"]["ExplicitWebTeachingItemIDs"])
        self.fixture.write_csv(self.fixture.recipes, ("RecipeItemID", "RecipeSpellID", "Build"),
                               [{"RecipeItemID": n, "RecipeSpellID": 700 if n == 7 else "",
                                 "Build": fixtures.BUILD} for n in range(1, 14)])
        second = self.audit()
        self.assertEqual(second["CurrentCSV"]["UnmappedRecipeItemCount"], 12)
        self.assertNotIn(7, {row["RecipeItemID"] for row in second["Items"]})
        self.assertEqual(second["Findings"]["ExplicitWebTeachingItemIDs"], [])

    def test_missing_caches_or_missing_teaches_list_stay_pending(self):
        self.cached("item", 7, [])
        report = self.audit()
        self.assertFalse(report["Coverage"]["Complete"])
        self.assertEqual(report["Coverage"]["PendingItems"], 13)
        self.assertEqual(report["Coverage"]["ItemsWithObservedWebEvidence"], 0)
        self.assertTrue(all(row["Status"] == "pending" for row in report["Items"]))

    def test_cross_patch_observation_preserves_provenance_but_stays_pending(self):
        self.cached("item", 7, [("spell", "teaches", [{"id": 700}])], patch="1.60.2")
        row = next(row for row in self.audit()["Items"] if row["RecipeItemID"] == 7)
        self.assertEqual(row["Status"], "pending")
        evidence = row["ExplicitWebTeachingEvidence"][0]
        self.assertEqual(evidence["VersionStatus"], "source_patch_mismatch")
        self.assertEqual(evidence["Source"]["SourcePatch"], "1.60.2")

    def test_replay_is_deterministic_and_does_not_mutate_cache_or_mapping(self):
        self.cached("item", 7, [("spell", "teaches", [{"id": 700}])])
        before = {path: path.read_bytes() for path in self.fixture.root.rglob("*") if path.is_file()}
        first, second = self.audit(), self.audit()
        self.assertEqual(first, second)
        self.assertEqual(before, {path: path.read_bytes()
                                 for path in self.fixture.root.rglob("*") if path.is_file()})
        result, stdout, stderr = self.run_cli("--dry-run")
        self.assertEqual(result, 0, stdout + stderr)
        self.assertFalse(self.output.exists())

    def test_invalid_hash_page_identity_or_timestamp_fails_before_publication(self):
        self.output.write_bytes(b"previous report")
        invalid = [
            {"sha256": "0" * 64},
            {"fetched_at": "2026-10-20T10:00:00"},
            {"html": page("item", 99, []),
             "sha256": hashlib.sha256(page("item", 99, []).encode("utf-8")).hexdigest()},
        ]
        for changes in invalid:
            with self.subTest(changes=changes):
                self.cached("item", 7, [], **changes)
                result, _, stderr = self.run_cli()
                self.assertEqual(result, 1, stderr)
                self.assertEqual(self.output.read_bytes(), b"previous report")

    def test_publication_cannot_overwrite_cached_source(self):
        cache_path = self.cached("item", 7, [])
        before = cache_path.read_bytes()
        result, _, stderr = self.run_cli("--output-json", str(cache_path))
        self.assertEqual(result, 1)
        self.assertIn("overwrite", stderr)
        self.assertEqual(cache_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
