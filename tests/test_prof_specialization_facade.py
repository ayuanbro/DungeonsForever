"""Specialization identities, fixed-route filtering and automatic mode wiring."""
import unittest

import test_prof_runtime as fixture


class SpecializationFacadeTests(unittest.TestCase):
    def setUp(self):
        fixture.RuntimeTests.setUp(self)
        self.load(str(fixture.ROOT / "Core/Data/Data_ProfSpecializationQuests.lua"))
        self.lua.execute("""
          knownAbilities={}
          C_SpellBook={IsSpellKnown=function(id) return knownAbilities[id]==true end}
          UnitFactionGroup=function() return 'Alliance' end
          UnitLevel=function() return 60 end
          ns.ProfSpecializationsMeta={schemaVersion=1,targetBuild='1.60.1.70450',
            sources={recipeItems={sha256='items-a'},trainers={sha256='trainers-a'}}}
          ns.ProfSpecializations={
            [102]={status='confirmed',hasPending=true,routes={
              {kind='trainer',requiredAbility=20219,status='confirmed'},
              {kind='item',itemID=999,requiredAbility=0,status='pending'}}}}
        """)

    def test_expected_acquisition_advances_plan_but_lost_original_ability_blocks_it(self):
        self.lua.execute("""
          local ra=ns.ProfRouteAuto
          ns.ProfEconomy.SetEngineeringSpecialization('gnomish')
          local plan=ra.StampSpecializations({steps={{200,201,101,1}},mats={{id=11,count=1}},total=7},
            'engineering',{target=201})
          knownAbilities[20219]=true
          assert(not ra.SpecializationPlanChanged(plan,'engineering'))
          assert(ra.ValidateSpecializationPlan(plan,'engineering')==plan)
          local learned=ra.StampSpecializations({steps={{200,201,101,1}},mats={{id=11,count=1}},total=7},
            'engineering',{target=201})
          knownAbilities[20219]=nil
          local blocked=ra.ValidateSpecializationPlan(learned,'engineering')
          assert(blocked~=learned and blocked.status=='recalculate_required')
          assert(#blocked.steps==0 and #blocked.mats==0)
          assert(#learned.steps==1 and learned.total==7)
        """)

    def test_changed_selection_and_data_reject_old_plan_without_mutating_it(self):
        self.lua.execute("""
          local ra=ns.ProfRouteAuto
          local plan=ra.StampSpecializations({steps={{1,2,101,1}},total=7},'engineering',{target=2})
          ns.ProfEconomy.SetEngineeringSpecialization('goblin')
          assert(ra.SpecializationPlanChanged(plan,'engineering'))
          assert(plan.specializationPolicy.choice=='none')
          ns.ProfEconomy.SetEngineeringSpecialization('none')
          assert(not ra.SpecializationPlanChanged(plan,'engineering'))
          ns.ProfSpecializationsMeta.sources.trainers.sha256='trainers-b'
          assert(ra.SpecializationPlanChanged(plan,'engineering'))
          assert(plan.total==7)
        """)

    def test_legacy_unstamped_plan_cannot_bypass_new_rules(self):
        self.lua.execute("""
          local old={steps={{200,201,102,1}},mats={{id=11,count=1}},total=7}
          local view=ns.ProfRouteAuto.ValidateSpecializationPlan(old,'engineering')
          assert(view.status=='recalculate_required' and #view.mats==0)
          assert(#old.steps==1 and old.total==7)
        """)

    def test_fixed_route_removes_restricted_rows_and_retains_unknown_ordinary_recipe(self):
        self.lua.execute("""
          ns.ProfRecipes={engineering={rows={
            {101,10,1,'','','',1,210,220,230,false,{{11,1}}},
            {102,12,1,'','','',1,210,220,230,false,{{11,1}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          local steps={{190,200,101,10},{200,201,102,1}}
          local filtered,blocked,goal=ns.ProfRouteAuto.FilterFixedSpecializations('engineering',steps,{target=201})
          assert(#filtered==1 and filtered[1][3]==101 and #blocked==1 and blocked[1].spell==102)
          assert(not goal and #steps==2)
          knownAbilities[20219]=true
          filtered,blocked=ns.ProfRouteAuto.FilterFixedSpecializations('engineering',steps,{target=201})
          assert(#filtered==2 and #blocked==0)
          knownAbilities[20219]=false
          ns.ProfEconomy.SetEngineeringSpecialization('gnomish')
          filtered,blocked,goal=ns.ProfRouteAuto.FilterFixedSpecializations('engineering',steps,{target=201})
          assert(goal and #filtered==1)
        """)

    def test_all_automatic_modes_complete_task_even_when_skill_target_already_met(self):
        for scheme in ("cheapest", "matcost", "crafts", "optim"):
            with self.subTest(scheme=scheme):
                self.lua.globals().testScheme = scheme
                self.lua.execute("""
                  local s={recipes={},prices={[4394]=2,[10507]=3,[4384]=4},
                    professions={engineering={cur=200,max=300}},known={},
                    level=60,faction='A',specializationAbilities={[20219]=false,[20222]=false}}
                  local result=ns.ProfRouteAuto.Compute('engineering',{snapshot=s,start=200,target=200,
                    engineeringSpecialization='goblin',scheme=testScheme})
                  assert(result.feasible and result.targetReached, result.status)
                  assert(result.total==120,tostring(result.total))
                  local quests=0
                  for _,step in ipairs(result.executionSteps) do
                    if step.kind=='specialization_quest' then quests=quests+1;assert(step.questID==3639) end
                  end
                  assert(quests==1 and result.scheme==testScheme)
                  assert(result.specializationPolicy.choice=='goblin')
                """)

    def test_changing_selection_cancels_queued_plan_and_requires_recalculation(self):
        fixture.RuntimeTests.live_capture_fixture(self)
        self.lua.execute("""
          local ra=ns.ProfRouteAuto
          local options={start=1,target=2}
          local first=ra.Get('alchemy',options)
          assert(first.status=='searching')
          ns.ProfEconomy.SetEngineeringSpecialization('goblin')
          local view=ra.Get('alchemy',options)
          assert(view.status=='recalculate_required')
          assert(view.diagnostics[1].code=='specializationChanged')
          ra.Pump('alchemy')
          assert(ra.Get('alchemy',options).status=='recalculate_required')
          assert(#view.mats==0)
        """)

    def test_known_conflict_keeps_executable_prefix_in_all_modes(self):
        self.lua.execute("""
          local s={recipes={{profession='engineering',spell=101,item=10,count=1,
            learn=1,yellow=200,green=210,grey=220,mats={{11,1}}}},prices={[11]=3},
            professions={engineering={cur=199,max=300}},known={['engineering:101']=true},
            level=60,faction='A',specializationAbilities={[20219]=true,[20222]=false}}
          for _,mode in ipairs({'cheapest','matcost','crafts','optim'}) do
            local options={snapshot=s,start=199,target=201,engineeringSpecialization='goblin',scheme=mode}
            local result=ns.ProfRouteAuto.Compute('engineering',options)
            assert(result.feasible and result.partial and not result.targetReached,mode)
            assert(result.plannedTo==200 and #result.executionSteps==1,mode)
            assert(ns.ProfRouteAuto.ValidateSpecializationPlan(result,'engineering',options)==result,mode)
          end
        """)


if __name__ == "__main__":
    unittest.main()
