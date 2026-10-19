# -*- coding: utf-8 -*-
"""生成 117 个新坐骑条目并追加到 Core/Data/Data_CollectionMounts.lua

数据源（全部 2026-10-07 抓自 wowhead /forever/cn）：
- _temp/_wh_mounts_items.json      物品分类页 listviewitems（id/名/modelviewer.displayid）
- _temp/_wh_mount_item_pages.json  逐物品页（og:image 图标 + sold-by/dropped-by 来源）
- _temp/_wh_mount_fixups.json      导航补漏 displayid（可为空）
- nether tooltip 兜底图标：23193 / 23720（物品页被 CloudFront 封锁）

规则：
- group：sold-by → "rep"（沿用既有商人条目口径）；掉落/无来源 → "unknown"
- details：商人：<名> · 售价 <金级格式> ／ 掉落：<boss>（<区域>）／ wowhead 暂未收录获取方式
- 名字与坐标不落盘（与头注纪律一致）；cam 不写（待实机校准）
"""
import json, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = 'Core/Data/Data_CollectionMounts.lua'
ITEMS = json.load(open('_temp/_wh_mounts_items.json', encoding='utf-8'))
PAGES = json.load(open('_temp/_wh_mount_item_pages.json', encoding='utf-8'))
try:
    FIXUPS = json.load(open('_temp/_wh_mount_fixups.json', encoding='utf-8'))
except FileNotFoundError:
    FIXUPS = {'nav': {}}

EXISTING = {280611, 280544, 277718, 269681, 269683, 274930, 269671, 269678, 274933,
            262766, 274706, 276063, 265839, 265838, 265840, 274799, 269682, 269673,
            277960, 275993, 46102}
# 物品页被 CloudFront 封锁 → nether tooltip 服务兜底图标（2026-10-07 实测）
NETHER_ICONS = {23193: 'ability_mount_undeadhorse', 23720: 'ability_hunter_pet_turtle'}

ZONE_NAMES = {721: '诺莫瑞根', 1977: '祖尔格拉布', 3428: '安其拉废墟'}


def money_str(copper):
    g, rem = divmod(copper, 10000)
    s, c = divmod(rem, 100)
    parts = []
    if g:
        parts.append('%d金' % g)
    if s:
        parts.append('%d银' % s)
    if c:
        parts.append('%d铜' % c)
    return ''.join(parts) or '0铜'


def vendor_details(rows):
    names = []
    for s in rows:
        nm = (s.get('name') or '').strip()
        nm = nm.strip('[]')  # wowhead 未本地化 NPC 的 [英文] 兜底
        if nm and nm not in names:
            names.append(nm)
    shown = ' / '.join(names[:2])
    if len(names) > 2:
        shown += ' 等'
    # 价格取各行最低（多处商人折扣不同时以最低为准）
    best = None
    item_cost = None
    for s in rows:
        c = s.get('cost')
        if not c:
            continue
        row = c[0] if isinstance(c[0], list) else c
        if not isinstance(row, list):
            continue
        money = row[0] if isinstance(row[0], (int, float)) else 0
        extras = row[2] if len(row) > 2 else []
        if extras:
            it = extras[0]
            if isinstance(it, list) and len(it) >= 2:
                item_cost = (it[0], it[1])
        elif isinstance(money, (int, float)) and money > 0:
            if best is None or money < best:
                best = money
    if item_cost:
        price = '物品 %d×%d' % (item_cost[0], item_cost[1])
    elif best:
        price = money_str(int(best))
    else:
        price = '?'
    return '商人：%s · 售价 %s' % (shown, price)


def drop_details(rows):
    parts = []
    for d in rows:
        nm = (d.get('name') or '').strip().strip('[]')
        loc = d.get('location') or []
        zone = ZONE_NAMES.get(loc[0]) if loc else None
        parts.append('%s（%s）' % (nm, zone) if zone else nm)
    return '掉落：' + '、'.join(parts)


def build():
    out = []
    idx = 23
    for r in ITEMS:
        iid = r['id']
        if iid in EXISTING:
            continue
        idx += 1
        p = PAGES.get(str(iid), {})
        slug = p.get('icon') or NETHER_ICONS.get(iid, '')
        sold = p.get('sold-by') or []
        dropped = p.get('dropped-by') or []
        if sold:
            group = 'rep'
            details = vendor_details(sold)
        elif dropped:
            group = 'unknown'
            details = drop_details(dropped)
        else:
            group = 'unknown'
            details = 'wowhead 暂未收录获取方式'
        disp = r.get('displayid')
        if not disp:
            nav = FIXUPS.get('nav', {}).get(str(iid)) or FIXUPS.get('nav', {}).get(iid) or {}
            disp = nav.get('displayid')
        tail = ', %d' % disp if disp else ''
        out.append((idx, iid, slug, group, details, tail))
    return out


def render(entries):
    lines = []
    for idx, iid, slug, group, details, tail in entries:
        pad = ' ' * (3 - len(str(idx))) if idx < 100 else ''
        idpad = ' ' * (7 - len(str(iid)))
        lines.append('    [%d]%s = { %d,%s "item", "%s", "%s",' % (idx, pad, iid, idpad, slug, group))
        lines.append('             "%s"%s },' % (details, tail))
    return '\n'.join(lines)


HEADER_NOTE = """
-- ★ 2026-10-07 晚间全量补录：数据源2 = wowhead forever/cn 物品分类页
--   items/miscellaneous/mounts（138 个坐骑物品，逐页抓 sold-by/dropped-by）。
--   [24] 起为分类页补录条目：group 口径 —— 商人出售 → rep（沿用既有条目口径）；
--   掉落 / 暂无来源页 → unknown（details 里写实际来源）。物品页被
--   CloudFront 按物品 id 封锁的 4 个无限服专属条目（211498/211499/216492/234465）
--   slug 留空 + 来源 unknown；23193 / 23720 图标经 nether tooltip 服务兜底。
--   display 缺失时 UI 自动退化大图标（与头注纪律一致）。
"""


def main():
    entries = build()
    print('new entries:', len(entries))
    src = open(SRC, encoding='utf-8').read()
    assert src.count('\r\n') == 0, 'CRLF found!'

    # 幂等：已补录过就不再追加
    if '2026-10-07 晚间全量补录' in src:
        print('already patched, skip')
        return

    # 插入点：ns.CollectionMounts 表的收尾 "}" 前（即最后一行 [23] 条目之后）
    m = re.search(r'\n\}\n\nns\.CollectionMountMeta', src)
    assert m, 'table end not found'
    block = render(entries)
    src = src[:m.start()] + '\n' + block + '\n' + src[m.start() + 1:]

    # 头注：在「★ 坐标纪律」段前插补录说明
    m2 = src.find('-- ★ 坐标纪律')
    assert m2 > 0, 'header anchor not found'
    src = src[:m2] + HEADER_NOTE.strip('\n') + '\n\n' + src[m2:]

    open(SRC, 'w', encoding='utf-8', newline='\n').write(src)
    raw = open(SRC, 'rb').read()
    print('CRLF:', raw.count(b'\r\n'), 'LF:', raw.count(b'\n'), 'size:', len(raw))
    # 摘要
    from collections import Counter
    print(Counter(e[3] for e in entries))
    for e in entries[:6]:
        print(e)
    print('...')
    for e in entries[-4:]:
        print(e)


if __name__ == '__main__':
    main()
