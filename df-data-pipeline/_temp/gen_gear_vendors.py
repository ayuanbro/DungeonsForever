# -*- coding: utf-8 -*-
# 生成 Core/Data/Data_GearVendors.lua（装备库 · 商人定位表）
# 数据源：wowhead Forever 库逐件 Sold by（NPC id/名/区域/阵营）+ QuestieDB 刷点补坐标
# 抓取：QQ浏览器本体开 CDP 调试口，playwright connect_over_cdp 附加（真指纹过 WAF）
# 本地缓存：_temp/_gearvend/{id}.html（>20KB 视为有效，--refetch 强制重下）
# 产物：
#   ns.GearVendors[id]      = { {npcID, 区域AreaID, "a"|"h"|nil, 商人名}, ... }
#   ns.GearVendorSpawns[npcID] = { {区域AreaID, 图uiMapID, x, y}, ... }（同 NPC 多区域 = 多行）
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, '_gearvend')
PROXY = 'http://127.0.0.1:7897'
URL = 'https://www.wowhead.com/forever/item={id}'
QB = r'C:/Program Files (x86)/Tencent/QQBrowser/QQBrowser.exe'
CDP_BASE_PORT = 9222
WORKERS = 2
PAGE_DELAY = 4.0


def vendor_item_ids():
    gd = open(os.path.join(ROOT, 'Core', 'Data', 'Data_Gear.lua'),
              encoding='utf-8').read()
    ids = [int(x) for x in re.findall(r'\[(\d+)\]="商人', gd)]
    return sorted(set(ids))


def cache_path(item_id):
    return os.path.join(CACHE, '%d.html' % item_id)


def is_ban(cur):
    return ('could not be satisfied' in cur
            or 'Static CDN Error' in cur)


def cdp_up(port):
    try:
        urllib.request.urlopen(
            'http://127.0.0.1:%d/json/version' % port, timeout=2)
        return True
    except Exception:
        return False


def worker(items_q, out_q, port, profile):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        state = {'br': None, 'pg': None, 'proc': None}

        def ensure():
            if state['br'] is not None and state['br'].is_connected():
                return True
            own = not cdp_up(port)
            if own:
                state['proc'] = subprocess.Popen([
                    QB, '--remote-debugging-port=%d' % port,
                    '--user-data-dir=' + profile,
                    '--no-first-run', '--no-default-browser-check',
                    '--window-position=3200,0', 'about:blank'])
                for _ in range(60):
                    if cdp_up(port):
                        break
                    time.sleep(1)
                if not cdp_up(port):
                    return False
            try:
                state['br'] = p.chromium.connect_over_cdp(
                    'http://127.0.0.1:%d' % port)
                ctx = state['br'].contexts[0]
                pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                pg.goto('about:blank', timeout=15000)
                pg.route('**/*', lambda route: route.abort()
                         if route.request.resource_type in
                         ('image', 'font', 'media') else route.continue_())
                state['pg'] = pg
                return True
            except Exception:
                return False

        ensure()
        cooldowns = 0
        wid = port - CDP_BASE_PORT
        while True:
            try:
                iid = items_q.get_nowait()
            except queue.Empty:
                break
            dst = cache_path(iid)
            reuse = (os.path.exists(dst) and os.path.getsize(dst) > 20000
                     and 'Static CDN Error' not in open(
                         dst, encoding='utf-8', errors='ignore').read())
            if reuse and '--empty' in sys.argv:
                ch = open(dst, encoding='utf-8', errors='ignore').read()
                reuse = not ('tab-sold-by' in ch
                             and not parse_sold_by(ch))
            if reuse:
                out_q.put((iid, open(dst, encoding='utf-8',
                                     errors='ignore').read(), 'cached'))
                continue
            html, last = None, ''
            gave_up = False
            while not gave_up:
                if not ensure():
                    last = 'cdp attach fail'
                    time.sleep(5)
                    continue
                try:
                    state['pg'].goto(URL.format(id=iid),
                                     wait_until='domcontentloaded',
                                     timeout=45000)
                    state['pg'].wait_for_timeout(3500)
                    try:
                        state['pg'].evaluate(
                            "var a=document.getElementById('tab-sold-by');"
                            "if(a){a.click();}")
                        state['pg'].wait_for_timeout(1200)
                    except Exception:
                        pass
                    cur = state['pg'].content()
                    if is_ban(cur):
                        cooldowns += 1
                        print('  [w%d] 封禁冷却 #%d，睡 300s'
                              % (wid, cooldowns), flush=True)
                        time.sleep(300)
                        continue
                    if len(cur) <= 20000 or 'gokuProps' in cur:
                        state['pg'].wait_for_timeout(5000)
                        cur = state['pg'].content()
                    if len(cur) > 20000 and 'gokuProps' not in cur \
                            and not is_ban(cur):
                        html = cur
                        open(dst, 'w', encoding='utf-8').write(cur)
                        break
                    last = 'waf len=%d' % len(cur)
                except Exception as e:
                    last = str(e)[:120]
                    try:
                        state['br'].close()
                    except Exception:
                        pass
                    state['br'] = None
                    if state['proc'] is not None:
                        try:
                            state['proc'].kill()
                        except Exception:
                            pass
                        state['proc'] = None
                if cooldowns > 60:
                    gave_up = True
                time.sleep(2)
            out_q.put((iid, html, last))
            time.sleep(PAGE_DELAY)
        try:
            state['br'].close()
        except Exception:
            pass
        if state['proc'] is not None:
            time.sleep(2)
            try:
                state['proc'].kill()
            except Exception:
                pass


ROW_RE = re.compile(r'<tr class="listview-row">(.*?)</tr>', re.S)
NPC_RE = re.compile(r'npc=(\d+)/[a-z0-9-]*"[^>]*data-wowhead="map">([^<]*)</a>')
ZONE_RE = re.compile(r'zone=(\d+)/[a-z0-9-]*"[^>]*>([^<]*)</a>')
SIDE_RE = re.compile(r'<span class="q2">([AH])</span>')


def parse_sold_by(html):
    i = html.find('tab-sold-by')
    if i < 0:
        return []
    seg = html[i:i + 120000]
    rows = []
    for m in ROW_RE.finditer(seg):
        row = m.group(1)
        nm = NPC_RE.search(row)
        if not nm:
            continue
        zn = ZONE_RE.search(row)
        sd = SIDE_RE.search(row)
        rows.append({
            'npc': int(nm.group(1)),
            'name': nm.group(2).strip(),
            'zone': int(zn.group(1)) if zn else None,
            'side': sd.group(1).lower() if sd else None,
        })
    return rows


def load_area_map():
    d = open(os.path.join(ROOT, 'Core', 'Data', 'Data_AreaMap.lua'),
             encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'\[(-?\d+)\]\s*=\s*(\d+)', d):
        out[int(m.group(1))] = int(m.group(2))
    return out


def nether_zh(nid):
    for _ in range(3):
        r = subprocess.run(
            ['curl', '-s', '-m', '20', '-x', PROXY,
             'https://nether.wowhead.com/forever/tooltip/npc/%d?locale=zhCN'
             % nid],
            capture_output=True, text=True)
        try:
            zh = (json.loads(r.stdout).get('name') or '').strip()
            if zh:
                return zh
        except Exception:
            pass
        time.sleep(1)
    return ''


def main():
    qj = json.load(open(os.path.join(HERE, 'questie', 'questie_forever.json'),
                        encoding='utf-8'))
    spawns = qj.get('npc_spawns') or {}
    area_map = load_area_map()

    ids = vendor_item_ids()
    print('商人来源装备 %d 件' % len(ids), flush=True)
    os.makedirs(CACHE, exist_ok=True)

    refetch = '--refetch' in sys.argv
    items_q = queue.Queue()
    for iid in ids:
        items_q.put(iid)
    out_q = queue.Queue()
    threads = []
    for i in range(WORKERS):
        prof = os.path.join(HERE, '_qqb_profile%d' % i)
        threads.append(threading.Thread(
            target=worker, daemon=True,
            args=(items_q, out_q, CDP_BASE_PORT + i, prof)))
    for i, t in enumerate(threads):
        t.start()
        if i < len(threads) - 1:
            time.sleep(25)
    n = 0
    pages = {}
    while n < len(ids):
        iid, html, how = out_q.get()
        n += 1
        pages[iid] = (html or '')
        if n % 50 == 0 or n == len(ids):
            print('  %d/%d (%s)' % (n, len(ids), how), flush=True)

    vendors = {}
    npc_used = set()
    no_data = []
    for iid in ids:
        html = pages.get(iid) or ''
        rows = parse_sold_by(html)
        if not rows:
            no_data.append(iid)
        for r in rows:
            vendors.setdefault(iid, []).append(
                (r['npc'], r['zone'], r['side'], r['name']))
            npc_used.add(r['npc'])

    spawn_rows = {}
    no_spawn = []
    for nid in sorted(npc_used):
        zmap = spawns.get(str(nid)) or {}
        rows2 = []
        for zs, xy in zmap.items():
            aid = int(zs)
            try:
                x, y = float(xy[0]), float(xy[1])
            except Exception:
                continue
            rows2.append((aid, area_map.get(aid), round(x, 1), round(y, 1)))
        if not rows2:
            no_spawn.append(nid)
        spawn_rows[nid] = rows2

    print('nether 中文名补全 %d 个 NPC…' % len(npc_used), flush=True)
    name_zh = {}
    for nid in sorted(npc_used):
        zh = nether_zh(nid)
        if zh:
            name_zh[nid] = zh
        time.sleep(0.25)
    print('  命中 %d/%d' % (len(name_zh), len(npc_used)), flush=True)

    lit = lambda s: '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

    lines = []
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('')
    lines.append('local _, ns = ...')
    lines.append('')
    lines.append('ns.GearVendors = {')
    for iid in sorted(vendors):
        parts = []
        for nid, zone, side, name in vendors[iid]:
            parts.append('{ %d, %s, %s, %s, %s }' % (
                nid,
                zone if zone else 'nil',
                lit(side) if side else 'nil',
                lit(name),
                lit(name_zh[nid]) if name_zh.get(nid) else 'nil'))
        lines.append('    [%d] = { %s },' % (iid, ', '.join(parts)))
    lines.append('}')
    lines.append('')
    lines.append('ns.GearVendorSpawns = {')
    for nid in sorted(spawn_rows):
        parts = []
        for aid, mid, x, y in spawn_rows[nid]:
            parts.append('{ %d, %s, %s, %s }' % (
                aid, mid if mid else 'nil',
                ('%g' % x), ('%g' % y)))
        lines.append('    [%d] = { %s },' % (nid, ', '.join(parts)))
    lines.append('}')
    lines.append('')

    out = os.path.join(ROOT, 'Core', 'Data', 'Data_GearVendors.lua')
    open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('商人装备收录 %d 件 / 无 sold-by %d 件 / 无刷点 NPC %d 个'
          % (len(vendors), len(no_data), len(no_spawn)))
    print('NPC %d 个，写出 %s' % (len(spawn_rows), out))


if __name__ == '__main__':
    main()
