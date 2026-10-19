# -*- coding: utf-8 -*-
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_enus_data as G
SRC_DIR = os.path.join(os.path.dirname(HERE), 'Core', 'Data')

def literals(src):
    out, i, n = [], 0, len(src)
    while i < n:
        if src[i] in '"\'':
            q = src[i]; j = i + 1; buf = []
            while j < n:
                if src[j] == '\\':
                    buf.append(src[j:j+2]); j += 2; continue
                if src[j] == q:
                    break
                buf.append(src[j]); j += 1
            out.append(''.join(buf)); i = j + 1; continue
        i += 1
    return out

from collections import Counter
res = Counter()
for fn in sorted(os.listdir(SRC_DIR)):
    if not fn.endswith('.lua'):
        continue
    src = io.open(os.path.join(SRC_DIR, fn), encoding='utf-8').read()
    body, _ = G.transform(src)
    G.CUR_FILE = fn
    for lit in literals(body):
        t = G.translate(lit)
        if t != lit and not re.search(r'[\u4e00-\u9fff]', t):
            continue
        if re.search(r'[\u4e00-\u9fff]', lit) and '\n' not in lit:
            res[lit] += 1
for s, c in res.most_common():
    print(c, repr(s))
