import struct
import math
import numpy as np
from PIL import Image, ImageDraw

S = 512
C = S // 2
OUT = 'D:/workspace/DungeonsForever/Media/'
SYM_H = 318

HD = 1000.0
LW = 138.0
RAD = 181.0
A0 = -58.0
A1 = 206.0
DOT_R = 106.0
GAP = 54.0
CX = RAD + LW / 2
CY = LW / 2 + RAD
W = 2 * (RAD + LW / 2)
PX_T = CX + RAD * math.cos(math.radians(-A0))
PX_B = PX_T - 18.0
DOT_CY = HD - DOT_R
DOT_CX = PX_B
STEM_TOP = CY + RAD * math.sin(math.radians(-A0)) - LW / 2
STEM_BOT = DOT_CY - DOT_R - GAP


def build(ss=3):
    w = int(round(W * ss))
    h = int(round(HD * ss))
    xs = (np.arange(w) + 0.5) / ss
    ys = (np.arange(h) + 0.5) / ss
    X, Y = np.meshgrid(xs, ys)

    dx = X - CX
    dy = CY - Y
    dist = np.sqrt(dx * dx + dy * dy)
    ang = np.degrees(np.arctan2(dy, dx))
    in_arc = ((ang >= A0) | (ang <= A1 - 360.0)) & (np.abs(dist - RAD) <= LW / 2)
    for a in (A0, A1):
        ex = CX + RAD * math.cos(math.radians(a))
        ey = CY - RAD * math.sin(math.radians(a))
        in_arc |= ((X - ex) ** 2 + (Y - ey) ** 2) <= (LW / 2) ** 2

    t = np.clip((Y - STEM_TOP) / max(1.0, (STEM_BOT - STEM_TOP)), 0.0, 1.0)
    cxs = PX_T + (PX_B - PX_T) * t
    in_stem = (np.abs(X - cxs) <= LW / 2) & (Y >= STEM_TOP) & (Y <= STEM_BOT)
    in_dot = ((X - DOT_CX) ** 2 + (Y - DOT_CY) ** 2) <= DOT_R ** 2

    m = (in_arc | in_stem | in_dot)
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


print('design W=%.0f outer=%.0f hole=%.0f stem=%.0f dot=%.0f' % (W, 2 * RAD + LW, 2 * RAD - LW, STEM_BOT - STEM_TOP, 2 * DOT_R))
save_tga(fit(build()), OUT + 'QMarkAsk.tga')
save_tga(excl(), OUT + 'QMarkExcl.tga')
for f in ('QMarkAsk', 'QMarkExcl'):
    im = Image.open(OUT + f + '.tga').convert('RGBA')
    bb = im.split()[3].getbbox()
    print(f, 'bbox', bb, 'w=%d h=%d' % (bb[2] - bb[0], bb[3] - bb[1]))
