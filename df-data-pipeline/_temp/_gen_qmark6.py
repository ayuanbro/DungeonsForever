import struct
import numpy as np
from PIL import Image, ImageDraw

S = 512
OUT = 'D:/workspace/DungeonsForever/Media/'

CX = 8.0
CY = 7.0
RX_O = 6.7
RY_O = 6.0
RX_I = 2.0
RY_I = 2.2
A_OPEN_FROM = -146.0
A_OPEN_TO = -54.0
STEM_P0 = (11.4, 9.6)
STEM_P1 = (7.6, 14.7)
STEM_W = 3.7
DOT_C = (7.5, 20.8)
DOT_R = 2.15

X_LO, X_HI = 1.0, 15.0
Y_LO, Y_HI = 1.0, 23.1
TARGET_H = 352.0
SCALE = TARGET_H / (Y_HI - Y_LO)
OX = (S - (X_HI - X_LO) * SCALE) / 2.0
OY = (S - TARGET_H) / 2.0


def tx(x):
    return OX + (x - X_LO) * SCALE


def ty(y):
    return OY + (y - Y_LO) * SCALE


def seg_dist(x, y, p0, p1):
    ax, ay = p0
    bx, by = p1
    vx, vy = bx - ax, by - ay
    t = ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)
    t = np.clip(t, 0.0, 1.0)
    return np.sqrt((x - (ax + vx * t)) ** 2 + (y - (ay + vy * t)) ** 2)


def build():
    xs = (np.arange(S) + 0.5 - OX) / SCALE + X_LO
    ys = (np.arange(S) + 0.5 - OY) / SCALE + Y_LO
    X, Y = np.meshgrid(xs, ys)

    u = (X - CX) / RX_O
    v = (Y - CY) / RY_O
    ring = (u * u + v * v) <= 1.0
    ui = (X - CX) / RX_I
    vi = (Y - CY) / RY_I
    ring &= (ui * ui + vi * vi) >= 1.0

    th = np.degrees(np.arctan2(-v, u))
    ring &= ~((th >= A_OPEN_FROM) & (th <= A_OPEN_TO))

    stem = seg_dist(X, Y, STEM_P0, STEM_P1) <= STEM_W / 2
    dot = ((X - DOT_C[0]) ** 2 + (Y - DOT_C[1]) ** 2) <= DOT_R ** 2

    m = ring | stem | dot
    return Image.fromarray((m * 255).astype(np.uint8), 'L')


def excl():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = 80
    d.rounded_rectangle([S // 2 - lw // 2, S // 2 - 140, S // 2 + lw // 2, S // 2 + 40], radius=lw // 2, fill=(255, 255, 255, 255))
    r = 40
    cy = S // 2 + 118
    d.ellipse([S // 2 - r, cy - r, S // 2 + r, cy + r], fill=(255, 255, 255, 255))
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


mask = build()
rgba = Image.new('RGBA', (S, S), (0, 0, 0, 0))
rgba.paste(Image.new('RGBA', (S, S), (255, 255, 255, 255)), (0, 0), mask)
save_tga(rgba, OUT + 'QMarkAsk.tga')
save_tga(excl(), OUT + 'QMarkExcl.tga')
for f in ('QMarkAsk', 'QMarkExcl'):
    im = Image.open(OUT + f + '.tga').convert('RGBA')
    bb = im.split()[3].getbbox()
    print(f, 'bbox', bb, 'w=%d h=%d' % (bb[2] - bb[0], bb[3] - bb[1]))
