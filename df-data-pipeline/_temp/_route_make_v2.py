# -*- coding: utf-8 -*-
import io
import json
import re

ROOT = 'D:/workspace/DungeonsForever/_temp/_route_plan'
src = io.open(ROOT + '/route.json', encoding='utf-8').read()
data = json.loads(src)

# 只保留页面需要的字段，压缩体积
out = {}
for f, row in data.items():
    out[f] = {
        'segs': [{'n': s['n'], 'from': s['from'], 'to': s['to'],
                  't0': s['t0'], 't1': s['t1'], 'pts': s['pts']} for s in row['segs']],
        'stops': [{'en': st['en'], 'cn': st['cn'], 'kind': st['kind'],
                   'pins': st['pins'][:1]} for st in row['stops']],
        'notes': [{'x': n['x'], 'y': n['y'], 'text': n['text']} for n in row['notes']],
        'entrance': row.get('entrance'),
        'raw': row.get('raw') or [],
    }

js = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
p = ROOT + '/v2.html'
html = io.open(p, encoding='utf-8').read()
html = re.sub(r'const ROUTE = .*?;\n', 'const ROUTE = ' + js + ';\n', html, count=1, flags=re.S)
io.open(p, 'w', encoding='utf-8', newline='\n').write(html)
print('injected', len(js), 'bytes')
