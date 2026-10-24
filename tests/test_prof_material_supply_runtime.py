"""Material NPC prices require positive supply evidence independent of item prices."""
import unittest

from test_prof_vendor import ROOT, runtime


class MaterialSupplyRuntime(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()

    def test_missing_supply_and_schema_never_promote_root_prices(self):
        self.lua.execute('''
          for _,id in ipairs({2589,2840})do
            ns.ProfItems[id]={cost_copper=1,VendorStackCount=1,offers={
              [7]={npc_id=7,cost_copper=1,stock=-1}}}
            assert(ns.ProfItemPrices.GetPrice(id)==nil)
          end
          material(2589)
          assert(ns.ProfItemPrices.GetPrice(2589)==37/4)
          ns.ProfMaterialSupplyMeta.schemaVersion=2
          assert(ns.ProfItemPrices.GetPrice(2589)==nil)
          ns.ProfMaterialSupplyMeta=nil
          assert(ns.ProfItemPrices.GetPrice(2589)==nil)
        ''')

    def test_supply_conditions_fail_closed(self):
        self.lua.execute('''
          for _,case in ipairs({{eligible=false},{stockState='limited'},
            {stockState='unknown'},{costKind='mixed'},{costKind='currency'},
            {access='unknown'},{access='reputation'},{role='quartermaster'},
            {side='unknown'},{priceSource='unverified'},
            {sourceURL=''},{verifiedAt=''},{evidenceHash=''},
            {currency_kind='item'},{currencyID=123}})do
            material(2589,case)
            assert(#ns.ProfItemPrices.GetOffers(2589)==0,
              'invalid qualification accepted: '..tostring(next(case)))
          end
          local row=material(2589)
          for _,key in ipairs({'eligible','stockState','costKind','access','role','side',
            'priceSource','sourceURL','verifiedAt','evidenceHash','price','quantity'})do
            local saved=row[key];row[key]=nil
            assert(#ns.ProfItemPrices.GetOffers(2589)==0,'missing evidence accepted: '..key)
            row[key]=saved
          end
        ''')

    def test_roles_faction_access_and_multiple_sellers(self):
        self.lua.execute('''
          for _,role in ipairs({'profession_supply','trade_supply','reagent_supply',
            'general_goods','cooking_supply','fishing_supply'})do
            local row=material(2320,{role=role,side='a'})
            assert(#ns.ProfItemPrices.GetOffers(2320,{faction='Alliance'})==1)
            assert(#ns.ProfItemPrices.GetOffers(2320,{faction='Horde'})==0)
            assert(#ns.ProfItemPrices.GetOffers(2320,{faction='A',npcAccess={[7]=false}})==0)
          end
          material(2320,{side='h',price=5,quantity=1},8)
          material(2320,{side='n',price=9,quantity=2},9)
          local a=ns.ProfItemPrices.GetOffers(2320,{faction='A'})
          local h=ns.ProfItemPrices.GetOffers(2320,{faction='H'})
          assert(#a==2 and #h==2 and a[1].unit==4.5 and h[1].unit==4.5)
          assert(a[2].price==37 and h[2].price==5)
          for _,q in ipairs(a)do
            for _,key in ipairs({'npcID','npcName','name','faction','areaID','mapID','url',
              'stock','maxStock','requirements'})do assert(q[key]==nil)end
          end
          a[1].price=1000
          assert(ns.ProfMaterialSupply[2320].offers[9].price==9)
        ''')

    def test_identical_unlimited_quotes_deduplicate_after_access_without_losing_bundles(self):
        self.lua.execute('''
          for npc=7,106 do
            material(2320,{price=10,quantity=5,evidenceHash='proof-'..npc},npc)
          end
          local quotes=ns.ProfItemPrices.GetOffers(2320)
          assert(#quotes==1 and quotes[1].evidenceHash=='proof-7')
          quotes=ns.ProfItemPrices.GetOffers(2320,{npcAccess={[7]=false}})
          assert(#quotes==1 and quotes[1].evidenceHash=='proof-8',
            'denied first supplier suppressed an accessible identical offer')
          ns.ProfMaterialSupply[2320].offers[7].side='h'
          quotes=ns.ProfItemPrices.GetOffers(2320,{faction='A'})
          assert(#quotes==1 and quotes[1].evidenceHash=='proof-8')
          material(2320,{price=2,quantity=1},107)
          material(2320,{price=11,quantity=5},108)
          material(2320,{price=10,quantity=5,priceSource='wowhead_npc_bundle'},109)
          quotes=ns.ProfItemPrices.GetOffers(2320,{faction='A'})
          assert(#quotes==4,'distinct bundle, price or source alternatives were collapsed')
          local options={}
          for _,q in ipairs(quotes)do
            options[q.price..':'..q.quantity..':'..q.priceSource]=true
          end
          assert(options['10:5:client_base_bundle'] and options['2:1:client_base_bundle'])
          assert(options['11:5:client_base_bundle'] and options['10:5:wowhead_npc_bundle'])
          assert(ns.ProfMaterialSupply[2320].offers[7].evidenceHash=='proof-7')
          assert(ns.ProfMaterialSupply[2320].offers[106].evidenceHash=='proof-106')
        ''')

    def test_integer_procurement_selects_whole_bundle_and_cheaper_auction(self):
        ns = self.lua.globals().ns
        ns.LoadForeverPages = True
        for name in ('ProfEconomy.lua', 'ProfRouteSolver.lua'):
            self.lua.execute((ROOT / 'Core' / name).read_text(encoding='utf-8-sig'), 'Test', ns)
        self.lua.execute('''
          material(2320,{price=37,quantity=4},7)
          material(2320,{price=26,quantity=3},8)
          local s={recipes={},professions={},known={},prices={[2320]=10},
            offers={[2320]=ns.ProfItemPrices.GetOffers(2320)}}
          local r=ns.ProfRouteSolver.Procure(s,2320,6)
          assert(r.feasible and r.total==52 and r.vendorTotal==52 and r.ahTotal==0)
          local purchased=0
          for _,m in ipairs(r.mats)do
            assert(m.npcID==nil and m.count%m.bundleSize==0)
            purchased=purchased+m.count
          end
          assert(purchased==6)
          s.prices[2320]=2
          r=ns.ProfRouteSolver.Procure(s,2320,6)
          assert(r.feasible and r.total==12 and r.ahTotal==12 and r.vendorTotal==0)
          material(2320,{price=10,quantity=1},9)
          s.prices={};s.offers[2320]=ns.ProfItemPrices.GetOffers(2320)
          r=ns.ProfRouteSolver.Procure(s,2320,1)
          assert(r.feasible and r.total==10 and r.vendorTotal==10,
            'lowest unit price hid the cheaper small-demand bundle')
          assert(#r.mats==1 and r.mats[1].bundleSize==1 and r.mats[1].count==1)
        ''')

    def test_material_fingerprint_invalidates_even_ah_purchasing_view_without_mutation(self):
        ns = self.lua.globals().ns
        ns.LoadForeverPages = True
        self.lua.execute((ROOT / 'Core/ProfRouteAuto.lua').read_text(encoding='utf-8-sig'), 'Test', ns)
        self.lua.execute('''
          assert(ns.ProfEconomy==nil,'quotation-only test unexpectedly loaded economy')
          ns.ProfItemsMeta={sources={csv={sha256='formula-fixed'}}}
          local original={status='complete',scheme='cheapest',steps={{1,2,10,1}},
            mats={{id=2589,source='ah',cost=7}},actions={},total=7,ahTotal=7,
            vendorTotal=0,start=1,target=2,feasible=true,craftsDone=3}
          ns.ProfRouteAuto.StampVendorQuotes(original)
          assert(not ns.ProfRouteAuto.VendorQuotesChanged(original))
          ns.ProfMaterialSupplyMeta.fingerprint='supply-b'
          local view=ns.ProfRouteAuto.ValidateVendorQuotes(original)
          assert(view~=original and view.status=='recalculate_required' and view.total==0)
          assert(#view.steps==0 and #view.mats==0 and view.vendorQuoteRevision==5)
          assert(original.total==7 and original.craftsDone==3 and #original.steps==1)
          assert(original.vendorQuoteData=='material-supply-v1:supply-a|formula:formula-fixed')
          assert(view.vendorQuoteData=='material-supply-v1:supply-b|formula:formula-fixed')
        ''')

    def test_quote_validation_without_economy_preserves_existing_formula_policy(self):
        ns = self.lua.globals().ns
        ns.LoadForeverPages = True
        self.lua.execute((ROOT / 'Core/ProfRouteAuto.lua').read_text(encoding='utf-8-sig'), 'Test', ns)
        self.lua.execute('''
          assert(ns.ProfEconomy==nil)
          local original={status='complete',steps={{1,2,10,1}},mats={},total=7,
            formulaPolicy={revision=1,allowLimited=true},craftsDone=3}
          ns.ProfRouteAuto.StampVendorQuotes(original)
          assert(original.formulaPolicy.allowLimited==true)
          assert(ns.ProfRouteAuto.ValidateVendorQuotes(original)==original)
          ns.ProfMaterialSupplyMeta.fingerprint='supply-b'
          local view=ns.ProfRouteAuto.ValidateVendorQuotes(original)
          assert(view.status=='recalculate_required' and view.total==0 and #view.steps==0)
          assert(view.diagnostics[1].code=='vendorQuoteChanged')
          assert(original.total==7 and original.craftsDone==3 and #original.steps==1)
          assert(original.formulaPolicy.allowLimited==true)
        ''')


if __name__ == '__main__':
    unittest.main()
