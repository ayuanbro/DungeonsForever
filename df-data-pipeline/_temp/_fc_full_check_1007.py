# -*- coding: utf-8 -*-
"""fc vs 本地库 全量更新核查（2026-10-07 新鲜快照）
对比维度：地下城清单 / 掉落（逐 boss + 全本物品集 + fc「新增」标记）/ 任务 / 图钉
输出：_fc_full_check_report.json
"""
import re, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fc_compare import SLUG2DID, norm, ours_block, ROOT  # noqa

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_ref')

def read(p):
    return open(p, encoding='utf-8').read()

# ---------------- fc 侧解析 ----------------
SEC_RE = re.compile(r'<section id="([a-z0-9-]+)" class="lb-boss"[^>]*>(.*?)</section>', re.S)
ITEM_RE = re.compile(
    r'<a href="/zh-cn/item/(\d+)">.*?<span class="lb-name ([^"]*)">([^<]*)</span>'
    r'(.*?)</span></a></li>', re.S)

def fc_bosses(h):
    """[(boss_slug, 中文名, npcID, {iid: (name, chance, is_new)})]"""
    out = []
    for m in SEC_RE.finditer(h):
        slug, body = m.group(1), m.group(2)
        zh = ''
        hm = re.search(r'<h2[^>]*>([^<]*)</h2>', body)
        if hm:
            zh = hm.group(1).strip()
        npc = ''
        fm = re.search(r'/wow-ui/bosses/(\d+)\.webp', body)
        if fm:
            npc = fm.group(1)
        items = {}
        for it in ITEM_RE.finditer(body):
            iid = int(it.group(1))
            name = it.group(3).strip()
            ch = None
            cm = re.search(r'lb-chance[^>]*>\s*\(\s*([\d.]+)\s*%', it.group(4))
            if cm:
                ch = float(cm.group(1))
            is_new = 'lb-mark-new' in it.group(4)
            items[iid] = (name, ch, is_new)
        out.append((slug, zh, npc, items))
    return out

def fc_sec_quests(h, sec_id):
    m = re.search(r'<section id="%s"[^>]*>(.*?)</section>' % sec_id, h, re.S)
    if not m:
        return []
    return sorted({int(x) for x in re.findall(r'/zh-cn/quest/(\d+)', m.group(1))})

def fc_all_quests(h):
    secs = ['quests', 'quest-items', 'givers']
    ids = set()
    for s in secs:
        ids.update(fc_sec_quests(h, s))
    return sorted(ids)

def fc_pins(h):
    """floors.pins -> [{x,y,boss,face,faceKind,label}]"""
    out = []
    for m in re.finditer(r'\\"pins\\":\[(.*?)\]', h):
        for p in re.finditer(
                r'\{"x":([\d.]+),"y":([\d.]+),"boss":"([^"]*)","face":(\d+),'
                r'"faceKind":"([^"]*)","label":"([^"]*)"', m.group(1)):
            out.append({'x': float(p.group(1)), 'y': float(p.group(2)),
                        'boss': p.group(3), 'face': int(p.group(4)),
                        'kind': p.group(5), 'label': p.group(6)})
    return out

def fc_summary(h):
    """页面顶层小节清单 + 「推荐等级」等元信息"""
    secs = re.findall(r'<section id="([a-z0-9-]+)"', h)
    return sorted(set(secs))

# ---------------- 本地侧解析 ----------------
lt = read(os.path.join(ROOT, 'Core/Data/Data_DungeonLoot.lua'))

def ours_loot(did):
    """(英文名, 中文名, 说明, npcid) -> {iid: (chance, is_quest)}；None=本地无此本"""
    blk = ours_block(lt, did)
    if not blk:
        return None
    rows = []
    for m in re.finditer(r'\{ "([^"]+)", "([^"]*)", "([^"]*)", "(\d*)", \{(.*?)\n        \} \}', blk, re.S):
        en, zhcn, note, npc, items = m.groups()
        d = {}
        for it in re.finditer(r'\{ (\d+), (nil|[\d.]+), (true|false|nil) \}', items):
            chance = None if it.group(2) == 'nil' else float(it.group(2))
            d[int(it.group(1))] = (chance, it.group(3) == 'true')
        rows.append({'en': en, 'zh': zhcn, 'note': note, 'npc': npc, 'items': d})
    return rows

qt = read(os.path.join(ROOT, 'Core/Data/Data_DungeonQuests.lua'))

def ours_quests(did):
    blk = ours_block(qt, did)
    if not blk:
        return []
    m = re.match(r'\s*\[', blk)
    ids = set()
    for row in re.finditer(r'^        \{ (\d+),', blk, re.M):
        ids.add(int(row.group(1)))
    return sorted(ids)

bp = read(os.path.join(ROOT, 'Core/Data/Data_BossPos.lua'))

def ours_bosspos(did):
    blk = ours_block(bp, did)
    if not blk:
        return {}
    out = {}
    for m in re.finditer(r'        \["([^"]+)"\] = \{ ([^}]*) \}', blk):
        pts = re.findall(r'\{ ([\d.]+), ([\d.]+)(?:, (\d+))? \}', m.group(2))
        out[m.group(1)] = [(float(a), float(b), c or '') for a, b, c in pts]
    return out

mp = read(os.path.join(ROOT, 'Core/Data/Data_MapPins.lua'))

def ours_mappins(did):
    blk = ours_block(mp, did)
    if not blk:
        return {}
    out = {}
    for m in re.finditer(r'(\w+) = \{ ([^}]*) \}', blk):
        out[m.group(1)] = re.findall(r'\{ ([\d.]+), ([\d.]+)', m.group(2))
    return out

dt = read(os.path.join(ROOT, 'Core/Data/Data_Dungeons.lua'))
def ours_meta(did):
    m = re.search(r'\{ id = "%s".*?\} \},' % did, dt, re.S)
    if not m:
        return None
    row = m.group(0)
    def g(k):
        mm = re.search(r'%s = ([^,]+),' % k, row)
        return mm.group(1).strip() if mm else None
    return {'bossCount': g('bossCount'), 'dropCount': g('dropCount'), 'isNew': g('isNew')}

# ---------------- 主循环 ----------------
report = {'dungeon_list': {'fc_count': 35, 'ours_count': 0}, 'dungeons': {}}

for slug, did in sorted(SLUG2DID.items()):
    p = os.path.join(REF, 'dg_%s.html' % slug)
    if not os.path.exists(p):
        continue
    h = read(p)
    d = {}
    # 元信息
    d['meta'] = ours_meta(did)
    # fc 是否有 boss 明细
    bosses = fc_bosses(h)
    d['fc_secs'] = fc_summary(h)
    d['fc_boss_count'] = len(bosses)
    d['fc_bosses'] = [{'slug': s, 'zh': z, 'npc': n, 'items': len(it)} for s, z, n, it in bosses]
    # 掉落对比（仅当本地有该本）
    ours = ours_loot(did)
    d['ours_loot_rows'] = None if ours is None else len(ours)
    if ours is not None and bosses:
        # 匹配：npc 优先，其次中文名
        ours_by_npc = {r['npc']: r for r in ours if r['npc']}
        ours_by_zh = {r['zh']: r for r in ours}
        loot_diff = []
        fc_all_items = set()
        for slugb, zhb, npcb, items in bosses:
            fc_all_items.update(items.keys())
            row = ours_by_npc.get(npcb) or ours_by_zh.get(zhb)
            if row is None:
                loot_diff.append({'type': 'FC-BOSS-WE-LACK', 'boss': zhb or slugb, 'npc': npcb, 'fc_items': sorted(items)})
                continue
            our_items = set(row['items'])
            add = sorted(set(items) - our_items)
            rem = sorted(our_items - set(items))
            if add or rem:
                loot_diff.append({'type': 'FC-ITEM-DIFF', 'boss': row['en'], 'npc': row['npc'],
                                  '+': add, '-': rem,
                                  '+detail': {str(i): items[i] for i in add}})
        # fc 全本物品集（含小怪节）vs 本地全集
        local_all = set()
        for r in ours:
            local_all.update(r['items'])
        d['fc_item_total'] = len(fc_all_items)
        d['ours_item_total'] = len(local_all)
        d['loot_diff'] = loot_diff
    elif ours is None:
        d['loot_diff'] = 'OUR-LOOT-MISSING'
    # 任务
    fq = fc_all_quests(h)
    oq = ours_quests(did)
    d['fc_quests'] = fq
    d['ours_quests'] = oq
    d['quests_diff'] = {'fc_only': sorted(set(fq) - set(oq)), 'ours_only': sorted(set(oq) - set(fq))}
    # 图钉
    pins = fc_pins(h)
    d['fc_pins_kind'] = {}
    for pin in pins:
        d['fc_pins_kind'][pin['kind']] = d['fc_pins_kind'].get(pin['kind'], 0) + 1
    obp = ours_bosspos(did)
    # fc boss/rare 钉 vs 本地 BossPos（按 face npc 匹配）
    npc2en = {}
    if ours:
        for r in ours:
            if r['npc']:
                npc2en[r['npc']] = r['en']
    pin_diff = []
    fc_by_boss = {}
    for pin in pins:
        fc_by_boss.setdefault(pin['face'], []).append((pin['x'], pin['y'], pin['kind'], pin['boss']))
    for face, pts in fc_by_boss.items():
        en = npc2en.get(str(face))
        if en is None:
            pin_diff.append({'type': 'FC-PIN-UNMATCHED', 'face': face,
                             'boss_slug': pts[0][3], 'kind': pts[0][2], 'n': len(pts)})
            continue
        if en not in obp:
            pin_diff.append({'type': 'FC-PIN-WE-LACK', 'boss': en, 'face': face,
                             'kind': pts[0][2], 'n': len(pts), 'pts': pts})
    d['pin_diff'] = pin_diff
    d['ours_bosspos_bosses'] = sorted(obp.keys())
    d['ours_mappins'] = ours_mappins(did)
    report['dungeons'][did] = d

report['dungeon_list']['ours_count'] = len(report['dungeons'])
json.dump(report, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '_fc_full_check_report.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('done', report['dungeon_list'])
