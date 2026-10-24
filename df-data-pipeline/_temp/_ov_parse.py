# -*- coding: utf-8 -*-
"""解析 wh_ov_*.html（forever 副本 overview 攻略页）→ _ov_parsed.json

每页抽出：
- level: 推荐等级句
- overview: Overview 段纯文本
- location: Location 段（含 H/A 通道、npc/item/zone 引用）
- maps: [{zone, pins:[{x,y,type,label}]}]
- quests: Quests 段文本
- trash: Trash 段文本（含 npc/spell id）
- bosses: [{name, npc, text, spells:[id]}]
- raw_bbcode: 整段 BBCode（后续翻译/复核用）
"""
import os, re, json, html as H

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_ref_wowhead")

SLUGS = [s[:-5] for s in os.listdir(OUT) if s.startswith("wh_ov_") and s.endswith(".html")]

# 我方 did → wowhead slug（仅本次抓到的 17 本）
DID = {
    "ragefire-chasm": "ragefire_chasm",
    "wailing-caverns": "wailing_caverns",
    "the-deadmines": "the_deadmines",
    "shadowfang-keep": "shadowfang_keep",
    "blackfathom-deeps": "blackfathom_deeps",
    "the-stockade": "the_stockade",
    "gnomeregan": "gnomeregan",
    "razerfen-kraul": "razorfen_kraul",
    "razorfen-downs": "razorfen_downs",
    "scarlet-monastery-graveyard": "sm_graveyard",
    "scarlet-monastery-library": "sm_library",
    "scarlet-monastery-armory": "sm_armory",
    "scarlet-monastery-cathedral": "sm_cathedral",
    "excavation-site-wetlands": "excavation_wetlands",
    "city-of-dalaran": "city_of_dalaran",
    "hall-of-thanes": "hall_of_thanes",
    "ruins-of-lordaeron": "ruins_of_lordaeron",
}


def unesc(seg):
    seg = seg.replace("\\r\\n", "\n").replace("\\/", "/").replace('\\"', '"')
    return seg


def get_bbcode(h):
    """抠出页面里的整段指南 BBCode（从第一个 [h2 type=bar 到 guide-body 结尾）。"""
    i0 = h.find("[h2 type=bar")
    if i0 < 0:
        return ""
    i1 = h.find('"guide-body"', i0)
    if i1 < 0:
        i1 = min(i0 + 90000, len(h))
    return unesc(h[i0:i1])


def strip_bb(s):
    """BBCode → 纯文本（保留 [[npc=123]]/[[spell=456]]/[[item=…]] 引用记号）。"""
    s = re.sub(r"\[/?pad\]|\[br\]|\[/?(center|columns|column|grid|div|ul|li)\b[^\]]*\]", " ", s)
    s = re.sub(r"\[(npc|spell|item|quest|zone|item)(?:=(\w+))?\]", r"[\1=\2]", s)
    s = re.sub(r"\[(box|tab|tabs|section-header|h2|h3|i|b|color|span|img|icon|map|pin|screenshot)\b[^\]]*\]", "", s)
    s = re.sub(r"\[/\w+\]", "", s)
    s = H.unescape(s)
    return re.sub(r"[ \t]+", " ", s)


def section(bb, toc):
    m = re.search(r'\[h2 type=bar toc="%s"\](.*?)(?=\[h2 type=bar|\Z)' % re.escape(toc), bb, re.S)
    return m.group(1) if m else ""


def parse_page(did, slug):
    h = open(os.path.join(OUT, "wh_ov_%s.html" % slug), encoding="utf-8").read()
    bb = get_bbcode(h)
    rec = {"did": did, "slug": slug, "maps": [], "bosses": []}

    # 地图与钉点
    for m in re.finditer(r"\[map\s+zone=(\d+)\](.*?)\[/map\]", bb, re.S):
        zone = int(m.group(1))
        pins = []
        for p in re.finditer(r"\[pin\s+x=([\d.]+)\s+y=([\d.]+)\s+type=(\d+)\](?:([^\[]*))?", m.group(2)):
            pins.append({"x": float(p.group(1)), "y": float(p.group(2)),
                         "type": int(p.group(3)), "label": (p.group(4) or "").strip()})
        rec["maps"].append({"zone": zone, "pins": pins})

    # 等级
    lv = re.search(r"recommended level for [^.]*(\d+)\s*(?:to|-|and)\s*(\d+)", bb)
    if lv:
        rec["level"] = "%s-%s" % (lv.group(1), lv.group(2))

    # Overview / Location / Quests / Trash 段
    for toc, key in [("Overview", "overview"), ("Location", "location"),
                     ("Quests", "quests"), ("Trash Mobs", "trash")]:
        seg = section(bb, toc)
        rec[key] = strip_bb(seg).strip()
        rec[key + "_bb"] = seg

    # Bosses：box-highlight 块
    for m in re.finditer(r'\[box-highlight name="([^"]+)"\](.*?)(?=\[box-highlight|\[h2 type=bar|\Z)', bb, re.S):
        name, body = m.group(1), m.group(2)
        npc = re.search(r"\[npc=(\d+)\]", body)
        spells = re.findall(r"\[spell=(\d+)\]", body)
        text = strip_bb(re.sub(r"\[table.*?\[/table\]", " ", body, flags=re.S)).strip()
        rec["bosses"].append({
            "name": name, "npc": int(npc.group(1)) if npc else None,
            "spells": sorted(set(int(s) for s in spells)), "text": text,
        })
    rec["bbcode"] = bb
    return rec


def main():
    out = {}
    for slug, did in DID.items():
        fn = os.path.join(OUT, "wh_ov_%s.html" % slug)
        if not os.path.exists(fn):
            continue
        rec = parse_page(did, slug)
        out[did] = rec
        print("%-22s maps=%d pins=%d bosses=%d lvl=%s trash=%d chars" % (
            did, len(rec["maps"]), sum(len(m["pins"]) for m in rec["maps"]),
            len(rec["bosses"]), rec.get("level", "-"), len(rec["trash"])))
    json.dump(out, open(os.path.join(HERE, "_ov_parsed.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("done -> _ov_parsed.json")


if __name__ == "__main__":
    main()
