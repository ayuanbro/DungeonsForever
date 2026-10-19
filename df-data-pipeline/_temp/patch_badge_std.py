import sys

SRC = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CHK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
RULE = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"

def patch(path, pairs, tag):
    with open(path, "rb") as f:
        d = f.read()
    c0 = d.count(b"\r\n"); b0 = d.count(b"\n") - c0
    for old, new in pairs:
        o = old.encode("utf-8"); n = new.encode("utf-8")
        c = d.count(o)
        if c != 1:
            print("HIT-MISS", tag, c, old[:80]); sys.exit(1)
        d = d.replace(o, n)
    with open(path, "wb") as f:
        f.write(d)
    c1 = d.count(b"\r\n"); b1 = d.count(b"\n") - c1
    print("OK", tag, "CRLF", c0, "->", c1, "bareLF", b0, "->", b1)

patch(SRC, [
    ("DG.Q_BADGE_H = 16\r\n", "DG.Q_BADGE_H = 14\r\n"),
    ("DG.Q_BADGE_FS = 14\r\n", "DG.Q_BADGE_FS = 12\r\n"),
], "SRC")

patch(CHK, [
    ("       and 'DG.PlaceBadge(r.shareB, bx, L[\"可共享\"])' in src)\n",
     "       and 'DG.PlaceBadge(r.shareB, bx, L[\"可共享\"])' in src\n"
     "       and 'DG.Q_BADGE_H = 14' in src and 'DG.Q_BADGE_FS = 12' in src\n"
     "       and 'DG.Q_BADGE_GAP = 4' in src and 'DG.Q_BADGE_PAD = 3' in src)\n"),
], "CHK")

patch(RULE, [
    ("11 太小）。详情标题 18 类特例以各页既有定案为准。",
     "11 太小）。详情标题 18 类特例以各页既有定案为准。**唯一例外：行内小卡片/徽章 = 字号 12**"
     "（2026-10-13 用户拍板，见下方徽章标准）。"),
    ("） + 居中 FontString（14 号）。宽度 = `lab:GetStringWidth() + 2×3`；高 **16**"
     "（2026-10-13 用户拍板缩小：20→16，内衬 5→3，圆角 6→4，字号仍 14 —— 贴合改造前纯文字大小）、"
     "枚间距 **4**、贴着前一元素右缘排（`DG.PlaceBadge` 返下一枚 x）。",
     "） + 居中 FontString。**尺寸标准（2026-10-13 用户拍板 · 全插件遵从）**：高 **14** / "
     "字号 **12**（§7 唯一例外）/ 左右内衬 **3** / 枚间距 **4** / 圆角 **4**；"
     "宽度 = `lab:GetStringWidth() + 2×3`，卡内文字垂直居中（`DG.PlaceBadge` 按 `(行高 − 卡高)/2` 自动落）、"
     "贴着前一元素右缘排（返下一枚 x）。"),
], "RULE")
