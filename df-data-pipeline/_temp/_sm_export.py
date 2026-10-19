# -*- coding: utf-8 -*-
"""导出 ScarletMonasteryOld 的 4 层整图（12 块拼接，保留 1002x668 口径）。

只为「血色 4 分区 = 4 张独立地图」这件事出对照图（2026-10-01 用户点名索引）。
复用 _map_inv.json 的 fids；已有瓦片就跳过。产物 _temp/_mapcheck/full/<prefix>/tNN.png + _sm_lN.png
"""
import json, os, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LYCH = os.path.join(os.path.dirname(sys.executable), "..", "..", "..", "node", "versions",
                    "22.22.2-5", "node.exe")
LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-5/node.exe"
WRAP = r"C:/Users/Administrator/.workbuddy/skills/lycheedev/scripts/lycheedev.mjs"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
BS = chr(92)

inv = json.load(open(os.path.join(HERE, "_map_inv.json"), encoding="utf-8"))
cands = {}
for c in inv.get("sm_graveyard", []):
    parts = c["path"].split(BS)
    if len(parts) >= 4 and parts[2].lower() == "scarletmonasteryold":
        cands[parts[3]] = c

print("候选:", sorted(cands))
for base in ["scarletmonastery1_", "scarletmonastery2_", "scarletmonastery3_", "scarletmonastery4_"]:
    c = cands.get(base)
    if not c:
        print("缺", base); continue
    d = os.path.join(HERE, "_mapcheck", "full", "scarletmonasteryold__" + base)
    os.makedirs(d, exist_ok=True)
    ims = []
    for n in range(1, 13):
        f = os.path.join(d, "t%02d.png" % n)
        if not (os.path.exists(f) and os.path.getsize(f) > 500):
            fid = c.get("fids", {}).get(str(n))
            subprocess.run([LYCH, WRAP, "asset", "export", "--snapshot", PIN, "--installation", INST,
                            "--file-id", str(fid), "--encoding", "png", "--output", f,
                            "--overwrite", "--format", "json"],
                           capture_output=True, text=True, env=env)
        ims.append(Image.open(f).convert("RGB") if os.path.exists(f) and os.path.getsize(f) > 500 else None)
    canvas = Image.new("RGB", (1024, 768), (0, 0, 0))
    for idx, im in enumerate(ims):
        if im:
            r_, c_ = divmod(idx, 4)
            canvas.paste(im, (c_ * 256, r_ * 256))
    out = os.path.join(HERE, "_sm_%s.png" % base)
    canvas.save(out)
    print("ok", base, sum(1 for i in ims if i), "/12 ->", out, canvas.size)
