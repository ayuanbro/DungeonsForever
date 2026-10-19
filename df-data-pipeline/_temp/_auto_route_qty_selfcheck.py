# -*- coding: utf-8 -*-
"""自校验：Simulate 报出的 qty 是否等于「用模块自己的 Gain 对 [from, to-1] 逐点积分」？

如果两者不等，说明除了模型参数之外，次数累计本身还有偏差（合并 / 取整 / 边界）。

用法：python _temp/_auto_route_qty_selfcheck.py [slug] [GY] [GG]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51


def make_lua(addon, gy, gg):
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
    lua.execute('UnitName = function() return "p" end')
    lua.execute('GetRealmName = function() return "r" end')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o=GetBuildInfo; GetBuildInfo=function(...) '
                'local a,b,c,d=o(...); return a,b,c,16001,e end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = { GetAreaInfo = function(id) return "z"..tostring(id) end }
Auctionator = { API = { v1 = {
  GetAuctionPriceByItemID = function(c,id) return 1000 end,
  GetAuctionAgeByItemID = function(c,id) return 0 end,
  GetVendorPriceByItemID = function(c,id) return 500 end } },
  SavedState = { TimeOfLastGetAllScan = 1796850000 - 3600 } }
''')
    wrap = lua.eval('function(src) local ch=assert(loadstring(src)) '
                    'return function() return ch("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        src = open(os.path.join(addon, rel), encoding='utf-8',
                   errors='replace').read()
        if rel.replace('\\', '/') == 'Core/ProfRouteAuto.lua':
            src = src.replace('local G_YELLOW, G_GREEN = 0.7, 0.25',
                              'local G_YELLOW, G_GREEN = %s, %s' % (gy, gg), 1)
        wrap(src)()
    return lua


DUMP = r'''
(function(slug, GY, GG)
  local RA = TF_NS.ProfRouteAuto
  RA.Invalidate()
  -- ★ 复刻模块自己的 Gain（同一份插值 + 同一组常量）
  local function Gain(skill, o, y, g, gr)
    if skill < o or skill >= gr then return nil end
    if skill < y then return 1.0 end
    if skill < g then
      local span = g - y
      if span <= 0 then return GY end
      return 1.0 - (skill - y) / span * (1.0 - GY)
    end
    local span = gr - g
    if span <= 0 then return GG end
    return GY - (skill - g) / span * (GY - GG)
  end
  local res = RA.Compute(slug, { start = 1, target = 300 })
  local rm = {}
  for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do rm[r[1]] = r end
  for sp, ri in pairs((TF_NS.ProfLeveling[slug] or {}).rinfo or {}) do
    if not rm[sp] then rm[sp] = ri end
  end
  local out = {}
  for i, st in ipairs(res.steps) do
    local rec = rm[st[3]]
    local o = rec and (rec[7] or rec.learn)
    local y = rec and (rec[8] or rec.yellow)
    local g = rec and (rec[9] or rec.green)
    local gr = rec and (rec[10] or rec.grey)
    local integ = -1
    if o then
      -- ★ st[2] = 练到的技能值（Compute 出口已 +1）⇒ 可做点区间 = [st[1], st[2] - 1]
      local t = 0
      local okall = true
      for sk = st[1], st[2] - 1 do
        local p = Gain(sk, o, y, g, gr)
        if not p then okall = false break end
        t = t + 1 / p
      end
      if okall then integ = t end
    end
    out[#out + 1] = string.format("%d,%d-%d,%d,qty=%d,integ=%.2f,diff=%+.2f",
      i, st[1], st[2], st[3], st[4], integ, (integ >= 0) and (st[4] - integ) or -999)
  end
  return table.concat(out, "\n")
end)
'''


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    slug = sys.argv[1] if len(sys.argv) > 1 else 'alchemy'
    gy = sys.argv[2] if len(sys.argv) > 2 else '0.7'
    gg = sys.argv[3] if len(sys.argv) > 3 else '0.25'
    lua = make_lua(addon, gy, gg)
    print('=== %s  G_YELLOW=%s G_GREEN=%s ===' % (slug, gy, gg))
    print(lua.eval(DUMP)(slug, float(gy), float(gg)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
