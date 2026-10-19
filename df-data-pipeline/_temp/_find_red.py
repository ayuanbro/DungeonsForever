# -*- coding: utf-8 -*-
# 找三张截图里红圈标记的质心，换算为地图画布百分比（与 ns.MapPins 同口径：x/宽, y/高）。
from PIL import Image

IMGS = [
    ('ragefire-chasm', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-892Z-a81ad3cf.jpg'),
    ('wailing-caverns', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-893Z-b78a9289.jpg'),
    ('the-deadmines', r'C:/Users/Administrator/.workbuddy/clipboard-images/clipboard-2026-10-03T23-42-49-895Z-c282c8c8.jpg'),
]

for slug, path in IMGS:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            # 用户标记红圈：饱和红（R 明显高于 G/B）
            if r > 190 and g < 90 and b < 90:
                xs.append(x)
                ys.append(y)
    if not xs:
        print(slug, 'NO RED')
        continue
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    print('%s  size=%dx%d  centroid=(%.0f, %.0f)  ->  %.1f, %.1f' % (
        slug, w, h, cx, cy, cx / w * 100, cy / h * 100))
