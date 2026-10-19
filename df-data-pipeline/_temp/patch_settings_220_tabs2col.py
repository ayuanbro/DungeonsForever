# -*- coding: utf-8 -*-
"""2026-10-08 三稿：弹窗宽度恒 220 + 标签页也双列。

用户反馈：
  1) 不要加宽弹窗，宽度永远 220 → 回退 MainFrame 260→220，harness ㉓ 同步回 220。
  2) 标签页也两列显示 → TogglePair 泛化（parent 参数化），卡一七开关两两配对，落单尾行整行。
  3) 220 宽几何预算（host=208，左列开关右缘 CENTER-6=98，右列贴右缘 200，14px 字）：
     左列标签 ≤3 字（48px）、右列 ≤4 字（56px）。「推荐五人本」五字（70px）放不进任何半列
     → 独占整行，专业/探索双列；标签页「职业指南」为第 4 行落单尾 → 整行。
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


# ── 1. Core/QuickBar.lua ─────────────────────────────────────────────────
p = os.path.join(ROOT, "Core", "QuickBar.lua")
s = load(p)
nl = "\r\n" if "\r\n" in s else "\n"


def a(t):
    return t.replace("\n", nl) if nl == "\r\n" else t


# 1a. TogglePair 泛化版插到 y 游标之后（卡一也要用）
OLD_HEAD = a("""    local set = { group = {}, expl = {}, tabs = {} }
    local y = -44
""")
NEW_HEAD = a("""    local set = { group = {}, expl = {}, tabs = {} }
    local y = -44

    -- ★ 双列开关对（QB_SET_2COL，2026-10-08 用户；同日三稿：弹窗恒 220 宽）。
    --   左列开关右缘锚 parent CENTER-6（220 宽半列预算 @14px：左列 ≤3 字、右列 ≤4 字）；
    --   五字名（推荐五人本）与落单尾行走整行 ToggleRow / TabRow。yv 为本行 y 游标，行高由调用方自扣。
    local function TogglePair(parent, yv, aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        local at = Toggle(parent)
        at:SetPoint("TOPRIGHT", parent, "CENTER", -6, yv)
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
            bt2 = Toggle(parent)
            bt2:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 6 - SET_PAD, yv) -- 2COL-R
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
        return at, bt2
    end
""")
s = sub1(s, OLD_HEAD, NEW_HEAD, "insert TogglePair")

# 1b. 标签页七开关改双列（两两配对，落单尾行整行）
OLD_TABS = a("""        for _, def in ipairs({
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
""")
NEW_TABS = a("""        local function mkSetOn(key)
            return function(v)
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
            end
        end

        local vis = {}
        for _, def in ipairs({
            { key = "Dungeons",    label = L["5人本"] },
            { key = "Raids",       label = L["团本"] },
            { key = "Professions", label = L["专业"] },
            { key = "Explore",     label = L["探索"] },
            { key = "Collections", label = L["藏品"] },
            { key = "Bis",         label = L["BIS配装"] },
            { key = "Tier",        label = L["职业指南"] },
        }) do
            if ns.LoadForeverPages or def.key == "Dungeons" or def.key == "Raids" then vis[#vis + 1] = def end
        end
        -- 双列（QB_SET_2COL，2026-10-08 三稿）：两两配对；落单尾行整行（TabRow 自扣游标）
        for i = 1, #vis, 2 do
            local m, n2 = vis[i], vis[i + 1]
            local gm = function() return ns.QuickCfg().tabs[m.key] ~= false end
            if n2 then
                local gn = function() return ns.QuickCfg().tabs[n2.key] ~= false end
                set.tabs[m.key], set.tabs[n2.key] = TogglePair(tabCard, ty,
                    m.label, gm, mkSetOn(m.key), n2.label, gn, mkSetOn(n2.key))
                ty = ty - SET_ROW_H
            else
                set.tabs[m.key] = TabRow(m.label, gm, mkSetOn(m.key))
            end
        end
""")
s = sub1(s, OLD_TABS, NEW_TABS, "tabs 2col")

# 1c. 卡二的 ToggleRow2 换成薄包装（TogglePair 已上移）
OLD_T2 = a("""    -- ★ 双列开关行（QB_SET_2COL，2026-10-08 用户）：显示分组 / 探索子页改双列。
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
""")
NEW_T2 = a("""    -- 双列行薄包装（QB_SET_2COL）：吃一行游标；TogglePair 实现见本函数顶部
    local function ToggleRow2(aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        local at, bt2 = TogglePair(host, hy, aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        hy = hy - SET_ROW_H
        return at, bt2
    end
""")
s = sub1(s, OLD_T2, NEW_T2, "ToggleRow2 wrapper")

# 1d. 显示分组：推荐五人本独占整行（五字 220 半列放不下），专业/探索双列
OLD_GRP = a("""    -- 显示分组：双列（QB_SET_2COL）
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
""")
NEW_GRP = a("""    -- 显示分组（QB_SET_2COL，2026-10-08 三稿）：推荐五人本五字独占整行（220 宽半列放不下），
    -- 专业 / 探索双列；非永服只有推荐五人本一行。
    Header(L["显示分组"])
    do
        set.group.dungeon = ToggleRow(L["推荐五人本"],
            function() return ns.QuickCfg().groups.dungeon end,
            function(v) ns.QuickCfg().groups.dungeon = v end)
        if ns.LoadForeverPages then
            set.group.prof, set.group.explore = ToggleRow2(
                L["专业"],
                function() return ns.QuickCfg().groups.prof end,
                function(v) ns.QuickCfg().groups.prof = v end,
                L["探索"],
                function() return ns.QuickCfg().groups.explore end,
                function(v) ns.QuickCfg().groups.explore = v end)
        end
    end
""")
s = sub1(s, OLD_GRP, NEW_GRP, "groups layout")
save(p, s)
print("OK: QuickBar 220 + tabs 2col")

# ── 2. Core/MainFrame.lua：260 → 220（用户：恒不加宽）────────────────────
p = os.path.join(ROOT, "Core", "MainFrame.lua")
s = load(p)
s = sub1(s, "settingsPop:SetWidth(260)", "settingsPop:SetWidth(220)", "MainFrame width back")
save(p, s)
print("OK: MainFrame popup width 220")

# ── 3. harness：㊸ 锚点随 TogglePair 泛化、㉓ 回 220 ─────────────────────
p = os.path.join(ROOT, "_temp", "df_dungeon_check.py")
s = load(p)
s = sub1(s, """ck('★★ ㊸ 设置弹窗双列开关行（QB_SET_2COL，2026-10-08 用户：显示分组/探索子页双列；ToggleRow2 左列锚 CENTER+6、右列贴右缘）',
   'QB_SET_2COL' in _qb_src
   and 'local function ToggleRow2(' in _qb_src
   and 'at:SetPoint("TOPRIGHT", host, "CENTER", 6, hy)' in _qb_src""",
         """ck('★★ ㊸ 设置弹窗双列开关行（QB_SET_2COL，2026-10-08 三稿：显示分组/探索子页/标签页双列；TogglePair 泛化 parent，左列锚 CENTER-6、右列贴右缘；弹窗恒 220）',
   'QB_SET_2COL' in _qb_src
   and 'local function TogglePair(' in _qb_src
   and 'local function ToggleRow2(' in _qb_src
   and 'at:SetPoint("TOPRIGHT", parent, "CENTER", -6, yv)' in _qb_src""", "38 guard")
s = sub1(s, """ck('★★ ㉓ 设置弹窗贴主窗外侧右手边（左缘 = 主窗右缘 + 8，顶底与主窗齐平、高度一致，宽 260——2026-10-08 双列开关行加宽）',
   'settingsPop:SetPoint("TOPLEFT", f, "TOPRIGHT", 8, 0)' in _about_src
   and 'settingsPop:SetPoint("BOTTOMLEFT", f, "BOTTOMRIGHT", 8, 0)' in _about_src
   and 'settingsPop:SetWidth(260)' in _about_src)""",
         """ck('★★ ㉓ 设置弹窗贴主窗外侧右手边（左缘 = 主窗右缘 + 8，顶底与主窗齐平、高度一致，宽 220——2026-10-08 用户：恒不加宽）',
   'settingsPop:SetPoint("TOPLEFT", f, "TOPRIGHT", 8, 0)' in _about_src
   and 'settingsPop:SetPoint("BOTTOMLEFT", f, "BOTTOMRIGHT", 8, 0)' in _about_src
   and 'settingsPop:SetWidth(220)' in _about_src)""", "23 width back")
save(p, s)
print("OK: harness guards updated")
print("ALL PATCHES APPLIED")
