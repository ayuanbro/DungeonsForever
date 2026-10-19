# -*- coding: utf-8 -*-
"""一次性补丁：往 port_dungeonsforever.py 注入 FONT_UPGRADES 层（详情页字号口径）。

用户 2026-09-24 对照详情页截图逐项定口径：
  · 标题类（右栏任务标题 / 分组头）= 16；横幅标题已是 16。
  · 正文、按钮、行内小字（前置 / 阵营兜底单字）一律 14。
  · 「数据来源：wowhead」署名保持 11 不动。
行高 / 列位 / 步进随字号配套（见规则表各条注释）。

层设计：受检批量替换（每条声明预期命中数，数不对就 die），与 CAPSULE_PATCHES 的
count==1 并行不悖 —— put 步进这类同类串散落多处，语义一致就一起升。
注入位置：措辞终检之前（注释同样过 LEAK 闸）、写盘之前。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'port_dungeonsforever.py')
CRLF = '\r\n'

BLOCK = [
    "# ── 详情页字号口径：标题 16 / 正文 14（2026-09-24 用户定）─────────────────────",
    "# 用户对照详情页截图逐项定：标题类（右栏任务标题/分组头）16；正文、按钮、行内小字",
    "# （前置/阵营兜底单字）一律 14；「数据来源：wowhead」署名保持 11。",
    "# ★ 受检批量替换：每条声明预期命中数，数不对就 die。put 步进这类同类串散落多处，",
    "#   语义一致就一起升；顺序敏感：put(f,20)→24 必须排在 put(f,16)→20 之前防链式误改。",
    "FONT_UPGRADES = [",
    "    ('DG.Q_FS_DET = 12', 'DG.Q_FS_DET = 14', 1, '右列详情正文 12→14'),",
    "    ('DG.Q_FS_META = 12', 'DG.Q_FS_META = 14', 1, '任务行副字（地点/等级/状态）12→14'),",
    "    ('DG.Q_FS_HDR = 14', 'DG.Q_FS_HDR = 16', 1, '分组头 14→16'),",
    "    ('U.dungeonQDetName = MakeFS(qdchild, 15, C_GOLD, \"LEFT\")',",
    "     'U.dungeonQDetName = MakeFS(qdchild, 16, C_GOLD, \"LEFT\")', 1, '右栏任务标题 15→16'),",
    "    ('U.dungeonSum = MakeFS(page, 12, C_GREY, \"RIGHT\")',",
    "     'U.dungeonSum = MakeFS(page, 14, C_GREY, \"RIGHT\")', 1, '统计行 12→14'),",
    "    ('U.dungeonDetailMeta = MakeFS(hero, 12, C_GREY, \"LEFT\")',",
    "     'U.dungeonDetailMeta = MakeFS(hero, 14, C_GREY, \"LEFT\")', 1, '横幅 meta 12→14'),",
    "    ('U.dungeonQuestSum = MakeFS(qchild, 13, C_GOLD, \"LEFT\")',",
    "     'U.dungeonQuestSum = MakeFS(qchild, 14, C_GOLD, \"LEFT\")', 1, '任务进度行 13→14'),",
    "    ('U.dungeonQDetSt = MakeFS(qdchild, 12, C_GREY, \"LEFT\")',",
    "     'U.dungeonQDetSt = MakeFS(qdchild, 14, C_GREY, \"LEFT\")', 1, '右栏状态行 12→14'),",
    "    ('U.dungeonDetailNote = MakeFS(dchild, 13, C_GREY, \"LEFT\")',",
    "     'U.dungeonDetailNote = MakeFS(dchild, 14, C_GREY, \"LEFT\")', 1, '详情备注 13→14'),",
    "    ('U.dungeonQuestNote = MakeFS(qchild, 13, C_GREY, \"LEFT\")',",
    "     'U.dungeonQuestNote = MakeFS(qchild, 14, C_GREY, \"LEFT\")', 1, '任务备注 13→14'),",
    "    ('r.emL = MakeFS(r, 10, C_GREY, \"LEFT\")', 'r.emL = MakeFS(r, 14, C_GREY, \"LEFT\")', 1, '阵营兜底单字 10→14'),",
    "    ('r.cls = MakeFS(r, 10, C_GREY, \"LEFT\")', 'r.cls = MakeFS(r, 14, C_GREY, \"LEFT\")', 1, '职业徽记单字 10→14'),",
    "    ('r.pre = MakeFS(r, 10, C_GREY, \"LEFT\")', 'r.pre = MakeFS(r, 14, C_GREY, \"LEFT\")', 1, '前置标 10→14'),",
    "    ('            f = MakeFS(child, 11, C_GREY, \"LEFT\")',",
    "     '            f = MakeFS(child, 14, C_GREY, \"LEFT\")', 1, '右栏字段名 11→14'),",
    "    ('r.name = MakeFS(r, 12, C_TEXT, \"LEFT\")', 'r.name = MakeFS(r, 14, C_TEXT, \"LEFT\")', 1, '前导环节名 12→14'),",
    "    ('r.st = MakeFS(r, 11, C_GREY, \"RIGHT\")', 'r.st = MakeFS(r, 14, C_GREY, \"RIGHT\")', 1, '环节状态 11→14'),",
    "    ('r.sub = MakeFS(r, 11, C_GREY, \"LEFT\")', 'r.sub = MakeFS(r, 14, C_GREY, \"LEFT\")', 1, '环节副行 11→14'),",
    "    ('NewButton(page, def.text, SW, 22, 13)', 'NewButton(page, def.text, SW, 24, 14)', 1, '子页签 13→14'),",
    "    ('NewButton(detail, L[\"‹ 副本\"], 70, 22, 13)', 'NewButton(detail, L[\"‹ 副本\"], 70, 24, 14)', 1, '返回按钮 13→14'),",
    "    ('NewButton(detail, def.text, 70, 22, 13)', 'NewButton(detail, def.text, 70, 24, 14)', 1, '掉落/任务按钮 13→14'),",
    "    ('NewButton(detail, \"\", 76, 22, 12)', 'NewButton(detail, \"\", 92, 24, 14)', 1, '筛选芯片 12→14 加宽 76→92'),",
    "    ('(i - 1) * 82, -DG.FILTER_Y', '(i - 1) * 96, -DG.FILTER_Y', 1, '筛选芯片间距 82→96'),",
    "    ('DG.Q_ROW_H = 30', 'DG.Q_ROW_H = 34', 1, '任务行高 30→34'),",
    "    ('DG.Q_HDR_H = 22', 'DG.Q_HDR_H = 26', 1, '分组头行高 22→26'),",
    "    ('DG.Q_SUM_H = 24', 'DG.Q_SUM_H = 28', 1, '进度行高 24→28'),",
    "    ('(DG.Q_ROW_H - 10) / 2', '(DG.Q_ROW_H - 14) / 2', 3, '行内小字居中偏移按 14 号重算 ×3'),",
    "    ('DG.Q_X_PRE = 408', 'DG.Q_X_PRE = 416', 1, '前置列右移 8px 让位 14 号「N 级可接」'),",
    "    ('r:SetSize(detW, 34)', 'r:SetSize(detW, 38)', 1, '前导环节行高 34→38'),",
    "    ('r.sub:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 10, -18)',",
    "     'r.sub:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 10, -21)', 1, '环节副行下移 18→21'),",
    "    ('f:SetSize(detW, 20)', 'f:SetSize(detW, 24)', 1, '起始 NPC 行高 20→24'),",
    "    ('put(stf, 18)', 'put(stf, 22)', 1, '状态行步进 18→22'),",
    "    ('put(f, 20)', 'put(f, 24)', 5, 'kv/NPC 行步进 20→24 ×5'),",
    "    ('put(f, 16)', 'put(f, 20)', 6, '小节标题步进 16→20 ×6'),",
    "    ('put(t, 18)', 'put(t, 22)', 3, '正文行步进 18→22 ×3'),",
    "    ('y = -24', 'y = -28', 1, '右栏头部 y 起点 24→28'),",
    "]",
    "for _old, _new, _exp, _lab in FONT_UPGRADES:",
    "    _n = out.count(_old)",
    "    if _n != _exp:",
    "        die('字号升级锚点命中 %d 次（应 %d）：%s' % (_n, _exp, _lab))",
    "    out = out.replace(_old, _new)",
    "print('  详情页字号：标题 16 / 正文 14（%d 条受检替换全部命中）' % len(FONT_UPGRADES))",
]

src = io.open(P, 'r', encoding='utf-8', newline='').read()

if 'FONT_UPGRADES' in src:
    print('  [SKIP] FONT_UPGRADES 层已在位（幂等）')
    sys.exit(0)

ANCHOR = '# ── 输出措辞终检'
idx = src.find(ANCHOR)
if idx < 0 or src.count(ANCHOR) != 1:
    sys.exit('注入锚点（措辞终检注释）找不到或不唯一')

head, tail = src[:idx], src[idx:]
new = head + CRLF.join(BLOCK) + CRLF + CRLF + tail
io.open(P, 'w', encoding='utf-8', newline='').write(new)
print('  [OK] 已注入 FONT_UPGRADES 层（%d 条规则）' % (len(BLOCK) - 9))
