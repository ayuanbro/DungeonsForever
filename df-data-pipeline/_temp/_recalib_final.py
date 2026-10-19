# -*- coding: utf-8 -*-
# 终版：白心红环红圈质心 + boss 钉线性标定映射 → 三个入口的最终画布百分比。
from PIL import Image

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

GOLD = lambda r, g, b: r > 200 and 130 < g < 235 and b < 120
RED = lambda r, g, b: r > 205 and 55 < g < 100 and 25 < b < 70
WHITE = lambda r, g, b: r > 244 and g > 235 and b > 185


def gold_centroid(im, nx, ny, win):
    w, h = im.size
    px = im.load()
    x0, x1 = int((nx - win) * w), int((nx + win) * w)
    y0, y1 = int((ny - win) * h), int((ny + win) * h)
    xs, ys = [], []
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            if GOLD(*px[x, y]):
                xs.append(x)
                ys.append(y)
    if len(xs) < 30:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def fit(pairs):
    n = len(pairs)
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxx = sum(p[0] * p[0] for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    a = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - a * sx) / n
    errs = [abs(a * p[0] + b - p[1]) for p in pairs]
    return a, b, max(errs)


def red_circle(im):
    w, h = im.size
    px = im.load()
    pts = [(x, y) for y in range(0, h, 2) for x in range(0, w, 2) if WHITE(*px[x, y])]
    cell = {}
    for p in pts:
        cell.setdefault((p[0] // 16, p[1] // 16), []).append(p)
    seen, cands = set(), []
    for key in cell:
        if key in seen:
            continue
        stack, comp = [key], []
        seen.add(key)
        while stack:
            k = stack.pop()
            comp.extend(cell[k])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (k[0] + dx, k[1] + dy)
                    if nk not in seen and nk in cell:
                        seen.add(nk)
                        stack.append(nk)
        if len(comp) < 4:
            continue
        xs = [c[0] for c in comp]
        ys = [c[1] for c in comp]
        if max(xs) - min(xs) > 50 or max(ys) - min(ys) > 50:
            continue
        cands.append((sum(xs) / len(xs), sum(ys) / len(ys)))
    best, bestscore = None, 0
    for cx, cy in cands:
        rin = rout = 0
        for y in range(int(cy) - 40, int(cy) + 41, 2):
            for x in range(int(cx) - 40, int(cx) + 41, 2):
                if not (0 <= x < w and 0 <= y < h):
                    continue
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if 12 ** 2 <= d2 <= 38 ** 2:
                    rout += 1
                    if RED(*px[x, y]):
                        rin += 1
        score = rin / max(1, rout)
        if score > bestscore:
            bestscore, best = score, (cx, cy)
    if not best or bestscore < 0.12:
        return None
    cx, cy = best
    xs, ys = [], []
    for y in range(int(cy) - 40, int(cy) + 41, 2):
        for x in range(int(cx) - 40, int(cx) + 41, 2):
            if not (0 <= x < w and 0 <= y < h):
                continue
            if WHITE(*px[x, y]) or RED(*px[x, y]):
                if (x - cx) ** 2 + (y - cy) ** 2 <= 38 ** 2:
                    xs.append(x)
                    ys.append(y)
    return sum(xs) / len(xs), sum(ys) / len(ys)


for tag, path, bosspos, redpath in IMGS:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    pairs = []
    for bx, by in bosspos:
        r = gold_centroid(im, bx / 100, by / 100, 0.05)
        if r:
            pairs.append((bx, r[0], by, r[1]))
    ax, bx_, ex = fit([(p[0], p[1]) for p in pairs])
    ay, by_, ey = fit([(p[2], p[3]) for p in pairs])
    rim = Image.open(redpath).convert('RGB')
    rc = red_circle(rim)
    if not rc:
        print(tag, '红圈未找到')
        continue
    nx = (rc[0] - bx_) / ax
    ny = (rc[1] - by_) / ay
    print('%s: pairs=%d err=(%.1f,%.1f)px  红圈(%.0f,%.0f) -> 最终 (%.1f, %.1f)' % (
        tag, len(pairs), ex, ey, rc[0], rc[1], nx, ny))
