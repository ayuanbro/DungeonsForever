"""Reviewed fixed First Aid metadata survives the maintained three-language build."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'df-data-pipeline/_temp'
sys.path.insert(0, str(SCRIPTS))
import fc_gen
import fc_locales
import fc_maintenance as maintenance


class FirstAidFixedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = SCRIPTS / '_fc/data'
        cls.canonical = json.loads((cls.directory / 'prof_first-aid.json').read_text(encoding='utf-8'))
        cls.rows = {row['spell']: row for row in cls.canonical['rows']}
        raw, cls.manifest = fc_gen.revision_inputs(cls.directory)
        cls.raw_model = maintenance.load_sources(raw)
        cls.outputs = fc_gen.render_data(cls.directory)
        cls.model = maintenance.load_sources(cls.outputs)
        cls.guide = cls.model['Data_ProfLeveling.lua']['ProfLeveling']['first-aid']
        cls.rinfo = cls.guide['rinfo']

    def test_every_fixed_step_has_material_output_and_threshold_metadata(self):
        steps = maintenance._array(self.guide['steps'])
        self.assertTrue(steps)
        self.assertEqual(set(self.rinfo), {step[3] for step in steps})
        for step in steps:
            info = self.rinfo[step[3]]
            self.assertGreater(info['makes'], 0)
            self.assertTrue(info['mats'])
            for mat in info['mats'].values():
                self.assertGreater(mat[1], 0)
                self.assertGreater(mat[2], 0)
            self.assertLessEqual(info['learn'], step[1])
            self.assertLessEqual(info['learn'], info['yellow'])
            self.assertLessEqual(info['yellow'], info['green'])
            self.assertLessEqual(info['green'], info['grey'])

    def test_rinfo_matches_canonical_recipes_and_preserves_multi_output(self):
        self.assertEqual(len(self.rinfo), 14)
        for spell, info in self.rinfo.items():
            row = self.rows[spell]
            guide = self.canonical['leveling']['recipes'][str(spell)]
            for field in ('learn', 'yellow', 'green', 'grey'):
                self.assertEqual(info[field], row[field], (spell, field))
                self.assertEqual(info[field], guide[field], (spell, field))
            self.assertEqual(info['makes'], row['id'])
            self.assertEqual(info['count'], row['count'])
            self.assertEqual([maintenance._array(mat) for mat in info['mats'].values()], row['reagents'])
            self.assertEqual(info['trainer'], guide['source'] == 'trainer')
            self.assertEqual(info['learnSource'], 'trainer' if info['trainer'] else 'catalogue')
        self.assertEqual(self.rinfo[1259342]['count'], 3,
                         'disease remedy crafts produce three items, not one')

    def test_vendor_bandage_manuals_retain_formula_and_source_evidence(self):
        original = {row[1]: row for row in self.raw_model['Data_ProfRecipes.lua']['ProfRecipes']['first-aid']['rows'].values()}
        for spell, formula in ((7929, 16112), (10840, 16113)):
            info = self.rinfo[spell]
            self.assertFalse(info['trainer'])
            self.assertEqual(info['formula'], formula)
            self.assertEqual(info['formula'], self.rows[spell]['formula'][0])
            self.assertEqual(info['source'], original[spell][14])
            self.assertEqual({vendor['id'] for vendor in info['source']['vendors'].values()}, {2805, 13476})
        for spell, info in self.rinfo.items():
            if info['trainer']:
                self.assertNotIn('formula', info)

    def test_first_aid_recipe_catalogue_stays_suppressed_and_delta_is_additive(self):
        self.assertNotIn('first-aid', self.model['Data_ProfRecipes.lua']['ProfRecipes'])
        self.assertNotIn('first-aid', maintenance._array(self.model['Data_ProfRecipes.lua']['ProfRecipeKeys']))
        path = ['Data_ProfLeveling.lua', 'ProfLeveling', 'first-aid', 'rinfo']
        changes = [change for change in self.manifest['changes'] if change['path'] == path]
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['base'], maintenance.MISSING)
        self.assertEqual(maintenance.unpack(changes[0]['value']), self.rinfo)
        self.assertEqual(maintenance.semantic_sha(self.model), self.manifest['baseline_semantic_sha256'])

    def test_base_and_locale_generation_replay_checked_in_bytes_without_writes(self):
        inputs = fc_gen.generation_input_paths()
        before = {name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                  for name, path in inputs.items()}
        runtime_paths = [ROOT / 'Core/Data' / relative for relative in (
            'Data_ProfLeveling.lua', 'enUS/Data_ProfLeveling.lua', 'zhTW/Data_ProfLeveling.lua')]
        runtime_before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in runtime_paths}
        # Vendor output receives a separate NPC enrichment stage; this change
        # owns only the fixed-route file and its two translated overlays.
        self.assertEqual(fc_gen.render_data(self.directory), self.outputs)
        self.assertEqual(maintenance.render_model(self.model), self.outputs)
        # Git autocrlf may change checkout line endings. Compare generated LF
        # content exactly, while checking original bytes and mtimes below.
        self.assertEqual(self.outputs['Data_ProfLeveling.lua'],
                         runtime_before[runtime_paths[0]][0].replace(b'\r\n', b'\n'))
        localized = fc_locales.render_locales({'Data_ProfLeveling.lua': self.outputs['Data_ProfLeveling.lua']}, ROOT / 'Core/Data')
        for relative, content in localized.items():
            self.assertEqual(content, runtime_before[ROOT / 'Core/Data' / relative][0].replace(b'\r\n', b'\n'), relative)
            runtime = maintenance.lua_runtime()
            runtime.eval('function(locale) GetLocale=function() return locale end end')(relative.split('/')[0])
            namespace = runtime.table()
            runtime.eval('function(src, ns) assert(loadstring(src))("DungeonsForever", ns) end')(content.decode('utf-8'), namespace)
            guide = maintenance.lua_value(namespace)['ProfLeveling']['first-aid']['rinfo']
            for spell, info in self.rinfo.items():
                actual = guide[spell]
                for field in ('learn', 'yellow', 'green', 'grey', 'mats', 'makes', 'count', 'formula', 'trainer', 'learnSource'):
                    self.assertEqual(actual.get(field), info.get(field), (relative, spell, field))
                if not info['trainer']:
                    self.assertEqual({v['id'] for v in actual['source']['vendors'].values()}, {2805, 13476})
        self.assertEqual(before, {name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                                  for name, path in inputs.items()})
        self.assertEqual(runtime_before, {path: (path.read_bytes(), path.stat().st_mtime_ns)
                                          for path in runtime_paths})


if __name__ == '__main__':
    unittest.main()
