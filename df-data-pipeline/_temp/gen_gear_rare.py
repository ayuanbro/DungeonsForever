# -*- coding: utf-8 -*-
"""生成 Data_GearRareSpawns.lua：装备库「稀有掉落」装备 → 稀有怪 NPC 刷点坐标。

链路：Data_Gear src 串（含 zh 怪名/区域）
  → zh→EN（_gqf_name_cache.json npcs + Lootified Locale_zhCN name 反查）
  → EN→npcID（QuestieDB npc_info name 索引）
  → npcID→刷点（npc_spawns {areaID: [x,y]}）
  → areaID→uiMapID（Data_AreaMap.lua）
输出：ns.GearRareSpawns = { [itemId] = { {npc, uiMap, area, x, y}, ... } }
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lupa import LuaRuntime


def load_lua(path, name):
    with open(path, 'rb') as f:
        src = f.read().decode('utf-8', 'replace')
    from lupa import lua51
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    t = L.table()
    L.globals()[name] = t
    fn = L.eval("function(src,name) local f,err=loadstring(src,name) "
                "if not f then error(err) end return f end")(
        src, os.path.basename(path))
    fn("addon", t)
    return L


def parse_area_map():
    txt = open(os.path.join(ROOT, 'Core/Data/Data_AreaMap.lua'),
               encoding='utf-8').read()
    amap = {int(a): int(m) for a, m in
            re.findall(r'\[(\d+)\]\s*=\s*(\d+)', txt)}
    z2a = {z: int(a) for a, m, z in
           re.findall(r'\[(\d+)\]\s*=\s*(\d+),\s*--\s*(\S+)', txt)}
    zones = set(re.findall(r'--\s*(\S[^\r\n]*?)\s*$', txt, re.M))
    zones = {z.strip('，、 ') for z in zones}
    return amap, zones, z2a


def split_zone_name(place, zones):
    if '·' in place:
        a, b = place.split('·', 1)
        if a in zones:
            return a, b
    return '', place


def parse_rare_items():
    gear = open(os.path.join(ROOT, 'Core/Data/Data_Gear.lua'),
                encoding='utf-8').read()
    i = gear.find('src = {')
    seg = gear[i:gear.find('\n},', i)]
    _, zones, _ = parse_area_map()
    out = []
    for sid, s in re.findall(r'\[(\d+)\]=\"((?:[^\"\\\\]|\\\\.)*)\"', seg):
        if '稀有' not in s:
            continue
        if '|' in s:
            kind, place = (s.split('|', 1) + [''])[:2]
        else:
            kind, place = s, ''
        if kind == '稀有掉落':
            zone, name = split_zone_name(place, zones)
            out.append((int(sid), name.strip(), zone.strip()))
        elif place.startswith('稀有'):
            zone = place.split('，', 1)[1] if '，' in place else ''
            out.append((int(sid), kind.strip(), zone.strip()))
        else:
            out.append((int(sid), kind.strip(), ''))
    return out


def main():
    items = parse_rare_items()
    print('稀有装备条目:', len(items))

    qd = json.load(open(os.path.join(HERE, 'questie', 'questie_forever.json'),
                        encoding='utf-8'))
    ni, ns_ = qd['npc_info'], qd['npc_spawns']
    en2ids = {}
    for k, v in ni.items():
        if isinstance(v, list) and v and isinstance(v[0], str):
            en2ids.setdefault(v[0], []).append(int(k))

    cache = json.load(open(os.path.join(HERE, '_gqf_name_cache.json'),
                           encoding='utf-8'))
    zh2en = {}
    for en, v in cache.get('npcs', {}).items():
        z = (v or {}).get('zh')
        if z and z != en:
            zh2en.setdefault(z, en)

    loc_zh = {}
    try:
        LL = load_lua(r"D:/Game/World of Warcraft/_classic_beta_/Interface/"
                      r"AddOns/Lootified/Data/Locale_zhCN.lua", 'NSLJ')
        nm = LL.globals().NSLJ.Locales.zhCN()['name']
        for k, v in nm.items():
            if isinstance(k, str) and isinstance(v, str) and v != k:
                loc_zh.setdefault(v, k)
        print('Lootified 译名:', len(loc_zh))
    except Exception as e:
        print('⚠ Lootified 加载失败:', e)

    amap, _, z2a = parse_area_map()

    out, miss = {}, []
    for iid, name, zone in items:
        en = zh2en.get(name) or loc_zh.get(name) or (name if re.match(
            r'^[\x20-\x7e]+$', name) else None)
        ids = en2ids.get(en, []) if en else []
        cands = []
        for nid in ids:
            sp = ns_.get(str(nid))
            if not sp:
                continue
            for z, xy in sp.items():
                aid, m = int(z), amap.get(int(z))
                if m:
                    cands.append({'npc': nid, 'uiMap': m, 'area': aid,
                                  'x': round(xy[0], 2), 'y': round(xy[1], 2),
                                  'zh': name})
        if cands:
            cands.sort(key=lambda c: (c['uiMap'], c['x'], c['y']))
            out[iid] = cands
            print('  [%d] %-14s %s -> %d 处' % (iid, name, en, len(cands)))
        else:
            miss.append((iid, name, zone, en))
    print('命中 %d / 未命中 %d' % (len(out), len(miss)))
    for iid, name, zone, en in miss:
        print('  ✗ [%d] %s（区域=%s EN=%s）' % (iid, name, zone or '-', en))

    if miss:
        out, miss = zh_pass(out, miss, ns_, amap, z2a)
        print('补查后命中 %d / 未命中 %d' % (len(out), len(miss)))
        for iid, name, zone, en in miss:
            print('  ✗ [%d] %s（区域=%s）' % (iid, name, zone or '-'))

    if out:
        lines = []
        for iid in sorted(out):
            rows = ', '.join(
                '{%d,%d,%d,%.2f,%.2f,"%s"}' % (c['npc'], c['uiMap'],
                                               c['area'], c['x'], c['y'],
                                               c['zh'])
                for c in out[iid])
            lines.append('[%d]={%s}' % (iid, rows))
        body = ',\n'.join(lines)
        txt = (
            "-- =============================================================================\n"
            "-- 无限副本手册 · 装备库稀有怪刷点（itemID → 刷点列表）\n"
            "-- ★ 本文件由 _temp/gen_gear_rare.py 生成，请勿手改 ★\n"
            "-- 行格式：[itemID]={{npcID,uiMapID,areaID,x,y,zhName},...}\n"
            "-- =============================================================================\n"
            "\nlocal AddonName, ns = ...\n\n"
            "ns.GearRareSpawns = {\n" + body + ",\n}\n")
        dst = os.path.join(ROOT, 'Core/Data/Data_GearRareSpawns.lua')
        open(dst, 'wb').write(txt.encode('utf-8'))
        print('写出', dst, len(out), '件')


def norm(s):
    return re.sub(r'[\s·\"“”\u201c\u201d]', '', s or '')


def nether_zh(nid, timeout=20):
    r = subprocess.run(
        ['curl', '-s', '-m', str(timeout), '-x', 'http://127.0.0.1:7897',
         'https://nether.wowhead.com/forever/tooltip/npc/%d?locale=zhCN' % nid],
        capture_output=True, text=True)
    try:
        return (json.loads(r.stdout).get('name') or '').strip()
    except Exception:
        return ''


def zh_pass(out, miss, ns_, amap, z2a):
    cpath = os.path.join(HERE, '_rare_zh_cache.json')
    zc = {}
    if os.path.exists(cpath):
        try:
            zc = json.load(open(cpath, encoding='utf-8'))
        except Exception:
            zc = {}
    z2n = {}
    for iid, name, zone, en in miss:
        aid = z2a.get(zone)
        if not aid:
            continue
        for k, v in ns_.items():
            if str(aid) in v:
                z2n.setdefault(int(k), int(aid))
    todo = [k for k in z2n if str(k) not in zc]
    print('nether 补名候选 %d（需爬 %d）' % (len(z2n), len(todo)))
    for i, nid in enumerate(sorted(todo)):
        n = nether_zh(nid)
        zc[str(nid)] = n
        if i % 40 == 39:
            json.dump(zc, open(cpath, 'w', encoding='utf-8'))
            print('  爬名 %d/%d' % (i + 1, len(todo)))
        time.sleep(0.35)
    json.dump(zc, open(cpath, 'w', encoding='utf-8'))

    zh2ids = {}
    for k, n in zc.items():
        key = norm(n)
        if key:
            zh2ids.setdefault(key, []).append(int(k))
    for iid, name, zone, en in list(miss):
        key = norm(name)
        ids = zh2ids.get(key, [])
        if not ids and len(key) >= 4:
            for kk, vv in zh2ids.items():
                if key in kk or kk in key:
                    ids = vv
                    break
        cands = []
        for nid in ids:
            sp = ns_.get(str(nid)) or {}
            for z, xy in sp.items():
                m = amap.get(int(z))
                if m:
                    cands.append({'npc': nid, 'uiMap': m, 'area': int(z),
                                  'x': round(xy[0], 2), 'y': round(xy[1], 2),
                                  'zh': name})
        if cands:
            cands.sort(key=lambda c: (c['uiMap'], c['x'], c['y']))
            out[iid] = cands
            miss.remove((iid, name, zone, en))
            print('  ✓ [%d] %s -> npc %d，%d 处'
                  % (iid, name, cands[0]['npc'], len(cands)))
    return out, miss


if __name__ == '__main__':
    main()
