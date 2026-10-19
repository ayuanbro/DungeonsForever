# -*- coding: utf-8 -*-
"""Final verification of the version-name normalization in generated data files.

Checks (per team-lead instruction E):
  - residual counts: 永恒 / 永恆 / 版本性永久 / latin 'Forever'
  - form distribution: 《魔兽世界：无限》 / 《无限》 / 无限服 / 无限版本 / 无限版 / 无限测试服
  - whitespace residues around version tokens: '《无限》 ' and ' 《无限》'
"""
import json
import re
import sys

ROOT = r'D:/workspace/DungeonsForever'

TARGETS = [
    ('zhCN', ROOT + '/Core/Data/Data_ClassGuide.lua'),
    ('zhTW', ROOT + '/Core/Data/zhTW/Data_ClassGuide.lua'),
    ('enUS', ROOT + '/Core/Data/enUS/Data_ClassGuide.lua'),
]

# Residual (should all be 0 in data files)
RESIDUAL = {
    '永恒': re.compile(r'永恒'),
    '永恆': re.compile(r'永恆'),
    '版本性永久': re.compile(r'版本性永久'),
    'latin Forever': re.compile(r'Forever'),
}

# Forms (mutually informative counters; note 无限版本/无限版/无限测试服/无限服/《无限》/《魔兽世界：无限》)
FORMS = {
    '《魔兽世界：无限》': re.compile(r'《魔兽世界：无限》'),
    '《无限》': re.compile(r'《无限》'),
    '无限服': re.compile(r'无限服'),
    '无限版本': re.compile(r'无限版本'),
    '无限版': re.compile(r'无限版'),
    '无限测试服': re.compile(r'无限测试服'),
}

# Whitespace residuals
WS_BAD = {
    '《无限》 尾随空格': re.compile(r'《无限》[ \t]'),
    '前置空格 《无限》': re.compile(r'[ \t]《无限》'),
    '无限版本 尾随空格': re.compile(r'无限版本[ \t]'),
    '前置空格 无限版本': re.compile(r'[ \t]无限版本'),
}

out = {}
for label, path in TARGETS:
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            text = fh.read()
    except FileNotFoundError:
        out[label] = {'error': 'FILE NOT FOUND'}
        continue
    res = {}
    for name, rx in RESIDUAL.items():
        res[name] = len(rx.findall(text))
    forms = {}
    for name, rx in FORMS.items():
        forms[name] = len(rx.findall(text))
    ws = {}
    for name, rx in WS_BAD.items():
        ws[name] = len(rx.findall(text))
    out[label] = {'residual': res, 'forms': forms, 'ws': ws, 'bytes': len(text)}

with open(ROOT + '/_temp/_final_verify.out', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print('DONE')
