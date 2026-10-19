# -*- coding: utf-8 -*-
import re, json
targets = {252798, 253906, 273840, 274158, 274160}
pat = re.compile(r'\{\\"i\\":(\d+),\\"n\\":\\"([^\\]+)\\",\\"q\\":(\d+)')
for slug in ['blackfathom-deeps', 'the-deadmines', 'razorfen-kraul']:
    h = open('_fc_dg_%s.html' % slug, encoding='utf-8').read()
    for m in pat.finditer(h):
        iid = int(m.group(1))
        if iid in targets:
            print(slug, iid, m.group(2), 'q%s' % m.group(3))
    try:
        d = json.load(open('_fc/cache/fc_site_dg_%s.json' % slug, encoding='utf-8'))
        for b in d.get('bosses', []):
            for it in b.get('items', []):
                if it.get('i') in targets:
                    print(slug, '(old)', it['i'], it['n'])
    except Exception as e:
        print(slug, 'old fail', e)
