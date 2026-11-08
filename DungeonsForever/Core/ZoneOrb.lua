local _, ns = ...

local L = ns.L or function(k) return k end
local O = {}
ns.ZoneOrb = O

local ORB_SIZE = 48
local PANEL_W = 288
local PAD = 12
local CARD_H = 52
local HEAD_H = 20
local ROW_H = 44
local ROW_GAP = 6
local ROW_MAX = 8
local GAP = 8
local SLIDE = 26
local CLOSE_S = 36
local SIDE_S = 29

local FOOD_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_food.ogg"
local RESTED_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_rested.ogg"
local ON_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\prof_voice_on.ogg"
local OFF_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_voice_off.ogg"
local MANAGE_S = 23
local GLYPH = 0xA0 / 255
local TOP_Y = -48
local TEXT = { 0.95, 0.96, 0.98 }
local DIM = { 0.63, 0.65, 0.68 }
local FAINT = { 0.50, 0.51, 0.53 }
local ACC = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }

local orb, panel, badge, badgeText, tweener, icon, disc, ring, voiceBtn
local cards, heads, subRows, row, btnOpen, btnSkip, btnBlock, manage, moreText
local closeBtn, gear, opts, optCbs
local orbMenu, menuOpenedAt = nil, 0
local job = nil
local current = nil
local hovered = false
local lastFood, lastRested = false, false
local openedAt = 0
local hideToken = 0
local lastN = -1
local pulseFrame, pulseT = nil, 0

local function Cfg()
    return ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
end

local function ApplyOrbSize()
    if not orb then return end
    local sz = tonumber(Cfg().icon) or 32
    if sz < 20 then sz = 20 end
    if sz > 44 then sz = 44 end
    local orbSz = sz + 16
    orb:SetSize(orbSz, orbSz)
    local shown = sz * 1.25
    local ringSz = shown * 55 / 36
    if icon then icon:SetSize(shown, shown) end
    if disc then disc:SetSize(ringSz * 0.80, ringSz * 0.80) end
    if ring then ring:SetSize(ringSz, ringSz) end
end

local function PaintRing(n)
    if not ring then return end
    if hovered then
        ring:SetDesaturated(false)
        ring:SetVertexColor(1, 0.95, 0.65, 1)
    elseif (n or 0) > 0 then
        ring:SetDesaturated(false)
        ring:SetVertexColor(1, 0.85, 0.4, 1)
    else
        ring:SetDesaturated(true)
        ring:SetVertexColor(0.58, 0.58, 0.58, 1)
    end
end

local function PaintVoiceBtn()
    if not (voiceBtn and voiceBtn.tex) then return end
    local muted = Cfg().voice ~= true
    if muted then
        voiceBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
        voiceBtn.tex:SetVertexColor(0.95, 0.32, 0.32, 0.98)
    else
        voiceBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_voice_on.tga")
        voiceBtn.tex:SetVertexColor(GLYPH, GLYPH, GLYPH, 1)
    end
end

local function TextW(fs, dflt)
    local w = fs and fs.GetStringWidth and fs:GetStringWidth()
    if type(w) == "number" then return w end
    local t = fs and fs.GetText and fs:GetText()
    if type(t) == "string" and #t > 0 then return #t * 7 end
    return dflt or 0
end

local function SavePos()
    if not orb then return end
    local c = Cfg()
    local p, _, rp, x, y = orb:GetPoint(1)
    if p then
        c.orb = { p = p, rp = rp or p, x = x or 0, y = y or 0 }
    end
end

local function ApplyPos()
    local c = Cfg()
    local o = c.orb
    orb:ClearAllPoints()
    if type(o) == "table" and o.p then
        orb:SetPoint(o.p, UIParent, o.rp or o.p, o.x or 0, o.y or 0)
    else
        orb:SetPoint("LEFT", UIParent, "LEFT", 12, 0)
    end
end

local function StartTween(dur, apply, done)
    job = { t = 0, dur = dur, apply = apply, done = done }
    if tweener then tweener:Show() end
end

function O.ArmGhost()
    if not orb or not orb:IsShown() or orb:GetAlpha() == 0 then return end
    if orb.ghostPending then return end
    orb.ghostPending = true
    orb.ghostTok = (orb.ghostTok or 0) + 1
    local my = orb.ghostTok
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    C_Timer.After(2.5, function()
        orb.ghostPending = false
        if my ~= orb.ghostTok then return end
        if orb:IsMouseOver() or (panel and panel:IsShown()) or (opts and opts:IsShown()) then return end
        local c = Cfg()
        if c.on == false or not c.onlyTodo then return end
        if current and (current.total or 0) > 0 then return end
        if orb:GetAlpha() ~= 0 then orb:SetAlpha(0) end
        orb.revealed = false
    end)
end

local function Close()
    if not panel or not panel:IsShown() then return end
    hideToken = hideToken + 1
    StartTween(0.12, function(e)
        panel:SetAlpha(1 - e)
    end, function()
        panel:Hide()
        panel:SetAlpha(1)
    end)
end

local function StartHideTimer()
    hideToken = hideToken + 1
    local my = hideToken
    local d = tonumber(Cfg().dur) or 12
    if d <= 0 then return end
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    C_Timer.After(d, function()
        if my ~= hideToken then return end
        if opts and opts:IsShown() then return end
        if panel and panel:IsShown() and not hovered then Close() end
    end)
end

local function SubText(s)
    local parts = {}
    if s.learn then parts[#parts + 1] = string.format(L["%d 级可学"], s.learn) end
    if s.rank then parts[#parts + 1] = string.format(L["第 %d 阶"], s.rank) end
    if #parts == 0 then
        if s.tab and s.tab ~= "" then return s.tab end
        return L["可学"]
    end
    return table.concat(parts, " · ")
end

local function MakeCard(i)
    local card = cards[i]
    if card then return card end
    card = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(card, 8, "both", ns.hui.layer.L1)
    end
    card.title = card:CreateFontString(nil, "OVERLAY")
    card.title:SetFont(ns.FONT, 14, "")
    card.title:SetPoint("TOPLEFT", card, "TOPLEFT", 10, -10)
    card.title:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    card.text = card:CreateFontString(nil, "OVERLAY")
    card.text:SetFont(ns.FONT, 12, "")
    card.text:SetPoint("TOPLEFT", card, "TOPLEFT", 10, -30)
    card.text:SetJustifyH("LEFT")
    card.text:SetTextColor(DIM[1], DIM[2], DIM[3])
    card.text:SetWidth(PANEL_W - PAD * 2 - 56)
    card.text:SetWordWrap(false)
    if ns.hui and ns.hui.MakeSolidChip then
        card.chip = ns.hui.MakeSolidChip(card, panel:GetFrameLevel() + 3)
        card.chip:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, -7)
    end
    cards[i] = card
    return card
end

local function MakeHead(i)
    local h = heads[i]
    if h then return h end
    h = CreateFrame("Frame", nil, panel)
    h.label = h:CreateFontString(nil, "OVERLAY")
    h.label:SetFont(ns.FONT, 14, "")
    h.label:SetPoint("LEFT", h, "LEFT", 2, 0)
    h.label:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    h.cnt = h:CreateFontString(nil, "OVERLAY")
    h.cnt:SetFont(ns.FONT, 14, "")
    h.cnt:SetPoint("RIGHT", h, "RIGHT", -2, 0)
    h.cnt:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    heads[i] = h
    return h
end

local function HideTip()
    if GameTooltip then GameTooltip:Hide() end
end

local function AddGray(text)
    if text and text ~= "" then
        GameTooltip:AddLine(text, 0.82, 0.86, 0.90, true)
    end
end

local function AddAccent(text)
    if text and text ~= "" then
        GameTooltip:AddLine(text, ACC[1], ACC[2], ACC[3], true)
    end
end

local function Tip(owner, title, desc, foot)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(title or "", 1, 1, 1, true)
    AddGray(desc)
    AddAccent(foot)
    GameTooltip:Show()
end

local function ItemTip(owner, id, name, desc, foot)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    local ok = false
    if id and GameTooltip.SetItemByID then
        ok = pcall(GameTooltip.SetItemByID, GameTooltip, id)
        if ok then ok = (GameTooltip:NumLines() or 0) > 0 end
    end
    if not ok then
        GameTooltip:ClearLines()
        GameTooltip:AddLine(name or "", 1, 1, 1, true)
    end
    AddGray(desc)
    AddAccent(foot)
    GameTooltip:Show()
end

local function SpellTip(owner, id, name, sub, foot)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    local ok = false
    if id and GameTooltip.SetSpellByID then
        ok = pcall(GameTooltip.SetSpellByID, GameTooltip, id)
        if ok then ok = (GameTooltip:NumLines() or 0) > 0 end
    end
    if not ok then
        GameTooltip:ClearLines()
        GameTooltip:AddLine(name or "", 1, 1, 1, true)
    end
    AddGray(sub)
    AddAccent(foot)
    GameTooltip:Show()
end

local function MarkOnMap(it)
    if not it then return false end
    local EG = ns.ExploreModule
    if it.areaID and it.x and it.y and EG and EG.MarkPoint then
        local ok = pcall(EG.MarkPoint, it.areaID, it.x, it.y)
        if ok then return true end
    end
    local mapID = it.mapID or (current and current.ctx and current.ctx.mapID)
    if mapID and it.x and it.y and UiMapPoint and UiMapPoint.CreateFromCoordinates
       and C_Map and C_Map.SetUserWaypoint then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, it.x / 100, it.y / 100)
        if ok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
            if C_Map.OpenWorldMap then pcall(C_Map.OpenWorldMap, mapID) end
            return true
        end
    end
    if it.qid and ns.MapUI and ns.MapUI.GotoQuest then
        pcall(ns.MapUI.GotoQuest, it.qid, false)
        return true
    end
    return false
end

local function MakeRow(i)
    local r = subRows[i]
    if r then return r end
    r = CreateFrame("Button", nil, panel, "BackdropTemplate")
    local fx = ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(r, 6, 1)
    if not fx and ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(r, 8, "both", ns.hui.layer.L1)
    end
    r.icon = r:CreateTexture(nil, "ARTWORK")
    r.icon:SetSize(32, 32)
    r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -6)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    r.sym = r:CreateTexture(nil, "OVERLAY")
    r.sym:SetAllPoints(r.icon)
    r.sym:Hide()
    r.name = r:CreateFontString(nil, "OVERLAY")
    r.name:SetFont(ns.FONT, 14, "")
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -6)
    r.name:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    r.name:SetWidth(PANEL_W - PAD * 2 - 82)
    r.name:SetWordWrap(false)
    r.name:SetJustifyH("LEFT")
    r.sub = r:CreateFontString(nil, "OVERLAY")
    r.sub:SetFont(ns.FONT, 12, "")
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -26)
    r.sub:SetTextColor(DIM[1], DIM[2], DIM[3])
    r.sub:SetWidth(PANEL_W - PAD * 2 - 82)
    r.sub:SetWordWrap(false)
    r.sub:SetJustifyH("LEFT")
    r.btn = CreateFrame("Button", nil, r)
    r.btn:SetSize(24, 24)
    r.btn:SetPoint("RIGHT", r, "RIGHT", -6, 0)
    r.xt = r.btn:CreateFontString(nil, "OVERLAY")
    r.xt:SetFont(ns.FONT, 18, "")
    r.xt:SetPoint("CENTER", r.btn, "CENTER", 0, 0)
    r.xt:SetText("×")
    r.xt:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    r.btn:SetScript("OnEnter", function()
        r.xt:SetTextColor(0.89, 0.30, 0.29)
        Tip(r.btn, L["忽略此条"], L["以后不再提醒这一条"], L["可在管理忽略里恢复"])
    end)
    r.btn:SetScript("OnLeave", function()
        r.xt:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
        HideTip()
    end)
    r.btn:SetScript("OnClick", function()
        ns.PlaySound(1)
        if r.ikey and ns.ZoneHint and ns.ZoneHint.IgnoreItem then
            ns.ZoneHint.IgnoreItem(r.ikind, r.iid, r.ilabel)
        end
        O.Refresh()
    end)
    r:SetScript("OnClick", function()
        if not r.jump then return end
        if ns.ZoneHint and ns.ZoneHint.IsSim and ns.ZoneHint.IsSim() then return end
        ns.PlaySound(1)
        Close()
        r.jump()
    end)
    r:SetScript("OnEnter", function()
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "hover") end
        r.name:SetTextColor(ACC[1], ACC[2], ACC[3])
        local sub = r.sub:GetText()
        if r.ikind == "turnin" then
            ItemTip(r, r.iid, r.ilabel, r.idesc or sub, L["点击在地图上定位上交 NPC"])
        elseif r.ikind == "book" or r.ikind == "collect" or r.ikind == "rested" then
            local desc = sub
            if r.idesc and r.idesc ~= "" then
                desc = (sub ~= "" and (sub .. " · " .. r.idesc)) or r.idesc
            end
            ItemTip(r, r.iid, r.ilabel, desc, L["点击在地图标出位置"])
        elseif r.ikind == "quest" then
            Tip(r, r.ilabel, r.idesc or sub, L["点击在地图上定位"])
        else
            SpellTip(r, r.itipid or r.iid, r.ilabel, sub)
        end
    end)
    r:SetScript("OnLeave", function()
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "norm") end
        r.name:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        HideTip()
    end)
    subRows[i] = r
    return r
end

local function Layout(res)
    local list = (res and res.items) or {}
    local n = #list
    local ci, hi, ri = 0, 0, 0
    if moreText then moreText:Hide() end

    local want = {}
    for i = 1, n do
        local subs = list[i].list
        if type(subs) == "table" and #subs > 0 then want[i] = #subs end
    end

    local iconSz = tonumber(Cfg().icon) or 32
    if iconSz < 20 then iconSz = 20 end
    if iconSz > 44 then iconSz = 44 end
    local rowH = ROW_H
    if iconSz + 12 > rowH then rowH = iconSz + 12 end
    local textLeft = iconSz + 16
    local textW = PANEL_W - PAD * 2 - textLeft - 36

    local function HeightFor(cap)
        local h = 0
        for i = 1, n do
            local c = want[i]
            if c and c > 0 then
                local shown = c > cap and cap or c
                h = h + HEAD_H + 2 + shown * (rowH + ROW_GAP)
                if c > shown then h = h + 18 end
            else
                h = h + CARD_H + GAP
            end
        end
        return h
    end

    local maxH = ((UIParent and UIParent:GetHeight()) or 900) - 120
    local cap = ROW_MAX
    while cap > 1 and HeightFor(cap) > maxH do cap = cap - 1 end

    local y = TOP_Y
    local contentBottom = nil
    for i = 1, n do
        local it = list[i]
        local subs = it.list
        if type(subs) == "table" and #subs > 0 then
            hi = hi + 1
            local h = MakeHead(hi)
            h:ClearAllPoints()
            h:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, y)
            h:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, y)
            h:SetHeight(HEAD_H)
            h.label:SetText(it.title or "")
            h.cnt:SetText(string.format(L["%d 个"], #subs))
            h:Show()
            y = y - (HEAD_H + 2)
            local shown = #subs > cap and cap or #subs
            for k = 1, shown do
                local s = subs[k]
                ri = ri + 1
                local r = MakeRow(ri)
                if s.disc then
                    r.icon:SetTexture(s.disc)
                    r.icon:SetTexCoord(0, 1, 0, 1)
                    local dc = s.discCol
                    if dc then
                        r.icon:SetVertexColor(dc[1], dc[2], dc[3])
                    else
                        r.icon:SetVertexColor(1, 1, 1)
                    end
                    r.sym:SetTexture(s.sym)
                    local sc = s.symCol
                    if sc then
                        r.sym:SetVertexColor(sc[1], sc[2], sc[3])
                    else
                        r.sym:SetVertexColor(1, 1, 1)
                    end
                    r.sym:Show()
                else
                    r.sym:Hide()
                    r.icon:SetVertexColor(1, 1, 1)
                    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                    r.icon:SetTexture(s.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
                end
                r.icon:SetSize(iconSz, iconSz)
                r.name:ClearAllPoints()
                r.name:SetPoint("TOPLEFT", r, "TOPLEFT", textLeft, -6)
                r.name:SetWidth(textW)
                r.sub:ClearAllPoints()
                r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", textLeft, -26)
                r.sub:SetWidth(textW)
                r.name:SetText(s.name or "")
                r.sub:SetText(s.sub or SubText(s))
                do
                    local DG = ns.DungeonDG or (ns.ProfHost and ns.ProfHost.DG)
                    if s.badge and DG and DG.MakeBadge and DG.BadgeTint then
                        if not r.badge then r.badge = DG.MakeBadge(r) end
                        DG.BadgeTint(r.badge, s.badge.col)
                        r.badge.lab:SetText(s.badge.t or "")
                        local bw = TextW(r.badge.lab, 20) + (DG.Q_BADGE_PAD or 5) * 2
                        if bw < (DG.Q_BADGE_MIN_W or 24) then bw = DG.Q_BADGE_MIN_W or 24 end
                        if ns.hui and ns.hui.PaintSolidChip then
                            ns.hui.PaintSolidChip(r.badge, s.badge.t or "", s.badge.col, bw)
                        else
                            r.badge:SetWidth(bw)
                        end
                        r.badge:ClearAllPoints()
                        r.badge:SetPoint("TOPLEFT", r.sub, "TOPLEFT", TextW(r.sub, 12) + 6, -1)
                        r.badge:Show()
                    elseif r.badge then
                        r.badge:Hide()
                    end
                end
                r.ikey = s.ikey
                r.ikind = s.ikind or it.kind
                r.iid = s.base or s.id
                r.itipid = s.id
                r.idesc = s.desc
                r.ilabel = s.name
                if s.areaID or s.qid or (s.mapID and s.x and s.y) then
                    r.jump = function() return MarkOnMap(s) end
                else
                    r.jump = nil
                end
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, y)
                r:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, y)
                r:SetHeight(rowH)
                r:Show()
                contentBottom = y - rowH
                y = y - (rowH + ROW_GAP)
            end
            if #subs > shown and moreText then
                moreText:SetText(string.format(L["还有 %d 个，打开手册查看"], #subs - shown))
                moreText:ClearAllPoints()
                moreText:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD + 4, contentBottom - 4)
                moreText:Show()
                y = contentBottom - 20
                contentBottom = y + 2
            end
        else
            ci = ci + 1
            local card = MakeCard(ci)
            card.title:SetText(it.title or "")
            card.text:SetText(it.text or "")
            if card.chip and ns.hui and ns.hui.PaintSolidChip then
                ns.hui.PaintSolidChip(card.chip, tostring(it.n or 0), ns.hui.ACCENT, 32)
            end
            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, y)
            card:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, y)
            card:SetHeight(CARD_H)
            card:Show()
            contentBottom = y - CARD_H
            y = y - (CARD_H + GAP)
        end
    end
    for i = ci + 1, #cards do cards[i]:Hide() end
    for i = hi + 1, #heads do heads[i]:Hide() end
    for i = ri + 1, #subRows do subRows[i]:Hide() end

    local btY = (contentBottom or (TOP_Y + 4)) - GAP
    row:ClearAllPoints()
    row:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, btY)
    row:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, btY)
    row:SetHeight(24)
    row:Show()
    panel:SetHeight(-btY + 24 + PAD)
end

local function Open()
    if not panel or panel:IsShown() then return end
    if opts then opts:Hide() end
    Layout(current)
    panel:SetAlpha(0)
    local function apply(e)
        panel:ClearAllPoints()
        panel:SetPoint("LEFT", orb, "RIGHT", 8 - SLIDE * (1 - e), 0)
        panel:SetAlpha(e)
    end
    apply(0)
    panel:Show()
    openedAt = (GetTime and GetTime()) or 0
    StartTween(0.18, apply)
    StartHideTimer()
end

local function Toggle()
    if panel and panel:IsShown() then
        Close()
    else
        Open()
    end
end

local function Pulse()
    if not badge or not badge:IsShown() then return end
    pulseT = 0
    if pulseFrame then pulseFrame:Show() end
end

function O.Update(res)
    current = res
    if not badge then return end
    local onc = Cfg()
    local n = (res and res.total) or 0
    local settingsOpen = opts and opts.IsShown and opts:IsShown() or false
    local wantOrb = onc.on ~= false
    if orb then
        local ghost = wantOrb and (onc.onlyTodo and not settingsOpen) and n == 0
        if wantOrb and not orb:IsShown() then orb:Show() end
        if not wantOrb and orb:IsShown() then orb:Hide() end
        if ghost then
            if orb:IsMouseOver() or (panel and panel:IsShown()) then
                if orb:GetAlpha() ~= 1 then orb:SetAlpha(1) end
            elseif orb.revealed then
                O.ArmGhost()
            else
                if orb:GetAlpha() ~= 0 then orb:SetAlpha(0) end
            end
        elseif orb:IsShown() then
            if orb:GetAlpha() ~= 1 then orb:SetAlpha(1) end
        end
    end
    PaintRing(n)
    if n > 0 then
        if badgeText then badgeText:SetText(n > 9 and "9+" or tostring(n)) end
        badge:Show()
        if lastN ~= n then Pulse() end
        lastN = n
    else
        badge:Hide()
        lastN = 0
    end
    local sawFood, sawRested = false, false
    for _, it in ipairs(res and res.items or {}) do
        if it.kind == "buff" and it.list then
            for _, r in ipairs(it.list) do
                if r.ikind == "food" then sawFood = true
                elseif r.ikind == "rested" then sawRested = true end
            end
        end
    end
    if onc.on ~= false then
        if sawFood and not lastFood and onc.voice == true and onc.foodVoice ~= false then
            pcall(PlaySoundFile, FOOD_CUE, "Master")
        end
        if sawRested and not lastRested and onc.voice == true and onc.restedVoice ~= false then
            pcall(PlaySoundFile, RESTED_CUE, "Master")
        end
    end
    lastFood, lastRested = sawFood, sawRested
    if panel and panel:IsShown() then Layout(res) end
end

function O.Reveal(res, reason)
    O.Update(res)
    local mode = Cfg().mode or "auto"
    if mode == "silent" or mode == "badge" then return end
    if reason == "login" or reason == "zone" or reason == "manual" then Open() end
end

function O.IsShown()
    return panel ~= nil and panel:IsShown()
end

function O.Hide()
    Close()
    if orb then orb:Hide() end
end

local function InitVoiceBtn()
    voiceBtn = CreateFrame("Button", nil, panel)
    voiceBtn:SetSize(SIDE_S, SIDE_S)
    voiceBtn:SetPoint("CENTER", panel, "TOPRIGHT", -100, -22)
    voiceBtn:SetFrameLevel(panel:GetFrameLevel() + 4)
    voiceBtn.hover = false
    voiceBtn.tex = voiceBtn:CreateTexture(nil, "ARTWORK")
    voiceBtn.tex:SetSize(19, 19)
    voiceBtn.tex:SetPoint("CENTER", voiceBtn, "CENTER", 0, 0)
    voiceBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
    voiceBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = Cfg()
        c.voice = not (c.voice == true)
        PaintVoiceBtn()
        if c.voice == true then pcall(PlaySoundFile, ON_CUE, "Master") else pcall(PlaySoundFile, OFF_CUE, "Master") end
        if voiceBtn:IsMouseOver() then
            Tip(voiceBtn, L["语音"], (c.voice == true) and L["语音提示：开启（点击静音）"] or L["语音提示：已静音（点击恢复）"])
        end
    end)
    voiceBtn:SetScript("OnEnter", function()
        local c = Cfg()
        Tip(voiceBtn, L["语音"], (c.voice ~= true) and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"])
    end)
    voiceBtn:SetScript("OnLeave", function()
        HideTip()
    end)
    PaintVoiceBtn()
end

function O.Init()
    if orb then
        ApplyPos()
        return
    end

    orb = CreateFrame("Button", "DFZoneOrb", UIParent)
    orb:SetSize(ORB_SIZE, ORB_SIZE)
    orb:SetFrameStrata("MEDIUM")
    orb:SetFrameLevel(300)
    orb:SetClampedToScreen(true)
    orb:SetMovable(true)
    orb:RegisterForDrag("LeftButton")
    orb:EnableMouse(true)
    ApplyPos()

    disc = orb:CreateTexture(nil, "BACKGROUND")
    disc:SetPoint("CENTER", orb, "CENTER", 0, 0)
    disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc")
    disc:SetVertexColor(0x10 / 255, 0x13 / 255, 0x1A / 255, 1)

    ring = orb:CreateTexture(nil, "BORDER")
    ring:SetPoint("CENTER", orb, "CENTER", 0, 0)
    ring:SetAtlas("Talents-Main-Ring-c60")

    icon = orb:CreateTexture(nil, "ARTWORK")
    icon:SetSize(30, 30)
    icon:SetPoint("CENTER", orb, "CENTER", 0, 0)
    icon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever")

    badge = CreateFrame("Frame", nil, orb)
    badge:SetSize(20, 20)
    badge:SetPoint("TOPRIGHT", orb, "TOPRIGHT", 4, 4)
    badge:SetFrameLevel(orb:GetFrameLevel() + 5)
    local disc2 = badge:CreateTexture(nil, "BACKGROUND")
    disc2:SetAllPoints(badge)
    disc2:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc")
    disc2:SetVertexColor(0x7F / 255, 0x1F / 255, 0x1F / 255, 1)
    badgeText = badge:CreateFontString(nil, "OVERLAY")
    badgeText:SetFont(ns.FONT, 11, "OUTLINE")
    badgeText:SetPoint("CENTER", badge, "CENTER", 0, 0)
    badgeText:SetTextColor(1, 1, 1)
    badge:Hide()

    pulseFrame = CreateFrame("Frame")
    pulseFrame:Hide()
    pulseFrame:SetScript("OnUpdate", function(_, dt)
        pulseT = pulseT + dt
        local k = pulseT / 0.32
        if k >= 1 then
            pulseFrame:Hide()
            if badge then badge:SetScale(1) end
            return
        end
        if badge then badge:SetScale(1 + 0.32 * math.sin(k * math.pi)) end
    end)

    tweener = CreateFrame("Frame")
    tweener:Hide()
    tweener:SetScript("OnUpdate", function(_, dt)
        if not job then
            tweener:Hide()
            return
        end
        job.t = job.t + dt
        local k = job.t / job.dur
        if k > 1 then k = 1 end
        local e = 1 - (1 - k) * (1 - k) * (1 - k)
        job.apply(e)
        if k >= 1 then
            local done = job.done
            job = nil
            tweener:Hide()
            if done then done() end
        end
    end)

    panel = CreateFrame("Frame", "DFZoneOrbPanel", UIParent, "BackdropTemplate")
    panel:SetSize(PANEL_W, 120)
    panel:SetPoint("LEFT", orb, "RIGHT", 8, 0)
    panel:SetFrameStrata("MEDIUM")
    panel:SetFrameLevel(400)
    panel:SetClampedToScreen(true)
    panel:EnableMouse(true)
    panel:Hide()
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(panel, 10, "both", ns.hui.layer.L0)
    end

    panel.title = panel:CreateFontString(nil, "OVERLAY")
    panel.title:SetFont(ns.FONT, 16, "")
    panel.title:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, -12)
    panel.title:SetTextColor(TEXT[1], TEXT[2], TEXT[3])

    panel.count = panel:CreateFontString(nil, "OVERLAY")
    panel.count:SetFont(ns.FONT, 14, "")
    panel.count:SetPoint("LEFT", panel.title, "RIGHT", 8, 0)
    panel.count:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    moreText = panel:CreateFontString(nil, "OVERLAY")
    moreText:SetFont(ns.FONT, 14, "")
    moreText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    moreText:Hide()

    closeBtn = CreateFrame("Button", nil, panel, "BackdropTemplate")
    closeBtn:SetSize(CLOSE_S, CLOSE_S)
    closeBtn:SetPoint("CENTER", panel, "TOPRIGHT", -22, -22)
    closeBtn:SetFrameLevel(panel:GetFrameLevel() + 4)
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(closeBtn, { noFrame = true }) end
    local ct = closeBtn:CreateTexture(nil, "ARTWORK")
    ct:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    ct:SetSize(32, 32)
    ct:SetPoint("CENTER", closeBtn, "CENTER", 0, 0.4)
    ct:SetVertexColor(GLYPH, GLYPH, GLYPH)
    closeBtn:SetScript("OnClick", function() Close() end)
    closeBtn:SetScript("OnEnter", function()
        ct:SetVertexColor(1, 1, 1)
        Tip(closeBtn, L["关闭"], L["收起抽屉，角标继续显示待办数"], nil)
    end)
    closeBtn:SetScript("OnLeave", function()
        ct:SetVertexColor(GLYPH, GLYPH, GLYPH)
        HideTip()
    end)

    row = CreateFrame("Frame", nil, panel)
    row:SetFrameLevel(panel:GetFrameLevel() + 2)

    local function MakeBtn(text)
        local b = ns.CreateButton(row)
        b:SetSize(82, 24)
        b:SetText(text)
        return b
    end

    btnOpen = MakeBtn(L["打开手册"])
    btnOpen:SetPoint("LEFT", row, "LEFT", 0, 0)
    btnSkip = MakeBtn(L["本次忽略"])
    btnSkip:SetPoint("CENTER", row, "CENTER", 0, 0)
    btnBlock = MakeBtn(L["永久忽略"])
    btnBlock:SetPoint("RIGHT", row, "RIGHT", 0, 0)

    btnOpen:HookScript("OnEnter", function()
        Tip(btnOpen, L["打开手册"], L["查看完整的地图待办、副本与探索清单"], nil)
    end)
    btnOpen:HookScript("OnLeave", HideTip)
    btnSkip:HookScript("OnEnter", function()
        Tip(btnSkip, L["本次忽略"], L["本次登录内不再提醒这张地图"], L["重新登录或重载后恢复"])
    end)
    btnSkip:HookScript("OnLeave", HideTip)
    btnBlock:HookScript("OnEnter", function()
        Tip(btnBlock, L["永久忽略"], L["加入黑名单，以后进入这张地图都不再提醒"], L["可在管理忽略里恢复"])
    end)
    btnBlock:HookScript("OnLeave", HideTip)

    manage = CreateFrame("Button", nil, panel)
    manage:SetSize(MANAGE_S, MANAGE_S)
    manage:SetPoint("CENTER", panel, "TOPRIGHT", -48, -22)
    manage:SetFrameLevel(panel:GetFrameLevel() + 4)
    manage.tex = {}
    local function paintManage(v)
        for i = 1, #manage.tex do manage.tex[i]:SetColorTexture(v, v, v, 1) end
    end
    do
        local g = GLYPH
        for i = 1, 3 do
            local yy = 6.3 - (i - 1) * 6.3
            local dot = manage:CreateTexture(nil, "ARTWORK")
            dot:SetColorTexture(g, g, g, 1)
            dot:SetSize(2.7, 2.7)
            dot:SetPoint("CENTER", manage, "CENTER", -6.3, yy)
            manage.tex[#manage.tex + 1] = dot
            local bar = manage:CreateTexture(nil, "ARTWORK")
            bar:SetColorTexture(g, g, g, 1)
            bar:SetSize(10, 1.8)
            bar:SetPoint("CENTER", manage, "CENTER", 0.9, yy)
            manage.tex[#manage.tex + 1] = bar
        end
    end
    manage:SetScript("OnEnter", function()
        paintManage(1)
        Tip(manage, L["管理忽略"], L["查看与恢复已忽略的地图和小项"])
    end)
    manage:SetScript("OnLeave", function()
        paintManage(GLYPH)
        HideTip()
    end)
    manage:SetScript("OnClick", function()
        ns.PlaySound(1)
        Close()
        if ns.ZoneHintList and ns.ZoneHintList.Open then ns.ZoneHintList.Open() end
    end)

    gear = CreateFrame("Button", "DFZoneOrbGear", panel)
    gear:SetSize(SIDE_S, SIDE_S)
    gear:SetPoint("CENTER", panel, "TOPRIGHT", -74, -22)
    gear:SetFrameLevel(panel:GetFrameLevel() + 4)
    local gt = gear:CreateTexture(nil, "ARTWORK")
    gt:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings")
    gt:SetSize(19, 19)
    gt:SetPoint("CENTER")
    gt:SetVertexColor(GLYPH, GLYPH, GLYPH, 1)

    InitVoiceBtn()
    opts = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    opts:SetSize(184, 312)
    opts:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -8, -40)
    opts:SetFrameLevel(panel:GetFrameLevel() + 8)
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(opts, 8, "both", ns.hui.layer.L2)
        if ns.hui.SkinShadow then ns.hui.SkinShadow(opts, nil, nil, 8) end
    end
    opts:EnableMouse(true)
    opts:SetScript("OnEnter", function()
        hovered = true
        hideToken = hideToken + 1
    end)
    opts:SetScript("OnLeave", function()
        hovered = false
        StartHideTimer()
    end)
    opts:Hide()

    local oph = opts:CreateFontString(nil, "OVERLAY")
    oph:SetFont(ns.FONT, 14, "")
    oph:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -8)
    oph:SetText(L["提醒内容"])
    oph:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    optCbs = {}

    local function OptRow(y, label, key, tip, vkey)
        local t = opts:CreateFontString(nil, "OVERLAY")
        t:SetFont(ns.FONT, 14, "")
        t:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, y - 4)
        t:SetText(label)
        t:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        if vkey then
            local vb = CreateFrame("Button", nil, opts)
            vb:SetSize(28, 22)
            vb:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -56, y + 1)
            vb.tex = vb:CreateTexture(nil, "ARTWORK")
            vb.tex:SetSize(21, 21)
            vb.tex:SetPoint("CENTER", vb, "CENTER", 0, 0)
            vb.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
            local cue = (vkey == "foodVoice") and FOOD_CUE or RESTED_CUE
            local function paint()
                local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
                if c[vkey] == false then
                    vb.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
                    vb.tex:SetVertexColor(0xC6 / 255, 0xCB / 255, 0xD4 / 255, 1)
                else
                    vb.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_voice_on.tga")
                    vb.tex:SetVertexColor(ACC[1], ACC[2], ACC[3], 1)
                end
            end
            vb.PaintVoice = paint
            vb:SetScript("OnClick", function()
                ns.PlaySound(1)
                local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
                if c then c[vkey] = (c[vkey] == false) and true or false end
                paint()
                if c and c[vkey] ~= false then pcall(PlaySoundFile, cue, "Master") else pcall(PlaySoundFile, "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_voice_off.ogg", "Master") end
                if vb:IsMouseOver() then
                    Tip(vb, L["语音"], (c and c[vkey] == false) and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"])
                end
            end)
            vb:SetScript("OnEnter", function()
                local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
                Tip(vb, L["语音"], (c[vkey] == false) and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"])
            end)
            vb:SetScript("OnLeave", function()
                HideTip()
            end)
            paint()
            optCbs[vkey] = vb
        end
        local cb = CreateFrame("CheckButton", nil, opts)
        cb:SetSize(36, 20)
        cb:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -8, y + 1)
        if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(cb) end
        cb:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
            if not c then return end
            local nv = not (c[key] ~= false)
            c[key] = nv
            if self.SetChecked then self:SetChecked(nv) end
            if C_Timer and C_Timer.After then
                C_Timer.After(0, function()
                    local c2 = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
                    if c2 and self.SetChecked then self:SetChecked(c2[key] ~= false) end
                end)
            end
            O.Refresh()
            if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
        end)
        cb:SetScript("OnEnter", function()
            Tip(cb, label, tip)
        end)
        cb:SetScript("OnLeave", HideTip)
        optCbs[key] = cb
        return cb
    end

    OptRow(-32, L["探索-书籍提醒"], "book", L["本图还有未收集的书时提示"])
    OptRow(-54, L["探索-书籍上交提醒"], "turnin", L["在幽暗城且背包有可上交的书时提示"])
    OptRow(-76, L["探索-睡袋提醒"], "bag", L["本图有睡袋任务链的一步时提示"])
    OptRow(-98, L["探索-火炬提醒"], "torch", L["本图有守夜人火炬可拾取时提示"])
    OptRow(-120, L["探索-旗帜提醒"], "banner", L["进入血色修道院副本后，有未拾取的血色旗帜时提示"])
    OptRow(-142, L["副本-任务提醒"], "quest", L["本图有可接的副本任务时提示"])
    OptRow(-164, L["职业-技能提醒"], "spell", L["主城有训练师且技能可学时提示"])
    OptRow(-186, L["增益-食物提醒"], "food", L["没吃食物、缺少经验加成时提示"], "foodVoice")
    OptRow(-208, L["增益-睡袋提醒"], "rested", L["背包有睡袋且未休息或 buff 快到期时提示"], "restedVoice")

    local oph2 = opts:CreateFontString(nil, "OVERLAY")
    oph2:SetFont(ns.FONT, 14, "")
    oph2:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -236)
    oph2:SetText(L["窗口设置"])
    oph2:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    OptRow(-256, L["仅有待办时显示"], "onlyTodo", L["没有待办时隐藏圆形按钮"])

    local SIZES = { 24, 28, 32, 36, 40 }

    local szLabel = opts:CreateFontString(nil, "OVERLAY")
    szLabel:SetFont(ns.FONT, 14, "")
    szLabel:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -284)
    szLabel:SetText(L["待办图标大小"])
    szLabel:SetTextColor(TEXT[1], TEXT[2], TEXT[3])

    local szBtn = CreateFrame("Button", nil, opts, "BackdropTemplate")
    szBtn:SetSize(36, 20)
    szBtn:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -8, -279)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(szBtn, 6, ns.hui.layer.L2, "both", true, 1)
    end
    local szt = szBtn:CreateFontString(nil, "OVERLAY")
    szt:SetFont(ns.FONT, 14, "")
    szt:SetPoint("CENTER", szBtn, "CENTER", 0, 0)
    szt:SetTextColor(ACC[1], ACC[2], ACC[3])

    local function SyncSize()
        szt:SetText(tostring(tonumber(Cfg().icon) or 32))
    end

    szBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if not c then return end
        local cur = tonumber(c.icon) or 32
        local idx = 1
        for i = 1, #SIZES do
            if SIZES[i] == cur then idx = i end
        end
        c.icon = SIZES[idx % #SIZES + 1]
        SyncSize()
        ApplyOrbSize()
        if current then
            O.Update(current)
        else
            O.Refresh()
        end
    end)
    szBtn:SetScript("OnEnter", function()
        Tip(szBtn, L["待办图标大小"], L["点击切换待办圆球与条目的图标尺寸"])
    end)
    szBtn:SetScript("OnLeave", HideTip)

    gear:SetScript("OnClick", function()
        ns.PlaySound(1)
        if opts:IsShown() then
            opts:Hide()
            if current then O.Update(current) end
        else
            local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
            for k, cb in pairs(optCbs) do
                if cb.SetChecked then cb:SetChecked(c[k] and true or false)
                elseif cb.PaintVoice then cb:PaintVoice() end
            end
            SyncSize()
            local rx = (panel.GetRight and panel:GetRight() or 0) - 8
            local ty = (panel.GetTop and panel:GetTop() or 0) - 40
            opts:ClearAllPoints()
            opts:SetPoint("TOPRIGHT", UIParent, "BOTTOMLEFT", rx, ty)
            opts:Show()
        end
    end)
    gear:SetScript("OnEnter", function()
        gt:SetVertexColor(1, 1, 1)
        Tip(gear, L["提醒设置"], L["选择要提醒的内容"])
    end)
    gear:SetScript("OnLeave", function()
        gt:SetVertexColor(GLYPH, GLYPH, GLYPH)
        HideTip()
    end)

    btnOpen:SetScript("OnClick", function()
        ns.PlaySound(1)
        Close()
        if ns.Open then ns.Open() end
    end)

    btnSkip:SetScript("OnClick", function()
        ns.PlaySound(1)
        if ns.ZoneHint and ns.ZoneHint.IsSim and ns.ZoneHint.IsSim() then Close() return end
        local key = current and current.key
        if key and ns.ZoneHint then ns.ZoneHint.SkipSession(key) end
        if badge then badge:Hide() end
        lastN = 0
        Close()
    end)

    btnBlock:SetScript("OnClick", function()
        ns.PlaySound(1)
        if ns.ZoneHint and ns.ZoneHint.IsSim and ns.ZoneHint.IsSim() then Close() return end
        local key = current and current.key
        if key and ns.ZoneHint then
            local name = current and current.ctx and current.ctx.zone or key
            ns.ZoneHint.Block(key, name, "all")
        end
        if badge then badge:Hide() end
        lastN = 0
        Close()
        if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
    end)

    orbMenu = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
    orbMenu:SetHeight(64)
    orbMenu:SetFrameStrata("FULLSCREEN_DIALOG")
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(orbMenu, 8, "both", ns.hui.layer.L2)
        if ns.hui.SkinShadow then ns.hui.SkinShadow(orbMenu, nil, nil, 8) end
    end
    local oml1 = orbMenu:CreateFontString(nil, "OVERLAY")
    oml1:SetFont(ns.FONT, 13, "")
    oml1:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 12, -11)
    oml1:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    local omb1 = CreateFrame("Button", nil, orbMenu)
    omb1:SetSize(10, 28)
    omb1:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 0, 0)
    omb1:SetPoint("TOPRIGHT", orbMenu, "TOPRIGHT", 0, 0)
    omb1:SetScript("OnEnter", function()
        oml1:SetTextColor(ACC[1], ACC[2], ACC[3])
        Tip(omb1, L["仅有待办时显示"], L["没有待办时隐藏圆形按钮"])
    end)
    omb1:SetScript("OnLeave", function()
        oml1:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        HideTip()
    end)
    local oml2 = orbMenu:CreateFontString(nil, "OVERLAY")
    oml2:SetFont(ns.FONT, 13, "")
    oml2:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 12, -39)
    oml2:SetText(L["永久关闭"])
    oml2:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    local omb2 = CreateFrame("Button", nil, orbMenu)
    omb2:SetSize(10, 28)
    omb2:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 0, -30)
    omb2:SetPoint("TOPRIGHT", orbMenu, "TOPRIGHT", 0, -30)
    omb2:SetScript("OnEnter", function()
        oml2:SetTextColor(ACC[1], ACC[2], ACC[3])
        Tip(omb2, L["永久关闭"], L["等同于设置里的地图待办开关，可随时重新开启"])
    end)
    omb2:SetScript("OnLeave", function()
        oml2:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        HideTip()
    end)
    local function SyncMenuLabels()
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
        oml1:SetText(L["仅有待办时显示"] .. "：" .. ((c.onlyTodo and L["开"]) or L["关"]))
    end
    omb1:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if c then c.onlyTodo = not c.onlyTodo and true or false end
        SyncMenuLabels()
        if optCbs and optCbs.onlyTodo then optCbs.onlyTodo:SetChecked(c.onlyTodo and true or false) end
        if current then
            O.Update(current)
        else
            O.Refresh()
        end
    end)
    omb2:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if c then c.on = false end
        orbMenu:Hide()
        Close()
        if orb then orb:Hide() end
        if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
    end)
    orbMenu:Hide()

    local function ToggleOrbMenu()
        if orbMenu:IsShown() then
            orbMenu:Hide()
            return
        end
        SyncMenuLabels()
        local w = math.max(TextW(oml1, 60), TextW(oml2, 60)) + 24
        if w < 120 then w = 120 end
        orbMenu:SetWidth(w)
        orbMenu:ClearAllPoints()
        orbMenu:SetPoint("TOPLEFT", orb, "BOTTOMRIGHT", 4, -4)
        orbMenu:Show()
        menuOpenedAt = (GetTime and GetTime()) or 0
    end

    ApplyOrbSize()
    orb:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    orb:SetScript("OnClick", function(_, btn)
        ns.PlaySound(1)
        if btn == "RightButton" then
            ToggleOrbMenu()
        else
            if orbMenu then orbMenu:Hide() end
            Toggle()
        end
    end)

    orb:SetScript("OnEnter", function()
        hovered = true
        hideToken = hideToken + 1
        orb.revealed = true
        orb.ghostPending = false
        orb.ghostTok = (orb.ghostTok or 0) + 1
        if orb:GetAlpha() ~= 1 then orb:SetAlpha(1) end
        PaintRing((current and current.total) or 0)
        if icon then icon:SetVertexColor(1, 1, 1, 1) end
        local zone = (current and current.ctx and current.ctx.zone) or ""
        local n = (current and current.total) or 0
        local desc
        if n > 0 then
            desc = string.format(L["本图待办 %d"], n)
        else
            desc = L["本图暂无待办"]
        end
        Tip(orb, zone ~= "" and zone or L["当前地图"], desc, L["左键展开 · 右键永久关闭 · 拖拽移动"])
    end)

    orb:SetScript("OnLeave", function()
        hovered = false
        PaintRing((current and current.total) or 0)
        local gc = Cfg()
        if gc.on ~= false and gc.onlyTodo and (current and (current.total or 0) == 0) and not (opts and opts:IsShown()) and not (panel and panel:IsShown()) then
            O.ArmGhost()
        end
        if icon then icon:SetVertexColor(0.92, 0.93, 0.95, 1) end
        HideTip()
        if panel and panel:IsShown() then StartHideTimer() end
    end)

    orb:SetScript("OnDragStart", function()
        if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
        orb:StartMoving()
    end)

    orb:SetScript("OnDragStop", function()
        orb:StopMovingOrSizing()
        SavePos()
        if panel and panel:IsShown() then
            panel:ClearAllPoints()
            panel:SetPoint("LEFT", orb, "RIGHT", 8, 0)
        end
    end)

    panel:SetScript("OnEnter", function()
        hovered = true
        hideToken = hideToken + 1
    end)

    panel:SetScript("OnLeave", function()
        hovered = false
        StartHideTimer()
    end)

    local watcher = CreateFrame("Frame")
    watcher:RegisterEvent("GLOBAL_MOUSE_DOWN")
    watcher:SetScript("OnEvent", function()
        local now = (GetTime and GetTime()) or 0
        if orbMenu and orbMenu:IsShown() then
            if now - menuOpenedAt >= 0.2 and not orbMenu:IsMouseOver() and not orb:IsMouseOver() then
                orbMenu:Hide()
            end
            return
        end
        if not panel or not panel:IsShown() then return end
        if now - openedAt < 0.2 then return end
        if panel:IsMouseOver() then return end
        if opts and opts:IsShown() and opts:IsMouseOver() then return end
        if orb:IsMouseOver() then return end
        Close()
    end)

    if UISpecialFrames then
        local found = false
        for i = 1, #UISpecialFrames do
            if UISpecialFrames[i] == "DFZoneOrbPanel" then found = true break end
        end
        if not found then table.insert(UISpecialFrames, "DFZoneOrbPanel") end
    end
    panel:HookScript("OnHide", function() O.ArmGhost() end)

    if panel.title then panel.title:SetText("") end
    cards, heads, subRows = {}, {}, {}
end

function O.Refresh()
    if not (ns.ZoneHint and ns.ZoneHint.Collect) then return nil end
    local ctx = ns.ZoneHint.Context()
    local res = ns.ZoneHint.Collect(ctx)
    res.key = ns.ZoneHint.Key(ctx)
    O.Update(res)
    if (res.total or 0) == 0 then
        lastN = 0
        if badge then badge:Hide() end
        if not (opts and opts:IsShown()) then Close() end
    end
    return res
end

function O.ForceOpen(res)
    O.Update(res)
    Open()
end

function O.SetHeader(res)
    if not panel then return end
    local ctx = res and res.ctx
    local zone = ctx and ctx.zone or ""
    if zone == "" then zone = L["当前地图"] end
    if #zone > 12 then zone = zone:sub(1, 12) .. "..." end
    panel.title:SetText(zone)
    local n = (res and res.total) or 0
    if n > 0 then
        panel.count:SetText(string.format(L["本图待办 %d"], n))
    else
        panel.count:SetText(L["本图暂无待办"])
    end
end

local baseLayout = Layout
Layout = function(res)
    baseLayout(res)
    O.SetHeader(res)
end
