# -*- coding: utf-8 -*-
"""把 Data_ProfRecipes / Data_BIS / Data_ClassGuide 三组九个文件
的 ns.X 顶层赋值包成惰性构建函数 ns.EnsureX（与 _gear_lazy_wrap.py 同思路）。

- 头部：ns.NAME = {  →  ns.EnsureX = function() / if ns.NAME then return ns.NAME end / ns.NAME = {
- 尾部：文件末尾追加 return ns.NAME / end（BIS 的派生别名行保留在函数体内、return 之前）
"""
import os

ROOT = "D:/workspace/DungeonsForever/Core/Data"

JOBS = [
    ("Data_ProfRecipes.lua", "ProfRecipes", "EnsureProfRecipes"),
    ("Data_BIS.lua", "BIS", "EnsureBISData"),
    ("Data_ClassGuide.lua", "ClassGuide", "EnsureClassGuide"),
]

for sub in ("", "zhTW/", "enUS/"):
    for fname, var, fn in JOBS:
        p = os.path.join(ROOT, sub, fname)
        with open(p, "rb") as fh:
            d = fh.read()
        head = ("ns.%s = {\n" % var).encode()
        assert d.count(head) == 1, ("head", p, d.count(head))
        new_head = (
            ("ns.%s = function()\n" % fn).encode()
            + b"if ns." + var.encode() + b" then return ns." + var.encode() + b" end\n"
            + head
        )
        d = d.replace(head, new_head)
        if var == "BIS":
            tail_marker = b"ns.BIS.classes = ns.BIS.levels[ns.BIS.default].classes\n"
            assert d.rstrip(b"\n").endswith(tail_marker.rstrip(b"\n")), ("tail", p)
            d = d.rstrip(b"\n") + b"\nreturn ns.BIS\nend\n"
        else:
            assert d.endswith(b"}\n"), ("tail", p, d[-20:])
            d = d + b"return ns." + var.encode() + b"\nend\n"
        with open(p, "wb") as fh:
            fh.write(d)
        print("ok", os.path.getsize(p), p)
