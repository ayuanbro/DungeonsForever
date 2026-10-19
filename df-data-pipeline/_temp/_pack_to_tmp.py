# -*- coding: utf-8 -*-
"""临时驱动：把 package_zip 的 OUT_DIR 指到 _temp/_out_tmp 再执行（绕开被锁的旧 ZIP）。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = io.open(os.path.join(HERE, "package_zip.py"), encoding="utf-8").read()
old = 'OUT_DIR = r"D:\\UGit\\打包后\\无限副本手册"'
assert old in src, "OUT_DIR 常量没匹配上"
src = src.replace(old, 'OUT_DIR = r"' + os.path.join(HERE, "_out_tmp") + '"')
code = compile(src, "package_zip.py", "exec")
g = {"__name__": "__main__", "__file__": os.path.join(HERE, "package_zip.py")}
exec(code, g)
