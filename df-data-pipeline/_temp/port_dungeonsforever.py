# -*- coding: utf-8 -*-
"""把 TalentsForever/Core/UI.lua 的副本段抽成 DungeonsForever/Core/DungeonUI.lua。

纯机械抽取：按行号区间从源文件逐字取（保留 CRLF），只做点名替换 + 手写文件头/生命周期。
★ 点名替换里含「去全局化」：上游的 BuildDungeons / BuildDungeonOverview 是裸全局，
  必须挂到本文件 local 表 DG 上，否则会被后加载的同名插件覆盖（2026-09-23 实机事故）。
用法：python port_dungeonsforever.py
验收：生成后跑 luacheck，确认 0 error，且 `ns.DungeonUI` 有导出。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)                                     # DungeonsForever/
SRC = os.path.join(os.path.dirname(DF), 'TalentsForever', 'Core', 'UI.lua')
DST = os.path.join(DF, 'Core', 'DungeonUI.lua')

# ── 源文件行号区间（1-based，闭区间）。改上游行号后必须同步这里 ──────────────────
SEG_ISHUI = (78, 88)      # IsHui / Fnt / Unpack
SEG_MAKEFS = (112, 118)   # MakeFS
SEG_NEWBUTTON = (164, 170)  # NewButton
SEG_MAKEOUTLINE = (172, 210)  # 按钮描边（注释 + 实现）
SEG_SETOUTLINE = (212, 225)
SEG_SETTIP = (227, 235)
SEG_ENSURE = (237, 256)   # 内容根容器
SEG_MODULE = (4585, 7612)  # 「数据来源条目」标题 → RenderDungeonTab 末行 end

CRLF = '\r\n'


def die(msg):
    sys.stderr.write('port_dungeonsforever: %s\n' % msg)
    sys.exit(1)


# ── 退役闸（2026-09-25）─────────────────────────────────────────────────────
# 上游 TalentsForever 已移除副本页（副本功能由本插件独立承载），
# Core/DungeonUI.lua 自此冻结为手维护源文件，本生成器退役、不再运行。
_src_probe = open(SRC, 'rb').read().decode('utf-8', 'replace')
if '-------------------- 副本模块 --------------------' not in _src_probe:
    die('上游 TalentsForever/Core/UI.lua 已无副本模块段（2026-09-25 移除）：'
        '本生成器退役，DungeonUI.lua 已冻结为手维护源文件，请勿再运行本脚本。')

raw = open(SRC, 'rb').read()
if raw.count(b'\r\n') < 1000:
    die('%s 应为 CRLF 行尾，实际 CRLF 计数 %d' % (SRC, raw.count(b'\r\n')))
lines = raw.decode('utf-8').split(CRLF)     # lines[i-1] = 第 i 行


def seg(a, b):
    return CRLF.join(lines[a - 1:b])


# ── 边界自检：抽错一段的后果是静默的（少函数 → 运行时 nil 调用）────────────────
checks = [
    (lines[4584], '数据来源条目', 'SEG_MODULE 首行'),
    (lines[4583].strip(), '', 'SEG_MODULE 之前应是空行（其上是 U:UpdateActiveSub 的 end）'),
    (lines[4582].strip(), 'end', 'SEG_MODULE 之前应是 U:UpdateActiveSub 的结尾 end'),
    (lines[7611].strip(), 'end', 'SEG_MODULE 末行应为 RenderDungeonTab 的 end'),
    (lines[7613], 'function U:Build()', 'SEG_MODULE 之后应紧跟 U:Build'),
    (lines[4658], 'local DG = {}', 'DG 表定义应在段内'),
    (lines[4983], 'function BuildDungeons()', 'BuildDungeons 定义应在段内'),
    (lines[5307], 'function BuildDungeonOverview()', 'BuildDungeonOverview 定义应在段内'),
]
for text, needle, what in checks:
    if needle not in text:
        die('%s 校验失败：期望含 %r，实际 %r' % (what, needle, text[:80]))

module = seg(*SEG_MODULE)

# ── 点名替换（全部可用 grep 复核）────────────────────────────────────────────
REPLACES = [
    # 上游 TS:DB() 返回 TalentsForeverDB.sim；本插件的 DB() 返回同形子表、字段名不变
    ('TS:DB()', 'DB()'),
    # 块内原有导出名 ns.DungeonUI 让位给页面控制器 U；DG 表改挂 DungeonModule
    ('ns.DungeonUI = DG', 'ns.DungeonModule = DG'),
    # 弹窗键去撞车
    ('TalentsForever_SourceURL', 'DungeonsForever_SourceURL'),
    # 兜底默认 URL 去身份（2026-09-24 用户口径：数据来源只保留 wowhead）。
    # 该默认值运行时永不被显示（每次点击都会先 ShowSourceURL(url) 覆盖），
    # 但作为字面量进了包，解包可搜到 talentsforever.com 域名 —— 换成 wowhead。
    ('local pendingSourceURL = "https://talentsforever.com"',
     'local pendingSourceURL = "https://www.wowhead.com/forever"'),
    # ★★ 去全局化（2026-09-23 实机事故，见 AGENTS.md「跨插件全局撞名」）：
    #    上游这两个是**裸全局函数**，TalentsForever 也定义同名全局；WoW 按文件夹名字母序加载
    #    （DungeonsForever < TalentsForever）→ 上游覆盖本插件 → 本插件的 U:SwitchSub 调到上游函数
    #    （用上游的文件级 local U，U.dungeonPage 为 nil）→ MakeFS(nil)，
    #    报错落在 TalentsForever/Core/UI.lua:113。挂到本文件已有的 local 表 DG 上，
    #    既消掉全局又不新增 main chunk local（上游那个 chunk 已逼近 200 上限）。
    #    注意 BuildDungeonOverview 在段内**先调用（上游 5278 行）后定义（5308 行）**，
    #    所以只能用表字段、不能用 local function。
    ('BuildDungeons()', 'DG.BuildDungeons()'),
    ('BuildDungeonOverview()', 'DG.BuildDungeonOverview()'),
]
for old, new in REPLACES:
    if old not in module:
        die('替换目标未命中：%r（上游可能已改名，先核对再跑）' % old)
    module = module.replace(old, new)

# ── 注释措辞中性化（2026-09-23 定：不留「移植 / 剥离 / 照抄 / 上游 / 第三方来源」字样）────────
#    ★★ 2026-09-23：**上游 UI.lua 已同步做过同一批中性化**（37 条，由
#       _temp/patch_upstream_capsule_notes.py 施加到上游）→ 抽取段本身就是中性文本，
#       本表退化为空表。真正的守护是下面的兜底闸（_LEAK）：
#       上游若把那批措辞改回去，抽取时会直接 die（不会静默产出带来源出处的注释）。
NOTE_FIXES = []
for old, new in NOTE_FIXES:
    if old not in module:
        die('注释措辞替换目标未命中：%r' % old)
    module = module.replace(old, new)

# 兜底闸：中性化之后，段内不得再出现任何具名来源 / 移植措辞
_LEAK = ('站点', 'AtlasQuest', 'nfuwow', 'nfu ', 'TalentsForever', '上游', '剥离',
         '照抄', '抄它', '抽取段', '出处', '参考')
_leak = []
for _kw in _LEAK:
    if _kw in module:
        for _l in module.split(CRLF):
            if _kw in _l:
                _leak.append('%s ← %s' % (_l.strip()[:70], _kw))
                break
if _leak:
    die('段内仍残留来源/移植措辞：\n  ' + '\n  '.join(_leak[:8]))

# ★ 硬闸：段内不得再出现裸全局函数定义（跨插件撞名的唯一来源）。
#   实测口径：裸全局函数被后加载的同名插件覆盖后，调用点会默默跑别人的代码，
#   而离线 harness（只加载本插件）**永远测不出**。故必须在生成期就拦住。
_bare = re.findall(r'(?m)^function\s+[A-Za-z_]\w*\s*\(', module)
if _bare:
    die('段内仍有裸全局函数定义（会与上游撞名，必须挂到 DG. 上）：%s' % _bare)

if 'TalentsForever' in module:
    bad = [l for l in module.split(CRLF) if 'TalentsForever' in l]
    die('段内仍残留 TalentsForever：\n  ' + '\n  '.join(bad[:5]))

# ── 工具函数（逐字照抄，仅 Fnt 的字体来源改成本文件 local）──────────────────────
ishui = seg(*SEG_ISHUI).replace('BIAOGE_FONT', 'FONT_BASE')

HEAD = '''local _, ns = ...
local L = ns.L
if not ns.IsTitan then return end
local U = {}
ns.DungeonUI = U
local FONT_BASE
local CONTENT_W = 960
local PAGE_INSET = 12
local HDR_H = 142
local CARD_H = 484
local CREDIT_H = 22
local CONTENT_H = HDR_H + CARD_H + CREDIT_H
local ROW_SUB = 0
local ROW_CLASS = 30
local FALLBACK_ICON = "Interface\\\\Icons\\\\INV_Misc_QuestionMark"
local C_GOLD = { 1, 0.82, 0.0 }
local C_GREEN = { 0.25, 0.85, 0.35 }
local C_GREY = { 0.55, 0.55, 0.55 }
local C_DIM = { 0.63, 0.63, 0.63 }
local C_DARKGREY = { 0.30, 0.30, 0.30 }
local C_WHITE = { 1, 1, 1 }
local C_TEXT = { 0.88, 0.88, 0.88 }
local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local s = DungeonsForeverDB.dungeon
    if not s then
        s = {}
        DungeonsForeverDB.dungeon = s
    end
    return s
end'''

TAIL = '''
-------------------- 头部控件 --------------------
-- 上游顶栏是 7 个页签里排第 2 的那颗「副本」胶囊；本插件只有一页，
-- 保留同一颗（同宽 82 / 同高 20 / 同位置：锚在 panel 顶、ROW_SUB=0），右侧留白。
-- ⚠️ 删掉顶栏会让正文上移 → 与上游不再逐像素一致，故必须保留这颗胶囊。
local function BuildSubTabs()
    local defs = {
        { key = "Dungeons", text = L["副本"], width = 82 },
    }
    local BTN_H = IsHui() and 20 or 26
    local GAP = IsHui() and 0 or 6
    local totalW = 0
    for i, t in ipairs(defs) do
        totalW = totalW + t.width
        if i > 1 then totalW = totalW + GAP end
    end
    -- ⚠️ host 必须是「按钮的精确包围盒」：轨道锚在 host 四边、滑块偏移自 0 起累加，
    --    host 尺寸/首个按钮位置对不上就会错位
    local host = CreateFrame("Frame", nil, U.panel)
    host:SetSize(totalW, BTN_H)
    host:SetPoint("TOP", U.panel, "TOP", 0, -ROW_SUB)

    local ctrl
    if IsHui() and ns.hui and ns.hui.CreateSegmentedControl then
        ctrl = ns.hui.CreateSegmentedControl(host)
    end

    local btns, prev = {}, nil
    for _, tab in ipairs(defs) do
        local bt
        if ctrl then
            bt = CreateFrame("Button", nil, host)
            bt:SetSize(tab.width, BTN_H)
            if prev then
                bt:SetPoint("LEFT", prev, "RIGHT", 0, 0)
            else
                bt:SetPoint("TOPLEFT", host, "TOPLEFT", 0, 0)
            end
            local t = bt:CreateFontString()
            t:SetAllPoints()
            t:SetFont(Fnt(14))
            t:SetText(tab.text)
            t:SetWordWrap(false)
            t:SetTextColor(Unpack(C_DIM))
            bt:SetFontString(t)
        else
            bt = NewButton(host, tab.text, tab.width, BTN_H, 14)
            if prev then
                bt:SetPoint("LEFT", prev, "RIGHT", GAP, 0)
            else
                bt:SetPoint("TOPLEFT", host, "TOPLEFT", 0, 0)
            end
        end
        prev = bt
        btns[#btns + 1] = bt
        tab.button = bt
        bt:SetScript("OnClick", function()
            U:SwitchSub(tab.key)
            ns.PlaySound(1)
        end)
    end
    if ctrl then ctrl:AttachButtons(btns) end
    U.subTabs = defs
    U.subCtrl = ctrl
end

-------------------- 子页切换 --------------------
-- 上游有 7 个分支；本插件只有副本一页，故恒等于「显示副本页 + 构建 + 刷新」。
-- 页面互斥的 SetShown 逻辑不再需要（没有第二页），但切页仍走同一入口，
-- 以便 build 中断后重入时逻辑与上游一致。
-- 参数保留是为与上游调用点同形（BuildSubTabs 的 OnClick 传 tab.key），值被忽略。
function U:SwitchSub(_key)
    local key = "Dungeons"
    U.curSub = key
    DB().subTab = key
    if U.dungeonPage then U.dungeonPage:SetShown(true) end
    DG.BuildDungeons()
    U:UpdateDungeons()
    for _, tab in ipairs(U.subTabs or {}) do
        local selected = (tab.key == key)
        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end
        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))
    end
end

-- 刷新当前所在的子页。上游此处**没有** Dungeons 分支（副本内容与职业无关，
-- 作者当初未列入），后果是关窗再开沿用旧分组；本插件只有一个页面，恒刷新它。
function U:UpdateActiveSub()
    self:UpdateDungeons()
end

-------------------- 构建 --------------------
function U:Build()
    if U.built or U.building then return end
    FONT_BASE = FONT_BASE or ns.FONT
    if not FONT_BASE then return end
    U.building = true

    U.curSub = "Dungeons"

    local panel = EnsureContent()
    -- 副本页只在所有客户端展示（经典 26 个为通用数据，9 个无限新增仅在 16001 有意义）
    U.dungeonPage = CreateFrame("Frame", nil, panel)
    U.dungeonPage:SetAllPoints(panel)
    U.dungeonPage:Hide()

    -- 页面 frame 重建后懒构建旗标必须复位：否则旧页面的控件引用全部悬空
    U.dungeonBuilt = false
    -- 副本页的常驻控件池 / 滚动子帧都挂在旧 page 上，UI 重建后必须整体丢弃
    -- （否则会复用父级已失效的帧）
    U.dungeonListChild = nil
    U.dungeonListPool = nil
    U.dungeonListLevel = nil
    U.dungeonDetailChild = nil
    U.dungeonDetailHero = nil
    U.dungeonDetailPool = nil
    U.dungeonDetailNote = nil
    U.dungeonDetailCur = nil          -- 详情当前副本（筛选切换后要按它重渲染）
    U.dungeonFilterBtns = nil         -- 掉落筛选行的按钮，同样挂在旧 page 上
    U.dungeonDetailTipZone = nil      -- 标题说明的悬停热区
    U.dungeonDetailHover = nil        -- 当前悬停的掉落行（物品数据到货后重刷提示框用）
    -- 任务页的常驻资源，与掉落页同理：挂在旧 page 上，UI 重建后必须整体丢弃
    U.dungeonQuestScroll = nil
    U.dungeonQuestChild = nil
    U.dungeonQuestPool = nil
    U.dungeonQuestSum = nil
    U.dungeonQuestNote = nil
    U.dungeonQuestHover = nil
    U.dungeonTabBtns = nil
    U.dungeonQDet = nil              -- 右列详情面板与它的池，同掉落页纪律整体丢弃
    U.dungeonQDetChild = nil
    U.dungeonQDetPool = nil
    U.dungeonQDetName = nil
    U.dungeonQDetSt = nil
    U.dungeonQuestSel = nil          -- 选中行随页面重建清空（新页面自动选第一行）
    U.dungeonQSide = nil             -- 阵营档回自动：重新按当前角色阵营勾选
    -- 子视图默认「列表」（公测定：打开即见副本卡墙，详情由点击进入）
    U.dungeonView = (DB().dungeonView == "overview") and "overview" or "list"
    -- 掉落筛选默认「全部」，存档里记住上次选择（RenderDungeonLoot 会自动纠正失效档位）
    U.dungeonFilter = DB().dungeonFilter or "all"
    -- 任务档的筛选（未完成 / 已完成）；页签默认「掉落」
    U.dungeonQFilter = DB().dungeonQuestFilter or "all"
    U.dungeonTab = (DB().dungeonTab == "quest") and "quest" or "loot"
    U.sourceCredits = {}

    BuildSubTabs()

    -- 数据来源条目：贴面板右下角
    MakeSourceCredit(panel, L["数据来源：wowhead"], "https://www.wowhead.com/forever")

    U:SwitchSub("Dungeons")
    -- 构建末尾才置位：中途报错时保持未构建态，下次显示可重建
    U.building = false
    U.built = true
end

function U:Refresh()
    if not U.built then return end
    self:UpdateDungeons()
end

-------------------- 生命周期 --------------------
ns.Init(function()
    local frame = ns.TalentSimFrame
    if not frame then return end
    frame:SetScript("OnShow", function()
        FONT_BASE = FONT_BASE or ns.FONT
        if not U.built then
            U.building = false -- 允许重试：构建失败不留死状态
            local ok, err = xpcall(U.Build, function(e)
                -- 错误瞬间抓真实堆栈（pcall 只剩消息，定位不到行）
                return tostring(e) .. "\\n" .. debugstack(2, 40)
            end, U)
            if not ok then
                U.building = false
                U.built = false
                print("|cff46bf72[无限副本手册] 界面构建出错：|r" .. tostring(err))
                return
            end
        end
        -- 每次开窗都按当下等级重算分组（否则会停在旧值）
        U:UpdateActiveSub()
    end)
    frame:SetScript("OnHide", function()
        GameTooltip:Hide()
        -- 一并清掉 hover 记录：窗口隐藏期间鼠标不会触发 OnLeave，
        -- 留着会在下次刷新时误重弹提示框
        U.dungeonDetailHover, U.dungeonQuestHover = nil, nil
    end)
end)
'''

def crlf(s):
    """把手写字面量的换行统一成 CRLF（本文件必须全 CRLF，裸 LF 会在泰坦上出问题）"""
    return s.replace(CRLF, '\n').replace('\n', CRLF)


parts = [
    crlf(HEAD),
    ishui, CRLF, CRLF,
    seg(*SEG_MAKEFS), CRLF, CRLF,
    seg(*SEG_NEWBUTTON), CRLF, CRLF,
    seg(*SEG_MAKEOUTLINE), CRLF, CRLF,
    seg(*SEG_SETOUTLINE), CRLF, CRLF,
    seg(*SEG_SETTIP), CRLF, CRLF,
    seg(*SEG_ENSURE), CRLF,
    module,
    crlf(TAIL),
]
out = ''.join(parts)

# ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 10 ──────────────────────────────
# 用户 2026-09-23：「副本」→「5人本」，右侧加「团本」；胶囊行整体往上移 15；
# 随后追加「胶囊按钮往下移动 5」→ 净上移量 DG.CAPSULE_LIFT = 10。
# 已与用户确认：「团本」= **空态骨架**（团本数据未收录），但要**能切换**。
#
# ⚠️ 这几处目标分散在三个不同的拼装件里（ENSURE 段 / module 段 / TAIL 手写字面量），
#    逐段去改容易漏；故统一在**组装之后**对整份 out 打一次补丁，
#    每条锚点用 count == 1 兜底唯一性（多命中/零命中都直接 die，不静默产出）。
#
# ★ 设计要点（改之前先读）：
#   · 两颗胶囊**等宽**（DG.CAPSULE_W = 82，与原「副本」同宽）：分段控件滑块的宽度取自
#     按钮宽（ctrl:AttachButtons 按 bt:GetWidth() 累加偏移），不等宽会跳形。
#   · 上移只动 host 的 y 偏移（`-ROW_SUB` → `DG.CAPSULE_LIFT - ROW_SUB`）。
#     host 只给一个 TOP 锚点 → 整行自动水平居中，与主窗左侧标题横向不交叠。
#   · U.raidPage 是**常驻**空态帧，在 U:Build() 里一次建好（不切页时懒建）——
#     harness 有「渲染路径零新建帧 / 首屏恰好新建 N 帧」的不变量，首屏之后不得再建帧。
#   · 存档 `subTab` 从「写了没人读」变成真的会用（开窗沿用上次那颗）。
def _p(*lines):
    """把若干行拼成 CRLF 文本（out 是纯 CRLF，锚点必须带 CRLF 才命中）"""
    return CRLF.join(lines)


CAPSULE_PATCHES = [
    (
        _p('    -- hui：顶胶囊 -6.25..-26.25（2026-09-23 整行上移 10px → +3.75..-16.25）；classic：左上描边按钮 -36..-64，内容一律下移让位'),
        _p('    -- hui：顶胶囊 -6.25..-26.25；classic：左上描边按钮 -36..-64，内容一律下移让位。',
           '    -- ★ 2026-09-23 起顶栏胶囊改为「5人本 / 团本」两颗并整体上移 DG.CAPSULE_LIFT(=10)：',
           '    --   胶囊会有 10px 探出本面板上边缘（用户指定，设计如此）；本面板位置不动。'),
        '内容面板锚点注释',
    ),
    (
        _p('-------------------- 头部控件 --------------------',
           '-- 上游顶栏是 7 个页签里排第 2 的那颗「副本」胶囊；本插件只有一页，',
           '-- 保留同一颗（同宽 82 / 同高 20 / 同位置：锚在 panel 顶、ROW_SUB=0），右侧留白。',
           '-- ⚠️ 删掉顶栏会让正文上移 → 与上游不再逐像素一致，故必须保留这颗胶囊。',
           'local function BuildSubTabs()',
           '    local defs = {',
           '        { key = "Dungeons", text = L["副本"], width = 82 },',
           '    }'),
        _p('-------------------- 头部控件 --------------------',
           '-- 顶栏胶囊行 = 两颗：「5人本」/「团本」（用户 2026-09-23 指定）。',
           '-- 本插件只保留这一行，其余位置留白。',
           '-- ⚠️ 删掉顶栏会让正文上移，故必须保留。',
           '-- ★ 两颗**等宽**（与原「副本」同宽）：分段控件的滑块宽度按按钮宽取，等宽才不跳形。',
           'DG.CAPSULE_LIFT = 10     -- 胶囊行整体自 panel 顶边上移的像素（用户 2026-09-23：「往上移 15」→「往下移动 5」→ 净 10）',
           'DG.CAPSULE_W = 82        -- 单颗胶囊宽',
           'local function BuildSubTabs()',
           '    local defs = {',
           '        { key = "Dungeons", text = L["5人本"], width = DG.CAPSULE_W },',
           '        { key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W },',
           '    }'),
        '顶栏胶囊 defs（两颗）',
    ),
    (
        _p('    local host = CreateFrame("Frame", nil, U.panel)',
           '    host:SetSize(totalW, BTN_H)',
           '    host:SetPoint("TOP", U.panel, "TOP", 0, -ROW_SUB)'),
        _p('    local host = CreateFrame("Frame", nil, U.panel)',
           '    host:SetSize(totalW, BTN_H)',
           '    -- ★ 上移 DG.CAPSULE_LIFT：胶囊 TOP 落在 panel 顶边**之上** 10px（y = +10），',
           '    --   本体 10~-10；hui 分段控件轨道再上下各外扩 2px → 整行约 +12~-12（panel 顶边记 0）。',
           '    --   横向仍是整行居中：host 只给一个 TOP 锚点 → 自动水平居中（主窗中线 ±总宽/2），',
           '    --   与左侧标题（主窗 TOPLEFT 18,-14）横向不交叠。',
           '    host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)'),
        'host 上移 10',
    ),
    (
        _p('    -- 子页签行紧跟在顶部胶囊行之下。实测面板纵向坐标（截图逐像素量得）：',
           '    --   胶囊本体原是 y = 0~-20（ROW_SUB=0、BTN_H=20），hui 轨道上下各外扩 2px → +2~-22，底边约 y = -22；',
           '    --   ★ 2026-09-23 胶囊行整体上移 CAPSULE_LIFT(=10) → 整行约 +12~-12，底边约 y = -12。',
           '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由约 8px 变成约 18px（子页签行本身不动）。',
           '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。',
           '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 12；本页仍取 30。'),
        _p('    -- 子页签行紧跟在顶部胶囊行之下。实测面板纵向坐标（截图逐像素量得）：',
           '    --   胶囊本体原是 y = 0~-20（ROW_SUB=0、BTN_H=20），hui 轨道上下各外扩 2px → +2~-22，',
           '    --   选中滑块高 22、底边约 y = -22；',
           '    --   ★ 2026-09-23 用户要求胶囊行整体上移 DG.CAPSULE_LIFT(=10) → 整行约 +12~-12。',
           '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由原约 8px 变成约 18px。',
           '    --   ⚠️ 用户只要求挪胶囊：子页签行保持原值 30 不动（要收拢就同步减小 SUBTAB_Y）。',
           '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区（用户截图指出）。',
           '    -- ⚠️ 胶囊底边上移后，SUBTAB_Y 可用的最小间隔从 23 降到约 12；本页仍取 30。'),
        'SUBTAB_Y 注释',
    ),
    (
        _p('-------------------- 子页切换 --------------------',
           '-- 上游有 7 个分支；本插件只有副本一页，故恒等于「显示副本页 + 构建 + 刷新」。',
           '-- 页面互斥的 SetShown 逻辑不再需要（没有第二页），但切页仍走同一入口，',
           '-- 以便 build 中断后重入时逻辑与上游一致。',
           '-- 参数保留是为与上游调用点同形（BuildSubTabs 的 OnClick 传 tab.key），值被忽略。',
           'function U:SwitchSub(_key)',
           '    local key = "Dungeons"',
           '    U.curSub = key',
           '    DB().subTab = key',
           '    if U.dungeonPage then U.dungeonPage:SetShown(true) end',
           '    DG.BuildDungeons()',
           '    U:UpdateDungeons()',
           '    for _, tab in ipairs(U.subTabs or {}) do',
           '        local selected = (tab.key == key)',
           '        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end',
           '        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))',
           '    end',
           'end'),
        _p('-------------------- 子页切换 --------------------',
           '-- 两颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本），其余一律按 5人本处理。',
           '-- 页面互斥走 SetShown（两页都是 panel 的常驻子帧，只切显隐、不重建）；',
           '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
           '-- ★「团本」目前是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
           '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
           'function U:SwitchSub(key)',
           '    local k = (key == "Raids") and "Raids" or "Dungeons"',
           '    U.curSub = k',
           '    DB().subTab = k',
           '    local isRaid = (k == "Raids")',
           '    if U.dungeonPage then U.dungeonPage:SetShown(not isRaid) end',
           '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
           '    if not isRaid then',
           '        DG.BuildDungeons()',
           '        U:UpdateDungeons()',
           '    end',
           '    for _, tab in ipairs(U.subTabs or {}) do',
           '        local selected = (tab.key == k)',
           '        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end',
           '        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))',
           '    end',
           'end'),
        'SwitchSub 按 key 分流',
    ),
    (
        _p('-- 刷新当前所在的子页。上游此处**没有** Dungeons 分支（副本内容与职业无关，',
           '-- 作者当初未列入），后果是关窗再开沿用旧分组；本插件只有一个页面，恒刷新它。',
           'function U:UpdateActiveSub()',
           '    self:UpdateDungeons()',
           'end'),
        _p('-- 刷新当前所在的子页。关窗再开沿用旧分组是历史问题，本插件按当前胶囊刷新。',
           '-- ★ 团本是空态骨架、没有可刷新的内容 → 直接跳过（别对未构建的副本页调 UpdateDungeons）。',
           'function U:UpdateActiveSub()',
           '    if self.curSub ~= "Raids" then self:UpdateDungeons() end',
           'end'),
        'UpdateActiveSub 跳过团本',
    ),
    (
        _p('    U.building = true',
           '',
           '    U.curSub = "Dungeons"',
           '',
           '    local panel = EnsureContent()',
           '    -- 副本页只在所有客户端展示（经典 26 个为通用数据，9 个无限新增仅在 16001 有意义）',
           '    U.dungeonPage = CreateFrame("Frame", nil, panel)',
           '    U.dungeonPage:SetAllPoints(panel)',
           '    U.dungeonPage:Hide()'),
        _p('    U.building = true',
           '',
           '    -- 开窗落在上次那一颗胶囊上（存档 subTab；首次为 nil → 5人本）',
           '    U.curSub = (DB().subTab == "Raids") and "Raids" or "Dungeons"',
           '',
           '    local panel = EnsureContent()',
           '    -- 副本页只在所有客户端展示（经典 26 个为通用数据，9 个无限新增仅在 16001 有意义）',
           '    U.dungeonPage = CreateFrame("Frame", nil, panel)',
           '    U.dungeonPage:SetAllPoints(panel)',
           '    U.dungeonPage:Hide()',
           '',
           '    -- 团本页 = 空态骨架（boss / 掉落 / 任务均未收录）。',
           '    -- ⚠️ 必须在 Build 里一次建好，不能等切页时懒建：',
           '    --   harness 有「渲染路径零新建帧 / 首屏恰好新建 N 帧」的不变量，首屏之后不得再建帧。',
           '    --   帧本身没有贴图与背景（不遮任何东西），默认也不抢鼠标，只承载一句居中占位文案。',
           '    U.raidPage = CreateFrame("Frame", nil, panel)',
           '    U.raidPage:SetAllPoints(panel)',
           '    U.raidPage:Hide()',
           '    U.raidNote = MakeFS(U.raidPage, 15, C_GREY, "CENTER")',
           '    U.raidNote:SetPoint("CENTER", U.raidPage, "CENTER", 0, 0)',
           '    U.raidNote:SetText(L["团本数据待补"])'),
        'Build：subTab + raidPage',
    ),
    (
        _p('    U:SwitchSub("Dungeons")'),
        _p('    U:SwitchSub(U.curSub)'),
        'Build 收尾 SwitchSub',
    ),
]

# ── 专业页（仅无限服）：把上面刚定稿的「两颗」区域就地扩成「三颗 + 独立页」──────────
# 用户 2026-09-23 定：「专业」整页只对无限服（1.60.x）开放 —— 营地系统 / Legacy 特权 /
# 1→300 路线都是无限服自己的规则，泰坦 3.80.2 端没有对应物品与专业（加载了只会画出一堆
# 查不到的空名字）。故第三颗胶囊与 U.profPage 都由 ns.IsForever 门控。
#
# ★★ 为什么**改写 CAPSULE_PATCHES 的替换文本**，而不是再对同一段打一遍补丁：
#    胶囊 defs / SwitchSub / UpdateActiveSub / Build 这四处已经由上面那批补丁重写过一次；
#    再叠一层的话，读生成物时看不出哪一层加了什么、改错了也很难定位（同一段被改两次）。
#    这里在**施加之前**把文本改好，生成物里每个区域仍然只有一次成文。
#    锚点用 `count == 1` 兜底唯一性：上游/上面那批一改，这里立刻 die 而不是静默少一颗。
def _prof(label, old, new):
    """改写 CAPSULE_PATCHES 里某一条的「替换后」文本（就地）。"""
    for i, (_o, _n, _lbl) in enumerate(CAPSULE_PATCHES):
        if _lbl != label:
            continue
        if _n.count(old) != 1:
            die('专业页补丁锚点在「%s」的替换文本里命中 %d 次（应为 1）'
                % (label, _n.count(old)))
        CAPSULE_PATCHES[i] = (_o, _n.replace(old, new), _lbl)
        return
    die('专业页补丁找不到胶囊补丁条目：%s' % label)


# ① 顶栏胶囊：三颗（无限服）/ 两颗（泰坦）
_prof('顶栏胶囊 defs（两颗）',
     _p('-- 顶栏胶囊行 = 两颗：「5人本」/「团本」（用户 2026-09-23 指定）。',
        '-- 本插件只保留这一行，其余位置留白。',
        '-- ⚠️ 删掉顶栏会让正文上移，故必须保留。',
        '-- ★ 两颗**等宽**（与原「副本」同宽）：分段控件的滑块宽度按按钮宽取，等宽才不跳形。'),
     _p('-- 顶栏胶囊行 = 三颗（无限服）/ 两颗（泰坦）：「5人本」/「团本」/「专业」。',
        '-- 本插件只保留这一行，其余位置留白。',
        '-- ⚠️ 删掉顶栏会让正文上移，故必须保留。',
        '-- ★ 各颗**等宽**（与原「副本」同宽）：分段控件的滑块宽度按按钮宽取，等宽才不跳形。'))

_prof('顶栏胶囊 defs（两颗）',
     _p('        { key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W },',
        '    }'),
     _p('        { key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W },',
        '    }',
        '    -- ★ 第三颗「专业」只在无限服（1.60.x）出现：营地系统 / Legacy 特权 / 1→300 路线',
        '    --   都是无限服自己的规则，泰坦 3.80.2 端没有对应物品与专业。',
        '    --   三颗仍等宽 → host 总宽 246、整行居中，不会与左侧标题交叠。',
        '    if ns.IsForever then',
        '        defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }',
        '    end'))

# ② SwitchSub：两颗互斥 → 三颗互斥（「专业」额外要求无限服）
_prof('SwitchSub 按 key 分流',
     _p('-- 两颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本），其余一律按 5人本处理。',
        '-- 页面互斥走 SetShown（两页都是 panel 的常驻子帧，只切显隐、不重建）；',
        '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
        '-- ★「团本」目前是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
        '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
        'function U:SwitchSub(key)',
        '    local k = (key == "Raids") and "Raids" or "Dungeons"',
        '    U.curSub = k',
        '    DB().subTab = k',
        '    local isRaid = (k == "Raids")',
        '    if U.dungeonPage then U.dungeonPage:SetShown(not isRaid) end',
        '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
        '    if not isRaid then',
        '        DG.BuildDungeons()',
        '        U:UpdateDungeons()',
        '    end'),
     _p('-- 三颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本）/ "Professions"（专业）；',
        '-- 其余一律按 5人本处理，「专业」还额外要求无限服（泰坦端根本没有这一颗）。',
        '-- 页面互斥走 SetShown（三页都是 panel 的常驻子帧，只切显隐、不重建）；',
        '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
        '-- ★「团本」是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
        '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
        '-- ★「专业」页的骨架与绘制全在 Core/ProfessionUI.lua（本文件只留这个挂钩），',
        '--   故这里只调它的 Open()；模块不存在（泰坦端 / 加载失败）时静默跳过。',
        'function U:SwitchSub(key)',
        '    local k = "Dungeons"',
        '    if key == "Raids" then',
        '        k = "Raids"',
        '    elseif key == "Professions" and ns.IsForever then',
        '        k = "Professions"',
        '    end',
        '    U.curSub = k',
        '    DB().subTab = k',
        '    local isDun, isRaid, isProf = (k == "Dungeons"), (k == "Raids"), (k == "Professions")',
        '    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end',
        '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
        '    if U.profPage then U.profPage:SetShown(isProf) end',
        '    if isDun then',
        '        DG.BuildDungeons()',
        '        U:UpdateDungeons()',
        '    elseif isProf and ns.ProfModule then',
        '        ns.ProfModule.Open()',
        '    end'))

# ③ UpdateActiveSub：团本跳过、专业刷自己那一套
_prof('UpdateActiveSub 跳过团本',
     _p('-- 刷新当前所在的子页。关窗再开沿用旧分组是历史问题，本插件按当前胶囊刷新。',
        '-- ★ 团本是空态骨架、没有可刷新的内容 → 直接跳过（别对未构建的副本页调 UpdateDungeons）。',
        'function U:UpdateActiveSub()',
        '    if self.curSub ~= "Raids" then self:UpdateDungeons() end',
        'end'),
     _p('-- 刷新当前所在的子页。关窗再开沿用旧分组是历史问题，本插件按当前胶囊刷新。',
        '-- ★ 团本是空态骨架、没有可刷新的内容 → 直接跳过（别对未构建的副本页调 UpdateDungeons）。',
        '-- ★ 专业页刷的是它自己那一套（ProfModule.Refresh），与副本页的 UpdateDungeons 无关；',
        '--   混着调会把副本页在专业态下刷出来（两页互斥就破了）。',
        'function U:UpdateActiveSub()',
        '    if self.curSub == "Raids" then return end',
        '    if self.curSub == "Professions" then',
        '        if ns.ProfModule then ns.ProfModule.Refresh() end',
        '        return',
        '    end',
        '    self:UpdateDungeons()',
        'end'))

# ④ Build：开窗落点三选一 + 专业页在首屏一次建好
_prof('Build：subTab + raidPage',
     _p('    -- 开窗落在上次那一颗胶囊上（存档 subTab；首次为 nil → 5人本）',
        '    U.curSub = (DB().subTab == "Raids") and "Raids" or "Dungeons"'),
     _p('    -- 开窗落在上次那一颗胶囊上（存档 subTab；首次为 nil → 5人本）。',
        '    -- 「专业」只在无限服存在：泰坦端存档里即便留着它也要落回 5人本。',
        '    local saved = DB().subTab',
        '    if saved == "Raids" then',
        '        U.curSub = "Raids"',
        '    elseif saved == "Professions" and ns.IsForever then',
        '        U.curSub = "Professions"',
        '    else',
        '        U.curSub = "Dungeons"',
        '    end'))

_prof('Build：subTab + raidPage',
     _p('    U.raidNote:SetText(L["团本数据待补"])'),
     _p('    U.raidNote:SetText(L["团本数据待补"])',
        '',
        '    -- 专业页（仅无限服）：页面骨架在 ProfModule.Build 里**一次建全**',
        '    --   （左导航 / 子页签 / 工具条 / 滚动容器 / 行池 / 材料芯片池 / 详情条），',
        '    --   之后切专业、切子页签、翻页都只复用池子、不建帧。',
        '    -- ⚠️ 与团本页同理：必须挂在 Build 里。若改成「切页时懒建」，',
        '    --   「渲染路径零新建帧」这条不变量当场破（harness 有这个断言）。',
        '    --   泰坦端 ns.ProfModule 为 nil（Core/ProfessionUI.lua 整体 return）→ 整段不发生。',
        '    if ns.IsForever then',
        '        U.profPage = CreateFrame("Frame", nil, panel)',
        '        U.profPage:SetAllPoints(panel)',
        '        U.profPage:Hide()',
        '        if ns.ProfModule then ns.ProfModule.Build(U.profPage) end',
        '    end'))

print('  专业页：4 处胶囊区域已就地扩成三颗 + 独立页')

# ── 探索页（仅无限服，2026-09-24 用户定）：顶栏第四颗胶囊「探索」+ 独立页 ──────────
# 页面骨架与绘制全在 Core/ExploreUI.lua（手写骨架件），本文件只留挂钩：
# 胶囊 defs / SwitchSub / UpdateActiveSub / Build 各扩一路 "Explore"。
# ★ 链式补丁：锚点对准上面专业页补丁**替换后**的文本；apply 的 count==1 检查兜底。
CAPSULE_PATCHES.append((
    _p('-- 顶栏胶囊行 = 三颗（无限服）/ 两颗（泰坦）：「5人本」/「团本」/「专业」。'),
    _p('-- 顶栏胶囊行 = 四颗（无限服）/ 两颗（泰坦）：「5人本」/「团本」/「专业」/「探索」。'),
    '探索：顶栏胶囊行注释',
))
CAPSULE_PATCHES.append((
    _p('    --   三颗仍等宽 → host 总宽 246、整行居中，不会与左侧标题交叠。',
       '    if ns.IsForever then',
       '        defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }',
       '    end'),
    _p('    -- ★ 第四颗「探索」同样只对无限服开放（2026-09-24 用户定）：40 本书收集 / 地图标记，',
       '    --   骨架与绘制全在 Core/ExploreUI.lua。',
       '    --   四颗仍等宽 → host 总宽 328、整行居中，不会与左侧标题交叠。',
       '    if ns.IsForever then',
       '        defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }',
       '        defs[#defs + 1] = { key = "Explore", text = L["探索"], width = DG.CAPSULE_W }',
       '    end'),
    '探索：胶囊 defs 第四颗',
))
CAPSULE_PATCHES.append((
    _p('-- 三颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本）/ "Professions"（专业）；',
       '-- 其余一律按 5人本处理，「专业」还额外要求无限服（泰坦端根本没有这一颗）。',
       '-- 页面互斥走 SetShown（三页都是 panel 的常驻子帧，只切显隐、不重建）；',
       '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
       '-- ★「团本」是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
       '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
       '-- ★「专业」页的骨架与绘制全在 Core/ProfessionUI.lua（本文件只留这个挂钩），',
       '--   故这里只调它的 Open()；模块不存在（泰坦端 / 加载失败）时静默跳过。',
       'function U:SwitchSub(key)',
       '    local k = "Dungeons"',
       '    if key == "Raids" then',
       '        k = "Raids"',
       '    elseif key == "Professions" and ns.IsForever then',
       '        k = "Professions"',
       '    end',
       '    U.curSub = k',
       '    DB().subTab = k',
       '    local isDun, isRaid, isProf = (k == "Dungeons"), (k == "Raids"), (k == "Professions")',
       '    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end',
       '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
       '    if U.profPage then U.profPage:SetShown(isProf) end',
       '    if isDun then',
       '        DG.BuildDungeons()',
       '        U:UpdateDungeons()',
       '    elseif isProf and ns.ProfModule then',
       '        ns.ProfModule.Open()',
       '    end'),
    _p('-- 四颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本）/ "Professions"（专业）/',
       '--   "Explore"（探索）；其余一律按 5人本处理，后两颗还额外要求无限服（泰坦端没有）。',
       '-- 页面互斥走 SetShown（四页都是 panel 的常驻子帧，只切显隐、不重建）；',
       '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
       '-- ★「团本」是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
       '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
       '-- ★「专业」页的骨架与绘制全在 Core/ProfessionUI.lua（本文件只留这个挂钩），',
       '--   故这里只调它的 Open()；模块不存在（泰坦端 / 加载失败）时静默跳过。',
       '-- ★「探索」页同理挂在 Core/ExploreUI.lua（2026-09-24 加）。',
       'function U:SwitchSub(key)',
       '    local k = "Dungeons"',
       '    if key == "Raids" then',
       '        k = "Raids"',
       '    elseif key == "Professions" and ns.IsForever then',
       '        k = "Professions"',
       '    elseif key == "Explore" and ns.IsForever then',
       '        k = "Explore"',
       '    end',
       '    U.curSub = k',
       '    DB().subTab = k',
       '    local isDun, isRaid, isProf, isExpl = (k == "Dungeons"), (k == "Raids"), (k == "Professions"), (k == "Explore")',
       '    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end',
       '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
       '    if U.profPage then U.profPage:SetShown(isProf) end',
       '    if U.explorePage then U.explorePage:SetShown(isExpl) end',
       '    if isDun then',
       '        DG.BuildDungeons()',
       '        U:UpdateDungeons()',
       '    elseif isProf and ns.ProfModule then',
       '        ns.ProfModule.Open()',
       '    elseif isExpl and ns.ExploreModule then',
       '        ns.ExploreModule.Open()',
       '    end'),
    '探索：SwitchSub 四颗互斥',
))
CAPSULE_PATCHES.append((
    _p('    if self.curSub == "Professions" then',
       '        if ns.ProfModule then ns.ProfModule.Refresh() end',
       '        return',
       '    end',
       '    self:UpdateDungeons()',
       'end'),
    _p('    if self.curSub == "Professions" then',
       '        if ns.ProfModule then ns.ProfModule.Refresh() end',
       '        return',
       '    end',
       '    if self.curSub == "Explore" then',
       '        if ns.ExploreModule then ns.ExploreModule.Refresh() end',
       '        return',
       '    end',
       '    self:UpdateDungeons()',
       'end'),
    '探索：UpdateActiveSub 分支',
))
CAPSULE_PATCHES.append((
    _p('    elseif saved == "Professions" and ns.IsForever then',
       '        U.curSub = "Professions"',
       '    else'),
    _p('    elseif saved == "Professions" and ns.IsForever then',
       '        U.curSub = "Professions"',
       '    elseif saved == "Explore" and ns.IsForever then',
       '        U.curSub = "Explore"',
       '    else'),
    '探索：Build 开窗落点',
))
CAPSULE_PATCHES.append((
    _p('    if ns.IsForever then',
       '        U.profPage = CreateFrame("Frame", nil, panel)',
       '        U.profPage:SetAllPoints(panel)',
       '        U.profPage:Hide()',
       '        if ns.ProfModule then ns.ProfModule.Build(U.profPage) end',
       '    end'),
    _p('    if ns.IsForever then',
       '        U.profPage = CreateFrame("Frame", nil, panel)',
       '        U.profPage:SetAllPoints(panel)',
       '        U.profPage:Hide()',
       '        if ns.ProfModule then ns.ProfModule.Build(U.profPage) end',
       '        -- 探索页（仅无限服）：骨架与绘制全在 Core/ExploreUI.lua，一次建全（2026-09-24 加）。',
       '        U.explorePage = CreateFrame("Frame", nil, panel)',
       '        U.explorePage:SetAllPoints(panel)',
       '        U.explorePage:Hide()',
       '        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end',
       '    end'),
    '探索：Build 挂 explorePage',
))

# ── BIS配装页（仅无限服，2026-09-25 用户定）：顶栏第五颗胶囊「BIS配装」+ 独立页 ────
# 页面骨架与绘制全在 Core/BisUI.lua（手写骨架件，ns.BisModule），
# 数据在 Core/Data/Data_BIS.lua（_temp/fc_bis.py 生成）。本文件只留挂钩：
# 胶囊 defs / SwitchSub / UpdateActiveSub / Build 开窗落点 / Build 挂页 各扩一路 "Bis"。
# ★ 链式补丁：锚点对准上面探索补丁**替换后**的文本；apply 的 count==1 检查兜底。
CAPSULE_PATCHES.append((
    _p('-- 顶栏胶囊行 = 四颗（无限服）/ 两颗（泰坦）：「5人本」/「团本」/「专业」/「探索」。'),
    _p('-- 顶栏胶囊行 = 五颗（无限服）/ 两颗（泰坦）：「5人本」/「团本」/「专业」/「探索」/',
       '--   「BIS配装」。'),
    'BIS：顶栏胶囊行注释',
))
CAPSULE_PATCHES.append((
    _p('    -- ★ 第四颗「探索」同样只对无限服开放（2026-09-24 用户定）：40 本书收集 / 地图标记，',
       '    --   骨架与绘制全在 Core/ExploreUI.lua。',
       '    --   四颗仍等宽 → host 总宽 328、整行居中，不会与左侧标题交叠。',
       '    if ns.IsForever then',
       '        defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }',
       '        defs[#defs + 1] = { key = "Explore", text = L["探索"], width = DG.CAPSULE_W }',
       '    end'),
    _p('    -- ★ 第四颗「探索」同样只对无限服开放（2026-09-24 用户定）：40 本书收集 / 地图标记，',
       '    --   骨架与绘制全在 Core/ExploreUI.lua。',
       '    -- ★ 第五颗「BIS配装」同样只对无限服开放（2026-09-25 用户定）：20级各部位最佳',
       '    --   装备 / 换装 / 方案管理，骨架与绘制全在 Core/BisUI.lua。',
       '    --   五颗仍等宽 → host 总宽 410、整行居中，不会与左侧标题交叠。',
       '    if ns.IsForever then',
       '        defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }',
       '        defs[#defs + 1] = { key = "Explore", text = L["探索"], width = DG.CAPSULE_W }',
       '        defs[#defs + 1] = { key = "Bis", text = L["BIS配装"], width = DG.CAPSULE_W }',
       '    end'),
    'BIS：胶囊 defs 第五颗',
))
CAPSULE_PATCHES.append((
    _p('-- 四颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本）/ "Professions"（专业）/',
       '--   "Explore"（探索）；其余一律按 5人本处理，后两颗还额外要求无限服（泰坦端没有）。',
       '-- 页面互斥走 SetShown（四页都是 panel 的常驻子帧，只切显隐、不重建）；',
       '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
       '-- ★「团本」是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
       '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
       '-- ★「专业」页的骨架与绘制全在 Core/ProfessionUI.lua（本文件只留这个挂钩），',
       '--   故这里只调它的 Open()；模块不存在（泰坦端 / 加载失败）时静默跳过。',
       '-- ★「探索」页同理挂在 Core/ExploreUI.lua（2026-09-24 加）。',
       'function U:SwitchSub(key)',
       '    local k = "Dungeons"',
       '    if key == "Raids" then',
       '        k = "Raids"',
       '    elseif key == "Professions" and ns.IsForever then',
       '        k = "Professions"',
       '    elseif key == "Explore" and ns.IsForever then',
       '        k = "Explore"',
       '    end',
       '    U.curSub = k',
       '    DB().subTab = k',
       '    local isDun, isRaid, isProf, isExpl = (k == "Dungeons"), (k == "Raids"), (k == "Professions"), (k == "Explore")',
       '    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end',
       '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
       '    if U.profPage then U.profPage:SetShown(isProf) end',
       '    if U.explorePage then U.explorePage:SetShown(isExpl) end',
       '    if isDun then',
       '        DG.BuildDungeons()',
       '        U:UpdateDungeons()',
       '    elseif isProf and ns.ProfModule then',
       '        ns.ProfModule.Open()',
       '    elseif isExpl and ns.ExploreModule then',
       '        ns.ExploreModule.Open()',
       '    end'),
    _p('-- 五颗胶囊互斥：key 只认 "Dungeons"（5人本）/ "Raids"（团本）/ "Professions"（专业）/',
       '--   "Explore"（探索）/ "Bis"（BIS配装）；其余一律按 5人本处理，后三颗还额外要求',
       '--   无限服（泰坦端没有）。',
       '-- 页面互斥走 SetShown（五页都是 panel 的常驻子帧，只切显隐、不重建）；',
       '-- 选中态同时写进存档（DB().subTab），下次开窗沿用上次那一颗。',
       '-- ★「团本」是**空态骨架**（用户 2026-09-23 定：先做骨架、数据待收录）：',
       '--   只切显隐，**不做任何构建与刷新调用** —— raidPage 没有内容可建可刷。',
       '-- ★「专业」页的骨架与绘制全在 Core/ProfessionUI.lua（本文件只留这个挂钩），',
       '--   故这里只调它的 Open()；模块不存在（泰坦端 / 加载失败）时静默跳过。',
       '-- ★「探索」页同理挂在 Core/ExploreUI.lua（2026-09-24 加）。',
       '-- ★「BIS配装」页同理挂在 Core/BisUI.lua（2026-09-25 加）。',
       'function U:SwitchSub(key)',
       '    local k = "Dungeons"',
       '    if key == "Raids" then',
       '        k = "Raids"',
       '    elseif key == "Professions" and ns.IsForever then',
       '        k = "Professions"',
       '    elseif key == "Explore" and ns.IsForever then',
       '        k = "Explore"',
       '    elseif key == "Bis" and ns.IsForever then',
       '        k = "Bis"',
       '    end',
       '    U.curSub = k',
       '    DB().subTab = k',
       '    local isDun, isRaid, isProf, isExpl, isBis = (k == "Dungeons"), (k == "Raids"), (k == "Professions"), (k == "Explore"), (k == "Bis")',
       '    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end',
       '    if U.raidPage then U.raidPage:SetShown(isRaid) end',
       '    if U.profPage then U.profPage:SetShown(isProf) end',
       '    if U.explorePage then U.explorePage:SetShown(isExpl) end',
       '    if U.bisPage then U.bisPage:SetShown(isBis) end',
       '    if isDun then',
       '        DG.BuildDungeons()',
       '        U:UpdateDungeons()',
       '    elseif isProf and ns.ProfModule then',
       '        ns.ProfModule.Open()',
       '    elseif isExpl and ns.ExploreModule then',
       '        ns.ExploreModule.Open()',
       '    elseif isBis and ns.BisModule then',
       '        ns.BisModule.Open()',
       '    end'),
    'BIS：SwitchSub 五颗互斥',
))
CAPSULE_PATCHES.append((
    _p('    if self.curSub == "Professions" then',
       '        if ns.ProfModule then ns.ProfModule.Refresh() end',
       '        return',
       '    end',
       '    if self.curSub == "Explore" then',
       '        if ns.ExploreModule then ns.ExploreModule.Refresh() end',
       '        return',
       '    end',
       '    self:UpdateDungeons()',
       'end'),
    _p('    if self.curSub == "Professions" then',
       '        if ns.ProfModule then ns.ProfModule.Refresh() end',
       '        return',
       '    end',
       '    if self.curSub == "Explore" then',
       '        if ns.ExploreModule then ns.ExploreModule.Refresh() end',
       '        return',
       '    end',
       '    if self.curSub == "Bis" then',
       '        if ns.BisModule then ns.BisModule.Refresh() end',
       '        return',
       '    end',
       '    self:UpdateDungeons()',
       'end'),
    'BIS：UpdateActiveSub 分支',
))
CAPSULE_PATCHES.append((
    _p('    elseif saved == "Professions" and ns.IsForever then',
       '        U.curSub = "Professions"',
       '    elseif saved == "Explore" and ns.IsForever then',
       '        U.curSub = "Explore"',
       '    else'),
    _p('    elseif saved == "Professions" and ns.IsForever then',
       '        U.curSub = "Professions"',
       '    elseif saved == "Explore" and ns.IsForever then',
       '        U.curSub = "Explore"',
       '    elseif saved == "Bis" and ns.IsForever then',
       '        U.curSub = "Bis"',
       '    else'),
    'BIS：Build 开窗落点',
))
CAPSULE_PATCHES.append((
    _p('        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end',
       '    end'),
    _p('        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end',
       '        -- BIS配装页（仅无限服）：骨架与绘制全在 Core/BisUI.lua，一次建全（2026-09-25 加）。',
       '        U.bisPage = CreateFrame("Frame", nil, panel)',
       '        U.bisPage:SetAllPoints(panel)',
       '        U.bisPage:Hide()',
       '        if ns.BisModule then ns.BisModule.Build(U.bisPage) end',
       '    end'),
    'BIS：Build 挂 bisPage',
))

# ── 副本列表卡：左上角副本名 / 左下角「等级 · BOSS n」字号各 +2（2026-09-24 用户要求）──
# 用户原话：「五人本列表页面每个副本左上角和左下角的介绍字体都需要放大一些，现在有点太小了」。
# ★ 只改数字、不增删行：产物 DungeonUI.lua 的行号结构保持逐行稳定（说明写在这里，不落进产物）。
#   12pt / 10pt → 16pt / 12pt：卡 175x58 内两行合计 28px，仍余 30px 空隙；
#   卡宽 175 - 左右内边距 16 - 「新」标记 20 = 139px，最长副本名（4 个汉字 ≈ 56px）远未触边。
#   层级也随之理顺：副本名 14 > 副行 12 > 「新」标记 11 / 分组说明 11。
CAPSULE_PATCHES.append((
    _p('    card.name = MakeFS(card, 12, C_WHITE, "LEFT")',
       '    card.name:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -5)',
       '    card.name:SetWordWrap(false)',
       '    card.meta = MakeFS(card, 10, C_GREY, "LEFT")',
       '    card.meta:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 8, 5)'),
    _p('    card.name = MakeFS(card, 16, C_WHITE, "LEFT")',
       '    card.name:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -5)',
       '    card.name:SetWordWrap(false)',
       '    card.meta = MakeFS(card, 12, C_GREY, "LEFT")',
       '    card.meta:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 8, 5)',
       '    -- hui 主题 FontFlags 恒返回 ""（无描边），副行压在场景图上发虚 → 补 1px 阴影当细描边，',
       '    --   与详情页标题 dungeonDetailTitle/Meta 的 SetShadowOffset(1, -1) 同款。',
       '    card.meta:SetShadowColor(0, 0, 0, 1)',
       '    card.meta:SetShadowOffset(1, -1)'),
    '副本卡字号 12/10 → 16/12 + meta 细描边',
))

# ── 任务目标 / 任务注释 / 收获 / 前导链备注：高度改客户端实测（2026-09-24 用户要求）──────────
# 用户原话：「任务目标和任务注释下方都有很多空行，把这些空行都删了」。
# 根因：高度按 #txt 字节估行数（#txt 对中文是 3 字节/字）→ 估出行数 ≈ 实际换行的 3 倍
#       → 文本下方大片空行。修法：takeTxt 建立时已 SetWidth(detW-8)（按宽换行），
#       直接用 GetStringHeight() 实测换行总高，一行不多一行不少。
# ★ 三处同型一起修（目标/注释、收获、前导链备注）；只换实现、不增删行，行号结构保持稳定。
CAPSULE_PATCHES.append((
    _p('            -- 高度按估算行数：串长 / 每行约 (detW-8)/13 个字，向上取整',
       '            local perLine = math.max(8, math.floor((detW - 8) / 13))',
       '            local lines = math.ceil(#txt / perLine)',
       '            put(t, lines * 18 + 4)'),
    _p('            -- 高度按客户端实测换行（GetStringHeight）：按字节估行数会把中文（3 字节/字）虚胖约 3 倍',
       '            -- ★ 必须判型：离线桩里 GetStringHeight 回假对象，`or 18` 兜不住（同既有 GetStringWidth 判型先例）',
       '            local h = t:GetStringHeight()',
       '            put(t, (type(h) == "number" and h or 18) + 4)'),
    '任务目标/任务注释高度改实测',
))
CAPSULE_PATCHES.append((
    _p('            local txt = table.concat(seg, " · ")',
       '            local t = takeTxt()',
       '            t:SetText(txt)',
       '            t:SetTextColor(Unpack(C_TEXT))',
       '            local perLine = math.max(8, math.floor((detW - 8) / 13))',
       '            local lines = math.ceil(#txt / perLine)',
       '            put(t, lines * 18 + 4)'),
    _p('            local txt = table.concat(seg, " · ")',
       '            local t = takeTxt()',
       '            t:SetText(txt)',
       '            t:SetTextColor(Unpack(C_TEXT))',
       '            -- 高度实测（GetStringHeight）替代字节估算（中文 3 字节/字虚胖约 3 倍）；判型兜桩假对象',
       '            local h = t:GetStringHeight()',
       '            put(t, (type(h) == "number" and h or 18) + 4)'),
    '收获行高度改实测',
))

for old, new, label in CAPSULE_PATCHES:
    n = out.count(old)
    if n != 1:
        die('胶囊补丁锚点命中 %d 次（应为 1）：%s' % (n, label))
    out = out.replace(old, new)

# ── 物品卡的 Shift+点击：把物品链接送进聊天输入框（2026-09-23 用户要求）──────────
# 用户原话：「物品需要支持 Shift 点击，然后能发送到聊天输入框」。
# 这是本插件自己的交互功能 → 走组装后补丁落地（源文件段区间是硬编码行号，
# 增删一行就整段错位，所以那边一个字都不动）。
#
# ★ 设计要点（改之前先读）：
#   · 掉落卡片与任务奖励芯片原本都是 **Frame**。Frame 不支持 OnClick —— 实测
#     "script type not supported"（任务行踩过这个坑、当时改成 Button 才好），
#     故两处一并改 Button + OnClick（与任务行同款，实机已验证可用）。
#   · 逻辑全部收进 DG.ItemShiftClick / DG.InsertItemLink / DG.ItemLink 三个函数，
#     控件回调只做转发 —— 断言切片才能钉在函数体里（同名串散在回调里会白测）。
#   · 链接优先客户端自己的 hyperlink；物品数据懒加载、尚未到货时它给 nil，此时
#     自造 item:<id> 兜底 —— 绝不静默失败（与「取数只认客户端」的口径不冲突：
#     兜底用的就是客户端给的 itemID 本身）。
_ITEM_FUNCS = _p(
    '',
    '-- 物品链接：优先客户端自己的 hyperlink（GetItemInfo 的第 2 个返回值）。',
    '-- 客户端物品数据是**懒加载**的：还没拉下来时它给 nil，但不代表客户端不认这件 ——',
    '-- 此时自造等价的 item string 兜底（少几个后缀字段不影响解析，收端仍按 itemID 取）。',
    'function DG.ItemLink(id)',
    '    if id == nil then return nil end',
    '    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)',
    '    if type(fn) == "function" then',
    '        local ok, _, link = pcall(fn, id)',
    '        if ok and type(link) == "string" and link ~= "" then return link end',
    '    end',
    '    return "item:" .. tostring(id) .. ":0:0:0:0:0:0:0"',
    'end',
    '',
    '-- 把物品链接送进聊天输入框，两路：',
    '--   ① 聊天框已经开着 → 插到光标处（不覆盖已输入的草稿）；',
    '--   ② 还没开 → 直接开框并把链接塞进去（等价于游戏内 Shift+点击物品的行为）。',
    'function DG.InsertItemLink(id)',
    '    local link = DG.ItemLink(id)',
    '    if link == nil then return false end',
    '    if type(ChatEdit_GetActiveWindow) == "function"',
    '       and type(ChatEdit_InsertLink) == "function"',
    '       and ChatEdit_GetActiveWindow() then',
    '        ChatEdit_InsertLink(link)',
    '        return true',
    '    end',
    '    if type(ChatFrame_OpenChat) == "function" then',
    '        ChatFrame_OpenChat(link)',
    '        return true',
    '    end',
    '    return false',
    'end',
    '',
    '-- Shift+左键点击物品（掉落卡片 / 任务奖励芯片共用）。',
    '-- ⚠️ 非左键、未按 Shift 一律放过：不打扰原有的悬停提示与滚轮。',
    'function DG.ItemShiftClick(row, button)',
    '    if button ~= "LeftButton" then return false end',
    '    if type(IsShiftKeyDown) ~= "function" or not IsShiftKeyDown() then return false end',
    '    local it = row and row.__it',
    '    if it == nil then return false end',
    '    return DG.InsertItemLink(it[1])',
    'end',
)

_PCT_ANCHOR = _p(
    '-- 掉率文本：沿用原始口径 —— ≥10 取整，<10 保留原值（如 35 / 3.5）',
    'function DG.Pct(v)',
    '    if type(v) ~= "number" then return nil end',
    '    if v >= 10 then return format("%d%%", math.floor(v + 0.5)) end',
    '    return tostring(v) .. "%"',
    'end',
)

_CARD_CREATE_OLD = '            r = CreateFrame("Frame", nil, child, "BackdropTemplate")'
_CARD_CREATE_NEW = _p(
    '            -- Button（不是 Frame）：Frame 不支持 OnClick，挂上去实机直接',
    '            --   "script type not supported"（任务行踩过这个坑才改的 Button）。',
    '            r = CreateFrame("Button", nil, child, "BackdropTemplate")',
)

_CARD_LEAVE_OLD = _p(
    '            r:SetScript("OnLeave", function(self)',
    '                if U.dungeonDetailHover == self then U.dungeonDetailHover = nil end',
    '                self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)',
    '                self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)',
    '                GameTooltip:Hide()',
    '            end)',
)
_CARD_LEAVE_NEW = _CARD_LEAVE_OLD + CRLF + _p(
    '            -- Shift+左键点击：把物品链接发到聊天输入框（逻辑全在 DG.ItemShiftClick）',
    '            r:SetScript("OnClick", function(self, button) DG.ItemShiftClick(self, button) end)',
)

_CHIP_CREATE_OLD = '            r = CreateFrame("Frame", nil, child)'
_CHIP_CREATE_NEW = _p(
    '            -- Button（不是 Frame）：同掉落卡，Frame 不支持 OnClick。',
    '            r = CreateFrame("Button", nil, child)',
)

_CHIP_LEAVE_OLD = _p(
    '            r:SetScript("OnLeave", function(self) GameTooltip:Hide() end)',
    '            r.icon = r:CreateTexture(nil, "ARTWORK")',
)
_CHIP_LEAVE_NEW = _p(
    '            r:SetScript("OnLeave", function(self) GameTooltip:Hide() end)',
    '            -- Shift+左键点击：奖励物品同样能发链接（与掉落卡片同一入口）',
    '            r:SetScript("OnClick", function(self, button) DG.ItemShiftClick(self, button) end)',
    '            r.icon = r:CreateTexture(nil, "ARTWORK")',
)

ITEM_CLICK_PATCHES = [
    (_PCT_ANCHOR, _PCT_ANCHOR + CRLF + _ITEM_FUNCS, '物品链接三函数'),
    (_CARD_CREATE_OLD, _CARD_CREATE_NEW, '掉落卡片改 Button'),
    (_CARD_LEAVE_OLD, _CARD_LEAVE_NEW, '掉落卡片挂 OnClick'),
    (_CHIP_CREATE_OLD, _CHIP_CREATE_NEW, '奖励芯片改 Button'),
    (_CHIP_LEAVE_OLD, _CHIP_LEAVE_NEW, '奖励芯片挂 OnClick'),
]
for old, new, label in ITEM_CLICK_PATCHES:
    m = out.count(old)
    if m != 1:
        die('物品卡补丁锚点命中 %d 次（应为 1）：%s' % (m, label))
    out = out.replace(old, new)
print('  物品卡 Shift+点击：%d 条补丁已施加' % len(ITEM_CLICK_PATCHES))

# ── 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）────────────────────
# 用户原话：「给 2040 这个前导任务需要备注一下：不需要接 2041 就可以接」。
# 2040 的直连前置写的是 2041（诺恩给的引导任务），但那个环不做也能接 2040；
# 而「前导任务」区会把它渲染成一个链节点 + 「下一步」标 → 很容易被读成「必须先接 2041」。
#
# ★ 备注数据在数据层 ns.DungeonQuestPreNote[questID]（由 _temp/sync_data.py 注入 ——
#   Data_DungeonQuests.lua 是生成物，手改会被下次同步覆盖）；这里只负责渲染。
# ★ 为什么写在链节点**下方**：备注点名的就是刚读完的那个环，脚注读法最自然，
#   也不会把链推下去。
# ★ 走 takeTxt 池、不新建帧：详情面板有「池化复用，渲染路径零新建帧」的纪律。
# ★ 独立列一条补丁表（不混进 ITEM_CLICK_PATCHES）：两件事没有共同点，
#   混在一起将来改一方会连累另一方的锚点。
_QNOTE_ANCHOR = _p(
    '                y = y - 38',
    '            end',
    '        end',
    '        y = y - 4',
    '    end',
    '',
    '    -- 后续任务：本表反查（403 条之内能链上就显示）',
)
_QNOTE_NEW = _p(
    '                y = y - 38',
    '            end',
    '        end',
    '        -- 前导链备注（数据层 ns.DungeonQuestPreNote[questID]）：链上某些环其实',
    '        -- **非必需** —— 不做那个环也能接本任务，写在链节点下方说清楚。',
    '        local pnote = ns.DungeonQuestPreNote and ns.DungeonQuestPreNote[q[1]]',
    '        if pnote then',
    '            local t = takeTxt()',
    '            t:SetText(pnote)',
    '            t:SetTextColor(Unpack(C_GREY))',
    '            local perLine = math.max(8, math.floor((detW - 8) / 13))',
    '            put(t, math.ceil(#pnote / perLine) * 18 + 2)',
    '        end',
    '        y = y - 4',
    '    end',
    '',
    '    -- 后续任务：本表反查（403 条之内能链上就显示）',
)
QUEST_NOTE_PATCHES = [
    (_QNOTE_ANCHOR, _QNOTE_NEW, '前导链备注渲染'),
]
for old, new, label in QUEST_NOTE_PATCHES:
    q = out.count(old)
    if q != 1:
        die('前导链备注补丁锚点命中 %d 次（应为 1）：%s' % (q, label))
    out = out.replace(old, new)
print('  前导链备注：%d 条补丁已施加' % len(QUEST_NOTE_PATCHES))

# ── 前导链备注高度改实测（2026-09-24，同「任务目标/注释」一批）────────────────
# ★ 必须排在 QUEST_NOTE_PATCHES 之后：pnote 块是上面那条补丁插入的，CAPSULE_PATCHES
#   阶段（上游抽取文本）还没有这段。只换实现、不增删行。
QNOTE_HEIGHT_PATCHES = [
    (
        _p('            t:SetText(pnote)',
           '            t:SetTextColor(Unpack(C_GREY))',
           '            local perLine = math.max(8, math.floor((detW - 8) / 13))',
           '            put(t, math.ceil(#pnote / perLine) * 18 + 2)'),
        _p('            t:SetText(pnote)',
           '            t:SetTextColor(Unpack(C_GREY))',
           '            local h = t:GetStringHeight()  -- 实测换行高替代字节估算（中文 3 字节/字虚胖约 3 倍）',
           '            put(t, (type(h) == "number" and h or 18) + 2)'),
        '前导链备注高度改实测',
    ),
]
for old, new, label in QNOTE_HEIGHT_PATCHES:
    q = out.count(old)
    if q != 1:
        die('备注高度补丁锚点命中 %d 次（应为 1）：%s' % (q, label))
    out = out.replace(old, new)
print('  前导链备注高度改实测：%d 条补丁已施加' % len(QNOTE_HEIGHT_PATCHES))

# ── 副本入口标记（2026-09-24 用户要求）────────────────────────────────────────
# 点副本详情页的标题 → 打开该副本入口所在地图并放下用户航点，与「点 NPC 名」同一条链路。
# 坐标表是另开的一张 ns.DungeonEntry（键 = 副本 id 字符串）：副本入口不属于任何 NPC，
# 客户端 Lua 也没有按副本 ID 查位置的口。
# 为什么走补丁而不是改既有行：相关函数由生成器整段继承，改它等于改另一个插件的同名文件；
# 这里只在段尾**追加**两个新函数，再给标题绑一次鼠标事件，不动任何既有行。
_ENT_ANCHOR = _p(
    '    GameTooltip:AddLine(L["未收录该 NPC 的地图位置"], 0.6, 0.6, 0.6)',
    '    end',
    '    GameTooltip:Show()',
    'end',
)
_ENT_NEW = _p(
    '    GameTooltip:AddLine(L["未收录该 NPC 的地图位置"], 0.6, 0.6, 0.6)',
    '    end',
    '    GameTooltip:Show()',
    'end',
    '',
    '-- 副本入口标记（2026-09-24）：点副本详情页标题 → 打开入口所在地图并放下用户航点。',
    '-- 与 NPC 标记同一条链路，坐标表换成 ns.DungeonEntry（键 = 副本 id，不是 npcID）。',
    '-- 未收录的副本（黑石山三兄弟 / 本服自制新副本）明说，不假装成功。',
    'function DG.MarkEntrance(dungeonID)',
    '    local ver = select(4, GetBuildInfo()) or 0',
    '    if ver < 16000 or ver > 16999 then',
    '        if UIErrorsFrame and UIErrorsFrame.AddMessage then',
    '            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)',
    '        end',
    '        return',
    '    end',
    '    local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]',
    '    if not loc then',
    '        if UIErrorsFrame and UIErrorsFrame.AddMessage then',
    '            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该副本的入口位置"], 1, 0.4, 0.4)',
    '        end',
    '        return',
    '    end',
    '    local mapID = loc[1]',
    '    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint',
    '        and (not C_Map.CanSetUserWaypointOnMap or C_Map.CanSetUserWaypointOnMap(mapID)) then',
    '        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, loc[2] / 100, loc[3] / 100)',
    '        -- ★ 这一行刻意压成单行：DG.MarkNPC 里有一处**逐字相同**的三行块，',
    '        --   两处完全同形会让按缩进定位的静态检查与变异锚点命中 2 次而静默失效。',
    '        if ok and pt then pcall(C_Map.SetUserWaypoint, pt) end',
    '        if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then',
    '            pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)',
    '        end',
    '    end',
    '    if C_Map and C_Map.OpenWorldMap then',
    '        pcall(C_Map.OpenWorldMap, mapID)',
    '    elseif OpenWorldMap then',
    '        pcall(OpenWorldMap, mapID)',
    '    end',
    'end',
    '',
    '-- 副本标题悬停：说明可点 + 给出收录的入口坐标（未收录明说）',
    'function DG.ShowEntranceTip(owner)',
    '    if not GameTooltip then return end',
    '    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")',
    '    GameTooltip:AddLine(L["点击：在地图上标记副本入口"], 1, 0.82, 0)',
    '    local d = U.dungeonDetailCur',
    '    local loc = d and ns.DungeonEntry and ns.DungeonEntry[d.id]',
    '    if loc then',
    '        -- 多段指引（2026-09-24 用户要求）：航点仍落主点（副本入口），指引点只在',
    '        -- 提示框里逐行列出（领主大厅：先到铁炉堡楼梯 44.2,52，再下到入口 28.2,47.7）。',
    '        local route = d and ns.DungeonEntryRoute and ns.DungeonEntryRoute[d.id]',
    '        GameTooltip:AddLine((route and (L["副本入口"] .. " ") or "") ..',
    '            format("%s %.1f, %.1f", tostring(loc[4] or ""), loc[2], loc[3]), 0.75, 0.75, 0.75)',
    '        if route then',
    '            for i = 1, #route do',
    '                local p = route[i]',
    '                GameTooltip:AddLine(tostring(p[4] or "") .. " " .. tostring(p[5] or "") .. " " ..',
    '                    format("%.1f, %.1f", p[2], p[3]), 0.6, 0.6, 0.6)',
    '            end',
    '        end',
    '    else',
    '        GameTooltip:AddLine(L["未收录该副本的入口位置"], 0.6, 0.6, 0.6)',
    '    end',
    '    GameTooltip:Show()',
    'end',
    '',
    '-- 入口点清单（2026-09-24 用户定：标题右侧芯片按钮的取数口）——',
    '-- 1 号 = 主点（副本入口，ns.DungeonEntry），2+ 号 = 多段指引点（ns.DungeonEntryRoute）。',
    '-- 返回 { { mapID=, x=, y=, label=, mapName= }, ... }（主点 label 为 nil）；未收录返回 nil。',
    'function DG.EntrancePoints(dungeonID)',
    '    local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]',
    '    if not loc then return nil end',
    '    local pts = { { mapID = loc[1], x = loc[2], y = loc[3], label = nil, mapName = loc[4] } }',
    '    local route = dungeonID and ns.DungeonEntryRoute and ns.DungeonEntryRoute[dungeonID]',
    '    if route then',
    '        for i = 1, #route do',
    '            local p = route[i]',
    '            pts[#pts + 1] = { mapID = p[1], x = p[2], y = p[3], label = p[4], mapName = p[5] }',
    '        end',
    '    end',
    '    return pts',
    'end',
    '',
    '-- 按序号标记入口点（1 = 主点 / 副本入口，2+ = 指引点）：入口芯片的点击落点。',
    '-- 链路与 MarkEntrance 相同（端号门禁 → 落航点 → 开图），正文刻意换形',
    '--（wp/p 命名、两行落点），避免与 MarkNPC / MarkEntrance 的同形块撞锚点。',
    'function DG.MarkEntranceAt(dungeonID, idx)',
    '    local ver = select(4, GetBuildInfo()) or 0',
    '    if ver < 16000 or ver > 16999 then',
    '        if UIErrorsFrame and UIErrorsFrame.AddMessage then',
    '            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)',
    '        end',
    '        return',
    '    end',
    '    local pts = DG.EntrancePoints(dungeonID)',
    '    local p = pts and pts[idx or 1]',
    '    if not p then',
    '        if UIErrorsFrame and UIErrorsFrame.AddMessage then',
    '            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该副本的入口位置"], 1, 0.4, 0.4)',
    '        end',
    '        return',
    '    end',
    '    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint',
    '        and (not C_Map.CanSetUserWaypointOnMap or C_Map.CanSetUserWaypointOnMap(p.mapID)) then',
    '        local ok, wp = pcall(UiMapPoint.CreateFromCoordinates, p.mapID, p.x / 100, p.y / 100)',
    '        if ok and wp then pcall(C_Map.SetUserWaypoint, wp) end',
    '        if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then',
    '            pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)',
    '        end',
    '    end',
    '    if C_Map and C_Map.OpenWorldMap then',
    '        pcall(C_Map.OpenWorldMap, p.mapID)',
    '    elseif OpenWorldMap then',
    '        pcall(OpenWorldMap, p.mapID)',
    '    end',
    'end',
    '',
    '-- 入口芯片悬停：点击说明 + 该点的地图名与坐标（主点标「副本入口」，指引点用自己的标签）',
    'function DG.ShowEntrancePointTip(owner, idx)',
    '    if not GameTooltip then return end',
    '    local d = U.dungeonDetailCur',
    '    local pts = d and DG.EntrancePoints(d.id)',
    '    local p = pts and pts[idx or 1]',
    '    if not p then return end',
    '    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")',
    '    GameTooltip:AddLine(L["点击：在地图上标记此点"], 1, 0.82, 0)',
    '    GameTooltip:AddLine(tostring(p.label or L["副本入口"]) .. " " .. tostring(p.mapName or "") .. " " ..',
    '        format("%.1f, %.1f", p.x, p.y), 0.75, 0.75, 0.75)',
    '    GameTooltip:Show()',
    'end',
)

_ENTBIND_ANCHOR = _p(
    '    U.dungeonDetailTitle:SetPoint("TOPLEFT", hero, "TOPLEFT", 12, -DG.HERO_TITLE_Y)',
)
_ENTBIND_NEW = _p(
    '    U.dungeonDetailTitle:SetPoint("TOPLEFT", hero, "TOPLEFT", 12, -DG.HERO_TITLE_Y)',
    '    -- 标题可点：开图放副本入口航点（仅无限服；未收录的副本点了会明说）',
    '    -- 鼠标事件绑在 FontString 自身：点击区 = 标题文字，不额外叠帧。',
    '    U.dungeonDetailTitle:EnableMouse(true)',
    '    U.dungeonDetailTitle:SetScript("OnMouseUp", function()',
    '        local dd = U.dungeonDetailCur',
    '        if dd then DG.MarkEntrance(dd.id) end',
    '    end)',
    '    U.dungeonDetailTitle:SetScript("OnEnter", function(self) DG.ShowEntranceTip(self) end)',
    '    U.dungeonDetailTitle:SetScript("OnLeave", function() GameTooltip:Hide() end)',
    '    -- 入口芯片（2026-09-24 用户定）：标题右侧一排按钮，一枚芯片 = 一个可标记的坐标点。',
    '    -- 主点 + 多段指引点（领主大厅 = 入口 + 楼梯入口）；Build 一次建池（3 枚封顶），',
    '    -- 显示 / 文案 / 位置由 ShowDungeonDetail 摆 —— 保住「渲染路径零新建帧」不变量。',
    '    -- 必须是 Button（项目口径）；显式抬一层：tipZone 与 hero 同级且创建更晚。',
    '    U.dungeonEntChips = {}',
    '    for i = 1, 3 do',
    '        local chip = NewButton(detail, "", 70, 20, 12)',
    '        chip:SetFrameLevel(hero:GetFrameLevel() + 1)',
    '        chip.__entIdx = i',
    '        chip:SetScript("OnClick", function(self)',
    '            local dd = U.dungeonDetailCur',
    '            if dd then DG.MarkEntranceAt(dd.id, self.__entIdx) end',
    '        end)',
    '        chip:SetScript("OnEnter", function(self) DG.ShowEntrancePointTip(self, self.__entIdx) end)',
    '        chip:SetScript("OnLeave", function() GameTooltip:Hide() end)',
    '        chip:Hide()',
    '        U.dungeonEntChips[i] = chip',
    '    end',
)
ENTRANCE_PATCHES = [
    (_ENT_ANCHOR, _ENT_NEW, '副本入口标记函数'),
    (_ENTBIND_ANCHOR, _ENTBIND_NEW, '副本标题点击绑定'),
]
for old, new, label in ENTRANCE_PATCHES:
    q = out.count(old)
    if q != 1:
        die('副本入口补丁锚点命中 %d 次（应为 1）：%s' % (q, label))
    out = out.replace(old, new)
print('  副本入口标记：%d 条补丁已施加' % len(ENTRANCE_PATCHES))

# ── 入口芯片排布（2026-09-24 用户定）：ShowDungeonDetail 里按入口点清单摆芯片 ─────
# 锚点 = 详情标题 SetText 整行（全文件唯一）；芯片锚在标题 FontString 右侧，
# 标题宽窄变化自动跟，不另算坐标。未收录的副本 n=0 → 整排隐藏。
_ENTCHIP_ANCHOR = _p(
    '    U.dungeonDetailTitle:SetText(d.name .. "  " .. d.nameEn)',
)
_ENTCHIP_NEW = _p(
    '    U.dungeonDetailTitle:SetText(d.name .. "  " .. d.nameEn)',
    '    -- 入口芯片排布：贴标题右侧一字排开（锚在标题上，标题宽窄自动跟）；',
    '    -- 主点文案「入口」，指引点用数据标签（楼梯入口）。未收录的副本整排隐藏。',
    '    do',
    '        local chips = U.dungeonEntChips or {}',
    '        local pts = DG.EntrancePoints(d.id)',
    '        local n = pts and #pts or 0',
    '        for ci = 1, #chips do',
    '            local chip = chips[ci]',
    '            if ci <= n then',
    '                local p = pts[ci]',
    '                chip:SetText(p.label or L["入口"])',
    '                if ci == 1 then',
    '                    chip:SetPoint("LEFT", U.dungeonDetailTitle, "RIGHT", 10, 0)',
    '                else',
    '                    chip:SetPoint("LEFT", chips[ci - 1], "RIGHT", 6, 0)',
    '                end',
    '                chip:Show()',
    '            else',
    '                chip:Hide()',
    '            end',
    '        end',
    '    end',
)
ENTCHIP_PATCHES = [
    (_ENTCHIP_ANCHOR, _ENTCHIP_NEW, '入口芯片排布'),
]
for old, new, label in ENTCHIP_PATCHES:
    q = out.count(old)
    if q != 1:
        die('入口芯片补丁锚点命中 %d 次（应为 1）：%s' % (q, label))
    out = out.replace(old, new)
print('  入口芯片排布：%d 条补丁已施加' % len(ENTCHIP_PATCHES))

# ── 子页签上移 8：掉落/任务切换按钮往标题靠 ─────────────────────────────────
# 该行逐字来自上游（SEG_MODULE 内，上游严禁增删行）→ 只受检替换 y 偏移：
# -(HERO_META_Y - 4) → -(HERO_META_Y - 12)。锚带 8 空格缩进，全文件唯一。
_TABLIFT_ANCHOR = _p(
    '        bt:SetPoint("TOPRIGHT", detail, "TOPRIGHT", -8 - (i - 1) * 76, -(DG.HERO_META_Y - 4))',
)
_TABLIFT_NEW = _p(
    '        -- 子页签整体上移 8：往标题靠拢',
    '        bt:SetPoint("TOPRIGHT", detail, "TOPRIGHT", -8 - (i - 1) * 76, -(DG.HERO_META_Y - 12))',
)
TABLIFT_PATCHES = [
    (_TABLIFT_ANCHOR, _TABLIFT_NEW, '子页签上移 8'),
]
for old, new, label in TABLIFT_PATCHES:
    q = out.count(old)
    if q != 1:
        die('子页签上移补丁锚点命中 %d 次（应为 1）：%s' % (q, label))
    out = out.replace(old, new)
print('  子页签上移：%d 条补丁已施加' % len(TABLIFT_PATCHES))

# ── 专业页基建交接：把本文件的局部件交给 Core/ProfessionUI.lua（仅无限服）────────────
# 专业页是**另一个文件**（Core/ProfessionUI.lua，手写骨架件、非生成物），在 TOC 里紧挨
# 本文件之后加载。它要画出与副本页**同一套皮**，就得拿到这里的局部件
# （MakeFS / MakeOutline / 颜色 / 常量 / 行池要用的 DG）。故交出一张具名表 ns.ProfHost：
# 本文件因此**一个全局都不新增**（跨插件撞名的唯一来源就是裸全局，见本文件头的说明），
# 那个文件也不必去猜任何需要跨文件可见的名字。
#
# ⚠️ 必须落在**文件末尾**：这些局部件在上面（SEG_* 各段与模块段）才全部就位；
#    写在中间会读到 nil（`local` 的作用域自声明处开始）。
_PROF_HOST = _p(
    '',
    '-------------------- 专业页基建交接（仅无限服）--------------------',
    '-- 专业页在另一个文件里（Core/ProfessionUI.lua，手写骨架件、非生成物），TOC 中紧挨',
    '-- 本文件之后加载。它要画出与副本页同一套皮，就得拿到这里的局部件',
    '-- （MakeFS / MakeOutline / 颜色 / 常量 / 行池所依赖的 DG）。故在此交出这张具名表，',
    '-- 本文件因此一个全局都不新增，那个文件也不必去猜任何跨文件可见的名字。',
    '--',
    '-- ⚠️ 必须写在文件末尾：这些局部件在上面才全部就位（local 的作用域自声明处开始），',
    '--    写在中间会读到 nil。',
    'ns.ProfHost = {',
    '    U = U, DG = DG,',
    '    MakeFS = MakeFS, NewButton = NewButton, MakeOutline = MakeOutline,',
    '    SetOutline = SetOutline, SetTip = SetTip, Unpack = Unpack,',
    '    C_GOLD = C_GOLD, C_GREEN = C_GREEN, C_GREY = C_GREY,',
    '    C_DIM = C_DIM, C_WHITE = C_WHITE, C_TEXT = C_TEXT,',
    '    CONTENT_W = CONTENT_W, CONTENT_H = CONTENT_H,',
    '    PAGE_INSET = PAGE_INSET, ROW_CLASS = ROW_CLASS,',
    '    FALLBACK_ICON = FALLBACK_ICON,',
    '}',
)
if out.count('ns.ProfHost') != 0:
    die('产物里已存在 ns.ProfHost（重复交接？）')
out += _PROF_HOST + CRLF
print('  专业页：ns.ProfHost 基建已交接（%d 项）' % _PROF_HOST.count('='))

# ── 字号口径：标题 16 / 正文·注释 14（2026-09-24 用户定）─────────────────────
# 用户对照详情页截图逐项定：标题类（右栏任务标题/分组头）16；正文、按钮、行内小字
# （前置/阵营兜底单字）一律 14；「数据来源：wowhead」署名保持 11。
# 2026-09-24 追加列表页同口径：分组标题 16、分组右侧注释与卡片副行 14（卡片标题本就 16）。
# ★ 受检批量替换：每条声明预期命中数，数不对就 die。put 步进这类同类串散落多处，
#   语义一致就一起升；顺序敏感：put(f,20)→24 必须排在 put(f,16)→20 之前防链式误改。
FONT_UPGRADES = [
    ('DG.Q_FS_DET = 12', 'DG.Q_FS_DET = 14', 1, '右列详情正文 12→14'),
    ('DG.Q_FS_META = 12', 'DG.Q_FS_META = 14', 1, '任务行副字（地点/等级/状态）12→14'),
    ('DG.Q_FS_HDR = 14', 'DG.Q_FS_HDR = 16', 1, '分组头 14→16'),
    ('U.dungeonQDetName = MakeFS(qdchild, 15, C_GOLD, "LEFT")',
     'U.dungeonQDetName = MakeFS(qdchild, 16, C_GOLD, "LEFT")', 1, '右栏任务标题 15→16'),
    ('U.dungeonSum = MakeFS(page, 12, C_GREY, "RIGHT")',
     'U.dungeonSum = MakeFS(page, 14, C_GREY, "RIGHT")', 1, '统计行 12→14'),
    ('U.dungeonDetailMeta = MakeFS(hero, 12, C_GREY, "LEFT")',
     'U.dungeonDetailMeta = MakeFS(hero, 14, C_GREY, "LEFT")', 1, '横幅 meta 12→14'),
    ('U.dungeonQuestSum = MakeFS(qchild, 13, C_GOLD, "LEFT")',
     'U.dungeonQuestSum = MakeFS(qchild, 14, C_GOLD, "LEFT")', 1, '任务进度行 13→14'),
    ('U.dungeonQDetSt = MakeFS(qdchild, 12, C_GREY, "LEFT")',
     'U.dungeonQDetSt = MakeFS(qdchild, 14, C_GREY, "LEFT")', 1, '右栏状态行 12→14'),
    ('U.dungeonDetailNote = MakeFS(dchild, 13, C_GREY, "LEFT")',
     'U.dungeonDetailNote = MakeFS(dchild, 14, C_GREY, "LEFT")', 1, '详情备注 13→14'),
    ('U.dungeonQuestNote = MakeFS(qchild, 13, C_GREY, "LEFT")',
     'U.dungeonQuestNote = MakeFS(qchild, 14, C_GREY, "LEFT")', 1, '任务备注 13→14'),
    ('r.emL = MakeFS(r, 10, C_GREY, "LEFT")', 'r.emL = MakeFS(r, 14, C_GREY, "LEFT")', 1, '阵营兜底单字 10→14'),
    ('r.cls = MakeFS(r, 10, C_GREY, "LEFT")', 'r.cls = MakeFS(r, 14, C_GREY, "LEFT")', 1, '职业徽记单字 10→14'),
    ('r.pre = MakeFS(r, 10, C_GREY, "LEFT")', 'r.pre = MakeFS(r, 14, C_GREY, "LEFT")', 1, '前置标 10→14'),
    ('            f = MakeFS(child, 11, C_GREY, "LEFT")',
     '            f = MakeFS(child, 14, C_GREY, "LEFT")', 1, '右栏字段名 11→14'),
    ('r.name = MakeFS(r, 12, C_TEXT, "LEFT")', 'r.name = MakeFS(r, 14, C_TEXT, "LEFT")', 1, '前导环节名 12→14'),
    ('r.st = MakeFS(r, 11, C_GREY, "RIGHT")', 'r.st = MakeFS(r, 14, C_GREY, "RIGHT")', 1, '环节状态 11→14'),
    ('r.sub = MakeFS(r, 11, C_GREY, "LEFT")', 'r.sub = MakeFS(r, 14, C_GREY, "LEFT")', 1, '环节副行 11→14'),
    ('NewButton(page, def.text, SW, 22, 13)', 'NewButton(page, def.text, SW, 24, 14)', 1, '子页签 13→14'),
    ('NewButton(detail, L["‹ 副本"], 70, 22, 13)', 'NewButton(detail, L["‹ 副本"], 70, 24, 14)', 1, '返回按钮 13→14'),
    ('NewButton(detail, def.text, 70, 22, 13)', 'NewButton(detail, def.text, 70, 24, 14)', 1, '掉落/任务按钮 13→14'),
    ('NewButton(detail, "", 76, 22, 12)', 'NewButton(detail, "", 92, 24, 14)', 1, '筛选芯片 12→14 加宽 76→92'),
    ('(i - 1) * 82, -DG.FILTER_Y', '(i - 1) * 96, -DG.FILTER_Y', 1, '筛选芯片间距 82→96'),
    ('DG.Q_ROW_H = 30', 'DG.Q_ROW_H = 34', 1, '任务行高 30→34'),
    ('DG.Q_HDR_H = 22', 'DG.Q_HDR_H = 26', 1, '分组头行高 22→26'),
    ('DG.Q_SUM_H = 24', 'DG.Q_SUM_H = 28', 1, '进度行高 24→28'),
    ('(DG.Q_ROW_H - 10) / 2', '(DG.Q_ROW_H - 14) / 2', 3, '行内小字居中偏移按 14 号重算 ×3'),
    ('DG.Q_X_PRE = 408', 'DG.Q_X_PRE = 416', 1, '前置列右移 8px 让位 14 号「N 级可接」'),
    ('r:SetSize(detW, 34)', 'r:SetSize(detW, 38)', 1, '前导环节行高 34→38'),
    ('r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -18)',
     'r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -21)', 1, '环节副行下移 18→21'),
    ('f:SetSize(detW, 20)', 'f:SetSize(detW, 24)', 1, '起始 NPC 行高 20→24'),
    ('put(stf, 18)', 'put(stf, 22)', 1, '状态行步进 18→22'),
    ('put(f, 20)', 'put(f, 24)', 5, 'kv/NPC 行步进 20→24 ×5'),
    ('put(f, 16)', 'put(f, 20)', 6, '小节标题步进 16→20 ×6'),
    ('put(t, 18)', 'put(t, 22)', 3, '正文行步进 18→22 ×3'),
    ('y = -24', 'y = -28', 1, '右栏头部 y 起点 24→28'),
    ('txt = MakeFS(child, 13, C_GOLD, "LEFT")',
     'txt = MakeFS(child, 16, C_GOLD, "LEFT")', 1, '列表分组标题 13→16'),
    ('hint = MakeFS(child, 11, C_DIM, "RIGHT")',
     'hint = MakeFS(child, 14, C_DIM, "RIGHT")', 1, '列表分组右侧注释 11→14'),
    ('card.meta = MakeFS(card, 12, C_GREY, "LEFT")',
     'card.meta = MakeFS(card, 14, C_GREY, "LEFT")', 1, '卡片副行注释 12→14'),
]
for _old, _new, _exp, _lab in FONT_UPGRADES:
    _n = out.count(_old)
    if _n != _exp:
        die('字号升级锚点命中 %d 次（应 %d）：%s' % (_n, _exp, _lab))
    out = out.replace(_old, _new)
print('  详情页字号：标题 16 / 正文 14（%d 条受检替换全部命中）' % len(FONT_UPGRADES))

# ── 本地化 L 化补丁（2026-09-25 zhTW）────────────────────────────────────────
# 任务奖励经验/货币单位串与职业限制两表原为硬编码简体，zhTW 客户端字体缺字形显示
# 豆腐框。全部包 L（zhCN 下 L 回退键名原文，语义不变）；QCLASS 两表的**键**也要包 ——
# 键与数据层 q[15] 的职业名对查，两侧必须经同一条繁体化管线同步转换。
# 键名未在 zhCN.lua 登记 → 走 __index 回退，无需登记（gen_locales 未登记清单会多几条，正常）。
_LOCALE_PATCHES = [
    (_p('                seg[#seg + 1] = out .. " 经验"'),
     _p('                seg[#seg + 1] = out .. L[" 经验"]'), '经验单位'),
    (_p('                if go > 0 then ms = ms .. go .. "金" end'),
     _p('                if go > 0 then ms = ms .. go .. L["金"] end'), '金单位'),
    (_p('                if si > 0 then ms = ms .. si .. "银" end'),
     _p('                if si > 0 then ms = ms .. si .. L["银"] end'), '银单位'),
    (_p('                if co > 0 or ms == "" then ms = ms .. co .. "铜" end'),
     _p('                if co > 0 or ms == "" then ms = ms .. co .. L["铜"] end'), '铜单位'),
    (_p(
        'DG.QCLASS_TOKEN = {',
        '    ["战士"] = "WARRIOR", ["圣骑士"] = "PALADIN", ["猎人"] = "HUNTER", ["盗贼"] = "ROGUE",',
        '    ["牧师"] = "PRIEST", ["萨满"] = "SHAMAN", ["法师"] = "MAGE", ["术士"] = "WARLOCK", ["德鲁伊"] = "DRUID",',
        '}',
        'DG.QCLASS_CHAR = {',
        '    ["战士"] = "战", ["圣骑士"] = "骑", ["猎人"] = "猎", ["盗贼"] = "盗", ["牧师"] = "牧",',
        '    ["萨满"] = "萨", ["法师"] = "法", ["术士"] = "术", ["德鲁伊"] = "德",',
        '}',
     ), _p(
        'DG.QCLASS_TOKEN = {',
        '    [ns.DL("战士")] = "WARRIOR", [ns.DL("圣骑士")] = "PALADIN", [ns.DL("猎人")] = "HUNTER", [ns.DL("盗贼")] = "ROGUE",',
        '    [ns.DL("牧师")] = "PRIEST", [ns.DL("萨满")] = "SHAMAN", [ns.DL("法师")] = "MAGE", [ns.DL("术士")] = "WARLOCK", [ns.DL("德鲁伊")] = "DRUID",',
        '}',
        'DG.QCLASS_CHAR = {',
        '    [ns.DL("战士")] = L["战"], [ns.DL("圣骑士")] = L["骑"], [ns.DL("猎人")] = L["猎"], [ns.DL("盗贼")] = L["盗"], [ns.DL("牧师")] = L["牧"],',
        '    [ns.DL("萨满")] = L["萨"], [ns.DL("法师")] = L["法"], [ns.DL("术士")] = L["术"], [ns.DL("德鲁伊")] = L["德"],',
        '}',
     ), '职业限制两表 L 化（键走 DL 与数据同空间，值走 L 纯显示）'),
]
for _old, _new, _lab in _LOCALE_PATCHES:
    _n = out.count(_old)
    if _n != 1:
        die('本地化补丁锚点命中 %d 次（应为 1）：%s' % (_n, _lab))
    out = out.replace(_old, _new)
print('  本地化 L 化：%d 条补丁已施加（经验/金银铜 + 职业两表）' % len(_LOCALE_PATCHES))

# ── 输出措辞终检（2026-09-23 用户红线）──────────────────────────────────────
#    最终产物里不得残留任何「来源 / 移植」措辞；数据来源只保留 wowhead 署名。
LEAK = ('站点', 'AtlasQuest', 'nfuwow', 'nfu', 'TalentsForever', '剥离', '照抄', '抄它',
        '抽取段', '上游', '出处', '参考')
_lk = []
for _kw in LEAK:
    for _i, _l in enumerate(out.split(CRLF), 1):
        if _kw in _l:
            _lk.append('行%d [%s] %s' % (_i, _kw, _l.strip()[:80]))
if _lk:
    die('产物仍残留来源/移植措辞：\n  ' + '\n  '.join(_lk[:10]))
print('  措辞终检通过：无来源 / 移植残留（wowhead 数据来源署名保留）')

if '\n' in out.replace(CRLF, ''):
    die('输出里出现了裸 LF —— 本文件必须全 CRLF')
if not out.endswith(CRLF):
    out += CRLF

open(DST, 'wb').write(out.encode('utf-8'))
print('已生成 %s' % DST)
print('  行数 %d（CRLF %d）' % (out.count(CRLF), out.count(CRLF)))
