# -*- coding: utf-8 -*-
"""QA 独立：在最终产物 Lua 上重放「无限+杂词」相邻判据（fc_guide 口径）。"""
import io, os, re
DF = r'D:\workspace\DungeonsForever'
BS = chr(92)
VER_TOK = r'(?:《魔兽世界：无限》|《无限》|无限测试服|无限版本|无限服|无限版)'
WORDY = (r'(?:怀旧服|懷舊服|怀旧|懷舊|资料片|資料片|永驻|永駐|永燃|永夜|永昼'
         r'|永[恒恆](?!之)|永久|经典赛季|經典賽季|永远的魔兽世界|[Ff]orefore)')
RE_ADJ = re.compile(r'(?:' + VER_TOK + r'\s*' + WORDY + r'|' + WORDY + r'\s*' + VER_TOK + r')')
RE_TOK = re.compile(VER_TOK)
RE_WORDY = re.compile(WORDY)

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
    ss = extract_strings(t)
    adj = [s for s in ss if RE_ADJ.search(s)]
    tok = [s for s in ss if RE_TOK.search(s)]
    wordy = [s for s in ss if RE_WORDY.search(s)]
    tok_wordy = [s for s in ss if RE_TOK.search(s) and RE_WORDY.search(s)]
    print('=' * 74)
    print(f)
    print('  含版本 token 的串 =', len(tok))
    print('  含「版本性杂词」的串 =', len(wordy))
    print('  同时含 token+杂词(未必相邻) =', len(tok_wordy))
    for s in tok_wordy:
        print('      [TOK+WORDY] %s' % s[:170])
    print('  ★ 相邻违规(无限+杂词) =', len(adj))
    for s in adj:
        print('      [ADJ] %s' % s[:170])
