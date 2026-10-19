# -*- coding: utf-8 -*-
"""WarnTri.tga 自绘警告三角（2026-10-11 用户拍板方案 C）。
64px 32bpp 二次幂 TGA，4x 超采样抗锯齿；圆角三角 + 深红描边 + 白色感叹号。
y 向下设计坐标、desc=0x28，与 gen_entry_icons.py 同管线（已在产验证）。
"""
import struct, math, zlib

S = 64
SS = 4
RED = (236, 50, 50)
RED_DARK = (146, 22, 22)
WHITE = (252, 252, 254)

A = (32.0, 9.0)
B = (55.0, 53.0)
C = (9.0, 53.0)
R = 4.0
OUT = 2.2


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def pip(poly, x, y):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def offset_line(p1, p2, d):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    return (p1[0] + nx * d, p1[1] + ny * d), (dx / L, dy / L)


def line_isect(l1, l2):
    (p1, d1), (p2, d2) = l1, l2
    den = d1[0] * d2[1] - d1[1] * d2[0]
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)


edges = [(A, B), (B, C), (C, A)]
offs = [offset_line(p1, p2, R) for (p1, p2) in edges]
INSET = [line_isect(offs[i - 1], offs[i]) for i in range(3)]
INSET_BD = [(INSET[i], INSET[(i + 1) % 3]) for i in range(3)]


def tri_dist(x, y):
    if pip(INSET, x, y):
        return 0.0
    return min(seg_dist(x, y, s[0][0], s[0][1], s[1][0], s[1][1]) for s in INSET_BD)


def capsule(ax, ay, bx, by, r, x, y):
    return seg_dist(x, y, ax, ay, bx, by) <= r


def circle(cx, cy, r, x, y):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


BAR = lambda fx, fy: capsule(32, 23, 32, 35, 3.1, fx, fy)
DOT = lambda fx, fy: circle(32, 46.5, 3.2, fx, fy)

layers = [
    (RED_DARK, 1.0, lambda fx, fy: tri_dist(fx, fy) <= R + OUT),
    (RED, 1.0, lambda fx, fy: tri_dist(fx, fy) <= R),
    (WHITE, 1.0, lambda fx, fy: BAR(fx, fy) or DOT(fx, fy)),
]


def render(ls):
    img = [[(0, 0, 0, 0.0)] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            acc = {}
            for sy in range(SS):
                for sx in range(SS):
                    fx = x + (sx + 0.5) / SS
                    fy = y + (sy + 0.5) / SS
                    col = None
                    for (color, base, fn) in ls:
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


img = render(layers)
write_tga('Media/WarnTri.tga', img)
write_png_preview('_temp/_corner_view/WarnTri.png', img)
