"""Recovery settings and quotes are frozen until explicit route recalculation."""
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT


class RecoveryCacheTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.lua.execute("""
          salePrice=2;captures=0
          function GetItemInfo(id)
            return 'Item'..id,nil,1,1,1,nil,nil,1,nil,nil,id==10 and salePrice or 0,nil,nil,0
          end
        """)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ('ProfEconomy.lua', 'ProfRecovery.lua', 'ProfRouteSolver.lua', 'ProfRouteAuto.lua'):
            self.load(str(ROOT / 'Core' / name))
        self.lua.execute("""
          ns.ProfEconomy.Capture=function(slug,opts)
            captures=captures+1
            local s=ns.ProfEconomy.Index(fixture())
            ns.ProfRecovery.Capture(s,opts)
            return s
          end
          ns.ProfEconomy.Professions=function()return {alchemy={cur=1,max=300}}end
        """)

    def test_settings_and_quotes_wait_for_manual_recalculate(self):
        self.lua.execute("""
          local ra=ns.ProfRouteAuto
          local r=finish('alchemy',{start=1,target=2})
          assert(r.recoveryRevision==1 and r.recoveryEnabled and r.recoveryOptimized)
          assert(r.purchaseTotal==7 and r.recoveryTotal==2 and r.netTotal==5)
          local count=captures;local scheduled=#queue
          salePrice=4
          local old=ra.Get('alchemy',{start=1,target=2})
          assert(old==r and old.stale and old.recoveryStale)
          assert(old.recoveryTotal==2 and captures==count and #queue==scheduled)
          DungeonsForeverDB.prof.recoveryEnabled=false
          assert(ra.Get('alchemy',{start=1,target=2})==r and captures==count)
          ra.Recalculate('alchemy',{start=1,target=2})
          local fresh=finish('alchemy',{start=1,target=2})
          assert(fresh~=r and not fresh.recoveryEnabled and not fresh.recoveryOptimized)
          assert(fresh.purchaseTotal==7 and fresh.recoveryTotal==4 and fresh.netTotal==3)
        """)

    def test_legacy_saved_plan_restores_as_stale_without_research(self):
        self.lua.execute("""
          original=finish('alchemy',{start=1,target=2})
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          local r=cache.routes[cache.active.alchemy].result
          r.recoveryRevision=nil;r.recoverySnapshot=nil;r.recoveryOptimized=nil
          captureCount=captures;queueCount=#queue
        """)
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute("""
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2})
          assert(r.cached and r.stale and r.recoveryStale)
          assert(not r.recoveryRevision and not r.recoveryOptimized)
          assert(r.total==7 and captures==captureCount and #queue==queueCount)
        """)

    def test_frozen_execution_keeps_estimate_and_record_after_input_change(self):
        self.load(str(ROOT / 'Core' / 'ProfExecution.lua'))
        self.lua.execute("""
          local ra=ns.ProfRouteAuto;local xp=ns.ProfExecution
          local r=finish('alchemy',{start=1,target=2})
          local run=assert(xp.Bind('alchemy',r));local frozen=xp.GetPlan('alchemy')
          local planID=frozen.planID;local casts=run.progressVersion
          salePrice=9;DungeonsForeverDB.prof.recoveryFeePercent=7
          local shown=ra.Get('alchemy',{start=1,target=2})
          assert(shown==frozen and shown.recoveryStale and shown.recoveryTotal==2)
          assert(shown.planID==planID and xp.GetRun('alchemy')==run and run.progressVersion==casts)
        """)

    def test_fixed_page_shop_and_hud_share_retained_quote_until_clear(self):
        self.lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,20,30,40,false,{{11,1}},nil,{}}}}}
          ns.EnsureProfRecipes=function()return ns.ProfRecipes end
          ns.ProfRouteAuto.AHPriceOf=function(id)return id==11 and 7 or nil end
          ns.ProfItemPrices={GetOffers=function(id)
            return id==11 and {{price=7,quantity=1,unlimited=true}} or {}
          end}
          local steps={{1,2,101,1,profession='alchemy'}}
          local ra=ns.ProfRouteAuto
          fixed=assert(ra.FixedSummary('alchemy',steps,{target=2}))
          assert(fixed.mode=='fixed' and fixed.total==7 and fixed.recoveryTotal==2)
          assert(not fixed.recoveryOptimized)
          local count=captures
          salePrice=5;DungeonsForeverDB.prof.recoveryEnabled=false
          assert(ra.FixedSummary('alchemy',steps,{target=2})==fixed)
          assert(fixed.recoveryTotal==2 and fixed.recoveryStale and captures==count)
          ra.ClearFixedSummary('alchemy')
          local fresh=assert(ra.FixedSummary('alchemy',steps,{target=2}))
          assert(fresh~=fixed and fresh.recoveryTotal==5 and not fresh.recoveryEnabled)
        """)
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute("""
          local r=ns.ProfRouteAuto.FixedSummary('alchemy',{{1,2,101,1,profession='alchemy'}},{target=2})
          assert(r.recoveryTotal==5 and r.mode=='fixed')
        """)

    def test_direct_fishing_reference_keeps_choices_and_frozen_sale_snapshot(self):
        self.load(str(ROOT / 'Core' / 'ProfFishing.lua'))
        self.lua.execute("""
          ns.ProfFishingRoutes={cookingSteps={{from=1,to=2,spell=101}},
            fish={[6291]={name='Fish',catchRate=1,minSkill=1,areas={{mapID=1,minSkill=1}}}}}
          local s={recipes={{profession='cooking',key='cooking:101',spell=101,item=10,count=1,
            learn=1,yellow=10,green=10,grey=10,mats={{6291,1}},cooldown=false}},
            professions={cooking={cur=1,max=300}},known={['cooking:101']=true},sellPrices={[10]=2}}
          local r=ns.ProfFishing.Compute({snapshot=s,start=1,target=2,recoveryEnabled=false})
          assert(r.targetReached and r.scheme=='fishing' and r.steps[1][3]==101 and r.steps[1][4]==1)
          assert(r.recoveryRevision==1 and not r.recoveryOptimized and not r.recoveryEnabled)
          assert(r.total==0 and r.recoveryTotal==2 and r.netTotal==-2 and #r.mats==0)
          salePrice=9;s.sellPrices[10]=9
          assert(r.recoveryTotal==2 and r.recoverySnapshot.quotes[10].npcUnit==2)
        """)


if __name__ == '__main__':
    unittest.main()
