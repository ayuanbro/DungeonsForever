# -*- coding: utf-8 -*-
"""专业页数据 · 第 2.5 步：区域名 → AreaTable ID（英文区域名不再进产物）。

为什么要有这一步：采集页的「分布 / 可钓区域」要显示**中文区域名**，而中文名只从
客户端取（`C_Map.GetAreaInfo(areaID)`）—— 数据表里就该只存区域 ID，与「物品名只存
ID、名字运行时问客户端」是同一条口径。站点给的 JSON 里只有英文区域名，所以在这里
做一次性解析，把结果落成 `_fc/data/zone_ids.json`。

源：wago.tools 的 AreaTable（取 Classic 分支**最后一个 build**）。CSV 缓存到
`_fc/cache/areatable_classic.csv`，之后 `--offline` 可离线重放。

★ 多解取**最小 ID**：同名条目都是 SoD / 自定义副本（AshenvaleInstance、DuskwoodNightmareGrove、
  Westfall cont=36 之类），与我们要的经典区域**同名**，所以取最小既能稳定命中经典那条，
  也保证 `GetAreaInfo` 回什么名字都是对的（同名项不会显示错字）。
★ 未命中直接报错退出：宁可让流水线红，也不要静默把英文名漏进产物。

用法：
    python fc_zones.py            联网取表（有缓存则直接用）→ 解析 → 落 zone_ids.json
    python fc_zones.py --offline  只用缓存，不联网
"""
import argparse
import csv
import collections
import io
import json
import os
import re
import subprocess
import sys
import time
from fc_pipeline_common import configured_path

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = configured_path('DF_PIPELINE_CACHE_DIR', os.path.join(HERE, '_fc', 'cache'))
DATA = configured_path('DF_PIPELINE_DATA_DIR', os.path.join(HERE, '_fc', 'data'))

CSV_NAME = 'areatable_classic.csv'
BUILDS_API = 'https://wago.tools/api/builds'
CSV_API = 'https://wago.tools/db2/AreaTable/csv?build=%s'
# Classic 分支（1.13/1.14/1.15）—— 泰坦端是 3.80.2，但本表只服务无限服（ns.IsForever）
CLASSIC_PREFIX = ('1.13.', '1.14.', '1.15.')
PROXY = os.environ.get('DF_PIPELINE_PROXY', 'http://127.0.0.1:7897')

# 抓取纪律：站点偶尔会抖，退避重试；失败不留半截文件（会被当成有效缓存）
RETRY = 3


def die(msg):
    sys.stderr.write('fc_zones: %s\n' % msg)
    sys.exit(1)


def http_get(url, dst=None, tries=RETRY):
    """直连优先，失败退避重试，再失败走本机 Clash 代理（7897）。

    直连 wago.tools 实测 200 / <1s，所以常规路径不碰代理；代理只当兜底，
    免得「代理没开」变成硬依赖。
    """
    last = ''
    for i in range(tries):
        cmd = ['curl', '-s', '-m', '90', '-w', '%{http_code} %{size_download}', url]
        if dst:
            cmd[1:1] = ['-o', dst]
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = (r.stdout or '').strip()
        parts = out.split()
        code = parts[0] if parts else '000'
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if code == '200' and size > 1000:
            return size
        last = 'HTTP %s size %d' % (code, size)
        time.sleep(1.0 + i)
    # 兜底：Clash Verge 系统代理（本机 127.0.0.1:7897）
    cmd = ['curl', '-s', '-m', '90', '-w', '%{http_code} %{size_download}', '-x', PROXY, url]
    if dst:
        cmd[1:1] = ['-o', dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or '').strip()
    parts = out.split()
    if parts and parts[0] == '200':
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    if dst and os.path.exists(dst):
        os.remove(dst)
    die('取表失败 %s（%s）' % (url, last))


def pick_build():
    r = subprocess.run(['curl', '-s', '-m', '60', BUILDS_API], capture_output=True, text=True)
    txt = r.stdout or ''
    builds = sorted(set(re.findall(r'"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"', txt)))
    classic = [b for b in builds if b.startswith(CLASSIC_PREFIX)]
    if not classic:
        die('builds 列表里没有 Classic 分支（%d 个 build）' % len(builds))
    return classic[-1]


def load_name_index(path):
    """CSV → {名字: 最小 ID}（ZoneName 与 AreaName_lang 两列都算）。"""
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


def wanted_zones():
    """index.json 里出现过的全部区域名（采矿/采药/剥皮/钓鱼）。"""
    p = os.path.join(DATA, 'index.json')
    if not os.path.exists(p):
        die('缺 %s —— 先跑 fc_parse.py' % p)
    d = json.load(open(p, encoding='utf-8'))
    g = d.get('gathering') or {}
    out = set()
    for k in ('mining', 'herbalism', 'skinning'):
        for it in g.get(k) or []:
            for z in it.get('zones') or []:
                if z and z[0]:
                    out.add(z[0])
    for it in g.get('fishing') or []:
        if it.get('zone'):
            out.add(it['zone'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true', help='只用缓存表，不联网')
    args = ap.parse_args()

    csv_path = os.path.join(CACHE, CSV_NAME)
    if args.offline:
        if not os.path.exists(csv_path):
            die('--offline 但缺缓存 %s' % csv_path)
        build = 'cached'
    else:
        build = pick_build()
        http_get(CSV_API % build, dst=csv_path)
    print('AreaTable  build=%s  %s (%.1f KB)'
          % (build, os.path.basename(csv_path), os.path.getsize(csv_path) / 1024.0))

    idx = load_name_index(csv_path)
    print('表内可用区域名 %d 个' % len(idx))

    want = wanted_zones()
    miss = sorted(z for z in want if z not in idx)
    if miss:
        die('以下区域名在 AreaTable 里查不到，不能静默漏成英文：\n  ' + '\n  '.join(miss))

    out = {z: idx[z] for z in sorted(want)}
    dst = os.path.join(DATA, 'zone_ids.json')
    old = None
    if os.path.exists(dst):
        old = json.load(open(dst, encoding='utf-8'))
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    same = (old == out)
    print('区域名 → ID：%d 条%s → %s'
          % (len(out), '（与上次一致）' if same else '（有变化）',
             os.path.relpath(dst, os.path.dirname(HERE))))
    for z in sorted(out)[:5]:
        print('    %-22s -> %d' % (z, out[z]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
