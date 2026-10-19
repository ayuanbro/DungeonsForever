# -*- coding: utf-8 -*-
"""拼接指定候选组的 12 块瓦片，缩略成一张对比图。路径从 _map_inv.json 里按目录名取，避免手写反斜杠。"""
import json, os, subprocess
from PIL import Image, ImageDraw

LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
D = r"D:/workspace/DungeonsForever/_temp/_mapcheck"

inv = json.load(open("_map_inv.json", encoding="utf-8"))
seen = {}
for did, cands in inv.items():
    for c in cands:
        seen.setdefault(c["path"], c)

# (中文名, 目录, base 前缀)
PICK = [
    ("哀嚎洞穴",   "wailingcaverns",           "wailingcaverns1_"),
    ("死亡矿井",   "thedeadmines",             "thedeadmines1_"),
    ("诺莫瑞根",   "gnomeregan",               "gnomeregan1_"),
    ("厄运之槌",   "diremaul",                 "diremaul1_"),
    ("黑石塔上层", "upperblackrockspire",      "upperblackrockspire1_"),
    ("达拉然城",   "dalaran",                  "dalaran1_"),
    ("洛丹伦废墟", "ruinsoflordaeronscenario", "ruinsoflordaeronscenario"),
    ("沉没的神庙", "thetempleofatalhakkar",    "thetempleofatalhakkar1_"),
    ("血色修道院", "scarletmonasteryold",      "scarletmonastery1_"),
    ("黑石深渊",   "blackrockdepths",          "blackrockdepths1_"),
]


def find(d, base):
    for p, c in seen.items():
        parts = p.split("\\")
        if len(parts) >= 4 and parts[2].lower() == d.lower() and parts[3].startswith(base):
            return c
    return None


def safe(p):
    return p.replace("Interface\\WorldMap\\", "").replace("\\", "__")


def get_imgs(path, c):
    d = os.path.join(D, "full", safe(path))
    os.makedirs(d, exist_ok=True)
    ims = []
    for n in range(1, 13):
        f = os.path.join(d, "t%02d.png" % n)
        if not (os.path.exists(f) and os.path.getsize(f) > 500):
            fid = c["fids"].get(str(n))
            if not fid:
                ims.append(None)
                continue
            subprocess.run([LYCH, "asset", "export", "--snapshot", PIN, "--installation", INST,
                            "--file-id", str(fid), "--encoding", "png", "--output", f,
                            "--overwrite", "--format", "json"],
                           capture_output=True, text=True, env=env, shell=True)
        ims.append(Image.open(f).convert("RGB") if os.path.exists(f) and os.path.getsize(f) > 500 else None)
    return ims


CW = 300
cells = []
for zh, d, base in PICK:
    c = find(d, base)
    if not c:
        print("%-10s 候选未找到" % zh)
        continue
    ims = get_imgs(c["path"], c)
    ok = sum(1 for i in ims if i)
    if not ok:
        print("%-10s 无块" % zh)
        continue
    W, H = 256, 256
    canvas = Image.new("RGB", (W * 4, H * 3), (0, 0, 0))
    for idx, im in enumerate(ims):
        if not im:
            continue
        r_, c_ = divmod(idx, 4)
        canvas.paste(im, (c_ * W, r_ * H))
    bb = canvas.convert("RGBA").getbbox()
    if bb:
        canvas = canvas.crop(bb)
    sc = CW / canvas.width
    thumb = canvas.resize((CW, max(1, int(canvas.height * sc))))
    cells.append((zh, thumb, ok))
    print("%-10s 块 %d/12  拼图 %s" % (zh, ok, canvas.size), flush=True)

PER = 5
rows = (len(cells) + PER - 1) // PER
TH = max(c[1].height for c in cells)
sheet = Image.new("RGB", (PER * (CW + 8), rows * (TH + 22)), (22, 22, 22))
dr = ImageDraw.Draw(sheet)
for i, (zh, im, ok) in enumerate(cells):
    r_, c_ = divmod(i, PER)
    x, y = c_ * (CW + 8), r_ * (TH + 22)
    sheet.paste(im, (x, y + 18))
    dr.text((x + 2, y + 3), "%s (%d/12)" % (zh, ok), fill=(255, 220, 120))
out = os.path.join(D, "_full_sheet.png")
sheet.save(out)
print("ok", out, sheet.size)
