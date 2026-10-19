# -*- coding: utf-8 -*-
"""把「用户在地图截图上手绘的目标位置」反解成 Data_BossPos 的百分比坐标。

为什么需要它
------------
用户经常给一张游戏内「地图」页截图，在上面画个圈（淡黄环）说「把 XX 移到这里」。
截图里的像素 → 地图画布的百分比是**线性**关系（等比缩放 + 平移），所以：
    用 2 个以上「能在截图里认出图标中心」的已知钉点拟合
        pct_x = a*px_x + c        pct_y = b*px_y + d
    再把手绘标记的**中心像素**代回去，就得到目标百分比。
实测残差 < 0.2 个百分点（≈1.5px），足够钉点级精度。

坐标的单位口径
--------------
用户说的裸数字位移 = **WoW UI 像素**（要百分比会写「%」）。地图画布
`M.MAP_W` = 663、`M.MAP_H` = 442 ⇒ 1px = 1/663*100 = 0.1508%（x）、1/442*100 = 0.2262%（y）。

怎么用
------
1) 先量像素：截图里 pin 图标是圆盘，按色相分辨（青/黄绿/橙/红…），
   本文件 find_blobs() 给了一个够用的连通域工具；手绘标记（淡黄环）
   颜色约 rgb(228,195,103)，判据见 MARKER_RGB。
2) 组装 refs / targets 调 solve()，或直接改本文件末尾的 __main__ 自检数据。

⚠️ 改完坐标要写回**数据源**：ART 瓦片副本的第 1 层在 `_temp/_bosspos_draft.json`，
   2+ 层在 `_temp/_bosspos_floors.json`（自制手绘图也在 floors）。
   然后 `gen_boss_pos.py` → `sync_beta.py --apply` → `run_all_checks.py`。
"""
import json
import os
import re
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)

# 手绘淡黄环的典型颜色（JPEG 压缩后仍稳定）
MARKER_RGB = (228, 195, 103)


# ---------------------------------------------------------------- 像素工具
def find_blobs(mask, minsize=60, box=None, maxn=6):
    """8 邻域连通域；box=(x0,x1,y0,y1) 限定搜索区。返回按面积降序的
    [(n, cx, cy, x0, x1, y0, y1), ...]。"""
    import numpy as np
    h, w = mask.shape
    m = mask
    if box:
        m = np.zeros_like(mask)
        x0, x1, y0, y1 = box
        m[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
    seen = np.zeros_like(m, dtype=bool)
    out = []
    ys, xs = np.nonzero(m)
    for y0_, x0_ in zip(ys, xs):
        if seen[y0_, x0_]:
            continue
        q = deque([(y0_, x0_)])
        seen[y0_, x0_] = True
        pts = []
        while q:
            y, x = q.popleft()
            pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
        if len(pts) >= minsize:
            P = np.array(pts)
            yy, xx = P[:, 0], P[:, 1]
            out.append((len(pts), float(xx.mean()), float(yy.mean()),
                        int(xx.min()), int(xx.max()), int(yy.min()), int(yy.max())))
    return sorted(out, key=lambda t: -t[0])[:maxn]


def marker_mask(arr):
    """淡黄手绘环（r 高 g 中 b 低，r-b 明显）。"""
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    return (r > 205) & (g > 180) & (b < 145) & ((r - g) > 20) & ((g - b) > 45)


# ---------------------------------------------------------------- 线性拟合
def _fit(pxs, pcts):
    """最小二乘拟合 pct = k*px + m，返回 (k, m, 残差列表)。"""
    n = len(pxs)
    mx = sum(pxs) / n
    mp = sum(pcts) / n
    num = sum((x - mx) * (p - mp) for x, p in zip(pxs, pcts))
    den = sum((x - mx) ** 2 for x in pxs)
    k = num / den
    m = mp - k * mx
    res = [p - (k * x + m) for x, p in zip(pxs, pcts)]
    return k, m, res


def solve(refs, targets, verbose=True):
    """refs   = [(name, px_x, px_y, pct_x, pct_y), ...]  至少 2 条
       targets= [(name, px_x, px_y), ...]
    返回 {name: (pct_x, pct_y)}"""
    ax, cx, rx = _fit([r[1] for r in refs], [r[3] for r in refs])
    by, dy, ry = _fit([r[2] for r in refs], [r[4] for r in refs])
    if verbose:
        print("x: pct = %.6f * px %+.4f   残差 %s" % (ax, cx, ["%+.2f" % v for v in rx]))
        print("y: pct = %.6f * px %+.4f   残差 %s" % (by, dy, ["%+.2f" % v for v in ry]))
        mx = max(abs(v) for v in rx + ry)
        if mx > 0.5:
            print("  ⚠️ 最大残差 %.2f 个百分点偏大（>0.5）→ 检查参考点像素有没有量错" % mx)
    out = {}
    for name, px, py in targets:
        out[name] = (round(ax * px + cx, 1), round(by * py + dy, 1))
        if verbose:
            print("  %-28s px(%.1f,%.1f) -> (%s, %s)" % (name, px, py, *out[name]))
    return out


# ------------------------------------------------- 已知钉点（第 1 层）百分比
def load_first_floor(did, lua=None):
    """从 Core/Data/Data_BossPos.lua 读某副本第 1 层（两位坐标）钉点。"""
    lua = lua or os.path.join(DF, "Core", "Data", "Data_BossPos.lua")
    src = open(lua, encoding="utf-8").read()
    m = re.search(r'\["%s"\]\s*=\s*\{(.*?)\n    \},' % re.escape(did), src, re.S)
    if not m:
        raise SystemExit("找不到副本 %s" % did)
    pos = {}
    for en, body in re.findall(r'\["([^"]+)"\]\s*=\s*\{\s*(.*?)\s*\}\s*,', m.group(1), re.S):
        pts = re.findall(r'\{\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*(\d+))?\s*\}', body)
        first = [(float(a), float(b)) for a, b, c in pts if not c]
        if first:
            pos[en] = first
    return pos


def px_of(pct, k, m):
    """百分比 → 截图像素（k,m 为拟合系数，用于回画校验图）。"""
    return (pct - m) / k


# ---------------------------------------------------------------- 自检
if __name__ == "__main__":
    # 2026-10-01 影牙城堡实例：截图 1218x807，4 个已知图标像素中心
    refs = [
        ("Commander Springvale",        314.3, 452.0, 25.5, 55.6),
        ("Jordan's Smithing Hammer",    454.7, 434.9, 37.3, 53.8),
        ("Rethilgore",                  800.1, 575.9, 66.1, 71.1),
        ("Fel Steed / Shadow Charger",  406.4, 508.8, 33.1, 62.6),
    ]
    # 用户手绘的淡黄环中心像素
    targets = [
        ("Commander Springvale",        343.1, 480.9),
        ("Fel Steed / Shadow Charger",  440.1, 510.4),
    ]
    print("== 反解 ==")
    solve(refs, targets)
    print("\n(期望：Commander 27.9,59.3 / Fel Steed 36.0,62.9)")
