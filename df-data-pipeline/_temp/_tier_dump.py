# -*- coding: utf-8 -*-
"""导出三页 tier list 的可读全文（梯队表 + 正文，内联法术/图标已还原），供翻译用。"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '_tier_probe')
STR = '("(?:[^"\\\\]|\\\\.)*")'


def braces_json(h, start):
    i = h.index('{', start)
    depth, in_str, esc = 0, False, False
    for j in range(i, len(h)):
        c = h[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return h[i:j + 1]
    return '{}'


def load(path):
    h = open(path, encoding='utf-8').read()
    sp = {}
    for m in re.finditer(r'WH\.Gatherer\.addData\(6,', h):
        try:
            sp.update(json.loads(braces_json(h, m.end())))
        except Exception:
            pass
    mk = json.loads(re.search(r'WH\.markup\.printHtml\(\s*' + STR, h, re.S).group(1))
    return mk, sp


out = []
for k in ('dps', 'tank', 'healer'):
    mk, sp = load(os.path.join(D, k + '.html'))
    mk = re.sub(r'\[spell=(\d+)\]',
                lambda m: '«%s»' % (sp.get(m.group(1), {}).get('name_zhcn') or m.group(1)), mk)
    mk = re.sub(r'\[spec-badge=([a-z0-9\-]+)\]', lambda m: '<' + m.group(1) + '>', mk)
    mk = re.sub(r'\[url guide=\d+ hash=[a-z0-9\-]+\]\[filter-target="[^"]*"\]', '', mk)
    mk = re.sub(r'\[/?filter-target[^\]]*\]|\[/url\]', '', mk)
    mk = re.sub(r'\[tier-list[^\]]*\]', '\n=== TIER LIST ===\n', mk)
    mk = re.sub(r'\[/tier-list\]', '\n=== END ===\n', mk)
    mk = re.sub(r'\[tier-label bg=(q\d)\]', r'\n[TIER \1] ', mk)
    mk = re.sub(r'\[h([23])[^\]]*\]', r'\n\n## ', mk)
    mk = re.sub(r'\[li\]', '\n- ', mk)
    mk = re.sub(r'\[/?[a-z0-9]+[^\]]*\]', '', mk)
    mk = re.sub(r'[ \t]+', ' ', mk)
    mk = re.sub(r'\n{3,}', '\n\n', mk)
    out.append('\n\n################ %s ################\n' % k.upper() + mk.strip())

open(os.path.join(HERE, '_tier_full.txt'), 'w', encoding='utf-8').write('\n'.join(out))
print('written', os.path.join(HERE, '_tier_full.txt'))
