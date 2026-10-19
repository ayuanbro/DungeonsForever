import sys

CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
c = open(CK, "rb").read()
print("check CRLF", c.count(b"\r\n"), "bareLF", c.count(b"\n") - c.count(b"\r\n"))

old = (b"       'U.dungeonQDoneTg' in src and 'ns.hui.ReskinToggle(tg)' in src\n"
       b"       and 'function U:SetQuestShowDone(on)' in src\n"
       b"       and 'if bt and i > 3 then' in src)")
new = (b"       'U.dungeonQDoneTg' in src and 'ns.hui.ReskinToggle(tg)' in src\n"
       b"       and 'function U:SetQuestShowDone(on)' in src\n"
       b"       and 'if bt and i > 3 then' in src\n"
       b"       and 'tg:SetPoint(\"TOPRIGHT\", plateL, \"TOPRIGHT\", -DG.Q_PAD, -DG.Q_PAD - 2)' in src\n"
       b"       and 'tg.label:SetPoint(\"RIGHT\", tg, \"LEFT\", -6, 0)' in src)")
n = c.count(old)
print("命中", n)
if n != 1:
    sys.exit(1)
open(CK, "wb").write(c.replace(old, new))
print("OK")
