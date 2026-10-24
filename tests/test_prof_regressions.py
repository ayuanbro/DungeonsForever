"""Regressions from the first Forever client trial (2026-10-17)."""
from pathlib import Path
import unittest
import test_prof_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


class TrialRegressions(unittest.TestCase):
    def setUp(self):
        runtime.RuntimeTests.setUp(self)

    def test_usable_prefix_survives_unreachable_goal(self):
        self.lua.execute('''
          local s=fixture()
          s.recipes[1].grey=3; s.recipes[1].yellow=3; s.recipes[1].green=3
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(r.feasible and r.partial and not r.targetReached and not r.optimal)
          assert(r.plannedTo==3 and r.target==4 and r.total==14)
          assert(#r.steps==1 and r.steps[1][4]==2 and r.steps[1].recipe.mats[1][1]==11)
          assert(#r.mats==1 and r.mats[1].count==2)
          assert(r.status=='incomplete' and #r.blockingDiagnostics>0)
        ''')

    def test_real_ban_never_appears_in_usable_prefix(self):
        self.lua.execute('''
          local s=fixture()
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2,
            exclusions={['alchemy:101']='ban'}})
          assert(not r.feasible and #r.steps==0)
          local excluded=false
          for _,d in ipairs(r.diagnostics) do if d.code=='excluded' then excluded=true end end
          assert(excluded)
        ''')

    def test_obsolete_no_formula_setting_cannot_block_material_route(self):
        self.lua.execute('''
          local s=fixture(); s.known={}; s.recipes[1].formula=99; s.prices[99]=3
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2,noFormula=true})
          assert(r.feasible and r.targetReached and r.total==10 and r.formulasTotal==3)
          for _,d in ipairs(r.diagnostics) do
            assert(d.code~='excluded','setting mislabeled as user exclusion')
            assert(d.code~='formulaExcluded','removed filter still changes route')
          end
          assert(#r.mats==1 and r.mats[1].id==11)
        ''')

    def test_recipe_explicitly_absent_in_client_is_not_crafted(self):
        self.lua.execute('''
          local s=fixture(); s.recipes[1].clientUnavailable=true
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(not r.feasible and #r.actions==0)
          local absent=false
          for _,d in ipairs(r.diagnostics) do if d.code=='clientUnavailable' then absent=true end end
          assert(absent)
        ''')

    def test_obsolete_formula_filter_does_not_change_snapshot_result(self):
        self.lua.execute('''
          local s=fixture(); s.known={}; s.recipes[1].formula=99; s.prices[99]=3
          local a={snapshot=s,start=1,target=2,noFormula=true}
          local b={snapshot=s,start=1,target=2,noFormula=false}
          local ra,rb=finish('alchemy',a),finish('alchemy',b)
          assert(ra.feasible and rb.feasible and ra.total==10 and rb.total==10)
          assert(#ra.mats==1 and #rb.mats==1 and ra.mats[1].id==11 and rb.mats[1].id==11)
        ''')

    def test_auctionator_loading_does_not_create_negative_price_cache(self):
        self.load(str(ROOT/'Core'/'AuctionatorBridge.lua'))
        self.lua.execute('''
          Auctionator={State={Loaded=false},API={v1={}}}
          local queries=0
          Auctionator.API.v1.GetAuctionPriceByItemID=function(caller,id)
            queries=queries+1; assert(caller=='DungeonsForever'); return 17
          end
          assert(not ns.ProfRouteAuto.Available())
          assert(ns.ProfRouteAuto.AHPriceOf(11)==nil and queries==0)
          Auctionator.Database={}; Auctionator.State.Loaded=true
          assert(ns.ProfRouteAuto.Available())
          assert(ns.ProfRouteAuto.AHPriceOf(11)==17 and queries==1)
        ''')

    def test_grey_material_at_skill_cap_does_not_train_next_rank(self):
        self.lua.execute('''
          local s=fixture()
          s.professions.alchemy={cur=75,max=75}
          s.recipes[1].grey=70; s.recipes[1].yellow=40; s.recipes[1].green=60
          s.rankCosts={alchemy={[150]=20}}
          s.rankRequirements={alchemy={[150]={level=50}}}; s.level=30
          local r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(r.feasible and r.total==7 and r.trainingTotal==nil)
          assert(r.finalSkills.alchemy==75)
          for _,a in ipairs(r.actions) do assert(a.type~='train') end
        ''')

    def test_material_crafting_at_cap_does_not_buy_incidental_skill_gain(self):
        self.lua.execute('''
          local s=fixture(); s.professions.alchemy={cur=75,max=75}
          s.recipes[1].grey=100; s.recipes[1].yellow=90; s.recipes[1].green=95
          s.rankCosts={alchemy={[150]=20}}
          local r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(r.feasible and r.total==7 and r.finalSkills.alchemy==75)
          for _,a in ipairs(r.actions) do assert(a.type~='train') end
        ''')


if __name__ == '__main__':
    unittest.main()
