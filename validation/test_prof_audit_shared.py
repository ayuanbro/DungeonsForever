"""Per-profession audit regressions for shared fixed-guide and UI guards."""
import unittest
import test_prof_ui_fusion as fixture


class FixedRouteAuditTests(unittest.TestCase):
    setUp=fixture.ProfessionUIFusionTests.setUp
    boot=fixture.ProfessionUIFusionTests.boot

    def test_diagnostic_renderer_emits_blocking_messages_to_the_caller(self):
        self.lua.execute('''
          local messages={}
          ns.ProfEconomy.DiagnosticText=function(d)return 'blocked:'..d.code end
          PD.PlanDiagnostics(function(text)messages[#messages+1]=text end,
            {steps={{1,2,101,1}},feasible=false,blockingDiagnostics={{code='clientUnavailable',spell=101}}})
          assert(#messages==1 and messages[1]=='blocked:clientUnavailable',
            'local diagnostic grouping shadowed the row callback')
        ''')

    def test_fixed_guide_uses_current_client_eligibility_and_clears_old_block(self):
        self.lua.execute('''
          local E,RA=ns.ProfEconomy,ns.ProfRouteAuto
          local rejected=true
          E.FindRecipe=function(slug,spell)return {profession=slug,spell=spell,clientUnavailable=rejected}end
          E.LearningEligibility=function(recipe)
            return not recipe.clientUnavailable,recipe.clientUnavailable and 'clientUnavailable' or nil
          end
          local steps={{1,2,101,1}}
          local kept,blocked=RA.FilterFixedSpecializations('alchemy',steps)
          assert(#kept==0 and blocked[1].reason=='clientUnavailable')
          RA.MarkFixedSpecializations('alchemy',steps);assert(steps[1].specBlocked)
          rejected=false
          RA.MarkFixedSpecializations('alchemy',steps);assert(not steps[1].specBlocked)
        ''')

    def test_missing_first_aid_recipe_is_unknown_instead_of_zero_cost_execution(self):
        self.lua.execute('''
          local E,RA=ns.ProfEconomy,ns.ProfRouteAuto
          E.FindRecipe=function()end
          local sum=RA.SummarizeSteps({{1,2,3275,1}},'first-aid',{target=2})
          assert(sum.feasible==false and sum.status=='recalculate_required')
          assert(sum.clientPending and sum.completeCost==false and sum.priced==false)
          assert(sum.blockingDiagnostics[1].code=='clientDataPending')
        ''')

    def test_gather_checkpoints_do_not_require_a_crafting_recipe(self):
        self.lua.execute('''
          local kept,blocked=ns.ProfRouteAuto.FilterFixedSpecializations('mining',
            {{1,65,0,0,checkpoint=true},{65,125,0,0,checkpoint=true}})
          assert(#kept==2 and #blocked==0)
        ''')

    def test_updated_learning_algorithm_does_not_silently_reuse_an_old_execution(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local ra,xp=ns.ProfRouteAuto,ns.ProfExecution
          local result=finish('alchemy',{start=1,target=3})
          local run=assert(xp.Bind('alchemy',result));local original=run.plan
          -- Change the generic evaluator's version, not a source-data table.
          ns.ProfEconomy.LearningPolicyFingerprint=function()return 'test-only-algorithm-version' end
          local shown=ra.Get('alchemy',{start=1,target=3})
          assert(shown.status=='recalculate_required' and shown.diagnostics[1].code=='learningPolicyChanged')
          assert(run.plan==original and run.status=='active','existing execution facts were overwritten')
          assert(not ra.HasWork('alchemy'),'input changes silently launched replacement work')
        ''')


if __name__=='__main__':unittest.main()
