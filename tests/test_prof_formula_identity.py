"""Recover omitted enchant formulas from current client teaching evidence."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
from lupa.lua51 import LuaRuntime


class FormulaIdentityTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
          ns={}
          GetBuildInfo=function()return '1.60.1','70450' end
          UnitFactionGroup=function()return 'Alliance' end
          function evidence(item,spell,values)
            local row={kind='item',itemID=item,status='pending',requiredAbility=0,
              sourceBuild='1.60.1.70450',hotfixBuild='70450',
              learningPath='Item['..item..'].ClassID=9 -> ItemEffect[9].SpellID='..spell..'/TriggerType=6'}
            for k,v in pairs(values or{})do row[k]=v end
            return row
          end
          ns.ProfSpecializationsMeta={schemaVersion=1,targetBuild='1.60.1.70450',hotfixBuild='70450'}
          ns.ProfSpecializations={[100]={routes={evidence(99,100)}}}
        ''')
        self.load('Core/ProfItemPrices.lua')

    def load(self, name):
        self.lua.execute((ROOT / name).read_text(encoding='utf-8-sig'),
                         'Test', self.lua.globals().ns)

    def test_explicit_formula_wins_and_pending_specialization_does_not_erase_identity(self):
        self.lua.execute('''
          local resolve=ns.ProfItemPrices.GetFormulaItemID
          assert(resolve(100)==99)
          assert(resolve(100,{formulaID='98'})==98)
          assert(resolve(100,{formulaID=0})==99)
          assert(resolve(100,{created=900,output=900})==99)
          assert(resolve(101)==nil)
          ns.ProfSpecializations[100].routes[2]=evidence(99,100)
          assert(resolve(100)==99,'duplicate evidence is not an alternative item')
          ns.ProfSpecializations[100].routes[3]=evidence(98,100)
          assert(resolve(100)==nil,'distinct teaching items must stay ambiguous')
        ''')

    def test_stale_build_and_missing_client_api_do_not_create_identity(self):
        self.lua.execute('''
          local resolve=ns.ProfItemPrices.GetFormulaItemID
          GetBuildInfo=function()return '1.60.1','70338' end
          assert(resolve(100)==nil)
          GetBuildInfo=function()error('unavailable')end
          assert(resolve(100)==nil)
          GetBuildInfo=nil
          assert(resolve(100)==nil)
          assert(resolve(100,{formulaID=98})==98)
          GetBuildInfo=function()return '1.60.1','70450' end
          local row=ns.ProfSpecializations[100].routes[1]
          row.sourceBuild='1.60.1.70338';assert(resolve(100)==nil)
          row.sourceBuild='1.60.1.70450';row.hotfixBuild='70338';assert(resolve(100)==nil)
          row.hotfixBuild='70450';assert(resolve(100)==99)
        ''')

    def test_item_identity_requires_a_matching_teaching_path(self):
        self.lua.execute('''
          local resolve=ns.ProfItemPrices.GetFormulaItemID
          local row=ns.ProfSpecializations[100].routes[1]
          for _,bad in ipairs({'', 'Item[98].ClassID=9 -> ItemEffect[9].SpellID=100/TriggerType=6',
              'Item[99].ClassID=9 -> ItemEffect[9].SpellID=1000/TriggerType=6',
              'Item[99].ClassID=9 -> ItemEffect[9].SpellID=100/TriggerType=0'})do
            row.learningPath=bad;assert(resolve(100)==nil)
          end
          row.learningPath='Item[99].ClassID=9 -> SpellEffect[9].Effect=36/EffectTriggerSpell=1000'
          assert(resolve(100)==nil)
          row.learningPath='Item[99].ClassID=9 -> SpellEffect[9].Effect=36/EffectTriggerSpell=100'
          assert(resolve(100)==99)
          row.kind='trainer';assert(resolve(100)==nil)
        ''')

    def test_all_real_enchants_match_independent_client_csv_and_screenshot_costs(self):
        for name in ('Data_ProfRecipes.lua', 'Data_ProfSpecializations.lua',
                     'Data_ProfItems.lua', 'Data_ProfVendors.lua'):
            self.load('Core/Data/' + name)
        self.lua.execute('ns.EnsureProfRecipes({"enchanting"})')
        ns = self.lua.globals().ns
        target = ns.ProfSpecializationsMeta.targetBuild
        by_spell = {}
        path = ROOT / 'df-data-pipeline/_temp/_fc/inputs/client/recipe-item-specializations.csv'
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                if row['RecipeSpellID'] and row['Build'] == target:
                    by_spell.setdefault(int(row['RecipeSpellID']), set()).add(int(row['RecipeItemID']))
        count = recovered = ambiguous = 0
        for _, enchant in ns.ProfRecipes.enchanting.enchants.items():
            count += 1
            spell, source = enchant[14], enchant[10]
            expected = by_spell.get(spell, set())
            explicit = source and source.formulaID
            wanted = explicit or (next(iter(expected)) if len(expected) == 1 else None)
            self.assertEqual(ns.ProfItemPrices.GetFormulaItemID(spell, source), wanted,
                             'enchant spell %s' % spell)
            recovered += bool(wanted)
            ambiguous += len(expected) > 1
        self.assertGreaterEqual(count, 165)
        self.assertGreater(recovered, 50)
        self.lua.execute('''
          local prices=ns.ProfItemPrices
          local byName={}
          for _,en in ipairs(ns.ProfRecipes.enchanting.enchants)do byName[en[1]]=en end
          assert(byName['Enchant Weapon - Recovery'][14]==1248760)
          assert(byName['Enchant Weapon - Revelation'][14]==1248805)
          assert(prices.GetFormulaItemID(byName['Enchant Weapon - Recovery'][14],
            byName['Enchant Weapon - Recovery'][10])==249480)
          assert(prices.GetFormulaItemID(13536)==11101)
          assert(prices.GetFormulaItemID(1248760)==249480)
          assert(prices.GetFormulaItemID(1248805)==249481)
          for _,spell in ipairs({1248760,1248805})do
            local id=prices.GetFormulaItemID(spell)
            local offers=prices.GetFormulaDisplayOffers(id)
            assert(#offers==1 and offers[1].faction=='A')
            assert(offers[1].currencyKind=='currency' and offers[1].currencyID==3402
              and offers[1].currencyAmount==45 and offers[1].costCopper==nil)
            assert(#prices.GetFormulaOffers(id)==0,'exchange must not become a copper quote')
          end
        ''')

    def test_generated_three_locale_rows_retain_every_repaired_source_spell(self):
        directory = ROOT / 'df-data-pipeline/_temp/_fc'
        manifest = json.loads((directory / 'maintenance/professions.json').read_bytes())
        repair = manifest['provenance']['enchant_identity_repair']
        raw_ids = (directory / 'data/enchant_ids.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw_ids).hexdigest(), repair['source_sha256'])
        ids = json.loads(raw_ids)
        self.assertEqual(len(repair['restored_spell_fields']), 26)
        baseline = None
        for locale in ('zhCN', 'enUS', 'zhTW'):
            self.lua.globals().formulaLocale = locale
            self.lua.execute('GetLocale=function()return formulaLocale end')
            self.load('Core/Data/Data_ProfRecipes.lua')
            if locale != 'zhCN':
                self.load('Core/Data/' + locale + '/Data_ProfRecipes.lua')
            self.lua.execute('ns.EnsureProfRecipes({"enchanting"})')
            enchants = self.lua.globals().ns.ProfRecipes.enchanting.enchants
            rows = {row[1]: row[14] for row in enchants.values()}
            spell_order = [enchants[i][14] for i in range(1, len(enchants) + 1)]
            for row in repair['restored_spell_fields']:
                self.assertEqual(row['spell'], ids[row['name']]['spell'])
                self.assertEqual(rows[row['name']], row['spell'], locale + ':' + row['name'])
            self.assertEqual(len(rows), 169)
            if baseline is None:
                baseline = spell_order
            else:
                self.assertEqual(spell_order, baseline)

    def test_real_enchant_cards_show_formula_currency_and_affiliation_in_three_locales(self):
        from test_prof_recipe_sources import RecipeSourceTests
        for locale in ('zhCN', 'enUS', 'zhTW'):
            fixture = RecipeSourceTests('test_dual_sources_have_independent_labels_tooltips_and_existing_actions')
            fixture.setUp()
            lua = fixture.lua
            lua.globals().formulaLocale = locale
            lua.execute('''
              GetLocale=function()return formulaLocale end
              GetBuildInfo=function()return '1.60.1','70450' end
              PD.cur='enchanting'
              C_CurrencyInfo={GetCurrencyInfo=function(id)
                if id==3402 then return{name='TestCurrency3402',iconFileID=789}end
              end}
            ''')
            for path in ('Locales/zhCN.lua', 'Locales/enUS.lua', 'Locales/zhTW.lua',
                         'Core/Data/Data_ProfRecipes.lua', 'Core/Data/Data_ProfSpecializations.lua',
                         'Core/Data/Data_ProfItems.lua', 'Core/Data/Data_ProfVendors.lua'):
                lua.execute((ROOT / path).read_text(encoding='utf-8-sig'), 'Test', lua.globals().ns)
            if locale != 'zhCN':
                path = 'Core/Data/' + locale + '/Data_ProfRecipes.lua'
                lua.execute((ROOT / path).read_text(encoding='utf-8-sig'), 'Test', lua.globals().ns)
            lua.execute('''
              L=ns.L
              ns.EnsureProfRecipes({'enchanting'})
              local bySpell={}
              for _,en in ipairs(ns.ProfRecipes.enchanting.enchants)do bySpell[en[14] or 0]=en end
              for _,pair in ipairs({{1248760,249480},{1248805,249481},{13536,11101}})do
                local en=assert(bySpell[pair[1]],'screenshot enchant missing from formal catalogue')
                local resolved=PD.RecipeData(en,'enchants')
                assert(resolved.formula==pair[2],'card failed to receive proven formula ID')
                local spec=PD.EnchantSpec(en)
                local part
                for _,segment in ipairs(spec.sourceSegments or{})do
                  if segment.text==L['图纸.商人'] then part=segment end
                end
                assert(part and part.act,'missing merchant card segment or map action')
                local lines=part.lines()
                local item=ns.ProfItems[pair[2]]
                assert(lines[1][1]==string.format(L['图纸：%s'],item['Name_'..formulaLocale]))
                local offers=ns.ProfItemPrices.GetFormulaDisplayOffers(pair[2],nil,resolved.source)
                assert(#offers==1 and offers[1].faction=='A')
                local seller=offers[1]
                assert(seller.npcFactionName and hasLine(lines,seller.npcFactionName))
                assert(hasLine(lines,seller.name) and not hasLine(lines,L['阵营未知']))
                assert(not hasLine(lines,L['价格未知']))
                if pair[2]==11101 then
                  assert(hasLine(lines,'2500'))
                else
                  assert(hasLine(lines,'TestCurrency3402') and hasLine(lines,'45'))
                  assert(#ns.ProfItemPrices.GetFormulaOffers(pair[2])==0)
                end
              end
            ''')


if __name__ == '__main__':
    unittest.main()
