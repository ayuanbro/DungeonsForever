# -*- coding: utf-8 -*-
# 入口钉偏移修正 v2：局部窗口标定。对每个 BossPos 钉，在预期像素 ±5% 窗口内
# 找金色像素质心 → 配对 → 最小二乘 px=a*nx+b → 红圈质心逆映射。
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


def gold_centroid(im, nx, ny, win):
    """在归一化 (nx,ny) ± win 窗口内找金色像素质心，返回像素坐标或 None"""
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
    return sum(xs) / len(xs), sum(ys) / len(ys), len(xs)


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


for tag, path, bosspos, redpath in IMGS:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    # 单轮：按 BossPos 原值 ±5% 窗口找金骷髅质心 → 拟合（第二轮重定位会把窗口带飞，弃）
    guess = [(p[0] / 100, p[1] / 100) for p in bosspos]
    pairs = []
    for (bx, by), (gx, gy) in zip(bosspos, guess):
        r = gold_centroid(im, gx, gy, 0.05)
        if r:
            pairs.append((bx, r[0], by, r[1]))
    if len(pairs) < 2:
        print(tag, '配对不足', len(pairs))
        continue
    ax, bx_, ex = fit([(p[0], p[1]) for p in pairs])
    ay, by_, ey = fit([(p[2], p[3]) for p in pairs])
    # 红圈质心 → 逆映射
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
    nx = (rcx - bx_) / ax
    ny = (rcy - by_) / ay
    print('%s: pairs=%d err=(%.1f,%.1f)px  红圈(%.0f,%.0f) -> (%.1f, %.1f)' % (
        tag, len(pairs), ex, ey, rcx, rcy, nx, ny))
