# -*- coding: utf-8 -*-
"""量化「为什么习惯性把一个配方做到灰」。

根因假设（读源码得出，本探针负责量化）：
  Simulate 选段时把 bestMetric = cost / Gain(from) **冻结在段首**（第 340 行），
  之后逐点只与这个冻结值比较（第 376 行 `c.cost / g2 < bestMetric - 1e-9`）。
  ⇒ 一个「随技能升高才变便宜」的配方（典型：低阶材料 1 件 vs 高阶材料 3 件，
     高阶 P 掉得慢所以比值随时间反超）永远拿不到切换机会 ——
     段只能做到「配方变灰」或「同点起就有更便宜的配方」才结束。

本探针对每段逐点复核（stale = 按冻结 metric / live = 按当点最优）：
  · stale_better —— 该点已存在严格更便宜的配方（= 算法应换未换的点数）
  · 段是否因此贴到灰点
对外只读，不改产品代码。

用法：python _temp/_stale_metric_probe.py [slug ...]
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
    wrap = lua.eval('function(src) local ch=assert(loadstring(src)) '
                    'return function() return ch("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        wrap(open(os.path.join(addon, rel), encoding='utf-8',
                  errors='replace').read())()
    return lua


DUMP = r'''
(function(slugs)
  local RA = TF_NS.ProfRouteAuto
  local out = {}
  for _, slug in ipairs(slugs) do
    RA.Invalidate()
    local res = RA.Compute(slug, { start = 1, target = 300 })
    if res then
      local sold = {}
      for _, id in ipairs((TF_NS.ProfLeveling[slug] or {}).sold or {}) do sold[id] = true end
      local function unit(id) return sold[id] and 500 or 1000 end
      local cands, greyOf = {}, {}
      for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do
        if type(r[1]) == "number" and type(r[7]) == "number"
           and type(r[10]) == "number" and r[10] > r[7]
           and type(r[12]) == "table" and #r[12] > 0 then
          local cost = 0
          for _, m in ipairs(r[12]) do cost = cost + unit(m[1]) * (m[2] or 1) end
          cands[#cands + 1] = { spell = r[1], learn = r[7], yellow = r[8], green = r[9],
                                grey = r[10], cost = cost }
          greyOf[r[1]] = r[10]
        end
      end
      local function P(sk, c)
        if sk < c.learn or sk >= c.grey then return nil end
        if sk < c.yellow then return 1 end
        if sk < c.green then return 1 - (sk - c.yellow) / (c.green - c.yellow) * 0.5 end
        if c.grey == c.green then return 0.05 end
        return 0.5 - (sk - c.green) / (c.grey - c.green) * 0.45
      end
      local function metricAt(sk, spell)
        for _, c in ipairs(cands) do
          if c.spell == spell then
            local p = P(sk, c)
            if p then return c.cost / p end
          end
        end
        return nil
      end
      for i, st in ipairs(res.steps) do
        local frozen = metricAt(st[1], st[3])
        local stale, total, alt = 0, 0, nil
        if frozen then
          for sk = st[1], st[2] do
            total = total + 1
            local best, bestSpell = math.huge, nil
            for _, c in ipairs(cands) do
              local p = P(sk, c)
              if c.learn <= sk and p then
                local m = c.cost / p
                if m < best - 1e-9 then best, bestSpell = m, c.spell end
              end
            end
            if bestSpell and bestSpell ~= st[3] then
              stale = stale + 1
              alt = alt or bestSpell
            end
          end
        end
        local gr = greyOf[st[3]]
        out[#out + 1] = string.format("%s|%d|%d-%d|%d|%d|%d|%d|%s",
          slug, i, st[1], st[2], st[3], total, stale,
          (gr and st[2] + 1 >= gr) and 1 or 0, tostring(alt))
      end
    end
  end
  return table.concat(out, "\n")
end)
'''


def lua_list(lua, items):
    t = lua.table()
    for i, v in enumerate(items, 1):
        t[i] = v
    return t


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    slugs = sys.argv[1:] or SLUGS
    lua = make_lua(addon)
    raw = lua.eval(DUMP)(lua_list(lua, slugs))
    print('%-16s %3s %-11s %6s %5s %6s %7s %s'
          % ('专业', '段', '区间', 'spell', '点数', '应换点', '贴灰', '可换成的配方'))
    tot_seg = tot_stale = tot_pt = tot_tail = 0
    alts = {}
    for line in raw.splitlines():
        slug, i, rng, spell, total, stale, tail, alt = line.split('|')
        tot_seg += 1
        tot_pt += int(total)
        tot_stale += int(stale)
        tot_tail += int(tail)
        if alt and alt != 'nil':
            alts[alt] = alts.get(alt, 0) + 1
        flag = '★' if int(stale) > 0 else ' '
        print('%-16s %3s %-11s %6s %5s %6s %7s %s %s'
              % (slug, i, rng, spell, total, stale, tail, alt, flag))
    print('-' * 92)
    print('段数 %d；技能点合计 %d；「已出现更便宜配方却仍沿用旧配方」的点 = %d（%.1f%%）；贴灰段 %d'
          % (tot_seg, tot_pt, tot_stale,
             100.0 * tot_stale / tot_pt if tot_pt else 0, tot_tail))
    if alts:
        top = sorted(alts.items(), key=lambda kv: -kv[1])[:6]
        print('算法最常漏换的替代配方：%s'
              % ', '.join('%s×%d' % (k, v) for k, v in top))
    return 0


if __name__ == '__main__':
    sys.exit(main())
