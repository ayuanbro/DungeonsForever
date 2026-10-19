"""Lua 5.1 regressions for merged guide content and BiS selection ownership."""
import os
from pathlib import Path
import sys
import unittest

for runtime in (Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime",
                Path.home() / "AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0, str(runtime))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

MOCKS = r'''
function widget(parent)
    local w = {parent=parent, shown=true, scripts={}}
    return setmetatable(w, {__index=function(t, k)
        if k == 'Show' then return function(s) s.shown=true end end
        if k == 'Hide' then return function(s) s.shown=false end end
        if k == 'SetShown' then return function(s,v) s.shown=v end end
        if k == 'IsShown' then return function(s) return s.shown end end
        if k == 'SetText' then return function(s,v) s.text=v end end
        if k == 'GetText' then return function(s) return s.text or '' end end
        if k == 'GetStringWidth' then return function(s) return #(s.text or '') * 6 end end
        if k == 'GetStringHeight' then return function() return 16 end end
        if k == 'GetWidth' then return function(s) return s.width or 600 end end
        if k == 'GetHeight' then return function(s) return s.height or 400 end end
        if k == 'SetWidth' then return function(s,v) s.width=v end end
        if k == 'SetHeight' then return function(s,v) s.height=v end end
        if k == 'SetSize' then return function(s,a,b) s.width=a; s.height=b end end
        if k == 'GetFrameLevel' then return function() return 1 end end
        if k == 'GetParent' then return function(s) return s.parent end end
        if k == 'GetFontString' then return function(s) s.font=s.font or widget(s); return s.font end end
        if k == 'CreateTexture' or k == 'CreateFontString' then return function(s) return widget(s) end end
        if k == 'SetScript' then return function(s,event,fn) s.scripts[event]=fn end end
        if k == 'HookScript' then return function(s,event,fn)
            local prev=s.scripts[event]
            s.scripts[event]=function(...) if prev then prev(...) end; fn(...) end
        end end
        if type(k)=='string' and string.match(k,'^[A-Z]') then return function() end end
    end})
end
function CreateFrame(_,_,parent) return widget(parent) end
function GetLocale() return 'zhCN' end
function UnitClass() return '德鲁伊','DRUID' end
function UnitFactionGroup() return 'Alliance' end
function UnitLevel() return 30 end
function GetTime() return 1 end
talentTab=2
function GetNumTalents() return 1 end
function GetTalentInfo(tab) return nil,nil,nil,nil,tab==talentTab and 10 or 0 end
function GetItemStats(id)
    if tonumber(id)==1 then return {ITEM_MOD_STRENGTH_SHORT=100} end
    if tonumber(id)==2 then return {ITEM_MOD_SPELL_POWER_SHORT=9} end
    return {ITEM_MOD_STRENGTH_SHORT=1000,ITEM_MOD_SPELL_POWER_SHORT=100}
end
UIParent=widget()
GameTooltip=widget()
function GameTooltip:AddLine(text) self.line=text end
local color={1,1,1}
ns={LoadForeverPages=true,DL=function(s) return s end,
    L=setmetatable({}, {__index=function(_,k) return k end}),
    OpenPerf={Begin=function() end,Mark=function() end},
    PlaySound=function() end}
ns.ProfHost={DG={ItemLink=function(id) return tostring(id) end,
    ItemInfo=function(id) return tostring(id),nil,nil,nil,tonumber(id)==3 and 40 or 20 end},
    MakeFS=function(p) return widget(p) end, NewButton=function(p,text) local w=widget(p); w.text=text; return w end,
    MakeOutline=function() end,SetOutline=function() end,Unpack=unpack,
    C_GOLD=color,C_GREY=color,C_DIM=color,C_WHITE=color,C_TEXT=color,C_GREEN=color,
    PAGE_INSET=8,CONTENT_W=956,FALLBACK_ICON='icon',ROW_CLASS={}}
ns.EnsureBISData=function() return {default=60,classes={{slug='druid',
    specs={{id='pve',slots={}}}}}} end
ns.GearModule={catalog={{id=1,s='Head',c=4,u=1,req=20},
    {id=2,s='Head',c=4,u=1,req=20},{id=3,s='Head',c=4,u=1,req=40}}}
ns.EnsureGearData=function() return {src={[1]='任务奖励|测试',[2]='任务奖励|测试',[3]='任务奖励|测试'}} end
ns.PhasedStart=function(_,co)
    while coroutine.status(co)~='dead' do local ok,err=coroutine.resume(co); assert(ok,err) end
end
ns.ClassTier={meta={patch='1.0',level=60,updated='2026-10-01'},
    pages={{key='dps',tiers={},factors={},notes={}}},
    specs={DRUID={{key='feral',name='野性',icon='icon'}}}}
ns.EnsureClassGuide=function() return {meta={patch='2.0',level=60},
    specs={DRUID={feral={updated='2026-10-19',sections={
        {key='rotation',flow={{t='p',v='原文字循环仍可访问'}}}}}}}} end
function loadModule(path) assert(loadfile(path))('DungeonsForever',ns) end
'''


class MergeGuidesBisTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.globals().loadModule

    def load_bis(self):
        self.load(str(ROOT / "Core/BisUI.lua"))
        self.lua.execute("BG=ns.BisModule; BG.built=true; BG.RequestRender=function() end; BG.ScheduleSweep=function() end")

    def test_manual_generation_uses_filter_while_auto_uses_current_level(self):
        self.load_bis()
        self.lua.execute('''
            BG.filterLv=60; BG.GeneratePlan(); assert(BG.cur.head==3)
            BG.filterLv=20; BG.GeneratePlan(); assert(BG.cur.head==1)
            BG.filterLv=nil; BG.GeneratePlan(); assert(BG.cur.head==3)
            BG.UseAutoPlan('known'); assert(BG.cur.head==1)
        ''')

    def test_talent_change_recomputes_only_active_talent_weighted_auto_plan(self):
        self.load_bis()
        self.lua.execute('''
            BG.UseAutoPlan('known'); assert(BG.cur.head==1)
            talentTab=1; BG.OnTalentChanged(); assert(BG.cur.head==2)
            BG.SetSlot('head',1); assert(BG.autoPlan==nil)
            talentTab=2; BG.OnTalentChanged(); assert(BG.cur.head==1)
            talentTab=1; BG.OnTalentChanged(); assert(BG.cur.head==1)
            BG.UseAutoPlan('all'); BG.wRole='feral'
            local cur=BG.cur; BG.OnTalentChanged(); assert(BG.cur==cur)
            BG.wRole=nil; BG.wActive=1
            BG.OnTalentChanged(); assert(BG.cur==cur)
        ''')

    def test_manual_regeneration_clears_slots_excluded_by_stricter_filters(self):
        self.load_bis()
        self.lua.execute('''
            ns.GearModule.catalog={{id=3,s='Head',c=4,u=1,req=40}}
            ns.EnsureGearData=function() return {src={[3]='商人|测试'}} end
            BG.cur.custom=77
            BG.filterLv=60; BG.GeneratePlan(); assert(BG.cur.head==3)
            BG.filterLv=20; BG.GeneratePlan()
            assert(BG.cur.head==nil,'lowering the level cap must clear the old ineligible item')
            assert(BG.cur.custom==77,'regeneration must retain unrelated state')
            BG.filterLv=60; BG.GeneratePlan(); assert(BG.cur.head==3)
            BG.srcSet={quest=true}; BG.GeneratePlan()
            assert(BG.cur.head==nil,'excluding the old item source must clear the slot')
            assert(BG.cur.custom==77)
        ''')

    def test_auto_cache_uses_weight_revision_without_prior_paint(self):
        self.load_bis()
        self.lua.execute('''
            BG.wSchemes={{w={STRENGTH=1,SPELL_POWER=0}}}; BG.wActive=1
            BG.UseAutoPlan('all'); assert(BG.cur.head==1)
            BG.wSchemes[1].w={STRENGTH=0,SPELL_POWER=1}; BG.wGen=BG.wGen+1
            BG.UseAutoPlan('all'); assert(BG.cur.head==2)
        ''')

    def test_reopen_preserves_manual_saved_preset_and_selected_auto_modes(self):
        self.load_bis()
        self.lua.execute('''
            BG.__wantDefault=true; BG.SetSlot('head',2); BG.Open()
            assert(BG.cur.head==2 and BG.autoPlan==nil)
            BG.GeneratePlan(); BG.Open(); assert(BG.cur.head==3)
            local plan={items={head=2}}; BG.UsePlan(plan); BG.Open()
            assert(BG.usingPlan==plan and next(BG.cur)==nil)
            BG.UsePreset(1); BG.Open(); assert(BG.autoPlan==nil and next(BG.cur)==nil)
            BG.UseAutoPlan('all'); BG.Open(); assert(BG.autoPlan=='all')
            BG.ResetToRec(); BG.Open(); assert(BG.autoPlan==nil and next(BG.cur)==nil)
            BG.__wantDefault=true; BG.Open(); assert(BG.autoPlan=='known')
        ''')

    def test_guide_build_keeps_text_rotation_and_header_metadata_tooltip(self):
        self.load(str(ROOT / "Core/TierUI.lua"))
        self.lua.execute('''
            TT=ns.TierModule
            DungeonsForeverDB={tier={nav='spec',mode='text',cls='DRUID',spec='feral',sec='rotation'}}
            TT.Build(widget())
            assert(TT.curSec=='rotation' and TT.secTabs[1].__secKey=='rotation')
            local found=false
            for _,row in ipairs(TT.rowPool) do if row.text=='原文字循环仍可访问' and row:IsShown() then found=true end end
            assert(found,'the original rotation paragraph was not rendered')
            assert(TT.hero.__metadata=='补丁 2.0 · 等级上限 60 · 已更新 2026-10-19')
            TT.headerTip.scripts.OnEnter(TT.headerTip); assert(GameTooltip.line==TT.hero.__metadata)
            TT.headerTip.scripts.OnLeave(TT.headerTip); assert(not GameTooltip:IsShown())
            assert(TT.headerTip:GetHeight()==20,'tooltip region must stay above the spec buttons')
            assert(table.concat(TT.MODE_KEYS,',')=='rotation,macro,cq,text')
            local seen={}
            ns.ClassCombatUI={RenderRotation=function() TT.PaintHeader(); seen.rotation=true end,
                RenderMacro=function() TT.PaintHeader(); seen.macro=true end,HideRows=function() end,Cull=function() end}
            ns.ClassQuestUI={Render=function() TT.PaintHeader(); seen.cq=true end,Hide=function() end,Cull=function() end}
            for _,mode in ipairs({'rotation','macro','cq'}) do
                DungeonsForeverDB.tier.mode=mode; TT.Render(); assert(seen[mode])
            end
            DungeonsForeverDB.tier.mode='text'; TT.Render(); assert(TT.curSec=='rotation')
            DungeonsForeverDB.tier.nav='rank'; TT.Render()
            local tab=TT.subBtns.dps
            tab.scripts.OnEnter(tab)
            assert(GameTooltip.line=='补丁 1.0 · 等级上限 60 · 已更新 2026-10-01')
        ''')


if __name__ == "__main__":
    unittest.main()
