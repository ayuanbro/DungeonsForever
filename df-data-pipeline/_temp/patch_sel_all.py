import sys

DF = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
CK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"

# ---------- 1) 运行时 ----------
d = open(DF, "rb").read()
print("DF CRLF", d.count(b"\r\n"), "bareLF", d.count(b"\n") - d.count(b"\r\n"))

old = (b'            local sel = (i <= 3 and side == key)'
       b' or (i == 4 and status == "todo") or (i == 5 and status == "done")')
new = (b'            local sel = (i <= 3 and side == (i == 1 and "all" or key))'
       b' or (i == 4 and status == "todo") or (i == 5 and status == "done")')
n = d.count(old)
print("DF 命中", n)
if n != 1:
    sys.exit(1)
open(DF, "wb").write(d.replace(old, new))
print("DF 写回 OK")

# ---------- 2) harness 静态 pin ----------
c = open(CK, "rb").read()
print("CK CRLF", c.count(b"\r\n"), "bareLF", c.count(b"\n") - c.count(b"\r\n"))

anchor = (b'       and \'tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)\' in src)\n')
add = (b"    ck('\xe2\x98\x85\xe2\x98\x85 \xe4\xbb\xbb\xe5\x8a\xa1\xe9\xa1\xb5\xe3\x80\x8c\xe5\x85\xa8\xe9\x83\xa8\xe3\x80\x8d"
       b"\xe9\x80\x89\xe4\xb8\xad\xe6\x80\x81\xef\xbc\x88\xe6\x8c\x89\xe9\x92\xae\xe9\x94\xae\xe5\x80\xbc qall \xe9\xa1\xbb"
       b"\xe5\xbd\x92\xe4\xb8\x80\xe5\x88\xb0 side \xe5\x80\xbc\xe5\x9f\x9f all/A/H\xef\xbc\x89',\n"
       b"       'side == (i == 1 and \"all\" or key)' in src)\n")
n = c.count(anchor)
print("CK 命中", n)
if n != 1:
    sys.exit(1)
c = c.replace(anchor, anchor + add)
open(CK, "wb").write(c)
print("CK 写回 OK")
