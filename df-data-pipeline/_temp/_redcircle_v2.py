# -*- coding: utf-8 -*-
# 红圈检测 v2：红圈 = 白色数字心 + 红环。找白团 → 验证周围红环比例 → 取最优者。
from PIL import Image

IMGS = [
    ('ragefire', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-892Z-a81ad3cf.jpg'),
    ('wailing', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-893Z-b78a9289.jpg'),
    ('deadmines', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-895Z-c282c8c8.jpg'),
]

RED = lambda r, g, b: r > 205 and 55 < g < 100 and 25 < b < 70
WHITE = lambda r, g, b: r > 244 and g > 235 and b > 185

for tag, path in IMGS:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    # ① 白团：BFS 连通（降采样 2px）
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
        if len(comp) < 6:
            continue
        xs = [c[0] for c in comp]
        ys = [c[1] for c in comp]
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        if bw > 50 or bh > 50:
            continue
        cands.append((sum(xs) / len(xs), sum(ys) / len(ys), bw, bh))
    # ② 红环验证
    best, bestscore = None, 0
    for cx, cy, bw, bh in cands:
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
        print(tag, '未找到红圈 cands=%d best=%.2f' % (len(cands), bestscore))
        continue
    # ③ 质心：白心 + 红环像素合并
    cx, cy = best
    xs, ys = [], []
    for y in range(int(cy) - 40, int(cy) + 41, 2):
        for x in range(int(cx) - 40, int(cx) + 41, 2):
            if not (0 <= x < w and 0 <= y < h):
                continue
            if WHITE(*px[x, y]) or RED(*px[x, y]):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if d2 <= 38 ** 2:
                    xs.append(x)
                    ys.append(y)
    fx, fy = sum(xs) / len(xs), sum(ys) / len(ys)
    print('%s: 白团=%d 环分=%.2f 红圈=(%.0f,%.0f)px -> 直接百分比 (%.2f, %.2f)' % (
        tag, len(cands), bestscore, fx, fy, fx / w * 100, fy / h * 100))
