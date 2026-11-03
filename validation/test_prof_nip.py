"""Nip recipes never enter UI choices, route inputs, or execution.

Tests use actual Lua 5.1 modules, shared exclusion IDs and current localized catalogues.
Synthetic prices/skills exercise the policy, not live-server availability.
"""
import unittest
from test_prof_native_data import native_runtime
from test_prof_route_plans import ROOT
import test_prof_route_plans as plan_fixture
import test_prof_ui_fusion as ui_fixture
import test_prof_recipe_data_first_aid as client_fixture

NIP_IDS = {11447, 17579, 22430, 1251750, 2671, 8366, 8368, 9942,
              16960, 16965, 16967, 16980, 16986, 16987, 12719, 12720,
              12722, 12900, 12904, 10550, 19106, 7636, 8778, 12062,
              12063, 12068, 12083, 12087, 12090,
              1252247, 1252248, 1252249, 1252250, 1252251}


def load(lua, path):
    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT / path).read_text(encoding='utf-8-sig'))


class RecipeNIPTests(unittest.TestCase):
    def plans(self):
        plan_fixture.NativeRoutePlansTests.setUp(self)
        load(self.lua, 'Core/Data/Data_ProfRecipes.lua')

    def test_shared_nip_list_is_identical_in_three_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                lua = native_runtime(locale)
                ns = lua.globals().ns
                self.assertEqual(set(ns.ProfRecipeNIP.keys()), NIP_IDS)
                marked = {}
                for slug, group in ns.EnsureProfRecipes().items():
                    for _, row in (group['rows'] or {}).items():
                        if row['nip']:
                            marked[row[1]] = slug
                            self.assertEqual(row['nip'], '未实装到游戏里')
                            self.assertIsNone(ns.ProfEconomy.FindRecipe(slug, row[1]))
                self.assertEqual(set(marked), NIP_IDS)

    def test_normalization_cannot_reintroduce_excluded_recipe_shapes(self):
        lua = native_runtime()
        lua.execute('''
          local E=ns.ProfEconomy
          assert(not E.Normalize({11447,8827,1,'',nil,nil,1,10,20,30,nil,{{11,1}}},'alchemy'))
          assert(not E.Normalize({spell=11447,item=8827,count=1,mats={{11,1}},learn=1,grey=30},'alchemy'))
          assert(not E.Normalize({11447,8827,1,1,10,20,30,{{11,1}}},'alchemy','crafted'))
          local enchant={[14]=11447,[15]=8827,[5]=1,[6]=10,[7]=20,[8]=30,[9]={{11,1}}}
          assert(not E.Normalize(enchant,'enchanting','enchants'))
          assert(not E.Normalize({spell=999999,nip='not implemented'},'alchemy'))
          ns.ProfRecipeRuntime={[11447]={learned=true,available=true,validated=true,item=8827,count=1,mats={{11,1}}}}
          assert(not E.FindRecipe('alchemy',11447))
          assert(E.FindRecipe('alchemy',7183),'ordinary recipe disappeared')
        ''')

    def test_capture_filters_rows_rinfo_crafted_enchants_and_client_reads(self):
        lua = native_runtime()
        lua.execute('''
          local E=ns.ProfEconomy;reads=0
          ns.ProfRecipes={alchemy={rows={{11447,8827,1,'',nil,nil,1,10,20,30,nil,{{11,1}}}},
            crafted={{12062,10010,1,1,10,20,30,{{11,1}}}},
            enchants={{[14]=12719,[15]=10579,[5]=1,[6]=10,[7]=20,[8]=30,[9]={{11,1}}}}}}
          ns.ProfLeveling={alchemy={rinfo={[16960]={makes=12764,count=1,mats={{11,1}},learn=1,grey=30}}}}
          C_TradeSkillUI={GetRecipeInfo=function()reads=reads+1;return {learned=true}end}
          local s=E.Capture('alchemy',{start=1,target=2,autoCraftTools=false})
          assert(#s.recipes==0 and next(s.byKey)==nil and next(s.byItem)==nil and reads==0)
        ''')

    def test_snapshot_filter_keeps_input_immutable_and_product_purchasable(self):
        self.plans()
        self.lua.execute('''
          local s=fixture();local bad=ns.ProfEconomy.Copy(s.recipes[1])
          bad.spell=12719;bad.profession='engineering';bad.item=10579;bad.mats={{99,1}}
          s.recipes[1].mats={{10579,1}};s.recipes[2]=bad
          s.professions.engineering={cur=195,max=300};s.known['engineering:12719']=true
          s.prices={[10579]=7,[99]=1}
          local captured=ns.ProfEconomy.Capture('alchemy',{snapshot=s,autoCraftTools=false})
          assert(#captured.recipes==1 and not captured.byKey['engineering:12719'] and not captured.byItem[10579])
          assert(#s.recipes==2 and s.recipes[2]==bad and captured.prices[10579]==7)
          local r=finish('alchemy',{snapshot=s,start=1,target=2,autoCraftTools=false,recoveryEnabled=false})
          assert(r.feasible and r.total==7 and r.steps[1][3]==101)
        ''')

    def test_both_route_schemes_ignore_cheaper_learned_excluded_recipe(self):
        self.plans()
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','stable'})do
            local s=fixture();local bad=ns.ProfEconomy.Copy(s.recipes[1])
            bad.spell=11447;bad.mats={{99,1}};s.recipes[2]=bad
            s.prices[99]=1;s.known['alchemy:11447']=true
            local r=finish('alchemy',{snapshot=s,start=1,target=3,scheme=scheme,autoCraftTools=false,recoveryEnabled=false})
            assert(r.feasible and r.total==14)
            for _,step in ipairs(r.executionSteps)do assert(step[3]~=11447)end
          end
        ''')

    def test_no_alternative_returns_no_excluded_upgrade_steps(self):
        self.plans()
        self.lua.execute('''
          local s=fixture();s.recipes[1].spell=11447;s.known={['alchemy:11447']=true}
          local r=finish('alchemy',{snapshot=s,start=1,target=2,autoCraftTools=false})
          assert(not r.feasible and #r.steps==0 and #r.executionSteps==0)
        ''')

    def test_direct_nip_flag_is_also_filtered_from_snapshot(self):
        self.plans()
        self.lua.execute('''
          local s=fixture();s.recipes[1].nip='未实装到游戏里'
          local c=ns.ProfEconomy.Capture('alchemy',{snapshot=s})
          assert(#c.recipes==0 and not c.byKey['alchemy:101'] and not c.byItem[10])
        ''')

    def test_known_or_teaching_item_evidence_never_overrides_nip(self):
        lua = native_runtime()
        lua.execute('''
          for _,forever in ipairs({false,true})do
            ns.IsForever=forever;observedKnown[12062]=true
            local rec={spell=12062,profession='tailoring',key='tailoring:12062',trainerAvailable=true,
              learningInfo={routes={{kind='item',teachingItemID=254681}}}}
            for _,check in ipairs({ns.ProfEconomy.RouteRecipeEligibility,ns.ProfEconomy.SelectLearningRoute})do
              local ok,reason=check(rec,{known={['tailoring:12062']=true}})
              assert(not ok and reason=='catalogueFiltered')
            end
          end
        ''')

    def test_fast_candidate_path_cannot_use_rinfo_fallback(self):
        lua = native_runtime()
        client_fixture.add_route_and_execution(lua)
        lua.execute('''
          ns.ProfRecipes={alchemy={rows={}}}
          ns.ProfLeveling={alchemy={rinfo={[11447]={makes=8827,count=1,mats={{11,1}},learn=1,yellow=10,green=20,grey=30}}}}
          ns.ProfRouteAuto.AHPriceOf=function()return 1 end
          local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=2,autoCraftTools=false})
          assert(#r.steps==0 and #r.gaps>0)
        ''')

    def test_skeleton_rejection_does_not_display_or_shorten_blocked_route(self):
        self.plans()
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local original=finish('alchemy',{start=1,target=3})
          local c=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local skel=c.routes[c.active.alchemy].skeleton
          skel.steps[1][3]=11447
        ''')
        load(self.lua, 'Core/ProfRoutePlans.lua')
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(not r.feasible and r.status=='recalculate_required')
          assert(#r.steps==0 and #r.executionSteps==0 and #r.mats==0)
          local found=false;for _,d in ipairs(r.diagnostics)do if d.code=='catalogueFiltered'then found=true end end
          assert(found and not ns.ProfExecution.Bind('alchemy',r))
        ''')

    def test_frozen_embedded_recipe_cannot_bypass_execution_admission(self):
        self.plans()
        self.lua.execute('''
          local r=finish('alchemy',{snapshot=fixture(),start=1,target=3})
          for _,step in ipairs(r.executionSteps)do step[3]=11447;step.spell=11447;step.recipe.spell=11447 end
          local run,reason=ns.ProfExecution.Bind('alchemy',r)
          assert(not run and reason=='catalogueFiltered')
          local ok,why=ns.ProfExecution.ValidateLearning(r,'alchemy',r.executionSteps[1])
          assert(not ok and why=='catalogueFiltered')
        ''')

    def test_continuation_uses_bags_and_cannot_choose_excluded_recipe(self):
        self.plans()
        self.lua.execute('''
          ns.ProfEconomy.Capture=function(slug,opts)
            local s=fixture();s.executionInventory=opts.executionInventory
            local bad=ns.ProfEconomy.Copy(s.recipes[1]);bad.spell=11447;bad.mats={{99,1}}
            s.recipes[2]=bad;s.prices[99]=1;s.known['alchemy:11447']=true
            return ns.ProfEconomy.Index(s)
          end
          local ra=ns.ProfRouteAuto;local original=finish('alchemy',{start=1,target=3})
          local run=assert(ns.ProfExecution.Bind('alchemy',original));bag[11]=1
          ra.Recalculate('alchemy',{start=1,target=3});local r=finish('alchemy',{start=1,target=3})
          assert(r.total==7 and r.seedInventory[11]==1 and run.plan.total==14)
          for _,step in ipairs(r.executionSteps)do assert(step[3]==101)end
        ''')

    def test_fixed_summary_rejects_whole_route_before_costing(self):
        self.plans()
        self.lua.execute('''
          local r=ns.ProfRouteAuto.SummarizeSteps({{1,2,11447,1},{2,3,7183,1}},'alchemy',{})
          assert(not r.feasible and #r.steps==0 and #r.mats==0 and not r.total)
          assert(r.diagnostics[1].code=='catalogueFiltered')
          assert(not ns.ProfEconomy.StepsHaveNIP({{1,2,11447,0,checkpoint=true}}))
        ''')

    def test_ui_list_count_currency_search_and_material_use_exclude_nip(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                lua = native_runtime(locale)
                client_fixture.add_route_and_execution(lua)
                lua.execute('actual={ns.ProfData,ns.ProfRecipes,ns.ProfLeveling}')
                lua.execute(ui_fixture.UI_MOCKS)
                lua.execute('ns.ProfData,ns.ProfRecipes,ns.ProfLeveling=unpack(actual)')
                load(lua, 'Core/ProfessionUI.lua')
                lua.execute('''
                  local PD=ns.ProfModule;PD.cur='alchemy';PD.toolKey='all';PD.moneyKey=nil
                  PD.ItemName=function(id)return 'Item'..tostring(id),true end
                  PD.TextW=function(text)return #text end;PD.RecipeSpec=function(row)return {spell=row[1]}end
                  PD.RowCurHit=function()return true end
                  PD.CurKeysOfFid=function()return nil end
                  local function verify()
                    local rows=PD.RecipeList(10000);local count=PD.ScanRecipe()
                    assert(count==#rows and count>0)
                    for _,r in ipairs(rows)do assert(not ns.ProfRecipeNIP[r.spell])end
                    local d=ns.ProfRecipes[PD.cur]
                    local tools=PD.RecipeTool(d);local types=PD.RecipeTypeItems(d)
                    assert(tools[1].text==format(ns.L['全部 %d'],count))
                    assert(types[1].text==format(ns.L['全部 %d'],count))
                    assert(PD.CurCounts(d)[PD.NO_SELL_KEY]==count)
                  end
                  for _,slug in ipairs({'alchemy','blacksmithing','engineering','leatherworking','tailoring'})do
                    PD.cur=slug;verify();PD.moneyKey=999;verify();PD.moneyKey=nil
                    for _,r in ipairs(ns.ProfRecipes[slug].rows)do
                      if r.nip then assert(not PD.RawHit(r,'item'..r[2]) and not PD.RecipeVisible(r[1]))end
                    end
                  end
                ''')
                # The material-use helper is local: execute its actual function,
                # with only its catalogue accessor replaced for isolation.
                source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
                block = source[source.index('local function MatRecipesUsing(itemId)'):source.index('local function SetMatBan(itemId, ban)')]
                lua.execute('local PD=ns.ProfModule;local function RGet(k)return ns.ProfRecipes[k]end\n' + block + '''
                  PD.cur='alchemy';local group=ns.ProfRecipes.alchemy;local expected={}
                  for _,r in ipairs(group.rows)do
                    for _,m in ipairs(r[12]or{})do
                      for _,id in ipairs(MatRecipesUsing(m[1]))do assert(not ns.ProfRecipeNIP[id])end
                    end
                  end
                ''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
