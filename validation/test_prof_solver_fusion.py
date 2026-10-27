"""Lua 5.1 regression fixtures for the route solver merged into dev.

Run with the bundled Python and a Lua 5.1 capable lupa on PYTHONPATH, or use
the existing .pipeline-runtime/lib runtime. No WoW client or catalogue module
is required; synthetic inputs exercise the actual Core implementation.
"""
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (
    ROOT / ".pipeline-runtime" / "lib",
    Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime-py312",
):
    if directory.is_dir():
        sys.path.insert(0, str(directory))
from lupa.lua51 import LuaRuntime


FIXTURE = r'''
ns={LoadForeverPages=true,L=setmetatable({},{__index=function(_,k)return k end})}
DungeonsForeverDB={prof={}}
time=function() return 1000 end
function recipe(prof,spell,item,count,mats,learn,grey)
  return {profession=prof,spell=spell,item=item,count=count,mats=mats,
    learn=learn or 1,yellow=100,green=200,grey=grey or 300,cooldown=false}
end
function snapshot(recipes,prices)
  local s={recipes=recipes or {},prices=prices or {},inventory={},
    professions={alchemy={cur=1,max=300},mining={cur=300,max=300}},known={}}
  for _,r in ipairs(s.recipes) do s.known[r.profession..':'..r.spell]=true end
  return s
end
function solve(slug,s,target,opts)
  opts=opts or {}; opts.snapshot=s; opts.start=opts.start or 1;opts.target=target
  if opts.recoveryEnabled==nil then opts.recoveryEnabled=false end
  local r,j=ns.ProfRouteSolver.Compute(slug,opts)
  assert(not j.error,tostring(j.error));return r,j
end
function bought(r,id)
  local n=0;for _,m in ipairs(r.mats)do if m.id==id then n=n+m.count end end;return n
end
function countCrafts(r,spell)
  local n=0;for _,a in ipairs(r.actions)do if a.type=='craft'and a.spell==spell then n=n+a.count end end;return n
end
function conversions(r)
  local rows={};for _,s in ipairs(r.executionSteps)do if s.kind=='essence_conversion'then rows[#rows+1]=s end end;return rows
end
function essenceSnapshot(mats,prices,lSupply,gSupply)
  local r=recipe('enchanting',1,nil,1,mats,1,300)
  local s=snapshot({r},prices);s.professions={enchanting={cur=1,max=300}}
  s.essenceConversions=true;s.auctionSupply={}
  if lSupply then s.auctionSupply[10938]={quantity=lSupply,complete=true,source='observed'} end
  if gSupply then s.auctionSupply[10939]={quantity=gSupply,complete=true,source='observed'} end
  return s
end
'''


class ProfessionSolverFusionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        load = self.lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for name in ("ProfPolicies", "ProfEssences", "ProfGates", "ProfSolverCapture", "ProfRecovery", "ProfRouteSolver"):
            load((ROOT / "Core" / (name + ".lua")).read_text(encoding="utf-8-sig"))

    def test_integer_pack_and_recursive_craft_purchase_compete(self):
        self.lua.execute(r'''
          local s=snapshot({recipe('mining',101,10,2,{{11,1}},1,1)},{[10]=5,[11]=7})
          local r,j=ns.ProfRouteSolver.Procure(s,10,3,{recoveryEnabled=false})
          assert(not j.error,tostring(j.error))
          assert(r.feasible and r.total==12,tostring(r.total))
          assert(countCrafts(r,101)==1 and bought(r,10)==1 and bought(r,11)==1)
          r,j=ns.ProfRouteSolver.Procure(s,10,3)
          assert(not j.error and r.total==12,'optional procurement settings must remain optional')
        ''')

    def test_integer_procurement_matches_independent_make_buy_enumeration(self):
        self.lua.execute(r'''
          for need=1,5 do for output=1,3 do
            for _,craftPrice in ipairs({2,7})do for _,buyPrice in ipairs({3,5})do
              local expected=math.huge
              for crafts=0,need do
                expected=math.min(expected,crafts*craftPrice+math.max(0,need-crafts*output)*buyPrice)
              end
              local s=snapshot({recipe('mining',101,10,output,{{11,1}},1,1)},
                {[10]=buyPrice,[11]=craftPrice})
              local r,j=ns.ProfRouteSolver.Procure(s,10,need,{recoveryEnabled=false})
              assert(not j.error and r.feasible and r.costComplete)
              assert(r.total==expected,table.concat({need,output,craftPrice,buyPrice,r.total,expected},':'))
            end end
          end end
        ''')

    def test_split_competes_with_direct_purchase_and_carries_surplus(self):
        self.lua.execute(r'''
          local r=solve('enchanting',essenceSnapshot({{10938,4}},{[10938]=4,[10939]=10}),2)
          assert(r.feasible and r.total==14,tostring(r.total))
          assert(bought(r,10938)==1 and bought(r,10939)==1 and #conversions(r)==1)
          assert(r.crafts==1 and conversions(r)[1].expectedGain==0)
          local s=essenceSnapshot({{10938,1}},{[10938]=8,[10939]=10})
          local r=solve('enchanting',s,3)
          assert(r.total==10 and r.inventory[10938]==1 and r.crafts==2)
          assert(conversions(r)[1].requiredOutputs[10938]==2)
        ''')

    def test_combine_obeys_shared_finite_auction_budget(self):
        self.lua.execute(r'''
          local s=essenceSnapshot({{10939,1},{10938,1}},{[10938]=2,[10939]=50},4,0)
          local r=solve('enchanting',s,2)
          assert(r.feasible and r.total==8 and bought(r,10938)==4 and bought(r,10939)==0)
          s.auctionSupply[10938].quantity=3
          r=solve('enchanting',s,2)
          assert(not r.feasible,'the same lesser essence must not be consumed twice')
        ''')

    def test_missing_alternative_quote_limits_optimality(self):
        self.lua.execute(r'''
          local s=essenceSnapshot({{10938,2}},{[10938]=4})
          local r=solve('enchanting',s,2)
          assert(r.feasible and r.costComplete and r.total==8 and r.essenceQuoteIncomplete)
          assert(not r.inputModelOptimal and not r.quoteComplete)
          s.auctionSupply[10939]={quantity=0,source='observed',complete=true}
          r=solve('enchanting',s,2)
          assert(r.feasible and not r.essenceQuoteIncomplete and r.quoteComplete)
        ''')

    def test_only_verified_execution_stock_can_offset_purchase(self):
        self.lua.execute(r'''
          local s=essenceSnapshot({{10938,2}},{[10938]=4,[10939]=10})
          s.inventory={[10938]=999,[10939]=999}
          local r=solve('enchanting',s,2)
          assert(r.total==8 and bought(r,10938)==2)
          r=solve('enchanting',s,2,{executionInventory={[10939]=1}})
          assert(r.total==0 and #r.mats==0 and r.inventory[10938]==1)
          assert(#conversions(r)==1 and #r.seedAllocations==1)
        ''')

    def test_solver_honors_requested_budget_and_reports_frontier_limit(self):
        self.lua.execute(r'''
          local s=snapshot({recipe('alchemy',1,10,1,{{11,1}})},{[11]=1})
          local j=ns.ProfRouteSolver.NewJob('alchemy',{snapshot=s,start=1,target=2,cpuLimitMs=8000})
          assert(j.cpuLimitMs==8000 and j.frontierLimit==20000)
          s=snapshot({recipe('alchemy',1,10,1,{{11,1}}),recipe('alchemy',2,20,1,{{12,1}})},
            {[11]=1,[12]=2})
          s.recovery={revision=1,enabled=true,feePercent=0,feeSource='manual',quotes={
            [10]={unit=1,npcUnit=1,source='npc'},[20]={unit=1,npcUnit=1,source='npc'}}}
          local r,j=solve('alchemy',s,5,{maxFrontier=1,recoveryEnabled=true})
          assert(j.frontierLimit==1 and r.searchFrontierLimit==1)
          assert(r.searchModel=='fractional_skill_accumulation')
          assert(r.searchTermination=='frontier_limit' and r.budgetLimited)
          assert(r.targetReached and not r.inputModelOptimal and not r.optimal)
        ''')

    def test_cpu_cutoff_finalizes_incumbent_in_cooperative_slices(self):
        self.lua.execute(r'''
          local now=0;debugprofilestop=function()now=now+.01;return now end
          local s=snapshot({recipe('alchemy',1,10,1,{{11,1}}),
            recipe('alchemy',2,20,1,{{11,2}})},{[11]=1})
          local S=ns.ProfRouteSolver
          local j=S.NewJob('alchemy',{snapshot=s,start=1,target=5,recoveryEnabled=false,cpuLimitMs=8000})
          local turns=0
          while not j.best and not j.finished do S.Run(j,.05);turns=turns+1;assert(turns<10000)end
          assert(j.best and not j.error)
          j.cpuUsed=j.cpuLimitMs
          while not S.Run(j,.05)do turns=turns+1;assert(turns<10000)end
          assert(j.result and j.result.feasible and j.result.targetReached and not j.error)
          assert(j.result.searchTermination=='cpu_limit' and j.result.budgetLimited)
          assert(not j.result.inputModelOptimal and #j.result.actions>0)
        ''')

    def test_recovery_threshold_and_unknown_fee_are_conservative(self):
        self.lua.execute(r'''
          local function capture(netPrice,quantity,fee)
            local s=snapshot({recipe('alchemy',1,10,1,{{11,1}})},{[10]=netPrice})
            s.sellPrices={[10]=10}
            s.auctionSupply={[10]={quantity=quantity,complete=true,ownerExcluded=true,
              source='client-auction-results',observedAt=999}}
            local r=ns.ProfRecovery.Capture(s,{recoveryEnabled=true,recoveryFeePercent=fee})
            return r.quotes[10],r
          end
          local q=capture(111,40,0);assert(q.source=='ah' and q.unit==111)
          q=capture(110,40,0);assert(q.source=='npc' and q.unit==10)
          q=capture(111,39,0);assert(q.source=='npc')
          local fee,source=ns.ProfRecovery.Fee({},{})
          assert(fee==nil and source=='unknown')
          q=capture(111,40,nil);assert(q.source=='npc')
        ''')

    def test_recovery_can_choose_higher_cash_for_lower_final_net_cost(self):
        self.lua.execute(r'''
          local s=snapshot({recipe('alchemy',101,10,1,{{1,1}}),recipe('alchemy',102,20,1,{{2,1}})},
            {[1]=1,[2]=30})
          s.recovery={revision=1,enabled=true,feePercent=0,feeSource='manual',quotes={
            [10]={unit=0,npcUnit=0,source='npc'},[20]={unit=100,npcUnit=100,source='npc'}}}
          local r=solve('alchemy',s,3,{recoveryEnabled=true})
          assert(r.total==60 and r.recoveryTotal==200 and r.netTotal==-140)
          assert(countCrafts(r,102)==2 and r.targetReached and r.searchComplete)
        ''')


if __name__ == "__main__":
    unittest.main()
