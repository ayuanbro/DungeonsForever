"""The released source package and the real consumer use the same rank scale."""
from pathlib import Path
import unittest
from data_pipeline.professions.tests import test_runtime_learning as fixtures

ROOT = Path(__file__).resolve().parents[3]


class GeneratedReputationTests(unittest.TestCase):
    setUp = fixtures.LearningSourceRuntimeTests.setUp

    def test_generated_revered_book_uses_one_based_client_reaction(self):
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT / 'Core/Data/Data_ProfLearningSources.lua').read_text(encoding='utf8'))
        self.lua.execute("""
          local E=ns.ProfEconomy
          local r=assert(E.FindRecipe('enchanting',23802))
          local snap=input('enchanting');snap.ownedTeachingItems[19447]=1
          snap.reputations[529]=6 -- Honored in the client API, not Revered.
          local allowed,reason=E.RouteRecipeEligibility(r,snap)
          assert(not allowed and reason=='reputationRequired')
          snap.reputations[529]=7 -- Revered, DB2 MinReputation=6 normalized +1.
          local ok,_,detail=E.RouteRecipeEligibility(r,snap)
          assert(ok and detail.routeId=='item:23802:19447')
          assert(detail.quote.source=='owned' and detail.quote.cost==0)
          snap.known[r.key]=true;snap.reputations[529]=4
          assert(E.RouteRecipeEligibility(r,snap),'historical requirements blocked a learned recipe')
        """)
