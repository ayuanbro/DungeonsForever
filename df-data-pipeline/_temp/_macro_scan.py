# -*- coding: utf-8 -*-
import re, sys, glob, html as H
sys.stdout.reconfigure(encoding='utf-8')
# 1) hub: all class guide links
hub = open('_temp/_macro_probe/hub.html', encoding='utf-8', errors='replace').read()
links = set(re.findall(r'href="(/classic/guide/classes/[a-z\-]+/[a-z0-9\-]+)"', hub))
print('hub class-guide links:', len(links))
for l in sorted(links): print('  ', l)
