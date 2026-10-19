# -*- coding: utf-8 -*-
import io, glob, re

def scan(pat):
    n = 0
    for p in glob.glob('_temp/_cg_trans/*.json'):
        n += len(re.findall(pat, io.open(p, encoding='utf-8').read()))
    return n

def scanb(pat):
    n = 0
    for p in glob.glob('_temp/_cg_trans_bak/*.json'):
        n += len(re.findall(pat, io.open(p, encoding='utf-8').read()))
    return n

rows = [
    ('永恒', '永恒'),
    ('永恆', '永恆'),
    ('永久', '永久'),
    ('latin Forever', 'Forever'),
    ('无限 合计', '无限'),
    ('《魔兽世界：无限》', '《魔兽世界：无限》'),
    ('《无限》', '《无限》'),
    ('无限服', '无限服'),
    ('无限版本', '无限版本'),
    ('无限版(非版本)', '无限版(?!本)'),
    ('无限测试服', '无限测试服'),
    ('空格+《无限》(leading)', ' 《无限》'),
    ('《无限》+空格(trailing)', '《无限》 '),
    ('空格+无限版本', ' 无限版本'),
    ('空格+无限服', ' 无限服'),
]
print('%-24s %8s %8s' % ('pattern', 'BEFORE', 'AFTER'))
for lbl, pat in rows:
    print('%-24s %8d %8d' % (lbl, scanb(pat), scan(pat)))

# 残留 永久 上下文
print('--- residual 永久 contexts (AFTER) ---')
for p in sorted(glob.glob('_temp/_cg_trans/*.json')):
    t = io.open(p, encoding='utf-8').read()
    for m in re.finditer('永久', t):
        s = max(0, m.start() - 18); e = min(len(t), m.end() + 18)
        print('  %s | ...%s...' % (p.split('/')[-1], t[s:e]))
