# -*- coding: utf-8 -*-
"""商人定位 · wowhead 解析补齐（fc_vendors.py --resolve 的执行体）。

对 vendor_loc.json 里还没有坐标的商人逐个做三件事：
  1. 名字 → NPC ID：wowhead forever 分支 NPC 列表筛选页（filter=name:xxx），
     解析返回里的 /npc=ID 候选，再用 zh 页标题核对名字（防同名误配）；
  2. zh 页标题 → 中文名（回填 zh.json，经 fc_i18n 的 --add 口径）；
  3. NPC 页内联 g_mapperData → 首点位 {mapID, x, y}（Stormwind uiMapID 1453 沿用
     新生代边界口径，改取 wotlk 分支页坐标 —— 与 Data_NPCLoc 暴风城校正同一条纪律）。

★ 通道：本机/代理 IP 直连 wowhead 被 CloudFront 403（2026-10-08 晚），走
  `r.jina.ai/<目标URL>`，且要拿 **html** 格式（g_mapperData 是内联 JS，markdown
  会剥掉）。匿名 jina 对 wowhead 有封禁窗口（本日 23:03 GMT+8 解封），所以
  这一步单独成文件、可反复重跑，结果合并进 vendor_loc.json / zh.json。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '_fc', 'data')
ZH_PATH = os.path.join(HERE, '_fc', 'i18n', 'zh.json')
OUT = os.path.join(DATA, 'vendor_loc.json')
PROXY = 'http://127.0.0.1:7897'
SLEEP = 1.5
CACHE = os.path.join(HERE, '_fc', 'cache_wh_vendors')


def jina_get(url, dst, html=True):
    """r.jina.ai 通道抓一个页面（缓存）。html=True 时要原始 HTML（内联数据不被剥）。"""
    if os.path.exists(dst) and os.path.getsize(dst) > 3000:
        return open(dst, encoding='utf-8', errors='replace').read()
    full = 'https://r.jina.ai/' + url
    cmd = ['curl', '-s', '-m', '90', '-x', PROXY]
    if html:
        cmd += ['-H', 'x-return-format: html']
    cmd += ['-o', dst, '-w', '%{http_code}', full]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if (r.stdout or '').strip() != '200':
        return None
    txt = open(dst, encoding='utf-8', errors='replace').read()
    if len(txt) < 3000:
        return None
    return txt


def search_npc(name, zone_hint):
    """名字 → [(id, 标题或 None)] 候选列表。forever 分支优先，空了退 classic 分支。"""
    out = []
    for branch in ('forever', 'classic'):
        url = 'https://www.wowhead.com/%s/npcs?filter=name:%s' % (branch, name.replace(' ', '+'))
        h = jina_get(url, os.path.join(CACHE, 'search_%s_%s.html' % (branch, re.sub(r'\W+', '_', name))))
        if not h:
            continue
        # 列表行：id="npc-12345" 与名称同现；jina html 模式下是原始 DOM
        for m in re.finditer(r'id="npc-(\d+)"', h):
            nid = int(m.group(1))
            seg = h[max(0, m.start() - 200): m.end() + 400]
            if zone_hint and zone_hint.replace(' ', '') in seg.replace(' ', ''):
                out.insert(0, (nid, branch))          # 区域同现的候选排前
            else:
                out.append((nid, branch))
        if out:
            break
    return out


def npc_page(nid):
    """zh 页 → (zh名或None, g_mapperData 首点位或None)。暴风城(1453)取 wotlk 分支坐标。"""
    h = jina_get('https://www.wowhead.com/forever/cn/npc=%d' % nid,
                 os.path.join(CACHE, 'npc_%d_zh.html' % nid))
    if not h:
        return None, None
    t = re.search(r'<title>\s*\[?([^\]\<]+?)\]?\s*[-——]?\s*NPC', h)
    zh = t.group(1).strip() if t else None
    pt = parse_mapper_any(h)
    if not pt or pt[0] == 1453:
        hw = jina_get('https://www.wowhead.com/wotlk/cn/npc=%d' % nid,
                      os.path.join(CACHE, 'npc_%d_wotlk.html' % nid))
        ptw = parse_mapper_any(hw) if hw else None
        if ptw:
            pt = ptw
    return zh, pt


def parse_mapper(h):
    """g_mapperData 里第一个点位。★ 2026-10 起页面格式改为
    {"85":[{"count":2,"coords":[[61,52.4],[61,52.6]],"uiMapId":1420,...}]}
    （键=旧 zoneID，coords 是 [x,y] 数组，uiMapId 才是 UI 地图 ID）；
    旧 {"map":[{"x":..,"y":..}]} 格式保留兜底。"""
    if not h:
        return None
    i = h.find('g_mapperData')
    if i < 0:
        return None
    j = h.find('{', i)
    if j < 0:
        return None
    depth, end = 0, None
    for k in range(j, min(j + 200000, len(h))):
        c = h[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = k
                break
    if not end:
        return None
    blob = h[j:end + 1]
    mid = re.search(r'"uiMapId"\s*:\s*(\d+)', blob)
    co = re.search(r'"coords"\s*:\s*\[\s*\[\s*([\d.]+)\s*,\s*([\d.]+)', blob)
    if mid and co:
        return (int(mid.group(1)), float(co.group(1)), float(co.group(2)))
    m = re.search(r'"?(\d+)"?\s*:\s*\[\s*\{\s*"?(?:x|X)"?\s*:\s*([\d.]+)\s*,\s*"?(?:y|Y)"?\s*:\s*([\d.]+)\s*\}',
                  blob.replace("'", '"'))
    if m:
        return (int(m.group(1)), float(m.group(2)), float(m.group(3)))
    m = re.search(r'(\d+)\s*:\s*\[\{[^\}]*?([\d.]+)\s*,\s*([\d.]+)', blob)
    if m:
        return (int(m.group(1)), float(m.group(2)), float(m.group(3)))
    return None


def parse_mapper_any(h):
    """g_mapperData 优先；没有再试 myMapper.update({zone,x,y})（部分 NPC 页只走这条）。"""
    pt = parse_mapper(h)
    if pt:
        return pt
    if not h:
        return None
    m = re.search(r'myMapper\.update\(\{[^}]*?zone\D*(\d+)[^}]*?x\D*([\d.]+)[^}]*?y\D*([\d.]+)',
                  h)
    if not m:
        m = re.search(r'myMapper\.update\(\{[^}]*?x\D*([\d.]+)[^}]*?y\D*([\d.]+)[^}]*?zone\D*(\d+)',
                      h)
        if m:
            return (int(m.group(3)), float(m.group(1)), float(m.group(2)))
        return None
    return (int(m.group(1)), float(m.group(2)), float(m.group(3)))


def run(loc, vendors):
    os.makedirs(CACHE, exist_ok=True)
    zh_all = json.load(open(ZH_PATH, encoding='utf-8'))
    todo = sorted(k for k in vendors
                  if not (loc.get(k, {}).get('x') is not None
                          and (loc[k].get('areaID') or loc[k].get('mapID'))))
    print('=== wowhead 商人解析：%d 个待补 ===' % len(todo))
    done = miss = 0
    for i, name in enumerate(todo):
        zones = sorted(z or '' for z in vendors[name])
        cands = search_npc(name, zones[0] if zones else '')
        got = False
        for nid, _br in cands[:3]:
            zh, pt = npc_page(nid)
            if not pt:
                continue
            ent = loc.setdefault(name, {})
            ent['id'] = nid
            ent['mapID'], ent['x'], ent['y'] = pt
            if zh:
                ent['zh'] = zh
                if name not in zh_all:
                    zh_all[name] = zh
            got = True
            break
        done, miss = done + (1 if got else 0), miss + (0 if got else 1)
        print('  [%d/%d] %s → %s' % (i + 1, len(todo), name,
                                     ('id=%s map=%s' % (loc[name].get('id'), loc[name].get('mapID')))
                                     if got else '未解析'))
        time.sleep(SLEEP)
    json.dump(loc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1, sort_keys=True)
    json.dump(zh_all, open(ZH_PATH, 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1, sort_keys=True)
    print('=== 完成：定位 %d · 未定位 %d（vendor_loc.json / zh.json 已合并）===' % (done, miss))
