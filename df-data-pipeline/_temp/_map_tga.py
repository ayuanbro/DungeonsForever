# -*- coding: utf-8 -*-
"""用户手绘副本图 → Media/Maps/<名字>.tga（通用版；口径见下）。

用法：
  python _map_tga.py <源图路径> <输出名> [--mode fit|center]

口径（2026-10-01 定案 / 2026-10-03 两次改规格，**定稿 663×442**）：
  源图 → **映射**到 **663×442**（= 游戏内画布 M.MAP_W × M.FRAME_H，恰 3:2）→
  存 **24 位（RGB，无 alpha）RLE TGA，原点左下(desc=0)**。
  ★ 贴图**就是画面**：没有黑边、没有多余留白，运行期 `SetTexCoord(0, 1, 0, 1)` 取满。
  ★★ 历次规格与 UV 比例（钉点百分比坐标一次都没动过）：
     · 512×512   画面 512×341   （v 上限 0.666015625）→ 用户反馈「压缩过头」
     · 1024×1024 画面 1024×682  （v 上限 0.666015625）→ 仍不是画布原生像素
     · **663×442  全画面**       （v 上限 1）           → 现在
     前两者 UV 比例完全相等；与 442/663 = 0.666666… 也仅差 0.07%（<0.3 像素）。

★ 为什么是 663×442（2026-10-03 用户：「按照游戏中实际画布的大小去制作」）：
  · 游戏内画布 = M.MAP_W × M.FRAME_H = 663×442（MapUI 由面板几何算出，恰 3:2）。
  · 贴图 1:1 等于画布 ⇒ 既不欠采样（512 那种放大糊）也不带 50% 黑边（1024 那种）。
  · 非 2 的幂 TGA 本客户端可用 —— 仓内已有 44×88 的 LibHUI 贴图先例。

★ 模式说明（为什么默认 fit 而不是 center）：
  · 既有三张（HallOfThanes / RuinsOfLordaeron / Dalaran）源图比例都在 1.500~1.509，
    此时 fit 与 center **结果几乎相同**（差 <1px），所以既有成品不用重做。
  · 2026-10-03 挖掘场湿地源图是 1.383（比 3:2 高 8.5%），且**带完整装饰边框**：
    center（上下各裁 68px）会把上下边框整条切掉、只留左右边框，观感与既有两张不一致；
    fit 保边框完整、仅横向拉伸 8.5%。故选 fit 作默认。
  · ⚠️ 若某天源图比例偏离 3:2 很多（>15%，如 4:3），fit 的形变会肉眼可见 ——
    那时改用 --mode center，并回头确认地图主体没被裁掉。
"""
import os
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 663, 442       # = MapUI 的 M.MAP_W × M.FRAME_H（游戏内画布实际像素，恰 3:2）
RATIO = W / H         # 1.5
BIG = 2               # 高清备份倍数 → 1326×884（存 _temp/_tga2x_bak/，需要提档时直接换）


def plate(src, w, h, mode="fit"):
    """源图 → (w, h) 画面。
    mode='fit'    : 整幅映射（可各向异性，保边框完整）
    mode='center' : 中心裁到 3:2 再等比缩（源图≈3:2 时与 fit 等价）
    """
    if mode == "center":
        sw, sh = src.size
        tw = min(sw, int(round(sh * RATIO)))
        th = min(sh, int(round(sw / RATIO)))
        src = src.crop(((sw - tw) // 2, (sh - th) // 2,
                        (sw - tw) // 2 + tw, (sh - th) // 2 + th))
    return src.resize((w, h), Image.LANCZOS)


def convert(src_path, out_name, mode="fit"):
    src = Image.open(src_path).convert("RGB")
    print("源图", os.path.basename(src_path), src.size,
          "比例 %.4f" % (src.size[0] / src.size[1]), "mode =", mode)

    im = plate(src, W, H, mode)
    out_tga = os.path.normpath(os.path.join(HERE, "..", "Media", "Maps", out_name + ".tga"))
    os.makedirs(os.path.dirname(out_tga), exist_ok=True)
    im.save(out_tga, rle=True)
    print("ok ->", out_tga, im.size, "字节", os.path.getsize(out_tga))

    big = plate(src, W * BIG, H * BIG, mode)
    out_bak = os.path.normpath(os.path.join(HERE, "_tga2x_bak", out_name + ".tga"))
    os.makedirs(os.path.dirname(out_bak), exist_ok=True)
    big.save(out_bak, rle=True)
    print("ok ->", out_bak, big.size, "字节", os.path.getsize(out_bak))
    return out_tga


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src_path, out_name = sys.argv[1], sys.argv[2]
    mode = "fit"
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]
    convert(src_path, out_name, mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
