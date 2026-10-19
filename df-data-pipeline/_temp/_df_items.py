# -*- coding: utf-8 -*-
import re

src = open("Core/Data/Data_DungeonLoot.lua", encoding="utf-8").read()
SRC = re.compile(r'^\s*\{ "(?:[^"\\]|\\.)*", "(?:[^"\\]|\\.)*", "(?:[^"\\]|\\.)*", "((?:[^"\\]|\\.)*)", \{')
ITEM = re.compile(r'^\s*\{ \d+,')
lines = src.splitlines()
counts, named, i = [], [], 0
while i < len(lines):
    m = SRC.match(lines[i])
    if m:
        j, n = i + 1, 0
        while j < len(lines) and not SRC.match(lines[j]) and not re.match(r'^\s*\},', lines[j]):
            if ITEM.match(lines[j]):
                n += 1
            j += 1
        counts.append(n)
        if m.group(1) != "":
            named.append(n)
        i = j
    else:
        i += 1
counts.sort(reverse=True)
named.sort(reverse=True)
print("全部来源件数 TOP10:", counts[:10])
print("有 npcid 的来源件数 TOP10:", named[:10])
print("有 npcid 来源数:", len(named), " >16 的:", sum(1 for c in named if c > 16))

