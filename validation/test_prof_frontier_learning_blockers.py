"""Learning coverage gaps must not replace the route's actual stopping cause."""
import unittest
import test_prof_solver_fusion as solver
import test_prof_route_plans as plans


class FrontierLearningBlockersTests(unittest.TestCase):
    def setUp(self):
        solver.ProfessionSolverFusionTests.setUp(self)
        self.lua.execute('''
          local original=snapshot
          snapshot=function(...)
            local result=original(...)
            result.considerAuctionSupply=true
            return result
          end
        ''')

    def missing(self, spell):
        self.lua.globals().missingSpell=spell
        self.lua.execute('''
          local E=ns.ProfEconomy
          local previous=E.RouteRecipeEligibility or E.RecipeSpecializationAllowed
          E.RouteRecipeEligibility=function(r,s,t)
            if r.spell==missingSpell then
              return false,'learningDataMissing',{status='missing',coverage='missing',missingReasons={'source_missing'}}
            end
            return previous(r,s,t)
          end
        ''')

    def test_bypassed_grey_recipe_does_not_hide_the_later_auction_shortage(self):
        self.missing(103)
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,2)
          local b=recipe('alchemy',102,20,1,{{12,2}},2,300)
          local unused=recipe('alchemy',103,30,1,{{13,1}},1,2)
          local s=snapshot({a,b,unused},{[11]=1,[12]=1,[13]=1})
          s.known['alchemy:103']=nil
          s.auctionSupply={[11]={quantity=1},[12]={quantity=1},[13]={quantity=100}}
          local r=solve('alchemy',s,3,{autoCraftTools=false,cpuLimitMs=1000})
          assert(r.partial and r.plannedTo==2 and not r.targetReached)
          assert(#r.learningGaps==1 and not r.learningCoverageComplete)
          assert(r.learningComplete and not r.learningBlocked and #r.blockingLearningGaps==0)
          local shortage=false
          for _,d in ipairs(r.blockingDiagnostics)do
            assert(d.code~='learningDataMissing','unrelated coverage gap became a blocker')
            if d.code=='auctionSupplyLimited'then shortage=true end
          end
          assert(shortage and r.costComplete and r.completeCost)
        ''')

    def test_explicit_exclusion_does_not_collect_missing_learning_data(self):
        self.missing(103)
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,2}},1,300)
          local excluded=recipe('alchemy',103,30,1,{{13,1}},1,300)
          local s=snapshot({a,excluded},{[11]=1,[13]=1})
          s.known['alchemy:103']=nil
          s.auctionSupply={[11]={quantity=1},[13]={quantity=100}}
          local r=solve('alchemy',s,2,{autoCraftTools=false,cpuLimitMs=1000,
            exclusions={['alchemy:103']='ban'}})
          assert(not r.targetReached and not r.learningBlocked and #r.learningGaps==0)
          local shortage,excluded=false,false
          for _,d in ipairs(r.blockingDiagnostics)do
            if d.code=='auctionSupplyLimited'then shortage=true end
            if d.code=='excluded'then excluded=true end
          end
          assert(shortage and excluded)
        ''')

    def test_missing_current_starting_recipe_remains_a_learning_block(self):
        self.missing(101)
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,10,1,{{11,1}},1,300)},{[11]=1})
          s.known={};s.auctionSupply={[11]={quantity=100}}
          local r=solve('alchemy',s,2,{autoCraftTools=false,cpuLimitMs=1000})
          assert(not r.targetReached and not r.feasible and r.learningBlocked)
          assert(not r.learningComplete and #r.blockingLearningGaps==1)
          assert(r.blockingLearningGaps[1].spell==101 and r.blockingLearningGaps[1].code=='learningDataMissing')
          local found=false
          for _,d in ipairs(r.blockingDiagnostics)do if d.code=='learningDataMissing'then found=true end end
          assert(found)
        ''')

    def test_missing_grey_material_producer_is_still_a_real_frontier_block(self):
        self.missing(103)
        self.lua.execute('''
          local consumer=recipe('alchemy',101,20,1,{{10,1}},2,300)
          local producer=recipe('alchemy',103,10,1,{{11,1}},1,2)
          local s=snapshot({consumer,producer},{[11]=1})
          s.professions.alchemy.cur=2;s.known['alchemy:103']=nil
          local r=solve('alchemy',s,3,{start=2,autoCraftTools=false,cpuLimitMs=1000})
          assert(not r.targetReached and r.learningBlocked)
          local producerMissing=false
          for _,d in ipairs(r.blockingLearningGaps)do if d.spell==103 then producerMissing=true end end
          assert(producerMissing,'a needed producer was discarded merely because its skill gain is grey')
        ''')

    def test_complete_verified_route_keeps_unused_coverage_gaps_separate(self):
        self.missing(103)
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,300)
          local unused=recipe('alchemy',103,30,1,{{13,1}},1,300)
          local s=snapshot({a,unused},{[11]=1,[13]=1});s.known['alchemy:103']=nil
          local r=solve('alchemy',s,3,{autoCraftTools=false,cpuLimitMs=1000})
          assert(r.feasible and r.targetReached and r.total==2)
          assert(#r.learningGaps==1 and #r.blockingLearningGaps==0 and not r.learningBlocked)
          assert(r.learningComplete and r.costComplete and r.completeCost)
          assert(countCrafts(r,103)==0,'missing learning facts were made executable')
        ''')

    def test_unknown_current_recipe_is_rejected_before_its_material_stock_is_evaluated(self):
        self.missing(101)
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,10,1,{{11,2}},1,300)},{[11]=1})
          s.known={};s.auctionSupply={[11]={quantity=1}}
          local r=solve('alchemy',s,2,{autoCraftTools=false,cpuLimitMs=1000})
          assert(r.learningBlocked and #r.blockingLearningGaps==1 and #r.actions==0)
          for _,d in ipairs(r.blockingDiagnostics)do
            assert(d.code~='auctionSupplyLimited','a rejected recipe was treated as a purchasable route')
          end
        ''')

    def test_future_leveling_recipe_does_not_block_the_current_stock_failure(self):
        self.missing(103)
        self.lua.execute('''
          local current=recipe('alchemy',101,20,1,{{11,2}},1,300)
          local future=recipe('alchemy',103,30,1,{{12,1}},50,300)
          local s=snapshot({current,future},{[11]=1,[12]=1})
          s.known['alchemy:103']=nil;s.auctionSupply={[11]={quantity=1},[12]={quantity=100}}
          local r=solve('alchemy',s,2,{autoCraftTools=false,cpuLimitMs=1000})
          assert(not r.targetReached and not r.learningBlocked and #r.learningGaps==0)
          local shortage=false
          for _,d in ipairs(r.blockingDiagnostics)do if d.code=='auctionSupplyLimited'then shortage=true end end
          assert(shortage)
        ''')

    def test_future_material_producer_does_not_pretend_its_learning_gap_blocks_current_skill(self):
        self.missing(103)
        self.lua.execute('''
          local current=recipe('alchemy',101,20,1,{{10,1}},1,300)
          local future=recipe('alchemy',103,10,1,{{11,1}},50,300)
          local s=snapshot({current,future},{[11]=1});s.known['alchemy:103']=nil
          local r=solve('alchemy',s,2,{autoCraftTools=false,cpuLimitMs=1000})
          assert(not r.targetReached and not r.learningBlocked and #r.learningGaps==0,
            'an unreachable future material producer polluted the current learning diagnosis')
          local skill=false
          for _,d in ipairs(r.blockingDiagnostics)do if d.code=='skillRequired' and d.spell==103 then skill=true end end
          assert(skill)
        ''')


class FailureDiagnosticCacheTests(unittest.TestCase):
    setUp=plans.NativeRoutePlansTests.setUp

    def test_partial_skeleton_restores_prefix_without_reusing_search_diagnostics(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.auctionSupply={[11]={quantity=1}}
            return ns.ProfEconomy.Index(s)
          end
          original=finish('alchemy',{start=1,target=3})
          assert(original.partial and original.plannedTo==2)
          assert(original.failureDiagnosticVersion==ns.ProfRouteSolver.FailureDiagnosticVersion)
          for _,record in pairs(DungeonsForeverDB.prof.routePlans.characters['Test-Realm'].routes)do
            assert(record.result==nil and record.skeleton.failureDiagnosticVersion==nil)
          end
        ''')
        self.load((solver.ROOT/'Core'/'ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.cached and r.partial and not r.targetReached and not r.optimal)
          assert(not r.diagnosticPolicyChanged and r.failureDiagnosticVersion==ns.ProfRouteSolver.FailureDiagnosticVersion)
          assert(r.planID==original.planID and r.total==original.total and #r.steps==#original.steps)
          assert(not ns.ProfRouteAuto.HasWork('alchemy'))
        ''')

    def test_completed_skeleton_revalidates_current_route_rules(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          original=finish('alchemy',{start=1,target=3})
          assert(original.targetReached)
          for _,record in pairs(DungeonsForeverDB.prof.routePlans.characters['Test-Realm'].routes)do
            assert(record.result==nil and record.skeleton.failureDiagnosticVersion==nil)
          end
        ''')
        self.load((solver.ROOT/'Core'/'ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local r=finish('alchemy',{start=1,target=3})
          assert(r.cached and r.targetReached and not r.stale and not r.diagnosticPolicyChanged)
          assert(r.planID==original.planID and r.total==original.total)
        ''')

    def test_old_partial_execution_keeps_frozen_facts_and_receipts(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()
            local s=fixture();s.auctionSupply={[11]={quantity=1}}
            return ns.ProfEconomy.Index(s)
          end
          local result=finish('alchemy',{start=1,target=3})
          local run=assert(ns.ProfExecution.Bind('alchemy',result))
          local frozen=run.plan;frozen.failureDiagnosticVersion=nil
          local steps,actions,total=frozen.executionSteps,frozen.actions,frozen.total
          local receipts=run.receipts
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(r==frozen and r.stale and r.diagnosticPolicyChanged and r.staleReason=='diagnostic-policy')
          assert(r.executionSteps==steps and r.actions==actions and r.total==total and run.receipts==receipts)
          assert(run.status=='active' and not ns.ProfRouteAuto.HasWork('alchemy'))
        ''')


if __name__=='__main__':unittest.main()
