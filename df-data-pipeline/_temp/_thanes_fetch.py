# -*- coding: utf-8 -*-
"""导出 oldironforge（领主大厅所在的老铁炉堡）地图瓦片并拼图。"""
import json, os, subprocess
from PIL import Image
LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
OUT = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
d = os.path.join(OUT, "oldironforge"); os.makedirs(d, exist_ok=True)
IDS = {i: 2470313 + i - 1 for i in range(1, 13)}
ok = 0
for n in range(1, 13):
    p = os.path.join(d, "t%02d.png" % n)
    if not os.path.exists(p):
        r = subprocess.run([LYCH, "asset", "export", "--snapshot", PIN, "--installation", INST,
                            "--file-id", str(IDS[n]), "--encoding", "png", "--output", p,
                            "--format", "json"], capture_output=True, text=True, env=env, shell=True)
        try:
            j = json.loads(r.stdout)
        except Exception:
            print("  n=%d 非 json: %s" % (n, r.stdout[:200])); continue
        if not j.get("ok"):
            print("  n=%d ERR %s" % (n, json.dumps(j.get("error"), ensure_ascii=False)[:160])); continue
    ok += 1
print("导出 %d/12" % ok)
if ok == 12:
    ims = [Image.open(os.path.join(d, "t%02d.png" % n)).convert("RGB") for n in range(1, 13)]
    print("单块尺寸", ims[0].size)
    W, H = ims[0].size
    canvas = Image.new("RGB", (W * 4, H * 3), (0, 0, 0))
    for idx, im in enumerate(ims):          # 行优先：1..4 第一行
        r_, c_ = divmod(idx, 4)
        canvas.paste(im, (c_ * W, r_ * H))
    canvas.save(os.path.join(OUT, "oldironforge_4x3.png"))
    crop = canvas.convert("RGBA"); bb = crop.getbbox()
    crop.crop(bb).save(os.path.join(OUT, "oldironforge_crop.png"))
    print("拼图", canvas.size, "内容 bbox", bb, "->", crop.crop(bb).size)
