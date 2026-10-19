import sys
from PIL import Image, ImageDraw

src = "C:/Users/Administrator/AppData/Local/WuxianWorkshop/snaps/snap-143749-619.png"
im = Image.open(src).convert("RGB")
Z = 6
boxes = [
    ("A  top col2", 985, 880, 1090, 965),
    ("B  top col4", 1345, 880, 1450, 965),
    ("C  bot col2", 985, 1110, 1090, 1200),
    ("D  bot col4", 1345, 1110, 1450, 1200),
]
tw = (boxes[0][3] - boxes[0][1]) * Z
th = (boxes[0][4] - boxes[0][2]) * Z
pad = 26
W = tw * 2 + 30
H = (th + pad) * 2 + 10
out = Image.new("RGB", (W, H), (18, 20, 22))
d = ImageDraw.Draw(out)
for i, (lab, x1, y1, x2, y2) in enumerate(boxes):
    c = im.crop((x1, y1, x2, y2)).resize(((x2 - x1) * Z, (y2 - y1) * Z), Image.LANCZOS)
    ox = 10 + (i % 2) * (tw + 10)
    oy = 6 + (i // 2) * (th + pad)
    out.paste(c, (ox, oy + pad))
    d.text((ox + 2, oy + 4), lab, fill=(255, 210, 90))
out.save("D:/workspace/DungeonsForever/_temp/junc2.png")
print("saved", out.size)
