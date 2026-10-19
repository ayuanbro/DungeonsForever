# -*- coding: utf-8 -*-
"""BuildCapsule 换贴图前后：角块像素仿真对比（半径语义是否一致 + 边缘质量）。"""
import os
import struct

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_corner_view")
os.makedirs(OUT, exist_ok=True)

OLD = os.path.join(ROOT, "Media/LibHUI/HUIRoundCornerFill.tga")
NEW = os.path.join(ROOT, "Media/LibHUI/HUIGlassFill8.tga")


def load_alpha(path):
    d = open(path, "rb").read()
    w, h, bpp, desc = struct.unpack("<HHBB", d[12:18])
    img = Image.new("L", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = d[18 + (y * w + x) * 4 + 3]
    return img


old_src = load_alpha(OLD)
new_src = load_alpha(NEW)
print("旧贴图", old_src.size, "| 新贴图", new_src.size)

R = 8
# 旧：整张贴图缩放到 r×r
old_corner = old_src.resize((R, R), Image.BILINEAR)
# 新：取左上象限 UV 0..snap/32 = 0..0.25 → 像素 [0, 16)
q = 16
new_corner = new_src.crop((0, 0, q, q)).resize((R, R), Image.BILINEAR)

print("旧角块 alpha 矩阵（%dx%d）：" % (R, R))
for y in range(R):
    print("   " + "".join("%4d" % old_corner.getpixel((x, y)) for x in range(R)))
print("新角块 alpha 矩阵（%dx%d）：" % (R, R))
for y in range(R):
    print("   " + "".join("%4d" % new_corner.getpixel((x, y)) for x in range(R)))

diff = 0
for y in range(R):
    for x in range(R):
        diff = max(diff, abs(old_corner.getpixel((x, y)) - new_corner.getpixel((x, y))))
print("两角块单像素最大 alpha 差 =", diff)

# 整体 36x20 开关轨道对比
W, H = 36, 20
def render(corner):
    im = Image.new("L", (W, H), 0)
    px = im.load()
    for y in range(H):
        for x in range(W):
            a = 0
            if R <= x < W - R and R <= y < H - R:
                a = 255                       # 中段
            elif R <= x < W - R:
                a = 255                       # 上下直边
            elif R <= y < H - R:
                a = 255                       # 左右直边
            else:
                cx = 0 if x < R else W - R
                cy = 0 if y < R else H - R
                ox, oy = x - cx, y - cy
                if x >= R and y < R:
                    ox, oy = ox, oy
                if x < R and y < R:
                    a = corner.getpixel((x, y))
                elif x >= W - R and y < R:
                    a = corner.getpixel((R - 1 - (x - (W - R)), y))
                elif x < R and y >= H - R:
                    a = corner.getpixel((x, R - 1 - (y - (H - R))))
                else:
                    a = corner.getpixel((R - 1 - (x - (W - R)), R - 1 - (y - (H - R))))
            px[x, y] = a
    return im

old_full = render(old_corner)
new_full = render(new_corner)

Z = 8
canvas = Image.new("L", (W * Z * 2 + 30, H * Z + 56), 30)
canvas.paste(old_full.resize((W * Z, H * Z), Image.NEAREST), (10, 40))
canvas.paste(new_full.resize((W * Z, H * Z), Image.NEAREST), (W * Z + 20, 40))
canvas.save(os.path.join(OUT, "capsule_old_vs_new.png"))
print("输出：", os.path.join(OUT, "capsule_old_vs_new.png"))
