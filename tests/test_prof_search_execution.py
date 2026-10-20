"""Live optimizer diagnostics must not be frozen with execution obligations."""
import unittest

import test_prof_runtime as fixture


CONTROLLED_SEARCH = r'''
local s=ns.ProfRouteSolver
function s.NewJob(slug,opts)
  return {slug=slug,opts=opts,target=opts.target,expanded=0,status='searching',
    co=coroutine.create(function()coroutine.yield()end)}
end
function s.Result(job,state,status)
  local rec={profession='alchemy',spell=101,item=10,count=1,outputMin=1,outputMax=1,
    learn=1,yellow=20,green=30,grey=40,mats={{11,1}}}
  local step={1,3,101,2,profession='alchemy',recipe=rec,segmentID='segment:a',
    expectedGain=2,goalSkill=3,expectedCrafts=2,requiredOutputs={},allocations={}}
  return {planVersion=2,executionVersion=1,scheme='cheapest',feasible=state~=nil,
    status=status,expanded=job.expanded,start=1,target=3,total=job.expanded>=21 and 6 or 7,
    steps=state and {step} or {},executionSteps=state and {step} or {},mats={},formulas={},
    initialTotal=7,savings=job.expanded>=21 and 1 or 0,searchComplete=job.finished or false}
end
function s.Run(job)
  if job.finished or job.status=='stopped' then return true end
  job.expanded=job.expanded+7
  if job.expanded>=21 then job.finished=true;job.status='complete' end
  job.best={};job.result=s.Result(job,job.best,job.status)
  return job.finished
end
opts={start=1,target=3}
ra=ns.ProfRouteAuto;xp=ns.ProfExecution
ra.Get('alchemy',opts);ra.Pump('alchemy')
run=xp.Bind('alchemy',ra.Get('alchemy',opts));frozen=run.plan
xp.RecordAttempt('alchemy',101,'recorded-craft')
'''


class SearchExecutionTests(unittest.TestCase):
    def setUp(self):
        fixture.RuntimeTests.setUp(self)
        fixture.RuntimeTests.live_capture_fixture(self)
        self.load(str(fixture.ROOT / 'Core/ProfExecution.lua'))
        self.lua.execute("ns.ProfEconomy.Professions=function()return {alchemy={cur=liveSkill,max=300}}end")
        self.lua.execute(CONTROLLED_SEARCH)

    def test_live_comparisons_and_completion_do_not_replace_execution_facts(self):
        self.lua.execute('''
          local first=ra.Get('alchemy',opts)
          assert(first==frozen and first.expanded==7 and first.searchState.expanded==7)
          ra.Pump('alchemy');local second=ra.Get('alchemy',opts)
          assert(second==frozen and second.searchState.expanded==14 and second.searchState.running)
          ra.Pump('alchemy');local done=ra.Get('alchemy',opts)
          assert(done==frozen and done.searchState.expanded==21 and done.searchState.status=='complete')
          assert(not done.searchState.running and done.searchState.bestTotal==6)
          assert(done.total==7 and done.expanded==7 and done.executionSteps[1][4]==2)
          assert(xp.GetRun('alchemy')==run and xp.Progress('alchemy',1).casts==1)
        ''')

    def test_stop_and_continue_update_the_same_frozen_plan(self):
        self.lua.execute('''
          ra.Cancel('alchemy');local stopped=ra.Get('alchemy',opts)
          assert(stopped==frozen and stopped.searchState.status=='stopped' and not stopped.searchState.running)
          ra.Pump('alchemy');ra.Continue('alchemy')
          assert(ra.Get('alchemy',opts).searchState.status=='searching')
          ra.Pump('alchemy');ra.Pump('alchemy')
          assert(ra.Get('alchemy',opts).searchState.status=='complete')
          assert(xp.Progress('alchemy',1).casts==1)
        ''')

    def test_selecting_an_old_scheme_cache_cannot_replace_live_search_diagnostics(self):
        self.lua.execute('''
          ra.Cancel('alchemy')
          local cache=DungeonsForeverDB.prof.routeCache['Test-Realm']
          local record=cache.routes[cache.active.alchemy];local old={}
          for k,v in pairs(record.result)do old[k]=v end
          local signature=record.signature:gsub('^cheapest','matcost')
          old.planID='another-calculation';old.scheme='matcost';old.status='complete';old.total=123
          old.cacheSignature=signature
          cache.routes['alchemy|'..signature]={slug='alchemy',signature=signature,result=old}
          ra.Pump('alchemy');ra.Continue('alchemy')
          local visible=ra.Get('alchemy',{start=1,target=3,scheme='matcost'})
          assert(visible==frozen and visible.searchState.status=='searching' and visible.searchState.running)
          assert(visible.searchState.bestTotal==7 and visible.total==7)
          ra.Pump('alchemy');ra.Pump('alchemy')
          visible=ra.Get('alchemy',{start=1,target=3,scheme='matcost'})
          assert(visible.searchState.status=='complete' and visible.searchState.bestTotal==6)
          assert(xp.Progress('alchemy',1).casts==1)
        ''')

    def test_reload_during_search_does_not_show_an_eternal_running_job(self):
        self.lua.execute("ra.Pump('alchemy');before=#queue;savedID=run.planID")
        self.load(str(fixture.ROOT / 'Core/ProfRouteAuto.lua'))
        self.lua.execute('''
          local restored=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(restored.planID==savedID and restored.searchState.status=='interrupted')
          assert(restored.searchState.expanded==14 and restored.searchState.bestTotal==7)
          assert(not restored.searchState.running and #queue==before,
            'opening the saved execution plan silently launched another search')
          assert(xp.Progress('alchemy',1).casts==1)
        ''')

    def test_reloaded_final_search_diagnostics_stay_separate_from_saved_purchases(self):
        self.lua.execute("ra.Pump('alchemy');ra.Pump('alchemy');before=#queue")
        self.load(str(fixture.ROOT / 'Core/ProfRouteAuto.lua'))
        self.lua.execute('''
          local restored=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(restored==frozen and restored.total==7)
          assert(restored.searchState.status=='complete' and restored.searchState.expanded==21)
          assert(restored.searchState.bestTotal==6 and not restored.searchState.running and #queue==before)
        ''')


if __name__ == '__main__':
    unittest.main()
