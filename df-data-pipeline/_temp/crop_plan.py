import sys
from PIL import Image

src = sys.argv[1]
out = sys.argv[2]
l = float(sys.argv[3]); t = float(sys.argv[4]); w = float(sys.argv[5]); h = float(sys.argv[6])

im = Image.open(src)
f = im.width / 2088.0
x0 = int(l * f) - 10
y0 = int(im.height - t * f) - 14
x1 = int((l + w) * f) + 10
y1 = int(im.height - (t - h) * f) + 14
im.crop((x0, y0, x1, y1)).save(out)
print("saved", out, (x0, y0, x1, y1))
