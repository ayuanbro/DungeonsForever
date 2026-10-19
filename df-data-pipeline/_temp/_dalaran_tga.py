# -*- coding: utf-8 -*-
"""达拉然手绘图 → Media/Maps/Dalaran.tga（★ 口径与既有两本自制图**逐像素同款**）。

约定（2026-10-01 定案，本脚本 2026-10-02 用既有成品反解复核）：
  源图 → **中心裁到正好 3:2** → LANCZOS 缩到 512×341 → 贴到 512×512 黑底**顶部** →
  存 **24 位（RGB，无 alpha）RLE TGA，原点左下(desc=0)**。
  512×341 之外的下方 171 行是黑边；运行期 SetTexCoord(0,1,0,341/512) 只取画面。

反解证据：用同一条流水线重跑 农户大厅.png / 洛丹伦废墟.png，与既有
Media/Maps/HallOfThanes.tga / RuinsOfLordaeron.tga 逐像素比 —— 最大通道差 7、平均 0.6
（就是 PIL 版本重采样核的差），其余候选（不裁直接压扁 / 等比留黑 / 靠左裁）差 ≥166 被排除。

顺带留 1024 高清版进 _temp/_tga1024_bak/（画面 682 行），沿用既有习惯。
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "C:/Users/Administrator/Desktop/无限副本手册/达拉然\u200b.png"
OUT_TGA = os.path.join(HERE, "..", "Media", "Maps", "Dalaran.tga")
OUT_BAK = os.path.join(HERE, "_tga1024_bak", "Dalaran.tga")

CANVAS = 512          # 画布边长（2 的幂，512）
VH = 341              # 画面行数（341/512 = 0.666 ≈ 2/3，正好 3:2）
BIG = 1024            # 高清备份
BIG_VH = round(BIG * VH / CANVAS)   # 682


def plate(src, canvas, vh):
    """中心裁到 3:2 → 缩到 (canvas, vh) → 贴到 canvas×canvas 黑底顶部。"""
    w, h = src.size
    tw, th = min(w, int(round(h * 1.5))), min(h, int(round(w / 1.5)))
    im = src.crop(((w - tw) // 2, (h - th) // 2,
                   (w - tw) // 2 + tw, (h - th) // 2 + th))
    im = im.resize((canvas, vh), Image.LANCZOS)
    out = Image.new("RGB", (canvas, canvas), (0, 0, 0))
    out.paste(im, (0, 0))
    return out, (tw, th)


def main():
    src = Image.open(SRC).convert("RGB")
    print("源图", src.size, "比例 %.4f" % (src.size[0] / src.size[1]))

    small, cropped = plate(src, CANVAS, VH)
    os.makedirs(os.path.dirname(OUT_TGA), exist_ok=True)
    small.save(OUT_TGA, rle=True)
    print("ok ->", os.path.normpath(OUT_TGA), small.size,
          "裁剪后 %dx%d" % cropped, "字节", os.path.getsize(OUT_TGA))

    big, _ = plate(src, BIG, BIG_VH)
    os.makedirs(os.path.dirname(OUT_BAK), exist_ok=True)
    big.save(OUT_BAK, rle=True)
    print("ok ->", os.path.normpath(OUT_BAK), big.size, "字节", os.path.getsize(OUT_BAK))


if __name__ == "__main__":
    main()
