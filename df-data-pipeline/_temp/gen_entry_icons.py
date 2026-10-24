# -*- coding: utf-8 -*-
"""入口/地图 自制图标（B 单色玻璃基调）：
- EntryPin.tga  定位 pin：灰白描边 teardrop + 金色内点（详情页「入口」chip 13px、地图入口钉点 27px）
- MapFold.tga   折叠地图：灰白线稿 + 折缝 + 金色定位针压中心（暗色描边垫底）（详情页「地图」页签 14px）
64px 32bpp TGA，4x 超采样抗锯齿；全部程序化绘制，不用任何外部素材。
"""
import struct, math, zlib

GRAY = (216, 222, 232)
GOLD = (232, 198, 106)
DARK = (10, 12, 16)
S = 64
SS = 4  # 超采样


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


def teardrop_boundary(c, r, tip, arc_n=48):
    """teardrop（定位 pin）边界折线：圆弧（过顶）+ 两条切线到 tip。y 向下坐标系。"""
    cx, cy = c
    dx, dy = tip[0] - cx, tip[1] - cy
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    px_, py_ = -uy, ux
    k = math.sqrt(d * d - r * r)
    t1 = (cx + r * (r / d * ux + k / d * px_), cy + r * (r / d * uy + k / d * py_))
    t2 = (cx + r * (r / d * ux - k / d * px_), cy + r * (r / d * uy - k / d * py_))
    a1 = math.atan2(t1[1] - cy, t1[0] - cx)
    a2 = math.atan2(t2[1] - cy, t2[0] - cx)
    # 取经过「顶部」(角度 a_c - pi/2 方向) 的那段弧
    atop = math.atan2(-uy, -ux)  # 顶点方向 = tip 的反方向（y 向下坐标）
    def norm(a):
        while a < 0: a += 2 * math.pi
        while a >= 2 * math.pi: a -= 2 * math.pi
        return a
    a1, a2, atop = norm(a1), norm(a2), norm(atop)
    # 弧走向：从 a1 增到 a2，途中必须含 atop
    def span(f, t):
        return (t - f) % (2 * math.pi)
    if not (span(a1, atop) < span(a1, a2)):
        a1, a2 = a2, a1
    total = span(a1, a2)
    pts = []
    for i in range(arc_n + 1):
        a = a1 + total * i / arc_n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(tip)
    pts.append(pts[0])  # 闭合：tip → T1
    return pts


def render(layers):
    """layers: [(color, base_alpha, coverage_fn(x,y)->bool), ...] 后层压前层"""
    img = [[(0, 0, 0, 0.0)] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            acc = {}  # 按 color 累计覆盖
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
            # 取覆盖数最多的颜色
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


# ── EntryPin：pin 满幅（地图钉点也用同一张）──
pin = teardrop_boundary((32, 27), 15.5, (32, 59))
dot = lambda fx, fy: circle_hit(32, 27, 5.6, fx, fy)
entry_layers = [
    (GRAY, 1.0, lambda fx, fy: stroke_alpha(pin, fx, fy, 3.4)),
    (GOLD, 1.0, dot),
]
img = render(entry_layers)
write_tga('Media/EntryPin.tga', img)
write_png_preview('_temp/_corner_view/EntryPin.png', img)

# ── MapFold：折叠地图 + 中心金色定位针 ──
map_outline = [(26, 16), (38, 20), (50, 16), (50, 44), (38, 48), (26, 44), (14, 48), (14, 20), (26, 16)]
fold1 = [(26, 16), (26, 44)]
fold2 = [(38, 20), (38, 48)]
mpin = teardrop_boundary((32, 29.5), 5.2, (32, 42.5))
map_layers = [
    (GRAY, 0.55, lambda fx, fy: stroke_alpha(fold1, fx, fy, 1.8) or stroke_alpha(fold2, fx, fy, 1.8)),
    (GRAY, 1.0, lambda fx, fy: stroke_alpha(map_outline, fx, fy, 3.0)),
    (DARK, 0.9, lambda fx, fy: stroke_alpha(mpin, fx, fy, 6.6)),
    (GOLD, 1.0, lambda fx, fy: pip(mpin, fx, fy)),
    (DARK, 1.0, lambda fx, fy: circle_hit(32, 29.5, 1.7, fx, fy)),
]
img2 = render(map_layers)
write_tga('Media/MapFold.tga', img2)
write_png_preview('_temp/_corner_view/MapFold.png', img2)
