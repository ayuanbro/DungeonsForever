# -*- coding: utf-8 -*-
"""导出达拉然城客户端瓦片 2 层整图（12 块拼接，1002x668 口径），供与用户手绘图对比。

复用 _map_inv.json 的 fids；已有瓦片跳过。产物 _temp/_mapcheck/full/dalaran__dalaranN_/tNN.png
"""
import json, os, subprocess
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-5/node.exe"
WRAP = r"C:/Users/Administrator/.workbuddy/skills/lycheedev/scripts/lycheedev.mjs"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
BS = chr(92)

inv = json.load(open(os.path.join(HERE, "_map_inv.json"), encoding="utf-8"))
cands = {}
for c in inv.get("city_of_dalaran", []):
    parts = c["path"].split(BS)
    if len(parts) >= 4 and parts[2].lower() == "dalaran" and parts[3].lower().startswith("dalaran"):
        cands[parts[3].lower()] = c

print("候选:", sorted(cands))
for base in ["dalaran1_", "dalaran2_"]:
    c = cands.get(base)
    if not c:
        print("缺", base)
        continue
    d = os.path.join(HERE, "_mapcheck", "full", "dalaran__" + base)
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
    out = os.path.join(HERE, "_dalaran_%s.png" % base)
    canvas.save(out)
    print("ok", base, sum(1 for i in ims if i), "/12 ->", out, canvas.size)
