"""Raw schema-2 item costs reach NPC quotes and full-purchase route totals."""
import csv
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_prof_vendor import LuaRuntime, MOCKS, ROOT, runtime


SCHEMA_FIXTURES = r'''
function schema(item, values, quantity)
    local raw={npc_id=7,name_en='Schema Seller',zone_id=12,side='n',stock=-1,
        cost_copper=37,cost_text='37c',price_source='client'}
    for key,value in pairs(values or {}) do raw[key]=value end
    ns.ProfItems[item]={item_id=item,VendorStackCount=quantity or 4,offers={[7]=raw}}
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

    def test_raw_schema2_prices_are_used_without_legacy_audit_attributes(self):
        self.lua.execute('''
          local raw=schema(999100)
          local offers=ns.ProfItemPrices.GetOffers(999100)
          assert(#offers==1 and offers[1].price==37 and offers[1].quantity==4)
          local q=offers[1]
          assert(q.npcID==7 and q.bundleSize==4 and q.unit==37/4)
          assert(q.source=='client' and q.priceSource=='client' and q.priceBasis=='Data_ProfItems')
          assert(q.reference and not q.estimated and q.priceVerified==nil and q.verifiedAt==nil)
          assert(ns.ProfItemPrices.GetPrice(999100)==37/4)
          assert(raw.price==nil and raw.unit==nil and raw.npcID==nil and raw.verifiedAt==nil)
          local suppliers=ns.ProfItemPrices.GetSuppliers(999100)
          assert(#suppliers==1 and suppliers[1].unlimited and suppliers[1].npcID==7)
        ''')

    def test_legacy_catalogue_amounts_and_runtime_caches_cannot_supply_a_price(self):
        self.lua.execute('''
          local raw=schema(999101)
          ns.ProfVendorOffers={[999101]={{npcID=7,price=1,quantity=1,unlimited=true}}}
          ns.ProfFormulaOffers={[999101]={{npcID=7,price=1,quantity=1,unlimited=true}}}
          db.profVendorOffers={[999101]={old={price=2,quantity=1,npcID=7,unlimited=true}}}
          Auctionator={API={v1={GetVendorPriceByItemID=function()error('merchant cache read')end}}}
          assert(ns.ProfItemPrices.GetPrice(999101)==37/4)
          raw.cost_copper=nil
          assert(ns.ProfVendorOffers[999101][1].price==1 and #ns.ProfItemPrices.GetOffers(999101)==0)
          assert(ns.ProfItemPrices.GetPrice(999101)==nil)
        ''')

    def test_dynamic_raw_amount_and_bundle_changes_are_not_hidden_by_price_cache(self):
        self.lua.execute('''
          local raw=schema(999102)
          assert(ns.ProfItemPrices.GetPrice(999102)==37/4)
          raw.cost_copper=60; ns.ProfItems[999102].VendorStackCount=3
          assert(ns.ProfItemPrices.GetPrice(999102)==20)
          assert(raw.cost_copper==60 and raw.stock==-1)
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
          assert(#ns.ProfItemPrices.GetOffers(999104)==0)
          local f=ns.ProfItemPrices.GetFormulaOffers(999104)
          assert(#f==1 and f[1].price==nil and not f[1].priceUsable)
          raw.cost_copper=37;ns.ProfItems[999104].VendorStackCount=nil
          assert(#ns.ProfItemPrices.GetOffers(999104)==0)
          f=ns.ProfItemPrices.GetFormulaOffers(999104)
          assert(#f==1 and f[1].price==nil and not f[1].priceUsable)
        ''')

    def test_faction_and_explicit_access_apply_to_raw_npc_rows(self):
        self.lua.execute('''
          local raw=schema(999105,{side='a'})
          assert(#ns.ProfItemPrices.GetOffers(999105,{faction='Horde'})==0)
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
          assert(#ns.ProfItemPrices.GetOffers(999106)==0)
          assert(#ns.ProfItemPrices.GetSuppliers(999106)==0)
          local f=ns.ProfItemPrices.GetFormulaOffers(999106)
          assert(#f==1 and f[1].price==37 and f[1].quantity==4 and f[1].priceUsable)
          assert(f[1].limited and not f[1].unlimited and f[1].maxStock==2)
          assert(f[1].stock==nil and f[1].stockStatus=='limited')
          assert(f[1].source=='wowhead' and raw.stock==2)
          raw.stock=nil
          f=ns.ProfItemPrices.GetFormulaOffers(999106)
          assert(#f==1 and f[1].stockUnknown and not f[1].unlimited)
          assert(#ns.ProfItemPrices.GetOffers(999106)==0)
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
          local q=ns.ProfItemPrices.GetOffers(999113)[1]
          assert(q.areaID==12 and q.mapID==1429 and q.x==nil and q.y==nil)
          assert(ns.ProfVendors[7][1]==1 and ns.ProfVendors[7][2]==100 and ns.ProfVendors[7][3]==10)
          ns.AreaMap=nil
          q=ns.ProfItemPrices.GetOffers(999113)[1]
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
          assert(r.mats[1].bundleSize==4 and r.mats[1].npcID==7)
          assert(r.mats[1].quoteSource=='client')
          assert(r.inventory[999108]==2,'bag inventory was subtracted or retained')
          assert(test.merchantReads==0 and test.dbReads==0)
        ''')

    def test_capture_keeps_auction_quote_when_known_npc_has_no_csv_cost(self):
        self.economy()
        self.lua.execute('''
          local raw=schema(999109);raw.cost_copper=nil;raw.cost_text=nil
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
            if m.source=='vendor' then assert(m.npcID==7 and m.cost==37 and m.bundleSize==4 and m.need==4)
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
          s.recipes={s.recipes[1]};s.recipes[1].mats={{999122,1},{11,1}}
          s.formulaOffers[999122]=ns.ProfItemPrices.GetFormulaOffers(999122)
          s.offers={[999122]=ns.ProfItemPrices.GetOffers(999122)}
          s.auctionSupply={[999122]={quantity=1}}
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
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
                  assert(ns.ProfItemPrices.GetPrice(5640,{faction='A'})==nil,'limited formula became an unlimited reagent')
                ''')

    def test_actual_importer_only_updates_data_and_retains_runtime_provider(self):
        from test_prof_items_pipeline import (
            NPC_FIELDS, PRICE_FIELDS, VENDOR_FIELDS, VENDORS_LUA, npc, price, vendor,
        )

        with tempfile.TemporaryDirectory(prefix="df-prof-runtime-preserved-") as directory:
            repository = Path(directory)
            package = repository / "df-prof-pipeline-v1.0"
            scripts = package / "_temp"
            output = package / "Core/Data"
            scripts.mkdir(parents=True)
            output.mkdir(parents=True)
            shutil.copyfile(ROOT / "df-prof-pipeline-v1.0/_temp/fc_prof_items.py",
                            scripts / "fc_prof_items.py")
            runtime_path = package / "Core/ProfItemPrices.lua"
            shutil.copyfile(ROOT / "Core/ProfItemPrices.lua", runtime_path)
            shutil.copyfile(ROOT / "DungeonsForever.toc", package / "DungeonsForever.toc")
            (package / "Core/Unrelated.lua").write_bytes(b"-- retain unrelated runtime code\r\n")
            vendors_lua = output / "Data_ProfVendors.lua"
            vendors_lua.write_text(VENDORS_LUA, encoding="utf-8")
            for relative, fields, rows in (
                ("scripts/out/vendors.csv", VENDOR_FIELDS, [vendor()]),
                ("scripts/out/npcs.csv", NPC_FIELDS, [npc()]),
                ("scripts/export_buyprice/output/item-buy-prices.csv", PRICE_FIELDS, [price()]),
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
            self.assertEqual({path for path in repository.rglob("*") if path.is_file()},
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
            lua.execute("assert(ns.ProfItemPrices.GetPrice(100,{faction='A'})==12345/5)")


if __name__ == "__main__":
    unittest.main()
