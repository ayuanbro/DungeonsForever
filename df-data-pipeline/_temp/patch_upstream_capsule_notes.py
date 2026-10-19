# -*- coding: utf-8 -*-
"""上游 TalentsForever/Core/UI.lua 一次性改动（2026-09-23，用户要求）：
  ① 顶栏胶囊行整体上移 10px（与 DungeonsForever 的位置对齐）
  ② 注释删减：把下游那次「注释措辞中性化」（NOTE_FIXES）原样回灌上游

★★ 硬约束：改动必须**严格不增删行**。
   下游 _temp/port_dungeonsforever.py 用行号区间从上游抽段（SEG_ISHUI=78-88 … SEG_MODULE=4585-7612），
   上游一增行，所有区间错位 → 抽错段（后果静默：少函数/多函数）。故脚本末尾断言行数不变。

★★ 连带影响（改上游会让下游生成器的锚点失效，已在上游改完后同步）：
   · NOTE_FIXES 37 条 → 上游已是中性文本后，下游该步将 0 命中 → 下游需清空该表
   · 下游补丁① 锚 245 行注释、补丁④ 锚 4994-4999 注释 → 锚点文本需同步更新

用法：python patch_upstream_capsule_notes.py [--check]
"""
import ast
import io
import os
import sys

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TG = os.path.join(os.path.dirname(DF), 'TalentsForever')
GEN = os.path.join(DF, '_temp', 'port_dungeonsforever.py')
UI = os.path.join(TG, 'Core', 'UI.lua')
BAK = os.path.join(DF, '_temp', '_sync_bak')

CRLF = '\r\n'
CHECK = '--check' in sys.argv

# ── 从下游生成器取 NOTE_FIXES（权威来源，避免手抄 37 条）──────────────────
src = io.open(GEN, encoding='utf-8').read()
fixes = None
leak = None
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            nm = getattr(t, 'id', None)
            if nm == 'NOTE_FIXES':
                fixes = ast.literal_eval(node.value)
            elif nm == '_LEAK':
                leak = ast.literal_eval(node.value)
if not fixes or not leak:
    sys.exit('未能从下游生成器解析出 NOTE_FIXES / _LEAK')

raw = open(UI, 'rb').read()
if raw.count(b'\r\n') != raw.count(b'\n'):
    sys.exit('上游 UI.lua 不是纯 CRLF（CRLF %d / LF %d）' % (raw.count(b'\r\n'), raw.count(b'\n')))
text = raw.decode('utf-8')
n0 = text.count(CRLF)
print('上游 UI.lua：%d 行  %d 字节' % (n0, len(raw)))


def sub(old, new, label, expect=1):
    global text
    c = text.count(old)
    if c != expect:
        sys.exit('[%s] 锚点命中 %d 次（应为 %d）：%r' % (label, c, expect, old[:90]))
    text = text.replace(old, new, 1)
    print('  %-30s OK' % label)


print('\n=== ① 顶栏胶囊上移 10px ===')
# 1a. 常量：并入已有 ROW_* 元组（不新增行 → 不动任何 SEG 行号）
sub(
    'local ROW_SUB, ROW_CLASS, ROW_CTRL, ROW_BTN, ROW_CODE = 0, 30, 62, 88, 114',
    'local ROW_SUB, ROW_CLASS, ROW_CTRL, ROW_BTN, ROW_CODE, CAPSULE_LIFT = 0, 30, 62, 88, 114, 10'
    '  -- CAPSULE_LIFT：顶栏胶囊行自 panel 顶边上移的像素（2026-09-23 用户要求）',
    '常量 CAPSULE_LIFT = 10')

# 1b. 内容面板锚点注释：给出上移后的新值（保留原值，不丢信息）
sub(
    '    -- hui：顶胶囊 -6.25..-26.25；classic：左上描边按钮 -36..-64，内容一律下移让位',
    '    -- hui：顶胶囊 -6.25..-26.25（2026-09-23 整行上移 10px → +3.75..-16.25）；'
    'classic：左上描边按钮 -36..-64，内容一律下移让位',
    '内容面板锚点注释')

# 1c. 真正的锚点：host 的 y 偏移
sub(
    '    host:SetPoint("TOP", U.panel, "TOP", 0, -ROW_SUB)',
    '    host:SetPoint("TOP", U.panel, "TOP", 0, CAPSULE_LIFT - ROW_SUB)'
    '  -- 整行上移 CAPSULE_LIFT(=10)px（2026-09-23）',
    'host 上移锚点')

# 1d. 副本页 SUBTAB_Y 注释：胶囊底边下移 5px → 与子页签行间距 22 → 18
sub(
    CRLF.join([
        '    -- 子页签行紧贴在顶部标签栏之下。实测面板纵向坐标（截图逐像素量得）：',
        '    --   标签栏本体 y = 0~20（ROW_SUB=0、BTN_H=20），hui 分段控件胶囊再上下各外扩 2px → -2~22，',
        '    --   选中滑块高 22、底边落在 y = 23。',
        '    -- 故 SUBTAB_Y = ROW_CLASS(30) 正是「胶囊下方第一行」，与胶囊底留 7px；',
        '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。',
        '    -- ⚠️ 下限 = 23（胶囊底边），再往上就会压在标签栏上（实测写成 10 时两个子页签直接叠在标签栏上）。',
    ]),
    CRLF.join([
        '    -- 子页签行紧跟在顶部胶囊行之下。实测面板纵向坐标（截图逐像素量得）：',
        '    --   胶囊本体原是 y = 0~-20（ROW_SUB=0、BTN_H=20），hui 轨道上下各外扩 2px → +2~-22，底边约 y = -22；',
        '    --   ★ 2026-09-23 胶囊行整体上移 CAPSULE_LIFT(=10) → 整行约 +12~-12，底边约 y = -12。',
        '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由约 8px 变成约 18px（子页签行本身不动）。',
        '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。',
        '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 12；本页仍取 30。',
    ]),
    '副本页 SUBTAB_Y 注释')

print('\n=== ② 注释删减（回灌下游那次中性化，%d 条）===' % len(fixes))
for i, (old, new) in enumerate(fixes, 1):
    if text.count(old) != 1:
        sys.exit('NOTE_FIXES 第 %d 条命中 %d 次（应为 1）：%r' % (i, text.count(old), old[:80]))
    text = text.replace(old, new, 1)
print('  37 条全部替换 OK')

# ── 自检 ────────────────────────────────────────────────────────────────
n1 = text.count(CRLF)
assert n1 == n0, '★ 行数变了（%d → %d）—— 会打乱下游 SEG_* 行号区间！' % (n0, n1)
print('\n行数不变 ✓  %d 行' % n1)

lines = text.split(CRLF)
MOD_A, MOD_B = 4585, 7612
_leak = []
for kw in leak:
    # 「TalentsForever」在上游是**自己的插件名**：4588 行 `TalentsForever_SourceURL` 是弹窗键名，
    # 本就该这么写（下游生成时才改名去撞车）→ 不作为措辞残留。
    if kw == 'TalentsForever':
        continue
    for n, l in enumerate(lines, 1):
        if kw in l and MOD_A <= n <= MOD_B:
            _leak.append('  行 %d  %s ← %s' % (n, l.strip()[:80], kw))
if _leak:
    sys.exit('★ 副本段内仍残留来源/移植措辞：\n' + '\n'.join(_leak[:8]))
print('副本段 (4585-7612) 措辞清洁 ✓')

# 段外残留只报告，不拦（那些是别的功能页，属另一次改动的范围）
print('\n段外同类措辞（本轮不动，仅报告）：')
for kw in ('站点', '照抄', 'nfu', 'AtlasQuest'):
    pos = [n for n, l in enumerate(lines, 1) if kw in l and not (MOD_A <= n <= MOD_B)]
    if pos:
        print('  %-12s %s' % (kw, pos))

if CHECK:
    print('\n[--check] 全部通过，未写盘。')
    sys.exit(0)

os.makedirs(BAK, exist_ok=True)
bak = os.path.join(BAK, 'UI.lua.bak')
open(bak, 'wb').write(raw)
open(UI, 'wb').write(text.encode('utf-8'))
after = open(UI, 'rb').read()
print('\n已写回 %s' % UI)
print('  备份 → %s' % bak)
print('  字节 %d → %d ；CRLF %d / LF %d' % (len(raw), len(after), after.count(b'\r\n'), after.count(b'\n')))
