import io, sys

SRC = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
RULE = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"

def patch(path, pairs):
    with open(path, "rb") as f:
        d = f.read()
    crlf = d.count(b"\r\n")
    bare = d.count(b"\n") - crlf
    for old, new in pairs:
        o = old.encode("utf-8")
        n = new.encode("utf-8")
        c = d.count(o)
        if c != 1:
            print("HIT-MISS", c, old[:70])
            sys.exit(1)
        d = d.replace(o, n)
    with open(path, "wb") as f:
        f.write(d)
    crlf2 = d.count(b"\r\n")
    bare2 = d.count(b"\n") - crlf2
    print("OK", path, "CRLF", crlf, "->", crlf2, "bareLF", bare, "->", bare2)

patch(SRC, [
    ("DG.Q_BADGE_H = 20\r\n", "DG.Q_BADGE_H = 16\r\n"),
    ("DG.Q_BADGE_PAD = 5\r\n", "DG.Q_BADGE_PAD = 3\r\n"),
    ("ns.hui.BuildRoundedBG(b, 6, bg or ns.hui.layer.L3,",
     "ns.hui.BuildRoundedBG(b, 4, bg or ns.hui.layer.L3,"),
])

patch(RULE, [
    ("+ 居中 FontString（14 号）。宽度 = `lab:GetStringWidth() + 2×5`；高 **20**、枚间距 **4**",
     "+ 居中 FontString（14 号）。宽度 = `lab:GetStringWidth() + 2×3`；高 **16**（2026-10-13 用户拍板缩小：20→16，内衬 5→3，圆角 6→4，字号仍 14 —— 贴合改造前纯文字大小）、枚间距 **4**"),
])
