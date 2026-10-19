# -*- coding: utf-8 -*-
"""板条箱详情探针：复现 df_dungeon_check 三个 FAIL（最省标签 / 成本汇总标题 / 静态行数）。"""
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
  local RA = TF_NS.ProfRouteAuto
  local out = {}
  out[#out+1] = 'RA=' .. tostring(RA ~= nil) .. ' AHPriceOf=' .. tostring(RA and RA.AHPriceOf ~= nil)
  local CD = TF_NS.CratesData
  out[#out+1] = 'crates=' .. tostring(CD and CD.crates and #CD.crates or 'nil')
  if CD and CD.crates and CD.crates[1] then
    local c = CD.crates[1]
    out[#out+1] = ('crate1 id=%s tier=%s opts=%s'):format(
      tostring(c.id), tostring(c.tier), tostring(c.opts and #c.opts or 'nil'))
    if c.opts then
      for i, o in ipairs(c.opts) do
        if i <= 3 then
          out[#out+1] = ('  opt%d: item=%s qty=%s'):format(i, tostring(o[1]), tostring(o[2]))
        end
      end
    end
  end
  PD.sweeping = true
  PD.Show("crates")
  PD.SetTab("crate")
  out[#out+1] = 'secCount=' .. tostring(PD.secCount)
  local n, tagBest, buyRow = 0, false, false
  local heads = {}
  local fs14 = 0
  for idx, sp in ipairs(PD.specs or {}) do
    if sp.sec and sp.col == 2 then n = n + 1 end
    if sp.tag then
      out[#out+1] = ('  spec%d tag=%s'):format(idx, tostring(sp.tag.text))
      if sp.tag.text == "最省" then tagBest = true end
    end
    if type(sp.text) == "string" and sp.text:find("购买 ") then buyRow = true end
    if sp.kind == "head" then heads[tostring(sp.text or "")] = true end
    if sp.col == 2 and sp.fs == 14 then fs14 = fs14 + 1 end
  end
  out[#out+1] = ('nCrate=%d tagBest=%s buyRow=%s fs14=%d specs=%d'):format(
    n, tostring(tagBest), tostring(buyRow), fs14, #(PD.specs or {}))
  local hk = {}
  for k in pairs(heads) do hk[#hk + 1] = k end
  out[#out+1] = 'heads=' .. table.concat(hk, ' | ')
  return table.concat(out, '\n')
end)()
'''

RENDER_STUB = r'''
(function()
  local PD = TF_NS.ProfModule
  local RA = TF_NS.ProfRouteAuto
  local _old = RA and RA.AHPriceOf or nil
  if RA then RA.AHPriceOf = function() return 100 end end
  PD.sweeping = true
  PD.Show("crates")
  PD.SetTab("crate")
  local out = {}
  out[#out+1] = '--- with AHPriceOf=100 stub ---'
  local n, tagBest, buyRow, fs14 = 0, false, false, 0
  local heads = {}
  for idx, sp in ipairs(PD.specs or {}) do
    if sp.sec and sp.col == 2 then n = n + 1 end
    if sp.tag then
      out[#out+1] = ('  spec%d tag=%s right=%s'):format(idx, tostring(sp.tag.text), tostring(sp.right))
      if sp.tag.text == "最省" then tagBest = true end
    end
    if type(sp.text) == "string" and sp.text:find("购买 ") then buyRow = true end
    if sp.kind == "head" then heads[tostring(sp.text or "")] = true end
    if sp.col == 2 and sp.fs == 14 then fs14 = fs14 + 1 end
  end
  out[#out+1] = ('nCrate=%d tagBest=%s buyRow=%s fs14=%d'):format(
    n, tostring(tagBest), tostring(buyRow), fs14)
  local hk = {}
  for k in pairs(heads) do hk[#hk + 1] = k end
  out[#out+1] = 'heads=' .. table.concat(hk, ' | ')
  if RA then RA.AHPriceOf = _old end
  return table.concat(out, '\n')
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
    print('=== crate page (no price stub) ===')
    print(lua.eval(RENDER))
    drain(lua)
    print()
    print(lua.eval(RENDER_STUB))
    drain(lua)
    return 0


if __name__ == '__main__':
    sys.exit(main())
