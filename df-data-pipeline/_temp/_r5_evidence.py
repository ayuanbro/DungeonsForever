# -*- coding: utf-8 -*-
"""第五轮证据：① 生成物中各处修正后的实际文本；② 译源 diff（vs /tmp/trans_snap5）。"""
import difflib
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TD = os.path.join(ROOT, '_temp', '_cg_trans')
SNAP = os.path.join(ROOT, '_temp', '_trans_snap5_bak')


def grep(rel, needles):
    p = os.path.join(ROOT, rel)
    txt = io.open(p, encoding='utf-8').read()
    lines = txt.split('\n')
    for nd in needles:
        hits = [i + 1 for i, l in enumerate(lines) if nd in l]
        print('  [%s] %d 处 @ %s' % (nd, len(hits), hits[:6]))
        for i in hits[:2]:
            l = lines[i - 1]
            j = l.find(nd)
            print('      L%d: …%s…' % (i, l[max(0, j - 40):j + len(nd) + 60]))


print('########## ① 生成物 Core/Data/Data_ClassGuide.lua（zhCN）逐处确认 ##########')
grep('Core/Data/Data_ClassGuide.lua', [
    '联盟盗贼通常会优先选择',
    '部落盗贼会更倾向于',
    '随《无限》重做',
    '高阶天裔',
    '对野兽和龙类的伤害',
    '我们现有的技能和天赋有许多改动',
    '现在使反弹的伤害按施法者的法术强度缩放',
    '延长我们的|s1430|和|s8938|的 HoT 持续时间',
    '满级时为我们的 HoT 提供 5% 加成',
    '现在成为基础技能，且可由施法触发',
])
print()
print('########## ② 遗留：不该再出现者（应各为 0） ##########')
for bad in ['怀旧服', '资料片']:
    txt = io.open(os.path.join(ROOT, 'Core/Data/Data_ClassGuide.lua'), encoding='utf-8').read()
    print('  "%s" 出现次数 = %d' % (bad, txt.count(bad)))

print()
print('########## ③ 译源 diff（vs 第五轮前快照 /tmp/trans_snap5） ##########')
changed = []
for fn in sorted(os.listdir(TD)):
    a = os.path.join(SNAP, fn)
    b = os.path.join(TD, fn)
    if not os.path.exists(a) or not os.path.exists(b):
        continue
    ta = io.open(a, encoding='utf-8').read().split('\n')
    tb = io.open(b, encoding='utf-8').read().split('\n')
    if ta != tb:
        changed.append(fn)
        d = list(difflib.unified_diff(ta, tb, lineterm='', n=0))
        print('--- %s (%d diff lines) ---' % (fn, len(d)))
        for l in d[2:]:
            print('   ' + l[:220])
print('变更文件:', changed)
