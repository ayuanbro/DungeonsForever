# -*- coding: utf-8 -*-
"""核对：配方页「显示中的制作物热区」是否都对应商人半段（spec.dval）。
若 mismatch > 0，说明有热区是**不该显示的残留**（透明却能吞鼠标）。只读。"""
import os
import re
import sys

sys.path.insert(0, r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = os.environ.get('DF_ADDON_ROOT') or r'D:\workspace\DungeonsForever'
toc = open(os.path.join(ADDON, 'DungeonsForever.toc'), encoding='utf-8', errors='replace').read()
files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
         for l in toc.splitlines() if l.strip() and not l.strip().startswith('##')]

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
stub = T.STUB.replace(
    '            elseif NUMERIC[k] then f = function() return 100 end',
    '            elseif k == "GetStringWidth" then'
    ' f = function(self) return #(self.__text or "") * 6 end\n'
    '            elseif NUMERIC[k] then f = function() return 100 end', 1)
lua.execute(stub)
lua.execute('C_Timer = { After = function(t, fn) fn() end }')
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 end')
lua.execute("BG.hui.OnThemeChange = function(fn) end")
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('UnitLevel = function() return 60 end')
lua.execute('BG.hui = nil')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
            'local a, b, c, d = o(...); return a, b, c, 16001, e end end')
lua.execute('UIErrorsFrame = { AddMessage = function() end }')
lua.execute('C_Map = { CanSetUserWaypointOnMap = function() return true end, '
            'SetUserWaypoint = function() end, OpenWorldMap = function() end, '
            'GetAreaInfo = function() return "x" end }')
lf = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel) '
              'if not c then return nil end '
              'return function() return c("DungeonsForever", TF_NS) end end')
for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    lf(rel)()
lua.execute('do UnitLevel = function() return 60 end '
            'if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end '
            'TF_NS.DungeonUI:Build() TF_NS.DungeonUI:SwitchSub("Professions") end')

CHECK = r'''(function(key)
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show("alchemy")
  PD.SetTab(key)
  local nDval, nZone, mismatch, nMn, nMz = 0, 0, 0, 0, 0
  for i, r in pairs(PD.rows or {}) do
    local sp = PD.specs and PD.specs[i]
    if sp then
      if sp.dval then nDval = nDval + 1 end
      local z = rawget(r, "__iconZone")
      if z and z.__shown == true then
        nZone = nZone + 1
        if not sp.dval then mismatch = mismatch + 1 end
      end
      for j = 1, #(rawget(r, "mn") or {}) do
        if rawget(rawget(r, "mn")[j], "__shown") == true then nMn = nMn + 1 end
      end
      for j = 1, #(rawget(r, "mz") or {}) do
        if rawget(rawget(r, "mz")[j], "__shown") == true then nMz = nMz + 1 end
      end
    end
  end
  return nDval, nZone, mismatch, nMn, nMz
end)(...)
'''
for key in ("recipe", "leveling"):
    d, z, mis, nmn, nmz = lua.eval(CHECK.replace('...', '"%s"' % key))
    print('[%s] 有 dval 的行=%s  显示中热区=%s  其中无 dval 的即残留=%s  材料段字串=%s 材料段热区=%s'
          % (key, d, z, mis, nmn, nmz))
