"""Execution source blocks remain visible in the existing HUD."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'validation'))
import test_prof_execution_fusion as execution


class HUDLearningTests(unittest.TestCase):
    setUp = execution.ExecutionFusionTests.setUp
    load = execution.ExecutionFusionTests.load
    load_follow = execution.ExecutionFusionTests.load_follow

    def test_blocked_progress_uses_diagnostic_reason_without_losing_step(self):
        self.load_follow()
        self.lua.execute("""
          local calls=0
          ns.ProfEconomy.DiagnosticText=function(code)
            calls=calls+1;assert(code=='reputationRequired');return 'Standing required'
          end
          local progress={learningBlocked=true,reason='reputationRequired',remainingCrafts=4}
          assert(pf.LearningWarning('alchemy',progress)=='Standing required')
          assert(progress.remainingCrafts==4 and progress.learningBlocked and calls==1)
          assert(pf.LearningWarning('alchemy',{learningBlocked=false})==nil and calls==1)
        """)

    def test_first_aid_frozen_hud_requires_recalculation_without_erasing_history(self):
        self.load_follow()
        self.lua.execute("""
          skills['first-aid']={cur=1,max=75}
          local frozen=fixture();frozen.mode='fixed';frozen.slug='first-aid'
          frozen.learningPolicyFingerprint='old-source-data'
          frozen.executionSteps[1].profession='first-aid'
          ns.ProfLeveling['first-aid']={steps=frozen.executionSteps}
          local previous=xp.GetPlan
          xp.GetPlan=function(slug)if slug=='first-aid' then return frozen end;return previous(slug)end
          ns.ProfEconomy.LearningPolicyFingerprint=function()return 'new-source-data'end
          pf.InvalidateRoute()
          local list=pf.ShoppingList('first-aid')
          assert(#list==0,'Stale First Aid plans must not issue purchase instructions')
          assert(pf.pendingPlans['first-aid'].status=='recalculate_required')
          assert(frozen.learningPolicyFingerprint=='old-source-data')
        """)


if __name__ == '__main__':
    unittest.main()
