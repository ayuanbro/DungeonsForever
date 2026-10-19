import sys
from PIL import Image


def cls(c):
    r, g, b = c
    if g > 110 and g - r > 45 and g - b > 45:
        return "G"
    if r > 170 and g > 135 and b < 100 and r - b > 100:
        return "Y"
    if max(r, g, b) - min(r, g, b) < 26 and 70 < r < 200:
        return "X"
    if r < 60 and g < 60 and b < 70:
        return "."
    return "?"


def runs(px, y, x1, x2, minlen=3):
    out = []
    cur = None
    s = x1
    for x in range(x1, x2):
        k = cls(px[x, y])
        if k != cur:
            if cur is not None and x - s >= minlen:
                out.append((cur, s, x - 1))
            cur = k
            s = x
    if cur is not None and x2 - s >= minlen:
        out.append((cur, s, x2 - 1))
    return out


p = sys.argv[1]
x1, x2 = int(sys.argv[2]), int(sys.argv[3])
y1, y2 = int(sys.argv[4]), int(sys.argv[5])
im = Image.open(p).convert("RGB")
px = im.load()
for y in range(y1, y2):
    r = runs(px, y, x1, x2)
    tot = sum(b - a + 1 for k, a, b in r if k in ("G", "Y"))
    if tot < 6:
        continue
    print("%4d %s" % (y, " ".join("%s[%d-%d]" % (k, a, b) for k, a, b in r if k in ("G", "Y", "X"))))
