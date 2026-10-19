# -*- coding: utf-8 -*-
"""DungeonsForever/Core/DungeonUI.lua 补丁：顶栏胶囊改两颗 + 整体上移 15。

用户 2026-09-23 要求：
  ① 「副本」→「5人本」，右侧新增「团本」；
  ② 胶囊行整体往上移 15。

配套（已与用户确认）：「团本」= **空态骨架**（数据未收录），但要**能切换**。

做法：
  · 两颗等宽胶囊（DG.CAPSULE_W = 82，与原「副本」同宽）；host 只有一个 TOP 锚点 →
    整行自动水平居中（与主窗左侧标题横向不交叠）。
  · 上移量 = DG.CAPSULE_LIFT = 15，host 的 y 偏移从 `-ROW_SUB` 改成 `DG.CAPSULE_LIFT - ROW_SUB`。
  · U.raidPage 是常驻空态帧，**在 U:Build() 里建**（不在切页时懒建）——
    这样 harness 的「渲染路径零新建帧 / 首屏恰好新建 N 帧」不变量不受影响。
  · SwitchSub 按 key 分流：Dungeons → 原逻辑；Raids → 只切 SetShown，不构建不刷新。
  · 存档 `subTab` 从「写了没人读」变成真的会用（开窗沿用上次那颗）。

本文件是一次性补丁；改的是 CRLF 文件，故走「读 bytes → 归一成 \\n → 改 → 还原 CRLF → 写 bytes」。
用法：python patch_capsules.py --check   # 只验锚点
      python patch_capsules.py           # 落盘
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(os.path.dirname(HERE), 'Core', 'DungeonUI.lua')

raw = io.open(TARGET, 'rb').read()
# ── 换行自检：纯 CRLF（无裸 LF、无孤 CR），否则下面的归一化会丢信息 ──────────────
assert raw.count(b'\n') == raw.count(b'\r\n'), 'DungeonUI.lua 出现裸 LF，先查清再改'
assert raw.count(b'\r') == raw.count(b'\r\n'), 'DungeonUI.lua 出现孤立 CR，先查清再改'
n_crlf0 = raw.count(b'\r\n')

src = raw.decode('utf-8').replace('\r\n', '\n')

REPS = []


def rep(old, new, label):
    REPS.append((old, new, label))


# ── ① 内容面板锚点注释：说明胶囊现在会探出面板上边缘 ─────────────────────────
rep(
    '    -- hui：顶胶囊 -6.25..-26.25；classic：左上描边按钮 -36..-64，内容一律下移让位\n',
    '    -- hui：顶胶囊 -6.25..-26.25；classic：左上描边按钮 -36..-64，内容一律下移让位。\n'
    '    -- ★ 2026-09-23 起顶栏胶囊改为「5人本 / 团本」两颗并整体上移 DG.CAPSULE_LIFT(=15)：\n'
    '    --   胶囊会有 15px 探出本面板上边缘（用户指定，设计如此）；本面板位置不动。\n',
    '内容面板锚点注释',
)

# ── ② 顶栏胶囊：一颗「副本」→ 两颗「5人本 / 团本」───────────────────────────
rep(
    '-------------------- 头部控件 --------------------\n'
    '-- 上游顶栏是 7 个页签里排第 2 的那颗「副本」胶囊；本插件只有一页，\n'
    '-- 保留同一颗（同宽 82 / 同高 20 / 同位置：锚在 panel 顶、ROW_SUB=0），右侧留白。\n'
    '-- ⚠️ 删掉顶栏会让正文上移 → 与上游不再逐像素一致，故必须保留这颗胶囊。\n'
    'local function BuildSubTabs()\n'
    '    local defs = {\n'
    '        { key = "Dungeons", text = L["副本"], width = 82 },\n'
    '    }\n',
    '-------------------- 头部控件 --------------------\n'
    '-- 顶栏胶囊行 = 两颗：「5人本」/「团本」（用户 2026-09-23 指定，取代上游那颗单页签「副本」）。\n'
    '-- 上游此处是 7 个页签里排第 2 的那颗；本插件只保留这一行，其余位置留白。\n'
    '-- ⚠️ 删掉顶栏会让正文上移，故必须保留。\n'
    '-- ★ 两颗**等宽**（与原「副本」同宽）：分段控件的滑块宽度按按钮宽取，等宽才不跳形。\n'
    'DG.CAPSULE_LIFT = 15     -- 胶囊行整体自 panel 顶边上移的像素（用户 2026-09-23：「往上移 15」）\n'
    'DG.CAPSULE_W = 82        -- 单颗胶囊宽\n'
    'local function BuildSubTabs()\n'
    '    local defs = {\n'
    '        { key = "Dungeons", text = L["5人本"], width = DG.CAPSULE_W },\n'
    '        { key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W },\n'
    '    }\n',
    '顶栏胶囊 defs（两颗）',
)

# ── ③ 上移 15：host 的 y 偏移 ────────────────────────────────────────────────
rep(
    '    -- ⚠️ host 必须是「按钮的精确包围盒」：轨道锚在 host 四边、滑块偏移自 0 起累加，\n'
    '    --    host 尺寸/首个按钮位置对不上就会错位\n'
    '    local host = CreateFrame("Frame", nil, U.panel)\n'
    '    host:SetSize(totalW, BTN_H)\n'
    '    host:SetPoint("TOP", U.panel, "TOP", 0, -ROW_SUB)\n',
    '    -- ⚠️ host 必须是「按钮的精确包围盒」：轨道锚在 host 四边、滑块偏移自 0 起累加，\n'
    '    --    host 尺寸/首个按钮位置对不上就会错位\n'
    '    local host = CreateFrame("Frame", nil, U.panel)\n'
    '    host:SetSize(totalW, BTN_H)\n'
    '    -- ★ 上移 DG.CAPSULE_LIFT：胶囊 TOP 落在 panel 顶边**之上** 15px（y = +15），\n'
    '    --   本体 15~-5；hui 分段控件轨道再上下各外扩 2px → 整行约 +17~-7（panel 顶边记 0）。\n'
    '    --   横向仍是整行居中：host 只给一个 TOP 锚点 → 自动水平居中（主窗中线 ±总宽/2），\n'
    '    --   与左侧标题（主窗 TOPLEFT 18,-14）横向不交叠。\n'
    '    host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)\n',
    'host 上移 15',
)

# ── ④ 子页签行的坐标注释（胶囊底边上移后间距变了）───────────────────────────
rep(
    '    -- 子页签行紧贴在顶部标签栏之下。实测面板纵向坐标（截图逐像素量得）：\n'
    '    --   标签栏本体 y = 0~20（ROW_SUB=0、BTN_H=20），hui 分段控件胶囊再上下各外扩 2px → -2~22，\n'
    '    --   选中滑块高 22、底边落在 y = 23。\n'
    '    -- 故 SUBTAB_Y = ROW_CLASS(30) 正是「胶囊下方第一行」，与胶囊底留 7px；\n'
    '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。\n'
    '    -- ⚠️ 下限 = 23（胶囊底边），再往上就会压在标签栏上（实测写成 10 时两个子页签直接叠在标签栏上）。\n',
    '    -- 子页签行紧跟在顶部胶囊行之下。实测面板纵向坐标（截图逐像素量得）：\n'
    '    --   胶囊本体原是 y = 0~-20（ROW_SUB=0、BTN_H=20），hui 轨道上下各外扩 2px → +2~-22，\n'
    '    --   选中滑块高 22、底边约 y = -22；\n'
    '    --   ★ 2026-09-23 用户要求胶囊行整体上移 DG.CAPSULE_LIFT(=15) → 整行约 +17~-7。\n'
    '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由约 7px 变成约 22px。\n'
    '    --   ⚠️ 用户只要求挪胶囊：子页签行保持原值 30 不动（要收拢就同步减小 SUBTAB_Y）。\n'
    '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。\n'
    '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 7；本页仍取 30。\n',
    'SUBTAB_Y 注释',
)

# ── ⑤ SwitchSub：按 key 分流 ─────────────────────────────────────────────────
rep(
    '-------------------- 子页切换 --------------------\n'
    '-- 上游有 7 个分支；本插件只有副本一页，故恒等于「显示副本页 + 构建 + 刷新」。\n'
    '-- 页面互斥的 SetShown 逻辑不再需要（没有第二页），但切页仍走同一入口，\n'
    '-- 以便 build 中断后重入时逻辑与上游一致。\n'
    '-- 参数保留是为与上游调用点同形（BuildSubTabs 的 OnClick 传 tab.key），值被忽略。\n'
    'function U:SwitchSub(_key)\n'
    '    local key = "Dungeons"\n'
    '    U.curSub = key\n'
    '    DB().subTab = key\n'
    '    if U.dungeonPage then U.dungeonPage:SetShown(true) end\n'
    '    DG.BuildDungeons()\n'
    '    U:UpdateDungeons()\n'
    '    for _, tab in ipairs(U.subTabs or {}) do\n'
    '        local selected = (tab.key == key)\n'
    '        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end\n'
    '        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))\n'
    '    end\n'
    'end\n',
    '-------------------- 子页切换 --------------------\n'
    '-- 两颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本），其余一律按 5人本处理。\n'
    '-- 页面互斥走 SetShown（两页都是 panel 的常驻子帧，只切显隐、不重建）；\n'
    '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。\n'
    '-- ★「团本」目前是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：\n'
    '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。\n'
    'function U:SwitchSub(key)\n'
    '    local k = (key == "Raids") and "Raids" or "Dungeons"\n'
    '    U.curSub = k\n'
    '    DB().subTab = k\n'
    '    local isRaid = (k == "Raids")\n'
    '    if U.dungeonPage then U.dungeonPage:SetShown(not isRaid) end\n'
    '    if U.raidPage then U.raidPage:SetShown(isRaid) end\n'
    '    if not isRaid then\n'
    '        DG.BuildDungeons()\n'
    '        U:UpdateDungeons()\n'
    '    end\n'
    '    for _, tab in ipairs(U.subTabs or {}) do\n'
    '        local selected = (tab.key == k)\n'
    '        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end\n'
    '        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))\n'
    '    end\n'
    'end\n',
    'SwitchSub 按 key 分流',
)

# ── ⑥ UpdateActiveSub：空态团本页直接跳过 ────────────────────────────────────
rep(
    '-- 刷新当前所在的子页。上游此处**没有** Dungeons 分支（副本内容与职业无关，\n'
    '-- 作者当初未列入），后果是关窗再开沿用旧分组；本插件只有一个页面，恒刷新它。\n'
    'function U:UpdateActiveSub()\n'
    '    self:UpdateDungeons()\n'
    'end\n',
    '-- 刷新当前所在的子页。上游此处**没有** Dungeons 分支（副本内容与职业无关，\n'
    '-- 作者当初未列入），后果是关窗再开沿用旧分组；本插件按当前胶囊刷新。\n'
    '-- ★ 团本是空态骨架、没有可刷新的内容 → 直接跳过（别对未构建的副本页调 UpdateDungeons）。\n'
    'function U:UpdateActiveSub()\n'
    '    if self.curSub ~= "Raids" then self:UpdateDungeons() end\n'
    'end\n',
    'UpdateActiveSub 跳过团本',
)

# ── ⑦ Build：沿用存档 subTab + 建常驻空态团本页 ──────────────────────────────
rep(
    '    U.building = true\n'
    '\n'
    '    U.curSub = "Dungeons"\n'
    '\n'
    '    local panel = EnsureContent()\n'
    '    -- 副本页只在所有客户端展示（经典 26 个为通用数据，9 个无限新增仅在 16001 有意义）\n'
    '    U.dungeonPage = CreateFrame("Frame", nil, panel)\n'
    '    U.dungeonPage:SetAllPoints(panel)\n'
    '    U.dungeonPage:Hide()\n',
    '    U.building = true\n'
    '\n'
    '    -- 开窗落在上次那一颗胶囊上（存档 subTab；首次为 nil → 5人本）\n'
    '    U.curSub = (DB().subTab == "Raids") and "Raids" or "Dungeons"\n'
    '\n'
    '    local panel = EnsureContent()\n'
    '    -- 副本页只在所有客户端展示（经典 26 个为通用数据，9 个无限新增仅在 16001 有意义）\n'
    '    U.dungeonPage = CreateFrame("Frame", nil, panel)\n'
    '    U.dungeonPage:SetAllPoints(panel)\n'
    '    U.dungeonPage:Hide()\n'
    '\n'
    '    -- 团本页 = 空态骨架（boss / 掉落 / 任务均未收录）。\n'
    '    -- ⚠️ 必须在 Build 里一次建好，不能等切页时懒建：\n'
    '    --   harness 有「渲染路径零新建帧 / 首屏恰好新建 N 帧」的不变量，首屏之后不得再建帧。\n'
    '    --   帧本身没有贴图与背景（不遮任何东西），默认也不抢鼠标，只承载一句居中占位文案。\n'
    '    U.raidPage = CreateFrame("Frame", nil, panel)\n'
    '    U.raidPage:SetAllPoints(panel)\n'
    '    U.raidPage:Hide()\n'
    '    U.raidNote = MakeFS(U.raidPage, 15, C_GREY, "CENTER")\n'
    '    U.raidNote:SetPoint("CENTER", U.raidPage, "CENTER", 0, 0)\n'
    '    U.raidNote:SetText(L["团本数据待补"])\n',
    'Build：subTab + raidPage',
)

# ── ⑧ Build 收尾：按 curSub 切，而不是写死 Dungeons ──────────────────────────
rep(
    '    U:SwitchSub("Dungeons")\n',
    '    U:SwitchSub(U.curSub)\n',
    'Build 收尾 SwitchSub',
)

# ────────────────────────────────────────────────────────────────────────────
check_only = '--check' in sys.argv

txt = src
for old, new, label in REPS:
    n = txt.count(old)
    if n != 1:
        sys.exit('✗ 锚点命中 %d 次（应为 1）：%s' % (n, label))
    if old == new:
        sys.exit('✗ 新旧文本相同：%s' % label)
    txt = txt.replace(old, new)
    print('  ✔ %-28s 1 处' % label)

if check_only:
    print('全部 %d 条锚点各命中 1 次 —— 可以正式跑。' % len(REPS))
    sys.exit(0)

out = txt.replace('\n', '\r\n').encode('utf-8')
assert out.count(b'\n') == out.count(b'\r\n'), '落盘前出现裸 LF'
print('CRLF %d -> %d 行；裸 LF = %d' % (n_crlf0, out.count(b'\r\n'),
                                      out.count(b'\n') - out.count(b'\r\n')))
io.open(TARGET, 'wb').write(out)
print('已写回 %s（%d -> %d 字节）' % (TARGET, len(raw), len(out)))
