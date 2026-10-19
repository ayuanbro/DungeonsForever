# -*- coding: utf-8 -*-
"""挖掘场湿地：把用户截图里标的 1/2/3/4 换算成插件实际渲染的钉点，出对照校验图。

左 = 用户原始标注；右 = 同区域按插件真实几何画出的钉点（身份色圆点 + 下方 boss 名）
      以及左上角「隐藏 boss」开关（本副本单层 ⇒ 右上角没有楼层按钮）。
所有几何都按源码常量 × 截图倍率换算，不凭感觉画。
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = r'C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-02T21-53-47-280Z-91743acf.jpg'

FONT_CANDIDATES = [
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/msyh.ttc',
]
FONT = next(p for p in FONT_CANDIDATES if os.path.exists(p) and os.path.getsize(p) > 1000)

# 插件源码常量（Core/MapUI.lua）
PIN_MIN = 27          # 未选中钉点直径（game px）
BOSSBAR_W, BOSSBAR_H, INSET = 72, 20, 6   # 「隐藏 boss」开关尺寸 / 距左上角边距
CANVAS_W = 663        # 游戏内画布宽（game px）

# 身份色（M.BOSS_PALETTE 前四位）
PALETTE = [(0.94, 0.30, 0.28), (1.00, 0.58, 0.19), (1.00, 0.82, 0.00), (0.42, 0.88, 0.34)]
BOSSES = [
    ('1', 'Saltspine',       '盐脊',       62.0, 47.1),
    ('2', 'Shadetooth',      '暗齿',       40.6, 53.6),
    ('3', 'Highland Horror', '高地惊魂',   26.3, 56.2),
    ('4', 'Relic Guardian',  '遗物守护者', 46.6, 74.1),
]

BG = (16, 17, 20)
CARD = (26, 28, 33)
GOLD = (240, 200, 96)
WHITE = (238, 238, 240)
DIM = (150, 154, 162)


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def rgb(c):
    return tuple(int(round(v * 255)) for v in c)


def main():
    L, T, W, H = [float(v) for v in np.load(os.path.join(HERE, '_regist.npy'))]
    scale = W / CANVAS_W          # 截图 px / game px

    shot = Image.open(SHOT).convert('RGB')
    crop = shot.crop((int(L), int(T), int(L + W), int(T + H)))

    CW, CH = int(W), int(H)
    sw = int(BOSSBAR_W * scale)
    sh = int(BOSSBAR_H * scale)
    inset = int(INSET * scale)
    pd = int(PIN_MIN * scale)

    # 右panel：画插件实际渲染结果
    right = crop.copy()
    d = ImageDraw.Draw(right)
    # 左上角「隐藏 boss」开关（灰边未点亮，文案「隐藏boss」）
    d.rectangle([inset, inset, inset + sw, inset + sh], fill=(22, 22, 24), outline=(120, 120, 126), width=2)
    tf = fnt(int(sh * 0.62))
    lab = '隐藏boss'
    bb = d.textbbox((0, 0), lab, font=tf)
    d.text((inset + (sw - (bb[2] - bb[0])) / 2 - bb[0],
            inset + (sh - (bb[3] - bb[1])) / 2 - bb[1]), lab, font=tf, fill=(196, 198, 204))

    nf = fnt(max(14, int(14 * scale * 0.86)))
    for i, (num, en, zh, x, y) in enumerate(BOSSES):
        px, py = x / 100 * CW, y / 100 * CH
        col = rgb(PALETTE[i])
        r = pd / 2
        d.ellipse([px - r, py - r, px + r, py + r], fill=col, outline=(20, 20, 20), width=2)
        # 名字常驻在钉点正下方
        bb = d.textbbox((0, 0), zh, font=nf)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        tx, ty = px - tw / 2 - bb[0], py + r + 2 - bb[1]
        d.rectangle([tx - 3, ty - 1, tx + tw + 3, ty + th + 1], fill=(0, 0, 0))
        d.text((tx, ty), zh, font=nf, fill=col)

    # 版面
    PAD, GAPX = 26, 30
    HEAD = 130
    FOOT_H = 250
    Wtot = PAD * 2 + CW * 2 + GAPX
    Htot = HEAD + CH + FOOT_H
    im = Image.new('RGB', (Wtot, Htot), BG)
    dr = ImageDraw.Draw(im)

    dr.text((PAD, 20), '挖掘场：湿地 · 四个 boss 钉点落到你标的 1/2/3/4 上（2026-10-03）',
            font=fnt(25), fill=GOLD)
    dr.text((PAD, 58), '左：你的标注（1/2/3/4）　右：插件实际渲染（身份色圆点 + 名字在钉点正下方；'
                       '本副本单层 ⇒ 右上角没有楼层按钮，左上角是新加的「隐藏 boss」开关）',
            font=fnt(14), fill=WHITE)

    for i, (lab_txt, img) in enumerate((('你的标注（1/2/3/4）', crop), ('插件渲染（钉点 = 你标的点）', right))):
        x = PAD + i * (CW + GAPX)
        dr.rectangle([x - 2, HEAD - 2, x + CW + 2, HEAD + CH + 2], outline=(70, 72, 78), width=2)
        im.paste(img, (x, HEAD))
        dr.text((x + 4, HEAD - 26), lab_txt, font=fnt(15), fill=GOLD if i == 0 else rgb(PALETTE[3]))

    # 页脚：坐标与口径
    y = HEAD + CH + 16
    dr.text((PAD, y), '落库坐标（相对画布 663×442 的百分比，左上原点 → ns.BossPos["excavation_wetlands"]）：',
            font=fnt(15), fill=WHITE)
    y += 26
    for i, (num, en, zh, x, y2) in enumerate(BOSSES):
        col = rgb(PALETTE[i])
        dr.text((PAD + 6, y), '%s  %-16s %-6s  left = %.1f%%   top = %.1f%%' % (num, en, zh, x, y2),
                font=fnt(15), fill=col)
        y += 24
    y += 6
    for txt in (
        '★ 反解方式：把你的截图与自制 TGA 素材（ExcavationSite.tga 顶部 341 行）做归一化互相关配准 —— '
        '得分 0.9637、解出宽高比 1.5013 ≈ 素材 1.5015（说明游戏里是等比铺满，没有拉伸）。',
        '★ 画布在截图里 = (60, 428) 起、1198×798 px（含合成自检：模板贴已知位置能 1:1 找回）。',
        '★ 顺序咬死：钉点顺序 = 右栏首领名单顺序 = 掉落表顺序 = 你标的 1 盐脊 / 2 暗齿 / 3 高地惊魂 / 4 遗物守护者。',
    ):
        dr.text((PAD, y), txt, font=fnt(13), fill=DIM)
        y += 22

    out = os.path.join(HERE, 'SITE_PINS_PREVIEW.png')
    im.save(out)
    print('ok', out, im.size)


if __name__ == '__main__':
    main()
