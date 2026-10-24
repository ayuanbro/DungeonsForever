# -*- coding: utf-8 -*-
"""专精指南解析：_cg_probe/*.html markup 载荷 → 结构化 JSON（英文原样）。

产物 _cg_parsed.json：
  { "<cls>_<spec>": { updated, sections: [ {key, lead?, items?, rows?, good?, bad?, multi?} ] } }

板块 key：changes / sw / beginner / systems / rotation / stats / races / prof
spell 引用一律转成 |sID| 占位，翻译层与生成层原样透传。
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, '_cg_probe')
OUT = os.path.join(HERE, '_cg_parsed.json')

PAT_MARKUP = r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")'
PAT_HEAD = re.compile(r'\[(h2|h3|h4)([^\]]*)\]([^\[]*?)\[/\1\]', re.S)
PAT_TABLE = re.compile(r'\[table[^\]]*\](.*?)\[/table\]', re.S)
PAT_TR = re.compile(r'\[tr([^\]]*)\](.*?)\[/tr\]', re.S)
PAT_TD = re.compile(r'\[td([^\]]*)\](.*?)\[/td\]', re.S)
PAT_UL = re.compile(r'\[ul\](.*?)\[/ul\]', re.S)
PAT_LI = re.compile(r'\[li([^\]]*)\](.*?)\[/li\]', re.S)

CLASS_NAME = {1: '战士', 2: '圣骑士', 3: '猎人', 4: '盗贼', 5: '牧师', 6: '死亡骑士',
              7: '萨满祭司', 8: '法师', 9: '术士', 10: '武僧', 11: '德鲁伊'}

SPEC_SLUGS = [
    ('warrior', 'arms'), ('warrior', 'fury'), ('warrior', 'protection'),
    ('paladin', 'holy'), ('paladin', 'protection'), ('paladin', 'retribution'),
    ('hunter', 'beast-mastery'), ('hunter', 'marksmanship'), ('hunter', 'survival'),
    ('rogue', 'assassination'), ('rogue', 'combat'), ('rogue', 'subtlety'),
    ('priest', 'discipline'), ('priest', 'holy'), ('priest', 'shadow'),
    ('shaman', 'elemental'), ('shaman', 'enhancement'), ('shaman', 'restoration'),
    ('mage', 'arcane'), ('mage', 'fire'), ('mage', 'frost'),
    ('warlock', 'affliction'), ('warlock', 'demonology'), ('warlock', 'destruction'),
    ('druid', 'balance'), ('druid', 'feral'), ('druid', 'restoration'),
]


def spell(m):
    return '\x01%s\x02' % m.group(1)


def attr(tag, name):
    m = re.search(r'%s="?([^\]"]*)"?' % name, tag)
    return m.group(1) if m else ''


def clean(s):
    s = re.sub(r'\[spell=(\d+)\]', spell, s)
    s = re.sub(r'\[icon name=side_alliance\]\s*/?\[?/icon\]?', '\x06', s)
    s = re.sub(r'\[icon name=side_horde\]\s*/?\[?/icon\]?', '\x07', s)
    s = re.sub(r'\[icon name=([a-z\-]+)\]\s*/?\[?/icon\]?', lambda m: '[R:%s]' % m.group(1), s)
    s = re.sub(r'\[icon[^\]]*\]\[/icon\]', '', s)
    s = re.sub(r'\[span class=icon-tick\]\s*\[/span\]', '', s)
    s = re.sub(r'\[span class=icon-star\]\s*\[/span\]', '	', s)
    s = re.sub(r'\[span class=icon-(alliance|horde)\]', lambda m: '\x06' if m.group(1) == 'alliance' else '\x07', s)
    s = re.sub(r'\[/span\]', '', s)
    s = re.sub(r'\[class=(\d+)\]', lambda m: '[CLS:%d]' % int(m.group(1)), s)
    s = re.sub(r'\[b\]([^\[]*?)\[/b\]', lambda m: '\x03' + m.group(1) + '\x04', s)
    s = re.sub(r'\[/?(?:b|i|u|center|small|pad|toc)\]', '', s)
    s = re.sub(r'\[li[^\]]*\]', '\x05', s)
    s = re.sub(r'\[/li\]', '\x05', s)
    s = re.sub(r'\[/?color[^\]]*\]', '', s)
    s = re.sub(r'\[/?grid[^\]]*\]', '', s)
    s = re.sub(r'\[h\d[^\]]*\]', '', s)
    s = re.sub(r'\[/?ul\]', '', s)
    s = s.replace('[CLS:11]', 'Druid')
    s = re.sub(r'\[CLS:(\d+)\]', lambda m: CLASS_NAME.get(int(m.group(1)), 'class'), s)
    s = re.sub(r'\[R:([a-z\-]+)\]', lambda m: RACE_EN.get(m.group(1), ''), s)
    s = re.sub(r'\[\w+[^\]]*\]', '', s)
    s = re.sub(r'\[/[^\]]*\]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s*([\x01\x02\x03\x04\x05\x06\x07])\s*', r'\1', s)
    s = re.sub(r'\x01(\d+)\x02', r'|s\1|', s)
    s = re.sub(r'\x05+', '\x05', s).strip('\x05')
    return s


def unmark(s):
    """把 \x03b\x04 加粗占位与 \x05 条目分隔还原成纯文本（供普通段落）。"""
    s = s.replace('\x03', '').replace('\x04', '')
    parts = [p for p in s.split('\x05') if p]
    return '；'.join(parts) if len(parts) > 1 else s


RACE_EN = {'human': 'Human', 'dwarf': 'Dwarf', 'night-elf': 'Night Elf', 'gnome': 'Gnome',
           'orc': 'Orc', 'undead': 'Undead', 'tauren': 'Tauren', 'troll': 'Troll',
           'skyborne': 'Skyborne'}


def parse_table(tb):
    rows = []
    for trm in PAT_TR.finditer(tb):
        bgtone = attr(trm.group(1), 'background')
        cells = [clean(td.group(2)) for td in PAT_TD.finditer(trm.group(2))]
        if cells:
            rows.append({'bg': bgtone, 'cells': cells})
    return rows


def race_table_rows(rows):
    """种族勾选表 → [{race, side, mark}]；解析不了返回 None。"""
    if len(rows) < 2:
        return None
    head = rows[0]['cells']
    body = rows[1]
    out = []
    for i, cell in enumerate(body['cells']):
        if i >= len(head):
            break
        if '' in cell:
            mark = 'tick'
        elif '	' in cell:
            mark = 'star'
        else:
            continue
        h = head[i]
        if '\x06' in h:
            side = 'alliance'
        elif '\x07' in h:
            side = 'horde'
        else:
            side = 'both'
        name = h.replace('\x06', ' ').replace('\x07', ' ')
        name = re.sub(r'\[R:([a-z\-]+)\]',
                      lambda m: RACE_EN.get(m.group(1), ''), name)
        name = re.sub(r'\s+', ' ', name).strip()
        if name:
            out.append({'race': name, 'side': side, 'mark': mark})
    return out or None


def section_key(title):
    t = title.lower()
    if 'strengths' in t or 'weaknesses' in t:
        return 'sw'
    if 'changes' in t and 'existing' not in t and 'new' not in t:
        return 'changes'
    if 'new abilities' in t or 'new spells' in t:
        return 'changes_new'
    if 'existing abilities' in t or 'changes to existing' in t:
        return 'changes_mod'
    if 'removed' in t:
        return 'changes'
    if 'viability' in t:
        return 'viability'
    if 'beginner' in t or 'new player' in t:
        return 'beginner'
    if 'class systems' in t or ('systems' in t and 'class' in t):
        return 'systems'
    if 'bullets and arrows' in t or 'ammo' in t:
        return 'systems'
    if 'rotation' in t:
        return 'rotation'
    if 'multiple targets' in t or 'aoe' in t:
        return 'rotation'
    if t.strip() == 'stats':
        return 'stats'
    if 'race' in t:
        return 'races'
    if 'profession' in t:
        return 'prof'
    if 'talent' in t:
        return 'systems'
    if 'gear' in t or 'loot' in t or 'gem' in t or 'enchant' in t:
        return 'systems'
    if 'leveling' in t:
        return 'beginner'
    if 'macro' in t or 'addon' in t:
        return 'systems'
    if 'faq' in t or 'question' in t:
        return 'systems'
    if t in ('false', '', 'h2', 'h3'):
        return 'systems'
    return 'misc'


def parse_markup(markup):
    markup = re.sub(r'\[toc\]', '', markup)
    markup = re.sub(r'\[pad\]', '\n', markup)
    heads = []
    for m in PAT_HEAD.finditer(markup):
        toc = attr(m.group(2), 'toc')
        title = toc or clean(m.group(3))
        heads.append({'lvl': m.group(1), 'title': title,
                      'begin': m.start(), 'start': m.end()})
    sections = []
    if not heads:
        heads = [{'lvl': 'h2', 'title': 'misc', 'begin': 0, 'start': 0}]

    sec = None
    for i, h in enumerate(heads):
        seg_end = heads[i + 1]['begin'] if i + 1 < len(heads) else len(markup)
        seg = markup[h['start']:seg_end]
        if h['lvl'] == 'h4' and sec is not None:
            sec['flow'].append({'t': 'h4', 'v': unmark(clean(h['title']))})
        else:
            sec = {'lvl': h['lvl'], 'title': h['title'], 'key': section_key(h['title']),
                   'flow': []}
            sections.append(sec)
        pos = 0
        for tbm in PAT_TABLE.finditer(seg):
            before = seg[pos:tbm.start()]
            p = clean(before)
            if p:
                sec['flow'].append({'t': 'p', 'v': p})
            sec['flow'].append({'t': 'tb', 'v': parse_table(tbm.group(1))})
            pos = tbm.end()
        rest = seg[pos:]
        rest = PAT_UL.sub(lambda m: '\n' + m.group(1) + '\n', rest)
        lis = []
        for lim in PAT_LI.finditer(rest):
            icon = attr(lim.group(1), 'icon')
            raw = lim.group(2)
            c = clean(raw)
            if not c:
                continue
            item = {'icon': icon, 'text': c}
            tm = re.match(r'\x03([^\x04]*)\x04', c)
            if tm:
                item['term'] = tm.group(1)
                item['text'] = c[tm.end():].lstrip('\x05 ：:').strip() or c
            lis.append(item)
        if lis:
            sec['flow'].append({'t': 'ul', 'v': lis})
        body = PAT_LI.sub('', rest)
        for para in re.split(r'\n\s*\n', body):
            p = clean(para)
            if p:
                sec['flow'].append({'t': 'p', 'v': p})
    return sections


def merge_sections(sections):
    """同名标准板块归并（保持出现顺序），flow 顺次拼接。"""
    out = {}
    order = []
    for sec in sections:
        k = sec['key']
        if k == 'changes_new' or k == 'changes_mod':
            k = 'changes'
        if k not in out:
            out[k] = {'key': k, 'title': sec['title'], 'flow': []}
            order.append(k)
        out[k]['flow'].extend(sec['flow'])
    return [out[k] for k in order]


def parse_updated(html):
    m = re.search(r'"dateModified":\s*"(\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1).replace('-', '/')
    m = re.search(r'Updated ([A-Z][a-z]{2} \d{1,2}, \d{4})', html)
    if m:
        return m.group(1)
    return ''


def main():
    result = {}
    for cls, spec in SPEC_SLUGS:
        key = '%s_%s' % (cls, spec)
        path = os.path.join(PROBE, key + '.html')
        if not os.path.exists(path):
            print('[missing]', key)
            continue
        html = io.open(path, encoding='utf-8', errors='replace').read()
        blocks = re.findall(PAT_MARKUP, html)
        if not blocks:
            print('[no markup]', key)
            continue
        markup = json.loads(blocks[0])
        sections = merge_sections(parse_markup(markup))
        # 种族勾选表 → 结构化要点（信息等价转文本，丢掉难渲染的表格）
        for sec in sections:
            if sec['key'] != 'races':
                continue
            nf = []
            for f in sec['flow']:
                if f['t'] == 'tb':
                    marks = race_table_rows(f['v'])
                    if marks:
                        nf.append({'t': 'races', 'v': marks})
                        continue
                nf.append(f)
            sec['flow'] = nf
        result[key] = {'updated': parse_updated(html), 'sections': sections}
        ks = [s['key'] for s in sections]
        nflow = sum(len(s['flow']) for s in sections)
        print('%-24s flow=%-3d %s' % (key, nflow, ','.join(ks)))
    io.open(OUT, 'w', encoding='utf-8').write(
        json.dumps(result, ensure_ascii=False, indent=1))
    print('->', OUT)


if __name__ == '__main__':
    main()
