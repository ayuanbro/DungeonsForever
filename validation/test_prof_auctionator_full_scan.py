"""Consume Auctionator 341 raw full-scan events without issuing another query.

The event names and 18-field raw records were checked against the installed
addon source read-only. Tests themselves read only project files and use mocks.
"""
import unittest
import test_prof_auction_supply as stock

ROOT = stock.ROOT

SOURCE_MOCK = r'''
Auctionator={FullScan={Events={ScanStart='get_all_scan_start',ScanProgress='get_all_scan_progress',
  ScanFailed='get_all_scan_failed',ScanComplete='get_all_scan_complete'}},
  Config={Options={REPLICATE_SCAN='replicate'},Get=function()return true end},
  Database={db={['11']={a={['0']=999},m=1}}},SavedState={TimeOfLastGetAllScan=clock}}
local bus={listeners={},registers=0};Auctionator.EventBus=bus
function bus:Register(listener,events)
 self.registers=self.registers+1
 for _,e in ipairs(events)do
  self.listeners[e]=self.listeners[e] or {};table.insert(self.listeners[e],listener)
 end
end
function bus:Emit(event,...)
 for _,listener in ipairs(self.listeners[event] or {})do listener:ReceiveEvent(event,...)end
end
fullCount=0
GetNumAuctionItems=function()return fullCount,fullCount end
function rawRow(id,q,buy,owner,modern)
 local info={[1]='Item'..id,[3]=q,[10]=buy,[14]=owner,[15]=owner,[17]=id,[18]=true}
 local row={itemLink='item:'..id};row[modern and 'replicateInfo' or 'auctionInfo']=info;return row
end
function beginFull(count)
 fullCount=count
 local ev=Auctionator.FullScan.Events
 bus:Emit(ev.ScanStart);bus:Emit(ev.ScanProgress,0.1);bus:Emit(ev.ScanProgress,0.2)
end
function sendFull(rows)bus:Emit(Auctionator.FullScan.Events.ScanComplete,rows)end
function finishFull()
 for _=1,100 do
  if ns.AuctionBridge.FullScanStatus().status~='processing'then return end
  step()
 end
 error('full scan import did not finish')
end
'''


class AuctionatorFullScanTests(unittest.TestCase):
    setUp = stock.AuctionSupplyBridgeTests.setUp

    def source(self, modern=False):
        self.lua.execute(SOURCE_MOCK)
        if modern:
            self.lua.execute(r'''
              Auctionator.FullScan.Events={ScanStart='replicate_scan_start',ScanProgress='replicate_scan_progress',
                ScanFailed='replicate_scan_failed',ScanComplete='replicate_scan_complete'}
              C_AuctionHouse={GetNumReplicateItems=function()return fullCount end}
            ''')
        self.lua.execute("event('ADDON_LOADED','Auctionator')")

    def test_automatic_attachment_reads_latest_quantity_not_the_daily_high(self):
        self.source()
        self.lua.execute(r'''
          local b=ns.AuctionBridge
          event('PLAYER_LOGIN');assert(b.ConnectAuctionatorStock())
          assert(Auctionator.EventBus.registers==1,'listener registered more than once')
          assert(b.GetAuctionSupply(11)==nil,'daily maximum became current stock')
          beginFull(5)
          assert(b.StartSupplyScan==nil and b.CancelSupplyScan==nil)
          sendFull({rawRow(11,2,20,'Seller'),rawRow(11,3,21,'Other'),
            rawRow(11,100,1,'Player'),rawRow(12,20,0,'Bidder'),rawRow(13,30,30,'Player-Realm')})
          finishFull()
          local q=b.GetAuctionSupply(11)
          assert(q.quantity==5 and q.market==41/5 and q.method=='auctionator-full-scan')
          assert(q.complete and q.ownerExcluded and #requests==0)
          assert(b.GetAuctionSupply(12).quantity==0 and b.GetAuctionSupply(13).quantity==0)
          assert(b.GetAuctionSupply(99).quantity==0,'complete market did not establish absence')
          assert(DungeonsForeverDB.prof.auctionFullScan==nil,'default scan persisted a market copy')
        ''')

    def test_replicate_scan_records_use_the_same_quantity_budget(self):
        self.source(modern=True)
        self.lua.execute(r'''
          beginFull(2);sendFull({rawRow(11,8,56,'Seller',true),rawRow(11,10,10,'Player',true)})
          finishFull()
          local b=ns.AuctionBridge
          assert(b.GetAuctionSupply(11).quantity==8 and #requests==0)
          clock=clock+1801
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='expired')
        ''')

    def test_truncated_or_missing_payload_never_claims_zero_stock(self):
        self.source()
        self.lua.execute(r'''
          local b=ns.AuctionBridge
          beginFull(3);sendFull({rawRow(11,8,56,'Seller')});finishFull()
          assert(b.FullScanStatus().status=='incomplete')
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupply(12)==nil)
          assert(b.GetAuctionSupplyStatus(11)=='incomplete')
          beginFull(0);sendFull(nil)
          assert(b.FullScanStatus().status=='incomplete' and b.GetAuctionSupply(12)==nil)
          -- No server result count means the listener joined too late.
          Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanStart)
          sendFull({rawRow(11,100,700,'Seller')})
          assert(b.FullScanStatus().status=='incomplete' and b.GetAuctionSupply(11)==nil)
        ''')

    def test_unread_owner_or_item_info_only_invalidates_the_identified_item(self):
        self.source()
        self.lua.execute(r'''
          beginFull(3)
          local unloaded=rawRow(12,9,90,'Seller');unloaded.auctionInfo[18]=false
          sendFull({rawRow(11,8,56,nil),unloaded,rawRow(13,4,40,'Seller')});finishFull()
          local b=ns.AuctionBridge
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='incomplete')
          assert(b.GetAuctionSupply(12)==nil and b.GetAuctionSupplyStatus(12)=='incomplete')
          assert(b.GetAuctionSupply(13).quantity==4 and b.GetAuctionSupply(14).quantity==0)
        ''')

    def test_latest_full_scan_replaces_stock_and_ignores_newer_legacy_cache(self):
        self.source()
        self.lua.execute(r'''
          local b=ns.AuctionBridge
          local old={q=999,p=1,t=clock+1000,c=true,ox=true,mk='Realm:Alliance',ob='Player',
            s='client-auction-results',v=2,u=9999}
          DungeonsForeverDB.prof.auctionSupply={[11]=old}
          assert(b.GetAuctionSupply(11)==nil)
          beginFull(1);sendFull({rawRow(11,5,35,'Seller')});finishFull()
          assert(b.GetAuctionSupply(11).quantity==5)
          beginFull(1);sendFull({rawRow(11,2,14,'Seller')});finishFull()
          assert(b.GetAuctionSupply(11).quantity==2)
          beginFull(0);sendFull({});finishFull()
          assert(b.GetAuctionSupply(11).quantity==0,'old single query resurrected absent stock')
          assert(DungeonsForeverDB.prof.auctionSupply[11]==old and #requests==0)
        ''')

    def test_failed_scan_and_cancelled_import_do_not_refresh_old_observations(self):
        self.source()
        self.lua.execute(r'''
          local b=ns.AuctionBridge;local ev=Auctionator.FullScan.Events
          beginFull(1);sendFull({rawRow(11,2,14,'Seller')});finishFull()
          clock=clock+50
          beginFull(1);sendFull({rawRow(11,200,1400,'Seller')})
          Auctionator.EventBus:Emit(ev.ScanFailed)
          assert(b.GetAuctionSupply(11)==nil,'failed new scan reused the discarded batch')
          beginFull(1);sendFull({rawRow(11,3,21,'Seller')});finishFull()
          assert(b.GetAuctionSupply(11).quantity==3 and #requests==0)
          clock=clock+1801;assert(b.GetAuctionSupply(11)==nil)
        ''')

    def test_import_is_atomic_and_is_split_across_frames(self):
        self.source()
        self.lua.execute(r'''
          local b=ns.AuctionBridge;local rows={}
          for i=1,301 do rows[i]=rawRow(11,1,7,'Seller')end
          beginFull(301);sendFull(rows);step()
          assert(b.FullScanStatus().done==250 and b.GetAuctionSupply(11)==nil)
          step();assert(b.GetAuctionSupply(11).quantity==301 and #requests==0)
          UnitName=function()return 'AnotherPlayer'end
          assert(b.GetAuctionSupply(11)==nil)
        ''')

    def test_raw_scan_reaches_the_real_recipe_capture_and_solver_without_manual_query(self):
        self.source()
        for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture','ProfRouteSolver'):
            self.load((ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfModule={ProfLearned=function()return {alchemy={cur=1,max=300}}end}
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
          beginFull(1);sendFull({rawRow(11,1,7,'Seller')});finishFull()
          local s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3,autoCraftTools=false,considerAuctionSupply=true})
          assert(s.auctionSupply[11].quantity==1 and s.prices[11]==7)
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false})
          assert(not r.targetReached and #r.auctionSupplyShortages==1)
          assert(r.mats[1].supplyMethod=='auctionator-full-scan' and #requests==0)
        ''')

    def test_identical_full_scan_keeps_cached_route_fresh_but_changed_stock_marks_it(self):
        self.source()
        for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture',
                     'ProfRecovery','ProfRouteSolver','ProfExecution','ProfSolverRun','ProfRoutePlans'):
            self.load((ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfModule={ProfLearned=function()return {alchemy={cur=1,max=300}}end}
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
          local b,ra=ns.AuctionBridge,ns.ProfRouteAuto
          local opts={start=1,target=3,autoCraftTools=false,considerAuctionSupply=true}
          local function route()
            local r=ra.Get('alchemy',opts)
            for _=1,1000 do
              ra.Pump('alchemy');r=ra.Get('alchemy',opts)
              if not ra.HasWork('alchemy')then return r end
            end
            error('route did not finish')
          end
          beginFull(1);sendFull({rawRow(11,5,35,'Seller')});finishFull()
          local r=route();assert(r.targetReached and not r.stale and r.total==14)
          local id=r.planID
          clock=clock+10;beginFull(1);sendFull({rawRow(11,5,35,'Seller')});finishFull()
          r=ra.Get('alchemy',opts)
          assert(r.planID==id and not r.stale,'timestamp-only full scan changed the route')
          clock=clock+10;beginFull(1);sendFull({rawRow(11,1,7,'Seller')});finishFull()
          r=ra.Get('alchemy',opts)
          assert(r.planID==id and r.stale and r.staleReason=='supply')
          ra.Recalculate('alchemy',opts);r=route()
          assert(not r.targetReached and #r.auctionSupplyShortages==1 and #requests==0)
        ''')


class AuctionatorFullScanUITests(unittest.TestCase):
    setUp=stock.AuctionSupplyUITests.setUp
    boot=stock.AuctionSupplyUITests.boot

    def test_valid_data_only_needs_recalculation_and_missing_data_requests_a_full_rescan(self):
        self.lua.execute(r'''
          PD.autoSnapshotSlug='alchemy'
          local p={stale=true,staleReason='supply',mats={{id=11,source='ah'}}};PD.autoSnapshot=p
          local available=true
          ns.AuctionBridge={GetAuctionSupply=function()if available then return {quantity=30}end end}
          local function hasCheck()
            for _,button in ipairs(PD.LevelTool())do if button.key=='supply_scan'then return true end end
            return false
          end
          assert(not hasCheck() and not PD.RouteSupplyNeedsRescan(p))
          assert(PD.PlanCacheText(p)==ns.L['拍卖行库存已更新，点击重新计算即可使用。'])
          available=false;assert(not hasCheck() and PD.RouteSupplyNeedsRescan(p))
          assert(PD.PlanCacheText(p)==ns.L['请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'])
          local text=PD.PlanSupplyText({auctionSupplyUnknown=1,mats={{id=11,source='ah'}}})
          assert(text:find('Auctionator',1,true))
          local lines=PD.AuctionSupplyLines({id=11,source='ah',availableCount=10,count=3,
            supplySource='client-auction-results',supplyMethod='auctionator-full-scan'})
          local found=false
          for _,line in ipairs(lines)do
            if line[1]==ns.L['数量来源：Auctionator 完整扫描（已排除本人拍卖）']then found=true end
          end
          assert(found)
        ''')

    def test_automatic_import_messages_exist_in_all_three_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute(r'''
                  for _,key in ipairs({'拍卖行库存已更新，点击重新计算即可使用。',
                    '数量来源：Auctionator 完整扫描（已排除本人拍卖）',
                    '请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。',
                    '有 %d 种物品需要更新在售数量；请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。',
                    '请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。'})do
                    assert(GetLocale()=='zhCN' and ns.L[key] or rawget(ns.L,key),key)
                  end
                ''')


if __name__=='__main__':unittest.main()
