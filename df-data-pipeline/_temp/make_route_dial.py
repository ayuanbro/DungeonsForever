# -*- coding: utf-8 -*-
"""生成探索路线追踪条的罗盘两贴图（512 超采样 → 128 落盘）。

route_dial.tga  静态罗盘盘：深色圆盘 + 金环 + 顶部北点
route_arrow.tga 旋转金镖（掠翼镖）+ 中心深色轴心（居中 ⇒ 旋转不变）
输出：非压缩 32 位 TGA、左上原点（descriptor 0x28），WoW 直接可读。
"""
import os
import struct
from PIL import Image, ImageDraw

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(DF, 'Media', 'textures')
S = 512          # 超采样画布
FINAL = 128      # 落盘尺寸
GOLD = (240, 181, 61, 255)
DARK = (13, 14, 18, 255)
HUB = (16, 18, 22, 255)


def save_tga(path, img):
    w, h = img.size
    header = struct.pack('<BBB5xHHHHBB',
                         0, 0,          # id 长度 / 色表类型
                         2,             # 非压缩真彩
                         0, 0,          # x/y origin（左上）
                         w, h, 32, 0x28)
    with open(path, 'wb') as f:
        f.write(header)
        r, g, b, a = img.convert('RGBA').split()
        f.write(Image.merge('RGBA', (b, g, r, a)).tobytes())  # TGA 字节序 = BGRA
    print('OK', path, w, 'x', h)


def canvas():
    return Image.new('RGBA', (S, S), (0, 0, 0, 0))


def down(img):
    return img.resize((FINAL, FINAL), Image.LANCZOS)


# ── route_dial：深盘 + 金环 + 北点 ─────────────────────────
img = canvas()
d = ImageDraw.Draw(img)
cx = cy = S // 2
d.ellipse((cx - 246, cy - 246, cx + 246, cy + 246), fill=DARK)
d.ellipse((cx - 222, cy - 222, cx + 222, cy + 222), outline=GOLD, width=24)
d.ellipse((cx - 12, cy - 208, cx + 12, cy - 184), fill=GOLD)   # 北点
save_tga(os.path.join(OUT, 'route_dial.tga'), down(img))

# ── route_arrow：掠翼镖（旋转层）+ 居中轴心 ────────────────
img = canvas()
d = ImageDraw.Draw(img)
d.polygon([(cx, 58), (cx + 82, cy + 80), (cx, cy + 16), (cx - 82, cy + 80)],
          fill=GOLD)
d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=HUB)
d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), outline=GOLD, width=6)
save_tga(os.path.join(OUT, 'route_arrow.tga'), down(img))
