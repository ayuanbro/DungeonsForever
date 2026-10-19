# -*- coding: utf-8 -*-
"""探针：**跨版本**比对「打开插件」与「点开一个副本」的开销（统一口径）。

为什么要这个：1.6.x 加了副本内地图页，并把它挂进「详情预建链」，于是
「点副本」那一帧从「只建本页」变成「本页 + 地图页整页」——用户反馈的
「点副本就卡死」正是这条回归。1.3.1（正式服 AddOns 下的现成版本）**根本没有
地图页**，正好当基线。

口径（两个版本完全一致）：
  · 「同步帧」= U:ShowDungeonDetail(d) 返回那一刻累计新建的对象数
    —— 这就是真机上玩家点下去、主线程交回给游戏的那一帧。
    新版首块已被 C_Timer.After(0, pump) 推迟 ⇒ 同步段只有外壳。
  · 「后续块」= 排在零延迟队列里的回调个数（新版才非零）。

用法：
  python _temp/_probe_vs.py --addon <插件目录> --build <端号> --label <名字>
只读，不改任何文件。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--addon', required=True, help='插件目录（含 DungeonsForever.toc）')
ap.add_argument('--build', type=int, default=16001, help='模拟的客户端端号')
ap.add_argument('--label', default='', help='显示用的版本标签')
ap.add_argument('--only', default='', help='只测这一个副本 id（单副本 = 干净实例：会付详情外壳的钱）')
args = ap.parse_args()

ADDON = os.path.abspath(args.addon)
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
if not os.path.isfile(TOC):
    print('找不到 toc:', TOC)
    sys.exit(2)

toc = open(TOC, encoding='utf-8', errors='replace').read()
toc_ver = ''
for line in toc.splitlines():
    s = line.strip()
    if s.lower().startswith('## version'):
        toc_ver = s.split(':', 1)[1].strip()
files = [l.strip().replace('\\', '/') for l in toc.splitlines()
         if l.strip() and not l.strip().startswith('##')]

print('=' * 78)
print('插件目录 : %s' % ADDON)
print('toc 版本 : %s   （标签：%s）' % (toc_ver, args.label or '-'))
print('模拟端号 : %d' % args.build)
print('=' * 78)

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 - 3660 end')
lua.execute("BG.hui.OnThemeChange = function(fn) end")
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('BG.hui = nil')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('ONLY_ID = %r' % args.only)
lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
            'local a,b,c,d = orig(...); return a,b,c,%d,e end end' % args.build)
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
        print('loadfile nil:', rel)
        bad += 1
        continue
    try:
        chunk()
    except Exception as e:
        print('加载失败 %s: %s' % (rel, str(e)[:200]))
        bad += 1
if bad:
    print('!! 有 %d 个文件没加载成功，下面的数不可信' % bad)

probe = lua.eval(r'''
(function()
  local U  = TF_NS.DungeonUI
  local DG = TF_NS.DungeonModule
  local out = {}
  if not U then return "TF_NS.DungeonUI 不存在（插件没加载？）" end

  local nF, nT, nS, nTex, nItem = 0, 0, 0, 0, 0
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
        if type(v) == "string" then nTex = nTex + 1 end
        return _st(s, v)
      end
      return t
    end
    f.CreateFontString = function(self, ...) nS = nS + 1; return _cfs(self, ...) end
    if f.SetItemByID then
      local _si = f.SetItemByID
      f.SetItemByID = function(s, ...) nItem = nItem + 1; return _si(s, ...) end
    end
    return f
  end
  _G.GetItemInfo = function() return nil end
  _G.GetItemInfoInstant = function() return nil end
  if C_Item == nil then C_Item = {} end
  C_Item.RequestLoadItemDataByID = C_Item.RequestLoadItemDataByID or function() end
  C_Item.GetItemInfo = C_Item.GetItemInfo or function() return nil end

  -- 零延迟回调 = 后续帧；>0 的 = 到货重扫，收起来单列
  local Q, LATER = {}, {}
  C_Timer = { NewTicker = function() return {} end,
              After = function(t, fn)
                if type(fn) ~= "function" then return end
                if not t or t <= 0 then Q[#Q + 1] = fn else LATER[#LATER + 1] = fn end
              end }

  local function flush()
    local g = 0
    while #Q > 0 and g < 20000 do g = g + 1; pcall(table.remove(Q, 1)) end
    for _ = 1, #LATER do table.remove(LATER, 1) end
    if DG.stepping ~= nil then DG.stepping = false end
  end

  local function snap() return nF, nT, nS, nTex, nItem end
  local function zero() nF, nT, nS, nTex, nItem = 0, 0, 0, 0, 0 end

  local function fmt(tag, f, t, s, tex, it)
    return string.format("  %-34s 帧 %-5d 纹理 %-6d 字体串 %-6d 贴图 %-5d 物品取数 %-4d",
      tag, f, t, s, tex, it)
  end

  -- ── ① 开窗 + 进副本页 ──
  zero()
  local okB, errB = pcall(function() U:Build() end)
  local f1, t1, s1, x1, i1 = snap()
  out[#out + 1] = fmt("① U:Build()（开窗）", f1, t1, s1, x1, i1)
    .. (okB and "" or ("  [报错] " .. tostring(errB):sub(1, 90)))
  flush()

  zero()
  local okS, errS = pcall(function() U:SwitchSub("Dungeons") end)
  local f2, t2, s2, x2, i2 = snap()
  out[#out + 1] = fmt("② U:SwitchSub(\"Dungeons\")", f2, t2, s2, x2, i2)
    .. (okS and "" or ("  [报错] " .. tostring(errS):sub(1, 90)))
  flush()

  -- 新版才有：预热 tooltip（不给 NumLines 会让名字收割整条崩）
  if type(DG.RequestItem) == "function" then
    _G.TFItemWarmTipTextLeft1 = {
      GetText = function() return "探针到货名" end,
      GetTextColor = function() return 1, 1, 1 end,
    }
    pcall(DG.RequestItem, 6948, true)
    if DG.__warmTip then DG.__warmTip.NumLines = function() return 1 end end
    flush()
  end

  local byId = {}
  if TF_NS.DungeonData and TF_NS.DungeonData.dungeons then
    for _, d in ipairs(TF_NS.DungeonData.dungeons) do byId[d.id] = d end
  end
  local nDun = 0
  for _ in pairs(byId) do nDun = nDun + 1 end
  out[#out + 1] = string.format("  （本版副本数据 %d 本）", nDun)
  out[#out + 1] = ""

  -- ── ② 点开副本：同步那一帧 ──
  out[#out + 1] = "  ── 点开副本：同步那一帧（= 真机上玩家点下去那一下）──"
  out[#out + 1] = string.format("  %-22s %7s | %6s %7s %7s %7s %6s %6s %7s",
    "副本", "掉落件", "同步帧", "纹理", "字体串", "贴图", "取数", "后续块", "后续帧合计")
  local ids = { "hall_of_thanes", "excavation_wetlands", "the_stockade",
                "blackrock_depths", "scholomance" }
  if ONLY_ID and ONLY_ID ~= "" then ids = { ONLY_ID } end
  local rows = {}
  for _, id in ipairs(ids) do
    local d = byId[id]
    if not d then
      rows[#rows + 1] = string.format("  %-22s （本版数据里没有这本）", id)
    else
      local loot = (TF_NS.DungeonLoot or {})[id] or {}
      local set, nTot = {}, 0
      for i = 1, #loot do
        for _, it in ipairs(loot[i][5] or {}) do set[it[1]] = true end
      end
      for _ in pairs(set) do nTot = nTot + 1 end

      zero()
      local ok, err = pcall(function() U:ShowDungeonDetail(d) end)
      local sf, st, ss, sx, si = snap()
      -- 后续块：逐块跑，累计其成本
      local blocks, bf, bt = 0, 0, 0
      local g = 0
      while #Q > 0 and g < 20000 do
        g = g + 1
        local a, b = nF, nT
        pcall(table.remove(Q, 1))
        blocks = blocks + 1
        bf = bf + (nF - a); bt = bt + (nT - b)
      end
      for _ = 1, #LATER do local fn = table.remove(LATER, 1); pcall(fn) end
      rows[#rows + 1] = string.format("  %-22s %7d | %6d %7d %7d %7d %6d %6d %7d%s",
        id, nTot, sf, st, ss, sx, si, blocks, bf,
        ok and "" or ("  [报错] " .. tostring(err):sub(1, 90)))
    end
  end
  for _, r in ipairs(rows) do out[#out + 1] = r end

  -- 页签数（新版有三态，1.3.1 只有两态）
  out[#out + 1] = ""
  local tabs = 0
  for _ in pairs(U.dungeonTabBtns or {}) do tabs = tabs + 1 end
  out[#out + 1] = string.format("  详情页签按钮 %d 个；U.dungeonTab 当前 = %s",
    tabs, tostring(U.dungeonTab))
  out[#out + 1] = string.format("  地图页模块 ns.MapModule = %s",
    tostring(TF_NS.MapModule ~= nil))
  out[#out + 1] = string.format("  分帧器 DG.PushStep = %s / DG.stepping = %s",
    tostring(type(DG.PushStep) == "function"), tostring(DG.stepping))

  return table.concat(out, "\n")
end)()
''')
print(probe)
