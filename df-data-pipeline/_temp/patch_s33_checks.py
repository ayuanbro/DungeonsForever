# -*- coding: utf-8 -*-
"""同步 harness 断言 / 变异锚点：详情子页栅格内衬 8 -> 0（贴 detail 边 = 距内容面板 12）。

- df_dungeon_check.py：掉落地网格卡宽 224->228、x 序列 8/240/472/704 -> 0/236/472/708、
  任务页两板/滚动区锚点文本。
- df_mut_check.py：MUT_PLATE_OVERLAP 的 plateR 锚点文本跟随。

二进制读写保行尾；--check 只校验锚点命中数，不写盘。
"""
import sys

ROOT = r'D:\workspace\DungeonsForever'
CHECK = '--check' in sys.argv


def B(s):
    return s.encode('utf-8')


EDS_CHECK = [
    # ---- 任务页两列主从 / 两板锚点 ----
    (B('"BOTTOMLEFT", DG.GUTTER + DG.Q_LIST_W, 0)\' in src'),
     B('"BOTTOMLEFT", DG.Q_LIST_W, 0)\' in src'), 1),
    (B('★ 两块底板卡不重叠且收进栅格（板L = GUTTER…+Q_LIST_W，板R 左缘 +Q_DET_GAP，间隙 8）'),
     B('★ 两块底板卡不重叠且收进栅格（板L 贴左缘 0…+Q_LIST_W，板R 左缘 +Q_DET_GAP，间隙 8）'), 1),
    (B('\'DG.GUTTER + DG.Q_LIST_W, 0)\' in src'),
     B('\'DG.Q_LIST_W, 0)\' in src'), 1),
    (B('and \'DG.GUTTER + DG.Q_LIST_W + DG.Q_DET_GAP,\' in src'),
     B('and \'DG.Q_LIST_W + DG.Q_DET_GAP,\' in src'), 1),

    # ---- 掉落 4 列卡宽 / 摆位 ----
    (B('卡片 224 × 44（4 列 · 双行——2026-10-10 间距标准：网格内衬 GUTTER，221 → 224）'),
     B('卡片 228 × 44（4 列 · 双行——2026-10-13 三外缘拉平：内容贴 detail 边，栅格 0 起）'), 1),
    (B('cw == 224 and chh == 44'), B('cw == 228 and chh == 44'), 1),
    (B('★ 同一排三张卡 x = 8 / 240 / 472（4 列：栅格 8 起，224 + 8 列距）'),
     B('★ 同一排三张卡 x = 0 / 236 / 472（4 列：栅格 0 起，228 + 8 列距）'), 1),
    (B('px(d1) == 8 and px(d2) == 240 and px(d3) == 472'),
     B('px(d1) == 0 and px(d2) == 236 and px(d3) == 472'), 1),
    (B('x 只能落在 4 列上（8/240/472/704）；向右走必是 +232（同一排）；'),
     B('x 只能落在 4 列上（0/236/472/708）；向右走必是 +236（同一排）；'), 1),
    (B('local _colset = { [8]=true, [240]=true, [472]=true, [704]=true }'),
     B('local _colset = { [0]=true, [236]=true, [472]=true, [708]=true }'), 1),
    (B('elseif _pvx ~= nil and xx ~= 8 and xx <= _pvx then'),
     B('elseif _pvx ~= nil and xx ~= 0 and xx <= _pvx then'), 1),
    (B('elseif _pvx ~= nil and xx == 8'), B('elseif _pvx ~= nil and xx == 0'), 1),
    (B('★ 4 列摆位规律（x 循环 4 列 8/240/472/704、向右必 +232、回第 1 列必降一整行）'),
     B('★ 4 列摆位规律（x 循环 4 列 0/236/472/708、向右必 +236、回第 1 列必降一整行）'), 1),
]

EDS_MUT = [
    (B('DG.GUTTER + DG.Q_LIST_W + DG.Q_DET_GAP, -DG.SCROLL_Y)'),
     B('DG.Q_LIST_W + DG.Q_DET_GAP, -DG.SCROLL_Y)'), 1),
    (B('DG.GUTTER + DG.Q_LIST_W, -DG.SCROLL_Y) -- MUT: overlap'),
     B('DG.Q_LIST_W, -DG.SCROLL_Y) -- MUT: overlap'), 1),
]


def run(path, edits):
    raw = open(path, 'rb').read()
    is_crlf = raw.count(b'\r\n') > 0 and raw.count(b'\n') == raw.count(b'\r\n')
    txt = raw.replace(b'\r\n', b'\n') if is_crlf else raw
    fails = 0
    for old, new, expect in edits:
        n = txt.count(old)
        if n != expect:
            print('  FAIL hits=%d expect=%d : %s' % (n, expect, old.decode('utf-8')[:78]))
            fails += 1
            continue
        txt = txt.replace(old, new)
        print('  ok   x%d : %s' % (n, old.decode('utf-8')[:70]))
    if fails or CHECK:
        return fails
    out = txt.replace(b'\n', b'\r\n') if is_crlf else txt
    open(path, 'wb').write(out)
    print('  WRITTEN %s  %d -> %d bytes' % (path, len(raw), len(out)))
    return 0


def main():
    print('=== _temp/df_dungeon_check.py ===')
    rc = run(ROOT + r'\_temp\df_dungeon_check.py', EDS_CHECK)
    print('=== _temp/df_mut_check.py ===')
    rc += run(ROOT + r'\_temp\df_mut_check.py', EDS_MUT)
    print('fails=%d  check=%s' % (rc, CHECK))
    return 1 if rc else 0


if __name__ == '__main__':
    sys.exit(main())
