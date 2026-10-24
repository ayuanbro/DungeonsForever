"""Independent origin and final-ledger checks across recovery integration."""
import unittest

import test_prof_recovery_solver as solver_fixtures


class RecoveryAuditTests(unittest.TestCase):
    setUp = solver_fixtures.RecoverySolverTests.setUp

    def test_unusable_opening_stock_does_not_preserve_consumed_crafted_revenue(self):
        self.lua.execute("""
          local mid=recipe('alchemy',101,10,2,{{1,1}},1,2)
          local finish=recipe('alchemy',102,20,1,{{10,2}},2,3)
          local s=recoverySnapshot({mid,finish}, {[1]=20}, {[10]=100,[20]=0})
          local r,j=solveRecovery(s,3,{executionInventory={[10]={count=5,usable=false}}})
          assert(r.targetReached and r.total==20 and r.inventory[10]==5)
          assert(j.best.unusable[10]==5 and j.best.unusableSeed[10]==5)
          assert(j.best.produced[10]==0)
          assert(r.recoveryTotal==0 and r.bestNetTotal==r.netTotal and r.netTotal==20)
          assert(ns.ProfRecovery.StateRevenue(j.best,j.snap)==r.recoveryTotal)
        """)

    def test_derived_fixed_trace_keeps_nonadjacent_same_recipe_accounts_separate(self):
        self.lua.execute("""
          local a=recipe('alchemy',101,10,1,{{1,1}})
          local b=recipe('alchemy',102,20,1,{{1,1}})
          local s=recoverySnapshot({a,b}, {[1]=1}, {[10]=7,[20]=3})
          local r={scheme='fixed',total=3,mats={{id=1,count=3,cost=3}},steps={
            {1,2,101,1,profession='alchemy',recipe=a},
            {2,3,102,1,profession='alchemy',recipe=b},
            {3,4,101,1,profession='alchemy',recipe=a}}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.recoveryTotal==17)
          local cost,revenue=0,0
          for _,step in ipairs(r.steps) do
            assert(step.productionCost==1 and step.attributedCost==1)
            cost=cost+step.attributedCost;revenue=revenue+step.recoveryTotal
          end
          assert(cost==r.total and revenue==r.recoveryTotal)
          assert(r.steps[1].recoveryTotal==7 and r.steps[3].recoveryTotal==7)
        """)

    def test_repeated_fixed_recipe_allocates_revenue_to_actual_final_batch(self):
        self.lua.execute("""
          local a=recipe('alchemy',101,10,1,{{1,1}})
          local b=recipe('alchemy',102,20,1,{{10,1}})
          local s=recoverySnapshot({a,b}, {[1]=1}, {[10]=7,[20]=3})
          local r={scheme='fixed',total=2,mats={{id=1,count=2,cost=2}},steps={
            {1,2,101,1,profession='alchemy',recipe=a},
            {2,3,102,1,profession='alchemy',recipe=b},
            {3,4,101,1,profession='alchemy',recipe=a}}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.recoveryTotal==10)
          assert(r.steps[1].attributedCost==0 and r.steps[1].transferredCost==1)
          assert(r.steps[1].recoveryTotal==0 and r.steps[1].costTransferred)
          assert(r.steps[2].productionCost==1 and r.steps[2].attributedCost==1)
          assert(r.steps[3].attributedCost==1 and r.steps[3].transferredCost==0)
          assert(r.steps[3].recoveryTotal==7 and not r.steps[3].costTransferred)
        """)

    def test_derived_purchase_pack_remainder_stays_with_its_real_consumer(self):
        self.lua.execute("""
          local a=recipe('alchemy',101,10,1,{{1,1}})
          local b=recipe('alchemy',102,20,1,{{2,1}})
          local s=recoverySnapshot({a,b}, {}, {[10]=0,[20]=0})
          local r={scheme='fixed',total=6,mats={{id=1,count=5,cost=5},{id=2,count=1,cost=1}},steps={
            {1,2,101,1,profession='alchemy',recipe=a},
            {2,3,102,1,profession='alchemy',recipe=b}}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.steps[1].productionCost==1 and r.steps[1].attributedCost==5)
          assert(r.steps[2].productionCost==1 and r.steps[2].attributedCost==1)
          assert(#r.purchaseRemainders==1 and r.purchaseRemainders[1].cost==4)
          assert(r.steps[1].attributedCost+r.steps[2].attributedCost==r.total)
        """)

    def test_procurement_demand_sink_preserves_only_natural_surplus_revenue(self):
        self.lua.execute("""
          local mid=recipe('alchemy',101,10,3,{{1,1}},1,1)
          local s=recoverySnapshot({mid}, {[1]=20}, {[10]=100})
          local r,j=ns.ProfRouteSolver.Procure(s,10,2)
          assert(r.feasible and r.procurement and r.total==20)
          assert(r.consumedDemands[10]==2 and j.best.produced[10]==1)
          assert(r.recoveryTotal==100 and r.netTotal==-80)
          assert(ns.ProfRecovery.StateRevenue(j.best,j.snap)==r.recoveryTotal)
          assert(#r.saleOutputs==1 and r.saleOutputs[1].count==1)
          for _,step in ipairs(r.executionSteps) do assert(step.profession~='__purchase') end
          for _,action in ipairs(r.actions) do assert(action.profession~='__purchase') end
        """)

    def test_actual_enchant_normalization_without_scroll_has_no_sale_lot(self):
        self.lua.execute("""
          local enchant=ns.ProfEconomy.Normalize({[5]=1,[6]=10,[7]=10,[8]=10,
            [9]={{1,1}},[10]={skill=true},[14]=101},'alchemy','enchants')
          assert(enchant and enchant.item==nil and enchant.count==0)
          local s=recoverySnapshot({enchant}, {[1]=7}, {[101]=1000})
          local r,j=solveRecovery(s,3)
          assert(r.targetReached and r.total==14 and r.recoveryTotal==0 and r.netTotal==14)
          assert(#r.saleOutputs==0 and ns.ProfRecovery.StateRevenue(j.best,j.snap)==0)
          assert(r.steps[1].productionCost==14 and r.steps[1].attributedCost==14)
        """)


if __name__ == '__main__':
    unittest.main()
