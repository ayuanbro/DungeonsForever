# -*- coding: utf-8 -*-
"""挖掘场湿地「地图」页换自制手绘图示意（2026-10-03 用户给了成品图）。

三块：
  1. 源图 挖掘场湿地.png（2408×1741 = 1.383，带装饰边框）
  2. 产物 Media/Maps/ExcavationSite.tga 的**画面区**（512×341，画布 512×512 顶部）
  3. 游戏内效果：满铺 663×442 地图画布（按插件真实几何）
     ★ 本副本单层 + ns.BossPos 无数据 ⇒ 右上无楼层按钮、左上无「隐藏 boss」开关。
产物 _temp/WETLANDS_MAP_PAGE.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    r"C:/Users/Administrator/AppData/Local/Microsoft/Windows/Fonts/方正小标宋简体.TTF",
    r"C:/Windows/Fonts/Noto Sans SC Bold (TrueType).otf",
    r"C:/Windows/Fonts/simhei.ttf",
]
FONT = next(p for p in FONT_CANDIDATES if os.path.exists(p) and os.path.getsize(p) > 1000)

CW, CH = 663, 442          # 地图画布（与客户端瓦片同一块）
CANVAS, VH = 512, 341      # CUSTOM_CANVAS / CUSTOM_VH

BG = (24, 22, 20)
PANEL_BD = (120, 122, 130)
GOLD = (255, 209, 0)
GREY = (168, 168, 168)
WHITE = (240, 238, 232)
DIM = (188, 184, 176)
GREEN = (107, 224, 87)
RED = (226, 106, 96)


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def wrap(d, txt, font, maxw):
    lines, cur = [], ""
    for ch in txt:
        if d.textlength(cur + ch, font=font) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def main():
    src = Image.open("C:/Users/Administrator/Desktop/无限副本手册/挖掘场湿地\u200b.png").convert("RGB")
    tga = Image.open(os.path.join(HERE, "..", "Media", "Maps", "ExcavationSite.tga")).convert("RGB")
    frame = tga.crop((0, 0, CANVAS, VH))          # 画面区（下方 171 行是黑边）

    PAD, GAPX = 44, 54
    BW, BH = 520, 348                              # 源图 / 画面区 展示框
    W = PAD * 2 + BW * 2 + GAPX
    im = Image.new("RGB", (W, 1500), BG)
    d = ImageDraw.Draw(im)

    d.text((PAD, 30), "挖掘场湿地 · 「地图」页 = 用户绘制的成品图（2026-10-03）", font=fnt(24), fill=GOLD)
    y = 70
    for txt, col in [
        ("源图 2408×1741（比例 1.383）→ Media/Maps/ExcavationSite.tga：512×512 / 24 位 RLE / "
         "画面占顶部 341 行（3:2）/ 原点左下；下方 171 行黑边，运行期只取画面。", WHITE),
        ("★ 比例与 3:2 差 8.5% 且图**带完整装饰边框** ⇒ 转换用「整幅映射」（横向拉伸 8.5%）"
         "而不是「中心裁」：裁剪会把上下边框整条切掉、只留左右边框。", GREEN),
    ]:
        for ln in wrap(d, txt, fnt(14), W - PAD * 2):
            d.text((PAD, y), ln, font=fnt(14), fill=col)
            y += 22
    TOP = y + 58

    # ① 源图
    a = src.copy(); a.thumbnail((BW, BH), Image.LANCZOS)
    box = Image.new("RGB", (BW, BH), (12, 11, 10))
    box.paste(a, ((BW - a.width) // 2, (BH - a.height) // 2))
    im.paste(box, (PAD, TOP))
    d.rectangle([PAD - 1, TOP - 1, PAD + BW, TOP + BH], outline=PANEL_BD)
    d.text((PAD, TOP - 28), "① 源图  挖掘场湿地.png（2408×1741）", font=fnt(17), fill=GOLD)
    d.text((PAD, TOP + BH + 8), "四边带装饰边框 / 上下框约 25px", font=fnt(13), fill=DIM)

    # ② TGA 画面区
    x2 = PAD + BW + GAPX
    b = frame.resize((BW, round(BW * VH / CANVAS)), Image.LANCZOS)
    im.paste(b, (x2, TOP))
    d.rectangle([x2 - 1, TOP - 1, x2 + BW, TOP + b.height], outline=PANEL_BD)
    d.text((x2, TOP - 28), "② 产物画面区  ExcavationSite.tga（512×341）", font=fnt(17), fill=GOLD)
    yy = TOP + b.height + 10
    for txt, col in [
        ("18 字节文件头与既有三张自制图（领主大厅 / 洛丹伦废墟 / 达拉然）**逐字节相同**"
         "：512×512 / 24 位 / 类型 10 = RLE / 描述符 0 = 原点左下。", GREEN),
        ("1024 高清备份（画面 682 行）留在 _temp/_tga1024_bak/。", DIM),
    ]:
        for ln in wrap(d, txt, fnt(13), BW):
            d.text((x2, yy), ln, font=fnt(13), fill=col)
            yy += 22

    # ③ 游戏内效果
    TOP2 = max(TOP + BH, yy) + 96
    d.text((PAD, TOP2 - 34), "③ 游戏内「地图」页效果（按插件真实几何：画布 663×442）", font=fnt(17), fill=GOLD)
    art = frame.resize((CW, CH), Image.LANCZOS)
    im.paste(art, (PAD, TOP2))
    d.rectangle([PAD - 1, TOP2 - 1, PAD + CW, TOP2 + CH], outline=PANEL_BD)
    # 角落标注（本副本没有的控件，画虚线框 + 红字说明）
    d.rectangle([PAD + 6, TOP2 + 6, PAD + 6 + 72, TOP2 + 6 + 20], outline=RED)
    d.text((PAD + 6, TOP2 + 30), "左上「隐藏 boss」开关：不出现", font=fnt(12), fill=RED)
    d.rectangle([PAD + CW - 6 - 56, TOP2 + 6, PAD + CW - 6, TOP2 + 6 + 20], outline=RED)
    tt = "右上楼层按钮：不出现（单层）"
    d.text((PAD + CW - 12 - d.textlength(tt, font=fnt(12)), TOP2 + 30), tt, font=fnt(12), fill=RED)

    yy = TOP2 + CH + 16
    for txt, col in [
        ("★ 满铺同一块 663×442 画布 ⇒ 与客户端瓦片**共用百分比坐标系**，将来补上 boss 坐标"
         "钉点能直接落（钉点坐标是百分比，横向拉伸不影响落点）。", WHITE),
        ("★ 机制：登记进整图自制表 CUSTOM[excavation_wetlands] ⇒ Paint 走「铺整张 + 12 块瓦片全隐」"
         "一支，空态文案不出现。本副本单层（无 ART 层），楼层按钮本来就不出。", WHITE),
        ("★ 目前 ns.BossPos 没有挖掘场湿地 ⇒ 零钉点、「隐藏 boss」开关也不出现；"
         "wowhead forever 页没给 boss 坐标，按坐标纪律不猜（没写就留 false）。", DIM),
    ]:
        for ln in wrap(d, txt, fnt(13), W - PAD * 2):
            d.text((PAD, yy), ln, font=fnt(13), fill=col)
            yy += 24
        yy += 6

    out = os.path.join(HERE, "WETLANDS_MAP_PAGE.png")
    im.crop((0, 0, W, yy + 12)).save(out)
    print("ok", out, (W, yy + 12))


if __name__ == "__main__":
    main()
