# -*- coding: utf-8 -*-
"""_pvp_site_data.json -> Core/Data/Data_PvPRanks.lua + Core/Data/Data_PvPSets.lua

数据层口径（与专业页/掉落一致）：
- 只存 itemID / 数字 / 语言中立键名；名字、图标、品质运行期从客户端取。
- 文件零中文（zhTW/enUS 副本因此不需要）；文案一律在 PvPUI.lua 的 L["…"] 键。
- LF 换行；头注释一块；正文不带行内注释。
"""
import json, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
DATA = json.load(io.open(os.path.join(HERE, '_pvp_site_data.json'), encoding='utf-8'))

SPEC_KEY = {
    '所有专精': 'all', '神圣': 'holy', '惩戒': 'retri', '暗影': 'shadow',
    '神圣和戒律': 'holydisc', '增强': 'enhance', '恢复': 'resto', '元素': 'ele',
    '野性战斗': 'feral', '平衡': 'balance',
}
SLOT_KEY = {
    '手腕': 'wrist', '腰部': 'waist', '脚': 'feet', '手部': 'hands',
    '腿部': 'legs', '肩部': 'shoulder', '胸部': 'chest', '头部': 'head',
}

def idsLua(lst):
    return '{ ' + ', '.join(str(x) for x in lst) + ' }' if lst else '{}'

# ── Data_PvPRanks.lua ────────────────────────────────────────────────────
lines = []
A = lines.append
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('local _, ns = ...')
A('')
A('ns.PvPRankData = {')
A('    updated = "2026-10-11",')
A('    marks = {')
for m in DATA['marks']:
    A('        { id = %d, slot = "%s", rank = %d },' % (m['id'], SLOT_KEY[m['slot']], m['rank']))
A('    },')
A('    ranks = {')
for r in DATA['ranks']:
    rw = r['rewards']
    A('        [%d] = { pts = %d, cum = %d, week = %d, a = %s, h = %s, s = %s },' % (
        r['level'], r['pts'], r['cum'], r['week'],
        idsLua(rw['a']), idsLua(rw['h']), idsLua(rw['shared'])))
A('    },')
A('    caps = {')
for c in DATA['caps']:
    A('        [%d] = { rank = %d, cum = %d, inc = %d },' % (c['week'], c['rank'], c['cum'], c['inc']))
A('    },')
A('    battlefields = {')
A('        { key = "spear", minLevel = 30, maxLevel = 60, size = 15, cta = 1 },')
A('        { key = "ab",    minLevel = 20, maxLevel = 60, size = 15, cta = 2 },')
A('        { key = "wsg",   minLevel = 10, maxLevel = 60, size = 10, cta = 3 },')
A('        { key = "av",    minLevel = 51, maxLevel = 60, size = 40, cta = 0 },')
A('    },')
A('}')

# ── Data_PvPSets.lua ─────────────────────────────────────────────────────
B = []
Ap = B.append
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('')
Ap('local _, ns = ...')
Ap('')
Ap('ns.PvPSetData = {')
Ap('    updated = "2026-10-11",')
Ap('    sets = {')
for s in DATA['sets']:
    Ap('        { class = "%s", spec = "%s",' % (s['class'], SPEC_KEY[s['spec']]))
    for tier in ('blue', 'epic'):
        Ap('          %s = {' % tier)
        Ap('            A = %s,' % idsLua(s[tier]['A']['ids']))
        Ap('            H = %s,' % idsLua(s[tier]['H']['ids']))
        Ap('          },')
    Ap('        },')
Ap('    },')
Ap('    spear = {')
STANDING_KEY = {'友善': 'friendly', '尊敬': 'honored', '崇敬': 'revered', '崇拜': 'exalted'}
SPEAR_FACTIONS = {'A': 2799, 'H': 2798}
FAC = json.load(io.open(os.path.join(HERE, '_wuxian_fac.json'), encoding='utf-8'))
FAC_BY_ID = {f['id']: f for f in FAC['factions']}
for cn, key in STANDING_KEY.items():
    sides = {}
    for side, fid in SPEAR_FACTIONS.items():
        sides[side] = [r['item_id'] for r in FAC_BY_ID[fid].get('rewards', []) if r['standing'] == cn]
    Ap('        %s = { A = { %s }, H = { %s } },' % (
        key,
        ', '.join(str(i) for i in sides['A']),
        ', '.join(str(i) for i in sides['H'])))
Ap('    },')

# ── battle = 战场声望奖励（阿拉希盆地，阿拉索联军 509 / 污染者 510，军需官全列表）──
BG_FACTIONS = {'ab': {'A': 509, 'H': 510}}
Ap('    battle = {')
for bkey, sides in BG_FACTIONS.items():
    Ap('        %s = {' % bkey)
    by_standing = {}
    for side, fid in sides.items():
        for r in FAC_BY_ID[fid]['rewards']:
            if r['item_id'] == 215450:
                continue
            by_standing.setdefault(STANDING_KEY[r['standing']], {})[side] = \
                by_standing.setdefault(STANDING_KEY[r['standing']], {}).get(side, [])
            by_standing[STANDING_KEY[r['standing']]][side].append(r['item_id'])
    for st in ('friendly', 'honored', 'revered', 'exalted'):
        grp = by_standing.get(st, {})
        Ap('        %s = {' % st)
        for side in ('A', 'H'):
            Ap('            %s = { %s },' % (side, ', '.join(str(i) for i in grp.get(side, []))))
        Ap('        },')
    Ap('        },')
Ap('    },')
Ap('}')

for rel, body in (('Core/Data/Data_PvPRanks.lua', '\n'.join(lines) + '\n'),
                  ('Core/Data/Data_PvPSets.lua', '\n'.join(B) + '\n')):
    p = os.path.join(ROOT, rel)
    assert '\r' not in body
    with open(p, 'wb') as f:
        f.write(body.encode('utf-8'))
    print('wrote', rel, len(body), 'chars')
