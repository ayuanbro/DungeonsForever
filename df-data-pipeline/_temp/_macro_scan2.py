# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
h = open('_temp/_macro_probe/rogue_dps.html', encoding='utf-8', errors='replace').read()
links = sorted(set(re.findall(r'href="(/classic/guide/[^"]+)"', h)))
print('all /classic/guide links:', len(links))
for l in links[:80]: print('  ', l)
