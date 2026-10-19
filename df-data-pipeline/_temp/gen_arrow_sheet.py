from PIL import Image, ImageDraw, ImageFont

BG = (26, 29, 35)
CARD = (22, 26, 34)
TXT = (232, 234, 238)
DIM = (150, 154, 162)

ROWS = [
    ('A', 'Chevron', '_temp/_arrow_A_detail.png', '_temp/_arrow_A_px12.png'),
    ('B', 'Bar+head', '_temp/_arrow_B_detail.png', '_temp/_arrow_B_px12.png'),
    ('C', 'Double-V', '_temp/_arrow_C_detail.png', '_temp/_arrow_C_px12.png'),
    ('D', 'Triangle', '_temp/_arrow_D_detail.png', '_temp/_arrow_D_px12.png'),
    ('E', 'Thin line', '_temp/_arrow_E_detail.png', '_temp/_arrow_E_px12.png'),
]

ROW_H = 104
W = 660
H = 60 + ROW_H * len(ROWS) + 14
sheet = Image.new('RGB', (W, H), BG)
dr = ImageDraw.Draw(sheet)
try:
    fb = ImageFont.truetype('arialbd.ttf', 17)
    fs = ImageFont.truetype('arial.ttf', 13)
    fxs = ImageFont.truetype('arial.ttf', 11)
except Exception:
    fb = fs = fxs = ImageFont.load_default()

dr.text((20, 16), 'Arrow style variants  -  gold = in-game vertex color', font=fs, fill=DIM)

y = 60
for key, name, dp, pp in ROWS:
    dr.rounded_rectangle((16, y + 6, W - 16, y + ROW_H - 6), 10, fill=CARD)
    dr.rounded_rectangle((30, y + 32, 62, y + 64), 8, fill=(55, 138, 221))
    dr.text((38, y + 38), key, font=fb, fill=(255, 255, 255))
    dr.text((78, y + 40), name, font=fs, fill=TXT)

    dr.text((150, y + 16), '64x64 detail', font=fxs, fill=DIM)
    d64 = Image.open(dp).convert('RGBA')
    sheet.paste(d64, (150, y + 32), d64)

    dr.text((240, y + 16), '12px (4x)', font=fxs, fill=DIM)
    p12 = Image.open(pp).convert('RGBA').resize((12, 12), Image.NEAREST)
    sheet.paste(p12.resize((48, 48), Image.NEAREST), (236, y + 32), p12.resize((48, 48), Image.NEAREST))

    dr.text((310, y + 16), '12px real', font=fxs, fill=DIM)
    sheet.paste(p12, (306, y + 48), p12)

    dr.text((370, y + 16), 'card gap scene', font=fxs, fill=DIM)
    cx = 366
    dr.rounded_rectangle((cx, y + 40, cx + 56, y + 64), 5, fill=CARD, outline=(90, 95, 105))
    dr.rounded_rectangle((cx + 68, y + 40, cx + 124, y + 64), 5, fill=CARD, outline=(90, 95, 105))
    sheet.paste(p12, (cx + 56, y + 46), p12)

    dr.text((510, y + 16), 'chain', font=fxs, fill=DIM)
    sheet.paste(p12, (506, y + 48), p12)
    sheet.paste(p12, (520, y + 48), p12)
    sheet.paste(p12, (534, y + 48), p12)

    y += ROW_H

sheet.save('_temp/_arrow_variants_sheet.png')
print('wrote _temp/_arrow_variants_sheet.png', sheet.size)
