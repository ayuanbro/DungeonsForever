"""Lua 5.1 tests for shared route snapshots, HUD progress, and AH exports.

Run with a Python environment containing lupa (a temporary installation in
%TEMP%/df-lua-runtime is also detected). No game files or saved variables change.
"""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.path.join(os.environ.get("TEMP", "/tmp"), "df-lua-runtime"))
if os.environ.get("LOCALAPPDATA"):
    sys.path.insert(0, os.path.join(os.environ["LOCALAPPDATA"], "Temp", "df-lua-runtime"))
sys.path.insert(0, str(Path.home() / "AppData" / "Local" / "Temp" / "df-lua-runtime"))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

STUBS = r'''
local frameMethods = {}
function frameMethods:SetScript(event, fn) self.scripts[event] = fn end
function frameMethods:GetScript(event) return self.scripts[event] end
function frameMethods:Show() self.shown = true end
function frameMethods:Hide() self.shown = false end
function frameMethods:IsShown() return self.shown end
function frameMethods:IsVisible() return self.shown end
function frameMethods:SetShown(shown) self.shown = shown end
function frameMethods:SetText(text) self.text = text end
function frameMethods:GetText() return self.text end
function frameMethods:GetFontString() return self end
function frameMethods:CreateTexture() return makeFrame() end
function frameMethods:CreateFontString() return makeFrame() end
function makeFrame()
  return setmetatable({scripts={}, shown=false}, {__index=function(_, key)
    if frameMethods[key] then return frameMethods[key] end
    if key:match('^[A-Z]') then return function() end end
  end})
end
CreateFrame = function() return makeFrame() end
UIParent = makeFrame()
GameTooltip = makeFrame()
UnitName = function() return 'Test' end
GetRealmName = function() return 'Realm' end
time = function() return 1000 end
strjoin = function(delim, ...) return table.concat({...}, delim) end
bag = {[10]=100, [11]=100, [12]=100}
C_Item = {GetItemCount=function(id) return bag[id] or 0 end}
known = {[101]=true, [102]=true, [201]=true}
C_Spell = {IsSpellKnown=function(id) return known[id] end,
  GetSpellInfo=function(id) return {name='Spell'..id} end}
C_Timer = {After=function(_, fn) fn() end, NewTicker=function() end}
skills = {alchemy={cur=150,max=300}, mining={cur=140,max=300}}
settings = {autoRoute=true, autoScheme='cheapest', autoFromCurrent=false}
currentResult = {planVersion=2,revision=1,feasible=true,steps={},mats={},formulas={}}
lastOptions = nil
local RA = {Available=function() return false end,
  OptionsFor=function(_, start) return {start=start,scheme=settings.autoScheme} end,
  Get=function(_, opts) lastOptions=opts; return currentResult end,
  OnPlanChanged=function(fn) planChanged=fn end}
ns = {LoadForeverPages=true, L=setmetatable({}, {__index=function(_,k) return k end}),
  ProfData={pro={alchemy={name='Alchemy'},mining={name='Mining'}}},
  ProfLeveling={alchemy={steps={{1,300,101,299}}}, mining={steps={{1,300,201,299}}}},
  ProfRecipes={alchemy={rows={{101,20,1,0,0,0,1,100,200,300,false,{{10,2}}}}},
               mining={rows={{201,21,1,0,0,0,1,100,200,300,false,{{11,1}}}}}},
  ProfRouteAuto=RA, PlaySound=function() end}
ns.EnsureProfRecipes=function() return ns.ProfRecipes end
ns.ProfHost={DG={ItemName=function(id) return 'Item'..id,true end,
  RequestItem=function() end, ItemIcon=function() return 0 end},
  MakeFS=function() return makeFrame() end,
  NewButton=function() return makeFrame() end, SetOutline=function() end,
  Unpack=unpack,C_GOLD={1,1,1},C_GREY={1,1,1},C_DIM={1,1,1},C_TEXT={1,1,1}}
ns.ProfModule={SettingRaw=function(key) return settings[key] end,
  Setting=function(key) return settings[key] end,
  ProfLearned=function() return skills end}
DungeonsForeverDB={prof={follow={['Test-Realm']={slug='alchemy',skill=150,step=1,t0=1000}}}}
followState=DungeonsForeverDB.prof.follow['Test-Realm']
GetProfessions=function() return 1,2 end
GetProfessionInfo=function(idx)
  if idx==1 then return 'Alchemy','AlchemyIcon',150,300,0,0,171 end
  return 'Mining','MiningIcon',140,300,0,0,186
end
C_TradeSkillUI={OpenTradeSkill=function(line) openedLine=line end,
  SetSelectedRecipe=function(id) selectedRecipe=id end,
  GetSelectedRecipeID=function() return selectedRecipe end,
  SetRecipeRepeatCount=function(id,n) repeatCount=n end}
StaticPopupDialogs={}
StaticPopup_Show=function() end
DEFAULT_CHAT_FRAME={AddMessage=function() end}
'''


class FollowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUBS)
        loader = self.lua.eval("function(path) assert(loadfile(path))('DungeonsForever',ns) end")
        loader(str(ROOT / "Core" / "AuctionatorBridge.lua"))
        loader(str(ROOT / "Core" / "ProfFollow.lua"))

    def test_vendor_only_plan_does_not_require_auctionator(self):
        self.lua.execute('''
          currentResult.steps={{150,151,101,1,actionID='a1',profession='alchemy'}}
          local mode,steps,res=ns.ProfFollow.GetRoute('alchemy',150)
          assert(mode=='auto' and res==currentResult and #steps==1)
          assert(lastOptions.start==150 and lastOptions.follow==true)
        ''')

    def test_pending_and_infeasible_never_fall_back_to_fixed(self):
        self.lua.execute('''
          currentResult=nil
          local mode,steps=ns.ProfFollow.GetRoute('alchemy',150)
          assert(mode=='auto' and #steps==0)
          currentResult={planVersion=2,revision=1,feasible=false,status='infeasible',steps={}}
          mode,steps=ns.ProfFollow.GetRoute('alchemy',150)
          assert(mode=='auto' and #steps==0)
          currentResult.mats={{id=10,count=3,source='ah'}}
          assert(#ns.ProfFollow.GetPurchases(followState)==0)
          ns.ProfFollow.Build(); ns.ProfFollow.f:Show(); ns.ProfFollow.Sync(); ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.finish.text=='当前限制下没有可行路线')
        ''')

    def test_profession_pair_gate_blocks_hud_and_legacy_route_fallback(self):
        self.lua.execute('''
          ns.ProfRouteAuto.Available=function() return true end
          for _,scheme in ipairs({'cheapest','optim','cost'}) do
            settings.autoScheme=scheme
            for _,status in ipairs({'selection_required','recalculate_required'}) do
              currentResult={planVersion=2,revision=1,feasible=false,status=status,steps={},mats={}}
              local mode,steps,r=ns.ProfFollow.GetRoute('alchemy',150)
              assert(mode=='auto' and #steps==0 and r==currentResult,
                'waiting for a partner fell back to a fixed route')
              assert(#ns.ProfFollow.GetPurchases(followState)==0)
            end
          end
        ''')

    def test_profession_pair_gate_displays_actionable_hud_notice_and_prevents_import(self):
        self.lua.execute('''
          local labels={selection_required='请选择搭配的主专业',
            recalculate_required='搭配专业已更改，点击重新计算应用。'}
          ns.AuctionBridge.DoImport=function() error('blocked route imported purchases') end
          ns.ProfFollow.Build(); ns.ProfFollow.f:Show()
          for status,label in pairs(labels) do
            currentResult={planVersion=2,revision=1,feasible=false,status=status,steps={},mats={}}
            ns.ProfFollow.Sync();ns.ProfFollow.Paint()
            assert(ns.ProfFollow.f.finish.text==label)
            local bt=makeFrame();ns.ProfFollow.PaintImportBtn(bt,'alchemy');bt.scripts.OnClick()
          end
        ''')

    def test_purchases_ignore_owned_materials_and_include_formula_purchases(self):
        self.lua.execute('''
          currentResult.mats={{id=10,count=3,source='ah'}, {id=11,count=4,source='vendor',vendor=true}}
          currentResult.formulas={{id=12,count=1,source='ah'}}
          local p=ns.ProfFollow.GetPurchases(followState)
          assert(#p==3 and p[1].need==3 and p[1].have==nil)
          assert(p[2].source=='vendor' and p[2].need==4)
          assert(p[3].formula and p[3].id==12 and p[3].need==1)
        ''')

    def test_hud_purchases_keep_shared_auction_quantity_snapshot(self):
        self.lua.execute('''
          currentResult.mats={{id=10,count=3,source='ah',availableCount=7,
            supplyObserved=true,supplyComplete=false}}
          currentResult.formulas={{id=12,count=1,source='ah',supplyObserved=false}}
          local p=ns.ProfFollow.GetPurchases(followState)
          assert(#p==2 and p[1].need==3 and p[1].availableCount==7)
          assert(p[1].supplyObserved==true and p[1].supplyComplete==false)
          assert(p[2].formula and p[2].supplyObserved==false and p[2].availableCount==nil)
        ''')

    def test_auction_import_contains_ah_material_and_formula_purchases_only(self):
        self.lua.execute('''
          currentResult.mats={{id=10,count=3,source='ah'}, {id=11,count=4,source='vendor',vendor=true}}
          currentResult.formulas={{id=12,count=1,source='ah'}}
          ns.AuctionBridge.DoImport=function(_,items) imported=items end
          local bt=makeFrame(); ns.ProfFollow.PaintImportBtn(bt,'alchemy'); bt.scripts.OnClick()
          assert(#imported==2 and imported[1].name=='Item10' and imported[1].need==3)
          assert(imported[2].name=='Item12' and imported[2].need==1)
        ''')

    def test_vendor_flag_always_prevents_auction_import(self):
        self.lua.execute('''
          currentResult.mats={{id=10,count=3,source='ah',vendor=true},
            {id=11,count=4,source='npc'}, {id=12,count=2,source='auction'}}
          ns.AuctionBridge.DoImport=function(_,items) imported=items end
          local bt=makeFrame(); ns.ProfFollow.PaintImportBtn(bt,'alchemy'); bt.scripts.OnClick()
          assert(#imported==1 and imported[1].name=='Item12' and imported[1].need==2)
        ''')

    def test_legacy_shopping_quantities_ignore_large_owned_stock(self):
        self.lua.execute('''
          settings.autoRoute=false
          local p=ns.ProfFollow.GetPurchases(followState)
          assert(#p==1 and p[1].need>100 and p[1].have==nil)
          bag[10]=100000
          local q=ns.ProfFollow.GetPurchases(followState)
          assert(q[1].need==p[1].need and q[1].have==nil)
        ''')

    def test_hud_and_shop_render_without_reading_character_inventory(self):
        self.lua.execute('''
          C_Item.GetItemCount=function() error('inventory must not enter route display') end
          currentResult.steps={{150,151,101,1,actionID='a1',profession='alchemy',
            recipe={spell=101,item=20,count=1,mats={{10,2}}}}}
          currentResult.mats={{id=10,count=2,source='ah'}}
          ns.ProfFollow.Build(); ns.ProfFollow.f:Show(); ns.ProfFollow.Sync()
          ns.ProfFollow.showShop=true; ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.shop.head.text=='购物清单 · 共1种')
          assert(ns.ProfFollow.f.shop.missTog==nil and ns.ProfFollow.f.shop.missLab==nil)
        ''')

    def test_unread_client_recipe_shows_refresh_reason_and_does_not_import(self):
        self.lua.execute('''
          currentResult={planVersion=2,revision=1,feasible=false,status='infeasible',steps={},
            diagnostics={{code='clientDataPending'}}}
          ns.AuctionBridge.DoImport=function() didImport=true end
          DEFAULT_CHAT_FRAME.AddMessage=function(_,msg) lastMessage=msg end
          local bt=makeFrame(); ns.ProfFollow.PaintImportBtn(bt,'alchemy'); bt.scripts.OnClick()
          assert(not didImport and lastMessage:find('客户端数据待读取',1,true))
          ns.ProfFollow.Build(); ns.ProfFollow.f:Show(); ns.ProfFollow.Sync(); ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.finish.text=='客户端数据待读取')
        ''')

    def test_material_and_secondary_actions_track_success_counts(self):
        self.lua.execute('''
          currentResult.steps={
            {150,150,101,2,actionID='a1',profession='alchemy',reason='material'},
            {1,2,201,1,actionID='a2',profession='mining',reason='secondary'}}
          ns.ProfFollow.Sync(); assert(followState.step==1)
          ns.ProfFollow.CraftSucceeded('pet','wrong',101); assert(followState.step==1)
          ns.ProfFollow.CraftSucceeded('player','cast1',101); assert(followState.step==1)
          ns.ProfFollow.CraftSucceeded('player','cast1',101); assert(followState.step==1)
          ns.ProfFollow.CraftSucceeded('player','cast2',101); assert(followState.step==2)
          ns.ProfFollow.Sync(); assert(followState.step==2)
          ns.ProfFollow.CraftSucceeded('player','cast3',201); assert(followState.step==3)
        ''')

    def test_new_snapshot_does_not_apply_old_action_counts(self):
        self.lua.execute('''
          currentResult.steps={{150,150,101,2,actionID='a1',profession='alchemy',reason='material'}}
          ns.ProfFollow.Sync(); ns.ProfFollow.CraftSucceeded('player','cast1',101)
          currentResult={planVersion=2,revision=2,feasible=true,
            steps={{150,150,101,1,actionID='a1',profession='alchemy',reason='material'}}}
          ns.ProfFollow.Sync(); assert(followState.step==1)
          ns.ProfFollow.CraftSucceeded('player','cast2',101); assert(followState.step==2)
        ''')

    def test_hud_executes_chronological_steps_after_recipe_rows_are_grouped(self):
        self.lua.execute('''
          currentResult.steps={{150,152,101,2,profession='alchemy'},
            {150,151,201,1,profession='mining'}}
          currentResult.executionSteps={
            {150,151,101,1,actionID='a1',profession='alchemy'},
            {150,151,201,1,actionID='a2',profession='mining'},
            {151,152,101,1,actionID='a3',profession='alchemy'}}
          local mode,steps=ns.ProfFollow.GetRoute('alchemy',150)
          assert(mode=='auto' and steps==currentResult.executionSteps and #steps==3)
          ns.ProfFollow.Sync()
          ns.ProfFollow.CraftSucceeded('player','chron1',101); assert(followState.step==2)
          ns.ProfFollow.CraftSucceeded('player','chron2',201); assert(followState.step==3)
          ns.ProfFollow.CraftSucceeded('player','chron3',101); assert(followState.step==4)
        ''')

    def test_gather_checkpoint_waits_for_actual_mining_skill(self):
        self.lua.execute('''
          currentResult.steps={{140,155,0,0,actionID='g1',profession='mining',checkpoint=true}}
          ns.ProfFollow.Sync(); assert(followState.step==1)
          ns.ProfFollow.CraftSucceeded('player','cast1',0); assert(followState.step==1)
          skills.mining.cur=155; ns.ProfFollow.Sync(); assert(followState.step==2)
        ''')

    def test_craft_button_opens_step_profession_with_skill_line_not_icon(self):
        self.lua.execute('''
          currentResult.steps={{140,140,201,2,actionID='a1',profession='mining',reason='material'}}
          ns.ProfFollow.Sync(); ns.ProfFollow.Build()
          ns.ProfFollow.f.craftBtn.scripts.OnClick()
          assert(openedLine==186 and selectedRecipe==201 and repeatCount==2)
        ''')

    def test_hud_and_craft_button_use_snapshot_inputs_and_output(self):
        self.lua.execute('''
          currentResult.steps={{140,140,201,2,actionID='a1',item=22,profession='mining',reason='material'}}
          currentResult.actions={{id='a1',type='craft',profession='mining',spell=201,
            count=2,item=22,inputs={{14,6}},outputs={{22,4}}}}
          ns.ProfFollow.Sync(); ns.ProfFollow.Build(); ns.ProfFollow.f:Show(); ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.card.__it[1]==22)
          assert(ns.ProfFollow.f.card.__mats[1][1]==14 and ns.ProfFollow.f.card.__mats[1][2]==3)
          ns.ProfFollow.f.craftBtn.scripts.OnClick(); assert(openedLine==nil)
          bag[14]=6; ns.ProfFollow.f.craftBtn.scripts.OnClick(); assert(openedLine==186)
        ''')

    def test_auctionator_export_keeps_exact_quantity(self):
        self.lua.execute('''
          local text=ns.AuctionBridge.ExportString('List',{{name='Copper Ore',need=3}})
          assert(text:find('"Copper Ore"',1,true))
          assert(text:sub(-1)=='3')
        ''')

    def test_hud_does_not_report_full_completion_at_partial_route_end(self):
        self.lua.execute('''
          currentResult.partial=true; currentResult.plannedTo=151; currentResult.target=300
          currentResult.steps={{150,151,101,1,actionID='p1',profession='alchemy'}}
          ns.ProfFollow.Sync(); ns.ProfFollow.Build(); ns.ProfFollow.f:Show()
          ns.ProfFollow.Paint(); assert(ns.ProfFollow.f.card.shown)
          ns.ProfFollow.CraftSucceeded('player','partial1',101)
          ns.ProfFollow.Paint()
          assert(ns.ProfFollow.f.finish.text=='已计算至 151；后续路线待补全')
          assert(not ns.ProfFollow.f.card.shown and not ns.ProfFollow.f.craftBtn.shown)
        ''')


if __name__ == "__main__":
    unittest.main()
