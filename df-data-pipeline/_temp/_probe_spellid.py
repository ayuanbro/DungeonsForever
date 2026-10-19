# -*- coding: utf-8 -*-
"""探测上游页面是否藏有 spell id（临时脚本）。"""
import re

h = open('_temp/_ref/dg_ragefire-chasm.html', encoding='utf-8', errors='replace').read()
for pat in ['data-spell', r'spell=\d+', r'/spell/\d+', 'spell:', 'spell_id',
            'spellId', 'db.spell', 'wowhead.com/spell']:
    print('%-20s %d' % (pat, len(re.findall(pat, h))))

m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
print('NEXT_DATA:', bool(m))
if m:
    j = m.group(1)
    print('spell in json:', j.count('spell'), ' ability in json:', j.count('abilit'))
    for kw in ['abilities', '"spells"', 'spellIds']:
        i = j.find(kw)
        if i > 0:
            print('---', kw, '---')
            print(j[max(0, i - 150):i + 700])
