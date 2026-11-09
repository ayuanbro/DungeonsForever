local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

local NB = {}
ns.NativeSpellBook = NB

local TAB_ICON = "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp"
local TAB_ICON_FALLBACK = "Interface\\Icons\\INV_Misc_QuestionMark"
local TAB_ICON_WEAPON = "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\WeaponBook.blp"

local TPL_SPELL = "SPELL"
local TPL_HEADER = "HEADER"

local GROUP_ORDER = {
    { key = "available", name = "可学" },
    { key = "next",      name = "即将学" },
    { key = "notlevel",  name = "等级不够" },
    { key = "quest",     name = "任务获得" },
    { key = "talent",    name = "天赋获得" },
    { key = "known",     name = "已学" },
}

local WGROUP_ORDER = {
    { key = "available", name = "可学" },
    { key = "notlevel",  name = "等级不够" },
    { key = "known",     name = "已学" },
}

local book, tabButton, weaponTabButton
local subState = "class"
local activePage
local nativeTpl
local ourProvider
local restoring = false
local lastTab

local pending = false

local function InCombat()
    if type(InCombatLockdown) ~= "function" then return false end
    local ok, v = pcall(InCombatLockdown)
    return ok and v or false
end

local function DeferInCombat()
    if not InCombat() then return false end
    pending = true
    return true
end

local function EUIOn()
    if not EllesmereUI then return false end
    if EllesmereUI.GetBlizzWindowStyle then
        local ok, s = pcall(EllesmereUI.GetBlizzWindowStyle, "playerspells")
        if ok and s then return s ~= "off" end
    end
    return false
end

local function EUIPx()
    if EllesmereUI and EllesmereUI.PanelPP and EllesmereUI.PanelPP.mult then
        return EllesmereUI.PanelPP.mult
    end
    return 1
end

local BOOK_R, BOOK_G, BOOK_B
local function BookTextRGB()
    if BOOK_R then return BOOK_R, BOOK_G, BOOK_B end
    local c = _G.SPELLBOOK_FONT_COLOR
    if c and c.GetRGB then
        BOOK_R, BOOK_G, BOOK_B = c:GetRGB()
    end
    if not BOOK_R then BOOK_R, BOOK_G, BOOK_B = 0.78, 0.66, 0.5 end
    return BOOK_R, BOOK_G, BOOK_B
end

local function ReleaseTip()
    if GameTooltip then GameTooltip:Hide() end
    if ns.hui then ns.hui.nativeTipOwner = nil end
end

local cmpTip, cmpOwner

local function HideCompare()
    if cmpTip then cmpTip:Hide() end
    cmpOwner = nil
end

local function ShowCompare(owner, id)
    if not (owner and id) then
        HideCompare()
        return
    end
    if not cmpTip then
        cmpTip = CreateFrame("GameTooltip", "DungeonsForeverSpellCompareTip", UIParent, "GameTooltipTemplate")
        cmpTip:SetClampedToScreen(true)
    end
    cmpTip:SetOwner(owner, "ANCHOR_NONE")
    cmpTip:ClearLines()
    local ok = pcall(cmpTip.SetSpellByID, cmpTip, id)
    if not ok then
        cmpTip:Hide()
        return
    end
    cmpTip:AddLine(ns.L["已学等级"], 0.5, 0.5, 0.5)
    cmpTip:Show()
    cmpTip:ClearAllPoints()
    local main = GameTooltip
    local screen = (GetScreenWidth and GetScreenWidth()) or 1024
    if main and main:GetRight() and (main:GetRight() + cmpTip:GetWidth()) <= screen then
        cmpTip:SetPoint("TOPLEFT", main, "TOPRIGHT", 0, 0)
    elseif main then
        cmpTip:SetPoint("TOPRIGHT", main, "TOPLEFT", 0, 0)
    end
    cmpOwner = owner
end

local cmpWatch = CreateFrame("Frame")
cmpWatch:SetScript("OnEvent", function()
    if not cmpOwner then
        cmpWatch:UnregisterAllEvents()
        return
    end
    local d = cmpOwner.__d
    if not (d and d.knownId and GameTooltip and GameTooltip:IsShown()) then
        HideCompare()
        cmpWatch:UnregisterAllEvents()
        return
    end
    if IsAltKeyDown() then
        ShowCompare(cmpOwner, d.knownId)
    else
        HideCompare()
    end
end)

local function TrackCompare(owner, id)
    if not id then
        HideCompare()
        return
    end
    if IsAltKeyDown() then
        ShowCompare(owner, id)
        cmpWatch:RegisterEvent("MODIFIER_STATE_CHANGED")
    else
        HideCompare()
    end
end

local function OpenClassQuest(key)
    local CQ = ns.ClassQuestUI
    if not (CQ and CQ.Focus and key) then return false end
    local db = ns.ClassDB and ns.ClassDB()
    if type(db) ~= "table" then db = ns.DB and ns.DB() end
    if db then
        db.tier = db.tier or {}
        db.tier.mode = "cq"
        db.tier.nav = "spec"
        db.tier.cls = select(2, UnitClass("player"))
        db.tier.spec = nil
    end
    if ns.Open then pcall(ns.Open) end
    if ns.OpenPage then pcall(ns.OpenPage, "Tier") end
    pcall(CQ.Focus, key)
    return true
end

local function SpellLink(id)
    local link
    if C_Spell and C_Spell.GetSpellLink then
        link = C_Spell.GetSpellLink(id)
    elseif GetSpellLink then
        link = GetSpellLink(id)
    end
    return link
end

local function InsertLink(id)
    local link = SpellLink(id)
    if not link then return end
    local done
    if ChatFrameUtil and ChatFrameUtil.InsertLink then
        done = ChatFrameUtil.InsertLink(link)
    elseif ChatEdit_InsertLink then
        done = ChatEdit_InsertLink(link)
    end
    if not done and ChatFrame_OpenChat then
        ChatFrame_OpenChat(link, SELECTED_DOCK_FRAME)
    end
end

local ART
local function SquareArt()
    if ART == nil then
        ART = (SpellBookItemMixin and SpellBookItemMixin.ArtSet and SpellBookItemMixin.ArtSet.Square) or false
    end
    return ART or nil
end

local function ItemOf(btn)
    if not btn then return nil end
    if btn.__item then return btn.__item end
    if btn.GetParent then return btn:GetParent() end
    return nil
end

local function ItemEnter(btn)
    local frame = ItemOf(btn)
    local d = frame and frame.__d
    if not d then return end
    local GT = GameTooltip
    if not GT then return end
    if ns.hui then ns.hui.nativeTipOwner = frame end
    GT:SetOwner(btn or frame, "ANCHOR_RIGHT")
    GT:ClearLines()
    local ok = false
    if d.spellID and type(GT.SetSpellByID) == "function" then
        ok = pcall(GT.SetSpellByID, GT, d.spellID)
    end
    if not ok then GT:SetText(d.name or "", 1, 1, 1) end
    if d.trainer then
        local tr = d.trainer
        GT:AddLine(format("%s %s %.1f, %.1f", d.sub or "", tr.zoneName or "", tr.x or 0, tr.y or 0), 0.9, 0.9, 0.9)
        GT:AddLine(ns.L["点击：在地图上标记该训练师"], 1, 0.82, 0, true)
    end
    if d.quest then
        local q = d.quest
        if q.name then
            GT:AddLine(format("%s %s", ns.L["任务"], q.name), 1, 0.82, 0)
        end
        if q.npc and q.zone then
            GT:AddLine(format("%s %s %.1f, %.1f", q.npc, q.zone, q.x or 0, q.y or 0), 0.9, 0.9, 0.9)
        end
        GT:AddLine(ns.L["左键：打开职业任务页"], 1, 0.82, 0, true)
        GT:AddLine(ns.L["右键：在地图上标记"], 1, 0.82, 0, true)
    end
    if ns.hui and ns.hui.ShowNativeTip then ns.hui.ShowNativeTip(GT) end
    GT:Show()
    TrackCompare(frame, d.knownId)
    if frame.Button and frame.Button.IconHighlight and not EUIOn() then
        frame.Button.IconHighlight:SetAlpha(1)
    end
end

local function ItemLeave(btn)
    HideCompare()
    cmpWatch:UnregisterAllEvents()
    ReleaseTip()
    local frame = ItemOf(btn)
    if frame and frame.Button and frame.Button.IconHighlight and not EUIOn() then
        frame.Button.IconHighlight:SetAlpha(frame.iconHighlightHoverAlpha or 0.35)
    end
end

local function ItemClick(btn, button)
    local frame = ItemOf(btn)
    local d = frame and frame.__d
    if not d then return end
    if d.quest then
        if button == "RightButton" then
            if ns.WeaponMasters then ns.WeaponMasters.MarkNPC(d.quest) end
        else
            OpenClassQuest(d.quest.key)
        end
        return
    end
    if d.trainer then
        if ns.WeaponMasters then ns.WeaponMasters.MarkNPC(d.trainer) end
        return
    end
    if not d.spellID or not IsShiftKeyDown() then return end
    InsertLink(d.spellID)
end

local function ItemInit(frame, d)
    frame.elementData = d
    frame.spellBookItemInfo = nil
    if frame.ClearSpellData then pcall(frame.ClearSpellData, frame) end

    local art = SquareArt()
    frame.artSet = art
    local dim = d.dim == true
    local eui = EUIOn()

    frame.Name:SetText(d.name or "")
    frame.SubName:SetText(d.sub or "")
    frame.RequiredLevel:SetText(d.req or "")
    frame.RequiredLevel:SetShown((d.req or "") ~= "")

    local tr, tg, tb2 = 1, 1, 1
    if not eui then tr, tg, tb2 = BookTextRGB() end
    local txt = 1
    if dim then txt = eui and 0.55 or (frame.unlearnedTextAlpha or 0.6) end
    for _, fs in ipairs({ frame.Name, frame.SubName, frame.RequiredLevel }) do
        fs:SetTextColor(tr, tg, tb2)
        fs:SetAlpha(txt)
    end

    local btn = frame.Button
    local icon = d.icon
    if type(icon) == "string" then
        if icon ~= "" and icon:sub(1, 9) ~= "Interface" then icon = "Interface\\Icons\\" .. icon end
    elseif type(icon) ~= "number" then
        icon = nil
    end
    btn.Icon:SetTexture(icon or TAB_ICON_FALLBACK)
    btn.Icon:SetVertexColor(1, 1, 1)
    btn.Icon:SetDesaturated(dim)
    btn.Icon:SetAlpha(dim and (frame.unlearnedIconAlpha or 0.6) or 1)

    if art then
        local border = dim and art.inactiveBorder or art.activeBorder
        local anchors = dim and art.inactiveBorderAnchors or art.activeBorderAnchors
        pcall(frame.ApplyBorderArt, frame, border, anchors)
        if btn.IconMask and art.iconMask then
            pcall(btn.IconMask.SetAtlas, btn.IconMask, art.iconMask, false)
            btn.IconMask:Show()
        end
        if btn.IconHighlight and art.iconHighlight then
            pcall(btn.IconHighlight.SetAtlas, btn.IconHighlight, art.iconHighlight, false)
        end
        if frame.ApplyBorderSheenMaskArt then pcall(frame.ApplyBorderSheenMaskArt, frame) end
    end

    if btn.Border then
        if eui then
            btn.Border:SetAlpha(0.5)
            if btn.Border.SetDesaturation then btn.Border:SetDesaturation(0.5) end
        else
            btn.Border:SetAlpha(1)
            if btn.Border.SetDesaturation then btn.Border:SetDesaturation(0) end
        end
    end
    if btn.BorderShadow then btn.BorderShadow:SetAlpha(eui and 0 or 1) end
    if btn.IconHighlight then
        btn.IconHighlight:SetAlpha(eui and 0 or (frame.iconHighlightHoverAlpha or 0.35))
    end
    if frame.Backplate then
        frame.Backplate:SetAlpha(eui and 0 or (frame.defaultBackplateAlpha or 0.25))
    end

    if frame.UpdateTextContainer then pcall(frame.UpdateTextContainer, frame) end

    frame.__d = d
    btn.__item = frame
    btn:SetScript("OnEnter", ItemEnter)
    btn:SetScript("OnLeave", ItemLeave)
    btn:SetScript("OnClick", ItemClick)
    btn:SetScript("OnMouseDown", nil)
    btn:SetScript("OnMouseUp", nil)
    btn:SetScript("OnDragStart", nil)

    local ov = frame.__ov
    if not ov then
        ov = CreateFrame("Button", nil, frame)
        ov:SetAllPoints(frame)
        ov:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        ov:SetScript("OnEnter", ItemEnter)
        ov:SetScript("OnLeave", ItemLeave)
        ov:SetScript("OnClick", ItemClick)
        frame.__ov = ov
        local lvl = 1
        if btn.GetFrameLevel then
            local okL, bl = pcall(btn.GetFrameLevel, btn)
            if okL and bl then lvl = math.max(1, bl - 1) end
        end
        ov:SetFrameLevel(lvl)
    end
    ov.__item = frame
    ov:EnableMouse(true)
    ov:Show()
end

local function RestoreFrame(frame)
    if not frame then return end
    frame.__d = nil
    if frame.__ov then
        frame.__ov:EnableMouse(false)
        frame.__ov:Hide()
    end
    local eui = EUIOn()
    if frame.Text and frame.Border then
        local hr, hg, hb = 1, 1, 1
        if not eui then hr, hg, hb = BookTextRGB() end
        frame.Text:SetTextColor(hr, hg, hb)
        if frame.Backplate then frame.Backplate:SetAlpha(eui and 0 or 0.65) end
        frame.Border:SetAlpha(eui and 0 or 1)
        if frame.__dfLine then frame.__dfLine:SetShown(eui) end
    end
    local btn = frame.Button
    if not btn then return end
    btn.__item = nil
    if SpellBookItemButtonMixin then
        btn:SetScript("OnEnter", SpellBookItemButtonMixin.OnEnter)
        btn:SetScript("OnLeave", SpellBookItemButtonMixin.OnLeave)
        btn:SetScript("OnClick", SpellBookItemButtonMixin.OnClick)
        btn:SetScript("OnMouseDown", SpellBookItemButtonMixin.OnMouseDown)
        btn:SetScript("OnMouseUp", SpellBookItemButtonMixin.OnMouseUp)
        btn:SetScript("OnDragStart", SpellBookItemButtonMixin.OnDragStart)
    end
    if btn.Icon then
        btn.Icon:SetDesaturated(false)
        btn.Icon:SetAlpha(1)
        btn.Icon:SetVertexColor(1, 1, 1)
    end
    if btn.Border then
        btn.Border:SetAlpha(eui and 0.5 or 1)
        if btn.Border.SetDesaturation then btn.Border:SetDesaturation(eui and 0.5 or 0) end
    end
    if btn.BorderShadow then btn.BorderShadow:SetAlpha(eui and 0 or 1) end
    if btn.IconHighlight then
        btn.IconHighlight:SetAlpha(eui and 0 or (frame.iconHighlightHoverAlpha or 0.35))
    end
    if frame.Backplate then frame.Backplate:SetAlpha(eui and 0 or 0.25) end
    local ir, ig, ib = 1, 1, 1
    if not eui then ir, ig, ib = BookTextRGB() end
    if frame.Name then
        frame.Name:SetAlpha(1)
        frame.Name:SetTextColor(ir, ig, ib)
        ns.ThinFont(frame.Name)
    end
    if frame.SubName then
        frame.SubName:SetAlpha(1)
        frame.SubName:SetTextColor(ir, ig, ib)
        ns.ThinFont(frame.SubName)
    end
    if frame.RequiredLevel then
        frame.RequiredLevel:SetAlpha(1)
        frame.RequiredLevel:SetTextColor(ir, ig, ib)
        ns.ThinFont(frame.RequiredLevel)
    end
end

local function ItemReset(pool, frame)
    if SpellBookItemMixin and SpellBookItemMixin.Reset then
        pcall(SpellBookItemMixin.Reset, pool, frame)
    end
    RestoreFrame(frame)
end

local function HeaderInit(frame, d)
    local eui = EUIOn()
    if frame.Text then
        frame.Text:SetText(d.text or "")
        local r, g, b = 1, 1, 1
        if not eui then r, g, b = BookTextRGB() end
        frame.Text:SetTextColor(r, g, b)
        frame.Text:SetAlpha(1)
        ns.ThinFont(frame.Text)
    end
    if frame.Backplate then
        frame.Backplate:SetAlpha(eui and 0 or 0.65)
    end
    local border = frame.Border
    if border then
        if eui then
            border:SetAlpha(0)
            local line = frame.__dfLine
            if not line then
                line = frame:CreateTexture(nil, "OVERLAY")
                line:SetColorTexture(1, 1, 1, 0.25)
                frame.__dfLine = line
            end
            line:SetHeight(EUIPx())
            line:ClearAllPoints()
            line:SetPoint("LEFT", border, "LEFT", 20, 0)
            line:SetPoint("RIGHT", border, "RIGHT", 0, 0)
            line:Show()
        else
            border:SetAlpha(1)
            if frame.__dfLine then frame.__dfLine:Hide() end
        end
    end
end

local OURS = {
    [TPL_HEADER] = {
        template = "SpellBookHeaderTemplate",
        initFunc = HeaderInit,
    },
    [TPL_SPELL] = {
        template = "SpellBookItemTemplate",
        initFunc = ItemInit,
        resetFunc = ItemReset,
    },
}

local function Paged()
    if not book then
        local psf = PlayerSpellsFrame
        local sb = psf and psf.SpellBookFrame
        if sb then book = sb end
    end
    return book and book.PagedSpellsFrame
end

local function LevelText(lv)
    if not lv then return "" end
    return format(ns.L["人物 %d 级"], lv)
end

local function QuestWhere(q)
    if q.zone and q.x then
        return format("%s %.1f, %.1f", q.zone, q.x, q.y or 0)
    end
    return LevelText(q.lv)
end

local function BuildSpellGroups()
    local st = ns.SpellTraining
    if not (st and st.Rows) then return nil end
    local rows, plv = st.Rows()
    if not rows then return nil end
    local groups = {}
    for _, gd in ipairs(GROUP_ORDER) do
        local g = rows[gd.key] or {}
        if #g > 0 then
            local elements = {}
            for _, row in ipairs(g) do
                local el = {
                    templateKey = TPL_SPELL,
                    name = row.name,
                    icon = row.icon,
                    spellID = row.id,
                    knownId = row.knownId,
                }
                if row.quest then
                    el.quest = row.quest
                    el.sub = row.quest.name or ""
                    el.req = QuestWhere(row.quest)
                    el.dim = (gd.key == "notlevel") or ((row.quest.lv or 0) > plv)
                else
                    el.sub = (row.rank and format(ns.L["等级 %d"], row.rank)) or ((row.tab and row.tab ~= row.name) and row.tab) or ""
                    el.req = gd.known and ns.L["已学"] or LevelText(row.learn)
                    el.dim = (gd.key == "notlevel")
                end
                elements[#elements + 1] = el
            end
            groups[#groups + 1] = {
                header = { templateKey = TPL_HEADER, text = ns.L[gd.name] },
                elements = elements,
            }
        end
    end
    return groups
end

local function BuildWeaponGroups()
    local wm = ns.WeaponMasters
    if not (wm and wm.Rows) then return nil end
    local rows = wm.Rows()
    if not rows then return nil end
    local groups = {}
    for _, gd in ipairs(WGROUP_ORDER) do
        local g = rows[gd.key] or {}
        if #g > 0 then
            local elements = {}
            for _, row in ipairs(g) do
                local trainers = row.trainers or {}
                if #trainers == 0 then
                    elements[#elements + 1] = {
                        templateKey = TPL_SPELL,
                        name = row.name,
                        icon = row.icon,
                        sub = "",
                        req = ns.L["未收录该训练师的地图位置"],
                        spellID = row.id,
                        dim = true,
                    }
                else
                    for _, tr in ipairs(trainers) do
                        elements[#elements + 1] = {
                            templateKey = TPL_SPELL,
                            name = row.name,
                            icon = row.icon,
                            sub = tr.name or "",
                            req = format("%s %.1f, %.1f", tr.zoneName or "", tr.x or 0, tr.y or 0),
                            spellID = row.id,
                            trainer = tr,
                            dim = (gd.key == "notlevel"),
                        }
                    end
                end
            end
            groups[#groups + 1] = {
                header = { templateKey = TPL_HEADER, text = ns.L[gd.name] },
                elements = elements,
            }
        end
    end
    return groups
end

local function EmptyGroup()
    return { { elements = {} } }
end

local function ClassGroups()
    local ct = ns.ClassTrainers
    if ct and ct.Groups then
        local g = ct.Groups()
        if g and #g > 0 then return g end
    end
    return nil
end

local function ThinAll()
    local paged = Paged()
    if not paged then return end
    local function scan(f, d)
        if d > 6 then return end
        local regions = { f:GetRegions() }
        for i = 1, #regions do
            local r = regions[i]
            if r.GetObjectType and r:GetObjectType() == "FontString" then
                ns.ThinFont(r)
            end
        end
        local kids = { f:GetChildren() }
        for i = 1, #kids do
            scan(kids[i], d + 1)
        end
    end
    pcall(scan, paged, 0)
end

local function InstallOurs()
    if DeferInCombat() then return false end
    local paged = Paged()
    if not paged then return false end
    local groups
    if activePage == "weapon" then
        if subState == "weapon" then
            groups = BuildWeaponGroups()
        else
            groups = ClassGroups()
        end
    else
        groups = BuildSpellGroups()
    end
    if not groups or #groups == 0 then groups = EmptyGroup() end
    paged:SetElementTemplateData(OURS)
    paged:SetDataProvider(CreateDataProvider(groups), false)
    ourProvider = paged.dataProvider
    C_Timer.After(0, ThinAll)
    C_Timer.After(0.15, ThinAll)
    return true
end

local subBar, subClassBtn, subWeaponBtn

local function PageBox()
    local paged = Paged()
    if not paged then return nil end
    for _, ch in ipairs({ paged:GetChildren() }) do
        local n = 0
        for _, c2 in ipairs({ ch:GetChildren() }) do
            if c2.IsObjectType and c2:IsObjectType("Button") then n = n + 1 end
        end
        if n >= 2 then return ch end
    end
    return nil
end

local function SubPaint()
    local items = { { subClassBtn, subState == "class" }, { subWeaponBtn, subState == "weapon" } }
    for _, it in ipairs(items) do
        local b, sel = it[1], it[2]
        if b then
            if b.label then
                if sel then
                    b.label:SetTextColor(1, 0.86, 0.45)
                else
                    b.label:SetTextColor(0.72, 0.68, 0.58)
                end
            end
            if sel and b.LockHighlight then
                b:LockHighlight()
            elseif b.UnlockHighlight then
                b:UnlockHighlight()
            end
        end
    end
end

local function SetSub(key)
    if subState == key then return end
    subState = key
    SubPaint()
    if activePage == "weapon" then InstallOurs() end
end

local function BuildSubBar()
    if subBar then return subBar end
    local paged = Paged()
    if not paged then return nil end
    local box = PageBox()
    local host = box or paged
    subBar = CreateFrame("Frame", nil, host)
    subBar:SetSize(190, 32)
    if box then
        subBar:SetPoint("BOTTOMRIGHT", box, "BOTTOMLEFT", -6, 0)
    else
        subBar:SetPoint("BOTTOMLEFT", paged, "BOTTOMLEFT", 10, 2)
    end
    local function mk(name, text, key, w)
        local b = CreateFrame("Button", name, subBar, "UIPanelButtonTemplate")
        b:SetSize(w, 32)
        b:SetText("")
        local fs = b:CreateFontString(nil, "OVERLAY")
        fs:SetFont(ns.FONT, 13, "")
        fs:SetPoint("CENTER", b, "CENTER", 0, 0)
        fs:SetText(text)
        b.label = fs
        b:SetScript("OnClick", function() SetSub(key) end)
        if ns.NDuiOn and ns.NDuiOn() then ns.NDuiReskin(b) end
        return b
    end
    subClassBtn = mk("DungeonsForeverSubClass", ns.L["职业训练师"], "class", 94)
    subClassBtn:SetPoint("LEFT", subBar, "LEFT", 0, 0)
    subWeaponBtn = mk("DungeonsForeverSubWeapon", ns.L["武器大师"], "weapon", 86)
    subWeaponBtn:SetPoint("LEFT", subClassBtn, "RIGHT", 3, 0)
    SubPaint()
    return subBar
end

local function SyncSubBar(show)
    if DeferInCombat() then return end
    local bar = BuildSubBar()
    if not bar then return end
    if show then
        bar:Show()
    else
        bar:Hide()
    end
end

local function RestoreNative()
    if DeferInCombat() then return end
    local paged = Paged()
    if not (paged and nativeTpl) then return end
    local wasOurs = (ourProvider ~= nil and paged.dataProvider == ourProvider)
    paged:SetElementTemplateData(nativeTpl)
    restoring = true
    if book and book.UpdateDisplayedSpells then
        pcall(book.UpdateDisplayedSpells, book, true, true)
    end
    if wasOurs and paged.dataProvider == ourProvider and book and book.UpdateAllSpellData then
        pcall(book.UpdateAllSpellData, book, true)
    end
    restoring = false
    ourProvider = nil
    for _, v in ipairs({ paged.View1, paged.View2 }) do
        if v then
            for _, f in ipairs({ v:GetChildren() }) do
                RestoreFrame(f)
            end
        end
    end
end

local function ApplyData()
    if activePage then
        InstallOurs()
    else
        RestoreNative()
    end
end

local ShowPage

local tabLineH

local function TabLine(tb)
    if not tb then return nil end
    for _, r in ipairs({ tb:GetRegions() }) do
        if r and r.IsObjectType and r:IsObjectType("Texture") then
            local h = r:GetHeight() or 0
            local w = r:GetWidth() or 0
            if h > 0 and h <= 3 and w >= 20 then return r end
        end
    end
end

local function LineHeight()
    if tabLineH then return tabLineH end
    local sys = book and book.CategoryTabSystem
    for _, t in ipairs((sys and sys.tabs) or {}) do
        local u = TabLine(t)
        if u then
            tabLineH = u:GetHeight() or 1
            return tabLineH
        end
    end
    return 1
end

local function LineRGB()
    local db = EllesmereUIDB and EllesmereUIDB.blizzWinAccentBar
    if db then
        if db.enabled == false then return nil end
        if db.useCustom and db.color then
            local c = db.color
            return c.r or 1, c.g or 1, c.b or 1
        end
    end
    local g = EllesmereUI and EllesmereUI.ELLESMERE_GREEN
    if g then return g.r or 1, g.g or 1, g.b or 1 end
    return 1, 1, 1
end

local function TabLineShow(tb, on)
    if not tb then return end
    local line = tb.__dfLine
    if not line then
        if not EUIOn() then return end
        if not LineRGB() then return end
        line = tb:CreateTexture(nil, "OVERLAY", nil, 6)
        line:SetPoint("BOTTOMLEFT", tb, "BOTTOMLEFT", 0, 0)
        line:SetPoint("BOTTOMRIGHT", tb, "BOTTOMRIGHT", 0, 0)
        line:SetHeight(LineHeight())
        tb.__dfLine = line
    end
    local r, g, b = LineRGB()
    if not r then
        line:Hide()
        return
    end
    line:SetColorTexture(r, g, b, 1)
    if on and EUIOn() then line:Show() else line:Hide() end
end

local function StyleOurTab(tb, sel)
    if not tb then return end
    if tb.SetSquareMode then pcall(tb.SetSquareMode, tb, true) end
    if tb.SetTabSelected then pcall(tb.SetTabSelected, tb, sel and true or false) end
    if tb.Enable then pcall(tb.Enable, tb) end
    if tb.Icon then tb.Icon:Show() end
    if tb.IconMask then tb.IconMask:Show() end
    TabLineShow(tb, sel)
end

local function PaintTabs()
    if DeferInCombat() then return end
    if not book then return end
    local shown = activePage ~= nil
    StyleOurTab(tabButton, shown and activePage == "spell")
    StyleOurTab(weaponTabButton, shown and activePage == "weapon")
    local sys = book.CategoryTabSystem
    for _, tab in ipairs((sys and sys.tabs) or {}) do
        if not tab.__dfClick then
            tab.__dfClick = true
            tab:HookScript("OnClick", function()
                if activePage then ShowPage(nil) end
            end)
        end
        local active = not shown and tab:IsSelected()
        if tab.SquareBackground then tab.SquareBackground:SetShown(not active) end
        if tab.SquareBackgroundActive then tab.SquareBackgroundActive:SetShown(active) end
        if tab.SquareBackgroundActiveGlow then tab.SquareBackgroundActiveGlow:SetShown(active) end
        local ul = TabLine(tab)
        if ul then ul:SetShown(active) end
        if tab.SetEnabled then tab:SetEnabled(not tab:IsForceDisabled()) end
    end
end

ShowPage = function(key)
    if DeferInCombat() then return end
    if not book then return end
    if not nativeTpl then
        local paged = Paged()
        if paged then nativeTpl = paged.elementTemplateData end
    end
    if not nativeTpl then return end
    if activePage == key then
        if key then ApplyData() end
        return
    end
    activePage = key
    local shown = key ~= nil
    if book.SearchBox then book.SearchBox:SetShown(not shown) end
    if book.SettingsDropdown then book.SettingsDropdown:SetShown(not shown) end
    if book.SearchPreviewContainer then book.SearchPreviewContainer:Hide() end
    PaintTabs()
    SyncSubBar(key == "weapon")
    ApplyData()
    if NB.OnPage then NB.OnPage(activePage) end
end

local function OnTabClick(key)
    if InCombatLockdown then
        local ok, busy = pcall(InCombatLockdown)
        if ok and busy then
            print(ns.L["战斗中无法打开训练师"])
            return
        end
    end
    if SOUNDKIT and SOUNDKIT.U_CHAT_SCROLL_BUTTON then
        pcall(PlaySound, SOUNDKIT.U_CHAT_SCROLL_BUTTON)
    end
    ShowPage(activePage == key and nil or key)
    if C_Timer and C_Timer.After then
        C_Timer.After(0, PaintTabs)
        C_Timer.After(0.6, PaintTabs)
    end
end

local function GetSystem()
    local sb = book
    if not sb then
        local psf = PlayerSpellsFrame
        sb = psf and psf.SpellBookFrame
    end
    return sb, (sb and sb.CategoryTabSystem)
end

local function IsForeignTab(ch, sys)
    if ch == tabButton or ch == weaponTabButton or ch == sys then return false end
    if not (ch.IsObjectType and ch:IsObjectType("Button")) then return false end
    if not ch.Icon then return false end
    if ch.IsShown and not ch:IsShown() then return false end
    return true
end

function NB.OthersOccupied()
    local _, sys = GetSystem()
    if not sys then return false end
    local nativeSet, known = {}, 0
    for _, t in ipairs(sys.tabs or {}) do
        nativeSet[t] = true
        known = known + 1
    end
    local total, foreign = 0, 0
    for _, ch in ipairs({ sys:GetChildren() }) do
        if IsForeignTab(ch, sys) then
            total = total + 1
            if not nativeSet[ch] then foreign = foreign + 1 end
        end
    end
    if known > 0 then return foreign > 0 end
    local native = 0
    if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines then
        local ok, n = pcall(C_SpellBook.GetNumSpellBookSkillLines)
        if ok and type(n) == "number" then native = n end
    end
    if native <= 0 then return false end
    return total > native
end

local function LastForeignTab()
    local _, sys = GetSystem()
    if not (sys and sys.GetRight) then return nil end
    local sr = sys:GetRight()
    if not sr or sr < 2 then return nil end
    local best, bestRight
    for _, ch in ipairs({ sys:GetChildren() }) do
        if IsForeignTab(ch, sys) and ch.IsShown and ch:IsShown() and ch.GetRight then
            local r = ch:GetRight()
            if r and r > sr and (not bestRight or r > bestRight) then
                best, bestRight = ch, r
            end
        end
    end
    return best
end

local function AnchorTabs()
    if DeferInCombat() then return end
    if not tabButton or not book then return end
    local host = LastForeignTab()
    local key = host or false
    if tabButton.__anchorHost == key then return end
    tabButton.__anchorHost = key
    tabButton:ClearAllPoints()
    if host then
        tabButton:SetPoint("LEFT", host, "RIGHT", 1, 0)
    else
        tabButton:SetPoint("LEFT", book.CategoryTabSystem, "RIGHT", 1, 0)
    end
end

local function ReparentTabs()
    local psf = PlayerSpellsFrame
    local sys = book and book.CategoryTabSystem
    if not (psf and sys and tabButton) then return end
    local sc = 1
    if sys.GetEffectiveScale and psf.GetEffectiveScale then
        local a, b = sys:GetEffectiveScale(), psf:GetEffectiveScale()
        if a and b and a > 0 and b > 0 then sc = a / b end
    end
    local lv = sys:GetFrameLevel() + 5
    local strata = sys:GetFrameStrata()
    if tabButton:GetParent() ~= psf then
        tabButton:SetParent(psf)
        tabButton:SetScale(sc)
        tabButton:SetFrameStrata(strata)
        tabButton:SetFrameLevel(lv)
        tabButton.__anchorHost = false
        tabButton:ClearAllPoints()
        tabButton:SetPoint("LEFT", sys, "RIGHT", 1, 0)
    end
    if weaponTabButton and weaponTabButton:GetParent() ~= psf then
        weaponTabButton:SetParent(psf)
        weaponTabButton:SetScale(sc)
        weaponTabButton:SetFrameStrata(strata)
        weaponTabButton:SetFrameLevel(lv)
        weaponTabButton.__anchorHost = nil
    end
end

local function Attach()
    if DeferInCombat() then return false end
    local psf = PlayerSpellsFrame
    local sb = psf and psf.SpellBookFrame
    if not (sb and sb.CategoryTabSystem and sb.PagedSpellsFrame) then return false end
    if book and tabButton then return true end
    if psf and psf.HookScript and not psf.__dfThin then
        psf.__dfThin = true
        psf:HookScript("OnShow", function()
            C_Timer.After(0, ThinAll)
            C_Timer.After(0.1, ThinAll)
            C_Timer.After(0.3, ThinAll)
        end)
    end
    book = sb
    nativeTpl = sb.PagedSpellsFrame.elementTemplateData

    tabButton = CreateFrame("Button", "DungeonsForeverSpellBookTab", sb.CategoryTabSystem,
                            "SpellBookCategoryTabTemplate")
    local iconFile = TAB_ICON_FALLBACK
    if GetFileIDFromPath then
        local ok, id = pcall(GetFileIDFromPath, TAB_ICON)
        if ok and id and id ~= 0 then iconFile = TAB_ICON end
    end
    tabButton:Init(0, nil, iconFile)
    tabButton:SetPoint("LEFT", sb.CategoryTabSystem, "RIGHT", 1, 0)
    tabButton:SetTooltipText(ns.L["职业技能"])
    tabButton:SetScript("OnClick", function() OnTabClick("spell") end)

    local wIconFile = TAB_ICON_FALLBACK
    if GetFileIDFromPath then
        local ok, wid = pcall(GetFileIDFromPath, TAB_ICON_WEAPON)
        if ok and wid and wid ~= 0 then wIconFile = TAB_ICON_WEAPON end
    end
    weaponTabButton = CreateFrame("Button", "DungeonsForeverWeaponBookTab", sb.CategoryTabSystem,
                                  "SpellBookCategoryTabTemplate")
    weaponTabButton:Init(0, nil, wIconFile)
    weaponTabButton:SetPoint("LEFT", tabButton, "RIGHT", 1, 0)
    weaponTabButton:SetTooltipText(ns.L["训练师"])
    weaponTabButton:SetScript("OnClick", function() OnTabClick("weapon") end)

    lastTab = sb.GetTab and sb:GetTab()
    ReparentTabs()

    local function FitSearchBoxNow()
        if DeferInCombat() then return end
        local box = book and book.SearchBox
        if not box then return end
        local rightmost = weaponTabButton or tabButton
        local left, right = rightmost and rightmost:GetRight(), box:GetRight()
        if left and right then
            box:SetWidth(math.max(1, math.min(300, right - left - 10)))
        end
    end

    local function FitSearchBox()
        if C_Timer and C_Timer.After then
            C_Timer.After(0, FitSearchBoxNow)
            C_Timer.After(0.2, FitSearchBoxNow)
        else
            FitSearchBoxNow()
        end
    end

    local function OnSpellsRefresh()
        if restoring or not book then return end
        local id = book.GetTab and book:GetTab()
        if id ~= lastTab then
            lastTab = id
            if activePage then ShowPage(nil) end
            return
        end
        if activePage then
            InstallOurs()
        elseif C_Timer and C_Timer.After then
            C_Timer.After(0, ThinAll)
        end
        FitSearchBox()
    end

    local function DeferRefresh()
        if C_Timer and C_Timer.After then
            C_Timer.After(0, OnSpellsRefresh)
        else
            OnSpellsRefresh()
        end
    end

    if EventRegistry and EventRegistry.RegisterCallback then
        pcall(EventRegistry.RegisterCallback,
            "PlayerSpellsFrame.SpellBookFrame.DisplayedSpellsChanged", DeferRefresh, tabButton)
    end
    if sb.HookScript then
        sb:HookScript("OnSizeChanged", function()
            if DeferInCombat() then return end
            ReparentTabs()
            AnchorTabs()
            FitSearchBox()
        end)
    end
    sb:HookScript("OnShow", function()
        if DeferInCombat() then return end
        if NB.RefreshEnabled then NB.RefreshEnabled() end
        ReparentTabs()
        AnchorTabs()
        if sb.ResizeSearchBox then pcall(sb.ResizeSearchBox, sb) end
        SyncSubBar(activePage == "weapon")
        if activePage then InstallOurs() end
        PaintTabs()
        if C_Timer and C_Timer.After then
            C_Timer.After(0.3, PaintTabs)
            C_Timer.After(1.2, PaintTabs)
            C_Timer.After(1.2, function()
                if NB.RefreshEnabled then NB.RefreshEnabled() end
            end)
        end
    end)
    AnchorTabs()
    return true
end

local retryTimer, retryLeft = nil, 0

local function ApplyEnabled()
    if DeferInCombat() then return false end
    local on = ns.SpellEnhOn and ns.SpellEnhOn()
    if on then
        if not (book and tabButton) then Attach() end
        if not (book and tabButton) then
            if retryLeft > 0 and not retryTimer and C_Timer and C_Timer.After then
                retryLeft = retryLeft - 1
                retryTimer = C_Timer.After(1.0, function()
                    retryTimer = nil
                    if ns.SpellEnhOn and ns.SpellEnhOn() then ApplyEnabled() end
                end)
            end
            return false
        end
        retryLeft = 0
        tabButton:Show()
        if weaponTabButton then weaponTabButton:Show() end
        AnchorTabs()
        return true
    end
    if activePage then ShowPage(nil) end
    if tabButton then tabButton:Hide() end
    if weaponTabButton then weaponTabButton:Hide() end
    return false
end

function NB.SetEnabled(on)
    if DeferInCombat() then return end
    if on then
        retryLeft = 6
        if not (book and tabButton) then Attach() end
        if tabButton then tabButton:Show() end
        if weaponTabButton then weaponTabButton:Show() end
        AnchorTabs()
        if not tabButton then ApplyEnabled() end
    else
        retryLeft = 0
        if activePage then ShowPage(nil) end
        if tabButton then tabButton:Hide() end
        if weaponTabButton then weaponTabButton:Hide() end
    end
end

function NB.SetWeaponEnabled(on)
    if DeferInCombat() then return end
    if on then
        retryLeft = 6
        if not (book and tabButton) then Attach() end
        if weaponTabButton then weaponTabButton:Show() end
    else
        if activePage == "weapon" then ShowPage(nil) end
        if weaponTabButton then weaponTabButton:Hide() end
    end
end

function NB.SetSubTab(key)
    if key ~= "spell" and key ~= "weapon" then return end
    if activePage == key then return end
    ShowPage(key)
end

function NB.RefreshEnabled()
    retryLeft = 6
    return ApplyEnabled()
end

local function FlushPending()
    if not pending then return end
    pending = false
    if activePage then InstallOurs() end
    PaintTabs()
    AnchorTabs()
    SyncSubBar(activePage == "weapon")
    ApplyEnabled()
end

local flush = CreateFrame("Frame")
flush:RegisterEvent("PLAYER_REGEN_ENABLED")
flush:SetScript("OnEvent", function() FlushPending() end)

function NB.Refresh()
    if activePage then InstallOurs() end
    AnchorTabs()
end

function NB.CurrentPage()
    return activePage
end

function NB.ContentBox()
    return PageBox()
end

function NB.Page(delta)
    if DeferInCombat() then return end
    local paged = Paged()
    local pc = paged and paged.PagingControls
    if not (pc and activePage) then return end
    if delta < 0 then
        pc:PreviousPage()
    else
        pc:NextPage()
    end
end

if ns.SpellTraining then
    ns.SpellTraining.OnDirty = function()
        if activePage then InstallOurs() end
    end
end

ns.Init(function()
    retryLeft = 6
    if IsLoggedIn and IsLoggedIn() then ApplyEnabled() end
    if EventUtil and EventUtil.ContinueOnAddOnLoaded then
        EventUtil.ContinueOnAddOnLoaded("Blizzard_PlayerSpells", function()
            ApplyEnabled()
        end)
    end
    local boot = CreateFrame("Frame")
    boot:RegisterEvent("PLAYER_ENTERING_WORLD")
    boot:SetScript("OnEvent", function(self)
        self:UnregisterEvent("PLAYER_ENTERING_WORLD")
        retryLeft = 6
        ApplyEnabled()
        if C_Timer and C_Timer.After then
            C_Timer.After(2.0, function()
                if NB.RefreshEnabled then NB.RefreshEnabled() end
            end)
            C_Timer.After(6.0, function()
                if NB.RefreshEnabled then NB.RefreshEnabled() end
            end)
        end
    end)
end)
