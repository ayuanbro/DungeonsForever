# -*- coding: utf-8 -*-
"""专业页数据 · 商人定位表（vendor_loc.json → Data_ProfVendors.lua 的数据源）。

为什么要有这一步：配方来源里的 vendors[] 只有「英文名 + 英文区域名」，没有 ID
也没有坐标 —— 界面要「点击商人出售的配方 → 地图落点」就得知道每个商人站在哪。

数据从三个来源汇：
  1. 站点自身的 `vendor` 字段（各专业军需官，a/h 各一）—— 带 NPCID 与坐标；
  2. zone_ids.json —— 商人所在英文区域名 → AreaTable ID（界面再经 Data_AreaMap
     转 uiMapID，与升级页军需官同一条口径）；
  3. wowhead（--resolve，后置）：其余商人按「名字 + 区域」搜 NPC ID，再抓
     /forever/cn/npc=ID 页拿中文名 + g_mapperData 首点位。wowhead 对本机/代理
     IP 有时段性封锁（CloudFront 403 / r.jina.ai 域禁），所以这步**单独可重跑**
     且结果合并进 vendor_loc.json，不阻塞主链路。

产物 `_fc/data/vendor_loc.json`：{ "Nina Surefire": {"id":256729,"x":10.8,...}, ... }
  · id / x / y / areaID / mapID 任一都可能暂缺（null）—— UI 只落有坐标的；
  · 名字键恒为英文原文（与站点数据一致，localize 之前查它）。

用法：
    python fc_vendors.py             # 收集 + 种子（军需官），只写 vendor_loc.json
    python fc_vendors.py --report    # 覆盖率对账（多少商人有 ID / 有坐标）
    python fc_vendors.py --resolve   # 对缺坐标的商人跑 wowhead（联网，慢）
"""
import argparse
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '_fc', 'data')
OUT = os.path.join(DATA, 'vendor_loc.json')
ZH_JSON = os.path.join(HERE, '_fc', 'i18n', 'zh.json')


def load_json(path, default):
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return default


def collect_vendors():
    """所有配方来源里的唯一商人名 → {zones:set}。rows / enchants / crafted 三处同构。"""
    out = {}
    for f in glob.glob(os.path.join(DATA, 'prof_*.json')):
        d = json.load(open(f, encoding='utf-8'))
        for coll in ('rows', 'enchants', 'crafted'):
            for r in d.get(coll) or []:
                src = r.get('source')
                if not isinstance(src, dict):
                    continue
                for v in src.get('vendors') or []:
                    if isinstance(v, dict) and (v.get('npc') or v.get('name')):
                        out.setdefault(v.get('npc') or v.get('name'), set()).add(v.get('zone'))
    return out


def seed_from_site(loc):
    """军需官种子：站点 vendor 字段带 NPCID + 坐标；区域 AreaID 沿用营地口径。"""
    zone_ids = load_json(os.path.join(DATA, 'zone_ids.json'), {})
    for f in glob.glob(os.path.join(DATA, 'prof_*.json')):
        d = json.load(open(f, encoding='utf-8'))
        for side in ('a', 'h'):
            vd = (d.get('vendor') or {}).get(side)
            if not isinstance(vd, dict) or not vd.get('npc'):
                continue
            cur = loc.setdefault(vd['npc'], {})
            if vd.get('id'):
                cur['id'] = int(vd['id'])
            if vd.get('x') is not None and vd.get('y') is not None:
                cur['x'] = vd['x']
                cur['y'] = vd['y']
    return loc


def fill_area_ids(loc, vendors):
    """按商人自己的区域名填 areaID（zone_ids 没有的区域留空，等 wowhead 的 mapID）。"""
    for name, zones in vendors.items():
        cur = loc.setdefault(name, {})
        if cur.get('areaID') or cur.get('mapID'):
            continue
        for z in zones:
            aid = zone_ids_fill(loc, z) if z else None
            if aid:
                cur['areaID'] = aid
                break
    return loc


_ZIDS = None


def zone_ids_fill(loc, z):
    global _ZIDS
    if _ZIDS is None:
        _ZIDS = load_json(os.path.join(DATA, 'zone_ids.json'), {})
    return _ZIDS.get(z)


def report(loc, vendors):
    n = len(vendors)
    has_id = sum(1 for k in vendors if loc.get(k, {}).get('id'))
    has_pos = sum(1 for k in vendors
                  if loc.get(k, {}).get('x') is not None and (loc[k].get('areaID') or loc[k].get('mapID')))
    print('=== 商人定位表 ===')
    print('  唯一商人 %d · 有 NPCID %d · 可落图 %d' % (n, has_id, has_pos))
    missing = sorted(k for k in vendors if not (loc.get(k, {}).get('x') is not None
                                                and (loc[k].get('areaID') or loc[k].get('mapID'))))
    if missing:
        print('  未定位 %d 个（等 wowhead --resolve）：%s…' % (len(missing), '、'.join(missing[:8])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--resolve', action='store_true', help='wowhead 解析缺失商人（联网）')
    args = ap.parse_args()

    loc = load_json(OUT, {})
    vendors = collect_vendors()
    seed_from_site(loc)
    fill_area_ids(loc, vendors)

    if args.resolve:
        import fc_vendors_resolve  # 单独一文件：wowhead 通道（可能被 IP 封锁）
        fc_vendors_resolve.run(loc, vendors)

    json.dump(loc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1, sort_keys=True)
    report(loc, vendors)


if __name__ == '__main__':
    main()
