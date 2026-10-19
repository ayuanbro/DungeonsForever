# -*- coding: utf-8 -*-
import sys
from PIL import Image

p = sys.argv[1]
im = Image.open(p).convert('RGB')
W, H = im.size
px = im.load()
print('size', W, H)
for y in [int(v) for v in sys.argv[2].split(',')]:
    hits = []
    for x in range(0, W):
        r, g, b = px[x, y]
        lum = (r + g + b) // 3
        if lum > 34:
            hits.append((x, lum))
    groups = []
    for x, l in hits:
        if groups and x - groups[-1][-1][0] <= 2:
            groups[-1].append((x, l))
        else:
            groups.append([(x, l)])
    print('y=%d  bright groups:%d' % (y, len(groups)))
    for g in groups[:24]:
        print('   x %d..%d (n=%d) maxlum=%d' % (g[0][0], g[-1][0], len(g), max(l for _, l in g)))
