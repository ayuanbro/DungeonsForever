"""Batch scheduling reprices actual execution, including incidental skill gains."""
import unittest
import json
from pathlib import Path
import test_prof_solver_fusion as fixtures
import test_prof_route_plans as lifecycle
from test_prof_native_data import native_runtime


SETUP = r'''
function engineering()
 local a=recipe('engineering',3918,4357,1,{{2835,1}},1,40);a.yellow=20;a.green=30
 local b=recipe('engineering',3919,4358,2,{{4357,1},{2589,1}},1,60);b.yellow=30;b.green=45
 local s=snapshot({a,b},{[2835]=2,[2589]=3});s.professions={engineering={cur=1,max=75}}
 return s
end
function finalizeBatch(job)
 job.opts.fixedSteps=nil;job.opts.preserveRecipeOrder=nil
 job.finished=false;job.rebatchFinalized=nil;job.resultState=nil;job.resultCache=nil
 job.co=coroutine.create(function()
  job.result=ns.ProfRouteSolver.Result(job,job.best,job.status);job.finished=true
 end)
 for i=1,20000 do if ns.ProfRouteSolver.Run(job,.2) then return job.result end end
 error('batch finalization did not finish')
end
function planned(s,target,extra)
 local opts=extra or {};opts.fixedSteps=opts.fixedSteps or {{1,target,3919,1}}
 local before,job=solve('engineering',s,target,opts)
 assert(before.targetReached,tostring(job.error))
 local after=finalizeBatch(job)
 assert(after.targetReached and not job.error,tostring(job.error))
 return before,after,job
end
function assertLedger(r)
 local stock={}
 for _,a in ipairs(r.actions)do
  if a.type=='buy' or a.type=='seed' then stock[a.item]=(stock[a.item] or 0)+a.count
  else
   for _,m in ipairs(a.inputs or {})do
    stock[m[1]]=(stock[m[1]] or 0)-m[2];assert(stock[m[1]]>=0,'material consumed before production')
   end
   for _,m in ipairs(a.outputs or {})do stock[m[1]]=(stock[m[1]] or 0)+m[2]end
  end
 end
 for id,n in pairs(r.inventory)do assert((stock[id] or 0)==n,'inventory mismatch')end
 local money=0;for _,m in ipairs(r.mats)do money=money+m.cost end
 assert(math.abs(money-r.matTotal)<1e-6,'purchase budget mismatch')
end
'''


class BatchExecutionTests(unittest.TestCase):
    def setUp(self):
        fixtures.ProfessionSolverFusionTests.setUp(self)
        self.lua.execute(SETUP)

    def test_powder_then_dynamite_recomputes_counts_from_actual_batch_skill(self):
        self.lua.execute('''
          local before,after=planned(engineering(),50)
          assert(#before.executionSteps>30 and #after.executionSteps==2)
          local a,b=after.executionSteps[1],after.executionSteps[2]
          assert(a[3]==3918 and b[3]==3919 and a[4]==b[4])
          assert(after.crafts<before.crafts and after.total<before.total)
          assert(a[2]==b[1] and b[2]>=50)
          assert(a.requiredOutputs[4357]==b[4])
          for _,edge in ipairs(a.allocations)do assert(edge.consumerID==b.segmentID)end
          assert(bought(after,2835)==a[4] and bought(after,2589)==b[4])
          assertLedger(after)
        ''')

    def test_batch_cost_and_input_counts_do_not_change_with_preexisting_materials(self):
        self.lua.execute('''
          local s=engineering();s.inventory={[4357]=5};s.auctionSupply={[2835]={quantity=100},[2589]={quantity=100}}
          local before,after=planned(s,50,{executionInventory={[4357]=5},considerAuctionSupply=true})
          assert(#after.executionSteps==2)
          assert(bought(after,2835)==after.executionSteps[1][4])
          assert(after.executionSteps[1][4]==after.executionSteps[2][4])
          assert(bought(after,2835)<=100 and bought(after,2589)<=100)
          assertLedger(after)
        ''')

    def test_stable_route_never_adds_green_leveling_attempts(self):
        self.lua.execute('''
          local before,after=planned(engineering(),50,{scheme='stable'})
          assert(after.greenLevelCrafts<=before.greenLevelCrafts)
          assertLedger(after)
        ''')

    def test_fixed_guide_order_is_untouched_until_explicit_new_candidate(self):
        self.lua.execute('''
          local r,j=solve('engineering',engineering(),50,{fixedSteps={{1,50,3919,1}}})
          assert(#r.executionSteps>30 and j.best and r.targetReached)
          assertLedger(r)
        ''')

    def test_gray_intermediate_batches_for_different_unlocked_recipes(self):
        self.lua.execute('''
          local bolt=recipe('engineering',1,10,1,{{11,1}},1,20)
          local a=recipe('engineering',2,20,1,{{10,1}},30,300)
          local b=recipe('engineering',3,30,1,{{10,2}},35,300)
          local c=recipe('engineering',4,40,1,{{10,3}},40,300)
          local s=snapshot({bolt,a,b,c},{[11]=1});s.professions={engineering={cur=30,max=75}}
          local before,after=planned(s,45,{start=30,fixedSteps={{30,35,2,1},{35,40,3,1},{40,45,4,1}}})
          assert(#after.executionSteps==4 and after.executionSteps[1][3]==1)
          assert(after.executionSteps[1][4]==30 and after.total==30 and after.crafts==45)
          assert(after.executionSteps[2][3]==2 and after.executionSteps[3][3]==3 and after.executionSteps[4][3]==4)
          assertLedger(after)
        ''')

    def test_material_cycles_keep_executable_order(self):
        self.lua.execute('''
          local a=recipe('engineering',1,10,1,{{11,1}},1,300)
          local b=recipe('engineering',2,11,1,{{10,1}},1,300)
          local s=snapshot({a,b},{[11]=1});s.professions={engineering={cur=1,max=75}}
          local before,after=planned(s,5,{executionInventory={[11]=1},fixedSteps={{1,2,1,1},{2,3,2,1},{3,4,1,1},{4,5,2,1}}})
          assert(#after.executionSteps==4 and after.crafts==4)
          assertLedger(after)
        ''')

    def test_gray_batch_keeps_later_formula_purchase_and_skill_unlock(self):
        self.lua.execute('''
          local bolt=recipe('engineering',1,10,1,{{11,1}},1,20)
          local a=recipe('engineering',2,20,1,{{10,1}},30,300)
          local b=recipe('engineering',3,30,1,{{10,2}},35,300);b.formula=100
          local s=snapshot({bolt,a,b},{[11]=1});s.professions={engineering={cur=30,max=75}}
          s.known['engineering:3']=nil
          s.formulaOffers={[100]={{npcID=1,price=10,quantity=1,unlimited=true}}}
          local before,after=planned(s,40,{start=30,fixedSteps={{30,35,2,1},{35,40,3,1}}})
          assert(#after.executionSteps==3 and after.executionSteps[1][3]==1)
          assert(after.executionSteps[3][3]==3 and after.executionSteps[3][1]>=35)
          assert(after.formulasTotal==10 and #after.formulas==1 and after.total==25)
          assertLedger(after)
        ''')

    def test_cpu_cutoff_finishes_batch_build_in_the_coroutine(self):
        self.lua.execute('''
          local before,j=solve('engineering',engineering(),50,{fixedSteps={{1,50,3919,1}}})
          j.cpuLimitMs=1
          local after=finalizeBatch(j)
          assert(not j.error and j.rebatchFinalized and #after.executionSteps==2)
          assertLedger(after)
        ''')


class NativeBatchExecutionTests(unittest.TestCase):
    def test_saved_engineering_recipe_itinerary_with_real_catalogue(self):
        lua=native_runtime()
        lua.execute(fixtures.FIXTURE[fixtures.FIXTURE.index('function recipe'):])
        lua.execute(SETUP)
        case=json.loads((Path(__file__).parent/'fixtures/engineering_batch_route.json').read_text(encoding='utf-8'))
        lua.globals().savedSteps=lua.table_from([lua.table_from(row) for row in case['steps']])
        lua.execute('''
          local E=ns.ProfEconomy;local recs,known,outputs,prices,seen={},{},{},{},{}
          for _,st in ipairs(savedSteps)do
            local key='engineering:'..st[3]
            if not seen[key] and st[3]~=0 then
              local r=assert(E.FindRecipe('engineering',st[3]),key)
              recs[#recs+1]=r;known[key]=true;seen[key]=true
              if r.item then outputs[r.item]=true end
            end
          end
          for _,r in ipairs(recs)do for _,m in ipairs(r.mats)do if not outputs[m[1]] then prices[m[1]]=1 end end end
          local s={recipes=recs,known=known,prices=prices,professions={engineering={cur=1,max=300}}}
          local before,after=planned(s,300,{fixedSteps=savedSteps})
          assert(#before.executionSteps>350 and #after.executionSteps<60)
          assert(after.crafts<=before.crafts and after.total<=before.total)
          assert(after.executionSteps[1][3]==3918 and after.executionSteps[1][4]>20)
          assert(after.executionSteps[2][3]==3919 and after.executionSteps[2][4]>20)
          local bolts=0
          for _,st in ipairs(after.executionSteps)do
            if st[3]==3922 and st[1]>=75 and st[1]<150 then bolts=bolts+1 end
          end
          assert(bolts==1,'gray bolts are still split around each finished recipe')
          assertLedger(after)
        ''')


class BatchLifecycleTests(unittest.TestCase):
    def setUp(self):
        lifecycle.NativeRoutePlansTests.setUp(self)
        self.lua.execute(fixtures.FIXTURE[fixtures.FIXTURE.index('function recipe'):])
        self.lua.execute(SETUP)
        self.lua.execute("skills={engineering={cur=1,max=75}}")

    def test_frozen_plan_and_hud_progress_use_full_batch_counts(self):
        self.lua.execute('''
          local before,after=planned(engineering(),50)
          local xp=ns.ProfExecution;local run=assert(xp.StartNew('engineering',after))
          assert(#run.plan.executionSteps==2)
          local p=xp.Progress('engineering',1)
          assert(p.remainingCrafts>=after.executionSteps[1][4] and p.remainingCrafts>20)
          assert(xp.Progress('engineering',2).remainingCrafts>=after.executionSteps[2][4])
          assert(run.currentIndex==1 and not p.complete)
        ''')

    def test_batched_candidate_skeleton_restores_same_counts_and_costs(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(engineering())end
          opts={start=1,target=50,recoveryEnabled=false,autoCraftTools=false,cpuLimitMs=100}
          original=finish('engineering',opts)
          assert(#original.executionSteps==2 and original.targetReached)
        ''')
        self.load((lifecycle.ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local restored=finish('engineering',opts)
          assert(restored.fromSkeleton and restored.targetReached and #restored.executionSteps==2)
          assert(restored.total==original.total and restored.crafts==original.crafts)
          for i,st in ipairs(restored.executionSteps)do assert(st[4]==original.executionSteps[i][4])end
          assertLedger(restored)
        ''')


if __name__=='__main__':unittest.main()
