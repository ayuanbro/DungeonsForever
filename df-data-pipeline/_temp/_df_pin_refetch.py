# -*- coding: utf-8 -*-
"""重抓 foreverchanges.pro 全部副本页（2026-10 改版后带 floors.pins JSON 的新版）。

旧格式缓存页已移 _ref_oldfmt/。本脚本只抓 zh-cn 页（钉点 label 中英混排，
对齐走 _df_pin_floors2.py 的 zh/en 双向表）。
用法：python _df_pin_refetch.py
"""
import os, re, time, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "_ref")
PROXY = "http://127.0.0.1:7897"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

SLUG = {
    "ragefire_chasm": "ragefire-chasm",
    "wailing_caverns": "wailing-caverns",
    "the_deadmines": "the-deadmines",
    "shadowfang_keep": "shadowfang-keep",
    "blackfathom_deeps": "blackfathom-deeps",
    "the_stockade": "the-stockade",
    "gnomeregan": "gnomeregan",
    "razorfen_kraul": "razorfen-kraul",
    "razorfen_downs": "razorfen-downs",
    "sm_graveyard": "scarlet-monastery-graveyard",
    "sm_library": "scarlet-monastery-library",
    "sm_armory": "scarlet-monastery-armory",
    "sm_cathedral": "scarlet-monastery-cathedral",
    "uldaman": "uldaman",
    "zul_farrak": "zulfarrak",
    "maraudon": "maraudon",
    "sunken_temple": "sunken-temple",
    "blackrock_depths": "blackrock-depths",
    "dire_maul_east": "dire-maul-east",
    "dire_maul_north": "dire-maul-north",
    "dire_maul_west": "dire-maul-west",
    "lower_blackrock_spire": "lower-blackrock-spire",
    "upper_blackrock_spire": "upper-blackrock-spire",
    "scholomance": "scholomance",
    "stratholme_main": "stratholme-main-gate",
    "stratholme_service": "stratholme-service-gate",
    "city_of_dalaran": "city-of-dalaran",
}

BACKOFF = [15, 25, 35, 45]


def fetch(slug):
    out = os.path.join(REF, "dg_%s.html" % slug)
    if os.path.exists(out) and os.path.getsize(out) > 20000 and "floors" in open(out, encoding="utf-8", errors="replace").read(400000):
        return "cached"
    url = "https://foreverchanges.pro/zh-cn/dungeons/%s" % slug
    for wait in [0] + BACKOFF:
        if wait:
            print("  403，退避 %ds…" % wait, flush=True)
            time.sleep(wait)
        subprocess.run(["curl", "-s", "-x", PROXY, "-A", UA, "-o", out, url],
                       check=False)
        try:
            txt = open(out, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if len(txt) > 20000 and "floors" in txt:
            return "ok %dKB" % (len(txt) // 1024)
        if len(txt) > 20000 and "403" not in txt[:2000]:
            # 有页面但无 floors：也可能本就单层/无钉点
            return "ok-nofloors %dKB" % (len(txt) // 1024)
    return "FAIL"


def main():
    os.makedirs(REF, exist_ok=True)
    bad = []
    for did, slug in SLUG.items():
        r = fetch(slug)
        print("%-24s %-30s %s" % (did, slug, r), flush=True)
        if r == "FAIL":
            bad.append(did)
    print("\n失败：", bad or "无")


if __name__ == "__main__":
    main()
