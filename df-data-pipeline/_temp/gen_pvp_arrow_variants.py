import math
import struct
import zlib

S = 64
GOLD = (255, 209, 0)


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def clamp01(v):
    return max(0.0, min(1.0, v))


def stroke_fn(pts, w):
    def f(x, y):
        d = min(seg_dist(x + 0.5, y + 0.5, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                for i in range(len(pts) - 1))
        return clamp01(w / 2 + 0.5 - d)
    return f


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


def poly_fn(polys, ss=4):
    def f(x, y):
        n = 0
        for i in range(ss):
            for j in range(ss):
                px = x + (i + 0.5) / ss
                py = y + (j + 0.5) / ss
                for poly in polys:
                    if pip(poly, px, py):
                        n += 1
                        break
        return n / (ss * ss)
    return f


def combine(*fns):
    def f(x, y):
        return max(fn(x, y) for fn in fns)
    return f


VARIANTS = {
    'A': ('V 形（现款）', stroke_fn([(20, 22), (44, 32), (20, 42)], 8.0)),
    'B': ('杆 + 实心三角', poly_fn([
        [(16, 29), (38, 29), (38, 35), (16, 35)],
        [(36, 22), (52, 32), (36, 42)]])),
    'C': ('双 V 递进', combine(
        stroke_fn([(18, 22), (30, 32), (18, 42)], 7.0),
        stroke_fn([(34, 22), (46, 32), (34, 42)], 7.0))),
    'D': ('实心圆角三角', poly_fn([[(22, 20), (52, 32), (22, 44)]], ss=6)),
    'E': ('细线箭头', combine(
        stroke_fn([(16, 32), (42, 32)], 3.5),
        stroke_fn([(36, 24), (50, 32), (36, 40)], 3.5))),
}


def chunk(t, data):
    c = t + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)


def write_png_rgb(path, w, h, rows):
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for (r, g, b) in row:
            raw += bytes([r, g, b])
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)


def write_png_rgba(path, w, h, rows):
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for (r, g, b, a) in row:
            raw += bytes([r, g, b, int(a * 255 + 0.5)])
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)


for key, (name, fn) in VARIANTS.items():
    img = [[(255, 255, 255, fn(x, y)) for x in range(S)] for y in range(S)]

    rows = []
    for y in range(S):
        row = []
        for x in range(S):
            r, g, b, a = img[y][x]
            bg = (70, 70, 74) if (x + y) % 2 == 0 else (52, 52, 56)
            row.append((int(bg[0] + (r - bg[0]) * a),
                        int(bg[1] + (g - bg[1]) * a),
                        int(bg[2] + (b - bg[2]) * a)))
        rows.append(row)
    write_png_rgb('_temp/_arrow_%s_detail.png' % key, S, S, rows)

    small = [[0.0] * 12 for _ in range(12)]
    for y in range(12):
        for x in range(12):
            x0, x1 = x * S / 12.0, (x + 1) * S / 12.0
            y0, y1 = y * S / 12.0, (y + 1) * S / 12.0
            n = 0
            acc = 0.0
            yy = y0
            while yy < y1:
                xx = x0
                while xx < x1:
                    xi = min(S - 1, int(xx))
                    yi = min(S - 1, int(yy))
                    acc += img[yi][xi][3]
                    n += 1
                    xx += 1.0
                yy += 1.0
            small[y][x] = acc / n

    up = []
    for Y in range(96):
        row = []
        for X in range(96):
            a = small[Y // 8][X // 8]
            row.append((GOLD[0], GOLD[1], GOLD[2], a))
        up.append(row)
    write_png_rgba('_temp/_arrow_%s_px12.png' % key, 96, 96, up)
    print('variant %s %s done' % (key, name))
