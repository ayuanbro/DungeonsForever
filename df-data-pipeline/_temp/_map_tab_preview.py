# -*- coding: utf-8 -*-
"""把「详情页地图页签」的最终版式按代码里的真实常量渲染成一张预览图。

数据来源：_mapprobe_png/ragefire/ragefire_01..12.png（实机从客户端导出的 12 块瓦片）
几何来源：Core/MapUI.lua 的常量 + Core/DungeonUI.lua 的 detail / 页签落点
（不是凭空画的：ART_W/H=1002/668、COLS/ROWS=4/3、TILE=256、FitBox 居中、
  页签右起 x = -8-(i-1)*76、页签行 y = -(HERO_META_Y-12)、地图区顶 = HERO_H+8）
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_mapprobe_png", "ragefire")
OUT = os.path.join(HERE, "MAP_TAB_PREVIEW.png")

FONT = "C:/Windows/Fonts/msyh.ttc"

COLS, ROWS, TILE = 4, 3, 256
ART_W, ART_H = 1002, 668
DETAIL_W, DETAIL_H = 936, 630
HERO_H, HERO_META_Y = 120, 104
TAB_W, TAB_H, TAB_GAP = 70, 24, 6
TABS = [("掉落", False), ("任务", False), ("攻略", False), ("地图", True)]

BG = (16, 20, 24)
PANEL = (36, 36, 38)
HERO = (58, 62, 70)
TAB_OFF = (44, 46, 52)
TAB_ON = (96, 78, 22)
GOLD = (255, 209, 0)
GREY = (170, 170, 170)
WHITE = (240, 240, 240)


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def build_map_panel():
    """按 Core/MapUI.lua 的 Layout 逻辑拼出最终上屏的 752x502 画面。"""
    canvas = Image.new("RGB", (COLS * TILE, ROWS * TILE), (0, 0, 0))
    for n in range(1, COLS * ROWS + 1):
        f = os.path.join(SRC, "ragefire_%02d.png" % n)
        if not os.path.exists(f):
            continue
        col, row = (n - 1) % COLS, (n - 1) // COLS
        canvas.paste(Image.open(f).convert("RGB"), (col * TILE, row * TILE))
    # 有效画面 = 左上 1002x668（右侧 22 / 底部 100 是装饰边）
    canvas = canvas.crop((0, 0, ART_W, ART_H))
    # 等比适应到 936x502 的可用区（高受限）
    s = min(DETAIL_W / ART_W, (DETAIL_H - (HERO_H + 8)) / ART_H)
    w, h = int(ART_W * s), int(ART_H * s)
    return canvas.resize((w, h), Image.LANCZOS), w, h


def main():
    mp, mw, mh = build_map_panel()
    avail_h = DETAIL_H - (HERO_H + 8)
    ox = int((DETAIL_W - mw) / 2)
    oy = HERO_H + 8 + int((avail_h - mh) / 2)

    PAD_L, PAD_T = 72, 84
    W = DETAIL_W + PAD_L * 2
    H = DETAIL_H + PAD_T + 96
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    dx, dy = PAD_L, PAD_T
    d.rectangle([dx, dy, dx + DETAIL_W, dy + DETAIL_H], fill=PANEL, outline=(90, 92, 100))

    # hero 横幅
    d.rectangle([dx + 1, dy + 1, dx + DETAIL_W - 1, dy + HERO_H], fill=HERO)
    d.text((dx + 12, dy + 84 - 26), "怒焰裂谷", font=fnt(16), fill=WHITE)
    d.text((dx + 12, dy + HERO_META_Y - 20), "13-18 级 · 奥格瑞玛 · BOSS 4",
           font=fnt(13), fill=GREY)
    d.text((dx + 8, dy + 8), "‹ 副本", font=fnt(14), fill=GREY)

    # 详情页签（右起排布：i=1 最右）
    ty = dy + (HERO_META_Y - 12)
    for i, (name, on) in enumerate(TABS, start=1):
        rx = dx + DETAIL_W - 8 - (i - 1) * (TAB_W + TAB_GAP)
        lx = rx - TAB_W
        d.rectangle([lx, ty, rx, ty + TAB_H], fill=TAB_ON if on else TAB_OFF,
                    outline=GOLD if on else (110, 112, 120))
        tw = d.textlength(name, font=fnt(14))
        d.text((lx + (TAB_W - tw) / 2, ty + 3), name, font=fnt(14),
               fill=GOLD if on else GREY)

    # 地图画面（等比适应后居中）
    im.paste(mp, (dx + ox, dy + oy))
    d.rectangle([dx + ox - 1, dy + oy - 1, dx + ox + mw, dy + oy + mh],
                outline=(120, 122, 130))

    cap = ("详情页 · 第四颗页签「地图」（最左）｜可用区 936×502，"
           "画面等比适应 %d×%d 居中（左右各留 %d）" % (mw, mh, ox))
    d.text((PAD_L, dy + DETAIL_H + 18), cap, font=fnt(14), fill=GOLD)
    d.text((PAD_L, dy + DETAIL_H + 42),
           "27 个副本走这张真实副本地图；其余 8 个（含旧铁炉堡这类区域图）走空态文案，不给区域图顶替。",
           font=fnt(13), fill=GREY)
    d.text((PAD_L, dy + DETAIL_H + 64),
           "瓦片 = 客户端 Interface\\WorldMap\\Ragefire\\Ragefire1_1..12（实机 12/12 命中），只取第 1 层。",
           font=fnt(13), fill=(120, 122, 130))

    im.save(OUT)
    print("ok", OUT, im.size, "map=%dx%d offset=%d,%d" % (mw, mh, ox, oy))


if __name__ == "__main__":
    main()
