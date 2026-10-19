# -*- coding: utf-8 -*-
"""诊断「为什么做到灰」：在段内每个技能点上，列出所有可用配方的真实性价比
metric = cost / P（cost = 材料件数 × 单价，P = 单次制作升点概率），
看当前选中的配方是不是真的最便宜；若是最便宜，则是**成本最小化**的必然结果。

★ 2026-10-09 修：初版有两个致命口径错——
  ① metric 写成 `#材料种类 / 每点次数`，与真实算法 `cost / 升点概率` 量纲相反（一乘一除），
     排序会整体反向；
  ② 只数材料**种类**、不累加**件数**，1 件皮与 5 件皮的配方被当成同价。
  修法：metric = Σ(件数×单价) / P，与 ProfRouteAuto.Simulate 里的 `c.cost / g` 逐字一致。

用法：python _temp/_why_to_grey_probe.py <slug> <段号>
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
    lua.execute('UnitName = function() return "p" end')
    lua.execute('GetRealmName = function() return "r" end')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o=GetBuildInfo; GetBuildInfo=function(...) '
                'local a,b,c,d=o(...); return a,b,c,16001,e end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = { GetAreaInfo = function(id) return "z"..tostring(id) end }
-- 两档价格，与真实运行同构：AH 1000 / 商人直售 500（soldSet 里的材料走商人价）
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
(function(slug, segIdx, atPoints)
  local RA = TF_NS.ProfRouteAuto
  RA.Invalidate()
  local res = RA.Compute(slug, { start = 1, target = 300 })
  local st = res.steps[segIdx]
  if not st then return "无此段" end
  -- ★ 复刻真实候选集：cost = Σ(件数 × 单价)，单价走 soldSet（商人直售 500）/ AH 1000
  local rr = TF_NS.ProfRecipes[slug]
  local sold = {}
  for _, id in ipairs((TF_NS.ProfLeveling[slug] or {}).sold or {}) do sold[id] = true end
  local function unit(id) return sold[id] and 500 or 1000 end
  local cands = {}
  for _, r in ipairs(rr.rows or {}) do
    if type(r[1]) == "number" and type(r[7]) == "number"
       and type(r[10]) == "number" and r[10] > r[7]
       and type(r[12]) == "table" and #r[12] > 0 then
      local cost = 0
      for _, m in ipairs(r[12]) do cost = cost + unit(m[1]) * (m[2] or 1) end
      cands[#cands + 1] = { spell = r[1], learn = r[7], yellow = r[8], green = r[9],
                            grey = r[10], cost = cost }
    end
  end
  local function P(sk, o, y, g, gr)
    if sk < o or sk >= gr then return nil end
    if sk < y then return 1 end
    if sk < g then return 1.0 - (sk - y) / (g - y) * (1.0 - 0.5) end
    if gr == g then return 0.05 end
    return 0.5 - (sk - g) / (gr - g) * (0.5 - 0.05)
  end
  local out = { string.format("段 %d: %d-%d  spell=%d qty=%d", segIdx, st[1], st[2], st[3], st[4]) }
  for _, sk in ipairs(atPoints) do
    local rows = {}
    for _, c in ipairs(cands) do
      local p = P(sk, c.learn, c.yellow, c.green, c.grey)
      if p then rows[#rows + 1] = { spell = c.spell, p = p,
                                    metric = c.cost / p, cost = c.cost,
                                    grey = c.grey, gp = c.cost }
      end
    end
    table.sort(rows, function(a, b) return a.metric < b.metric end)
    local head = {}
    for i = 1, math.min(3, #rows) do
      head[#head + 1] = string.format("%d(料价%d,P%.3f,性价比%.0f,灰%d)"
        , rows[i].spell, rows[i].cost, rows[i].p, rows[i].metric, rows[i].grey)
    end
    -- 当前段的机会成本：若该点它已不是最优，标出「本段仍在做它」的原因
    local cur = rows[1] and rows[1].spell
    out[#out + 1] = string.format("  skill=%3d 候选%2d 最优: %s", sk, #rows,
                                  table.concat(head, " | "))
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
    slug = sys.argv[1] if len(sys.argv) > 1 else 'leatherworking'
    seg = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    lua = make_lua(addon)
    pts = [1, 20, 35, 45, 50, 55, 58, 59, 60]
    if len(sys.argv) > 3:
        pts = [int(x) for x in sys.argv[3].split(',')]
    print(lua.eval(DUMP)(slug, seg, lua_list(lua, pts)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
