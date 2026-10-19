# -*- coding: utf-8 -*-
"""找书打卡标三态纹理（白色单色，运行时 SetVertexColor 染色）：
- CheckDisc.tga  实心圆盘（背包有=绿 / 已上交=金）
- CheckRing.tga  圆环描边（未找到=灰，悬停提亮）
- CheckMark.tga  对勾笔画（单勾=第一步；错位双勾=已上交第二步，第二张运行时降 alpha 左移）
64px 32bpp TGA，4x 超采样抗锯齿；全部程序化绘制，不用任何外部素材。
"""
import struct, math, zlib

S = 64
SS = 4
WHITE = (255, 255, 255)


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


def ring_pts(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


# 实心圆盘（染色底）
disc = [(WHITE, 1.0, lambda fx, fy: circle_hit(32, 32, 30.5, fx, fy))]
write_tga('Media/CheckDisc.tga', render(disc))

# 圆环描边（未勾选态）
ring = ring_pts(32, 32, 28.5)
ring_img = render([(WHITE, 1.0, lambda fx, fy: stroke_alpha(ring, fx, fy, 5.5))])
write_tga('Media/CheckRing.tga', ring_img)

# 单勾（圆头笔画：折线 + 两端圆帽）
tick = [(19, 34), (28.5, 43), (46, 22)]
cap1 = lambda fx, fy: circle_hit(19, 34, 3.4, fx, fy)
cap2 = lambda fx, fy: circle_hit(46, 22, 3.4, fx, fy)
tick_img = render([(WHITE, 1.0, lambda fx, fy: stroke_alpha(tick, fx, fy, 6.8) or cap1(fx, fy) or cap2(fx, fy))])
write_tga('Media/CheckMark.tga', tick_img)

# 并排双勾（已上交终态：两道 f0.8 白勾 ∓9.5 并排烘焙成一张，运行时整贴直用）
def tick_pts(f, dx, dy):
    return [(19 * f + (1 - f) * 32 + dx, 34 * f + (1 - f) * 32 + dy),
            (28.5 * f + (1 - f) * 32 + dx, 43 * f + (1 - f) * 32 + dy),
            (46 * f + (1 - f) * 32 + dx, 22 * f + (1 - f) * 32 + dy)]

def tick_layer(f, dx, dy):
    pts = tick_pts(f, dx, dy)
    w = 6.8 * f
    return lambda fx, fy: (stroke_alpha(pts, fx, fy, w)
                           or circle_hit(pts[0][0], pts[0][1], w / 2, fx, fy)
                           or circle_hit(pts[2][0], pts[2][1], w / 2, fx, fy))

ticks2_img = render([
    (WHITE, 1.0, tick_layer(0.8, -9.5, 0)),
    (WHITE, 1.0, tick_layer(0.8, 9.5, 0)),
])
write_tga('Media/CheckTicks2.tga', ticks2_img)

# 预览：三态合成（灰环 / 绿盘单勾 / 金盘双勾）
def stack(layers):
    return render(layers)

GREEN = (63, 163, 77)
GOLD = (209, 165, 18)
GREY = (107, 111, 118)
CHAMP = (232, 198, 106)

def shift_tick(dx, dy):
    return lambda fx, fy: stroke_alpha([(x + dx, y + dy) for x, y in tick], fx, fy, 6.8) \
        or circle_hit(19 + dx, 34 + dy, 3.4, fx, fy) or circle_hit(46 + dx, 22 + dy, 3.4, fx, fy)

prev_dir = '_temp/_corner_view'
states = [
    ('CheckStates_idle', [(GREY, 1.0, lambda fx, fy: stroke_alpha(ring, fx, fy, 5.5))]),
    ('CheckStates_bag', [(GREEN, 1.0, lambda fx, fy: circle_hit(32, 32, 30.5, fx, fy)),
                         (WHITE, 1.0, shift_tick(0, 0))]),
    ('CheckStates_done', [(CHAMP, 1.0, lambda fx, fy: circle_hit(32, 32, 30.5, fx, fy)),
                          (WHITE, 1.0, tick_layer(0.8, -9.5, 0)),
                          (WHITE, 1.0, tick_layer(0.8, 9.5, 0))]),
]
for name, layers in states:
    img = stack(layers)
    write_png_preview('%s/%s.png' % (prev_dir, name), img)
