# -*- coding: utf-8 -*-
"""探针 v2：把「点开一个副本」的贴图载入按阶段拆开，并列出最频繁/最可疑的贴图来源。

用法：python _temp/_probe_cost2.py
只读，不改任何文件。
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
  local out = {}

  local nF, nTexStr, nTexNum = 0, 0, 0
  local hist = {}
  local _cf = CreateFrame
  CreateFrame = function(...)
    nF = nF + 1
    local f = _cf(...)
    local _ct = f.CreateTexture
    f.CreateTexture = function(self, ...)
      local t = _ct(self, ...)
      local _st = t.SetTexture
      t.SetTexture = function(s, v)
        if type(v) == "string" then
          nTexStr = nTexStr + 1
          hist[v] = (hist[v] or 0) + 1
        elseif type(v) == "number" then
          nTexNum = nTexNum + 1
          hist["#" .. v] = (hist["#" .. v] or 0) + 1
        end
        return _st(s, v)
      end
      return t
    end
    return f
  end

  local function drain()
    local guard = 0
    while DG.pendingSteps and #DG.pendingSteps > 0 and guard < 500 do
      guard = guard + 1
      pcall(table.remove(DG.pendingSteps, 1))
    end
    DG.stepping = false
  end
  local function reset() nF, nTexStr, nTexNum = 0, 0, 0 end
  local function line(tag)
    out[#out + 1] = string.format("%-34s 帧 %-5d 贴图(路径 %-5d / id %-5d) = %d",
      tag, nF, nTexStr, nTexNum, nTexStr + nTexNum)
  end

  reset(); U:Build(); drain(); line("① 开窗（团本页）")

  reset(); U:SwitchSub("Dungeons"); drain(); line("② 点副本页")

  local d1 = TF_NS.DungeonData.dungeons[1]
  -- 阶段拆解：详情页的每一块单独量
  reset()
  local _ed = DG.EnsureDetailBuilt
  DG.EnsureDetailBuilt = function()
    if U.detailBuilt then return _ed() end
    -- 手动分阶段复现：先量「懒建主体」，再量 4 个块
    return _ed()
  end
  reset(); _ed(); drain()
  line("④ 详情页懒建主体 + 4 块分帧")

  reset(); U:ShowDungeonDetail(d1); drain()
  line("④' ShowDungeonDetail 全集")
  DG.EnsureDetailBuilt = _ed

  -- 明细：谁在大量 SetTexture
  out[#out + 1] = ""
  out[#out + 1] = "── 贴图载入 TOP 25（④' 期间）──"
  local arr = {}
  for k, v in pairs(hist) do arr[#arr + 1] = { k, v } end
  table.sort(arr, function(a, b) return a[2] > b[2] end)
  for i = 1, math.min(25, #arr) do
    out[#out + 1] = string.format("  %-58s x%d", arr[i][1], arr[i][2])
  end

  return table.concat(out, "\n")
end)()
''')
print(probe)
