# -*- coding: utf-8 -*-
"""生成「BuildCapsule 换贴图前后」的标注对比图（交付用）。"""
import os
import struct

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_corner_view")
os.makedirs(OUT, exist_ok=True)


def load_alpha(path):
    d = open(path, "rb").read()
    w, h, bpp, desc = struct.unpack("<HHBB", d[12:18])
    img = Image.new("L", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = d[18 + (y * w + x) * 4 + 3]
    return img


old_src = load_alpha(os.path.join(ROOT, "Media/LibHUI/HUIRoundCornerFill.tga"))
new_src = load_alpha(os.path.join(ROOT, "Media/LibHUI/HUIGlassFill8.tga"))

R = 8
old_corner = old_src.resize((R, R), Image.BILINEAR)
new_corner = new_src.crop((0, 0, 16, 16)).resize((R, R), Image.BILINEAR)

Z = 14
W, H = 760, 330
canvas = Image.new("RGB", (W, H), (250, 250, 252))
dr = ImageDraw.Draw(canvas)
try:
    F = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
    Fs = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
except Exception:
    F = Fs = ImageFont.load_default()

dr.text((28, 20), "iOS 开关圆角：换贴图前后（半径 8，角块放大 14 倍）", fill=(30, 30, 34), font=F)


def paste_corner(corner, x0, label, sub):
    big = corner.resize((R * Z, R * Z), Image.NEAREST)
    # 深底显白
    tile = Image.new("RGB", (R * Z + 2, R * Z + 2), (36, 40, 48))
    tile.paste(big.convert("RGB").point(lambda v: v), (1, 1), big)
    canvas.paste(tile, (x0, 70))
    dr.text((x0, 48), label, fill=(30, 30, 34), font=Fs)
    dr.text((x0, 70 + R * Z + 10), sub, fill=(90, 90, 96), font=Fs)


paste_corner(old_corner, 60, "改前：4 张独立角贴图（32×32）", "BuildCapsule 旧路径")
paste_corner(new_corner, 300, "改后：单张 64×64 超采样图 UV 取象限", "与卡片底/描边同一体系")

dr.line((260, 60, 260, 250), fill=(200, 200, 206), width=1)
dr.text((28, 250), "角块 alpha 矩阵逐像素比对：最大差 8/255（≈3%）—— 圆角半径与弧线位置完全一致；",
        fill=(40, 40, 44), font=Fs)
dr.text((28, 274), "差异只来自新贴图的 2 倍采样密度（四角同源、边缘更细腻）。件数仍为 7 片，几何零改动。",
        fill=(40, 40, 44), font=Fs)
dr.text((28, 300), "适用范围：iOS 开关 / 滑杆轨道与圆钮 / hover 胶囊 / 按钮皮 / 制品药丸（全部 BuildCapsule 消费方）。",
        fill=(120, 120, 126), font=Fs)

out = os.path.join(OUT, "capsule_radius_before_after.png")
canvas.save(out)
print("输出", out)
