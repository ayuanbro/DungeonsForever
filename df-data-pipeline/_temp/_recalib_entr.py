# -*- coding: utf-8 -*-
# 入口钉偏移修正：用截图上已渲染的金骷髅 boss 钉（BossPos 已知百分比）做线性标定，
# 解 px = a*nx + b，再代入红圈质心求真实画布百分比。
from PIL import Image
import sys

sys.setrecursionlimit(100000)

# 每图：截图路径 + BossPos 钉点（含名字文字块干扰，后面按形状过滤）
IMGS = [
    ('ragefire', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-04T00-05-29-928Z-c8cbf35e.jpg',
     [(41.5, 86.2), (33, 84.5), (56.1, 38), (41, 57.7)],
     r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-892Z-a81ad3cf.jpg'),
    ('wailing', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-04T00-05-29-931Z-ad9cf77d.jpg',
     [(25.8, 44.6), (30.5, 43.2), (28.1, 31.8), (47, 45.6), (40.3, 27.4), (15.6, 58.5), (62.5, 53.3), (34.2, 15.8), (56.4, 47.4)],
     r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-893Z-b78a9289.jpg'),
    ('deadmines', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-04T00-05-29-930Z-2f56ed25.jpg',
     [(52.7, 50.5), (38.6, 60.9), (45, 88.9)],
     r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-895Z-c282c8c8.jpg'),
]


def find_blobs(im, cond, step=2):
    """按颜色条件找像素连通块（降采样），返回 [(cx, cy, w, h, n)]"""
    w, h = im.size
    px = im.load()
    pts = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            if cond(*px[x, y]):
                pts.append((x, y))
    # 网格哈希 BFS 连通域（邻域 = 2*step）
    cell = {}
    for p in pts:
        cell.setdefault((p[0] // 16, p[1] // 16), []).append(p)
    seen = set()
    blobs = []
    for key in cell:
        if key in seen:
            continue
        stack = [key]
        seen.add(key)
        comp = []
        while stack:
            k = stack.pop()
            comp.extend(cell[k])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (k[0] + dx, k[1] + dy)
                    if nk not in seen and nk in cell:
                        seen.add(nk)
                        stack.append(nk)
        if len(comp) < 8:
            continue
        xs = [c[0] for c in comp]
        ys = [c[1] for c in comp]
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        # 骷髅钉：近方形团块；文字行：细长 → 过滤
        if bw > 40 or bh > 40 or bw > bh * 2.2 or bh > bw * 2.2 or bw < 8 or bh < 8:
            continue
        blobs.append((sum(xs) / len(xs), sum(ys) / len(ys), bw, bh, len(comp)))
    return blobs, (w, h)


def fit(pairs):
    """最小二乘 px = a*nx + b；返回 (a, b, max_err)"""
    n = len(pairs)
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxx = sum(p[0] * p[0] for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    a = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - a * sx) / n
    errs = [abs(a * p[0] + b - p[1]) for p in pairs]
    return a, b, max(errs)


for tag, path, bosspos, redpath in IMGS:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    # 金骷髅钉颜色：染金色 (1,0.82,0)≈(255,209,0)，描边/骨白也偏暖；放宽
    cond = lambda r, g, b: r > 215 and 140 < g < 235 and b < 110
    blobs, _ = find_blobs(im, cond)
    # 与 BossPos 配对：两集合质心整体平移对齐后最近邻，取 <6% 的对
    bcx = sum(b[0] / w for b in blobs) / max(1, len(blobs))
    bcy = sum(b[1] / h for b in blobs) / max(1, len(blobs))
    pcx = sum(p[0] for p in bosspos) / len(bosspos)
    pcy = sum(p[1] for p in bosspos) / len(bosspos)
    pairs = []
    used = set()
    for b in blobs:
        nx, ny = b[0] / w, b[1] / h
        # 对齐偏移后的最近 boss 点
        cand = min(range(len(bosspos)),
                   key=lambda i: abs(bosspos[i][0] - (nx + pcx - bcx)) + abs(bosspos[i][1] - (ny + pcy - bcy)))
        d = abs(bosspos[cand][0] - (nx + pcx - bcx)) + abs(bosspos[cand][1] - (ny + pcy - bcy))
        if d < 6 and cand not in used:
            used.add(cand)
            pairs.append((bosspos[cand][0], b[0], bosspos[cand][1], b[1]))
    if len(pairs) < 3:
        print(tag, '配对不足', len(pairs), 'blobs=', len(blobs))
        continue
    ax, bx, ex = fit([(p[0], p[1]) for p in pairs])
    ay, by, ey = fit([(p[2], p[3]) for p in pairs])
    # 红圈质心（原图坐标，前一轮已算）→ 代入逆映射 nx = (px - b)/a
    rim = Image.open(redpath).convert('RGB')
    rw, rh = rim.size
    rpx = rim.load()
    xs, ys = [], []
    for y in range(0, rh, 2):
        for x in range(0, rw, 2):
            r, g, b = rpx[x, y]
            if r > 190 and g < 90 and b < 90:
                xs.append(x)
                ys.append(y)
    rcx, rcy = sum(xs) / len(xs), sum(ys) / len(ys)
    nx = (rcx - bx) / ax * 100
    ny = (rcy - by) / ay * 100
    print('%s: pairs=%d  px_err=(%.1f,%.1f)px  红圈(%.0f,%.0f)px -> %.1f, %.1f' % (
        tag, len(pairs), ex, ey, rcx, rcy, nx, ny))
