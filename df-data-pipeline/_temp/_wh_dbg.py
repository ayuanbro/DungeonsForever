# -*- coding: utf-8 -*-
import json, re, os
OV = json.load(open('_ov_parsed.json', encoding='utf-8'))
lt = open(r'D:\workspace\DungeonsForever\Core\Data\Data_DungeonLoot.lua', encoding='utf-8').read()

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def ours_block(src, did):
    i = src.find('    ["%s"] = {' % did)
    if i < 0:
        return None
    j = src.find('{', i)
    depth = 0
    k = j
    while k < len(src):
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                break
        k += 1
    return src[j:k + 1]

def ours_loot_bosses(did):
    blk = ours_block(lt, did)
    if not blk:
        return None
    return [m.group(1) for m in re.finditer(r'\{ "([^"]+)", "[^"]*", "', blk)]

for did in ['excavation_wetlands', 'blackfathom_deeps', 'the_deadmines', 'sm_armory']:
    print('##', did)
    wh = [b['name'] for b in OV[did]['bosses']]
    my = ours_loot_bosses(did)
    print('  WH repr:', [repr(n) for n in wh[:5]])
    print('  MY repr:', [repr(n) for n in my[:5]])
    print('  WH norm:', [norm(n) for n in wh[:5]])
    print('  MY norm:', [norm(n) for n in my[:5]])
