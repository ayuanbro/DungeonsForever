# -*- coding: utf-8 -*-
import io, os, re, collections
DF = r'D:\workspace\DungeonsForever'
CJK = re.compile(r'[\u4e00-\u9fff]')
LATIN = re.compile(r"(?<![A-Za-z])([A-Za-z][A-Za-z0-9'\-]{0,})(?![A-Za-z])")
BS = chr(92)

def extract_strings(t):
    out = []; i = 0; n = len(t)
    while i < n:
        c = t[i]
        if c == '"':
            j = i + 1; buf = []
            while j < n:
                ch = t[j]
                if ch == BS:
                    buf.append(t[j:j+2]); j += 2; continue
                if ch == '"':
                    break
                buf.append(ch); j += 1
            out.append(''.join(buf)); i = j + 1
        else:
            i += 1
    return out

for f in ['Core/Data/Data_ClassGuide.lua', 'Core/Data/zhTW/Data_ClassGuide.lua']:
    t = io.open(os.path.join(DF, f), encoding='utf-8', errors='replace').read()
    cnt = collections.Counter(); ex = {}
    for s in extract_strings(t):
        s2 = re.sub(r'\|s\d+\|', ' ', s)
        if not CJK.search(s2):
            continue
        for tk in LATIN.findall(s2):
            if tk.isdigit():
                continue
            cnt[tk] += 1
            ex.setdefault(tk, s2[:110])
    print('=' * 70); print(f, 'unique latin tokens =', len(cnt))
    for tk, c in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print('   %-14s x%-3d  eg: %s' % (tk, c, ex[tk]))
