# -*- coding: utf-8 -*-
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core', 'Data', 'Data_DungeonQuests.lua')

raw = io.open(SRC, 'rb').read().decode('utf-8')
assert '\r\n' in raw, 'expect CRLF'

EDITS = []

# (1) 95682 补前置 95663（wowhead breadcrumb 已证实）
EDITS.append((
    '{ 95682, "H", 24, nil, "亡灵卫兵密探", "湿地 - 挖掘场入口旁的山丘", nil, false, nil, {271740, 271732, 271745}',
    '{ 95682, "H", 24, nil, "亡灵卫兵密探", "湿地 - 挖掘场入口旁的山丘", nil, false, {95663}, {271740, 271732, 271745}',
))

# (2) 96395 双阵营
EDITS.append((
    '{ 96395, "A", 10, 15,',
    '{ 96395, nil, 10, 15,',
))

# (3) 1200 双阵营
EDITS.append((
    '{ 1200, "A", 18, 27,',
    '{ 1200, nil, 18, 27,',
))

# (4) sm_library 段新增 96800 Arrow
Q96800 = ('        { 96800, "A", 30, 38, "大法师奥尔韦克", "奥特兰克山脉 9.8,63", nil, false, nil, '
          '{276898, 276899}, "从血色修道院取回《符文大师的失落魔法》，交给奥特兰克山脉的大法师奥尔韦克。", '
          '"书在图书馆尾王奥法师杜安房间右侧的桌上（红色书）。", '
          '{{30,1}, {34,2}, {36,3}, {41,4}, {48,5}}, {273169}, nil, 264265, "大法师奥尔韦克", '
          '{ xp = 2850, money = 4500, rep = { {2740, 100, "肯瑞托"} } } },')
EDITS.append((
    '    ["sm_library"] = {\r\n',
    '    ["sm_library"] = {\r\n' + Q96800 + '\r\n',
))

# (5) PreExtra 补 95663（前置任务在副本外，主表不收）
EDITS.append((
    '    [95737] = { npc = "蓝纳", lv = 24 },\r\n',
    '    [95737] = { npc = "蓝纳", lv = 24 },\r\n    [95663] = { npc = "萨鲁克", lv = 24 },\r\n',
))

for old, new in EDITS:
    n = raw.count(old)
    if n != 1:
        print('FAIL count=%d for: %s' % (n, old[:70]))
        sys.exit(1)
    raw = raw.replace(old, new, 1)

io.open(SRC, 'wb').write(raw.encode('utf-8'))
print('OK 5 edits applied')
