# -*- coding: utf-8 -*-
"""探针：量每个动作（开窗 / 点副本页 / 开详情 / 切地图页）各建多少帧、纹理、字体串。

用法：python _temp/_probe_cost.py
只读，不改任何文件。给「点副本就卡死」找一个可对比的数字。
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
-- 让开窗默认落在「团本」子页 ⇒ 副本页留给「点副本」这一步去建
DungeonsForeverDB = { dungeon = { subTab = "Raids" }, ui = {} }
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
  local U  = TF_NS.DungeonUI
  local DG = TF_NS.DungeonModule
  local Map = TF_NS.MapModule
  local out = {}

  -- ── 计数器：帧 / 纹理 / 字体串 / 真实贴图路径（SetTexture 传字符串或数字）──
  local nF, nT, nS, nTex = 0, 0, 0, 0
  local _cf = CreateFrame
  CreateFrame = function(...)
    nF = nF + 1
    local f = _cf(...)
    local _ct  = f.CreateTexture
    local _cfs = f.CreateFontString
    f.CreateTexture = function(self, ...)
      nT = nT + 1
      local t = _ct(self, ...)
      local _st = t.SetTexture
      t.SetTexture = function(s, v)
        if type(v) == "string" or type(v) == "number" then nTex = nTex + 1 end
        return _st(s, v)
      end
      return t
    end
    f.CreateFontString = function(self, ...) nS = nS + 1; return _cfs(self, ...) end
    return f
  end

  local function drain()
    local guard = 0
    while DG.pendingSteps and #DG.pendingSteps > 0 and guard < 500 do
      guard = guard + 1
      local ok, err = pcall(table.remove(DG.pendingSteps, 1))
      if not ok then out[#out + 1] = "  [分帧块报错] " .. tostring(err) end
    end
    DG.stepping = false
  end
  local function count(fn)
    nF, nT, nS, nTex = 0, 0, 0, 0
    local ok, err = pcall(fn)
    drain()
    return string.format("帧 %-5d 纹理 %-6d 字体串 %-5d 贴图载入 %-4d%s",
      nF, nT, nS, nTex, ok and "" or ("  [报错] " .. tostring(err):sub(1, 90)))
  end

  out[#out + 1] = "① 开窗 U:Build()（默认落「团本」页）      : " ..
    count(function() U:Build() end)
  out[#out + 1] = "② 首次「点副本」= SwitchSub(Dungeons)  : " ..
    count(function() U:SwitchSub("Dungeons") end)
  out[#out + 1] = "③ 再切一次副本页（应≈0）               : " ..
    count(function() U:SwitchSub("Dungeons") end)

  -- 详情页：先只为第一个副本建壳 + 默认「掉落」页
  local d1 = TF_NS.DungeonData.dungeons[1]
  out[#out + 1] = "④ 首次点开副本（掉落页）+ 分帧跑完     : " ..
    count(function() U:ShowDungeonDetail(d1) end)

  -- 切到「地图」页签（MapUI 在 1.6.0 被重写）
  U.dungeonTab = "map"
  out[#out + 1] = "⑤ 首次切「地图」页签                   : " ..
    count(function() U:RenderDungeonTab() end)
  out[#out + 1] = "⑥ 二次切「地图」页签                   : " ..
    count(function() U:RenderDungeonTab() end)

  -- 换一个副本再开（看是否是「每本一次」的成本）
  local d2 = TF_NS.DungeonData.dungeons[2]
  out[#out + 1] = "⑦ 换一本再开（地图页）                 : " ..
    count(function() U:ShowDungeonDetail(d2) end)

  -- 卡片视图
  out[#out + 1] = "⑧ 切掉落「卡片」视图                   : " ..
    count(function() U:SetLootView("card") end)

  return table.concat(out, "\n")
end)()
''')
print(probe)
