# -*- coding: utf-8 -*-
"""前置任务四项改造（tooltip / 任务注释 / npcid / 徽章）的**动态**回归检查。

为什么另起一个 harness：
  _temp/df_dungeon_check.py 只对 MakeBadge / BadgeTint / ExtQuestRow 做**静态字符串**断言，
  它证明不了：
    ① ExtQuestRow 造出来的伪行第 16 位真的是 npcid（119 条逐条跑）；
    ② 悬停总览「前置」节点走的是 DG.ShowQuestTip（与副本内同一条链路），不再自绘；
    ③ 徽章在**池复用**时不串色（上一轮画成「前置」黄，下一轮变「副本内」青必须重涂）；
    ④ 11 条 npcid 为空的条目点开详情不炸（伪行 q[16] = nil → 回落纯文本）。

用法：python _temp/qa_nt_verify.py（读已 deploy 的 beta 副本，不修改任何业务代码）
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
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
CLIENT_BUILD = int(os.environ.get('TF_BUILD', '16001'))

PASSED, FAILED = [], []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))
    return ok


LUA_SCRIPT = r'''
(function()
  local R = {}
  local function ck(name, cond, extra)
    R[#R + 1] = (cond and "OK" or "FAIL") .. "\t" .. name
      .. (extra ~= nil and ("\t[" .. tostring(extra) .. "]") or "")
  end
  local function badgeCol(b)
    local hc = b and rawget(b, "__huiCard")
    if type(hc) == "table" and type(hc.fill) == "table" and hc.fill[1] then
      local g = hc.fill[1].__huiGlass
      if g and type(g.c) == "table" then return g.c end
    end
    return nil
  end
  local function near(a, b)
    return math.abs((a or -99) - b) < 1e-6
  end
  local ok, err = pcall(function()
    local U = TF_NS.DungeonUI
    local DG = TF_NS.DungeonModule
    local EXT = TF_NS.DungeonQuestExtInfo
    ck("① 主题口径：ns.huiTheme = hui（徽章走圆角填充，才有颜色可断）",
       TF_NS.huiTheme == "hui", TF_NS.huiTheme)
    DG.EnsureCardPool()
    DG.EnsureOverviewBuilt()
    DG.EnsureDetailBuilt()
    DG.EnsureQuestLane()
    local function isNpcRow(f)
      return type(rawget(f, "fs")) == "table" and rawget(f, "__shown") == true
         and rawget(f, "__npc") ~= nil
    end

    -- ================= A/C：伪行结构（119 条逐条） =================
    do
      local n, badRow, bad16, badMid, nNil = 0, 0, 0, 0, 0
      for pid, info in pairs(EXT) do
        n = n + 1
        local row = DG.ExtQuestRow(pid)
        if type(row) ~= "table" then
          badRow = badRow + 1
        else
          if row[1] ~= pid then badRow = badRow + 1 end
          if row[16] ~= info.npcid then bad16 = bad16 + 1 end
          if row[11] ~= info.obj or row[12] ~= info.text or row[17] ~= info.npc then
            badMid = badMid + 1
          end
          if info.npcid == nil then nNil = nNil + 1 end
        end
      end
      ck("① ExtInfo 条目数 = 119", n == 119, n)
      ck("① 每条都能造出伪行且首字段 = 任务 ID（ExtQuestRow 不炸）", badRow == 0, badRow)
      ck("① 伪行第 16 位 == info.npcid（全 119 条逐条比对）", bad16 == 0, bad16)
      ck("① 伪行第 11/12/17 位 = obj / text / npc（未错位）", badMid == 0, badMid)
      ck("① npcid 为空的条目 = 11（回落纯文本的那批）", nNil == 11, nNil)
    end

    -- ================= A：伪行提示框（与副本内同一条 ShowQuestTip） =================
    do
      local owner = CreateFrame("Frame", nil, U.dungeonPage)
      TOOLTIP_LINES = {}
      DG.ShowQuestTip(owner, DG.ExtQuestRow(5727))
      local j = table.concat(TOOLTIP_LINES, " | ")
      ck("A 伪行提示框含「起始：」行（走 ShowQuestTip 不是自绘）",
         j:find("起始：", 1, true) ~= nil, j:sub(1, 90))
      ck("A 起始行 = NPC 名 + #4949（与副本内同款）",
         j:find("萨尔 #4949", 1, true) ~= nil, j:sub(1, 90))
      ck("A 前置行带 #5726", j:find("#5726", 1, true) ~= nil, j:sub(1, 120))
      ck("A 不再出现自绘文案「副本外前置任务」/「点击查看详情」",
         j:find("副本外前置任务", 1, true) == nil
         and j:find("点击查看详情", 1, true) == nil, j:sub(1, 120))
      -- nil-npcid 伪行：不得炸，且不得凭空冒出 #nil
      TOOLTIP_LINES = {}
      local okE = pcall(DG.ShowQuestTip, owner, DG.ExtQuestRow(720))
      ck("A npcid 为空的伪行 ShowQuestTip 不炸", okE == true)
      ck("A npcid 为空的伪行不出现「#nil」", table.concat(TOOLTIP_LINES, " | "):find("#nil", 1, true) == nil)
    end

    -- ================= D：总览徽章（含池复用串色） =================
    local pick, pickB
    do
      local best, bestN, best2, best2N = nil, -1, nil, -1
      for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
        local list = DG.QuestList(dg)
        local inside = {}
        for _, q in ipairs(list) do inside[q[1]] = true end
        local ne = 0
        for _, q in ipairs(list) do
          if q[9] then
            for _, pid in ipairs(q[9]) do
              if not inside[pid] and EXT[pid] then ne = ne + 1 end
            end
          end
        end
        if ne > bestN then best, bestN = dg, ne end
        if ne == 0 and #list > best2N then best2, best2N = dg, #list end
      end
      pick, pickB = best, best2
      ck("D 找到「有副本外前置」的副本（第一轮：前置徽章）",
         pick ~= nil and bestN > 0, tostring(pick and pick.id) .. "/ext=" .. bestN)
      ck("D 找到「无副本外前置」的副本（第二轮：同池改画副本内，验串色）",
         pickB ~= nil, tostring(pickB and pickB.id))
    end

    local function scanNodes()
      local nIn, nExt, nMark, badLab, badSub, badMark, badColIn, badColExt, nCol = 0, 0, 0, 0, 0, 0, 0, 0, 0
      for _, f in ipairs(ALLF) do
        local b = rawget(f, "posB")
        if type(b) == "table" and rawget(f, "__shown") then
          local lab = rawget(b, "lab")
          local sub = rawget(f, "sub")
          local subtree = type(sub) == "table" and rawget(sub, "__text") or nil
          if rawget(f, "__ext") then
            nExt = nExt + 1
            if not lab or rawget(lab, "__text") ~= "前置" then badLab = badLab + 1 end
            local c = badgeCol(b)
            if c then
              nCol = nCol + 1
              if not near(c[1], DG.Q_BADGE_PRE_BG[1]) then badColExt = badColExt + 1 end
            end
            if type(subtree) == "string" and subtree ~= "" then badSub = badSub + 1 end
          elseif rawget(f, "__q") then
            nIn = nIn + 1
            if not lab or rawget(lab, "__text") ~= "副本内" then badLab = badLab + 1 end
            local c = badgeCol(b)
            if c then
              nCol = nCol + 1
              if not near(c[1], DG.Q_BADGE_IN_BG[1]) then badColIn = badColIn + 1 end
            end
            if type(subtree) == "string" and subtree ~= "" then badSub = badSub + 1 end
          else
            nMark = nMark + 1
            if rawget(b, "__shown") then badMark = badMark + 1 end
            if type(subtree) ~= "string" or subtree == "" then badMark = badMark + 1 end
          end
        end
      end
      return nIn, nExt, nMark, badLab, badSub, badMark, badColIn, badColExt, nCol
    end

    do
      U.dungeonQSide = "H"
      U.dungeonQuestSel = nil
      U.dungeonQDetExt = nil
      U:ShowDungeonDetail(pick)
      U.dungeonQView = "overview"
      DungeonsForeverDB = DungeonsForeverDB or {}
      DungeonsForeverDB.dungeon = DungeonsForeverDB.dungeon or {}
      DungeonsForeverDB.dungeon.dungeonQView = "overview"
      U:RenderDungeonQuests()
      local nIn, nExt, nMark, badLab, badSub, badMark, badColIn, badColExt, nCol = scanNodes()
      ck("D 第一轮建出「副本内」节点（>=1）", nIn >= 1, nIn)
      ck("D 第一轮建出「前置」节点（>=1）", nExt >= 1, nExt)
      ck("D 第一轮建出「等级/完成度」标记节点（>=1，且徽章全隐藏）",
         nMark >= 1 and badMark == 0, nMark .. "/bad=" .. badMark)
      ck("D 徽章文案正确（副本内 / 前置）", badLab == 0 and nIn + nExt > 0, badLab)
      ck("D 徽章节点副标题已清空（n.sub:SetText(\"\")）", badSub == 0, badSub)
      ck("D 徽章颜色随类型（前置=黄 / 副本内=青，非创建时定死）",
         badColIn == 0 and badColExt == 0 and nCol > 0,
         "col=" .. nCol .. " badIn=" .. badColIn .. " badExt=" .. badColExt)

      -- 悬停「前置」节点：必须与副本内同一条 ShowQuestTip
      local extNode, inNode
      for _, f in ipairs(ALLF) do
        if type(rawget(f, "posB")) == "table" and rawget(f, "__shown") then
          if rawget(f, "__ext") and not extNode then extNode = f end
          if rawget(f, "__q") and not inNode then inNode = f end
        end
      end
      if extNode then
        TOOLTIP_LINES = {}
        rawget(extNode, "__scripts").OnEnter(extNode)
        local j = table.concat(TOOLTIP_LINES, " | ")
        ck("A 悬停「前置」节点 → ShowQuestTip 伪行（有起始行）",
           j:find("起始：", 1, true) ~= nil, j:sub(1, 90))
        ck("A 悬停「前置」节点不再出自绘文案",
           j:find("副本外前置任务", 1, true) == nil
           and j:find("点击查看详情", 1, true) == nil, j:sub(1, 90))
      end
      if inNode then
        TOOLTIP_LINES = {}
        rawget(inNode, "__scripts").OnEnter(inNode)
        local j = table.concat(TOOLTIP_LINES, " | ")
        ck("A 悬停「副本内」节点同款（起始行）", j:find("起始：", 1, true) ~= nil, j:sub(1, 90))
      end

      -- 第二轮：换成「无副本外前置」的副本 → 同池节点全部改画「副本内」，颜色必须重涂
      U:ShowDungeonDetail(pickB)
      U.dungeonQView = "overview"
      DungeonsForeverDB = DungeonsForeverDB or {}
      DungeonsForeverDB.dungeon = DungeonsForeverDB.dungeon or {}
      DungeonsForeverDB.dungeon.dungeonQView = "overview"
      U:RenderDungeonQuests()
      local nIn2, _, _, badLab2, badSub2, _, badColIn2, _, nCol2 = scanNodes()
      ck("D 第二轮（同池复用）副本内节点仍 >=1", nIn2 >= 1, nIn2)
      ck("D ★★ 池复用不串色：上一轮的「前置」黄被重涂成「副本内」青",
         badColIn2 == 0 and nCol2 > 0,
         "col=" .. nCol2 .. " bad=" .. badColIn2)
      ck("D ★★ 池复用文案不残留（全部「副本内」）", badLab2 == 0, badLab2)
      ck("D ★★ 池复用副标题不残留", badSub2 == 0, badSub2)
    end

    -- ================= B/C：任务详情页（注释 / 起始行 / 空 npcid） =================
    do
      U.dungeonQSide = "H"
      U.dungeonQView = "list"
      U:ShowDungeonDetail(pick)
      U.dungeonQuestSel = nil
      U.dungeonQDetExt = 5727
      U:RenderDungeonQuests()
      local child = U.dungeonQDetChild
      local kid = (child and rawget(child, "__children")) or {}
      local parts = {}
      for _, c in ipairs(kid) do
        if type(rawget(c, "__text")) == "string" then parts[#parts + 1] = rawget(c, "__text") end
      end
      local allTxt = table.concat(parts, "\n")
      ck("B 详情页出现「任务注释」小节", allTxt:find("任务注释", 1, true) ~= nil)
      ck("B 注释正文 = 攻略讲解（_ext_notes 原文命中）",
         allTxt:find("从萨尔处拿到军官的徽章后", 1, true) ~= nil, "")
      ck("B 注释不再是窝窝头剧情 lore",
         allTxt:find("让我们看看你找到的徽章是否有价值", 1, true) == nil, "")
      ck("B 任务说明仍是客户端原文（obj，未被攻略替换）",
         allTxt:find("将军官的徽章交给尼尔鲁·火刃", 1, true) ~= nil, "")

      local npcRow
      for _, f in ipairs(ALLF) do
        if isNpcRow(f) and rawget(f, "__npc") == 4949 then npcRow = f end
      end
      ck("C 起始行 = 可点 NPC 行（__npc = 4949）", npcRow ~= nil)
      local npcTxt = npcRow and rawget(rawget(npcRow, "fs"), "__text") or nil
      ck("C 起始行文案含 NPC#ID",
         type(npcTxt) == "string" and npcTxt:find("#4949", 1, true) ~= nil, npcTxt)
      C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
      if npcRow then rawget(npcRow, "__scripts").OnClick(npcRow) end
      ck("C 点起始行 → 落地图标记（奥格瑞玛 uiMapID 1454）",
         C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1454,
         C_MAP_MARK.wp and C_MAP_MARK.wp.uiMapID)
      ck("C 点起始行 → 同时打开对应地图", C_MAP_MARK.opened == 1454, C_MAP_MARK.opened)
      -- 反向：npcid 为空的条目不该冒出可点行
      U.dungeonQDetExt = 720
      U:RenderDungeonQuests()
      local shownNpc, txt720 = 0, {}
      for _, f in ipairs(ALLF) do
        if isNpcRow(f) then shownNpc = shownNpc + 1 end
      end
      for _, c in ipairs(rawget(U.dungeonQDetChild, "__children") or {}) do
        if type(rawget(c, "__text")) == "string" then txt720[#txt720 + 1] = rawget(c, "__text") end
      end
      local t720 = table.concat(txt720, "\n")
      ck("C npcid 为空（720）→ 无可点行、起始行回落纯文本",
         shownNpc == 0 and t720:find("起始：", 1, true) ~= nil,
         "shownNpc=" .. shownNpc)
    end

    -- ================= 风险：11 条 npcid 为空条目逐条开详情不炸 =================
    do
      local ids = { 720, 739, 1100, 2278, 2933, 2945, 92432, 92434, 95663, 95737, 96391 }
      local bad, badTxt = {}, {}
      for _, pid in ipairs(ids) do
        U.dungeonQDetExt = pid
        local okR, e = pcall(U.RenderDungeonQuests, U)
        if not okR then bad[#bad + 1] = pid .. ":" .. tostring(e):sub(1, 60) end
        local shown = 0
        for _, f in ipairs(ALLF) do
          if isNpcRow(f) then shown = shown + 1 end
        end
        if shown ~= 0 then badTxt[#badTxt + 1] = pid .. "/npcRow=" .. shown end
      end
      ck("风险 11 条 npcid 空条目：详情渲染零异常", #bad == 0, table.concat(bad, " ; "))
      ck("风险 11 条 npcid 空条目：不出现可点 NPC 行", #badTxt == 0, table.concat(badTxt, " ; "))
    end

    -- ================= 全量：119 条 ExtInfo 逐条开详情不炸 =================
    do
      local bad = {}
      for pid in pairs(EXT) do
        U.dungeonQDetExt = pid
        local okR, e = pcall(U.RenderDungeonQuests, U)
        if not okR then bad[#bad + 1] = tostring(pid) .. ":" .. tostring(e):sub(1, 50) end
      end
      ck("全量 119 条 ExtInfo 逐条渲染详情零异常", #bad == 0, table.concat(bad, " ; "))
    end
  end)
  if not ok then
    R[#R + 1] = "FAIL\tLua 断言块抛异常\t[" .. tostring(err):gsub("[\r\n]+", " "):sub(1, 300) .. "]"
  end
  return table.concat(R, "\n")
end)()
'''


def main():
    print('=' * 72)
    print('前置任务四项改造 · 动态回归（TF_BUILD=%d）' % CLIENT_BUILD)
    print('=' * 72)

    toc = open(TOC, encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute(r'''
C_Timer = { After = function(t, fn) if t == 0 then fn(); return end
  SWEEPS = SWEEPS or {}; SWEEPS[#SWEEPS + 1] = { t = t, fn = fn } end }
ALLF = {}
do
  local orig = CreateFrame
  CreateFrame = function(...)
    local f = orig(...)
    if type(f) == "table" then ALLF[#ALLF + 1] = f end
    return f
  end
end''')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('GetCursorPosition = function() return 400, 300 end')
    lua.execute('BG.hui.OnThemeChange = function(fn) end')
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a,b,c,d = orig(...); return a, b, c, %d, e end end' % CLIENT_BUILD)
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
''')
    lua.execute(r'''
do
  local function tipPatch(tt)
    local oldShow, oldHide, oldClear = tt.Show, tt.Hide, tt.ClearLines
    tt.Show = function(self)
      local was = rawget(self, "__shown")
      oldShow(self)
      if was ~= true then
        local s = rawget(self, "__scripts")
        if s and s.OnShow then s.OnShow() end
      end
      return self
    end
    tt.Hide = function(self) oldHide(self) return self end
    tt.SetOwner = function(self, owner) rawset(self, "__owner", owner) return self end
    tt.GetOwner = function(self) return rawget(self, "__owner") end
    tt.GetItem = function(self) return rawget(self, "__itemName"), rawget(self, "__itemLink") end
    tt.ClearLines = function(self)
      rawset(self, "__itemName", nil); rawset(self, "__itemLink", nil)
      return oldClear(self)
    end
  end
  tipPatch(GameTooltip)
  tipPatch(ItemRefTooltip)
end
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
            ck('加载 %s' % rel, False, 'loadfile 返回 nil')
            return 1
        try:
            chunk()
        except Exception as e:
            ck('加载 %s' % rel, False, str(e)[:200])
            return 1

    print('   全部 %d 个 Lua 文件加载完成' % len([f for f in files if not f.lower().endswith('.xml')]))
    lua.execute('if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end')
    lua.execute(r'''
PLAYER_LEVEL = 16
UnitLevel = function() return PLAYER_LEVEL end
if not TF_NS.DungeonUI.built then TF_NS.DungeonUI:Build() end
TF_NS.DungeonUI:SwitchSub("Dungeons")
''')

    out = lua.eval(LUA_SCRIPT)
    for line in (out or '').split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            ck('Lua 侧输出缺制表符', False, line[:200])
            continue
        ck(parts[1], parts[0] == 'OK', parts[2] if len(parts) > 2 else None)

    print('=' * 72)
    print('通过 %d 项 / 失败 %d 项' % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print('  ✗ %s' % f)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
