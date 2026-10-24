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
import hashlib
import io
import math
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.request
from html import unescape
from html.parser import HTMLParser

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

# 零面额会省略；金币、银币、铜币分别读取，只处理传入的成本单元格。
MONEY_RE = re.compile(
    r'''<span\b[^>]*\bclass=["'][^"']*\bmoney(gold|silver|copper)\b[^"']*["'][^>]*>\s*(\d+)\s*</span>''')


def parse_cost(cost_cell):
    parts = MONEY_RE.findall(cost_cell)
    units = {'gold': 10000, 'silver': 100, 'copper': 1}
    return sum(int(amount) * units[unit] for unit, amount in parts) if parts else None


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


def _js_value_end(text, start, delimiter):
    """Find a top-level delimiter without evaluating JavaScript."""
    stack, quote, escaped = [], None, False
    i = start
    while i < len(text):
        char = text[i]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'", '`'):
            quote = char
        elif text.startswith('//', i):
            end = text.find('\n', i + 2)
            i = len(text) if end < 0 else end
            continue
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0:
                raise ValueError('Unterminated comment in Listview options')
            i = end + 2
            continue
        elif not stack and char == delimiter:
            return i
        elif char in '[{(':
            stack.append(char)
        elif char in ']})':
            if not stack or '[{('.index(stack.pop()) != ']})'.index(char):
                raise ValueError('Unbalanced Listview options')
        i += 1
    if stack or quote:
        raise ValueError('Unterminated Listview options')
    return len(text)


def _next_listview(script, start):
    call = re.compile(r'\bnew\s+Listview\s*\(\s*\{')
    i = start
    while i < len(script):
        if script[i] in ('"', "'", '`'):
            quote, escaped = script[i], False
            i += 1
            while i < len(script):
                char = script[i]
                i += 1
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == quote:
                    break
        elif script.startswith('//', i):
            end = script.find('\n', i + 2)
            i = len(script) if end < 0 else end + 1
        elif script.startswith('/*', i):
            end = script.find('*/', i + 2)
            i = len(script) if end < 0 else end + 2
        else:
            match = call.match(script, i)
            if match:
                return match
            i += 1
    return None


def _sold_by_listview(html):
    """Read only the sold-by NPC Listview's JSON data, including hidden tabs."""
    found = None
    key = re.compile(r'''\s*(?:([A-Za-z_]\w*)|["']([A-Za-z_]\w*)["'])\s*:\s*''')
    for script in re.findall(r'<script\b[^>]*>(.*?)</script\s*>', html, re.S | re.I):
        offset = 0
        while True:
            match = _next_listview(script, offset)
            if not match:
                break
            end = _js_value_end(script, match.end(), '}')
            if end == len(script):
                raise ValueError('Unterminated Listview object')
            body, fields = script[match.end():end], {}
            position = 0
            while position < len(body):
                value_end = _js_value_end(body, position, ',')
                part = body[position:value_end]
                field = key.match(part)
                if field:
                    fields[field.group(1) or field.group(2)] = part[field.end():].strip()
                position = value_end + 1
            offset = end + 1
            if not re.fullmatch(r'''["']npc["']''', fields.get('template', '')) \
                    or not re.fullmatch(r'''["']sold-by["']''', fields.get('id', '')):
                continue
            if found is not None:
                raise ValueError('Multiple sold-by NPC Listviews')
            try:
                found = json.loads(fields['data'])
            except (KeyError, ValueError) as error:
                raise ValueError('Invalid sold-by Listview JSON data') from error
            if not isinstance(found, list):
                raise ValueError('Sold-by Listview data must be an array')
    return found


def _source_cost(cost, npc):
    unknown = (None, None, None, None)
    if cost is None or cost == []:
        return unknown

    def valid(value, minimum):
        return type(value) is int and value >= minimum

    def unsupported():
        raise ValueError('Unsupported sold-by cost for NPC %d: %r' % (npc, cost))

    if not isinstance(cost, list) or len(cost) != 1 \
            or not isinstance(cost[0], list) or len(cost[0]) > 3:
        unsupported()
    option = cost[0]
    copper = option[0] if option else None
    if copper is not None and not valid(copper, 0):
        unsupported()
    currencies = option[1] if len(option) > 1 else []
    items = option[2] if len(option) > 2 else []
    if not isinstance(currencies, list) or not isinstance(items, list) \
            or len(currencies) + len(items) > 1:
        unsupported()
    tokens = currencies or items
    if not tokens:
        return copper, None, None, None
    pair = tokens[0]
    if not isinstance(pair, list) or len(pair) != 2 \
            or not valid(pair[0], 1) or not valid(pair[1], 0):
        unsupported()
    # Zero copper in a token exchange is not a free gold purchase.
    return copper or None, 'currency' if currencies else 'item', pair[0], pair[1]


class _SoldByPanel(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth, self.parts, self.complete = 0, [], False

    def handle_starttag(self, tag, attrs):
        if self.complete:
            return
        if tag == 'div' and (self.depth or dict(attrs).get('id') == 'tab-sold-by'):
            self.depth += 1
        if self.depth:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth:
            self.parts.append('</%s>' % tag)
            if tag == 'div':
                self.depth -= 1
                self.complete = self.depth == 0

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        self.handle_data('&%s;' % name)

    def handle_charref(self, name):
        self.handle_data('&#%s;' % name)


def parse_sold_by(html):
    """Read sold-by source JSON first; rendered HTML remains a scoped fallback."""
    source = _sold_by_listview(html)
    if source is not None:
        rows = []
        for raw in source:
            if not isinstance(raw, dict) or type(raw.get('id')) is not int or raw['id'] <= 0:
                raise ValueError('Invalid sold-by NPC record: %r' % raw)
            npc = raw['id']
            copper, kind, currency, amount = _source_cost(raw.get('cost'), npc)
            locations = raw.get('location')
            zone = locations[0] if isinstance(locations, list) and locations else None
            zone = zone if type(zone) is int and zone > 0 else None
            react = raw.get('react')
            side = None
            if isinstance(react, list) and len(react) == 2:
                available = [type(value) in (int, float) and value >= 0 for value in react]
                side = 'n' if all(available) else 'a' if available[0] else 'h' if available[1] else None
            name = raw.get('name')
            if not isinstance(name, str) or not name.strip():
                name = raw.get('displayName')
            stock = raw.get('stock')
            rows.append({'npc': npc, 'name': unescape(name).strip() if isinstance(name, str) else '',
                         'zone': zone, 'side': side, 'cost': copper,
                         'currency_kind': kind, 'currency_id': currency,
                         'currency_amount': amount,
                         'stock': stock if type(stock) is int and stock >= -1 else None})
        return rows
    panel = _SoldByPanel()
    panel.feed(html)
    seg = ''.join(panel.parts)
    rows = []
    for m in ROW_RE.finditer(seg):
        row = m.group(1)
        nm = NPC_RE.search(row)
        if not nm:
            continue
        zn = ZONE_RE.search(row)
        sd = SIDE_RE.search(row)
        cells = TD_RE.findall(row)
        cost_cell = cells[5] if len(cells) > 5 else ''
        ckind, cid, camt = parse_currency(cost_cell)
        rows.append({
            'npc': int(nm.group(1)),
            'name': nm.group(2).strip(),
            'zone': int(zn.group(1)) if zn else None,
            'side': sd.group(1).lower() if sd else None,
            'cost': parse_cost(cost_cell),
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
                                "var a=document.querySelector('[role=tab][data-href=\"#sold-by\"]');"
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
# 契约：npc_provider.npc_info(npcs) -> {npcID: {'name': str, 'coords': [(zone,x,y),...],
# 'faction': 可选的明确所属组织证据}}。所属组织与出售行的 A/H/N side 独立。

class _NpcTooltipRows(HTMLParser):
    """Read tooltip row text and explicit faction links without evaluating HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.current, self.faction_links = [], None, []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current, self.faction_links, self.anchor = [], [], None
        elif self.current is not None and tag == 'a':
            href = dict(attrs).get('href') or ''
            match = re.search(r'(?:/|[?&])faction[=/](\d+)(?:\D|$)', href)
            if match and int(match.group(1)) > 0:
                self.anchor = (int(match.group(1)), [])

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)
        if self.anchor is not None:
            self.anchor[1].append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            fid, text = self.anchor
            self.faction_links.append((fid, ' '.join(''.join(text).split())))
            self.anchor = None
        elif tag == 'tr' and self.current is not None:
            self.rows.append((' '.join(''.join(self.current).split()), self.faction_links))
            self.current, self.faction_links, self.anchor = None, [], None


def parse_npc_faction(tooltip):
    """Extract the explicit affiliation row, never from the NPC's name or react.

    Nether puts an affiliation after the creature level/type row. A lone type
    row such as ``Demon (Rare)`` supplies no affiliation.
    """
    parser = _NpcTooltipRows()
    parser.feed(tooltip or '')
    linked = {(fid, name) for _, links in parser.rows for fid, name in links}
    if linked:
        if len(linked) != 1:
            raise ValueError('conflicting explicit NPC faction links')
        fid, name = next(iter(linked))
        if not name:
            raise ValueError('explicit NPC faction link has no name')
        return {'name': name, 'factionID': fid}
    creature_line = re.compile(
        r'^(?:Level\s+(?:\d+\b|\?+)|等级\s*(?:\d+\b|\?+)|等級\s*(?:\d+\b|\?+)|'
        r'(?:Beast|Dragonkin|Demon|Elemental|Giant|Undead|Humanoid|Critter|Mechanical|'
        r'Not specified|Totem|Non-combat Pet|Gas Cloud|Wild Pet|Aberration|'
        r'野兽|野獸|龙类|龍類|恶魔|惡魔|元素生物|巨人|亡灵|不死族|人型生物|'
        r'小动物|小動物|机械|機械|未指定|图腾|圖騰|非战斗宠物|非戰鬥寵物|畸变|畸變)'
        r'(?:\s*[(（]|\s*$))')
    if len(parser.rows) >= 3 and creature_line.search(parser.rows[-2][0]):
        name = parser.rows[-1][0]
        if name and not creature_line.search(name):
            return {'name': name}
    return None


def load_faction_names(path):
    """Index exact client Faction names; no NPC-name or fuzzy matching."""
    if not path:
        return {}, None
    with open(path, 'rb') as stream:
        content = stream.read()
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    by_name, by_id, ambiguous = {}, {}, set()
    for row in reader:
        value = row.get('ID') or row.get('FactionID') or ''
        if not re.fullmatch(r'[1-9]\d*', value):
            raise ValueError('Faction CSV has an invalid ID: %r' % value)
        fid = int(value)
        names = {locale: unescape(row.get('Name_' + locale) or '').strip()
                 for locale in ('enUS', 'zhCN', 'zhTW')}
        if not any(names.values()):
            names['enUS'] = unescape(row.get('Name_lang') or row.get('Name') or '').strip()
        names = {locale: name for locale, name in names.items() if name}
        if not names or 'enUS' not in names:
            raise ValueError('Faction CSV must provide an English name for ID %d' % fid)
        record = {'factionID': fid, 'names': names}
        if fid in by_id and by_id[fid] != record:
            raise ValueError('Faction CSV has conflicting names for ID %d' % fid)
        by_id[fid] = record
        for name in names.values():
            if name in by_name and by_name[name]['factionID'] != fid:
                ambiguous.add(name)
                by_name.pop(name)
            if name not in ambiguous:
                by_name[name] = record
    return by_name, {'type': 'client-faction-csv', 'file': os.path.basename(path),
                     'sha256': hashlib.sha256(content).hexdigest()}


def _faction_evidence(value):
    """Validate the collector's replayable affiliation shape, before English merge."""
    if not isinstance(value, dict) or set(value) - {'factionID', 'names', 'sources'}:
        raise ValueError('NPC faction evidence must contain names, sources and optional factionID')
    names, sources = value.get('names'), value.get('sources')
    if not isinstance(names, dict) or not names or set(names) - {'enUS', 'zhCN', 'zhTW'} \
            or any(not isinstance(name, str) or not name.strip() for name in names.values()):
        raise ValueError('NPC faction evidence has invalid localized names')
    if not isinstance(sources, list) or not sources:
        raise ValueError('NPC faction evidence has no sources')
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get('type'), str) \
                or not source['type'].strip() \
                or not any(isinstance(source.get(key), str) and source[key].strip()
                           for key in ('url', 'file')):
            raise ValueError('NPC faction evidence has an invalid source')
    result = {'names': {locale: name.strip() for locale, name in names.items()},
              'sources': [dict(source) for source in sources]}
    if 'factionID' in value:
        fid = value['factionID']
        if type(fid) is not int or fid <= 0:
            raise ValueError('NPC factionID must be a positive integer')
        result['factionID'] = fid
    return result


def merge_npc_faction_evidence(values):
    """Merge language observations of one NPC; contradictory evidence fails closed."""
    names, sources, fid = {}, [], None
    for value in values:
        record = _faction_evidence(value)
        observed_id = record.get('factionID')
        if fid is not None and observed_id is not None and fid != observed_id:
            raise ValueError('conflicting explicit NPC faction IDs')
        if observed_id is not None:
            fid = observed_id
        for locale, name in record['names'].items():
            if locale in names and names[locale] != name:
                raise ValueError('conflicting NPC faction names for locale %s' % locale)
            names[locale] = name
        for source in record['sources']:
            if source not in sources:
                sources.append(source)
    if not names:
        return None
    result = {'names': names, 'sources': sources}
    if fid is not None:
        result['factionID'] = fid
    return result


def build_npc_factions(info, faction_names=None, client_source=None, diagnostics=None):
    """Create optional affiliation metadata without changing CSV or A/H/N side."""
    records, messages = {}, diagnostics if diagnostics is not None else []
    for nid, npc in sorted(info.items()):
        observations = ([npc['faction']] if npc.get('faction') else []) + list(npc.get('factions') or [])
        if not observations:
            continue
        try:
            faction = merge_npc_faction_evidence(observations)
        except ValueError as error:
            # Missing evidence is a reported coverage gap. Contradictory valid
            # observations still raise rather than publishing one arbitrarily.
            if any(isinstance(value, dict) and not value.get('sources') for value in observations):
                messages.append({'npcID': nid, 'code': 'affiliation_missing_evidence',
                                 'message': str(error), 'severity': 'warning'})
                continue
            raise ValueError('NPC %s: %s' % (nid, error)) from error
        faction = faction or {}
        names = faction.get('names') or {}
        sources = faction.get('sources') or []
        if not names or not sources:
            continue
        client_matches = {(faction_names or {})[name]['factionID']
                          for name in names.values() if name in (faction_names or {})}
        if len(client_matches) > 1:
            raise ValueError('conflicting client faction names for NPC %s' % nid)
        match = next(((faction_names or {})[name] for name in names.values()
                      if name in (faction_names or {})), None)
        fid = faction.get('factionID')
        if match:
            if fid is not None and fid != match['factionID']:
                raise ValueError('tooltip/client faction ID conflict for NPC %s' % nid)
            names, fid = dict(names, **match['names']), match['factionID']
            sources = sources + ([client_source] if client_source else [])
        # Non-English collection cannot be relabeled as an English fallback.
        if not names.get('enUS'):
            messages.append({'npcID': nid, 'code': 'affiliation_missing_english',
                             'message': 'localized affiliation has no English comparison or client mapping',
                             'severity': 'warning'})
            continue
        record = {'names': names, 'sources': sources}
        if fid is not None:
            record['factionID'] = fid
        records[str(nid)] = record
    result = {'schemaVersion': 1, 'npcs': records}
    if diagnostics is None and messages:
        result['diagnostics'] = messages
    return result

class NpcNether:
    """NPC tooltip fields and explicit affiliation, independently of A/H/N.

    Every result has ``collectionStatus`` (ok/missing/error) and ``diagnostics``
    objects with code/message/severity/locale. A valid payload with no faction
    is ok; failed refreshes keep readable fields while reporting error. Cache
    maximum age uses the cached file's mtime; cache_only never performs HTTP.
    """

    def __init__(self, proxy=PROXY, refetch=False, locale='', cache_only=False,
                 max_age_days=0, cache_dir=None):
        if locale not in ('', 'enUS', 'zhCN', 'zhTW'):
            raise ValueError('unsupported NPC tooltip locale: %s' % locale)
        if not isinstance(max_age_days, (int, float)) or not math.isfinite(max_age_days) \
                or max_age_days < 0:
            raise ValueError('NPC cache maximum age must be a finite nonnegative number')
        if refetch and cache_only:
            raise ValueError('NPC cache-only mode cannot force refetch')
        self.cache_dir = cache_dir or os.path.join(CACHE, 'nether')
        self.refetch = refetch
        self.proxy = proxy
        self.locale = locale
        self.cache_only = cache_only
        self.max_age_days = max_age_days

    def _read_info(self, nid, locale, cache_only=None):
        cache_only = self.cache_only if cache_only is None else cache_only
        diagnostics = []

        def report(code, message, severity='warning'):
            diagnostics.append({'code': code, 'message': str(message), 'severity': severity,
                                'locale': locale or 'enUS'})

        # 缓存按语言分开，避免 zhCN 与英文互相污染
        suffix = '.' + locale if locale and locale != 'enUS' else ''
        p = os.path.join(self.cache_dir, '%d%s.json' % (nid, suffix))
        cached = load_cached(p, False)
        url = NETHER_NPC_URL % nid
        if locale:
            url += '?locale=' + locale
        stale = bool(cached is not None and self.max_age_days and os.path.isfile(p)
                     and time.time() - os.path.getmtime(p) > self.max_age_days * 86400)
        if stale:
            report('cache_expired', 'NPC cache exceeds maximum age')
        data, digest = None, None
        if cached is not None:
            try:
                data = json.loads(cached)
                if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not data['name'].strip():
                    raise ValueError('NPC payload has no nonempty name')
                # Preserve the hash of exact cached bytes, including CRLF, for
                # independently frozen source snapshots.
                if os.path.isfile(p):
                    with open(p, 'rb') as stream:
                        raw = stream.read()
                else:
                    raw = cached.encode('utf-8')
                normalized = raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
                if normalized != cached.replace('\r\n', '\n').replace('\r', '\n'):
                    raise ValueError('NPC cache changed while reading source bytes')
                digest = hashlib.sha256(raw).hexdigest()
            except (ValueError, OSError) as error:
                report('cache_invalid', error)
                data = None
        needs_fetch = data is None or stale or self.refetch
        failed = False
        if needs_fetch and not cache_only:
            try:
                fetched = http_json(url, proxy=self.proxy, timeout=25, retries=2)
                if not isinstance(fetched, dict) or not isinstance(fetched.get('name'), str) \
                        or not fetched['name'].strip():
                    raise ValueError('NPC request did not return a valid named payload')
                serialized = json.dumps(fetched, ensure_ascii=False)
                data = fetched
                digest = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
                try:
                    save(p, serialized)
                except OSError as error:
                    report('cache_write_failed', error, 'error')
                    failed = True
                if diagnostics:
                    report('request_recovered', 'valid NPC payload obtained after cache problem')
            except (ValueError, OSError) as error:
                report('request_failed', error, 'error')
                failed = True
        elif needs_fetch:
            report('cache_only_unavailable', 'no valid fresh NPC cache; network disabled', 'error')
            failed = True
        if data is None:
            return {'name': '', 'coords': [], 'diagnostics': diagnostics,
                    'collectionStatus': 'missing' if cached is None and cache_only else 'error'}
        result = {'name': data['name'].strip(), 'coords': [], 'diagnostics': diagnostics,
                  'collectionStatus': 'error' if failed else 'ok'}
        if failed:
            report('cache_fallback', 'preserving readable NPC fields after collection failure')
        m = data.get('map')
        if m is not None and not isinstance(m, dict):
            report('coordinates_invalid', 'NPC map is not an object')
            m = {}
        m = m or {}
        try:
            zone = m.get('zone')
            if zone is not None:
                if isinstance(zone, bool) or not re.fullmatch(r'[1-9]\d*', str(zone)):
                    raise ValueError('invalid NPC map zone')
                zone = int(zone)
                cd = m.get('coords') or {}
                if not isinstance(cd, dict):
                    raise ValueError('NPC map coordinates are not an object')
                for pairs in cd.values():
                    if not isinstance(pairs, list) or not pairs:
                        continue
                    try:
                        x, y = float(pairs[0][0]), float(pairs[0][1])
                        if not all(math.isfinite(value) and 0 <= value <= 100 for value in (x, y)):
                            raise ValueError('coordinates outside 0..100')
                        result['coords'].append((zone, round(x, 1), round(y, 1)))
                        break
                    except (TypeError, ValueError, IndexError) as error:
                        report('coordinates_invalid', error)
        except (TypeError, ValueError) as error:
            report('coordinates_invalid', error)
        try:
            faction = parse_npc_faction(data.get('tooltip'))
            if faction:
                affiliation = {'names': {locale or 'enUS': faction['name']},
                               'sources': [{'type': 'wowhead-npc-tooltip', 'url': url,
                                            'sha256': digest, 'locale': locale or 'enUS'}]}
                if faction.get('factionID'):
                    affiliation['factionID'] = faction['factionID']
                result['faction'] = affiliation
        except (TypeError, ValueError) as error:
            report('affiliation_invalid', error, 'error')
            result['collectionStatus'] = 'error'
        return result

    def _info(self, nid):
        result = self._read_info(nid, self.locale)
        if self.locale not in ('', 'enUS') and result.get('faction'):
            # A prior English observation can retain localized affiliations in
            # an offline replay. Do not issue an extra request implicitly.
            english_path = os.path.join(self.cache_dir, '%d.json' % nid)
            if os.path.isfile(english_path):
                english = self._read_info(nid, '', cache_only=True)
                if english.get('faction') and english['collectionStatus'] == 'ok':
                    try:
                        result['faction'] = merge_npc_faction_evidence(
                            [result['faction'], english['faction']])
                    except ValueError as error:
                        result.pop('faction', None)
                        result['collectionStatus'] = 'error'
                        result['diagnostics'].append({'code': 'affiliation_conflict',
                                                      'message': str(error), 'severity': 'error'})
                else:
                    result['diagnostics'].extend(english['diagnostics'])
        return result

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
    """Replay NPC observations or the schema-1 standalone affiliation JSON."""

    def __init__(self, path):
        with open(path, encoding='utf-8-sig') as stream:
            self.data = json.load(stream)
        if not isinstance(self.data, dict):
            raise ValueError('NPC JSON must be an object')
        self.factions_only = 'schemaVersion' in self.data
        if self.factions_only:
            if type(self.data.get('schemaVersion')) is not int or self.data['schemaVersion'] != 1 \
                    or not isinstance(self.data.get('npcs'), dict):
                raise ValueError('NPC affiliation JSON must use schemaVersion=1 with npcs object')
            self.data = self.data['npcs']

    def npc_info(self, npcs):
        out = {}
        for nid in npcs:
            e = self.data.get(str(nid)) or self.data.get(nid) or {}
            record = {'name': '', 'coords': [], 'collectionStatus': 'ok' if e else 'missing',
                      'diagnostics': []}
            out[nid] = record
            if not isinstance(e, dict):
                record['collectionStatus'] = 'error'
                record['diagnostics'].append({'code': 'json_invalid', 'message': 'NPC record is not an object',
                                               'severity': 'error'})
                continue
            if isinstance(e.get('name'), str):
                record['name'] = e['name'].strip()
            coords = e.get('coords') or []
            if not isinstance(coords, list):
                record['diagnostics'].append({'code': 'coordinates_invalid',
                                              'message': 'replayed NPC coordinates must be a list',
                                              'severity': 'warning'})
                coords = []
            for point in coords:
                try:
                    if not isinstance(point, (list, tuple)) or len(point) != 3:
                        raise ValueError('replayed NPC coordinate must contain zone,x,y')
                    zone, x, y = point
                    if isinstance(zone, bool) or not re.fullmatch(r'[1-9]\d*', str(zone)):
                        raise ValueError('invalid replayed NPC zone')
                    x, y = float(x), float(y)
                    if not all(math.isfinite(value) and 0 <= value <= 100 for value in (x, y)):
                        raise ValueError('replayed NPC coordinates outside 0..100')
                    record['coords'].append((int(zone), x, y))
                except (TypeError, ValueError) as error:
                    record['diagnostics'].append({'code': 'coordinates_invalid', 'message': str(error),
                                                  'severity': 'warning'})
            faction = e if self.factions_only and e else e.get('faction')
            if faction is not None:
                try:
                    record['faction'] = _faction_evidence(faction)
                except ValueError as error:
                    record['collectionStatus'] = 'error'
                    record['diagnostics'].append({'code': 'affiliation_invalid', 'message': str(error),
                                                  'severity': 'error'})
            if e.get('collectionStatus') in ('error', 'missing'):
                record['collectionStatus'] = e['collectionStatus']
            if isinstance(e.get('diagnostics'), list):
                record['diagnostics'].extend(e['diagnostics'])
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
    return NpcNether(proxy=args.proxy, refetch=args.refetch, locale=args.locale,
                     cache_only=getattr(args, 'npc_cache_only', False),
                     max_age_days=getattr(args, 'npc_max_age', 0))


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
    ap.add_argument('--npc-factions-out', default='',
                    help='可选：独立所属组织 JSON（不改写商人 CSV 或 A/H/N）')
    ap.add_argument('--faction-names-csv',
                    help='可选：客户端 Faction CSV 的精确 ID/三语名称映射')
    ap.add_argument('--npc-cache-only', action='store_true',
                    help='NPC 信息只读缓存，不发送请求；缺失/失效在诊断中报告')
    ap.add_argument('--npc-max-age', type=float, default=0,
                    help='NPC 缓存超过 N 天则刷新（0=永不；缓存模式仍报告失效）')
    ap.add_argument('--locale', default='', choices=['', 'enUS', 'zhCN', 'zhTW'],
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
    faction_names, faction_source = load_faction_names(args.faction_names_csv)

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

    diagnostics = []
    for nid, npc in sorted(info.items()):
        for message in npc.get('diagnostics') or []:
            diagnostics.append(dict(message, npcID=nid) if isinstance(message, dict)
                               else {'npcID': nid, 'message': str(message)})
    faction_output = (build_npc_factions(info, faction_names, faction_source, diagnostics)
                      if args.npc_factions_out else None)
    for message in diagnostics:
        log('  [npc] %s %s: %s' % (message.get('npcID', '?'), message.get('code', 'diagnostic'),
                                  message.get('message', '')))
    if faction_output is not None and diagnostics:
        faction_output['diagnostics'] = diagnostics
    if args.npc_factions_out and any(message.get('code') in
                                    ('affiliation_invalid', 'affiliation_conflict') for message in diagnostics):
        raise SystemExit('NPC affiliation evidence conflicts; no CSV/JSON output was published')

    # ── 产物（只写 CSV，不写 Lua） ──
    if not args.dry:
        if args.csv_out:
            emit_csv_vendors(vendors, npc_locale, args.csv_out)
        if args.npcs_out:
            emit_csv_npcs(spawns, npc_en, npc_locale, args.npcs_out)
        if args.npc_factions_out:
            save(os.path.abspath(args.npc_factions_out),
                 json.dumps(faction_output, ensure_ascii=False, indent=2) + '\n')
    else:
        log('--dry：跳过文件写入')

    log('完成：商人物品 %d / 空 %d / NPC %d / 无坐标 NPC %d'
        % (len(vendors), len(no_data), len(npcs), len(no_spawn)))


if __name__ == '__main__':
    main()
