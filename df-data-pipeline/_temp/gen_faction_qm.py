# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_FactionQM.lua（声望军需官位置 · 生成物）。

数据源两层：
- 军需官 NPC 对应关系：QMS 手工核对表（factionID → npcID），
  由「阵营奖励物品 → 出售 NPC」聚合得出并人工复核（questie item_vendors）。
- 坐标：questie_forever.json 的 npc_spawns（旧 areaID 口径），
  经 Core/Data/Data_AreaMap.lua 换算成 uiMapID 后落盘。

用法：python _temp/gen_faction_qm.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
QUESTIE = os.path.join(HERE, 'questie', 'questie_forever.json')
AMAP_LUA = os.path.join(DF, 'Core', 'Data', 'Data_AreaMap.lua')
DST = os.path.join(DF, 'Core', 'Data', 'Data_FactionQM.lua')

QMS = {
    21: 265575,
    270: 14921,
    369: 265576,
    470: 265574,
    509: 15127,
    510: 15126,
    529: 11536,
    576: 11557,
    577: 265577,
    609: 15179,
    2586: 256389,
    2587: 256384,
    2740: 32287,
    2765: 255151,
    2787: 264078,
    2798: 263570,
    2827: 255897,
}

TOC = r"D:\workspace\DungeonsForever\_temp\questie\forever\QuestieDB\QuestieDB_Forever.toc"


def load_amap():
    amap = {}
    for line in open(AMAP_LUA, encoding='utf-8'):
        m = re.match(r"\s*\[(\d+)\]\s*=\s*(\d+)", line)
        if m:
            amap[int(m.group(1))] = int(m.group(2))
    return amap


def main():
    with open(QUESTIE, encoding='utf-8') as f:
        q = json.load(f)
    spawns = q['npc_spawns']
    amap = load_amap()
    missing_zone = []
    out = []
    for fid in sorted(QMS):
        nid = QMS[fid]
        sp = spawns.get(str(nid)) or spawns.get(nid)
        if not sp:
            print('缺坐标: 阵营 %d npc %d' % (fid, nid))
            continue
        zone = next(iter(sp))
        xy = sp[zone]
        z = int(zone)
        mid = amap.get(z)
        if not mid:
            missing_zone.append((fid, nid, z))
            continue
        out.append((fid, nid, mid, float(xy[0]), float(xy[1])))
    if missing_zone:
        for fid, nid, z in missing_zone:
            print('areaID %d（阵营 %d npc %d）不在 Data_AreaMap' % (z, fid, nid))
        sys.exit(1)
    lines = [
        '-- =============================================================================',
        '-- 无限副本手册 · 声望军需官位置',
        '-- ★ 本文件由脚本生成，请勿手改 ★',
        '-- 用途：声望页「军需官位置」按钮 → 地图标记军需官。条目 = {npcID, uiMapID, x, y}',
        '-- =============================================================================',
        '',
        'local AddOnName, ns = ...',
        '',
        'ns.FactionQM = {',
    ]
    for fid, nid, mid, x, y in out:
        lines.append('    [%d] = { %d, %d, %.2f, %.2f },' % (fid, nid, mid, x, y))
    lines += ['}', '']
    open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('写出 %d 条 → %s' % (len(out), DST))


import sys
main()
