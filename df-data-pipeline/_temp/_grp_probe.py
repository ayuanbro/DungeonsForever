# -*- coding: utf-8 -*-
import prof_probe as P
lua = P.load()
R = lua.eval('TF_NS.ProfRecipes')
bad = []
def w(t, fs=12):
    n = 0
    for ch in t:
        n += fs if ord(ch) > 127 else fs * 0.55
    return n
mx = []
for slug, d in R.items():
    gs = d['groups']
    if gs is None: continue
    for i in range(1, len(gs) + 1):
        g = gs[i]
        label = '%s %s' % (g[2], g[4])
        mx.append((w(label), slug, label))
mx.sort(reverse=True)
for x in mx[:12]:
    print('%6.1f  %-14s %s' % x)
print('---- 最长标签宽度（fs=12, 需 +18 内边距）:', mx[0][0] if mx else 0)
