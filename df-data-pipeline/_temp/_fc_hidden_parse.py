# -*- coding: utf-8 -*-
"""解析 hidden-items 页 RSC payload：Forever 专属 27 套（套装id/名/部件/隐藏态）。

输出 JSON 到 _fc_hidden_sets.json，并打印人读清单核对。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '_fc_hidden_items.html')
OUT = os.path.join(HERE, '_fc_hidden_sets.json')


def rsc_payload(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', html, flags=re.S)
    payload = ''
    for c in chunks:
        try:
            payload += json.loads(c)
        except Exception:
            payload += c
    return payload


def main():
    h = open(SRC, encoding='utf-8', errors='replace').read()
    p = rsc_payload(h)
    start = p.find('"hid-sets"')
    if start < 0:
        print('没找到 hid-sets'); return 1
    seg = p[start:]

    # 每套 = ["$","li","<setid>",{"children":[ [name-span, pieces-span] …
    # 按 li 切（下一个 li 出现处），name 与每件 href/className 逐个抓
    li_iter = list(re.finditer(
        r'\["\$","li","(\d+)",\{"children":\[',
        seg))
    print('li 命中 %d 个' % len(li_iter))
    sets = []
    for i, m in enumerate(li_iter):
        end = li_iter[i + 1].start() if i + 1 < len(li_iter) else len(seg)
        body = seg[m.start():end]
        nm = re.search(r'"hid-set-name","children":"([^"]+)"', body)
        if not nm:
            print('!! li #%d 无名字' % i); continue
        pieces = re.findall(
            r'\["\$","a","(\d+)",\{"href":"/zh-cn/item/\1","className":"(hid-piece[^"]*)"',
            body)
        sets.append({
            'set_id': m.group(1),
            'name': nm.group(1),
            'pieces': [{'id': int(pid), 'hidden': 'hid-piece-hidden' in cls}
                       for pid, cls in pieces],
        })
    print('共解析 %d 套' % len(sets))
    for s in sets:
        ids = ' '.join('%d%s' % (pc['id'], '*' if pc['hidden'] else '')
                       for pc in s['pieces'])
        print('  set=%-5s %-14s %2d 件: %s' % (s['set_id'], s['name'], len(s['pieces']), ids))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(sets, f, ensure_ascii=False, indent=1)
    print('已写 %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
