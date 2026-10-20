"""Independent integer-cost and dependency fixtures for the Lua 5.1 solver."""
import itertools
import heapq
import os
from pathlib import Path
import sys
import unittest

for path in (
    Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime",
    Path.home() / "AppData" / "Local" / "Temp" / "df-lua-runtime",
):
    sys.path.insert(0, str(path))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

FIXTURES = r'''
ns={LoadForeverPages=true}
time=function() return 1000 end
function recipe(prof,spell,item,count,mats,learn,grey)
  return {profession=prof,spell=spell,item=item,count=count,mats=mats,
    learn=learn or 1,yellow=100,green=200,grey=grey or 300,cooldown=false}
end
function snapshot(recipes,prices,inventory)
  local s={recipes=recipes or {},prices=prices or {},inventory=inventory or {},
    professions={alchemy={cur=1,max=300},mining={cur=300,max=300}},known={}}
  for _,r in ipairs(s.recipes) do s.known[r.profession..':'..r.spell]=true end
  return s
end
function countCrafts(res,spell)
  local n=0; for _,a in ipairs(res.actions) do if a.type=='craft' and a.spell==spell then n=n+a.count end end
  return n
end
'''


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURES)
        load = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        load(str(ROOT / "Core" / "ProfEconomy.lua"))
        load(str(ROOT / "Core" / "ProfRouteSolver.lua"))

    def test_user_integer_hybrid_cost_is_twelve(self):
        self.lua.execute('''
          local s=snapshot({recipe('mining',101,10,2,{{11,1}},1,1)}, {[10]=5,[11]=7})
          local r=ns.ProfRouteSolver.Procure(s,10,3)
          assert(r.feasible and r.costComplete and r.total==12, tostring(r.total))
          assert(countCrafts(r,101)==1)
        ''')

    def test_actual_engineering_prices_buy_tubes_and_level_only_with_scopes(self):
        # Client-observed recipe quantities and saved prices from 2026-10-17.
        # This deliberately supplies abundant old stock: it must be ignored.
        self.lua.execute('''
          local tube=recipe('engineering',3924,4361,1,{{2840,2},{2880,1}},50,110)
          tube.yellow=80; tube.green=95
          local scope=recipe('engineering',3977,4405,1,{{4361,1},{774,1},{4359,1}},60,120)
          scope.yellow=90; scope.green=105
          local bolt=recipe('engineering',3922,4359,1,{{2840,1}},30,60)
          bolt.yellow=45; bolt.green=52
          local s=snapshot({tube,scope,bolt},
            {[2840]=275,[4361]=159,[774]=15,[4359]=430,[4405]=1000},
            {[2840]=999,[4361]=999,[774]=999,[4359]=999,[2880]=999})
          s.professions={engineering={cur=60,max=75}}
          s.offers={[2880]={{unlimited=true,price=90,quantity=1,npcID=5512}}}
          local r,j=ns.ProfRouteSolver.Compute('engineering',{snapshot=s,start=60,target=75})
          assert(not j.error and r.feasible and r.targetReached and r.optimal)
          assert(r.total==6735,'expected 15*(159+15+275), got '..tostring(r.total))
          assert(countCrafts(r,3924)==0 and countCrafts(r,3977)==15 and countCrafts(r,3922)==15)
          local bought={}; for _,m in ipairs(r.mats) do bought[m.id]=m.count end
          assert(bought[4361]==15 and bought[774]==15 and bought[2840]==15)
          assert(not bought[2880] and not bought[4359])
          local seen={}
          for _,step in ipairs(r.steps) do
            local key=step.profession..':'..step[3]
            assert(not seen[key],'duplicate recipe row '..key); seen[key]=true
          end
          assert(#r.steps==2 and r.total==r.matTotal and r.matTotal==r.ahTotal+r.vendorTotal)
          assert(#r.executionSteps>=2)
          local segments={};for _,step in ipairs(r.executionSteps) do assert(not segments[step.segmentID]);segments[step.segmentID]=true end
          assert(r.steps[1][3]==3922 and r.steps[1].role=='material' and r.steps[1].cost==4125)
          assert(r.steps[2][3]==3977 and r.steps[2].role=='level' and r.steps[2].cost==2610)
          assert(r.searchComplete and not r.budgetLimited and r.expanded<1000)
          assert(r.initialTotal==9060 and r.savings==2325 and r.improvements>=1)
        ''')

    def test_verified_vendor_material_uses_npc_pack_price_and_no_auction_purchase(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,10,1,{{11,1}},1,10)},{[11]=1})
          s.vendorItems={[11]=true}; s.vendorSuppliers={[11]={{npcID=1313}}}
          s.offers={[11]={{unlimited=true,price=18,quantity=2,npcID=1313}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(r.feasible and r.total==36 and r.vendorTotal==36 and r.ahTotal==0)
          assert(#r.mats==1 and r.mats[1].source=='vendor' and r.mats[1].npcID==1313 and r.mats[1].count==4)
          for _,a in ipairs(r.actions) do if a.type=='buy' then assert(a.source=='vendor') end end
        ''')

    def test_unknown_vendor_price_without_own_source_excludes_recipe_and_never_uses_auction_price(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,10,1,{{11,1}},1,10)},{[11]=999})
          s.vendorItems={[11]=true}; s.vendorSuppliers={[11]={{npcID=1313}}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(not r.feasible and not r.costComplete and not r.optimal)
          assert(#r.steps==0 and #r.mats==0 and not r.pricePending)
          for _,a in ipairs(r.actions) do assert(a.type~='buy') end
        ''')

    def test_verified_vendor_reference_is_priced_and_keeps_quote_provenance(self):
        self.lua.execute('''
          local s=snapshot({recipe('alchemy',101,10,1,{{11,1}},1,10)},{[11]=1})
          s.vendorItems={[11]=true}; s.vendorSuppliers={[11]={{npcID=1313}}}
          s.offers={[11]={{unlimited=true,price=18,quantity=5,npcID=1313,
            source='wowhead-forever',priceBasis='wowhead-reference',reference=true,
            estimated=true,verifiedAt='2026-10-18',url='https://example.test/npc=1313'}}}
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(not j.error and r.feasible and r.costComplete and r.total==18)
          assert(r.vendorTotal==18 and r.ahTotal==0 and r.referencePrices)
          assert(#r.diagnostics==0 and #r.mats==1)
          local m=r.mats[1]
          assert(m.vendor and m.source=='vendor' and m.reference and m.estimated and not m.unpriced)
          assert(m.quoteSource=='wowhead-forever' and m.priceBasis=='wowhead-reference')
          assert(m.npcID==1313 and m.count==5 and m.bundleSize==5 and m.verifiedAt=='2026-10-18')
          assert(m.url=='https://example.test/npc=1313' and m.unit==18/5)
          local cash=0
          for _,a in ipairs(r.actions) do if a.type=='buy' then
            assert(a.source=='vendor' and a.reference and a.quoteSource=='wowhead-forever')
            cash=cash+a.cost
          end end
          local stepCost=0; for _,step in ipairs(r.steps) do stepCost=stepCost+step.cost end
          assert(cash==18 and stepCost==18)
        ''')

    def test_unqualified_vendor_estimate_still_marks_cost_incomplete(self):
        self.lua.execute('''
          local s=snapshot({}, {})
          s.vendorItems={[11]=true}; s.vendorSuppliers={[11]={{npcID=1313}}}
          s.offers={[11]={{unlimited=true,price=18,quantity=5,npcID=1313,
            source='auctionator-vendor',estimated=true}}}
          local r=ns.ProfRouteSolver.Procure(s,11,3)
          assert(r.feasible and r.total==18 and not r.costComplete and not r.referencePrices)
          assert(r.mats[1].estimated and not r.mats[1].reference)
          local found=false
          for _,d in ipairs(r.diagnostics) do if d.code=='vendorEstimate' then found=true end end
          assert(found)
        ''')

    def test_level_and_material_recipe_preserves_chronological_segments(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,2); a.yellow=2; a.green=2
          local b=recipe('alchemy',102,12,1,{{10,1}},2,3); b.yellow=3; b.green=3
          local c=recipe('alchemy',103,14,1,{{10,1},{12,1}},3,4); c.yellow=4; c.green=4
          local s=snapshot({a,b,c},{[11]=4})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4})
          assert(r.feasible and r.targetReached and r.total==8)
          assert(#r.steps==3 and #r.executionSteps==4)
          assert(r.steps[1][3]==101 and r.steps[1][4]==2 and r.steps[1].role=='both')
          assert(r.steps[1][1]==1 and r.steps[1][2]==3)
          local expected={101,102,101,103}
          for i,spell in ipairs(expected) do assert(r.executionSteps[i][3]==spell) end
          local inv={}; local seen={}
          for _,a in ipairs(r.actions) do
            for _,dependency in ipairs(a.dependencies or {}) do assert(seen[dependency]) end
            for _,m in ipairs(a.inputs or {}) do
              assert((inv[m[1]] or 0)>=m[2],'action consumes unproduced material')
              inv[m[1]]=inv[m[1]]-m[2]
            end
            if a.type=='buy' then inv[a.item]=(inv[a.item] or 0)+a.count end
            for _,m in ipairs(a.outputs or {}) do inv[m[1]]=(inv[m[1]] or 0)+m[2] end
            seen[a.id]=true
          end
        ''')

    def test_small_route_search_matches_independent_inventory_dijkstra(self):
        # Oracle actions explicitly manufacture the grey two-output intermediate,
        # manufacture a levelling intermediate, or consume/buy them to level.
        # It shares neither the Lua procurement recursion nor its search bound.
        def oracle(target, raw_price, tube_price, part_price, extra_price):
            first = (1, 0, 0)
            queue = [(0, first)]
            best = {first: 0}
            cap = target + 1
            while queue:
                cost, state = heapq.heappop(queue)
                if best[state] != cost:
                    continue
                skill, tubes, parts = state
                if skill >= target:
                    return cost
                options = []
                if tubes < cap:
                    options.append((2 * raw_price, (skill + 1, tubes + 1, parts)))
                # A scope buys exactly the deficit and consumes retained output.
                options.append((extra_price + (0 if tubes else tube_price)
                                + (0 if parts else part_price),
                                (skill + 1, max(0, tubes - 1), max(0, parts - 1))))
                if parts + 2 <= cap:
                    options.append((3 * raw_price, (skill, tubes, parts + 2)))
                for spent, nxt in options:
                    total = cost + spent
                    if total < best.get(nxt, float('inf')):
                        best[nxt] = total
                        heapq.heappush(queue, (total, nxt))
            raise AssertionError('finite oracle unexpectedly found no route')

        solve = self.lua.eval('''function(target,raw,tubePrice,partPrice,extra)
          local a=recipe('alchemy',101,10,1,{{11,2}})
          local b=recipe('alchemy',102,12,1,{{10,1},{14,1},{13,1}})
          local c=recipe('mining',103,14,2,{{11,3}},1,1)
          local s=snapshot({a,b,c},{[11]=raw,[10]=tubePrice,[14]=partPrice,[13]=extra})
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=target})
          assert(r.feasible and r.costComplete and not j.error)
          return r.total,r.optimal
        end''')
        for target, raw, tube, part, extra in itertools.product(
                (3, 5), (1, 3), (2, 7), (2, 6), (1, 4)):
            expected = oracle(target, raw, tube, part, extra)
            total, optimal = solve(target, raw, tube, part, extra)
            self.assertEqual(total, expected, (target, raw, tube, part, extra))
            self.assertTrue(optimal)

    def test_missing_client_smelting_data_does_not_turn_into_free_mining(self):
        self.lua.execute('''
          local copper=recipe('mining',101,10,1,{{11,1}},1,70)
          copper.clientPending=true
          local s=snapshot({copper},{[2901]=2,[11]=1})
          s.professions.mining={cur=1,max=300}
          local r=ns.ProfRouteSolver.Compute('mining',{snapshot=s,start=1,target=65})
          assert(not r.feasible and r.status=='incomplete')
          for _,a in ipairs(r.actions) do assert(a.type~='gather') end
        ''')

    def test_removed_rank_requirements_do_not_block_material_budget(self):
        self.lua.execute('''
          local s=snapshot({}, {}, {[2901]=1})
          s.professions.mining={cur=225,max=225}; s.level=30
          s.rankCosts={mining={[300]=17}}; s.rankRequirements={mining={[300]={level=35}}}
          local r=ns.ProfRouteSolver.Compute('mining',{snapshot=s,start=225,target=300})
          assert(r.feasible and r.total==0 and r.finalSkills.mining==300)
          for _,a in ipairs(r.actions) do assert(a.type~='buy' and a.type~='train') end
        ''')

    def test_mining_checkpoint_has_no_tool_purchase_or_rank_charge(self):
        self.lua.execute('''
          local s=snapshot({}, {[2901]=10})
          s.professions.mining={cur=185,max=225}; s.rankCosts={mining={[300]=17}}
          local r=ns.ProfRouteSolver.Compute('mining',{snapshot=s,start=185,target=300})
          assert(r.feasible and r.costComplete and r.total==0)
          assert(r.finalSkills.mining==300 and #r.mats==0)
          for _,a in ipairs(r.actions) do assert(a.type=='gather') end
          assert(r.toolsTotal==nil and r.trainingTotal==nil and r.formulasTotal==0)
          assert(r.total==r.ahTotal+r.vendorTotal and r.matTotal==r.total)
        ''')

    def test_exhaustive_single_producer_small_integer_cases(self):
        # Enumerate every possible make/buy split independently of the solver.
        solve = self.lua.eval('''function(need,output,craftCost,buyCost,owned)
          local s=snapshot({recipe('mining',101,10,output,{{11,1}},1,1)},
            {[10]=buyCost,[11]=craftCost},{[10]=owned})
          local r,j=ns.ProfRouteSolver.Procure(s,10,need)
          assert(r.feasible and r.costComplete and not j.error)
          return r.total,r.optimal
        end''')
        for need, output, craft_cost, buy_cost, owned in itertools.product(
            range(1, 6), (1, 2, 3), (2, 7), (3, 5), (0, 1)
        ):
            # Initial bags/bank have no effect; only this plan's outputs are reused.
            missing = need
            expected = min(
                n * craft_cost + max(0, missing - n * output) * buy_cost
                for n in range(missing + 1)
            )
            got, optimal = solve(need, output, craft_cost, buy_cost, owned)
            self.assertEqual(got, expected, (need, output, craft_cost, buy_cost, owned))
            self.assertTrue(optimal)

    def test_multi_level_producers_and_batch_leftovers(self):
        self.lua.execute('''
          local s=snapshot({recipe('mining',101,10,2,{{11,2}},1,1),
            recipe('alchemy',102,12,1,{{10,1},{13,1}},1,1)},
            {[10]=20,[11]=3,[12]=50,[13]=2})
          local r=ns.ProfRouteSolver.Procure(s,12,2)
          assert(r.feasible and r.total==10,tostring(r.total))
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==2)
          assert((r.inventory[10] or 0)==0)
        ''')

    def test_route_outputs_feed_later_recipes_without_repurchase(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,2,{{11,1}},1,2)
          a.yellow=2; a.green=2
          local b=recipe('alchemy',102,12,1,{{10,2}},2,3)
          b.yellow=3; b.green=3
          local s=snapshot({a,b},{[11]=4,[10]=20})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3})
          assert(r.feasible and r.total==4,tostring(r.total))
          assert(countCrafts(r,101)==1 and countCrafts(r,102)==1)
          assert(#r.mats==1 and r.mats[1].id==11 and r.mats[1].count==1)
          assert((r.inventory[10] or 0)==0)
        ''')

    def test_nested_reagents_cannot_consume_stock_reserved_for_parent(self):
        self.lua.execute('''
          local a=recipe('mining',101,12,1,{{10,1}},1,1)
          local b=recipe('alchemy',102,13,1,{{10,1},{12,1}},1,1)
          local s=snapshot({a,b},{[10]=5,[12]=20,[13]=100},{[10]=1})
          local r=ns.ProfRouteSolver.Procure(s,13,1)
          assert(r.feasible and r.total==10,tostring(r.total))
          assert(#r.mats==1 and r.mats[1].id==10 and r.mats[1].count==2)
          for id,n in pairs(r.inventory) do assert(n>=0,'negative inventory '..id) end
        ''')

    def test_ban_producer_keeps_buying_its_output_available(self):
        self.lua.execute('''
          local s=snapshot({recipe('mining',101,10,2,{{11,1}},1,1)}, {[10]=5,[11]=1})
          local r=ns.ProfRouteSolver.Procure(s,10,3,{exclusions={['mining:101']='ban'}})
          assert(r.feasible and r.total==15 and countCrafts(r,101)==0)
        ''')

    def test_soft_exclusion_allows_material_but_not_level_target(self):
        self.lua.execute('''
          local s=snapshot({recipe('mining',101,10,2,{{11,1}},1,301)}, {[10]=5,[11]=1})
          local policy={['mining:101']='level'}
          local r=ns.ProfRouteSolver.Procure(s,10,3,{exclusions=policy})
          assert(r.feasible and r.total==2 and countCrafts(r,101)==2)
          s.professions.mining.cur=1
          r=ns.ProfRouteSolver.Compute('mining',{snapshot=s,start=1,target=2,exclusions=policy})
          assert(countCrafts(r,101)==0)
        ''')

    def test_cooldown_and_output_conflict_never_craft(self):
        self.lua.execute('''
          for _,flag in ipairs({'cooldown','cooldownUnknown','outputConflict'}) do
            local a=recipe('mining',101,10,2,{{11,1}},1,1); a[flag]=true
            local s=snapshot({a},{[10]=5,[11]=1})
            local r=ns.ProfRouteSolver.Procure(s,10,3)
            assert(r.feasible and r.total==15 and countCrafts(r,101)==0,flag)
          end
        ''')

    def test_other_profession_uses_current_skill_and_optional_material_only_upgrade(self):
        self.lua.execute('''
          local low=recipe('mining',100,20,1,{{11,1}},1,2); low.yellow=2; low.green=2
          local high=recipe('mining',101,10,2,{{12,1}},2,2)
          local s=snapshot({low,high},{[10]=10,[11]=2,[12]=1})
          s.professions.mining.cur=1
          local r=ns.ProfRouteSolver.Procure(s,10,2)
          assert(r.total==20 and countCrafts(r,101)==0)
          r=ns.ProfRouteSolver.Procure(s,10,2,{allowSecondaryLeveling=true})
          assert(r.total==3 and countCrafts(r,100)==1 and countCrafts(r,101)==1,tostring(r.total))
          assert(r.finalSkills.mining==2)
        ''')

    def test_formula_cost_is_once_and_trainer_cost_is_removed(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}}); a.formula=12; a.trainingCost=3
          local s=snapshot({a},{[11]=1,[12]=10}); s.known={}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3})
          assert(r.feasible and r.costComplete and r.total==12,tostring(r.total))
          assert(r.formulasTotal==10 and r.trainingTotal==nil and r.matTotal==2)
          assert(#r.formulas==1 and r.formulas[1].id==12)
          for _,a in ipairs(r.actions) do
            assert(a.type~='learn' and a.type~='train')
          end
        ''')

    def test_tools_and_rank_training_do_not_enter_material_plan(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}}); a.tools={12}
          local s=snapshot({a},{[11]=1,[12]=8})
          s.professions.alchemy={cur=75,max=75}; s.rankCosts={alchemy={[150]=20}}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=75,target=77})
          assert(r.feasible and r.costComplete and r.total==2,tostring(r.total))
          assert(r.trainingTotal==nil and r.toolsTotal==nil and r.inventory[12]==nil)
          assert(countCrafts(r,101)==2)
        ''')

    def test_initial_owned_tool_is_ignored_and_never_enters_result_inventory(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}}); a.tools={12}; a.formula=13
          local s=snapshot({a},{[11]=1,[12]=8,[13]=50},{[12]=1})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3})
          assert(r.feasible and r.total==2 and r.formulasTotal==0 and r.toolsTotal==nil)
          assert(r.inventory[12]==nil)
        ''')

    def test_initial_stock_cannot_unlock_an_unpriced_material(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,2); a.yellow=2; a.green=2
          local b=recipe('alchemy',102,12,1,{{10,1},{11,1}},2,3); b.yellow=3; b.green=3
          local alternative=recipe('alchemy',103,10,1,{{13,1}},1,2); alternative.yellow=2; alternative.green=2
          local s=snapshot({a,b,alternative},{[13]=4},{[11]=1})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=3})
          assert(not r.targetReached and not r.optimal and r.plannedTo==2)
          assert(countCrafts(r,101)==0 and countCrafts(r,103)==1 and countCrafts(r,102)==0)
          for _,m in ipairs(r.mats) do assert(m.id~=11 and not m.unpriced) end
          assert((r.inventory[11] or 0)==0)
        ''')

    def test_self_dependency_without_bootstrap_has_no_free_solution(self):
        self.lua.execute('''
          local a=recipe('mining',101,10,2,{{12,1}},1,1)
          local b=recipe('alchemy',102,12,1,{{10,1}},1,1)
          local s=snapshot({a,b},{})
          local r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(not r.feasible and not r.optimal)
        ''')

    def test_missing_tool_price_does_not_block_material_plan(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}}); a.tools={12}
          local s=snapshot({a},{[11]=1})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.feasible and r.costComplete and r.total==1 and r.optimal)
          assert(#r.mats==1 and r.mats[1].id==11)
        ''')

    def test_missing_material_price_is_not_free(self):
        self.lua.execute('''
          local s=snapshot({}, {})
          local r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(not r.feasible and not r.costComplete and not r.optimal)
          local a=recipe('alchemy',101,10,1,{{11,1}})
          s=snapshot({a},{[11]=1}); s.known={}
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.feasible and r.costComplete and r.total==1 and r.optimal)
        ''')

    def test_missing_auction_quote_at_leaf_excludes_recipe_instead_of_publishing_reference_cost(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1},{12,1}},1,10)
          local s=snapshot({a},{[12]=7})
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=4,maxNodes=1})
          assert(not r.targetReached and #r.steps==0 and not r.feasible)
          assert(not r.pricePending and not r.referenceRoute and not r.optimal)
          assert(#r.mats==0 and #r.actions==0,'failed candidate left purchases in final route')
        ''')

    def test_unpriced_reference_never_displaces_a_fully_priced_route(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,10)
          local b=recipe('alchemy',102,12,1,{{13,1}},1,10)
          local s=snapshot({a,b},{[13]=7});s.coverageComplete=false
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.feasible and r.costComplete and r.total==7 and not r.pricePending)
          assert(countCrafts(r,101)==0 and countCrafts(r,102)==1)
        ''')

    def test_reference_route_respects_exclusions_and_known_nontradable_materials(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,10)
          local s=snapshot({a},{});s.nonAuctionable={[11]=true}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(#r.steps==0 and not r.feasible,'bound material was assumed buyable')
          s.nonAuctionable={}
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2,exclusions={['alchemy:101']='ban'}})
          assert(#r.steps==0 and not r.feasible,'reference fallback bypassed exclusion')
        ''')

    def test_client_confirmation_and_catalogue_sources_allow_new_recipe_without_formula_fee(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,10)
          a.isNew=true;a.availabilityUnknown=true;a.verified=false;a.clientAvailable=true
          local s=snapshot({a},{[11]=7});s.known={}
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.feasible and r.total==7 and r.targetReached)
          a.clientUnavailable=true
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(not r.feasible and #r.steps==0)
          a.clientUnavailable=nil;a.clientAvailable=nil
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(not r.feasible and #r.steps==0)
          a.availabilityUnknown=nil;a.verified=nil;a.catalogue=true
          r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.feasible and r.total==7)
        ''')

    def test_first_executable_prefix_is_published_before_recursive_optimization(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,1,{{11,1}},1,2);a.yellow=2;a.green=2
          local s=snapshot({a},{[11]=7})
          local j=ns.ProfRouteSolver.NewJob('alchemy',{snapshot=s,start=1,target=3,referenceFallback=false})
          for i=1,100 do
            ns.ProfRouteSolver.Run(j,2)
            if j.result and #j.result.steps>0 then break end
          end
          assert(not j.error and j.result and #j.result.steps==1)
          assert(j.result.partial and j.result.plannedTo==2 and j.expanded==0)
          assert(j.result.steps[1][3]==101 and j.result.steps[1][4]==1)
        ''')

    def test_variable_output_uses_guaranteed_minimum_for_dependency_batches(self):
        self.lua.execute('''
          local a=recipe('alchemy',101,10,2,{{11,1}},1,10)
          a.outputMin=2;a.outputMax=4;a.variableOutput=true;a.outputBasis='minimum'
          local s=snapshot({a},{[11]=7})
          local r=ns.ProfRouteSolver.Procure(s,10,5)
          assert(r.feasible and r.costComplete and r.total==21 and countCrafts(r,101)==3)
          assert(r.inventory[10]==1,'unearned random output was consumed or sold')
          assert(r.steps[1].recipe.outputMin==2 and r.steps[1].recipe.outputMax==4)
        ''')

    def test_vendor_packages_can_mix_with_ah_and_limited_stock_is_ignored(self):
        self.lua.execute('''
          local s=snapshot({}, {[10]=5})
          s.offers={[10]={{unlimited=false,price=1,quantity=3,npcID=1},
            {unlimited=true,price=7,quantity=2,npcID=2}}}
          local r=ns.ProfRouteSolver.Procure(s,10,3)
          assert(r.feasible and r.total==12,tostring(r.total))
          assert(#r.mats==2)
          for _,e in ipairs(r.mats) do assert(e.npcID~=1) end
        ''')

    def test_wrong_faction_extended_currency_and_unverified_vendor_are_ignored(self):
        self.lua.execute('''
          local s=snapshot({}, {[10]=5}); s.faction='Alliance'
          s.offers={[10]={{unlimited=true,price=1,quantity=1,faction='Horde'},
            {unlimited=true,price=1,quantity=1,hasExtendedCost=true},
            {price=1,quantity=1},
            {unlimited=true,price=1,quantity=1,purchasable=false}}}
          local r=ns.ProfRouteSolver.Procure(s,10,3)
          assert(r.feasible and r.total==15 and r.vendorTotal==0)
        ''')

    def test_station_requirements_are_outside_material_budget(self):
        self.lua.execute('''
          local a=recipe('mining',101,10,1,{{11,1}},1,1); a.station='moltenFoundry'
          local s=snapshot({a},{[11]=2})
          local r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(r.feasible and r.costComplete and r.total==2 and r.optimal)
          assert(#r.diagnostics==0)
          s.stations={moltenFoundry=true}
          r=ns.ProfRouteSolver.Procure(s,10,1)
          assert(r.feasible and r.costComplete and r.total==2)
        ''')

    def test_grey_smelting_is_material_source_but_does_not_level_mining(self):
        self.lua.execute('''
          local a=recipe('mining',101,10,1,{{11,1}},140,140)
          local s=snapshot({a},{[11]=2,[2901]=3}); s.professions.mining.cur=140
          local r=ns.ProfRouteSolver.Compute('mining',{snapshot=s,start=140,target=155})
          assert(r.feasible and countCrafts(r,101)==0)
          assert(#r.steps==1 and r.steps[1].checkpoint and r.steps[1][1]==140 and r.steps[1][2]==155)
          assert(r.total==0)
        ''')

    def test_live_recipe_output_and_reagents_override_conflicted_seed(self):
        self.lua.execute('''
          ns.ProfRecipeMeta={[101]={outputConflict=true}}
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,2,3,4,false,{{11,1}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          ns.ProfRecipeKeys={'alchemy'}
          GetProfessions=function() return 1 end
          GetProfessionInfo=function() return 'Alchemy','Icon',1,300,0,0,171 end
          C_Item={GetItemCount=function() return 0 end}
          C_TradeSkillUI={GetAllRecipeIDs=function() return {101} end,
            GetRecipeInfo=function() return {learned=true} end,
            GetRecipeNumItemsProduced=function() return 2,2 end,
            GetRecipeItemLink=function() return 'item:14' end,
            GetRecipeNumReagents=function() return 1 end,
            GetRecipeReagentItemLink=function() return 'item:11' end,
            GetRecipeReagentInfo=function() return 'Ore',nil,3 end}
          ns.ProfEconomy.ScanRecipes()
          local s=ns.ProfEconomy.Capture('alchemy',{start=1})
          assert(s.byKey['alchemy:101'].count==2)
          assert(s.byKey['alchemy:101'].item==14)
          assert(not s.byKey['alchemy:101'].outputConflict)
          assert(s.byKey['alchemy:101'].mats[1][2]==3)
        ''')

    def test_unread_client_data_uses_known_material_fallback(self):
        self.lua.execute('''
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,2,3,4,false,{{11,1}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          GetProfessions=function() return 1 end
          GetProfessionInfo=function() return 'Alchemy','Icon',1,300,0,0,171 end
          C_Item={GetItemCount=function() return 0 end}
          C_Spell={IsSpellKnown=function() return true end}
          ns.ProfRouteAuto={AHPriceOf=function() return 1 end}
          local s=ns.ProfEconomy.Capture('alchemy',{start=1})
          assert(not s.byKey['alchemy:101'].clientPending)
          assert(s.byKey['alchemy:101'].materialSource=='catalogue')
          local r=ns.ProfRouteSolver.Compute('alchemy',{snapshot=s,start=1,target=2})
          assert(r.feasible and r.total==1 and not r.optimal)
        ''')

    def test_partial_client_reagent_loading_keeps_known_material_fallback(self):
        self.lua.execute('''
          ns.ProfRecipes={alchemy={rows={{101,10,1,'','','',1,2,3,4,false,{{11,1}}}}}}
          ns.EnsureProfRecipes=function() return ns.ProfRecipes end
          GetProfessions=function() return 1 end
          GetProfessionInfo=function() return 'Alchemy','Icon',1,300,0,0,171 end
          C_Item={GetItemCount=function() return 0 end}
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeNumItemsProduced=function() return 2,2 end,
            GetRecipeItemLink=function() return 'item:14' end,
            GetRecipeNumReagents=function() return 1 end,
            GetRecipeReagentItemLink=function() return nil end,
            GetRecipeReagentInfo=function() return 'Ore',nil,3 end}
          ns.ProfEconomy.ScanRecipes()
          local s=ns.ProfEconomy.Capture('alchemy',{start=1})
          assert(not s.byKey['alchemy:101'].clientPending)
          assert(s.byKey['alchemy:101'].mats[1][1]==11 and s.byKey['alchemy:101'].mats[1][2]==1)
          assert(s.byKey['alchemy:101'].item==14 and s.byKey['alchemy:101'].count==2)
          assert(ns.ProfRecipeRuntime[101].mats==nil)
        ''')

    def test_linked_profession_cannot_replace_own_recipe_observation(self):
        self.lua.execute('''
          C_TradeSkillUI={GetRecipeInfo=function() return {learned=true} end,
            GetRecipeNumItemsProduced=function() return 2,2 end,
            GetRecipeItemLink=function() return 'item:14' end,
            GetRecipeNumReagents=function() return 1 end,
            GetRecipeReagentItemLink=function() return 'item:11' end,
            GetRecipeReagentInfo=function() return 'Ore',nil,3 end}
          ns.ProfEconomy.ReadRecipe(101)
          assert(ns.ProfRecipeRuntime[101].count==2 and ns.ProfRecipeRuntime[101].learned)
          C_TradeSkillUI.IsTradeSkillLinked=function() return true end
          C_TradeSkillUI.GetRecipeInfo=function() return {learned=false} end
          C_TradeSkillUI.GetRecipeNumItemsProduced=function() return 9,9 end
          ns.ProfEconomy.ReadRecipe(101)
          assert(ns.ProfRecipeRuntime[101].count==2 and ns.ProfRecipeRuntime[101].learned)
        ''')


if __name__ == "__main__":
    unittest.main()
