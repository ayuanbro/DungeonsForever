# -*- coding: utf-8 -*-
import re, io, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = io.open(os.path.join(HERE, '..', 'Core', 'Data', 'Data_DungeonQuests.lua'), encoding='utf-8').read()

def split_fields(row):
    fields, buf, depth, in_str, i, n = [], [], 0, False, 0, len(row)
    while i < n:
        c = row[i]
        if in_str:
            buf.append(c)
            if c == '\\':
                buf.append(row[i+1] if i+1 < n else '')
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            buf.append(c)
        elif c == '{':
            depth += 1
            buf.append(c)
        elif c == '}':
            depth -= 1
            buf.append(c)
        elif c == ',' and depth == 0:
            fields.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        fields.append(''.join(buf).strip())
    return fields

rows = list(re.finditer(r'\{ (\d{3,6}), .{0,8000}?\},\r?\n', src))
print('matches:', len(rows))
cnt = 0
title_by_qid = {}
for m in rows:
    row = m.group(0)
    fields = split_fields(row)
    if cnt < 2:
        print('nf=%d f0=%r f4=%r f6=%r' % (len(fields), fields[0][:20], fields[4][:20] if len(fields) > 4 else '', fields[6][:20] if len(fields) > 6 else ''))
    if len(fields) > 6 and fields[6].startswith('"'):
        title_by_qid[int(fields[0])] = fields[6].strip('"')
    cnt += 1
print('rows walked:', cnt, 'titles:', len(title_by_qid))
for k in list(title_by_qid)[:6]:
    print(' ', k, title_by_qid[k])
