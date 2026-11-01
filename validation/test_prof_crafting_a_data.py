"""Field-level evidence checks for the alchemy/engineering/enchanting supplement.

The candidate inventory is exhaustive for the two pinned spell sets. Inventory
coverage is separate from evidence that a recipe is learnable in a live client.
"""
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

try:
    from validation.test_prof_solver_fusion import LuaRuntime, ROOT
except ModuleNotFoundError:
    from test_prof_solver_fusion import LuaRuntime, ROOT

PATH = ROOT / 'validation/data/prof_crafting_a_candidates.json'


class CraftingADataEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding='utf-8'))
        cls.records = {(r['profession'], r['spell']): r for r in cls.data['records']}
        cls.reference = LuaRuntime(unpack_returned_tuples=True)
        cls.reference.execute('ns={}')
        for path in ('AddOns/DungeonsForever/Framework/CatalogCodec.lua',
                     'AddOns/DungeonsForever_RecipeData/Data/Data_ProfCatalog.lua',
                     'AddOns/DungeonsForever_RecipeData/Domain/ProfCatalog.lua'):
            text = subprocess.check_output(['git', 'show', cls.data['modularizationReference'] + ':' + path], cwd=ROOT, text=True, encoding='utf-8')
            cls.reference.execute("assert(loadstring(...))('DungeonsForever',ns)", text)
        cls.native = LuaRuntime(unpack_returned_tuples=True)
        cls.native.execute('ns={}')
        for path in ('Core/Data/Data_ProfRecipes.lua', 'Core/Data/Data_ProfLeveling.lua'):
            text = subprocess.check_output(['git', 'show', cls.data['devReference'] + ':' + path], cwd=ROOT, text=True, encoding='utf-8')
            cls.native.execute("assert(loadstring(...))('DungeonsForever',ns)", text)
        cls.native_ids = cls.native.eval(r'''function(slug)
          local ids={};local group=ns.ProfRecipes[slug]or{}
          local function add(id)if type(id)=='number'and id>0 then ids[id]=true end end
          for _,row in ipairs(group.rows or{})do add(row[1])end
          for spell in pairs((ns.ProfLeveling[slug]or{}).rinfo or{})do add(spell)end
          for _,row in ipairs(group.crafted or{})do add(row[1])end
          for _,row in ipairs(group.enchants or{})do add(row[14])end
          return ids
        end''')
        cls.snapshots = {}
        cls.tables = {}
        for sid, source in cls.data['sources'].items():
            path = ROOT / source['local_snapshot']
            if not path.is_file():
                continue
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != source['sha256']:
                raise AssertionError('raw source digest mismatch: ' + sid)
            cls.snapshots[sid] = body.decode('utf-8-sig')
            if '/csv?' in source['url']:
                cls.tables[sid] = {r['ID']: r for r in csv.DictReader(cls.snapshots[sid].splitlines())}

    def test_exact_spell_sets_have_one_matching_or_reviewed_record(self):
        for slug, coverage in self.data['coverage'].items():
            reference_ids = set()
            iterator = self.reference.globals().ns.ProfCatalog.IterRecipes(slug)
            while True:
                recipe = iterator()
                if recipe is None:
                    break
                reference_ids.add(int(recipe.spell))
            self.assertEqual(reference_ids, set(coverage['modularization_spell_ids']))
            self.assertEqual({int(spell) for spell in self.native_ids(slug)}, set(coverage['dev_spell_ids']))
            reviewed = {spell for profession, spell in self.records if profession == slug}
            matching = set(coverage['matching_spell_ids'])
            self.assertFalse(reviewed & matching)
            self.assertEqual(reviewed | matching, reference_ids | set(coverage['dev_spell_ids']))
        self.assertEqual(len(self.records), len(self.data['records']))

    def test_every_accepted_field_has_evidence_and_no_implicit_defaults(self):
        for record in self.records.values():
            for field, value in record['acceptedFields'].items():
                self.assertIsNotNone(value, (record['spell'], field))
                self.assertTrue(record['fieldEvidence'].get(field), (record['spell'], field))
            if record.get('planningReadyFromAcceptedFields'):
                fields = record['acceptedFields']
                self.assertTrue(all(isinstance(fields.get(f), (int, float)) for f in ('learn', 'yellow', 'green', 'grey')))
                self.assertTrue(fields.get('mats'))
                self.assertIn('count', fields)

    def test_all_local_source_bytes_match_recorded_sha256_and_product(self):
        self.assertTrue(self.snapshots, 'raw snapshots are unavailable for evidence validation')
        for sid, source in self.data['sources'].items():
            self.assertEqual(source['product'], 'wowf')
            self.assertEqual(source['build'], self.data['sourceBuild'])
            self.assertIn(sid, self.snapshots, 'missing raw source: ' + sid)

    def test_accepted_materials_are_exact_raw_same_build_reagents(self):
        for record in self.records.values():
            fields = record['acceptedFields']
            if 'mats' not in fields:
                continue
            proof = record['fieldEvidence']['mats'][0]
            row = self.tables[proof['source']][proof['row']['ID']]
            self.assertEqual(row, proof['row'])
            self.assertEqual(int(row['SpellID']), record['spell'])
            materials = sorted((int(row['Reagent_' + str(i)]), int(row['ReagentCount_' + str(i)]))
                               for i in range(8) if int(row['Reagent_' + str(i)]) > 0 and int(row['ReagentCount_' + str(i)]) > 0)
            self.assertEqual(materials, [(m['item'], m['count']) for m in fields['mats']])

    def test_accepted_output_count_is_definite_effect_or_non_item_enchant(self):
        for record in self.records.values():
            fields = record['acceptedFields']
            if 'count' not in fields:
                continue
            proof = record['fieldEvidence']['count'][0]
            if fields['count'] == 0:
                self.assertEqual(record['profession'], 'enchanting')
                effects = proof['non_item_effects']
                self.assertTrue(any(int(e['Effect']) == 53 for e in effects))
                self.assertFalse(any(int(e['Effect']) == 24 for e in effects))
            else:
                row = self.tables[proof['source']][proof['row']['ID']]
                self.assertEqual(int(row['SpellID']), record['spell'])
                self.assertEqual(int(row['Effect']), 24)
                self.assertEqual(int(row['EffectItemType']), fields['item'])
                self.assertEqual(float(row['EffectBasePointsF']), fields['count'])
                self.assertEqual(float(row['Variance']), 0)

    def test_item_identity_is_checked_independently_from_output_quantity(self):
        for record in self.records.values():
            fields = record['acceptedFields']
            if 'item' not in fields:
                continue
            for proof in record['fieldEvidence']['item']:
                row = self.tables[proof['source']][proof['row']['ID']]
                self.assertTrue(all(row[key] == value for key, value in proof['row'].items()))
                self.assertEqual(int(row['SpellID']), record['spell'])
                self.assertEqual(int(row['Effect']), 24)
                self.assertEqual(int(row['EffectItemType']), fields['item'])
                self.assertGreater(fields['item'], 0)

    def test_all_new_single_item_effects_preserve_unknown_quantity(self):
        source = next(sid for sid, value in self.data['sources'].items()
                      if '/SpellEffect/csv?' in value['url'])
        effects = defaultdict(list)
        for row in self.tables[source].values():
            if int(row['Effect']) == 24 and int(row['EffectItemType']) > 0:
                effects[int(row['SpellID'])].append(row)
        unresolved_outputs = set()
        for record in self.records.values():
            if record['dev'] or not (record['modularization'] or {}).get('item'):
                continue
            item = record['modularization']['item']
            rows = effects[record['spell']]
            if not rows or {int(row['EffectItemType']) for row in rows} != {item}:
                continue
            fields = record['acceptedFields']
            self.assertEqual(fields.get('item'), item, record['spell'])
            self.assertNotIn('item', record['unresolvedFields'])
            definite = any(float(row['EffectBasePointsF']) > 0 and
                           float(row['Variance']) == 0 for row in rows)
            if definite:
                continue
            unresolved_outputs.add(record['spell'])
            self.assertNotIn('count', fields, record['spell'])
            self.assertIn('count', record['unresolvedFields'])
            self.assertFalse(record['planningReadyFromAcceptedFields'])
            uncertainty = record['outputQuantityUncertainty']
            self.assertEqual(uncertainty['decision'], 'retain_unknown')
            self.assertEqual({proof['row']['ID'] for proof in uncertainty['effectRows']},
                             {row['ID'] for row in rows})
        # Cover both zero base quantities and variable nonzero base quantities.
        self.assertTrue({430409, 463869, 471400, 435964, 435966} <= unresolved_outputs)
        for spell in (435964, 435966):
            self.assertEqual(float(effects[spell][0]['EffectBasePointsF']), 3)
            self.assertEqual(float(effects[spell][0]['Variance']), 1)

    def test_formula_links_are_real_item_learning_effects(self):
        for record in self.records.values():
            fields = record['acceptedFields']
            if 'formula' not in fields:
                continue
            proof = record['fieldEvidence']['formula'][0]
            link = self.tables[proof['source']][proof['row']['ID']]
            effect = self.tables[proof['item_effect_source']][proof['item_effect']['ID']]
            self.assertEqual(link, proof['row'])
            self.assertEqual(effect, proof['item_effect'])
            self.assertEqual(int(link['ItemID']), fields['formula'])
            self.assertEqual(link['ItemEffectID'], effect['ID'])
            self.assertEqual(int(effect['SpellID']), record['spell'])
            self.assertEqual(int(effect['TriggerType']), 6)

    def test_all_accepted_thresholds_match_raw_web_fields_or_db2_endpoints(self):
        parsed = {}
        decoder = json.JSONDecoder()

        def rows(sid):
            if sid in parsed:
                return parsed[sid]
            text = self.snapshots[sid]
            out = defaultdict(list)
            for match in re.finditer(r'\bdata\s*:\s*(\[)', text):
                try:
                    items, _ = decoder.raw_decode(text, match.start(1))
                except ValueError:
                    continue
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and 'id' in item:
                            out[item['id']].append(item)
            for match in re.finditer(r'\$\.extend\(g_spells\[(\d+)\],\s*(\{)', text):
                start = match.start(2)
                stop = text.find(',difficulties:', start)
                if stop < 0:
                    continue
                try:
                    item = decoder.raw_decode(text[start:stop] + '}')[0]
                except ValueError:
                    continue
                if isinstance(item, dict):
                    out[int(match[1])].append(item)
            parsed[sid] = out
            return out

        for record in self.records.values():
            for field, value in record['acceptedFields'].items():
                if field not in ('learn', 'yellow', 'green', 'grey'):
                    continue
                found = False
                for proof in record['fieldEvidence'][field]:
                    if 'row' in proof:
                        row = self.tables[proof['source']][proof['row']['ID']]
                        column = 'TrivialSkillLineRankLow' if field == 'yellow' else 'TrivialSkillLineRankHigh'
                        found = found or int(row[column]) == value
                        continue
                    for item in rows(proof['source'])[record['spell']]:
                        actual = item.get('learnedat') if field == 'learn' else (item.get('colors') or [None] * 4)[{'yellow': 1, 'green': 2, 'grey': 3}[field]]
                        found = found or actual == value
                self.assertTrue(found, (record['profession'], record['spell'], field, value))

    def test_existing_conflicts_are_not_overwritten_by_reference_labels(self):
        for record in self.records.values():
            old = record['dev']
            if not old:
                continue
            for field, new in record['acceptedFields'].items():
                if old.get(field) is None or old.get(field) == new:
                    continue
                self.assertEqual(field, 'green', (record['spell'], field))
                self.assertNotEqual(old['green'], int(old['green']))
                self.assertEqual(old['yellow'], record['modularization']['yellow'])
                self.assertEqual(old['grey'], record['modularization']['grey'])
            for conflict in record['conflicts']:
                self.assertNotIn(conflict['field'], record['acceptedFields'])

    def test_partial_2330_and_7181_never_become_invented_complete_recipes(self):
        for spell, yellow, grey in ((2330, 55, 95), (7181, 175, 215)):
            record = self.records['alchemy', spell]
            self.assertEqual(record['acceptedFields'], {'yellow': yellow, 'grey': grey})
            self.assertFalse(record['planningReadyFromAcceptedFields'])
            self.assertTrue({'learn', 'green', 'mats', 'item', 'count'} <= set(record['unresolvedFields']))

    def test_custom_enchanting_reagents_are_preserved(self):
        for spell in (7418, 7421):
            record = self.records['enchanting', spell]
            self.assertEqual(record['dev']['mats'], record['modularization']['mats'])
            self.assertIn({'item': 247786, 'count': 1}, record['dev']['mats'])
            self.assertNotIn('mats', record['acceptedFields'])
            self.assertNotIn('learn', record['acceptedFields'])

    def test_tool_membership_matches_the_pinned_native_and_modular_preferences(self):
        text = subprocess.check_output(['git', 'show', self.data['modularizationReference'] + ':AddOns/DungeonsForever_Professions/Data/Data_ProfPreferences.lua'], cwd=ROOT, text=True, encoding='utf-8')
        self.reference.execute("assert(loadstring(...))('DungeonsForever',ns)", text)
        for slug, tools in self.data['tools'].items():
            expected = sorted(int(spell) for _, spell in self.reference.globals().ns.ProfPreferences.toolGoals[slug].items())
            self.assertEqual(sorted(tool['spell'] for tool in tools), expected)


if __name__ == '__main__':
    unittest.main()
