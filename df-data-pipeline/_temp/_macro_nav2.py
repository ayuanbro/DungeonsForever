# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
for f in ('druid_healer','priest_healer','shaman_healer','warrior_dps'):
    h = open('_temp/_macro_pages/%s.html' % f, encoding='utf-8', errors='replace').read()
    seen = set()
    print('====', f)
    for m in re.finditer(r'<a href="(https://www\.wowhead\.com/classic/guides?/[^"]+)"[^>]*>\s*<span class="text-content" data-text="([^"]*)"', h):
        u, t = m.group(1), m.group(2)
        if u in seen: continue
        seen.add(u)
        if 'macros' in u or t == 'macros':
            print('   ', t, '|', u)
