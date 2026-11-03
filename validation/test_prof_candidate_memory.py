"""Candidate ownership, undo and coroutine lifetime in the native Lua runtime."""
import unittest
import test_prof_route_plans as fixtures


class CandidateMemoryTests(unittest.TestCase):
    def setUp(self):
        fixtures.NativeRoutePlansTests.setUp(self)
        self.lua.execute('''
          ra=ns.ProfRouteAuto;xp=ns.ProfExecution;opts={start=1,target=4}
          ns.ProfEconomy.Capture=function(slug,options)
            local s=fixture();s.executionInventory=options.executionInventory
            s.recipes[1].profession=slug;s.professions={[slug]={cur=1,max=300}}
            s.known={[slug..':101']=true};return ns.ProfEconomy.Index(s)
          end
          function up(fn,name)
            for i=1,100 do
              local key,value=debug.getupvalue(fn,i)
              if not key then break end
              if key==name then return value end
            end
            error('upvalue not found: '..name)
          end
          function count(t)local n=0;for _ in pairs(t)do n=n+1 end;return n end
          function drain()
            for _=1,10000 do
              local pending=queue;queue={}
              for _,fn in ipairs(pending)do
                if fn()~=true then queue[#queue+1]=fn end
              end
              if #queue==0 then return end
            end
            error('job queue did not finish')
          end
          function gc()collectgarbage('collect');collectgarbage('collect')end
          function current(target)
            ra.Recalculate('alchemy',{start=1,target=target or 4});drain()
            return assert(ra.Peek('alchemy'))
          end
          weak=setmetatable({},{__mode='v'})
        ''')

    def test_reserve_modes_keep_one_result_and_one_independent_undo(self):
        self.lua.execute('''
          current()
          for i=1,21 do
            local old=ra.Peek('alchemy');weak[i]=old
            local mode=({'off','standard','ample'})[(i-1)%3+1]
            ra.ChangeReserveMode('alchemy',mode);drain()
            assert(ra.Peek('alchemy').executionOptions.reserveMode==mode)
            assert(count(up(ra.Get,'results'))==1 and ra.HasPlanPrev('alchemy'))
          end
          assert(count(up(ra.SavePlanPrev,'planPrevMem'))==1)
        ''')
        self.lua.execute('''
          gc()
          for i=1,21 do assert(weak[i]==nil,'replaced candidate is still retained: '..i)end
          local previous=up(ra.SavePlanPrev,'planPrevMem')['Test-Realm|alchemy'].result
          local id,total=previous.planID,previous.total
          local restored=assert(ra.RevertPlan('alchemy',opts))
          assert(restored.planID==id and restored.total==total)
          assert(ra.Get('alchemy',opts)==restored and count(up(ra.Get,'results'))==1)
        ''')

    def test_bind_releases_undo_without_querying_the_button(self):
        self.lua.execute('''
          current();current()
          weak.undo=up(ra.SavePlanPrev,'planPrevMem')['Test-Realm|alchemy'].result
          run=assert(xp.Bind('alchemy',ra.Peek('alchemy')))
          assert(count(up(ra.SavePlanPrev,'planPrevMem'))==0)
        ''')
        self.lua.execute('''
          gc();assert(weak.undo==nil,'disabled undo still retains a result')
          local frozen=run.plan;local id,total=frozen.planID,frozen.total
          assert(xp.GetPlan('alchemy')==frozen and run.attemptsDone==0)
          ra.ChangeReserveMode('alchemy','off');drain()
          assert(xp.GetPlan('alchemy')==frozen and frozen.planID==id and frozen.total==total)
          assert(run.attemptsDone==0 and not ra.HasPlanPrev('alchemy'))
        ''')

    def test_other_profession_and_independent_snapshots_survive_replacement(self):
        self.lua.execute('''
          current()
          local other=finish('enchanting',opts);drain()
          local a={start=1,target=3,snapshot=fixture()}
          local b={start=1,target=4,snapshot=fixture()}
          local first=finish('alchemy',a);drain()
          local second=finish('alchemy',b);drain()
          ra.ChangeReserveMode('alchemy','off');drain()
          assert(ra.Get('enchanting',opts)==other)
          assert(ra.Get('alchemy',a)==first and ra.Get('alchemy',b)==second)
          assert(count(up(ra.Get,'results'))==4)
          current(5)
          assert(ra.Get('enchanting',opts)==other)
          assert(ra.Get('alchemy',a)==first and ra.Get('alchemy',b)==second)
          assert(count(up(ra.Get,'results'))==4)
          assert(ra.RevertPlan('alchemy',opts))
          assert(ra.Get('enchanting',opts)==other)
          assert(ra.Get('alchemy',a)==first and ra.Get('alchemy',b)==second)
          assert(count(up(ra.Get,'results'))==4)
        ''')

    def test_replacing_a_skeleton_uses_its_request_key_for_cleanup(self):
        self.lua.execute('''
          current()
          local saved=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local skeleton=ns.ProfEconomy.Copy(saved.routes[saved.active.alchemy].skeleton)
          ra.RebuildFromSkel('alchemy',skeleton,{start=1,target=6});drain()
          local restored=ra.Peek('alchemy');weak.restored=restored
          local key=up(ra.Get,'active')['Test-Realm|alchemy']
          assert(key~='Test-Realm|alchemy|'..restored.cacheSignature)
          assert(restored.target==4 and restored.settingsChanged)
          ra.ChangeReserveMode('alchemy','off');drain()
          assert(count(up(ra.Get,'results'))==1)
        ''')
        self.lua.execute("gc();assert(weak.restored==nil,'skeleton result survived under a different request key')")

    def test_cancel_continue_keeps_the_same_computation(self):
        self.lua.execute('''
          ra.Recalculate('alchemy',{start=1,target=35})
          local job=next(up(ra.Pump,'jobs'))
          job=up(ra.Pump,'jobs')[job];local co=job.co
          assert(ra.Cancel('alchemy') and job.cancelled and job.co==co)
          drain()
          assert(not ra.HasWork('alchemy') and job.co==co and not job.invalid)
          ra.Continue('alchemy')
          assert(ra.HasWork('alchemy') and job.co==co and not job.cancelled)
          drain()
          local result=ra.Peek('alchemy')
          assert(result.targetReached and result.target==35 and result.total==238)
          assert(not ra.HasWork('alchemy') and count(up(ra.Pump,'jobs'))==0)
        ''')

    def test_replaced_paused_coroutine_is_released_after_queue_drain(self):
        self.lua.execute('''
          local original=current()
          local saved=DungeonsForeverDB.prof.routePlans.characters['Test-Realm']
          local skeleton=ns.ProfEconomy.Copy(saved.routes[saved.active.alchemy].skeleton)
          ra.Recalculate('alchemy',{start=1,target=35})
          local _,job=next(up(ra.Pump,'jobs'));weak.job=job;weak.co=job.co
          local obsolete=queue[#queue]
          ra.Cancel('alchemy')
          ra.RebuildFromSkel('alchemy',skeleton,opts)
          assert(obsolete()==true)
          drain()
          assert(ra.Peek('alchemy').total==original.total)
          assert(ra.Peek('alchemy').target==4 and not ra.HasWork('alchemy'))
        ''')
        self.lua.execute("gc();assert(not weak.job and not weak.co,'replaced computation was retained')")

    def test_facade_releases_the_replaced_job_and_result(self):
        self.lua.execute('''
          ns.ProfModule={cur='alchemy'}
          local handle=ns.ProfSolverRun.Start('alchemy',opts);drain()
          weak.job=handle.job;weak.result=handle.job.result
          assert(weak.result==ns.ProfSolverRun.Result())
          ra.ChangeReserveMode('alchemy','off');drain()
          assert(ns.ProfSolverRun.Result()==ra.Peek('alchemy'))
        ''')
        self.lua.execute("gc();assert(not weak.job and not weak.result,'facade retained the replaced computation')")

    def test_execution_reference_change_only_releases_its_profession_undo(self):
        self.lua.execute('''
          current();current()
          finish('enchanting',opts);drain()
          ra.Recalculate('enchanting',opts);drain()
          local backups=up(ra.SavePlanPrev,'planPrevMem')
          weak.alchemy=backups['Test-Realm|alchemy'].result
          weak.enchanting=backups['Test-Realm|enchanting'].result
          local run=assert(xp.Bind('alchemy',ra.Peek('alchemy')))
          assert(not backups['Test-Realm|alchemy'] and backups['Test-Realm|enchanting'])
          assert(xp.GetPlan('alchemy')==run.plan)
          ra.CacheReferencesChanged('Another-Realm')
          assert(backups['Test-Realm|enchanting'])
        ''')
        self.lua.execute('''
          gc();assert(not weak.alchemy and weak.enchanting)
          assert(ra.HasPlanPrev('enchanting') and ra.RevertPlan('enchanting',opts))
        ''')


if __name__=='__main__':unittest.main()
