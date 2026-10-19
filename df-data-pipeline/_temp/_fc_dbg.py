# -*- coding: utf-8 -*-
import re, sys
sys.path.insert(0, '.')
from _fc_compare import unesc, balanced

h = open('_fc_dg_shadowfang-keep.html', encoding='utf-8').read()
blks = balanced(h, r'\\"bosses\\":\[', ']')
print('bosses blocks:', len(blks))
for blk in blks:
    fj = unesc(blk)
    print('unesc len:', len(fj))
    print(fj[:300])
    # english 出现次数
    print('english count:', len(re.findall(r'"english":"([^"]*)"', fj)))
    print('items count:', len(re.findall(r'"items":\[', fj)))
    break
