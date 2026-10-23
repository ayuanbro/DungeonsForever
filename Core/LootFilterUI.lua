local _, ns = ...

if not ns.IsTitan then return end

local L = ns.L
local LF = ns.LootFilter
local D = ns.LootFilterData

local UI = {}
ns.LootFilterUI = UI

if not LF then return end

local BAR_H = 26
local ICON_SZ = 25
local ICON_GAP = 10
local GEAR_SZ = 24
local PLUS_SZ = 20
local BTN_GAP = 8
local MAXS = (LF.MAX_SCHEMES or 6)

local CFG_PAD = 12
local CFG_CONTENT_W = 196
local CFG_ICON_SZ, CFG_ICON_GAP = 22, 6
local CFG_PAGE = 4
local CFG_COLS, CFG_COL_W = 2, 94
local CFG_ROW_H, CFG_HEAD_H, CFG_GROUP_GAP = 24, 26, 8
local CFG_ROW1_Y, CFG_HDR_Y, CFG_SCROLL_TOP = -32, -8, 58

local C_WHITE = { 1, 1, 1 }
local C_TEXT = { 0.88, 0.88, 0.88 }
local C_DIM = { 0.62, 0.62, 0.62 }
local C_RED = { 1, 0.35, 0.30 }

local GROUP_ORDER = {
    { "Weapon",  "武器" },
    { "Armor",   "护甲" },
    { "ShuXing", "装备词缀" },
    { "Other",   "其他", { "Class", "BnetAccount", "Tank" } },
}

UI.ICON_CHOICES = {
    "Interface\\Icons\\INV_Sword_01", "Interface\\Icons\\INV_Axe_01",
    "Interface\\Icons\\INV_Mace_01", "Interface\\Icons\\INV_Staff_01",
    "Interface\\Icons\\INV_Shield_01", "Interface\\Icons\\INV_Helmet_01",
    "Interface\\Icons\\INV_Chest_Plate01", "Interface\\Icons\\INV_Boots_Plate_01",
    "Interface\\Icons\\INV_Gauntlets_01", "Interface\\Icons\\INV_Belt_01",
    "Interface\\Icons\\INV_Bracer_01", "Interface\\Icons\\INV_Misc_Cape_01",
    "Interface\\Icons\\INV_Jewelry_Ring_01", "Interface\\Icons\\INV_Jewelry_Necklace_01",
    "Interface\\Icons\\INV_Jewelry_Talisman_01", "Interface\\Icons\\INV_Misc_Gem_01",
    "Interface\\Icons\\INV_Misc_Book_01", "Interface\\Icons\\INV_Misc_QuestionMark",
    "Interface\\Icons\\Ability_Warrior_DefensiveStance", "Interface\\Icons\\Ability_Warrior_Charge",
    "Interface\\Icons\\Spell_Holy_DevotionAura", "Interface\\Icons\\Spell_Holy_HolyBolt",
    "Interface\\Icons\\Spell_DeathKnight_BloodPresence", "Interface\\Icons\\Spell_DeathKnight_FrostPresence",
}

local function Accent()
    local a = ns.hui and ns.hui.ACCENT
    if a then return a[1], a[2], a[3] end
    return 0x46 / 255, 0xbf / 255, 0x72 / 255
end

local function Fnt(size)
    return ns.FONT, size, (ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE")) or "OUTLINE"
end

local function MakeFS(parent, size, color, justify)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    fs:SetFont(Fnt(size))
    if color then fs:SetTextColor(color[1], color[2], color[3]) end
    if justify then fs:SetJustifyH(justify) end
    return fs
end

local function NewBtn(parent, text, w, h)
    local bt = ns.CreateButton(parent)
    bt:SetSize(w, h)
    if text then bt:SetText(text) end
    local f = bt:GetFontString()
    if f then f:SetFont(Fnt(14)) end
    return bt
end

local function MakeIconButton(parent, size)
    local bt = CreateFrame("Button", nil, parent)
    bt:SetSize(size, size)
    bt.tex = bt:CreateTexture(nil, "ARTWORK")
    bt.tex:SetAllPoints()
    bt.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.tex) end
    bt.hi = bt:CreateTexture(nil, "HIGHLIGHT")
    bt.hi:SetAllPoints()
    bt.hi:SetColorTexture(1, 1, 1, 0.15)
    bt.sel = bt:CreateTexture(nil, "OVERLAY")
    bt.sel:SetColorTexture(Accent())
    bt.sel:SetHeight(2)
    bt.sel:SetPoint("BOTTOMLEFT", bt, "BOTTOMLEFT", 0, -2)
    bt.sel:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", 0, -2)
    bt.sel:Hide()
    return bt
end

local function MakeToggle(parent)
    local tg = CreateFrame("CheckButton", nil, parent)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg.label = MakeFS(parent, 14, C_TEXT, "LEFT")
    tg.label:SetPoint("LEFT", tg, "RIGHT", 4, 0)
    return tg
end

local function MakePager(parent, right)
    local bt = CreateFrame("Button", nil, parent)
    bt:SetSize(14, 14)
    bt.tex = bt:CreateTexture(nil, "ARTWORK")
    bt.tex:SetAllPoints()
    bt.tex:SetTexture("Interface/AddOns/DungeonsForever/Media/textures/arrow.tga")
    if right then
        bt.tex:SetTexCoord(0, 1, 1, 1, 0, 0, 1, 0)
    else
        bt.tex:SetTexCoord(1, 0, 0, 0, 1, 1, 0, 1)
    end
    bt.tex:SetVertexColor(C_DIM[1], C_DIM[2], C_DIM[3])
    return bt
end

local function OpenMenu(anchor, menu)
    local items = {}
    for i = 1, #menu do
        local m = menu[i]
        items[#items + 1] = { text = m.text, icon = m.icon, color = m.colorCode, func = m.func }
    end
    ns.hui.ShowMenu(items, { owner = anchor })
end

local function SchemeActionMenu(idx)
    local store = LF.GetStore()
    local sch = store[idx]
    if not sch then return end
    local menu = {
        { text = L["切换到此方案"], func = function()
            LF.SetActiveScheme(idx); UI:RefreshBar(); UI:RefreshConfig()
        end },
        { text = L["关闭过滤"], func = function()
            LF.SetActiveScheme(nil); UI:RefreshBar(); UI:RefreshConfig()
        end },
        { text = L["重命名 / 更换图标"], func = function() UI:OpenSchemeDialog("edit", idx) end },
        { text = L["左移"], func = function()
            LF.MoveScheme(idx, -1); UI:RefreshBar(); UI:RefreshConfig()
        end },
        { text = L["右移"], func = function()
            LF.MoveScheme(idx, 1); UI:RefreshBar(); UI:RefreshConfig()
        end },
        { text = L["删除方案"], func = function()
            LF.DeleteScheme(idx); UI:RefreshBar(); UI:RefreshConfig()
        end },
    }
    OpenMenu(nil, menu)
end

function UI:EnsureBar()
    if UI.bar then return UI.bar end
    local U = ns.DungeonUI
    local detail = U and U.dungeonDetail
    local DGM = ns.DungeonModule
    if not (detail and DGM) then return nil end

    local bar = CreateFrame("Frame", nil, detail)
    bar:SetSize(250, BAR_H)
    bar:SetPoint("TOPRIGHT", detail, "TOPRIGHT", -4, -(DGM.FILTER_Y or 128))
    UI.bar = bar
    U.lootFilterBar = bar

    local gear = CreateFrame("Button", nil, bar)
    gear:SetSize(GEAR_SZ, GEAR_SZ)
    gear:SetPoint("RIGHT", bar, "RIGHT", 0, 0)
    local gt = gear:CreateTexture(nil, "ARTWORK")
    gt:SetAllPoints()
    gt:SetTexture(ns.SET_ICON)
    gt:SetVertexColor(ns.SET_ICON_IDLE[1], ns.SET_ICON_IDLE[2], ns.SET_ICON_IDLE[3])
    gear:SetScript("OnEnter", function(self)
        gt:SetVertexColor(ns.SET_ICON_ON[1], ns.SET_ICON_ON[2], ns.SET_ICON_ON[3])
        GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["装备过滤设置"], 1, 1, 1, true)
        GameTooltip:Show()
    end)
    gear:SetScript("OnLeave", function()
        gt:SetVertexColor(ns.SET_ICON_IDLE[1], ns.SET_ICON_IDLE[2], ns.SET_ICON_IDLE[3])
        GameTooltip:Hide()
    end)
    gear:SetScript("OnClick", function() ns.PlaySound(1); UI:ToggleConfig() end)
    UI.gear = gear

    local plus = CreateFrame("Button", nil, bar)
    plus:SetSize(PLUS_SZ, PLUS_SZ)
    plus:SetPoint("RIGHT", gear, "LEFT", -BTN_GAP, 0)
    plus.t = MakeFS(plus, 16, C_TEXT, "CENTER")
    plus.t:SetAllPoints()
    plus.t:SetText("+")
    plus:SetScript("OnEnter", function() plus.t:SetTextColor(Accent()) end)
    plus:SetScript("OnLeave", function() plus.t:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3]) end)
    plus:SetScript("OnClick", function()
        ns.PlaySound(1)
        UI:OpenNewScheme()
    end)
    UI.plus = plus

    UI.barIcons = {}
    local prev = plus
    for i = 1, MAXS do
        local bt = MakeIconButton(bar, ICON_SZ)
        bt:SetPoint("RIGHT", prev, "LEFT", -BTN_GAP, 0)
        bt:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        bt.scheme = i
        bt:SetScript("OnClick", function(self, button)
            if button == "RightButton" then
                SchemeActionMenu(self.scheme)
            else
                ns.PlaySound(1)
                local st = LF.GetStore()
                local target = self.scheme
                if st.chooseID == target then target = nil end
                LF.SetActiveScheme(target)
                UI:RefreshBar()
                UI:RefreshConfig()
            end
        end)
        bt:SetScript("OnEnter", function(self)
            local st = LF.GetStore()
            local sch = st[self.scheme]
            if not sch then return end
            GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(sch.Name or "", 1, 1, 1, true)
            GameTooltip:AddLine(L["左键开关过滤 · 右键菜单"], 0.7, 0.75, 0.8, true)
            GameTooltip:Show()
        end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        bt:Hide()
        UI.barIcons[i] = bt
        prev = bt
    end

    UI.barHint = MakeFS(bar, 14, C_RED, "RIGHT")
    UI.barHint:SetPoint("TOPRIGHT", bar, "BOTTOMRIGHT", 0, -2)
    UI.barHint:Hide()

    return bar
end

function UI:FlashHint(anchor, text)
    if not UI.barHint then return end
    UI.barHint:SetText(text)
    UI.barHint:Show()
    UI.__hintN = (UI.__hintN or 0) + 1
    local n = UI.__hintN
    if C_Timer and C_Timer.After then
        C_Timer.After(2, function()
            if UI.__hintN == n and UI.barHint then UI.barHint:Hide() end
        end)
    end
end

function UI:RefreshBar()
    if not UI.barIcons then return end
    local store = LF.GetStore()
    local ch = store.chooseID
    for i = 1, MAXS do
        local bt = UI.barIcons[i]
        local sch = store[i]
        if bt then
            if sch then
                bt.tex:SetTexture(sch.Icon or D.DEFAULT_ICON)
                bt.scheme = i
                local active = (ch == i)
                bt.tex:SetDesaturated(not active)
                bt.tex:SetAlpha(active and 1 or 0.72)
                bt.sel:SetShown(active)
                bt:Show()
            else
                bt:Hide()
            end
        end
    end
end

function UI:OpenNewScheme()
    local store = LF.GetStore()
    if #store >= MAXS then
        if UI.bar then UI:FlashHint(UI.bar, L["方案数量已达上限（最多 6 个）"]) end
        return
    end
    UI:OpenSchemeDialog("new")
end

function UI:EnsureConfig()
    if UI.cfg then return UI.cfg end
    local host = ns.MainFrame or UIParent

    local popup = CreateFrame("Frame", "DungeonsForever_LootFilterCfg", host, "BackdropTemplate")
    popup:SetFrameLevel(512)
    popup:SetFrameStrata("HIGH")
    popup:EnableMouse(true)
    popup:SetScript("OnMouseWheel", function() end)
    popup:SetWidth(220)
    if ns.MainFrame then
        popup:SetPoint("TOPLEFT", host, "TOPRIGHT", 4, 0)
        popup:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", 4, 0)
    else
        popup:SetPoint("CENTER")
        popup:SetSize(220, 600)
    end
    popup:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(popup, 8, "both", ns.hui.layer.L0) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(popup) end

    local title = MakeFS(popup, 16, C_WHITE, "LEFT")
    title:SetPoint("TOPLEFT", popup, "TOPLEFT", 16, -8)
    title:SetText(L["装备过滤"])

    local titleHit = CreateFrame("Frame", nil, popup)
    titleHit:EnableMouse(true)
    titleHit:SetPoint("TOPLEFT", title, "TOPLEFT", -6, 4)
    titleHit:SetPoint("BOTTOMRIGHT", title, "BOTTOMRIGHT", 6, -4)
    titleHit:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["装备过滤"], 1, 1, 1, true)
        GameTooltip:AddLine(L["勾选 = 我需要"], 0.7, 0.75, 0.8, true)
        GameTooltip:Show()
    end)
    titleHit:SetScript("OnLeave", function() GameTooltip:Hide() end)

    local cfg = {
        popup = popup,
        page = 0,
        collapsed = {},
        icons = {},
        toggles = {},
        cells = {},
        headers = {},
    }

    local row = CreateFrame("Frame", nil, popup)
    row:SetSize(CFG_CONTENT_W, 22)
    row:SetPoint("TOPLEFT", popup, "TOPLEFT", CFG_PAD, CFG_ROW1_Y)
    cfg.row = row

    local prev = nil
    for i = 1, CFG_PAGE do
        local bt = MakeIconButton(row, CFG_ICON_SZ)
        if prev then
            bt:SetPoint("LEFT", prev, "RIGHT", CFG_ICON_GAP, 0)
        else
            bt:SetPoint("LEFT", row, "LEFT", 20, 0)
        end
        bt:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        bt:SetScript("OnClick", function(self, button)
            local st = LF.GetStore()
            if not self.scheme or not st[self.scheme] then return end
            if button == "RightButton" then
                SchemeActionMenu(self.scheme)
                return
            end
            ns.PlaySound(1)
            local target = self.scheme
            if st.chooseID == target then target = nil end
            LF.SetActiveScheme(target)
            UI:RefreshBar()
            UI:RefreshConfig()
        end)
        bt:SetScript("OnEnter", function(self)
            local st = LF.GetStore()
            local sch = self.scheme and st[self.scheme]
            if not sch then return end
            GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(sch.Name or "", 1, 1, 1, true)
            GameTooltip:AddLine(L["左键开关过滤 · 右键菜单"], 0.7, 0.75, 0.8, true)
            GameTooltip:Show()
        end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        bt:Hide()
        cfg.icons[i] = bt
        prev = bt
    end

    local rightPager = MakePager(row, true)
    rightPager:SetPoint("RIGHT", row, "RIGHT", 0, 0)
    rightPager:SetScript("OnClick", function() ns.PlaySound(1); UI:TurnPage(1) end)
    cfg.right = rightPager

    local leftPager = MakePager(row, false)
    leftPager:SetPoint("LEFT", row, "LEFT", 0, 0)
    leftPager:SetScript("OnClick", function() ns.PlaySound(1); UI:TurnPage(-1) end)
    cfg.left = leftPager

    local reset = NewBtn(popup, L["重置"], 44, 20)
    reset:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -CFG_PAD, CFG_HDR_Y)
    reset:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        local list = LF.LoadPresets(LF.PlayerClass())
        local menu = {}
        for i = 1, #list do
            local p = list[i]
            local pick = i
            local nm = (type(p.Name) == "string" and p.Name ~= "") and p.Name or tostring(i)
            menu[#menu + 1] = { text = L["重置"] .. " · " .. nm, func = function()
                local st = LF.GetStore()
                local sch = st.chooseID and st[st.chooseID]
                if not sch then UI:ConfigHint(L["请先选择一个方案"]); return end
                LF.ApplyPreset(sch, LF.PlayerClass(), pick)
                UI:RefreshBar(); LF.ApplyAll(); UI:RefreshConfig()
            end }
        end
        menu[#menu + 1] = { text = L["勾选全部"], func = function()
            local st = LF.GetStore()
            local sch = st.chooseID and st[st.chooseID]
            if not sch then UI:ConfigHint(L["请先选择一个方案"]); return end
            LF.ToggleBulk(sch, "all"); LF.ApplyAll(); UI:RefreshConfig()
        end }
        menu[#menu + 1] = { text = L["取消勾选全部"], func = function()
            local st = LF.GetStore()
            local sch = st.chooseID and st[st.chooseID]
            if not sch then UI:ConfigHint(L["请先选择一个方案"]); return end
            LF.ToggleBulk(sch, "none"); LF.ApplyAll(); UI:RefreshConfig()
        end }
        OpenMenu(self, menu)
    end)

    local schemeSet = NewBtn(popup, L["方案设置"], 68, 20)
    schemeSet:SetPoint("RIGHT", reset, "LEFT", -6, 0)
    schemeSet:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        local id = LF.GetStore().chooseID
        if not id then UI:ConfigHint(L["请先选择一个方案"]); return end
        SchemeActionMenu(id)
    end)

    local scroll = CreateFrame("ScrollFrame", nil, popup)
    scroll:SetPoint("TOPLEFT", popup, "TOPLEFT", CFG_PAD, -CFG_SCROLL_TOP)
    scroll:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -CFG_PAD, 12)
    local content = CreateFrame("Frame", nil, scroll)
    content:SetWidth(CFG_CONTENT_W)
    content:SetHeight(10)
    scroll:SetScrollChild(content)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(self, delta) UI:ScrollConfig(delta) end)
    content:EnableMouseWheel(true)
    content:SetScript("OnMouseWheel", function(self, delta) UI:ScrollConfig(delta) end)
    cfg.scroll, cfg.content = scroll, content

    for _, g in ipairs(GROUP_ORDER) do
        local gkey, glabel = g[1], g[2]
        local dims = g[3] or { gkey }

        local hdr = {}
        hdr.arrD = content:CreateTexture(nil, "ARTWORK")
        hdr.arrD:SetSize(10, 10)
        hdr.arrD:SetTexture("Interface/AddOns/DungeonsForever/Media/textures/arrow.tga")
        hdr.arrD:SetRotation(math.pi)
        hdr.arrU = content:CreateTexture(nil, "ARTWORK")
        hdr.arrU:SetSize(10, 10)
        hdr.arrU:SetTexture("Interface/AddOns/DungeonsForever/Media/textures/arrow.tga")
        hdr.label = MakeFS(content, 14, C_WHITE, "LEFT")
        hdr.label:SetText(L[glabel])
        hdr.hit = CreateFrame("Button", nil, content)
        hdr.hit:SetHeight(CFG_HEAD_H)
        hdr.hit:RegisterForClicks("LeftButtonUp")
        hdr.hit.gkey = gkey
        hdr.hit:SetScript("OnClick", function(self)
            if not self.gkey then return end
            cfg.collapsed[self.gkey] = not cfg.collapsed[self.gkey] or nil
            ns.PlaySound(1)
            UI:LayoutConfig()
        end)
        hdr.hit:SetScript("OnEnter", function(self)
            if not self.gkey then return end
            GameTooltip:SetOwner(self, "ANCHOR_TOP")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(L["点击折叠 / 展开该组"], 1, 1, 1, true)
            GameTooltip:Show()
        end)
        hdr.hit:SetScript("OnLeave", function() GameTooltip:Hide() end)
        hdr.hit:EnableMouseWheel(true)
        hdr.hit:SetScript("OnMouseWheel", function(self, delta) UI:ScrollConfig(delta) end)
        cfg.headers[gkey] = hdr

        for _, dim in ipairs(dims) do
            for _, k in ipairs(D.KeyList(dim)) do
                local tg = MakeToggle(content)
                tg.dim, tg.key = dim, k.key
                tg.label:SetText(k.label)
                tg:SetScript("OnClick", function(self)
                    local st = LF.GetStore()
                    local sch = st.chooseID and st[st.chooseID]
                    if not sch then self:SetChecked(false); return end
                    local on = not (type(sch[self.dim]) == "table" and sch[self.dim][self.key] == 1)
                    LF.SetOption(sch, self.dim, self.key, on)
                    self:SetChecked(on)
                    ns.PlaySound(1)
                    LF.ApplyAll()
                end)
                cfg.cells[#cfg.cells + 1] = { tg = tg, group = gkey }
                cfg.toggles[#cfg.toggles + 1] = tg
            end
        end
    end

    local hint = MakeFS(popup, 14, C_RED, "LEFT")
    hint:SetPoint("BOTTOMLEFT", popup, "BOTTOMLEFT", 14, 10)
    hint:Hide()
    cfg.hint = hint

    UI.cfg = cfg
    UI:LayoutConfig()
    return cfg
end

function UI:LayoutConfig()
    local cfg = UI.cfg
    if not cfg then return end
    local content = cfg.content
    local y = 0
    local ci = 0
    for _, g in ipairs(GROUP_ORDER) do
        local gkey = g[1]
        local hdr = cfg.headers[gkey]
        if hdr then
            local collapsed = cfg.collapsed[gkey] == true
            hdr.arrD:ClearAllPoints()
            hdr.arrD:SetPoint("TOPLEFT", content, "TOPLEFT", 0, y - 3)
            hdr.arrU:ClearAllPoints()
            hdr.arrU:SetPoint("TOPLEFT", content, "TOPLEFT", 0, y - 3)
            hdr.arrD:SetShown(not collapsed)
            hdr.arrU:SetShown(collapsed)
            hdr.label:ClearAllPoints()
            hdr.label:SetPoint("TOPLEFT", content, "TOPLEFT", 14, y - 1)
            hdr.hit:ClearAllPoints()
            hdr.hit:SetPoint("TOPLEFT", content, "TOPLEFT", 0, y)
            hdr.hit:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y)
            y = y - CFG_HEAD_H

            local n = 0
            while true do
                local cell = cfg.cells[ci + 1]
                if not cell or cell.group ~= gkey then break end
                ci = ci + 1
                n = n + 1
                local tg = cell.tg
                if collapsed then
                    tg:Hide()
                    tg.label:Hide()
                else
                    local col = (n - 1) % CFG_COLS
                    local rowi = math.floor((n - 1) / CFG_COLS)
                    tg:ClearAllPoints()
                    tg:SetPoint("TOPLEFT", content, "TOPLEFT",
                                col * (CFG_COL_W + 8), y - rowi * CFG_ROW_H - 2)
                    tg.label:ClearAllPoints()
                    tg.label:SetPoint("LEFT", tg, "RIGHT", 4, 0)
                    tg:Show()
                    tg.label:Show()
                end
            end
            if not collapsed then
                local rows = math.max(1, math.ceil(n / CFG_COLS))
                y = y - rows * CFG_ROW_H
            end
            y = y - CFG_GROUP_GAP
        end
    end
    content:SetHeight(math.max(10, -y + 8))
end

function UI:ScrollConfig(delta)
    local cfg = UI.cfg
    if not cfg or not cfg.scroll or not cfg.content then return end
    local scroll, content = cfg.scroll, cfg.content
    local maxS = math.max(0, (content:GetHeight() or 0) - (scroll:GetHeight() or 0))
    local cur = scroll:GetVerticalScroll() or 0
    scroll:SetVerticalScroll(math.max(0, math.min(maxS, cur - (delta or 0) * 40)))
end

function UI:CountPages()
    local store = LF.GetStore()
    local n = 0
    for i = 1, MAXS do if store[i] then n = n + 1 end end
    local pages = math.ceil(n / CFG_PAGE)
    if pages < 1 then pages = 1 end
    return pages
end

function UI:TurnPage(dir)
    local cfg = UI.cfg
    if not cfg then return end
    local p = (cfg.page or 0) + (dir or 0)
    local last = UI:CountPages() - 1
    if p < 0 then p = 0 end
    if p > last then p = last end
    if p == cfg.page then return end
    cfg.page = p
    UI:RefreshConfig()
end

function UI:ConfigHint(text)
    if not UI.cfg or not UI.cfg.hint then return end
    UI.cfg.hint:SetText(text)
    UI.cfg.hint:Show()
    UI.__cfgHintN = (UI.__cfgHintN or 0) + 1
    local n = UI.__cfgHintN
    if C_Timer and C_Timer.After then
        C_Timer.After(2.5, function()
            if UI.__cfgHintN == n and UI.cfg and UI.cfg.hint then UI.cfg.hint:Hide() end
        end)
    end
end

function UI:RefreshConfig()
    if not UI.cfg then return end
    local cfg = UI.cfg
    local store = LF.GetStore()
    local ch = store.chooseID
    local sch = ch and store[ch]

    local maxPage = math.max(0, (UI:CountPages() or 1) - 1)
    if (cfg.page or 0) > maxPage then cfg.page = maxPage end
    if (cfg.page or 0) < 0 then cfg.page = 0 end

    local page = cfg.page or 0
    local base = page * CFG_PAGE
    for slot = 1, CFG_PAGE do
        local bt = cfg.icons[slot]
        local idx = base + slot
        local s = (idx <= MAXS) and store[idx] or nil
        if s then
            bt.scheme = idx
            bt.tex:SetTexture(s.Icon or D.DEFAULT_ICON)
            local active = (ch == idx)
            bt.tex:SetDesaturated(not active)
            bt.tex:SetAlpha(active and 1 or 0.72)
            bt.sel:SetShown(active)
            bt:Show()
        else
            bt.scheme = nil
            bt:Hide()
        end
    end

    local last = UI:CountPages() - 1
    local canL = page > 0
    local canR = page < last
    cfg.left:SetAlpha(canL and 1 or 0.3)
    cfg.left:EnableMouse(canL)
    cfg.right:SetAlpha(canR and 1 or 0.3)
    cfg.right:EnableMouse(canR)

    for _, tg in ipairs(cfg.toggles) do
        local on = false
        if sch and type(sch[tg.dim]) == "table" and sch[tg.dim][tg.key] == 1 then on = true end
        tg:SetChecked(on)
        if sch then tg:Enable() else tg:Disable() end
    end
end

function UI:ConfigPopup()
    return UI.cfg and UI.cfg.popup or nil
end

function UI:OpenConfig()
    if ns.CloseSettings then ns.CloseSettings() end
    if ns.CloseExploreMapSettings then pcall(ns.CloseExploreMapSettings) end
    UI:EnsureConfig()
    if not UI.cfg then return end
    UI:LayoutConfig()
    UI:RefreshConfig()
    UI.cfg.popup:Show()
    if ns.QuickBar and ns.QuickBar.Reanchor then ns.QuickBar:Reanchor() end
end

function UI:CloseConfig()
    if UI.cfg and UI.cfg.popup then UI.cfg.popup:Hide() end
    if ns.QuickBar and ns.QuickBar.Reanchor then ns.QuickBar:Reanchor() end
end

function UI:ToggleConfig()
    if UI.cfg and UI.cfg.popup and UI.cfg.popup:IsShown() then
        UI:CloseConfig()
    else
        UI:OpenConfig()
    end
end

function UI:EnsureDialog()
    if UI.dlg then return UI.dlg end
    local host = ns.MainFrame or UIParent

    local popup = CreateFrame("Frame", "DungeonsForever_LootFilterScheme", host, "BackdropTemplate")
    popup:SetSize(420, 262)
    popup:SetFrameStrata("DIALOG")
    popup:SetMovable(true)
    popup:EnableMouse(true)
    popup:SetClampedToScreen(true)
    popup:SetPoint("CENTER", host, "CENTER", 0, 0)
    popup:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(popup, 8) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(popup) end

    local titleBar = CreateFrame("Frame", nil, popup)
    titleBar:SetPoint("TOPLEFT", popup, "TOPLEFT", 0, 0)
    titleBar:SetPoint("TOPRIGHT", popup, "TOPRIGHT", 0, 0)
    titleBar:SetHeight(32)
    titleBar:EnableMouse(true)
    titleBar:RegisterForDrag("LeftButton")
    titleBar:SetScript("OnDragStart", function() popup:StartMoving() end)
    titleBar:SetScript("OnDragStop", function() popup:StopMovingOrSizing() end)
    local title = MakeFS(titleBar, 16, C_WHITE, "LEFT")
    title:SetPoint("LEFT", titleBar, "LEFT", 16, 0)

    local nameLabel = MakeFS(popup, 14, C_TEXT, "LEFT")
    nameLabel:SetPoint("TOPLEFT", popup, "TOPLEFT", 16, -44)
    nameLabel:SetText(L["名称："])

    local edit = ns.CreateEditBox(popup, 260)
    edit:SetSize(260, 22)
    edit:SetFont(ns.FONT, 14, "")
    edit:SetPoint("LEFT", nameLabel, "RIGHT", 6, 0)

    local gridLabel = MakeFS(popup, 14, C_TEXT, "LEFT")
    gridLabel:SetPoint("TOPLEFT", popup, "TOPLEFT", 16, -74)
    gridLabel:SetText(L["图标："])

    local icons = {}
    local COLS = 12
    local CELL, GAP = 28, 4
    for i, tex in ipairs(UI.ICON_CHOICES) do
        local col = (i - 1) % COLS
        local row = math.floor((i - 1) / COLS)
        local bt = MakeIconButton(popup, CELL - 4)
        bt:SetPoint("TOPLEFT", popup, "TOPLEFT", 18 + col * (CELL + GAP), -96 - row * (CELL + GAP))
        bt.tex:SetTexture(tex)
        bt.icon = tex
        bt:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            UI.dlg.picked = self.icon
            UI:RefreshDialog()
        end)
        icons[i] = bt
    end

    local hint = MakeFS(popup, 14, C_RED, "LEFT")
    hint:SetPoint("TOPLEFT", popup, "TOPLEFT", 16, -196)
    hint:Hide()

    local ok = NewBtn(popup, L["确定"], 84, 24)
    ok:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -16, 14)
    ok:SetScript("OnClick", function()
        ns.PlaySound(1)
        UI:CommitSchemeDialog()
    end)

    local back = NewBtn(popup, L["返回"], 84, 24)
    back:SetPoint("RIGHT", ok, "LEFT", -10, 0)
    back:SetScript("OnClick", function() ns.PlaySound(1); popup:Hide() end)

    UI.dlg = { popup = popup, title = title, edit = edit, icons = icons, hint = hint, picked = D.DEFAULT_ICON }
    return UI.dlg
end

function UI:OpenSchemeDialog(mode, idx)
    UI:EnsureDialog()
    if not UI.dlg then return end
    UI.dlg.mode = mode
    UI.dlg.idx = idx
    UI.dlg.hint:Hide()
    if mode == "edit" then
        local store = LF.GetStore()
        local s = store[idx]
        UI.dlg.edit:SetText((s and s.Name) or "")
        UI.dlg.picked = (s and s.Icon) or D.DEFAULT_ICON
        UI.dlg.title:SetText(L["编辑方案"])
    else
        UI.dlg.edit:SetText("")
        UI.dlg.picked = D.DEFAULT_ICON
        UI.dlg.title:SetText(L["新建方案"])
    end
    UI:RefreshDialog()
    UI.dlg.popup:Show()
    UI.dlg.edit:SetFocus()
end

function UI:RefreshDialog()
    if not UI.dlg then return end
    local picked = UI.dlg.picked or D.DEFAULT_ICON
    for _, bt in ipairs(UI.dlg.icons) do
        local on = (bt.icon == picked)
        bt.tex:SetDesaturated(not on)
        bt.tex:SetAlpha(on and 1 or 0.75)
        bt.sel:SetShown(on)
    end
end

function UI:CommitSchemeDialog()
    if not UI.dlg then return end
    local name = UI.dlg.edit:GetText()
    if type(name) ~= "string" or name == "" then name = L["未命名方案"] end
    local icon = UI.dlg.picked or D.DEFAULT_ICON

    if UI.dlg.mode == "edit" then
        local idx = UI.dlg.idx
        LF.RenameScheme(idx, name)
        LF.SetSchemeIcon(idx, icon)
        UI:RefreshBar(); UI:RefreshConfig()
        LF.ApplyAll()
        UI.dlg.popup:Hide()
    else
        local idx = LF.AddScheme(name, icon)
        if not idx then
            UI.dlg.hint:SetText(L["方案数量已达上限（最多 6 个）"])
            UI.dlg.hint:Show()
            return
        end
        LF.SetActiveScheme(idx)
        UI:RefreshBar(); UI:RefreshConfig()
        UI.dlg.popup:Hide()
    end
end
