# -*- coding: utf-8 -*-
"""专业页数据 · 补充步：zh-cn 页 → 区域中文名对照（zone_zh.json）。

为什么需要：配方来源里的 drops[]/vendors[] 带英文区域名（"Teldrassil"），
而 wago 的 AreaTable CSV 只有英文名、客户端的 C_Map.GetAreaInfo 需要 areaID ——
但 areatable 覆盖不了 4 个无限服自定义区域（Riverglades / Zephras Isle 等）。
站点自己的 /zh-cn/ 页面把**全部**区域名翻成了中文（NPC 名仍是英文），于是：

    对齐键 = (spell, id)  →  逐条 zip drops/vendors → 英文区域名 ↔ 中文区域名

产物 `_fc/data/zone_zh.json`：{ "Teldrassil": "泰达希尔", ... }
fc_gen 落盘时按它套中文，未命中回落英文原文（与 fc_i18n 同一口径，不阻塞更新）。

用法：
    python fc_zh_sync.py            # 联网抓 zh-cn 13 页（有缓存跳过）→ 生成
    python fc_zh_sync.py --offline  # 只用缓存重放
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_parse  # noqa: E402  复用 RSC 解码

BASE = 'https://foreverchanges.pro'
CACHE = os.path.join(HERE, '_fc', 'cache_zh')
OUT = os.path.join(HERE, '_fc', 'data', 'zone_zh.json')
SLEEP = 0.8

# 与 fc_fetch 抓的主页专业清单一致（13 个：12 生产 + 露营）
SLUGS = ['alchemy', 'blacksmithing', 'enchanting', 'engineering', 'leatherworking',
         'tailoring', 'mining', 'herbalism', 'skinning', 'cooking', 'fishing',
         'first-aid', 'camping']

# 站点 zh-cn 自己也没翻的（2026-10-08 核对：AQ 相关行两侧同文）。手工补齐。
MANUAL_ZONE = {
    "Ahn'Qiraj Temple": '安其拉神殿',
}


def fetch(url, dst):
    if os.path.exists(dst) and os.path.getsize(dst) > 20000:
        return 'cached'
    for i in range(3):
        r = subprocess.run(['curl', '-s', '-m', '60', '-o', dst, '-w', '%{http_code} %{size_download}', url],
                           capture_output=True, text=True)
        parts = (r.stdout or '').strip().split()
        if parts and parts[0] == '200' and len(parts) > 1 and int(parts[1]) > 20000:
            return 'ok'
        time.sleep(1.0 + i)
    raise RuntimeError('fetch fail %s -> %s' % (url, (r.stdout or '').strip()))


def collect_sources(html_path):
    """一个页面 → {(spell,id): source_dict}。重复键（同名配方多行）保留首见。"""
    out = {}
    for node in _walk(fc_parse.rsc_rows(html_path)):
        if not isinstance(node, dict):
            continue
        src = node.get('source')
        if not isinstance(src, dict):
            continue
        key = (node.get('spell'), node.get('id'))
        if key not in out:
            out[key] = src
    return out


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    mapping = {}
    stats = {'rows': 0, 'zone_hit': 0}
    for slug in SLUGS:
        dst = os.path.join(CACHE, 'prof_%s.html' % slug)
        if not args.offline:
            fetch(BASE + '/zh-cn/professions/' + slug, dst)
            time.sleep(SLEEP)
        zh_srcs = collect_sources(dst)
        en_path = os.path.join(HERE, '_fc', 'cache', 'professions_%s' % slug)
        # fc_fetch 的缓存命名与 slug_of() 保持一致
        if not os.path.exists(en_path):
            cands = [p for p in os.listdir(os.path.join(HERE, '_fc', 'cache'))
                     if slug in p and p.endswith('.html')]
            en_path = os.path.join(HERE, '_fc', 'cache', cands[0]) if cands else None
        if not en_path:
            print('  ! 无英文缓存，跳过 %s' % slug)
            continue
        en_srcs = collect_sources(en_path)
        for key, esrc in en_srcs.items():
            zsrc = zh_srcs.get(key)
            if not zsrc:
                continue
            for field in ('drops', 'vendors'):
                elist, zlist = esrc.get(field) or [], zsrc.get(field) or []
                if not isinstance(zlist, list):
                    continue
                # ★ zh 页的 drops/vendors 列表比 en 页全（en 砍掉了部分阵营项），
                #   按下标 zip 会错位；但 **NPC 名两侧都是英文**（站点没翻 NPC 名），
                #   用它做条目级对齐键是稳的。同名 NPC 取首见 zone。
                zzone = {}
                for z in zlist:
                    if isinstance(z, dict) and z.get('npc'):
                        zzone.setdefault(z['npc'], z.get('zone'))
                for e in elist:
                    if not isinstance(e, dict) or not e.get('zone') or not e.get('npc'):
                        continue
                    zn = zzone.get(e['npc'])
                    if isinstance(zn, str) and re.search(r'[\u4e00-\u9fff]', zn):
                        stats['zone_hit'] += 1
                        mapping[e['zone']] = zn
            stats['rows'] += 1
        print('  %s: en %d 行 · zh %d 行' % (slug, len(en_srcs), len(zh_srcs)))

    json.dump(mapping, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1, sort_keys=True)
    print('=== zone_zh.json：%d 条对照（%d 次行级命中）===' % (len(mapping), stats['zone_hit']))


if __name__ == '__main__':
    main()
