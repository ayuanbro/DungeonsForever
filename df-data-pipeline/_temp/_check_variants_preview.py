# -*- coding: utf-8 -*-
"""双勾形态 / 配色方案预览（只出预览图，不动运行时 TGA）。
形态 A 并排双勾 / B 深色后勾 / C 勾+点 / D 盘内白环
配色：正黄(现) / 香槟金 / 琥珀金 / 天蓝 / 亮绿
输出：上排 = 4 形态（香槟金盘），下排 = 5 配色（盘+单白勾）
"""
import struct, math, zlib

S = 64
SS = 4
WHITE = (255, 255, 255)
GOLD_NOW = (255, 209, 0)
CHAMPAGNE = (232, 198, 106)
AMBER = (209, 160, 40)
SKY = (77, 159, 255)
LIME = (64, 217, 89)


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


def scale_tick(f, dx=0.0, dy=0.0, w=None):
    pts = [(19 * f + (1 - f) * 32 + dx, 34 * f + (1 - f) * 32 + dy),
           (28.5 * f + (1 - f) * 32 + dx, 43 * f + (1 - f) * 32 + dy),
           (46 * f + (1 - f) * 32 + dx, 22 * f + (1 - f) * 32 + dy)]
    return pts, (w or 6.8 * f)


def tick_hit(pts, w):
    p1, p2 = pts[0], pts[2]
    return (lambda fx, fy: stroke_alpha(pts, fx, fy, w)
            or circle_hit(p1[0], p1[1], w / 2, fx, fy)
            or circle_hit(p2[0], p2[1], w / 2, fx, fy))


def darken(c, k=0.62):
    return tuple(int(v * k) for v in c)


def tile_rgb(img, scale=4):
    """返回 scale 倍放大的 RGB 像素行列表（每行 = S*scale 个 (r,g,b)）"""
    rows = []
    for Y in range(S * scale):
        y = Y // scale
        row = []
        for X in range(S * scale):
            x = X // scale
            r, g, b, a = img[y][x]
            bg = (70, 70, 74) if (x + y) % 2 == 0 else (52, 52, 56)
            row.append((int(bg[0] + (r - bg[0]) * a),
                        int(bg[1] + (g - bg[1]) * a),
                        int(bg[2] + (b - bg[2]) * a)))
        rows.append(row)
    return rows


def grid_png(path, tiles, cols, pad=8):
    tw = S * 4
    rows = (len(tiles) + cols - 1) // cols
    W = cols * tw + (cols + 1) * pad
    H = rows * tw + (rows + 1) * pad
    canvas = [[(36, 36, 40)] * W for _ in range(H)]
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        oy, ox = pad + r * (tw + pad), pad + c * (tw + pad)
        for y in range(tw):
            canvas[oy + y][ox:ox + tw] = t[y]
    raw = bytearray()
    for row in canvas:
        raw.append(0)
        for (r, g, b) in row:
            raw += bytes([r, g, b])
    def chunk(t, data):
        c = t + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)
    print('preview', path)


disc_fn = lambda fx, fy: circle_hit(32, 32, 30.5, fx, fy)

aL, aw = scale_tick(0.8, -9.5, 0)
aR, arw = scale_tick(0.8, 9.5, 0)
bB, bw = scale_tick(0.9, -7, 1.5)
bF, bfw = scale_tick(0.9, 0, 0)
c_dot = lambda fx, fy: circle_hit(21, 36, 5.6, fx, fy)
cT, cw = scale_tick(0.85, 8, 0)
d_ring = [(32 + 26 * math.cos(2 * math.pi * i / 72), 32 + 26 * math.sin(2 * math.pi * i / 72)) for i in range(73)]
dT, dw = scale_tick(0.8, 0, 0)

shapes = [
    [(CHAMPAGNE, 1.0, disc_fn), (WHITE, 1.0, tick_hit(aL, aw)), (WHITE, 1.0, tick_hit(aR, arw))],
    [(CHAMPAGNE, 1.0, disc_fn), (darken(CHAMPAGNE), 1.0, tick_hit(bB, bw)), (WHITE, 1.0, tick_hit(bF, bfw))],
    [(CHAMPAGNE, 1.0, disc_fn), (WHITE, 1.0, c_dot), (WHITE, 1.0, tick_hit(cT, cw))],
    [(CHAMPAGNE, 1.0, disc_fn), (WHITE, 1.0, lambda fx, fy: stroke_alpha(d_ring, fx, fy, 3.6)), (WHITE, 1.0, tick_hit(dT, dw))],
]

tiles = [tile_rgb(render(layers)) for layers in shapes]

for col in (GOLD_NOW, CHAMPAGNE, AMBER, SKY, LIME):
    t, tw = scale_tick(0.85, 0, 0)
    tiles.append(tile_rgb(render([(col, 1.0, disc_fn), (WHITE, 1.0, tick_hit(t, tw))])))

grid_png('_temp/_corner_view/CheckVariants.png', tiles, 5)
