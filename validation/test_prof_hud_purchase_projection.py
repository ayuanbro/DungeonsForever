"""Frozen purchase receipts and current HUD buying needs use separate ledgers."""
import unittest

import test_prof_ui_fusion as ui
import test_prof_issue4 as issue4


class HUDPurchaseProjectionTests(unittest.TestCase):
    setUp = issue4.Issue4Tests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def prepare(self, needed=7, have=0):
        self.lua.globals().needed=needed
        self.lua.globals().owned=have
        self.lua.execute('''
          local snapshot=fixture();snapshot.recipes[1].mats={{11,needed}}
          snapshot.prices[11]=1;snapshot.auctionSupply={[11]={quantity=2}}
          snapshot.offers={[11]={{npcID=9,price=10,quantity=5,unlimited=true}}}
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(snapshot)end
          frozen=finish('alchemy',{start=1,target=2,recoveryEnabled=false})
          assert(frozen.targetReached)
          assert(ns.ProfExecution.Bind('alchemy',frozen))
          bag[11]=owned
          ns.AuctionBridge={GetAuctionSupply=function()return {quantity=2}end,
            GetAuctionSupplyStatus=function()return 'verified'end,
            DoImport=function(name,items)imported=items end}
          DungeonsForeverDB.prof.follow={['Test-Realm']={slug='alchemy',skill=1,step=1,t0=1000}}
          pf=ns.ProfFollow
          ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n)..'c'end
          ns.ProfVendorNames={[9]='Supplier'}
          ns.VendorPriceDB.GetOffers=function()error('projection fetched a new NPC quote')end
          ns.ProfRouteAuto.AHPriceOf=function()error('projection fetched a new auction quote')end
        ''')

    def test_owned_stock_is_allocated_by_whole_pack_cost_instead_of_a_fixed_source_order(self):
        for needed,have,ah,vendor,cost,plan_cost in ((7,2,0,5,10,12),(12,5,2,5,12,22)):
            with self.subTest(needed=needed,owned=have):
                if needed==12:
                    self.setUp()
                self.prepare(needed,have)
                self.lua.globals().expectedAH=ah
                self.lua.globals().expectedNPC=vendor
                self.lua.globals().expectedCost=cost
                self.lua.globals().expectedPlanCost=plan_cost
                self.lua.execute('''
                  local row=pf.ShoppingList('alchemy')[1]
                  assert(row.need==needed and row.materialNeed==needed and row.have==owned)
                  assert(row.missing==needed-owned and row.purchaseCount==expectedAH+expectedNPC)
                  assert(row.planPurchaseCount==needed and row.planPurchaseCost==expectedPlanCost)
                  assert(row.ahCount==expectedAH and row.vendorCount==expectedNPC and row.purchaseCost==expectedCost)
                  assert(row.purchaseChanged and not row.inventoryUnknown)
                  assert(pf.ShoppingSourceDetail(row):find(ns.L['已有材料已抵扣；按原计划货源和报价计算待购费用。'],1,true))
                  local vendors=pf.VendorPurchases('alchemy')
                  assert(#vendors==1 and vendors[1].missing==expectedNPC and vendors[1].cost==10)
                  pf.ImportShoppingList('alchemy','Alchemy')
                  assert(#imported==(expectedAH>0 and 1 or 0))
                  if expectedAH>0 then assert(imported[1].need==expectedAH)end
                  local current=pf.ShoppingList('alchemy',true)
                  assert(current[1].need==needed and current[1].have==owned and not current[1].planPurchases)
                  assert(frozen.total==expectedPlanCost and #frozen.executionSteps==1)
                ''')

    def test_npc_whole_pack_surplus_is_not_confused_with_recipe_demand(self):
        self.prepare(4,0)
        self.lua.execute('''
          local row=pf.ShoppingList('alchemy')[1]
          assert(row.need==4 and row.materialNeed==4 and row.missing==4)
          assert(row.planPurchaseCount==5 and row.purchaseCount==5 and row.packSurplus==1)
          assert(row.planPurchaseCost==10 and row.purchaseCost==10)
          local text=pf.ShoppingSourceText(row)
          assert(text:find('×5',1,true) and text:find('10c',1,true))
          assert(text:find(format(ns.L['整包余量 %d'],1),1,true))
          pf.ImportShoppingList('alchemy','Alchemy');assert(#imported==0)
        ''')

    def test_current_npc_replacement_covers_lost_auction_stock_without_a_false_block(self):
        self.prepare()
        self.lua.execute('''
          ns.AuctionBridge.GetAuctionSupply=function()return {quantity=0}end
          local row=pf.ShoppingList('alchemy')[1]
          assert(row.ahCount==0 and row.vendorCount==10 and row.purchaseCost==20)
          assert(row.purchaseChanged and row.supplyChanged and row.packSurplus==3)
          assert(not row.auctionShortage and not row.auctionUnknown and (row.purchaseUncovered or 0)==0)
          local text=pf.ShoppingSourceDetail(row)
          assert(text:find(ns.L['拍卖行可购数量已变化；待购数量按原计划货源和报价重新分配。'],1,true))
          assert(not text:find(ns.L['拍卖行可购数量不足，无法继续此配方；请在 Auctionator 重新完整扫描或改用其他配方。'],1,true))
          assert(row.planAHCount==2 and row.planVendorCount==5 and row.planPurchaseCost==12)
          pf.ImportShoppingList('alchemy','Alchemy');assert(#imported==0)
          assert(pf.VendorPurchases('alchemy')[1].missing==10)
        ''')

    def test_expired_mixed_auction_quantity_is_unknown_without_changing_the_frozen_receipt(self):
        self.prepare()
        self.lua.execute('''
          ns.AuctionBridge.GetAuctionSupply=function()return nil end
          ns.AuctionBridge.GetAuctionSupplyStatus=function()return 'expired'end
          local row=pf.ShoppingList('alchemy')[1]
          assert(row.ahCount==2 and row.vendorCount==5 and row.auctionUnknown and row.supplyStatus=='expired')
          assert(row.availableCount==nil and not row.supplyObserved)
          assert(row.planPurchaseCost==12 and row.purchaseCost==12)
          assert(pf.ShoppingSourceText(row):find(ns.L['库存未知'],1,true))
          assert(pf.ShoppingSourceDetail(row):find(ns.L['拍卖行可购数量未知，当前仅按价格估算；请在 Auctionator 重新完整扫描。'],1,true))
        ''')

    def test_unreadable_character_stock_never_becomes_zero_or_an_auction_export(self):
        self.prepare()
        self.lua.execute('''
          C_Item.GetItemCount=function()error('client count unavailable')end;GetItemCount=nil
          messages={};DEFAULT_CHAT_FRAME={AddMessage=function(_,text)messages[#messages+1]=text end}
          local row=pf.ShoppingList('alchemy')[1]
          assert(row.inventoryUnknown and row.haveKnown==false and row.missing==nil)
          assert(row.purchaseCount==nil and row.purchaseCost==nil and #row.purchases==0)
          assert(row.planPurchaseCount==7 and row.planPurchaseCost==12)
          pf.ImportShoppingList('alchemy','Alchemy');assert(#imported==0 and #messages==1)
          assert(messages[1]:find(ns.L['背包或银行数量未能读取，无法确认还需购买多少。'],1,true))
        ''')

    def test_comparison_reserves_frozen_pattern_stock_and_cost_without_applying_its_purchases(self):
        self.prepare()
        self.lua.execute('''
          local plan=ns.ProfExecution.GetPlan('alchemy')
          plan.formulas={{id=11,count=1,cost=3,source='ah',recipeKey='other:999',
            recipes={{key='other:999'}},costComplete=true}}
          captured=ns.ProfEconomy.Index(fixture())
          captured.auctionSupply={[11]={quantity=5}}
          captured.known['other:999']=false
          ns.ProfEconomy.Capture=function()return captured end
          ns.IdleJobs.Add=function(fn)previewPump=fn end
          debugprofilestop=function()return 0 end
          ns.ProfRouteSolver.NewProcurementJob=function(snapshot,demands)
            previewSnapshot=snapshot;previewDemands=demands
            return {result={feasible=true,costComplete=true,total=8,
              mats={{id=11,count=7,cost=8,source='vendor',npcID=99}}}}
          end
          ns.ProfRouteSolver.Run=function()return true end
          local before=pf.ShoppingList('alchemy')[1]
          pf.ProcureStart();assert(previewPump and previewPump())
          assert(previewSnapshot~=captured and previewSnapshot.auctionSupply[11].quantity==4)
          assert(previewSnapshot.known['other:999'] and captured.known['other:999']==false)
          assert(captured.auctionSupply[11].quantity==5 and previewDemands[11]==7)
          assert(pf.procureRes.notApplied and pf.procureRes.formulaBudget==3 and pf.procureRes.comparisonTotal==11)
          local after=pf.ShoppingList('alchemy')[1]
          assert(after.planPurchaseCost==before.planPurchaseCost and after.purchaseCost==before.purchaseCost)
          assert(after.vendorCount==before.vendorCount and after.ahCount==before.ahCount)
          assert(ns.ProfExecution.GetPlan('alchemy')==plan and plan.total==12)
        ''')


    def test_comparison_does_not_hide_unbuyable_original_auction_patterns(self):
        self.prepare()
        self.lua.execute('''
          ns.ProfExecution.GetPlan('alchemy').formulas={{id=11,count=1,cost=3,source='ah',recipeKey='other:999'}}
          local captured=ns.ProfEconomy.Index(fixture());captured.auctionSupply={[11]={quantity=0}}
          ns.ProfEconomy.Capture=function()return captured end
          ns.IdleJobs.Add=function(fn)previewPump=fn end
          debugprofilestop=function()return 0 end
          ns.ProfRouteSolver.NewProcurementJob=function()return {result={feasible=true,costComplete=true,
            total=70,mats={{id=11,count=7,cost=70,source='vendor'}}}}end
          ns.ProfRouteSolver.Run=function()return true end
          pf.ProcureStart();assert(previewPump())
          assert(pf.procureRes.notApplied and pf.procureRes.comparisonCanBuy==false)
          local diagnostic=pf.procureRes.comparisonFormulaDiagnostics[1]
          assert(diagnostic.code=='auctionSupplyLimited'and diagnostic.item==11 and diagnostic.available==0)
          assert(captured.auctionSupply[11].quantity==0 and not captured.known['other:999'])
        ''')


if __name__=='__main__':
    unittest.main()
