# -*- coding: utf-8 -*-
"""把 Data_Gear 三个语言层的 ns.GearData 顶层赋值包成惰性构建函数 ns.EnsureGearData。"""
import os

FILES = [
    r"D:/workspace/DungeonsForever/Core/Data/Data_Gear.lua",
    r"D:/workspace/DungeonsForever/Core/Data/zhTW/Data_Gear.lua",
    r"D:/workspace/DungeonsForever/Core/Data/enUS/Data_Gear.lua",
]
OLD_HEAD = b"ns.GearData = {\n"
NEW_HEAD = (
    b"ns.EnsureGearData = function()\n"
    b"if ns.GearData then return ns.GearData end\n"
    b"ns.GearData = {\n"
)
OLD_TAIL = b"  },\n}\n"
NEW_TAIL = b"  },\n  }\nreturn ns.GearData\nend\n"

for p in FILES:
    with open(p, "rb") as fh:
        d = fh.read()
    assert d.count(OLD_HEAD) == 1, ("head", p, d.count(OLD_HEAD))
    assert d.count(OLD_TAIL) == 1, ("tail", p, d.count(OLD_TAIL))
    assert d.count(b"\r\n") == 0, ("crlf", p)
    d = d.replace(OLD_HEAD, NEW_HEAD).replace(OLD_TAIL, NEW_TAIL)
    with open(p, "wb") as fh:
        fh.write(d)
    print("ok", os.path.getsize(p), p)
