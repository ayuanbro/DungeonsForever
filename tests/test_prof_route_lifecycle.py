"""Replacement jobs release search memory and never freeze a tentative prefix."""
import unittest

import test_prof_runtime as fixture


class RouteLifecycleTests(unittest.TestCase):
    def setUp(self):
        fixture.RuntimeTests.setUp(self)
        fixture.RuntimeTests.live_capture_fixture(self)

    def test_recalculation_releases_suspended_coroutine_before_idle_queue_drains(self):
        self.lua.execute(r'''
          local s,ra=ns.ProfRouteSolver,ns.ProfRouteAuto
          local original=s.NewJob
          tracked=setmetatable({}, {__mode='v'})
          s.NewJob=function(...)
            local j=original(...);tracked[1]=j.co;return j
          end
          ra.Get('alchemy',{start=1,target=2})
          local obsolete=queue[1]
          assert(tracked[1])
          s.NewJob=original
          ra.Recalculate('alchemy',{start=1,target=3})
          collectgarbage('collect');collectgarbage('collect')
          assert(not tracked[1], 'replaced coroutine retained its search frontier')
          local publications=0;ra.OnPlanChanged(function()publications=publications+1 end)
          assert(obsolete() and publications==0)
          assert(finish('alchemy',{start=1,target=3}).targetReached)
        ''')

    def test_completed_job_releases_snapshot_but_keeps_result_and_diagnostics(self):
        self.lua.execute(r'''
          local s,ra=ns.ProfRouteSolver,ns.ProfRouteAuto
          local capture=ns.ProfEconomy.Capture
          tracked=setmetatable({}, {__mode='v'})
          ns.ProfEconomy.Capture=function(...)
            local snap=capture(...);tracked[1]=snap;return snap
          end
          local result=finish('alchemy',{start=1,target=3})
          collectgarbage('collect');collectgarbage('collect')
          assert(not tracked[1], 'finished job retained its normalized input graph')
          assert(result.targetReached and result.searchComplete and #result.steps>0)
          local publications=0;ra.OnPlanChanged(function()publications=publications+1 end)
          for _,pump in ipairs(queue) do assert(pump()) end
          ra.Pump('alchemy');ra.Cancel('alchemy');ra.Continue('alchemy')
          assert(publications==0 and ra.Get('alchemy',{start=1,target=3})==result)
        ''')

    def test_automatic_rebind_waits_until_partial_search_finishes(self):
        self.load(str(fixture.ROOT / 'Core/ProfExecution.lua'))
        self.lua.execute(r'''
          local ra,xp=ns.ProfRouteAuto,ns.ProfExecution
          local old=finish('alchemy',{start=1,target=2})
          assert(xp.Bind('alchemy',old))
          xp.PrepareRecalculate('alchemy')
          local preview=ns.ProfEconomy.Copy(old)
          preview.status='searching';preview.target=10;preview.partial=true;preview.targetReached=false
          assert(not xp.PlanRecalculated('alchemy',preview))
          assert(not xp.GetRun('alchemy'), 'first tentative prefix became a frozen execution plan')
          local settled=ns.ProfEconomy.Copy(preview)
          settled.status='incomplete';settled.plannedTo=8
          local run=assert(xp.PlanRecalculated('alchemy',settled))
          assert(run.plan.plannedTo==8 and run.plan.status=='incomplete')
        ''')

    def test_non_joint_legacy_cache_uses_profession_diagnostic(self):
        self.lua.execute(r'''
          local ra=ns.ProfRouteAuto
          finish('alchemy',{start=1,target=2})
          local c=DungeonsForeverDB.prof.routeCache['Test-Realm']
          local old=c.routes[c.active.alchemy].result
          old.targetUnlearned=nil;old.professionPolicy=nil
          ns.ProfEconomy.Professions=function()return {}end
        ''')
        self.load(str(fixture.ROOT / 'Core/ProfRouteAuto.lua'))
        self.lua.execute(r'''
          local view=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2,allowSecondaryLeveling=false})
          assert(view.status=='recalculate_required' and #view.steps==0)
          assert(view.diagnostics[1].code=='professionChanged')
        ''')


if __name__ == '__main__':
    unittest.main()
