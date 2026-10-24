# -*- coding: utf-8 -*-
"""enUS 产物内「字符串字面量里的 CJK」精确扫描（注释不计）。"""
import glob, io, re, sys
sys.stdout.reconfigure(encoding="utf-8")

def literals(line):
    out, i, n = [], 0, len(line)
    while i < n:
        if line[i] in '"\'':
            q = line[i]; j = i + 1; buf = []
            while j < n:
                if line[j] == '\\':
                    buf.append(line[j:j+2]); j += 2; continue
                if line[j] == q:
                    break
                buf.append(line[j]); j += 1
            out.append(''.join(buf)); i = j + 1; continue
        i += 1
    return out

total = 0
for p in sorted(glob.glob('Core/Data/enUS/*.lua')):
    hits = []
    for i, ln in enumerate(io.open(p, encoding='utf-8'), 1):
        code = re.sub(r'--.*$', '', ln.rstrip('\n'))
        for lit in literals(code):
            if re.search(r'[\u4e00-\u9fff]', lit):
                hits.append((i, lit[:110]))
    if hits:
        total += len(hits)
        print('%s: %d 条' % (p, len(hits)))
        for i, lit in hits[:6]:
            print('   %5d  %s' % (i, lit))
print('字符串 CJK 总数:', total)
