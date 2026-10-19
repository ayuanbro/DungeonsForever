# -*- coding: utf-8 -*-
import re

src = open("Core/Data/Data_DungeonLoot.lua", encoding="utf-8").read()
B = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
S = re.compile(r'^\s*\{ "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)",')
cur = None
d = {}
for L in src.splitlines():
    m = B.match(L)
    if m:
        cur = m.group(1); d[cur] = []; continue
    if cur:
        m2 = S.match(L)
        if m2:
            d[cur].append((m2.group(1), m2.group(2), m2.group(3), m2.group(4)))
print("副本数", len(d))
lst = []
for k, v in d.items():
    named = [x for x in v if x[3] != ""]
    lst.append((len(named), len(v), k))
lst.sort(reverse=True)
for n, t, k in lst[:14]:
    print("  %-24s 有npc=%d 总来源=%d" % (k, n, t))
print()
print("有npc 数量分布:", sorted([n for n, _, _ in lst]))
lens = [len(zh) for v in d.values() for en, zh, note, npc in v if npc]
print("名字最长(zh):", max(lens), "平均", round(sum(lens) / len(lens), 1))
