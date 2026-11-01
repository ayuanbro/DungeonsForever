"""Repeated crafts must amortize NPC packs across the actual route demand."""
import unittest

import test_prof_route_plans as routes
import test_prof_ui_fusion as ui


class RouteWideVendorPurchasesTests(unittest.TestCase):
    setUp = routes.NativeRoutePlansTests.setUp

    def test_reported_vial_quantities_across_all_route_strategies(self):
        self.lua.execute('''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            for _,row in ipairs({{3371,222,4,18,800,220,2},
                                {3372,107,45,189,4059,105,2},
                                {8925,140,531,2368,66304,140,0}})do
              local id,need,price,pack=row[1],row[2],row[3],row[4]
              local s=fixture();s.recipes[1].mats={{id,1}}
              s.recipes[1].yellow=300;s.recipes[1].green=300
              s.prices={[id]=price};s.offers={[id]={{npcID=7,price=pack,
                quantity=5,unlimited=true,reference=true,source='supply-verified'}}}
              -- Even a one-node search must publish a properly priced incumbent.
              local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=need+1,
                scheme=scheme,autoCraftTools=false,recoveryEnabled=false,maxNodes=1})
              local npc,ah=0,0
              for _,m in ipairs(r.mats)do
                if m.source=='vendor' then npc=npc+m.count else ah=ah+m.count end
              end
              assert(r.targetReached and r.costComplete)
              assert(r.total==row[5] and npc==row[6] and ah==row[7],
                scheme..':'..id..':'..r.total..':'..npc..':'..ah)
              assert(r.crafts==need,'purchase repair changed the crafting route')
            end
          end
        ''')

    def test_shipped_suppliers_and_a_fixed_recipe_sequence(self):
        for path in ('Core/Data/Data_ProfMaterialSupply.lua', 'Core/ProfSupply.lua',
                     'Core/VendorPriceDB.lua'):
            self.load((routes.ROOT / path).read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          ns.DB=function()return DungeonsForeverDB end
          local s=fixture();s.recipes[1].mats={{3371,1}};s.prices={[3371]=4}
          s.offers={[3371]=ns.VendorPriceDB.GetOffers(3371)}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=31,
            fixedSteps={{1,15,101,14},{15,31,101,16}},recoveryEnabled=false})
          assert(r.targetReached and r.total==108 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].count==30 and r.mats[1].unlimited)
          assert(r.mats[1].npcID and r.mats[1].quoteSource=='supply-verified')
        ''')

    def test_finite_auction_stock_and_genuinely_cheaper_auction_remain_valid(self):
        self.lua.execute('''
          for _,supply in ipairs({2,30})do
            local s=fixture();s.prices[11]=1
            s.offers={[11]={{npcID=7,price=15,quantity=5,unlimited=true}}}
            s.auctionSupply={[11]={quantity=supply,complete=true,source='observed'}}
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=13,
              scheme='matcost',autoCraftTools=false,recoveryEnabled=false})
            assert(r.targetReached and r.ahTotal==(supply==2 and 2 or 12))
            assert(r.total==(supply==2 and 32 or 12))
          end
        ''')

    def test_pack_surplus_and_execution_inventory_are_not_bought_twice(self):
        self.lua.execute('''
          local s=fixture();s.prices[11]=4
          s.offers={[11]={{npcID=7,price=18,quantity=5,unlimited=true}}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=13,
            scheme='matcost',executionInventory={[11]=2},autoCraftTools=false,recoveryEnabled=false})
          assert(r.targetReached and r.total==36 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].count==10 and r.crafts==12)
        ''')

    def test_unavailable_and_uncertain_suppliers_do_not_replace_reliable_purchases(self):
        self.lua.execute('''
          for _,field in ipairs({'available','purchasable','unlimited','estimated','hasExtendedCost'})do
            local s=fixture();s.prices[11]=4
            local offer={npcID=7,price=1,quantity=5,unlimited=true}
            offer[field]=field=='estimated' or field=='hasExtendedCost'
            s.offers={[11]={offer}}
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=13,
              scheme='matcost',autoCraftTools=false,recoveryEnabled=false})
            assert(r.targetReached and r.total==48 and r.ahTotal==48,field)
          end
        ''')

    def test_formula_copies_reserve_their_share_of_auction_supply(self):
        self.lua.execute('''
          local s=fixture();s.known={};s.recipes[1].formula=11
          s.recipes[1].source={drops={{npc='Reference drop'}}}
          s.prices[11]=4
          s.formulaOffers={[11]={{npcID=9,price=100,quantity=1,unlimited=true}}}
          s.offers={[11]={{npcID=7,price=18,quantity=5,unlimited=true}}}
          s.stamp=1000
          s.auctionSupply={[11]={quantity=3,complete=true,observedAt=900,
            ownerExcluded=true,source='client-auction-results'}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=13,
            scheme='matcost',autoCraftTools=false,recoveryEnabled=false})
          assert(r.targetReached and r.total==48 and r.formulaAHTotal==4)
          local count=0
          for _,a in ipairs(r.actions)do
            if a.source=='ah' then count=count+a.count end
          end
          assert(count==3,'material repurchase reused the formula auction copy')
        ''')

    def test_old_frozen_plan_requires_recalculation_without_deleting_execution(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local opts={start=1,target=13,recoveryEnabled=false}
          local plan=finish('alchemy',opts)
          local run=assert(ns.ProfExecution.Bind('alchemy',plan))
          local frozen=run.plan
          frozen.procurementPolicyVersion=ns.ProfRouteSolver.ProcurementPolicyVersion-1
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==frozen and frozen.stale)
          assert(run.plan==frozen and ns.ProfExecution.GetPlan('alchemy')==frozen)
        ''')


class RouteWideVendorCrossViewTests(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_repaired_route_shop_hud_and_export_share_the_same_purchases(self):
        self.lua.execute('''
          PD.Wrap=function(text)return {text}end
          ns.ProfVendorNames={[7]='Supplier'}
          ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n)..'c'end
          local supply={quantity=222,complete=true,ownerExcluded=true,source='client-auction-results',
            observedAt=1000,expiresAt=2800}
          vialSnapshot=fixture();vialSnapshot.stamp=1000;vialSnapshot.prices[11]=4
          vialSnapshot.recipes[1].yellow=300;vialSnapshot.recipes[1].green=300
          vialSnapshot.auctionSupply={[11]=supply}
          vialSnapshot.offers={[11]={{npcID=7,price=18,quantity=5,unlimited=true}}}
          ns.ProfEconomy.Capture=function(_,opts)
            return ns.ProfEconomy.Index(ns.ProfEconomy.Copy(opts and opts.snapshot or vialSnapshot))
          end
          ns.ProfEconomy.LearningPolicyFingerprint=function()return 'vial-policy'end
          ns.AuctionBridge={GetAuctionSupply=function()return supply end,
            DoImport=function(_,items)imported=items end}
          ns.ProfRouteAuto.AHPriceOf=function()return 4 end
          GetItemCount=function()return 0 end;C_Item.GetItemCount=GetItemCount
          local plan=ns.ProfRouteAuto.Compute('alchemy',{snapshot=vialSnapshot,start=1,target=223,
            scheme='matcost',autoCraftTools=false,recoveryEnabled=false})
          assert(plan.targetReached and plan.total==800 and plan.ahTotal==8 and plan.vendorTotal==792)
          plan.planID='vial-route';plan.learningPolicyFingerprint='vial-policy'
          assert(ns.ProfExecution.Bind('alchemy',plan))
          for _,group in ipairs({false,true})do
            PD.shopGroup=group;local rows={};PD.RowsAutoShop(rows,plan)
            local count=0
            for _,row in ipairs(rows)do if row.it and row.it[1]==11 then
              count=count+1
              if row.tag.text==ns.L['拍卖行'] then
                assert(row.right:find('×2',1,true) and row.right2=='8c')
              else
                assert(row.tag.text==ns.L['NPC购买'])
                assert(row.right:find('×220',1,true) and row.right2=='792c')
              end
            end end
            assert(count==2)
          end
        ''')
        self.load((ui.ROOT / 'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local pf=ns.ProfFollow;pf.InvalidateRoute()
          local list=pf.ShoppingList('alchemy')
          assert(#list==1 and list[1].need==222)
          assert(list[1].vendorCount==220 and list[1].ahCount==2 and list[1].purchaseCost==800)
          pf.ImportShoppingList('alchemy','Alchemy')
          assert(#imported==1 and imported[1].need==2)
        ''')


if __name__ == '__main__':
    unittest.main()
