"""Idle expiry and combat suspension against the native executor and HUD."""
import unittest
import test_prof_execution_fusion as execution
import test_prof_hud_voice as hud


class TrackingLifecycleTests(unittest.TestCase):
    load = execution.ExecutionFusionTests.load

    def setUp(self):
        execution.ExecutionFusionTests.setUp(self)
        self.lua.execute('''
          scheduled={};limit=48*60*60;inCombat=false
          InCombatLockdown=function()return inCombat end
          C_Timer={NewTimer=function(delay,fn)
            local t={due=clock+delay,fn=fn}
            function t:Cancel()self.cancelled=true end
            scheduled[#scheduled+1]=t;return t
          end}
          function tick(at)
            clock=at
            for i=1,100 do
              local nextTimer
              for _,t in ipairs(scheduled)do
                if not t.cancelled and not t.fired and t.due<=clock then nextTimer=t;break end
              end
              if not nextTimer then return end
              nextTimer.fired=true;nextTimer.fn()
            end
            error('timer failed to settle')
          end
          function timerCount()
            local n=0;for _,t in ipairs(scheduled)do
              if not t.cancelled and not t.fired then n=n+1 end
            end;return n
          end
          function combat(on)
            inCombat=on
            xp.eventFrame.OnEvent(xp.eventFrame,on and 'PLAYER_REGEN_DISABLED' or 'PLAYER_REGEN_ENABLED')
          end
          xp.RefreshObservation()
        ''')

    def reload(self):
        self.lua.execute('xp.DisableTracking();DungeonsForeverDB=ns.ProfEconomy.Copy(DungeonsForeverDB)')
        self.load('Core/ProfExecution.lua')
        self.lua.execute('initialize();xp=ns.ProfExecution')

    def test_idle_run_ends_at_48_hours_without_repeated_timer_wakeups(self):
        self.lua.execute('''
          assert(timerCount()==1 and #scheduled==1)
          tick(1000+limit-1);assert(xp.GetActive('alchemy')==run)
          tick(1000+limit)
          assert(not xp.GetActive('alchemy') and run.archiveReason=='inactive')
          assert(not next(xp.eventFrame.events) and timerCount()==0)
          assert(xp.Get('alchemy',run.planID)==run)
        ''')

    def test_actual_craft_extends_deadline_but_bags_and_duplicates_do_not(self):
        self.lua.execute('''
          clock=1100;assert(xp.RecordAttempt('alchemy',101,'real'))
          assert(run.lastCraftAt==1100 and #scheduled==1)
          clock=1200;xp.eventFrame.OnEvent(xp.eventFrame,'BAG_UPDATE_DELAYED')
          assert(not xp.RecordAttempt('alchemy',101,'real'))
          xp.Sync('alchemy');xp.Bind('alchemy',plan)
          assert(run.lastCraftAt==1100)
          tick(1000+limit);assert(xp.GetActive('alchemy')==run and timerCount()==1)
          tick(1100+limit);assert(not xp.GetActive('alchemy'))
          assert(xp.GetRecipeTotals('alchemy',run.planID)[1].casts==1)
        ''')

    def test_missed_spell_recovery_counts_as_real_activity(self):
        self.lua.execute('''
          clock=1200
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='recovered'}))
          assert(run.lastCraftAt==1200 and run.attemptsDone==1)
          clock=1300;xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='recovered'})
          assert(run.lastCraftAt==1200 and run.attemptsDone==1)
        ''')

    def test_reload_retains_original_deadline(self):
        self.lua.execute("clock=1100;xp.RecordAttempt('alchemy',101,'real');clock=1100+limit-1")
        self.reload()
        self.lua.execute('''
          assert(xp.GetActive('alchemy').lastCraftAt==1100)
          tick(1100+limit);assert(not xp.GetActive('alchemy'))
        ''')

    def test_offline_time_expires_before_event_observation_resumes(self):
        self.lua.execute('clock=1000+limit')
        self.reload()
        self.lua.execute('''
          assert(not xp.GetActive('alchemy') and not next(xp.eventFrame.events))
          assert(timerCount()==0)
        ''')

    def test_recalculation_carries_activity_time_without_resetting_timeout(self):
        self.lua.execute('''
          clock=1100;xp.RecordAttempt('alchemy',101,'real');local old=run
          clock=1200;xp.PrepareRecalculate('alchemy')
          local p=fixture();p.planID='replacement'
          run=assert(xp.PlanRecalculated('alchemy',p))
          assert(run~=old and run.lastCraftAt==1100)
          tick(1100+limit);assert(not xp.GetActive('alchemy'))
        ''')

    def test_waiting_recalculation_expires_and_cannot_rebind_later(self):
        self.lua.execute('''
          xp.PrepareRecalculate('alchemy');tick(1000+limit)
          assert(not xp.IsPreparing('alchemy') and run.archiveReason=='inactive')
          local p=fixture();p.planID='too-late'
          assert(not xp.PlanRecalculated('alchemy',p) and not xp.GetActive('alchemy'))
        ''')

    def test_expiry_suspends_hud_before_notifying_and_explicit_restart_works(self):
        self.lua.execute('''
          local suspended
          ns.ProfFollow={SuspendAutoTrack=function(slug,reason)
            assert(slug=='alchemy');suspended=reason
          end}
          xp.OnChanged(function(_,_,reason)if reason=='ended'then assert(suspended=='inactive')end end)
          tick(1000+limit);assert(suspended=='inactive')
          local p=fixture();p.executionSourcePlanID=run.planID
          local restarted=assert(xp.StartNew('alchemy',p))
          assert(restarted.status=='active' and restarted.createdAt==clock)
          tick(clock+limit-1);assert(xp.GetActive('alchemy')==restarted)
        ''')

    def test_expiry_is_per_profession(self):
        self.lua.execute('''
          clock=1100;skills.enchanting={cur=1,max=300}
          local p=fixture();p.planID='other';p.executionSteps[1].profession='enchanting'
          local other=assert(xp.Bind('enchanting',p))
          tick(1000+limit)
          assert(not xp.GetActive('alchemy') and xp.GetActive('enchanting')==other)
          assert(xp.eventFrame.events.BAG_UPDATE_DELAYED)
          tick(1100+limit);assert(not next(xp.eventFrame.events))
        ''')

    def test_manual_end_and_disable_cancel_the_idle_timer(self):
        self.lua.execute('''
          local stale=scheduled[1];xp.End('alchemy','cancel');assert(timerCount()==0)
          local replacement=xp.StartNew('alchemy',fixture());stale.fn()
          assert(xp.GetActive('alchemy')==replacement and timerCount()==1)
          xp.DisableTracking();assert(timerCount()==0 and not next(xp.eventFrame.events))
        ''')

    def test_combat_detaches_heavy_events_and_sync_does_not_scan_professions(self):
        self.lua.execute('''
          local calls=0;ns.ProfEconomy.Professions=function()calls=calls+1;return skills end
          combat(true)
          assert(xp.eventFrame.events.PLAYER_REGEN_ENABLED)
          assert(not xp.eventFrame.events.BAG_UPDATE_DELAYED and not xp.eventFrame.events.UNIT_SPELLCAST_SUCCEEDED)
          assert(not xp.eventFrame.events.CHAT_MSG_LOOT)
          xp.Sync('alchemy');xp.eventFrame.OnEvent(xp.eventFrame,'BAG_UPDATE_DELAYED')
          assert(calls==0 and xp.GetActive('alchemy')==run)
          assert(not xp.RecordAttempt('alchemy',101,'combat-cast'))
          assert(not xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='combat-cast'}))
          assert(run.attemptsDone==0 and run.lastCraftAt==nil)
        ''')

    def test_combat_retains_known_late_receipt_without_route_work_or_new_crafts(self):
        self.lua.execute('''
          xp.RecordAttempt('alchemy',101,'before-combat')
          local calls,notifications=0,0
          ns.ProfEconomy.Professions=function()calls=calls+1;return skills end
          xp.OnChanged(function()notifications=notifications+1 end)
          combat(true);assert(xp.eventFrame.events.TRADE_SKILL_ITEM_CRAFTED_RESULT)
          clock=1100
          assert(xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='before-combat'}))
          assert(not xp.RecordCraftedResult({itemID=10,quantity=3,castGUID='during-combat'}))
          assert(calls==0 and notifications==0 and run.attemptsDone==1 and run.lastCraftAt==1000)
          combat(false)
          assert(calls>0 and notifications>0 and xp.Progress('alchemy',1).actualOutputs==3)
          assert(xp.eventFrame.events.UNIT_SPELLCAST_SUCCEEDED)
        ''')

    def test_combat_exit_resyncs_bags_without_replacing_plan_or_inventing_crafts(self):
        self.lua.execute('''
          local frozen=run.plan;combat(true);bag[10]=6;skills.alchemy.cur=3
          xp.Sync('alchemy');assert(run.currentIndex==1)
          combat(false)
          assert(run.plan==frozen and run.currentIndex==2 and run.attemptsDone==0)
        ''')

    def test_expiry_during_combat_is_not_undone_on_exit(self):
        self.lua.execute('''
          combat(true);tick(1000+limit);combat(false)
          assert(not xp.GetActive('alchemy') and not next(xp.eventFrame.events))
          assert(timerCount()==0)
        ''')

    def test_reload_in_combat_keeps_plan_but_does_not_attach_craft_events(self):
        self.lua.execute('inCombat=true')
        self.reload()
        self.lua.execute('''
          assert(xp.GetActive('alchemy') and xp.eventFrame.events.PLAYER_REGEN_ENABLED)
          assert(not xp.eventFrame.events.BAG_UPDATE_DELAYED)
          combat(false);assert(xp.eventFrame.events.BAG_UPDATE_DELAYED)
        ''')

    def test_explicit_start_waits_until_out_of_combat(self):
        self.lua.execute('''
          combat(true);xp.End('alchemy','cancel')
          assert(not xp.StartNew('alchemy',fixture()))
          inCombat=false;assert(xp.StartNew('alchemy',fixture()))
        ''')


class TrackingHUDTests(unittest.TestCase):
    boot = hud.HUDVoiceTests.boot
    setUp = hud.HUDVoiceTests.setUp

    def test_combat_hud_skips_progress_and_renders_and_resumes(self):
        self.lua.execute('''
          local savedSync=xp.Sync;local calls=0
          xp.Sync=function(...)calls=calls+1;return savedSync(...)end
          xp.eventFrame.OnEvent(xp.eventFrame,'PLAYER_REGEN_DISABLED')
          assert(pf.f.skill:GetText()==ns.L['战斗中暂停追踪，脱战后自动恢复。'])
          calls=0
          for i=1,10 do assert(not pf.Sync());pf.Paint()end
          local timersBefore=#timers;pf.f.scripts.OnEvent(pf.f,'BAG_UPDATE_DELAYED')
          assert(calls==0 and #timers==timersBefore)
          xp.eventFrame.OnEvent(xp.eventFrame,'PLAYER_REGEN_ENABLED')
          assert(calls>0 and pf.f.skill:GetText()~=ns.L['战斗中暂停追踪，脱战后自动恢复。'])
        ''')

    def test_expiry_leaves_hud_stopped_until_explicit_restart(self):
        self.lua.execute('''
          clock=clock+48*60*60;xp.ExpireIdle()
          assert(follow.autoTrackSuspended=='inactive' and not xp.GetActive('alchemy'))
          assert(pf.f.skill:GetText()==ns.L['48 小时无制作，追踪已自动结束。'])
          for i=1,5 do pf.Sync();pf.Paint()end
          assert(not xp.GetActive('alchemy'))
          xp.StartNew('alchemy',run.plan)
          assert(xp.GetActive('alchemy') and not follow.autoTrackSuspended)
          assert(pf.f.skill:GetText()~=ns.L['48 小时无制作，追踪已自动结束。'])
        ''')


if __name__ == '__main__':
    unittest.main()
