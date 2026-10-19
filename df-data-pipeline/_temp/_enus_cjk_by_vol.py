# -*- coding: utf-8 -*-
"""按卷统计 enUS 覆盖层的残留中文（20级 vs 30级）。"""
import re

t = open('Core/Data/enUS/Data_BIS.lua', encoding='utf-8').read()
a = t.find('[20] = {')
b = t.find('[30] = {')
for tag, seg in (('lv20', t[a:b]), ('lv30', t[b:])):
    strs = re.findall(r'"((?:[^"\\]|\\.)*)"', seg)
    cjk = [s for s in strs if re.search(r'[\u4e00-\u9fff]', s)]
    print('%s 字符串 %d | 含中文 %d' % (tag, len(strs), len(cjk)))
    kinds = {}
    for s in cjk:
        k = '任务：' if s.startswith('任务：') else ('note 句' if len(s) > 8 else '短词')
        kinds[k] = kinds.get(k, 0) + 1
    print('   ', kinds)
