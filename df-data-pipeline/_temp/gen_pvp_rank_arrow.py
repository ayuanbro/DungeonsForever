import math
import struct
import zlib

S = 64
W = 7.0
V1 = [(18.0, 22.0), (30.0, 32.0), (18.0, 42.0)]
V2 = [(34.0, 22.0), (46.0, 32.0), (34.0, 42.0)]


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def poly_dist(px, py, pts):
    return min(seg_dist(px, py, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
               for i in range(len(pts) - 1))


img = [[(255, 255, 255, 0.0) for _ in range(S)] for _ in range(S)]
for y in range(S):
    for x in range(S):
        d = min(poly_dist(x + 0.5, y + 0.5, V1), poly_dist(x + 0.5, y + 0.5, V2))
        a = max(0.0, min(1.0, W / 2 + 0.5 - d))
        img[y][x] = (255, 255, 255, a)

raw = bytearray()
for row in img:
    for (r, g, b, a) in row:
        raw += bytes([b, g, r, int(a * 255 + 0.5)])
hdr = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, S, S, 32, 0x28)
open('Media/PvPRankArrow.tga', 'wb').write(hdr + bytes(raw))
print('wrote Media/PvPRankArrow.tga')

scale = 6
H = W2 = S * scale
raw2 = bytearray()
for Y in range(H):
    raw2.append(0)
    for X in range(W2):
        x, y = X // scale, Y // scale
        r, g, b, a = img[y][x]
        bg = (70, 70, 74) if (x + y) % 2 == 0 else (52, 52, 56)
        raw2 += bytes([int(bg[0] + (r - bg[0]) * a),
                       int(bg[1] + (g - bg[1]) * a),
                       int(bg[2] + (b - bg[2]) * a)])


def chunk(t, data):
    c = t + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)


png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', W2, H, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(bytes(raw2), 6))
png += chunk(b'IEND', b'')
open('_temp/_pvp_rank_arrow_preview.png', 'wb').write(png)
print('preview _temp/_pvp_rank_arrow_preview.png')
