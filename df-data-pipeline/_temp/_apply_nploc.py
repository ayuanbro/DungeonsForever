# -*- coding: utf-8 -*-
"""NPCLoc 补录挖掘场新增任务的 7 个起始/交接 NPC（2026-10-02）。

数据源：wowhead forever/cn NPC 页 SSR g_mapperData（首点位，原管道同口径）：
  [956]  多林·桑布雷德    赤脊山 1433  25.6,46.6
  [1077] 勘察员维尔加     湿地 1437    38.8,52.2
  [1244] 绿色守卫者雷希耶尔 湿地 1437  56.2,40.4
  [1480] 凯特林·格拉斯曼  湿地 1437    11.6,58.4
  [2093] 埃纳尔·石钳      湿地 1437    49.8,39.4
  [2094] 詹姆斯·哈洛兰    湿地 1437    8.4,55.8
  [3970] 蓝纳             灰谷 1440    35.0,48.4
uiMapID 与表内既有同图条目口径一致（赤脊山 1433 / 湿地 1437 / 灰谷 1440）。
幂等：已应用报 [SAME]。
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = r'D:/workspace/DungeonsForever'


def load(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def save(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def insert_sorted(text, nid, row, tag):
    """在 ns.NPCLoc 主表（第一个 ns.NPCLoc = { 到其列 0 收尾 }）内按 id 升序插入 row。"""
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
    if bigger:
        pos = m_open.end() + min(bigger, key=lambda x: x[1])[1]
    else:
        pos = end
    return text[:pos] + '\n' + row + text[pos:]


p = ROOT + '/Core/Data/Data_NPCLoc.lua'
s = load(p)
ROWS = [
    (956,  '    [956] = { 1433, 25.6, 46.6, "赤脊山" },'),
    (1077, '    [1077] = { 1437, 38.8, 52.2, "湿地" },'),
    (1244, '    [1244] = { 1437, 56.2, 40.4, "湿地" },'),
    (1480, '    [1480] = { 1437, 11.6, 58.4, "湿地" },'),
    (2093, '    [2093] = { 1437, 49.8, 39.4, "湿地" },'),
    (2094, '    [2094] = { 1437, 8.4, 55.8, "湿地" },'),
    (3970, '    [3970] = { 1440, 35.0, 48.4, "灰谷" },'),
]
acts = []
for nid, row in ROWS:
    before = s
    s = insert_sorted(s, nid, row, 'NPCLoc[%d]' % nid)
    if s != before:
        acts.append(str(nid))

# QuestPreNpcID：[469] = 2093（升序区，[389] 行后）、[95737] = 3970（表尾追加）
if '[469] =' not in s:
    m = re.search(r'(    \[389\] = 1646,\n)', s)
    if not m:
        raise SystemExit('[ABORT] QuestPreNpcID [389] 锚点未命中')
    s = s[:m.end()] + '    [469] = 2093,\n' + s[m.end():]
    acts.append('PreNpcID[469]')
if '[95737] =' not in s:
    m = re.search(r'(    \[92752\] = 11026,\n)', s)
    if not m:
        raise SystemExit('[ABORT] QuestPreNpcID 表尾锚点未命中')
    s = s[:m.end()] + '    [95737] = 3970,\n' + s[m.end():]
    acts.append('PreNpcID[95737]')

save(p, s)
print('[OK] Data_NPCLoc.lua ' + (' + '.join(acts) if acts else '无改动'))

# ── 任务表：95647 起始地点修正（凯特林在湿地，灰谷是蓝纳） + [469] NPC 官方名 ──
p = ROOT + '/Core/Data/Data_DungeonQuests.lua'
s = load(p)
acts = []
old = '{ 95647, "A", 24, 31, "凯特林·格拉斯曼", "灰谷",'
new = '{ 95647, "A", 24, 31, "凯特林·格拉斯曼", "湿地 - 米奈希尔港南 11.6,58.4",'
if old in s:
    if s.count(old) != 1:
        raise SystemExit('[ABORT] 95647 锚点命中 %d 次' % s.count(old))
    s = s.replace(old, new, 1)
    acts.append('95647 起始地点 灰谷→湿地')
old2 = '[469] = { npc = "艾纳尔·石握", lv = 18 },'
new2 = '[469] = { npc = "埃纳尔·石钳", lv = 18 },'
if old2 in s:
    s = s.replace(old2, new2, 1)
    acts.append('PreExtra[469] 名→埃纳尔·石钳')
if acts:
    save(p, s)
    print('[OK] Data_DungeonQuests.lua ' + ' / '.join(acts))
else:
    print('[SAME] Data_DungeonQuests.lua 已是新值')
