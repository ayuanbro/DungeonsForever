"""Supplier eligibility regressions compared with master, using actual Lua 5.1."""
import unittest
from test_prof_solver_fusion import ROOT, LuaRuntime


class VendorRegressionTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r'''
          ns={LoadForeverPages=true,L=setmetatable({},{__index=function(_,k)return k end})}
          DungeonsForeverDB={prof={}}
          ns.DB=function()return DungeonsForeverDB end
          UnitName=function()return 'Test'end;GetRealmName=function()return 'Realm'end
          UnitFactionGroup=function()return 'Alliance'end
          function time()return 1000 end
          function reference(price)
            return {npcID=1313,price=price or 20,quantity=5,unlimited=true,available=true,
              reference=true,priceVerified=true,source='supply-verified',verifiedAt='2026-10-21',faction='A'}
          end
          function observed()
            return {npcID=1313,price=18,quantity=5,unlimited=true,available=true,purchasable=true,
              source='merchant',verifiedAt=999,character='Test-Realm',faction='A',reputationKey='72:4'}
          end
          ns.ProfVendorOffers={[3371]={reference()}}
          ns.ProfSupply={Ensure=function()end,FormulaList=function()return {reference(200)}end}
          function save(offer)DungeonsForeverDB.profVendorOffers={[3371]={offer}}end
        ''')
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT/'Core/VendorPriceDB.lua').read_text(encoding='utf-8-sig'))

    def test_lower_remote_quote_is_retained_and_city_only_breaks_equal_price_ties(self):
        self.lua.execute(r'''
          local remote=reference(20);remote.npcID=1;remote.quantity=1;remote.areaID=440
          local city=reference(100);city.npcID=2;city.quantity=1;city.areaID=1519
          ns.ProfVendorOffers={[3371]={remote,city}}
          local offers=ns.VendorPriceDB.GetOffers(3371)
          assert(#offers==2 and offers[1].npcID==1 and offers[1].unit==20)
          assert(ns.VendorPriceDB.GetPrice(3371)==20)
          local preferred=ns.VendorPriceDB.PreferredOffers({remote,city})
          assert(#preferred==2 and preferred[1]==city and preferred[2]==remote)
          assert(ns.ProfVendorOffers[3371][1]==remote,'display sorting mutated source data')
          remote.price=100
          offers=ns.VendorPriceDB.GetOffers(3371)
          assert(#offers==2 and offers[1].npcID==2,'the final quote sort erased the equal-price city preference')
          remote.price=20
          local blocked=observed();blocked.npcID=1;blocked.available=false
          save(blocked)
          offers=ns.VendorPriceDB.GetOffers(3371)
          assert(#offers==1 and offers[1].npcID==2,'retaining remote offers revived sold-out stock')
          blocked.available=true;blocked.requirements={questID=123}
          offers=ns.VendorPriceDB.GetOffers(3371,{quests={[123]=false}})
          assert(#offers==1 and offers[1].npcID==2,'an inaccessible supplier was revived')
        ''')

    def test_shipped_remote_supplier_is_not_hidden_by_a_more_expensive_city(self):
        for path in ('Core/Data/Data_ProfVendors.lua','Core/Data/Data_ProfMaterialSupply.lua','Core/ProfSupply.lua'):
            self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                             (ROOT/path).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfSupply.Ensure()
          local best=math.huge
          for _,o in ipairs(ns.ProfVendorOffers[2324])do
            if o.faction~='H' then best=math.min(best,o.price/o.quantity)end
          end
          assert(best==23,'the native bleach quote changed; recheck the actual suppliers')
          assert(ns.VendorPriceDB.GetPrice(2324)==best)
          local offers=ns.VendorPriceDB.GetOffers(2324)
          assert(offers[1].unit==best and #offers>1)
        ''')

    def test_invalid_reputation_price_keeps_verified_vendor_in_default_route(self):
        self.lua.execute(r'''
          local old=observed();save(old)
          local offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5'})
          assert(#offers==1 and offers[1].source=='supply-verified' and offers[1].price==20)
          assert(offers[1].unlimited and offers[1].quantity==5 and offers[1].npcID==1313)
          assert(#ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5',requireObservedPrice=true})==0)
          assert(DungeonsForeverDB.profVendorOffers[3371][1]==old)
        ''')

    def test_unread_merchant_price_does_not_hide_a_regular_supplier(self):
        self.lua.execute(r'''
          local old=observed();old.price=nil;save(old)
          local offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:4'})
          assert(#offers==1 and offers[1].source=='supply-verified')
        ''')

    def test_current_quote_and_explicit_rejections_stay_authoritative(self):
        self.lua.execute(r'''
          save(observed())
          local offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:4'})
          assert(#offers==1 and offers[1].source=='merchant' and offers[1].price==18)
          for _,field in ipairs({'available','unlimited','purchasable','currencyID','hasExtendedCost'})do
            local old=observed()
            old[field]=(field=='currencyID' and 99) or (field=='hasExtendedCost' and true) or false
            save(old)
            offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5'})
            for _,o in ipairs(offers)do assert(o.npcID~=1313 or o.priceOnly)end
          end
          local old=observed();old.requirements={questID=123};save(old)
          offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5',quests={[123]=false}})
          assert(#offers==0)
        ''')

    def test_formula_supplier_falls_back_only_when_a_price_is_stale(self):
        self.lua.execute(r'''
          local old=observed();old.formulaPrice=18;save(old)
          local offers=ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})
          assert(#offers==1 and offers[1].source=='supply-verified' and offers[1].price==200)
          assert(offers[1].stockStatus=='unlimited' and offers[1].unlimited)
          old.hasExtendedCost=true
          assert(#ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})==0)
          old.hasExtendedCost=false;old.purchasable=false
          assert(#ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})==0)
          old.purchasable=true;old.stock=0;old.unlimited=false
          assert(#ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})==0,
            'stale price revived a known sold-out supplier')
          old.reputationKey='72:5';old.stock=0;old.unlimited=false
          offers=ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})
          assert(#offers==1 and offers[1].limited and offers[1].stockStatus=='limited')
          assert(not offers[1].available and not offers[1].priceUsable)
        ''')

    def test_first_supplier_lookup_loads_reference_data(self):
        self.lua.execute(r'''
          ns.ProfVendorOffers=nil;local calls=0
          ns.ProfSupply.Ensure=function()
            calls=calls+1;ns.ProfVendorOffers={[3371]={reference()}}
          end
          local suppliers=ns.VendorPriceDB.GetSuppliers(3371)
          assert(calls==1 and #suppliers==1 and suppliers[1].npcID==1313)
        ''')

    def test_limited_formula_reference_preserves_the_original_stock_limit(self):
        self.lua.execute(r'''
          ns.ProfSupply.FormulaList=function()
            local o=reference(200);o.quantity=1;o.unlimited=false;o.limited=2;o.maxStock=2
            o.source='formula-offers';return {o}
          end
          local offers=ns.VendorPriceDB.GetFormulaOffers(3371)
          assert(#offers==1 and offers[1].limited==true and not offers[1].unlimited)
          assert(offers[1].stockStatus=='limited' and offers[1].maxStock==2)
        ''')

    def test_shipped_vial_supplier_data_is_loaded_without_an_optimization_pass(self):
        for path in ('Core/Data/Data_ProfMaterialSupply.lua','Core/ProfSupply.lua'):
            self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                             (ROOT/path).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfVendorOffers=nil
          for _,id in ipairs({3371,3372,8925})do
            local offers=ns.VendorPriceDB.GetOffers(id)
            assert(#offers>0)
            for _,o in ipairs(offers)do
              assert(o.npcID and o.quantity==5 and o.unlimited and o.source=='supply-verified')
              assert(o.reference and o.priceVerified and o.price>0)
            end
          end
        ''')


if __name__=='__main__':unittest.main()
