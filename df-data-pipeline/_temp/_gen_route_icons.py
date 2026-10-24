# -*- coding: utf-8 -*-
import os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(ROOT, '..', 'Media')
OUT = os.path.join(ROOT, '_route_plan', 'img', '_icons')
os.makedirs(OUT, exist_ok=True)


def tint(im, rgb):
    r, g, b, a = im.split()
    lut = lambda k: [min(255, int(i * k)) for i in range(256)]
    r = r.point(lut(rgb[0]))
    g = g.point(lut(rgb[1]))
    b = b.point(lut(rgb[2]))
    return Image.merge('RGBA', (r, g, b, a))


def load(name):
    return Image.open(os.path.join(MEDIA, name + '.tga')).convert('RGBA')


jobs = []

jobs.append(('entrance', load('EntryPin'), None, 0))
jobs.append(('boss', load('BossSkull'), None, 0))
jobs.append(('q_ready', load('QuestPinReady'), None, 0))
jobs.append(('q_pre', load('QuestPinPre'), None, 0))
jobs.append(('q_lock', load('QuestPinLocked'), None, 0))
jobs.append(('qmark_excl', load('QMarkExcl'), None, 0))
jobs.append(('qmark_ask', load('QMarkAsk'), None, 0))

arrow = load('PvPRankArrow')
jobs.append(('arrow_down', arrow, (1.00, 0.80, 0.34), -90))
jobs.append(('arrow_up', arrow, (0.58, 0.82, 1.00), 90))

for name, im, rgb, rot in jobs:
    o = im
    if rot:
        o = o.rotate(rot, expand=True, resample=Image.BICUBIC)
    if rgb:
        o = tint(o, rgb)
    o.save(os.path.join(OUT, name + '.png'))
    print('%-11s %s' % (name, o.size))
print('->', os.path.normpath(OUT))
