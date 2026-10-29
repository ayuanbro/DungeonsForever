local _, ns = ...

local L = ns.L

if not ns.IsTitan then return end

local U = {}
ns.DungeonUI = U

local FONT_BASE
local CONTENT_W = 960
local PAGE_INSET = 12
local HDR_H = 142
local CARD_H = 484
local CREDIT_H = 22
local CONTENT_H = HDR_H + CARD_H + CREDIT_H

local ROW_SUB = 0
local ROW_CLASS = 30

local FALLBACK_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"

local C_GOLD = { 1, 0.82, 0.0 }
local C_GREEN = { 0.25, 0.85, 0.35 }
local C_RED = { 0.9, 0.35, 0.35 }
local C_GREY = { 0.55, 0.55, 0.55 }
local C_DIM = { 0.63, 0.63, 0.63 }
local C_DARKGREY = { 0.30, 0.30, 0.30 }
local C_WHITE = { 1, 1, 1 }
local C_TEXT = { 0.88, 0.88, 0.88 }
local C_LINK_Q = { 0.53, 0.81, 0.98 }
local C_LINK_NPC = C_GOLD

local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local s = DungeonsForeverDB.dungeon
    if not s then
        s = {}
        DungeonsForeverDB.dungeon = s
    end
    return s
end

local function IsHui()
    return ns.huiTheme == "hui"
end

local function Fnt(size)
    return FONT_BASE, size, ns.hui.FontFlags("OUTLINE")
end

local function Unpack(c)
    return c[1], c[2], c[3]
end

local function MakeFS(parent, size, color, justify)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    fs:SetFont(Fnt(size))
    if color then fs:SetTextColor(Unpack(color)) end
    if justify then fs:SetJustifyH(justify) end
    return fs
end

local function NewButton(parent, text, w, h, size)
    local bt = ns.CreateButton(parent)
    bt:SetSize(w, h)
    if text then bt:SetText(text) end
    bt:GetFontString():SetFont(Fnt(size or 13))
    return bt
end

local function AddBtnIcon(bt, tex, size, pad)
    local fs = bt:GetFontString()
    local t = bt:CreateTexture(nil, "OVERLAY")
    t:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\" .. tex)
    t:SetSize(size, size)
    t:SetPoint("LEFT", bt, "LEFT", pad or 5, 0)
    if fs then
        fs:ClearAllPoints()
        fs:SetPoint("TOPLEFT", bt, "TOPLEFT", (pad or 5) + size + 2, 0)
        fs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)
        fs:SetJustifyH("CENTER")
    end
    bt.__icon = t
    return t
end

local function MakeOutline(bt, r, g, b)
    if IsHui() and ns.hui and ns.hui.BuildRoundBorder then
        local f = CreateFrame("Frame", nil, bt)
        f:SetAllPoints()
        f:SetFrameLevel((bt:GetFrameLevel() or 0) + 5)
        local pieces = ns.hui.BuildRoundBorder(f, 6, { r or 1, g or 1, b or 1, 1 }, f, "OVERLAY", "both", 1) or {}
        for _, tex in ipairs(pieces) do tex:SetShown(true) end
        f:Hide()
        bt.__outlineFrame = f
        bt.__bars = pieces
        return
    end
    bt.__outlineFrame = false
    local bars = {}
    local function mk(w, h, pt1, ox1, oy1, pt2, ox2, oy2)
        local tex = bt:CreateTexture(nil, "OVERLAY")
        tex:SetTexture("Interface\\Buttons\\WHITE8x8")
        tex:SetPoint(pt1, bt, pt1, ox1, oy1)
        tex:SetPoint(pt2, bt, pt2, ox2, oy2)
        if w then tex:SetWidth(w) end
        if h then tex:SetHeight(h) end
        tex:Hide()
        bars[#bars + 1] = tex
    end
    mk(nil, 2, "TOPLEFT", -2, 2, "TOPRIGHT", 2, 2)
    mk(nil, 2, "BOTTOMLEFT", -2, -2, "BOTTOMRIGHT", 2, -2)
    mk(2, nil, "TOPLEFT", -2, 0, "BOTTOMLEFT", -2, 0)
    mk(2, nil, "TOPRIGHT", 2, 0, "BOTTOMRIGHT", 2, 0)
    bt.__bars = bars
    return bars
end

local function HuiCardFX(f, hoverR, baseN)
    if not (IsHui() and ns.hui and ns.hui.BuildRoundedBG) then return false end
    local lv = ns.hui.layer
    local base, hov = lv.L1, lv.L3
    if baseN == 2 then base, hov = lv.L2, lv.L4
    elseif baseN == 3 then base, hov = lv.L3, lv.L5
    elseif baseN == 4 then base, hov = lv.L4, lv.L5 end
    if f.SetBackdropColor then f:SetBackdropColor(0, 0, 0, 0) end
    if f.SetBackdropBorderColor then f:SetBackdropBorderColor(0, 0, 0, 0) end
    local fill, border = ns.hui.BuildRoundedBG(f, 6, base, "both", true, 1)
    f.__huiCard = { fill = fill, border = border }
    if hoverR and ns.hui.BuildCapsule then
        local hp = ns.hui.BuildCapsule(f, 6, hov, 1, 2)
        for _, t in ipairs(hp) do t:Hide() end
        f.__hov = hp
    end
    return true
end

local function HuiCardState(f, st)
    local bp = f.__huiCard
    if not bp then return false end
    local showBase = (st ~= "flat")
    if bp.fill then for _, t in ipairs(bp.fill) do t:SetShown(showBase) end end
    if bp.border then for _, t in ipairs(bp.border) do t:SetShown(showBase) end end
    local hov = (st == "hover")
    if f.__hov then for _, t in ipairs(f.__hov) do t:SetShown(hov) end end
    return true
end
ns.hui.HuiCardFX = HuiCardFX
ns.hui.HuiCardState = HuiCardState

local function SetOutline(bt, on, r, g, b)
    if bt.__outlineFrame then
        bt.__outlineFrame:SetShown(on and true or false)
        return
    end
    for _, tex in ipairs(bt.__bars or {}) do
        if on then
            tex:SetColorTexture(r or 1, g or 1, b or 1, 1)
            tex:Show()
        else
            tex:Hide()
        end
    end
end

local function SetTip(frame, tip)
    frame:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(tip, 1, 1, 1, true)
        GameTooltip:Show()
    end)
    frame:SetScript("OnLeave", function() GameTooltip:Hide() end)
end

local function EnsureContent()
    if U.panel then return U.panel end
    local host = ns.TalentSimFrame
    local panel = CreateFrame("Frame", nil, host, "BackdropTemplate")
    panel:SetSize(CONTENT_W, CONTENT_H)
    panel:SetPoint("TOP", host, "TOP", 0, -(IsHui() and 44 or 76))
    U.panel = panel
    return panel
end
local DG = {}
ns.DungeonModule = DG

function DG.RowPaint(f)
    if IsHui() then
        local l2 = ns.hui.layer.L2
        f:SetBackdropColor(l2[1], l2[2], l2[3], 0.95)
        f:SetBackdropBorderColor(1, 1, 1, 0.10)
    else
        f:SetBackdropColor(0, 0, 0, 0.35)
        f:SetBackdropBorderColor(0.30, 0.30, 0.30, 1)
    end
end

DG.AX0, DG.AX1, DG.LO, DG.HI = 78, 838, 13, 60
DG.BARMAX, DG.MINW, DG.GAPX = 924, 100, 4
DG.LANE_H, DG.BAR_H = 35, 31
DG.CUR_H, DG.TICK_H, DG.BOT_PAD = 16, 20, 10
DG.TICKS = { 13, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60 }
DG.NEW_EDGE = { 0.19, 0.62, 0.47 }
DG.OLD_EDGE = { 0.30, 0.35, 0.50 }
DG.NOART_COLOR = { 0.26, 0.28, 0.32 }

DG.HERO_H = 144
DG.HERO_PLATE_H = 52
DG.HERO_TITLE_Y, DG.HERO_META_Y = DG.HERO_H - 24, DG.HERO_H - 16
DG.HERO_TITLE_MAXW = 226
DG.ENT_CHIP_ICONW = 21
DG.ENT_CHIP_TXTPAD = 8
DG.ENT_CHIP_MINW = 60
DG.ENT_CHIP_MAXW = 150
DG.ENT_CHIP_H = 24
DG.ENT_CHIP_GAP = 6
DG.ENT_CHIP_LEAD = 10
DG.FILTER_Y = DG.HERO_H + 8
DG.SCROLL_Y = DG.FILTER_Y + 32
DG.GUIDE_TOP_Y = DG.HERO_H + 8
DG.HERO_FADE_REVERSED = false
DG.HERO_FADE = {
    { 0.00, 0.10, 0.85, 0.65 },
    { 0.10, 0.25, 0.65, 0.15 },
    { 0.25, 0.40, 0.15, 0.00 },
}
DG.HERO_TEX_OFFICIAL = { 0.02, 0.98, 0.422, 0.668 }
DG.HERO_TEX_CAMELOT = { 0.00, 1.00, 0.372, 0.628 }
DG.WIDE_TEX_OFFICIAL = { 0.115, 0.885, 0.295, 0.805 }
DG.WIDE_TEX_CAMELOT  = { 0.000, 1.000, 0.169, 0.831 }
DG.HERO_FDID = {
    ragefire_chasm = 131862, wailing_caverns = 131882, the_deadmines = 131833,
    shadowfang_keep = 131869, blackfathom_deeps = 131823, the_stockade = 131870,
    gnomeregan = 131841, razorfen_kraul = 131865, razorfen_downs = 131864,
    sm_graveyard = 131852, sm_library = 131852, sm_armory = 131852, sm_cathedral = 131852,
    uldaman = 131876, zul_farrak = 131885, maraudon = 131850, sunken_temple = 131872,
    blackrock_depths = 131824, dire_maul_east = 131835, dire_maul_north = 131835,
    dire_maul_west = 131835, lower_blackrock_spire = 131825, upper_blackrock_spire = 131825,
    scholomance = 131868, stratholme_main = 131871, stratholme_service = 131859,
}
DG.HERO_CAMELOT = {
    city_of_dalaran = 7963775,
    excavation_wetlands = 7963777,
    ruins_of_lordaeron = 7963782,
    hall_of_thanes = 7963781,
}
local MEDIA_HERO = {
    onyxias_lair = "Interface\\AddOns\\DungeonsForever\\Media\\Loadings\\OnyxiasLairHero",
}
local MEDIA_WIDE = {
    onyxias_lair = "Interface\\AddOns\\DungeonsForever\\Media\\Loadings\\OnyxiasLairWide",
}

function DG.ArtOf(d, kind)
    local wide = (kind == "wide")
    local mpath = wide and MEDIA_WIDE[d.id] or MEDIA_HERO[d.id]
    if mpath then return mpath, nil end
    if ns.IsForever then
        local cam = DG.HERO_CAMELOT[d.id]
        if cam then return cam, (wide and DG.WIDE_TEX_CAMELOT or DG.HERO_TEX_CAMELOT) end
    end
    local fd = DG.HERO_FDID[d.id]
    if fd then return fd, (wide and DG.WIDE_TEX_OFFICIAL or DG.HERO_TEX_OFFICIAL) end
    return nil
end

function DG.CardArtFor(d)
    return DG.ArtOf(d, "wide")
end
U.CardArtFor = DG.CardArtFor

function DG.PaintArt(tex, d, kind)
    tex:SetDrawLayer("BACKGROUND", 2)
    local art, coord = DG.ArtOf(d, kind)
    if art then
        tex:SetTexture(art)
        if coord then tex:SetTexCoord(coord[1], coord[2], coord[3], coord[4])
        else tex:SetTexCoord(0, 1, 0, 1) end
        return true
    end
    if IsHui() and ns.hui and ns.hui.layer then
        local c = ns.hui.layer.L2
        tex:SetColorTexture(c[1], c[2], c[3], 1)
    else
        tex:SetColorTexture(DG.NOART_COLOR[1], DG.NOART_COLOR[2], DG.NOART_COLOR[3], 1)
    end
    return false
end

function DG.X(level)
    return DG.AX0 + (level - DG.LO) / (DG.HI - DG.LO) * (DG.AX1 - DG.AX0)
end

function DG.Pack(list)
    local sorted = {}
    for _, d in ipairs(list) do sorted[#sorted + 1] = d end
    table.sort(sorted, function(a, b)
        if a.levelMin ~= b.levelMin then return a.levelMin < b.levelMin end
        return a.levelMax < b.levelMax
    end)
    local right, out = {}, {}
    for _, d in ipairs(sorted) do
        local x1 = DG.X(d.levelMin)
        local x2 = math.max(DG.X(d.levelMax), x1 + DG.MINW)
        if x2 > DG.BARMAX then x2 = DG.BARMAX end
        local lane
        for i = 1, #right do
            if right[i] + DG.GAPX <= x1 then
                lane = i
                break
            end
        end
        if not lane then
            right[#right + 1] = 0
            lane = #right
        end
        right[lane] = x2
        out[#out + 1] = { d = d, lane = lane, x1 = x1, x2 = x2 }
    end
    return out, #right
end

DG.CARD_COLS, DG.CARD_H, DG.CARD_GAP = 5, 58, 8
DG.GUTTER = 8
DG.CHILD_W = CONTENT_W - PAGE_INSET * 2
DG.CARD_W = math.floor((DG.CHILD_W - DG.GUTTER * 2 - (DG.CARD_COLS - 1) * DG.CARD_GAP) / DG.CARD_COLS)
DG.CARD_GLOW_K = { 0.16, 0.12, 0.09, 0.06, 0.04, 0.02 }
DG.CARD_STROKE = false
DG.CARD_MASK = "Interface\\AddOns\\DungeonsForever\\Media\\DFCardMaskRect"
DG.CARD_SHADE = { { 1, 0.22, 0.78, 0.82, 0.92 } }

local function CardRoundTex(tex)
    if not (tex and tex.AddMaskTexture) then return end
    local f = tex:GetParent()
    if not f then return end
    local m = f:CreateMaskTexture(nil, "OVERLAY")
    m:SetAllPoints(tex)
    m:SetTexture(DG.CARD_MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
    tex:AddMaskTexture(m)
    tex.__dfMask = m
end

function DG.WheelScroll(scroll, child, delta)
    if not (scroll and child) then return end
    local maxScroll = math.max(0, child:GetHeight() - scroll:GetHeight())
    scroll:SetVerticalScroll(math.max(0, math.min(maxScroll, scroll:GetVerticalScroll() - delta * 48)))
    if scroll == U.dungeonQuestScroll then DG.CullQuestRows()
    elseif scroll == U.dungeonGuideScroll then DG.CullGuideCards()
    elseif scroll == U.dungeonDetailScroll then DG.CullLootCards() end
end

function DG.ClampScroll(sf, child, val)
    if not (sf and child) then return end
    local cw = tonumber(child.GetHeight and child:GetHeight()) or 0
    local vw = tonumber(sf.GetHeight and sf:GetHeight()) or 0
    local mx = math.max(0, cw - vw)
    local v = tonumber(val) or 0
    if v < 0 then v = 0 end
    if v > mx then v = mx end
    sf:SetVerticalScroll(v)
end

local function CardEdge(card, r, g, b, a)
    a = a or 1
    if card.__rborder then
        for _, t in ipairs(card.__rborder) do
            t:SetVertexColor(r, g, b)
            t:SetAlpha(a)
        end
    elseif not card.__noStroke then
        card:SetBackdropBorderColor(r, g, b, a)
    end
    local gl = card.__rglow
    if gl then
        for i = 1, #gl do
            local e = gl[i]
            local al = a * e[2]
            for _, t in ipairs(e[1]) do
                t:SetVertexColor(r, g, b)
                t:SetAlpha(al)
            end
        end
    end
end

function DG.NewCard(parent)
    local card = CreateFrame("Button", nil, parent, "BackdropTemplate")
    card:SetSize(DG.CARD_W, DG.CARD_H)
    card:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    card:SetBackdropColor(0, 0, 0, 0)
    local rounded = false
    if IsHui() and ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(card, 6, ns.hui.layer.L2, "both", false)
        card:SetBackdropBorderColor(0, 0, 0, 0)
        if ns.hui.BuildRoundBorder then
            if DG.CARD_STROKE == false then
                card.__noStroke = true
            else
                card.__rborder = ns.hui.BuildRoundBorder(card, 6, ns.hui.CARD_BORDER, card, "OVERLAY", "both", 1)
                local gl = {}
                for step, k in ipairs(DG.CARD_GLOW_K) do
                    local pc = ns.hui.BuildRoundBorder(card, 6, ns.hui.CARD_BORDER, card, "OVERLAY", "both", 1, nil, nil, nil, step)
                    if pc then gl[#gl + 1] = { pc, k } end
                end
                card.__rglow = gl
            end
            local sh = {}
            for i = 1, #DG.CARD_SHADE do
                local e = DG.CARD_SHADE[i]
                local pc = ns.hui.BuildRoundBorder(card, 6, { e[3], e[4], e[5], e[2] },
                    card, "OVERLAY", "both", 1, nil, nil, nil, e[1])
                if pc then
                    for _, t in ipairs(pc) do t:SetAlpha(e[2]) end
                    sh[#sh + 1] = pc
                end
            end
            card.__rshade = sh
        end
        rounded = true
    end
    card.art = card:CreateTexture(nil, "BACKGROUND")
    card.art:SetAllPoints()
    if rounded then CardRoundTex(card.art) end
    card.dim = card:CreateTexture(nil, "ARTWORK")
    card.dim:SetAllPoints()
    if rounded then CardRoundTex(card.dim) end
    card.plate = card:CreateTexture(nil, "ARTWORK")
    card.plate:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 1, 1)
    card.plate:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -1, 1)
    card.plate:SetHeight(20)
    if rounded then CardRoundTex(card.plate) end
    if IsHui() then
        card.plate:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\VGradient")
    else
        card.plate:SetColorTexture(0, 0, 0, 0.55)
    end
    card.name = MakeFS(card, 16, C_WHITE, "LEFT")
    card.name:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -5)
    card.name:SetWordWrap(false)
    card.meta = MakeFS(card, 14, C_GREY, "LEFT")
    card.meta:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 8, 3)
    card.meta:SetShadowColor(0, 0, 0, 1)
    card.meta:SetShadowOffset(1, -1)
    card.badge = MakeFS(card, 14, { 0.42, 0.94, 0.62 }, "RIGHT")
    card.badge:SetPoint("TOPRIGHT", card, "TOPRIGHT", -7, -4)
    card.badge:SetText(L["新"])
    card.__hovOn = false
    card:SetScript("OnEnter", function(self)
        self.__hovOn = true
        CardEdge(self, 1, 1, 1, 0.9)
        if not self.__tip then return end
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(self.__tip, 1, 1, 1, true)
        GameTooltip:Show()
    end)
    card:SetScript("OnLeave", function(self)
        self.__hovOn = false
        local e = self.__edge
        if e then CardEdge(self, e[1], e[2], e[3], e[4]) end
        GameTooltip:Hide()
    end)
    card:EnableMouseWheel(true)
    card:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(U.dungeonListScroll, U.dungeonListChild, delta)
    end)
    card:SetScript("OnClick", function(self)
        if self.__d then U:ShowDungeonDetail(self.__d) end
        ns.PlaySound(1)
    end)
    return card
end

function DG.GroupOf(d, lv)
    if d.levelMin > lv then return "up" end
    if d.levelMax and lv <= d.levelMax then return "rec" end
    return "now"
end

function DG.BuildList()
    local data = ns.DungeonData
    local scroll, child, pool = U.dungeonListScroll, U.dungeonListChild, U.dungeonListPool
    if not (data and data.dungeons and scroll and child and pool) then return end

    local lv = UnitLevel("player") or 0
    U.dungeonListLevel = lv

    local cols, gx = DG.CARD_COLS, DG.CARD_GAP
    local cardW = DG.CARD_W
    local nCard, nHdr = 0, 0

    local collapsed = U.dungeonListCollapsed
    if type(collapsed) ~= "table" then collapsed = {} end
    U.dungeonListCollapsed = collapsed

    local groups = {
        { key = "rec", label = L["推荐"],         hint = L["等级正合适，优先前往"], color = C_GOLD },
        { key = "now", label = L["现在可以进入"], hint = L["等级已超出，仍可前往"], color = { 0.74, 0.80, 0.90 } },
        { key = "up",  label = L["还需升级"],     hint = L["等级达到下限后开放"],   color = { 0.74, 0.72, 0.68 } },
    }
    local buckets = { now = {}, rec = {}, up = {} }
    for _, d in ipairs(data.dungeons) do
        local b = buckets[DG.GroupOf(d, lv)]
        b[#b + 1] = d
    end

    local y = -4
    for _, g in ipairs(groups) do
        local list = buckets[g.key]
        table.sort(list, function(a, b)
            if a.levelMin ~= b.levelMin then return a.levelMin < b.levelMin end
            return a.levelMax < b.levelMax
        end)

        nHdr = nHdr + 1
        local ui = pool.hdr[nHdr]
        if not ui then
            ui = {
                txt = MakeFS(child, 16, C_GOLD, "LEFT"),
                hint = MakeFS(child, 14, C_DIM, "RIGHT"),
                div = child:CreateTexture(nil, "ARTWORK"),
            }
            ui.div:SetHeight(1)
            ui.arrD = child:CreateTexture(nil, "ARTWORK")
            ui.arrD:SetSize(14, 14)
            ui.arrD:SetTexture("Interface/AddOns/DungeonsForever/Media/textures/arrow.tga")
            ui.arrD:SetRotation(math.pi)
            ui.arrU = child:CreateTexture(nil, "ARTWORK")
            ui.arrU:SetSize(14, 14)
            ui.arrU:SetTexture("Interface/AddOns/DungeonsForever/Media/textures/arrow.tga")
            ui.hit = CreateFrame("Button", nil, child)
            ui.hit:SetHeight(26)
            ui.hit:RegisterForClicks("LeftButtonUp")
            ui.hit:SetScript("OnClick", function(self)
                local key = self.__key
                if not key then return end
                collapsed[key] = not collapsed[key] or nil
                ns.PlaySound(1)
                DG.BuildList()
            end)
            ui.hit:SetScript("OnEnter", function(self)
                if not self.__key then return end
                GameTooltip:SetOwner(self, "ANCHOR_TOP")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(L["点击折叠 / 展开该组"], 1, 1, 1, true)
                GameTooltip:Show()
            end)
            ui.hit:SetScript("OnLeave", function() GameTooltip:Hide() end)
            ui.hit:EnableMouseWheel(true)
            ui.hit:SetScript("OnMouseWheel", function(self, delta)
                DG.WheelScroll(U.dungeonListScroll, U.dungeonListChild, delta)
                DG.CullListRows()
            end)
            pool.hdr[nHdr] = ui
        end
        local isClosed = collapsed[g.key] == true
        ui.__closed = isClosed
        ui.__active = true
        ui.txt:SetTextColor(Unpack(g.color))
        ui.txt:SetText(g.label .. " · " .. #list .. L[" 个"])
        ui.txt:ClearAllPoints()
        ui.txt:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER + 18, y)
        for _, at in ipairs({ ui.arrD, ui.arrU }) do
            at:SetVertexColor(g.color[1], g.color[2], g.color[3])
            at:ClearAllPoints()
            at:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER, y - 2)
        end
        ui.arrD:SetShown(not isClosed)
        ui.arrU:SetShown(isClosed)
        ui.hint:SetText(g.hint)
        ui.hint:ClearAllPoints()
        ui.hint:SetPoint("TOPRIGHT", child, "TOPRIGHT", -DG.GUTTER, y - 1)
        ui.div:SetColorTexture(g.color[1], g.color[2], g.color[3], 0.30)
        ui.div:ClearAllPoints()
        ui.div:SetPoint("TOPLEFT", ui.txt, "BOTTOMLEFT", -(DG.GUTTER + 14), -6)
        ui.div:SetPoint("RIGHT", child, "RIGHT", -DG.GUTTER, 0)
        ui.div:Show()
        ui.hit:ClearAllPoints()
        ui.hit:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER, y)
        ui.hit:SetPoint("RIGHT", child, "RIGHT", -DG.GUTTER, 0)
        ui.hit.__key = g.key
        ui.hit:Show()
        ui.__vtop = -y
        ui.__vh = 28
        y = y - 28

        if isClosed then
            y = y - 2
        else
            for i, d in ipairs(list) do
            local col = (i - 1) % cols
            local row = math.floor((i - 1) / cols)
            nCard = nCard + 1
            local card = pool.card[nCard]
            if not card then
                card = DG.NewCard(child)
                pool.card[nCard] = card
            end
            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUTTER + col * (cardW + gx), y - row * (DG.CARD_H + gx))
            local ea = (g.key == "up") and 0.30 or 0.70
            card.__edge = { g.color[1], g.color[2], g.color[3], ea }
            CardEdge(card, g.color[1], g.color[2], g.color[3], ea)
            DG.PaintArt(card.art, d, "wide")
            card.dim:SetColorTexture(0, 0, 0,
                (g.key == "rec") and 0.38 or ((g.key == "now") and 0.52 or 0.66))
            card.name:SetTextColor(Unpack((g.key == "up") and C_DIM or C_WHITE))
            card.name:SetText(d.name)
            card.name:ClearAllPoints()
            card.name:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -5)
            card.name:SetPoint("RIGHT", card, "RIGHT", d.isNew and -24 or -8, 0)
            card.meta:SetText(d.levelMin .. "–" .. d.levelMax ..
                (d.bossCount and (" · BOSS " .. d.bossCount) or ""))
            card.badge:SetShown(d.isNew and true or false)
            card.__tip = d.name .. "  " .. d.nameEn .. "\n" ..
                format(L["等级 %d–%d · %s"], d.levelMin, d.levelMax, d.zone or L["位置未知"])
            card.__d = d
            card.__active = true
            card.__vtop = -y + row * (DG.CARD_H + gx)
            card.__vh = DG.CARD_H
            if card.IsMouseOver and card:IsMouseOver() then
                card.__hovOn = true
                CardEdge(card, 1, 1, 1, 0.9)
            else
                card.__hovOn = false
                local e = card.__edge
                CardEdge(card, e[1], e[2], e[3], e[4])
            end
            card:Show()
        end

            local rows = math.ceil(#list / cols)
            y = y - rows * (DG.CARD_H + gx) - 12
        end
    end

    for i = nCard + 1, #pool.card do
        pool.card[i].__active = false
        pool.card[i]:Hide()
    end
    for i = nHdr + 1, #pool.hdr do
        pool.hdr[i].__active = false
        pool.hdr[i].txt:Hide()
        pool.hdr[i].hint:Hide()
        pool.hdr[i].div:Hide()
        pool.hdr[i].arrD:Hide()
        pool.hdr[i].arrU:Hide()
        pool.hdr[i].hit:Hide()
    end
    child:SetHeight(math.max(10, -y + 10))
    DG.CullListRows(true)
end

function DG.CullListRows(force)
    local sc, pool = U.dungeonListScroll, U.dungeonListPool
    if not (sc and pool and sc:IsShown()) then return end
    local gt = sc.GetTop and sc:GetTop()
    if type(gt) ~= "number" then return end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    local last = pool.__cullSig
    if not force and last and last.gt == gt and last.h == viewH and last.v == v then return end
    local vTop, vBot = v - 2, v + viewH + 2
    for _, card in ipairs(pool.card) do
        if not card.__active then
            card:Hide()
        else
            local cy = card.__vtop
            if type(cy) == "number" then
                local ch = card.__vh or DG.CARD_H
                if (cy + ch) > vTop and cy < vBot then card:Show() else card:Hide() end
            end
        end
    end
    for _, ui in ipairs(pool.hdr) do
        local parts = { ui.txt, ui.hint, ui.div, ui.hit }
        if not ui.__active then
            for _, part in ipairs(parts) do
                if part then part:Hide() end
            end
        else
            local cy = ui.__vtop
            local vis = false
            if type(cy) == "number" then
                local ch = ui.__vh or 28
                vis = (cy + ch) > vTop and cy < vBot
            end
            for _, part in ipairs(parts) do
                if part then
                    if vis then part:Show() else part:Hide() end
                end
            end
            if ui.arrD and ui.arrU then
                if vis and not ui.__closed then ui.arrD:Show() else ui.arrD:Hide() end
                if vis and ui.__closed then ui.arrU:Show() else ui.arrU:Hide() end
            end
        end
    end
    pool.__cullSig = { gt = gt, h = viewH, v = v }
end

function DG.ListFadesVisible(vis)
    local fades = U.dungeonListFades
    if not fades then return end
    for _, f in ipairs(fades) do
        if vis then f:Show() else f:Hide() end
    end
end

function DG.DetailTopMask(topY)
    local detail = U.dungeonDetail
    local base = U.dungeonDetailBase
    if not (detail and base) then return end
    if not (IsHui() and ns.hui and ns.hui.layer and ns.hui.layer.L0) then return end
    local L0 = ns.hui.layer.L0
    local mask = CreateFrame("Frame", nil, detail)
    mask:SetFrameLevel(base + 2)
    mask:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, 8)
    mask:SetPoint("TOPRIGHT", detail, "TOPRIGHT", 0, 8)
    mask:SetPoint("BOTTOMLEFT", detail, "TOPLEFT", 0, -topY)
    mask:SetPoint("BOTTOMRIGHT", detail, "TOPRIGHT", 0, -topY)
    local tex = mask:CreateTexture(nil, "OVERLAY")
    tex:SetAllPoints()
    tex:SetTexture("Interface\\Buttons\\WHITE8x8")
    tex:SetVertexColor(L0[1], L0[2], L0[3], L0[4] or 1)
    mask:Hide()
    return mask
end

function DG.RaiseDetailChrome()
    local base = U.dungeonDetailBase
    if not base then return end
    if U.dungeonDetailHero then U.dungeonDetailHero:SetFrameLevel(base + 3) end
    if U.dungeonDetailTipZone then U.dungeonDetailTipZone:SetFrameLevel(base + 3) end
    if U.dungeonBack then U.dungeonBack:SetFrameLevel(base + 3) end
    local lv = base + 4
    for _, bt in pairs(U.dungeonTabBtns or {}) do bt:SetFrameLevel(lv) end
    for _, chip in ipairs(U.dungeonEntChips or {}) do chip:SetFrameLevel(lv) end
    for _, bt in ipairs(U.dungeonFilterBtns or {}) do bt:SetFrameLevel(lv) end
    if U.dungeonQDoneTg then U.dungeonQDoneTg:SetFrameLevel(lv) end
    if U.dungeonLootBossDd then U.dungeonLootBossDd:SetFrameLevel(lv) end
    for _, bt in ipairs(U.dungeonLootViewBtns or {}) do bt:SetFrameLevel(lv) end
    if U.lootFilterBar then U.lootFilterBar:SetFrameLevel(lv) end
end

local function VScrollBounds(sc)
    local gt = sc.GetTop and sc:GetTop()
    if type(gt) ~= "number" then return nil end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return nil end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    return v - 2, v + viewH + 2
end

local function CullVItems(sc, items, defH, clipBot)
    if type(items) ~= "table" then return end
    local vTop, vBot = VScrollBounds(sc)
    if not vTop then return end
    for _, el in ipairs(items) do
        if el.__vgen == DG.__vgen and type(el.__vtop) == "number" then
            local bot = el.__vtop + (el.__vh or defH)
            local inn = bot > vTop and (not clipBot or bot <= vBot)
            if inn then
                el:Show()
            else
                el:Hide()
            end
        end
    end
end

function DG.CullQuestRows()
    local sc, pool = U.dungeonQuestScroll, U.dungeonQuestPool
    if not (sc and pool and sc.IsShown and sc:IsShown()) then return end
    CullVItems(sc, pool.row, DG.Q_ROW_H, true)
    local vTop, vBot = VScrollBounds(sc)
    if not vTop then return end
    for _, hd in ipairs(pool.hdr or {}) do
        if hd.__vgen == DG.__vgen and type(hd.__vtop) == "number" then
            local bot = hd.__vtop + (hd.__vh or DG.Q_HDR_H)
            local vis = bot > vTop and bot <= vBot
            if vis then hd.name:Show() hd.cnt:Show() else hd.name:Hide() hd.cnt:Hide() end
        end
    end
end

function DG.CullGuideCards()
    local sc, pool = U.dungeonGuideScroll, U.dungeonGuidePool
    if not (sc and pool and sc.IsShown and sc:IsShown()) then return end
    CullVItems(sc, pool.card, 100)
end

function DG.CullLootCards()
    local sc, pool = U.dungeonDetailScroll, U.dungeonDetailPool
    if not (sc and pool and sc.IsShown and sc:IsShown()) then return end
    CullVItems(sc, pool.card, DG.LOOT_CARD_MIN_H)
    CullVItems(sc, pool.item, DG.LOOT_CARD_H)
    local vTop, vBot = VScrollBounds(sc)
    if not vTop then return end
    for _, hd in ipairs(pool.hdr or {}) do
        if hd.__vgen == DG.__vgen and type(hd.__vtop) == "number" then
            local vis = (hd.__vtop + (hd.__vh or DG.LOOT_HDR_H)) > vTop and hd.__vtop < vBot
            if vis then hd.name:Show() hd.cnt:Show() else hd.name:Hide() hd.cnt:Hide() end
        end
    end
end

function DG.BuildDungeons()
    if U.dungeonBuilt then return end
    local data = ns.DungeonData
    if not (data and data.dungeons and #data.dungeons > 0) then return end
    local page = U.dungeonPage
    if not page then return end
    U.dungeonBuilt = true

    local CARD_TOP = DG.GUTTER
    local DETAIL_Y = DG.GUTTER
    local LIST_Y = CARD_TOP + DG.GUTTER
    local CARD_BOTTOM = PAGE_INSET
    local listW = CONTENT_W - PAGE_INSET * 2

    local listCard = CreateFrame("Frame", nil, page)
    listCard:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -CARD_TOP)
    listCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -PAGE_INSET, CARD_BOTTOM)
    if IsHui() and ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(listCard, 6, ns.hui.layer.L1, "both", true, 1)
    end
    U.dungeonListCard = listCard

    local baseLv = page:GetFrameLevel()
    listCard:SetFrameLevel(baseLv + 1)

    local listScroll = CreateFrame("ScrollFrame", nil, page)
    if listScroll.SetClipsChildren then listScroll:SetClipsChildren(true) end
    listScroll:SetFrameLevel(baseLv + 2)
    listScroll:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -LIST_Y)
    listScroll:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -PAGE_INSET, CARD_BOTTOM)
    local listChild = CreateFrame("Frame", nil, listScroll)
    listChild:SetSize(DG.CHILD_W, 10)
    listScroll:SetScrollChild(listChild)
    listScroll:EnableMouseWheel(true)
    listScroll:SetScript("OnMouseWheel", function(self, delta)
        local ch = U.dungeonListChild
        if not ch then return end
        local maxScroll = math.max(0, ch:GetHeight() - self:GetHeight())
        self:SetVerticalScroll(math.max(0, math.min(maxScroll, self:GetVerticalScroll() - delta * 48)))
        DG.CullListRows()
    end)
    listScroll:HookScript("OnShow", function() DG.CullListRows(true) end)
    listScroll:HookScript("OnVerticalScroll", function() DG.CullListRows() end)
    U.dungeonListScroll = listScroll

    if IsHui() and ns.hui and ns.hui.layer and ns.hui.layer.L0 then
        local L0 = ns.hui.layer.L0
        local mask = CreateFrame("Frame", nil, page)
        mask:SetFrameLevel(baseLv + 3)
        mask:SetPoint("TOPLEFT", listCard, "BOTTOMLEFT", 0, -1)
        mask:SetPoint("TOPRIGHT", listCard, "BOTTOMRIGHT", 0, -1)
        mask:SetPoint("BOTTOMLEFT", page, "BOTTOMLEFT", 0, 0)
        mask:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", 0, 0)
        local tex = mask:CreateTexture(nil, "OVERLAY")
        tex:SetAllPoints()
        tex:SetTexture("Interface\\Buttons\\WHITE8x8")
        tex:SetVertexColor(L0[1], L0[2], L0[3], L0[4] or 1)
        mask:Hide()
        U.dungeonListFades = { mask }
    end
    U.dungeonListChild = listChild
    U.dungeonListPool = { card = {}, hdr = {} }

    local detail = CreateFrame("Frame", nil, page)
    detail:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -DETAIL_Y)
    detail:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -PAGE_INSET, PAGE_INSET)
    detail:SetFrameLevel(baseLv + 2)
    detail:Hide()
    U.dungeonDetail = detail

    local oscroll = CreateFrame("ScrollFrame", nil, page)
    if oscroll.SetClipsChildren then oscroll:SetClipsChildren(true) end
    oscroll:SetFrameLevel(baseLv + 2)
    oscroll:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -LIST_Y)
    oscroll:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -PAGE_INSET, PAGE_INSET)
    local ochild = CreateFrame("Frame", nil, oscroll)
    ochild:SetSize(listW - 20, 10)
    oscroll:SetScrollChild(ochild)
    oscroll:EnableMouseWheel(true)
    oscroll:SetScript("OnMouseWheel", function(self, delta)
        local maxScroll = math.max(0, ochild:GetHeight() - self:GetHeight())
        self:SetVerticalScroll(math.max(0, math.min(maxScroll, self:GetVerticalScroll() - delta * 48)))
    end)
    U.dungeonOverviewScroll = oscroll
    U.dungeonOverviewChild = ochild
    oscroll:Hide()

    DG.BuildList()
end

DG.Loader = {
    budgetMs = 4,
    preset   = "normal",
    budgetFactor = 0.05,
    capMin = 1,
    capMax = 2,
}
DG.LOADER_PRESETS = { eco = 2, normal = 4, turbo = 8 }
DG.LOADER_LABEL = { eco = L["省电"], normal = L["标准"], turbo = L["激进"] }

DG.LOADER_FACTOR = { eco = 0.6, normal = 0.8, turbo = 1.0 }

function DG.Loader.CurCap(remaining)
    local L0 = DG.Loader
    local dt = L0.__dt
    if type(dt) ~= "number" or dt <= 0 then dt = 16 end
    local cap = dt * (L0.budgetFactor or 0.05)
    local lo = L0.capMin or 1
    local hi = L0.capMax or 2
    if dt > 400 then
        local slow = dt * 0.5
        if slow > 800 then slow = 800 end
        if slow > hi then hi = slow end
    end
    if cap < lo then cap = lo end
    if cap > hi then cap = hi end
    return cap
end

function DG.Loader.SetBudget(k)
    local v = DG.LOADER_PRESETS[k]
    DG.Loader.budgetFactor = DG.LOADER_FACTOR[k] or 0.8
    if type(v) ~= "number" then return false end
    DG.Loader.budgetMs = v
    DG.Loader.preset = k
    DB().loadBudget = (k ~= "normal") and k or nil
    return true
end

function DG.Loader.Init()
    local k = DB().loadBudget
    if DG.LOADER_PRESETS[k] then
        DG.Loader.budgetMs = DG.LOADER_PRESETS[k]
        DG.Loader.budgetFactor = DG.LOADER_FACTOR[k] or 0.8
        DG.Loader.preset = k
    else
        DG.Loader.preset = "normal"
        DG.Loader.budgetMs = DG.LOADER_PRESETS.normal
        DG.Loader.budgetFactor = DG.LOADER_FACTOR.normal
    end
end

function DG.__nowMs()
    local f = debugprofilestop
    if type(f) == "function" then
        local ok, v = pcall(f)
        if ok and type(v) == "number" then return v end
    end
    return nil
end

DG.Gate = { on = false, total = 0, done = 0, minSteps = 2, skipped = false, w = CONTENT_W }

function DG.Gate.Ensure()
    if DG.Gate.bar then return true end
    local panel = U.panel or (U.dungeonPage and U.dungeonPage:GetParent())
    if not panel then return false end
    local host = panel:GetParent() or panel
    local bar = CreateFrame("Frame", nil, host)
    bar:SetFrameLevel(host:GetFrameLevel() + 20)
    bar:SetPoint("TOPLEFT", host, "TOPLEFT", 8, 0)
    bar:SetPoint("TOPRIGHT", host, "TOPRIGHT", -8, 0)
    bar:SetHeight(3)
    do
        local gw = 1000
        local mw = host.GetWidth and host:GetWidth()
        if type(mw) == "number" and mw > 0 then gw = mw end
        DG.Gate.w = gw - 16
    end
    bar.bg = bar:CreateTexture(nil, "BACKGROUND")
    bar.bg:SetAllPoints()
    if IsHui() and ns.hui and ns.hui.layer then
        local L1c = ns.hui.layer.L1
        bar.bg:SetColorTexture(L1c[1], L1c[2], L1c[3], 0.9)
    else
        bar.bg:SetColorTexture(0, 0, 0, 0.45)
    end
    bar.fill = bar:CreateTexture(nil, "ARTWORK")
    bar.fill:SetPoint("TOPLEFT", bar, "TOPLEFT", 0, 0)
    bar.fill:SetPoint("BOTTOMLEFT", bar, "BOTTOMLEFT", 0, 0)
    bar.fill:SetWidth(1)
    bar.fill:SetColorTexture(Unpack(C_GOLD))
    bar:Hide()
    DG.Gate.bar = bar

    local pill = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    pill:SetFrameLevel(panel:GetFrameLevel() + 21)
    pill:SetSize(240, 28)
    pill:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -10, 10)
    pill:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    pill:SetBackdropColor(0, 0, 0, 0.72)
    pill:SetBackdropBorderColor(1, 0.82, 0, 0.45)
    if IsHui() and ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(pill, 8, nil, ns.hui.layer.L2)
    end
    pill.text = MakeFS(pill, 14, C_TEXT, "LEFT")
    pill.text:SetPoint("LEFT", pill, "LEFT", 10, 0)
    do
        local sk = CreateFrame("Button", nil, pill)
        sk:SetSize(52, 20)
        sk:SetPoint("RIGHT", pill, "RIGHT", -5, 0)
        local sl = MakeFS(sk, 14, C_GOLD, "CENTER")
        sl:SetPoint("CENTER", sk, "CENTER", 0, 0)
        sl:SetText(L["跳过"])
        sk:SetScript("OnClick", function() DG.Gate.Skip() end)
        pill.skip = sk
    end
    pill:Hide()
    pill.__idle = 0
    pill:SetScript("OnUpdate", function(self, el)
        if DG.Gate.on then
            self.__idle = 0
            return
        end
        self.__idle = (self.__idle or 0) + (el or 0)
        if self.__idle > 1.5 then
            self.__idle = 0
            DG.Gate.HideUI()
        end
    end)
    DG.Gate.pill = pill
    return true
end

function DG.Gate.Paint()
    local bar, pill = DG.Gate.bar, DG.Gate.pill
    local total = DG.Gate.total
    local done = DG.Gate.done
    if total <= 0 then total = 1 end
    local pct = math.floor(done / total * 100 + 0.5)
    if pct < 0 then pct = 0 end
    local lim = (done < total) and 99 or 100
    if pct > lim then pct = lim end
    if DG.Gate.pctShow and pct < DG.Gate.pctShow then pct = DG.Gate.pctShow end
    DG.Gate.pctShow = pct
    if bar then
        bar.fill:SetWidth(math.max(1, math.floor(DG.Gate.w * pct / 100)))
    end
    if pill and pill.text then
        local eta = ""
        local t0 = DG.Gate.t0
        if t0 and done > 0 and type(debugprofilestop) == "function" then
            local el = debugprofilestop() - t0
            local left = total - done
            if left > 0 and el > 400 then
                local s = math.floor(el / done * left / 1000 + 0.5)
                if s >= 0 and s < 600 then eta = " · " .. s .. "s" end
            end
        end
        pill.text:SetText(L["正在载入…"] .. " " .. pct .. "%" .. eta)
    end
end

function DG.Gate.HideUI()
    if DG.Gate.bar then DG.Gate.bar:Hide() end
    if DG.Gate.pill then DG.Gate.pill:Hide() end
end

function DG.Gate.Begin(n)
    DG.Gate.total = (type(n) == "number" and n > 0) and math.floor(n) or 1
    DG.Gate.done = 0
    DG.Gate.pctShow = nil
    DG.Gate.paintT = 0
    DG.Gate.skipped = false
    DG.Loader.__cap = nil
    DG.Loader.__buildT0 = type(debugprofilestop) == "function" and debugprofilestop() or nil
    DG.Gate.t0 = DG.Loader.__buildT0
    if DG.Gate.total < DG.Gate.minSteps then
        if not DG.Gate.on then DG.Gate.HideUI() end
        return
    end
    DG.Gate.on = true
    if DG.Gate.Ensure() then
        DG.Gate.bar:Show()
        DG.Gate.pill:Show()
    end
    local wd = DG.Gate.__wd
    if not wd then
        wd = CreateFrame("Frame")
        DG.Gate.__wd = wd
    end
    wd.__lastDone = -1
    wd.__stall = 0
    wd.__printT = 0
    wd.__lastGT = nil
    wd.__lastDP = nil
    wd:SetScript("OnUpdate", function(self)
            local gt = type(GetTime) == "function" and GetTime() or nil
            local el = 0
            if gt then
                if self.__lastGT and gt > self.__lastGT then el = (gt - self.__lastGT) * 1000 end
                self.__lastGT = gt
            elseif type(debugprofilestop) == "function" then
                local dp = debugprofilestop()
                if self.__lastDP then
                    local gap = dp - self.__lastDP
                    if gap >= 5 and gap < 5000 then el = gap end
                end
                self.__lastDP = dp
            end
            if el > 0 and el < 5000 then
                DG.Loader.__dt = math.min(math.max((DG.Loader.__dt or 16) * 0.8 + el * 0.2, 1), 5000)
                self.__printT = self.__printT + el
            end
            if not DG.Gate.on then
                self:SetScript("OnUpdate", nil)
                return
            end
            if self.__printT >= 10000 then
                self.__printT = 0
                local L0 = DG.Loader
                local fps = L0.__dt and L0.__dt > 0 and math.floor(1000 / L0.__dt) or -1
                local pct = DG.Gate.total > 0 and math.floor(DG.Gate.done / DG.Gate.total * 100 + 0.5) or 0
                local msg = "|cff46bf72[无限副本手册] 载入中|r "
                    .. DG.Gate.done .. "/" .. DG.Gate.total .. "（" .. pct .. "%）"
                    .. " fps～" .. tostring(fps)
                    .. " 切片～" .. (L0.__sliceMs and math.floor(L0.__sliceMs * 10) / 10 or "?") .. "ms"
                    .. " 预算～" .. math.floor(L0.CurCap(DG.Gate.total - DG.Gate.done)) .. "ms"
                print(msg)
            end
            if DG.Gate.done ~= self.__lastDone then
                self.__lastDone = DG.Gate.done
                self.__stall = 0
            else
                self.__stall = self.__stall + el
                if self.__stall > 6000 then
                    self:SetScript("OnUpdate", nil)
                    DG.Gate.Finish()
                    print("|cffffaa40[无限副本手册] 载入停滞已跳过，可重新打开界面重试|r")
                end
            end
    end)
    DG.Gate.Paint()
end

function DG.Gate.Advance(k)
    DG.Gate.done = DG.Gate.done + (k or 1)
    if DG.Gate.done > DG.Gate.total then DG.Gate.total = DG.Gate.done end
    if DG.Gate.on then
        local now = type(GetTime) == "function" and GetTime() or nil
        if now then
            if now - (DG.Gate.paintT or 0) >= 0.035 then
                DG.Gate.paintT = now
                DG.Gate.Paint()
            end
        else
            DG.Gate.Paint()
        end
    end
end

function DG.Gate.Skip()
    DG.Gate.skipped = true
    DG.Gate.on = false
    DG.Loader.__buildT0 = nil
    DG.Gate.HideUI()
    if DG.DEMO_SAVE then DG.Loader.EndDemo() end
end

function DG.Gate.Finish()
    DG.Gate.done = DG.Gate.total
    if DG.Gate.on then DG.Gate.Paint() end
    DG.Gate.on = false
    DG.Loader.__buildT0 = nil
    DG.Gate.HideUI()
    if DG.DEMO_SAVE then DG.Loader.EndDemo() end
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERDIAG1 = "/dfdiag"
    SlashCmdList["DUNGEONSFOREVERDIAG"] = function()
        local ok, err = pcall(function()
            local L0 = DG.Loader
            local fps = L0.__dt and L0.__dt > 0 and math.floor(1000 / L0.__dt) or -1
            local n = 0
            if GetNumAddOns and IsAddOnLoaded then
                for i = 1, GetNumAddOns() do
                    if IsAddOnLoaded(i) then n = n + 1 end
                end
            end
            local msg = "|cff46bf72[无限副本手册] 载入诊断|r"
                .. " fps～" .. tostring(fps)
                .. " 切片～" .. (L0.__sliceMs and math.floor(L0.__sliceMs * 10) / 10 or "?") .. "ms"
                .. " 预算～" .. math.floor(L0.CurCap(DG.Gate.total - DG.Gate.done)) .. "ms"
                .. " 进度～" .. tostring(DG.Gate.done) .. "/" .. tostring(DG.Gate.total)
                .. " 插件～" .. n
                .. " 堆～" .. math.floor(collectgarbage("count") / 1024) .. "MB"
                print(msg)
            return msg
        end)
        if not ok then
            DEFAULT_CHAT_FRAME:AddMessage("|cffff5040[dfdiag 执行出错]|r " .. tostring(err))
        end
    end
    SLASH_DUNGEONSFOREVERCPU1 = "/dfcpu"
    SlashCmdList["DUNGEONSFOREVERCPU"] = function()
        if not (ResetCPUUsage and UpdateAddOnCPUUsage and GetAddOnCPUUsage and C_Timer) then
            print("|cffff5040[无限副本手册]|r 本客户端不支持 CPU 采样")
            return
        end
        local function NOW()
            if type(debugprofilestop) == "function" then return debugprofilestop() end
            return (GetTime() or 0) * 1000
        end
        local t0 = NOW()
        ResetCPUUsage()
        local PD = ns.ProfModule
        local origRender = PD and PD.Render
        local renders = 0
        if origRender and not ns.__dfcpuBusy then
            ns.__dfcpuBusy = true
            PD.Render = function(...)
                renders = renders + 1
                return origRender(...)
            end
        end
        print("|cff46bf72[无限副本手册]|r CPU 采样 5 秒，请停在当前页面不要操作")
        C_Timer.After(5, function()
            if origRender and ns.__dfcpuBusy then
                PD.Render = origRender
                ns.__dfcpuBusy = nil
            end
            UpdateAddOnCPUUsage()
            local dt = (NOW() - t0) / 1000
            if dt <= 0 then dt = 5 end
            local me = GetAddOnCPUUsage("DungeonsForever") or 0
            local top, topName = 0, "-"
            if C_AddOns and C_AddOns.GetNumAddOns and C_AddOns.GetAddOnInfo then
                for i = 1, C_AddOns.GetNumAddOns() do
                    local nm = C_AddOns.GetAddOnInfo(i)
                    if nm and nm ~= "DungeonsForever" then
                        local v = GetAddOnCPUUsage(nm) or 0
                        if v > top then top, topName = v, nm end
                    end
                end
            end
            print(string.format(
                "|cff46bf72[无限副本手册]|r %.0f 秒内：本插件 %.1fms（%.2f%% 单核）｜专业页重绘 %d 次｜其他最高 %s %.1fms｜fps %.0f",
                dt, me, me / dt / 10, renders, topName, top, GetFramerate and GetFramerate() or -1))
        end)
    end
end
if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERSPEED1 = "/dfspeed"
    SlashCmdList["DUNGEONSFOREVERSPEED"] = function(msg)
        local k = tostring(msg or ""):lower():gsub("%s+", "")
        if DG.LOADER_PRESETS[k] then
            DG.Loader.SetBudget(k)
            print("|cff46bf72[无限副本手册]|r " .. L["载入速度"] .. " = "
                  .. (DG.LOADER_LABEL[k] or k) .. "（" .. math.floor(DG.Loader.CurCap()) .. "ms/帧）")
            return
        end
        print("|cff46bf72[无限副本手册]|r " .. L["载入速度"] .. "："
              .. L["省电"] .. " / " .. L["标准"] .. " / " .. L["激进"]
              .. "（" .. L["当前"] .. " = " .. (DG.LOADER_LABEL[DG.Loader.preset] or "standard") .. "）")
    end
end

DG.__pendRows = {}

DG.GATE_MIN_SHOW = 24
DG.ROW_SYNC_MAX = 20

function DG.RealizePendingRow(e)
    local rows = U.dungeonDetailPool and U.dungeonDetailPool.item
    if not (rows and e) or rows[e.idx] then return end
    local ok, r = pcall(e.make)
    if ok and r then
        rows[e.idx] = r
        if e.paint then pcall(e.paint, r) end
    end
end

function DG.BuildPendRows()
    local list = DG.__pendRows
    local rows = U.dungeonDetailPool and U.dungeonDetailPool.item
    if not (list and rows) then
        DG.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    local t0 = DG.__nowMs()
    local left = DG.LOOT_ROW_FRAME_CAP
    while #list > 0 and left > 0 do
        DG.RealizePendingRow(table.remove(list, 1))
        DG.Gate.Advance(1)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.CurCap() then break end
    end
    if #list > 0 then
        DG.PushStep(DG.BuildPendRows)
    else
        DG.Gate.Finish()
    end
    DG.CullLootCards()
end

function DG.FlushPendingRows()
    local n = #DG.__pendRows
    if n == 0 then
        DG.Gate.Finish()
        return
    end
    if n < DG.ROW_SYNC_MAX then
        for k = 1, n do DG.RealizePendingRow(DG.__pendRows[k]) end
        DG.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    DG.Gate.Begin(n)
    DG.PushStep(DG.BuildPendRows)
    DG.RunSteps()
end

DG.LOOT_ROW_FRAME_CAP = 64

DG.DEMO_SAVE = nil

function DG.Loader.StartDemo()
    if DG.DEMO_SAVE then DG.Loader.EndDemo() end
    DG.DEMO_SAVE = {
        minSteps = DG.Gate.minSteps,
        syncMax  = DG.ROW_SYNC_MAX,
        rowCap   = DG.LOOT_ROW_FRAME_CAP,
        cardCap  = DG.CARD_POOL_CAP,
    }
    DG.Gate.minSteps      = 0
    DG.ROW_SYNC_MAX       = 0
    DG.LOOT_ROW_FRAME_CAP = 2
    DG.CARD_POOL_CAP      = 1
    local it = U.dungeonDetailPool and U.dungeonDetailPool.item
    if it then
        for i = #it, 1, -1 do it[i]:Hide() end
        U.dungeonDetailPool.item = {}
    end
    if (U.lootView or "list") == "card" and U.dungeonDetailPool then
        local cs = U.dungeonDetailPool.card
        if cs then
            for i = #cs, 1, -1 do cs[i]:Hide() end
        end
        U.cardPoolBuilt = nil
        DG.__cardPoolI = 0
    end
    if U.dungeonDetailCur then U:SetDungeonTab("loot") end
end

function DG.Loader.EndDemo()
    local s = DG.DEMO_SAVE
    DG.DEMO_SAVE = nil
    if not s then return end
    DG.Gate.minSteps      = s.minSteps
    DG.ROW_SYNC_MAX       = s.syncMax
    DG.LOOT_ROW_FRAME_CAP = s.rowCap
    DG.CARD_POOL_CAP      = s.cardCap or 24
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERGATE1 = "/dfgate"
    SlashCmdList["DUNGEONSFOREVERGATE"] = function(msg)
        local a = tostring(msg or ""):lower():gsub("%s+", "")
        if a == "demo" then
            if not U.dungeonDetailCur then
                print("|cff46bf72[无限副本手册]|r " .. L["先点开一个副本的掉落页，再运行这个命令。"])
                return
            end
            DG.Loader.StartDemo()
            print("|cff46bf72[无限副本手册]|r " .. L["演示：每帧只建 2 行，进度条会走完一遍。"])
            return
        end
        if a == "off" then
            DG.Loader.EndDemo()
            print("|cff46bf72[无限副本手册]|r " .. L["已还原。"])
            return
        end
        local pool = U.dungeonDetailPool
        local n = (pool and pool.item) and #pool.item or 0
        print("|cff46bf72[无限副本手册]|r " .. L["载入速度"] .. " = "
              .. (DG.LOADER_LABEL[DG.Loader.preset] or DG.Loader.preset) .. "（" .. math.floor(DG.Loader.CurCap()) .. "ms/帧）")
        print("  " .. L["进度条"] .. " " .. DG.Gate.done .. "/" .. DG.Gate.total
              .. " · " .. L["待建行"] .. " " .. #DG.__pendRows
              .. " · " .. L["行池"] .. " " .. n)
        print("  /dfgate demo — " .. L["演示：每帧只建 2 行，进度条会走完一遍。"])
    end
end

DG.pendingSteps = {}
DG.stepping = false
function DG.PushStep(fn)
    DG.pendingSteps[#DG.pendingSteps + 1] = fn
end
function DG.RunSteps()
    if DG.stepping then return end
    DG.stepping = true
    local function finish()
        DG.stepping = false
        DG.Gate.Finish()
    end
    local function drainAll()
        while #DG.pendingSteps > 0 do
            local fn = table.remove(DG.pendingSteps, 1)
            local ok, err = pcall(fn)
            if not ok then
                print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
            end
        end
        finish()
    end
    if not DG.__nowMs() then
        drainAll()
        return
    end
    local f = DG.__pumpFrame
    if not f then
        f = CreateFrame("Frame", nil, UIParent)
        f:SetWidth(1)
        f:SetHeight(1)
        f:SetFrameStrata("TOOLTIP")
        f:SetFrameLevel(1)
        DG.__pumpFrame = f
    end
    f:SetScript("OnUpdate", function(self, el)
        if type(el) == "number" and el > 0 and el < 5 then
            local L0 = DG.Loader
            L0.__dt = math.min(math.max((L0.__dt or 16) * 0.7 + el * 1000 * 0.3, 1), 5000)
        end
        if #DG.pendingSteps == 0 then
            self:SetScript("OnUpdate", nil)
            finish()
            return
        end
        local t0 = DG.__nowMs()
        local cap = DG.Loader.CurCap(DG.Gate.total - DG.Gate.done)
        while #DG.pendingSteps > 0 do
            local fn = table.remove(DG.pendingSteps, 1)
            local s0 = DG.__nowMs()
            local ok, err = pcall(fn)
            local s1 = DG.__nowMs()
            if s0 and s1 then
                local sm = s1 - s0
                DG.Loader.__sliceMs = (DG.Loader.__sliceMs or sm) * 0.7 + sm * 0.3
            end
            if not ok then
                print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
            end
            if s1 and (s1 - t0) >= cap then break end
        end
        if #DG.pendingSteps == 0 then
            self:SetScript("OnUpdate", nil)
            finish()
        end
    end)
    f:Show()
end

ns.PhasedStart = function(total, body, onFail)
    if type(collectgarbage) == "function" then
        pcall(collectgarbage, "setpause", 150)
        pcall(collectgarbage, "setstepmul", 300)
    end
    local co = type(body) == "thread" and body or coroutine.create(body)
    local __sliceN = 0
    local function gcRestore()
        if type(collectgarbage) == "function" then
            pcall(collectgarbage, "restart")
            pcall(collectgarbage, "setpause", 200)
            pcall(collectgarbage, "setstepmul", 200)
        end
    end
    local function step()
        local done = false
        local ok, err = pcall(function()
            if coroutine.status(co) == "dead" then
                done = true
                return
            end
            local t0 = DG.__nowMs()
            local cap = DG.Loader.CurCap(DG.Gate.total - DG.Gate.done)
            while true do
                local s0 = DG.__nowMs()
                __sliceN = __sliceN + 1
                local rok, rerr = coroutine.resume(co)
                if not rok then
                    local sok, sst = pcall(coroutine.status, co)
                    error(tostring(rerr) .. " @slice" .. __sliceN .. "|costat=" .. tostring(sst) .. "|body=" .. type(body), 0)
                end
                local s1 = DG.__nowMs()
                if s0 and s1 then
                    local sm = s1 - s0
                    DG.Loader.__sliceMs = (DG.Loader.__sliceMs or sm) * 0.7 + sm * 0.3
                end
                DG.Gate.Advance(1)
                if coroutine.status(co) == "dead" then
                    done = true
                    return
                end
                local t1 = t0 and DG.__nowMs()
                if t1 and (t1 - t0) >= cap then return end
            end
        end)
        if not ok then
            gcRestore()
            _G.DF_LAST_BUILD_ERR = tostring(err)
                .. " || " .. (type(debugstack) == "function" and debugstack(co, 2, 1, 12) or "")
            DG.Gate.Finish()
            if type(onFail) == "function" then pcall(onFail) end
            print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
            return
        end
        if done then
            gcRestore()
            if ns.IdleJobs then ns.IdleJobs.StepGC(60, 512) end
            return
        end
        DG.PushStep(step)
    end
    DG.Gate.Begin(total)
    DG.PushStep(step)
    DG.RunSteps()
end

function DG.NewBossCard(dchild, arrow)
            local c = CreateFrame("Frame", nil, dchild)
            c:EnableMouse(false)
            if ns.hui and ns.hui.BuildRoundedBG then
                ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L1, "both", true, 1)
            end
            c.hit = CreateFrame("Button", nil, c)
            c.hit:RegisterForClicks("LeftButtonUp")
            c.hit:SetHeight(DG.LOOT_CARD_MIN_H)
            c.arrD = c:CreateTexture(nil, "ARTWORK")
            c.arrD:SetSize(DG.LOOT_CARD_ARROW, DG.LOOT_CARD_ARROW)
            c.arrD:SetTexture(arrow)
            c.arrD:SetRotation(math.pi)
            c.arrU = c:CreateTexture(nil, "ARTWORK")
            c.arrU:SetSize(DG.LOOT_CARD_ARROW, DG.LOOT_CARD_ARROW)
            c.arrU:SetTexture(arrow)
            for _, at in ipairs({ c.arrD, c.arrU }) do
                at:SetVertexColor(Unpack(C_GOLD))
                at:SetPoint("TOPRIGHT", c, "TOPRIGHT", -DG.LOOT_CARD_PAD,
                            -(DG.LOOT_CARD_HDR_H - DG.LOOT_CARD_ARROW) / 2)
            end
            c.name = MakeFS(c, DG.LOOT_FS_HDR, C_TEXT, "LEFT")
            c.name:SetWordWrap(false)
            c.name:SetPoint("LEFT", c, "TOPLEFT", DG.LOOT_CARD_PAD, -DG.LOOT_CARD_HDR_H / 2)
            c.cnt = MakeFS(c, DG.LOOT_FS_META, C_GREY, "RIGHT")
            c.cnt:SetPoint("RIGHT", c.arrD, "LEFT", -6, 0)
            c.hit:SetScript("OnClick", function(self)
                local key = self.__key
                if not key then return end
                DG.LootFoldToggle(key)
            end)
            c.hit:SetScript("OnEnter", function(self)
                local g = self.__g or {}
                local n = g.gi and #(g.items or {}) or 0
                GameTooltip:SetOwner(self, "ANCHOR_TOP")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(g.srcName or "", 1, 1, 1, true)
                if g.enName and g.enName ~= "" then
                    GameTooltip:AddLine(g.enName, 0.55, 0.55, 0.55, true)
                end
                GameTooltip:AddLine(format(L["%d 件"], n), 1, 0.82, 0, true)
                GameTooltip:AddLine(L["点击折叠 / 展开该组"], 0.55, 0.55, 0.55, true)
                GameTooltip:Show()
                local hi = self.__hi
                if type(hi) == "table" then
                    for _, t in ipairs(hi) do t:Show() end
                else
                    hi:Show()
                end
            end)
            c.hit:SetScript("OnLeave", function(self)
                GameTooltip:Hide()
                local hi = self.__hi
                if type(hi) == "table" then
                    for _, t in ipairs(hi) do t:Hide() end
                else
                    hi:Hide()
                end
            end)
            c.hit:EnableMouseWheel(true)
            c.hit:SetScript("OnMouseWheel", function(self, delta)
                DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)
            end)
            if IsHui() and ns.hui and ns.hui.BuildCapsule then
                local hp = ns.hui.BuildCapsule(c.hit, 8, { 1, 1, 1, 0.08 }, 0, 2)
                for _, t in ipairs(hp) do t:Hide() end
                c.hit.__hi = hp
            else
                local htx = c.hit:CreateTexture(nil, "OVERLAY")
                htx:SetAllPoints()
                htx:SetColorTexture(1, 1, 1, 0.06)
                htx:Hide()
                c.hit.__hi = htx
            end
            c:Hide()
    return c
end

DG.CARD_POOL_CAP = 24
function DG.CardPoolReady()
    return (DG.__cardPoolI or 0) >= (DG.LOOT_CARD_MAX or 0)
end

function DG.BuildCardPool()
    local dchild = U.dungeonDetailChild
    local pool = U.dungeonDetailPool
    if not (dchild and pool and pool.card) then return end
    local n = DG.LOOT_CARD_MAX or 0
    local i = DG.__cardPoolI or 0
    if not DG.__cardPoolBegun then
        DG.__cardPoolBegun = true
        DG.Gate.Begin(n)
    end
    local t0 = DG.__nowMs()
    local left = DG.CARD_POOL_CAP
    local arrow = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\arrow.tga"
    while i < n and left > 0 do
        i = i + 1
        pool.card[i] = DG.NewBossCard(dchild, arrow)
        DG.Gate.Advance(1)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.CurCap() then break end
    end
    DG.__cardPoolI = i
    if i < n then
        DG.PushStep(DG.BuildCardPool)
    elseif (U.lootView or "list") == "card" and U.dungeonDetailCur then
        DG.PushStep(function() U:RenderDungeonLoot() end)
    end
end

function DG.EnsureCardPool()
    if U.cardPoolBuilt then return end
    local dchild, pool = U.dungeonDetailChild, U.dungeonDetailPool
    if not (dchild and pool) then return end
    U.cardPoolBuilt = true
    pool.card = {}
    local maxG = 0
    for _, srcs in pairs(ns.DungeonLoot or {}) do
        local n = #srcs
        if n > maxG then maxG = n end
    end
    DG.LOOT_CARD_MAX = math.max(maxG, 6)
    DG.__cardPoolI = 0
    DG.__cardPoolBegun = nil
    DG.PushStep(DG.BuildCardPool)
    DG.RunSteps()
end

function DG.EnsureQuestLane()
    if U.questLaneBuilt then return end
    local detail = U.dungeonDetail
    if not detail then return end
    U.questLaneBuilt = true
    local ilc = CreateFrame("Frame", nil, detail, "BackdropTemplate")
    ilc:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    if not HuiCardFX(ilc, nil, 1) then
        ilc:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        ilc:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
    end
    ilc:SetFrameLevel(U.dungeonDetailBase + 1)
    ilc:SetPoint("TOPLEFT", detail, "TOPLEFT", 8, -(DG.FILTER_Y + DG.Q_HEAD_H))
    ilc:SetPoint("BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W - 8, 8)
    ilc:Hide()
    U.dungeonQListCard = ilc
    local qscroll = CreateFrame("ScrollFrame", nil, detail)
    qscroll:SetFrameLevel(U.dungeonDetailBase + 1)
    qscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -(DG.FILTER_Y + DG.Q_HEAD_H))
    qscroll:SetPoint("BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W, 8)
    local qchild = CreateFrame("Frame", nil, qscroll)
    qchild:SetSize(DG.Q_LIST_W, 10)
    qscroll:SetScrollChild(qchild)
    qscroll:EnableMouseWheel(true)
    qscroll:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(self, U.dungeonQuestChild, delta)
    end)
    qscroll:Hide()
    qscroll:HookScript("OnShow", function() DG.CullQuestRows() end)
    U.dungeonQuestScroll = qscroll
    U.dungeonQuestChild = qchild
    U.dungeonQuestPool = { hdr = {}, row = {} }
    U.dungeonQMask = DG.DetailTopMask(DG.FILTER_Y)
    if IsHui() and ns.hui and ns.hui.layer and ns.hui.layer.L1 and ns.hui.GlassZoneColor then
        local tm = CreateFrame("Frame", nil, detail)
        tm:SetFrameLevel(U.dungeonDetailBase + 2)
        tm:SetPoint("TOPLEFT", detail, "TOPLEFT", 1, -(DG.FILTER_Y + 1))
        tm:SetPoint("BOTTOMRIGHT", detail, "TOPLEFT", DG.Q_LIST_W - 1, -(DG.FILTER_Y + DG.Q_HEAD_H))
        local ttex = tm:CreateTexture(nil, "OVERLAY")
        ttex:SetAllPoints()
        ttex:SetTexture("Interface\\Buttons\\WHITE8x8")
        local gr, gg, gb = ns.hui.GlassZoneColor(ns.hui.layer.L1, "top")
        ttex:SetVertexColor(gr, gg, gb, 1)
        tm:Hide()
        U.dungeonQTrackMask = tm
    end
    DG.RaiseDetailChrome()
    U.dungeonQuestSum = MakeFS(qchild, 14, C_GOLD, "LEFT")
    U.dungeonQuestNote = MakeFS(qchild, 14, C_GREY, "LEFT")

    local qdet = CreateFrame("ScrollFrame", nil, detail)
    qdet:SetFrameLevel(U.dungeonDetailBase + 1)
    qdet:SetPoint("TOPLEFT", detail, "TOPLEFT",
                  DG.Q_LIST_W + DG.Q_DET_GAP + DG.Q_PAD, -DG.FILTER_Y)
    qdet:SetPoint("BOTTOMRIGHT", detail, "BOTTOMRIGHT", -(DG.Q_PAD), 0)
    local qdchild = CreateFrame("Frame", nil, qdet)
    qdchild:SetSize(DG.Q_DET_W, 10)
    qdet:SetScrollChild(qdchild)
    qdet:EnableMouseWheel(true)
    qdet:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(self, U.dungeonQDetChild, delta)
    end)
    qdet:Hide()
    qdet:HookScript("OnShow", function() DG.CullQuestRows() end)
    U.dungeonQDet = qdet
    U.dungeonQDetChild = qdchild

    local qdTrack = CreateFrame("Frame", nil, detail)
    qdTrack:SetFrameLevel(U.dungeonDetailBase + 11)
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(qdTrack, 3, ns.hui.layer.L2)
    else
        qdTrack:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        qdTrack:SetBackdropColor(0, 0, 0, 0.25)
        qdTrack:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    qdTrack:SetWidth(7)
    qdTrack:SetPoint("TOPRIGHT", qdet, "TOPRIGHT", 7, -2)
    qdTrack:SetPoint("BOTTOMRIGHT", qdet, "BOTTOMRIGHT", 7, 2)
    qdTrack:Hide()
    U.dungeonQDetBar = qdTrack
    local qdThumb = CreateFrame("Button", nil, qdTrack)
    qdThumb:SetWidth(5)
    qdThumb:EnableMouse(true)
    local qdTP, qdTX = nil, nil
    if ns.hui and ns.hui.BuildCapsule then
        qdTP = ns.hui.BuildCapsule(qdThumb, 2, ns.hui.layer.L4)
    else
        qdTX = qdThumb:CreateTexture(nil, "OVERLAY")
        qdTX:SetAllPoints()
        qdTX:SetColorTexture(1, 1, 1, 0.30)
    end
    qdThumb:SetScript("OnEnter", function()
        if qdTP then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(qdTP) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif qdTX then
            qdTX:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    qdThumb:SetScript("OnLeave", function()
        if qdTP then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(qdTP) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif qdTX then
            qdTX:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    qdThumb:SetPoint("TOP", qdTrack, "TOP", 0, -1)
    qdThumb:Hide()

    function DG.UpdateQDetBar()
        if not qdet:IsShown() then qdTrack:Hide() qdThumb:Hide() return end
        local viewH = qdet:GetHeight()
        local contentH = qdchild:GetHeight()
        if type(viewH) ~= "number" or type(contentH) ~= "number"
            or contentH <= viewH + 2 then
            qdTrack:Hide()
            qdThumb:Hide()
            return
        end
        qdTrack:Show()
        qdThumb:Show()
        local vpos = qdet:GetVerticalScroll()
        if type(vpos) ~= "number" then vpos = 0 end
        local trackH = qdTrack:GetHeight() - 2
        local maxScroll = contentH - viewH
        local frac = math.min(1, math.max(0, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        qdThumb:SetHeight(th)
        qdThumb:ClearAllPoints()
        qdThumb:SetPoint("TOP", qdTrack, "TOP", 0, -1 - frac * (trackH - th))
    end
    qdet:HookScript("OnVerticalScroll", function() DG.UpdateQDetBar() end)
    qdThumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = qdet:GetVerticalScroll()
        if type(sc0) ~= "number" then sc0 = 0 end
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = qdTrack:GetHeight() - 2
            local span = trackH - qdThumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = qdchild:GetHeight() - qdet:GetHeight()
            qdet:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
        end)
    end)
    qdThumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    qdThumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    U.dungeonQDetPool = {
        lab = {}, kv = {}, txt = {}, node = {}, chip = {}, npc = {},
        fLab = {}, fTxt = {}, fLink = {}, fNum = {},
    }
    U.dungeonQDetName = MakeFS(qdchild, 16, C_GOLD, "LEFT")
    U.dungeonQDetName:SetWordWrap(false)
    U.dungeonQDetName:SetWidth(DG.Q_DET_W - 8)
    U.dungeonQDetSt = MakeFS(qdchild, 14, C_GREY, "LEFT")

    local function questPlate()
        local p = CreateFrame("Frame", nil, detail, "BackdropTemplate")
        p:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        if not HuiCardFX(p) then
            p:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
            p:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
        end
        p:Hide()
        return p
    end
    local plateL = questPlate()
    plateL:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.FILTER_Y)
    plateL:SetPoint("BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W, 0)
    plateL:SetFrameLevel(qscroll:GetFrameLevel() - 1)
    local plateR = questPlate()
    plateR:SetPoint("TOPLEFT", detail, "TOPLEFT",
                    DG.Q_LIST_W + DG.Q_DET_GAP, -DG.FILTER_Y)
    plateR:SetPoint("BOTTOMRIGHT", detail, "BOTTOMRIGHT", 0, 0)
    plateR:SetFrameLevel(qdet:GetFrameLevel() - 1)
    U.dungeonQPlateL = plateL
    U.dungeonQPlateR = plateR

    local ovTop = DG.FILTER_Y + DG.Q_HEAD_H
    local card = CreateFrame("Frame", nil, detail, "BackdropTemplate")
    card:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    if not HuiCardFX(card, nil, 1) then
        card:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        card:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
    end
    card:SetPoint("TOPLEFT", detail, "TOPLEFT", 8, -ovTop)
    card:SetPoint("BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W - 8, 8)
    card:SetFrameLevel(U.dungeonDetailBase + 1)
    card:EnableMouse(true)
    card:EnableMouseWheel(true)
    card:SetScript("OnMouseWheel", function(_, delta)
        if U.dungeonQOVWheel then U.dungeonQOVWheel(delta) end
    end)
    card:SetScript("OnMouseDown", function(_, b)
        if b == "LeftButton" and U.dungeonQOVDragStart then U.dungeonQOVDragStart(card) end
    end)
    card:SetScript("OnMouseUp", function()
        if U.dungeonQOVDragStop then U.dungeonQOVDragStop() end
    end)
    card:Hide()
    U.dungeonQOVCard = card

    local sf = CreateFrame("ScrollFrame", nil, detail)
    sf:SetFrameLevel(U.dungeonDetailBase + 2)
    sf:SetPoint("TOPLEFT", detail, "TOPLEFT", 12, -(ovTop + 4))
    sf:SetPoint("BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W - 22, 12)
    sf:EnableMouse(false)
    sf:EnableMouseWheel(false)
    sf:Hide()
    U.dungeonQOverviewF = sf

    local zoomf = CreateFrame("Frame", nil, sf)
    zoomf:SetSize(DG.Q_LIST_W - 24, 10)
    sf:SetScrollChild(zoomf)
    local ovc = CreateFrame("Button", nil, zoomf)
    ovc:SetPoint("TOPLEFT", zoomf, "TOPLEFT", 0, 0)
    ovc:SetSize(DG.Q_LIST_W - 24, 10)
    U.dungeonQOVCanvas = ovc
    U.dungeonQOVPool = { node = {}, line = {}, lab = {}, arc = {}, fil = {} }
    U.dungeonQOVOff = 0
    U.dungeonQOVZoom = 1.25

    local function sync_ov_zoom()
        local z = U.dungeonQOVZoom or 1
        zoomf:SetSize(ovc:GetWidth() * z, ovc:GetHeight() * z)
        ovc:SetScale(z)
    end
    U.dungeonQOVSync = sync_ov_zoom
    local function clampScroll()
        sync_ov_zoom()
        local vw, vh = sf:GetWidth(), sf:GetHeight()
        local mx = math.max(0, zoomf:GetWidth() - vw)
        local my = math.max(0, zoomf:GetHeight() - vh)
        sf:SetHorizontalScroll(math.max(0, math.min(mx, sf:GetHorizontalScroll())))
        sf:SetVerticalScroll(math.max(0, math.min(my, sf:GetVerticalScroll())))
        if U.dungeonQOVBar then U.dungeonQOVBar() end
    end
    U.dungeonQOVClamp = clampScroll
    local function applyZoom(z, cx, cy)
        z = math.max(0.5, math.min(2, z))
        local old = U.dungeonQOVZoom or 1
        if z == old then return end
        local vs, hs = sf:GetVerticalScroll(), sf:GetHorizontalScroll()
        local vw, vh = sf:GetWidth(), sf:GetHeight()
        if not cx then cx, cy = vw / 2, vh / 2 end
        local wx, wy = (hs + cx) / old, (vs + cy) / old
        U.dungeonQOVZoom = z
        sync_ov_zoom()
        sf:UpdateScrollChildRect()
        sf:SetHorizontalScroll(wx * z - cx)
        sf:SetVerticalScroll(wy * z - cy)
        clampScroll()
    end
    U.dungeonQOVZoomBy = function(delta)
        applyZoom((U.dungeonQOVZoom or 1) * (delta > 0 and 1.15 or 1 / 1.15))
    end

    local proxy = CreateFrame("Frame", nil, detail)
    proxy:SetSize(1, 1)
    proxy:EnableMouse(false)
    proxy:SetMovable(true)
    proxy:SetPoint("BOTTOMLEFT", detail, "BOTTOMLEFT", 0, 0)
    proxy:SetFrameLevel(U.dungeonDetailBase)
    U.dungeonQOVProxy = proxy

    local function ovWheel(delta)
        local step = delta * 40
        if IsShiftKeyDown() then
            sf:SetHorizontalScroll(sf:GetHorizontalScroll() - step)
        else
            sf:SetVerticalScroll(sf:GetVerticalScroll() + step)
        end
        clampScroll()
    end
    U.dungeonQOVWheel = ovWheel
    local function ovDragStop()
        U.__ovDrag = nil
        U.__ovDragDist = nil
        ovc:SetScript("OnUpdate", nil)
        if card and card.SetScript then card:SetScript("OnUpdate", nil) end
        pcall(proxy.StopMovingOrSizing, proxy)
    end
    U.dungeonQOVDragStop = ovDragStop
    local function ovDragStart(host)
        proxy:ClearAllPoints()
        proxy:SetPoint("BOTTOMLEFT", detail, "BOTTOMLEFT", 0, 0)
        pcall(proxy.StartMoving, proxy)
        local px, py = GetCursorPosition()
        U.__ovDrag = {
            l = proxy:GetLeft(), b = proxy:GetBottom(), px = px, py = py,
            hs = sf:GetHorizontalScroll(), vs = sf:GetVerticalScroll(), d = 0,
        }
        local function tick(s)
            local st = U.__ovDrag
            if not st or not sf:IsShown() then
                ovDragStop()
                return
            end
            local okDown, down = pcall(IsMouseButtonDown, "LeftButton")
            if okDown and down == false then
                ovDragStop()
                return
            end
            local dx, dy
            local cx, cy = GetCursorPosition()
            if cx ~= st.px or cy ~= st.py then
                local sc = sf:GetEffectiveScale() or 1
                dx, dy = (cx - st.px) / sc, (cy - st.py) / sc
                st.px, st.py = cx, cy
                st.l, st.b = proxy:GetLeft(), proxy:GetBottom()
            else
                local l, bt = proxy:GetLeft(), proxy:GetBottom()
                if not l or not st.l then return end
                dx, dy = l - st.l, bt - st.b
                st.l, st.b = l, bt
            end
            if dx == 0 and dy == 0 then return end
            st.d = st.d + math.abs(dx) + math.abs(dy)
            U.__ovDragDist = st.d
            local mx = math.max(0, zoomf:GetWidth() - sf:GetWidth())
            local my = math.max(0, zoomf:GetHeight() - sf:GetHeight())
            st.hs = math.max(0, math.min(mx, st.hs - dx))
            st.vs = math.max(0, math.min(my, st.vs + dy))
            sf:SetHorizontalScroll(st.hs)
            sf:SetVerticalScroll(st.vs)
            if U.dungeonQOVBar then U.dungeonQOVBar() end
        end
        if host then host:SetScript("OnUpdate", tick) else ovc:SetScript("OnUpdate", tick) end
    end
    U.dungeonQOVDragStart = ovDragStart
    ovc:EnableMouse(true)
    ovc:EnableMouseWheel(true)
    ovc:SetScript("OnMouseWheel", function(_, delta)
        ovWheel(delta)
    end)
    ovc:SetScript("OnMouseDown", function(_, b)
        if b == "LeftButton" then ovDragStart(ovc) end
    end)
    ovc:SetScript("OnMouseUp", function()
        ovDragStop()
    end)

    local zpill = CreateFrame("Frame", nil, card, "BackdropTemplate")
    zpill:SetSize(96, 24)
    zpill:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -6, 6)
    zpill:SetFrameLevel(sf:GetFrameLevel() + 10)
    zpill:EnableMouse(true)
    zpill:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
    if IsHui() and ns.hui and ns.hui.layer and ns.hui.layer.L2 then
        local c2 = ns.hui.layer.L2
        zpill:SetBackdropColor(c2[1], c2[2], c2[3], 1)
    else
        zpill:SetBackdropColor(0x16 / 255, 0x1a / 255, 0x22 / 255, 1)
    end
    if IsHui() and ns.hui and ns.hui.BuildRoundBorder then
        local zbf = CreateFrame("Frame", nil, zpill)
        zbf:SetAllPoints()
        ns.hui.BuildRoundBorder(zbf, 12, { 0x55 / 255, 0x58 / 255, 0x5e / 255 })
    end
    U.dungeonQOVPill = zpill
    local zlab = MakeFS(zpill, 14, { 0.91, 0.93, 0.94 }, "CENTER")
    zlab:SetPoint("CENTER", zpill, "CENTER", 0, 0)
    zlab:SetText("125%")
    local function refreshZoomLabel()
        zlab:SetText(math.floor((U.dungeonQOVZoom or 1) * 100 + 0.5) .. "%")
    end
    local function zoomStep(dir)
        U.dungeonQOVZoomBy(dir)
        refreshZoomLabel()
    end
    local Z_GLYPH = { 0.67, 0.70, 0.73 }
    for i = 1, 2 do
        local bt = CreateFrame("Button", nil, zpill)
        bt:SetSize(24, 24)
        if i == 1 then
            bt:SetPoint("LEFT", zpill, "LEFT", 2, 0)
        else
            bt:SetPoint("RIGHT", zpill, "RIGHT", -2, 0)
        end
        bt:SetFrameLevel(zpill:GetFrameLevel() + 3)
        bt:EnableMouse(true)
        if IsHui() and ns.hui and ns.hui.BuildCapsule then
            bt.__hov = ns.hui.BuildCapsule(bt, 8, ns.hui.layer.L4, 1, 2)
            for _, hv in ipairs(bt.__hov) do hv:Hide() end
        end
        local t = MakeFS(bt, 28, { Z_GLYPH[1], Z_GLYPH[2], Z_GLYPH[3] })
        t:ClearAllPoints()
        t:SetPoint("CENTER", 0, 1)
        t:SetText(i == 1 and "-" or "+")
        bt:SetScript("OnEnter", function(self)
            if self.__hov then
                for _, hv in ipairs(self.__hov) do hv:Show() end
            end
            if ns.hui and ns.hui.ACCENT then
                t:SetTextColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3])
            else
                t:SetTextColor(1, 1, 1)
            end
        end)
        bt:SetScript("OnLeave", function(self)
            if self.__hov then
                for _, hv in ipairs(self.__hov) do hv:Hide() end
            end
            t:SetTextColor(Z_GLYPH[1], Z_GLYPH[2], Z_GLYPH[3])
        end)
        bt:SetScript("OnClick", function()
            zoomStep(i == 1 and -1 or 1)
        end)
    end
    refreshZoomLabel()
    U.dungeonQOVLabel = refreshZoomLabel

    local legend = {
        { "Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc", DG.Q_OV_DONE, "Interface\\AddOns\\DungeonsForever\\Media\\CheckMark", { 0.043, 0.239, 0.102 }, DG.Q_OV_DONE, L["任务完成"] },
        { "Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc", DG.Q_OV_ACT, "Interface\\AddOns\\DungeonsForever\\Media\\QMarkAsk", { 0.227, 0.165, 0 }, DG.Q_OV_ACT, L["已接取"] },
        { "Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc", DG.Q_OV_TODO, "Interface\\AddOns\\DungeonsForever\\Media\\QMarkExcl", { 0.102, 0.102, 0.102 }, DG.Q_OV_TODO, L["未接取"] },
    }
    local legf = CreateFrame("Frame", nil, card)
    legf:SetFrameLevel(sf:GetFrameLevel() + 10)
    legf:SetHeight(22)
    local legParts, legW = {}, 0
    for _, it in ipairs(legend) do
        local fs = MakeFS(legf, 11, it[5], "LEFT")
        fs:SetText(it[6])
        legParts[#legParts + 1] = { it, fs, fs:GetStringWidth() }
        legW = legW + DG.Q_BADGE_H + 4 + fs:GetStringWidth()
    end
    legW = legW + 8 * (#legend - 1)
    legf:SetWidth(legW)
    legf:SetPoint("RIGHT", zpill, "LEFT", -10, 0)
    local legX = 0
    for _, part in ipairs(legParts) do
        local it, fs, tw = part[1], part[2], part[3]
        local d = legf:CreateTexture(nil, "ARTWORK")
        d:SetTexture(it[1])
        d:SetSize(DG.Q_BADGE_H, DG.Q_BADGE_H)
        d:SetPoint("LEFT", legf, "LEFT", legX, 0)
        d:SetVertexColor(it[2][1], it[2][2], it[2][3], 1)
        local s = legf:CreateTexture(nil, "OVERLAY")
        s:SetTexture(it[3])
        s:SetAllPoints(d)
        s:SetVertexColor(it[4][1], it[4][2], it[4][3], 1)
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", d, "RIGHT", 4, 0)
        legX = legX + DG.Q_BADGE_H + 4 + tw + 8
    end

    local vbar = CreateFrame("Frame", nil, card, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
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
    vbar:SetFrameLevel(sf:GetFrameLevel() + 12)
    vbar:Hide()
    local vthumb = CreateFrame("Button", nil, vbar)
    vthumb:SetWidth(6)
    vthumb:EnableMouse(true)
    local vtTex = nil
    if ns.hui and ns.hui.BuildCapsule then
        vtTex = ns.hui.BuildCapsule(vthumb, 2, ns.hui.layer.L4)
    else
        vtTex = vthumb:CreateTexture(nil, "OVERLAY")
        vtTex:SetAllPoints()
        vtTex:SetColorTexture(1, 1, 1, 0.30)
    end
    vthumb:SetScript("OnEnter", function()
        if type(vtTex) == "table" then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(vtTex) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif vtTex then
            vtTex:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    vthumb:SetScript("OnLeave", function()
        if type(vtTex) == "table" then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(vtTex) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif vtTex then
            vtTex:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    vthumb:SetPoint("TOP", vbar, "TOP", 0, -1)
    local function ovBarUpdate()
        local viewH = sf:GetHeight()
        local contentH = zoomf:GetHeight()
        if not sf:IsShown() or viewH <= 0 or contentH <= viewH + 2 then
            vbar:Hide()
            return
        end
        vbar:ClearAllPoints()
        vbar:SetPoint("TOPRIGHT", sf, "TOPRIGHT", 11, -2)
        vbar:SetPoint("BOTTOMRIGHT", sf, "BOTTOMRIGHT", 11, 30)
        vbar:Show()
        local trackH = vbar:GetHeight() - 2
        local maxScroll = contentH - viewH
        local vpos = sf:GetVerticalScroll() or 0
        if type(vpos) ~= "number" then vpos = 0 end
        local frac = math.max(0, math.min(1, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        vthumb:SetHeight(th)
        vthumb:ClearAllPoints()
        vthumb:SetPoint("TOP", vbar, "TOP", 0, -1 - frac * (trackH - th))
    end
    U.dungeonQOVBar = ovBarUpdate
    vthumb:SetScript("OnMouseDown", function(self, b)
        if b ~= "LeftButton" then return end
        local scale = sf:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = sf:GetVerticalScroll()
        self:SetScript("OnUpdate", function(s)
            local okDown, down = pcall(IsMouseButtonDown, "LeftButton")
            if okDown and down == false then
                s:SetScript("OnUpdate", nil)
                return
            end
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = vbar:GetHeight() - 2
            local span = trackH - vthumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = math.max(0, zoomf:GetHeight() - sf:GetHeight())
            sf:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
            ovBarUpdate()
        end)
    end)
    vthumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    vthumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    sf:SetScript("OnShow", function()
        if U.dungeonQOVBar then U.dungeonQOVBar() end
    end)
    sf:SetScript("OnSizeChanged", function()
        if U.dungeonQOVBar then U.dungeonQOVBar() end
    end)
end

DG.Q_OV_W = 170
DG.Q_OV_H = 42
DG.Q_OV_GAP = 20
DG.Q_OV_RAD = 6
DG.Q_OV_COL = { 8, 8 + 170 + 24 }
DG.Q_OV_DONE = { 0.25, 0.85, 0.35, 1 }
DG.Q_OV_ACT = { 1, 0.82, 0, 1 }
DG.Q_OV_TODO = { 0.55, 0.55, 0.55, 1 }
function DG.PaintQuestOverview(d)
    local ov, canvas, pool = U.dungeonQOverviewF, U.dungeonQOVCanvas, U.dungeonQOVPool
    if not (ov and canvas and pool and d) then return end
    local gcOn = type(collectgarbage) == "function"
    if gcOn then pcall(collectgarbage, "stop") end
    local qovOk, qovErr = pcall(function()
    local list = DG.QuestList(d)
    DG.PrefetchQuestData(list)
    local side = U.dungeonQSide
    if side == "A" or side == "H" then
        local fl = {}
        for i = 1, #list do
            local q = list[i]
            if q[2] == side or not q[2] then fl[#fl + 1] = q end
        end
        list = fl
    end
    local inside = {}
    for i = 1, #list do inside[list[i][1]] = list[i] end
    local parent, extOf, extSeen = {}, {}, {}
    for i = 1, #list do
        local q = list[i]
        local pres = q[9]
        if type(pres) == "table" then
            for _, pid in ipairs(pres) do
                if inside[pid] then
                    if not parent[q[1]] then parent[q[1]] = pid end
                elseif not extSeen[pid] then
                    extSeen[pid] = true
                    extOf[q[1]] = pid
                end
            end
        end
    end
    local depth, listIdx = {}, {}
    for i = 1, #list do listIdx[list[i][1]] = i end
    local function rootOf(qid)
        local cur, n = qid, 0
        while parent[cur] do
            cur = parent[cur]
            n = n + 1
        end
        depth[qid] = n
        return cur
    end
    local chains, colOrder = {}, {}
    for i = 1, #list do
        local q = list[i]
        local r = rootOf(q[1])
        if not chains[r] then
            chains[r] = {}
            colOrder[#colOrder + 1] = r
        end
        local ch = chains[r]
        ch[#ch + 1] = q
    end
    for _, r in ipairs(colOrder) do
        local ch = chains[r]
        table.sort(ch, function(a, b)
            local da, db = depth[a[1]] or 0, depth[b[1]] or 0
            if da ~= db then return da < db end
            return (listIdx[a[1]] or 0) < (listIdx[b[1]] or 0)
        end)
    end
    local chainLab = {}
    for _, r in ipairs(colOrder) do
        local anchor
        for k = 1, #chains[r] do
            if DG.QLCall("GetQuestType", chains[r][k][1]) == 81 then anchor = k break end
        end
        if anchor then
            for k = 1, #chains[r] do
                if k ~= anchor and DG.QLCall("GetQuestType", chains[r][k][1]) ~= 81 then
                    chainLab[chains[r][k][1]] = (k < anchor) and L["前置"] or L["后续"]
                end
            end
        end
    end
    local packs = {}
    for _, r in ipairs(colOrder) do
        packs[#packs + 1] = { r }
    end
    local nCols = #packs
    local COL_GAP = 12
    local availW = ov:GetWidth() or (DG.Q_LIST_W - 24)
    local nw = DG.Q_OV_W
    if nCols > 0 then
        nw = math.floor((availW - 16 - 4 * COL_GAP) / 5)
        if nw < 72 then nw = 72 end
    end
    local colX = {}
    for c = 1, nCols do colX[c] = 8 + (c - 1) * (nw + COL_GAP) end

    local nodes = {}
    local nNode = 0
    local QOV_L2 = ns.hui and ns.hui.layer and ns.hui.layer.L2
    local QOV_ACC = ns.hui and ns.hui.ACCENT
    local function pQovNodeState(n, st)
        local bp = n.__huiCard
        if type(bp) ~= "table" or type(bp.fill) ~= "table" then return end
        if not (ns.hui and ns.hui.GlassPaint and QOV_L2 and QOV_ACC) then return end
        local function tintAlpha()
            if n.tint and n.__tintC then
                local a = (st == "norm") and 0.2 or 0.05
                n.tint:SetVertexColor(n.__tintC[1], n.__tintC[2], n.__tintC[3], a)
            end
        end
        if n.__qovSt == st then tintAlpha() return end
        n.__qovSt = st
        local col = QOV_L2
        if st == "hover" then
            col = (ns.hui.layer and ns.hui.layer.L4) or QOV_L2
        elseif st == "sel" then
            col = {
                QOV_L2[1] + (QOV_ACC[1] - QOV_L2[1]) * 0.28,
                QOV_L2[2] + (QOV_ACC[2] - QOV_L2[2]) * 0.28,
                QOV_L2[3] + (QOV_ACC[3] - QOV_L2[3]) * 0.28,
                1,
            }
        end
        for i = 1, #bp.fill do
            local t = bp.fill[i]
            if t and t.__huiGlass then
                t.__huiGlass.c = col
                ns.hui.GlassPaint(t)
            end
        end
        tintAlpha()
    end
    local function takeNode()
        nNode = nNode + 1
        local n = pool.node[nNode]
        if not n then
            n = CreateFrame("Button", nil, canvas, "BackdropTemplate")
            n:SetSize(DG.Q_OV_W, DG.Q_OV_H)
            n:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            HuiCardFX(n, 12, 2)
            n:EnableMouseWheel(true)
            n:SetScript("OnMouseWheel", function(_, delta)
                if U.dungeonQOVWheel then U.dungeonQOVWheel(delta) end
            end)
            n.name = MakeFS(n, 14, C_TEXT, "LEFT")
            n.name:SetPoint("TOPLEFT", n, "TOPLEFT", 4, -5)
            n.name:SetWidth(DG.Q_OV_W - 12)
            n.name:SetWordWrap(false)
            n.sub = MakeFS(n, 12, C_GREY, "LEFT")
            n.sub:SetPoint("TOPLEFT", n, "TOPLEFT", 4, -25)
            n.sub:SetWidth(DG.Q_OV_W - 12)
            n.sub:SetWordWrap(false)
            n.stbar = n:CreateTexture(nil, "ARTWORK")
            n.stbar:SetSize(4, 24)
            n.stbar:SetPoint("LEFT", n, "LEFT", 3, 0)
            n.posB = DG.MakeBadge(n, DG.Q_BADGE_PRE_BG)
            n.clsB = DG.MakeBadge(n, DG.Q_BADGE_CLS_BG)
            n.tint = n:CreateTexture(nil, "ARTWORK")
            n.tint:SetAllPoints()
            n.tint:Hide()
            n.okD = n:CreateTexture(nil, "ARTWORK")
            n.okD:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
            n.okD:SetSize(DG.Q_BADGE_H, DG.Q_BADGE_H)
            n.okD:SetPoint("BOTTOMRIGHT", n, "BOTTOMRIGHT", -6, DG.Q_OV_H - 24 - DG.Q_BADGE_H)
            n.okD:Hide()
            n.okT = n:CreateTexture(nil, "OVERLAY")
            n.okT:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
            n.okT:SetAllPoints(n.okD)
            n.okT:Hide()
            n:SetScript("OnEnter", function(self)
                pQovNodeState(self, self.__selNow and "sel" or "hover")
                if self.__q then
                    DG.ShowQuestTip(self, self.__q)
                elseif self.__ext then
                    local exrow = DG.ExtQuestRow(self.__ext)
                    if exrow then DG.ShowQuestTip(self, exrow) end
                end
            end)
            n:SetScript("OnLeave", function(self)
                pQovNodeState(self, self.__selNow and "sel" or "norm")
                GameTooltip:Hide()
            end)
            n:SetScript("OnClick", function(self)
                if U.__ovDragDist then return end
                if self.__q then
                    DG.OpenQuest(self.__q[1])
                elseif self.__ext then
                    U.dungeonQDetExt = self.__ext
                    U:RenderDungeonQuests()
                    ns.PlaySound(1)
                end
            end)
            pool.node[nNode] = n
        end
        n:Show()
        return n
    end
    for _, l in ipairs(pool.line) do l:Hide() end
    for _, t in ipairs(pool.arc) do t:Hide() end
    for _, t in ipairs(pool.fil) do t:Hide() end
    local nArc = 0
    local nFil = 0
    local nLine = 0
    local function takeLine()
        nLine = nLine + 1
        local l = pool.line[nLine]
        if not l then
            l = canvas:CreateLine(nil, "ARTWORK", nil, 1)
            l:SetThickness(2.5)
            pool.line[nLine] = l
        end
        l:Show()
        return l
    end

    local function nodeState(q)
        if DG.QuestDone(q[1]) then return DG.Q_OV_DONE end
        if DG.QuestActive(q[1]) then return DG.Q_OV_ACT end
        return DG.Q_OV_TODO
    end
    local MARK_ICON = {
        [DG.Q_OV_DONE] = "Interface\\AddOns\\DungeonsForever\\Media\\CheckMark",
        [DG.Q_OV_ACT] = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkAsk",
        [DG.Q_OV_TODO] = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkExcl",
    }
    local function extState(pid)
        local st = DG.QuestState(pid)
        if st == "done" then return DG.Q_OV_DONE end
        if st == "active" then return DG.Q_OV_ACT end
        return DG.Q_OV_TODO
    end
    local function nodeBorder(n, c)
        local hc = n.__huiCard
        local bd = hc and hc.border
        if bd and #bd > 0 then
            for i = 1, #bd do
                local t = bd[i]
                if c then
                    t:SetVertexColor(c[1], c[2], c[3])
                    t:SetAlpha(c[4] or 1)
                else
                    t:SetVertexColor(1, 1, 1)
                    t:SetAlpha(0.1)
                end
            end
            return
        end
        if n.SetBackdropBorderColor then
            if c then
                n:SetBackdropBorderColor(c[1], c[2], c[3], c[4])
            else
                n:SetBackdropBorderColor(1, 1, 1, 0.1)
            end
        end
    end
    local MARK_INK = {
        [DG.Q_OV_DONE] = { 0.043, 0.239, 0.102 },
        [DG.Q_OV_ACT] = { 0.227, 0.165, 0 },
        [DG.Q_OV_TODO] = { 0.102, 0.102, 0.102 },
    }
    local function setMark(n, c)
        if n.okD then
            n.okD:SetVertexColor(c[1], c[2], c[3], 1)
            n.okD:Show()
        end
        if n.okT then
            n.okT:SetTexture(MARK_ICON[c] or MARK_ICON[DG.Q_OV_TODO])
            local k = MARK_INK[c]
            if k then
                n.okT:SetVertexColor(k[1], k[2], k[3], 1)
            else
                n.okT:SetVertexColor(1, 1, 1, 1)
            end
            n.okT:Show()
        end
    end
    local function applyState(n, c)
        if n.stbar then n.stbar:SetVertexColor(c[1], c[2], c[3], c[4]) end
        nodeBorder(n, (c == DG.Q_OV_TODO) and nil or c)
        setMark(n, c)
    end
    local function place(q, c, y)
        local n = takeNode()
        n:SetSize(nw, DG.Q_OV_H)
        n.name:SetWidth(nw - 8)
        n.sub:SetWidth(nw - 8)
        n.__q = q
        n.__ext = nil
        local nm = DG.QuestName(q[1])
        DG.ClipTo(n.name, nm, nw - 8)
        n.name:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3], 1)
        n.stbar:Show()
        n.stbar:SetSize(4, 24)
        local chainText = chainLab[q[1]]
        n.posB.__wantCol = chainText and DG.Q_BADGE_PRE_BG or DG.Q_BADGE_IN_BG
        DG.BadgeTint(n.posB, n.posB.__wantCol)
        n.posB.lab:SetText(chainText or ((DG.QLCall("GetQuestType", q[1]) == 81) and L["地下城"] or L["副本内"]))
        local bw = (n.posB.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2
        n.posB:SetWidth(bw)
        n.posB:ClearAllPoints()
        n.posB:SetPoint("TOPLEFT", n, "TOPLEFT", 6, -24)
        n.posB:Show()
        DG.QuestOverviewClsBadge(n, q[15])
        n.sub:SetText("")
        applyState(n, nodeState(q))
        n.tint:Hide()
        n.__tintC = nil
        n.__selNow = (q[1] == U.dungeonQuestSel)
        pQovNodeState(n, n.__selNow and "sel" or "norm")
        n:ClearAllPoints()
        n:SetPoint("TOPLEFT", canvas, "TOPLEFT", colX[c], -y)
        n.__ox = colX[c]
        n.__oy = y
        return n
    end
    local function placeExt(pid, c, y)
        local n = takeNode()
        n:SetSize(nw, DG.Q_OV_H)
        n.name:SetWidth(nw - 8)
        n.sub:SetWidth(nw - 8)
        n.__q = nil
        n.__ext = pid
        local nm = DG.QuestName(pid)
        DG.ClipTo(n.name, nm, nw - 8)
        n.name:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3], 1)
        local exinfo = ns.EnsureDungeonQuestExtInfo()[pid]
        DG.QuestOverviewClsBadge(n, exinfo and exinfo.cls)
        n.sub:SetText("")
        n.stbar:Show()
        n.stbar:SetSize(4, 24)
        n.posB.__wantCol = DG.Q_BADGE_PRE_BG
        DG.BadgeTint(n.posB, n.posB.__wantCol)
        n.posB.lab:SetText(L["前置"])
        local bw = (n.posB.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2
        n.posB:SetWidth(bw)
        n.posB:ClearAllPoints()
        n.posB:SetPoint("TOPLEFT", n, "TOPLEFT", 6, -24)
        n.posB:Show()
        applyState(n, extState(pid))
        n.tint:Hide()
        n.__tintC = nil
        n.__selNow = (U.dungeonQDetExt ~= nil and pid == U.dungeonQDetExt)
        pQovNodeState(n, n.__selNow and "sel" or "norm")
        n:ClearAllPoints()
        n:SetPoint("TOPLEFT", canvas, "TOPLEFT", colX[c], -y)
        n.__ox = colX[c]
        n.__oy = y
        return n
    end
    local function placeMark(title, subText, tintC, x, y, bC, subC)
        local n = takeNode()
        n:SetSize(nw, DG.Q_OV_H)
        n.name:SetWidth(nw - 8)
        n.sub:SetWidth(nw - 8)
        n.__q = nil
        n.__ext = nil
        n.name:SetText(title)
        n.name:SetTextColor(tintC[1], tintC[2], tintC[3], 1)
        n.sub:SetText(subText)
        if subC then
            n.sub:SetTextColor(subC[1], subC[2], subC[3], 1)
        else
            n.sub:SetTextColor(C_GREY[1], C_GREY[2], C_GREY[3], 1)
        end
        if n.posB then n.posB:Hide() end
        if n.clsB then n.clsB:Hide() end
        n.stbar:Hide()
        if n.okD then n.okD:Hide() end
        if n.okT then n.okT:Hide() end
        nodeBorder(n, bC)
        n.__tintC = tintC
        n.__selNow = false
        n.tint:SetVertexColor(tintC[1], tintC[2], tintC[3], 0.2)
        n.tint:Show()
        pQovNodeState(n, "norm")
        n:ClearAllPoints()
        n:SetPoint("TOPLEFT", canvas, "TOPLEFT", x, -y)
        n.__ox = x
        n.__oy = y
        return n
    end

    local ROWH = DG.Q_OV_H + DG.Q_OV_GAP
    local function rowY(rr)
        return ROWH * (rr + 1)
    end
    local RAD = DG.Q_OV_RAD or 6
    local function lineLvl(lc)
        if lc == DG.Q_OV_DONE then return 4 end
        if lc == DG.Q_OV_ACT then return 2 end
        return 0
    end
    local function rawSeg(x1, y1, x2, y2, lc)
        if math.abs(x2 - x1) < 0.05 and math.abs(y2 - y1) < 0.05 then return end
        local l = takeLine()
        l:SetColorTexture(lc[1], lc[2], lc[3], 0.9)
        l:SetDrawLayer("ARTWORK", lineLvl(lc))
        l:SetStartPoint("TOPLEFT", canvas, x1, -y1)
        l:SetEndPoint("TOPLEFT", canvas, x2, -y2)
    end
    local LINEW = 2.5
    local ARC_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\DFLineArc"
    local function takeArc()
        nArc = nArc + 1
        local t = pool.arc[nArc]
        if not t then
            t = canvas:CreateTexture(nil, "ARTWORK")
            t:SetTexture(ARC_TEX)
            pool.arc[nArc] = t
        end
        t:Show()
        return t
    end
    local function arcLvl(lc)
        return lineLvl(lc) + 1
    end
    local function rawArc(px, py, ix, iy, ox, oy, r, lc)
        local cx = px - ix * r + ox * r
        local cy = py - iy * r + oy * r
        local out = r + LINEW / 2
        local sx = (ox ~= 0) and -ox or ix
        local sy = (oy ~= 0) and -oy or iy
        local x0 = (sx > 0) and cx or cx - out
        local y0 = (sy > 0) and cy or cy - out
        local u = (r + LINEW / 2) / 16
        local a, b, c, d = 0, 0, 0, u
        local e, f, g, h = u, 0, u, u
        if sx < 0 then a, c, e, g = u, u, 0, 0 end
        if sy < 0 then b, d, f, h = u, 0, u, 0 end
        local t = takeArc()
        t:SetTexCoord(a, b, c, d, e, f, g, h)
        t:SetDrawLayer("ARTWORK", arcLvl(lc))
        t:SetSize(out, out)
        t:ClearAllPoints()
        t:SetPoint("TOPLEFT", canvas, "TOPLEFT", x0, -y0)
        t:SetVertexColor(lc[1], lc[2], lc[3], 0.9)
    end
    local FIL_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\DFLineFil"
    local FIL_R = 8
    local FIL_OUT = FIL_R + LINEW / 2
    local FIL_UV = FIL_OUT / 16
    local function fillet(cx, cy, sx, sy, lc)
        local u = FIL_UV
        local a, b, c, d = 0, 0, 0, u
        local e, f, g, h = u, 0, u, u
        if sx < 0 then a, c, e, g = u, u, 0, 0 end
        if sy < 0 then b, d, f, h = u, 0, u, 0 end
        nFil = nFil + 1
        local t = pool.fil[nFil]
        if not t then
            t = canvas:CreateTexture(nil, "ARTWORK")
            t:SetTexture(FIL_TEX)
            pool.fil[nFil] = t
        end
        t:Show()
        t:SetTexCoord(a, b, c, d, e, f, g, h)
        t:SetDrawLayer("ARTWORK", arcLvl(lc))
        t:SetSize(FIL_OUT, FIL_OUT)
        t:ClearAllPoints()
        t:SetPoint("TOPLEFT", canvas, "TOPLEFT", (sx > 0) and cx or (cx - FIL_OUT), -((sy > 0) and cy or (cy - FIL_OUT)))
        t:SetVertexColor(lc[1], lc[2], lc[3], 0.9)
    end
    local function path(lc, pts)
        local n = #pts
        if n < 2 then return end
        local seg = {}
        for i = 1, n - 1 do
            local dx = pts[i + 1][1] - pts[i][1]
            local dy = pts[i + 1][2] - pts[i][2]
            seg[i] = { x = dx, y = dy, len = math.sqrt(dx * dx + dy * dy) }
        end
        local cutIn, cutOut = {}, {}
        for i = 1, n do cutIn[i], cutOut[i] = 0, 0 end
        for i = 2, n - 1 do
            local a, b = seg[i - 1], seg[i]
            if a.len > 0.05 and b.len > 0.05 then
                local ax, ay = a.x / a.len, a.y / a.len
                local bx, by = b.x / b.len, b.y / b.len
                if math.abs(ax - bx) > 0.01 or math.abs(ay - by) > 0.01 then
                    local r = math.min(RAD, a.len - cutOut[i - 1], b.len)
                    if r >= 1.5 then
                        cutIn[i], cutOut[i] = r, r
                    end
                end
            end
        end
        for i = 1, n - 1 do
            local s = seg[i]
            local ux, uy = 0, 0
            if s.len > 0.05 then ux, uy = s.x / s.len, s.y / s.len end
            rawSeg(pts[i][1] + ux * cutOut[i], pts[i][2] + uy * cutOut[i],
                    pts[i + 1][1] - ux * cutIn[i + 1], pts[i + 1][2] - uy * cutIn[i + 1], lc)
            local r = cutIn[i + 1]
            if r > 0 and i < n - 1 then
                local px, py = pts[i + 1][1], pts[i + 1][2]
                local o = seg[i + 1]
                local vx, vy = 0, 0
                if o.len > 0.05 then vx, vy = o.x / o.len, o.y / o.len end
                rawArc(px, py, ux, uy, vx, vy, r, lc)
            end
        end
    end
    local function vline(x, yTop, yBot, lc)
        rawSeg(x, yTop, x, yBot, lc)
    end
    local function elbow(x1, y1, x2, y2, lc)
        if x1 == x2 then
            vline(x1, y1, y2, lc)
            return
        end
        local midY = (y1 + y2) / 2
        path(lc, { { x1, y1 }, { x1, midY }, { x2, midY }, { x2, y2 } })
    end
    local function lineColor(childQ, srcQ)
        if DG.QuestDone(childQ[1]) or (srcQ and DG.QuestDone(srcQ[1])) then
            return DG.Q_OV_DONE
        end
        if DG.QuestActive(childQ[1]) or (srcQ and DG.QuestActive(srcQ[1])) then
            return DG.Q_OV_ACT
        end
        return DG.Q_OV_TODO
    end

    local function hline(y, x1, x2, lc)
        rawSeg(x1, y, x2, y, lc)
    end
    local function laneElbow(x, y1, y2, lc)
        if y2 - y1 < ROWH then
            vline(x, y1, y2, lc)
            return
        end
        local lx = math.max(0, x - nw / 2 - 6)
        path(lc, { { x, y1 }, { x, y1 + 8 }, { lx, y1 + 8 }, { lx, y2 - 8 }, { x, y2 - 8 }, { x, y2 } })
    end

    local canvasW = (nCols > 0) and (colX[nCols] + nw + 8) or math.max(DG.Q_LIST_W - 24, 200)
    if nCols > 0 and DG.CurQuestFlow(d) then
        canvasW = math.max(canvasW, nw * 5 + COL_GAP * 2 + 32)
    end
    local startCX = math.max(8, (canvasW - nw) / 2)
    local maxRR = 0
    if nCols == 0 and U.dungeonQOVFlowCard then U.dungeonQOVFlowCard:Hide() end
    if nCols > 0 then
        local minLv, maxLv = nil, nil
        for i = 1, #list do
            local lv = tonumber(list[i][3])
            if lv then
                if not minLv or lv < minLv then minLv = lv end
                if not maxLv or lv > maxLv then maxLv = lv end
            end
        end
        local dMin = (minLv and DG.DifficultyColor(minLv)) or DG.Q_OV_DONE
        local dMax = (maxLv and DG.DifficultyColor(maxLv)) or { 1, 0.5, 0.25, 1 }
        local lvB = (maxLv and (UnitLevel("player") or 0) >= maxLv) and DG.Q_OV_DONE or nil
        placeMark(format(L["最低 %d 级"], minLv or 1), format(L["最高 %d 级"], maxLv or minLv or 1), dMin, startCX, 0, lvB, dMax)
        local fw = nw * 2 + COL_GAP
        DG.PaintOverviewFlow(d, canvas, canvasW - 8 - fw, fw)

        local nodeByQid, nodeByExt = {}, {}
        local extDone = {}
        local placed = {}
        local colBot = {}
        for c = 1, nCols do
            local rr = 0
            local prev = nil
            for _, r in ipairs(packs[c]) do
                local ch = chains[r]
                for k = 1, #ch do
                    local q = ch[k]
                    local pres = q[9]
                    if type(pres) == "table" then
                        for _, pid in ipairs(pres) do
                            if type(pid) == "number" and not inside[pid] and not extDone[pid] then
                                extDone[pid] = true
                                local chainEx = { pid }
                                local cur = pid
                                while true do
                                    local pe = ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[cur]
                                    cur = (type(pe) == "table" and pe[1] and not inside[pe[1]]) and pe[1] or nil
                                    if not cur or extDone[cur] then break end
                                    extDone[cur] = true
                                    table.insert(chainEx, 1, cur)
                                end
                                local lastN = nil
                                for _, xid in ipairs(chainEx) do
                                    local en = placeExt(xid, c, rowY(rr))
                                    nodeByExt[xid] = en
                                    rr = rr + 1
                                    if lastN then
                                        vline(colX[c] + nw / 2, lastN.__oy + DG.Q_OV_H, en.__oy, lineColor({ en.__ext }, { lastN.__ext }))
                                    end
                                    lastN = en
                                end
                            end
                        end
                    end
                    local n = place(q, c, rowY(rr))
                    nodeByQid[q[1]] = n
                    placed[#placed + 1] = { q = q, n = n }
                    if prev then
                        local x = colX[c] + nw / 2
                        local y1 = prev.__oy + DG.Q_OV_H
                        local y2 = n.__oy
                        local lc = lineColor(q, prev.__q)
                        if y2 - y1 <= ROWH + 1 then
                            vline(x, y1, y2, lc)
                        else
                            laneElbow(x, y1, y2, lc)
                        end
                    end
                    prev = n
                    rr = rr + 1
                end
            end
            if rr > maxRR then maxRR = rr end
            colBot[c] = prev
        end

        local spineY = (DG.Q_OV_H + rowY(0)) / 2
        local xTop = startCX + nw / 2
        local xL = math.min(xTop, colX[1] + nw / 2)
        local xR = colX[nCols] + nw / 2
        local bendR = math.min(RAD, rowY(0) - spineY)
        local bend = (xR - xL) > bendR * 2
        local lo = bend and (xL + bendR) or xL
        local hi = bend and (xR - bendR) or xR
        local anyDone, anyAct = false, false
        local marks = {}
        for c = 1, nCols do
            local tq = chains[packs[c][1]][1]
            local dn = (tq and DG.QuestDone(tq[1])) or false
            local ac = (tq and DG.QuestActive(tq[1])) or false
            if dn then anyDone = true end
            if ac then anyAct = true end
            marks[#marks + 1] = { x = colX[c] + nw / 2, dn = dn, ac = ac, c = c, lc = lineColor(tq, nil) }
        end
        local onCol = false
        for c = 1, nCols do
            if math.abs(colX[c] + nw / 2 - xTop) < 0.5 then onCol = true break end
        end
        if not onCol then marks[#marks + 1] = { x = xTop, dn = false, ac = false } end
        table.sort(marks, function(p, r) return p.x < r.x end)
        local splitR = 0
        if not onCol and (spineY - DG.Q_OV_H) > RAD + 1 then
            local iTrunk
            for i = 1, #marks do
                if math.abs(marks[i].x - xTop) < 0.5 then iTrunk = i break end
            end
            if iTrunk and iTrunk > 1 and iTrunk < #marks then
                local gl = xTop - marks[iTrunk - 1].x
                local gr = marks[iTrunk + 1].x - xTop
                if gl > RAD + 2 and gr > RAD + 2 then splitR = RAD end
            end
        end
        local vtop = {}
        for i = 1, #marks do
            local m = marks[i]
            m.junc = false
            if m.c and i > 1 and i < #marks then
                local onHub = onCol and (math.abs(m.x - xTop) < 0.5)
                if not onHub and (m.x - marks[i - 1].x) > FIL_R + 2 and (marks[i + 1].x - m.x) > FIL_R + 2 then
                    m.junc = true
                end
            end
            if m.c then vtop[m.c] = spineY + (m.junc and FIL_R or LINEW / 2) end
        end
        local rDoneL, rDoneR, rActL, rActR = 0, 0, 0, 0
        for i = 1, #marks do
            local m = marks[i]
            local dl = xTop - m.x
            local dr = m.x - xTop
            if m.dn then
                if dl > rDoneL then rDoneL = dl end
                if dr > rDoneR then rDoneR = dr end
            end
            if m.ac then
                if dl > rActL then rActL = dl end
                if dr > rActR then rActR = dr end
            end
        end
        local lcNearL, lcNearR
        for i = 1, #marks - 1 do
            local a, b = marks[i], marks[i + 1]
            local outer = math.max(math.abs(a.x - xTop), math.abs(b.x - xTop))
            local left = ((a.x + b.x) / 2 < xTop)
            local lc = DG.Q_OV_TODO
            if outer <= (left and rDoneL or rDoneR) + 0.5 then
                lc = DG.Q_OV_DONE
            elseif outer <= (left and rActL or rActR) + 0.5 then
                lc = DG.Q_OV_ACT
            end
            if splitR > 0 then
                if math.abs(b.x - xTop) < 0.5 then lcNearL = lc end
                if math.abs(a.x - xTop) < 0.5 then lcNearR = lc end
            end
            a.segr = lc
            b.segl = lc
            local s1, s2 = a.x, b.x
            if a.junc then s1 = a.x + ((a.x < xTop) and FIL_R or -FIL_R) end
            if b.junc then s2 = b.x + ((b.x < xTop) and FIL_R or -FIL_R) end
            s1 = math.max(s1, lo)
            s2 = math.min(s2, hi)
            if splitR > 0 then
                if a.x >= xTop - 0.5 then s1 = math.max(s1, xTop + splitR) end
                if b.x <= xTop + 0.5 then s2 = math.min(s2, xTop - splitR) end
            end
            if s2 - s1 > 0.25 then hline(spineY, s1, s2, lc) end
        end
        for i = 1, #marks do
            local m = marks[i]
            if m.junc then
                local lc = m.lc or DG.Q_OV_TODO
                if m.x < xTop then
                    fillet(m.x + FIL_R, spineY + FIL_R, -1, -1, lc)
                else
                    fillet(m.x - FIL_R, spineY + FIL_R, 1, -1, lc)
                end
            end
        end
        if splitR > 0 then
            local lcT = DG.Q_OV_TODO
            if lcNearL == DG.Q_OV_DONE or lcNearR == DG.Q_OV_DONE then
                lcT = DG.Q_OV_DONE
            elseif lcNearL == DG.Q_OV_ACT or lcNearR == DG.Q_OV_ACT then
                lcT = DG.Q_OV_ACT
            end
            vline(xTop, DG.Q_OV_H, spineY - splitR, lcT)
            rawArc(xTop, spineY, 0, 1, -1, 0, splitR, lcNearL or lcT)
            rawArc(xTop, spineY, 0, 1, 1, 0, splitR, lcNearR or lcT)
        else
            local lcT = DG.Q_OV_TODO
            if anyDone then
                lcT = DG.Q_OV_DONE
            elseif anyAct then
                lcT = DG.Q_OV_ACT
            end
            if not (nCols == 1 and onCol) then vline(xTop, DG.Q_OV_H, spineY, lcT) end
        end
        local oneCol = (nCols == 1 and onCol)
        for c = 1, nCols do
            local topQ = chains[packs[c][1]][1]
            local lc = lineColor(topQ, nil)
            local xc = colX[c] + nw / 2
            if bend and xc == xL then
                path(lc, { { xL + bendR, spineY }, { xL, spineY }, { xL, rowY(0) } })
            elseif bend and xc == xR then
                path(lc, { { xR - bendR, spineY }, { xR, spineY }, { xR, rowY(0) } })
            elseif oneCol then
                vline(xc, DG.Q_OV_H, rowY(0), lc)
            else
                vline(xc, vtop[c] or (spineY + LINEW / 2), rowY(0), lc)
            end
        end

        local endY = rowY(maxRR)
        local endCX = startCX
        local allDone = true
        for i = 1, #list do
            if not DG.QuestDone(list[i][1]) then
                allDone = false
                break
            end
        end
        if allDone then
            local en = placeMark(L["已完成"], L["任务路线"], DG.Q_OV_DONE, endCX, endY, DG.Q_OV_DONE)
            setMark(en, DG.Q_OV_DONE)
        else
            placeMark(L["未完成"], L["任务路线"], { 0.85, 0.25, 0.25, 1 }, endCX, endY)
        end
        local corrY = endY - 10
        local xEndC = endCX + nw / 2
        local bmarks = {}
        for c = 1, nCols do
            local bn = colBot[c]
            if bn then
                bmarks[#bmarks + 1] = {
                    x = colX[c] + nw / 2,
                    y = bn.__oy + DG.Q_OV_H,
                    dn = (bn.__q and DG.QuestDone(bn.__q[1])) and true or false,
                    ac = (bn.__q and DG.QuestActive(bn.__q[1])) and true or false,
                }
            end
        end
        bmarks[#bmarks + 1] = { x = xEndC, y = corrY, dn = allDone, ac = false }
        table.sort(bmarks, function(p, r) return p.x < r.x end)
        local endOnCol = false
        for c = 1, nCols do
            if math.abs(colX[c] + nw / 2 - xEndC) < 0.5 then endOnCol = true break end
        end
        local hubR = 0
        if not endOnCol and (endY - corrY) > RAD + 1 then
            local iHub
            for i = 1, #bmarks do
                if math.abs(bmarks[i].x - xEndC) < 0.5 then iHub = i break end
            end
            if iHub and iHub > 1 and iHub < #bmarks then
                if (xEndC - bmarks[iHub - 1].x) > RAD + 2 and (bmarks[iHub + 1].x - xEndC) > RAD + 2 then
                    hubR = RAD
                end
            end
        end
        for i = 1, #bmarks do
            local m = bmarks[i]
            m.junc = false
            local isHub = (hubR > 0) and (math.abs(m.x - xEndC) < 0.5)
            local onHub = endOnCol and (math.abs(m.x - xEndC) < 0.5)
            if not isHub and not onHub and i > 1 and i < #bmarks then
                if (m.x - bmarks[i - 1].x) > FIL_R + 2 and (bmarks[i + 1].x - m.x) > FIL_R + 2
                    and (corrY - m.y) > FIL_R + LINEW / 2 then
                    m.junc = true
                end
            end
        end
        local cLo = bmarks[1].x + RAD
        local cHi = bmarks[#bmarks].x - RAD
        local hDoneL, hDoneR, hActL, hActR = 0, 0, 0, 0
        for i = 1, #bmarks do
            local m = bmarks[i]
            local dl = xEndC - m.x
            local dr = m.x - xEndC
            if m.dn then
                if dl > hDoneL then hDoneL = dl end
                if dr > hDoneR then hDoneR = dr end
            end
            if m.ac then
                if dl > hActL then hActL = dl end
                if dr > hActR then hActR = dr end
            end
        end
        local lcHubL, lcHubR
        for i = 1, #bmarks - 1 do
            local a, b = bmarks[i], bmarks[i + 1]
            local outer = math.max(math.abs(a.x - xEndC), math.abs(b.x - xEndC))
            local left = ((a.x + b.x) / 2 < xEndC)
            local lc = DG.Q_OV_TODO
            if outer <= (left and hDoneL or hDoneR) + 0.5 then
                lc = DG.Q_OV_DONE
            elseif outer <= (left and hActL or hActR) + 0.5 then
                lc = DG.Q_OV_ACT
            end
            if hubR > 0 then
                if math.abs(b.x - xEndC) < 0.5 then lcHubL = lc end
                if math.abs(a.x - xEndC) < 0.5 then lcHubR = lc end
            end
            a.segr = lc
            b.segl = lc
            local s1, s2 = a.x, b.x
            if a.junc then s1 = a.x + ((a.x < xEndC) and FIL_R or -FIL_R) end
            if b.junc then s2 = b.x + ((b.x < xEndC) and FIL_R or -FIL_R) end
            s1 = math.max(s1, cLo)
            s2 = math.min(s2, cHi)
            if hubR > 0 then
                if a.x >= xEndC - 0.5 then s1 = math.max(s1, xEndC + hubR) end
                if b.x <= xEndC + 0.5 then s2 = math.min(s2, xEndC - hubR) end
            end
            if s2 - s1 > 0.25 then hline(corrY, s1, s2, lc) end
        end
        local singleCol = (#bmarks > 1) and (math.abs(bmarks[1].x - bmarks[#bmarks].x) < 0.5)
        for i = 1, #bmarks do
            local m = bmarks[i]
            local lc = m.dn and DG.Q_OV_DONE or (m.ac and DG.Q_OV_ACT or DG.Q_OV_TODO)
            local isHub = (hubR > 0) and (math.abs(m.x - xEndC) < 0.5)
            if i == 1 and not singleCol then
                path(lc, { { m.x, m.y }, { m.x, corrY }, { m.x + RAD, corrY } })
            elseif i == #bmarks and not singleCol then
                path(lc, { { m.x, m.y }, { m.x, corrY }, { m.x - RAD, corrY } })
            elseif not isHub and math.abs(m.y - corrY) > 0.25 then
                local ey
                if m.junc then
                    ey = corrY - FIL_R
                elseif singleCol then
                    ey = corrY
                else
                    ey = corrY + ((m.y < corrY) and -LINEW / 2 or LINEW / 2)
                end
                vline(m.x, math.min(m.y, ey), math.max(m.y, ey), lc)
            end
        end
        for i = 1, #bmarks do
            local m = bmarks[i]
            if m.junc then
                local lc = m.dn and DG.Q_OV_DONE or (m.ac and DG.Q_OV_ACT or DG.Q_OV_TODO)
                if m.x < xEndC then
                    fillet(m.x + FIL_R, corrY - FIL_R, -1, 1, lc)
                else
                    fillet(m.x - FIL_R, corrY - FIL_R, 1, 1, lc)
                end
            end
        end
        if hubR > 0 then
            local lcE = allDone and DG.Q_OV_DONE or DG.Q_OV_TODO
            rawArc(xEndC, corrY, 1, 0, 0, 1, hubR, lcHubL or lcE)
            rawArc(xEndC, corrY, -1, 0, 0, 1, hubR, lcHubR or lcE)
            vline(xEndC, corrY + hubR, endY, lcE)
        else
            vline(xEndC, corrY, endY, allDone and DG.Q_OV_DONE or DG.Q_OV_TODO)
        end

        for i = 1, #list do
            local q = list[i]
            local cn = nodeByQid[q[1]]
            local pres = q[9]
            if cn and type(pres) == "table" then
                for _, pid in ipairs(pres) do
                    if inside[pid] then
                        if parent[q[1]] ~= pid then
                            local pn = nodeByQid[pid]
                            if pn then
                                elbow(pn.__ox + nw / 2, pn.__oy + DG.Q_OV_H, cn.__ox + nw / 2, cn.__oy, lineColor(q, pn.__q))
                            end
                        end
                    else
                        local en = nodeByExt[pid]
                        if en then
                            vline(cn.__ox + nw / 2, en.__oy + DG.Q_OV_H, cn.__oy, lineColor(q, { en.__ext }))
                        end
                    end
                end
            end
        end

        local curN = nil
        for i = 1, #placed do
            if DG.QuestActive(placed[i].q[1]) then
                curN = placed[i].n
                break
            end
        end
        if curN then
            curN.name:SetTextColor(1, 0.82, 0, 1)
            curN.stbar:SetSize(6, 28)
        end
    end

    local cvh = (nCols > 0) and (rowY(maxRR) + DG.Q_OV_H + 8) or 10
    canvas:SetSize(canvasW, cvh)
    if U.__ovFitW ~= math.floor(canvasW) then
        U.__ovFitW = math.floor(canvasW)
        U.dungeonQOVZoom = math.max(0.5, math.min(1, availW / canvasW))
        if U.dungeonQOVLabel then U.dungeonQOVLabel() end
    end
    canvas:SetScale(U.dungeonQOVZoom or 1)
    if U.dungeonQOVSync then U.dungeonQOVSync() end
    if U.dungeonQOVClamp then U.dungeonQOVClamp() end
    for i = nNode + 1, #(pool.node) do pool.node[i]:Hide() end
    end)
    if gcOn then pcall(collectgarbage, "restart") end
    if not qovOk then _G.DF_QOV_ERR = tostring(qovErr) end
end

function DG.EnsureGuideLane()
    if U.guideLaneBuilt then return end
    local detail = U.dungeonDetail
    if not detail then return end
    U.guideLaneBuilt = true
    local gscroll = CreateFrame("ScrollFrame", nil, detail)
    gscroll:SetFrameLevel(U.dungeonDetailBase + 1)
    gscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.GUIDE_TOP_Y)
    gscroll:SetPoint("BOTTOMRIGHT", detail, "BOTTOMRIGHT", 0, 0)
    local gchild = CreateFrame("Frame", nil, gscroll)
    gchild:SetSize(DG.CHILD_W, 10)
    gscroll:SetScrollChild(gchild)
    gscroll:EnableMouseWheel(true)
    gscroll:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(self, U.dungeonGuideChild, delta)
    end)
    gscroll:Hide()
    gscroll:HookScript("OnShow", function() DG.CullGuideCards() end)
    U.dungeonGuideScroll = gscroll
    U.dungeonGuideChild = gchild
    U.dungeonGuidePool = { card = {} }
    U.dungeonGMask = DG.DetailTopMask(DG.GUIDE_TOP_Y)
    DG.RaiseDetailChrome()

end

function DG.EnsureMapPage()
    if U.mapPageBuilt then return end
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    U.mapPageBuilt = true
    if ns.MapModule then
        U.dungeonMapFrame = ns.MapModule.Build(detail, hero)
    end

end

function DG.EnsureDetailBuilt()
    if U.detailBuilt then return end
    local detail = U.dungeonDetail
    local listScroll = U.dungeonListScroll
    if not (detail and listScroll) then return end
    U.detailBuilt = true
    local hero = CreateFrame("Frame", nil, detail)
    hero:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, 0)
    hero:SetPoint("TOPRIGHT", detail, "TOPRIGHT", 0, 0)
    hero:SetHeight(DG.HERO_H)
    hero.art = hero:CreateTexture(nil, "BACKGROUND")
    hero.art:SetAllPoints()
    hero.fade = {}
    for i = 1, #DG.HERO_FADE do
        local seg = DG.HERO_FADE[i]
        local t = hero:CreateTexture(nil, "ARTWORK")
        t:SetTexture("Interface/Buttons/WHITE8X8")
        local a1, a2 = seg[3], seg[4]
        if DG.HERO_FADE_REVERSED then a1, a2 = a2, a1 end
        t:SetGradient("HORIZONTAL", CreateColor(0, 0, 0, a1), CreateColor(0, 0, 0, a2))
        hero.fade[i] = t
    end
    local function LayoutHeroFade()
        local w = (hero.GetWidth and hero:GetWidth()) or 0
        if type(w) ~= "number" or w <= 0 then return end
        for i = 1, #DG.HERO_FADE do
            local seg = DG.HERO_FADE[i]
            local t = hero.fade[i]
            if t then
                t:ClearAllPoints()
                t:SetPoint("TOPLEFT", hero, "TOPLEFT", math.floor(w * seg[1] + 0.5), 0)
                t:SetPoint("BOTTOMRIGHT", hero, "BOTTOMLEFT", math.floor(w * seg[2] + 0.5), 0)
            end
        end
    end
    hero.LayoutFade = LayoutHeroFade
    LayoutHeroFade()
    hero:HookScript("OnSizeChanged", LayoutHeroFade)
    local heroPlate = hero:CreateTexture(nil, "ARTWORK")
    heroPlate:SetPoint("BOTTOMLEFT", hero, "BOTTOMLEFT", 0, 0)
    heroPlate:SetPoint("BOTTOMRIGHT", hero, "BOTTOMRIGHT", 0, 0)
    heroPlate:SetHeight(DG.HERO_PLATE_H)
    heroPlate:SetTexture("Interface/Buttons/WHITE8X8")
    heroPlate:SetGradient("VERTICAL", CreateColor(0, 0, 0, 1.00), CreateColor(0, 0, 0, 0))
    U.dungeonDetailHero = hero
    U.dungeonDetailBase = hero:GetFrameLevel()

    local back = NewButton(detail, L["副本"], 76, 24, 14)
    back:SetFrameLevel(hero:GetFrameLevel() + 1)
    back:SetPoint("TOPLEFT", detail, "TOPLEFT", 8, -8)
    back:SetScript("OnClick", function()
        if U.dungeonDetailCur and U.dungeonDetailCur.raid and U.SwitchSub then
            U:SwitchSub("Raids")
            ns.PlaySound(1)
            return
        end
        detail:Hide()
        listScroll:Show()
        if U.dungeonListCard then U.dungeonListCard:Show() end
        DG.ListFadesVisible(true)
        DG.CullListRows()
        ns.PlaySound(1)
    end)
    local bicon = back:CreateTexture(nil, "OVERLAY")
    bicon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\BackChevron.tga")
    bicon:SetSize(16, 16)
    bicon:SetPoint("LEFT", back, "LEFT", 7, 0)
    back.__backIcon = bicon
    local bfs = back:GetFontString()
    if bfs then
        bfs:ClearAllPoints()
        bfs:SetPoint("LEFT", 28, 0)
        bfs:SetJustifyH("LEFT")
    end
    U.dungeonBack = back
    U.dungeonDetailTitle = MakeFS(hero, 16, C_WHITE, "LEFT")
    U.dungeonDetailTitle:SetShadowColor(0, 0, 0, 1)
    U.dungeonDetailTitle:SetShadowOffset(1, -1)
    U.dungeonDetailTitle:SetPoint("TOPLEFT", hero, "TOPLEFT", 12, -DG.HERO_TITLE_Y)
    U.dungeonDetailTitle:EnableMouse(true)
    U.dungeonDetailTitle:SetScript("OnMouseUp", function()
        local dd = U.dungeonDetailCur
        if dd then DG.MarkEntrance(dd.id) end
    end)
    U.dungeonDetailTitle:SetScript("OnEnter", function(self) DG.ShowEntranceTip(self) end)
    U.dungeonDetailTitle:SetScript("OnLeave", function() GameTooltip:Hide() end)
    U.dungeonEntChips = {}
    U.dungeonDetailMeta = MakeFS(hero, 14, C_GREY, "LEFT")
    U.dungeonDetailMeta:SetShadowColor(0, 0, 0, 1)
    U.dungeonDetailMeta:SetShadowOffset(1, -1)
    U.dungeonDetailMeta:SetPoint("TOPLEFT", hero, "TOPLEFT", 12, -DG.HERO_META_Y)
    U.dungeonDetailMeta:Hide()
    U.dungeonDetailTipZone = CreateFrame("Frame", nil, detail)
    U.dungeonDetailTipZone:SetPoint("TOPLEFT", detail, "TOPLEFT", 10, -DG.HERO_TITLE_Y + 4)
    U.dungeonDetailTipZone:SetPoint("TOPRIGHT", detail, "TOPRIGHT", 0, -DG.HERO_TITLE_Y + 4)
    U.dungeonDetailTipZone:SetHeight(36)
    U.dungeonDetailTipZone:EnableMouse(true)

    local dscroll = CreateFrame("ScrollFrame", nil, detail)
    if dscroll.SetClipsChildren then dscroll:SetClipsChildren(true) end
    dscroll:SetFrameLevel(U.dungeonDetailBase + 1)
    dscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.SCROLL_Y)
    dscroll:SetPoint("BOTTOMRIGHT", detail, "BOTTOMRIGHT", 0, 0)
    local dchild = CreateFrame("Frame", nil, dscroll)
    dchild:SetSize(DG.CHILD_W, 10)
    dscroll:SetScrollChild(dchild)
    dscroll:EnableMouseWheel(true)
    dscroll:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(self, U.dungeonDetailChild, delta)
    end)
    U.dungeonDetailScroll = dscroll
    U.dungeonDetailChild = dchild
    U.dungeonDetailPool = { hdr = {}, item = {} }
    U.dungeonDetailNote = MakeFS(dchild, 14, C_GREY, "LEFT")
    dscroll:HookScript("OnShow", function() DG.CullLootCards() end)
    U.dungeonLMask = DG.DetailTopMask(DG.SCROLL_Y)
    DG.RaiseDetailChrome()

    U.dungeonTabBtns = {}
    U.dungeonFilterBtns = {}
    U.dungeonLootViewBtns = {}
    DG.PushStep(DG.BuildDetailTabs)
    DG.PushStep(DG.BuildDetailChips)
    DG.PushStep(DG.BuildDetailFilterRow)
    DG.PushStep(DG.BuildDetailLootView)
    DG.PushStep(DG.EnsureQuestLane)
    DG.PushStep(DG.EnsureGuideLane)
    DG.RunSteps()
end

local function ChipTextFor(chip, label, maxw)
    local room = maxw - DG.ENT_CHIP_ICONW - DG.ENT_CHIP_TXTPAD - 4
    if room < 20 then room = 20 end
    local nm = DG.ClipTo(chip, label, room)
    if nm ~= label then
        if nm == "" then nm = "…" else nm = nm .. "…" end
    end
    return nm
end

local function ChipMeasure(chip, label)
    chip:SetSize(DG.ENT_CHIP_MAXW, DG.ENT_CHIP_H)
    chip:SetText(label)
    local fs = chip:GetFontString()
    local tw = (fs and fs:GetStringWidth()) or 0
    if type(tw) ~= "number" then tw = 0 end
    return DG.ENT_CHIP_ICONW + tw + DG.ENT_CHIP_TXTPAD
end

local function ChipResize(chip, w)
    if w < DG.ENT_CHIP_MINW then w = DG.ENT_CHIP_MINW end
    if w > DG.ENT_CHIP_MAXW then w = DG.ENT_CHIP_MAXW end
    chip:SetSize(w, DG.ENT_CHIP_H)
    return w
end

function DG.PaintEntChips(d)
    local chips = U.dungeonEntChips
    if not (d and chips) then return end
    local pts = DG.EntrancePoints(d.id)
    local n = pts and #pts or 0
    local hero = U.dungeonDetailHero
    local title = U.dungeonDetailTitle
    local heroW = (hero and hero.GetWidth and hero:GetWidth()) or 0
    local titleW = (title and title.GetStringWidth and title:GetStringWidth()) or 0
    local rightLimit = 0
    if type(heroW) == "number" and heroW > 0 then rightLimit = heroW - 12 end
    local used = 12 + (type(titleW) == "number" and titleW or 0) + DG.ENT_CHIP_LEAD
    for ci = 1, #chips do
        local chip = chips[ci]
        if ci <= n then
            local p = pts[ci]
            local label = p.label or L["入口"]
            local w = ChipMeasure(chip, label)
            if w > DG.ENT_CHIP_MAXW then
                chip:SetText(ChipTextFor(chip, label, DG.ENT_CHIP_MAXW))
                w = DG.ENT_CHIP_MAXW
            end
            if rightLimit > 0 and used + w > rightLimit then
                local avail = rightLimit - used
                if avail >= DG.ENT_CHIP_MINW and avail < w then
                    chip:SetText(ChipTextFor(chip, label, avail))
                    w = avail
                end
            end
            w = ChipResize(chip, w)
            chip:ClearAllPoints()
            if ci == 1 then
                chip:SetPoint("LEFT", title, "RIGHT", DG.ENT_CHIP_LEAD, 0)
            else
                chip:SetPoint("LEFT", chips[ci - 1], "RIGHT", DG.ENT_CHIP_GAP, 0)
            end
            used = used + w + DG.ENT_CHIP_GAP
            chip:Show()
        else
            chip:Hide()
        end
    end
end

function DG.RefreshFilterRow()
    local cur = U.dungeonTab or "loot"
    if cur == "guide" or cur == "map" then
        for i = 1, #(U.dungeonFilterBtns or {}) do U.dungeonFilterBtns[i]:Hide() end
        return
    end
    if cur == "quest" then DG.EnsureQuestLane() end
    DG.__chromeOnly = true
    local ok, err = pcall(function()
        if cur == "quest" then U:RenderDungeonQuests() else U:RenderDungeonLoot() end
    end)
    DG.__chromeOnly = nil
    if not ok then
        print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
    end
end

function DG.ApplyDetailChrome(cur)
    cur = cur or U.dungeonTab or "loot"
    DG.RaiseDetailChrome()
    local isQuest = (cur == "quest")
    local isGuide = (cur == "guide")
    local isMap   = (cur == "map")
    if #(U.dungeonLootViewBtns or {}) > 0 then
        if cur == "loot" then U:RefreshLootViewBtns() end
        for i = 1, #U.dungeonLootViewBtns do
            U.dungeonLootViewBtns[i]:SetShown(cur == "loot")
        end
    end
    if U.dungeonLootBossDd then
        U.dungeonLootBossDd:SetShown(cur == "loot")
    end
    if isGuide or isMap then
        for i = 1, #(U.dungeonFilterBtns or {}) do
            U.dungeonFilterBtns[i]:Hide()
        end
    end
    for i = 1, #(U.dungeonFilterBtns or {}) do
        local bt = U.dungeonFilterBtns[i]
        if bt and bt.__em then
            if isQuest and (i == 1 or i == 2) then
                local tex = DG.Q_FAC_ICON[(i == 1) and "A" or "H"]
                if tex then
                    bt.__em:SetTexture(tex)
                    bt.__em:Show()
                else
                    bt.__em:Hide()
                end
            else
                bt.__em:Hide()
            end
        end
    end
    if isQuest and U.dungeonQPlateL then
        local plateL = U.dungeonQPlateL
        for i = 1, #(U.dungeonFilterBtns or {}) do
            local bt = U.dungeonFilterBtns[i]
            if bt then
                local bx = DG.Q_PAD
                for k = 1, i - 1 do bx = bx + ((k <= 2) and 92 or 50) end
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", plateL, "TOPLEFT", bx, -DG.Q_PAD)
                bt:SetWidth((i <= 2) and 84 or 42)
                bt:SetFrameLevel(plateL:GetFrameLevel() + 5)
            end
        end
    elseif U.dungeonDetail then
        for i = 1, #(U.dungeonFilterBtns or {}) do
            local bt = U.dungeonFilterBtns[i]
            if bt then
                local bx = (cur == "loot" and i == 1) and 0 or DG.GUTTER + (i - 1) * 100
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", U.dungeonDetail, "TOPLEFT", bx, -DG.FILTER_Y)
                if not (cur == "loot" and i == 1) then bt:SetWidth(92) end
            end
        end
    end
    if U.dungeonQDoneTg then
        local tg = U.dungeonQDoneTg
        if isQuest and U.dungeonQPlateL then
            local plateL = U.dungeonQPlateL
            tg:ClearAllPoints()
            tg:SetPoint("TOPRIGHT", plateL, "TOPRIGHT", -DG.Q_PAD, -DG.Q_PAD - 2)
            tg:SetFrameLevel(plateL:GetFrameLevel() + 5)
            tg:Show()
        else
            tg:Hide()
        end
    end
    if U.dungeonQuestPinTg then
        local tg = U.dungeonQuestPinTg
        if isQuest and U.dungeonQDoneTg then
            tg:ClearAllPoints()
            tg:SetPoint("RIGHT", U.dungeonQDoneTg.label, "LEFT", -8, 0)
            tg:SetFrameLevel(U.dungeonQDoneTg:GetFrameLevel())
            tg:Show()
        else
            tg:Hide()
        end
    end
    if U.dungeonQuestPinCfg then
        local bt = U.dungeonQuestPinCfg
        if isQuest and U.dungeonQuestPinTg then
            bt:ClearAllPoints()
            bt:SetPoint("RIGHT", U.dungeonQuestPinTg.label, "LEFT", -6, 0)
            bt:SetFrameLevel(U.dungeonQuestPinTg:GetFrameLevel())
            bt:Show()
        else
            bt:Hide()
        end
    end
    for key, bt in pairs(U.dungeonTabBtns or {}) do
        local sel = (key == cur)
        ns.hui.SetButtonSelected(bt, sel)
    end
end

function DG.BuildDetailTabs()
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    if next(U.dungeonTabBtns or {}) then return end
    local tabs = { { key = "loot", text = L["掉落"] }, { key = "quest", text = L["任务"] }, { key = "guide", text = L["攻略"] }, { key = "map", text = L["地图"] } }
    for i, def in ipairs(tabs) do
        local bt = NewButton(detail, def.text, 70, 24, 14)
        bt:SetFrameLevel(hero:GetFrameLevel() + 1)
        bt:SetPoint("TOPRIGHT", detail, "TOPRIGHT", -8 - (i - 1) * 78, -(DG.HERO_META_Y - 12))
        bt:SetScript("OnClick", function()
            U:SetDungeonTab(def.key)
        end)
        U.dungeonTabBtns[def.key] = bt
    end
    DG.ApplyDetailChrome(U.dungeonTab or "loot")
end

function DG.BuildDetailChips()
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    if next(U.dungeonEntChips or {}) then return end
    for i = 1, 3 do
        local chip = NewButton(detail, "", DG.ENT_CHIP_MINW, DG.ENT_CHIP_H, 14)
        AddBtnIcon(chip, "EntryPin", 14, 5)
        chip:SetFrameLevel(hero:GetFrameLevel() + 1)
        chip.__entIdx = i
        chip:SetScript("OnClick", function(self)
            local dd = U.dungeonDetailCur
            if dd then DG.MarkEntranceAt(dd.id, self.__entIdx) end
        end)
        chip:SetScript("OnEnter", function(self) DG.ShowEntrancePointTip(self, self.__entIdx) end)
        chip:SetScript("OnLeave", function() GameTooltip:Hide() end)
        chip:Hide()
        U.dungeonEntChips[i] = chip
    end
    DG.PaintEntChips(U.dungeonDetailCur)
end

function DG.BuildDetailFilterRow()
    local detail, hero = U.dungeonDetail, U.dungeonDetailHero
    if not (detail and hero) then return end
    if next(U.dungeonFilterBtns or {}) then return end
    for i = 1, DG.FILTER_MAX do
        local bt = NewButton(detail, "", 92, 24, 14)
        bt:SetPushedTextOffset(0, 0)
        bt:SetPoint("TOPLEFT", detail, "TOPLEFT", DG.GUTTER + (i - 1) * 100, -DG.FILTER_Y)
        bt.__mode, bt.__key = "loot", "all"
        local em = bt:CreateTexture(nil, "OVERLAY")
        em:SetSize(16, 16)
        em:SetPoint("LEFT", bt, "LEFT", 7, 0)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(em) end
        em:Hide()
        bt.__em = em
        bt:SetScript("OnClick", function()
            if bt.__mode == "loot" and bt.__key == "__typeMenu" then
                DG.OpenLootTypeMenu(bt)
            elseif bt.__mode == "quest" then
                if bt.__key == "A" or bt.__key == "H" then
                    U:SetQuestSide(bt.__key)
                elseif bt.__key == "qov" then
                    U.dungeonQView = "overview"
                    U:RenderDungeonQuests()
                elseif bt.__key == "qlist" then
                    U.dungeonQView = "list"
                    U:RenderDungeonQuests()
                else
                    U:SetQuestFilter(bt.__key)
                end
            else
                U:SetDungeonFilter(bt.__key)
            end
            ns.PlaySound(1)
        end)
        U.dungeonFilterBtns[i] = bt
    end
    if not U.dungeonQDoneTg then
        local tg = CreateFrame("CheckButton", nil, detail)
        tg:SetSize(36, 20)
        tg:EnableMouse(true)
        if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
        tg.label = MakeFS(tg, 14, C_TEXT, "RIGHT")
        tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)
        tg.label:SetText(L["已完成"])
        tg:SetHitRectInsets(-((tg.label:GetStringWidth() or 60) + 6), 0, 0, 0)
        tg:Hide()
        tg:SetScript("OnClick", function(self)
            U:SetQuestShowDone(self:GetChecked() and true or false)
        end)
        U.dungeonQDoneTg = tg
    end
    if not U.dungeonQuestPinTg then
        local tg = CreateFrame("CheckButton", nil, detail)
        tg:SetSize(36, 20)
        tg:EnableMouse(true)
        if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
        tg.label = MakeFS(tg, 14, C_TEXT, "RIGHT")
        tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)
        tg.label:SetText(L["地图图钉"])
        tg:SetHitRectInsets(-((tg.label:GetStringWidth() or 60) + 6), 0, 0, 0)
        tg:SetChecked(DB().mapQuestPins ~= false)
        tg:SetScript("OnClick", function(self)
            local s = DB()
            s.mapQuestPins = self:GetChecked() and true or false
            self:SetChecked(s.mapQuestPins ~= false)
            if ns.MapModule and ns.MapModule.SyncPins then ns.MapModule.SyncPins() end
            if ns.MapModule and ns.MapModule.SyncWorldQuestPins then ns.MapModule.SyncWorldQuestPins() end
        end)
        tg:Hide()
        U.dungeonQuestPinTg = tg
    end
    if not U.dungeonQuestPinCfg then
        local bt = CreateFrame("Button", nil, detail)
        bt:SetSize(16, 16)
        bt:EnableMouse(true)
        bt.tex = bt:CreateTexture(nil, "ARTWORK")
        bt.tex:SetSize(14, 14)
        bt.tex:SetPoint("CENTER")
        bt.tex:SetTexture(ns.SET_ICON or "Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings")
        bt.SyncIconState = function(self)
            local open = (ns.MapModule and ns.MapModule.QuestPinPanel and ns.MapModule.QuestPinPanel()) and true or false
            if open then
                self.tex:SetVertexColor(1, 0.82, 0)
            elseif self.hot then
                self.tex:SetVertexColor(1, 1, 1)
            else
                self.tex:SetVertexColor(0.62, 0.62, 0.62)
            end
        end
        bt:SetScript("OnEnter", function(self)
            if GameTooltip then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:AddLine(L["图钉设置"], 1, 0.82, 0)
                GameTooltip:Show()
            end
            self.hot = true
            self:SyncIconState()
        end)
        bt:SetScript("OnLeave", function(self)
            if GameTooltip then GameTooltip:Hide() end
            self.hot = nil
            self:SyncIconState()
        end)
        bt:SetScript("OnClick", function()
            ns.PlaySound(1)
            if ns.MapModule and ns.MapModule.ToggleQuestPinPanel then
                ns.MapModule.ToggleQuestPinPanel()
            end
            if U.dungeonQuestPinCfg then U.dungeonQuestPinCfg:SyncIconState() end
        end)
        bt:Hide()
        U.dungeonQuestPinCfg = bt
    end
    DG.RefreshFilterRow()
    DG.ApplyDetailChrome(U.dungeonTab or "loot")
end

function DG.BuildDetailLootView()
    local detail = U.dungeonDetail
    if not detail then return end
    if next(U.dungeonLootViewBtns or {}) then return end

    for vi = 1, 2 do
        local vk = (vi == 1) and "list" or "card"
        local bt = NewButton(detail, (vk == "list") and L["列表"] or L["卡片"],
                             DG.LOOT_VIEW_W, 24, 14)
        bt:SetPoint("TOPLEFT", detail, "TOPLEFT",
                    DG.LOOT_VIEW_X + (vi - 1) * (DG.LOOT_VIEW_W + DG.LOOT_VIEW_GAP), -DG.FILTER_Y)
        bt.__lootView = vk
        bt.__mode = "lootview"
        bt:SetScript("OnClick", function() U:SetLootView(vk) end)
        U.dungeonLootViewBtns[vi] = bt
    end
    if not U.dungeonLootBossDd then
        local dd = NewButton(detail, "", DG.LOOT_BOSS_W, 24, 14)
        dd:SetPoint("TOPLEFT", detail, "TOPLEFT", DG.LOOT_BOSS_X, -DG.FILTER_Y)
        dd:SetScript("OnClick", function() DG.OpenLootBossMenu(dd) end)
        U.dungeonLootBossDd = dd
    end
    DG.ApplyLootDropdownChrome()
    DG.ApplyDetailChrome(U.dungeonTab or "loot")
end

function DG.EnsureOverviewBuilt()
    if U.overviewBuilt then return end
    if not U.dungeonOverviewChild then return end
    U.overviewBuilt = true
    DG.BuildDungeonOverview()
end

function DG.PaintCurrentLevel()
    local ov, line, tag = U.dungeonCurOverlay, U.dungeonCurLine, U.dungeonCurTag
    if not (ov and line and tag) then return end
    local lv = UnitLevel("player") or 0
    if lv < DG.LO or lv > DG.HI then
        ov:Hide()
        return
    end
    ov:Show()
    local mx = DG.X(lv)
    line:ClearAllPoints()
    line:SetPoint("TOPLEFT", ov, "TOPLEFT", mx, -(U.dungeonGridTop or 0))
    tag:ClearAllPoints()
    tag:SetPoint("CENTER", ov, "TOPLEFT", mx, -(DG.CUR_H / 2))
    tag:SetText(format(L["当前等级 %d"], lv))
end

function DG.BuildDungeonOverview()
    local data = ns.DungeonData
    local child = U.dungeonOverviewChild
    if not (child and data and data.dungeons) then return end

    local places, lanes = DG.Pack(data.dungeons)

    local yRow = DG.CUR_H + DG.TICK_H + 4
    local totalH = yRow + lanes * DG.LANE_H + DG.BOT_PAD
    child:SetHeight(totalH)

    local gridTop = DG.CUR_H + DG.TICK_H - 4
    U.dungeonGridTop = gridTop
    for _, lv in ipairs(DG.TICKS) do
        local gx = DG.X(lv)
        local ln = child:CreateTexture(nil, "BACKGROUND")
        ln:SetWidth(1)
        ln:SetHeight(totalH - gridTop)
        ln:SetPoint("TOPLEFT", child, "TOPLEFT", gx, -gridTop)
        ln:SetColorTexture(1, 1, 1, 0.06)
        local fs = MakeFS(child, 14, C_GREY, "CENTER")
        fs:SetPoint("CENTER", child, "TOPLEFT", gx, -(DG.CUR_H + DG.TICK_H / 2))
        fs:SetText(tostring(lv))
    end

    local function drawBar(p)
        local d = p.d
        local bar = CreateFrame("Button", nil, child, "BackdropTemplate")
        bar:SetSize(p.x2 - p.x1, DG.BAR_H)
        bar:SetPoint("TOPLEFT", child, "TOPLEFT", p.x1, -(yRow + (p.lane - 1) * DG.LANE_H))
        bar:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        bar:SetBackdropColor(0, 0, 0, 0)
        local edge = d.isNew and DG.NEW_EDGE or DG.OLD_EDGE
        bar:SetBackdropBorderColor(edge[1], edge[2], edge[3], 0.90)

        local art = bar:CreateTexture(nil, "BACKGROUND")
        art:SetAllPoints()
        DG.PaintArt(art, d, "wide")
        local dim = bar:CreateTexture(nil, "ARTWORK")
        dim:SetAllPoints()
        dim:SetColorTexture(0, 0, 0, d.isNew and 0.42 or 0.52)

        local nm = MakeFS(bar, 14, C_WHITE, "LEFT")
        nm:SetPoint("TOPLEFT", bar, "TOPLEFT", 7, -4)
        nm:SetWordWrap(false)
        nm:SetText(d.name)
        local barW = p.x2 - p.x1
        local nameW = nm:GetStringWidth()
        if type(nameW) ~= "number" or nameW <= 0 then nameW = (#d.name / 3) * 12 end
        if not d.isNew then
            nm:SetPoint("RIGHT", bar, "RIGHT", -4, 0)
        else
            local badge = MakeFS(bar, 14, { 0.42, 0.94, 0.62 }, "LEFT")
            badge:SetText(L["新"])
            if nameW + 14 <= barW - 14 then
                badge:SetPoint("LEFT", nm, "RIGHT", 4, 0)
            else
                nm:SetPoint("RIGHT", bar, "RIGHT", -18, 0)
                badge:SetPoint("RIGHT", bar, "RIGHT", -4, 0)
            end
        end
        local lv = MakeFS(bar, 14, C_GREY, "LEFT")
        lv:SetPoint("BOTTOMLEFT", bar, "BOTTOMLEFT", 7, 4)
        lv:SetText(d.levelMin .. "–" .. d.levelMax .. (d.bossCount and (" · BOSS " .. d.bossCount) or ""))

        SetTip(bar, d.name .. "  " .. d.nameEn .. "\n" ..
            format(L["等级 %d–%d · %s"], d.levelMin, d.levelMax, d.zone or L["位置未知"]))
        bar:SetScript("OnClick", function()
            U:SetDungeonView("list")
            U:ShowDungeonDetail(d)
            ns.PlaySound(1)
        end)
    end

    for _, p in ipairs(places) do drawBar(p) end

    local ov = CreateFrame("Frame", nil, child)
    ov:SetAllPoints(child)
    ov:EnableMouse(false)
    ov:SetFrameLevel((child:GetFrameLevel() or 1) + 30)
    U.dungeonCurOverlay = ov
    U.dungeonCurLine = ov:CreateTexture(nil, "ARTWORK")
    U.dungeonCurLine:SetWidth(1)
    U.dungeonCurLine:SetHeight(totalH - gridTop)
    U.dungeonCurLine:SetColorTexture(C_GOLD[1], C_GOLD[2], C_GOLD[3], 0.60)
    U.dungeonCurTag = MakeFS(ov, 14, C_GOLD, "CENTER")
    DG.PaintCurrentLevel()
end

function U:SetDungeonView(view)
    local v = (view == "overview") and "overview" or "list"
    local changed = (v ~= U.dungeonView)
    U.dungeonView = v
    DB().dungeonView = v
    if changed and U.dungeonDetail then U.dungeonDetail:Hide() end
    U:UpdateDungeons()
end

function U:UpdateDungeons()
    if not U.dungeonBuilt then return end
    local view = "list"
    local lv = UnitLevel("player") or 0
    local isOverview = (view == "overview")
    if isOverview then DG.EnsureOverviewBuilt() end
    if U.dungeonOverviewScroll then U.dungeonOverviewScroll:SetShown(isOverview) end
    if isOverview then
        DG.PaintCurrentLevel()
        if U.dungeonListScroll then U.dungeonListScroll:Hide() end
        if U.dungeonListCard then U.dungeonListCard:Hide() end
        DG.ListFadesVisible(false)
        if U.dungeonDetail then U.dungeonDetail:Hide() end
    else
        local detailOpen = (U.dungeonDetail and U.dungeonDetail:IsShown()) or false
        if U.dungeonListCard then U.dungeonListCard:SetShown(not detailOpen) end
        if U.dungeonListScroll then
            U.dungeonListScroll:SetShown(not detailOpen)
            DG.ListFadesVisible(not detailOpen)
            if (U.dungeonListLevel or -1) ~= lv then
                DG.BuildList()
            end
            U.dungeonListScroll:SetVerticalScroll(0)
            DG.CullListRows()
        end
    end
end

DG.LOOT_COLS = 4
DG.LOOT_GAP_X = 8
DG.LOOT_GAP_Y = 8
DG.LOOT_CARD_H = 44
DG.LOOT_PAD_X = 6
DG.LOOT_ICON = 32
DG.LOOT_ICON_GAP = 5
DG.LOOT_TEXT_R = 30
DG.LOOT_TAG_W = 50
DG.LOOT_FS_NAME = 14
DG.LOOT_FS_META = 14
DG.LOOT_FS_SUB = 12
DG.LOOT_FS_TAG = 14
DG.LOOT_FS_HDR = 14
DG.LOOT_HDR_H = 24
DG.LOOT_GRP_GAP = 8
DG.LOOT_CARD_BG, DG.LOOT_CARD_EDGE = 0.03, 0.05
DG.LOOT_CARD_BG_HOVER, DG.LOOT_CARD_EDGE_HOVER = 0.09, 0.18
DG.LOOT_ROW_HOVER = 0.06
DG.LOOT_CARD_W = math.floor((DG.CHILD_W - (DG.LOOT_COLS - 1) * DG.LOOT_GAP_X) / DG.LOOT_COLS)

DG.LOOT_VIEW_W = 60
DG.LOOT_VIEW_GAP = 8
DG.LOOT_BOSS_W = 150
DG.LOOT_BOSS_X = DG.LOOT_BOSS_W + DG.GUTTER
DG.LOOT_VIEW_X = DG.LOOT_BOSS_X + DG.LOOT_BOSS_W + DG.GUTTER
DG.LOOT_DD_TEXT_W = 140
DG.LOOT_CARD_PAD = 6
DG.LOOT_CARD_ARROW = 14
DG.LOOT_CARD_ROW_GAP = 4
DG.LOOT_CARD_NAME_R = 52
DG.LOOT_CARD_HDR_H = DG.LOOT_HDR_H
DG.LOOT_CARD_MIN_H = DG.LOOT_CARD_HDR_H + DG.LOOT_CARD_PAD

DG.LOOT_TRASH = "__trash"
DG.LOOT_TRASH_LABEL = L["小怪"]

DG.LOOT_COLS3 = 3
DG.LOOT_MODEL_W = 160
DG.LOOT_MODEL_H = 256
DG.LOOT_CARD_W3 = math.floor((DG.CHILD_W - DG.LOOT_MODEL_W - DG.LOOT_COLS3 * DG.LOOT_GAP_X) / DG.LOOT_COLS3)
DG.LOOT_MODEL_X = DG.CHILD_W - DG.LOOT_MODEL_W

DG.GUIDE_COLS, DG.GUIDE_GAP_X, DG.GUIDE_GAP_Y = 2, 8, 8
DG.GUIDE_PAD, DG.GUIDE_HDR_H = 10, 26
DG.GUIDE_SIDE = 0
DG.GUIDE_GRID_W = CONTENT_W - PAGE_INSET * 2 - DG.GUIDE_SIDE * 2
DG.GUIDE_CARD_W = math.floor((DG.GUIDE_GRID_W - (DG.GUIDE_COLS - 1) * DG.GUIDE_GAP_X) / DG.GUIDE_COLS)
DG.GUIDE_ACCENT = {
    { 0.42, 0.72, 0.94 },
    { 0.19, 0.62, 0.47 },
    { 0.85, 0.65, 0.13 },
    { 0.78, 0.45, 0.42 },
}
DG.FILTERS = { "all", "weapon", "armor", "quest", "new" }
DG.FILTER_LABEL = {
    all = L["全部"], weapon = L["武器"], armor = L["护甲"],
    quest = L["任务物品"], new = L["仅新增"],
}
DG.FILTER_MAX = 5

DG.QUALTAB = {
    { 0.62, 0.62, 0.62 },
    { 1.00, 1.00, 1.00 },
    { 0.12, 1.00, 0.00 },
    { 0.00, 0.44, 0.87 },
    { 0.64, 0.21, 0.93 },
    { 1.00, 0.50, 0.00 },
}
function DG.QColor(q)
    local t = ITEM_QUALITY_COLORS and ITEM_QUALITY_COLORS[q or 1]
    if t and t.r then return t.r, t.g, t.b end
    local d = DG.QUALTAB[(q or 1) + 1] or DG.QUALTAB[1]
    return d[1], d[2], d[3]
end
function DG.ItemInfo(id)
    if id == nil then return nil end
    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(fn) ~= "function" then return nil end
    return fn(id)
end
function DG.ItemInfoInstant(id)
    if id == nil then return nil end
    local fn = GetItemInfoInstant or (C_Item and C_Item.GetItemInfoInstant)
    if type(fn) ~= "function" then return nil end
    return fn(id)
end
function DG.ItemApiName()
    if type(GetItemInfo) == "function" then return "GetItemInfo（全局）" end
    if C_Item and type(C_Item.GetItemInfo) == "function" then return "C_Item.GetItemInfo（命名空间）" end
    return nil
end

function DG.QualOf(id)
    if id then
        local _, _, q = DG.ItemInfo(id)
        if type(q) == "number" then return q end
        q = DG.NsCall("GetItemQualityByID", id)
        if type(q) == "number" then return q end
    end
    return nil
end

function DG.NsCall(name, id)
    if id == nil then return nil end
    local fn = C_Item and C_Item[name]
    if type(fn) ~= "function" then return nil end
    local ok, v = pcall(fn, id)
    if ok then return v end
    return nil
end

function DG.ContinueOnItemLoad(id, cb)
    local mk = _G.Item and _G.Item.CreateFromItemID
    if id == nil or type(mk) ~= "function" then return false end
    local ok, item = pcall(mk, _G.Item, id)
    if not ok or not item then return false end
    local ok2 = pcall(item.ContinueOnItemLoad, item, cb)
    return ok2 and true or false
end

function DG.RefreshItemCards(itemID)
    if not itemID then return end
    local q = DG.__rcQ
    if not q then q = {} DG.__rcQ = q end
    q[itemID] = true
    if DG.__rcT then return end
    DG.__rcT = C_Timer.NewTimer(0.1, function()
        DG.__rcT = nil
        local qq = DG.__rcQ
        DG.__rcQ = nil
        if not qq then return end
        for id in pairs(qq) do DG.FlushItemCards(id) end
        if DG.__fcPending then DG.FlushPendingItems() end
    end)
end

function DG.HarvestTipName(id)
    if not id then return nil end
    local cache = DG.__tipName
    local hit = cache and cache[id]
    if hit then
        if hit[2] then DG.__tipColor = { hit[2], hit[3], hit[4] } end
        return hit[1]
    end
    if DG.__tipDead and DG.__tipDead[id] then return nil end
    if DungeonsForeverDB and DungeonsForeverDB.dfNoTipWarm then return nil end
    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    local nm, _, _, q
    if fn then nm, _, _, q = fn(id) end
    if type(nm) == "string" and nm ~= "" then
        local r, g, b
        if type(q) == "number" and GetItemQualityColor then r, g, b = GetItemQualityColor(q) end
        if not cache then cache = {} DG.__tipName = cache end
        cache[id] = { nm, r, g, b }
        DG.__tipCapN = (DG.__tipCapN or 0) + 1
        if DG.__tipCapN > 3000 then
            for k in pairs(cache) do cache[k] = nil end
            DG.__tipCapN = 0
            cache[id] = { nm, r, g, b }
        end
        if r then DG.__tipColor = { r, g, b } end
        return nm
    end
    if not (DG.__asked and DG.__asked[id]) then DG.RequestItem(id) end
    return nil
end

function DG.FlushItemCards(itemID)
    local df = debugprofilestop
    local now = type(df) == "function" and df() or nil
    local last = DG.__rcLast
    if not last then last = {} DG.__rcLast = last end
    local waitMap = DG.__rcWait
    if not waitMap then waitMap = {} DG.__rcWait = waitMap end
    local wait = waitMap[itemID] or 0
    if now and now - (last[itemID] or 0) < wait * 1000 then return end
    if now then last[itemID] = now end
    local pend = DG.__fcPending
    if not pend then pend = {} DG.__fcPending = pend end
    pend[itemID] = true
    if not DG.__fcT then
        DG.__fcT = true
        if C_Timer and C_Timer.NewTimer then
            C_Timer.NewTimer(0, function()
                DG.__fcT = nil
                DG.FlushPendingItems()
            end)
        else
            DG.__fcT = nil
            DG.FlushPendingItems()
        end
    end
end

function DG.BroadcastItemData(itemID)
    local PVM = ns.PvPModule
    if PVM and PVM.OnItemData then PVM.OnItemData(itemID) end
    local EGM = ns.ExploreModule
    if EGM and EGM.OnItemData then EGM.OnItemData(itemID) end
    local CGM = ns.CollectionModule
    if CGM and CGM.OnItemData then CGM.OnItemData(itemID) end
    local FCM = ns.FactionModule
    if FCM and FCM.OnItemData then FCM.OnItemData(itemID) end
    local BM = ns.BisModule
    if BM and BM.OnItemData then BM.OnItemData(itemID) end
    local CQM = ns.ClassQuestUI
    if CQM and CQM.OnItemData then CQM.OnItemData(itemID) end
    local MM = ns.MapModule
    if MM and MM.OnItemData then MM.OnItemData(itemID) end
    local PM = ns.ProfModule
    if PM and PM.OnItemData then PM.OnItemData(itemID) end
end

function DG.FlushPendingItems()
    local pend = DG.__fcPending
    DG.__fcPending = nil
    if not pend then return end
    local LF = ns.LootFilter
    local waitMap = DG.__rcWait
    for id in pairs(pend) do
        if LF then LF.Invalidate(id) end
        DG.BroadcastItemData(id)
        if waitMap then
            local _, hasName = DG.ItemName(id)
            if hasName then
                waitMap[id] = 1
            else
                local w = waitMap[id] or 1
                waitMap[id] = math.min((w > 1 and w or 1) * 2, 60)
            end
        end
    end
    DG.PoolApplyItems(pend)
end

function DG.PoolApplyItems(ids)
    local LF = ns.LootFilter
    local pool = U.dungeonDetailPool and U.dungeonDetailPool.item
    if pool then
        for i = 1, #pool do
            local c = pool[i]
            local it = c and c.__it
            local iid = it and it[1]
            if iid and ids[iid] then
                DG.PaintItemRow(c, iid)
                if LF and LF.Apply then LF.Apply(c) end
            end
        end
    end
    local qpool = U.dungeonQDetPool and U.dungeonQDetPool.chip
    if qpool then
        for i = 1, #qpool do
            local c = qpool[i]
            local it = c and c.__it
            local iid = it and it[1]
            if iid and ids[iid] then
                DG.PaintItemChip(c, iid)
            end
        end
    end
end

function DG.FlushItemCardsNow(itemID)
    local LF = ns.LootFilter
    if LF then LF.Invalidate(itemID) end
    DG.BroadcastItemData(itemID)
    DG.PoolApplyItems({ [itemID] = true })
end

function DG.PaintItemRow(c, itemID)
    if not (c and itemID) then return end
    if c.name then
        local nm, hasName = DG.ItemName(itemID)
        c.name:SetText(nm)
        if hasName then
            c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))
        else
            c.name:SetTextColor(Unpack(C_GREY))
        end
        c.__named = hasName
    end
    if c.icon and c.icon.SetTexture then
        c.icon:SetTexture(DG.ItemIcon(itemID))
        if ns.hui and ns.hui.SetIconRing then
            ns.hui.SetIconRing(c.icon, { ns.hui.QColor(DG.QualOf(itemID)) })
        end
    end
    if c.tp then c.tp:SetText(DG.ItemMeta(itemID)) end
end

function DG.PaintItemChip(c, itemID)
    if not (c and c.name and itemID) then return end
    local nm, hasName = DG.ItemName(itemID)
    c.name:SetText(nm)
    if hasName then
        local qr, qg, qb = DG.QColor(DG.QualOf(itemID))
        if qr then
            c.name:SetTextColor(qr, qg, qb)
        else
            c.name:SetTextColor(Unpack(C_TEXT))
        end
    else
        c.name:SetTextColor(Unpack(C_GREY))
    end
    c.__named = hasName
end

function DG.ItemName(id)
    if id then
        local nm = DG.ItemInfo(id)
        if type(nm) == "string" and nm ~= "" then return nm, true end
        nm = DG.NsCall("GetItemNameByID", id)
        if type(nm) == "string" and nm ~= "" then return nm, true end
    end
    return L["暂时没有客户端数据"], false
end

function DG.Pct(v)
    if type(v) ~= "number" then return nil end
    if v >= 10 then return format("%d%%", math.floor(v + 0.5)) end
    return tostring(v) .. "%"
end

function DG.ItemLink(id)
    if id == nil then return nil end
    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(fn) == "function" then
        local ok, _, link = pcall(fn, id)
        if ok and type(link) == "string" and link ~= "" then return link end
    end
    return "item:" .. tostring(id) .. ":0:0:0:0:0:0:0"
end

function DG.InsertItemLink(id)
    local link = DG.ItemLink(id)
    if link == nil then return false end
    if type(ChatEdit_GetActiveWindow) == "function"
       and type(ChatEdit_InsertLink) == "function"
       and ChatEdit_GetActiveWindow() then
        ChatEdit_InsertLink(link)
        return true
    end
    if type(ChatFrame_OpenChat) == "function" then
        ChatFrame_OpenChat(link)
        return true
    end
    return false
end

function DG.TryOn(id)
    if id == nil then return false end
    if type(DressUpItemLink) ~= "function" then return false end
    local link = DG.ItemLink(id)
    if link == nil then return false end
    DressUpItemLink(link)
    return true
end

function DG.ItemShiftClick(row, button)
    if button ~= "LeftButton" then return false end
    local it = row and row.__it
    if it == nil then return false end
    if type(it) ~= "table" then it = { it } end
    if type(IsShiftKeyDown) == "function" and IsShiftKeyDown() then
        return DG.InsertItemLink(it[1])
    end
    if type(IsControlKeyDown) == "function" and IsControlKeyDown() then
        return DG.TryOn(it[1])
    end
    return false
end

function DG.Hex(c)
    return format("|cff%02x%02x%02x",
        math.floor(c[1] * 255 + 0.5), math.floor(c[2] * 255 + 0.5), math.floor(c[3] * 255 + 0.5))
end

DG.CAT_BY_CLASS = { [2] = "weapon", [6] = "weapon", [4] = "armor", [12] = "quest" }
function DG.CatOf(id)
    local _, _, _, _, _, classID = DG.ItemInfoInstant(id)
    return DG.CAT_BY_CLASS[classID] or "other"
end

function DG.ItemIcon(id)
    local tex = select(10, DG.ItemInfo(id))
    if type(tex) ~= "string" or tex == "" then
        local ic = select(5, DG.ItemInfoInstant(id))
        if type(ic) == "string" or type(ic) == "number" then tex = ic end
    end
    if type(tex) == "string" and tex ~= "" then return tex end
    if type(tex) == "number" then return tex end
    return FALLBACK_ICON
end

function DG.ItemMeta(id)
    local _, _, subType, loc, _, _, subID = DG.ItemInfoInstant(id)
    local a
    if type(loc) == "string" then
        a = _G[loc]
        if type(a) ~= "string" and loc:sub(1, 8) ~= "INVTYPE_" then a = loc end
    end
    if type(a) ~= "string" or a == "" then return "" end
    if type(subID) == "number" and subID ~= 0
        and type(subType) == "string" and subType ~= "" then
        return a .. " · " .. subType
    end
    return a
end

function DG.LootTypeKey(id)
    local m = DG.ItemMeta(id)
    if type(m) ~= "string" or m == "" then return L["其它"] end
    local b = m:match("^(.-) · (.+)$")
    if type(b) == "string" and b ~= "" then return b end
    return m
end

DG.__asked = {}
DG.__qAsked = {}
function DG.RequestItem(id, force)
    if type(id) ~= "number" or id < 1 or id > 2147483647 or id ~= math.floor(id) then return end
    if DG.__asked[id] and not force then return end
    DG.__asked[id] = true
    DG.__askedN = (DG.__askedN or 0) + 1
    if DG.__askedN > 4000 then
        for k in pairs(DG.__asked) do DG.__asked[k] = nil end
        DG.__askedN = 0
        DG.__asked[id] = true
    end
    DG.EnsureItemListener()
    if C_Item and C_Item.RequestLoadItemDataByID then
        pcall(C_Item.RequestLoadItemDataByID, id)
    end
    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(fn) == "function" then pcall(fn, id) end
    DG.ContinueOnItemLoad(id, function() DG.RefreshItemCards(id) end)
end

function DG.EnsureItemListener()
    if DG.__itemEvt then return end
    local ev = CreateFrame("Frame")
    ev:RegisterEvent("GET_ITEM_INFO_RECEIVED")
    pcall(ev.RegisterEvent, ev, "ITEM_DATA_LOAD_RESULT")
    pcall(ev.RegisterEvent, ev, "PLAYER_ENTERING_WORLD")
    ev:SetScript("OnEvent", function(_, event, itemID, success)
        if event == "PLAYER_ENTERING_WORLD" then
            DG.__tipDead = nil
            return
        end
        if success == false then return end
        if not (itemID and DG.__asked[itemID]) then return end
        if DG.__tipDead then DG.__tipDead[itemID] = nil end
        C_Timer.After(0, function()
            local r = U.dungeonDetailHover
            if r and r.__it and r.__it[1] == itemID and r:IsMouseOver()
               and r.__tipReshown ~= itemID then
                r.__tipReshown = itemID
                DG.ShowItemTip(r, r.__it)
            end
            local pr = ns.ProfModule and ns.ProfModule.hoverRow
            if pr and pr.__it and pr.__it[1] == itemID and pr:IsMouseOver()
               and pr.__tipReshown ~= itemID then
                pr.__tipReshown = itemID
                DG.ShowItemTip(pr, pr.__it)
            end
            DG.RefreshItemCards(itemID)
        end)
    end)
    DG.__itemEvt = ev
end

function DG.PrewarmLoot(d)
    if not d then return end
    local loot = (ns.DungeonLoot or {})[d.id]
    if not loot then return end
    DG.EnsureItemListener()
    local list, n = {}, 0
    for _, s in ipairs(loot) do
        local its = s[5]
        for k = 1, #(its or {}) do
            n = n + 1
            list[n] = its[k]
        end
    end
    local i = 1
    local function warmChunk()
        local stop = i + DG.ITEM_WARM_CHUNK - 1
        if stop > n then stop = n end
        for k = i, stop do
            local it = list[k]
            local _, hasName = DG.ItemName(it[1])
            DG.RequestItem(it[1], not hasName)
        end
        i = stop + 1
        if i <= n then DG.PushStep(warmChunk) end
    end
    if n > 0 then
        DG.PushStep(warmChunk)
        DG.RunSteps()
    end
    DG.ScheduleNameSweep()
end

DG.ITEM_WARM_CHUNK = 6

DG.SWEEP_AT = { 0.5, 1.5, 4, 9 }

function DG.SweepMissingNames()
    local LF = ns.LootFilter
    local left = DG.ITEM_WARM_CHUNK * 2
    local more = false
    local named = 0
    local pool = U.dungeonDetailPool and U.dungeonDetailPool.item
    if pool then
        for i = 1, #pool do
            local c = pool[i]
            local it = c and c.__it
            if it and not c.__named then
                if DG.__tipDead and DG.__tipDead[it[1]] then
                    c.__named = true
                else
                DG.PaintItemRow(c, it[1])
                if LF then LF.Invalidate(it[1]) end
                if not c.__named and DG.HarvestTipName then
                    if left <= 0 then
                        more = true
                    else
                        left = left - 1
                        local nm = DG.HarvestTipName(it[1])
                        if nm and c.name then
                            c.name:SetText(nm)
                            local col = DG.__tipColor
                            if col then
                                c.name:SetTextColor(col[1] or 1, col[2] or 1, col[3] or 1)
                                DG.__tipColor = nil
                            else
                                c.name:SetTextColor(Unpack(C_GREY))
                            end
                            c.__named = true
                            named = named + 1
                        end
                    end
                end
                end
            end
        end
    end
    local qpool = U.dungeonQDetPool and U.dungeonQDetPool.chip
    local needQRender = false
    if qpool then
        for i = 1, #qpool do
            local c = qpool[i]
            local it = c and c.__it
            if it and not c.__named then
                DG.PaintItemChip(c, it[1])
                if LF then LF.Invalidate(it[1]) end
                if not c.__named and DG.HarvestTipName then
                    if left <= 0 then
                        more = true
                    else
                        left = left - 1
                        local nm = DG.HarvestTipName(it[1])
                        if nm and c.name then
                            c.name:SetText(nm)
                            local col = DG.__tipColor
                            if col then
                                c.name:SetTextColor(col[1] or 1, col[2] or 1, col[3] or 1)
                                DG.__tipColor = nil
                            else
                                c.name:SetTextColor(Unpack(C_GREY))
                            end
                            c.__named = true
                            named = named + 1
                            DG.ApplyChipBadge(c)
                            if c.__q then needQRender = true end
                        end
                    end
                end
            end
        end
    end
    if more then
        if named > 0 then
            DG.__sweepStall = 0
            DG.PushStep(DG.SweepMissingNames)
            DG.RunSteps()
            return
        end
        local stall = (DG.__sweepStall or 0) + 1
        DG.__sweepStall = stall
        if stall >= 2 then return end
        DG.PushStep(DG.SweepMissingNames)
        DG.RunSteps()
        return
    end
    DG.__sweepStall = 0
    if needQRender and U.RenderQuestDetail and U.dungeonQDet
       and U.dungeonQDet.IsShown and U.dungeonQDet:IsShown() then
        U:RenderQuestDetail()
    end
    if LF then LF.ApplyAll() end
end

function DG.ScheduleNameSweep()
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    DG.__sweepStall = 0
    for _, t in ipairs(DG.SWEEP_AT) do
        C_Timer.After(t, function() DG.SweepMissingNames() end)
    end
end

function DG.ShowItemTip(owner, it, extra, title)
    if DG.__tipBusy then return end
    DG.__tipBusy = true
    local ok, err = pcall(DG.ShowItemTipBody, owner, it, extra, title)
    DG.__tipBusy = nil
    if not ok then error(err, 0) end
    if C_Timer and C_Timer.After then
        C_Timer.After(0, function()
            if GameTooltip:IsShown() then GameTooltip:Show() end
        end)
    end
end

function DG.TipAppendLines(lines)
    if type(lines) ~= "table" or #lines == 0 then return end
    local T = ns.TipLines
    if T and T.Append then
        T.Append(GameTooltip, lines)
        return
    end
    GameTooltip:AddLine(" ")
    for _, ln in ipairs(lines) do
        if type(ln) == "table" and type(ln[1]) == "string" then
            GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
        end
    end
end

function DG.TipAppendMerged(a, b)
    if not a then DG.TipAppendLines(b) return end
    if not b then DG.TipAppendLines(a) return end
    local m = {}
    for _, ln in ipairs(a) do m[#m + 1] = ln end
    for _, ln in ipairs(b) do m[#m + 1] = ln end
    DG.TipAppendLines(m)
end

function DG.ShowItemTipBody(owner, it, extra, title)
    local id = it[1]
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()

    local native = false
    local cached = false
    if id then
        local info = DG.ItemInfo(id)
        cached = (type(info) == "string" and info ~= "")
    end
    if id and cached and GameTooltip.SetHyperlink then
        local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, "item:" .. tostring(id))
        if ns.hui and ns.hui.MarkTipItem then ns.hui.MarkTipItem(GameTooltip, true) end
        if ok then
            GameTooltip:Show()
            local n = GameTooltip.NumLines and GameTooltip:NumLines() or 0
            native = (type(n) == "number" and n > 1)
        end
    end
    if not native and id then DG.RequestItem(id) end

    if native then
        if ns.hui and ns.hui.MarkTipItem then ns.hui.MarkTipItem(GameTooltip, true) end
        local tl = ns.TipLines and ns.TipLines.Lines(id)
        DG.TipAppendMerged(extra, tl)
        if title then
            local l1 = _G["GameTooltipTextLeft1"]
            if l1 then l1:SetText(title) end
        end
        GameTooltip:Show()
        if ns.TipLines and ns.TipLines.InsertIlvl then
            pcall(ns.TipLines.InsertIlvl, GameTooltip, id)
        end
        return
    end

    GameTooltip:ClearLines()
    local nm, hasName = DG.ItemName(id)
    if title then
        GameTooltip:AddLine(title, 1, 0.82, 0, true)
    elseif hasName then
        local r, g, b = DG.QColor(DG.QualOf(id))
        GameTooltip:AddLine(nm, r, g, b, true)
    else
        local meta = id and DG.ItemMeta(id) or ""
        if meta ~= "" then
            GameTooltip:AddLine(meta, 0.85, 0.85, 0.85)
        else
            GameTooltip:AddLine(format(L["物品 #%d"], id or 0), 0.6, 0.6, 0.6)
        end
    end
    if id and DG.ItemInfoInstant(id) then
        GameTooltip:AddLine(L["客户端详细数据加载中，稍后自动刷新"], 0.5, 0.5, 0.5, true)
    else
        GameTooltip:AddLine(L["客户端未收录此物品"], 0.5, 0.5, 0.5, true)
    end
    local tl = ns.TipLines and ns.TipLines.Lines(id)
    DG.TipAppendMerged(extra, tl)
    GameTooltip:Show()
end

function DG.FitText(s, fs, maxw)
    if type(s) ~= "string" then return "" end
    local H = ns.hui
    if H and H.Fit and type(maxw) == "number" and maxw > 0 then
        return H.Fit(s, fs, maxw)
    end
    local PD = ns.ProfModule
    if PD and PD.Fit then return PD.Fit(s, fs, maxw) end
    return s
end
function DG.ClipTo(f, s, maxw)
    if type(s) ~= "string" or not f then return "" end
    f:SetText(s)
    if (f:GetStringWidth() or 0) <= maxw then return s end
    local step = ns.hui and ns.hui.CharStep
    if not step then return s end
    local n, i = #s, 1
    local starts = {}
    while i <= n do
        starts[#starts + 1] = i
        local _, st = step(s, i)
        i = i + st
    end
    for k = #starts, 1, -1 do
        local cand = s:sub(1, starts[k] - 1)
        f:SetText(cand)
        if (f:GetStringWidth() or 0) <= maxw then return cand end
    end
    f:SetText("")
    return ""
end

function U:SetDungeonFilter(key)
    U.dungeonFilter = key
    DB().dungeonFilter = key
    U:RenderDungeonLoot()
end

function DG.LootBossNames(loot)
    local seen, out = {}, {}
    for _, s in ipairs(loot or {}) do
        local nm = s[2]
        local note = s[3] or ""
        local special = note:find("敌人", 1, true) or note:find("物件", 1, true)
        if not special and type(nm) == "string" and nm ~= "" and not seen[nm] then
            seen[nm] = true
            out[#out + 1] = nm
        end
    end
    return out
end

function U:SetLootBoss(name)
    if name == "" then name = nil end
    U.dungeonLootBoss = name
    DB().dungeonLootBoss = name
    U:RenderDungeonLoot()
    ns.PlaySound(1)
end

function DG.OpenLootTypeMenu(owner)
    local items = {}
    for _, key in ipairs(DG.FILTERS) do
        items[#items + 1] = {
            text = (DG.FILTER_LABEL[key] or key) .. " " .. tostring(DG.__filterCounts and DG.__filterCounts[key] or 0),
            func = function() U:SetDungeonFilter(key) end,
        }
    end
    ns.hui.ShowMenu(items, { owner = owner })
end

function DG.OpenLootBossMenu(owner)
    local d = U.dungeonDetailCur
    if not d then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}
    local items = { { text = L["全部"], func = function() U:SetLootBoss(nil) end } }
    local hasTrash = false
    for _, s in ipairs(loot) do
        local note = s[3] or ""
        if note:find("敌人", 1, true) then hasTrash = true break end
    end
    if hasTrash then
        items[#items + 1] = { text = DG.LOOT_TRASH_LABEL,
                              func = function() U:SetLootBoss(DG.LOOT_TRASH) end }
    end
    for _, nm in ipairs(DG.LootBossNames(loot)) do
        items[#items + 1] = { text = nm, func = function() U:SetLootBoss(nm) end }
    end
    ns.hui.ShowMenu(items, { owner = owner })
end

function DG.ApplyLootDropdownChrome()
    local bossDd = U.dungeonLootBossDd
    if bossDd then
        local bossSel = U.dungeonLootBoss
        bossDd:SetShown((U.dungeonTab or "loot") == "loot")
        local bossShown = bossSel == DG.LOOT_TRASH and DG.LOOT_TRASH_LABEL or bossSel
        bossDd:SetText(L["BOSS："] .. DG.FitText(bossShown or L["全部"], 14, 112))
        ns.hui.SetButtonSelected(bossDd, bossSel ~= nil)
    end
    local bt1 = U.dungeonFilterBtns and U.dungeonFilterBtns[1]
    if bt1 and bt1.__mode == "loot" and bt1.__key == "__typeMenu" then
        local filter = U.dungeonFilter or "all"
        local lab = DG.FILTER_LABEL[filter] or filter
        if filter ~= "all" then
            lab = lab .. " " .. tostring(DG.__filterCounts and DG.__filterCounts[filter] or 0)
        end
        bt1:SetWidth(DG.LOOT_BOSS_W)
        bt1:SetText(DG.FitText(L["类型："] .. lab, 14, DG.LOOT_DD_TEXT_W))
        if bt1.__em then bt1.__em:Hide() end
        local bfs = bt1.GetFontString and bt1:GetFontString()
        if bfs then
            bfs:ClearAllPoints()
            bfs:SetPoint("CENTER", bt1, "CENTER", 0, 0)
            bfs:SetJustifyH("CENTER")
        end
        ns.hui.SetButtonSelected(bt1, filter ~= "all")
        if bfs then
            if filter ~= "all" then
                bfs:SetTextColor(1, 1, 1)
            else
                bfs:SetTextColor(Unpack(C_TEXT))
            end
        end
    end
end

function U:SetQuestFilter(key)
    local cur = U.dungeonQFilter or "all"
    U.dungeonQFilter = (key == cur) and "all" or key
    DB().dungeonQuestFilter = (U.dungeonQFilter ~= "all") and U.dungeonQFilter or nil
    U:RenderDungeonQuests()
end

function U:SetQuestShowDone(on)
    U.dungeonQFilter = on and "all" or "todo"
    DB().dungeonQuestFilter = (U.dungeonQFilter ~= "all") and U.dungeonQFilter or nil
    U:RenderDungeonQuests()
end

function U:SetQuestSide(key)
    local k = (key == "A" or key == "H") and key or nil
    U.dungeonQSide = k
    U:RenderDungeonQuests()
    ns.PlaySound(1)
end

function U:ShowDungeonDetail(d)
    if not U.dungeonBuilt then return end
    DG.EnsureDetailBuilt()
    local detail = U.dungeonDetail
    local child, pool = U.dungeonDetailChild, U.dungeonDetailPool
    if not (detail and U.dungeonDetailScroll and child and pool) then return end
    U.dungeonListScroll:Hide()
    if U.dungeonListCard then U.dungeonListCard:Hide() end
    DG.ListFadesVisible(false)
    detail:Show()
    local hero = U.dungeonDetailHero
    if hero then
        DG.PaintArt(hero.art, d, "hero")
        if hero.LayoutFade then hero.LayoutFade() end
    end
    U.dungeonDetailCur = d
    U.dungeonQFlow = nil
    U.dungeonQDetKey = nil
    U.dungeonQListKey = nil
    if U.dungeonBack then U.dungeonBack:SetText(d.raid and L["团本"] or L["副本"]) end
    DG.PrewarmLoot(d)

    local titleFs = U.dungeonDetailTitle
    local loc = (type(GetLocale) == "function" and GetLocale()) or "zhCN"
    local nameTxt = d.name
    if loc ~= "zhCN" and loc ~= "zhTW" then nameTxt = d.nameEn or d.name end
    local tail = "  |cff8b8b8b" .. format(L["等级 %d-%d"], d.levelMin, d.levelMax) .. "|r"
    titleFs:SetText(tail)
    local tailW = titleFs:GetStringWidth() or 0
    local room = DG.HERO_TITLE_MAXW - tailW - 10
    if room < 30 then room = 30 end
    local nm = DG.ClipTo(titleFs, nameTxt, room)
    if nm ~= nameTxt then
        if nm == "" then nm = "…" else nm = nm .. "…" end
    end
    titleFs:SetText(nm .. tail)
    DG.PaintEntChips(d)
    SetTip(U.dungeonDetailTipZone, d.isNew and L["新副本的 boss 名单来自 beta 客户端，标「新」的是无限版新增的物品；没有掉落数据的 boss 只列名字。"]
        or L["谁掉什么、掉率多少是经典旧世的数据。标「新」的是无限版新增的掉落；其余物品无限版的属性可能有改动，以正式版为准。"])

    U:RenderDungeonTab()
end

local function PaintWishStar(bt, id)
    local gm = ns.GearModule
    local on = gm and gm.WishIs and id and gm.WishIs(id)
    bt.star:SetText(on and "★" or "☆")
    if on then
        bt.star:SetTextColor(1, 0.82, 0, 1)
    else
        bt.star:SetTextColor(0.55, 0.58, 0.65, 1)
    end
end

function U:RenderDungeonLoot()
    local LF = ns.LootFilter
    local d = U.dungeonDetailCur
    local child, pool = U.dungeonDetailChild, U.dungeonDetailPool
    if not (d and child and pool) then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}
    if not DG.__chromeOnly then DG.__pendRows = {} DG.__vgen = (DG.__vgen or 0) + 1 end

    local bossSel = U.dungeonLootBoss or DB().dungeonLootBoss
    if bossSel == DG.LOOT_TRASH then
        local has = false
        for _, s in ipairs(loot) do
            local note = s[3] or ""
            if note:find("敌人", 1, true) then has = true break end
        end
        if not has then bossSel = nil end
    elseif bossSel then
        local seen = {}
        for _, nm in ipairs(DG.LootBossNames(loot)) do seen[nm] = true end
        if not seen[bossSel] then
            bossSel = nil
        end
    end
    U.dungeonLootBoss = bossSel
    DB().dungeonLootBoss = bossSel

    local srcs = loot
    if bossSel then
        srcs = {}
        for _, s in ipairs(loot) do
            if bossSel == DG.LOOT_TRASH then
                local note = s[3] or ""
                if note:find("敌人", 1, true) then srcs[#srcs + 1] = s end
            elseif s[2] == bossSel then
                srcs[#srcs + 1] = s
            end
        end
    end

    local counts = { all = 0, weapon = 0, armor = 0, quest = 0, new = 0 }
    for _, s in ipairs(srcs) do
        for _, it in ipairs(s[5]) do
            counts.all = counts.all + 1
            local cat = DG.CatOf(it[1])
            if counts[cat] then counts[cat] = counts[cat] + 1 end
            if it[3] then counts.new = counts.new + 1 end
        end
    end

    local filter = U.dungeonFilter or "all"
    if filter ~= "all" and (not counts[filter] or counts[filter] == 0) then
        filter = "all"
        U.dungeonFilter = "all"
        DB().dungeonFilter = "all"
    end
    DG.__filterCounts = counts
    for i, key in ipairs(DG.FILTERS) do
        local bt = U.dungeonFilterBtns and U.dungeonFilterBtns[i]
        if bt then
            bt.__mode = "loot"
            local sel
            if i == 1 then
                bt.__key = "__typeMenu"
                bt:SetShown(true)
                sel = (filter ~= "all")
            else
                bt.__key = key
                bt:SetShown(false)
                sel = false
            end
            ns.hui.SetButtonSelected(bt, sel)
        end
    end
    for i = #DG.FILTERS + 1, #(U.dungeonFilterBtns or {}) do
        U.dungeonFilterBtns[i]:Hide()
    end
    DG.ApplyLootDropdownChrome()
    if DG.__chromeOnly then return end

    local trashMode = bossSel == DG.LOOT_TRASH
    local bossMode = bossSel ~= nil and not trashMode
    local typeMode = bossMode or trashMode
    local bossEn, bossNpc
    local groups
    if typeMode then
        if bossMode then
            for _, s in ipairs(srcs) do
                if not bossEn and s[4] ~= "" then
                    bossEn, bossNpc = s[1], tonumber(s[4])
                end
            end
        end
        local byKey, tg = {}, {}
        for _, s in ipairs(srcs) do
            for _, it in ipairs(s[5]) do
                local cat = DG.CatOf(it[1])
                if filter == "all" or cat == filter or (filter == "new" and it[3]) then
                    local tk = DG.LootTypeKey(it[1])
                    local g = byKey[tk]
                    if not g then
                        g = { src = { "", tk, "", "", {} }, items = {} }
                        byKey[tk] = g
                        tg[#tg + 1] = g
                    end
                    g.items[#g.items + 1] = it
                end
            end
        end
        groups = tg
    else
        local named, special = {}, {}
        for _, s in ipairs(srcs) do
            local items = {}
            for _, it in ipairs(s[5]) do
                local cat = DG.CatOf(it[1])
                if filter == "all" or cat == filter or (filter == "new" and it[3]) then
                    items[#items + 1] = it
                end
            end
            local g = { src = s, items = items }
            if s[4] ~= "" then named[#named + 1] = g else special[#special + 1] = g end
        end
        groups = {}
        for _, g in ipairs(named) do groups[#groups + 1] = g end
        for _, g in ipairs(special) do groups[#groups + 1] = g end
    end

    local hdr, rows = pool.hdr, pool.item
    local nH, nI, y = 0, 0, 0
    local cols = DG.LOOT_COLS
    local cw = DG.LOOT_CARD_W
    local stepX, stepY = cw + DG.LOOT_GAP_X, DG.LOOT_CARD_H + DG.LOOT_GAP_Y
    local tx = DG.LOOT_PAD_X + DG.LOOT_ICON + DG.LOOT_ICON_GAP
    if bossMode then
        cols, cw = DG.LOOT_COLS3, DG.LOOT_CARD_W3
        stepX = cw + DG.LOOT_GAP_X
    end

    local function makeRow()
        r = CreateFrame("Button", nil, child, "BackdropTemplate")
        r:SetSize(cw, DG.LOOT_CARD_H)
        r:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        HuiCardFX(r, 12)
        r:EnableMouse(true)
        r:EnableMouseWheel(true)
        r:SetScript("OnMouseWheel", function(self, delta)
            DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)
        end)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(DG.LOOT_ICON, DG.LOOT_ICON)
        r.icon:SetPoint("LEFT", r, "LEFT", DG.LOOT_PAD_X, 0)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.name = MakeFS(r, DG.LOOT_FS_NAME, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", tx, -6)
        r.name:SetWidth(cw - tx - DG.LOOT_TEXT_R)
        r.name:SetWordWrap(false)
        r.wishBt = CreateFrame("Button", nil, r)
        r.wishBt:SetSize(24, 24)
        r.wishBt:SetPoint("RIGHT", r, "RIGHT", -4, 0)
        r.wishBt:EnableMouse(true)
        r.wishBt.star = MakeFS(r.wishBt, 20, C_GREY, "CENTER")
        r.wishBt.star:SetAllPoints()
        r.wishBt:SetScript("OnClick", function(self)
            local gm = ns.GearModule
            local row = self:GetParent()
            local id = row.__it and row.__it[1]
            if not (gm and gm.WishToggle and id) then return end
            gm.WishToggle(id)
            PaintWishStar(self, id)
            ns.PlaySound(1)
        end)
        r.wishBt:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_LEFT")
            local gm = ns.GearModule
            local row = self:GetParent()
            local id = row.__it and row.__it[1]
            local on = gm and gm.WishIs and id and gm.WishIs(id)
            GameTooltip:SetText(on and L["移出心愿清单"] or L["加入心愿清单"], 1, 1, 1, 1, true)
            GameTooltip:Show()
        end)
        r.wishBt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        r.tag = MakeFS(r, DG.LOOT_FS_TAG, { 0.42, 0.94, 0.62 }, "RIGHT")
        r.tag:SetText(L["新"])
        r.tag:SetPoint("TOPRIGHT", r, "TOPRIGHT", -30, -6)
        r.tp = MakeFS(r, DG.LOOT_FS_SUB, C_GREY, "LEFT")
        r.tp:SetPoint("TOPLEFT", r, "TOPLEFT", tx, -26)
        r.ch = MakeFS(r, DG.LOOT_FS_SUB, C_GREY, "RIGHT")
        r.ch:SetPoint("TOPRIGHT", r, "TOPRIGHT", -30, -26)
        r.note = MakeFS(r, DG.LOOT_FS_META, C_GREY, "LEFT")
        r.note:SetPoint("LEFT", r, "LEFT", 8, 0)
        r:SetScript("OnEnter", function(self)
            U.dungeonDetailHover = self
            if self.__huiCard then
                HuiCardState(self, (U.lootView or "list") == "card" and "flat" or "hover")
            elseif (U.lootView or "list") == "card" then
                self:SetBackdropColor(1, 1, 1, DG.LOOT_ROW_HOVER)
                self:SetBackdropBorderColor(1, 1, 1, 0)
            else
                self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
                self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
            end
            if self.__it then DG.ShowItemTip(self, self.__it) end
        end)
        r:SetScript("OnLeave", function(self)
            if U.dungeonDetailHover == self then U.dungeonDetailHover = nil end
            self.__tipReshown = nil
            if self.__huiCard then
                HuiCardState(self, (U.lootView or "list") == "card" and "flat" or "norm")
            elseif (U.lootView or "list") == "card" then
                self:SetBackdropColor(1, 1, 1, 0)
                self:SetBackdropBorderColor(1, 1, 1, 0)
            else
                self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
            end
            GameTooltip:Hide()
        end)
        r:SetScript("OnClick", function(self, button) DG.ItemShiftClick(self, button) end)
        return r
    end

    local function takeRow(make, paint)
        nI = nI + 1
        local idx = nI
        local r = rows[idx]
        if r then
            paint(r)
            return
        end
        DG.__pendRows[#DG.__pendRows + 1] = { idx = idx, make = make, paint = paint }
    end

    if (U.lootView or "list") == "card" then
        U:RenderDungeonLootCards(groups, filter, takeRow, makeRow, bossMode, bossEn, bossNpc)
        return
    end

    for _, g in ipairs(groups) do
        local items = g.items
        if filter == "all" or #items > 0 then
            local s = g.src
            nH = nH + 1
            local hd = hdr[nH]
            if not hd then
                hd = { name = MakeFS(child, DG.LOOT_FS_HDR, C_TEXT, "LEFT"),
                       cnt = MakeFS(child, DG.LOOT_FS_META, C_GREY, "RIGHT") }
                hdr[nH] = hd
            end
            local en = s[1] or ""
            local sub = s[3] or ""
            if sub ~= "" then en = (en ~= "" and (en .. " · " .. sub) or sub) end
            hd.name:SetText(s[2] .. (en ~= "" and ("  " .. DG.Hex(C_GREY) .. en .. "|r") or ""))
            hd.name:ClearAllPoints()
            hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
            hd.__vtop, hd.__vh, hd.__vgen = -y, DG.LOOT_HDR_H, DG.__vgen
            hd.name:Show()
            hd.cnt:SetText(format(L["%d 件"], #items))
            hd.cnt:ClearAllPoints()
            hd.cnt:SetPoint("TOPRIGHT", child, "TOPRIGHT", 0, y - 1)
            hd.cnt:Show()
            y = y - DG.LOOT_HDR_H

            if #items == 0 then
                local baseY = y
                takeRow(makeRow, function(r)
                    r:SetSize(cw, DG.LOOT_CARD_H)
                    r.icon:Hide(); r.name:Hide(); r.tag:Hide(); r.tp:Hide(); r.ch:Hide()
                    if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(r.icon, nil) end
                    r.__it = nil
                    r:SetAlpha(1)
                    r.note:SetText(L["暂无掉落数据"])
                    r.note:Show()
                    if r.__huiCard then
                        HuiCardState(r, "norm")
                    else
                        r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
                    end
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, baseY)
                    r.__vtop, r.__vh, r.__vgen = -baseY, DG.LOOT_CARD_H, DG.__vgen
                    r:Show()
                end)
                y = y - stepY
            else
                local baseY = y
                local function paintRow(r, it, rx, ry)
                    r:SetSize(cw, DG.LOOT_CARD_H)
                    r.note:Hide()
                    r.icon:SetTexture(DG.ItemIcon(it[1]))
                    r.icon:Show()
                    if ns.hui and ns.hui.SetIconRing then
                        ns.hui.SetIconRing(r.icon, { ns.hui.QColor(DG.QualOf(it[1])) })
                    end
                    local nm, hasName = DG.ItemName(it[1])
                    local nbudget = it[3] and (cw - tx - DG.LOOT_TAG_W) or (cw - tx - DG.LOOT_TEXT_R)
                    r.name:SetText(DG.FitText(nm, DG.LOOT_FS_NAME, nbudget))
                    if hasName then
                        r.name:SetTextColor(DG.QColor(DG.QualOf(it[1])))
                    else
                        r.name:SetTextColor(Unpack(C_GREY))
                    end
                    r.__named = hasName
                    r.name:Show()
                    if it[3] then
                        r.name:SetWidth(cw - tx - DG.LOOT_TAG_W)
                        r.tag:Show()
                    else
                        r.name:SetWidth(cw - tx - DG.LOOT_TEXT_R)
                        r.tag:Hide()
                    end
                    r.tp:SetText(DG.ItemMeta(it[1]))
                    r.tp:Show()
                    r.ch:SetText(DG.Pct(it[2]) or "")
                    r.ch:Show()
                    r.__it = it
                    PaintWishStar(r.wishBt, it[1])
                    if LF and LF.Apply then LF.Apply(r) end
                    if r.__huiCard then
                        HuiCardState(r, "norm")
                    else
                        r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
                    end
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", rx, ry)
                    r.__vtop, r.__vh, r.__vgen = -ry, DG.LOOT_CARD_H, DG.__vgen
                    r:Show()
                end
                for i, it in ipairs(items) do
                    local rx = ((i - 1) % cols) * stepX
                    local ry = baseY - math.floor((i - 1) / cols) * stepY
                    takeRow(makeRow, function(r) paintRow(r, it, rx, ry) end)
                end
                y = y - math.ceil(#items / cols) * stepY
            end
            y = y - DG.LOOT_GRP_GAP
        end
    end

    for i = nH + 1, #hdr do hdr[i].name:Hide(); hdr[i].cnt:Hide() end
    for i = nI + 1, #rows do rows[i]:Hide() end
    DG.FlushPendingRows()
    DG.CullLootCards()

    local note = U.dungeonDetailNote
    if nH == 0 then
        note:ClearAllPoints()
        note:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)
        if #loot == 0 then
            note:SetText(L["尚未收录这个副本的 boss 名单，数据补上后会自动出现。"])
        else
            note:SetText(L["该分类下暂无掉落。"])
        end
        note:Show()
        y = y - 26
    else
        note:Hide()
    end

    for i = 1, #(pool.card or {}) do pool.card[i]:Hide() end

    local listH = math.max(10, -y + 12)
    if bossMode then
        listH = math.max(listH, DG.LootModelCardH() + DG.LOOT_GAP_Y)
        DG.PaintLootBossModel(d, bossSel, bossEn, bossNpc)
    else
        DG.HideLootBossModel()
    end
    child:SetHeight(listH)
    U.dungeonDetailScroll:SetVerticalScroll(0)
end

function U:RenderDungeonLootCards(groups, filter, takeRow, makeRow, bossMode, bossEn, bossNpc)
    DG.EnsureCardPool()
    local d = U.dungeonDetailCur
    local child, pool = U.dungeonDetailChild, U.dungeonDetailPool
    if not (d and child and pool and takeRow and makeRow) then return end
    local cards, rows = pool.card, pool.item
    if not (cards and rows) then return end
    if not DG.CardPoolReady() then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}
    DG.__pendRows = {}

    local cols = DG.LOOT_COLS
    local cw = DG.LOOT_CARD_W
    if bossMode then
        cols, cw = DG.LOOT_COLS3, DG.LOOT_CARD_W3
    end
    local stepX = cw + DG.LOOT_GAP_X
    local rowW = cw - DG.LOOT_CARD_PAD * 2
    local ix = DG.LOOT_CARD_PAD + DG.LOOT_ICON + DG.LOOT_ICON_GAP
    local nameW = cw - DG.LOOT_CARD_PAD - DG.LOOT_CARD_NAME_R

    local raidWide = (d.raid == true) and not bossMode and U.dungeonLootBoss ~= DG.LOOT_TRASH
    local wideCols = DG.LOOT_COLS
    local wideStepY = DG.LOOT_CARD_H + DG.LOOT_CARD_ROW_GAP
    if raidWide then
        cols = 1
        cw = DG.CHILD_W
        stepX = 0
        rowW = math.floor((cw - DG.LOOT_CARD_PAD * 2 - (wideCols - 1) * DG.LOOT_GAP_X) / wideCols)
        nameW = cw - DG.LOOT_CARD_PAD - DG.LOOT_CARD_NAME_R
    end

    local fold = DB().dungeonLootFold
    if type(fold) ~= "table" then
        fold = {}
        DB().dungeonLootFold = fold
    end

    local colY = {}
    for c = 1, cols do colY[c] = 0 end

    local nC, nR = 0, 0
    for gi = 1, #groups do
        local g = groups[gi]
        local items = g.items
        if filter == "all" or #items > 0 then
            nC = nC + 1
            local card = cards[nC]
            if not card then break end
            local s = g.src
            local key = d.id .. "#" .. gi
            local closed = fold[key] and true or false
            local n = closed and 0 or #items
            local visRows = n
            if raidWide and n > 0 then visRows = math.ceil(n / wideCols) end
            local h = DG.LOOT_CARD_HDR_H + DG.LOOT_CARD_PAD
            if n > 0 then h = h + visRows * DG.LOOT_CARD_H + (visRows - 1) * DG.LOOT_CARD_ROW_GAP end
            local col = ((nC - 1) % cols) + 1
            local cx, cy = (col - 1) * stepX, colY[col]
            colY[col] = cy - (h + DG.LOOT_GAP_Y)

            local en = s[1] or ""
            local sub = s[3] or ""
            if sub ~= "" then en = (en ~= "" and (en .. " · " .. sub) or sub) end
            card.__gid = key
            card.hit.__key = key
            card.hit.__g = { gi = gi, items = items, srcName = s[2] or "", enName = en }
            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", child, "TOPLEFT", cx, cy)
            card:SetSize(cw, h)
            card.__vtop, card.__vh, card.__vgen = -cy, h, DG.__vgen
            card.hit:SetPoint("TOPLEFT", card, "TOPLEFT", 0, 0)
            card.hit:SetPoint("TOPRIGHT", card, "TOPRIGHT", 0, 0)
            card.arrD:SetShown(not closed)
            card.arrU:SetShown(closed)
            card.name:SetText(DG.FitText(s[2] or "", DG.LOOT_FS_HDR, nameW))
            card.name:SetWidth(nameW)
            card.cnt:SetText(format(L["%d 件"], #items))
            card:Show()
            card.hit:SetHeight(DG.LOOT_CARD_MIN_H)

            for ii = 1, n do
                nR = nR + 1
                local it = items[ii]
                local rx = cx + DG.LOOT_CARD_PAD
                local ry = cy - DG.LOOT_CARD_HDR_H - (ii - 1) * (DG.LOOT_CARD_H + DG.LOOT_CARD_ROW_GAP)
                if raidWide then
                    local cc = ((ii - 1) % wideCols) + 1
                    local rr = math.floor((ii - 1) / wideCols)
                    rx = rx + (cc - 1) * (rowW + DG.LOOT_GAP_X)
                    ry = cy - DG.LOOT_CARD_HDR_H - rr * wideStepY
                end
                takeRow(makeRow, function(r)
                    r:SetSize(rowW, DG.LOOT_CARD_H)
                    r.note:Hide()
                    r.icon:SetTexture(DG.ItemIcon(it[1]))
                    r.icon:Show()
                    if ns.hui and ns.hui.SetIconRing then
                        ns.hui.SetIconRing(r.icon, { ns.hui.QColor(DG.QualOf(it[1])) })
                    end
                    local nm, hasName = DG.ItemName(it[1])
                    local nbudget = it[3] and (rowW - ix - DG.LOOT_TAG_W) or (rowW - ix - DG.LOOT_TEXT_R)
                    r.name:SetText(DG.FitText(nm, DG.LOOT_FS_NAME, nbudget))
                    if hasName then
                        r.name:SetTextColor(DG.QColor(DG.QualOf(it[1])))
                    else
                        r.name:SetTextColor(Unpack(C_GREY))
                    end
                    r.__named = hasName
                    r.name:Show()
                    if it[3] then
                        r.name:SetWidth(rowW - ix - DG.LOOT_TAG_W)
                        r.tag:Show()
                    else
                        r.name:SetWidth(rowW - ix - DG.LOOT_TEXT_R)
                        r.tag:Hide()
                    end
                    r.tp:SetText(DG.ItemMeta(it[1]))
                    r.tp:Show()
                    r.ch:SetText(DG.Pct(it[2]) or "")
                    r.ch:Show()
                    r.__it = it
                    PaintWishStar(r.wishBt, it[1])
                    local LF = ns.LootFilter
                    if LF and LF.Apply then LF.Apply(r) end
                    if r.__huiCard then
                        HuiCardState(r, "flat")
                    else
                        r:SetBackdropColor(1, 1, 1, 0)
                        r:SetBackdropBorderColor(1, 1, 1, 0)
                    end
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", rx, ry)
                    r.__vtop, r.__vh, r.__vgen = -ry, DG.LOOT_CARD_H, DG.__vgen
                    r:Show()
                end)
            end
        end
    end

    for i = nC + 1, #cards do cards[i]:Hide() end
    for i = nR + 1, #rows do rows[i]:Hide() end
    DG.FlushPendingRows()
    DG.CullLootCards()
    for i = 1, #(pool.hdr or {}) do
        pool.hdr[i].name:Hide()
        pool.hdr[i].cnt:Hide()
    end

    local note = U.dungeonDetailNote
    if nC == 0 then
        note:ClearAllPoints()
        note:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)
        if #loot == 0 then
            note:SetText(L["尚未收录这个副本的 boss 名单，数据补上后会自动出现。"])
        else
            note:SetText(L["该分类下暂无掉落。"])
        end
        note:Show()
    else
        note:Hide()
    end

    local bottom = 0
    for c = 1, cols do
        if colY[c] < bottom then bottom = colY[c] end
    end
    local cardH = math.max(10, -bottom + DG.LOOT_GAP_Y)
    if bossMode then
        cardH = math.max(cardH, DG.LootModelCardH() + DG.LOOT_GAP_Y)
        DG.PaintLootBossModel(d, U.dungeonLootBoss, bossEn, bossNpc)
    else
        DG.HideLootBossModel()
    end
    child:SetHeight(cardH)
end

local LOOT_MODEL_LATE = { 0.6, 3.5 }

function DG.LootModelProbe(m)
    local ok, v = pcall(m.GetDisplayInfo, m)
    return (ok and type(v) == "number" and v ~= 0) or false
end

function DG.LootModelAlpha(m, v)
    if m.SetAlpha then pcall(m.SetAlpha, m, v) end
end

function DG.LootModelPose(m)
    pcall(m.SetRotation, m, math.rad(-15))
end

function DG.LootModelApply(m, npc, disp)
    if disp and type(m.SetDisplayInfo) == "function" then
        pcall(m.SetDisplayInfo, m, disp)
    elseif npc then
        pcall(m.SetCreature, m, npc)
    end
end

function DG.LootModelLateCheck(c, npc, disp)
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    local m = c and c.model
    if not m then return end
    for i = 1, #LOOT_MODEL_LATE do
        C_Timer.After(LOOT_MODEL_LATE[i], function()
            if not (c:IsShown() and c.__disp == disp and c.__npc == npc) then return end
            if DG.LootModelProbe(m) then return end
            if i < #LOOT_MODEL_LATE then
                DG.LootModelApply(m, npc, disp)
                DG.LootModelPose(m)
            else
                c.__disp, c.__npc = nil, nil
                m:Hide()
            end
        end)
    end
end

function DG.EnsureLootBossCard()
    local child = U.dungeonDetailChild
    if not child then return nil end
    local c = U.dungeonLootBossCard
    if c and c:GetParent() == child then return c end
    c = CreateFrame("Frame", nil, child, "BackdropTemplate")
    c:SetWidth(DG.LOOT_MODEL_W)
    c:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    c:SetBackdropColor(0, 0, 0, 0)
    c:SetBackdropBorderColor(0, 0, 0, 0)
    if IsHui() and ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L1, "both", true, 1)
    else
        c:SetBackdropColor(1, 1, 1, 0.03)
        c:SetBackdropBorderColor(1, 1, 1, 0.10)
    end
    c.name = MakeFS(c, DG.LOOT_FS_HDR, C_TEXT, "LEFT")
    c.name:SetPoint("TOPLEFT", c, "TOPLEFT", 8, -6)
    c.name:SetWidth(DG.LOOT_MODEL_W - 16)
    c.name:SetWordWrap(false)
    local m = CreateFrame("PlayerModel", nil, c)
    m:EnableMouse(false)
    m:EnableMouseWheel(false)
    if m.SetKeepModelOnHide then m:SetKeepModelOnHide(true) end
    m:SetPoint("TOPLEFT", c, "TOPLEFT", 6, -(DG.LOOT_CARD_HDR_H + 6))
    m:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", -6, 6)
    m:Hide()
    c.model = m
    c:Hide()
    U.dungeonLootBossCard = c
    return c
end

function DG.LootModelCardH()
    local sc = U.dungeonDetailScroll
    local vh = sc and sc.GetHeight and sc:GetHeight()
    if type(vh) == "number" and vh > 0 then
        return math.floor(vh - PAGE_INSET - DG.GUTTER)
    end
    return DG.LOOT_MODEL_H
end

function DG.PaintLootBossModel(d, bossSel, bossEn, bossNpc)
    local c = DG.EnsureLootBossCard()
    if not (c and c.model) then return end
    if not U.dungeonDetailChild then return end
    c:SetHeight(DG.LootModelCardH())
    c:ClearAllPoints()
    c:SetPoint("TOPLEFT", U.dungeonDetailChild, "TOPLEFT", DG.LOOT_MODEL_X, 0)
    c.name:SetText(bossSel or "")
    c:Show()
    local m = c.model
    local row = (d and ns.BossModelDisplay and ns.BossModelDisplay[d.id]) or nil
    local disp = (row and bossEn) and row[bossEn] or nil
    if not bossNpc and not disp then
        m:Hide()
        c.__disp, c.__npc = nil, nil
        return
    end
    m:Show()
    if c.__disp ~= disp or c.__npc ~= bossNpc then
        c.__disp, c.__npc = disp, bossNpc
        DG.LootModelApply(m, bossNpc, disp)
        DG.LootModelPose(m)
        DG.LootModelLateCheck(c, bossNpc, disp)
    end
end

function DG.HideLootBossModel()
    local c = U.dungeonLootBossCard
    if c then c:Hide() end
end

function DG.LootFoldToggle(key)
    local s = DB()
    local f = s.dungeonLootFold
    if type(f) ~= "table" then
        f = {}
        s.dungeonLootFold = f
    end
    f[key] = (not f[key]) or nil
    local sc = ns.DungeonUI and ns.DungeonUI.dungeonDetailScroll
    local keep = sc and sc:GetVerticalScroll() or 0
    ns.DungeonUI:RenderDungeonLoot()
    if sc then sc:SetVerticalScroll(keep) end
    ns.PlaySound(1)
end

function U:SetLootView(v)
    local nv = (v == "card") and "card" or "list"
    U.lootView = nv
    DB().lootView = nv
    if nv == "card" then DG.EnsureCardPool() end
    U:RefreshLootViewBtns()
    U:RenderDungeonLoot()
    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetVerticalScroll(0) end
    ns.PlaySound(1)
end

function U:RefreshLootViewBtns()
    local cur = U.lootView or "list"
    for i = 1, #(U.dungeonLootViewBtns or {}) do
        local bt = U.dungeonLootViewBtns[i]
        if bt then
            local sel = (bt.__lootView == cur)
            ns.hui.SetButtonSelected(bt, sel)
        end
    end
end

function DG.QLFn(name)
    local fn = C_QuestLog and C_QuestLog[name]
    if type(fn) == "function" then return fn end
    return nil
end

function DG.QLCall(name, id)
    if id == nil then return nil end
    local fn = DG.QLFn(name)
    if not fn then return nil end
    local ok, v = pcall(fn, id)
    if ok then return v end
    return nil
end

DG.questDoneCache = {}
function DG.QuestSnapReset()
    DG.questDoneSet = nil
    DG.questDoneCache = {}
end
function DG.BuildQuestSnap()
    DG.QuestSnapReset()
    local fn = DG.QLFn("GetAllCompletedQuestIDs")
    if not fn then return false end
    local ok, list = pcall(fn)
    if not ok or type(list) ~= "table" then return false end
    local set = {}
    for i = 1, #list do
        local q = list[i]
        if q then set[q] = true end
    end
    DG.questDoneSet = set
    return true
end

function DG.QuestDone(id)
    if not id then return false end
    local sim = DG.questSim
    if sim then
        local st = sim[id]
        if st ~= nil then return st == "done" end
    end
    local set = DG.questDoneSet
    if set then return set[id] == true end
    local c = DG.questDoneCache[id]
    if c ~= nil then return c end
    local v = (DG.QLCall("IsQuestFlaggedCompleted", id) == true)
    DG.questDoneCache[id] = v
    return v
end
function DG.QuestActive(id)
    if not id then return false end
    local sim = DG.questSim
    if sim then
        local st = sim[id]
        if st ~= nil then return st == "active" end
    end
    return DG.QLCall("IsOnQuest", id) == true
end
DG.questSim = nil
DG.QUEST_SIM_CYCLE = { "done", "active", "none" }
DG.QUEST_SIM_TEXT = { done = "已完成", active = "已接取", none = "未接取" }
function DG.SimQuests(key, mode)
    local d
    for _, x in ipairs((ns.DungeonData and ns.DungeonData.dungeons) or {}) do
        if x.id == key then d = x break end
    end
    if not d then return nil end
    if mode ~= "done" and mode ~= "active" and mode ~= "none" then mode = nil end
    local list = DG.QuestList(d)
    local sim, out = {}, {}
    for i = 1, #list do
        local id = list[i][1]
        if type(id) == "number" then
            local st = mode or DG.QUEST_SIM_CYCLE[((i - 1) % 3) + 1]
            sim[id] = st
            out[#out + 1] = { id = id, st = st }
        end
    end
    local nq = #out
    for i = 1, #list do
        local pre = list[i][9]
        if type(pre) == "table" then
            for k = 1, #pre do
                local pid = tonumber(pre[k])
                if pid and not sim[pid] then
                    nq = nq + 1
                    local st = mode or DG.QUEST_SIM_CYCLE[((nq - 1) % 3) + 1]
                    sim[pid] = st
                    out[#out + 1] = { id = pid, st = st }
                end
            end
        end
    end
    DG.questSim = sim
    return d, out
end
function DG.ClearQuestSim()
    DG.questSim = nil
end
if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERQUESTSIM1 = "/dfsim"
    SLASH_DUNGEONSFOREVERQUESTSIM2 = "/dfsimq"
    SlashCmdList["DUNGEONSFOREVERQUESTSIM"] = function(msg)
        local a, b = tostring(msg or ""):match("^%s*(%S*)%s*(%S*)")
        a = (a or ""):lower()
        b = (b or ""):lower()
        local head = "|cff46bf72[无限副本手册·任务模拟]|r "
        if a == "off" or a == "0" or a == "clear" then
            DG.ClearQuestSim()
            if U.dungeonBuilt and U.dungeonDetailCur then U:RenderDungeonQuests() end
            print(head .. "模拟已关闭，恢复真实任务状态。")
            return
        end
        local key = (a == "" or a == "demo" or a == "on") and "hall_of_thanes" or a
        local d, out = DG.SimQuests(key, b)
        if not d then
            print(head .. "找不到副本 " .. key .. "。用法：/dfsim [副本id] [done|active|none] / /dfsim off")
            return
        end
        local n = out and #out or 0
        if ns.ShowDungeonDetail then ns.ShowDungeonDetail(d.id) end
        U.dungeonQView = "overview"
        if U.dungeonBuilt then U:RenderDungeonQuests() end
        local sub = (b == "done" or b == "active" or b == "none") and ("全部 " .. DG.QUEST_SIM_TEXT[b]) or "三态轮转"
        print(head .. (d.name or key) .. " · " .. n .. " 条任务 · " .. sub)
        for i = 1, n do
            local e = out[i]
            local nm = DG.QuestName(e.id)
            print("  |cff9a9a9a" .. i .. ".|r " .. tostring(nm) .. "  |cff" .. (e.st == "done" and "40d95a" or (e.st == "active" and "ffd100" or "8c8c8c")) .. DG.QUEST_SIM_TEXT[e.st] .. "|r")
        end
    end
end
DG.__qWatch = {}
DG.__qDataHooks = {}
function DG.OnQuestData(id)
    local MM = ns.MapModule
    if MM and MM.OnQuestData then MM.OnQuestData(id) end
    local hl = DG.__qDataHooks
    if hl then
        for i = 1, #hl do
            local fn = hl[i]
            if type(fn) == "function" then pcall(fn, id) end
        end
    end
end
function DG.RequestQuest(id)
    if type(id) ~= "number" or id < 1 or id ~= math.floor(id) then return end
    if not DG.__qEvt then
        local ev = CreateFrame("Frame")
        pcall(ev.RegisterEvent, ev, "QUEST_DATA_LOAD_RESULT")
        ev:SetScript("OnEvent", function(_, _, qid)
            if qid then
                C_Timer.After(0, function() DG.OnQuestData(qid) end)
            end
        end)
        DG.__qEvt = ev
    end
    if not DG.__qAsked[id] then
        DG.__qAsked[id] = true
        if C_QuestLog and C_QuestLog.RequestLoadQuestByID then
            pcall(C_QuestLog.RequestLoadQuestByID, id)
        end
        local n0 = DG.QLCall("GetTitleForQuestID", id)
        if type(n0) == "string" and n0 ~= "" then
            DG.OnQuestData(id)
            return
        end
    end
    if not (C_Timer and C_Timer.After) then return end
    if DG.__qWatch[id] then return end
    DG.__qWatch[id] = true
    for _, d in ipairs({ 0.3, 0.8, 1.5, 3 }) do
        C_Timer.After(d, function()
            local n = DG.QLCall("GetTitleForQuestID", id)
            if type(n) == "string" and n ~= "" then
                DG.__qWatch[id] = nil
                DG.OnQuestData(id)
            end
        end)
    end
end
function DG.QuestName(id)
    if not id then return nil, false end
    if type(id) ~= "number" then return tostring(id), false end
    local n = DG.QLCall("GetTitleForQuestID", id)
    if type(n) == "string" and n ~= "" then return n, true end
    if not DG.__qAsked[id] then
        DG.__qAsked[id] = true
        if C_QuestLog and C_QuestLog.RequestLoadQuestByID then
            pcall(C_QuestLog.RequestLoadQuestByID, id)
        end
        n = DG.QLCall("GetTitleForQuestID", id)
        if type(n) == "string" and n ~= "" then return n, true end
    end
    local ex = ns.EnsureDungeonQuestExtInfo()[id]
    if ex and type(ex.nm) == "string" and ex.nm ~= "" then return ex.nm, true end
    return format(L["任务 #%d"], id), false
end
function DG.QuestLevel(id)
    local n = DG.QLCall("GetQuestDifficultyLevel", id)
    if type(n) == "number" and n > 0 then return n end
    return nil
end
function DG.QuestLink(id, lvl)
    if not id or type(GetQuestLink) ~= "function" then return nil end
    local ok, s = pcall(GetQuestLink, id)
    if ok and type(s) == "string" and s ~= "" then return s end
    local title = DG.QLCall("GetTitleForQuestID", id)
    if type(title) ~= "string" or title == "" then title = "?" end
    return format("|cffffff00|Hquest:%d:%d|h[%s]|h|r", id, lvl or 1, title)
end

DG.__qDataAsked = DG.__qDataAsked or {}
function DG.PrefetchQuestData(list)
    local req = DG.QLFn("RequestLoadQuestByID")
    if not req then return end
    for i = 1, #(list or {}) do
        local id = type(list[i]) == "table" and list[i][1] or nil
        if id and not DG.__qDataAsked[id] then
            DG.__qDataAsked[id] = true
            pcall(req, id)
        end
    end
end

function DG.AskQuestData(id)
    if id == nil or DG.__qDataAsked[id] then return end
    DG.__qDataAsked[id] = true
    local req = DG.QLFn("RequestLoadQuestByID")
    if req then pcall(req, id) end
end

function DG.DifficultyColor(level)
    if type(level) ~= "number" or type(GetQuestDifficultyColor) ~= "function" then return nil end
    local ok, c1, c2, c3 = pcall(GetQuestDifficultyColor, level)
    if not ok then return nil end
    if type(c1) == "table" and type(c1.r) == "number" then
        return { c1.r, c1.g, c1.b }
    end
    if type(c1) == "number" and type(c2) == "number" and type(c3) == "number" then
        return { c1, c2, c3 }
    end
    return nil
end

function DG.ExtQuestRow(pid)
    local info = ns.EnsureDungeonQuestExtInfo()[pid]
    if not info then return nil end
    local req
    if info.goals then
        for _, g in ipairs(info.goals) do
            if g[1] == "i" then
                req = req or {}
                req[#req + 1] = g[2]
            end
        end
    end
    local diff
    if info.lv and info.lvStd then
        local t1 = info.lv
        local t2 = math.max(t1 + 1, info.lv + 3)
        local t3 = math.max(t2 + 1, info.lvStd - 2)
        local t4 = math.max(t3 + 1, info.lvStd + 3)
        local t5 = math.max(t4 + 1, info.lvStd + 7)
        diff = { { t1, 1 }, { t2, 2 }, { t3, 3 }, { t4, 4 }, { t5, 5 } }
    end
    local pre = info.pre
    if not pre and ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[pid] then
        local ex = ns.DungeonQuestPreExtra[pid]
        if type(ex) == "table" and type(ex[1]) == "number" then pre = { ex[1] } end
    end
    return {
        pid, info.side, info.lv, info.lvStd, info.npc, info.zone, nil, info.si or nil,
        pre, info.rew, info.obj, info.text, diff, req, info.cls, info.npcid, info.npc, info.gains,
        true, info.obj,
    }
end

function DG.QuestDescription(id)
    if id == nil then return nil end
    DG.AskQuestData(id)
    local d = DG.QLCall("GetQuestDescription", id)
    if type(d) == "string" and d ~= "" then return d end
    local link = DG.QuestLink(id)
    if not link then return nil end
    local title = DG.QLCall("GetTitleForQuestID", id)
    local function take(txt, parts)
        if txt == "" or txt:find("^%s*$") or txt:find("^　*$")
           or txt:find("^任务等级") or txt:find("^Level ") or txt:find("^等级")
           or txt:find("你已经在做") or txt:find("你已经完成")
           or txt:find("^You are already") or txt:find("^You have already") then
            return parts
        end
        parts = parts or {}
        parts[#parts + 1] = txt
        return parts
    end
    local parts
    if type(C_TooltipInfo) == "table" and type(C_TooltipInfo.GetHyperlink) == "function" then
        local ok, data = pcall(C_TooltipInfo.GetHyperlink, link)
        if ok and type(data) == "table" and type(data.lines) == "table" then
            local start = 0
            for i = 1, #data.lines do
                local ln = data.lines[i]
                local txt = (type(ln) == "table" and type(ln.leftText) == "string") and ln.leftText or nil
                if txt and title and txt ~= "" and txt:find(title, 1, true) then
                    start = i
                    break
                end
            end
            for i = start + 1, #data.lines do
                local ln = data.lines[i]
                local txt = (type(ln) == "table" and type(ln.leftText) == "string") and ln.leftText or nil
                if txt and (txt:find("^要求") or txt:find("^Requirements")
                   or txt:find("^任务 ID") or txt:find("^Quest ID")) then
                    break
                end
                if txt then parts = take(txt, parts) end
            end
        end
    end
    if not parts or #parts == 0 then return nil end
    return table.concat(parts, "\n")
end

DG.GAINS_FALLBACK = false

function DG.Thousand(n)
    local s = tostring(n)
    local k = #s % 3
    local out = (k > 0 and s:sub(1, k)) or ""
    for i = k + 1, #s, 3 do
        out = out .. (out ~= "" and "," or "") .. s:sub(i, i + 2)
    end
    return out
end

function DG.QuestRewardXP(id)
    if id == nil or type(GetQuestLogRewardXP) ~= "function" then return nil end
    local ok, v = pcall(GetQuestLogRewardXP, id)
    if ok and type(v) == "number" and v > 0 then return v end
    return nil
end

function DG.QuestRewardMoney(id)
    if id == nil or type(GetQuestLogRewardMoney) ~= "function" then return nil end
    local ok, v = pcall(GetQuestLogRewardMoney, id)
    if ok and type(v) == "number" and v > 0 then return v end
    return nil
end

function DG.QuestObjectiveList(id)
    if id == nil then return nil end
    local fn = DG.QLFn("GetQuestObjectives")
    if not fn then return nil end
    local ok, list = pcall(fn, id)
    if not ok or type(list) ~= "table" then return nil end
    local out = {}
    for _, o in ipairs(list) do
        if type(o) == "table" and type(o.text) == "string" and o.text ~= "" then
            out[#out + 1] = { o.text, tonumber(o.numFilled) or 0, tonumber(o.numRequired) or 0 }
        end
    end
    if #out == 0 then return nil end
    return out
end

function DG.QuestObjectives(id)
    local list = DG.QuestObjectiveList(id)
    if not list then return nil end
    local parts = {}
    for _, ob in ipairs(list) do
        local need = ob[3]
        if need > 0 and not ob[1]:find("%d+/%d+") then
            parts[#parts + 1] = format("%s（%d/%d）", ob[1], ob[2], need)
        else
            parts[#parts + 1] = ob[1]
        end
    end
    return table.concat(parts, "\n")
end

function DG.ItemObjectiveProgress(questID, itemID)
    if questID == nil or itemID == nil then return nil end
    local nm, ok = DG.ItemName(itemID)
    if not ok then return nil end
    local list = DG.QuestObjectiveList(questID)
    if not list then return nil end
    for _, ob in ipairs(list) do
        if ob[3] > 0 and ob[1]:find(nm, 1, true) then
            return ob[2], ob[3]
        end
    end
    return nil
end

function DG.ApplyChipBadge(c)
    if not (c and c.badge) then return end
    if not c.__q then c.badge:Hide() return end
    local have, need = DG.ItemObjectiveProgress(c.__q, c.__it and c.__it[1])
    if have then
        c.badge:SetText(format("%d/%d", have, need))
        if have >= need then
            c.badge:SetTextColor(Unpack(C_GREEN))
        else
            c.badge:SetTextColor(Unpack(C_GREY))
        end
        c.badge:Show()
    else
        c.badge:Hide()
    end
end

function DG.NeedObjectivesText(questID, items)
    local list = DG.QuestObjectiveList(questID)
    if not list then return nil end
    local names = {}
    if items then
        for _, iid in ipairs(items) do
            local nm, ok = DG.ItemName(iid)
            if ok then names[#names + 1] = nm end
        end
    end
    local parts = {}
    for _, ob in ipairs(list) do
        local taken = false
        if ob[3] > 0 then
            for _, nm in ipairs(names) do
                if ob[1]:find(nm, 1, true) then taken = true break end
            end
        end
        if not taken then
            if ob[3] > 0 and not ob[1]:find("%d+/%d+") then
                parts[#parts + 1] = format("%s（%d/%d）", ob[1], ob[2], ob[3])
            else
                parts[#parts + 1] = ob[1]
            end
        end
    end
    if #parts == 0 then return nil end
    return table.concat(parts, "\n")
end

function DG.QuestDataSig(id)
    local objLen, prog = 0, 0
    local list = DG.QuestObjectiveList(id)
    if list then
        for _, ob in ipairs(list) do
            objLen = objLen + #ob[1]
            prog = prog + ob[2] * 100 + ob[3]
        end
    end
    local desc = DG.QuestDescription(id)
    return format("%d:%d:%d:%d:%d", DG.QuestRewardXP(id) or 0, DG.QuestRewardMoney(id) or 0,
        objLen, prog, desc and #desc or 0)
end

function DG.GainsSegs(q)
    if not q or q[1] == nil then return nil end
    local g = q[18]
    local seg = {}
    local apiXp = DG.QuestRewardXP(q[1])
    local apiMoney = DG.QuestRewardMoney(q[1])
    local xp = apiXp or ((DG.GAINS_FALLBACK or q[19]) and g and g.xp or nil)
    if xp then seg[#seg + 1] = DG.Thousand(xp) .. L[" 经验"] end
    local money = apiMoney or ((DG.GAINS_FALLBACK or q[19]) and g and g.money or nil)
    if money then
        local go, si, co = math.floor(money / 10000), math.floor((money % 10000) / 100), money % 100
        local ms = ""
        if go > 0 then ms = ms .. go .. L["金"] end
        if si > 0 then ms = ms .. si .. L["银"] end
        if co > 0 or ms == "" then ms = ms .. co .. L["铜"] end
        seg[#seg + 1] = ms
    end
    if g and g.rep and #g.rep > 0 then
        local rs = {}
        for _, rr in ipairs(g.rep) do
            rs[#rs + 1] = rr[3] .. " +" .. rr[2]
        end
        seg[#seg + 1] = table.concat(rs, "、")
    end
    return seg
end

function DG.RewardsArrived(id)
    local sig = DG.QuestDataSig(id)
    local g = U.dungeonQDetGains
    if g and g.questID == id and sig ~= g.sig then
        g.sig = sig
        if U.RenderQuestDetail and U.dungeonQDet
           and U.dungeonQDet.IsShown and U.dungeonQDet:IsShown() then
            U:RenderQuestDetail()
        end
    end
    local w = DG.__bagGains
    if w and w.questID == id and sig ~= w.sig then
        w.sig = sig
        if w.apply then pcall(w.apply) end
    end
end

DG.__rewAsked = {}
function DG.RequestQuestRewardData(id)
    if not id or DG.__rewAsked[id] then return end
    DG.__rewAsked[id] = true
    DG.EnsureQuestRewardListener()
    local req = DG.QLFn("RequestLoadQuestByID")
    if req then pcall(req, id) end
    local pre = C_TaskQuest and type(C_TaskQuest.RequestPreloadRewardData) == "function"
        and C_TaskQuest.RequestPreloadRewardData or nil
    if pre then
        local hv = type(HaveQuestRewardData) == "function" and HaveQuestRewardData or nil
        local ok, ready
        if hv then ok, ready = pcall(hv, id) end
        if not ok or not ready then pcall(pre, id) end
    end
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        local step = 0
        local function tick()
            if not DG.__rewAsked[id] then return end
            step = step + 1
            if step < 3 and type(HaveQuestRewardData) == "function"
               and C_TaskQuest and type(C_TaskQuest.RequestPreloadRewardData) == "function" then
                local ok, ready = pcall(HaveQuestRewardData, id)
                if ok and not ready then pcall(C_TaskQuest.RequestPreloadRewardData, id) end
            end
            DG.RewardsArrived(id)
            if step < 3 then C_Timer.After(step * 1.2, tick) end
        end
        C_Timer.After(1.2, tick)
    end
end

function DG.EnsureQuestRewardListener()
    if DG.__rewEvt then return DG.__rewEvt end
    local ev = CreateFrame("Frame")
    ev:RegisterEvent("QUEST_LOG_UPDATE")
    pcall(ev.RegisterEvent, ev, "QUEST_DATA_LOAD_RESULT")
    pcall(ev.RegisterEvent, ev, "TOOLTIP_DATA_UPDATE")
    ev:SetScript("OnEvent", function(_, event, arg1)
        C_Timer.After(0, function()
            if event == "QUEST_DATA_LOAD_RESULT" then
                if arg1 then DG.RewardsArrived(arg1) end
            else
                local g = U.dungeonQDetGains
                if g then DG.RewardsArrived(g.questID) end
            end
        end)
    end)
    DG.__rewEvt = ev
    return ev
end

function DG.EnsureQuestListener()
    if DG.__questEvt then return DG.__questEvt end
    local ev = CreateFrame("Frame")
    ev:RegisterEvent("QUEST_TURNED_IN")
    ev:RegisterEvent("PLAYER_ENTERING_WORLD")
    ev:RegisterEvent("PLAYER_LOGIN")
    ev:RegisterEvent("QUEST_LOG_UPDATE")
    ev:SetScript("OnEvent", function(_, event, arg1)
        C_Timer.After(0, function()
            if event == "QUEST_TURNED_IN" then
                if arg1 then
                    if DG.questDoneSet then DG.questDoneSet[arg1] = true end
                    DG.questDoneCache[arg1] = true
                end
            elseif event == "QUEST_LOG_UPDATE" then
            else
                DG.BuildQuestSnap()
            end
            if U.RefreshQuestRows then U.RefreshQuestRows() end
        end)
    end)
    DG.__questEvt = ev
    return ev
end

function DG.ShowQuestTip(owner, q)
    if not q then return end
    DG.AskQuestData(q[1])
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local link = DG.QuestLink(q[1], q[3])
    local native = false
    if link and GameTooltip.SetHyperlink and not string.find(link, "[?]", 1, true) then
        local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, link)
        if ok then
            GameTooltip:Show()
            local n = GameTooltip.NumLines and GameTooltip:NumLines() or 0
            native = (type(n) == "number" and n > 1)
        end
    end
    if native then return end

    GameTooltip:ClearLines()
    local nm, hasName = DG.QuestName(q[1])
    GameTooltip:AddLine(nm, 1, 1, 1, true)
    local st = DG.QuestState(q[1])
    if st == "done" then
        GameTooltip:AddLine(L["已完成"], 0.25, 0.85, 0.35)
    elseif st == "active" then
        GameTooltip:AddLine(L["进行中"], 1, 0.82, 0)
    else
        GameTooltip:AddLine(L["未完成"], 0.6, 0.6, 0.6)
    end
    if q[3] then GameTooltip:AddLine(format(L["%d 级可接"], q[3]), 0.75, 0.75, 0.75) end
    local smap, sx, sy, szone = DG.StartLoc(q[1], q[16])
    local sloc = (smap and DG.LocText(smap, sx, sy, szone)) or DG.ZoneShort(q[6])
    local where = (q[17] and q[17] ~= "" and q[17]) or q[5] or ""
    if q[17] and q[17] ~= "" and q[16] then where = where .. " #" .. q[16] end
    if sloc and sloc ~= "" then where = (where ~= "" and (where .. " · " .. sloc) or sloc) end
    if where ~= "" then GameTooltip:AddLine(L["起始："] .. where, 0.75, 0.75, 0.75, true) end
    do
        local en = DG.QuestEndNpc(q[1])
        if en then
            local txt = (en[2] and en[2] ~= "" and en[2]) or ""
            if en[1] then txt = (txt ~= "" and (txt .. " #" .. en[1]) or ("#" .. en[1])) end
            local zl = DG.LocText(en[3], en[4], en[5], en[6])
            if zl and zl ~= "" then txt = (txt ~= "" and (txt .. " · " .. zl) or zl) end
            if txt ~= "" then GameTooltip:AddLine(L["结束："] .. txt, 0.75, 0.75, 0.75, true) end
        end
    end
    if q[9] and #q[9] > 0 then
        local parts = {}
        for _, seg in ipairs(q[9]) do
            if type(seg) == "number" then
                local pnm, pok = DG.QuestName(seg)
                if pok then
                    parts[#parts + 1] = pnm .. " #" .. seg
                elseif q[7] then
                    parts[#parts + 1] = q[7]
                else
                    parts[#parts + 1] = pnm
                end
            else
                parts[#parts + 1] = tostring(seg)
            end
        end
        if #parts > 0 then
            GameTooltip:AddLine(L["前置："] .. table.concat(parts, "、"), 0.75, 0.75, 0.75, true)
        end
    elseif q[7] then
        GameTooltip:AddLine(L["前置："] .. q[7], 0.75, 0.75, 0.75, true)
    end
    if not hasName then
        GameTooltip:AddLine(L["客户端未收录此任务，暂时没有客户端数据"], 0.5, 0.5, 0.5, true)
    end
    GameTooltip:Show()
end

DG.Q_LIST_W = 520
DG.Q_DET_GAP = 8
DG.Q_PAD = 8
DG.Q_DET_W = DG.CHILD_W - DG.Q_LIST_W - DG.Q_DET_GAP - DG.Q_PAD * 2
DG.Q_ROW_H = 34
DG.Q_GAP_Y = 4
DG.Q_X_NAME = 30
DG.Q_X_LOC = 288
DG.Q_X_LV = 386
DG.Q_W_NAME = 150
DG.Q_W_LOC = 90
DG.Q_BADGE_H = (ns.hui and ns.hui.ChipH and ns.hui.ChipH(14)) or 13.7
DG.Q_BADGE_GAP = 4
DG.Q_BADGE_PAD = 5
DG.Q_BADGE_FS = 11
DG.Q_BADGE_MIN_W = 24
DG.Q_BADGE_CLS_BG = { 0.64, 0.61, 0.55, 1 }
DG.Q_BADGE_PRE_BG = { 0.78, 0.60, 0.10, 1 }
DG.Q_BADGE_SHARE_BG = { 0.16, 0.52, 0.26, 1 }
DG.Q_BADGE_RACE_BG = { 0.78, 0.14, 0.12, 1 }
DG.Q_BADGE_IN_BG = { 0.20, 0.45, 0.55, 1 }
DG.Q_BADGE_BUY_BG = { 0.16, 0.38, 0.62, 1 }
DG.Q_BADGE_MID_BG = { 0.42, 0.26, 0.60, 1 }
DG.Q_RACE_TAG = { [1049] = { ok = { 2, 6, 8 }, label = "非亡灵" } }
DG.Q_RACE_TAG_L = { ["非亡灵"] = L["非亡灵"] }
function DG.QuestRaceTag(qid)
    local rt = DG.Q_RACE_TAG[qid]
    if not rt or not UnitRace then return nil end
    local _, _, rid = UnitRace("player")
    if not rid then return nil end
    for k = 1, #rt.ok do
        if rt.ok[k] == rid then return nil end
    end
    return DG.Q_RACE_TAG_L[rt.label] or rt.label
end
DG.Q_FS_DET = 14
DG.Q_FLOW_H = 20
DG.Q_FLOW_DOT = 16
DG.Q_FLOW_MARK = 14
DG.Q_MARK_SYM = {
    done = "Interface\\AddOns\\DungeonsForever\\Media\\CheckMark",
    active = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkAsk",
    todo = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkExcl",
}
DG.Q_MARK_INK = {
    done = { 0.043, 0.239, 0.102 },
    active = { 0.227, 0.165, 0 },
    todo = { 0.102, 0.102, 0.102 },
}
DG.Q_FLOW_SEC_GAP = 6
DG.Q_FLOW_ST_GAP = 4
DG.Q_FLOW_IDEO = "\227\128\128" .. " "
DG.Q_LINK_ITEM = { 1, 0.92, 0.72 }
DG.C_FAC_A = { 0.45, 0.65, 1 }
DG.C_FAC_H = { 1, 0.40, 0.40 }
DG.Q_FS_NAME = 14
DG.Q_FS_META = 14
DG.Q_FS_HDR = 16
DG.Q_HDR_H = 26
DG.Q_GRP_GAP = 8
DG.Q_SUM_H = 28
DG.Q_HEAD_H = DG.Q_PAD + 24 + DG.Q_PAD
DG.Q_STATUS_TAG = { done = L["已完成"], active = L["进行中"], todo = L["未完成"] }
DG.QFILTERS = { "all", "todo", "done" }
DG.QFILTER_LABEL = { all = L["全部"], todo = L["未完成"], done = L["已完成"] }
DG.QSIDE_LABEL = { all = L["全部"], A = L["联盟"], H = L["部落"] }
DG.Q_DIFF_COLOR = {
    [1] = { 1, 0.12, 0.12 }, [2] = { 1, 0.5, 0.25 }, [3] = { 1, 0.82, 0 },
    [4] = { 0.12, 1, 0 }, [5] = { 0.6, 0.6, 0.6 },
}
DG.QCLASS_DIM = 0.78
DG.QCLASS_LUM = 0.62
DG.QCLASS_TOKEN = {
    [ns.DL("战士")] = "WARRIOR", [ns.DL("圣骑士")] = "PALADIN", [ns.DL("猎人")] = "HUNTER", [ns.DL("盗贼")] = "ROGUE",
    [ns.DL("牧师")] = "PRIEST", [ns.DL("萨满")] = "SHAMAN", [ns.DL("法师")] = "MAGE", [ns.DL("术士")] = "WARLOCK", [ns.DL("德鲁伊")] = "DRUID",
}
function DG.QClassColor(cls)
    local t = RAID_CLASS_COLORS and RAID_CLASS_COLORS[DG.QCLASS_TOKEN[cls] or ""]
    if t and t.r then return { t.r, t.g, t.b } end
    return C_GOLD
end
function DG.QClassFill(cls)
    local c = DG.QClassColor(cls)
    local avg = (c[1] + c[2] + c[3]) / 3
    local k = DG.QCLASS_DIM
    if avg > 0 and avg * k > DG.QCLASS_LUM then k = DG.QCLASS_LUM / avg end
    return { c[1] * k, c[2] * k, c[3] * k, 1 }
end
function DG.QClassList(cls)
    if not cls or cls == "" then return nil end
    local s = string.gsub(string.gsub(cls, "、", "/"), ",", "/")
    local out = {}
    for seg in string.gmatch(s, "[^/]+") do
        seg = string.gsub(seg, "^%s*(.-)%s*$", "%1")
        if seg ~= "" then out[#out + 1] = seg end
    end
    if #out == 0 then return nil end
    return out
end
function DG.QClassLabel(cls)
    if not cls or cls == "" then return nil end
    local nm = L[cls] or cls
    if DG.QCLASS_TOKEN[cls] == "PALADIN" then
        nm = string.gsub(nm, "^圣", "")
        nm = string.gsub(nm, "^聖", "")
    end
    return nm
end

function DG.QuestOverviewClsBadge(n, cls)
    local b = n.clsB
    if not b then return end
    if not cls or cls == "" then
        b:Hide()
        return
    end
    local lab = DG.QClassLabel(cls) or cls
    b.lab:SetText(lab)
    local bw = (b.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2
    if bw < DG.Q_BADGE_MIN_W then bw = DG.Q_BADGE_MIN_W end
    if ns.hui and ns.hui.PaintSolidChip and b.__chipFill then
        ns.hui.PaintSolidChip(b, lab, DG.QClassColor(cls), bw)
    else
        b:SetWidth(bw)
        DG.BadgeTint(b, DG.QClassColor(cls))
    end
    b:ClearAllPoints()
    b:SetPoint("TOPLEFT", n.posB, "TOPRIGHT", 3, 0)
    b:Show()
end

function DG.QuestShare(id)
    if not id then return false end
    local v = DG.QLCall("IsPushableQuest", id)
    if v ~= nil then return v == true end
    return (ns.DungeonQuestShare and ns.DungeonQuestShare[id]) and true or false
end

function DG.QuestMapName(s)
    if not s or s == "" then return s end
    s = s:gsub("%s*[%d%.]+%s*,%s*[%d%.]+%s*$", "")
    s = s:gsub("%s*%-%s*[^%-]*$", "")
    return s
end

function DG.ZoneShort(s)
    if type(s) ~= "string" or s == "" then return s end
    local head, rest = s:match("^(.-)%s*%-%s*(.+)$")
    if not head or head == "" then return s end
    local c = rest:match("([%d%.]+%s*,%s*[%d%.]+)$")
    if not c then return s end
    return head .. " " .. c
end

function DG.LocText(mapID, x, y, fb)
    local z = DG.ZoneLabel(mapID, fb)
    if z and z ~= "" and x and y then
        return z .. format(" %.1f,%.1f", x, y)
    end
    return nil
end

function DG.StartLoc(qid, npcID)
    local t = ns.DungeonQuestStartLoc
    local r = t and t[qid]
    if not r then return nil end
    if npcID and r[1] and tonumber(r[1]) ~= tonumber(npcID) then return nil end
    if r[3] and r[4] and r[5] then return r[3], r[4], r[5], r[6] end
    return nil
end

function DG.NodeLoc(qid, npcID, fb)
    local m, x, y, z = DG.StartLoc(qid, npcID)
    local t = m and DG.LocText(m, x, y, z)
    if t and t ~= "" then return t end
    return DG.ZoneShort(fb)
end

DG.BADGE_CAP_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\HUIPillCap"
DG.BADGE_CAP_W = 8

function DG.MakeBadge(parent, bg)
    local b
    if ns.hui and ns.hui.MakeSolidChip then
        b = ns.hui.MakeSolidChip(parent, nil, DG.Q_BADGE_H)
    else
        b = CreateFrame("Frame", nil, parent)
        b:SetSize(10, DG.Q_BADGE_H)
        local cw = DG.BADGE_CAP_W
        b.capL = b:CreateTexture(nil, "BACKGROUND")
        b.capL:SetTexture(DG.BADGE_CAP_TEX)
        b.capL:SetTexCoord(0, 0.5, 0, 1)
        b.capL:SetPoint("TOPLEFT", b, "TOPLEFT", 0, 0)
        b.capL:SetPoint("BOTTOMLEFT", b, "BOTTOMLEFT", 0, 0)
        b.capL:SetWidth(cw)
        b.capR = b:CreateTexture(nil, "BACKGROUND")
        b.capR:SetTexture(DG.BADGE_CAP_TEX)
        b.capR:SetTexCoord(0.5, 1, 0, 1)
        b.capR:SetPoint("TOPRIGHT", b, "TOPRIGHT", 0, 0)
        b.capR:SetPoint("BOTTOMRIGHT", b, "BOTTOMRIGHT", 0, 0)
        b.capR:SetWidth(cw)
        b.mid = b:CreateTexture(nil, "BACKGROUND")
        b.mid:SetColorTexture(1, 1, 1, 1)
        b.mid:SetPoint("TOPLEFT", b.capL, "TOPRIGHT", 0, 0)
        b.mid:SetPoint("BOTTOMRIGHT", b.capR, "BOTTOMLEFT", 0, 0)
        b.lab = MakeFS(b, DG.Q_BADGE_FS, C_WHITE, "CENTER")
        b.lab:SetPoint("CENTER", b, "CENTER", 0, 0.5)
    end
    local col = bg
    if not col then
        col = (ns.hui and ns.hui.layer and ns.hui.layer.L3) or { 0.12, 0.12, 0.13, 1 }
    end
    b.__huiCard = { fill = b.__chipFill or { b.capL, b.mid, b.capR }, border = b.__chipBorder or {} }
    DG.BadgeTint(b, col)
    b:Hide()
    return b
end

function DG.PlaceBadge(b, x, text, maxX)
    b.lab:SetText(text)
    local w = (b.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2
    local minW = DG.Q_BADGE_MIN_W
    if w < minW then w = minW end
    if maxX and x + w > maxX then
        b:Hide()
        return x
    end
    if ns.hui and ns.hui.PaintSolidChip and b.__chipFill then
        ns.hui.PaintSolidChip(b, text, b.__chipCol, w)
    else
        b:SetWidth(w)
    end
    b:ClearAllPoints()
    local host = b:GetParent()
    local nm = host and host.name
    local nh = nm and nm.GetStringHeight and nm:GetStringHeight() or 0
    if nh <= 0 then nh = DG.Q_FS_NAME end
    if nm then
        b:SetPoint("TOPLEFT", nm, "TOPLEFT", x - DG.Q_X_NAME, -(nh - DG.Q_BADGE_H) / 2)
    else
        b:SetPoint("TOPLEFT", host, "TOPLEFT", x, -(DG.Q_ROW_H - DG.Q_BADGE_H) / 2)
    end
    b:Show()
    return x + w + DG.Q_BADGE_GAP
end

function DG.BadgeTint(b, col)
    if not (b and col) then return end
    b.__chipCol = col
    if b.__chipFill and ns.hui and ns.hui.PaintSolidFill and ns.hui.ChipSolidBase then
        ns.hui.PaintSolidFill(b.__chipFill, ns.hui.ChipSolidBase(col))
        if b.__chipBorder then
            for _, tex in ipairs(b.__chipBorder) do
                tex:SetVertexColor(col[1], col[2], col[3])
                tex:SetAlpha(1)
            end
        end
        if b.t then b.t:SetTextColor(1, 1, 1) end
        return
    end
    local a = col[4] or 1
    if b.mid then
        b.mid:SetColorTexture(col[1], col[2], col[3], a)
        if b.capL then
            b.capL:SetVertexColor(col[1], col[2], col[3], a)
            b.capL.__huiGlass = { c = col }
        end
        if b.capR then b.capR:SetVertexColor(col[1], col[2], col[3], a) end
        return
    end
    local hc = b.__huiCard
    local fill = type(hc) == "table" and hc.fill or nil
    if type(fill) == "table" then
        for i = 1, #fill do
            local t = fill[i]
            if t and t.__huiGlass and ns.hui and ns.hui.GlassPaint then
                t.__huiGlass.c = col
                ns.hui.GlassPaint(t)
            end
        end
    elseif b.SetBackdropColor then
        b:SetBackdropColor(col[1], col[2], col[3], 1)
    end
end

function DG.ClsBadgeAt(r, i)
    local t = r.clsB
    if type(t) ~= "table" then
        t = {}
        r.clsB = t
    end
    local b = t[i]
    if not b then
        b = DG.MakeBadge(r, DG.Q_BADGE_CLS_BG)
        t[i] = b
    end
    return b
end

DG.__preDone = nil
function DG.BuildPreDone(list)
    local set = {}
    local function pres(id)
        local out = {}
        local row = DG.QuestRowByID(id)
        local q = row and row[9]
        if type(q) == "table" then
            for i = 1, #q do
                local v = tonumber(q[i])
                if v then out[#out + 1] = v end
            end
        end
        local pe = ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[id]
        if type(pe) == "table" then
            local v = tonumber(pe[1])
            if v then out[#out + 1] = v end
        end
        return out
    end
    local function walk(id, depth)
        if depth > 16 then return end
        local ps = pres(id)
        for i = 1, #ps do
            local pid = ps[i]
            if not set[pid] then
                set[pid] = true
                walk(pid, depth + 1)
            end
        end
    end
    if type(list) == "table" then
        for i = 1, #list do
            local id = list[i] and list[i][1]
            if type(id) == "number" and (DG.QuestDone(id) or DG.QuestActive(id)) then
                walk(id, 1)
            end
        end
    end
    DG.__preDone = set
    return set
end

function DG.QuestState(id)
    if DG.QuestDone(id) then return "done" end
    local pd = DG.__preDone
    if pd and pd[id] then return "done" end
    if DG.QuestActive(id) then return "active" end
    return "todo"
end

function DG.PlayerSide()
    local f = UnitFactionGroup and UnitFactionGroup("player")
    if f == "Alliance" then return "A" end
    if f == "Horde" then return "H" end
    return nil
end

function DG.QuestRows(d)
    local all = DG.QuestList(d)
    local n = #all
    local ps = DG.PlayerSide()
    if not ps or n == 0 then return all, n, nil end
    local keep, m, other = {}, 0, false
    for i = 1, n do
        local s = all[i][2]
        if not s or s == "" or s == ps then
            m = m + 1
            keep[m] = all[i]
        else
            other = true
        end
    end
    if m == 0 then return all, n, (other and "fallback" or nil) end
    return keep, m, (other and "filtered" or nil)
end

function DG.QuestList(d)
    local alias = ns.DungeonQuestAlias and ns.DungeonQuestAlias[d.id]
    if alias then
        DG.EnsureRowByID()
        local out = {}
        for i = 1, #alias do
            local r = DG.__rowByID[alias[i]]
            if r then out[#out + 1] = r end
        end
        return out
    end
    return (ns.DungeonQuests or {})[d.id] or {}
end

DG.__rowByID = nil
function DG.EnsureRowByID()
    if DG.__rowByID then return end
    local map, keys = {}, {}
    for k in pairs(ns.DungeonQuests or {}) do keys[#keys + 1] = k end
    table.sort(keys)
    for i = 1, #keys do
        for _, q in ipairs(ns.DungeonQuests[keys[i]]) do map[q[1]] = q end
    end
    DG.__rowByID = map
end

function DG.QuestRowByID(id)
    DG.EnsureRowByID()
    return DG.__rowByID[id]
end

DG.__followers = nil
function DG.QuestFollowers(id)
    if not DG.__followers then
        local ids = {}
        local function add(prevId, fid)
            if type(prevId) ~= "number" or type(fid) ~= "number" then return end
            local t = ids[prevId]
            if not t then
                t = {}
                ids[prevId] = t
            end
            for _, v in ipairs(t) do
                if v == fid then return end
            end
            t[#t + 1] = fid
        end
        for _, rows in pairs(ns.DungeonQuests or {}) do
            for _, q in ipairs(rows) do
                if type(q[9]) == "table" then
                    for _, seg in ipairs(q[9]) do
                        if type(seg) == "number" then add(seg, q[1]) end
                    end
                end
            end
        end
        for fid, pe in pairs(ns.DungeonQuestPreExtra or {}) do
            if type(pe) == "table" then add(pe[1], fid) end
        end
        for fid, info in pairs(ns.EnsureDungeonQuestExtInfo()) do
            if type(info) == "table" and type(info.pre) == "table" then
                for _, p in ipairs(info.pre) do add(p, fid) end
            end
        end
        for _, t in pairs(ids) do table.sort(t) end
        DG.__followers = ids
    end
    local out = {}
    local t = DG.__followers[id]
    if t then
        for _, fid in ipairs(t) do
            local row = DG.QuestRowByID(fid) or DG.ExtQuestRow(fid)
            if row then out[#out + 1] = row end
        end
    end
    return out
end

DG.Q_FAC_ICON = {
    A = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    H = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}
DG.Q_FAC_ICON_SZ = 16

DG.QLIST_SEL_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\DF_RowSelGrad496"

function DG.PaintQListRow(r, st)
    if not r then return end
    local hui = ns.hui
    local lv = hui and hui.layer
    local sel = (st == "sel")
    if r.__qlSt ~= st then
        r.__qlSt = st
        if hui and lv and hui.GlassPaint and r.__huiCard then
            local col = (st == "hover") and lv.L4 or lv.L2
            local bp = r.__huiCard
            for i = 1, #bp.fill do
                local t = bp.fill[i]
                if t and t.__huiGlass then
                    t.__huiGlass.c = col
                    hui.GlassPaint(t)
                end
            end
            if r.__hov then
                for i = 1, #r.__hov do r.__hov[i]:Hide() end
            end
            if hui.PaintRowSelect then hui.PaintRowSelect(r, sel, DG.QLIST_SEL_TEX) end
        elseif r.SetBackdropColor then
            local ac = (hui and hui.ACCENT) or { 1, 1, 1 }
            if sel then
                r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
                r:SetBackdropBorderColor(ac[1], ac[2], ac[3], 0.95)
            elseif st == "hover" then
                r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
                r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
            else
                r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
            end
        end
    end
    if r.sub then
        if sel then
            r.sub:SetTextColor(1, 1, 1, 1)
        else
            r.sub:SetTextColor(C_GREY[1], C_GREY[2], C_GREY[3], 1)
        end
    end
    if r.meta then
        local mc = r.__metaCol
        if sel and (mc == C_GREY or mc == C_DARKGREY) then
            r.meta:SetTextColor(1, 1, 1, 1)
        elseif mc then
            r.meta:SetTextColor(mc[1], mc[2], mc[3], 1)
        end
    end
end

function U:RenderDungeonQuests()
    local d = U.dungeonDetailCur
    local child, pool = U.dungeonQuestChild, U.dungeonQuestPool
    if not (d and child and pool) then return end
    DG.EnsureQuestLane()
    DG.EnsureQuestListener()
    local list = DG.QuestList(d)
    DG.BuildPreDone(list)
    DG.PrefetchQuestData(list)
    local nAll = #list

    local cnt = { all = nAll, A = 0, H = 0, todo = 0, done = 0 }
    local doneN = 0
    for i = 1, nAll do
        local s = list[i][2]
        if s == "A" or not s then cnt.A = cnt.A + 1 end
        if s == "H" or not s then cnt.H = cnt.H + 1 end
        if DG.QuestDone(list[i][1]) then doneN = doneN + 1 end
    end
    cnt.done = doneN
    cnt.todo = nAll - doneN

    local view = U.dungeonQView
    if view ~= "overview" then view = "list" end
    U.dungeonQView = view
    local side = U.dungeonQSide
    if side ~= "A" and side ~= "H" then
        local ps = DG.PlayerSide()
        side = (ps == "A" or ps == "H") and ps or "A"
    end
    U.dungeonQSide = side
    local status = U.dungeonQFilter or "all"

    local listKey = tostring(d.id) .. "|" .. tostring(side) .. "|" .. tostring(view) .. "|" .. tostring(status)
    local keepList = (listKey == U.dungeonQListKey)
        and (U.dungeonQuestScroll and U.dungeonQuestScroll:GetVerticalScroll() or 0) or 0
    U.dungeonQListKey = listKey

    for i = 1, #(U.dungeonFilterBtns or {}) do
        local bt = U.dungeonFilterBtns[i]
        if bt and i > 4 then
            bt.__mode, bt.__key = "quest", nil
            bt:Hide()
            if bt.__em then bt.__em:Hide() end
        elseif bt then
            local key, label, n, tex
            if i == 1 then
                key, label, n, tex = "A", DG.QSIDE_LABEL.A, cnt.A, DG.Q_FAC_ICON.A
            elseif i == 2 then
                key, label, n, tex = "H", DG.QSIDE_LABEL.H, cnt.H, DG.Q_FAC_ICON.H
            elseif i == 3 then
                key, label = "qov", L["总览"]
            else
                key, label = "qlist", L["列表"]
            end
            bt.__mode, bt.__key = "quest", key
            bt:SetWidth((i <= 2) and 84 or 42)
            if n then
                bt:SetText(label .. " " .. n)
            else
                bt:SetText(label)
            end
            local bfs = bt:GetFontString()
            if bfs then
                bfs:ClearAllPoints()
                if tex then
                    bfs:SetPoint("TOPLEFT", bt, "TOPLEFT", 26, 0)
                    bfs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)
                else
                    bfs:SetPoint("CENTER", bt, "CENTER", 0, 0)
                end
                bfs:SetJustifyH("CENTER")
            end
            if tex then
                bt.__em:SetTexture(tex)
                bt.__em:Show()
            else
                bt.__em:Hide()
            end
            bt:SetShown(true)
            local sel = (i == 3 and view == "overview") or (i == 4 and view == "list")
                or (i == 1 and side == "A") or (i == 2 and side == "H")
            ns.hui.SetButtonSelected(bt, sel)
            if bfs and not sel then
                if i == 1 then
                    bfs:SetTextColor(0.40, 0.62, 1.00, 1)
                elseif i == 2 then
                    bfs:SetTextColor(1.00, 0.36, 0.26, 1)
                else
                    bfs:SetTextColor(Unpack(C_GREY))
                end
            end
            if bfs then
                bfs:ClearAllPoints()
                if tex then
                    bfs:SetPoint("TOPLEFT", bt, "TOPLEFT", 26, 0)
                    bfs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)
                else
                    bfs:SetPoint("CENTER", bt, "CENTER", 0, 0)
                end
                bfs:SetJustifyH("CENTER")
            end
        end
    end

    if DG.__chromeOnly then return end

    if view == "overview" then
        U.dungeonQuestScroll:SetShown(false)
        U.dungeonQuestChild:SetShown(false)
        U.dungeonQDet:SetShown(true)
        U.dungeonQPlateL:SetShown(true)
        U.dungeonQPlateR:SetShown(true)
        if U.dungeonQListCard then U.dungeonQListCard:SetShown(false) end
        if U.dungeonQOverviewF then U.dungeonQOverviewF:SetShown(true) end
        if U.dungeonQOVCard then U.dungeonQOVCard:SetShown(true) end
        U.dungeonQListKey = nil
        DG.PaintQuestOverview(d)
        U:RenderQuestDetail()
        DG.UpdateQDetBar()
        return
    end
    if U.dungeonQOverviewF then U.dungeonQOverviewF:SetShown(false) end
    if U.dungeonQOVCard then U.dungeonQOVCard:SetShown(false) end
    if U.dungeonQOVFlowCard then U.dungeonQOVFlowCard:SetShown(false) end
    if U.dungeonQListCard then U.dungeonQListCard:SetShown(true) end
    U.dungeonQuestScroll:SetShown(true)
    U.dungeonQuestChild:SetShown(true)

    local nVis, doneVis = 0, 0
    for i = 1, nAll do
        local q = list[i]
        if q[2] == side or not q[2] then
            nVis = nVis + 1
            if DG.QuestDone(q[1]) then doneVis = doneVis + 1 end
        end
    end
    local seg = ""
    if side == DG.PlayerSide() then
        seg = L["（已按你的阵营筛选）"]
    else
        seg = format(L["（只看%s阵营任务）"], DG.QSIDE_LABEL[side] or side)
    end
    U.dungeonQuestSum:ClearAllPoints()
    U.dungeonQuestSum:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD, 2)
    U.dungeonQuestSum:SetText(format(L["已完成 %d / %d"], doneVis, nVis) .. seg)
    U.dungeonQuestSum:Hide()
    if U.dungeonQDoneTg then U.dungeonQDoneTg:SetChecked(status ~= "todo") end

    local groups = { { inside = false, rows = {} }, { inside = true, rows = {} } }
    for i = 1, nAll do
        local q = list[i]
        if q[2] == side or not q[2] then
            local key = q[8] and 2 or 1
            local st = DG.QuestState(q[1])
            local hit = true
            if status == "done" then hit = (st == "done")
            elseif status == "todo" then hit = (st ~= "done") end
            if hit then
                local g = groups[key]
                g.rows[#g.rows + 1] = q
            end
        end
    end

    local selOk = false
    for gi = 1, 2 do
        for _, q in ipairs(groups[gi].rows) do
            if q[1] == U.dungeonQuestSel then selOk = true break end
        end
        if selOk then break end
    end
    if not selOk and not U.dungeonQDetExt and not U.dungeonQFlow then
        local first = groups[1].rows[1] or groups[2].rows[1]
        U.dungeonQuestSel = first and first[1] or nil
    end

    DG.__vgen = (DG.__vgen or 0) + 1
    local hdr, rows = pool.hdr, pool.row
    local nH, nR, y = 0, 0, -4

    local flow = DG.CurQuestFlow(d)
    if flow then
        local c = DG.EnsureFlowCard(child)
        c:ClearAllPoints()
        c:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD + 4, y)
        c.name:SetText(L["副本任务总览"])
        local ico = flow.side and DG.Q_FAC_ICON[flow.side]
        if ico then
            c.fac:SetTexture(ico)
            c.fac:Show()
            c.name:SetPoint("LEFT", c, "LEFT", 10 + DG.Q_FAC_ICON_SZ + 6, 0)
        else
            c.fac:Hide()
            c.name:SetPoint("LEFT", c, "LEFT", 12, 0)
        end
        c.sub:SetText(L["点击查看详细副本任务流程"])
        DG.PaintQListRow(c, (U.dungeonQFlow == true) and "sel" or "norm")
        c:Show()
        y = y - DG.Q_ROW_H - DG.Q_GAP_Y
    elseif U.dungeonQFlowCard then
        U.dungeonQFlow = nil
        U.dungeonQFlowCard:Hide()
    end

    local function takeRow()
        nR = nR + 1
        local r = rows[nR]
        if not r then
            r = CreateFrame("Button", nil, child, "BackdropTemplate")
            r:SetSize(DG.Q_LIST_W - DG.Q_PAD * 2 - 8, DG.Q_ROW_H)
            r:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            HuiCardFX(r, 12, 2)
            r:EnableMouse(true)
            r:EnableMouseWheel(true)
            r:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)
            end)
            r:SetScript("OnClick", function()
                if r.__q then DG.OpenQuest(r.__q[1]) end
            end)
            r.em = r:CreateTexture(nil, "ARTWORK")
            r.em:SetSize(DG.Q_FAC_ICON_SZ, DG.Q_FAC_ICON_SZ)
            r.em:SetPoint("TOPLEFT", r, "TOPLEFT", 12 + (18 - DG.Q_FAC_ICON_SZ) / 2,
                          -(DG.Q_ROW_H - DG.Q_FAC_ICON_SZ) / 2)
            r.name = MakeFS(r, DG.Q_FS_NAME, C_TEXT, "LEFT")
            r.name:SetPoint("TOPLEFT", r, "TOPLEFT", DG.Q_X_NAME, -(DG.Q_ROW_H - DG.Q_FS_NAME) / 2 - 1)
            r.name:SetWidth(DG.Q_W_NAME)
            r.name:SetWordWrap(false)
            r.sub = MakeFS(r, DG.Q_FS_META, C_GREY, "LEFT")
            r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", DG.Q_X_LOC, -(DG.Q_ROW_H - DG.Q_FS_META) / 2 - 1)
            r.sub:SetWidth(DG.Q_W_LOC)
            r.sub:SetWordWrap(false)
            r.lv = MakeFS(r, DG.Q_FS_META, C_GREY, "LEFT")
            r.lv:SetPoint("TOPLEFT", r, "TOPLEFT", DG.Q_X_LV, -(DG.Q_ROW_H - DG.Q_FS_META) / 2 - 1)
            r.preB = DG.MakeBadge(r, DG.Q_BADGE_PRE_BG)
            r.shareB = DG.MakeBadge(r, DG.Q_BADGE_SHARE_BG)
            r.raceB = DG.MakeBadge(r, DG.Q_BADGE_RACE_BG)
            r.meta = MakeFS(r, DG.Q_FS_META, C_GREY, "RIGHT")
            r.meta:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -(DG.Q_ROW_H - DG.Q_FS_META) / 2 - 1)
            r:SetScript("OnEnter", function(self)
                U.dungeonQuestHover = self
                DG.PaintQListRow(self, self.__selNow and "sel" or "hover")
                if self.__q then DG.ShowQuestTip(self, self.__q) end
            end)
            r:SetScript("OnLeave", function(self)
                if U.dungeonQuestHover == self then U.dungeonQuestHover = nil end
                DG.PaintQListRow(self, self.__selNow and "sel" or "norm")
                GameTooltip:Hide()
            end)
            rows[nR] = r
        end
        return r
    end

    for gi = 1, 2 do
        local g = groups[gi]
        if #g.rows > 0 then
            nH = nH + 1
            local hd = hdr[nH]
            if not hd then
                hd = { name = MakeFS(child, DG.Q_FS_HDR, C_TEXT, "LEFT"),
                       cnt = MakeFS(child, DG.Q_FS_META, C_GREY, "RIGHT") }
                hdr[nH] = hd
            end
            hd.name:SetText(g.inside and L["副本内领取 / 交付"] or L["进本前先去接"])
            hd.name:ClearAllPoints()
            hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD + 4, y)
            hd.__vtop, hd.__vh, hd.__vgen = -y, DG.Q_HDR_H, DG.__vgen
            hd.name:Show()
            hd.cnt:SetText(format(L["%d 个"], #g.rows))
            hd.cnt:ClearAllPoints()
            hd.cnt:SetPoint("TOPRIGHT", child, "TOPRIGHT", -(DG.Q_PAD + 4), y - 1)
            hd.cnt:Show()
            y = y - DG.Q_HDR_H

            for i = 1, #g.rows do
                local q = g.rows[i]
                local r = takeRow()
                local st = DG.QuestState(q[1])
                local col = (st == "done" and C_GREEN) or (st == "active" and C_GOLD) or C_GREY
                local nm, hasName = DG.QuestName(q[1])
                local ftex = q[2] and DG.Q_FAC_ICON[q[2]] or nil
                if ftex then
                    r.em:SetTexture(ftex)
                    r.em:Show()
                else
                    r.em:Hide()
                end
                local clsList = DG.QClassList(q[15])
                r.name:SetText(nm)
                if not hasName then
                    r.name:SetTextColor(Unpack(C_GREY))
                elseif st == "done" then
                    r.name:SetTextColor(Unpack(C_GREEN))
                elseif st == "active" then
                    r.name:SetTextColor(Unpack(C_GOLD))
                else
                    r.name:SetTextColor(Unpack(C_TEXT))
                end
                r.name:Show()
                local loc = q[6] or ""
                if loc == "" and q[8] then loc = L["副本任务"] end
                r.sub:SetText(DG.QuestMapName(loc))
                r.sub:Show()
                if hasName and q[3] then
                    r.lv:SetText(format(L["%d 级可接"], q[3]))
                    r.lv:SetTextColor(Unpack(C_GOLD))
                    r.lv:Show()
                else
                    r.lv:Hide()
                end
                local bmax = DG.Q_X_LOC - 4
                local bx = DG.Q_X_NAME + (r.name:GetStringWidth() or 0) + DG.Q_BADGE_GAP
                local ci = 0
                if hasName and clsList then
                    for k = 1, #clsList do
                        local cnm = DG.QClassLabel(clsList[k])
                        if cnm then
                            ci = ci + 1
                            local cb = DG.ClsBadgeAt(r, ci)
                            DG.BadgeTint(cb, DG.QClassColor(clsList[k]))
                            bx = DG.PlaceBadge(cb, bx, cnm, bmax)
                        end
                    end
                end
                local cbs = r.clsB
                if type(cbs) == "table" then
                    for k = ci + 1, #cbs do cbs[k]:Hide() end
                end
                if hasName and q[9] then
                    bx = DG.PlaceBadge(r.preB, bx, L["前置"], bmax)
                else
                    r.preB:Hide()
                end
                if hasName and DG.QuestShare(q[1]) then
                    bx = DG.PlaceBadge(r.shareB, bx, L["可共享"], bmax)
                else
                    r.shareB:Hide()
                end
                if hasName then
                    local rtag = DG.QuestRaceTag(q[1])
                    if rtag then
                        DG.PlaceBadge(r.raceB, bx, rtag, bmax)
                    else
                        r.raceB:Hide()
                    end
                else
                    r.raceB:Hide()
                end
                r.meta:SetText(hasName and (DG.Q_STATUS_TAG[st] or "") or L["暂时没有客户端数据"])
                r.__metaCol = hasName and col or C_DARKGREY
                r.meta:SetTextColor(Unpack(r.__metaCol))
                r.meta:Show()
                r.__q = q
                r.__selNow = (q[1] == U.dungeonQuestSel)
                DG.PaintQListRow(r, r.__selNow and "sel" or "norm")
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD + 4, y - (i - 1) * (DG.Q_ROW_H + DG.Q_GAP_Y))
                r.__vtop, r.__vh, r.__vgen = -(y - (i - 1) * (DG.Q_ROW_H + DG.Q_GAP_Y)), DG.Q_ROW_H, DG.__vgen
                r:Show()
            end
            y = y - #g.rows * (DG.Q_ROW_H + DG.Q_GAP_Y) - DG.Q_GRP_GAP
        end
    end

    for i = nH + 1, #hdr do hdr[i].name:Hide(); hdr[i].cnt:Hide() end
    for i = nR + 1, #rows do rows[i]:Hide() end

    local note = U.dungeonQuestNote
    if nH == 0 then
        note:ClearAllPoints()
        note:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD, y)
        if nAll == 0 then
            note:SetText(L["本站资料里这个副本还没有任务清单，数据补上后会自动出现。"])
        else
            note:SetText(L["该分类下暂无任务。"])
        end
        note:Show()
        y = y - 26
    else
        note:Hide()
    end

    child:SetHeight(math.max(10, -y + 4))
    DG.ClampScroll(U.dungeonQuestScroll, child, keepList)
    DG.CullQuestRows()
    U:RenderQuestDetail()
end

function U:RefreshQuestRows()
    if not U.dungeonBuilt then return end
    if (U.dungeonTab or "loot") ~= "quest" then return end
    if not (U.dungeonDetail and U.dungeonDetail:IsShown()) then return end
    U:RenderDungeonQuests()
end

function DG.QuestStartNpc(qid)
    local t = ns.DungeonQuestStartNpc
    if not t then return nil end
    return t[qid]
end

function DG.QuestEndNpc(qid)
    local t = ns.DungeonQuestEndNpc
    if not t then return nil end
    return t[qid]
end

function DG.ZoneLabel(mapID, fb)
    if mapID and C_Map and C_Map.GetMapInfo then
        local ok, info = pcall(C_Map.GetMapInfo, mapID)
        if ok and info and type(info.name) == "string" and info.name ~= "" then
            return info.name
        end
    end
    return fb
end

local function MapUsable(mapID)
    if not (C_Map and C_Map.GetMapInfo) then return true end
    local ok, info = pcall(C_Map.GetMapInfo, mapID)
    return ok and info ~= nil
end

function DG.MarkNPC(npcID, locOverride)
    local ver = select(4, GetBuildInfo()) or 0
    if ver < 16000 or ver > 16999 then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)
        end
        return
    end
    local loc = locOverride or (ns.NPCLoc and ns.NPCLoc[npcID])
    if not loc then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, format(L["NPC #%d 未收录地图位置"], npcID), 1, 0.4, 0.4)
        end
        return
    end
    local mapID = loc[1]
    if not MapUsable(mapID) then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该位置的地图，无法标记"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint
        and (not C_Map.CanSetUserWaypointOnMap or pcall(C_Map.CanSetUserWaypointOnMap, mapID)) then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, loc[2] / 100, loc[3] / 100)
        if ok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    end
end

function DG.ShowNpcTip(owner, npcID, locOverride)
    if not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine(L["点击：在地图上标记该 NPC"], 1, 0.82, 0)
    local loc = locOverride or (ns.NPCLoc and ns.NPCLoc[npcID])
    if loc then
        GameTooltip:AddLine(format("%s %.1f, %.1f", tostring(loc[4] or ""), loc[2], loc[3]), 0.75, 0.75, 0.75)
    else
        GameTooltip:AddLine(L["未收录该 NPC 的地图位置"], 0.6, 0.6, 0.6)
    end
    GameTooltip:Show()
end

function DG.MarkEntrance(dungeonID)
    local ver = select(4, GetBuildInfo()) or 0
    if ver < 16000 or ver > 16999 then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)
        end
        return
    end
    local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]
    if not loc then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该副本的入口位置"], 1, 0.4, 0.4)
        end
        return
    end
    local mapID = loc[1]
    if not MapUsable(mapID) then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该位置的地图，无法标记"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint
        and (not C_Map.CanSetUserWaypointOnMap or pcall(C_Map.CanSetUserWaypointOnMap, mapID)) then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, loc[2] / 100, loc[3] / 100)
        if ok and pt then pcall(C_Map.SetUserWaypoint, pt) end
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

function DG.ShowEntranceTip(owner)
    if not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine(L["点击：在地图上标记副本入口"], 1, 0.82, 0)
    local d = U.dungeonDetailCur
    local loc = d and ns.DungeonEntry and ns.DungeonEntry[d.id]
    if loc then
        local route = d and ns.DungeonEntryRoute and ns.DungeonEntryRoute[d.id]
        GameTooltip:AddLine((route and (L["副本入口"] .. " ") or "") ..
            format("%s %.1f, %.1f", tostring(loc[4] or ""), loc[2], loc[3]), 0.75, 0.75, 0.75)
        if route then
            for i = 1, #route do
                local p = route[i]
                GameTooltip:AddLine(tostring(p[4] or "") .. " " .. tostring(p[5] or "") .. " " ..
                    format("%.1f, %.1f", p[2], p[3]), 0.6, 0.6, 0.6)
            end
        end
    else
        GameTooltip:AddLine(L["未收录该副本的入口位置"], 0.6, 0.6, 0.6)
    end
    GameTooltip:Show()
end

function DG.EntrancePoints(dungeonID)
    local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]
    if not loc then return nil end
    local pts = { { mapID = loc[1], x = loc[2], y = loc[3], label = nil, mapName = loc[4] } }
    local route = dungeonID and ns.DungeonEntryRoute and ns.DungeonEntryRoute[dungeonID]
    if route then
        for i = 1, #route do
            local p = route[i]
            pts[#pts + 1] = { mapID = p[1], x = p[2], y = p[3], label = p[4], mapName = p[5] }
        end
    end
    return pts
end

function DG.MarkEntranceAt(dungeonID, idx)
    local ver = select(4, GetBuildInfo()) or 0
    if ver < 16000 or ver > 16999 then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)
        end
        return
    end
    local pts = DG.EntrancePoints(dungeonID)
    local p = pts and pts[idx or 1]
    if not p then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该副本的入口位置"], 1, 0.4, 0.4)
        end
        return
    end
    if not MapUsable(p.mapID) then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该位置的地图，无法标记"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint
        and (not C_Map.CanSetUserWaypointOnMap or pcall(C_Map.CanSetUserWaypointOnMap, p.mapID)) then
        local ok, wp = pcall(UiMapPoint.CreateFromCoordinates, p.mapID, p.x / 100, p.y / 100)
        if ok and wp then pcall(C_Map.SetUserWaypoint, wp) end
        if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
            pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, p.mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, p.mapID)
    end
end

function DG.ShowEntrancePointTip(owner, idx)
    if not GameTooltip then return end
    local d = U.dungeonDetailCur
    local pts = d and DG.EntrancePoints(d.id)
    local p = pts and pts[idx or 1]
    if not p then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine(L["点击：在地图上标记此点"], 1, 0.82, 0)
    GameTooltip:AddLine(tostring(p.label or L["副本入口"]) .. " " .. tostring(p.mapName or "") .. " " ..
        format("%.1f, %.1f", p.x, p.y), 0.75, 0.75, 0.75)
    GameTooltip:Show()
end

function DG.QuestFlow(d)
    local t = ns.EnsureDungeonQuestFlow and ns.EnsureDungeonQuestFlow()
    if not t or not d then return nil end
    local f = t[d.id]
    if not f then return nil end
    if type(f.sec) == "table" and #f.sec > 0 then return f end
    if type(f.secA) == "table" or type(f.secH) == "table" then return f end
    return nil
end

function DG.CurQuestFlow(d)
    local f = DG.QuestFlow(d)
    if not f then return nil end
    local vs = U.dungeonQSide
    if vs ~= "A" and vs ~= "H" then vs = DG.PlayerSide() end
    if vs ~= "A" and vs ~= "H" then vs = "A" end
    local alt = f["sec" .. vs]
    if type(alt) == "table" and #alt > 0 then
        return { side = vs, sec = alt }
    end
    if f.secA or f.secH then return nil end
    if not f.side then return f end
    if f.side ~= vs then return nil end
    return f
end

function DG.FlowQuestRow(id)
    if not id then return nil end
    DG.EnsureRowByID()
    local r = DG.__rowByID and DG.__rowByID[id]
    if r then return r end
    local list = DG.QuestList(U.dungeonDetailCur)
    for i = 1, #list do
        if list[i][1] == id then return list[i] end
    end
    return nil
end

function DG.FlowQuestStub(id)
    if not id then return nil end
    local ext = ns.EnsureDungeonQuestExtInfo and ns.EnsureDungeonQuestExtInfo()
    local e = ext and ext[id]
    local row = {}
    row[1] = id
    if e then
        row[3] = e.lv
        row[5] = e.npc
        row[6] = e.zone
        row[16] = e.npcid
        row[17] = e.npc
    end
    return row
end

function DG.OpenQuest(id)
    if not id then return end
    local row = DG.FlowQuestRow(id)
    U.dungeonQFlow = nil
    U.dungeonQuestSel = nil
    U.dungeonQDetExt = nil
    if row then
        U.dungeonQuestSel = id
    else
        local ext = ns.EnsureDungeonQuestExtInfo and ns.EnsureDungeonQuestExtInfo()
        if ext and ext[id] then
            U.dungeonQDetExt = id
        else
            U.dungeonQuestSel = id
        end
    end
    U:RenderDungeonQuests()
    if ns.PlaySound then ns.PlaySound(1) end
end

function DG.HideFlowRows(pool)
    if not pool then return end
    local i
    for i = 1, #pool.fLab do pool.fLab[i]:Hide() end
    for i = 1, #pool.fTxt do pool.fTxt[i]:Hide() end
    for i = 1, #pool.fLink do pool.fLink[i]:Hide() end
    for i = 1, #pool.fNum do
        pool.fNum[i].ic:Hide()
        pool.fNum[i].fs:Hide()
    end
    pool.nFLab, pool.nFTxt, pool.nFLink, pool.nFNum = 0, 0, 0, 0
end

function DG.HideDetailRows(pool)
    if not pool then return end
    local i
    for i = 1, #pool.lab do pool.lab[i]:Hide() end
    for i = 1, #pool.kv do pool.kv[i]:Hide() end
    for i = 1, #pool.txt do pool.txt[i]:Hide() end
    for i = 1, #pool.node do pool.node[i]:Hide() end
    for i = 1, #pool.chip do pool.chip[i]:Hide() end
    for i = 1, #pool.npc do pool.npc[i]:Hide() end
    pool.nLab, pool.nKv, pool.nTxt, pool.nNode, pool.nChip, pool.nNpc = 0, 0, 0, 0, 0, 0
    if U.dungeonQDetName then U.dungeonQDetName:Hide() end
    if U.dungeonQDetSt then U.dungeonQDetSt:Hide() end
end

function DG.FlowTakeTxt(child, pool)
    pool.nFTxt = pool.nFTxt + 1
    local i = pool.nFTxt
    local f = pool.fTxt[i]
    if not f then
        f = MakeFS(child, DG.Q_FS_DET, C_TEXT, "LEFT")
        f:SetWordWrap(false)
        pool.fTxt[i] = f
    end
    f:Show()
    return f
end

function DG.FlowTakeLink(child, pool)
    pool.nFLink = pool.nFLink + 1
    local i = pool.nFLink
    local b = pool.fLink[i]
    if not b then
        b = CreateFrame("Button", nil, child)
        b:EnableMouse(true)
        b:EnableMouseWheel(true)
        b:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(U.dungeonQDet, U.dungeonQDetChild, delta)
        end)
        b.fs = MakeFS(b, DG.Q_FS_DET, C_TEXT, "LEFT")
        b.fs:SetPoint("TOPLEFT", b, "TOPLEFT", 0, -3)
        b.fs:SetWordWrap(false)
        b.ic = b:CreateTexture(nil, "ARTWORK")
        b.ic:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        b.ic:SetSize(DG.Q_FLOW_MARK, DG.Q_FLOW_MARK)
        b.ic:SetPoint("LEFT", b, "LEFT", 0, 0)
        b.ic:Hide()
        b.icT = b:CreateTexture(nil, "OVERLAY")
        b.icT:SetAllPoints(b.ic)
        b.icT:Hide()
        b:SetScript("OnEnter", function(self)
            self.fs:SetTextColor(1, 1, 1, 1)
            if self.__npc then
                DG.ShowNpcTip(self, self.__npc)
            elseif self.__q then
                DG.ShowQuestTip(self, DG.FlowQuestRow(self.__q) or DG.FlowQuestStub(self.__q))
            elseif self.__item then
                DG.ShowItemTip(self, { self.__item })
            end
        end)
        b:SetScript("OnLeave", function(self)
            local c = self.__col or C_TEXT
            self.fs:SetTextColor(c[1], c[2], c[3], 1)
            GameTooltip:Hide()
        end)
        b:SetScript("OnClick", function(self)
            if self.__npc then
                DG.MarkNPC(self.__npc)
            elseif self.__q then
                DG.OpenQuest(self.__q)
            end
        end)
        pool.fLink[i] = b
    end
    b:Show()
    return b
end

local function FlowWrapLines(fs, size)
    local h = fs:GetStringHeight() or size
    return math.max(1, math.ceil(h / size))
end

function DG.FlowMark(b, st, col)
    if not b or not b.ic then return end
    if st and col then
        b.ic:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        b.ic:SetVertexColor(col[1], col[2], col[3], 1)
        b.icT:SetTexture(DG.Q_MARK_SYM[st] or DG.Q_MARK_SYM.todo)
        local k = DG.Q_MARK_INK[st]
        if k then b.icT:SetVertexColor(k[1], k[2], k[3], 1) else b.icT:SetVertexColor(1, 1, 1, 1) end
        b.ic:Show()
        b.icT:Show()
    else
        b.ic:Hide()
        b.icT:Hide()
    end
end

function DG.FlowLine(child, pool, seg, x0, xEnd, y)
    local cx = x0
    for k = 1, #seg do
        local tk = seg[k]
        local tw
        if tk.n or tk.q or tk.i then
            local b = DG.FlowTakeLink(child, pool)
            local col, txt, icx, ob = C_LINK_NPC, nil, 0, nil
            if tk.n then
                txt = tk.n
                b.__npc, b.__q, b.__item = tk.id, nil, nil
                DG.FlowMark(b, nil)
            elseif tk.i then
                local inm, inHas = DG.ItemName(tk.id)
                if not inHas or not inm or inm == "" then inm = tk.i end
                local iq = DG.QualOf(tk.id)
                if type(iq) == "number" and iq >= 2 then
                    col = { DG.QColor(iq) }
                else
                    col = DG.Q_LINK_ITEM
                end
                b.__npc, b.__q, b.__item = nil, nil, tk.id
                DG.FlowMark(b, nil)
                b.ic:SetTexture(DG.ItemIcon(tk.id))
                b.ic:SetVertexColor(1, 1, 1, 1)
                b.ic:Show()
                txt = format("「%s%s」", DG.Q_FLOW_IDEO, inm)
                ob = "「"
            else
                local nm, hasName = DG.QuestName(tk.id)
                if not hasName or not nm or nm == "" then nm = tk.q end
                col = C_LINK_Q
                b.__npc, b.__q, b.__item = nil, tk.id, nil
                if hasName then
                    local st = DG.QuestState(tk.id)
                    local mc = (st == "done" and C_GREEN) or (st == "active" and C_GOLD) or C_GREY
                    DG.FlowMark(b, st, mc)
                    txt = format("《%s%s》", DG.Q_FLOW_IDEO, nm)
                    ob = "《"
                else
                    DG.FlowMark(b, nil)
                    txt = format("《%s》", nm)
                end
            end
            b.__col = col
            b.fs:ClearAllPoints()
            b.fs:SetPoint("TOPLEFT", b, "TOPLEFT", 0, -3)
            b.fs:SetWidth(0)
            b.fs:SetWordWrap(false)
            if ob and b.ic:IsShown() then
                b.fs:SetText(ob)
                icx = b.fs:GetStringWidth() or 0
            end
            b.ic:ClearAllPoints()
            b.ic:SetPoint("LEFT", b, "LEFT", icx, 0)
            b.fs:SetText(txt)
            b.fs:SetTextColor(Unpack(col))
            tw = b.fs:GetStringWidth() or 0
            if cx + tw > xEnd and cx > x0 then
                y = y - DG.Q_FLOW_H
                cx = x0
            end
            local avail = xEnd - cx
            b:ClearAllPoints()
            b:SetPoint("TOPLEFT", child, "TOPLEFT", cx, y)
            if tw > avail then
                local fw = avail
                if fw < 10 then fw = 10 end
                b.fs:SetWidth(fw)
                b.fs:SetWordWrap(true)
                local lns = FlowWrapLines(b.fs, DG.Q_FS_DET)
                b:SetSize(avail, lns * DG.Q_FLOW_H)
                y = y - (lns - 1) * DG.Q_FLOW_H
                cx = xEnd
            else
                b:SetSize(tw, DG.Q_FLOW_H)
                cx = cx + tw
            end
        else
            local f = DG.FlowTakeTxt(child, pool)
            f:SetWidth(0)
            f:SetWordWrap(false)
            f:SetText(tk.t or "")
            tw = f:GetStringWidth() or 0
            if cx + tw > xEnd and cx > x0 then
                y = y - DG.Q_FLOW_H
                cx = x0
            end
            local avail = xEnd - cx
            f:ClearAllPoints()
            f:SetPoint("TOPLEFT", child, "TOPLEFT", cx, y - 3)
            if tw > avail then
                f:SetWidth(avail)
                f:SetWordWrap(true)
                local lns = FlowWrapLines(f, DG.Q_FS_DET)
                y = y - (lns - 1) * DG.Q_FLOW_H
                cx = xEnd
            else
                cx = cx + tw
            end
        end
    end
    return y - DG.Q_FLOW_H
end

function DG.RenderQuestFlow(child, pool, d, keep)
    local flow = DG.CurQuestFlow(d)
    if not flow then return end
    local xEnd = DG.Q_DET_W - 16
    local y = -DG.Q_PAD
    pool.nFLab, pool.nFTxt, pool.nFLink, pool.nFNum = 0, 0, 0, 0
    for si = 1, #flow.sec do
        local sec = flow.sec[si]
        pool.nFLab = pool.nFLab + 1
        local li = pool.nFLab
        local lab = pool.fLab[li]
        if not lab then
            lab = MakeFS(child, DG.Q_FS_DET, C_GOLD, "LEFT")
            lab:SetWordWrap(false)
            pool.fLab[li] = lab
        end
        lab:SetText(sec.hd)
        lab:ClearAllPoints()
        lab:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
        lab:Show()
        y = y - DG.Q_FLOW_H
        for i = 1, #(sec.st or {}) do
            pool.nFNum = pool.nFNum + 1
            local ni = pool.nFNum
            local num = pool.fNum[ni]
            if not num then
                num = {}
                num.ic = child:CreateTexture(nil, "ARTWORK")
                num.ic:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
                num.ic:SetSize(DG.Q_FLOW_DOT, DG.Q_FLOW_DOT)
                num.ic:SetVertexColor(0.22, 0.25, 0.30, 1)
                num.fs = MakeFS(child, 12, C_GREY, "CENTER")
                num.fs:SetSize(DG.Q_FLOW_DOT, DG.Q_FLOW_DOT)
                pool.fNum[ni] = num
            end
            num.ic:ClearAllPoints()
            num.ic:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y - 2)
            num.ic:Show()
            num.fs:ClearAllPoints()
            num.fs:SetPoint("CENTER", num.ic, "CENTER", 0, 0)
            num.fs:SetText(tostring(i))
            num.fs:Show()
            y = DG.FlowLine(child, pool, sec.st[i], DG.Q_FLOW_DOT + 6, xEnd, y)
            y = y - DG.Q_FLOW_ST_GAP
        end
        y = y - DG.Q_FLOW_SEC_GAP
    end
    local i
    for i = pool.nFLab + 1, #pool.fLab do pool.fLab[i]:Hide() end
    for i = pool.nFTxt + 1, #pool.fTxt do pool.fTxt[i]:Hide() end
    for i = pool.nFLink + 1, #pool.fLink do pool.fLink[i]:Hide() end
    for i = pool.nFNum + 1, #pool.fNum do
        pool.fNum[i].ic:Hide()
        pool.fNum[i].fs:Hide()
    end
    child:SetHeight(math.max(10, -y + 12))
    DG.ClampScroll(U.dungeonQDet, child, keep)
    DG.UpdateQDetBar()
end

function DG.EnsureFlowCard(child)
    if U.dungeonQFlowCard then return U.dungeonQFlowCard end
    local c = CreateFrame("Button", nil, child, "BackdropTemplate")
    c:SetSize(DG.Q_LIST_W - DG.Q_PAD * 2 - 8, DG.Q_ROW_H)
    c:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    HuiCardFX(c, 12, 2)
    c:EnableMouse(true)
    c:EnableMouseWheel(true)
    c:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)
    end)
    c:SetScript("OnClick", function()
        U.dungeonQFlow = true
        U.dungeonQuestSel = nil
        U.dungeonQDetExt = nil
        U.dungeonQView = "list"
        U:RenderDungeonQuests()
        if ns.PlaySound then ns.PlaySound(1) end
    end)
    c:SetScript("OnEnter", function(self)
        DG.PaintQListRow(self, (U.dungeonQFlow == true) and "sel" or "hover")
    end)
    c:SetScript("OnLeave", function(self)
        DG.PaintQListRow(self, (U.dungeonQFlow == true) and "sel" or "norm")
    end)
    c.fac = c:CreateTexture(nil, "ARTWORK")
    c.fac:SetSize(DG.Q_FAC_ICON_SZ, DG.Q_FAC_ICON_SZ)
    c.fac:SetPoint("LEFT", c, "LEFT", 10, 0)
    c.name = MakeFS(c, DG.Q_FS_NAME, C_TEXT, "LEFT")
    c.name:SetPoint("LEFT", c, "LEFT", 10 + DG.Q_FAC_ICON_SZ + 6, 0)
    c.name:SetWidth(200)
    c.name:SetWordWrap(false)
    c.sub = MakeFS(c, 14, C_GREY, "RIGHT")
    c.sub:SetPoint("RIGHT", c, "RIGHT", -10, 0)
    c.sub:SetWidth(240)
    c.sub:SetWordWrap(false)
    U.dungeonQFlowCard = c
    return c
end

function DG.PaintOVFlowCard(st)
    local c = U.dungeonQOVFlowCard
    if not c then return end
    if c.__ovSt == st then return end
    c.__ovSt = st
    local hui = ns.hui
    local lv = hui and hui.layer
    if not (hui and lv and hui.GlassPaint and c.__huiCard) then
        if st == "sel" then
            c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
            c:SetBackdropBorderColor(1, 0.82, 0, 0.9)
        else
            c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
            c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
        end
        return
    end
    local ACC = hui.ACCENT
    local col
    if st == "sel" then
        col = {
            lv.L2[1] + (ACC[1] - lv.L2[1]) * 0.28,
            lv.L2[2] + (ACC[2] - lv.L2[2]) * 0.28,
            lv.L2[3] + (ACC[3] - lv.L2[3]) * 0.28,
            1,
        }
    elseif st == "hover" then
        col = lv.L4
    else
        col = lv.L2
    end
    local bp = c.__huiCard
    for i = 1, #bp.fill do
        local t = bp.fill[i]
        if t and t.__huiGlass then
            t.__huiGlass.c = col
            hui.GlassPaint(t)
        end
    end
    if c.__hov then
        for i = 1, #c.__hov do c.__hov[i]:Hide() end
    end
    if hui.PaintRowSelect then
        hui.PaintRowSelect(c, st == "sel")
        if c.__huiRowSelTex then c.__huiRowSelTex:Hide() end
    end
    if c.name then
        if st == "sel" then
            c.name:SetTextColor(1, 1, 1, 1)
        else
            c.name:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3], 1)
        end
    end
end

function DG.SyncOverviewFlowCard()
    local c = U.dungeonQOVFlowCard
    if not c or not c:IsShown() then return end
    DG.PaintOVFlowCard((U.dungeonQFlow == true) and "sel" or "norm")
end

function DG.EnsureOVFlowCard(canvas)
    if U.dungeonQOVFlowCard then return U.dungeonQOVFlowCard end
    local c = CreateFrame("Button", nil, canvas, "BackdropTemplate")
    c:SetSize(DG.Q_OV_W, DG.Q_OV_H)
    c:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    HuiCardFX(c, 12, 2)
    c:EnableMouse(true)
    c:EnableMouseWheel(true)
    c:SetScript("OnMouseWheel", function(_, delta)
        if U.dungeonQOVWheel then U.dungeonQOVWheel(delta) end
    end)
    c:SetScript("OnClick", function()
        U.dungeonQFlow = true
        U.dungeonQuestSel = nil
        U.dungeonQDetExt = nil
        U:RenderQuestDetail()
        DG.SyncOverviewFlowCard()
        if ns.PlaySound then ns.PlaySound(1) end
    end)
    c:SetScript("OnEnter", function()
        DG.PaintOVFlowCard((U.dungeonQFlow == true) and "sel" or "hover")
    end)
    c:SetScript("OnLeave", function()
        DG.SyncOverviewFlowCard()
    end)
    c.fac = c:CreateTexture(nil, "ARTWORK")
    c.fac:SetSize(DG.Q_FAC_ICON_SZ, DG.Q_FAC_ICON_SZ)
    c.fac:SetPoint("LEFT", c, "LEFT", 6, 0)
    c.name = MakeFS(c, DG.Q_FS_NAME, C_TEXT, "LEFT")
    c.name:SetWordWrap(false)
    c.sub = MakeFS(c, 12, C_GREY, "LEFT")
    c.sub:SetWordWrap(false)
    U.dungeonQOVFlowCard = c
    return c
end

function DG.PaintOverviewFlow(d, canvas, x, w)
    local flow = DG.CurQuestFlow(d)
    local c = U.dungeonQOVFlowCard
    if not flow then
        if c then c:Hide() end
        return
    end
    if not c then c = DG.EnsureOVFlowCard(canvas) end
    c:ClearAllPoints()
    c:SetPoint("TOPLEFT", canvas, "TOPLEFT", x, 0)
    c:SetSize(w, DG.Q_OV_H)
    local nx = 6
    local ico = flow.side and DG.Q_FAC_ICON[flow.side]
    if ico then
        c.fac:SetTexture(ico)
        c.fac:Show()
        nx = nx + DG.Q_FAC_ICON_SZ + 4
    else
        c.fac:Hide()
    end
    c.name:ClearAllPoints()
    c.name:SetPoint("TOPLEFT", c, "TOPLEFT", nx, -5)
    c.name:SetWidth(w - nx - 6)
    c.name:SetText(L["副本任务总览"])
    c.sub:ClearAllPoints()
    c.sub:SetPoint("TOPLEFT", c, "TOPLEFT", nx, -25)
    c.sub:SetWidth(w - nx - 6)
    c.sub:SetText(L["点击查看详细副本任务流程"])
    c:Show()
    DG.SyncOverviewFlowCard()
end

function U:RenderQuestDetail()
    local d = U.dungeonDetailCur
    local child, pool = U.dungeonQDetChild, U.dungeonQDetPool
    if not (d and child and pool) then return end
    local detW = DG.Q_DET_W

    local flow = U.dungeonQFlow and DG.CurQuestFlow(d) or nil
    local detKey
    if flow then
        detKey = "F:" .. tostring(d.id) .. ":" .. tostring(flow.side or "-")
    elseif U.dungeonQDetExt then
        detKey = "E:" .. tostring(U.dungeonQDetExt) .. ":" .. tostring(d.id)
    else
        detKey = "Q:" .. tostring(U.dungeonQuestSel) .. ":" .. tostring(d.id)
    end
    local keepDet = (detKey == U.dungeonQDetKey)
        and (U.dungeonQDet and U.dungeonQDet:GetVerticalScroll() or 0) or 0
    U.dungeonQDetKey = detKey

    if flow then
        DG.HideDetailRows(pool)
        DG.RenderQuestFlow(child, pool, d, keepDet)
        DG.SyncOverviewFlowCard()
        return
    end
    U.dungeonQFlow = nil
    DG.HideFlowRows(pool)
    DG.SyncOverviewFlowCard()

    local q
    local qlist = DG.QuestList(d)
    DG.BuildPreDone(qlist)
    for _, row in ipairs(qlist) do
        if row[1] == U.dungeonQuestSel then q = row end
    end
    if U.dungeonQDetExt then q = DG.ExtQuestRow(U.dungeonQDetExt) end

    pool.nLab, pool.nKv, pool.nTxt, pool.nNode, pool.nChip, pool.nNpc = 0, 0, 0, 0, 0, 0
    local y = -DG.Q_PAD

    local MARK_SYM = DG.Q_MARK_SYM
    local MARK_SYM_INK = DG.Q_MARK_INK
    local function rowMark(r, st, col)
        if not r.ic then return end
        if st and col then
            r.ic:SetVertexColor(col[1], col[2], col[3], 1)
            r.icT:SetTexture(MARK_SYM[st] or MARK_SYM.todo)
            local k = MARK_SYM_INK[st]
            if k then
                r.icT:SetVertexColor(k[1], k[2], k[3], 1)
            else
                r.icT:SetVertexColor(1, 1, 1, 1)
            end
            r.ic:Show()
            r.icT:Show()
        else
            r.ic:Hide()
            r.icT:Hide()
        end
    end
    local function takeLab()
        pool.nLab = pool.nLab + 1
        local i = pool.nLab
        local f = pool.lab[i]
        if not f then
            f = MakeFS(child, 14, C_GREY, "LEFT")
            pool.lab[i] = f
        end
        return f
    end
    local function takeKv()
        pool.nKv = pool.nKv + 1
        local i = pool.nKv
        local f = pool.kv[i]
        if not f then
            f = MakeFS(child, DG.Q_FS_DET, C_TEXT, "LEFT")
            f:SetWidth(detW - 8)
            f:SetWordWrap(false)
            pool.kv[i] = f
        end
        return f
    end
    local function takeNpc()
        pool.nNpc = pool.nNpc + 1
        local i = pool.nNpc
        local f = pool.npc[i]
        if not f then
            f = CreateFrame("Button", nil, child)
            f:SetSize(detW, 24)
            f:EnableMouse(true)
            f:EnableMouseWheel(true)
            f:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(U.dungeonQDet, U.dungeonQDetChild, delta)
            end)
            f.fs = MakeFS(f, DG.Q_FS_DET, C_TEXT, "LEFT")
            f.fs:SetWidth(detW - 76)
            f.fs:SetWordWrap(false)
            f.fs:SetPoint("TOPLEFT", f, "TOPLEFT", 0, 0)
            local mb = NewButton(f, L["地图"], 68, 24, 14)
            AddBtnIcon(mb, "EntryPin", 14, 5)
            mb:SetPoint("RIGHT", f.fs, "RIGHT", 74, 0)
            mb:SetScript("OnClick", function(self)
                local p = self:GetParent()
                if p.__npc then DG.MarkNPC(p.__npc, p.__loc) end
            end)
            mb:SetScript("OnEnter", function(self)
                local p = self:GetParent()
                if p.__npc then DG.ShowNpcTip(self, p.__npc, p.__loc) end
            end)
            mb:SetScript("OnLeave", function() GameTooltip:Hide() end)
            f.mark = mb
            pool.npc[i] = f
        end
        return f
    end
    local function takeTxt()
        pool.nTxt = pool.nTxt + 1
        local i = pool.nTxt
        local f = pool.txt[i]
        if not f then
            f = MakeFS(child, DG.Q_FS_DET, C_TEXT, "LEFT")
            f:SetWidth(detW - 8)
            pool.txt[i] = f
        end
        return f
    end
    local function takeNode()
        pool.nNode = pool.nNode + 1
        local i = pool.nNode
        local r = pool.node[i]
        if not r then
            r = CreateFrame("Button", nil, child, "BackdropTemplate")
            r:SetSize(detW, 38)
            r:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            HuiCardFX(r, 10, 2)
            r:EnableMouse(true)
            r:EnableMouseWheel(true)
            r:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(U.dungeonQDet, U.dungeonQDetChild, delta)
            end)
            r:SetScript("OnEnter", function(self)
                if not HuiCardState(self, "hover") then
                    self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
                    self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
                end
                if self.__q then DG.ShowQuestTip(self, self.__q) end
            end)
            r:SetScript("OnLeave", function(self)
                if not HuiCardState(self, "norm") then
                    self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                    self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
                end
                GameTooltip:Hide()
            end)
            r:SetScript("OnClick", function(self)
                if self.__npc then DG.MarkNPC(self.__npc, self.__loc) end
            end)
            r.name = MakeFS(r, 14, C_TEXT, "LEFT")
            r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -3)
            r.name:SetWidth(detW - 126)
            r.name:SetWordWrap(false)
            r.st = MakeFS(r, 14, C_GREY, "RIGHT")
            r.st:SetPoint("TOPRIGHT", r, "TOPRIGHT", -26, -3)
            r.ic = r:CreateTexture(nil, "ARTWORK")
            r.ic:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
            r.ic:SetSize(DG.Q_BADGE_H, DG.Q_BADGE_H)
            r.ic:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -4)
            r.ic:Hide()
            r.icT = r:CreateTexture(nil, "OVERLAY")
            r.icT:SetAllPoints(r.ic)
            r.icT:Hide()
            r.sub = MakeFS(r, 12, C_GREY, "LEFT")
            r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -23)
            r.sub:SetWidth(detW - 18)
            r.sub:SetWordWrap(false)
            pool.node[i] = r
        end
        if not r.__huiCard then
            r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
            r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
        end
        return r
    end
    local function takeChip()
        pool.nChip = pool.nChip + 1
        local i = pool.nChip
        local r = pool.chip[i]
        if not r then
            r = CreateFrame("Button", nil, child, "BackdropTemplate")
            r:SetSize(detW, 44)
            r:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            if not r.__huiCard then HuiCardFX(r, 6, 2) end
            r:EnableMouse(true)
            r:EnableMouseWheel(true)
            r:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(U.dungeonQDet, U.dungeonQDetChild, delta)
            end)
            r:SetScript("OnEnter", function(self)
                if not HuiCardState(self, "hover") then
                    self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
                    self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
                end
                if self.__it then DG.ShowItemTip(self, self.__it) end
            end)
            r:SetScript("OnLeave", function(self)
                if not HuiCardState(self, "norm") then
                    self:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                    self:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
                end
                GameTooltip:Hide()
            end)
            r:SetScript("OnClick", function(self, button) DG.ItemShiftClick(self, button) end)
            r.icon = r:CreateTexture(nil, "ARTWORK")
            r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
            r.icon:SetSize(32, 32)
            r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
            r.name = MakeFS(r, DG.Q_FS_DET, C_TEXT, "LEFT")
            r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 46, -6)
            r.name:SetWidth(detW - 46 - 8)
            r.name:SetWordWrap(false)
            r.sub = MakeFS(r, 12, C_GREY, "LEFT")
            r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 46, -26)
            r.sub:SetWordWrap(false)
            r.badge = MakeFS(r, 12, C_GREY, "RIGHT")
            r.badge:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -26)
            r.badge:SetWidth(46)
            r.badge:SetWordWrap(false)
            pool.chip[i] = r
        end
        if not r.__huiCard then
            r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
            r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
        end
        return r
    end

    local function put(f, h)
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
        f:Show()
        y = y - h
    end

    local name = U.dungeonQDetName
    local stf = U.dungeonQDetSt
    if not q then
        U.dungeonQDetGains = nil
        name:ClearAllPoints()
        name:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -DG.Q_PAD)
        name:SetText(L["点左侧任务查看详情"])
        name:SetTextColor(Unpack(C_GREY))
        name:Show()
        stf:Hide()
        child:SetHeight(DG.Q_PAD + 24 + DG.Q_PAD)
        return
    end

    U.dungeonQDetGains = { questID = q[1], sig = DG.QuestDataSig(q[1]) }
    DG.RequestQuestRewardData(q[1])

    local nm, hasName = DG.QuestName(q[1])
    local st = DG.QuestState(q[1])
    local col = (st == "done" and C_GREEN) or (st == "active" and C_GOLD) or C_GREY
    if hasName then nm = nm .. format(" |cff9a9a9a#%d|r", q[1]) end
    name:SetText(nm)
    name:SetTextColor(Unpack(hasName and C_GOLD or C_GREY))
    name:ClearAllPoints()
    name:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -DG.Q_PAD)
    name:Show()
    y = -(DG.Q_PAD + 26)
    stf:SetText(hasName and (L["状态："] .. (DG.Q_STATUS_TAG[st] or "")) or L["暂时没有客户端数据"])
    stf:SetTextColor(Unpack(hasName and col or C_DARKGREY))
    put(stf, 22)

    local lvClient = DG.QuestLevel(q[1])
    local attain = q[3] and format(L["%d 级可接"], q[3]) or nil
    local lvCol = lvClient and DG.DifficultyColor(lvClient) or nil
    local lvTxt = ""
    if attain then
        lvTxt = DG.Hex(C_GOLD) .. attain .. "|r"
        if lvClient or q[4] then
            local lvSeg = format(L[" · 任务等级 Lv%s"], tostring(lvClient or q[4]))
            lvTxt = lvTxt .. (lvCol and DG.Hex(lvCol) .. lvSeg .. "|r" or lvSeg)
        end
    elseif lvClient or q[4] then
        local lvSeg = format(L["任务等级 Lv%s"], tostring(lvClient or q[4]))
        lvTxt = lvCol and DG.Hex(lvCol) .. lvSeg .. "|r" or lvSeg
    end
    local shareSeg
    do
        local push = DG.QLCall("IsPushableQuest", q[1])
        if push ~= nil then
            shareSeg = DG.Hex(C_GREY) .. L["共享"] .. "：|r"
                .. (push and DG.Hex(C_GREEN) .. L["可分享"] .. "|r"
                        or DG.Hex(C_RED) .. L["不可共享"] .. "|r")
        end
    end
    if lvTxt ~= "" then
        local f = takeKv()
        f:SetText(DG.Hex(C_GREY) .. L["可接等级"] .. "：|r" .. lvTxt
            .. (shareSeg and " · " .. shareSeg or ""))
        put(f, 24)
    elseif shareSeg then
        local f = takeKv()
        f:SetText(shareSeg)
        put(f, 24)
    end
    if q[13] and #q[13] > 0 then
        local parts = {}
        for _, d in ipairs(q[13]) do
            local dc = DG.Q_DIFF_COLOR[d[2]] or C_GREY
            parts[#parts + 1] = DG.Hex(dc) .. tostring(d[1]) .. "|r"
        end
        local f = takeKv()
        f:SetText(DG.Hex(C_GREY) .. L["任务难度"] .. "：|r" .. table.concat(parts, "  "))
        put(f, 24)
    end
    local startNpcID = q[16]
    local sn = (not q[16]) and DG.QuestStartNpc(q[1]) or nil
    if not startNpcID and sn then startNpcID = sn[1] end
    local smap, sx, sy, szone = DG.StartLoc(q[1], startNpcID)
    local sloc = (smap and DG.LocText(smap, sx, sy, szone)) or DG.ZoneShort(q[6])
    local where = q[5] or ""
    if q[16] then
        local nm = (q[17] and q[17] ~= "" and q[17]) or q[5] or ""
        where = "|cffffd100" .. nm .. "|r" .. format(" |cff9a9a9a#%d|r", q[16])
    end
    if sloc and sloc ~= "" then
        where = (where ~= "" and (where .. " · " .. sloc) or sloc)
    end
    if where ~= "" then
        local f
        if q[16] or sn then
            f = takeNpc()
            local suffix = ""
            if sn and sn[2] then
                suffix = DG.Hex(C_DIM) .. format(L["（%s 掉落）"], sn[2]) .. "|r"
            end
            f.fs:SetText(DG.Hex(C_GREY) .. L["起始："] .. "|r" .. where .. suffix)
            f.__npc = q[16] or sn[1]
            f.__loc = (smap and { smap, sx, sy }) or (sn and sn[3] and { sn[3], sn[4], sn[5] }) or nil
        else
            f = takeKv()
            f:SetText(DG.Hex(C_GREY) .. L["起始："] .. "|r" .. where)
        end
        put(f, 24)
    end
    do
        local en = DG.QuestEndNpc(q[1])
        if en then
            local enid, ename, emap, ex, ey, ezone = en[1], en[2], en[3], en[4], en[5], en[6]
            local txt
            if ename and ename ~= "" then
                txt = "|cffffd100" .. ename .. "|r"
                if enid then txt = txt .. format(" |cff9a9a9a#%d|r", enid) end
            elseif enid then
                txt = format("|cff9a9a9a#%d|r", enid)
            else
                txt = ""
            end
            local zl = DG.LocText(emap, ex, ey, ezone)
            if zl and zl ~= "" then txt = txt .. " · " .. zl end
            local f
            if emap and ex and ey and MapUsable(emap) then
                f = takeNpc()
                f.fs:SetText(DG.Hex(C_GREY) .. L["结束："] .. "|r" .. txt)
                f.__npc = enid
                f.__loc = { emap, ex, ey }
            else
                f = takeKv()
                f:SetText(DG.Hex(C_GREY) .. L["结束："] .. "|r" .. txt)
            end
            put(f, 24)
        end
    end
    do
        local f = takeKv()
        local fac, facCol
        if q[2] == "A" then
            fac, facCol = L["联盟专属"], DG.C_FAC_A
        elseif q[2] == "H" then
            fac, facCol = L["部落专属"], DG.C_FAC_H
        else
            fac = L["双阵营共有"]
        end
        f:SetText(DG.Hex(C_GREY) .. L["阵营"] .. "：|r"
            .. (facCol and DG.Hex(facCol) .. fac .. "|r" or fac))
        put(f, 24)
    end
    if q[15] then
        local f = takeKv()
        f:SetText(DG.Hex(C_GREY) .. L["职业"] .. "：|r"
            .. DG.Hex(DG.QClassColor(q[15])) .. format(L["%s专属"], q[15]) .. "|r")
        put(f, 24)
    end
    y = y - 4

    do
        local nodes, seen = {}, { [q[1]] = true }
        local function collect(row, depth)
            if not row or depth > 30 or #nodes >= 30 then return end
            local pre = row[9]
            if not pre then return end
            for k = #pre, 1, -1 do
                local seg = pre[k]
                if type(seg) == "number" and not seen[seg] then
                    seen[seg] = true
                    local prow = DG.QuestRowByID(seg) or DG.ExtQuestRow(seg)
                    if not prow and ns.DungeonQuestPreExtra then
                        local ex = ns.DungeonQuestPreExtra[seg]
                        if ex then prow = { [1] = seg, [9] = ex } end
                    end
                    collect(prow, depth + 1)
                    nodes[#nodes + 1] = seg
                elseif type(seg) == "string" then
                    nodes[#nodes + 1] = seg
                end
            end
        end
        collect(q, 1)
        local pnote = ns.DungeonQuestPreNote and ns.DungeonQuestPreNote[q[1]]
        if #nodes > 0 or pnote then
            local f = takeLab()
            f:SetText(L["前置任务"])
            put(f, 20)
            local frontier = true
            for _, seg in ipairs(nodes) do
                local r = takeNode()
                if type(seg) == "number" then
                    local pnm, pok = DG.QuestName(seg)
                    local pst = DG.QuestState(seg)
                    local pcol = (pst == "done" and C_GREEN) or (pst == "active" and C_GOLD) or C_GREY
                    r.name:SetText(pok and (pnm .. format(" |cff9a9a9a#%d|r", seg)) or pnm)
                    r.name:SetTextColor(Unpack(pok and pcol or C_GREY))
                    local stag = (pok and DG.Q_STATUS_TAG[pst]) or ""
                    local shex = format("%02x%02x%02x", pcol[1] * 255 + 0.5, pcol[2] * 255 + 0.5, pcol[3] * 255 + 0.5)
                    if frontier and pok and pst ~= "done" then
                        stag = "|cffffd100" .. L["下一步"] .. "|r" .. (stag ~= "" and (" · |cff" .. shex .. stag .. "|r") or "")
                        frontier = false
                    end
                    r.st:SetText(stag)
                    r.st:SetTextColor(Unpack(pok and pcol or C_GREY))
                    r.st:Show()
                    rowMark(r, pok and pst or nil, pcol)
                    local prow = DG.QuestRowByID(seg) or DG.ExtQuestRow(seg)
                    local sub = ""
                    if prow then
                        sub = prow[5] or ""
                        local nl = DG.NodeLoc(seg, prow[16], prow[6])
                        if nl and nl ~= "" then sub = (sub ~= "" and (sub .. " · " .. nl) or nl) end
                        if prow[3] then sub = sub .. " · " .. format(L["%d 级可接"], prow[3]) end
                    elseif ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[seg] then
                        local ex = ns.DungeonQuestPreExtra[seg]
                        if ex.src and ex.src ~= "" then
                            sub = ex.src
                            if ex.lv then sub = sub .. " · " .. format(L["%d 级可接"], ex.lv) end
                        elseif ex.npc and ex.npc ~= "" then
                            sub = ex.npc
                            if ex.lv then sub = sub .. " · " .. format(L["%d 级可接"], ex.lv) end
                        end
                    end
                    if sub == "" then sub = L["本表未收录起始信息"] end
                    r.sub:SetText(sub)
                    r.__q = prow
                    r.__preID = seg
                    local nid = prow and prow[16] or nil
                    if not nid and ns.QuestPreNpcID then nid = ns.QuestPreNpcID[seg] end
                    local sn = (not nid) and DG.QuestStartNpc(seg) or nil
                    if sn then nid = sn[1] end
                    r.__npc = nid
                    r.__loc = (sn and sn[3] and { sn[3], sn[4], sn[5] }) or nil
                else
                    r.name:SetText(seg)
                    r.name:SetTextColor(Unpack(C_GREY))
                    r.st:Hide()
                    rowMark(r, nil)
                    r.sub:SetText(L["前置 ID 未收录，查不了状态"])
                    r.__q = nil
                    r.__preID = nil
                    r.__npc = nil
                    r.__loc = nil
                end
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
                r:Show()
                y = y - 38
            end
        end
        if pnote then
            local t = takeTxt()
            t:SetText(pnote)
            t:SetTextColor(Unpack(C_GREY))
            local h = t:GetStringHeight()
            put(t, (type(h) == "number" and h or 18) + 2)
        end
        y = y - 4
    end

    do
        local fol = DG.QuestFollowers(q[1])
        if #fol > 0 then
            local f = takeLab()
            f:SetText(L["后续任务"])
            put(f, 20)
            for _, fq in ipairs(fol) do
                local r = takeNode()
                local fnm, fok = DG.QuestName(fq[1])
                local fst = DG.QuestState(fq[1])
                local fcol = (fst == "done" and C_GREEN) or (fst == "active" and C_GOLD) or C_GREY
                r.name:SetText(fok and (fnm .. format(" |cff9a9a9a#%d|r", fq[1])) or fnm)
                r.name:SetTextColor(Unpack(fok and fcol or C_GREY))
                r.st:SetText(fok and (DG.Q_STATUS_TAG[fst] or "") or "")
                r.st:SetTextColor(Unpack(fok and fcol or C_GREY))
                r.st:Show()
                rowMark(r, fok and fst or nil, fcol)
                local sub = fq[5] or ""
                local nl = DG.NodeLoc(fq[1], fq[16], fq[6])
                if nl and nl ~= "" then sub = (sub ~= "" and (sub .. " · " .. nl) or nl) end
                if sub == "" then sub = L["本表未收录起始信息"] end
                r.sub:SetText(sub)
                r.__q = fq
                local fsn = (not fq[16]) and DG.QuestStartNpc(fq[1]) or nil
                r.__npc = fq[16] or (fsn and fsn[1]) or nil
                local fm, fx, fy = DG.StartLoc(fq[1], r.__npc)
                r.__loc = (fm and { fm, fx, fy }) or (fsn and fsn[3] and { fsn[3], fsn[4], fsn[5] }) or nil
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
                r:Show()
                y = y - 38
            end
        end
        y = y - 4
    end

    do
        local desc = DG.QuestDescription(q[1]) or q[20]
        if desc then
            local f = takeLab()
            f:SetText(L["任务说明"])
            put(f, 20)
            local t = takeTxt()
            t:SetText(desc)
            t:SetTextColor(Unpack(C_TEXT))
            local h = t:GetStringHeight()
            put(t, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    do
        local note = q[12]
        if note then
            local f = takeLab()
            f:SetText(L["任务注释"])
            put(f, 20)
            local t = takeTxt()
            t:SetText(note)
            t:SetTextColor(Unpack(C_TEXT))
            local h = t:GetStringHeight()
            put(t, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    local function renderChips(items, ncol, questID)
        local colW = math.floor((detW - 8) / ncol)
        for idx, iid in ipairs(items) do
            local r = takeChip()
            r:SetSize(colW, 44)
            local nw = colW - 46 - 8
            if questID then
                r.__q = questID
                nw = nw - 46 - 4
            else
                r.__q = nil
            end
            r.name:SetWidth(nw)
            r.sub:SetWidth(nw)
            r.icon:SetTexture(DG.ItemIcon(iid))
            if ns.hui and ns.hui.SetIconRing then
                ns.hui.SetIconRing(r.icon, { ns.hui.QColor(DG.QualOf(iid)) })
            end
            local inm, iok = DG.ItemName(iid)
            r.name:SetText(inm)
            r.sub:SetText(DG.ItemMeta(iid) or "")
            if iok then
                local qr, qg, qb = DG.QColor(DG.QualOf(iid))
                if qr then
                    r.name:SetTextColor(qr, qg, qb)
                else
                    r.name:SetTextColor(Unpack(C_TEXT))
                end
            else
                r.name:SetTextColor(Unpack(C_GREY))
            end
            r.__named = iok
            r.__it = { iid }
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", child, "TOPLEFT",
                (idx - 1) % ncol * (colW + 8), y - math.floor((idx - 1) / ncol) * 52)
            HuiCardState(r, "norm")
            r:Show()
            DG.ApplyChipBadge(r)
        end
        for _, iid in ipairs(items) do
            local _, iok = DG.ItemName(iid)
            DG.RequestItem(iid, not iok)
        end
        return math.ceil(#items / ncol)
    end
    do
        local objTxt = DG.NeedObjectivesText(q[1], q[14])
        if not objTxt and not DG.QuestObjectiveList(q[1]) and (DG.GAINS_FALLBACK or not q[11]) then
            objTxt = q[11]
        end
        local hasChips = q[14] and #q[14] > 0
        if hasChips or objTxt then
            local f = takeLab()
            f:SetText(L["任务需求"])
            put(f, 20)
            if hasChips then
                y = y - renderChips(q[14], 2, q[1]) * 52 - 2
            end
            if objTxt then
                local t = takeTxt()
                t:SetText(objTxt)
                t:SetTextColor(Unpack(C_TEXT))
                local h = t:GetStringHeight()
                put(t, (type(h) == "number" and h or 18) + 4)
                y = y - 2
            end
        end
    end
    local rew = q[10]
    if rew and #rew > 0 then
        local f = takeLab()
        f:SetText(L["任务奖励"])
        put(f, 20)
        y = y - renderChips(rew, 2) * 52 - 2
    end
    do
        local seg = DG.GainsSegs(q)
        if seg and #seg > 0 then
            local f = takeLab()
            f:SetText(L["收获"])
            put(f, 20)
            local txt = table.concat(seg, " · ")
            local t = takeTxt()
            t:SetText(txt)
            t:SetTextColor(Unpack(C_TEXT))
            local h = t:GetStringHeight()
            put(t, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    do
        local t = takeTxt()
        t:SetText(L["状态来自你自己的任务日志，交完任务这里会自动变。"])
        t:SetTextColor(Unpack(C_DARKGREY))
        put(t, 22)
    end

    for i = pool.nLab + 1, #pool.lab do pool.lab[i]:Hide() end
    for i = pool.nKv + 1, #pool.kv do pool.kv[i]:Hide() end
    for i = pool.nTxt + 1, #pool.txt do pool.txt[i]:Hide() end
    for i = pool.nNode + 1, #pool.node do pool.node[i]:Hide() end
    for i = pool.nChip + 1, #pool.chip do pool.chip[i]:Hide() end
    for i = pool.nNpc + 1, #pool.npc do pool.npc[i]:Hide() end

    child:SetHeight(math.max(10, -y + 12))
    DG.ClampScroll(U.dungeonQDet, child, keepDet)
    DG.UpdateQDetBar()
end

function DG.GuideBossName(dungeonID, en)
    local loot = (ns.DungeonLoot or {})[dungeonID]
    if loot then
        for i = 1, #loot do
            if loot[i][1] == en then return loot[i][2] or en end
        end
    end
    return en
end

function U:RenderDungeonGuide()
    local d = U.dungeonDetailCur
    local child, pool = U.dungeonGuideChild, U.dungeonGuidePool
    if not (d and child and pool) then return end
    local g = (ns.DungeonGuide or {})[d.id]
    local cards = pool.card
    local nC = 0
    DG.__vgen = (DG.__vgen or 0) + 1

    local function takeCard()
        nC = nC + 1
        local c = cards[nC]
        if not c then
            c = CreateFrame("Frame", nil, child, "BackdropTemplate")
            c:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            if not HuiCardFX(c) then
                c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
                c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
            end
            c.title = MakeFS(c, 16, C_GOLD, "LEFT")
            c.title:SetPoint("TOPLEFT", c, "TOPLEFT", DG.GUIDE_PAD, -DG.GUIDE_PAD)
            c.rows = {}
            cards[nC] = c
        end
        c:Show()
        return c
    end

    local function takeT(c, w)
        local n = (c.n or 0) + 1
        c.n = n
        local f = c.rows[n]
        if not f then
            f = MakeFS(c, 14, C_TEXT, "LEFT")
            f:SetWordWrap(true)
            c.rows[n] = f
        end
        f:SetWidth(w)
        f:Show()
        return f
    end

    local function fillCard(c, def)
        c.n = 0
        c.title:SetText(def.label)
        local cy = -(DG.GUIDE_PAD + DG.GUIDE_HDR_H)
        local rows, last = def.rows, #def.rows
        for i = 1, last do
            local r = rows[i]
            local f = takeT(c, DG.GUIDE_CARD_W - DG.GUIDE_PAD * 2 - (r.x or 0))
            f:SetTextColor(Unpack(r.c or C_TEXT))
            f:SetText(r.t)
            f:ClearAllPoints()
            f:SetPoint("TOPLEFT", c, "TOPLEFT", DG.GUIDE_PAD + (r.x or 0), cy)
            local sh = f:GetStringHeight()
            cy = cy - (type(sh) == "number" and sh or 18) - (i == last and 0 or (r.gap or 4))
        end
        for i = c.n + 1, #c.rows do c.rows[i]:Hide() end
        return -cy + DG.GUIDE_PAD
    end

    local defs = {}
    if g then
        if g.tagline or (g.tips and #g.tips > 0) then
            local rows = {}
            if g.tagline then
                rows[#rows + 1] = { t = "· " .. g.tagline, c = C_TEXT, x = 0, gap = 5 }
            end
            if g.tips then
                for i = 1, #g.tips do
                    rows[#rows + 1] = { t = "· " .. g.tips[i], c = C_TEXT, x = 0, gap = 5 }
                end
            end
            defs[#defs + 1] = { label = L["副本须知"], accent = DG.GUIDE_ACCENT[1], rows = rows }
        end
        if g.entrance and (g.entrance.H or (g.entrance.A and #g.entrance.A > 0)) then
            local rows = {}
            if g.entrance.H then
                rows[#rows + 1] = { t = L["部落："] .. g.entrance.H, c = C_TEXT, x = 0, gap = 6 }
            end
            if g.entrance.A and #g.entrance.A > 0 then
                rows[#rows + 1] = { t = L["联盟："], c = C_TEXT, x = 0, gap = 2 }
                for i = 1, #g.entrance.A do
                    rows[#rows + 1] = { t = i .. ". " .. g.entrance.A[i], c = C_TEXT, x = 12, gap = 4 }
                end
            end
            defs[#defs + 1] = { label = L["怎么进本"], accent = DG.GUIDE_ACCENT[2], rows = rows }
        end
        if g.bosses and #g.bosses > 0 then
            local rows = {}
            for i = 1, #g.bosses do
                local b = g.bosses[i]
                local cn = DG.GuideBossName(d.id, b.en)
                rows[#rows + 1] = { t = (cn ~= b.en) and (cn .. "（" .. b.en .. "）") or b.en,
                                    c = C_GOLD, x = 0, gap = 3 }
                rows[#rows + 1] = { t = b.text, c = C_TEXT, x = 0, gap = 9 }
            end
            defs[#defs + 1] = { label = L["BOSS 打法"], accent = DG.GUIDE_ACCENT[3], rows = rows }
        end
        if g.trash and #g.trash > 0 then
            local rows = {}
            for i = 1, #g.trash do
                rows[#rows + 1] = { t = g.trash[i].title, c = C_GOLD, x = 0, gap = 3 }
                rows[#rows + 1] = { t = g.trash[i].text, c = C_TEXT, x = 0, gap = 9 }
            end
            defs[#defs + 1] = { label = L["小怪应对"], accent = DG.GUIDE_ACCENT[4], rows = rows }
        end
    end

    if #defs == 0 then
        if not pool.note then
            pool.note = MakeFS(child, 14, C_GREY, "LEFT")
            pool.note:SetWordWrap(true)
        end
        local f = pool.note
        f:SetWidth(DG.CHILD_W)
        f:SetText(L["这个副本还没有攻略，数据补上后会自动出现。"])
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)
        f:Show()
        for i = 1, #cards do cards[i]:Hide() end
        child:SetHeight(30)
        U.dungeonGuideScroll:SetVerticalScroll(0)
        return
    end
    if pool.note then pool.note:Hide() end

    local list = {}
    for k = 1, #defs do
        local c = takeCard()
        list[k] = { frame = c, h = fillCard(c, defs[k]) }
    end

    local top, i = 0, 1
    while i <= #list do
        local a, b = list[i], list[i + 1]
        local rh = a.h
        if b and b.h > rh then rh = b.h end
        a.frame:ClearAllPoints()
        a.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE, top)
        a.frame:SetSize(DG.GUIDE_CARD_W, rh)
        a.frame.__vtop, a.frame.__vh, a.frame.__vgen = -top, rh, DG.__vgen
        if b then
            b.frame:ClearAllPoints()
            b.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE + DG.GUIDE_CARD_W + DG.GUIDE_GAP_X, top)
            b.frame:SetSize(DG.GUIDE_CARD_W, rh)
            b.frame.__vtop, b.frame.__vh, b.frame.__vgen = -top, rh, DG.__vgen
        end
        top = top - rh - DG.GUIDE_GAP_Y
        i = i + 2
    end

    for i = nC + 1, #cards do cards[i]:Hide() end
    child:SetHeight(math.max(10, -top - DG.GUIDE_GAP_Y + DG.GUIDE_PAD))
    U.dungeonGuideScroll:SetVerticalScroll(0)
    DG.CullGuideCards()
end

function U:SetDungeonTab(tab)
    local t = "loot"
    if tab == "quest" then t = "quest" elseif tab == "guide" then t = "guide" elseif tab == "map" then t = "map" end
    U.dungeonTab = t
    DB().dungeonTab = t
    U.dungeonQDetKey = nil
    U.dungeonQListKey = nil
    U:RenderDungeonTab()
    ns.PlaySound(1)
end

function U:RenderDungeonTab()
    local cur = U.dungeonTab or "loot"
    local isQuest = (cur == "quest")
    local isGuide = (cur == "guide")
    local isMap = (cur == "map")

    if isQuest then
        DG.EnsureQuestLane()
        U:RenderDungeonQuests()
    elseif isGuide then
        DG.EnsureGuideLane()
        U:RenderDungeonGuide()
    elseif isMap then
        DG.EnsureMapPage()
        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end
    else
        U:RenderDungeonLoot()
    end
    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide and not isMap) end
    if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end
    if U.dungeonMapFrame then U.dungeonMapFrame:SetShown(isMap) end
    if not isMap and ns.MapModule and ns.MapModule.HideBossModel then ns.MapModule.HideBossModel() end
    if U.dungeonQuestScroll then U.dungeonQuestScroll:SetShown(isQuest and (U.dungeonQView ~= "overview")) end
    if U.dungeonQDet then U.dungeonQDet:SetShown(isQuest) end
    if U.dungeonQDetBar then
        U.dungeonQDetBar:SetShown(isQuest and DG.UpdateQDetBar ~= nil)
        if isQuest then DG.UpdateQDetBar() end
    end
    if U.dungeonQPlateL then U.dungeonQPlateL:SetShown(isQuest) end
    if U.dungeonQListCard then U.dungeonQListCard:SetShown(isQuest and U.dungeonQView ~= "overview") end
    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end
    if U.dungeonQOverviewF then U.dungeonQOverviewF:SetShown(isQuest and (U.dungeonQView == "overview")) end
    if U.dungeonQOVCard then U.dungeonQOVCard:SetShown(isQuest and (U.dungeonQView == "overview")) end
    if U.dungeonQOVFlowCard then
        U.dungeonQOVFlowCard:SetShown(isQuest and (U.dungeonQView == "overview")
            and (DG.CurQuestFlow(U.dungeonDetailCur) ~= nil))
    end
    if U.dungeonQMask then U.dungeonQMask:SetShown(isQuest) end
    if U.dungeonQTrackMask then U.dungeonQTrackMask:SetShown(isQuest) end
    if U.dungeonGMask then U.dungeonGMask:SetShown(isGuide) end
    if U.dungeonLMask then U.dungeonLMask:SetShown(not isQuest and not isGuide and not isMap) end
    do
        local LFUI = ns.LootFilterUI
        if cur == "loot" then
            if LFUI then LFUI:EnsureBar(); LFUI:RefreshBar() end
            if U.lootFilterBar then U.lootFilterBar:Show() end
        else
            if U.lootFilterBar then U.lootFilterBar:Hide() end
        end
    end
    DG.ApplyDetailChrome(cur)
end
DG.CAPSULE_LIFT = 20
DG.CAPSULE_W = 82
local function BuildSubTabs()
    local defs = {
        { key = "Dungeons", text = L["5人本"], width = DG.CAPSULE_W },
        { key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W },
    }
    if ns.LoadForeverPages then
        defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "Explore", text = L["探索"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "Collections", text = L["藏品"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "Factions", text = L["声望"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "Bis", text = L["BIS配装"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "Tier", text = L["职业指南"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "PvP", text = L["PvP"], width = DG.CAPSULE_W }
        defs[#defs + 1] = { key = "Gear", text = L["装备库"], width = DG.CAPSULE_W }
    end
    local BTN_H = IsHui() and 20 or 26
    local GAP = IsHui() and 0 or 6
    local totalW = 0
    for i, t in ipairs(defs) do
        totalW = totalW + t.width
        if i > 1 then totalW = totalW + GAP end
    end
    local host = CreateFrame("Frame", nil, U.panel)
    host:SetSize(totalW, BTN_H)
    host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)

    local ctrl
    if IsHui() and ns.hui and ns.hui.CreateSegmentedControl then
        ctrl = ns.hui.CreateSegmentedControl(host)
    end

    local btns, prev = {}, nil
    for _, tab in ipairs(defs) do
        local bt
        if ctrl then
            bt = CreateFrame("Button", nil, host)
            bt:SetSize(tab.width, BTN_H)
            if prev then
                bt:SetPoint("LEFT", prev, "RIGHT", 0, 0)
            else
                bt:SetPoint("TOPLEFT", host, "TOPLEFT", 0, 0)
            end
            local t = bt:CreateFontString()
            t:SetAllPoints()
            t:SetFont(Fnt(14))
            t:SetText(tab.text)
            t:SetWordWrap(false)
            t:SetTextColor(Unpack(C_DIM))
            bt:SetFontString(t)
        else
            bt = NewButton(host, tab.text, tab.width, BTN_H, 14)
            if prev then
                bt:SetPoint("LEFT", prev, "RIGHT", GAP, 0)
            else
                bt:SetPoint("TOPLEFT", host, "TOPLEFT", 0, 0)
            end
        end
        prev = bt
        btns[#btns + 1] = bt
        tab.button = bt
        bt:SetScript("OnClick", function()
            U:SwitchSub(tab.key)
            ns.PlaySound(1)
        end)
    end
    if ctrl then ctrl:AttachButtons(btns) end
    U.subTabs = defs
    U.subCtrl = ctrl
    ns.ApplyTabVisibility()
end

function ns.ApplyTabVisibility()
    if not U.subTabs then return end
    local cfg = ns.QuickCfg().tabs or {}
    local BTN_H = IsHui() and 20 or 26
    local GAP = IsHui() and 0 or 6
    local totalW, prev, firstVis = 0, nil, nil
    for _, tab in ipairs(U.subTabs) do
        local bt = tab.button
        if bt then
            local show = (cfg[tab.key] ~= false)
            bt:SetShown(show)
            if show then
                bt:ClearAllPoints()
                if prev then
                    bt:SetPoint("LEFT", prev, "RIGHT", GAP, 0)
                    totalW = totalW + GAP
                else
                    bt:SetPoint("TOPLEFT", bt:GetParent(), "TOPLEFT", 0, 0)
                end
                totalW = totalW + tab.width
                prev = bt
                firstVis = firstVis or tab.key
            end
        end
    end
    if not prev then return end
    local host = prev:GetParent()
    if host and host.SetSize then host:SetSize(totalW, BTN_H) end
    if U.subCtrl then
        local vis = {}
        for _, tab in ipairs(U.subTabs) do
            if cfg[tab.key] ~= false and tab.button then vis[#vis + 1] = tab.button end
        end
        U.subCtrl:AttachButtons(vis)
    end
    local cur = U.curSub
    if cur and cfg[cur] == false then
        U.curSub = firstVis
        if U.built then U:SwitchSub(firstVis) end
    end
end

function U:EnsureBuilt(k)
    if k == "Dungeons" then
        DG.BuildDungeons()
        return
    end
    if not U.subBuilt then U.subBuilt = {} end
    if U.subBuilt[k] then return end
    if k == "Raids" and ns.RaidModule and U.raidPage then
        U.subBuilt[k] = true
        ns.RaidModule.Build(U.raidPage)
    elseif k == "Professions" and ns.ProfModule and U.profPage then
        U.subBuilt[k] = true
        ns.ProfModule.Build(U.profPage)
    elseif k == "Explore" and ns.ExploreModule and U.explorePage then
        U.subBuilt[k] = true
        ns.ExploreModule.Build(U.explorePage)
    elseif k == "Collections" and ns.CollectionModule and U.collectionPage then
        U.subBuilt[k] = true
        ns.CollectionModule.Build(U.collectionPage)
    elseif k == "Factions" and ns.FactionModule and U.factionPage then
        U.subBuilt[k] = true
        ns.FactionModule.Build(U.factionPage)
    elseif k == "Bis" and ns.BisModule and U.bisPage then
        U.subBuilt[k] = true
        ns.BisModule.Build(U.bisPage)
    elseif k == "Tier" and ns.TierModule and U.tierPage then
        U.subBuilt[k] = true
        ns.TierModule.Build(U.tierPage)
    elseif k == "PvP" and ns.PvPModule and U.pvpPage then
        U.subBuilt[k] = true
        ns.PvPModule.Build(U.pvpPage)
    elseif k == "Gear" and ns.GearModule and U.gearPage then
        U.subBuilt[k] = true
        ns.GearModule.Build(U.gearPage)
    end
end

function U:SchedulePrebuild()
    return
end

function U:SwitchSub(key)
    local k = "Dungeons"
    if key == "Raids" then
        k = "Raids"
    elseif key == "Professions" and ns.LoadForeverPages then
        k = "Professions"
    elseif key == "Explore" and ns.LoadForeverPages then
        k = "Explore"
    elseif key == "Collections" and ns.LoadForeverPages then
        k = "Collections"
    elseif key == "Factions" and ns.LoadForeverPages then
        k = "Factions"
    elseif key == "Bis" and ns.LoadForeverPages then
        k = "Bis"
    elseif key == "Tier" and ns.LoadForeverPages then
        k = "Tier"
    elseif key == "PvP" and ns.LoadForeverPages then
        k = "PvP"
    elseif key == "Gear" and ns.LoadForeverPages then
        k = "Gear"
    end
    U.curSub = k
    DB().subTab = k
    DG.Gate.HideUI()
    ns.OpenPerf.Begin(({ Dungeons = "副本", Raids = "团本", Professions = "专业", Explore = "探索", Collections = "收藏", Factions = "阵营", Bis = "BIS", Tier = "职业指南", PvP = "PvP", Gear = "装备库" })[k] or k)
    local isDun, isRaid, isProf, isExpl, isColl, isBis, isTier = (k == "Dungeons"), (k == "Raids"), (k == "Professions"), (k == "Explore"), (k == "Collections"), (k == "Bis"), (k == "Tier")
    local isPvP = (k == "PvP")
    local isFac = (k == "Factions")
    local isGear = (k == "Gear")
    local function applyPages()
        if U.dungeonPage then U.dungeonPage:SetShown(isDun) end
        if U.raidPage then U.raidPage:SetShown(isRaid) end
        if U.profPage then U.profPage:SetShown(isProf) end
        if U.explorePage then U.explorePage:SetShown(isExpl) end
        if U.collectionPage then U.collectionPage:SetShown(isColl) end
        if U.bisPage then U.bisPage:SetShown(isBis) end
        if U.tierPage then U.tierPage:SetShown(isTier) end
        if U.pvpPage then U.pvpPage:SetShown(isPvP) end
        if U.factionPage then U.factionPage:SetShown(isFac) end
        if U.gearPage then U.gearPage:SetShown(isGear) end
    end
    applyPages()
    if isRaid then
        U:EnsureBuilt("Raids")
    elseif isDun then
        if U.dungeonDetail and U.dungeonDetailCur and U.dungeonDetailCur.raid
            and U.dungeonDetail:IsShown() then
            U.dungeonDetail:Hide()
        end
        DG.BuildDungeons()
        U:UpdateDungeons()
    elseif isProf and ns.ProfModule then
        U:EnsureBuilt("Professions")
        ns.ProfModule.Open()
    elseif isExpl and ns.ExploreModule then
        U:EnsureBuilt("Explore")
        ns.ExploreModule.Open()
    elseif isColl and ns.CollectionModule then
        U:EnsureBuilt("Collections")
        ns.CollectionModule.Open()
    elseif isBis and ns.BisModule then
        U:EnsureBuilt("Bis")
        ns.BisModule.Open()
    elseif isTier and ns.TierModule then
        U:EnsureBuilt("Tier")
        ns.TierModule.Refresh()
    elseif isPvP and ns.PvPModule then
        U:EnsureBuilt("PvP")
        ns.PvPModule.Open()
    elseif isFac and ns.FactionModule then
        U:EnsureBuilt("Factions")
        ns.FactionModule.Open()
    elseif isGear and ns.GearModule then
        U:EnsureBuilt("Gear")
        ns.GearModule.Open()
    end
    applyPages()
    ns.OpenPerf.Mark("就绪")
    for _, tab in ipairs(U.subTabs or {}) do
        local selected = (tab.key == k)
        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end
        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))
    end
end

function U:SetSubCapsule(key)
    for _, tab in ipairs(U.subTabs or {}) do
        local selected = (tab.key == key)
        if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end
        tab.button:GetFontString():SetTextColor(Unpack(selected and C_WHITE or C_DIM))
    end
end

function U:UpdateActiveSub()
    if self.curSub == "Raids" then return end
    if self.curSub == "Professions" then
        if ns.ProfModule then ns.ProfModule.Refresh() end
        return
    end
    if self.curSub == "Explore" then
        if ns.ExploreModule then ns.ExploreModule.Refresh() end
        return
    end
    if self.curSub == "Collections" then
        if ns.CollectionModule then ns.CollectionModule.Refresh() end
        return
    end
    if self.curSub == "Bis" then
        if ns.BisModule then ns.BisModule.Refresh() end
        return
    end
    if self.curSub == "Tier" then
        if ns.TierModule then ns.TierModule.Refresh() end
        return
    end
    if self.curSub == "PvP" then
        if ns.PvPModule then ns.PvPModule.Refresh() end
        return
    end
    if self.curSub == "Factions" then
        if ns.FactionModule then ns.FactionModule.Refresh() end
        return
    end
    if self.curSub == "Gear" then
        if ns.GearModule then ns.GearModule.Refresh() end
        return
    end
    self:UpdateDungeons()
end

function U:Build()
    if U.built or U.building then return end
    FONT_BASE = FONT_BASE or ns.FONT
    if not FONT_BASE then return end
    U.building = true
    DG.Loader.Init()

    local saved = DB().subTab
    if saved == "Raids" then
        U.curSub = "Raids"
    elseif saved == "Professions" and ns.LoadForeverPages then
        U.curSub = "Professions"
    elseif saved == "Explore" and ns.LoadForeverPages then
        U.curSub = "Explore"
    elseif saved == "Collections" and ns.LoadForeverPages then
        U.curSub = "Collections"
    elseif saved == "Bis" and ns.LoadForeverPages then
        U.curSub = "Bis"
    elseif saved == "Tier" and ns.LoadForeverPages then
        U.curSub = "Tier"
    elseif saved == "PvP" and ns.LoadForeverPages then
        U.curSub = "PvP"
    elseif saved == "Factions" and ns.LoadForeverPages then
        U.curSub = "Factions"
    elseif saved == "Gear" and ns.LoadForeverPages then
        U.curSub = "Gear"
    else
        U.curSub = "Dungeons"
    end

    local panel = EnsureContent()
    U.dungeonPage = CreateFrame("Frame", nil, panel)
    U.dungeonPage:SetAllPoints(panel)
    U.dungeonPage:Hide()

    U.raidPage = CreateFrame("Frame", nil, panel)
    U.raidPage:SetAllPoints(panel)
    U.raidPage:Hide()

    if ns.LoadForeverPages then
        U.profPage = CreateFrame("Frame", nil, panel)
        U.profPage:SetAllPoints(panel)
        U.profPage:Hide()
        U.explorePage = CreateFrame("Frame", nil, panel)
        U.explorePage:SetAllPoints(panel)
        U.explorePage:Hide()
        U.collectionPage = CreateFrame("Frame", nil, panel)
        U.collectionPage:SetAllPoints(panel)
        U.collectionPage:Hide()
        U.bisPage = CreateFrame("Frame", nil, panel)
        U.bisPage:SetAllPoints(panel)
        U.bisPage:Hide()
        U.tierPage = CreateFrame("Frame", nil, panel)
        U.tierPage:SetAllPoints(panel)
        U.tierPage:Hide()
        U.factionPage = CreateFrame("Frame", nil, panel)
        U.factionPage:SetAllPoints(panel)
        U.factionPage:Hide()
        U.pvpPage = CreateFrame("Frame", nil, panel)
        U.pvpPage:SetAllPoints(panel)
        U.pvpPage:Hide()
        U.gearPage = CreateFrame("Frame", nil, panel)
        U.gearPage:SetAllPoints(panel)
        U.gearPage:Hide()
    end

    U.dungeonBuilt = false
    DG.__chromeOnly = nil
    U.detailBuilt = nil
    U.overviewBuilt = nil
    U.cardPoolBuilt = nil
    U.questLaneBuilt = nil
    U.guideLaneBuilt = nil
    U.mapPageBuilt = nil
    U.dungeonListChild = nil
    U.dungeonListPool = nil
    U.dungeonListCard = nil
    U.dungeonListLevel = nil
    U.dungeonDetailChild = nil
    U.dungeonDetailHero = nil
    U.dungeonDetailPool = nil
    U.dungeonDetailNote = nil
    U.dungeonDetailCur = nil
    U.dungeonFilterBtns = nil
    U.dungeonLootViewBtns = nil
    U.dungeonDetailTipZone = nil
    U.dungeonDetailHover = nil
    U.dungeonQuestScroll = nil
    U.dungeonQuestChild = nil
    U.dungeonQuestPool = nil
    U.dungeonQListCard = nil
    U.dungeonQuestSum = nil
    U.dungeonQuestNote = nil
    U.dungeonQuestHover = nil
    U.dungeonGuideScroll = nil
    U.dungeonGuideChild = nil
    U.dungeonGuidePool = nil
    U.dungeonMapFrame = nil
    U.dungeonTabBtns = nil
    U.dungeonQDet = nil
    U.dungeonQDetChild = nil
    U.dungeonQDetBar = nil
    DG.UpdateQDetBar = nil
    U.dungeonQDetPool = nil
    U.dungeonQDetName = nil
    U.dungeonQDetSt = nil
    U.dungeonQuestSel = nil
    U.dungeonQDetExt = nil
    U.dungeonQFlow = nil
    U.dungeonQDetKey = nil
    U.dungeonQListKey = nil
    U.dungeonQFlowCard = nil
    U.dungeonQOVFlowCard = nil
    U.dungeonQSide = nil
    U.dungeonQView = nil
    U.dungeonQMask = nil
    U.dungeonQTrackMask = nil
    U.dungeonGMask = nil
    U.dungeonLMask = nil
    U.dungeonDetailBase = nil
    DG.__vgen = nil
    U.dungeonView = "list"
    if DB().dungeonView ~= "list" then DB().dungeonView = "list" end
    U.dungeonFilter = DB().dungeonFilter or "all"
    U.dungeonLootBoss = DB().dungeonLootBoss
    U.dungeonQFilter = DB().dungeonQuestFilter or "all"
    if U.dungeonQFilter == "done" then U.dungeonQFilter = "all" end
    U.lootView = (DB().lootView == "card") and "card" or "list"
    do
        local dt = DB().dungeonTab
        U.dungeonTab = (dt == "quest" or dt == "guide" or dt == "map") and dt or "loot"
    end
    U.subBuilt = {}

    BuildSubTabs()

    U:SwitchSub(U.curSub)
    U.building = false
    U.built = true
end

function U:Refresh()
    if not U.built then return end
    self:UpdateDungeons()
end

ns.Init(function()
    local frame = ns.TalentSimFrame
    if not frame then return end
    frame:SetScript("OnShow", function()
        FONT_BASE = FONT_BASE or ns.FONT
        if not U.built then
            U.building = false
            local ok, err = xpcall(U.Build, function(e)
                return tostring(e) .. "\n" .. debugstack(2, 40)
            end, U)
            if not ok then
                U.building = false
                U.built = false
                print("|cff46bf72[无限副本手册] 界面构建出错：|r" .. tostring(err))
                return
            end
        end
        if U.built then
            U:EnsureBuilt(U.curSub or "Dungeons")
        end
        U:UpdateActiveSub()
        U:SchedulePrebuild()
    end)
    frame:SetScript("OnHide", function()
        GameTooltip:Hide()
        U.dungeonDetailHover, U.dungeonQuestHover = nil, nil
        U.dungeonMapHover = nil
        if ns.IdleJobs then
            ns.IdleJobs.StepGC(90, 512)
        else
            collectgarbage("step", 512)
        end
    end)
end)

ns.ProfHost = {
    U = U, DG = DG,
    MakeFS = MakeFS, NewButton = NewButton, MakeOutline = MakeOutline,
    AddBtnIcon = AddBtnIcon,
    SetOutline = SetOutline, SetTip = SetTip, Unpack = Unpack,
    SetButtonSelected = ns.hui.SetButtonSelected,
    C_GOLD = C_GOLD, C_GREEN = C_GREEN, C_GREY = C_GREY,
    C_DIM = C_DIM, C_WHITE = C_WHITE, C_TEXT = C_TEXT,
    CONTENT_W = CONTENT_W, CONTENT_H = CONTENT_H,
    PAGE_INSET = PAGE_INSET, ROW_CLASS = ROW_CLASS,
    FALLBACK_ICON = FALLBACK_ICON,
}

function ns.OpenPage(key)
    local frame = ns.TalentSimFrame
    if not frame then return end
    if not frame:IsShown() then frame:Show() end
    frame:Raise()
    if U.built then U:SwitchSub(key) end
end

function ns.ShowDungeonDetail(id)
    local d
    for _, x in ipairs((ns.DungeonData and ns.DungeonData.dungeons) or {}) do
        if x.id == id then d = x break end
    end
    if not d then return end
    ns.OpenPage("Dungeons")
    if U.built and U.dungeonBuilt then
        U:SetDungeonView("list")
        U:ShowDungeonDetail(d)
    end
end
