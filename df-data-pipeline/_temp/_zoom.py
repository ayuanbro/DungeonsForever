import sys
from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
k = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
im = Image.open(src).convert("RGB")
w, h = im.size
im = im.resize((int(w * k), int(h * k)), Image.NEAREST)
im.save(dst)
print("saved", dst, im.size, "src", (w, h))
