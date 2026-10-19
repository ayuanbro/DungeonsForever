# -*- coding: utf-8 -*-
"""导出 ScholomanceOld 第 1 层 12 块瓦片并拼成 1024x768 空白羊皮纸底图。"""
import os, subprocess
from PIL import Image

LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")

OUT = os.path.dirname(os.path.abspath(__file__))
TDIR = os.path.join(OUT, "tiles_scholomanceold1")
os.makedirs(TDIR, exist_ok=True)

FIDS = {1: 5332424, 2: 5332428, 3: 5332429, 4: 5332430, 5: 5332431, 6: 5332432,
        7: 5332433, 8: 5332434, 9: 5332435, 10: 5332425, 11: 5332426, 12: 5332427}

for n, fid in sorted(FIDS.items()):
    f = os.path.join(TDIR, "tile_%02d.png" % n)
    if os.path.exists(f) and os.path.getsize(f) > 1000:
        continue
    r = subprocess.run([LYCH, "asset", "export", "--snapshot", PIN, "--installation", INST,
                        "--file-id", str(fid), "--encoding", "png",
                        "--output", f, "--overwrite", "--format", "json"],
                       capture_output=True, text=True, env=env, shell=True)
    print("tile", n, "ok" if os.path.exists(f) else "FAIL", flush=True)

canvas = Image.new("RGB", (1024, 768), (0, 0, 0))
for n in range(1, 13):
    r_, c_ = divmod(n - 1, 4)
    im = Image.open(os.path.join(TDIR, "tile_%02d.png" % n)).convert("RGB")
    canvas.paste(im, (c_ * 256, r_ * 256))
base = os.path.join(OUT, "parchment_base.png")
canvas.save(base)
print("拼好", base, canvas.size)
