# -*- coding: utf-8 -*-
"""探针：量「首屏 U:Build()」与「首次打开详情页」各新建多少帧。

用法：python _temp/_probe_lazy_frames.py
只读，不改任何文件。为的是给「打开就卡死」的懒建/分帧改动一个可对比的数字。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

toc = open(TOC, encoding='utf-8', errors='replace').read()
files = [l.strip().replace('\\', '/') for l in toc.splitlines()
         if l.strip() and not l.strip().startswith('##')]

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 - 3660 end')
lua.execute("BG.hui.OnThemeChange = function(fn) end")
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('BG.hui = nil')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
            'local a,b,c,d = orig(...); return a,b,c,16001,e end end')
lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }
C_MAP_MARK = { wp = nil, opened = nil }
UiMapPoint = {
  CreateFromCoordinates = function(mapID, x, y)
    return { uiMapID = mapID, x = x, y = y }
  end,
}
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) C_MAP_MARK.wp = pt end,
  OpenWorldMap = function(mapID) C_MAP_MARK.opened = mapID end,
}
PLAYER_LEVEL = 16
UnitLevel = function() return PLAYER_LEVEL end
''')

loadfile = lua.eval(
    'function(rel)\n'
    '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
    '  if not chunk then return nil end\n'
    '  return function() return chunk("DungeonsForever", TF_NS) end\n'
    'end')

bad = 0
for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    chunk = loadfile(rel)
    if chunk is None:
        print('loadfile nil:', rel)
        bad += 1
        continue
    try:
        chunk()
    except Exception as e:
        print('加载失败 %s: %s' % (rel, str(e)[:160]))
        bad += 1
if bad:
    sys.exit(1)

probe = lua.eval(r'''
(function()
  local U = TF_NS.DungeonUI
  local DG = TF_NS.DungeonModule
  local out = {}

  local n = 0
  local _cf = CreateFrame
  CreateFrame = function(...) n = n + 1; return _cf(...) end

  -- ① 首屏
  n = 0
  U:Build()
  out[#out + 1] = "首屏 U:Build() 新建帧 = " .. n

  -- ② 首屏之后，切到其余子页（分帧预热在桩里不跑 ⇒ 首次切页要建）
  local function count(fn)
    n = 0
    fn()
    return n
  end
  out[#out + 1] = "首次切「团本」新建帧 = " .. count(function() U:SwitchSub("Raids") end)
  out[#out + 1] = "二次切「团本」新建帧 = " .. count(function() U:SwitchSub("Raids") end)

  U:SwitchSub("Dungeons")
  out[#out + 1] = "切回「副本」新建帧 = " .. count(function() U:SwitchSub("Dungeons") end)

  -- ③ 首次打开详情页 = 懒建内容 + 4 个重池（离线桩 C_Timer 不跑 ⇒ 手动抽干）
  n = 0
  U:ShowDungeonDetail(TF_NS.DungeonData.dungeons[1])
  local nAfterShow = n
  local guard = 0
  while DG.pendingSteps and #DG.pendingSteps > 0 and guard < 200 do
    guard = guard + 1
    local f = table.remove(DG.pendingSteps, 1)
    pcall(f)
  end
  out[#out + 1] = "首次打开详情页新建帧 = " .. nAfterShow .. "（抽干后累计 " .. n .. "）"

  -- ④ 二次打开同一详情页（应为 0）
  out[#out + 1] = "二次打开详情页新建帧 = " .. count(function()
    U:ShowDungeonDetail(TF_NS.DungeonData.dungeons[1])
  end)

  -- ⑤ 总览页
  out[#out + 1] = "首次切「总览」新建帧 = " .. count(function() U:SetDungeonView("overview") end)
  U:SetDungeonView("list")

  return table.concat(out, "\n")
end)()
''')
print(probe)
