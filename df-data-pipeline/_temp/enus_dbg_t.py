# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = "D:/workspace/DungeonsForever/_temp"
sys.path.insert(0, HERE)
import gen_enus_data as G
for s in ('火焰伤害 +20', '冰霜法术伤害 +15', '治疗法术 +24', '永久附着于物品', '次级属性'):
    print(repr(s), '->', repr(G.translate(s)))
print('rules count:', len(G.RULES))
for pat, fn in G.RULES:
    m = pat.match('火焰伤害 +20')
    if m:
        print('matched by', pat.pattern, '->', fn(m))
