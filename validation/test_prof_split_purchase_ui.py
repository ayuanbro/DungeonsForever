"""Native route/shop rows keep finite-AH and NPC purchases separate.

Uses the actual Lua route and UI entry points. Widget measurement is mocked;
these checks do not claim in-game visual acceptance.
"""
import unittest
import test_prof_ui_fusion as ui


class SplitPurchaseUITests(unittest.TestCase):
    setUp=ui.ProfessionUIFusionTests.setUp
    boot=ui.ProfessionUIFusionTests.boot

    def prepare(self, locale='zhCN'):
        self.boot(locale)
        self.load((ui.ROOT/'Core/ProfSolverCapture.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
          function lineContains(row,text)
            for _,line in ipairs(row.lines or {})do
              if tostring(line[1]):find(text,1,true)then return true end
            end
            return false
          end
          function receiptRows(rows,id)
            local found={}
            for _,row in ipairs(rows)do
              if row.it and row.it[1]==id and row.purchaseSource then found[#found+1]=row end
            end
            return found
          end
          function textRow(rows,text)
            for _,row in ipairs(rows)do if row.text==text then return row end end
          end
          function splitPlan(reserveMode)
            local snap=fixture();snap.recipes[1].mats={{11,7}};snap.prices[11]=1
            snap.offers={[11]={{npcID=7,quantity=5,price=20,unlimited=true}}}
            snap.auctionSupply={[11]={quantity=2,complete=true,ownerExcluded=true}}
            return ns.ProfRouteSolver.Compute('alchemy',{snapshot=snap,start=1,target=2,
              autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000,reserveMode=reserveMode or 'off'})
          end
        ''')

    def test_native_split_route_and_default_list_agree_in_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.prepare(locale)
                self.lua.execute('''
                  local plan=splitPlan()
                  assert(plan.targetReached and plan.total==22 and plan.vendorTotal==20 and plan.ahTotal==2)
                  assert(#plan.mats==2 and plan.steps[1].cost==22)
                  ns.ProfRouteAuto.Get=function()return plan end
                  PD.autoPage='route';DungeonsForeverDB.prof.lvTarget.alchemy=2
                  local route={};PD.RowsLeveling(route)
                  local shown=false
                  for _,row in ipairs(route)do if row.lvstep then
                    assert(row.cost==ns.ProfRouteAuto.MoneyStr(22));shown=true
                  end end
                  assert(shown and PD.lvSummary.total==22)
                  local rows={};PD.RowsAutoShop(rows,plan)
                  local receipts=receiptRows(rows,11);assert(#receipts==2,'a split purchase row disappeared')
                  local money,quantity=0,0;local seen={}
                  for _,row in ipairs(receipts)do
                    money=money+row.purchaseCost;quantity=quantity+row.purchaseCount
                    seen[row.purchaseSource]=row
                    assert(lineContains(row,format(ns.L['本行采购：%d 件'],row.purchaseCount)))
                  end
                  assert(money==22 and quantity==7 and seen.ah and seen.vendor)
                  assert(seen.ah.purchaseCount==2 and seen.ah.purchaseCost==2)
                  assert(seen.vendor.purchaseCount==5 and seen.vendor.purchaseCost==20)
                  assert(seen.ah.tag.text==ns.L['拍卖行']and seen.vendor.tag.text==ns.L['NPC购买'])
                  assert(lineContains(seen.ah,format(ns.L['拍卖行数量快照：%d 件；本路线购买 %d 件。'],2,2)))
                  assert(not lineContains(seen.vendor,ns.L['商人直售（军需官处直购，无需拍卖行）']))
                  assert(textRow(rows,format(ns.L['共 %d 种材料 · 合计 %d 件'],1,7)))
                  assert(textRow(rows,ns.L['拍卖行购入']).right==ns.ProfRouteAuto.MoneyStr(2,'copper'))
                  assert(textRow(rows,ns.L['商人直售购入']).right==ns.ProfRouteAuto.MoneyStr(20,'copper'))
                  assert(textRow(rows,PD.PlanCostText(plan)))
                ''')

    def test_grouping_keeps_receipt_metadata_and_only_reports_supported_pack_surplus(self):
        self.prepare()
        self.lua.execute('''
          local entry={id=11,count=5,need=3,cost=20,unit=4,source='vendor',npcID=7,
            unlimited=true,bundleSize=5,bundlePrice=20,estimated=true,reference=true,
            costComplete=false,unavailable=false,quoteSource='supply-verified'}
          local data={mats={entry}}
          local groups=PD.TripGroups(data);local copied=groups[1].items[1]
          for key,value in pairs(entry)do assert(copied[key]==value,'grouping dropped '..key)end
          local rows={};PD.PushTripGroups(rows,data);local row=receiptRows(rows,11)[1]
          assert(lineContains(row,format(ns.L['本行采购：%d 件'],5)))
          assert(lineContains(row,format(ns.L['本行用于路线：%d 件；整包余量：%d 件。'],3,2)))
          data.mats[2]={id=11,count=2,cost=2,source='ah'}
          rows={};PD.PushTripGroups(rows,data)
          for _,receipt in ipairs(receiptRows(rows,11))do
            assert(not lineContains(receipt,format(ns.L['本行用于路线：%d 件；整包余量：%d 件。'],3,2)),
              'ambiguous per-source consumption was inferred from the combined item demand')
          end
        ''')

    def test_unknown_auction_quantity_survives_same_item_vendor_row_and_missing_counter(self):
        self.prepare()
        self.lua.execute('''
          local plan=splitPlan();plan.auctionSupplyUnknown=nil
          for _,e in ipairs(plan.mats)do if e.source=='ah'then
            e.availableCount=nil;e.supplyObserved=nil;e.supplyRequired=nil
          end end
          local head,detail=PD.PlanSupplyParts(plan)
          assert(head==format(ns.L['有 %d 种物品需要更新在售数量；请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'],1))
          assert(detail:find('Item11',1,true))
          local rows={};PD.RowsAutoShop(rows,plan)
          local seen={};for _,row in ipairs(receiptRows(rows,11))do seen[row.purchaseSource]=row end
          local warning=ns.L['请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。']
          assert(lineContains(seen.ah,warning))
          assert(not lineContains(seen.vendor,warning))
        ''')

    def test_known_shortage_has_the_actual_status_and_auction_row_explanation(self):
        self.prepare()
        self.lua.execute('''
          local plan=splitPlan();plan.feasible=false;plan.completeCost=false;plan.status='recalculate_required'
          local d={code='auctionSupplyLimited',item=11,required=3,available=2}
          plan.diagnostics={d};plan.blockingDiagnostics={d};plan.auctionSupplyShortages={d}
          for _,e in ipairs(plan.mats)do if e.source=='ah'then e.count=3;e.supplyRequired=3;e.unavailable=true end end
          assert(PD.PlanStatusText(plan)==ns.ProfEconomy.DiagnosticText(d))
          local rows={};PD.RowsAutoShop(rows,plan)
          local found=false
          for _,row in ipairs(receiptRows(rows,11))do if row.purchaseSource=='ah'then
            assert(lineContains(row,format(ns.L['扫描记录有 %d 件，需要 %d 件；请用 Auctionator 完整扫描后重新计算。'],2,3)))
            found=true
          end end
          assert(found and textRow(rows,PD.PlanCostText(plan)))
        ''')

    def test_invalid_stock_metadata_cannot_make_an_old_numeric_quantity_look_usable(self):
        self.prepare()
        self.lua.execute('''
          for _,invalid in ipairs({{supplyStatus='expired'},{supplyObserved=false},
            {supplyComplete=false},{supplySource='auctionator-history'}})do
            local plan=splitPlan();plan.auctionSupplyUnknown=nil
            local auction
            for _,entry in ipairs(plan.mats)do if entry.source=='ah'then auction=entry end end
            assert(auction.availableCount==2)
            for key,value in pairs(invalid)do auction[key]=value end
            assert(PD.PlanSupplyParts(plan))
            local warning=PD.AuctionSupplyText(auction)
            assert(warning:find('Auctionator',1,true))
            assert(not warning:find(format(ns.L['拍卖行数量快照：%d 件；本路线购买 %d 件。'],2,2),1,true))
            local rows={};PD.RowsAutoShop(rows,plan)
            for _,row in ipairs(receiptRows(rows,11))do if row.purchaseSource=='ah'then
              assert(lineContains(row,warning))
            end end
            assert(auction.availableCount==2,'warning rewrote the frozen receipt')
          end
        ''')


    def test_quantity_and_partial_vendor_explanations_exist_in_all_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            self.boot(locale)
            self.lua.execute('''
              for _,key in ipairs({'本行采购：%d 件','本行用于路线：%d 件；整包余量：%d 件。',
                '本路线选择从商人购买这部分材料。'})do
                local value=GetLocale()=='zhCN' and ns.L[key] or rawget(ns.L,key)
                assert(type(value)=='string' and value~='',key)
              end
            ''')


if __name__=='__main__':unittest.main()
