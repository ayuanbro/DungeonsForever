"""Tests real ProfRouteSolver.RebatchChronological under Lua 5.1.

Uses the existing native solver test fixture and bypasses unrelated game/UI logic.
Run: python3.12 -m unittest discover -s validation -p 'test_prof_rebatch.py' -v
"""
import unittest
from test_prof_solver_fusion import ProfessionSolverFusionTests


class RecipeRebatchTests(unittest.TestCase):
    # Reuse existing source loading, without inheriting unrelated solver test cases.
    setUp = ProfessionSolverFusionTests.setUp

    def test_replays_reduce_switches_without_changing_stock(self):
        self.lua.execute(r'''
          local S=ns.ProfRouteSolver
          local function craft(name, inputs, output)
            return {type='craft',profession='alchemy',spell=name,
                    inputs=inputs or {},item=output}
          end
          local function buy(item,count)
            return {type='buy',item=item,count=count}
          end
          local function state(list)
            local stock={};local chain=nil
            for _,a in ipairs(list) do
              if a.type=='buy' then stock[a.item]=(stock[a.item] or 0)+a.count
              elseif a.type=='craft' then
                for _,m in ipairs(a.inputs) do
                  if (stock[m[1]] or 0)<m[2] then return nil end
                  stock[m[1]]=stock[m[1]]-m[2]
                end
                if a.item then stock[a.item]=(stock[a.item] or 0)+1 end
              end
              chain={action=a,prev=chain}
            end
            return {log=chain,inv=stock,money=123,skill={alchemy=50},
              cap={alchemy=300},progress={alchemy=0},produced={},ahUsed={}}
          end
          local function order(s)
            local a={}; local node=s.log
            while node do
              if node.action.type=='craft' then
                table.insert(a,1,node.action.spell)
              end
              node=node.prev
            end
            return table.concat(a,',')
          end
          local old=assert(state({buy(11,1),craft(1,{{11,1}}),craft(2),buy(11,1),craft(1,{{11,1}})}))
          local improved=S.RebatchChronological(old,state)
          assert(order(old)=='1,2,1')
          assert(order(improved)=='1,1,2',order(improved))
          assert(improved.money==old.money and improved.skill.alchemy==old.skill.alchemy)
          assert(improved.inv[11]==old.inv[11])
          local dependent=assert(state({buy(11,1),craft(1,{{11,1}},17),
            craft(2,{{17,1}},11),craft(1,{{11,1}})}))
          assert(order(S.RebatchChronological(dependent,state))=='1,2,1')
        ''')

    def test_protected_residual_and_switch_free_single_recipe(self):
        self.lua.execute(r'''
          local S=ns.ProfRouteSolver
          local function simulate(seq)
            local inv={};local log=nil;local xp=1
            for _,a in ipairs(seq) do
              if a.type=='craft' then
                -- The only profitable sequence is A,B,A in this fixture.
                if a.spell==1 then if xp<3 then xp=xp+1 end
                elseif a.spell==2 and xp==2 then xp=xp+2 end
              end
              log={prev=log,action=a}
            end
            return {log=log,inv=inv,skill={alchemy=xp},cap={alchemy=300},
                    money=0,progress={},produced={},formulaPaid={}}
          end
          local A={type='craft',profession='alchemy',spell=1}
          local B={type='craft',profession='alchemy',spell=2}
          local orig=simulate({A,B,A})
          local reb=S.RebatchChronological(orig,simulate)
          assert(reb.skill.alchemy==orig.skill.alchemy)
          local list={}; local p=reb.log
          while p do table.insert(list,1,p.action.spell); p=p.prev end
          assert(table.concat(list,',')=='1,2,1')
          local same=simulate({A,A})
          assert(S.RebatchChronological(same,simulate)==same)
        ''')
