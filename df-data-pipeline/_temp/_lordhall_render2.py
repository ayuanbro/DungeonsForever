# -*- coding: utf-8 -*-
"""领主大厅 · 经典羊皮纸风格副本地图 v2：矢量轮廓 + 2x 超采样。

对 v1 的修正：
  - 轮廓改用 cv2 提取多边形（岩壁平滑+抖动做手绘感，建筑保持直墙），2x 超采样后缩小，消灭锯齿；
  - 色板整体调暖，贴近怒焰裂谷；
  - 岩壁加内阴影带 + 斑驳纹理，地板加细节纹样（实测图里的深色方格）；
  - 底部建筑群的院落空隙收进岩壁大面，不再悬空。
输出：
  _temp/lordhall_map_v2.png      1002x668 成图
  _temp/lordhall_v2_debug.png    掩膜调试图
"""
import os
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LAY = r"C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-09-30T02-37-51-596Z-23b3b073.jpg"
CLEAN = os.path.join(HERE, "parchment_clean.png")
OUT = os.path.join(HERE, "lordhall_map_v2.png")
DBG = os.path.join(HERE, "lordhall_v2_debug.png")
FONT = "C:/Windows/Fonts/simkai.ttf"

CW, CH = 1002, 668
SS = 2                       # 超采样倍率
SW, SH = CW * SS, CH * SS
RNG = np.random.default_rng(7)

# 怒焰裂谷风格色板（整体调暖）
ROCK = (139, 97, 36)
ROCK_D = (110, 74, 26)
ROCK_L = (160, 118, 54)
FLOOR = (210, 193, 136)
FLOOR_D = (176, 158, 104)     # 地板细节纹样
INNER = (104, 70, 24)         # 岩壁内阴影
OUTL = (56, 36, 12)


def chaikin(pts, iters=2):
    for _ in range(iters):
        out = []
        n = len(pts)
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            out.append(p0 * 0.75 + p1 * 0.25)
            out.append(p0 * 0.25 + p1 * 0.75)
        pts = np.array(out)
    return pts


def jitter(pts, amp, cell=6, seed=0):
    """沿法线的低频抖动（沿点序平滑）。"""
    if amp <= 0 or len(pts) < 8:
        return pts
    r = np.random.default_rng(seed + len(pts))
    off = r.standard_normal(len(pts)).astype(np.float32)
    k = cell
    ker = np.ones(k) / k
    off = np.convolve(off, ker, mode="same")
    off = off / (np.abs(off).max() + 1e-6) * amp
    # 法线
    d = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    n = np.stack([d[:, 1], -d[:, 0]], 1)
    n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-6)
    return pts + n * off[:, None]


def poly_area(pts):
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


# ---------- 1. 分类（全分辨率） ----------
im = Image.open(LAY).convert("RGB")
a = np.asarray(im).astype(np.int16)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
V = a.max(-1)
neutral = (np.abs(R - G) < 16) & (np.abs(G - B) < 16)
bg = neutral & (V > 95) & (V < 140)
white = neutral & (V >= 140)
# RGB 距离分类：靠近建筑棕 (95,72,50) 还是岩壁绿 (40,42,32)
d_floor = (R - 95) ** 2 + (G - 72) ** 2 + (B - 50) ** 2
d_rock = (R - 40) ** 2 + (G - 42) ** 2 + (B - 32) ** 2
warmish = (R - G >= 8) & (R - B >= 14)
floor0 = (d_floor < d_rock) & warmish & (V >= 42) & ~bg & ~white
rock0 = ~bg & ~floor0 & ~white
detail0 = floor0 & (V < 85)                 # 建筑内的深色纹样/墙影

floor0 = floor0 & ~rock0

# 形态学：中值去噪 + 小开
floor0 = cv2.medianBlur((floor0 * 255).astype(np.uint8), 5) > 127
rock0 = cv2.medianBlur((rock0 * 255).astype(np.uint8), 5) > 127
k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
floor0 = cv2.morphologyEx(floor0.astype(np.uint8), cv2.MORPH_OPEN, k3) > 0
rock0 = cv2.morphologyEx(rock0.astype(np.uint8), cv2.MORPH_OPEN, k3) > 0
detail0 = (detail0 & floor0)
detail0 = cv2.morphologyEx((detail0 * 255).astype(np.uint8),
                           cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0

content0 = rock0 | floor0
# 剪影：闭运算桥接小缝隙 + 填洞（取外轮廓即可）
sil0 = cv2.morphologyEx((content0 * 255).astype(np.uint8), cv2.MORPH_CLOSE,
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
cnts, _ = cv2.findContours(sil0, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
sil0 = np.zeros_like(sil0)
cv2.drawContours(sil0, cnts, -1, 255, -1)
sil0 = sil0 > 0

# 地板：闭小缝、去小斑块
floor0 = cv2.morphologyEx((floor0 * 255).astype(np.uint8), cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
floor0 = floor0 & sil0
n, lab, stats, _ = cv2.connectedComponentsWithStats((floor0 * 255).astype(np.uint8))
floor0 = np.zeros_like(floor0)
for i in range(1, n):
    if stats[i, cv2.CC_STAT_AREA] >= 500:
        floor0[lab == i] = True
detail0 &= floor0
n, lab, stats, _ = cv2.connectedComponentsWithStats((detail0 * 255).astype(np.uint8))
detail0 = np.zeros_like(detail0)
for i in range(1, n):
    if stats[i, cv2.CC_STAT_AREA] >= 150:
        detail0[lab == i] = True

# 白色高光（瀑布/晶簇，画在岩壁上的浅色斑）
white0 = (white & sil0 & ~floor0)
white0 = cv2.morphologyEx((white0 * 255).astype(np.uint8), cv2.MORPH_OPEN, k3) > 0
n, lab, stats, _ = cv2.connectedComponentsWithStats((white0 * 255).astype(np.uint8))
white0 = np.zeros_like(white0)
for i in range(1, n):
    if stats[i, cv2.CC_STAT_AREA] >= 400:
        white0[lab == i] = True

print("fullres  sil %.3f floor %.3f detail %.4f white %.4f"
      % (sil0.mean(), floor0.mean(), detail0.mean(), white0.mean()))

# ---------- 2. 摆到画布 ----------
rows = np.where(sil0.sum(1) > 8)[0]
cols = np.where(sil0.sum(0) > 8)[0]
y0, y1 = rows.min(), rows.max()
x0, x1 = cols.min(), cols.max()
print("content bbox", x0, x1, y0, y1)

TX0, TY0, TX1, TY1 = 40, 118, 962, 652
s = min((TX1 - TX0) / (x1 - x0 + 1), (TY1 - TY0) / (y1 - y0 + 1))
W = int((x1 - x0 + 1) * s)
H = int((y1 - y0 + 1) * s)
OX = (TX0 + TX1 - W) // 2
OY = TY0 + (TY1 - TY0 - H) // 2
print("scale %.3f size %dx%d off (%d,%d)" % (s, W, H, OX, OY))


def tx(pts):
    """全分辨率点 -> SS 画布点。cv2 轮廓点是 (x=col, y=row)，PIL 也按 (x,y)。"""
    p = (pts[:, 0, :].astype(np.float32) if pts.ndim == 3 else pts.astype(np.float32))
    p = (p - [x0, y0]) * (s * SS) + np.array([OX * SS, OY * SS], np.float32)
    return p


def mask_to_canvas(m):
    mm = (m[y0:y1 + 1, x0:x1 + 1] * 255).astype(np.uint8)
    mm = cv2.resize(mm, (W, H), interpolation=cv2.INTER_AREA) > 100
    full = np.zeros((CH, CW), bool)
    full[OY:OY + H, OX:OX + W] = mm
    return full


def contours_of(m, min_area, eps, smooth, jamp, seed):
    """掩膜 -> 变换到 SS 画布的多边形列表（含洞）。"""
    cnts, hier = cv2.findContours((m * 255).astype(np.uint8),
                                  cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    if hier is None:
        return polys
    hier = hier[0]
    for i, c in enumerate(cnts):
        if cv2.contourArea(c) < min_area:
            continue
        ap = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(np.float32)
        if smooth:
            ap = chaikin(ap, smooth)
        ap = jitter(ap, jamp, seed=seed + i)
        polys.append((tx(ap), hier[i][3]))  # (点, 父索引)
    return polys


sil_polys = contours_of(sil0, 1500, 6, 2, 3.0, 100)          # 剪影：平滑+抖动
floor_polys = contours_of(floor0, 900, 2.5, 0, 1.2, 200)     # 建筑：直墙微抖
detail_polys = contours_of(detail0, 60, 2.0, 0, 0.8, 300)
white_polys = contours_of(white0, 300, 5, 2, 2.5, 400)
print("polys  sil %d floor %d detail %d white %d"
      % (len(sil_polys), len(floor_polys), len(detail_polys), len(white_polys)))

# ---------- 3. SS 画布渲染 ----------
art = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
d = ImageDraw.Draw(art)

# 3a. 岩壁剪影（外轮廓填充，洞由地板覆盖）
sil_ext = [p for p, par in sil_polys if par < 0]
sil_holes = [p for p, par in sil_polys if par >= 0]
for p in sil_ext:
    d.polygon([tuple(q) for q in p], fill=ROCK + (255,))

# 3b. 剪影内阴影带
band = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
bd = ImageDraw.Draw(band)
for p in sil_ext:
    pp = [tuple(q) for q in p]
    bd.line(pp + [pp[0]], fill=INNER + (150,), width=16 * SS // 2, joint="curve")
# 只留剪影内部
sil_mask = Image.new("L", (SW, SH), 0)
sd = ImageDraw.Draw(sil_mask)
for p in sil_ext:
    sd.polygon([tuple(q) for q in p], fill=255)
band.putalpha(Image.composite(band.split()[3], Image.new("L", (SW, SH), 0),
                              sil_mask.filter(ImageFilter.MinFilter(5))))
art.alpha_composite(band)

# 3c. 岩壁亮斑（瀑布/晶簇）
for p, par in white_polys:
    d.polygon([tuple(q) for q in p], fill=(196, 172, 120, 90))

# 3d. 地板（含洞：洞不画，露出岩壁）
floor_ext = [p for p, par in floor_polys if par < 0]
floor_holes = [p for p, par in floor_polys if par >= 0]
for p in floor_ext:
    d.polygon([tuple(q) for q in p], fill=FLOOR + (255,))
for p in floor_holes:
    d.polygon([tuple(q) for q in p], fill=ROCK + (255,))

# 3e. 地板细节纹样（实测图里的深色方格）
for p, par in detail_polys:
    d.polygon([tuple(q) for q in p], fill=FLOOR_D + (170,))

# 3f. 地板描边
for p in floor_ext:
    pp = [tuple(q) for q in p]
    d.line(pp + [pp[0]], fill=OUTL + (255,), width=5 * SS, joint="curve")
for p in floor_holes:
    pp = [tuple(q) for q in p]
    d.line(pp + [pp[0]], fill=OUTL + (255,), width=4 * SS, joint="curve")

# 3g. 剪影描边
for p in sil_ext:
    pp = [tuple(q) for q in p]
    d.line(pp + [pp[0]], fill=OUTL + (255,), width=7 * SS, joint="curve")
for p in sil_holes:
    pp = [tuple(q) for q in p]
    d.line(pp + [pp[0]], fill=OUTL + (255,), width=5 * SS, joint="curve")

# ---------- 4. 缩小 + 纹理 ----------
art_small = art.resize((CW, CH), Image.LANCZOS)
base = np.asarray(Image.open(CLEAN).convert("RGB")).astype(np.float32)
aS = np.asarray(art_small).astype(np.float32)
al = aS[..., 3:4] / 255
comp = base * (1 - al) + aS[..., :3] * al

# 岩壁/地板掩膜（画布尺度，供纹理用）
sil_m = mask_to_canvas(sil0)
floor_m = mask_to_canvas(floor0)
rock_m = sil_m & ~floor_m


def blotch(shape, cell, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, shape[0] // cell), max(2, shape[1] // cell))).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize(
        (shape[1], shape[0]), Image.BILINEAR)
    return np.asarray(img).astype(np.float32) / 255 - 0.5


tex_r = blotch((CH, CW), 85, 41)[..., None] * 30 + (RNG.random((CH, CW, 1)) - 0.5) * 8
tex_f = blotch((CH, CW), 130, 42)[..., None] * 10 + (RNG.random((CH, CW, 1)) - 0.5) * 5
drawn = (al[..., 0] > 0)[..., None]
comp = comp + tex_r * rock_m[..., None] * drawn + tex_f * floor_m[..., None] * drawn
comp = np.clip(comp, 0, 255)

out_img = Image.fromarray(comp.astype(np.uint8))

# ---------- 5. 横幅标题 ----------
d2 = ImageDraw.Draw(out_img)
font = ImageFont.truetype(FONT, 30)
title = "领 主 大 厅"
tw = d2.textlength(title, font=font)
d2.text((512 - tw / 2, 58), title, font=font, fill=(96, 62, 22))

out_img.save(OUT)
print("saved", OUT, out_img.size)

dbg = np.zeros((CH, CW, 3), np.uint8)
dbg[sil_m] = (120, 80, 40)
dbg[floor_m] = (235, 225, 170)
Image.fromarray(dbg).save(DBG)
print("saved", DBG)
