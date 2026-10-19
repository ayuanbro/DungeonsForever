# -*- coding: utf-8 -*-
"""聚焦审计（2026-10-09 第二轮）：配方页主路径的**搜索过滤**是否还在。

背景：本轮为了消除「点开配方那一瞬间」的卡顿，把 RowsRecipe 的主路径改成了
  `list = PD.RecipeList(math.min(realN, PD.ROW_CAP))`
—— 直接跳过 `PD.SearchFilter`。共享 harness 的动态搜索断言此刻被并行会话的
团本页在途改动（wallLabels nil）提前崩掉、根本跑不到，所以单独立这里验。

判据不是条数，而是**内容**：搜索词 = "轻皮" 时，出现在 PD.specs 里的每一条，
其 名称/副行/材料名 必须**至少有一处**含该子串；反之，原始行里确实命中的那些，
必须都在里面（数量也要对得上）。

只读产品文件，不写任何产品文件。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51  # noqa: E402

FAILS = []


def ck(name, ok, extra=''):
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           ('  [%s]' % extra) if extra != '' else ''))
    if not ok:
        FAILS.append(name)


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) '
                'PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('CTIMER_REF = C_Timer')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = orig(...); return a, b, c, 16001, e end end')
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

    lua.execute(r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  local PD = TF_NS.ProfModule
  -- 挑原始行最多的专业（主路径覆盖面最大）
  local best, bestN = nil, -1
  for _, s in ipairs(TF_NS.ProfData.order or {}) do
    PD.Show(s); PD.SetTab("recipe")
    local d = TF_NS.ProfRecipes and TF_NS.ProfRecipes[s]
    local n = (d and d.rows and #d.rows) or 0
    if n > bestN then best, bestN = s, n end
  end
  PD.bestSlug, PD.bestN = best, bestN
end
''')

    SCRIPT = r'''
(function()
  local PD = TF_NS.ProfModule
  local DGm = TF_NS.ProfHost.DG
  local out = {}
  local function ck(name, ok, extra)
    out[#out + 1] = { name, ok and 1 or 0, extra or "" }
  end
  local function settle()
    DGm.stepping = false
    DGm.pendingSteps = {}
    PUMPS = {}
  end

  PD.sweeping = true
  PD.ROW_SYNC_MAX = 100000        -- 本审计只看「算出来的列表」，不走分帧
  settle()
  PD.Show(PD.bestSlug); PD.SetTab("recipe")

  -- 物品名做成可知的：50 的倍数 -> 轻皮甲片（稀有），其余偶数 -> 秘银锭，奇数 -> 铁扣环
  local _oIN = DGm.ItemName
  DGm.ItemName = function(id)
    id = tonumber(id) or 0
    if id % 50 == 0 then return "轻皮甲片", true end
    if id % 2 == 0 then return "秘银锭", true end
    return "铁扣环", true
  end

  local _rf = TF_NS.EnsureProfRecipes
  if _rf then _rf() end
  local d = TF_NS.ProfRecipes[PD.bestSlug]
  local ROW_CAP = PD.ROW_CAP

  -- 参考实现：对原始行按「名称/副行/材料名」逐字匹配（与 PD.SearchHit 同口径）
  local function refMatch(r, q)
    local nm = tostring(DGm.ItemName(r[2]) or "")
    if nm ~= "" and string.find(string.lower(nm), q, 1, true) then return true end
    local sub = tostring(r[5] or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    for _, m in ipairs(r[12] or {}) do
      local mn = tostring(DGm.ItemName(m[1]) or "")
      if mn ~= "" and string.find(string.lower(mn), q, 1, true) then return true end
    end
    return false
  end

  local function refCount(q)
    local n = 0
    for _, r in ipairs(d.rows or {}) do
      if refMatch(r, q) then n = n + 1 end
    end
    return n
  end

  local function specTexts(s)
    local t = {}
    if s.text and s.text ~= "" then t[#t + 1] = s.text end
    if s.sub and s.sub ~= "" then t[#t + 1] = s.sub end
    for _, m in ipairs(s._mats or {}) do
      local mn = DGm.ItemName(m[1])
      if mn and mn ~= "" then t[#t + 1] = tostring(mn) end
    end
    return t
  end

  -- ★ PD.specs 里除了配方行，还有抬头 / 间距 / 截断提示（PushHead / PushGap /
  --   PushText）—— 它们当然不含搜索词。只对**真正的配方行**验收（有 it = 有物品 id）。
  local function isRecipe(s)
    return s ~= nil and s.it ~= nil and (s.kind == "row" or s.kind == nil)
  end
  local function countRecipes(list)
    local n = 0
    for _, s in ipairs(list or {}) do
      if isRecipe(s) then n = n + 1 end
    end
    return n
  end

  -- ① 空搜索：基线
  PD.searchQ = nil
  PD.Render()
  local baseN = countRecipes(PD.specs)

  -- ② 搜索：逐条验收内容
  local Q = "轻皮"
  PD.searchQ = Q
  PD.Render()
  local got = PD.specs or {}
  local gotN = countRecipes(got)
  local refN = refCount(Q)
  local bad = 0
  local badEx = ""
  for _, s in ipairs(got) do
    if isRecipe(s) then
      local hit = false
      for _, t in ipairs(specTexts(s)) do
        if string.find(string.lower(t), Q, 1, true) then hit = true break end
      end
      if not hit then
        bad = bad + 1
        if badEx == "" then badEx = tostring(s.text) end
      end
    end
  end
  ck('★★ 搜索后列表里的每一条都真的命中（无混入未命中的行）',
     gotN > 0 and bad == 0,
     '配方行 ' .. tostring(gotN) .. ' 条，其中未命中 ' .. tostring(bad)
     .. (badEx ~= "" and ('（例如 ' .. badEx .. '）') or ''))

  local expect = math.min(refN, ROW_CAP)
  ck('★★ 搜索后条数 = min(命中数, ROW_CAP)',
     gotN == expect,
     '显示 ' .. tostring(gotN) .. ' / 期望 ' .. tostring(expect)
     .. '（命中 ' .. tostring(refN) .. '，封顶 ' .. tostring(ROW_CAP) .. '）')

  ck('★★ 搜索确实缩小了列表（不是照样全量）',
     gotN > 0 and gotN < baseN,
     tostring(baseN) .. ' -> ' .. tostring(gotN))

  -- ④ 清空还原
  PD.searchQ = nil
  PD.Render()
  local backN = countRecipes(PD.specs)
  ck('★ 清空搜索词后回到基线条数',
     backN == baseN,
     tostring(baseN) .. ' -> ' .. tostring(backN))

  DGm.ItemName = _oIN
  local o = {}
  for _, e in ipairs(out) do
    o[#o + 1] = e[1] .. "\t" .. tostring(e[2]) .. "\t" .. tostring(e[3])
  end
  return table.concat(o, "\n")
end)()
'''
    try:
        res = lua.eval(SCRIPT)
    except Exception as e:
        ck('Lua 审计段未抛异常', False, str(e)[:300])
        res = None
    if res:
        for line in str(res).split('\n'):
            if line.count('\t') < 2:
                continue
            name, ok, extra = line.split('\t', 2)
            ck(name, ok == '1', extra)

    print('-' * 72)
    print('失败 %d 项' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
