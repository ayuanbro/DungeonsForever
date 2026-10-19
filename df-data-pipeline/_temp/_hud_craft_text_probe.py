# -*- coding: utf-8 -*-
"""读 HUD 卡片实际渲染出来的「大约还需制作N次」文本（用户能看到的那个数）。

对照两版常量：0.7/0.25（旧）vs 0.5/0.05（新），确认 HUD 显示真的变了。

用法：
  python _temp/_hud_craft_text_probe.py            # 打 beta 副本
  DF_ADDON_ROOT=... python _temp/_hud_craft_text_probe.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

OLD = 'local G_YELLOW, G_GREEN = 0.7, 0.25'
NEW = 'local G_YELLOW, G_GREEN = 0.5, 0.05'


def make_lua(addon, patch):
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
    wrap = lua.eval('function(src)\n'
                    '  local ch = assert(loadstring(src))\n'
                    '  return function() return ch("DungeonsForever", TF_NS) end\n'
                    'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        src = open(os.path.join(addon, rel), encoding='utf-8',
                   errors='replace').read()
        if rel.replace('\\', '/') == 'Core/ProfRouteAuto.lua':
            assert NEW in src, '常量锚点 %r 没找到' % NEW
            src = src.replace(NEW, patch, 1)   # patch=NEW → 原样；patch=OLD → 还原对照
        wrap(src)()
    return lua


DRIVER = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  local PD = TF_NS.ProfModule
  PD.Show("alchemy")
  PD.SetTab("leveling")
end
'''

READ = r'''
(function()
  local PD = TF_NS.ProfModule
  local PF = TF_NS.ProfFollow
  local RA = TF_NS.ProfRouteAuto
  local out = {}
  DungeonsForeverDB.prof.autoRoute = true
  if RA and RA.Invalidate then RA.Invalidate() end
  local slug = "alchemy"
  local function fu()
    for _, e in pairs(DungeonsForeverDB.prof.follow or {}) do
      if e and e.slug == slug then return e end
    end
  end
  if not fu() then PF.Toggle(slug) end
  -- 逐段走一遍，收每段 HUD 卡片上的次数文本
  local e = fu()
  if not e then return "无跟随状态" end
  local steps = RA.Get(slug, {
    start = 1, onlyAH = PD.Setting("autoOnlyAH"),
    noFormula = PD.Setting("autoNoFormula"),
    learnedOnly = PD.Setting("autoLearnedOnly"),
    target = PD.LvTarget() }).steps
  local n = 0
  local sum = 0
  for i = 1, math.min(#steps, 6) do
    e.step = i
    PF.view = 0
    PF.Sync(); PF.Paint()
    local c = PF.f and PF.f.card
    local txt = (c and c.crafts and c.crafts.__text) or "?"
    local m = tonumber(tostring(txt):match("第?(%d+)次") or tostring(txt):match("(%d+)"))
    if m then sum = sum + m end
    n = n + 1
    out[#out + 1] = string.format("段%d %d-%d: %s", i, steps[i][1], steps[i][2], tostring(txt))
  end
  out[#out + 1] = string.format("前%d段累计 = %d", n, sum)
  return table.concat(out, "\n")
end)
'''


def run(addon, patch, label):
    lua = make_lua(addon, patch)
    lua.execute(DRIVER)
    txt = lua.eval(READ)()
    print('--- %s ---' % label)
    print(txt)
    return sum(int(l.split('=')[-1].strip())
               for l in txt.splitlines() if l.startswith('前'))


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    a = run(addon, NEW, '现状 0.5 / 0.05')
    print()
    b = run(addon, OLD, '对照 0.7 / 0.25')
    print()
    print('前 6 段累计：旧 %d 次 → 新 %d 次（%.2fx）' % (b, a, a / b if b else 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
