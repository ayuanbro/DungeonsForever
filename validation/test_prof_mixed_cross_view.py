"""One real mixed-purchase plan stays consistent through route, shop and HUD."""
import unittest

import test_prof_ui_fusion as ui


class MixedPurchaseCrossViewTests(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_default_route_shop_and_hud_keep_one_frozen_mixed_purchase_plan(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
          PD.autoPage='route'
          DungeonsForeverDB.prof.lvTarget.alchemy=8
          ns.ProfVendorNames={[7]='Supplier'}
          ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n)..'c'end
          local supply={quantity=2,complete=true,ownerExcluded=true,source='client-auction-results',
            observedAt=1000,expiresAt=2800}
          mixedSnapshot=fixture();mixedSnapshot.stamp=1000;mixedSnapshot.prices[11]=1
          mixedSnapshot.auctionSupply={[11]=supply}
          mixedSnapshot.offers={[11]={{npcID=7,price=10,quantity=5,unlimited=true,
            stock=-1,maxStock=-1,stockStatus='unlimited'}}}
          ns.ProfEconomy.Capture=function(_,opts)
            return ns.ProfEconomy.Index(ns.ProfEconomy.Copy(opts and opts.snapshot or mixedSnapshot))
          end
          ns.ProfEconomy.LearningPolicyFingerprint=function()return 'cross-view-policy'end
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==11 then return supply end end,
            DoImport=function(name,items)imported={name=name,items=items}end}
          ns.ProfRouteAuto.AHPriceOf=function(id)if id==11 then return 1 end end
          GetItemCount=function()return 0 end
          C_Item.GetItemCount=function()return 0 end
          local computed,job=ns.ProfRouteSolver.Compute('alchemy',{snapshot=mixedSnapshot,
            start=1,target=8,autoCraftTools=false,recoveryEnabled=false})
          assert(not job.error and computed.targetReached and computed.purchaseVerified)
          assert(computed.total==12 and computed.ahTotal==2 and computed.vendorTotal==10)
          assert(#computed.mats==2 and #computed.steps==1 and computed.steps[1][4]==7)
          computed.planID='mixed-cross-view'
          computed.learningPolicyFingerprint=ns.ProfEconomy.LearningPolicyFingerprint()
          local run=assert(ns.ProfExecution.Bind('alchemy',computed))
          frozenPlan=run.plan
          local rows={};PD.RowsLeveling(rows)
          local route={}
          for _,row in ipairs(rows)do if row.lvstep then route[#route+1]=row end end
          assert(#route==1 and route[1].cost=='12c' and route[1].trackCur)
          assert(PD.autoSnapshot==frozenPlan and PD.lvSummary.total==12)
          for _,group in ipairs({false,true})do
            PD.shopGroup=group;local shop={};PD.RowsAutoShop(shop,frozenPlan)
            local sources={};local count=0
            for _,row in ipairs(shop)do
              if row.it and row.it[1]==11 then
                count=count+1
                if row.tag.text==ns.L['拍卖行'] then
                  assert(row.right:find('×2',1,true) and row.right2=='2c')
                  sources.ah=true
                else
                  assert(row.tag.text==ns.L['NPC购买'])
                  assert(row.right:find('×5',1,true) and row.right2=='10c')
                  sources.vendor=true
                end
              elseif row.text==ns.L['拍卖行购入'] then assert(row.right=='2c')
              elseif row.text==ns.L['商人直售购入'] then assert(row.right=='10c')end
            end
            assert(count==2 and sources.ah and sources.vendor)
            assert(not PD.procureView and not PD.procureRes and not PD.procureJob,
              'default shopping layout started an optimization')
          end
        ''')
        self.load((ui.ROOT / 'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local pf=ns.ProfFollow
          pf.InvalidateRoute()
          local list=pf.ShoppingList('alchemy')
          assert(#list==1 and list[1].id==11)
          local entry=list[1]
          assert(entry.need==7 and entry.materialNeed==7 and entry.have==0)
          assert(entry.source=='mixed' and entry.planPurchaseCount==7 and entry.planPurchaseCost==12)
          assert(entry.purchaseCount==7 and entry.purchaseCost==12)
          assert(entry.planAHCount==2 and entry.ahCount==2
            and entry.planVendorCount==5 and entry.vendorCount==5)
          local plannedCount,plannedCost=0,0
          for _,purchase in ipairs(entry.planPurchases)do
            plannedCount=plannedCount+purchase.count;plannedCost=plannedCost+purchase.cost
          end
          assert(#entry.planPurchases==2 and plannedCount==7 and plannedCost==12)
          local bySource={};local total=0
          for _,purchase in ipairs(entry.purchases)do
            bySource[purchase.source]=purchase;total=total+purchase.cost
          end
          assert(#entry.purchases==2 and total==frozenPlan.total)
          assert(bySource.ah.count==2 and bySource.ah.cost==2)
          assert(bySource.vendor.count==5 and bySource.vendor.cost==10
            and bySource.vendor.npcID==7 and bySource.vendor.bundleSize==5)
          local source=pf.ShoppingSourceText(entry)
          for _,text in ipairs({ns.L['拍卖行'],'2','2c','5','10c'})do
            assert(source:find(text,1,true),'HUD source text lost '..text)
          end
          pf.ImportShoppingList('alchemy','Alchemy')
          assert(imported and imported.name=='Alchemy' and #imported.items==1)
          assert(imported.items[1].name=='Item11' and imported.items[1].need==2)
          assert(not pf.procureRes and not pf.procureJob,'HUD required optimization for normal procurement')
          assert(ns.ProfExecution.GetPlan('alchemy')==frozenPlan and frozenPlan.total==12)
        ''')


if __name__ == '__main__':
    unittest.main()
