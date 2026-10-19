# -*- coding: utf-8 -*-
"""导通灵学院 4 层整图（12 块拼接，保留 1002x668 原始口径，不裁 bbox）。"""
import json, os, subprocess
from PIL import Image
LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
BS = chr(92)
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ref")

inv = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_map_inv.json"), encoding="utf-8"))
want = {}
for did, cands in inv.items():
    for c in cands:
        parts = c["path"].split(BS)
        if len(parts) >= 4 and parts[2].lower() == "scholomanceold":
            want[parts[3]] = c

for base in ["scholomanceold1_", "scholomanceold2_", "scholomanceold3_", "scholomanceold4_"]:
    c = want.get(base)
    if not c:
        print("缺", base); continue
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mapcheck", "sch", base)
    os.makedirs(d, exist_ok=True)
    ims = []
    for n in range(1, 13):
        f = os.path.join(d, "t%02d.png" % n)
        if not (os.path.exists(f) and os.path.getsize(f) > 500):
            fid = c.get("fids", {}).get(str(n))
            subprocess.run([LYCH, "asset", "export", "--snapshot", PIN, "--installation", INST,
                            "--file-id", str(fid), "--encoding", "png", "--output", f,
                            "--overwrite", "--format", "json"],
                           capture_output=True, text=True, env=env, shell=True)
        ims.append(Image.open(f).convert("RGB") if os.path.exists(f) and os.path.getsize(f) > 500 else None)
    canvas = Image.new("RGB", (1024, 768), (0, 0, 0))
    for idx, im in enumerate(ims):
        if im:
            r_, c_ = divmod(idx, 4)
            canvas.paste(im, (c_ * 256, r_ * 256))
    out = os.path.join(OUTDIR, "sch_%s.png" % base)
    canvas.save(out)
    print("ok", base, sum(1 for i in ims if i), "/12 ->", out, canvas.size)
