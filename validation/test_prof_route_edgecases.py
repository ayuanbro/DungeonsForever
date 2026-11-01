"""Boundary regressions for asynchronous native profession route lifecycles."""
import unittest

try:
    from validation import test_prof_route_plans as fixtures
except ModuleNotFoundError:
    import test_prof_route_plans as fixtures


class NativeRouteEdgeCasesTests(unittest.TestCase):
    setUp = fixtures.NativeRoutePlansTests.setUp

    def test_cancelled_incumbent_stays_stopped_with_cpu_accounting(self):
        self.lua.execute(r'''
          local now=0;debugprofilestop=function()now=now+.03;return now end
          local s=fixture();s.recipes[2]={profession='alchemy',spell=102,item=20,count=1,
            mats={{11,2}},learn=1,yellow=100,green=200,grey=300,cooldown=false}
          s.known['alchemy:102']=true
          local ra=ns.ProfRouteAuto
          local opts={snapshot=s,start=1,target=60,cpuLimitMs=8000}
          ra.Get('alchemy',opts)
          local job=assert(ns.ProfSolverRun.Active()).job
          local count=0
          while not job.result and not job.finished do
            ra.Pump('alchemy');count=count+1;assert(count<10000)
          end
          assert(job.result and not job.finished,'fixture requires an in-flight incumbent')
          assert(ra.Cancel('alchemy'))
          local result=ra.Get('alchemy',opts)
          assert(result.status=='stopped','CPU accounting revived a cancelled plan: '..tostring(result.status))
          assert(result.searchTermination=='user_stopped','CPU accounting erased the stop reason')
          assert(not ra.HasWork('alchemy'))
        ''')

    def test_ending_execution_cannot_leave_a_permanent_searching_candidate(self):
        self.lua.execute(r'''
          local ra=ns.ProfRouteAuto
          local opts={snapshot=fixture(),start=1,target=3}
          local pending=ra.Get('alchemy',opts);assert(pending.status=='searching')
          ra.EndExecution('alchemy')
          assert(not ra.HasWork('alchemy'))
          local shown=ra.Get('alchemy',opts)
          assert(shown.status~='searching','ended work still appears to be optimizing')
          assert(shown.inFlight~=true)
        ''')

    def test_precision_api_preserves_progress_and_completion_callbacks(self):
        self.lua.execute(r'''
          local progressed,completed=0,0
          local opts={snapshot=fixture(),start=1,target=3}
          ns.ProfSolverRun.Start('alchemy',opts,{
            onProgress=function(job,state)
              assert(type(job)=='table' and type(state)=='table');progressed=progressed+1
            end,
            onDone=function(job)
              assert(job.finished and job.result.targetReached);completed=completed+1
            end})
          finish('alchemy',opts)
          assert(progressed>0,'legacy progress callback was dropped')
          assert(completed==1,'legacy completion callback must fire exactly once')
        ''')

    def test_synthetic_verified_inventory_is_part_of_route_identity(self):
        self.lua.execute(r'''
          local ra=ns.ProfRouteAuto
          local s=fixture()
          local first=finish('alchemy',{snapshot=s,start=1,target=3})
          assert(first.total==14)
          local second=finish('alchemy',{snapshot=s,start=1,target=3,executionInventory={[11]=2}})
          assert(second.total==0,'synthetic route reused a cache made with different verified stock')
          assert(first~=second)
        ''')

    def test_malformed_saved_route_cache_is_preserved_without_lua_error(self):
        self.lua.execute(r'''
          DungeonsForeverDB.prof.routePlans={version=1,characters={
            ['Test-Realm']={routes=false,active={},nextID=7}}}
          local original=DungeonsForeverDB.prof.routePlans
          local ok,result=pcall(ns.ProfRouteAuto.Get,'alchemy',{start=1,target=3})
          assert(ok,'malformed route cache crashed the profession page: '..tostring(result))
          assert(DungeonsForeverDB.prof.routePlans==original)
          assert(original.characters['Test-Realm'].routes==false,'opaque saved data was overwritten')
          assert(result and result.status=='recalculate_required')
        ''')

    def test_fewest_crafts_mode_keeps_essence_conversion_dependencies(self):
        self.lua.execute(r'''
          local s={recipes={{profession='enchanting',spell=101,count=0,mats={{10938,1}},
            learn=1,yellow=100,green=200,grey=300,cooldown=false}},
            professions={enchanting={cur=1,max=300}},known={['enchanting:101']=true},
            prices={[10938]=8,[10939]=10},coverageComplete=true}
          local opts={snapshot=s,start=1,target=3,scheme='crafts'}
          local pending=ns.ProfRouteAuto.Get('enchanting',opts)
          assert(pending and pending.status=='searching','conversion dependency bypassed shared solver')
          local r=finish('enchanting',opts)
          assert(r.targetReached and r.scheme=='crafts' and r.crafts==2 and r.total==10,tostring(r.total))
          local converted=0
          for _,step in ipairs(r.executionSteps)do
            if step.kind=='essence_conversion' then converted=converted+1;assert(step.expectedGain==0)end
          end
          assert(converted==1,'non-cost strategy lost its manual essence conversion')
          assert(not r.inputModelOptimal and r.restrictedReason=='strategy_route')
        ''')

    def test_material_cost_strategy_keeps_required_tool_goal(self):
        self.load((fixtures.ROOT/'Core'/'ProfGates.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute(r'''
          ns.ProfTools={engineering={{item=900,spell=201,minSkill=1,bindOnPickup=true}}}
          local s={recipes={
            {profession='engineering',spell=201,item=900,count=1,mats={{12,2}},
              learn=1,yellow=1,green=1,grey=1,cooldown=false},
            {profession='engineering',spell=202,item=901,count=1,mats={{11,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false}},
            professions={engineering={cur=1,max=300}},known={['engineering:201']=true,['engineering:202']=true},
            prices={[12]=3,[11]=4},coverageComplete=true}
          local opts={snapshot=s,start=1,target=3,scheme='matcost',autoCraftTools=true}
          local pending=ns.ProfRouteAuto.Get('engineering',opts)
          assert(pending and pending.status=='searching','tool goal bypassed shared solver')
          local r=finish('engineering',opts)
          assert(r.targetReached and r.scheme=='matcost' and r.total==14,tostring(r.total))
          assert(r.completedToolGoals['engineering:900'] and r.inventory[900]==1)
          local tool,goal=0,0
          for _,action in ipairs(r.actions)do
            if action.type=='craft' and action.spell==201 then tool=tool+action.count end
            if action.type=='tool_goal' and action.item==900 then goal=goal+1 end
          end
          assert(tool==1 and goal==1,'strategy omitted or duplicated required tool work')
          assert(not r.inputModelOptimal and r.restrictedReason=='strategy_route')
        ''')


if __name__ == '__main__':
    unittest.main()
