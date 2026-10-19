# -*- coding: utf-8 -*-
"""PvP 三页容器卡一次性探针：真跑 week/rep/sets 渲染，验证卡片显隐与定高不炸。

退出码：0 = 全部通过；1 = 有断言失败或渲染报错。
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
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("PvP")
end
'''

TAB = r'''
(function(key)
  local PV = TF_NS.PvPModule
  PV.SetTab(key)
  return PV.cur
end)(...)
'''

CHECK = r'''
(function()
  local PV = TF_NS.PvPModule
  local function num(v) return type(v) == "number" end
  local function h(f)
    if not f or not f.IsShown or not f:IsShown() then return -1 end
    local v = f.GetHeight and f:GetHeight()
    return num(v) and v or -2
  end
  if PV.cur == "week" then
    return h(PV.weekCard1), h(PV.weekCard2)
  elseif PV.cur == "rep" then
    return h(PV.repCard), -1
  elseif PV.cur == "sets" then
    return h(PV.setsLeftCard), h(PV.setsRightCard)
  else
    return h(PV.rankCard), h(PV.capCard)
  end
end)()
'''

SIM = r'''
(function()
  local PV = TF_NS.PvPModule
  PV.simRank = 5
  PV.SetTab("week")
  return 1
end)()
'''

REP_HONOR = r'''
(function()
  local PV = TF_NS.PvPModule
  PV.selRep = "honor"
  PV.SetTab("rep")
  return 1
end)()
'''

REP_BATTLE_A = r'''
(function()
  local PV = TF_NS.PvPModule
  PV.selRep = "ab"
  PV.faction = "A"
  PV.SetTab("rep")
  return 1
end)()
'''

REP_BATTLE_H = r'''
(function()
  local PV = TF_NS.PvPModule
  PV.selRep = "ab"
  PV.faction = "H"
  PV.SetTab("rep")
  return 1
end)()
'''

REP_BATTLE_WSG = r'''
(function()
  local PV = TF_NS.PvPModule
  PV.selRep = "ab"
  PV.selRep = "wsg"
  PV.SetTab("rep")
  return 1
end)()
'''

SET_SEL = r'''
(function()
  local PV = TF_NS.PvPModule
  PV.selSet = 3
  PV.SetTab("sets")
  return 1
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
    lua.execute(T.STUB)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c = orig(...); return a, b, c, 16001 end end')
    lua.execute('UIErrorsFrame = { AddMessage = function() end }')
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
    drain(lua)
    bad = 0

    cases = [
        ('ranks(基线回归)', TAB.replace('...', '"ranks"'), None),
        ('week(常规)', TAB.replace('...', '"week"'), None),
        ('week(模拟 R5 里程碑分支)', SIM, None),
        ('rep(暗矛)', TAB.replace('...', '"rep"'), None),
        ('rep(荣誉之地)', REP_HONOR, None),
        ('rep(战场声望·联盟)', REP_BATTLE_A, None),
        ('rep(战场声望·部落)', REP_BATTLE_H, None),
        ('rep(战场声望·战歌页签)', REP_BATTLE_WSG, None),
        ('sets(战士)', TAB.replace('...', '"sets"'), None),
        ('sets(第 3 套)', SET_SEL, None),
    ]
    for label, code, _ in cases:
        try:
            lua.eval(code)
            drain(lua)
            h1, h2 = lua.eval(CHECK)
            ok = (h1 and h1 > 0) and (h2 == -1 or (h2 and h2 > 0))
            if not ok:
                bad += 1
            print('%s %s  卡高1=%s 卡高2=%s' % ('OK  ' if ok else 'FAIL', label, h1, h2))
        except Exception as e:
            bad += 1
            print('FAIL %s  渲染报错: %s' % (label, e))

    # 军衔页回归：行池首行文本（harness 同款断言，确认 L1 改色没伤渲染）
    lua.eval(TAB.replace('...', '"ranks"'))
    drain(lua)
    txt = lua.eval('(function() local PV = TF_NS.PvPModule '
                   'return PV.rankRows[1].pts.__text end)()')
    if txt != '750':
        bad += 1
        print('FAIL 军衔首行点数 = %r（期望 750）' % txt)
    else:
        print('OK   军衔首行点数 750')

    print('通过 %d / 失败 %d' % (len(cases) + 1 - bad, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
