# -*- coding: utf-8 -*-
import os, sys
from PIL import Image, ImageDraw
d = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png/oldironforge"
per = 6; S = 200
ims = [Image.open(os.path.join(d, "t%02d.png" % n)).convert("RGB").resize((S, S)) for n in range(1, 13)]
rows = (len(ims) + per - 1) // per
sheet = Image.new("RGB", (per * (S + 8), rows * (S + 22)), (30, 30, 30))
dr = ImageDraw.Draw(sheet)
for i, im in enumerate(ims):
    r_, c_ = divmod(i, per)
    x, y = c_ * (S + 8), r_ * (S + 22)
    sheet.paste(im, (x, y + 16))
    dr.text((x + 4, y + 2), "t%02d" % (i + 1), fill=(255, 220, 120))
out = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png/oldironforge_sheet.png"
sheet.save(out); print("ok", out, sheet.size)
