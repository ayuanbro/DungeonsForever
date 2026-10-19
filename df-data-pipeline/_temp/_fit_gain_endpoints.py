# -*- coding: utf-8 -*-
"""用固定路线的攻略次数（wowhead 实采，独立数据）反过来标定自动路线的升点概率模型。

做法：对每个可检验的攻略段 [a,b)（段内每涨 1 点需要 1/P(sk) 次），
      在 (G_YELLOW, G_GREEN) 网格上算期望次数，取与攻略次数的相对误差最优的一组。

  P(sk):  sk < yellow            → 1.0
          yellow <= sk < green   → 1.0 → G_YELLOW
          green  <= sk < grey    → G_YELLOW → G_GREEN

用法：python _temp/_fit_gain_endpoints.py
"""
import os
import re
import sys

ADDON = os.environ.get('DF_ADDON_ROOT', r'D:\workspace\DungeonsForever')


def parse():
    base = os.path.join(ADDON, 'Core', 'Data')
    lv = open(base + '/Data_ProfLeveling.lua', encoding='utf-8',
              errors='replace').read()
    rc = open(base + '/Data_ProfRecipes.lua', encoding='utf-8',
              errors='replace').read()
    DESC = r'"(?:[^"\\]|\\.)*"'
    pat = re.compile(r'^\s*\{\s*(\d+),\s*(\d+),\s*\d+,\s*' + DESC + r',\s*' +
                     DESC + r',\s*' + DESC + r',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),',
                     re.M)
    br = {}
    for m in pat.finditer(rc):
        br[int(m.group(1))] = tuple(int(m.group(i)) for i in (3, 4, 5, 6))
    # 解析每个专业的固定路线 steps
    res, cur = [], None
    for line in lv.splitlines():
        m = re.match(r'\s*\["([a-z_]+)"\] = \{', line)
        if m:
            cur = m.group(1)
            continue
        if cur is None:
            continue
        if line.strip().startswith('shopping') or line.strip().startswith('rinfo'):
            cur = None
            continue
        m2 = re.match(r'\s*\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\},', line)
        if m2:
            a, b, sid, q = (int(m2.group(i)) for i in (1, 2, 3, 4))
            if 0 < a < b <= 300 and q > 0:
                res.append((cur, a, b, sid, q))
    return br, res


def integrate(a, b, o, y, g, gr, GY, GG):
    """[a, b) 区间，每点 1/P 求和；任一 P 为 nil 返回 None。"""
    t = 0.0
    for sk in range(a, b):
        if sk < o or sk >= gr:
            return None
        if sk < y:
            p = 1.0
        elif sk < g:
            span = g - y
            p = GY if span <= 0 else 1.0 - (sk - y) / span * (1.0 - GY)
        else:
            span = gr - g
            p = GG if span <= 0 else GY - (sk - g) / span * (GY - GG)
        if p <= 0:
            return None
        t += 1.0 / p
    return t


def main():
    br, segs = parse()
    rows = []
    for slug, a, b, sid, q in segs:
        r = br.get(sid)
        if not r:
            continue
        o, y, g, gr = r
        if not (o < y <= g < gr):
            continue
        if any((sk < o or sk >= gr) for sk in range(a, b)):
            continue
        rows.append((slug, a, b, sid, q, o, y, g, gr))
    print('可检验攻略段：%d 条（跳过无断点 / 越界 %d 条）'
          % (len(rows), len(segs) - len(rows)))
    guidesum = sum(r[4] for r in rows)

    def score(GY, GG):
        errs, tot = [], 0.0
        for slug, a, b, sid, q, o, y, g, gr in rows:
            e = integrate(a, b, o, y, g, gr, GY, GG)
            if e is None:
                continue
            tot += e
            errs.append(abs(e - q) / q)
        return (sum(errs) / len(errs)) if errs else 9e9, tot

    print()
    print('%-22s %8s %10s %10s' % ('模型（黄端点/绿端点）', '平均相对误差', '期望总次数', '攻略/模型'))
    cands = [('现行 0.70 / 0.25', 0.70, 0.25),
             ('经典 0.50 / 0.05', 0.50, 0.05),
             ('0.75 / 0.25', 0.75, 0.25),
             ('0.70 / 0.15', 0.70, 0.15),
             ('0.60 / 0.10', 0.60, 0.10),
             ('0.50 / 0.10', 0.50, 0.10),
             ('0.40 / 0.05', 0.40, 0.05)]
    for name, gy, gg in cands:
        e, tot = score(gy, gg)
        print('%-22s %7.2f%% %10.0f %10.3f'
              % (name, e * 100, tot, guidesum / tot if tot else 0))
    print('%-22s %8s %10d' % ('（攻略基准）', '—', guidesum))

    print()
    print('网格扫描（找误差最小的一组）：')
    best = None
    gy = 0.30
    while gy <= 1.0001:
        gg = 0.02
        while gg <= 0.4001:
            if gg < gy:
                e, tot = score(round(gy, 2), round(gg, 2))
                if best is None or e < best[0]:
                    best = (e, round(gy, 2), round(gg, 2), tot)
            gg += 0.01
        gy += 0.02
    print('  最优：G_YELLOW=%.2f  G_GREEN=%.2f  →  平均相对误差 %.2f%%，期望总次数 %.0f（攻略 %d，比 %.3f）'
          % (best[1], best[2], best[0] * 100, best[3], guidesum, guidesum / best[3]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
