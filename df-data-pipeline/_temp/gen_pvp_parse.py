# -*- coding: utf-8 -*-
"""从 foreverchanges.pro pvp-ranks 页面 HTML 解析全部 PvP 数据 -> JSON。
产物: _temp/_pvp_site_data.json
"""
import re, json, html, io, sys, os

SRC = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'tmp', 'pvpranks.html')
# git-bash /tmp 实际落在用户 Temp；直接按两个候选找
for cand in [
    r'C:/Users/Administrator/AppData/Local/Temp/pvpranks.html',
    r'/tmp/pvpranks.html',
    os.path.join(os.path.dirname(__file__), 'pvpranks.html'),
]:
    if os.path.exists(cand):
        SRC = cand
        break

raw = open(SRC, encoding='utf-8').read()

def item_ids(seg):
    return [int(x) for x in re.findall(r'/zh-cn/item/(\d+)', seg)]

def set_name(seg):
    m = re.search(r'pvr-set-name"><span class="q\d">([^<]+)</span>', seg)
    return html.unescape(m.group(1)) if m else None

out = {}

# ── 1. 套装区: table.pvr-sets ────────────────────────────────────────────
i = raw.find('pvr-sets')
j = raw.find('</table>', i)
tbl = raw[i:j]
rows = re.findall(r'<tr><th scope="row">(.*?)</th><td class="pvr-tier-blue">(.*?)</td><td class="pvr-tier-epic">(.*?)</td></tr>', tbl, re.S)
assert len(rows) == 15, '套装行数 %d != 15' % len(rows)

def parse_set_cell(cell):
    # cell 含 2 个 div.pvr-set：第一个 class 含 pvr-a（联盟）、pvr-h（部落）
    blocks = re.findall(r'<div class="(pvr-[ah]) pvr-set">(.*?)</div></div></div>|<div class="(pvr-[ah]) pvr-set">(.*?)(?=<div class="pvr-|</td>)', cell, re.S)
    sets = {}
    # 更稳的做法: 直接按 pvr-set-name 切
    parts = re.split(r'<div class="(pvr-[ah]) pvr-set">', cell)
    # parts[0] 是前导垃圾, 之后成对: side, content
    for k in range(1, len(parts) - 1, 2):
        side = 'A' if parts[k] == 'pvr-a' else 'H'
        content = parts[k + 1]
        sets[side] = {'name': set_name(content), 'ids': item_ids(content)}
    return sets

CLASS_KEY = {
    '战士': 'WARRIOR', '圣骑士': 'PALADIN', '猎人': 'HUNTER', '潜行者': 'ROGUE',
    '牧师': 'PRIEST', '萨满祭司': 'SHAMAN', '法师': 'MAGE', '术士': 'WARLOCK', '德鲁伊': 'DRUID',
}

sets = []
for th, blue, epic in rows:
    cm = re.search(r'<b class="pvr-c-\w+">([^<]+)</b><small>([^<]*)</small>', th)
    cls, spec = cm.group(1), cm.group(2)
    b = parse_set_cell(blue)
    e = parse_set_cell(epic)
    sets.append({
        'class': CLASS_KEY[cls], 'spec': spec,
        'blue': b, 'epic': e,
    })
out['sets'] = sets

# ── 2. 军衔表: table.pvr-ladder ─────────────────────────────────────────
i = raw.find('pvr-ladder')
j = raw.find('</table>', i)
rtbl = raw[i:j]
rrows = re.findall(r'<tr id="rank-(\d+)">(.*?)</tr>', rtbl, re.S)
assert len(rrows) == 14, '军衔行数 %d != 14' % len(rrows)
ranks = []
for lvl, r in rrows:
    nm = re.search(r'<span class="pvr-a">([^<]+)</span><span class="pvr-h">([^<]+)</span>', r)
    pts = int(re.search(r'pvr-points">([\d,]+)', r).group(1).replace(',', ''))
    cum = int(re.search(r'pvr-total[^>]*>([\d,]+)', r).group(1).replace(',', ''))
    wk = int(re.search(r'第(?:<!-- -->)?(\d+)(?:<!-- -->)?周', r).group(1))
    rew = {'shared': [], 'a': [], 'h': []}
    for li in re.findall(r'<li>(.*?)</li>', r, re.S):
        sa = re.search(r'<span class="pvr-a pvr-reward-items">(.*?)</span>', li, re.S)
        sh = re.search(r'<span class="pvr-h pvr-reward-items">(.*?)</span>', li, re.S)
        if sa or sh:
            if sa:
                rew['a'] += item_ids(sa.group(1))
            if sh:
                rew['h'] += item_ids(sh.group(1))
        else:
            rew['shared'] += item_ids(li)
    ranks.append({'level': int(lvl), 'pts': pts, 'cum': cum, 'week': wk,
                  'nameA': nm.group(1) if nm else None,
                  'nameH': nm.group(2) if nm else None,
                  'rewards': rew})
assert len(ranks) == 14, '军衔行数 %d != 14' % len(ranks)
out['ranks'] = ranks

# ── 3. 每周上限 ──────────────────────────────────────────────────────────
i = raw.find('pvr-weeks')
seg = raw[i:i + 9000]
caps = []
for m in re.finditer(r'第(?:<!-- -->)?(\d+)(?:<!-- -->)?周</span>.*?等级(?:<!-- -->)?(\d+).*?pvr-week-cap">([\d,]+)</span><small>\+<!-- -->([\d,]+)', seg, re.S):
    caps.append({'week': int(m.group(1)), 'rank': int(m.group(2)),
                 'cum': int(m.group(3).replace(',', '')), 'inc': int(m.group(4).replace(',', ''))})
assert len(caps) == 10, '周上限行数 %d != 10' % len(caps)
out['caps'] = caps

# ── 4. 暗矛群岛声望奖励 ─────────────────────────────────────────────────
i = raw.find('pvr-rep')
seg = raw[i:i + 16000]
h4s = re.findall(r'<h4 class="pvr-standing[^"]*">(尊敬|崇敬)</h4>(.*?)(?=<li><h4|</ul>)', seg, re.S)
spear = {}
for tier, body in h4s:
    ids = item_ids(body)
    spear[tier] = ids
    assert len(ids) == 8, '暗矛 %s 物品数 %d != 8' % (tier, len(ids))
out['spear'] = spear

# ── 5. 印记门槛（正文锚点核对） ─────────────────────────────────────────
i = raw.find('pvr-seals')
seg = raw[i:i + 6000]
marks = re.findall(r'href="/zh-cn/item/(\d+)"[^>]*aria-label="([^"]+)"><img[^>]*/></a><span>(手腕|腰部|脚|手部|腿部|肩部|胸部|头部)</span><b>等级(?:<!-- -->)?(\d+)', seg)
assert len(marks) == 8, '印记门槛数 %d != 8' % len(marks)
out['marks'] = [{'id': int(i), 'name': html.unescape(n), 'slot': s, 'rank': int(r)} for i, n, s, r in marks]

with io.open(os.path.join(os.path.dirname(__file__), '_pvp_site_data.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print('sets=%d ranks=%d caps=%d spear=%s marks=%d' % (
    len(sets), len(ranks), len(caps),
    {k: len(v) for k, v in spear.items()}, len(marks)))
