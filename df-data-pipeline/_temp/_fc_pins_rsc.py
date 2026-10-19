# -*- coding: utf-8 -*-
"""从 fc 副本页 RSC payload 里抽全量地图钉点（含 object / quest / entrance）。"""
import re, os, json

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_ref')
slugs = [s.strip() for s in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_fc_slugs.txt')).read().split() if s.strip()]

PIN_RE = re.compile(
    r'\{\\"x\\":([\d.]+),\\"y\\":([\d.]+),\\"boss\\":\\"([\w-]+)\\",\\"face\\":(\d+),\\"faceKind\\":\\"(\w+)\\",\\"label\\":\\"((?:[^"\\\\]|\\\\.)*)\\"')
FLOOR_RE = re.compile(r'"floors?":\s*(\[\{.*?\}\]|\d+)', re.S)

result = {}
kinds_used = {}
for slug in slugs:
    p = os.path.join(REF, 'dg_%s.html' % slug)
    if not os.path.exists(p):
        continue
    d = open(p, encoding='utf-8', errors='replace').read()
    pins = []
    for m in PIN_RE.finditer(d):
        x, y, boss, face, kind, label = m.groups()
        pins.append({'x': float(x), 'y': float(y), 'boss': boss,
                     'face': int(face), 'kind': kind,
                     'label': label.encode().decode('unicode_escape', errors='replace')})
        kinds_used[kind] = kinds_used.get(kind, 0) + 1
    # 静态 HTML 里的 entrance/quest 钉（另一套标记）
    ent, qst = [], []
    for m in re.finditer(r'<(a|span|button)([^>]*class="dgx-pin"[^>]*)>(.*?)</\1>', d, re.S):
        attrs, body = m.group(2), m.group(3)
        kind = re.search(r'data-kind="(\w+)"', attrs)
        kind = kind.group(1) if kind else 'boss'
        if kind not in ('entrance', 'quest'):
            continue
        st = re.search(r'left:\s*([\d.]+)%;\s*top:\s*([\d.]+)%', attrs)
        nm = re.search(r'<span class="dgx-pin-name">(.*?)</span>', body, re.S)
        nm = re.sub(r'<[^>]+>', '', nm.group(1)).strip() if nm else ''
        qid = re.search(r'href="#quest-(\d+)"', attrs)
        rec = {'x': float(st.group(1)), 'y': float(st.group(2)), 'label': nm}
        if qid:
            rec['quest'] = int(qid.group(1))
        (ent if kind == 'entrance' else qst).append(rec)
    result[slug] = {'rsc_pins': pins, 'entrance': ent, 'quest': qst}

json.dump(result, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          '_fc_pins_full.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('faceKind 用量:', kinds_used)
print()
for slug, r in result.items():
    by = {}
    for p in r['rsc_pins']:
        by.setdefault(p['kind'], 0)
        by[p['kind']] += 1
    ent_q = ('入口 %d / 任务钉 %d' % (len(r['entrance']), len(r['quest']))) if (r['entrance'] or r['quest']) else ''
    if r['rsc_pins'] or ent_q:
        extra = '  ' + ent_q if ent_q else ''
        obj_names = [p['label'] for p in r['rsc_pins'] if p['kind'] != 'boss']
        print('%-26s RSC钉 %d %s%s%s' % (slug, len(r['rsc_pins']),
              ('%s' % by if by else ''), extra,
              ('  非boss: ' + '; '.join('%s@(%s,%s)' % (o['label'][:28], o['x'], o['y']) for o in []) if False else '')))
        for p in r['rsc_pins']:
            if p['kind'] != 'boss':
                print('      [%s] (%s,%s) %s' % (p['kind'], p['x'], p['y'], p['label'][:56]))
        for q in r['quest']:
            print('      [quest] (%s,%s) id=%s %s' % (q['x'], q['y'], q.get('quest'), q['label'][:56]))
        for e in r['entrance']:
            print('      [entrance] (%s,%s)' % (e['x'], e['y']))
