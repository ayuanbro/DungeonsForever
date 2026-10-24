# -*- coding: utf-8 -*-
"""任务图钉三态图标（方案二 · 扁平色针，2026-10-14 用户拍板）：
- QuestPinReady.tga   可接：琥珀色针身 + 白色「!」
- QuestPinLocked.tga  被锁：灰银针身 + 白色挂锁
- QuestPinPre.tga     前置NPC：蓝色针身 + 白色链环
64px 32bpp TGA（二次幂），4x 超采样抗锯齿；全部程序化绘制，无外部素材。
针形与 EntryPin 同规格：圆心 (32,27) r15.5、尖 (32,59)。
用法：cd D:/workspace/DungeonsForever && python _temp/gen_quest_pin_icons.py
"""
import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)

AMBER = (239, 159, 39)
SLATE = (136, 135, 128)
BLUE = (55, 138, 221)
WHITE = (255, 255, 255)
OUTLINE = (255, 255, 255)

S = 64
SS = 4


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def stroke_alpha(pts, x, y, w):
    d = min(seg_dist(x, y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1))
    return d <= w / 2


def circle_hit(cx, cy, r, x, y):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


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


def rect_hit(x0, y0, x1, y1):
    return lambda x, y: x0 <= x <= x1 and y0 <= y <= y1


def rrect_hit(x0, y0, x1, y1, r):
    def hit(x, y):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        nx = min(max(x, x0 + r), x1 - r)
        ny = min(max(y, y0 + r), y1 - r)
        return (x - nx) ** 2 + (y - ny) ** 2 <= r * r
    return hit


def rot_rect_hit(cx, cy, length, width, deg):
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)
    hl, hw = length / 2.0, width / 2.0
    def hit(x, y):
        dx, dy = x - cx, y - cy
        du = dx * ux + dy * uy
        dv = -dx * uy + dy * ux
        return abs(du) <= hl and abs(dv) <= hw
    return hit


def teardrop_boundary(c, r, tip, arc_n=48, tip_r=None):
    cx, cy = c
    dx, dy = tip[0] - cx, tip[1] - cy
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    px_, py_ = -uy, ux
    k = math.sqrt(d * d - r * r)
    t1 = (cx + r * (r / d * ux + k / d * px_), cy + r * (r / d * uy + k / d * py_))
    t2 = (cx + r * (r / d * ux - k / d * px_), cy + r * (r / d * uy - k / d * py_))

    def norm(a):
        while a < 0: a += 2 * math.pi
        while a >= 2 * math.pi: a -= 2 * math.pi
        return a

    def span(f, t):
        return (t - f) % (2 * math.pi)

    if tip_r:
        alpha = math.asin(r / d)
        h = tip_r / math.sin(alpha)
        tlen = tip_r / math.tan(alpha)
        ct = (tip[0] - ux * h, tip[1] - uy * h)
        p1 = (tip[0] + (t1[0] - tip[0]) / math.hypot(t1[0] - tip[0], t1[1] - tip[1]) * tlen,
              tip[1] + (t1[1] - tip[1]) / math.hypot(t1[0] - tip[0], t1[1] - tip[1]) * tlen)
        p2 = (tip[0] + (t2[0] - tip[0]) / math.hypot(t2[0] - tip[0], t2[1] - tip[1]) * tlen,
              tip[1] + (t2[1] - tip[1]) / math.hypot(t2[0] - tip[0], t2[1] - tip[1]) * tlen)
        ap1 = norm(math.atan2(p1[1] - ct[1], p1[0] - ct[0]))
        ap2 = norm(math.atan2(p2[1] - ct[1], p2[0] - ct[0]))
        au = norm(math.atan2(uy, ux))
        sw21 = span(ap2, au) + span(au, ap1)
        sw12 = span(ap1, au) + span(au, ap2)
        if sw21 <= sw12:
            cap = [(ct[0] + tip_r * math.cos(ap2 + sw21 * i / 16),
                    ct[1] + tip_r * math.sin(ap2 + sw21 * i / 16)) for i in range(17)]
        else:
            cap = [(ct[0] + tip_r * math.cos(ap1 + sw12 * i / 16),
                    ct[1] + tip_r * math.sin(ap1 + sw12 * i / 16)) for i in range(17)]
            cap.reverse()
        a1 = norm(math.atan2(t1[1] - cy, t1[0] - cx))
        a2 = norm(math.atan2(t2[1] - cy, t2[0] - cx))
        atop = norm(math.atan2(-uy, -ux))
        if not (span(a1, atop) < span(a1, a2)):
            a1, a2 = a2, a1
        pts = []
        for i in range(arc_n + 1):
            a = a1 + span(a1, a2) * i / arc_n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pts += cap[1:]
        pts.append(pts[0])
        return pts
    a1 = math.atan2(t1[1] - cy, t1[0] - cx)
    a2 = math.atan2(t2[1] - cy, t2[0] - cx)
    atop = math.atan2(-uy, -ux)
    a1, a2, atop = norm(a1), norm(a2), norm(atop)
    if not (span(a1, atop) < span(a1, a2)):
        a1, a2 = a2, a1
    total = span(a1, a2)
    pts = []
    for i in range(arc_n + 1):
        a = a1 + total * i / arc_n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(tip)
    pts.append(pts[0])
    return pts


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


PIN = teardrop_boundary((32, 27), 15.5, (32, 59), tip_r=6)


def dilated_hit(pts, d):
    def hit(x, y):
        if pip(pts, x, y):
            return True
        for i in range(len(pts) - 1):
            if seg_dist(x, y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) <= d:
                return True
        return False
    return hit


PIN_OUT = dilated_hit(PIN, 2.2)

# 「!」：竖条 + 点
excl_bar = rect_hit(29.5, 16.5, 34.5, 28.5)
excl_dot = lambda x, y: circle_hit(32, 34.6, 2.7, x, y)

# 挂锁：锁环（上半环带）+ 锁体圆角矩形
lock_shackle = lambda x, y: circle_hit(32, 26.5, 5.6, x, y) and not circle_hit(32, 26.5, 3.4, x, y) and y <= 26.5
lock_body = rrect_hit(24.6, 26.5, 39.4, 37.4, 2.2)

# 链环：两枚斜排相扣的圆环（环带 = 外圆 − 内圆；斜排 45°）
RING_OUT, RING_IN = 6.2, 3.6
ring1 = lambda x, y: circle_hit(28, 32.5, RING_OUT, x, y) and not circle_hit(28, 32.5, RING_IN, x, y)
ring2 = lambda x, y: circle_hit(36, 24.5, RING_OUT, x, y) and not circle_hit(36, 24.5, RING_IN, x, y)
chain_glyph = lambda x, y: ring1(x, y) or ring2(x, y)

ICONS = [
    ("Media/QuestPinReady.tga", AMBER, lambda x, y: excl_bar(x, y) or excl_dot(x, y)),
    ("Media/QuestPinLocked.tga", SLATE, lambda x, y: lock_shackle(x, y) or lock_body(x, y)),
    ("Media/QuestPinPre.tga", BLUE, chain_glyph),
]

for rel, color, glyph in ICONS:
    layers = [
        (OUTLINE, 1.0, PIN_OUT),
        (color, 1.0, lambda x, y: pip(PIN, x, y)),
        (WHITE, 1.0, glyph),
    ]
    img = render(layers)
    write_tga(os.path.join(DF, rel), img)
    write_png_preview(os.path.join(DF, '_temp/_corner_view/' + os.path.basename(rel).replace('.tga', '.png')), img)
