"""Auctionator v341 readiness and public API lifecycle, using Lua 5.1 mocks."""
import os
from pathlib import Path
import sys
import unittest

for p in (Path(os.environ.get("TEMP", "/tmp"))/"df-lua-runtime", Path.home()/"AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0, str(p))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCKS = r'''
ns={LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k) return k end})}
frames={}; timers={}; messages={}; invalidations=0; imports={}; init={}
function ns.Init(fn) init[#init+1]=fn end
ns.ProfRouteAuto={Invalidate=function() invalidations=invalidations+1 end}
function CreateFrame()
  local f={events={}}
  function f:RegisterEvent(e) self.events[e]=true end
  function f:SetScript(k,v) self[k]=v end
  frames[#frames+1]=f; return f
end
C_Timer={After=function(delay,fn) timers[#timers+1]={delay=delay,fn=fn} end}
function flushZero()
  local old=timers; timers={}
  for _,t in ipairs(old) do
    if t.delay==0 then t.fn() else timers[#timers+1]=t end
  end
end
function flushAll()
  local old=timers; timers={}; for _,t in ipairs(old) do t.fn() end
end
function UnitName() return 'Tester' end
locales={}; metadata=nil
function GetAddOnMetadata(addon,key) assert(addon=='Auctionator' and key=='Version'); return metadata end
DEFAULT_CHAT_FRAME={AddMessage=function(_,s) messages[#messages+1]=s end}
StaticPopupDialogs={}
function StaticPopup_Show(which) lastPopup=StaticPopupDialogs[which] end
function strjoin(sep,...) return table.concat({...},sep) end
function loaded()
  metadata='341'
  Auctionator={State={Loaded=true},Database={},Shopping={ListManager={}},API={v1={}}}
  local api=Auctionator.API.v1
  function api.GetAuctionPriceByItemID(caller,id) assert(caller=='DungeonsForever'); return nil end
  function api.RegisterForDBUpdate(caller,fn) assert(caller=='DungeonsForever'); dbCallback=fn; subscriptions=(subscriptions or 0)+1 end
  function api.CreateShoppingList(caller,name,terms) assert(caller=='DungeonsForever'); imports[#imports+1]={name=name,terms=terms} end
end
'''


class AuctionatorTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
            str(ROOT/"Core"/"AuctionatorBridge.lua"))

    def test_installed_loading_is_distinct_from_missing(self):
        self.lua.execute("""
          local ab=ns.AuctionBridge
          assert(ab.Status().state=='missing' and not ab.Status().installed)
          metadata='341'
          assert(ab.Status().state=='loading' and ab.Status().installed)
          assert(not ab.PriceReady() and not ab.Available())
        """)

    def test_price_api_exists_before_login_database(self):
        self.lua.execute("""
          loaded(); Auctionator.Database=nil; Auctionator.State.Loaded=nil
          assert(type(Auctionator.API.v1.GetAuctionPriceByItemID)=='function')
          assert(ns.AuctionBridge.Status().state=='loading')
          assert(not ns.AuctionBridge.PriceReady())
          Auctionator.Database={}; Auctionator.State.Loaded=true
          assert(ns.AuctionBridge.PriceReady() and ns.AuctionBridge.Status().state=='ready')
        """)

    def test_login_observation_waits_for_other_login_handlers(self):
        self.lua.execute("""
          loaded(); Auctionator.Database=nil; Auctionator.State.Loaded=nil
          ns.AuctionBridge.Refresh(); local before=invalidations
          frames[1].OnEvent(frames[1],'PLAYER_LOGIN')
          assert(invalidations==before)
          Auctionator.Database={}; Auctionator.State.Loaded=true
          flushZero()
          assert(invalidations==before and ns.AuctionBridge.PriceReady())
        """)

    def test_public_database_changes_invalidate_price_and_plan_caches_once(self):
        self.lua.execute("""
          loaded(); ns.AuctionBridge.Refresh(); ns.AuctionBridge.Refresh()
          assert(subscriptions==1)
          local before=invalidations
          dbCallback(); dbCallback(); dbCallback()
          assert(invalidations==before)
          flushZero(); assert(invalidations==before+1)
        """)

    def test_coalesced_readiness_does_not_lose_database_change(self):
        self.lua.execute("""
          loaded(); ns.AuctionBridge.Refresh(); local before=invalidations
          frames[1].OnEvent(frames[1],'PLAYER_ENTERING_WORLD')
          dbCallback(); flushZero()
          assert(invalidations==before+1)
        """)

    def test_no_price_records_does_not_mean_uninstalled(self):
        self.lua.execute("""
          loaded(); local s=ns.AuctionBridge.Status()
          assert(s.state=='ready' and s.installed and s.priceReady)
          assert(Auctionator.API.v1.GetAuctionPriceByItemID('DungeonsForever',1)==nil)
          assert(ns.AuctionBridge.Status().state=='ready')
        """)

    def test_shopping_waits_for_manager_and_does_not_claim_missing(self):
        self.lua.execute("""
          loaded(); Auctionator.Shopping.ListManager=nil
          assert(not ns.AuctionBridge.Available())
          ns.AuctionBridge.DoImport('Alchemy',{{name='Copper Ore',need=3}})
          assert(#imports==0 and string.find(lastPopup.text,'正在初始化',1,true))
          Auctionator.Shopping.ListManager={}
          ns.AuctionBridge.DoImport('Alchemy',{{name='Copper Ore',need=3}})
          assert(#imports==1 and #imports[1].terms==1)
        """)

    def test_modern_and_legacy_enable_state_arguments(self):
        self.lua.execute("""
          metadata='341'
          C_AddOns={GetAddOnEnableState=function(addon,name) assert(addon=='Auctionator' and name=='Tester'); return 0 end}
          assert(ns.AuctionBridge.Status().state=='disabled')
          C_AddOns=nil
          GetAddOnEnableState=function(name,addon) assert(name=='Tester' and addon=='Auctionator'); return 0 end
          assert(ns.AuctionBridge.Status().state=='disabled')
        """)

    def test_readiness_retry_is_bounded_and_non_auctionator_load_ignored(self):
        self.lua.execute("""
          frames[1].OnEvent(frames[1],'ADDON_LOADED','OtherAddon'); assert(#timers==0)
          metadata='341'; ns.AuctionBridge.Refresh()
          for i=1,25 do flushAll() end
          assert(#timers==0 and ns.AuctionBridge.Status().state=='loading')
        """)


SUPPLY_MOCKS = r'''
now=100; function GetTime() return now end
function time() return 1792300000+now end
queryCalls=0; hook=nil; batch={}; total=0
function QueryAuctionItems(...) queryCalls=queryCalls+1; if hook then hook(...) end end
function hooksecurefunc(name,fn) assert(name=='QueryAuctionItems'); hook=fn end
function GetNumAuctionItems(which) assert(which=='list'); return #batch,total end
function GetAuctionItemInfo(which,index) assert(which=='list'); return unpack(batch[index],1,17) end
function GetAuctionItemLink(_,index) return 'item:'..tostring(batch[index][17]) end
names={[10]='Copper Ore',[20]='Tin Ore'}
function GetItemInfo(key)
  if type(key)=='number' then return names[key],names[key] and 'item:'..key end
  for id,name in pairs(names) do if name==key then return name,'item:'..id end end
end
function row(id,n,price,owner)
  local r={[1]=names[id] or 'Test Item',[3]=n,[10]=price,[14]=owner or 'Other',[16]=0,[17]=id}; return r
end
function event(name,arg) frames[1].OnEvent(frames[1],name,arg) end
function page(name,index,rows,allRows,all,exact)
  QueryAuctionItems(name,nil,nil,index,nil,nil,all,exact,nil)
  batch=rows; total=allRows; event('AUCTION_ITEM_LIST_UPDATE')
end
'''


class AuctionSupplyTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS + SUPPLY_MOCKS)
        self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
            str(ROOT/"Core"/"AuctionatorBridge.lua"))

    def test_unknown_and_historical_counts_do_not_become_supply(self):
        self.lua.execute("""
          loaded(); Auctionator.Database={a={[10]=9999}}
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          assert(queryCalls==0 and hook~=nil)
        """)

    def test_live_buyout_quantity_excludes_owned_and_bid_only(self):
        self.lua.execute("""
          page('Copper Ore',0,{row(10,6,60),row(10,3,90),row(10,9,0),row(10,4,40,'Tester')},4,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==9 and q.complete and #q.lots==2)
          assert(q.lots[1].buyout==60 and q.lots[1].unitPrice==10 and q.lots[1].stack)
          assert(ns.AuctionBridge.GetAuctionSupply(20)==nil)
          q.quantity=999; q.lots[1].quantity=999
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==9)
          assert(ns.AuctionBridge.GetAuctionSupply(10).lots[1].quantity==6)
        """)

    def test_compact_snapshot_omits_lots_and_does_not_mutate_cache(self):
        self.lua.execute("""
          page('Copper Ore',0,{row(10,6,60),row(10,3,90)},2,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10,true)
          assert(q.quantity==9 and q.complete and q.lots==nil)
          q.quantity=0
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==9)
        """)

    def test_pages_accumulate_without_repeated_event_double_count(self):
        self.lua.execute("""
          page('Copper Ore',0,{row(10,2,20)},2,false,true)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==2 and not ns.AuctionBridge.GetAuctionSupply(10).complete)
          event('AUCTION_ITEM_LIST_UPDATE')
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==2)
          page('Copper Ore',1,{row(10,3,90)},2,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==5 and q.complete)
        """)

    def test_missing_first_page_never_claims_complete(self):
        self.lua.execute("""
          page('Copper Ore',1,{row(10,2,20)},1,false,true)
          assert(not ns.AuctionBridge.GetAuctionSupply(10).complete)
        """)

    def test_exact_empty_is_zero_but_other_items_are_unknown(self):
        self.lua.execute("""
          page('Copper Ore',0,{},0,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q and q.quantity==0 and q.complete)
          assert(ns.AuctionBridge.GetAuctionSupply(20)==nil)
        """)

    def test_only_unowned_or_bid_rows_prove_zero_buyable(self):
        self.lua.execute("""
          page('Copper Ore',0,{row(10,5,50,'Tester'),row(10,7,0)},2,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==0 and q.complete and #q.lots==0)
        """)

    def test_filtered_query_is_partial_and_preserves_complete_observation(self):
        self.lua.execute("""
          page('Copper Ore',0,{row(10,5,50)},1,false,true)
          QueryAuctionItems('Copper Ore',1,nil,0,nil,nil,false,true,nil)
          batch={row(10,2,20)}; total=1; event('AUCTION_ITEM_LIST_UPDATE')
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
          QueryAuctionItems('Tin Ore',1,nil,0,nil,nil,false,true,nil)
          batch={row(20,2,20)}; total=1; event('AUCTION_ITEM_LIST_UPDATE')
          assert(not ns.AuctionBridge.GetAuctionSupply(20).complete)
        """)

    def test_full_scan_proves_missing_item_zero_without_five_minute_expiry(self):
        self.lua.execute("""
          page('',0,{row(10,5,50)},1,true,false)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
          now=401
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5 and ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
        """)

    def test_later_item_search_overrides_full_scan_within_same_clock_tick(self):
        self.lua.execute("""
          page('',0,{row(10,5,50)},1,true,false)
          page('Copper Ore',0,{row(10,2,20)},1,false,true)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==2)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
        """)

    def test_newer_partial_page_overrides_previous_complete_market_bound(self):
        self.lua.execute("""
          page('',0,{row(10,5,50)},1,true,false)
          page('Copper Ore',0,{row(10,2,20)},2,false,true)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==2 and not q.complete)
        """)

    def test_next_auction_house_session_retains_saved_supply(self):
        self.lua.execute("""
          page('',0,{row(10,5,50)},1,true,false)
          event('AUCTION_HOUSE_CLOSED'); flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
          event('AUCTION_HOUSE_SHOW')
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5 and ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
        """)

    def test_age_does_not_delete_or_invalidate_and_uses_no_expiry_timer(self):
        self.lua.execute("""
          loaded(); ns.AuctionBridge.Refresh()
          page('Copper Ore',0,{row(10,5,50)},1,false,true); flushZero()
          page('Tin Ore',0,{row(20,2,20)},1,false,true); flushZero()
          local delayed=0; for _,t in ipairs(timers) do if t.delay>0 then delayed=delayed+1 end end
          assert(delayed==0)
          local before,revision=invalidations,ns.AuctionBridge.SupplyRevision()
          now=200000; flushAll(); flushZero()
          assert(invalidations==before and ns.AuctionBridge.SupplyRevision()==revision)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5 and #timers==0)
          assert(ns.AuctionBridge.GetAuctionSupply(10).old)
        """)

    def test_full_scan_public_db_callback_can_observe_when_listener_suspended(self):
        self.lua.execute("""
          loaded(); ns.AuctionBridge.Refresh()
          QueryAuctionItems('',nil,nil,0,nil,nil,true,false,nil)
          batch={row(10,5,50)}; total=1
          dbCallback(); flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==5)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==0)
        """)

    def test_full_scan_detects_zero_based_rows_and_reads_exact_count(self):
        self.lua.execute("""
          local zeroRows={[0]=row(10,4,40),[1]=row(20,7,140)}
          GetNumAuctionItems=function(which) assert(which=='list'); return 2,2 end
          GetAuctionItemInfo=function(which,index)
            assert(which=='list' and index>=0 and index<=1,'zero-based index out of range')
            return unpack(zeroRows[index],1,17)
          end
          QueryAuctionItems('',nil,nil,0,nil,nil,true,false,nil)
          event('AUCTION_ITEM_LIST_UPDATE')
          local copper,tin=ns.AuctionBridge.GetAuctionSupply(10),ns.AuctionBridge.GetAuctionSupply(20)
          assert(copper.quantity==4 and copper.complete and #copper.lots==1)
          assert(tin.quantity==7 and tin.complete and #tin.lots==1)
        """)

    def test_full_scan_invalid_zero_keeps_one_based_client_range(self):
        self.lua.execute("""
          batch={row(10,4,40),row(20,7,140)}; total=2
          GetAuctionItemInfo=function(which,index)
            assert(which=='list'); if index==0 then return nil end
            assert(index==1 or index==2); return unpack(batch[index],1,17)
          end
          QueryAuctionItems('',nil,nil,0,nil,nil,true,false,nil)
          event('AUCTION_ITEM_LIST_UPDATE')
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==4 and ns.AuctionBridge.GetAuctionSupply(10).complete)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==7 and ns.AuctionBridge.GetAuctionSupply(20).complete)
        """)

    def test_full_scan_zero_alias_cannot_duplicate_first_and_lose_last_row(self):
        self.lua.execute("""
          batch={row(10,4,40),row(20,7,140)}; total=2
          GetAuctionItemInfo=function(which,index)
            assert(which=='list'); if index==0 then index=1 end
            assert(index==1 or index==2); return unpack(batch[index],1,17)
          end
          QueryAuctionItems('',nil,nil,0,nil,nil,true,false,nil)
          event('AUCTION_ITEM_LIST_UPDATE')
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==4 and ns.AuctionBridge.GetAuctionSupply(10).complete)
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==7 and ns.AuctionBridge.GetAuctionSupply(20).complete)
        """)

    def test_supply_changes_invalidate_and_do_not_issue_searches(self):
        self.lua.execute("""
          loaded(); ns.AuctionBridge.Refresh(); local before=invalidations
          local rev=ns.AuctionBridge.SupplyRevision()
          page('Copper Ore',0,{row(10,5,50)},1,false,true)
          assert(ns.AuctionBridge.SupplyRevision()>rev and invalidations==before)
          flushZero(); assert(invalidations==before+1 and queryCalls==1)
        """)

    def test_query_started_by_earlier_show_listener_is_not_erased(self):
        self.lua.execute("""
          -- Auctionator's SHOW handler can run before this addon's handler.
          QueryAuctionItems('Copper Ore',nil,nil,0,nil,nil,false,true,nil)
          event('AUCTION_HOUSE_SHOW')
          batch={row(10,5,50)};total=1;event('AUCTION_ITEM_LIST_UPDATE')
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q and q.quantity==5 and q.complete and q.ownerExcluded)
          assert(queryCalls==1,'adapter issued an extra search')
        """)

    def test_empty_exact_query_before_show_still_confirms_zero(self):
        self.lua.execute("""
          QueryAuctionItems('Copper Ore',nil,nil,0,nil,nil,false,true,nil)
          event('AUCTION_HOUSE_SHOW');batch={};total=0
          event('AUCTION_ITEM_LIST_UPDATE')
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q and q.quantity==0 and q.complete)
          event('AUCTION_HOUSE_CLOSED')
          local status=ns.AuctionBridge.SupplyStatus()
          assert(not status.queryActive and status.characterRecords==1)
          assert(ns.AuctionBridge.GetAuctionSupply(10).quantity==0)
        """)

    def test_large_full_scan_yields_and_new_query_cancels_obsolete_batch(self):
        self.lua.execute("""
          local rows={}; for i=1,301 do rows[i]=row(10,1,10) end
          page('',0,rows,301,true,false)
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
          page('Tin Ore',0,{row(20,2,20)},1,false,true)
          flushZero()
          assert(ns.AuctionBridge.GetAuctionSupply(20).quantity==2)
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
        """)

    def test_modern_commodity_tiers_and_owner_units(self):
        self.lua.execute("""
          local rows={{quantity=8,numOwnerItems=2,unitPrice=5},{quantity=2,numOwnerItems=0,unitPrice=8}}
          C_AuctionHouse={GetNumCommoditySearchResults=function(id) assert(id==10); return #rows end,
            GetCommoditySearchResultInfo=function(id,i) return rows[i] end,
            HasFullCommoditySearchResults=function(id) return true end,
            HasSearchResults=function(key) return true end, MakeItemKey=function(id) return {itemID=id} end}
          event('COMMODITY_SEARCH_RESULTS_UPDATED',10)
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==8 and q.complete and not q.lots[1].stack)
          assert(q.lots[1].quantity==6 and q.lots[1].buyout==30)
        """)

    def test_modern_item_results_exclude_account_owned_and_keep_stack_price(self):
        self.lua.execute("""
          local rows={{quantity=2,buyoutAmount=20,auctionID=1}, {quantity=5,buyoutAmount=10,containsAccountItem=true},
            {quantity=4,buyoutAmount=0}, {quantity=3,buyoutAmount=3,containsOwnerItem=true}}
          C_AuctionHouse={GetNumItemSearchResults=function(k) return #rows end,
            GetItemSearchResultInfo=function(k,i) return rows[i] end,
            HasFullItemSearchResults=function(k) return true end}
          event('ITEM_SEARCH_RESULTS_UPDATED',{itemID=10})
          local q=ns.AuctionBridge.GetAuctionSupply(10)
          assert(q.quantity==2 and q.complete and #q.lots==1 and q.lots[1].stack)
        """)

    def test_modern_zero_without_confirmed_results_is_unknown(self):
        self.lua.execute("""
          C_AuctionHouse={GetNumCommoditySearchResults=function() return 0 end,
            GetCommoditySearchResultInfo=function() end,
            HasSearchResults=function() return false end, MakeItemKey=function(id) return {itemID=id} end}
          event('COMMODITY_SEARCH_RESULTS_UPDATED',10)
          assert(ns.AuctionBridge.GetAuctionSupply(10)==nil)
        """)


if __name__ == "__main__":
    unittest.main()
