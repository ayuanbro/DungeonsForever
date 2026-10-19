"""Merchant API regression tests (Lua 5.1, no game/client required)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path.home() / "AppData/Local/Temp/df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

MOCKS = r'''
test = { name="Alice", realm="Realm", faction="Alliance", mode="modern", rep=0,
    guid="Creature-0-1-2-3-12345-00000001", entries={} }
db = { vendorPrices = { [999900] = { p=1, t=99 } } }
ns = { VendorPriceSeed = { [999901]=1 }, ProfVendors = {}, invalidations=0 }
ns.DB = function() return db end
ns.ProfRouteAuto = { Invalidate=function() ns.invalidations=ns.invalidations+1 end }
function time() return 1000 end
function UnitFullName() return test.name, test.realm end
function UnitName(unit) if unit=="npc" then return "Test Merchant" else return test.name end end
function GetRealmName() return test.realm end
function UnitFactionGroup() return test.faction end
function UnitGUID() return test.guid end
function GetMerchantNumItems() return #test.entries end
function GetMerchantItemID(index) return test.entries[index].id end
function GetMerchantItemInfo(index)
    local e = test.entries[index]
    if test.mode=="old7" then
        return e.name or "Item", 1, e.price, e.quantity, e.stock, e.purchasable, e.extended
    end
    return e.name or "Item", 1, e.price, e.quantity, e.stock, e.purchasable,
        e.usable, e.extended, e.currency or 0, 0
end
C_MerchantFrame = { GetItemInfo=function(index)
    if test.mode~="modern" then return nil end
    local e = test.entries[index]
    return { name=e.name or "Item", price=e.price, stackCount=e.quantity,
        numAvailable=e.stock, isPurchasable=e.purchasable, isUsable=e.usable,
        hasExtendedCost=e.extended, currencyID=e.currency or 0 }
end }
C_Reputation = {
    GetNumFactions=function() return 1 end,
    GetFactionDataByIndex=function() return { factionID=72, reaction=test.standing or 4, currentStanding=test.rep } end,
    GetFactionDataByID=function(id)
        if id==72 then return { reaction=test.standing or 4, atWarWith=test.atWar } end
    end,
}
C_Timer = { After=function(_, fn) fn() end }
function CreateFrame()
    vendorFrame={ events={} }
    function vendorFrame:RegisterEvent(event) self.events[event]=true end
    function vendorFrame:SetScript(_, fn) self.handler=fn end
    return vendorFrame
end
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCKS)
    ns = lua.globals().ns
    lua.execute((ROOT / "Core/Data/Data_ProfVendorOffers.lua").read_text(encoding="utf-8-sig"), "Test", ns)
    lua.execute((ROOT / "Core/VendorPriceDB.lua").read_text(encoding="utf-8-sig"), "Test", ns)
    return lua


class VendorOffers(unittest.TestCase):
    def test_vendor_cache_quote_requires_matching_observed_pack_and_keeps_estimate_flag(self):
        lua=runtime()
        lua.execute('''
          test.guid='Creature-0-1-2-3-1313-00000001'
          test.entries={{id=3371,price=20,quantity=5,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan(); test.name='Bob'
          -- No audited price: only the supplier/observed pack is known here.
          for _,offer in ipairs(ns.ProfVendorOffers[3371]) do
            offer.price=nil;offer.reference=nil;offer.priceVerified=nil
          end
          Auctionator={API={v1={GetVendorPriceByItemID=function(caller,id) assert(caller=='DungeonsForever' and id==3371); return 4 end,
            GetVendorPrice=function() error('obsolete API selected over installed public API') end}}}
          local offers=ns.VendorPriceDB.GetOffers(3371,{allowVendorCache=true,requireObservedPrice=false})
          assert(#offers==1 and offers[1].npcID==1313 and offers[1].quantity==5 and offers[1].price==20)
          assert(offers[1].estimated and offers[1].source=='auctionator-vendor')
          assert(not offers[1].reference,'cached estimate inherited trusted reference flag')
          assert(ns.VendorPriceDB.GetPrice(3371)==4,'unit-price consumer disagrees with route quotation')
          assert(#ns.VendorPriceDB.GetOffers(3371,{requireObservedPrice=true})==0)
        ''')

    def test_verified_thread_reference_beats_cross_character_vendor_cache(self):
        lua=runtime()
        lua.execute('''
          test.guid='Creature-0-1-2-3-4168-00000001'
          test.entries={{id=2320,price=8,quantity=1,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan(); test.name='Bob'
          Auctionator={API={v1={GetVendorPriceByItemID=function() return 8 end}}}
          local offers=ns.VendorPriceDB.GetOffers(2320,{allowVendorCache=true})
          assert(#offers>0)
          for _,offer in ipairs(offers) do
            assert(offer.reference and offer.priceVerified and offer.source=='wowhead-forever')
          end
          assert(#ns.VendorPriceDB.GetOffers(2320,{requireObservedPrice=true})==0)
        ''')

    def test_stale_discount_cache_uses_reference_then_current_merchant_price(self):
        lua=runtime()
        lua.execute('''
          test.guid='Creature-0-1-2-3-4168-00000001'
          test.entries={{id=2320,price=8,quantity=1,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          Auctionator={API={v1={GetVendorPriceByItemID=function() return 8 end}}}
          test.standing=5;test.entries={};vendorFrame.handler(vendorFrame,'UPDATE_FACTION')
          local offers=ns.VendorPriceDB.GetOffers(2320,{allowVendorCache=true})
          assert(#offers>0 and offers[1].reference and offers[1].priceBasis=='wowhead-reference')
          test.entries={{id=2320,price=7,quantity=1,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          offers=ns.VendorPriceDB.GetOffers(2320,{allowVendorCache=true})
          assert(#offers==1 and offers[1].source=='merchant' and offers[1].price==7)
          assert(not offers[1].reference and not offers[1].estimated)
        ''')

    def test_thread_reference_procurement_has_no_pending_merchant_diagnostic(self):
        lua=runtime()
        ns=lua.globals().ns
        ns.LoadForeverPages=True
        for filename in ('ProfEconomy.lua','ProfRouteSolver.lua'):
            lua.execute((ROOT/'Core'/filename).read_text(encoding='utf-8-sig'),'Test',ns)
        lua.execute('''
          test.guid='Creature-0-1-2-3-4168-00000001'
          test.entries={{id=2320,price=8,quantity=1,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan();test.name='Bob'
          Auctionator={API={v1={GetVendorPriceByItemID=function() return 8 end}}}
          local snapshot={recipes={},professions={},known={},prices={},vendorItems={[2320]=true},
            offers={[2320]=ns.VendorPriceDB.GetOffers(2320,{allowVendorCache=true})}}
          local r=ns.ProfRouteSolver.Procure(snapshot,2320,12)
          assert(r.feasible and r.costComplete and r.vendorTotal>0 and r.ahTotal==0)
          assert(r.referencePrices and #r.diagnostics==0)
          assert(#r.mats==1 and r.mats[1].reference and r.mats[1].quoteSource=='wowhead-forever')
        ''')

    def test_unit_cache_without_observed_pack_uses_verified_reference_instead(self):
        lua=runtime()
        lua.execute('''
          Auctionator={API={v1={GetVendorPrice=function() return 4 end}}}
          assert(#ns.VendorPriceDB.GetSuppliers(3371)>0)
          local offers=ns.VendorPriceDB.GetOffers(3371,{allowVendorCache=true,requireObservedPrice=false})
          assert(#offers>0)
          for _,offer in ipairs(offers) do
            assert(offer.source=='wowhead-forever' and offer.reference and offer.quantity==5)
          end
        ''')

    def test_observed_unlimited_vendor_is_discovered_without_reference_seed(self):
        lua=runtime()
        lua.execute('''
          test.entries={{id=999099,price=20,quantity=5,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          local suppliers=ns.VendorPriceDB.GetSuppliers(999099)
          assert(#suppliers==1 and suppliers[1].npcID==12345 and suppliers[1].source=='merchant')
        ''')

    def test_verified_reference_quotes_fill_missing_api_prices(self):
        lua = runtime()
        self.assertGreater(lua.eval("#ns.VendorPriceDB.GetSuppliers(3371)"), 0)
        self.assertGreater(lua.eval("#ns.VendorPriceDB.GetOffers(3371)"), 0)
        self.assertEqual(lua.eval("#ns.VendorPriceDB.GetOffers(3371,{requireObservedPrice=true})"), 0)
        self.assertGreater(lua.eval("ns.VendorPriceDB.GetPrice(3371)"), 0)
        self.assertTrue(lua.eval("ns.VendorPriceDB.GetOffers(3371)[1].reference"))
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetOffers(3371)[1].priceBasis"), "wowhead-reference")
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetOffers(3371)[1].quantity"), 5)
        self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999900)"))
        self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999901)"))
        self.assertEqual(lua.eval("db.vendorPrices[999900].t"), 99)

    def test_client_quote_wins_even_when_reference_is_cheaper(self):
        lua=runtime()
        lua.execute('''
          test.guid='Creature-0-1-2-3-1313-00000001'
          test.entries={{id=3371,price=50,quantity=5,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          local offers=ns.VendorPriceDB.GetOffers(3371)
          assert(#offers==1 and offers[1].price==50 and offers[1].source=='merchant')
          assert(not offers[1].reference and not offers[1].estimated)
          assert(ns.VendorPriceDB.GetPrice(3371)==10)
          test.entries[1].price=0;ns.VendorPriceDB.Scan()
          assert(ns.VendorPriceDB.GetPrice(3371)==0,'valid API zero price was replaced')
        ''')

    def test_changed_discount_uses_reference_until_rescanned(self):
        lua=runtime()
        lua.execute('''
          test.guid='Creature-0-1-2-3-1313-00000001'
          test.entries={{id=3371,price=50,quantity=5,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan();test.standing=5;test.entries={}
          vendorFrame.handler(vendorFrame,'UPDATE_FACTION')
          local offers=ns.VendorPriceDB.GetOffers(3371)
          assert(#offers>0 and offers[1].reference)
          assert(#ns.VendorPriceDB.GetOffers(3371,{requireObservedPrice=true})==0)
          test.entries={{id=3371,price=17,quantity=5,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          assert(ns.VendorPriceDB.GetPrice(3371)==17/5)
        ''')

    def test_summoned_catalogue_does_not_assume_access(self):
        lua=runtime()
        lua.execute('''
          assert(#ns.VendorPriceDB.GetSuppliers(10284)==0)
          assert(#ns.VendorPriceDB.GetOffers(10284)==0)
          assert(#ns.VendorPriceDB.GetSuppliers(10284,{npcAccess={[242498]=true}})==1)
          test.guid='Creature-0-1-2-3-242498-00000001'
          test.entries={{id=10284,price=20,quantity=5,stock=-1,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetOffers(10284)==1)
          assert(ns.VendorPriceDB.GetOffers(10284)[1].source=='merchant')
        ''')

    def test_all_merchant_api_versions(self):
        for mode in ("old7", "legacy10", "modern"):
            with self.subTest(mode=mode):
                lua = runtime()
                lua.globals().test.mode = mode
                lua.execute('''
                test.entries={
                    {id=999001, price=21, quantity=5, stock=-1, purchasable=true, usable=true, extended=false},
                    {id=999002, price=1, quantity=1, stock=3, purchasable=true, usable=true, extended=false},
                    {id=999003, price=2, quantity=1, stock=0, purchasable=true, usable=true, extended=false},
                    {id=999004, price=99, quantity=1, stock=-1, purchasable=true, usable=true, extended=true},
                    {id=999005, price=99, quantity=1, stock=-1, purchasable=true, usable=true, extended=true, currency=777},
                    {id=999006, price=99, quantity=1, stock=-1, purchasable=false, usable=false, extended=false},
                    {id=999007, price=99, quantity=0, stock=-1, purchasable=true, usable=true, extended=false},
                    {id=999008, price=0, quantity=1, stock=-1, purchasable=true, usable=true, extended=false},
                }
                ns.VendorPriceDB.Scan()
                ''')
                self.assertEqual(lua.eval("#ns.VendorPriceDB.GetOffers(999001,{requireObservedPrice=true})"), 1)
                self.assertAlmostEqual(lua.eval("ns.VendorPriceDB.GetPrice(999001)"), 4.2)
                self.assertEqual(lua.eval("ns.VendorPriceDB.GetOffers(999001)[1].quantity"), 5)
                self.assertEqual(lua.eval("ns.VendorPriceDB.GetOffers(999001)[1].price"), 21)
                self.assertEqual(lua.eval("ns.VendorPriceDB.GetOffers(999001)[1].npcID"), 12345)
                self.assertEqual(lua.eval("ns.VendorPriceDB.GetOffers(999001)[1].character"), "Alice-Realm")
                self.assertFalse(lua.eval("ns.VendorPriceDB.GetOffers(999001)[1].estimated"))
                for item in range(999002, 999008):
                    self.assertEqual(lua.eval(f"#ns.VendorPriceDB.GetOffers({item},{{requireObservedPrice=true}})"), 0)
                self.assertEqual(lua.eval("ns.VendorPriceDB.GetPrice(999008)"),0)
                self.assertEqual(lua.eval("db.vendorPrices[999900].p"), 1)
                self.assertGreater(lua.eval("ns.invalidations"), 0)

    def test_currency_flag_independent_of_extended_cost(self):
        for mode in ("modern", "legacy10"):
            with self.subTest(mode=mode):
                lua = runtime()
                lua.globals().test.mode = mode
                lua.execute('''test.entries={{id=999010,price=12,quantity=1,stock=-1,
                    purchasable=true,usable=true,extended=false,currency=777}};ns.VendorPriceDB.Scan()''')
                self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999010)"))

    def test_unusable_but_purchasable_is_allowed_in_modern_api(self):
        lua = runtime()
        lua.execute('''test.entries={{id=999010,price=12,quantity=1,stock=-1,
            purchasable=true,usable=false,extended=false}};ns.VendorPriceDB.Scan()''')
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetPrice(999010)"), 12)

    def test_character_isolation_and_reputation_invalidation(self):
        lua = runtime()
        lua.execute('''test.entries={{id=999011,price=12,quantity=1,stock=-1,
            purchasable=true,usable=true,extended=false}};ns.VendorPriceDB.Scan()''')
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetPrice(999011)"), 12)
        lua.execute('test.name="Bob"')
        self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999011)"))
        lua.execute('test.name="Alice";test.rep=100;test.entries={};vendorFrame.handler(vendorFrame,"UPDATE_FACTION")')
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetPrice(999011)"), 12)
        lua.execute('test.standing=5;vendorFrame.handler(vendorFrame,"UPDATE_FACTION")')
        self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999011)"))
        lua.execute('''test.entries={{id=999011,price=11,quantity=1,stock=-1,
            purchasable=true,usable=true,extended=false}};ns.VendorPriceDB.Scan()''')
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetPrice(999011)"), 11)

    def test_observed_limited_stock_suppresses_same_npc_reference(self):
        lua = runtime()
        lua.execute('''test.guid="Creature-0-1-2-3-1313-00000001";
            test.entries={{id=3371,price=20,quantity=5,stock=3,
                purchasable=true,usable=true,extended=false}};ns.VendorPriceDB.Scan()''')
        self.assertTrue(lua.eval('''(function()
            for _,offer in ipairs(ns.VendorPriceDB.GetOffers(3371)) do
                if offer.npcID==1313 then return false end
            end
            return true
        end)()'''))

    def test_persisted_discount_does_not_survive_changed_reputation(self):
        lua = runtime()
        lua.execute('''test.entries={{id=999014,price=12,quantity=1,stock=-1,
            purchasable=true,usable=true,extended=false}};ns.VendorPriceDB.Scan();test.rep=200;test.standing=5''')
        # Re-loading the module represents a new UI session with existing SV data.
        lua.execute((ROOT / "Core/VendorPriceDB.lua").read_text(encoding="utf-8-sig"), "Test", lua.globals().ns)
        self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999014)"))

    def test_rejection_record_tracks_changes_to_purchase_conditions(self):
        lua = runtime()
        lua.execute('''test.entries={{id=999015,price=12,quantity=1,stock=3,
            purchasable=true,usable=true,extended=false}};ns.VendorPriceDB.Scan()
            test.entries[1].stock=-1;test.entries[1].extended=true;ns.VendorPriceDB.Scan()''')
        self.assertTrue(lua.eval('db.profVendorOffers[999015]["Alice-Realm:12345"].unlimited'))
        self.assertTrue(lua.eval('db.profVendorOffers[999015]["Alice-Realm:12345"].hasExtendedCost'))
        self.assertIsNone(lua.eval("ns.VendorPriceDB.GetPrice(999015)"))

    def test_faction_requirement_unknown_and_hostile_are_filtered(self):
        lua = runtime()
        self.assertTrue(lua.eval('''(function()
            for _,offer in ipairs(ns.VendorPriceDB.GetOffers(247786,{faction="H"})) do
                if offer.faction=="A" then return false end
            end
            return true
        end)()'''))
        lua.execute('''ns.ProfVendorOffers[999012]={{itemID=999012,npcID=1,price=1,quantity=1,
            unlimited=true,source="wowhead-forever",verifiedAt="2026-10-17",
            reference=true,priceVerified=true,requirements={unknown=true}}}''')
        self.assertEqual(lua.eval("#ns.VendorPriceDB.GetOffers(999012)"), 0)
        lua.execute('''ns.ProfVendorOffers[999012][1].requirements=nil;
            ns.ProfVendorOffers[999012][1].npcFactionID=72;test.standing=2''')
        self.assertEqual(lua.eval("#ns.VendorPriceDB.GetOffers(999012)"), 0)

    def test_references_preserve_npc_access_faction_and_rejection_filters(self):
        lua=runtime()
        lua.execute('''
          for _,offer in ipairs(ns.VendorPriceDB.GetOffers(3371,{faction='H',npcAccess={[5594]=false}})) do
            assert(offer.faction~='A' and offer.npcID~=5594 and not offer.summoned)
          end
          ns.ProfVendorOffers[999020]={{itemID=999020,npcID=72,price=20,quantity=5,
            unlimited=true,available=true,source='wowhead-forever',verifiedAt='2026-10-18',
            reference=true,priceVerified=true,faction='A'}}
          assert(#ns.VendorPriceDB.GetOffers(999020)==1)
          assert(#ns.VendorPriceDB.GetOffers(999020,{faction='H'})==0)
          test.guid='Creature-0-1-2-3-72-00000001'
          test.entries={{id=999020,price=20,quantity=5,stock=-1,purchasable=true,usable=true,extended=true}}
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetOffers(999020)==0,'extended currency observation did not block fallback')
        ''')

    def test_unverified_seed_price_never_becomes_fallback(self):
        lua=runtime()
        lua.execute('''
          ns.ProfVendorOffers[999021]={{itemID=999021,npcID=1,price=1,quantity=1,
            unlimited=true,available=true,source='wowhead-forever',verifiedAt='2026-10-18'}}
          assert(#ns.VendorPriceDB.GetOffers(999021)==0)
          ns.ProfVendorOffers[999021][1].reference=true
          assert(#ns.VendorPriceDB.GetOffers(999021)==0)
          ns.ProfVendorOffers[999021][1].priceVerified=true
          assert(#ns.VendorPriceDB.GetOffers(999021)==1)
        ''')

    def test_api_rejection_without_price_still_suppresses_reference(self):
        lua=runtime()
        lua.execute('''
          ns.ProfVendorOffers[999022]={{itemID=999022,npcID=12345,price=20,quantity=5,
            unlimited=true,available=true,source='wowhead-forever',verifiedAt='2026-10-18',
            reference=true,priceVerified=true}}
          test.entries={{id=999022,quantity=5,stock=3,purchasable=true,usable=true,extended=false}}
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetOffers(999022)==0)
          assert(db.profVendorOffers[999022]['Alice-Realm:12345'].unlimited==false)
          test.entries[1].stock=-1;test.entries[1].purchasable=false
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetOffers(999022)==0)
          test.entries[1].purchasable=true;test.entries[1].extended=true
          ns.VendorPriceDB.Scan()
          assert(#ns.VendorPriceDB.GetOffers(999022)==0)
          test.entries[1].extended=false;ns.VendorPriceDB.Scan()
          local offers=ns.VendorPriceDB.GetOffers(999022)
          assert(#offers==1 and offers[1].reference,'unlimited shelf with missing price failed to fall back')
          assert(#ns.VendorPriceDB.GetOffers(999022,{requireObservedPrice=true})==0)
        ''')

    def test_changes_notify_once_and_offers_are_copies(self):
        lua = runtime()
        lua.execute('''test.notifications=0;ns.VendorPriceDB.OnChanged(function() test.notifications=test.notifications+1 end)
            test.entries={{id=999013,price=12,quantity=1,stock=-1,
                purchasable=true,usable=true,extended=false}};ns.VendorPriceDB.Scan();ns.VendorPriceDB.Scan()''')
        self.assertEqual(lua.eval("test.notifications"), 1)
        lua.execute("ns.VendorPriceDB.GetOffers(999013)[1].price=999")
        self.assertEqual(lua.eval("ns.VendorPriceDB.GetPrice(999013)"), 12)

    def test_catalogue_has_no_limited_or_unproven_legacy_imports(self):
        lua = runtime()
        self.assertTrue(lua.eval('''(function()
            for id,offers in pairs(ns.ProfVendorOffers) do
                for _,offer in ipairs(offers) do
                    if not offer.unlimited or offer.itemID~=id or not offer.url then return false end
                    if offer.reference then
                        if not offer.priceVerified or not offer.estimated or offer.priceBasis~='wowhead-reference'
                            or type(offer.price)~='number' or offer.price<0 or not offer.quantity
                            or offer.quantity<1 or offer.quantity~=math.floor(offer.quantity) then return false end
                    elseif not offer.catalogueOnly or offer.price~=nil or offer.quantity~=nil then return false end
                end
            end
            return true
        end)()'''))
        for item in (765, 4357, 4364, 10938, 10940, 6289, 9305):
            self.assertIsNone(lua.eval(f"ns.ProfVendorOffers[{item}]"))
        for item in (10284, 18567, 247786, 272941, 273636):
            self.assertGreater(lua.eval(f"#ns.ProfVendorOffers[{item}]"), 0)

    def test_all_reference_bundle_quotes_match_audited_npc_shelves(self):
        lua=runtime()
        evidence=json.loads((ROOT/"tests/data/vendor-price-reference.json").read_text(encoding="utf-8-sig"))
        count=0
        for item,offers in lua.globals().ns.ProfVendorOffers.items():
            for _,offer in offers.items():
                with self.subTest(item=item,npc=offer.npcID):
                    shelf=evidence["shelves"][str(offer.npcID)]
                    self.assertNotIn(item,shelf["excludedLimited"])
                    rows=[r for r in shelf["rows"] if r["itemID"]==item]
                    self.assertEqual(len(rows),1)
                    self.assertEqual(offer.price,rows[0]["price"])
                    self.assertEqual(offer.quantity,rows[0]["quantity"])
                    self.assertTrue(rows[0]["unlimited"])
                    self.assertTrue(offer.reference and offer.priceVerified)
                    self.assertEqual(offer.verifiedAt,evidence["verifiedAt"])
                    count+=1
        self.assertEqual(count,202)

    def test_reference_bundle_procurement_works_without_auctionator_or_merchant_visit(self):
        lua=runtime()
        ns=lua.globals().ns
        ns.LoadForeverPages=True
        for filename in ("ProfEconomy.lua","ProfRouteSolver.lua"):
            lua.execute((ROOT/"Core"/filename).read_text(encoding="utf-8-sig"),"Test",ns)
        lua.execute('''
          assert(Auctionator==nil and (not db.profVendorOffers or next(db.profVendorOffers)==nil))
          local offers=ns.VendorPriceDB.GetOffers(3371)
          local snapshot={recipes={},inventory={},professions={},known={},prices={[3371]=999},
            vendorItems={[3371]=true},offers={[3371]=offers},coverageComplete=false}
          local r=ns.ProfRouteSolver.Procure(snapshot,3371,6)
          assert(r.feasible and r.costComplete and r.total==36 and r.vendorTotal==36 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].count==10 and r.mats[1].bundleSize==5)
          assert(r.mats[1].npcID==1313 and r.mats[1].reference and r.mats[1].quoteSource=='wowhead-forever')
          for _,action in ipairs(r.actions) do assert(action.type~='buy' or action.source=='vendor') end
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
