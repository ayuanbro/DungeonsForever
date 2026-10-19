# -*- coding: utf-8 -*-
"""修 qb_guard 里的脚本包裹写法（避免 shell 转义踩坑）。"""
import io

P = r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py'

with io.open(P, 'r', encoding='utf-8', newline='') as f:
    s = f.read()

start = s.index('    out = lua.eval(')
tail_mark = "end)()')"
stop = s.index(tail_mark, start) + len(tail_mark)
if s[stop] == '\n':
    stop += 1  # 连同行尾一起换掉
old = s[start:stop]

new = '    out = lua.eval("(function()\\n%s\\nend)()" % QB_SCRIPT)\n'
s = s[:start] + new + s[stop:]

with io.open(P, 'w', encoding='utf-8', newline='') as f:
    f.write(s)

b = open(P, 'rb').read()
print('替换前: %r' % old)
print('替换后: %r' % new)
print('CRLF=%d bareLF=%d' % (b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
