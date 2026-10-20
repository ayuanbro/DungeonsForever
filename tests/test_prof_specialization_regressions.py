"""Independent regressions for specialization gates at integration boundaries."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT
from test_prof_solver import FIXTURES
from test_prof_specialization_solver import SPECIALIZATION_FIXTURES


class SpecializationProcurementRegressions(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES + SPECIALIZATION_FIXTURES)
        load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ("ProfEconomy.lua", "ProfRouteSolver.lua"):
            load(str(ROOT / "Core" / name))
        self.lua.execute("""
          ns.ProfSpecializations={
            [12760]={hasPending=true,routes={
              {kind='trainer',status='confirmed',requiredAbility=20222},
              {kind='item',status='pending',requiredAbility=0,itemID=123}
            }}
          }
        """)

    def test_supplement_does_not_inherit_unfinished_route_quest(self):
        self.lua.execute("""
          local s=engineering({}, {[10]=4,[11]=2},199,{{10,3}})
          local r,j=ns.ProfRouteSolver.ProcureMany(s,{[11]=2},{materialProfession='engineering'})
          assert(not j.error,tostring(j.error))
          assert(r.feasible and r.targetReached and r.total==4,
            'ordinary top-up was blocked by unfinished route specialization task')
          assert(not questStep(r) and bought(r,10)==0)
          assert(#s.specializationGoals==1,'procurement mutated the caller snapshot')
          assert(j.snap.specializationAbilities[20222]==false)
        """)

    def test_recursive_procurement_blocks_known_requirement_even_with_pending_route(self):
        self.lua.execute("""
          local recipe=recipe('engineering',12760,10,1,{{11,1}},1,300)
          local s=engineering({recipe},{[11]=2},200)
          s.specializationGoals={};s.known={}
          for _,abilities in ipairs({{}, {[20219]=true,[20222]=false}}) do
            s.specializationAbilities=abilities
            local r,j=ns.ProfRouteSolver.ProcureMany(s,{[10]=1},{materialProfession='engineering'})
            assert(not j.error,tostring(j.error))
            assert(not r.targetReached and countCrafts(r,12760)==0)
          end
        """)

    def test_buying_finished_specialization_item_does_not_require_learning_recipe(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',12760,10,1,{{11,1}},1,300)},
            {[10]=9,[11]=2},200)
          s.specializationGoals={};s.known={}
          local r=ns.ProfRouteSolver.ProcureMany(s,{[10]=1},{materialProfession='engineering'})
          assert(r.feasible and r.targetReached and r.total==9)
          assert(countCrafts(r,12760)==0 and bought(r,10)==1)
        """)

    def test_learned_recursive_recipe_bypasses_learning_but_not_client_availability(self):
        self.lua.execute("""
          local producer=recipe('engineering',12760,10,1,{{11,1}},1,300)
          local s=engineering({producer},{[11]=2},200)
          s.specializationGoals={}
          local r=ns.ProfRouteSolver.ProcureMany(s,{[10]=1},{materialProfession='engineering'})
          assert(r.targetReached and r.total==2 and countCrafts(r,12760)==1)
          producer.clientUnavailable=true
          r=ns.ProfRouteSolver.ProcureMany(s,{[10]=1},{materialProfession='engineering'})
          assert(not r.targetReached and countCrafts(r,12760)==0)
        """)


class SpecializationFrozenPlanRegressions(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ("ProfEconomy.lua", "ProfRouteSolver.lua", "ProfRouteAuto.lua"):
            load(str(ROOT / "Core" / name))
        self.lua.execute("""
          E=ns.ProfEconomy;RA=ns.ProfRouteAuto
          abilities={[20219]=false,[20222]=false,[9787]=false}
          C_SpellBook={IsSpellKnown=function(id) return abilities[id] end}
          E.SetEngineeringSpecialization('goblin')
          function frozen()
            return RA.StampSpecializations({steps={{199,200,101,1}},mats={{11,1}},
              executionSteps={{199,200,101,1}},actions={},target=200},'engineering',{target=200})
          end
        """)

    def test_expected_new_ability_preserves_frozen_plan(self):
        self.lua.execute("""
          local plan=frozen()
          abilities[20222]=true
          assert(not RA.SpecializationPlanChanged(plan,'engineering'))
          assert(RA.ValidateSpecializationPlan(plan,'engineering')==plan)
          abilities[9787]=true
          assert(not RA.SpecializationPlanChanged(plan,'engineering'),
            'an unrelated newly learned ability invalidated the execution plan')
        """)

    def test_new_opposite_ability_and_changed_choice_block_frozen_plan(self):
        self.lua.execute("""
          local plan=frozen()
          abilities[20219]=true
          assert(RA.SpecializationPlanChanged(plan,'engineering'))
          local blocked=RA.ValidateSpecializationPlan(plan,'engineering')
          assert(blocked.status=='recalculate_required' and #blocked.steps==0 and #blocked.mats==0)
          abilities[20219]=false
          E.SetEngineeringSpecialization('gnomish')
          assert(RA.SpecializationPlanChanged(plan,'engineering'))
          assert(#plan.steps==1 and #plan.mats==1,'validation mutated execution facts')
        """)

    def test_lost_original_ability_or_unknown_read_blocks_frozen_plan(self):
        self.lua.execute("""
          abilities[20222]=true;abilities[9787]=true
          local plan=frozen()
          abilities[9787]=nil
          assert(RA.SpecializationPlanChanged(plan,'engineering'))
          abilities[9787]=true;abilities[20222]=false
          assert(RA.SpecializationPlanChanged(plan,'engineering'))
        """)

    def test_legacy_modes_filter_both_catalog_rows_and_guide_only_recipes(self):
        self.lua.execute("""
          E.SetEngineeringSpecialization('none')
          ns.ProfSpecializations={
            [12760]={hasPending=true,routes={
              {kind='trainer',status='confirmed',requiredAbility=20222},
              {kind='item',status='pending',requiredAbility=0}
            }},
            [101]={routes={{kind='trainer',status='pending',requiredAbility=0}}}
          }
          ns.ProfRecipes={engineering={rows={
            {12760,10,1,'','','',1,20,30,40,false,{{11,1}}},
            {101,12,1,'','','',1,20,30,40,false,{{11,2}}}
          }}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfLeveling={engineering={}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function() return 2 end}}}
          for _,mode in ipairs({'crafts','matcost','optim'}) do
            local r=RA.Compute('engineering',{start=1,target=2,scheme=mode})
            assert(#r.steps==1 and r.steps[1][3]==101,mode..' bypassed the row gate')
          end
          ns.ProfRecipes={engineering={rows={}}}
          ns.ProfLeveling={engineering={rinfo={
            [12760]={learn=1,yellow=20,green=30,grey=40,item=10,count=1,mats={{11,1}}},
            [101]={learn=1,yellow=20,green=30,grey=40,item=12,count=1,mats={{11,2}}}
          }}}
          RA.Invalidate()
          for _,mode in ipairs({'crafts','matcost','optim'}) do
            local r=RA.Compute('engineering',{start=1,target=2,scheme=mode})
            assert(#r.steps==1 and r.steps[1][3]==101,mode..' bypassed the guide-only gate')
          end
        """)


if __name__ == "__main__":
    unittest.main()
