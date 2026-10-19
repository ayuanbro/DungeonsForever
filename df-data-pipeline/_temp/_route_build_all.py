# -*- coding: utf-8 -*-
"""把全部副本的路线/图钉/注释/底图整理成一份给 HTML 微调页用的清单。

产出：
  _route_plan/data/<dungeonId>.json   单副本原始 route 数据（沿用 route.json 结构）
  _route_plan/data/index.json         全部副本清单（页面只读这一个）
"""
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _route_gen as G

ROOT = 'D:/workspace/DungeonsForever'
PLAN = ROOT + '/_temp/_route_plan'
DATA = PLAN + '/data'
IMG = PLAN + '/img/maps'
MAPUI = ROOT + '/Core/MapUI.lua'
DUNGEONS = ROOT + '/Core/Data/Data_Dungeons.lua'
BOSS_POS = ROOT + '/Core/Data/Data_BossPos.lua'

FDR_KEY = {
    'ragefire_chasm': 'ragefire',
    'wailing_caverns': 'wailingcaverns',
    'the_deadmines': 'deadmines',
    'shadowfang_keep': 'shadowfang',
    'blackfathom_deeps': 'blackfathom',
    'the_stockade': 'stockade',
    'gnomeregan': 'gnomeregan',
    'razorfen_kraul': 'razorfenkraul',
    'razorfen_downs': 'razorfendowns',
    'sm_graveyard': 'sm_graveyard',
    'sm_library': 'sm_library',
    'sm_armory': 'sm_armory',
    'sm_cathedral': 'sm_cathedral',
    'uldaman': 'uldaman',
    'zul_farrak': 'zulfarrak',
    'maraudon': 'maraudon',
    'sunken_temple': 'sunkentemple',
    'blackrock_depths': 'blackrockdepths',
    'dire_maul_east': 'diremaul_east',
    'dire_maul_north': 'diremaul_north',
    'dire_maul_west': 'diremaul_west',
    'lower_blackrock_spire': 'lowerblackrock',
    'scholomance': 'scholomance',
    'stratholme_main': 'stratholme',
}


def parse_art():
    s = io.open(MAPUI, encoding='utf-8').read()
    dm = re.search(r'local DM = \{ "([^"]+)",\s*\{([^}]*)\} \}', s)
    st = re.search(r'local ST = \{ "([^"]+)", \{([^}]*)\} \}', s)
    smd = re.search(r'local SM_DIR = "([^"]+)"', s).group(1)
    DM = [dm.group(1)] + [x.strip().strip('"') for x in dm.group(2).split(',') if x.strip()]
    ST = [st.group(1)] + [x.strip().strip('"') for x in st.group(2).split(',') if x.strip()]
    body = re.search(r'^local ART = \{(.*?)\n\}', s, re.S | re.M).group(1)
    art = {}
    for line in body.split('\n'):
        line = line.strip()
        mm = re.match(r'^(\w+)\s*=\s*\{\s*"([^"]+)",\s*\{([^}]*)\}\s*\},?$', line)
        if mm:
            art[mm.group(1)] = [mm.group(2)] + [x.strip().strip('"') for x in mm.group(3).split(',') if x.strip()]
            continue
        mm = re.match(r'^(\w+)\s*=\s*(DM|ST)\s*,?$', line)
        if mm:
            art[mm.group(1)] = list(DM if mm.group(2) == 'DM' else ST)
            continue
        mm = re.match(r'^(\w+)\s*=\s*SMW\("([^"]+)"\)\s*,?$', line)
        if mm:
            art[mm.group(1)] = [smd, mm.group(2)]
            continue
    for mm in re.finditer(r'(\w+)\s*=\s*\{\s*"([^"]+)",\s*\n\s*\{([^}]*)\}\s*\}', body):
        art.setdefault(mm.group(1), [mm.group(2)] + [x.strip().strip('"') for x in mm.group(3).split(',') if x.strip()])
    return art


def parse_floor_names():
    s = io.open(MAPUI, encoding='utf-8').read()
    body = re.search(r'^local FLOOR_NAMES = \{(.*?)\n\}', s, re.S | re.M).group(1)
    out = {}
    for mm in re.finditer(r'(\w+)\s*=\s*\{(.*?)\n    \},', body, re.S):
        rows = []
        for rm in re.finditer(r'\{ "([^"]*)", "([^"]*)", "([^"]*)" \}', mm.group(2)):
            rows.append(rm.group(2))
        out[mm.group(1)] = rows
    return out


def parse_dungeon_list():
    s = io.open(DUNGEONS, encoding='utf-8').read()
    out = []
    for mm in re.finditer(r'\{ id = "([a-z_0-9]+)",\s*name = "([^"]*)",\s*nameEn = "([^"]*)"', s):
        out.append({'id': mm.group(1), 'cn': mm.group(2), 'en': mm.group(3)})
    return out


def derive_floor_key(fdr_key, dungeon_id, paths, stops):
    uis = sorted({p['floor'] for p in paths})
    bp = {}
    try:
        bp = G.parse_boss_pos(dungeon_id)
    except Exception:
        bp = {}
    votes = defaultdict(Counter)
    for st in stops:
        for q in bp.get(st['en'], []):
            votes[st['floor']][q['f']] += 1
    layers = {f: (votes[f].most_common(1)[0][0] if votes[f] else None) for f in uis}
    return uis, layers


def main():
    os.makedirs(DATA, exist_ok=True)
    art = parse_art()
    fnames = parse_floor_names()
    dlist = parse_dungeon_list()
    print('副本 %d / ART %d / 楼层名表 %d' % (len(dlist), len(art), len(fnames)))

    out = []
    for d in dlist:
        did, cn = d['id'], d['cn']
        row = {'id': did, 'cn': cn, 'en': d['en'], 'fdr': FDR_KEY.get(did) or '',
               'floors': [], 'route': bool(FDR_KEY.get(did))}
        a = art.get(did)
        nfloor = 1
        names = []
        if a:
            nfloor = max(1, len(a[1:]))
            names = fnames.get(did) or []
        else:
            names = fnames.get(did) or []

        route_data = {}
        fk = FDR_KEY.get(did)
        note = ''
        if fk:
            try:
                paths, stops, notes = G.parse_fdr(fk)
            except Exception as e:
                paths, stops, notes = [], [], []
                note = 'FDR 解析失败: %s' % e
            if paths:
                uis, guess = derive_floor_key(fk, did, paths, stops)
                for st in stops:
                    if st['floor'] not in uis:
                        uis.append(st['floor'])
                for nt in notes:
                    if nt['floor'] not in uis:
                        uis.append(nt['floor'])
                uis = sorted(set(uis))
                if len(uis) == nfloor:
                    floor_key = {u: i + 1 for i, u in enumerate(uis)}
                    note = note or ('%d 层按序号对齐' % len(uis))
                else:
                    floor_key = {}
                    last = 0
                    for u in uis:
                        g = guess.get(u) or (last + 1)
                        g = max(g, last + 1)
                        last = g
                        floor_key[u] = g
                    note = note or ('%d 层对 %d 张图，按首领位置推断' % (len(uis), nfloor))
                try:
                    G.gen(fdr_key=fk, dungeon_id=did, floor_uids=uis,
                          floor_key=floor_key, out_path=DATA + '/%s.json' % did)
                    route_data = json.load(io.open(DATA + '/%s.json' % did, encoding='utf-8'))
                except Exception as e:
                    note = (note + ' / ' + 'GEN FAIL %s' % e).strip(' /')

        bp = {}
        try:
            bp = G.parse_boss_pos(did)
        except Exception:
            bp = {}

        ui_of_layer = {}
        for u, idx in (floor_key if fk and route_data else {}).items():
            ui_of_layer[idx] = str(u)

        for n in range(1, nfloor + 1):
            ui = ui_of_layer.get(n)
            r = route_data.get(ui) if ui else None
            pins = []
            for en, pts in bp.items():
                for q in pts:
                    if (q.get('f') or 1) == n:
                        pins.append({'en': en, 'x': q['x'], 'y': q['y']})
            fl = {
                'n': n,
                'ui': ui,
                'name': (names[n - 1] if n - 1 < len(names) else '第 %d 层' % n),
                'img': ('img/maps/%s_%d.jpg' % (did, n)) if os.path.exists(IMG + '/%s_%d.jpg' % (did, n)) else '',
                'pins': pins,
                'segs': (r or {}).get('segs') or [],
                'sides': (r or {}).get('sides') or [],
                'stops': (r or {}).get('stops') or [],
                'notes': (r or {}).get('notes') or [],
                'loose': (r or {}).get('loose') or [],
                'raw': (r or {}).get('raw') or [],
                'entrance': (r or {}).get('entrance') or None,
            }
            row['floors'].append(fl)
        row['note'] = note
        out.append(row)
        segs = sum(len(f['segs']) for f in row['floors'])
        print('  %-22s %-10s 层%d 段%d 图%d %s' % (
            did, cn, len(row['floors']), segs,
            sum(1 for f in row['floors'] if f['img']), note), flush=True)

    bfd = DATA + '/blackfathom_deeps.json'
    if os.path.exists(bfd):
        io.open(PLAN + '/route.json', 'w', encoding='utf-8', newline='\n').write(
            io.open(bfd, encoding='utf-8').read())

    js = {'dungeons': out}
    io.open(DATA + '/index.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(js, ensure_ascii=False, separators=(',', ':')))
    print('\nindex.json %.1f KB / 有底图 %d 层 / 有路线 %d 副本' % (
        os.path.getsize(DATA + '/index.json') / 1024.0,
        sum(1 for d in out for f in d['floors'] if f['img']),
        sum(1 for d in out if sum(len(f['segs']) for f in d['floors']))))


if __name__ == '__main__':
    main()
