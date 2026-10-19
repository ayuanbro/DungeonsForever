# -*- coding: utf-8 -*-
"""
生成 Core/Data/Data_AreaMap.lua —— areaID → uiMapID（区域 → 世界地图号）。

★ 为什么要这张表（2026-10-01 实机事故）：
  无限服客户端（1.60.1.70009）**没有** C_Map.GetMapInfoFromAreaID
  （核对：D:/UGit/wow-ui-source-forever 的 MapDocumentation.lua 全表无此函数；
   该客户端 C_Map 只有 GetAreaInfo（areaID→名字），拿不回 mapID）。
  于是「areaID → uiMapID」在实机上**只能**靠静态表；表里漏一个 key，
  点热点就是静默失败（只弹一句「没有独立世界地图」）。
  探索页的 AREA_MAP 原来只有 31 项，暴风城/幽暗城/泽风岛三块地都不在 → 小动物页三处全点不动。

数据源：wago.tools 的 UiMapAssignment（与专业页 CAMP_AREA_MAP 的 1433/1413 同源口径）
  https://wago.tools/db2/UiMapAssignment/csv?build=<build>
  https://wago.tools/db2/UiMap   /csv?build=<build>&locale=zhCN   （只取 Name_lang 作备注）
  缓存落 _temp/_uimap_cache/；`--refresh` 强制重下。

用法：
  python _temp/gen_area_map.py            # 用缓存（缺则自动下）
  python _temp/gen_area_map.py --refresh  # 强制重下
  python _temp/gen_area_map.py --check    # 只对账不写盘（CI 口径：表是否与 wago 一致）

口径：
  · AreaID 0 = 大陆/世界图（艾泽拉斯/东部王国/卡利姆多），不是「区域」⇒ 不收。
  · 同一 areaID 出现多行且 UiMapID 不一致时取**首次**出现（wago 行序 = OrderIndex 升序）。
  · 输出按 areaID 升序，一行一项 + 中文图名备注。
"""

import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
TEMP = os.path.join(ROOT, '_temp')
CACHE = os.path.join(TEMP, '_uimap_cache')
OUT = os.path.join(ROOT, 'Core', 'Data', 'Data_AreaMap.lua')

BUILD = '1.60.1.70009'
PROXIES = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
FILES = {
    'UiMapAssignment.csv': 'https://wago.tools/db2/UiMapAssignment/csv?build=%s' % BUILD,
    'UiMap_zhCN.csv': 'https://wago.tools/db2/UiMap/csv?build=%s&locale=zhCN' % BUILD,
}

HEAD = '''local AddonName, ns = ...
ns.AreaMap = {'''


def fetch(fn, url):
    from curl_cffi import requests
    r = requests.get(url, impersonate='chrome110', proxies=PROXIES, timeout=90)
    if r.status_code != 200:
        raise SystemExit('下载 %s 失败：HTTP %d' % (url, r.status_code))
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, fn), 'w', encoding='utf-8', newline='') as f:
        f.write(r.text)
    print('  下载 %s（%d 字节）' % (fn, len(r.content)))


def load(refresh=False):
    for fn, url in FILES.items():
        p = os.path.join(CACHE, fn)
        if refresh or not os.path.exists(p) or os.path.getsize(p) < 200:
            fetch(fn, url)
    rows = list(csv.DictReader(open(os.path.join(CACHE, 'UiMapAssignment.csv'), encoding='utf-8')))
    names = {r['ID']: r['Name_lang']
             for r in csv.DictReader(open(os.path.join(CACHE, 'UiMap_zhCN.csv'), encoding='utf-8'))}
    m = {}
    for r in rows:
        a, u = int(r['AreaID']), int(r['UiMapID'])
        if a == 0:
            continue
        m.setdefault(a, u)
    return m, names


def render(m, names):
    body = []
    for a in sorted(m):
        body.append('    [%d] = %d,' % (a, m[a]))
    return HEAD % {'build': BUILD} + '\n'.join(body) + '\n}\n'


def main():
    refresh = '--refresh' in sys.argv
    check = '--check' in sys.argv
    m, names = load(refresh)
    text = render(m, names)
    if check:
        cur = open(OUT, encoding='utf-8', newline='').read()
        if cur == text:
            print('对账一致：%d 项区域（areaID → uiMapID）' % len(m))
            return 0
        print('!! 与 wago 不一致，需重跑 gen_area_map.py')
        return 1
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    print('写出 %s：%d 项区域' % (os.path.relpath(OUT, ROOT).replace('\\', '/'), len(m)))


if __name__ == '__main__':
    sys.exit(main())
