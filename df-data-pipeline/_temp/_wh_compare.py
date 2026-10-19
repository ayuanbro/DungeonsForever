# -*- coding: utf-8 -*-
"""Wowhead 17 本系统对拍：boss 名单 / 技能行 / 钉点 vs 我们数据"""
import re, json, os

ROOT = r'D:\workspace\DungeonsForever'
OV = json.load(open('_ov_parsed.json', encoding='utf-8'))

bs = open(os.path.join(ROOT, 'Core/Data/Data_BossSkills.lua'), encoding='utf-8').read()
lt = open(os.path.join(ROOT, 'Core/Data/Data_DungeonLoot.lua'), encoding='utf-8').read()
bp = open(os.path.join(ROOT, 'Core/Data/Data_BossPos.lua'), encoding='utf-8').read()
gd = open(os.path.join(ROOT, 'Core/Data/Data_DungeonGuide.lua'), encoding='utf-8').read()

def norm(s):
    # 解码 _ov_parsed.json 里残留的字面 \uXXXX 转义
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace('\\u2019', chr(0x2019))
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\s*\((?:Rare|Event)\)\s*', ' ', s)
    s = re.sub(r'^Event://s*', '', s)
    return re.sub(r'[^a-z0-9]', '', s.lower())

def ours_block(src, did):
    for pre in ('    ["%s"] = {' % did, '    %s = {' % did):
        i = src.find(pre)
        if i >= 0:
            break
    else:
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
    out = {}
    for m in re.finditer(r'\{ "([^"]+)", "[^"]*", "[^"]*", "([^"]*)", \{', blk):
        out[m.group(1)] = m.group(2) if not m.group(2).isdigit() else int(m.group(2))
    return out

def ours_skills(did):
    blk = ours_block(bs, did)
    if not blk:
        return None
    out = {}
    for m in re.finditer(r'\["([^"]+)"\] = \{(.*?)\n        \},', blk, re.S):
        out[m.group(1)] = [(int(a), b) for a, b in
                           re.findall(r'\{ "", "", (\d+), "([^"]*)"', m.group(2))]
    return out

def ours_guide_en(did):
    blk = ours_block(gd, did, ) or ours_block(gd, did)
    return blk

NON_BOSS = {'trashmobs', 'ringoflaw', 'tribute', 'cache', 'plans', 'chest'}

def show(t, items):
    if items:
        print('== %s (%d) ==' % (t, len(items)))
        for row in items[:50]:
            print('  ', ' | '.join(str(x)[:60] for x in row))

report = []
for did, rec in sorted(OV.items()):
    wh_bosses = {b['name']: b for b in rec.get('bosses', [])}
    my_loot = ours_loot_bosses(did)
    my_skills = ours_skills(did)
    if my_loot is None:
        report.append((did, 'NO-LOOT', '-', '-'))
        continue
    loot_norm = {norm(k): k for k in my_loot}
    # 1) boss 名单
    for en in wh_bosses:
        if norm(en) not in loot_norm and 'ring of law' not in en.lower():
            report.append((did, 'WH-BOSS-NOT-IN-LOOT', en, wh_bosses[en].get('npc')))
    for mn in my_loot:
        if norm(mn) not in {norm(e) for e in wh_bosses}:
            report.append((did, 'LOOT-BOSS-NOT-ON-WH', mn, my_loot[mn]))
    # 2) 技能行：wowhead spells vs 我们 BossSkills
    if my_skills:
        sk_norm = {norm(k): k for k in my_skills}
        for en, b in wh_bosses.items():
            key = sk_norm.get(norm(en))
            if key is None:
                continue
            wh_ids = set(b.get('spells') or [])
            my_ids = {s for s, _ in my_skills[key]}
            for sid in sorted(wh_ids - my_ids):
                report.append((did, 'WH-SPELL-WE-LACK', key, sid))
            for sid in sorted(my_ids - wh_ids):
                report.append((did, 'OUR-SPELL-NOT-ON-WH', key, sid))

json.dump(report, open('_wh_compare_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
show('WH-BOSS-NOT-IN-LOOT', [r for r in report if r[1] == 'WH-BOSS-NOT-IN-LOOT'])
show('LOOT-BOSS-NOT-ON-WH', [r for r in report if r[1] == 'LOOT-BOSS-NOT-ON-WH'])
show('WH-SPELL-WE-LACK', [r for r in report if r[1] == 'WH-SPELL-WE-LACK'])
print('total', len(report))
