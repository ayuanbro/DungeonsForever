# -*- coding: utf-8 -*-
"""统计 enUS 数据覆盖层里仍残留中文的字符串（= 未命中翻译表、回落简体原文）。"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'Core/Data/enUS/Data_BIS.lua'
t = open(path, encoding='utf-8').read()
strs = re.findall(r'"((?:[^"\\]|\\.)*)"', t)
cjk = [s for s in strs if re.search(r'[\u4e00-\u9fff]', s)]
print('字符串总数 %d | 含中文 %d' % (len(strs), len(cjk)))
for s in cjk[:12]:
    print('  -', s[:90])
