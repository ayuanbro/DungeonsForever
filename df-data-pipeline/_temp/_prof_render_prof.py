# -*- coding: utf-8 -*-
"""渲染帧剖析（2026-10-09）：点开配方页那一瞬间到底在同步算什么。

背景：行帧已经分帧了（`PD.__pendRows` + `DG.Gate`），可用户实机仍报「点配方那一
瞬间有卡顿」⇒ 卡的不在「建行帧」，在 `PD.Render()` **那一帧的同步重计算**。
本脚本只做**计数**（不测绝对时间 —— 桩是 lupa 的纯 Lua，绝对耗时与真机无关），
用「调用次数 × 字符处理量」排出热点，避免拍脑袋优化。

口径：
  · hui.TextW / hui.Fit        —— 逐字符 UTF-8 量宽，纯 Lua 循环，最贵
  · PD.MatCol / PD.MatText     —— 材料串重排（内部含多次量宽）
  · PD.RecipeSpec              —— 每行建 spec 表（format 拼接 / lines 表 / ItemName）
  · DG.ItemName                —— 物品名查询

用法：python _temp/_prof_render_prof.py
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

BUILD = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
'''

WRAP_DRIVER = r'''
do
  local NS, PD = TF_NS, TF_NS.ProfModule
  local DGm = TF_NS.ProfHost.DG
  COUNT = {}
  local C = COUNT
  local function wrap(t, k)
    local orig = t[k]
    if type(orig) ~= "function" then return end
    t[k] = function(...)
      local e = C[k]
      if not e then e = { n = 0, ch = 0 }; C[k] = e end
      e.n = e.n + 1
      local a = ...
      if type(a) == "string" then e.ch = e.ch + #a end
      return orig(...)
    end
  end
  wrap(NS.hui, "TextW")
  wrap(NS.hui, "Fit")
  wrap(PD, "MatCol")
  wrap(PD, "MatText")
  wrap(PD, "RecipeSpec")
  wrap(PD, "EnchantSpec")
  wrap(PD, "CraftedSpec")
  wrap(PD, "FavorSpec")
  wrap(PD, "SourceText")
  wrap(PD, "TierText")
  wrap(DGm, "ItemName")
  wrap(DGm, "RequestItem")

  -- 挑 rows 最多的专业
  local D, R = NS.ProfData, NS.ProfRecipes
  local best, bestN = nil, -1
  for _, s in ipairs(D.order or {}) do
    local d = R[s]
    local n = d and #(d.rows or {}) or 0
    if n > bestN then best, bestN = s, n end
  end
  PD.bestSlug, PD.bestRows = best, bestN
end
'''

SETUP = r'''
(function()
  local PD, DGm = TF_NS.ProfModule, TF_NS.ProfHost.DG
  PD.sweeping = true
  PD.Show(PD.bestSlug); PD.SetTab("recipe")
  DGm.stepping = false; DGm.pendingSteps = {}; PUMPS = {}
  for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
  PD.rows = {}; PD.__pendRows = {}
  return 1
end)()
'''

RENDER = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.Render()
  return #PD.__pendRows
end)()
'''

DRAIN = r'''
(function()
  local n = 0
  while #PUMPS > 0 do table.remove(PUMPS, 1)(); n = n + 1 end
  return n
end)()
'''


def build_lua():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
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
            raise RuntimeError('加载 %s 失败（loadfile nil）' % rel)
        chunk()
    return lua


def main():
    lua = build_lua()
    lua.execute(BUILD)
    lua.execute(WRAP_DRIVER)
    slug = lua.eval('TF_NS.ProfModule.bestSlug')
    raw_rows = lua.eval('TF_NS.ProfModule.bestRows')
    print('专业（原始 rows 最多）= %s（%s 条）' % (slug, raw_rows))

    lua.eval(SETUP)
    lua.execute('for k in pairs(COUNT) do COUNT[k] = nil end')

    def snap():
        c = lua.eval('COUNT')
        out = []
        for k in c.keys():
            e = c[k]
            out.append((int(e['n']), int(e['ch']), k))
        out.sort(reverse=True)
        return out

    def reset():
        lua.execute('for k in pairs(COUNT) do COUNT[k] = nil end')

    print()
    print('=== 分阶段（同一份 511 条配方，leatherworking）===')
    print()

    # 阶段 A：RecipeList（建全部 spec）+ SearchFilter
    reset()
    t0 = time.perf_counter()
    lua.eval(r'''
(function()
  local PD = TF_NS.ProfModule
  PH_LIST = PD.SearchFilter(PD.RecipeList())
  return #PH_LIST
end)()
''')
    ms_list = (time.perf_counter() - t0) * 1000
    a = snap()

    # 阶段 B：FitRecipeCols（全量量宽 + 全量材料串重排）
    reset()
    t0 = time.perf_counter()
    lua.eval(r'''
(function()
  local PD = TF_NS.ProfModule
  PD.FitRecipeCols(PH_LIST)
  return 1
end)()
''')
    ms_fit = (time.perf_counter() - t0) * 1000
    b = snap()

    # 阶段 C：整帧 Render（= A + B + PaintRows 版式 + 入队）
    lua.eval(SETUP)
    reset()
    t0 = time.perf_counter()
    pend = lua.eval(RENDER)
    ms_render = (time.perf_counter() - t0) * 1000
    c = snap()

    t1 = time.perf_counter()
    pumps = lua.eval(DRAIN)
    ms_drain = (time.perf_counter() - t1) * 1000

    def show(title, items, ms):
        print('--- %s：%.1f ms' % (title, ms))
        if not items:
            print('    （无调用）')
        for n, ch, k in items:
            print('    %-14s %8d 次 / %10d 字符' % (k, n, ch))
        print()

    show('A  RecipeList + SearchFilter（全量建 spec）', a, ms_list)
    show('B  FitRecipeCols（全量量宽 + 材料串重排）', b, ms_fit)
    show('C  整帧 Render（= A+B+PaintRows 版式）', c, ms_render)

    raw_len = lua.eval('(function() local rf = TF_NS.EnsureProfRecipes if rf then rf() end'
                       ' local d = TF_NS.ProfRecipes[TF_NS.ProfModule.bestSlug]'
                       ' or {} return #(d.rows or {}) end)()')
    specs_len = lua.eval('(function() return #(TF_NS.ProfModule.specs or {}) end)()')
    rows_len = lua.eval('(function() return #TF_NS.ProfModule.rows end)()')
    cap = lua.eval('(function() return TF_NS.ProfModule.ROW_CAP end)()')

    print('原始 rows = %s / 实际画 = %s（ROW_CAP=%s）/ 行池帧数 = %s'
          % (raw_len, specs_len, cap, rows_len))
    print('待建行帧 = %s，抽干 pump 回调 = %s 次（分帧段 %.1f ms，摊在多帧上）'
          % (pend, pumps, ms_drain))
    print()
    print('★ 整帧同步时间 %.1f ms 里：A %.1f + B %.1f = %.1f ms 花在**只值 300 行**的'
          % (ms_render, ms_list, ms_fit, ms_list + ms_fit))
    print('  全量 511 条上；建行帧已经被挪到分帧段（%.1f ms / %s 帧）。'
          % (ms_drain, pumps))
    return 0


if __name__ == '__main__':
    sys.exit(main())
