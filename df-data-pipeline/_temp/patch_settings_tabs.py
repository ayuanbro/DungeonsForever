# -*- coding: utf-8 -*-
"""QB_SET_TABS：设置弹窗「标签页」七开关（收一张独立小卡）+ 大卡行挂载层级修正。

改动面：
  1. Core/Core.lua        —— QUICK_TABS 七键 + QuickCfg().tabs 懒默认（全开）
  2. Core/DungeonUI.lua   —— ns.ApplyTabVisibility()（隐藏钮重锚不占位 / host 收宽 /
                             分段轨重挂 / 当前页兜底）+ BuildSubTabs 收口调用
  3. Core/QuickBar.lua    —— 设置弹窗：大卡行挂载修正（行挂卡，防子框盖字）+
                             「标签页」小卡七开关 + SyncSettings 回填 + QB:Apply 恒收显隐
  4. _temp/gen_enus.py    —— EN 表加「标签页」后重生成 enUS
  5. Locales/zhTW.lua     —— 手工补「標籤頁」

纪律：锚点命中数必须 == 1；幂等（标记串在即跳过）；保留原文件换行符。
"""
import io
import os

ROOT = r"D:/workspace/DungeonsForever"


def load(p):
    return io.open(os.path.join(ROOT, p), encoding="utf-8", newline="").read()


def save(p, s):
    io.open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="").write(s)


def eol_of(s):
    return "\r\n" if "\r\n" in s else "\n"


def adapt(t, nl):
    return t.replace("\n", nl) if nl == "\r\n" else t


def patch(p, jobs, marker):
    s = load(p)
    if marker in s:
        print("SKIP (already patched):", p)
        return
    nl = eol_of(s)
    for old, new in jobs:
        old2, new2 = adapt(old, nl), adapt(new, nl)
        n = s.count(old2)
        assert n == 1, "anchor hits=%d in %s: %r" % (n, p, old2[:70])
        s = s.replace(old2, new2, 1)
    save(p, s)
    print("OK:", p)


# ───────────────────────── 1. Core/Core.lua ─────────────────────────
CORE_MARKER = "QB_SET_TABS"
patch("Core/Core.lua", [
    # A1：常量表加 QUICK_TABS
    (
        'ns.QUICK_EXPLORE = { "books", "rewards", "bag", "bm" }',
        'ns.QUICK_EXPLORE = { "books", "rewards", "bag", "bm" }\n'
        'ns.QUICK_TABS = { "Dungeons", "Raids", "Professions", "Explore", "Collections", "Bis", "Tier" }'
        ' -- ★ 主窗标签页显隐（QB_SET_TABS，2026-10-08 用户）',
    ),
    # A2：QuickCfg 懒默认
    (
        "    for _, k in ipairs(ns.QUICK_EXPLORE) do\n"
        "        if q.expl[k] == nil then q.expl[k] = true end\n"
        "    end\n"
        "    return q",
        "    for _, k in ipairs(ns.QUICK_EXPLORE) do\n"
        "        if q.expl[k] == nil then q.expl[k] = true end\n"
        "    end\n"
        "    -- ★ 标签页显隐（QB_SET_TABS）：缺省全开（false = 隐藏该页签）\n"
        '    if type(q.tabs) ~= "table" then q.tabs = {} end\n'
        "    for _, k in ipairs(ns.QUICK_TABS) do\n"
        "        if q.tabs[k] == nil then q.tabs[k] = true end\n"
        "    end\n"
        "    return q",
    ),
], CORE_MARKER)

# ─────────────────────── 2. Core/DungeonUI.lua ───────────────────────
patch("Core/DungeonUI.lua", [
    (
        "    U.subTabs = defs\n"
        "    U.subCtrl = ctrl\n"
        "end",
        "    U.subTabs = defs\n"
        "    U.subCtrl = ctrl\n"
        "    ns.ApplyTabVisibility() -- QB_SET_TABS：建好即按存档收一次显隐\n"
        "end\n"
        "\n"
        "-- ★ 标签页显隐（QB_SET_TABS，2026-10-08 用户）：按 ns.QuickCfg().tabs 重排主窗页签。\n"
        "--   隐藏钮不占位（重锚到前一个可见钮），容器宽度回收 → 胶囊/分段轨随 host 居中收窄；\n"
        "--   Hui 皮重挂 AttachButtons 让滑块 offset 只数可见钮。当前页被隐藏时落回第一个可见页。\n"
        "function ns.ApplyTabVisibility()\n"
        "    if not U.subTabs then return end\n"
        "    local cfg = ns.QuickCfg().tabs or {}\n"
        "    local BTN_H = IsHui() and 20 or 26\n"
        "    local GAP = IsHui() and 0 or 6\n"
        "    local totalW, prev, firstVis = 0, nil, nil\n"
        "    for _, tab in ipairs(U.subTabs) do\n"
        "        local bt = tab.button\n"
        "        if bt then\n"
        "            local show = (cfg[tab.key] ~= false)\n"
        "            bt:SetShown(show)\n"
        "            if show then\n"
        "                bt:ClearAllPoints()\n"
        "                if prev then\n"
        '                    bt:SetPoint("LEFT", prev, "RIGHT", GAP, 0)\n'
        "                    totalW = totalW + GAP\n"
        "                else\n"
        '                    bt:SetPoint("TOPLEFT", bt:GetParent(), "TOPLEFT", 0, 0)\n'
        "                end\n"
        "                totalW = totalW + tab.width\n"
        "                prev = bt\n"
        "                firstVis = firstVis or tab.key\n"
        "            end\n"
        "        end\n"
        "    end\n"
        "    if not prev then return end\n"
        "    local host = prev:GetParent()\n"
        "    if host and host.SetSize then host:SetSize(totalW, BTN_H) end\n"
        "    if U.subCtrl then\n"
        "        local vis = {}\n"
        "        for _, tab in ipairs(U.subTabs) do\n"
        '            if cfg[tab.key] ~= false and tab.button then vis[#vis + 1] = tab.button end\n'
        "        end\n"
        "        U.subCtrl:AttachButtons(vis)\n"
        "    end\n"
        "    local cur = U.curSub\n"
        "    if cur and cfg[cur] == false then\n"
        "        U.curSub = firstVis\n"
        "        if U.built then U:SwitchSub(firstVis) end\n"
        "    end\n"
        "end",
    ),
], CORE_MARKER)

# ─────────────────────── 3. Core/QuickBar.lua ───────────────────────
QB_MARKER = "QB_SET_TABS"

# C1a：大卡顶让开标题 + 行挂上卡片（修「子框盖住弹窗字体串」的层级隐患）
patch("Core/QuickBar.lua", [
    (
        '    self.cardBg:ClearAllPoints()\n'
        '    self.cardBg:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, -6)\n'
        '    self.cardBg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -6, -6)\n'
        "\n"
        "    local function Header(text)\n"
        "        local fs = Fs(pop, self.FS_AUX, C_DIM)\n"
        '        fs:SetPoint("TOPLEFT", pop, "TOPLEFT", SET_PAD, y)\n'
        "        fs:SetText(text)\n"
        "        y = y - SET_HDR_H\n"
        "    end\n"
        "\n"
        "    local function ToggleRow(label, isOn, setOn)\n"
        "        local tg = Toggle(pop)\n"
        '        tg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -SET_PAD, y)',
        '    self.cardBg:ClearAllPoints()\n'
        '    -- ★ 顶从 -6 让到 -36（标题占 -14~-30）；行全部挂上卡片 host ——\n'
        '    --   子框架恒画在父框字体串之上，行挂 pop 会被大卡盖住（QB_SET_CARD_BG 层级修正）。\n'
        '    self.cardBg:SetPoint("TOPLEFT", pop, "TOPLEFT", 6, -36)\n'
        '    self.cardBg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -6, -36)\n'
        "    local host = self.cardBg\n"
        "\n"
        "    local function Header(text)\n"
        "        local fs = Fs(host, self.FS_AUX, C_DIM)\n"
        '        fs:SetPoint("TOPLEFT", host, "TOPLEFT", SET_PAD - 6, y + 36)\n'
        "        fs:SetText(text)\n"
        "        y = y - SET_HDR_H\n"
        "    end\n"
        "\n"
        "    local function ToggleRow(label, isOn, setOn)\n"
        "        local tg = Toggle(host)\n"
        '        tg:SetPoint("TOPRIGHT", host, "TOPRIGHT", 6 - SET_PAD, y + 36)',
    ),
    # C1b：专业列表两个 Chip 也挂卡
    (
        '        local learned = Chip(pop, L["只看已学"], 68, 22)\n'
        '        local all = Chip(pop, L["全部"], 68, 22)\n'
        '        learned:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -SET_PAD, y)',
        '        local learned = Chip(host, L["只看已学"], 68, 22)\n'
        '        local all = Chip(host, L["全部"], 68, 22)\n'
        '        learned:SetPoint("TOPRIGHT", host, "TOPRIGHT", 6 - SET_PAD, y + 36)',
    ),
    # C1c：「标签页」小卡七开关（插在大卡高度回填之前）
    (
        "    if self.cardBg then self.cardBg:SetHeight(6 - y) end",
        "    -- ★ 标签页显隐（QB_SET_TABS，2026-10-08 用户）：主窗七个页签做成开关，收进一张独立小卡\n"
        "    do\n"
        "        local tabCard = CreateFrame(\"Frame\", nil, host)\n"
        "        if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then\n"
        "            ns.hui.BuildRoundedBG(tabCard, 8, ns.hui.layer.L3, \"both\", true, 1)\n"
        "        else\n"
        "            local bg = tabCard:CreateTexture(nil, \"BACKGROUND\")\n"
        "            bg:SetColorTexture(0.18, 0.19, 0.22, 1)\n"
        "            bg:SetPoint(\"TOPLEFT\", tabCard, \"TOPLEFT\", 0, 0)\n"
        "            bg:SetPoint(\"BOTTOMRIGHT\", tabCard, \"BOTTOMRIGHT\", 0, 0)\n"
        "        end\n"
        "        tabCard:SetPoint(\"TOPLEFT\", host, \"TOPLEFT\", 4, y + 30)\n"
        "        tabCard:SetPoint(\"TOPRIGHT\", host, \"TOPRIGHT\", -4, y + 30)\n"
        "\n"
        "        local ty = -10\n"
        "        local tfs = Fs(tabCard, self.FS_AUX, C_DIM)\n"
        "        tfs:SetPoint(\"TOPLEFT\", tabCard, \"TOPLEFT\", 4, ty)\n"
        "        tfs:SetText(L[\"标签页\"])\n"
        "        ty = ty - SET_HDR_H\n"
        "\n"
        "        local function TabRow(label, isOn, setOn)\n"
        "            local tg = Toggle(tabCard)\n"
        "            tg:SetPoint(\"TOPRIGHT\", tabCard, \"TOPRIGHT\", -4, ty)\n"
        "            tg.label:SetText(label)\n"
        "            tg:SetChecked(isOn() and true or false)\n"
        "            tg:SetScript(\"OnClick\", function(sel)\n"
        "                ns.PlaySound(1)\n"
        "                setOn(not isOn())\n"
        "                sel:SetChecked(isOn() and true or false)\n"
        "                QB:SyncSettings()\n"
        "                if ns.ApplyTabVisibility then ns.ApplyTabVisibility() end\n"
        "            end)\n"
        "            ty = ty - SET_ROW_H\n"
        "            return tg\n"
        "        end\n"
        "\n"
        "        set.tabs = {}\n"
        "        for _, def in ipairs({\n"
        "            { key = \"Dungeons\",    label = L[\"5人本\"] },\n"
        "            { key = \"Raids\",       label = L[\"团本\"] },\n"
        "            { key = \"Professions\", label = L[\"专业\"] },\n"
        "            { key = \"Explore\",     label = L[\"探索\"] },\n"
        "            { key = \"Collections\", label = L[\"藏品\"] },\n"
        "            { key = \"Bis\",         label = L[\"BIS配装\"] },\n"
        "            { key = \"Tier\",        label = L[\"职业指南\"] },\n"
        "        }) do\n"
        "            if ns.LoadForeverPages or def.key == \"Dungeons\" or def.key == \"Raids\" then\n"
        "                local key = def.key\n"
        "                set.tabs[key] = TabRow(def.label,\n"
        "                    function() return ns.QuickCfg().tabs[key] ~= false end,\n"
        "                    function(v)\n"
        "                        local tabs = ns.QuickCfg().tabs\n"
        "                        if not v then\n"
        "                            -- 最后一个可见页签拒绝关闭（至少留一个入口）\n"
        "                            local left = 0\n"
        "                            for _, k in ipairs(ns.QUICK_TABS) do\n"
        "                                if k ~= key and tabs[k] ~= false\n"
        "                                    and (ns.LoadForeverPages or k == \"Dungeons\" or k == \"Raids\") then\n"
        "                                    left = left + 1\n"
        "                                end\n"
        "                            end\n"
        "                            if left == 0 then v = true end\n"
        "                        end\n"
        "                        tabs[key] = v\n"
        "                    end)\n"
        "            end\n"
        "        end\n"
        "\n"
        "        set.tabCard = tabCard\n"
        "        tabCard:SetHeight(8 - ty)\n"
        "        y = y - 12 - tabCard:GetHeight()\n"
        "    end\n"
        "\n"
        "    if self.cardBg then self.cardBg:SetHeight(6 - y) end",
    ),
    # C1d：SyncSettings 回填标签页开关态（页签显隐不随快捷栏 Gate）
    (
        "    PaintChip(set.chipLearned, cfg.profMode ~= \"all\")",
        "    for k, tg in pairs(set.tabs or {}) do\n"
        "        tg:SetChecked(cfg.tabs[k] ~= false)\n"
        "    end\n"
        "    PaintChip(set.chipLearned, cfg.profMode ~= \"all\")",
    ),
    # C1e：QB:Apply 恒收页签显隐（与快捷栏开关无关，放在早退之前）
    (
        "function QB:Apply()\n"
        "    local cfg = ns.QuickCfg()\n"
        "    if not cfg.on then",
        "function QB:Apply()\n"
        "    local cfg = ns.QuickCfg()\n"
        "    if ns.ApplyTabVisibility then ns.ApplyTabVisibility() end -- QB_SET_TABS：页签显隐与快捷栏开关无关\n"
        "    if not cfg.on then",
    ),
], QB_MARKER)

# ─────────────────────── 4. enUS 生成表 + zhTW ───────────────────────
patch("_temp/gen_enus.py", [
    (
        "    '快捷按钮栏': 'Quick bar',",
        "    '快捷按钮栏': 'Quick bar',\n    '标签页': 'Tabs',",
    ),
], "标签页")

patch("Locales/zhTW.lua", [
    (
        'L["探索子页"] = "探索子頁"',
        'L["探索子页"] = "探索子頁"\nL["标签页"] = "標籤頁"',
    ),
], "標籤頁")

print("ALL PATCHES DONE")
