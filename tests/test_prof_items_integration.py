"""Check importer orchestration and generator read-only behavior in isolation."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "df-prof-pipeline-v1.0/_temp"
CHILDREN = (
    "fc_fetch.py", "fc_parse.py", "fc_zones.py", "fc_fields.py",
    "fc_i18n.py", "fc_gen.py", "fc_prof_items.py", "strip_lua_comments.py",
)
STUB = '''import json
import os
from pathlib import Path
import sys

name = Path(__file__).name
with open(os.environ["DF_PIPELINE_TEST_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps({"script": name, "argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
sys.exit(7 if name == os.environ.get("DF_PIPELINE_TEST_FAIL") else 0)
'''


class ProfItemsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="df-prof-integration-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.scripts = self.directory / "package/_temp"
        self.scripts.mkdir(parents=True)
        shutil.copyfile(PIPELINE / "fc_update.py", self.scripts / "fc_update.py")
        for name in CHILDREN:
            (self.scripts / name).write_text(STUB, encoding="utf-8")
        self.caller = self.directory / "caller with spaces"
        self.caller.mkdir()
        self.log = self.directory / "calls.jsonl"

    def run_pipeline(self, *arguments, fail=""):
        environment = os.environ.copy()
        environment.update(DF_PIPELINE_TEST_LOG=str(self.log),
                           DF_PIPELINE_TEST_FAIL=fail, PYTHONIOENCODING="utf-8",
                           PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [sys.executable, "-B", str(self.scripts / "fc_update.py"), *arguments],
            cwd=self.caller, env=environment, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        calls = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()] \
            if self.log.exists() else []
        return result, calls

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)

    def test_check_orders_import_after_generation_and_forwards_absolute_inputs(self):
        arguments = ["--check", "--offline"]
        inputs = {"--vendors-csv": "inputs/vendors.csv", "--npcs-csv": "输入/npcs.csv",
                  "--prices-csv": "../prices.csv"}
        for option, value in inputs.items():
            arguments.extend((option, value))
        arguments.extend(("--verified-at", "2026-10-20"))
        result, calls = self.run_pipeline(*arguments)
        self.assert_ok(result)
        names = [call["script"] for call in calls]
        self.assertEqual(names, ["fc_fetch.py", "fc_parse.py", "fc_zones.py", "fc_fields.py",
                                 "fc_i18n.py", "fc_gen.py", "fc_prof_items.py", "fc_fields.py"])
        imported = calls[6]["argv"]
        self.assertIn("--dry-run", imported)
        for option, value in inputs.items():
            actual = imported[imported.index(option) + 1]
            self.assertEqual(actual, os.path.abspath(self.caller / value))
            self.assertTrue(os.path.isabs(actual))
            self.assertTrue(all(option not in call["argv"] for call in calls if call is not calls[6]))
        self.assertEqual(imported[imported.index("--verified-at") + 1], "2026-10-20")
        self.assertIn("--dry-run", calls[5]["argv"])
        self.assertIn("--offline", calls[0]["argv"])
        self.assertIn("--offline", calls[2]["argv"])
        self.assertTrue(all(Path(call["cwd"]) == self.scripts for call in calls))

    def test_apply_runs_post_import_audit_then_comment_cleanup(self):
        absolute = self.caller / "prices.csv"
        result, calls = self.run_pipeline("--apply", "--offline", "--prices-csv", str(absolute))
        self.assert_ok(result)
        self.assertTrue(all("--dry-run" not in call["argv"] for call in calls))
        self.assertEqual([call["script"] for call in calls][-3:],
                         ["fc_prof_items.py", "fc_fields.py", "strip_lua_comments.py"])
        self.assertEqual(calls[-1]["argv"], ["--apply"])
        imported = calls[-3]["argv"]
        self.assertEqual(imported[imported.index("--prices-csv") + 1], str(absolute))

    def test_default_mode_checks_without_comment_cleanup(self):
        result, calls = self.run_pipeline("--offline")
        self.assert_ok(result)
        self.assertEqual(calls[-1]["script"], "fc_fields.py")
        self.assertEqual(calls[-2]["argv"], ["--dry-run"])
        self.assertFalse(any(call["script"] == "strip_lua_comments.py" for call in calls))

    def test_apply_and_check_are_mutually_exclusive_before_running_children(self):
        result, calls = self.run_pipeline("--apply", "--check")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_child_failure_stops_before_later_steps_or_cleanup(self):
        for failed in ("fc_gen.py", "fc_prof_items.py"):
            with self.subTest(failed=failed):
                if self.log.exists():
                    self.log.unlink()
                result, calls = self.run_pipeline("--apply", "--offline", fail=failed)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual(calls[-1]["script"], failed)
                self.assertIn("[FAIL]", result.stdout)
                self.assertEqual(sum(call["script"] == "fc_fields.py" for call in calls), 1)
                self.assertFalse(any(call["script"] == "strip_lua_comments.py" for call in calls))

    def test_main_clears_failure_from_an_earlier_invocation(self):
        spec = importlib.util.spec_from_file_location("df_pipeline_repeat_test", PIPELINE / "fc_update.py")
        update = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(update)
        with mock.patch.object(update.subprocess, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()):
            run.return_value.returncode = 7
            self.assertEqual(update.main(["--offline", "--check"]), 1)
            self.assertTrue(update.FAILED)
            run.return_value.returncode = 0
            self.assertEqual(update.main(["--offline", "--check"]), 0)
            self.assertEqual(update.FAILED, [])


class ProfGeneratorDryRunTests(unittest.TestCase):
    def test_actual_generator_dry_run_preserves_existing_outputs_including_comments(self):
        with tempfile.TemporaryDirectory(prefix="df-prof-gen-dry-run-") as directory:
            package = Path(directory) / "package"
            scripts = package / "_temp"
            data = scripts / "_fc/data"
            translations = scripts / "_fc/i18n"
            output = package / "Core/Data"
            for path in (data, translations, output):
                path.mkdir(parents=True)
            for name in ("fc_gen.py", "fc_i18n.py", "strip_comments.py"):
                shutil.copyfile(PIPELINE / name, scripts / name)
            index = {"professions": [], "nav": [], "build": "fixture", "updated": "2026-10-20"}
            (data / "index.json").write_text(json.dumps(index), encoding="utf-8")
            (data / "zone_ids.json").write_text("{}", encoding="utf-8")
            (data / "enchant_ids.json").write_text("{}", encoding="utf-8")
            (translations / "zh.json").write_text("{}", encoding="utf-8")
            before = {}
            for name in ("Data_Professions.lua", "Data_ProfRecipes.lua", "Data_ProfLeveling.lua",
                         "Data_ProfGathering.lua", "Data_ProfVendors.lua"):
                path = output / name
                before[path] = b"-- existing header\r\nlocal preserved = 42 -- keep this comment\r\n"
                path.write_bytes(before[path])
            result = subprocess.run(
                [sys.executable, "-B", str(scripts / "fc_gen.py"), "--dry-run"],
                cwd=directory, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30,
                env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"),
            )
            self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
            self.assertEqual({path: path.read_bytes() for path in output.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
