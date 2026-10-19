# -*- coding: utf-8 -*-
"""把 _temp/rotations/wow_forever_rotations.md（窝窝头 WoW Forever 各专精循环）转成
_temp/cc_rot_wow.py：ns.ClassCombat.rotation[职业][专精] = { st = {...}, aoe = {...} }。

每条 = { spell = 登记表英文键（映射不到时留原文）, note = 说明原文 }。
等级取 Lv30 段（缺则回退 Lv20）；窝窝头只有 3 个专精真的分了 Single Target / AOE，其余是单张优先级表。

用法：python gen_rot_wowhead.py
"""
import collections
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'rotations', 'wow_forever_rotations.md')
ZH = os.path.join(HERE, 'rotations', '_zhmap.txt')
DST = os.path.join(HERE, 'cc_rot_wow.py')

CLASS_MAP = {
    '战士': 'WARRIOR', '圣骑士': 'PALADIN', '猎人': 'HUNTER', '潜行者': 'ROGUE',
    '牧师': 'PRIEST', '萨满': 'SHAMAN', '法师': 'MAGE', '术士': 'WARLOCK', '德鲁伊': 'DRUID',
}
SPEC_MAP = {
    'WARRIOR': {'武器': 'arms', '狂暴': 'fury', '防护': 'prot'},
    'PALADIN': {'神圣': 'holy', '防护': 'prot', '惩戒': 'ret'},
    'HUNTER': {'兽王': 'bm', '射击': 'mm', '生存': 'surv'},
    'ROGUE': {'刺杀': 'assa', '战斗': 'combat', '敏锐': 'sub'},
    'PRIEST': {'戒律': 'disc', '神圣': 'holy', '暗影': 'shadow'},
    'SHAMAN': {'元素': 'ele', '增强': 'enh', '恢复': 'resto'},
    'MAGE': {'奥术': 'arcane', '火焰': 'fire', '冰霜': 'frost'},
    'WARLOCK': {'痛苦': 'affli', '恶魔': 'demo', '毁灭': 'destro'},
    'DRUID': {'平衡': 'balance', '野性': 'feral', '恢复': 'resto'},
}
EXTRA_ZH = {
    ('WARRIOR', '斩杀'): 'Execute',
    ('WARRIOR', '横扫'): 'Sweeping Strikes',
    ('MAGE', '灼烧'): 'Scorch',
    ('MAGE', '节能施法'): 'Clearcasting',
    ('PRIEST', '苦修'): 'Penance',
    ('PRIEST', '联结治疗'): 'Binding Heal',
    ('PRIEST', '噬灵瘟疫'): 'Devouring Plague',
    ('WARLOCK', '魅魔'): 'Summon Succubus',
    ('DRUID', '星火术'): 'Starfire',
    ('DRUID', '扫击'): 'Swipe',
    ('DRUID', '精灵之火'): 'Faerie Fire',
    ('DRUID', '迅捷治愈'): 'Swiftmend',
    ('DRUID', '宁静'): 'Tranquility',
    ('ROGUE', '剑刃乱舞'): 'Blade Flurry',
}
from rot_zh_notes import ZH_NOTES, NOTE_FIX, BLURBS
from cc_rot import ROT as OLD_ROT
from cc_spells import SPELLS


def english_key(txt, cls):
    best = None
    keys = list(SPELLS.get(cls, {}).keys()) + list(SPELLS.get('HUNTER', {}).keys())
    for k in keys:
        if k in txt and ' ' not in k or (k in txt and len(k) > 10):
            if best is None or len(k) > len(best):
                best = k
    return best


def old_note(cls, spec, key):
    for row in (OLD_ROT.get(cls, {}).get(spec) or []):
        if row[0] == key and row[1]:
            return row[1]
    return None
CJK = re.compile('[\u4e00-\u9fff][\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]*[\u4e00-\u9fff]')


def load_zh():
    m = {}
    for ln in open(ZH, encoding='utf-8'):
        if '|' in ln:
            en, zh = ln.rstrip('\n').split('|', 1)
            if zh:
                m[zh.strip()] = en.strip()
    return m


def parse():
    data = collections.OrderedDict()
    cls_cn = spec_cn = None
    lv = None
    cur = 'st'
    for raw in open(SRC, encoding='utf-8'):
        ln = raw.strip()
        if ln.startswith('# '):
            cls_cn = ln[2:].strip()
            continue
        if ln.startswith('## '):
            spec_cn = ln[3:].strip().split('·')[-1].strip()
            continue
        m = re.match(r'###\s*Lv(\d+)', ln)
        if m:
            lv = int(m.group(1))
            cur = 'st'
            c = CLASS_MAP.get(cls_cn)
            s = (SPEC_MAP.get(c) or {}).get(spec_cn)
            if c and s:
                data.setdefault(c, {}).setdefault(s, {})
                data[c][s].setdefault(lv, {'st': [], 'aoe': []})
            continue
        if ln.startswith('**Single Target'):
            cur = 'st'
            continue
        if ln.startswith('**AOE'):
            cur = 'aoe'
            continue
        m = re.match(r'^\d+\.\s+(.*)$', ln)
        c = CLASS_MAP.get(cls_cn)
        s = (SPEC_MAP.get(c) or {}).get(spec_cn)
        if m and lv and c and s:
            txt = m.group(1)
            ek = english_key(txt, c)
            if ek:
                sp = ek
                note = re.sub(r'\s+', ' ', txt.replace(ek, ' ', 1))
            else:
                mm = CJK.search(txt)
                if not mm:
                    continue
                sp = mm.group(0)
                note = re.sub(r'\s+', ' ', (txt[:mm.start()] + ' ' + txt[mm.end():]).strip())
            note = re.sub(r'\s+', ' ', note).strip(' .,;:')
            data[c][s][lv][cur].append({'spell': sp, 'note': note})
    return data


def main():
    zh = load_zh()
    raw = parse()
    out = collections.OrderedDict()
    miss = {}
    for c in raw:
        for s in raw[c]:
            levels = raw[c][s]
            pick = levels.get(30) or levels.get(20) or {'st': [], 'aoe': []}
            if not pick['st'] and not pick['aoe']:
                pick = levels.get(20) or pick
            cols = {}
            for key in ('st', 'aoe'):
                rows = []
                for r in pick[key]:
                    k = zh.get(r['spell']) or EXTRA_ZH.get((c, r['spell'])) or r['spell']
                    if k == r['spell'] and CJK.match(r['spell']) and r['spell'] not in zh.values():
                        miss[r['spell']] = miss.get(r['spell'], 0) + 1
                    zn = NOTE_FIX.get((c, s, k)) or old_note(c, s, k) or ZH_NOTES.get(r['note']) or ''
                    rows.append((k, r['note'], zn))
                cols[key] = rows
            out.setdefault(c, {})[s] = {'note': BLURBS.get((c, s), ''), 'cols': cols}

    body = ['# -*- coding: utf-8 -*-',
            '"""窝窝头 WoW Forever 各专精输出循环（单体 / AOE 两列）。由 gen_rot_wowhead.py 生成。"""',
            '', 'ROT = {']
    for c in out:
        body.append('    %r: {' % c)
        for s in out[c]:
            body.append('        %r: {' % s)
            body.append("            'note': %r," % out[c][s]['note'])
            for key in ('st', 'aoe'):
                body.append('            %r: [' % key)
                for k, en, zn in out[c][s]['cols'][key]:
                    body.append('                (%r, %r, %r),' % (k, en, zn))
                body.append('            ],')
            body.append('        },')
        body.append('    },')
    body.append('}')
    body.append('')
    open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(body))

    n_st = sum(len(out[c][s]['cols']['st']) for c in out for s in out[c])
    n_aoe = sum(len(out[c][s]['cols']['aoe']) for c in out for s in out[c])
    specs = sum(len(out[c]) for c in out)
    print('specs=%d st=%d aoe=%d' % (specs, n_st, n_aoe))
    print('未映射名 %d 个：%s' % (len(miss), ', '.join(list(miss)[:40])))
    allnotes = set()
    for c in out:
        for s2 in out[c]:
            for key in ('st', 'aoe'):
                for _k, en, _zn in out[c][s2]['cols'][key]:
                    if en:
                        allnotes.add(en)
    unzh = sorted(n for n in allnotes if ZH_NOTES.get(n, n) == n)
    print('未汉化 %d 条：%s' % (len(unzh), ' || '.join(unzh[:12])))
    thin = 0
    for c in out:
        for s2 in out[c]:
            for key in ('st', 'aoe'):
                for _k, _en, zn in out[c][s2]['cols'][key]:
                    if len(zn) < 4:
                        thin += 1
    print('说明仍偏短/空的条目：%d' % thin)


if __name__ == '__main__':
    main()
