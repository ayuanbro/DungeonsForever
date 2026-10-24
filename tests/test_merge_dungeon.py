"""Exercise merged dungeon behavior against the real Lua 5.1 functions."""
import os
from pathlib import Path
import sys
import unittest

for path in (Path(os.environ.get("TEMP", "/tmp")) / "df-lua-runtime",
             Path.home() / "AppData/Local/Temp/df-lua-runtime"):
    sys.path.insert(0, str(path))
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
DUNGEON = (ROOT / "Core/DungeonUI.lua").read_text(encoding="utf-8-sig")
MAP = (ROOT / "Core/MapUI.lua").read_text(encoding="utf-8-sig")

FIXTURE = r'''
  methods={}
  function widget()
    return setmetatable({scripts={},shown=false,w=0,h=0,text=''}, {__index=function(_,k)
      if methods[k] then return methods[k] end
      if k:match('^[A-Z]') then return function() end end
    end})
  end
  function methods:SetScript(k,fn) self.scripts[k]=fn end
  function methods:RegisterEvent(k) end
  function methods:SetPoint(...) self.point={...} end
  function methods:ClearAllPoints() self.point=nil end
  function methods:SetSize(w,h) self.w=w;self.h=h end
  function methods:SetWidth(w) self.w=w end
  function methods:GetWidth() return self.w end
  function methods:GetFrameLevel() return 1 end
  function methods:GetFontString() return self end
  function methods:CreateTexture() return widget() end
  function methods:CreateFontString() return widget() end
  function methods:SetText(t) self.text=t end
  function methods:GetStringWidth()
    local width=0
    for ch in self.text:gmatch('[%z\1-\127\194-\244][\128-\191]*') do
      width=width+((#ch==1) and 7 or 14)
    end
    return width
  end
  function methods:Show() self.shown=true end
  function methods:Hide() self.shown=false end
  function methods:SetShown(on) self.shown=on end
  function methods:IsShown() return self.shown end
  function methods:SetChecked(on) self.checked=on end
  function methods:GetChecked() return self.checked end
  function methods:IsMouseOver() return false end
  function NewButton(_,text,w,h)
    local f=widget();f:SetText(text);f:SetSize(w,h);return f
  end
  function MakeFS() return widget() end
  function MakeOutline() end
  function SetOutline(bt,on) bt.selected=on end
  C_GOLD={1,.82,0};C_GREY={.5,.5,.5};C_TEXT={1,1,1};Unpack=unpack
  format=string.format;UIParent=widget();GameTooltip=widget()
  L=setmetatable({}, {__index=function(_,k)return k end})
  ns={L=L,PlaySound=function()end};DG={};U={};M={};store={}
  DungeonsForeverDB={dungeon=store};function DB() return store end
  now=1;timers={};flushed={};apiNames={};apiQualities={};tipNames={};tipCalls=0
  function GetTime() return now end
  function debugprofilestop() return now*1000 end
  function GetItemInfo(id) return apiNames[id],nil,apiQualities[id],999 end
  function GetItemQualityColor(q) lastQuality=q;return .2,.4,.6 end
  C_Item={RequestLoadItemDataByID=function()end}
  C_Timer={After=function(_,fn)timers[#timers+1]=fn end,
    NewTimer=function(_,fn)timers[#timers+1]=fn;return {} end}
  function runTimers()
    local pending=timers;timers={}
    for _,fn in ipairs(pending) do fn() end
  end
  function CreateFrame(kind)
    local f=widget()
    if kind=='GameTooltip' then
      function f:SetHyperlink(link)
        tipCalls=tipCalls+1;tipItem=tonumber(link:match('item:(%d+)'))
        if failTooltip then error('tooltip unavailable') end
        if onLink then onLink() end
      end
      function f:NumLines() return tipNames[tipItem] and 1 or 0 end
    end
    return f
  end
  TFItemWarmTipTextLeft1={GetText=function()return tipNames[tipItem]end,
    GetTextColor=function()return .7,.3,.9 end}
  DG.__asked={}
  DG.ContinueOnItemLoad=function()return false end
  DG.FlushItemCardsNow=function(id)flushed[#flushed+1]=id end
  DG.ItemName=function(id)
    local hit=DG.__tipName and DG.__tipName[id]
    return apiNames[id] or (hit and hit[1]),(apiNames[id] or hit)~=nil
  end
'''


class DungeonMergeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)

    def load_section(self, start, end, source=DUNGEON):
        begin = source.index(start)
        self.lua.execute(source[begin:source.index(end, begin + len(start))])

    def load_items(self):
        self.load_section("function DG.RefreshItemCards(", "function DG.FlushItemCardsNow(")
        self.load_section("function DG.RequestItem(", "function DG.PrewarmLoot(")

    def load_quests(self):
        self.lua.execute(r'''
          DG.Q_PAD=8;DG.Q_LIST_W=520;DG.GUTTER=8;DG.FILTER_MAX=5
          DG.FILTER_Y=160;DG.Q_FAC_ICON={A='alliance',H='horde'}
          DG.QSIDE_LABEL={all=L['全部'],A=L['联盟'],H=L['部落']}
          DG.EnsureQuestLane=function()end;DG.EnsureQuestListener=function()end
          DG.BuildPreDone=function()end;DG.PrefetchQuestData=function()end
          DG.RaiseDetailChrome=function()end;DG.RefreshFilterRow=function()end
          DG.PlayerSide=function()return playerSide end;playerSide='A'
          quests={{101,'A'},{102,'H'},{103}}
          DG.QuestList=function()return quests end
          DG.QuestDone=function(id)return id==102 end
          DG.QuestState=function(id)return id==102 and 'done' or 'todo' end
          DG.PaintQuestOverview=function()overviewCalls=(overviewCalls or 0)+1 end
          U.RenderQuestDetail=function()end
          U.dungeonDetail=widget();U.dungeonDetailHero=widget()
          U.dungeonDetailCur={id='test'};U.dungeonFilterBtns={}
          U.dungeonQPlateL=widget();U.dungeonQPlateL.w=DG.Q_LIST_W
          U.dungeonQPlateR=widget();U.dungeonQDet=widget()
          U.dungeonQuestScroll=widget();U.dungeonQuestChild=widget()
          U.dungeonQuestPool={};U.dungeonQuestSum=widget()
          U.dungeonQOverviewF=widget();U.dungeonQOVCard=widget()
          U.dungeonQListCard=widget()
        ''')
        head = next(line for line in DUNGEON.splitlines() if line.startswith("DG.Q_HEAD_H ="))
        self.lua.execute(head)
        self.load_section("function U:SetQuestSide(", "function U:ShowDungeonDetail(")
        self.load_section("function DG.ApplyDetailChrome(", "function DG.BuildDetailTabs(")
        self.load_section("function DG.BuildDetailFilterRow(", "function DG.BuildDetailLootView(")
        begin = DUNGEON.index("function U:RenderDungeonQuests(")
        end = DUNGEON.index("    local selOk = false", begin)
        self.lua.execute(DUNGEON[begin:end] + "return groups\nend")
        self.lua.execute("DG.BuildDetailFilterRow()")

    def test_tooltip_name_color_cache_reentrancy_and_batched_refresh(self):
        self.load_items()
        self.lua.execute(r'''
          tipNames[10]='客户端物品名';tipNames[11]='不应重入'
          onLink=function()
            DG.RefreshItemCards(10);DG.RefreshItemCards(10)
            assert(DG.HarvestTipName(11)==nil)
          end
          assert(DG.HarvestTipName(10)=='客户端物品名')
          assert(tipCalls==1 and DG.__tipColor[1]==.7 and DG.__tipColor[3]==.9)
          assert(not DG.__tipBusy and #flushed==0 and #timers==1)
          runTimers();assert(#flushed==1 and flushed[1]==10)
          assert(DG.HarvestTipName(10)=='客户端物品名' and tipCalls==1)
          apiNames[12]='API物品';apiQualities[12]=4
          assert(DG.HarvestTipName(12)=='API物品' and lastQuality==4 and tipCalls==1)
        ''')

    def test_tooltip_failure_ceiling_and_real_item_events_reset_it(self):
        self.load_items()
        self.lua.execute(r'''
          failTooltip=true;apiNames[20]=''
          for i=1,6 do assert(DG.HarvestTipName(20)==nil and not DG.__tipBusy) end
          assert(tipCalls==3 and DG.__tipFails[20]==3 and DG.__tipDead[20])
          DG.__itemEvt.scripts.OnEvent(DG.__itemEvt,'GET_ITEM_INFO_RECEIVED',20,false)
          assert(DG.__tipDead[20])
          DG.__itemEvt.scripts.OnEvent(DG.__itemEvt,'GET_ITEM_INFO_RECEIVED',999,true)
          assert(DG.__tipDead[20])
          DG.__itemEvt.scripts.OnEvent(DG.__itemEvt,'GET_ITEM_INFO_RECEIVED',20,true)
          assert(not DG.__tipDead[20] and not DG.__tipFails[20])
          failTooltip=false;tipNames[20]='重试成功'
          assert(DG.HarvestTipName(20)=='重试成功' and tipCalls==4)
          DG.__tipDead[21]=true;DG.__tipFails[21]=3
          DG.__itemEvt.scripts.OnEvent(DG.__itemEvt,'PLAYER_ENTERING_WORLD')
          assert(not DG.__tipDead and not DG.__tipFails)
        ''')

    def test_tooltip_budget_and_opt_out_do_not_count_as_failed_reads(self):
        self.load_items()
        self.lua.execute(r'''
          for id=1,41 do DG.__asked[id]=true;tipNames[id]='客户端'..id end
          for id=1,40 do assert(DG.HarvestTipName(id)) end
          assert(not DG.HarvestTipName(41) and tipCalls==40)
          assert(not DG.__tipFails or not DG.__tipFails[41])
          now=now+.25;assert(DG.HarvestTipName(41) and tipCalls==41)
          DungeonsForeverDB.dfNoTipWarm=true
          assert(not DG.HarvestTipName(42) and tipCalls==41)
          apiNames[43]='已缓存的API名称';apiQualities[43]=2
          assert(DG.HarvestTipName(43)=='已缓存的API名称' and tipCalls==41)
        ''')

    def test_all_factions_persist_and_overview_list_modes_coexist(self):
        self.load_quests()
        self.lua.execute(r'''
          local groups=U:RenderDungeonQuests()
          assert(U.dungeonQSide=='A' and store.dungeonQSide=='A' and #groups[1].rows==2)
          U:SetQuestSide('all');groups=U:RenderDungeonQuests()
          assert(store.dungeonQSide=='all' and #groups[1].rows==3)
          local keys={'all','A','H','qov','qlist'}
          for i,key in ipairs(keys) do assert(U.dungeonFilterBtns[i].__key==key) end
          U.dungeonQSide=nil
          assert(DG.QuestSideFor({A=2,H=2})=='all','reload lost explicit all')
          U.dungeonFilterBtns[4].scripts.OnClick()
          assert(U.dungeonQView=='overview' and overviewCalls==1 and U.dungeonQOverviewF.shown)
          U.dungeonFilterBtns[5].scripts.OnClick()
          assert(U.dungeonQView=='list' and not U.dungeonQOverviewF.shown)
          assert(store.dungeonQSide=='all' and U.dungeonFilterBtns[1].selected)
        ''')

    def test_legacy_faction_values_and_default_without_matching_quests(self):
        self.load_quests()
        self.lua.execute(r'''
          store.dungeonQSide='H';U.dungeonQSide=nil
          assert(DG.QuestSideFor({A=4,H=0})=='H','explicit legacy H must not be replaced')
          store.dungeonQSide='invalid';U.dungeonQSide=nil
          assert(DG.QuestSideFor({A=0,H=4})=='all')
          store.dungeonQSide=nil;U.dungeonQSide=nil
          assert(DG.QuestSideFor({A=2,H=2})=='A')
          U.dungeonFilterBtns[1].__mode='quest';U.dungeonFilterBtns[1].__key='all'
          U.dungeonFilterBtns[1].scripts.OnClick()
          assert(store.dungeonQSide=='all')
        ''')

    def test_quest_controls_fit_separate_rows_in_chinese_and_english(self):
        self.load_quests()
        self.lua.execute(r'''
          local function check()
            U:RenderDungeonQuests()
            local right=0
            for i,bt in ipairs(U.dungeonFilterBtns) do
              local x,y=bt.point[4],bt.point[5]
              assert(x>=right and y==-DG.Q_PAD,'filter controls overlap')
              right=x+bt.w
            end
            assert(right<=DG.Q_LIST_W-DG.Q_PAD,'filters exceed left panel')
            local done,pins=U.dungeonQDoneTg,U.dungeonQuestPinTg
            local secondTop=-done.point[5]
            assert(secondTop>=DG.Q_PAD+24+8,'switches overlap filters')
            assert(secondTop+done.h+DG.Q_PAD<=DG.Q_HEAD_H,'viewport covers switches')
            local width=done.w+done.label:GetStringWidth()+6+8+pins.w
              +pins.label:GetStringWidth()+6+6+U.dungeonQuestPinCfg.w
            assert(width<=DG.Q_LIST_W-2*DG.Q_PAD,'switch row exceeds left panel')
          end
          check()
          L['全部']='All';L['联盟']='Alliance';L['部落']='Horde'
          L['总览']='Overview';L['列表']='List'
          DG.QSIDE_LABEL={all=L['全部'],A=L['联盟'],H=L['部落']}
          U.dungeonQDoneTg.label:SetText('Show completed')
          U.dungeonQuestPinTg.label:SetText('Map pins')
          check()
        ''')

    def test_map_quest_pins_default_off_and_preserve_explicit_preferences(self):
        self.load_quests()
        self.load_section("function M.QuestPinsOn(", "function M.ExtraPinsFor(", MAP)
        self.lua.execute(r'''
          assert(not U.dungeonQuestPinTg.checked and not M.QuestPinsOn())
          U.dungeonQuestPinTg:SetChecked(true)
          U.dungeonQuestPinTg.scripts.OnClick(U.dungeonQuestPinTg)
          assert(store.mapQuestPins==true and M.QuestPinsOn())
          U.dungeonQuestPinTg:SetChecked(false)
          U.dungeonQuestPinTg.scripts.OnClick(U.dungeonQuestPinTg)
          assert(store.mapQuestPins==false and not M.QuestPinsOn())
          DungeonsForeverDB=nil;assert(not M.QuestPinsOn())
        ''')

    def test_waypoint_uses_permission_return_value_for_all_entry_points(self):
        self.lua.execute(r'''
          created={};placed={};opened={};M={}
          function GetBuildInfo()return '', '', '', 16001 end
          ns.NPCLoc={[1]={1453,10,20}};ns.DungeonEntry={test={1453,10,20}}
          ns.DungeonEntryRoute={test={{1454,30,40}}}
          UiMapPoint={CreateFromCoordinates=function(map,x,y)
            created[#created+1]={map,x,y};return {map=map,x=x,y=y}
          end}
          C_Map={GetMapInfo=function(map)return map~=999 and {} or nil end,
            CanSetUserWaypointOnMap=function()return allowed end,
            SetUserWaypoint=function(pt)placed[#placed+1]=pt end,
            OpenWorldMap=function(map)opened[#opened+1]=map end}
          C_SuperTrack={SetSuperTrackedUserWaypoint=function()end}
        ''')
        self.load_section("local function MapUsable(", "function DG.ShowEntrancePointTip(")
        self.lua.execute(r'''
          allowed=false
          DG.MarkNPC(1);DG.MarkEntrance('test');DG.MarkEntranceAt('test',2)
          assert(#created==0 and #placed==0 and #opened==3)
          allowed=true
          DG.MarkNPC(1,{1454,30,40});DG.MarkEntrance('test');DG.MarkEntranceAt('test',2)
          assert(#placed==3 and placed[1].map==1454 and placed[1].x==.3)
          DG.MarkNPC(1,{999,30,40});assert(#placed==3 and #opened==6)
          C_Map.CanSetUserWaypointOnMap=function()error('unsupported map')end
          DG.MarkNPC(1);assert(#placed==3)
          C_Map.CanSetUserWaypointOnMap=nil
          DG.MarkNPC(1);assert(#placed==4)
        ''')


if __name__ == "__main__":
    unittest.main()
