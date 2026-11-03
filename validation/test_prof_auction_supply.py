"""Auctionator full-scan snapshots -> finite route budgets, using the native Lua 5.1 code.

No client files are read or written. These mocks verify accounting and lifecycle;
actual server event timing still requires an in-game test of the project build.
"""
import unittest
from test_prof_solver_fusion import LuaRuntime, ROOT
import test_prof_route_plans as routes
import test_prof_ui_fusion as ui


BRIDGE_MOCKS = r'''
ns={LoadForeverPages=true,L=setmetatable({},{__index=function(_,k)return k end})}
-- Use a short deterministic expiry for isolated bridge lifecycle tests.
ns.ProfRouteAuto={MaxStaleSeconds=function()return 1800 end}
DungeonsForeverDB={prof={}};clock=10000;timers={};frames={};requests={};messages={}
function time()return clock end
function UnitName()return 'Player' end
function GetRealmName()return 'Realm' end
function UnitFactionGroup()return 'Alliance' end
function GetItemInfo(id)return 'Item'..id end
DEFAULT_CHAT_FRAME={AddMessage=function(_,s)messages[#messages+1]=s end}
AuctionFrame={IsShown=function()return true end}
function CreateFrame()
 local f={events={}}
 function f:RegisterEvent(e)self.events[e]=true end
 function f:UnregisterAllEvents()self.events={}end
 function f:SetScript(k,fn)self[k]=fn end
 frames[#frames+1]=f;return f
end
C_Timer={NewTimer=function(delay,fn)
 local t={fn=fn,delay=delay};function t:Cancel()self.cancelled=true end
 timers[#timers+1]=t;return t
end}
function step()
 while #timers>0 do
  local t=table.remove(timers,1)
  if not t.cancelled then t.fn();return end
 end
 error('no timer')
end
function event(e,arg)
 for _,f in ipairs(frames)do if f.events[e]then f.OnEvent(f,e,arg)end end
end
function QueryAuctionItems()error('inventory reading must not send a query')end
function CanSendAuctionQuery()return true end
function GetNumAuctionItems()return 0,0 end
function hooksecurefunc()error('inventory reading must not hook queries')end
'''


class AuctionSupplyBridgeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BRIDGE_MOCKS)
        self.load = self.lua.eval("function(s)assert(loadstring(s))('DungeonsForever',ns)end")
        self.load((ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))

    def test_standalone_scanner_is_removed(self):
        self.lua.execute(r'''
          local b=ns.AuctionBridge
          assert(b.StartSupplyScan==nil and b.CancelSupplyScan==nil)
          assert(b.SupplyScanActive==nil and b.SupplyScanProgress==nil)
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='unknown')
          assert(DungeonsForeverDB.prof.auctionSupply==nil and #requests==0)
        ''')

    def test_old_manual_cache_never_becomes_a_purchase_budget(self):
        self.lua.execute(r'''
          local b=ns.AuctionBridge
          local old={q=999,p=7,t=clock,c=true,ox=true,mk='Realm:Alliance',ob='Player',
            s='client-auction-results',v=2}
          DungeonsForeverDB.prof.auctionSupply={[11]=old}
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='unknown')
          assert(DungeonsForeverDB.prof.auctionSupply[11]==old and #requests==0)
        ''')

    def test_only_valid_full_scan_batches_provide_available_quantity(self):
        self.lua.execute(r'''
          local b=ns.AuctionBridge
          local batch={v=2,c=true,t=clock,mk='Realm:Alliance',ob='Player',items={[11]={q=7,p=20}}}
          DungeonsForeverDB.prof.auctionFullScan=batch
          assert(b.GetAuctionSupply(11).quantity==7 and b.GetAuctionSupply(12).quantity==0)
          clock=clock+1801
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='expired')
          clock=clock-1801;GetRealmName=function()return 'AnotherRealm'end
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='unverified')
          GetRealmName=function()return 'Realm'end;UnitName=function()return 'Other'end
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(11)=='unverified')
          UnitName=function()return 'Player'end;batch.c=false
          assert(b.GetAuctionSupply(11)==nil and b.GetAuctionSupplyStatus(12)=='incomplete')
          batch.c=true;batch.items[11].q=-1;assert(b.GetAuctionSupply(11)==nil)
          batch.items[11].q=0;assert(b.GetAuctionSupply(11).quantity==0)
          assert(#requests==0)
        ''')

    def test_real_capture_freezes_the_full_scan_budget_and_marks_expiration(self):
        for name in ('ProfPolicies','ProfRouteAuto','ProfEssences','ProfSolverCapture','ProfRouteSolver'):
            self.load((ROOT/'Core'/(name+'.lua')).read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfModule={ProfLearned=function()return {alchemy={cur=1,max=300}}end}
          ns.ProfRecipes={alchemy={rows={{101,10,1,'',nil,nil,1,100,200,300,false,{{11,1}}}}}}
          IsPlayerSpell=function()return true end;UnitLevel=function()return 60 end
          DungeonsForeverDB.prof.auctionFullScan={v=2,c=true,t=clock,mk='Realm:Alliance',ob='Player',
            items={[11]={q=1,p=7}}}
          local s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3,autoCraftTools=false,considerAuctionSupply=true})
          assert(s.prices[11]==7 and s.auctionSupply[11].quantity==1)
          DungeonsForeverDB.prof.auctionFullScan.items[11].q=100
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false})
          assert(not r.targetReached and #r.auctionSupplyShortages==1)
          assert(s.auctionSupply[11].quantity==1,'in-flight budget changed with saved data')
          Auctionator={API={v1={GetAuctionPriceByItemID=function()return 7 end}}}
          clock=clock+1801
          s=ns.ProfEconomy.Capture('alchemy',{start=1,target=3,autoCraftTools=false,considerAuctionSupply=true})
          assert(s.auctionSupply[11]==nil and s.auctionSupplyStatus[11]=='expired')
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3,autoCraftTools=false})
          assert(r.targetReached and r.auctionSupplyUnknown==1 and not r.purchaseVerified)
          assert(r.mats[1].supplyStatus=='expired' and #requests==0)
        ''')


class AuctionSupplyRouteTests(unittest.TestCase):
    setUp = routes.NativeRoutePlansTests.setUp

    def test_all_strategies_respect_shared_stock_and_take_an_alternative(self):
        self.lua.execute(r'''
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'})do
            local s=fixture();s.auctionSupply={[11]={quantity=1},[12]={quantity=20}}
            local alt=ns.ProfEconomy.Copy(s.recipes[1]);alt.spell=102;alt.mats={{12,1}}
            s.recipes[2]=alt;s.prices[12]=10;s.known['alchemy:102']=true
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=4,scheme=scheme})
            assert(r.targetReached and r.supplyComplete and r.purchaseVerified,scheme)
            local used=0;for _,m in ipairs(r.mats)do if m.id==11 or m[1]==11 then used=used+m.count end end
            assert(used<=1 and r.total>=27,scheme..' overspent observed stock')
          end
        ''')

    def test_shortage_reports_item_and_required_remaining_counts(self):
        self.lua.execute(r'''
          local s=fixture();s.auctionSupply={[11]={quantity=0}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(not r.targetReached and not r.supplyComplete and #r.auctionSupplyShortages==1)
          local d=r.auctionSupplyShortages[1]
          assert(d.item==11 and d.required>0 and d.available==0)
          assert(ns.ProfEconomy.DiagnosticText(d):find('#11',1,true))
          s.prices={}
          r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(not r.targetReached and #r.auctionSupplyShortages==1,
            'a missing quote hid observed zero stock')
        ''')

    def test_unknown_partial_and_historical_supply_are_estimates_never_verified_or_optimal(self):
        self.lua.execute(r'''
          for _,supply in ipairs({{}, {[11]={quantity=0,complete=false}},
            {[11]={quantity=0,source='auctionator-update'}}, {[11]={quantity=99,ownerExcluded=false}}})do
            local s=fixture();s.auctionSupply=supply
            local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3})
            assert(r.targetReached and r.auctionSupplyUnknown==1 and not r.supplyComplete)
            assert(not r.purchaseVerified and not r.optimal and not r.inputModelOptimal)
          end
        ''')

    def test_materials_and_formula_share_one_budget_and_use_vendor_remainder(self):
        self.lua.execute(r'''
          local s=fixture();s.known={};s.recipes[1].formula=11
          s.auctionSupply={[11]={quantity=2}}
          s.offers={[11]={{npcID=7,price=20,quantity=1,unlimited=true}}}
          local r=ns.ProfRouteAuto.Compute('alchemy',{snapshot=s,start=1,target=3,noFormula=false})
          assert(r.targetReached and r.supplyComplete)
          local used=0
          for _,a in ipairs(r.actions)do
            if (a.type=='buy' or a.type=='formula') and a.source=='ah' and a.item==11 then used=used+a.count end
          end
          assert(used<=2 and r.total>=34)
        ''')


class AuctionSupplyUITests(unittest.TestCase):
    setUp = ui.ProfessionUIFusionTests.setUp
    boot = ui.ProfessionUIFusionTests.boot

    def test_missing_stock_has_a_rescan_hint_without_any_scanner_controls(self):
        self.lua.execute(r'''
          PD.autoSnapshotSlug='alchemy';PD.autoSnapshot={auctionSupplyUnknown=1,mats={{id=11,source='ah'}}}
          ns.AuctionBridge={GetAuctionSupply=function()return nil end}
          for _,page in ipairs({'route','shop','recovery','log'})do
            PD.autoPage=page
            for _,button in ipairs(PD.LevelTool())do
              assert(button.key~='supply_scan' and button.key~='rec_scan')
            end
          end
          assert(PD.ScanRouteSupply==nil and PD.SolverText()==nil)
          assert(PD.SnapshotBadgeState({planVersion=2,completeCost=true,supplyComplete=false})=='stock_unknown')
          assert(PD.SnapshotBadgeState({planVersion=2,status='infeasible',completeCost=false,
            auctionSupplyShortages={{item=11}}})=='stock_short')
          assert(PD.AuctionSupplyText({source='ah',supplyObserved=false,supplyStatus='expired'})==
            ns.L['库存观测已过期；请在 Auctionator 重新完整扫描后计算路线。'])
          assert(PD.PlanSupplyText({feasible=false,auctionSupplyCandidates={11}})==nil,
            'an unused catalogue material requested a full scan')
          assert(PD.PlanSupplyText({feasible=false,auctionSupplyUnknown=1,
            mats={{id=11,source='ah'}}}):find('Auctionator',1,true))
        ''')

    def test_recovery_detail_has_no_independent_inventory_scan(self):
        self.lua.execute(r'''
          PD.Wrap=function(text)return {text}end
          local rows={};PD.RowsRecoveryDetail(rows,{saleOutputs={},recoveryTotal=0,total=0})
          for _,row in ipairs(rows)do
            for _,button in ipairs(row.segs or {})do assert(button.key~='rec_scan')end
          end
          assert(rows[1].segs[1].key=='rec_fee')
        ''')

    def test_stock_messages_are_localized_and_optim_does_not_hide_stock_warnings(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                self.boot(locale)
                self.lua.execute(r'''
                  for _,key in ipairs({'数量未核实',
                    '库存观测已过期；请在 Auctionator 重新完整扫描后计算路线。',
                    '库存数据缺失或已过期，请在 Auctionator 重新完整扫描后计算路线。'})do assert(GetLocale()=='zhCN' and ns.L[key] or rawget(ns.L,key))end
                  assert(PD.SnapshotBadgeState({planVersion=2,scheme='optim',supplyComplete=false})=='stock_unknown')
                ''')


if __name__=='__main__':
    unittest.main()
