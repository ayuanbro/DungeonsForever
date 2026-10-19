# -*- coding: utf-8 -*-
"""对照实验：把 ProfRouteAuto 的 Gain() 换成「经典升点概率」模型后，自动路线怎么变。

做法：读产品文件到内存 → 注入替换 Gain 的插值端点（只改内存里的字符串，产品文件零触碰），
      —— 再把 G_YELLOW/G_GREEN 之外的分母也改掉是做不到的（Gain 是解析式），
      所以这里直接整段替换 Gain 函数体为经典口径：
        橙 = 1.0（1 次/点）
        黄 = 1/(1-0.5t)      → 1.0 → 2.0  次/点
        绿 = 1/(0.5-0.45t)   → 2.0 → 20.0 次/点（灰点趋近 20）

关注三件事：
  ① 总次数（旧 vs 新）
  ② 出现「段末已绿」的段数（recipe 已绿还继续做的段）
  ③ 总花费（路线成本）—— 修了之后是变贵还是变便宜

用法：python _temp/_auto_route_classic_gain.py
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

OLD_GAIN = """local function Gain(skill, c)
    if skill < c.learn or skill >= c.grey then return nil end
    if skill < c.yellow then return 1.0 end
    if skill < c.green then
        local span = c.green - c.yellow
        if span <= 0 then return G_YELLOW end
        local t = (skill - c.yellow) / span
        return 1.0 - t * (1.0 - G_YELLOW)
    end
    local span = c.grey - c.green
    if span <= 0 then return G_GREEN end
    local t = (skill - c.green) / span
    return G_YELLOW - t * (G_YELLOW - G_GREEN)
end"""

NEW_GAIN = """local function Gain(skill, c)
    -- MUT: 经典升点概率口径（与 ProfFollow.expPerPoint 同源）
    if skill < c.learn or skill >= c.grey then return nil end
    if skill < c.yellow then return 1.0 end
    if skill < c.green then
        local span = c.green - c.yellow
        if span <= 0 then return 0.5 end
        local t = (skill - c.yellow) / span
        return 1.0 / (1.0 - 0.5 * t)
    end
    local span = c.grey - c.green
    if span <= 0 then return 0.05 end
    local t = (skill - c.green) / span
    return 1.0 / (0.5 - 0.45 * t)
end"""


def make_lua(addon, gain_src=None):
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
    wrapper = lua.eval(
        'function(src)\n'
        '  local chunk = assert(loadstring(src))\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        p = os.path.join(addon, rel)
        with open(p, encoding='utf-8', errors='replace') as fh:
            src = fh.read()
        if gain_src and rel.replace('\\', '/') == 'Core/ProfRouteAuto.lua':
            assert OLD_GAIN in src, 'Gain 锚点没找到，产品文件变了'
            src = src.replace(OLD_GAIN, gain_src, 1)
        try:
            wrapper(src)()
        except Exception as e:
            raise RuntimeError('%s: %s' % (rel, str(e)[:200]))
    return lua


MEASURE = r'''
(function(slugs)
  local RA = TF_NS.ProfRouteAuto
  local LV = TF_NS.ProfLeveling
  local out = {}
  for _, slug in ipairs(slugs) do
    RA.Invalidate()
    local res = RA.Compute(slug, { start = 1, target = 300 })
    if res then
      local rm = {}
      for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do rm[r[1]] = r end
      for sp, ri in pairs((LV[slug] or {}).rinfo or {}) do if not rm[sp] then rm[sp] = ri end end
      local greenSegs, greenCrafts, gapCrafts = 0, 0, 0
      for _, st in ipairs(res.steps) do
        local rec = rm[st[3]]
        local g = rec and (rec[9] or rec.green)
        if g and st[2] - 1 >= g then
          greenSegs = greenSegs + 1
          greenCrafts = greenCrafts + (st[4] or 0)
        end
      end
      out[#out + 1] = string.format("%s|%d|%d|%s|%d|%d",
        slug, #res.steps, res.crafts or 0, tostring(res.total or 0),
        greenSegs, greenCrafts)
    else
      out[#out + 1] = slug .. "|nil"
    end
  end
  return table.concat(out, ";")
end)
'''


def run(label, addon, gain=None):
    lua = make_lua(addon, gain)
    f = lua.eval(MEASURE)
    raw = f(lua.table(*SLUGS)) if False else f(_lua_list(lua, SLUGS))
    rows = []
    for part in raw.split(';'):
        c = part.split('|')
        rows.append(c)
    print('%-14s %-6s %-8s %-10s %-10s %s'
          % (label, '段数', '总次数', '总花费(铜)', '已绿段数', '已绿段次数'))
    for c in rows:
        if len(c) < 6:
            print('%-14s %s' % (label, c[0]))
            continue
        print('%-14s %-6s %-8s %-10s %-10s %s'
              % (c[0], c[1], c[2], c[3], c[4], c[5]))
    return {c[0]: c for c in rows if len(c) >= 6}


def _lua_list(lua, items):
    t = lua.table()
    for i, v in enumerate(items, 1):
        t[i] = v
    return t


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    base = run('现口径', addon)
    print()
    new = run('经典口径', addon, NEW_GAIN)
    print()
    print('%-18s %8s %8s %8s' % ('专业', '次数 旧', '次数 新', '倍数'))
    for s in SLUGS:
        if s in base and s in new:
            a, b = int(base[s][2]), int(new[s][2])
            print('%-18s %8d %8d %8.2fx' % (s, a, b, (b / a) if a else 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
