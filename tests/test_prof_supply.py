"""Finite auction quantities are shared procurement resources, not extra prices."""
import itertools
import unittest

from test_prof_solver import FIXTURES, LuaRuntime, ROOT
from test_prof_runtime import MOCKS


class AuctionSupplySolverTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        for name in ('ProfEconomy.lua', 'ProfRouteSolver.lua'):
            load(str(ROOT / 'Core' / name))
        self.lua.execute(r'''
          function solveSupply(s,target)
            local r,j=ns.ProfRouteSolver.Compute('alchemy',
              {snapshot=s,start=1,target=target})
            assert(not j.error,tostring(j.error));return r
          end
          function ahBought(r,id)
            local n=0
            for _,a in ipairs(r.actions)do
              if a.source=='ah' and a.item==id and
                  (a.type=='buy' or a.type=='formula')then n=n+a.count end
            end
            return n
          end
          function checkSupply(r,s)
            for id,offer in pairs(s.auctionSupply or {})do
              assert(ahBought(r,id)<=offer.quantity,
                'oversold '..id..': '..ahBought(r,id)..' > '..offer.quantity)
            end
            assert(r.total==r.ahTotal+r.vendorTotal,'purchase totals diverged')
            assert(r.total==r.matTotal+r.formulasTotal,'formula total counted twice')
          end
        ''')

    def test_cheapest_then_second_then_third_recipe_exhaust_their_materials(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,20,1,{{11,1}}),
            recipe('alchemy',102,21,1,{{12,1}}),
            recipe('alchemy',103,22,1,{{13,1}})}, {[11]=1,[12]=2,[13]=3})
          s.auctionSupply={[11]={quantity=2,complete=true},
            [12]={quantity=2,complete=true}}
          local r=solveSupply(s,7)
          assert(r.feasible and r.targetReached and r.total==12,tostring(r.total))
          assert(countCrafts(r,101)==2 and countCrafts(r,102)==2 and countCrafts(r,103)==2)
          assert(#r.steps==3);checkSupply(r,s)
        ''')

    def test_recipe_count_is_limited_by_the_smallest_reagent_capacity(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,20,1,{{11,2},{12,3}}),
            recipe('alchemy',102,21,1,{{13,1}})}, {[11]=1,[12]=1,[13]=8})
          s.auctionSupply={[11]={quantity=9,complete=true},
            [12]={quantity=8,complete=true}}
          local r=solveSupply(s,6)
          assert(r.targetReached and r.total==34,tostring(r.total))
          assert(countCrafts(r,101)==2 and countCrafts(r,102)==3)
          assert(ahBought(r,11)==4 and ahBought(r,12)==6);checkSupply(r,s)
        ''')

    def test_different_recipes_share_the_same_remaining_auction_quantity(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{11,1}},1,3)
          a.yellow=3;a.green=3
          local b=recipe('alchemy',102,21,1,{{11,1},{12,1}},3,10)
          local c=recipe('alchemy',103,22,1,{{13,1}})
          local s=snapshot({a,b,c},{[11]=1,[12]=1,[13]=5})
          s.auctionSupply={[11]={quantity=3,complete=true}}
          local r=solveSupply(s,6)
          assert(r.targetReached and r.total==14,tostring(r.total))
          assert(countCrafts(r,101)==2 and countCrafts(r,102)==1 and countCrafts(r,103)==2)
          assert(ahBought(r,11)==3);checkSupply(r,s)
        ''')

    def test_recursive_crafting_replaces_the_unavailable_part_of_an_auction_material(self):
        self.lua.execute('''
          local maker=recipe('alchemy',100,10,2,{{11,1}},1,1)
          local s=snapshot({maker,recipe('alchemy',101,20,1,{{10,1}})},
            {[10]=1,[11]=7})
          s.auctionSupply={[10]={quantity=1,complete=true}}
          local r=solveSupply(s,4)
          assert(r.targetReached and r.total==8,tostring(r.total))
          assert(countCrafts(r,100)==1 and countCrafts(r,101)==3)
          assert(ahBought(r,10)==1 and ahBought(r,11)==1);checkSupply(r,s)
        ''')

    def test_finite_auction_and_integer_crafting_batches_can_be_combined(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',100,10,2,{{11,1}},1,1)},
            {[10]=5,[11]=7})
          s.auctionSupply={[10]={quantity=1,complete=true}}
          local r=ns.ProfRouteSolver.Procure(s,10,3)
          assert(r.feasible and r.total==12,tostring(r.total))
          assert(countCrafts(r,100)==1 and ahBought(r,10)==1);checkSupply(r,s)
        ''')

    def test_finite_auction_and_integer_vendor_packs_can_be_combined(self):
        self.lua.execute('''
          local s=snapshot({}, {[10]=5})
          s.auctionSupply={[10]={quantity=1,complete=true}}
          s.offers={[10]={{unlimited=true,quantity=2,price=7,npcID=7}}}
          local r=ns.ProfRouteSolver.Procure(s,10,3)
          assert(r.feasible and r.total==12 and r.vendorTotal==7 and r.ahTotal==5,
            tostring(r.total))
          assert(ahBought(r,10)==1);checkSupply(r,s)
        ''')

    def test_known_sold_out_and_unknown_quantity_have_different_meanings(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,20,1,{{11,1}}),
            recipe('alchemy',102,21,1,{{12,1}})}, {[11]=1,[12]=5})
          local unknown=solveSupply(s,4)
          assert(unknown.targetReached and unknown.total==3 and countCrafts(unknown,101)==3)
          s.auctionSupply={[11]={quantity=0,complete=true}}
          local empty=solveSupply(s,4)
          assert(empty.targetReached and empty.total==15 and countCrafts(empty,101)==0)
          checkSupply(empty,s)
        ''')

    def test_partial_observation_is_a_conservative_cap_not_unlimited_stock(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,20,1,{{11,1}}),
            recipe('alchemy',102,21,1,{{12,1}})}, {[11]=1,[12]=5})
          s.auctionSupply={[11]={quantity=1,complete=false}}
          local r=solveSupply(s,4)
          assert(r.targetReached and r.total==11,tostring(r.total))
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==2);checkSupply(r,s)
        ''')

    def test_two_limited_green_recipes_can_jointly_supply_one_expected_skill_point(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{11,1}},1,10)
          local b=recipe('alchemy',102,21,1,{{12,1}},1,10)
          a.yellow=1;a.green=1;b.yellow=1;b.green=1
          local s=snapshot({a,b},{[11]=1,[12]=2})
          s.auctionSupply={[11]={quantity=1,complete=true},
            [12]={quantity=1,complete=true}}
          local r=solveSupply(s,2)
          assert(r.targetReached and r.total==3,tostring(r.total))
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==1);checkSupply(r,s)
        ''')

    def test_exhausted_supply_preserves_the_valid_prefix_and_reports_the_material(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,20,1,{{11,1}})}, {[11]=2})
          s.auctionSupply={[11]={quantity=2,complete=true}}
          local r=solveSupply(s,5)
          assert(r.feasible and r.partial and not r.targetReached and r.plannedTo==3)
          assert(r.total==4 and countCrafts(r,101)==2 and #r.steps==1)
          local found=false
          for _,d in ipairs(r.blockingDiagnostics or r.diagnostics or {})do
            if d.item==11 then found=true end
          end
          assert(found,'exhausted material is missing from diagnostics');checkSupply(r,s)
        ''')

    def test_shared_formula_is_bought_once_from_a_single_available_copy(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{11,1}},1,3)
          a.yellow=3;a.green=3;a.formula=99
          local b=recipe('alchemy',102,21,1,{{11,1}},3,5)
          b.yellow=5;b.green=5;b.formula=99
          local s=snapshot({a,b},{[11]=2,[99]=9});s.known={}
          s.auctionSupply={[99]={quantity=1,complete=true}}
          local r=solveSupply(s,5)
          assert(r.targetReached and r.total==17,tostring(r.total))
          assert(#r.formulas==1 and r.formulasTotal==9 and ahBought(r,99)==1)
          assert(countCrafts(r,101)==2 and countCrafts(r,102)==2);checkSupply(r,s)
        ''')

    def test_formula_and_reagent_purchase_share_the_same_item_supply(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{11,1}},1,2)
          a.yellow=2;a.green=2;a.formula=99
          local b=recipe('alchemy',102,21,1,{{99,1}},2,3)
          local c=recipe('alchemy',103,22,1,{{12,1}},2,3)
          local s=snapshot({a,b,c},{[11]=1,[12]=8,[99]=5})
          s.known['alchemy:101']=nil
          s.auctionSupply={[99]={quantity=1,complete=true}}
          local r=solveSupply(s,3)
          assert(r.targetReached and r.total==14,tostring(r.total))
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==0 and countCrafts(r,103)==1)
          assert(ahBought(r,99)==1);checkSupply(r,s)
        ''')

    def test_sold_out_auction_formula_uses_the_vendor_alternative(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{11,1}});a.formula=99
          local s=snapshot({a},{[11]=1,[99]=5});s.known={}
          s.auctionSupply={[99]={quantity=0,complete=true}}
          s.formulaOffers={[99]={{price=10,quantity=1,npcID=7,unlimited=true}}}
          local r=solveSupply(s,2)
          assert(r.targetReached and r.total==11,tostring(r.total))
          assert(#r.formulas==1 and r.formulas[1].source=='vendor' and r.formulas[1].ahPrice==5)
          assert(r.formulaVendorTotal==10 and ahBought(r,99)==0);checkSupply(r,s)
        ''')

    def test_material_consumption_can_block_a_later_formula_without_a_nil_state_error(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{99,1}},1,2)
          a.yellow=2;a.green=2
          local b=recipe('alchemy',102,21,1,{{11,1}},2,3);b.formula=99
          local s=snapshot({a,b},{[11]=1,[99]=5});s.known['alchemy:102']=nil
          s.auctionSupply={[99]={quantity=1,complete=true}}
          local r=solveSupply(s,3)
          assert(r.feasible and r.partial and r.plannedTo==2 and not r.targetReached)
          assert(r.total==5 and countCrafts(r,101)==1 and countCrafts(r,102)==0)
          assert(#r.formulas==0 and ahBought(r,99)==1);checkSupply(r,s)
        ''')

    def test_vendor_formula_can_reserve_the_only_auction_copy_for_a_later_material(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,20,1,{{11,1}},1,2)
          a.yellow=2;a.green=2;a.formula=99
          local b=recipe('alchemy',102,21,1,{{99,1}},2,3)
          local s=snapshot({a,b},{[11]=1,[99]=1});s.known['alchemy:101']=nil
          s.auctionSupply={[99]={quantity=1,complete=true}}
          s.formulaOffers={[99]={{price=5,quantity=1,npcID=7,unlimited=true}}}
          local r=solveSupply(s,3)
          assert(r.targetReached and r.total==7,tostring(r.total))
          assert(r.formulas[1].source=='vendor' and r.formulaVendorTotal==5)
          assert(ahBought(r,99)==1 and countCrafts(r,102)==1);checkSupply(r,s)
        ''')

    def test_small_finite_routes_match_independent_integer_allocation_oracle(self):
        solve = self.lua.eval('''function(points,capA,capShared,priceA,priceB)
          local s=snapshot({recipe('alchemy',101,20,1,{{11,2},{12,1}}),
            recipe('alchemy',102,21,1,{{11,1},{13,1}}),
            recipe('alchemy',103,22,1,{{14,1}})},
            {[11]=1,[12]=priceA,[13]=priceB,[14]=7})
          s.auctionSupply={[11]={quantity=capShared,complete=true},
            [12]={quantity=capA,complete=true},[13]={quantity=2,complete=true}}
          local r=solveSupply(s,points+1)
          assert(r.targetReached,'oracle fixture lost its always-available fallback')
          checkSupply(r,s);return r.total
        end''')
        for points, cap_a, cap_shared, price_a, price_b in itertools.product(
                (2, 4), (0, 1, 3), (1, 3), (1, 4), (2, 5)):
            choices = []
            for a in range(points + 1):
                for b in range(points - a + 1):
                    c = points - a - b
                    if a <= cap_a and 2 * a + b <= cap_shared and b <= 2:
                        choices.append(a * (2 + price_a) + b * (1 + price_b) + 7 * c)
            expected = min(choices)
            actual = solve(points, cap_a, cap_shared, price_a, price_b)
            self.assertEqual(actual, expected,
                             (points, cap_a, cap_shared, price_a, price_b))


class AuctionSupplyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        self.load = load
        for name in ('ProfEconomy.lua', 'ProfRouteSolver.lua', 'ProfRouteAuto.lua'):
            load(str(ROOT / 'Core' / name))
        self.lua.execute('''
          function supplyCatalog(withFormula)
            ns.ProfRecipes={alchemy={rows={
              {101,20,1,'','','',1,20,30,40,false,{{11,1}},withFormula and {99} or nil,{}},
              {102,21,1,'','','',1,20,30,40,false,{{12,1}},nil,{}}}}}
            ns.EnsureProfRecipes=function()return ns.ProfRecipes end
            Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)
              return ({[11]=1,[12]=5,[99]=9})[id]
            end}}}
          end
        ''')

    def test_capture_uses_observed_supply_and_preserves_unknown_as_absent(self):
        self.lua.execute('''
          supplyCatalog(true)
          local observed={[11]={quantity=2,complete=true,observedAt=1000},
            [99]={quantity=1,complete=false,observedAt=1000}}
          local asked={}
          ns.AuctionBridge={GetAuctionSupply=function(id)asked[id]=true;return observed[id]end}
          local s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3})
          assert(s.prices[11]==1 and s.prices[12]==5 and s.prices[99]==9)
          assert(asked[11] and asked[12] and asked[99],'formula or reagent supply was not requested')
          assert(s.auctionSupply[11].quantity==2 and s.auctionSupply[11].complete)
          assert(s.auctionSupply[99].quantity==1 and not s.auctionSupply[99].complete)
          assert(s.auctionSupply[12]==nil,'unknown quantity was turned into zero')
          observed[11].quantity=9
          assert(s.auctionSupply[11].quantity==2,'live supply mutated the captured search input')
        ''')

    def test_supply_summary_combines_formula_and_materials_and_counts_unknown_ids_once(self):
        self.lua.execute('''
          local r={mats={{id=11,count=2,source='ah'}, {id=12,count=4,source='vendor'},
              {id=14,count=1,source='ah'}, {id=14,count=2,source='ah'}},
            formulas={{id=99,count=1,source='ah'}, {id=11,count=1,source='ah'},
              {id=17,count=1,source='ah',known=true}}}
          local s={prices={},auctionSupply={[11]={quantity=2,complete=true,observedAt=1000},
            [99]={quantity=1,complete=false,observedAt=900}}}
          local got=ns.ProfEconomy.SummarizeAuctionSupply(r,s)
          assert(got==r and r.auctionSupplyRevision==2)
          assert(r.auctionSupplyObserved and r.auctionSupplyUnknown==1 and not r.supplyComplete)
          assert(r.mats[1].availableCount==2 and r.mats[1].supplyComplete and r.mats[1].supplyObservedAt==1000)
          assert(r.formulas[1].availableCount==1 and not r.formulas[1].supplyComplete)
          assert(r.formulas[2].supplyLimited,'shared material plus book exceeded supply unnoticed')
          assert(r.mats[2].supplyObserved==nil and r.formulas[3].supplyObserved==nil)
          assert(not r.mats[3].supplyObserved and not r.mats[4].supplyObserved)
        ''')

    def test_legacy_automatic_modes_switch_recipes_when_their_material_is_exhausted(self):
        self.lua.execute('''
          supplyCatalog(false)
          ns.AuctionBridge={GetAuctionSupply=function(id)
            if id==11 then return {quantity=1,complete=true}end
          end}
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=4,scheme=scheme})
            assert(r and #r.steps==2,scheme..' did not supplement the capped recipe')
            local made,bought={},{}
            for _,st in ipairs(r.steps)do made[st[3]]=(made[st[3]] or 0)+st[4]end
            for _,m in ipairs(r.mats)do if m.source=='ah'then bought[m.id]=m.count end end
            assert(made[101]==1 and made[102]==2,scheme)
            assert(bought[11]==1 and bought[12]==2,scheme)
            assert(r.total==11 and r.auctionSupplyObserved,scheme)
          end
        ''')

    def test_fixed_reference_keeps_its_steps_and_marks_the_unavailable_quantity(self):
        self.lua.execute('''
          supplyCatalog(false)
          ns.AuctionBridge={GetAuctionSupply=function(id)
            if id==11 then return {quantity=1,complete=true}end
          end}
          local r=ns.ProfRouteAuto.SummarizeSteps({{1,4,101,3}},'alchemy')
          assert(r and #r.steps==1 and r.steps[1][3]==101 and r.steps[1][4]==3)
          assert(#r.mats==1 and r.mats[1].count==3 and r.mats[1].availableCount==1)
          assert(r.mats[1].supplyLimited and not r.supplyComplete)
        ''')

    def test_legacy_modes_reserve_a_formula_copy_before_spending_the_material_supply(self):
        self.lua.execute('''
          supplyCatalog(true)
          ns.ProfRecipes.alchemy.rows[1][12]={{99,1}}
          Auctionator.API.v1.GetAuctionPriceByItemID=function(_,id)
            return ({[99]=1,[12]=5})[id]
          end
          ns.AuctionBridge={GetAuctionSupply=function(id)
            if id==99 then return {quantity=2,complete=true}end
          end}
          for _,scheme in ipairs({'matcost','crafts','optim'})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=4,scheme=scheme})
            assert(r and #r.steps==2,scheme)
            local made={}
            for _,st in ipairs(r.steps)do made[st[3]]=(made[st[3]] or 0)+st[4]end
            assert(made[101]==1 and made[102]==2,scheme)
            assert(#r.formulas==1 and r.formulasTotal==1 and r.total==12,scheme)
            local consumed=r.formulas[1].count
            for _,m in ipairs(r.mats)do if m.id==99 then consumed=consumed+m.count end end
            assert(consumed==2,scheme..' reused the book auction as a material')
          end
        ''')

    def test_saved_route_without_supply_revision_stays_visible_as_unknown_and_stale(self):
        self.lua.execute('''
          supplyCatalog(false)
          local r=finish('alchemy',{start=1,target=3})
          assert(r.total==2)
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          cache.routes[cache.active.alchemy].result.auctionSupplyRevision=nil
          jobsBefore=#queue
          ns.ProfEconomy.Capture=function()error('restoring a saved route must not recapture')end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.cached and r.stale and r.staleReason=='supply-model' and r.total==2)
          assert(r.auctionSupplyRevision==2 and r.auctionSupplyUnknown==1)
          assert(not r.mats[1].supplyObserved and r.mats[1].availableCount==nil)
          assert(#queue==jobsBefore and r.status=='complete')
        ''')

    def test_restored_observed_supply_waits_for_manual_recalculation(self):
        self.lua.execute('''
          supplyCatalog(false)
          observedQuantity=1
          ns.AuctionBridge={GetAuctionSupply=function(id)
            if id==11 then return {quantity=observedQuantity,complete=true}end
          end}
          captures=0
          local original=ns.ProfEconomy.Capture
          ns.ProfEconomy.Capture=function(...)
            captures=captures+1;return original(...)
          end
          local r=finish('alchemy',{start=1,target=4})
          assert(r.total==11 and r.auctionSupplyObserved and captures==1)
          jobsBefore=#queue;observedQuantity=0
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;local opts={start=1,target=4}
          local r=ra.Get('alchemy',opts)
          assert(r.cached and r.stale and r.staleReason=='supply' and r.total==11)
          assert(captures==1 and #queue==jobsBefore,'opening a stale route restarted the solver')
          ra.Recalculate('alchemy',opts)
          local fresh=finish('alchemy',opts)
          assert(not fresh.stale and fresh.total==15 and captures==2)
          assert(fresh.steps[1][3]==102 and #fresh.steps==1)
        ''')

    def test_capture_freezes_quantity_history_and_separate_price_times(self):
        self.lua.execute('''
          supplyCatalog(true)
          local current={quantity=2,complete=true,observedAt=1792300000,
            source='client-auction-results',ownerExcluded=true,observedPrice=1,
            market='Realm Alliance',batch=8,schemaVersion=2}
          local history={quantity=100,observedAt=1792280000,source='auctionator-daily-maximum'}
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return current end end,
            GetAuctionSupplyHistory=function(id)if id==11 then return history end end,
            GetAuctionPriceObservedAt=function(id)if id==11 then return 1792301000 end end}
          local s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3})
          current.quantity=20;history.quantity=999
          local result={mats={{id=11,source='ah',count=1}},formulas={}}
          ns.ProfEconomy.SummarizeAuctionSupply(result,s)
          local e=result.mats[1]
          assert(e.availableCount==2 and e.supplyObservedAt==1792300000)
          assert(e.supplySource=='client-auction-results' and e.supplyOwnerExcluded)
          assert(e.supplyObservedPrice==1 and e.priceObservedAt==1792301000)
          assert(e.supplyHistoryQuantity==100 and e.supplyHistoryObservedAt==1792280000)
          assert(e.supplyMarket=='Realm Alliance' and e.supplyBatch==8 and e.supplySchemaVersion==2)
        ''')

    def test_history_only_is_reference_and_does_not_limit_material_or_formula(self):
        self.lua.execute('''
          supplyCatalog(true)
          Auctionator.API.v1.GetAuctionPriceByItemID=function(_,id)return ({[11]=1,[12]=50,[99]=9})[id]end
          ns.AuctionBridge={GetAuctionSupply=function()return nil end,
            GetAuctionSupplyHistory=function()
              return {quantity=0,observedAt=1792280000,source='auctionator-daily-maximum'}
            end}
          local r=finish('alchemy',{start=1,target=3})
          assert(r.targetReached and r.total==11)
          assert(r.auctionSupplyUnknown==2 and not r.auctionSupplyObserved)
          assert(r.mats[1].supplyHistoryQuantity==0 and not r.mats[1].supplyObserved)
          assert(r.formulas[1].supplyHistoryQuantity==0 and r.formulas[1].availableCount==nil)
          assert(not r.mats[1].supplyLimited and not r.formulas[1].supplyLimited)
          local s=ns.ProfEconomy.Index({auctionSupply={[11]={quantity=0,source='auctionator-daily-maximum'}}})
          assert(s.auctionSupply[11]==nil,'daily maximum entered the solver purchase budget')
        ''')

    def test_aggregate_estimate_with_owned_auctions_cannot_claim_supply_complete(self):
        self.lua.execute('''
          local r={mats={{id=11,count=1,source='ah'}},formulas={}}
          ns.ProfEconomy.SummarizeAuctionSupply(r,{prices={},auctionSupply={
            [11]={quantity=5,complete=true,ownerExcluded=false,source='auctionator-update'}}})
          assert(r.mats[1].availableCount==5 and r.mats[1].supplyOwnerExcluded==false)
          assert(not r.supplyComplete,'unfiltered market total was labelled a verified buyable count')
        ''')

    def test_matching_persisted_observation_restores_without_becoming_stale(self):
        self.lua.execute('''
          supplyCatalog(false)
          observed={quantity=100,complete=true,observedAt=1792300000,
            source='client-auction-results',ownerExcluded=true,market='Realm Alliance',batch=8,schemaVersion=2}
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return observed end end}
          original=finish('alchemy',{start=1,target=3})
          assert(original.total==2 and not original.stale)
          jobsBefore=#queue
          ns.ProfEconomy.Capture=function()error('reload must not recapture')end
          time=function()return 1792600000 end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.cached and not r.stale and r.total==2 and #queue==jobsBefore)
          assert(r.mats[1].supplyObservedAt==1792300000,'reload replaced the observation time')
        ''')

    def test_replaced_observation_with_same_quantity_stales_by_identity(self):
        self.lua.execute('''
          supplyCatalog(false)
          observed={quantity=100,complete=true,observedAt=1792300000,
            source='client-auction-results',ownerExcluded=true,market='Realm Alliance',batch=8,schemaVersion=2}
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return observed end end}
          finish('alchemy',{start=1,target=3});jobsBefore=#queue
          observed.observedAt=1792301000;observed.batch=9
          ns.ProfEconomy.Capture=function()error('a changed observation must wait for manual recalculation')end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.cached and r.stale and r.staleReason=='supply' and #queue==jobsBefore)
          assert(r.mats[1].supplyObservedAt==1792300000,'saved input was silently replaced')
        ''')

    def test_previously_unknown_unused_candidate_quantity_marks_saved_input_changed(self):
        self.lua.execute('''
          supplyCatalog(false)
          observed={}
          ns.AuctionBridge={GetAuctionSupply=function(id)return observed[id]end}
          local r=finish('alchemy',{start=1,target=3})
          assert(r.total==2 and r.auctionSupplyInputs[12]==false)
          observed[12]={quantity=2,complete=true,observedAt=1792300000,schemaVersion=2}
          jobsBefore=#queue
          ns.ProfEconomy.Capture=function()error('candidate changes must not automatically rerun')end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.stale and r.staleReason=='supply' and r.total==2 and #queue==jobsBefore)
        ''')

    def test_history_and_price_timestamp_changes_do_not_change_quantity_inputs(self):
        self.lua.execute('''
          supplyCatalog(false)
          historyQuantity=100;priceTime=1792300000
          ns.AuctionBridge={GetAuctionSupply=function()return nil end,
            GetAuctionSupplyHistory=function()return {quantity=historyQuantity,observedAt=1792280000}end,
            GetAuctionPriceObservedAt=function()return priceTime end}
          finish('alchemy',{start=1,target=3});jobsBefore=#queue
          historyQuantity=999;priceTime=1792400000
          ns.ProfEconomy.Capture=function()error('history reference refresh must not recapture')end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.cached and not r.stale and r.total==2 and #queue==jobsBefore)
          assert(r.mats[1].supplyHistoryQuantity==100 and r.mats[1].priceObservedAt==1792300000)
        ''')

    def test_revision_one_uptime_metadata_is_cleared_without_discarding_route(self):
        self.lua.execute('''
          supplyCatalog(false)
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then
            return {quantity=2,complete=true,observedAt=500,source='client-auction-results'}
          end end}
          finish('alchemy',{start=1,target=3})
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          cache.routes[cache.active.alchemy].result.auctionSupplyRevision=1
          jobsBefore=#queue
          ns.ProfEconomy.Capture=function()error('uptime migration must not recapture')end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r.cached and r.stale and r.staleReason=='supply-model' and r.total==2)
          assert(r.mats[1].supplyObservedAt==nil and r.mats[1].availableCount==nil)
          assert(not r.mats[1].supplyObserved and r.auctionSupplyRevision==2 and #queue==jobsBefore)
        ''')

    def test_real_bridge_saved_observation_and_route_survive_reload_together(self):
        self.lua.execute('''
          supplyCatalog(false)
          clock=1792300000
          function time()return clock end
          function UnitFactionGroup()return 'Alliance' end
          function GetBuildInfo()return '1.60.1','70338','',16000 end
          function hooksecurefunc(target,key,callback)
            assert(type(target)=='table' and type(target[key])=='function')
            local original=target[key]
            target[key]=function(...)
              local result={original(...)};callback(...);return unpack(result)
            end
          end
          function flushBridge()
            for i=1,10 do
              if #timers==0 then return end
              local current=timers;timers={};for _,callback in ipairs(current)do callback()end
            end
            error('bridge refresh did not settle')
          end
          auctionatorHistory={price=1,maximum=100}
          function resetDatabaseObject()
            Auctionator.Database={}
            function Auctionator.Database:SetPrice(key,price,available)
              assert(key=='11');auctionatorHistory.price=price
              if available~=nil then auctionatorHistory.maximum=math.max(auctionatorHistory.maximum,available)end
            end
            function Auctionator.Database:GetPriceHistory(key)
              return key=='11' and {{rawDay=5,available=auctionatorHistory.maximum}} or {}
            end
            Auctionator.Constants={SCAN_DAY_0=1791800000}
          end
          resetDatabaseObject()
        ''')
        self.load(str(ROOT / 'Core' / 'AuctionatorBridge.lua'))
        self.lua.execute('''
          Auctionator.Database:SetPrice('11',1,2);flushBridge()
          local observed=ns.AuctionBridge.GetAuctionSupply(11,true)
          assert(observed.quantity==2 and observed.observedAt==1792300000 and observed.schemaVersion==2)
          assert(observed.source=='auctionator-update' and observed.ownerExcluded==false)
          assert(auctionatorHistory.maximum==100,'bridge overwrote Auctionator history')
          local r=finish('alchemy',{start=1,target=4})
          assert(r.total==7 and r.targetReached and r.auctionSupplyRevision==2)
          local material;for _,entry in ipairs(r.mats)do if entry.id==11 then material=entry end end
          assert(material.availableCount==2 and material.supplySource=='auctionator-update')
          assert(material.supplySchemaVersion==2 and material.supplyObservedAt==1792300000)
          assert(material.supplyObservedPrice==1 and material.priceObservedAt==1792300000)
          assert(material.supplyHistoryQuantity==100 and not r.supplyComplete)
          jobsBefore=#queue;clock=clock+3*86400;timers={};resetDatabaseObject()
          ns.ProfEconomy.Capture=function()error('reload opened a new route calculation')end
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.load(str(ROOT / 'Core' / 'AuctionatorBridge.lua'))
        self.lua.execute('''
          ns.AuctionBridge.Refresh('readiness');flushBridge()
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=4})
          assert(r.cached and not r.stale and r.total==7 and #queue==jobsBefore)
          local observed=ns.AuctionBridge.GetAuctionSupply(11,true)
          assert(observed.quantity==2 and observed.old and observed.observedAt==1792300000)
          assert(auctionatorHistory.maximum==100,'reload modified Auctionator data')
          assert(r.auctionSupplyInputs[11].market==observed.market)
          assert(r.auctionSupplyInputs[11].batch==observed.batch)
        ''')

    def test_search_before_auction_show_then_recalculate_clears_unknown_quantity(self):
        self.lua.execute('''
          supplyCatalog(false)
          function time()return 1792300000 end
          function UnitFactionGroup()return 'Alliance' end
          function QueryAuctionItems(...)if queryHook then queryHook(...)end end
          function hooksecurefunc(name,callback)
            assert(name=='QueryAuctionItems');queryHook=callback
          end
          local row={ [1]='Reagent', [3]=10, [10]=10, [14]='Other', [16]=0, [17]=11 }
          function GetNumAuctionItems()return 1,1 end
          function GetAuctionItemInfo()return unpack(row,1,17)end
        ''')
        self.load(str(ROOT / 'Core' / 'AuctionatorBridge.lua'))
        self.lua.execute('''
          local opts={start=1,target=3}
          local old=finish('alchemy',opts)
          assert(old.auctionSupplyUnknown==1 and old.mats[1].id==11)
          local before=#queue
          local frame=frames[#frames]
          QueryAuctionItems('Reagent',nil,nil,0,nil,nil,false,true,nil)
          frame.OnEvent(frame,'AUCTION_HOUSE_SHOW')
          frame.OnEvent(frame,'AUCTION_ITEM_LIST_UPDATE')
          for i=1,5 do
            local current=timers;timers={};for _,fn in ipairs(current)do fn()end
          end
          assert(ns.AuctionBridge.GetAuctionSupply(11).quantity==10)
          assert(#queue==before,'query unexpectedly recalculated a route')
          ns.ProfRouteAuto.Recalculate('alchemy',opts)
          local fresh=finish('alchemy',opts)
          assert(fresh.auctionSupplyUnknown==0 and fresh.mats[1].availableCount==10)
          assert(fresh.total==old.total and fresh.targetReached)
        ''')


if __name__ == '__main__':
    unittest.main()
