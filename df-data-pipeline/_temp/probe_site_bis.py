# -*- coding: utf-8 -*-
"""探针：按 sitemap 全量抓取站点 BIS 页，输出完整结构表（路径/标题/解析量）。
用途：确认站点当前分类法与我们 fc_bis.py 假设的差异，为「全部收录」定范围。"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fc_bis as F

HERE = os.path.dirname(os.path.abspath(__file__))
SM = os.path.join(HERE, '_fc_bis', 'sitemap.xml')
OUT30 = os.path.join(HERE, '_fc_bis', 'site30')
OUT20 = os.path.join(HERE, '_fc_bis', 'site20')
os.makedirs(OUT30, exist_ok=True)
os.makedirs(OUT20, exist_ok=True)

sm = open(SM, encoding='utf-8').read()
locs = [m.group(1) for m in re.finditer(r'<loc>([^<]+)</loc>', sm)]

p30, p20 = [], []
for l in locs:
    if '/zh-cn/bis' not in l:
        continue
    tail = l.split('/zh-cn/bis')[-1].strip('/')
    if not tail:
        continue
    if tail.startswith('level-20/'):
        p20.append(tail[len('level-20/'):])
    elif not tail.startswith('level-20'):
        p30.append(tail)

p30 = sorted(set(p30))
p20 = sorted(set(p20))
print('30级路径 %d / 20级路径 %d' % (len(p30), len(p20)))

rows = []
for lv, paths, outdir in ((30, p30, OUT30), (20, p20, OUT20)):
    for pth in paths:
        name = pth.replace('/', '_') + '.html'
        dst = os.path.join(outdir, name)
        url = '%s/zh-cn/bis/%s%s' % (F.BASE, 'level-20/' if lv == 20 else '', pth)
        st = F.fetch(url, dst, force=False, offline=False, allow_net=True)
        if st in ('missing', 'fail', '404'):
            print('  ! %d %-28s %s' % (lv, pth, st))
            continue
        h = open(dst, encoding='utf-8', errors='replace').read()
        tm = re.search(r'<title>(.*?)</title>', h, re.S)
        title = tm.group(1).strip() if tm else ''
        try:
            sp = F.parse_page(h)
            nslot = len(sp['slots'])
            nrow = sum(len(v) for v in sp['rows'].values())
            nench = len(sp.get('enchs') or [])
        except Exception as e:
            nslot = nrow = nench = -1
            title += ' [ERR %s]' % str(e)[:40]
        rows.append({'lv': lv, 'path': pth, 'title': title,
                     'slots': nslot, 'rows': nrow, 'enchs': nench})
        time.sleep(0.8)

with open(os.path.join(HERE, '_fc_bis', 'site_map.json'), 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

print()
print('%-4s %-30s %-6s %-6s %-6s %s' % ('lv', 'path', 'slots', 'rows', 'enchs', 'title'))
for r in rows:
    print('%-4d %-30s %-6d %-6d %-6d %s' % (r['lv'], r['path'], r['slots'], r['rows'],
                                             r['enchs'], r['title'][:52]))
