"""哀嚎洞穴「右上补洞」合成 v2（多边形直补）：
底 = 客户端 zhCN 原版图（1002x668 中文标注，横幅/房名全保留）
补 = 巫妖王版全视野图（同百分比空间）缩放到 1002x668，先抹掉自带的
     英文房名 WINDING CHASM 与烙印骷髅，再按手描多边形（羽化）补进底图。
多边形故意向外（羊皮纸侧）放宽：同内容区被重贴只是色调微移，羽化后不可见。
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = r"C:/Users/Administrator/Desktop/哀嚎洞穴_我们插件_客户端原图_插件实显.png"
WOTLK = r"C:/Users/Administrator/Desktop/哀嚎洞穴_参考插件_自带图_插件实显.png"
OUT = r"D:/workspace/DungeonsForever/_temp/_wc_compare/wailing_merged.png"

W, H = 1002, 668
BANNER = (470, 25, 900, 122)          # 横幅 bbox（双图横幅都在内，永不补）

# 巫妖王图需先抹掉的烙印元素（源坐标 bbox）
EN_LABEL = (812, 115, 888, 156)       # WINDING CHASM（羊皮纸上）
SKULL1 = (870, 183, 896, 207)         # 洞内烙印骷髅（灰池上）

# 补丁多边形（顺时针，右上洞区外扩到羊皮纸/同内容侧）
POLY = [(612, 162), (650, 140), (710, 126), (790, 118), (860, 112), (930, 108),
        (988, 106), (992, 500), (930, 505), (880, 470), (850, 420), (820, 380),
        (780, 350), (740, 330), (700, 300), (670, 270), (650, 230), (630, 195)]


def clone_fill(im, bbox, src_offset):
    """用 bbox 平移 src_offset 处的同尺寸块羽化覆盖 bbox（避免矩形色差）"""
    x0, y0, x1, y1 = bbox
    dx, dy = src_offset
    patch = im.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
    m = Image.new("L", patch.size, 0)
    ImageDraw.Draw(m).rectangle((2, 2, patch.size[0] - 3, patch.size[1] - 3), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2.5))
    im.paste(patch, (x0, y0), m)


def main():
    base = Image.open(BASE).convert("RGB")
    wotlk = Image.open(WOTLK).convert("RGB").resize((W, H), Image.LANCZOS)

    # ── 抹烙印：英文房名（上方羊皮纸下移盖）、骷髅（左侧同池面平移盖）──
    clone_fill(wotlk, EN_LABEL, (0, -34))      # 从正上方取羊皮纸
    clone_fill(wotlk, SKULL1, (-34, 0))        # 从左侧取同类灰池面
    wotlk.save(r"D:/workspace/DungeonsForever/_temp/_wc_compare/wotlk_clean.png")

    # ── 全局色调匹配 b -> a ──
    a = np.asarray(base).astype(np.float64)
    b = np.asarray(wotlk).astype(np.float64)
    aD, bD = a.reshape(-1, 3)[::7], b.reshape(-1, 3)[::7]
    fit = np.empty((2, 3))
    for c in range(3):
        x, y = bD[:, c], aD[:, c]
        k = np.cov(x, y, bias=True)[0, 1] / np.var(x)
        fit[0, c] = k
        fit[1, c] = y.mean() - k * x.mean()
    bm = b.copy()
    for c in range(3):
        bm[:, :, c] = b[:, :, c] * fit[0, c] + fit[1, c]

    # ── 多边形掩码（羽化）+ 横幅排除 ──
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(POLY, fill=255)
    ImageDraw.Draw(m).rectangle(BANNER, fill=0)
    m = m.filter(ImageFilter.GaussianBlur(3))
    alpha = (np.asarray(m).astype(np.float64) / 255)[:, :, None]

    out = a * (1 - alpha) + bm * alpha
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    res.save(OUT)
    print("色调匹配:", ["%.3f/%+.0f" % (fit[0, c], fit[1, c]) for c in range(3)])
    print("补丁区占比 %.1f%%" % (float((np.asarray(m) > 128).mean()) * 100))
    print("->", OUT)


if __name__ == "__main__":
    main()
