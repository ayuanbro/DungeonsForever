"""Recovery search is checked against independently enumerated complete routes."""
import itertools
from pathlib import Path
import unittest

from test_prof_solver import FIXTURES, LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

RECOVERY_FIXTURES = r"""
function recoverySnapshot(recipes,prices,sales,enabled)
  local s=snapshot(recipes,prices)
  s.professions={alchemy={cur=1,max=300}}
  s.recovery={revision=1,enabled=enabled~=false,feePercent=0,feeSource='manual',quotes={}}
  for id,unit in pairs(sales or {}) do s.recovery.quotes[id]={unit=unit,npcUnit=unit,source='npc'} end
  for _,r in ipairs(recipes) do r.yellow=300;r.green=300 end
  return s
end
function solveRecovery(s,target,extra)
  local opts=extra or {};opts.snapshot=s;opts.start=1;opts.target=target or 3
  local result,job=ns.ProfRouteSolver.Compute('alchemy',opts)
  assert(not job.error,tostring(job.error))
  return result,job
end
function saleCount(result,id)
  for _,row in ipairs(result.saleOutputs or {}) do if (row.itemID or row.id or row.item)==id then return row.count or row.sellCount or row.quantity end end
  return 0
end
"""


class RecoverySolverTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES + RECOVERY_FIXTURES)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        for name in ("ProfRecovery.lua", "ProfEconomy.lua", "ProfRouteSolver.lua"):
            load(str(ROOT / "Core" / name))

    def test_expensive_purchase_prefix_can_win_by_final_net_cost(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}}),
            recipe('alchemy',102,20,1,{{2,1}})}, {[1]=1,[2]=30}, {[10]=0,[20]=100})
          local r,j=solveRecovery(s)
          assert(r.targetReached and r.total==60 and countCrafts(r,102)==2,tostring(r.total))
          assert(r.recoveryTotal==200 and r.netTotal==-140)
          assert(r.recoveryOptimized and r.searchComplete and not r.budgetLimited)
          assert(r.bestNetTotal==r.netTotal and r.initialNetTotal-r.netSavings==r.bestNetTotal)
          assert(j.best.money==60)
        """)

    def test_disabled_recovery_and_other_schemes_keep_purchase_objective(self):
        for scheme, enabled in (("cheapest", False), ("fewest", True), ("materials", True)):
            with self.subTest(scheme=scheme, enabled=enabled):
                self.lua.globals().scheme = scheme
                self.lua.globals().enabled = enabled
                self.lua.execute("""
                  local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}}),
                    recipe('alchemy',102,20,1,{{2,1}})}, {[1]=1,[2]=30}, {[20]=100},enabled)
                  local r=solveRecovery(s,3,{scheme=scheme})
                  assert(r.total==2 and countCrafts(r,101)==2 and not r.recoveryOptimized)
                """)

    def test_equal_net_cost_prefers_lower_purchase_cash(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}}),
            recipe('alchemy',102,20,1,{{2,1}})}, {[1]=10,[2]=20}, {[10]=10,[20]=20})
          local r=solveRecovery(s,3)
          assert(r.netTotal==0 and r.total==20 and countCrafts(r,101)==2)
        """)

    def test_sale_relevant_finished_inventory_survives_state_merging(self):
        self.lua.execute("""
          local valuable=recipe('alchemy',101,10,1,{{1,1}},1,2)
          local cheap=recipe('alchemy',102,20,1,{{2,1}},1,2)
          local finish=recipe('alchemy',103,30,1,{{2,1}},2,5)
          local s=recoverySnapshot({valuable,cheap,finish}, {[1]=20,[2]=1}, {[10]=100})
          local r=solveRecovery(s,5)
          assert(r.total==23 and r.netTotal==-77 and countCrafts(r,101)==1)
          assert(countCrafts(r,103)==3 and r.inventory[10]==1)
        """)

    def test_consumed_intermediates_are_not_sale_income_and_natural_surplus_is(self):
        self.lua.execute("""
          local mid=recipe('alchemy',101,10,3,{{1,1}},1,2)
          local finish=recipe('alchemy',102,20,1,{{10,2}},2,3)
          local s=recoverySnapshot({mid,finish},{[1]=20}, {[10]=7,[20]=3})
          local r,j=solveRecovery(s,3)
          assert(r.total==20 and r.inventory[10]==1 and r.inventory[20]==1)
          assert(j.best.produced[10]==1 and j.best.produced[20]==1)
          assert(r.recoveryTotal==10 and r.netTotal==10,tostring(r.recoveryTotal))
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==1)
          assert(r.executionSteps[1].requiredOutputs[10]==2)
        """)

    def test_profitable_outputs_do_not_trigger_extra_or_post_target_crafts(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,100,{{1,1}})}, {[1]=1}, {[10]=1000})
          local r=solveRecovery(s,3)
          assert(r.crafts==2 and r.inventory[10]==200 and r.plannedTo==3)
          assert(r.recoveryTotal==200000 and r.total==2)
          for _,a in ipairs(r.actions) do if a.type=='craft' then assert(a.from<3 and a.count==1) end end
        """)

    def test_procurement_topups_keep_purchase_objective_but_show_surplus(self):
        self.lua.execute("""
          local mid=recipe('alchemy',101,10,2,{{1,1}},1,1)
          local s=recoverySnapshot({mid}, {[1]=20,[10]=1}, {[10]=100})
          local r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(r.feasible and r.total==1 and countCrafts(r,101)==0)
          assert(not r.recoveryOptimized and r.recoveryTotal==0)
        """)

    def test_unknown_sale_quotes_preserve_feasible_purchase_routes(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}})}, {[1]=7},{})
          local r=solveRecovery(s,3)
          assert(r.targetReached and r.total==14 and r.recoveryTotal==0 and r.netTotal==14)
        """)

    def test_purchased_pack_surplus_is_not_crafted_sale_revenue(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}})}, {}, {[1]=1000,[10]=5})
          s.offers={[1]={{price=3,quantity=5,unlimited=true}}}
          local r,j=solveRecovery(s,3)
          assert(r.total==3 and r.inventory[1]==3 and (j.best.produced[1] or 0)==0)
          assert(r.recoveryTotal==10 and r.netTotal==-7)
        """)

    def test_budget_end_keeps_best_complete_route_without_optimal_claim(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}})}, {[1]=5}, {[10]=7})
          local r=solveRecovery(s,3,{maxNodes=1})
          assert(r.targetReached and r.total==10 and r.netTotal==-4)
          assert(r.budgetLimited and not r.searchComplete and not r.optimal)
          assert(r.searchTermination=='node_limit' and r.searchCpuLimitMs==5000)
        """)

    def test_node_limit_on_last_frontier_state_preserves_exhaustion_proof(self):
        # This graph contains exactly the initial state and two one-point
        # crafts. Stopping at its third state leaves no unexplored candidate.
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}})}, {[1]=5}, {[10]=7})
          local r,j=solveRecovery(s,3,{maxNodes=3})
          assert(r.expanded==3 and r.targetReached and r.total==10 and r.netTotal==-4)
          assert(r.searchComplete and not r.budgetLimited and r.optimal)
          assert(r.searchTermination=='exhausted' and r.searchCpuMs==j.cpuUsed)
        """)

    def test_cpu_limit_reports_reason_and_retains_complete_route(self):
        self.lua.execute("""
          local s=recoverySnapshot({recipe('alchemy',101,10,1,{{1,1}})}, {[1]=5}, {[10]=7})
          local j=ns.ProfRouteSolver.NewJob('alchemy',{snapshot=s,start=1,target=3})
          while not j.best do ns.ProfRouteSolver.Run(j,2) end
          -- Account for an already consumed prior slice, then let the actual
          -- scheduler cross its CPU threshold at the next coroutine yield.
          j.cpuUsed=4999
          local clock=0
          debugprofilestop=function() clock=clock+2;return clock end
          ns.ProfRouteSolver.Run(j,2)
          local r=j.result
          assert(j.finished and r.targetReached and r.total==10 and r.netTotal==-4)
          assert(r.status=='complete' and r.budgetLimited and not r.searchComplete and not r.optimal)
          assert(r.searchTermination=='cpu_limit' and r.searchCpuMs==j.cpuUsed)
          assert(r.searchCpuMs>=r.searchCpuLimitMs and r.searchCpuLimitMs==5000)
        """)

    def test_small_routes_match_exhaustive_purchase_pack_and_sale_oracle(self):
        # Enumerate every complete recipe sequence and all useful AH/vendor
        # acquisition splits. Purchased raw leftovers have no resale credit.
        for ah_price, pack_size, pack_price, supply in itertools.product((1, 3), (2, 3), (2, 5), (1, 4)):
            recipes = ((101, 10, 1, 1, 0), (102, 20, 2, 1, 4), (103, 30, 3, 2, 2))
            best = [None]

            def visit(level, inventory, used, purchase, revenue):
                if level == 4:
                    value = (purchase - revenue, purchase)
                    if best[0] is None or value < best[0]:
                        best[0] = value
                    return
                for _, _, output_count, need, sale in recipes:
                    missing = max(0, need - inventory)
                    for packs in range((missing + pack_size - 1) // pack_size + 1):
                        auction = max(0, missing - packs * pack_size)
                        if used + auction <= supply:
                            visit(level + 1, inventory + packs * pack_size + auction - need,
                                  used + auction, purchase + packs * pack_price + auction * ah_price,
                                  revenue + output_count * sale)

            visit(1, 0, 0, 0, 0)
            with self.subTest(ah=ah_price, pack=pack_size, cost=pack_price, supply=supply):
                self.lua.execute(f"""
                  local s=recoverySnapshot({{recipe('alchemy',101,10,1,{{{{1,1}}}}),
                    recipe('alchemy',102,20,2,{{{{1,1}}}}),recipe('alchemy',103,30,3,{{{{1,2}}}})}},
                    {{[1]={ah_price}}}, {{[10]=0,[20]=4,[30]=2}})
                  s.offers={{[1]={{{{price={pack_price},quantity={pack_size},unlimited=true}}}}}}
                  s.auctionSupply={{[1]={{quantity={supply},complete=true,observedAt=1000}}}}
                  local r=solveRecovery(s,4)
                  assert(r.targetReached and r.searchComplete and not r.budgetLimited)
                  assert(r.netTotal=={best[0][0]} and r.total=={best[0][1]},
                    tostring(r.netTotal)..'/'..tostring(r.total)..' expected {best[0]}')
                """)


if __name__ == "__main__":
    unittest.main()
