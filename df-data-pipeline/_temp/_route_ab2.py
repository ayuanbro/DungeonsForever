# -*- coding: utf-8 -*-
import io, re, json, math
from PIL import Image, ImageDraw

FR = 'D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/ForeverDungeonRoutes/Data/DefaultRoutes.lua'
ROOT = 'D:/workspace/DungeonsForever/_temp/_route_plan'
W, H = 1002, 668
s = io.open(FR, encoding='utf-8').read()
body = re.search(r'DR\.DefaultRoutes\["blackfathom"\] = \{(.*?)\n\}\n', s, re.S).group(1)
paths = []
for pm in re.finditer(r'\{kind="(main|side)", floor=(\d+),(.*?)pts=\{([^}]*)\}\}', body):
    nums = [float(x) for x in pm.group(4).split(',') if x.strip()]
    pts = [(nums[i] * 100, nums[i + 1] * 100) for i in range(0, len(nums) - 1, 2)]
    paths.append((pm.group(1), int(pm.group(2)), pts))

data = json.load(io.open(ROOT + '/route.json', encoding='utf-8'))
for f, lay in ((221, 1), (222, 2)):
    big = Image.open('%s/img/bfd_L%d.jpg' % (ROOT, lay)).convert('RGBA').resize((W*2, H*2), Image.LANCZOS)
    ov = Image.new('RGBA', big.size, (0,0,0,0))
    d = ImageDraw.Draw(ov)
    for kind, pf, pts in paths:
        if pf != f: continue
        sp = [(x*2/100*W, y*2/100*H) for x, y in pts]
        d.line(sp, fill=(60, 190, 255, 190), width=5)
    for seg in data[str(f)]['segs']:
        sp = [(x*2/100*W, y*2/100*H) for x, y in seg['pts']]
        d.line(sp, fill=(255, 90, 40, 230), width=2)
    for st in data[str(f)]['stops']:
        for x, y in st['pins']:
            cx, cy = x*2/100*W, y*2/100*H
            d.ellipse([cx-8, cy-8, cx+8, cy+8], outline=(255, 240, 0, 255), width=3)
    Image.alpha_composite(big, ov).convert('RGB').save('%s/ab2_L%d.png' % (ROOT, lay))
    print('ok', lay)
