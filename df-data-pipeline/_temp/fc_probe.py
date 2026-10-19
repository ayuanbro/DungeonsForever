# -*- coding: utf-8 -*-
"""字段普查：把 13 个专业页的字段并集、类型、规模列出来，作为归一化 schema 的依据。

用法：python fc_probe.py [--keys] [--sample <slug>]
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_fc', 'cache')


def rsc_payload(html_path):
    h = open(html_path, encoding='utf-8', errors='replace').read()
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', h, flags=re.S)
    parts = []
    for c in chunks:
        try:
            parts.append(json.loads(c))
        except Exception:
            parts.append(c)
    return ''.join(parts)


def rsc_rows(html_path):
    """把页面里所有 RSC 行解成 {行号: 对象}。"""
    p = rsc_payload(html_path)
    rows = {}
    for m in re.finditer(r'(?m)^([0-9a-f]{1,3}):(.*)$', p):
        try:
            rows[m.group(1)] = json.loads(m.group(2))
        except Exception:
            pass
    return rows


def deep_find(node, pred):
    """深度遍历找第一个满足 pred 的节点。

    ★ 不依赖 RSC 行号与树位置：实测主页的业务对象在 $.10[3].children[0][3]，
      子页在另一个行号上，且行号会漂。按「对象里有哪个业务字段」定位最稳。
    """
    if isinstance(node, dict):
        if pred(node):
            return node
        for v in node.values():
            r = deep_find(v, pred)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = deep_find(v, pred)
            if r is not None:
                return r
    return None


def detail(slug):
    """子页详情对象：含 profession + rows/leveling 的那一层。"""
    rows = rsc_rows(os.path.join(CACHE, 'professions_%s.html' % slug))
    return deep_find(
        rows,
        lambda n: isinstance(n.get('profession'), dict)
        and any(k in n for k in ('rows', 'enchants', 'gathering', 'lede', 'counts')))


def index():
    """主页总览对象：含 professions 数组的那一层。"""
    rows = rsc_rows(os.path.join(CACHE, 'professions.html'))
    return deep_find(rows, lambda n: isinstance(n.get('professions'), list)
                     and len(n['professions']) > 5)


def shape(v, depth=0):
    if isinstance(v, dict):
        return 'dict{%s}' % ','.join(sorted(v.keys())[:14])
    if isinstance(v, list):
        if not v:
            return 'list[0]'
        return 'list[%d] of %s' % (len(v), shape(v[0], depth + 1) if depth < 2 else type(v[0]).__name__)
    if isinstance(v, str):
        return 'str(%d) %r' % (len(v), v[:50])
    return type(v).__name__ + ' ' + repr(v)


def walk_types(o, path, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            walk_types(v, path + '.' + k, acc)
    elif isinstance(o, list):
        for v in o[:3]:
            walk_types(v, path + '[]', acc)
    else:
        acc[path].add(type(o).__name__)


if __name__ == '__main__':
    idx = index()
    profs = idx['professions']
    print('=== 主页 professions[%d] 条目字段并集 ===' % len(profs))
    fields = defaultdict(set)
    for p in profs:
        for k, v in p.items():
            fields[k].add(shape(v).split(' ')[0] if not isinstance(v, (list, dict)) else shape(v))
    for k in sorted(fields):
        vals = sorted(fields[k])
        print('  %-18s %s' % (k, ' | '.join(vals[:3])))

    print()
    print('=== 主页顶层 keys ===', sorted(idx.keys()))
    for k, v in idx.items():
        if k in ('professions',):
            continue
        print('  %-12s %s' % (k, shape(v)))

    if '--keys' in sys.argv:
        print()
        print('=== 子页顶层 keys 并集 ===')
        allkeys = defaultdict(list)
        for f in sorted(glob.glob(os.path.join(CACHE, 'professions_*.html'))):
            slug = os.path.basename(f)[len('professions_'):-len('.html')]
            d = detail(slug)
            if d is None:
                print('  %-16s ★ 解析失败' % slug)
                continue
            print('  %-16s %s' % (slug, ', '.join(sorted(d.keys()))))
            for k, v in d.items():
                allkeys[k].append('%s:%s' % (slug, shape(v)))
        print()
        for k in sorted(allkeys):
            print('  %-16s (%d 页) e.g. %s' % (k, len(allkeys[k]), allkeys[k][0][:110]))

    slug = 'alchemy'
    if '--sample' in sys.argv:
        slug = sys.argv[sys.argv.index('--sample') + 1]
    d = detail(slug)
    print()
    print('=== %s 详情：逐字段 ===' % slug)
    for k, v in d.items():
        print('  %-16s %s' % (k, shape(v)[:400]))
    print()
    print('--- %s.rows[0] 全字段 ---' % slug)
    if d.get('rows'):
        print(json.dumps(d['rows'][0], ensure_ascii=False, indent=1))
    print('--- %s.rows 带 source 的一条 ---' % slug)
    for r in d.get('rows') or []:
        if r.get('source'):
            print(json.dumps(r, ensure_ascii=False, indent=1))
            break
    for key in ('enchants', 'crafted', 'favor', 'groups', 'camps', 'vendor', 'gathering',
                'smelting', 'levelSources'):
        v = d.get(key)
        if not v:
            continue
        print('--- %s.%s ---' % (slug, key))
        print(json.dumps(v[0] if isinstance(v, list) else v, ensure_ascii=False, indent=1)[:1500])
    if d.get('leveling'):
        print('--- %s.leveling 结构 ---' % slug)
        lv = d['leveling']
        for k, v in lv.items():
            print('  %-14s %s' % (k, shape(v)[:300]))
        for k in ('steps', 'shopping', 'sold', 'quest'):
            if lv.get(k):
                print('  [%s[0]] %s' % (k, json.dumps(lv[k][0], ensure_ascii=False)[:600]))
    print('--- %s.camp_objects[0] ---' % slug)
    pr = d['profession']
    if pr.get('camp_objects'):
        print(json.dumps(pr['camp_objects'][0], ensure_ascii=False, indent=1))
    print('--- %s.specific_perks[0] / shared_perks[0] ---' % slug)
    for k in ('specific_perks', 'shared_perks'):
        if pr.get(k):
            print(json.dumps(pr[k][0], ensure_ascii=False, indent=1)[:1200])
