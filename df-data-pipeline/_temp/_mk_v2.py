from PIL import Image, ImageDraw, ImageFont

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'
BG = (28, 31, 37, 255)
CW, CH = 170, 42
STATES = ['已完成', '已接取', '未接取']
EDGE = [(64, 217, 89), (255, 209, 0), (150, 150, 150)]
VAR = [('ring', '版本 A · 空心圈（推荐）', '空心 = 未完成，与已完成的实心绿圆形成层级'),
       ('solid', '版本 B · 实心圆', '三态同为实心圆，只靠颜色 + 符号区分')]

W, ROWH, HEAD = 1240, 300, 108
sheet = Image.new('RGBA', (W, HEAD + ROWH * 2 + 12), (20, 22, 26, 255))
sd = ImageDraw.Draw(sheet)
sd.text((34, 26), '三态图标 · 黄圈问号 / 灰圈叹号', font=ImageFont.truetype(FB, 27), fill=(240, 243, 250, 255))
sd.text((34, 68), '图标槽 14x14 逻辑像素 · 母版 64x64（4x 密度）· 已完成沿用现有绿圆白勾', font=ImageFont.truetype(FT, 15), fill=(148, 153, 163, 255))

for vi, (v, title, sub) in enumerate(VAR):
    y0 = HEAD + vi * ROWH
    sd.rounded_rectangle([18, y0, W - 18, y0 + ROWH - 16], radius=10, fill=(27, 29, 34, 255))
    sd.text((40, y0 + 18), title, font=ImageFont.truetype(FB, 21), fill=(236, 239, 246, 255))
    sd.text((40, y0 + 50), sub, font=ImageFont.truetype(FT, 14), fill=(142, 147, 157, 255))
    for si in range(3):
        x = 430 + si * 268
        big = Image.open('_plan/v2big_%s_%d.png' % (v, si)).convert('RGBA').resize((168, 168), Image.LANCZOS)
        sheet.alpha_composite(big, (x, y0 + 20))
        sm = Image.open('_plan/v2_%s_%d.png' % (v, si)).convert('RGBA').resize((14, 14), Image.LANCZOS)
        sheet.alpha_composite(sm.resize((48, 48), Image.NEAREST), (x, y0 + 202))
        sd.text((x + 60, y0 + 200), STATES[si], font=ImageFont.truetype(FB, 16), fill=EDGE[si])
        sd.text((x + 60, y0 + 224), '实际 14px 放大 3.4x', font=ImageFont.truetype(FT, 11), fill=(122, 127, 137, 255))

sheet.save('_plan/v2_icons.png')


def card(v, si):
    c = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=8, fill=BG, outline=EDGE[si] + (115,), width=1)
    d.text((6, 3), '谅解条约', font=ImageFont.truetype(FT, 14), fill=(228, 232, 240, 255))
    d.rounded_rectangle([5, 23, 45, 36], radius=3, fill=(70, 100, 150, 255))
    d.text((9, 24), '副本内', font=ImageFont.truetype(FT, 10), fill=(255, 255, 255, 255))
    ico = Image.open('_plan/v2_%s_%d.png' % (v, si)).convert('RGBA').resize((14, 14), Image.LANCZOS)
    c.alpha_composite(ico, (CW - 6 - 14, CH - 4 - 14))
    return c


Z = 3
LX = 168
colw, rowh = CW * Z, CH * Z
W2 = LX + colw * 3 + 26 * 3 + 12
H2 = 74 + (rowh + 44) * 2
s2 = Image.new('RGBA', (W2, H2), (20, 22, 26, 255))
d2 = ImageDraw.Draw(s2)
d2.text((24, 20), '卡片实景（3x 放大，图标为真实 14px 采样）', font=ImageFont.truetype(FB, 21), fill=(238, 241, 248, 255))
for si in range(3):
    d2.text((LX + si * (colw + 26) + 2, 50), STATES[si], font=ImageFont.truetype(FT, 13), fill=EDGE[si])
for vi, (v, title, sub) in enumerate(VAR):
    y = 74 + vi * (rowh + 44)
    d2.text((24, y + rowh // 2 - 20), title.split(' · ')[0], font=ImageFont.truetype(FB, 15), fill=(200, 205, 215, 255))
    d2.text((24, y + rowh // 2 + 1), title.split(' · ')[1].split('（')[0], font=ImageFont.truetype(FT, 13), fill=(140, 145, 155, 255))
    for si in range(3):
        c = card(v, si).resize((colw, rowh), Image.LANCZOS)
        s2.alpha_composite(c, (LX + si * (colw + 26), y))
s2.save('_plan/v2_cards.png')
print(sheet.size, s2.size)
