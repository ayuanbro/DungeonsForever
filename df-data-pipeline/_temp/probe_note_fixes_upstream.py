# -*- coding: utf-8 -*-
"""干跑：把下游生成器的 NOTE_FIXES（注释措辞中性化）逐条套到上游 UI.lua 上，
   报告命中 / 未命中 / 命中位置（是否跨出副本段 4585-7612）。只读，不写盘。

用法：python _temp/probe_note_fixes_upstream.py
"""
import ast
import io
import os
import sys

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TG = os.path.join(os.path.dirname(DF), 'TalentsForever')
GEN = os.path.join(DF, '_temp', 'port_dungeonsforever.py')
UI = os.path.join(TG, 'Core', 'UI.lua')

src = io.open(GEN, encoding='utf-8').read()
tree = ast.parse(src)
fixes = None
leak = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            name = getattr(t, 'id', None)
            if name == 'NOTE_FIXES':
                fixes = ast.literal_eval(node.value)
            elif name == '_LEAK':
                leak = ast.literal_eval(node.value)
if fixes is None:
    sys.exit('未找到 NOTE_FIXES')

raw = open(UI, 'rb').read()
crlf = raw.count(b'\r\n')
text = raw.decode('utf-8')
lines = text.split('\r\n')
print('上游 UI.lua：%d 行（CRLF %d / LF %d）' % (len(lines), crlf, raw.count(b'\n')))

MOD_A, MOD_B = 4585, 7612          # SEG_MODULE 副本段

print('\n=== NOTE_FIXES 逐条（%d 条）===' % len(fixes))
hit = miss = 0
cross = []
for i, (old, new) in enumerate(fixes, 1):
    c = text.count(old)
    pos = [n for n, l in enumerate(lines, 1) if old in l]
    if c == 0:
        miss += 1
        print('  %2d MISS  %s' % (i, old.replace('\r', '')[:96]))
        continue
    hit += 1
    outside = [p for p in pos if not (MOD_A <= p <= MOD_B)]
    flag = '  ← 跨出副本段 %s' % outside if outside else ''
    print('  %2d x%d  行 %s  %s%s' % (i, c, pos, old.replace('\r', '')[:64], flag))
    if outside:
        cross.append((i, old, outside))

print('\n命中 %d 条 / 未命中 %d 条' % (hit, miss))

print('\n=== 兜底闸关键词在【整个 UI.lua】的分布 ===')
for kw in (leak or []):
    pos = [n for n, l in enumerate(lines, 1) if kw in l]
    if not pos:
        continue
    outside = [p for p in pos if not (MOD_A <= p <= MOD_B)]
    print('  %-14s 共 %2d 行；副本段外 %d %s' % (kw, len(pos), len(outside), outside[:12]))

print('\n=== 副本段外的「站点」原文抽样（前 8 条）===')
n = 0
for i, l in enumerate(lines, 1):
    if '站点' in l and not (MOD_A <= i <= MOD_B):
        print('  %5d  %s' % (i, l.strip()[:110]))
        n += 1
        if n >= 8:
            break
if n == 0:
    print('  （无）')

print('\n=== 跨段条目明细 ===')
if not cross:
    print('  （无：全部只落在副本段内）')
for i, old, pos in cross:
    print('  条目 %d 命中行 %s' % (i, pos))
    print('    %s' % old.replace('\r', '')[:110])
    for p in pos:
        print('      %5d  %s' % (p, lines[p - 1].strip()[:100]))
