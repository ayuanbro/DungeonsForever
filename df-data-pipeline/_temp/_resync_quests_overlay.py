# -*- coding: utf-8 -*-
"""只重生成 Data_DungeonQuests.lua 的 zhTW / enUS 覆盖副本（最小影响面）。

主表改动后必须同步覆盖层（整表替换）。本次仅改动 Data_DungeonQuests.lua，
故只跑该文件的生成，避免把其他未改动文件的漂移卷入。
"""
import os, sys, io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

NAME = 'Data_DungeonQuests.lua'

# ---- zhTW ----
import gen_zhtw_data as Z
n = Z.process(NAME)
print('zhTW %s -> %d 处转换' % (NAME, n))
Z._strip_comments_after_gen()

# ---- enUS ----
import gen_enus_data as E
SRC = os.path.join(E.SRC_DIR, NAME)
src = io.open(SRC, encoding='utf-8').read()
E.CUR_FILE = NAME
body, changed = E.transform(src)
head = E.HEAD.format(name=NAME)
dst = os.path.join(E.DST_DIR, NAME)
io.open(dst, 'w', encoding='utf-8', newline='\n').write(head + body)
print('enUS %s -> %d 处转换' % (NAME, changed))
E._strip_comments_after_gen()
