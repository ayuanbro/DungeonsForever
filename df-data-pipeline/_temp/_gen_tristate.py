import os
from PIL import Image, ImageDraw, ImageFont

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'

DISC = Image.open('../Media/CheckDisc.tga').convert('RGBA')
SYMS = {
    'done': Image.open('../Media/CheckMark.tga').convert('RGBA'),
    'ask': Image.open('../Media/QMarkAsk.tga').convert('RGBA'),
    'exc': Image.open('../Media/QMarkExcl.tga').convert('RGBA'),
}

GREEN = (64, 217, 89)
GOLD = (255, 209, 0)
DARKGOLD = (184, 134, 11)
AMBER = (166, 112, 0)
GREY = (140, 140, 140)


def tint(img, rgb):
    out = img.copy()
    px = out.load()
    w, h = out.size
    for j in range(h):
        for i in range(w):
            r, g, b, a = px[i, j]
            if a > 0:
                px[i, j] = (rgb[0], rgb[1], rgb[2], a)
    return out


def solid(sym, rgb):
    o = Image.new('RGBA', sym.size, rgb + (0,))
    o.putalpha(sym.split()[3])
    return o


def icon(base, sym):
    im = tint(DISC, base)
    im.alpha_composite(sym)
    return im


SETS = [
    ('S · 现状', [
        icon(GREEN, SYMS['done']),
        icon(GOLD, SYMS['ask']),
        icon(GREY, SYMS['exc']),
    ]),
    ('A · 深墨符号', [
        icon(GREEN, SYMS['done']),
        icon(GOLD, solid(SYMS['ask'], (58, 42, 0))),
        icon(GREY, SYMS['exc']),
    ]),
    ('B · 压暗金', [
        icon(GREEN, SYMS['done']),
        icon(DARKGOLD, SYMS['ask']),
        icon(GREY, SYMS['exc']),
    ]),
    ('C · 暗琥珀', [
        icon(GREEN, SYMS['done']),
        icon(AMBER, SYMS['ask']),
        icon(GREY, SYMS['exc']),
    ]),
    ('E · 三态统一深符号', [
        icon(GREEN, solid(SYMS['done'], (11, 61, 26))),
        icon(GOLD, solid(SYMS['ask'], (58, 42, 0))),
        icon(GREY, solid(SYMS['exc'], (43, 43, 43))),
    ]),
]

CW, CH = 170, 42
CARDBG = (26, 29, 35, 255)
NAMES = ['已完成', '已接取', '未接取']
EDGE = [GREEN, GOLD, GREY]


def card(ico):
    c = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=8, fill=CARDBG, outline=(255, 255, 255, 30), width=1)
    d.text((6, 2), '地下地图', font=ImageFont.truetype(FT, 14), fill=(230, 233, 240, 255))
    d.rounded_rectangle([6, 23, 44, 36], radius=3, fill=(70, 100, 150, 255))
    d.text((9, 24), '副本内', font=ImageFont.truetype(FT, 10), fill=(255, 255, 255, 255))
    c.alpha_composite(ico.resize((14, 14), Image.LANCZOS), (CW - 6 - 14, CH - 4 - 14))
    return c


ROWH = 178
W = 40 + 240 + 3 * 262
H = 96 + ROWH * len(SETS) + 10
sheet = Image.new('RGBA', (W, H), (18, 20, 24, 255))
sd = ImageDraw.Draw(sheet)
sd.text((26, 18), '三态并排 · 选哪一版已接取图标', font=ImageFont.truetype(FB, 25), fill=(240, 242, 248, 255))
sd.text((26, 54), '上方 64px 母版，下方真实卡片（3x）', font=ImageFont.truetype(FT, 14), fill=(150, 156, 168, 255))

for r, (name, icons) in enumerate(SETS):
    y = 96 + r * ROWH
    cur = name.startswith('S')
    sd.rounded_rectangle([20, y, W - 20, y + ROWH - 16], radius=12,
                         fill=(25, 27, 32, 255) if not cur else (32, 29, 22, 255),
                         outline=(255, 209, 0, 70) if cur else (255, 255, 255, 10), width=1)
    sd.text((36, y + 20), name, font=ImageFont.truetype(FB, 17), fill=(236, 239, 246, 255))
    for c, ico in enumerate(icons):
        x = 40 + 240 + c * 262
        sheet.alpha_composite(ico.resize((46, 46), Image.LANCZOS), (x, y + 12))
        sheet.alpha_composite(ico.resize((14, 14), Image.LANCZOS).resize((56, 56), Image.NEAREST), (x + 52, y + 8))
        sheet.alpha_composite(card(ico).resize((CW * 3 // 2, CH * 3 // 2), Image.LANCZOS), (x, y + 78))

sheet.save('_plan/act_tristate.png')
print('ok', sheet.size)
