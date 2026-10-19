# -*- coding: utf-8 -*-
"""列宽口径探针：全量统计 vs 前 ROW_CAP 条统计，钳位后的 nameW 差多少。

决定「要不要把列宽统计也限流到前 300 条」—— 若两者钳位后一致，就可以放心限流。
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    toc = open(os.path.join(addon, os.path.basename(D.TOC)), encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines() if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a,b,c,d = orig(...); return a,b,c,16001,e end end')
    lua.execute('UIErrorsFrame = { AddMessage = function() end }')
    lua.execute('C_Map = { CanSetUserWaypointOnMap = function() return true end,'
                ' SetUserWaypoint = function() end, OpenWorldMap = function() end,'
                ' GetAreaInfo = function(id) return "x" end }')
    lf = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel) '
                  'if not c then return nil end '
                  'return function() return c("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'): continue
        ch = lf(rel)
        if ch is None: print('load fail', rel); return 1
        ch()
    lua.execute(r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
''')
    res = lua.eval(r'''
(function()
  local PD, D = TF_NS.ProfModule, TF_NS.ProfData
  PD.sweeping = true
  local out = {}
  for _, slug in ipairs(D.order or {}) do
    PD.cur = slug; PD.tab = "recipe"; PD.setOpen = false
    PD.toolKey = nil; PD.searchQ = nil
    local list = PD.RecipeList()
    local cap = PD.ROW_CAP
    local function maxOf(n)
      local m = 0
      for i = 1, math.min(n, #list) do
        local s = list[i]
        local w = PD.TextW(s.text or "", 13)
        if s.is_new then w = w + PD.RECIPE_BADGE_W end
        local sw = PD.TextW(s.sub or "", 11)
        if sw > w then w = sw end
        if w > m then m = w end
      end
      return m
    end
    local function nameOf(m)
      return math.floor(math.max(PD.RECIPE_NAME_MIN, math.min(PD.RECIPE_NAME_MAX, m + 6)))
    end
    local full, head = maxOf(#list), maxOf(cap)
    out[#out + 1] = { slug, #list, cap, full, head, nameOf(full), nameOf(head) }
  end
  return out
end)()
''')
    print('%-16s %6s %6s %8s %8s %8s %8s %s' %
          ('专业', '全量', '前300', 'maxW全', 'maxW300', 'nameW全', 'nameW300', '差'))
    bad = 0
    for i in range(1, len(res) + 1):
        r = res[i]
        d = int(r[6]) - int(r[7])
        if d != 0: bad += 1
        print('%-16s %6d %6d %8d %8d %8d %8d %s' %
              (r[1], r[2], r[3], r[4], r[5], r[6], r[7], ('%+d ← 有差' % d) if d else '0'))
    print()
    print('MIN=%s MAX=%s  → 列宽有差的专业数 = %d'
          % (lua.eval('TF_NS.ProfModule.RECIPE_NAME_MIN'),
             lua.eval('TF_NS.ProfModule.RECIPE_NAME_MAX'), bad))
    return 0

if __name__ == '__main__':
    sys.exit(main())
