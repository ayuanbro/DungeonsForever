# -*- coding: utf-8 -*-
"""统计任务数据的 q[7]（静态前置名兜底）与 q[9] 字符串段里还有多少英文。
   用途：判断「任务提示框 前置行显示英文」到底是数据层没中文化，还是 UI 层兜底选择问题。"""
import os, re
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
lua = lua51.LuaRuntime(unpack_returned_tuples=True)
ns = lua.table()
chunk = lua.eval('function(src,name,ns) local f=assert(loadstring(src,name)) return f(name,ns) end')
chunk(open(os.path.join(ROOT,'Core','Data','Data_DungeonQuests.lua'),encoding='utf-8').read(),'DQ',ns)

DQ = ns['DungeonQuests']
EN = re.compile(r'[A-Za-z]{2,}')
tot=q7_used=q7_en=seg_str=seg_str_en=0
samples_q7=[]; samples_seg=[]
for did, rows in DQ.items():
    for qid, q in rows.items():
        tot += 1
        q7 = q[7]; q9 = q[9]
        if q7 and str(q7).strip():
            q7_used += 1
            if EN.search(str(q7)):
                q7_en += 1
                if len(samples_q7)<15: samples_q7.append((q[1], str(q7)))
        if q9 is not None:
            for s in q9.values():
                if not isinstance(s,(int,float)):
                    seg_str += 1
                    if EN.search(str(s)):
                        seg_str_en += 1
                        if len(samples_seg)<15: samples_seg.append((q[1], str(s)))
print('任务行总数        =', tot)
print('q[7] 非空          =', q7_used)
print('★ q[7] 含英文      =', q7_en)
print('q[9] 字符串段      =', seg_str)
print('★ 其中含英文       =', seg_str_en)
print('--- q[7] 英文样例 ---')
for s in samples_q7: print('   ', s)
print('--- q[9] 字符串段英文样例 ---')
for s in samples_seg: print('   ', s)
