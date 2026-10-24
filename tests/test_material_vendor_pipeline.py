"""Material evidence refresh participates in the unified publication boundary."""
import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

import test_prof_items_integration as integration
import test_pipeline_preview_package as previews

pipeline, common = integration.pipeline, integration.common


class MaterialPipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = integration.UnifiedIntegrationTests('test_check_runs_every_step_and_does_not_publish')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.material_patch.stop()
        self.prepared = []
        self.collector = mock.Mock(side_effect=self.prepare)
        self.module = SimpleNamespace(prepare_batch=self.collector)
        self.module_patch = mock.patch.dict(sys.modules, {'fc_material_vendors': self.module})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def prepare(self, options, report):
        self.prepared.append(options)
        report.update(status='fixture', offline=options.offline)
        digest = 'a' * 64
        snapshot = {'schemaVersion': 1, 'eligibility': {'fingerprint': digest, 'items': 1, 'offers': 0}}
        lua = ('local _,ns=...\nns.ProfMaterialSupplyMeta={schemaVersion=1,gameFlavor="forever",fingerprint="%s"}\n'
               'ns.ProfMaterialSupply={[2320]={offers={}}}\n' % digest).encode('utf-8')
        return ({options.material_snapshot: common.json_bytes(snapshot), options.material_output_lua: lua},
                [{'role': 'frozen-input', 'path': str(p), 'sha256': common.sha(b)}
                 for p, b in options.input_overrides.items()])

    def invoke(self, *flags):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return pipeline.main(list(flags))

    def test_full_online_entry_refreshes_material_evidence_and_freezes_inputs(self):
        self.assertEqual(self.invoke('--check'), 0)
        self.collector.assert_called_once()
        options = self.prepared[0]
        self.assertFalse(options.offline)
        self.assertIsNone(options.material_provider)
        self.assertIsNone(options.material_headless)
        self.assertIsNone(options.material_channel)
        self.assertTrue(options.data_dir.is_relative_to(self.fixture.here / '_fc/cache/runs'))
        self.assertIn(self.fixture.here / '_fc/maintenance/material-vendors.json', options.input_overrides)
        self.assertIn(self.fixture.data / 'material-vendors.json', options.input_overrides)
        self.assertEqual(self.fixture.snapshot(), self.fixture.before)

    def test_browser_proxy_profile_and_channel_flags_are_forwarded_without_launching(self):
        profile = self.fixture.root / '.pipeline-runtime/material-profile'
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check',
                                     '--material-provider', 'chrome', '--material-proxy', 'http://127.0.0.1:9876',
                                     '--material-chrome-profile', str(profile), '--material-channel', 'msedge',
                                     '--no-material-headless'), 0)
        options = self.prepared[0]
        self.assertEqual(options.material_provider, 'chrome')
        self.assertEqual(options.material_proxy, 'http://127.0.0.1:9876')
        self.assertEqual(options.material_chrome_profile, profile.resolve())
        self.assertEqual(options.material_channel, 'msedge')
        self.assertIs(options.material_headless, False)
        self.assertFalse(profile.exists())

    def test_explicit_headless_true_and_live_progress_callback(self):
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check', '--material-headless'), 0)
        options = self.prepared[0]
        self.assertIs(options.material_headless, True)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            options.material_progress('material NPC 3364: ok')
        self.assertIn('material NPC 3364: ok', stream.getvalue())

    def test_browser_profile_outside_repository_is_rejected_before_collection(self):
        outside = self.fixture.root.parent / 'outside-material-profile'
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check',
                                     '--material-chrome-profile', str(outside)), 1)
        self.collector.assert_not_called()
        self.assertFalse(outside.exists())

    def test_materials_only_replays_offline_without_other_generators(self):
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in pipeline.CSV_INPUTS.values()}
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check'), 0)
        self.assertEqual(self.fixture.steps, ['validate'])
        self.assertTrue(self.prepared[0].offline)
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}, before)

    def test_materials_only_does_not_require_recipe_or_merchant_csvs(self):
        for key, path in pipeline.CSV_INPUTS.items():
            if key != 'prices_csv':
                path.unlink()
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check'), 0)
        self.assertTrue(self.prepared)

    def test_offline_missing_snapshot_stops_before_collection(self):
        (self.fixture.data / 'material-vendors.json').unlink()
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check'), 1)
        self.collector.assert_not_called()

    def test_check_can_stage_registry_and_lua_without_publishing(self):
        preview = self.fixture.root / '.pipeline-runtime/material-preview'
        self.assertEqual(self.invoke('--materials-only', '--offline', '--check', '--stage-dir', str(preview)), 0)
        manifest = json.loads((preview / 'preview-manifest.json').read_bytes())
        self.assertIn('Core/Data/Data_ProfMaterialSupply.lua', manifest['files'])
        self.assertIn('df-data-pipeline/_temp/_fc/data/material-vendors.json', manifest['files'])
        self.assertEqual(self.fixture.marker.read_bytes(), b'old marker')
        self.assertEqual((self.fixture.data / 'material-vendors.json').read_bytes(),
                         b'{"schemaVersion":1,"items":{}}')

    def test_materials_only_package_is_allowed_with_its_official_runtime_override(self):
        target = self.fixture.root / 'dist/materials.zip'
        def packaged(destination, outputs, expected):
            self.assertEqual(destination, target)
            self.assertEqual(set(outputs), {self.fixture.data / 'material-vendors.json',
                                            self.fixture.official / 'Data_ProfMaterialSupply.lua'})
            self.assertEqual(self.fixture.steps, ['validate'])
            return {'sha256': 'c' * 64, 'published': False}
        with mock.patch.object(previews.package, 'build_install_zip', side_effect=packaged) as build:
            self.assertEqual(self.invoke('--materials-only', '--offline', '--check', '--package-zip', str(target)), 0)
        build.assert_called_once()
        self.assertEqual(self.fixture.marker.read_bytes(), b'old marker')

    def test_collector_cannot_publish_raw_cache_or_another_dataset(self):
        original = self.prepare
        def invalid(options, report):
            outputs, seen = original(options, report)
            outputs[options.material_cache_root / 'npc.html'] = b'raw page'
            return outputs, seen
        self.collector.side_effect = invalid
        with mock.patch.object(common, 'publish_batch') as publish:
            self.assertEqual(self.invoke('--materials-only', '--offline', '--apply'), 1)
        publish.assert_not_called()
        self.assertEqual(self.fixture.snapshot(), self.fixture.before)

    def test_registry_fingerprint_mismatch_blocks_the_whole_batch(self):
        original = self.prepare
        def invalid(options, report):
            outputs, seen = original(options, report)
            data = json.loads(outputs[options.material_snapshot])
            data['eligibility']['fingerprint'] = 'b' * 64
            outputs[options.material_snapshot] = common.json_bytes(data)
            return outputs, seen
        self.collector.side_effect = invalid
        with mock.patch.object(common, 'publish_batch') as publish:
            self.assertEqual(self.invoke('--materials-only', '--offline', '--apply'), 1)
        publish.assert_not_called()
        self.assertEqual(self.fixture.snapshot(), self.fixture.before)

    def test_string_item_or_npc_lookup_keys_are_rejected(self):
        original = self.prepare
        for source in ('ns.ProfMaterialSupply={["2320"]={offers={}}}',
                       'ns.ProfMaterialSupply={[2320]={offers={["3364"]={}}}}'):
            with self.subTest(source=source):
                def invalid(options, report):
                    outputs, seen = original(options, report)
                    text = outputs[options.material_output_lua].decode('utf-8')
                    text = text.replace('ns.ProfMaterialSupply={[2320]={offers={}}}', source)
                    outputs[options.material_output_lua] = text.encode('utf-8')
                    return outputs, seen
                self.collector.side_effect = invalid
                with mock.patch.object(common, 'publish_batch') as publish:
                    self.assertEqual(self.invoke('--materials-only', '--offline', '--apply'), 1)
                publish.assert_not_called()

    def test_config_changed_during_collection_blocks_both_outputs(self):
        original = self.prepare
        def changed(options, report):
            outputs, seen = original(options, report)
            options.material_config.write_bytes(b'{"changedByOtherWriter":true}')
            return outputs, seen
        self.collector.side_effect = changed
        with mock.patch.object(common, 'publish_batch') as publish:
            self.assertEqual(self.invoke('--materials-only', '--offline', '--apply'), 1)
        publish.assert_not_called()
        self.assertFalse((self.fixture.official / 'Data_ProfMaterialSupply.lua').exists())
        self.assertEqual(self.fixture.marker.read_bytes(), b'old marker')

    def test_publish_failure_restores_registry_and_keeps_old_lua(self):
        registry = self.fixture.data / 'material-vendors.json'
        lua = self.fixture.official / 'Data_ProfMaterialSupply.lua'
        lua.write_bytes(b'local _,ns=...\nns.ProfMaterialSupply={}\n')
        previous = registry.read_bytes(), lua.read_bytes(), self.fixture.marker.read_bytes()
        replace = common.os.replace
        def fail(source, target):
            if Path(target) == lua and Path(source).name.startswith('.df-publish-'):
                raise OSError('injected material Lua publication failure')
            return replace(source, target)
        with mock.patch.object(common.os, 'replace', side_effect=fail):
            self.assertEqual(self.invoke('--materials-only', '--offline', '--apply'), 1)
        self.assertEqual((registry.read_bytes(), lua.read_bytes(), self.fixture.marker.read_bytes()), previous)

    def test_material_scope_does_not_allow_another_runtime_output(self):
        for target in (self.fixture.official / 'Data_ProfItems.lua',
                       self.fixture.root / 'Core/ProfEconomy.lua'):
            with self.subTest(target=target):
                self.assertEqual(self.invoke('--materials-only', '--offline', '--check',
                                             '--material-output-lua', str(target)), 1)
        self.collector.assert_not_called()

    def test_raw_cache_cannot_be_written_under_runtime_or_readonly_inputs(self):
        for target in (self.fixture.official / 'cache', self.fixture.here / '_fc/inputs/cache',
                       self.fixture.data / 'raw-cache'):
            with self.subTest(target=target):
                self.assertEqual(self.invoke('--materials-only', '--offline', '--check',
                                             '--material-cache-root', str(target)), 1)
                self.assertFalse(target.exists())
        self.collector.assert_not_called()


class MaterialPackageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = previews.PreviewPackageTests('test_staged_data_goes_into_install_zip_without_touching_checkout')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.toc = self.fixture.root / 'DungeonsForever.toc'
        self.toc.write_bytes(self.toc.read_bytes() + b'Core/Data/Data_ProfMaterialSupply.lua\n')
        self.lua = self.fixture.root / 'Core/Data/Data_ProfMaterialSupply.lua'

    def test_preview_packages_first_material_lua_at_actual_toc_path(self):
        candidate = b'local _,ns=...\nns.ProfMaterialSupply={}\n'
        report = previews.package.build_install_zip(self.fixture.zip, {self.lua: candidate}, {self.lua: None})
        self.assertFalse(self.lua.exists())
        self.assertIn('Core/Data/Data_ProfMaterialSupply.lua', report['dataOverrides'])
        with zipfile.ZipFile(self.fixture.zip) as archive:
            self.assertEqual(archive.read('DungeonsForever/Core/Data/Data_ProfMaterialSupply.lua'), candidate)

    def test_material_output_created_while_packaging_cannot_be_adopted(self):
        original = previews.package.runtime_files
        def changed(*args, **kwargs):
            files = original(*args, **kwargs)
            self.lua.write_bytes(b'created by another writer')
            return files
        with mock.patch.object(previews.package, 'runtime_files', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during packaging'):
                previews.package.build_install_zip(self.fixture.zip, {self.lua: b'staged candidate'})
        self.assertFalse(self.fixture.zip.exists())


if __name__ == '__main__':
    unittest.main()
