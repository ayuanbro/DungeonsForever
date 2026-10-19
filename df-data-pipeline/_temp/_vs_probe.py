# -*- coding: utf-8 -*-
"""工匠文书详情 vs 双卡行渲染探针（2026-10-11）。

用户报：文书详情里双卡区整块空白（卡底在、内容无）。
本探针离线真建 vs 行，逐件 dump 卡帧与字串/图标状态，定位空卡根因。

用法：python _temp/_vs_probe.py
退出码：0 = 打印完成（诊断性探针，不设判据）。
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

BUILD = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
'''

GOTO = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.Show("crates")
  PD.tab = "writ"
  PD.Render()
  return 1
end)()
'''

DUMP = r'''
(function()
  local PD = TF_NS.ProfModule
  local out = {}
  out[#out + 1] = "specs=" .. tostring(PD.specs and #PD.specs or "nil")
  local vi = nil
  if PD.specs then
    for i = 1, #PD.specs do
      if PD.specs[i] and PD.specs[i].kind == "vs" then vi = i break end
    end
  end
  out[#out + 1] = "vs_index=" .. tostring(vi)
  if not vi then return table.concat(out, " | ") end
  local spec = PD.specs[vi]
  out[#out + 1] = "spec_vw=" .. tostring(rawget(spec, "vw"))
  out[#out + 1] = "spec_h=" .. tostring(rawget(spec, "h"))
  local cards = rawget(spec, "cards")
  out[#out + 1] = "spec_cards=" .. tostring(type(cards) == "table" and #cards or "nil")
  if type(cards) == "table" then
    for k = 1, 2 do
      local d = cards[k]
      if type(d) == "table" then
        out[#out + 1] = string.format("spec_card%d lab=%s price=%s name=%s it=%s",
          k, tostring(rawget(d, "lab")), tostring(rawget(d, "price")),
          tostring(rawget(d, "name")), tostring(rawget(d, "it")))
      end
    end
  end
  local r = PD.rows[vi]
  out[#out + 1] = "row=" .. tostring(r)
  if not r then return table.concat(out, " | ") end
  out[#out + 1] = "row_shown=" .. tostring(rawget(r, "__shown"))
  out[#out + 1] = "row_w=" .. tostring(rawget(r, "__w")) .. " row_h=" .. tostring(rawget(r, "__h"))
  local vs = rawget(r, "__vs")
  out[#out + 1] = "__vs=" .. tostring(vs)
  if type(vs) ~= "table" then return table.concat(out, " | ") end
  local cards2 = rawget(vs, "cards")
  out[#out + 1] = "vs_cards_field=" .. tostring(type(cards2) == "table" and #cards2 or "nil")
  if type(cards2) == "table" then
    for k = 1, 2 do
      local c = cards2[k]
      if type(c) == "table" then
        out[#out + 1] = string.format(
          "card%d shown=%s w=%s h=%s host=%s lab=%s price=%s nm=%s ic_shown=%s ic_tex=%s",
          k, tostring(rawget(c, "__shown")), tostring(rawget(c, "__w")),
          tostring(rawget(c, "__h")), tostring(rawget(c, "host")),
          tostring(c.lab and rawget(c.lab, "__text")),
          tostring(c.price and rawget(c.price, "__text")),
          tostring(c.nm and rawget(c.nm, "__text")),
          tostring(c.ic and rawget(c.ic, "__shown")), tostring(c.ic and rawget(c.ic, "__texture")))
      end
    end
  end
  return table.concat(out, " | ")
end)()
'''


def build_lua():
    addon = ADDON
    toc = open(os.path.join(addon, os.path.basename(TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != T.STUB, 'GetStringWidth 桩补丁没生效'
    lua.execute(stub)
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('if TF_NS.hui then TF_NS.hui.OnThemeChange = function(fn) end end')
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute(r'''
do
  local orig = CreateFrame
  ALL_FRAMES = {}
  CreateFrame = function(...)
    local o = orig(...)
    if type(o) == "table" then ALL_FRAMES[#ALL_FRAMES + 1] = o end
    return o
  end
end
''')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c = orig(...); return a, b, c, 16001 end end')
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


def drain(lua):
    lua.eval('(function() while #PUMPS > 0 do table.remove(PUMPS, 1)() end return 1 end)()')


def main():
    lua = build_lua()
    lua.execute(BUILD)
    ok = lua.eval(GOTO)
    print('GOTO:', ok)
    drain(lua)
    print('DUMP:', lua.eval(DUMP))
    return 0


if __name__ == '__main__':
    sys.exit(main())
