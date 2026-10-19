import sys
from PIL import Image

src = sys.argv[1]
x1, y1, x2, y2 = [int(v) for v in sys.argv[2:6]]
im = Image.open(src).convert("RGB")
px = im.load()


def isline(p):
    r, g, b = p
    lo = min(r, g, b)
    hi = max(r, g, b)
    return 95 < lo and hi < 175 and (hi - lo) < 14


rows = []
for y in range(y1, y2):
    n = 0
    for x in range(x1, x2):
        if isline(px[x, y]):
            n += 1
    if n > 120:
        rows.append((y, n))
for y, n in rows:
    print("row y=%d n=%d" % (y, n))
