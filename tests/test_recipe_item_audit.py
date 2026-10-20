"""Offline fixture coverage for unresolved recipe-item teaching audits."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "df-data-pipeline/_temp"
sys.path.insert(0, str(PIPELINE))
try:
    SPEC = importlib.util.spec_from_file_location("df_recipe_item_audit_test", PIPELINE / "fc_recipe_item_audit.py")
    AUDIT = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(AUDIT)
finally:
    sys.path.pop(0)
BUILD = "1.60.1.70450"


class RecipeItemAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="df-recipe-audit-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        import fc_pipeline_common as common
        patcher = mock.patch.object(common, 'REPO', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.db2 = self.root / "db2"
        self.db2.mkdir()
        self.recipes = self.root / "recipes.csv"
        self.baseline = self.root / "baseline.csv"
        self.items = self.root / "items.csv"
        self.prices = self.root / "prices.csv"
        self.output = self.root / "audit.csv"
        self.summary = self.root / "audit.json"
        links = [(1, 100, 6), (2, 200, 0), (3, 300, 6), (4, 400, 6),
                 (5, 500, 6), (6, 600, 0), (7, 700, 6), (8, 800, 1),
                 (9, 901, 6), (9, 902, 6), (10, 100, 6), (10, 300, 6),
                 (11, 1100, 0), (12, 1200, 0), (13, 1300, 6)]
        self.tables = {
            "itemeffect": [{"ID": n, "SpellID": spell, "TriggerType": trigger}
                           for n, (_, spell, trigger) in enumerate(links, 1)],
            "itemxitemeffect": [{"ID": n, "ItemID": item, "ItemEffectID": n}
                               for n, (item, _, _) in enumerate(links, 1)],
            "spelleffect": [
                {"ID": n, "SpellID": spell, "Effect": effect,
                 "EffectTriggerSpell": target, "EffectMiscValue[0]": skill}
                for n, (spell, effect, target, skill) in enumerate([
                    (100, 44, 0, 202), (200, 36, 201, 0), (600, 36, -1, 0),
                    (1100, 118, 0, 40), (1100, 36, 1101, 0),
                    (1300, 36, 1301, 0), (1301, 36, 1300, 0),
                ], 1)
            ],
            "spelllearnspell": [{"ID": 1, "SpellID": 1200, "LearnSpellID": 1201}],
            "skilllineability": [
                {"ID": n, "Spell": spell, "SkillLine": skill}
                for n, (spell, skill) in enumerate([
                    (201, 2941), (400, 40), (800, 202),
                    (901, 202), (902, 202), (1101, 40), (1201, 202),
                ], 1)
            ],
            "skillline": [{"ID": 202, "ParentSkillLineID": 0},
                          {"ID": 2941, "ParentSkillLineID": 202},
                          {"ID": 40, "ParentSkillLineID": 0}],
            "spellname": [{"ID": spell, "Name_lang": "Goblin Gnomish name %d" % spell}
                          for spell in (100, 201, 300, 400, 700, 800, 901, 902, 1101, 1201)],
        }
        self.write_db2()
        recipe_rows = [{"RecipeItemID": n, "RecipeSpellID": "", "Build": BUILD}
                       for n in range(1, 14)]
        self.write_csv(self.recipes, ("RecipeItemID", "RecipeSpellID", "Build"), recipe_rows)
        self.baseline.write_bytes(self.recipes.read_bytes())
        self.write_csv(self.items, ("ID", "ClassID", "SubclassID"),
                       [{"ID": n, "ClassID": 9, "SubclassID": 0 if n == 7 else 3}
                        for n in range(1, 14)])
        self.write_csv(self.prices, ("ItemID", "Name_enUS", "Build"),
                       [{"ItemID": n, "Name_enUS": "Book or schematic %d" % n, "Build": BUILD}
                        for n in range(1, 14)])

    def write_csv(self, path, fields, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            writer.writerows(rows)

    def write_db2(self):
        manifest = {"build": BUILD, "tables": {}}
        for name, rows in self.tables.items():
            path = self.db2 / (name + ".csv")
            self.write_csv(path, AUDIT.TABLE_FIELDS[name], rows)
            manifest["tables"][name] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rows": len(rows),
                "url": "http://127.0.0.1:5000/dbc/export/?name=%s&build=%s" % (name, BUILD),
            }
        (self.db2 / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def run_audit(self, *extra, automatic=False):
        arguments = [
            "--recipe-items-csv", str(self.recipes), "--item-csv", str(self.items),
            "--prices-csv", str(self.prices),
            "--output-csv", str(self.output), "--summary-json", str(self.summary), *extra,
        ]
        if not automatic:
            arguments.extend(("--db2-dir", str(self.db2)))
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = AUDIT.main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def records(self):
        with self.output.open(encoding="utf-8-sig", newline="") as stream:
            return {int(row["ItemID"]): row for row in csv.DictReader(stream)}

    def test_explicit_fields_classify_ranks_skills_missing_and_multiple_targets(self):
        result, stdout, stderr = self.run_audit()
        self.assertEqual(result, 0, stdout + stderr)
        rows = self.records()
        expected = {
            1: "profession_rank", 2: "profession_recipe_candidate",
            3: "missing_skill_line", 4: "other_skill_line",
            5: "missing_spell_record", 6: "no_teaching_relation",
            7: "missing_skill_line", 8: "no_teaching_relation",
            9: "multiple_targets", 10: "mixed_targets", 11: "skill_rank",
            12: "profession_recipe_candidate", 13: "teaching_cycle",
        }
        self.assertEqual({key: row["classification"] for key, row in rows.items()}, expected)
        self.assertEqual(json.loads(rows[2]["TaughtSpellIDs"]), [201])
        self.assertEqual(json.loads(rows[12]["TaughtSpellIDs"]), [1201])
        self.assertEqual(rows[7]["SubclassID"], "0")
        self.assertIn("SpellLearnSpell[1]", rows[12]["LearningPath"])
        self.assertEqual(json.loads(rows[6]["TaughtSpellIDs"]), [])
        rank = json.loads(rows[11]["TargetClassifications"])["1101"][0]
        self.assertEqual(rank["rankSpellIDs"], [1100])

    def test_baseline_retains_resolved_items_without_changing_audit_evidence(self):
        self.write_csv(self.recipes, ("RecipeItemID", "RecipeSpellID", "Build"),
                       [{"RecipeItemID": n, "RecipeSpellID": 201 if n == 2 else "", "Build": BUILD}
                        for n in range(1, 14)])
        result, stdout, stderr = self.run_audit("--baseline-csv", str(self.baseline))
        self.assertEqual(result, 0, stdout + stderr)
        rows = self.records()
        self.assertEqual(len(rows), 13)
        self.assertEqual(rows[2]["MappingResolved"], "true")
        self.assertEqual(json.loads(rows[2]["CurrentRecipeSpellIDs"]), [201])
        summary = json.loads(self.summary.read_text(encoding="utf-8"))
        self.assertEqual(summary["mappingResolved"], 1)
        self.assertEqual(summary["stillUnmapped"], 12)
        result, stdout, stderr = self.run_audit()
        self.assertEqual(result, 0, stdout + stderr)
        self.assertNotIn(2, self.records())

    def test_cross_build_baseline_tracks_new_resolved_removed_and_mapping_regressions(self):
        self.write_csv(self.baseline, ("RecipeItemID", "RecipeSpellID", "Build"),
                       [{"RecipeItemID": n, "RecipeSpellID": 300 if n == 3 else "",
                         "Build": "1.60.1.70000"} for n in range(1, 14)])
        self.write_csv(self.recipes, ("RecipeItemID", "RecipeSpellID", "Build"),
                       [{"RecipeItemID": n, "RecipeSpellID": 201 if n == 2 else "", "Build": BUILD}
                        for n in range(1, 15) if n != 4])
        self.write_csv(self.items, ("ID", "ClassID", "SubclassID"),
                       [{"ID": n, "ClassID": 9, "SubclassID": 3} for n in range(1, 15) if n != 4])
        self.write_csv(self.prices, ("ItemID", "Name_enUS", "Build"),
                       [{"ItemID": n, "Name_enUS": str(n), "Build": BUILD}
                        for n in range(1, 15) if n != 4])
        result, stdout, stderr = self.run_audit("--baseline-csv", str(self.baseline),
                                                "--include-current-unmapped")
        self.assertEqual(result, 0, stdout + stderr)
        rows = self.records()
        self.assertEqual(set(rows), set(range(1, 15)))
        self.assertEqual(rows[4]["classification"], "removed_from_current_snapshot")
        self.assertEqual(rows[4]["MappingResolved"], "false")
        self.assertEqual(rows[4]["TaughtSpellIDs"], "[]")
        summary = json.loads(self.summary.read_text(encoding="utf-8"))
        self.assertEqual(summary["baselineBuild"], "1.60.1.70000")
        self.assertEqual(summary["targetBuild"], BUILD)
        self.assertEqual(summary["newlyUnmapped"], 2)
        self.assertEqual(summary["resolved"], 1)
        self.assertEqual(summary["removed"], 1)
        self.assertEqual(summary["stillUnmapped"], 12)
        self.assertEqual(summary["comparisonItemIDs"],
                         {"newlyUnmapped": [3, 14], "resolved": [2], "removed": [4]})
        result, stdout, stderr = self.run_audit("--baseline-csv", str(self.baseline))
        self.assertEqual(result, 0, stdout + stderr)
        self.assertNotIn(3, self.records())
        self.assertNotIn(14, self.records())

    def test_manifest_hash_build_and_count_errors_preserve_existing_outputs(self):
        self.output.write_bytes(b"old csv")
        self.summary.write_bytes(b"old json")
        manifest_path = self.db2 / "manifest.json"
        original = manifest_path.read_text(encoding="utf-8")
        for field, value in (
                ("sha256", "0" * 64), ("rows", 999),
                ("url", "http://localhost/?build=1.60.1.70451")):
            with self.subTest(field=field):
                manifest = json.loads(original)
                manifest["tables"]["itemeffect"][field] = value
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                result, _, stderr = self.run_audit()
                self.assertEqual(result, 1, stderr)
                self.assertEqual(self.output.read_bytes(), b"old csv")
                self.assertEqual(self.summary.read_bytes(), b"old json")
        manifest_path.write_text(original, encoding="utf-8")
        self.recipes.write_text(self.recipes.read_text(encoding="utf-8-sig").replace(
            BUILD, "1.60.1.70451"), encoding="utf-8-sig")
        result, _, stderr = self.run_audit()
        self.assertEqual(result, 1)
        self.assertIn("build mismatch", stderr)

    def test_catalog_matches_are_audit_only_and_non_teaching_trigger_stays_unmapped(self):
        catalog = self.root / "catalog.json"
        catalog.write_text(json.dumps([
            {"id": 3, "spell": 800, "skill": 202, "products": [[8, 1]]},
            {"id": 2, "spell": 400, "skill": 40, "products": [[4, 1]]},
        ]), encoding="utf-8")
        metadata = {"url": "https://wuxianwow.com/data/recipes.json", "sourceBuild": "",
                    "sha256": hashlib.sha256(catalog.read_bytes()).hexdigest()}
        (self.root / "source.json").write_text(json.dumps(metadata), encoding="utf-8")
        result, stdout, stderr = self.run_audit("--recipe-catalog-json", str(catalog))
        self.assertEqual(result, 0, stdout + stderr)
        evidence = json.loads(self.summary.read_text(encoding="utf-8"))["recipeCatalogAudit"]
        self.assertEqual(evidence["catalogRows"], 2)
        self.assertEqual(evidence["matchingSlaRows"], 2)
        self.assertFalse(evidence["catalogHasItemTeachingField"])
        self.assertEqual(evidence["matchingUnmappedItemCandidates"], [4, 8])
        self.assertEqual(evidence["source"]["sourceBuild"], "")
        self.assertEqual(self.records()[8]["classification"], "no_teaching_relation")
        self.assertEqual(self.records()[8]["MappingResolved"], "false")
        catalog.write_text("[]", encoding="utf-8")
        result, _, stderr = self.run_audit("--recipe-catalog-json", str(catalog))
        self.assertEqual(result, 1)
        self.assertIn("SHA-256 mismatch", stderr)

    def test_dry_run_never_writes_or_changes_inputs(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result, stdout, stderr = self.run_audit("--dry-run")
        self.assertEqual(result, 0, stdout + stderr)
        after = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, before)

    def test_default_db2_directory_comes_from_unique_recipe_build(self):
        scripts = self.root / "_temp"
        destination = scripts / "_fc/cache/specializations/db2" / BUILD
        shutil.copytree(self.db2, destination)
        with mock.patch.object(AUDIT, "HERE", scripts):
            result, stdout, stderr = self.run_audit("--dry-run", automatic=True)
        self.assertEqual(result, 0, stdout + stderr)

    def pointer_fixture(self):
        scripts = self.root / "_temp"
        cache_root = scripts / "_fc/cache/specializations"
        directory = cache_root / "db2" / BUILD / "new-hotfix-snapshot"
        shutil.copytree(self.db2, directory)
        pointer = {
            "schemaVersion": 1,
            "targetBuild": BUILD,
            "outputs": {"recipe_items": {
                "sha256": hashlib.sha256(self.recipes.read_bytes()).hexdigest()}},
            "db2Snapshot": {
                "path": str(directory),
                "manifestSHA256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
            },
        }
        pointer_path = cache_root / "current.json"
        pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
        return scripts, directory, pointer_path, pointer

    def test_matching_current_pointer_selects_exact_hotfix_snapshot(self):
        scripts, directory, _, _ = self.pointer_fixture()
        # A stale same-build legacy manifest must never take precedence.
        (directory.parent / "manifest.json").write_text("invalid legacy snapshot", encoding="utf-8")
        with mock.patch.object(AUDIT, "HERE", scripts):
            self.assertEqual(AUDIT.select_db2_dir(self.recipes, {}), directory)
            result, stdout, stderr = self.run_audit("--dry-run", automatic=True)
        self.assertEqual(result, 0, stdout + stderr)

    def test_read_only_csv_input_pointer_selects_current_snapshot(self):
        scripts, directory, pointer_path, pointer = self.pointer_fixture()
        pointer['schemaVersion'] = 2
        pointer['inputs'] = pointer.pop('outputs')
        pointer_path.write_text(json.dumps(pointer), encoding='utf-8')
        with mock.patch.object(AUDIT, 'HERE', scripts):
            self.assertEqual(AUDIT.select_db2_dir(self.recipes, {}), directory)
            result, stdout, stderr = self.run_audit('--dry-run', automatic=True)
        self.assertEqual(result, 0, stdout + stderr)

    def test_mismatched_current_pointer_requires_explicit_snapshot(self):
        scripts, _, pointer_path, original = self.pointer_fixture()
        cases = (
            ("recipe_hash", "0" * 64),
            ("target_build", "1.60.1.70451"),
            ("manifest_hash", "0" * 64),
        )
        for field, value in cases:
            with self.subTest(field=field):
                pointer = json.loads(json.dumps(original))
                if field == "recipe_hash":
                    pointer["outputs"]["recipe_items"]["sha256"] = value
                elif field == "target_build":
                    pointer["targetBuild"] = value
                else:
                    pointer["db2Snapshot"]["manifestSHA256"] = value
                pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
                with mock.patch.object(AUDIT, "HERE", scripts):
                    result, _, stderr = self.run_audit("--dry-run", automatic=True)
                    explicit, stdout, explicit_error = self.run_audit("--dry-run")
                self.assertEqual(result, 1)
                self.assertIn("--db2-dir", stderr)
                self.assertEqual(explicit, 0, stdout + explicit_error)
                self.assertFalse(self.output.exists())

    def test_missing_item_effect_reference_is_preserved_without_inventing_teaching(self):
        self.tables["itemxitemeffect"].append({"ID": 99, "ItemID": 6, "ItemEffectID": 999})
        self.write_db2()
        result, stdout, stderr = self.run_audit()
        self.assertEqual(result, 0, stdout + stderr)
        row = self.records()[6]
        self.assertEqual(row["classification"], "no_teaching_relation")
        self.assertEqual(json.loads(row["TaughtSpellIDs"]), [])
        self.assertIn("missing_ItemEffect_record", row["LearningPath"])
        self.assertIn("unresolved_ItemXItemEffect_reference", row["reason"])

    def test_output_cannot_alias_input_or_land_inside_db2_snapshot(self):
        original = self.recipes.read_bytes()
        result, _, stderr = self.run_audit("--output-csv", str(self.recipes))
        self.assertEqual(result, 1)
        self.assertIn("overwrite", stderr)
        self.assertEqual(self.recipes.read_bytes(), original)
        result, _, stderr = self.run_audit("--output-csv", str(self.db2 / "audit.csv"))
        self.assertEqual(result, 1)
        self.assertIn("DB2 snapshot", stderr)


if __name__ == "__main__":
    unittest.main()
