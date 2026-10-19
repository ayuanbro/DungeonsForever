# -*- coding: utf-8 -*-
"""独立冒烟（2026-10-09 需求三）：升级路线行「四档技能色阶条 + 名字右侧来源卡片」。

用户口径：
  「专业升级路线页面，我现在每行还是要显示这个配方的几级变绿、几级变黄」
  → 名字下一行（原来源行）改放四档色阶条（学 / 黄 / 绿 / 灰 + 当前档落点），
    来源压成名字右侧的小卡片（训练师 / 图纸·掉落 / 图纸·商人）。

共享 harness 的动态块被并行会话的在途改动提前崩掉（`wallLabels` 未初始化），
专业页运行时段跑不到 → 本冒烟自建驱动链（Build → Professions → alchemy → leveling）。
只读产品文件、只在内存桩里跑，不写任何产品文件。

用法：
  python _temp/_skillbar_smoke.py                    # 默认打 beta 副本（harness 口径）
  DF_ADDON_ROOT=D:/workspace/DungeonsForever python _temp/_skillbar_smoke.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # 复用 T.STUB / ADDON / TOC
from lupa import lua51

FAILS = []


def ck(name, ok, extra=''):
    tag = 'OK ' if ok else 'FAIL'
    line = '  [%s] %s%s' % (tag, name, ('  [%s]' % extra) if extra != '' else '')
    print(line)
    if not ok:
        FAILS.append(name)


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    build = 16001
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d = orig(...); return a, b, c, %d, e end end' % build)
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "测区" .. tostring(id) end,
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
            print('加载 %s 失败（loadfile nil）' % rel)
            return 1
        try:
            chunk()
        except Exception as e:
            print('加载 %s 抛异常：%s' % (rel, str(e)[:300]))
            return 1
    print('已加载 %d 个 Lua 文件，开始驱动链'
          % len([f for f in files if not f.lower().endswith('.xml')]))

    DRIVER = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  local PD = TF_NS.ProfModule
  PD.Show("alchemy")
  PD.SetTab("leveling")
end
'''
    lua.execute(DRIVER)

    SCRIPT = r'''
(function()
  local PD = TF_NS.ProfModule
  local out = {}
  local function ck(name, ok, extra)
    out[#out + 1] = { name, ok and 1 or 0, extra or "" }
  end

  -- ① 纯函数：四档落点（learn == yellow 的数据是最常见形态）
  ck("★★ LvTier：140 → 第 1 档（橙 · 必升）", PD.LvTier(140, 150, 150, 162, 175) == 1)
  ck("★★ LvTier：160 → 第 2 档（黄 · 大概率）", PD.LvTier(160, 150, 150, 162, 175) == 2)
  ck("★★ LvTier：165 → 第 3 档（绿 · 小概率）", PD.LvTier(165, 150, 150, 162, 175) == 3)
  ck("★★ LvTier：180 → 第 4 档（灰 · 不再提升）", PD.LvTier(180, 150, 150, 162, 175) == 4)
  ck("★★ LvTier：没阈值数据 → nil（不画落点，而不是硬落第 1 档）",
     PD.LvTier(180, nil, nil, nil, nil) == nil)
  ck("★★ LvTier：没当前技能等级 → nil", PD.LvTier(nil, 150, 150, 162, 175) == nil)
  ck("★★ LvTier：learn == yellow 时「必升」档仍存在（150 学 → 落在第 2 档不是第 1）",
     PD.LvTier(150, 150, 150, 162, 175) == 2)

  -- 扫一遍 specs：找一条带阈值、一条带卡片、一条「图纸·商人」
  local iSB, spSB, iCd, spCd, iVd, spVd
  for i = 1, #(PD.specs or {}) do
    local sp = PD.specs[i]
    if sp.kind == "row" and sp.lvstep then
      if not spSB and sp.sbVals then iSB, spSB = i, sp end
      if not spCd and sp.card then iCd, spCd = i, sp end
      if not spVd and sp.card and sp.card.kind == "vendor" then iVd, spVd = i, sp end
    end
  end

  local function vals(sp)
    if not sp or not sp.sbVals then return "无" end
    local t = {}
    for k = 1, 4 do t[k] = tostring(sp.sbVals[k]) end
    return table.concat(t, "/")
  end

  -- ② 色阶条：四段数字逐段对上阈值
  ck("★★ 升级页渲染出带四档阈值的路线行", spSB ~= nil, vals(spSB))
  if spSB then
    local r = (PD.rows or {})[iSB]
    ck("行池与 specs 同序（拿到同一行）", r ~= nil)
    if r then
      ck("★ 色阶条段数正好 4（不多不少）", #r.__sbTx == 4)
      local okTx, okBg, shown = true, true, true
      for k = 1, 4 do
        local want = spSB.sbVals[k] and tostring(spSB.sbVals[k]) or ""
        if not r.__sbTx[k] or r.__sbTx[k].__text ~= want then okTx = false end
        if not r.__sbBg[k] then okBg = false end
        if r.__sbTx[k] and r.__sbTx[k].__shown ~= true then shown = false end
      end
      ck("★★ 四段数字逐段对上配方阈值（学 / 黄 / 绿 / 灰，原样四个都显示）", okTx,
         r.__sbTx[1].__text .. " " .. r.__sbTx[2].__text .. " "
         .. r.__sbTx[3].__text .. " " .. r.__sbTx[4].__text)
      ck("★★ 四段色底纹理齐备且数字在显示态", okBg and shown)
      ck("★ 落点竖线对象已建（本行技能区间两端各一根）",
         r.__sbPin ~= nil and r.__sbPin[1] ~= nil and r.__sbPin[2] ~= nil
         and r.__sbPin[3] == nil,
         "区间=" .. tostring(spSB.sbLo) .. "–" .. tostring(spSB.sbHi))
      ck("★★ 四条数字都不是空串（四档阈值齐备）",
         r.__sbTx[1].__text ~= "" and r.__sbTx[2].__text ~= ""
         and r.__sbTx[3].__text ~= "" and r.__sbTx[4].__text ~= "")
    end
  end

  -- ③ 来源卡片：显示态 + 文案 + 悬停明细
  ck("★★ 升级页渲染出来源卡片", spCd ~= nil,
     spCd and (tostring(spCd.card.kind) .. " / " .. tostring(spCd.card.text)) or "未找到")
  if spCd then
    local r = (PD.rows or {})[iCd]
    local cz = r and r.__cardZone
    ck("★★ 卡片热区显示且文字 = 卡片文案（名字列右缘对齐）",
       cz and cz.__shown == true and r.__cardTx.__text == spCd.card.text,
       tostring(r and r.__cardTx and r.__cardTx.__text))
    ck("★★ 卡片热区挂悬停明细 __tipLines", cz and cz.__tipLines and #cz.__tipLines > 0,
       tostring(cz and cz.__tipLines and #cz.__tipLines))
    ck("★ 卡片热区显式转发滚轮（压在卡上也滚得动）",
       cz and cz.__scripts and cz.__scripts.OnMouseWheel ~= nil)
    if cz and cz.__scripts and cz.__scripts.OnEnter then
      TOOLTIP_LINES = {}
      cz.__scripts.OnEnter(cz)
      local joined = table.concat(TOOLTIP_LINES, " | ")
      ck("★★ 悬停来源卡片 → 出文字提示框（图纸名 / 掉落处数 / 商人明细）",
         #TOOLTIP_LINES > 0, joined)
    end
    if spCd.card.fid then
      ck("★★ 图纸卡片挂 __it（Shift 点击发图纸物品链接）",
         cz and cz.__it and cz.__it[1] == spCd.card.fid,
         tostring(cz and cz.__it and cz.__it[1]))
    end
  end

  -- ④ 「图纸·商人」卡片：点击落图
  do
    local has = spVd ~= nil
    ck("★ 本页存在「图纸·商人」卡片（点击落图口径可测）", has,
       has and tostring(spVd.card.text) or "本页无（条件覆盖，不算失败）")
    if has then
      local r = (PD.rows or {})[iVd]
      local cz = r and r.__cardZone
      ck("★★ 商人卡片挂自定义点击 __act", cz ~= nil and type(cz.__act) == "function")
      if cz and cz.__scripts and cz.__scripts.OnClick and cz.__act then
        local _marked = 0
        local _om = PD.MarkVendorLoc
        PD.MarkVendorLoc = function(loc) _marked = _marked + 1 end
        cz.__scripts.OnClick(cz, "LeftButton")
        PD.MarkVendorLoc = _om
        ck("★★ 点击商人卡片 → 触发 PD.MarkVendorLoc（落图链路）", _marked == 1,
           tostring(_marked))
      else
        ck("★★ 点击商人卡片 → 触发 PD.MarkVendorLoc（落图链路）", false, "无 __act")
      end
      if cz and cz.__scripts and cz.__scripts.OnEnter then
        TOOLTIP_LINES = {}
        cz.__scripts.OnEnter(cz)
      end
      local joined = table.concat(TOOLTIP_LINES or {}, " | ")
      ck("★★ 商人卡片悬停文案含「点击：在地图上标记该 NPC」",
         joined:find("地图", 1, true) ~= nil, joined)
    end
  end

  -- ⑤ 切页：行池跨页复用，色阶条与卡片都要收干净
  PD.SetTab("overview")
  do
    local _sb, _cd = 0, 0
    for _, r in ipairs(PD.rows or {}) do
      if r.__shown ~= false then
        if r.__cardZone and r.__cardZone.__shown == true then _cd = _cd + 1 end
        for k = 1, 4 do
          if r.__sbTx and r.__sbTx[k] and r.__sbTx[k].__shown == true then _sb = _sb + 1 end
        end
      end
    end
    ck("★★ 切页后无遗留色阶条 / 来源卡片热区（行池复用不许吞鼠标）",
       _sb == 0 and _cd == 0, "段=" .. tostring(_sb) .. " 卡片=" .. tostring(_cd))
  end

  -- ⑥ 往返重渲染零新建帧（先预热：让行池长到三页的最大行数，
  --    否则测到的是「行池生长」而不是「重渲染」）
  PD.SetTab("leveling")
  do
    PD.SetTab("overview")
    PD.SetTab("recipe")
    PD.SetTab("leveling")
    local _cf = CreateFrame
    local _n = 0
    CreateFrame = function(...) _n = _n + 1; return _cf(...) end
    PD.SetTab("overview")
    PD.SetTab("recipe")
    PD.SetTab("leveling")
    CreateFrame = _cf
    ck("★★ 升级页往返重渲染零新建帧（色阶条 / 卡片随行池一次建好）", _n == 0, _n)
  end

  -- ⑦ 两根竖线 = 本行技能区间两端，**起点向下吸 / 终点向上吸到交界**（用户 2026-10-09 十三轮）
  do
    -- ⑦-1 纯函数：用户第二个例子（阈值 55/85/100/115，区间 85 – 106）
    --   用户原话：「第二根竖线因为 106 已经大于 100 了，那么第二根竖线就要放在 100 的右边」
    --   + 「落在 100 和 115 的交界处，a 大于 85 且小于 100 则落在 55 和 85 交界处」
    ck("★★ SBValPos：85 → 0.25（起点向下吸到已跨过的 85 = 黄段左交界）",
       PD.SBValPos(85, 55, 85, 100, 115) == 0.25, tostring(PD.SBValPos(85, 55, 85, 100, 115)))
    ck("★★ SBValPos：106 → 0.75（终点向上吸：>100 ⇒ 下一道交界 115 = 灰段左交界）",
       PD.SBValPos(106, 55, 85, 100, 115, true) == 0.75,
       tostring(PD.SBValPos(106, 55, 85, 100, 115, true)))
    -- ⑦-1b 用户第一个例子（阈值 1/30/45/60，区间 36 – 45）仍然成立
    local x36 = PD.SBValPos(36, 1, 30, 45, 60)
    local x45 = PD.SBValPos(45, 1, 30, 45, 60, true)
    ck("★★ SBValPos：36 → 0.25（起点向下吸到已跨过的 30）",
       x36 ~= nil and math.abs(x36 - 0.25) < 1e-9, tostring(x36))
    ck("★★ SBValPos：45 → 0.50（终点向上吸，正好压在 45）",
       x45 ~= nil and math.abs(x45 - 0.50) < 1e-9, tostring(x45))
    ck("★★ 两根线是分开的（36/85 在 45/106 左边，不是叠在一起）",
       x36 ~= nil and x45 ~= nil and x36 < x45, tostring(x36) .. " < " .. tostring(x45))
    -- ⑦-2 两根线都只可能停在 0 / 0.25 / 0.50 / 0.75 四处
    ck("★★ 吸附口径：两根线各自落在 0 / 0.25 / 0.50 / 0.75（只停四处，不段内插值）",
       PD.SBValPos(10, 1, 30, 45, 60) == 0.00
       and PD.SBValPos(35, 1, 30, 45, 60) == 0.25
       and PD.SBValPos(40, 1, 30, 45, 60, true) == 0.50
       and PD.SBValPos(70, 1, 30, 45, 60, true) == 0.75)
    -- ⑦-2b 起点向下吸 / 终点向上吸：同一档的两端吸向相反两侧
    ck("★★ 起点向下 / 终点向上（30 起 ⇒ 0.25；40 终 ⇒ 0.50；同一档内两者分居交界两侧）",
       PD.SBValPos(30, 1, 30, 45, 60) == 0.25 and PD.SBValPos(44, 1, 30, 45, 60) == 0.25
       and PD.SBValPos(30, 1, 30, 45, 60, true) == 0.25
       and PD.SBValPos(44, 1, 30, 45, 60, true) == 0.50)
    -- ⑦-2c 边界：起点在最低阈值之下 ⇒ 0；终点超过最高阈值 ⇒ 0.75（贴右缘）
    ck("★★ 边界：下限 <1 起点吸到 0.00；终点 >60 吸到 0.75",
       PD.SBValPos(0.5, 1, 30, 45, 60) == 0.00
       and PD.SBValPos(999, 1, 30, 45, 60, true) == 0.75
       and PD.SBValPos(999, 1, 30, 45, 60) == 0.75)
    ck("★★ 没阈值 / 没等级 → nil（不硬落）",
       PD.SBValPos(36, nil, nil, nil, nil) == nil and PD.SBValPos(nil, 1, 30, 45, 60) == nil
       and PD.SBValPos(nil, 1, 30, 45, 60, true) == nil)
    -- ⑦-4 learn == yellow 零跨度（150/150/162/175）：向上吸取最小 ≥b 的阈值
    ck("★★ learn == yellow 零跨度照常吸附（起点 150 → 0.25；终点 150 → 0.25，不出 nan）",
       PD.SBValPos(150, 150, 150, 162, 175) == 0.25
       and PD.SBValPos(150, 150, 150, 162, 175, true) == 0.25,
       tostring(PD.SBValPos(150, 150, 150, 162, 175)) .. " / "
       .. tostring(PD.SBValPos(150, 150, 150, 162, 175, true)))
    -- ⑦-5 实测：页面里每行都算出两根线，且都在四档位点上、左 ≤ 右
    PD.SetTab("recipe")
    PD.SetTab("leveling")
    local _n, _pair, _bad, _snap = 0, 0, 0, 0
    for i = 1, #(PD.specs or {}) do
      local sp = PD.specs[i]
      if sp.kind == "row" and sp.lvstep and sp.sbVals then
        _n = _n + 1
        local a = PD.SBValPos(sp.sbLo, sp.sbVals[1], sp.sbVals[2], sp.sbVals[3], sp.sbVals[4])
        local b = PD.SBValPos(sp.sbHi, sp.sbVals[1], sp.sbVals[2], sp.sbVals[3], sp.sbVals[4], true)
        if a and b then
          _pair = _pair + 1
          if not (a <= b) then _bad = _bad + 1 end
          if a * 4 == math.floor(a * 4) and b * 4 == math.floor(b * 4) then _snap = _snap + 1 end
        end
      end
    end
    ck("★★ 实测本页每行都算出两根线（起点向下 / 终点向上；左 ≤ 右、都吸附在四档位点上）",
       _n > 0 and _pair == _n and _bad == 0 and _snap == _n,
       tostring(_pair) .. "/" .. tostring(_n) .. " 对，逆序 " .. tostring(_bad)
       .. "，吸附 " .. tostring(_snap))
  end

  -- ⑦b 有「已学专业」数据时：行池仍拿到本行区间（sbLo / sbHi 非 nil）
  do
    local _om = PD.ProfLearned
    PD.ProfLearned = function() return { alchemy = { cur = 60, max = 300 } } end
    PD.SetTab("recipe")
    PD.SetTab("leveling")
    local _n = 0
    for i = 1, #(PD.specs or {}) do
      local sp = PD.specs[i]
      if sp.kind == "row" and sp.lvstep and sp.sbVals
         and sp.sbLo ~= nil and sp.sbHi ~= nil then
        _n = _n + 1
      end
    end
    PD.ProfLearned = _om
    ck("★★ 有当前技能等级时行池仍带本行区间端点（sbLo / sbHi 非 nil）", _n > 0, tostring(_n))
  end

  return out
end)()
'''
    res = lua.eval(SCRIPT)
    for i in range(1, len(res) + 1):
        item = res[i]
        ck(item[1], item[2] == 1, item[3])

    print('=' * 56)
    print('冒烟完成：失败 %d 条' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
