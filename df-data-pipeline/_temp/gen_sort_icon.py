# -*- coding: utf-8 -*-
"""专业页列表表头「排序」小图标（表头右列左侧，点击切换价格排序）：
- SortIcon.tga  双竖箭头（左降右升），浅灰绘制，游戏内 SetVertexColor 染色（金=启用 / 灰=未启用）
32px 32bpp TGA（二次幂尺寸——引擎对非幂次 TGA 会拒载，24px 版实机不显示）（desc 0x28 = 顶行起 + 8bit alpha），4x 超采样抗锯齿；全程序化绘制。
用法：python gen_sort_icon.py
"""
import os
import struct
import zlib

GRAY = (222, 227, 235)
S = 32
SS = 4
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'Media', 'icon', 'NAV', 'SortIcon.tga')
PREV = OUT[:-4] + '_preview.png'


def tri_hit(p0, p1, p2, x, y):
    def sign(ax, ay, bx, by, cx, cy):
        return (x - bx) * (ay - by) - (ax - bx) * (y - by)
    d1 = sign(p0[0], p0[1], p1[0], p1[1], x, y)
    d2 = sign(p1[0], p1[1], p2[0], p2[1], x, y)
    d3 = sign(p2[0], p2[1], p0[0], p0[1], x, y)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def shaft_hit(cx, half_w, y0, y1, x, y):
    return cx - half_w <= x <= cx + half_w and y0 <= y <= y1


def render(layers):
    img = [[(0, 0, 0, 0.0)] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            acc = 0
            for sy in range(SS):
                for sx in range(SS):
                    fx = x + (sx + 0.5) / SS
                    fy = y + (sy + 0.5) / SS
                    if any(fn(fx, fy) for fn in layers):
                        acc += 1
            if acc:
                img[y][x] = (GRAY[0], GRAY[1], GRAY[2], acc / (SS * SS))
    return img


def write_tga(path, img):
    raw = bytearray()
    for row in img:
        for (r, g, b, a) in row:
            raw += bytes([b, g, r, int(a * 255 + 0.5)])
    hdr = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, S, S, 32, 0x28)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(hdr + bytes(raw))
    print('wrote', path)


def write_png_preview(path, img, scale=8):
    W = H = S * scale
    raw = bytearray()
    for Y in range(H):
        raw.append(0)
        for X in range(W):
            x, y = X // scale, Y // scale
            r, g, b, a = img[y][x]
            bg = (70, 70, 74) if (x + y) % 2 == 0 else (52, 52, 56)
            rr = int(bg[0] + (r - bg[0]) * a)
            gg = int(bg[1] + (g - bg[1]) * a)
            bb = int(bg[2] + (b - bg[2]) * a)
            raw += bytes([rr, gg, bb])

    def chunk(t, data):
        c = t + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)
    print('preview', path)


# 左 = 降序箭头（头朝下），右 = 升序箭头（头朝上）；杆宽 3px，头部 12px 等边
DN_CX, UP_CX = 10.0, 22.0
HALF = 2.0
layers = [
    lambda x, y: shaft_hit(DN_CX, HALF, 5.0, 20.0, x, y),
    lambda x, y: tri_hit((3.0, 19.0), (17.0, 19.0), (DN_CX, 28.0), x, y),
    lambda x, y: shaft_hit(UP_CX, HALF, 12.0, 27.0, x, y),
    lambda x, y: tri_hit((15.0, 13.0), (29.0, 13.0), (UP_CX, 4.0), x, y),
]

img = render(layers)
write_tga(OUT, img)
write_png_preview(PREV, img)
