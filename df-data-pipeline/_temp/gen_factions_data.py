# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_Factions.lua（声望页数据 · 生成物）。

数据源：_temp/_wuxian_fac.json（wuxianwow /data/factions.json 抓取缓存）。
口径：
- 只收 listed 且非 internal（系统条目剔除，剩 70 条）；
- 落库纯结构：id / name(兜底名，运行期优先客户端 GetFactionInfoByID) /
  side(alliance|horde|neutral) / group(分组键) / desc / start(起始值) /
  races(种族例外 {who, base}，与全种族主组相同的省略) /
  rewards{friendly|honored|revered|exalted|neutral = {itemID,...}}；
- 中文名/物品名/品质/图标一律运行期取客户端，站点文本仅作兜底；
- zhTW / enUS 覆盖层由 gen_zhtw_data.py / gen_enus_data.py 重跑产出。

用法：python gen_factions_data.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(HERE, '_wuxian_fac.json')
DST = os.path.join(DF, 'Core', 'Data', 'Data_Factions.lua')

SIDE_MAP = {'联盟': 'alliance', '部落': 'horde', '中立': 'neutral'}
GROUP_MAP = {
    '联盟': 'alliance',
    '联盟部队': 'allianceForces',
    '热砂集团': 'cartel',
    '其他势力': 'other',
    '专业专精': 'prof',
    '部落军队': 'hordeForces',
    '部落': 'horde',
}
GROUP_ORDER = ['alliance', 'allianceForces', 'cartel', 'other', 'prof', 'hordeForces', 'horde']
STANDING_KEYS = {'中立': 'neutral', '友善': 'friendly', '尊敬': 'honored', '崇敬': 'revered', '崇拜': 'exalted'}


def esc(s):
    if s is None:
        return ''
    return (str(s).replace('\\', '\\\\').replace('"', '\\"')
            .replace('\r', '').replace('\n', '\\n'))


def main():
    data = json.load(open(SRC, encoding='utf-8'))
    facs = [x for x in data['factions'] if x.get('listed') and not x.get('internal')]
    if len(facs) < 60:
        raise SystemExit('数据异常：listed 非 internal 仅 %d 条' % len(facs))

    by_group = {}
    for x in facs:
        g = GROUP_MAP.get(x.get('category'))
        if not g:
            print('跳过未知分类：%s / %s' % (x.get('category'), x.get('name')))
            continue
        side = SIDE_MAP.get(x.get('side'))
        if not side:
            raise SystemExit('未知 side：%s / %s' % (x.get('side'), x.get('name')))
        races = []
        for gr in (x.get('groups') or []):
            who = gr.get('who')
            base = gr.get('base')
            if not who or who == '全部种族' or not isinstance(base, (int, float)):
                continue
            if base == x.get('base'):
                continue
            races.append((who, int(base)))
        rewards = {}
        for r in (x.get('rewards') or []):
            key = STANDING_KEYS.get(r.get('standing'))
            if not key or not isinstance(r.get('item_id'), int):
                if r.get('standing') not in STANDING_KEYS:
                    print('未知奖励档位：%s / %s' % (r.get('standing'), x.get('name')))
                continue
            rewards.setdefault(key, []).append(int(r['item_id']))

        by_group.setdefault(g, []).append({
            'id': int(x['id']),
            'name': x.get('name') or '',
            'side': side,
            'desc': x.get('desc') or '',
            'start': int(x.get('base') or 0),
            'races': races,
            'rewards': rewards,
        })

    out = []
    out.append('')
    out.append('')
    out.append('local _, ns = ...')
    out.append('')
    out.append('ns.FactionsData = {')
    n_all = 0
    for g in GROUP_ORDER:
        rows = by_group.get(g)
        if not rows:
            continue
        for x in rows:
            n_all += 1
            parts = ['id=%d' % x['id'], 'name="%s"' % esc(x['name']), 'side="%s"' % x['side'],
                     'group="%s"' % g, 'desc="%s"' % esc(x['desc']), 'start=%d' % x['start']]
            if x['races']:
                rs = ', '.join('{ "%s", %d }' % (esc(w), b) for w, b in x['races'])
                parts.append('races={ %s }' % rs)
            if x['rewards']:
                rk = []
                for key in ('neutral', 'friendly', 'honored', 'revered', 'exalted'):
                    ids = x['rewards'].get(key)
                    if ids:
                        rk.append('%s={ %s }' % (key, ', '.join(str(i) for i in ids)))
                parts.append('rewards={ %s }' % ', '.join(rk))
            out.append('  { %s },' % ', '.join(parts))
    out.append('}')
    out.append('')

    open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
    print('OK %s：%d 阵营（%s）' % (
        os.path.relpath(DST, DF), n_all,
        ', '.join('%s %d' % (g, len(by_group[g])) for g in GROUP_ORDER if by_group.get(g))))


if __name__ == '__main__':
    main()
