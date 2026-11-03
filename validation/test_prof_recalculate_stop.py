"""Explicit page recalculation stops execution while preserving route inputs."""
import unittest

import test_prof_hud_voice as hud
import test_prof_ui_fusion as ui


PAGE_HELPERS = r'''
xp=ns.ProfExecution;ra=ns.ProfRouteAuto
DungeonsForeverDB.prof.lvTarget.alchemy=3
ns.ProfEconomy.Capture=function(slug,opts)
  local s=fixture();s.executionInventory=opts.executionInventory
  s.recipes[1].profession=slug;s.professions={[slug]={cur=1,max=300}}
  s.known={[slug..':101']=true}
  return ns.ProfEconomy.Index(s)
end
function pageOptions()
  return PD.BuildLvOpts('alchemy',skills.alchemy.cur)
end
function finishPage()
  PD.RowsLeveling({})
  for i=1,100 do
    ra.Pump('alchemy');PD.RowsLeveling({})
    if not ra.HasWork('alchemy') then
      local result=assert(PD.autoSnapshot)
      assert(result.feasible and #result.executionSteps>0)
      return result
    end
  end
  error('page recalculation did not finish')
end
function pageClick(key)
  local _,click=PD.LevelTool();click(key)
end
function trackButton()
  local list=PD.LevelTool()
  for _,entry in ipairs(list)do if entry.key=='track' then return entry end end
  error('missing execution button')
end
'''


class RecalculateStopPageTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot

    def setUp(self):
        self.boot('zhCN')
        self.lua.execute(PAGE_HELPERS)

    def test_running_without_hud_stops_immediately_and_restarts_only_on_click(self):
        self.lua.execute(r'''
          assert(not ns.ProfFollow)
          local original=finishPage();local old=assert(xp.StartNew('alchemy',original))
          assert(original.total==14 and xp.RecordAttempt('alchemy',101,'before-recalculate'))
          local progress=old.progress;bag[11]=1
          pageClick('recalc')
          assert(not xp.GetActive('alchemy'),'recalculate left execution active until rendering')
          assert(old.status=='archived' and old.endedAt and old.attemptsDone==1)
          assert(xp.Get('alchemy',old.planID)==old and old.progress==progress)
          assert(xp.GetContinuation('alchemy')[11]==1,'stopping discarded current bag stock')
          assert(PD.forceExact and not PD.autoSnapshot)
          assert(trackButton().text==ns.L['开始执行'] and not trackButton().on)
          PD.RowsLeveling({})
          assert(PD.autoSnapshot.status=='searching' and not xp.GetActive('alchemy'))
          local result=finishPage()
          assert(result.planID~=original.planID and next(result.seedInventory)==nil)
          assert(result.total==14 and result.mats[1].count==2,'backpack stock changed the route cost')
          assert(original.total==14 and old.plan.total==14 and old.attemptsDone==1)
          assert(not xp.GetActive('alchemy'),'finished candidate automatically resumed execution')
          assert(trackButton().text==ns.L['开始执行'])
          pageClick('track')
          local fresh=assert(xp.GetActive('alchemy'))
          assert(fresh~=old and fresh.planID==result.planID and fresh.plan.total==14)
          assert(fresh.inheritedFrom==old.planID and old.attemptsDone==1)
        ''')

    def test_recalculation_without_execution_retains_candidate_revert(self):
        self.lua.execute(r'''
          local original=finishPage()
          assert(not xp.GetActive('alchemy') and not PD.HasPlanPrev())
          pageClick('recalc');PD.RowsLeveling({})
          assert(PD.HasPlanPrev(),'stopping an empty execution removed candidate undo')
          local candidate=finishPage()
          assert(candidate.planID~=original.planID and not xp.GetActive('alchemy'))
          assert(PD.HasPlanPrev() and PD.RevertPlan())
          assert(PD.autoSnapshot.planID==original.planID and not PD.HasPlanPrev())
          PD.RowsLeveling({})
          assert(PD.autoSnapshot.planID==original.planID and not ra.HasWork('alchemy'))
          assert(not xp.GetActive('alchemy'))
        ''')

    def test_recalculation_does_not_end_another_professions_execution(self):
        self.lua.execute(r'''
          local original=finishPage();local old=assert(xp.StartNew('alchemy',original))
          local s=fixture();s.recipes[1].profession='enchanting'
          s.professions={enchanting={cur=1,max=300}};s.known={['enchanting:101']=true}
          local otherPlan=ra.Compute('enchanting',{snapshot=s,start=1,target=3})
          local other=assert(xp.StartNew('enchanting',otherPlan))
          assert(xp.RecordAttempt('enchanting',101,'other-cast'))
          local otherProgress=other.progress;local otherID=other.planID
          pageClick('recalc')
          assert(not xp.GetActive('alchemy') and old.status=='archived')
          assert(xp.GetActive('enchanting')==other and other.status=='active')
          finishPage()
          assert(not xp.GetActive('alchemy') and xp.GetActive('enchanting')==other)
          assert(other.planID==otherID and other.progress==otherProgress and other.attemptsDone==1)
        ''')


class RecalculateStopHUDTests(unittest.TestCase):
    boot = ui.ProfessionUIFusionTests.boot
    setUpHUD = hud.HUDVoiceTests.setUp

    def setUp(self):
        self.setUpHUD()
        self.lua.execute(PAGE_HELPERS)

    def test_visible_hud_is_suspended_before_end_callbacks_and_cannot_rebind(self):
        self.lua.execute(r'''
          local old=run;local oldID=old.planID
          assert(pf.f:IsShown() and xp.GetActive('alchemy')==old)
          local nativeBind=xp.Bind;bindCalls=0
          xp.Bind=function(...)
            bindCalls=bindCalls+1;return nativeBind(...)
          end
          local nativeEnd=ra.EndExecution;endCalls=0;endedEvents=0
          ra.EndExecution=function(slug)
            assert(slug=='alchemy' and follow.autoTrackSuspended=='recalculate',
              'HUD must be suspended before synchronous end notifications')
            endCalls=endCalls+1
            return nativeEnd(slug)
          end
          xp.OnChanged(function(slug,_,reason)
            if slug=='alchemy' and reason=='ended' then
              assert(follow.autoTrackSuspended=='recalculate')
              endedEvents=endedEvents+1
            end
          end)
          pageClick('recalc')
          assert(endCalls==1 and endedEvents==1 and bindCalls==0)
          assert(not xp.GetActive('alchemy') and old.status=='archived')
          for i=1,5 do pf.Sync();pf.Paint();xp.RefreshObservation()end
          assert(bindCalls==0 and not xp.GetActive('alchemy'))
          local candidate=finishPage()
          assert(candidate.planID~=oldID and follow.autoTrackSuspended=='recalculate')
          for i=1,5 do pf.RefreshRoute('alchemy');pf.Sync();pf.Paint()end
          assert(bindCalls==0 and not xp.GetActive('alchemy'),
            'HUD or finished-plan publication rebound a candidate')
          assert(pf.f:IsShown() and trackButton().text==ns.L['开始执行'])
          pageClick('track')
          local fresh=assert(xp.GetActive('alchemy'))
          assert(bindCalls==1 and fresh.planID==candidate.planID and fresh~=old)
        ''')

    def test_recalculation_clears_only_the_completed_plan_for_the_current_profession(self):
        self.lua.execute(r'''
          local completed=run.plan
          xp.End('alchemy','completed')
          assert(pf.endedPlan.alchemy==completed and not xp.GetActive('alchemy'))
          local other={planID='other-completed'};pf.endedPlan.enchanting=other
          pageClick('recalc')
          assert(not pf.endedPlan.alchemy,'completed HUD route survived explicit recalculation')
          assert(pf.endedPlan.enchanting==other and follow.autoTrackSuspended=='recalculate')
          local candidate=finishPage()
          pf.RefreshRoute('alchemy');pf.Sync();pf.Paint()
          assert(candidate.planID~=completed.planID and not xp.GetActive('alchemy'))
          assert(not pf.endedPlan.alchemy and pf.endedPlan.enchanting==other)
          assert(follow.step<=#candidate.executionSteps,
            'HUD still derives the completed position from the discarded route')
          assert(pf.f.card:IsShown() and pf.f.card.__step==follow.step)
        ''')


if __name__ == '__main__':
    unittest.main()
