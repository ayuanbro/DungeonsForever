# -*- coding: utf-8 -*-
"""临时：抓 fc 地下城页的 JS chunks，找 the-stockade 掉落数据所在 chunk。"""
import re
import subprocess
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_fc', 'cache')
html = open(os.path.join(CACHE, 'dungeons_root.html'), encoding='utf-8', errors='replace').read()

paths = sorted(set(re.findall(r'_next/static/chunks/[^"\')\s\\]+?\.js', html)))
print('chunks:', len(paths))
os.makedirs(os.path.join(CACHE, 'chunks'), exist_ok=True)
for p in paths:
    name = p.split('/')[-1]
    dst = os.path.join(CACHE, 'chunks', name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        continue
    url = 'https://foreverchanges.pro/' + p
    r = subprocess.run(['curl', '-s', '-m', '60', '-o', dst, '-w', '%{http_code}', url],
                       capture_output=True, text=True)
    print(name, r.stdout)

for p in paths:
    name = p.split('/')[-1]
    dst = os.path.join(CACHE, 'chunks', name)
    try:
        t = open(dst, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    hits = []
    for kw in ('Deepfury', 'the-stockade', 'Bruegal'):
        if kw in t:
            hits.append(kw)
    if hits:
        print('HIT', name, hits, os.path.getsize(dst))
