"""First feasible specialization route and bounded-search blocker regressions."""
from pathlib import Path
import unittest

from test_prof_solver import FIXTURES, LuaRuntime
from test_prof_specialization_solver import SPECIALIZATION_FIXTURES

ROOT = Path(__file__).resolve().parents[1]


class Target225SolverTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES + SPECIALIZATION_FIXTURES)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        for name in ("ProfEconomy.lua", "ProfRouteSolver.lua"):
            load(str(ROOT / "Core" / name))

    def test_first_quest_route_precedes_enumeration_of_all_procurement_splits(self):
        self.lua.execute('''
          local s=engineering({
            recipe('engineering',101,10,1,{{11,1}},1,150),
            recipe('engineering',102,20,1,{{21,1}},1,150),
            recipe('engineering',103,30,1,{{31,1}},1,150)},
            {[10]=100,[11]=1,[20]=100,[21]=1,[30]=100,[31]=1},
            200,{{10,20},{20,20},{30,20}})
          s.offers={}
          for _,id in ipairs({10,11,20,21,30,31}) do
            s.offers[id]={{unlimited=true,price=50,quantity=3,npcID=id}}
          end
          local job=ns.ProfRouteSolver.NewJob('engineering',{snapshot=s,start=200,target=200})
          local full
          -- Each slice also yields after at most 1000 solver ticks. This makes
          -- the warm-start bound independent of machine speed or a fake clock.
          for _=1,20 do
            ns.ProfRouteSolver.Run(job,1000000)
            if job.result and job.result.targetReached then full=job.result;break end
          end
          assert(not job.error,tostring(job.error))
          assert(full,'a feasible quest must publish before comparing every split')
          assert(job.expanded==0,'the first seed itself should complete the quest')
          assert(questStep(full) and full.inventory[10]==1 and full.inventory[20]==1 and full.inventory[30]==1)
          assert(full.completeCost and not full.optimal)
          local paid=0;for _,m in ipairs(full.mats) do paid=paid+m.cost end
          assert(paid==full.total)
        ''')

    def test_seed_timeout_does_not_erase_furthest_real_blocker(self):
        self.lua.execute('''
          local now=0
          debugprofilestop=function() now=now+1;return now end
          local s=snapshot({recipe('alchemy',101,10,1,{{11,100}},1,3),
            recipe('alchemy',102,11,1,{{12,1}},1,1)}, {[11]=100,[12]=1})
          s.professions={alchemy={cur=1,max=300}}
          local result,job=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=225})
          assert(not job.error and result.partial and result.plannedTo==3)
          assert(job.blockedSkill==3)
          local gap=false
          for _,d in ipairs(result.blockingDiagnostics or {}) do if d.code=='levelGap' then gap=true end end
          assert(gap,'the completed prefix must retain its actual terminal blocker')
        ''')


if __name__ == "__main__":
    unittest.main()
