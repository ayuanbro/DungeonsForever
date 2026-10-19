# -*- coding: utf-8 -*-
"""拉全 uiMap db2：uiMapID → DirectoryName + ParentUiMapID（副本画布 ↔ uiMapID 映射真源）。"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PIN = 'PIN-b3939f70f141fd3b2b7e18591b5e1bb751c280b323ba680dd2bb5f763360a1ff'
INST = 'D:/Game/World of Warcraft/_classic_beta_'
CLI = r'C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-6\node_modules\lycheedev\bin\lycheedev.mjs'
NODE = r'C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-6\node.exe'
ENV = dict(os.environ)
ENV['HTTPS_PROXY'] = 'http://127.0.0.1:7897'
ENV['HTTP_PROXY'] = 'http://127.0.0.1:7897'

rows = {}
after = None
for _ in range(60):
    cmd = [NODE, CLI, 'data', 'db2', '--table', 'uiMap', '--snapshot', PIN,
           '--installation', INST, '--limit', '500', '--format', 'json']
    if after is not None:
        cmd += ['--after-id', str(after)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=ENV)
    try:
        d = json.loads(r.stdout)
    except Exception:
        print('parse fail:', r.stdout[:300], r.stderr[:200])
        break
    res = d.get('result') or {}
    data = res.get('rows') or res.get('data') or res
    if isinstance(data, dict):
        data = data.get('rows') or []
    if not isinstance(data, list) or not data:
        print('no rows, keys:', list((d.get('result') or {}).keys()))
        print(str(d)[:800])
        break
    for row in data:
        rid = row.get('_id') or row.get('id') or row.get('ID')
        rows[rid] = row
    ids = [row.get('_id') or row.get('id') for row in data]
    after = max(i for i in ids if i is not None)
    print('page ok, rows:', len(data), 'total:', len(rows))
    if len(data) < 500:
        break

out = {}
for rid, row in rows.items():
    out[rid] = {
        'dir': row.get('DirectoryName') or row.get('dirname'),
        'parent': row.get('ParentUiMapID') or row.get('parentUiMapID'),
        'name': row.get('MapName_lang') or row.get('mapName_lang'),
    }
with open(os.path.join(HERE, '_uimap_all.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)
print('saved', len(out), 'uiMap rows')
