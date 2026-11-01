"""All native NPC materials, factions/locales, route modes and frozen HUD use.

Character state and auction offers are simulated. No Core/Data writes occur.
"""
import unittest

import audit_prof_vendor_routes as audit
import test_prof_ui_fusion as ui


class NativeMaterialMatrixTests(unittest.TestCase):
    def test_every_native_material_in_both_factions_and_three_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            for faction in ('A', 'H'):
                with self.subTest(locale=locale, faction=faction):
                    result = audit.material_matrix(locale, faction)
                    self.assertEqual(result['failures'], [])
                    self.assertEqual(len(result['inventory']), 15)

    def test_every_supplier_backed_reagent_survives_repeated_crafts_in_all_strategies(self):
        for faction in ('A', 'H'):
            lua = audit.runtime(faction=faction)
            lua.execute('''
              local inventory=auditInventory();local tested=0
              for _,profession in ipairs(inventory)do
                if profession.steps>0 and profession.slug~='first-aid' and profession.slug~='poisons' then
                  for _,material in ipairs(profession.materials)do if material.used and material.supplierCount>0 then
                    local id=material.id;local offer=material.offers[1];local pack=offer.quantity
                    local per=math.max(1,math.ceil(pack/20));local crafts=math.ceil((pack*3+2)/per)
                    local need=crafts*per;local price=math.max(1,math.ceil(offer.price/pack*1.25))
                    local expected=math.huge
                    for bundles=0,math.ceil(need/pack)do
                      local tail=math.max(0,need-bundles*pack)
                      expected=math.min(expected,bundles*offer.price+tail*price)
                    end
                    for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
                      local slug=profession.slug
                      local s={recipes={{profession=slug,spell=2000000001,count=1,item=2000000002,
                        learn=1,yellow=300,green=300,grey=301,cooldown=false,mats={{id,per}}}},
                        known={[slug..':2000000001']=true},prices={[id]=price},
                        offers={[id]=material.offers},faction=auditFaction,professions={[slug]={cur=1,max=300}}}
                      local plan,job=ns.ProfRouteAuto.Compute(slug,{snapshot=s,start=1,target=crafts+1,
                        scheme=scheme,autoCraftTools=false,recoveryEnabled=false,maxNodes=1})
                      assert(not job.error and plan.targetReached,slug..':'..id..':'..scheme)
                      assert(math.abs(plan.total-expected)<1e-6,
                        slug..':'..id..':'..scheme..':'..plan.total..' expected '..expected)
                      tested=tested+1
                    end
                  end end
                end
              end
              assert(tested>200,'the native material coverage unexpectedly shrank')
            ''')

    def test_catalogue_gaps_stay_unknown_to_npc_pricing_despite_live_quotes(self):
        lua = audit.runtime()
        lua.execute('''
          local ids={2723,2928,2930,5173,8923,8924}
          for _,id in ipairs(ids)do
            local before=ns.VendorPriceDB.GetOffers(id)
            for _,offer in ipairs(before)do assert(offer.priceOnly or not offer.unlimited)end
          end
          DungeonsForeverDB.profVendorOffers={};DungeonsForeverDB.vendorPrices={}
          for _,id in ipairs(ids)do
            DungeonsForeverDB.profVendorOffers[id]={{npcID=999999,price=10,quantity=5,
              unlimited=true,available=true,purchasable=true,source='merchant',verifiedAt=1000,
              character='Test-Realm',reputationKey=''}}
            DungeonsForeverDB.vendorPrices[id]={p=2,t=1000}
          end
          Auctionator.API.v1.GetVendorPriceByItemID=function()error('live vendor cache used')end
          GetMerchantNumItems=function()error('live merchant was scanned')end
          for _,id in ipairs(ids)do
            assert(ns.VendorPriceDB.GetPrice(id)==nil and #ns.VendorPriceDB.GetSuppliers(id)==0)
            assert(ns.ProfRouteAuto.NPCBuyPriceOf(id)==nil)
            local rows,cost,complete=ns.ProfRouteAuto.MaterialPurchases(id,10)
            assert(complete and cost==100000 and #rows==1 and rows[1].source=='ah')
            assert(rows[1].count==10,'normal auction purchasing was changed')
          end
        ''')

    def test_cached_vendor_unit_prices_reach_capture_fixed_and_optimized_costs(self):
        lua = audit.runtime()
        lua.execute('''
          local ids={2723,2928,2930,5173,8923,8924};local cached={}
          for _,id in ipairs(ids)do cached[id]=2 end
          Auctionator.API.v1.GetVendorPriceByItemID=function(caller,id)
            assert(caller=='DungeonsForever');return cached[id]
          end
          GetMerchantNumItems=function()error('the addon must not scan merchants')end
          ns.ProfRouteAuto.AHPriceOf=function()return 100 end
          for _,id in ipairs(ids)do
            assert(ns.ProfRouteAuto.NPCBuyPriceOf(id)==2)
            local rows,cost,complete=ns.ProfRouteAuto.MaterialPurchases(id,7)
            assert(complete and cost==14 and #rows==1 and rows[1].source=='vendor')
            assert(rows[1].count==7 and rows[1].unit==2 and rows[1].quoteSource=='auctionator-vendor')
            assert(rows[1].priceBasis=='cached-unit' and not rows[1].npcID)
          end
          -- Cache priority also applies when the collected quote is cheaper.
          assert(ns.VendorPriceDB.GetPrice(3371)<8)
          cached[3371]=8
          local captured=auditSnapshot('alchemy')
          assert(captured.vendorItems[3371] and #captured.offers[3371]==1 and captured.offers[3371][1].unit==8,
            'live capture did not prioritize the cache quote')
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim','fixed'})do
            local s={recipes={{profession='alchemy',spell=2000000001,count=1,item=2000000002,
              learn=1,yellow=300,green=300,grey=301,cooldown=false,mats={{3371,1}}}},
              known={['alchemy:2000000001']=true},prices={[3371]=100},
              offers={[3371]=captured.offers[3371]},faction='A',professions={alchemy={cur=1,max=300}}}
            local opts={snapshot=s,start=1,target=5,scheme=scheme,
              autoCraftTools=false,recoveryEnabled=false,maxNodes=1}
            if scheme=='fixed' then opts.fixedSteps={{1,5,2000000001,4}}end
            local plan,job=ns.ProfRouteAuto.Compute('alchemy',opts)
            assert(not job.error and plan.targetReached and plan.costComplete,scheme)
            assert(plan.total==32 and plan.ahTotal==0 and plan.mats[1].count==4,scheme)
            assert(plan.mats[1].quoteSource=='auctionator-vendor' and not plan.mats[1].npcID)
          end
          ns.ProfRouteAuto.AHPriceOf=function()return 1 end
          local rows,cost,complete=ns.ProfRouteAuto.MaterialPurchases(2723,7)
          assert(complete and cost==7 and rows[1].source=='ah','cheaper auction was ignored')
          cached[2723]=0;ns.ProfRouteAuto.Invalidate()
          assert(ns.ProfRouteAuto.NPCBuyPriceOf(2723)==0)
          rows,cost,complete=ns.ProfRouteAuto.MaterialPurchases(2723,7)
          assert(complete and cost==0 and rows[1].source=='vendor')
          assert(DungeonsForeverDB.profVendorOffers==nil and DungeonsForeverDB.vendorPrices==nil)
        ''')

    def test_native_full_routes_and_hud_agree_before_any_crafts(self):
        for slug in ('alchemy', 'enchanting'):
            with self.subTest(profession=slug):
                lua = audit.runtime()
                snapshot = lua.eval('auditSnapshot')(slug)
                lua.globals().auditSnap = snapshot
                lua.execute('observedKnown={};for _,r in ipairs(auditSnap.recipes)do observedKnown[r.spell]=true end')
                plan = lua.execute('''
                  local slug=...
                  local result=ns.ProfRouteAuto.Compute(slug,{snapshot=auditSnap,start=1,target=300,
                    scheme='matcost',autoCraftTools=false,recoveryEnabled=false,maxNodes=1})
                  return result
                ''', slug)
                self.assertTrue(plan['targetReached'])
                self.assertEqual(audit.check_plan(lua, plan, snapshot, slug), [])


class FutureHUDMaterialTests(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_current_progress_changes_only_current_demand_and_keeps_future_budget(self):
        self.lua.execute('''
          local s=fixture();s.recipes[1].grey=3;s.recipes[1].yellow=3;s.recipes[1].green=3
          s.recipes[2]={profession='alchemy',spell=102,item=20,count=1,mats={{12,1}},
            learn=3,yellow=100,green=200,grey=300,cooldown=false}
          s.known['alchemy:102']=true;s.prices={[11]=100,[12]=100}
          s.offers={[11]={{npcID=7,price=2,quantity=1,unlimited=true}},
            [12]={{npcID=7,price=3,quantity=1,unlimited=true}}}
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(ns.ProfEconomy.Copy(s))end
          local plan=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=5,
            autoCraftTools=false,recoveryEnabled=false})
          assert(plan.targetReached and plan.total==10)
          assert(ns.ProfExecution.Bind('alchemy',plan))
          GetItemCount=function()return 0 end;C_Item.GetItemCount=GetItemCount
          ns.AuctionBridge={DoImport=function(_,items)imported=items end}
        ''')
        self.load((ui.ROOT / 'Core/ProfFollow.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local pf=ns.ProfFollow;pf.InvalidateRoute()
          local function needs()
            local rows={};for _,row in ipairs(pf.ShoppingList('alchemy'))do rows[row.id]=row end
            return rows
          end
          local before=needs()
          assert(before[11].need==2 and before[12].need==2)
          assert(ns.ProfExecution.RecordAttempt('alchemy',101,'vendor-audit-cast'))
          skills.alchemy.cur=2;ns.ProfExecution.Sync('alchemy');pf.InvalidateRoute()
          local after=needs()
          assert(after[11].need==1 and after[12].need==2)
          assert(after[11].planVendorCount==2 and after[12].planVendorCount==2)
          pf.ImportShoppingList('alchemy','Alchemy');assert(#imported==0)
        ''')


if __name__ == '__main__':
    unittest.main()
