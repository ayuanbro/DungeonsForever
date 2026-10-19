#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 MapProbe 里「领主大厅 = 旧铁炉堡」这条自证式注释。

背景：/mapprobe 领主大厅 与 /mapprobe inv 里"领主大厅 12/12 OldIronforge"
其实是插件别名表自己填的候选，不是客户端的独立回答 —— 属于循环论证。
2026-09-30 独立核查结论：领主大厅**没有**副本内地图，旧铁炉堡是通往它的区域图。
本补丁只改措辞，不动逻辑；锚点全部避开反斜杠。
"""
import sys

PATCHES = [
    # (锚点, 替换, 说明)
    (
        "    -- 领主大厅（副本 Hall of Thanes）在游戏里就是「旧铁炉堡」那片地下区域，\n"
        "    -- 客户端自带的美术就是这一套（12 块，和湿地同规格）\n",
        "    -- 旧铁炉堡 = 「通往领主大厅」的区域图，**不是领主大厅的副本内图**。\n"
        "    -- 2026-09-30 独立核查：副本内 GetBestMapForUnit → nil；客户端全历史 listfile 的\n"
        "    --   1065 个 worldmap 目录里 0 个 thanes/hallofthanes（含 thane 的只有 NPC 语音）。\n"
        "    -- 留这个别名只为能看这张**区域图**，别拿它当领主大厅的副本地图。\n",
        "KNOWN 注释段",
    ),
    (
        'zh = "旧铁炉堡 · 领主大厅", prefix = ',
        'zh = "旧铁炉堡（区域图）", prefix = ',
        "KNOWN 显示名",
    ),
    (
        'note = "领主大厅（Hall of Thanes）就在旧铁炉堡，客户端自带的就是这张图" },',
        'note = "★ 通往领主大厅的区域图，不是副本内地图（该副本客户端无图，插件里走空态）" },',
        "KNOWN note",
    ),
    (
        "local INV = {\n",
        "local INV = {\n"
        "    -- ★ 下面「领主大厅」这条命中的是「旧铁炉堡」**区域图**（非副本内图）；\n"
        "    --   领主大厅的副本内地图客户端没有 ⇒ 副本手册地图页走空态。\n",
        "INV 表头注释",
    ),
    (
        '"  /mapprobe 领主大厅        就是客户端里的「旧铁炉堡」（Hall of Thanes 在铁炉堡地下）",',
        '"  /mapprobe 领主大厅        = 通往领主大厅的「旧铁炉堡」区域图（★ 不是副本内地图）",',
        "帮助文本",
    ),
]

FILES = [
    r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/MapProbe/MapProbe.lua",
    r"D:/workspace/DungeonsForever/_temp/_mapprobe_src/MapProbe.lua",
]

check_only = "--check" in sys.argv

for path in FILES:
    with open(path, "rb") as f:
        d = f.read().decode("utf-8")
    out = d
    ok = True
    for old, new, name in PATCHES:
        n = out.count(old)
        if n != 1:
            print("  !! [%d] %s :: %s" % (n, name, path.split("/")[-2]))
            ok = False
        if not check_only and n == 1:
            out = out.replace(old, new, 1)
    if not check_only and ok:
        with open(path, "wb") as f:
            f.write(out.encode("utf-8"))
        print("  已写入", path)
    elif check_only:
        print("  %s :: %s" % ("OK " if ok else "FAIL", path))
