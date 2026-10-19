# -*- coding: utf-8 -*-
"""BIS配装页 · 数据管线：抓 foreverchanges.pro 的 BiS 清单 → Core/Data/Data_BIS.lua。

一条命令跑完全链（抓取 → 解析 → 生成），产物**只存 ID + 结构**：
  物品名 / 图标 / 品质色 / 材料名 一律运行期由客户端给（GetItemInfo），本文件不落盘；
  客户端拿不到的兜底说明（来源备注 / 稀有 NPC 描述 / 附魔摘要）以文本形式跟在来源里。

抓取纪律（与 fc_fetch.py 同款）：站点是个人自建站，串行 + 0.8s 间隔 + 404 专精跳过。
专精覆盖随站点走：warrior×3 / paladin pve+tank / hunter pve+pvp / rogue pve+pvp /
priest pve / mage pve+pvp / warlock pve+pvp / druid pve+tank / shaman pve（2026-09-25 实测）。

★ 分卷（2026-10-03）：站点每个职业/专精只维护**一份**清单，等级上限一涨就整页换掉 ——
  等级切换是客户端的：URL 上没有等级参数（?lvl= / /20 都不认），旧等级页直接下线。
  所以 20级 卷只能读本地缓存离线复现（LEVELS 里 allow_net=False，永不联网）；
  30级 卷走现网抓取，缓存独立放 _fc_bis/cache30，互不覆盖。

用法：
    python _temp/fc_bis.py              # 20级读缓存 + 30级有缓存用缓存、缺的现抓
    python _temp/fc_bis.py --force      # 强制重抓允许联网的等级卷（30级）
    python _temp/fc_bis.py --offline    # 只用缓存，不联网（回归用）
    python _temp/fc_bis.py --level 20   # 只重建 20级 卷（纯离线）
"""
import argparse
import html as html_unescape_mod
import json
import os
import re
import subprocess
import sys
import time

BASE = 'https://foreverchanges.pro'
HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(os.path.dirname(HERE), 'Core', 'Data', 'Data_BIS.lua')

CLASSES = ['warrior', 'paladin', 'hunter', 'rogue', 'priest',
           'mage', 'warlock', 'druid', 'shaman']
# ★★★ 站点分类法（2026-10-16 实测重建，见 sitemap.xml）：
#   站点是「职业 / 细分专精」两级，**不是**「职业 × 场景」——
#   · 职业主页 = 该职业的某个默认专精（druid=野性、priest=暗影、shaman=元素、
#     mage=冰霜、paladin=惩戒、rogue=战斗、warrior=武器、hunter=射击、warlock=痛苦）；
#   · 其余专精走子路径（druid/balance、priest/holy、shaman/enhancement…）；
#   · PvP 页面命名不统一（warrior/pvp、paladin/holy-pvp、rogue/pvp-hemo、
#     priest/discipline-pvp）⇒ **绝不能按 url 规则拼**，必须逐页显式列出。
#   实测量：30级 38 页 / 20级 32 页（旧版按 cls+/pvp 规则只抓到 17 页）。
#
#   每页 = (站点路径, spec.id, tspec, 专精标签)
#     spec.id  ∈ pve / pvp / tank —— 界面顶部「类型」轴
#     tspec     = 天赋轴键，对应 BisUI.SPEC_DIR 的 key
#     key       = 站点路径，唯一标识；同 (id,tspec) 多页时（shockadin /
#                 pvp-hemo）靠它区分，界面按 key 精确取用
#   ⚠ 顺序即产出行序：同职业内按 pve → pvp → tank 分组，预设列表即自然分组。
PAGES = {
    30: [
        ('warrior',                'pve',  'arms',    '武器'),
        ('warrior/pvp',            'pvp',  'fury',    '狂暴'),
        ('warrior/tank',           'tank', 'prot',    '防战'),
        ('paladin',                'pve',  'ret',     '惩戒'),
        ('paladin/holy',           'pve',  'holy',    '神圣'),
        ('paladin/holy-pvp',       'pvp',  'holy',    '神圣'),
        ('paladin/retribution-pvp', 'pvp', 'ret',     '惩戒'),
        ('paladin/shockadin',      'pvp',  'holy',    '神圣震击'),
        ('paladin/tank',           'tank', 'prot',    '防护'),
        ('hunter',                 'pve',  'mm',      '射击'),
        ('hunter/pvp',             'pvp',  'surv',    '生存'),
        ('rogue',                  'pve',  'combat',  '战斗'),
        ('rogue/assassination',    'pve',  'assa',    '奇袭'),
        ('rogue/pvp',              'pvp',  'sub',     '敏锐'),
        ('rogue/pvp-hemo',         'pvp',  'sub',     '敏锐'),
        ('priest',                 'pve',  'shadow',  '暗牧'),
        ('priest/holy',            'pve',  'holy',    '神牧'),
        ('priest/discipline-pvp',  'pvp',  'disc',    '戒律'),
        ('priest/shadow-pvp',      'pvp',  'shadow',  '暗牧'),
        ('mage',                   'pve',  'frost',   '冰法'),
        ('mage/arcane',            'pve',  'arcane',  '奥法'),
        ('mage/fire',              'pve',  'fire',    '火法'),
        ('mage/fire-pvp',          'pvp',  'fire',    '火法'),
        ('mage/pvp',               'pvp',  'frost',   '冰法'),
        ('warlock',                'pve',  'affli',   '痛苦'),
        ('warlock/pvp',            'pvp',  'affli',   '痛苦'),
        ('druid',                  'pve',  'cat',     '猫德'),
        ('druid/balance',          'pve',  'balance', '鸟德'),
        ('druid/restoration',      'pve',  'resto',   '奶德'),
        ('druid/balance-pvp',      'pvp',  'balance', '鸟德'),
        ('druid/feral-pvp',        'pvp',  'cat',     '猫德'),
        ('druid/restoration-pvp',  'pvp',  'resto',   '奶德'),
        ('druid/tank',             'tank', 'bear',    '熊德'),
        ('shaman',                 'pve',  'ele',     '元素'),
        ('shaman/enhancement',     'pve',  'enh',     '增强'),
        ('shaman/restoration',     'pve',  'resto',   '奶萨'),
        ('shaman/elemental-pvp',   'pvp',  'ele',     '元素'),
        ('shaman/enhancement-pvp', 'pvp',  'enh',     '增强'),
    ],
    20: [
        ('warrior',                'pve',  'arms',    '武器'),
        ('warrior/pvp',            'pvp',  'fury',    '狂暴'),
        ('warrior/tank',           'tank', 'prot',    '防战'),
        ('paladin',                'pve',  'ret',     '惩戒'),
        ('paladin/holy',           'pve',  'holy',    '神圣'),
        ('paladin/holy-pvp',       'pvp',  'holy',    '神圣'),
        ('paladin/retribution-pvp', 'pvp', 'ret',     '惩戒'),
        ('paladin/shockadin',      'pvp',  'holy',    '神圣震击'),
        ('paladin/tank',           'tank', 'prot',    '防护'),
        ('hunter',                 'pve',  'mm',      '射击'),
        ('hunter/pvp',             'pvp',  'surv',    '生存'),
        ('rogue',                  'pve',  'combat',  '战斗'),
        ('rogue/pvp',              'pvp',  'sub',     '敏锐'),
        ('priest',                 'pve',  'shadow',  '暗牧'),
        ('priest/holy',            'pve',  'holy',    '神牧'),
        ('priest/discipline-pvp',  'pvp',  'disc',    '戒律'),
        ('priest/shadow-pvp',      'pvp',  'shadow',  '暗牧'),
        ('mage',                   'pve',  'frost',   '冰法'),
        ('mage/pvp',               'pvp',  'frost',   '冰法'),
        ('warlock',                'pve',  'affli',   '痛苦'),
        ('warlock/pvp',            'pvp',  'affli',   '痛苦'),
        ('druid',                  'pve',  'cat',     '猫德'),
        ('druid/balance',          'pve',  'balance', '鸟德'),
        ('druid/restoration',      'pve',  'resto',   '奶德'),
        ('druid/balance-pvp',      'pvp',  'balance', '鸟德'),
        ('druid/feral-pvp',        'pvp',  'cat',     '猫德'),
        ('druid/tank',             'tank', 'bear',    '熊德'),
        ('shaman',                 'pve',  'ele',     '元素'),
        ('shaman/enhancement',     'pve',  'enh',     '增强'),
        ('shaman/restoration',     'pve',  'resto',   '奶萨'),
        ('shaman/elemental-pvp',   'pvp',  'ele',     '元素'),
        ('shaman/enhancement-pvp', 'pvp',  'enh',     '增强'),
    ],
}

# ★ 分卷（2026-10-03 首版；2026-10-16 修正）：站点对 20级 另有
#   /zh-cn/bis/level-20/<path> 路由，**仍在线**（实测 HTTP 200 / 435KB），
#   旧注释「20级 页已下线、只能离线复现」已过时 ⇒ 两卷都可联网刷新。
LEVELS = [
    # (等级, 缓存目录, 是否允许联网)
    (20, os.path.join(HERE, '_fc_bis', 'cache20'), True),
    (30, os.path.join(HERE, '_fc_bis', 'cache30'), True),
]
DEFAULT_LEVEL = 30

# 产物级来源红线（与 AGENTS.md 同口径）：这些词出现即拒落盘
LEAK = ['站点', 'AtlasQuest', 'nfu', 'TalentsForever', '剥离', '照抄',
        '抄它', '抽取段', '上游', '出处', '参考', 'foreverchanges', 'ForeverChanges']

# 产物文本归一表：站点改文案时用来把红线词换回中性说法（见 lua_str）
# ★ 2026-10-07：站点「还不知道出处：如果你知道请告诉我们」是对站点读者的口吻，
#   进插件很怪 → 统一归一成中性「来源未知，欢迎补充」（须排在 出处→从哪里取得 前）
TEXT_FIXUPS = (('还不知道出处：如果你知道请告诉我们', '来源未知，欢迎补充'),
               ('还不知道出处： 如果你知道请告诉我们', '来源未知，欢迎补充'),
               ('还不知道从哪里取得：如果你知道请告诉我们', '来源未知，欢迎补充'),
               ('还不知道从哪里取得： 如果你知道请告诉我们', '来源未知，欢迎补充'),
               ('出处', '从哪里取得'))

# ── 来源备注汉化（2026-10-07）：站点 zh 页的来源里混着英文任务/NPC/区域名 ──
# 任务名 93 个来自 nether.wowhead classic/cn tooltip（官方经典旧世译名），
# NPC 名 15 个来自同源（含 wotlk 库的 Archmage Alvareaux），区域名内置官方译名。
# Forever 自定义内容（图书馆系列任务、Alynsia/Gezzy 等新军需官）站点与 wowhead
# 均无中文名，保留英文原文。
ZH_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_fc_bis', 'name_zh.json')
ZONES = {
    'Redridge Mountains': '赤脊山', 'The Barrens': '贫瘠之地', 'Ashenvale': '灰谷',
    'Stonetalon Mountains': '石爪山脉', 'Dun Morogh': '丹莫罗', 'Orgrimmar': '奥格瑞玛',
    'Silverpine Forest': '银松森林', 'Darnassus': '达纳苏斯', 'Thunder Bluff': '雷霆崖',
    'Stranglethorn Vale': '荆棘谷', 'Burning Steppes': '燃烧平原', 'Wetlands': '湿地',
    'Alterac Mountains': '奥特兰克山脉', 'Mulgore': '莫高雷', 'Loch Modan': '洛克莫丹',
    'Arathi Highlands': '阿拉希高地', 'Duskwood': '暮色森林', 'Stormwind City': '暴风城',
    'Ironforge': '铁炉堡', 'Undercity': '幽暗城',
}

try:
    _ZH_RAW = json.load(open(ZH_MAP_PATH, encoding='utf-8'))
except Exception:
    _ZH_RAW = {'quests': {}, 'names': {}}
# key 可能带站点尾缀（「Greater Friend of the Library，30级起」）或 HTML 实体
# （Agmond&#x27;s）→ 展开成纯名字形式，统一进替换表；带尾缀的 key 其值要拼回
# 尾缀（值是纯任务名，直接替换会吞掉「，30级起」这类尾缀）
_ZH_NAMES = {}
for _k, _v in _ZH_RAW['quests'].items():
    _k = html_unescape_mod.unescape(_k).strip()
    _k = re.sub(r'^任务[:：]\s*', '', _k)
    if '，' in _k:
        _name, _rest = _k.split('，', 1)
        _name, _rest = _name.strip(), _rest.strip()
        if _name:
            _ZH_NAMES[_name] = _v
            if _rest:
                _ZH_NAMES[_k] = _v + '，' + _rest
    else:
        _ZH_NAMES[_k] = _v
for _k, _v in _ZH_RAW['names'].items():
    _ZH_NAMES[html_unescape_mod.unescape(_k).strip()] = _v
_ZH_NAMES.update(ZONES)
# 最长优先替换，避免「Greater Friend of the Library」吃掉「…，30级起」前的同前缀名
_ZH_ORDERED = sorted(_ZH_NAMES.items(), key=lambda kv: -len(kv[0]))


def zh_note(s):
    for en, zh in _ZH_ORDERED:
        if en in s:
            s = s.replace(en, zh)
    return s

SLEEP = 0.8
PROXY = 'http://127.0.0.1:7897'


def die(msg):
    sys.stderr.write('fc_bis: %s\n' % msg)
    sys.exit(1)


# ── ① 抓取 ──────────────────────────────────────────────────────────────────

def fetch(url, dst, force, offline, allow_net=True):
    if not allow_net:
        # 已下线的等级卷：只认本地缓存，永不联网、永不删缓存
        return 'cached' if (os.path.exists(dst) and os.path.getsize(dst) > 20000) else 'missing'
    # ★ force 必须先于缓存命中判断（2026-10-07 实锤：--force 此前是空操作，
    #   缓存命中直接 return，站点补了来源也永远拿不到）
    if not force and os.path.exists(dst) and os.path.getsize(dst) > 20000:
        return 'cached'
    if offline:
        return 'missing'
    # ★ 必须走 curl_cffi（Chrome 指纹）：裸 curl 的 TLS 指纹会被服务器判别，
    #   缓存未命中的子页稳定回 200 空体（基页有 CDN 缓存才侥幸能拿）。
    #   7897 = 本机 Clash Verge 混合端口（wowhead 同款约定）。
    # ★ 2026-10-16：代理链路会整段失效（实测 `BoringSSL SSL_connect: Connection
    #   closed abruptly` / exit 35，而直连 200 正常）⇒ 逐个尝试
    #   [代理, 直连]，任一通即用；全失败才算失败。
    try:
        from curl_cffi import requests as cr
    except ImportError:
        die('需要 curl_cffi：venv 未安装（pip install curl_cffi）')
    routes = [{'http': PROXY, 'https': PROXY}, None]
    last = ''
    for i in range(4):
        time.sleep(1.5 * (i + 1))
        r = None
        proxies = routes[min(i, len(routes) - 1)]
        try:
            r = cr.get(url, impersonate='chrome', timeout=60, proxies=proxies)
        except Exception as e:
            last = 'exc %s' % str(e)[:80]
            continue
        if r.status_code == 404:
            return '404'
        if r.status_code == 200 and len(r.content) > 20000:
            open(dst, 'wb').write(r.content)
            return 'ok %d' % len(r.content)
        last = 'HTTP %s size %d' % (r.status_code, len(r.content))
    if os.path.exists(dst):
        os.remove(dst)
    print('  ! 抓取失败 %s（%s）' % (url, last))
    return 'fail'


# ── ② 解析 ──────────────────────────────────────────────────────────────────

def clean(s):
    """去标签、去空白、HTML 实体全量解码。"""
    import html as _html
    s = re.sub(r'<[^>]+>', '', s)
    s = _html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def tip_id(tip):
    """data-tip → 真实物品ID（字符串）。
    ★ 站点 2026-10 改版后部分 tip 变成「基础物品ID + 5位变体号」拼接
      （如 14210+12727=1421012727；/zh-cn/item/14210 = 活力斗篷基础页，
      12727 是无关物品 → 尾段不是 ID）。本库物品 ID ≤ 6 位，≥9 位的
      tip 必为拼接：尾段恰为 12xxx/13xxx 且前缀 3-6 位才拆，防误伤。"""
    if len(tip) >= 9:
        prefix, suffix = tip[:-5], tip[-5:]
        if suffix.startswith('1') and 12000 <= int(suffix) < 14000 \
                and 100 <= int(prefix) <= 999999:
            return prefix
    return tip


def lua_str(s):
    # ① 来源备注汉化：英文任务名/NPC 名/区域名 → 官方中文译名（zh_note，2026-10-07）
    s = zh_note(s)
    # ★ 产物级文本归一（站点文案随版本改写，红线词必须换成中性说法）：
    #   2026-10-03：30级 页把「还不知道从哪里取得」改写成「还不知道出处」，
    #   命中产物红线词「出处」⇒ 统一回中性说法（与 20级 卷口径一致）。
    for a, b in TEXT_FIXUPS:
        s = s.replace(a, b)
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')


def parse_from(link_text, href, span):
    """bis-from 的 <a>+<span> → 结构化来源 dict（纯 ID / 通用词 / 兜底说明文本）。"""
    src, unc = {}, False
    if span:
        if '未经确认' in span:
            unc = True
            span = clean(span.replace('玩家反馈，未经确认', ''))
        else:
            span = clean(span)
        if span in ('', '玩家反馈，未经确认'):
            span = ''
        else:
            span = span.rstrip('、，,')   # 「20级起、」这类尾部悬空顿号
    if not href:
        src = {'t': 'other', 'note': clean(link_text) or span or ''}
    elif '/quest=' in href:
        m = re.search(r'quest=(\d+)', href)
        src = {'t': 'quest', 'q': m.group(1) if m else None, 'note': span}
    elif '/dungeons/' in href:
        slug = href.split('/dungeons/')[-1].split('#')[0]
        anchor = href.split('#')[1] if '#' in href else ''
        # 锚点 quest-N = 副本内任务（文本「任务：英文名」，questID 就在锚点里）
        qm = re.match(r'quest-(\d+)', anchor)
        if qm:
            src = {'t': 'quest', 'q': qm.group(1), 'ref': slug.replace('-', '_'),
                   'note': span}
        else:
            dung, boss = '', ''
            if '，' in link_text:
                boss, _, dung = link_text.rpartition('，')
                boss, dung = clean(boss), clean(dung)
            else:
                dung = clean(link_text)
            # span 是掉率说明，清掉尾部悬空顿号
            src = {'t': 'boss', 'dung': dung, 'boss': boss,
                   'ref': slug.replace('-', '_'),
                   'rate': span.rstrip('、，,') if span else ''}
    elif '/professions/' in href:
        slug = href.split('/professions/')[-1].split('#')[0]
        lvl = None
        m = re.search(r'（(\d+)）', link_text)
        if m:
            lvl = int(m.group(1))
        src = {'t': 'craft', 'prof': slug, 'lvl': lvl, 'note': span}
    elif href.endswith('/rares'):
        src = {'t': 'rare', 'note': clean(link_text)}
    elif href.endswith('/library-books'):
        src = {'t': 'books', 'note': clean(link_text)}
    else:
        src = {'t': 'other', 'note': clean(link_text) or span or ''}
    if span and 'note' in src and not src['note']:
        src['note'] = span
    for k in [k for k in src if src[k] in (None, '')]:
        del src[k]
    return src, unc


def parse_row(li):
    """单个 <li class="bis-row"> → dict。"""
    row = {}
    # ★ 物品 ID 优先取名字链接的 href（站点 2026-10 起 data-tip 有拼接污染）
    m = re.search(r'class="bis-name[^"]*"\s+href="/zh-cn/item/(\d+)"', li)
    if not m:
        m = re.search(r'data-tip="(\d+)"', li)
    if not m:
        return None
    row['item'] = int(tip_id(m.group(1)))
    m = re.search(r'bis-name q(\d)', li) or re.search(r'bq(\d)', li)
    row['q'] = int(m.group(1)) if m else 1
    m = re.search(r'data-item-side="([ah])"', li)
    row['side'] = m.group(1) if m else None
    fm = re.search(r'<div class="bis-from"><p>(?:<a href="([^"]*)"[^>]*>(.*?)</a>)?(.*?)</p></div>', li, re.S)
    if fm:
        span_m = re.search(r'<span>(.*?)</span>', fm.group(3), re.S)
        span = span_m.group(1) if span_m else ''
        span = re.sub(r'<[^>]+>', '', span)
        link_text = fm.group(2) or ''
        if not link_text:
            # ★ 无链接的纯文本来源（2026-10-07 实锤：站点把「世界掉落，可在
            #   拍卖行购买」「任务：X」写成 <p><b>文本</b></p>，无 <a> 无 <span>
            #   ——此前整段被丢弃，产出 src={t="other"} 空说明）。整段（去
            #   span、去标签）就是来源说明。
            rest = re.sub(r'<span>.*?</span>', '', fm.group(3), flags=re.S)
            rest = re.sub(r'<[^>]+>', ' ', rest)
            link_text = re.sub(r'\s+', ' ', rest).strip(' 、，,')
        src, unc = parse_from(link_text, fm.group(1) or '', span)
        row['src'] = src
        if unc:
            row['unc'] = True
    mats = []
    for mm in re.finditer(r'<span class="bis-mat([^"]*)" data-tip="(\d+)">.*?(?:<b>(\d+)</b>)?</span>', li, re.S):
        if 'bis-mat-recipe' in mm.group(1):
            row['recipe'] = int(tip_id(mm.group(2)))
        else:
            n = int(mm.group(3)) if mm.group(3) else 1
            mats.append([int(tip_id(mm.group(2))), n])
    if mats:
        row['mats'] = mats
    return row


def parse_page(html):
    """一页 → {slots:{...}, rows:{...}}。slots 键 = 部位锚点名。"""
    spec = {'slots': {}, 'rows': {}}

    # 人偶区：bis-doll 里的 cell（防具 14 格）
    doll = re.search(r'<section class="bis-doll".*?</section>', html, re.S)
    if not doll:
        die('找不到 bis-doll 段')
    dhtml = doll.group(0)
    seen = {}          # finger/trinket 各出现两次（双戒指/双饰品是独立两格）：2nd → 键+"2"
    for cm in re.finditer(r'<a class="bis-cell" href="#slot-([a-z0-9-]+)">(.*?)</a>', dhtml, re.S):
        key, chtml = cm.group(1), cm.group(2)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = '%s%d' % (key, seen[key])
        slots = [None, None]
        for im in re.finditer(r'<span class="bis-cell-item([^"]*)" data-for="([ah])"(?: data-tip="(\d+)")?>(.*?)</span></span>', chtml, re.S):
            side = im.group(2)
            idx = 0 if side == 'a' else 1
            if not im.group(3):
                continue
            qm = re.search(r'bq(\d)', im.group(4)) or re.search(r'class="q(\d)"', im.group(4))
            ench = None
            em = re.search(r'bis-cell-enchant(?! bis-cell-noenchant)[^>]*>([^<]*)<', im.group(4))
            if em:
                ench = clean(em.group(1))
            slots[idx] = {'item': int(tip_id(im.group(3))), 'q': int(qm.group(1)) if qm else 1,
                          'ench': ench}
        spec['slots'][key] = slots
        spec['rows'].setdefault(key, [])

    # 武器区：bis-weapons 里的 3 格（主手 / 副手 / 远程）
    wm = re.search(r'<div class="bis-weapons">(.*?)</div></section>', dhtml, re.S)
    if wm:
        for cm in re.finditer(r'<span class="bis-cell-item([^"]*)" data-for="([ah])"(?: data-tip="(\d+)")?>(.*?)</span></span>', wm.group(1), re.S):
            hrefm = re.search(r'href="#slot-([a-z0-9-]+)"', cm.group(4))
            key = hrefm.group(1) if hrefm else None
            if not key or not cm.group(3):
                continue
            side = cm.group(2)
            idx = 0 if side == 'a' else 1
            qm = re.search(r'bq(\d)', cm.group(4)) or re.search(r'class="q(\d)"', cm.group(4))
            ench = None
            em = re.search(r'bis-cell-enchant(?! bis-cell-noenchant)[^>]*>([^<]*)<', cm.group(4))
            if em:
                ench = clean(em.group(1))
            spec['slots'].setdefault(key, [None, None])
            spec['slots'][key][idx] = {'item': int(tip_id(cm.group(3))), 'q': int(qm.group(1)) if qm else 1,
                                       'ench': ench}

    # 部位详情区：逐 section 的排名 rows
    # ★ li 标签可能带属性（如 <li class="bis-row" data-item-side="a">），
    #   正则必须容忍标签属性，否则阵营限定行整行丢失（2026-09-25 用户反馈：腿部空）
    for sm in re.finditer(r'<section class="bis-slot" id="slot-([a-z0-9-]+)">(.*?)</section>', html, re.S):
        key, shtml = sm.group(1), sm.group(2)
        rows = []
        for lm in re.finditer(r'<li class="bis-row([^"]*)"([^>]*)>(.*?)</li>', shtml, re.S):
            row = parse_row(lm.group(3))
            if row:
                sam = re.search(r'data-item-side="([ah])"', lm.group(2))
                if sam and not row.get('side'):
                    row['side'] = sam.group(1)
                rows.append(row)
        spec['rows'][key] = rows

    # 附魔区：id="enchants" 的 bis-enchant-row 列表（每专精独立；公式物品 = 附魔来源）
    enchs = []
    em = re.search(r'<section[^>]*id="enchants">.*?</ol>', html, re.S)
    if em:
        for li in re.finditer(r'<li class="bis-row bis-enchant-row">(.*?)</li>',
                              em.group(0), re.S):
            b = li.group(1)
            sm = re.search(r'bis-enchant-slots">([^<]+)</small>', b)
            fm = re.search(r'<div class="bis-from"><p><a href="/zh-cn/item/(\d+)"', b)
            # 「向训练师学习」的附魔没有公式物品（bis-from 里是 <b>附魔名</b> 纯文本），
            # 不再整行丢弃：item=None，选中令牌退化为 eff 文本（2026-09-25 用户反馈：
            # 胸部/手腕/手部/脚 等栏此前因此整栏缺附魔）。
            gm = re.search(r'<p class="bis-enchant-line">([^<]+)</p>', b)
            if not sm or not (fm or gm):
                continue
            # eff = 加成文本（bis-enchant-line，如「附魔：力量 +5」→ 存「力量 +5」）
            eff = ''
            if gm:
                eff = re.sub(r'^\s*附魔[:：]\s*', '', clean(gm.group(1)))
            lm = re.search(r'（附魔 (\d+)）', b)
            # 训练师附魔行无公式物品，附魔名只在 <b>纯文本</b> 里 → 存 name 兜底
            nm = None
            if not fm:
                bm = re.search(r'<div class="bis-from"><p><b>([^<]+)</b>', b)
                if bm:
                    nm = clean(bm.group(1))
            # note = from 段去公式锚点与（附魔 N）后的余文
            note = ''
            pm = re.search(r'<div class="bis-from"><p>(.*?)</p></div>', b, re.S)
            if pm:
                seg = re.sub(r'<a[^>]*>.*?</a>', '', pm.group(1), flags=re.S)
                seg = re.sub(r'<!--.*?-->', '', seg, flags=re.S)
                # 训练师附魔行无公式锚点，但 <b>附魔名</b> 是行的主名，也不进 note
                seg = re.sub(r'^\s*<b>.*?</b>\s*', '', seg, flags=re.S)
                seg = re.sub(r'^\s*（附魔 \d+）', '', clean(seg))
                note = seg
            mats = []
            for mm in re.finditer(r'<span class="bis-mat([^"]*)" data-tip="(\d+)">.*?(?:<b>(\d+)</b>)?</span>', b, re.S):
                if 'bis-mat-recipe' in mm.group(1):
                    continue
                mats.append([int(mm.group(2)),
                             int(mm.group(3)) if mm.group(3) else 1])
            enchs.append({'slot': clean(sm.group(1)),
                          'item': int(fm.group(1)) if fm else None,
                          'lvl': int(lm.group(1)) if lm else None,
                          'eff': eff or None,
                          'name': nm,
                          'note': note, 'mats': mats})
    spec['enchs'] = enchs
    return spec


# ── ②.5 自有掉落库交叉补源 ──────────────────────────────────────────────────
# 站点自己也不知道来源的行（2026-10-07 战士页就有几十条），先查**自家**
# Data_DungeonLoot.lua（掉落明细）能不能兜住：能兜住就补成结构化 boss 来源。

LOOT_LUA = os.path.join(os.path.dirname(DST), 'Data_DungeonLoot.lua')
DUNGEON_LUA = os.path.join(os.path.dirname(DST), 'Data_Dungeons.lua')
DUNGEON_NAMES = {}     # 副本id → 中文名（Data_Dungeons.lua）
LOOT_INDEX = {}        # itemID → (副本id, 首领中文名)（同件多首领取首见）


def load_own_loot():
    """读自有掉落库 + 副本名表。读不到只警告不致命（补源是增益不是依赖）。"""
    global DUNGEON_NAMES, LOOT_INDEX
    try:
        DUNGEON_NAMES = dict(re.findall(
            r'id = "([a-z_]+)",\s*name = "([^"]+)"',
            open(DUNGEON_LUA, encoding='utf-8').read()))
        dung = boss = None
        for line in open(LOOT_LUA, encoding='utf-8'):
            m = re.match(r'\s*\["([a-z_]+)"\] = \{', line)
            if m:
                dung, boss = m.group(1), None
                continue
            # 首领行：{ "英文名", "中文名", "附加说明", "NPC id", { 物品表
            m = re.match(r'\s*\{ "[^"]*", "([^"]*)", "[^"]*", "[^"]*", \{', line)
            if m:
                boss = m.group(1)
                continue
            # 物品行：{ itemID, 掉率|nil, 无限版新增 },?$
            m = re.match(r'\s*\{ (\d+), (?:nil|\d+), (?:true|false) \},?\s*$', line)
            if m and dung and boss:
                LOOT_INDEX.setdefault(int(m.group(1)), (dung, boss))
    except OSError as e:
        print('  ! 自有掉落库读取失败，跳过交叉补源：%s' % e)
        return False
    print('  自有掉落库：%d 副本名 / %d 物品映射' % (len(DUNGEON_NAMES), len(LOOT_INDEX)))
    return bool(LOOT_INDEX)


def fill_from_loot(spec):
    """站点未知来源的行 → 查自有掉落库补成结构化 boss 来源，返回补了多少条。
    只动「真不知道」的行：src 空，或 t=other 且无说明 / 说明含「还不知道」；
    「任务：X」「精英，24级起」这类有线索的 other 不覆盖。"""
    n = 0
    for rows in spec['rows'].values():
        for r in rows:
            src = r.get('src') or {}
            t, note = src.get('t'), src.get('note') or ''
            if t == 'other':
                unknown = (not note) or ('还不知道' in note)
            else:
                unknown = not t and not note
            if not unknown:
                continue
            hit = LOOT_INDEX.get(r['item'])
            if not hit:
                continue
            dung_id, boss_cn = hit
            r['src'] = {'t': 'boss', 'dung': DUNGEON_NAMES.get(dung_id, dung_id),
                        'boss': boss_cn, 'ref': dung_id}
            r.pop('unc', None)   # 自有掉落库是已公布数据，不再挂「未经确认」
            n += 1
    return n


# ── ③ 生成 ──────────────────────────────────────────────────────────────────

def fmt_slots(slots):
    parts = []
    for key in sorted(slots):
        sides = slots[key]
        cells = []
        for s in sides:
            if not s:
                cells.append('nil')
            elif s['ench']:
                cells.append('{%d,%d,%s}' % (s['item'], s['q'], lua_str(s['ench'])))
            else:
                cells.append('{%d,%d}' % (s['item'], s['q']))
        parts.append('[%s]={%s}' % (lua_str(key), ','.join(cells)))
    return '{%s}' % ','.join(parts)


def fmt_src(src):
    parts = ['t=%s' % lua_str(src['t'])]
    for k, v in src.items():
        if k == 't':
            continue
        if isinstance(v, str):
            parts.append('%s=%s' % (k, lua_str(v)))
        else:
            parts.append('%s=%s' % (k, v))
    return '{%s}' % ','.join(parts)


def fmt_row(r):
    parts = ['item=%d' % r['item'], 'q=%d' % r['q']]
    if r.get('side'):
        parts.append('side=%s' % lua_str(r['side']))
    if r.get('src'):
        parts.append('src=%s' % fmt_src(r['src']))
    if r.get('unc'):
        parts.append('unc=true')
    if r.get('mats'):
        parts.append('mats={%s}' % ','.join('{%d,%d}' % (a, b) for a, b in r['mats']))
    if r.get('recipe'):
        parts.append('recipe=%d' % r['recipe'])
    return '{%s}' % ','.join(parts)


def fmt_rows(rows):
    parts = []
    for key in sorted(rows):
        rl = rows[key]
        body = ','.join(fmt_row(r) for r in rl)
        parts.append('[%s]={%s}' % (lua_str(key), body))
    return '{%s}' % ','.join(parts)


def fmt_enchs(enchs):
    parts = []
    for e in enchs:
        p = ['slot=%s' % lua_str(e['slot'])]
        if e.get('item'):
            p.append('item=%d' % e['item'])
        if e.get('lvl'):
            p.append('lvl=%d' % e['lvl'])
        if e.get('eff'):
            p.append('eff=%s' % lua_str(e['eff']))
        if e.get('name'):
            p.append('name=%s' % lua_str(e['name']))
        if e.get('note'):
            p.append('note=%s' % lua_str(e['note']))
        if e.get('mats'):
            p.append('mats={%s}' % ','.join('{%d,%d}' % (a, b2)
                                            for a, b2 in e['mats']))
        parts.append('{%s}' % ','.join(p))
    return '{%s}' % ','.join(parts)


def fmt_spec(spec):
    s = 'slots=%s,rows=%s' % (fmt_slots(spec['slots']), fmt_rows(spec['rows']))
    if spec.get('enchs'):
        s += ',enchs=%s' % fmt_enchs(spec['enchs'])
    return s


HEAD = 'local _, ns = ...'


def build_classes(cls_list, ind):
    out = []
    for cls in cls_list:
        out.append('%s{ slug = %s, specs = {\n' % (ind, lua_str(cls['slug'])))
        for spec in cls['specs']:
            out.append('%s    { id = %s, tspec = %s, label = %s, key = %s, %s },\n'
                       % (ind, lua_str(spec['id']), lua_str(spec['tspec']),
                          lua_str(spec['label']), lua_str(spec['key']),
                          fmt_spec(spec)))
        out.append('%s} },\n' % ind)
    return ''.join(out)


def build_lua(vols):
    """vols = [(等级, {updated, classes}), ...]（按等级升序）。"""
    out = [HEAD]
    out.append('ns.EnsureBISData = function()\n')
    out.append('if ns.BIS then return ns.BIS end\n')
    out.append('ns.BIS = {\n    updated = %s,\n    default = %d,\n    levels = {\n'
               % (lua_str(vols[-1][1]['updated']), DEFAULT_LEVEL))
    for lv, data in vols:
        out.append('        [%d] = {\n            updated = %s,\n            classes = {\n'
                   % (lv, lua_str(data['updated'])))
        out.append(build_classes(data['classes'], ' ' * 16))
        out.append('            },\n        },\n')
    out.append('    },\n}\n')
    # ★ 运行期别名：界面层 ClassRec() 仍读 ns.BIS.classes，零改动即可兼容
    out.append('ns.BIS.classes = ns.BIS.levels[ns.BIS.default].classes\n')
    out.append('return ns.BIS\nend\n')
    return ''.join(out)


# ── 主流程 ──────────────────────────────────────────────────────────────────

def collect_level(lv, cache_dir, allow_net, args):
    """抓取（或读缓存）某一等级卷的全部「站点页面」→ {'updated', 'classes'}。

    页面清单来自 PAGES[lv]（显式逐页，不按 URL 规则拼）；产物里 spec 记录带
    tspec（天赋轴），同 id 下可多条（如 shaman pve 的 ele/enh/resto）。"""
    os.makedirs(cache_dir, exist_ok=True)
    print('── %d级卷 ──（缓存 %s）' % (lv, cache_dir))
    data = {'updated': time.strftime('%Y-%m-%d'), 'classes': []}
    n_spec = 0
    filled = 0

    todo = list(PAGES.get(lv) or [])
    gotten = {}          # path(站点路径) -> 本地缓存文件
    fails = []
    for rnd in range(3):
        fails = []
        for path_key, _sid, _tsp, _lbl in todo:
            fname = path_key.replace('/', '_') + '.html'
            dst = os.path.join(cache_dir, fname)
            url = '%s/zh-cn/bis/%s%s' % (BASE, '' if lv == 30 else 'level-%d/' % lv,
                                         path_key)
            status = fetch(url, dst, args.force and rnd == 0, args.offline,
                           allow_net=allow_net)
            if status == '404':
                print('  %s 无此页面，跳过' % path_key)
                continue
            if status in ('missing', 'fail'):
                fails.append((path_key, _sid, _tsp, _lbl))
                continue
            gotten[path_key] = dst
        if not fails or args.offline or not allow_net or not gotten:
            break
        # 连续抓取会被软拒（200 空体）：拉开 30s 再补漏
        print('  %d 页未抓到，等 30s 补漏（第 %d 轮）' % (len(fails), rnd + 2))
        time.sleep(30)
        todo = fails
    for pk, _s, _t, _l in fails:
        print('  ! %s 始终未抓到，跳过' % pk)

    by_cls = {}          # slug -> [spec, ...]（保持 PAGES 顺序）
    for path_key, spec_id, tspec, label in PAGES.get(lv) or []:
        dst = gotten.get(path_key)
        if not dst:
            continue
        cls = path_key.split('/')[0]
        html = open(dst, encoding='utf-8', errors='replace').read()
        spec = parse_page(html)
        if not spec['slots'] or not spec['rows']:
            die('%s级 %s 解析结果为空' % (lv, path_key))
        if LOOT_INDEX:
            filled += fill_from_loot(spec)
        rec = {'id': spec_id, 'tspec': tspec, 'label': label,
               'key': path_key, **spec}
        by_cls.setdefault(cls, []).append(rec)
        n_spec += 1
        n_rows = sum(len(v) for v in spec['rows'].values())
        print('  %-26s %-4s/%-7s %d 部位 / %d 条备选'
              % (path_key, spec_id, tspec, len(spec['slots']), n_rows))

    for cls in CLASSES:
        specs = by_cls.get(cls)
        if specs:
            data['classes'].append({'slug': cls, 'specs': specs})

    if not data['classes']:
        die('%d级卷一个专精都没解析出来（缓存为空且未联网）' % lv)
    print('  %d级卷：%d 职业 / %d 方案页 / 交叉补源 %d 条'
          % (lv, len(data['classes']), n_spec, filled))
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='无视缓存强制重抓（只对允许联网的等级卷生效）')
    ap.add_argument('--offline', action='store_true', help='只用缓存，不联网')
    ap.add_argument('--level', type=int, action='append',
                    help='只处理指定等级卷（可重复；缺省全部分卷）')
    args = ap.parse_args()

    load_own_loot()
    vols = []
    for lv, cache_dir, allow_net in LEVELS:
        if args.level and lv not in args.level:
            continue
        vols.append((lv, collect_level(lv, cache_dir, allow_net, args)))
    if not vols:
        die('没有可处理的分卷')

    lua = build_lua(vols)
    for w in LEAK:
        if w in lua:
            k = lua.find(w)
            die('产物命中来源红线关键词「%s」：%s' % (w, lua[max(0, k - 40):k + 40]))

    if os.path.exists(DST):
        old = open(DST, encoding='utf-8').read()
        if old == lua:
            print('[SAME] %s 内容无变化' % DST)
            return
        tag = '[SYNC]'
    else:
        tag = '[NEW]'
    open(DST, 'w', encoding='utf-8', newline='\n').write(lua)
    print('%s 已生成 %s（%d KB）' % (tag, DST, len(lua.encode('utf-8')) // 1024))


if __name__ == '__main__':
    main()
