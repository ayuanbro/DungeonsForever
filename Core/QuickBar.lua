local _, ns = ...

if not ns.IsTitan then return end

local L = ns.L

local QB = {}
ns.QuickBar = QB

QB.W = 120
QB.SLOT1 = 4
QB.SLOT2 = 228
QB.PAD = 8
QB.CW = QB.W - QB.PAD * 2
QB.TEXT_PAD = 4
QB.FS_NAME, QB.FS_AUX = 14, 16
QB.FS_GRP = 14
QB.ICON = 16
QB.ICON_X = 3
QB.NAME_ICON_X = QB.ICON_X + QB.ICON + 4
QB.BODY_Y = -10
QB.GRP_H, QB.GAP = 20, 3
QB.ROW_H = 22
QB.RADIUS = 6

local C_WHITE = { 1, 1, 1 }
local C_TEXT  = { 0.88, 0.88, 0.88 }
local C_DIM   = { 0.62, 0.62, 0.62 }
local C_GOLD  = { 1, 0.82, 0 }
local C_EDGE  = { 0.40, 0.43, 0.50 }
QB.EDGE, QB.EDGE_HOT = C_EDGE, C_GOLD
QB.FILL, QB.FILL_HOT = 0.04, 0.12

local strbyte, strsub, format = string.byte, string.sub, format or string.format

local EXPLORE_DEFS = {
    { key = "books",   text = L["40本书"] },
    { key = "rewards", text = L["奖励总览"] },
    { key = "bag",     text = L["睡袋"] },
    { key = "bm",      text = L["战斗法师"] },
}

local function Accent()
    local a = ns.hui and ns.hui.ACCENT
    if a then return a[1], a[2], a[3] end
    return 0x46 / 255, 0xbf / 255, 0x72 / 255
end

local function Fs(parent, size, color)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    fs:SetFont(ns.FONT, size, "")
    if color then fs:SetTextColor(color[1], color[2], color[3]) end
    return fs
end

local function Outline(bt, on)
    local H = ns.ProfHost
    if H and H.SetButtonSelected then H.SetButtonSelected(bt, on) end
end

local FALLBACK_ICON = (ns.ProfHost and ns.ProfHost.FALLBACK_ICON)
    or "Interface\\Icons\\INV_Misc_QuestionMark"

local function SetIcon(tex, name)
    if type(name) == "number" then
        tex:SetTexture(name)
    elseif type(name) == "string" and name ~= "" then
        if name:find("\\", 1, true) then
            tex:SetTexture(name)
        else
            tex:SetTexture("Interface\\Icons\\" .. name)
        end
    else
        tex:SetTexture(FALLBACK_ICON)
    end
end

local function Chars(s)
    local out, i, n = {}, 1, #s
    while i <= n do
        local b = strbyte(s, i) or 0
        local len = 1
        if b >= 0xF0 then len = 4
        elseif b >= 0xE0 then len = 3
        elseif b >= 0xC0 then len = 2 end
        out[#out + 1] = strsub(s, i, i + len - 1)
        i = i + len
    end
    return out
end

local function CharW(ch, size)
    local b = strbyte(ch, 1) or 0
    if b >= 0xE0 then return size end
    if b >= 0xC0 then return size * 0.9 end
    return size * 0.55
end

local function EstW(text, size)
    local w = 0
    for _, ch in ipairs(Chars(text)) do w = w + CharW(ch, size) end
    return w
end

local function Fit(text, maxw, size)
    if EstW(text, size) <= maxw then return text end
    local out, w = {}, 0
    local budget = maxw - size
    for _, ch in ipairs(Chars(text)) do
        local cw = CharW(ch, size)
        if w + cw > budget then break end
        out[#out + 1] = ch
        w = w + cw
    end
    if #out == 0 and budget > 0 then
        out[1] = Chars(text)[1]
    end
    return table.concat(out) .. "…"
end

local NAME_W = QB.CW - QB.TEXT_PAD * 2
local NAME_W_ICON = QB.CW - QB.NAME_ICON_X - QB.TEXT_PAD

local function NameW(hasIcon)
    if hasIcon then return NAME_W_ICON end
    return NAME_W
end

local function PlayerLevel()
    if type(UnitLevel) ~= "function" then return 0 end
    return UnitLevel("player") or 0
end

local function DungeonRow(d)
    return {
        text = d.name,
        tip = d.name .. "  " .. (d.nameEn or "") .. "\n"
            .. format(L["等级 %d-%d"], d.levelMin or 0, d.levelMax or 0)
            .. " · " .. (d.zone or L["位置未知"]),
        act = "dungeon",
        id = d.id,
    }
end

function QB:Collect()
    local cfg = ns.QuickCfg()
    local DG = ns.ProfHost and ns.ProfHost.DG
    local out = {}
    local n = { dungeon = 0, prof = 0, explore = 0 }

    if cfg.groups.dungeon then
        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }
        out[#out + 1] = { grp = L["推荐五人本"] }
        local lv = PlayerLevel()
        for _, d in ipairs((ns.DungeonData and ns.DungeonData.dungeons) or {}) do
            if DG and d.levelMin and DG.GroupOf(d, lv) == "rec" then
                out[#out + 1] = DungeonRow(d)
                n.dungeon = n.dungeon + 1
            end
        end
        if n.dungeon == 0 then
            out[#out + 1] = { text = L["当前等级暂无推荐副本"], dead = true }
        end
    end

    if cfg.groups.prof and ns.LoadForeverPages then
        out[#out + 1] = { grp = L["专业"] }
        local D = ns.ProfData
        local PD = ns.ProfModule
        local learned = (PD and PD.ProfLearned) and PD.ProfLearned() or {}
        for _, slug in ipairs((D and D.order) or {}) do
            local p = D.pro and D.pro[slug]
            local known = learned[slug]
            if p and (cfg.profMode == "all" or known) then
                local tip = p.name or slug
                if known then
                    tip = tip .. "\n" .. format(L["熟练度 %d/%d"], known.cur or 0, known.max or 0)
                else
                    tip = tip .. "\n" .. L["未学习"]
                end
                out[#out + 1] = {
                    text = p.name or slug,
                    icon = p.icon,
                    tip = tip,
                    act = "prof",
                    slug = slug,
                    known = known and true or false,
                }
                n.prof = n.prof + 1
            end
        end
        if n.prof == 0 then out[#out + 1] = { text = L["未学任何专业"], dead = true } end
    end

    if cfg.groups.explore and ns.LoadForeverPages then
        local picked = {}
        for _, e in ipairs(EXPLORE_DEFS) do
            if cfg.expl[e.key] then picked[#picked + 1] = e end
        end
        if #picked > 0 then
            out[#out + 1] = { grp = L["探索"] }
            for _, e in ipairs(picked) do
                out[#out + 1] = { text = e.text, act = "explore", key = e.key }
                n.explore = n.explore + 1
            end
        end
    end

    self.counts = n
    return out
end

function QB:Scroll(delta)
    local sc = self.scroll
    if not sc then return end
    local maxS = math.max(0, (self.content:GetHeight() or 0) - (sc:GetHeight() or 0))
    local cur = sc:GetVerticalScroll() or 0
    sc:SetVerticalScroll(math.max(0, math.min(maxS, cur - (delta or 0) * 40)))
end

function QB:RowAt(i)
    local r = self.pool[i]
    if r then return r end
    r = CreateFrame("Button", nil, self.content, "BackdropTemplate")
    r:SetSize(self.CW, self.ROW_H)
    r:RegisterForClicks("LeftButtonUp")
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(r) end

    r.iconTile = CreateFrame("Frame", nil, r)
    r.iconTile:SetSize(self.ICON, self.ICON)
    r.iconTile:SetPoint("LEFT", r, "LEFT", self.ICON_X, 0)
    r.icon = r.iconTile:CreateTexture(nil, "ARTWORK")
    r.icon:SetPoint("TOPLEFT", r.iconTile, "TOPLEFT", 0, 0)
    r.icon:SetPoint("BOTTOMRIGHT", r.iconTile, "BOTTOMRIGHT", 0, 0)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.iconTile:Hide()

    r.name = Fs(r, self.FS_NAME, C_TEXT)
    r.name:SetPoint("LEFT", r, "LEFT", self.TEXT_PAD, 0)
    r.name:SetWidth(NAME_W)
    r.name:SetHeight(self.FS_NAME)
    r.name:SetJustifyH("LEFT")
    r.name:SetWordWrap(false)

    r:SetScript("OnEnter", function(self)
        if self.spec and self.spec.tip then
            GameTooltip:SetOwner(self, "ANCHOR_LEFT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(self.spec.tip, 1, 1, 1, true)
            GameTooltip:Show()
        end
    end)
    r:SetScript("OnLeave", function(self)
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function(self) QB:Click(self.spec) end)
    r:EnableMouseWheel(true)
    r:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)

    self.pool[i] = r
    return r
end

local function PopShown(pop)
    return (pop and pop.IsShown and pop:IsShown()) and true or false
end

function QB:SlotX()
    if PopShown(ns.SettingsPopup) then return self.SLOT2 end
    local LF = ns.LootFilterUI
    if LF and LF.ConfigPopup and PopShown(LF:ConfigPopup()) then return self.SLOT2 end
    if ns.ExploreMapConfigPopup and PopShown(ns.ExploreMapConfigPopup()) then return self.SLOT2 end
    if ns.MapModule and ns.MapModule.QuestPinPanel and PopShown(ns.MapModule.QuestPinPanel()) then return self.SLOT2 end
    local bget = ns.GetBisSettingsPop
    if bget and PopShown(bget()) then return self.SLOT2 end
    return self.SLOT1
end

function QB:Reanchor(force)
    local f, host = self.frame, ns.MainFrame
    if not (f and host) then return end
    local x = self:SlotX()
    if not force and self.slotX == x then return end
    self.slotX = x
    f:ClearAllPoints()
    f:SetPoint("TOPLEFT", host, "TOPRIGHT", x, 0)
    f:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", x, 0)
end

function QB:HookSettings()
    self.hookedPops = self.hookedPops or {}
    local function hook(pop)
        if not (pop and pop.HookScript) or self.hookedPops[pop] then return end
        self.hookedPops[pop] = true
        pop:HookScript("OnShow", function() if QB.built then QB:Reanchor() end end)
        pop:HookScript("OnHide", function() if QB.built then QB:Reanchor() end end)
    end
    hook(ns.SettingsPopup)
    local LF = ns.LootFilterUI
    if LF and LF.ConfigPopup then hook(LF:ConfigPopup()) end
    if ns.ExploreMapConfigPopup then hook(ns.ExploreMapConfigPopup()) end
    if ns.MapModule and ns.MapModule.QuestPinPanel then hook(ns.MapModule.QuestPinPanel()) end
end

function QB:Ensure()
    if self.built then return self end
    local host = ns.MainFrame
    if not host then return nil end

    local f = CreateFrame("Frame", "DungeonsForever_QuickBar", host, "BackdropTemplate")
    f:SetWidth(self.W)
    f:SetFrameLevel(512)
    f:EnableMouse(true)
    f:SetScript("OnMouseWheel", function() end)
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then ns.hui.SkinPopup(f, 8, nil, ns.hui.layer.L0) end
    self.frame = f

    local scroll = CreateFrame("ScrollFrame", nil, f)
    scroll:SetPoint("TOPLEFT", f, "TOPLEFT", self.PAD, self.BODY_Y)
    scroll:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -self.PAD, 10)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)

    local content = CreateFrame("Frame", nil, scroll)
    content:SetWidth(self.CW)
    content:SetHeight(10)
    scroll:SetScrollChild(content)
    content:EnableMouseWheel(true)
    content:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)

    if host.HookScript then
        host:HookScript("OnShow", function() if QB.built then QB:Apply() end end)
    end

    self.scroll, self.content = scroll, content
    self.pool, self.grpPool = {}, {}
    self.built = true
    self:HookSettings()
    self:Reanchor(true)
    return self
end

function QB:Render()
    if not self.built then return end
    self:HookSettings()
    self:Reanchor()
    local specs = self:Collect()
    self.specs = specs

    local y, nRow, nGrp = -2, 0, 0
    for _, sp in ipairs(specs) do
        if sp.grp then
            nGrp = nGrp + 1
            local fs = self.grpPool[nGrp]
            if not fs then
                fs = Fs(self.content, self.FS_GRP, C_DIM)
                fs:SetJustifyH("LEFT")
                self.grpPool[nGrp] = fs
            end
            fs:SetText(sp.grp)
            fs:ClearAllPoints()
            fs:SetPoint("TOPLEFT", self.content, "TOPLEFT", self.TEXT_PAD, y - 4)
            fs:Show()
            y = y - self.GRP_H
        else
            nRow = nRow + 1
            local r = self:RowAt(nRow)
            local wantIcon = sp.icon and true or false
            r.spec = sp
            if r.hasIcon ~= wantIcon then
                r.hasIcon = wantIcon
                r.iconTile:SetShown(wantIcon)
                r.name:ClearAllPoints()
                r.name:SetPoint("LEFT", r, "LEFT",
                    wantIcon and self.NAME_ICON_X or self.TEXT_PAD, 0)
            end
            if wantIcon then SetIcon(r.icon, sp.icon) end
            r.name:SetText(Fit(sp.text, NameW(wantIcon), self.FS_NAME))
            if sp.dead then
                r.name:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
            elseif sp.gold then
                r.name:SetTextColor(C_GOLD[1], C_GOLD[2], C_GOLD[3])
            elseif sp.known then
                r.name:SetTextColor(Accent())
            else
                r.name:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3])
            end
            r:SetHeight(self.ROW_H)
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", self.content, "TOPLEFT", 0, y)
            r:Show()
            y = y - self.ROW_H - self.GAP
        end
    end
    for i = nRow + 1, #self.pool do self.pool[i]:Hide() end
    for i = nGrp + 1, #self.grpPool do self.grpPool[i]:Hide() end
    self.content:SetHeight(math.max(10, -y + 6))
    self.rows, self.groups = nRow, nGrp
end

function QB:Click(spec)
    if type(spec) ~= "table" or spec.dead then return end
    ns.PlaySound(1)
    if spec.act == "dungeon" then
        if ns.ShowDungeonDetail then ns.ShowDungeonDetail(spec.id) end
    elseif spec.act == "prof" then
        ns.OpenPage("Professions")
        if ns.ProfModule and ns.ProfModule.Show then ns.ProfModule.Show(spec.slug) end
    elseif spec.act == "explore" then
        ns.OpenPage("Explore")
        if ns.ExploreModule and ns.ExploreModule.ShowSub then
            ns.ExploreModule.ShowSub(spec.key)
        end
    elseif spec.act == "page" then
        ns.OpenPage(spec.key)
    end
end

function QB:Apply()
    local cfg = ns.QuickCfg()
    if ns.ApplyTabVisibility then ns.ApplyTabVisibility() end
    if not cfg.on then
        if self.frame then self.frame:Hide() end
        return
    end
    if not self.built and not self:Ensure() then return end
    self:HookSettings()
    self:Reanchor()
    self:Render()
    self.frame:Show()
end

function QB:Boot()
    if not ns.QuickCfg().on then return end
    if not self:Ensure() then return end
    self.frame:Show()
    local host = ns.MainFrame
    if host and host.IsShown and host:IsShown() then self:Render() end
end

function QB:OnMainShow()
    self:Apply()
end

local SET_PAD, SET_ROW_H, SET_HDR_H = 14, 24, 22

local function Toggle(parent)
    local tg = CreateFrame("CheckButton", nil, parent)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg.label = Fs(parent, 14, C_TEXT)
    tg.label:SetJustifyH("RIGHT")
    tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)
    return tg
end

local function Chip(parent, text, w, h)
    local bt = CreateFrame("Button", nil, parent, "BackdropTemplate")
    bt:SetSize(w, h)
    bt.__huiKeepTextColor = true
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
    bt.label = Fs(bt, 14, C_TEXT)
    bt.label:SetText(text)
    bt.label:SetPoint("CENTER", bt, "CENTER", 0, 0)
    local H = ns.ProfHost
    if H and H.SetButtonSelected then H.SetButtonSelected(bt, false) end
    return bt
end

local function PaintChip(bt, on)
    Outline(bt, on)
    local c = on and C_TEXT or C_DIM
    bt.label:SetTextColor(c[1], c[2], c[3])
end

function QB:EnsureSettings()
    if self.setBuilt then return true end
    local pop = ns.SettingsPopup
    if not pop then return false end

    local set = { group = {}, expl = {}, tabs = {} }
    local y = -44

    local function TogglePair(parent, yv, aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        local at = Toggle(parent)
        if bLabel then
            at:SetPoint("TOPLEFT", parent, "TOPLEFT", SET_PAD - 6, yv)
            at.label:ClearAllPoints()
            at.label:SetPoint("LEFT", at, "RIGHT", 6, 0)
        else
            at:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 6 - SET_PAD, yv)
        end
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
            bt2:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 6 - SET_PAD, yv)
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

        local function mkSetOn(key)
            return function(v)
                local tabs = ns.QuickCfg().tabs
                if not v then
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
            { key = "Factions",    label = L["声望"] },
            { key = "Bis",         label = L["BIS配装"] },
            { key = "Tier",        label = L["职业指南"] },
            { key = "PvP",         label = L["PvP"] },
            { key = "Gear",        label = L["装备库"] },
        }) do
            if ns.LoadForeverPages or def.key == "Dungeons" or def.key == "Raids" then vis[#vis + 1] = def end
        end
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

        set.tabCard = tabCard
        tabCard:SetHeight(8 - ty)
        y = y + ty - 18
    end

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

    local function ToggleRow2(aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        local at, bt2 = TogglePair(host, hy, aLabel, aIsOn, aSetOn, bLabel, bIsOn, bSetOn)
        hy = hy - SET_ROW_H
        return at, bt2
    end

    do
        local hfs = Fs(host, self.FS_AUX, C_DIM)
        hfs:SetPoint("TOPLEFT", host, "TOPLEFT", SET_PAD - 6, hy)
        hfs:SetText(L["快捷按钮栏"])
        set.on = Toggle(host)
        set.on:ClearAllPoints()
        set.on:SetPoint("TOPRIGHT", host, "TOPRIGHT", 6 - SET_PAD, hy)
        set.on:SetChecked(ns.QuickCfg().on and true or false)
        set.on:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            ns.QuickCfg().on = not (ns.QuickCfg().on and true)
            self:SetChecked(ns.QuickCfg().on and true or false)
            QB:SyncSettings()
            QB:Apply()
        end)
        hy = hy - SET_HDR_H
    end

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

    Header(L["探索子页"])
    do
        local a = { key = "books", text = L["40本书"] }
        local b = { key = "bag",   text = L["睡袋"] }
        local ga = function() return ns.QuickCfg().expl[a.key] end
        local sa = function(v) ns.QuickCfg().expl[a.key] = v end
        local gb = function() return ns.QuickCfg().expl[b.key] end
        local sb = function(v) ns.QuickCfg().expl[b.key] = v end
        set.expl[a.key], set.expl[b.key] = ToggleRow2(a.text, ga, sa, b.text, gb, sb)
    end

    if self.cardBg then self.cardBg:SetHeight(8 - hy) end

    self.set, self.setBuilt = set, true
    return true
end

function QB:SyncSettings()
    if not self:EnsureSettings() then return end
    local cfg = ns.QuickCfg()
    local set = self.set

    local function Gate(tg)
        if cfg.on then tg:Enable() else tg:Disable() end
    end

    set.on:SetChecked(cfg.on and true or false)
    for k, tg in pairs(set.group) do
        tg:SetChecked(cfg.groups[k] and true or false)
        Gate(tg)
    end
    for k, tg in pairs(set.expl) do
        tg:SetChecked(cfg.expl[k] and true or false)
        Gate(tg)
    end
    for k, tg in pairs(set.tabs or {}) do
        tg:SetChecked(cfg.tabs[k] ~= false)
    end
    PaintChip(set.chipLearned, cfg.profMode ~= "all")
    PaintChip(set.chipAll, cfg.profMode == "all")
end

ns.Init(function()
    QB:Boot()

    local ev = CreateFrame("Frame")
    ev:RegisterEvent("PLAYER_LEVEL_UP")
    ev:RegisterEvent("PLAYER_ENTERING_WORLD")
    ev:RegisterEvent("SKILL_LINES_CHANGED")
    ev:SetScript("OnEvent", function()
        C_Timer.After(0, function()
        if QB.built then QB:Render() end
        local mf = ns.MainFrame
        if mf and mf.IsShown and mf:IsShown() and not QB.built then QB:Boot() end
        end)
    end)
    QB.events = ev
end)
