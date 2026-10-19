# -*- coding: utf-8 -*-
"""残检：产物里是否残留旧身份串（与 pack_verify.py 的 RESIDUAL_RE 同口径）。"""
import glob
import os
import re
import sys

ROOT = r'D:\workspace\DungeonsForever'
RES = re.compile(
    r"TalentsForeverDB|TalentsForever_MainFrame|TalentsForever_SourceURL"
    r"|Interface[/\\]AddOns[/\\]TalentsForever|ns\.TalentSimUI|ns\.OpenTalentSim"
    r"|TALENTSFOREVER|无限天赋模拟器"
    r"|foreverchanges|Icy-Veins|icy-veins|warcrafttavern|indiekings|MageBookTracker"
    r"|站点")

bad = []
n = 0
for sub in ('Core', 'Locales'):
    for p in glob.glob(os.path.join(ROOT, sub, '**', '*.lua'), recursive=True):
        n += 1
        t = open(p, encoding='utf-8', errors='replace').read()
        for m in RES.finditer(t):
            bad.append((os.path.relpath(p, ROOT), t[:m.start()].count('\n') + 1, m.group(0)))
print('扫描 %d 个 lua，旧身份串命中 %d 处' % (n, len(bad)))
for b in bad[:12]:
    print('   %s:%d  %s' % b)
if not bad:
    print('   ✓ 干净')
