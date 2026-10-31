"""Native First Aid data, purchasing, UI and execution use the real Lua paths."""
import json
import unittest
from test_prof_recipe_data_first_aid import runtime, load, add_route_and_execution, ROOT, FIXED_SPELLS
import test_prof_first_aid_ui as ui_fixture


def complete_runtime(locale='zhCN', strict=True):
    lua = runtime(locale, missing=False)
    add_route_and_execution(lua)
    if strict:
        lua.execute('ns.IsForever=true')
        load(lua, 'Data/Data_ProfLearningSources')
    return lua


class FirstAidCompleteTests(unittest.TestCase):
    def test_all_native_rows_and_rinfo_cover_every_authored_step_in_three_locales(self):
        audit = json.loads((ROOT/'data_pipeline/professions/reports/first-aid-recipes-2026-10-30.json').read_text(encoding='utf-8'))
        for locale in ('zhCN','zhTW','enUS'):
            lua = complete_runtime(locale)
            self.assertEqual(lua.eval("#ns.ProfRecipes['first-aid'].rows"),32)
            for row in audit['records']:
                with self.subTest(locale=locale,spell=row['spell']):
                    r = lua.eval('ns.ProfEconomy.FindRecipe')('first-aid',row['spell'])
                    for field in ('item','count','learn','yellow','green','grey'):
                        self.assertEqual(r[field],row[field])
                    self.assertEqual(sorted((m[1],m[2])for m in r['mats'].values()),sorted(map(tuple,row['mats'])))
            lua.execute('''
              local group=ns.ProfRecipes['first-aid']
              for _,step in ipairs(ns.ProfLeveling['first-aid'].steps)do
                local r=assert(ns.ProfEconomy.FindRecipe('first-aid',step[3]))
                assert(r.item>0 and r.count>0 and #r.mats>0 and not r.clientPending)
                assert(r.learn<=step[1] and r.grey>=step[2])
              end
              for _,r in ipairs(group.rows)do
                assert(r[1]~=3273 and r[1]~=3274 and r[1]~=7924 and r[1]~=10846)
              end
              assert(ns.ProfEconomy.FindRecipe('first-aid',3275).count==1)
              assert(ns.ProfEconomy.FindRecipe('first-aid',1259342).count==3)
            ''')

    def test_full_known_fixed_route_matches_authored_shopping_and_can_bind(self):
        lua=complete_runtime()
        lua.execute('''
          for _,r in ipairs(ns.ProfRecipes['first-aid'].rows)do observedKnown[r[1]]=true end
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=300})
          assert(#p.steps==16 and #p.mats==14)
          assert(not p.referenceOnly and not p.referenceShopping and not p.clientPending)
          assert(p.feasible~=false and p.completeCost~=false and p.priced)
          local actual={};for _,m in ipairs(p.mats)do actual[m.id]=(actual[m.id]or 0)+m.count end
          for _,m in ipairs(ns.ProfLeveling['first-aid'].shopping)do assert(actual[m[1]]==m[2],m[1])end
          for _,s in ipairs(p.steps)do assert(s.cost and s.cost>0 and #s.mats>0)end
          local run,reason=ns.ProfExecution.Bind('first-aid',p)
          assert(run,reason)
        ''')

    def test_partial_target_has_real_materials_and_preserves_original_steps(self):
        lua=complete_runtime()
        lua.execute('''
          observedKnown[3275]=true
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=20})
          assert(#p.steps==1 and p.steps[1][2]==20 and #p.mats==1)
          assert(p.mats[1].id==2589 and p.mats[1].count==21 and p.mats[1].cost==21)
          assert(p.feasible~=false and p.completeCost~=false and not p.clientPending)
          assert(ns.ProfLeveling['first-aid'].steps[1][2]==41 and ns.ProfLeveling['first-aid'].steps[1][4]==43)
        ''')

    def test_missing_prices_and_stock_do_not_make_completed_data_free_or_available(self):
        lua=complete_runtime()
        lua.execute('''
          observedKnown[3275]=true
          Auctionator.API.v1.GetAuctionPriceByItemID=function()return nil end
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=20})
          assert(not p.clientPending and #p.mats==1 and p.mats[1].unpriced)
          assert(p.completeCost==false and p.feasible==false)
          assert(not ns.ProfExecution.Bind('first-aid',p))
          Auctionator.API.v1.GetAuctionPriceByItemID=function()return 1 end
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=0,observedAt=1000,
            complete=true,ownerExcluded=true,source='client-auction-results',market=1}end}
          p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=20,considerAuctionSupply=true})
          assert(p.feasible==false and p.completeCost==false and p.mats[1].unavailable)
          assert(not ns.ProfExecution.Bind('first-aid',p))
        ''')

    def test_unknown_learning_defaults_to_trainer_and_observations_still_work(self):
        lua=complete_runtime()
        lua.execute('''
          local E=ns.ProfEconomy
          assert(E.GetLearningInfo('first-aid',3275))
          local r=E.FindRecipe('first-aid',10841)
          local ok,reason,detail=E.RouteRecipeEligibility(r,{known={},professions={['first-aid']={cur=240,max=300}},level=60})
          assert(ok,reason)
          assert(detail.route.kind=='trainer' and detail.route.defaultTrainer)
          assert(detail.quote.usable and detail.quote.cost==nil and detail.quote.unpriced)
          assert(E.LearningSource(r)=='trainer')
          assert(E.GetLearningInfo('first-aid',10841).coverage=='none','default overwrote source evidence')
          observedKnown[10841]=true
          assert(E.RouteRecipeEligibility(E.FindRecipe('first-aid',10841)))
          observedKnown[10841]=nil;currentSkill=240
          E.ScanTrainer(nil,{services={{spell=10841,requirement={level=35,skill=240,available=true}}}})
          assert(E.FindRecipe('first-aid',10841).trainerObserved)
          assert(E.RouteRecipeEligibility(E.FindRecipe('first-aid',10841)))
        ''')

    def test_default_trainer_keeps_skill_gates_and_explicit_item_or_quest_sources(self):
        lua=complete_runtime()
        lua.execute('''
          local E=ns.ProfEconomy
          for _,spell in ipairs({10841,18629,18630})do
            local r=E.FindRecipe('first-aid',spell)
            local s={known={},professions={['first-aid']={cur=r.learn,max=300}},level=60}
            local ok,reason,detail=E.RouteRecipeEligibility(r,s)
            assert(ok and detail.route.kind=='trainer',reason)
            s.professions['first-aid'].cur=r.learn-1
            ok,reason=E.RouteRecipeEligibility(r,s)
            assert(not ok and reason=='skillRequired',reason)
            r.clientUnavailable=true;s.professions['first-aid'].cur=r.learn
            ok,reason=E.RouteRecipeEligibility(r,s)
            assert(not ok and reason=='clientUnavailable',reason)
          end
          for _,spell in ipairs({7929,10840,1244435,1259344,30021,470349})do
            local r=E.FindRecipe('first-aid',spell)
            assert(r.formula and E.LearningSource(r)~='trainer','known book replaced by trainer')
            local _,_,detail=E.SelectLearningRoute(r)
            assert(not (detail and detail.route and detail.route.defaultTrainer))
          end
          local quest={profession='first-aid',spell=999999,learn=1,
            learningRoutes={{kind='quest',questIDs={123},status='unknown'}}}
          assert(E.LearningSource(quest)~='trainer')
          local ok,_,detail=E.SelectLearningRoute(quest)
          assert(not ok and not (detail.route and detail.route.defaultTrainer))
          local other={profession='alchemy',spell=999999,learn=1}
          assert(E.LearningSource(other)~='trainer' and not E.SelectLearningRoute(other))
        ''')

    def test_learning_fingerprint_is_enforced_for_first_aid_execution(self):
        lua=complete_runtime()
        lua.execute('''
          observedKnown[3275]=true
          local p=ns.ProfRouteAuto.FixedPlan('first-aid',{target=20})
          assert(ns.ProfExecution.ValidateLearning(p,'first-aid',p.steps[1]))
          p.learningPolicyFingerprint='old-first-aid-data'
          local ok,reason=ns.ProfExecution.ValidateLearning(p,'first-aid',p.steps[1])
          assert(not ok and reason=='learningPolicyChanged')
        ''')

    def test_recipe_book_rank_is_not_replaced_by_yellow_threshold(self):
        lua=complete_runtime()
        lua.execute('''
          local E=ns.ProfEconomy;local r=E.FindRecipe('first-aid',1244434)
          assert(r.learn==155 and r.yellow==175)
          local info=assert(E.GetLearningInfo('first-aid',1244434))
          local found=false
          for _,route in ipairs(info.routes)do if route.teachingItemID==255723 then
            for _,c in ipairs(route.conditions)do if c.kind=='skill'then assert(c.value==155);found=true end end
          end end
          assert(found)
        ''')

    def test_client_recipe_observations_now_have_native_first_aid_seed(self):
        lua=complete_runtime()
        lua.execute('''
          local calls=0
          C_TradeSkillUI={GetRecipeInfo=function(id)calls=calls+1
            return {recipeID=id,learned=true,requiredSkillRank=1,hasCooldown=false}end}
          ns.ProfEconomy.ReadRecipe(3275)
          assert(calls>0 and ns.ProfRecipeRuntime[3275] and ns.ProfRecipeRuntime[3275].learned)
        ''')


class FirstAidCompleteUITests(unittest.TestCase):
    def test_unknown_first_aid_origin_displays_trainer_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            fixture=ui_fixture.FirstAidUITests();fixture.boot(locale,missing=False)
            lua=fixture.lua;lua.execute('ns.IsForever=true')
            load(lua,'Data/Data_ProfLearningSources')
            lua.execute('''
              for _,spell in ipairs({10841,18629,18630})do
                local recipe=ns.ProfEconomy.FindRecipe('first-aid',spell)
                local card=PD.RecipeLearningCard(recipe,false)
                assert(card and card.kind=='trainer' and card.text==ns.L['训练师'])
              end
            ''')

    def test_real_recipe_rows_and_leveling_costs_in_all_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            fixture=ui_fixture.FirstAidUITests()
            fixture.boot(locale, missing=False)
            lua=fixture.lua
            lua.execute('''
              ns.ProfHost.DG.ItemIcon=function()return 134400 end
              for _,r in ipairs(ns.ProfRecipes['first-aid'].rows)do observedKnown[r[1]]=true end
              local rows={};PD.tab='recipe';PD.RowsRecipe(rows)
              local seen={};for _,r in ipairs(rows)do if r.it then
                seen[r.it[1]]=true
                assert(r.right2~=ns.L['配方资料待补全'])
              end end
              assert(seen[1251] and seen[255716] and seen[279951])
              PD.tab='leveling';rows={};PD.RowsLeveling(rows)
              assert(not PD.lvSummary.referenceOnly and not PD.lvSummary.clientPending)
              local count=0;for _,r in ipairs(rows)do if r.lvstep then
                count=count+1;assert(r.cost~=ns.L['配方资料待补全'])
              end end
              assert(count==16)
            ''')


if __name__=='__main__':unittest.main()
