"""Native first-aid gaps remain explicit without runtime data supplements."""
import unittest

from test_prof_native_data import native_runtime, ROOT

FIXED_SPELLS={3275,3276,3277,3278,7928,7929,10840,10841,18629,18630,
              1244431,1244432,1244433,1259342}


def runtime(locale="zhCN"):
    lua=native_runtime(locale)
    lua.execute("""
      selected='first-aid';currentSkill=1
      ns.ProfModule.ProfLearned=function()return {['first-aid']={cur=currentSkill,max=300}}end
      ns.ProfEconomy.EnsureClientRuntime()
    """)
    return lua


def load(lua,name):
    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT/"Core"/(name+".lua")).read_text(encoding="utf-8-sig"))


def add_route_and_execution(lua):
    lua.execute("""
      callbacks={};ns.Init=function(fn)callbacks[#callbacks+1]=fn end
      function CreateFrame()
        local frame={events={}}
        function frame:RegisterEvent(event)self.events[event]=true end
        function frame:UnregisterEvent(event)self.events[event]=nil end
        function frame:UnregisterAllEvents()self.events={}end
        function frame:SetScript(key,fn)self[key]=fn end
        return frame
      end
      C_Timer={After=function()end}
      Auctionator={API={v1={GetAuctionPriceByItemID=function()return 1 end,
        GetVendorPriceByItemID=function()return nil end}}}
      ns.VendorPriceDB={GetPrice=function()return 1 end,GetOffers=function()return {}end,
        GetFormulaOffers=function()return {}end}
      bag={};C_Item={GetItemCount=function(item)return bag[item]or 0 end}
    """)
    for name in ("ProfRouteAuto","ProfTrack","ProfExecution"):
        load(lua,name)
    lua.execute("for _,fn in ipairs(callbacks)do fn()end;callbacks={}")


class FirstAidUnseededBoundaryTests(unittest.TestCase):
    def test_fourteen_authored_spells_remain_references_without_fabricated_recipe_seeds(self):
        for locale in ("zhCN","zhTW","enUS"):
            lua=runtime(locale)
            steps=lua.execute("return ns.ProfLeveling['first-aid'].steps")
            self.assertEqual(len(steps),16)
            self.assertEqual({step[3]for _,step in steps.items()},FIXED_SPELLS)
            for spell in FIXED_SPELLS:
                with self.subTest(locale=locale,spell=spell):
                    self.assertIsNone(lua.eval("ns.ProfEconomy.FindRecipe")("first-aid",spell))
            lua.execute("""
              assert(ns.ProfRecipes['first-aid']==nil)
              assert(ns.ProfLeveling['first-aid'].rinfo==nil)
              assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)
            """)

    def test_first_aid_solver_reports_missing_data_even_if_a_spell_is_known(self):
        for locale in ("zhCN","zhTW","enUS"):
            lua=runtime(locale)
            lua.execute("""
              observedKnown={[3275]=true,[1244431]=true}
              for _,learnedOnly in ipairs({false,true})do
                local result=ns.ProfRouteSolver.Compute('first-aid',{start=1,target=2,
                  learnedOnly=learnedOnly,autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
                assert(not result.feasible and #result.executionSteps==0)
                assert(result.status=='infeasible' or result.status=='incomplete')
              end
              assert(ns.ProfEconomy.FindRecipe('first-aid',3275)==nil)
            """)

    def test_recipe_api_does_not_append_unseeded_first_aid_static_data(self):
        lua=runtime()
        lua.execute("""
          local calls=0
          C_TradeSkillUI={GetRecipeInfo=function(id)
            calls=calls+1;return {recipeID=id,learned=true,requiredSkillRank=1,hasCooldown=false}
          end}
          assert(ns.ProfEconomy.ReadRecipe(3275)==nil)
          assert(ns.ProfEconomy.ReadRecipe(1244431)==nil)
          assert(calls==0,'reader queried a recipe outside the native static index')
          assert(ns.ProfRecipes['first-aid']==nil)
          assert(ns.ProfRecipeRuntime[3275]==nil and ns.ProfRecipeRuntime[1244431]==nil)
        """)

    def test_trainer_observation_does_not_create_missing_static_recipes(self):
        lua=runtime()
        lua.execute("""
          ns.ProfEconomy.ScanTrainer(nil,{services={{spell=3275,
            requirement={level=5,skill=1,skillName='First Aid',available=true}}}})
          assert(ns.ProfEconomy.FindRecipe('first-aid',3275)==nil)
          assert(ns.ProfRecipes['first-aid']==nil and ns.ProfRecipeRuntime[3275]==nil)
          local snapshot=ns.ProfEconomy.Capture('first-aid',{target=2,autoCraftTools=false,recoveryEnabled=false})
          assert(#snapshot.recipes==0)
        """)

    def test_old_saved_runtime_observations_cannot_promote_unknown_static_spells(self):
        lua=runtime()
        lua.execute("""
          -- An earlier save may contain an observation, but it is not an
          -- authorized addition to the preserved dev Data catalogue.
          observedKnown[3275]=true
          ns.ProfRecipeRuntime[3275]={learned=true,available=true,learn=1,item=1251,count=1,
              mats={{2589,1}},validated=true,cooldown=false,cooldownVerified=true}
          assert(ns.ProfEconomy.FindRecipe('first-aid',3275)==nil)
          local snapshot=ns.ProfEconomy.Capture('first-aid',{target=2,autoCraftTools=false,recoveryEnabled=false})
          assert(#snapshot.recipes==0 and snapshot.byKey['first-aid:3275']==nil)
          assert(ns.ProfRecipes['first-aid']==nil)
        """)

    def test_fixed_quantity_summary_stays_pending_and_cannot_start_zero_cost_execution(self):
        lua=runtime()
        add_route_and_execution(lua)
        lua.execute("""
          local steps=ns.ProfLeveling['first-aid'].steps
          local result=assert(ns.ProfRouteAuto.SummarizeSteps(steps,'first-aid',{target=300,scheme='fixed'}))
          assert(#result.steps==16 and #result.mats==0)
          assert(result.feasible==false and result.completeCost==false and result.priced==false)
          assert(result.status=='recalculate_required' and result.clientPending)
          assert(#result.diagnostics>0)
          local pending=false
          for _,d in ipairs(result.diagnostics)do if d.code=='clientDataPending'then pending=true end end
          assert(pending)
          local run,reason=ns.ProfExecution.Bind('first-aid',result)
          assert(run==nil and reason=='pending')
          assert(ns.ProfExecution.GetRun('first-aid')==nil)
        """)

    def test_fixed_filter_rejects_missing_first_aid_seeds_without_removing_authored_reference(self):
        lua=runtime()
        add_route_and_execution(lua)
        lua.execute("""
          local steps=ns.ProfLeveling['first-aid'].steps
          local filtered,blocked=ns.ProfRouteAuto.FilterFixedSpecializations('first-aid',steps,{target=300})
          assert(#filtered==0 and #blocked==16)
          for _,step in ipairs(blocked)do assert(step.reason=='clientDataPending')end
          assert(#steps==16 and steps[1][3]==3275 and steps[1][4]==43)
          assert(steps[1].mats==nil,'unknown materials were written into the guide')
        """)


if __name__=="__main__":
    unittest.main()
