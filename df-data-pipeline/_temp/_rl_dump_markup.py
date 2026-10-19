# -*- coding: utf-8 -*-
"""把新闻页 / 攻略页的正文载荷（BBCode 风格 markup）导成纯文本，便于阅读与核对。"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")'


def dump(name, out):
    src = io.open(os.path.join(HERE, '_rl_raw', name + '.html'), encoding='utf-8', errors='replace').read()
    blocks = re.findall(PAT, src)
    print(name, 'blocks', len(blocks))
    parts = []
    for i, b in enumerate(blocks):
        s = json.loads(b)
        parts.append('===== BLOCK %d (len %d) =====\n%s' % (i, len(s), s))
    io.open(out, 'w', encoding='utf-8').write('\n\n'.join(parts))
    print(' ->', out, sum(len(p) for p in parts))


dump('news', os.path.join(HERE, '_rl_news_markup.txt'))
dump('guide', os.path.join(HERE, '_rl_guide_markup.txt'))
dump('zone', os.path.join(HERE, '_rl_zone_markup.txt'))
