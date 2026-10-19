# -*- coding: utf-8 -*-
"""地图页几何探针：验证 M.FRAME_H 与「详情页真实可用高」是否自洽。

桩只记原始 SetPoint 参数（__pts）与 SetSize（__w/__h），不解算绝对坐标 ⇒
本探针打印常量 + 关键帧的原始锚点，绝对位置在 Python 侧手算。
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

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\workspace\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

BUILD = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  local DG = TF_NS.ProfHost.DG
  if DG.EnsureDetailBuilt then DG.EnsureDetailBuilt() end
  if DG.EnsureMapPage then DG.EnsureMapPage() end
  local M = TF_NS.MapModule
  if M and M.Paint then pcall(M.Paint, { id = "onyxias_lair" }) end
end
'''

DUMP = r'''
(function()
  local U  = TF_NS.DungeonUI
  local DG = TF_NS.ProfHost.DG
  local M  = TF_NS.MapModule
  local out = {}
  local function p(s) out[#out+1] = s end
  local function n(v) return (type(v) == 'number') and tostring(v) or ('<'..type(v)..'>') end
  local function anchors(f, tag)
    if not f then p(tag..' = nil'); return end
    local a = f.__pts
    if not a then p(tag..' __pts=nil'); return end
    -- __pts 可能被 ClearAllPoints+SetPoint 覆盖成最后一发；逐点打印
    p(tag..' __pts={'..tostring(a[1])..','..tostring(a[3])..','..n(a[4])..','..n(a[5])..'}'
      ..' w='..n(f.__w)..' h='..n(f.__h)..' shown='..tostring(f.__shown))
  end

  p('--- Host 常量 ---')
  p('CONTENT_W='..n(TF_NS.ProfHost.CONTENT_W)..' CONTENT_H='..n(TF_NS.ProfHost.CONTENT_H)
    ..' PAGE_INSET='..n(TF_NS.ProfHost.PAGE_INSET)..' ROW_CLASS='..n(TF_NS.ProfHost.ROW_CLASS))
  p('--- DG 纵向常量 ---')
  p('HERO_H='..n(DG.HERO_H)..' GUIDE_TOP_Y='..n(DG.GUIDE_TOP_Y)
    ..' FILTER_Y='..n(DG.FILTER_Y)..' SCROLL_Y='..n(DG.SCROLL_Y)..' GUTTER='..n(DG.GUTTER))
  p('--- MapUI 常量 ---')
  p('FRAME_W='..n(M.FRAME_W)..' FRAME_H='..n(M.FRAME_H)..' MAP_W='..n(M.MAP_W)
    ..' SIDE_W='..n(M.SIDE_W)..' SIDE_GAP='..n(M.SIDE_GAP)..' SIDE_PAD='..n(M.SIDE_PAD))
  p('MAP_H='..n(M.MAP_H)..' HDR_CARD_H='..n(M.HDR_CARD_H)..' HDR_GAP='..n(M.HDR_GAP)
    ..' sum(卡+距+图)='..n((M.HDR_CARD_H or 0) + (M.HDR_GAP or 0) + (M.MAP_H or 0)))

  p('--- 帧锚点（原始 SetPoint 参数：point, relPoint, x, y）---')
  anchors(U.dungeonPage, 'page')
  anchors(U.dungeonDetail, 'detail')
  anchors(U.dungeonDetailHero, 'hero')
  local fr = M.frame
  anchors(fr, 'map.frame')
  if fr then
    anchors(fr.hdrCard, 'map.frame.hdrCard')
    anchors(fr.canvas, 'map.frame.canvas')
    anchors(fr.bar, 'map.frame.bar')
    anchors(fr.bossBtn, 'map.frame.bossBtn')
    anchors(fr.side, 'map.frame.side')
    anchors(fr.detScroll, 'map.frame.detScroll')
    anchors(fr.blkLoot, 'map.frame.blkLoot')
    anchors(fr.blkSkill, 'map.frame.blkSkill')
    anchors(fr.blkGuide, 'map.frame.blkGuide')
  else
    p('map.frame = nil (EnsureMapPage 未建/未调用)')
  end
  return table.concat(out, '\n')
end)()
'''


def build_lua():
    toc = open(os.path.join(ADDON, os.path.basename(TOC)),
               encoding='utf-8', errors='replace').read()
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
    # 补建地图页（需 detail + hero 已建）
    lua.execute('do local DG = TF_NS.ProfHost.DG; if DG and DG.EnsureMapPage then DG.EnsureMapPage() end end')
    drain(lua)
    r = lua.eval(DUMP)
    drain(lua)
    print(r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
