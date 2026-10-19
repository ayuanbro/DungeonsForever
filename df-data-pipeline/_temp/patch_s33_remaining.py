# -*- coding: utf-8 -*-
"""§3.3 剩余三页外缘拉平补丁：TierUI / 五人本 / 团本（+ 团本断言同步）。
二进制读写，保真各文件自身换行风格；锚点必须恰好命中 1 次，否则中止。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (相对路径, old, new, 说明)
PATCHES = [
    ('Core/TierUI.lua',
     'TT.EDGE = 20\n',
     'TT.EDGE = PAGE_INSET\n',
     'TierUI 三外缘总源 20->PAGE_INSET'),
    ('Core/DungeonUI.lua',
     '    local CARD_BOTTOM = PAGE_INSET + DG.GUTTER',
     '    local CARD_BOTTOM = PAGE_INSET',
     '五人本列表大卡底 20->PAGE_INSET'),
    ('Core/RaidUI.lua',
     'RU.CARD_BOTTOM = 20\n',
     'RU.CARD_BOTTOM = PAGE_INSET\n',
     '团本大卡底 20->PAGE_INSET'),
    ('_temp/df_dungeon_check.py',
     "and 'RU.CARD_BOTTOM = 20' in _ra",
     "and 'RU.CARD_BOTTOM = PAGE_INSET' in _ra",
     '团本守门断言同步'),
]


def run(check_only):
    failures = 0
    for rel, old, new, desc in PATCHES:
        p = os.path.join(ROOT, rel)
        raw = open(p, 'rb').read()
        crlf = b'\r\n' in raw
        ob = old.encode('utf-8')
        nb = new.encode('utf-8')
        if crlf:
            ob = ob.replace(b'\n', b'\r\n')
            nb = nb.replace(b'\n', b'\r\n')
        n = raw.count(ob)
        if n != 1:
            print('  FAIL %-28s anchor hits %d (expect 1)  [%s]' % (rel, n, desc))
            failures += 1
            continue
        if check_only:
            print('  ok   %-28s anchor hits 1  (%s)' % (rel, 'CRLF' if crlf else 'LF'))
            continue
        out = raw.replace(ob, nb, 1)
        if crlf:
            if out.count(b'\r\n') != raw.count(b'\r\n'):
                print('  FAIL %-28s CRLF count changed' % rel)
                failures += 1
                continue
            if out.count(b'\n') - out.count(b'\r\n') != 0:
                print('  FAIL %-28s bare LF introduced' % rel)
                failures += 1
                continue
        open(p, 'wb').write(out)
        print('  OK   %-28s patched  [%s]' % (rel, desc))
    return failures


if __name__ == '__main__':
    check = '--check' in sys.argv
    print('--- %s ---' % ('DRY-RUN' if check else 'APPLY'))
    f = run(check)
    sys.exit(2 if f else 0)
