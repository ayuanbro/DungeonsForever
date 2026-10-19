# -*- coding: utf-8 -*-
import sys
from PIL import Image

p = sys.argv[1]
x0, x1 = (int(v) for v in sys.argv[2].split(','))
y0, y1, st = (int(v) for v in sys.argv[3].split(','))
im = Image.open(p).convert('RGB')
px = im.load()
print('x %d..%d  y %d..%d step %d' % (x0, x1, y0, y1, st))
print('    ' + ''.join(str((x // 10) % 10) for x in range(x0, x1)))
print('    ' + ''.join(str(x % 10) for x in range(x0, x1)))


def cc(v):
    if v < 20:
        return '.'
    if v < 30:
        return ':'
    if v < 40:
        return '-'
    if v < 60:
        return '+'
    if v < 100:
        return '*'
    return '#'


for y in range(y0, y1, st):
    row = ''.join(cc((px[x, y][0] + px[x, y][1] + px[x, y][2]) // 3) for x in range(x0, x1))
    print('%4d %s' % (y, row))
