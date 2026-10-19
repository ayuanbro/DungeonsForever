# -*- coding: utf-8 -*-
"""探索页 · 第 3 步：书名 → 物品 ID、区域名 → AreaTable ID。

- 物品：wago.tools ItemSparse（Classic 最后一个 build，与 fc_zones 同一套取表纪律）。
  解析不到直接报错退出 —— 宁可流水线红，也不静默塞占位 ID。
- 区域：复用 fc_zones 缓存的 areatable_classic.csv，同名取最小 ID。
输出：_fc/data/explore_resolved.json
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_fc', 'cache')
DATA = os.path.join(HERE, '_fc', 'data')

BOOKS = os.path.join(DATA, 'explore_books.json')
OUT = os.path.join(DATA, 'explore_resolved.json')
ITEMS_CSV = os.path.join(CACHE, 'itemsparse_classic.csv')
AREA_CSV = os.path.join(CACHE, 'areatable_classic.csv')

BUILDS_API = 'https://wago.tools/api/builds'
ITEMS_API = 'https://wago.tools/db2/ItemSparse/csv?build=%s'
CLASSIC_PREFIX = ('1.13.', '1.14.', '1.15.')
PROXY = 'http://127.0.0.1:7897'
RETRY = 3


def die(msg):
    sys.stderr.write('explore_resolve: %s\n' % msg)
    sys.exit(1)


def http_get(url, dst):
    """直连优先，退避重试，失败走本机 Clash 代理（fc_zones 同款）。"""
    last = ''
    for i in range(RETRY):
        cmd = ['curl', '-s', '-m', '300', '-o', dst, '-w', '%{http_code} %{size_download}', url]
        r = subprocess.run(cmd, capture_output=True, text=True)
        parts = (r.stdout or '').split()
        code = parts[0] if parts else '000'
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if code == '200' and size > 100000:
            return size
        last = 'HTTP %s size %d' % (code, size)
        time.sleep(1.0 + i)
    cmd[5:5] = ['-x', PROXY]
    r = subprocess.run(cmd, capture_output=True, text=True)
    parts = (r.stdout or '').split()
    if parts and parts[0] == '200' and len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    if os.path.exists(dst):
        os.remove(dst)
    die('取表失败 %s（%s）' % (url, last))


def norm(s):
    s = re.sub(r'\s+', ' ', (s or ''))
    s = s.replace('\u2019', "'").replace('\u2018', "'")
    s = s.replace('\u2013', '-').replace('\u2014', '-')  # en/em dash → 连字符（游戏用 -）
    return s.strip()


def pick_build():
    r = subprocess.run(['curl', '-s', '-m', '60', BUILDS_API], capture_output=True, text=True)
    builds = sorted(set(re.findall(r'"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"', r.stdout or '')))
    classic = [b for b in builds if b.startswith(CLASSIC_PREFIX)]
    if not classic:
        die('builds 列表里没有 Classic 分支')
    return classic[-1]


def load_items(path):
    """ItemSparse CSV → {规范名: [itemID,...]}。"""
    by = collections.defaultdict(list)
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(io.StringIO(f.read())):
            try:
                iid = int(row['ID'])
            except (KeyError, TypeError, ValueError):
                continue
            nm = norm(row.get('Display_lang') or '')
            if nm:
                by[nm].append(iid)
    return by


def load_areas(path):
    by = collections.defaultdict(list)
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(io.StringIO(f.read())):
            try:
                aid = int(row['ID'])
            except (KeyError, TypeError, ValueError):
                continue
            for col in ('ZoneName', 'AreaName_lang'):
                nm = (row.get(col) or '').strip()
                if nm:
                    by[nm].append(aid)
    return {k: min(v) for k, v in by.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true', help='只用缓存表')
    args = ap.parse_args()

    books = json.load(open(BOOKS, encoding='utf-8'))
    print('待解析 %d 本' % len(books))

    # ── 物品表 ──
    if not os.path.exists(ITEMS_CSV) or not args.offline:
        build = pick_build()
        print('ItemSparse  build=%s 下载中（约 20-40MB）...' % build)
        size = http_get(ITEMS_API % build, ITEMS_CSV)
        print('  %d bytes' % size)
    if not os.path.exists(ITEMS_CSV):
        die('缺缓存 %s（--offline 需先联网跑一次）' % ITEMS_CSV)
    items = load_items(ITEMS_CSV)
    print('ItemSparse 名称 %d 个' % len(items))

    if not os.path.exists(AREA_CSV):
        die('缺 %s —— 先跑 fc_zones.py' % AREA_CSV)
    areas = load_areas(AREA_CSV)

    out, miss_i, miss_z = [], [], []
    for b in books:
        zone = re.sub(r'\s*\(\s*\d+\s*-\s*\d+\s*\)\s*$', '', b['zone']).strip()
        rec = dict(b)
        rec['zone'] = zone
        ids = items.get(norm(b['name']))
        if not ids:
            miss_i.append(b['name'])
        else:
            if len(ids) > 1:
                print('  [重名物品] %-46s %s → 取最小 %d'
                      % (b['name'], sorted(ids), min(ids)))
            rec['item_id'] = min(ids)
        aid = areas.get(zone)
        if not aid:
            miss_z.append(zone)
        else:
            rec['area_id'] = aid
        for a in rec.get('alt', []):
            a['area_id'] = areas.get(re.sub(r'\s*\(\s*\d+\s*-\s*\d+\s*\)\s*$', '', a['zone']).strip())
        out.append(rec)

    if miss_i:
        die('以下书名在 ItemSparse 里查不到（检查引号/标点差异）：\n  ' + '\n  '.join(miss_i))
    if miss_z:
        die('以下区域在 AreaTable 里查不到：\n  ' + '\n  '.join(miss_z))
    n_alt_bad = [a['zone'] for b in out for a in b.get('alt', []) if not a.get('area_id')]
    if n_alt_bad:
        die('多位置区域解析失败：%s' % n_alt_bad)

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('解析完成 %d 条 → %s' % (len(out), os.path.relpath(OUT, os.path.dirname(HERE))))
    for b in out[:5]:
        print('  #%d %-48s area=%s (%s)' % (b['item_id'], b['name'], b['area_id'], b['zone']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
