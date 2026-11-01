"""HUD shopping and Auctionator export share the route's purchase decisions."""
import unittest
import test_prof_execution_fusion as execution


class HUDShoppingSourceTests(unittest.TestCase):
    setUp=execution.ExecutionFusionTests.setUp
    load=execution.ExecutionFusionTests.load
    load_follow=execution.ExecutionFusionTests.load_follow

    def follow(self):
        self.load_follow()
        self.lua.execute('''
          ns.ProfHost.DG.ItemName=function(id)return 'Item'..id,true end
          ns.ProfHost.DG.RequestItem=function()end
          ns.ProfRouteAuto.MoneyStr=function(n)return tostring(n)..'c'end
          ns.ProfVendorNames={[1]='Supplier'}
          ns.ProfEconomy.Known=function()return false end
          ns.AuctionBridge={DoImport=function(name,items)imported=items end}
        ''')

    def test_default_list_has_npc_material_and_pattern_source_stock_cost(self):
        self.follow()
        self.lua.execute('''
          local p=fixture();p.planID='pattern'
          p.mats={{id=20,count=3,source='vendor',npcID=1,unlimited=true}}
          p.formulas={{id=400,spell=101,count=1,cost=50,source='vendor',npcID=1,limited=1}}
          xp.StartNew('alchemy',p);pf.InvalidateRoute()
          local list=pf.ShoppingList('alchemy');assert(#list==2 and not pf.procureRes)
          assert(list[1].id==20 and list[1].source=='vendor' and list[1].unlimited and list[1].need==3)
          assert(list[2].id==400 and list[2].formula and list[2].formulaNeed==1 and list[2].need==1)
          assert(list[2].source=='vendor' and list[2].npcID==1 and list[2].limited==1)
          local materialText=pf.ShoppingSourceText(list[1])
          assert(materialText:find('Supplier ×3',1,true) and materialText:find('不限量',1,true))
          local formulaText=pf.ShoppingSourceText(list[2])
          assert(formulaText:find('Supplier ×1',1,true) and formulaText:find('限量',1,true) and formulaText:find('50c',1,true))
          pf.ImportShoppingList('alchemy','Alchemy');assert(#imported==0)
          ns.ProfEconomy.Known=function()return true end
          assert(#pf.ShoppingList('alchemy')==1,'learned recipe still buys a pattern')
        ''')

    def test_auction_pattern_is_imported_once_and_owned_pattern_is_not_missing(self):
        self.follow()
        self.lua.execute('''
          local p=fixture();p.planID='auction-pattern'
          p.mats={{id=20,count=3,source='vendor',npcID=1,unlimited=true}}
          local f={id=400,spell=101,count=1,cost=50,source='ah'}
          p.formulas={f,f}
          xp.StartNew('alchemy',p);pf.InvalidateRoute()
          local list=pf.ShoppingList('alchemy');assert(#list==2 and list[2].need==1)
          pf.ImportShoppingList('alchemy','Alchemy')
          assert(#imported==1 and imported[1].name=='Item400' and imported[1].need==1)
          bag[400]=1;pf.ImportShoppingList('alchemy','Alchemy');assert(#imported==0)
        ''')

    def test_full_list_exports_leaves_and_keeps_current_step_raw_materials(self):
        self.follow()
        self.lua.execute('''
          local p=fixture();p.planID='chain';local a=p.executionSteps[1]
          a.allocations={{consumerID='b',itemID=10,count=6}}
          local b={1,3,102,3,segmentID='b',profession='alchemy',recipe=recipes[102],item=11,
            goalSkill=3,expectedGain=2,expectedCrafts=3,attemptLimit=3,outputMin=2,outputMax=2,
            requiredOutputs={[11]=6},materialMinCrafts=3,allocations={}}
          p.executionSteps={a,b};p.steps={a,b}
          p.mats={{id=20,count=2,source='vendor',npcID=1,unlimited=true},
            {id=20,count=1,source='ah'}}
          xp.StartNew('alchemy',p);pf.InvalidateRoute()
          local list=pf.ShoppingList('alchemy')
          assert(#list==1 and list[1].id==20 and list[1].need==3 and list[1].source=='mixed')
          local now=pf.ShoppingList('alchemy',true);assert(#now==1 and now[1].need==3)
          pf.ImportShoppingList('alchemy','Alchemy')
          assert(#imported==1 and imported[1].name=='Item20' and imported[1].need==1)
          for _,e in ipairs(list)do assert(e.id~=10,'planned crafted intermediate became a purchase')end
        ''')

    def test_expired_auction_quantity_is_unknown_in_hud_instead_of_reusing_old_count(self):
        self.follow()
        self.lua.execute('''
          local p=fixture();p.planID='stale-quantity'
          p.mats[1].availableCount=500;p.mats[1].supplyObserved=true
          xp.StartNew('alchemy',p);pf.InvalidateRoute()
          ns.AuctionBridge.GetAuctionSupply=function()return nil end
          local entry=pf.ShoppingList('alchemy')[1]
          assert(entry.availableCount==nil and not entry.supplyObserved)
          assert(pf.ShoppingSourceText(entry):find('库存未知',1,true))
          ns.AuctionBridge.GetAuctionSupply=function()return {quantity=0}end
          local row=pf.ShoppingList('alchemy')[1]
          assert(row.availableCount==0 and (row.purchaseUncovered or 0)>0)
        ''')

    def test_material_optimization_never_treats_patterns_as_generic_materials(self):
        self.follow()
        self.lua.execute('''
          local p=fixture();p.planID='optimize-leaves'
          p.formulas={{id=400,spell=101,count=1,cost=50,source='ah'}}
          xp.StartNew('alchemy',p);pf.InvalidateRoute()
          debugprofilestop=function()return 0 end
          ns.ProfEconomy.Capture=function()return {}end
          ns.ProfEconomy.ConsiderAuctionSupply=function()return true end
          ns.ProfRouteSolver={Run=function()end,NewProcurementJob=function(snap,demands)
            captured=demands;return {}end}
          ns.IdleJobs={Add=function()end}
          pf.ProcureStart();assert(pf.procureJob)
          assert(coroutine.resume(pf.procureJob.co))
          assert(captured[20]==3 and captured[400]==nil)
        ''')

    def test_first_aid_hud_refuses_legacy_automatic_execution_without_erasing_it(self):
        self.follow()
        self.lua.execute('''
          local p=fixture();p.planID='old-first-aid'
          p.executionSteps[1].profession='first-aid'
          local old=xp.StartNew('first-aid',p)
          DungeonsForeverDB.prof.follow['Test-Realm']={slug='first-aid',skill=1,step=1,t0=1000}
          pf.InvalidateRoute();pf.Sync()
          assert(pf.pendingPlans['first-aid'].diagnostics[1].code=='fixedOnlyChanged')
          assert(xp.GetRun('first-aid')==old and old.planID=='old-first-aid')
        ''')


if __name__=='__main__':unittest.main()
