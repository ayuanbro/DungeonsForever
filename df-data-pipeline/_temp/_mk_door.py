# -*- coding: utf-8 -*-
"""画 Media/MapDoor.tga（入口钉 · 自制石门，BossSkull 同套扁平风）。128x128 RGBA。"""
from PIL import Image, ImageDraw

W = H = 128
img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

STONE = (106, 97, 84, 255)      # 石框
STONE_DK = (78, 71, 62, 255)    # 石框暗缘
OPEN = (24, 20, 14, 255)        # 门洞
GOLD = (226, 181, 60, 255)      # 顶心石（与 boss 金同族）

# 外框：拱 = 上半圆 + 矩形（石框层，最大）
d.pieslice([16, 8, 112, 104], 180, 360, fill=STONE)
d.rectangle([16, 56, 112, 120], fill=STONE)
# 底沿
d.rectangle([16, 112, 112, 120], fill=STONE_DK)

# 内层门洞（内缩 16）
d.pieslice([32, 24, 96, 88], 180, 360, fill=OPEN)
d.rectangle([32, 56, 96, 112], fill=OPEN)

# 顶心石（拱顶一块金色楔石）
d.pieslice([58, 8, 70, 20], 180, 360, fill=GOLD)
d.rectangle([58, 12, 70, 24], fill=GOLD)

# 石框上的两道砖缝（左右竖直）
d.line([24, 60, 24, 118], fill=STONE_DK, width=2)
d.line([104, 60, 104, 118], fill=STONE_DK, width=2)

img.save('Media/MapDoor.tga')
print('Media/MapDoor.tga 已生成', img.size)
