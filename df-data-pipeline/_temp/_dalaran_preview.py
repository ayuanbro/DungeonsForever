# -*- coding: utf-8 -*-
"""达拉然城「地图」页两层对照示意图（2026-10-02 用户重绘第 1 层）。

左 = 第 1 层（自制手绘图顶掉客户端 Dalaran1_），右 = 第 2 层（下水道，仍走客户端瓦片）。
两块都按**插件里的真实几何**画：地图画布 663×442、楼层按钮贴右上角内 6px
（LAYER_W=56 / BAR_H=20 / GAP=6，选中金描边）。产物 _temp/DALARAN_MAP_LAYERS.png
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

# 插件真常量（Core/MapUI.lua）
CW, CH = 663, 442          # 地图画布（与客户端瓦片同一块）
INSET = 6                  # FLOOR_INSET
LW, LH, LG = 56, 20, 6     # LAYER_W / BAR_H / LAYER_GAP

BG = (24, 22, 20)
PANEL_BD = (120, 122, 130)
GOLD = (255, 209, 0)
GREY = (168, 168, 168)
WHITE = (240, 238, 232)
DIM = (188, 184, 176)
GREEN = (107, 224, 87)


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def wrap(d, txt, font, maxw):
    """按像素宽度折行（中文无空格，只能逐字试）。"""
    lines, cur = [], ""
    for ch in txt:
        if d.textlength(cur + ch, font=font) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def panel(im, d, x, y, img, badge, sub, cur):
    art = img.resize((CW, CH), Image.LANCZOS)
    im.paste(art, (x, y))
    d.rectangle([x - 1, y - 1, x + CW, y + CH], outline=PANEL_BD)
    # 楼层按钮条（右上角内 6px，两颗）—— ★ 与插件同序：末层贴最右，往前层往左排
    #   （SyncBar：SetPoint("TOPRIGHT", bar, "TOPRIGHT", -((n - i) * (W + GAP)), 0)）
    bx = x + CW - INSET
    for i in (2, 1):
        bw = LW
        left = bx - bw
        top = y + INSET
        sel = (i == cur)
        d.rectangle([left, top, left + bw, top + LH],
                    fill=(60, 54, 44) if sel else (44, 42, 40),
                    outline=GOLD if sel else (96, 94, 92))
        lab = "第 %d 层" % i
        f = fnt(12)
        tw = d.textlength(lab, font=f)
        d.text((left + (bw - tw) / 2, top + (LH - 15) / 2), lab, font=f,
               fill=GOLD if sel else GREY)
        bx = left - LG
    # 标题徽标 + 副标题
    f = fnt(19)
    d.text((x, y - 30), badge, font=f, fill=GOLD)
    d.text((x, y + CH + 10), sub, font=fnt(13), fill=DIM)


def main():
    draw_src = Image.open("C:/Users/Administrator/Desktop/无限副本手册/达拉然\u200b.png").convert("RGB")
    cli = Image.open(os.path.join(HERE, "_dalaran_dalaran2_.png")).convert("RGB")
    cli = cli.crop((0, 0, 1002, 668))          # 有效画面（右侧 22 / 底部 100 是装饰边）

    PAD, GAPX = 44, 60
    W = PAD * 2 + CW * 2 + GAPX
    H = 900
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    hf, sf = fnt(24), fnt(14)
    d.text((PAD, 30), "达拉然城 · 「地图」页两层 = 自制手绘图 + 客户端瓦片（2026-10-02）",
           font=hf, fill=GOLD)
    y = 70
    for txt, col, f in [
        ("第 1 层换成用户重绘的成品图（导 TGA 进 Media/）；第 2 层「达拉然下水道」没画 "
         "⇒ 仍走客户端瓦片。楼层按钮照旧 2 颗。", WHITE, sf),
        ("两块按插件真实几何画：地图画布 663×442、楼层按钮贴右上角内 6px"
         "（LAYER_W=56 / BAR_H=20 / GAP=6，选中金描边）。", GREEN, sf),
    ]:
        for ln in wrap(d, txt, f, W - PAD * 2):
            d.text((PAD, y), ln, font=f, fill=col)
            y += 22
    TOP = y + 42

    panel(im, d, PAD, TOP, draw_src,
          "第 1 层 · 达拉然城 · 自制手绘图",
          "Media/Maps/Dalaran.tga（512×512 / 24 位 RLE / 画面占顶部 341 行）", 1)
    panel(im, d, PAD + CW + GAPX, TOP, cli,
          "第 2 层 · 达拉然下水道 · 客户端瓦片",
          "Interface\\WorldMap\\Dalaran\\Dalaran2_（12 块 4×3 拼接）", 2)

    y = TOP + CH + 46
    notes = [
        ("★ 贴图口径与既有两本自制图**逐像素同款**（用同一条流水线重跑领主大厅/洛丹伦废墟，"
         "与成品最大通道差 7、平均 0.6）：中心裁到 3:2 → LANCZOS 缩 512×341 → 贴 512×512 黑底顶部 → "
         "24 位 RLE TGA、原点左下；下方 171 行黑边，运行期 SetTexCoord(0,1,0,341/512) 只取画面。", GREEN),
        ("★ 满铺同一块 663×442 画布 ⇒ 与客户端瓦片**共用百分比坐标系**，钉点可直接落"
         "（本副本目前没有钉点数据，所以左上角「隐藏 boss」开关也不出现）。", WHITE),
        ("★ 机制：CustomFloorFor(副本, 层号) —— 整图自制（领主大厅/洛丹伦废墟）仍走 CustomFor；"
         "两者互斥登记。没画的层 / 越界层号一律回客户端瓦片，不会被顶掉。", DIM),
    ]
    nf = fnt(13)
    for txt, col in notes:
        for ln in wrap(d, txt, nf, W - PAD * 2):
            d.text((PAD, y), ln, font=nf, fill=col)
            y += 24
        y += 8

    out = os.path.join(HERE, "DALARAN_MAP_LAYERS.png")
    im = im.crop((0, 0, W, y + 10))
    im.save(out)
    print("ok", out, im.size)


if __name__ == "__main__":
    main()
