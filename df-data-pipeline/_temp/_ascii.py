import sys
from PIL import Image

for src in sys.argv[1:]:
    im = Image.open(src).convert("RGB")
    px = im.load()
    W, H = im.size
    print("==", src, W, H)
    for y in range(H):
        row = []
        for x in range(W):
            r, g, b = px[x, y]
            v = (r + g + b) / 3.0
            if v > 110:
                row.append("#")
            elif v > 70:
                row.append("+")
            elif v > 45:
                row.append(".")
            else:
                row.append(" ")
        print("%2d %s" % (y, "".join(row)))
    print()
