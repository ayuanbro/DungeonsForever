# -*- coding: utf-8 -*-
"""证明 HUD 与专业页对同一段的次数/段落指针不一致（+1 改动的真正价值）。

背景（读源码得出）：
  · Simulate 存 { from, cur-1, … } ⇒ st[2] = **最后能做的技能值**（to）。
  · ProfFollow.craftsLeft 却按 `for sk = from, seg[2] - 1` 积分 ⇒ 少算 sk = to 那一点。
  · ProfFollow.derivedStep 用 `if skill < s[2]` ⇒ skill == to 时提前跳到下一段。
  两者都是**按「达到值」语义写的**（即假设 st[2] = 练到的技能值 = to + 1）。

本探针渲染 HUD 真实文本（card.crafts），与专业页同段 st[4] 对比，
并给出「按 HUD 口径（seg[2]-1）」与「按正确口径（seg[2]）」的积分差。

用法：python _temp/_hud_vs_page_probe.py [slug]
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
  PD.Show("alchemy")
  PD.SetTab("leveling")
end
'''

READ = r'''
(function(slug)
  local PD = TF_NS.ProfModule
  local PF = TF_NS.ProfFollow
  local RA = TF_NS.ProfRouteAuto
  DungeonsForeverDB.prof.autoRoute = true
  RA.Invalidate()
  local steps = RA.Get(slug, {
    start = 1, onlyAH = PD.Setting("autoOnlyAH"),
    noFormula = PD.Setting("autoNoFormula"),
    learnedOnly = PD.Setting("autoLearnedOnly"),
    target = PD.LvTarget() }).steps
  -- 断点表（配方本身）
  local rm = {}
  for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do rm[r[1]] = r end
  for sp, ri in pairs((TF_NS.ProfLeveling[slug] or {}).rinfo or {}) do
    if not rm[sp] then rm[sp] = ri end
  end
  local function E(sk, o, y, g, gr)
    if sk < o or sk >= gr then return nil end
    if sk < y then return 1 end
    if sk < g then return 1 / (1 - 0.5 * (sk - y) / (g - y)) end
    return 1 / (0.5 - 0.45 * (sk - g) / (gr - g))
  end
  local function fu()
    for _, e in pairs(DungeonsForeverDB.prof.follow or {}) do
      if e and e.slug == slug then return e end
    end
  end
  if not fu() then PF.Toggle(slug) end
  local e = fu()
  if not e then return "无跟随状态" end
  local out = {}
  local totPage, totHud, totFix, mism = 0, 0, 0, 0
  for i = 1, #steps do
    e.step = i
    PF.view = 0
    PF.Sync(); PF.Paint()
    local c = PF.f and PF.f.card
    local txt = (c and c.crafts and c.crafts.__text) or "?"
    local m = tonumber(tostring(txt):match("(%d+)"))
    local st = steps[i]
    local rec = rm[st[3]]
    local o = rec and (rec[7] or rec.learn)
    local y = rec and (rec[8] or rec.yellow)
    local g = rec and (rec[9] or rec.green)
    local gr = rec and (rec[10] or rec.grey)
    -- 正确口径：st[2] 是「练到的技能值」，最后能做的点是 st[2]-1 ⇒ 积分 [from, st[2]-1]
    local fixed = nil
    if o then
      local t, ok = 0, true
      for sk = st[1], st[2] - 1 do
        local v = E(sk, o, y, g, gr)
        if not v then ok = false break end
        t = t + v
      end
      if ok then fixed = math.ceil(t - 1e-9) end
    end
    totPage = totPage + (st[4] or 0)
    totHud = totHud + (m or 0)
    totFix = totFix + (fixed or 0)
    if m and fixed and m ~= fixed then mism = mism + 1 end
    out[#out + 1] = string.format(
      "段%2d %3d-%3d spell=%-8d 页面=%-4d HUD=%-4s 正确=%-4s %s",
      i, st[1], st[2], st[3], st[4] or 0, tostring(m), tostring(fixed),
      (m and fixed and m ~= fixed) and "★ HUD≠正确" or "")
  end
  out[#out + 1] = string.format(
    "合计：页面 %d ／ HUD %d ／ 正确口径 %d；HUD 与正确口径不一致段 = %d",
    totPage, totHud, totFix, mism)
  return table.concat(out, "\n")
end)
'''


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    slug = sys.argv[1] if len(sys.argv) > 1 else 'leatherworking'
    lua = make_lua(addon)
    lua.execute(DRIVER)
    print(lua.eval(READ)(slug))
    return 0


if __name__ == '__main__':
    sys.exit(main())
