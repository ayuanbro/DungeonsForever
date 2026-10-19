# -*- coding: utf-8 -*-
"""训练师板几何探针：量「列头色带 → 第一排 chip 顶」的空行 + 「末 chip 底 vs boardH」的溢出。

桩环境 SetPoint 记 __pts（原始参数表）、SetSize 记 __w/__h；band 高度源码写死 2。
默认加载开发仓（DF_ADDON_ROOT 可指向客户端）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\workspace\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

BUILD = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
'''

RENDER = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show("blacksmithing")
  PD.SetTab("trainer")
  PD.trFac = "A"
  PD.Render()
  local root = PD.trainerBoard
  local out = {}
  out[#out+1] = 'boardH=' .. tostring(PD.trainerBoardH)
  local h1, h2 = root.__fs[1], root.__fs[2]
  out[#out+1] = 'h1.top=' .. tostring(h1 and h1.__pts and h1.__pts[5])
  out[#out+1] = 'h2.top=' .. tostring(h2 and h2.__pts and h2.__pts[5])
  local band = root.__bands and root.__bands[1]
  local bandTop = band and band.__pts and band.__pts[5]
  out[#out+1] = 'band.top=' .. tostring(bandTop) .. ' band.bottom=' .. tostring(bandTop and (bandTop - 2))
  local n, firstTop, minTop, minH = 0, nil, nil, nil
  for _, c in ipairs(root.__chips or {}) do
    if c.__shown and c.__pts then
      n = n + 1
      local t = c.__pts[5]
      if not firstTop then firstTop = t end
      if not minTop or t < minTop then minTop, minH = t, c.__h end
    end
  end
  out[#out+1] = ('chips=%d firstTop=%s deepestTop=%s chipH=%s'):format(
    n, tostring(firstTop), tostring(minTop), tostring(minH))
  if firstTop and bandTop then
    out[#out+1] = ('BLANK_PX=%dpx (bandBottom-firstChipTop; 正值=首chip顶在色带底下)'):format((bandTop - 2) - firstTop)
  end
  if minTop and minH then
    out[#out+1] = ('deepestChipBottom=%d vs boardH=%d OVERFLOW=%dpx'):format(
      minTop - minH, PD.trainerBoardH, (minH - minTop) - PD.trainerBoardH)
  end
  return table.concat(out, ' ')
end)()
'''


def build_lua():
    toc = open(os.path.join(ADDON, os.path.basename(TOC)),
               encoding='utf-8', errors='replace').read()
    files = [__import__('re').sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != T.STUB, 'GetStringWidth stub patch failed'
    lua.execute(stub)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = orig(...); return a, b, c, 16001, d end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "test area" .. tostring(id) end,
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
            raise RuntimeError('load %s failed (loadfile nil)' % rel)
        chunk()
    return lua


def drain(lua):
    lua.eval('(function() while #PUMPS > 0 do table.remove(PUMPS, 1)() end return 1 end)()')


def main():
    print('ADDON =', ADDON)
    lua = build_lua()
    lua.execute(BUILD)
    drain(lua)
    r = lua.eval(RENDER)
    drain(lua)
    print('=== blacksmithing trainer page (trFac=A, alliance) ===')
    print(r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
