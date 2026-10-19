# -*- coding: utf-8 -*-
"""插桩版探针：内存里给 ProfessionUI.lua 的 RecipeList 注入调试日志，
走真加载链路，看「全部」分支到底走到哪一步。"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS); sys.path.insert(0, HERE)
import tf_dryrun as T
from lupa import lua51

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
lua = lua51.LuaRuntime(unpack_returned_tuples=True)
stub = T.STUB.replace(
    '            elseif NUMERIC[k] then f = function() return 100 end',
    '            elseif k == "GetStringWidth" then f = function(self) return #(self.__text or "") * 6 end\n'
    '            elseif NUMERIC[k] then f = function() return 100 end', 1)
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
lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) local a, b, c, d = orig(...); return a, b, c, 16001, d end end')
lua.execute('UIErrorsFrame = { AddMessage = function() end }')
lua.execute('C_Map = { CanSetUserWaypointOnMap = function() return true end, SetUserWaypoint = function(pt) end, OpenWorldMap = function(m) end, GetAreaInfo = function(id) return "z" end }')

# ── 源码注入 ──────────────────────────────────────────────
src_path = os.path.join(ADDON, 'Core', 'ProfessionUI.lua')
src = open(src_path, 'rb').read().decode('utf-8')
NL = '\r\n' if '\r\n' in src else '\n'
log = []
n = src.count('function PD.RecipeList(limit, q)')
assert n == 1, 'RecipeList 定义数 = %d' % n


def A(s):
    return s.replace('\n', NL)


anchor1 = A('    local cap = limit or PD.ROW_CAP\n    if cap < 1 then return out end\n')
assert src.count(anchor1) == 1
src = src.replace(anchor1, anchor1 +
    "    _DBGLOG[#_DBGLOG+1] = ('ENTER d=%s key=%s cap=%s ench=%s rows=%s')"
    ":format(tostring(d), tostring(key), tostring(cap),"
    " d and d.enchants and #d.enchants or 'nil', d and d.rows and #d.rows or 'nil')" + NL, 1)
anchor2 = A('    if key == "__enchant" then\n')
assert src.count(anchor2) == 1
src = src.replace(anchor2, "    _DBGLOG[#_DBGLOG+1] = 'not-enchant-branch key=' .. tostring(key)" + NL + anchor2, 1)
anchor3 = A('        local want = (key == "all") and nil or tostring(key)\n')
assert src.count(anchor3) == 1
src = src.replace(anchor3, "        _DBGLOG[#_DBGLOG+1] = 'ENCH-BRANCH-IN want=' .. tostring(want)" + NL + anchor3, 1)
anchor3b = A('        for _, e in ipairs(d.enchants or {}) do\n            local g = tostring(e[3] or "")\n            if g == "" then g = L["其他"] end\n')
print('anchor3b count:', src.count(anchor3b))
assert src.count(anchor3b) == 1
src = src.replace(anchor3b, anchor3b +
    "            _DBGLOG[#_DBGLOG+1] = 'LOOP g=' .. g .. ' n-loop=' .. #_DBGLOG" + NL, 1)
anchor4 = A('                out[#out + 1] = PD.EnchantSpec(e)\n')
print('EnchantSpec-call sites:', src.count(anchor4))
assert src.count(anchor4) == 1
src = src.replace(anchor4,
    "                _DBGLOG[#_DBGLOG+1] = 'CALL g=' .. tostring(g) .. ' tES=' .. type(PD.EnchantSpec) .. ' want=' .. tostring(want)" + NL + anchor4 +
    "                _DBGLOG[#_DBGLOG+1] = 'CALLED t=' .. type(out[#out])" + NL, 1)
anchor5 = A('        return out\n    end\n    if key == "__crafted" then\n')
assert src.count(anchor5) == 1
src = src.replace(anchor5, "        _DBGLOG[#_DBGLOG+1] = 'ENCH-BRANCH-OUT n=' .. #out" + NL + anchor5, 1)
anchor6 = A('function PD.EnchantSpec(en)\n')
assert src.count(anchor6) == 1
src = src.replace(anchor6, anchor6 +
    "    _DBGLOG[#_DBGLOG+1] = 'SPEC-IN en=' .. tostring(en ~= nil)" + NL, 1)
anchor7 = A('    return {\n        kind = "row", is_new = en[11], _mats = en[9],')
assert src.count(anchor7) == 1
src = src.replace(anchor7, "    _DBGLOG[#_DBGLOG+1] = 'SPEC-RET'" + NL + anchor7, 1)
lua.execute('_DBGLOG = {}')
runner = lua.eval('function(s, name) local c = assert(loadstring(s, name)) return function() return c("DungeonsForever", TF_NS) end end')

toc = open(os.path.join(ADDON, 'DungeonsForever.toc'), encoding='utf-8', errors='replace').read()
files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/') for l in toc.splitlines() if l.strip() and not l.strip().startswith('##')]
loadfn = lua.eval('function(rel2) local c = loadfile(ADDON_ROOT .. "/" .. rel2) if not c then return nil end return function() return c("DungeonsForever", TF_NS) end end')
for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    if rel.replace('\\', '/') == 'Core/ProfessionUI.lua':
        ch = runner(src, rel + ' (instrumented)')
    else:
        ch = loadfn(rel)
    if ch is None:
        raise RuntimeError(rel)
    ch()

lua.execute('do UnitLevel = UnitLevel or function() return 60 end if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end TF_NS.DungeonUI:Build() TF_NS.DungeonUI:SwitchSub("Professions") end')

DBG = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show("enchanting")
  PD.SetTab("recipe")
  PD.toolKey = "all"
  local list = PD.RecipeList(nil, nil)
  return 'list=' .. #list
end)()
'''
print(lua.eval(DBG))
gl = lua.eval(r'''function()
  local sin, sret, loop = 0, 0, 0
  for _, e in ipairs(_DBGLOG) do
    if e:find('SPEC%-IN') then sin = sin + 1
    elseif e:find('SPEC%-RET') then sret = sret + 1
    elseif e:find('LOOP') then loop = loop + 1 end
  end
  local tail = {}
  for i = math.max(1, #_DBGLOG - 40), #_DBGLOG do tail[#tail+1] = _DBGLOG[i] end
  return ('sin=%d sret=%d loop=%d total=%d\nLAST40:\n%s'):format(sin, sret, loop, #_DBGLOG, table.concat(tail, '\n'))
end''')
print(gl())
