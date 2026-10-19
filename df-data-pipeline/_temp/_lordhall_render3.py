# -*- coding: utf-8 -*-
"""领主大厅 · 画师风格全重绘 v3c（对齐修复版）。

修复：
  - 剪影去噪（小组件剔除）后重算 bbox，参数化建筑与剪影共用同一变换
  - 补画顶部圆形大厅（齿轮环 + 圆形地板 + 中央平台）、主厅中央平台
  - 光晕裁剪进地板范围；岩壁暗斑改噪声纹理；岩壁衬块改软性不规则 blob
  - 晶簇阈值 V>=120；黑铁洞窟多边形加抖动
输出: _temp/lordhall_map_v3.png
"""
import math
import os
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LAY = r"C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-09-30T02-37-51-596Z-23b3b073.jpg"
CLEAN = os.path.join(HERE, "parchment_clean.png")
OUT = os.path.join(HERE, "lordhall_map_v3.png")

CW, CH = 1002, 668
K = 1666 / 1080          # 实测图 fullres/display

ROCK    = (104, 84, 50)
ROCK_D  = (86, 68, 38)
WALL    = (140, 112, 74)
WALL_L  = (206, 182, 136)
FLOOR   = (219, 199, 150)
FLOOR_D = (170, 148, 102)
EDGE    = (110, 86, 52)
CRYS_L  = (176, 190, 205)
CRYS_D  = (127, 141, 162)
CRYS_O  = (48, 54, 66)
GLOW    = (248, 220, 110)
ROOFR   = (104, 91, 58)
ICON_D  = (66, 54, 32)
ICON_L  = (196, 174, 128)
DOOR_D  = (92, 30, 24)
DOOR_L  = (178, 58, 42)
GOLD    = (232, 196, 100)

# ================= 1. 实测图：剪影 + 晶簇位点 =================
im = Image.open(LAY).convert("RGB")
a = np.asarray(im).astype(np.int16)
R_, G_, B_ = a[..., 0], a[..., 1], a[..., 2]
V = a.max(-1)
neutral = (np.abs(R_ - G_) < 16) & (np.abs(G_ - B_) < 16)
bg = neutral & (V > 95) & (V < 140)
white = neutral & (V >= 120)
d_floor = (R_ - 95) ** 2 + (G_ - 72) ** 2 + (B_ - 50) ** 2
d_rock = (R_ - 40) ** 2 + (G_ - 42) ** 2 + (B_ - 32) ** 2
warmish = (R_ - G_ >= 8) & (R_ - B_ >= 14)
floor0 = (d_floor < d_rock) & warmish & (V >= 42) & ~bg & ~white
rock0 = ~bg & ~floor0 & ~white
floor0 = cv2.medianBlur((floor0 * 255).astype(np.uint8), 5) > 127
rock0 = cv2.medianBlur((rock0 * 255).astype(np.uint8), 5) > 127
k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
floor0 = cv2.morphologyEx(floor0.astype(np.uint8), cv2.MORPH_OPEN, k3) > 0
rock0 = cv2.morphologyEx(rock0.astype(np.uint8), cv2.MORPH_OPEN, k3) > 0
content0 = rock0 | floor0
sil0 = cv2.morphologyEx((content0 * 255).astype(np.uint8), cv2.MORPH_CLOSE,
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
cnts, _ = cv2.findContours(sil0, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
sil0 = np.zeros_like(sil0)
for c in cnts:
    if cv2.contourArea(c) >= 2500:
        cv2.drawContours(sil0, [c], -1, 255, -1)
sil0 = cv2.morphologyEx(sil0, cv2.MORPH_CLOSE,
                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
sil0 = cv2.morphologyEx(sil0, cv2.MORPH_OPEN,
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
sil0 = sil0 > 0

rows = np.where(sil0.sum(1) > 8)[0]
cols = np.where(sil0.sum(0) > 8)[0]
fy0, fy1 = rows.min(), rows.max()
fx0, fx1 = cols.min(), cols.max()
# 统一变换：display 坐标 -> canvas
DX0, DY0 = fx0 / K, fy0 / K
DX1, DY1 = fx1 / K, fy1 / K
DS = min(922 / (DX1 - DX0), 534 / (DY1 - DY0))
DW, DH = (DX1 - DX0) * DS, (DY1 - DY0) * DS
OX = (40 + 962) / 2 - DW / 2
OY = 118
print("display bbox (%.0f,%.0f)-(%.0f,%.0f) scale %.3f off (%.0f,%.0f)"
      % (DX0, DY0, DX1, DY1, DS, OX, OY))


def T(x, y):
    return (OX + (x - DX0) * DS, OY + (y - DY0) * DS)


def sil_to_canvas():
    mm = (sil0[fy0:fy1 + 1, fx0:fx1 + 1] * 255).astype(np.uint8)
    w, h = int(DW), int(DH)
    ox, oy = int(OX), int(OY)
    mm = cv2.resize(mm, (w, h), interpolation=cv2.INTER_AREA) > 100
    full = np.zeros((CH, CW), bool)
    full[oy:oy + h, ox:ox + w] = mm
    return full


sil_m = sil_to_canvas()

# 晶簇位点
white0 = (white & ~bg)
white0 = cv2.morphologyEx((white0 * 255).astype(np.uint8),
                          cv2.MORPH_OPEN,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
n, lab, stats, _ = cv2.connectedComponentsWithStats((white0 * 255).astype(np.uint8))
cry_sites = []
for i in range(1, n):
    if stats[i, cv2.CC_STAT_AREA] >= 60:
        x = (stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] / 2) / K
        y = (stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2) / K
        cry_sites.append((x, y, stats[i, cv2.CC_STAT_AREA]))
# 邻近聚簇（70px 网格）
clusters = []
for x, y, ar in sorted(cry_sites, key=lambda t: -t[2]):
    for c in clusters:
        if abs(c['x'] - x) < 70 and abs(c['y'] - y) < 70:
            c['pts'].append((x, y, ar))
            c['x'] = sum(p[0] for p in c['pts']) / len(c['pts'])
            c['y'] = sum(p[1] for p in c['pts']) / len(c['pts'])
            c['area'] += ar
            break
    else:
        clusters.append({'x': x, 'y': y, 'area': ar, 'pts': [(x, y, ar)]})
print("crystal clusters", len(clusters))

# ================= 2. 参数化建筑（display 坐标） =================
masses = [
    (500, 226, 551, 434),      # 顶部竖廊
    (468, 428, 588, 522),      # 中楼
    (455, 524, 595, 656),      # 主厅
    (424, 566, 462, 612),      # 左连接廊
    (588, 566, 662, 612),      # 右连接廊
    (258, 516, 396, 658),      # 左翼
    (654, 516, 792, 658),      # 右翼
    (478, 656, 578, 770),      # 南楼
    (478, 768, 578, 800),      # 底部结构
]
floors = [
    (510, 230, 541, 431),
    (478, 438, 578, 512),
    (465, 534, 585, 646),
    (429, 573, 457, 605),
    (593, 573, 656, 605),
    (268, 566, 388, 612),
    (664, 566, 784, 612),
    (514, 662, 536, 764),
    (492, 774, 562, 796),
]
wing_rooms = []
for wx0 in (272, 306, 340, 374):
    wing_rooms += [(wx0, 522, wx0 + 26, 562), (wx0, 616, wx0 + 26, 652)]
for wx0 in (668, 702, 736, 770):
    wing_rooms += [(wx0, 522, wx0 + 26, 562), (wx0, 616, wx0 + 26, 652)]
south_rooms = [(484, 670, 510, 752), (542, 670, 568, 752)]
mid_rooms = [(476, 436, 502, 462), (554, 436, 580, 462),
             (476, 478, 502, 504), (554, 478, 580, 504)]
_cave_raw = [(588, 436), (616, 414), (652, 402), (700, 396), (752, 400),
             (800, 414), (830, 440), (836, 470), (820, 496), (786, 512),
             (744, 518), (704, 512), (664, 502), (624, 488), (596, 466),
             (586, 450)]
_cx = sum(p[0] for p in _cave_raw) / len(_cave_raw)
_cy = sum(p[1] for p in _cave_raw) / len(_cave_raw)
cave_pts = [(_cx + (x - _cx) * 0.86, _cy + (y - _cy) * 0.86) for x, y in _cave_raw]
cave_neck = (726, 502, 760, 532)
doors = [
    (468, 448, 'v'), (468, 472, 'v'), (468, 496, 'v'),
    (588, 448, 'v'), (588, 472, 'v'), (588, 496, 'v'),
    (498, 524, 'h'), (552, 524, 'h'),
    (424, 580, 'v'), (662, 580, 'v'),
]
stairs = [(510, 240, 541, 262), (510, 300, 541, 322),
          (514, 690, 536, 712), (514, 730, 536, 752)]
trees = [(742, 436), (782, 448), (758, 470)]
spiral_at = (527, 794)
glows = [((525, 588), 110, 1.5), ((525, 185), 46, 0.8), ((527, 790), 36, 0.7),
         ((720, 455), 60, 0.55)]
# 翼楼/底部背后的岩壁衬块（blob 中心集）
rock_blobs = [
    [(280, 560, 95), (350, 590, 105), (300, 650, 90), (380, 640, 85)],
    [(740, 560, 95), (680, 590, 100), (760, 650, 90), (660, 640, 85)],
    [(515, 700, 85), (545, 760, 80), (500, 800, 75)],
    [(520, 450, 110), (580, 470, 90), (470, 480, 80)],
]

# ================= 3. 绘制 =================
def new_layer():
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def soft(img, rad):
    img.putalpha(img.split()[3].filter(ImageFilter.GaussianBlur(rad)))
    return img


base = Image.open(CLEAN).convert("RGB")

# 3a. 岩壁衬块（软 blob）
rockL, rd = new_layer()
for blob in rock_blobs:
    for cx, cy, r in blob:
        px, py = T(cx, cy)
        rr = r * DS * 1.15
        rd.ellipse([px - rr, py - rr * 0.8, px + rr, py + rr * 0.8], fill=ROCK + (255,))
rockL = soft(rockL, 10)

# 3b. 岩壁剪影（减去建筑）
sub = Image.new("L", (CW, CH), 0)
sd = ImageDraw.Draw(sub)
for m in masses:
    sd.rectangle([*R(*m)] if False else [*T(m[0], m[1]), *T(m[2], m[3])], fill=255)
sub = sub.filter(ImageFilter.MaxFilter(9))
sil_arr = np.zeros((CH, CW), np.uint8)
sil_arr[sil_m] = 255
sil_arr[np.asarray(sub) > 0] = 0
silL = Image.new("RGBA", (CW, CH), ROCK + (0,))
alpha = Image.fromarray(sil_arr).filter(ImageFilter.GaussianBlur(2.2))
silL.putalpha(alpha)
# 岩壁斑驳（亮+暗双向软噪声）
blotch = np.random.default_rng(41).random((CH // 28 + 2, CW // 28 + 2))
blotch = np.asarray(Image.fromarray((blotch * 255).astype(np.uint8)).resize(
    (CW, CH), Image.BILINEAR)).astype(np.float32) / 255
blotch2 = np.random.default_rng(43).random((CH // 55 + 2, CW // 55 + 2))
blotch2 = np.asarray(Image.fromarray((blotch2 * 255).astype(np.uint8)).resize(
    (CW, CH), Image.BILINEAR)).astype(np.float32) / 255
mott = blotch * 0.5 + blotch2 * 0.5
mott_np = np.zeros((CH, CW, 4), np.uint8)
light_m = (mott > 0.60) & (sil_arr > 0)
dark_m = (mott < 0.34) & (sil_arr > 0)
mott_np[light_m, 0] = 134; mott_np[light_m, 1] = 110; mott_np[light_m, 2] = 70
mott_np[dark_m, 0] = 80;  mott_np[dark_m, 1] = 63;  mott_np[dark_m, 2] = 34
mott_np[..., 3] = (light_m * 55 + dark_m * 80).astype(np.uint8)
mott_img = Image.fromarray(mott_np)
mott_img.putalpha(Image.fromarray(mott_np[..., 3]).filter(ImageFilter.GaussianBlur(3)))
silL.alpha_composite(mott_img)

art = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
art.alpha_composite(rockL)
art.alpha_composite(silL)

# 3c. 圆形大厅（顶部）
circL, cd = new_layer()
cx, cy = T(525, 185)
r_out, r_in, r_floor = 50 * DS, 40 * DS, 33 * DS
cd.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=WALL + (255,))
cd.ellipse([cx - r_floor, cy - r_floor, cx + r_floor, cy + r_floor], fill=FLOOR + (255,))
# 齿轮刻痕
for t in range(16):
    ang = t * math.pi / 8
    x1 = cx + (r_out - 2) * math.cos(ang)
    y1 = cy + (r_out - 2) * math.sin(ang)
    x2 = cx + r_out * math.cos(ang)
    y2 = cy + r_out * math.sin(ang)
    cd.line([x1, y1, x2, y2], fill=WALL_L + (200,), width=2)
# 中央平台
cd.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=ROOFR + (255,), outline=GOLD + (255,))
circL = soft(circL, 0.6)
art.alpha_composite(circL)

# 3d. 墙体块
wallL, wd = new_layer()
for m in masses:
    wd.rectangle([*T(m[0], m[1]), *T(m[2], m[3])], fill=WALL + (255,))
olL, od = new_layer()
for m in masses:
    od.rectangle([*T(m[0], m[1]), *T(m[2], m[3])], outline=WALL_L + (210,), width=2)
olL = soft(olL, 0.9)
wallL.alpha_composite(olL)
wallL = soft(wallL, 0.7)
art.alpha_composite(wallL)

# 3e. 走道地板 + 晕影
haloL, hd = new_layer()
for f in floors:
    hd.rectangle([*T(f[0], f[1]), *T(f[2], f[3])], outline=EDGE + (160,), width=4)
hd.polygon([T(x, y) for x, y in cave_pts], outline=EDGE + (160,), width=4)
haloL = soft(haloL, 2.2)
floorL, fd = new_layer()
for f in floors:
    fd.rectangle([*T(f[0], f[1]), *T(f[2], f[3])], fill=FLOOR + (255,))
fd.polygon([T(x, y) for x, y in cave_pts], fill=(178, 158, 116, 255))
fd.rectangle([*T(cave_neck[0], cave_neck[1]), *T(cave_neck[2], cave_neck[3])],
             fill=FLOOR + (255,))
floorL = soft(floorL, 0.5)
art.alpha_composite(haloL)
art.alpha_composite(floorL)
floor_alpha = np.asarray(floorL.split()[3]).astype(np.float32) / 255

# 3f. 主厅中央平台
platL, pd = new_layer()
c = [*T(503, 560), *T(548, 612)]
pd.rectangle(c, fill=ROOFR + (255,), outline=WALL_L + (200,), width=2)
c2 = [*T(514, 572), *T(537, 596)]
pd.rectangle(c2, fill=(204, 176, 96, 255), outline=ICON_D + (255,), width=2)
art.alpha_composite(platL)

# 3g. 光晕（裁剪进地板）
glowL, gd = new_layer()
for (gcx, gcy), r, k in glows:
    gx, gy = T(gcx, gcy)
    gr = r * DS * 1.4
    for i in range(int(gr), 0, -2):
        al = int(235 * k * (i / gr) ** 2)
        gd.ellipse([gx - i, gy - i, gx + i, gy + i], fill=GLOW + (al,))
ga = np.asarray(glowL).astype(np.float32)
ga[..., 3] = np.minimum(ga[..., 3], floor_alpha * 255)
glowL = Image.fromarray(ga.astype(np.uint8))
art.alpha_composite(glowL)

# 3h. 房间
roomL, rd2 = new_layer()
for rm in wing_rooms + south_rooms + mid_rooms:
    rc = [*T(rm[0], rm[1]), *T(rm[2], rm[3])]
    rd2.rectangle(rc, fill=ROOFR + (255,), outline=WALL_L + (190,), width=1)
    x0, y0, x1, y1 = rc
    iw, ih = (x1 - x0) * 0.42, (y1 - y0) * 0.44
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rd2.rectangle([cx - iw / 2, cy - ih / 2, cx + iw / 2, cy + ih / 2],
                  fill=ICON_L + (255,), outline=ICON_D + (255,), width=2)
art.alpha_composite(roomL)

# 3i. 楼梯
stL, sd2 = new_layer()
for x0, y0, x1, y1 in stairs:
    c = [*T(x0, y0), *T(x1, y1)]
    yy, flip = c[1], False
    while yy < c[3]:
        col = FLOOR_D if not flip else (232, 214, 168)
        sd2.rectangle([c[0], yy, c[2], min(yy + 3.4, c[3])], fill=col + (255,))
        yy += 3.4
        flip = not flip
art.alpha_composite(stL)

# 3j. 红门
drL, dd2 = new_layer()
for cx, cy, orient in doors:
    px, py = T(cx, cy)
    if orient == 'v':
        box = [px - 3.4, py - 6.5, px + 3.4, py + 6.5]
    else:
        box = [px - 6.5, py - 3.4, px + 6.5, py + 3.4]
    dd2.rectangle(box, fill=DOOR_D + (255,))
    dd2.rectangle([box[0] + 1.4, box[1] + 1.4, box[2] - 1.4, box[3] - 1.4],
                  fill=DOOR_L + (255,))
art.alpha_composite(drL)

# 3k. 树
trL, td = new_layer()
for cx, cy in trees:
    px, py = T(cx, cy)
    r = 7 * DS * 1.3
    td.ellipse([px - r, py - r * 1.25, px + r, py + r * 0.9], fill=(84, 88, 52, 255))
    td.ellipse([px - r * 0.55, py - r * 1.05, px + r * 0.35, py - r * 0.1],
               fill=(104, 108, 62, 255))
    td.rectangle([px - 1.2, py, px + 1.2, py + r * 0.8], fill=(58, 44, 26, 255))
art.alpha_composite(trL)

# 3l. 螺旋入口
sx, sy = T(*spiral_at)
spL, spd = new_layer()
spd.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], outline=GOLD + (255,), width=3)
pts = [(sx + (1.0 + t * 0.85) * math.cos(t), sy + (1.0 + t * 0.85) * math.sin(t))
       for t in np.linspace(0, 3.6 * math.pi, 60)]
spd.line(pts, fill=GOLD + (255,), width=2)
art.alpha_composite(spL)

# ================= 4. 合成 + 纹理 =================
base_a = np.asarray(base).astype(np.float32)
aS = np.asarray(art).astype(np.float32)
al = aS[..., 3:4] / 255
comp = base_a * (1 - al) + aS[..., :3] * al

rock_m = (sil_arr > 0).copy()
yy, xx = np.mgrid[0:CH, 0:CW]
for blob in rock_blobs:
    for cx, cy, r in blob:
        px, py = T(cx, cy)
        rr = r * DS * 1.15
        rock_m |= ((yy - py) ** 2 / (rr * 0.8) ** 2 + (xx - px) ** 2 / rr ** 2) < 1
floor_m = al[..., 0] > 0


def blotch2(shape, cell, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, shape[0] // cell), max(2, shape[1] // cell))).astype(np.float32)
    im2 = Image.fromarray((small * 255).astype(np.uint8)).resize(
        (shape[1], shape[0]), Image.BILINEAR)
    return np.asarray(im2).astype(np.float32) / 255 - 0.5


tex_r = blotch2((CH, CW), 70, 41)[..., None] * 24
tex_f = blotch2((CH, CW), 110, 42)[..., None] * 10
comp = comp + tex_r * rock_m[..., None] + tex_f * (floor_m & ~rock_m)[..., None]
comp = np.clip(comp, 0, 255)
img1 = Image.fromarray(comp.astype(np.uint8)).convert("RGBA")

# ================= 5. 晶簇 =================
crystal_chains = [
    [(238, 282), (272, 318), (318, 352), (372, 382), (436, 408)],
    [(560, 300), (600, 330), (648, 352), (706, 352), (764, 322), (800, 296)],
]


def draw_shard(dc, gx, gy, ang, ln, wdt):
    ca, sa = math.cos(ang), math.sin(ang)
    shape = [(-ln / 2, 0), (-ln / 4, -wdt / 2), (ln / 4, -wdt / 2),
             (ln / 2, 0), (ln / 4, wdt / 2), (-ln / 4, wdt / 2)]
    rp = [(gx + px * ca - py * sa, gy + px * sa + py * ca) for px, py in shape]
    dc.polygon(rp, fill=CRYS_D + (255,), outline=CRYS_O + (255,))
    rp2 = [(gx + px * ca * 0.6 - py * sa * 0.6 - 1.2,
            gy + px * sa * 0.6 + py * ca * 0.6 - 1.2) for px, py in shape]
    dc.polygon(rp2, fill=CRYS_L + (235,))


dc = ImageDraw.Draw(img1)
rng = np.random.default_rng(55)
for chain in crystal_chains:
    for i in range(len(chain) - 1):
        x0, y0 = chain[i]
        x1, y1 = chain[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        nsh = max(2, int(seg / 16))
        base_ang = math.atan2(y1 - y0, x1 - x0)
        for k in range(nsh):
            t = (k + rng.uniform(0.15, 0.85)) / nsh
            bx = x0 + (x1 - x0) * t + rng.normal(0, 5)
            by = y0 + (y1 - y0) * t + rng.normal(0, 4)
            gx, gy = T(bx, by)
            ang = base_ang + rng.normal(0, 0.55) + (math.pi / 2 if rng.random() < 0.5 else 0)
            draw_shard(dc, gx, gy, ang, rng.uniform(9, 18), rng.uniform(4, 8))
for c in clusters:
    nsh = max(3, min(8, int(c['area'] / 150)))
    for k in range(nsh):
        gx, gy = T(c['x'] + rng.normal(0, 14), c['y'] + rng.normal(0, 9))
        draw_shard(dc, gx, gy, rng.random() * math.pi,
                   rng.uniform(8, 16), rng.uniform(4, 7.5))

# ================= 6. 横幅标题 =================
img1 = img1.convert("RGB")
d2 = ImageDraw.Draw(img1)
font = None
for fp in ("C:/Windows/Fonts/simli.ttf", "C:/Windows/Fonts/SIMLI.TTF",
           "C:/Windows/Fonts/simkai.ttf"):
    if os.path.exists(fp):
        font = ImageFont.truetype(fp, 34)
        break
title = "领 主 大 厅"
tw = d2.textlength(title, font=font)
tx0 = 535 - tw / 2
d2.text((tx0 + 1.5, 56 + 1.5), title, font=font, fill=(62, 40, 14))
d2.text((tx0, 56), title, font=font, fill=GOLD)

img1.save(OUT)
print("saved", OUT)
