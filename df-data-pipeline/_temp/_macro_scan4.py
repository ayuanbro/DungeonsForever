# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
h = open('_temp/_macro_probe/rogue_dps.html', encoding='utf-8', errors='replace').read()
# find nav data mentioning macros
for kw in ['guide-navigation','guideNav','"macros"',"-macros'",'-macros"','data-nav']:
    idxs = [m.start() for m in re.finditer(re.escape(kw), h)][:3]
    print(kw, '->', idxs)
i = h.find('guide-navigation')
if i > 0:
    print(repr(h[i-200:i+2500]))
