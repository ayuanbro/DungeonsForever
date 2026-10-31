"""Lua 5.1 integration: strict source gaps, selected fees, frozen execution.

These tests exercise real route/UI/execution entry points with controlled source
evidence. They do not assert live game learnability or rendered widget layout.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation"))
import test_prof_solver_fusion as solver
import test_prof_route_plans as plans
import test_prof_ui_fusion as ui
import test_prof_execution_fusion as execution


class StrictLearningSolverTests(unittest.TestCase):
    def setUp(self):
        solver.ProfessionSolverFusionTests.setUp(self)
        self.lua.execute("""
          ns.IsForever=true
          ns.ProfLearningSources={meta={schema=1,product='wowf',fingerprint='test-data'},Get=function()end}
          function trainer(r,cost)
            r.learningInfo={spell=r.spell,profession=r.profession,coverage='complete',missingReasons={},
              routes={{id='trainer:'..r.spell,kind='trainer',status='confirmed',conditionsKnown=true,
                conditions={},trainingCost=cost}}}
            return r
          end
          function missing(r)
            r.learningInfo={spell=r.spell,profession=r.profession,coverage='partial',
              missingReasons={'itemDetailsMissing','sourceMissing'},
              routes={{id='item:'..r.spell,kind='item',teachingItemID=5577,status='unknown',
                conditionsKnown=false,conditions={}}}}
            return r
          end
        """)
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                         (ROOT / "Core/ProfLearning.lua").read_text(encoding="utf-8"))

    def test_missing_future_path_keeps_only_verified_prefix_and_exact_gap(self):
        self.lua.execute("""
          local a=trainer(recipe('alchemy',101,10,1,{{11,1}},1,2),0)
          local b=missing(recipe('alchemy',102,12,1,{{11,1}},2,300))
          local snap=snapshot({a,b},{[11]=7});snap.known={['alchemy:101']=true}
          local result,job=solve('alchemy',snap,4,{autoCraftTools=false})
          assert(job.finished and result.partial and result.plannedTo==2)
          assert(not result.targetReached and result.completeCost==false)
          assert(#result.steps==1 and result.steps[1][3]==101)
          assert(#result.learningGaps==1 and result.learningGaps[1].spell==102)
          assert(result.learningGaps[1].missingReasons[1]=='itemDetailsMissing')
          for _,a in ipairs(result.actions)do assert(a.type~='craft' or a.spell~=102)end
        """)

    def test_unobtainable_teaching_item_finishes_with_purchase_gap_instead_of_spinning(self):
        self.lua.execute("""
          local snap=snapshot({missing(recipe('alchemy',102,12,1,{{11,1}},1,300))},{[11]=7})
          snap.known={}
          local result,job=solve('alchemy',snap,3,{autoCraftTools=false})
          assert(job.finished and not result.feasible and not result.targetReached)
          assert(#result.steps==0 and result.learningGaps[1].spell==102)
          assert(result.learningGaps[1].code=='formulaUnavailable',tostring(result.learningGaps[1].code))
        """)

    def test_confirmed_trainer_alternative_has_one_real_fee_and_no_book_purchase(self):
        self.lua.execute("""
          local a=trainer(recipe('alchemy',101,10,1,{{11,1}},1,300),50)
          a.learningInfo.routes[#a.learningInfo.routes+1]={id='missing-book',kind='item',
            teachingItemID=5577,status='unknown',conditionsKnown=false,conditions={}}
          local snap=snapshot({a},{[11]=7,[5577]=1});snap.known={}
          local result=solve('alchemy',snap,3,{autoCraftTools=false})
          assert(result.targetReached and result.total==64,tostring(result.total))
          assert(#result.formulas==1 and result.formulas[1].source=='trainer')
          assert(result.formulas[1].id==nil and result.formulas[1].cost==50)
          assert(result.formulas[1].learningRouteId=='trainer:101')
          assert(result.formulaVendorTotal==50)
          for _,a in ipairs(result.actions)do assert(a.item~=5577)end
        """)

    def test_drop_pattern_with_auction_price_enters_exact_and_fixed_routes_with_one_purchase(self):
        self.lua.execute("""
          for _,fixed in ipairs({false,true})do
            local a=recipe('alchemy',101,10,1,{{11,1}},1,300)
            a.formula=900001;a.source={drops={{id=777}}}
            a.learningInfo={spell=101,profession='alchemy',coverage='partial',missingReasons={'acquisitionSourceMissing'},
              routes={{id='item:101:900001',kind='item',teachingItemID=900001,status='confirmed',
                conditionsKnown=true,conditions={},acquisition={status='unknown',coverage='partial',
                  conditionsKnown=false,conditions={},dropSourceCount=200,dropDetailsOffline=true,nonAuctionable=false}}}}
            local snap=snapshot({a},{[11]=7,[900001]=501});snap.known={};snap.noFormula=false
            snap.stamp=1000
            snap.auctionSupply={[11]={quantity=3,complete=true,ownerExcluded=true,source='fixture'},
              [900001]={quantity=2,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}}
            local opts={autoCraftTools=false}
            if fixed then opts.fixedSteps={{1,4,101,3}}end
            local result,job=solve('alchemy',snap,4,opts)
            assert(not job.error and result.targetReached,tostring(job.error)..' '..tostring(result.reason))
            assert(result.total==522,tostring(result.total))
            assert(#result.formulas==1 and result.formulas[1].id==900001)
            assert(result.formulas[1].source=='ah' and result.formulas[1].cost==501)
            assert(result.formulas[1].count==1,'teaching item was bought for every craft')
          end
        """)

    def test_unknown_training_fee_is_never_zero_cost(self):
        self.lua.execute("""
          local a=trainer(recipe('alchemy',101,10,1,{{11,1}},1,300),nil)
          local snap=snapshot({a},{[11]=7});snap.known={}
          local result,job=solve('alchemy',snap,3,{autoCraftTools=false})
          assert(job.finished and result.targetReached and result.feasible)
          assert(result.completeCost==false)
          assert(#result.formulas==1 and result.formulas[1].source=='trainer')
          assert(result.formulas[1].usable and result.formulas[1].cost==nil)
          assert(result.formulas[1].unpriced and not result.formulas[1].costComplete)
        """)

    def test_unrelated_unknown_recipe_does_not_block_a_complete_known_route(self):
        self.lua.execute("""
          local a=trainer(recipe('alchemy',101,10,1,{{11,1}},1,300),0)
          local b=missing(recipe('alchemy',102,12,1,{{11,1}},1,300))
          local snap=snapshot({a,b},{[11]=7});snap.known={['alchemy:101']=true}
          local result=solve('alchemy',snap,3,{autoCraftTools=false})
          assert(result.targetReached and result.learningComplete and result.total==14)
          for _,step in ipairs(result.steps)do assert(step[3]==101)end
        """)


class LearningUIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.boot = ui.ProfessionUIFusionTests.boot.__get__(self)
        self.boot("zhCN")

    def test_each_source_failure_has_a_distinct_localized_explanation_in_three_locales(self):
        for locale in ("zhCN", "zhTW", "enUS"):
            self.boot(locale)
            self.lua.execute("""
              local p={status='infeasible',feasible=false,targetReached=false,steps={},total=0,completeCost=false,
                learningComplete=false,learningGaps={{code='learningDataMissing',spell=2671,item=5577,
                  missingReasons={'itemDetailsMissing','sourceMissing','sourceBlocked','parseError','unsupportedRaceMask','sourceConflict'}}}}
              local text=PD.LearningGapText(p.learningGaps[1])
              assert(text:find('2671',1,true) and text:find('5577',1,true))
              assert(PD.LearningGapReason('sourceBlocked')~=PD.LearningGapReason('sourceMissing'))
              local shown={};PD.PlanDiagnostics(function(t)shown[#shown+1]=t end,p)
              assert(#shown>0 and table.concat(shown,' '):find('5577',1,true))
              assert(PD.PlanStatusParts(p)==ns.L['学习资料不足，当前无法到达目标。'])
              assert(PD.PlanCostText(p)==ns.L['路线尚未完整，费用待确认'])
              assert(PD.SnapshotBadgeState(p)=='learning_unknown')
            """)

    def test_trainer_learning_row_has_fee_and_does_not_present_an_unknown_book(self):
        self.lua.execute("""
          local rows={};PD.RowsFormulaShop(rows,{formulas={{source='trainer',spell=2671,cost=120,
            costComplete=true,count=1}}})
          local names={};for _,row in ipairs(rows)do names[#names+1]=row.text or '' end
          local text=table.concat(names,' ')
          assert(text:find('2671',1,true) and not text:find(ns.L['未知图纸'],1,true))
          assert(text:find(ns.L['学习费用（%d 项）']:gsub('%%d','1'),1,true))
        """)


class LearningFastRouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        plans.NativeRoutePlansTests.setUp(self)
        self.lua.execute("""
          ns.IsForever=true;ns.ProfRecovery=nil
          local records={}
          records[101]={spell=101,profession='alchemy',coverage='complete',missingReasons={},routes={
            {id='trainer:101',kind='trainer',status='confirmed',conditionsKnown=true,conditions={},trainingCost=50}}}
          records[102]={spell=102,profession='alchemy',coverage='partial',missingReasons={'itemDetailsMissing'},routes={
            {id='item:102',kind='item',teachingItemID=5577,status='unknown',conditionsKnown=false,conditions={}}}}
          ns.ProfLearningSources={meta={schema=1,product='wowf',fingerprint='fast-test'},Get=function(_,spell)return records[spell]end}
          ns.ProfRecipes={alchemy={rows={
            {101,10,1,'','','',1,100,200,2,false,{{11,1}}},
            {102,12,1,'','','',2,100,200,300,false,{{11,1}}}}}}
          ns.ProfLeveling={alchemy={sold={},rinfo={}}}
          Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)return 7 end}}}
          ns.ProfEconomy.Known=function()return false end
          ns.ProfModule={Setting=function()return true end,SettingRaw=function(key)return key~='autoAllowUnknownLearning' end}
        """)
        for name in ("ProfRouteAuto", "ProfLearning"):
            self.load((ROOT / "Core" / (name + ".lua")).read_text(encoding="utf-8"))

    def test_fast_route_stops_before_the_unverified_interval(self):
        self.lua.execute("""
          ns.ProfEconomy.Known=function(spell)return spell==101 end
          local result=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=4,onlyAH=true,scheme='cheapest'})
          assert(result.partial and result.plannedTo==2 and not result.targetReached)
          assert(#result.steps==1 and result.steps[1][3]==101)
          assert(result.learningGaps[1].spell==102 and result.learningGaps[1].item==5577)
          assert(result.completeCost==false and result.status=='incomplete')
        """)

    def test_fast_route_includes_confirmed_training_cost_once(self):
        self.lua.execute("""
          local result=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=2,onlyAH=true,scheme='cheapest'})
          assert(result.formulasTotal==50,tostring(result.formulasTotal))
          assert(#result.formulas==1 and result.formulas[1].source=='trainer')
          assert(result.total==57,tostring(result.total))
        """)

    def test_fast_route_prices_a_drop_pattern_from_auction_once_for_multiple_crafts(self):
        self.lua.execute("""
          ns.ProfRecipes.alchemy.rows={ns.ProfRecipes.alchemy.rows[1]}
          ns.ProfRecipes.alchemy.rows[1][10]=300
          ns.ProfLearningSources.meta.fingerprint='drop-auction-fast'
          ns.ProfLearningSources.Get=function(_,spell)
            if spell~=101 then return end
            return {spell=101,profession='alchemy',coverage='partial',missingReasons={'acquisitionSourceMissing'},
              routes={{id='item:101:900001',kind='item',teachingItemID=900001,status='confirmed',conditionsKnown=true,
                conditions={},acquisition={status='unknown',coverage='partial',conditionsKnown=false,
                  conditions={},dropDetailsOffline=true,dropSourceCount=200,nonAuctionable=false}}}}
          end
          Auctionator.API.v1.GetAuctionPriceByItemID=function(_,id)return id==900001 and 501 or 7 end
          ns.AuctionBridge={GetAuctionSupply=function(id)if id==900001 then return {
            quantity=2,observedAt=1000,complete=true,ownerExcluded=true,source='client-auction-results'}end end}
          local result=ns.ProfRouteAuto.Compute('alchemy',{start=1,target=4,onlyAH=true,
            noFormula=false,considerAuctionSupply=false,scheme='cheapest'})
          assert(#result.steps>0 and result.steps[1][1]==1 and result.steps[#result.steps][2]==4)
          assert(#result.gaps==0 and #result.learningGaps==0)
          assert(result.formulasTotal==501,tostring(result.formulasTotal))
          assert(result.total==522,tostring(result.total))
          assert(#result.formulas==1 and result.formulas[1].id==900001 and result.formulas[1].source=='ah')
          assert(result.formulas[1].count==1,'fast route bought the pattern repeatedly')
        """)


class FrozenLearningRouteViewTests(unittest.TestCase):
    def setUp(self):
        plans.NativeRoutePlansTests.setUp(self)

    def test_policy_update_keeps_frozen_route_visible_for_explicit_recalculation(self):
        self.lua.execute("""
          policy='one';ns.ProfEconomy.LearningPolicyFingerprint=function()return policy end
          local candidate=finish('alchemy',{snapshot=fixture(),start=1,target=3})
          local run=assert(ns.ProfExecution.Bind('alchemy',candidate))
          ns.ProfExecution.RecordAttempt('alchemy',101,'before-update')
          local frozen=run.plan;local first=frozen.executionSteps[1]
          policy='two'
          local shown=ns.ProfRouteAuto.Get('alchemy',{start=1,target=3})
          assert(shown==frozen and #shown.steps>0 and shown.executionSteps[1]==first)
          assert(shown.stale and shown.staleReason=='learning-data' and shown.learningBlocked)
          assert(shown.status=='recalculate_required')
          assert(run.progress[first.segmentID].casts==1)
        """)


class LearningExecutionIntegrationTests(unittest.TestCase):
    load = execution.ExecutionFusionTests.load

    def setUp(self):
        execution.ExecutionFusionTests.setUp(self)
        self.lua.execute("""
          ns.IsForever=true;ns.ProfLearningSources={};policy='data-a';observation=0;checks=0
          local E=ns.ProfEconomy
          E.LearningPolicyFingerprint=function()return policy end
          E.LearningObservationFingerprint=function()return observation end
          E.RouteRecipeEligibility=function(r)
            checks=checks+1
            if blockedSpell==r.spell then return false,'learningDataMissing',{status='unknown',missingReasons={'sourceMissing'}}end
            return true,nil,{status='learned'}
          end
          plan=fixture();plan.planID='strict';plan.learningPolicyFingerprint=policy
          run=xp.StartNew('alchemy',plan)
          assert(run)
        """)

    def test_data_update_blocks_resume_but_keeps_frozen_steps_and_receipts(self):
        self.lua.execute("""
          xp.RecordAttempt('alchemy',101,'kept')
          local frozen=run.plan;local segment=frozen.executionSteps[1]
          policy='data-b'
          local resumed,reason=xp.Bind('alchemy',plan)
          assert(not resumed and reason=='learningPolicyChanged')
          assert(run.plan==frozen and frozen.executionSteps[1]==segment)
          assert(run.progress[segment.segmentID].casts==1)
          local p=xp.Progress('alchemy');assert(p.learningBlocked and p.reason=='learningPolicyChanged')
        """)

    def test_repeated_current_step_reads_are_cached_until_character_inputs_change(self):
        self.lua.execute("""
          xp.Progress('alchemy');local before=checks
          for i=1,20 do xp.Progress('alchemy') end
          assert(checks==before)
          observation=observation+1;blockedSpell=101
          local p=xp.Progress('alchemy')
          assert(checks==before+1 and p.learningBlocked and p.reason=='learningDataMissing')
          assert(xp.CalculateSupplement('alchemy')==nil)
        """)

    def test_missing_provider_cannot_bypass_execution_revalidation(self):
        self.lua.execute("""
          local frozen=run.plan
          ns.ProfLearningSources=nil;policy='missing-provider'
          local resumed,reason=xp.Bind('alchemy',plan)
          assert(not resumed and reason=='learningPolicyChanged')
          assert(run.plan==frozen and #frozen.executionSteps>0)
        """)

    def test_first_aid_enforces_changed_learning_policy_before_execution(self):
        self.lua.execute("""
          policy='changed';local before=checks
          local ok,reason=xp.ValidateLearning(plan,'first-aid',plan.executionSteps[1])
          assert(not ok and reason=='learningPolicyChanged')
          assert(checks==before)
        """)

    def test_next_step_is_rechecked_without_erasing_completed_work(self):
        self.lua.execute("""
          local p=fixture();p.planID='two-steps';p.learningPolicyFingerprint=policy;p.target=4
          local b={3,4,102,1,profession='alchemy',recipe=recipes[102],segmentID='b',
            goalSkill=4,expectedGain=1,expectedCrafts=1,attemptLimit=1,item=11,
            requiredOutputs={[11]=2},materialMinCrafts=1,outputMin=2,outputMax=2,allocations={}}
          p.executionSteps[2]=b;p.steps=p.executionSteps
          run=assert(xp.StartNew('alchemy',p));blockedSpell=102
          xp.RecordAttempt('alchemy',101,'first-a');xp.RecordOutput({itemID=10,quantity=3,castGUID='first-a'})
          xp.RecordAttempt('alchemy',101,'first-b');xp.RecordOutput({itemID=10,quantity=3,castGUID='first-b'})
          skills.alchemy.cur=3;xp.Sync('alchemy')
          assert(run.currentIndex==2 and run.learningBlocked and run.learningBlockReason=='learningDataMissing')
          assert(run.progress[run.plan.executionSteps[1].segmentID].casts==2)
          assert(not run.finished and #run.plan.executionSteps==2)
        """)

    def test_compact_source_views_are_materialized_in_frozen_execution(self):
        self.lua.execute("""
          local view=setmetatable({raw=42},{__profLearningMaterialize=function()
            return {id='trainer:101',kind='trainer',status='confirmed',conditionsKnown=true,conditions={},trainingCost=10}
          end})
          local p=fixture();p.planID='compact';p.learningPolicyFingerprint=policy
          p.executionSteps[1].recipe.learningInfo={routes={view}}
          local r=assert(xp.StartNew('alchemy',p))
          local frozen=r.plan.executionSteps[1].recipe.learningInfo.routes[1]
          assert(frozen.id=='trainer:101' and frozen.kind=='trainer' and frozen.raw==nil)
          assert(view.raw==42 and rawget(view,'kind')==nil,'source view was mutated')
        """)


if __name__ == "__main__":
    unittest.main()
