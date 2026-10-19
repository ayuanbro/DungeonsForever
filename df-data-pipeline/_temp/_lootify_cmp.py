# -*- coding: utf-8 -*-
"""对比 DungeonsForever 装备库 vs Lootified 数据层（只读探针，不改数据）。
输出：副本/首领覆盖差、逐 boss 物品差、掉率覆盖、世界掉落、副本任务差。
"""
import os, re, sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
LOOT = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/Lootified"

L = lua51.LuaRuntime(unpack_returned_tuples=True)

def load_lua(path, holder):
    src = open(path, 'rb').read().decode('utf-8', 'replace')
    g = L.globals()
    t = L.table()
    g[holder] = t
    body = L.eval("function(src, name) local f, err = loadstring(src, name) if not f then error(err) end return f end")
    f = body(src, os.path.basename(path))
    f("addon", t)

load_lua(os.path.join(DF, 'Core/Data/Data_DungeonLoot.lua'), 'ns')
ns = L.globals().ns
ours = ns.DungeonLoot

load_lua(os.path.join(LOOT, 'Data/Instances.lua'), 'LJ')
LJ = L.globals().LJ
inst = LJ.Data.Instances

# ── 我方：boss(英文名/npc) -> {items, dungeon} ──
our_boss = {}   # lower(en name) -> set(itemIDs)
our_npc = {}    # npc str -> set
our_slug_bosses = {}
for slug in ours.keys():
    lst = ours[slug]
    our_slug_bosses[slug] = []
    for src in lst.values():
        en, zh, _, npcid = src[1], src[2], src[3], src[4]
        items = set()
        for it in src[5].values():
            items.add(int(it[1]))
        k = (en or '').lower()
        our_boss.setdefault(k, set()).update(items)
        our_slug_bosses[slug].append(en)
        if npcid and str(npcid).isdigit():
            our_npc.setdefault(str(npcid), set()).update(items)

# ── 对方 Instances ──
their_boss = {}   # lower name -> (items, chance, rare, inst key)
their_npc = {}
n_inst = 0
n_boss = 0
n_item_slots = 0
n_chance_known = 0
rare_bosses = []
for I in inst.values():
    n_inst += 1
    for b in I['bosses'].values():
        n_boss += 1
        loot = [int(x) for x in b['loot'].values()]
        ch = b['chance']
        chl = [int(x) for x in ch.values()] if ch else None
        if chl:
            n_item_slots += len(loot)
            n_chance_known += sum(1 for c in chl if c and c > 0)
        if b['rare']:
            rare_bosses.append((I['name'], b['name']))
        k = (b['name'] or '').lower()
        their_boss[k] = (set(loot), chl, I['name'])
        if b['npc']:
            their_npc[str(b['npc'])] = set(loot)

print('== 总量 ==')
print('Lootified 副本 %d 个 / 首领 %d 个；我方 DungeonLoot 副本 %d 个 / 来源条目 %d 个'
      % (n_inst, n_boss, len(list(ours.keys())), sum(len(list(v.values())) for v in ours.values())))
print('对方带掉率覆盖：%d/%d 物品槽位' % (n_chance_known, n_item_slots))
our_slots = 0; our_known = 0
for slug in ours.keys():
    for src in ours[slug].values():
        for it in src[5].values():
            our_slots += 1
            ch = it[2]
            if (ch is not None and ch is not False) or ch == 0:
                our_known += 1
print('我方掉率非空：%d/%d 物品槽位' % (our_known, our_slots))

print()
print('== 首领差（按英文 boss 名对齐）==')
miss_boss = []
for k, (items, chl, iname) in their_boss.items():
    if k not in our_boss:
        miss_boss.append((iname, k))
print('对方有而我方没有的首领：%d 个' % len(miss_boss))
by_inst = {}
for iname, k in miss_boss:
    by_inst.setdefault(iname, []).append(k)
for iname in sorted(by_inst):
    print('  [%s] %s' % (iname, ', '.join(by_inst[iname])))
extra_boss = [k for k in our_boss if k not in their_boss]
print('我方有而对方没有的来源条目：%d 个（多为小怪/宝箱/收集物，未必是缺失）' % len(extra_boss))

print()
print('== 物品差（按已对齐的首领）==')
only_their_total = 0
only_our_total = 0
miss_items_by_inst = {}
for k, (items, chl, iname) in their_boss.items():
    if k not in our_boss:
        continue
    d1 = items - our_boss[k]
    d2 = our_boss[k] - items
    only_their_total += len(d1)
    only_our_total += len(d2)
    if d1:
        miss_items_by_inst.setdefault(iname, {}).setdefault(k, set()).update(d1)
print('对方有而我方缺的掉落物品：%d 个（累计）' % only_their_total)
print('我方有而对方没有：%d 个（累计）' % only_our_total)
for iname in sorted(miss_items_by_inst):
    bosses = miss_items_by_inst[iname]
    n = sum(len(v) for v in bosses.values())
    print('  [%s] 缺 %d 件：' % (iname, n) + '; '.join(
        '%s:+%s' % (b, ','.join(sorted(str(x) for x in ids))[:90]) for b, ids in sorted(bosses.items())))

print()
print('== rare 首领（对方标记 rare）==')
for iname, b in rare_bosses:
    has = '有' if b.lower() in our_boss else '缺'
    print('  [%s] %s：%s' % (iname, b, has))

# ── 世界掉落 ──
load_lua(os.path.join(LOOT, 'Data/WorldDrops.lua'), 'LJ2')
wd = L.globals().LJ2.Data.WorldDrops
wm = L.globals().LJ2.Data.WorldMobs
print()
print('== 世界掉落 ==')
print('对方 WorldMobs（世界怪/稀有怪）：%d 个；WorldDrops（世界装备掉落）：%d 件' %
      (len(list(wm.keys())), len(list(wd.keys()))))
our_world = 0
for f in ('Data_Explore.lua', 'Data_NPCLoc.lua'):
    p = os.path.join(DF, 'Core/Data', f)
    if os.path.exists(p):
        txt = open(p, encoding='utf-8', errors='replace').read()
        our_world += txt.count('worldDrops') + txt.count('WorldDrops')
print('我方世界装备掉落表：无（Explore/NPCLoc 均非装备掉落）' if our_world == 0 else '?')

# ── 副本任务 ──
load_lua(os.path.join(LOOT, 'Data/Quests.lua'), 'LJ3')
iq = L.globals().LJ3.Data.InstanceQuests
their_qids = set()
n_iq = 0
for key in iq.keys():
    for q in iq[key].values():
        n_iq += 1
        if isinstance(q, (int, float)):
            their_qids.add(int(q))
        else:
            try:
                qid = q[1]
                if isinstance(qid, (int, float)):
                    their_qids.add(int(qid))
                else:
                    qid2 = q[2]
                    if isinstance(qid2, (int, float)):
                        their_qids.add(int(qid2))
            except Exception:
                pass
our_qids = set()
q = os.path.join(DF, 'Core/Data/Data_DungeonQuests.lua')
load_lua(q, 'NSQ')
dqs = L.globals().NSQ.DungeonQuests
n_oq = 0
for slug in dqs.keys():
    for row in dqs[slug].values():
        n_oq += 1
        our_qids.add(int(row[1]))
print()
print('== 副本任务 ==')
print('对方 InstanceQuests：%d 条（%d 个实例键）；我方：%d 条' % (n_iq, len(list(iq.keys())), n_oq))
inter = their_qids & our_qids
print('任务 ID 交集：%d；对方独有：%d；我方独有：%d' %
      (len(inter), len(their_qids - our_qids), len(our_qids - their_qids)))
