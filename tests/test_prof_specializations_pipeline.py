"""Exercise specialization evidence and publishing without any network requests."""
import contextlib
import copy
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "df-data-pipeline/_temp"
sys.path.insert(0, str(PIPELINE))
try:
    SPEC = importlib.util.spec_from_file_location(
        "df_specializations_test", PIPELINE / "fc_prof_specializations.py")
    SPECIALIZATIONS = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(SPECIALIZATIONS)
finally:
    sys.path.pop(0)

BUILD = "1.60.1.70450"


class FetchError(RuntimeError):
    pass


class CooldownError(FetchError):
    pass


def item(**changes):
    value = dict.fromkeys(SPECIALIZATIONS.ITEM_FIELDS, "")
    value.update(
        RecipeItemID=18653, RecipeSpellID=23078, RequiredAbility=20222,
        Status="confirmed", Reason="explicit_item_requirement",
        LearningPath="ItemXItemEffect:154042>ItemEffect:223078>Spell:23078",
        Build=BUILD, HotfixBuild="70450", Source="wow.tools.local",
    )
    value.update(changes)
    return value


def trainer(**changes):
    value = dict.fromkeys(SPECIALIZATIONS.TRAINER_FIELDS, "")
    value.update(
        RecipeSpellID=12760, RequiredAbility=20222, Status="confirmed",
        Reason="explicit_specialization_and_trainer_source", SkillLineID=202,
        LearnedAt=205, NPCIDs=[8126], TrainerObserved=True,
        SpecializationObserved=True, TargetBuild=BUILD,
        SourceEnvironment="forever",
        SourceURL="https://www.wowhead.com/forever/skill%3D202/engineering",
        SourcePatch="1.60.1", SourceBuild="",
        SourceFetchedAt="2026-10-20T12:00:00Z", SourceSHA256="a" * 64,
        Evidence="recipes.specialization; recipes.source contains 6",
    )
    value.update(changes)
    return value


class SpecializationPipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="df-specializations-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        import fc_pipeline_common as common
        patcher = mock.patch.object(common, 'REPO', self.directory)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.data = self.directory / "data"
        self.data.mkdir()
        self.item_csv = self.directory / "recipe-items.csv"
        self.trainer_csv = self.data / "trainer-recipe-specializations.csv"
        self.output = self.directory / "Core/Data/Data_ProfSpecializations.lua"
        self.cache = self.directory / "cache"
        self.write_items([item()])
        self.write_json("prof_engineering.json", {
            "build": "1.60.1.70245",
            "rows": [{"spell": 12760}, {"spell": 12754}, {"spell": 12906}],
            "leveling": {"recipes": {"3918": {}}, "steps": [{"spell": 3922}]},
        })
        self.write_json("prof_enchanting.json", {
            "build": "1.60.1.70245",
            "enchants": [{"name": "Enchant Bracer - Test"},
                         {"name": "unresolved enchant"}],
            "crafted": [{"spell": 7421}],
        })
        self.write_json("enchant_ids.json", {
            "Enchant Bracer - Test": {"spell": 7443, "created": 0},
        })

    def write_json(self, name, value):
        (self.data / name).write_text(json.dumps(value), encoding="utf-8")

    def write_items(self, rows, fields=None):
        with self.item_csv.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fields or SPECIALIZATIONS.ITEM_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def write_trainers(self, rows):
        normalized = [SPECIALIZATIONS.normalize_trainer(row, BUILD) for row in rows]
        self.trainer_csv.write_bytes(SPECIALIZATIONS.csv_bytes(normalized))

    def run_cli(self, *extra, records=None, failure=None, collect_action=None):
        fake = types.ModuleType("fc_specialization_fetch")
        fake.FetchError = FetchError
        fake.collect_trainers = mock.Mock()
        if failure is not None:
            fake.collect_trainers.side_effect = failure
        elif collect_action is not None:
            fake.collect_trainers.side_effect = collect_action
        else:
            fake.collect_trainers.return_value = {
                "records": [] if records is None else copy.deepcopy(records),
                "coverage": {"provider": "fixture"},
            }
        arguments = [
            "--recipe-items-csv", str(self.item_csv),
            "--trainer-csv", str(self.trainer_csv),
            "--output-lua", str(self.output),
            "--data-dir", str(self.data),
            "--cache-dir", str(self.cache),
            *extra,
        ]
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(sys.modules, {"fc_specialization_fetch": fake}), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = SPECIALIZATIONS.main(arguments)
        return result, stdout.getvalue(), stderr.getvalue(), fake.collect_trainers

    def seed_outputs(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.trainer_csv.write_bytes(b"previous trainer snapshot\n")
        self.output.write_bytes(b"previous Lua snapshot\n")
        return self.trainer_csv.read_bytes(), self.output.read_bytes()

    def assert_outputs(self, expected):
        self.assertEqual((self.trainer_csv.read_bytes(), self.output.read_bytes()), expected)

    def test_online_cli_preserves_target_and_source_builds_and_enchant_identity(self):
        records = [trainer(), trainer(RecipeSpellID=12754),
                   trainer(RecipeSpellID=12906, RequiredAbility=20219)]
        result, stdout, stderr, collect = self.run_cli(records=records)
        self.assertEqual(result, 0, stdout + stderr)
        collect.assert_called_once_with(self.cache.resolve(), offline=False, refresh=False)
        with self.trainer_csv.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        by_spell = {int(row["RecipeSpellID"]): row for row in rows}
        for spell in (12760, 12754, 12906, 23078, 7443, 7421, 3918, 3922):
            self.assertIn(spell, by_spell)
        self.assertEqual(by_spell[12906]["RequiredAbility"], "20219")
        self.assertEqual(by_spell[12760]["TargetBuild"], BUILD)
        self.assertEqual(by_spell[12760]["SourceBuild"], "")
        self.assertEqual(by_spell[7443]["Status"], "pending")
        generated = self.output.read_text(encoding="utf-8")
        self.assertIn("ns.ProfSpecializationsMeta", generated)
        self.assertIn("ns.ProfSpecializations = {", generated)
        self.assertIn("[7443]", generated)
        self.assertIn('coverage="observed-only"', generated)
        self.assertIn('build="1.60.1.70245"', generated)
        self.assertIn('"catalogWithoutSpellID": 1', stdout)

    def test_zero_requirement_stays_pending_in_both_learning_routes(self):
        self.write_items([item(RequiredAbility=0, Status="pending",
                               Reason="no_item_required_ability")])
        unknown = trainer(RequiredAbility=0, Status="pending",
                          SpecializationObserved=False,
                          Reason="no_explicit_specialization")
        result, stdout, stderr, _ = self.run_cli(records=[unknown])
        self.assertEqual(result, 0, stdout + stderr)
        generated = self.output.read_text(encoding="utf-8")
        self.assertIn('[23078] = {status="pending"', generated)
        self.assertIn('[12760] = {status="pending"', generated)
        self.assertNotIn('status="universal"', generated)
        self.assertNotIn('status="unrestricted"', generated)

    def test_item_build_validation_stops_before_fetch(self):
        cases = (
            ([item(), item(RecipeItemID=18654, Build="1.60.1.70451", HotfixBuild="70451")], []),
            ([item(HotfixBuild="70451")], []),
            ([item(Build="1.60.1", HotfixBuild="70450")], []),
            ([item()], ["--build", "1.60.1.70451"]),
            ([], []),
        )
        for rows, options in cases:
            with self.subTest(rows=rows, options=options):
                self.write_items(rows)
                result, _, stderr, collect = self.run_cli(*options)
                self.assertEqual(result, 1, stderr)
                collect.assert_not_called()
                self.assertFalse(self.output.exists())
        self.write_items([])
        result, stdout, stderr, _ = self.run_cli("--build", BUILD, "--offline")
        self.assertEqual(result, 0, stdout + stderr)

    def test_conflicting_source_patch_and_build_are_rejected(self):
        previous = self.seed_outputs()
        row = trainer(SourceBuild="1.60.2.70450")
        result, _, stderr, _ = self.run_cli(records=[row])
        self.assertEqual(result, 1, stderr)
        self.assert_outputs(previous)

    def test_offline_replays_csv_when_page_cache_is_missing(self):
        self.write_trainers([trainer()])
        result, stdout, stderr, collect = self.run_cli("--offline")
        self.assertEqual(result, 0, stdout + stderr)
        collect.assert_called_once_with(self.cache.resolve(), offline=True, refresh=False)
        first = self.trainer_csv.read_bytes(), self.output.read_bytes()
        result, stdout, stderr, _ = self.run_cli("--offline")
        self.assertEqual(result, 0, stdout + stderr)
        self.assert_outputs(first)
        reloaded = SPECIALIZATIONS.load_trainers(self.trainer_csv, BUILD, {})
        known = next(row for row in reloaded if row["RecipeSpellID"] == 12760)
        self.assertTrue(known["TrainerObserved"])
        self.assertEqual(known["NPCIDs"], [8126])
        self.assertEqual(known["RequiredAbility"], 20222)

    def test_offline_retarget_preserves_original_web_provenance(self):
        self.write_trainers([trainer()])
        text = self.trainer_csv.read_text(encoding="utf-8-sig").replace(BUILD, "1.60.1.70449")
        self.trainer_csv.write_text(text, encoding="utf-8-sig")
        result, _, stderr, collect = self.run_cli("--offline")
        self.assertEqual(result, 0, stderr)
        collect.assert_called_once()
        rows = SPECIALIZATIONS.load_trainers(self.trainer_csv, BUILD, {})
        known = next(row for row in rows if row["RecipeSpellID"] == 12760)
        self.assertEqual(known["TargetBuild"], BUILD)
        self.assertEqual(known["SourcePatch"], "1.60.1")
        self.assertEqual(known["SourceBuild"], "")
        self.assertEqual(known["SourceFetchedAt"], "2026-10-20T12:00:00Z")
        self.assertEqual(known["SourceSHA256"], "a" * 64)

    def test_malformed_offline_target_build_is_rejected(self):
        self.write_trainers([trainer()])
        text = self.trainer_csv.read_text(encoding="utf-8-sig").replace(BUILD, "invalid-build")
        self.trainer_csv.write_text(text, encoding="utf-8-sig")
        result, _, stderr, collect = self.run_cli("--offline")
        self.assertEqual(result, 1, stderr)
        collect.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_different_source_patch_or_exact_build_remains_pending(self):
        for changes in (
                {"SourcePatch": "1.60.2"},
                {"SourceBuild": "1.60.1.70449"},
        ):
            with self.subTest(changes=changes):
                row = SPECIALIZATIONS.normalize_trainer(trainer(**changes), BUILD)
                self.assertEqual(row["Status"], "pending")
                self.assertTrue(row["Reason"])
                for key, value in changes.items():
                    self.assertEqual(row[key], value)

    def test_version_pending_recovers_when_replayed_against_matching_target(self):
        for changes, matching_build in (
                ({"SourcePatch": "1.60.2"}, "1.60.2.70450"),
                ({"SourceBuild": "1.60.1.70449"}, "1.60.1.70449"),
        ):
            with self.subTest(changes=changes):
                pending = SPECIALIZATIONS.normalize_trainer(trainer(**changes), BUILD)
                self.assertEqual(pending["Status"], "pending")
                self.trainer_csv.write_bytes(SPECIALIZATIONS.csv_bytes([pending]))
                rows = SPECIALIZATIONS.load_trainers(self.trainer_csv, matching_build, {})
                self.assertEqual(rows[0]["Status"], "confirmed")
                self.assertEqual(rows[0]["TargetBuild"], matching_build)
                self.assertEqual(rows[0]["SourceFetchedAt"], pending["SourceFetchedAt"])
                self.assertEqual(rows[0]["SourceSHA256"], pending["SourceSHA256"])
                ordinary_pending = trainer(Status="pending", Reason="awaiting_confirmation")
                unchanged = SPECIALIZATIONS.normalize_trainer(ordinary_pending, BUILD)
                self.assertEqual(unchanged["Status"], "pending")

    def test_offline_merge_keeps_missing_pages_and_newer_evidence(self):
        old = trainer()
        previous = [old, trainer(RecipeSpellID=12906, RequiredAbility=20219,
                                SourceURL="https://www.wowhead.com/forever/spell=12906")]
        newer = trainer(SourceFetchedAt="2026-10-21T12:00:00Z", SourceSHA256="b" * 64,
                        LearnedAt=210)
        merged = SPECIALIZATIONS.merge_trainer_snapshots(previous, [newer], BUILD)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["LearnedAt"], 210)
        self.assertEqual(merged[1]["RequiredAbility"], 20219)
        with self.assertRaises(SPECIALIZATIONS.DataError):
            SPECIALIZATIONS.merge_trainer_snapshots(
                [old], [trainer(SourceSHA256="b" * 64)], BUILD)

    def test_offline_merge_keeps_supplemental_trainer_evidence_when_cache_is_missing(self):
        previous = trainer(
            TrainerSourceURL="https://www.wowhead.com/forever/spell%3D12760",
            TrainerSourcePatch="1.60.1",
            TrainerSourceFetchedAt="2026-10-20T12:01:00Z",
            TrainerSourceSHA256="c" * 64,
            Evidence="Wowhead.recipes.specialization; Wowhead.taught-by-npc",
        )
        missing = trainer(
            Status="pending", Reason="trainer_page_cache_missing",
            TrainerObserved=False, NPCIDs=[],
            Evidence="Wowhead.recipes.specialization; trainer_unconfirmed",
        )
        merged = SPECIALIZATIONS.merge_trainer_snapshots([previous], [missing], BUILD)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["Status"], "confirmed")
        self.assertEqual(merged[0]["NPCIDs"], [8126])
        self.assertEqual(merged[0]["TrainerSourceSHA256"], "c" * 64)

    def test_newer_supplemental_trainer_page_replaces_relationship_on_same_skill_snapshot(self):
        previous = trainer(
            TrainerSourceURL="https://www.wowhead.com/forever/spell%3D12760",
            TrainerSourcePatch="1.60.1",
            TrainerSourceFetchedAt="2026-10-20T12:01:00Z",
            TrainerSourceSHA256="c" * 64,
            Evidence="Wowhead.recipes.specialization; Wowhead.taught-by-npc",
        )
        newer = dict(previous, TrainerSourceFetchedAt="2026-10-21T12:01:00Z",
                     TrainerSourceSHA256="d" * 64, NPCIDs=[7406])
        merged = SPECIALIZATIONS.merge_trainer_snapshots([previous], [newer], BUILD)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["NPCIDs"], [7406])
        self.assertEqual(merged[0]["TrainerSourceSHA256"], "d" * 64)

    def test_supplemental_page_version_mismatch_preserves_evidence_as_pending(self):
        base = trainer(
            TrainerSourceURL="https://www.wowhead.com/forever/spell%3D12760",
            TrainerSourcePatch="1.60.1",
            TrainerSourceFetchedAt="2026-10-20T12:01:00Z",
            TrainerSourceSHA256="c" * 64,
            Evidence="Wowhead.recipes.specialization; Wowhead.taught-by-npc",
        )
        cases = (
            ({"TrainerSourcePatch": "1.60.2"}, "trainer_source_patch_mismatch"),
            ({"TrainerSourceBuild": "1.60.1.70449"}, "trainer_source_build_mismatch"),
        )
        for changes, reason in cases:
            with self.subTest(changes=changes):
                row = SPECIALIZATIONS.normalize_trainer(dict(base, **changes), BUILD)
                self.assertEqual(row["Status"], "pending")
                self.assertEqual(row["Reason"], reason)
                self.assertEqual(row["NPCIDs"], [8126])
                self.assertEqual(row["RequiredAbility"], 20222)
                for key, value in changes.items():
                    self.assertEqual(row[key], value)
        with self.assertRaises(SPECIALIZATIONS.DataError):
            SPECIALIZATIONS.normalize_trainer(
                dict(base, TrainerSourceBuild="1.60.2.70450"), BUILD)

    def test_alternative_items_and_trainers_do_not_create_false_conflict(self):
        items = [item(RecipeSpellID=12760),
                 item(RecipeItemID=18654, RecipeSpellID=12760, RequiredAbility=20219)]
        trainers = [SPECIALIZATIONS.normalize_trainer(trainer(), BUILD),
                    SPECIALIZATIONS.normalize_trainer(
                        trainer(RequiredAbility=20219, NPCIDs=[7406]), BUILD)]
        mapped, _ = SPECIALIZATIONS.requirement_map(items, trainers, {12760})
        self.assertEqual(mapped[12760]["status"], "confirmed")
        self.assertEqual(len(mapped[12760]["routes"]), 4)
        self.assertTrue(all(row["status"] == "confirmed" for row in mapped[12760]["routes"]))

    def test_same_item_or_trainer_with_different_abilities_conflicts(self):
        items = [item(RecipeSpellID=12760),
                 item(RecipeSpellID=12760, RequiredAbility=20219)]
        trainers = [SPECIALIZATIONS.normalize_trainer(trainer(), BUILD),
                    SPECIALIZATIONS.normalize_trainer(trainer(RequiredAbility=20219), BUILD)]
        mapped, _ = SPECIALIZATIONS.requirement_map(items, trainers, {12760})
        self.assertEqual(mapped[12760]["status"], "conflict")
        self.assertTrue(all(row["status"] == "conflict" for row in mapped[12760]["routes"]))

    def test_overlapping_trainer_sets_mark_every_conflicting_route(self):
        trainers = [trainer(RequiredAbility=20219, NPCIDs=[1, 2]),
                    trainer(RequiredAbility=20222, NPCIDs=[1]),
                    trainer(RequiredAbility=20222, NPCIDs=[2])]
        for records in (trainers, list(reversed(trainers))):
            normalized = [SPECIALIZATIONS.normalize_trainer(row, BUILD) for row in records]
            mapped, _ = SPECIALIZATIONS.requirement_map([], normalized, {12760})
            self.assertEqual(mapped[12760]["status"], "conflict")
            self.assertTrue(all(row["status"] == "conflict"
                                for row in mapped[12760]["routes"]))

    def test_invalid_trainer_schema_cannot_publish(self):
        previous = self.seed_outputs()
        invalid = (
            {"SourceEnvironment": "classic"},
            {"SourceURL": "https://www.wowhead.com/classic/spell=12760"},
            {"SourceSHA256": ""},
            {"SourceFetchedAt": "2026-10-20T12:00:00"},
            {"SourcePatch": "12.0.1"},
            {"RequiredAbility": 0},
            {"Evidence": ""},
            {"TrainerObserved": False},
            {"NPCIDs": "not json"},
            {"TrainerObserved": "1"},
        )
        for changes in invalid:
            with self.subTest(changes=changes):
                result, _, stderr, _ = self.run_cli(records=[trainer(**changes)])
                self.assertEqual(result, 1, stderr)
                self.assert_outputs(previous)

    def test_online_failure_preserves_both_existing_outputs(self):
        previous = self.seed_outputs()
        result, _, stderr, _ = self.run_cli(failure=FetchError("403; cooldown active"))
        self.assertEqual(result, 1)
        self.assertIn("cooldown", stderr)
        self.assert_outputs(previous)

    def test_cooldown_error_subclass_returns_failure_without_traceback(self):
        previous = self.seed_outputs()
        result, _, stderr, _ = self.run_cli(failure=CooldownError("cooldown active"))
        self.assertEqual(result, 1)
        self.assertIn("cooldown active", stderr)
        self.assertNotIn("Traceback", stderr)
        self.assert_outputs(previous)

    def test_first_online_failure_does_not_publish_partial_output(self):
        result, _, stderr, _ = self.run_cli(failure=FetchError("missing page"))
        self.assertEqual(result, 1, stderr)
        self.assertFalse(self.trainer_csv.exists())
        self.assertFalse(self.output.exists())

    def test_dry_run_preserves_outputs_and_forwards_explicit_refresh(self):
        previous = self.seed_outputs()
        result, stdout, stderr, collect = self.run_cli(
            "--dry-run", "--refresh-trainers", records=[trainer()])
        self.assertEqual(result, 0, stdout + stderr)
        collect.assert_called_once_with(self.cache.resolve(), offline=False, refresh=True)
        self.assertIn("[CHECK]", stdout)
        self.assert_outputs(previous)

    def test_input_change_during_fetch_prevents_publication(self):
        previous = self.seed_outputs()

        def mutate_input(*args, **kwargs):
            self.write_items([item(RequiredAbility=20219)])
            return {"records": [trainer()]}

        result, _, stderr, _ = self.run_cli(collect_action=mutate_input)
        self.assertEqual(result, 1)
        self.assertIn("input changed", stderr)
        self.assert_outputs(previous)

    def test_path_aliases_and_output_inside_cache_are_rejected(self):
        cases = (
            ["--trainer-csv", str(self.item_csv)],
            ["--output-lua", str(self.trainer_csv)],
            ["--output-lua", str(self.cache / "specializations.lua")],
        )
        for options in cases:
            with self.subTest(options=options):
                result, _, stderr, collect = self.run_cli(*options)
                self.assertEqual(result, 1, stderr)
                collect.assert_not_called()
        self.output.parent.mkdir(parents=True)
        try:
            os.link(self.item_csv, self.output)
        except OSError as error:
            self.skipTest("hardlinks unavailable: %s" % error)
        before = self.item_csv.read_bytes()
        result, _, stderr, collect = self.run_cli()
        self.assertEqual(result, 1, stderr)
        collect.assert_not_called()
        self.assertEqual(self.item_csv.read_bytes(), before)

    def test_malformed_csv_stops_before_collection(self):
        self.item_csv.write_text("RecipeItemID,RecipeSpellID\n18653,23078\n", encoding="utf-8")
        result, _, stderr, collect = self.run_cli()
        self.assertEqual(result, 1)
        self.assertIn("missing columns", stderr)
        collect.assert_not_called()

    def test_publication_failure_restores_replaced_trainer_csv(self):
        previous = self.seed_outputs()
        actual_replace = SPECIALIZATIONS.os.replace

        def fail_lua(source, destination):
            if Path(destination) == self.output and str(source).endswith(".tmp"):
                raise OSError("fixture Lua publication failure")
            return actual_replace(source, destination)

        with mock.patch.object(SPECIALIZATIONS.os, "replace", side_effect=fail_lua):
            result, _, stderr, _ = self.run_cli(records=[trainer()])
        self.assertEqual(result, 1)
        self.assertIn("publication failure", stderr)
        self.assert_outputs(previous)


if __name__ == "__main__":
    unittest.main()
