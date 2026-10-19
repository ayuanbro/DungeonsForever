from PIL import Image, ImageDraw, ImageFont

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'
CW, CH = 170, 42
BG = (28, 31, 37, 255)


def card(ico_path, title):
    c = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=8, fill=BG, outline=(72, 78, 90, 255), width=1)
    d.text((6, 3), title, font=ImageFont.truetype(FT, 14), fill=(228, 232, 240, 255))
    d.rounded_rectangle([5, 23, 45, 36], radius=3, fill=(70, 100, 150, 255))
    d.text((9, 24), '副本内', font=ImageFont.truetype(FT, 10), fill=(255, 255, 255, 255))
    if ico_path:
        ico = Image.open(ico_path).convert('RGBA').resize((14, 14), Image.LANCZOS)
        c.alpha_composite(ico, (CW - 6 - 14, CH - 4 - 14))
    return c


names = ['s1', 's2', 's3', 's4']
labels = ['已完成', '已接取', '未接取']
Z = 6
pad = 14
W = CW * Z * 3 + pad * 4
H = CH * Z * 4 + pad * 5
sheet = Image.new('RGBA', (W, H), (18, 20, 24, 255))
for pi, nm in enumerate(names):
    for si in range(3):
        c = card('_plan/%s_%d.png' % (nm, si), '谅解条约')
        c = c.resize((CW * Z, CH * Z), Image.LANCZOS)
        sheet.alpha_composite(c, (pad + si * (CW * Z + pad), pad + pi * (CH * Z + pad)))
sheet.save('_plan/plan_cards_2.png')
print(sheet.size)
