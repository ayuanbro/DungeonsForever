# -*- coding: utf-8 -*-
"""把导出的候选首块拼成联络表（按副本分组）。"""
import os, json, math
from PIL import Image, ImageDraw
D = r"D:/workspace/DungeonsForever/_temp/_mapcheck"
inv = json.load(open("_map_inv.json", encoding="utf-8"))
ex = json.load(open("_map_exists.json", encoding="utf-8"))
def safe(p): return p.replace("Interface\WorldMap\\", "").replace("\\", "__")
cells = []
for did, cands in inv.items():
    for c in cands:
        p = c["path"]
        f = os.path.join(D, safe(p) + ".png")
        if ex.get(p, {}).get("ok") and os.path.exists(f):
            cells.append((did, safe(p), f))
print("格子数", len(cells))
PER, CW, CH, LBL = 8, 168, 126, 15
rows = math.ceil(len(cells) / PER)
sheet = Image.new("RGB", (PER * (CW + 6), rows * (CH + LBL + 6)), (24, 24, 24))
dr = ImageDraw.Draw(sheet)
for i, (did, name, f) in enumerate(cells):
    r, c = divmod(i, PER)
    x, y = c * (CW + 6), r * (CH + LBL + 6)
    try:
        im = Image.open(f).convert("RGB").resize((CW, CH))
    except Exception:
        continue
    sheet.paste(im, (x, y + LBL))
    dr.text((x + 2, y + 2), name[:26], fill=(255, 220, 120))
    dr.text((x + 2, y + CH + LBL - 1), did[:24], fill=(120, 220, 255))
    dr.rectangle([x, y + LBL, x + CW - 1, y + LBL + CH - 1], outline=(80, 80, 80))
# 上下对半切两张，方便看
half = rows // 2
a = sheet.crop((0, 0, sheet.width, half * (CH + LBL + 6)))
b = sheet.crop((0, half * (CH + LBL + 6), sheet.width, sheet.height))
a.save(os.path.join(D, "_sheet_a.png")); b.save(os.path.join(D, "_sheet_b.png"))
print("A", a.size, "B", b.size)
