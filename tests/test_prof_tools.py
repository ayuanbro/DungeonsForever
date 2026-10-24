"""Mandatory permanent tool goals share procurement and execution contracts."""
import unittest

import test_prof_runtime as fixture


class ProfessionToolTests(unittest.TestCase):
    def setUp(self):
        fixture.RuntimeTests.setUp(self)
        self.load(str(fixture.ROOT / "Core/Data/Data_ProfTools.lua"))
        self.lua.execute("""
          function toolRecipe(p,spell,item,learn,grey,mats)
            return {profession=p,spell=spell,item=item,count=1,learn=learn,
              yellow=grey,green=grey,grey=grey,mats=mats,cooldown=false}
          end
          function engineeringTools(price)
            return {recipes={toolRecipe('engineering',7430,6219,50,90,{{2840,6}}),
              toolRecipe('engineering',101,10,1,300,{{11,1}})},
              professions={engineering={cur=100,max=300}},known={['engineering:7430']=true,['engineering:101']=true},
              prices={[2840]=2,[6219]=price,[11]=1}}
          end
          function toolsSolve(s,p,start,target,extra)
            local o=extra or {};o.snapshot=s;o.start=start;o.target=target
            local r,j=ns.ProfRouteSolver.Compute(p,o)
            assert(not j.error,tostring(j.error));return r,j
          end
          function made(r,spell)
            local n=0;for _,a in ipairs(r.actions or {}) do if a.type=='craft' and a.spell==spell then n=n+a.count end end;return n
          end
        """)

    def test_real_catalogue_ids_and_forever_skill_thresholds(self):
        self.load(str(fixture.ROOT / "Core/Data/Data_ProfRecipes.lua"))
        self.load(str(fixture.ROOT / "Core/Data/Data_ProfLeveling.lua"))
        self.lua.execute("""
          local total=0
          for _,p in ipairs({'engineering','alchemy','enchanting'}) do
            for _,tool in ipairs(ns.ProfTools[p]) do
              local r=ns.ProfEconomy.FindRecipe(p,tool.spell)
              assert(r and r.item==tool.item,p..':'..tool.spell)
              local data=ns.ProfRecipes[p];local checked=false
              for _,kind in ipairs({'rows','crafted'}) do for _,row in ipairs(data[kind] or {}) do
                if row[1]==tool.spell then assert(row[kind=='rows' and 7 or 4]==tool.minSkill);checked=true end
              end end
              assert(checked)
              total=total+1
            end
          end
          assert(total==8 and ns.ProfTools.alchemy[2].minSkill==275)
        """)

    def test_default_and_strict_target_boundary_and_disabled_option(self):
        self.lua.execute("""
          local e=ns.ProfEconomy
          assert(e.ToolPlanningEnabled())
          local s=engineeringTools(20)
          assert(#e.Capture('engineering',{snapshot=s,target=50}).toolGoals==0)
          assert(#e.Capture('engineering',{snapshot=s,target=51}).toolGoals==1)
          assert(#e.Capture('engineering',{snapshot=s,target=51,autoCraftTools=false}).toolGoals==0)
          local r=toolsSolve(s,'engineering',100,101,{autoCraftTools=false})
          assert(r.targetReached and r.total==1 and made(r,7430)==0)
        """)

    def test_tradeable_tool_compares_craft_auction_and_verified_vendor(self):
        self.lua.execute("""
          local s=engineeringTools(20)
          local r=toolsSolve(s,'engineering',100,101)
          assert(r.targetReached and r.total==13 and made(r,7430)==1)
          s.prices[6219]=3;r=toolsSolve(s,'engineering',100,101)
          assert(r.targetReached and r.total==4 and made(r,7430)==0)
          s.offers={[6219]={{unlimited=true,price=2,quantity=1}}}
          r=toolsSolve(s,'engineering',100,101)
          assert(r.total==3 and r.vendorTotal==2 and made(r,7430)==0)
          s.prices[6219]=nil;s.offers={};r=toolsSolve(s,'engineering',100,101)
          assert(r.total==13 and made(r,7430)==1)
          s.auctionSupply={[6219]={quantity=0}};s.prices[6219]=1
          r=toolsSolve(s,'engineering',100,101)
          assert(made(r,7430)==1 and r.total==13)
        """)

    def test_grey_tool_stays_a_real_execution_output_obligation(self):
        self.lua.execute("""
          local r=toolsSolve(engineeringTools(20),'engineering',100,101)
          assert(r.executionVersion==1 and r.executionSteps[1][3]==7430)
          local t=r.executionSteps[1]
          assert(t.tool and t.toolItem==6219 and t.expectedGain==0)
          assert(t.requiredOutputs[6219]==1 and t.materialMinCrafts==1)
          assert(r.inventory[6219]==1 and #r.toolGoals==1)
        """)

    def test_bound_tools_never_use_auction_or_vendor_and_all_lower_tools_are_added(self):
        self.lua.execute("""
          local s={recipes={},prices={[1]=2},offers={},known={},professions={alchemy={cur=280,max=300}}}
          for _,t in ipairs(ns.ProfTools.alchemy) do
            s.recipes[#s.recipes+1]=toolRecipe('alchemy',t.spell,t.item,t.minSkill,300,{{1,1}})
            s.known['alchemy:'..t.spell]=true;s.prices[t.item]=1
            s.offers[t.item]={{unlimited=true,price=0,quantity=1}}
          end
          local r=toolsSolve(s,'alchemy',280,281)
          assert(r.targetReached and r.total==4)
          for _,t in ipairs(ns.ProfTools.alchemy) do assert(made(r,t.spell)==1 and r.inventory[t.item]==1) end
          for _,a in ipairs(r.actions) do if a.type=='buy' then assert(a.item==1) end end
        """)

    def test_retained_tool_is_not_sale_revenue(self):
        self.load(str(fixture.ROOT / "Core/ProfRecovery.lua"))
        self.lua.execute("""
          local s=engineeringTools(20)
          s.sellPrices={[6219]=999,[10]=0}
          local r=toolsSolve(s,'engineering',100,101,{recoveryFeePercent=0})
          assert(r.targetReached and r.recoveryTotal==0 and r.netTotal==r.total)
          for _,out in ipairs(r.saleOutputs) do assert(out.id~=6219) end
          assert(#r.retainedTools==1 and r.retainedTools[1].id==6219)
        """)

    def test_fixed_and_other_automatic_modes_include_tool(self):
        self.lua.execute("""
          local s=engineeringTools(20)
          local o={snapshot=s,start=100,target=101}
          local fixed=ns.ProfRouteAuto.SummarizeSteps({{100,101,101,1}},'engineering',o)
          assert(fixed.mode=='fixed' and fixed.targetReached and made(fixed,7430)==1 and fixed.total==13)
          for _,scheme in ipairs({'cheapest','matcost','crafts','optim'}) do
            o.scheme=scheme
            local r=ns.ProfRouteAuto.Compute('engineering',o)
            assert(r.targetReached and made(r,7430)==1,scheme)
          end
        """)

    def test_policy_change_blocks_old_cache_and_preserves_source(self):
        self.lua.execute("""
          local ra=ns.ProfRouteAuto
          local old={steps={{100,101,101,1}},mats={{id=11,count=1}},total=1}
          local view=ra.ValidateSpecializationPlan(old,'engineering')
          assert(view.status=='recalculate_required' and view.diagnostics[1].code=='toolPolicyChanged')
          assert(old.total==1 and #old.steps==1)
          ra.StampToolPolicy(old,'engineering')
          assert(not ra.ToolPolicyChanged(old,'engineering'))
          DungeonsForeverDB={prof={autoCraftTools=false}}
          assert(ra.ToolPolicyChanged(old,'engineering'))
          view=ra.ValidateSpecializationPlan(old,'engineering')
          assert(#view.mats==0 and #old.mats==1)
        """)

    def test_procurement_does_not_schedule_parent_tool_goals(self):
        self.lua.execute("""
          local s=ns.ProfEconomy.Capture('engineering',{snapshot=engineeringTools(20),target=101})
          local r=ns.ProfRouteSolver.ProcureMany(s,{[11]=2})
          assert(r.feasible and r.total==2 and made(r,7430)==0)
        """)

    def test_tool_skill_gain_reduces_fixed_recipe_and_purchase_quantity(self):
        self.lua.execute("""
          ns.ProfTools.engineering={{spell=7430,item=6219,minSkill=1}}
          local s={recipes={toolRecipe('engineering',7430,6219,1,20,{{1,1}}),
            toolRecipe('engineering',101,10,1,300,{{2,1}})},known={},
            prices={[1]=1,[2]=10},professions={engineering={cur=1,max=300}}}
          local r=ns.ProfRouteAuto.SummarizeSteps({{1,3,101,2}},'engineering',{snapshot=s,start=1,target=3})
          assert(r.targetReached and r.plannedTo==3 and r.total==11)
          assert(made(r,7430)==1 and made(r,101)==1)
        """)

    def test_consumed_lower_tool_is_not_duplicated_or_retained_twice(self):
        self.lua.execute("""
          ns.ProfTools.engineering={{spell=7430,item=6219,minSkill=1,bindOnPickup=true},
            {spell=200,item=20,minSkill=2,bindOnPickup=true}}
          local s={recipes={toolRecipe('engineering',7430,6219,1,1,{{1,1}}),
            toolRecipe('engineering',200,20,2,2,{{6219,1},{2,1}}),
            toolRecipe('engineering',101,10,1,300,{{3,1}})},known={},
            prices={[1]=1,[2]=2,[3]=3},professions={engineering={cur=2,max=300}}}
          local r=toolsSolve(s,'engineering',2,3)
          assert(r.targetReached and r.total==6)
          assert(made(r,7430)==1 and made(r,200)==1 and r.inventory[6219]==0 and r.inventory[20]==1)
          assert(r.executionSteps[1].requiredOutputs[6219]==1)
        """)

    def test_purchase_and_step_attribution_include_direct_tool_cost(self):
        self.load(str(fixture.ROOT / "Core/ProfRecovery.lua"))
        self.lua.execute("""
          local s=engineeringTools(3);s.sellPrices={[6219]=999,[10]=0}
          local r=toolsSolve(s,'engineering',100,101,{recoveryFeePercent=0})
          local total=0;for _,step in ipairs(r.steps) do total=total+(step.attributedCost or 0) end
          assert(r.total==4 and total==4 and r.demandNonCraftCost==0)
          assert(r.productNPC==0 and r.recoveryTotal==0)
        """)

    def test_execution_keeps_grey_tool_pending_until_a_real_craft(self):
        self.load(str(fixture.ROOT / "Core/ProfExecution.lua"))
        self.lua.execute("""
          local r=toolsSolve(engineeringTools(20),'engineering',100,101)
          ns.ProfEconomy.Professions=function() return {engineering={cur=101,max=300}} end
          local run,why=ns.ProfExecution.Bind('engineering',r)
          assert(run,tostring(why))
          local p=ns.ProfExecution.Progress('engineering',1)
          assert(not p.complete and p.skillDone and p.remainingCrafts==1)
        """)


if __name__ == '__main__':
    unittest.main()
