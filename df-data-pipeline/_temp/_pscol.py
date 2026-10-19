from PIL import Image

p = r"C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-10-18T07-09-22-434Z-691a85bb.png"
im = Image.open(p).convert("RGB")
w, h = im.size


def cls(c):
    r, g, b = c
    if r > 180 and g > 150 and b < 90:
        return "Y"
    if g > 140 and r < 120:
        return "G"
    if r > 200 and g > 200 and b > 200:
        return "W"
    if abs(r - 27) < 12 and abs(g - 30) < 12 and abs(b - 36) < 12:
        return "."
    return "x"


for x in (117, 294, 490, 654, 842):
    runs = []
    prev = None
    start = 0
    for y in range(40, 430):
        c = cls(im.getpixel((x, y)))
        if c != prev:
            if prev is not None:
                runs.append((prev, start, y - 1))
            prev = c
            start = y
    runs.append((prev, start, 429))
    out = " ".join("%s:%d-%d" % (a, b, c) for a, b, c in runs if a not in ".x" or c - b > 3)
    print("x=%d  %s" % (x, out))
