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
          assert(#offers==2 and offers[1].npcID==1,'a live record hid a collected supplier')
          remote.requirements={questID=123}
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

    def test_obsolete_observation_flags_cannot_replace_collected_prices(self):
        self.lua.execute(r'''
          local old=observed();save(old)
          local offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5'})
          assert(#offers==1 and offers[1].source=='supply-verified' and offers[1].price==20)
          assert(offers[1].unlimited and offers[1].quantity==5 and offers[1].npcID==1313)
          assert(ns.VendorPriceDB.GetPrice(3371,{reputationKey='72:5',requireObservedPrice=true})==4)
          assert(DungeonsForeverDB.profVendorOffers[3371][1]==old)
        ''')

    def test_unread_merchant_price_does_not_hide_a_regular_supplier(self):
        self.lua.execute(r'''
          local old=observed();old.price=nil;save(old)
          local offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:4'})
          assert(#offers==1 and offers[1].source=='supply-verified')
        ''')

    def test_live_quotes_and_rejections_never_override_the_catalogue(self):
        self.lua.execute(r'''
          save(observed())
          local offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:4'})
          assert(#offers==1 and offers[1].source=='supply-verified' and offers[1].price==20)
          for _,field in ipairs({'available','unlimited','purchasable','currencyID','hasExtendedCost'})do
            local old=observed()
            old[field]=(field=='currencyID' and 99) or (field=='hasExtendedCost' and true) or false
            save(old)
            offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5'})
            assert(#offers==1 and offers[1].price==20 and offers[1].source=='supply-verified')
          end
          local old=observed();old.requirements={questID=123};save(old)
          offers=ns.VendorPriceDB.GetOffers(3371,{reputationKey='72:5',quests={[123]=false}})
          assert(#offers==1 and offers[1].price==20)
        ''')

    def test_formula_prices_and_stock_policy_ignore_live_records(self):
        self.lua.execute(r'''
          local old=observed();old.formulaPrice=18;save(old)
          local offers=ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})
          assert(#offers==1 and offers[1].source=='supply-verified' and offers[1].price==200)
          assert(offers[1].stockStatus=='unlimited' and offers[1].unlimited)
          old.hasExtendedCost=true
          assert(ns.VendorPriceDB.GetFormulaOffers(3371)[1].price==200)
          old.hasExtendedCost=false;old.purchasable=false
          assert(ns.VendorPriceDB.GetFormulaOffers(3371)[1].price==200)
          old.purchasable=true;old.stock=0;old.unlimited=false
          assert(ns.VendorPriceDB.GetFormulaOffers(3371)[1].price==200)
          old.reputationKey='72:5';old.stock=0;old.unlimited=false
          offers=ns.VendorPriceDB.GetFormulaOffers(3371,{reputationKey='72:5'})
          assert(#offers==1 and offers[1].unlimited and offers[1].stockStatus=='unlimited')
          assert(offers[1].available and offers[1].priceUsable and offers[1].stock==nil)
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

    def test_static_access_requirements_still_apply_without_merchant_records(self):
        self.lua.execute(r'''
          local o=ns.ProfVendorOffers[3371][1]
          local ctx={level=60,quests={[123]=true},reputations={[72]=5},
            professions={alchemy=100},npcAccess={[1313]=true}}
          o.summoned=true;o.npcFactionID=72
          o.requirements={level=20,questID=123,reputationFactionID=72,minimumStanding=5,
            profession='alchemy',skill=75}
          assert(ns.VendorPriceDB.GetPrice(3371,ctx)==4)
          for key,value in pairs({level=19,quests={},reputations={[72]=4},
              professions={alchemy=74},npcAccess={},faction='H'})do
            local blocked={};for k,v in pairs(ctx)do blocked[k]=v end;blocked[key]=value
            assert(ns.VendorPriceDB.GetPrice(3371,blocked)==nil,key..' restriction was bypassed')
          end
        ''')

    def test_shipped_tools_prefer_cache_and_formulas_keep_collected_quotes(self):
        for path in ('Core/Data/Data_ProfMaterialSupply.lua', 'Core/Data/Data_ProfFormulaOffers.lua',
                     'Core/ProfSupply.lua'):
            self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                             (ROOT/path).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          local cached
          Auctionator={API={v1={GetVendorPriceByItemID=function()return cached end}}}
          DungeonsForeverDB.profVendorOffers={}
          for _,id in ipairs({2901,5956,6217,7005})do
            local first=assert(ns.VendorPriceDB.GetOffers(id)[1])
            local old=observed();old.npcID=first.npcID;old.price=1;old.quantity=100
            DungeonsForeverDB.profVendorOffers[id]={old}
            cached=1
            local tools=ns.VendorPriceDB.GetOffers(id)
            assert(tools[1].price==1 and tools[1].quantity==1)
            assert(tools[1].source=='auctionator-vendor' and not tools[1].npcID)
            cached=nil
            local fallback=ns.VendorPriceDB.GetOffers(id)
            assert(fallback[1].price==first.price and fallback[1].npcID==first.npcID)
            assert(fallback[1].source=='supply-verified')
          end
          -- Recipe 10311 has one Alliance NPC in the collected data, stock limit 1.
          local old=observed();old.npcID=4168;old.formulaPrice=1;old.stock=0;old.available=false
          DungeonsForeverDB.profVendorOffers[10311]={old}
          cached=1
          local offers=ns.VendorPriceDB.GetFormulaOffers(10311)
          assert(#offers==1 and offers[1].npcID==4168 and offers[1].price==3157)
          assert(offers[1].quantity==1 and offers[1].maxStock==1 and offers[1].limited)
          assert(offers[1].source=='formula-offers' and offers[1].priceUsable and offers[1].stock==nil)
        ''')

    def test_missing_material_facts_stay_unknown_without_a_valid_cache_quote(self):
        self.lua.execute(r'''
          Auctionator={API={v1={GetVendorPriceByItemID=function()error('live vendor cache used')end}}}
          ns.VendorPriceSeed={[3371]=1};DungeonsForeverDB.vendorPrices={[3371]={p=1,t=1000}}
          save(observed())
          for _,field in ipairs({'price','quantity','verifiedAt','priceVerified'})do
            local o=reference();o[field]=nil;ns.ProfVendorOffers[3371]={o}
            assert(ns.VendorPriceDB.GetPrice(3371,{allowVendorCache=true})==nil,field)
          end
          local o=reference();o.price=0/0;ns.ProfVendorOffers[3371]={o}
          assert(ns.VendorPriceDB.GetPrice(3371)==nil)
        ''')

    def test_auctionator_price_has_priority_over_collected_quotes(self):
        self.lua.execute(r'''
          local calls,cached=0,2
          Auctionator={API={v1={GetVendorPriceByItemID=function(caller,id)
            assert(caller=='DungeonsForever' and id==3371)
            calls=calls+1;return cached
          end}}}
          assert(ns.VendorPriceDB.GetPrice(3371)==2 and calls==1)
          cached=8
          assert(ns.VendorPriceDB.GetPrice(3371)==8,'cheaper collected price overrode cache priority')
          ns.ProfVendorOffers[3371]={reference(0)}
          assert(ns.VendorPriceDB.GetPrice(3371)==8,'collected zero price overrode cache priority')
          cached=2
          ns.ProfVendorOffers[3371]={}
          local before=calls
          local offers=ns.VendorPriceDB.GetOffers(3371)
          assert(calls==before+1 and #offers==1 and offers[1].unit==2 and offers[1].price==2)
          assert(offers[1].quantity==1 and offers[1].priceBasis=='cached-unit')
          assert(offers[1].source=='auctionator-vendor' and not offers[1].reference)
          assert(not offers[1].npcID and not offers[1].url and not offers[1].verifiedAt)
          assert(ns.VendorPriceDB.GetPrice(3371)==2 and #ns.VendorPriceDB.GetSuppliers(3371)==0)
          assert(DungeonsForeverDB.profVendorOffers==nil and DungeonsForeverDB.vendorPrices==nil)
          assert(ns.VendorPriceDB.GetFormulaOffers(3371)[1].price==200,'formula policy changed')
          local before=calls;ns.ProfSupply.FormulaList=function()return {}end
          assert(#ns.VendorPriceDB.GetFormulaOffers(3371)==0 and calls==before)
          assert(ns.ProfVendorOffers[3371][1]==nil,'cache quote was written into collected data')
        ''')

    def test_invalid_cache_falls_back_to_collected_quotes_or_stays_unknown(self):
        self.lua.execute(r'''
          local function checkFallback()
            ns.ProfVendorOffers[3371]={reference()}
            local offers=ns.VendorPriceDB.GetOffers(3371)
            assert(#offers==1 and offers[1].unit==4 and offers[1].quantity==5)
            assert(offers[1].source=='supply-verified' and offers[1].npcID==1313)
            ns.ProfVendorOffers[3371]={}
            assert(ns.VendorPriceDB.GetPrice(3371)==nil)
          end
          for _,value in ipairs({false,'2',-1,math.huge,-math.huge,0/0})do
            Auctionator={API={v1={GetVendorPriceByItemID=function()return value end}}}
            checkFallback()
          end
          Auctionator={API={v1={GetVendorPriceByItemID=function()return nil end}}}
          checkFallback()
          Auctionator.API.v1.GetVendorPriceByItemID=function()error('API unavailable')end
          checkFallback()
          Auctionator.API.v1.GetVendorPriceByItemID=nil
          checkFallback()
          Auctionator=nil
          checkFallback()
          Auctionator={API={v1={GetVendorPriceByItemID=function()return 0 end}}}
          ns.ProfVendorOffers[3371]={reference()}
          assert(ns.VendorPriceDB.GetPrice(3371)==0,'an explicit zero quote was discarded')
        ''')

    def test_formula_unknown_price_and_pack_are_not_invented(self):
        self.lua.execute(r'''
          ns.ProfSupply.FormulaList=function()return {}end
          local old=observed();old.formulaPrice=1;save(old)
          local source={vendors={
            {id=1313,name='Unpriced',quantity=1,unlimited=true},
            {id=1314,name='Unknown pack',price=10,priceVerified=true,verifiedAt=1,unlimited=true},
            {id=1315,name='Collected quote',price=12,quantity=3,priceVerified=true,verifiedAt=1,unlimited=true}}}
          local offers=ns.VendorPriceDB.GetFormulaOffers(3371,{},source)
          assert(#offers==3 and offers[1].npcID==1315 and offers[1].unit==4)
          for i=2,3 do
            assert(offers[i].price==nil and offers[i].unit==nil and not offers[i].priceUsable)
            assert(not offers[i].priceVerified)
          end
        ''')

    def test_collected_formula_adapter_preserves_unknowns_and_explicit_zero(self):
        self.lua.execute(r'''
          ns.EnsureProfFormulaOffers=function()return {
            [3371]={1313,false,-1,1,1519,1,0,0,
                    1314,10,-1,1,1519,0,0,0,
                    1315,0,-1,1,1519,1,0,0}}end
          ns.ProfFormulaOffersMeta={schemaVersion=1,source='collected-formula-fixture'}
        ''')
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT/'Core/ProfSupply.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          local offers=ns.VendorPriceDB.GetFormulaOffers(3371)
          assert(#offers==3 and offers[1].npcID==1315 and offers[1].price==0 and offers[1].priceUsable)
          assert(offers[2].npcID==1313 and offers[2].price==nil and not offers[2].priceUsable)
          assert(offers[3].npcID==1314 and offers[3].quantity==nil and not offers[3].priceUsable)
        ''')

    def test_fresh_install_never_records_merchants_or_registers_migration(self):
        self.lua.execute(r'''
          pending={};events={};timers=0;invalidations=0
          ns.Init=function(fn)pending[#pending+1]=fn end
          CreateFrame=function()return {
            RegisterEvent=function(_,event)events[event]=true end,
            SetScript=function(_,_,fn)onEvent=fn end}end
          C_Timer={After=function()timers=timers+1 end}
          GetMerchantNumItems=function()error('merchant scanning is retired')end
          ns.ProfRouteAuto={Invalidate=function()invalidations=invalidations+1 end}
          DungeonsForeverDB={prof={}}
        ''')
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT/'Core/VendorPriceDB.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          assert(#pending==0,'vendor pricing must not register a migration callback')
          assert(not events.MERCHANT_SHOW and not events.MERCHANT_UPDATE and timers==0)
          assert(ns.VendorPriceDB.GetPrice(3371)==4)
          assert(ns.VendorPriceDB.GetFormulaOffers(3371)[1].price==200)
          assert(DungeonsForeverDB.profVendorOffers==nil and DungeonsForeverDB.vendorPrices==nil)
          assert(events.UPDATE_FACTION);onEvent(nil,'UPDATE_FACTION')
          assert(invalidations==1 and ns.VendorPriceDB.revision==1)
          assert(DungeonsForeverDB.profVendorOffers==nil and DungeonsForeverDB.vendorPrices==nil)
        ''')


if __name__=='__main__':unittest.main()
