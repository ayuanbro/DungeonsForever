# -*- coding: utf-8 -*-
"""从新闻页原始 HTML 里挖出正文载荷（jina 渲染不出的动态任务清单）。"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
H = io.open(os.path.join(HERE, '_rl_raw', 'news.html'), encoding='utf-8', errors='replace').read()

PAT = r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")'
blocks = re.findall(PAT, H)
print('printHtml blocks:', len(blocks))
for i, b in enumerate(blocks):
    s = json.loads(b)
    print('=' * 30, 'block', i, 'len', len(s))
    print(s[:6000])
