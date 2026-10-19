# -*- coding: utf-8 -*-
"""给 mk_df_check.py 加第 ⑨ 步：上游数据同步的「下限守护」断言。

背景（2026-09-23）：上游 `Core/Data/Data_NPCLoc.lua` 由 `_temp/gen_nploc.py` 产出，
本插件靠 `_temp/sync_data.py` 逐字节同步。这个项目**踩过**「上游重跑生成器 →
本插件数据静默变旧」的坑（当时残留 NPCLoc 176 / QuestPreNpcID 9，
而新数据是 237 / 218）。所以要钉两条下限 + 一条「表外链兜底真被数据支撑」。

★ 关键（与 ⑦⑧ 步同一个坑）：mk_df_check.py **不含 harness 正文** —— 它在运行时把上游
   `tf_dungeon_check.py` 读进 `text` 再派生。所以断言不能直接写成字面量（写了只是
   mk_df_check.py 里多一段没人执行的文本），必须写成**生成器代码**：
   定义 SYNC_ANCHOR / SYNC_EXTRA，再做 text.replace(...) 让它落进生成器。

用法：python patch_mkcheck_sync.py --check   # 只看锚点命中
      python patch_mkcheck_sync.py           # 正式写回
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'mk_df_check.py')
CHECK_ONLY = '--check' in sys.argv

GEN_BLOCK = '''
# ── ⑨ 上游数据同步「下限守护」（2026-09-23：NPCLoc 176→237 / QuestPreNpcID 9→218）──
# 上游 Data_NPCLoc.lua 由 _temp/gen_nploc.py 产出，本插件靠 _temp/sync_data.py 逐字节同步。
# 踩过的坑：上游重跑生成器后本插件数据静默变旧（旧数据只有 NPCLoc 176 / QuestPreNpcID 9）。
SYNC_ANCHOR = '    local U = TF_NS.DungeonUI\\n'
SYNC_EXTRA = r"""
    -- ---------- 上游数据同步下限守护（2026-09-23）----------
    -- 上游 Core/Data/Data_NPCLoc.lua 由 _temp/gen_nploc.py 产出；本插件靠 _temp/sync_data.py
    -- 逐字节同步。踩过的坑：上游一重跑，本插件数据静默变旧（曾残留 176 / 9）。
    -- 这里钉「不得回退」的下限 + 「表外链兜底真被数据支撑」，防止将来又同步到旧数据。
    do
      local _npc, _pre = TF_NS.NPCLoc, TF_NS.QuestPreNpcID
      local _nNpc, _nPre = 0, 0
      for _ in pairs(_npc or {}) do _nNpc = _nNpc + 1 end
      for _ in pairs(_pre or {}) do _nPre = _nPre + 1 end
      ck("★★ NPCLoc 条目数不得回退（2026-09-23 实测 237）", _nNpc >= 230, _nNpc)
      ck("★★ QuestPreNpcID 条目数不得回退（2026-09-23 实测 218）", _nPre >= 210, _nPre)
      -- 表外链兜底：统计「q[9] 数字段、行内拿不到 NPCID、只能靠 QuestPreNpcID、
      -- 且该 NPC 在 NPCLoc 里有坐标」的用例数 —— 少了就说明同步回了旧数据。
      local _hit = 0
      for _, _dg in ipairs(TF_NS.DungeonData.dungeons) do
        for _, _qq in ipairs(TF_NS.DungeonModule.QuestList(_dg)) do
          if _qq[9] then
            for _, _seg in ipairs(_qq[9]) do
              if type(_seg) == "number" then
                local _pr = TF_NS.DungeonModule.QuestRowByID(_seg)
                if _pr == nil or _pr[16] == nil then
                  local _nid = _pre and _pre[_seg]
                  if _nid and _npc and _npc[_nid] then _hit = _hit + 1 end
                end
              end
            end
          end
        end
      end
      ck("★★ 表外链靠 QuestPreNpcID 兜底且能落旗的用例 >= 80", _hit >= 80, _hit)
    end
"""
if SYNC_ANCHOR not in text:
    sys.exit('未找到⑨步数据守护插入锚点（上游 harness 可能已改动）')
text = text.replace(SYNC_ANCHOR, SYNC_ANCHOR + SYNC_EXTRA, 1)
print('  %-30s → %d 处' % ('⑨数据同步守护块', 1))

'''

raw = open(TARGET, 'rb').read()
txt = raw.decode('utf-8')

ANCHOR = '\n# 残留自检'
n = txt.count(ANCHOR)
print('  插入锚点 "%s" 命中 %d 次' % ('# 残留自检', n))
if n != 1:
    sys.exit('插入锚点命中 %d 次（应为 1），中止' % n)

if '⑨ 上游数据同步' in txt:
    print('  [SKIP] ⑨ 步已存在')
    sys.exit(0)

if CHECK_ONLY:
    print('  [--check] 锚点 OK，未写盘')
    sys.exit(0)

new = txt.replace(ANCHOR, GEN_BLOCK + ANCHOR, 1)
assert new != txt
open(TARGET, 'wb').write(new.encode('utf-8'))
print('  已写回 %s（%d -> %d 字节）' % (os.path.basename(TARGET), len(raw), len(new)))

# 语法自检
import py_compile
py_compile.compile(TARGET, doraise=True)
print('  mk 语法 OK')
