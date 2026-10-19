import sys
from PIL import Image

path = sys.argv[1]
y = int(sys.argv[2])

im = Image.open(path).convert("RGB")
w, h = im.size
px = im.load()

runs = []
prev = None
start = 0
for x in range(w):
    r, g, b = px[x, y]
    if g > 140 and r < 140 and b < 160:
        c = "G"
    elif r > 110 and abs(r - g) < 25 and abs(g - b) < 25:
        c = "X"
    else:
        c = "."
    if c != prev:
        if prev in ("G", "X") and x - start > 3:
            runs.append((prev, start, x - 1))
        prev = c
        start = x
if prev in ("G", "X") and w - start > 3:
    runs.append((prev, start, w - 1))
print("y=%d h=%d" % (y, h))
print(" | ".join("%s:%d-%d" % (c, a, b) for c, a, b in runs))
