# -*- coding: utf-8 -*-
"""冒烟：/dfprofrows 的 Lua 侧（PD.AuditRows）在桩里跑得通、不报错、有输出。
只读。用法：DF_ADDON_ROOT=<addon> python _temp/_prof_rowaudit_smoke.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51  # noqa: E402


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = D.T.STUB.replace(
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
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
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

    fails = 0
    checks = [
        ("slash 命令已注册",
         'return type(SlashCmdList) == "table" and type(SlashCmdList["DUNGEONSFOREVERPROFROWS"]) == "function"'),
        ("PD.AuditRows 是函数", 'return type(TF_NS.ProfModule.AuditRows) == "function"'),
    ]
    for name, code in checks:
        ok = lua.eval('(function() ' + code + ' end)()')
        print('[%s] %s' % ('OK  ' if ok else 'FAIL', name))
        if not ok:
            fails += 1

    # 切到升级/路线，再调（含 all 模式）—— 只要不抛错、有输出即可
    lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true '
             'PD.Show("alchemy") PD.autoPage="route" PD.SetTab("leveling") return 1 end)()')
    for arg in ('false', 'true'):
        r = lua.eval('(function() local ok, e = pcall(function() '
                     'TF_NS.ProfModule.AuditRows(%s) end) '
                     'return ok, tostring(e) end)()' % arg)
        ok, err = r[0], r[1]
        print('[%s] AuditRows(%s) 不抛错' % ('OK  ' if ok else 'FAIL', arg))
        if not ok:
            print('       错误：%s' % err)
            fails += 1
    # 顺带跑一次真正的斜杠入口
    r = lua.eval('(function() local ok, e = pcall(SlashCmdList["DUNGEONSFOREVERPROFROWS"], "all") '
                 'return ok, tostring(e) end)()')
    print('[%s] 斜杠入口 /dfprofrows all 不抛错' % ('OK  ' if r[0] else 'FAIL'))
    if not r[0]:
        print('       错误：%s' % r[1])
        fails += 1

    print('\n结论：%s' % ('★ 有失败' if fails else '全过'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
