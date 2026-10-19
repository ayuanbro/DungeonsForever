# -*- coding: utf-8 -*-
"""导出 30级 卷在 enUS 覆盖层里未命中的中文串（去重、按频次）。"""
import collections
import re

t = open('Core/Data/enUS/Data_BIS.lua', encoding='utf-8').read()
seg = t[t.find('[30] = {'):]
strs = re.findall(r'"((?:[^"\\]|\\.)*)"', seg)
cjk = [s for s in strs if re.search(r'[\u4e00-\u9fff]', s)]
c = collections.Counter(cjk)
for s, n in c.most_common():
    print('%3d  %s' % (n, s))
print('---- 去重 %d / 总 %d' % (len(c), len(cjk)))
