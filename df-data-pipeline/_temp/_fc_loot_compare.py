# -*- coding: utf-8 -*-
"""掉落三层对比：fc 新页 vs fc 旧缓存 vs Data_DungeonLoot"""
import re, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fc_compare import (SLUG2DID, norm, unesc, balanced, ours_block, ROOT)  # noqa

lt = open(os.path.join(ROOT, 'Core/Data/Data_DungeonLoot.lua'), encoding='utf-8').read()

def ours_loot(did):
    """boss英文名 -> {itemid: (chance|None, is_quest)}"""
    blk = ours_block(lt, did)
    if not blk:
        return None
    out = {}
    for m in re.finditer(r'\{ "([^"]+)", "[^"]*", "[^"]*", "(\d+)", \{(.*?)\n        \} \}', blk, re.S):
        boss, npc, items = m.group(1), m.group(2), m.group(3)
        rows = {}
        for it in re.finditer(r'\{ (\d+), (nil|[\d.]+), (true|false|nil) \}', items):
            iid = int(it.group(1))
            chance = None if it.group(2) == 'nil' else float(it.group(2))
            quest = it.group(3) == 'true'
            rows[iid] = (chance, quest)
        out[boss] = rows
    return out

def fc_old(slug):
    p = '_fc/cache/fc_site_dg_%s.json' % slug
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding='utf-8'))
    out = {}
    for b in d.get('bosses', []):
        out[b.get('english') or b.get('name', '')] = {it['i'] for it in b.get('items', [])}
    return out

def fc_new(slug):
    h = open('_fc_dg_%s.html' % slug, encoding='utf-8').read()
    out = {}
    for blk in balanced(h, r'\\"bosses\\":\[', ']'):
        fj = unesc(blk)
        # 逐顶层对象平衡切分
        i = 0
        n = len(fj)
        objs = []
        while i < n:
            if fj[i] == '{':
                depth = 0
                j = i
                instr = False
                while j < n:
                    c = fj[j]
                    if c == '"':
                        instr = not instr
                    elif not instr:
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                break
                    j += 1
                objs.append(fj[i:j + 1])
                i = j + 1
            else:
                i += 1
        for obj in objs:
            en_m = re.search(r'"english":"([^"]*)"', obj)
            if not en_m:
                continue
            en = en_m.group(1)
            items = {int(x) for x in re.findall(r'\{"i":(\d+)', obj)}
            out.setdefault(en, set()).update(items)
    return out

def show(t, items):
    if items:
        print('== %s (%d) ==' % (t, len(items)))
        for s, a, b, c in items[:40]:
            print('  %-26s %-30s %s' % (s, a, str(c)[:70]))

report = []
for slug, did in sorted(SLUG2DID.items()):
    o, n = fc_old(slug), fc_new(slug)
    mine = ours_loot(did)
    if mine is None:
        report.append((slug, 'NO-OUR-LOOT', '-', '-'))
        continue
    my_norm = {norm(k): k for k in mine}
    # 1) fc 新旧差异（站方改过掉落？）
    for en in n:
        key = None
        for k, v in o.items():
            if norm(k) == norm(en):
                key = en
                break
        old_set = o.get(key, set()) if key else set()
        added = n[en] - old_set
        removed = old_set - n[en]
        if added or removed:
            report.append((slug, 'FC-OLD-NEW-DIFF', en,
                           ' +%s -%s' % (sorted(added), sorted(removed))))
    # 2) fc 新 vs 我们
    for en, items in n.items():
        key = my_norm.get(norm(en))
        if key is None:
            continue
        my_items = set(mine[key].keys())
        miss = items - my_items
        if miss:
            report.append((slug, 'FC-ITEM-WE-LACK', key, sorted(miss)))
        extra = my_items - items
        if extra:
            report.append((slug, 'OUR-ITEM-NOT-ON-FC', key, sorted(extra)))

json.dump(report, open('_fc_loot_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
show('FC-OLD-NEW-DIFF (站方改过掉落)', [r for r in report if r[1] == 'FC-OLD-NEW-DIFF'])
show('FC-ITEM-WE-LACK', [r for r in report if r[1] == 'FC-ITEM-WE-LACK'])
show('OUR-ITEM-NOT-ON-FC', [r for r in report if r[1] == 'OUR-ITEM-NOT-ON-FC'])
print('total', len(report))
