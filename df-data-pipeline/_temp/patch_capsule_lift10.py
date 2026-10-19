# -*- coding: utf-8 -*-
"""一次性补丁：胶囊行上移量 15 -> 10（用户 2026-09-23：「胶囊按钮往下移动5」）

改动面（三处，缺一处就会全绿但是旧值）：
  1. _temp/port_dungeonsforever.py   ← 常量 + 4 处注释里的数值（生成物禁手改）
  2. _temp/mk_df_check.py            ← 静态断言钉的数值
  3. AGENTS.md                       ← 几何表 + 胶囊小节

几何（BTN_H = 20，panel 顶边记 0）：
  LIFT=15 → 本体 +15~-5 ，轨道外扩 2 → 整行 +17~-7 ；胶囊底边 -7  → 与 SUBTAB_Y(30) 间距 ~22
  LIFT=10 → 本体 +10~-10，轨道外扩 2 → 整行 +12~-12；胶囊底边 -12 → 与 SUBTAB_Y(30) 间距 ~18
  SUBTAB_Y 可用下限：-7 时 ~7  →  -12 时 ~12
"""
import io
import re
import sys


def load(path):
    raw = open(path, 'rb').read()
    assert raw.count(b'\r\n') == 0, '%s 应为纯 LF（脚本文件）' % path
    return raw.decode('utf-8')


def save(path, text):
    open(path, 'wb').write(text.encode('utf-8'))


def sub(text, pairs, tag):
    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            sys.exit('[%s] 锚点命中 %d 次（应为 1）：%r' % (tag, n, old[:90]))
        text = text.replace(old, new, 1)
    print('  %-28s %d 处替换 OK' % (tag, len(pairs)))
    return text


CHECK = '--check' in sys.argv

# ── ① 生成器 ────────────────────────────────────────────────────────────
GEN = '_temp/port_dungeonsforever.py'
t = load(GEN)
t = sub(t, [
    # 头部总说明
    ('# ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 15 ──────────────────────────────',
     '# ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 10 ──────────────────────────────'),
    ('# 用户 2026-09-23 要求：「副本」→「5人本」，右侧加「团本」；胶囊行整体往上移 15。',
     '# 用户 2026-09-23：「副本」→「5人本」，右侧加「团本」；胶囊行整体往上移 15；\n'
     '# 随后追加「胶囊按钮往下移动 5」→ 净上移量 DG.CAPSULE_LIFT = 10。'),
    # 补丁①：内容面板锚点注释
    ('           \'    -- ★ 2026-09-23 起顶栏胶囊改为「5人本 / 团本」两颗并整体上移 DG.CAPSULE_LIFT(=15)：\',',
     '           \'    -- ★ 2026-09-23 起顶栏胶囊改为「5人本 / 团本」两颗并整体上移 DG.CAPSULE_LIFT(=10)：\','),
    ('           \'    --   胶囊会有 15px 探出本面板上边缘（用户指定，设计如此）；本面板位置不动。\'),',
     '           \'    --   胶囊会有 10px 探出本面板上边缘（用户指定，设计如此）；本面板位置不动。\'),'),
    # 补丁②：常量行
    ("           'DG.CAPSULE_LIFT = 15     -- 胶囊行整体自 panel 顶边上移的像素（用户 2026-09-23：「往上移 15」）',",
     "           'DG.CAPSULE_LIFT = 10     -- 胶囊行整体自 panel 顶边上移的像素（用户 2026-09-23：「往上移 15」→「往下移动 5」→ 净 10）',"),
    # 补丁③：host 上移注释 + label
    ("           '    -- ★ 上移 DG.CAPSULE_LIFT：胶囊 TOP 落在 panel 顶边**之上** 15px（y = +15），',",
     "           '    -- ★ 上移 DG.CAPSULE_LIFT：胶囊 TOP 落在 panel 顶边**之上** 10px（y = +10），',"),
    ("           '    --   本体 15~-5；hui 分段控件轨道再上下各外扩 2px → 整行约 +17~-7（panel 顶边记 0）。',",
     "           '    --   本体 10~-10；hui 分段控件轨道再上下各外扩 2px → 整行约 +12~-12（panel 顶边记 0）。',"),
    ("        'host 上移 15',", "        'host 上移 10',"),
    # 补丁④：SUBTAB_Y 注释
    ("           '    --   ★ 2026-09-23 用户要求胶囊行整体上移 DG.CAPSULE_LIFT(=15) → 整行约 +17~-7。',",
     "           '    --   ★ 2026-09-23 用户要求胶囊行整体上移 DG.CAPSULE_LIFT(=10) → 整行约 +12~-12。',"),
    ("           '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由约 7px 变成约 22px。',",
     "           '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由原约 8px 变成约 18px。',"),
    ("           '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 7；本页仍取 30。'),",
     "           '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 12；本页仍取 30。'),"),
], '生成器 port_dungeonsforever.py')
# 残留自检：生成器里不得再有 15 这个旧值
bad = re.findall(r'DG\.CAPSULE_LIFT\s*=\s*15|\+17~-7|本体 15~-5|上移量[^\n]*15', t)
assert not bad, '生成器残留旧值：%r' % bad[:5]

# ── ② harness 生成器 ───────────────────────────────────────────────────
MK = '_temp/mk_df_check.py'
m = load(MK)
m = sub(m, [
    ("    # ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 15（2026-09-23 用户指定）──",
     "    # ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 10（2026-09-23 用户指定）──"),
    ("    ck('★★ 胶囊行上移量 DG.CAPSULE_LIFT = 15',",
     "    ck('★★ 胶囊行上移量 DG.CAPSULE_LIFT = 10（先 +15 后 -5）',"),
    (r"       re.search(r'DG\.CAPSULE_LIFT\s*=\s*15\b', src) is not None)",
     r"       re.search(r'DG\.CAPSULE_LIFT\s*=\s*10\b', src) is not None)"),
    ("# ── ⑧ 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 15（2026-09-23 用户指定）────────",
     "# ── ⑧ 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 10（2026-09-23 用户指定）────────"),
], 'harness 生成器 mk_df_check.py')
bad = re.findall(r'CAPSULE_LIFT\s*=\s*15', m)
assert not bad, 'harness 残留旧值：%r' % bad[:5]

# ── ③ AGENTS.md ────────────────────────────────────────────────────────
AG = 'AGENTS.md'
a = load(AG)
a = sub(a, [
    ('`ROW_SUB=0`、`DG.CAPSULE_LIFT=15` |',
     '`ROW_SUB=0`、`DG.CAPSULE_LIFT=10` |'),
    ('**整体自面板顶边上移 15px**（`DG.CAPSULE_LIFT = 15`，用户 2026-09-23 要求）。',
     '**整体自面板顶边上移 10px**（`DG.CAPSULE_LIFT = 10`；用户 2026-09-23 先要求「往上移 15」、随后「往下移动 5」→ 净 10）。'),
    ('- ⚠️ **上移 15px 只能静态钉**：',
     '- ⚠️ **上移量（纯几何）只能静态钉**：'),
], 'AGENTS.md')

# ── 逐文件写回（--check 时只演练）───────────────────────────────────────
if CHECK:
    print('\n[--check] 全部锚点唯一，未写盘。')
else:
    save(GEN, t)
    save(MK, m)
    save(AG, a)
    print('\n已写回 3 个文件。')
    for p in (GEN, MK, AG):
        b = open(p, 'rb').read()
        print('  %-34s %6d 字节  LF %d  CRLF %d' % (p, len(b), b.count(b'\n'), b.count(b'\r\n')))
