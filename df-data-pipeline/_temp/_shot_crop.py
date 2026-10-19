# -*- coding: utf-8 -*-
import sys
from PIL import Image, ImageDraw

src = sys.argv[1]
out = sys.argv[2]
x0, y0, x1, y1 = (int(v) for v in sys.argv[3].split(','))
z = int(sys.argv[4]) if len(sys.argv) > 4 else 3
im = Image.open(src).convert('RGB')
crop = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST)
d = ImageDraw.Draw(crop)
for i in range(x0, x1):
    if i % 10 == 0:
        cx = (i - x0) * z
        d.line([(cx, 0), (cx, crop.height)], fill=(255, 0, 0), width=1)
crop.save(out)
print('saved', out, crop.size, 'origin x0=%d y0=%d zoom=%d' % (x0, y0, z))
