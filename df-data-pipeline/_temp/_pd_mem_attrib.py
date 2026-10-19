# -*- coding: utf-8 -*-
"""离线归因：第一次进配方页的一次性内存增量拆段。

段位：ensure(数据表) / page(页面帧+导航) / render(首渲染) / steps(分帧建满行池) / warm(名字预热)。
用法：DF_ADDON_ROOT=D:/workspace/DungeonsForever python _temp/_pd_mem_attrib.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

PROBE = r'''
function()
  local out = {}
  local function mark(k)
    collectgarbage("collect"); collectgarbage("collect")
    out[#out + 1] = string.format("%-10s %10.1f KB", k, collectgarbage("count"))
  end
  local PD, DGm = TF_NS.ProfModule, TF_NS.ProfHost.DG
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end

  mark("load")
  local rf = TF_NS.EnsureProfRecipes
  if rf then rf() end
  mark("ensure")
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  mark("page")

  local best, bestN = nil, -1
  local R = TF_NS.ProfRecipes
  for _, s in ipairs(TF_NS.ProfData.order or {}) do
    local d = R and R[s]
    local n = (d and d.rows and #d.rows) or 0
    if n > bestN then best, bestN = s, n end
  end
  PD.Show(best); PD.SetTab("recipe")
  mark("render")

  local guard = 0
  while #DGm.pendingSteps > 0 and guard < 4000 do
    guard = guard + 1
    local fn = table.remove(DGm.pendingSteps, 1)
    if fn then pcall(fn) end
  end
  mark("steps")
  DGm.stepping = false

  local n = math.min(bestN or 0, PD.ROW_CAP or 300)
  local all = R[best] and R[best].rows
  if all then
    for i = 1, n do
      local r = all[i]
      if r then
        PD.WarmId(r[2])
        local ms = r[12]
        if ms then for k = 1, #ms do PD.WarmId(ms[k] and ms[k][1]) end end
      end
    end
  end
  mark("warm")
  return tostring(best) .. "|" .. tostring(bestN) .. "|" ..
      "|池=" .. tostring(PD.rows and #PD.rows or "?") ..
      "|待建=" .. tostring(#DGm.pendingSteps) .. "\n" .. table.concat(out, "\n")
end
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
    lua.execute('date = function() return "00:00:00" end')
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
    print(lua.eval(PROBE)())
    return 0


if __name__ == '__main__':
    sys.exit(main())
