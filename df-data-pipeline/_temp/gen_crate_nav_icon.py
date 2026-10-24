# -*- coding: utf-8 -*-
"""专业页导航「板条箱」自制图标（B 单色玻璃基调，同 gen_entry_icons.py 口径）：
- CrateNav.tga  木箱：灰白圆角线稿 + 两条金色竖捆带 + 横板缝，暗色底垫衬
64px 32bpp TGA（desc 0x28 = 顶行起 + 8bit alpha），4x 超采样抗锯齿；全程序化绘制。
用法：python gen_crate_nav_icon.py
"""
import os
import struct
import zlib

GRAY = (216, 222, 232)
GOLD = (232, 198, 106)
DARK = (10, 12, 16)
S = 64
SS = 4
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'Media', 'icon', 'NAV', 'CrateNav.tga')
PREV = OUT[:-4] + '_preview.png'


def rrect_hit(x0, y0, x1, y1, r, x, y):
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cxs = ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r))
    for cx, cy in cxs:
        ex = (x0 if cx == x0 + r else x1)
        ey = (y0 if cy == y0 + r else y1)
        if (ex == x0 and x <= cx) or (ex == x1 and x >= cx):
            if (ey == y0 and y <= cy) or (ey == y1 and y >= cy):
                return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    return True


def rrect_stroke(x0, y0, x1, y1, r, w, x, y):
    m = w / 2.0
    outer = rrect_hit(x0 - m, y0 - m, x1 + m, y1 + m, r + m, x, y)
    if not outer:
        return False
    inner = rrect_hit(x0 + m, y0 + m, x1 - m, y1 - m, max(0.0, r - m), x, y)
    return not inner


def band_hit(a, b, w, x, y):
    m = w / 2.0
    return a - m <= x <= b + m


def render(layers):
    img = [[(0, 0, 0, 0.0)] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            acc = {}
            for sy in range(SS):
                for sx in range(SS):
                    fx = x + (sx + 0.5) / SS
                    fy = y + (sy + 0.5) / SS
                    col = None
                    for (color, base, fn) in layers:
                        if fn(fx, fy):
                            col = (color, base)
                    if col:
                        key = col[0] + (col[1],)
                        acc[key] = acc.get(key, 0) + 1
            if acc:
                key, n = max(acc.items(), key=lambda kv: kv[1])
                a = n / (SS * SS) * key[3]
                img[y][x] = (key[0], key[1], key[2], a)
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


def write_png_preview(path, img, scale=6):
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


X0, Y0, X1, Y1 = 10.0, 12.0, 54.0, 52.0
RAD = 7.0
STR_W = 3.0

layers = [
    (DARK, 0.78, lambda x, y: rrect_hit(X0, Y0, X1, Y1, RAD, x, y)),
    (GRAY, 1.0, lambda x, y: rrect_stroke(X0, Y0, X1, Y1, RAD, STR_W, x, y)),
    (GRAY, 0.85, lambda x, y: (not rrect_stroke(X0, Y0, X1, Y1, RAD, STR_W, x, y))
                               and (abs(y - (Y0 + (Y1 - Y0) / 3.0)) <= 0.8 or abs(y - (Y0 + 2 * (Y1 - Y0) / 3.0)) <= 0.8)
                               and rrect_hit(X0, Y0, X1, Y1, RAD, x, y)),
    (GOLD, 1.0, lambda x, y: band_hit(X0 + (X1 - X0) / 3.0, X0 + (X1 - X0) / 3.0, STR_W, x, y)
                               and rrect_hit(X0, Y0, X1, Y1, RAD, x, y)),
    (GOLD, 1.0, lambda x, y: band_hit(X0 + 2 * (X1 - X0) / 3.0, X0 + 2 * (X1 - X0) / 3.0, STR_W, x, y)
                               and rrect_hit(X0, Y0, X1, Y1, RAD, x, y)),
]

img = render(layers)
write_tga(OUT, img)
write_png_preview(PREV, img)
