# -*- coding: utf-8 -*-
"""把 loc_zh/loc_tw 按完整地名字符重新生成（sub · zone），幂等。
行格式：{ ... loc_en = "X", loc_zh = "Y", loc_tw = "Z" },"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LUA = os.path.join(REPO, 'Core', 'Data', 'Data_ProfTrainers.lua')

DIC = json.load(open(os.path.join(HERE, '_trainers_zone_full.json'), encoding='utf-8'))

try:
    from opencc import OpenCC
    _cc = OpenCC('s2twp')
    def s2t(s):
        return _cc.convert(s)
except Exception:
    def s2t(s):
        return s


def zh_of(en):
    return DIC.get(en) or DIC.get(en.replace("'", '\u2019')) or en


src = open(LUA, encoding='utf-8', newline='').read()
NL = '\r\n' if '\r\n' in src else '\n'

row_pat = re.compile(
    r'(loc_en = "([^"]*)", loc_zh = ")([^"]*)(", loc_tw = ")([^"]*)(")')

n_sub = n_zone = n_fb = 0


def repl(m):
    global n_sub, n_zone, n_fb
    loc_en = m.group(2)
    old_zh = m.group(3)
    note = ''
    body = loc_en
    mn = re.search(r' \((.*)\)$', body)
    if mn:
        note = mn.group(1)
        body = body[:mn.start()]
    parts = body.split(', ')
    if len(parts) == 2:
        sub, zone = parts
    else:
        sub, zone = None, parts[0]
    sz = zh_of(sub) if sub else None
    zz = zh_of(zone)
    if sz == sub:
        n_fb += 1
    else:
        n_sub += 1
    if zz == zone:
        n_fb += 1
    else:
        n_zone += 1
    new_zh = (sz + ' · ' + zz) if sz else zz
    new_tw = s2t(new_zh)
    if new_zh == old_zh:
        n_noop = True
    return 'loc_en = "%s", loc_zh = "%s", loc_tw = "%s"' % (loc_en, new_zh, new_tw)


out = row_pat.sub(repl, src)
open(LUA, 'w', encoding='utf-8', newline='').write(out)
print('rows rewritten; sub_zh=%d zone_zh=%d fallback=%d' % (n_sub, n_zone, n_fb))
left = re.findall(r'loc_zh = "([^"]*)"', out)
bad = [z for z in left if re.search(r'[A-Za-z]{4,}', z)]
print('still-latin rows:', len(bad))
for b in bad[:10]:
    print('  ', b)
