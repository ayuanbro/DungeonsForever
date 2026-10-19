# -*- coding: utf-8 -*-
"""探针 v3：量「点开一个副本」时，主线程上打了多少次物品数据请求。

判据：GameTooltip:SetItemByID / GetItemInfo / C_Item.RequestLoadItemDataByID 在**同一帧里**
      被调用的次数。真实客户端上每一次「拿不到缓存的物品」都会触发一次同步数据装载，
      成百上千次堆在一帧 = 主线程长时间卡住（Windows 判定无响应就涂灰窗口）。

用法：python _temp/_probe_cost3.py
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

  local C = {}
  local function bump(k) C[k] = (C[k] or 0) + 1 end

  -- 想数谁就包一层（桩里存在的全局/命名空间函数）
  local function wrap(ns, name)
    local t = ns
    if t == nil or type(t[name]) ~= "function" then return false end
    local orig = t[name]
    t[name] = function(...)
      bump(name)
      return orig(...)
    end
    return true
  end

  -- 先建好探针要用的桩（有些桩是插件自己挂的）
  _G.GetItemInfo = function() return nil end
  _G.GetItemInfoInstant = function() return nil end
  C_Item = C_Item or {}
  C_Item.RequestLoadItemDataByID = C_Item.RequestLoadItemDataByID or function() end
  C_Item.GetItemInfo = C_Item.GetItemInfo or function() return nil end

  local _cf = CreateFrame
  CreateFrame = function(...)
    local f = _cf(...)
    local _st = f.SetItemByID
    f.SetItemByID = function(self, ...) bump("SetItemByID"); return _st(self, ...) end
    local _sh = f.SetHyperlink
    f.SetHyperlink = function(self, ...) bump("SetHyperlink"); return _sh(self, ...) end
    return f
  end

  local drainGuard = 0
  local function drain()
    drainGuard = 0
    while DG.pendingSteps and #DG.pendingSteps > 0 and drainGuard < 500 do
      drainGuard = drainGuard + 1
      pcall(table.remove(DG.pendingSteps, 1))
    end
    DG.stepping = false
  end
  local function reset() for k in pairs(C) do C[k] = nil end end
  local function line(tag)
    local keys = {}
    for k in pairs(C) do keys[#keys + 1] = k end
    table.sort(keys)
    local parts = {}
    for _, k in ipairs(keys) do parts[#parts + 1] = k .. "=" .. C[k] end
    out[#out + 1] = string.format("%-30s %s", tag, table.concat(parts, "  "))
  end

  -- 包住探针关心的函数
  wrap(_G, "GetItemInfo")
  wrap(_G, "GetItemInfoInstant")
  wrap(C_Item, "RequestLoadItemDataByID")
  wrap(C_Item, "GetItemInfo")
  local origReq = DG.RequestItem
  DG.RequestItem = function(id, force)
    bump("DG.RequestItem")
    return origReq(id, force)
  end
  local origPre = DG.PrewarmLoot
  DG.PrewarmLoot = function(d)
    bump("DG.PrewarmLoot")
    return origPre(d)
  end

  U:Build(); drain()

  reset()
  U:SwitchSub("Dungeons"); drain()
  line("② 点副本页")

  reset()
  U:ShowDungeonDetail(TF_NS.DungeonData.dungeons[1]); drain()
  line("④ 点开第 1 个副本")

  reset()
  U:ShowDungeonDetail(TF_NS.DungeonData.dungeons[12]); drain()
  line("⑤ 点开第 12 个副本")

  reset()
  U:ShowDungeonDetail(TF_NS.DungeonData.dungeons[25]); drain()
  line("⑥ 点开第 25 个副本")

  -- 掉落总条数有多大
  local nSrc, nItem = 0, 0
  for _, srcs in pairs(TF_NS.DungeonLoot or {}) do
    for i = 1, #srcs do
      nSrc = nSrc + 1
      nItem = nItem + #(srcs[i][5] or {})
    end
  end
  out[#out + 1] = string.format("全库：掉落来源 %d 条，物品条目 %d 条", nSrc, nItem)
  local d1 = TF_NS.DungeonData.dungeons[1]
  local l1 = (TF_NS.DungeonLoot or {})[d1.id] or {}
  local c1 = 0
  for i = 1, #l1 do c1 = c1 + #(l1[i][5] or {}) end
  out[#out + 1] = string.format("第 1 个副本 %s：来源 %d 条，物品 %d 条", d1.id, #l1, c1)

  return table.concat(out, "\n")
end)()
''')
print(probe)
