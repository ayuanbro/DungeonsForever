# -*- coding: utf-8 -*-
import sys
from PIL import Image

p = sys.argv[1]
x0, x1, sx = (int(v) for v in sys.argv[2].split(','))
y0, y1, sy = (int(v) for v in sys.argv[3].split(','))
im = Image.open(p).convert('RGB')
px = im.load()


def cc(v):
    if v < 18:
        return '.'
    if v < 26:
        return ','
    if v < 32:
        return ':'
    if v < 42:
        return '-'
    if v < 64:
        return '+'
    if v < 104:
        return '*'
    return '#'


hdr = '     ' + ''.join('|' if (x % 80 < sx) else ' ' for x in range(x0, x1, sx))
print('x %d..%d step %d ; y %d..%d step %d' % (x0, x1, sx, y0, y1, sy))
print(hdr)
for y in range(y0, y1, sy):
    row = ''.join(cc((px[x, y][0] + px[x, y][1] + px[x, y][2]) // 3) for x in range(x0, x1, sx))
    print('%4d %s' % (y, row))
