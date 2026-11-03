"""Collect invalid full-scan payloads without losing valid stock or history."""
import unittest

from test_prof_auction_supply import BRIDGE_MOCKS, LuaRuntime, ROOT
from test_prof_auctionator_full_scan import SOURCE_MOCK


MEMORY_MOCKS = r'''
b=ns.AuctionBridge
watched=setmetatable({},{__mode='v'})
function private(fn,name)
 for i=1,100 do
  local key,value=debug.getupvalue(fn,i)
  if not key then break end
  if key==name then return value end
 end
 error('missing upvalue '..name)
end
function watchBatch()
 local batch=assert(private(b.ReplicateScanReady,'fullBatch'))
 watched[1]=batch;watched[2]=batch.items;watched[3]=batch.items[11]
end
function collect()
 for i=#timers,1,-1 do if timers[i].cancelled then table.remove(timers,i)end end
 collectgarbage('collect');collectgarbage('collect')
 return collectgarbage('count')
end
function released()
 collect()
 assert(private(b.ReplicateScanReady,'fullBatch')==nil)
 for i=1,3 do assert(watched[i]==nil,'scan payload retained at '..i)end
end
function scan()
 beginFull(1);sendFull({rawRow(11,2,14,'Seller')});finishFull();watchBatch()
 assert(b.GetAuctionSupply(11).quantity==2)
end
function expiryTimer()
 local result
 for _,timer in ipairs(timers)do if not timer.cancelled and timer.delay>0 then
  assert(not result,'multiple active expiry timers');result=timer
 end end
 return result
end
function fireDue(at)
 clock=at
 for _=1,1000 do
  local found=false
  for i=#timers,1,-1 do if timers[i].cancelled then table.remove(timers,i)end end
  for _,timer in ipairs(timers)do if timer.due<=clock then found=true;break end end
  if not found then return end
  step()
 end
 error('timers did not settle')
end
function detach(timer)
 for i,value in ipairs(timers)do if value==timer then table.remove(timers,i);return end end
 error('timer not scheduled')
end
'''


class ScanMemoryLifecycleTests(unittest.TestCase):
    def boot(self, max_age=1800):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BRIDGE_MOCKS)
        self.lua.execute('local age=...;ns.IsForever=true;ns.ProfRouteAuto.MaxStaleSeconds=function()return age end', max_age)
        self.lua.execute(SOURCE_MOCK)
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(MEMORY_MOCKS)

    def setUp(self):
        self.boot()

    def test_valid_summary_keeps_stock_and_releases_raw_auction_rows(self):
        self.lua.execute('''
          local rows={rawRow(11,2,14,'Seller')};watched[4]=rows
          beginFull(#rows);sendFull(rows);finishFull();watchBatch();rows=nil
          collect();assert(watched[4]==nil,'raw auction rows retained after aggregation')
          assert(watched[1] and watched[2] and watched[3])
          assert(b.GetAuctionSupply(11).quantity==2 and b.GetAuctionSupply(12).quantity==0)
          assert(expiryTimer().due==clock+1801)
          assert(#requests==0 and DungeonsForeverDB.prof.auctionFullScan==nil)
        ''')

    def test_passive_expiry_releases_payload_after_the_inclusive_freshness_boundary(self):
        self.lua.execute('''
          scan();local stamp=clock
          fireDue(stamp+1800);assert(watched[1] and expiryTimer())
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==2)
          local changes=0
          b.OnChanged(function(_,reason)
            if reason=='supply' then
              changes=changes+1;assert(not b.ReplicateScanReady())
              assert(b.GetAuctionSupply(11)==nil)
            end
          end)
          fireDue(stamp+1801);released()
          assert(changes==1 and not expiryTimer())
          assert(b.GetAuctionSupplyStatus(11)=='expired')
          local ready,reason=b.ReplicateScanReady()
          assert(ready==false and reason=='replicateScanRequired')
        ''')

    def test_production_48_hour_expiry_preserves_the_last_valid_second(self):
        self.boot(48*3600)
        self.lua.execute('''
          scan();local stamp=clock
          fireDue(stamp+48*3600)
          assert(b.ReplicateScanReady() and expiryTimer())
          fireDue(stamp+48*3600+1);released()
          assert(not expiryTimer() and b.GetAuctionSupplyStatus(11)=='expired')
        ''')

    def test_early_timer_reschedules_one_deadline_and_keeps_valid_data(self):
        self.lua.execute('''
          scan();local timer=expiryTimer();detach(timer);timer.fn();timer=nil
          collect();assert(watched[1] and b.ReplicateScanReady())
          assert(expiryTimer().due==clock+1801)
          fireDue(clock+1801);released();assert(not expiryTimer())
        ''')

    def test_new_scan_releases_previous_batch_before_its_first_result(self):
        self.lua.execute('''
          scan();beginFull(1);released()
          assert(not expiryTimer() and not b.ReplicateScanReady())
          assert(b.GetAuctionSupply(11)==nil)
          Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
          released();assert(b.GetAuctionSupply(11)==nil)
          scan();assert(b.ReplicateScanReady() and expiryTimer())
        ''')

    def test_cancelled_import_releases_partial_aggregate_and_raw_rows(self):
        self.lua.execute('''
          local rows={};for i=1,301 do rows[i]=rawRow(11,1,7,'Seller')end
          watched[4]=rows;beginFull(#rows);sendFull(rows);step();rows=nil
          local ev=Auctionator.FullScan.Events
          local listener=Auctionator.EventBus.listeners[ev.ScanComplete][1]
          local partial=assert(private(listener.ReceiveEvent,'fullRead'))
          watched[1]=partial;watched[2]=partial.items;watched[3]=partial.items[11];partial=nil
          Auctionator.EventBus:Emit(ev.ScanFailed)
          released();assert(watched[4]==nil and not expiryTimer())
          assert(b.GetAuctionSupply(11)==nil and not b.ReplicateScanReady())
        ''')

    def test_mode_switch_drops_counts_and_never_resurrects_them_when_reenabled(self):
        self.lua.execute('''
          scan();Auctionator.Config.Get=function()return false end;b.ObserveReplicateMode()
          released();assert(not expiryTimer())
          local ready,reason=b.ReplicateScanReady()
          assert(ready==false and reason=='replicateModeDisabled')
          Auctionator.Config.Get=function()return true end;b.ObserveReplicateMode()
          assert(not b.ReplicateScanReady() and b.GetAuctionSupply(11)==nil)
          scan();assert(b.ReplicateScanReady() and expiryTimer())
        ''')

    def test_transient_mode_read_failure_retains_unexpired_batch_for_recovery(self):
        self.lua.execute('''
          scan();Auctionator.Config.Get=function()return nil end
          local ready,reason=b.ReplicateScanReady()
          assert(ready==nil and reason=='replicateModeUnknown' and b.GetAuctionSupply(11)==nil)
          collect();assert(watched[1] and watched[2] and expiryTimer())
          Auctionator.Config.Get=function()return true end
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(11).quantity==2)
        ''')

    def test_newer_summary_scan_discards_full_counts_but_leaves_history_readable(self):
        self.lua.execute('''
          Auctionator.Constants={SCAN_DAY_0=9000}
          Auctionator.Database.GetPriceHistory=function()return {{rawDay=0,available=99}}end
          scan();Auctionator.SavedState.TimeOfLastBrowseScan=clock
          assert(not b.ReplicateScanReady());released();assert(not expiryTimer())
          assert(b.GetAuctionSupply(11)==nil)
          local history=b.GetAuctionSupplyHistory(11)
          assert(history.quantity==99 and history.observedAt==9000 and not history.complete)
          assert(history.source=='auctionator-history' and DungeonsForeverDB.prof.auctionFullScan==nil)
        ''')

    def test_confirmed_identity_change_discards_counts_and_keeps_failure_identity(self):
        for change in ("GetRealmName=function()return 'AnotherRealm'end",
                       "UnitName=function()return 'AnotherPlayer'end"):
            with self.subTest(change=change):
                self.boot()
                self.lua.execute('scan();'+change+'''
                  assert(b.GetAuctionSupplyStatus(11)=='unverified')
                  released();assert(not expiryTimer())
                  GetRealmName=function()return 'Realm'end;UnitName=function()return 'Player'end
                  assert(b.GetAuctionSupply(11)==nil and not b.ReplicateScanReady())
                ''')
        self.boot()
        self.lua.execute('''
          scan();fireDue(clock+1801);released()
          assert(b.GetAuctionSupplyStatus(11)=='expired')
          GetRealmName=function()return 'AnotherRealm'end
          assert(b.GetAuctionSupplyStatus(11)=='unverified')
        ''')

    def test_global_incompleteness_releases_aggregate_but_individual_failures_do_not(self):
        self.lua.execute('''
          local rows={};for i=1,301 do rows[i]=rawRow(11,1,7,'Seller')end
          beginFull(302);sendFull(rows);step();rows=nil
          local ev=Auctionator.FullScan.Events
          local listener=Auctionator.EventBus.listeners[ev.ScanComplete][1]
          local partial=assert(private(listener.ReceiveEvent,'fullRead'))
          watched[1]=partial;watched[2]=partial.items;watched[3]=partial.items[11];partial=nil
          finishFull();released()
          assert(not expiryTimer() and b.GetAuctionSupplyStatus(11)=='incomplete')
          beginFull(2);sendFull({rawRow(11,1,7,nil),rawRow(12,3,21,'Seller')});finishFull();watchBatch()
          collect();assert(watched[1] and watched[2] and expiryTimer())
          assert(b.ReplicateScanReady() and b.GetAuctionSupply(12).quantity==3)
          assert(b.GetAuctionSupplyStatus(11)=='incomplete' and b.GetAuctionSupply(11)==nil)
        ''')

    def test_stale_expiry_callback_cannot_clear_a_new_scan_or_its_timer(self):
        self.lua.execute('''
          scan();local old=expiryTimer().fn
          beginFull(1);sendFull({rawRow(11,8,56,'Seller')});finishFull()
          local current=expiryTimer();old()
          assert(expiryTimer()==current and b.GetAuctionSupply(11).quantity==8)
          assert(b.ReplicateScanReady())
        ''')

    def test_large_invalid_batch_is_collected_without_forcing_gc_in_production(self):
        self.lua.execute('''
          local rows={};for i=1,10000 do rows[i]=rawRow(i,2,14,'Seller')end
          beginFull(#rows);sendFull(rows);finishFull();rows=nil;watchBatch()
          local before=collect();Auctionator.Config.Get=function()return false end;b.ObserveReplicateMode()
          released();local after=collect()
          assert(before-after>500,'discarded market aggregate was not reclaimed')
          assert(not expiryTimer() and #requests==0)
        ''')


if __name__ == '__main__':
    unittest.main()
