# -*- coding: utf-8 -*-
"""回答「为什么习惯性把一个配方做到灰为止」：把每段的制作量按颜色带拆开。

对自动路线的每段，用与模块一致的经典 P 模型逐点积分，统计：
  · 橙/黄带（sk < green）的制作次数
  · 绿带（green <= sk < grey）的制作次数   ← 用户问的那部分
并给出「每段止点离 grey 有多近」。

用法：python _temp/_green_tail_probe.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

SLUGS = ['alchemy', 'blacksmithing', 'leatherworking', 'tailoring',
         'enchanting', 'engineering', 'cooking']


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
    lf = lua.eval('function(rel)\n'
                  '  local ch = loadfile(ADDON_ROOT .. "/" .. rel)\n'
                  '  if not ch then return nil end\n'
                  '  return function() return ch("DungeonsForever", TF_NS) end\n'
                  'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        c = lf(rel)
        if c is None:
            raise RuntimeError('loadfile nil: ' + rel)
        c()
    return lua


DUMP = r'''
(function(slugs)
  local RA = TF_NS.ProfRouteAuto
  local out = {}
  local function P(sk, o, y, g, gr)
    if sk < o or sk >= gr then return nil end
    if sk < y then return 1 end
    if sk < g then return 1 / (1 - 0.5 * (sk - y) / (g - y)) end
    return 1 / (0.5 - 0.45 * (sk - g) / (gr - g))
  end
  for _, slug in ipairs(slugs) do
    RA.Invalidate()
    local res = RA.Compute(slug, { start = 1, target = 300 })
    if res then
      local rm = {}
      for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do rm[r[1]] = r end
      for sp, ri in pairs((TF_NS.ProfLeveling[slug] or {}).rinfo or {}) do
        if not rm[sp] then rm[sp] = ri end
      end
      local tot, greenTot, segs, reachGrey = 0, 0, 0, 0
      for _, st in ipairs(res.steps) do
        local rec = rm[st[3]]
        local o = rec and (rec[7] or rec.learn)
        local y = rec and (rec[8] or rec.yellow)
        local gg = rec and (rec[9] or rec.green)
        local gr = rec and (rec[10] or rec.grey)
        if o and y and gg and gr then
          segs = segs + 1
          local all, green = 0, 0
          for sk = st[1], st[2] do
            local e = P(sk, o, y, gg, gr)
            if not e then break end
            all = all + e
            if sk >= gg then green = green + e end
          end
          tot = tot + all
          greenTot = greenTot + green
          -- 止点是否已到 grey（即做到灰为止）
          if st[2] + 1 >= gr then reachGrey = reachGrey + 1 end
        end
      end
      out[#out + 1] = string.format("%s|%d|%.0f|%.0f|%.1f|%d",
        slug, segs, tot, greenTot, greenTot / tot * 100, reachGrey)
    end
  end
  return table.concat(out, ";")
end)
'''


def lua_list(lua, items):
    t = lua.table()
    for i, v in enumerate(items, 1):
        t[i] = v
    return t


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    lua = make_lua(addon)
    raw = lua.eval(DUMP)(lua_list(lua, SLUGS))
    print('%-16s %5s %9s %11s %9s %14s'
          % ('专业', '段数', '总次数', '绿带次数', '绿带占比', '止点已到灰的段'))
    print('-' * 74)
    T = G = S = R = 0
    for part in raw.split(';'):
        if not part:
            continue
        slug, segs, tot, green, pct, rg = part.split('|')
        segs, tot, green, pct, rg = int(segs), float(tot), float(green), float(pct), int(rg)
        T += tot; G += green; S += segs; R += rg
        print('%-16s %5d %9.0f %11.0f %8.1f%% %11d/%d'
              % (slug, segs, tot, green, pct, rg, segs))
    print('-' * 74)
    print('合计：%d 段 / %d 次，其中绿带 %d 次 = %.1f%%；%d/%d 段的止点已经贴到灰点'
          % (S, T, G, G / T * 100, R, S))
    return 0


if __name__ == '__main__':
    sys.exit(main())
