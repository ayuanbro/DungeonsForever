"""Retired source opt-ins cannot invent a route or affect persisted plans."""
import unittest
from test_prof_production_learning_ui import production_ui_runtime
from test_prof_native_data import ROOT

class RetiredLearningOptionTests(unittest.TestCase):
    def setUp(self):
        self.lua=production_ui_runtime()
        self.lua.execute("""
          PD.Wrap=function(t)return {t}end
          function unavailableRecipe()
            return {profession='alchemy',spell=990001,key='alchemy:990001',learn=1,
              learningSourcesRequired=true,learningInfo={profession='alchemy',spell=990001,
              routes={},coverage='none',missingReasons={'learningSourceMissing'}}}
          end
        """)

    def test_old_opt_in_cannot_invent_a_learning_channel(self):
        self.lua.execute("""
          local E=ns.ProfEconomy
          for _,old in ipairs({false,true})do
            local s=E.Capture('alchemy',{start=1,target=2,allowUnknownLearning=old})
            local ok,why=E.RouteRecipeEligibility(unavailableRecipe(),s)
            assert(not ok and why=='learningDataMissing')
            assert(s.allowUnknownLearning==nil)
          end
          assert(E.AllowUnknownLearning==nil)
        """)

    def test_saved_retired_settings_are_ignored_and_rows_removed(self):
        self.lua.execute("""
          local keys={'autoLearnedOnly','autoAllowUnknownLearning','autoSkipUnpricedFormulas','autoNoFormula'}
          for _,key in ipairs(keys)do
            DungeonsForeverDB.prof[key]=true
            PD.SetSettingRaw(key,true,'alchemy')
            assert(not PD.Setting(key,'alchemy'))
          end
          local o=PD.BuildLvOpts('alchemy',1)
          assert(o.learnedOnly==nil and o.allowUnknownLearning==nil and o.skipUnpricedFormulas==nil and o.noFormula==nil)
          local rows={};PD.RowsSettings(rows)
          for _,row in ipairs(rows)do for _,key in ipairs(keys)do
            assert(row.settingKey~=key and row.key~=key)
          end end
        """)

    def test_known_recipe_needs_no_new_acquisition(self):
        self.lua.execute("""
          local E=ns.ProfEconomy;local r=unavailableRecipe()
          local ok,_,detail=E.RouteRecipeEligibility(r,{known={[990001]=true}})
          assert(ok and detail.status=='learned')
          r.clientUnavailable=true
          local usable,why=E.RouteRecipeEligibility(r,{known={[990001]=true}})
          assert(not usable and why=='clientUnavailable')
        """)

    def test_unknown_actual_condition_is_not_missing_source_documentation(self):
        self.lua.execute("""
          local E=ns.ProfEconomy;local r=E.FindRecipe('alchemy',17554)
          r.learningConstraints={{kind='playerCondition',value=123}}
          local ok,why=E.RouteRecipeEligibility(r,nil,{skill={alchemy=300}})
          assert(not ok and why=='learningDataMissing')
          r.learningConstraints={{kind='raceIDs',values={8}}}
          ok,why=E.RouteRecipeEligibility(r,nil,{skill={alchemy=300}})
          assert(not ok and why=='characterRaceRequired')
        """)

class RetiredLearningCacheTests(unittest.TestCase):
    def setUp(self):
        from test_prof_route_plans import NativeRoutePlansTests
        NativeRoutePlansTests.setUp(self)
        self.load((ROOT/'Core/ProfLearning.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute("ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end")

    def test_retired_option_does_not_stale_a_saved_plan(self):
        self.lua.execute("""
          local RA=ns.ProfRouteAuto;local opts={start=1,target=3,allowUnknownLearning=false}
          local p=finish('alchemy',opts)
          assert(not RA.Get('alchemy',opts).stale)
          opts.allowUnknownLearning=true;opts.noFormula=true;opts.learnedOnly=true;opts.skipUnpricedFormulas=true
          assert(RA.Get('alchemy',opts)==p and not p.stale)
          assert(not RA.HasWork('alchemy'))
        """)

if __name__=='__main__':unittest.main()
