# -*- coding: utf-8 -*-
"""多层副本「楼层」按钮 · 版式预览（按 Core/MapUI.lua 的真实常量渲染）。

几何来源：MapUI.lua 的 COLS/ROWS/TILE、ART_W/H=1002/668、FitBox、MAX_LAYERS=8、
          LAYER_W=56、LAYER_GAP=6、BAR_H=30；DungeonUI.lua 的 detail / 页签落点。
素材：_temp/_mapcheck/scholomanceold__scholomanceold{1..4}_.png（实机导出的 12 块拼接图）
出图：MAP_FLOOR_PREVIEW.png —— 左「默认第 1 层」/ 右「点第 3 层后」，各带真实按钮条。
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_mapcheck")
OUT = os.path.join(HERE, "MAP_FLOOR_PREVIEW.png")
FONT = "C:/Windows/Fonts/msyh.ttc"

COLS, ROWS, TILE = 4, 3, 256
ART_W, ART_H = 1002, 668
DETAIL_W, DETAIL_H = 936, 630
HERO_H, HERO_META_Y, GUIDE_TOP_Y = 120, 104, 128
TAB_W, TAB_H, TAB_GAP = 70, 24, 6
LAYER_W, LAYER_GAP, BAR_H, BAR_BTN_H = 56, 6, 30, 22

BG = (16, 20, 24)
PANEL = (36, 36, 38)
HERO = (58, 62, 70)
TAB_OFF = (44, 46, 52)
TAB_ON = (96, 78, 22)
BTN_OFF = (40, 42, 48)
BTN_ON = (78, 62, 16)
GOLD = (255, 209, 0)
GREY = (170, 170, 170)
DIM = (120, 122, 130)
WHITE = (240, 240, 240)


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def layer_art(idx):
    """通灵学院第 idx 层的上屏画面（按 FitBox 等比适应到可用区）。"""
    p = os.path.join(SRC, "scholomanceold__scholomanceold%d_.png" % idx)
    canvas = Image.open(p).convert("RGB")
    # 拼接图已按 4x3 拼好；保险起见裁到有效画面
    canvas = canvas.crop((0, 0, min(canvas.width, ART_W), min(canvas.height, ART_H)))
    avail_h = (DETAIL_H - GUIDE_TOP_Y) - BAR_H
    s = min(DETAIL_W / ART_W, avail_h / ART_H)
    w, h = int(ART_W * s), int(ART_H * s)
    return canvas.resize((w, h), Image.LANCZOS), w, h


def draw_detail(im, d, dx, dy, cur, nlayers, title):
    """一个详情页 mock；cur = 当前层（1 基）。"""
    d.rectangle([dx, dy, dx + DETAIL_W, dy + DETAIL_H], fill=PANEL, outline=(90, 92, 100))
    d.rectangle([dx + 1, dy + 1, dx + DETAIL_W - 1, dy + HERO_H], fill=HERO)
    d.text((dx + 12, dy + 84 - 26), title, font=fnt(16), fill=WHITE)
    d.text((dx + 12, dy + HERO_META_Y - 20), "38-48 级 · 西瘟疫之地 · BOSS 6", font=fnt(13), fill=GREY)
    d.text((dx + 8, dy + 8), "‹ 副本", font=fnt(14), fill=GREY)

    for i, name in enumerate(["掉落", "任务", "攻略", "地图"], start=1):
        rx = dx + DETAIL_W - 8 - (i - 1) * (TAB_W + TAB_GAP)
        lx = rx - TAB_W
        on = (name == "地图")
        ty = dy + (HERO_META_Y - 12)
        d.rectangle([lx, ty, rx, ty + TAB_H], fill=TAB_ON if on else TAB_OFF,
                    outline=GOLD if on else (110, 112, 120))
        tw = d.textlength(name, font=fnt(14))
        d.text((lx + (TAB_W - tw) / 2, ty + 3), name, font=fnt(14), fill=GOLD if on else GREY)

    mp, mw, mh = layer_art(cur)
    avail_h = (DETAIL_H - GUIDE_TOP_Y) - BAR_H
    ox = int((DETAIL_W - mw) / 2)
    oy = GUIDE_TOP_Y + int((avail_h - mh) / 2)
    im.paste(mp, (dx + ox, dy + oy))
    d.rectangle([dx + ox - 1, dy + oy - 1, dx + ox + mw, dy + oy + mh], outline=(120, 122, 130))

    # 楼层按钮条：bar 高 22、贴 frame 底
    by = dy + DETAIL_H - BAR_BTN_H
    total = nlayers * LAYER_W + (nlayers - 1) * LAYER_GAP
    x0 = dx + (DETAIL_W - total) / 2
    for i in range(1, nlayers + 1):
        lx = x0 + (i - 1) * (LAYER_W + LAYER_GAP)
        sel = (i == cur)
        d.rectangle([lx, by, lx + LAYER_W, by + BAR_BTN_H],
                    fill=BTN_ON if sel else BTN_OFF,
                    outline=GOLD if sel else (120, 122, 130), width=2 if sel else 1)
        t = "第 %d 层" % i
        tw = d.textlength(t, font=fnt(13))
        d.text((lx + (LAYER_W - tw) / 2, by + 4), t, font=fnt(13),
               fill=GOLD if sel else GREY)


def main():
    PAD_L, PAD_T, GAPX = 48, 92, 56
    W = PAD_L * 2 + DETAIL_W * 2 + GAPX
    H = PAD_T + DETAIL_H + 118
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    d.text((PAD_L, 22), "详情页 ·「地图」页签 · 多层副本的楼层切换（通灵学院 ScholomanceOld · 客户端里就画了 4 层）",
           font=fnt(19), fill=GOLD)
    d.text((PAD_L, 54), "下方一排「第 N 层」按钮：层数 >1 才出现；点一下换图；选中按钮金字金边、其余灰字灰边。",
           font=fnt(14), fill=GREY)

    draw_detail(im, d, PAD_L, PAD_T, 1, 4, "通灵学院")
    draw_detail(im, d, PAD_L + DETAIL_W + GAPX, PAD_T, 3, 4, "通灵学院")

    capy = PAD_T + DETAIL_H + 16
    d.text((PAD_L, capy), "① 进入副本默认画第 1 层（＝加楼层功能之前的那张图，观感不回归）",
           font=fnt(14), fill=WHITE)
    d.text((PAD_L + DETAIL_W + GAPX, capy), "② 点「第 3 层」→ 12 块瓦片整幅换成 ScholomanceOld3_，按钮选中态跟着走",
           font=fnt(14), fill=WHITE)
    d.text((PAD_L, capy + 30),
           "几何按 Core/MapUI.lua 真实常量：可用 936×502 − 楼层条 30 = 472 高 ⇒ FitBox 等比 708×472 居中（左右各 114）；"
           "按钮 56×22、间距 6、居中排布。帧只在 Build 建一次，切层零新建帧。",
           font=fnt(12), fill=DIM)

    im.save(OUT)
    print("ok", OUT, im.size)


if __name__ == "__main__":
    main()
