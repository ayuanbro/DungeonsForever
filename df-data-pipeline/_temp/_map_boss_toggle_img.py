# -*- coding: utf-8 -*-
"""地图页「隐藏 boss」开关 版式示意图（2026-10-01 交付）。

产物 _temp/MAP_BOSS_TOGGLE.png：两张并列面板 —— ① 默认（钉点在地图上）
② 点开关后（钉点全收、开关转金、右栏列表照旧）。几何全部按源码常量缩放复算：
  FRAME_W=936 / FRAME_H=442 / MAP_W=663 / SIDE_W=263 / SIDE_GAP=10
  BAR_H=20 / LAYER_W=46 / LAYER_GAP=4 / FLOOR_INSET=6 / BOSS_BTN_W=72
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    r"C:/Users/Administrator/AppData/Local/Microsoft/Windows/Fonts/方正小标宋简体.TTF",
    r"C:/Windows/Fonts/Noto Sans SC Bold (TrueType).otf",
    r"C:/Windows/Fonts/simhei.ttf",
]
FONT = next(p for p in FONT_CANDIDATES if os.path.exists(p) and os.path.getsize(p) > 1000)

S = 0.85                                   # 缩放（源码 px → 图 px）
FRAME_W, FRAME_H = round(936 * S), round(442 * S)
MAP_W, SIDE_W, SIDE_GAP = round(663 * S), round(263 * S), round(10 * S)
BAR_H, LAYER_W, LAYER_GAP, INSET = round(20 * S), round(46 * S), round(4 * S), round(6 * S)
BOSS_BTN_W = round(72 * S)

PAD, GAPX = 30, 34
TITLE_H, FOOT_H = 64, 86
PANEL_W, PANEL_H = FRAME_W, FRAME_H
W = PAD * 2 + PANEL_W * 2 + GAPX
H = PAD + TITLE_H + PANEL_H + FOOT_H

BG = (24, 22, 20)
PANEL = (16, 15, 14)
CANVAS = (30, 36, 40)
GRID = (44, 52, 56)
SIDE = (32, 34, 36)
ROW = (40, 43, 46)
GOLD = (255, 209, 0)
GREY = (140, 140, 140)
TEXT = (224, 224, 224)
WHITE = (245, 245, 245)

PALETTE = [(240, 77, 71), (255, 148, 48), (255, 209, 0), (107, 224, 87)]

fb = ImageFont.truetype(FONT, 21)
ft = ImageFont.truetype(FONT, 15)
fs = ImageFont.truetype(FONT, 12)
fx = ImageFont.truetype(FONT, 11)

canvas = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(canvas)


def skull(dr, cx, cy, r, color):
    """骷髅钉点：一个圆 + 两只眼（示意，非真实贴图）。"""
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    eye = max(1, round(r * 0.28))
    for dx in (-round(r * 0.34), round(r * 0.34)):
        dr.ellipse([cx + dx - eye, cy - r * 0.18 - eye, cx + dx + eye, cy - r * 0.18 + eye], fill=(25, 25, 25))


def panel(px, py, hidden):
    d.rounded_rectangle([px - 4, py - 4, px + FRAME_W + 4, py + FRAME_H + 4], 7, fill=PANEL)

    # ── 地图区（左）──
    d.rectangle([px, py, px + MAP_W, py + MAP_H], fill=CANVAS)
    for i in range(1, 4):
        x = px + MAP_W * i / 4
        d.line([x, py, x, py + MAP_H], fill=GRID, width=1)
    for i in range(1, 3):
        y = py + MAP_H * i / 3
        d.line([px, y, px + MAP_W, y], fill=GRID, width=1)

    # 钉点（带名字）—— 隐藏态则整片不画
    if not hidden:
        pts = [(0.22, 0.30), (0.53, 0.23), (0.33, 0.67), (0.71, 0.60)]
        for i, (rx, ry) in enumerate(pts):
            cx, cy = px + MAP_W * rx, py + MAP_H * ry
            skull(d, cx, cy, round(9 * S) + 3, PALETTE[i % 4])
            nm = "首领 %d" % (i + 1)
            tw = d.textlength(nm, font=fs)
            d.text((cx - tw / 2, cy + round(11 * S) + 6), nm, font=fs, fill=PALETTE[i % 4])
    else:
        tw = d.textlength("地图上已无 boss 钉点", font=ft)
        d.text((px + (MAP_W - tw) / 2, py + MAP_H / 2 - 10), "地图上已无 boss 钉点", font=ft, fill=GREY)

    # ── 右上角：楼层按钮条（B 方案，悬浮）──
    n = 2
    for i in range(n):
        bw, bh = LAYER_W, BAR_H
        bx = px + MAP_W - INSET - (n - i) * (bw + LAYER_GAP) + LAYER_GAP
        by = py + INSET
        sel = (i == 0)
        d.rectangle([bx, by, bx + bw, by + bh], fill=(38, 34, 20) if sel else (34, 34, 34))
        d.rectangle([bx, by, bx + bw, by + bh], outline=GOLD if sel else GREY, width=1)
        lab = "第 %d 层" % (i + 1)
        tw = d.textlength(lab, font=fx)
        d.text((bx + (bw - tw) / 2, by + (bh - 15) / 2), lab, font=fx, fill=GOLD if sel else GREY)

    # ── 左上角：隐藏 boss 开关（本次新增）──
    bx, by = px + INSET, py + INSET
    d.rectangle([bx - 3, by - 3, bx + BOSS_BTN_W + 3, by + BAR_H + 3], outline=(90, 90, 90), width=1)
    d.rectangle([bx, by, bx + BOSS_BTN_W, by + BAR_H], fill=(44, 38, 16) if hidden else (34, 34, 34))
    d.rectangle([bx, by, bx + BOSS_BTN_W, by + BAR_H], outline=GOLD if hidden else GREY, width=1)
    lab = "显示boss" if hidden else "隐藏boss"
    tw = d.textlength(lab, font=fx)
    d.text((bx + (BOSS_BTN_W - tw) / 2, by + (BAR_H - 15) / 2), lab, font=fx,
           fill=GOLD if hidden else GREY)

    # ── 右栏（首领列表，两态都不变）──
    sx = px + FRAME_W - SIDE_W
    d.rounded_rectangle([sx, py, sx + SIDE_W, py + FRAME_H], 5, fill=SIDE)
    d.text((sx + 8, py + 8), "首领", font=ft, fill=GOLD)
    rh, rg = round(38 * S), round(8 * S)
    y = py + round(32 * S) + 8
    for i in range(4):
        d.rounded_rectangle([sx + 7, y, sx + SIDE_W - 7, y + rh], 5,
                            fill=ROW, outline=PALETTE[i % 4], width=1)
        cx, cy = sx + 7 + round(6 * S) + round(16 * S), y + rh / 2
        skull(d, cx, cy, round(16 * S) * 0.8, PALETTE[i % 4])
        d.text((cx + round(20 * S), cy - 8), "首领 %d" % (i + 1), font=ft, fill=TEXT)
        y += rh + rg


MAP_H = FRAME_H

# 面板 ① 默认
p1x, p1y = PAD, PAD + TITLE_H
panel(p1x, p1y, hidden=False)
d.text((PAD, PAD + 12), "① 默认：地图上有 boss 钉点（带名字）", font=fb, fill=WHITE)
d.text((PAD, PAD + 36), "左上角开关 = 灰边「隐藏boss」", font=ft, fill=GREY)

# 面板 ② 已隐藏
p2x = PAD + PANEL_W + GAPX
panel(p2x, p1y, hidden=True)
d.text((p2x, PAD + 12), "② 点开关后：钉点全收，开关转金「显示boss」", font=fb, fill=GOLD)
d.text((p2x, PAD + 36), "右栏首领列表 / 详情不受影响（只藏地图上的按钮）", font=ft, fill=GREY)

# 图注
fy = PAD + TITLE_H + PANEL_H + 14
d.text((PAD, fy), "几何按源码常量复算：左上/右上同一组边距 FLOOR_INSET=6、同一高度 BAR_H=20；"
                  "开关宽 BOSS_BTN_W=72；状态存 DungeonsForeverDB.dungeon.mapBossHidden",
       font=ft, fill=GREY)
d.text((PAD, fy + 22), "无钉点的副本（如挖掘场湿地）开关整颗不出现 —— 判据 HasPins(副本)，与当前层、与隐藏状态都无关",
       font=ft, fill=GREY)

out = os.path.join(HERE, "MAP_BOSS_TOGGLE.png")
canvas.save(out)
print("→", out, canvas.size, "font =", os.path.basename(FONT))
