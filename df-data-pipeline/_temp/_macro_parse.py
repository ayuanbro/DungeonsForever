# -*- coding: utf-8 -*-
"""解析 wowhead Classic 职业宏指南：按带 id 的 h2/h3 分段，取 pre.code / div.box 两种代码块。"""
import html as H
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

PAGES = [
    ('战士', '防护坦克', 'warrior_tank', '_temp/_macro_pages/warrior_tank.html', '_temp/_macro_probe2/warrior_tank_cn.html'),
    ('圣骑士', '神圣治疗', 'paladin_healer', '_temp/_macro_pages/paladin_healer.html', '_temp/_macro_cn/paladin_healer.html'),
    ('圣骑士', '惩戒输出', 'paladin_dps', '_temp/_macro_pages/paladin_dps.html', '_temp/_macro_cn/paladin_dps.html'),
    ('猎人', '兽王 / 射击 / 生存', 'hunter_dps', '_temp/_macro_pages/hunter_dps.html', '_temp/_macro_cn/hunter_dps.html'),
    ('潜行者', '战斗 / 刺杀 / 敏锐', 'rogue_dps', '_temp/_macro_pages/rogue_dps.html', '_temp/_macro_probe2/rogue_dps_cn.html'),
    ('牧师', '神圣 / 戒律治疗', 'priest_healer', '_temp/_macro_pages/priest_healer.html', '_temp/_macro_cn/priest_healer.html'),
    ('萨满', '恢复治疗', 'shaman_healer', '_temp/_macro_pages/shaman_healer.html', '_temp/_macro_cn/shaman_healer.html'),
    ('法师', '冰霜 / 火焰 / 奥术', 'mage_dps', '_temp/_macro_pages/mage_dps.html', '_temp/_macro_cn/mage_dps.html'),
    ('术士', '痛苦 / 恶魔 / 毁灭', 'warlock_dps', '_temp/_macro_pages/warlock_dps.html', '_temp/_macro_cn/warlock_dps.html'),
    ('德鲁伊', '恢复治疗', 'druid_healer', '_temp/_macro_pages/druid_healer.html', '_temp/_macro_cn/druid_healer.html'),
]

HEAD = re.compile(r'<h([23])\s+([^>]*?)>(.*?)</h\1>', re.S)
CODE_RE = re.compile(r'<pre class="code[^"]*">(.*?)</pre>|<div class="box"[^>]*>(.*?)</div>', re.S)


def clean_code(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = s.replace('/<wbr>', '/').replace('<wbr>', '')
    s = re.sub(r'<[^>]+>', '', s)
    s = H.unescape(s)
    lines = [ln.rstrip() for ln in s.split('\n')]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines)


def plain(s):
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = H.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def parse(path):
    if not os.path.exists(path):
        return []
    h = open(path, encoding='utf-8', errors='replace').read()
    cut = h.find('class="comment-body')
    if cut > 0:
        h = h[:cut]
    marks = [m for m in HEAD.finditer(h) if 'id="' in m.group(2)]
    out = []
    section = ''
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(h)
        seg = h[m.end():end]
        title = plain(m.group(3))
        if m.group(1) == '2':
            section = title
        hits = list(CODE_RE.finditer(seg))
        if not hits:
            continue
        codes = [clean_code(x.group(1) if x.group(1) is not None else x.group(2)) for x in hits]
        codes = [c for c in codes if c.strip()]
        if not codes:
            continue
        after = seg[hits[-1].end():]
        desc = plain(re.split(r'<hr\s*/?>', after)[0])
        if len(desc) < 12:
            desc = plain(seg[:hits[0].start()])
        out.append({'section': section, 'title': title, 'codes': codes, 'desc': desc})
    return out


def main():
    data = []
    for cls, spec, key, en_p, cn_p in PAGES:
        data.append({'key': key, 'cls': cls, 'spec': spec, 'cn': parse(cn_p), 'en': parse(en_p)})
    json.dump(data, open('_temp/_macro_data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    tc = te = tk = 0
    for it in data:
        c = sum(len(x['codes']) for x in it['cn'])
        e = sum(len(x['codes']) for x in it['en'])
        tc += c
        te += e
        tk += len(it['cn'])
        print('%-14s %-6s cn=%2d条/%-2d码  en=%2d条/%-2d码 | %s' % (
            it['key'], it['cls'], len(it['cn']), c, len(it['en']), e,
            ' / '.join(x['title'] for x in it['cn'])[:90]))
    print('合计 CN %d 条（%d 段码） / EN %d 条（%d 段码）' % (tk, tc, sum(len(x['en']) for x in data), te))


if __name__ == '__main__':
    main()
