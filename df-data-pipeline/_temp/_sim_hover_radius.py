from PIL import Image, ImageDraw, ImageFont

ROW_W, ROW_H = 496, 34
PAD = 12
S = 8
CZ = 56

CARD_BG = (0x2A, 0x30, 0x3D)
CARD_BORDER = (0x55, 0x5C, 0x6A)
HOV = (0x3B, 0x43, 0x54)
OUT_BG = (0x14, 0x18, 0x20)
DIM = (0x8A, 0x93, 0xA3)


def row_img(hov_r):
    W, H = ROW_W + PAD * 2, ROW_H + PAD * 2
    im = Image.new('RGB', (W, H), OUT_BG)
    x0, y0 = PAD, PAD
    x1, y1 = PAD + ROW_W, PAD + ROW_H
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x0, y0, x1, y1], radius=6, fill=CARD_BG,
                        outline=CARD_BORDER, width=1)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=hov_r, fill=255)
    im.paste(Image.new('RGB', (W, H), HOV), (0, 0), mask)
    f = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 12)
    d.text((x0 + 12, (y0 + y1) // 2), '旧铁炉堡入侵', font=f,
           fill=(0xE6, 0xE9, 0xEE), anchor='lm')
    return im


before = row_img(12)
after = row_img(6)

tiles = []
for im in (before, after):
    for cx, cy in ((PAD, PAD), (PAD + ROW_W, PAD)):
        z = im.crop((cx - CZ // 2, cy - CZ // 2, cx + CZ // 2, cy + CZ // 2))
        tiles.append(z.resize((CZ * S, CZ * S), Image.NEAREST))

gap = 24
W = CZ * S * 4 + gap * 5
H = CZ * S + gap * 2 + 58
canvas = Image.new('RGB', (W, H), (0x11, 0x14, 0x1B))
d = ImageDraw.Draw(canvas)
f = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 15)
fd = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 13)
labels = ['修改前 · 左上角', '修改前 · 右上角', '修改后 · 左上角', '修改后 · 右上角']
for i, t in enumerate(tiles):
    x = gap + i * (CZ * S + gap)
    y = gap
    canvas.paste(t, (x, y))
    d.rectangle([x, y, x + CZ * S, y + CZ * S], outline=(0x33, 0x3A, 0x48), width=1)
    d.text((x + CZ * S / 2, y + CZ * S + 8), labels[i], font=f, fill=DIM, anchor='ma')
d.text((gap, H - 18),
       '选中高亮胶囊半径 12 ≠ 底卡圆角 6 → 四角双弧/月牙缝；同径 6 后角弧贴合（8x 放大）',
       font=fd, fill=DIM, anchor='lm')
canvas.save('_temp/_corner_view/quest_hover_radius_fix.png')
print('saved', canvas.size)
