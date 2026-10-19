"""Formula acquisition is a one-time route cost, separate from reagents."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT
from test_prof_vendor import runtime as vendor_runtime


class FormulaEconomyTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load=self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ('ProfEconomy.lua','ProfRouteSolver.lua','ProfRouteAuto.lua'):
            self.load(str(ROOT/'Core'/name))
        self.lua.execute(r'''
          function book(spell,item,material,formula,learn,grey)
            return {profession='alchemy',spell=spell,item=item,count=1,
              learn=learn or 1,yellow=grey or 10,green=grey or 10,grey=grey or 10,
              mats={{material,1}},formula=formula,cooldown=false,catalogue=true}
          end
          function sample(recipes,prices,known)
            return {recipes=recipes,prices=prices,known=known or {},
              professions={alchemy={cur=1,max=300}}}
          end
          function solve(s,target)
            local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=target or 5})
            assert(not j.error,tostring(j.error));return r
          end
          function checkTotals(r)
            assert(r.total==r.matTotal+r.formulasTotal)
            assert(r.total==r.ahTotal+r.vendorTotal)
            local sum=0;for _,st in ipairs(r.steps)do sum=sum+st.cost end
            assert(sum==r.total,'step cost sum '..sum..' total '..r.total)
            for _,m in ipairs(r.mats)do assert(m.id~=99,'formula became a reagent')end
          end
          function legacyFixture(quest)
            ns.ProfRecipes={alchemy={rows={
              {101,20,1,'','','',1,20,30,40,false,{{11,1}},{99},quest and {quests={{id=1}}} or {}},
              {102,21,1,'','','',1,20,30,40,false,{{12,1}},nil,{}}}}}
            ns.EnsureProfRecipes=function()return ns.ProfRecipes end
            Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)
              if id==99 and quest then return nil end
              return ({[11]=2,[12]=20,[99]=5})[id]
            end}}}
          end
        ''')

    def test_formula_can_make_a_cheaper_material_recipe_more_expensive(self):
        self.lua.execute('''
          local r=solve(sample({book(101,20,11,99),book(102,21,12)},
            {[11]=1,[12]=3,[99]=100}))
          assert(r.feasible and r.targetReached and r.total==12 and #r.formulas==0)
          assert(#r.steps==1 and r.steps[1][3]==102);checkTotals(r)
        ''')

    def test_formula_is_paid_once_and_can_amortize_over_many_crafts(self):
        self.lua.execute('''
          local r=solve(sample({book(101,20,11,99),book(102,21,12)},
            {[11]=1,[12]=4,[99]=6}))
          assert(r.feasible and r.total==10 and r.matTotal==4 and r.formulasTotal==6)
          assert(#r.formulas==1 and r.formulas[1].source=='ah')
          local n=0;for _,a in ipairs(r.actions)do if a.type=='formula'then n=n+1 end end
          assert(n==1 and r.inventory[99]==nil);checkTotals(r)
        ''')

    def test_shared_formula_for_two_recipes_is_only_purchased_once(self):
        self.lua.execute('''
          local r=solve(sample({book(101,20,11,99,1,2),book(102,21,12,99,2,3)},
            {[11]=2,[12]=2,[99]=9}),3)
          assert(r.targetReached and r.total==13 and #r.formulas==1)
          assert(#r.formulas[1].recipes==2);checkTotals(r)
        ''')

    def test_known_recipe_never_buys_its_formula(self):
        self.lua.execute('''
          local r=solve(sample({book(101,20,11,99)},{[11]=2,[99]=100},
            {['alchemy:101']=true}))
          assert(r.total==8 and r.formulasTotal==0 and #r.formulas==0);checkTotals(r)
        ''')

    def test_material_producer_formula_changes_make_or_buy_choice(self):
        self.lua.execute('''
          local maker=book(100,10,11,99,1,1)
          local r=solve(sample({maker,book(101,20,10)}, {[10]=10,[11]=2,[99]=100}))
          assert(r.targetReached and r.total==40 and #r.formulas==0)
          for _,a in ipairs(r.actions)do assert(a.spell~=100)end
          checkTotals(r)
        ''')

    def test_quest_formula_without_auction_quote_is_rejected_with_alternative(self):
        self.lua.execute('''
          local a=book(101,20,11,99);a.source={quests={{id=1}}}
          local r=solve(sample({a,book(102,21,12)},{[11]=1,[12]=3}))
          assert(r.targetReached and r.total==12 and r.steps[1][3]==102)
          local blocked=solve(sample({a},{[11]=1}))
          assert(not blocked.feasible and #blocked.steps==0)
          local found=false;for _,d in ipairs(blocked.diagnostics)do
            if d.code=='formulaUnavailable'then found=true end end
          assert(found)
        ''')

    def test_quest_formula_auction_quote_or_existing_knowledge_is_valid(self):
        self.lua.execute('''
          local a=book(101,20,11,99);a.source={questOnly=true}
          local r=solve(sample({a},{[11]=1,[99]=5}))
          assert(r.targetReached and r.total==9 and r.formulas[1].questOnly)
          r=solve(sample({a},{[11]=1},{['alchemy:101']=true}))
          assert(r.targetReached and r.total==4 and #r.formulas==0)
        ''')

    def test_quest_material_producer_cannot_bypass_formula_requirement(self):
        self.lua.execute('''
          local a=book(100,10,11,99,1,1);a.source={quests={{id=1}}}
          local r=solve(sample({a,book(101,20,10)},{[11]=1}))
          assert(not r.feasible and #r.steps==0)
        ''')

    def test_unknown_ordinary_formula_is_not_free_and_trainer_needs_no_item(self):
        self.lua.execute('''
          local a=book(101,20,11,99)
          assert(not solve(sample({a},{[11]=1})).feasible)
          a.learnSource='trainer'
          local r=solve(sample({a},{[11]=1}))
          assert(r.targetReached and r.total==4 and #r.formulas==0)
        ''')

    def test_both_prices_are_retained_and_vendor_price_is_compared(self):
        self.lua.execute('''
          local s=sample({book(101,20,11,99)},{[11]=2,[99]=30})
          s.formulaOffers={[99]={{price=7,quantity=1,npcID=7,unlimited=true}}}
          local r=solve(s)
          assert(r.total==15 and r.matTotal==8 and r.formulasTotal==7)
          assert(r.vendorTotal==7 and r.ahTotal==8 and r.formulaVendorTotal==7)
          assert(r.formulas[1].ahPrice==30 and r.formulas[1].vendorPrice==7)
          assert(r.formulas[1].unlimited and r.formulas[1].source=='vendor');checkTotals(r)
        ''')

    def test_limited_vendor_reference_is_not_guaranteed_stock(self):
        self.lua.execute('''
          local s=sample({book(101,20,11,99)},{[11]=2})
          s.formulaOffers={[99]={{price=7,quantity=1,npcID=7,unlimited=false,limited=true,maxStock=1}}}
          local r=solve(s)
          assert(r.targetReached and r.total==15 and not r.completeCost and not r.optimal)
          assert(r.formulas[1].limited and r.formulas[1].availabilityUncertain)
        ''')

    def test_sold_out_vendor_quote_remains_visible_but_auction_is_chosen(self):
        self.lua.execute('''
          local s=sample({book(101,20,11,99)},{[11]=2,[99]=20})
          s.formulaOffers={[99]={{price=7,quantity=1,npcID=7,limited=true,stock=0,available=false}}}
          local r=solve(s);local f=r.formulas[1]
          assert(r.total==28 and f.source=='ah' and f.vendorPrice==7 and f.ahPrice==20)
        ''')

    def test_formula_vendor_bundle_is_compared_as_whole_purchase(self):
        self.lua.execute('''
          local s=sample({book(101,20,11,99)},{[11]=2,[99]=9})
          s.formulaOffers={[99]={{price=12,quantity=3,npcID=7,unlimited=true}}}
          local r=solve(s)
          assert(r.total==17 and r.formulas[1].vendorPrice==4 and r.formulas[1].source=='ah')
          s.prices[99]=20;r=solve(s)
          assert(r.total==20 and r.formulas[1].count==3 and r.formulas[1].need==1)
        ''')

    def test_reference_quest_metadata_is_used_without_inferring_empty_sources(self):
        self.load(str(ROOT/'Core/Data/Data_ProfFormulaSources.lua'))
        self.lua.execute('''
          local s=ns.ProfEconomy.Index(sample({book(4508,20,11,4597)},{[11]=2}))
          local f=ns.ProfEconomy.FormulaFor(s.recipes[1],s)
          assert(f.questOnly and not f.usable and f.sources.quests[1].id==429)
          local unknown=book(101,21,11,99)
          assert(not ns.ProfEconomy.FormulaFor(unknown,s).questOnly,'empty source invented a quest')
        ''')

    def test_legacy_cost_mode_considers_formula_before_choosing_recipe(self):
        self.lua.execute('''
          legacyFixture(false)
          Auctionator.API.v1.GetAuctionPriceByItemID=function(_,id)
            return ({[11]=1,[12]=3,[99]=100})[id]
          end
          local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=3,scheme='matcost'})
          assert(r and #r.steps==1 and r.steps[1][3]==102 and r.total==6)
        ''')

    def test_fixed_and_all_legacy_modes_include_formula_once(self):
        self.lua.execute('''
          legacyFixture(false)
          local ra=ns.ProfRouteAuto
          local r=ra.SummarizeSteps({{1,2,101,1},{2,3,101,1}},'alchemy')
          assert(r.total==9 and r.matTotal==4 and r.formulasTotal==5 and #r.formulas==1)
          assert(r.ahTotal+r.vendorTotal==r.total)
          assert(r.steps[1].cost+r.steps[2].cost==r.total)
          for _,mode in ipairs({'matcost','crafts','optim'})do
            r=ra.Compute('alchemy',{start=1,target=3,scheme=mode})
            assert(r and #r.formulas==1 and r.formulasTotal==5 and r.total==r.matTotal+5,mode)
          end
        ''')

    def test_legacy_modes_reject_quest_only_unpriced_recipe(self):
        self.lua.execute('''
          legacyFixture(true)
          for _,mode in ipairs({'matcost','crafts','optim'})do
            local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=3,scheme=mode})
            assert(r and #r.steps>0)
            for _,st in ipairs(r.steps)do assert(st[3]~=101,mode)end
          end
          local ref=ns.ProfRouteAuto.SummarizeSteps({{1,3,101,2}},'alchemy')
          assert(#ref.formulas==1 and ref.formulas[1].blocked and not ref.completeCost)
        ''')

    def test_formula_cache_migrates_once(self):
        self.lua.execute('''
          captures=0;ns.ProfEconomy.Capture=function()
            captures=captures+1;return ns.ProfEconomy.Index(fixture())end
          local r=finish('alchemy',{start=1,target=2})
          local c=DungeonsForeverDB.prof.routeCache['Test-Realm']
          c.routes[c.active.alchemy].result.formulaRevision=nil
        ''')
        self.load(str(ROOT/'Core/ProfRouteAuto.lua'))
        self.lua.execute('''
          assert(ns.ProfRouteAuto.Get('alchemy',{start=1,target=2}).status=='searching')
          local r=finish('alchemy',{start=1,target=2})
          assert(captures==2 and r.formulaRevision==1)
        ''')
        self.load(str(ROOT/'Core/ProfRouteAuto.lua'))
        self.lua.execute("assert(ns.ProfRouteAuto.Get('alchemy',{start=1,target=2}).cached and captures==2)")


class FormulaVendorTests(unittest.TestCase):
    def test_limited_price_is_retained_without_entering_material_quotes(self):
        lua=vendor_runtime()
        lua.execute('''
          test.entries={{id=99,price=42,quantity=1,stock=2,purchasable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          local f=ns.VendorPriceDB.GetFormulaOffers(99)
          assert(#f==1 and f[1].price==42 and f[1].limited and f[1].stock==2 and f[1].priceUsable)
          assert(#ns.VendorPriceDB.GetOffers(99)==0 and #ns.VendorPriceDB.GetSuppliers(99)==0)
          test.entries[1].stock=0;ns.VendorPriceDB.Scan()
          f=ns.VendorPriceDB.GetFormulaOffers(99)
          assert(f[1].price==42 and not f[1].priceUsable and f[1].stock==0)
        ''')

    def test_unknown_catalogue_stock_stays_unknown_without_price(self):
        lua=vendor_runtime()
        lua.execute('''
          local f=ns.VendorPriceDB.GetFormulaOffers(99,nil,{vendors={{id=7,name='Seller'}}})
          assert(#f==1 and f[1].stockUnknown and not f[1].price and not f[1].priceUsable)
        ''')

    def test_old_quote_without_purchase_pack_cannot_price_a_formula(self):
        lua=vendor_runtime()
        lua.execute('''
          db.profVendorOffers={[99]={old={itemID=99,npcID=7,character='Alice-Realm',
            source='merchant',verifiedAt=1,price=50,unlimited=true,available=true,
            reputationKey='72:4'}}}
          local f=ns.VendorPriceDB.GetFormulaOffers(99)
          assert(#f==1 and not f[1].price and not f[1].priceUsable)
        ''')

    def test_extended_currency_cannot_become_gold_formula_purchase(self):
        lua=vendor_runtime()
        lua.execute('''
          test.entries={{id=99,price=42,quantity=1,stock=2,purchasable=true,extended=true}}
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetFormulaOffers(99)==0)
        ''')

    def test_currency_rejection_also_blocks_same_npc_reference_fallback(self):
        lua=vendor_runtime()
        lua.execute('''
          ns.ProfFormulaOffers={[99]={{npcID=12345,price=5,quantity=1,unlimited=true,
            reference=true,priceVerified=true,verifiedAt='2026-10-18',source='wowhead-forever'}}}
          test.entries={{id=99,price=42,quantity=1,stock=2,purchasable=true,extended=true}}
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetFormulaOffers(99)==0)
        ''')


if __name__=='__main__':
    unittest.main()
