"""Unified entrypoint boundaries: one transaction after every generation step."""
import argparse
import contextlib
import importlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'df-data-pipeline/_temp'))
import fc_pipeline as pipeline
import fc_pipeline_common as common
import fc_gen
import fc_locales
import fc_prof_items as items
import fc_refresh_specializations as refresh


class UnifiedIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / '.pipeline-runtime/tmp'
        temporary_root.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='unified-中文 ', dir=temporary_root)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.here = self.root / 'df-data-pipeline/_temp'
        self.data = self.here / '_fc/data'
        self.official = self.root / 'Core/Data'
        for path in (self.data, self.official, self.here / '_fc/i18n', self.here / '_fc/maintenance'):
            path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(mock.patch.stopall)
        for module, values in (
            (common, {'REPO': self.root, 'LOCK_PATH': self.here / '_fc/cache/.pipeline-state/update.lock'}),
            (pipeline, {'REPO': self.root, 'PACKAGE': self.here.parent, 'HERE': self.here,
                        'OFFICIAL': self.official, 'DATA_DIR': self.data}),
        ):
            for name, value in values.items():
                mock.patch.object(module, name, value).start()
        for name in pipeline.BASE_FILES:
            (self.official / name).write_bytes(b'local _,ns=...\nns.Existing={ [1]=true }\n')
        self.marker = self.here / '_fc/cache/.pipeline-state/current.json'
        self.marker.parent.mkdir(parents=True)
        self.marker.write_bytes(b'old marker')
        self.inputs = {
            'index.json': b'{"build":"fixture"}', 'prof_engineering.json': b'{"rows":[]}',
            'zone_ids.json': b'{}', 'recipe-item-link-audit-summary.json': b'{"audit":"old"}',
        }
        for name, content in self.inputs.items():
            (self.data / name).write_bytes(content)
        (self.here / '_fc/i18n/zh.json').write_bytes(b'{}')
        for name in ('professions.json', 'locales.json'):
            (self.here / '_fc/maintenance' / name).write_bytes(b'{"schema":1}')
        inputs = {}
        for name in ('vendors_csv', 'npcs_csv', 'prices_csv', 'item_csv', 'recipe_items_csv'):
            source = self.here / '_fc/inputs' / (name + '.csv')
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b'fixture\n')
            inputs[name] = source
        mock.patch.object(pipeline, 'CSV_INPUTS', inputs).start()
        self.steps = []
        self.failure = None
        mock.patch.object(pipeline, 'run_step', side_effect=self.step).start()
        mock.patch.object(fc_gen, 'render_data', side_effect=self.base).start()
        mock.patch.object(fc_gen, 'render_catalog', return_value={'prof_engineering.json': b'{"rows":[]}',
                                                                 'enchant_ids.json': b'{}'}).start()
        mock.patch.object(fc_locales, 'render_locales', side_effect=self.languages).start()
        mock.patch.object(refresh, 'prepare_batch', side_effect=self.specializations).start()
        mock.patch.object(items, 'build_batch', side_effect=self.items).start()
        mock.patch.object(pipeline, 'validate_batch', side_effect=self.validate).start()
        self.before = self.snapshot()

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*')
                if p.is_file() and '/cache/' not in p.as_posix() and '/reports/' not in p.as_posix()}

    def point(self, name):
        self.steps.append(name)
        if self.failure == name:
            raise common.PipelineError('injected ' + name)

    def step(self, script, arguments, environment):
        self.point(script)
        if script == 'fc_parse.py':
            # A staged old audit must never overwrite the newly prepared audit.
            self.assertTrue(Path(environment['DF_PIPELINE_DATA_DIR']).is_relative_to(self.root))
        self.assertTrue(Path(environment['DF_PIPELINE_REPORT_DIR']).is_relative_to(self.root))

    def base(self, data, **kwargs):
        self.point('base')
        return {name: (self.official / name).read_bytes() for name in pipeline.BASE_FILES}

    def specializations(self, args, report):
        self.point('specializations')
        return {self.data / 'recipe-item-link-audit-summary.json': b'{"audit":"new"}'}, {}

    def items(self, args):
        self.point('items')
        if not args.from_csv:
            self.assertIn(self.official / 'Data_ProfVendors.lua', args.input_overrides)
        return {args.items_lua: b'local _,ns=...\nns.ProfItems={ [1]={item_id=1} }\n'}, {}

    def languages(self, base, baseline, **kwargs):
        self.point('languages')
        self.assertEqual(set(base), set(pipeline.BASE_FILES))
        return {locale + '/' + name: b'local _,ns=...\nns.Locale={ [1]=true }\n'
                for locale in ('enUS', 'zhTW') for name in pipeline.BASE_FILES}

    def validate(self, outputs, before, report, full=True, approved_removals=(), catalog_identities=None):
        self.point('validate')
        self.assertEqual(outputs.get(self.data / 'recipe-item-link-audit-summary.json', b'{"audit":"new"}'),
                         b'{"audit":"new"}')

    def invoke(self, *flags):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return pipeline.main(['--offline', *flags])

    def test_check_runs_every_step_and_does_not_publish(self):
        with mock.patch.object(common, 'publish_batch') as publish:
            self.assertEqual(self.invoke('--check'), 0)
        publish.assert_not_called()
        self.assertEqual(self.steps, ['fc_fetch.py', 'fc_parse.py', 'fc_zones.py', 'fc_fields.py',
                                     'fc_i18n.py', 'base', 'specializations', 'items', 'languages', 'validate'])
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(self.marker.read_bytes(), b'old marker')

    def test_apply_publishes_only_after_validation_and_keeps_new_audit(self):
        real = common.publish_batch
        def publish(outputs, expected):
            self.assertEqual(self.steps[-1], 'validate')
            return real(outputs, expected)
        with mock.patch.object(common, 'publish_batch', side_effect=publish) as committed:
            self.assertEqual(self.invoke('--apply'), 0)
        self.assertEqual(committed.call_count, 1)
        self.assertEqual((self.data / 'recipe-item-link-audit-summary.json').read_bytes(), b'{"audit":"new"}')
        self.assertTrue((self.official / 'enUS/Data_ProfRecipes.lua').exists())
        self.assertNotEqual(self.marker.read_bytes(), b'old marker')

    def test_every_failure_before_commit_keeps_the_old_batch(self):
        for name in ('fc_fetch.py', 'fc_parse.py', 'fc_zones.py', 'fc_fields.py', 'fc_i18n.py',
                     'base', 'specializations', 'items', 'languages', 'validate'):
            with self.subTest(name=name), mock.patch.object(common, 'publish_batch') as publish:
                self.failure = name
                self.assertEqual(self.invoke('--apply'), 1)
                publish.assert_not_called()
                self.assertEqual(self.snapshot(), self.before)

    def test_marker_modified_during_generation_is_not_overwritten(self):
        original = self.validate
        def changed(*args, **kwargs):
            original(*args, **kwargs)
            self.marker.write_bytes(b'external change')
        with mock.patch.object(pipeline, 'validate_batch', side_effect=changed):
            self.assertEqual(self.invoke('--apply'), 1)
        self.assertEqual(self.marker.read_bytes(), b'external change')
        self.assertEqual(self.snapshot(), self.before)

    def test_new_output_created_during_generation_is_not_adopted(self):
        original = self.languages
        path = self.official / 'enUS/Data_ProfRecipes.lua'
        def changed(*args, **kwargs):
            outputs = original(*args, **kwargs)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'external output')
            return outputs
        with mock.patch.object(fc_locales, 'render_locales', side_effect=changed):
            self.assertEqual(self.invoke('--apply'), 1)
        self.assertEqual(path.read_bytes(), b'external output')

    def test_csv_mode_does_not_enter_network_base_or_language_steps(self):
        source = self.data / 'DataProfItems.csv'
        source.write_bytes(b'fixture')
        self.assertEqual(self.invoke('--check', '--from-csv', str(source)), 0)
        self.assertEqual(self.steps, ['items', 'validate'])

    def test_specializations_only_keeps_its_existing_scope(self):
        self.assertEqual(self.invoke('--check', '--specializations-only'), 0)
        self.assertEqual(self.steps, ['specializations', 'validate'])

    def test_check_can_retain_validated_outputs_without_publishing(self):
        preview = self.root / '.pipeline-runtime/preview'
        with mock.patch.object(common, 'publish_batch') as publish:
            self.assertEqual(self.invoke('--check', '--stage-dir', str(preview)), 0)
        publish.assert_not_called()
        self.assertTrue((preview / 'preview-manifest.json').is_file())
        self.assertEqual((preview / 'Core/Data/Data_ProfItems.lua').read_bytes(),
                         b'local _,ns=...\nns.ProfItems={ [1]={item_id=1} }\n')
        self.assertEqual(self.marker.read_bytes(), b'old marker')
        self.assertEqual((self.data / 'recipe-item-link-audit-summary.json').read_bytes(), b'{"audit":"old"}')

    def test_invalid_paths_and_colliding_destinations_fail_before_steps(self):
        for options in [('--cache-dir', str(self.root.parent / 'outside')),
                        ('--items-lua', str(self.marker)),
                        ('--from-csv', str(self.data / 'fixture.csv'), '--items-lua', str(self.root / 'Core/ProfEconomy.lua')),
                        ('--from-csv', str(self.data / 'fixture.csv'), '--items-lua', str(self.official / 'Data_ProfSpecializations.lua')),
                        ('--from-csv', str(self.data / 'fixture.csv'), '--items-lua', str(self.here.parent / 'Core/Data/Data_Professions.lua')),
                        ('--prices-csv', str(self.data / 'collision.csv'), '--trainer-csv', str(self.data / 'collision.csv'))]:
            with self.subTest(options=options):
                self.assertEqual(self.invoke('--check', *options), 1)
                self.assertFalse(self.steps)


class PreservationTests(unittest.TestCase):
    def test_sparse_lua_tuple_can_be_filled_without_record_loss(self):
        self.assertEqual(pipeline.missing_records({2: 1453, 3: 53, 4: 74.2}, [1519, 1453, 53, 74.2]), [])

    def test_missing_stable_recipe_is_reported(self):
        self.assertTrue(pipeline.missing_records([[100, 20], [101, 21]], [[100, 20]]))

    def test_bad_lua_is_an_actionable_validation_error(self):
        with self.assertRaisesRegex(ValueError, 'Lua validation failed'):
            common.raw_namespace([('broken.lua', b'local = broken')])


if __name__ == '__main__':
    unittest.main()
