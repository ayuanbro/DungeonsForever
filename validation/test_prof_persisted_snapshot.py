"""Cross-reload provenance, bounded storage, route reuse, and localized UI."""
import copy
import unittest
import test_prof_stock_persistence as storage
import test_prof_required_replicate_scan as required
import test_prof_ui_fusion as ui
import test_prof_hud_voice as hud


class PersistedSnapshotTests(unittest.TestCase):
    def boot(self, saved=None, stamp=10000, mode=True):
        lua = storage.LuaRuntime(unpack_returned_tuples=True)
        lua.execute(storage.BRIDGE_MOCKS)
        lua.execute('ns.IsForever=true;ns.ProfRouteAuto.MaxAuctionSupplyAgeSeconds=function()return 172800 end')
        lua.globals().clock = stamp
        if saved is not None:
            lua.globals().DungeonsForeverDB = storage.table(lua, saved)
        lua.execute(storage.SOURCE_MOCK)
        lua.globals().scanMode = mode
        lua.execute('''
          Auctionator.Config.Get=function()return scanMode end
          Auctionator.Config.Set=function(option,value)
            assert(option==Auctionator.Config.Options.REPLICATE_SCAN);scanMode=value
          end
          function hooksecurefunc(target,key,callback)
            assert(target==Auctionator.Config and key=='Set')
            local original=target[key]
            target[key]=function(...)original(...);callback(...)end
          end
        ''')
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                    (storage.ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        return lua

    def saved(self):
        lua = self.boot()
        storage.StockPersistenceTests().scan(lua)
        return storage.plain(lua.globals().DungeonsForeverDB)

    def test_restore_at_two_day_boundary_does_not_extend_lifetime(self):
        saved = self.saved()
        for stamp, status in ((10000, 'available'), (182800, 'available'), (182801, 'expired')):
            with self.subTest(stamp=stamp):
                lua = self.boot(saved, stamp)
                state = lua.eval('ns.AuctionBridge.FullScanSnapshotStatus()')
                self.assertEqual(state['status'], status)
                self.assertEqual(state['observedAt'], 10000)
                self.assertEqual(state['expiresAt'], 182800)
                self.assertTrue(state['restored'])
                if status == 'available':
                    quote = lua.eval('ns.AuctionBridge.GetAuctionSupply(11)')
                    self.assertEqual(quote['quantity'], 8)
                    self.assertEqual(quote['market'], 7)
                    self.assertEqual(quote['observedAt'], 10000)
                snapshot = lua.eval('DungeonsForeverDB.prof.auctionFullScan')
                self.assertEqual(snapshot['items'] is None, status == 'expired')
        lua = self.boot(storage.plain(self.boot(saved, 182801).globals().DungeonsForeverDB), 190000)
        self.assertEqual(lua.eval('ns.AuctionBridge.FullScanSnapshotStatus().status'), 'expired')

    def test_corrupt_and_legacy_snapshots_never_supply_inventory(self):
        saved = self.saved()
        bad = [{'v': 2}, {'c': False}, {'s': 'auctionator-history'}, {'ox': False},
               {'t': 10001}, {'t': 0}, {'t': float('nan')}, {'completedAt': 9999},
               {'completedAt': 10001}, {'expected': 5}, {'received': -1},
               {'items': {11: {'q': -1, 'p': 7}}}, {'items': {11: {'q': 1}}},
               {'items': {11: {'q': 1, 'p': float('inf')}}}, {'ob': ''}]
        for change in bad:
            with self.subTest(change=change):
                value = copy.deepcopy(saved)
                value['prof']['auctionFullScan'].update(change)
                lua = self.boot(value)
                lua.execute('''
                  assert(not ns.AuctionBridge.ReplicateScanReady())
                  assert(ns.AuctionBridge.GetAuctionSupply(11)==nil)
                  assert(ns.AuctionBridge.FullScanSnapshotStatus().status=='invalid')
                  assert(DungeonsForeverDB.prof.auctionFullScan.items==nil)
                ''')

    def test_first_failed_scan_leaves_snapshot_missing_even_after_reload(self):
        lua = self.boot()
        lua.execute('''
          beginFull(1);Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
          assert(ns.AuctionBridge.FullScanStatus().status=='failed')
          assert(ns.AuctionBridge.FullScanSnapshotStatus().status=='missing')
          assert(ns.AuctionBridge.GetAuctionSupply(11)==nil)
        ''')
        fresh = self.boot(storage.plain(lua.globals().DungeonsForeverDB))
        self.assertEqual(fresh.eval('ns.AuctionBridge.FullScanSnapshotStatus().status'), 'missing')

    def test_summary_mode_does_not_subscribe_or_write_and_setting_reconnects_once(self):
        lua = self.boot(mode=False)
        lua.execute('''
          local b=ns.AuctionBridge;local bus=Auctionator.EventBus;local ev=Auctionator.FullScan.Events
          assert(bus.registers==0 and b.FullScanStatus().status=='summary')
          beginFull(1);sendFull({rawRow(11,999,999,'Seller')});bus:Emit(ev.ScanFailed)
          assert(bus.registers==0 and DungeonsForeverDB.prof.auctionFullScan==nil)
          assert(b.GetAuctionSupply(11)==nil and b.FullScanSnapshotStatus().status=='missing')
          local cfg=Auctionator.Config
          cfg.Set(cfg.Options.REPLICATE_SCAN,true);cfg.Set(cfg.Options.REPLICATE_SCAN,true)
          assert(bus.registers==1)
          beginFull(1);sendFull({rawRow(11,8,56,'Seller')});finishFull()
          local saved=DungeonsForeverDB.prof.auctionFullScan
          cfg.Set(cfg.Options.REPLICATE_SCAN,false)
          for _,listeners in pairs(bus.listeners)do assert(#listeners==0)end
          beginFull(1);sendFull({rawRow(11,999,999,'Seller')});bus:Emit(ev.ScanFailed)
          assert(DungeonsForeverDB.prof.auctionFullScan==saved and b.GetAuctionSupply(11).quantity==8)
          assert(b.FullScanStatus().status=='summary' and b.ReplicateScanReady())
          assert(#requests==0)
        ''')

    def test_summary_mode_restores_day_old_snapshot_and_cleans_up_at_two_days(self):
        lua = self.boot(self.saved(), stamp=10000+86400, mode=False)
        lua.execute('''
          local b=ns.AuctionBridge
          assert(Auctionator.EventBus.registers==0 and b.ReplicateScanReady())
          assert(b.GetAuctionSupply(11).quantity==8 and b.GetAuctionSupply(11).market==7)
          assert(b.FullScanSnapshotStatus().restored and b.FullScanSnapshotStatus().observedAt==10000)
          local weak=setmetatable({DungeonsForeverDB.prof.auctionFullScan},{__mode='v'})
          clock=10000+172800;assert(b.ReplicateScanReady())
          clock=clock+1;step()
          assert(b.FullScanSnapshotStatus().status=='expired' and not b.ReplicateScanReady())
          assert(DungeonsForeverDB.prof.auctionFullScan.items==nil)
          collectgarbage('collect');collectgarbage('collect');assert(weak[1]==nil)
          assert(Auctionator.EventBus.registers==0 and #requests==0)
        ''')

    def test_summary_switch_cancels_partial_import_and_ignores_stale_callbacks(self):
        lua = self.boot(self.saved())
        lua.execute('''
          local b=ns.AuctionBridge;local saved=DungeonsForeverDB.prof.auctionFullScan
          local rows={};for i=1,301 do rows[i]=rawRow(11,1,7,'Seller')end
          local weak=setmetatable({rows},{__mode='v'})
          beginFull(#rows);sendFull(rows);step();rows=nil
          local oldCallback
          for _,timer in ipairs(timers)do if timer.delay==0 and not timer.cancelled then oldCallback=timer.fn end end
          assert(oldCallback)
          local cfg=Auctionator.Config;cfg.Set(cfg.Options.REPLICATE_SCAN,false)
          oldCallback();oldCallback=nil
          for _,listeners in pairs(Auctionator.EventBus.listeners)do assert(#listeners==0)end
          assert(b.FullScanStatus().status=='summary' and DungeonsForeverDB.prof.auctionFullScan==saved)
          for i=#timers,1,-1 do if timers[i].cancelled then table.remove(timers,i)end end
          collectgarbage('collect');collectgarbage('collect');assert(weak[1]==nil)
          cfg.Set(cfg.Options.REPLICATE_SCAN,true)
          beginFull(1);sendFull({rawRow(11,3,21,'Seller')});finishFull()
          assert(b.GetAuctionSupply(11).quantity==3 and DungeonsForeverDB.prof.auctionFullScan~=saved)
        ''')

    def test_summary_mode_can_calculate_routes_from_a_day_old_snapshot(self):
        fixture=required.RequiredReplicateScanTests();fixture.setUp()
        fixture.lua.execute('''
          scan();local saved=DungeonsForeverDB.prof.auctionFullScan
          Auctionator.Config.Get=function()return false end;bridge.ObserveReplicateMode()
          for _,listeners in pairs(Auctionator.EventBus.listeners)do assert(#listeners==0)end
          clock=saved.t+86400
          local result=finish('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(result.targetReached and result.total==14 and result.purchaseVerified)
          assert(DungeonsForeverDB.prof.auctionFullScan==saved and saved.t==1001)
        ''')

    def test_mode_change_discovered_at_import_completion_does_not_write_scan_metadata(self):
        lua = self.boot()
        lua.execute('''
          beginFull(1);sendFull({rawRow(11,8,56,'Seller')})
          scanMode=false;step()
          assert(DungeonsForeverDB.prof.auctionFullScan==nil)
          assert(ns.AuctionBridge.FullScanStatus().status=='summary')
          for _,listeners in pairs(Auctionator.EventBus.listeners)do assert(#listeners==0)end
        ''')

    def test_other_character_or_market_preserves_single_account_slot_until_success(self):
        lua = self.boot(self.saved())
        lua.execute('''
          local b=ns.AuctionBridge;local previous=DungeonsForeverDB.prof.auctionFullScan
          UnitName=function()return 'Other'end
          assert(b.FullScanSnapshotStatus().status=='mismatch' and b.GetAuctionSupply(11)==nil)
          beginFull(1);Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
          assert(DungeonsForeverDB.prof.auctionFullScan==previous)
          UnitName=function()return 'Player'end
          assert(b.GetAuctionSupply(11).quantity==8)
          GetRealmName=function()return 'Elsewhere'end
          assert(b.FullScanSnapshotStatus().status=='mismatch')
          GetRealmName=function()return 'Realm'end
          UnitFactionGroup=function()return 'Horde'end
          assert(b.FullScanSnapshotStatus().status=='mismatch')
          UnitFactionGroup=function()return 'Alliance'end;UnitName=function()return 'Other'end
          beginFull(1);sendFull({rawRow(12,3,21,'Seller')});finishFull()
          assert(DungeonsForeverDB.prof.auctionFullScan~=previous)
          assert(b.GetAuctionSupply(12).quantity==3 and b.GetAuctionSupply(11).quantity==0)
          UnitName=function()return 'Player'end
          assert(not b.ReplicateScanReady() and b.GetAuctionSupply(12)==nil)
        ''')

    def test_repeated_atomic_replacement_keeps_one_table_and_reclaims_old_data(self):
        lua = self.boot(self.saved())
        lua.execute('''
          local b=ns.AuctionBridge;local watched=setmetatable({},{__mode='v'})
          for i=1,8 do
            local previous=DungeonsForeverDB.prof.auctionFullScan;watched[i]=previous
            clock=clock+1
            local rows={rawRow(11,i,7*i,'Seller')}
            watched[100+i]=rows
            beginFull(1);sendFull(rows)
            assert(DungeonsForeverDB.prof.auctionFullScan==previous)
            assert(b.GetAuctionSupply(11).quantity==previous.items[11].q)
            finishFull()
            for n=1,30 do
              local name,value=debug.getupvalue(b.FullScanSnapshotStatus,n)
              if not name then break end
              if name=='fullBatch' then assert(rawequal(value,DungeonsForeverDB.prof.auctionFullScan))end
            end
          end
          for i=#timers,1,-1 do if timers[i].cancelled then table.remove(timers,i)end end
          collectgarbage('collect');collectgarbage('collect')
          for _,value in pairs(watched)do error('old snapshot or raw rows retained')end
          assert(b.GetAuctionSupply(11).quantity==8 and #requests==0)
        ''')

    def test_failed_and_summary_scans_do_not_refresh_saved_observation(self):
        lua = self.boot(self.saved())
        lua.execute('''
          local saved=DungeonsForeverDB.prof.auctionFullScan;local b=ns.AuctionBridge
          clock=11000;beginFull(2);sendFull({rawRow(11,999,999,'Seller')});finishFull()
          assert(DungeonsForeverDB.prof.auctionFullScan==saved and saved.t==10000)
          assert(b.GetAuctionSupply(11).quantity==8 and b.FullScanStatus().status=='incomplete')
          Auctionator.Config.Get=function()return false end;b.ObserveReplicateMode()
          Auctionator.SavedState.TimeOfLastBrowseScan=clock
          assert(b.ReplicateScanReady() and saved.t==10000)
          clock=182801;assert(not b.ReplicateScanReady())
          assert(DungeonsForeverDB.prof.auctionFullScan.items==nil)
        ''')

    def test_empty_market_and_individual_failures_survive_reload(self):
        for empty in (False, True):
            lua = self.boot()
            lua.globals().empty = empty
            lua.execute('''
              beginFull(empty and 0 or 3)
              sendFull(empty and {} or {rawRow(11,3,21,nil),rawRow(12,4,28,'Seller'),rawRow(13,8,56,'Player')})
              finishFull()
            ''')
            fresh = self.boot(storage.plain(lua.globals().DungeonsForeverDB))
            fresh.globals().empty = empty
            fresh.execute('''
              local b=ns.AuctionBridge;assert(b.ReplicateScanReady())
              assert(b.GetAuctionSupply(99).quantity==0 and b.GetAuctionSupply(13).quantity==0)
              if empty then assert(b.GetAuctionSupply(11).quantity==0)
              else assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupply(12).quantity==4)end
            ''')

    def test_completed_snapshot_allows_new_profession_and_recalculation_after_reload(self):
        before = required.RequiredReplicateScanTests();before.setUp()
        before.lua.execute('''
          scan();original=finish('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(xp.Bind('alchemy',original));assert(xp.RecordAttempt('alchemy',101,'before-reload'))
        ''')
        saved = storage.plain(before.lua.globals().DungeonsForeverDB)
        fresh = required.RequiredReplicateScanTests();fresh.setUp()
        fresh.lua.globals().DungeonsForeverDB = storage.table(fresh.lua, saved)
        fresh.lua.execute('clock=1002')
        fresh.load((storage.ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        fresh.lua.execute('''
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
          bridge=ns.AuctionBridge
          assert(bridge.FullScanSnapshotStatus().restored and bridge.ReplicateScanReady())
          local plan=xp.GetPlan('alchemy');local id=plan.planID
          assert(xp.Progress('alchemy',1).casts==1)
          local old=ra.Get('alchemy',{start=1,target=3});assert(old.planID==id)
          ns.ProfEconomy.Capture=function(slug)
            local s=fixture();s.stamp=clock;s.recipes[1].profession=slug
            s.professions={[slug]={cur=1,max=300}};s.known={[slug..':101']=true}
            s.auctionSupply={[11]=bridge.GetAuctionSupply(11)}
            return ns.ProfEconomy.Index(s)
          end
          local new=finish('enchanting',{start=1,target=3,considerAuctionSupply=true})
          assert(new.targetReached and new.total==14 and new.purchaseVerified)
          assert(xp.GetPlan('alchemy').planID==id and xp.Progress('alchemy',1).casts==1)
          local recalculated=ra.Recalculate('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(recalculated.status~='recalculate_required')
          assert(finish('alchemy',{start=1,target=3,considerAuctionSupply=true}).targetReached)
        ''')


class SnapshotPresentationTests(unittest.TestCase):
    def test_summary_recommendation_appears_once_in_all_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
            fixture.lua.execute('''
              ns.IsForever=true;PD.AuctionatorState=function()return 'ok'end
              mode=true;ns.AuctionBridge={ReplicateScanEnabled=function()return mode end,
                ReplicateScanReady=function()return true end,
                FullScanSnapshotStatus=function()return {status='available',observedAt=820}end}
              local key='不使用专业功能时，推荐切回摘要模式。'
              assert(rawget(ns.L,key) and PD.ScanModeAdvice()==ns.L[key])
              assert(rawget(ns.L,'摘要模式下，本插件不监听或保存扫描数据；仍可使用 2 天内的完整扫描快照计算。'))
              assert(rawget(ns.L,'完整扫描快照保留 2 天，过期后自动删除；重载或切换扫描模式不会延长有效期。'))
              PD.Wrap=function(text)return {text}end
              local rows={};PD.RowsLeveling(rows)
              local n=0;for _,row in ipairs(rows)do if row.text==ns.L[key]then n=n+1 end end
              assert(n==1)
              mode=false;assert(PD.ScanModeAdvice()==nil and PD.ReplicateScanWarning()==nil)
            ''')

    def test_cost_card_and_body_share_snapshot_state_in_all_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
            fixture.lua.execute('''
              ns.IsForever=true;PD.AuctionatorState=function()return 'ok'end
              state={status='available',observedAt=820,restored=true}
              ns.AuctionBridge={FullScanSnapshotStatus=function()return state end,
                FullScanStatus=function()return {status='ready'}end,
                ReplicateScanReady=function()return state.status=='available','replicateScanRequired'end}
              local function tile()
                local f=widget();f.label=widget();f.val=widget()
                f.val.SetText=function(self,value)self.text=value end;return f
              end
              PD.lvTiles={mode=tile(),scheme=tile(),excl=tile(),target=tile(),cost=tile()}
              PD.chipOrder={'mode','scheme','excl','target'};PD.LV_TILE_H=60
              PD.PaintTileBorder=function()end;PD.PlaceCards=function()end
              PD.SetBadge=function(text)badge=text end;PD.SetSub=function()end
              PD.TipTile=function(t,lines)t.lines=lines end
              PD.Wrap=function(text)return {text}end
              for _,status in ipairs({'available','expired','mismatch','invalid'})do
                state.status=status
                PD.lvSummary={planVersion=2,status='complete',priced=true,total=21,snapshotAge=180,
                  stale=true,staleReason='supply',auctionPurchases={[11]=2}}
                PD.PaintLvTiles()
                local count=0;for _,line in ipairs(PD.lvTiles.cost.lines)do
                  if line[1]==PD.ScanSnapshotText()then count=count+1 end
                end;assert(count==1,'cost card repeats or omits snapshot status')
                if status=='available' then
                  assert(PD.lvTiles.cost.val.text~=ns.L['请扫描拍卖行'])
                  assert(badge~=ns.L['请扫描拍卖行'])
                else
                  assert(PD.lvTiles.cost.val.text==ns.L['请扫描拍卖行'])
                  local rows={};PD.RowsLeveling(rows);count=0
                  for _,row in ipairs(rows)do if row.text==PD.ScanSnapshotText()then count=count+1 end end
                  assert(count==1,'page repeats or omits the scan warning')
                end
              end
            ''')

    def test_localized_states_share_one_message_and_do_not_show_false_scan_badge(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
            fixture.lua.execute('''
              ns.IsForever=true;PD.AuctionatorState=function()return 'ok'end
              state={status='available',observedAt=820,restored=true};attempt={status='ready'}
              ns.AuctionBridge={FullScanSnapshotStatus=function()return state end,
                FullScanStatus=function()return attempt end,
                ReplicateScanReady=function()return state.status=='available','replicateScanRequired'end}
              assert(PD.ScanSnapshotText()==format(ns.L['使用 %d 分钟前的完整扫描'],3))
              assert(PD.ReplicateScanWarning()==nil)
              for _,value in ipairs({'scanning','processing','failed','incomplete'})do
                attempt.status=value;local text=PD.ScanSnapshotText()
                local key=(value=='scanning' or value=='processing')
                  and '正在更新扫描，当前使用上次完整扫描' or '本次扫描失败，沿用 %d 分钟前的完整扫描'
                assert(rawget(ns.L,key) and text==format(ns.L[key],3))
                assert(PD.ReplicateScanWarning()==nil)
              end
              PD.SnapshotBadgeState=function()return 'stock_changed'end
              assert(PD.SnapshotBadgeText({})==ns.L['路线待重算'])
              for status,key in pairs({expired='完整扫描数据已超过 2 天，请更新后重新计算。',
                mismatch='已保存的完整扫描属于其他角色或市场，请用当前角色完成一次完整扫描。',
                invalid='已保存的完整扫描数据无效，请重新完成一次完整扫描。'})do
                state.status=status;assert(rawget(ns.L,key))
                local text,blocked=PD.ReplicateScanWarning()
                assert(blocked and text==ns.L[key] and text==PD.ReplicateScanMessage('replicateScanRequired'))
              end
            ''')

    def test_saved_route_heading_and_hud_show_snapshot_age_without_resetting_progress(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            fixture=hud.HUDVoiceTests()
            fixture.boot=lambda _: ui.ProfessionUIFusionTests.boot(fixture, locale)
            fixture.setUp()
            fixture.lua.execute('''
              ns.IsForever=true;PD.AuctionatorState=function()return 'ok'end
              local status='available'
              ns.AuctionBridge={FullScanSnapshotStatus=function()return {status=status,observedAt=820}end,
                FullScanStatus=function()return {status='ready'}end,
                ReplicateScanReady=function()return status=='available','replicateScanRequired'end}
              run.plan.expanded=614;run.plan.optimal=true
              run.plan.learningPolicyFingerprint='native-learning:7:native-route-eligibility'
              PD.cur='alchemy';PD.autoPage='route';PD.SetSettingRaw('autoRoute',true)
              PD.Wrap=function(text)return {text}end
              local rows={};PD.RowsLeveling(rows)
              assert(PD.lvRouteHead.progress==format(ns.L['已保存路线 · %s'],format(ns.L['优化结束：已比较 %d 种组合'],614)))
              local count=0;for _,row in ipairs(rows)do if row.text==PD.ScanSnapshotText()then count=count+1 end end
              assert(count==1 and xp.GetRun('alchemy').planID==run.planID)
              pf.Paint();assert(pf.f.scanStatus:GetText()==PD.ScanSnapshotText())
              status='expired';pf.Paint();assert(pf.f.scanStatus:GetText()==PD.ScanSnapshotText())
              assert(xp.GetRun('alchemy').planID==run.planID)
            ''')



if __name__ == '__main__':
    unittest.main()
