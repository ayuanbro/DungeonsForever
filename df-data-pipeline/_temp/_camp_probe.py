# -*- coding: utf-8 -*-
"""临时探针：打印各专业营地档位的技能值分布（用于设计总览表格列）。"""
import sys, prof_probe as P

lua = P.load()
D = lua.eval('TF_NS.ProfData')
order = D['order']
allv = {}
print('%-16s %-24s %s' % ('slug', 'levels', '#'))
for i in range(1, len(order) + 1):
    slug = order[i]
    p = D['pro'][slug]
    camp = p['camp']
    if camp is None:
        continue
    lv = [camp[j][4] for j in range(1, len(camp) + 1)]
    for v in lv:
        allv[v] = allv.get(v, 0) + 1
    print('%-16s %-24s %d' % (slug, str(lv), len(lv)))
print()
print('档位值 → 出现次数：', dict(sorted(allv.items())))
print('最大档位数：', max(len(D['pro'][order[i]]['camp'] or []) for i in range(1, len(order) + 1) if D['pro'][order[i]]['camp']))
