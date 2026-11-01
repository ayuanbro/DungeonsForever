"""Grouped route presentation retains an executable, finite-supply ledger."""
import unittest
import test_prof_route_plans as routes
from test_prof_native_data import native_runtime


class GroupedEngineeringLedgerTests(unittest.TestCase):
    setUp=routes.NativeRoutePlansTests.setUp

    def test_powder_and_dynamite_are_grouped_without_reordering_execution(self):
        self.lua.execute('''
          local E,S=ns.ProfEconomy,ns.ProfRouteSolver
          local s={recipes={
            {profession='engineering',spell=101,item=10,count=1,mats={{11,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false},
            {profession='engineering',spell=102,item=20,count=1,mats={{10,1},{12,1}},
              learn=1,yellow=100,green=200,grey=300,cooldown=false}},
            professions={engineering={cur=1,max=300}},known={['engineering:101']=true,['engineering:102']=true},
            prices={[11]=2,[12]=3},auctionSupply={[11]={quantity=5},[12]={quantity=5}},coverageComplete=true}
          local sequence={}
          for i=1,5 do
            sequence[#sequence+1]={0,0,101,1,profession='engineering'}
            sequence[#sequence+1]={0,0,102,1,profession='engineering'}
          end
          groupedPlan=S.Compute('engineering',{snapshot=s,start=1,target=11,fixedSteps=sequence,
            autoCraftTools=false,recoveryEnabled=false,considerAuctionSupply=true})
          local r=groupedPlan
          assert(r.targetReached and r.total==25 and r.supplyComplete)
          assert(#r.steps==2 and r.steps[1][3]==101 and r.steps[2][3]==102)
          assert(r.steps[1][4]==5 and r.steps[2][4]==5 and r.crafts==10)
          assert(#r.steps[1].segmentIDs==5 and #r.steps[2].segmentIDs==5)
          assert(#r.executionSteps==10,'grouping hid required chronology')
          local powder=0
          for index,step in ipairs(r.executionSteps)do
            assert(step[4]==1)
            if step[3]==101 then powder=powder+1;assert(step.stepIndex==1)
            else powder=powder-1;assert(step[3]==102 and step.stepIndex==2)end
            assert(powder>=0,'consumer ran before its producer')
          end
          assert(powder==0 and r.inventory[10]==0 and r.inventory[20]==5)
          for _,m in ipairs(r.mats)do assert(m.count==5 and (m.id==11 or m.id==12))end
          skills={engineering={cur=1,max=300}}
          local xp=ns.ProfExecution
          local run=xp.Bind('engineering',r)
          assert(run and run.currentIndex==1)
          for index,step in ipairs(r.executionSteps)do
            local cast='grouped:'..index
            assert(xp.RecordAttempt('engineering',step[3],cast))
            assert(xp.RecordOutput({itemID=step.item,quantity=1,castGUID=cast}))
            skills.engineering.cur=step[2];xp.Sync('engineering')
            assert(run.currentIndex==index+1,'execution did not follow chronological segments')
          end
          assert(run.finished and xp.Progress('engineering',1).complete)
        ''')


class CompletedEngineeringIntroductionTests(unittest.TestCase):
    def test_completed_intro_does_not_stop_ordinary_engineering_at_200(self):
        lua=native_runtime()
        lua.execute('''
          selected='engineering'
          C_QuestLog={IsQuestFlaggedCompleted=function(id)return id==3641 end}
          local opts={start=200,target=205,engineeringSpecialization='gnomish',
            autoCraftTools=false,noFormula=true,recoveryEnabled=false,cpuLimitMs=1000}
          local E=ns.ProfEconomy
          local s=E.Capture('engineering',opts)
          assert(s.specializationAbilities[20219]==false)
          assert(#s.specializationGoals==0 and #s.specializationContext.unresolvedGoals==1)
          local r=ns.ProfRouteSolver.Compute('engineering',opts)
          assert(r.targetReached and r.plannedTo>=205 and #r.steps>0,
            'completed introduction still blocked ordinary leveling at 200')
          assert(r.specializationAbilities[20219]~=true,'quest completion invented a specialization')
          assert(not r.specializationComplete and not r.inputModelOptimal)
          local warning=false
          for _,d in ipairs(r.diagnostics)do
            if d.code=='specializationQuestAlreadyCompleted'then warning=true end
          end
          assert(warning,'the unresolved specialization silently disappeared')
          for _,action in ipairs(r.actions)do
            assert(action.type~='specialization_quest','completed quest was planned again')
            if action.type=='craft'then
              assert(ns.ProfGates.RequiredAbility(action.spell)==0,
                'unverified specialization unlocked a specialized recipe')
            end
          end
        ''')

    def test_uncompleted_intro_keeps_real_specialization_requirements(self):
        lua=native_runtime()
        lua.execute('''
          selected='engineering'
          C_QuestLog={IsQuestFlaggedCompleted=function()return false end}
          UnitLevel=function()return 20 end
          local s=ns.ProfEconomy.Capture('engineering',{start=200,target=205,
            engineeringSpecialization='gnomish',autoCraftTools=false})
          assert(#s.specializationGoals==1 and s.specializationGoals[1].blockedReason=='specializationLevelRequired')
          assert(s.specializationAbilities[20219]~=true)
        ''')


if __name__=='__main__':unittest.main()
