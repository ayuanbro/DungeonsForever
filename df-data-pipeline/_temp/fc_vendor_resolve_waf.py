# -*- coding: utf-8 -*-
"""商人定位 · WAF 通道驱动（wowhead 全封时的 fc_vendors_resolve 替代执行体）。

2026-10-09 起直连/jina 全被 wowhead WAF 拦（curl 403、r.jina.ai 吃 AWS WAF
挑战页、旧 aws-waf-token 绑浏览器指纹不能给 curl 复用）——唯一活通道是
真 Chromium 过墙（_temp/_waf_fetch.js，10-07 验证过）。

架构：本脚本只做编排与解析，抓页全部委托 _waf_fetch.js（同一浏览器上下文
里逐页 goto，202 挑战自解后存 HTML）。分四段，每段产物落缓存、可断点重跑：
  1. 批量抓搜索页（forever 分支 npcs?filter=name:xxx）→ search/；
  2. 解析候选 NPC ID（复用 fc_vendors_resolve 的同款正则）；
  3. 批量抓 NPC zh 页（+需 wotlk 兜底的补 wotlk 页）→ npc/；
  4. 解析坐标/中文名，合并进 vendor_loc.json / zh.json（口径与
     fc_vendors_resolve.run 完全一致）。

用法：python _temp/fc_vendor_resolve_waf.py [--batch 40]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_vendors_resolve as R  # noqa: E402  复用 parse_mapper_any 等解析件

DATA = os.path.join(HERE, '_fc', 'data')
ZH_PATH = os.path.join(HERE, '_fc', 'i18n', 'zh.json')
OUT = os.path.join(DATA, 'vendor_loc.json')
CACHE = os.path.join(HERE, '_fc', 'cache_wh_vendors_waf')
FETCH_JS = os.path.join(HERE, '_waf_fetch.js')
NODE = 'node'


def sanitize(name):
    return re.sub(r'\W+', '_', name)


def waf_batch(items, outdir, batch=40):
    """items: [(key, url)] → 分批调 _waf_fetch.js，返回成功 key 集合。"""
    os.makedirs(outdir, exist_ok=True)
    done = set()
    for i in range(0, len(items), batch):
        chunk = items[i:i + batch]
        # 已缓存的跳过（>20KB 视为有效）
        todo = [(k, u) for k, u in chunk
                if not os.path.exists(os.path.join(outdir, k + '.html'))
                or os.path.getsize(os.path.join(outdir, k + '.html')) < 20000]
        if not todo:
            done |= {k for k, _ in chunk}
            continue
        print('  [waf] 批次 %d/%d：%d 页' % (i // batch + 1,
                                            (len(items) + batch - 1) // batch, len(todo)))
        argv = [NODE, FETCH_JS, outdir] + ['%s=%s' % (k, u) for k, u in todo]
        r = subprocess.run(argv, capture_output=True, text=True,
                           cwd=HERE,
                           env={**os.environ,
                                'NODE_PATH': 'C:/Users/Administrator/.workbuddy/'
                                             'binaries/node/workspace/node_modules'})
        log = (r.stdout or '') + (r.stderr or '')
        for line in log.splitlines():
            if 'saved' in line or 'FAILED' in line or 'attempt' in line:
                print('    ' + line.strip())
        for k, _ in chunk:
            p = os.path.join(outdir, k + '.html')
            if os.path.exists(p) and os.path.getsize(p) > 20000:
                done.add(k)
    return done


def read_html(outdir, key):
    p = os.path.join(outdir, key + '.html')
    if os.path.exists(p):
        return open(p, encoding='utf-8', errors='replace').read()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int, default=40)
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 个（冒烟）')
    args = ap.parse_args()

    loc = json.load(open(OUT, encoding='utf-8'))
    zh_all = json.load(open(ZH_PATH, encoding='utf-8'))

    # 与 fc_vendors_resolve.run 完全一致的待补清单
    vendors = {}
    for f in os.listdir(DATA):
        if f.startswith('prof_') and f.endswith('.json'):
            d = json.load(open(os.path.join(DATA, f), encoding='utf-8'))
            for coll in ('rows', 'enchants', 'crafted'):
                for r in d.get(coll) or []:
                    src = r.get('source')
                    if not isinstance(src, dict):
                        continue
                    for v in src.get('vendors') or []:
                        if isinstance(v, dict) and (v.get('npc') or v.get('name')):
                            vendors.setdefault(v.get('npc') or v.get('name'), set()).add(v.get('zone'))

    def need_pos(name):
        e = loc.get(name) or {}
        return not (e.get('x') is not None and (e.get('areaID') or e.get('mapID')))

    todo = sorted(k for k in vendors if need_pos(k))
    if args.limit:
        todo = todo[:args.limit]
    print('=== WAF 通道商人解析：%d 个待补 ===' % len(todo))

    # 段 1+2：搜索页 → 候选 NPC ID
    # ★ 通道定稿：forever/npcs?filter= 的 Listview 是纯前端渲染且 filter 参数被无视
    #   （实测 15164 条全量）；/forever/search?q= 服务端内嵌结果 JSON，含 npc=ID 与
    #   url slug（可用 slug==名字 归一核对防同名误配）。
    search_items = [('whsearch_' + sanitize(n),
                     'https://www.wowhead.com/forever/search?q=%s'
                     % urllib.parse.quote(n)) for n in todo]
    got = waf_batch(search_items, os.path.join(CACHE, 'search'), args.batch)

    cands = {}
    for n in todo:
        key = 'whsearch_' + sanitize(n)
        if key not in got:
            continue
        h = read_html(os.path.join(CACHE, 'search'), key) or ''
        slugish = re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
        exact, others, seen = [], [], set()
        for m in re.finditer(r'forever[/\\]+npc=(\d+)[/\\]+([a-z0-9\-]+)', h):
            nid, slug = int(m.group(1)), m.group(2)
            if nid in seen:
                continue
            seen.add(nid)
            (exact if slug == slugish else others).append(nid)
        cands[n] = (exact + others)[:3]

    no_cand = [n for n in todo if not cands.get(n)]
    if no_cand:
        print('  无候选 %d 个：%s…' % (len(no_cand), '、'.join(no_cand[:8])))

    # 段 3a：NPC zh 页（每名最多 3 候选）
    npc_items, npc_key_of = [], {}
    for n, ids in cands.items():
        for nid in ids:
            key = 'npc_%d_zh' % nid
            npc_key_of[key] = nid
            npc_items.append((key, 'https://www.wowhead.com/forever/cn/npc=%d' % nid))
    got_zh = waf_batch(npc_items, os.path.join(CACHE, 'npc'), args.batch)

    # 段 4：解析 + 需要时补 wotlk 页
    zh_extra_items, zh_extra_key = [], {}
    resolve = {}
    for n, ids in cands.items():
        for nid in ids:
            if 'npc_%d_zh' % nid not in got_zh:
                continue
            h = read_html(os.path.join(CACHE, 'npc'), 'npc_%d_zh' % nid)
            t = re.search(r'<title>\s*\[?([^\]\<]+?)\]?\s*[-—]?\s*NPC', h or '')
            zh = t.group(1).strip() if t else None
            if zh:
                zh = zh.strip('[] ').strip()
                if not re.search(r'[\u4e00-\u9fff]', zh):
                    zh = None  # 站点没翻的（如 [Aisarra Nightmeadow]）不污染 zh 链
            pt = R.parse_mapper_any(h)
            if not pt or pt[0] == 1453:
                key = 'npc_%d_wotlk' % nid
                if key not in zh_extra_key:
                    zh_extra_key[key] = nid
                    zh_extra_items.append((key, 'https://www.wowhead.com/wotlk/cn/npc=%d' % nid))
            resolve.setdefault(n, []).append((nid, zh, pt))
    if zh_extra_items:
        got_w = waf_batch(zh_extra_items, os.path.join(CACHE, 'npc'), args.batch)
        for n, entries in resolve.items():
            for i, (nid, zh, pt) in enumerate(entries):
                if (not pt or pt[0] == 1453) and 'npc_%d_wotlk' % nid in got_w:
                    hw = read_html(os.path.join(CACHE, 'npc'), 'npc_%d_wotlk' % nid)
                    ptw = R.parse_mapper_any(hw)
                    if ptw:
                        entries[i] = (nid, zh, ptw)

    # 合并（口径 = fc_vendors_resolve.run）
    done = miss = 0
    for n, entries in resolve.items():
        for nid, zh, pt in entries:
            if not pt:
                continue
            ent = loc.setdefault(n, {})
            ent['id'] = nid
            ent['mapID'], ent['x'], ent['y'] = pt
            if zh:
                ent['zh'] = zh
                if n not in zh_all:
                    zh_all[n] = zh
            done += 1
            break
        else:
            miss += 1
    for n in no_cand:
        miss += 1
    json.dump(loc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1, sort_keys=True)
    json.dump(zh_all, open(ZH_PATH, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1, sort_keys=True)
    print('=== 完成：定位 %d · 未定位 %d（vendor_loc.json / zh.json 已合并）==='
          % (done, miss))


if __name__ == '__main__':
    main()
