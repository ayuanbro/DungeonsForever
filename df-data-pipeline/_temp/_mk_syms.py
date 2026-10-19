from PIL import Image, ImageDraw, ImageFont

SS, S = 8, 512
C, R = S // 2, 240
ACT = (255, 209, 0, 255)
WHITE = (255, 255, 255, 255)


def base():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([C - R, C - R, C + R, C + R], fill=ACT)
    return im, d


def sym_bang(d):
    d.rounded_rectangle([C - 28, C - 138, C + 28, C + 42], radius=28, fill=WHITE)
    r = 36
    d.ellipse([C - r, C + 40, C + r, C + 112], fill=WHITE)


def sym_tri(d):
    d.polygon([(C - 66, C - 128), (C - 66, C + 128), (C + 132, C)], fill=WHITE)


def sym_dot(d):
    r = 92
    d.ellipse([C - r, C - r, C + r, C + r], fill=WHITE)


def sym_dia(d):
    d.polygon([(C, C - 118), (C + 118, C), (C, C + 118), (C - 118, C)], fill=WHITE)


def sym_dash(d):
    for i, dx in enumerate((-84, 0, 84)):
        r = 26
        d.ellipse([C + dx - r, C - r, C + dx + r, C + r], fill=WHITE)


def sym_ring(d):
    d.ellipse([C - 96, C - 96, C + 96, C + 96], outline=WHITE, width=54)


SYMS = [('叹号', sym_bang), ('三角', sym_tri), ('圆点', sym_dot),
        ('菱形', sym_dia), ('三点', sym_dash), ('空心', sym_ring)]

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'
Z = 134
W = 40 + len(SYMS) * (Z + 26)
H = 268
sheet = Image.new('RGBA', (W, H), (20, 22, 26, 255))
sd = ImageDraw.Draw(sheet)
sd.text((24, 16), '「已接取」符号备选（同为金色实心圆底）', font=ImageFont.truetype(FB, 20), fill=(238, 241, 248, 255))
for i, (nm, fn) in enumerate(SYMS):
    im, d = base()
    fn(d)
    x = 40 + i * (Z + 26)
    sheet.alpha_composite(im.resize((Z, Z), Image.LANCZOS), (x, 56))
    small = im.resize((64, 64), Image.LANCZOS).resize((14, 14), Image.LANCZOS)
    sheet.alpha_composite(small.resize((42, 42), Image.NEAREST), (x + 86, 208))
    sd.text((x, 214), nm, font=ImageFont.truetype(FT, 14), fill=(190, 195, 205, 255))
sheet.save('_plan/act_symbols.png')
print(sheet.size)
