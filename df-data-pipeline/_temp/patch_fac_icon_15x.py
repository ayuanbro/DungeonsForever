# -*- coding: utf-8 -*-
"""任务行阵营图标放大 1.5 倍（12 -> 18）。字节级保 CRLF。"""
import sys

SRC = 'Core/DungeonUI.lua'

BLOCKS = []

# ① 常量：在 DG.Q_FAC_ICON 表后登记边长
BLOCKS.append((
    b'DG.Q_FAC_ICON = {\r\n'
    b'    A = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Alliance",\r\n'
    b'    H = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Horde",\r\n'
    b'}\r\n',

    b'DG.Q_FAC_ICON = {\r\n'
    b'    A = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Alliance",\r\n'
    b'    H = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Horde",\r\n'
    b'}\r\n'
    b'-- \xe8\xa1\x8c\xe5\x86\x85\xe5\xa3\xb0\xe8\x90\xa5\xe5\x9b\xbe\xe6\xa0\x87\xe8\xbe\xb9\xe9\x95\xbf\xef\xbc\x88 12 \xc3\x97 1.5 = 18\xef\xbc\x8c2026-10-13 \xe7\x94\xa8\xe6\x88\xb7\xe5\xae\x9a\xef\xbc\x89\r\n'
    b'DG.Q_FAC_ICON_SZ = 18\r\n'
))

# ② 行创建：尺寸 + 垂直落点
BLOCKS.append((
    b'            r.em = r:CreateTexture(nil, "ARTWORK")\r\n'
    b'            r.em:SetSize(12, 12)\r\n'
    b'            r.em:SetPoint("TOPLEFT", r, "TOPLEFT", 12, -(DG.Q_ROW_H - 12) / 2)\r\n',

    b'            r.em = r:CreateTexture(nil, "ARTWORK")\r\n'
    b'            r.em:SetSize(DG.Q_FAC_ICON_SZ, DG.Q_FAC_ICON_SZ)\r\n'
    b'            r.em:SetPoint("TOPLEFT", r, "TOPLEFT", 12, -(DG.Q_ROW_H - DG.Q_FAC_ICON_SZ) / 2)\r\n'
))

d = open(SRC, 'rb').read()
for i, (old, new) in enumerate(BLOCKS, 1):
    n = d.count(old)
    if n != 1:
        print('[HIT-MISS] block %d: count=%d' % (i, n))
        sys.exit(1)
    d = d.replace(old, new)
    print('[OK] block %d' % i)

open(SRC, 'wb').write(d)
crlf = d.count(b'\r\n')
print('CRLF=%d LF-only=%d' % (crlf, d.count(b'\n') - crlf))
