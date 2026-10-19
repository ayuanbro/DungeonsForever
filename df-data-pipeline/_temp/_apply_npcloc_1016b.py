# -*- coding: utf-8 -*-
"""补录本轮任务改动牵涉的 NPC 地图定位（Data_NPCLoc.lua）。

数据源：
  [264265] 大法师奥尔韦克   QuestieDB npc_spawns areaID 36（奥特兰克山脉）→ uiMapID 1416
                           坐标 (10.72, 64.07)，与任务页起始地点一致
  [2787]   萨鲁克          QuestieDB npc_spawns areaID 45（阿拉希高地）→ uiMapID 1417
                           坐标 (74.54, 35.64)
  [13155]  亡灵卫兵密探     wowhead 玩家实测 (51.4, 59.2)，湿地 → uiMapID 1437
QuestPreNpcID:
  [95663] = 2787   95663 是本表 95682 的前置，登记在 DungeonQuestPreExtra，
                   需 QuestPreNpcID 才能在前置链上点击出航点。
幂等：已存在即跳过。
"""
import io
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'Core', 'Data', 'Data_NPCLoc.lua')

s = io.open(P, encoding='utf-8', newline='').read()
acts = []


def insert_sorted(text, nid, row, tag):
    if '[%d] =' % nid in text:
        print('[SAME]', tag)
        return text
    m_open = re.search(r'\nns\.NPCLoc = \{', text)
    if not m_open:
        raise SystemExit('[ABORT] NPCLoc 表头找不到')
    end = text.index('\n}', m_open.end())
    seg = text[m_open.end():end]
    keys = [(int(m.group(1)), m.start()) for m in re.finditer(r'\n    \[(\d+)\] =', seg)]
    bigger = [k for k in keys if k[0] > nid]
    pos = (m_open.end() + min(bigger, key=lambda x: x[1])[1]) if bigger else end
    print('[ADD]', tag)
    return text[:pos] + '\n' + row + text[pos:]


ROWS = [
    (2787,   '    [2787] = { 1417, 74.5, 35.6, "阿拉希高地" },'),
    (13155,  '    [13155] = { 1437, 51.4, 59.2, "湿地" },'),
    (264265, '    [264265] = { 1416, 10.7, 64.1, "奥特兰克山脉" },'),
]
for nid, row in ROWS:
    before = s
    s = insert_sorted(s, nid, row, 'NPCLoc[%d]' % nid)
    if s != before:
        acts.append(str(nid))

if '[95663] =' not in s:
    m = re.search(r'(    \[95737\] = 3970,\n)', s)
    if not m:
        raise SystemExit('[ABORT] QuestPreNpcID [95737] 锚点未命中')
    s = s[:m.end()] + '    [95663] = 2787,\n' + s[m.end():]
    acts.append('PreNpcID[95663]')
else:
    print('[SAME] PreNpcID[95663]')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('[OK] Data_NPCLoc.lua ' + (' + '.join(acts) if acts else '无改动'))
