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
    if r > 230 and g > 230 and b > 230:
        return "."
    return "?"


def runs(px, y, x1, x2, minlen=2):
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
    return [o for o in out if o[0] in ("G", "Y", "X")]


def main():
    p = sys.argv[1]
    im = Image.open(p).convert("RGB")
    px = im.load()
    W, H = im.size
    mode = sys.argv[2]
    if mode == "rows":
        for y in range(int(sys.argv[3]), int(sys.argv[4])):
            r = runs(px, y, 0, W)
            tot = sum(b - a + 1 for k, a, b in r)
            print("%4d n=%-4d %s" % (y, tot, " ".join("%s[%d-%d]" % (k, a, b) for k, a, b in r if b - a > 3)))
    elif mode == "line":
        y = int(sys.argv[3])
        print("y=%d" % y)
        for k, a, b in runs(px, y, 0, W):
            print("  %s %d..%d  len=%d" % (k, a, b, b - a + 1))
    elif mode == "col":
        x = int(sys.argv[3])
        y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        y2 = int(sys.argv[5]) if len(sys.argv) > 5 else H
        cur = None
        s = y1
        for y in range(y1, y2):
            k = cls(px[x, y])
            if k != cur:
                if cur is not None and y - s >= 2 and cur in ("G", "Y", "X"):
                    print("  %s %d..%d len=%d" % (cur, s, y - 1, y - s))
                cur = k
                s = y
        if cur in ("G", "Y", "X") and y2 - s >= 2:
            print("  %s %d..%d len=%d" % (cur, s, y2 - 1, y2 - s))


main()
