# -*- coding: utf-8 -*-
"""从副本任务数据提取「副本内任务 NPC」图标，产出 _route_plan/data/qicons/<dungeonId>.json

每条图标 = { x, y, floor, npcs: [{id, cn, quests:[任务id...], unk:bool}] }
坐标来源优先级：Data_MapPins 现有 quest 项 > Data_NPCLoc（uiMapID 命中副本层）> 未知（放入口旁，unk=true）
"""
import io
import json
import os
import re

ROOT = 'D:/workspace/DungeonsForever'
DATA = ROOT + '/_temp/_route_plan/data'
OUT = DATA + '/qicons'

ui = None


def parse_npcloc():
    s = io.open(ROOT + '/Core/Data/Data_NPCLoc.lua', encoding='utf-8').read()
    loc = {}
    for m in re.finditer(r'\[(\d+)\]\s*=\s*\{\s*(\d+),\s*([\d.]+),\s*([\d.]+),\s*"([^"]*)"', s):
        loc[int(m.group(1))] = (int(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5))
    return loc


def parse_mappins():
    s = io.open(ROOT + '/Core/Data/Data_MapPins.lua', encoding='utf-8').read()
    out = {}
    for dm in re.finditer(r'\["([a-z_0-9]+)"\]\s*=\s*\{(.*?)\n\s*\},', s, re.S):
        did, body = dm.group(1), dm.group(2)
        qm = re.search(r'quest\s*=\s*\{(.*)\}\s*,?\s*$', body, re.M)
        if not qm:
            continue
        items = []
        for m in re.finditer(r'\{\s*([\d.]+),\s*([\d.]+),\s*(\d+)(?:,\s*(\d+))?\s*\}', qm.group(1)):
            items.append((float(m.group(1)), float(m.group(2)), int(m.group(3)),
                          int(m.group(4)) if m.group(4) else 1))
        if items:
            out[did] = items
    return out


def parse_quests():
    s = io.open(ROOT + '/Core/Data/Data_DungeonQuests.lua', encoding='utf-8').read()
    quests = {}
    for dm in re.finditer(r'\["([a-z_0-9]+)"\]\s*=\s*\{(.*?)\n\s*\},', s, re.S):
        did, body = dm.group(1), dm.group(2)
        rows = []
        for rm in re.finditer(r'\{\s*(\d+),\s*("(?:A|H)"|nil),\s*(\d+),.*?\},\s*\n', body + '\n'):
            rows.append(int(rm.group(1)))
        quests[did] = rows
    return quests


def main():
    idx = json.load(io.open(DATA + '/index.json', encoding='utf-8'))
    loc = parse_npcloc()
    pins = parse_mappins()
    os.makedirs(OUT, exist_ok=True)

    s = io.open(ROOT + '/Core/Data/Data_DungeonQuests.lua', encoding='utf-8').read()
    total = 0
    for d in idx['dungeons']:
        did = d['id']
        bm = re.search(r'\["%s"\]\s*=\s*\{(.*?)\n\s*\},' % re.escape(did), s, re.S)
        if not bm:
            continue
        body = bm.group(1)
        fmap = {str(f['n']): f['ui'] for f in d['floors']}
        bypin = {}
        for x_, y_, qid_, fl_ in pins.get(did, []):
            bypin[qid_] = (x_, y_, fl_)
        icons = []
        for line in re.findall(r'^\s*\{.*?\},?\s*$', body, re.M):
            cols = split_cols(line)
            if cols is None:
                continue
            qid, loc_txt = cols[0], cols[5]
            inside = (not loc_txt) or ('副本内' in loc_txt) or (d['cn'] in loc_txt)
            if not inside:
                continue
            ent = {'qid': qid, 'cn': cols[16] or cols[4] or ('由物品起始' if cols[7] else ''),
                   'loc': loc_txt or '', 'x': None, 'y': None, 'floor': 1, 'unk': True}
            if cols[1] in ('A', 'H'):
                ent['side'] = cols[1]
            if qid in bypin:
                ent.update(x=bypin[qid][0], y=bypin[qid][1], floor=bypin[qid][2], unk=False)
            elif cols[15] and cols[15] in loc:
                m, x_, y_ = loc[cols[15]][0], loc[cols[15]][1], loc[cols[15]][2]
                for fn, fu in fmap.items():
                    if fu and int(fu) == m:
                        ent.update(x=x_, y=y_, floor=int(fn), unk=False)
                        break
            icons.append(ent)
        if not icons:
            continue
        io.open(OUT + '/%s.json' % did, 'w', encoding='utf-8', newline='\n').write(
            json.dumps({'icons': icons}, ensure_ascii=False))
        n_unk = sum(1 for e in icons if e['unk'])
        total += len(icons)
        print('%-24s 图标%2d 已定位%2d 待定%2d' % (did, len(icons), len(icons) - n_unk, n_unk))
    print('total', total)


def split_cols(line):
    line = line.strip()
    qid = re.match(r'\{\s*(\d+),', line)
    if not qid:
        return None
    cols = []
    depth = 0
    cur = ''
    in_str = False
    esc = False
    for ch in line[1:]:
        if esc:
            cur += ch
            esc = False
            continue
        if ch == '\\':
            cur += ch
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            cur += ch
            continue
        if not in_str:
            if ch == '{':
                depth += 1
            elif ch == '}':
                if depth == 0:
                    break
                depth -= 1
            elif ch == ',' and depth == 0:
                cols.append(cur.strip())
                cur = ''
                continue
        cur += ch
    cols.append(cur.strip())
    if len(cols) < 17:
        return None

    def val(c):
        if c == 'nil' or c == '':
            return None
        m = re.match(r'^-?\d+$', c)
        if m:
            return int(c)
        m = re.match(r'^"(.*)"$', c)
        if m:
            return m.group(1)
        return c

    return [val(c) for c in cols[:17]]


if __name__ == '__main__':
    main()
