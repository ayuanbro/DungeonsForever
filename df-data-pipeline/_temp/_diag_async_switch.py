# -*- coding: utf-8 -*-
"""诊断 v4：真·异步分帧窗口下的跨页签残留。

关键：`C_Timer.After` **不立即执行**，而是排队 —— 复刻真机 `DG.RunSteps` 的
「每帧只跑一块」窗口（桩若同步跑完，窗口被折叠，之前所有探针都测不到）。

序列（用户口径）：升级/购物清单（分帧建到一半）→ 配方页 → 升级/路线。
判据：整页显示帧集合 == 干净基线（同池规模下的稳态）。

用法：DF_ADDON_ROOT=<addon> python _temp/_diag_async_switch.py
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
    # ★ 真机口径：C_Timer 只排队，不立即执行
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

    PUMP_ALL = '(function() local g=0 while #PUMPS>0 and g<4000 do g=g+1 table.remove(PUMPS,1)() end return g end)()'
    PUMP_ONE = '(function() if #PUMPS>0 then table.remove(PUMPS,1)() return 1 end return 0 end)()'
    NPUMP = '(function() return #PUMPS end)()'

    DUMP = r'''
(function()
  local PD = TF_NS.ProfModule
  local page = PD.page
  local function descendant(f)
    local p, g = f, 0
    while p and g < 40 do if p == page then return true end
      p = rawget(p, "__parent"); g = g + 1 end
    return false
  end
  local function allShown(f)
    local p, g = rawget(f, "__parent"), 0
    while p and g < 40 do
      if p == page then return true end
      if rawget(p, "__shown") == false then return false end
      p = rawget(p, "__parent"); g = g + 1
    end
    return true
  end
  local function txt(f)
    local ch = rawget(f, "__children")
    if ch then for i = 1, #ch do
      local v = rawget(ch[i], "__text")
      if v ~= nil and tostring(v) ~= "" then return tostring(v) end
    end end
    return ""
  end
  local out = {}
  for _, f in ipairs(ALL_FRAMES or {}) do
    if rawget(f, "__shown") ~= false and descendant(f) and allShown(f) then
      local own = rawget(f, "__text")
      local pts = rawget(f, "__pts")
      out[#out + 1] = string.format("%s|%sx%s|%s|%s",
        tostring(rawget(f, "__name")), tostring(rawget(f, "__w")),
        tostring(rawget(f, "__h")), (pts and pts[1]) and tostring(pts[1]) or "",
        (own ~= nil) and tostring(own) or txt(f))
    end
  end
  return #out, table.concat(out, "\n")
end)()
'''

    lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true PD.Show("alchemy") return 1 end)()')

    def lv(mode):
        lua.eval('(function() local PD=TF_NS.ProfModule PD.autoPage="%s" PD.SetTab("leveling") return 1 end)()' % mode)

    def go(key):
        lua.eval('(function() local PD=TF_NS.ProfModule PD.SetTab("%s") return 1 end)()' % key)

    def pump_all():
        lua.eval(PUMP_ALL)

    def pump(n):
        for _ in range(n):
            lua.eval(PUMP_ONE)

    # ── 干净基线：异步建完之后再连渲一次（稳态） ──
    lv('route'); pump_all(); lv('route'); pump_all()
    nA, sA = lua.eval(DUMP)
    A = sorted([x for x in str(sA).split('\n') if x])

    # ── 用户序列：购物清单（分帧半途）→ 配方 → 路线 ──
    bad = 0
    for depth in (0, 1, 2, 3, 5, 8):
        # 重置到「购物清单，分帧刚开始」
        lua.eval('(function() local PD=TF_NS.ProfModule for i=#PD.rows,1,-1 do if PD.rows[i] then PD.rows[i]:Hide() end end PD.rows={} PD.__pendRows={} PD.sweeping=true return 1 end)()')
        lv('shop')
        left1 = int(lua.eval(NPUMP))
        pump(depth)
        left2 = int(lua.eval(NPUMP))
        # 半途切配方
        go('recipe')
        left3 = int(lua.eval(NPUMP))
        pump(depth)
        # 切回路线
        lv('route')
        pump_all()
        lv('route')
        pump_all()
        nB, sB = lua.eval(DUMP)
        B = sorted([x for x in str(sB).split('\n') if x])
        extra = [x for x in B if x not in A]
        missing = [x for x in A if x not in B]
        mark = 'OK  ' if (not extra and not missing) else 'FAIL'
        print('[%s] 泵深度=%d（队列 %d→%d→配方后 %d）：显示帧 %d vs %d，多 %d 少 %d'
              % (mark, depth, left1, left2, left3, nA, nB, len(extra), len(missing)))
        if extra or missing:
            bad += 1
            for e in extra[:8]:
                print('    + %s' % e[:180])
            for m in missing[:8]:
                print('    - %s' % m[:180])
    print('\n结论：%s' % ('★ 异步窗口下有残留' if bad else '异步窗口下无残留'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
