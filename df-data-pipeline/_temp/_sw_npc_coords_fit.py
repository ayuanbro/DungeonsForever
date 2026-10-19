# -*- coding: utf-8 -*-
"""
暴风城「经典边界 → 新生代边界」线性变换拟合（补 1748 伯瓦尔用）
=========================================================
Questie Classic 库与 Wotlk 库对同一批暴风城 NPC 各记一套百分比坐标，两套之间的差异
正是「地图边界换版」。用两库都收录、且各自只有单一 spawn 点的 NPC 做配对，
最小二乘拟合 x' = a·x + b（y 同理），再用残差判断该变换是否严格成立。
产物：拟合系数 + 残差分位 + 对 1748（巫妖王库缺）的预测值。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADDONS = os.path.dirname(os.path.dirname(HERE))
DB = os.path.join(ADDONS, "Questie", "Database")
CLS = os.path.join(DB, "Classic", "classicNpcDB.lua")
WOT = os.path.join(DB, "Wotlk", "wotlkNpcDB.lua")

# 只取这两张「同一物理区域」的地图（1519 = 东部王国 → 1453 暴风城）
WANT = (1453,)


def load(path):
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r'\n\[(\d+)\] = \{', raw):
        nid = int(m.group(1))
        m2 = re.compile(r'\n\[\d+\] = \{').search(raw, m.end())
        seg = raw[m.end(): m2.start() if m2 else len(raw)]
        pts = []
        for mm in re.finditer(r'\[1519\]\s*=\s*\{', seg):
            i = mm.end() - 1
            d = 0
            blk = None
            for k in range(i, min(i + 40000, len(seg))):
                if seg[k] == '{':
                    d += 1
                elif seg[k] == '}':
                    d -= 1
                    if d == 0:
                        blk = seg[i:k + 1]
                        break
            if not blk:
                continue
            for pm in re.finditer(r'\{\s*([\d.]+)\s*,\s*([\d.]+)', blk):
                pts.append((float(pm.group(1)), float(pm.group(2))))
        out[nid] = pts
    return out


def fit(pairs):
    """最小二乘 y = a·x + b（n≥2）"""
    n = len(pairs)
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxx = sum(p[0] * p[0] for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    den = n * sxx - sx * sx
    if den == 0:
        return 1.0, 0.0
    a = (n * sxy - sx * sy) / den
    b = (sy - a * sx) / n
    return a, b


def pct(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return s[i]


cls = load(CLS)
wot = load(WOT)
print("Classic NPC %d 条 / Wotlk NPC %d 条" % (len(cls), len(wot)))

xp, yp = [], []
for nid, cp in cls.items():
    wp = wot.get(nid)
    if not wp or len(cp) != 1 or len(wp) != 1:
        continue
    xp.append((cp[0][0], wp[0][0]))
    yp.append((cp[0][1], wp[0][1]))

ax, bx = fit(xp)
ay, by = fit(yp)
print("配对 %d 组" % len(xp))
print("x' = %.6f·x + %.4f" % (ax, bx))
print("y' = %.6f·y + %.4f" % (ay, by))

rx = [abs(ax * a + bx - b) for a, b in xp]
ry = [abs(ay * a + by - b) for a, b in yp]
print("残差 x: 均值 %.3f / p50 %.3f / p95 %.3f / max %.3f" % (sum(rx) / len(rx), pct(rx, .5), pct(rx, .95), max(rx)))
print("残差 y: 均值 %.3f / p50 %.3f / p95 %.3f / max %.3f" % (sum(ry) / len(ry), pct(ry, .5), pct(ry, .95), max(ry)))

# 用 19 条里的 18 组实测配对（现行值 → Questie 巫妖王值）做独立交叉检验
PAIRS = [
    (332, 75.8, 59.8, 78.3, 70.7), (656, 65.2, 21.2, 70.3, 40.8), (928, 37.2, 33.0, 48.4, 50.2),
    (1284, 39.4, 27.4, 50.3, 45.5), (1416, 51.6, 12.2, 59.7, 33.8), (1646, 49.0, 30.2, 57.7, 47.9),
    (1719, 41.0, 57.0, 51.5, 69.4), (1721, 66.8, 46.4, 73.3, 55.5), (2198, 33.2, 70.4, 56.4, 74.1),
    (2285, 74.0, 29.2, 76.9, 47.8), (4984, 21.4, 55.4, 36.2, 67.6), (5384, 64.2, 20.8, 69.5, 40.4),
    (5413, 57.4, 16.0, 64.6, 37.2), (6171, 39.4, 30.4, 50.5, 47.5), (6579, 55.4, 12.4, 62.6, 34.1),
    (7917, 40.4, 30.4, 51.0, 48.4), (12336, 42.0, 24.8, 52.6, 43.2), (14450, 47.2, 38.4, 56.3, 54.0),
]
ex = max(abs(ax * p[1] + bx - p[3]) for p in PAIRS)
ey = max(abs(ay * p[2] + by - p[4]) for p in PAIRS)
print("\n用 19 条清单里 18 组做独立检验：最大偏差 x %.2f / y %.2f" % (ex, ey))
for p in PAIRS:
    px, py = ax * p[1] + bx, ay * p[2] + by
    print("  %-7d 预测 %6.1f,%6.1f  实取 %6.1f,%6.1f  Δ %.2f,%.2f" % (p[0], px, py, p[3], p[4], px - p[3], py - p[4]))

print("\n1748 伯瓦尔·弗塔根公爵（现行 77.4, 18.4）→ 预测 %.1f, %.1f" % (ax * 77.4 + bx, ay * 18.4 + by))
print("校验：用 18 组自身拟合 →", end=" ")
a2x, b2x = fit([(p[1], p[3]) for p in PAIRS])
a2y, b2y = fit([(p[2], p[4]) for p in PAIRS])
print("x %.6f·x+%.4f / y %.6f·y+%.4f → 1748 = %.1f, %.1f"
      % (a2x, b2x, a2y, b2y, a2x * 77.4 + b2x, a2y * 18.4 + b2y))

sys.exit(0)
