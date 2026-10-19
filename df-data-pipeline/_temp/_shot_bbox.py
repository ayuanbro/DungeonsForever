# -*- coding: utf-8 -*-
import sys
from PIL import Image

p = sys.argv[1]
im = Image.open(p).convert('RGB')
W, H = im.size
px = im.load()
BANDS = [(24, 31), (16, 22)]
for lo, hi in BANDS:
    cnt = 0
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            l = (r + g + b) // 3
            if lo <= l <= hi:
                cnt += 1
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    if cnt:
        bw, bh = x1 - x0, y1 - y0
        print('band lum %d..%d : n=%d  bbox x %d..%d y %d..%d  (%dx%d  ratio h/w=%.3f)'
              % (lo, hi, cnt, x0, x1, y0, y1, bw, bh, bh / float(bw) if bw else 0))
for y in [int(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 else []:
    xs = [x for x in range(W) if 24 <= sum(px[x, y]) // 3 <= 31]
    runs = []
    for x in xs:
        if runs and x - runs[-1][-1] <= 3:
            runs[-1].append(x)
        else:
            runs.append([x])
    big = [(r[0], r[-1], len(r)) for r in runs if len(r) > 40]
    print('y=%d bands(%d..31): %s' % (y, big[:8]))
