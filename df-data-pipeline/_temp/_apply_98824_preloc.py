# -*- coding: utf-8 -*-
"""98824 前置链落图修复（用户实机反馈 + wowhead npc=1077 #ends 实证）：
  · QuestPreNpcID +[95810] = 1077 —— 98824 详情页点前置节点（95810，起始为物品、行内无
    NPCID）时按 questID 反查落到勘察员维尔加；
  · 98824 行第 16/17 位补 1077 / 勘察员维尔加 —— 98824 本身也在维尔加处接续（Follow-up），
    其详情页起始行与它出现在 95810 后续区的节点都可点落图。幂等。
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r'D:/workspace/DungeonsForever/Core/Data/Data_NPCLoc.lua'
Q = r'D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua'


def load(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def save(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


acts = []
s = load(P)
if '[95810] =' not in s:
    anchor = '    [9052] = 9619,\n'
    if s.count(anchor) != 1:
        raise SystemExit('[ABORT] QuestPreNpcID [9052] 锚点命中 %d 次' % s.count(anchor))
    s = s.replace(anchor, anchor + '    [95810] = 1077,\n', 1)
    save(P, s)
    acts.append('QuestPreNpcID[95810]=1077')
else:
    print('[SAME] QuestPreNpcID[95810] 已存在')

s = load(Q)
old = '{ 98824, "A", 24, nil, nil, nil, "运送失落的圣物", false, {95810}, {271716, 271767, 271766}, "把泰坦圣物带给铁炉堡探险者大厅的高级探险家玛盖拉斯（High Explorer Magellas）。", "「运送失落的圣物」的后续；圣物由尾王遗迹守卫者掉落（#270865）。", nil, {270865}, nil, nil, nil, nil },'
new = '{ 98824, "A", 24, nil, "勘察员维尔加", nil, "运送失落的圣物", false, {95810}, {271716, 271767, 271766}, "把泰坦圣物带给铁炉堡探险者大厅的高级探险家玛盖拉斯（High Explorer Magellas）。", "「运送失落的圣物」的后续，在勘察员维尔加（#1077）处接续；圣物由尾王遗迹守卫者掉落（#270865）。", nil, {270865}, nil, 1077, "勘察员维尔加", nil },'
if new not in s:
    if s.count(old) != 1:
        raise SystemExit('[ABORT] 98824 行锚点命中 %d 次' % s.count(old))
    s = s.replace(old, new, 1)
    save(Q, s)
    acts.append('98824 行补 1077')
else:
    print('[SAME] 98824 行已是新值')

print('[OK] ' + ' / '.join(acts) if acts else '[SAME] 全部已应用')
