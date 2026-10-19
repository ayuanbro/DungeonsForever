import math

from PIL import Image, ImageDraw, ImageFont

ROOT = 'D:/workspace/DungeonsForever'
AST = ROOT + '/_temp/_route_assets'
OUT = ROOT + '/_temp/_route_plan/img/pin_sheet.png'

CIRCLE = Image.open(AST + '/circle.png').convert('RGBA')
RING = Image.open(AST + '/ring.png').convert('RGBA')
DIA = Image.open(AST + '/diamond.png').convert('RGBA')
DIAR = Image.open(AST + '/diamondring.png').convert('RGBA')
SQ = Image.open(AST + '/square.png').convert('RGBA')
SQR = Image.open(AST + '/squarering.png').convert('RGBA')
CHK = Image.open(AST + '/check.png').convert('RGBA')
GLOW = Image.open(AST + '/glow.png').convert('RGBA')
PLAY = Image.open(AST + '/player.png').convert('RGBA')


def tint(im, rgb):
    from PIL import ImageChops
    layer = Image.new('RGBA', im.size, (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255))
    out = ImageChops.multiply(im, layer)
    out.putalpha(im.getchannel('A'))
    return out


def rs(im, d):
    return im.resize((int(d), int(d)), Image.LANCZOS)


def main():
    W, H = 1002, 300
    base = Image.open(ROOT + '/_temp/_route_preview_png/bfd_L2_crop.png').convert('RGBA')
    base = base.resize((W, H), Image.LANCZOS).point(lambda v: int(v * 0.42 + 20))
    canvas = base.convert('RGBA')
    d = ImageDraw.Draw(canvas)
    try:
        f13 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 13)
        f11 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 11)
        fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 11)
    except Exception:
        f13 = f11 = fb = ImageFont.load_default()

    items = [
        ('boss', (242, 194, 79), '首领 Boss', '24px · 金环'),
        ('rare', (227, 222, 209), '稀有 Rare', '24px · 银环'),
        ('optional', (158, 199, 242), '可选 Optional', '24px · 蓝环'),
        ('done', (242, 194, 79), '已完成', '勾 + alpha 55%'),
        ('next', (242, 194, 79), '下一个目标', '46px 光晕'),
        ('note', (255, 199, 178), '注释 Note', '20px · 菱形'),
        ('link', (171, 209, 255), '楼层链接', '20px · 方钉'),
        ('player', (255, 214, 92), '玩家 / 队友', '28px · 朝向箭头'),
        ('edit', (255, 255, 255), '编辑顶点', '5px（当前 9px）'),
    ]
    cx0, step = 74, 104
    cy = 120

    def paste(im, x, y):
        canvas.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))

    for i, (kind, rgb, label, sub) in enumerate(items):
        x = cx0 + i * step
        if kind in ('boss', 'rare', 'optional', 'done', 'next'):
            paste(rs(tint(CIRCLE, (0.06, 0.05, 0.04)), 24), x, cy)
            paste(rs(tint(RING, [v / 255 for v in rgb]), 24), x, cy)
            d.text((x, cy + 1), '1', font=fb, fill=rgb, anchor='mm')
            if kind == 'done':
                paste(rs(tint(CHK, (0.25, 0.85, 0.35)), 18), x + 8, cy + 8)
            if kind == 'next':
                g = rs(tint(GLOW, (1, 0.85, 0.4)), 46)
                ovy = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
                ovy.alpha_composite(g, (int(x - 23), int(cy - 23)))
                canvas.alpha_composite(ovy)
                paste(rs(tint(CIRCLE, (0.06, 0.05, 0.04)), 24), x, cy)
                paste(rs(tint(RING, [v / 255 for v in rgb]), 24), x, cy)
                d.text((x, cy + 1), '2', font=fb, fill=rgb, anchor='mm')
        elif kind == 'note':
            paste(rs(tint(DIA, (0.55, 0.16, 0.14)), 20), x, cy)
            paste(rs(tint(DIAR, (1, 0.78, 0.7)), 20), x, cy)
            d.text((x, cy), '!', font=fb, fill=(255, 244, 236), anchor='mm')
        elif kind == 'link':
            paste(rs(tint(SQ, (0.12, 0.24, 0.36)), 20), x, cy)
            paste(rs(tint(SQR, (0.67, 0.82, 1.0)), 20), x, cy)
            d.line([x, cy - 5, x, cy + 5], fill=(230, 242, 255), width=2)
            d.polygon([(x - 4, cy - 3), (x, cy - 7), (x + 4, cy - 3)], fill=(230, 242, 255))
            d.polygon([(x - 4, cy + 3), (x, cy + 7), (x + 4, cy + 3)], fill=(230, 242, 255))
        elif kind == 'player':
            paste(rs(tint(PLAY, (1, 1, 1)), 28), x, cy)
        elif kind == 'edit':
            for k in range(3):
                r = 5 if k != 1 else 9
                paste(rs(tint(CIRCLE, (1, 1, 1)), r), x - 16 + k * 16, cy)
        d.text((x, cy + 26), label, font=f13, fill=(238, 232, 220), anchor='ma')
        d.text((x, cy + 44), sub, font=f11, fill=(168, 160, 148), anchor='ma')

    d.text((16, 14), '图钉类型 · 按真实尺寸 1:1 渲染', font=f13, fill=(255, 222, 150))
    d.text((16, 34), '底图为黑暗深渊第二层，压暗背景以便看清', font=f11, fill=(170, 162, 150))
    canvas.convert('RGB').save(OUT, quality=92)
    print(OUT, canvas.size)


if __name__ == '__main__':
    main()
