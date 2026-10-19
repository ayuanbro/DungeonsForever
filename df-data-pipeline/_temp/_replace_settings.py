# -*- coding: utf-8 -*-
"""把 ExploreMap.lua 的设置面板整段替换为侧挂面板版（照装备过滤骨架）。"""
import io

P = r"D:\workspace\DungeonsForever\Core\ExploreMap.lua"

NEW_BLOCK = u'''-- ── 设置面板（照「装备过滤设置」骨架：侧挂主窗右缘 220 宽，不另开浮窗）──
local C_TXT  = { 0.88, 0.88, 0.88 }
local C_WHT  = { 0.95, 0.96, 0.98 }
local C_GOLD = { 1, 0.82, 0 }

local function setFs(parent, size, col)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    local flags = (ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE")) or "OUTLINE"
    fs:SetFont(ns.FONT, size, flags)
    fs:SetTextColor(col[1], col[2], col[3])
    return fs
end

-- 开关行：标签挂父帧（ReskinToggle 的 PurgeNative 会隐藏 tg 上非自建子件），开关靠右
local function mkToggleRow(content, y, label, get, set)
    local tg = CreateFrame("CheckButton", nil, content)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg.label = setFs(content, 14, C_TXT)
    tg.label:SetJustifyH("LEFT")
    tg.label:SetPoint("RIGHT", tg, "LEFT", -8, 0)
    tg.label:SetText(label)
    tg:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y)
    tg:SetChecked(get() and true or false)
    tg:SetScript("OnClick", function(self)
        -- ReskinToggle 覆写了 SetChecked → 存档反推后必须**显式** SetChecked 才会重绘
        set(not (get() and true))
        self:SetChecked(get() and true or false)
        ns.PlaySound(1)
    end)
    tg.sync = function() tg:SetChecked(get() and true or false) end
    return tg
end

-- 档位切换钮（点一下轮换；两三档够用，不引下拉组件）
local function mkCyclerRow(content, y, label, items, get, set)
    local lab = setFs(content, 14, C_TXT)
    lab:SetJustifyH("LEFT")
    lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 5)
    lab:SetText(label)
    local b = mkBtn(content, "", 74)
    b:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 2)
    b.sync = function()
        local v = get()
        for _, it in ipairs(items) do
            if it.v == v then b:SetText(it.t) return end
        end
        b:SetText(items[1].t)
    end
    b:SetScript("OnClick", function()
        local idx, v = 1, get()
        for i, it in ipairs(items) do
            if it.v == v then idx = i break end
        end
        set(items[idx % #items + 1].v)
        b:sync()
        ns.PlaySound(1)
    end)
    b:sync()
    return b
end

-- 数值步进行：[-] 值 [+]（替代滑条——OptionsSliderTemplate 自带「低/高」标签，不合面板风格）
local function mkStepperRow(content, y, label, minv, maxv, step, get, set, fmt)
    local lab = setFs(content, 14, C_TXT)
    lab:SetJustifyH("LEFT")
    lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 5)
    lab:SetText(label)
    local plus = mkBtn(content, "+", 20)
    plus:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 2)
    local minus = mkBtn(content, "-", 20)
    minus:SetPoint("TOPRIGHT", plus, "TOPLEFT", -4, 0)
    local val = setFs(content, 13, C_TXT)
    val:SetJustifyH("RIGHT")
    val:SetPoint("RIGHT", minus, "LEFT", -6, 0)
    val:SetPoint("LEFT", lab, "RIGHT", 6, 0)
    local function clamp(v)
        v = math.floor(v + 0.5)
        return math.max(minv, math.min(maxv, v))
    end
    local function bump(dir)
        set(clamp(get() + dir * step))
        val:SetText(fmt(get()))
        applySettings()
    end
    plus:SetScript("OnClick", function() bump(step) end)
    minus:SetScript("OnClick", function() bump(-step) end)
    val:SetText(fmt(get()))
    local row = {
        sync = function() val:SetText(fmt(get())) end,
        minus = minus, plus = plus,
    }
    return row
end

local function createSettings()
    local host = ns.MainFrame or UIParent
    local f = CreateFrame("Frame", "DFExploreMapSettings", host, "BackdropTemplate")
    f:SetFrameLevel(512)
    f:SetFrameStrata("HIGH")
    f:EnableMouse(true)
    f:SetScript("OnMouseWheel", function() end)
    f:SetWidth(220)
    if host ~= UIParent then
        f:SetPoint("TOPLEFT", host, "TOPRIGHT", 8, 0)
        f:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", 8, 0)
    else
        f:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
        f:SetHeight(600)
    end
    f:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(f, 8) end

    -- 标题行：左「地图设置」，右「重置」（同装备过滤：无 ✕，出口在齿轮/互斥）
    local title = setFs(f, 16, C_WHT)
    title:SetPoint("TOPLEFT", f, "TOPLEFT", 16, -8)
    title:SetJustifyH("LEFT")
    title:SetText(L["地图设置"])
    local syncers = {}
    local resetB = mkBtn(f, L["重置"], 52)
    resetB:SetPoint("TOPRIGHT", f, "TOPRIGHT", -12, -10)
    resetB:SetScript("OnClick", function()
        ns.PlaySound(1)
        local db = ns.DB and ns.DB()
        if db and db.explore and db.explore.mapCfg then
            local c = db.explore.mapCfg
            for k in pairs(c) do c[k] = nil end
        end
        cfg()
        for _, fn in ipairs(syncers) do fn() end
        applySettings()
        if f.syncCoord then f.syncCoord() end
    end)

    -- 滚动区（内容宽 196 = 220 − 左右各 12）
    local scroll = CreateFrame("ScrollFrame", nil, f)
    scroll:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -34)
    scroll:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -12, 12)
    local content = CreateFrame("Frame", nil, scroll)
    content:SetWidth(196)
    content:SetHeight(10)
    scroll:SetScrollChild(content)
    scroll:EnableMouseWheel(true)
    content:EnableMouseWheel(true)
    local function wheel(self, delta)
        local maxr = self:GetVerticalScrollRange() or 0
        if maxr <= 0 then return end
        local cur = (self:GetVerticalScroll() or 0) - delta * 28
        self:SetVerticalScroll(math.max(0, math.min(maxr, cur)))
    end
    scroll:SetScript("OnMouseWheel", wheel)
    content:SetScript("OnMouseWheel", wheel)

    local y = -2
    local function hdr(text)
        local fs = setFs(content, 14, C_WHT)
        fs:SetJustifyH("LEFT")
        fs:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y)
        fs:SetText(text)
        y = y - 26
    end

    -- ── 路线 ──
    hdr(L["路线"])
    do
        local cy = mkCyclerRow(content, y, L["连接方式"], {
            { v = "near", t = L["就近串联"] },
            { v = "area", t = L["按区域分堆"] },
            { v = "order", t = L["数据表顺序"] },
        }, function() return cfg().connect or "near" end,
            function(v) cfg().connect = v BuildRoute()
                if updateTrackerFn then updateTrackerFn() end end)
        syncers[#syncers + 1] = function() cy:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["打卡后自动重算"],
            function() return cfg().autoRecalc ~= false end,
            function(v) cfg().autoRecalc = v end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["包含存疑书籍"],
            function() return cfg().showUnver == true end,
            function(v) cfg().showUnver = v ns.ExploreMapRefresh() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["开图自动亮路线"],
            function() return cfg().autoRoute == true end,
            function(v) cfg().autoRoute = v end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end

    -- ── 地图 ──
    hdr(L["地图"])
    do
        local row = mkStepperRow(content, y, L["图钉大小"], 14, 32, 2,
            function() return cfg().pinSize or 20 end,
            function(v) cfg().pinSize = v end,
            function(v) return tostring(v) end)
        syncers[#syncers + 1] = function() row:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["显示连线"],
            function() return cfg().showLines ~= false end,
            function(v) cfg().showLines = v ns.ExploreMapRefresh() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local cy = mkCyclerRow(content, y, L["连线粗细"], {
            { v = 1.5, t = L["细"] }, { v = 2, t = L["中"] }, { v = 3, t = L["粗"] },
        }, function() return cfg().lineW or 2 end,
            function(v) cfg().lineW = v ns.ExploreMapRefresh() end)
        syncers[#syncers + 1] = function() cy:sync() end
        y = y - 24
    end

    -- ── 追踪条 ──
    hdr(L["追踪条"])
    do
        local cy = mkCyclerRow(content, y, L["书籍显示"], {
            { v = "manual", t = L["手动选书"] },
            { v = "auto", t = L["自动跟随"] },
        }, function() return cfg().bookMode or "manual" end,
            function(v)
                cfg().bookMode = v
                if updateTrackerFn then updateTrackerFn() end
                if f.syncCoord then f.syncCoord() end
            end)
        syncers[#syncers + 1] = function() cy:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["显示罗盘"],
            function() return cfg().showCompass ~= false end,
            function(v) cfg().showCompass = v relayoutTracker(tracker) end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["锁定位置"],
            function() return cfg().lockPos == true end,
            function(v) cfg().lockPos = v applySettings() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local row = mkStepperRow(content, y, L["界面缩放"], 75, 150, 5,
            function() return math.floor((cfg().hudScale or 1) * 100 + 0.5) end,
            function(v) cfg().hudScale = v / 100 end,
            function(v) return v .. "%" end)
        syncers[#syncers + 1] = function() row:sync() end
        y = y - 24
    end

    -- ── 进度数据：坐标输入框（点入全选，手动 Ctrl+C 复制）──
    hdr(L["进度数据"])
    do
        local lab = setFs(content, 14, C_TXT)
        lab:SetJustifyH("LEFT")
        lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 6)
        lab:SetText(L["下一站坐标"])
        local eb = CreateFrame("EditBox", nil, content, "InputBoxTemplate")
        eb:SetSize(120, 20)
        eb:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 2)
        eb:SetAutoFocus(false)
        eb:SetScript("OnEscapePressed", function(s) s:ClearFocus() end)
        eb:SetScript("OnEditFocusGained", function(s) s:HighlightText() end)
        f.syncCoord = function()
            if eb.HasFocus and eb:HasFocus() then return end
            local s2
            if (cfg().bookMode or "manual") == "auto" then
                s2 = route[1]
            elseif manualTrack then
                s2 = stepOfRec(manualTrack)
            end
            if s2 then
                eb:SetText(format("%.1f, %.1f  %s",
                    s2.x * 100, s2.y * 100, tostring(EG.ZoneName(s2.area, s2.area))))
            else
                eb:SetText(L["暂无目标"])
            end
        end
        f.syncCoord()
        y = y - 30
    end

    content:SetHeight(math.max(-y + 8, 40))
    f.syncAll = function()
        for _, fn in ipairs(syncers) do fn() end
        if f.syncCoord then f.syncCoord() end
    end
    f:SetScript("OnShow", function()
        if f.syncAll then f:syncAll() end
    end)
    f:SetScript("OnHide", function() if GameTooltip then GameTooltip:Hide() end end)
    return f
end

function ns.CloseExploreMapSettings()
    if settingsFrame and settingsFrame.IsShown and settingsFrame:IsShown() then
        settingsFrame:Hide()
    end
end

function ns.ExploreMapSettingsToggle()
    if settingsFrame then
        if settingsFrame:IsShown() then
            settingsFrame:Hide()
        else
            -- 与「设置」弹窗 / 装备过滤面板互斥：同侧只挂一个
            if ns.CloseSettings then pcall(ns.CloseSettings) end
            if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then
                pcall(ns.LootFilterUI.CloseConfig, ns.LootFilterUI)
            end
            if settingsFrame.syncAll then settingsFrame:syncAll() end
            settingsFrame:Show()
        end
        return
    end
    settingsFrame = createSettings()
    if ns.CloseSettings then pcall(ns.CloseSettings) end
    if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then
        pcall(ns.LootFilterUI.CloseConfig, ns.LootFilterUI)
    end
    settingsFrame:Show()
end

'''

def main():
    src = io.open(P, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    i = 637  # 0-based → 行 638
    j = 955  # 替换到行 955（含）
    assert u"设置面板" in lines[i], lines[i]
    assert lines[947].startswith(u"function ns.ExploreMapSettingsToggle"), lines[947]
    assert lines[954].strip() == u"end", repr(lines[954])
    lines[i:955] = [NEW_BLOCK]
    io.open(P, "w", encoding="utf-8", newline="").writelines(lines)
    print("OK, total lines:", len(io.open(P, encoding="utf-8").read().splitlines()))

main()
