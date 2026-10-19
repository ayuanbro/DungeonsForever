# -*- coding: utf-8 -*-
"""QA 独立检查：行尾规范 + 注入点核对。只读，不改任何文件。"""
import os

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
SRC = r'D:\workspace\DungeonsForever'

FILES = ['Core/DungeonUI.lua', 'Core/MainFrame.lua', 'Core/LootFilter.lua',
         'Core/LootFilterUI.lua', 'Core/Data/Data_LootFilter.lua', 'DungeonsForever.toc']


def eol_report(base, label):
    print('=== %s ===' % label)
    for f in FILES:
        p = os.path.join(base, f.replace('/', os.sep))
        if not os.path.exists(p):
            print('  MISSING %s' % f)
            continue
        b = open(p, 'rb').read()
        crlf = b.count(b'\r\n')
        lf = b.count(b'\n')
        cr = b.count(b'\r')
        kind = 'CRLF' if crlf and crlf == cr else ('LF' if lf and cr == 0 else 'MIXED')
        print('  %-34s %-6s crlf=%-6d lf=%-6d bare_cr=%d' % (f, kind, crlf, lf, cr - crlf))


eol_report(SRC, '源仓库 D:\\workspace\\DungeonsForever')
eol_report(ADDON, 'beta 副本')

print()
print('=== 注入点核对（源仓库 Core/DungeonUI.lua）===')
src = open(os.path.join(SRC, 'Core', 'DungeonUI.lua'), encoding='utf-8', errors='replace').read()
for needle in ['LF.Invalidate(itemID)', 'LF.ApplyAll()', 'LF.Apply(r)',
               'local LF = ns.LootFilter', 'r:SetAlpha(1)', 'r.__it = it',
               'U.lootFilterBar']:
    print('  %-32s count=%d' % (needle, src.count(needle)))

print()
print('=== MainFrame 注入点 ===')
mf = open(os.path.join(SRC, 'Core', 'MainFrame.lua'), encoding='utf-8', errors='replace').read()
print('  ns.LootFilterUI:CloseConfig()  count=%d' % mf.count('ns.LootFilterUI:CloseConfig()'))

print()
print('=== TOC 顺序 ===')
toc = open(os.path.join(SRC, 'DungeonsForever.toc'), encoding='utf-8', errors='replace').read()
lines = [l.strip().replace('\\', '/') for l in toc.splitlines()
         if l.strip() and not l.strip().startswith('##')]
for i, l in enumerate(lines, 1):
    if 'LootFilter' in l or 'DungeonUI' in l or 'RaidUI' in l:
        print('  %2d  %s' % (i, l))
