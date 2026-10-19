# -*- coding: utf-8 -*-
"""哀嚎洞穴全视野图中文化合成 v3（2026-10-10）。

底图 = 用户截图（1002x668，与钉点空间恒等对齐）。
- banner/pitfangs/dreamer/guilly：整块矩形从 beta 原图搬运（v2 已验证完美）。
- chasm：WINDING CHASM 用截图自身邻近羊皮纸克隆盖掉（beta 无中文名，留空）。
- crag：英文 CRAG OF THE EVERLIVING 用字形级修补（中值背景填充）抹除；
  中文 永生峭壁 只搬字迹（字形掩膜），红房间/岩石背景全部保留截图自己的
  （beta 该区红房间过亮，整块搬必出接缝；v2 还把克隆源压在标签上切了字）。
"""
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

S = Image.open(r'C:/Users/Administrator/.workbuddy/clipboard-images/'
               r'clipboard-2026-10-10T05-03-08-813Z-e2a5080c.jpg').convert('RGB')
B = Image.open(r'C:/Users/Administrator/Desktop/哀嚎洞穴_我们插件_客户端原图_插件实显.png').convert('RGB')
assert S.size == B.size == (1002, 668)
W, H = S.size

out = S.copy()

# ── 1) 整块矩形搬运（v2 同款：环带色调匹配 + 羽化）───────────────────────────
RECT_PATCHES = [
    ('banner 哀嚎洞穴',   (452,   8, 908, 122)),
    ('pitfangs 毒牙深渊', (50,   88, 194, 172)),
    ('dreamer 美梦石',    (263,  28, 407, 100)),
    ('guilly 激流溪谷',   (450, 176, 572, 285)),
]
Sn = np.asarray(S, np.float64)
Bn = np.asarray(B, np.float64)
for name, (x0, y0, x1, y1) in RECT_PATCHES:
    ring = np.zeros((H, W), bool)
    ring[max(y0-8, 0):y1+8, max(x0-8, 0):x1+8] = True
    ring[y0:y1, x0:x1] = False
    a, b = Sn[ring], Bn[ring]
    patch = Bn[y0:y1, x0:x1].copy()
    ks = []
    for c in range(3):
        k = np.clip(a[:, c].std() / max(b[:, c].std(), 1e-6), 0.6, 1.6)
        m = a[:, c].mean() - k * b[:, c].mean()
        patch[:, :, c] = np.clip(patch[:, :, c] * k + m, 0, 255)
        ks.append('%.2f/%+d' % (k, m))
    print('%-18s 色调 %s' % (name, ks))
    layer = Sn.copy()
    layer[y0:y1, x0:x1] = patch
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rectangle((x0, y0, x1-1, y1-1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    out = Image.composite(Image.fromarray(layer.astype(np.uint8)), out, mask)

# ── 2) chasm：截图自身邻近羊皮纸克隆（同图无色调问题）───────────────────────
# 英文 WINDING CHASM + 光晕 bbox ≈ (793,110,899,166)；源取左侧同尺寸净区
sx0, sy0, sx1, sy1 = 682, 108, 792, 168      # 源（截图自身，净羊皮纸）
dx0, dy0 = 790, 108                          # 目标左上
clone = out.crop((sx0, sy0, sx1, sy1))
layer = out.copy()
layer.paste(clone, (dx0, dy0))
mask = Image.new('L', (W, H), 0)
ImageDraw.Draw(mask).rectangle((dx0, dy0, dx0 + (sx1-sx0) - 1, dy0 + (sy1-sy0) - 1), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(4))
out = Image.composite(layer, out, mask)
print('chasm 克隆盖除完成')

# ── 3) crag：字形级处理 ─────────────────────────────────────────────────────
def glyph_mask(img_np, bbox, thr=16, blur=15, dilate=2):
    """bbox 内 |原图 - 中值背景| > thr 的像素（字迹+光晕），膨胀后羽化。"""
    from scipy.ndimage import median_filter, binary_dilation
    x0, y0, x1, y1 = bbox
    sub = img_np[y0:y1, x0:x1]
    bg = np.stack([median_filter(sub[:, :, c], size=blur) for c in range(3)], -1)
    g = np.abs(sub - bg).max(-1) > thr
    g = binary_dilation(g, iterations=dilate)
    m = Image.new('L', (W, H), 0)
    m.paste(Image.fromarray((g * 255).astype(np.uint8)), (x0, y0))
    return m.filter(ImageFilter.GaussianBlur(1.2))

On = np.asarray(out, np.float64)

# 3a) 抹英文：字形像素用中值背景填充（inpaint）
from scipy.ndimage import median_filter, binary_dilation
ex0, ey0, ex1, ey1 = 628, 488, 758, 558      # CRAG OF THE EVERLIVING + 光晕
sub = On[ey0:ey1, ex0:ex1]
bg = np.stack([median_filter(sub[:, :, c], size=15) for c in range(3)], -1)
filled = np.where(np.abs(sub - bg).max(-1, keepdims=True) > 14, bg, sub)
layer = On.copy()
layer[ey0:ey1, ex0:ex1] = filled
# 仅字迹区羽化过渡
m = glyph_mask(On, (ex0, ey0, ex1, ey1), thr=14, dilate=3)
out = Image.composite(Image.fromarray(layer.astype(np.uint8)), out, m)
print('crag 英文字形修补完成')

# 3b) 搬中文 永生峭壁：只搬 beta 的字迹像素（背景不动，零接缝）
On = np.asarray(out, np.float64)
lx0, ly0, lx1, ly1 = 640, 510, 782, 566      # 永生峭壁 + 光晕
m = glyph_mask(Bn, (lx0, ly0, lx1, ly1), thr=14, blur=15, dilate=2)
layer = Image.fromarray(On.astype(np.uint8)).copy()
layer.paste(Image.fromarray(Bn.astype(np.uint8)).crop((lx0, ly0, lx1, ly1)), (lx0, ly0))
out = Image.composite(layer, out, m)
print('crag 中文字迹搬运完成')

R = out
R.save('_temp/_wc_compare/wailing_cn_full.png')
R.resize((663, 442), Image.LANCZOS).save('Media/Maps/WailingCaverns.tga',
                                         format='TGA', compression='tga_rle')
b = open('Media/Maps/WailingCaverns.tga', 'rb').read()
print('TGA type', b[2], 'bpp', b[16], 'desc 0x%02x' % b[17], 'bytes', len(b))
R.save(r'C:/Users/Administrator/Desktop/哀嚎洞穴_全视野_中文版.png')
print('desktop preview saved')
