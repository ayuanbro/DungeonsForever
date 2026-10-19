import sys

P = r"D:\workspace\DungeonsForever\Core\Hui.lua"

PAIRS = [
    # 1) 常量区：新增公共控件边框色，开关边框改为共用它
    ("    local C_TOGGLE_BORDER = {0.42, 0.42, 0.46}\n",
     "    local C_CTRL_BORDER = {0x4A / 255, 0x52 / 255, 0x63 / 255}\n"
     "    local C_TOGGLE_BORDER = C_CTRL_BORDER\n"),
    # 2) SkinButton：按钮边框改用同一常量（单一真源）
    ("        local C_BORDER = {0x4A / 255, 0x52 / 255, 0x63 / 255}\n",
     "        local C_BORDER = C_CTRL_BORDER\n"),
]

d = open(P, "rb").read()
c0 = d.count(b"\r\n"); b0 = d.count(b"\n") - c0
for old, new in PAIRS:
    o = old.encode("utf-8"); n = new.encode("utf-8")
    c = d.count(o)
    print("hit", c, old.strip()[:60])
    if c != 1:
        sys.exit(1)
    d = d.replace(o, n)
open(P, "wb").write(d)
c1 = d.count(b"\r\n"); b1 = d.count(b"\n") - c1
print("OK Hui.lua CRLF", c0, "->", c1, "bareLF", b0, "->", b1)
