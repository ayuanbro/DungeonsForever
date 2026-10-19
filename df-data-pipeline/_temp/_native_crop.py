import sys
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
x1, y1, x2, y2 = [int(v) for v in sys.argv[3:7]]
zoom = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
im = Image.open(src).convert("RGB")
c = im.crop((x1, y1, x2, y2))
if zoom != 1.0:
    c = c.resize((int(c.width * zoom), int(c.height * zoom)), Image.LANCZOS)
c.save(dst)
print("saved", dst, c.size)
