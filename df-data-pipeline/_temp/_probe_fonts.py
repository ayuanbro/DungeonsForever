import os
import sys
from fontTools.ttLib import TTFont

ROOT = r"D:/Game/World of Warcraft"
DIRS = ["_classic_beta_", "_cn_beta_", "_classic_", "_classic_era_", "_classic_titan_", "_retail_"]
TW = "龍劍護裝藥務戰擊體顯髮網醫師臺灣們個為與這說點數"
CN = "龙剑护装药务战击体显发网医师台湾们个为与这点数"


def probe(p):
    f = TTFont(p, fontNumber=0, lazy=True)
    cmap = set()
    for t in f["cmap"].tables:
        cmap |= set(t.cmap.keys())
    fam = ""
    for rec in f["name"].names:
        if rec.nameID == 1:
            fam = rec.toUnicode()
            break
    n = f["maxp"].numGlyphs
    tw = "".join(c for c in TW if ord(c) not in cmap)
    cn = "".join(c for c in CN if ord(c) not in cmap)
    f.close()
    return fam, n, len(cmap), len(tw), len(cn)


for d in DIRS:
    fd = os.path.join(ROOT, d, "Fonts")
    if not os.path.isdir(fd):
        print("== %s : (no Fonts dir)" % d)
        continue
    print("== %s" % d)
    for name in sorted(os.listdir(fd)):
        if not name.lower().endswith((".ttf", ".otf")):
            continue
        p = os.path.join(fd, name)
        try:
            fam, n, cm, tm, cm2 = probe(p)
            print("   %-18s %10d %7d %7d  %-24s TWmiss=%d CNmiss=%d" % (name, os.path.getsize(p), n, cm, fam, tm, cm2))
        except Exception as e:
            print("   %-18s %10d  ERR %s" % (name, os.path.getsize(p), e))
