"""Sale evidence boundaries and independent recursive spending attribution."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime",
             Path.home() / "AppData/Local/Temp/df-lua-runtime", ROOT / ".pipeline-runtime/lib"):
    sys.path.insert(0, str(path))
from lupa.lua51 import LuaRuntime


class RecoveryEconomicsTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r'''
          ns={LoadForeverPages=true};clock=200000;time=function()return clock end
          function snap()
            return {recipes={{profession='alchemy',spell=1,item=10,count=2,mats={{100,1}}}},
              prices={[10]=500},sellPrices={[10]=100},auctionSupply={
                [10]={quantity=40,complete=true,ownerExcluded=true,observedAt=clock,source='client-auction-results'}}}
          end
          function capture(s,opts) return ns.ProfRecovery.Capture(s,opts or {recoveryFeePercent=0}) end
          function close(a,b) assert(math.abs(a-b)<1e-7,tostring(a)..' != '..tostring(b)) end
          function line(id,spell,n) return {1,2,spell,n or 1,profession='alchemy',actionID=id,actionIDs={id}} end
          function craft(id,spell,item,n,inputs,count)
            return {type='craft',id=id,profession='alchemy',spell=spell,count=count or 1,item=item,
                    outputs=item and {{item,n}} or {},inputs=inputs or {}}
          end
          function find(list,id) for _,r in ipairs(list)do if r.id==id then return r end end end
        ''')
        self.lua.execute("assert(loadfile(...))('DungeonsForever',ns)", str(ROOT / "Core/ProfRecovery.lua"))

    def test_copper_spread_and_quantity_boundaries(self):
        self.lua.execute(r'''
          local s=snap();s.prices[10]=200;assert(capture(s).quotes[10].source=='npc')
          s=snap();s.prices[10]=201;assert(capture(s).quotes[10].source=='ah')
          s=snap();s.auctionSupply[10].quantity=39;assert(capture(s).quotes[10].source=='npc')
          s=snap();s.auctionSupply[10].quantity=40;assert(capture(s).quotes[10].source=='ah')
        ''')

    def test_two_days_inclusive_and_future_unknown_partial_history_fail(self):
        self.lua.execute(r'''
          local s=snap();s.auctionSupply[10].observedAt=clock-172800
          assert(capture(s).quotes[10].source=='ah')
          s=snap();s.auctionSupply[10].observedAt=clock-172801
          assert(capture(s).quotes[10].source=='npc')
          for _,field in ipairs({'quantity','complete','ownerExcluded','observedAt'})do
            s=snap();s.auctionSupply[10][field]=nil;assert(capture(s).quotes[10].source=='npc',field)
          end
          for _,source in ipairs({'auctionator-daily-maximum','auctionator-update','unknown','history'})do
            s=snap();s.auctionSupply[10].source=source;assert(capture(s).quotes[10].source=='npc')
          end
          s=snap();s.auctionSupply[10].source=nil;assert(capture(s).quotes[10].source=='npc')
          s=snap();s.auctionSupply[10].observedAt=clock+1;assert(capture(s).quotes[10].source=='npc')
        ''')

    def test_net_fee_is_floored_per_item(self):
        self.lua.execute(r'''
          local s=snap();s.prices[10]=211
          local q=capture(s,{recoveryFeePercent=5}).quotes[10]
          assert(q.auctionNet==200 and q.source=='npc')
          s=snap();s.prices[10]=212
          q=capture(s,{recoveryFeePercent=5}).quotes[10]
          assert(q.auctionNet==201 and q.source=='ah')
        ''')

    def test_fee_source_order_manual_client_auctionator_unknown(self):
        self.lua.execute(r'''
          Auctionator={Constants={AfterAHCut=.95}}
          local s=snap();local r=ns.ProfRecovery.Capture(s,{})
          close(r.feePercent,5);assert(r.feeReference and r.feeSource=='auctionator-reference')
          s=snap();s.auctionFee={percent=7,reliable=true,source='verified-client'}
          r=ns.ProfRecovery.Capture(s,{});assert(r.feePercent==7 and not r.feeReference)
          s=snap();s.auctionFee={percent=7,reliable=true}
          r=capture(s,{recoveryFeePercent=9});assert(r.feePercent==9 and r.feeSource=='manual')
          Auctionator=nil;s=snap();r=ns.ProfRecovery.Capture(s,{})
          assert(r.feePercent==nil and r.quotes[10].source=='npc')
        ''')

    def test_zero_sell_price_is_loaded_and_missing_is_not_zero(self):
        self.lua.execute(r'''
          C_Item={GetItemInfo=function() return 'loaded',nil,nil,nil,nil,nil,nil,nil,nil,nil,0 end}
          assert(ns.ProfRecovery.NPCSellPriceOf(10)==0)
          C_Item={GetItemInfo=function() return nil end}
          assert(ns.ProfRecovery.NPCSellPriceOf(10)==nil)
          local s=snap();s.sellPrices[10]=nil
          local q=capture(s).quotes[10];assert(q.missing and q.unit==0 and q.source=='unknown')
          s=snap();s.sellPrices[10]=0;q=capture(s).quotes[10]
          assert(not q.missing and q.source=='ah')
        ''')

    def test_binding_and_no_item_output_do_not_invent_auction_revenue(self):
        self.lua.execute(r'''
          local s=snap();s.nonAuctionable={[10]=true}
          assert(capture(s).quotes[10].source=='npc')
          s=snap();s.recipes[1].item=nil;assert(next(capture(s).quotes)==nil)
          local r={total=10,scheme='cheapest',steps={line('a',1)},actions={craft('a',1,nil,0,{})}}
          ns.ProfRecovery.Apply(r,s);assert(r.recoveryTotal==0 and #r.saleOutputs==0)
        ''')

    def test_missing_client_output_requests_once_but_known_zero_does_not(self):
        self.lua.execute(r'''
          local requests={};ns.ProfHost={DG={RequestItem=function(id)requests[#requests+1]=id end}}
          local s=snap();s.sellPrices[10]=nil;capture(s)
          s=snap();s.sellPrices[10]=nil;capture(s)
          assert(#requests==1 and requests[1]==10)
          s=snap();s.recipes[1].item=20;s.sellPrices[20]=0;capture(s)
          assert(#requests==1)
        ''')

    def test_all_two_hundred_leftovers_use_qualified_forty_quantity(self):
        self.lua.execute(r'''
          local s=snap();capture(s)
          local r={total=500,scheme='cheapest',steps={line('a',1,100)},actions={craft('a',1,10,200,{},100)}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.recoveryTotal==100000 and r.netTotal==-99500 and r.purchaseTotal==500)
          assert(r.saleOutputs[1].count==200 and r.recoveryAssumesAllSold and r.recoveryOptimized)
        ''')

    def test_multilevel_multiple_consumers_formula_and_bundle_cost_conservation(self):
        self.lua.execute(r'''
          local s=snap();s.recipes={}
          for _,pair in ipairs({{1,10},{2,20},{3,30},{4,40}})do
            s.recipes[#s.recipes+1]={profession='alchemy',spell=pair[1],item=pair[2],count=1,mats={}}
          end
          s.sellPrices={[10]=1,[20]=10,[30]=20,[40]=30};s.prices={};capture(s)
          local r={total=30,scheme='cheapest',steps={line('a',1),line('b',2),line('c',3),line('d',4)},
            executionSteps={line('a',1),line('b',2),line('c',3),line('d',4)},actions={
              {type='buy',item=100,count=5,cost=25,owner='alchemy:1'},
              {type='formula',cost=5,owner='alchemy:1'},
              craft('a',1,10,10,{{100,4}}),craft('b',2,20,2,{{10,6}}),
              craft('c',3,30,1,{{10,2}}),craft('d',4,40,1,{{20,1}})}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.recoveryTotal==62 and r.netTotal==-32)
          close(r.steps[1].productionCost,25);close(r.steps[1].transferredCost,20)
          close(r.steps[1].attributedCost,10);close(r.steps[2].productionCost,15)
          close(r.steps[2].transferredCost,7.5);close(r.steps[2].attributedCostExact,7.5)
          close(r.steps[3].attributedCost,5);close(r.steps[4].attributedCostExact,7.5)
          assert(r.steps[2].attributedCost==8 and r.steps[4].attributedCost==7)
          assert(#r.purchaseRemainders==1 and r.purchaseRemainders[1].cost==5)
          for _,list in ipairs({r.steps,r.executionSteps})do
            local cost,revenue=0,0
            for _,step in ipairs(list)do cost=cost+step.attributedCost;revenue=revenue+step.recoveryTotal end
            close(cost,r.total);close(revenue,r.recoveryTotal)
          end
          assert(find(r.saleOutputs,10).count==2 and find(r.saleOutputs,20).count==1)
        ''')

    def test_purchased_identical_items_consumed_first_never_count_as_crafted_sales(self):
        self.lua.execute(r'''
          local s=snap();capture(s)
          local r={total=23,scheme='cheapest',steps={line('a',1),line('b',2)},actions={
            {type='buy',item=10,count=3,cost=3},{type='buy',item=100,count=1,cost=20},
            craft('a',1,10,2,{{100,1}}),craft('b',2,nil,0,{{10,3}})}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.saleOutputs[1].count==2 and r.saleOutputs[1].cost==20)
          assert(r.steps[1].transferredCost==0 and r.steps[2].productionCost==3)
        ''')

    def test_unusable_secondary_output_is_sold_but_never_consumed(self):
        self.lua.execute(r'''
          local s=snap();capture(s)
          local a=craft('a',1,10,2,{});a.usableOutput=false
          local r={total=20,scheme='cheapest',steps={line('a',1),line('b',2),line('c',3)},actions={
            a,{type='buy',item=100,count=1,cost=20},craft('b',2,10,2,{{100,1}}),craft('c',3,nil,0,{{10,2}})}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.saleOutputs[1].count==2 and r.saleOutputs[1].cost==0)
          assert(r.steps[2].transferredCost==20 and r.steps[3].productionCost==20)
        ''')

    def test_natural_batch_remainder_and_leveling_surplus_are_separate(self):
        self.lua.execute(r'''
          local s=snap();capture(s)
          local r={total=0,scheme='cheapest',steps={line('a',1,5),line('b',2)},actions={
            craft('a',1,10,10,{},5),craft('b',2,nil,0,{{10,5}})}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.steps[1].naturalRemainder==1 and r.steps[1].levelingRemainder==4)
          assert(r.steps[1].saleCount==5 and r.steps[1].consumedCount==5)
        ''')

    def test_fixed_trace_and_fishing_craft_only_trace_include_material_and_formula_cost(self):
        self.lua.execute(r'''
          for _,useActions in ipairs({false,true})do
            local s=snap();s.prices={};s.recipes[1].key='alchemy:1';capture(s)
            local step=line('a',1,2);step.recipe=s.recipes[1]
            local r={total=15,scheme='fishing',steps={step},executionSteps={},mats={{id=100,count=3,cost=9}},
              formulas={{cost=6,recipes={{key='alchemy:1'}}}}}
            if useActions then r.actions={craft('a',1,10,4,{{100,2}},2)} end
            ns.ProfRecovery.Apply(r,s)
            assert(r.recoveryTotal==400 and not r.recoveryOptimized)
            assert(r.steps[1].productionCost==12 and r.steps[1].attributedCost==15)
          end
        ''')

    def test_missing_outputs_and_toggle_preserve_forecast(self):
        self.lua.execute(r'''
          local s=snap();s.sellPrices[10]=nil;capture(s,{recoveryEnabled=false,recoveryFeePercent=0})
          local r={total=10,scheme='cheapest',steps={line('a',1)},actions={craft('a',1,10,1,{})}}
          ns.ProfRecovery.Apply(r,s)
          assert(not r.recoveryEnabled and not r.recoveryOptimized and r.recoveryMissing==1)
          assert(r.recoveryMissingItems[1]==10 and r.netTotal==10)
          assert(ns.ProfRecovery.Objective({money=10,produced={[10]=5}},s)==10)
        ''')

    def test_capture_freezes_data_changed_only_marks_new_evidence(self):
        self.lua.execute(r'''
          local s=snap();capture(s)
          local r={total=10,scheme='cheapest',steps={},actions={}}
          ns.ProfRecovery.Apply(r,s)
          local q=r.recoverySnapshot.quotes[10];assert(q.source=='ah')
          local input=snap();assert(not ns.ProfRecovery.Changed(r,{snapshot=input,recoveryFeePercent=0}))
          clock=clock+1;assert(not ns.ProfRecovery.Changed(r,{snapshot=input,recoveryFeePercent=0}))
          input.auctionSupply[10].quantity=39
          assert(ns.ProfRecovery.Changed(r,{snapshot=input,recoveryFeePercent=0}))
          assert(q.source=='ah' and r.recoveryTotal==0)
          s.prices[10]=1;assert(ns.ProfRecovery.Capture(s,{}).quotes[10].auctionGross==500)
          assert(ns.ProfRecovery.Changed({}))
        ''')

    def test_repeat_apply_recomputes_exact_costs_and_rounding_in_both_lists(self):
        self.lua.execute(r'''
          local s=snap();capture(s)
          local r={total=11,scheme='cheapest',steps={line('a',1),line('b',2)},
            executionSteps={line('a',1),line('b',2)},actions={
              {type='buy',item=100,count=1,cost=11},craft('a',1,10,2,{{100,1}}),craft('b',2,nil,0,{{10,1}})}}
          ns.ProfRecovery.Apply(r,s)
          for _,list in ipairs({r.steps,r.executionSteps})do
            assert(list[1].attributedCost==6 and list[2].attributedCost==5)
            close(list[1].attributedCostExact,5.5)
          end
          r.total=17;r.actions[1].cost=17;ns.ProfRecovery.Apply(r,s)
          for _,list in ipairs({r.steps,r.executionSteps})do
            assert(list[1].attributedCost==9 and list[2].attributedCost==8)
            close(list[1].attributedCostExact,8.5)
          end
          assert(r.recoveryTotal==500 and r.netTotal==-483)
        ''')

    def test_top_up_required_outputs_are_kept_and_only_natural_surplus_is_sold(self):
        self.lua.execute(r'''
          for _,need in ipairs({2,3})do
            local s=snap();s.prices={};capture(s)
            local r={total=9,scheme='cheapest',procurement=true,consumedDemands={[10]=need},
              steps={line('a',1)},executionSteps={line('a',1)},actions={
                {type='buy',item=100,count=1,cost=9},craft('a',1,10,3,{{100,1}})}}
            ns.ProfRecovery.Apply(r,s)
            assert(r.recoveryTotal==(3-need)*100 and r.demandCost==need*3)
            assert(r.steps[1].attributedCost==9 and r.executionSteps[1].attributedCost==9)
            assert(r.steps[1].demandCount==need and r.steps[1].demandCost==need*3)
            assert(#r.saleOutputs==(need==3 and 0 or 1) and not r.recoveryOptimized)
            ns.ProfRecovery.Apply(r,s)
            assert(r.recoveryTotal==(3-need)*100 and r.steps[1].attributedCost==9)
          end
          local s=snap();capture(s)
          local r={total=6,scheme='cheapest',procurement=true,consumedDemands={[10]=2},steps={},actions={
            {type='buy',item=10,count=2,cost=6}}}
          ns.ProfRecovery.Apply(r,s)
          assert(r.recoveryTotal==0 and r.demandCost==6 and r.demandNonCraftCost==6 and r.recoveryUnallocatedCost==0)
        ''')


if __name__ == '__main__':
    unittest.main()
