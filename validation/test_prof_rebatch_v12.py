"""RecipeRebatch v1.2: expensive replay probes run only at terminal publication.

Uses the existing native Lua 5.1 solver fixture; no UI or game client required.
"""
import unittest
from test_prof_solver_fusion import ProfessionSolverFusionTests


class RecipeRebatchTerminalTests(unittest.TestCase):
    setUp = ProfessionSolverFusionTests.setUp

    def test_final_rebatch_does_not_run_during_quick_seed_or_search(self):
        self.lua.execute(r'''
          local S = ns.ProfRouteSolver
          local original = S.RebatchChronological
          assert(type(original)=='function', 'RecipeRebatch v1.2 is not installed')
          local count = 0
          S.RebatchChronological = function(...)
              count = count + 1
              return original(...)
          end

          local s = snapshot({
              recipe('alchemy',101,10,1,{{11,1}},1,300)
          }, {[11]=7})
          local job = S.NewJob('alchemy',{
              snapshot=s,start=1,target=3,
              recoveryEnabled=false,cpuLimitMs=8000
          })
          local finished = false
          for i=1,12000 do
              local done = S.Run(job,0.5)
              if job.status == 'searching' then
                  assert(count == 0,
                      'Expensive rebatch was called in search/preview hot path')
              end
              if done then finished=true;break end
          end
          assert(finished and job.finished, 'Solver did not terminate')
          assert(job.result and job.result.targetReached,
              'Final route no longer reaches the requested target')
          assert(count == 1,
              'Final rebatch must run once; actual calls: '..count)
          local last = S.Result(job,job.best,job.status)
          assert(last.targetReached and count == 1,
              'Repeated result requests reran the rebatch')
        ''')


if __name__ == '__main__':
    unittest.main()
