# -*- coding: utf-8 -*-
"""对 Data_DungeonQuests.lua 全字符串跑一遍 enUS 翻译管线，列出仍保持中文的。"""
import io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_enus_data as G

CJK = re.compile(r'[\u4e00-\u9fff]')

def literals(src):
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

src = io.open(G.SRC_DIR + "/Data_DungeonQuests.lua", encoding="utf-8").read()
body, _ = G.transform(src)
seen, res = set(), []
for lit in literals(body):
    if CJK.search(lit) and lit not in seen:
        seen.add(lit)
        res.append(lit)

sys.stdout.reconfigure(encoding="utf-8")
print(len(res))
for s in res:
    print(repr(s))
