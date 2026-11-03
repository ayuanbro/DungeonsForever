"""Optional market persistence keeps live inventory independent of SavedVariables."""
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

    def test_default_scan_stays_in_memory_and_keeps_all_item_kinds(self):
        for preference in ({}, {'recoveryEnabled': False}):
            with self.subTest(preference=preference):
                lua = self.boot({'prof': preference})
                self.scan(lua)
                lua.execute("""
                  local b=ns.AuctionBridge
                  assert(not b.StockPersistenceEnabled() and b.ReplicateScanReady())
                  for id,q in pairs({[11]=8,[12]=2,[10940]=10,[9999]=3})do
                    assert(b.GetAuctionSupply(id).quantity==q)
                  end
                  assert(b.GetAuctionSupply(88).quantity==0)
                  assert(DungeonsForeverDB.prof.auctionFullScan==nil and #requests==0)
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
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
        """)

    def test_enabling_saves_current_memory_and_disabling_keeps_live_inventory(self):
        lua = self.boot()
        self.scan(lua)
        lua.execute("""
          local b=ns.AuctionBridge;local revision=b.SupplyRevision()
          DungeonsForeverDB.prof.recoveryEnabled=true;b.SyncStockPersistence()
          local saved=DungeonsForeverDB.prof.auctionFullScan
          assert(saved and saved.v==2 and saved.items[12].q==2)
          assert(saved.items[10940].q==10 and saved.items[9999].q==3)
          assert(saved.items[11].auctionInfo==nil)
          DungeonsForeverDB.prof.recoveryEnabled=false;b.SyncStockPersistence()
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(12).quantity==2)
          assert(b.SupplyRevision()==revision and #requests==0)
        """)

    def test_default_reload_loses_inventory_and_does_not_use_daily_high(self):
        lua = self.boot()
        self.scan(lua)
        fresh = self.boot(plain(lua.globals().DungeonsForeverDB))
        fresh.execute("""
          local b=ns.AuctionBridge
          local ready,reason=b.ReplicateScanReady()
          assert(ready==false and reason=='replicateScanRequired')
          assert(b.GetAuctionSupply(11)==nil and DungeonsForeverDB.prof.auctionFullScan==nil)
          assert(Auctionator.Database.db['11'].a['0']==999)
          beginFull(1);sendFull({rawRow(11,1,7,'Seller')});finishFull()
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==1)
        """)

    def test_enabled_reload_restores_complete_market(self):
        lua = self.boot({'prof': {'recoveryEnabled': True}})
        self.scan(lua)
        saved = plain(lua.globals().DungeonsForeverDB)
        self.assertIn('auctionFullScan', saved['prof'])
        fresh = self.boot(saved)
        fresh.execute("""
          local b=ns.AuctionBridge
          assert(b.StockPersistenceEnabled() and b.ReplicateScanReady())
          assert(b.GetAuctionSupply(12).quantity==2 and b.GetAuctionSupply(9999).quantity==3)
          assert(b.GetAuctionSupply(88).quantity==0)
        """)

    def test_disabling_then_reload_does_not_resurrect_saved_market(self):
        lua = self.boot({'prof': {'recoveryEnabled': True}})
        self.scan(lua)
        lua.execute("DungeonsForeverDB.prof.recoveryEnabled=false;ns.AuctionBridge.SyncStockPersistence()")
        saved = plain(lua.globals().DungeonsForeverDB)
        self.assertNotIn('auctionFullScan', saved['prof'])
        fresh = self.boot(saved)
        fresh.execute("assert(not ns.AuctionBridge.ReplicateScanReady() and ns.AuctionBridge.GetAuctionSupply(11)==nil)")

    def test_disabled_setting_does_not_restore_or_retain_existing_saved_batch(self):
        lua = self.boot({'prof': {'recoveryEnabled': True}})
        self.scan(lua)
        saved = plain(lua.globals().DungeonsForeverDB)
        saved['prof']['recoveryEnabled'] = False
        fresh = self.boot(saved)
        fresh.execute("""
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil)
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
          DungeonsForeverDB.prof.recoveryEnabled=true;ns.AuctionBridge.SyncStockPersistence()
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil and DungeonsForeverDB.prof.auctionFullScan==nil)
        """)

    def test_another_professions_recovery_keeps_shared_inventory_saved(self):
        lua=self.boot({'prof': {'professionSettings': {'alchemy': {'recoveryEnabled': True},
                                                    'engineering': {'recoveryEnabled': True}}}})
        self.scan(lua)
        lua.execute("""
          local b=ns.AuctionBridge;local db=DungeonsForeverDB.prof
          assert(b.StockPersistenceEnabled() and db.auctionFullScan)
          db.professionSettings.alchemy.recoveryEnabled=false
          b.SyncStockPersistence()
          assert(b.StockPersistenceEnabled() and db.auctionFullScan.items[12].q==2)
          ns.ProfModule.cur='engineering'
          assert(b.StockPersistenceEnabled() and b.GetAuctionSupply(12).quantity==2)
          db.professionSettings.engineering.recoveryEnabled=false
          b.SyncStockPersistence()
          assert(not b.StockPersistenceEnabled() and db.auctionFullScan==nil)
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(12).quantity==2)
        """)

    def test_setting_at_completion_controls_chunked_scan_storage(self):
        for final in (False, True):
            with self.subTest(final=final):
                lua = self.boot({'prof': {'recoveryEnabled': not final}})
                lua.globals().final = final
                lua.execute("""
                  local b=ns.AuctionBridge;local rows={}
                  for i=1,301 do rows[i]=rawRow(11,1,7,'Seller')end
                  beginFull(301);sendFull(rows);step()
                  assert(b.FullScanStatus().done==250 and b.GetAuctionSupply(11)==nil)
                  DungeonsForeverDB.prof.recoveryEnabled=final;b.SyncStockPersistence()
                  step()
                  assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==301)
                  assert((DungeonsForeverDB.prof.auctionFullScan~=nil)==final)
                """)

    def test_failed_scan_and_mode_changes_cannot_reuse_unverified_memory(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                lua = self.boot({'prof': {'recoveryEnabled': enabled}})
                self.scan(lua)
                lua.execute("""
                  local b=ns.AuctionBridge
                  beginFull(1);Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
                  assert(not b.ReplicateScanReady() and b.GetAuctionSupply(11)==nil)
                  beginFull(1);sendFull({rawRow(11,2,14,'Seller')});finishFull()
                  assert(b.GetAuctionSupply(11).quantity==2)
                  Auctionator.Config.Get=function()return false end
                  assert(not b.ReplicateScanReady())
                  Auctionator.Config.Get=function()return true end
                  assert(not b.ReplicateScanReady() and b.GetAuctionSupply(11)==nil)
                """)

    def test_incomplete_market_never_claims_missing_item_is_zero(self):
        lua = self.boot()
        lua.execute("""
          beginFull(2);sendFull({rawRow(11,1,7,'Seller')});finishFull()
          assert(not ns.AuctionBridge.ReplicateScanReady())
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil and ns.AuctionBridge.GetAuctionSupply(12)==nil)
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
        """)

    def test_expiration_and_observer_checks_apply_to_memory_and_restored_data(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                lua = self.boot({'prof': {'recoveryEnabled': enabled}})
                self.scan(lua)
                if enabled:
                    lua = self.boot(plain(lua.globals().DungeonsForeverDB))
                lua.execute("""
                  local b=ns.AuctionBridge
                  UnitName=function()return 'AnotherPlayer'end
                  assert(b.GetAuctionSupply(11)==nil)
                  UnitName=function()return 'Player'end;clock=clock+1801
                  assert(not b.ReplicateScanReady() and b.GetAuctionSupply(11)==nil)
                """)


class StockPersistenceRouteTests(unittest.TestCase):
    def test_reload_keeps_frozen_execution_but_requires_scan_for_new_calculation(self):
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
          for _,f in ipairs({ra.Recalculate,ra.Compute})do
            local blocked=f('alchemy',{start=1,target=3})
            assert(blocked.status=='recalculate_required' and blocked.diagnostics[1].code=='replicateScanRequired')
          end
          local new=ra.Get('enchanting',{start=1,target=3})
          assert(new.status=='recalculate_required' and new.diagnostics[1].code=='replicateScanRequired')
          assert(xp.GetPlan('alchemy').planID==expected_plan and xp.Progress('alchemy',1).casts==1)
        """)


class StockPersistenceUITests(unittest.TestCase):
    def test_existing_recovery_setting_controls_storage_without_an_extra_toggle(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
                fixture.lua.execute("""
                  local PD=ns.ProfModule;local calls=0
                  assert(PD.SETTING_DEF.recoveryEnabled==false and not PD.Setting('recoveryEnabled'))
                  ns.AuctionBridge={SyncStockPersistence=function()calls=calls+1 end}
                  PD.cur='alchemy';PD.SetSettingRaw('recoveryEnabled',true)
                  assert(calls==1 and PD.Setting('recoveryEnabled'))
                  PD.cur='engineering';assert(not PD.Setting('recoveryEnabled'))
                  PD.SetSettingRaw('recoveryEnabled',true)
                  assert(calls==2 and PD.Setting('recoveryEnabled'))
                  PD.SetSettingRaw('recoveryEnabled',false)
                  assert(calls==3 and not PD.Setting('recoveryEnabled'))
                  PD.cur='alchemy';assert(PD.Setting('recoveryEnabled'))
                  local key='有专业开启回血时保存共享拍卖库存；全部关闭后仅保留本次内存数据。'
                  assert(GetLocale()=='zhCN' and ns.L[key] or rawget(ns.L,key))
                """)


if __name__=='__main__':
    unittest.main()
