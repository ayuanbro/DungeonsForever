"""Shopping view clicks preserve real solver/execution procurement facts.

Native Lua renders shopping rows and handles header/fold clicks. Widgets record
state and callbacks; these tests do not assert in-game pixels or font metrics.
"""
import unittest
import test_prof_ui_fusion as ui
import test_prof_split_purchase_ui as split
from test_prof_issue4 import WIDGETS
from test_prof_reserve import HELPERS


class ShoppingViewTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.prepare()

    def prepare(self, locale='zhCN'):
        split.SplitPurchaseUITests.prepare(self, locale)
        self.lua.execute(WIDGETS)
        self.lua.execute('''
          local base=recordedWidget
          function recordedWidget(...)
            local w=base(...)
            function w:GetFontString()return self end
            function w:GetTextColor()return 1,1,1,1 end
            function w:CreateFontString()return recordedWidget()end
            function w:GetAlpha()return 1 end
            return w
          end
          CreateFrame=recordedWidget
          ns.ProfHost.MakeFS=recordedWidget
          ns.ProfHost.NewButton=function(parent,text,width,height)
            local b=recordedWidget(parent);b:SetText(text);b:SetSize(width,height);return b
          end
          ns.ProfHost.SetButtonSelected=function(w,on)w.selected=on end
          ns.ProfHost.DG.ItemIcon=function()return '?'end
          ns.hui.layer={L0={},L1={},L2={},L3={}}
          ns.hui.BuildRoundedBG=function()return{}end
        ''')
        self.load((ui.ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.load((ui.ROOT/'Core/ProfReserve.lua').read_text(encoding='utf-8-sig'))
        self.load((ui.ROOT/'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(HELPERS)
        self.lua.execute('''
          PD=ns.ProfModule;PD.cur='alchemy';PD.tab='leveling';PD.autoPage='shop'
          PD.child=recordedWidget();PD.scroll=recordedWidget()
          PD.ProfLearned=function()return skills end
          PD.Fit=function(text)return text end;PD.Wrap=function(text)return{text}end
          PD.CardOf=function()end;PD.PriceTipLines=function()return{}end
          PD.MakePill=function()local w=recordedWidget();w.t=recordedWidget();return w end
          ns.ProfFollow.Paint=function()end
          ns.ProfVendorNames={[7]='Selected supplier'}
          ns.ProfVendors={[7]={'Zone',101,22,33}}
          C_Map={GetMapInfo=function()return{name='Selected zone'}end}
          PD.MarkVendorLoc=function(loc)marked=loc end
          ns.AuctionBridge={DoImport=function(name,items)importName=name;imported=items end,
            GetAuctionSupply=function()return{quantity=2}end,
            GetAuctionSupplyStatus=function()return'verified'end}
          function deepEqual(a,b)
            if type(a)~=type(b)then return false end
            if type(a)~='table'then return a==b end
            for k,v in pairs(a)do if not deepEqual(v,b[k])then return false end end
            for k in pairs(b)do if a[k]==nil then return false end end
            return true
          end
          function receipts(rows)
            local out={}
            for _,r in ipairs(rows)do if r.purchaseSource then
              out[#out+1]={id=r.it[1],source=r.purchaseSource,count=r.purchaseCount,cost=r.purchaseCost}
            end end
            table.sort(out,function(a,b)
              if a.id~=b.id then return a.id<b.id end
              return a.source<b.source
            end)
            return out
          end
          function findFold(rows,key)
            for _,r in ipairs(rows)do if r.foldKey==key then return r end end
          end
          function findText(rows,text)
            for _,r in ipairs(rows)do if r.text==text then return r end end
          end
          function currentRows()
            local rows={};PD.RowsAutoShop(rows,plan);return rows
          end
          function paintShopping()
            renderCalls=(renderCalls or 0)+1
            visibleRows=currentRows()
            local _,handler=PD.LevelTool();PD.onTool=handler
            titleWidget=PD.Row(1);PD.BindRow(titleWidget,visibleRows[1],24)
            local fold=findFold(visibleRows,'shop_mats')
            foldWidget=PD.Row(2)
            if fold then PD.BindRow(foldWidget,fold,24)else foldWidget.foldZone:Hide()end
          end
          PD.Render=paintShopping;PD.RequestRender=paintShopping
          function clickHeader(key)
            for _,b in ipairs(titleWidget.segBtns)do
              if b.visible and b.__segKey==key then b.scripts.OnClick(b);return end
            end
            error('missing header button '..key)
          end
          function clickFold()
            assert(foldWidget.foldZone.visible)
            foldWidget.foldZone.scripts.OnClick(foldWidget.foldZone)
          end
          function usePlan(p)
            run=assert(ns.ProfExecution.StartNew('alchemy',p));plan=run.plan
            frozen=ns.ProfEconomy.Copy(plan);index=run.currentIndex
            PD.autoSnapshot=plan;PD.autoSnapshotSlug='alchemy'
            PD.Render()
          end
          function unchanged()
            assert(run.currentIndex==index and deepEqual(plan,frozen),'view changed frozen execution')
            assert(DungeonsForeverDB.prof.shopGroup==nil and DungeonsForeverDB.prof.shop_mats==nil)
          end
        ''')

    def test_default_header_actual_clicks_and_mixed_receipts_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.prepare(locale)
                self.lua.execute('''
                  assert(PD.shopGroup==false and not PD.FoldOn('shop_mats'))
                  usePlan(splitPlan())
                  assert(#visibleRows[1].segs==2 and findFold(visibleRows,'shop_mats'))
                  local ordinary=receipts(visibleRows)
                  assert(#ordinary==2 and ordinary[1].source=='ah' and ordinary[1].count==2 and ordinary[1].cost==2)
                  assert(ordinary[2].source=='vendor' and ordinary[2].count==5 and ordinary[2].cost==20)
                  clickHeader('shop_group')
                  assert(PD.shopGroup and not findFold(visibleRows,'shop_mats'))
                  assert(findText(visibleRows,'Selected supplier'))
                  assert(deepEqual(ordinary,receipts(visibleRows)))
                  clickHeader('shop_group')
                  assert(not PD.shopGroup and deepEqual(ordinary,receipts(visibleRows)))
                  for _,row in ipairs(visibleRows)do for _,seg in ipairs(row.segs or {})do
                    assert(not seg.key:find('procure',1,true),'buying optimizer returned')
                  end end
                  unchanged()
                ''')

    def test_whole_material_fold_keeps_formula_and_budget_and_survives_view_switch(self):
        self.lua.execute('''
          local p=splitPlan();p.formulas={{id=400,count=1,cost=50,source='vendor',npcID=7,spell=102}}
          p.formulaTotal=50;p.formulasTotal=50
          usePlan(p)
          local receipt=receipts(visibleRows);local budget=PD.PlanCostText(plan)
          assert(#receipt==2 and findFold(visibleRows,'shop_formulas'))
          clickFold()
          assert(PD.FoldOn('shop_mats') and #receipts(visibleRows)==0)
          assert(findFold(visibleRows,'shop_formulas') and findText(visibleRows,budget))
          local formula=false;for _,row in ipairs(visibleRows)do if row.it and row.it[1]==400 then formula=true end end
          assert(formula,'material fold hid teaching items')
          clickHeader('shop_group');assert(deepEqual(receipt,receipts(visibleRows)))
          clickHeader('shop_group');assert(#receipts(visibleRows)==0)
          clickFold();assert(deepEqual(receipt,receipts(visibleRows)))
          unchanged()
        ''')

    def test_import_button_uses_real_auction_export_in_every_view_and_fold_state(self):
        self.lua.execute('''
          usePlan(splitPlan())
          local expected
          for state=1,4 do
            if state==2 then clickFold()
            elseif state==3 then clickHeader('shop_group')
            elseif state==4 then clickHeader('shop_group')end
            imported=nil;clickHeader('import_list')
            assert(imported and #imported==1 and imported[1].need==2 and imported[1].name=='Item11')
            assert(importName and importName~='')
            expected=expected or ns.ProfEconomy.Copy(imported)
            assert(deepEqual(expected,imported));unchanged()
          end
        ''')

    def test_reserve_inventory_deduction_and_budget_are_identical_in_both_views(self):
        self.lua.execute('''
          bag[11]=6;usePlan(reserveSolve())
          local reference=ns.ProfFollow.ShoppingForPlan('alchemy',plan)[1]
          assert(reference.baseNeed==5 and reference.reserveNeed==3 and reference.need==8)
          assert(reference.have==6 and reference.purchaseCount==2 and reference.purchaseCost==14)
          local ordinary=receipts(visibleRows)
          assert(#ordinary==1 and ordinary[1].count==2 and ordinary[1].cost==14)
          local budget=format(ns.L['备用材料预算：%s'],ns.ProfRouteAuto.MoneyStr(plan.reserve.total,'copper'))
          assert(findText(visibleRows,budget))
          clickFold();assert(#receipts(visibleRows)==0 and findText(visibleRows,budget))
          clickHeader('shop_group');assert(deepEqual(ordinary,receipts(visibleRows)))
          clickHeader('import_list');assert(#imported==1 and imported[1].need==2)
          clickHeader('shop_group');assert(#receipts(visibleRows)==0)
          clickFold();assert(deepEqual(ordinary,receipts(visibleRows)))
          assert(ns.ProfFollow.ShoppingForPlan('alchemy',plan)[1].have==6)
          unchanged()
        ''')

    def test_reserve_split_sources_and_unknown_inventory_never_merge_or_turn_into_zero(self):
        self.lua.execute('''
          usePlan(splitPlan('ample'))
          local ordinary=receipts(visibleRows);assert(#ordinary==2)
          assert(ordinary[1].source=='ah' and ordinary[1].count==2)
          assert(ordinary[2].source=='vendor' and ordinary[2].count==5)
          clickHeader('shop_group');assert(deepEqual(ordinary,receipts(visibleRows)))
          C_Item.GetItemCount=function()return nil end;PD.Render()
          local unknown=receipts(visibleRows)
          assert(#unknown==1 and unknown[1].source=='unknown' and unknown[1].count==nil and unknown[1].cost==nil)
          clickHeader('shop_group');assert(deepEqual(unknown,receipts(visibleRows)))
          for _,row in ipairs(visibleRows)do if row.purchaseSource=='unknown' then
            assert(row.right==ns.L['请检查背包'] and row.right2==ns.L['请核对价格'])
          end end
          unchanged()
        ''')

    def test_unknown_costs_stay_unknown_for_rows_and_vendor_auction_subtotals(self):
        self.lua.execute('''
          local p=splitPlan();p.mats[1].cost=nil;p.mats[2].cost=nil
          p.mats[1].unit=1;p.mats[2].unit=4
          p.total=nil;p.completeCost=false
          usePlan(p)
          local ordinary=receipts(visibleRows)
          assert(#ordinary==2 and ordinary[1].cost==nil and ordinary[2].cost==nil)
          for _,row in ipairs(visibleRows)do if row.purchaseSource then
            assert(row.right2==PD.UnpriceShort({}) or row.right2==ns.L['请核对价格'])
          end end
          clickHeader('shop_group')
          assert(deepEqual(ordinary,receipts(visibleRows)))
          assert(findText(visibleRows,'Selected supplier').suffix:find(ns.L['请核对价格'],1,true))
          assert(findText(visibleRows,format(ns.L['拍卖行（%d 种）'],1)).right==ns.L['请扫描拍卖行'])
          assert(findText(visibleRows,format(ns.L['材料（%d 种）· 按商人采购'],1)).right:find(ns.L['请核对价格'],1,true))
          unchanged()
        ''')

    def test_vendor_rows_keep_same_map_action_in_plain_and_grouped_views(self):
        self.lua.execute('''
          usePlan(splitPlan())
          ns.VendorPriceDB={GetOffers=function()error('view requested a new supplier')end}
          for view=1,2 do
            local vendor,auction
            for _,row in ipairs(visibleRows)do
              if row.purchaseSource=='vendor'then vendor=row elseif row.purchaseSource=='ah'then auction=row end
            end
            assert(vendor and vendor.act and auction and not auction.act)
            local widget=PD.Row(3);PD.BindRow(widget,vendor,vendor.h)
            marked=nil;widget.scripts.OnClick(widget,'LeftButton')
            assert(marked==ns.ProfVendors[7])
            if view==1 then clickHeader('shop_group')end
          end
          unchanged()
        ''')

    def test_reload_resets_only_in_memory_view_and_fold_preferences(self):
        self.lua.execute('''
          usePlan(splitPlan());clickFold();clickHeader('shop_group')
          assert(PD.shopGroup and PD.FoldOn('shop_mats'))
          savedDB=DungeonsForeverDB;savedPlan=run.plan;savedID=run.planID
        ''')
        self.load((ui.ROOT/'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD=ns.ProfModule
          assert(PD.shopGroup==false and not PD.FoldOn('shop_mats'))
          assert(DungeonsForeverDB==savedDB and run.plan==savedPlan and run.planID==savedID)
          unchanged()
        ''')

    def vendor_cache_fixture(self):
        self.load((ui.ROOT/'Core/VendorPriceDB.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          cachedVendorCalls={}
          Auctionator={API={v1={GetVendorPriceByItemID=function(caller,id)
            assert(caller=='DungeonsForever')
            cachedVendorCalls[id]=(cachedVendorCalls[id] or 0)+1
            return ({[2880]=95,[4470]=38})[id]
          end}}}
          ns.ProfSupply={Ensure=function()end}
          ns.ProfVendorOffers={[12]={{npcID=7,price=5,quantity=1,unlimited=true,
            available=true,purchasable=true,reference=true,priceVerified=true,
            source='supply-verified',verifiedAt=1000,faction='N'}}}
          function cachedNPCPlan(mode,auctionFlux)
            local s=fixture();s.considerAuctionSupply=false
            s.recipes[1].mats={{2880,3},{4470,2},{11,1},{12,1}}
            s.prices={[2880]=auctionFlux and 1 or 200,[4470]=100,[11]=7,[12]=20}
            s.offers={}
            for _,id in ipairs({2880,4470,12})do
              s.offers[id]=ns.VendorPriceDB.GetOffers(id)
            end
            for _,id in ipairs({2880,4470})do
              local q=s.offers[id][1]
              assert(q and q.npcID==nil and q.priceSource=='auctionator-vendor' and q.priceBasis=='cached-unit')
            end
            if mode=='ample' then s.recipes[1].yellow=1;s.recipes[1].green=1;s.recipes[1].grey=100 end
            local p,j=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=2,
              autoCraftTools=false,recoveryEnabled=false,reserveMode=mode,cpuLimitMs=1000})
            assert(not j.error and p.targetReached)
            return p
          end
          function rowSections(rows)
            local out,current={},nil
            for _,row in ipairs(rows)do
              if row.kind=='head' and row.col==1 then current=row.text end
              if row.purchaseSource then out[row.it[1]]={row=row,section=current}end
            end
            return out
          end
          function assertCachedReceipts()
            for _,e in ipairs(plan.mats)do if e.id==2880 or e.id==4470 then
              assert(e.source=='vendor' and e.npcID==nil and e.quoteSource=='auctionator-vendor')
              assert(e.priceBasis=='cached-unit' and e.unit==(e.id==2880 and 95 or 38))
            end end
            for _,entry in ipairs(ns.ProfFollow.ShoppingForPlan('alchemy',plan))do
              if entry.id==2880 or entry.id==4470 then
                for _,p in ipairs(entry.purchases or {})do
                  assert(p.source=='vendor' and p.npcID==nil and p.quoteSource=='auctionator-vendor')
                  assert(p.priceBasis=='cached-unit')
                end
              end
            end
          end
        ''')

    def test_real_vendor_cache_without_npc_has_own_group_in_base_and_reserve_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            for mode in ('off','ample'):
                with self.subTest(locale=locale,reserve=mode):
                    self.prepare(locale);self.vendor_cache_fixture()
                    self.lua.globals().reserveMode=mode
                    self.lua.execute('''
                      usePlan(cachedNPCPlan(reserveMode))
                      assert(cachedVendorCalls[2880]>0 and cachedVendorCalls[4470]>0)
                      if reserveMode=='off' then assert(plan.total==373)
                      else assert(plan.reserve.total>0)end
                      assertCachedReceipts()
                      local plain=receipts(visibleRows)
                      clickHeader('shop_group')
                      assert(deepEqual(plain,receipts(visibleRows)))
                      local sections=rowSections(visibleRows)
                      local label=ns.L['NPC采购（未指定商人）']
                      assert(sections[2880].section==label and sections[4470].section==label)
                      assert(sections[2880].row.tag.text==ns.L['NPC购买'] and not sections[2880].row.act)
                      assert(sections[4470].row.tag.text==ns.L['NPC购买'] and not sections[4470].row.act)
                      assert(sections[12].section=='Selected supplier' and sections[12].row.act)
                      assert(sections[11].section==format(ns.L['拍卖行（%d 种）'],1))
                      local cacheCost=sections[2880].row.purchaseCost+sections[4470].row.purchaseCost
                      local vendorCost=cacheCost+sections[12].row.purchaseCost
                      assert(findText(visibleRows,label).right==format(ns.L['%d 种 · %s'],2,
                        ns.ProfRouteAuto.MoneyStr(cacheCost,'copper')))
                      assert(findText(visibleRows,format(ns.L['材料（%d 种）· 按商人采购'],4)).right==
                        format(ns.L['NPC采购合计：%s'],ns.ProfRouteAuto.MoneyStr(vendorCost,'copper')))
                      imported=nil;clickHeader('import_list')
                      assert(imported and #imported==1 and imported[1].name=='Item11')
                      assert(imported[1].need==sections[11].row.purchaseCount)
                      for _,key in ipairs({'NPC采购（未指定商人）','来源待确认','NPC采购合计：%s'})do
                        assert(GetLocale()=='zhCN' and ns.L[key] or rawget(ns.L,key),key)
                      end
                      assertCachedReceipts();unchanged()
                    ''')

    def test_explicit_cheaper_auction_remains_auction_despite_real_vendor_cache(self):
        self.vendor_cache_fixture()
        self.lua.execute('''
          usePlan(cachedNPCPlan('off',true))
          local plain=receipts(visibleRows)
          clickHeader('shop_group')
          local sections=rowSections(visibleRows)
          assert(sections[2880].row.purchaseSource=='ah')
          assert(sections[2880].section==format(ns.L['拍卖行（%d 种）'],2))
          assert(sections[4470].section==ns.L['NPC采购（未指定商人）'])
          assert(deepEqual(plain,receipts(visibleRows)))
          imported=nil;clickHeader('import_list')
          assert(imported and #imported==2)
          local seen={};for _,entry in ipairs(imported)do seen[entry.name]=entry.need end
          assert(seen.Item2880==3 and seen.Item11==1 and not seen.Item4470)
          unchanged()
        ''')

    def test_unassigned_npc_unknown_price_and_unknown_source_have_distinct_headers(self):
        self.vendor_cache_fixture()
        self.lua.execute('''
          local p=cachedNPCPlan('off');local cached
          for _,e in ipairs(p.mats)do if e.id==4470 then e.cost=nil;e.unpriced=true;cached=e end end
          assert(cached and cached.npcID==nil)
          p.mats[#p.mats+1]={id=99,count=2,source='unknown',vendor=true,cost=nil,unpriced=true}
          usePlan(p);local plain=receipts(visibleRows)
          clickHeader('shop_group')
          local sections=rowSections(visibleRows)
          local label=ns.L['NPC采购（未指定商人）']
          assert(sections[4470].section==label and sections[4470].row.purchaseCost==nil)
          assert(sections[99].section==ns.L['来源待确认'] and sections[99].row.purchaseCost==nil)
          assert(sections[99].row.purchaseSource=='unknown')
          assert(findText(visibleRows,label).right==format(ns.L['%d 种 · %s'],2,ns.L['请核对价格']))
          assert(findText(visibleRows,format(ns.L['材料（%d 种）· 按商人采购'],5)).right==
            format(ns.L['NPC采购合计：%s'],ns.L['请核对价格']))
          assert(deepEqual(plain,receipts(visibleRows)))
          unchanged()
        ''')


if __name__=='__main__':unittest.main()
