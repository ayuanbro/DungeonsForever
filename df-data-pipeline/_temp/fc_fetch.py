# -*- coding: utf-8 -*-
"""专业页数据 · 第 1 步：抓取 14 个页面到本地缓存。

为什么单独一步：抓取是唯一依赖网络、且最慢的一环。缓存下来之后，
解析 / 生成 / 断言全部可离线重放（`--offline`），回归可重复、不受站点抖动影响。

站点是 Next.js App Router：业务数据以 RSC 载荷内嵌在页面里，
本步只负责把原始 HTML 存下来，解析交给 fc_parse.py。

用法：
    python fc_fetch.py              # 抓主页 → 拿到专业清单 → 抓各专业子页
    python fc_fetch.py --offline    # 只列缓存清单，不联网
    python fc_fetch.py --force      # 无视缓存强制重抓
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from fc_pipeline_common import configured_path

BASE = 'https://foreverchanges.pro'
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = configured_path('DF_PIPELINE_CACHE_DIR', os.path.join(HERE, '_fc', 'cache'))

# 抓取纪律：站点是个人自建站，不并发、不猛拉。
# 实测单页 100~800KB，14 页合计约 3.9MB，全程 < 30s。
SLEEP = 0.8
RETRY = 3


def die(msg):
    sys.stderr.write('fc_fetch: %s\n' % msg)
    sys.exit(1)


def slug_of(path):
    """'/professions/alchemy' → 'professions_alchemy'；'/professions' → 'professions'"""
    return path.strip('/').replace('/', '_') or 'root'


def fetch(url, dst, force=False):
    if os.path.exists(dst) and not force and os.path.getsize(dst) > 20000:
        return 'cached'
    last = ''
    for i in range(RETRY):
        r = subprocess.run(
            ['curl', '-s', '-m', '60', '-o', dst, '-w', '%{http_code} %{size_download}',
             url],
            capture_output=True, text=True)
        out = (r.stdout or '').strip()
        parts = out.split()
        code = parts[0] if parts else '000'
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if code == '200' and size > 20000:
            return 'ok %d bytes' % size
        last = 'HTTP %s size %d' % (code, size)
        time.sleep(1.0 + i)
    # 抓失败时不要留下半截文件（会被后续步骤当成有效缓存）
    if os.path.exists(dst):
        os.remove(dst)
    die('抓取失败 %s（%s）' % (url, last))


def page_slugs(html_path):
    """从主页 RSC 里抠出专业 slug 列表（顺序即站点展示顺序）。"""
    h = open(html_path, encoding='utf-8', errors='replace').read()
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', h, flags=re.S)
    payload = ''
    for c in chunks:
        try:
            payload += json.loads(c)
        except Exception:
            payload += c
    slugs = re.findall(r'\\"slug\\":\\"([a-z0-9\-]+)\\"', payload)
    if not slugs:
        # 兼容未转义形态
        slugs = re.findall(r'"slug":"([a-z0-9\-]+)"', payload)
    if not slugs:
        # 兼容 2026-10 改版：RSC 载荷不再带 "slug" 键，从导航 tile 的 href 抠
        # （顺序即页面渲染顺序；professions 页面链接只会指向专业子页，无噪声）
        slugs = re.findall(r'href="/professions/([a-z0-9\-]+)"', h)
        if not slugs:
            slugs = re.findall(r'\\"href\\":\\"\\/professions\\/([a-z0-9\-]+)\\"', payload)
    seen, out = set(), []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true', help='不联网，只列缓存清单')
    ap.add_argument('--force', action='store_true', help='无视缓存强制重抓')
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    main_path = os.path.join(CACHE, 'professions.html')

    if args.offline:
        if not os.path.exists(main_path):
            die('离线模式但缓存为空：%s' % CACHE)
        slugs = page_slugs(main_path)
        print('缓存模式：主页 + %d 个专业页' % len(slugs))
        for s in slugs:
            p = os.path.join(CACHE, 'professions_%s.html' % s)
            print('  %-18s %s' % (s, '有' if os.path.exists(p) else '★缺失'))
        return 0

    print('抓取主页 ...')
    print('  %s' % fetch(BASE + '/professions', main_path, args.force))
    slugs = page_slugs(main_path)
    if len(slugs) < 10:
        die('主页只解析出 %d 个 slug，疑似站点改版：%s' % (len(slugs), slugs))
    print('  专业清单 %d 个：%s' % (len(slugs), ', '.join(slugs)))

    for s in slugs:
        dst = os.path.join(CACHE, 'professions_%s.html' % s)
        print('  %-18s %s' % (s, fetch(BASE + '/professions/' + s, dst, args.force)))
        time.sleep(SLEEP)

    # 记录抓取时间戳：变更报告里要能看到「上次抓取」基准
    meta = {'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'slugs': slugs}
    with open(os.path.join(CACHE, '_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print('已缓存 %d 个页面 → %s' % (len(slugs) + 1, CACHE))
    return 0


if __name__ == '__main__':
    sys.exit(main())
