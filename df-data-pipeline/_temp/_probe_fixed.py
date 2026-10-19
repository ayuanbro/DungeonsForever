# -*- coding: utf-8 -*-
"""探针：把「点开一个副本」的成本**按块拆开**，验证「固定开销 vs 数据量」假设。

用户质疑：挖掘场（掉落仅 10 件）没什么数据也会卡死 —— 说明成本不随数据量走。
本探针把 ShowDungeonDetail 的每个懒建块单独记账（帧/纹理/字体串/取数调用），
再拿一个数据量大的副本做对照，看「首开」与「次开」的差。

做法：把 DG.PushStep 换成「只订不排」，于是 ShowDungeonDetail 只跑外壳；
随后逐个取出缓冲里的块，每块单独数一次。

用法：python _temp/_probe_fixed.py
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
  local out = {}

  -- ── 计数器 ──
  local nF, nT, nS, nTex = 0, 0, 0, 0
  local nItem, nSpell = 0, 0
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
    if f.SetItemByID then
      local _si = f.SetItemByID
      f.SetItemByID = function(s, ...) nItem = nItem + 1; return _si(s, ...) end
    end
    if f.SetSpellByID then
      local _ss = f.SetSpellByID
      f.SetSpellByID = function(s, ...) nSpell = nSpell + 1; return _ss(s, ...) end
    end
    return f
  end
  _G.GetItemInfo = function() return nil end
  _G.GetItemInfoInstant = function() return nil end

  -- ── PushStep 换成「只订不排」：ShowDungeonDetail 只跑外壳，块留给我逐个称重 ──
  local BUF = {}
  DG.PushStep = function(fn) BUF[#BUF + 1] = fn end

  -- C_Timer：零延迟的收进 Q（预热续帧），>0 的收进 LATER（到货重扫）
  local Q, LATER = {}, {}
  C_Timer = { NewTicker = function() return {} end, After = function(t, fn)
    if type(fn) ~= "function" then return end
    if not t or t <= 0 then Q[#Q + 1] = fn else LATER[#LATER + 1] = fn end
  end }

  local function nameOf(fn)
    if fn == DG.EnsureCardPool   then return "EnsureCardPool（boss 卡池 29 张）" end
    if fn == DG.EnsureQuestLane  then return "EnsureQuestLane（任务双栏）" end
    if fn == DG.EnsureGuideLane  then return "EnsureGuideLane（攻略栏）" end
    if fn == DG.EnsureMapPage    then return "EnsureMapPage（MapUI.Build 整页）" end
    if fn == DG.SweepMissingNames then return "SweepMissingNames（名字收割分片）" end
    -- ★ 2026-10-03 第四刀：地图页自身拆成 4 个重池块 + 收尾
    local MM = TF_NS.MapModule
    if MM then
      if fn == MM.EnsurePins     then return "MapUI ①钉点池 16" end
      if fn == MM.EnsureListRows then return "MapUI ②首领行池 30" end
      if fn == MM.EnsureBlocks   then return "MapUI ③三张分组卡" end
      if fn == MM.EnsureSideRows then return "MapUI ④掉落30+技能8" end
      if fn == MM.EnsureFinal    then return "MapUI ⑤收尾+补渲染" end
    end
    return "预热分片 warmChunk（6 件）"
  end

  local function fmt(tag)
    return string.format("  %-36s 帧 %-5d 纹理 %-6d 字体串 %-5d 贴图 %-5d 物品取数 %-4d 法术取数 %-3d",
      tag, nF, nT, nS, nTex, nItem, nSpell)
  end
  local function count(fn, tag)
    nF, nT, nS, nTex, nItem, nSpell = 0, 0, 0, 0, 0, 0
    local ok, err = pcall(fn)
    out[#out + 1] = fmt(tag) .. (ok and "" or ("  [报错] " .. tostring(err):sub(1, 80)))
    return ok
  end

  local function flush()
    local g = 0
    while #Q > 0 and g < 20000 do g = g + 1; pcall(table.remove(Q, 1)) end
    for _ = 1, #LATER do table.remove(LATER, 1) end
    for _ = 1, #BUF do table.remove(BUF, 1) end
    DG.stepping = false
  end

  local byId = {}
  for _, d in ipairs(TF_NS.DungeonData.dungeons) do byId[d.id] = d end
  -- ★ 隐藏 tooltip 的名字读取要能用（真机由 GameTooltip 模板提供；桩里得补）：
  --   不补的话 tip:NumLines() 抛错 ⇒ HarvestTipName 中断 ⇒ 收割链整条崩，
  --   探针会误报「到货重扫几乎没干活」（本轮真被坑了一次）。
  _G.TFItemWarmTipTextLeft1 = {
    GetText = function() return "探针到货名" end,
    GetTextColor = function() return 1, 1, 1 end,
  }
  DG.RequestItem(6948, true)
  if DG.__warmTip then DG.__warmTip.NumLines = function() return 1 end end
  flush()
  local LOW  = byId["excavation_wetlands"]
  local HIGH = byId["scholomance"]

  local function lootN(id)
    local loot = (TF_NS.DungeonLoot or {})[id] or {}
    local set, n = {}, 0
    for i = 1, #loot do
      for _, it in ipairs(loot[i][5] or {}) do set[it[1]] = true end
    end
    for _ in pairs(set) do n = n + 1 end
    return n, #loot
  end

  out[#out + 1] = "=== 阶段成本（帧/纹理/字体串/贴图 = 建帧成本；取数 = 真机同步装载的嫌疑口）==="
  count(function() U:Build() end, "① 开窗 U:Build()")
  flush()
  count(function() U:SwitchSub("Dungeons") end, "② 首次进「副本」子页（35 行列表）")
  flush()

  local nLow, sLow = lootN("excavation_wetlands")
  out[#out + 1] = string.format("")
  out[#out + 1] = string.format("=== 首次点开【挖掘场】= 10 件掉落 / 4 个来源 ===")

  -- 外壳（点击那一帧同步跑的）
  count(function() U:ShowDungeonDetail(LOW) end, "③ 详情外壳（点击帧）")

  -- 逐个称重懒建块
  local guard = 0
  while #BUF > 0 and guard < 40 do
    guard = guard + 1
    local fn = table.remove(BUF, 1)
    local nm = nameOf(fn)
    count(fn, "④ " .. nm)
  end
  -- 预热续帧 + 到货重扫
  guard = 0
  while #Q > 0 and guard < 60 do
    guard = guard + 1
    count(table.remove(Q, 1), "⑤ 预热续帧")
  end
  guard = 0
  while #BUF > 0 and guard < 40 do
    guard = guard + 1
    count(table.remove(BUF, 1), "⑤ 续帧里的块")
  end
  for _ = 1, #LATER do
    local fn = table.remove(LATER, 1)
    count(fn, "⑥ 到货重扫 SweepMissingNames")
  end
  guard = 0
  while #Q > 0 and guard < 60 do
    guard = guard + 1
    count(table.remove(Q, 1), "⑥ 重扫续帧")
  end
  guard = 0
  while #BUF > 0 and guard < 40 do
    guard = guard + 1
    count(table.remove(BUF, 1), "⑥ 重扫里的块")
  end

  -- 「地图」页签（用户上次就停在这一页 ⇒ /reload 后点开副本会直接渲染地图页）
  out[#out + 1] = ""
  out[#out + 1] = "=== 地图页签（1.6.0 重写；第四刀后 = 外壳同步 + 四个重池逐帧）==="
  U.dungeonTab = "map"
  count(function() U:RenderDungeonTab() end, "⑦ 点「地图」页签那一帧（只建外壳 + 铺瓦片）")
  guard = 0
  while #BUF > 0 and guard < 40 do
    guard = guard + 1
    local fn = table.remove(BUF, 1)
    count(fn, "⑦b " .. nameOf(fn))
  end
  count(function() U:RenderDungeonTab() end, "⑧ 二次渲染地图页（已建，应≈0）")

  -- 对照：数据量大的副本「二次开」（池已建好 ⇒ 只付本副本自己的行）
  out[#out + 1] = ""
  local nHigh, sHigh = lootN("scholomance")
  out[#out + 1] = string.format("=== 对照：点开【通灵学院】= 292 件掉落 / %d 个来源（池已建好）===", sHigh)
  count(function() U:ShowDungeonDetail(HIGH) end, "⑨ 通灵学院外壳")
  guard = 0
  while #BUF > 0 and guard < 40 do
    guard = guard + 1
    local fn = table.remove(BUF, 1)
    count(fn, "⑨ " .. nameOf(fn))
  end
  guard = 0
  while #Q > 0 and guard < 60 do
    guard = guard + 1
    count(table.remove(Q, 1), "⑨ 预热续帧")
  end
  guard = 0
  while #BUF > 0 and guard < 40 do
    guard = guard + 1
    count(table.remove(BUF, 1), "⑨ 续帧里的块")
  end

  out[#out + 1] = ""
  out[#out + 1] = string.format("掉落件数：挖掘场 %d（%d 来源） / 通灵学院 %d（%d 来源）", nLow, sLow, nHigh, sHigh)
  out[#out + 1] = string.format("池上限常量：卡池 LOOT_CARD_MAX=%s / 地图钉点 MAX_PINS=%s / 首领行 MAX_LIST=%s / 掉落行 MAX_LOOT=%s / 技能行 MAX_SKILL=%s / 楼层 MAX_LAYERS=%s",
    tostring(DG.LOOT_CARD_MAX), tostring(TF_NS.MapModule and TF_NS.MapModule.MAX_PINS),
    tostring(TF_NS.MapModule and TF_NS.MapModule.MAX_LIST), tostring(TF_NS.MapModule and TF_NS.MapModule.MAX_LOOT),
    tostring(TF_NS.MapModule and TF_NS.MapModule.MAX_SKILL), tostring(TF_NS.MapModule and TF_NS.MapModule.MAX_LAYERS))
  return table.concat(out, "\n")
end)()
''')
print(probe)
