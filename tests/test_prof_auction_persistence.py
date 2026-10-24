"""Latest quantities persist independently of Auctionator's daily maxima."""
import unittest

from test_prof_auctionator import LuaRuntime, MOCKS, ROOT, SUPPLY_MOCKS


PERSIST_MOCKS = r'''
realm='Test Realm'; faction='Alliance'; character='Player-1'
function GetRealmName() return realm end
function UnitFactionGroup() return faction end
function UnitGUID() return character end
function GetBuildInfo() return '1.0','','',16001 end
hookCounts={}
function hooksecurefunc(target,key,callback)
  if type(target)=='string' then
    assert(target=='QueryAuctionItems'); hook=key; return
  end
  assert(type(target)=='table' and type(target[key])=='function')
  hookCounts[key]=(hookCounts[key] or 0)+1
  local original=target[key]
  target[key]=function(...)
    local result={original(...)}; callback(...); return unpack(result)
  end
end
function newDB()
  local db={records={}}
  function db:SetPrice(key,price,available)
    local r=self.records[key] or {}; self.records[key]=r
    r.price=price
    if type(available)=='number' and available>=0 and available<math.huge then
      r.maximum=math.max(r.maximum or 0,available)
    end
  end
  function db:ProcessScan(groups)
    self.ticker={cancelled=false,IsCancelled=function(t)return t.cancelled end}
    C_Timer.After(0,function()
      for key,rows in pairs(groups)do
        local n,price=0,math.huge
        for _,r in ipairs(rows)do n=n+r.available;price=math.min(price,r.price)end
        self:SetPrice(key,price,n)
      end
      self.ticker.cancelled=true
    end)
  end
  function db:GetPriceHistory(key)
    local r=self.records[key]
    return r and {{rawDay='2',available=r.maximum}} or {}
  end
  return db
end
loaded();Auctionator.Database=newDB();Auctionator.Constants={SCAN_DAY_0=1792000000}
function saveLiteral()
  local function encode(v)
    if type(v)=='string'then return string.format('%q',v)end
    if type(v)~='table'then return tostring(v)end
    local out={};for k,value in pairs(v)do out[#out+1]='['..encode(k)..']='..encode(value)end
    return '{'..table.concat(out,',')..'}'
  end
  return encode(DungeonsForeverDB)
end
'''


class AuctionPersistenceTests(unittest.TestCase):
    def runtime(self, saved=None):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(MOCKS + SUPPLY_MOCKS + PERSIST_MOCKS)
        if saved:
            lua.execute('DungeonsForeverDB=' + saved)
        lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
            str(ROOT / 'Core' / 'AuctionatorBridge.lua'))
        lua.execute('ns.AuctionBridge.Refresh()')
        return lua

    def setUp(self):
        self.lua = self.runtime()

    def test_last_update_replaces_daily_maximum_and_survives_fresh_runtime(self):
        self.lua.execute('''
          local db=Auctionator.Database
          db:SetPrice('10',7,100);now=101;db:SetPrice('10',8,20)
          assert(db.records['10'].maximum==100)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==20 and q.observedPrice==8 and q.observedAt==time())
          assert(q.source=='auctionator-update' and not q.complete and not q.ownerExcluded)
        ''')
        restored = self.runtime(self.lua.eval('saveLiteral()'))
        restored.execute('''
          now=1000000;event('PLAYER_LOGIN');flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==20)
          assert(ns.AuctionBridge.GetAuctionSupply(10).old)
          assert(invalidations==0 and queryCalls==0)
        ''')

    def test_price_only_update_has_its_own_time_and_never_refreshes_quantity(self):
        self.lua.execute('''
          Auctionator.Database:SetPrice('10',7,12)
          local first=ns.AuctionBridge.GetAuctionSupply(10)
          now=500;Auctionator.Database:SetPrice('10',9)
          local later=ns.AuctionBridge.GetAuctionSupply(10)
          assert(later.quantity==12 and later.observedAt==first.observedAt)
          assert(later.observedPrice==7 and ns.AuctionBridge.GetAuctionPriceObservedAt(10)==time())
        ''')

    def test_aliases_and_invalid_values_never_create_or_accumulate_supply(self):
        self.lua.execute('''
          local db=Auctionator.Database
          db:SetPrice('gr:10:suffix',4,99);db:SetPrice('g:10:10',4,99)
          db:SetPrice('p:10',4,99);db:SetPrice('010',4,99)
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          for _,n in ipairs({-1,1.5,math.huge,0/0})do db:SetPrice('10',4,n)end
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          db:SetPrice('10',4,8);db:SetPrice('10',4,8)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==8)
        ''')

    def test_daily_maximum_is_reference_only_and_does_not_trigger_query(self):
        self.lua.execute('''
          Auctionator.Database.records['10']={price=7,maximum=100}
          local h=ns.AuctionBridge.GetAuctionSupplyHistory(10)
          assert(h.quantity==100 and h.source=='auctionator-daily-maximum')
          assert(h.observedAt==1792000000+2*86400)
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil and queryCalls==0)
          assert(Auctionator.Database.records['10'].maximum==100)
        ''')

    def test_partial_zero_does_not_erase_positive_but_complete_zero_does(self):
        self.lua.execute('''
          page('Copper Ore',0,{row(10,5,50)},1,false,true)
          page('Copper Ore',0,{row(10,9,90,'Tester')},2,false,true)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
          page('Copper Ore',0,{row(10,9,90,'Tester')},1,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==0 and q.complete and q.ownerExcluded)
          Auctionator.Database:SetPrice('10',10,0)
          assert(ns.AuctionBridge.GetAuctionSupply(10).source=='client-auction-results')
        ''')

    def test_full_market_absence_and_later_same_second_update_survive_reload(self):
        self.lua.execute('''
          page('',0,{row(10,5,50)},1,true,false)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
          Auctionator.Database:SetPrice('20',9,3)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==3)
        ''')
        restored = self.runtime(self.lua.eval('saveLiteral()'))
        restored.execute('''
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==3)
          assert(ns.AuctionBridge.GetAuctionSupply(30).quantity==0)
          event('AUCTION_HOUSE_SHOW');event('AUCTION_HOUSE_CLOSED');flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(30).quantity==0)
        ''')

    def test_normal_scan_client_owner_filter_wins_then_purchase_report_replaces_it(self):
        self.lua.execute('''
          page('Copper Ore',0,{row(10,9,90),row(10,3,30,'Tester')},2,false,true)
          Auctionator.Database:ProcessScan({['10']={{price=10,available=12}}})
          dbCallback();flushZero();flushZero()
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==9 and q.complete and q.ownerExcluded)
          Auctionator.Database:SetPrice('10',10,5)
          q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==5 and q.source=='auctionator-update' and not q.complete)
        ''')

    def test_full_scan_database_writes_before_client_callback(self):
        self.lua.execute('''
          QueryAuctionItems('',nil,nil,0,nil,nil,true,false,nil)
          batch={row(10,9,90),row(10,3,30,'Tester')};total=2
          Auctionator.Database:ProcessScan({['10']={{price=10,available=12}}})
          flushZero();dbCallback();flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==9)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
        ''')

    def test_new_scan_and_changed_raw_aggregate_can_replace_old_complete_observation(self):
        self.lua.execute('''
          page('Copper Ore',0,{row(10,9,90),row(10,3,30,'Tester')},2,false,true)
          Auctionator.Database:ProcessScan({['10']={{price=10,available=5}}})
          flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
          page('Copper Ore',0,{row(10,7,70)},1,false,true)
          Auctionator.Database:ProcessScan({['10']={{price=10,available=7}}})
          flushZero();assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==7)
        ''')

    def test_repeated_async_boundary_write_retains_scan_owner_filter(self):
        self.lua.execute('''
          page('Copper Ore',0,{row(10,9,90),row(10,3,30,'Tester')},2,false,true)
          Auctionator.Database:ProcessScan({['10']={{price=10,available=12}}})
          flushZero()
          -- Installed Auctionator overlaps the 351st row with the next ticker.
          Auctionator.Database:SetPrice('10',10,12)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==9)
          Auctionator.Database:SetPrice('10',10,5)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
        ''')

    def test_large_single_item_group_uses_captured_raw_total_without_rewalking_lots(self):
        self.lua.execute('''
          local rows,groups={},{['10']={}}
          for i=1,301 do
            rows[i]=row(10,1,10,i==301 and 'Tester' or 'Other')
            groups['10'][i]={price=10,available=1}
          end
          page('Copper Ore',0,rows,#rows,false,true)
          flushZero();flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==300)
          Auctionator.Database:ProcessScan(groups)
          flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==300)
        ''')

    def test_later_price_only_public_notification_does_not_recapture_old_full_scan(self):
        self.lua.execute('''
          page('',0,{row(10,5,50)},1,true,false)
          local first=ns.AuctionBridge.GetAuctionSupply(10)
          now=1000;Auctionator.Database:SetPrice('10',12);dbCallback();flushZero()
          local later=ns.AuctionBridge.GetAuctionSupply(10)
          assert(later.quantity==5 and later.observedAt==first.observedAt)
          assert(later.batch==first.batch)
        ''')

    def test_full_scan_persistence_yields_and_cancellation_never_publishes_false_absence(self):
        self.lua.execute('''
          local rows={};for i=1,451 do rows[i]=row(1000+i,1,10)end
          page('',0,rows,#rows,true,false)
          -- Finish collection; the first 150 records are then committed.
          for i=1,3 do flushZero()end
          local m=DungeonsForeverDB.auctionSupply.markets['16001:Test Realm Alliance']
          local c=m.characters[character]
          local n=0;for _ in pairs(c.items)do n=n+1 end
          assert(n==150 and not c.full,'full publication did not yield')
          page('Copper Ore',0,{row(10,3,30)},1,false,true)
          for i=1,8 do flushZero()end
          n=0;for _ in pairs(c.items)do n=n+1 end
          assert(n==151 and not c.full and ns.AuctionBridge.GetAuctionSupply(999)==nil)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==3)
        ''')

    def test_unsupported_or_failed_observer_cannot_break_auctionator_and_reports_error(self):
        self.lua.execute('''
          local original=GetRealmName
          GetRealmName=function()error('test market identity failure')end
          -- The original Auctionator write still succeeds, our hook is isolated.
          Auctionator.Database:SetPrice('10',7,9)
          assert(Auctionator.Database.records['10'].maximum==9)
          GetRealmName=original;ns.AuctionBridge.Refresh()
          assert(ns.AuctionBridge.SupplyStatus().hook=='error')
          assert(ns.AuctionBridge.SupplyStatus().lastError:find('test market identity failure',1,true))
        ''')

    def test_hook_is_once_per_object_method_and_old_object_is_ignored(self):
        self.lua.execute('''
          ns.AuctionBridge.Refresh();ns.AuctionBridge.Refresh()
          assert(hookCounts.SetPrice==1 and hookCounts.ProcessScan==1)
          local old=Auctionator.Database
          Auctionator.Database=newDB();ns.AuctionBridge.Refresh()
          old:SetPrice('10',7,99)
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          Auctionator.Database:SetPrice('10',7,4)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==4)
          assert(hookCounts.SetPrice==2)
          Auctionator.Database.SetPrice=function(self,key,price,n) self.last=n end
          ns.AuctionBridge.Refresh();ns.AuctionBridge.Refresh()
          Auctionator.Database:SetPrice('10',7,2)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==2 and hookCounts.SetPrice==3)
        ''')

    def test_missing_internal_interface_keeps_client_and_saved_fallback(self):
        self.lua.execute('''
          Auctionator.Database:SetPrice('10',7,4)
          Auctionator.Database={};ns.AuctionBridge.Refresh()
          assert(ns.AuctionBridge.SupplyStatus().hook=='unsupported')
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==4)
          page('Copper Ore',0,{row(10,2,20)},1,false,true)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==2)
        ''')

    def test_diagnostic_distinguishes_listener_state_from_saved_quantities(self):
        self.lua.execute('''
          GetAddOnMetadata=function(addon,key)
            return addon=='DungeonsForever' and '1.8.28' or '341'
          end
          local first=ns.AuctionBridge.SupplyStatus()
          assert(first.addonVersion=='1.8.28' and first.hook=='listening' and first.queryHook)
          assert(first.sharedRecords==0 and first.characterRecords==0 and not first.latestObservedAt)
          QueryAuctionItems('Copper Ore',nil,nil,0,nil,nil,false,true,nil)
          assert(ns.AuctionBridge.SupplyStatus().queryActive)
          batch={row(10,5,50)};total=1;event('AUCTION_ITEM_LIST_UPDATE')
          Auctionator.Database:SetPrice('20',7,9)
          local status=ns.AuctionBridge.SupplyStatus()
          assert(status.sharedRecords==1 and status.characterRecords==1 and status.latestObservedAt==time())
          assert(queryCalls==1)
        ''')

    def test_market_and_owner_filtered_character_records_are_isolated(self):
        self.lua.execute('''
          page('Copper Ore',0,{row(10,9,90)},1,false,true)
          character='Player-2'
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          Auctionator.Database:SetPrice('10',7,12)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==12)
          faction='Horde';assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          faction='Alliance';realm='Other Realm'
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          realm='Test Realm';character='Player-1'
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==12)
        ''')

    def test_saved_records_are_compact_and_old_uptime_schema_is_not_migrated(self):
        self.lua.execute('''
          DungeonsForeverDB={auctionSupply={version=1,markets={bad={items={[10]={quantity=99,observedAt=100}}}}}}
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          page('Copper Ore',0,{row(10,2,20)},1,false,true)
          for _,m in pairs(DungeonsForeverDB.auctionSupply.markets)do
            for _,c in pairs(m.characters)do
              assert(c.items[10].lots==nil and c.items[10].schemaVersion==2)
            end
          end
        ''')


if __name__ == '__main__':
    unittest.main()
