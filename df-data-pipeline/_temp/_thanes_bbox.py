# -*- coding: utf-8 -*-
"""分析 oldironforge 每块瓦片的非黑边界，推断真实格位。"""
import os
from PIL import Image, ImageChops
d = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png/oldironforge"
def nb(im):
    bg = Image.new("RGB", im.size, (0, 0, 0))
    return ImageChops.difference(im.convert("RGB"), bg).convert("L").point(lambda v: 255 if v > 8 else 0).getbbox()
for n in range(1, 13):
    im = Image.open(os.path.join(d, "t%02d.png" % n))
    bb = nb(im)
    # 右边/下边是否贴黑
    r = "-" if bb is None else "x%d..%d y%d..%d" % (bb[0], bb[2], bb[1], bb[3])
    print("t%02d %s  %s" % (n, im.size, r))
