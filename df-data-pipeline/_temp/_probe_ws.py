# -*- coding: utf-8 -*-
import io, re

t = io.open('Core/Data/Data_ClassGuide.lua', encoding='utf-8').read()
print('=== 《无限》 + trailing space ===')
for m in re.finditer('《无限》 ', t):
    s = max(0, m.start() - 26); e = min(len(t), m.end() + 26)
    print('  ...%s...' % t[s:e].replace('\n', ' '))
print('=== leading space + 《无限》 ===')
for m in re.finditer(' 《无限》', t):
    s = max(0, m.start() - 26); e = min(len(t), m.end() + 26)
    print('  ...%s...' % t[s:e].replace('\n', ' '))
print('=== space + 无限版本 ===')
for m in re.finditer(' 无限版本', t):
    s = max(0, m.start() - 26); e = min(len(t), m.end() + 26)
    print('  ...%s...' % t[s:e].replace('\n', ' '))
print('=== 无限测试服 / 《无限》测试服 ===')
print('  《无限》测试服 =', t.count('《无限》测试服'))
print('  无限测试服 =', t.count('无限测试服'))
print('=== lines with 无限 AND heavy latin (English fallback) ===')
for line in t.split('\n'):
    if '无限' in line and len(re.findall(r'[A-Za-z]{2,}', line)) > 4:
        print('  ', line.strip()[:180])
