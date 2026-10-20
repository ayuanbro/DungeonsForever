#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_vendors.py —— 商人定位采集器（只依赖 Item.csv 与 Wowhead）

任务：为 Item.csv 里的每张图纸/配方（ClassID=9）找出：谁卖它（NPC）、在哪卖
（区域 + 坐标 + 阵营），并解析出售行的成本与库存。只输出 CSV，不写 Lua，
不取售价（售价由游戏内 API 取得）。

数据链路（每层可切换，见 --xxx-provider）：
  1. 物品全集   Item.csv（wow.tools 导出）：ClassID=9 配方物品（默认排除 sub=0 书籍）
                --ids / --id-file 可额外追加
  2. Sold by    Wowhead Forever 物品页 tab-sold-by（本机 Chrome，代理过 WAF）
                每行解析：NPC id / 区域 / 阵营 / 英文名 / 成本(铜) / 库存
  3. NPC 信息   nether.wowhead.com NPC tooltip（默认英文名，--locale 可切 + map.zone + 首组坐标）
                QuestieDB npc_spawns 兜底
  4. 产物       scripts/out/vendors.csv + scripts/out/npcs.csv

用法示例：
  # 预演（只读，不抓取不写文件）
  python scripts/gen_vendors.py --item-db2 "C:/Users/yewei/Downloads/item.csv" --plan

  # 全量：Item.csv 的配方 → Chrome 抓 wowhead → 写 CSV
  python scripts/gen_vendors.py --item-db2 "C:/Users/yewei/Downloads/item.csv"

  # 少量试水
  python scripts/gen_vendors.py --ids 85,193 --dry

依赖：pip install playwright + 本机 Chrome（--channel/--browser/--cdp 可选）；
nether 访问走 --proxy（Windows 默认 http://127.0.0.1:7897，无代理时传 --proxy ""）。
"""
import argparse
import csv
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, '.cache')
OUTDIR = os.path.join(HERE, 'out')

# ─────────────────────────── 可调配置 ───────────────────────────

IS_WIN = sys.platform == 'win32'
PROXY = os.environ.get('DF_PROXY', 'http://127.0.0.1:7897' if IS_WIN else '')
WH_ITEM_URL = 'https://www.wowhead.com/forever/item=%d'        # Sold by 区块
NETHER_NPC_URL = 'https://nether.wowhead.com/forever/tooltip/npc/%d'  # +?locale=

CHROME_CHANNEL = os.environ.get(
    'DF_CHROME_CHANNEL', 'chrome' if IS_WIN else 'chromium')   # 服务器默认 playwright 自装 chromium
CHROME_EXE = os.environ.get('DF_CHROME_EXE', '')               # 可选：显式 chrome.exe 路径
WORKERS = 2
PAGE_DELAY = 4.0
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

CSV_VENDORS_OUT = os.path.join(OUTDIR, 'vendors.csv')
CSV_NPCS_OUT = os.path.join(OUTDIR, 'npcs.csv')
AREA_MAP_LUA = os.path.join(ROOT, 'Core', 'Data', 'Data_AreaMap.lua')

RECIPE_CLASS = 9   # WoW 物品类别：9 = Recipe（配方/图纸）

# wowhead WAF / 封禁特征（沿用旧脚本）
BAN_MARKERS = ('could not be satisfied', 'Static CDN Error')

# ─────────────────────────── 通用小工具 ───────────────────────────

def log(*a):
    print(*a, flush=True)


def http_get(url, proxy=None, timeout=30, retries=3, quiet=False):
    """带代理的 GET，返回 bytes；失败返回 None。"""
    handler = urllib.request.ProxyHandler(
        {'http': proxy, 'https': proxy} if proxy else {})
    opener = urllib.request.build_opener(handler)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with opener.open(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if i == retries - 1:
                if not quiet:
                    log('  [http] %s -> %s' % (url[:110], e))
                return None
            time.sleep(1.0 + i)


def http_json(url, proxy=None, timeout=30, retries=3, quiet=False):
    data = http_get(url, proxy, timeout, retries, quiet=quiet)
    if not data:
        return None
    try:
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        if not quiet:
            log('  [json] %s -> %s' % (url[:110], e))
        return None


def load_cached(path, refetch):
    if not refetch and os.path.exists(path):
        try:
            return open(path, encoding='utf-8').read()
        except Exception:
            pass
    return None


def save(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


# ─────────────────────────── 1. 物品全集（Item.csv） ───────────────────────────

def load_id_list(path):
    ids = []
    for line in open(path, encoding='utf-8'):
        line = line.strip().split('#', 1)[0].strip()
        if not line:
            continue
        for tok in re.split(r'[,\s]+', line):
            if tok.isdigit():
                ids.append(int(tok))
    return ids


def load_item_db2(path, exclude_books=True):
    """读 wow.tools 导出的 Item.csv，取 ClassID=9（配方类）物品 ID。
    exclude_books=True 时排除 SubclassID=0（书籍/手册，非专业配方）。"""
    ids = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            try:
                cls = int(row.get('ClassID') or -1)
            except (TypeError, ValueError):
                cls = -1
            if cls != RECIPE_CLASS:
                continue
            try:
                iid = int(row.get('ID') or 0)
            except (TypeError, ValueError):
                continue
            if iid <= 0:
                continue
            if exclude_books:
                try:
                    sub = int(row.get('SubclassID') or 0)
                except (TypeError, ValueError):
                    sub = 0
                if sub == 0:
                    continue
            ids.append(iid)
    return sorted(set(ids))


# ─────────────────────────── 2. Sold by 层（可切换） ───────────────────────────
# 契约：soldby_provider.sold_by(ids) -> {itemID: [row,...]}
# row = {npc, name, zone, side, cost, stock}

ROW_RE = re.compile(r'<tr class="listview-row">(.*?)</tr>', re.S)
TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
# 注意：data-wowhead="map" 之后可能还有 style 等属性（带图标行），要容到 ">"
NPC_RE = re.compile(r'npc=(\d+)/[a-z0-9-]*"[^>]*data-wowhead="map"[^>]*>([^<]*)</a>')
ZONE_RE = re.compile(r'zone=(\d+)/[a-z0-9-]*"[^>]*>([^<]*)</a>')
SIDE_RE = re.compile(r'<span class="q2?">([AH])</span>')

# 成本：wowhead 金钱三段（金/银/铜 span），或只有铜
MONEY_GSC_RE = re.compile(
    r'<span class="moneygold">(\d+)</span>\s*'
    r'<span class="moneysilver">(\d+)</span>\s*'
    r'<span class="moneycopper">(\d+)</span>')
MONEY_CU_RE = re.compile(r'<span class="moneycopper">(\d+)</span>')


def parse_cost(row):
    m = MONEY_GSC_RE.search(row)
    if m:
        return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
    m = MONEY_CU_RE.search(row)
    if m:
        return int(m.group(1))
    return None


# 非金币价格：成本单元格里是 <a href="…/currency=3402/…">数量</a>（如商人青睐），
# 以物易物时也可能是 <a href="…/item=ID/…">数量</a>。
CURRENCY_LINK_RE = re.compile(
    r'href="[^"]*currency=(\d+)/[a-z0-9-]*"[^>]*>\s*(\d+)\s*</a>')
ITEM_LINK_RE = re.compile(
    r'href="[^"]*item=(\d+)/[a-z0-9-]*"[^>]*>\s*(\d+)\s*</a>')


def parse_currency(row):
    """返回 (kind, id, amount)：kind='currency'（如商人青睐）或 'item'（以物易物）。"""
    m = CURRENCY_LINK_RE.search(row)
    if m:
        return 'currency', int(m.group(1)), int(m.group(2))
    m = ITEM_LINK_RE.search(row)
    if m:
        return 'item', int(m.group(1)), int(m.group(2))
    return None, None, None


def parse_stock(row):
    """Sold by 表的 Stock 列（第 5 个单元格）：
    -1 = 不限量（单元格为 ∞）；N = 限量 N 个；None = 未知。"""
    cells = TD_RE.findall(row)
    if len(cells) <= 4:
        return None
    text = re.sub(r'<[^>]+>', '', cells[4]).strip()
    if '∞' in text:
        return -1
    if text.isdigit():
        return int(text)
    return None


def parse_sold_by(html):
    """从物品页 HTML 解析 tab-sold-by：NPC id / 区域 / 阵营 / 英文名 / 成本 / 库存。"""
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
        ckind, cid, camt = parse_currency(row)
        rows.append({
            'npc': int(nm.group(1)),
            'name': nm.group(2).strip(),
            'zone': int(zn.group(1)) if zn else None,
            'side': sd.group(1).lower() if sd else None,
            'cost': parse_cost(row),
            'currency_kind': ckind,
            'currency_id': cid,
            'currency_amount': camt,
            'stock': parse_stock(row),
        })
    return rows


def is_ban(cur):
    return any(b in cur for b in BAN_MARKERS)


class SoldByWowhead:
    """Wowhead Forever 物品页抓取（本机 Chrome，playwright 渠道，代理过 WAF）。"""

    def __init__(self, channel=CHROME_CHANNEL, executable=None, cdp_url=None,
                 workers=WORKERS, page_delay=PAGE_DELAY, proxy=PROXY,
                 refetch=False, headless=None, max_age_days=0):
        self.channel = channel          # playwright 渠道：chrome / msedge / chromium
        self.executable = executable    # 可选：显式浏览器 exe 路径
        self.cdp_url = cdp_url          # 可选：附加到已开调试口的浏览器
        self.workers = 1 if cdp_url else workers
        self.page_delay = page_delay
        self.proxy = proxy
        self.refetch = refetch
        # 服务器（非 Windows）默认 headless；Windows 默认带窗口
        self.headless = (not IS_WIN) if headless is None else headless
        self.max_age_days = max_age_days
        self.cache_dir = os.path.join(CACHE, 'soldby')

    def _cache_path(self, iid):
        return os.path.join(self.cache_dir, '%d.html' % iid)

    def _valid_cached(self, p):
        try:
            cur = open(p, encoding='utf-8', errors='ignore').read()
            return len(cur) > 20000 and not is_ban(cur)
        except Exception:
            return False

    def _fresh(self, p):
        """每日增量：缓存页超过 max_age_days 天则视为过期重抓。"""
        if self.max_age_days <= 0:
            return True
        try:
            return (time.time() - os.path.getmtime(p)) \
                < self.max_age_days * 86400
        except OSError:
            return False

    def _worker(self, items_q, out_q, wid, profile):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log('  [soldby] 需要 pip install playwright（并安装 Chrome）')
            while True:
                try:
                    iid = items_q.get_nowait()
                except queue.Empty:
                    return
                out_q.put((iid, None, 'no-playwright'))
            return

        with sync_playwright() as p:
            state = {'ctx': None, 'pg': None, 'br': None}

            def ensure():
                if state['ctx'] is not None:
                    try:
                        state['pg'].goto('about:blank', timeout=8000)
                        return True
                    except Exception:
                        pass
                try:
                    if state['ctx'] is not None:
                        state['ctx'].close()
                except Exception:
                    pass
                state['ctx'] = state['pg'] = None
                state['br'] = None
                try:
                    if self.cdp_url:
                        state['br'] = p.chromium.connect_over_cdp(self.cdp_url)
                        state['ctx'] = state['br'].contexts[0]
                        state['pg'] = state['ctx'].pages[0] \
                            if state['ctx'].pages else state['ctx'].new_page()
                    else:
                        kwargs = dict(
                            channel=self.channel,
                            executable_path=self.executable or None,
                            headless=self.headless,
                            viewport={'width': 1280, 'height': 800},
                            args=['--no-first-run', '--no-default-browser-check'])
                        if not self.headless:
                            kwargs['args'] += ['--window-position=3200,0',
                                               '--window-size=1280,800']
                        else:
                            kwargs['args'] += [
                                '--disable-blink-features=AutomationControlled']
                        state['ctx'] = p.chromium.launch_persistent_context(
                            profile, **kwargs)
                        state['pg'] = state['ctx'].pages[0] \
                            if state['ctx'].pages else state['ctx'].new_page()
                    state['ctx'].route(
                        '**/*',
                        lambda route: route.abort()
                        if route.request.resource_type in
                        ('image', 'font', 'media') else route.continue_())
                    state['pg'].goto('about:blank', timeout=15000)
                    return True
                except Exception as e:
                    log('  [soldby] Chrome 启动/连接失败：%s' % str(e)[:140])
                    return False

            ensure()
            cooldowns = 0
            while True:
                try:
                    iid = items_q.get_nowait()
                except queue.Empty:
                    break
                dst = self._cache_path(iid)
                if not self.refetch and self._valid_cached(dst) \
                        and self._fresh(dst):
                    out_q.put((iid, open(dst, encoding='utf-8',
                                         errors='ignore').read(), 'cached'))
                    continue
                html, last = None, ''
                gave_up = False
                while not gave_up:
                    if not ensure():
                        last = 'chrome attach fail'
                        time.sleep(5)
                        continue
                    try:
                        state['pg'].goto(WH_ITEM_URL % iid,
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
                            log('  [w%d] 封禁冷却 #%d，睡 300s'
                                % (wid, cooldowns))
                            time.sleep(300)
                            continue
                        if len(cur) <= 20000 or 'gokuProps' in cur:
                            state['pg'].wait_for_timeout(5000)
                            cur = state['pg'].content()
                        if len(cur) > 20000 and 'gokuProps' not in cur \
                                and not is_ban(cur):
                            html = cur
                            save(dst, cur)
                            break
                        last = 'waf len=%d' % len(cur)
                    except Exception as e:
                        last = str(e)[:120]
                        try:
                            state['ctx'].unroute('**/*')
                        except Exception:
                            pass
                        try:
                            state['ctx'].close()
                        except Exception:
                            pass
                        state['ctx'] = state['pg'] = None
                        state['br'] = None
                    if cooldowns > 60:
                        gave_up = True
                    time.sleep(2)
                out_q.put((iid, html, last))
                time.sleep(self.page_delay)
            # --cdp 附加的是玩家自己的浏览器，不代为关闭
            if not self.cdp_url:
                try:
                    state['pg'].goto('about:blank', timeout=5000)
                    state['pg'].wait_for_timeout(300)
                except Exception:
                    pass
                try:
                    state['ctx'].unroute('**/*')
                except Exception:
                    pass
                time.sleep(0.3)
                try:
                    state['ctx'].close()
                except Exception:
                    pass

    def sold_by(self, ids):
        ids = list(ids)
        if not ids:
            return {}
        os.makedirs(self.cache_dir, exist_ok=True)
        items_q, out_q = queue.Queue(), queue.Queue()
        for iid in ids:
            items_q.put(iid)
        threads = []
        for i in range(self.workers):
            prof = os.path.join(CACHE, '_chrome_profile%d' % i)
            t = threading.Thread(target=self._worker, daemon=True,
                                 args=(items_q, out_q, i, prof))
            threads.append(t)
            t.start()
            if i < len(threads) - 1:
                time.sleep(25)
        pages, n = {}, 0
        while n < len(ids):
            iid, html, how = out_q.get()
            n += 1
            pages[iid] = html or ''
            if n % 50 == 0 or n == len(ids):
                log('  [soldby] %d/%d (%s)' % (n, len(ids), how))
        out = {}
        for iid in ids:
            rows = parse_sold_by(pages.get(iid) or '')
            out[iid] = rows
        return out


class SoldByCache:
    """只用本地缓存（离线重算）。"""

    def __init__(self):
        self.cache_dir = os.path.join(CACHE, 'soldby')

    def sold_by(self, ids):
        out = {}
        for iid in ids:
            p = os.path.join(self.cache_dir, '%d.html' % iid)
            html = ''
            if os.path.exists(p):
                html = open(p, encoding='utf-8', errors='ignore').read()
            out[iid] = parse_sold_by(html)
        return out


class SoldByJson:
    """外部 JSON 导入（游戏内商人窗口采集导出的
    {item: [{npc,zone,side,name,cost,stock}]}）。"""

    def __init__(self, path):
        self.data = json.load(open(path, encoding='utf-8'))

    def sold_by(self, ids):
        out = {}
        for iid in ids:
            rows = self.data.get(str(iid)) or self.data.get(iid) or []
            out[iid] = [{
                'npc': int(r['npc']),
                'name': r.get('name') or '',
                'zone': r.get('zone'),
                'side': r.get('side'),
                'cost': r.get('cost'),
                'currency_kind': r.get('currency_kind'),
                'currency_id': r.get('currency_id'),
                'currency_amount': r.get('currency_amount'),
                'stock': r.get('stock'),
            } for r in rows]
        return out


def make_soldby_provider(args):
    if args.soldby_provider == 'cache':
        return SoldByCache()
    if args.soldby_provider == 'json':
        if not args.soldby_json:
            raise SystemExit('--soldby-provider json 需要 --soldby-json <file>')
        return SoldByJson(args.soldby_json)
    return SoldByWowhead(channel=args.channel, executable=args.browser or None,
                         cdp_url=args.cdp or None, workers=args.workers,
                         page_delay=args.page_delay, refetch=args.refetch,
                         headless=args.headless,
                         max_age_days=args.soldby_max_age)


# ─────────────────────────── 3. NPC 信息层（可切换） ───────────────────────────
# 契约：npc_provider.npc_info(npcs) -> {npcID: {'name': str, 'coords': [(zone,x,y),...]}}

class NpcNether:
    """nether.wowhead.com NPC tooltip：名称（默认英文，--locale 可切）+ map.zone + 首组坐标。"""

    def __init__(self, proxy=PROXY, refetch=False, locale=''):
        self.cache_dir = os.path.join(CACHE, 'nether')
        self.refetch = refetch
        self.proxy = proxy
        self.locale = locale

    def _info(self, nid):
        # 缓存按语言分开，避免 zhCN 与英文互相污染
        suffix = '.' + self.locale if self.locale else ''
        p = os.path.join(self.cache_dir, '%d%s.json' % (nid, suffix))
        cached = load_cached(p, self.refetch)
        if cached is None:
            url = NETHER_NPC_URL % nid
            if self.locale:
                url += '?locale=' + self.locale
            data = http_json(url, proxy=self.proxy, timeout=25, retries=2)
            if data:
                cached = json.dumps(data, ensure_ascii=False)
                save(p, cached)
        if not cached:
            return {'name': '', 'coords': []}
        try:
            d = json.loads(cached)
            name = (d.get('name') or '').strip()
            m = d.get('map') or {}
            zone = m.get('zone')
            coords = []
            if zone:
                try:
                    zone = int(zone)
                except (TypeError, ValueError):
                    zone = None
                cd = m.get('coords') or {}
                for _k, pairs in cd.items():
                    if isinstance(pairs, list) and pairs:
                        x, y = float(pairs[0][0]), float(pairs[0][1])
                        if zone is not None:
                            coords.append((zone, round(x, 1), round(y, 1)))
                        break
            return {'name': name, 'coords': coords}
        except Exception:
            return {'name': '', 'coords': []}

    def npc_info(self, npcs):
        out = {}
        with __import__('concurrent.futures').futures.ThreadPoolExecutor(
                max_workers=8) as ex:
            for nid, info in ex.map(lambda n: (n, self._info(n)), sorted(npcs)):
                out[nid] = info
        return out


class NpcQuestie:
    """QuestieDB questie_forever.json 的 npc_spawns：{npcid: {areaID: [x,y]}}。"""

    def __init__(self, path):
        qj = json.load(open(path, encoding='utf-8'))
        self.spawns = qj.get('npc_spawns') or {}

    def npc_info(self, npcs):
        out = {}
        for nid in npcs:
            zmap = self.spawns.get(str(nid)) or {}
            coords = []
            for zs, xy in zmap.items():
                try:
                    x, y = float(xy[0]), float(xy[1])
                except (TypeError, ValueError):
                    continue
                coords.append((int(zs), round(x, 1), round(y, 1)))
            out[nid] = {'name': '', 'coords': coords}
        return out


class NpcJson:
    """外部 JSON 导入：{npcID: {name, coords: [[zone,x,y],...]}}。"""

    def __init__(self, path):
        self.data = json.load(open(path, encoding='utf-8'))

    def npc_info(self, npcs):
        out = {}
        for nid in npcs:
            e = self.data.get(str(nid)) or self.data.get(nid) or {}
            out[nid] = {'name': e.get('name') or '',
                        'coords': [tuple(c) for c in (e.get('coords') or [])]}
        return out


def make_npc_provider(args):
    if args.npc_provider == 'questie':
        if not args.questie:
            raise SystemExit('--npc-provider questie 需要 --questie <questie_forever.json>')
        return NpcQuestie(args.questie)
    if args.npc_provider == 'json':
        if not args.npc_json:
            raise SystemExit('--npc-provider json 需要 --npc-json <file>')
        return NpcJson(args.npc_json)
    return NpcNether(proxy=args.proxy, refetch=args.refetch, locale=args.locale)


# ─────────────────────────── 4. 区域映射与 CSV 产物 ───────────────────────────

def load_area_map(path=AREA_MAP_LUA):
    d = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'\[(-?\d+)\]\s*=\s*(\d+)', d):
        out[int(m.group(1))] = int(m.group(2))
    return out


def money_str(copper):
    if copper is None:
        return ''
    g, r = divmod(copper, 10000)
    s, c = divmod(r, 100)
    parts = []
    if g:
        parts.append('%dg' % g)
    if s:
        parts.append('%ds' % s)
    if c or not parts:
        parts.append('%dc' % c)
    return ''.join(parts)


def emit_csv_vendors(vendors, npc_locale, out_path):
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['item_id', 'npc_id', 'zone_id', 'side', 'name_en',
                    'name_locale', 'cost_copper', 'cost_text',
                    'currency_kind', 'currency_id', 'currency_amount', 'stock'])
        n = 1
        for iid in sorted(vendors):
            for nid, zone, side, name, cost, ckind, cid, camt, stock \
                    in vendors[iid]:
                w.writerow([iid, nid, '' if zone is None else zone,
                            side or '', name, npc_locale.get(nid) or '',
                            '' if cost is None else cost, money_str(cost),
                            ckind or '', '' if cid is None else cid,
                            '' if camt is None else camt,
                            '' if stock is None else stock])
                n += 1
    log('  [out] %s（%d 行）' % (out_path, n))


def emit_csv_npcs(spawns, npc_en, npc_locale, out_path):
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['npc_id', 'name_en', 'name_locale', 'zone_id',
                    'ui_map_id', 'x', 'y'])
        n = 1
        for nid in sorted(spawns):
            for aid, mid, x, y in spawns[nid]:
                w.writerow([nid, npc_en.get(nid) or '', npc_locale.get(nid) or '',
                            aid, '' if mid is None else mid, x, y])
                n += 1
    log('  [out] %s（%d 行）' % (out_path, n))


# ─────────────────────────── 自检（无网络） ───────────────────────────

def selftest():
    ok = 0
    def check(name, cond):
        nonlocal ok
        log('  %-46s %s' % (name, 'PASS' if cond else 'FAIL'))
        ok += 1 if cond else 0

    # 1. sold-by 解析（真实表结构：…/Stock/Cost 列，含成本与不限量库存）
    html = ('<html><body><div id="tab-sold-by"><table>'
            '<tr class="listview-row"><td class="listview-env-change"><span class="tip">'
            'Updated</span></td><td>'
            '<a class="listview-cleartext icontiny tinyspecial" '
            'href="/forever/npc=2113/archibald-kava" class="q2" '
            'data-wowhead="map" style="background-image: url(&quot;x.gif&quot;);">'
            'Archibald Kava</a></td><td>'
            '<a href="/forever/zone=85/undercity" class="q">Undercity</a></td>'
            '<td><span class="q2">H</span></td>'
            '<td>∞</td>'
            '<td><span class="moneygold">1</span> '
            '<span class="moneysilver">23</span> '
            '<span class="moneycopper">45</span></td>'
            '<td><span class="popularity-icon popularity-8"></span></td></tr>'
            '<tr class="listview-row"><td class="listview-env-change"></td><td>'
            '<a href="/forever/npc=3492/vexspindle" data-wowhead="map">Vexspindle</a>'
            '</td><td><a href="/forever/zone=17/elwynn-forest" class="q">'
            'Elwynn Forest</a></td><td><span class="q2">A</span></td>'
            '<td>3</td><td></td></tr>'
            '<tr class="listview-row"><td class="listview-env-change"><span>New</span></td><td>'
            '<a class="listview-cleartext" href="/forever/npc=248200/fizzlefuse" '
            'data-wowhead="map">Fizzlefuse</a></td><td>'
            '<a class="q1" href="/forever/zone=17/the-barrens">The Barrens</a></td>'
            '<td><span class="q">H</span></td><td>∞</td>'
            '<td><a href="https://www.wowhead.com/forever/currency=3402/merchants-favor" '
            'class="icontinyr tip q1 no-wrap" '
            'style="background-image: url(&quot;x.gif&quot;);">360</a></td>'
            '<td><span class="popularity-icon popularity-8"></span></td></tr>'
            '</table></div></body></html>')
    rows = parse_sold_by(html)
    check('parse_sold_by: 3 rows', len(rows) == 3)
    check('parse_sold_by: npc 2113', rows and rows[0]['npc'] == 2113)
    check('parse_sold_by: zone 85', rows and rows[0]['zone'] == 85)
    check('parse_sold_by: side h', rows and rows[0]['side'] == 'h')
    check('parse_sold_by: en name', rows and rows[1]['name'] == 'Vexspindle')
    check('parse_sold_by: cost=1g23s45c', rows and rows[0]['cost'] == 12345)
    check('parse_sold_by: stock ∞→-1(不限量)', rows and rows[0]['stock'] == -1)
    check('parse_sold_by: stock 3(限量)', rows and rows[1]['stock'] == 3)
    check('parse_sold_by: 第二行无成本', rows and rows[1]['cost'] is None)
    check('parse_sold_by: currency=3402', rows and rows[2]['currency_id'] == 3402
          and rows[2]['currency_kind'] == 'currency')
    check('parse_sold_by: currency 数量 360', rows and rows[2]['currency_amount'] == 360
          and rows[2]['cost'] is None)
    check('parse_sold_by: 无区块为空', parse_sold_by('<html></html>') == [])
    check('money_str: 1g23s45c', money_str(12345) == '1g23s45c')

    # 2. nether NPC 解析（默认英文名）
    nether = json.loads(
        '{"name":"Archibald Kava","tooltip":"<table></table>",'
        '"map":{"zone":85,"coords":{"0":[[32.4,65.6]]}}}')
    prov = NpcNether.__new__(NpcNether)
    prov.cache_dir = os.path.join(CACHE, 'nether_selftest')
    prov.refetch = False
    prov.proxy = None
    prov.locale = ''
    import types
    def _fake_info(self, nid):
        if nid == 2113:
            return {'name': 'Archibald Kava',
                    'coords': [(85, 32.4, 65.6)]}
        return {'name': '', 'coords': []}
    prov._info = types.MethodType(_fake_info, prov)
    info = prov.npc_info([2113])[2113]
    check('nether parse: en name', info['name'] == 'Archibald Kava')
    check('nether parse: coords', info['coords'] == [(85, 32.4, 65.6)])

    # 3. Item.csv 配方识别（排除书籍）
    import tempfile
    tmp = tempfile.NamedTemporaryFile(
        'w', suffix='.csv', delete=False, encoding='utf-8')
    tmp.write('ID,ClassID,SubclassID\n1,9,6\n2,9,0\n3,4,2\n4,9,3\n')
    tmp.close()
    ids = load_item_db2(tmp.name, exclude_books=True)
    check('item db2: 排除书籍 [1,4]', ids == [1, 4])
    ids2 = load_item_db2(tmp.name, exclude_books=False)
    check('item db2: 保留书籍 [1,2,4]', ids2 == [1, 2, 4])
    os.unlink(tmp.name)

    # 4. 区域映射表（读真实文件）
    area = load_area_map()
    check('area map: rows>30', len(area) > 30)
    check('area map: 85->uiMap', area.get(85) is not None)

    log('selftest %d/19' % ok)


# ─────────────────────────── 主流程 ───────────────────────────

def plan_mode(args, ids):
    log('== 预演（只读） ==')
    log('入选物品：%d 件' % len(ids))
    n_cached = 0
    for iid in ids:
        p = os.path.join(CACHE, 'soldby', '%d.html' % iid)
        if os.path.exists(p):
            n_cached += 1
    log('已缓存 wowhead 页：%d / %d' % (n_cached, len(ids)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--item-db2', help='wow.tools 导出的 Item.csv（取 ClassID=9 配方物品作全集）')
    ap.add_argument('--keep-books', action='store_true',
                    help='保留 SubclassID=0 的书籍（默认排除）')
    ap.add_argument('--ids', help='逗号分隔的物品 ID（额外追加）')
    ap.add_argument('--id-file', help='每行一个物品 ID 的文件（额外追加）')
    ap.add_argument('--plan', action='store_true', help='只读预演，不抓取不写文件')
    ap.add_argument('--selftest', action='store_true', help='无网络自检')

    ap.add_argument('--soldby-provider', choices=['wowhead', 'cache', 'json'],
                    default='wowhead')
    ap.add_argument('--soldby-json', help='soldby-provider=json 时的导入文件')
    ap.add_argument('--refetch', action='store_true', help='强制重抓 wowhead 页面')
    ap.add_argument('--headless', dest='headless', action='store_true', default=None,
                    help='无头模式（服务器用；Windows 默认带窗口，Linux 默认无头）')
    ap.add_argument('--soldby-max-age', type=float, default=0,
                    help='缓存的 wowhead 页超过 N 天则重抓（每日更新建议 7；0=永不）')

    ap.add_argument('--npc-provider', choices=['nether', 'questie', 'json'],
                    default='nether')
    ap.add_argument('--questie', help='questie_forever.json（坐标兜底）')
    ap.add_argument('--npc-json', help='npc-provider=json 时的导入文件')
    ap.add_argument('--locale', default='',
                    help='nether 名称语言：留空=英文（默认），zhCN=中文')

    ap.add_argument('--proxy', default=PROXY)
    ap.add_argument('--channel', default=CHROME_CHANNEL,
                    help='playwright 浏览器渠道：chrome / msedge / chromium')
    ap.add_argument('--browser', default=(CHROME_EXE or None),
                    help='显式浏览器 exe 路径（可选，覆盖 --channel）')
    ap.add_argument('--cdp', default='',
                    help='附加到已开调试口的浏览器（如 http://127.0.0.1:9222）')
    ap.add_argument('--workers', type=int, default=WORKERS)
    ap.add_argument('--page-delay', type=float, default=PAGE_DELAY)
    ap.add_argument('--csv-out', default=CSV_VENDORS_OUT,
                    help='vendors.csv 路径（空串=不写）')
    ap.add_argument('--npcs-out', default=CSV_NPCS_OUT,
                    help='npcs.csv 路径（空串=不写）')
    ap.add_argument('--dry', action='store_true', help='只抓取计算，不写文件')
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    ids = []
    if args.ids:
        ids += [int(x) for x in re.split(r'[,\s]+', args.ids)
                if x.strip().isdigit()]
    if args.id_file:
        ids += load_id_list(args.id_file)
    if args.item_db2:
        if not os.path.exists(args.item_db2):
            raise SystemExit('找不到 Item.csv：' + args.item_db2)
        db2_ids = load_item_db2(args.item_db2,
                                exclude_books=not args.keep_books)
        ids += db2_ids
        log('从 Item.csv 载入配方物品 %d 件（%s）'
            % (len(db2_ids), '保留书籍' if args.keep_books else '已排除书籍 sub=0'))
    ids = sorted(set(ids))
    if not ids:
        raise SystemExit('没有物品 ID：请提供 --item-db2 Item.csv 或 --ids / --id-file')
    log('入选物品 %d 件' % len(ids))

    if args.plan:
        plan_mode(args, ids)
        return

    # ── Sold by ──
    sp = make_soldby_provider(args)
    sold = sp.sold_by(ids)

    vendors = {}
    for iid, vrows in sold.items():
        if vrows:
            vendors[iid] = [(r['npc'], r['zone'], r['side'], r['name'],
                             r['cost'], r['currency_kind'], r['currency_id'],
                             r['currency_amount'], r['stock']) for r in vrows]
    npcs = {r[0] for lst in vendors.values() for r in lst}
    npc_en = {}
    for lst in vendors.values():
        for row in lst:
            npc_en.setdefault(row[0], row[3])
    no_data = [iid for iid in ids if not sold.get(iid)]
    log('sold-by 命中 %d 件 / 空 %d 件 / NPC %d 个'
        % (len(vendors), len(no_data), len(npcs)))

    # ── NPC 信息（nether 默认 + questie 兜底） ──
    np = make_npc_provider(args)
    info = np.npc_info(npcs) if npcs else {}
    questie = None
    if args.questie:
        questie = NpcQuestie(args.questie).npc_info(npcs)

    npc_locale = {nid: info.get(nid, {}).get('name', '') for nid in npcs}
    area_map = load_area_map()
    spawns = {}
    for nid in npcs:
        coords = list(info.get(nid, {}).get('coords') or [])
        if not coords and questie:
            coords = list(questie.get(nid, {}).get('coords') or [])
        rows2 = []
        for z, x, y in coords:
            try:
                z, x, y = int(z), float(x), float(y)
            except (TypeError, ValueError):
                continue
            rows2.append((z, area_map.get(z), round(x, 1), round(y, 1)))
        spawns[nid] = rows2
    no_spawn = [nid for nid in npcs if not spawns[nid]]
    log('NPC 名称 %d/%d · 无坐标 %d 个'
        % (sum(1 for v in npc_locale.values() if v), len(npcs), len(no_spawn)))

    # ── 产物（只写 CSV，不写 Lua） ──
    if not args.dry:
        if args.csv_out:
            emit_csv_vendors(vendors, npc_locale, args.csv_out)
        if args.npcs_out:
            emit_csv_npcs(spawns, npc_en, npc_locale, args.npcs_out)
    else:
        log('--dry：跳过文件写入')

    log('完成：商人物品 %d / 空 %d / NPC %d / 无坐标 NPC %d'
        % (len(vendors), len(no_data), len(npcs), len(no_spawn)))


if __name__ == '__main__':
    main()
