# -*- coding: utf-8 -*-
import re
blk = open(r'D:\workspace\DungeonsForever\Core\Data\Data_BossSkills.lua', encoding='utf-8').read()
i = blk.find('    ragefire_chasm = {')
j = blk.find('{', i)
d = 0
k = j
while k < len(blk):
    if blk[k] == '{':
        d += 1
    elif blk[k] == '}':
        d -= 1
        if d == 0:
            break
    k += 1
blk = blk[j:k + 1]
m = re.search(r'\["Oggleflint"\] = \{(.*?)\},\n', blk, re.S)
print('G1:', repr(m.group(1)))
print('TEST:', re.findall(r'\{ "", "", (\d+), "([^"]*)" \}', m.group(1)))
# 全块逐 boss
for mm in re.finditer(r'\["([^"]+)"\] = \{(.*?)\},\n', blk, re.S):
    rows = re.findall(r'\{ "", "", (\d+), "([^"]*)" \}', mm.group(2))
    print(mm.group(1), '->', rows)
