# -*- coding: utf-8 -*-
"""把 wowhead 中文名直接注入 Data_ProfTrainers.lua 的 zh/tw 字段（zh==en 的回退行）。
不重抓 icy-veins；tw 用生成器同款 s2t。幂等：已注入的行跳过。"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_prof_trainers import s2t  # noqa: E402

LUA = os.path.join(HERE, '..', 'Core', 'Data', 'Data_ProfTrainers.lua')
npcid = json.load(open(os.path.join(HERE, '_trainers_npcid.json'), encoding='utf-8'))
zhdb = json.load(open(os.path.join(HERE, '_trainers_zh.json'), encoding='utf-8'))

id2zh = {}
for en, eid in npcid.items():
    z = zhdb.get(str(eid))
    if z:
        id2zh.setdefault(en, z)


def strip_sfx(en):
    return re.sub(r'\s*\([^)]*\)\s*$', '', en).strip()


zh_of = {}
for en, z in id2zh.items():
    zh_of[en] = z
    zh_of[strip_sfx(en)] = z

src = open(LUA, encoding='utf-8', newline='').read()
dup = re.compile(r'(tw = "[^"]*"), tw = "[^"]*"')
src = dup.sub(r'\1', src)
pat = re.compile(r'en = "([^"]*)", zh = "([^"]*)", tw = "([^"]*)"')
n_fix = 0


def repl(m):
    global n_fix
    en, zh, tw = m.group(1), m.group(2), m.group(3)
    z = zh_of.get(en) or zh_of.get(strip_sfx(en))
    if not z:
        return m.group(0)
    if zh == en or tw == en or tw == s2t(z):
        n_fix += 1
        return 'en = "%s", zh = "%s", tw = "%s"' % (en, z, s2t(z))
    return m.group(0)


out = pat.sub(repl, src)
open(LUA, 'w', encoding='utf-8', newline='').write(out)
print('injected %d names' % n_fix)

left = len([1 for en, zh, tw in pat.findall(out) if en == zh or tw == en])
print('still english: %d (waiting for fetch)' % left)
