# -*- coding: utf-8 -*-
"""审 HEAD 的 enchanting 段结构"""
import re
d = open('_temp/_head_recipes.lua', encoding='utf-8').read()
i = d.find('["enchanting"] = {')
seg = d[i:d.find('\n    },', i)]
print('段字节数:', len(seg))
for k in ('enchants = {', 'favor = {', 'crafted = {', 'id='):
    print(k, seg.count(k))
row = re.search(r'\{ "Enchant Bracer[^\n]*', seg).group(0)
depth = 0; n = 0; instr = False; esc = False
for ch in row:
    if esc:
        esc = False
        continue
    if ch == chr(92):
        esc = True
        continue
    if ch == '"':
        instr = not instr
        continue
    if instr:
        continue
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            n += 1
print('首行顶层字段数:', n)
# drops 条目带 id 的比例
dr = re.findall(r'\{ npc="([^"]+)", zone="[^"]*", chance=[0-9.]+, lv=\{[^}]*\}(, id=(\d+))?', seg)
print('drops 总数:', len(dr), ' 有 id:', sum(1 for t in dr if t[2]))
