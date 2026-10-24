"""Preserve the complete maintained baseline while replaying old source inputs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'df-data-pipeline/_temp'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fc_gen
import fc_maintenance as maintenance


class PipelineMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = maintenance.read_manifest()
        _, cls.active_manifest = fc_gen.revision_inputs(SCRIPTS / '_fc/data')
        cls.outputs = fc_gen.render_data(SCRIPTS / '_fc/data')
        cls.model = maintenance.load_sources(cls.outputs)

    def temporary(self):
        directory = tempfile.TemporaryDirectory(prefix='.pipeline-maintenance-test-', dir=ROOT)
        self.addCleanup(directory.cleanup)
        return Path(directory.name)

    def test_complete_six_file_baseline_replays_semantic_fingerprint(self):
        self.assertEqual(set(self.outputs), set(maintenance.FILES))
        self.assertEqual(maintenance.semantic_sha(self.model),
                         self.active_manifest['baseline_semantic_sha256'])
        professions = self.model['Data_Professions.lua']['ProfData']
        self.assertEqual(professions['build'], self.active_manifest['provenance']['target_build'])
        expected_updated = ('2026-10-11' if self.active_manifest.get('revision', 1) == 1
                            else self.active_manifest['provenance']['rebase']['reviewed_source_updated'])
        self.assertEqual(professions['updated'], expected_updated)

    def test_manual_professions_additions_suppressions_and_order_survive(self):
        ns = self.model['Data_ProfRecipes.lua']
        self.assertEqual(maintenance._array(ns['ProfRecipeKeys']), [
            'alchemy', 'blacksmithing', 'enchanting', 'engineering',
            'leatherworking', 'tailoring', 'cooking', 'poisons', 'comprehension'])
        recipes = ns['ProfRecipes']
        self.assertNotIn('first-aid', recipes)
        self.assertTrue(all(not value.get('favor') for slug, value in recipes.items()
                            if slug != 'enchanting'))
        self.assertEqual(len(recipes['enchanting']['favor']), 40)
        self.assertEqual(len(recipes['poisons']['rows']), 26)
        self.assertEqual(len(recipes['comprehension']['rows']), 18)
        rows = {row[1]: row for row in recipes['engineering']['rows'].values()}
        self.assertEqual(rows[1308182][2], 280309)
        self.assertEqual(rows[12722][8], 240)
        self.assertEqual(len(recipes['enchanting']['enchants']), 169)

    def test_normalization_is_lossless_including_shop_nodes_and_positional_holes(self):
        self.assertEqual(maintenance.denormalize(maintenance.normalize(self.model)), self.model)
        leveling = self.model['Data_ProfLeveling.lua']['ProfLeveling']
        self.assertTrue(leveling['alchemy']['shopping'])
        self.assertTrue(leveling['enchanting']['rinfo'])
        self.assertTrue(self.model['Data_ProfGathering.lua']['ProfGathering'])

    def test_recipe_output_retains_lazy_selective_prewarming_contract(self):
        runtime = maintenance.lua_runtime()
        ns = runtime.table()
        runtime.eval('function(src,n) assert(loadstring(src))(nil,n) end')(
            self.outputs['Data_ProfRecipes.lua'].decode('utf-8'), ns)
        rawget = runtime.eval('rawget')
        self.assertIsNone(rawget(ns.ProfRecipes, 'alchemy'))
        self.assertIsNone(rawget(ns.ProfRecipes, 'engineering'))
        ns.EnsureProfRecipes(runtime.table_from(['engineering']))
        self.assertIsNone(rawget(ns.ProfRecipes, 'alchemy'))
        self.assertIsNotNone(rawget(ns.ProfRecipes, 'engineering'))
        ns.EnsureProfRecipes()
        self.assertEqual(len(list(ns.ProfRecipes.items())), 9)

    def test_three_way_merge_is_idempotent_and_keeps_unrelated_changes(self):
        base = {'rows': {'spell:1': {'count': 1, 'learn': 10}}}
        local = {'rows': {'spell:1': {'count': 2, 'learn': 10}, 'item:12': {'count': 1}}}
        changes = maintenance.make_changes(base, local)
        incoming = copy.deepcopy(base)
        incoming['rows']['spell:1']['learn'] = 20
        output = maintenance.apply_changes(incoming, changes)
        self.assertEqual(output['rows']['spell:1'], {'count': 2, 'learn': 20})
        self.assertIn('item:12', output['rows'])
        self.assertEqual(maintenance.apply_changes(output, changes), output)
        self.assertEqual(incoming['rows']['spell:1']['count'], 1)

    def test_conflict_blocks_every_change_and_does_not_mutate_input(self):
        base = {'rows': {'spell:1': {'count': 1}}}
        local = {'rows': {'spell:1': {'count': 2}}, 'new': {'data': 42}}
        incoming = {'rows': {'spell:1': {'count': 3}}}
        before = copy.deepcopy(incoming)
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'conflicts'):
            maintenance.apply_changes(incoming, maintenance.make_changes(base, local))
        self.assertEqual(incoming, before)

    def test_missing_empty_and_null_are_distinct(self):
        base = {'removed': {}, 'null': None, 'number': {10: 'ten'}}
        target = {'null': {}, 'number': {10: 'changed'}, 'added': None}
        changes = maintenance.make_changes(base, target)
        self.assertEqual(maintenance.apply_changes(base, changes), target)
        self.assertEqual(maintenance.unpack(maintenance.pack(target)), target)

    def test_stable_keys_distinguish_zero_spell_comprehension_scrolls(self):
        self.assertNotEqual(maintenance.stable_key('rows', {'spell': 0, 'id': 211780}),
                            maintenance.stable_key('rows', {'spell': 0, 'id': 211785}))
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'duplicate stable key'):
            maintenance.normalize({'Data_ProfRecipes.lua': {'ProfRecipes': {'x': {
                'rows': {1: {1: 1, 2: 2}, 2: {1: 1, 2: 2}}}}}})

    def test_renderer_preserves_large_number_keys_sparse_arrays_and_control_text(self):
        source = {'Table': {987654321: {1: '中文\x00\x01\n"\\', 3: False}, 'count': 4}}
        encoded = maintenance.render_namespace('test.lua', source)
        self.assertLess(len(encoded), 250)
        self.assertEqual(maintenance.load_sources({'test.lua': encoded})['test.lua'], source)

    def test_vendor_importer_accepts_nil_location_slots_without_losing_coordinates(self):
        spec = importlib.util.spec_from_file_location('maintenance_items_importer',
                                                     SCRIPTS / 'fc_prof_items.py')
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
        result, stats = importer.update_vendors(self.outputs['Data_ProfVendors.lua'].decode('utf-8'), [])
        actual = maintenance.load_sources({'Data_ProfVendors.lua': result})
        expected = self.model['Data_ProfVendors.lua']['ProfVendors']
        self.assertEqual(actual['Data_ProfVendors.lua']['ProfVendors'], expected)
        self.assertEqual(stats['vendorLocations'], len(expected))

    def test_effective_catalog_retains_every_original_evidence_field_and_row(self):
        output = fc_gen.render_catalog(SCRIPTS / '_fc/data')
        for source in (SCRIPTS / '_fc/data').glob('prof_*.json'):
            original = json.loads(source.read_text(encoding='utf-8'))
            effective = json.loads(output[source.name])
            for field, value in original.items():
                if field not in ('rows', 'enchants', 'crafted'):
                    self.assertEqual(effective[field], value, (source.name, field))
                    continue
                self.assertGreaterEqual(len(effective[field]), len(value))
                for index, row in enumerate(value):
                    for key, old in row.items():
                        current = effective[field][index][key]
                        if key in ('spell', 'id', 'created') and not old:
                            self.assertTrue(current == old or isinstance(current, int) and current > 0)
                        else:
                            self.assertEqual(current, old, (source.name, field, index, key))
        self.assertEqual(output['enchant_ids.json'], (SCRIPTS / '_fc/data/enchant_ids.json').read_bytes())
        self.assertEqual(len(json.loads(output['prof_first-aid.json'])['rows']), 31)
        self.assertTrue(json.loads(output['prof_alchemy.json'])['favor'])
        self.assertEqual(len(json.loads(output['prof_comprehension.json'])['rows']), 18)

    def test_effective_catalog_adds_all_maintained_spell_ids_without_losing_raw_spells(self):
        spec = importlib.util.spec_from_file_location('maintenance_specialization_catalog',
                                                     SCRIPTS / 'fc_prof_specializations.py')
        specialization = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(specialization)
        original, _, _ = specialization.catalog(SCRIPTS / '_fc/data', {})
        directory = self.temporary()
        outputs = fc_gen.render_catalog(SCRIPTS / '_fc/data')
        for name, content in outputs.items():
            (directory / name).write_bytes(content)
        effective, _, unresolved = specialization.catalog(directory, {})
        self.assertTrue(original <= effective)
        self.assertEqual(len(effective - original), 47)
        for spell in (2365, 16980, 28461, 28462, 28463, 1270632, 1308182,
                      424641, 12720, 12722, 12904, 428424, 435841, 435848,
                      1231583, 1250775, 1219577, 1219578, 1219581, 1220623, 1302508):
            self.assertIn(spell, effective)
        self.assertEqual(unresolved, 19)

    def test_manual_catalogue_keeps_original_source_build_and_auditable_hash(self):
        source = SCRIPTS / '_fc/maintenance/source/rebase-2-70450'
        frozen = source / 'revision-1-manifest.json'
        previous = json.loads(frozen.read_text(encoding='utf-8'))
        for directory in (SCRIPTS / '_fc/data', source / 'normalized'):
            catalog = fc_gen.render_catalog(directory)
            for slug, count in (('poisons', 26), ('comprehension', 18)):
                data = json.loads(catalog['prof_%s.json' % slug])
                self.assertEqual(data['build'], '1.60.1.70338')
                self.assertEqual(len(data['rows']), count)
                evidence = data['source_provenance']
                evidence_path = maintenance.DEFAULT_PATH.parent / evidence['source_file']
                self.assertEqual(evidence_path.resolve(), frozen.resolve())
                self.assertEqual(evidence['source_sha256'], hashlib.sha256(frozen.read_bytes()).hexdigest())
                self.assertTrue(any(change['path'] == evidence['record_path']
                                    and change['base'] == maintenance.MISSING
                                    for change in previous['changes']))
                self.assertIn('not reverified', evidence['status'])
        # Old manifests without this explicit source evidence cannot turn the
        # current target version into an invented source version.
        raw, active = fc_gen.revision_inputs(source / 'normalized')
        unknown = copy.deepcopy(active)
        unknown.pop('supplemental_catalog_sources')
        with mock.patch.object(fc_gen, 'revision_inputs', return_value=(raw, unknown)):
            catalog = fc_gen.render_catalog(source / 'normalized')
        for slug in ('poisons', 'comprehension'):
            self.assertEqual(json.loads(catalog['prof_%s.json' % slug])['build'], '')

    def test_catalog_has_no_write_side_effect_and_does_not_change_runtime_output(self):
        inputs = fc_gen.generation_input_paths()
        before = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in inputs.items()}
        fc_gen.render_catalog(SCRIPTS / '_fc/data')
        self.assertEqual(before, {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for name, path in inputs.items()})
        self.assertEqual(fc_gen.render_data(SCRIPTS / '_fc/data'), self.outputs)

    def test_exact_prepared_input_selects_only_its_reviewed_revision(self):
        historical = self.manifest['accepted_revisions'][0]
        self.assertEqual(maintenance.select_revision(self.manifest, historical['input_semantic_sha256'])['revision'], 1)
        self.assertEqual(maintenance.select_revision(self.manifest, self.manifest['input_semantic_sha256'])['revision'], 2)
        self.assertIs(maintenance.select_revision(self.manifest, 'unknown-third-input'), self.manifest)
        self.assertNotIn('.pipeline-runtime', maintenance.DEFAULT_PATH.read_text(encoding='utf-8'))

    def test_revision2_replays_latest_counts_sources_and_exact_approved_removal(self):
        directory = SCRIPTS / '_fc/maintenance/source/rebase-2-70450/normalized'
        outputs = fc_gen.render_data(directory)
        model = maintenance.load_sources(outputs)
        self.assertEqual(maintenance.semantic_sha(model), self.manifest['baseline_semantic_sha256'])
        self.assertEqual(model['Data_Professions.lua']['ProfData']['build'], '1.60.1.70450')
        self.assertEqual(model['Data_Professions.lua']['ProfData']['updated'], '2026-10-16')
        recipes = model['Data_ProfRecipes.lua']['ProfRecipes']
        alchemy = recipes['alchemy']
        self.assertEqual(len(alchemy['rows']), 181)
        self.assertEqual(alchemy['counts']['total'], len(alchemy['rows']))
        self.assertFalse(any(row[1] == 1251750 or row[2] == 250952 for row in alchemy['rows'].values()))
        for data in recipes.values():
            rows = data.get('rows', {})
            for group in data.get('groups', {}).values():
                self.assertEqual(group[4], sum(row[4] == group[1] for row in rows.values()))
        self.assertEqual(len(self.manifest['approved_removals']), 1)
        approval = self.manifest['approved_removals'][0]
        self.assertEqual((approval['namespace'], approval['profession'], approval['collection'], approval['spell'], approval['item']),
                         ('ProfRecipes', 'alchemy', 'rows', 1251750, 250952))
        self.assertEqual(approval['target_build'], '1.60.1.70450')
        self.assertIn('跟随最新网页', approval['approval'])

    def test_upstream_caught_up_threshold_keeps_a_third_value_guard(self):
        path = ['Data_ProfRecipes.lua', 'ProfRecipes', 'cooking', 'rows', '$rows',
                'spell:1249957/item:249865', 'yellow']
        guard = next(change for change in self.manifest['changes'] if change['path'] == path)
        self.assertEqual((guard['base'], guard['value']), (30, 30))
        source = SCRIPTS / '_fc/maintenance/source/rebase-2-70450/incoming-input-model.json'
        model = maintenance.normalize(maintenance.unpack(json.loads(source.read_text(encoding='utf-8'))))
        model['Data_ProfTrainers.lua'] = maintenance.unpack(self.manifest['trainer_seed'])
        model['Data_ProfRecipes.lua']['ProfRecipes']['cooking']['rows']['$rows'][path[-2]]['yellow'] = 31
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'conflicts'):
            maintenance.apply_changes(model, self.manifest['changes'])

    def test_updated_guide_retains_legacy_enchant_runtime_recipe_fallback(self):
        from fc_pipeline_common import raw_namespace
        directory = SCRIPTS / '_fc/maintenance/source/rebase-2-70450'
        outputs = fc_gen.render_data(directory / 'normalized')
        path = ['Data_ProfLeveling.lua', 'ProfLeveling', 'enchanting', 'rinfo', 13746]
        guard = next(change for change in self.manifest['changes'] if change['path'] == path)
        self.assertEqual(guard['base'], maintenance.MISSING)
        self.assertEqual(guard['intent'], 'retain_legacy_runtime_recipe_fallback')
        economy = (ROOT / 'Core/ProfEconomy.lua').read_text(encoding='utf-8-sig')
        for sources in (self.outputs, outputs):
            runtime, ns = raw_namespace(list(sources.items()))
            runtime.eval('function(source,ns) assert(loadstring(source))("DungeonsForever",ns) end')(economy, ns)
            recipe = ns.ProfEconomy.FindRecipe('enchanting', 13746)
            self.assertIsNotNone(recipe)
            self.assertEqual((recipe.learn, recipe.yellow, recipe.green, recipe.grey), (205, 225, 245, 265))
            self.assertEqual((recipe.mats[1][1], recipe.mats[1][2]), (11137, 1))
            row = next(row for _, row in ns.ProfRecipes['enchanting']['enchants'].items()
                       if row[1] == 'Enchant Cloak - Greater Defense')
            self.assertEqual(row[14], 13746)
            normalized = ns.ProfEconomy.Normalize(row, 'enchanting', 'enchants')
            self.assertIsNotNone(normalized)
            self.assertEqual(normalized.spell, 13746)
            # A sparse legacy row must still resolve through the retained rinfo
            # record; restoring a proven catalogue ID must not remove fallback.
            row[14] = None
            self.assertIsNone(ns.ProfEconomy.Normalize(row, 'enchanting', 'enchants'))
            fallback = ns.ProfEconomy.FindRecipe('enchanting', 13746)
            self.assertIsNotNone(fallback)
            self.assertEqual((fallback.learn, fallback.yellow, fallback.green, fallback.grey),
                             (205, 225, 245, 265))
            row[14] = 13746
        latest = maintenance.load_sources(outputs)
        steps = latest['Data_ProfLeveling.lua']['ProfLeveling']['enchanting']['steps'].values()
        self.assertEqual([step[3] for step in steps if (step[1], step[2]) == (218, 225)], [13815])
        incoming = maintenance.normalize(maintenance.unpack(json.loads(
            (directory / 'incoming-input-model.json').read_text(encoding='utf-8'))))
        incoming['Data_ProfTrainers.lua'] = maintenance.unpack(self.manifest['trainer_seed'])
        incoming['Data_ProfLeveling.lua']['ProfLeveling']['enchanting']['rinfo'][13746] = {'learn': 999}
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'conflicts'):
            maintenance.apply_changes(incoming, self.manifest['changes'])

    def test_sequence_merge_keeps_upstream_order_and_manual_addition_order(self):
        result = maintenance._merge_order(['a', 'b', 'c'], ['a', 'm', 'n', 'b', 'c'],
                                          ['b', 'a', 'c', 'upstream-new'],
                                          {'a', 'b', 'c', 'm', 'n', 'upstream-new'})
        result = maintenance._array(result)
        self.assertEqual([x for x in result if x not in ('m', 'n')], ['b', 'a', 'c', 'upstream-new'])
        self.assertLess(result.index('m'), result.index('n'))
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'explicit review'):
            maintenance._merge_order(['a', 'b'], ['b', 'a'], ['a', 'b'], {'a', 'b'})

    def test_rebase_does_not_allow_an_unapproved_record_removal(self):
        source = SCRIPTS / '_fc/maintenance/source/rebase-2-70450'
        previous = json.loads((source / 'revision-1-manifest.json').read_text(encoding='utf-8'))
        old_model = maintenance.unpack(json.loads((source / 'previous-input-model.json').read_text(encoding='utf-8')))
        new_model = maintenance.unpack(json.loads((source / 'incoming-input-model.json').read_text(encoding='utf-8')))
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'unapproved maintained record removal'):
            maintenance.prepare_rebase(previous, old_model, new_model, [], {'test': True})

    def test_render_uses_frozen_inputs_without_reading_previous_lua(self):
        directory = self.temporary()
        inputs = fc_gen.generation_input_paths()
        for name, source in inputs.items():
            destination = directory / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        before = {name: hashlib.sha256(source.read_bytes()).hexdigest()
                  for name, source in inputs.items()}
        output = fc_gen.render_data(directory, reference_dir=directory / 'missing-old-lua',
                                    maintenance_path=directory / 'maintenance/professions.json')
        self.assertEqual(output, self.outputs)
        self.assertEqual(before, {name: hashlib.sha256(source.read_bytes()).hexdigest()
                                  for name, source in inputs.items()})
        self.assertFalse(any(directory.glob('*.lua')))

    def test_changed_old_cache_field_conflicts_with_maintained_threshold(self):
        directory = self.temporary()
        for source in (SCRIPTS / '_fc/data').glob('*.json'):
            shutil.copyfile(source, directory / source.name)
        path = directory / 'prof_cooking.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        delta = next(change for change in self.manifest['changes']
                     if len(change['path']) >= 6 and change['path'][1:4] == ['ProfRecipes', 'cooking', 'rows']
                     and change['path'][-1] == 'yellow')
        identity = delta['path'][5]
        spell = int(identity.split('/')[0].split(':')[1])
        next(row for row in data['rows'] if row['spell'] == spell)['yellow'] = 9999
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(maintenance.MaintenanceError, 'conflicts'):
            fc_gen.render_data(directory)
        self.assertFalse(any(directory.glob('*.lua')))

    def test_dry_run_does_not_strip_or_rewrite_any_existing_output(self):
        directory = self.temporary()
        sentinel = directory / 'Data_ProfRecipes.lua'
        original = b'-- preserve this comment\r\nlocal untouched = true\r\n'
        sentinel.write_bytes(original)
        with mock.patch.object(fc_gen, 'OUT', str(directory)):
            self.assertEqual(fc_gen.main(['--dry-run']), 0)
        self.assertEqual(sentinel.read_bytes(), original)
        self.assertEqual([p.name for p in directory.iterdir()], [sentinel.name])


if __name__ == '__main__':
    unittest.main()
