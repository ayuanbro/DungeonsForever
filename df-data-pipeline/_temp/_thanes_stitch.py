# -*- coding: utf-8 -*-
"""按真实瓦片编号（fid 排序 != 编号）重拼 oldironforge。"""
import json, os
from PIL import Image
LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
OUT = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png"
d = os.path.join(OUT, "oldironforge")
# fid -> 真实瓦片编号（来自 listfile：oldironforge<N>.blp）
FID2N = {2470313: 1, 2470314: 10, 2470315: 11, 2470316: 12, 2470317: 2, 2470318: 3,
         2470319: 4, 2470320: 5, 2470321: 6, 2470322: 7, 2470323: 8, 2470324: 9}
MY = {1: 1, 10: 2, 11: 3, 12: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12}  # 编号 -> 我的 t 文件号
canvas = Image.new("RGB", (4 * 256, 3 * 256), (0, 0, 0))
for n in range(1, 13):                     # n = 真实瓦片编号（行优先）
    im = Image.open(os.path.join(d, "t%02d.png" % MY[n])).convert("RGB")
    r_, c_ = divmod(n - 1, 4)
    canvas.paste(im, (c_ * 256, r_ * 256))
canvas.save(os.path.join(OUT, "oldironforge_ok.png"))
print("拼好", canvas.size)
