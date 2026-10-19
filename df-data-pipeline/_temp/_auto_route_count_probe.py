# -*- coding: utf-8 -*-
"""自动路线「制作次数」模型审查探针（2026-10-12）。

只读产品文件、只在内存桩里跑，不写任何产品文件。

目的：用户质疑「很多阶段配方已经是绿色了，涨点率比较低，你大于制作次数是正确的吗？」

本探针把 RA.Compute 产出的每段打成一行：
  区间 | spell | 次数 | 区间长度 | 次数/区间 | 该段起点/终点的 Gain 值 | 配方窗口 learn/yellow/green/grey

并对比三种口径：
  ① 实现口径（ProfRouteAuto.Gain：橙 1.0 / 黄线性 1.0→0.7 / 绿线性 0.7→0.25）
  ② 经典口径（ProfFollow.expPerPoint：黄 1/(1-0.5t) 即 1.0→2.0；绿 1/(0.5-0.45t) 即 2.0→20）
     —— 即升点概率 = 1/G，绿色段真的需要 5~20 次/点
  ③ 攻略口径（Data_ProfLeveling.lv.steps 的预置次数）

用法：
  python _temp/_auto_route_count_probe.py [slug]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51

FAILS = []


def load_lua(addon, build=16001):
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('BG.hui.OnThemeChange = function(fn) end')
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('UnitName = function() return "探针角色" end')
    lua.execute('GetRealmName = function() return "测试服" end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d = orig(...); return a, b, c, %d, e end end' % build)
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "测区" .. tostring(id) end,
}
-- Auctionator 桩：所有物品单价固定 1000 铜（≈10 银），保证所有配方都「有价」
Auctionator = { API = { v1 = {
  GetAuctionPriceByItemID = function(caller, id) return 1000 end,
  GetAuctionAgeByItemID  = function(caller, id) return 0 end,
  GetVendorPriceByItemID = function(caller, id) return 500 end,
} } }
Auctionator.SavedState = { TimeOfLastGetAllScan = 1796850000 - 3600 }
''')
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        c = loadfile(rel)
        if c is None:
            raise RuntimeError('loadfile nil: ' + rel)
        c()
    return lua


DUMP = r'''
(function(slug)
  local RA = TF_NS.ProfRouteAuto
  local PD = TF_NS.ProfModule
  RA.Invalidate()
  local res = RA.Compute(slug, { start = 1, target = 300 })
  if not res then return nil end
  -- 配方查找表（rows + rinfo）
  local rm = {}
  local rr = TF_NS.ProfRecipes[slug]
  for _, r in ipairs((rr and rr.rows) or {}) do rm[r[1]] = r end
  for sp, ri in pairs((TF_NS.ProfLeveling[slug] or {}).rinfo or {}) do
    if not rm[sp] then rm[sp] = ri end
  end
  local out = {}
  for i, st in ipairs(res.steps or {}) do
    local rec = rm[st[3]]
    local lrn = rec and (rec[7] or rec.learn)
    local y   = rec and (rec[8] or rec.yellow)
    local g   = rec and (rec[9] or rec.green)
    local gr  = rec and (rec[10] or rec.grey)
    local learns = y and (y - lrn) or -1
    local span = (st[2] - st[1])
    out[#out + 1] = {
      from = st[1], to = st[2], spell = st[3], qty = st[4],
      cost = st.cost or -1, spans = span,
      learn = lrn or -1, yellow = y or -1, green = g or -1, grey = gr or -1,
      unpriced = st.unpriced and 1 or 0, est = st.est and 1 or 0,
    }
  end
  local gaps = {}
  for _, gp in ipairs(res.gaps or {}) do gaps[#gaps + 1] = { gp[1], gp[2] } end
  return out, gaps, res.crafts or -1, #(res.steps or {})
end)
'''


def exp_per_point(sk, o, y, g, gr):
    """ProfFollow 的经典口径（返回「每点需要几次」）。"""
    if sk < y:
        return 1.0
    if sk < g:
        return 1.0 / (1 - 0.5 * (sk - y) / (g - y))
    if sk < gr:
        return 1.0 / (0.5 - 0.45 * (sk - g) / (gr - g))
    return None


def classic_crafts(a, b, o, y, g, gr):
    t = 0.0
    for sk in range(a, b):
        e = exp_per_point(sk, o, y, g, gr)
        if e is None:
            return None
        t += e
    return t


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    slug = sys.argv[1] if len(sys.argv) > 1 else 'alchemy'
    lua = load_lua(addon)
    dump = lua.eval(DUMP)
    got = dump(slug)
    if got is None:
        print('Compute 返回 nil：%s' % slug)
        return 1
    steps, gaps, total_crafts, n = got
    steps = list(steps.values()) if hasattr(steps, 'values') else list(steps)
    gaps = list(gaps.values()) if hasattr(gaps, 'values') else list(gaps)
    print('=' * 100)
    print('专业 %s：%d 段，总次数 %s' % (slug, n, total_crafts))
    print('=' * 100)
    print('%-12s %-8s %5s %5s %7s  %-26s %s'
          % ('区间', 'spell', '次数', '段长', '次/点', '配方窗口 橙黄绿灰', '端点 Gain（实/经）'))
    for s in steps:
        f, t = s['from'], s['to']
        span = s['spans']
        qty = s['qty']
        o, y, g, gr = s['learn'], s['yellow'], s['green'], s['grey']
        per = (qty / span) if span > 0 else 0
        win = '%d/%d/%d/%d' % (o, y, g, gr) if o > 0 else '（无断点）'
        cls = classic_crafts(f, t, o, y, g, gr) if o > 0 else None
        extra = '经典≈%.0f' % cls if cls is not None else ''
        # 段末是不是「已经绿了」：终点-1 技能值的颜色档
        col = ''
        if o > 0 and t - 1 >= g:
            col = '（段末已绿）'
        elif o > 0 and t - 1 >= y:
            col = '（段末已黄）'
        ratio = ('%.2fx' % (cls / qty)) if (cls and qty > 0) else ''
        print('%-12s %-8s %5d %5d %7.2f  %-26s %-10s %-6s %s'
              % ('%d-%d' % (f, t), s['spell'], qty, span, per, win, extra, ratio, col))
    if gaps:
        print('缺口：' + ', '.join('%d-%d' % (a, b) for a, b in gaps))
    # 总量对比
    tot_cls = 0.0
    for s in steps:
        o, y, g, gr = s['learn'], s['yellow'], s['green'], s['grey']
        if o > 0:
            c = classic_crafts(s['from'], s['to'], o, y, g, gr)
            tot_cls += (c or 0)
    print('-' * 100)
    print('总次数：实现口径 %s ／ 经典概率口径 %.0f ／ 比值 %.2fx'
          % (total_crafts, tot_cls, (tot_cls / total_crafts) if total_crafts else 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
