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
          PD.ProcureActive=function()return nil end
          nativeProcureStart=PD.ProcureStart
          PD.ProcureStart=function()error('default shopping must not run Optimize')end
          function lineContains(row,text)
            for _,line in ipairs(row.lines or {})do
              if tostring(line[1]):find(text,1,true)then return true end
            end
            return false
          end
          function receiptRows(rows,id)
            local found={}
            for _,row in ipairs(rows)do
              if row.it and row.it[1]==id and row.purchaseSource and not row.comparisonPreview then found[#found+1]=row end
            end
            return found
          end
          function textRow(rows,text)
            for _,row in ipairs(rows)do if row.text==text then return row end end
          end
          function splitPlan()
            local snap=fixture();snap.recipes[1].mats={{11,7}};snap.prices[11]=1
            snap.offers={[11]={{npcID=7,quantity=5,price=20,unlimited=true}}}
            snap.auctionSupply={[11]={quantity=2,complete=true,ownerExcluded=true}}
            return ns.ProfRouteSolver.Compute('alchemy',{snapshot=snap,start=1,target=2,
              autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
          end
        ''')

    def test_native_split_route_and_both_default_shop_layouts_agree_in_three_locales(self):
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
                  for _,grouped in ipairs({false,true})do
                    PD.shopGroup=grouped;local rows={};PD.RowsAutoShop(rows,plan)
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
                  end
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
          assert(head==format(ns.L['有 %d 种拍卖行物品数量未知，路线仅按价格估算，不能确认能买齐；请在 Auctionator 重新完整扫描。'],1))
          assert(detail:find('Item11',1,true))
          for _,grouped in ipairs({false,true})do
            PD.shopGroup=grouped;local rows={};PD.RowsAutoShop(rows,plan)
            local seen={};for _,row in ipairs(receiptRows(rows,11))do seen[row.purchaseSource]=row end
            local warning=ns.L['拍卖行可购数量未知，当前仅按价格估算；请在 Auctionator 重新完整扫描。']
            assert(lineContains(seen.ah,warning))
            assert(not lineContains(seen.vendor,warning))
          end
        ''')

    def test_known_shortage_has_the_actual_status_and_auction_row_explanation(self):
        self.prepare()
        self.lua.execute('''
          local plan=splitPlan();plan.feasible=false;plan.completeCost=false;plan.status='recalculate_required'
          local d={code='auctionSupplyLimited',item=11,required=3,available=2}
          plan.diagnostics={d};plan.blockingDiagnostics={d};plan.auctionSupplyShortages={d}
          for _,e in ipairs(plan.mats)do if e.source=='ah'then e.count=3;e.supplyRequired=3;e.unavailable=true end end
          assert(PD.PlanStatusText(plan)==ns.ProfEconomy.DiagnosticText(d))
          for _,grouped in ipairs({false,true})do
            PD.shopGroup=grouped;local rows={};PD.RowsAutoShop(rows,plan)
            local found=false
            for _,row in ipairs(receiptRows(rows,11))do if row.purchaseSource=='ah'then
              assert(lineContains(row,format(ns.L['拍卖行已读取数量不足：可购 %d 件，需要 %d 件。'],2,3)))
              found=true
            end end
            assert(found and textRow(rows,PD.PlanCostText(plan)))
          end
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
            for _,grouped in ipairs({false,true})do
              PD.shopGroup=grouped;local rows={};PD.RowsAutoShop(rows,plan)
              for _,row in ipairs(receiptRows(rows,11))do if row.purchaseSource=='ah'then
                assert(lineContains(row,warning))
              end end
            end
            assert(auction.availableCount==2,'warning rewrote the frozen receipt')
          end
        ''')

    def test_manual_comparison_is_an_unapplied_preview_and_never_replaces_the_plan(self):
        self.prepare()
        self.lua.execute('''
          local data=splitPlan();data.formulasTotal=3;data.formulaComplete=true
          data.formulas={{id=400,count=1,source='vendor',vendor=true,cost=3,unit=3,unlimited=true}}
          data.total=25;data.vendorTotal=23
          PD.RowsFormulaShop=function()end
          local opt={mats={{id=11,count=7,source='ah',cost=7,unit=1,supplyObserved=false}},
            formulas={{id=401,count=1,source='ah',cost=4}},total=11,vendorTotal=0,ahTotal=11,
            auctionSupplyUnknown=1,completeCost=false}
          PD.ProcureActive=function()return opt end;PD.shopGroup=true;PD.lvSummary={total=25}
          local rows={};PD.RowsAutoShop(rows,data)
          assert(PD.lvSummary.total==25)
          assert(textRow(rows,PD.PlanCostText(data)))
          assert(textRow(rows,ns.L['商人直售购入']).right==ns.ProfRouteAuto.MoneyStr(23,'copper'))
          assert(textRow(rows,ns.L['拍卖行购入']).right==ns.ProfRouteAuto.MoneyStr(2,'copper'))
          local current=receiptRows(rows,11);assert(#current==2)
          local source={};for _,row in ipairs(current)do source[row.purchaseSource]=row.purchaseCount end
          assert(source.vendor==5 and source.ah==2,'comparison replaced the selected plan sources')
          assert(textRow(rows,ns.L['材料采购比较（未应用）']).comparisonPreview)
          assert(textRow(rows,format(ns.L['比较总预算（含图纸）：%s'],
            PD.PlanCostText({total=14,completeCost=false}))).comparisonPreview)
          assert(textRow(rows,format(ns.L['已计入原路线图纸支出：%s'],
            ns.ProfRouteAuto.MoneyStr(3,'copper'))).comparisonPreview)
          local preview=0
          for _,row in ipairs(rows)do if row.comparisonPreview and row.purchaseSource=='ah'and row.it[1]==11 then
            assert(row.purchaseCount==7 and row.purchaseCost==7)
            assert(lineContains(row,ns.L['拍卖行可购数量未知，当前仅按价格估算；请在 Auctionator 重新完整扫描。']))
            preview=preview+1
          end end
          assert(preview==1)
          PD.FoldOn=function(key)return key=='shop_comparison'end
          rows={};PD.RowsAutoShop(rows,data)
          assert(#receiptRows(rows,11)==2 and PD.lvSummary.total==25)
          assert(textRow(rows,ns.L['材料采购比较（未应用）']))
          assert(not textRow(rows,format(ns.L['比较总预算（含图纸）：%s'],
            PD.PlanCostText({total=14,completeCost=false}))))
        ''')

    def test_comparison_capture_reserves_original_formula_stock_without_mutating_player_facts(self):
        self.prepare()
        self.lua.execute('''
          debugprofilestop=function()return 0 end
          PD.ProcureStart=nativeProcureStart
          local original={known={['alchemy:101']=false},auctionSupply={[11]={quantity=3}},prices={[11]=1},
            recipes={},professions={alchemy={cur=1,max=300}}}
          ns.ProfEconomy.Capture=function()return original end
          local result={feasible=false,status='infeasible',mats={},formulas={},total=0,
            blockingDiagnostics={{code='auctionSupplyLimited',item=11,required=7,available=2}}}
          local captured
          ns.ProfRouteSolver.NewProcurementJob=function(snapshot,demands)
            captured=snapshot;assert(demands[11]==7)
            return {result=result}
          end
          ns.ProfRouteSolver.Run=function()return true end
          local data={mats={{id=11,count=7,source='ah'}},formulas={{id=11,count=1,source='ah',
            recipeKey='alchemy:101',recipes={{key='alchemy:101'},{profession='alchemy',spell=102}}}}}
          PD.ProcureStart(data);assert(PD.procureJob)
          assert(queue[#queue]())
          assert(captured~=original and captured.auctionSupply[11].quantity==2)
          assert(captured.known['alchemy:101']and captured.known['alchemy:102'])
          assert(original.auctionSupply[11].quantity==3 and original.known['alchemy:101']==false
            and original.known['alchemy:102']==nil,'comparison changed actual player knowledge or input stock')
          assert(PD.procureRes==result and PD.procureView,'an unbuyable comparison was silently discarded')
        ''')

    def test_quantity_and_partial_vendor_explanations_exist_in_all_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            self.boot(locale)
            self.lua.execute('''
              for _,key in ipairs({'本行采购：%d 件','本行用于路线：%d 件；整包余量：%d 件。',
                '本路线选择从商人购买这部分材料。','材料采购比较（未应用）',
                '此比较尚未应用；升级路线、购物清单和 HUD 仍使用当前计划。',
                '比较买法','关闭比较','停止比较','材料（%d 种）· 比较买法',
                '比较总预算（含图纸）：%s','已计入原路线图纸支出：%s'})do
                assert(type(rawget(ns.L,key))=='string'and rawget(ns.L,key)~='',key)
              end
            ''')

    
    def test_comparison_validates_actual_pattern_demand(self):
        self.prepare()
        self.lua.execute('''
          PD.ProcureStart=nativeProcureStart
          debugprofilestop=function()return 0 end
          ns.IdleJobs={Add=function(fn)previewPump=fn end}

          local cases={
            {stock=0,need=1,allowed=false,reason='formulaAuctionSupplyInsufficient'},
            {stock=1,need=1,allowed=true},
            {stock=false,need=1,allowed=false,reason='formulaAuctionSupplyUnknown'},
            {stock=1,need=2,allowed=false,reason='formulaAuctionSupplyInsufficient'},
            {stock=2,need=2,allowed=true},
          }

          for _,case in ipairs(cases)do
            PD.ProcureClear()
            local original={
              known={},auctionSupply={},recipes={},
              professions={alchemy={cur=1,max=300}},
              considerAuctionSupply=false,stamp=1000
            }

            if case.stock~=false then
              original.auctionSupply[11]={
                quantity=case.stock,observedAt=1000,
                complete=true,ownerExcluded=true,
                source='client-auction-results'
              }
            end

            ns.ProfEconomy.Capture=function()return original end
            local result={
              feasible=true,costComplete=true,total=70,
              mats={{id=11,count=7,source='vendor',cost=70}}
            }
            ns.ProfRouteSolver.NewProcurementJob=function()
              return {result=result}
            end
            ns.ProfRouteSolver.Run=function()return true end

            local data={
              mats={{id=11,count=7,source='vendor',cost=70}},
              formulasTotal=3,formulaComplete=true,
              formulas={{
                id=11,count=case.need,cost=3,source='ah',
                recipeKey='alchemy:999'
              }}
            }

            PD.ProcureStart(data)
            assert(previewPump())

            local candidate=PD.procureRes
            assert(candidate==result)
            assert(candidate.comparisonCanBuy==case.allowed)

            local diagnostics=candidate.comparisonFormulaDiagnostics or {}
            if case.allowed then
              assert(#diagnostics==0,
                'valid auction pattern was incorrectly rejected')
            else
              assert(#diagnostics==1)
              local diagnostic=diagnostics[1]
              assert(diagnostic.item==11)
              assert(diagnostic.code==case.reason)

              if case.stock~=false then
                assert(diagnostic.available==case.stock)
                assert(diagnostic.required==case.need)
              end

              local rows={}
              PD.RowsProcurementComparison(rows,candidate,data)
              assert(textRow(rows,ns.ProfEconomy.DiagnosticText(diagnostic)))
            end

            assert(original.known['alchemy:999']==nil)
            assert(data.formulas[1].cost==3)
          end
        ''')



if __name__=='__main__':unittest.main()
