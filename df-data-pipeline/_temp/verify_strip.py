# -*- coding: utf-8 -*-
"""正确性铁证：strip_text(清理前备份) 必须与当前文件**逐字节相同**。
不同 = 清理过程出了错（误删代码 / 事后被别的改动碰到）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BAK = os.path.join(HERE, '_pre_comment_strip')
sys.path.insert(0, HERE)
import strip_comments as S

bad = []
n = 0
for dp, _, fn in os.walk(os.path.join(BAK, 'Core')):
    for f in sorted(fn):
        if not f.endswith('.lua.bak'):
            continue
        bpath = os.path.join(dp, f)
        rel = os.path.relpath(bpath, BAK)[:-4]        # 去掉 .bak
        cur = os.path.join(ROOT, rel)
        n += 1
        old = open(bpath, 'rb').read().decode('utf-8')
        now = open(cur, 'rb').read().decode('utf-8')
        expect, _c, _t = S.strip_text(old)
        if expect != now:
            bad.append(rel)
for dp, _, fn in os.walk(os.path.join(BAK, 'Locales')):
    for f in sorted(fn):
        if not f.endswith('.lua.bak'):
            continue
        bpath = os.path.join(dp, f)
        rel = os.path.relpath(bpath, BAK)[:-4]
        cur = os.path.join(ROOT, rel)
        n += 1
        old = open(bpath, 'rb').read().decode('utf-8')
        now = open(cur, 'rb').read().decode('utf-8')
        expect, _c, _t = S.strip_text(old)
        if expect != now:
            bad.append(rel)

print('核对 %d 个文件：%s' % (n, '全部一致 ✓' if not bad else '不一致 %d 个 ✗' % len(bad)))
for b in bad:
    print('   ✗', b)
    old = open(os.path.join(BAK, b + '.bak'), 'rb').read().decode('utf-8')
    now = open(os.path.join(ROOT, b), 'rb').read().decode('utf-8')
    expect, _c, _t = S.strip_text(old)
    import difflib
    d = list(difflib.unified_diff(expect.split('\n'), now.split('\n'),
                                  'expect', 'now', lineterm='', n=1))
    for l in d[:40]:
        print('     ', l)
