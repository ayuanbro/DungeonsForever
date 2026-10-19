from PIL import Image, ImageDraw, ImageFont
import os

S = 512
C = S // 2
R = 240
OUT = 64

DONE = (64, 217, 89, 255)
ACT = (255, 209, 0, 255)
TODO = (140, 140, 140, 255)
WHITE = (255, 255, 255, 255)

FB = 'C:/Windows/Fonts/msyhbd.ttc'
FT = 'C:/Windows/Fonts/msyh.ttc'


def glyph(ch, target_h, fpath, size=400):
    f = ImageFont.truetype(fpath, size)
    tmp = Image.new('L', (size * 2, size * 2), 0)
    d = ImageDraw.Draw(tmp)
    d.text((size, size), ch, font=f, fill=255, anchor='mm')
    bb = tmp.getbbox()
    tmp = tmp.crop(bb)
    w, h = tmp.size
    nw = max(1, int(round(w * target_h / h)))
    return tmp.resize((nw, target_h), Image.LANCZOS)


def white_glyph(ch, h):
    g = glyph(ch, h, FB)
    a = Image.new('RGBA', g.size, WHITE)
    return a, g


def paste_glyph(im, ch, h):
    a, m = white_glyph(ch, h)
    im.paste(a, (C - a.width // 2, C - a.height // 2), m)


def check(d, lw=60):
    pts = [(C - 132, C + 6), (C - 44, C + 96), (C + 144, C - 100)]
    d.line(pts, fill=WHITE, width=lw, joint='curve')
    for p in pts:
        d.ellipse([p[0] - lw // 2, p[1] - lw // 2, p[0] + lw // 2, p[1] + lw // 2], fill=WHITE)


def done_icon():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([C - R, C - R, C + R, C + R], fill=DONE)
    check(d)
    return im


def state_icon(color, ch, ring, w_ring=58, gh=296):
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if ring:
        d.ellipse([C - R, C - R, C + R, C + R], outline=color, width=w_ring)
    else:
        d.ellipse([C - R, C - R, C + R, C + R], fill=color)
    paste_glyph(im, ch, gh)
    return im


os.makedirs('_plan', exist_ok=True)
VARIANTS = ['ring', 'solid']
for v in VARIANTS:
    ring = (v == 'ring')
    for si, im in enumerate([done_icon(), state_icon(ACT, '?', ring, 58, 300), state_icon(TODO, '!', ring, 58, 268)]):
        im.resize((OUT, OUT), Image.LANCZOS).save('_plan/v2_%s_%d.png' % (v, si))
        im.resize((160, 160), Image.LANCZOS).save('_plan/v2big_%s_%d.png' % (v, si))

print('ok')
