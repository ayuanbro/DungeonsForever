# -*- coding: utf-8 -*-
"""血色修道院 4 分区 → 客户端瓦片层 对照图（2026-10-01 索引核对用）。

产物 _temp/SM_MAP_INDEX.png：2×2，每格 = 该分区整图（1002x668 缩到 500x334）+ 标注。
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

ROWS = [
    ("1 墓园",   "sm_graveyard", "ScarletMonastery1_"),
    ("2 图书馆", "sm_library",   "ScarletMonastery2_"),
    ("3 军械库", "sm_armory",    "ScarletMonastery3_"),
    ("4 大教堂", "sm_cathedral", "ScarletMonastery4_"),
]

MW, MH = 500, 334          # 地图缩略
PAD, GAP, BAR = 18, 16, 30
CELL_W, CELL_H = MW, MH + BAR
W = PAD * 2 + CELL_W * 2 + GAP
H = PAD * 2 + CELL_H * 2 + GAP

canvas = Image.new("RGB", (W, H), (246, 243, 236))
d = ImageDraw.Draw(canvas)
f_big = ImageFont.truetype(FONT, 19)
f_small = ImageFont.truetype(FONT, 13)

for i, (zh, did, pre) in enumerate(ROWS):
    r, c = divmod(i, 2)
    x = PAD + c * (CELL_W + GAP)
    y = PAD + r * (CELL_H + GAP)
    src = Image.open(os.path.join(HERE, "_sm_%s.png" % pre.lower())).convert("RGB")
    thumb = src.crop((0, 0, 1002, 668)).resize((MW, MH), Image.LANCZOS)
    canvas.paste(thumb, (x, y + BAR))
    d.rectangle([x, y + BAR, x + MW - 1, y + BAR + MH - 1], outline=(168, 152, 120), width=1)
    d.text((x + 2, y + 2), "血色修道院 · %s" % zh, font=f_big, fill=(122, 78, 24))
    d.text((x + MW - 4, y + 8), "%s  →  %s" % (did, pre), font=f_small,
           fill=(110, 108, 104), anchor="ra")

out = os.path.join(HERE, "SM_MAP_INDEX.png")
canvas.save(out)
print(out, canvas.size)
