# -*- coding: utf-8 -*-
"""一次性补丁：往 port_dungeonsforever.py 的 CAPSULE_PATCHES 追加一条「副本卡字号」。

用户 2026-09-24 要求：「五人本列表页面每个副本左上角和左下角的介绍字体都需要放大一些」。

落点说明：
  · 卡片左上角 = card.name（副本名，原 12pt）；左下角 = card.meta（「等级 · BOSS n」，原 10pt）。
  · Core/DungeonUI.lua 是生成物（源区间是硬编码行号，不能手改）→ 走 CAPSULE_PATCHES 受检替换。
  · ★ 只改数字、不增删行：产物的行号结构保持逐行稳定，避免任何基于行号的引用被悄悄挪位。

受检插入：锚点命中不是 1 次就直接退出（不静默改错）。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'port_dungeonsforever.py')
CRLF = '\r\n'

BLOCK = [
    '# ── 副本列表卡：左上角副本名 / 左下角「等级 · BOSS n」字号各 +2（2026-09-24 用户要求）──',
    '# 用户原话：「五人本列表页面每个副本左上角和左下角的介绍字体都需要放大一些，现在有点太小了」。',
    '# ★ 只改数字、不增删行：产物 DungeonUI.lua 的行号结构保持逐行稳定（说明写在这里，不落进产物）。',
    '#   12pt / 10pt → 14pt / 12pt：卡 175x58 内两行合计 26px，仍余 32px 空隙；',
    '#   卡宽 175 - 左右内边距 16 - 「新」标记 20 = 139px，最长副本名（4 个汉字 ≈ 56px）远未触边。',
    '#   层级也随之理顺：副本名 14 > 副行 12 > 「新」标记 11 / 分组说明 11。',
    'CAPSULE_PATCHES.append((',
    "    _p('    card.name = MakeFS(card, 12, C_WHITE, \"LEFT\")',",
    "       '    card.name:SetPoint(\"TOPLEFT\", card, \"TOPLEFT\", 8, -5)',",
    "       '    card.name:SetWordWrap(false)',",
    "       '    card.meta = MakeFS(card, 10, C_GREY, \"LEFT\")',",
    "       '    card.meta:SetPoint(\"BOTTOMLEFT\", card, \"BOTTOMLEFT\", 8, 5)'),",
    "    _p('    card.name = MakeFS(card, 14, C_WHITE, \"LEFT\")',",
    "       '    card.name:SetPoint(\"TOPLEFT\", card, \"TOPLEFT\", 8, -5)',",
    "       '    card.name:SetWordWrap(false)',",
    "       '    card.meta = MakeFS(card, 12, C_GREY, \"LEFT\")',",
    "       '    card.meta:SetPoint(\"BOTTOMLEFT\", card, \"BOTTOMLEFT\", 8, 5)'),",
    "    '副本卡字号 12/10 → 14/12',",
    '))',
]

src = io.open(P, 'r', encoding='utf-8', newline='').read()

if '副本卡字号 12/10' in src:
    print('  [SKIP] 补丁已在位（幂等）')
    sys.exit(0)

ANCHOR_TAIL = "for old, new, label in CAPSULE_PATCHES:"
idx = src.find(ANCHOR_TAIL)
if idx < 0:
    sys.exit('找不到应用点 for old, new, label in CAPSULE_PATCHES:')

head = src[:idx]
tail = src[idx:]

# 幂等/唯一性护栏：BLOCK 首行的关键词在文件里必须不存在
if '副本列表卡：左上角副本名' in src:
    sys.exit('BLOCK 首行关键词已存在，拒绝重复插入')

new = head + CRLF.join(BLOCK) + CRLF + CRLF + tail
io.open(P, 'w', encoding='utf-8', newline='').write(new)
print('  [OK] 已追加「副本卡字号」补丁到 CAPSULE_PATCHES')
