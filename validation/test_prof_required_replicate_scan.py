"""Require valid completed replicate snapshots at profession route entry points."""
import unittest
import test_prof_route_plans as routes
from test_prof_auctionator_full_scan import SOURCE_MOCK

ROOT=routes.ROOT


class RequiredReplicateScanTests(unittest.TestCase):
    def setUp(self):
        routes.NativeRoutePlansTests.setUp(self)
        self.lua.execute('ns.IsForever=true')
        self.lua.execute(SOURCE_MOCK)
        self.lua.execute('''
          fullTimers={}
          C_Timer.NewTimer=function(delay,fn)
            local h={fn=fn,due=clock+delay};function h:Cancel()self.cancelled=true end
            fullTimers[#fullTimers+1]=h;return h
          end
          function step()
            local pending=fullTimers;fullTimers={}
            for _,h in ipairs(pending)do
              if not h.cancelled then
                if h.due<=clock then h.fn()else fullTimers[#fullTimers+1]=h end
              end
            end
          end
        ''')
        self.load((ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
          ra=ns.ProfRouteAuto;bridge=ns.AuctionBridge;xp=ns.ProfExecution
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.stamp=clock;s.auctionSupply={[11]=bridge.GetAuctionSupply(11)}
            return ns.ProfEconomy.Index(s)
          end
          function scan()
            clock=clock+1
            beginFull(2);sendFull({rawRow(11,8,56,'Seller'),rawRow(11,99,1,'Test')});finishFull()
            assert(bridge.ReplicateScanReady() and bridge.GetAuctionSupply(11).quantity==8)
          end
          function assertBlocked(fn,slug,opts,reason)
            local r=fn(slug,opts)
            assert(r.status=='recalculate_required' and r.feasible==false)
            assert(#r.steps==0 and #r.mats==0 and r.diagnostics[1].code==reason)
          end
        ''')

    def test_mode_and_completed_scan_are_required_regardless_of_settings_or_supplied_snapshot(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()error('blocked route captured inputs')end
          for _,state in ipairs({'disabled','unreadable','enabled'})do
            Auctionator.Config.Get=function()
              if state=='unreadable' then return nil end
              return state=='enabled'
            end
            local reason=state=='disabled' and 'replicateModeDisabled'
              or state=='unreadable' and 'replicateModeUnknown' or 'replicateScanRequired'
            for _,fn in ipairs({ra.Get,ra.Compute,ra.Recalculate,ra.FixedPlan})do
              for _,slug in ipairs({'alchemy','first-aid','poisons'})do
                for _,scheme in ipairs({'cheapest','stable','fishing','fixed'})do
                  for _,enabled in ipairs({false,true})do
                    local opts={start=1,target=3,scheme=scheme,recoveryEnabled=enabled,
                      considerAuctionSupply=enabled,onlyAH=enabled}
                    assertBlocked(fn,slug,opts,reason)
                    opts.snapshot=fixture();assertBlocked(fn,slug,opts,reason)
                  end
                end
              end
            end
          end
          assert(not ra.HasWork() and #queue==0)
        ''')

    def test_missing_bridge_and_failed_mode_read_cannot_bypass_gate(self):
        self.lua.execute('''
          ns.AuctionBridge=nil
          assertBlocked(ra.Get,'alchemy',{start=1,target=3},'replicateModeUnknown')
          local run,reason=xp.StartNew('alchemy',{})
          assert(not run and reason=='replicateModeUnknown')
          ns.AuctionBridge=bridge;scan()
          Auctionator.Config.Get=function()error('not readable')end
          local q=bridge.GetAuctionSupply(11)
          assert(q.quantity==8 and bridge.ReplicateScanReady())
          assert(ra.Compute('alchemy',{start=1,target=3}).targetReached)
        ''')

    def test_scan_must_finish_importing_before_routes_can_use_its_quantities(self):
        self.lua.execute('''
          beginFull(1)
          assertBlocked(ra.Compute,'alchemy',{start=1,target=3},'replicateScanRequired')
          sendFull({rawRow(11,8,56,'Seller')})
          assert(bridge.FullScanStatus().status=='processing')
          assertBlocked(ra.Compute,'alchemy',{start=1,target=3},'replicateScanRequired')
          finishFull()
          local result=ra.Compute('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(result.targetReached and result.total==14)
          assert(result.mats[1].availableCount==8 and result.auctionSupplyUnknown==0)
          assert(DungeonsForeverDB.prof.auctionFullScan.items[11].q==8 and DungeonsForeverDB.prof.auctionReplicateGate==nil)
        ''')

    def test_failed_partial_and_summary_scans_keep_last_success_until_expiry(self):
        self.lua.execute('''
          scan();beginFull(1);Auctionator.EventBus:Emit(Auctionator.FullScan.Events.ScanFailed)
          assert(bridge.ReplicateScanReady() and bridge.GetAuctionSupply(11).quantity==8)
          scan();beginFull(2);sendFull({rawRow(11,8,56,'Seller')});finishFull()
          assert(bridge.ReplicateScanReady() and bridge.GetAuctionSupply(11).quantity==8)
          scan();Auctionator.SavedState.TimeOfLastBrowseScan=clock
          assert(bridge.ReplicateScanReady() and bridge.GetAuctionSupply(11).quantity==8)
          scan();assert(ra.Compute('alchemy',{start=1,target=3}).targetReached)
        ''')

    def test_mid_search_expiry_blocks_pump_resume_and_new_execution(self):
        self.lua.execute('''
          scan();local candidate=ra.Get('alchemy',{start=1,target=3})
          assert(ra.HasWork('alchemy'))
          clock=clock+172801
          ns.ProfRouteSolver.Run=function()error('stale scan search advanced')end
          ra.Pump('alchemy')
          assert(candidate.searchTermination=='replicate_scan_required' and not ra.HasWork('alchemy'))
          assert(ra.Continue('alchemy')==false)
          local bound,reason=xp.StartNew('alchemy',candidate)
          assert(not bound and reason=='replicateScanRequired')
          assert(not xp.GetRun('alchemy'))
        ''')

    def test_rebuild_and_reserve_change_cannot_bypass_gate_or_destroy_candidate(self):
        self.lua.execute('''
          scan();local opts={start=1,target=3,considerAuctionSupply=true}
          local candidate=finish('alchemy',opts)
          local before=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local skel
          for _,record in pairs(before.routes)do skel=record.skeleton;break end
          assert(skel)
          local nextID=before.nextID
          clock=clock+172801
          assertBlocked(function(slug,supplied)return ra.RebuildFromSkel(slug,skel,supplied)end,
            'alchemy',opts,'replicateScanRequired')
          local blocked=ra.ChangeReserveMode('alchemy','ample')
          assert(blocked.status=='recalculate_required' and blocked.diagnostics[1].code=='replicateScanRequired')
          assert(ra.Peek('alchemy')==candidate and before.nextID==nextID and not ra.HasWork('alchemy'))
        ''')

    def test_empty_complete_market_is_ready_but_is_not_an_infinite_material_budget(self):
        self.lua.execute('''
          beginFull(0);sendFull({});finishFull()
          assert(bridge.ReplicateScanReady())
          assert(bridge.GetAuctionSupply(11).quantity==0)
          local p=ra.Compute('alchemy',{start=1,target=3,considerAuctionSupply=true})
          assert(not p.targetReached and p.auctionSupplyUnknown==0)
          for _,entry in ipairs(p.mats or {})do assert((entry.count or 0)==0)end
        ''')


class RequiredReplicateScanUITests(unittest.TestCase):
    def test_blocked_auto_and_fixed_pages_show_scan_action_without_false_recipe_warning(self):
        import test_prof_ui_fusion as ui
        for locale in ('zhCN','zhTW','enUS'):
            fixture=ui.ProfessionUIFusionTests();fixture.boot(locale)
            fixture.lua.execute("""
              ns.IsForever=true;PD.AuctionatorState=function()return 'ok'end
              PD.Wrap=function(text)return {text}end
              ns.AuctionBridge={ReplicateScanReady=function()return false,'replicateScanRequired'end}
              local notice=PD.ReplicateScanMessage('replicateScanRequired')
              for _,slug in ipairs({'alchemy','first-aid'})do
                for _,auto in ipairs({false,true})do
                  PD.cur=slug;PD.autoPage='route';PD.SetSettingRaw('autoRoute',auto)
                  local rows={};PD.RowsLeveling(rows);local n=0
                  for _,row in ipairs(rows)do if row.text==notice then n=n+1 end end
                  assert(n==1,slug..':'..n)
                  assert(PD.autoSnapshot.status=='recalculate_required' and #PD.autoSnapshot.steps==0)
                  for _,line in ipairs(PD.warnNotes and PD.warnNotes.warnings or {})do
                    assert(line[1]~=ns.L['固定路线中有配方资料或学习条件未确认，请在游戏中核对。'])
                    assert(line[1]~=ns.L['固定攻略包含不可执行步骤，请切换自动规划或先满足学习条件。'])
                  end
                  assert(not ns.ProfExecution.GetRun(slug))
                end
              end
            """)

    def test_hud_keeps_pending_scan_reason_for_auto_and_fixed_routes(self):
        import test_prof_hud_voice as hud
        fixture=hud.HUDVoiceTests();fixture.setUp()
        fixture.lua.execute("""
          xp.End('alchemy');pf.endedPlan=nil
          ns.IsForever=true;PD.AuctionatorState=function()return 'ok'end
          ns.AuctionBridge={ReplicateScanReady=function()return false,'replicateScanRequired'end}
          follow.autoTrackSuspended=nil
          for _,auto in ipairs({true,false})do
            PD.SetSettingRaw('autoRoute',auto);pf.RefreshRoute('alchemy')
            local pending=pf.pendingPlans.alchemy
            assert(pending.status=='recalculate_required' and pending.diagnostics[1].code=='replicateScanRequired')
            assert(not xp.GetRun('alchemy'))
            pf.Paint()
            assert(pf.f.finish:GetText()==PD.ReplicateScanMessage('replicateScanRequired'))
          end
        """)


class RequiredReplicateSupplementTests(unittest.TestCase):
    def test_topup_requires_scan_before_start_and_each_slice_without_erasing_progress(self):
        import test_prof_execution_fusion as execution
        fixture=execution.ExecutionSupplementSolverTests();fixture.setUp()
        fixture.lua.execute("""
          ns.IsForever=true;local ready=false
          ns.AuctionBridge={ReplicateScanReady=function()return ready,'replicateScanRequired'end}
          ns.IdleJobs={Add=function(fn)pendingPump=fn end}
          local plan=run.plan;local casts=xp.Progress('alchemy',1).casts
          local blocked,reason=xp.CalculateSupplement('alchemy')
          assert(not blocked and reason=='replicateScanRequired' and run.supplement==nil)
          ready=true;local state=assert(xp.CalculateSupplement('alchemy'))
          assert(state.inFlight and pendingPump)
          ready=false;assert(pendingPump())
          assert(state.status=='recalculate_required' and state.error=='replicateScanRequired')
          assert(not state.inFlight and not state.appended)
          assert(run.plan==plan and #plan.executionSteps==1 and xp.Progress('alchemy',1).casts==casts)
          ready=true;local result=assert(xp.CalculateSupplement('alchemy'))
          for i=1,5000 do if not result.inFlight then break end;xp.Pump('alchemy')end
          assert(result.appended and result.total==4)
          assert(xp.Progress('alchemy',2).casts==casts)
        """)


if __name__=='__main__':unittest.main()
