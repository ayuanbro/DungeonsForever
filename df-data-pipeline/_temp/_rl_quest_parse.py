# -*- coding: utf-8 -*-
"""解析 10 个洛丹伦废墟任务页：标题 / 等级 / 阵营 / 起止 NPC / 目标 / 说明 / 奖励 / 收获。"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_rl_quests')
QUESTS = [92401, 92415, 92421, 92422, 95189, 95195, 95204, 95216, 95250, 97288]


def field(txt, label, nxt, flags=re.S):
    m = re.search(re.escape(label) + r'\s*(.*?)(?=' + nxt + r')', txt, flags)
    return m.group(1).strip() if m else None


def clean(s):
    if s is None:
        return s
    s = re.sub(r'\[!\[Image[^\]]*\]\([^)]*\)\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


for q in QUESTS:
    p = os.path.join(CACHE, 'q%d.txt' % q)
    t = io.open(p, encoding='utf-8', errors='replace').read()
    # 标题
    title = None
    m = re.search(r'^Title:\s*(.+)$', t, re.M)
    if m:
        title = m.group(1).strip()
    # infobox 行
    box = field(t, '| * 等级', r'\|\| ')
    # 目标：第一个 "# 标题" 之后的正文行
    obj = None
    m = re.search(r'# [^\n]+\n\n(.+?)\n(\| |## )', t)
    if m:
        obj = m.group(1).strip()
    desc = field(t, '## 描述', r'## ')
    print('=' * 70)
    print('Q%d  %s' % (q, clean(title)))
    print('  BOX :', clean(box))
    print('  OBJ :', clean(obj))
    print('  DESC:', (clean(desc) or '')[:300])
