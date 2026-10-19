from PIL import Image, ImageDraw, ImageFont

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'
CW, CH = 170, 42
BG = (28, 31, 37, 255)
NAMES = ['s1', 's2', 's3', 's4']
PLAN_T = ['方案 1  同族圆标', '方案 2  靶心三态', '方案 3  清单方块', '方案 4  开口环']
STATES = ['已完成', '已接取', '未接取']


def card(ico_path, title, state_i):
    c = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    edge = [(64, 217, 89), (255, 209, 0), (150, 150, 150)][state_i]
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=8, fill=BG,
                        outline=edge + (110,), width=1)
    d.text((6, 3), title, font=ImageFont.truetype(FT, 14), fill=(228, 232, 240, 255))
    d.rounded_rectangle([5, 23, 45, 36], radius=3, fill=(70, 100, 150, 255))
    d.text((9, 24), '副本内', font=ImageFont.truetype(FT, 10), fill=(255, 255, 255, 255))
    if ico_path:
        ico = Image.open(ico_path).convert('RGBA').resize((14, 14), Image.LANCZOS)
        c.alpha_composite(ico, (CW - 6 - 14, CH - 4 - 14))
    return c


Z = 3
LX, TOP = 150, 92
colw = CW * Z
rowh = CH * Z
gapx, gapy = 26, 20
W = LX + colw * 3 + gapx * 3 + 8
H = TOP + rowh * 4 + gapy * 4 + 10
sheet = Image.new('RGBA', (W, H), (18, 20, 24, 255))
sd = ImageDraw.Draw(sheet)
sd.text((24, 20), '卡片实景观感（3x 放大，图标为真实 14px 采样）', font=ImageFont.truetype(FB, 22), fill=(238, 241, 248, 255))
for si in range(3):
    x = LX + si * (colw + gapx)
    sd.text((x + 2, 60), STATES[si], font=ImageFont.truetype(FB, 15),
            fill=[(120, 225, 140), (255, 214, 70), (170, 175, 185)][si])
for pi, nm in enumerate(NAMES):
    y = TOP + pi * (rowh + gapy)
    sd.text((24, y + rowh // 2 - 12), PLAN_T[pi], font=ImageFont.truetype(FB, 15), fill=(200, 205, 215, 255))
    for si in range(3):
        c = card('_plan/%s_%d.png' % (nm, si), '谅解条约', si)
        c = c.resize((colw, rowh), Image.LANCZOS)
        sheet.alpha_composite(c, (LX + si * (colw + gapx), y))
sheet.save('_plan/plan_cards_3.png')
print(sheet.size)
