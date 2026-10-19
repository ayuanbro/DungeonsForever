# -*- coding: utf-8 -*-
"""第六刀补丁：详情外壳「四组按钮」从点击帧挪进分帧管线。

背景（探针 _probe_shell.py 实测）：
    详情外壳 60 帧 / 336 纹理，其中 15 颗按钮吃掉 59 帧 / 333 纹理
    （ns.CreateButton ≈3 帧/颗；BuildRoundBorder 描边 0 帧但占满纹理额度），
    非按钮部分（hero / 标题 / 备注 / 提示区 / 滚动容器）只占 1 帧。

做法：
    · EnsureDetailBuilt 只同步建「hero + 返回键 + 标题 + 入口表 + 备注 + 提示区 +
      滚动容器/重池表」，四张控件表先立空表；
    · 页签 / 入口 chip / 筛选行 / 视图按钮 四组各成一个分帧块（原循环体逐字搬运，
      缩进一字未动，保证变异锚点不被打散）；
    · 每块建完立刻补刷一次「外壳文字 / 选中态 / 显隐」——
      新增 DG.ApplyDetailChrome（从 U:RenderDungeonTab 尾部整段搬出）、
      DG.PaintEntChips（从 U:ShowDungeonDetail 搬出并左移 4 格）、
      DG.RefreshFilterRow（借 DG.__chromeOnly 复用掉落/任务两条渲染路径里的
      「筛选行上字」那一段，不重排待建行）。

只改 Core/DungeonUI.lua；行尾 CRLF 守恒（0 裸 LF）。
"""
import io
import os

ROOT = r'D:\workspace\DungeonsForever'
P = os.path.join(ROOT, 'Core', 'DungeonUI.lua')

b = io.open(P, 'rb').read()
assert b.count(b'\n') - b.count(b'\r\n') == 0, '源文件本来就有裸 LF，先查清楚再改'
s = b.decode('utf-8').replace('\r\n', '\n')


def rep(old, new, tag, n=1):
    global s
    c = s.count(old)
    assert c == n, '%s：锚点命中 %d 次（期望 %d）\n%r' % (tag, c, n, old[:120])
    s = s.replace(old, new, n)


# ══════════════════════════════════════════════════════════════════════════
# 1) 先把 U:RenderDungeonTab 尾部整段搬出来（DG.ApplyDetailChrome 的函数体）
# ══════════════════════════════════════════════════════════════════════════
i_rt = s.index('function U:RenderDungeonTab()')
i_cap = s.index('DG.CAPSULE_LIFT = 10', i_rt)
i_chrome = s.index('    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(', i_rt)
assert i_chrome < i_cap
chrome_body = s[i_chrome:i_cap]
assert chrome_body.endswith('end\n'), repr(chrome_body[-20:])
chrome_body = chrome_body[:-len('end\n')]
rep(s[i_chrome:i_cap], '    DG.ApplyDetailChrome(cur)\nend\n',
    'R1 RenderDungeonTab 尾部改调 DG.ApplyDetailChrome')

# ══════════════════════════════════════════════════════════════════════════
# 2) 把 EnsureDetailBuilt 的九段切出来
# ══════════════════════════════════════════════════════════════════════════
i_fn = s.index('function DG.EnsureDetailBuilt()')
i_next = s.index('function DG.EnsureOverviewBuilt()')
body = s[i_fn:i_next]

M_HERO = '    local hero = CreateFrame("Frame", nil, detail)\n'
M_BACKEND = '    U.dungeonBack = back\n'
M_TABS = '    U.dungeonTabBtns = {}\n'
M_TITLE = '    U.dungeonDetailTitle = MakeFS(hero, 16, C_WHITE, "LEFT")\n'
M_CHIPS = '    U.dungeonEntChips = {}\n'
M_META = '    U.dungeonDetailMeta = MakeFS(hero, 14, C_GREY, "LEFT")\n'
M_FILTER = '    U.dungeonFilterBtns = {}\n'
M_LOOTVIEW = '    -- ★★ 掉落页显示方式切换'
M_LV_TBL = '    U.dungeonLootViewBtns = {}\n'
M_SCROLL = '    local dscroll = CreateFrame("ScrollFrame", nil, detail)\n'
M_NOTE = '    U.dungeonDetailNote = MakeFS(dchild, 14, C_GREY, "LEFT")\n'


def at(m):
    assert body.count(m) == 1, '标记不唯一：%r' % m[:60]
    return body.index(m)


def strip_tail_blank(t):
    while t.endswith('\n\n'):
        t = t[:-1]
    return t


def drop_first_line(t):
    return t[t.index('\n') + 1:]


pre = body[:at(M_HERO)]
hero_ = body[at(M_HERO):at(M_BACKEND) + len(M_BACKEND)]
tabs_inner = drop_first_line(strip_tail_blank(body[at(M_TABS):at(M_TITLE)]))
title_ = body[at(M_TITLE):at(M_CHIPS)]
chips_inner = drop_first_line(strip_tail_blank(body[at(M_CHIPS):at(M_META)]))
meta_ = strip_tail_blank(body[at(M_META):at(M_FILTER)])
filt_inner = drop_first_line(strip_tail_blank(body[at(M_FILTER):at(M_LOOTVIEW)]))
lv_cmt = body[at(M_LOOTVIEW):at(M_LV_TBL)]
lv_inner = drop_first_line(strip_tail_blank(body[at(M_LV_TBL):at(M_SCROLL)]))
scroll_ = body[at(M_SCROLL):at(M_NOTE) + len(M_NOTE)]

for name, t, head in (('tabs', tabs_inner, '    local tabs = {'),
                      ('chips', chips_inner, '    for i = 1, 3 do\n'),
                      ('filt', filt_inner, '    for i = 1, DG.FILTER_MAX do\n'),
                      ('lv', lv_inner, '    for vi = 1, 2 do\n')):
    assert t.startswith(head), (name, t[:60])
    assert t.endswith('    end\n'), (name, t[-40:])

# ══════════════════════════════════════════════════════════════════════════
# 3) 组装新的 EnsureDetailBuilt + 四个分帧块 + 三个补刷助手
# ══════════════════════════════════════════════════════════════════════════
NEW_BODY_TAIL = '''    -- ★ 分帧：重池摊到随后的空闲帧里建（首屏只付壳体）。
    --   每块都幂等；切页/切视图时若还没轮到，会由对应的 Ensure* 同步补建。
    --
    -- ★★★ 2026-10-03「点副本就卡死」第四刀：**不再预建 boss 卡池与地图页**。
    --   实测这两块是首开成本的大头，且都属于「用到才需要」：
    --     · boss 卡池（58 帧 / 580 纹理）只有掉落页切到「卡片」视图才用 ——
    --       RenderDungeonLootCards / U:SetLootView 自己会补建（DG.EnsureCardPool）；
    --     · 地图页（138 帧 / 1153 纹理）只有切到「地图」页签才用 ——
    --       U:RenderDungeonTab 的 map 分支自己会补建（DG.EnsureMapPage）。
    --   ★ 任务两栏 / 攻略栏仍预建：各只是两个滚动容器 + 几行文字，很轻，且是常用页签。
    --
    -- ★★★ 第六刀 · 详情外壳分片（2026-10-03「点开瞬间只出框架 + 进度条」）：
    --   探针实测（_temp/_probe_shell.py）外壳 60 帧 / 336 纹理里，**15 颗按钮吃掉
    --   59 帧 / 333 纹理**（ns.CreateButton 约 3 帧/颗；BuildRoundBorder 描边 0 帧
    --   但把纹理额度占满），非按钮部分只占 1 帧。⇒ 页签 / 入口 chip / 筛选行 /
    --   视图按钮 四组各排一块到分帧管线里，点副本那一帧只剩「hero + 返回键 +
    --   标题 + 备注 + 提示区 + 滚动容器」。
    --   ★ 四张控件表在这里先立成**空表**：首次渲染时那几行循环全是 nil 安全
    --     （`#(U.xxx or {})` / `if U.xxx then`），内容照常画，只是按钮晚几帧出现；
    --     每块建完立刻补刷一次文字与选中态（DG.ApplyDetailChrome 等）把顺序追平
    --     —— 顺序仍是「先建壳、后切显隐」，不踩那条空白老坑。
    U.dungeonTabBtns = {}
    U.dungeonFilterBtns = {}
    U.dungeonLootViewBtns = {}
    DG.PushStep(DG.BuildDetailTabs)
    DG.PushStep(DG.BuildDetailChips)
    DG.PushStep(DG.BuildDetailFilterRow)
    DG.PushStep(DG.BuildDetailLootView)
    DG.PushStep(DG.EnsureQuestLane)
    DG.PushStep(DG.EnsureGuideLane)
    DG.RunSteps()
end

'''

new_fn = (pre + hero_ + title_ + M_CHIPS + meta_ + '\n' + scroll_ + '\n'
          + NEW_BODY_TAIL)

BUILDERS = '''-- ══ 详情外壳的四组控件（分帧建；每块一组，建完立刻补刷外壳文字/选中态）══════
--   ★ 循环体是**逐字搬过来**的（缩进一字未动）—— 里面那些 SetPoint / SetScript
--     既是版式常量又是变异锚点，重排一次就会打散。
--   ★ 幂等闸：对应表里已经有东西就直接 return（分帧块万一被重排也不重复建）。
--   ★ 四张空表由 DG.EnsureDetailBuilt 先立好，所以渲染路径任何时刻看到的都是表不是 nil。
--   ★ 时间序：这四块排在详情渲染**之后**、行帧分片**之前**（RenderDungeonLoot 尾部
--     才会 PushStep(DG.BuildPendRows)），所以它们各自独占一帧、互不叠加。

-- 入口 chip 的「上字 + 显隐」：首帧渲染时 chip 还没建，只能等这一块建完补一次。
function DG.PaintEntChips(d)
    local chips = U.dungeonEntChips
    if not (d and chips) then return end
    local pts = DG.EntrancePoints(d.id)
    local n = pts and #pts or 0
    for ci = 1, #chips do
        local chip = chips[ci]
        if ci <= n then
            local p = pts[ci]
            chip:SetText(p.label or L["入口"])
            if ci == 1 then
                chip:SetPoint("LEFT", U.dungeonDetailTitle, "RIGHT", 10, 0)
            else
                chip:SetPoint("LEFT", chips[ci - 1], "RIGHT", 6, 0)
            end
            chip:Show()
        else
            chip:Hide()
        end
    end
end

-- 筛选行的「上字」按当前页签分派：
--   · 掉落页 → U:RenderDungeonLoot 里那一段；· 任务页 → U:RenderDungeonQuests 里那一段。
--   两者都靠 DG.__chromeOnly 只跑「筛选行上字」就收工 —— **绝不能重排待建行**
--   （那会把已经排好、还没建的行帧整体丢掉 = 真丢行）。
--   · 攻略 / 地图页本来就不显示筛选行，直接隐藏。
function DG.RefreshFilterRow()
    local cur = U.dungeonTab or "loot"
    if cur == "guide" or cur == "map" then
        for i = 1, #(U.dungeonFilterBtns or {}) do U.dungeonFilterBtns[i]:Hide() end
        return
    end
    if cur == "quest" then DG.EnsureQuestLane() end
    DG.__chromeOnly = true
    local ok, err = pcall(function()
        if cur == "quest" then U:RenderDungeonQuests() else U:RenderDungeonLoot() end
    end)
    DG.__chromeOnly = nil
    if not ok then
        print("|cffff5040[无限副本手册] 外壳补刷出错（已跳过）：|r" .. tostring(err))
    end
end

-- 详情页外壳的「显隐 / 选中态 / 页签高亮」统一入口。
--   渲染路径（U:RenderDungeonTab 末尾）与外壳分片补建都调它 ⇒
--   「先建壳、后补壳」两种时序下最终状态完全一致。
function DG.ApplyDetailChrome(cur)
    cur = cur or U.dungeonTab or "loot"
    local isQuest = (cur == "quest")
    local isGuide = (cur == "guide")
    local isMap   = (cur == "map")
{CHROME}end

function DG.BuildDetailTabs()
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    if next(U.dungeonTabBtns or {}) then return end
{TABS}    DG.ApplyDetailChrome(U.dungeonTab or "loot")
end

function DG.BuildDetailChips()
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    if next(U.dungeonEntChips or {}) then return end
{CHIPS}    DG.PaintEntChips(U.dungeonDetailCur)
end

function DG.BuildDetailFilterRow()
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    if next(U.dungeonFilterBtns or {}) then return end
{FILT}    DG.RefreshFilterRow()
    DG.ApplyDetailChrome(U.dungeonTab or "loot")
end

function DG.BuildDetailLootView()
    local detail = U.dungeonDetail
    if not detail then return end
    if next(U.dungeonLootViewBtns or {}) then return end
{LVC}    DG.ApplyDetailChrome(U.dungeonTab or "loot")
end

'''

BUILDERS = (BUILDERS
            .replace('{CHROME}', chrome_body)
            .replace('{TABS}', tabs_inner)
            .replace('{CHIPS}', chips_inner)
            .replace('{FILT}', filt_inner)
            .replace('{LVC}', lv_cmt + '\n' + lv_inner))
for ph in ('{CHROME}', '{TABS}', '{CHIPS}', '{FILT}', '{LVC}'):
    assert ph not in BUILDERS, ph

s = s[:i_fn] + new_fn + BUILDERS + s[i_next:]

# ══════════════════════════════════════════════════════════════════════════
# 4) U:ShowDungeonDetail 的 chip 上字段 → 调 DG.PaintEntChips
# ══════════════════════════════════════════════════════════════════════════
OLD_CHIP = '''    do
        local chips = U.dungeonEntChips or {}
        local pts = DG.EntrancePoints(d.id)
        local n = pts and #pts or 0
        for ci = 1, #chips do
            local chip = chips[ci]
            if ci <= n then
                local p = pts[ci]
                chip:SetText(p.label or L["入口"])
                if ci == 1 then
                    chip:SetPoint("LEFT", U.dungeonDetailTitle, "RIGHT", 10, 0)
                else
                    chip:SetPoint("LEFT", chips[ci - 1], "RIGHT", 6, 0)
                end
                chip:Show()
            else
                chip:Hide()
            end
        end
    end
'''
rep(OLD_CHIP, '    DG.PaintEntChips(d)\n', 'R2 ShowDungeonDetail 的 chip 上字段')

# ══════════════════════════════════════════════════════════════════════════
# 5) DG.__chromeOnly 三处守卫（掉落 / 任务 渲染路径 + Build 重置）
# ══════════════════════════════════════════════════════════════════════════
rep('''    DG.__pendRows = {}

    local counts = { all = 0, weapon = 0, armor = 0, quest = 0, new = 0 }''',
    '''    -- ★★★ 第六刀：外壳分片补建时只借下面「筛选行上字」那一段，别动待建表
    --   （那些行还在队列里等着建 —— 丢了就是真丢行）。
    if not DG.__chromeOnly then DG.__pendRows = {} end

    local counts = { all = 0, weapon = 0, armor = 0, quest = 0, new = 0 }''',
    'R3 RenderDungeonLoot 待建表守卫')

rep('''    for i = #DG.FILTERS + 1, #(U.dungeonFilterBtns or {}) do
        U.dungeonFilterBtns[i]:Hide()
    end

    local named, special = {}, {}''',
    '''    for i = #DG.FILTERS + 1, #(U.dungeonFilterBtns or {}) do
        U.dungeonFilterBtns[i]:Hide()
    end
    -- ★★★ 第六刀：外壳分片补建时，借完「筛选行上字」就收工（不重排待建行）。
    if DG.__chromeOnly then return end

    local named, special = {}, {}''',
    'R4 RenderDungeonLoot 补刷早退')

rep('    local nVis, doneVis = 0, 0',
    '''    -- ★★★ 第六刀：外壳分片补建时，借完「筛选行上字」就收工。
    if DG.__chromeOnly then return end

    local nVis, doneVis = 0, 0''',
    'R5 RenderDungeonQuests 补刷早退')

rep('''    U.dungeonBuilt = false
    U.detailBuilt = nil''',
    '''    U.dungeonBuilt = false
    DG.__chromeOnly = nil
    U.detailBuilt = nil''',
    'R6 Build 重置 __chromeOnly')

# ══════════════════════════════════════════════════════════════════════════
# 6) 落盘（CRLF 守恒）
# ══════════════════════════════════════════════════════════════════════════
out = s.replace('\n', '\r\n').encode('utf-8')
assert out.count(b'\n') - out.count(b'\r\n') == 0, '产生了裸 LF'
io.open(P, 'wb').write(out)
print('OK  %s  %d bytes  CRLF %d  裸LF %d'
      % (P, len(out), out.count(b'\r\n'), out.count(b'\n') - out.count(b'\r\n')))
