import os
from fontTools.ttLib import TTFont

ROOT = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns"
CJK = "漢為說龍劍護裝戰擊體顯髮網醫師臺灣內沒強換產盜綠"
LAT = "ABCabc123"


def cmap_of(p):
    f = TTFont(p, fontNumber=0, lazy=True)
    cm = set()
    for t in f["cmap"].tables:
        cm |= set(t.cmap.keys())
    f.close()
    return cm


def scan(label, folder):
    tot = cjk = lat = neither = 0
    cjk_names = []
    for dp, dn, fn in os.walk(folder):
        for f in fn:
            if not f.lower().endswith((".ttf", ".otf", ".ttc")):
                continue
            p = os.path.join(dp, f)
            tot += 1
            try:
                cm = cmap_of(p)
            except Exception:
                neither += 1
                continue
            has_cjk = all(ord(c) in cm for c in CJK)
            has_lat = all(ord(c) in cm for c in LAT)
            if has_cjk:
                cjk += 1
                cjk_names.append(os.path.relpath(p, folder))
            elif has_lat:
                lat += 1
            else:
                neither += 1
    print("[%s] total=%d  含完整中文=%d  仅拉丁/部分=%d  解析失败=%d" % (label, tot, cjk, lat, neither))
    for n in cjk_names[:25]:
        print("     CJK:", n)


scan("EllesmereUI", os.path.join(ROOT, "EllesmereUI"))

# 其他插件里的字体目录（只统计，不逐个打印）
others = {}
for d in sorted(os.listdir(ROOT)):
    if d.startswith("EllesmereUI"):
        continue
    p = os.path.join(ROOT, d)
    if not os.path.isdir(p):
        continue
    n = sum(1 for dp, dn, fn in os.walk(p) for f in fn if f.lower().endswith((".ttf", ".otf", ".ttc")))
    if n:
        others[d] = n
print("\n其他插件自带字体数（前 20）:", sorted(others.items(), key=lambda kv: -kv[1])[:20])
