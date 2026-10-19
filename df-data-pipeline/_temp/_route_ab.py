# -*- coding: utf-8 -*-
import io, re, math
from PIL import Image, ImageDraw

FR = 'D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/ForeverDungeonRoutes/Data/DefaultRoutes.lua'
ROOT = 'D:/workspace/DungeonsForever/_temp/_route_plan'
W, H = 1002, 668

s = io.open(FR, encoding='utf-8').read()
body = re.search(r'DR\.DefaultRoutes\["blackfathom"\] = \{(.*?)\n\}\n', s, re.S).group(1)
paths = []
for pm in re.finditer(r'\{kind="(main|side)", floor=(\d+),(.*?)pts=\{([^}]*)\}\}', body):
    nums = [float(x) for x in pm.group(4).split(',') if x.strip()]
    pts = [(nums[i] * W, nums[i + 1] * H) for i in range(0, len(nums) - 1, 2)]
    paths.append((pm.group(1), int(pm.group(2)), pts))

stops = []
for sm in re.finditer(r'\{kind="(\w+)", floor=(\d+), x=([\d.]+), y=([\d.]+), name="([^"]*)"', body):
    stops.append((sm.group(1), int(sm.group(2)), float(sm.group(3)) * W, float(sm.group(4)) * H, sm.group(5)))

for f, lay in ((221, 1), (222, 2)):
    big = Image.open('%s/img/bfd_L%d.jpg' % (ROOT, lay)).convert('RGBA').resize((W * 2, H * 2), Image.LANCZOS)
    ov = Image.new('RGBA', big.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for kind, pf, pts in paths:
        if pf != f:
            continue
        sp = [(x * 2, y * 2) for x, y in pts]
        d.line(sp, fill=(0, 220, 255, 230), width=3)
        for p in sp[:1]:
            d.ellipse([p[0]-6, p[1]-6, p[0]+6, p[1]+6], fill=(255, 0, 0, 255))
        for p in sp[-1:]:
            d.ellipse([p[0]-6, p[1]-6, p[0]+6, p[1]+6], fill=(0, 255, 0, 255))
    for kind, pf, x, y, name in stops:
        if pf != f:
            continue
        d.ellipse([x*2-5, y*2-5, x*2+5, y*2+5], fill=(255, 220, 0, 255))
    Image.alpha_composite(big, ov).convert('RGB').save('%s/ab_L%d.png' % (ROOT, lay))
    print('ab_L%d' % lay)
