"""Run native consumers with the shipped Forever learning-source provider.

The shared native fixture normally covers the legacy/non-Forever path. This
helper adds the real provider and strict policy, without inventing learning
records or treating DB2 catalogue membership as proof of availability.
"""
import unittest

from test_prof_native_data import ROOT, native_runtime


def production_runtime(locale='zhCN'):
    lua = native_runtime(locale)
    lua.execute('ns.IsForever=true')
    lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                (ROOT / 'Core/Data/Data_ProfLearningSources.lua').read_text(encoding='utf-8-sig'))
    lua.execute('''
      assert(ns.ProfLearningSources and ns.ProfLearningSources.meta.product=='wowf')
      function GetBuildInfo()
        local value=ns.ProfLearningSources.meta.build
        local version,revision=value:match('^(%d+%.%d+%.%d+)%.(%d+)$')
        return version,tonumber(revision)
      end
      UnitClass=function()return 'Warrior','WARRIOR',1 end
      UnitRace=function()return 'Human','Human',1 end
    ''')
    return lua


class ProductionLearningTests(unittest.TestCase):
    def setUp(self):
        self.lua = production_runtime()
        self.lua.execute('''
          -- Match the report: Alchemy has not been learned. Other professions
          -- are positive observations and do not establish any Alchemy skill.
          ns.ProfModule.ProfLearned=function()return {
            blacksmithing={cur=57,max=300},herbalism={cur=50,max=300}}
          end
          -- Isolate learning coverage from inventory: every auction material
          -- has a complete, fresh, sufficiently large snapshot in this test.
          ns.AuctionBridge={GetAuctionSupply=function()return {
            quantity=100000,observedAt=1000,complete=true,ownerExcluded=true,
            source='client-auction-results',market=1}
          end}
          function productionAlchemyInput()
            return ns.ProfEconomy.Capture('alchemy',{start=1,target=300,
              noFormula=true,considerAuctionSupply=true,autoCraftTools=false,recoveryEnabled=false})
          end
        ''')

    def test_shipped_starter_has_affirmative_automatic_skill_evidence(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local snapshot=productionAlchemyInput()
          assert(snapshot.learningSourcesRequired and snapshot.professions.alchemy.unlearned)
          local recipe=E.FindRecipe('alchemy',7183)
          assert(recipe.learn==1 and recipe.item==5997)
          local info=E.GetLearningInfo('alchemy',7183)
          assert(info and #info.routes>0 and info.routes[1].acquisition.kind=='skillGrant')
          local reasons={};for _,code in ipairs(info.missingReasons)do reasons[code]=true end
          assert(not reasons.learningSourceMissing)
          local allowed,reason,detail=E.RouteRecipeEligibility(recipe,snapshot,{skill={alchemy=1}})
          assert(allowed and detail.quote.automatic and detail.quote.cost==0)
          assert(snapshot.auctionSupply[765].quantity==100000)
        ''')

    def test_exclusions_and_complete_stock_keep_the_verified_starter_usable(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          E.SetPolicy('alchemy','alchemy',2334,'ban',false)
          E.SetPolicy('alchemy','alchemy',2365,'ban',false)
          local result=ns.ProfRouteSolver.Compute('alchemy',{start=1,target=2,
            noFormula=true,considerAuctionSupply=true,autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
          assert(result.targetReached and #result.steps>0 and #result.formulas==0)
          local gap
          for _,row in ipairs(result.learningGaps or {})do
            if row.spell==7183 then gap=row end
          end
          assert(not gap,'verified automatic starter retained a learning-source gap')
          assert(result.auctionSupplyUnknown==0,
            'a missing learning path was misreported as missing auction inventory')
        ''')

    def test_positive_known_observation_allows_the_short_native_starter_route(self):
        self.lua.execute('''
          ns.ProfModule.ProfLearned=function()return {alchemy={cur=1,max=75}}end
          observedKnown[7183]=true
          local E=ns.ProfEconomy
          local snapshot=productionAlchemyInput()
          local recipe=E.FindRecipe('alchemy',7183)
          local allowed,_,detail=E.RouteRecipeEligibility(recipe,snapshot,{skill={alchemy=1}})
          assert(allowed and detail.status=='learned')
          local result=ns.ProfRouteSolver.Compute('alchemy',{start=1,target=2,
            noFormula=true,considerAuctionSupply=true,learnedOnly=true,autoCraftTools=false,
            recoveryEnabled=false,cpuLimitMs=1000})
          assert(result.targetReached and #result.steps==1)
          assert(result.steps[1][3]==1245246 and result.completeCost and result.total==2,
            'retired learnedOnly excluded the cheaper automatic recipe')
        ''')

    def test_stocked_teaching_item_is_eligible_until_client_roster_proves_unavailable(self):
        self.lua.execute('''
          local E=ns.ProfEconomy
          local snapshot=productionAlchemyInput()
          local recipe=E.FindRecipe('alchemy',2365)
          assert(recipe.item==2460 and recipe.learn==100)
          local allowed,reason=E.RouteRecipeEligibility(recipe,snapshot,{skill={alchemy=300}})
          assert(allowed,reason)
          local quote=E.FormulaFor(recipe,snapshot)
          assert(quote.source=='ah' and quote.cost==1)
          E.EnsureClientRuntime()
          E.ClientStore().recipeRosters={alchemy={complete=true,ids={[7183]=true,[2334]=true}}}
          recipe=E.FindRecipe('alchemy',2365)
          allowed,reason=E.RouteRecipeEligibility(recipe,snapshot,{skill={alchemy=300}})
          assert(recipe.clientUnavailable and not allowed and reason=='clientUnavailable')
        ''')


if __name__ == '__main__':
    unittest.main()
