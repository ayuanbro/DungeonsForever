# -*- coding: utf-8 -*-
"""解析 wowhead tier-list guide 正文 markup：抽出梯队结构 + 说明文本。"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '_tier_probe')

STR = r'("(?:[^"\\]|\\.)*")'


def load_markup(path):
    h = open(path, encoding='utf-8').read()
    m = re.search(r'WH\.markup\.printHtml\(\s*' + STR, h, re.S)
    if not m:
        return ''
    return json.loads(m.group(1))


def clean(s):
    s = re.sub(r'\[/?[^\]]*\]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


for key in ('dps', 'tank', 'healer'):
    mk = load_markup(os.path.join(D, key + '.html'))
    print('=' * 74)
    print('### %s   markup len=%d' % (key, len(mk)))
    tl = re.search(r'\[tier-list[^\]]*\](.*?)\[/tier-list\]', mk, re.S)
    rows = []
    if tl:
        for tier in re.finditer(r'\[tier\](.*?)\[/tier\]', tl.group(1), re.S):
            blk = tier.group(1)
            lab = re.search(r'\[tier-label[^\]]*\]\s*([A-Za-z][+-]?)\s*\[/tier-label\]', blk)
            badges = re.findall(r'\[spec-badge=([a-z0-9\-]+)\]', blk)
            rows.append((lab.group(1) if lab else '?', badges))
    for lab, badges in rows:
        print('  %-3s : %s' % (lab, ', '.join(badges) if badges else '(空)'))
    print('  -- 小标题 --')
    for m in re.finditer(r'\[h([23])[^\]]*\](.*?)\[/h\1\]', mk):
        print('   h%s %s' % (m.group(1), clean(m.group(2))))
    print('  -- 列表项 --')
    for m in re.finditer(r'\[li\](.*?)\[/li\]', mk, re.S):
        print('   * %s' % clean(m.group(1))[:110])
    body = mk
    body = re.sub(r'\[tier-list[^\]]*\].*?\[/tier-list\]', '<<TIER>>', body, flags=re.S)
    print('  -- 正文（去表格，前 1400 字）--')
    print('   ' + clean(body)[:1400])
