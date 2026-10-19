# -*- coding: utf-8 -*-
"""下游生成器连带同步（上游 UI.lua 已改注释 + 胶囊上移后必须同步，否则抽取直接 die）。

三处：
  ① CAPSULE_PATCHES 条目① 的锚点  ← 上游 245 行注释已加「上移 10px」说明
  ② CAPSULE_PATCHES 条目④ 的锚点  ← 上游 SUBTAB_Y 注释已改成新版 6 行
  ③ NOTE_FIXES 清空                ← 上游已做过同一批中性化，本步从「改写」退化为「守护」

★ ① ② 只换锚点、不动输出 → 重跑生成链后下游产物应**字节不变**（这是「37 条回灌完全等价」的强自检）。

用法：python patch_downstream_for_upstream.py [--check]
"""
import sys

GEN = '_temp/port_dungeonsforever.py'
LF = '\n'
CHECK = '--check' in sys.argv

t = open(GEN, encoding='utf-8').read()
n0 = len(t)


def sub(old, new, label):
    global t
    c = t.count(old)
    if c != 1:
        sys.exit('[%s] 锚点命中 %d 次（应为 1）：%r' % (label, c, old[:120]))
    t = t.replace(old, new, 1)
    print('  %-34s OK' % label)


print('=== 补丁锚点同步 ===')
sub(
    "        _p('    -- hui：顶胶囊 -6.25..-26.25；classic：左上描边按钮 -36..-64，内容一律下移让位'),",
    "        _p('    -- hui：顶胶囊 -6.25..-26.25（2026-09-23 整行上移 10px → +3.75..-16.25）；"
    "classic：左上描边按钮 -36..-64，内容一律下移让位'),",
    '补丁① 锚点（24x 行内容面板注释）')

sub(
    LF.join([
        "        _p('    -- 子页签行紧贴在顶部标签栏之下。实测面板纵向坐标（截图逐像素量得）：',",
        "           '    --   标签栏本体 y = 0~20（ROW_SUB=0、BTN_H=20），hui 分段控件胶囊再上下各外扩 2px → -2~22，',",
        "           '    --   选中滑块高 22、底边落在 y = 23。',",
        "           '    -- 故 SUBTAB_Y = ROW_CLASS(30) 正是「胶囊下方第一行」，与胶囊底留 7px；',",
        "           '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。',",
        "           '    -- ⚠️ 下限 = 23（胶囊底边），再往上就会压在标签栏上（实测写成 10 时两个子页签直接叠在标签栏上）。'),",
    ]),
    LF.join([
        "        _p('    -- 子页签行紧跟在顶部胶囊行之下。实测面板纵向坐标（截图逐像素量得）：',",
        "           '    --   胶囊本体原是 y = 0~-20（ROW_SUB=0、BTN_H=20），hui 轨道上下各外扩 2px → +2~-22，底边约 y = -22；',",
        "           '    --   ★ 2026-09-23 胶囊行整体上移 CAPSULE_LIFT(=10) → 整行约 +12~-12，底边约 y = -12。',",
        "           '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由约 8px 变成约 18px（子页签行本身不动）。',",
        "           '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。',",
        "           '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 12；本页仍取 30。'),",
    ]),
    '补丁④ 锚点（SUBTAB_Y 注释）')

print('\n=== NOTE_FIXES 清空 ===')
k = t.index('# ── 注释措辞中性化')
j = t.index('for old, new in NOTE_FIXES:')
block = LF.join([
    '# ── 注释措辞中性化（2026-09-23 定：不留「移植 / 剥离 / 照抄 / 上游 / 第三方来源」字样）────────',
    '#    ★★ 2026-09-23：**上游 UI.lua 已同步做过同一批中性化**（37 条，由',
    '#       _temp/patch_upstream_capsule_notes.py 施加到上游）→ 抽取段本身就是中性文本，',
    '#       本表退化为空表。真正的守护是下面的兜底闸（_LEAK）：',
    '#       上游若把那批措辞改回去，抽取时会直接 die（不会静默产出带来源出处的注释）。',
    'NOTE_FIXES = []',
]) + LF
t = t[:k] + block + t[j:]
print('  %-34s OK（%d → %d 字符）' % ('NOTE_FIXES = []', n0, len(t)))

# 自检：具名来源的「替换对」已清空；`站点`/`AtlasQuest` 只应出现在兜底闸的关键词表里
leftover = [l.strip()[:90] for l in t.split(LF)
            if ('站点' in l or 'AtlasQuest' in l)
            and '_LEAK' not in l and not l.strip().startswith('LEAK =')]
assert not leftover, '生成器仍有具名来源替换对：%r' % leftover
print('  生成器内已无具名来源替换对（仅剩兜底闸关键词表）✓')

if CHECK:
    print('\n[--check] 通过，未写盘。')
    sys.exit(0)

open(GEN, 'wb').write(t.encode('utf-8'))
print('\n已写回 %s' % GEN)
