"""Execution chronology, material obligations and incremental procurement regressions."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_prof_solver import SolverTests, ROOT


class ExecutionSolverTests(SolverTests):
    # Inherit only setup; base oracle tests are discovered independently.
    def normalize_fixture(self):
        source = (ROOT / "Core/ProfRouteSolver.lua").read_text(encoding="utf-8-sig")
        source = source.replace("    j.co=coroutine.create(function()", "    j.auditNormalize=batchPlan\n    j.co=coroutine.create(function()", 1)
        self.lua.eval("function(s) assert(loadstring(s))('DungeonsForever',ns) end")(source)
        self.lua.execute(r"""
          function normalize(s,seq,options)
            options=options or {};options.snapshot=s;options.start=options.start or 1;options.target=options.target or 4
            local j=ns.ProfRouteSolver.NewJob('alchemy',options)
            ns.ProfRouteSolver.Run(j,2)
            local raw={diagnostics={}}
            for _,a in ipairs(seq) do raw.log={prev=raw.log,action=a} end
            local state
            local co=coroutine.create(function() state=j.auditNormalize(raw,true) end)
            while coroutine.status(co)~='dead' do local ok,e=coroutine.resume(co);assert(ok,e) end
            return state and ns.ProfRouteSolver.Result(j,state,'complete'),j
          end
          function buy(id,n,cost,bundle,source,owner)
            return {type='buy',item=id,count=n,cost=cost,bundleSize=bundle or 1,source=source or 'ah',owner=owner}
          end
          function make(spell,n,reason)
            return {type='craft',profession='alchemy',spell=spell,count=n,reason=reason or 'level'}
          end
        """)

    def test_interleaved_material_recipe_keeps_dependency_chronology_and_fraction(self):
        self.normalize_fixture()
        self.lua.execute(r"""
          local a=recipe('alchemy',101,10,1,{{11,1}},1,3);a.yellow=1;a.green=2
          local b=recipe('alchemy',102,20,1,{{10,1},{12,1}},1,3);b.yellow=1;b.green=2
          local c=recipe('alchemy',103,30,1,{{10,2}},3,100)
          local s=snapshot({a,b,c},{[11]=1,[12]=1})
          local seq={buy(11,3,3),buy(12,1,1),make(101,1),make(102,1),make(101,2,'material'),make(103,1)}
          local r=normalize(s,seq)
          assert(r.targetReached and #r.steps==3 and #r.executionSteps==4)
          local expected={101,102,101,103}
          for i,spell in ipairs(expected) do assert(r.executionSteps[i][3]==spell) end
          local trial=r.executionSteps[2]
          assert(trial[1]==trial[2] and trial.expectedGain==.5 and trial.role=='level')
          assert(trial.attemptLimit==1 and trial.goalSkill==3 and trial.fractionalTransition)
          assert(r.steps[1][4]==3 and #r.steps[1].segmentIDs==2)
          assert(r.executionSteps[1].requiredOutputs[10]==1)
          assert(r.executionSteps[3].requiredOutputs[10]==2 and r.executionSteps[3].materialMinCrafts==2)
          assert(r.executionSteps[1].allocations[1].consumerID==trial.segmentID)
          local again=normalize(s,seq)
          for i,step in ipairs(r.executionSteps) do assert(step.segmentID==again.executionSteps[i].segmentID) end
        """)

    def test_zero_gain_unused_parent_removed_and_ah_surplus_repriced(self):
        self.normalize_fixture()
        self.lua.execute(r"""
          local a=recipe('alchemy',101,10,1,{{11,1}},1,3);a.yellow=1;a.green=2
          local b=recipe('alchemy',102,20,1,{{10,3},{12,1}},1,3);b.yellow=1;b.green=2
          local r=normalize(snapshot({a,b},{[11]=1,[12]=7}),
            {buy(11,10,10,1,'ah','alchemy:102'),buy(12,1,7),make(101,3,'material'),make(102,1)}, {target=3})
          assert(r.targetReached and r.total==3 and #r.executionSteps==1)
          assert(r.executionSteps[1][3]==101 and r.executionSteps[1].role=='level')
          assert(r.executionSteps[1].cost==r.total and r.executionSteps[1].materialMinCrafts==0)
          assert(#r.mats==1 and r.mats[1].id==11 and r.mats[1].count==3)
          assert(r.inventory[10]==3 and not r.inventory[12])
        """)

    def test_cleanup_preserves_npc_pack_rounding(self):
        self.normalize_fixture()
        self.lua.execute(r"""
          local a=recipe('alchemy',101,10,1,{{11,1}},1,3);a.yellow=1;a.green=2
          local b=recipe('alchemy',102,20,1,{{10,3}},1,3);b.yellow=1;b.green=2
          local s=snapshot({a,b},{})
          s.offers={[11]={{unlimited=true,price=7,quantity=5,npcID=1}}}
          local r=normalize(s,{buy(11,20,28,5,'vendor'),make(101,3,'material'),make(102,1)},{target=3})
          assert(r.total==7 and r.mats[1].count==5 and r.inventory[11]==2)
        """)

    def test_cleanup_cannot_convert_material_only_recipe_to_forbidden_leveling(self):
        self.normalize_fixture()
        self.lua.execute(r"""
          local a=recipe('alchemy',101,10,1,{{11,1}},1,3);a.yellow=1;a.green=2
          local b=recipe('alchemy',102,20,1,{{10,3}},1,3);b.yellow=1;b.green=2
          local r=normalize(snapshot({a,b},{[11]=1}),{buy(11,3,3),make(101,3,'material'),make(102,1)},
            {target=3,exclusions={['alchemy:101']='level'}})
          assert(r==nil)
        """)

    def test_variable_output_allocations_use_units_and_guaranteed_minimum(self):
        self.lua.execute(r"""
          local a=recipe('alchemy',101,10,2,{{11,1}},1,1);a.outputMin=2;a.outputMax=4;a.variableOutput=true
          local r=ns.ProfRouteSolver.ProcureMany(snapshot({a},{[11]=3}),{[10]=3},{materialProfession='alchemy'})
          assert(r.feasible and r.procurement and r.target==nil and #r.executionSteps==1)
          local step=r.executionSteps[1]
          assert(step.outputMin==2 and step.outputMax==4 and step.requiredOutputs[10]==3)
          assert(step.materialMinCrafts==2 and step.expectedCrafts==2 and step.role=='material')
          assert(step.allocations[1].consumerID=='demand:10' and step.allocations[1].count==3)
          assert(r.inventory[10]==1)
        """)

    def test_procure_many_shares_intermediate_output_and_finite_auction_budget(self):
        self.lua.execute(r"""
          local a=recipe('alchemy',101,10,2,{{11,1}},1,1)
          local b=recipe('alchemy',102,12,1,{{10,1}},1,1)
          local s=snapshot({a,b},{[11]=3});s.auctionSupply={[11]={quantity=1,complete=true}}
          local r=ns.ProfRouteSolver.ProcureMany(s,{{id=10,count=1},{id=12,count=1}},{materialProfession='alchemy'})
          assert(r.feasible and r.total==3 and #r.mats==1 and r.mats[1].count==1)
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==1 and #r.executionSteps==2)
          local bad=ns.ProfRouteSolver.ProcureMany(s,{[10]=2,[12]=1},{materialProfession='alchemy'})
          assert(not bad.feasible)
        """)

    def test_procure_many_only_accepts_explicit_execution_stock_not_bags(self):
        self.lua.execute(r"""
          local s=snapshot({}, {}, {[10]=999})
          local bad=ns.ProfRouteSolver.ProcureMany(s,{[10]=2},{materialProfession='alchemy'})
          assert(not bad.feasible)
          local r=ns.ProfRouteSolver.ProcureMany(s,{[10]=2},{materialProfession='alchemy',executionInventory={[10]=3}})
          assert(r.feasible and r.total==0 and #r.mats==0 and #r.executionSteps==0 and r.inventory[10]==1)
          assert(r.seedInventory[10]==3 and r.seedAllocations[1].count==2 and r.seedAllocations[1].consumerID=='demand:10')
          local unusable=ns.ProfRouteSolver.ProcureMany(s,{[10]=2},{materialProfession='alchemy',executionInventory={[10]={count=3,usable=false}}})
          assert(not unusable.feasible)
        """)

    def test_procure_many_missing_quote_cannot_use_other_profession(self):
        self.lua.execute(r"""
          local a=recipe('mining',101,10,1,{{11,1}},1,1)
          local s=snapshot({a},{[11]=3})
          local r=ns.ProfRouteSolver.ProcureMany(s,{[10]=1},{materialProfession='alchemy'})
          assert(not r.feasible)
        """)

    def test_deferred_procurement_returns_unstarted_cooperative_job(self):
        self.lua.execute(r"""
          local r,j=ns.ProfRouteSolver.ProcureMany(snapshot({}, {[11]=3}),{[11]=2},{defer=true})
          assert(r==nil and j.snap==nil and coroutine.status(j.co)=='suspended')
          for i=1,100 do if ns.ProfRouteSolver.Run(j,2) then break end end
          assert(j.result.feasible and j.result.procurement and j.result.total==6)
        """)


# Do not rediscover inherited base tests in this module.
for _name in tuple(vars(SolverTests)):
    if _name.startswith('test_') and _name not in vars(ExecutionSolverTests):
        setattr(ExecutionSolverTests, _name, None)
del SolverTests

if __name__ == '__main__':
    unittest.main()
