# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
h = open('_temp/_macro_cn/rogue_dps.html' if False else '_temp/_macro_probe2/rogue_dps_cn.html', encoding='utf-8', errors='replace').read()
i = h.find('Auto-Attack Macro')
print(repr(h[max(0,i-700):i+1200]))
print('===== containers')
for kw in ['id="guide-body"','class="guide-body','id="main-contents','text-content','guide-content']:
    print(kw, '->', h.find(kw))
