# -*- coding: utf-8 -*-
"""双勾形态定稿预览（香槟金盘 + 游戏内深色底 + 大图 + 18px 实际大小对照）。"""
import struct, math, zlib
from PIL import Image, ImageDraw, ImageFont

S = 64
SS = 4
WHITE = (255, 255, 255)
CHAMPAGNE = (232, 198, 106)
PANEL = (22, 26, 34)          # 游戏内 L2 卡底近似
PANEL2 = (16, 19, 26)


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def stroke_alpha(pts, x, y, w):
    d = min(seg_dist(x, y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1))
    return d <= w / 2


def circle_hit(cx, cy, r, x, y):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def render(layers):
    img = [[(0, 0, 0, 0.0)] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            acc = {}
            for sy in range(SS):
                for sx in range(SS):
                    fx = x + (sx + 0.5) / SS
                    fy = y + (sy + 0.5) / SS
                    col = None
                    for (color, base, fn) in layers:
                        if fn(fx, fy):
                            col = (color, base)
                    if col:
                        key = col[0] + (col[1],)
                        acc[key] = acc.get(key, 0) + 1
            if acc:
                key, n = max(acc.items(), key=lambda kv: kv[1])
                a = n / (SS * SS) * key[3]
                img[y][x] = (key[0], key[1], key[2], a)
    return img


def scale_tick(f, dx=0.0, dy=0.0, w=None):
    pts = [(19 * f + (1 - f) * 32 + dx, 34 * f + (1 - f) * 32 + dy),
           (28.5 * f + (1 - f) * 32 + dx, 43 * f + (1 - f) * 32 + dy),
           (46 * f + (1 - f) * 32 + dx, 22 * f + (1 - f) * 32 + dy)]
    return pts, (w or 6.8 * f)


def tick_hit(pts, w):
    p1, p2 = pts[0], pts[2]
    return (lambda fx, fy: stroke_alpha(pts, fx, fy, w)
            or circle_hit(p1[0], p1[1], w / 2, fx, fy)
            or circle_hit(p2[0], p2[1], w / 2, fx, fy))


def darken(c, k=0.62):
    return tuple(int(v * k) for v in c)


disc_fn = lambda fx, fy: circle_hit(32, 32, 30.5, fx, fy)

aL, aw = scale_tick(0.8, -9.5, 0)
aR, arw = scale_tick(0.8, 9.5, 0)
bB, bw = scale_tick(0.9, -7, 1.5)
bF, bfw = scale_tick(0.9, 0, 0)
c_dot = lambda fx, fy: circle_hit(21, 36, 5.6, fx, fy)
cT, cw = scale_tick(0.85, 8, 0)
d_ring = [(32 + 26 * math.cos(2 * math.pi * i / 72), 32 + 26 * math.sin(2 * math.pi * i / 72)) for i in range(73)]
dT, dw = scale_tick(0.8, 0, 0)

variants = [
    ('A · 并排双勾', [(CHAMPAGNE, 1.0, disc_fn), (WHITE, 1.0, tick_hit(aL, aw)), (WHITE, 1.0, tick_hit(aR, arw))]),
    ('B · 深色后勾', [(CHAMPAGNE, 1.0, disc_fn), (darken(CHAMPAGNE), 1.0, tick_hit(bB, bw)), (WHITE, 1.0, tick_hit(bF, bfw))]),
    ('C · 勾加点', [(CHAMPAGNE, 1.0, disc_fn), (WHITE, 1.0, c_dot), (WHITE, 1.0, tick_hit(cT, cw))]),
    ('D · 盘内白环', [(CHAMPAGNE, 1.0, disc_fn), (WHITE, 1.0, lambda fx, fy: stroke_alpha(d_ring, fx, fy, 3.6)), (WHITE, 1.0, tick_hit(dT, dw))]),
]

BIG = 384  # 64*6
PAD = 28
LABEL_H = 56
SMALL = 18
COLW = BIG + SMALL + PAD * 3
ROWH = BIG + LABEL_H + PAD
W = PAD + COLW * 2 + PAD
H = PAD + ROWH * 2 + PAD + 60

img = Image.new('RGB', (W, H), PANEL2)
dr = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 26)
    font_s = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
except Exception:
    font = ImageFont.load_default()
    font_s = font

for i, (name, layers) in enumerate(variants):
    r, c = divmod(i, 2)
    ox = PAD + c * COLW
    oy = PAD + r * ROWH
    dr.rounded_rectangle([ox - 6, oy - 6, ox + COLW - SMALL - PAD + 6, oy + ROWH - PAD + 6],
                         radius=10, fill=PANEL)
    rendered = render(layers)
    big = Image.new('RGBA', (S, S))
    px = big.load()
    for y in range(S):
        for x in range(S):
            pr, pg, pb, pa = rendered[y][x]
            px[x, y] = (pr, pg, pb, int(pa * 255))
    big = big.resize((BIG, BIG), Image.NEAREST)
    img.paste(big, (ox + PAD, oy + PAD), big)
    dr.text((ox + PAD, oy + BIG + 12), name, fill=(235, 238, 245), font=font)
    small = big.resize((SMALL, SMALL), Image.LANCZOS)
    sx = ox + PAD + BIG + PAD
    sy = oy + PAD + BIG - SMALL
    img.paste(small, (sx, sy), small)
    dr.rectangle([sx - 2, sy - 2, sx + SMALL + 2, sy + SMALL + 2], outline=(70, 76, 88), width=1)
    dr.text((sx - 2, sy + SMALL + 6), '18px', fill=(150, 156, 168), font=font_s)

dr.text((PAD, H - 46), '上：18px 实装大小对照（右侧小格）    下：放大 6 倍观感', fill=(150, 156, 168), font=font_s)
img.save('_temp/_corner_view/CheckShapes_Final.png')
print('saved _temp/_corner_view/CheckShapes_Final.png', img.size)
