from PIL import Image, ImageDraw, ImageFont
import os

SS = 8
S = 512
C = S // 2
OUT = 64

DONE = (64, 217, 89, 255)
ACT = (255, 209, 0, 255)
TODO = (140, 140, 140, 255)
WHITE = (255, 255, 255, 255)
R = 240


def canvas():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def check_color(d, color, lw=60):
    pts = [(C - 132, C + 6), (C - 44, C + 96), (C + 144, C - 100)]
    d.line(pts, fill=color, width=lw, joint='curve')
    for p in pts:
        d.ellipse([p[0] - lw // 2, p[1] - lw // 2, p[0] + lw // 2, p[1] + lw // 2], fill=color)


def bang(d, color, lw=56):
    d.rounded_rectangle([C - lw // 2, C - 138, C + lw // 2, C + 42], radius=lw // 2, fill=color)
    r = 36
    d.ellipse([C - r, C + 76 - r, C + r, C + 76 + r], fill=color)


def s1_done():
    im, d = canvas()
    d.ellipse([C - R, C - R, C + R, C + R], fill=DONE)
    check_color(d, WHITE)
    return im


def s1_act():
    im, d = canvas()
    d.ellipse([C - R, C - R, C + R, C + R], fill=ACT)
    bang(d, WHITE)
    return im


def s1_todo():
    im, d = canvas()
    d.ellipse([C - R, C - R, C + R, C + R], outline=TODO, width=56)
    return im


def s2_done():
    return s1_done()


def s2_act():
    im, d = canvas()
    d.ellipse([C - R, C - R, C + R, C + R], outline=ACT, width=60)
    r = 92
    d.ellipse([C - r, C - r, C + r, C + r], fill=ACT)
    return im


def s2_todo():
    im, d = canvas()
    d.ellipse([C - R, C - R, C + R, C + R], outline=TODO, width=40)
    return im


def box(d, fill, outline, lw):
    pad = 24
    d.rounded_rectangle([C - R - 4 + pad, C - R - 4 + pad, C + R + 4 - pad, C + R + 4 - pad],
                        radius=80, fill=fill, outline=outline, width=lw)


def s3_done():
    im, d = canvas()
    box(d, DONE, None, 0)
    check_color(d, WHITE, 58)
    return im


def s3_act():
    im, d = canvas()
    box(d, None, ACT, 58)
    d.rounded_rectangle([C - 96, C - 28, C + 96, C + 28], radius=28, fill=ACT)
    return im


def s3_todo():
    im, d = canvas()
    box(d, None, TODO, 48)
    return im


def s4_done():
    return s1_done()


def s4_act():
    im, d = canvas()
    d.arc([C - R, C - R, C + R, C + R], 315, 225, fill=ACT, width=58)
    for ang in (315, 225):
        pass
    return im


def s4_todo():
    im, d = canvas()
    d.arc([C - R, C - R, C + R, C + R], 0, 180, fill=TODO, width=56)
    return im


PLANS = [
    ('方案 1', '同族圆标', ('三态同一尺寸底形，只换颜色和内部符号：', '勾 / 叹号 / 空环'), [s1_done, s1_act, s1_todo]),
    ('方案 2', '靶心三态', ('已完成实心，已接取金环套实心点，', '未接取细灰环 —— 靠填充度分层'), [s2_done, s2_act, s2_todo]),
    ('方案 3', '清单方块', ('改成圆角勾选框：实心勾 / 半选横杠 /', '空框，最像任务清单'), [s3_done, s3_act, s3_todo]),
    ('方案 4', '开口环', ('靠缺口大小表示完成度：全勾 / 缺 90° /', '缺 180° 半环'), [s4_done, s4_act, s4_todo]),
]

STATES = ['已完成', '已接取', '未接取']
NAMES = ['s1', 's2', 's3', 's4']

os.makedirs('_plan', exist_ok=True)
big = {}
for pi, (tag, name, desc, fns) in enumerate(PLANS):
    for si, fn in enumerate(fns):
        im = fn()
        small = im.resize((OUT, OUT), Image.LANCZOS)
        small.save('_plan/%s_%d.png' % (NAMES[pi], si))
        big[(pi, si)] = (im, small)

FT = 'C:/Windows/Fonts/msyh.ttc'
FB = 'C:/Windows/Fonts/msyhbd.ttc'
f_title = ImageFont.truetype(FB, 27)
f_name = ImageFont.truetype(FB, 23)
f_desc = ImageFont.truetype(FT, 15)
f_state = ImageFont.truetype(FT, 15)
f_small = ImageFont.truetype(FT, 12)
f_tiny = ImageFont.truetype(FT, 11)

TW = 320
W, ROWH, HEAD = 1220, 218, 112
H = HEAD + ROWH * 4 + 22
sheet = Image.new('RGBA', (W, H), (20, 22, 26, 255))
sd = ImageDraw.Draw(sheet)
sd.text((34, 28), '任务总览 · 三态图标方案', font=f_title, fill=(240, 240, 245, 255))
sd.text((34, 68), '卡片 170x42　图标槽 14x14（右下角，与「前置 / 副本内」徽章同高）', font=f_desc, fill=(148, 153, 163, 255))

for pi, (tag, name, desc, fns) in enumerate(PLANS):
    y0 = HEAD + pi * ROWH
    sd.rounded_rectangle([18, y0 + 4, W - 18, y0 + ROWH - 8], radius=10, fill=(27, 29, 34, 255))
    sd.text((40, y0 + 18), tag, font=f_tiny, fill=(125, 130, 140, 255))
    sd.text((40, y0 + 36), name, font=f_name, fill=(236, 239, 246, 255))
    sd.text((40, y0 + 72), desc[0], font=f_desc, fill=(146, 151, 161, 255))
    sd.text((40, y0 + 94), desc[1], font=f_desc, fill=(146, 151, 161, 255))
    for si in range(3):
        cx = TW + si * 292
        im, small = big[(pi, si)]
        sheet.alpha_composite(im.resize((134, 134), Image.LANCZOS), (cx, y0 + 18))
        sd.text((cx + 2, y0 + 160), STATES[si], font=f_state, fill=(205, 210, 220, 255))
        sheet.alpha_composite(small.resize((36, 36), Image.NEAREST), (cx + 70, y0 + 156))
        sd.text((cx + 112, y0 + 164), '实际 14px', font=f_tiny, fill=(118, 123, 133, 255))

sheet.save('_plan/plan_icons.png')
print('ok', sheet.size)
