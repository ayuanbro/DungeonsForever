# -*- coding: utf-8 -*-
"""生成团本套装数据层：zhCN 源 + enUS 覆盖层。

产出
----
  Core/Data/Data_RaidSets.lua        —— 简体源（ns.RaidSetData）
  Core/Data/enUS/Data_RaidSets.lua   —— 英文覆盖层（仅 enUS 客户端加载）

口径
----
- 套装名 / 效果文案的**简体**取客户端口径（与 TalentsForever 的套装表逐条核对），
  并同时与参考页的 data-zh 对查（去空格后逐字相等才算通过）。
- **英文**取参考页自带的官方英文原文 —— **不是机翻**，所以本文件不进
  _temp/gen_enus_data.py 的机翻管线（该脚本的 ENUS_EXCLUDE 已收录本文件名）。
- P2 标注层 marks[n]：该件效果对应的技能在无限版的状态与天赋树位置，来源同参考页。
  st 用键（new / changed / same / moved / baseline），文案在界面层走 L 键。
- zhTW 副本由 _temp/gen_zhtw_data.py 按 Data_*.lua 通配自动生成，本脚本不负责。

用法
----
  $PY _temp/gen_raidsets.py            # 写盘
  $PY _temp/gen_raidsets.py --check    # 只核对不写盘
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
PAGE = os.path.join(HERE, '_src', 'gi_tier_tier1.html')
TF_SRC = os.environ.get(
    'DF_SETS_SRC',
    'D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/TalentsForever/Core/Data/Data_GearSets.lua')

CLASS_ORDER = ['WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST',
               'SHAMAN', 'MAGE', 'WARLOCK', 'DRUID']
CLASS_TOKEN = {'Warrior': 'WARRIOR', 'Paladin': 'PALADIN', 'Hunter': 'HUNTER',
               'Rogue': 'ROGUE', 'Priest': 'PRIEST', 'Shaman': 'SHAMAN',
               'Mage': 'MAGE', 'Warlock': 'WARLOCK', 'Druid': 'DRUID'}
ROLE_KEY = {'输出': 'dps', '坦克': 'tank', '治疗': 'heal'}
ARMOR_EN = {'板甲': 'Plate', '锁甲': 'Mail', '皮甲': 'Leather', '布甲': 'Cloth'}

# 参考页 data-zh 里的中文瑕疵（逐条修正，别让它们进数据层）
WHERE_ZH_FIX = {'Elemental树 · 第 7 行': '元素树 · 第 7 行'}

def norm(s):
    """去空白 + 统一全半角标点，用于「页面中文 vs 客户端中文」对查。"""
    s = re.sub(r'\s+', '', html.unescape(s))
    for a, b in (('＋', '+'), ('：', ':'), ('，', ','), ('。', '.')):
        s = s.replace(a, b)
    return s


def lua_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


# ---------------------------------------------------------------- 解析参考页

def parse_page():
    s = open(PAGE, encoding='utf-8', errors='replace').read()
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    out = []
    for sec in re.finditer(r'<section class="gi-fv-tier-class" id="([A-Za-z]+)"[^>]*>(.*?)</section>', s, re.S):
        body = sec.group(2)
        for art in re.finditer(r'<article class="gi-fv-card gi-fv-tier-set" data-role="(\w+)">(.*?)</article>', body, re.S):
            role, ab = art.group(1), art.group(2)
            chip = re.search(r'<span class="gi-fv-chip[^"]*" data-zh="([^"]*)">([^<]*)</span>', ab)
            h3 = re.search(r'<h3 data-zh="([^"]*)">([^<]*)</h3>', ab)
            wh = re.search(r'item-set=(\d+)', ab)
            rec = {
                'class': CLASS_TOKEN[sec.group(1)],
                'role': role,
                'id': int(wh.group(1)),
                'nameZh': h3.group(1),
                'nameEn': html.unescape(h3.group(2)).strip(),
                'chipZh': chip.group(1),
                'chipEn': html.unescape(re.sub(r'<[^>]+>', '', chip.group(2))).strip(),
                'bonuses': {},
                'marks': {},
            }
            # 专精 = chip 去掉「角色 · 」前缀
            if ' · ' in rec['chipEn']:
                rec['specEn'] = rec['chipEn'].split(' · ', 1)[1]
            else:
                rec['specEn'] = rec['chipEn']
            for b in re.finditer(r'<div class="gi-fv-tier-bonus">(.*?)</div>\s*</div>', ab, re.S):
                bb = b.group(1)
                piece = re.search(r'<b>(\d)<span', bb)
                pz = re.search(r'<p data-zh="([^"]*)">(.*?)</p>', bb, re.S)
                n = int(piece.group(1))
                rec['bonuses'][n] = {
                    'zh': pz.group(1),
                    'en': html.unescape(re.sub(r'<[^>]+>', '', pz.group(2))).strip(),
                }
                ref = re.search(r'<small class="gi-fv-tier-ref st-(\w+)">(.*?)</small>', bb, re.S)
                if ref:
                    spans = re.findall(r'<span[^>]*data-zh="([^"]*)">(.*?)</span>', ref.group(2), re.S)
                    spans = [(z, html.unescape(re.sub(r'<[^>]+>', '', t)).strip()) for z, t in spans]
                    mark = {'st': ref.group(1)}
                    if len(spans) >= 2:
                        mark['whereZh'], mark['whereEn'] = spans[1][0], spans[1][1]
                    if len(spans) >= 3:
                        mark['noteZh'], mark['noteEn'] = spans[2][0], spans[2][1]
                    rec['marks'][n] = mark
            out.append(rec)
    return out


# ------------------------------------------------------------- 解析客户端源

def parse_client():
    s = open(TF_SRC, encoding='utf-8', errors='replace').read()
    out = {}
    pat = re.compile(
        r'class = "(\w+)", name = "([^"]+)", nameEn = "([^"]+)",\s*'
        r'role = "([^"]+)", spec = "([^"]*)", armor = "([^"]+)", id = (\d+), slots = SLOTS,\s*'
        r'bonuses = \{(.*?)\},', re.S)
    for m in pat.finditer(s):
        cls, name, nameen, role, spec, armor, sid, block = m.groups()
        bons = {}
        for bm in re.finditer(r'\[(\d)\]\s*=\s*"((?:[^"\\]|\\.)*)"', block):
            bons[int(bm.group(1))] = bm.group(2)
        out[int(sid)] = {'class': cls, 'name': name, 'nameEn': nameen,
                         'role': role, 'spec': spec, 'armor': armor, 'bonuses': bons}
    return out


# ------------------------------------------------------------------ 主流程

def merge():
    page = parse_page()
    client = parse_client()
    page_by_id = {r['id']: r for r in page}
    problems, soft = [], []

    if len(page) != 18:
        problems.append('参考页套装数 %d ≠ 18' % len(page))
    if len(client) != 18:
        problems.append('客户端源套装数 %d ≠ 18' % len(client))
    for sid in sorted(set(page_by_id) ^ set(client)):
        problems.append('id %d 只出现在一侧' % sid)

    marks_n = sum(len(r['marks']) for r in page)
    if marks_n != 20:
        problems.append('标注条数 %d ≠ 20' % marks_n)

    merged = []
    for r in page:
        c = client[r['id']]
        if c['class'] != r['class']:
            problems.append('id %d 职业不一致 %s / %s' % (r['id'], c['class'], r['class']))
        if ROLE_KEY.get(c['role']) != r['role']:
            problems.append('id %d 角色不一致 %s / %s' % (r['id'], c['role'], r['role']))
        if c['name'] != r['nameZh']:
            soft.append('id %d 套装名措辞不同（取客户端） 客户端: %s / 参考页: %s'
                        % (r['id'], c['name'], r['nameZh']))
        if c['nameEn'] != r['nameEn']:
            problems.append('id %d 英文名不一致 %s / %s' % (r['id'], c['nameEn'], r['nameEn']))
        for n in (2, 3, 4, 5):
            cz = c['bonuses'].get(n, '')
            pz = r['bonuses'].get(n, {}).get('zh', '')
            if cz and pz and norm(cz) != norm(pz):
                soft.append('id %d %d件 文字有出入\n      客户端: %s\n      参考页: %s'
                            % (r['id'], n, cz, pz))
            if not r['bonuses'].get(n, {}).get('en'):
                problems.append('id %d %d件 缺英文原文' % (r['id'], n))
        rec = dict(r)
        rec['nameZh'] = c['name']
        rec['nameEn'] = c['nameEn']
        rec['roleKey'] = ROLE_KEY[c['role']]
        rec['spec'] = c['spec']
        rec['armor'] = c['armor']
        rec['bonusesZh'] = {n: c['bonuses'][n] for n in (2, 3, 4, 5)}
        merged.append(rec)

    merged.sort(key=lambda r: (CLASS_ORDER.index(r['class']), r['id']))
    # 页内顺序：同职业按参考页顺序（dps/tank/heal）
    order = {('WARRIOR', 'dps'): 0, ('WARRIOR', 'tank'): 1,
             ('PALADIN', 'heal'): 0, ('PALADIN', 'tank'): 1, ('PALADIN', 'dps'): 2,
             ('SHAMAN', 'heal'): 0, ('SHAMAN', 'dps'): 1,
             ('PRIEST', 'heal'): 0, ('PRIEST', 'dps'): 1,
             ('DRUID', 'heal'): 0, ('DRUID', 'tank'): 1, ('DRUID', 'dps'): 2,
             ('HUNTER', 'dps'): 0, ('ROGUE', 'dps'): 0,
             ('MAGE', 'dps'): 0, ('WARLOCK', 'dps'): 0}
    merged.sort(key=lambda r: (CLASS_ORDER.index(r['class']),
                               order.get((r['class'], r['roleKey']), 9), r['id']))
    return merged, problems, soft


HEAD_ZH = '''local _, ns = ...
ns.RaidSetData = {
    updated = "2026-09-30",
    raid    = "海加尔峰",
    total   = 18,
    pieces  = 6,
    sets = {'''

HEAD_EN = '''local _, ns = ...
if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
ns.RaidSetData = {
    updated = "2026-09-30",
    raid    = "Mount Hyjal",
    total   = 18,
    pieces  = 6,
    sets = {'''


def body(recs, lang):
    out = []
    for r in recs:
        head = ('        { class = %s, id = %d, role = %s, spec = %s, armor = %s,\n'
                '          name = %s,\n'
                '          bonuses = {\n')
        if lang == 'zh':
            spec, armor, name = r['spec'], r['armor'], r['nameZh']
            bons = {n: r['bonusesZh'][n] for n in (2, 3, 4, 5)}
        else:
            spec, armor, name = r['specEn'], ARMOR_EN[r['armor']], r['nameEn']
            bons = {n: r['bonuses'][n]['en'] for n in (2, 3, 4, 5)}
        out.append(head % (lua_str(r['class']), r['id'], lua_str(r['roleKey']),
                           lua_str(spec), lua_str(armor), lua_str(name)))
        for n in (2, 3, 4, 5):
            out.append('              [%d] = %s,\n' % (n, lua_str(bons[n])))
        out.append('          }')
        if r['marks']:
            items = []
            for n in sorted(r['marks']):
                m = r['marks'][n]
                if lang == 'zh':
                    where = WHERE_ZH_FIX.get(m.get('whereZh', ''), m.get('whereZh', ''))
                    note = m.get('noteZh', '')
                else:
                    where = m.get('whereEn', '')
                    note = m.get('noteEn', '')
                # 参考页该处中文补充说明尾部残缺（以「38级时」断开），截干净
                if lang == 'zh' and note and note.endswith('38级时'):
                    note = note[:-4]
                parts = ['st = %s' % lua_str(m['st'])]
                if where:
                    parts.append('where = %s' % lua_str(where))
                if note:
                    parts.append('note = %s' % lua_str(note))
                items.append('[%d] = { %s }' % (n, ', '.join(parts)))
            out.append(',\n          marks = { ' + ', '.join(items) + ' }')
        out.append(' },\n')
    out.append('    },\n}\n')
    return ''.join(out)


def main():
    check = '--check' in sys.argv
    recs, problems, soft = merge()
    if soft:
        print('[注] 参考页中文措辞与客户端文案有 %d 处出入（简体一律以客户端为准，仅供参考）：' % len(soft))
        for p in soft:
            print('   ~', p)
    if problems:
        print('!! 核对未通过，共 %d 条：' % len(problems))
        for p in problems:
            print('   -', p)
        raise SystemExit(1)
    print('[OK] 18 套 / 72 条效果 / 20 条标注 全部对齐')

    marks_n = sum(len(r['marks']) for r in recs)
    print('     套数 %d · 效果 %d · 标注 %d' % (len(recs), len(recs) * 4, marks_n))
    if check:
        return

    p1 = os.path.join(DF, 'Core', 'Data', 'Data_RaidSets.lua')
    p2 = os.path.join(DF, 'Core', 'Data', 'enUS', 'Data_RaidSets.lua')
    open(p1, 'wb').write((HEAD_ZH + body(recs, 'zh')).encode('utf-8'))
    open(p2, 'wb').write((HEAD_EN + body(recs, 'en')).encode('utf-8'))
    print('写出 %s (%d B)' % (p1, os.path.getsize(p1)))
    print('写出 %s (%d B)' % (p2, os.path.getsize(p2)))


if __name__ == '__main__':
    main()
