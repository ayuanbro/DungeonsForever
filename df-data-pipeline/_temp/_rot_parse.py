# -*- coding: utf-8 -*-
"""解析 wowhead forever 各专精 Level 20/30 指南页的 rotation 章节 -> _temp/_rot_data.json"""
import glob
import html as H
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))

CLS_ZH = {
    'warrior': '战士', 'paladin': '圣骑士', 'hunter': '猎人', 'rogue': '潜行者',
    'priest': '牧师', 'shaman': '萨满', 'mage': '法师', 'warlock': '术士', 'druid': '德鲁伊',
}
SPEC_ZH = {
    'arms': '武器', 'fury': '狂暴', 'protection': '防护', 'holy': '神圣', 'retribution': '惩戒',
    'beast-mastery': '兽王', 'marksmanship': '射击', 'survival': '生存',
    'assassination': '刺杀', 'combat': '战斗', 'subtlety': '敏锐',
    'discipline': '戒律', 'shadow': '暗影', 'elemental': '元素', 'enhancement': '增强',
    'restoration': '恢复', 'arcane': '奥术', 'fire': '火焰', 'frost': '冰霜',
    'affliction': '痛苦', 'demonology': '恶魔', 'destruction': '毁灭',
    'balance': '平衡', 'feral': '野性',
}
ORDER = ['warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman', 'mage', 'warlock', 'druid']


def plain(seg):
    s = re.sub(r'<script.*?</script>', ' ', seg, flags=re.S | re.I)
    s = re.sub(r'<style.*?</style>', ' ', s, flags=re.S | re.I)
    s = re.sub(r'<img[^>]*>', '', s)
    s = re.sub(r'<span class="tinyicontxt">(.*?)</span>', r'\1', s, flags=re.S)
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'</(p|li|div|tr|td|h\d)>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = H.unescape(s).replace('\u00a0', ' ')
    s = re.sub(r'window\.tude.*$', ' ', s, flags=re.S)
    s = re.sub(r'tude\.[a-z]+\.push\([^)]*;?', ' ', s)
    return ' '.join(s.split())


def list_items(body):
    out = []
    for m in re.finditer(r'<li[^>]*>(.*?)(?=</li>|<li[^>]*>|</ol>|</ul>|$)', body, re.S):
        t = plain(m.group(1))
        if t:
            out.append(t)
    return out


def br_steps(body):
    """无列表时按 <br> 切行；整行 <b>…</b> 视作小节名。"""
    out = []
    name, items = '', []
    for part in re.split(r'<br\s*/?>', body):
        b = re.fullmatch(r'\s*<b>(.*?)</b>\s*', part, re.S)
        if b:
            if items:
                out.append({'name': name, 'kind': 'steps', 'items': items, 'note': ''})
                items = []
            name = plain(b.group(1))
            continue
        t = plain(part)
        if t:
            items.append(t)
    if items:
        out.append({'name': name, 'kind': 'steps', 'items': items, 'note': ''})
    return out


def strip_lists(body):
    s = re.sub(r'<(ol|ul)[^>]*>.*?</\1>', '', body, flags=re.S)
    s = re.sub(r'<li[^>]*>.*?</li>', '', s, flags=re.S)
    s = re.sub(r'<li[^>]*>.*$', '', s, flags=re.S)
    return s


def parse_page(path):
    h = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'<h2 id="rotation"[^>]*>(.*?)</h2>', h, re.S)
    if not m:
        return None
    title = plain(m.group(1))
    start = m.end()
    nxt = re.search(r'<h2 ', h[start:])
    seg = h[start:start + (nxt.start() if nxt else 30000)]

    marks = list(re.finditer(r'<h3 id="([^"]*)"[^>]*>(.*?)</h3>', seg, re.S))
    blocks = []

    def emit(prefix_html, name, force_prose=False):
        if force_prose:
            note = plain(prefix_html)
            if note:
                blocks.append({'name': name, 'kind': 'prose', 'items': [], 'note': note})
            return
        if '<li' in prefix_html:
            items = list_items(prefix_html)
            note = plain(strip_lists(prefix_html))
            if items:
                blocks.append({'name': name, 'kind': 'list', 'items': items,
                               'note': note if note and note != name else ''})
            elif note:
                blocks.append({'name': name, 'kind': 'prose', 'items': [], 'note': note})
            return
        steps = br_steps(prefix_html)
        if steps:
            if name and len(steps) > 1:
                blocks.append({'name': name, 'kind': 'steps', 'items': steps[0]['items'],
                               'note': steps[0]['note']})
                for s in steps[1:]:
                    blocks.append(s)
            else:
                for s in steps:
                    if name and not s['name']:
                        s['name'] = name
                    blocks.append(s)
        else:
            note = plain(prefix_html)
            if note:
                blocks.append({'name': name, 'kind': 'prose', 'items': [], 'note': note})

    if marks:
        emit(seg[:marks[0].start()], '', force_prose=True)
        for i, mm in enumerate(marks):
            bstart = mm.end()
            bend = marks[i + 1].start() if i + 1 < len(marks) else len(seg)
            emit(seg[bstart:bend], plain(mm.group(2)))
    else:
        emit(seg, '')
    return {'title': title, 'blocks': blocks}


def role_of(cls, spec):
    if spec in ('protection',):
        return 'tank'
    if spec in ('holy', 'restoration', 'discipline'):
        return 'healer'
    return 'dps'


def main():
    out = []
    for path in sorted(glob.glob(os.path.join(HERE, '_rot_pages', '*.html'))):
        base = os.path.basename(path)[:-5]
        m = re.match(r'([a-z\-]+)_([a-z\-]+)_l(\d+)', base)
        cls, spec, lv = m.group(1), m.group(2), int(m.group(3))
        rec = parse_page(path)
        if rec is None:
            print('NO-ROTATION', base)
            continue
        rec.update({'key': base, 'cls': cls, 'spec': spec, 'lv': lv,
                    'role': role_of(cls, spec), 'cls_zh': CLS_ZH[cls], 'spec_zh': SPEC_ZH[spec]})
        out.append(rec)
    out.sort(key=lambda r: (ORDER.index(r['cls']), r['spec'], r['lv']))
    dst = os.path.join(HERE, '_rot_data.json')
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('parsed pages:', len(out), '/ 54')
    print('%-26s %-4s %-6s %-6s %s' % ('key', 'lv', 'items', 'blocks', 'sections'))
    tot = 0
    for r in out:
        n = sum(len(b['items']) for b in r['blocks'])
        tot += n
        secs = ['%s[%s:%d]' % (b['name'] or '(intro)', b['kind'][0], len(b['items'])) for b in r['blocks']]
        print('%-26s L%-3d %-6d %-6d %s' % (r['key'], r['lv'], n, len(r['blocks']), ' | '.join(secs)))
    print('total items:', tot)
    print('written ->', dst)


if __name__ == '__main__':
    main()
