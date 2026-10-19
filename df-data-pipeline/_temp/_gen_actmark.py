import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'

BASE = Image.open('../Media/CheckDisc.tga').convert('RGBA')
ASK = Image.open('../Media/QMarkAsk.tga').convert('RGBA')

GOLD = (255, 209, 0)


def lum(c):
    def f(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


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


def outlined(sym, rgb, px=4):
    mask = sym.split()[3].filter(ImageFilter.MaxFilter(px * 2 + 1))
    o = Image.new('RGBA', sym.size, rgb + (0,))
    o.putalpha(mask)
    o.alpha_composite(sym)
    return o


def build(base_rgb, sym=None):
    im = tint(BASE, base_rgb)
    im.alpha_composite(sym if sym is not None else ASK)
    return im


def solid(sym, rgb):
    o = Image.new('RGBA', sym.size, rgb + (0,))
    o.putalpha(sym.split()[3])
    return o


VARIANTS = []


def add(key, name, img, base_rgb, sym_rgb, note):
    VARIANTS.append(dict(key=key, name=name, img=img, base=base_rgb,
                         sym=sym_rgb, note=note, cr=ratio(base_rgb, sym_rgb)))


add('S', '现状', build(GOLD), GOLD, (255, 255, 255), '亮金 + 白符号')
add('A', '深墨符号', build(GOLD, solid(ASK, (58, 42, 0))), GOLD, (58, 42, 0), '金色不动，符号改深墨')
add('B', '压暗金', build((184, 134, 11)), (184, 134, 11), (255, 255, 255), '金色压到 72%')
add('C', '暗琥珀', build((166, 112, 0)), (166, 112, 0), (255, 255, 255), '金色压到 65%，偏琥珀')
add('D', '描边白符号', build(GOLD, outlined(ASK, (52, 38, 0), 4)), GOLD, (255, 255, 255), '金色不动，白符号加深描边')

os.makedirs('_plan', exist_ok=True)

CW, CH = 170, 42
CARDBG = (26, 29, 35, 255)


def card_img(im):
    c = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=8, fill=CARDBG, outline=GOLD + (150,), width=1)
    d.text((6, 2), '地下地图', font=ImageFont.truetype(FT, 14), fill=(230, 233, 240, 255))
    d.rounded_rectangle([6, 23, 44, 36], radius=3, fill=GOLD + (255,))
    d.text((9, 24), '前置', font=ImageFont.truetype(FT, 10), fill=(60, 44, 0, 255))
    c.alpha_composite(im.resize((14, 14), Image.LANCZOS), (CW - 6 - 14, CH - 4 - 14))
    return c


COLW = 262
HEAD = 116
CARD_Z = 1.45
H = HEAD + 132 + 130 + int(CH * CARD_Z) + 34
W = 40 + COLW * len(VARIANTS)
sheet = Image.new('RGBA', (W, H), (18, 20, 24, 255))
sd = ImageDraw.Draw(sheet)

sd.text((26, 18), '已接取图标 · 底色与符号配色方案', font=ImageFont.truetype(FB, 25), fill=(240, 242, 248, 255))
sd.text((26, 54), '真实贴图合成，符号槽 14px。右侧大图 = 14px 原始采样放大 8 倍',
        font=ImageFont.truetype(FT, 14), fill=(150, 156, 168, 255))

for i, v in enumerate(VARIANTS):
    x = 40 + i * COLW
    cur = (v['key'] == 'S')
    sd.rounded_rectangle([x, HEAD, x + COLW - 18, H - 16], radius=12,
                         fill=(25, 27, 32, 255) if not cur else (32, 29, 22, 255),
                         outline=(255, 209, 0, 80) if cur else (255, 255, 255, 14), width=1)
    sd.text((x + 16, HEAD + 12), v['key'], font=ImageFont.truetype(FB, 14), fill=(150, 156, 168, 255))
    sd.text((x + 36, HEAD + 10), v['name'], font=ImageFont.truetype(FB, 17), fill=(236, 239, 246, 255))

    sheet.alpha_composite(v['img'].resize((84, 84), Image.LANCZOS), (x + 16, HEAD + 40))
    sheet.alpha_composite(v['img'].resize((14, 14), Image.LANCZOS).resize((112, 112), Image.NEAREST),
                          (x + 114, HEAD + 26))
    sd.text((x + 114, HEAD + 140), '14px', font=ImageFont.truetype(FT, 11), fill=(118, 124, 136, 255))

    sd.text((x + 16, HEAD + 148), v['note'], font=ImageFont.truetype(FT, 13), fill=(158, 164, 176, 255))
    cr = v['cr']
    col = (92, 210, 124) if cr >= 4.5 else ((236, 200, 72) if cr >= 3 else (232, 108, 96))
    sd.text((x + 16, HEAD + 168), '对比 %.2f:1' % cr, font=ImageFont.truetype(FB, 13), fill=col)
    sd.text((x + 16, HEAD + 188), '底 #%02X%02X%02X' % v['base'], font=ImageFont.truetype(FT, 12), fill=(130, 136, 148, 255))
    sd.text((x + 16, HEAD + 204), '符 #%02X%02X%02X' % v['sym'], font=ImageFont.truetype(FT, 12), fill=(130, 136, 148, 255))

    ci = card_img(v['img']).resize((int(CW * CARD_Z), int(CH * CARD_Z)), Image.LANCZOS)
    sheet.alpha_composite(ci, (x + 14, HEAD + 226))

sheet.save('_plan/act_plans.png')
print('ok', sheet.size)
