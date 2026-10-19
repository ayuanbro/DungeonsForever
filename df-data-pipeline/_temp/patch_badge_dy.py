import sys

SRC = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CHK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
RULE = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"
DBG = r"D:\workspace\DungeonsForever\_temp\_dbg_qbadge.py"

def patch(path, pairs, tag):
    d = open(path, "rb").read()
    c0 = d.count(b"\r\n"); b0 = d.count(b"\n") - c0
    for old, new in pairs:
        o = old.encode("utf-8"); n = new.encode("utf-8")
        c = d.count(o)
        if c != 1:
            print("HIT-MISS", tag, c, old[:80]); sys.exit(1)
        d = d.replace(o, n)
    open(path, "wb").write(d)
    c1 = d.count(b"\r\n"); b1 = d.count(b"\n") - c1
    print("OK", tag, "CRLF", c0, "->", c1, "bareLF", b0, "->", b1)

patch(SRC, [
    ("DG.Q_BADGE_GAP = 4\r\nDG.Q_BADGE_PAD = 3\r\n",
     "DG.Q_BADGE_GAP = 4\r\nDG.Q_BADGE_PAD = 3\r\nDG.Q_BADGE_DY = 2\r\n"),
    ('b:SetPoint("TOPLEFT", b:GetParent(), "TOPLEFT", x, -(DG.Q_ROW_H - DG.Q_BADGE_H) / 2)',
     'b:SetPoint("TOPLEFT", b:GetParent(), "TOPLEFT", x, -(DG.Q_ROW_H - DG.Q_BADGE_H) / 2 - DG.Q_BADGE_DY)'),
], "SRC")

patch(CHK, [
    ("       and 'DG.Q_BADGE_GAP = 4' in src and 'DG.Q_BADGE_PAD = 3' in src)\n",
     "       and 'DG.Q_BADGE_GAP = 4' in src and 'DG.Q_BADGE_PAD = 3' in src\n"
     "       and 'DG.Q_BADGE_DY = 2' in src\n"
     "       and '-(DG.Q_ROW_H - DG.Q_BADGE_H) / 2 - DG.Q_BADGE_DY)' in src)\n"),
], "CHK")

patch(RULE, [
    ("宽度 = `lab:GetStringWidth() + 2×3`，卡内文字垂直居中（`DG.PlaceBadge` 按 `(行高 − 卡高)/2` 自动落）、"
     "贴着前一元素右缘排（返下一枚 x）。",
     "宽度 = `lab:GetStringWidth() + 2×3`；**垂直落点 = `(行高 − 卡高)/2 − DG.Q_BADGE_DY`**，"
     "`DG.Q_BADGE_DY = 2` 是**视觉基准补偿**（★★ 2026-10-13 用户截图实锤：徽章是 Frame=几何框，"
     "任务名是 FontString=字形墨迹在框内天然偏下，两者「中心」不是同一基准，不加这 2px 徽章视觉上偏上 ≈1.9px；"
     "卡内文字自身仍 `CENTER` 居中）。贴着前一元素右缘排（返下一枚 x）。"),
], "RULE")

patch(DBG, [
    ("    return string.format('shown=%s w=%s txt=%s bg=%s', tostring(b.__shown), n(b.__w),",
     "    return string.format('shown=%s w=%s y=%s txt=%s bg=%s', tostring(b.__shown), n(b.__w),\n"
     "      tostring(b.__pts and b.__pts[5]),"),
], "DBG")
