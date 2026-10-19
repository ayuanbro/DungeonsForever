# -*- coding: utf-8 -*-
import re, sys, glob, os
sys.stdout.reconfigure(encoding='utf-8')
allm = {}
for f in sorted(glob.glob('_temp/_macro_pages/*.html')) + ['_temp/_macro_probe/hub.html']:
    h = open(f, encoding='utf-8', errors='replace').read()
    for u in re.findall(r'href="(https://www\.wowhead\.com/classic/guide[s]?/[^"]*macros[^"]*)"', h):
        allm[u] = os.path.basename(f)
    for u in re.findall(r'href="(/classic/guide/classes/[^"]*macros[^"]*)"', h):
        allm['https://www.wowhead.com'+u] = os.path.basename(f)
for u, src in sorted(allm.items()):
    print(u, ' <- ', src)
print('total', len(allm))
