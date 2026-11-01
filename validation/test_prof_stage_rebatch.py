"""Stage batching with real Lua 5.1 solver, allocation and lifecycle checks."""
import unittest
import test_prof_solver_fusion as solver
import test_prof_route_plans as lifecycle


CASES = r'''
function craft(id,spell,inputs,item,prof,reason)
 return {id=id,type='craft',profession=prof or 'alchemy',spell=spell,count=1,
  inputs=inputs or {},outputs=item and {{item,1}} or {},item=item,outputCount=item and 1 or 0,
  reason=reason or 'material',from=100,to=100}
end
function buy(id,item,n)
 return {id=id,type='buy',item=item,count=n,cost=n,source='ah'}
end
function ledger(list)
 local stock,pools,allocations,log,money={},{},{},nil,0
 for _,a in ipairs(list)do
  for _,m in ipairs(a.inputs or {})do
   local id,need=m[1],m[2]
   if (stock[id] or 0)<need then return end
   stock[id]=stock[id]-need
   for _,made in ipairs({false,true})do
    for _,p in ipairs(pools[id] or {})do
     if p.made==made and need>0 then
      local n=math.min(need,p.n);need=need-n;p.n=p.n-n
      if n>0 then local k=p.id..'>'..a.id..':'..id;allocations[k]=(allocations[k] or 0)+n end
     end
    end
   end
   assert(need==0)
  end
  local function add(id,n,made)
   stock[id]=(stock[id] or 0)+n;pools[id]=pools[id] or {}
   pools[id][#pools[id]+1]={id=a.id,n=n,made=made}
  end
  if a.type=='buy' or a.type=='seed' then
   add(a.item,a.count,false);money=money+(a.cost or 0)
  else for _,m in ipairs(a.outputs or {})do add(m[1],m[2],a.type=='craft')end end
  log={action=a,prev=log}
 end
 local produced={}
 for id,ps in pairs(pools)do
  produced[id]=0;for _,p in ipairs(ps)do if p.made then produced[id]=produced[id]+p.n end end
 end
 return {log=log,inv=stock,produced=produced,money=money,allocations=allocations,
   skill={alchemy=100},progress={alchemy=0},cap={alchemy=300}}
end
function listOf(state)
 local out={};local p=state.log
 while p do table.insert(out,1,p.action);p=p.prev end
 return out
end
function groups(state)
 local count,last=0,nil
 for _,a in ipairs(listOf(state))do if a.type=='craft' then
  local key=a.profession..':'..a.spell
  if key~=last then count=count+1;last=key end
 end end
 return count
end
function equal(a,b)
 for k,v in pairs(a)do assert(b[k]==v,k..' changed')end
 for k,v in pairs(b)do assert(a[k]==v,k..' added')end
end
function alternating(n,offset)
 local out={buy('raw'..(offset or ''),11,n)}
 for i=1,n do
  local id=tostring(offset or '')..i
  out[#out+1]=craft('A'..id,1,{{11,1}},10)
  out[#out+1]=craft('B'..id,2,{{10,1}},20,nil,'level')
 end
 return out
end
function improve(list,replay,recipes)
 local before=assert((replay or ledger)(list));local calls=0
 local after=ns.ProfRouteSolver.RebatchChronological(before,function(seq)
  calls=calls+1;return (replay or ledger)(seq)
 end,nil,nil,recipes)
 equal(before.allocations,after.allocations)
 equal(before.inv,after.inv)
 assert(before.money==after.money)
 return after,before,calls
end
'''


class StageBatchTests(unittest.TestCase):
    def setUp(self):
        solver.ProfessionSolverFusionTests.setUp(self)
        self.lua.execute(CASES)

    def test_twenty_and_long_routes_batch_in_one_replay(self):
        self.lua.execute('''
          for _,n in ipairs({20,120,350})do
            local after,before,calls=improve(alternating(n))
            assert(groups(before)==2*n and groups(after)==2,tostring(groups(after)))
            assert(calls==1,'one complete batch should need one replay')
          end
        ''')

    def test_nested_cross_profession_dependencies_batch_in_producer_order(self):
        self.lua.execute('''
          local list={buy('raw',11,20)}
          for i=1,20 do
            list[#list+1]=craft('A'..i,1,{{11,1}},10,'mining')
            list[#list+1]=craft('B'..i,2,{{10,1}},20,'engineering')
            list[#list+1]=craft('C'..i,3,{{20,1}},30,'engineering','level')
          end
          local result=improve(list);assert(groups(result)==3)
          local seq=listOf(result)
          assert(seq[2].profession=='mining' and seq[22].spell==2 and seq[42].spell==3)
        ''')

    def test_shared_raw_material_lot_does_not_prevent_batching(self):
        self.lua.execute('''
          local list=alternating(20);list[1].count=40;list[1].cost=40
          for _,a in ipairs(list)do if a.spell==2 then a.inputs[2]={11,1} end end
          local result=improve(list);assert(groups(result)==2)
        ''')

    def test_purchase_and_seed_allocations_are_preserved(self):
        self.lua.execute('''
          local list={{type='seed',id='bag',item=10,count=1},buy('raw',11,4)}
          for i=1,4 do
            list[#list+1]=craft('A'..i,1,{{11,1}},10)
            list[#list+1]=craft('B'..i,2,{{10,1}},20,nil,'level')
            if i==2 then list[#list+1]=buy('bought-intermediate',10,1) end
          end
          local after,before=improve(list)
          assert(groups(after)<groups(before))
          assert(after.allocations['bag>B1:10']==1)
          assert(after.allocations['bought-intermediate>B3:10']==1)
        ''')

    def test_tasks_tools_learning_gathering_and_conversions_separate_stages(self):
        self.lua.execute('''
          for _,kind in ipairs({'formula','gather','convert','specialization_quest','tool_goal'})do
            local list=alternating(10,'first');list[#list+1]={type=kind,id='boundary'}
            local boundary=#list
            for _,a in ipairs(alternating(10,'second'))do list[#list+1]=a end
            local after=improve(list);local seq=listOf(after)
            assert(seq[boundary].id=='boundary' and groups(after)==4,kind)
            for i=1,boundary-1 do assert(not seq[i].id:find('second'),kind)end
            for i=boundary+1,#seq do assert(not seq[i].id:find('first'),kind)end
          end
        ''')

    def test_skill_unlock_and_rank_crossings_separate_stages(self):
        self.lua.execute('''
          local list={craft('A1',1),craft('B1',2),craft('A2',1)}
          list[1].from=1;list[1].to=2;list[2].from=2;list[2].to=3;list[3].from=3;list[3].to=3
          local after=improve(list,nil,{['alchemy:1']={learn=1},['alchemy:2']={learn=2}})
          assert(groups(after)==3)
          list[1].from=74;list[1].to=75;list[2].from=75;list[2].to=75;list[3].from=75;list[3].to=75
          assert(groups(improve(list))==3)
        ''')

    def test_cyclic_material_chain_keeps_required_alternation(self):
        self.lua.execute('''
          local list={buy('raw',11,1),craft('A1',1,{{11,1}},10),
            craft('B1',2,{{10,1}},11),craft('A2',1,{{11,1}},10)}
          local result=improve(list);assert(groups(result)==3)
        ''')

    def test_main_leveling_recipe_order_is_not_rewritten(self):
        self.lua.execute('''
          local list={craft('A1',1,{},nil,nil,'level'),craft('B1',2,{},nil,nil,'secondary'),
            craft('A2',1,{},nil,nil,'level')}
          assert(groups(improve(list))==3)
        ''')

    def test_failed_skill_stage_does_not_block_independent_safe_batches(self):
        self.lua.execute('''
          local list={craft('unsafeA1',90),craft('unsafeB',91),craft('unsafeA2',90),{type='formula'}}
          for _,a in ipairs(alternating(20))do list[#list+1]=a end
          local function replay(seq)
            local result=ledger(seq);if not result then return end
            local xp=1
            for _,a in ipairs(seq)do
              if a.spell==90 and xp<3 then xp=xp+1
              elseif a.spell==91 and xp==2 then xp=xp+2 end
            end
            result.skill.alchemy=xp;return result
          end
          local after,before,calls=improve(list,replay)
          assert(after.skill.alchemy==before.skill.alchemy and groups(after)<groups(before))
          assert(calls<=12)
          local seq=listOf(after)
          assert(seq[1].id=='unsafeA1' and seq[2].id=='unsafeB' and seq[3].id=='unsafeA2')
        ''')

    def test_rejects_more_green_attempts_and_respects_existing_time_budget(self):
        self.lua.execute('''
          local list=alternating(2)
          local function replay(seq)
            local result=ledger(seq);if not result then return end
            result.rebatchGreenCrafts=groups(result)<4 and 1 or 0;return result
          end
          assert(groups(improve(list,replay))==4)
          local before=ledger(alternating(120));local clock=0
          local after=ns.ProfRouteSolver.RebatchChronological(before,function()error('budget exceeded')end,
            nil,function()clock=clock+100;return clock end)
          assert(after==before)
        ''')

    def test_mixed_lot_allocations_survive_varied_valid_routes(self):
        self.lua.execute('''
          math.randomseed(67219)
          for case=1,80 do
            local list={buy('raw',11,200)}
            local made,used=0,0
            for i=1,30 do
              local choice=math.random(1,4)
              if choice==1 then
                list[#list+1]=buy('buy'..i,10,math.random(1,3));made=made+list[#list].count
              elseif choice==2 and made>used then
                local n=math.random(1,math.min(3,made-used))
                list[#list+1]=craft('consumer'..i,2,{{10,n},{11,1}},20,nil,'level');used=used+n
              else
                list[#list+1]=craft('producer'..i,1,{{11,1}},10);made=made+1
              end
            end
            improve(list)
          end
        ''')


NATIVE = r'''
function batchFixture()
 local s=fixture()
 s.recipes={
  {profession='alchemy',spell=101,item=10,count=1,mats={{11,1}},learn=1,yellow=1,green=1,grey=1},
  {profession='alchemy',spell=102,item=20,count=1,mats={{10,1}},learn=1,yellow=100,green=200,grey=300}}
 s.known={['alchemy:101']=true,['alchemy:102']=true};s.prices={[11]=7}
 return s
end
function batchOptions()
 return {snapshot=batchFixture(),start=1,target=21,recoveryEnabled=false,
  specializationRecipeScore=function(_,_,_,cost)return cost end}
end
function verifyBatched(result)
 assert(result.targetReached and result.total==140 and result.crafts==40)
 assert(#result.executionSteps==2,tostring(#result.executionSteps))
 local producer,consumer=result.executionSteps[1],result.executionSteps[2]
 assert(producer[3]==101 and producer[4]==20 and consumer[3]==102 and consumer[4]==20)
 assert(producer.requiredOutputs[10]==20)
 local allocated=0
 for _,a in ipairs(producer.allocations)do
  assert(a.consumerID==consumer.segmentID and a.itemID==10);allocated=allocated+a.count
 end
 assert(allocated==20)
 assert(result.mats[1].id==11 and result.mats[1].count==20 and result.mats[1].cost==140)
end
'''


class NativeStageBatchTests(unittest.TestCase):
    def setUp(self):
        lifecycle.NativeRoutePlansTests.setUp(self)
        self.lua.execute(NATIVE)

    def test_actual_strategy_candidate_batches_and_rebuilds_allocations(self):
        self.lua.execute('''
          local r,j=ns.ProfRouteSolver.Compute('alchemy',batchOptions())
          assert(not j.error,tostring(j.error));verifyBatched(r)
        ''')

    def test_new_candidate_does_not_change_frozen_execution(self):
        self.lua.execute('''
          local solver=ns.ProfRouteSolver;local original=solver.RebatchChronological
          solver.RebatchChronological=function(s)return s end
          local old=ns.ProfRouteAuto.Compute('alchemy',batchOptions())
          assert(#old.executionSteps==40)
          local run=assert(ns.ProfExecution.StartNew('alchemy',old))
          local frozen=run.plan;local first=frozen.executionSteps[1].segmentID
          solver.RebatchChronological=original
          local candidate=ns.ProfRouteAuto.Compute('alchemy',batchOptions());verifyBatched(candidate)
          assert(ns.ProfExecution.GetRun('alchemy')==run and run.plan==frozen)
          assert(#run.plan.executionSteps==40 and run.plan.executionSteps[1].segmentID==first)
        ''')

    def test_explicit_fixed_sequence_and_preserve_order_are_protected(self):
        self.lua.execute('''
          local opts=batchOptions();opts.preserveRecipeOrder=true
          local r=ns.ProfRouteSolver.Compute('alchemy',opts)
          assert(#r.executionSteps==40)
          opts=batchOptions();opts.fixedSteps={};opts.specializationRecipeScore=nil
          for i=1,20 do
            opts.fixedSteps[#opts.fixedSteps+1]={i,i,101,1,profession='alchemy',preserveCount=true,reason='material'}
            opts.fixedSteps[#opts.fixedSteps+1]={i,i+1,102,1,profession='alchemy',preserveCount=true,reason='level'}
          end
          r=ns.ProfRouteSolver.Compute('alchemy',opts)
          assert(r.targetReached and #r.executionSteps==40)
        ''')

    def test_non_stable_route_cannot_increase_green_leveling_attempts(self):
        self.lua.execute('''
          local opts=batchOptions();opts.target=5
          local a,b=opts.snapshot.recipes[1],opts.snapshot.recipes[2]
          a.yellow=3;a.green=3;a.grey=3;b.yellow=3;b.green=3;b.grey=5
          local solver=ns.ProfRouteSolver;local original=solver.RebatchChronological
          solver.RebatchChronological=function(s)return s end
          local before,old=solver.Compute('alchemy',opts)
          solver.RebatchChronological=original
          local after,job=solver.Compute('alchemy',opts)
          assert(before.targetReached and after.targetReached)
          assert(old.best.rebatchGreenCrafts>0 and job.best.rebatchGreenCrafts<=old.best.rebatchGreenCrafts)
          assert(before.total==after.total and before.crafts==after.crafts)
          assert(after.plannedTo>=before.plannedTo)
        ''')

    def test_batched_skeleton_restores_same_counts_and_dependencies(self):
        self.lua.execute('''
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(batchFixture())end
          opts=batchOptions();opts.snapshot=nil
          before=finish('alchemy',opts);verifyBatched(before)
        ''')
        self.load((lifecycle.ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          local restored=finish('alchemy',opts)
          assert(restored.fromSkeleton);verifyBatched(restored)
        ''')


if __name__ == '__main__':
    unittest.main()
