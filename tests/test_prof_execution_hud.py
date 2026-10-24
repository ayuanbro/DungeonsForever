"""Shared persistent execution service through the real HUD, using Lua 5.1.

These tests exercise event ownership, button scripts and published snapshots;
they do not claim live Forever client event or mouse hit-testing validation.
"""
from pathlib import Path
import unittest

from test_prof_follow import LuaRuntime, ROOT, STUBS


EXECUTION_STUBS = r'''
local originalMakeFrame=makeFrame
function makeFrame()
  local f=originalMakeFrame()
  f.points={};f.level=1
  function f:SetPoint(...) self.points[#self.points+1]={...};self.point={...} end
  function f:ClearAllPoints() self.points={};self.point=nil end
  function f:SetFrameLevel(n) self.level=n end
  function f:GetFrameLevel() return self.level end
  function f:SetWidth(w) self.width=w end
  function f:SetHeight(h) self.height=h end
  function f:SetSize(w,h) self.width=w;self.height=h end
  return f
end
CreateFrame=function(_,_,parent) local f=makeFrame();f.parent=parent;return f end
ns.ProfHost.NewButton=function(parent,text,w,h)
  local f=makeFrame();f.parent=parent;f.text=text;f.width=w;f.height=h;f:Show();return f
end
ns.ProfEconomy={Professions=function() return skills end,
  Gain=function(rec,skill) if skill>=(rec.grey or 300) then return 0 end;return 1 end}
function makeStep(from,to,spell,count,opts)
  opts=opts or {};local item=spell==201 and 21 or 20
  local prof=spell==201 and 'mining' or 'alchemy'
  local s={from,to,spell,count,segmentID=opts.id or ('s'..spell),profession=prof,
    expectedCrafts=count,attemptLimit=count,expectedGain=opts.gain or (to-from),
    goalSkill=opts.goal or to,item=item,outputMin=opts.minimum or 1,outputMax=opts.maximum or 1,
    requiredOutputs=opts.required or {},materialMinCrafts=opts.materialCasts or 0,
    allocations={},recipe={spell=spell,item=item,count=opts.minimum or 1,
      outputMin=opts.minimum or 1,outputMax=opts.maximum or 1,
      mats={{10,2}},learn=1,yellow=100,green=200,grey=300}}
  s.role=next(s.requiredOutputs) and ((s.expectedGain or 0)>0 and 'both' or 'material') or 'level'
  return s
end
function setPlan(segments)
  currentResult={planVersion=2,executionVersion=1,revision=1,feasible=true,status='complete',
    steps=segments,executionSteps=segments,mats={{id=10,count=10,source='ah'}},formulas={},total=100}
end
function event(eventName,...)
  local f=ns.ProfExecution.eventFrame
  f.scripts.OnEvent(f,eventName,...)
end
function savedLiteral(v)
  if type(v)=='table' then
    local out={'{'}
    for k,x in pairs(v) do out[#out+1]='['..savedLiteral(k)..']='..savedLiteral(x)..',' end
    out[#out+1]='}';return table.concat(out)
  end
  if type(v)=='string' then return string.format('%q',v) end
  if type(v)=='number' or type(v)=='boolean' then return tostring(v) end
  return 'nil'
end
'''


class ExecutionHUDTests(unittest.TestCase):
    def make_runtime(self, saved=None):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(STUBS)
        lua.execute(EXECUTION_STUBS)
        if saved:
            lua.execute("DungeonsForeverDB=" + saved)
            lua.execute("followState=DungeonsForeverDB.prof.follow['Test-Realm']")
        loader = lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        loader(str(ROOT / "Core" / "AuctionatorBridge.lua"))
        loader(str(ROOT / "Core" / "ProfExecution.lua"))
        loader(str(ROOT / "Core" / "ProfFollow.lua"))
        return lua

    def setUp(self):
        self.lua = self.make_runtime()

    def test_skill_progress_is_actual_while_material_quota_stays_independent(self):
        self.lua.execute(r'''
          skills.alchemy.cur=60;followState.skill=60
          setPlan({makeStep(60,75,101,15)})
          ns.ProfFollow.Sync();skills.alchemy.cur=62;ns.ProfFollow.Sync()
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.card.crafts.text=='预计还需13次 · 已制作0次')
          assert(followState.step==1)
        ''')

    def test_skill_met_does_not_skip_49_of_60_material_quota(self):
        self.lua.execute(r'''
          skills.alchemy.cur=1;followState.skill=1
          setPlan({makeStep(1,60,101,60,{required={[20]=60},materialCasts=60})})
          ns.ProfFollow.Sync()
          for i=1,49 do
            event('UNIT_SPELLCAST_SUCCEEDED','player','quota'..i,101)
            event('TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=20,quantity=1,castGUID='quota'..i})
          end
          skills.alchemy.cur=60;ns.ProfFollow.Sync()
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          assert(followState.step==1)
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.casts==49 and p.confirmedOutputs==49 and p.remainingCrafts==11)
          assert(ns.ProfFollow.f.card.progress[1].text=='技能已达标，仍需为后续准备材料。')
          assert(ns.ProfFollow.f.card.progress[3].text=='需60份，已确认49份，还需11份。')
        ''')

    def test_random_actual_outputs_allow_early_completion_and_deduplicate_sources(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,150,101,5,{gain=0,required={[20]=5},materialCasts=5,maximum=3})})
          ns.ProfFollow.Sync()
          event('UNIT_SPELLCAST_SUCCEEDED','player','output1',101)
          event('TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=20,quantity=2,castGUID='output1',eventID='r1'})
          event('UNIT_SPELLCAST_SUCCEEDED','player','output2',101)
          event('TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=20,quantity=3,castGUID='output2',eventID='r2'})
          event('TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=20,quantity=3,castGUID='output2',eventID='r2'})
          ns.ProfExecution.RecordOutput({itemID=20,quantity=2,castGUID='output1'},'chat')
          ns.ProfFollow.Sync()
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.casts==2 and p.confirmedOutputs==5 and p.complete)
          assert(followState.step==2)
        ''')

    def test_counts_keep_growing_above_estimate_and_hidden_hud_never_owns_events(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,153,101,2)})
          ns.ProfFollow.Sync()
          assert(ns.ProfFollow.f==nil)
          for i=1,4 do event('UNIT_SPELLCAST_SUCCEEDED','player','overrun'..i,101) end
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.casts==4 and p.pendingOutputs==4 and not p.complete)
          ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.card.crafts.text=='预计还需3次 · 已制作4次')
          assert(ns.ProfFollow.f.card.progress[2].text=='最低保证4份；4次制作的产出待确认。')
          -- Even a duplicate cast delivered to the visible HUD has one owner.
          ns.ProfFollow.f.scripts.OnEvent(ns.ProfFollow.f,'UNIT_SPELLCAST_SUCCEEDED','player','overrun4',101)
          assert(ns.ProfExecution.Progress('alchemy',1).casts==4)
          ns.ProfFollow.f:Hide()
          event('UNIT_SPELLCAST_SUCCEEDED','player','overrun5',101)
          assert(ns.ProfExecution.Progress('alchemy',1).casts==5)
        ''')

    def test_saved_execution_restores_in_fresh_runtime_without_reusing_new_revision(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,150,101,5,{gain=0,required={[20]=5},materialCasts=5})})
          ns.ProfFollow.Sync();event('UNIT_SPELLCAST_SUCCEEDED','player','persist1',101)
          event('TRADE_SKILL_ITEM_CRAFTED_RESULT',{itemID=20,quantity=2,castGUID='persist1'})
          ns.ProfFollow.Sync()
          savedPlanID=ns.ProfExecution.GetRun('alchemy').planID
        ''')
        plan_id = self.lua.eval("savedPlanID")
        saved = self.lua.eval("savedLiteral(DungeonsForeverDB)")
        restored = self.make_runtime(saved)
        restored.execute(r'''
          setPlan({makeStep(150,151,101,1)})
          currentResult.revision=999
          ns.ProfFollow.Sync()
          assert(ns.ProfExecution.Progress('alchemy',1).casts==1)
          assert(ns.ProfExecution.Progress('alchemy',1).confirmedOutputs==2)
          assert(#ns.ProfExecution.GetPlan('alchemy').executionSteps==1)
          assert(ns.ProfExecution.GetPlan('alchemy').executionSteps[1][4]==5)
          ns.ProfFollow.Toggle('mining')
          ns.ProfFollow.Toggle('alchemy')
          assert(ns.ProfExecution.Progress('alchemy',1).casts==1)
        ''')
        self.assertEqual(restored.eval("ns.ProfExecution.GetRun('alchemy').planID"), plan_id)

    def test_return_button_synchronizes_before_clearing_browse_and_is_outside_card(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,151,101,1,{id='one'}),makeStep(151,152,102,1,{id='two'})})
          ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show()
          ns.ProfFollow.Skip();ns.ProfFollow.showShop=true;ns.ProfFollow.Paint()
          local f=ns.ProfFollow.f
          assert(f.nowBtn.parent==f.controls and f.controls.parent==f)
          assert(f.controls.level>f.card.level and f.nowBtn.point[2]==f.controls)
          skills.alchemy.cur=151
          f.nowBtn.scripts.OnClick()
          assert(followState.step==2 and ns.ProfFollow.view==0)
          assert(f.card.name.text=='Spell102')
          assert(ns.ProfExecution.Progress('alchemy',1).casts==0)
        ''')

    def test_manual_output_verification_uses_cumulative_quantity(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,150,101,10,{gain=0,required={[20]=10},materialCasts=10,maximum=3})})
          ns.ProfFollow.Sync()
          event('UNIT_SPELLCAST_SUCCEEDED','player','verify1',101)
          assert(not ns.ProfFollow.VerifyCurrentOutput(-1))
          assert(not ns.ProfFollow.VerifyCurrentOutput(1.5))
          assert(ns.ProfFollow.VerifyCurrentOutput(7))
          local p=ns.ProfExecution.Progress('alchemy',1)
          assert(p.casts==1 and p.confirmedOutputs==7 and p.remainingOutputs==3)
        ''')

    def test_stale_supply_result_asks_for_recalculation(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,152,101,2)})
          ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show()
          ns.ProfExecution.GetRun('alchemy').supplement={feasible=false,stale=true,status='stale',total=0}
          ns.ProfFollow.showShop=true;ns.ProfFollow.shopKind='supplement';ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.shop.summary.text=='进度已变化，请重新计算补料')
        ''')

    def test_old_v2_route_preserves_legacy_counts_and_requires_manual_recalculation(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,150,101,5,{gain=0,required={[20]=5},materialCasts=5})})
          currentResult.executionVersion=nil;followState.actionDone={old=3}
          ns.ProfFollow.Sync();ns.ProfFollow.Build();ns.ProfFollow.f:Show();ns.ProfFollow.Paint()
          assert(followState.actionDone.old==3)
          assert(ns.ProfFollow.f.finish.text=='旧路线缺少执行信息，请重新计算后继续跟随。')
          assert(ns.ProfExecution.GetRun('alchemy')==nil)
        ''')

    def test_fixed_route_uses_the_same_durable_recorder(self):
        self.lua.execute(r'''
          settings.autoRoute=false
          ns.ProfEconomy.FindRecipe=function()return makeStep(1,300,101,299).recipe end
          ns.ProfFollow.Sync()
          assert(ns.ProfExecution.GetRun('alchemy'))
          event('UNIT_SPELLCAST_SUCCEEDED','player','fixed-craft',101)
          assert(ns.ProfExecution.Progress('alchemy',1).casts==1)
        ''')

    def test_switching_back_to_an_existing_profession_restores_event_ownership(self):
        self.lua.execute(r'''
          setPlan({makeStep(150,152,101,2)})
          ns.ProfFollow.Sync();local original=ns.ProfExecution.GetRun('alchemy')
          local other={executionVersion=1,planVersion=2,feasible=true,status='complete',executionSteps={makeStep(140,141,201,1)}}
          ns.ProfExecution.Bind('mining',other)
          ns.ProfFollow.Sync();event('UNIT_SPELLCAST_SUCCEEDED','player','back-again',101)
          assert(original.attemptsDone==1 and ns.ProfExecution.GetRun('mining').attemptsDone==0)
        ''')


if __name__ == "__main__":
    unittest.main()
