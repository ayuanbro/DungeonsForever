# -*- coding: utf-8 -*-
"""探针 v4：量「**单帧**里打了多少次物品数据请求」（真正的卡死判据）。

v3 数的是「打开一个副本一共打了几次」——分帧只改变「摊在哪几帧」，总量不变，
所以 v3 的数看不出分帧效果。这里把账按**帧**记：C_Timer.After(0, …) 排队的回调
（DG.RunSteps 的 pump）逐个手工执行 = 一帧；统计每一帧内的 SetItemByID /
DG.RequestItem 次数，取最大值。

判据：真机上 tooltip 渲染一个「客户端没缓存」的物品会触发一次**同步装载**，
一帧里几十上百次 = 主线程卡住数秒 ⇒ Windows 判定无响应、整窗涂灰。
修复目标：最坏那一帧的次数从「整个副本的掉落件数」降到「一个分片」。

用法：python _temp/_probe_frame.py
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

  local function wrap(ns, name)
    local t = ns
    if t == nil or type(t[name]) ~= "function" then return false end
    local orig = t[name]
    t[name] = function(...) bump(name); return orig(...) end
    return true
  end

  _G.GetItemInfo = function() return nil end
  _G.GetItemInfoInstant = function() return nil end
  C_Item = C_Item or {}
  C_Item.RequestLoadItemDataByID = C_Item.RequestLoadItemDataByID or function() end
  C_Item.GetItemInfo = C_Item.GetItemInfo or function() return nil end

  local _cf = CreateFrame
  CreateFrame = function(...)
    local f = _cf(...)
    if f and f.SetItemByID then
      local _st = f.SetItemByID
      f.SetItemByID = function(self, ...) bump("SetItemByID"); return _st(self, ...) end
    end
    return f
  end

  -- ★ 零延迟回调入队（= 后续帧）；>0 的延迟收进 LATER（= DG.ScheduleNameSweep 的
  --   0.5/1.5/4/9 秒「到货重扫」），测完预热帧之后再**按原顺序**当作后续帧重放。
  local Q, LATER = {}, {}
  C_Timer = { NewTicker = function() return {} end, After = function(t, fn)
    if type(fn) ~= "function" then return end
    if not t or t <= 0 then Q[#Q + 1] = fn else LATER[#LATER + 1] = fn end
  end }

  local origReq = DG.RequestItem
  DG.RequestItem = function(id, force) bump("DG.RequestItem"); return origReq(id, force) end

  -- 收割链路记账（看清楚 sweeps 到底干了多少活）
  local harvestN, sweepN = 0, 0
  if type(DG.HarvestTipName) == "function" then
    local oh = DG.HarvestTipName
    DG.HarvestTipName = function(id) harvestN = harvestN + 1; return oh(id) end
  end
  if type(DG.SweepMissingNames) == "function" then
    local os2 = DG.SweepMissingNames
    DG.SweepMissingNames = function(...) sweepN = sweepN + 1; return os2(...) end
  end
  local function poolStat()
    local p = U.dungeonDetailPool and U.dungeonDetailPool.item or {}
    local n, un = #p, 0
    for i = 1, n do if not p[i].__named then un = un + 1 end end
    return n, un
  end

  local function reset() for k in pairs(C) do C[k] = nil end end

  -- 逐帧跑完：把「同步那一段」算第 1 帧，之后每个排队回调 = 一帧。
  -- 同时按帧记 keys 里每个计数器的增量，返回 (帧数, 最坏帧, 总数)。
  local function measure(keys, runFirst)
    local prev, maxs, tots = {}, {}, {}
    for _, k in ipairs(keys) do prev[k] = 0; maxs[k] = 0; tots[k] = 0 end
    local frames = 0
    local function tick()
      frames = frames + 1
      for _, k in ipairs(keys) do
        local cur = C[k] or 0
        local d = cur - prev[k]
        prev[k] = cur
        tots[k] = cur
        if d > maxs[k] then maxs[k] = d end
      end
    end
    runFirst()
    tick()                                  -- 第 1 帧：打开详情时同步跑掉的那一段
    local guard = 0
    while #Q > 0 and guard < 20000 do
      guard = guard + 1
      pcall(table.remove(Q, 1))
      tick()
    end
    -- 再把「到货重扫」按原顺序逐帧重放（真实时序上它们排在预热之后）
    for _ = 1, #LATER do
      local fn = table.remove(LATER, 1)
      pcall(fn)
      tick()
    end
    guard = 0
    while #Q > 0 and guard < 20000 do
      guard = guard + 1
      pcall(table.remove(Q, 1))
      tick()
    end
    return frames, maxs, tots
  end

  wrap(_G, "GetItemInfo")
  wrap(_G, "GetItemInfoInstant")
  wrap(C_Item, "RequestLoadItemDataByID")

  -- 开窗 + 进副本页（先把一次性开销走掉，不干扰逐副本测量）
  local function flushQ()
    local g = 0
    while #Q > 0 and g < 20000 do g = g + 1; pcall(table.remove(Q, 1)) end
    for _ = 1, #LATER do table.remove(LATER, 1) end
    DG.stepping = false
  end
  U:Build(); flushQ()
  U:SwitchSub("Dungeons"); flushQ()

  -- 隐藏 tooltip 的名字读取要能用（真机由 GameTooltip 模板提供；桩里得补）：
  --   不补的话 tip:NumLines() 会抛错 ⇒ HarvestTipName 中断 ⇒ 收割链整条崩，
  --   探针就会误报「收割几乎没干活」。
  _G.TFItemWarmTipTextLeft1 = {
    GetText = function() return "探针到货名" end,
    GetTextColor = function() return 1, 1, 1 end,
  }
  DG.RequestItem(6948, true)         -- 把懒建的预热 tooltip 造出来
  if DG.__warmTip then
    DG.__warmTip.NumLines = function() return 1 end
  end
  flushQ()

  local ids = { "hall_of_thanes", "blackrock_depths", "scholomance" }
  local byId = {}
  for _, d in ipairs(TF_NS.DungeonData.dungeons) do byId[d.id] = d end

  local chunk = DG.ITEM_WARM_CHUNK
  out[#out + 1] = string.format("分片大小 DG.ITEM_WARM_CHUNK = %s", tostring(chunk))
  out[#out + 1] = string.format("%-18s %6s %5s | %8s %8s %7s | %8s %7s %7s",
    "副本", "掉落件", "帧数", "请求件总", "最坏帧", "最坏帧率", "取数总", "最坏帧", "最坏帧率")
  out[#out + 1] = string.format("%-18s %6s %5s | %8s %8s %7s | %8s %7s %7s",
    "", "", "", "RequestItem", "", "", "SetItemByID", "", "")

  for _, id in ipairs(ids) do
    local d = byId[id]
    if d then
      local loot = (TF_NS.DungeonLoot or {})[id] or {}
      local ids2, nItem = {}, 0
      for i = 1, #loot do
        for _, it in ipairs(loot[i][5] or {}) do ids2[it[1]] = true end
      end
      for _ in pairs(ids2) do nItem = nItem + 1 end

      reset()
      local h0, s0 = harvestN, sweepN
      local nf, mx, tot = measure({ "DG.RequestItem", "SetItemByID" },
        function() U:ShowDungeonDetail(d) end)
      local np, nun = poolStat()
      out[#out + 1] = string.format("%-18s %6d %5d | %8d %8d %6d%% | %8d %7d %6d%%",
        id, nItem, nf,
        tot["DG.RequestItem"], mx["DG.RequestItem"], math.floor(mx["DG.RequestItem"] * 100 / (nItem > 0 and nItem or 1)),
        tot["SetItemByID"], mx["SetItemByID"], math.floor(mx["SetItemByID"] * 100 / (nItem > 0 and nItem or 1)))
      out[#out + 1] = string.format("    └ 卡池 %d 张 / 仍未命名 %d；收割 %d 次（SweepMissingNames %d 次）",
        np, nun, harvestN - h0, sweepN - s0)
    else
      out[#out + 1] = "找不到副本 " .. id
    end
  end

  return table.concat(out, "\n")
end)()
''')
print(probe)
