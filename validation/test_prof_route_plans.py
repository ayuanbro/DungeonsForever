"""Native dev route lifecycle integration, running the actual Lua 5.1 sources."""
from pathlib import Path
import unittest
from test_prof_solver_fusion import LuaRuntime, ROOT


MOCKS = r'''
ns={LoadForeverPages=true,L=setmetatable({},{__index=function(_,k)return k end})}
DungeonsForeverDB={prof={}};queue={};callbacks={};timers={};frames={};clock=1000
time=function()return clock end
UnitName=function()return 'Test'end;GetRealmName=function()return 'Realm'end
UnitLevel=function()return 60 end;UnitFactionGroup=function()return 'Alliance'end
function CreateFrame()
 local f={events={}}
 function f:RegisterEvent(event)self.events[event]=true end
 function f:UnregisterEvent(event)self.events[event]=nil end
 function f:SetScript(key,fn)self[key]=fn end
 frames[#frames+1]=f;return f
end
ns.Init=function(fn)callbacks[#callbacks+1]=fn end
ns.IdleJobs={Add=function(fn)queue[#queue+1]=fn end}
C_Timer={After=function(_,fn)timers[#timers+1]=fn end}
bag={};C_Item={GetItemCount=function(id)return bag[id] or 0 end}
skills={alchemy={cur=1,max=300},enchanting={cur=1,max=300}}
-- Existing quantity-ledger fixtures explicitly exercise the enabled policy.
function fixture()
 return {considerAuctionSupply=true,recipes={{profession='alchemy',spell=101,item=10,count=1,mats={{11,1}},learn=1,yellow=100,green=200,grey=300,cooldown=false}},
  professions={alchemy={cur=1,max=300}},known={['alchemy:101']=true},prices={[11]=7},coverageComplete=true}
end
function finish(slug,opts)
 local r=ns.ProfRouteAuto.Get(slug,opts)
 for i=1,1000 do
  ns.ProfRouteAuto.Pump(slug);r=ns.ProfRouteAuto.Get(slug,opts)
  if not ns.ProfRouteAuto.HasWork(slug) then return r end
 end
 error('route did not terminate')
end
'''


class NativeRoutePlansTests(unittest.TestCase):
    def test_real_solver_reports_seed_skill_then_search_phase(self):
        self.lua.execute('''
          local solver=ns.ProfRouteSolver;local runner=ns.ProfSolverRun
          local j=solver.NewJob('alchemy',{snapshot=fixture(),start=1,target=35})
          local seed,search=false,false
          for i=1,20000 do
            solver.Run(j,0.01)
            local phase=runner.Stamp(j)
            if phase=='seed' and (j.seedSkill or 1)>1 then seed=true end
            if phase=='search' then search=true end
            if j.finished then break end
          end
          assert(j.finished and j.cpuLimitMs==8000)
          assert(seed and search,'solver did not report both live phases')
        ''')

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load=self.lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for name in ("ProfPolicies","ProfRouteAuto","ProfTrack","ProfEssences","ProfSolverCapture","ProfRecovery","ProfRouteSolver","ProfExecution","ProfSolverRun","ProfRoutePlans"):
            self.load((ROOT/"Core"/(name+".lua")).read_text(encoding="utf-8-sig"))
        self.lua.execute('''
          ns.ProfEconomy.Professions=function()return skills end
          ns.ProfEconomy.RecipeSpecializationAllowed=function()return true end
          for _,fn in ipairs(callbacks)do fn()end;callbacks={}
        ''')

    def test_get_schedules_one_job_and_uses_recursive_solver(self):
        self.lua.execute('''
          opts={snapshot=fixture(),start=1,target=3}
          local r=ns.ProfRouteAuto.Get('alchemy',opts)
          assert(r.status=='searching' and #queue==1)
          assert(ns.ProfRouteAuto.Get('alchemy',opts)==r and #queue==1)
          r=finish('alchemy',opts)
          assert(r.status=='complete' and r.total==14 and r.targetReached)
          assert(r.planVersion==2 and #r.executionSteps>0)
        ''')

    def test_invalidating_market_marks_stale_without_restarting_search(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto
          opts={snapshot=fixture(),start=1,target=3}
          local r=finish('alchemy',opts);local queued=#queue
          ra.Invalidate('prices')
          assert(ra.Get('alchemy',opts)==r and r.stale and #queue==queued)
          local pending=ra.Recalculate('alchemy',opts)
          assert(pending.status=='searching' and pending~=r)
          assert(finish('alchemy',opts).total==14)
        ''')

    def test_cancel_resume_cannot_run_obsolete_scheduler_callback(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;opts={snapshot=fixture(),start=1,target=3}
          ra.Get('alchemy',opts);local old=queue[1]
          assert(ra.Cancel('alchemy') and ra.Get('alchemy',opts).status=='stopped')
          ra.Continue('alchemy');assert(old()==true,'cancelled callback was revived')
          assert(finish('alchemy',opts).total==14)
          ra.Cancel('alchemy');ra.Continue('alchemy')
          assert(ra.Get('alchemy',opts).status=='complete')
        ''')

    def test_old_generation_cannot_publish_after_recalculate(self):
        self.lua.execute('''
          local ra=ns.ProfRouteAuto;opts={snapshot=fixture(),start=1,target=3}
          ra.Get('alchemy',opts);local old=queue[1]
          local pending=ra.Recalculate('alchemy',opts)
          assert(old()==true and ra.Get('alchemy',opts)==pending)
          assert(finish('alchemy',opts).total==14)
        ''')

    def test_live_cache_survives_reload_and_skill_changes_until_recalculated(self):
        self.lua.execute('''
          captures=0;price=7
          ns.ProfEconomy.Capture=function()
            captures=captures+1;local s=fixture();s.prices[11]=price
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3});assert(original.total==14 and captures==1)
          price=99;skills.alchemy.cur=2
        ''')
        self.load((ROOT/"Core"/"ProfRoutePlans.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute('''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=2,target=3})
          assert(r.cached and r.total==14 and r.start==1 and captures==1)
          ns.ProfRouteAuto.Recalculate('alchemy',{start=2,target=3})
          r=finish('alchemy',{start=2,target=3})
          assert(r.total==99 and captures==2 and r.planID~=original.planID)
        ''')

    def test_execution_plan_does_not_follow_candidate_replacement(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local ra=ns.ProfRouteAuto;local r=finish('alchemy',{start=1,target=3})
          local run=assert(ns.ProfExecution.Bind('alchemy',r));local frozen=run.plan
          assert(ra.Get('alchemy',{start=1,target=3})==frozen)
          ra.Invalidate('prices')
          assert(ra.Get('alchemy',{start=2,target=3})==frozen and frozen.stale)
          assert(run.plan==frozen and run.plan.planID==r.planID)
        ''')


class NativeArchitectureTests(unittest.TestCase):
    def test_all_sources_compile_under_lua51_and_main_toc_paths_exist(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        compile_source=lua.eval("function(source,name)local fn,error=loadstring(source,name);return fn~=nil,error end")
        for path in (ROOT/"Core").rglob("*.lua"):
            ok,error=compile_source(path.read_text(encoding="utf-8-sig"),str(path))
            self.assertTrue(ok,error)
        toc=(ROOT/"DungeonsForever.toc").read_text(encoding="utf-8-sig")
        self.assertIn('## SavedVariables: DungeonsForeverDB',toc)
        self.assertIn('## LoadOnDemand: 0',toc)
        for line in toc.splitlines():
            if line.startswith(('Core\\','Locales\\')):
                relative=line.split(' [',1)[0].replace('\\','/')
                self.assertTrue((ROOT/relative).is_file(),relative)


if __name__=="__main__":unittest.main()
