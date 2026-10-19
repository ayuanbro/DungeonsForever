import sys
from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
box = [float(x) for x in sys.argv[3:7]]
im = Image.open(src)
w, h = im.size
x1, y1, x2, y2 = int(w * box[0]), int(h * box[1]), int(w * box[2]), int(h * box[3])
crop = im.crop((x1, y1, x2, y2))
cw, ch = crop.size
scale = 1400.0 / cw
crop = crop.resize((1400, int(ch * scale)), Image.LANCZOS)
crop.save(dst)
print("saved", dst, crop.size)
