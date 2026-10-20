"""Item material prices and formula NPC quotations ignore legacy catalogues."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path.home() / "AppData/Local/Temp/df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCKS = r'''
test={faction='Alliance',merchantReads=0,dbReads=0,frames=0}
db={vendorPrices={[999900]={p=1,t=99}}}
ns={ProfVendors={},ProfItems={}}
ns.DB=function()
    test.dbReads=test.dbReads+1
    if test.denyDB then error('NPC prices must not read SavedVariables')end
    return db
end
function UnitFactionGroup()return test.faction end
function UnitLevel()return 30 end
function GetMerchantNumItems()test.merchantReads=test.merchantReads+1;error('merchant API called')end
function GetMerchantItemInfo()test.merchantReads=test.merchantReads+1;error('merchant API called')end
C_MerchantFrame={GetItemInfo=GetMerchantItemInfo}
function CreateFrame()
    test.frames=test.frames+1
    local f={events={}}
    function f:RegisterEvent(event)self.events[event]=true end
    function f:SetScript(_,fn)self.handler=fn end
    return f
end
function put(item,values,quantity)
    local raw={npc_id=7,name_en='Schema Seller',zone_id=12,side='n',
        cost_copper=21,cost_text='21c',stock=-1,price_source='client'}
    for key,value in pairs(values or {})do raw[key]=value end
    local record={item_id=item,VendorStackCount=quantity or 5,offers={[raw.npc_id]=raw}}
    for _,key in ipairs({'cost_copper','cost_text','price_source',
      'currency_kind','currency_id','currency_amount'})do record[key]=raw[key] end
    ns.ProfItems[item]=record
    return raw,record
end
'''


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCKS)
    lua.execute((ROOT / 'Core/ProfItemPrices.lua').read_text(encoding='utf-8-sig'), 'Test', lua.globals().ns)
    return lua


class VendorOffers(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()

    def test_empty_data_has_no_price_supplier_or_formula(self):
        self.lua.execute('''
          assert(ns.ProfItemPrices.GetPrice(999001)==nil)
          assert(#ns.ProfItemPrices.GetOffers(999001)==0)
          assert(#ns.ProfItemPrices.GetSuppliers(999001)==0)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999001)==0)
        ''')

    def test_raw_bundle_price_preserves_source_without_fabricated_audit_date(self):
        self.lua.execute('''
          put(999002)
          local q=ns.ProfItemPrices.GetOffers(999002)[1]
          assert(q.price==21 and q.quantity==5 and q.bundleSize==5 and q.unit==21/5)
          assert(q.source=='client' and q.priceSource=='client' and q.priceBasis=='Data_ProfItems')
          assert(q.reference and not q.estimated and q.verifiedAt==nil and q.priceVerified==nil)
          assert(q.npcID==nil and q.npcName==nil and q.materialPrice)
          assert(ns.ProfItemPrices.GetPrice(999002)==21/5)
        ''')

    def test_wowhead_source_and_explicit_zero_cost_remain_known(self):
        self.lua.execute('''
          put(999003,{cost_copper=0,cost_text='0c',price_source='wowhead'})
          local q=ns.ProfItemPrices.GetOffers(999003)[1]
          assert(q.price==0 and q.unit==0 and q.source=='wowhead')
          assert(ns.ProfItemPrices.GetPrice(999003)==0)
        ''')

    def test_invalid_cost_or_missing_noninteger_bundle_cannot_price_goods(self):
        self.lua.execute('''
          local raw,item=put(999004)
          for _,value in ipairs({-1,1.5,'21',math.huge,0/0})do
            raw.cost_copper=value;item.cost_copper=value
            assert(#ns.ProfItemPrices.GetOffers(999004)==0)
            assert(ns.ProfItemPrices.GetFormulaOffers(999004)[1].price==nil)
          end
          raw.cost_copper=21;item.cost_copper=21
          for _,value in ipairs({0,-1,1.5,'5',math.huge,0/0})do
            item.VendorStackCount=value;assert(#ns.ProfItemPrices.GetOffers(999004)==0)
          end
          item.VendorStackCount=nil
          assert(#ns.ProfItemPrices.GetOffers(999004)==0)
          local f=ns.ProfItemPrices.GetFormulaOffers(999004)
          assert(#f==1 and f[1].price==nil and not f[1].priceUsable)
        ''')

    def test_page_text_without_copper_remains_unpriced(self):
        self.lua.execute('''
          local raw,item=put(999005);raw.cost_copper=nil;raw.cost_text='99 tokens'
          item.cost_copper=nil;item.cost_text='99 tokens'
          assert(#ns.ProfItemPrices.GetSuppliers(999005)==0)
          assert(#ns.ProfItemPrices.GetOffers(999005)==0 and ns.ProfItemPrices.GetPrice(999005)==nil)
          local f=ns.ProfItemPrices.GetFormulaOffers(999005)
          assert(#f==1 and f[1].price==nil and not f[1].priceUsable)
        ''')

    def test_old_namespaces_sources_seeds_and_locations_cannot_establish_supply(self):
        self.lua.execute('''
          local old={npcID=7,price=1,quantity=1,unlimited=true,reference=true,
            priceVerified=true,verifiedAt='date',source='merchant'}
          ns.ProfVendorOffers={[999006]={old}}
          ns.ProfFormulaOffers={[999006]={old}}
          ns.VendorPriceSeed={[999006]=1};ns.ItemPurchasePrices={[999006]={1,1}}
          ns.ProfVendors[7]={12,1429,10,20}
          local source={vendors={{id=7,name='Old source',price=1,quantity=1,unlimited=true}}}
          assert(ns.ProfItemPrices.GetPrice(999006)==nil)
          assert(#ns.ProfItemPrices.GetOffers(999006)==0 and #ns.ProfItemPrices.GetSuppliers(999006)==0)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999006,nil,source)==0)
        ''')

    def test_old_price_and_conditions_cannot_override_new_rows(self):
        self.lua.execute('''
          put(999007)
          local poison={npcID=7,price=999,quantity=1,unlimited=false,faction='H',
            hasExtendedCost=true,requirements={unknown=true},available=false}
          ns.ProfVendorOffers={[999007]={poison}};ns.ProfFormulaOffers={[999007]={poison}}
          local source={vendors={{id=7,price=999,faction='H',requirements={level=999}}}}
          assert(ns.ProfItemPrices.GetPrice(999007,{faction='A'})==21/5)
          local f=ns.ProfItemPrices.GetFormulaOffers(999007,{faction='A'},source)
          assert(#f==1 and f[1].price==21 and f[1].quantity==5 and f[1].priceUsable)
          assert(poison.price==999 and poison.available==false)
        ''')

    def test_saved_merchant_and_auctionator_vendor_caches_are_never_read(self):
        self.lua.execute('''
          put(999008)
          db.profVendorOffers={[999008]={old={npcID=7,price=1,quantity=1,unlimited=true}}}
          Auctionator={API={v1={GetVendorPriceByItemID=function()error('old vendor cache read')end,
            GetVendorPrice=function()error('old vendor cache read')end}}}
          assert(ns.ProfItemPrices.GetPrice(999008,{allowVendorCache=true})==21/5)
          assert(ns.ProfItemPrices.GetPrice(999900)==nil)
          assert(test.dbReads==0 and db.profVendorOffers[999008].old.price==1)
        ''')

    def test_runtime_merchants_and_reputation_events_do_not_change_prices(self):
        self.lua.execute('''
          put(999009)
          assert(ns.ProfItemPrices.GetPrice(999009)==21/5)
          assert(test.merchantReads==0 and test.dbReads==0 and test.frames==0)
          assert(ns.ProfItemPrices.Scan==nil and ns.ProfItemPrices.Count==nil)
          assert(ns.ProfItemPrices.GetBasePurchasePrice==nil and ns.ProfItemPrices.OnChanged==nil)
        ''')

    def test_side_and_explicit_npc_access_restrict_formulas_without_gating_materials(self):
        self.lua.execute('''
          local raw=put(999010,{side='a'})
          assert(#ns.ProfItemPrices.GetOffers(999010,{faction='Horde'})==1)
          assert(#ns.ProfItemPrices.GetOffers(999010,{faction='Alliance'})==1)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999010,{faction='H'})==0)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999010,{faction='A'})==1)
          for _,side in ipairs({'n','N','Neutral'})do
            raw.side=side;assert(#ns.ProfItemPrices.GetOffers(999010,{faction='H'})==1)
            assert(#ns.ProfItemPrices.GetFormulaOffers(999010,{faction='H'})==1)
          end
          raw.side=nil
          assert(#ns.ProfItemPrices.GetOffers(999010,{npcAccess={[7]=false}})==1)
          assert(#ns.ProfItemPrices.GetSuppliers(999010,{npcAccess={[7]=false}})==1)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999010,{npcAccess={[7]=false}})==0)
        ''')

    def test_currency_or_item_exchange_including_zero_placeholders_is_not_gold(self):
        self.lua.execute('''
          for _,values in ipairs({{currency_kind='currency'},{currency_kind='item'},
            {currency_id=0},{currency_amount=0},{currency_kind='0'},
            {currency_id=77,currency_amount=3}})do
            put(999011,values)
            assert(#ns.ProfItemPrices.GetOffers(999011)==0)
            assert(#ns.ProfItemPrices.GetSuppliers(999011)==0)
            assert(#ns.ProfItemPrices.GetFormulaOffers(999011)==0)
          end
          put(999011,{currency_kind=' \t ',currency_id='',currency_amount='  '})
          assert(#ns.ProfItemPrices.GetOffers(999011)==1)
          local raw,item=put(999011,{currency_kind='item',currency_id=77,currency_amount=3})
          item.currency_kind=nil;item.currency_id=nil;item.currency_amount=nil
          assert(#ns.ProfItemPrices.GetOffers(999011)==1,
            'a formula seller exchange overrode the independent material base price')
          assert(#ns.ProfItemPrices.GetFormulaOffers(999011)==0)
        ''')

    def test_formula_stock_limits_do_not_restrict_anonymous_material_quotes(self):
        self.lua.execute('''
          local raw=put(999012,{stock=2})
          assert(#ns.ProfItemPrices.GetOffers(999012)==1 and #ns.ProfItemPrices.GetSuppliers(999012)==1)
          local f=ns.ProfItemPrices.GetFormulaOffers(999012)
          assert(#f==1 and f[1].limited and f[1].maxStock==2 and f[1].stock==nil and f[1].priceUsable)
          raw.stock=nil;f=ns.ProfItemPrices.GetFormulaOffers(999012)
          assert(#f==1 and f[1].stockUnknown and f[1].stock==nil)
          assert(#ns.ProfItemPrices.GetOffers(999012)==1)
          raw.stock=-1
          assert(#ns.ProfItemPrices.GetOffers(999012)==1 and #ns.ProfItemPrices.GetSuppliers(999012)==1)
        ''')

    def test_zero_refresh_cap_keeps_formula_quote_but_marks_it_unavailable(self):
        self.lua.execute('''
          put(999013,{stock=0})
          local f=ns.ProfItemPrices.GetFormulaOffers(999013)
          assert(#f==1 and f[1].price==21 and f[1].maxStock==0)
          assert(f[1].limited and f[1].stock==nil and not f[1].priceUsable and not f[1].available)
          local material=ns.ProfItemPrices.GetOffers(999013)[1]
          assert(material and material.price==21 and material.npcID==nil and material.maxStock==nil)
        ''')

    def test_root_cost_without_npc_establishes_material_price_but_no_formula_seller(self):
        self.lua.execute('''
          ns.ProfItems[999014]={item_id=999014,VendorStackCount=5,cost_copper=21,
            cost_text='21c',price_source='client',stock=-1,offers={}}
          ns.ProfVendors[7]={12,1429,10,20}
          assert(ns.ProfItemPrices.GetPrice(999014)==21/5)
          assert(#ns.ProfItemPrices.GetSuppliers(999014)==1 and #ns.ProfItemPrices.GetOffers(999014)==1)
          assert(ns.ProfItemPrices.GetSuppliers(999014)[1].npcID==nil)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999014,nil,{vendors={{id=7}}})==0)
        ''')

    def test_non_schema_metadata_is_ignored_instead_of_becoming_compatibility_policy(self):
        self.lua.execute('''
          put(999015,{price=999,quantity=1,unlimited=false,available=false,purchasable=false,
            faction='H',hasExtendedCost=true,currencyID=77,requirements={unknown=true},summoned=true})
          local q=ns.ProfItemPrices.GetOffers(999015,{faction='A'})[1]
          assert(q and q.price==21 and q.quantity==5 and q.available and q.purchasable)
          assert(q.requirements==nil and q.summoned==nil and q.hasExtendedCost==nil)
        ''')

    def test_returned_quotes_and_suppliers_do_not_mutate_raw_rows(self):
        self.lua.execute('''
          local raw,item=put(999016)
          local q=ns.ProfItemPrices.GetOffers(999016)[1];q.price=999;q.npcID=888
          local s=ns.ProfItemPrices.GetSuppliers(999016)[1];s.quantity=100
          local f=ns.ProfItemPrices.GetFormulaOffers(999016)[1];f.price=900
          assert(raw.cost_copper==21 and raw.npc_id==7 and raw.stock==-1 and item.VendorStackCount==5)
          assert(raw.price==nil and raw.unit==nil and ns.ProfItemPrices.GetPrice(999016)==21/5)
        ''')

    def test_invalid_or_conflicting_npc_ids_do_not_create_formula_offers(self):
        self.lua.execute('''
          local raw=put(999017)
          raw.npc_id=8
          assert(#ns.ProfItemPrices.GetFormulaOffers(999017)==0)
          assert(ns.ProfItemPrices.GetPrice(999017)==21/5)
          raw.npc_id=7;ns.ProfItems[999017].offers={[0]=raw}
          assert(#ns.ProfItemPrices.GetFormulaOffers(999017)==0)
          assert(ns.ProfItemPrices.GetPrice(999017)==21/5)
        ''')

    def test_formula_quotes_sort_by_unit_price_without_changing_material_price(self):
        self.lua.execute('''
          local raw,item=put(999018)
          item.offers[8]={npc_id=8,cost_copper=10,stock=-1,side='n',price_source='wowhead'}
          local q=ns.ProfItemPrices.GetFormulaOffers(999018)
          assert(#q==2 and q[1].npcID==8 and q[1].unit==2 and q[2].npcID==7)
          assert(raw.cost_copper==21 and item.offers[8].cost_copper==10)
          local material=ns.ProfItemPrices.GetOffers(999018)
          assert(#material==1 and material[1].npcID==nil and material[1].unit==21/5)
        ''')


if __name__ == '__main__':
    unittest.main()
