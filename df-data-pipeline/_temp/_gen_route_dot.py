# -*- coding: utf-8 -*-
"""生成路线圆点贴图 route_dot.tga：32x32 白圆，抗锯齿边缘（8x 超采样）。"""
from PIL import Image, ImageDraw

SS = 8
SIZE = 32
big = SIZE * SS
img = Image.new("RGBA", (big, big), (255, 255, 255, 0))
d = ImageDraw.Draw(img)
pad = SS // 2
d.ellipse([pad, pad, big - pad - 1, big - pad - 1], fill=(255, 255, 255, 255))
img = img.resize((SIZE, SIZE), Image.LANCZOS)

out = r"D:\workspace\DungeonsForever\Media\textures\route_dot.tga"
img.save(out)
print("saved", out, img.size, img.mode)
