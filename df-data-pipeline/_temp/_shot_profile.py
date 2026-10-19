# -*- coding: utf-8 -*-
import sys
from PIL import Image

p = sys.argv[1]
rows = [int(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 else [1150]
im = Image.open(p).convert('RGB')
W, H = im.size
px = im.load()
print('size', W, H)
for y in rows:
    vals = []
    for x in range(1290, 1440):
        r, g, b = px[x, y]
        vals.append((r + g + b) // 3)
    line = ' '.join('%3d' % v for v in vals)
    print('y=%d lum x=1290..1439:' % y)
    print(line)
    peaks = [1290 + i for i, v in enumerate(vals) if v > 34]
    print('  bright(>34) x =', peaks[:40])
