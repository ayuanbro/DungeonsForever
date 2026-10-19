# -*- coding: utf-8 -*-
"""toc 插入 Data_MapPins 三行（兼容 CRLF/LF）。"""
toc = open('DungeonsForever.toc', 'rb').read().decode('utf-8')
crlf = '\r\n' in toc
eol = '\r\n' if crlf else '\n'
lines = toc.split(eol)
out, done = [], set()
for ln in lines:
    out.append(ln)
    if ln.endswith('Data_BossPos.lua') and 'zhTW' not in ln and 'enUS' not in ln:
        out.append('Core\\Data\\Data_MapPins.lua'); done.add('root')
    if ln.endswith('Data_BossPos.lua') and 'zhTW' in ln:
        out.append('Core\\Data\\zhTW\\Data_MapPins.lua'); done.add('tw')
    if ln.endswith('Data_BossPos.lua') and 'enUS' in ln:
        out.append('Core\\Data\\enUS\\Data_MapPins.lua'); done.add('us')
assert done == {'root', 'tw', 'us'}, done
open('DungeonsForever.toc', 'wb').write(eol.join(out).encode('utf-8'))
print('插入:', done, '| 行尾:', 'CRLF' if crlf else 'LF')
