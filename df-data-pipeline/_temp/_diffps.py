from PIL import Image, ImageChops
import sys

a = Image.open(r"C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-18T07-09-22-434Z-691a85bb.png").convert("RGB")
b = Image.open(r"C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-18T07-09-22-436Z-359a3671.png").convert("RGB")
print("target", a.size, "game", b.size)

a2 = a.resize(b.size, Image.LANCZOS)
d = ImageChops.difference(a2, b)
px = d.load()
w, h = d.size

cells = 6
cw, ch = w // cells, h // cells
acc = [[0] * cells for _ in range(cells)]
for y in range(h):
    for x in range(w):
        r, g, bl = px[x, y]
        v = r + g + bl
        if v > 60:
            acc[y // ch][x // cw] += v

for row in acc:
    print(" ".join("%7d" % v for v in row))

out = Image.new("RGB", b.size)
op = out.load()
for y in range(h):
    for x in range(w):
        r, g, bl = px[x, y]
        v = min(255, (r + g + bl) * 2)
        op[x, y] = (v, v // 3, 0)
out.save(r"D:\workspace\DungeonsForever\_temp\diffmap.png")
print("saved diffmap")
