# -*- coding: utf-8 -*-
import sys
from collections import Counter
from PIL import Image

p = sys.argv[1]
im = Image.open(p).convert('RGB')
W, H = im.size
px = im.load()
print('size', W, H)
c = Counter()
for y in range(0, H, 4):
    for x in range(0, W, 4):
        c[px[x, y]] += 1
for col, n in c.most_common(14):
    print(col, n)
print('--- luminance<30 longest run per row (sampled rows) ---')


def dark(p):
    return (p[0] + p[1] + p[2]) / 3.0 < 30


for y in range(0, H, max(1, H // 24)):
    best = (0, -1, -1)
    s = None
    for x in range(W):
        f = dark(px[x, y])
        if f and s is None:
            s = x
        elif not f and s is not None:
            if x - s > best[0]:
                best = (x - s, s, x - 1)
            s = None
    if s is not None and W - s > best[0]:
        best = (W - s, s, W - 1)
    print('y=%4d run=%4d  x %d..%d' % (y, best[0], best[1], best[2]))
