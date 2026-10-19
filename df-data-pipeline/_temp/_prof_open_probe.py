# -*- coding: utf-8 -*-
"""「点开配方页」交互序列剖析（2026-10-09 第二轮）。

单帧 Render 已经量过（_prof_render_prof.py），但用户感到的卡顿 = **一次点击
触发的所有帧之和**。树状侧栏点「炼金 → 配方」可能连打 Show(Render overview)
+ SetTab(Render recipe)，再加上名字到货后的 Refresh 又是一次。这里把 PD.Render
包一层计数器，量出：一次点击调了几次 Render、各次多贵。

用法：DF_ADDON_ROOT=D:/workspace/DungeonsForever python _temp/_prof_open_probe.py
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

DRIVER = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
'''

WRAP = r'''
do
  local PD = TF_NS.ProfModule
  RENDER_N, RENDER_LOG = 0, {}
  local orig = PD.Render
  PD.Render = function(...)
    RENDER_N = RENDER_N + 1
    RENDER_LOG[#RENDER_LOG + 1] = { PD.cur or "-", PD.tab or "-", PD.setOpen and 1 or 0,
                                    PD.searchQ or "" }
    return orig(...)
  end
end
'''

CASE = r'''
(function(what)
  local PD, DGm = TF_NS.ProfModule, TF_NS.ProfHost.DG
  PD.sweeping = true
  local function settle()
    DGm.stepping = false; DGm.pendingSteps = {}; PUMPS = {}
  end
  RENDER_N, RENDER_LOG = 0, {}
  local t = {}
  if what == "first" then
    for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
    PD.rows = {}
    PD.Show(PROBE_SLUG); PD.SetTab("recipe")
  elseif what == "again" then
    PD.Show(PROBE_SLUG); PD.SetTab("recipe")           -- 池已满：纯复用
  elseif what == "switch" then
    PD.Show(PROBE_OTHER); PD.SetTab("recipe")
  elseif what == "search" then
    PD.Show(PROBE_SLUG); PD.SetTab("recipe")
    RENDER_N, RENDER_LOG = 0, {}
    PD.searchQ = "e"                                    -- 模拟输入一个字符
    PD.Render()
  elseif what == "tabback" then
    PD.Show(PROBE_SLUG); PD.SetTab("overview")
    RENDER_N, RENDER_LOG = 0, {}
    PD.SetTab("recipe")
  end
  t[1] = RENDER_N
  t[2] = #PD.rows
  t[3] = #PD.__pendRows
  local s = {}
  for i = 1, math.min(#RENDER_LOG, 8) do
    local e = RENDER_LOG[i]
    s[#s + 1] = tostring(e[1]) .. "/" .. tostring(e[2])
      .. (e[3] == 1 and "+set" or "") .. (e[4] ~= "" and ('?q="' .. e[4] .. '"') or "")
  end
  t[4] = table.concat(s, "  →  ")
  return t
end)(...)
'''


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
    lf = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel) '
                  'if not c then return nil end '
                  'return function() return c("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        ch = lf(rel)
        if ch is None:
            print('加载失败 %s' % rel)
            return 1
        ch()
    lua.execute(DRIVER)
    lua.execute(WRAP)

    # 挑「配方行最多」和「次多」的两个专业
    picked = lua.eval(r'''
(function()
  local D, R = TF_NS.ProfData, (TF_NS.EnsureProfRecipes and TF_NS.EnsureProfRecipes() or nil)
  local a = {}
  for _, s in ipairs(D.order or {}) do
    a[#a + 1] = { s, #((R[s] or {}).rows or {}) }
  end
  table.sort(a, function(x, y) return x[2] > y[2] end)
  return tostring(a[1][1]) .. "|" .. tostring(a[1][2]) .. "|"
      .. tostring(a[2][1]) .. "|" .. tostring(a[2][2])
end)()
''')
    p = picked.split('|')
    lua.globals().PROBE_SLUG = p[0]
    lua.globals().PROBE_OTHER = p[2]
    print('主专业 = %s(%s 条)   另一专业 = %s(%s 条)' % (p[0], p[1], p[2], p[3]))

    cases = [
        ('first', '首次点开配方页（行池是空的，名字可能未到货）'),
        ('again', '再点一次同一页（行池已满 → 纯复用）'),
        ('switch', '切到另一个专业的配方页（池够用，不新建帧）'),
        ('tabback', '从总览切回配方页'),
        ('search', '搜索框输入 1 个字符'),
    ]
    probe = lua.eval(r'''
function(what)
  local PD, DGm = TF_NS.ProfModule, TF_NS.ProfHost.DG
  PD.sweeping = true
  local function settle() DGm.stepping = false; DGm.pendingSteps = {}; PUMPS = {} end
  RENDER_N, RENDER_LOG = 0, {}
  if what == "first" then
    for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
    PD.rows = {}
    PD.Show(PROBE_SLUG); PD.SetTab("recipe")
  elseif what == "again" then
    PD.Show(PROBE_SLUG); PD.SetTab("recipe")
  elseif what == "switch" then
    PD.Show(PROBE_OTHER); PD.SetTab("recipe")
  elseif what == "tabback" then
    PD.Show(PROBE_SLUG); PD.SetTab("overview")
    RENDER_N, RENDER_LOG = 0, {}
    PD.SetTab("recipe")
  elseif what == "search" then
    PD.Show(PROBE_SLUG); PD.SetTab("recipe")
    RENDER_N, RENDER_LOG = 0, {}
    PD.searchQ = "e"; PD.Render()
  end
  local s = {}
  for i = 1, #RENDER_LOG do
    local e = RENDER_LOG[i]
    s[#s + 1] = tostring(e[1]) .. "/" .. tostring(e[2])
      .. (e[3] == 1 and "+settings" or "")
      .. (e[4] ~= "" and (' q="' .. tostring(e[4]) .. '"') or "")
  end
  return { RENDER_N, #PD.rows, #PD.__pendRows, table.concat(s, "  →  ") }
end
''')
    print()
    print('%-46s %5s %9s   %s' % ('场景', 'Render', '相对耗时', '触发链'))
    for key, desc in cases:
        t0 = time.perf_counter()
        r = probe(key)
        ms = (time.perf_counter() - t0) * 1000
        print('%-46s %5d %7.1f ms   %s' % (desc, int(r[1]), ms, r[4]))
        print('%62s行池 #%d / 待建 #%d' % ('', int(r[2]), int(r[3])))
    lua.execute('TF_NS.ProfModule.searchQ = nil')
    return 0


if __name__ == '__main__':
    sys.exit(main())
