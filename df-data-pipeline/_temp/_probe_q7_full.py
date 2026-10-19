# -*- coding: utf-8 -*-
"""判断 DG.ShowQuestTip 里 q[7] 兜底分支（显示英文静态前置名）到底还能不能删。

问题背景：行 2029~2050 的提示框前置行逻辑是
    q[9] 有 -> 逐环 DG.QuestName(seg)；拿不到客户端名就退 q[7]（站点英文名）
    q[9] 空 -> 直接显示 q[7]

本脚本回答三件事：
  1) q[7] 非空的行里，有多少同时有可用的「数字前置 ID」（= 能改成「任务 #ID」文案）；
  2) 只有 q[7]、没有任何数字 ID 的行有多少（= 删掉就真丢信息）；
  3) 这些行分别在哪些副本、样例长什么样。
"""
import os, re, sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'Core', 'Data', 'Data_DungeonQuests.lua')
print('### 目标：', TARGET)
lua = lua51.LuaRuntime(unpack_returned_tuples=True)
ns = lua.table()
chunk = lua.eval('function(src,name,ns) local f=assert(loadstring(src,name)) return f(name,ns) end')
chunk(open(TARGET, encoding='utf-8').read(), 'DQ', ns)

EN = re.compile(r'[A-Za-z]{2,}')
DQ = ns['DungeonQuests']

raw = {}   # (副本键, 行序号) -> 记录；q[1] 才是真正的 questID
for did, rows in DQ.items():
    for idx, q in rows.items():
        segs = []
        if q[9] is not None:
            for k in q[9].keys():
                segs.append(q[9][k])
        nums = [s for s in segs if isinstance(s, (int, float))]
        strs = [s for s in segs if not isinstance(s, (int, float))]
        key = (str(did), int(idx))
        raw[key] = dict(
            did=str(did), idx=int(idx), qid=int(q[1]),
            q7=str(q[7]) if q[7] else '',
            nums=[int(x) for x in nums], strs=[str(s) for s in strs],
        )

tot = len(raw)
q7_rows = {k: v for k, v in raw.items() if v['q7'].strip()}
q7_en = {k: v for k, v in q7_rows.items() if EN.search(v['q7'])}

has_num = {k: v for k, v in q7_en.items() if v['nums']}
only_str = {k: v for k, v in q7_en.items() if v['strs'] and not v['nums']}
nothing = {k: v for k, v in q7_en.items() if not v['nums'] and not v['strs']}

print('任务行总数                 =', tot)
print('q[7] 非空                   =', len(q7_rows))
print('  └ 其中含英文              =', len(q7_en))
print()
print('★ 英文 q[7] 且 q[9] 有数字ID =', len(has_num), '  → 可安全改「任务 #ID」')
print('★ 英文 q[7] 且 q[9] 只有字符串 =', len(only_str), '  → 字符串段本身是英文（另一路问题）')
print('★ 英文 q[7] 且 q[9] 完全没有  =', len(nothing), '  → 删 q[7] 会真丢信息')
print()

if nothing:
    print('--- q[9] 完全没有的英文 q[7] 行（删了会丢信息的） ---')
    for k, v in list(nothing.items())[:25]:
        print('   副本%-16s 任务%-7s q7=%-45s strs=%s' % (v['did'], v['qid'], v['q7'], v['strs']))
    print()

if only_str:
    print('--- q[9] 只有字符串段的英文行 ---')
    for k, v in list(only_str.items())[:25]:
        print('   副本%-16s 任务%-7s q7=%-45s strs=%s' % (v['did'], v['qid'], v['q7'], v['strs']))
    print()

print('--- 英文 q[7] 样例（前 20，看是不是站点口径的英文原名） ---')
for k, v in list(q7_en.items())[:20]:
    print('   副本%-16s 任务%-7s nums=%-22s q7=%s' % (v['did'], v['qid'], v['nums'], v['q7']))
print()

# 数字前置 ID 是否能在本表里找到（= 是不是 28 副本之外的任务）
def in_table(qid):
    return qid in raw

outside = set()
for k, v in q7_en.items():
    for n in v['nums']:
        if not in_table(n):
            outside.add(n)
print('英文 q[7] 行引用的「表外前置任务 ID」共 %d 个' % len(outside))
print('   样例:', sorted(outside)[:20])
