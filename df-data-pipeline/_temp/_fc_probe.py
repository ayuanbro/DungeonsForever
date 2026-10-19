# -*- coding: utf-8 -*-
"""探测 fc 页 boss 名单/章节结构"""
import re, sys, collections

slug = sys.argv[1]
h = open('_fc_dg_%s.html' % slug, encoding='utf-8').read()

# boss section 形态：找 'bosses' 键
print('bosses key:', len(re.findall(r'\\"bosses\\":\[', h)))
print('fights key:', len(re.findall(r'\\"fights\\":\{', h)))
print('lootTables:', len(re.findall(r'\\"lootTables\\":', h)))
print('encounters:', len(re.findall(r'\\"encounters\\":', h)))

# 提取所有英文 boss 名（english 字段）
names = re.findall(r'\\"english\\":\\"([^\\]+)\\"', h)
c = collections.OrderedDict()
for n in names:
    if n not in c:
        c[n] = 1
print('english names (%d):' % len(c))
for n in list(c)[:25]:
    print('  ', n)

# 技能 icon slug 出现
icons = re.findall(r'\\"icon\\":\\"([a-z0-9_]+)\\"', h)
print('icons:', len(icons), list(dict.fromkeys(icons))[:10])
