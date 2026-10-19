import glob
import os
from fontTools.ttLib import TTFont

REPO = r"D:/workspace/DungeonsForever"
FD = r"D:/Game/World of Warcraft/_classic_beta_/Fonts"

files = [os.path.join(REPO, "Locales", "zhTW.lua"), os.path.join(REPO, "Locales", "zhCN.lua")]
files += glob.glob(os.path.join(REPO, "Core", "Data", "zhTW", "*.lua"))

chars = set()
for p in files:
    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
        for ch in fh.read():
            o = ord(ch)
            if 0x3400 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF:
                chars.add(ch)

print("corpus files =", len(files), " unique CJK chars =", len(chars))


def cmap_of(name):
    f = TTFont(os.path.join(FD, name), fontNumber=0, lazy=True)
    cm = set()
    for t in f["cmap"].tables:
        cm |= set(t.cmap.keys())
    f.close()
    return cm


for name in ["ARKai_C.ttf", "ARKai_T.ttf", "ARHei.ttf"]:
    cm = cmap_of(name)
    miss = sorted(c for c in chars if ord(c) not in cm)
    print("%-14s missing %4d / %d  (%.1f%%)" % (name, len(miss), len(chars), 100.0 * len(miss) / len(chars)))
    if miss:
        print("     sample:", "".join(miss[:60]))
