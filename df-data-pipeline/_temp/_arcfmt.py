import sys
from PIL import Image

p = "D:/workspace/DungeonsForever/Media/DFLineArc.tga"
raw = open(p, "rb").read()
print("len", len(raw))
print("header", list(raw[:18]))
print("idlen", raw[0], "cmap", raw[1], "type", raw[2], "bpp", raw[16], "desc", raw[17])
im = Image.open(p).convert("RGBA")
px = im.load()
for y in range(0, 40, 2):
    row = []
    for x in range(0, 40, 2):
        r, g, b, a = px[x, y]
        row.append("%3d/%3d" % (a, r))
    print(y, " ".join(row))
