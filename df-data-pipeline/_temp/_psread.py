import sys
from PIL import Image

p = sys.argv[1]
x1, y1, x2, y2 = [int(v) for v in sys.argv[2:6]]
im = Image.open(p).convert("RGB")
px = im.load()


def cls(c):
    r, g, b = c
    if g > 110 and g > r + 40 and g > b + 40:
        return "G"
    if r > 140 and g > 110 and b < 90 and r > b + 70:
        return "Y"
    if abs(r - g) < 30 and abs(g - b) < 30:
        if r > 95:
            return "X"
        if r > 40:
            return "o"
        return "."
    if r > 150 and g < 110 and b < 110:
        return "R"
    if r > 200 and g > 200 and b > 200:
        return "W"
    return "?"


rows = []
for y in range(y1, y2):
    s = "".join(cls(px[x, y]) for x in range(x1, x2))
    rows.append("%4d %s" % (y, s))
print("     " + "".join(str((x1 + i) // 100 % 10) for i in range(x2 - x1)))
print("     " + "".join(str((x1 + i) // 10 % 10) for i in range(x2 - x1)))
print("     " + "".join(str((x1 + i) % 10) for i in range(x2 - x1)))
for r in rows:
    print(r)
