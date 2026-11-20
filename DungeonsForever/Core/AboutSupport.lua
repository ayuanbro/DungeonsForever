local _, ns = ...

if not ns.IsTitan then return end

local L = ns.L

local GRID_TOP_PAD = 10
local LIST_MAX = 57
local NOTE_H = 58

local DONATE_ON = true

function ns.BuildAboutSupport(about, G)
    local hui = ns.hui
    local head, val, dim = G.head, G.val, G.dim

    local card = CreateFrame("Frame", nil, about, "BackdropTemplate")
    card:SetSize(G.w, G.h)
    card:SetPoint("TOPLEFT", about, "TOPLEFT", G.x, -G.top)
    card:SetFrameLevel(about:GetFrameLevel() + 2)
    card:EnableMouse(true)
    card:SetScript("OnMouseUp", function()
        ns.PlaySound(1)
        about:Hide()
        if G.sync then G.sync() end
    end)
    if card.SetBackdropColor then card:SetBackdropColor(0, 0, 0, 0) end
    if card.SetBackdropBorderColor then card:SetBackdropBorderColor(0, 0, 0, 0) end
    hui.BuildRoundedBG(card, 8, hui.layer.L1, "both", true)

    local hdr = card:CreateFontString(nil, "OVERLAY")
    hdr:SetFont(ns.FONT, 16, "")
    hdr:SetText(L["感谢名单"])
    hdr:SetPoint("TOPLEFT", card, "TOPLEFT", G.pad, -(G.pad + 4))
    hdr:SetTextColor(head[1], head[2], head[3])

    local members = ns.Thanks or {}
    local shown = math.min(#members, LIST_MAX)
    local rowH = G.rowH - 1

    local div = card:CreateTexture(nil, "ARTWORK")
    div:SetTexture("Interface\\Buttons\\WHITE8x8")
    local dv = hui.layer.DIV
    div:SetVertexColor(dv[1], dv[2], dv[3], 1)
    div:SetHeight(1)
    div:SetPoint("TOPLEFT", card, "TOPLEFT", G.pad, -G.divY)
    div:SetPoint("TOPRIGHT", card, "TOPRIGHT", -G.pad, -G.divY)

    local listH = G.gridH - NOTE_H
    local scroll = CreateFrame("ScrollFrame", nil, card)
    scroll:SetPoint("TOPLEFT", card, "TOPLEFT", G.pad, -G.gridTop)
    scroll:SetSize(G.availW, listH)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(G.availW, listH)
    scroll:SetScrollChild(child)

    for i = 1, shown do
        local col = (i - 1) % G.cols
        local row = math.floor((i - 1) / G.cols)
        local nm = child:CreateFontString(nil, "OVERLAY")
        local fam = ns.WIDE_UI and (_G.GameFontHighlightLarge or _G.GameFontHighlight)
        if fam then
            nm:SetFontObject(fam)
        else
            nm:SetFont(ns.FONT, 16, "")
        end
        nm:SetJustifyH("LEFT")
        nm:SetWordWrap(false)
        nm:SetTextColor(1, 1, 1)
        nm:SetPoint("TOPLEFT", child, "TOPLEFT",
            col * (G.colW + G.colGap),
            -(row * rowH + GRID_TOP_PAD))
        if G.fit then G.fit(nm, members[i], G.colW - 4) else nm:SetText(members[i]) end
    end
    local cy = math.ceil(shown / G.cols) * rowH + GRID_TOP_PAD
    child:SetHeight(math.max(cy, listH))

    local noteText = L["没在名单里出现的朋友，\n你们的反馈和建议同样让本插件变得更好。"]
    local brk = noteText:find("\n", 1, true)
    local lineA, lineB = noteText, nil
    if brk then
        lineA = noteText:sub(1, brk - 1)
        lineB = noteText:sub(brk + 1)
    end
    local nA = card:CreateFontString(nil, "OVERLAY")
    nA:SetFont(ns.FONT, 16, "")
    nA:SetJustifyH("CENTER")
    nA:SetWidth(G.availW)
    nA:SetText(lineA)
    nA:SetTextColor(dim[1], dim[2], dim[3])
    local lineH = nA:GetStringHeight() or 0
    local gap = rowH - lineH
    if lineB and gap > 0 then
        local nB = card:CreateFontString(nil, "OVERLAY")
        nB:SetFont(ns.FONT, 16, "")
        nB:SetJustifyH("CENTER")
        nB:SetWidth(G.availW)
        nB:SetText(lineB)
        nB:SetTextColor(dim[1], dim[2], dim[3])
        nB:SetPoint("BOTTOM", card, "BOTTOM", 0, G.pad + 2)
        nA:SetPoint("BOTTOM", nB, "TOP", 0, gap)
    else
        nA:SetPoint("BOTTOM", card, "BOTTOM", 0, G.pad + 2)
    end

    if #members == 0 then
        local empty = card:CreateFontString(nil, "OVERLAY")
        empty:SetFont(ns.FONT, 14, "")
        empty:SetText(L["还没有记录"])
        empty:SetTextColor(dim[1], dim[2], dim[3])
        empty:SetPoint("CENTER", scroll, "CENTER", 0, 0)
    end

    local track = CreateFrame("Frame", nil, card)
    track:SetSize(G.bar - 1, listH - 4)
    track:SetPoint("TOPLEFT", scroll, "TOPRIGHT", 0, -2)
    track:SetFrameLevel(card:GetFrameLevel() + 10)
    track.__fill = hui.BuildSolidFill(track, 3, hui.layer.L2)
    track:Hide()

    local thumb = CreateFrame("Frame", nil, card)
    thumb:SetSize(G.bar - 3, 24)
    thumb:SetFrameLevel(card:GetFrameLevel() + 11)
    thumb.__fill = hui.BuildSolidFill(thumb, 2, hui.layer.L4)
    thumb:EnableMouse(true)
    thumb:Hide()

    local function BarUpdate()
        local ch = child:GetHeight() or 0
        local vh = scroll:GetHeight() or 0
        if vh <= 0 or ch <= vh + 2 then
            track:Hide()
            thumb:Hide()
            return
        end
        track:Show()
        thumb:Show()
        local th = math.max(24, track:GetHeight() * vh / ch)
        thumb:SetHeight(th)
        local vp = scroll:GetVerticalScroll()
        if type(vp) ~= "number" then vp = 0 end
        local frac = 0
        local maxs = ch - vh
        if maxs > 0 then frac = vp / maxs end
        if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
        local span = math.max(0, track:GetHeight() - th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -(frac * span))
    end

    card:SetScript("OnMouseWheel", function(_, delta)
        if not track:IsShown() then return end
        local maxs = (child:GetHeight() or 0) - (scroll:GetHeight() or 0)
        local v = (scroll:GetVerticalScroll() or 0) - delta * 48
        if v < 0 then v = 0 elseif v > maxs then v = maxs end
        scroll:SetVerticalScroll(v)
        BarUpdate()
    end)

    thumb:SetScript("OnMouseDown", function(self)
        local scale = UIParent:GetEffectiveScale()
        local _, cy0 = GetCursorPosition()
        self.__y0 = cy0 / scale
        self.__s0 = scroll:GetVerticalScroll() or 0
        self:SetScript("OnUpdate", function(me)
            local span = (track:GetHeight() or 0) - (me:GetHeight() or 0)
            if span <= 0 then return end
            local _, cy1 = GetCursorPosition()
            local maxs = (child:GetHeight() or 0) - (scroll:GetHeight() or 0)
            local v = me.__s0 + (me.__y0 - cy1 / scale) / span * maxs
            if v < 0 then v = 0 elseif v > maxs then v = maxs end
            scroll:SetVerticalScroll(v)
            BarUpdate()
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnEnter", function(self)
        self.__hover = true
        hui.PaintSolidFill(self.__fill, hui.layer.L5)
    end)
    thumb:SetScript("OnLeave", function(self)
        self.__hover = false
        hui.PaintSolidFill(self.__fill, hui.layer.L4)
    end)

    hui.AddRepaint(card, function()
        hui.PaintSolidFill(track.__fill, hui.layer.L2)
        hui.PaintSolidFill(thumb.__fill, thumb.__hover and hui.layer.L5 or hui.layer.L4)
        local d2 = hui.layer.DIV
        div:SetVertexColor(d2[1], d2[2], d2[3], 1)
    end)

    if DONATE_ON then
        local donateShade
        local donateBuilt
        local function HideDonate()
            if donateShade and donateShade:IsShown() then donateShade:Hide() end
        end
        local function BuildDonate()
            if donateBuilt then return end
            donateBuilt = true
            local shade = CreateFrame("Button", "DungeonsForeverDonate", about)
            shade:SetAllPoints(about)
            shade:SetFrameLevel(about:GetFrameLevel() + 20)
            local bg = shade:CreateTexture(nil, "BACKGROUND")
            bg:SetAllPoints()
            bg:SetColorTexture(0, 0, 0, 0.52)
            shade:SetScript("OnClick", function() HideDonate() end)
            shade:Hide()
            table.insert(UISpecialFrames, "DungeonsForeverDonate")

            local pop = CreateFrame("Frame", nil, shade, "BackdropTemplate")
            pop:SetSize(260, 310)
            pop:SetPoint("CENTER", about, "CENTER", 0, 0)
            pop:SetFrameLevel(shade:GetFrameLevel() + 2)
            pop:SetClampedToScreen(true)
            pop:EnableMouse(true)
            if pop.SetBackdropColor then pop:SetBackdropColor(0, 0, 0, 0) end
            if pop.SetBackdropBorderColor then pop:SetBackdropBorderColor(0, 0, 0, 0) end
            if hui.SkinPopup then hui.SkinPopup(pop, 10, nil, hui.layer.L0) end
            if hui.SkinShadow then hui.SkinShadow(pop) end

            local close = CreateFrame("Button", nil, pop)
            close:SetSize(24, 24)
            close:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -8, -8)
            close:SetFrameLevel(pop:GetFrameLevel() + 3)
            close:SetHitRectInsets(-4, -4, -4, -4)
            local ci = close:CreateTexture(nil, "ARTWORK")
            ci:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
            ci:SetSize(14, 14)
            ci:SetPoint("CENTER")
            local cg = 0xa0 / 255
            ci:SetVertexColor(cg, cg, cg)
            close:SetScript("OnEnter", function() ci:SetVertexColor(1, 1, 1) end)
            close:SetScript("OnLeave", function() ci:SetVertexColor(cg, cg, cg) end)
            close:SetScript("OnClick", function()
                ns.PlaySound(1)
                HideDonate()
            end)

            local plate = CreateFrame("Frame", nil, pop, "BackdropTemplate")
            plate:SetSize(216, 216)
            plate:SetPoint("TOP", pop, "TOP", 0, -34)
            plate:SetFrameLevel(pop:GetFrameLevel() + 1)
            if plate.SetBackdropColor then plate:SetBackdropColor(0, 0, 0, 0) end
            if plate.SetBackdropBorderColor then plate:SetBackdropBorderColor(0, 0, 0, 0) end
            hui.BuildRoundedBG(plate, 6, hui.layer.L2, "both", false)

            local qr = plate:CreateTexture(nil, "ARTWORK")
            qr:SetAllPoints()
            qr:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\About\\wechat-support.tga")

            local h1 = pop:CreateFontString(nil, "OVERLAY")
            h1:SetFont(ns.FONT, 13, "")
            h1:SetText(L["手机微信扫一扫"])
            h1:SetTextColor(val[1], val[2], val[3])
            h1:SetPoint("TOP", pop, "TOP", 0, -262)

            local h2 = pop:CreateFontString(nil, "OVERLAY")
            h2:SetFont(ns.FONT, 12, "")
            h2:SetText(L["点击空白处或按 Esc 关闭"])
            h2:SetTextColor(dim[1], dim[2], dim[3])
            h2:SetPoint("TOP", pop, "TOP", 0, -282)

            donateShade = shade
        end
        local function ToggleDonate()
            BuildDonate()
            if donateShade:IsShown() then
                donateShade:Hide()
            else
                donateShade:Show()
            end
        end

        ns.ToggleDonate = ToggleDonate

        about:HookScript("OnHide", function() HideDonate() end)
    end

    BarUpdate()
    return card
end
