"""Formula market availability and independent NPC/BOP procurement policies."""
import unittest

from test_prof_native_data import native_runtime


class FormulaChannelTests(unittest.TestCase):
    def setUp(self):
        self.lua=native_runtime()
        self.lua.execute('''
          -- Keep expiry cases deterministic in this isolated economy fixture.
          ns.ProfRouteAuto.MaxStaleSeconds=function()return 1800 end
          function formulaRecipe()
            return {key='alchemy:999001',profession='alchemy',spell=999001,formula=400,source={}}
          end
          function stock(q)
            return {quantity=q,observedAt=900,complete=true,ownerExcluded=true,source='client-auction-results'}
          end
          function input()
            return {stamp=1000,known={},prices={[400]=100},formulaOffers={},offers={},
              nonAuctionable={},auctionSupply={[400]=stock(2)},considerAuctionSupply=false}
          end
          function vendor(price,limited,id)
            return {npcID=id or 1,price=price,quantity=1,unlimited=not limited,
              limited=limited or nil,maxStock=limited and 1 or nil,available=true,priceUsable=true}
          end
        ''')

    def test_auction_needs_price_and_recent_stock_despite_retired_flags_and_material_setting(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input()
          s.noFormula=true;s.learnedOnly=true;s.allowUnknownLearning=false;s.skipUnpricedFormulas=true
          for _,materialLimit in ipairs({false,true})do
            s.considerAuctionSupply=materialLimit
            local q=E.FormulaFor(formulaRecipe(),s)
            assert(q.usable and q.source=='ah' and q.cost==100)
          end
          s.prices[400]=nil
          assert(not E.FormulaFor(formulaRecipe(),s).usable)
          s.prices[400]=0
          assert(not E.FormulaFor(formulaRecipe(),s).usable)
        ''')

    def test_zero_missing_stale_unverified_and_own_auction_counts_cannot_qualify(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input()
          s.auctionSupply[400]=stock(0)
          assert(E.FormulaFor(formulaRecipe(),s).reason=='formulaAuctionSupplyInsufficient')
          local bad={stock(20),stock(20),stock(20),stock(20),{quantity=20}}
          bad[1].observedAt=1;s.stamp=2000
          bad[2].complete=false;bad[3].ownerExcluded=false;bad[4].source='auctionator-history'
          for _,value in ipairs(bad)do
            s.auctionSupply[400]=value
            local q=E.FormulaFor(formulaRecipe(),s)
            assert(not q.usable and q.cost==nil and q.reason=='formulaAuctionSupplyUnknown')
          end
          s.auctionSupply={}
          assert(not E.FormulaFor(formulaRecipe(),s).usable)
        ''')

    def test_limited_toggle_only_adds_npc_competition_and_uses_cheapest_eligible_channel(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input();s.formulaOffers[400]={vendor(50,true)}
          s.allowLimitedFormulas=false
          local q=E.FormulaFor(formulaRecipe(),s)
          assert(q.source=='ah' and q.usable and q.cost==100 and q.vendorPrice==50)
          s.allowLimitedFormulas=true;q=E.FormulaFor(formulaRecipe(),s)
          assert(q.source=='vendor' and q.usable and q.cost==50 and q.availabilityUncertain)
          s.formulaOffers[400][1].price=200;q=E.FormulaFor(formulaRecipe(),s)
          assert(q.source=='ah' and q.cost==100)
          s.auctionSupply[400]=nil;q=E.FormulaFor(formulaRecipe(),s)
          assert(q.source=='vendor' and q.usable and q.cost==200)
          s.allowLimitedFormulas=false
          assert(not E.FormulaFor(formulaRecipe(),s).usable)
        ''')

    def test_unlimited_suppliers_compare_actual_prices_without_location_preference(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input()
          s.formulaOffers[400]={vendor(80,false,1),vendor(50,false,2)}
          E.PreferredVendorOffers=function()error('location preference must not hide cheaper quotes')end
          local q=E.FormulaFor(formulaRecipe(),s)
          assert(q.source=='vendor' and q.npcID==2 and q.cost==50)
          s.prices[400]=40
          q=E.FormulaFor(formulaRecipe(),s)
          assert(q.source=='ah' and q.cost==40)
        ''')

    def test_bound_pure_gold_recipe_without_auction_uses_only_npc_stock_policy(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input();s.nonAuctionable[400]=true;s.prices[400]=nil
          s.formulaOffers[400]={vendor(50,false)}
          local q=E.FormulaFor(formulaRecipe(),s)
          assert(q.usable and q.source=='vendor' and q.cost==50 and not q.ahPrice)
          s.formulaOffers[400]={vendor(50,true)}
          for _,bound in ipairs({false,true})do for _,currency in ipairs({false,true})do
            s.allowBindOnPickupFormulas=bound;s.allowCurrencyFormulas=currency
            q=E.FormulaFor(formulaRecipe(),s)
            assert(not q.usable and q.reason=='limitedFormulaDisabled' and not q.ahPrice,
              'non-gold permissions bypassed the limited NPC policy')
          end end
          s.allowBindOnPickupFormulas=false;s.allowCurrencyFormulas=false;s.allowLimitedFormulas=true
          q=E.FormulaFor(formulaRecipe(),s)
          assert(q.usable and q.source=='vendor' and q.cost==50 and not q.ahPrice)
          s.formulaOffers[400]={};q=E.FormulaFor(formulaRecipe(),s)
          assert(not q.usable and not q.ahPrice,'missing auction price became a purchase')
        ''')

    def test_effective_currency_permission_is_the_union_of_two_independent_saved_flags(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          for _,bound in ipairs({false,true})do for _,currency in ipairs({false,true})do
            local s=input();s.allowBindOnPickupFormulas=bound;s.allowCurrencyFormulas=currency
            assert(E.AllowBindOnPickupFormulas(s)==bound)
            assert(E.AllowCurrencyFormulas(s)==(bound or currency))
            local captured=E.Capture('alchemy',{snapshot=s})
            assert(captured.allowBindOnPickupFormulas==bound and captured.allowCurrencyFormulas==currency,
              'effective currency policy overwrote an independently saved switch')
          end end
        ''')

    def test_gold_plus_currency_or_items_is_not_a_pure_gold_purchase(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input();s.nonAuctionable[400]=true;s.prices[400]=nil
          for _,kind in ipairs({'currencyID','hasExtendedCost','currencies','costItems'})do
            local o=vendor(50,false)
            if kind=='currencyID' then o[kind]=123
            elseif kind=='hasExtendedCost' then o[kind]=true
            else o[kind]={{id=123,count=2}} end
            s.formulaOffers[400]={o}
            local q=E.FormulaFor(formulaRecipe(),s)
            assert(not q.usable and q.source~='vendor' and not q.ahPrice,
              'exchange component was lost from '..kind)
          end
        ''')

    def test_remaining_budget_cannot_replace_observed_positive_stock_threshold(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input()
          assert(E.FormulaFor(formulaRecipe(),s,1).usable)
          assert(not E.FormulaFor(formulaRecipe(),s,0).usable)
          s.auctionSupply[400]=stock(1)
          assert(E.FormulaFor(formulaRecipe(),s,1).usable)
          s.auctionSupply[400]=stock(0)
          assert(not E.FormulaFor(formulaRecipe(),s,99).usable)
          s.auctionSupply={}
          assert(not E.FormulaFor(formulaRecipe(),s,99).usable)
        ''')

    def test_formula_quantity_evidence_remains_visible_with_material_check_disabled(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input()
          local q=E.FormulaFor(formulaRecipe(),s)
          local result={formulas={q},mats={{id=400,count=1,source='ah'}}}
          E.SummarizeAuctionSupply(result,s)
          assert(result.considerAuctionSupply==false and result.mats[1].considerAuctionSupply==false)
          assert(q.considerAuctionSupply and q.supplyObserved and q.availableCount==2)
          assert(q.supplyRequired==2 and q.supplyObservedAt==900 and not q.supplyLimited)
          assert(result.formulaAuctionSupplyInputs[400].quantity==2)
        ''')

    def test_frozen_inputs_never_read_live_market_or_binding(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          ns.AuctionBridge={GetAuctionSupply=function()error('live supply read')end}
          ns.ProfRouteAuto.AHPriceOf=function()error('live price read')end
          E.NonAuctionableItem=function()error('live binding read')end
          local s=input();s.auctionSupply={}
          assert(not E.FormulaFor(formulaRecipe(),s).usable)
        ''')

    def test_formula_availability_invalidates_plans_even_with_material_stock_off(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input();s.recipes={formulaRecipe()}
          local result={considerAuctionSupply=false,formulas={},mats={}}
          E.SummarizeAuctionSupply(result,s)
          local current=stock(2)
          ns.AuctionBridge={GetAuctionSupply=function(id)assert(id==400);return current end}
          assert(not E.AuctionSupplyChanged(result))
          current=stock(1);assert(E.AuctionSupplyChanged(result))
          current=nil;assert(E.AuctionSupplyChanged(result))
        ''')

    def test_index_marks_all_teaching_items_and_binding_without_live_reads(self):
        self.lua.execute('''
          local E=ns.ProfEconomy;local s=input();local r=formulaRecipe()
          r.learn=1;r.grey=50;r.mats={};r.learningInfo={routes={{kind='item',teachingItemID=401,
            acquisition={nonAuctionable=true}}}}
          s.recipes={r};s=E.Index(s)
          assert(s.formulaItems[400] and s.formulaItems[401] and s.nonAuctionable[401])
        ''')

    def test_missing_snapshot_permissions_default_off_instead_of_reading_live_settings(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          ns.ProfModule.SettingRaw=function()error('snapshot read live permission')end
          local s=input()
          assert(not E.AllowLimitedFormulas(s))
          assert(not E.AllowBindOnPickupFormulas(s) and not E.AllowCurrencyFormulas(s))
          s.allowBindOnPickupFormulas=true;s.allowCurrencyFormulas=true;s.allowLimitedFormulas=true
          assert(E.AllowLimitedFormulas(s) and E.AllowBindOnPickupFormulas(s) and E.AllowCurrencyFormulas(s))
        ''')


if __name__=='__main__':unittest.main()
