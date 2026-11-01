"""Master's residual estimate and preference limit through native route search."""
import unittest
import test_prof_route_plans as fixtures


class ProfitPriorityTests(unittest.TestCase):
    def setUp(self):
        fixtures.NativeRoutePlansTests.setUp(self)
        self.lua.execute('''
          function profitFixture()
            local s=fixture();local a=s.recipes[1]
            local b=ns.ProfEconomy.Copy(a);b.spell=102;b.item=12;b.mats={{13,1}};s.recipes[2]=b
            s.known['alchemy:102']=true;s.prices={[11]=100,[13]=50,[10]=500,[12]=1}
            s.sellPrices={[10]=0,[12]=0}
            s.auctionSupply={[10]={quantity=100,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}}
            return s
          end
          function solve(s,target,residual,recovery)
            return ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=target,
              recoveryEnabled=recovery~=false,recoveryFeePercent=0,residualMass=residual==true})
          end
          function counts(r)
            local t={};for _,st in ipairs(r.executionSteps)do t[st[3]]=(t[st[3]] or 0)+st[4]end;return t
          end
        ''')

    def test_profit_preference_stops_at_twenty_but_route_reaches_target(self):
        self.lua.execute('''
          local r=solve(profitFixture(),26);local c=counts(r)
          assert(r.targetReached and r.total==2250 and c[101]==20 and c[102]==5)
          assert(r.netTotal==-7750 and r.priorityTotal==-7750)
        ''')

    def test_required_crafts_over_twenty_remain_allowed_and_all_sales_are_displayed(self):
        self.lua.execute('''
          local s=profitFixture();s.recipes[2]=nil
          local r=solve(s,26);assert(r.targetReached and counts(r)[101]==25)
          assert(r.total==2500 and r.recoveryTotal==12500 and r.netTotal==-10000)
          assert(r.priorityTotal==-7500 and r.profitPriorityLimit==20)
        ''')

    def test_discount_changes_real_recipe_selection(self):
        self.lua.execute('''
          local function input()
            local s=profitFixture();s.prices[11]=300;s.prices[13]=100
            s.prices[10]=600;s.prices[12]=350;s.auctionSupply[12]=ns.ProfEconomy.Copy(s.auctionSupply[10])
            return s
          end
          local full=solve(input(),4,false);local discounted=solve(input(),4,true)
          assert(counts(full)[101]==3 and counts(discounted)[102]==3)
          assert(full.recoveryTotal==1800 and discounted.recoveryTotal==735)
          assert(discounted.residualMass and discounted.recoverySnapshot.quotes[12].auctionGross==350)
        ''')

    def test_discount_applies_before_fee_and_preserves_npc_floor(self):
        self.lua.execute('''
          local s=profitFixture();s.sellPrices[12]=300;s.prices[12]=350
          s.auctionSupply[12]=ns.ProfEconomy.Copy(s.auctionSupply[10])
          local R=ns.ProfRecovery
          local q=R.Capture(s,{recoveryEnabled=true,recoveryFeePercent=5,residualMass=true}).quotes
          assert(q[10].auctionGross==500 and q[10].auctionNet==332)
          assert(q[12].unit==300 and q[12].source=='npc')
          R.Capture(s,{recoveryFeePercent=0,residualMass=false})
          assert(s.recovery.quotes[10].unit==500)
        ''')

    def test_disabled_recovery_and_other_strategy_keep_purchase_objective(self):
        self.lua.execute('''
          local r=solve(profitFixture(),26,true,false)
          assert(counts(r)[102]==25 and not counts(r)[101])
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=profitFixture(),start=1,target=26,
            recoveryEnabled=true,recoveryFeePercent=0,scheme='matcost'})
          assert(counts(r)[102]==25 and not counts(r)[101])
        ''')

    def test_profitable_prerequisite_materials_can_exceed_twenty(self):
        self.lua.execute('''
          local s=profitFixture();local a,b=s.recipes[1],s.recipes[2]
          a.yellow=2;a.green=2;a.grey=2
          b.learn=2;b.mats={{10,25}};s.prices[10]=10000
          local r=solve(s,3);assert(r.targetReached and counts(r)[101]==25 and counts(r)[102]==1)
          assert(r.total==2500 and r.recoveryTotal==0)
        ''')

    def test_setting_is_in_signature_and_skeleton_and_keeps_frozen_execution(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(profitFixture())end
          local ra=ns.ProfRouteAuto;local opts={start=1,target=3,residualMass=true,recoveryEnabled=true}
          local r=finish('alchemy',opts);local run=assert(ns.ProfExecution.Bind('alchemy',r))
          assert(ra.PlanSig('alchemy',opts)~=ra.PlanSig('alchemy',{start=1,target=3,residualMass=false,recoveryEnabled=true}))
          local store=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          assert(store.routes[store.active.alchemy].skeleton.options.residualMass==true)
          local frozen=run.plan
          opts.residualMass=false;assert(ra.Get('alchemy',opts)==frozen and frozen.staleReason=='settings')
        ''')


if __name__=='__main__':unittest.main()
