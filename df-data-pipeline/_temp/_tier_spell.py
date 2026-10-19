# -*- coding: utf-8 -*-
"""提取三页 HTML 里 WH.Gatherer.addData(6, ...) 的法术条目（id → 中文名）。"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '_tier_probe')
STR = '("(?:[^"\\\\]|\\\\.)*")'


def braces_json(h, start):
    """从 h[start] == '{' 起用花括号计数取出一段平衡的 JSON 文本。"""
    i = h.index('{', start)
    depth = 0
    in_str = False
    esc = False
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


def spells(path):
    h = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'WH\.Gatherer\.addData\(6,', h):
        raw = braces_json(h, m.end())
        try:
            out.update(json.loads(raw))
        except Exception as e:
            print('   skip:', e)
    return out


def markup(path):
    h = open(path, encoding='utf-8').read()
    m = re.search(r'WH\.markup\.printHtml\(\s*' + STR, h, re.S)
    return json.loads(m.group(1)) if m else ''


for k in ('dps', 'tank', 'healer'):
    sp = spells(os.path.join(D, k + '.html'))
    mk = markup(os.path.join(D, k + '.html'))
    used = [int(x) for x in re.findall(r'\[spell=(\d+)\]', mk)]
    print('###', k, '法术条目 %d / 引用 %d' % (len(sp), len(used)))
    for sid in sorted(set(used)):
        e = sp.get(str(sid)) or {}
        print('   %-8s %-14s %s' % (sid, e.get('name_zhcn', '?'), (e.get('name') or '')[:34]))
    extra = sorted(set(sp) - set(str(x) for x in used))
    if extra:
        print('   未被引用:', ', '.join('%s=%s' % (i, sp[i].get('name_zhcn')) for i in extra[:14]))
