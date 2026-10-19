# -*- coding: utf-8 -*-
"""挖掘场任务第二批：wowhead 攻略页改版（联盟 7 / 部落 4）新增 4 个任务落库。

  95682 Open the Maw        H  起始 13155 亡灵卫兵密探（副本外，wowhead 无坐标）
  98823 Earthen Echo        H  前置 95664 长者知识（交穆恩·大地之怒，无 npc id）
  95809 Heartwoven          A  前置 95647 灌木丛里的东西（物品 270901 提供起始，交凯特林 1480）
  98824 Prehistoric Prism   A  前置 95810 运送失落的圣物（物品 270865，交铁炉堡）
顺手修：95697 口味变了第 10 位漏了 itemchoices（280766/280805）。幂等。
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r'D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua'


def load(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def save(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


s = load(P)
acts = []

# ── 1. 挖掘场段尾追加 4 行（锚 = 95810 行 + 段收尾） ──
ROW95682 = '        { 95682, "H", 24, nil, "亡灵卫兵密探", nil, nil, false, nil, {271740, 271732, 271745}, "在挖掘场杀 2 名龙喉破坏者和 4 名龙喉守卫，带着战利品回到副本外的亡灵卫兵密探处。", "龙喉急件（#284844）由副本内龙喉单位掉落；wowhead 标注起始点与前置关系待确认（TBD）。", nil, {284844}, nil, 13155, "亡灵卫兵密探", nil },\n'
ROW98823 = '        { 98823, "H", 24, nil, nil, nil, "长者知识", false, {95664}, {271766, 271767, 271719}, "把泰坦圣物带给莫高雷西北天空守望者高地的穆恩·大地之怒（Muln Earthfury）。", "「长者知识」的后续；圣物由尾王遗迹守卫者掉落（#270865）。", nil, {270865}, nil, nil, nil, nil },\n'
ROW95809 = '        { 95809, "A", 24, nil, nil, nil, "灌木丛里的东西", false, {95647}, {1710, 3827, 2459, 280766}, "把编草心带回米奈希尔港交给凯特林·格拉斯曼。", "完成「灌木丛里的东西」后阿尔丁给的信物编草心（#270901，Reed-woven Heart）开启本任务。", nil, {270901}, nil, nil, nil, nil },\n'
ROW98824 = '        { 98824, "A", 24, nil, nil, nil, "运送失落的圣物", false, {95810}, {271716, 271767, 271766}, "把泰坦圣物带给铁炉堡探险者大厅的高级探险家玛盖拉斯（High Explorer Magellas）。", "「运送失落的圣物」的后续；圣物由尾王遗迹守卫者掉落（#270865）。", nil, {270865}, nil, nil, nil, nil },\n'
if '{ 95809,' not in s:
    anchor = '{ 95810, "A", 24, 31, nil, nil, nil, false, nil, nil, "把泰坦圣物带给湿地的勘察员维尔加。", "拾取泰坦圣物（#270865）开启；联盟方交给维尔加挖掘场的勘察员维尔加（#1077）。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, {270865}, nil, nil, nil, { xp = 630 } },\n    },'
    if s.count(anchor) != 1:
        raise SystemExit('[ABORT] 挖掘场段尾锚点命中 %d 次' % s.count(anchor))
    repl = anchor[:-len('    },')] + ROW95682 + ROW98823 + ROW95809 + ROW98824 + '    },'
    s = s.replace(anchor, repl, 1)
    acts.append('+4 任务行')

# ── 2. 95697 奖励补 itemchoices ──
old = '{ 95697, "H", 24, 31, nil, "奥格瑞玛", nil, false, nil, {250185, 250077},'
new = '{ 95697, "H", 24, 31, nil, "奥格瑞玛", nil, false, nil, {280766, 280805, 250185, 250077},'
if old in s:
    if s.count(old) != 1:
        raise SystemExit('[ABORT] 95697 锚点命中 %d 次' % s.count(old))
    s = s.replace(old, new, 1)
    acts.append('95697 奖励+三选一')

if acts:
    save(P, s)
    print('[OK] ' + ' / '.join(acts))
else:
    print('[SAME] 已应用')
