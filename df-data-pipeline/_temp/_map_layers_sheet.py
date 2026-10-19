# -*- coding: utf-8 -*-
"""层对比图：指定副本目录的若干『层前缀』，各导出 12 块瓦片拼成一张缩略图横排对比。

用途：确认文件名的层号到底是不是「楼层」，以及各层内容差异。
路径/fid 从 _map_inv.json 取，避免手写反斜杠。
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
D = r"D:/workspace/DungeonsForever/_temp/_mapcheck"
BS = chr(92)

inv = json.load(open(r"D:/workspace/DungeonsForever/_temp/_map_inv.json", encoding="utf-8"))
seen = {}
for _did, cands in inv.items():
    for c in cands:
        seen.setdefault(c["path"], c)

# (标题, 目录, [该目录下的层前缀])
JOBS = [
    ("奥达曼 · Uldaman", "uldaman",
     ["uldaman1_", "uldaman2_", "uldaman18_"]),
    ("诺莫瑞根 · Gnomeregan", "gnomeregan",
     ["gnomeregan1_", "gnomeregan2_", "gnomeregan3_", "gnomeregan4_", "gnomeregan10_"]),
]


def find(d, base):
    for p, c in seen.items():
        parts = p.split(BS)
        if len(parts) >= 4 and parts[2].lower() == d.lower() and parts[3].startswith(base):
            return p, c
    return None, None


def safe(p):
    return p.replace("Interface" + BS + "WorldMap" + BS, "").replace(BS, "__")


def layer_img(path, c, tag):
    d = os.path.join(D, "layers", safe(path))
    os.makedirs(d, exist_ok=True)
    ims = []
    for n in range(1, 13):
        f = os.path.join(d, "t%02d.png" % n)
        if not (os.path.exists(f) and os.path.getsize(f) > 500):
            fid = c.get("fids", {}).get(str(n))
            if not fid:
                ims.append(None)
                continue
            subprocess.run([LYCH, "asset", "export", "--snapshot", PIN, "--installation", INST,
                            "--file-id", str(fid), "--encoding", "png", "--output", f,
                            "--overwrite", "--format", "json"],
                           capture_output=True, text=True, env=env, shell=True)
        ims.append(Image.open(f).convert("RGB")
                   if os.path.exists(f) and os.path.getsize(f) > 500 else None)
    if not any(ims):
        return None, 0
    canvas = Image.new("RGB", (256 * 4, 256 * 3), (0, 0, 0))
    for idx, im in enumerate(ims):
        if im:
            r_, c_ = divmod(idx, 4)
            canvas.paste(im, (c_ * 256, r_ * 256))
    bb = canvas.convert("RGBA").getbbox()
    if bb:
        canvas = canvas.crop(bb)
    return canvas, sum(1 for i in ims if i)


CW = 320
for title, dr, prefixes in JOBS:
    cells = []
    for pre in prefixes:
        p, c = find(dr, pre)
        if not p:
            print("  %-24s 候选未在 inv 表里" % pre)
            continue
        img, ok = layer_img(p, c, pre)
        print("  %-24s 块 %2d/12  %s" % (pre, ok, img.size if img else "-"), flush=True)
        if img:
            sc = CW / img.width
            cells.append((pre, img.resize((CW, max(1, int(img.height * sc))))))
    if not cells:
        continue
    TH = max(c[1].height for c in cells)
    sheet = Image.new("RGB", (len(cells) * (CW + 10), TH + 24), (22, 22, 22))
    drw = ImageDraw.Draw(sheet)
    for i, (pre, im) in enumerate(cells):
        x, y = i * (CW + 10), 20
        sheet.paste(im, (x, y))
        drw.text((x + 3, 4), pre, fill=(255, 220, 120))
    out = os.path.join(D, "_layers_%s.png" % dr)
    sheet.save(out)
    print("  ->", out, sheet.size)
