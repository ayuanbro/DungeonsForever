# -*- coding: utf-8 -*-
"""同一段、两个模型：自动路线页（ProfRouteAuto.Gain 线性）vs HUD「大约还需制作N次」（ProfFollow.expPerPoint 经典）。

用户观察：「很多阶段这个配方已经是绿色了，涨点率比较低了」→ 质疑次数不准。
本探针把每个专业自动路线的每一段都跑两遍，找出两处口径不一致的段。

用法：python _temp/_craft_count_cross_check.py
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
    lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
                'local a,b,c,d = o(...); return a,b,c,16001,e end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = { GetAreaInfo = function(id) return "z"..tostring(id) end }
Auctionator = { API = { v1 = {
  GetAuctionPriceByItemID = function(c, id) return 1000 end,
  GetAuctionAgeByItemID  = function(c, id) return 0 end,
  GetVendorPriceByItemID = function(c, id) return 500 end } },
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


# 每段：page 口径 st[4]（线性 Gain 累积）；hud 口径 = ProfFollow 的经典 expPerPoint 积分
DUMP = r'''
(function(slugs)
  local RA = TF_NS.ProfRouteAuto
  local out = {}
  for _, slug in ipairs(slugs) do
    RA.Invalidate()
    local res = RA.Compute(slug, { start = 1, target = 300 })
    if res then
      for _, st in ipairs(res.steps) do
        out[#out + 1] = string.format("%s|%d|%d|%d|%d", slug, st[1], st[2], st[3], st[4])
      end
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


def exp_pp(sk, y, g, gr, learn):
    if sk < y:
        return 1.0
    if sk < g:
        return 1.0 / (1 - 0.5 * (sk - y) / (g - y))
    if sk < gr:
        return 1.0 / (0.5 - 0.45 * (sk - g) / (gr - g))
    return None


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    lua = make_lua(addon)
    raw = lua.eval(DUMP)(lua_list(lua, SLUGS))
    # 断点表
    breaks = {}
    rc = open(os.path.join(addon, 'Core/Data/Data_ProfRecipes.lua'),
              encoding='utf-8', errors='replace').read()
    DESC = r'"(?:[^"\\]|\\.)*"'
    pat = re.compile(r'^\s*\{\s*(\d+),\s*(\d+),\s*\d+,\s*' + DESC + r',\s*' + DESC +
                     r',\s*' + DESC + r',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),', re.M)
    for m in pat.finditer(rc):
        breaks[int(m.group(1))] = tuple(int(m.group(i)) for i in (3, 4, 5, 6))
    # rinfo 兜底（附魔等）
    lvr = open(os.path.join(addon, 'Core/Data/Data_ProfLeveling.lua'),
               encoding='utf-8', errors='replace').read()

    print('%-16s %-10s %-8s %6s %6s %7s  %s'
          % ('专业', '区间', 'spell', '页面', 'HUD', 'HUD/页面', '备注'))
    bad = 0
    total_page, total_hud = 0, 0
    for part in raw.split(';'):
        if not part:
            continue
        slug, a, b, spell, qty = part.split('|')
        a, b, spell, qty = int(a), int(b), int(spell), int(qty)
        total_page += qty
        br = breaks.get(spell)
        if not br:
            print('%-16s %-10s %-8d %6d %6s %7s  %s'
                  % (slug, '%d-%d' % (a, b), spell, qty, '-', '-', '无断点数据'))
            continue
        o, y, g, gr = br
        t = 0.0
        okc = True
        # ★ 区间含端点：段 [a, b] 对应逐点 a..b（少算 b 会漏掉段末深绿点，1/P 可达 14 次）
        for sk in range(a, b + 1):
            e = exp_pp(sk, y, g, gr, o)
            if e is None:
                okc = False
                break
            t += e
        if not okc:
            print('%-16s %-10s %-8d %6d %6s %7s  %s'
                  % (slug, '%d-%d' % (a, b), spell, qty, '-', '-', '中途已灰'))
            continue
        hud = int(t + 0.9999)
        total_hud += hud
        ratio = hud / qty if qty else 0
        flag = ''
        if ratio > 1.1:
            flag = '★ HUD 明显偏大' if ratio > 1.25 else 'HUD 偏大'
            bad += 1
        elif ratio < 0.9:
            flag = 'HUD 偏小'
        print('%-16s %-10s %-8d %6d %6d %6.2fx  %s'
              % (slug, '%d-%d' % (a, b), spell, qty, hud, ratio, flag))
    print('-' * 78)
    print('合计：页面口径 %d 次 ／ HUD 口径 %d 次（比值 %.2fx）；不一致段 %d 条'
          % (total_page, total_hud, total_hud / total_page if total_page else 0, bad))
    return 0


if __name__ == '__main__':
    sys.exit(main())
