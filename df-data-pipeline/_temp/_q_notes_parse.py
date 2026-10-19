# -*- coding: utf-8 -*-
"""解析 Data_DungeonQuests.lua：每个副本的任务 ID 列表 + 12 号字段（任务注释）现值。"""
import json
import re

SRC = r'D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua'
txt = open(SRC, encoding='utf-8').read()


def split_fields(body):
    """按顶层逗号切一行任务的 18 个字段（花括号/引号感知）。"""
    fields, depth, cur, i, n = [], 0, '', 0, len(body)
    inq = None
    while i < n:
        c = body[i]
        if inq:
            cur += c
            if c == '\\':
                cur += body[i + 1]
                i += 2
                continue
            if c == inq:
                inq = None
            i += 1
            continue
        if c in '"\'':
            inq = c
            cur += c
        elif c == '{':
            depth += 1
            cur += c
        elif c == '}':
            depth -= 1
            cur += c
        elif c == ',' and depth == 0:
            fields.append(cur.strip())
            cur = ''
        else:
            cur += c
        i += 1
    if cur.strip():
        fields.append(cur.strip())
    return fields


def unquote(s):
    s = s.strip()
    if s == 'nil' or s == '':
        return None
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1].replace('\\"', '"')
    return s


out = {}
cur_dun = None
for line in txt.splitlines():
    m = re.match(r'\s*\[\s*"([a-z0-9_]+)"\s*\]\s*=\s*\{\s*$', line)
    if m:
        cur_dun = m.group(1)
        out[cur_dun] = []
        continue
    m = re.match(r'\s*\{\s*(\d+)\s*,(.*)\}\s*,?\s*$', line)
    if m and cur_dun:
        qid = int(m.group(1))
        flds = split_fields(m.group(2))
        # flds[0] 是字段2（阵营），字段12(注释) = flds[10]
        note = unquote(flds[10]) if len(flds) >= 11 else None
        out[cur_dun].append({'id': qid, 'note': note, 'nf': len(flds) + 1})

json.dump(out, open('_q_notes_map.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
total = sum(len(v) for v in out.values())
bad = [(d, r['id'], r['nf']) for d, v in out.items() for r in v if r['nf'] != 18]
print('dungeons:', len(out), 'quests:', total, 'non-18-field rows:', bad)
