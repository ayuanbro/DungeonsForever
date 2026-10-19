# -*- coding: utf-8 -*-
"""全字段英文残留扫描：把每个任务行里所有字符串值（含嵌套表）过一遍，列出含 [A-Za-z]{2,} 的字段。

用于对比「上游（已被一次性清英文 pass 处理）」与「副本手册移植副本（较早拷贝）」的差异。
用法：python _probe_en_scan.py <Data_DungeonQuests.lua 路径>
"""
import os, re, sys
from lupa import lua51

TARGET = sys.argv[1]
print('### 目标：', TARGET)
lua = lua51.LuaRuntime(unpack_returned_tuples=True)
ns = lua.table()
chunk = lua.eval('function(src,name,ns) local f=assert(loadstring(src,name)) return f(name,ns) end')
chunk(open(TARGET, encoding='utf-8').read(), 'DQ', ns)
DQ = ns['DungeonQuests']

# 字段序号 → 中文名（见 Data_DungeonQuests.lua 头注释）
FIELDS = {1: 'questID', 2: '阵营', 3: '可接等级', 4: '任务等级', 5: '起始NPC', 6: '起始地点',
          7: '前置名', 8: '副本内', 9: '前置ID', 10: '奖励物品ID', 11: '任务目标', 12: '任务注释',
          13: '难度档位', 14: '需要提供物品ID', 15: '职业限制', 16: '起始NPCID', 17: '起始NPC名',
          18: '收获'}
EN = re.compile(r'[A-Za-z]{2,}')


def walk(v, path):
    if isinstance(v, str):
        if EN.search(v):
            yield path, v
    elif isinstance(v, (int, float, bool)) or v is None:
        return
    else:                                   # Lua table（数组或字典）
        try:
            for k in v.keys():
                sub = v[k]
                yield from walk(sub, path + '[%s]' % k)
        except Exception:
            return


hits = {}
tot = 0
for did, rows in DQ.items():
    for idx, q in rows.items():
        tot += 1
        for k in range(1, 19):
            v = q[k]
            if v is None:
                continue
            for path, s in walk(v, ''):
                fld = FIELDS.get(k, '?%d' % k)
                hits.setdefault(fld, []).append((str(did), int(q[1]), s))

print('任务行总数 =', tot)
print()
if not hits:
    print('★ 全字段零英文残留')
for fld in sorted(hits, key=lambda x: -len(hits[x])):
    lst = hits[fld]
    print('%-10s %3d 处' % (fld, len(lst)))
    for did, qid, s in lst[:6]:
        print('      %-20s %-8s %s' % (did, qid, s[:90]))
