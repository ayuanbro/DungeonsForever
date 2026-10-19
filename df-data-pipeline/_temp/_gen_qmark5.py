import struct
import math
import numpy as np
from PIL import Image, ImageDraw

S = 512
C = S // 2
OUT = 'D:/workspace/DungeonsForever/Media/'
SYM_H = 350

OV_W = 16.0
OV_H = 24.0
CX = 8.0
CY = 7.0
RX_O = 7.0
RY_O = 6.0
RX_I = 3.3
RY_I = 3.0
A_OPEN_FROM = -146.0
A_OPEN_TO = -54.0
STEM_P0 = (11.4, 10.0)
STEM_P1 = (7.6, 17.2)
STEM_W = 3.7
DOT_C = (7.5, 20.5)
DOT_R = 2.0
SS = 120


def seg_dist(x, y, p0, p1):
    ax, ay = p0
    bx, by = p1
    vx, vy = bx - ax, by - ay
    t = ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)
    t = np.clip(t, 0.0, 1.0)
    return np.sqrt((x - (ax + vx * t)) ** 2 + (y - (ay + vy * t)) ** 2)


def build():
    w = int(round(OV_W * SS))
    h = int(round(OV_H * SS))
    xs = (np.arange(w) + 0.5) / SS
    ys = (np.arange(h) + 0.5) / SS
    X, Y = np.meshgrid(xs, ys)

    u = (X - CX) / RX_O
    v = (Y - CY) / RY_O
    ring = (u * u + v * v) <= 1.0
    ui = (X - CX) / RX_I
    vi = (Y - CY) / RY_I
    ring &= (ui * ui + vi * vi) >= 1.0

    th = np.degrees(np.arctan2(-v, u))
    gap = (th >= A_OPEN_FROM) & (th <= A_OPEN_TO)
    ring &= ~gap

    stem = seg_dist(X, Y, STEM_P0, STEM_P1) <= STEM_W / 2
    dot = ((X - DOT_C[0]) ** 2 + (Y - DOT_C[1]) ** 2) <= DOT_R ** 2

    m = ring | stem | dot
    return Image.fromarray((m * 255).astype(np.uint8), 'L')


def fit(mask, target_h=SYM_H):
    w, h = mask.size
    nw = max(1, int(round(w * target_h / h)))
    mask = mask.resize((nw, target_h), Image.LANCZOS)
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    a = Image.new('RGBA', mask.size, (255, 255, 255, 255))
    im.paste(a, (C - nw // 2, C - target_h // 2), mask)
    return im


def excl():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = 80
    d.rounded_rectangle([C - lw // 2, C - 140, C + lw // 2, C + 40], radius=lw // 2, fill=(255, 255, 255, 255))
    r = 40
    cy = C + 118
    d.ellipse([C - r, cy - r, C + r, cy + r], fill=(255, 255, 255, 255))
    return im


def save_tga(im, path):
    im = im.resize((64, 64), Image.LANCZOS)
    px = im.load()
    buf = bytearray()
    for j in range(64):
        for i in range(64):
            r, g, b, a = px[i, j]
            buf += bytes((b, g, r, a))
    hdr = bytearray()
    hdr += bytes((0, 0, 2, 0, 0, 0, 0, 0))
    hdr += bytes((0, 0, 0, 0))
    hdr += struct.pack('<HH', 64, 64)
    hdr += bytes((32, 0x28))
    open(path, 'wb').write(bytes(hdr) + bytes(buf))


save_tga(fit(build()), OUT + 'QMarkAsk.tga')
save_tga(excl(), OUT + 'QMarkExcl.tga')
for f in ('QMarkAsk', 'QMarkExcl'):
    im = Image.open(OUT + f + '.tga').convert('RGBA')
    bb = im.split()[3].getbbox()
    print(f, 'bbox', bb, 'w=%d h=%d' % (bb[2] - bb[0], bb[3] - bb[1]))
