"""Supplier metadata and synthetic quotation regressions (Lua 5.1)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path.home() / "AppData/Local/Temp/df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

MOCKS = r'''
test = { name="Alice", realm="Realm", faction="Alliance", standing=4,
    merchantReads=0, dbReads=0, entries={} }
db = { vendorPrices = { [999900] = { p=1, t=99 } } }
ns = { VendorPriceSeed = { [999901]=1 }, ProfVendors = {}, invalidations=0 }
ns.DB = function()
    test.dbReads=test.dbReads+1
    if test.denyDB then error('NPC quotations accessed player SavedVariables') end
    return db
end
ns.ProfRouteAuto = { Invalidate=function() ns.invalidations=ns.invalidations+1 end }
function UnitFactionGroup() return test.faction end
function UnitLevel() return test.level or 30 end
function GetMerchantNumItems() test.merchantReads=test.merchantReads+1;error('merchant API called') end
function GetMerchantItemInfo() test.merchantReads=test.merchantReads+1;error('merchant API called') end
C_MerchantFrame={GetItemInfo=GetMerchantItemInfo}
C_Reputation = { GetFactionDataByID=function(id)
    if id==72 then return {reaction=test.standing,atWarWith=test.atWar} end
end }
function CreateFrame()
    vendorFrame={events={}}
    function vendorFrame:RegisterEvent(event) self.events[event]=true end
    function vendorFrame:SetScript(_, fn) self.handler=fn end
    return vendorFrame
end
function put(item,values)
    local offer={itemID=item,npcID=7,price=21,quantity=5,unlimited=true,
        available=true,reference=true,priceVerified=true,source='wowhead-forever',
        verifiedAt='2026-10-18',priceBasis='npc-shelf'}
    for key,value in pairs(values or {}) do offer[key]=value end
    ns.ProfVendorOffers[item]={offer}
    return offer
end
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCKS)
    ns = lua.globals().ns
    for name in ("Core/Data/Data_ProfVendorOffers.lua", "Core/Data/Data_ProfFormulaSources.lua", "Core/VendorPriceDB.lua"):
        lua.execute((ROOT / name).read_text(encoding="utf-8-sig"), "Test", ns)
    return lua


class VendorOffers(unittest.TestCase):
    def test_merchant_open_never_records_or_changes_quotes(self):
        lua = runtime()
        lua.execute('''
          test.denyDB=true
          local price=ns.VendorPriceDB.GetPrice(3371)
          assert(not vendorFrame.events.MERCHANT_SHOW and not vendorFrame.events.MERCHANT_UPDATE)
          vendorFrame.handler(vendorFrame,'MERCHANT_SHOW')
          vendorFrame.handler(vendorFrame,'MERCHANT_UPDATE')
          assert(ns.VendorPriceDB.GetPrice(3371)==price)
          assert(test.merchantReads==0 and test.dbReads==0 and ns.invalidations==0)
          assert(db.profVendorOffers==nil and db.vendorPrices[3371]==nil)
          assert(ns.VendorPriceDB.Scan==nil and ns.VendorPriceDB.Count==nil)
          assert(ns.VendorPriceDB.GetBasePurchasePrice==nil and ns.VendorPriceDB.OnChanged==nil)
        ''')

    def test_legacy_persisted_records_neither_add_quotes_nor_block_shelves(self):
        lua = runtime()
        lua.execute('''
          local expected=ns.VendorPriceDB.GetPrice(3371)
          db.profVendorOffers={
            [3371]={old={npcID=1313,source='merchant',character='Alice-Realm',price=1,
              quantity=5,unlimited=false,available=false,hasExtendedCost=true}},
            [999900]={old={npcID=7,source='merchant',character='Alice-Realm',price=1,
              quantity=1,unlimited=true,available=true,verifiedAt=1}},
          }
          db.formulaPrices={[999900]=1}
          test.denyDB=true
          assert(ns.VendorPriceDB.GetPrice(3371)==expected)
          assert(ns.VendorPriceDB.GetPrice(999900)==nil)
          assert(#ns.VendorPriceDB.GetSuppliers(999900)==0)
          assert(#ns.VendorPriceDB.GetFormulaOffers(999900)==0)
          assert(test.dbReads==0 and db.profVendorOffers[3371].old.price==1)
        ''')

    def test_auctionator_vendor_cache_is_never_consulted(self):
        lua = runtime()
        lua.execute('''
          Auctionator={API={v1={
            GetVendorPriceByItemID=function() error('Auctionator vendor cache read') end,
            GetVendorPrice=function() error('Auctionator vendor cache read') end}}}
          local expected=ns.VendorPriceDB.GetPrice(3371)
          assert(expected==nil)
          assert(ns.VendorPriceDB.GetPrice(3371,{allowVendorCache=true})==expected)
          assert(ns.VendorPriceDB.GetPrice(999900,{allowVendorCache=true})==nil)
          assert(#ns.VendorPriceDB.GetFormulaOffers(999900)==0)
        ''')

    def test_unqualified_seed_and_base_prices_do_not_imply_sold_items(self):
        lua = runtime()
        lua.execute('''
          ns.ItemPurchasePrices={[999901]={10,5},[765]={5,1}}
          assert(ns.VendorPriceDB.GetPrice(999901)==nil)
          assert(ns.VendorPriceDB.GetPrice(765)==nil)
          assert(#ns.VendorPriceDB.GetSuppliers(999901)==0)
          assert(#ns.VendorPriceDB.GetOffers(765)==0)
          assert(db.vendorPrices[999900].t==99)
        ''')

    def test_bundled_suppliers_preserve_bundles_without_prices(self):
        lua = runtime()
        lua.execute('''
          local suppliers=ns.VendorPriceDB.GetSuppliers(3371)
          assert(#suppliers>0 and suppliers[1].quantity==5)
          assert(suppliers[1].bundleSize==5 and suppliers[1].source=='wowhead-forever')
          for _,supplier in ipairs(suppliers) do
            assert(supplier.price==nil and supplier.unit==nil and supplier.priceVerified==nil)
          end
          assert(#ns.VendorPriceDB.GetOffers(3371)==0 and ns.VendorPriceDB.GetPrice(3371)==nil)
        ''')

    def test_synthetic_integer_bundle_cost_without_auctionator_or_merchant_visit(self):
        lua = runtime()
        ns = lua.globals().ns
        ns.LoadForeverPages = True
        for filename in ("ProfEconomy.lua", "ProfRouteSolver.lua"):
            lua.execute((ROOT / "Core" / filename).read_text(encoding="utf-8-sig"), "Test", ns)
        lua.execute('''
          put(999777,{price=37,quantity=4})
          local snapshot={recipes={},professions={},known={},prices={[999777]=999},
            vendorItems={[999777]=true},offers={[999777]=ns.VendorPriceDB.GetOffers(999777)}}
          local r=ns.ProfRouteSolver.Procure(snapshot,999777,6)
          assert(r.feasible and r.costComplete and r.total==74 and r.vendorTotal==74 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].count==8 and r.mats[1].bundleSize==4)
          assert(r.mats[1].npcID==7 and r.mats[1].reference)
          assert(Auctionator==nil and test.merchantReads==0)
        ''')

    def test_catalogue_only_supplier_stays_unpriced(self):
        lua = runtime()
        lua.execute('''
          local offer=put(999010)
          offer.price=nil;offer.reference=nil;offer.priceVerified=nil
          assert(#ns.VendorPriceDB.GetSuppliers(999010)==1)
          assert(#ns.VendorPriceDB.GetOffers(999010)==0)
          assert(ns.VendorPriceDB.GetPrice(999010)==nil)
        ''')

    def test_unverified_reference_fields_are_not_free_prices(self):
        lua = runtime()
        lua.execute('''
          local offer=put(999011)
          for _,field in ipairs({'reference','priceVerified','verifiedAt','source'}) do
            local value=offer[field];offer[field]=nil
            assert(#ns.VendorPriceDB.GetOffers(999011)==0,field)
            offer[field]=value
          end
          assert(#ns.VendorPriceDB.GetOffers(999011)==1)
        ''')

    def test_invalid_prices_and_noninteger_bundles_are_rejected(self):
        lua = runtime()
        lua.execute('''
          local offer=put(999012)
          for _,value in ipairs({-1,'21',math.huge,0/0}) do
            offer.price=value;assert(#ns.VendorPriceDB.GetOffers(999012)==0)
          end
          offer.price=21
          for _,value in ipairs({0,-1,1.5,math.huge,0/0}) do
            offer.quantity=value;assert(#ns.VendorPriceDB.GetOffers(999012)==0)
          end
          offer.quantity=5;offer.price=0
          assert(ns.VendorPriceDB.GetPrice(999012)==0)
        ''')

    def test_limited_currency_unavailable_shelves_never_price_reagents(self):
        lua = runtime()
        lua.execute('''
          for _,values in ipairs({{unlimited=false},{available=false},{purchasable=false},
            {currencyID=7},{hasExtendedCost=true}}) do
            put(999013,values)
            assert(#ns.VendorPriceDB.GetOffers(999013)==0)
            assert(#ns.VendorPriceDB.GetSuppliers(999013)==0)
          end
        ''')

    def test_faction_and_explicit_npc_access_are_respected(self):
        lua = runtime()
        lua.execute('''
          put(999014,{faction='A'})
          assert(#ns.VendorPriceDB.GetOffers(999014,{faction='H'})==0)
          assert(#ns.VendorPriceDB.GetSuppliers(999014,{faction='H'})==0)
          assert(#ns.VendorPriceDB.GetOffers(999014,{faction='Alliance'})==1)
          assert(#ns.VendorPriceDB.GetOffers(999014,{npcAccess={[7]=false}})==0)
          assert(#ns.VendorPriceDB.GetSuppliers(999014,{npcAccess={[7]=false}})==0)
        ''')

    def test_summoned_vendor_needs_explicit_access(self):
        lua = runtime()
        lua.execute('''
          assert(#ns.VendorPriceDB.GetSuppliers(10284)==0)
          assert(#ns.VendorPriceDB.GetOffers(10284)==0)
          assert(#ns.VendorPriceDB.GetSuppliers(10284,{npcAccess={[242498]=true}})==1)
          assert(#ns.VendorPriceDB.GetOffers(10284,{npcAccess={[242498]=true}})==0)
          assert(#ns.VendorPriceDB.GetOffers(10284,{npcAccess={[242498]=false}})==0)
        ''')

    def test_level_quest_reputation_and_profession_requirements(self):
        lua = runtime()
        lua.execute('''
          local offer=put(999015,{requirements={level=30,questID=12,
            reputationFactionID=72,minimumStanding=5,profession='alchemy',skill=150}})
          local context={level=30,quests={[12]=true},reputations={[72]=5},professions={alchemy={cur=150}}}
          assert(#ns.VendorPriceDB.GetOffers(999015,context)==1)
          for field,missing in pairs({level=29,quests={[12]=false},reputations={[72]=4},professions={alchemy=149}}) do
            local value=context[field];context[field]=missing
            assert(#ns.VendorPriceDB.GetOffers(999015,context)==0,field)
            context[field]=value
          end
          context.requirementsMet=function()return true end
          assert(#ns.VendorPriceDB.GetOffers(999015,context)==1)
          context.requirementsMet=function()error('unknown condition')end
          assert(#ns.VendorPriceDB.GetOffers(999015,context)==0)
        ''')

    def test_unknown_or_hostile_requirements_are_filtered(self):
        lua = runtime()
        lua.execute('''
          local offer=put(999016)
          for _,field in ipairs({'unknown','event','currency','condition'}) do
            offer.requirements={[field]=true}
            assert(#ns.VendorPriceDB.GetOffers(999016)==0)
          end
          offer.requirements=nil;offer.npcFactionID=72;test.standing=2
          assert(#ns.VendorPriceDB.GetOffers(999016)==0)
          test.standing=5;test.atWar=true
          assert(#ns.VendorPriceDB.GetSuppliers(999016)==0)
        ''')

    def test_reputation_events_invalidate_access_without_reading_merchants(self):
        lua = runtime()
        lua.execute('''
          assert(vendorFrame.events.UPDATE_FACTION)
          local price=ns.VendorPriceDB.GetPrice(3371)
          vendorFrame.handler(vendorFrame,'UPDATE_FACTION')
          assert(ns.invalidations==1 and test.merchantReads==0 and test.dbReads==0)
          assert(ns.VendorPriceDB.GetPrice(3371)==price)
          put(999017,{npcFactionID=72})
          assert(#ns.VendorPriceDB.GetOffers(999017)==1)
          test.standing=2;vendorFrame.handler(vendorFrame,'UPDATE_FACTION')
          assert(#ns.VendorPriceDB.GetOffers(999017)==0 and ns.invalidations==2)
        ''')

    def test_returned_quote_and_supplier_tables_do_not_mutate_catalogue(self):
        lua = runtime()
        lua.execute('''
          local offer=put(999018)
          ns.VendorPriceDB.GetOffers(999018)[1].price=1000
          ns.VendorPriceDB.GetSuppliers(999018)[1].npcID=9
          assert(offer.price==21 and offer.npcID==7 and ns.VendorPriceDB.GetPrice(999018)==21/5)
        ''')

    def test_bundled_limited_formulas_keep_stock_metadata_without_prices(self):
        lua = runtime()
        lua.execute('''
          local offers=ns.VendorPriceDB.GetFormulaOffers(5640)
          assert(#offers==1 and offers[1].price==nil and offers[1].limited)
          assert(offers[1].maxStock==2 and offers[1].stock==nil and not offers[1].priceUsable)
          assert(offers[1].stockStatus=='limited' and not offers[1].stockUnknown)
          assert(#ns.VendorPriceDB.GetOffers(5640)==0 and #ns.VendorPriceDB.GetSuppliers(5640)==0)
          assert(#ns.VendorPriceDB.GetFormulaOffers(5640,{faction='H'})==0)
        ''')

    def test_formula_catalogue_keeps_unknown_stock_and_access_restrictions(self):
        lua = runtime()
        lua.execute('''
          local source={vendors={{id=7,name='Seller',price=1,faction='A',requirements={questID=12}}}}
          assert(#ns.VendorPriceDB.GetFormulaOffers(99,{quests={[12]=false}},source)==0)
          assert(#ns.VendorPriceDB.GetFormulaOffers(99,{faction='H',quests={[12]=true}},source)==0)
          local offers=ns.VendorPriceDB.GetFormulaOffers(99,{quests={[12]=true}},source)
          assert(#offers==1 and offers[1].npcID==7 and offers[1].npcName=='Seller')
          assert(offers[1].stockUnknown and offers[1].price==nil and not offers[1].priceUsable)
        ''')

    def test_audited_formula_source_prices_are_usable_with_bundle_and_conditions(self):
        lua = runtime()
        lua.execute('''
          local source={vendors={{id=7,name='Seller',price=42,quantity=3,unlimited=true,
            priceVerified=true,verifiedAt='2026-10-18',requirements={level=30}}}}
          local offers=ns.VendorPriceDB.GetFormulaOffers(99,{level=30},source)
          assert(#offers==1 and offers[1].priceUsable and offers[1].price==42 and offers[1].unit==14)
          assert(#ns.VendorPriceDB.GetFormulaOffers(99,{level=29},source)==0)
          source.vendors[1].currencyID=7
          assert(#ns.VendorPriceDB.GetFormulaOffers(99,{level=30},source)==0)
        ''')

    def test_formula_offers_are_sorted_and_audited_npc_is_not_duplicated(self):
        lua = runtime()
        lua.execute('''
          ns.ProfFormulaOffers={[99]={{npcID=7,price=10,quantity=1,unlimited=true,
            reference=true,priceVerified=true,source='wowhead-forever',verifiedAt='2026-10-18'}}}
          local source={vendors={{id=7,name='duplicate'}, {id=8,name='other'},
            {id=9,name='cheap',price=5,quantity=1,priceVerified=true,verifiedAt='2026-10-18'}}}
          local offers=ns.VendorPriceDB.GetFormulaOffers(99,nil,source)
          assert(#offers==3 and offers[1].npcID==9 and offers[2].npcID==7 and offers[3].npcID==8)
          assert(offers[3].price==nil and not offers[3].priceUsable)
        ''')

    def test_all_bundled_supplier_metadata_match_evidence_and_have_no_prices(self):
        lua = runtime()
        evidence = json.loads((ROOT / "tests/data/vendor-price-reference.json").read_text(encoding="utf-8-sig"))
        count = 0
        for item, offers in lua.globals().ns.ProfVendorOffers.items():
            for _, offer in offers.items():
                with self.subTest(item=item, npc=offer.npcID):
                    shelf = evidence["shelves"][str(offer.npcID)]
                    self.assertNotIn(item, shelf["excludedLimited"])
                    rows = [r for r in shelf["rows"] if r["itemID"] == item]
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(offer.quantity, rows[0]["quantity"])
                    self.assertNotIn("price", rows[0])
                    self.assertTrue(rows[0]["unlimited"] and offer.catalogueOnly)
                    for field in ("price", "reference", "priceVerified", "estimated", "priceBasis"):
                        self.assertIsNone(offer[field])
                    self.assertEqual(offer.verifiedAt, evidence["verifiedAt"])
                    count += 1
        self.assertEqual(count, 202)

    def test_loading_bundled_catalogues_never_produces_npc_prices(self):
        lua = runtime()
        lua.execute('''
          local access={npcAccess={[242498]=true},faction='A'}
          for id in pairs(ns.ProfVendorOffers) do
            assert(#ns.VendorPriceDB.GetOffers(id,access)==0)
            assert(ns.VendorPriceDB.GetPrice(id,access)==nil)
          end
          for id,offers in pairs(ns.ProfFormulaOffers) do
            for _,offer in ipairs(offers) do
              assert(offer.price==nil and offer.reference==nil and offer.priceVerified==nil)
              assert(offer.estimated==nil and offer.priceBasis==nil)
            end
            for _,offer in ipairs(ns.VendorPriceDB.GetFormulaOffers(id,access)) do
              assert(offer.price==nil and offer.unit==nil and not offer.priceUsable)
            end
          end
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
