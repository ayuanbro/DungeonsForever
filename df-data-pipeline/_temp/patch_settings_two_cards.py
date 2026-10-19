# -*- coding: utf-8 -*-
"""2026-10-08 二稿：设置弹窗双卡重排 + 双列开关行。

用户反馈（截图）：
  1) 两卡重叠 —— 根因：卡底 SetHeight(6 - y) 使大卡底边到 y-42，而标签页卡顶在 y-18，
     重叠 24px 且压住「标签页」头。
  2) 标签页卡内容放最上面 → 标签页卡改为卡一（置顶），快捷栏卡为卡二。
  3) 显示分组 / 探索子页改双列（QB_SET_2COL）。
  4) 弹窗 220 → 260（「推荐五人本」五字 + 开关 42px > 半列 104px，220 放不下双列）。
"""
import io
import os

ROOT = r"D:/workspace/DungeonsForever"


def load(p):
    with io.open(p, encoding="utf-8", newline="") as f:
        return f.read()


def save(p, s):
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, "%s: hits=%d" % (tag, n)
    return s.replace(old, new, 1)


# ── 1. Core/QuickBar.lua：EnsureSettings 双卡重排 + 双列 ──────────────────
p = os.path.join(ROOT, "Core", "QuickBar.lua")
s = load(p)
nl = "\r\n" if "\r\n" in s else "\n"


def a(t):
    return t.replace("\n", nl) if nl == "\r\n" else t


START = a("    local set = { group = {}, expl = {} }")
END = a("        set.tabCard = tabCard\n        tabCard:SetHeight(8 - ty)\n    end")
assert s.count(START) == 1 and s.count(END) == 1
i0 = s.index(START)
i1 = s.index(END) + len(END)
assert i0 < i1

NEW = a("""    local set = { group = {}, expl = {}, tabs = {} }
    local y = -44

    -- ★ 卡一「标签页」（QB_SET_TABS，2026-10-08 用户；同日二稿：置顶 + 独立成卡）：
    --   主窗七个页签开关。两张卡两块设置内容，本卡放最上面（修两卡重叠：卡二顶随卡一底 +10px 间隙）。
    do
        local tabCard = CreateFrame("Frame", nil, pop)
        if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
            ns.hui.BuildRoundedBG(tabCard, 8, ns.hui.layer.L2, "both", true, 1)
        else
            local bg = tabCard:CreateTexture(nil, "BACKGROUND")
            bg:SetColorTexture(0.18, 0.19, 0.22, 1)
            bg:SetPoint("TOPLEFT", tabCard, "TOPLEFT", 0, 0)
            bg:SetPoint("BOTTOMRIGHT", tabCard, "BOTTOMRIGHT", 0, 0)
        end
        tabCard:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, y)
        tabCard:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -6, y)

        local ty = -10
        local tfs = Fs(tabCard, self.FS_AUX, C_DIM)
        tfs:SetPoint("TOPLEFT", tabCard, "TOPLEFT", 4, ty)
        tfs:SetText(L["标签页"])
        ty = ty - SET_HDR_H

        local function TabRow(label, isOn, setOn)
            local tg = Toggle(tabCard)
            tg:SetPoint("TOPRIGHT", tabCard, "TOPRIGHT", -4, ty)
            tg.label:SetText(label)
            tg:SetChecked(isOn() and true or false)
            tg:SetScript("OnClick", function(sel)
                ns.PlaySound(1)
                setOn(not isOn())
                sel:SetChecked(isOn() and true or false)
                QB:SyncSettings()
                if ns.ApplyTabVisibility then ns.ApplyTabVisibility() end
            end)
            ty = ty - SET_ROW_H
            return tg
        end

        for _, def in ipairs({
            { key = "Dungeons",    label = L["5人本"] },
            { key = "Raids",       label = L["团本"] },
            { key = "Professions", label = L["专业"] },
            { key = "Explore",     label = L["探索"] },
            { key = "Collections", label = L["藏品"] },
            { key = "Bis",         label = L["BIS配装"] },
            { key = "Tier",        label = L["职业指南"] },
        }) do
            if ns.LoadForeverPages or def.key == "Dungeons" or def.key == "Raids" then
                local key = def.key
                set.tabs[key] = TabRow(def.label,
                    function() return ns.QuickCfg().tabs[key] ~= false end,
                    function(v)
                        local tabs = ns.QuickCfg().tabs
                        if not v then
                            -- 最后一个可见页签拒绝关闭（至少留一个入口）
                            local left = 0
                            for _, k in ipairs(ns.QUICK_TABS) do
                                if k ~= key and tabs[k] ~= false
                                    and (ns.LoadForeverPages or k == "Dungeons" or k == "Raids") then
                                    left = left + 1
                                end
                            end
                            if left == 0 then v = true end
                        end
                        tabs[key] = v
                    end)
            end
        end

        set.tabCard = tabCard
        tabCard:SetHeight(8 - ty)
        y = y + ty - 18  -- 卡一底 = y+ty-8；卡二顶再留 10px 间隙（修重叠）
    end

    -- ★ 卡二「快捷按钮栏」（QB_SET_CARD_BG，2026-10-08 用户）：内容区垫一张 L2 圆角大卡片
    --   （与各页「页底大卡」同皮：弧盘 + 1px 描边）。先于各行创建 ⇒ 恒垫底；
    --   普通 Frame 不收鼠标；高度在内容排完后回填（底边超出末行 12px）。
    if not self.cardBg then
        local card = CreateFrame("Frame", nil, pop)
        if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
            ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L2, "both", true, 1)
        else
            local bg = card:CreateTexture(nil, "BACKGROUND")
            bg:SetColorTexture(0.21, 0.22, 0.25, 1)
            bg:SetPoint("TOPLEFT", card, "TOPLEFT", 0, 0)
            bg:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", 0, 0)
        end
        self.cardBg = card
    end
    self.cardBg:ClearAllPoints()
    -- 卡二顶随卡一底（10px 间隙在卡一收口处计入 y）；行全部挂卡片 host ——
    -- 子框架恒画在父框字体串之上，行挂 pop 会被大卡盖住（QB_SET_CARD_BG 层级修正）。
    self.cardBg:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, y)
    self.cardBg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -6, y)
    local host = self.cardBg
    local hy = -10

    local function Header(text)
        local fs = Fs(host, self.FS_AUX, C_DIM)
        fs:SetPoint("TOPLEFT", host, "TOPLEFT", SET_PAD - 6, hy)
        fs:SetText(text)
        hy = hy - SET_HDR_H
    end

    local function ToggleRow(label, isOn, setOn)
        local tg = Toggle(host)
        tg:SetPoint("TOPRIGHT", host, "TOPRIGHT", 6 - SET_PAD, hy)
        tg.label:SetText(label)
        tg:SetChecked(isOn() and true or false)
        tg:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            setOn(not isOn())
            self:SetChecked(isOn() and true or false)
            QB:SyncSettings()
            QB:Apply()
        end)
        hy = hy - SET_ROW_H
        return tg
    end

    -- ★ 双列开关行（QB_SET_2COL，2026-10-08 用户）：显示分组 / 探索子页改双列。
    --   左列开关右缘锚 host CENTER+6（标签右对齐其左侧，五字名放得下），右列贴右缘；
    --   b 侧可为 nil（奇数项落单）。一行吃一个 SET_ROW_H，返回两个开关供落档。
    local function ToggleRow2(aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        local at = Toggle(host)
        at:SetPoint("TOPRIGHT", host, "CENTER", 6, hy)
        at.label:SetText(aLabel)
        at:SetChecked(aIsOn() and true or false)
        at:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            aSetOn(not aIsOn())
            self:SetChecked(aIsOn() and true or false)
            QB:SyncSettings()
            QB:Apply()
        end)
        local bt2
        if bLabel then
            bt2 = Toggle(host)
            bt2:SetPoint("TOPRIGHT", host, "TOPRIGHT", 6 - SET_PAD, hy) -- 2COL-R
            bt2.label:SetText(bLabel)
            bt2:SetChecked(bIsOn() and true or false)
            bt2:SetScript("OnClick", function(self)
                ns.PlaySound(1)
                bSetOn(not bIsOn())
                self:SetChecked(bIsOn() and true or false)
                QB:SyncSettings()
                QB:Apply()
            end)
        end
        hy = hy - SET_ROW_H
        return at, bt2
    end

    Header(L["快捷按钮栏"])
    set.on = ToggleRow(L["显示快捷按钮栏"],
        function() return ns.QuickCfg().on end,
        function(v) ns.QuickCfg().on = v end)

    -- 显示分组：双列（QB_SET_2COL）
    Header(L["显示分组"])
    do
        local vis = {}
        for _, def in ipairs({
            { key = "dungeon", label = L["推荐五人本"] },
            { key = "prof",    label = L["专业"] },
            { key = "explore", label = L["探索"] },
        }) do
            if ns.LoadForeverPages or def.key == "dungeon" then vis[#vis + 1] = def end
        end
        for i = 1, #vis, 2 do
            local m, n2 = vis[i], vis[i + 1]
            local gm = function() return ns.QuickCfg().groups[m.key] end
            local sm = function(v) ns.QuickCfg().groups[m.key] = v end
            if n2 then
                local gn = function() return ns.QuickCfg().groups[n2.key] end
                local sn = function(v) ns.QuickCfg().groups[n2.key] = v end
                set.group[m.key], set.group[n2.key] = ToggleRow2(m.label, gm, sm, n2.label, gn, sn)
            else
                set.group[m.key] = ToggleRow(m.label, gm, sm)
            end
        end
    end

    Header(L["专业列表"])
    do
        local learned = Chip(host, L["只看已学"], 68, 22)
        local all = Chip(host, L["全部"], 68, 22)
        learned:SetPoint("TOPRIGHT", host, "TOPRIGHT", 6 - SET_PAD, hy)
        all:SetPoint("RIGHT", learned, "LEFT", -6, 0)
        set.chipLearned, set.chipAll = learned, all
        learned:SetScript("OnClick", function()
            ns.PlaySound(1)
            ns.QuickCfg().profMode = "learned"
            QB:SyncSettings()
            QB:Apply()
        end)
        all:SetScript("OnClick", function()
            ns.PlaySound(1)
            ns.QuickCfg().profMode = "all"
            QB:SyncSettings()
            QB:Apply()
        end)
        hy = hy - SET_ROW_H
    end

    -- 探索子页：双列（QB_SET_2COL）
    Header(L["探索子页"])
    for i = 1, #EXPLORE_DEFS, 2 do
        local m, n2 = EXPLORE_DEFS[i], EXPLORE_DEFS[i + 1]
        local gm = function() return ns.QuickCfg().expl[m.key] end
        local sm = function(v) ns.QuickCfg().expl[m.key] = v end
        if n2 then
            local gn = function() return ns.QuickCfg().expl[n2.key] end
            local sn = function(v) ns.QuickCfg().expl[n2.key] = v end
            set.expl[m.key], set.expl[n2.key] = ToggleRow2(m.text, gm, sm, n2.text, gn, sn)
        else
            set.expl[m.key] = ToggleRow(m.text, gm, sm)
        end
    end

    -- 卡二高度在此定稿（底边超出末行 12px）
    if self.cardBg then self.cardBg:SetHeight(8 - hy) end
""")
s = s[:i0] + NEW + s[i1:]
save(p, s)
print("OK: QuickBar two-card reorder + 2col")

# ── 2. Core/MainFrame.lua：弹窗 220 → 260 ────────────────────────────────
p = os.path.join(ROOT, "Core", "MainFrame.lua")
s = load(p)
s = sub1(s, "settingsPop:SetWidth(220)", "settingsPop:SetWidth(260)", "MainFrame width")
save(p, s)
print("OK: MainFrame popup width 260")

# ── 3. harness：df_dungeon_check.py 静态/动态断言随新结构更新 + 新增 ㊸ ──
p = os.path.join(ROOT, "_temp", "df_dungeon_check.py")
s = load(p)
assert "㊸" not in s

# 3a. 动态：卡底锚定只查 x（y 现为运行期变量）
s = sub1(s, 'ck("★ ㊱ 卡片背景锚定弹窗内容区（末次 SetPoint = TOPRIGHT 槽 x=-6 y=-36）",\n'
            "   cardBg ~= nil and cardBg.__pts ~= nil and cardBg.__pts[1] == 'TOPRIGHT'\n"
            "   and cardBg.__pts[4] == -6 and cardBg.__pts[5] == -36,",
         'ck("★ ㊱ 卡片背景锚定弹窗内容区（末次 SetPoint = TOPRIGHT 槽 x=-6）",\n'
         "   cardBg ~= nil and cardBg.__pts ~= nil and cardBg.__pts[1] == 'TOPRIGHT'\n"
         "   and cardBg.__pts[4] == -6,", "dyn cardbg anchor")
# 3b. 动态：小卡挂弹窗（文案随二稿）
s = sub1(s, "ck('★ 标签页小卡已建（挂大卡）', QB.set.tabCard ~= nil)",
         "ck('★ 标签页小卡已建（卡一，挂弹窗）', QB.set.tabCard ~= nil)", "dyn tabcard text")

# 3c. 静态 ㊱：卡二锚点/高度随新结构
s = sub1(s, '''   and 'self.cardBg:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, -36)' in _qb_src
   and 'self.cardBg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -6, -36)' in _qb_src
   and 'self.cardBg:SetHeight(6 - y)' in _qb_src''',
         '''   and 'self.cardBg:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, y)' in _qb_src
   and 'self.cardBg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -6, y)' in _qb_src
   and 'self.cardBg:SetHeight(8 - hy)' in _qb_src
   and 'local hy = -10' in _qb_src''', "static cardbg")

# 3d. 静态 ㊷：卡一置顶 + 收口公式，顺序闸反转为 卡一先建
s = sub1(s, """   and 'tabCard:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, y - 18)' in _qb_src
   and _qb_src.find('self.cardBg:SetHeight(6 - y)') < _qb_src.find('set.tabs = {}'))""",
         """   and 'tabCard:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, y)' in _qb_src
   and 'tabCard:SetHeight(8 - ty)' in _qb_src
   and 'y = y + ty - 18' in _qb_src
   and _qb_src.find('QB_SET_TABS') < _qb_src.find('QB_SET_CARD_BG'))""",
         "static tabcard")

# 3e. 新增 ㊸ 静态断言（双列开关行），插在 ㊷ 块之后
NEW_CK = """
ck('★★ ㊸ 设置弹窗双列开关行（QB_SET_2COL，2026-10-08 用户：显示分组/探索子页双列；ToggleRow2 左列锚 CENTER+6、右列贴右缘）',
   'QB_SET_2COL' in _qb_src
   and 'local function ToggleRow2(' in _qb_src
   and 'at:SetPoint("TOPRIGHT", host, "CENTER", 6, hy)' in _qb_src
   and 'if bLabel then' in _qb_src
   and 'return at, bt2' in _qb_src
   and _qb_src.count('-- 2COL-R') == 1)"""
s = sub1(s, """   and _qb_src.find('QB_SET_TABS') < _qb_src.find('QB_SET_CARD_BG'))""",
         """   and _qb_src.find('QB_SET_TABS') < _qb_src.find('QB_SET_CARD_BG'))""" + NEW_CK,
         "insert 2col ck")
save(p, s)
print("OK: df_dungeon_check guards updated")

# ── 4. harness：df_mut_check.py 变异表（更新卡底高度条目 + 新增双列条目）──
p = os.path.join(ROOT, "_temp", "df_mut_check.py")
s = load(p)
s = sub1(s, "b'    if self.cardBg then self.cardBg:SetHeight(6 - y) end\\n'",
         "b'    if self.cardBg then self.cardBg:SetHeight(8 - hy) end\\n'", "mut cardbg height")
OLD_TAIL = """    ('标签页：SyncSettings 不回填开关态（重开设置弹窗勾选错）',
     ('Core/QuickBar.lua', b'        tg:SetChecked(cfg.tabs[k] ~= false)', b'        -- MUT: tabs sync dropped')),
]"""
NEW_TAIL = """    ('标签页：SyncSettings 不回填开关态（重开设置弹窗勾选错）',
     ('Core/QuickBar.lua', b'        tg:SetChecked(cfg.tabs[k] ~= false)', b'        -- MUT: tabs sync dropped')),
    # ㊸ 双列开关行（2026-10-08 用户）
    ('设置弹窗：双列开关右列被砍（只建左列 = 双列退化单列）',
     ('Core/QuickBar.lua', b'        if bLabel then\\n', b'        if false then -- MUT: right col dropped\\n')),
]"""
s = sub1(s, OLD_TAIL, NEW_TAIL, "mut append 2col")
save(p, s)
print("OK: df_mut_check mutations updated")

# ── 5. harness：df_check_new_muts.py DEFAULT_WANT 登记 ───────────────────
p = os.path.join(ROOT, "_temp", "df_check_new_muts.py")
s = load(p)
s = sub1(s, "    '快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',\\n]",
         "    '快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',\\n"
         "    '设置弹窗：双列开关右列被砍（只建左列 = 双列退化单列）',\\n]", "register 2col mut")
save(p, s)
print("OK: DEFAULT_WANT registered")

print("ALL PATCHES APPLIED")
