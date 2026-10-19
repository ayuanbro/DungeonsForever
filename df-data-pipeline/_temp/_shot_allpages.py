# -*- coding: utf-8 -*-
import glob
import os
from PIL import Image

D = r'C:\Users\Administrator\Desktop\无限副本手册\1.8.0'
Y0, Y1 = 700, 1300
ROWS = Y1 - Y0
for p in sorted(glob.glob(os.path.join(D, '*.png'))):
    im = Image.open(p).convert('RGB')
    W, H = im.size
    px = im.load()
    lum = [[0] * W for _ in range(H)]
    for y in range(Y0, Y1):
        r = lum[y]
        pxl = px
        for x in range(1150, min(W, 1420)):
            c = pxl[x, y]
            r[x] = (c[0] + c[1] + c[2]) // 3
    hits = []
    for x in range(1150, min(W, 1420)):
        n = sum(1 for y in range(Y0, Y1) if lum[y][x] > 38)
        if n > ROWS * 0.45:
            hits.append((x, n))
    print('%-16s %s' % (os.path.basename(p), hits))
