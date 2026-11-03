"""Profession tools add a one-item obligation without removing leveling recipes.

Synthetic snapshots exercise the real capture, learning, procurement and route
code under Lua 5.1. Recipes are explicitly known and client-available unless a
test checks a blocked recipe; no catalogue, Git reference or live client is used.
"""
import unittest

from test_prof_solver_fusion import LuaRuntime, ROOT


FIXTURE = r'''
ns={LoadForeverPages=true,IsForever=true,L=setmetatable({},{__index=function(_,k)return k end})}
DungeonsForeverDB={prof={}}
time=function()return 1000 end
bag={};C_Item={GetItemCount=function(id)return bag[id] or 0 end}
function CreateFrame()
  local frame={events={}}
  function frame:RegisterEvent(event)self.events[event]=true end
  function frame:SetScript(name,fn)self[name]=fn end
  return frame
end
ns.ProfTools={revision=1,engineering={{spell=7430,item=6219,minSkill=50}}}
function recipe(spell,item,material,grey,profession)
  return {profession=profession or 'engineering',spell=spell,item=item,count=1,
    mats={{material,1}},learn=50,yellow=60,green=60,grey=grey or 50,
    cooldown=false,verified=true,clientAvailable=true}
end
function fixture()
  local tool=recipe(7430,6219,2840)
  local level=recipe(8000,90000,11,300)
  return {recipes={tool,level},prices={[2840]=100,[11]=1,[6219]=2},
    professions={engineering={cur=50,max=300}},
    known={['engineering:7430']=true,['engineering:8000']=true},
    learningSourcesRequired=true,coverageComplete=true,considerAuctionSupply=false,
    faction='A',level=60,stamp=1000}
end
function solve(s,enabled,target)
  local result,job=ns.ProfRouteSolver.Compute('engineering',{
    snapshot=s,start=50,target=target or 51,autoCraftTools=enabled,
    recoveryEnabled=false,cpuLimitMs=1000})
  assert(not job.error,tostring(job.error))
  assert(job.finished,'tool fixture did not finish')
  return result,job
end
function bought(result,item)
  local count=0
  for _,row in ipairs(result.mats)do if row.id==item then count=count+row.count end end
  return count
end
function crafted(result,spell)
  local count=0
  for _,action in ipairs(result.actions)do
    if action.type=='craft' and action.spell==spell then count=count+action.count end
  end
  return count
end
function executionCrafts(result,spell)
  local count=0
  for _,step in ipairs(result.executionSteps)do
    if step[3]==spell then count=count+step[4] end
  end
  return count
end
'''


class ProfessionToolPolicyTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        load = self.lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for name in (
            "ProfRouteAuto", "ProfPolicies", "ProfGates", "ProfEssences",
            "ProfSolverCapture", "ProfLearning", "ProfRecovery", "ProfRouteSolver",
        ):
            load((ROOT / "Core" / (name + ".lua")).read_text(encoding="utf-8-sig"))

    def test_disabled_keeps_a_cheap_tool_recipe_for_repeated_leveling(self):
        self.lua.execute('''
          local s=fixture();s.recipes[1].grey=60;s.prices[2840]=2;s.prices[11]=100
          local r,j=solve(s,false,53)
          assert(r.targetReached and r.total==6)
          assert(j.snap.autoCraftTools==false and #j.snap.toolGoals==0)
          assert(crafted(r,7430)==3 and executionCrafts(r,7430)==3,
            'disabling tool preparation removed an ordinary leveling candidate')
          assert(bought(r,6219)==0 and next(r.retainedToolItems)==nil)
        ''')

    def test_disabled_does_not_force_an_expensive_tool_or_purchase(self):
        self.lua.execute('''
          local s=fixture();s.recipes[1].grey=60
          local r,j=solve(s,false)
          assert(r.targetReached and r.total==1 and crafted(r,8000)==1)
          assert(#j.snap.toolGoals==0 and next(r.retainedToolItems)==nil)
          assert(crafted(r,7430)==0 and executionCrafts(r,7430)==0 and bought(r,6219)==0)
        ''')

    def test_enabled_prepares_one_of_each_required_missing_tool(self):
        self.lua.execute('''
          ns.ProfTools.engineering[2]={spell=8001,item=70000,minSkill=50}
          local s=fixture();s.recipes[3]=recipe(8001,70000,12)
          s.known['engineering:8001']=true;s.prices[12]=100;s.prices[70000]=3
          local r,j=solve(s,true)
          assert(r.targetReached and #j.snap.toolGoals==2 and r.total==6)
          for _,goal in ipairs(j.snap.toolGoals)do
            assert(r.completedToolGoals[goal.id] and r.retainedToolItems[goal.item]==1)
            assert(r.inventory[goal.item]>=1 and bought(r,goal.item)==1)
          end
          assert(crafted(r,7430)==0 and crafted(r,8001)==0)
        ''')

    def test_enabled_does_not_prepare_an_already_owned_tool_again(self):
        self.lua.execute('''
          for _,legacy in ipairs({false,true})do
            if legacy then
              C_Item=nil;GetItemCount=function(id)return bag[id] or 0 end
            end
            bag[6219]=1
            local r,j=solve(fixture(),true)
            assert(r.targetReached and r.total==1 and #j.snap.toolGoals==0)
            assert(j.snap.ownedToolItems[6219] and crafted(r,7430)==0)
            assert(executionCrafts(r,7430)==0 and bought(r,6219)==0)
          end
        ''')

    def test_cheaper_tradeable_tool_is_a_shopping_item_without_a_craft_step(self):
        self.lua.execute('''
          local r,j=solve(fixture(),true)
          assert(r.targetReached and r.total==3 and #j.snap.toolGoals==1)
          assert(bought(r,6219)==1 and crafted(r,7430)==0 and executionCrafts(r,7430)==0)
          local found=false
          for _,row in ipairs(r.mats)do if row.id==6219 then
            assert(row.tool and row.source=='ah' and row.count==1 and row.cost==2)
            found=true
          end end
          assert(found,'the selected tool purchase was absent from the shopping list')
        ''')

    def test_cheaper_tool_crafting_enters_the_execution_steps(self):
        self.lua.execute('''
          local s=fixture();s.prices[2840]=2;s.prices[6219]=10
          local r=solve(s,true)
          assert(r.targetReached and r.total==3 and bought(r,6219)==0)
          assert(crafted(r,7430)==1 and executionCrafts(r,7430)==1 and r.inventory[6219]==1)
          local found=false
          for _,step in ipairs(r.executionSteps)do if step[3]==7430 then
            assert(step.tool and step.toolItem==6219 and step.requiredOutputs[6219]==1)
            found=true
          end end
          assert(found,'selected tool crafting was absent from execution')
        ''')

    def test_bind_on_pickup_tool_is_crafted_despite_a_cheaper_auction_quote(self):
        self.lua.execute('''
          ns.ProfTools.engineering[1].bindOnPickup=true
          local s=fixture();s.prices[6219]=1
          local r,j=solve(s,true)
          assert(r.targetReached and r.total==101)
          assert(j.snap.nonAuctionable[6219] and j.snap.toolCraftOnlyItems[6219])
          assert(bought(r,6219)==0 and crafted(r,7430)==1 and executionCrafts(r,7430)==1)
          for _,step in ipairs(r.executionSteps)do if step[3]==7430 then
            assert(step.tool and step.toolBop and step.requiredOutputs[6219]==1)
          end end
        ''')

    def test_auction_quantity_cannot_replace_an_uncraftable_bind_on_pickup_tool(self):
        self.lua.execute('''
          ns.ProfTools.engineering[1].bindOnPickup=true
          local s=fixture();s.considerAuctionSupply=true
          s.auctionSupply={
            [6219]={quantity=999,complete=true,source='fixture'},
            [2840]={quantity=0,complete=true,source='fixture'},
            [11]={quantity=999,complete=true,source='fixture'}}
          local r=solve(s,true)
          assert(not r.feasible and not r.targetReached,
            'auction stock satisfied a bound tool whose crafting materials were unavailable')
          assert(bought(r,6219)==0 and crafted(r,7430)==0 and executionCrafts(r,7430)==0)
        ''')

    def test_tool_goal_preserves_client_learning_and_own_profession_checks(self):
        self.lua.execute('''
          ns.ProfTools.engineering[1].bindOnPickup=true
          for _,blocked in ipairs({'client','learning','foreign'})do
            local s=fixture()
            if blocked=='learning' then
              s.known['engineering:7430']=nil
            else
              s.recipes[1].clientUnavailable=true
            end
            if blocked=='foreign' then
              s.recipes[3]=recipe(8002,6219,12,50,'mining')
              s.professions.mining={cur=300,max=300}
              s.known['mining:8002']=true;s.prices[12]=1
            end
            local r=solve(s,true)
            assert(not r.feasible and not r.targetReached,blocked)
            assert(crafted(r,7430)==0 and crafted(r,8002)==0 and bought(r,6219)==0,blocked)
          end
        ''')


if __name__ == "__main__":
    unittest.main()
