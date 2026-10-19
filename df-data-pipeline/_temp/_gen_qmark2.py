import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import grey_dilation

S = 512
C = S // 2
FB = 'C:/Windows/Fonts/msyhbd.ttc'
OUT = 'D:/workspace/DungeonsForever/Media/'
SYM_H = 318
R_GROW = 8
GAP_RATIO = 0.155
FONT_PT = 500
STROKE = 10


def row_runs(mask):
    px = mask.load()
    w, h = mask.size
    rows = [sum(px[i, j] for i in range(w)) for j in range(h)]
    y0 = next(j for j in range(h) if rows[j] > 0)
    y1 = next(j for j in range(h - 1, -1, -1) if rows[j] > 0)
    runs = []
    run = 0
    for j in range(y0, y1 + 1):
        if rows[j] < 24:
            run += 1
        else:
            if run:
                runs.append((j - run, run))
            run = 0
    if run:
        runs.append((y1 - run + 1, run))
    return [r for r in runs if r[0] > y0 + 2 and r[0] + r[1] < y1]


def dilate(mask, r):
    a = np.array(mask)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    se = (xx * xx + yy * yy) <= r * r
    pad = np.pad(a, r, mode='constant')
    out = grey_dilation(pad, footprint=se)
    return Image.fromarray(out.astype(np.uint8))


def fit(mask, target_h=SYM_H):
    w, h = mask.size
    nw = max(1, int(round(w * target_h / h)))
    mask = mask.resize((nw, target_h), Image.LANCZOS)
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    a = Image.new('RGBA', mask.size, (255, 255, 255, 255))
    im.paste(a, (C - nw // 2, C - target_h // 2), mask)
    return im


def ask():
    f = ImageFont.truetype(FB, FONT_PT)
    tmp = Image.new('L', (1200, 1200), 0)
    d = ImageDraw.Draw(tmp)
    d.text((600, 600), '?', font=f, fill=255, anchor='mm', stroke_width=STROKE, stroke_fill=255)
    tmp = tmp.crop(tmp.getbbox())
    w, h = tmp.size
    runs = row_runs(tmp)
    gs, gl = max(runs, key=lambda r: r[1])
    d_need = int(round((2 * R_GROW + GAP_RATIO * (h + 2 * R_GROW) - gl) / (1 - GAP_RATIO)))
    d_need = max(d_need, 0)
    top = tmp.crop((0, 0, w, gs))
    bot = tmp.crop((0, gs + gl, w, h))
    canvas = Image.new('L', (w, h + d_need + 2 * R_GROW), 0)
    canvas.paste(top, (R_GROW, R_GROW))
    canvas.paste(bot, (R_GROW, R_GROW + gs + gl + d_need))
    if R_GROW > 0:
        canvas = dilate(canvas, R_GROW)
    canvas = canvas.crop(canvas.getbbox())
    print('ask  font=%d stroke=%d h=%d gap=%d pushed=%d final=%dx%d' %
          (FONT_PT, STROKE, h, gl, d_need, canvas.size[0], canvas.size[1]))
    return fit(canvas)


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


save_tga(ask(), OUT + 'QMarkAsk.tga')
save_tga(excl(), OUT + 'QMarkExcl.tga')
for f in ('QMarkAsk', 'QMarkExcl'):
    im = Image.open(OUT + f + '.tga').convert('RGBA')
    print(f, 'bbox', im.split()[3].getbbox())
