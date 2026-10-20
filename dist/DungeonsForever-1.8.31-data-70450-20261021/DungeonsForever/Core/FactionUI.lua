local _, ns = ...

local L = ns.L
local format = string.format
local floor = math.floor
local max = math.max
local min = math.min

local Host = ns.ProfHost
if not Host then return end

local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local MakeOutline, SetOutline = Host.MakeOutline, Host.SetOutline
local SetTip = Host.SetTip
local Unpack = Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local CONTENT_W = Host.CONTENT_W
local PAGE_INSET = Host.PAGE_INSET
local DG = Host.DG

local FD = ns.FactionsData
if type(FD) ~= "table" or #FD == 0 then return end

local GUTTER = (DG and type(DG.GUTTER) == "number") and DG.GUTTER or 8
local HUI = ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG and ns.hui or nil

local STANDINGS = {
    { label = L["仇恨"], bottom = -42000, top = -6001, span = 36000, vis = 3000, color = { 0x9E / 255, 0x32 / 255, 0x32 / 255 } },
    { label = L["敌对"], bottom = -6000, top = -3001, span = 3000, vis = 3000, color = { 0xC7 / 255, 0x4A / 255, 0x3C / 255 } },
    { label = L["冷淡"], bottom = -3000, top = -1, span = 3000, vis = 3000, color = { 0xD9 / 255, 0x82 / 255, 0x2B / 255 } },
    { label = L["中立"], bottom = 0, top = 2999, span = 3000, vis = 3000, color = { 0xD9 / 255, 0xB9 / 255, 0x3C / 255 } },
    { label = L["友善"], bottom = 3000, top = 8999, span = 6000, vis = 6000, color = { 0x6F / 255, 0xBF / 255, 0x5A / 255 } },
    { label = L["尊敬"], bottom = 9000, top = 20999, span = 12000, vis = 12000, color = { 0x2F / 255, 0x9E / 255, 0x7F / 255 } },
    { label = L["崇敬"], bottom = 21000, top = 41999, span = 21000, vis = 21000, color = { 0x3F / 255, 0x7F / 255, 0xA0 / 255 } },
    { label = L["崇拜"], bottom = 42000, top = 43000, span = 1000, vis = 1000, color = { 0xB5 / 255, 0x8F / 255, 0xD8 / 255 } },
}

local VIS_CUM = {}
do
    local acc = 0
    for i, t in ipairs(STANDINGS) do
        VIS_CUM[i] = acc
        acc = acc + t.vis
    end
end
local VIS_TOTAL = VIS_CUM[#STANDINGS] + STANDINGS[#STANDINGS].vis

local REWARD_TIERS = { "friendly", "honored", "revered", "exalted", "neutral" }
local TIER_OF_KEY = { friendly = 5, honored = 6, revered = 7, exalted = 8, neutral = 4 }

local SIDE_INFO = {
    alliance = { text = L["联盟"], color = { 0x3F / 255, 0x7F / 255, 0xA0 / 255 },
        icon = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance" },
    horde = { text = L["部落"], color = { 0xC7 / 255, 0x4A / 255, 0x3C / 255 },
        icon = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde" },
    neutral = { text = L["中立"], color = { 0xD9 / 255, 0xB9 / 255, 0x3C / 255 } },
}

local OPTS = {
    { key = "ally", text = L["本阵营"] },
    { key = "enemy", text = L["敌对阵营"] },
    { key = "neutral", text = L["中立"] },
}

local GOLD = { 0xE8 / 255, 0xC6 / 255, 0x6A / 255 }

local FV = {}
ns.FactionModule = FV

FV.X = PAGE_INSET
FV.W = CONTENT_W - 2 * FV.X
FV.LW = 330
FV.RW = FV.W - FV.LW - GUTTER
FV.CARD_TOP = GUTTER
FV.CARD_BOT = PAGE_INSET
FV.PAD = 12
FV.LROW_W = FV.LW - FV.PAD * 2 - 14
FV.ROW_H = 36
FV.LIST_GAP = 4
FV.COLS = 3

local function Cfg()
    local db = ns.DB()
    db.factions = db.factions or {}
    local c = db.factions
    if c.ally == nil then c.ally = true end
    if c.enemy == nil then c.enemy = false end
    if c.neutral == nil then c.neutral = true end
    if c.search == nil then c.search = "" end
    return c
end

local function PlayerSide()
    local ok, side = pcall(UnitFactionGroup, "player")
    if ok and side == "Horde" then return "horde" end
    return "alliance"
end

local function NumStr(n)
    n = floor(tonumber(n) or 0)
    local neg = n < 0
    if neg then n = -n end
    local s = tostring(n)
    local rev = s:reverse():gsub("(%d%d%d)", "%1,")
    local out = rev:reverse()
    if out:sub(1, 1) == "," then out = out:sub(2) end
    return (neg and "-" or "") .. out
end

local function TextW(s)
    local w = 0
    local bytes = { string.byte(s, 1, #s) }
    for _, ch in ipairs(bytes) do
        if ch >= 128 then w = w + 13 else w = w + 7 end
    end
    return w
end

local function StandingIdx(v)
    v = tonumber(v) or 0
    for i = #STANDINGS, 1, -1 do
        if v >= STANDINGS[i].bottom then return i end
    end
    return 1
end

local function VisPos(v)
    v = tonumber(v) or 0
    if v <= STANDINGS[1].bottom then return 0 end
    if v >= STANDINGS[#STANDINGS].top then return VIS_TOTAL end
    for i = #STANDINGS, 1, -1 do
        local t = STANDINGS[i]
        if v >= t.bottom then
            return VIS_CUM[i] + (v - t.bottom) / t.span * t.vis
        end
    end
    return 0
end

local function FacData(id)
    if type(id) == "number" and type(C_Reputation) == "table" and type(C_Reputation.GetFactionDataByID) == "function" then
        local ok, d = pcall(C_Reputation.GetFactionDataByID, id)
        if ok and type(d) == "table" then return d end
    end
    return nil
end

local function FacName(x)
    local d = FacData(x.id)
    if d and type(d.name) == "string" and d.name ~= "" then return d.name end
    if type(x.id) == "number" and type(GetFactionInfoByID) == "function" then
        local ok, nm = pcall(GetFactionInfoByID, x.id)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return x.name or ""
end

local function ClientDesc(x)
    local d = FacData(x.id)
    if d and type(d.description) == "string" and d.description ~= "" then return d.description end
    if type(x.id) == "number" and type(GetFactionInfoByID) == "function" then
        local ok, _, desc = pcall(GetFactionInfoByID, x.id)
        if ok and type(desc) == "string" and desc ~= "" then return desc end
    end
    return nil
end

local function LiveValue(id)
    if type(id) ~= "number" then return nil end
    local earned
    local d = FacData(id)
    if d then
        if type(d.currentStanding) == "number" then
            earned = d.currentStanding
        elseif type(d.earnedValue) == "number" then
            earned = d.earnedValue
        end
    end
    if not earned and type(GetFactionInfoByID) == "function" then
        local ok, _, _, _, _, _, ev = pcall(GetFactionInfoByID, id)
        if ok and type(ev) == "number" then earned = ev end
    end
    if not earned then return nil end
    if earned < STANDINGS[1].bottom then earned = STANDINGS[1].bottom end
    if earned > STANDINGS[#STANDINGS].top then earned = STANDINGS[#STANDINGS].top end
    return earned
end

local function FacBySel(sel)
    if type(sel) ~= "number" then return nil end
    for _, x in ipairs(FD) do
        if x.id == sel then return x end
    end
    return nil
end

local function QMLoc(x)
    if not (type(x) == "table" and type(x.id) == "number") then return nil end
    local q = type(ns.FactionQM) == "table" and ns.FactionQM[x.id]
    if type(q) == "table" and type(q[1]) == "number" and type(q[2]) == "number"
        and type(q[3]) == "number" and type(q[4]) == "number" then
        return q[1], q[2], q[3], q[4]
    end
    return nil
end

function FV:MarkQM()
    local x = FacBySel(Cfg().sel)
    local npc, mapID, qx, qy = QMLoc(x)
    if not npc then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该阵营的军需官位置"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint
        and (not C_Map.CanSetUserWaypointOnMap or C_Map.CanSetUserWaypointOnMap(mapID)) then
        local ok, wp = pcall(UiMapPoint.CreateFromCoordinates, mapID, qx / 100, qy / 100)
        if ok and wp then pcall(C_Map.SetUserWaypoint, wp) end
        if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
            pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    end
end

function FV:ShowQMTip(owner)
    if not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine(L["点击：在地图上标记军需官位置"], 1, 0.82, 0)
    local x = FacBySel(Cfg().sel)
    local npc, mapID, qx, qy = QMLoc(x)
    if npc then
        local zn = ""
        if C_Map and C_Map.GetMapInfo then
            local ok, mi = pcall(C_Map.GetMapInfo, mapID)
            if ok and type(mi) == "table" and type(mi.name) == "string" then zn = mi.name .. " " end
        end
        GameTooltip:AddLine(zn .. format("%.1f, %.1f", qx, qy), 0.75, 0.75, 0.75)
    else
        GameTooltip:AddLine(L["未收录该阵营的军需官位置"], 0.6, 0.6, 0.6)
    end
    GameTooltip:Show()
end

local function SideAllowed(x, pside, c)
    if x.side == "neutral" then return c.neutral and true or false end
    if x.side == pside then return c.ally and true or false end
    return c.enemy and true or false
end

local function SearchHit(x, needle)
    if needle == "" then return true end
    local nm = FacName(x):lower()
    if nm:find(needle, 1, true) then return true end
    local fb = (x.name or ""):lower()
    return fb:find(needle, 1, true) ~= nil
end

local function HasRewards(x)
    local r = x.rewards
    if type(r) ~= "table" then return false end
    for _, key in ipairs(REWARD_TIERS) do
        local ids = r[key]
        if type(ids) == "table" and #ids > 0 then return true end
    end
    return false
end

local function PassFilter(x, pside, c)
    if not SideAllowed(x, pside, c) then return false end
    if not HasRewards(x) then return false end
    return SearchHit(x, c.search or "")
end

local function WheelTo(scroll, child, delta)
    if DG and DG.WheelScroll then
        DG.WheelScroll(scroll, child, delta)
    end
end

local function Cull(scroll, items)
    if not (scroll and items and scroll.IsShown and scroll:IsShown()) then return end
    local gt = scroll.GetTop and scroll:GetTop()
    if type(gt) ~= "number" then return end
    local viewH = scroll.GetHeight and scroll:GetHeight()
    if type(viewH) ~= "number" then return end
    local v = scroll.GetVerticalScroll and scroll:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    local top, bot = v - 2, v + viewH + 2
    for _, f in ipairs(items) do
        if not f.__active then
            f:Hide()
        else
            local vt = f.__vtop
            if type(vt) == "number" then
                if (vt + (f.__vh or 20)) > top and vt < bot then f:Show() else f:Hide() end
            end
        end
    end
end

local function RoundBG(f, r, color)
    if HUI then
        local fill, border = ns.hui.BuildRoundedBG(f, r, color or ns.hui.layer.L1, "both", true, 1)
        return fill, border
    end
    f.edge = f:CreateTexture(nil, "BACKGROUND")
    f.edge:SetAllPoints(f)
    f.edge:SetColorTexture(1, 1, 1, 0.10)
    f.bg = f:CreateTexture(nil, "BACKGROUND", nil, 1)
    f.bg:SetPoint("TOPLEFT", f, "TOPLEFT", 1, -1)
    f.bg:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -1, 1)
    f.bg:SetColorTexture(0x10 / 255, 0x13 / 255, 0x1A / 255, 1)
    return nil, nil
end

local function SideText(side)
    local info = SIDE_INFO[side]
    if not info then return "" end
    local c = info.color
    return format("|cff%02x%02x%02x%s|r", floor(c[1] * 255), floor(c[2] * 255), floor(c[3] * 255), info.text)
end

local function MakeChip(parent)
    local f = CreateFrame("Frame", nil, parent)
    f:SetHeight(20)
    local fill, border = RoundBG(f, 6, HUI and ns.hui.layer.L2 or nil)
    f.__border = border
    f.txt = MakeFS(f, 14, C_TEXT, "CENTER")
    f.txt:SetAllPoints(f)
    f.txt:SetWordWrap(false)
    return f
end

local function PaintChip(f, text, color)
    f.txt:SetText(text)
    local tw = (f.txt.GetStringWidth and f.txt:GetStringWidth()) or TextW(text)
    if type(tw) ~= "number" or tw <= 0 then tw = TextW(text) end
    f:SetWidth(16 + tw)
    if f.__border and color then
        for _, t in ipairs(f.__border) do t:SetVertexColor(color[1], color[2], color[3]) end
    end
    if color then
        f.txt:SetTextColor(color[1], color[2], color[3])
    else
        f.txt:SetTextColor(Unpack(C_TEXT))
    end
end

FV.Build = function(page)
    if FV.built or FV.building then return end
    FV.building = true
    ns.PhasedStart(34, coroutine.create(function()
    FV.page = page

    local leftCard = CreateFrame("Frame", nil, page)
    leftCard:SetPoint("TOPLEFT", page, "TOPLEFT", FV.X, -FV.CARD_TOP)
    leftCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", FV.X + FV.LW, FV.CARD_BOT)
    RoundBG(leftCard, 6, HUI and ns.hui.layer.L1 or nil)
    FV.leftCard = leftCard
    coroutine.yield()

    local rightCard = CreateFrame("Frame", nil, page)
    rightCard:SetPoint("TOPLEFT", page, "TOPLEFT", FV.X + FV.LW + GUTTER, -FV.CARD_TOP)
    rightCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -FV.X, FV.CARD_BOT)
    RoundBG(rightCard, 6, HUI and ns.hui.layer.L1 or nil)
    FV.rightCard = rightCard
    coroutine.yield()

    local sb = CreateFrame("Frame", nil, leftCard)
    sb:SetSize(FV.LW - FV.PAD * 2 - 88 - GUTTER, 24)
    sb:SetPoint("TOPLEFT", leftCard, "TOPLEFT", FV.PAD, -10)
    RoundBG(sb, 8, HUI and ns.hui.layer.L2 or nil)
    FV.searchBox = sb
    local eb = CreateFrame("EditBox", nil, sb)
    eb:SetAllPoints()
    eb:SetFontObject("GameFontHighlightSmall")
    eb:SetTextInsets(6, 6, 0, 0)
    eb:SetAutoFocus(false)
    eb:SetMaxLetters(30)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    eb:SetScript("OnTextChanged", function(self)
        local c = Cfg()
        c.search = string.lower(self:GetText() or "")
        FV.searchPH:SetShown(self:GetText() == "")
        FV.RequestRender()
    end)
    FV.searchPH = MakeFS(sb, 14, C_DIM, "LEFT")
    FV.searchPH:SetPoint("LEFT", sb, "LEFT", 8, 0)
    FV.searchPH:SetText(L["搜索阵营…"])
    coroutine.yield()

    local fb = NewButton(leftCard, "▽ " .. L["筛选"], 88, 24, 14)
    fb:SetPoint("TOPRIGHT", leftCard, "TOPRIGHT", -FV.PAD, -10)
    if HUI and ns.hui.ACCENT then
        MakeOutline(fb, Unpack(ns.hui.ACCENT))
    else
        MakeOutline(fb, 1, 0.82, 0)
    end
    fb:SetScript("OnClick", function()
        ns.PlaySound(1)
        FV:SetPopupShown(not FV.pop:IsShown())
    end)
    FV.filterBtn = fb
    coroutine.yield()

    local popMask = CreateFrame("Frame", nil, page)
    popMask:SetAllPoints(page)
    popMask:EnableMouse(true)
    popMask:SetScript("OnMouseDown", function() FV:SetPopupShown(false) end)
    popMask:Hide()
    FV.popMask = popMask
    coroutine.yield()

    local pop = CreateFrame("Frame", nil, page)
    pop:SetSize(150, #OPTS * 26 + 14)
    pop:EnableMouse(true)
    pop:Hide()
    FV.pop = pop
    RoundBG(pop, 6, HUI and ns.hui.layer.L3 or nil)
    FV.optRows = {}
    for i, opt in ipairs(OPTS) do
        local bt = CreateFrame("Button", nil, pop)
        bt:SetSize(136, 26)
        bt:SetPoint("TOPLEFT", pop, "TOPLEFT", 7, -7 - (i - 1) * 26)
        local boxF = CreateFrame("Frame", nil, bt)
        boxF:SetSize(18, 18)
        boxF:SetPoint("LEFT", bt, "LEFT", 4, 0)
        bt.boxF = boxF
        bt.ring = boxF:CreateTexture(nil, "ARTWORK")
        bt.ring:SetAllPoints()
        bt.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
        bt.disc = boxF:CreateTexture(nil, "ARTWORK")
        bt.disc:SetAllPoints()
        bt.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        bt.tick = boxF:CreateTexture(nil, "OVERLAY")
        bt.tick:SetAllPoints()
        bt.tick:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
        bt.label = MakeFS(bt, 14, C_TEXT, "LEFT")
        bt.label:SetPoint("LEFT", boxF, "RIGHT", 7, 0)
        bt.label:SetText(opt.text)
        bt:SetScript("OnClick", function()
            ns.PlaySound(1)
            local c = Cfg()
            c[opt.key] = not c[opt.key]
            FV:SyncPopup()
            FV:PaintList()
        end)
        FV.optRows[i] = bt
    end
    coroutine.yield()

    local baseLv = (page.GetFrameLevel and type(page:GetFrameLevel()) == "number") and page:GetFrameLevel() or 0
    popMask:SetFrameLevel(baseLv + 30)
    pop:SetFrameLevel(baseLv + 31)

    local scroll = CreateFrame("ScrollFrame", nil, leftCard)
    scroll:SetPoint("TOPLEFT", leftCard, "TOPLEFT", FV.PAD, -44)
    scroll:SetPoint("BOTTOMRIGHT", leftCard, "BOTTOMRIGHT", -FV.PAD, FV.PAD)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(scroll, FV.lChild, delta)
        FV:CullLeft()
    end)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(FV.LW - FV.PAD * 2, 10)
    scroll:SetScrollChild(child)
    FV.lScroll, FV.lChild = scroll, child
    scroll:SetScript("OnUpdate", function(_, dt)
        FV.__syncT = (FV.__syncT or 0) + (dt or 0)
        if FV.__syncT < 0.1 then return end
        FV.__syncT = 0
        FV:SyncHover()
    end)
    scroll:HookScript("OnShow", function() FV:CullLeft() end)
    coroutine.yield()

    local vbar = CreateFrame("Frame", nil, leftCard, "BackdropTemplate")
    if HUI and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(vbar, 3, ns.hui.layer.L2)
    else
        vbar:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        vbar:SetBackdropColor(0, 0, 0, 0.25)
        vbar:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    vbar:SetWidth(9)
    vbar:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", -1, -2)
    vbar:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", -1, 2)
    vbar:SetFrameLevel((scroll:GetFrameLevel() or 0) + 10)
    vbar:Hide()
    local vthumb = CreateFrame("Button", nil, vbar)
    vthumb:SetWidth(6)
    vthumb:EnableMouse(true)
    local vtp = nil
    if HUI and ns.hui.BuildCapsule then
        vtp = ns.hui.BuildCapsule(vthumb, 2, ns.hui.layer.L4)
    else
        local vtx = vthumb:CreateTexture(nil, "OVERLAY")
        vtx:SetAllPoints()
        vtx:SetColorTexture(1, 1, 1, 0.30)
        vtp = { vtx }
    end
    vthumb:SetScript("OnEnter", function()
        if not vtp then return end
        local c5 = ns.hui.layer and ns.hui.layer.L5
        if not c5 then return end
        for _, t in ipairs(vtp) do t:SetVertexColor(c5[1], c5[2], c5[3]) end
    end)
    vthumb:SetScript("OnLeave", function()
        if not vtp then return end
        local c4 = ns.hui.layer and ns.hui.layer.L4
        if not c4 then return end
        for _, t in ipairs(vtp) do t:SetVertexColor(c4[1], c4[2], c4[3]) end
    end)
    vthumb:SetPoint("TOP", vbar, "TOP", 0, -1)
    local function UpdateLeftBar()
        local sc, ch = FV.lScroll, FV.lChild
        if not (sc and ch) then return end
        if not sc:IsShown() then vbar:Hide() return end
        local viewH = tonumber(sc.GetHeight and sc:GetHeight())
        local contentH = tonumber(ch.GetHeight and ch:GetHeight())
        if not (viewH and contentH) or contentH <= viewH + 2 or viewH <= 0 then
            vbar:Hide()
            return
        end
        vbar:Show()
        local trackH = vbar:GetHeight() - 2
        local maxScroll = contentH - viewH
        local v = tonumber(sc.GetVerticalScroll and sc:GetVerticalScroll()) or 0
        local frac = min(1, max(0, v / maxScroll))
        local th = max(24, trackH * viewH / contentH)
        vthumb:SetHeight(th)
        vthumb:ClearAllPoints()
        vthumb:SetPoint("TOP", vbar, "TOP", 0, -1 - frac * (trackH - th))
    end
    FV.UpdateLeftBar = UpdateLeftBar
    scroll:HookScript("OnVerticalScroll", function() UpdateLeftBar() end)
    vthumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent.GetEffectiveScale and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = FV.lScroll:GetVerticalScroll()
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = vbar:GetHeight() - 2
            local span = trackH - vthumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = FV.lChild:GetHeight() - FV.lScroll:GetHeight()
            FV.lScroll:SetVerticalScroll(min(maxScroll, max(0, sc0 + (cy0 - cy) / span * maxScroll)))
            FV:CullLeft()
        end)
    end)
    vthumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    vthumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    coroutine.yield()

    FV.rows = {}
    for i = 1, #FD do
        local r = CreateFrame("Button", nil, child)
        r:SetSize(FV.LROW_W, FV.ROW_H)
        if HUI and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(r, 6, 2)
        end
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -5)
        r.name:SetWidth(FV.LROW_W - 60)
        r.name:SetWordWrap(false)
        r.sub = MakeFS(r, 14, C_GREY, "LEFT")
        r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -22)
        r.sub:SetWordWrap(false)
        r.badge = MakeFS(r, 14, C_TEXT, "RIGHT")
        r.badge:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -11)
        r:EnableMouse(true)
        r:SetScript("OnEnter", function(self)
            if self.__huiCard and ns.hui.HuiCardState then
                ns.hui.HuiCardState(self, "hover")
                self.__hst = "hover"
            end
            if self.__tip and SetTip then SetTip(self, self.__tip) end
        end)
        r:SetScript("OnLeave", function(self)
            if self.__huiCard and ns.hui.HuiCardState then
                ns.hui.HuiCardState(self, "norm")
                self.__hst = "norm"
            end
            GameTooltip:Hide()
        end)
        r:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            Cfg().sel = self.__fid
            FV:PaintList()
            FV:PaintDetail()
        end)
        r:SetScript("OnMouseWheel", function(_, delta)
            WheelTo(scroll, child, delta)
            FV:CullLeft()
        end)
        r:Hide()
        FV.rows[i] = r
        if i % 14 == 0 then coroutine.yield() end
    end
    coroutine.yield()
    FV:SyncPopup()
    FV:PaintList()
    coroutine.yield()

    local dScroll = CreateFrame("ScrollFrame", nil, rightCard)
    dScroll:SetPoint("TOPLEFT", rightCard, "TOPLEFT", 0, 0)
    dScroll:SetPoint("BOTTOMRIGHT", rightCard, "BOTTOMRIGHT", 0, 0)
    dScroll:EnableMouseWheel(true)
    dScroll:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(dScroll, FV.dChild, delta)
        FV:CullRight()
    end)
    local dChild = CreateFrame("Frame", nil, dScroll)
    dChild:SetSize(FV.RW, 10)
    dScroll:SetScrollChild(dChild)
    FV.dScroll, FV.dChild = dScroll, dChild
    dScroll:HookScript("OnShow", function() FV:CullRight() end)
    coroutine.yield()

    FV.dIcon = dChild:CreateTexture(nil, "ARTWORK")
    FV.dIcon:SetSize(20, 20)
    FV.dTitle = MakeFS(dChild, 16, C_WHITE, "LEFT")
    FV.dDesc = MakeFS(dChild, 14, C_GREY, "LEFT")

    FV.dReadout = MakeChip(dChild)
    FV.barTrack = CreateFrame("Frame", nil, dChild)
    FV.barTrack:SetHeight(14)
    if HUI and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(FV.barTrack, 7, ns.hui.layer.L0)
    else
        FV.barTrack.bg = FV.barTrack:CreateTexture(nil, "BACKGROUND")
        FV.barTrack.bg:SetAllPoints(FV.barTrack)
        FV.barTrack.bg:SetColorTexture(0x0A / 255, 0x0C / 255, 0x10 / 255, 1)
    end
    FV.segs = {}
    for i = 1, #STANDINGS do
        local seg = FV.barTrack:CreateTexture(nil, "BORDER")
        seg:SetHeight(8)
        seg:SetColorTexture(STANDINGS[i].color[1], STANDINGS[i].color[2], STANDINGS[i].color[3])
        seg:Hide()
        FV.segs[i] = seg
    end
    FV.ticks = {}
    for i = 1, #STANDINGS - 1 do
        local tk = FV.barTrack:CreateTexture(nil, "OVERLAY")
        tk:SetSize(1, 8)
        local dv = HUI and ns.hui.layer and ns.hui.layer.DIV
        if dv then
            tk:SetColorTexture(dv[1], dv[2], dv[3], dv[4] or 1)
        else
            tk:SetColorTexture(0x1B / 255, 0x20 / 255, 0x29 / 255, 1)
        end
        tk:Hide()
        FV.ticks[i] = tk
    end
    FV.labMin = MakeFS(dChild, 14, C_DIM, "LEFT")
    FV.labMid = MakeFS(dChild, 14, C_DIM, "CENTER")
    FV.labMax = MakeFS(dChild, 14, C_DIM, "RIGHT")
    FV.cursor = FV.barTrack:CreateTexture(nil, "OVERLAY")
    FV.cursor:SetSize(3, 22)
    FV.cursor:SetColorTexture(GOLD[1], GOLD[2], GOLD[3])
    FV.cursor:Hide()
    coroutine.yield()

    FV.rSeps = {}
    for i = 1, #REWARD_TIERS do
        local s = CreateFrame("Frame", nil, dChild)
        s:SetSize(FV.RW - 28, 20)
        s.line = s:CreateTexture(nil, "BACKGROUND")
        s.line:SetPoint("BOTTOMLEFT", s, "BOTTOMLEFT", 0, 4)
        s.line:SetPoint("BOTTOMRIGHT", s, "BOTTOMRIGHT", 0, 4)
        s.line:SetHeight(1)
        s.label = MakeFS(s, 14, C_TEXT, "LEFT")
        s.label:SetPoint("BOTTOMLEFT", s, "BOTTOMLEFT", 8, 7)
        s:Hide()
        FV.rSeps[i] = s
    end
    coroutine.yield()

    FV.rCards = {}

    local qb = NewButton(rightCard, L["军需官位置"], 104, 24, 14)
    qb:SetPoint("TOPRIGHT", rightCard, "TOPRIGHT", -14, -10)
    local qfs = qb:GetFontString()
    local qt = qb:CreateTexture(nil, "OVERLAY")
    qt:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\EntryPin")
    qt:SetSize(12, 12)
    qt:SetPoint("LEFT", qb, "LEFT", 4, 0)
    if qfs then
        qfs:ClearAllPoints()
        qfs:SetPoint("TOPLEFT", qb, "TOPLEFT", 18, 0)
        qfs:SetPoint("BOTTOMRIGHT", qb, "BOTTOMRIGHT", -2, 0)
        qfs:SetJustifyH("CENTER")
    end
    qb:SetScript("OnClick", function() FV:MarkQM() end)
    qb:SetScript("OnEnter", function(self) FV:ShowQMTip(self) end)
    qb:SetScript("OnLeave", function() GameTooltip:Hide() end)
    FV.qmBtn = qb

    FV.built = true
    FV.building = false
    FV:PaintDetail()
    end))
end

function FV:CullLeft()
    if not FV.lCull then return end
    Cull(FV.lScroll, FV.lCull)
    if FV.UpdateLeftBar then FV.UpdateLeftBar() end
end

function FV:CullRight()
    if not FV.dCull then return end
    Cull(FV.dScroll, FV.dCull)
end

local function MouseOverSafe(f)
    if not (type(GetCursorPosition) == "function"
        and f.GetEffectiveScale and f.GetLeft and f.GetBottom and f.GetWidth and f.GetHeight) then
        return false
    end
    local ok, cx, cy = pcall(GetCursorPosition)
    if not ok or type(cx) ~= "number" or type(cy) ~= "number" then return false end
    local s = f:GetEffectiveScale()
    if type(s) ~= "number" or s <= 0 then return false end
    cx, cy = cx / s, cy / s
    local l, b, w, h = f:GetLeft(), f:GetBottom(), f:GetWidth(), f:GetHeight()
    if type(l) ~= "number" or type(b) ~= "number"
        or type(w) ~= "number" or type(h) ~= "number" then return false end
    return cx >= l and cx <= l + w and cy >= b and cy <= b + h
end

function FV:SyncHover()
    if not (FV.lScroll and FV.lScroll.IsShown and FV.lScroll:IsShown()) then return end
    if not FV.dCull then return end
    for _, f in ipairs(FV.lCull) do
        if f.__active and f.__huiCard and f.__fid and f.IsShown and f:IsShown() then
            local st = MouseOverSafe(f) and "hover" or "norm"
            if f.__hst ~= st and ns.hui and ns.hui.HuiCardState then
                ns.hui.HuiCardState(f, st)
                f.__hst = st
            end
        end
    end
    for _, f in ipairs(FV.dCull) do
        if f.__active and f.__huiCard and f.IsShown and f:IsShown() then
            local st = MouseOverSafe(f) and "hover" or "norm"
            if f.__hst ~= st and ns.hui and ns.hui.HuiCardState then
                ns.hui.HuiCardState(f, st)
                f.__hst = st
            end
        end
    end
end

function FV:SetPopupShown(on)
    FV.popMask:SetShown(on and true or false)
    FV.pop:SetShown(on and true or false)
    if on then
        FV.pop:ClearAllPoints()
        FV.pop:SetPoint("TOPRIGHT", FV.filterBtn, "BOTTOMRIGHT", 0, -4)
        FV:SyncPopup()
    end
end

function FV:SyncPopup()
    local c = Cfg()
    local n = 0
    for i, opt in ipairs(OPTS) do
        local bt = FV.optRows[i]
        local on = c[opt.key] and true or false
        bt.ring:SetShown(not on)
        bt.disc:SetShown(on)
        bt.tick:SetShown(on)
        if on then
            bt.disc:SetVertexColor(0.91, 0.78, 0.42)
            bt.tick:SetVertexColor(1, 1, 1, 1)
        else
            bt.ring:SetVertexColor(0.42, 0.41, 0.38, 0.9)
        end
        if on then n = n + 1 end
    end
    if n >= #OPTS then
        FV.filterBtn:SetText("▽ " .. L["筛选"])
    else
        FV.filterBtn:SetText("▽ " .. L["筛选"] .. " " .. n)
    end
end

local function PY()
    if coroutine.running and coroutine.running() then coroutine.yield() end
end

function FV:PaintList()
    if not FV.rows then return end
    local c = Cfg()
    local pside = PlayerSide()
    FV.lCull = {}
    local nRow = 0
    local y = 0
    for _, x in ipairs(FD) do
        if PassFilter(x, pside, c) then
            nRow = nRow + 1
            local r = FV.rows[nRow]
            if not r then break end
            r.__active = true
            r.__vtop = y
            r.__vh = FV.ROW_H
            r.__fid = x.id
            r.name:SetText(FacName(x))
            local __lv = LiveValue(x.id) or x.start
            local __ti = StandingIdx(__lv)
            local __sc = STANDINGS[__ti].color
            r.name:SetTextColor(__sc[1], __sc[2], __sc[3])
            r.sub:SetText(STANDINGS[__ti].label .. " " .. NumStr(__lv - STANDINGS[__ti].bottom)
                .. "/" .. NumStr(STANDINGS[__ti].span))
            r.badge:SetText(SideText(x.side))
            local sel = (c.sel == x.id)
            if HUI and r.__huiCard and ns.hui.HuiCardState then
                ns.hui.HuiCardState(r, "norm")
                r.__hst = "norm"
            end
            if sel then
                if HUI and ns.hui.BuildRoundBorder then
                    if r.__selBorder then
                        for _, t in ipairs(r.__selBorder) do
                            t:SetVertexColor(GOLD[1], GOLD[2], GOLD[3])
                            t:Show()
                        end
                    else
                        r.__selBorder = ns.hui.BuildRoundBorder(r, 6, GOLD, r, "OVERLAY")
                    end
                else
                    MakeOutline(r, 1, 0.82, 0)
                end
            else
                if r.__selBorder then
                    for _, t in ipairs(r.__selBorder) do t:Hide() end
                end
            end
            r.__tip = FacName(x) .. "\n" .. SIDE_INFO[x.side].text .. " · " .. L["起始声望"] .. " " .. NumStr(x.start)
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", FV.lChild, "TOPLEFT", 0, -y)
            r:Show()
            FV.lCull[#FV.lCull + 1] = r
            y = y + FV.ROW_H + FV.LIST_GAP
            if nRow % 4 == 0 then PY() end
        end
    end
    for i = nRow + 1, #FV.rows do
        FV.rows[i].__active = false
        FV.rows[i]:Hide()
    end
    local selX = FacBySel(c.sel)
    if nRow > 0 and not (selX and PassFilter(selX, pside, c)) then
        c.sel = FV.rows[1].__fid
    end
    FV.lChild:SetHeight(max(10, y + 10))
    local __v = tonumber(FV.lScroll.GetVerticalScroll and FV.lScroll:GetVerticalScroll())
    local __mx = (tonumber(FV.lChild.GetHeight and FV.lChild:GetHeight()) or 0)
        - (tonumber(FV.lScroll.GetHeight and FV.lScroll:GetHeight()) or 0)
    if type(__v) == "number" and __mx >= 0 and __v > __mx then
        FV.lScroll:SetVerticalScroll(__mx)
    end
    FV:CullLeft()
    if FV.UpdateLeftBar then FV.UpdateLeftBar() end
end

function FV:PaintRewardCard(f, id)
    f.__id = id
    local nm, ok
    if DG and DG.ItemName then nm, ok = DG.ItemName(id) end
    if ok then
        local budget = f.__nameW or 200
        f.name:SetText(DG.FitText and DG.FitText(nm, 14, budget) or nm)
        if DG.QColor and DG.QualOf then
            local qr, qg, qb = DG.QColor(DG.QualOf(id))
            if qr then f.name:SetTextColor(qr, qg, qb) end
        end
        local meta = ""
        if DG.ItemMeta then meta = DG.ItemMeta(id) or "" end
        f.meta:SetText(type(meta) == "string" and meta or "")
    else
        f.name:SetText(format(L["物品 #%d"], id or 0))
        f.name:SetTextColor(Unpack(C_GREY))
        f.meta:SetText("")
        if DG and DG.RequestItem then DG.RequestItem(id) end
    end
    if DG and DG.ItemIcon then
        f.iconTex:SetTexture(DG.ItemIcon(id))
    end
end

function FV.OnItemData(itemID)
    if not FV.built then return end
    for _, f in ipairs(FV.rCards) do
        if f.__id == itemID and f:IsShown() then FV:PaintRewardCard(f, itemID) end
    end
end

function FV:PaintDetail()
    if not FV.segs then return end
    local c = Cfg()
    local x = FacBySel(c.sel)
    FV.dCull = {}
    for _, seg in ipairs(FV.segs) do seg:Hide() end
    for _, tk in ipairs(FV.ticks) do tk:Hide() end
    FV.cursor:Hide()
    local innerW = FV.RW - 28
    local cardW = floor((innerW - (FV.COLS - 1) * GUTTER) / FV.COLS)
    local nCard = 0
    local y = 12

    if not x then
        FV.dTitle:ClearAllPoints()
        FV.dTitle:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", 14, -y)
        FV.dTitle:SetText("")
        FV.dChild:SetHeight(10)
        FV.__lastSel = nil
        FV:CullRight()
        return
    end

    local info = SIDE_INFO[x.side] or SIDE_INFO.neutral

    FV.dIcon:SetTexture(info.icon or "")
    FV.dIcon:SetShown(type(info.icon) == "string")
    FV.dIcon:ClearAllPoints()
    FV.dIcon:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", 14, -y)
    FV.dIcon.__active = true
    FV.dIcon.__vtop = y
    FV.dIcon.__vh = 20
    FV.dCull[#FV.dCull + 1] = FV.dIcon

    FV.dTitle:ClearAllPoints()
    FV.dTitle:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", (info.icon and 42 or 14), -(y - 1))
    FV.dTitle:SetText(FacName(x))
    FV.dTitle.__active = true
    FV.dTitle.__vtop = y - 1
    FV.dTitle.__vh = 24
    FV.dCull[#FV.dCull + 1] = FV.dTitle
    y = y + 26

    local desc = ClientDesc(x) or ""
    local descH = 0
    if desc ~= "" then
        FV.dDesc:ClearAllPoints()
        FV.dDesc:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", 14, -y)
        FV.dDesc:SetWidth(innerW)
        FV.dDesc:SetText(desc)
        local gh = FV.dDesc.GetStringHeight and FV.dDesc:GetStringHeight() or 0
        descH = (type(gh) == "number" and gh > 0) and gh or 16
        FV.dDesc.__active = true
        FV.dDesc.__vtop = y
        FV.dDesc.__vh = descH
        FV.dCull[#FV.dCull + 1] = FV.dDesc
    else
        FV.dDesc:SetText("")
        FV.dDesc.__active = false
    end
    y = y + descH + 10

    local live = LiveValue(x.id)
    local curVal = live or x.start
    local curTier = StandingIdx(curVal)
    local pos = VisPos(curVal)

    FV.dReadout:ClearAllPoints()
    FV.dReadout:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", 14, -y)
    PaintChip(FV.dReadout, STANDINGS[curTier].label .. " " .. NumStr(curVal - STANDINGS[curTier].bottom)
        .. "/" .. NumStr(STANDINGS[curTier].span), STANDINGS[curTier].color)
    FV.dReadout.__active = true
    FV.dReadout.__vtop = y
    FV.dReadout.__vh = 22
    FV.dCull[#FV.dCull + 1] = FV.dReadout

    local INSET = 3
    local barX = 14 + FV.dReadout:GetWidth() + 8
    local barW = innerW - (barX - 14)
    local scale = (barW - INSET * 2) / VIS_TOTAL
    FV.barTrack:ClearAllPoints()
    FV.barTrack:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", barX, -(y + 3))
    FV.barTrack:SetWidth(barW)
    FV.barTrack.__active = true
    FV.barTrack.__vtop = y
    FV.barTrack.__vh = 14
    FV.dCull[#FV.dCull + 1] = FV.barTrack
    for i, seg in ipairs(FV.segs) do
        if i <= curTier then
            local x0 = INSET + VIS_CUM[i] * scale
            local w = STANDINGS[i].vis * scale
            if i == curTier then
                w = (pos - VIS_CUM[i]) * scale
            end
            seg:ClearAllPoints()
            seg:SetPoint("TOPLEFT", FV.barTrack, "TOPLEFT", x0, -3)
            seg:SetWidth(max(1, w))
            seg:Show()
        else
            seg:Hide()
        end
    end
    for i = 2, #STANDINGS do
        local tk = FV.ticks[i - 1]
        tk:ClearAllPoints()
        tk:SetPoint("TOPLEFT", FV.barTrack, "TOPLEFT", INSET + VIS_CUM[i] * scale, -3)
        tk:Show()
    end
    FV.labMin:ClearAllPoints()
    FV.labMin:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", barX + INSET, -(y + 23))
    FV.labMin:SetText("-42,000")
    FV.labMid:ClearAllPoints()
    FV.labMid:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", barX + INSET + VisPos(0) * scale - 4, -(y + 23))
    FV.labMid:SetText("0")
    FV.labMax:ClearAllPoints()
    FV.labMax:SetPoint("TOPRIGHT", FV.dChild, "TOPLEFT", barX + barW - INSET, -(y + 23))
    FV.labMax:SetText("+42,999")
    FV.cursor:ClearAllPoints()
    FV.cursor:SetPoint("TOPLEFT", FV.barTrack, "TOPLEFT", INSET + pos * scale - 1, 4)
    FV.cursor:Show()
    y = y + 46

    local nSep = 0
    for _, key in ipairs(REWARD_TIERS) do
        local ids = x.rewards and x.rewards[key]
        if type(ids) == "table" and #ids > 0 then
            nSep = nSep + 1
            local s = FV.rSeps[nSep]
            local ti = TIER_OF_KEY[key]
            s.__active = true
            s.__vtop = y
            s.__vh = 20
            s:ClearAllPoints()
            s:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", 14, -y)
            s.line:SetColorTexture(STANDINGS[ti].color[1], STANDINGS[ti].color[2], STANDINGS[ti].color[3], 0.55)
            s.label:SetText(STANDINGS[ti].label)
            s.label:SetTextColor(STANDINGS[ti].color[1], STANDINGS[ti].color[2], STANDINGS[ti].color[3])
            s:Show()
            FV.dCull[#FV.dCull + 1] = s
            y = y + 24
            local col = 0
            local rowTop = y
            for _, id in ipairs(ids) do
                nCard = nCard + 1
                local cd = FV.rCards[nCard]
                if not cd then
                    cd = CreateFrame("Button", nil, FV.dChild)
                    cd:SetSize(cardW, 44)
                    if HUI and ns.hui.HuiCardFX then
                        ns.hui.HuiCardFX(cd, 12, 2)
                    end
                    cd.iconTex = cd:CreateTexture(nil, "ARTWORK")
                    cd.iconTex:SetSize(32, 32)
                    cd.iconTex:SetPoint("LEFT", cd, "LEFT", 6, 0)
                    cd.iconTex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                    if HUI and ns.hui.RoundIcon then ns.hui.RoundIcon(cd.iconTex) end
                    cd.name = MakeFS(cd, 14, C_TEXT, "LEFT")
                    cd.name:SetPoint("TOPLEFT", cd, "TOPLEFT", 43, -4)
                    cd.name:SetWidth(cardW - 50)
                    cd.name:SetWordWrap(false)
                    cd.meta = MakeFS(cd, 14, C_GREY, "LEFT")
                    cd.meta:SetPoint("TOPLEFT", cd, "TOPLEFT", 43, -23)
                    cd.meta:SetWordWrap(false)
                    cd.__nameW = cardW - 50
                    cd:EnableMouse(true)
                    cd:SetScript("OnEnter", function(self)
                        if self.__huiCard and ns.hui.HuiCardState then
                            ns.hui.HuiCardState(self, "hover")
                            self.__hst = "hover"
                        end
                        if self.__id and DG and DG.ShowItemTip then DG.ShowItemTip(self, { self.__id }) end
                    end)
                    cd:SetScript("OnLeave", function(self)
                        if self.__huiCard and ns.hui.HuiCardState then
                            ns.hui.HuiCardState(self, "norm")
                            self.__hst = "norm"
                        end
                        GameTooltip:Hide()
                    end)
                    cd:SetScript("OnClick", function(self, button)
                        if DG and DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
                    end)
                    cd:SetScript("OnMouseWheel", function(_, delta)
                        WheelTo(FV.dScroll, FV.dChild, delta)
                        FV:CullRight()
                    end)
                    FV.rCards[nCard] = cd
                end
                if col == 0 then rowTop = y end
                cd:ClearAllPoints()
                cd:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", 14 + col * (cardW + GUTTER), -rowTop)
                FV:PaintRewardCard(cd, id)
                if cd.__huiCard and ns.hui.HuiCardState then
                    ns.hui.HuiCardState(cd, "norm")
                    cd.__hst = "norm"
                end
                cd.__active = true
                cd.__vtop = rowTop
                cd.__vh = 44
                cd:Show()
                FV.dCull[#FV.dCull + 1] = cd
                col = col + 1
                if nCard % 4 == 0 then PY() end
                if col >= FV.COLS then
                    col = 0
                    y = y + 44 + GUTTER
                end
            end
            if col > 0 then
                y = y + 44 + GUTTER
            end
            y = y + 4
        end
    end
    for i = nSep + 1, #FV.rSeps do
        FV.rSeps[i].__active = false
        FV.rSeps[i]:Hide()
    end
    for i = nCard + 1, #FV.rCards do
        FV.rCards[i].__active = false
        FV.rCards[i]:Hide()
    end

    FV.dChild:SetHeight(max(10, y + 12))
    if FV.__lastSel ~= x.id then
        FV.__lastSel = x.id
        if FV.dScroll.SetVerticalScroll then FV.dScroll:SetVerticalScroll(0) end
    end
    FV:CullRight()
end

function FV.RequestRender()
    if not FV.built then return end
    if not (ns.PaintJob and ns.IdleJobs) then
        FV:PaintList()
        FV:PaintDetail()
        return
    end
    if ns.PaintJob.Active("Factions") then
        FV.__pend = true
        return
    end
    ns.PaintJob.Run("Factions", function()
        FV:PaintList()
        FV:PaintDetail()
    end, function()
        if FV.__pend then
            FV.__pend = false
            FV.RequestRender()
        end
    end)
end

function FV.Open()
    if not FV.built then return end
    local c = Cfg()
    if not FacBySel(c.sel) then
        local pside = PlayerSide()
        for _, x in ipairs(FD) do
            if PassFilter(x, pside, c) then
                c.sel = x.id
                break
            end
        end
    end
    FV.RequestRender()
end

function FV.Refresh()
    if not FV.built then return end
    FV.RequestRender()
end
