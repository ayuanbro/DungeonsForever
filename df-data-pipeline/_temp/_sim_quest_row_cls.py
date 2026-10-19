# -*- coding: utf-8 -*-
"""任务行「阵营图标 + 职业小卡片」视觉交付图。

上图：任务行 2x 仿真（尺寸全部取自 Core/DungeonUI.lua 常量）
下图：阵营标识 旧（单字兜底）→ 新（自制品图标）1x / 4x 对照
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
OUT = os.path.join(HERE, '_corner_view', 'quest_row_cls_badge.png')

S = 2
ROW_W, ROW_H, ROW_GAP = 504, 34, 4
X_NAME, W_NAME = 30, 150
BADGE_H, BADGE_FS, BADGE_GAP, BADGE_PAD, BADGE_DY = 14, 12, 4, 3, 2
ICON_S, ICON_X = 18, 12
DIM, LUM = 0.78, 0.62

BG_PANEL = (0x10, 0x13, 0x1A)
BG_CARD = (0x1A, 0x1F, 0x28)
BG_EDGE = (0x3A, 0x42, 0x50)
PRE_BG = (0.78, 0.60, 0.10)
SHARE_BG = (0.16, 0.52, 0.26)
TXT = (0xE8, 0xEC, 0xF2)
DIMTXT = (0x8A, 0x92, 0xA0)

CLASSES = {
    'WARRIOR': (0.78, 0.61, 0.43), 'PALADIN': (0.96, 0.55, 0.73),
    'HUNTER': (0.67, 0.83, 0.45), 'ROGUE': (1.00, 0.96, 0.41),
    'PRIEST': (1.00, 1.00, 1.00), 'SHAMAN': (0.00, 0.44, 0.87),
    'MAGE': (0.41, 0.80, 0.94), 'WARLOCK': (0.58, 0.51, 0.79),
    'DRUID': (1.00, 0.49, 0.04),
}
LABEL = {'WARRIOR': '战士', 'PALADIN': '骑士', 'HUNTER': '猎人', 'ROGUE': '盗贼',
         'PRIEST': '牧师', 'SHAMAN': '萨满', 'MAGE': '法师', 'WARLOCK': '术士',
         'DRUID': '德鲁伊'}
F = lambda px, bd=False: ImageFont.truetype(
    r'C:\Windows\Fonts\msyhbd.ttc' if bd else r'C:\Windows\Fonts\msyh.ttc', px * S)


def cls_fill(tok):
    r, g, b = CLASSES[tok]
    avg = (r + g + b) / 3
    k = DIM
    if avg > 0 and avg * k > LUM:
        k = LUM / avg
    return tuple(int(round(v * k * 255)) for v in (r, g, b))


def rgb(c):
    return tuple(int(round(v * 255)) for v in c)


def rr(d, box, rad, fill, outline=None, width=1):
    d.rounded_rectangle(box, radius=rad * S, fill=fill, outline=outline, width=width * S)


def load(path, size):
    im = Image.open(path).convert('RGBA')
    return im.resize((size * S, size * S), Image.LANCZOS)


ALLI = load(os.path.join(DF, 'Media', 'icon', 'FACTION', 'FactionIcon_Alliance.tga'), ICON_S)
HORD = load(os.path.join(DF, 'Media', 'icon', 'FACTION', 'FactionIcon_Horde.tga'), ICON_S)
ALLI_BIG = load(os.path.join(DF, 'Media', 'icon', 'FACTION', 'FactionIcon_Alliance.tga'), ICON_S * 4)
HORD_BIG = load(os.path.join(DF, 'Media', 'icon', 'FACTION', 'FactionIcon_Horde.tga'), ICON_S * 4)

ROWS = [
    ('通缉：霍格与他的八个同伙', 'A', [], True, True, False),
    ('正义试炼', 'A', ['PALADIN'], True, False, True),
    ('索兰鲁克宝珠', None, ['WARLOCK'], False, True, False),
    ('尘泥沼泽的暗影', 'H', ['PRIEST'], True, False, False),
    ('野性之心', 'H', ['DRUID'], False, False, False),
    ('双职业任务示例', None, ['PALADIN', 'WARLOCK'], True, True, False),
]
PAD = 8
HEADER = 34
R1_H = PAD + len(ROWS) * (ROW_H + ROW_GAP) - ROW_GAP + PAD
R2_H = 104
CAP_H = 34
W = ROW_W + PAD * 6
H = HEADER + R1_H + 12 + R2_H + CAP_H

img = Image.new('RGB', (W * S, H * S), BG_PANEL)
d = ImageDraw.Draw(img)
d.text((PAD * S, 16 * S), '任务行：阵营图标 + 职业色小卡片', font=F(16, True), fill=TXT, anchor='lm')
d.text((W * S - PAD * S, 16 * S), '2x 仿真 · 尺寸取自源码常量', font=F(12), fill=DIMTXT, anchor='rm')

# ---- 面板 1：任务行 ----
top = HEADER
rr(d, (PAD * S, top * S, (W - PAD) * S, (top + R1_H) * S), 8,
   tuple(int(v * 0.72) for v in BG_PANEL), (0x24, 0x2A, 0x34), 1)
y = top + PAD
for nm, side, cl, pre, share, sel in ROWS:
    rr(d, ((PAD + 0) * S, y * S, (PAD + ROW_W) * S, (y + ROW_H) * S), 6, BG_CARD, BG_EDGE, 1)
    if sel:
        d.rounded_rectangle(((PAD) * S - 1, y * S - 1, (PAD + ROW_W) * S + 1,
                             (y + ROW_H) * S + 1), radius=6 * S,
                            outline=rgb((1, 0.82, 0)), width=1 * S)
    if side:
        ic = ALLI if side == 'A' else HORD
        img.paste(ic, (int((PAD + ICON_X) * S), int((y + (ROW_H - ICON_S) / 2) * S)), ic)
    d.text(((PAD + X_NAME) * S, (y + ROW_H / 2) * S), nm, font=F(14), fill=TXT, anchor='lm',
           stroke_width=1, stroke_fill=(0, 0, 0))
    x = PAD + X_NAME + d.textlength(nm, font=F(14)) / S + BADGE_GAP
    for tok in cl + ['__pre__' if pre else None, '__share__' if share else None]:
        if tok is None:
            continue
        if tok == '__pre__':
            lab, col = '前置', rgb(PRE_BG)
        elif tok == '__share__':
            lab, col = '可共享', rgb(SHARE_BG)
        else:
            lab, col = LABEL[tok], cls_fill(tok)
        bw = d.textlength(lab, font=F(BADGE_FS)) / S + BADGE_PAD * 2
        rr(d, (x * S, (y + (ROW_H - BADGE_H) / 2 - BADGE_DY) * S,
               (x + bw) * S, (y + (ROW_H + BADGE_H) / 2 - BADGE_DY) * S), 4, col)
        d.text(((x + bw / 2) * S, (y + ROW_H / 2 - BADGE_DY) * S), lab, font=F(BADGE_FS),
               fill=(255, 255, 255), anchor='mm', stroke_width=1, stroke_fill=(0, 0, 0))
        x += bw + BADGE_GAP
    d.text(((PAD + ROW_W - 6) * S, (y + ROW_H / 2) * S), '未完成', font=F(12), fill=DIMTXT,
           anchor='rm')
    y += ROW_H + ROW_GAP

# ---- 面板 2：阵营标识对照 ----
top2 = HEADER + R1_H + 12
rr(d, (PAD * S, top2 * S, (W - PAD) * S, (top2 + R2_H) * S), 8,
   tuple(int(v * 0.72) for v in BG_PANEL), (0x24, 0x2A, 0x34), 1)
d.text(((PAD + 10) * S, (top2 + 10) * S), '阵营标识：旧单字兜底 → 自制品图标', font=F(13),
       fill=TXT, anchor='lm')
cy = top2 + 62
# 旧
d.text(((PAD + 10) * S, cy * S), '旧', font=F(12), fill=DIMTXT, anchor='lm')
for i, (lab, col) in enumerate((('盟', (0.45, 0.65, 1)), ('部', (1, 0.40, 0.40)))):
    d.text(((PAD + 42 + i * 26) * S, cy * S), lab, font=F(14), fill=rgb(col), anchor='mm',
           stroke_width=1, stroke_fill=(0, 0, 0))
d.text(((PAD + 10) * S, (cy + 26) * S), '12px 彩字兜底（已退役）', font=F(11), fill=DIMTXT, anchor='lm')
# 新（18px）
d.text(((PAD + 150) * S, cy * S), '新', font=F(12), fill=DIMTXT, anchor='lm')
for i, ic in enumerate((ALLI, HORD)):
    img.paste(ic, (int((PAD + 182 + i * 26) * S), int((cy - ICON_S / 2) * S)), ic)
d.text(((PAD + 150) * S, (cy + 26) * S), '18px 自制品图标（行内实际大小）', font=F(11),
       fill=DIMTXT, anchor='lm')
# 新（4x）
for i, ic in enumerate((ALLI_BIG, HORD_BIG)):
    img.paste(ic, (int((PAD + 400 + i * (ICON_S * 4 + 10)) * S), int((cy - ICON_S * 2) * S)), ic)
d.text(((PAD + 400) * S, (cy + 26) * S), '4x 放大', font=F(11), fill=DIMTXT, anchor='lm')

d.text((PAD * S, (H - 24) * S),
       '行高 34 · 卡高 %d / 字号 %d / 枚距 %d / 内衬 %d / 垂直补偿 %d'
       % (BADGE_H, BADGE_FS, BADGE_GAP, BADGE_PAD, BADGE_DY),
       font=F(11), fill=DIMTXT, anchor='lm')
d.text((PAD * S, (H - 9) * S),
       '职业色 × %.2f（均亮超 %.2f 封顶：牧师纯白 → 中灰底）· 徽章链：职业卡 → 前置 → 可共享'
       % (DIM, LUM),
       font=F(11), fill=DIMTXT, anchor='lm')

img.save(OUT)
print('wrote', OUT, img.size)
