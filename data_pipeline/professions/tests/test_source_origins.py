"""Keep source facts distinct from gold purchase feasibility in every profession."""
import copy
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'validation'))
from test_prof_native_data import native_runtime
from test_prof_ui_fusion import UI_MOCKS
from data_pipeline.professions.build import normalize, runtime_facts, vendor_cost
from data_pipeline.professions.tests.test_source_pipeline import fixture_tables, snapshot, temporary_directory


class SourceOriginGenerationTests(unittest.TestCase):
    def test_gold_currency_and_item_costs_preserve_their_units(self):
        self.assertEqual(vendor_cost([[123]]), {'price': 123})
        self.assertEqual(vendor_cost([[123, [], []]]), {'price': 123})
        quote = vendor_cost([[0, [[3402, 30]], []]])
        self.assertTrue(quote['hasExtendedCost'])
        self.assertEqual((quote['currencyID'], quote['currencyAmount'], quote['price']), (3402, 30, 0))
        barter = vendor_cost([[5, [], [[1234, 2]]]])
        self.assertEqual(barter['costItems'], [{'id': 1234, 'count': 2}])
        self.assertEqual(vendor_cost([[0, [[3402, 'unknown']], []]]), {})

    def test_automatic_skill_grants_require_explicit_acquire_method_and_level_schema(self):
        tables = fixture_tables()
        tables['SkillLineAbility'][0].update(AcquireMethod='1', MinSkillLineRank='1')
        tables['SkillLineAbility'][1].update(AcquireMethod='0', MinSkillLineRank='1')
        tables['SpellLevels'] = [{'ID': '1', 'SpellID': '1000', 'DifficultyID': '0', 'BaseLevel': '5', 'SpellLevel': '5'}]
        with temporary_directory() as temp:
            raw=Path(temp); manifest=snapshot(raw, with_web=False, tables=tables)
            facts,_=normalize(raw,manifest)
            automatic=facts['alchemy'][1000]['routes'][0]
            self.assertEqual(automatic['acquisition']['kind'], 'skillGrant')
            self.assertEqual(automatic['status'], 'confirmed')
            self.assertEqual(automatic['trainingCost'], 0)
            self.assertIn({'kind':'level','value':5}, automatic['conditions'])
            self.assertFalse(any(r.get('acquisition',{}).get('kind')=='skillGrant' for r in facts['alchemy'][1001]['routes']))

        tables['SpellLevels'][0].pop('SpellLevel')
        with temporary_directory() as temp:
            raw=Path(temp); manifest=snapshot(raw, with_web=False, tables=tables)
            facts,_=normalize(raw,manifest)
            automatic=facts['alchemy'][1000]['routes'][0]
            self.assertEqual(automatic['status'], 'unknown')
            self.assertFalse(automatic['conditionsKnown'])

    def test_runtime_reference_compaction_preserves_costs_and_supplier_identity(self):
        vendor={'id':12,'npcID':12,'name':'Reference','areas':[44],**vendor_cost([[0,[[3402,30]],[]]])}
        facts={'alchemy':{1000:{'routes':[{'acquisition':{'vendors':[vendor]}}]}}}
        original=copy.deepcopy(facts)
        compact=runtime_facts(facts)['alchemy'][1000]['routes'][0]['acquisition']['vendors'][0]
        self.assertEqual(compact,{k:v for k,v in vendor.items() if k not in ('npcID','name','areas')})
        self.assertEqual(facts,original)


class ShippedSourceOriginTests(unittest.TestCase):
    def setUp(self, locale='zhCN'):
        self.lua=native_runtime(locale)
        self.lua.execute('ns.IsForever=true')
        candidate=Path(os.environ.get('DF_SOURCE_CANDIDATE',ROOT/'Core/Data/Data_ProfLearningSources.lua'))
        self.lua.execute("assert(loadstring(...,'@source-origins'))('DungeonsForever',ns)",candidate.read_text(encoding='utf8'))
        for name in ('Data_ProfSources.lua','Data_ProfNPCLocs.lua'):
            self.lua.execute("assert(loadstring(...,'@native-source-reference'))('DungeonsForever',ns)",
                (ROOT/'Core/Data'/name).read_text(encoding='utf8'))
        self.lua.execute("assert(loadstring(...,'@native-source-merge'))('DungeonsForever',ns)",
            (ROOT/'Core/ProfSourceMerge.lua').read_text(encoding='utf8'))
        self.lua.execute('savedData={ns.ProfData,ns.ProfRecipes,ns.ProfLeveling}')
        self.lua.execute(UI_MOCKS)
        self.lua.execute('''
          ns.ProfData,ns.ProfRecipes,ns.ProfLeveling=unpack(savedData)
          UnitClass=function()return 'Warrior','WARRIOR',1 end
          UnitRace=function()return 'Human','Human',1 end
          ns.ProfEconomy.Professions=function()return {alchemy={cur=1,max=75},blacksmithing={cur=57,max=300}}end
          ns.ProfRouteAuto.MatListCost=function()return 1,0 end
          ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n)end
          ns.ProfHost.DG.ItemIcon=function()return 'Interface/Icons/INV_Misc_QuestionMark'end
        ''')
        self.lua.execute("assert(loadstring(...,'@source-ui'))('DungeonsForever',ns)",
            (ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf8'))
        self.lua.execute('''
          PD=ns.ProfModule;PD.cur='alchemy'
          PD.ItemName=function(id)return 'Item'..id,true end
          PD.KitSub=function()return ''end;PD.AhPct=function()end;PD.ScheduleSweep=function()end
        ''')

    def test_three_actual_starters_are_automatic_not_extra_training_or_pattern_purchases(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,spell in ipairs({7183,1245246,1245250})do
            local r=E.FindRecipe('alchemy',spell)
            local ok,reason,d=E.SelectLearningRoute(r,nil,{skill={alchemy=1}})
            assert(ok,tostring(spell)..':'..tostring(reason))
            assert(d.quote.automatic and d.quote.cost==0 and d.quote.usable)
            assert(d.route.acquisition.kind=='skillGrant' and d.route.acquisition.minSkillRank==1)
            local card=PD.RecipeLearningCard(r,false)
            assert(card.text==ns.L['随专业技能获得'] and card.fid==nil)
            r.selectedLearningRoute=d.route;r.learningQuote=d.quote
            assert(PD.RecipeLearningCard(r,true).text==ns.L['随专业技能获得'],
              'frozen automatic source was mislabeled as a trainer')
            local snapshot={known={},professions={alchemy={cur=1,max=75}},recipes={r},learningSourcesRequired=true}
            local rows,cost,complete=E.CollectFormulas({{recipe=r,count=3}},'alchemy',snapshot)
            assert(#rows==0 and cost==0 and complete,'automatic recipe created a learning purchase')
          end
        ''')

    def test_eight_confirmed_grants_use_rank_one_without_changing_data_or_color_thresholds(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,case in ipairs({{'alchemy',1245246,10},{'alchemy',1245250,10},
            {'blacksmithing',1245287,10},{'enchanting',7428,20},{'enchanting',1245320,10},
            {'enchanting',1245321,10},{'poisons',8681,125},{'tailoring',3755,5}})do
            local slug,spell,old=unpack(case);PD.cur=slug
            local raw,kind
            for _,k in ipairs({'rows','enchants','crafted'})do
              for _,row in ipairs((ns.ProfRecipes[slug] or {})[k] or {})do
                if (k=='enchants' and row[14] or row[1])==spell then raw,kind=row,k;break end
              end
              if raw then break end
            end
            local original=raw and E.Normalize(raw,slug,kind)
            local r=E.FindRecipe(slug,spell)
            assert(r and r.learn==1 and r.catalogueLearn==old and r.skillSource=='automaticSkillGrant',slug..':'..spell)
            assert(E.Gain(r,1)>0,'old learning threshold still prevents skill gain')
            if original then
              assert(r.yellow==original.yellow and r.green==original.green and r.grey==original.grey)
              local view=PD.RecipeData(raw,kind,slug)
              assert(view.learn==1 and E.Normalize(raw,slug,kind).learn==old,'native tuple changed')
            end
            local snapshot={learningSourcesRequired=true,known={},classID=4,raceID=1,level=60,
              professions={[slug]={cur=1,max=300}},specializationAbilities={}}
            local ok,why,d=E.SelectLearningRoute(r,snapshot,{skill={[slug]=1}})
            assert(ok,slug..':'..spell..':'..tostring(why))
            assert(d.quote.automatic and d.quote.cost==0)
            if slug=='poisons'then
              snapshot.classID=1
              local allowed,reason=E.SelectLearningRoute(r,snapshot,{skill={[slug]=1}})
              assert(not allowed and reason=='poisonRogueRequired','automatic grant erased the Rogue restriction')
            end
          end
        ''')

    def test_automatic_rank_keeps_live_thresholds_and_frozen_inputs_authoritative(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          ns.ProfRecipeRuntime=ns.ProfRecipeRuntime or {}
          ns.ProfRecipeRuntime[1245246]={learn=7}
          local r=E.FindRecipe('alchemy',1245246)
          assert(r.learn==7 and r.skillSource=='client')
          local frozen={profession='alchemy',professions={alchemy={cur=1,max=75}},known={},
            recipes={{profession='alchemy',spell=1245246,key='alchemy:1245246',learn=10,grey=15,mats={}}},
            learningDataFingerprint='previous-policy',learningPolicyFingerprint='previous-policy'}
          ns.ProfLearningSources.AutomaticSkillRank=function()error('frozen input read current grants')end
          local copy=E.Capture('alchemy',{snapshot=frozen,start=1,target=2})
          assert(copy.recipes[1].learn==10 and frozen.recipes[1].learn==10)
          assert(copy.learningDataFingerprint=='previous-policy')
        ''')

    def test_confirmed_rank_and_source_labels_match_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.setUp(locale)
                self.lua.execute('''
                  for _,case in ipairs({{'alchemy',1245246},{'alchemy',1245250},{'blacksmithing',1245287},
                    {'enchanting',7428},{'enchanting',1245320},{'enchanting',1245321},{'poisons',8681},{'tailoring',3755}})do
                    local r=ns.ProfEconomy.FindRecipe(case[1],case[2]);PD.cur=case[1]
                    assert(r and r.learn==1 and r.catalogueLearn>1,case[1]..':'..case[2])
                    assert(PD.RecipeLearningCard(r,false).text==ns.L['随专业技能获得'])
                  end
                ''')

    def test_all_eight_real_recipes_can_start_an_isolated_route_at_rank_one(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,case in ipairs({{'alchemy',1245246},{'alchemy',1245250},{'blacksmithing',1245287},
            {'enchanting',7428},{'enchanting',1245320},{'enchanting',1245321},{'poisons',8681},{'tailoring',3755}})do
            local slug,spell=unpack(case)
            E.Professions=function()return {[slug]={cur=1,max=300}}end
            local s=E.Capture(slug,{start=1,target=2,autoCraftTools=false,recoveryEnabled=false,
              noFormula=true,considerAuctionSupply=false})
            local selected=s.byKey[slug..':'..spell]
            assert(selected and selected.learn==1,slug..':'..spell..':capture retained old threshold')
            s.recipes={selected};s.known={};s.classID=4;s.raceID=1;s.level=60
            s.professions={[slug]={cur=1,max=300}};s.toolGoals={};s.specializationGoals={}
            for _,mat in ipairs(selected.mats)do s.prices[mat[1]]=1;s.nonAuctionable[mat[1]]=nil end
            E.Index(s)
            for _,fixed in ipairs({false,true})do
              local result=ns.ProfRouteSolver.Compute(slug,{snapshot=s,start=1,target=2,
                fixed=fixed and {{1,2,spell,1}} or nil,autoCraftTools=false,recoveryEnabled=false,
                noFormula=true,considerAuctionSupply=false,cpuLimitMs=1000})
              assert(result.targetReached,slug..':'..spell..':'..tostring(result.status))
              local crafted=false
              for _,step in ipairs(result.steps)do if step[3]==spell then crafted=true end end
              assert(crafted and #result.formulas==0,slug..':'..spell..':fees='..#result.formulas..':fixed='..tostring(fixed))
              for _,action in ipairs(result.actions or {})do assert(action.type~='formula')end
            end
          end
        ''')

    def test_automatic_origins_and_row_views_cover_all_affected_professions(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local total,professions,rendered=0,0,0
          for _,slug in ipairs({'alchemy','blacksmithing','enchanting','engineering','leatherworking',
            'tailoring','cooking','mining','herbalism','skinning','poisons'})do
            local found=0;PD.cur=slug
            for spell,info in ns.ProfLearningSources.Each(slug)do
              local automatic=false
              for _,route in ipairs(info.routes)do
                if route.acquisition and route.acquisition.kind=='skillGrant'then automatic=true end
              end
              if automatic then
                found=found+1;total=total+1
                local group=ns.ProfRecipes[slug] or {}
                for _,kind in ipairs({'rows','enchants','crafted'})do
                  for _,raw in ipairs(group[kind] or {})do
                    if (kind=='enchants' and raw[14] or raw[1])==spell then
                      local spec=kind=='enchants' and PD.EnchantSpec(raw) or kind=='crafted' and PD.CraftedSpec(raw) or PD.RecipeSpec(raw)
                      assert(spec.right2==ns.L['随专业技能获得'],slug..':'..spell..':'..kind..':'..tostring(spec.right2))
                      rendered=rendered+1
                    end
                  end
                end
              end
            end
            if found>0 then professions=professions+1 end
          end
          assert(total==37 and professions==10 and rendered>25)
          assert(ns.ProfLearningSources.AutomaticSkillRank('first-aid',3275)==1)
        ''')

    def test_currency_pattern_keeps_merchant_origin_even_without_a_gold_quote(self):
        self.lua.execute('''
          PD.cur='blacksmithing'
          local E=ns.ProfEconomy;local r=E.FindRecipe('blacksmithing',1252263)
          local info=E.GetLearningInfo('blacksmithing',1252263)
          assert(info.routes[1].teachingItemID==251366 and r.item==250514)
          assert(#info.routes[1].acquisition.vendors==2)
          local queried={}
          PD.FormulaOffersByNpc=function(id)queried[id]=true;return nil end
          local card=PD.RecipeLearningCard(r,false)
          assert(card.fid==251366 and card.kind=='currency' and card.text==ns.L['图纸 · 通货兑换'])
          local found=false
          for _,v in ipairs(card.source.vendors)do
            if v.id==256730 then assert(v.cur==3402 and v.amt==30);found=true end
          end
          local text={};for _,line in ipairs(card.lines)do text[#text+1]=line[1]end
          assert(table.concat(text,' '):find('30',1,true),'currency amount was lost in the source tooltip')
          assert(found and queried[251366] and not queried[250514],'product supplier was used as a pattern supplier')
          local quote=E.FormulaFor(r,{known={},prices={},professions={blacksmithing={cur=57,max=300}},noFormula=true})
          assert(not quote.usable and quote.cost==nil,'currency purchase became a free gold offer')
        ''')

    def test_every_profession_retains_known_pattern_origins_without_promoting_unknown_learning(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local checked=0
          for _,slug in ipairs({'alchemy','blacksmithing','enchanting','engineering','leatherworking','tailoring','cooking'})do
            PD.cur=slug
            for _,raw in ipairs(ns.ProfRecipes[slug].rows or {})do
              local r=E.FindRecipe(slug,raw[1]);local info=E.GetLearningInfo(slug,raw[1])
              local trainer=false
              for _,route in ipairs(info and info.routes or {})do
                if route.kind=='trainer' and route.status=='confirmed'then trainer=true end
              end
              if not trainer and r.formula and r.source and #(r.source.vendors or {})>0 then
                local card=PD.RecipeLearningCard(r,false)
                assert(card and (card.kind=='vendor' or card.kind=='both' or card.kind=='currency'),slug..':'..raw[1])
                assert(card.fid==r.formula);checked=checked+1
              end
            end
          end
          assert(checked>100,'cross-profession source audit did not cover real patterns')
        ''')
