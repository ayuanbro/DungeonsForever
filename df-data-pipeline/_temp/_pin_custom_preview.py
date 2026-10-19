# -*- coding: utf-8 -*-
"""两个「自制手绘图」副本的「地图」页实装效果（2026-10-01 修复后）。

只画这两本：左半区 = 用户手绘 TGA（UV 裁顶满铺同一块 663×442 画布）+ 首领钉点（身份色），
右栏 = 默认「首领」列表。钉子坐标/名字/颜色全部读插件真数据（lupa 读 Data_BossPos /
Data_DungeonLoot），与 Core/MapUI.lua 的 BOSS_PALETTE 同色序。

出图：_temp/MAP_CUSTOM_PIN_PREVIEW.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

import _map_boss_preview as P  # noqa: E402

# 与 Core/MapUI.lua 的 M.BOSS_PALETTE 同序（12 色循环）
PALETTE = [
    (240, 77, 71), (255, 148, 48), (255, 209, 0), (107, 224, 87),
    (77, 214, 214), (92, 140, 255), (179, 115, 242), (242, 107, 199),
    (232, 227, 209), (143, 166, 191), (201, 140, 89), (199, 230, 77),
]


def color_of(did, en):
    for i, b in enumerate(P.bosses_for(did), start=1):
        if b['en'] == en:
            return PALETTE[(i - 1) % len(PALETTE)]
    return (255, 255, 255)


def draw_pin(im, d, cx, cy, col, name, size):
    r = size / 2.0
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col, outline=(20, 18, 14), width=2)
    f = P.fnt(14)
    w = d.textlength(name, font=f)
    # 名字压在地图上：细描边（OUTLINE 效果用四次偏移模拟）
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        d.text((cx - w / 2 + ox, cy + r + 1 + oy), name, font=f, fill=(0, 0, 0))
    d.text((cx - w / 2, cy + r + 1), name, font=f, fill=col)


def block(did, tga, title, meta, y, im, d):
    PAD = 40
    P.draw_shell(d, PAD, y, title, meta)
    art = P.map_custom(tga)
    mx, my, mw, mh = PAD, y + P.GUIDE_TOP_Y, P.MAP_W, P.FRAME_H
    mp = P.fit(art, mw, mh)
    ox, oy = mx + (mw - mp.width) // 2, my + (mh - mp.height) // 2
    im.paste(mp, (ox, oy))
    d.rectangle([ox - 1, oy - 1, ox + mp.width, oy + mp.height], outline=(118, 120, 128))
    pins = P.pins_for(did)
    for p in pins:
        cx = ox + p['left'] / 100.0 * mp.width
        cy = oy + p['top'] / 100.0 * mp.height
        draw_pin(im, d, cx, cy, color_of(did, p['en']), p['zh'], P.PIN_MIN)
    px, py, _, _ = P.side_rect(PAD, y)
    P.draw_side_list(im, d, px, py, [b['zh'] for b in P.bosses_for(did)])
    return len(pins), len(P.bosses_for(did))


def main():
    PAD, TITLE_H, GAPY, CAP_H = 40, 130, 70, 104
    W = PAD * 2 + P.DETAIL_W
    H = TITLE_H + 2 * (P.DETAIL_H + CAP_H + GAPY) + 20
    im = Image.new("RGB", (W, H), P.BG)
    d = ImageDraw.Draw(im)
    d.text((PAD, 24), "「地图」页 · 自制手绘图副本的首领钉点（2026-10-01 修复后实装版式）",
           font=P.fnt(20), fill=P.GOLD)
    d.text((PAD, 56), "修复点：MapUI.SyncPins 此前拿「有 ART 层」当地图存在判据 ⇒ 自制图副本被当无图，"
                      "钉点一颗都不画。", font=P.fnt(13), fill=P.WHITE)
    d.text((PAD, 78), "现在：自制图与客户端瓦片共用同一块 663×442 画布与同一套百分比坐标 ⇒ 钉点照画"
                      "（单张整图 = 固定第 1 层）。", font=P.fnt(13), fill=P.GREEN)
    d.text((PAD, 100), "钉点/名字用首领身份色（M.BOSS_PALETTE，按副本内首领序号取色）—— 与右栏列表行图标同色。",
           font=P.fnt(13), fill=P.GREY)

    y = TITLE_H
    n1 = block("hall_of_thanes", "HallOfThanes.tga", "领主大厅",
               "13-18 级 · 铁炉堡地下，丹莫罗 · BOSS 4 · 自制手绘图 + 首领钉点", y, im, d)
    P.cap(d, PAD, y, [
        ("钉点 4 枚：杜尔根·挽歌之锤 / 普兰德 / 玛格玛图斯 / 法尔德里姆·安威玛尔"
         "（数据 ns.BossPos.hall_of_thanes，两位式坐标 = 第 1 层）。", P.WHITE),
        ("自制图 = Media/HallOfThanes.tga（1024×1024，画面占顶部 683 行）UV 裁顶满铺 ⇒ "
         "与客户端瓦片图同一坐标系，钉点百分比直接可用。", P.GREEN),
    ])

    y += P.DETAIL_H + CAP_H + GAPY
    n2 = block("ruins_of_lordaeron", "RuinsOfLordaeron.tga", "洛丹伦废墟",
               "15-20 级 · 洛丹伦废城 · BOSS 7 · 自制手绘图 + 首领钉点", y, im, d)
    P.cap(d, PAD, y, [
        ("钉点 6 枚：男爵 / 枯牙 / 被遗弃者 / 比约克 / 拉斯玛尔 / 邪恶的维克托。"
         "右栏 7 行 —— 「洛丹伦上尉」是稀有、只有掉落没坐标，所以只在列表里。", P.WHITE),
        ("右栏列表行图标 = 同一身份色；点列表行或地图钉点都进该首领详情（掉落在上、攻略在下）。", P.GREEN),
    ])

    out = os.path.join(HERE, "MAP_CUSTOM_PIN_PREVIEW.png")
    im.save(out)
    print("ok", out, im.size, "领主大厅 钉点/首领 =", n1, "洛丹伦 钉点/首领 =", n2)


if __name__ == "__main__":
    main()
