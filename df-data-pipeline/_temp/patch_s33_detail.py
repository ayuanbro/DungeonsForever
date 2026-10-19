# -*- coding: utf-8 -*-
"""详情子页（任务 / 攻略 / 掉落）栅格内衬 8 -> 0：内容直接贴 detail 边。

背景：detail 四边锚 = page 内缩 PAGE_INSET(12)，detail 实宽 936 = CONTENT_W - 24。
任务/攻略/掉落三页的滚动区 child 已贴 detail（偏移 0），但**栅格又加了一层 DG.GUTTER(8) 内衬**
=> 实际落点距内容面板 20（12 + 8）。本轮把这一层内衬归 0，落到 12（与 hero / 地图框 / 列表大卡统一）。

二进制读写保行尾；--check 只校验锚点命中数，不写盘。
"""
import sys

ROOT = r'D:\workspace\DungeonsForever'
CHECK = '--check' in sys.argv


def B(s):
    return s.encode('utf-8')


EDS_DUI = [
    # ---------------- 任务页（DG.EnsureQuestLane） ----------------
    # qscroll + plateL 左缘（两处同文本）
    (B('"TOPLEFT", detail, "TOPLEFT", DG.GUTTER, -DG.SCROLL_Y)'),
     B('"TOPLEFT", detail, "TOPLEFT", 0, -DG.SCROLL_Y)'), 2),
    # qscroll + plateL 底右（两处同文本）
    (B('"BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.GUTTER + DG.Q_LIST_W, 0)'),
     B('"BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W, 0)'), 2),
    # qdet 左缘
    (B('DG.GUTTER + DG.Q_LIST_W + DG.Q_DET_GAP + DG.Q_PAD, -DG.SCROLL_Y)'),
     B('DG.Q_LIST_W + DG.Q_DET_GAP + DG.Q_PAD, -DG.SCROLL_Y)'), 1),
    # qdet 右缘
    (B('"BOTTOMRIGHT", detail, "BOTTOMRIGHT", -(DG.GUTTER + DG.Q_PAD), 0'),
     B('"BOTTOMRIGHT", detail, "BOTTOMRIGHT", -(DG.Q_PAD), 0'), 1),
    # plateR 左缘
    (B('DG.GUTTER + DG.Q_LIST_W + DG.Q_DET_GAP, -DG.SCROLL_Y)'),
     B('DG.Q_LIST_W + DG.Q_DET_GAP, -DG.SCROLL_Y)'), 1),
    # plateR 右缘
    (B('"BOTTOMRIGHT", detail, "BOTTOMRIGHT", -DG.GUTTER, 0)'),
     B('"BOTTOMRIGHT", detail, "BOTTOMRIGHT", 0, 0)'), 1),
    # 右栏详情内容宽常量
    (B('DG.Q_DET_W = DG.CHILD_W - DG.GUTTER * 2 - DG.Q_LIST_W - DG.Q_DET_GAP - DG.Q_PAD * 2'),
     B('DG.Q_DET_W = DG.CHILD_W - DG.Q_LIST_W - DG.Q_DET_GAP - DG.Q_PAD * 2'), 1),

    # ---------------- 攻略页 ----------------
    (B('DG.GUIDE_SIDE = 8'), B('DG.GUIDE_SIDE = 0'), 1),
    (B('f:SetWidth(DG.CHILD_W - DG.GUTTER * 2)'), B('f:SetWidth(DG.CHILD_W)'), 1),
    (B('f:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER, 0)'),
     B('f:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)'), 1),

    # ---------------- 掉落页（列表视图 / 卡片视图 / 团本整宽 / 空态） ----------------
    (B('DG.LOOT_CARD_W = math.floor((DG.CHILD_W - DG.GUTTER * 2 - (DG.LOOT_COLS - 1) * DG.LOOT_GAP_X) / DG.LOOT_COLS)'),
     B('DG.LOOT_CARD_W = math.floor((DG.CHILD_W - (DG.LOOT_COLS - 1) * DG.LOOT_GAP_X) / DG.LOOT_COLS)'), 1),
    (B('DG.LOOT_CARD_W3 = math.floor((DG.CHILD_W - DG.GUTTER * 2 - DG.LOOT_MODEL_W - DG.LOOT_COLS3 * DG.LOOT_GAP_X) / DG.LOOT_COLS3)'),
     B('DG.LOOT_CARD_W3 = math.floor((DG.CHILD_W - DG.LOOT_MODEL_W - DG.LOOT_COLS3 * DG.LOOT_GAP_X) / DG.LOOT_COLS3)'), 1),
    (B('DG.LOOT_MODEL_X = DG.CHILD_W - DG.GUTTER - DG.LOOT_MODEL_W'),
     B('DG.LOOT_MODEL_X = DG.CHILD_W - DG.LOOT_MODEL_W'), 1),
    (B('hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER, y)'),
     B('hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)'), 1),
    (B('hd.cnt:SetPoint("TOPRIGHT", child, "TOPRIGHT", -DG.GUTTER, y - 1)'),
     B('hd.cnt:SetPoint("TOPRIGHT", child, "TOPRIGHT", 0, y - 1)'), 1),
    (B('r:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER, baseY)'),
     B('r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, baseY)'), 1),
    (B('local rx = DG.GUTTER + ((i - 1) % cols) * stepX'),
     B('local rx = ((i - 1) % cols) * stepX'), 1),
    # 列表视图空态 + 卡片视图空态（两处同文本）
    (B('note:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER, 0)'),
     B('note:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)'), 2),
    (B('cw = DG.CHILD_W - DG.GUTTER * 2'), B('cw = DG.CHILD_W'), 1),
    (B('local cx, cy = DG.GUTTER + (col - 1) * stepX, colY[col]'),
     B('local cx, cy = (col - 1) * stepX, colY[col]'), 1),
]


def run(path, edits):
    raw = open(path, 'rb').read()
    assert raw.count(b'\n') == raw.count(b'\r\n'), 'not pure CRLF: ' + path
    txt = raw.replace(b'\r\n', b'\n')
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
    out = txt.replace(b'\n', b'\r\n')
    open(path, 'wb').write(out)
    print('  WRITTEN %s  %d -> %d bytes' % (path, len(raw), len(out)))
    return 0


def main():
    print('=== Core/DungeonUI.lua ===')
    rc = run(ROOT + r'\Core\DungeonUI.lua', EDS_DUI)
    print('fails=%d  check=%s' % (rc, CHECK))
    return 1 if rc else 0


if __name__ == '__main__':
    sys.exit(main())
