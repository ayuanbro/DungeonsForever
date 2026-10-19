# -*- coding: utf-8 -*-
"""领主大厅 · 经典羊皮纸风格副本地图 v1 渲染（方案A：程序化提取 + 手绘风渲染）。

输入：
  实测俯视布局 jpg（灰底 + 深绿岩壁 + 暗棕建筑地板，R>G>B）
  _temp/parchment_base.png  ScholomanceOld1 12 块瓦片拼图（1024x768）
输出：
  _temp/lordhall_map_v1.png        1002x668 成图
  _temp/lordhall_map_v1_debug.png  掩膜调试图
色板：怒焰裂谷实测采样。
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LAY = r"C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-09-30T02-37-51-596Z-23b3b073.jpg"
BASE = os.path.join(HERE, "parchment_base.png")
OUT = os.path.join(HERE, "lordhall_map_v1.png")
DBG = os.path.join(HERE, "lordhall_map_v1_debug.png")
FONT = "C:/Windows/Fonts/simkai.ttf"

CW, CH = 1002, 668
RNG = np.random.default_rng(7)

ROCK = np.array([131, 91, 33], float)
ROCK_D = np.array([106, 72, 26], float)
FLOOR = np.array([180, 170, 118], float)
OUTL = np.array([58, 38, 12], float)


def L(m):
    return Image.fromarray((m * 255).astype(np.uint8))


def clean(m, med=3, op=1, cl=3):
    p = L(m).filter(ImageFilter.MedianFilter(med))
    p = p.filter(ImageFilter.MinFilter(op * 2 + 1)).filter(ImageFilter.MaxFilter(op * 2 + 1))
    p = p.filter(ImageFilter.MaxFilter(cl * 2 + 1)).filter(ImageFilter.MinFilter(cl * 2 + 1))
    return np.asarray(p) > 127


def wobble(p, amp=0.16, blur=2, seed=1):
    f = np.asarray(p).astype(np.float32) / 255
    r = np.random.default_rng(seed)
    n = r.random((max(2, f.shape[0] // 6), max(2, f.shape[1] // 6))).astype(np.float32)
    nimg = Image.fromarray((n * 255).astype(np.uint8)).resize(
        (f.shape[1], f.shape[0]), Image.BILINEAR)
    n = np.asarray(nimg).astype(np.float32) / 255 - 0.5
    f = np.clip(f * 0.92 + 0.04 + n * amp, 0, 1)
    q = Image.fromarray((f * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(q) > 127


def band(m, w=4):
    p = L(m)
    inner = np.asarray(p.filter(ImageFilter.MinFilter(w * 2 + 1))) > 127
    outer = np.asarray(p.filter(ImageFilter.MaxFilter(w * 2 + 1))) > 127
    return outer & ~inner


def blotch(shape, cell=90, seed=2):
    r = np.random.default_rng(seed)
    small = r.random((max(2, shape[0] // cell), max(2, shape[1] // cell))).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize(
        (shape[1], shape[0]), Image.BILINEAR)
    return np.asarray(img).astype(np.float32) / 255


def boxblur_arr(arr, r):
    if arr.ndim == 2:
        return np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
                          .filter(ImageFilter.BoxBlur(r))).astype(np.float32)
    chans = []
    for c in range(arr.shape[2]):
        chans.append(np.asarray(Image.fromarray(np.clip(arr[..., c], 0, 255).astype(np.uint8))
                                .filter(ImageFilter.BoxBlur(r))).astype(np.float32))
    return np.stack(chans, -1)


# ---------- 1. 布局图分类 ----------
im = Image.open(LAY).convert("RGB")
a = np.asarray(im).astype(np.int16)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
V = a.max(-1)
neutral = (np.abs(R - G) < 16) & (np.abs(G - B) < 16)
bg = neutral & (V > 95) & (V < 140)
white = neutral & (V >= 140)
warm_order = (R - G >= 8) & (R - B >= 12) & ~bg & ~white   # 暗棕建筑 R>G>B
floor0 = warm_order & (V >= 45)
rock0 = (~floor0) & ~bg & ~white

content = clean(rock0 | floor0, med=3, op=1, cl=3)
rock_m = clean(rock0 & content, med=3, op=1, cl=3)
floor_m = clean(floor0 & content, med=3, op=1, cl=3)
floor_m &= ~rock_m
print("px  rock %.3f floor %.3f" % (rock_m.mean(), floor_m.mean()))

rows = np.where(content.sum(1) > 8)[0]
cols = np.where(content.sum(0) > 8)[0]
y0, y1 = rows.min(), rows.max()
x0, x1 = cols.min(), cols.max()
print("content bbox", x0, x1, y0, y1)

# ---------- 2. 摆到画布 ----------
TX0, TY0, TX1, TY1 = 48, 130, 954, 640
s = min((TX1 - TX0) / (x1 - x0 + 1), (TY1 - TY0) / (y1 - y0 + 1))
W = int((x1 - x0 + 1) * s)
H = int((y1 - y0 + 1) * s)
OX = (TX0 + TX1 - W) // 2
OY = TY0 + (TY1 - TY0 - H) // 2
print("scale %.3f size %dx%d off (%d,%d)" % (s, W, H, OX, OY))


def to_canvas(m, seed, amp=0.16, blur=2):
    p = L(m).crop((x0, y0, x1 + 1, y1 + 1)).resize((W, H), Image.BILINEAR)
    w = wobble(p, amp=amp, blur=blur, seed=seed)
    full = np.zeros((CH, CW), bool)
    full[OY:OY + H, OX:OX + W] = w
    return full


rock_c = to_canvas(rock_m, seed=11, amp=0.14, blur=2)
floor_c = to_canvas(floor_m, seed=22, amp=0.10, blur=1)
floor_c &= rock_c

# ---------- 3. 底图清理 ----------
base = Image.open(BASE).convert("RGB").crop((0, 0, CW, CH))
base_a = np.asarray(base).astype(np.float32)
bR, bG, bB = base_a[..., 0], base_a[..., 1], base_a[..., 2]
bS2 = bR + bG + bB
yy, xx = np.mgrid[0:CH, 0:CW]


def hf_patch(region_src, mask, bsize=64):
    """把干净区高频纹理随机拼贴进 mask 区域，返回整幅画布尺寸的高频图。"""
    sb = boxblur_arr(region_src, 3)
    hf = region_src - sb
    Hh, Wh = hf.shape[:2]
    out = np.zeros((CH, CW, 3), np.float32)
    ys2, xs2 = np.where(mask)
    if len(ys2) == 0:
        return out
    y_min, y_max = ys2.min(), ys2.max()
    x_min, x_max = xs2.min(), xs2.max()
    for by in range(y_min, y_max + 1, bsize):
        for bx in range(x_min, x_max + 1, bsize):
            oy = int(RNG.integers(0, max(1, Hh - bsize)))
            ox = int(RNG.integers(0, max(1, Wh - bsize)))
            tile = hf[oy:oy + bsize, ox:ox + bsize]
            y2, x2 = min(CH, by + bsize), min(CW, bx + bsize)
            th, tw = y2 - by, x2 - bx
            out[by:y2, bx:x2] = tile[:th, :tw]
    return out


# 3a. 抹通灵学院底图楼层/文字/图标：扩散补低频 + 贴羊皮纸高频
inbox = (xx > 170) & (xx < 852) & (yy > 185) & (yy < 540)
sch = inbox & ((((bR - bB) > 12) & ((bR - bB) < 64) & (bS2 > 235) & (bS2 < 530)) | (bS2 <= 235))
sch = np.asarray(L(sch).filter(ImageFilter.MaxFilter(7))) > 127
print("sch px", sch.sum())

cur = base_a.copy()
cur[sch] = base_a[~sch].reshape(-1, 3).mean(0)
for _ in range(90):
    bl = boxblur_arr(cur, 9)
    cur[sch] = bl[sch]
hf = hf_patch(base_a[545:655, 60:940], sch)
cur = np.clip(cur + hf, 0, 255)
base_a = cur

# 3b. 抹横幅「通灵学院」文字
by0, by1, bx0, bx1 = 46, 106, 380, 700
region = base_a[by0:by1, bx0:bx1].copy()
tR, tG, tB = region[..., 0], region[..., 1], region[..., 2]
tmask = (tR + tG + tB) < 440
tmask = np.asarray(Image.fromarray((tmask * 255).astype(np.uint8))
                   .filter(ImageFilter.MaxFilter(5))) > 127
print("banner text px", tmask.sum())
for _ in range(45):
    bl = boxblur_arr(region, 5)
    region[tmask] = bl[tmask]
# 用横幅右段干净区的高频补回缎带纹理
hf2 = hf_patch(base_a[46:106, 700:880], np.zeros(region.shape[:2], bool))
hf2_small = hf2[:region.shape[0], :region.shape[1]]
region = np.clip(region + hf2_small * (tmask[..., None] * 0.9), 0, 255)
base_a[by0:by1, bx0:bx1] = region
base_clean = Image.fromarray(base_a.astype(np.uint8))

# ---------- 4. 手绘风渲染 ----------
def fill_layer(m, color, tex_amp=10, alpha=235, seed=3):
    tex = blotch((CH, CW), cell=110, seed=seed) - 0.5
    grain = (RNG.random((CH, CW)) - 0.5) * 6
    col = color[None, None, :] + tex[..., None] * tex_amp + grain[..., None]
    layer = np.zeros((CH, CW, 4), np.float32)
    layer[..., :3] = np.clip(col, 0, 255)
    layer[..., 3] = m * alpha
    return layer


def edge_layer(m, w, color=OUTL, alpha=255):
    e = band(m, w)
    eimg = Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    e = np.asarray(eimg) > 40
    layer = np.zeros((CH, CW, 4), np.float32)
    layer[..., :3] = color
    layer[..., 3] = e * alpha
    return layer


darkb = blotch((CH, CW), cell=140, seed=32)
dark_m = rock_c & (darkb > 0.62)

layers = [
    fill_layer(rock_c, ROCK, tex_amp=26, alpha=240, seed=31),
    fill_layer(dark_m, ROCK_D, tex_amp=8, alpha=170, seed=33),
    edge_layer(rock_c, 4),
    fill_layer(floor_c, FLOOR, tex_amp=8, alpha=245, seed=34),
    edge_layer(floor_c, 3),
]

art = np.zeros((CH, CW, 4), np.float32)
for ly in layers:
    al = ly[..., 3:4] / 255
    art[..., :3] = art[..., :3] * (1 - al) + ly[..., :3] * al
    art[..., 3] = np.maximum(art[..., 3], ly[..., 3])

out = base_a * (1 - art[..., 3:4] / 255) + art[..., :3] * (art[..., 3:4] / 255)
out_img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

# ---------- 5. 横幅写「领主大厅」----------
d = ImageDraw.Draw(out_img)
font = ImageFont.truetype(FONT, 30)
title = "领 主 大 厅"
tw = d.textlength(title, font=font)
d.text((512 - tw / 2, 58), title, font=font, fill=(96, 62, 22))

out_img.save(OUT)
print("saved", OUT, out_img.size)

dbg = np.zeros((CH, CW, 3), np.uint8)
dbg[rock_c] = (120, 80, 40)
dbg[floor_c] = (235, 225, 170)
Image.fromarray(dbg).save(DBG)
print("saved", DBG)
