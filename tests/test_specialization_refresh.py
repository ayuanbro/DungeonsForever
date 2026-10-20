"""Read-only client CSV inputs, independent web acquisition and transactional publication."""
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

PIPELINE = Path(__file__).resolve().parents[1] / "df-data-pipeline/_temp"
sys.path.insert(0, str(PIPELINE))
import fc_refresh_specializations as update
from fc_recipe_item_audit import TABLE_FIELDS
REAL_CHILD = update.child
REAL_POPEN = subprocess.Popen


class RefreshTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="df-refresh-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        import fc_pipeline_common as common
        patcher = mock.patch.object(common, 'REPO', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
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
        raw_item = b'ID,ClassID,SubclassID\n1,9,0\n'
        (self.fixture / 'item.csv').write_bytes(raw_item)
        manifest['tables']['item'] = {'sha256': update.sha(raw_item), 'rows': 1,
                                     'url': 'http://localhost/?build=1.60.1.70451'}
        raw_sparse = b'ID,Display_lang,BuyPrice,VendorStackCount,RequiredAbility\n1,Fixture,5,1,0\n'
        (self.fixture / 'itemsparse.csv').write_bytes(raw_sparse)
        manifest['tables']['itemsparse'] = {'sha256': update.sha(raw_sparse), 'rows': 1,
                                           'url': 'http://localhost/?build=1.60.1.70451'}
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
        self.client_keys = ('--prices-csv', '--item-csv', '--recipe-items-csv')
        self.options['--item-csv'].write_bytes(raw_item)
        self.write_csv(self.options['--prices-csv'], update.PRICE_FIELDS, {
            'ItemID': '1', 'Name_enUS': 'Fixture', 'Name_zhTW': '圖紙', 'Name_zhCN': '图纸',
            'BuyPriceCopper': '5', 'VendorStackCount': '1', 'PriceStatus': 'priced',
            'Build': '1.60.1.70451', 'HotfixBuild': '70451',
        })
        self.write_csv(self.options['--recipe-items-csv'], update.RECIPE_ITEM_FIELDS, {
            'RecipeItemID': '1', 'RecipeSpellID': '', 'RequiredAbility': '',
            'Status': 'pending', 'Reason': 'no_teaching_relation', 'LearningPath': '',
            'Build': '1.60.1.70451', 'HotfixBuild': '70451', 'Source': 'fixture',
        })
        self.calls = []
        self.fail_child = None
        self.after_child = None
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(update, "LOCK_PATH", self.root / "locks/update.lock").start()
        self.processes = mock.patch.object(update.subprocess, "Popen", side_effect=AssertionError("external process forbidden")).start()
        mock.patch.object(update, "child", side_effect=self.generate).start()
        self.web = mock.patch.object(update, "collect_pages", return_value={"coverage": {}}).start()

    def write_csv(self, path, fields, row):
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            writer.writerow(row)

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
            self.audited_price_bytes = path('--prices-csv').read_bytes()
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

    def run_update(self, *extra, snapshot=True):
        args = ["--skip-catalog", "--data-dir", str(self.data), "--cache-root", str(self.cache)]
        if snapshot:
            args.extend(['--db2-dir', str(self.fixture)])
        for option, path in self.options.items():
            args.extend([option, str(path)])
        args.extend(extra)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return update.main(args)

    def contents(self):
        return {path: path.read_bytes() for path in self.options.values()}

    def alter_csv(self, option, **changes):
        path = self.options[option]
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            row = next(reader)
        row.update(changes)
        self.write_csv(path, fields, row)

    def directory_link(self, link, destination):
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(destination, target_is_directory=True)
        except OSError as error:
            if os.name != 'nt':
                self.skipTest('directory links are unavailable: %s' % error)
            with mock.patch.object(subprocess, 'Popen', REAL_POPEN):
                result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(destination)],
                                        capture_output=True, text=True, errors='replace')
            if result.returncode:
                self.skipTest('junction creation is unavailable: ' + result.stderr)

    def external_directory(self):
        temporary = tempfile.TemporaryDirectory(prefix='df-refresh-outside-')
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def test_check_stages_every_child_without_publishing_or_moving_baseline(self):
        before = self.contents()
        self.assertEqual(self.run_update("--check"), 0)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / "current.json").exists())
        self.assertEqual(self.calls, ["fc_prof_specializations.py", "fc_recipe_item_audit.py",
                                      "fc_recipe_item_web_audit.py"])
        self.processes.assert_not_called()
        self.assertEqual(list((self.cache / "runs").glob("stage-*")), [])

    def test_online_only_collects_web_evidence_and_never_publishes_source_csv(self):
        original = {self.options[key]: (self.options[key].read_bytes(), self.options[key].stat().st_mtime_ns)
                    for key in self.client_keys}
        snapshot = {path: path.read_bytes() for path in self.fixture.iterdir()}
        self.assertEqual(self.run_update('--apply'), 0)
        self.web.assert_called_once()
        self.processes.assert_not_called()
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in original}, original)
        self.assertEqual({path: path.read_bytes() for path in self.fixture.iterdir()}, snapshot)
        state = json.loads((self.cache / 'current.json').read_bytes())
        self.assertEqual(state['schemaVersion'], 2)
        self.assertEqual(set(state['inputs']), {'prices', 'items', 'recipe_items'})
        self.assertEqual(set(state['outputs']), {'trainers', 'lua', 'audit_csv', 'audit_json', 'web_audit_json'})
        self.assertFalse((self.cache / 'db2').exists())

    def test_existing_legacy_marker_uses_matching_input_hashes_at_new_paths(self):
        self.cache.mkdir()
        old = {'schemaVersion': 1, 'targetBuild': '1.60.1.70451', 'comparisonBaseline': None,
               'db2Snapshot': {'path': str(self.fixture),
                               'manifestSHA256': update.fingerprint(self.fixture / 'manifest.json')},
               'outputs': {name: {'path': str(self.root / 'retired-inputs' / path.name),
                                  'sha256': update.fingerprint(path)}
                           for name, path in zip(('prices', 'items', 'recipe_items'),
                                                 (self.options[key] for key in self.client_keys))}}
        (self.cache / 'current.json').write_bytes(update.json_bytes(old))
        self.assertEqual(self.run_update('--apply', snapshot=False), 0)
        state = json.loads((self.cache / 'current.json').read_bytes())
        self.assertEqual(state['schemaVersion'], 2)
        self.assertEqual(state['inputs']['prices']['path'], str(self.options['--prices-csv']))
        self.assertIsNone(state['comparisonBaseline'])

    def test_wrong_item_snapshot_hash_fails_before_any_web_request(self):
        self.options['--item-csv'].write_bytes(b'ID,ClassID,SubclassID\n1,9,1\n')
        self.assertEqual(self.run_update('--check'), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

    def test_mixed_client_build_or_hotfix_fails_before_any_web_request(self):
        originals = self.contents()
        for option, changes in (
                ('--prices-csv', {'Build': '1.60.1.70000'}),
                ('--prices-csv', {'HotfixBuild': '70000'}),
                ('--recipe-items-csv', {'Build': '1.60.1.70000'}),
                ('--recipe-items-csv', {'HotfixBuild': '70000'})):
            with self.subTest(option=option, changes=changes):
                for path, content in originals.items():
                    path.write_bytes(content)
                self.alter_csv(option, **changes)
                self.assertEqual(self.run_update('--check'), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

    def test_same_build_price_or_ability_from_another_snapshot_is_rejected(self):
        originals = self.contents()
        for option, changes in (('--prices-csv', {'BuyPriceCopper': '999'}),
                                ('--recipe-items-csv', {'RequiredAbility': '20222'})):
            with self.subTest(option=option):
                for path, content in originals.items():
                    path.write_bytes(content)
                self.alter_csv(option, **changes)
                self.assertEqual(self.run_update('--check'), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

    def test_output_alias_to_any_read_only_client_csv_is_rejected(self):
        for key in self.client_keys:
            self.assertEqual(self.run_update('--apply', '--trainer-csv', str(self.options[key])), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

    def test_apply_then_offline_and_online_repeat_leave_unchanged_file_mtimes(self):
        self.assertEqual(self.run_update("--apply"), 0)
        before = self.contents()
        modified = {path: path.stat().st_mtime_ns for path in before}
        self.calls.clear()
        self.assertEqual(self.run_update("--apply", "--offline"), 0)
        self.assertNotIn("export", self.calls)
        self.assertEqual(self.contents(), before)
        self.assertEqual({path: path.stat().st_mtime_ns for path in before}, modified)
        # Source timestamps do not rewrite unchanged derived files.
        manifest = json.loads((self.fixture / "manifest.json").read_bytes())
        manifest["fetchedAt"] = "2026-10-22T00:00:00Z"
        (self.fixture / "manifest.json").write_bytes(update.json_bytes(manifest))
        self.assertEqual(self.run_update("--apply"), 0)
        self.assertEqual(self.contents(), before)
        self.assertEqual({path: path.stat().st_mtime_ns for path in before}, modified)
        self.assertFalse((self.cache / 'db2').exists())
        audit = json.loads(self.options["--audit-json"].read_bytes())
        self.assertEqual(audit["sources"][0]["path"], str(self.options["--recipe-items-csv"]))
        self.assertNotIn("stage-", self.options["--web-audit-json"].read_text())

    def test_failed_generation_never_changes_source_csv_or_publishes_partial_lua(self):
        before = self.contents()
        self.fail_child = "fc_recipe_item_web_audit.py"
        self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / "current.json").exists())
        self.assertFalse((self.cache / 'db2').exists())
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

    def test_concurrent_source_csv_change_is_detected_and_not_overwritten(self):
        def change(script):
            if script == "fc_recipe_item_web_audit.py":
                self.options["--prices-csv"].write_bytes(b"external writer")
        self.after_child = change
        self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.options["--prices-csv"].read_bytes(), b"external writer")
        self.assertEqual(self.options["--output-lua"].read_bytes(), b"old snapshot\n")

    def test_web_collection_uses_frozen_csv_and_detects_a_concurrent_source_change(self):
        source = self.options['--prices-csv']
        original = source.read_bytes()
        def collect(*_args):
            source.write_bytes(b'external writer during web collection')
            return {'coverage': {}}
        self.web.side_effect = collect
        self.assertEqual(self.run_update('--apply'), 1)
        self.assertEqual(self.audited_price_bytes, original)
        self.assertEqual(source.read_bytes(), b'external writer during web collection')
        self.assertEqual(self.options['--output-lua'].read_bytes(), b'old snapshot\n')
        self.assertFalse((self.cache / 'current.json').exists())

    def test_concurrent_derived_output_change_is_not_overwritten(self):
        source_before = {self.options[key]: self.options[key].read_bytes() for key in self.client_keys}
        def change(script):
            if script == 'fc_recipe_item_web_audit.py':
                self.options['--output-lua'].write_bytes(b'external Lua writer')
        self.after_child = change
        self.assertEqual(self.run_update('--apply'), 1)
        self.assertEqual(self.options['--output-lua'].read_bytes(), b'external Lua writer')
        self.assertEqual({path: path.read_bytes() for path in source_before}, source_before)
        self.assertFalse((self.cache / 'current.json').exists())

    def test_current_snapshot_requires_matching_csv_hashes_in_both_web_modes(self):
        self.assertEqual(self.run_update('--check', snapshot=False), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()
        self.assertEqual(self.run_update('--apply'), 0)
        self.calls.clear()
        self.web.reset_mock()
        self.assertEqual(self.run_update('--check', snapshot=False), 0)
        self.assertEqual(self.web.call_count, 1)
        self.assertEqual(self.run_update('--check', '--offline', snapshot=False), 0)
        self.options['--recipe-items-csv'].write_bytes(b'unrelated')
        self.calls.clear()
        self.web.reset_mock()
        for flags in (('--check',), ('--check', '--offline')):
            self.assertEqual(self.run_update(*flags, snapshot=False), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

    def test_lock_is_global_to_checkout_and_conflicting_outputs_are_rejected(self):
        with update.update_lock(update.LOCK_PATH):
            self.assertEqual(self.run_update("--apply"), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.run_update("--output-lua", str(self.options["--prices-csv"])), 1)
        self.assertEqual(self.calls, [])

    def test_target_build_constraint_never_relabels_the_source_snapshot(self):
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

    def test_missing_explicit_baseline_or_required_csv_fails_before_web_requests(self):
        before = self.contents()
        self.assertEqual(self.run_update('--apply', '--baseline-csv', str(self.root / 'absent.csv')), 1)
        self.assertEqual(self.contents(), before)
        for key in self.client_keys:
            path = self.options[key]
            content = path.read_bytes()
            path.unlink()
            self.assertEqual(self.run_update('--check'), 1)
            path.write_bytes(content)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

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

    def test_prepare_returns_complete_batch_without_publishing_or_retaining_stage_paths(self):
        arguments = ['--skip-catalog', '--data-dir', str(self.data),
                     '--cache-root', str(self.cache), '--db2-dir', str(self.fixture)]
        for option, path in self.options.items():
            arguments.extend([option, str(path)])
        args = update.parse_args(arguments)
        before = self.contents()
        report = {}
        outputs, expected = update.prepare_batch(args, report)
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.cache / 'current.json').exists())
        self.assertEqual(set(outputs), {p for key, p in self.options.items() if key not in self.client_keys} | {self.cache / 'current.json'})
        self.assertTrue(all(self.options[key] not in outputs for key in self.client_keys))
        self.assertEqual(report['status'], 'prepared')
        self.assertTrue(all(isinstance(content, bytes) for content in outputs.values()))
        self.assertTrue(all('stage-' not in str(path) for path in expected))
        self.assertEqual(list((self.cache / 'runs').glob('stage-*')), [])
        update.publish_batch(outputs, expected)
        self.assertTrue((self.cache / 'current.json').exists())

    def test_outside_repository_output_is_rejected_before_export_or_cache_creation(self):
        outside = self.root.parent / (self.root.name + '-outside.lua')
        self.assertEqual(self.run_update('--apply', '--output-lua', str(outside)), 1)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.cache.exists())
        self.assertFalse(outside.exists())

    def test_removed_external_service_options_are_rejected_without_any_process(self):
        for option in ('--tool-directory', '--base-url', '--powershell'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                update.parse_args([option, 'unused'])
            self.assertEqual(error.exception.code, 2)
        with self.assertRaises(update.DataError):
            REAL_CHILD('../scripts/export_buyprice/export-item-buy-prices.ps1')
        self.processes.assert_not_called()

    def test_runs_junction_cannot_create_logs_or_staging_outside_repository(self):
        outside = self.external_directory()
        self.directory_link(self.cache / 'runs', outside)
        self.assertEqual(self.run_update('--check'), 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(outside.iterdir()), [])

    def test_snapshot_directory_link_cannot_read_outside_repository(self):
        outside = self.external_directory()
        shutil.copytree(self.fixture, outside / 'snapshot')
        self.directory_link(self.cache / 'db2', outside)
        self.assertEqual(self.run_update('--check', '--db2-dir', str(self.cache / 'db2/snapshot')), 1)
        self.assertEqual(self.calls, [])
        self.web.assert_not_called()

    def test_baseline_junction_cannot_publish_an_external_baseline(self):
        outside = self.external_directory()
        self.directory_link(self.cache / 'baselines', outside)
        with self.assertRaises(ValueError):
            update.save_baseline(self.options['--recipe-items-csv'], self.cache, {})
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
