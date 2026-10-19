import sys
from PIL import Image

src = sys.argv[1]
ys = [int(v) for v in sys.argv[2].split(",")]
x1 = int(sys.argv[3]) if len(sys.argv) > 3 else 600
x2 = int(sys.argv[4]) if len(sys.argv) > 4 else 1550
im = Image.open(src).convert("RGB")
px = im.load()


def cls(p):
    r, g, b = p
    if g > 90 and g > r + 30 and g > b + 20:
        return "G"
    if r > 85 and g > 85 and b > 85 and abs(r - g) < 40 and abs(g - b) < 45:
        return "X"
    if r > 120 and g > 80 and b < 90:
        return "Y"
    return "."


for y in ys:
    runs = []
    cur = None
    st = x1
    for x in range(x1, x2):
        c = cls(px[x, y])
        if cur is None:
            cur = c
            st = x
        elif c != cur:
            runs.append((cur, st, x - 1))
            cur = c
            st = x
    runs.append((cur, st, x2 - 1))
    out = [f"{c}:{a}-{b}" for c, a, b in runs if c != "." and b - a > 3]
    print(y, " | ".join(out))
