# -*- coding: utf-8 -*-
"""文档同步：上游/下游 AGENTS.md（2026-09-23 胶囊上移 10px + 注释回灌 + 不增删行纪律）。

用法：python patch_agents_docs.py [--check]
"""
import sys

DF = 'D:/workspace/DungeonsForever'
TG = 'D:/Game/World of Warcraft/_classic_titan_/Interface/AddOns/TalentsForever'
LF = '\n'
CHECK = '--check' in sys.argv


def load(p):
    raw = open(p, 'rb').read()
    assert raw.count(b'\r\n') == 0, '%s 应为纯 LF' % p
    return raw.decode('utf-8')


def save(p, t):
    open(p, 'wb').write(t.encode('utf-8'))


def sub(t, old, new, label):
    c = t.count(old)
    if c != 1:
        sys.exit('[%s] 锚点命中 %d 次（应为 1）：%r' % (label, c, old[:100]))
    return t.replace(old, new, 1)


# ── 上游 AGENTS.md：新增两节（顶栏胶囊位置 + 不增删行纪律）──────────────────
up_path = TG + '/AGENTS.md'
up = load(up_path)
anchor = '## 种族页（种族详情 / 职业×种族组合总表）'
new_section = LF.join([
    '## 顶栏胶囊位置与「不增删行」纪律（2026-09-23）',
    '',
    '- 主窗顶栏胶囊行（`Core/UI.lua` 的 `BuildSubTabs`）**整体自内容面板顶边上移 `CAPSULE_LIFT = 10` px**：',
    '  `host:SetPoint("TOP", U.panel, "TOP", 0, CAPSULE_LIFT - ROW_SUB)`（`ROW_SUB = 0`）。',
    '  胶囊底边随之由 y≈-22 抬到 y≈-12，与副本页子页签行（`SUBTAB_Y = 30`）的间距由 ~8px 变 ~18px。',
    '  常量**并入第 44 行 `local ROW_SUB, ROW_CLASS, … ` 那一行**，不另起一行。',
    '- ★★ **`Core/UI.lua` 严禁增删行**：DungeonsForever（无限副本手册）的抽取生成器',
    '  `AddOns/DungeonsForever/_temp/port_dungeonsforever.py` 用**硬编码行号区间**从本文件抽段',
    '  （`SEG_ISHUI = 78-88` … `SEG_MODULE = 4585-7612`），本文件一增删行，这些区间全部错位',
    '  （抽错段的后果是**静默**的：少函数 → 运行期 nil 调用）。要加常量/说明就**并入已有行**。',
    '  一次性改动脚本：`AddOns/DungeonsForever/_temp/patch_upstream_capsule_notes.py`（带 `--check` 演练 + 断言行数不变）。',
    '- 注释口径（与 DungeonsForever 一致）：**不留「站点 / AtlasQuest / nfu / 照抄 / 抄它 / 移植 / 剥离 / 上游」字样**，',
    '  数据来源只保留 `wowhead`。2026-09-23 已清洗副本段（4585-7612，37 条）；',
    '  **副本段外仍有 6 处「站点」+ 1 处「照抄」（1266 / 2183 / 2184 / 2192 / 2391 / 2671 / 3690）**，属另一次改动的范围。',
    '',
])
up = sub(up, anchor, new_section + anchor, '上游：新增胶囊/行号纪律小节')

# ── 下游 AGENTS.md：四处 ─────────────────────────────────────────────────
dn_path = DF + '/AGENTS.md'
dn = load(dn_path)

dn = sub(
    dn,
    '- 改动上游行号后，`port_dungeonsforever.py` 里的 `SEG_*` 区间必须同步；脚本有边界自检，抽错会直接报错退出（不会静默生成半截文件）。',
    '- ★★ **改上游 `Core/UI.lua` 必须严格不增删行**：`SEG_*` 是**硬编码行号区间**'
    '（`SEG_ISHUI = 78-88` … `SEG_MODULE = 4585-7612`），上游一增删行就全部错位。'
    '要加常量/说明就**并入已有行**（例：上游 `CAPSULE_LIFT` 并入 `ROW_SUB, ROW_CLASS, …` 那行）。'
    '脚本有边界自检会报错退出，但只在段首尾附近有效。',
    '下游：SEG 行号纪律')

dn = sub(
    dn,
    LF.join([
        '- 界面层注释由 `port_dungeonsforever.py` 的 `NOTE_FIXES`（逐条点名替换）清洗；',
        '  脚本末尾还有一层**产物级终检 `LEAK`**，产物里再出现这些词就直接 `die`（关键词：',
    ]),
    LF.join([
        '- ★ **2026-09-23 起上游也做了同一批中性化**（37 条，由 `patch_upstream_capsule_notes.py` 施加到上游 `Core/UI.lua`）',
        '  → 抽取段本就是中性文本，`NOTE_FIXES` 已**清空为空表**（变量与循环保留，以后需要再填）。',
        '  ⚠️ 改动上游那 37 处注释后，重新抽取的产物应当**字节不变**（「回灌等价」强自检，已验证）。',
        '  ⚠️ **改上游注释会让本生成器的锚点失效**：`CAPSULE_PATCHES` 的补丁①锚 245 行内容面板注释、',
        '  补丁④锚 `SUBTAB_Y` 注释 —— 上游一改就必须同步这两个锚点（本次已同步）。',
        '- 脚本末尾还有一层**产物级终检 `LEAK`**，产物里再出现这些词就直接 `die`（关键词：',
    ]),
    '下游：NOTE_FIXES 说明')

dn = sub(
    dn,
    '胶囊上移后与正文首行的间距由 ~7px 变 ~22px（`SUBTAB_Y` 仍为 30，用户只要求挪胶囊、没要求挪正文）。',
    '胶囊底边由 y≈-22 抬到 y≈-12，与正文首行的间距由 ~8px 变 **~18px**'
    '（`SUBTAB_Y` 仍为 30，用户只要求挪胶囊、没要求挪正文；`SUBTAB_Y` 可用下限由 23 降到 ~12）。',
    '下游：胶囊间距数值')

dn = sub(
    dn,
    '  - ⚠️ **上移量（纯几何）只能静态钉**：',
    '  - ★ **上游 `TalentsForever/Core/UI.lua` 的顶栏胶囊行也已移到同一位置**'
    '（`CAPSULE_LIFT = 10`；2026-09-23 用户要求「把上游软件的胶囊按钮也移到这个位置」）——两边数值保持一致，改一边记得看另一边。\n'
    '  - ⚠️ **上移量（纯几何）只能静态钉**：',
    '下游：上游同位置说明')

if CHECK:
    print('[--check] 两个 AGENTS.md 共 5 处锚点全部唯一，未写盘。')
    sys.exit(0)

save(up_path, up)
save(dn_path, dn)
for p in (up_path, dn_path):
    b = open(p, 'rb').read()
    print('%-70s %6d 字节  LF %d / CRLF %d' % (p.split('AddOns/')[-1], len(b), b.count(b'\n'), b.count(b'\r\n')))
