"""Offline behavior checks for the master spellbook integration.

Real data and modules run under Lua 5.1. Client frames, API responses and event
dispatch are simulated; this does not establish live-client rendering or taint safety.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
from lupa.lua51 import LuaRuntime


MOCKS = r'''
format=string.format;frames={};timers={};initFns={};addonCallbacks={}
known={};queries=0;class='WARRIOR';level=20;faction='Alliance';build=16001
combat=false;logged=true;messages={};mapCalls={};db={ui={}}
ns={IsTitan=true,hui={},FONT='mock'}
function ns.Init(fn)initFns[#initFns+1]=fn end
function ns.DB()return db end
function ns.PlaySound()end
function GetLocale()return locale end
function UnitClass()return class,class end
function UnitLevel()return level end
function UnitFactionGroup()return faction end
function GetBuildInfo()return '1.60','mock','',build end
function IsLoggedIn()return logged end
function InCombatLockdown()return combat end
function IsShiftKeyDown()return shift==true end
function print(s)messages[#messages+1]=s end
Enum={SpellBookSpellBank={Player=0}}
C_SpellBook={IsSpellKnownOrInSpellBook=function(id)
  queries=queries+1;return known[id]==true
end,GetNumSpellBookSkillLines=function()return 1 end}
C_Spell={GetSpellName=function(id)return 'Spell '..id end,
  GetSpellTexture=function(id)return id end,GetSpellLink=function(id)return 'spell:'..id end}
C_Timer={After=function(delay,fn)timers[#timers+1]={delay=delay,fn=fn}end}
EventUtil={ContinueOnAddOnLoaded=function(name,fn)addonCallbacks[name]=fn end}
function drainTimers()
  local n=0
  while #timers>0 do
    local t=table.remove(timers,1);t.fn();n=n+1;assert(n<50,'unbounded retry')
  end
  return n
end
function fire(event,...)
  for _,f in ipairs(frames)do
    if f.events[event] and f.scripts.OnEvent then f.scripts.OnEvent(f,event,...)end
  end
end
function hooksecurefunc(t,key,fn)
  local original=assert(t[key],key)
  t[key]=function(...)local result=original(...);fn(...);return result end
end

local Node={}
function Node:SetScript(k,f)self.scripts[k]=f end
function Node:HookScript(k,f)
  local original=self.scripts[k]
  self.scripts[k]=function(...)if original then original(...)end;f(...)end
end
function Node:RegisterEvent(k)self.events[k]=true end
function Node:UnregisterEvent(k)self.events[k]=nil end
function Node:SetShown(v)self.shown=v end
function Node:Show()self.shown=true end
function Node:Hide()self.shown=false end
function Node:IsShown()return self.shown end
function Node:SetPoint(...)self.point={...} end
function Node:ClearAllPoints()self.point=nil end
function Node:GetChildren()return unpack(self.children)end
function Node:GetRegions()return unpack(self.regions)end
function Node:GetParent()return self.parent end
function Node:GetRight()return self.right or 300 end
function Node:SetWidth(v)self.width=v end
function Node:GetWidth()return self.width or 30 end
function Node:SetHeight(v)self.height=v end
function Node:GetHeight()return self.height or 30 end
function Node:SetSize(w,h)self.width=w;self.height=h end
function Node:IsObjectType(k)return self.kind==k end
function Node:SetText(v)self.text=v end
function Node:SetTexture(v)self.texture=v end
function Node:SetAlpha(v)self.alpha=v end
function Node:SetDesaturated(v)self.desaturated=v end
function Node:SetDesaturation(v)self.desaturation=v end
function Node:SetTextColor(...)self.color={...}end
function Node:SetVertexColor(...)self.color={...}end
function Node:GetVertexColor()return unpack(self.color or {1,1,1})end
function Node:SetColorTexture(...)self.color={...}end
function Node:EnableMouse(v)self.mouse=v end
function Node:SetChecked(v)self.checked=v end
function Node:SetEnabled(v)self.enabled=v end
function Node:Enable()self.enabled=true end
function Node:SetTabSelected(v)self.selected=v end
function Node:IsSelected()return self.selected==true end
function Node:IsForceDisabled()return self.forceDisabled==true end
function Node:SetFrameLevel(v)self.frameLevel=v end
function Node:GetFrameLevel()return self.frameLevel or 3 end
function Node:SetTooltipText(v)self.tooltip=v end
function Node:Init(_,_,icon)self.Icon:SetTexture(icon)end
for _,key in ipairs({'SetAllPoints','RegisterForClicks','SetFont','SetJustifyH',
  'SetBackdrop','SetBackdropColor','SetBackdropBorderColor','SetSquareMode','SetAtlas'})do
  Node[key]=function()end
end
function node(kind,parent)
  local f=setmetatable({kind=kind or 'Frame',parent=parent,shown=true,
    scripts={},events={},children={},regions={}},{__index=Node})
  if parent then parent.children[#parent.children+1]=f end
  return f
end
function Node:CreateFontString()return node('FontString',self)end
function Node:CreateTexture()
  local t=node('Texture');self.regions[#self.regions+1]=t;return t
end
function CreateFrame(kind,name,parent,template)
  local f=node(kind,parent);frames[#frames+1]=f
  if name then _G[name]=f end
  if template=='SpellBookCategoryTabTemplate' then
    for _,key in ipairs({'Icon','IconMask','SquareBackground','SquareBackgroundActive',
      'SquareBackgroundActiveGlow'})do f[key]=node('Texture')end
  end
  return f
end
function makeBook(foreign)
  local sb=node();local sys=node('Frame',sb);sys.right=100
  local tab=CreateFrame('Button',nil,sys,'SpellBookCategoryTabTemplate');tab.right=100;tab.selected=true
  sys.tabs={tab};function sys:SetTab(id)sb.tab=id end
  if foreign then
    foreignTab=CreateFrame('Button',nil,sys,'SpellBookCategoryTabTemplate');foreignTab.right=140
  end
  local p=node();p.elementTemplateData={native=true};p.dataProvider={native=true}
  p.View1=node();p.View2=node();p.PagingControls={page=1,
    PreviousPage=function(s)s.page=s.page-1 end,NextPage=function(s)s.page=s.page+1 end}
  function p:SetElementTemplateData(v)self.elementTemplateData=v end
  function p:SetDataProvider(v)self.dataProvider=v end
  sb.CategoryTabSystem=sys;sb.PagedSpellsFrame=p;sb.tab=1
  function sb:GetTab()return self.tab end
  function sb:UpdateDisplayedSpells()p.dataProvider={native=true}end
  function sb:UpdateAllSpellData()p.dataProvider={native=true}end
  function sb:ResizeSearchBox()self.SearchBox.width=300 end
  sb.SearchBox=node();sb.SearchBox.right=600;sb.SettingsDropdown=node();sb.SearchPreviewContainer=node()
  PlayerSpellsFrame={SpellBookFrame=sb};book=sb;paged=p
end
function CreateDataProvider(groups)return {groups=groups}end
function boot()for _,fn in ipairs(initFns)do fn()end end
function click(tab)tab.scripts.OnClick(tab)end
UIErrorsFrame={AddMessage=function(_,s)messages[#messages+1]=s end}
UiMapPoint={CreateFromCoordinates=function(id,x,y)return {id=id,x=x,y=y}end}
C_Map={GetAreaInfo=function(id)return 'Zone '..id end,
  CanSetUserWaypointOnMap=function()return true end,
  SetUserWaypoint=function(pt)mapCalls.point=pt end,
  OpenWorldMap=function(id)mapCalls.open=id end}
C_SuperTrack={SetSuperTrackedUserWaypoint=function(on)mapCalls.super=on end}
GameTooltip=node();function GameTooltip:SetOwner()end
function GameTooltip:ClearLines()self.lines={}end
function GameTooltip:AddLine(text)self.lines[#self.lines+1]=text end
function GameTooltip:SetSpellByID(id)self.spell=id end
ChatFrameUtil={InsertLink=function(link)insertedLink=link;return true end}
SpellBookItemButtonMixin={}
for _,key in ipairs({'OnEnter','OnLeave','OnClick','OnMouseDown','OnMouseUp','OnDragStart'})do
  SpellBookItemButtonMixin[key]=function()end
end
function itemFrame()
  local f=node();f.Name=node();f.SubName=node();f.RequiredLevel=node();f.Backplate=node()
  f.Button=node('Button',f)
  for _,key in ipairs({'Icon','Border','BorderShadow','IconHighlight'})do f.Button[key]=node('Texture')end
  return f
end
'''


class NativeSpellBookTests(unittest.TestCase):
    def load(self, name):
        self.lua.execute('local fn=assert(loadstring(...));fn("DungeonsForever",ns)',
                         (ROOT / name).read_text(encoding='utf-8-sig'))

    def setup_client(self, locale='zhCN', supported=True, foreign=False, attached=True):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().locale = locale
        self.lua.execute(MOCKS)
        self.lua.globals().ns.IsTitan = supported
        self.load('Locales/zhCN.lua')
        if locale != 'zhCN':
            self.load('Locales/' + locale + '.lua')
        source = (ROOT / 'Core/Core.lua').read_text(encoding='utf-8-sig')
        helpers = source[source.index('function ns.SpellTabsTaken()'):source.index('\ndo\n', source.index('function ns.SpellTabsTaken()'))]
        self.lua.execute('local DB=ns.DB\n' + helpers)
        # Respect actual TOC order and locale conditions for all new data.
        for row in (ROOT / 'DungeonsForever.toc').read_text(encoding='utf-8-sig').splitlines():
            if 'Data_SpellBook.lua' not in row and 'Data_WeaponTraining.lua' not in row:
                continue
            if '[AllowLoadTextLocale ' in row and ('[AllowLoadTextLocale ' + locale + ']') not in row:
                continue
            self.load(row.split(' [', 1)[0].replace('\\', '/'))
        self.load('Core/SpellTraining.lua')
        self.load('Core/WeaponMasters.lua')
        if attached:
            self.lua.eval('makeBook')(foreign)
        self.load('Core/NativeSpellBook.lua')

    def test_unsupported_client_does_not_install_modules(self):
        self.setup_client(supported=False)
        self.lua.execute('assert(not ns.SpellTraining and not ns.WeaponMasters and not ns.NativeSpellBook);assert(#initFns==0)')

    def test_real_data_all_classes_levels_factions_and_locales(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                self.setup_client(locale)
                self.lua.execute('''
                  local classCount=0
                  for cls,data in pairs(ns.SpellBookData.classes)do
                    class=cls;classCount=classCount+1
                    local total=0;for _,tab in ipairs(data.tabs)do total=total+#tab.spells end
                    for _,lv in ipairs({1,18,20,60})do
                      level=lv;local groups=ns.SpellTraining.Rows();local count=0
                      for key,rows in pairs(groups)do
                        for _,r in ipairs(rows)do
                          count=count+1;assert(r.id and r.name and r.icon)
                          if key=='available' then assert(r.learn<=lv)end
                          if key=='next' then assert(r.learn>lv and r.learn<=lv+2)end
                          if key=='notlevel' then assert(r.learn>lv+2)end
                        end
                      end
                      assert(count==total)
                      for _,fac in ipairs({'Alliance','Horde'})do
                        faction=fac;local wg=ns.WeaponMasters.Rows();local seen={}
                        for _,rows in pairs(wg)do for _,r in ipairs(rows)do
                          assert(not seen[r.id]);seen[r.id]=true
                          assert(ns.WeaponTraining.skills[r.id].classes[cls])
                          for _,tr in ipairs(r.trainers)do
                            assert(tr.uiMapId and tr.x>=0 and tr.x<=100 and tr.y>=0 and tr.y<=100)
                            local found=false
                            for _,raw in ipairs(ns.WeaponTraining.skills[r.id].trainers)do
                              if raw.npc==tr.npc and raw.faction==fac then found=true end
                            end
                            assert(found)
                          end
                        end end
                      end
                    end
                  end
                  assert(classCount==9)
                ''')

    def test_next_rank_and_known_talent_classification(self):
        self.setup_client()
        self.lua.execute('''
          ns.SpellBookData={classes={WARRIOR={tabs={{name='Test',spells={
            {name='Ranked',ranks={{id=1,learn=1},{id=2,learn=21},{id=3,learn=30}}},
            {name='Single',id=4,learnLv=1},{name='Talent',id=5,isTalent=true},
            {name='Future',id=6,learnLv=30}}}}}}}
          known[1]=true;known[4]=true;local g=ns.SpellTraining.Rows()
          assert(g.next[1].id==2 and g.next[1].rank==2)
          assert(g.known[1].id==4 and g.talent[1].id==5 and g.notlevel[1].id==6)
          known[3]=true;ns.SpellTraining.Invalidate();g=ns.SpellTraining.Rows()
          assert(#g.next==0 and #g.known==2)
          class='UNKNOWN';assert(ns.SpellTraining.Rows()==nil)
        ''')

    def test_knowledge_cache_and_event_invalidation(self):
        self.setup_client()
        self.lua.execute('''
          assert(not ns.SpellTraining.Knows(1));known[1]=true
          assert(not ns.SpellTraining.Knows(1) and queries==1)
          fire('LEARNED_SPELL_IN_SKILL_LINE');assert(ns.SpellTraining.Knows(1) and queries==2)
          for _,event in ipairs({'PLAYER_LEVEL_UP','SKILL_LINES_CHANGED','PLAYER_ENTERING_WORLD'})do
            fire(event);ns.SpellTraining.Knows(1)
          end
          assert(queries==5)
        ''')

    def test_spell_api_fallbacks_and_errors(self):
        self.setup_client()
        self.lua.execute('''
          for _,api in ipairs({'IsSpellKnownOrInSpellBook','IsSpellInSpellBook','IsSpellKnown','legacy','throw'})do
            C_SpellBook={};IsSpellKnown=nil
            if api=='legacy' then IsSpellKnown=function()return true end
            elseif api=='throw' then C_SpellBook.IsSpellKnown=function()error('unavailable')end
            else C_SpellBook[api]=function()return true end end
            ns.SpellTraining.Invalidate();assert(ns.SpellTraining.Knows(1)==(api~='throw'))
          end
          C_SpellBook={IsSpellInSpellBook=function()return false end,IsSpellKnown=function()return true end}
          ns.SpellTraining.Invalidate();assert(ns.SpellTraining.Knows(1))
        ''')

    def test_weapon_skill_level_known_and_faction(self):
        self.setup_client()
        self.lua.execute('''
          local function has(rows,id)for _,r in ipairs(rows)do if r.id==id then return r end end end
          level=19;local g=ns.WeaponMasters.Rows();assert(has(g.notlevel,200))
          level=20;g=ns.WeaponMasters.Rows();assert(has(g.available,200))
          known[200]=true;ns.SpellTraining.Invalidate();g=ns.WeaponMasters.Rows();assert(has(g.known,200).known)
          faction='Horde';g=ns.WeaponMasters.Rows();assert(has(g.known,200).trainers[1].npc==11870)
          class='MAGE';g=ns.WeaponMasters.Rows();assert(not has(g.known,200) and not has(g.available,200))
        ''')

    def test_waypoint_coordinates_and_unsupported_or_missing_location(self):
        self.setup_client()
        self.lua.execute('''
          local tr={uiMapId=1453,x=63.9,y=69.1}
          ns.WeaponMasters.MarkNPC(tr)
          assert(mapCalls.point.id==1453 and math.abs(mapCalls.point.x-0.639)<1e-8)
          assert(math.abs(mapCalls.point.y-0.691)<1e-8 and mapCalls.open==1453 and mapCalls.super==false)
          mapCalls={};build=120005;ns.WeaponMasters.MarkNPC(tr);assert(next(mapCalls)==nil and #messages==1)
          build=16001;ns.WeaponMasters.MarkNPC({});assert(next(mapCalls)==nil and #messages==2)
          C_Map.CanSetUserWaypointOnMap=function()return false end
          ns.WeaponMasters.MarkNPC(tr);assert(not mapCalls.point and mapCalls.open==1453)
        ''')

    def test_default_yields_to_foreign_tabs_explicit_choice_wins(self):
        self.setup_client(foreign=True)
        self.lua.execute('''
          assert(ns.SpellTabsTaken() and not ns.SpellEnhOn());boot()
          assert(not DungeonsForeverSpellBookTab)
          ns.SetSpellEnh(true)
          assert(DungeonsForeverSpellBookTab:IsShown() and DungeonsForeverWeaponBookTab:IsShown())
          assert(DungeonsForeverSpellBookTab.point[2]==foreignTab)
          assert(db.ui.spellEnh==true and ns.SpellEnhOn())
          ns.SetSpellEnh(false);assert(not DungeonsForeverSpellBookTab:IsShown() and not ns.SpellEnhOn())
        ''')

    def test_late_foreign_tab_restores_native_page_without_saving_preference(self):
        self.setup_client()
        self.lua.execute('''
          boot();click(DungeonsForeverSpellBookTab);assert(not paged.dataProvider.native)
          local tab=CreateFrame('Button',nil,book.CategoryTabSystem,'SpellBookCategoryTabTemplate')
          book.scripts.OnShow(book)
          assert(not DungeonsForeverSpellBookTab:IsShown() and paged.dataProvider.native)
          assert(db.ui.spellEnh==nil)
        ''')

    def test_delayed_native_addon_load_and_bounded_retry(self):
        self.setup_client(attached=False)
        self.lua.execute('''
          boot();assert(not DungeonsForeverSpellBookTab)
          assert(drainTimers()==6)
          makeBook(false);addonCallbacks.Blizzard_PlayerSpells()
          assert(DungeonsForeverSpellBookTab:IsShown())
          local original=DungeonsForeverSpellBookTab
          fire('PLAYER_ENTERING_WORLD');drainTimers()
          assert(DungeonsForeverSpellBookTab==original)
        ''')

    def test_spell_weapon_pages_restore_native_controls_and_provider(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                self.setup_client(locale)
                self.lua.execute('''
                  boot();local native=paged.elementTemplateData
                  click(DungeonsForeverSpellBookTab)
                  assert(not book.SearchBox:IsShown() and not book.SettingsDropdown:IsShown())
                  assert(paged.dataProvider.groups[1].header.text==ns.L['可学'])
                  ns.NativeSpellBook.Page(1);assert(paged.PagingControls.page==2)
                  ns.NativeSpellBook.Page(-1);assert(paged.PagingControls.page==1)
                  click(DungeonsForeverWeaponBookTab)
                  assert(paged.dataProvider.groups[1].elements[1].trainer)
                  click(book.CategoryTabSystem.tabs[1])
                  assert(paged.dataProvider.native and paged.elementTemplateData==native)
                  assert(book.SearchBox:IsShown() and book.SettingsDropdown:IsShown())
                  click(DungeonsForeverSpellBookTab);ns.SetSpellEnh(false)
                  assert(paged.dataProvider.native and not DungeonsForeverWeaponBookTab:IsShown())
                ''')

    def test_combat_click_does_not_replace_native_provider(self):
        self.setup_client()
        self.lua.execute('''
          boot();combat=true;click(DungeonsForeverSpellBookTab)
          assert(paged.dataProvider.native and book.SearchBox:IsShown() and #messages==1)
          click(DungeonsForeverWeaponBookTab);assert(paged.dataProvider.native and #messages==2)
        ''')

    def test_native_updates_and_learning_events_refresh_active_page(self):
        self.setup_client()
        self.lua.execute('''
          boot();click(DungeonsForeverSpellBookTab)
          local first=paged.dataProvider;book:UpdateDisplayedSpells()
          assert(paged.dataProvider~=first and paged.dataProvider.groups)
          first=paged.dataProvider;fire('PLAYER_LEVEL_UP');assert(paged.dataProvider~=first)
          book:UpdateAllSpellData();assert(paged.dataProvider.groups)
          book.CategoryTabSystem:SetTab(2);assert(paged.dataProvider.native)
        ''')

    def test_reused_native_item_tooltip_link_waypoint_and_reset(self):
        self.setup_client()
        self.lua.execute('''
          boot();click(DungeonsForeverSpellBookTab)
          local tpl=paged.elementTemplateData.SPELL;local f=itemFrame()
          tpl.initFunc(f,{name='Future',icon='INV_Sword_27',req='Level 30',dim=true,spellID=123})
          assert(f.Button.Icon.desaturated and f.RequiredLevel:IsShown())
          f.Button.scripts.OnEnter(f.Button);assert(GameTooltip.spell==123 and ns.hui.nativeTipOwner==f)
          f.Button.scripts.OnLeave(f.Button);assert(not GameTooltip:IsShown() and not ns.hui.nativeTipOwner)
          shift=true;click(f.Button);assert(insertedLink=='spell:123')
          tpl.initFunc(f,{name='Known',icon=123,req='',spellID=123})
          assert(not f.Button.Icon.desaturated and not f.RequiredLevel:IsShown())
          tpl.initFunc(f,{name='Trainer',trainer={uiMapId=1453,x=10,y=20},spellID=123})
          click(f.Button);assert(mapCalls.point.id==1453)
          tpl.resetFunc({},f)
          assert(not f.__d and not f.__ov:IsShown() and not f.__ov.mouse)
          assert(f.Button.scripts.OnClick==SpellBookItemButtonMixin.OnClick and f.Button.Icon.alpha==1)
        ''')

    def test_settings_card_toggle_and_foreign_tab_note(self):
        for locale in ('zhCN', 'zhTW', 'enUS'):
            with self.subTest(locale=locale):
                self.setup_client(locale)
                source = (ROOT / 'Core/MainFrame.lua').read_text(encoding='utf-8-sig')
                card = source[source.index('local spellCard\n'):source.index('local function AnchorTipCard(card)')]
                self.lua.execute('''
                  local L=ns.L;local settingsPop=node();local appearanceCard=node()
                  local C_TIP_DIM={.6,.6,.6};local C_TIP_TXT={1,1,1}
                ''' + card + '''
                  ns.BuildSpellCard();local card=spellCard;assert(spellToggle.checked)
                  assert(spellNote.text==ns.L['训练师、武器技能两页'])
                  click(spellToggle);assert(db.ui.spellEnh==false and not spellToggle.checked)
                  click(spellToggle);assert(db.ui.spellEnh==true and spellToggle.checked)
                  local tab=CreateFrame('Button',nil,book.CategoryTabSystem,'SpellBookCategoryTabTemplate')
                  ns.BuildSpellCard();assert(spellCard==card)
                  assert(spellNote.text==ns.L['其它插件页签同时开启'])
                  click(spellToggle);assert(spellNote.text==ns.L['已有插件占用技能页'])
                ''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
