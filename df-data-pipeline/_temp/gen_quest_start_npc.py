# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import io

from lupa import lua51

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'D:/workspace/DungeonsForever'
QJ = ROOT + '/_temp/questie/questie_forever.json'
OUT_LUA = ROOT + '/Core/Data/Data_QuestStartNpc.lua'
NEED = ROOT + '/_temp/_qsn_needwow.json'
WOW = ROOT + '/_temp/_qsn_wow_loc.json'

data = json.load(open(QJ, encoding='utf-8'))
start_item = data['quest_startItem']
drop_npcs = data['item_npcDrops']
spawns = data['npc_spawns']

L = lua51.LuaRuntime(unpack_returned_tuples=True)

def load_lua(path, setup):
    src = open(path, encoding='utf-8').read()
    src = re.sub(r'^local [A-Za-z_, ]+ = \.\.\.$', 'local ns = NS', src, count=1, flags=re.M)
    return L.execute('return (function() %s %s return NS end)()' % (setup, src))

nploc = load_lua(ROOT + '/Core/Data/Data_NPCLoc.lua', 'local NS = { IsTitan = true }')['NPCLoc']
dq_ns = load_lua(ROOT + '/Core/Data/Data_DungeonQuests.lua', 'local NS = {}')
quests = dq_ns['DungeonQuests']
ext = dq_ns['DungeonQuestExtInfo']
amap = load_lua(ROOT + '/Core/Data/Data_AreaMap.lua', 'local NS = {}')['AreaMap']
entry = load_lua(ROOT + '/Core/Data/Data_DungeonEntry.lua', 'local NS = {}')['DungeonEntry']

walk_rows = L.eval(r'''
function(t)
    local out = {}
    for _, dq in pairs(t) do
        if type(dq) == "table" then
            for _, q in ipairs(dq) do
                if type(q[1]) == "number" and not q[16] then
                    out[#out + 1] = q[1] end end end end
    return table.concat(out, ",")
end
''')
walk_si = L.eval(r'''
function(t)
    local out = {}
    for k, v in pairs(t) do
        if type(k) == "number" and v.si and not v.npcid then
            out[#out + 1] = k end end
    table.sort(out)
    return table.concat(out, ",")
end
''')
walk_slug = L.eval(r'''
function(t)
    local out = {}
    for slug, dq in pairs(t) do
        if type(dq) == "table" then
            for _, q in ipairs(dq) do
                if type(q[1]) == "number" then
                    out[#out + 1] = slug .. "|" .. q[1]
                    if q[9] then
                        for _, seg in ipairs(q[9]) do
                            if type(seg) == "number" then
                                out[#out + 1] = slug .. "|" .. seg
                            end
                        end
                    end
                end
            end
        end
    end
    return table.concat(out, "\n")
end
''')
has = L.eval('function(t, k) return t[k] ~= nil end')
amap_get = L.eval('function(t, k) return t[k] end')
entry_get = L.eval('function(t, k) return t[k] end')

slug_of = {}
for line in walk_slug(quests).split('\n'):
    if '|' in line:
        sg, qid = line.split('|', 1)
        slug_of.setdefault(int(qid), sg)

entry_by_zone = {}
for k in L.eval('function(t) local ks = {} for key in pairs(t) do ks[#ks+1] = key end return table.concat(ks, ",") end')(entry).split(','):
    v = entry_get(entry, k)
    if v and v[4] and not entry_by_zone.get(v[4]):
        entry_by_zone[v[4]] = k

qids = sorted(set(int(x) for x in walk_rows(quests).split(',') if x)
              | set(int(x) for x in walk_si(ext).split(',') if x))

wow_loc = {}
if os.path.exists(WOW):
    wow_loc = json.load(open(WOW, encoding='utf-8'))

def loc_from_nploc(nid):
    if not has(nploc, nid):
        return None
    v = L.eval('function(t, k) return t[k] end')(nploc, nid)
    return [int(v[1]), float(v[2]), float(v[3])]

def loc_from_spawns(nid):
    sp = spawns.get(str(nid)) or {}
    for z, pt in sp.items():
        if not (isinstance(pt, list) and len(pt) >= 2):
            continue
        x, y = pt[0], pt[1]
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
            continue
        if not (0 < x <= 100 and 0 < y <= 100):
            continue
        um = amap_get(amap, int(z))
        if not um:
            continue
        return [int(um), round(float(x), 1), round(float(y), 1)]
    return None

def loc_from_wow(nid):
    w = wow_loc.get(str(nid))
    if w and len(w) >= 3 and w[0]:
        return [int(w[0]), float(w[1]), float(w[2])]
    return None

def loc_from_entry(qid, zone):
    sg = slug_of.get(qid)
    if not sg and zone:
        sg = entry_by_zone.get(zone)
    if not sg:
        return None
    v = entry_get(entry, sg)
    if v:
        return [int(v[1]), float(v[2]), float(v[3])]
    return None

resolved = {}
need = {}
stats = {'nploc': 0, 'spawns': 0, 'wow': 0, 'entry': 0, 'noitem': 0, 'none': 0}
for qid in qids:
    si = start_item.get(str(qid))
    if not si:
        stats['noitem'] += 1
        continue
    cands = []
    for iid in (si if isinstance(si, list) else [si]):
        cands.extend(drop_npcs.get(str(iid), []))
    cands = sorted(set(cands))
    if not cands:
        stats['none'] += 1
        continue
    qzone = None
    ev = L.eval('function(t, k) return t[k] end')(ext, qid)
    if ev is not None:
        qzone = ev['zone']
    pick = None
    for src, fn in (('nploc', loc_from_nploc), ('spawns', loc_from_spawns), ('wow', loc_from_wow)):
        for nid in cands:
            loc = fn(nid)
            if loc:
                pick = (nid, loc, src)
                break
        if pick:
            break
    if not pick:
        eloc = loc_from_entry(qid, qzone if type(qzone) == str else None)
        if eloc:
            resolved[qid] = (cands[0], eloc, 'entry')
            stats['entry'] += 1
        else:
            need[qid] = cands[0]
            stats['wow'] += 1
        continue
    resolved[qid] = pick
    stats[pick[2]] += 1

print('quests scanned: %d -> %s' % (len(qids), stats))
for qid in sorted(need):
    print('  NEEDWOW qid=%s rep_npc=%s' % (qid, need[qid]))
json.dump(need, open(NEED, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def npc_name(nid):
    w = wow_loc.get(str(nid))
    if w and len(w) >= 4 and w[3]:
        return re.sub(r'["\\]', '', str(w[3]))
    return None

lines = []
lines.append('local _, ns = ...')
lines.append('')
lines.append('ns.DungeonQuestStartNpc = {')
for qid in sorted(resolved):
    nid, loc, src = resolved[qid]
    nm = npc_name(nid)
    seg = '%d, %s, %d, %s, %s' % (nid, ('"%s"' % nm) if nm else 'nil', loc[0], loc[1], loc[2])
    lines.append('    [%d] = { %s },' % (qid, seg))
lines.append('}')
open(OUT_LUA, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('written', OUT_LUA, '(entries: %d)' % len(resolved))
