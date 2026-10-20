"""Specialization quest transitions share the chronological Lua solver ledger."""
from pathlib import Path
import itertools
import unittest

from test_prof_solver import FIXTURES, LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

SPECIALIZATION_FIXTURES = r"""
function engineering(recipes,prices,start,inputs)
  local s=snapshot(recipes,prices)
  s.professions={engineering={cur=start or 199,max=300}}
  s.level=60;s.faction='A'
  s.specializationAbilities={[20219]=false,[20222]=false}
  s.specializationContext={actual='none',choice='goblin'}
  s.specializationGoals={{id='engineering:goblin',questID=3639,abilityID=20222,
    profession='engineering',minSkill=200,minLevel=30,inputs=inputs or {{10,1}}}}
  for _,r in ipairs(recipes) do r.yellow=300;r.green=300 end
  return s
end
function solve(s,start,target,extra)
  local opts=extra or {};opts.snapshot=s;opts.start=start;opts.target=target
  local result,job=ns.ProfRouteSolver.Compute('engineering',opts)
  assert(not job.error,tostring(job.error))
  return result,job
end
function questStep(result)
  local found
  for _,step in ipairs(result.executionSteps) do
    if step.kind=='specialization_quest' then assert(not found);found=step end
  end
  return found
end
function bought(result,item)
  local n=0
  for _,m in ipairs(result.mats) do if m.id==item then n=n+m.count end end
  return n
end
"""


class SpecializationSolverTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES + SPECIALIZATION_FIXTURES)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        load(str(ROOT / "Core" / "ProfEconomy.lua"))
        load(str(ROOT / "Core" / "ProfRouteSolver.lua"))

    def test_target_at_threshold_still_consumes_quest_and_unlocks(self):
        self.lua.execute("""
          local s=engineering({}, {[10]=4},200,{{10,3}})
          local r=solve(s,200,200)
          local q=questStep(r)
          assert(r.feasible and r.targetReached and q)
          assert(r.total==12 and r.crafts==0 and bought(r,10)==3)
          assert(r.inventory[10]==0 and r.completedSpecializationGoals['engineering:goblin'])
          assert(r.specializationAbilities[20222] and q.cost==12)
          assert(q[1]==200 and q[2]==200 and q[3]==0 and q[4]==0)
          assert(not q.goalSkill and not q.checkpoint and not next(q.requiredOutputs))
        """)

    def test_leveling_output_is_consumed_once_and_not_sold(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',101,10,2,{{11,1}},199,200)},
            {[10]=100,[11]=7},199,{{10,2}})
          local r=solve(s,199,200)
          local q=questStep(r)
          assert(r.targetReached and r.total==7 and r.crafts==1)
          assert(bought(r,11)==1 and bought(r,10)==0 and r.inventory[10]==0)
          assert(r.productAH==0 and #r.executionSteps==2)
          local craft=r.executionSteps[1]
          assert(craft.role=='both' and craft.requiredOutputs[10]==2)
          assert(#craft.allocations==1 and craft.allocations[1].consumerID==q.segmentID)
          assert(craft.allocations[1].count==2 and craft.materialMinCrafts==1)
          assert(r.total==craft.cost+q.cost)
        """)

    def test_grey_nested_producers_survive_cleanup(self):
        self.lua.execute("""
          local s=engineering({
            recipe('engineering',101,10,1,{{12,2}},1,150),
            recipe('engineering',102,12,2,{{11,1}},1,150)},
            {[10]=40,[12]=15,[11]=3},200,{{10,2}})
          local r=solve(s,200,200)
          assert(r.targetReached and r.total==6 and r.crafts==4)
          assert(countCrafts(r,101)==2 and countCrafts(r,102)==2)
          assert(bought(r,11)==2 and bought(r,10)==0 and bought(r,12)==0)
          assert(r.inventory[10]==0 and r.inventory[12]==0 and #r.executionSteps==3)
          assert(r.executionSteps[1].role=='material' and r.executionSteps[2].role=='material')
          assert(r.executionSteps[2].allocations[1].consumerID==questStep(r).segmentID)
        """)

    def test_quest_inputs_share_supplier_pack_and_reserve_dependencies(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',101,10,1,{{11,2}},1,150)},
            {[10]=100},200,{{11,1},{10,1}})
          s.offers={[11]={{unlimited=true,price=5,quantity=3,npcID=5}}}
          local r=solve(s,200,200)
          assert(r.targetReached and r.total==5 and bought(r,11)==3)
          assert(r.inventory[11]==0 and r.inventory[10]==0)
          assert(countCrafts(r,101)==1 and r.matTotal==r.vendorTotal)
        """)

    def test_quest_crafting_recursion_rejects_other_profession_even_with_quote(self):
        self.lua.execute("""
          local s=engineering({recipe('alchemy',101,10,1,{{11,1}},1,150),
            recipe('engineering',102,10,1,{{12,1}},1,150)}, {[10]=20,[11]=1,[12]=4},200)
          s.professions.alchemy={cur=300,max=300}
          local r=solve(s,200,200)
          assert(r.targetReached and r.total==4 and countCrafts(r,101)==0)
          assert(countCrafts(r,102)==1 and bought(r,12)==1)
          s.recipes={recipe('engineering',103,10,1,{{12,1}},1,150),
            recipe('alchemy',104,12,1,{{11,1}},1,150)}
          s.prices={[10]=20,[12]=8,[11]=1}
          r=solve(s,200,200)
          assert(r.targetReached and r.total==8 and countCrafts(r,104)==0 and bought(r,12)==1)
        """)

    def test_locked_recipe_only_used_after_quest_and_sink_not_reused(self):
        self.lua.execute("""
          local s=engineering({
            recipe('engineering',101,10,1,{{11,1}},199,200),
            recipe('engineering',102,20,1,{{10,1}},200,202)}, {[11]=3,[10]=10},199)
          s.known['engineering:102']=false;s.recipes[2].learnSource='trainer'
          ns.ProfSpecializations={[102]={routes={{kind='trainer',status='confirmed',requiredAbility=20222}}}}
          local r=solve(s,199,201)
          assert(r.targetReached and r.total==6 and countCrafts(r,101)==2)
          assert(countCrafts(r,102)==1 and r.inventory[10]==0)
          local seen=false
          for _,a in ipairs(r.actions) do
            if a.type=='specialization_quest' then seen=true end
            if a.type=='craft' and a.spell==102 then assert(seen) end
          end
          assert(questStep(r).abilityID==20222)
        """)

    def test_finite_supply_shared_between_leveling_and_task(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',101,20,1,{{11,1}},199,200),
            recipe('engineering',102,10,1,{{11,1}},1,150)}, {[11]=2,[10]=100},199)
          s.auctionSupply={[11]={quantity=1,price=2,stamp=1000}}
          s.offers={[11]={{unlimited=true,price=5,quantity=1,npcID=5}}}
          local r=solve(s,199,200)
          assert(r.targetReached and r.total==7 and bought(r,11)==2)
          assert(r.ahTotal==2 and r.vendorTotal==5 and countCrafts(r,102)==1)
        """)

    def test_task_procurement_matches_independent_integer_oracle(self):
        # The route consumes A once; the quest consumes A three times and B once.
        # A can be bought from finite AH / packs of 3, or crafted 2 at a time
        # from R. R itself has AH / packs of 2. B is bought or made from A + Q.
        # This enumerates supplier/craft counts independently of Lua's search.
        for price_a, price_r, price_b, supply_a in itertools.product(
            (1, 3, 7), (2, 5), (2, 12), (1, 2)
        ):
            expected = float("inf")
            for buy_b in (0, 1):
                make_b = 1 - buy_b
                need_a = 4 + make_b
                for make_a in range((need_a + 1) // 2 + 1):
                    raw_cost = min(
                        ah_r * price_r + packs_r * 5
                        for ah_r in range(make_a + 1)
                        for packs_r in range((make_a + 1) // 2 + 1)
                        if ah_r + 2 * packs_r >= make_a
                    )
                    for ah_a in range(supply_a + 1):
                        for packs_a in range((need_a + 2) // 3 + 1):
                            if 2 * make_a + ah_a + 3 * packs_a >= need_a:
                                expected = min(
                                    expected,
                                    ah_a * price_a + packs_a * 8 + raw_cost
                                    + buy_b * price_b + make_b * 3,
                                )
            with self.subTest(prices=(price_a, price_r, price_b), supply=supply_a):
                self.lua.globals().oracle_price_a = price_a
                self.lua.globals().oracle_price_r = price_r
                self.lua.globals().oracle_price_b = price_b
                self.lua.globals().oracle_supply_a = supply_a
                self.lua.globals().oracle_expected = expected
                self.lua.execute("""
                  local s=engineering({
                    recipe('engineering',101,10,2,{{11,1}},1,150),
                    recipe('engineering',102,20,1,{{10,1},{12,1}},1,150),
                    recipe('engineering',103,30,1,{{10,1}},199,200)},
                    {[10]=oracle_price_a,[11]=oracle_price_r,[12]=3,[20]=oracle_price_b},
                    199,{{10,3},{20,1}})
                  s.auctionSupply={[10]={quantity=oracle_supply_a,price=oracle_price_a,stamp=1000}}
                  s.offers={[10]={{unlimited=true,price=8,quantity=3,npcID=5}},
                    [11]={{unlimited=true,price=5,quantity=2,npcID=6}}}
                  local r=solve(s,199,200)
                  assert(r.targetReached and r.costComplete)
                  assert(r.total==oracle_expected,'oracle '..oracle_expected..', solver '..r.total)
                  local ah=0;local stepCost=0
                  for _,m in ipairs(r.mats) do if m.id==10 and m.source=='ah' then ah=ah+m.count end end
                  for _,step in ipairs(r.executionSteps) do stepCost=stepCost+step.cost end
                  assert(ah<=oracle_supply_a and stepCost==r.total)
                  assert(r.inventory[10]>=0 and r.inventory[20]>=0)
                """)

    def test_unavailable_task_keeps_leveling_prefix_without_false_completion(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',101,20,1,{{11,1}},199,200)},
            {[11]=3},199,{{10,1}})
          local r=solve(s,199,200)
          assert(r.feasible and r.partial and not r.targetReached and r.plannedTo==200)
          assert(r.total==3 and not questStep(r))
          assert(not r.specializationAbilities[20222])
        """)

    def test_zero_skill_task_remains_useful_prefix_when_later_leveling_blocked(self):
        self.lua.execute("""
          local s=engineering({}, {[10]=4},200)
          for _,mode in ipairs({'cheapest','crafts'}) do
            local opts={scheme=mode}
            if mode=='crafts' then opts.specializationRecipeScore=function() return 1 end end
            local r=solve(s,200,201,opts)
            assert(r.feasible and r.partial and not r.targetReached and r.status=='incomplete')
            assert(r.total==4 and questStep(r) and r.completedSpecializationGoals['engineering:goblin'])
          end
        """)

    def test_global_route_can_pay_more_for_leveling_to_avoid_expensive_quest_purchase(self):
        self.lua.execute("""
          local s=engineering({
            recipe('engineering',101,20,1,{{11,1}},199,200),
            recipe('engineering',102,10,1,{{12,1}},199,200)},
            {[11]=1,[12]=5,[10]=20},199)
          local r=solve(s,199,200)
          assert(r.targetReached and r.total==5 and countCrafts(r,101)==0)
          assert(countCrafts(r,102)==1 and bought(r,10)==0)
        """)

    def test_unknown_ability_or_insufficient_level_cannot_unlock(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',101,20,1,{{11,1}},199,200)},
            {[11]=3,[10]=4},199)
          s.specializationAbilities={};s.specializationContext.actual='unknown'
          local r=solve(s,199,200)
          assert(r.partial and not r.targetReached and not questStep(r) and r.total==3)
          s.specializationAbilities={[20219]=false,[20222]=false}
          s.specializationContext.actual='none';s.level=29
          r=solve(s,199,200)
          assert(r.partial and not r.targetReached and not questStep(r) and r.total==3)
        """)

    def test_actual_learned_branch_skips_task_and_allows_recipe(self):
        self.lua.execute("""
          local s=engineering({recipe('engineering',101,20,1,{{11,1}},200,202)}, {[11]=3},200)
          s.specializationAbilities[20222]=true;s.specializationContext.actual='goblin'
          s.known['engineering:101']=false;s.recipes[1].learnSource='trainer'
          ns.ProfSpecializations={[101]={routes={{kind='trainer',status='confirmed',requiredAbility=20222}}}}
          local r=solve(s,200,201)
          assert(r.targetReached and not questStep(r) and r.total==3)
        """)

    def test_mode_score_preserved_and_task_still_uses_cheapest_procurement(self):
        self.lua.execute("""
          local s=engineering({
            recipe('engineering',101,20,1,{{11,1}},199,200),
            recipe('engineering',102,21,1,{{12,1}},199,200),
            recipe('engineering',103,10,1,{{13,1}},1,150)},
            {[11]=1,[12]=9,[13]=2,[10]=30},199)
          local calls=0
          local r=solve(s,199,200,{scheme='crafts',specializationRecipeScore=function(recipe,state,snapshot,cost)
            calls=calls+1;assert(state.skill.engineering==199 and cost>0)
            return recipe.spell==102 and 1 or 2
          end})
          assert(calls>0 and r.scheme=='crafts' and not r.optimal)
          assert(r.targetReached and r.total==11 and countCrafts(r,102)==1 and countCrafts(r,101)==0)
          assert(countCrafts(r,103)==1 and bought(r,10)==0)
        """)

    def test_fractional_mode_score_receives_one_craft_cost_once(self):
        self.lua.execute("""
          local s=engineering({
            recipe('engineering',101,10,1,{{11,1}},190,200),
            recipe('engineering',102,20,1,{{12,1}},190,200)},
            {[11]=2,[12]=5,[10]=20},199)
          s.recipes[1].yellow=198;s.recipes[1].green=199
          local r=solve(s,199,200,{scheme='matcost',specializationRecipeScore=function(recipe,state,snapshot,cost)
            if recipe.spell==101 then assert(cost==2,'expected one-craft quote') end
            return cost/ns.ProfEconomy.Gain(recipe,state.skill.engineering)
          end})
          assert(r.targetReached and r.total==4 and countCrafts(r,101)==2 and countCrafts(r,102)==0)
          assert(r.crafts==2 and questStep(r))
        """)

    def test_conflicting_actual_branch_cannot_be_switched_for_free(self):
        self.lua.execute("""
          local s=engineering({}, {[10]=4},200)
          s.specializationAbilities[20219]=true
          s.specializationContext.selectionConflict=true
          local r=solve(s,200,200)
          assert(not r.targetReached and not questStep(r) and not r.feasible)
        """)

    def test_conflict_preserves_prefix_to_threshold_and_does_not_raise_lower_target(self):
        self.lua.execute("""
          local s=engineering({
            recipe('engineering',101,20,1,{{11,1}},190,200),
            recipe('engineering',102,21,1,{{12,1}},190,210)},
            {[11]=3,[12]=1,[10]=4},199)
          s.specializationAbilities[20219]=true
          s.specializationGoals=nil
          s.known['engineering:102']=false;s.recipes[2].learnSource='trainer'
          ns.ProfSpecializations={[102]={routes={{kind='trainer',status='confirmed',requiredAbility=20222}}}}
          local r=solve(s,199,201)
          assert(r.feasible and r.partial and r.plannedTo==200 and not r.targetReached)
          assert(r.total==3 and countCrafts(r,101)==1 and countCrafts(r,102)==0 and not questStep(r))
          local found=false
          for _,d in ipairs(r.blockingDiagnostics or {}) do if d.code=='specializationChoiceConflict' then found=true end end
          assert(found)
          r=solve(s,198,199)
          assert(r.targetReached and r.target==199 and r.plannedTo==199 and not questStep(r))
          assert(r.total==3 and countCrafts(r,102)==0)
        """)


if __name__ == "__main__":
    unittest.main()
