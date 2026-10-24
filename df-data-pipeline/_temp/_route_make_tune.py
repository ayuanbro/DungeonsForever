# -*- coding: utf-8 -*-
import io
import json
import re
import sys

from _route_paths import TEMP, PLAN, checked
from _route_gen import replay_amplitudes

sys.path.insert(0, TEMP)
import _route_faction as FAC

ROOT = PLAN
IDX = checked(ROOT + '/data/index.json')
OVRF = checked(TEMP + '/_route_override.json')
QTIPF = checked(TEMP + '/_route_qtip_override.json')
QHIDEF = checked(TEMP + '/_route_qi_hide.json')

data = json.load(io.open(IDX, encoding='utf-8'))

try:
    raw = json.load(io.open(OVRF, encoding='utf-8'))
except Exception as e:
    print('override 读取失败:', e)
    raw = {}

try:
    qtips = json.load(io.open(QTIPF, encoding='utf-8'))
    if not isinstance(qtips, dict):
        qtips = {}
except Exception:
    qtips = {}


def r2(p):
    return [round(float(p[0]), 2), round(float(p[1]), 2)]


def norm_floor(fl, did=None):
    fl = fl or {}
    out = {}
    segs = {}
    rawsegs = fl.get('segs')
    if isinstance(rawsegs, dict):
        for n, s in rawsegs.items():
            v = s or {}
            if isinstance(v, list):
                v = {'pts': v}
            if v.get('del'):
                segs[str(n)] = {'del': 1}
                continue
            pts = v.get('pts') or []
            if len(pts) >= 2:
                o = {'pts': [r2(q) for q in pts]}
                if v.get('from'):
                    o['from'] = str(v['from'])
                if v.get('to'):
                    o['to'] = str(v['to'])
                segs[str(n)] = o
    elif any(isinstance(v, list) for v in fl.values()):
        for n, pts in fl.items():
            if isinstance(pts, list) and len(pts) >= 2 and isinstance(pts[0], list):
                segs[str(n)] = [r2(q) for q in pts]
    if segs:
        out['segs'] = segs
    amp = {}
    for n, v in (fl.get('amp') or {}).items():
        try:
            amp[str(n)] = round(float(v), 1)
        except Exception:
            pass
    if amp:
        out['amp'] = amp
    marks = []
    for m in (fl.get('marks') or []):
        try:
            o = {'k': m.get('k'), 'x': round(float(m['x']), 2), 'y': round(float(m['y']), 2)}
            if m.get('hide'):
                o['hide'] = 1
            if m.get('tip'):
                o['tip'] = str(m.get('tip'))
            marks.append(o)
        except Exception:
            pass
    if marks:
        out['marks'] = marks
    pins = []
    for p in (fl.get('pins') or []):
        try:
            o = {'en': p.get('en') or '', 'x': round(float(p['x']), 2), 'y': round(float(p['y']), 2)}
            if p.get('hide'):
                o['hide'] = 1
            pins.append(o)
        except Exception:
            pass
    if pins:
        out['pins'] = pins
    notes = []
    for n in (fl.get('notes') or []):
        try:
            o = {'x': round(float(n['x']), 2), 'y': round(float(n['y']), 2),
                 'text': n.get('text') or ''}
            if n.get('hide'):
                o['hide'] = 1
            sd = n.get('side')
            if sd in ('A', 'H'):
                o['side'] = sd
            elif not sd and did:
                sd = FAC.note_side(did, o['text'], n.get('raw') or '')
                if sd:
                    o['side'] = sd
            notes.append(o)
        except Exception:
            pass
    if notes:
        out['notes'] = notes
    return out


ov = {}
for row in data.get('dungeons') or []:
    k = row.get('fdr')
    if not k or k not in raw:
        continue
    floors = {}
    for ui, fl in (raw[k] or {}).items():
        nf = norm_floor(fl, row['id'])
        if nf:
            floors[str(ui)] = nf
    if floors:
        ov[row['id']] = floors

for row in data.get('dungeons') or []:
    did = row.get('id')
    for fl in row.get('floors') or []:
        floor_key = str(fl['ui']) if fl.get('ui') else 'L%d' % fl['n']
        fl['segs'] = replay_amplitudes(fl, (raw.get(row.get('fdr') or did) or {}).get(floor_key) or {})
        for n in fl.get('notes') or []:
            if not n.get('side'):
                sd = FAC.note_side(did, n.get('text'), n.get('raw') or '')
                if sd:
                    n['side'] = sd

js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
js2 = json.dumps(ov, ensure_ascii=False, separators=(',', ':'))

qd = {}
import os
QDIR = checked(ROOT + '/data/qicons')
if os.path.isdir(QDIR):
    for fn in os.listdir(QDIR):
        if fn.endswith('.json'):
            did = fn[:-5]
            icons = json.load(io.open(checked(QDIR + '/' + fn), encoding='utf-8')).get('icons') or []
            for e in icons:
                sd = FAC.quest_side(did, e.get('qid'))
                if sd:
                    e['side'] = sd
            qd[did] = icons
js3 = json.dumps(qd, ensure_ascii=False, separators=(',', ':'))
js4 = json.dumps(qtips, ensure_ascii=False, separators=(',', ':'))
try:
    qhide = json.load(io.open(QHIDEF, encoding='utf-8'))
    if not isinstance(qhide, dict):
        qhide = {}
except Exception:
    qhide = {}
js5 = json.dumps(qhide, ensure_ascii=False, separators=(',', ':'))

p = checked(ROOT + '/tune.html')
html = io.open(p, encoding='utf-8').read()
n0 = html.count('<script')
html2 = re.sub(r'^const DATA = .*$', lambda m: 'const DATA = ' + js + ';', html, count=1, flags=re.M)
html2 = re.sub(r'^const OVR = .*$', lambda m: 'const OVR = ' + js2 + ';', html2, count=1, flags=re.M)
html2 = re.sub(r'^const QDATA = .*$', lambda m: 'const QDATA = ' + js3 + ';', html2, count=1, flags=re.M)
html2 = re.sub(r'^const QTIP = .*$', lambda m: 'const QTIP = ' + js4 + ';', html2, count=1, flags=re.M)
html2 = re.sub(r'^const QHIDE = .*$', lambda m: 'const QHIDE = ' + js5 + ';', html2, count=1, flags=re.M)
n1 = html2.count('<script')
if n0 != n1 or 'const DATA = ' + js[:24] not in html2:
    raise SystemExit('inject failed: script tags %d -> %d' % (n0, n1))
if 'const OVR = ' + js2[:12] not in html2:
    raise SystemExit('inject OVR failed')
if 'const QDATA = ' + js3[:12] not in html2:
    raise SystemExit('inject QDATA failed')
if 'const QTIP = ' + js4[:12] not in html2:
    raise SystemExit('inject QTIP failed')
if 'const QHIDE = ' + js5[:12] not in html2:
    raise SystemExit('inject QHIDE failed')
io.open(p, 'w', encoding='utf-8', newline='\n').write(html2)
print('injected %.1f KB data, %.1f KB ovr (%d 副本有接管), %.1f KB qicons (%d 副本), '
      '%d 条提示文字, %d 个隐藏任务图标, script tags %d' % (
          len(js) / 1024.0, len(js2) / 1024.0, len(ov), len(js3) / 1024.0, len(qd),
          len(qtips), sum(len(v or {}) for v in qhide.values()), n1))
