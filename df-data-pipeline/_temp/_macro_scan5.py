# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
h = open('_temp/_macro_probe/rogue_dps.html', encoding='utf-8', errors='replace').read()
import json
for p in (37554, 113463):
    print('==== at', p)
    print(repr(h[p-600:p+900]))
