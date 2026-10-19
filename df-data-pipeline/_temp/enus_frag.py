# -*- coding: utf-8 -*-
"""enUS 产物字符串里残余 CJK 片段统计（找半翻模式）。"""
import glob, io, re, sys
sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter

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

frag = Counter()
whole = Counter()
for p in sorted(glob.glob('Core/Data/enUS/*.lua')):
    for ln in io.open(p, encoding='utf-8'):
        code = re.sub(r'--.*$', '', ln.rstrip('\n'))
        for lit in literals(code):
            if not re.search(r'[\u4e00-\u9fff]', lit):
                continue
            whole[lit] += 1
            for m in re.findall(r'[\u4e00-\u9fff][\u4e00-\u9fff·]+', lit):
                frag[m] += 1
print('含 CJK 字符串总数:', sum(whole.values()), ' distinct:', len(whole))
print('\n== 整串样例 ==')
for s, c in whole.most_common(25):
    print('%3d %s' % (c, s[:90]))
print('\n== 中文片段 ==')
for s, c in frag.most_common(40):
    print('%3d %s' % (c, s))
