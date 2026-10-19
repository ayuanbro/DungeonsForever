# -*- coding: utf-8 -*-
"""把 12 块瓦片按多种候选排布拼出来，肉眼选对的。"""
import os
from PIL import Image, ImageDraw
d = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png/oldironforge"
ims = {n: Image.open(os.path.join(d, "t%02d.png" % n)).convert("RGB") for n in range(1, 13)}

def build(seq, cols, rows):
    """seq = 按 (行,列) 填的块号列表，长度 cols*rows"""
    canvas = Image.new("RGB", (cols * 256, rows * 256), (0, 0, 0))
    for i, n in enumerate(seq):
        r_, c_ = divmod(i, cols)
        canvas.paste(ims[n], (c_ * 256, r_ * 256))
    return canvas

CAND = {
    "A 4x3 行优先":   build(list(range(1, 13)), 4, 3),
    "B 4x3 列优先":   build([1,2,3,4,5,6,7,8,9,10,11,12][:0] or [1,5,9,2,6,10,3,7,11,4,8,12], 4, 3),
    "C 3x4 行优先":   build(list(range(1, 13)), 3, 4),
    "D 3x4 列优先":   build([1,5,9,2,6,10,3,7,11,4,8,12], 3, 4),
    "E 4x3 行优先翻转": build(list(range(12, 0, -1)), 4, 3),
    "F 6x2 行优先":   build(list(range(1, 13)), 6, 2),
}
S = 460
cell_w, cell_h = S, int(S * 0.75)
cols = 2; rows = (len(CAND) + 1) // 2
sheet = Image.new("RGB", (cols * (cell_w + 10), rows * (cell_h + 24)), (35, 35, 35))
dr = ImageDraw.Draw(sheet)
for i, (k, im) in enumerate(CAND.items()):
    r_, c_ = divmod(i, cols)
    x, y = c_ * (cell_w + 10), r_ * (cell_h + 24)
    sheet.paste(im.resize((cell_w, cell_h)), (x, y + 18))
    dr.text((x + 4, y + 3), k, fill=(255, 220, 120))
out = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png/oldironforge_cand.png"
sheet.save(out); print("ok", out, sheet.size)
