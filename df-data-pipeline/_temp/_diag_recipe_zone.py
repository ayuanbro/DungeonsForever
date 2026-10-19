# -*- coding: utf-8 -*-
"""诊断：升级页 → 配方页，为什么还有显示中的热区（62）。只读，不写产品文件。"""
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
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
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
            raise RuntimeError('加载 %s 失败' % rel)
        chunk()

    lua.execute(r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
''')
    lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true PD.Show("alchemy") PD.SetTab("leveling") return 1 end)()')

    DIAG = r'''
(function()
  local PD = TF_NS.ProfModule
  local out = {}
  local n = #(PD.rows or {})
  local vis, shownZone, shownIcon, shownBlk = 0, 0, 0, 0
  for i = 1, n do
    local r = PD.rows[i]
    if r and r.__shown ~= false then
      vis = vis + 1
      if r.__iconZone and r.__iconZone.__shown == true then
        shownIcon = shownIcon + 1
        out[#out + 1] = string.format("i=%d __iconZone shown  kind=%s", i,
          tostring(PD.specs and PD.specs[i] and PD.specs[i].kind))
      end
      for j = 1, #(r.blk or {}) do
        local z = r.blk[j].zone
        if z and z.__shown == true then
          shownZone = shownZone + 1
          if #out < 12 then
            out[#out + 1] = string.format("i=%d blk[%d].zone shown kind=%s", i, j,
              tostring(PD.specs and PD.specs[i] and PD.specs[i].kind))
          end
        end
      end
    end
  end
  return n, vis, shownIcon, shownZone, table.concat(out, " | "), (PD.specs and #PD.specs or -1)
end)()
'''
    for label, script in (
        ('leveling', '(function() local PD=TF_NS.ProfModule PD.autoPage="route" PD.SetTab("leveling") return 1 end)()'),
        ('recipe', '(function() local PD=TF_NS.ProfModule PD.SetTab("recipe") return 1 end)()'),
    ):
        lua.eval(script)
        n, vis, si, sz, detail, nspec = lua.eval(DIAG)
        print('[%s] 池=%s 可见=%s 制作物热区=%s 材料热区=%s specs=%s'
              % (label, n, vis, si, sz, nspec))
        if detail:
            print('   %s' % str(detail)[:1500])
    return 0


if __name__ == '__main__':
    sys.exit(main())
