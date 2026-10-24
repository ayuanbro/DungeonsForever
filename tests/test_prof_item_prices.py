"""Verified material supply and explicit formula NPC quotes stay independent."""
import csv
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.pipeline-runtime/lib'))
from lupa.lua51 import LuaRuntime as _LocalLuaRuntime
from test_prof_vendor import LuaRuntime, MOCKS, ROOT, runtime


SCHEMA_FIXTURES = r'''
function schema(item, values, quantity)
    local raw={npc_id=7,name_en='Schema Seller',zone_id=12,side='n',stock=-1,
        cost_copper=37,cost_text='37c',price_source='client'}
    for key,value in pairs(values or {}) do raw[key]=value end
    local record={item_id=item,VendorStackCount=quantity or 4,offers={[7]=raw}}
    for _,key in ipairs({'cost_copper','cost_text','price_source',
      'currency_kind','currency_id','currency_amount'})do record[key]=raw[key] end
    ns.ProfItems[item]=record
    material(item,{price=raw.cost_copper,quantity=quantity or 4,
      priceSource=raw.price_source=='wowhead' and 'wowhead_npc_bundle' or 'client_base_bundle',
      currency_kind=raw.currency_kind,currency_id=raw.currency_id,currency_amount=raw.currency_amount})
    return raw
end
'''


class ProfItemPrices(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()
        self.lua.execute(SCHEMA_FIXTURES)

    def economy(self):
        ns = self.lua.globals().ns
        ns.LoadForeverPages = True
        for name in ("ProfEconomy.lua", "ProfRouteSolver.lua"):
            self.lua.execute((ROOT / "Core" / name).read_text(encoding="utf-8-sig"), "Test", ns)

    def fixed_routes(self):
        self.economy()
        self.lua.execute((ROOT / "Core/ProfRouteAuto.lua").read_text(encoding="utf-8-sig"),
                         "Test", self.lua.globals().ns)
        self.lua.execute('''
          function fixedFixture(item,perCraft)
            schema(item)
            ns.ProfRecipes={alchemy={rows={{101,20,1,'','','',1,20,30,40,false,{{item,perCraft}}}}}}
            ns.ProfLeveling={alchemy={}}
            ns.EnsureProfRecipes=function()return ns.ProfRecipes end
            Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)
              return id==item and 10 or nil
            end}}}
          end
        ''')

    def formula_routes(self):
        self.economy()
        self.lua.execute('''
          function formulaScenario(item)
            schema(item,{stock=1,cost_copper=1},1)
            local a={profession='alchemy',spell=101,item=20,count=1,learn=1,yellow=10,
              green=10,grey=10,mats={{11,1}},formula=item,cooldown=false,catalogue=true}
            local b={profession='alchemy',spell=102,item=21,count=1,learn=1,yellow=10,
              green=10,grey=10,mats={{12,1}},cooldown=false}
            return {recipes={a,b},professions={alchemy={cur=1,max=75}},known={['alchemy:102']=true},
              prices={[11]=1,[12]=100,[item]=5},formulaOffers={[item]=ns.ProfItemPrices.GetFormulaOffers(item)}}
          end
        ''')

    def test_verified_supply_quotes_are_used_without_legacy_audit_attributes(self):
        self.lua.execute('''
          local raw=schema(999100)
          local offers=ns.ProfItemPrices.GetOffers(999100)
          assert(#offers==1 and offers[1].price==37 and offers[1].quantity==4)
          local q=offers[1]
          assert(q.npcID==nil and q.npcName==nil and q.faction==nil and q.bundleSize==4 and q.unit==37/4)
          assert(q.source=='client_base_bundle' and q.priceSource=='client_base_bundle' and q.priceBasis=='Data_ProfMaterialSupply')
          assert(q.reference and not q.estimated and q.priceVerified==nil and q.verifiedAt==nil)
          assert(ns.ProfItemPrices.GetPrice(999100)==37/4)
          assert(raw.price==nil and raw.unit==nil and raw.npcID==nil and raw.verifiedAt==nil)
          local suppliers=ns.ProfItemPrices.GetSuppliers(999100)
          assert(#suppliers==1 and suppliers[1].unlimited and suppliers[1].npcID==nil)
        ''')

    def test_material_root_price_never_proves_supply_and_does_not_create_formula_seller(self):
        self.lua.execute('''
          for _,id in ipairs({2589,2840,999140})do
            ns.ProfItems[id]={item_id=id,cost_copper=20,VendorStackCount=5}
            assert(#ns.ProfItemPrices.GetOffers(id)==0)
            assert(#ns.ProfItemPrices.GetSuppliers(id)==0)
            assert(ns.ProfItemPrices.GetPrice(id)==nil)
            assert(#ns.ProfItemPrices.GetFormulaOffers(id)==0)
          end
        ''')

    def test_material_evidence_is_independent_from_formula_npc_rows(self):
        self.lua.execute('''
          local raw=schema(999141,{side='h',stock=1,cost_copper=1})
          local supply=material(999141,{price=80,quantity=4})
          for _,stock in ipairs({0,1,2,-1})do
            raw.stock=stock;raw.currency_kind='item';raw.currency_id=123;raw.currency_amount=9
            local q=ns.ProfItemPrices.GetOffers(999141,{faction='A'})[1]
            assert(q and q.price==80 and q.quantity==4 and q.npcID==nil)
            assert(#ns.ProfItemPrices.GetFormulaOffers(999141,{faction='A'})==0)
          end
          ns.ProfItems[999141]=nil
          assert(ns.ProfItemPrices.GetPrice(999141)==20)
          supply.stockState='limited'
          assert(ns.ProfItemPrices.GetPrice(999141)==nil)
        ''')

    def test_invalid_supply_amounts_bundles_and_exchange_fields_never_become_quotes(self):
        self.lua.execute('''
          schema(999142)
          local supply=ns.ProfMaterialSupply[999142].offers[7]
          for _,value in ipairs({false,-1,1.5,math.huge,'37',0/0})do
            supply.price=value;assert(#ns.ProfItemPrices.GetOffers(999142)==0)
          end
          supply.price=nil;assert(#ns.ProfItemPrices.GetOffers(999142)==0)
          supply.price=37
          for _,value in ipairs({false,0,-1,1.5,math.huge,'4',0/0})do
            supply.quantity=value;assert(#ns.ProfItemPrices.GetOffers(999142)==0)
          end
          supply.quantity=nil;assert(#ns.ProfItemPrices.GetOffers(999142)==0)
          supply.quantity=4
          for _,field in ipairs({'currency_kind','currency_id','currency_amount'})do
            supply[field]=0;assert(#ns.ProfItemPrices.GetOffers(999142)==0);supply[field]=nil
          end
          supply.price=0
          supply.currency_kind='  ';supply.currency_id='';supply.currency_amount='  '
          assert(ns.ProfItemPrices.GetPrice(999142)==0)
        ''')

    def test_legacy_catalogue_amounts_and_runtime_caches_cannot_supply_a_price(self):
        self.lua.execute('''
          schema(999101)
          ns.ProfVendorOffers={[999101]={{npcID=7,price=1,quantity=1,unlimited=true}}}
          ns.ProfFormulaOffers={[999101]={{npcID=7,price=1,quantity=1,unlimited=true}}}
          db.profVendorOffers={[999101]={old={price=2,quantity=1,npcID=7,unlimited=true}}}
          Auctionator={API={v1={GetVendorPriceByItemID=function()error('merchant cache read')end}}}
          assert(ns.ProfItemPrices.GetPrice(999101)==37/4)
          ns.ProfMaterialSupply[999101]=nil
          assert(ns.ProfVendorOffers[999101][1].price==1 and #ns.ProfItemPrices.GetOffers(999101)==0)
          assert(ns.ProfItemPrices.GetPrice(999101)==nil)
        ''')

    def test_dynamic_supply_amount_and_bundle_changes_are_not_hidden_by_price_cache(self):
        self.lua.execute('''
          local raw=schema(999102)
          assert(ns.ProfItemPrices.GetPrice(999102)==37/4)
          local supply=ns.ProfMaterialSupply[999102].offers[7]
          supply.price=60;supply.quantity=3
          assert(ns.ProfItemPrices.GetPrice(999102)==20)
          assert(raw.cost_copper==37 and raw.stock==-1)
        ''')

    def test_formula_display_preserves_exchange_and_copper_without_authorizing_procurement(self):
        self.lua.execute('''
          local raw=schema(999130,{currency_kind=' item ',currency_id=220775,currency_amount=2})
          local display=ns.ProfItemPrices.GetFormulaDisplayOffers(999130)
          assert(#display==1)
          local d=display[1]
          assert(d.npcID==7 and d.costCopper==37 and d.costText=='37c')
          assert(d.currencyKind=='item' and d.currencyID==220775 and d.currencyAmount==2)
          assert(d.quantity==4 and d.bundleSize==4 and d.hasExtendedCost and d.displayOnly)
          assert(d.price==nil and d.priceUsable==nil and d.purchasable==nil)
          assert(#ns.ProfItemPrices.GetOffers(999130)==0)
          assert(#ns.ProfItemPrices.GetSuppliers(999130)==0)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999130)==0)
          raw.currency_kind='currency';raw.currency_id=3402;raw.currency_amount=45
          d=ns.ProfItemPrices.GetFormulaDisplayOffers(999130)[1]
          assert(d.currencyKind=='currency' and d.currencyID==3402 and d.currencyAmount==45)
        ''')

    def test_formula_display_joins_localized_catalogue_and_raw_sellers_without_mutation(self):
        self.lua.execute('''
          schema(999131)
          ns.ProfItems[999131].offers[8]={npc_id=8,name_en='Raw Only',zone_id=44,
            currency_kind='currency',currency_id=3402,currency_amount=45}
          ns.ProfVendors[7]={12,1429,10,20}
          local source={vendors={{id=7,name='本地商人',zone='本地区域'},
            {id=9,name='目录商人',zone='目录区域',side='a',cost='1g',price=1,stock=-1}}}
          GetLocale=function()return 'zhCN' end
          ns.L=setmetatable({['Raw Only']='原始商人'}, {__index=function(_,key)return key end})
          local list=ns.ProfItemPrices.GetFormulaDisplayOffers(999131,nil,source)
          assert(#list==3 and list[1].npcID==7 and list[2].npcID==9 and list[3].npcID==8)
          assert(list[1].name=='本地商人' and list[1].npcName=='本地商人')
          assert(list[1].zone=='本地区域' and list[1].areaID==12 and list[1].faction=='N')
          assert(list[1].mapID==1429 and list[1].x==10 and list[1].y==20)
          assert(list[2].catalogueOnly and list[2].faction=='A' and list[2].costCopper==nil)
          assert(list[2].costText==nil and list[2].price==nil)
          assert(list[3].name=='原始商人' and list[3].areaID==44 and list[3].faction==nil)
          list[1].name='changed';list[1].costCopper=999;list[2].zone='changed'
          local again=ns.ProfItemPrices.GetFormulaDisplayOffers(999131,nil,source)
          assert(again[1].name=='本地商人' and again[1].costCopper==37)
          assert(again[2].zone=='目录区域' and source.vendors[1].name=='本地商人')
          assert(ns.ProfItems[999131].offers[7].cost_copper==37 and ns.ProfVendors[7][3]==10)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999131,nil,source)==1)
          assert(test.dbReads==0 and test.merchantReads==0)
        ''')

    def test_formula_display_raw_faction_filters_catalogue_duplicates_and_explicit_access(self):
        self.lua.execute('''
          local raw=schema(999132,{side='h'})
          local source={vendors={{id=7,name='Catalogue',side='a'},
            {id=8,name='Alliance',side='a'},{id=9,name='Neutral',side='n'}}}
          local list=ns.ProfItemPrices.GetFormulaDisplayOffers(999132,{faction='Alliance'},source)
          assert(#list==2 and list[1].npcID==8 and list[2].npcID==9)
          list=ns.ProfItemPrices.GetFormulaDisplayOffers(999132,
            {faction='Horde',npcAccess={[9]=false}},source)
          assert(#list==1 and list[1].npcID==7 and list[1].faction=='H')
          assert(raw.side=='h' and source.vendors[1].side=='a')
          UnitFactionGroup=nil
          assert(#ns.ProfItemPrices.GetFormulaDisplayOffers(999132,nil,source)==3)
        ''')

    def test_formula_display_retains_unknown_cost_and_unknown_faction(self):
        self.lua.execute('''
          local raw=schema(999133,{side='unknown'})
          raw.cost_copper=nil;raw.cost_text='3 tokens';raw.currency_id=0
          ns.ProfItems[999133].VendorStackCount=nil
          local d=ns.ProfItemPrices.GetFormulaDisplayOffers(999133)[1]
          assert(d.faction==nil and d.costCopper==nil and d.quantity==nil)
          assert(d.costText=='3 tokens' and d.hasExtendedCost and d.currencyID==nil)
          raw.currency_id=nil;raw.cost_copper=0
          d=ns.ProfItemPrices.GetFormulaDisplayOffers(999133)[1]
          assert(d.costCopper==0 and d.hasExtendedCost==nil)
          raw.cost_copper=-1
          assert(ns.ProfItemPrices.GetFormulaDisplayOffers(999133)[1].costCopper==nil)
        ''')

    def test_formula_display_normalizes_ids_and_keeps_catalogue_only_costs_unknown(self):
        self.lua.execute('''
          local source={vendors={{id='12',name='Catalogue',zone='Zone',side='a',
            cost_copper=100,currency_kind='item',currency_id=22,currency_amount=3},
            {id=0,name='Invalid'},{id=12,name='Duplicate'}}}
          ns.ProfVendors[12]={44,1433,5,6}
          local d=ns.ProfItemPrices.GetFormulaDisplayOffers('999134',nil,source)
          assert(#d==1 and d[1].npcID==12 and d[1].itemID==999134 and d[1].areaID==44)
          assert(d[1].catalogueOnly and d[1].costCopper==nil and d[1].currencyID==nil)
          assert(d[1].currencyKind==nil and d[1].quantity==nil and d[1].mapID==1433)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999134,nil,source)==0)
          assert(#ns.ProfItemPrices.GetFormulaDisplayOffers(nil,nil,source)==0)
          assert(#ns.ProfItemPrices.GetFormulaDisplayOffers(-1,nil,source)==0)
          schema(999134)
          ns.ProfVendors[7]={44,1433,5,6};ns.AreaMap={[12]=1429}
          d=ns.ProfItemPrices.GetFormulaDisplayOffers(999134)[1]
          assert(d.areaID==12 and d.mapID==1429 and d.x==nil and d.y==nil)
        ''')

    def test_formula_display_retains_known_catalogue_sellers_without_npc_ids(self):
        self.lua.execute('''
          local source={vendors={{name='已知商人',zone='已知地区'},
            {name='部落商人',zone='已知地区',side='h'},
            {zone='另一区域',side='a'},{side='a'},
            {id=8,name='编号商人',zone='编号地区',side='a'}}}
          local rows=ns.ProfItemPrices.GetFormulaDisplayOffers(999135,{faction='A'},source)
          assert(#rows==3 and rows[1].name=='已知商人' and rows[1].zone=='已知地区')
          assert(rows[1].npcID==nil and rows[1].faction==nil and rows[1].catalogueOnly)
          assert(rows[1].costCopper==nil and rows[1].price==nil and rows[1].mapID==nil)
          assert(rows[1].x==nil and rows[1].y==nil and rows[2].zone=='另一区域')
          assert(rows[2].npcID==nil and rows[2].faction=='A' and type(rows[2].name)=='string')
          assert(rows[3].npcID==8 and rows[3].name=='编号商人')
          assert(#ns.ProfItemPrices.GetFormulaOffers(999135,nil,source)==0)
          assert(#ns.ProfItemPrices.GetFormulaDisplayOffers(nil,nil,source)==0)
          GetLocale=function()return 'zhCN' end
          rows=ns.ProfItemPrices.GetFormulaDisplayOffers(999135,{faction='H'},source)
          assert(#rows==2 and rows[1].name=='已知商人' and rows[2].name=='部落商人')
          assert(source.vendors[1].id==nil and source.vendors[1].name=='已知商人')
        ''')

    def test_each_exchange_field_even_zero_rejects_gold_quotes(self):
        self.lua.execute('''
          for _,value in ipairs({{currency_kind='currency'},{currency_kind='item'},
            {currency_id=0},{currency_amount=0},{currency_kind='0'},
            {currency_id=77,currency_amount=3}}) do
            schema(999103,value)
            assert(#ns.ProfItemPrices.GetOffers(999103)==0)
            assert(#ns.ProfItemPrices.GetSuppliers(999103)==0)
            assert(#ns.ProfItemPrices.GetFormulaOffers(999103)==0)
          end
          schema(999103,{currency_kind=' \t ',currency_id='',currency_amount=' \t '})
          assert(#ns.ProfItemPrices.GetOffers(999103)==1,'blank exchange fields became currency costs')
        ''')

    def test_page_text_does_not_become_copper_and_missing_quantity_is_not_assumed_one(self):
        self.lua.execute('''
          local raw=schema(999104)
          raw.cost_copper=nil;raw.cost_text='3 tokens or 99 points'
          ns.ProfItems[999104].cost_copper=nil;ns.ProfItems[999104].cost_text=raw.cost_text
          ns.ProfMaterialSupply[999104].offers[7].price=nil
          assert(#ns.ProfItemPrices.GetOffers(999104)==0)
          local f=ns.ProfItemPrices.GetFormulaOffers(999104)
          assert(#f==1 and f[1].price==nil and not f[1].priceUsable)
          raw.cost_copper=37;ns.ProfItems[999104].cost_copper=37;ns.ProfItems[999104].VendorStackCount=nil
          ns.ProfMaterialSupply[999104].offers[7].price=37;ns.ProfMaterialSupply[999104].offers[7].quantity=nil
          assert(#ns.ProfItemPrices.GetOffers(999104)==0)
          f=ns.ProfItemPrices.GetFormulaOffers(999104)
          assert(#f==1 and f[1].price==nil and not f[1].priceUsable)
        ''')

    def test_independent_material_supply_uses_its_own_faction_and_access(self):
        self.lua.execute('''
          local raw=schema(999105,{side='a'})
          assert(#ns.ProfItemPrices.GetOffers(999105,{faction='Horde'})==1)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999105,{faction='H'})==0)
          assert(#ns.ProfItemPrices.GetOffers(999105,{faction='Alliance'})==1)
          assert(#ns.ProfItemPrices.GetOffers(999105,{npcAccess={[7]=false},faction='A'})==0)
          raw.side='n'
          assert(#ns.ProfItemPrices.GetOffers(999105,{faction='H'})==1)
          raw.side=nil
          assert(#ns.ProfItemPrices.GetOffers(999105,{npcAccess={[7]=false}})==0)
          assert(#ns.ProfItemPrices.GetSuppliers(999105,{npcAccess={[7]=false}})==0)
          assert(#ns.ProfItemPrices.GetFormulaOffers(999105,{npcAccess={[7]=false}})==0)
        ''')

    def test_limited_stock_is_formula_refresh_cap_not_current_inventory(self):
        self.lua.execute('''
          local raw=schema(999106,{stock=2,price_source='wowhead'})
          assert(#ns.ProfItemPrices.GetOffers(999106)==1)
          assert(#ns.ProfItemPrices.GetSuppliers(999106)==1)
          local f=ns.ProfItemPrices.GetFormulaOffers(999106)
          assert(#f==1 and f[1].price==37 and f[1].quantity==4 and f[1].priceUsable)
          assert(f[1].limited and not f[1].unlimited and f[1].maxStock==2)
          assert(f[1].stock==nil and f[1].stockStatus=='limited')
          assert(f[1].source=='wowhead' and raw.stock==2)
          raw.stock=nil
          f=ns.ProfItemPrices.GetFormulaOffers(999106)
          assert(#f==1 and f[1].stockUnknown and not f[1].unlimited)
          assert(#ns.ProfItemPrices.GetOffers(999106)==1)
        ''')

    def test_formula_names_use_matching_localized_source_without_supplier_authority(self):
        self.lua.execute('''
          local raw=schema(999125,{stock=1},1)
          local source={vendors={{id=7,name='配方商人',price=0,stock=-1,available=false},
            {id=999,name='旧目录商人',price=0,stock=-1}}}
          local offers=ns.ProfItemPrices.GetFormulaOffers(999125,{},source)
          assert(#offers==1 and offers[1].npcID==7 and offers[1].name=='配方商人')
          assert(offers[1].npcName=='配方商人' and offers[1].price==37 and offers[1].maxStock==1)
          assert(offers[1].available and not offers[1].unlimited)
          assert(raw.name_en=='Schema Seller' and source.vendors[1].price==0)
          local plain=ns.ProfItemPrices.GetFormulaOffers(999125,{})
          assert(plain[1].name=='Schema Seller','localized labels contaminated later quotes')
        ''')

    def test_npc_reputation_affiliation_is_localized_without_becoming_player_side(self):
        self.lua.execute('''
          local raw=schema(999151)
          raw.side=nil
          ns.ProfVendorFactions={[7]={factionID=93,
            names={enUS='Magram Clan Centaur',zhCN='已保存的所属阵营'}}}
          GetLocale=function()return 'zhCN' end
          C_Reputation={GetFactionDataByID=function()error('not ready')end}
          local p=ns.ProfItemPrices
          local offer=p.GetFormulaDisplayOffers(999151,{faction='A'})[1]
          assert(offer.npcFactionID==93 and offer.npcFactionName=='已保存的所属阵营')
          assert(offer.faction==nil and raw.side==nil and offer.costCopper==37)
          GetFactionInfoByID=function(id)assert(id==93);return '旧客户端阵营名' end
          assert(p.GetFormulaDisplayOffers(999151,{faction='H'})[1].npcFactionName=='旧客户端阵营名')
          C_Reputation.GetFactionDataByID=function(id)
            assert(id==93);return {name='新客户端阵营名'}
          end
          local quote=p.GetFormulaOffers(999151,{faction='A'})[1]
          assert(quote.npcFactionName=='新客户端阵营名' and quote.faction==nil and quote.price==37)
          assert(ns.ProfVendorFactions[7].names.zhCN=='已保存的所属阵营')
          raw.side='h'
          assert(#p.GetFormulaDisplayOffers(999151,{faction='A'})==0)
          assert(#p.GetFormulaOffers(999151,{faction='A'})==0)
          assert(#p.GetFormulaDisplayOffers(999151,{faction='H'})==1)
        ''')

    def test_missing_or_unlocalized_npc_affiliation_remains_independent_of_access(self):
        self.lua.execute('''
          local raw=schema(999152)
          GetLocale=function()return 'zhTW' end
          ns.ProfVendorFactions={[7]={names={enUS='Explicit NPC Affiliation'}}}
          C_Reputation=nil;GetFactionInfoByID=nil
          local p=ns.ProfItemPrices
          local offer=p.GetFormulaDisplayOffers(999152)[1]
          assert(offer.npcFactionID==nil and offer.npcFactionName=='Explicit NPC Affiliation')
          assert(offer.faction=='N' and raw.side=='n')
          ns.ProfVendorFactions={}
          offer=p.GetFormulaDisplayOffers(999152)[1]
          assert(offer.npcFactionName==nil and offer.faction=='N')
          ns.ProfVendorFactions=nil
          assert(p.GetNPCFaction(7)==nil)
        ''')

    def test_known_source_names_survive_missing_translation_and_old_number_placeholders(self):
        self.lua.execute('''
          local raw=schema(999150)
          GetLocale=function()return 'zhCN' end
          ns.L=setmetatable({}, {__index=function(_,key)return key end})
          local old={vendors={{id=7,name='商人 NPC #7'}}}
          local p=ns.ProfItemPrices
          local display=p.GetFormulaDisplayOffers(999150,nil,old)[1]
          local quote=p.GetFormulaOffers(999150,nil,old)[1]
          assert(display.name=='Schema Seller' and display.npcNameUntranslated)
          assert(quote.name=='Schema Seller' and quote.npcNameUntranslated)
          assert(display.npcNameCanonical==raw.name_en and quote.price==37)
          ns.L['Schema Seller']='已加载的商人名称'
          assert(p.GetFormulaDisplayOffers(999150)[1].name=='已加载的商人名称')
          assert(not p.GetFormulaOffers(999150)[1].npcNameUntranslated)
          raw.name_en=nil
          display=p.GetFormulaDisplayOffers(999150,nil,old)[1]
          assert(display.name=='商人 NPC #7' and display.npcNameUntranslated)
          assert(old.vendors[1].name=='商人 NPC #7' and raw.cost_copper==37)
          raw.name_en='   '
          assert(p.GetFormulaOffers(999150)[1].name=='商人 NPC #7')
        ''')

    def test_screenshot_merchants_keep_their_real_names_in_all_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                lua=runtime();ns=lua.globals().ns
                lua.globals().testLocale=locale
                lua.execute('GetLocale=function()return testLocale end')
                for name in ('zhCN',locale):
                    lua.execute((ROOT/'Locales'/f'{name}.lua').read_text(encoding='utf-8-sig'),'Test',ns)
                lua.execute((ROOT/'Core/Data/Data_ProfItems.lua').read_text(encoding='utf-8-sig'),'Test',ns)
                lua.execute('''
                  local p=ns.ProfItemPrices
                  local names={[253139]='Gorhak',[253140]='Molkar',[266901]='Pexmit'}
                  local centaur=p.GetFormulaDisplayOffers(250979,{faction='A'})
                  assert(#centaur==2)
                  for _,offer in ipairs(centaur)do
                    assert(offer.name==names[offer.npcID] and offer.npcNameCanonical==offer.name)
                    assert(offer.currencyKind=='item' and offer.currencyID==254432)
                    assert(offer.currencyAmount==(offer.npcID==253139 and 15 or 60))
                    assert(offer.faction==nil,'missing faction was invented as neutral')
                  end
                  local portal=p.GetFormulaDisplayOffers(251468,{faction='H'})
                  assert(#portal==1 and portal[1].npcID==266901 and portal[1].name=='Pexmit')
                  assert(portal[1].costCopper==100000 and portal[1].faction==nil)
                  local quote=p.GetFormulaOffers(251468,{faction='A'})[1]
                  assert(quote.name=='Pexmit' and quote.price==100000)
                ''')

    def test_actual_supplier_names_use_verified_chinese_or_the_preserved_source_name(self):
        audit=json.loads((ROOT/'tests/data/prof-vendor-localization.json').read_text(encoding='utf-8'))
        records={row['npcID']:row for row in audit['vendors']}
        self.assertEqual(len(records),len(audit['vendors']))
        for row in records.values():
            for locale in ('zhCN','zhTW'):
                if row.get(locale+'Status')=='not_verified':
                    self.assertIsNone(row.get(locale))
                    self.assertTrue(row.get(locale+'Reason'))
                    self.assertTrue(row.get(locale+'Source'))
                    self.assertTrue(row.get('enUSSource'))
                    proof=row['enUSEvidence']
                    self.assertEqual(proof['kind'],'cached_sold_by_listview_json')
                    self.assertGreater(proof['itemID'],0)
                    self.assertTrue(proof['file'])
                    self.assertRegex(proof['sha256'],r'^[0-9a-f]{64}$')
        for locale in ('zhCN','zhTW'):
            with self.subTest(locale=locale):
                lua=runtime();ns=lua.globals().ns
                lua.globals().testLocale=locale
                lua.globals().evidence=lua.table_from(records,recursive=True)
                lua.execute('GetLocale=function()return testLocale end')
                for name in ('zhCN',locale):
                    lua.execute((ROOT/'Locales'/f'{name}.lua').read_text(encoding='utf-8-sig'),'Test',ns)
                lua.execute((ROOT/'Core/Data/Data_ProfItems.lua').read_text(encoding='utf-8-sig'),'Test',ns)
                lua.execute('''
                  local seen={}
                  for id,item in pairs(ns.ProfItems)do
                    for npc,raw in pairs(item.offers or {})do
                      local proof=assert(evidence[npc],'supplier NPC is missing localization audit evidence')
                      assert(proof.enUS==raw.name_en,'canonical supplier identity drifted')
                      local faction=raw.side=='h' and 'H' or 'A'
                      for _,offer in ipairs(ns.ProfItemPrices.GetFormulaOffers(id,{faction=faction}))do
                        if offer.npcID==npc then
                          assert(offer.npcNameCanonical==raw.name_en,'original name was lost')
                          if proof[testLocale]then
                            assert(offer.name==proof[testLocale],'verified name differs from quotation')
                            assert(not offer.npcNameUntranslated)
                          else
                            local status=proof[testLocale..'Status']
                            assert(status=='unavailable' or status=='not_verified')
                            assert(offer.name==raw.name_en and offer.npcNameUntranslated,
                              'a known canonical name was replaced with an NPC number')
                          end
                          seen[npc]=true
                        end
                      end
                    end
                  end
                  assert(next(seen),'no actual supplier names were exercised')
                ''')

    def test_returned_quotes_and_suppliers_do_not_mutate_raw_rows(self):
        self.lua.execute('''
          local raw=schema(999107)
          local offer=ns.ProfItemPrices.GetOffers(999107)[1]
          offer.price=1000;offer.npcID=888
          local supplier=ns.ProfItemPrices.GetSuppliers(999107)[1]
          supplier.quantity=100;supplier.npcID=999
          local formula=ns.ProfItemPrices.GetFormulaOffers(999107)[1]
          formula.price=900;formula.maxStock=800
          assert(raw.cost_copper==37 and raw.npc_id==7 and raw.stock==-1)
          assert(ns.ProfItems[999107].VendorStackCount==4)
          assert(ns.ProfItemPrices.GetPrice(999107)==37/4)
        ''')

    def test_old_requirement_tables_are_ignored_even_when_cyclic(self):
        self.lua.execute('''
          schema(999112)
          local requirements={level=999,unknown=true};requirements.self=requirements
          ns.ProfVendorOffers={[999112]={{npcID=7,requirements=requirements,available=false}}}
          ns.ProfFormulaOffers={[999112]={{npcID=7,requirements=requirements,available=false}}}
          local q=ns.ProfItemPrices.GetOffers(999112,{level=1})[1]
          assert(q and q.price==37 and q.requirements==nil and q.available)
          assert(requirements.level==999 and requirements.self==requirements)
        ''')

    def test_new_area_does_not_reuse_old_map_coordinates(self):
        self.lua.execute('''
          local raw=schema(999113)
          raw.zone_id=12;ns.ProfVendors[7]={1,100,10,20};ns.AreaMap={[12]=1429}
          local q=ns.ProfItemPrices.GetFormulaOffers(999113)[1]
          assert(q.areaID==12 and q.mapID==1429 and q.x==nil and q.y==nil)
          assert(ns.ProfVendors[7][1]==1 and ns.ProfVendors[7][2]==100 and ns.ProfVendors[7][3]==10)
          ns.AreaMap=nil
          q=ns.ProfItemPrices.GetFormulaOffers(999113)[1]
          assert(q.areaID==12 and q.mapID==nil and q.x==nil and q.y==nil)
        ''')

    def test_old_formula_sources_and_conditions_have_no_effect_on_new_rows(self):
        self.economy()
        self.lua.execute('''
          schema(999114)
          ns.ProfFormulaOffers={[999114]={{itemID=999114,npcID=7,requirements={level=999},price=1}}}
          local source={vendors={{id=777,name='Old source',requirements={level=999},price=1}},
            quests={{id=12}},drops={{id=8}},skill=20}
          local offers=ns.ProfItemPrices.GetFormulaOffers(999114,{level=1},source)
          assert(#offers==1 and offers[1].npcID==7 and offers[1].price==37 and offers[1].priceUsable)
          local recipe={profession='alchemy',spell=101,key='alchemy:101',formula=999114,source=source}
          local f=ns.ProfEconomy.FormulaFor(recipe,{known={},prices={}})
          assert(#f.sources.vendors==1 and f.sources.vendors[1].id==7)
          assert(f.sources.vendors[1].id~=777 and f.sources.quests[1].id==12)
          assert(f.sources.drops[1].id==8 and f.sources.skill==20)
          assert(recipe.source==source and #source.vendors==1 and source.vendors[1].id==777)
          ns.ProfItems[999114]=nil
          assert(#ns.ProfItemPrices.GetFormulaOffers(999114,{level=999},source)==0)
          f=ns.ProfEconomy.FormulaFor(recipe,{known={},prices={}})
          assert(#f.sources.vendors==0 and f.unpriced and not f.usable)
          assert(f.sources.quests[1].id==12 and f.sources.drops[1].id==8 and #source.vendors==1)
          local questSource={questOnly=true,quests={{id=12}},vendors={{id=777,name='Old source'}}}
          recipe.source=questSource
          f=ns.ProfEconomy.FormulaFor(recipe,{known={},prices={}})
          assert(f.questOnly and #f.sources.vendors==0 and questSource.vendors[1].id==777)
        ''')

    def test_end_to_end_procurement_rounds_whole_packs_and_ignores_initial_inventory(self):
        self.economy()
        self.lua.execute('''
          schema(999108)
          local s={recipes={},professions={},known={},prices={[999108]=20},
            inventory={[999108]=999},vendorItems={[999108]=true},
            vendorSuppliers={[999108]=ns.ProfItemPrices.GetSuppliers(999108)},
            offers={[999108]=ns.ProfItemPrices.GetOffers(999108)}}
          local r=ns.ProfRouteSolver.Procure(s,999108,6)
          assert(r.feasible and r.costComplete and r.total==74 and r.vendorTotal==74 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].count==8)
          assert(r.mats[1].bundleSize==4 and r.mats[1].npcID==nil)
          assert(r.mats[1].quoteSource=='client_base_bundle')
          assert(r.inventory[999108]==2,'bag inventory was subtracted or retained')
          assert(test.merchantReads==0 and test.dbReads==0)
        ''')

    def test_capture_keeps_auction_quote_when_known_npc_has_no_csv_cost(self):
        self.economy()
        self.lua.execute('''
          local raw=schema(999109);raw.cost_copper=nil;raw.cost_text=nil
          ns.ProfItems[999109].cost_copper=nil;ns.ProfItems[999109].cost_text=nil
          ns.ProfMaterialSupply[999109].offers[7].price=nil
          ns.ProfEconomy.Professions=function()return {alchemy={cur=1,max=75,primary=true}}end
          ns.ProfRecipes={alchemy={rows={{101,20,1,'','','',1,20,30,40,false,{{999109,1}}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          ns.ProfRouteAuto={AHPriceOf=function()return 9 end}
          local s=ns.ProfEconomy.Capture('alchemy',{})
          assert(#s.offers[999109]==0 and s.prices[999109]==9)
          local r=ns.ProfRouteSolver.Procure(s,999109,3)
          assert(r.feasible and r.costComplete and r.total==27 and r.ahTotal==27 and r.vendorTotal==0)
        ''')

    def test_exchange_rows_cannot_give_free_gold_purchase_but_auction_remains_usable(self):
        self.economy()
        self.lua.execute('''
          schema(999110,{cost_copper=0,currency_kind='item',currency_id=77,currency_amount=3})
          local s={recipes={},professions={},known={},prices={[999110]=9},
            vendorSuppliers={[999110]=ns.ProfItemPrices.GetSuppliers(999110)},
            offers={[999110]=ns.ProfItemPrices.GetOffers(999110)}}
          local r=ns.ProfRouteSolver.Procure(s,999110,3)
          assert(r.feasible and r.costComplete and r.total==27 and r.ahTotal==27 and r.vendorTotal==0)
        ''')

    def test_capture_can_choose_auction_when_it_beats_a_valid_whole_npc_pack(self):
        self.economy()
        self.lua.execute('''
          schema(999111)
          ns.ProfEconomy.Professions=function()return {alchemy={cur=1,max=75,primary=true}}end
          ns.ProfRecipes={alchemy={rows={{101,20,1,'','','',1,20,30,40,false,{{999111,1}}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          ns.ProfRouteAuto={AHPriceOf=function()return 9 end}
          local s=ns.ProfEconomy.Capture('alchemy',{})
          assert(#s.offers[999111]==1 and s.prices[999111]==9)
          local r=ns.ProfRouteSolver.Procure(s,999111,3)
          assert(r.feasible and r.costComplete and r.total==27 and r.ahTotal==27 and r.vendorTotal==0)
          assert(#r.mats==1 and r.mats[1].source=='ah' and r.mats[1].count==3)
        ''')

    def test_fixed_route_mixes_npc_whole_pack_and_auction_remainder(self):
        self.fixed_routes()
        self.lua.execute('''
          fixedFixture(999116,5)
          local steps={{1,2,101,1}}
          local r=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(r.total==47 and r.matTotal==47 and r.vendorTotal==37 and r.ahTotal==10)
          assert(r.completeCost and r.costComplete and #r.mats==2 and steps[1].cost==47)
          local count,total={},0
          for _,m in ipairs(r.mats)do
            count[m.source]=m.count;total=total+m.cost
            if m.source=='vendor' then assert(m.npcID==nil and m.cost==37 and m.bundleSize==4 and m.need==4)
            elseif m.source=='ah' then assert(m.cost==10 and m.need==1) end
          end
          assert(count.vendor==4 and count.ah==1 and total==47)
          local s={recipes={},professions={},known={},prices={[999116]=10},
            offers={[999116]=ns.ProfItemPrices.GetOffers(999116)}}
          local exact=ns.ProfRouteSolver.Procure(s,999116,5)
          assert(exact.total==r.total and exact.vendorTotal==r.vendorTotal and exact.ahTotal==r.ahTotal)
        ''')

    def test_fixed_route_mixed_purchase_reuses_pack_leftovers_across_steps_once(self):
        self.fixed_routes()
        self.lua.execute('''
          fixedFixture(999117,1)
          local steps={{1,3,101,2},{3,6,101,3}}
          local r=ns.ProfRouteAuto.SummarizeSteps(steps,'alchemy')
          assert(r.total==47 and r.vendorTotal==37 and r.ahTotal==10 and #r.mats==2)
          assert(steps[1].cost==37 and steps[2].cost==10,'pack cash was not shared across the execution steps')
          assert(steps[1].cost+steps[2].cost==r.total)
          assert(steps[1][4]==2 and steps[2][4]==3,'purchase consolidation changed craft counts')
          local shorter={{1,3,101,2},{3,5,101,2}}
          r=ns.ProfRouteAuto.SummarizeSteps(shorter,'alchemy')
          assert(r.total==37 and r.vendorTotal==37 and r.ahTotal==0 and #r.mats==1)
          assert(r.mats[1].source=='vendor' and r.mats[1].count==4)
          assert(shorter[1].cost==37 and shorter[2].cost==0,'one shared pack was charged twice')
          assert(shorter[1].cost+shorter[2].cost==r.total)
        ''')

    def test_available_auction_formula_is_not_hidden_by_cheaper_limited_npc_reference(self):
        self.formula_routes()
        self.lua.execute('''
          local s=formulaScenario(999120)
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(not j.error and r.feasible and r.costComplete and r.total==6)
          assert(r.ahTotal==6 and r.vendorTotal==0 and r.formulasTotal==5)
          assert(#r.steps==1 and r.steps[1][3]==101 and #r.formulas==1)
          assert(r.formulas[1].source=='ah' and r.formulas[1].vendorPrice==1)
          assert(r.formulas[1].limited and not r.formulas[1].availabilityUncertain)
          assert(#r.formulas[1].vendorOffers==1,'AH candidate discarded supplier display metadata')
        ''')

    def test_auction_formula_alternative_requires_available_tradable_auction_copy(self):
        self.formula_routes()
        self.lua.execute('''
          for _,restriction in ipairs({'empty','nonAuctionable'})do
            local s=formulaScenario(999121)
            if restriction=='empty' then s.auctionSupply={[999121]={quantity=0}}
            else s.nonAuctionable={[999121]=true} end
            local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
            assert(not j.error and r.feasible and r.costComplete and r.total==100,restriction)
            assert(#r.steps==1 and r.steps[1][3]==102 and #r.formulas==0,restriction)
          end
        ''')

    def test_limited_npc_formula_can_reserve_single_auction_copy_for_reagent(self):
        self.formula_routes()
        self.lua.execute('''
          local s=formulaScenario(999122)
          local raw=ns.ProfItems[999122].offers[7];raw.cost_copper=8
          ns.ProfItems[999122].cost_copper=nil;ns.ProfMaterialSupply[999122]=nil -- isolate finite AH material supply from the separate formula seller
          s.recipes={s.recipes[1]};s.recipes[1].mats={{999122,1},{11,1}}
          s.formulaOffers[999122]=ns.ProfItemPrices.GetFormulaOffers(999122)
          s.offers={[999122]=ns.ProfItemPrices.GetOffers(999122)}
          s.auctionSupply={[999122]={quantity=1}}
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2,allowLimitedFormulas=true})
          assert(not j.error and r.feasible and r.targetReached and r.total==14)
          assert(r.vendorTotal==8 and r.ahTotal==6 and r.formulasTotal==8)
          assert(#r.formulas==1 and r.formulas[1].source=='vendor' and r.formulas[1].availabilityUncertain)
          assert(not r.costComplete and not r.formulaComplete,'limited refresh stock became guaranteed inventory')
          local copies=0
          for _,m in ipairs(r.mats)do if m.id==999122 then copies=copies+m.count;assert(m.source=='ah') end end
          assert(copies==1,'finite auction copy was bought twice or consumed by the formula')
        ''')

    def test_actual_toc_loads_schema2_after_locale_data_before_runtime(self):
        entries = []
        for line in (ROOT / "DungeonsForever.toc").read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                entries.append(line)
        paths = [entry.split(" [", 1)[0].replace("\\", "/") for entry in entries]
        data_path = "Core/Data/Data_ProfItems.lua"
        self.assertEqual(paths.count(data_path), 1)
        overlays = [i for i, path in enumerate(paths) if path.startswith(("Core/Data/enUS/", "Core/Data/zhTW/"))]
        self.assertGreater(paths.index(data_path), max(overlays))
        self.assertLess(paths.index(data_path), paths.index("Core/ProfEconomy.lua"))
        self.assertLess(paths.index(data_path), paths.index("Core/ProfItemPrices.lua"))
        for locale in ("zhCN", "zhTW", "enUS"):
            with self.subTest(locale=locale):
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute(MOCKS)
                lua.globals().testLocale = locale
                lua.execute("GetLocale=function()return testLocale end; ns.L=setmetatable({}, {__index=function(_,key)return key end})")
                ns = lua.globals().ns
                for entry, path in zip(entries, paths):
                    if not path.startswith("Core/Data/") or "/Data_Prof" not in path:
                        continue
                    condition = re.search(r"\[AllowLoadTextLocale (\w+)\]", entry)
                    if condition and condition.group(1) != locale:
                        continue
                    lua.execute((ROOT / path).read_text(encoding="utf-8-sig"), "Test", ns)
                namespace_before = set(ns.keys())
                lua.execute((ROOT / "Core/ProfItemPrices.lua").read_text(encoding="utf-8-sig"), "Test", ns)
                self.assertEqual(set(ns.keys()) - namespace_before, {"ProfItemPrices"})
                lua.execute('''
                  assert(type(ns.ProfItemPrices)=='table')
                  for _,name in ipairs({'GetOffers','GetSuppliers','GetPrice','GetFormulaOffers'}) do
                    assert(type(ns.ProfItemPrices[name])=='function','missing quotation interface: '..name)
                  end
                  assert(ns.ProfItemsMeta.schemaVersion==2 and ns.ProfItems[5640].Name_zhCN)
                  local raw=ns.ProfItems[5640].offers[1685]
                  local offers=ns.ProfItemPrices.GetFormulaOffers(5640,{faction='A'})
                  local found
                  for _,offer in ipairs(offers)do if offer.npcID==1685 then found=offer end end
                  assert(found and found.price==raw.cost_copper and found.priceUsable)
                  assert(found.quantity==ns.ProfItems[5640].VendorStackCount and found.maxStock==raw.stock)
                  assert(found.source==raw.price_source and found.stock==nil and found.verifiedAt==nil)
                  assert(ns.ProfItemPrices.GetPrice(5640,{faction='A'})==nil,
                    'formula-only item root price invented unlimited material supply')
                ''')

    def test_actual_importer_only_updates_data_and_retains_runtime_provider(self):
        input_tools = str(ROOT / "df-data-pipeline/_temp")
        sys.path.insert(0, input_tools)
        self.addCleanup(lambda: sys.path.remove(input_tools))
        from fc_pipeline_paths import CSV_INPUTS
        from test_prof_items_pipeline import (
            NPC_FIELDS, PRICE_FIELDS, VENDOR_FIELDS, VENDORS_LUA, npc, price, vendor,
        )

        with tempfile.TemporaryDirectory(prefix="df-prof-runtime-preserved-") as directory:
            repository = Path(directory)
            package = repository / "df-data-pipeline"
            scripts = package / "_temp"
            output = package / "Core/Data"
            scripts.mkdir(parents=True)
            output.mkdir(parents=True)
            shutil.copyfile(ROOT / "df-data-pipeline/_temp/fc_prof_items.py",
                            scripts / "fc_prof_items.py")
            shutil.copyfile(ROOT / "df-data-pipeline/_temp/fc_pipeline_common.py",
                            scripts / "fc_pipeline_common.py")
            shutil.copyfile(ROOT / "df-data-pipeline/_temp/fc_pipeline_paths.py",
                            scripts / "fc_pipeline_paths.py")
            runtime_path = package / "Core/ProfItemPrices.lua"
            shutil.copyfile(ROOT / "Core/ProfItemPrices.lua", runtime_path)
            shutil.copyfile(ROOT / "DungeonsForever.toc", package / "DungeonsForever.toc")
            (package / "Core/Unrelated.lua").write_bytes(b"-- retain unrelated runtime code\r\n")
            vendors_lua = output / "Data_ProfVendors.lua"
            vendors_lua.write_text(VENDORS_LUA, encoding="utf-8")
            for relative, fields, rows in (
                (CSV_INPUTS["vendors_csv"].relative_to(ROOT), VENDOR_FIELDS, [vendor()]),
                (CSV_INPUTS["npcs_csv"].relative_to(ROOT), NPC_FIELDS, [npc()]),
                (CSV_INPUTS["prices_csv"].relative_to(ROOT), PRICE_FIELDS, [price()]),
            ):
                path = repository / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", encoding="utf-8-sig", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
            before = {path: path.read_bytes() for path in repository.rglob("*") if path.is_file()}
            result = subprocess.run(
                [sys.executable, "-B", str(scripts / "fc_prof_items.py")],
                cwd=directory, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
            items_lua = output / "Data_ProfItems.lua"
            merged_csv = scripts / "_fc/data/DataProfItems.csv"
            self.assertEqual({path for path in repository.rglob("*") if path.is_file()
                              and not path.is_relative_to(repository / '.implementation-backup')},
                             set(before) | {items_lua, merged_csv})
            for path, contents in before.items():
                if path != vendors_lua:
                    self.assertEqual(path.read_bytes(), contents, str(path.relative_to(repository)))
            self.assertNotEqual(vendors_lua.read_bytes(), before[vendors_lua])
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.execute(MOCKS)
            ns = lua.globals().ns
            lua.execute(items_lua.read_text(encoding="utf-8-sig"), "Test", ns)
            lua.execute(runtime_path.read_text(encoding="utf-8-sig"), "Test", ns)
            lua.execute("assert(ns.ProfItemPrices.GetPrice(100,{faction='A'})==nil)")


if __name__ == "__main__":
    unittest.main()
