# -*- coding: utf-8 -*-
"""自动路线次数模型：最小改动对照实验

关键发现（先看代码语义）：
  ProfRouteAuto.Simulate 里是 `crafts = crafts + 1 / g`，即「涨 1 技能点需要 1/g 次制作」
  ⇒ Gain() 必须返回 **单次制作的升点概率 P**（点/次），而不是「收益」的某种缩放。

  现行 Gain 的插值端点：G_YELLOW=0.7、G_GREEN=0.25 ⇒
      黄色段 P: 1.0 → 0.7 （经典应为 1.0 → 0.5）
      绿色段 P: 0.7 → 0.25（经典应为 0.5 → 0.05）
  即绿色段的升点率被高估最多 5 倍（段末 P 报 0.25，实际 0.05）。

本实验只改这两个数字（内存替换，产品文件零触碰），三臂对比：
  A 现行 0.7/0.25
  B 修正 0.5/0.05   ← 与 ProfFollow.expPerPoint（已被攻略次数验证过）等价
  C 现行为基准、B 之后用 ProfFollow 的 craftsLeft 复算 → 验证两处口径是否收敛

用法：python _temp/_auto_route_gain_fix_ab.py
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

OLD_LINE = 'local G_YELLOW, G_GREEN = 0.7, 0.25'
NEW_LINE = 'local G_YELLOW, G_GREEN = 0.5, 0.05'


def make_lua(addon, patch=None):
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
    wrap = lua.eval('function(src)\n'
                    '  local ch = assert(loadstring(src))\n'
                    '  return function() return ch("DungeonsForever", TF_NS) end\n'
                    'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        src = open(os.path.join(addon, rel), encoding='utf-8',
                   errors='replace').read()
        if patch and rel.replace('\\', '/') == 'Core/ProfRouteAuto.lua':
            assert OLD_LINE in src, '常量锚点没找到'
            src = src.replace(OLD_LINE, patch, 1)
        wrap(src)()
    return lua


MEASURE = r'''
(function(slugs, useHud)
  local RA = TF_NS.ProfRouteAuto
  local LV = TF_NS.ProfLeveling
  local out = {}
  for _, slug in ipairs(slugs) do
    RA.Invalidate()
    local res = RA.Compute(slug, { start = 1, target = 300 })
    if not res then out[#out + 1] = slug .. "|nil" else
      local rm = {}
      for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do rm[r[1]] = r end
      for sp, ri in pairs((LV[slug] or {}).rinfo or {}) do if not rm[sp] then rm[sp] = ri end end
      local greenSegs, greenCrafts = 0, 0
      local hudCrafts = 0
      for _, st in ipairs(res.steps) do
        local rec = rm[st[3]]
        local g = rec and (rec[9] or rec.green)
        if g and st[2] - 1 >= g then
          greenSegs = greenSegs + 1
          greenCrafts = greenCrafts + (st[4] or 0)
        end
        -- HUD 口径：整段用 rec 自己的断点，逐点积分（等同从段首做到底）
        local o, y, gg, gr = rec and (rec[7] or rec.learn), rec and (rec[8] or rec.yellow),
                             rec and (rec[9] or rec.green), rec and (rec[10] or rec.grey)
        if o and y and gg and gr and gg > y and gr > gg then
          local t = 0
          for sk = st[1], st[2] - 1 do
            local e
            if sk < y then e = 1
            elseif sk < gg then e = 1 / (1 - 0.5 * (sk - y) / (gg - y))
            elseif sk < gr then e = 1 / (0.5 - 0.45 * (sk - gg) / (gr - gg)) end
            if not e then t = -1 break end
            t = t + e
          end
          if t >= 0 then hudCrafts = hudCrafts + t end
        end
      end
      out[#out + 1] = string.format("%s|%d|%d|%d|%d|%d|%d",
        slug, #res.steps, res.crafts or 0, res.total or 0,
        greenSegs, greenCrafts, math.floor(hudCrafts + 0.5))
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


def run(addon, patch=None):
    lua = make_lua(addon, patch)
    raw = lua.eval(MEASURE)(lua_list(lua, SLUGS), False)
    out = {}
    for part in raw.split(';'):
        if not part:
            continue
        c = part.split('|')
        if len(c) < 7:
            out[c[0]] = None
            continue
        out[c[0]] = dict(slug=c[0], segs=int(c[1]), crafts=int(c[2]),
                         cost=int(c[3]), gsegs=int(c[4]), gcrafts=int(c[5]),
                         hud=int(c[6]))
    return out


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    a = run(addon)
    b = run(addon, NEW_LINE)
    print('%-15s | %-28s | %-28s' % ('专业', '现行 0.7 / 0.25', '修正 0.5 / 0.05'))
    print('%-15s | %6s %7s %9s %10s | %6s %7s %9s %10s'
          % ('', '段数', '总次数', '总花费(金)', '已绿段次数', '段数', '总次数', '总花费(金)', '已绿段次数'))
    print('-' * 102)
    sa = sb = ca = cb = 0
    ga = gb = 0
    for s in SLUGS:
        x, y = a.get(s), b.get(s)
        if not x or not y:
            print('%-15s | %s' % (s, '缺'))
            continue
        sa += x['crafts']; sb += y['crafts']
        ca += x['cost']; cb += y['cost']
        ga += x['gcrafts']; gb += y['gcrafts']
        print('%-15s | %6d %7d %9.0f %10d | %6d %7d %9.0f %10d'
              % (s, x['segs'], x['crafts'], x['cost'] / 10000.0, x['gcrafts'],
                 y['segs'], y['crafts'], y['cost'] / 10000.0, y['gcrafts']))
    print('-' * 102)
    print('合计：次数 %d → %d (%+.0f%%)；花费 %.0f 金 → %.0f 金 (%+.0f%%)'
          % (sa, sb, (sb / sa - 1) * 100, ca / 10000.0, cb / 10000.0,
             (cb / ca - 1) * 100))
    print('      其中「段末已绿」的段：次数 %d → %d；占总量 %.0f%% → %.0f%%'
          % (ga, gb, 100.0 * ga / sa, 100.0 * gb / sb))
    print()
    print('页面次数 vs HUD 口径（ProfFollow 经典模型）在同一段上的差：')
    print('%-15s %10s %10s %10s' % ('专业', '现行页面', '修正后页面', 'HUD 口径'))
    for s in SLUGS:
        x, y = a.get(s), b.get(s)
        if not x or not y:
            continue
        print('%-15s %10d %10d %10d  （修正后 页面/HUD = %.3f）'
              % (s, x['crafts'], y['crafts'], y['hud'],
                 y['crafts'] / y['hud'] if y['hud'] else 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
