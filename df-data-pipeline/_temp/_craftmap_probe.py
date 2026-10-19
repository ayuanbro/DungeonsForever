# -*- coding: utf-8 -*-
"""配方库覆盖探针（2026-10-12）。

用户实锤：工匠文书详情「自己制造」卡显示「未登记配方」（重磅青铜炸弹本该有配方）。
怀疑 CraftAllMap 首次被调用时 R（ns.ProfRecipes）未就绪 → 空 map 被 PD.craftAll 永久缓存。

本探针离线重建插件环境，直接验证：
  1) ns.EnsureProfRecipes() 返回值与 slug 全集；
  2) engineering 段 rows 数、重磅青铜炸弹（spell 3950）配方及其产量 rec[3]；
  3) CraftAllMap 首调空缓存问题的复现与自愈修复验证。
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

PROBE = r'''
(function()
  local NS = TF_NS
  local out = {}
  local R = NS.EnsureProfRecipes()
  out[#out + 1] = "ensure_type=" .. type(R)
  if type(R) ~= "table" then return table.concat(out, " | ") end
  local slugs = {}
  for k in pairs(R) do slugs[#slugs + 1] = k end
  table.sort(slugs)
  out[#out + 1] = "slugs=" .. #slugs .. "(" .. table.concat(slugs, ",") .. ")"
  local eng = R.engineering
  if not eng then
    out[#out + 1] = "engineering=MISSING"
  else
    out[#out + 1] = "engineering_rows=" .. tostring(eng.rows and #eng.rows)
    for _, rec in ipairs(eng.rows or {}) do
      if rec[1] == 3950 then
        out[#out + 1] = "bomb spell=3950 product=" .. tostring(rec[2]) .. " yield=" .. tostring(rec[3]) .. " mats=" .. tostring(rec[12] and #rec[12])
      end
    end
  end
  local PD = NS.ProfModule
  if PD then
    local before = rawget(PD, "craftAll")
    out[#out + 1] = "craftAll_before=" .. tostring(before ~= nil)
    if before then
      local n = 0
      for _ in pairs(before) do n = n + 1 end
      out[#out + 1] = "craftAll_before_size=" .. n
    end
  end
  local prod = 3950
  return table.concat(out, " | ")
end)()
'''

CRAFTMAP = r'''
(function()
  local NS = TF_NS
  local PD = NS.ProfModule
  PD.craftAll = nil
  local R = NS.EnsureProfRecipes()
  local map = {}
  for slug, d in pairs(R or {}) do
    if type(d) == "table" and type(d.rows) == "table" then
      for _, rec in ipairs(d.rows) do
        local iid = rec[2]
        if type(iid) == "number" and type(rec[12]) == "table" and #rec[12] > 0 and not map[iid] then
          map[iid] = { rec = rec, slug = slug }
        end
      end
    end
  end
  local n = 0
  for _ in pairs(map) do n = n + 1 end
  local bomb
  for iid, v in pairs(map) do
    if v.rec[1] == 3950 then bomb = iid end
  end
  return "map_size=" .. n .. " bomb_item=" .. tostring(bomb)
end)()
'''


def build_lua():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != T.STUB, 'GetStringWidth stub patch not applied'
    lua.execute(stub)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
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
                'local a, b, c, d, e = orig(...); return a, b, c, 16001, e end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypointOnMap = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "test-area" .. tostring(id) end,
}
''')
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    toc = open(os.path.join(ADDON, os.path.basename(TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            raise RuntimeError('failed to load %s (loadfile nil)' % rel)
        chunk()
    return lua


RENDER = r'''
(function()
  local NS = TF_NS
  local PD = NS.ProfModule
  local out = {}
  PD.Show("crates")
  for _, key in ipairs({ "crate", "writ" }) do
    PD.writSel = nil
    PD.SetTab(key)
    local ok, err = pcall(PD.Render)
    out[#out + 1] = key .. "=" .. tostring(ok) .. (ok and "" or (" ERR:" .. tostring(err)))
  end
  local m = PD.craftAll
  local n = 0
  if m then for _ in pairs(m) do n = n + 1 end end
  out[#out + 1] = "craftAll_cached=" .. tostring(m ~= nil) .. " size=" .. n
  return table.concat(out, " | ")
end)()
'''


def drain(lua):
    lua.eval('(function() while #PUMPS > 0 do table.remove(PUMPS, 1)() end return 1 end)()')


def main():
    lua = build_lua()
    lua.execute(BUILD)
    drain(lua)
    print('PROBE:', lua.eval(PROBE))
    print('CRAFTMAP:', lua.eval(CRAFTMAP))
    print('RENDER:', lua.eval(RENDER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
