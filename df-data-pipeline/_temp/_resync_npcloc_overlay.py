# -*- coding: utf-8 -*-
"""只重生成 Data_NPCLoc.lua 的 zhTW / enUS 覆盖副本。"""
import os, sys, io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

NAME = 'Data_NPCLoc.lua'

import gen_zhtw_data as Z
n = Z.process(NAME)
print('zhTW %s -> %d 处转换' % (NAME, n))
Z._strip_comments_after_gen()

import gen_enus_data as E
src = io.open(os.path.join(E.SRC_DIR, NAME), encoding='utf-8').read()
E.CUR_FILE = NAME
body, changed = E.transform(src)
io.open(os.path.join(E.DST_DIR, NAME), 'w', encoding='utf-8', newline='\n').write(
    E.HEAD.format(name=NAME) + body)
print('enUS %s -> %d 处转换' % (NAME, changed))
E._strip_comments_after_gen()
