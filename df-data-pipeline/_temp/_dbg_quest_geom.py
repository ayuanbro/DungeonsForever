# -*- coding: utf-8 -*-
"""详情子页（任务 / 攻略 / 掉落）栅格探针：验证内衬 8 -> 0 后各常量与锚点真值。

只 dump 常量 + 原始 SetPoint 参数（桩不解算绝对坐标），绝对位置在 Python 侧手算。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT') or r'D:\workspace\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

BUILD = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  local DG = TF_NS.ProfHost.DG
  if DG.EnsureDetailBuilt then DG.EnsureDetailBuilt() end
  if DG.EnsureQuestLane then DG.EnsureQuestLane() end
  if DG.EnsureGuideLane then DG.EnsureGuideLane() end
end
'''

DUMP = r'''
(function()
  local U  = TF_NS.DungeonUI
  local DG = TF_NS.ProfHost.DG
  local out = {}
  local function p(s) out[#out+1] = s end
  local function n(v) return (type(v) == 'number') and tostring(v) or ('<'..type(v)..'>') end
  p('--- 栅格常量 ---')
  p('CHILD_W='..n(DG.CHILD_W)..' GUTTER='..n(DG.GUTTER)..' PAGE_INSET='..n(TF_NS.ProfHost.PAGE_INSET))
  p('Q_LIST_W='..n(DG.Q_LIST_W)..' Q_DET_GAP='..n(DG.Q_DET_GAP)..' Q_PAD='..n(DG.Q_PAD)
    ..' Q_DET_W='..n(DG.Q_DET_W))
  p('--- 任务页纵向 ---')
  p('HERO_H='..n(DG.HERO_H)..' FILTER_Y='..n(DG.FILTER_Y)..' SCROLL_Y='..n(DG.SCROLL_Y)
    ..' Q_SUM_H='..n(DG.Q_SUM_H)..' Q_HEAD_H='..n(DG.Q_HEAD_H))
  p('GUIDE_SIDE='..n(DG.GUIDE_SIDE)..' GUIDE_GRID_W='..n(DG.GUIDE_GRID_W)
    ..' GUIDE_CARD_W='..n(DG.GUIDE_CARD_W)..' GUIDE_GAP_X='..n(DG.GUIDE_GAP_X))
  p('LOOT_CARD_W='..n(DG.LOOT_CARD_W)..' LOOT_CARD_W3='..n(DG.LOOT_CARD_W3)
    ..' LOOT_MODEL_W='..n(DG.LOOT_MODEL_W)..' LOOT_MODEL_X='..n(DG.LOOT_MODEL_X))
  p('--- 帧锚点（末发 SetPoint 原始参数）---')
  local function a(f, tag)
    if not f then p(tag..' = nil'); return end
    local t = f.__pts
    if not t then p(tag..' __pts=nil'); return end
    p(tag..' {'..tostring(t[1])..','..tostring(t[3])..','..n(t[4])..','..n(t[5])..'}'
      ..' w='..n(f.__w)..' h='..n(f.__h))
  end
  a(U.dungeonDetail, 'detail     ')
  a(U.dungeonQuestScroll, 'qscroll    ')
  a(U.dungeonQDet, 'qdet       ')
  a(U.dungeonQPlateL, 'plateL     ')
  a(U.dungeonQPlateR, 'plateR     ')
  a(U.dungeonGuideScroll, 'gscroll    ')
  a(U.dungeonDetailScroll, 'dscroll    ')
  p('--- 任务筛选按钮（ApplyDetailChrome("quest") 后）---')
  local sum = U.dungeonQuestSum
  p('questSum text="'..tostring(sum and sum.__text)..'" shown='..tostring(sum and sum.__shown))
  for i = 1, #(U.dungeonFilterBtns or {}) do
    local bt = U.dungeonFilterBtns[i]
    if bt and bt.__pts then
      local t = bt.__pts
      p('btn'..i..' {'..tostring(t[1])..','..tostring(t[3])..','..n(t[4])..','..n(t[5])..'}'
        ..' w='..n(bt.__w)..' h='..n(bt.__h)..' text="'..tostring(bt.__text)..'"')
    end
  end
  return table.concat(out, '\n')
end)()
'''


def build_lua():
    toc = open(TOC, encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != T.STUB, 'GetStringWidth stub patch failed'
    lua.execute(stub)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = orig(...); return a, b, c, 16001, d end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "test area" .. tostring(id) end,
}
''')
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            raise RuntimeError('load %s failed (loadfile nil)' % rel)
        chunk()
    return lua


def drain(lua):
    lua.eval('(function() while #PUMPS > 0 do table.remove(PUMPS, 1)() end return 1 end)()')


def main():
    print('ADDON =', ADDON)
    lua = build_lua()
    lua.execute(BUILD)
    drain(lua)
    lua.execute('TF_NS.DungeonUI.dungeonTab = "quest"')
    lua.execute('TF_NS.ProfHost.DG.ApplyDetailChrome("quest")')
    print(lua.eval(DUMP))
    return 0


if __name__ == '__main__':
    sys.exit(main())
