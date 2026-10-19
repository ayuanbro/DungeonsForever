# -*- coding: utf-8 -*-
# 2026-10-10 七轮：快照 < 60 秒显示「刚刚」，避免刚扫完仍显示「1 分钟前」被误读为坏值。
# ProfessionUI.lua = CRLF。
import sys

PUI = 'Core/ProfessionUI.lua'


def crlf(s):
    return s.replace('\r\n', '\n').replace('\n', '\r\n')


EDITS = []

# E1) 信息卡：< 60s → 刚刚
EDITS.append(('card-fresh', '''    local atxt
    if s.priced and snapSec then
        if snapSec < 90 * 60 then
            atxt = format(L["%d 分钟前 · Auctionator"], math.max(1, math.floor(snapSec / 60 + 0.5)))
''', '''    local atxt
    if s.priced and snapSec then
        if snapSec < 60 then
            atxt = L["刚刚 · Auctionator"]
        elseif snapSec < 90 * 60 then
            atxt = format(L["%d 分钟前 · Auctionator"], math.max(1, math.floor(snapSec / 60 + 0.5)))
'''))

# E2) 购物清单：< 60s → 刚刚
EDITS.append(('shop-fresh', '''    local atxt
    if snapSec then
        if snapSec < 90 * 60 then
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(snapSec / 60 + 0.5)))
''', '''    local atxt
    if snapSec then
        if snapSec < 60 then
            atxt = L["价格快照：刚刚（Auctionator）"]
        elseif snapSec < 90 * 60 then
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(snapSec / 60 + 0.5)))
'''))


def check():
    d = open(PUI, encoding='utf-8', newline='').read()
    ok = True
    for name, old, new in EDITS:
        c = d.count(crlf(old))
        if c != 1:
            print('MISS %-12s count=%d' % (name, c)); ok = False
        else:
            print('ok   ', name)
    return ok


def apply():
    if not check():
        sys.exit('anchor check failed, abort')
    d = open(PUI, encoding='utf-8', newline='').read()
    for name, old, new in EDITS:
        d = d.replace(crlf(old), crlf(new), 1)
    open(PUI, 'w', encoding='utf-8', newline='').write(d)
    print('applied ui=%d' % len(EDITS))
    raw = open(PUI, 'rb').read()
    print('CRLF:', raw.count(b'\r\n'), 'bareLF:', raw.count(b'\n') - raw.count(b'\r\n'))


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        apply()
