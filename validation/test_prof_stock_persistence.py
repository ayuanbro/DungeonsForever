"""Persisted full-scan snapshots, reload reuse, and required scan provenance."""
import unittest
import test_prof_route_plans as routes
import test_prof_ui_fusion as ui
from test_prof_auction_supply import BRIDGE_MOCKS, LuaRuntime, ROOT
from lupa.lua51 import lua_type
from test_prof_auctionator_full_scan import SOURCE_MOCK


def plain(value):
    if lua_type(value) != 'table':
        return value
    return {key: plain(child) for key, child in value.items()}


def table(lua, value):
    if isinstance(value, dict):
        return lua.table_from({key: table(lua, child) for key, child in value.items()})
    return value


class StockPersistenceTests(unittest.TestCase):
    def boot(self, saved=None, stamp=10000):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(BRIDGE_MOCKS)
        if saved is not None:
            lua.globals().DungeonsForeverDB = table(lua, saved)
        lua.globals().clock = stamp
        lua.execute("""
          ns.IsForever=true
          ns.ProfModule={cur='alchemy',Setting=function(k,slug)
            local db=DungeonsForeverDB.prof
            local values=db.professionSettings and db.professionSettings[slug or ns.ProfModule.cur]
            local v=values and values[k]
            if v==nil then v=db[k]end
            return v==true
          end,
            ProfLearned=function()return {alchemy={cur=1,max=300}}end}
        """)
        lua.execute(SOURCE_MOCK)
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
            (ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        lua.execute("event('PLAYER_LOGIN')")
        return lua

    def scan(self, lua):
        lua.execute("""
          beginFull(4)
          sendFull({rawRow(11,8,56,'Seller'),rawRow(12,2,14,'Seller'),
            rawRow(10940,10,50,'Seller'),rawRow(9999,3,21,'Seller')})
          finishFull()
        """)

    def test_default_scan_persists_and_keeps_all_item_kinds(self):
        for preference in ({}, {'recoveryEnabled': False}, {'recoveryEnabled': True},
                           {'professionSettings': {'engineering': {'recoveryEnabled': True}}}):
            with self.subTest(preference=preference):
                lua = self.boot({'prof': preference})
                before=plain(lua.globals().DungeonsForeverDB)
                self.scan(lua)
                after=plain(lua.globals().DungeonsForeverDB)
                snapshot=after['prof'].pop('auctionFullScan')
                self.assertEqual(after,before)
                self.assertEqual(snapshot['v'],3)
                lua.execute("""
                  local b=ns.AuctionBridge
                  assert(b.StockPersistenceEnabled==nil and b.SyncStockPersistence==nil and b.ReplicateScanReady())
                  for id,q in pairs({[11]=8,[12]=2,[10940]=10,[9999]=3})do
                    assert(b.GetAuctionSupply(id).quantity==q)
                  end
                  assert(b.GetAuctionSupply(88).quantity==0)
                  assert(DungeonsForeverDB.prof.auctionFullScan.items[11].q==8 and #requests==0)
                """)

    def test_default_memory_snapshot_reaches_real_capture_and_solver(self):
        lua = self.boot()
        for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture','ProfRouteSolver'):
            lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
        lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
          beginFull(1);sendFull({rawRow(11,8,56,'Seller')});finishFull()
          local s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3,autoCraftTools=false,considerAuctionSupply=true})
          assert(s.auctionSupply[11].quantity==8 and s.prices[11]==7)
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false})
          assert(r.targetReached and r.total==14 and r.purchaseVerified)
          assert(DungeonsForeverDB.prof.auctionFullScan.items[11].q==8)
        """)

    def test_toggling_recovery_does_not_change_saved_inventory(self):
        lua = self.boot()
        self.scan(lua)
        lua.execute("""
          local b=ns.AuctionBridge;local revision=b.SupplyRevision()
          for _,enabled in ipairs({true,false,true}) do
            DungeonsForeverDB.prof.recoveryEnabled=enabled
            assert(DungeonsForeverDB.prof.auctionFullScan.items[11].q==8)
            assert(DungeonsForeverDB.prof.auctionReplicateGate==nil)
            assert(b.ReplicateScanReady() and b.GetAuctionSupply(12).quantity==2)
          end
          assert(b.SupplyRevision()==revision and #requests==0)
        """)

    def test_default_reload_restores_inventory_and_does_not_use_daily_high(self):
        lua = self.boot()
        self.scan(lua)
        fresh = self.boot(plain(lua.globals().DungeonsForeverDB))
        fresh.execute("""
          local b=ns.AuctionBridge
          local ready,reason=b.ReplicateScanReady()
          assert(ready==true and reason==nil and b.FullScanSnapshotStatus().restored)
          assert(b.GetAuctionSupply(11).quantity==8 and b.GetAuctionSupply(11).observedAt==10000)
          assert(Auctionator.Database.db['11'].a['0']==999)
          beginFull(1);sendFull({rawRow(11,1,7,'Seller')});finishFull()
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==1)
        """)

    def test_recovery_enabled_reload_restores_scan_prices(self):
        lua = self.boot({'prof': {'recoveryEnabled': True}})
        self.scan(lua)
        saved = plain(lua.globals().DungeonsForeverDB)
        self.assertIn('auctionFullScan', saved['prof'])
        self.assertNotIn('auctionReplicateGate', saved['prof'])
        fresh = self.boot(saved)
        fresh.execute("assert(loadstring(...))('DungeonsForever',ns)",
            (ROOT/'Core/ProfRouteAuto.lua').read_text(encoding='utf-8-sig'))
        fresh.execute("""
          Auctionator.API={v1={GetAuctionPriceByItemID=function()return 19 end}}
          local b=ns.AuctionBridge
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(12).quantity==2)
          assert(b.GetAuctionSupplyStatus(12)=='verified')
          assert(ns.ProfRouteAuto.AHPriceOf(12)==7)
          beginFull(1);sendFull({rawRow(12,2,14,'Seller')});finishFull()
          assert(ns.ProfRouteAuto.AHPriceOf(12)==7)
        """)

    def test_disabled_recovery_reload_restores_inventory(self):
        lua = self.boot({'prof': {'recoveryEnabled': True}})
        self.scan(lua)
        lua.execute("DungeonsForeverDB.prof.recoveryEnabled=false")
        saved = plain(lua.globals().DungeonsForeverDB)
        self.assertIn('auctionFullScan', saved['prof'])
        fresh = self.boot(saved)
        fresh.execute("assert(ns.AuctionBridge.ReplicateScanReady() and ns.AuctionBridge.GetAuctionSupply(11).quantity==8)")

    def test_removed_scan_fields_are_discarded_without_touching_execution_or_settings(self):
        saved={'prof': {'recoveryEnabled': True, 'auctionFullScan': {
            'v': 2, 'c': True, 't': 10000, 'mk': 'Realm:Alliance', 'ob': 'Player',
            'items': {11: {'q': 999, 'p': 7}}},
            'auctionReplicateGate': {'v': 1, 'enabled': True, 'generation': 3, 'scanSerial': 9},
            'replicateRequiredAfter': 9000, 'track': {'sentinel': 123}, 'routePlans': {'sentinel': 456}}}
        fresh=self.boot(saved)
        fresh.execute("""
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil)
          assert(DungeonsForeverDB.prof.auctionFullScan.items==nil and ns.AuctionBridge.FullScanSnapshotStatus().status=='invalid')
          assert(DungeonsForeverDB.prof.auctionReplicateGate==nil)
          assert(DungeonsForeverDB.prof.replicateRequiredAfter==nil)
          assert(DungeonsForeverDB.prof.recoveryEnabled)
          assert(DungeonsForeverDB.prof.track.sentinel==123 and DungeonsForeverDB.prof.routePlans.sentinel==456)
        """)

    def test_shared_memory_is_unchanged_when_switching_professions(self):
        lua=self.boot({'prof': {'professionSettings': {'alchemy': {'recoveryEnabled': True},
                                                    'engineering': {'recoveryEnabled': True}}}})
        self.scan(lua)
        lua.execute("""
          local b=ns.AuctionBridge;local db=DungeonsForeverDB.prof
          db.professionSettings.alchemy.recoveryEnabled=false
          ns.ProfModule.cur='engineering'
          assert(b.GetAuctionSupply(12).quantity==2 and db.auctionFullScan.items[12].q==2)
          db.professionSettings.engineering.recoveryEnabled=false
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(12).quantity==2)
          assert(db.auctionFullScan.items[12].q==2 and db.auctionReplicateGate==nil)
        """)

    def test_chunked_scan_publishes_only_when_complete_regardless_of_recovery(self):
        for final in (False, True):
            with self.subTest(final=final):
                lua = self.boot({'prof': {'recoveryEnabled': not final}})
                lua.globals().final = final
                lua.execute("""
                  local b=ns.AuctionBridge;local rows={}
                  for i=1,301 do rows[i]=rawRow(11,1,7,'Seller')end
                  beginFull(301);sendFull(rows);step()
                  assert(b.FullScanStatus().done==250 and b.GetAuctionSupply(11)==nil)
                  DungeonsForeverDB.prof.recoveryEnabled=final
                  step()
                  assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==301)
                  assert(DungeonsForeverDB.prof.auctionFullScan.items[11].q==301)
                """)

    def test_failed_scan_and_mode_changes_retain_verified_snapshot(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                lua = self.boot({'prof': {'recoveryEnabled': enabled}})
                self.scan(lua)
                lua.execute("""
                  local b=ns.AuctionBridge
                  beginFull(1);Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
                  assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==8)
                  beginFull(1);sendFull({rawRow(11,2,14,'Seller')});finishFull()
                  assert(b.GetAuctionSupply(11).quantity==2)
                  Auctionator.Config.Get=function()return false end
                  assert(b.ReplicateScanReady())
                  Auctionator.Config.Get=function()return true end
                  assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==2)
                """)

    def test_incomplete_market_never_claims_missing_item_is_zero(self):
        lua = self.boot()
        lua.execute("""
          beginFull(2);sendFull({rawRow(11,1,7,'Seller')});finishFull()
          assert(not ns.AuctionBridge.ReplicateScanReady())
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil and ns.AuctionBridge.GetAuctionSupply(12)==nil)
          assert(DungeonsForeverDB.prof.auctionFullScan.items==nil)
        """)

    def test_expiration_and_observer_checks_apply_regardless_of_recovery(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                lua = self.boot({'prof': {'recoveryEnabled': enabled}})
                self.scan(lua)
                lua.execute("""
                  local b=ns.AuctionBridge
                  UnitName=function()return 'AnotherPlayer'end
                  assert(b.GetAuctionSupply(11)==nil)
                  UnitName=function()return 'Player'end;clock=clock+1801
                  assert(not b.ReplicateScanReady() and b.GetAuctionSupply(11)==nil)
                """)

    def test_live_recovery_uses_verified_snapshot_without_inventing_stock(self):
        for scanned in (False,True):
            with self.subTest(scanned=scanned):
                lua=self.boot({'prof': {'recoveryEnabled': True}})
                for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture','ProfRecovery'):
                    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                        (ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
                lua.globals().scanned=scanned
                lua.execute("""
                  ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
                  IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
                  C_Item={GetItemSellPrice=function()return 2 end}
                  Auctionator.API={v1={GetAuctionPriceByItemID=function(_,id)return id==10 and 500 or 7 end}}
                  if scanned then
                    beginFull(2);sendFull({rawRow(11,8,56,'Seller'),rawRow(10,40,12000,'Seller')});finishFull()
                  end
                  local s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3,autoCraftTools=false,
                    considerAuctionSupply=true,recoveryEnabled=true,recoveryFeePercent=5})
                  local q=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=5}).quotes[10]
                  if scanned then
                    assert(q.supplyReliable and q.source=='ah' and q.unit==285 and q.quantity==40)
                  else
                    assert(not q.supplyReliable and q.source=='npc' and q.unit==2 and q.quantity==nil)
                    local f=ns.ProfEconomy.FormulaAuctionSupplyOf(s,11)
                    assert(f==nil,'historical daily high was used as formula stock')
                  end
                  assert((DungeonsForeverDB.prof.auctionFullScan~=nil)==scanned)
                """)

    def test_price_only_capture_still_requires_a_complete_auction_scan(self):
        lua=self.boot()
        for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture','ProfRouteSolver','ProfExecution','ProfRoutePlans'):
            lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
        lua.execute("""
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
          Auctionator.API={v1={GetAuctionPriceByItemID=function()return 7 end}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=3,autoCraftTools=false,considerAuctionSupply=true})
          assert(r.status=='recalculate_required' and r.diagnostics[1].code=='replicateScanRequired')
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil and DungeonsForeverDB.prof.auctionFullScan==nil)
        """)


class StockPersistenceRouteTests(unittest.TestCase):
    def test_reload_keeps_frozen_execution_but_requires_scan_for_new_routes(self):
        before=routes.NativeRoutePlansTests();before.setUp()
        before.lua.execute("""
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          original=finish('alchemy',{start=1,target=3})
          assert(ns.ProfExecution.Bind('alchemy',original))
          assert(ns.ProfExecution.RecordAttempt('alchemy',101,'before-reload'))
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
        """)
        saved=plain(before.lua.globals().DungeonsForeverDB)
        plan_id=before.lua.globals().original.planID
        fresh=routes.NativeRoutePlansTests();fresh.setUp()
        fresh.lua.globals().DungeonsForeverDB=table(fresh.lua,saved)
        fresh.lua.globals().expected_plan=plan_id
        fresh.lua.execute('ns.IsForever=true')
        fresh.lua.execute(SOURCE_MOCK)
        fresh.load((ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        fresh.lua.execute("""
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
          local ra,b,xp=ns.ProfRouteAuto,ns.AuctionBridge,ns.ProfExecution
          assert(not b.ReplicateScanReady() and b.GetAuctionSupply(11)==nil)
          ns.ProfEconomy.Capture=function()error('frozen execution recaptured live inventory')end
          local r=ra.Get('alchemy',{start=1,target=3})
          assert(r.planID==expected_plan and r.total==14 and #r.mats>0 and #r.actions>0)
          assert(xp.Progress('alchemy',1).casts==1 and not r.fromSkeleton)
          ns.ProfEconomy.Capture=function(slug)
            local s=fixture();s.recipes[1].profession=slug;s.professions={[slug]={cur=1,max=300}}
            s.known={[slug..':101']=true};return ns.ProfEconomy.Index(s)
          end
          for _,f in ipairs({ra.Compute,ra.Get,ra.Recalculate})do
            local blocked=f('enchanting',{start=1,target=3,considerAuctionSupply=false})
            assert(blocked.status=='recalculate_required' and blocked.diagnostics[1].code=='replicateScanRequired')
          end
          local bound,why=xp.StartNew('alchemy',r)
          assert(not bound and why=='replicateScanRequired')
          assert(xp.GetPlan('alchemy').planID==expected_plan and xp.Progress('alchemy',1).casts==1)
        """)

    def test_candidate_skeleton_rebuilds_after_relogin_using_current_prices(self):
        before=routes.NativeRoutePlansTests();before.setUp()
        before.lua.execute("""
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          original=finish('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(original.total==14)
        """)
        saved=plain(before.lua.globals().DungeonsForeverDB)
        fresh=routes.NativeRoutePlansTests();fresh.setUp()
        fresh.lua.globals().DungeonsForeverDB=table(fresh.lua,saved)
        fresh.lua.execute('ns.IsForever=true')
        fresh.lua.execute(SOURCE_MOCK)
        fresh.load((ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        fresh.lua.execute("""
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.prices[11]=19;return ns.ProfEconomy.Index(s)
          end
          local pending=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(pending.status=='recalculate_required' and pending.diagnostics[1].code=='replicateScanRequired')
          C_Timer.NewTimer=function(delay,fn)
            local handle={due=clock+delay,fn=fn}
            function handle:Cancel()self.cancelled=true end
            timers[#timers+1]=handle;return handle
          end
          beginFull(1);sendFull({rawRow(11,100,1900,'Seller')})
          local pending=timers;timers={}
          for _,handle in ipairs(pending)do
            if not handle.cancelled then
              if handle.due<=clock then handle.fn()else timers[#timers+1]=handle end
            end
          end
          assert(ns.AuctionBridge.ReplicateScanReady())
          local r=finish('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(r.fromSkeleton and r.total==38 and #r.actions>0)
          assert(r.auctionSupplyUnknown==1 and not r.purchaseVerified)
          assert(DungeonsForeverDB.prof.auctionFullScan.items[11].q==100 and DungeonsForeverDB.prof.auctionReplicateGate==nil)
          assert(not ns.ProfExecution.GetPlan('alchemy'))
        """)


class StockPersistenceUITests(unittest.TestCase):
    def test_recovery_setting_has_no_storage_side_effect_and_scan_is_required(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
                fixture.lua.execute("""
                  local PD=ns.ProfModule
                  assert(PD.SETTING_DEF.recoveryEnabled==false and not PD.Setting('recoveryEnabled'))
                  ns.IsForever=true;PD.AuctionatorState=function()return 'ok' end
                  local ready=false
                  ns.AuctionBridge={SyncStockPersistence=function()error('storage callback is still wired')end,
                    ReplicateScanReady=function()return ready,'replicateScanRequired'end}
                  PD.cur='alchemy';PD.SetSettingRaw('recoveryEnabled',true)
                  assert(PD.Setting('recoveryEnabled'))
                  PD.cur='engineering';assert(not PD.Setting('recoveryEnabled'))
                  PD.SetSettingRaw('recoveryEnabled',true);PD.SetSettingRaw('recoveryEnabled',false)
                  assert(not PD.Setting('recoveryEnabled'))
                  PD.cur='alchemy';assert(PD.Setting('recoveryEnabled'))
                  local key='请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'
                  assert(rawget(ns.L,key))
                  local text,blocked=PD.ReplicateScanWarning()
                  assert(text==ns.L[key] and blocked)
                  local rows={};PD.RowsLeveling(rows)
                  assert(PD.autoSnapshot.status=='recalculate_required')
                  assert(not ns.ProfRouteAuto.HasWork('alchemy'))
                  ready=true;assert(PD.ReplicateScanWarning()==nil)
                  local r=finish('alchemy',PD.lvOpts);assert(r.targetReached)
                """)


if __name__=='__main__':
    unittest.main()
