import os
from PIL import Image, ImageDraw, ImageFont

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'

DISC = Image.open('../Media/CheckDisc.tga').convert('RGBA')
ASK = Image.open('../Media/QMarkAsk.tga').convert('RGBA')
EXC = Image.open('../Media/QMarkExcl.tga').convert('RGBA')
MARK = Image.open('../Media/CheckMark.tga').convert('RGBA')

GREEN = (64, 217, 89)
GOLD = (255, 209, 0)
GREY = (140, 140, 140)
INK_A = (58, 42, 0)
INK_D = (11, 61, 26)
INK_T = (26, 26, 26)


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


def icon(base, sym, symrgb=None):
    im = tint(DISC, base)
    s = tint(sym, symrgb) if symrgb else sym
    im.alpha_composite(s)
    return im


CW, CH = 170, 42
CARDBG = (26, 29, 35, 255)


def card(ico):
    c = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=8, fill=CARDBG, outline=(255, 255, 255, 30), width=1)
    d.text((6, 2), '地下地图', font=ImageFont.truetype(FT, 14), fill=(230, 233, 240, 255))
    d.rounded_rectangle([6, 23, 44, 36], radius=3, fill=(70, 100, 150, 255))
    d.text((9, 24), '副本内', font=ImageFont.truetype(FT, 10), fill=(255, 255, 255, 255))
    c.alpha_composite(ico.resize((14, 14), Image.LANCZOS), (CW - 6 - 14, CH - 4 - 14))
    return c


TRIO = [
    ('已完成', icon(GREEN, MARK, INK_D)),
    ('已接取', icon(GOLD, ASK, INK_A)),
    ('未接取', icon(GREY, EXC, INK_T)),
]

W, H = 1000, 470
sheet = Image.new('RGBA', (W, H), (18, 20, 24, 255))
sd = ImageDraw.Draw(sheet)
sd.text((28, 18), 'E 方案落地 · 三态统一「亮底 + 深色符号」', font=ImageFont.truetype(FB, 23),
        fill=(240, 242, 248, 255))
sd.text((28, 54), '三种状态并排，右侧为 14px 原始采样放大 10 倍', font=ImageFont.truetype(FT, 14),
        fill=(150, 156, 168, 255))

for i, (nm, ico) in enumerate(TRIO):
    x = 30 + i * 322
    sd.rounded_rectangle([x, 92, x + 300, 250], radius=12, fill=(25, 27, 32, 255),
                         outline=(255, 255, 255, 12), width=1)
    sd.text((x + 16, 106), nm, font=ImageFont.truetype(FB, 16), fill=(205, 210, 220, 255))
    sheet.alpha_composite(ico.resize((72, 72), Image.LANCZOS), (x + 16, 134))
    sheet.alpha_composite(ico.resize((14, 14), Image.LANCZOS).resize((126, 126), Image.NEAREST), (x + 158, 112))
    sd.text((x + 16, 218), '14px 实际效果', font=ImageFont.truetype(FT, 12),
            fill=(140, 146, 158, 255))

sd.text((28, 272), '真实卡片（4x）', font=ImageFont.truetype(FB, 15), fill=(190, 195, 205, 255))
for i, (nm, ico) in enumerate(TRIO):
    cx = 30 + i * 322
    sheet.alpha_composite(card(ico).resize((int(CW * 1.7), int(CH * 1.7)), Image.LANCZOS), (cx, 302))

sd.text((28, 400), '说明：三态底色不变（绿 #40D959 / 金 #FFD100 / 灰 #8C8C8C），符号统一改深色：深绿 #0B3D1A / 深墨 #3A2A00 / 深灰 #1A1A1A。',
        font=ImageFont.truetype(FT, 13), fill=(150, 156, 168, 255))
sd.text((28, 422), '问号已放大到 22x46（原 20x42），叹号杆加粗到 10px、点半径 40，问号点与杆净空约 1.2px。',
        font=ImageFont.truetype(FT, 13), fill=(150, 156, 168, 255))

os.makedirs('_plan', exist_ok=True)
sheet.save('_plan/act_A_final.png')
print('ok', sheet.size)
