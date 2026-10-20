"""Exercise the updater's staging/commit boundary without a network or live WTL."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = Path(__file__).resolve().parents[1] / "df-prof-pipeline-v1.0/_temp"
sys.path.insert(0, str(PIPELINE))
import fc_refresh_specializations as update
from fc_recipe_item_audit import TABLE_FIELDS


class RefreshTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="df-refresh-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cache = self.root / "cache"
        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "prof_engineering.json").write_text('{"rows":[]}', encoding="utf-8")
        self.fixture = self.root / "snapshot"
        self.fixture.mkdir()
        manifest = {"schemaVersion": 1, "build": "1.60.1.70451", "hotfixBuild": 70451,
                    "hotfixSHA256": "a" * 64, "useHotfixes": True,
                    "fetchedAt": "2026-10-21T00:00:00Z", "tables": {}}
        for name, fields in TABLE_FIELDS.items():
            content = (",".join(fields) + "\n").encode()
            (self.fixture / (name + ".csv")).write_bytes(content)
            manifest["tables"][name] = {"sha256": update.sha(content), "rows": 0,
                                       "url": "http://localhost/?build=1.60.1.70451"}
        (self.fixture / "manifest.json").write_bytes(update.json_bytes(manifest))
        self.options = {
            "--prices-csv": self.root / "prices.csv", "--item-csv": self.root / "item.csv",
            "--recipe-items-csv": self.root / "recipe-items.csv",
            "--trainer-csv": self.root / "trainers.csv", "--output-lua": self.root / "data.lua",
            "--audit-csv": self.root / "audit.csv", "--audit-json": self.root / "audit.json",
            "--web-audit-json": self.root / "web.json",
        }
        for path in self.options.values():
            path.write_bytes(b"old snapshot\n")
        # The default comparison baseline is opaque to the updater; the audit
        # child owns CSV/build validation.
        self.calls = []
        self.fail_child = None
        self.after_child = None
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(update, "LOCK_PATH", self.root / "locks/update.lock").start()
        mock.patch.object(update, "run_command", side_effect=self.export).start()
        mock.patch.object(update, "child", side_effect=self.generate).start()
        mock.patch.object(update, "collect_pages", return_value={"coverage": {}}).start()

    def export(self, args):
        self.calls.append("export")
        values = [str(value) for value in args]
        shutil.copytree(self.fixture, Path(values[values.index("-LearningSnapshotPath") + 1]))
        for option, content in (
            ("-OutputPath", b"ItemID,Build\n1,1.60.1.70451\n"),
            ("-ItemOutputPath", b"ID,ClassID,SubclassID\n1,9,0\n"),
            ("-RecipeItemOutputPath", b"RecipeItemID,RecipeSpellID,Build\n1,,1.60.1.70451\n"),
        ):
            Path(values[values.index(option) + 1]).write_bytes(content)

    def generate(self, script, *args):
        self.calls.append(script)
        values = [str(value) for value in args]
        def path(flag):
            return Path(values[values.index(flag) + 1])
        if script == self.fail_child:
            raise update.DataError("fixture child failure")
        if script == "fc_prof_specializations.py":
            path("--trainer-csv").write_bytes(b"RecipeSpellID,Status\n1,pending\n")
            path("--output-lua").write_bytes(b"local _, ns = ...\nns.ProfSpecializations = {}\n")
        elif script == "fc_recipe_item_audit.py":
            path("--output-csv").write_bytes(b"ItemID,MappingResolved\n1,false\n")
            path("--summary-json").write_bytes(update.json_bytes({
                "items": 1, "mappingResolved": 0, "stillUnmapped": 1,
                "stillUnmappedClassifications": {"missing_skill_line": 1},
                "sources": [{"path": str(path("--recipe-items-csv"))}],
                "baselineSHA256": update.fingerprint(path("--baseline-csv"))
                if "--baseline-csv" in values else None,
            }))
        elif script == "fc_recipe_item_web_audit.py":
            path("--output-json").write_bytes(update.json_bytes({
                "source": str(path("--recipe-items-csv")), "newMappings": [],
            }))
        else:
            self.fail("unexpected child " + script)
        if self.after_child:
            self.after_child(script)

    def run_update(self, *extra):
        args = ["--skip-catalog", "--data-dir", str(self.data), "--cache-root", str(self.cache)]
        for option, path in self.options.items():
            args.extend([option, str(path)])
        args.extend(extra)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return update.main(args)

    def contents(self):
        return {path: path.read_bytes() for path in self.options.values()}

    def test_check_stages_every_child_without_publishing_or_moving_baseline(self):
        before = self.contents()
        self.assertEqual(self.run_update("--check"), 0)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / "current.json").exists())
        self.assertEqual(self.calls, ["export", "fc_prof_specializations.py",
                                      "fc_recipe_item_audit.py", "fc_recipe_item_web_audit.py"])
        self.assertEqual(list((self.cache / "runs").glob("stage-*")), [])

    def test_apply_then_offline_and_online_repeat_leave_unchanged_file_mtimes(self):
        self.assertEqual(self.run_update("--apply"), 0)
        before = self.contents()
        modified = {path: path.stat().st_mtime_ns for path in before}
        self.calls.clear()
        self.assertEqual(self.run_update("--apply", "--offline"), 0)
        self.assertNotIn("export", self.calls)
        self.assertEqual(self.contents(), before)
        self.assertEqual({path: path.stat().st_mtime_ns for path in before}, modified)
        # A new fetch timestamp alone does not create a second DB2 snapshot.
        manifest = json.loads((self.fixture / "manifest.json").read_bytes())
        manifest["fetchedAt"] = "2026-10-22T00:00:00Z"
        (self.fixture / "manifest.json").write_bytes(update.json_bytes(manifest))
        self.assertEqual(self.run_update("--apply"), 0)
        self.assertEqual(self.contents(), before)
        self.assertEqual({path: path.stat().st_mtime_ns for path in before}, modified)
        snapshots = list((self.cache / "db2/1.60.1.70451").glob("*/manifest.json"))
        self.assertEqual(len(snapshots), 1)
        audit = json.loads(self.options["--audit-json"].read_bytes())
        self.assertEqual(audit["sources"][0]["path"], str(self.options["--recipe-items-csv"]))
        self.assertNotIn("stage-", self.options["--web-audit-json"].read_text())

    def test_failed_generation_never_publishes_exported_prices_or_partial_lua(self):
        before = self.contents()
        self.fail_child = "fc_recipe_item_web_audit.py"
        self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / "current.json").exists())
        self.assertTrue(list((self.cache / "db2").glob("*/*/manifest.json")))
        self.assertEqual(json.loads((self.cache / "runs/last-run.json").read_bytes())["status"], "failed")

    def test_batch_replace_failure_rolls_back_all_outputs_and_commit_marker(self):
        before = self.contents()
        real_replace = update.os.replace
        failed = False
        def replace(source, destination):
            nonlocal failed
            if Path(destination) == self.options["--audit-csv"] and not failed:
                failed = True
                raise OSError("fixture replace failure")
            return real_replace(source, destination)
        with mock.patch.object(update.os, "replace", side_effect=replace):
            self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / "current.json").exists())

    def test_concurrent_output_change_is_detected_and_not_overwritten(self):
        def change(script):
            if script == "fc_recipe_item_web_audit.py":
                self.options["--prices-csv"].write_bytes(b"external writer")
        self.after_child = change
        self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.options["--prices-csv"].read_bytes(), b"external writer")
        self.assertEqual(self.options["--output-lua"].read_bytes(), b"old snapshot\n")

    def test_offline_rejects_unrelated_snapshot_and_online_override(self):
        self.assertEqual(self.run_update("--offline", "--apply"), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.run_update("--apply"), 0)
        self.options["--recipe-items-csv"].write_bytes(b"unrelated")
        self.calls.clear()
        self.assertEqual(self.run_update("--offline", "--apply"), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.run_update("--db2-dir", str(self.fixture)), 1)

    def test_lock_is_global_to_checkout_and_conflicting_outputs_are_rejected(self):
        with update.update_lock():
            self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.run_update("--output-lua", str(self.options["--prices-csv"])), 1)
        self.assertEqual(self.calls, [])

    def test_target_build_constraint_never_relabels_new_export(self):
        before = self.contents()
        self.assertEqual(self.run_update("--apply", "--build", "1.60.1.70000"), 1)
        self.assertEqual(self.contents(), before)

    def test_external_offline_snapshot_cannot_be_overwritten_by_outputs(self):
        before = (self.fixture / "manifest.json").read_bytes()
        self.assertEqual(self.run_update("--apply", "--offline", "--db2-dir", str(self.fixture),
                                        "--audit-json", str(self.fixture / "manifest.json")), 1)
        self.assertEqual((self.fixture / "manifest.json").read_bytes(), before)

    def test_snapshot_change_between_children_aborts_publication(self):
        def change(script):
            if script == "fc_recipe_item_web_audit.py":
                with (self.fixture / "spellname.csv").open("ab") as stream:
                    stream.write(b"100,changed\n")
        self.after_child = change
        before = self.contents()
        self.assertEqual(self.run_update("--apply", "--offline", "--db2-dir", str(self.fixture)), 1)
        self.assertEqual(self.contents(), before)

    def test_missing_explicit_baseline_fails_but_first_run_without_previous_csv_works(self):
        before = self.contents()
        self.assertEqual(self.run_update("--apply", "--baseline-csv", str(self.root / "absent.csv")), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.contents(), before)
        self.options["--recipe-items-csv"].unlink()
        self.assertEqual(self.run_update("--apply"), 0)
        state = json.loads((self.cache / "current.json").read_bytes())
        self.assertIsNone(state["comparisonBaseline"])

    def test_saved_baseline_change_after_audit_aborts_publication(self):
        def change(script):
            if script == "fc_recipe_item_web_audit.py":
                baseline = next((self.cache / "baselines").glob("*.csv"))
                baseline.write_bytes(b"changed cached baseline")
        self.after_child = change
        before = self.contents()
        self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / "current.json").exists())

    def test_new_snapshot_cannot_disagree_with_build_hotfix_identity(self):
        path = self.fixture / "manifest.json"
        original = json.loads(path.read_bytes())
        for field, value in (("hotfixBuild", 70000), ("useHotfixes", False),
                             ("hotfixSHA256", "missing"), ("schemaVersion", 2)):
            with self.subTest(field=field):
                manifest = dict(original, **{field: value})
                path.write_bytes(update.json_bytes(manifest))
                before = self.contents()
                self.assertEqual(self.run_update("--apply", "--offline", "--db2-dir", str(self.fixture)), 1)
                self.assertEqual(self.contents(), before)


if __name__ == "__main__":
    unittest.main()
