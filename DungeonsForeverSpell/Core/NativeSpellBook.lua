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
local restoring = false
local lastTab
local openGuard = 0

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

local function BookShown()
    if not (book and book.IsShown) then return false end
    if book.IsVisible then
        local ok, v = pcall(book.IsVisible, book)
        if ok then return v and true or false end
    end
    local ok2, v2 = pcall(book.IsShown, book)
    if not ok2 then return true end
    return v2 and true or false
end

local function ShowTabs()
    if not BookShown() then return end
    if tabButton then tabButton:Show() end
    if weaponTabButton then weaponTabButton:Show() end
end

local function HideTabs()
    if tabButton then tabButton:Hide() end
    if weaponTabButton then weaponTabButton:Hide() end
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

local function Paged()
    if not book then
        local psf = PlayerSpellsFrame
        local sb = psf and psf.SpellBookFrame
        if sb then book = sb end
    end
    return book and book.PagedSpellsFrame
end

local OVL_ROW_H = 60
local OVL_ROW_STEP = 70
local OVL_COL_GAP = 14

local ovl, ovlClip, ovlArt, listHost, ovlPager
local tabCatcher
local pageSeq = 0
local SyncTabCatcher
local artPool = {}
local itemPool, headPool = {}, {}
local pageSet, pageNo
local ovlPaging = false

local function RectInPsf(f)
    local psf = PlayerSpellsFrame
    if not (f and psf) then return nil end
    local ok1, l = pcall(f.GetLeft, f)
    local ok2, t = pcall(f.GetTop, f)
    local ok3, w = pcall(f.GetWidth, f)
    local ok4, h = pcall(f.GetHeight, f)
    local ok5, pl = pcall(psf.GetLeft, psf)
    local ok6, pt = pcall(psf.GetTop, psf)
    if not (ok1 and ok2 and ok3 and ok4 and ok5 and ok6) then return nil end
    if type(l) ~= "number" or type(t) ~= "number" or type(w) ~= "number" or type(h) ~= "number" then return nil end
    if type(pl) ~= "number" or type(pt) ~= "number" then return nil end
    local sc = 1
    local okA, a = pcall(f.GetEffectiveScale, f)
    local okB, b = pcall(psf.GetEffectiveScale, psf)
    if okA and okB and type(a) == "number" and type(b) == "number" and a > 0 and b > 0 then sc = a / b end
    return (l - pl) * sc, (pt - t) * sc, w * sc, h * sc
end

local function ViewList(allowHidden)
    local paged = Paged()
    if not paged then return nil end
    local v1, v2 = paged.View1, paged.View2
    if not v1 and paged.ViewFrames then v1, v2 = paged.ViewFrames[1], paged.ViewFrames[2] end
    if not v1 then return nil end
    if not allowHidden then
        local okv, vis = pcall(v1.IsVisible, v1)
        if okv and not vis then return nil end
    end
    local list = { v1 }
    if v2 then
        local ok, sh = pcall(v2.IsShown, v2)
        local l1, _, w1 = RectInPsf(v1)
        local l2, _, w2 = RectInPsf(v2)
        local pw = 0
        local psf = PlayerSpellsFrame
        if psf then pw = psf:GetWidth() or 0 end
        local apart = (l1 and l2 and w1 and w1 > 0) and (math.abs(l2 - l1) >= w1 * 0.5)
        local fits = (l2 and w2 and pw > 0) and (l2 + w2 <= pw + 4)
        if (ok and sh or allowHidden) and apart and fits then list[2] = v2 end
    end
    return list
end

local function PagerFrame()
    local paged = Paged()
    if not paged then return nil end
    if paged.PagingControls and paged.PagingControls.GetObjectType then return paged.PagingControls end
    for _, ch in ipairs({ paged:GetChildren() }) do
        local n = 0
        for _, c in ipairs({ ch:GetChildren() }) do
            if c.IsObjectType and c:IsObjectType("Button") then n = n + 1 end
        end
        if n >= 2 then return ch end
    end
    return nil
end

local function Metrics(allowHidden)
    local views = ViewList(allowHidden)
    if not views then return nil end
    local _, _, vw, vh = RectInPsf(views[1])
    if not vw or vw <= 0 or not vh or vh <= 0 then return nil end
    local paged = Paged()
    local cols = paged and paged.columnsPerRow or 2
    if type(cols) ~= "number" or cols < 1 then cols = 2 end
    local cellW = (vw - OVL_COL_GAP * (cols - 1)) / cols
    local rows = math.floor((vh - OVL_ROW_H) / OVL_ROW_STEP) + 1
    if rows < 1 then rows = 1 end
    return cols, cellW, rows
end

local function ArtCopies()
    local psf = PlayerSpellsFrame
    local out = {}
    if not psf then return out end
    local function scan(f, d)
        if d > 5 then return end
        for _, r in ipairs({ f:GetRegions() }) do
            local ok, atlas = pcall(r.GetAtlas, r)
            if ok and type(atlas) == "string" and atlas:find("^spellbook%-Page") then
                local okv, v = pcall(r.IsVisible, r)
                if okv and v then
                    local l, t, w, h = RectInPsf(r)
                    if l and w > 8 and h > 8 then
                        out[#out + 1] = { atlas = atlas, l = l, t = t, w = w, h = h }
                    end
                end
            end
        end
        for _, ch in ipairs({ f:GetChildren() }) do scan(ch, d + 1) end
    end
    scan(psf, 0)
    return out
end

local function EnsureOverlay()
    if ovl then return ovl end
    local psf = PlayerSpellsFrame
    if not psf then return nil end
    if InCombat() then return nil end
    ovl = CreateFrame("Frame", "DungeonsForeverBookOverlay", psf)
    ovl:SetAllPoints(psf)
    ovl:SetFrameStrata(psf:GetFrameStrata())
    ovl:SetFrameLevel(104)
    ovlClip = CreateFrame("Frame", nil, ovl)
    ovlClip:SetFrameLevel(105)
    ovlClip:SetClipsChildren(true)
    ovlClip:EnableMouse(true)
    ovlClip:EnableMouseWheel(true)
    ovlClip:SetScript("OnMouseWheel", function(_, delta)
        if not delta then return end
        if delta > 0 then
            NB.Page(-1)
        else
            NB.Page(1)
        end
    end)
    ovlArt = CreateFrame("Frame", nil, ovlClip)
    ovlArt:SetFrameLevel(106)
    listHost = CreateFrame("Frame", nil, ovl)
    listHost:SetAllPoints(ovl)
    listHost:SetFrameLevel(120)
    listHost:EnableMouse(false)
    ovl:Hide()
    return ovl
end

local function ThinItem(f)
    local function thin(o)
        if not o or not o.GetObjectType then return end
        local ok, t = pcall(o.GetObjectType, o)
        if ok and t == "FontString" then ns.ThinFont(o) end
    end
    thin(f.Name)
    thin(f.SubName)
    thin(f.RequiredLevel)
end

local function NewItem()
    local ok, f = pcall(CreateFrame, "Frame", nil, listHost, "SpellBookItemTemplate")
    if not ok or not f then
        ok, f = pcall(CreateFrame, "Button", nil, listHost, "SpellBookItemTemplate")
    end
    if not ok or not f then return nil end
    return f
end

local function NewHead()
    local ok, f = pcall(CreateFrame, "Frame", nil, listHost, "SpellBookHeaderTemplate")
    if not ok or not f then return nil end
    return f
end

local function PrebuildPool()
    if InCombat() or not listHost then return end
    for i = #itemPool + 1, 40 do
        local f = NewItem()
        if not f then break end
        f:Hide()
        itemPool[i] = f
    end
    for i = #headPool + 1, 12 do
        local h = NewHead()
        if not h then break end
        h:Hide()
        headPool[i] = h
    end
end

local function PackGroups(groups, cols, rows, viewCount)
    local pages = {}
    local page, view, row, col
    local function newPage()
        page = { views = {} }
        for i = 1, viewCount do page.views[i] = {} end
        pages[#pages + 1] = page
        view, row, col = 1, 0, 0
    end
    newPage()
    local function advance()
        col = 0
        row = row + 1
    end
    local function nextView()
        if view < viewCount then
            view, row, col = view + 1, 0, 0
            return true
        end
        newPage()
        return false
    end
    for _, g in ipairs(groups) do
        local head = g.header and g.header.text
        if head then
            if col > 0 then advance() end
            while row >= rows do
                nextView()
            end
            local slots = page.views[view]
            slots[#slots + 1] = { head = head, row = row }
            advance()
        end
        for _, d in ipairs(g.elements or {}) do
            if col >= cols then advance() end
            while row >= rows do
                nextView()
            end
            local slots = page.views[view]
            slots[#slots + 1] = { d = d, row = row, col = col }
            col = col + 1
        end
    end
    return pages
end

local function PaintPage()
    if not (ovl and pageSet) then return end
    local views = ViewList(true)
    if not views then return end
    local cols, cellW, rows = Metrics(true)
    if not cols then return end
    local page = pageSet[pageNo]
    local ii, hi = 0, 0
    for vIdx, v in ipairs(views) do
        local l, t = RectInPsf(v)
        if l then
            local slots = page and page.views[vIdx]
            for _, s in ipairs(slots or {}) do
                local top = t + s.row * OVL_ROW_STEP
                if s.head then
                    hi = hi + 1
                    local h = headPool[hi]
                    if not h then
                        h = NewHead()
                        headPool[hi] = h
                    end
                    if h then
                        HeaderInit(h, { text = s.head })
                        h:ClearAllPoints()
                        h:SetPoint("TOPLEFT", listHost, "TOPLEFT", l, -top)
                        h:SetSize(cellW * cols + OVL_COL_GAP * (cols - 1), OVL_ROW_H)
                        h:Show()
                    end
                else
                    ii = ii + 1
                    local f = itemPool[ii]
                    if not f then
                        f = NewItem()
                        itemPool[ii] = f
                    end
                    if f then
                        ItemInit(f, s.d)
                        ThinItem(f)
                        f:ClearAllPoints()
                        f:SetPoint("TOPLEFT", listHost, "TOPLEFT", l + s.col * (cellW + OVL_COL_GAP), -top)
                        f:SetSize(cellW, OVL_ROW_H)
                        f:Show()
                    end
                end
            end
        end
    end
    for i = ii + 1, #itemPool do itemPool[i]:Hide() end
    for i = hi + 1, #headPool do headPool[i]:Hide() end
end

local function PagerSync()
    local pg = ovlPager
    if not pg then return end
    local total = pageSet and #pageSet or 1
    if total < 1 then total = 1 end
    ovlPaging = true
    if pg.SetMaxPages then pcall(pg.SetMaxPages, pg, total) end
    if pg.SetCurrentPage then pcall(pg.SetCurrentPage, pg, pageNo or 1) end
    if pg.PageText then pcall(pg.PageText.SetText, pg.PageText, string.format("%d/%d%s", pageNo or 1, total, "页")) end
    ovlPaging = false
end

local function SetPage(n)
    if not pageSet or #pageSet == 0 then return end
    if n < 1 then n = 1 end
    if n > #pageSet then n = #pageSet end
    if n == pageNo then return end
    pageNo = n
    PaintPage()
    PagerSync()
end

local function EnsurePager()
    if ovlPager then return ovlPager end
    if not ovl then return nil end
    local ok, f = pcall(CreateFrame, "Frame", "DungeonsForeverBookPager", ovl, "PagingControlsHorizontalTemplate")
    if not ok or not f then return nil end
    ovlPager = f
    f:SetSize(114, 32)
    f:SetFrameLevel(140)
    f:EnableMouseWheel(false)
    if f.PageText then pcall(f.PageText.SetFontObject, f.PageText, "SystemFont_Med3") end
    f.GetPageDelta = function() return 1 end
    local function WirePageButton(btn, delta)
        if not (btn and btn.SetScript) then return end
        pcall(btn.SetScript, btn, "OnClick", function()
            if not pageSet or #pageSet == 0 then return end
            SetPage((pageNo or 1) + delta)
        end)
    end
    WirePageButton(f.PrevPageButton, -1)
    WirePageButton(f.NextPageButton, 1)
    ovl.OnPageChanged = function()
        if ovlPaging then return end
        local cur
        local okc, v = pcall(f.GetCurrentPage, f)
        if okc and type(v) == "number" then cur = v end
        if not cur or cur == pageNo then return end
        if not pageSet or #pageSet == 0 then return end
        if cur < 1 then cur = 1 end
        if cur > #pageSet then cur = #pageSet end
        pageNo = cur
        PaintPage()
        PagerSync()
    end
    return f
end

local function LayoutOverlay()
    local psf = PlayerSpellsFrame
    if not (psf and ovl) then return false end
    local views = ViewList()
    if not views then return false end
    local minX, minT, maxX, maxB
    local function absorb(l, t, w, h)
        if not l then return end
        if not minX then
            minX, minT, maxX, maxB = l, t, l + w, t + h
        else
            minX = math.min(minX, l)
            minT = math.min(minT, t)
            maxX = math.max(maxX, l + w)
            maxB = math.max(maxB, t + h)
        end
    end
    for _, v in ipairs(views) do
        absorb(RectInPsf(v))
    end
    if not minX then return false end
    local arts = ArtCopies()
    for _, it in ipairs(arts) do
        absorb(it.l, it.t, it.w, it.h)
    end
    local tabs = book and book.CategoryTabSystem
    if tabs then
        local _, tt, _, th = RectInPsf(tabs)
        if tt and th then minT = math.max(minT, tt + th + 6) end
    end
    local pg = PagerFrame()
    if pg then
        absorb(RectInPsf(pg))
    end
    local pw, ph = psf:GetWidth(), psf:GetHeight()
    minX = math.max(0, minX)
    minT = math.max(0, minT)
    maxX = math.min(pw, maxX)
    maxB = math.min(ph, maxB)
    if maxB - minT < 8 or maxX - minX < 8 then return false end
    ovlClip:ClearAllPoints()
    ovlClip:SetPoint("TOPLEFT", ovl, "TOPLEFT", minX, -minT)
    ovlClip:SetSize(maxX - minX, maxB - minT)
    ovlArt:ClearAllPoints()
    ovlArt:SetPoint("TOPLEFT", ovlClip, "TOPLEFT", -minX, minT)
    ovlArt:SetSize(pw, ph)
    local paintArt = not EUIOn()
    local used = 0
    if paintArt then
        for i = 1, #arts do
            local it = arts[i]
            local tex = artPool[i]
            if not tex then
                tex = ovlArt:CreateTexture(nil, "BACKGROUND")
                artPool[i] = tex
            end
            local okat = pcall(tex.SetAtlas, tex, it.atlas, true)
            if okat then
                tex:ClearAllPoints()
                tex:SetPoint("TOPLEFT", ovlArt, "TOPLEFT", it.l, -it.t)
                tex:SetSize(it.w, it.h)
                tex:Show()
                used = i
            else
                tex:Hide()
            end
        end
    end
    for i = used + 1, #artPool do artPool[i]:Hide() end
    local pgf = EnsurePager()
    if pgf and pg then
        local l, t, w, h = RectInPsf(pg)
        if l then
            pgf:ClearAllPoints()
            pgf:SetPoint("TOPLEFT", ovl, "TOPLEFT", l, -t)
            pgf:SetSize(w, h)
            pgf:Show()
        else
            pgf:Hide()
        end
    end
    return true
end

local hiddenNative = {}

local function HideNativeList()
    local paged = Paged()
    if not paged then return end
    local function hide(f)
        if f and f.IsShown and f:IsShown() then
            hiddenNative[#hiddenNative + 1] = f
            f:Hide()
        end
    end
    hide(paged.View1)
    hide(paged.View2)
    if paged.ViewFrames then
        for _, v in ipairs(paged.ViewFrames) do hide(v) end
    end
end

local function RestoreNativeList()
    for _, f in ipairs(hiddenNative) do
        if f.IsShown then f:Show() end
    end
    hiddenNative = {}
end

local function HideOverlay()
    RestoreNativeList()
    if ovl then ovl:Hide() end
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

local groupCache = {}

local function BuildGroups()
    if activePage == "weapon" then
        if subState == "weapon" then
            return BuildWeaponGroups()
        end
        return ClassGroups()
    end
    return BuildSpellGroups()
end

local function CacheKey()
    if activePage == "weapon" then
        return subState == "weapon" and "weapon" or "class"
    end
    return "spell"
end

local function WarmCache()
    if InCombat() then return end
    local g = BuildSpellGroups()
    if g and #g > 0 then groupCache.spell = g end
    g = ClassGroups()
    if g and #g > 0 then groupCache["class"] = g end
    g = BuildWeaponGroups()
    if g and #g > 0 then groupCache.weapon = g end
end

local function InstallOurs()
    if not book then return false end
    if not BookShown() then
        if ovl then ovl:Hide() end
        return false
    end
    if not EnsureOverlay() then return false end
    RestoreNativeList()
    local key = CacheKey()
    local groups
    if InCombat() then
        groups = groupCache[key]
        if not groups then groups = BuildGroups() end
    else
        groups = BuildGroups()
        if groups and #groups > 0 then groupCache[key] = groups end
    end
    if not groups or #groups == 0 then groups = EmptyGroup() end
    local cols, _, rows = Metrics()
    local views = ViewList()
    if not cols or not views then
        HideOverlay()
        return false
    end
    pageSet = PackGroups(groups, cols, rows, #views)
    pageNo = 1
    if not LayoutOverlay() then
        HideOverlay()
        return false
    end
    PaintPage()
    PagerSync()
    HideNativeList()
    ovl:Show()
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
    subBar:SetFrameLevel(150)
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
    local bar = subBar
    if not bar then
        if InCombat() then return end
        bar = BuildSubBar()
        if not bar then return end
    end
    if show then
        bar:Show()
    else
        bar:Hide()
    end
end

local function RestoreNative()
    HideOverlay()
end

local function ApplyData()
    if activePage then
        InstallOurs()
    else
        RestoreNative()
    end
end

local function SyncLastTab()
    if not (book and book.GetTab) then return end
    local ok, id = pcall(book.GetTab, book)
    if ok and id ~= nil then lastTab = id end
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

local function StyleOurTabs()
    if not book then return end
    local shown = activePage ~= nil
    StyleOurTab(tabButton, shown and activePage == "spell")
    StyleOurTab(weaponTabButton, shown and activePage == "weapon")
end

local function PaintNativeTabs()
    if not book then return end
    local shown = activePage ~= nil
    local sys = book.CategoryTabSystem
    for _, tab in ipairs((sys and sys.tabs) or {}) do
        local active = not shown and tab:IsSelected()
        if tab.SquareBackground then tab.SquareBackground:SetShown(not active) end
        if tab.SquareBackgroundActive then tab.SquareBackgroundActive:SetShown(active) end
        if tab.SquareBackgroundActiveGlow then tab.SquareBackgroundActiveGlow:SetShown(active) end
        local ul = TabLine(tab)
        if ul then ul:SetShown(active) end
    end
end

local function PaintTabs()
    StyleOurTabs()
    if InCombat() then return end
    PaintNativeTabs()
end

ShowPage = function(key)
    if not book then return end
    if activePage == key then
        if key then ApplyData() end
        return
    end
    activePage = key
    if key then pageSeq = pageSeq + 1 end
    if GetTime then openGuard = GetTime() + 1.2 end
    local shown = key ~= nil
    StyleOurTabs()
    SyncSubBar(key == "weapon")
    if not InCombat() then
        if book.SearchBox then pcall(book.SearchBox.SetShown, book.SearchBox, not shown) end
        if book.SettingsDropdown then book.SettingsDropdown:SetShown(not shown) end
        if book.SearchPreviewContainer then book.SearchPreviewContainer:Hide() end
        PaintNativeTabs()
    end
    if key and not BookShown() then
        local psf = PlayerSpellsFrame
        if psf and not InCombat() then
            pcall(psf.SetTab, psf, 3)
            if C_Timer and C_Timer.After then
                C_Timer.After(0.05, function()
                    if activePage == key then ApplyData(); SyncLastTab() end
                end)
                C_Timer.After(0.3, function()
                    if activePage == key then ApplyData(); SyncLastTab() end
                end)
                C_Timer.After(1.0, function()
                    if activePage == key then SyncLastTab() end
                end)
            end
        end
    end
    ApplyData()
    if not InCombat() then SyncLastTab() end
    if SyncTabCatcher then SyncTabCatcher() end
    if NB.OnPage then NB.OnPage(activePage) end
end

local function NativeTabClicked()
    if not activePage then return end
    local seq = pageSeq
    local function leave()
        if not activePage or pageSeq ~= seq then return end
        ShowPage(nil)
        SyncLastTab()
        PaintTabs()
    end
    if C_Timer and C_Timer.After then
        C_Timer.After(0, leave)
    else
        leave()
    end
end

local function HookNativeTabs()
    local sys = book and book.CategoryTabSystem
    for _, t in ipairs((sys and sys.tabs) or {}) do
        if t and t.HookScript and not t.__dfTabHook then
            local ok = pcall(t.HookScript, t, "OnClick", NativeTabClicked)
            if ok then t.__dfTabHook = true end
        end
    end
end

local function EnsureTabCatcher()
    if tabCatcher then return tabCatcher end
    local psf = PlayerSpellsFrame
    if not psf then return nil end
    if InCombat() then return nil end
    tabCatcher = CreateFrame("Button", "DungeonsForeverTabCatcher", psf)
    tabCatcher:SetFrameLevel(108)
    tabCatcher:RegisterForClicks("AnyUp")
    tabCatcher:SetScript("OnClick", function() NativeTabClicked() end)
    tabCatcher:SetScript("OnEnter", function(self)
        local t = self.__target
        local f = t and t.GetScript and t:GetScript("OnEnter")
        if f then pcall(f, t) end
    end)
    tabCatcher:SetScript("OnLeave", function(self)
        local t = self.__target
        local f = t and t.GetScript and t:GetScript("OnLeave")
        if f then pcall(f, t) end
    end)
    tabCatcher:Hide()
    return tabCatcher
end

SyncTabCatcher = function()
    local sys = book and book.CategoryTabSystem
    if not (sys and tabCatcher) then return end
    if not activePage or not BookShown() then
        if tabCatcher:IsShown() then tabCatcher:Hide() end
        return
    end
    local target
    for _, t in ipairs(sys.tabs or {}) do
        if t and t.IsShown and t:IsShown() and t.IsSelected and t:IsSelected() then
            target = t
            break
        end
    end
    if not target then
        for _, t in ipairs(sys.tabs or {}) do
            if t and t.IsShown and t:IsShown() and t.IsEnabled and not t:IsEnabled() then
                target = t
                break
            end
        end
    end
    if not target then
        if tabCatcher:IsShown() then tabCatcher:Hide() end
        return
    end
    if tabCatcher.__target ~= target then
        tabCatcher.__target = target
        tabCatcher:ClearAllPoints()
        tabCatcher:SetAllPoints(target)
    end
    if not tabCatcher:IsShown() then tabCatcher:Show() end
end

local function OnTabClick(key)
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
    HookNativeTabs()
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
    book = sb

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
    if not BookShown() then HideTabs() end

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
        if id ~= nil and lastTab == nil then
            lastTab = id
            return
        end
        if id ~= lastTab then
            local now = GetTime and GetTime() or 0
            if activePage and now <= openGuard then return end
            lastTab = id
            if activePage then ShowPage(nil) end
            return
        end
        if activePage then
            InstallOurs()
            if SyncTabCatcher then SyncTabCatcher() end
        elseif C_Timer and C_Timer.After then
            C_Timer.After(0, ThinAll)
        end
        HookNativeTabs()
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
    local function SbShown(f)
        if not (f and f.IsShown) then return false end
        if f.IsVisible then
            local ok, v = pcall(f.IsVisible, f)
            if ok then return v and true or false end
        end
        local ok2, v2 = pcall(f.IsShown, f)
        return (ok2 and v2) and true or false
    end

    local function OnBookShown()
        if InCombat() then
            ShowTabs()
            StyleOurTabs()
            if C_Timer and C_Timer.After then
                C_Timer.After(0.05, ShowTabs)
                C_Timer.After(0.3, ShowTabs)
                C_Timer.After(0.9, ShowTabs)
            end
            if activePage then
                InstallOurs()
                if C_Timer and C_Timer.After then
                    C_Timer.After(0.1, function()
                        if activePage then InstallOurs() end
                    end)
                    C_Timer.After(0.35, function()
                        if activePage then InstallOurs() end
                    end)
                    C_Timer.After(0.9, function()
                        if activePage then InstallOurs() end
                    end)
                end
            end
            return
        end
        if C_Timer and C_Timer.After then
            C_Timer.After(0, ThinAll)
            C_Timer.After(0.1, ThinAll)
            C_Timer.After(0.3, ThinAll)
        else
            ThinAll()
        end
        if NB.RefreshEnabled then NB.RefreshEnabled() end
        ReparentTabs()
        AnchorTabs()
        ShowTabs()
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
    end

    local function OnBookHidden()
        HideTabs()
        HideOverlay()
        if subBar then subBar:Hide() end
        if tabCatcher then tabCatcher:Hide() end
    end

    local function OnBookResized()
        if DeferInCombat() then return end
        ReparentTabs()
        AnchorTabs()
        FitSearchBox()
        if activePage then
            InstallOurs()
            if C_Timer and C_Timer.After then
                C_Timer.After(0.15, function()
                    if activePage and not InCombat() then InstallOurs() end
                end)
                C_Timer.After(0.45, function()
                    if activePage and not InCombat() then InstallOurs() end
                end)
            end
        end
    end

    local beatAcc, lastShown, lastW, lastH, lastTal, lastSig = 0, nil, nil, nil, nil, nil
    local lastPsf = nil
    local beat = CreateFrame("Frame")
    beat:RegisterEvent("UI_SCALE_CHANGED")
    beat:RegisterEvent("DISPLAY_SIZE_CHANGED")
    beat:SetScript("OnEvent", function()
        if activePage and not InCombat() then InstallOurs() end
    end)
    beat:SetScript("OnUpdate", function(_, elapsed)
        beatAcc = beatAcc + elapsed
        if beatAcc < 0.2 then return end
        beatAcc = 0
        local psf = PlayerSpellsFrame
        local psfShown = false
        if psf then
            local okp, vp = pcall(psf.IsVisible, psf)
            psfShown = (okp and vp) and true or false
        end
        if psfShown ~= lastPsf then
            lastPsf = psfShown
            if psfShown then
                if not InCombat() then AnchorTabs() end
                ShowTabs()
            elseif not InCombat() then
                HideTabs()
            end
        end
        local shown = SbShown(sb)
        if shown ~= lastShown then
            lastShown = shown
            lastW, lastH, lastSig = nil, nil, nil
            if shown then OnBookShown() else OnBookHidden() end
        end
        if sb.GetTab then
            local okt, id = pcall(sb.GetTab, sb)
            if okt and id ~= lastTab then
                local now = GetTime and GetTime() or 0
                if not (activePage and now <= openGuard) then
                    lastTab = id
                    if activePage then ShowPage(nil) end
                end
            end
        end
        if activePage and ovl and not ovl:IsVisible() and BookShown() then InstallOurs() end
        if SyncTabCatcher then SyncTabCatcher() end
        if tabButton and not tabButton:IsShown() and BookShown() and (ns.SpellEnhOn and ns.SpellEnhOn()) then ShowTabs() end
        if InCombat() then return end
        if shown then
            local w, h = sb:GetWidth(), sb:GetHeight()
            local views = ViewList()
            local pw, ph = 0, 0
            local psf = PlayerSpellsFrame
            if psf then pw, ph = psf:GetWidth(), psf:GetHeight() end
            local sig = tostring(w) .. "x" .. tostring(h) .. "@" .. math.floor(pw) .. "x" .. math.floor(ph)
                .. "#" .. tostring(views and #views or 0)
            if views and views[1] then
                local _, _, vw, vh = RectInPsf(views[1])
                if vw and vh then
                    sig = sig .. ":" .. math.floor(vw) .. "x" .. math.floor(vh)
                end
            end
            if sig ~= lastSig then
                lastSig = sig
                lastW, lastH = w, h
                OnBookResized()
            end
        end
    end)
    AnchorTabs()
    if not InCombat() then
        EnsureOverlay()
        EnsureTabCatcher()
        PrebuildPool()
        EnsurePager()
        WarmCache()
    end
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
        ShowTabs()
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
        ShowTabs()
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
        if weaponTabButton and BookShown() then weaponTabButton:Show() end
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
    WarmCache()
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

function NB.CacheInfo()
    local t = {}
    for _, k in ipairs({ "spell", "class", "weapon" }) do
        local g = groupCache[k]
        if g then
            local n = 0
            for _, grp in ipairs(g) do n = n + #(grp.elements or {}) end
            t[k] = n
        else
            t[k] = -1
        end
    end
    return t
end

function NB.ContentBox()
    return PageBox()
end

function NB.Page(delta)
    if not pageSet or (not activePage) then return end
    SetPage(pageNo + (delta < 0 and -1 or 1))
end

if ns.SpellTraining then
    ns.SpellTraining.OnDirty = function()
        WarmCache()
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
