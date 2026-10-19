# -*- coding: utf-8 -*-
"""给 mk_df_mut.py 加第 ⑦ 步：2 条「上游数据同步」变异。

配合 mk_df_check.py 第 ⑨ 步的数据下限断言（NPCLoc >= 230 / QuestPreNpcID >= 210 /
表外链兜底用例 >= 80）。把两张表清空 → 断言必须变红，用来证明它们不是恒真白测。

★ 坑（第 ⑥ 步踩过）：mk_df_mut.py 里的 `"MUTATIONS = [\\n"` 是**源码里的转义串**，
  用「真实换行」当锚点会 0 命中。所以不锚它，改成锚一个真实换行的普通文本行
  （`# 残留自检`），把新内容作为**生成器代码**插进去。
★ 数据文件是 **LF**（不是 CRLF）→ 变异的字节锚点用 `\\n`。
★ 本文件的 GEN_BLOCK 是 **raw 字符串**：里面写的 `\\n` / `\\r\\n` / `"` 会原样成为
  mk_df_mut.py 的源码，不再经过一层转义。

用法：python patch_mkmut_sync.py --check   # 只看锚点命中
      python patch_mkmut_sync.py           # 正式写回
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'mk_df_mut.py')
CHECK_ONLY = '--check' in sys.argv

GEN_BLOCK = r'''
# ── ⑦ 2 条「上游数据同步」变异（2026-09-23：NPCLoc 176->237 / QuestPreNpcID 9->218）──
# 目标文件是数据层 Core/Data/Data_NPCLoc.lua（LF），所以字节锚点用 \n 而非 \r\n。
# 清空表 = 模拟「同步回了旧数据」这一真实事故形态（本项目踩过：上游重跑生成器，
# 本插件数据静默变旧）。变异是 bytes，注释只能英文。
_SYNC_MUT_DEFS = (
    "MUT_NPCLOC_EMPTY = ('Core/Data/Data_NPCLoc.lua', (\n"
    "    b'ns.NPCLoc = {\\n',\n"
    "    b'ns.NPCLoc = { } -- MUT: npc loc emptied\\nns._npc_dead = {\\n'))\n"
    "\n"
    "MUT_PRE_NPCID_EMPTY = ('Core/Data/Data_NPCLoc.lua', (\n"
    "    b'ns.QuestPreNpcID = {\\n',\n"
    "    b'ns.QuestPreNpcID = { } -- MUT: pre-npcid map emptied\\nns._qpn_dead = {\\n'))\n"
    "\n"
)
_SYNC_DEF_ANCHOR = "MUTATIONS = [\n"
if _SYNC_DEF_ANCHOR not in text:
    sys.exit('未找到 MUTATIONS 定义处（第⑦步），上游可能已改动')
if 'MUT_NPCLOC_EMPTY' in text:
    sys.exit('数据同步变异已存在，不再重复登记（幂等保护）')
text = text.replace(_SYNC_DEF_ANCHOR, _SYNC_MUT_DEFS + _SYNC_DEF_ANCHOR, 1)
print('  %-40s -> %d 处' % ('数据同步变异定义 2 条', 1))

_SYNC_REG_ANCHOR = (
    "    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),\n"
    "]\n"
)
if _SYNC_REG_ANCHOR not in text:
    sys.exit('未找到胶囊变异登记尾部锚点（第⑦步），上游或第⑥步可能已改动')
text = text.replace(
    _SYNC_REG_ANCHOR,
    "    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),\n"
    "\n"
    "    # ⑫ 上游数据同步下限守护（2026-09-23 NPCLoc 176->237 / QuestPreNpcID 9->218）\n"
    "    ('同步：NPCLoc 表被清空（数据退回旧版）', MUT_NPCLOC_EMPTY),\n"
    "    ('同步：QuestPreNpcID 表被清空（表外链落旗失效）', MUT_PRE_NPCID_EMPTY),\n"
    "]\n",
    1)
print('  %-40s -> %d 处' % ('数据同步变异登记 2 条', 1))

'''

raw = open(TARGET, 'rb').read()
txt = raw.decode('utf-8')

ANCHOR = '\n# 残留自检'
n = txt.count(ANCHOR)
print('  插入锚点 "# 残留自检" 命中 %d 次' % n)
if n != 1:
    sys.exit('插入锚点命中 %d 次（应为 1），中止' % n)

if '⑦ 2 条「上游数据同步」变异' in txt:
    print('  [SKIP] ⑦ 步已存在')
    sys.exit(0)

if CHECK_ONLY:
    print('  [--check] 锚点 OK，未写盘')
    sys.exit(0)

new = txt.replace(ANCHOR, GEN_BLOCK + ANCHOR, 1)
assert new != txt
open(TARGET, 'wb').write(new.encode('utf-8'))
print('  已写回 %s' % os.path.basename(TARGET))

import py_compile
py_compile.compile(TARGET, doraise=True)
print('  语法 OK')
