# -*- coding: utf-8 -*-
"""诊断 v3：整页帧集合差分（升级页 基线 vs 配方页往返）。
抓 PD.page 子树下所有「显示中」的帧，带身份描述，做集合差。
只读，不写产品文件。

用法：DF_ADDON_ROOT=<addon> python _temp/_diag_page_subtree.py
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
    build = 16001
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
    assert stub != D.T.STUB
    lua.execute(stub)
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

    DUMP = r'''
(function()
  local PD = TF_NS.ProfModule
  local page = PD.page
  local function descendant(f)
    local p, guard = f, 0
    while p and guard < 40 do
      if p == page then return true end
      p = rawget(p, "__parent"); guard = guard + 1
    end
    return false
  end
  local function txt(f)
    local ch = rawget(f, "__children")
    if ch then
      for i = 1, #ch do
        local v = rawget(ch[i], "__text")
        if v ~= nil and tostring(v) ~= "" then return tostring(v) end
      end
    end
    return ""
  end
  local function allShown(f)
    local p, guard = rawget(f, "__parent"), 0
    while p and guard < 40 do
      if p == page then return true end
      if rawget(p, "__shown") == false then return false end
      p = rawget(p, "__parent"); guard = guard + 1
    end
    return true
  end
  local out = {}
  for _, f in ipairs(ALL_FRAMES or {}) do
    if rawget(f, "__shown") ~= false and descendant(f) and allShown(f) then
      local p0 = rawget(f, "__parent")
      local pts = rawget(f, "__pts")
      local anchor = (pts and pts[1]) and tostring(pts[1]) or ""
      local own = rawget(f, "__text")
      local name = tostring(rawget(f, "__name"))
      out[#out + 1] = string.format("%s|%sx%s|%s|%s|%s",
        name, tostring(rawget(f, "__w")), tostring(rawget(f, "__h")),
        anchor, (own ~= nil) and tostring(own) or txt(f),
        (p0 == page) and "PAGE" or (p0 == PD.child) and "CHILD" or "X")
    end
  end
  return #out, table.concat(out, "\n")
end)()
'''

    lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true PD.Show("alchemy") return 1 end)()')

    LV = '(function() local PD=TF_NS.ProfModule PD.autoPage="%s" PD.SetTab("leveling") return 1 end)()'
    GO = '(function() local PD=TF_NS.ProfModule PD.setOpen=false PD.SetTab("%s") return 1 end)()'

    from collections import Counter
    bad = 0
    total = 0
    # from 状态：6 个页签 + 升级的另一个子页（「购物清单 → 路线」= 原始报障路径）
    FROM = [("tab", "recipe", "配方"), ("tab", "gather", "采集"), ("tab", "camp", "营地"),
            ("tab", "overview", "总览"), ("tab", "legacy", "传承"), ("tab", "notes", "说明"),
            ("sub", "shop", "购物清单"), ("sub", "route", "路线")]
    for mode, mlabel in (("route", "路线"), ("shop", "购物清单")):
        lua.eval(LV % mode)
        lua.eval(LV % mode)
        n1, s1 = lua.eval(DUMP)
        ca = Counter([x for x in str(s1).split('\n') if x])
        for kind, key, flabel in FROM:
            if kind == "sub" and key == mode:
                continue
            if kind == "tab":
                lua.eval(GO % key)
            else:
                lua.eval(LV % key)
            lua.eval(LV % mode)
            lua.eval(LV % mode)
            n2, s2 = lua.eval(DUMP)
            cb = Counter([x for x in str(s2).split('\n') if x])
            extra = sorted((cb - ca).elements())
            missing = sorted((ca - cb).elements())
            total += 1
            mark = 'OK  ' if (not extra and not missing) else 'FAIL'
            if mark == 'FAIL':
                bad += 1
            print('[%s] %-8s → 升级/%s：帧 %s vs %s，多 %d 少 %d'
                  % (mark, flabel, mlabel, n1, n2, len(extra), len(missing)))
            for e in extra[:6]:
                print('    + %s' % e[:180])
            for m in missing[:6]:
                print('    - %s' % m[:180])

    print('\n结论：%s（%d 组 / 整页显示帧集合）'
          % ('★ 有整页帧残留' if bad else '整页帧集合全部一致', total))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
