# -*- coding: utf-8 -*-
"""离线桩探针：全 toc 加载 + TabsFor('enchanting') 真值（排查训练师/配方页签缺失）"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools')
import tf_dryrun as T
from lupa import lua51

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute(r'''
C_Timer = { After = function(t, fn) if t == 0 then fn(); return end end }''')
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 - 3660 end')
lua.execute("BG.hui.OnThemeChange = function(fn) end")
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('BG.hui = nil')
BS = chr(92)
lua.execute('ADDON_ROOT = %r' % ADDON.replace(BS, '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('UIErrorsFrame = { AddMessage = function() end }')
lua.execute(r'''
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }
UiMapPoint = { CreateFromCoordinates = function(m, x, y) return { uiMapID = m, x = x, y = y } end }
C_Map = { CanSetUserWaypointOnMap = function() return true end,
          SetUserWaypoint = function(p) end, OpenWorldMap = function(m) end }''')

toc = open(TOC, encoding='utf-8', errors='replace').read()
files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace(BS, '/')
         for l in toc.splitlines() if l.strip() and not l.strip().startswith('##')]
err = []
runner = lua.eval(r'''function(src, name)
    local c = assert(loadstring(src, name))
    local ok, e = pcall(c, "DungeonsForever", TF_NS)
    if not ok then return tostring(e) end
    return nil
end''')
for f in files:
    p = os.path.join(ADDON, f.replace('/', os.sep))
    if not os.path.exists(p):
        err.append('MISSING ' + f)
        continue
    if not f.endswith('.lua'):
        continue
    src = open(p, 'rb').read()
    e = runner(src, f)
    if e:
        err.append('%s -> %s' % (f, e))
print('LOAD ERRORS:', err if err else 'none')
kq = lua.eval(r'''function()
    local t = {}
    for k in pairs(TF_NS) do t[#t+1] = tostring(k) end
    table.sort(t)
    return table.concat(t, ', ')
end''')
print('TF_NS keys:', kq())
q = lua.eval(r'''function()
    local ok, r = pcall(function()
        local R = TF_NS.EnsureProfRecipes and TF_NS.EnsureProfRecipes()
        local e = R and R.enchanting
        if not e then return 'no enchanting rec' end
        return ('rows=%s enchants=%s crafted=%s'):format(e.rows and #e.rows or 'nil', e.enchants and #e.enchants or 'nil', e.crafted and #e.crafted or 'nil')
    end)
    if not ok then return 'ERR ' .. tostring(r) end
    return r
end''')
print('enchanting rec:', q())
tq = lua.eval(r'''function()
    local PD = TF_NS.ProfModule
    if not PD or not PD.TabsFor then return 'ProfModule/TabsFor missing' end
    local ok, r = pcall(PD.TabsFor, "enchanting")
    if not ok then return 'ERR ' .. tostring(r) end
    local s = {}
    for i, v in ipairs(r) do s[i] = tostring(v) end
    return table.concat(s, ' | ')
end''')
print('TabsFor(enchanting):', tq())
