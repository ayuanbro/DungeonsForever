# -*- coding: utf-8 -*-
"""扫描 Core/Data/enUS/*.lua 里仍含 CJK 的字符串字面量，按文件去重输出。"""
import re, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"D:/workspace/DungeonsForever/Core/Data/enUS")
CJK = re.compile(r'[\u4e00-\u9fff]')

def literals(src):
    """逐字符扫描，抽出字符串字面量（处理 \\ 转义与 [[..]] 长串）。"""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == '-' and src[i:i+2] == '--':
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '"' or c == "'":
            q = c; j = i + 1; buf = []
            while j < n:
                if src[j] == '\\':
                    buf.append(src[j:j+2]); j += 2; continue
                if src[j] == q:
                    break
                buf.append(src[j]); j += 1
            out.append(''.join(buf)); i = j + 1
            continue
        if src[i:i+2] == '[[':
            j = src.find(']]', i + 2)
            out.append(src[i+2:j if j >= 0 else n]); i = (j + 2) if j >= 0 else n
            continue
        i += 1
    return out

total = 0
for f in sorted(ROOT.glob('Data_*.lua')):
    seen, res = set(), []
    for lit in literals(f.read_text(encoding='utf-8')):
        if CJK.search(lit) and lit not in seen:
            seen.add(lit); res.append(lit)
    if res:
        total += len(res)
        print(f'== {f.name}  ({len(res)}) ==')
        for s in res:
            print(repr(s))
        print()
print('TOTAL', total)
