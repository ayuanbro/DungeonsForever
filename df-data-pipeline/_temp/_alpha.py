import sys
from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
z = int(sys.argv[3]) if len(sys.argv) > 3 else 8
im = Image.open(src).convert("RGBA")
print("size", im.size)
a = im.split()[-1]
a = a.resize((im.width * z, im.height * z), Image.NEAREST)
a.save(dst)
print("saved", dst)
