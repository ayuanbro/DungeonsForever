"""分析每块瓦片的非黑内容边界，反推网格排布。"""
import os
import re
import sys
import numpy as np
from PIL import Image

d = sys.argv[1]
files = {}
for x in os.listdir(d):
    m = re.search(r"(\d+)\.png$", x)
    if m:
        files[int(m.group(1))] = os.path.join(d, x)

for i in sorted(files):
    a = np.asarray(Image.open(files[i]).convert("RGB")).astype(np.int16)
    # 近黑判定
    nb = (a.max(axis=2) > 12)
    rows = np.where(nb.any(axis=1))[0]
    cols = np.where(nb.any(axis=0))[0]
    if len(rows) == 0:
        print("#%-3d 全黑" % i)
        continue
    print("#%-3d 非黑区域 x[%3d..%3d] y[%3d..%3d]  黑占比 %.1f%%  均色 %s" % (
        i, cols[0], cols[-1], rows[0], rows[-1],
        100.0 * (1 - nb.mean()),
        tuple(int(v) for v in a[nb].mean(axis=0)) if nb.any() else None,
    ))
