# -*- coding: utf-8 -*-
"""抓 foreverchanges.pro 各副本页的首领钉点（npcID + left%/top% + 名）。

站点把钉点写成 <button class="dgx-pin" style="left:56.1%;top:38%"
aria-label="奥格弗林特"> … 头像 url(/wow-ui/bosses/<npcid>.webp)。
地图贴图尺寸 = 1002×668（与本插件 ART_W/ART_H 同口径），故 left/top 可直接用。

缓存到 _temp/_ref/dg_<slug>.html，二次运行不再联网。
"""
import os, re, json, time, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "_ref")
PROXY = "http://127.0.0.1:7897"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 本插件 id → 站点 slug（27 个有客户端内地图的副本）
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


def fetch(slug):
    out = os.path.join(REF, "dg_%s.html" % slug)
    if os.path.exists(out) and os.path.getsize(out) > 20000:
        return open(out, encoding="utf-8", errors="replace").read()
    url = "https://foreverchanges.pro/zh-cn/dungeons/%s" % slug
    subprocess.run(["curl", "-s", "-x", PROXY, "-A", UA, "-o", out, url], check=False)
    time.sleep(0.8)
    try:
        return open(out, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


PIN_RE = re.compile(r'<button[^>]*class="dgx-pin"[^>]*>(.*?)</button>', re.S)
TAG_RE = re.compile(r'<button[^>]*class="dgx-pin"[^>]*>')
ST_RE = re.compile(r'style="([^"]*)"')
AL_RE = re.compile(r'aria-label="([^"]*)"')
NPC_RE = re.compile(r'/wow-ui/bosses/(\d+)\.webp')
MAP_RE = re.compile(r'<img[^>]*src="(/dungeons/maps/[^"]+)"[^>]*>')


def parse(html):
    m = MAP_RE.search(html)
    mapimg = m.group(1) if m else None
    pins = []
    for m in PIN_RE.finditer(html):
        tag = TAG_RE.search(m.group(0))
        if not tag:
            continue
        tag = tag.group(0)
        st = ST_RE.search(tag)
        al = AL_RE.search(tag)
        npc = NPC_RE.search(m.group(0))
        pos = {}
        if st:
            for k, v in re.findall(r'(left|top)\s*:\s*([0-9.]+)%', st.group(1)):
                pos[k] = float(v)
        pins.append({
            "npcid": int(npc.group(1)) if npc else None,
            "name": al.group(1) if al else None,
            "left": pos.get("left"),
            "top": pos.get("top"),
        })
    return mapimg, pins


def main():
    out = {}
    for did, slug in SLUG.items():
        html = fetch(slug)
        mapimg, pins = parse(html)
        out[did] = {"slug": slug, "map": mapimg, "pins": pins}
        print("%-24s %-30s map=%-42s pins=%d" % (did, slug, mapimg, len(pins)))
    dst = os.path.join(HERE, "_boss_pins_raw.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n写出", dst)


if __name__ == "__main__":
    main()
