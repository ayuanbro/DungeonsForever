"""The route facade keeps persisted execution separate from search publication."""
import unittest

import test_prof_runtime as fixture


class ExecutionFacadeTests(unittest.TestCase):
    def setUp(self):
        fixture.RuntimeTests.setUp(self)
        fixture.RuntimeTests.live_capture_fixture(self)
        self.load(str(fixture.ROOT / 'Core' / 'ProfExecution.lua'))
        self.lua.execute('''
          ns.ProfEconomy.Professions=function()return {alchemy={cur=liveSkill,max=300}}end
        ''')

    def test_plan_identity_survives_reload_and_changes_only_on_new_calculation(self):
        self.lua.execute('''
          opts={start=1,target=2};original=finish('alchemy',opts)
          assert(original.executionVersion==1 and original.planID)
          planID=original.planID
        ''')
        self.load(str(fixture.ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute('''
          local restored=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(restored.planID==planID and restored.cached)
          ns.ProfRouteAuto.Recalculate('alchemy',opts)
          assert(finish('alchemy',opts).planID~=planID)
        ''')

    def test_active_execution_is_a_frozen_copy_of_search_result(self):
        self.lua.execute('''
          local opts={start=1,target=2};local candidate=finish('alchemy',opts)
          local xp=ns.ProfExecution
          local run=assert(xp.Bind('alchemy',candidate))
          local frozen=assert(xp.GetPlan('alchemy'))
          assert(frozen~=candidate)
          local count=frozen.executionSteps[1][4]
          candidate.executionSteps[1][4]=999;candidate.revision=candidate.revision+1
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==frozen)
          assert(frozen.executionSteps[1][4]==count)
          assert(xp.GetRun('alchemy')==run)
        ''')

    def test_explicit_recalculate_supplies_verified_seed_and_actual_skill(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          finish('alchemy',{start=1,target=2})
          local prepared=0;local published=0;local captured
          ns.ProfExecution.PrepareRecalculate=function(slug)
            assert(slug=='alchemy');prepared=prepared+1;return {[10]=2},'previous-plan'
          end
          ns.ProfExecution.PlanRecalculated=function()published=published+1 end
          local capture=ns.ProfEconomy.Capture
          ns.ProfEconomy.Capture=function(slug,opts)captured=opts;return capture(slug,opts)end
          liveSkill=7
          ra.Recalculate('alchemy',{start=1,target=8,fromCurrent=false})
          local r=finish('alchemy',{start=7,target=8})
          assert(prepared==1 and published>0)
          assert(captured.executionInventory[10]==2)
          assert(captured.executionSourcePlanID=='previous-plan' and captured.start==7)
          assert(r.start==7 and r.cacheSignature:find('execution:previous-plan',1,true))
        ''')

    def test_synthetic_solver_fixtures_never_start_or_replace_player_execution(self):
        self.lua.execute('''
          ns.ProfExecution.PrepareRecalculate=function()error('synthetic run touched player state')end
          ns.ProfExecution.PlanRecalculated=function()error('synthetic run touched player state')end
          local r=finish('alchemy',{snapshot=fixture(),start=1,target=2})
          assert(r.total==7)
          ns.ProfRouteAuto.Recalculate('alchemy',{snapshot=fixture(),start=1,target=2})
          assert(ns.ProfExecution.GetRun('alchemy')==nil)
        ''')


if __name__ == '__main__':
    unittest.main()
