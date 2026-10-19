# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
h = open('_temp/_macro_probe/rogue_dps.html', encoding='utf-8', errors='replace').read()
print('len', len(h), '| #showtooltip count:', h.count('#showtooltip'))
for m in list(re.finditer(r'#showtooltip', h))[:3]:
    s = m.start()
    print('---- ctx ----')
    print(h[max(0,s-800):s+900])
