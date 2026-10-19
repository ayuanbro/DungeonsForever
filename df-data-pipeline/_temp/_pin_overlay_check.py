# -*- coding: utf-8 -*-
"""把自制副本钉点画到手绘 TGA 上，肉眼核对坐标是否落在正确位置。"""
import os, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
VH, CANVAS = 683, 1024
W, H = 1002, 668
D = json.load(open(os.path.join(HERE, '_bosspos_floors.json'), encoding='utf-8'))
NAMES = {'hall_of_thanes': 'HallOfThanes', 'ruins_of_lordaeron': 'RuinsOfLordaeron'}
try:
    F = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
except Exception:
    F = ImageFont.load_default()
for did, fn in NAMES.items():
    im = Image.open(os.path.join(DF, 'Media', 'Maps', fn + '.tga')).convert('RGB')
    im = im.crop((0, 0, CANVAS, VH)).resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for row in D[did]['1']:
        x, y = row['x'] / 100 * W, row['y'] / 100 * H
        r = 14
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 40, 40), width=4)
        d.line([x - r - 8, y, x + r + 8, y], fill=(255, 40, 40), width=2)
        d.line([x, y - r - 8, x, y + r + 8], fill=(255, 40, 40), width=2)
        d.text((x + r + 4, y - 34), row['zh'], fill=(255, 30, 30), font=F, stroke_width=2, stroke_fill=(255, 255, 255))
    out = os.path.join(HERE, '_pin_overlay_%s.png' % did)
    im.save(out)
    print('saved', out)
