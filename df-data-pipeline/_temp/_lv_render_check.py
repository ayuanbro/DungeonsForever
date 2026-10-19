# -*- coding: utf-8 -*-
"""核对升级页「分段路线」渲染：固定路线 vs 自动路线 的区间口径是否一致。

用户诉求：自动路线的止点要 +1（42-59 → 42-60）。本探针直接渲染两种模式的行，
读回每行的 rng 文本，验证：
  ① 自动路线止点 = 练到的技能值（下一段起点 = 本段止点，首尾相接）；
  ② 固定路线（数据里本就是重叠口径）与自动路线**口径一致**；
  ③ 高亮（over/passed）行仍正确落在玩家当前技能所在的段。

用法：python _temp/_lv_render_check.py [slug]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51


def make_lua(addon):
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 end')
    lua.execute('BG.hui.OnThemeChange = function(fn) end')
    lua.execute('BG.hui = nil')
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('UnitName = function() return "探针角色" end')
    lua.execute('GetRealmName = function() return "测试服" end')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o=GetBuildInfo; GetBuildInfo=function(...) '
                'local a,b,c,d=o(...); return a,b,c,16001,e end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = { CanSetUserWaypointOnMap = function() return true end,
          SetUserWaypoint = function(pt) end,
          OpenWorldMap = function(mapID) end,
          GetAreaInfo = function(id) return "测区"..tostring(id) end }
Auctionator = { API = { v1 = {
  GetAuctionPriceByItemID = function(c, id) return 1000 end,
  GetAuctionAgeByItemID  = function(c, id) return 0 end,
  GetVendorPriceByItemID = function(c, id) return 500 end } },
  SavedState = { TimeOfLastGetAllScan = 1796850000 - 3600 } }
''')
    wrap = lua.eval('function(src) local ch=assert(loadstring(src)) '
                    'return function() return ch("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        wrap(open(os.path.join(addon, rel), encoding='utf-8',
                  errors='replace').read())()
    return lua


DRIVER = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  local PD = TF_NS.ProfModule
    PD.Show("__SLUG__")
    PD.SetTab("leveling")
end
'''

READ = r'''
(function()
  local PD = TF_NS.ProfModule
  local out = {}
  for _, mode in ipairs({ "fixed", "auto" }) do
    DungeonsForeverDB.prof.autoRoute = (mode == "auto")
    if TF_NS.ProfRouteAuto and TF_NS.ProfRouteAuto.Invalidate then
      TF_NS.ProfRouteAuto.Invalidate()
    end
    local rows = {}
    PD.RowsLeveling(rows)
    local segs = {}
    for _, r in ipairs(rows) do
      if r.lvstep and r.rng then
        segs[#segs + 1] = { rng = r.rng, over = r.over, cur = r.cur }
      end
    end
    out[#out + 1] = string.format("--- %s（%d 段）---", mode, #segs)
    for i = 1, math.min(#segs, 8) do
      out[#out + 1] = string.format("  %-10s over=%-5s cur=%-5s",
        segs[i].rng, tostring(segs[i].over), tostring(segs[i].cur))
    end
    -- 衔接性：第 i 段止点 == 第 i+1 段起点？
    local bad = 0
    for i = 1, #segs - 1 do
      local b = tonumber(segs[i].rng:match("[–-]%s*(%d+)"))
      local c = tonumber(segs[i + 1].rng:match("(%d+)"))
      if b and c and b ~= c then bad = bad + 1 end
    end
    out[#out + 1] = string.format("  首尾相接违规段 = %d", bad)
  end
  return table.concat(out, "\n")
end)
'''


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    slug = sys.argv[1] if len(sys.argv) > 1 else 'leatherworking'
    lua = make_lua(addon)
    lua.execute(DRIVER.replace('__SLUG__', slug))
    print(lua.eval(READ)())
    return 0


if __name__ == '__main__':
    sys.exit(main())
