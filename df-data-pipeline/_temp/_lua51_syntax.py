# -*- coding: utf-8 -*-
"""真 Lua 5.1（lupa）语法闸：逐个编译指定 lua 文件，报错即非零退出。

用法：python _temp/_lua51_syntax.py Core/Data/Data_BIS.lua Core/BisUI.lua ...
"""
import os
import sys

import lupa.lua51 as lua51

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)

rt = lua51.LuaRuntime()
bad = 0
for rel in sys.argv[1:]:
    p = rel if os.path.isabs(rel) else os.path.join(DF, rel)
    src = open(p, 'rb').read()
    try:
        rt.compile(src)
        print('  OK   %s' % rel)
    except Exception as e:
        bad += 1
        print('  FAIL %s\n       %s' % (rel, str(e).replace('\n', ' ')))
print('[lua51] %d 个文件，%d 个语法错误' % (len(sys.argv) - 1, bad))
sys.exit(1 if bad else 0)
