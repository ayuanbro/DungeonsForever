# -*- coding: utf-8 -*-
"""从 wowhead forever/cn 任务页 RSC 载荷提取 开始/结束 NPC。"""
import re
import io
import sys

BS = chr(92)
UESC = re.compile(BS + BS + 'u([0-9a-fA-F]{4})')


def deesc(s: str) -> str:
    return UESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def find_all(h: str, needle: str, limit: int = 2, span: int = 340):
    got = []
    pos = 0
    while len(got) < limit:
        i = h.find(needle, pos)
        if i < 0:
            break
        got.append(deesc(h[i:i + span]))
        pos = i + 1
    return got


def main():
    for q in ['92457', '96774', '8181', '8182']:
        path = f'_ref/wh_quest_{q}.html'
        h = io.open(path, encoding='utf-8').read()
        print('=' * 22, q)
        for hexkw, name in [('5f00', 'START'), ('7ed3', 'END')]:
            needle = BS + 'u' + hexkw + BS + 'u'
            hits = find_all(h, needle)
            if not hits:
                print(f'  [{name}] 无')
            for seg in hits:
                seg = seg.replace('/forever/cn/', '>')
                print(f'  [{name}]', seg[:260])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
