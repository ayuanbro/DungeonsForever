# -*- coding: utf-8 -*-
"""校验：重建后的 20级 卷是否与原 Data_BIS.lua 数据完全一致（先去注释、再去空白比对）。"""
import re


def sw(s):
    return re.sub(r'\s+', '', s)


def code_only(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    return '\n'.join(l for l in lines if not l.lstrip().startswith('--'))


old = sw(code_only('_temp/_bis_bak20.lua'))
new = sw(code_only('Core/Data/Data_BIS.lua'))

obody = old[old.find('classes='):]
a = new.find('[20]={')
b = new.find('[30]={')
blk = new[a:b] if b > a else new[a:]
nb = blk[blk.find('classes='):]

print('old body len', len(obody), '| new[20] len', len(nb))
print('旧 20级 数据完整保留:', nb.rstrip('},').startswith(obody.rstrip('},')))
i = 0
while i < min(len(obody), len(nb)) and obody[i] == nb[i]:
    i += 1
print('首个差异位置', i)
print('old ...', obody[max(0, i - 60):i + 80])
print('new ...', nb[max(0, i - 60):i + 80])
