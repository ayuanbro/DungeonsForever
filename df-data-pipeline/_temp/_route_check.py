# -*- coding: utf-8 -*-
import io
import json
import math
import os

from PIL import Image, ImageDraw

ROOT = 'D:/workspace/DungeonsForever/_temp/_route_plan'
W, H = 1002, 668
SS = 2


def grad(t):
    G = [(0.00, 0.24, 0.78, 0.80), (0.55, 0.98, 0.82, 0.35), (1.00, 1.00, 0.55, 0.22)]
    for i in range(len(G) - 1):
        a, b = G[i], G[i + 1]
        if t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
            return tuple(int(255 * (a[k] + (b[k] - a[k]) * u)) for k in (1, 2, 3))
    return tuple(int(255 * v) for v in G[-1][1:])


def main():
    data = json.load(io.open(ROOT + '/route.json', encoding='utf-8'))
    for f, lay in (('221', 'L1'), ('222', 'L2')):
        base = Image.open('%s/img/bfd_%s.jpg' % (ROOT, lay)).convert('RGB')
        big = base.resize((W * SS, H * SS), Image.LANCZOS)
        ov = Image.new('RGBA', big.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for s in data[f]['segs']:
            pts = [(x * SS / 100 * W, y * SS / 100 * H) for x, y in s['pts']]
            d.line(pts, fill=(12, 9, 6, 200), width=int(7 * SS), joint='curve')
            n = len(pts)
            for i in range(1, n):
                pass
            d.line(pts, fill=grad((s['t0'] + s['t1']) / 2), width=int(4 * SS), joint='curve')
            for p in (pts[0], pts[-1]):
                r = 5 * SS
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                          fill=grad((s['t0'] + s['t1']) / 2))
        for st in data[f]['stops']:
            for x, y in st['pins']:
                cx, cy = x * SS / 100 * W, y * SS / 100 * H
                r = 8 * SS
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 220),
                          outline=(255, 200, 90, 255), width=2 * SS)
        for nt in data[f]['notes']:
            cx, cy = nt['x'] * SS / 100 * W, nt['y'] * SS / 100 * H
            r = 6 * SS
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                      fill=(230, 190, 60, 240), outline=(20, 14, 8, 255))
        out = Image.alpha_composite(big.convert('RGBA'), ov)
        p = '%s/check_%s.png' % (ROOT, lay)
        out.convert('RGB').save(p)
        print(p)


if __name__ == '__main__':
    main()
