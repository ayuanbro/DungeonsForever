# -*- coding: utf-8 -*-
import sys
from PIL import Image

p = sys.argv[1]
im = Image.open(p).convert('RGB')
W, H = im.size
px = im.load()
lum = [[0] * W for _ in range(H)]
for y in range(H):
    row = lum[y]
    for x in range(W):
        r, g, b = px[x, y]
        row[x] = (r + g + b) // 3


def vlines(x0, x1, y0, y1, thr=40):
    out = []
    for x in range(x0, x1):
        n = sum(1 for y in range(y0, y1) if lum[y][x] > thr)
        if n > (y1 - y0) * 0.25:
            out.append((x, n))
    return out


def hlines(y0, y1, x0, x1, thr=40):
    out = []
    for y in range(y0, y1):
        n = sum(1 for x in range(x0, x1) if lum[y][x] > thr)
        if n > (x1 - x0) * 0.25:
            out.append((y, n))
    return out


print('=== vertical lines x=1300..1420 (over y 700..1300) ===')
for x, n in vlines(1300, 1420, 700, 1300):
    print('   x=%d count=%d' % (x, n))
print('=== vertical lines x=2200..2300 ===')
for x, n in vlines(2200, 2300, 700, 1300):
    print('   x=%d count=%d' % (x, n))
print('=== horizontal lines y=250..420 (over x 1400..2200) ===')
for y, n in hlines(250, 420, 1400, 2200):
    print('   y=%d count=%d' % (y, n))
print('=== horizontal lines y=1280..1395 ===')
for y, n in hlines(1280, 1395, 1400, 2200):
    print('   y=%d count=%d' % (y, n))
