import io, sys

def rd(p):
    return open(p, "rb").read()

def wr(p, d):
    open(p, "wb").write(d)

def rep(d, old, new, path):
    n = d.count(old)
    if n != 1:
        print("!! 命中 %d 次 (期望 1): %s" % (n, path))
        print("   old=", old[:80])
        sys.exit(1)
    return d.replace(old, new)

DF = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"

# ---------- 1) 运行时：开关右对齐到左卡右缘 ----------
d = rd(DF)
print("DungeonUI CRLF", d.count(b"\r\n"), "bareLF", d.count(b"\n") - d.count(b"\r\n"))

old_a = b'            tg:SetPoint("TOPLEFT", plateL, "TOPLEFT", DG.Q_PAD + 3 * 100, -DG.Q_PAD - 2)'
new_a = b'            tg:SetPoint("TOPRIGHT", plateL, "TOPRIGHT", -DG.Q_PAD, -DG.Q_PAD - 2)'
d = rep(d, old_a, new_a, "DF/anchor")

old_b = (b'        tg.label = MakeFS(tg, 14, C_TEXT, "LEFT")\r\n'
         b'        tg.label:SetPoint("LEFT", tg, "RIGHT", 6, 0)\r\n'
         b'        tg.label:SetText(L["\xe6\x98\xbe\xe7\xa4\xba\xe5\xb7\xb2\xe5\xae\x8c\xe6\x88\x90"])\r\n'
         b'        tg:SetHitRectInsets(0, -((tg.label:GetStringWidth() or 60) + 6), 0, 0)')
new_b = (b'        tg.label = MakeFS(tg, 14, C_TEXT, "RIGHT")\r\n'
         b'        tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)\r\n'
         b'        tg.label:SetText(L["\xe6\x98\xbe\xe7\xa4\xba\xe5\xb7\xb2\xe5\xae\x8c\xe6\x88\x90"])\r\n'
         b'        tg:SetHitRectInsets(-((tg.label:GetStringWidth() or 60) + 6), 0, 0, 0)')
d = rep(d, old_b, new_b, "DF/label")
wr(DF, d)
print("DungeonUI 写回 OK")

# ---------- 2) harness：把右对齐钉进断言 ----------
c = rd(CK)
print("check CRLF", c.count(b"\r\n"), "bareLF", c.count(b"\n") - c.count(b"\r\n"))

old_c = (b"       'U.dungeonQDoneTg' in src and 'ns.hui.ReskinToggle(tg)' in src\r\n"
         b"       and 'function U:SetQuestShowDone(on)' in src\r\n"
         b"       and 'if bt and i > 3 then' in src)")
new_c = (b"       'U.dungeonQDoneTg' in src and 'ns.hui.ReskinToggle(tg)' in src\r\n"
         b"       and 'function U:SetQuestShowDone(on)' in src\r\n"
         b"       and 'if bt and i > 3 then' in src\r\n"
         b"       and 'tg:SetPoint(\"TOPRIGHT\", plateL, \"TOPRIGHT\", -DG.Q_PAD, -DG.Q_PAD - 2)' in src\r\n"
         b"       and 'tg.label:SetPoint(\"RIGHT\", tg, \"LEFT\", -6, 0)' in src)")
c = rep(c, old_c, new_c, "CK/assert")
wr(CK, c)
print("check 写回 OK")
