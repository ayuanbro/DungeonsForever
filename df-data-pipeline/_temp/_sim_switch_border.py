# -*- coding: utf-8 -*-
"""开关边框压暗前后的截图级预览（直接对用户截图重着色）。"""
import os

from PIL import Image, ImageDraw, ImageFont

SRC = r"C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-13T05-06-46-140Z-8c1180a1.png"
OUT = r"D:\workspace\DungeonsForever\_temp\_corner_view\switch_border_before_after.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

im = Image.open(SRC).convert("RGB")
W, H = im.size
px = im.load()

OLD = (107, 107, 117)
NEW = (74, 82, 99)
k = NEW[0] / OLD[0]

after = im.copy()
ap = after.load()
X0 = 505                       # 开关区域左界（避开「显示已完成」文字）
n = 0
for x in range(X0, W):
    for y in range(H):
        r, g, b = px[x, y]
        if 78 <= r <= 135 and abs(r - g) < 14 and 6 <= b - r <= 20:
            ap[x, y] = (int(r * k), int(g * k), int(b * k))
            n += 1
print("重着色像素", n)

Z = 2
canvas = Image.new("RGB", (W * Z, (H * 2 + 46) * Z), (250, 250, 252))
dr = ImageDraw.Draw(canvas)
try:
    F = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
except Exception:
    F = ImageFont.load_default()
dr.text((16, 10), "改前：开关边框 (107,107,117) —— 比按钮亮 45%", fill=(30, 30, 34), font=F)
canvas.paste(im.resize((W * Z, H * Z), Image.NEAREST), (0, 40))
dr.text((16, (H + 40) * Z + 12), "改后：开关边框 (74,82,99) —— 与按钮皮同色（厚度本就相同）", fill=(30, 30, 34), font=F)
canvas.paste(after.resize((W * Z, H * Z), Image.NEAREST), (0, (H + 40) * Z))

# 裁掉下方多余留白后保存
canvas.crop((0, 0, W * Z, (H + 40) * Z + H * Z + 36)).save(OUT)
print("输出", OUT)
