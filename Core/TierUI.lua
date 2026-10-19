local _, ns = ...

if not ns.LoadForeverPages then return end

local format = string.format
local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton, MakeOutline = Host.NewButton, Host.MakeOutline
local SetOutline, Unpack = Host.SetOutline, Host.Unpack
local C_GOLD = Host.C_GOLD
local C_GREY, C_DIM, C_WHITE, C_TEXT = Host.C_GREY, Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local PAGE_INSET, CONTENT_W = Host.PAGE_INSET, Host.CONTENT_W
local ROW_CLASS = Host.ROW_CLASS
local FALLBACK_ICON = Host.FALLBACK_ICON

local T = ns.ClassTier
if not T or type(T.pages) ~= "table" or #T.pages == 0 then return end

local TT = {}
ns.TierModule = TT

TT.EDGE = PAGE_INSET
TT.CARD_TOP = 8
TT.NAV_X, TT.NAV_PAD = TT.EDGE, 8
TT.NAV_TOP = TT.CARD_TOP + 8
TT.NAV_W = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 184 or 148
TT.NAV_ITEM_H, TT.NAV_ICON, TT.NAV_FS = 26, 20, 16
TT.NAV_ITEM_GAP = 4
TT.NAV_ITEM_STEP = TT.NAV_ITEM_H + TT.NAV_ITEM_GAP
TT.NAV_HEAD_Y  = TT.NAV_TOP + 2
TT.NAV_RANK_Y  = TT.NAV_TOP + 22
TT.NAV_GROUP_Y = TT.NAV_TOP + 58
TT.NAV_FIRST_Y = TT.NAV_TOP + 84
TT.NAV_HEAD_FS = 16
TT.TAB_FS = 14
TT.CLASS_ICON_DIR = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\"
TT.X0 = TT.NAV_X + TT.NAV_PAD + TT.NAV_W + TT.NAV_PAD + 8
TT.INSET = 8
TT.RIGHT_X = TT.X0 + TT.INSET
TT.RIGHT_W = CONTENT_W - TT.RIGHT_X - TT.EDGE - TT.INSET
TT.SUB_Y, TT.SUB_H, TT.SUB_W, TT.SUB_STEP = TT.CARD_TOP + TT.INSET, 24, 70, 78
TT.BODY_TOP = TT.SUB_Y + TT.SUB_H + 8
TT.TOPCARD_TOP  = TT.CARD_TOP + TT.INSET
TT.TOPCARD_H    = 92
TT.TOPCARD_BOT  = TT.TOPCARD_TOP + TT.TOPCARD_H
TT.HERO_ICON_Y  = TT.TOPCARD_TOP + TT.INSET
TT.SPEC_BTN_W   = 52
TT.SPEC_BTN_GAP = 8
TT.SPEC_BTN_PAD = 10
TT.SPEC_BTN_Y   = TT.TOPCARD_TOP + TT.INSET + 20
TT.SPEC_META_Y  = TT.TOPCARD_TOP + 10
TT.MODE_KEYS    = { "rotation", "macro", "cq", "text" }
TT.MODE_H       = 24
TT.MODE_GAP     = 8
TT.MODE_Y       = TT.TOPCARD_TOP + TT.INSET + 52
TT.MODE_TOP     = TT.TOPCARD_BOT + 8
TT.LIST_PAD = 5
TT.CARD_W = TT.RIGHT_W

TT.GRID_COLS = 8
TT.GRID_ROWS = 1
TT.ICON = 28
TT.CELL_H = 40
TT.CELL_GAP = 8
TT.EMPTY_H = 26
TT.BADGE_W = 44
TT.CARD_GAP = 8

TT.OUTER_PAD = 0
TT.COL_GAP = 8
TT.FULL_W = TT.CARD_W
TT.COL_W = (TT.FULL_W - TT.COL_GAP) / 2
TT.CARD_PAD = 10
TT.HDR_H = 26
TT.SPEC_GAP = 8
TT.SPEC_ICON = 44
TT.HERO_H = TT.SPEC_ICON
TT.SPEC_TITLE_X = TT.INSET + TT.SPEC_ICON + TT.INSET
TT.INNER_W = TT.COL_W - 2 * TT.CARD_PAD
TT.INNER_FULL_W = TT.FULL_W - 2 * TT.CARD_PAD
TT.SPEC_TOP = TT.TOPCARD_BOT

TT.SEC_TAB_H    = 24
TT.SEC_TAB_GAP  = 8
TT.SEC_TAB_STEP = 8
TT.SEC_TAB_PAD  = 24
TT.SEC_TAB_MAX  = 9
TT.SEC_TAB_Y    = TT.SPEC_TOP + TT.SEC_TAB_GAP
TT.SEC_DROP     = 16
TT.SEC_TOP      = TT.SEC_TAB_Y + TT.SEC_TAB_H + TT.SEC_DROP
TT.SEC_TEXT_W   = TT.FULL_W - 2 * TT.CARD_PAD
TT.SEC_ORDER = { "changes", "viability", "sw", "beginner", "systems", "stats", "races", "prof" }

TT.CARD_RADIUS = 6
TT.PAIR_GAP = 12
TT.CHIP_H = 20
TT.CHIP_GAP = 5
TT.ROW_MAX = 120
TT.CARD_MAX = 14
TT.CHIP_MAX = 10
TT.SPAN_FULL = 2
TT.GOOD = { 0.37, 0.66, 0.37 }
TT.BAD = { 0.76, 0.39, 0.36 }
TT.HELP_ROW = 4
TT.HELP_HEAD = 6

TT.COLOR = {
    S = { 1.00, 0.50, 0.00 },
    A = { 0.64, 0.21, 0.93 },
    B = { 0.00, 0.44, 0.87 },
    C = { 0.12, 0.60, 0.00 },
    D = { 0.62, 0.62, 0.62 },
}
TT.BADGE_TEXT = { 0.08, 0.08, 0.08 }
TT.BADGE_R = 6

TT.PAGE_NAME = {
    dps = L["输出"],
    tank = L["坦克"],
    healer = L["治疗"],
}

local SPEC_INDEX = {}
for cls, list in pairs(T.specs or {}) do
    SPEC_INDEX[cls] = SPEC_INDEX[cls] or {}
    for _, sp in ipairs(list) do SPEC_INDEX[cls][sp.key] = sp end
end

local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local s = DungeonsForeverDB.tier
    if not s then
        s = {}
        DungeonsForeverDB.tier = s
    end
    if not s.tab then s.tab = T.pages[1].key end
    if s.nav ~= "spec" then s.nav = "rank" end
    if s.mode ~= "rotation" and s.mode ~= "macro" and s.mode ~= "cq" then s.mode = "text" end
    return s
end

local function PageFor(key)
    for _, p in ipairs(T.pages) do
        if p.key == key then return p end
    end
    return T.pages[1]
end

local function SpecRec(cls, key)
    local m = SPEC_INDEX[cls]
    return m and m[key]
end

local function ClassName(cls)
    local n = LOCALIZED_CLASS_NAMES_MALE and LOCALIZED_CLASS_NAMES_MALE[cls]
    return n or cls
end

local function ClassColor(cls)
    local c = RAID_CLASS_COLORS and RAID_CLASS_COLORS[cls]
    if c then return c.r, c.g, c.b end
    return 1, 1, 1
end

local function SpecGrade(cls, spec)
    local pages = T.pages
    if type(pages) ~= "table" then return nil end
    for _, p in ipairs(pages) do
        for _, tr in ipairs(p.tiers or {}) do
            for _, e in ipairs(tr.specs or {}) do
                if e.class == cls and e.spec == spec then
                    return tr.key, p.key
                end
            end
        end
    end
    return nil
end

local FONT_BASE
local function Fnt(size)
    FONT_BASE = FONT_BASE or ns.FONT or "Fonts\\FRIZQT__.TTF"
    local flags = "OUTLINE"
    if ns.hui and ns.hui.FontFlags then flags = ns.hui.FontFlags("OUTLINE") end
    return FONT_BASE, size, flags
end

local function SetFont(fs, size)
    local a, b, c = Fnt(size)
    if a and fs.SetFont then fs:SetFont(a, b, c) end
end

local function SetIcon(tex, path)
    if type(path) == "string" and path ~= "" then
        tex:SetTexture(path)
    else
        tex:SetTexture(FALLBACK_ICON)
    end
end

local function ClassIconPath(cls)
    return TT.CLASS_ICON_DIR .. "ClassIcon_" .. cls:sub(1, 1) .. cls:sub(2):lower()
end

local function MakeIconTile(parent, size)
    local fr = CreateFrame("Frame", nil, parent)
    fr:SetSize(size, size)
    local tex = fr:CreateTexture(nil, "ARTWORK")
    tex:SetAllPoints()
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(tex) end
    return fr, tex
end

local function FSHeight(fs)
    local h = fs.GetStringHeight and fs:GetStringHeight()
    return tonumber(h) or 16
end

local function TextChars(s)
    local n, i, len = 0, 1, #s
    while i <= len do
        local c = string.byte(s, i)
        local step = 1
        if c >= 240 then step = 4
        elseif c >= 224 then step = 3
        elseif c >= 192 then step = 2 end
        i = i + step
        n = n + 1
    end
    return n
end

local function MobileCls()
    local _, cls = UnitClass("player")
    return cls
end

local function PatchBadge(frame)
    if not frame.SetBackdrop then return end
    frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
end

local G
local function EnsureCG()
    if not G then
        local cg = ns.EnsureClassGuide and ns.EnsureClassGuide() or nil
        G = (cg and type(cg.specs) == "table") and cg or nil
    end
    return G
end

TT.CLASS_ORDER = { "WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "SHAMAN", "MAGE", "WARLOCK", "DRUID" }

TT.SPEC_ART = {
    WARRIOR = { arms = "WarriorArms", fury = "WarriorFury", prot = "WarriorProtection" },
    PALADIN = { holy = "PaladinHoly", prot = "PaladinProtection", ret = "PaladinCombat" },
    HUNTER = { bm = "HunterBeastMastery", mm = "HunterMarksmanship", surv = "HunterSurvival" },
    ROGUE = { assa = "RogueAssassination", combat = "RogueCombat", sub = "RogueSubtlety" },
    PRIEST = { disc = "PriestDiscipline", holy = "PriestHoly", shadow = "PriestShadow" },
    SHAMAN = { ele = "ShamanElementalCombat", enh = "ShamanEnhancement", resto = "ShamanRestoration" },
    MAGE = { arcane = "MageArcane", fire = "MageFire", frost = "MageFrost" },
    WARLOCK = { affli = "WarlockCurses", demo = "WarlockSummoning", destro = "WarlockDestruction" },
    DRUID = { balance = "DruidBalance", feral = "DruidFeralCombat", resto = "DruidRestoration" },
}
TT.SPEC_ART_DIR = "Interface\\TalentFrame\\"
TT.SPEC_ART_ALPHA = 0.75
TT.SPEC_ART_SUFFIX = "-TopLeft"
TT.SPEC_ART_RATIO = (0.8 * 246) / ((2 / 3) * 442)

TT.SEC_TITLE = {
    changes = L["改动速览"],
    viability = L["定位评估"],
    sw = L["优缺点"],
    beginner = L["新手上手"],
    systems = L["职业系统"],
    rotation = L["输出循环"],
    stats = L["属性优先级"],
    races = L["种族推荐"],
    prof = L["专业推荐"],
}

TT.MODE_TITLE = {
    rotation = L["输出循环"],
    macro = L["宏命令"],
    cq = L["职业任务"],
    text = L["文字攻略"],
}

TT.RACE_SIDE = {
    alliance = L["联盟"],
    horde = L["部落"],
    both = L["新增"],
}
TT.RACE_ORDER = { "alliance", "horde", "both" }

local function SpellName(id)
    if not id then return nil end
    local nm
    if C_Spell and C_Spell.GetSpellInfo then
        local info = C_Spell.GetSpellInfo(id)
        nm = info and info.name
    end
    if (type(nm) ~= "string" or nm == "") and type(GetSpellInfo) == "function" then
        nm = GetSpellInfo(id)
    end
    if type(nm) == "string" and nm ~= "" then return nm end
    return format(L["法术 #%d"], id)
end

local function Spellify(text)
    if type(text) ~= "string" or text == "" then return text or "" end
    if not string.find(text, "|s", 1, true) then return text end
    return string.gsub(text, "|s(%d+)|", function(id)
        local nm = SpellName(tonumber(id))
        return format("|cff71d5ff|Hspell:%s|h[%s]|h|r", id, nm)
    end)
end

local function Prep(text)
    if type(text) ~= "string" then return tostring(text or "") end
    local s = string.gsub(text, "|l|", "\n")
    return Spellify(s)
end

local function HyperTip(frame, link)
    if not link or not GameTooltip then return end
    GameTooltip:SetOwner(frame, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, link)
    if not ok or (GameTooltip.NumLines and (GameTooltip:NumLines() or 0) == 0) then
        GameTooltip:AddLine(link, 0.8, 0.8, 0.8, true)
    end
    GameTooltip:Show()
end

local function Cardify(frame, alpha)
    if ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(frame, 6, nil, ns.hui.layer.L2)
    elseif frame.SetBackdrop then
        frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        frame:SetBackdropColor(1, 1, 1, alpha or 0.03)
    end
end

local function SkinChip(frame)
    if ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(frame, 6, nil, ns.hui.layer.L3)
    elseif frame.SetBackdrop then
        frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        frame:SetBackdropColor(1, 1, 1, 0.06)
    end
end

local function RoundButtonFill(bt)
    if not (ns.hui and ns.hui.BuildRoundedBG) then return end
    bt:SetBackdrop({ edgeFile = "Interface/ChatFrame/ChatFrameBackground", edgeSize = 1 })
    bt:SetBackdropBorderColor(0, 0, 0, 0)
    if bt.SetBackdropColor then bt:SetBackdropColor(0, 0, 0, 0) end
    bt.__roundFill = ns.hui.BuildRoundedBG(bt, 6, ns.hui.layer.L3, "both", false)
end
TT.RoundButtonFill = RoundButtonFill

local function SetClassBase(cb, on)
    if cb.__base then
        for _, t in ipairs(cb.__base) do t:SetShown(on) end
    elseif cb.bg then
        cb.bg:SetShown(on)
    end
end

local function SetClassHover(cb, on)
    if cb.__hovc then
        for _, t in ipairs(cb.__hovc) do t:SetShown(on) end
    end
end

local function PaintCell(cell, own, hover)
    if cell.__own or cell.__hov then
        local hv = hover == true
        if cell.__hov then
            for _, t in ipairs(cell.__hov) do t:SetShown(hv) end
        end
        if cell.__own then
            for _, t in ipairs(cell.__own) do t:SetShown(own == true and not hv) end
        end
    elseif cell.bg then
        cell.bg:SetShown(own == true or hover == true)
    end
end

local function CellTip(cell)
    local rec, cls = cell.rec, cell.cls
    if not rec then return end
    GameTooltip:SetOwner(cell, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local tc = TT.COLOR[cell.tierKey] or TT.COLOR.D
    GameTooltip:AddLine(format(L["%s 档"], cell.tierKey), tc[1], tc[2], tc[3])
    local cr, cg, cb = ClassColor(cls)
    GameTooltip:AddLine(ClassName(cls) .. " · " .. rec.name, cr, cg, cb)
    if rec.nameEn and rec.nameEn ~= "" then
        GameTooltip:AddLine(rec.nameEn, 0.6, 0.6, 0.6)
    end
    if cls == cell.own then
        GameTooltip:AddLine(L["你的职业"], 0.47, 0.75, 0.45)
    end
    GameTooltip:Show()
end

local function BuildNav(page)
    TT.nav = {}
    local label = MakeFS(page, TT.NAV_HEAD_FS, C_GREY, "LEFT")
    label:SetPoint("TOPLEFT", page, "TOPLEFT", TT.NAV_X + TT.NAV_PAD + 2, -TT.NAV_HEAD_Y)
    label:SetText(L["指南"])
    TT.navLabel = label

    local bt = NewButton(page, L["职业排行"], TT.NAV_W, TT.NAV_ITEM_H, TT.NAV_FS)
    bt:SetPoint("TOPLEFT", page, "TOPLEFT", TT.NAV_X + TT.NAV_PAD, -TT.NAV_RANK_Y)
    MakeOutline(bt, 1, 0.82, 0)
    SetOutline(bt, true, 1, 0.82, 0)
    bt.__huiKeepTextColor = true
    bt.__name = L["职业排行"]
    local fs = bt:GetFontString()
    fs:ClearAllPoints()
    fs:SetPoint("LEFT", bt, "LEFT", 5 + TT.NAV_ICON + 5, 0)
    fs:SetJustifyH("LEFT")
    local btile, bicon = MakeIconTile(bt, TT.NAV_ICON)
    btile:SetPoint("LEFT", bt, "LEFT", 5, 0)
    SetIcon(bicon, "Interface\\Icons\\inv_misc_book_11")
    bt.__tile = btile
    bt.__icon = bicon
    bt:SetScript("OnClick", function()
        DB().nav = "rank"
        TT.RequestRender()
        ns.PlaySound(1)
    end)
    TT.navBtn = bt

    G = EnsureCG()
    if not G then return end
    local glabel = MakeFS(page, TT.NAV_HEAD_FS, C_GREY, "LEFT")
    glabel:SetPoint("TOPLEFT", page, "TOPLEFT", TT.NAV_X + TT.NAV_PAD + 2, -TT.NAV_GROUP_Y)
    glabel:SetText(L["专精指南"])
    TT.navGroup = glabel

    TT.classBtns = {}
    local y = TT.NAV_FIRST_Y
    for _, cls in ipairs(TT.CLASS_ORDER) do
        if G.specs[cls] then
            local cb = NewButton(page, ClassName(cls), TT.NAV_W, TT.NAV_ITEM_H, TT.NAV_FS)
            if not (ns.hui and ns.hui.BuildCapsule) then
                cb:SetHighlightTexture("Interface\\Buttons\\WHITE8x8")
                local hl = cb:GetHighlightTexture()
                if hl then hl:SetAlpha(0.08) end
            end
            MakeOutline(cb, 1, 0.82, 0)
            SetOutline(cb, false, 1, 0.82, 0)
            cb.__huiKeepTextColor = true
            local cfs = cb:GetFontString()
            cfs:ClearAllPoints()
            cfs:SetPoint("LEFT", cb, "LEFT", 5 + TT.NAV_ICON + 5, 0)
            cfs:SetJustifyH("LEFT")
            if ns.hui and ns.hui.BuildCapsule then
                cb.__base = ns.hui.BuildCapsule(cb, 8, ns.hui.layer.L2, 1, 2)
                cb.__hovc = ns.hui.BuildCapsule(cb, 8, ns.hui.layer.L4, 1, 2)
                for _, t in ipairs(cb.__base) do t:Hide() end
                for _, t in ipairs(cb.__hovc) do t:Hide() end
            else
                cb.bg = cb:CreateTexture(nil, "BACKGROUND", nil, 2)
                cb.bg:SetAllPoints()
                cb.bg:SetColorTexture(1, 1, 1, 0.04)
                cb.bg:Hide()
            end
            local tile, ic = MakeIconTile(cb, TT.NAV_ICON)
            tile:SetPoint("LEFT", cb, "LEFT", 5, 0)
            SetIcon(ic, ClassIconPath(cls))
            cb:SetScript("OnClick", function()
                TT.OpenSpec(cls)
            end)
            cb:SetScript("OnEnter", function(self)
                SetClassHover(self, true)
                if not self.__hovc and self.bg then self.bg:Show() end
            end)
            cb:SetScript("OnLeave", function(self)
                SetClassHover(self, false)
                if not self.__hovc and self.bg then self.bg:Hide() end
            end)
            cb.__cls = cls
            cb.__txt = cfs
            cb.__icon = ic
            cb.__tile = tile
            TT.classBtns[cls] = cb
            cb:SetPoint("TOPLEFT", page, "TOPLEFT", TT.NAV_X + TT.NAV_PAD, -y)
            y = y + TT.NAV_ITEM_STEP
        end
    end
end

local function BuildSubTabs(page)
    TT.subBtns = {}
    local x = 0
    for _, p in ipairs(T.pages) do
        local bt = NewButton(page, TT.PAGE_NAME[p.key] or p.key, TT.SUB_W, TT.SUB_H, TT.TAB_FS)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", TT.RIGHT_X + x, -TT.SUB_Y)
        bt:SetScript("OnClick", function()
            DB().tab = p.key
            DB().nav = "rank"
            TT.RequestRender()
            ns.PlaySound(1)
        end)
        TT.subBtns[p.key] = bt
        x = x + TT.SUB_STEP
    end

    G = EnsureCG()
    if not G then return end
    TT.specTabs = {}
    for i = 1, 3 do
        local bt = NewButton(page, "", TT.SPEC_BTN_W, TT.SUB_H, TT.TAB_FS)
        MakeOutline(bt, 1, 0.82, 0)
        RoundButtonFill(bt)
        bt.__huiKeepTextColor = true
        bt:SetPoint("TOPLEFT", page, "TOPLEFT",
            TT.RIGHT_X + TT.SPEC_TITLE_X + (i - 1) * (TT.SPEC_BTN_W + TT.SPEC_BTN_GAP), -TT.SPEC_BTN_Y)
        bt:Hide()
        bt:SetScript("OnClick", function()
            local db = DB()
            if bt.__specKey then
                db.spec = bt.__specKey
                TT.RequestRender()
                ns.PlaySound(1)
            end
        end)
        TT.specTabs[i] = bt
    end

    TT.modeBtns = {}
    local mcount = #TT.MODE_KEYS
    local mavail = TT.RIGHT_W - 2 * TT.INSET
    local mw = math.floor((mavail - (mcount - 1) * TT.MODE_GAP) / mcount)
    local mx = TT.RIGHT_X + TT.INSET
    for i, key in ipairs(TT.MODE_KEYS) do
        local w = mw
        if i == mcount then w = mavail - (mcount - 1) * (mw + TT.MODE_GAP) end
        local bt = NewButton(page, TT.MODE_TITLE[key], w, TT.MODE_H, TT.TAB_FS)
        MakeOutline(bt, 1, 0.82, 0)
        RoundButtonFill(bt)
        bt.__huiKeepTextColor = true
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", mx, -TT.MODE_Y)
        mx = mx + w + TT.MODE_GAP
        bt.__modeKey = key
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            DB().mode = self.__modeKey
            TT.RequestRender()
            ns.PlaySound(1)
        end)
        TT.modeBtns[i] = bt
    end
end

local RenderSpec

local function BuildSecTabs(page)
    G = EnsureCG()
    if not G then return end
    TT.secTabs = {}
    for i = 1, TT.SEC_TAB_MAX do
        local bt = NewButton(page, "", 60, TT.SEC_TAB_H, TT.TAB_FS)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", TT.RIGHT_X + 8, -TT.SEC_TAB_Y)
        bt:SetScript("OnClick", function(self)
            if self.__secKey then
                DB().sec = self.__secKey
                RenderSpec()
                ns.PlaySound(1)
            end
        end)
        bt:Hide()
        TT.secTabs[i] = bt
    end
end

local function BuildCards(parent)
    TT.cards = {}
    local maxSpecs = 0
    for _, p in ipairs(T.pages) do
        for _, t in ipairs(p.tiers or {}) do
            local n = #(t.specs or {})
            if n > maxSpecs then maxSpecs = n end
        end
    end
    TT.GRID_ROWS = math.max(1, math.ceil(maxSpecs / TT.GRID_COLS))
    local gridW = TT.CARD_W - 2 * TT.LIST_PAD - TT.BADGE_W - 16
    local cellW = gridW / TT.GRID_COLS
    for i = 1, 5 do
        local card = CreateFrame("Frame", nil, parent)
        card:SetWidth(TT.CARD_W)
        Cardify(card, 0.03)
        local badge = CreateFrame("Frame", nil, card, "BackdropTemplate")
        badge:SetSize(TT.BADGE_W, TT.EMPTY_H)
        local badgeColor = { 1, 1, 1, 1 }
        local badgeRepaint
        if ns.hui and ns.hui.SkinPopup and ns.huiTheme == "hui" then
            ns.hui.SkinPopup(badge, 6, nil, badgeColor)
            local reps = badge.__huiRepaints
            if reps and #reps > 0 then
                badgeRepaint = function()
                    for _, fn in ipairs(reps) do pcall(fn) end
                end
            end
        else
            PatchBadge(badge)
        end
        local letter = MakeFS(badge, 16, TT.BADGE_TEXT, "CENTER")
        letter:SetAllPoints()
        local empty = MakeFS(card, 14, C_GREY, "LEFT")
        empty:SetText(L["本档为空"])
        local cells = {}
        for c = 1, TT.GRID_COLS * TT.GRID_ROWS do
            local cell = CreateFrame("Button", nil, card)
            cell:SetSize(cellW, TT.CELL_H)
            if ns.hui and ns.hui.BuildCapsule then
                cell.__own = ns.hui.BuildCapsule(cell, 4, ns.hui.layer.L2, 0, 2)
                cell.__hov = ns.hui.BuildCapsule(cell, 4, ns.hui.layer.L4, 0, 2)
                for _, t in ipairs(cell.__own) do t:Hide() end
                for _, t in ipairs(cell.__hov) do t:Hide() end
            else
                cell.bg = cell:CreateTexture(nil, "BACKGROUND")
                cell.bg:SetAllPoints()
                cell.bg:SetColorTexture(1, 1, 1, 0.05)
                cell.bg:Hide()
            end
            local ic = CreateFrame("Frame", nil, cell)
            ic:SetSize(TT.ICON, TT.ICON)
            ic:SetPoint("TOP", cell, "TOP", 0, 0)
            cell.icon = ic:CreateTexture(nil, "ARTWORK")
            cell.icon:SetAllPoints()
            cell.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(cell.icon) end
            cell.name = MakeFS(cell, 14, C_TEXT, "CENTER")
            cell.name:SetPoint("TOP", ic, "BOTTOM", 0, 0)
            cell.name:SetWordWrap(false)
            cell:RegisterForClicks("LeftButtonUp")
            cell:SetScript("OnEnter", function(self)
                PaintCell(self, self.own, true)
                CellTip(self)
            end)
            cell:SetScript("OnLeave", function(self)
                PaintCell(self, self.own, false)
                GameTooltip:Hide()
            end)
            cell:SetScript("OnClick", function(self)
                local cg = EnsureCG()
                if self.cls and self.spec and cg and cg.specs[self.cls] and cg.specs[self.cls][self.spec] then
                    TT.OpenSpec(self.cls, self.spec)
                end
            end)
            cells[c] = cell
        end
        TT.cards[i] = { frame = card, badge = badge, letter = letter, empty = empty, cells = cells, cellW = cellW, badgeColor = badgeColor, badgeRepaint = badgeRepaint }
    end
end

local function BuildNotes(parent)
    TT.factorTitle = MakeFS(parent, 14, C_WHITE, "LEFT")
    TT.factorTitle:SetText(L["排名依据"])
    TT.factorRows = {}
    for i = 1, 6 do
        local row = MakeFS(parent, 14, C_DIM, "LEFT")
        TT.factorRows[i] = row
    end
    TT.noteRows = {}
    for i = 1, 10 do
        local row = MakeFS(parent, 14, C_DIM, "LEFT")
        TT.noteRows[i] = row
    end
end

local function BuildSpecHero(page)
    G = EnsureCG()
    if not G then return end
    local topCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
    if ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(topCard, 6, nil, ns.hui.layer.L2)
    else
        topCard:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        topCard:SetBackdropColor(0.086, 0.102, 0.133, 1)
        topCard:SetBackdropBorderColor(1, 1, 1, 0.1)
    end
    topCard:SetPoint("TOPLEFT", page, "TOPLEFT", TT.RIGHT_X, -TT.TOPCARD_TOP)
    topCard:SetSize(TT.RIGHT_W, TT.TOPCARD_H)
    topCard:Hide()
    TT.specTopCard = topCard

    local art = CreateFrame("Frame", nil, topCard)
    art:SetAllPoints(topCard)
    local AW, AH = TT.RIGHT_W, TT.TOPCARD_H
    local A = TT.SPEC_ART_RATIO
    local s = math.max(AW / A, AH)
    local artW, artH = A * s, s
    local ox, oy = (AW - artW) / 2, (AH - artH) / 2
    local artTex = art:CreateTexture(nil, "BACKGROUND", nil, 2)
    artTex:SetAlpha(TT.SPEC_ART_ALPHA)
    artTex:SetPoint("TOPLEFT", art, "TOPLEFT", 0, 0)
    artTex:SetSize(AW, AH)
    artTex:SetTexCoord(-ox / artW, (AW - ox) / artW, -oy / artH, (AH - oy) / artH)
    artTex:Hide()
    TT.specArt, TT.specArtTex = art, artTex

    local hero = CreateFrame("Frame", nil, page)
    hero:SetPoint("TOPLEFT", page, "TOPLEFT", TT.RIGHT_X + TT.INSET, -TT.HERO_ICON_Y)
    hero:SetSize(TT.RIGHT_W - 2 * TT.INSET, TT.HERO_H)
    hero:Hide()
    TT.hero = hero

    local iconFrame = CreateFrame("Frame", nil, hero)
    iconFrame:SetSize(TT.SPEC_ICON, TT.SPEC_ICON)
    iconFrame:SetPoint("TOPLEFT", hero, "TOPLEFT", 0, -(TT.HERO_H - TT.SPEC_ICON) / 2)
    local icon = iconFrame:CreateTexture(nil, "ARTWORK")
    icon:SetAllPoints()
    icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(icon) end
    TT.heroIcon = icon

    local tx = TT.SPEC_ICON + 10
    local title = MakeFS(hero, 16, C_WHITE, "LEFT")
    title:SetPoint("TOPLEFT", hero, "TOPLEFT", tx, -2)
    TT.specTitle = title

    local meta = MakeFS(page, 14, C_GREY, "LEFT")
    meta:SetPoint("RIGHT", page, "TOPRIGHT", -(TT.EDGE + TT.INSET), -TT.SPEC_META_Y)
    TT.specMeta = meta

    local grade = MakeFS(hero, 14, C_GREY, "RIGHT")
    grade:SetPoint("TOPRIGHT", hero, "TOPRIGHT", 0, -2)
    TT.heroGrade = grade

    local sep = topCard:CreateTexture(nil, "ARTWORK")
    sep:SetHeight(1)
    sep:SetColorTexture(1, 1, 1, 0.08)
    sep:SetPoint("TOPLEFT", topCard, "TOPLEFT", TT.INSET, -(TT.MODE_Y - TT.TOPCARD_TOP - 4))
    sep:SetWidth(TT.RIGHT_W - 2 * TT.INSET)
    TT.topSep = sep
end

local UpdateScrollUI, CullScrollContent, TierWheel

local function BuildSpecPool(parent)
    G = EnsureCG()
    if not G then return end
    local child = TT.child

    TT.scCards = {}
    for i = 1, TT.CARD_MAX do
        local fr = CreateFrame("Frame", nil, child)
        fr:SetWidth(TT.FULL_W)
        fr:Hide()
        local title = MakeFS(fr, 14, C_WHITE, "LEFT")
        title:SetPoint("TOPLEFT", fr, "TOPLEFT", TT.CARD_PAD, -TT.CARD_PAD)
        local divider = fr:CreateTexture(nil, "ARTWORK")
        divider:SetWidth(1)
        divider:SetColorTexture(1, 1, 1, 0.1)
        divider:Hide()
        TT.scCards[i] = { frame = fr, title = title, divider = divider, n = 0, H = 0 }
    end

    TT.rowPool = {}
    for i = 1, TT.ROW_MAX do
        local fs = MakeFS(TT.rowHost, 14, C_TEXT, "LEFT")
        fs:SetWordWrap(true)
        fs:Hide()
        if fs.EnableHyperlinks then
            fs:EnableHyperlinks()
        elseif fs.SetHyperlinksEnabled then
            fs:SetHyperlinksEnabled(true)
        end
        TT.rowPool[i] = fs
    end

    TT.chipPool = {}
    for i = 1, TT.CHIP_MAX do
        local cf = CreateFrame("Frame", nil, child)
        cf:SetHeight(TT.CHIP_H)
        cf:Hide()
        SkinChip(cf)
        local cfs = MakeFS(cf, 14, C_TEXT, "CENTER")
        cfs:SetPoint("CENTER", cf, "CENTER", 0, 0)
        TT.chipPool[i] = { frame = cf, fs = cfs }
    end

    local topLvl = 0
    for i = 1, TT.CARD_MAX do
        local lv = TT.scCards[i] and TT.scCards[i].frame:GetFrameLevel() or 0
        if lv > topLvl then topLvl = lv end
    end
    TT.rowHost:SetFrameLevel(topLvl + 1)

    local fr = child
    fr:EnableMouse(true)
    if fr.SetHyperlinksEnabled then
        fr:SetHyperlinksEnabled(true)
    end
    fr:SetScript("OnHyperlinkEnter", HyperTip)
    fr:SetScript("OnHyperlinkLeave", function() GameTooltip:Hide() end)
    fr:SetScript("OnMouseWheel", function(_, delta)
        TierWheel(delta)
    end)
end

local function TakeSpecCard()
    TT.__cards = (TT.__cards or 0) + 1
    return TT.scCards[TT.__cards]
end

local function Elide()
    local card = TT.__cur
    if not card or not card.lastFS or card.elided then return end
    card.elided = true
    local fs = card.lastFS
    local txt = fs.GetText and fs:GetText()
    if type(txt) ~= "string" then txt = "" end
    if string.sub(txt, -3) ~= "…" then
        fs:SetText(txt .. "…")
    end
    local nh = FSHeight(fs)
    local d = nh - (card.lastH or 0)
    if d > 0.01 then
        card.elideDelta = (card.elideDelta or 0) + d
    end
    card.lastH = nh
end

local function TakeRowFS()
    TT.__rows = (TT.__rows or 0) + 1
    local fs = TT.rowPool[TT.__rows]
    if not fs then
        TT.__overflow = (TT.__overflow or 0) + 1
        Elide()
        return nil
    end
    return fs
end

local function TakeSpecChip()
    TT.__chips = (TT.__chips or 0) + 1
    return TT.chipPool[TT.__chips]
end

local function PutRow(text, size, color, x, y, w)
    local card = TT.__cur
    local fs = TakeRowFS()
    if not fs then return nil end
    card.n = card.n + 1
    SetFont(fs, size)
    fs:SetWidth(w)
    fs:SetText(Prep(text))
    fs:SetTextColor(color[1], color[2], color[3])
    fs:Show()
    local h = FSHeight(fs)
    fs:ClearAllPoints()
    fs:SetPoint("TOPLEFT", card.frame, "TOPLEFT", x, y)
    fs.__cy, fs.__ch = -y, h
    fs.__cgen = TT.__renderGen
    card.lastFS = fs
    card.lastH = h
    return h
end

local function AddRow(text, size, color, indent, gap, w)
    local w2 = w or (TT.__innerW - (indent or 0))
    local h = PutRow(text, size, color, TT.CARD_PAD + (indent or 0), TT.__cy, w2)
    if not h then return false end
    TT.__cy = TT.__cy - h - (gap or TT.HELP_ROW)
    return true
end

local function AddPair(goods, bads, innerW)
    local card = TT.__cur
    local gap = TT.PAIR_GAP
    local colW = math.floor((innerW - (gap * 2 + 1)) / 2)
    local leftX = TT.CARD_PAD
    local lineX = TT.CARD_PAD + colW + gap
    local rightX = lineX + 1 + gap
    local startY = TT.__cy
    local ly, ry = startY, startY
    for _, item in ipairs(goods) do
        local h = PutRow(item, 14, TT.GOOD, leftX, ly, colW)
        if not h then break end
        ly = ly - h - TT.HELP_ROW
    end
    for _, item in ipairs(bads) do
        local h = PutRow(item, 14, TT.BAD, rightX, ry, colW)
        if not h then break end
        ry = ry - h - TT.HELP_ROW
    end
    local bot = math.max(ly, ry)
    card.pairLineX = lineX
    card.pairBot = bot
    card.divider:ClearAllPoints()
    card.divider:SetPoint("TOPLEFT", card.frame, "TOPLEFT", lineX, startY - 1)
    card.divider:SetPoint("BOTTOMLEFT", card.frame, "TOPLEFT", lineX, bot + 5)
    card.divider:Show()
    card.divider.__cy = -(bot + 5)
    card.divider.__ch = (bot - startY) + 6
    card.divider.__cgen = TT.__renderGen
    TT.__cy = bot - TT.SPEC_GAP
end

local function AddRaces(items, innerW)
    local card = TT.__cur
    local groups = {}
    local seen = {}
    local order = {}
    for _, r in ipairs(items) do
        local name = r.race or r.name or ""
        local side = r.side or "both"
        if not groups[side] then
            groups[side] = {}
            seen[side] = true
            order[#order + 1] = side
        end
        groups[side][#groups[side] + 1] = { name = name, mark = r.mark }
    end
    local seq = {}
    for _, s in ipairs(TT.RACE_ORDER) do
        if groups[s] then seq[#seq + 1] = s end
    end
    for _, s in ipairs(order) do
        if not (s == "alliance" or s == "horde" or s == "both") then seq[#seq + 1] = s end
    end
    for _, side in ipairs(seq) do
        local label = TT.RACE_SIDE[side] or side
        local rowY = TT.__cy
        local lfs = TakeRowFS()
        if not lfs then break end
        card.n = card.n + 1
        SetFont(lfs, 14)
        lfs:SetWidth(innerW)
        lfs:SetText(label)
        lfs:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
        local lw = tonumber(lfs:GetStringWidth()) or 30
        lfs:ClearAllPoints()
        lfs:SetPoint("TOPLEFT", card.frame, "TOPLEFT", TT.CARD_PAD, rowY)
        lfs:Show()
        card.lastFS = lfs
        card.lastH = FSHeight(lfs)
        lfs.__cy, lfs.__ch = -rowY, card.lastH
        lfs.__cgen = TT.__renderGen
        local cx = TT.CARD_PAD + lw + TT.CHIP_GAP
        local cy2 = rowY
        for _, item in ipairs(groups[side]) do
            local chip = TakeSpecChip()
            if not chip then break end
            local text = ((item.mark == "star") and "★" or "") .. item.name
            local cfs = chip.fs
            cfs:SetText(text)
            chip.frame:Show()
            local tw = tonumber(cfs:GetStringWidth()) or 30
            local cw = math.max(24, tw + 12)
            if cx + cw > TT.CARD_PAD + innerW then
                cx = TT.CARD_PAD
                cy2 = cy2 - TT.CHIP_H - TT.HELP_ROW
            end
            chip.frame:SetWidth(cw)
            chip.frame:ClearAllPoints()
            chip.frame:SetPoint("TOPLEFT", card.frame, "TOPLEFT", cx, cy2)
            chip.frame.__cy, chip.frame.__ch = -cy2, TT.CHIP_H
            chip.frame.__cgen = TT.__renderGen
            cx = cx + cw + TT.CHIP_GAP
        end
        TT.__cy = cy2 - TT.CHIP_H - TT.HELP_HEAD
    end
end

local function SectionSpan(sec)
    local hasGood, hasBad = false, false
    for _, e in ipairs(sec.flow or {}) do
        if e.t == "good" and e.v and #e.v > 0 then hasGood = true end
        if e.t == "bad" and e.v and #e.v > 0 then hasBad = true end
    end
    if hasGood and hasBad then return TT.SPAN_FULL end
    for _, e in ipairs(sec.flow or {}) do
        if e.t == "tb" or e.t == "races" then return TT.SPAN_FULL end
    end
    return 1
end

local function SectionHas(sec)
    for _, e in ipairs(sec.flow or {}) do
        local t = e.t
        if t == "p" or t == "h4" then
            if type(e.v) == "string" and e.v ~= "" then return true end
        elseif e.v and #e.v > 0 then
            return true
        end
    end
    return false
end

local function SpecSectionKeys(data)
    local have = {}
    for _, sec in ipairs(data.sections or {}) do
        local k = sec.key
        if k and TT.SEC_TITLE[k] and SectionHas(sec) then have[k] = true end
    end
    local keys = {}
    for _, k in ipairs(TT.SEC_ORDER) do
        if have[k] then keys[#keys + 1] = k end
    end
    return keys
end

local function SecTabWidth(bt, text)
    bt:SetWidth(TT.RIGHT_W)
    bt:SetText(text)
    local fs = bt.GetFontString and bt:GetFontString()
    local n
    if fs and fs.GetStringWidth then n = tonumber(fs:GetStringWidth()) end
    if not n or n <= 0 then n = TextChars(text) * TT.TAB_FS end
    return n
end

local function PaintSecTabs(data)
    local db = DB()
    local keys = SpecSectionKeys(data)
    local tabs = TT.secTabs
    if not tabs then return keys end
    local n = #keys
    if n > 0 then
        local found = false
        for _, k in ipairs(keys) do
            if k == db.sec then found = true break end
        end
        if not found then db.sec = keys[1] end
    end
    local sel = n > 0 and db.sec or nil
    local maxW = n > 0 and math.floor((TT.RIGHT_W - (n - 1) * TT.SEC_TAB_STEP) / n) or 48
    local x = 0
    for i = 1, TT.SEC_TAB_MAX do
        local bt = tabs[i]
        if bt and i <= n then
            local key = keys[i]
            local w = SecTabWidth(bt, TT.SEC_TITLE[key] or key)
            w = math.max(48, math.min(w + TT.SEC_TAB_PAD, maxW))
            bt:SetWidth(w)
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", TT.page, "TOPLEFT", TT.RIGHT_X + 8 + x, -TT.SEC_TAB_Y)
            x = x + w + TT.SEC_TAB_STEP
            bt.__secKey = key
            local on = (key == sel)
            SetOutline(bt, on, 1, 0.82, 0)
            bt:GetFontString():SetTextColor(Unpack(on and C_WHITE or C_DIM))
            bt.__sel = on and true or false
            bt:Show()
        elseif bt then
            bt.__sel = false
            bt:Hide()
        end
    end
    return keys
end

local function BuildSpecCard(sec)
    local card = TakeSpecCard()
    if not card then return nil end
    local span = TT.SPAN_FULL
    local w = TT.FULL_W
    local innerW = TT.INNER_FULL_W
    card.frame:SetWidth(w)
    card.frame:Show()
    card.divider:Hide()
    card.title:Hide()
    card.n = 0
    card.lastFS = nil
    card.lastH = 0
    card.elided = false
    card.elideDelta = 0
    card.pairLineX = nil
    card.pairBot = nil

    TT.__cur = card
    TT.__innerW = innerW
    TT.__cy = -TT.CARD_PAD

    local goods, bads = {}, {}
    for _, e in ipairs(sec.flow or {}) do
        if e.t == "good" then
            for _, item in ipairs(e.v or {}) do goods[#goods + 1] = item end
        elseif e.t == "bad" then
            for _, item in ipairs(e.v or {}) do bads[#bads + 1] = item end
        end
    end
    local pair = (#goods > 0) and (#bads > 0)
    local pairDone = false

    for _, e in ipairs(sec.flow or {}) do
        local t = e.t
        if t == "good" or t == "bad" then
            if not pairDone then
                pairDone = true
                if pair then
                    AddPair(goods, bads, innerW)
                else
                    local items = (#goods > 0) and goods or bads
                    for _, item in ipairs(items) do
                        if not AddRow(item, 14, C_TEXT, 0, TT.CHIP_GAP, TT.SEC_TEXT_W) then break end
                    end
                end
            end
        elseif t == "tb" then
            for _, cells in ipairs(e.v or {}) do
                if type(cells) == "table" then
                    local label = tostring(cells[1] or "")
                    local rest = {}
                    for i = 2, #cells do
                        local cc = cells[i]
                        if cc ~= nil and cc ~= "" then rest[#rest + 1] = tostring(cc) end
                    end
                    local body = table.concat(rest, "　")
                    if label ~= "" then
                        if not AddRow(label, 14, C_GOLD, 0, body ~= "" and 3 or 9) then break end
                    end
                    if body ~= "" then
                        if not AddRow(body, 14, C_TEXT, 0, 9) then break end
                    end
                end
            end
        elseif t == "ul" then
            for _, it in ipairs(e.v or {}) do
                local term, txt = it.term or "", it.text or ""
                if txt ~= "" then
                    if term ~= "" then
                        if not AddRow(term, 14, C_GOLD, 0, 3, TT.SEC_TEXT_W) then break end
                    end
                    if not AddRow(txt, 14, C_TEXT, 0, 6, TT.SEC_TEXT_W) then break end
                elseif term ~= "" then
                    if not AddRow(term, 14, C_GOLD, 0, 6, TT.SEC_TEXT_W) then break end
                end
            end
        elseif t == "races" then
            AddRaces(e.v or {}, innerW)
        elseif t == "h4" then
            TT.__cy = TT.__cy - TT.HELP_HEAD
            if not AddRow(e.v, 14, C_WHITE, 0, 8, TT.SEC_TEXT_W) then break end
        else
            if type(e.v) == "string" and e.v ~= "" then
                if not AddRow(e.v, 14, C_TEXT, 0, 6, TT.SEC_TEXT_W) then break end
            end
        end
    end

    if (card.elideDelta or 0) > 0.01 then
        TT.__cy = TT.__cy - card.elideDelta
        if card.pairLineX and card.pairBot and card.divider:IsShown() then
            card.divider:SetPoint("BOTTOMLEFT", card.frame, "TOPLEFT",
                card.pairLineX, card.pairBot - card.elideDelta + 5)
        end
    end
    card.H = -TT.__cy + TT.CARD_PAD
    card.frame:SetHeight(card.H)
    return { card = card, span = span }
end

TT.PaintHeader = function()
    if TT.specTopCard then TT.specTopCard:Show() end
    if TT.topSep then TT.topSep:Show() end
    G = EnsureCG()
    if not G then return nil end
    local db = DB()
    local cls = db.cls or TT.CLASS_ORDER[1]
    local rec = G.specs[cls]
    if not rec then
        for _, c in ipairs(TT.CLASS_ORDER) do
            if G.specs[c] then cls = c rec = G.specs[c] break end
        end
        if not rec then return nil end
    end
    local spec = db.spec
    if not spec or not rec[spec] then
        local list = T.specs and T.specs[cls]
        if list then
            for _, sp in ipairs(list) do
                if rec[sp.key] then spec = sp.key break end
            end
        end
        if not spec or not rec[spec] then
            spec = next(rec)
        end
    end
    db.cls, db.spec = cls, spec
    local data = rec[spec]
    local spRec = SpecRec(cls, spec)

    local cr, cg, cb = ClassColor(cls)
    TT.specTitle:SetText(ClassName(cls) .. " · " .. (spRec and spRec.name or spec))
    TT.specTitle:SetTextColor(cr, cg, cb)
    TT.specMeta:SetText("")
    TT.specMeta:Hide()
    SetIcon(TT.heroIcon, spRec and spRec.icon)
    local gk, pk = SpecGrade(cls, spec)
    if gk then
        local gc = TT.COLOR[gk] or TT.COLOR.D
        TT.heroGrade:SetText(format(L["★ %s级 · %s"], gk, TT.PAGE_NAME[pk] or ""))
        TT.heroGrade:SetTextColor(gc[1], gc[2], gc[3])
        TT.heroGrade:Show()
    else
        TT.heroGrade:Hide()
    end
    TT.hero:Show()
    if TT.specArtTex then
        local artName = (TT.SPEC_ART[cls] or {})[spec]
        local ok, r = false, nil
        if artName then
            ok, r = pcall(TT.specArtTex.SetTexture, TT.specArtTex,
                          TT.SPEC_ART_DIR .. artName .. TT.SPEC_ART_SUFFIX)
        end
        if ok and r ~= false then
            TT.specArtTex:Show()
        else
            TT.specArtTex:Hide()
        end
    end
    return cls, spec, data
end

RenderSpec = function()
    TT.__renderGen = (TT.__renderGen or 0) + 1
    local cls, spec, data = TT.PaintHeader()
    if not data then return end
    local db = DB()

    TT.__rows = 0
    TT.__cards = 0
    TT.__chips = 0
    TT.__overflow = 0

    local keys = PaintSecTabs(data)

    if #keys == 0 then
        TT.curSec = nil
        TT.HideSpecContent()
        TT.child:SetHeight(TT.SPEC_GAP)
        TT.scroll:SetVerticalScroll(0)
        TT.overflowed = false
        return
    end

    local plan
    for _, sec in ipairs(data.sections or {}) do
        if sec.key == db.sec and TT.SEC_TITLE[sec.key] and SectionHas(sec) then
            plan = BuildSpecCard(sec)
            break
        end
    end

    for i = (TT.__cards or 0) + 1, TT.CARD_MAX do
        TT.scCards[i].frame:Hide()
        TT.scCards[i].divider:Hide()
    end
    for i = (TT.__rows or 0) + 1, TT.ROW_MAX do TT.rowPool[i]:Hide() end
    for i = (TT.__chips or 0) + 1, TT.CHIP_MAX do TT.chipPool[i].frame:Hide() end

    TT.curSec = db.sec
    if plan then
        local card = plan.card
        card.frame:ClearAllPoints()
        card.frame:SetPoint("TOPLEFT", TT.child, "TOPLEFT", TT.OUTER_PAD, 0)
        TT.child:SetHeight(card.H + TT.SPEC_GAP)
    else
        TT.child:SetHeight(TT.SPEC_GAP)
    end
    TT.__v = 0
    TT.child:SetPoint("TOPLEFT", TT.scroll, "TOPLEFT", 0, 0)
    CullScrollContent()
    TT.overflowed = (TT.__overflow or 0) > 0
end

local function BuildScroll(page)
    local scroll = CreateFrame("ScrollFrame", nil, page)
    scroll:EnableMouseWheel(true)
    scroll:SetPoint("TOPLEFT", page, "TOPLEFT", TT.RIGHT_X, -TT.BODY_TOP)
    scroll:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT",
                    -(TT.EDGE + TT.INSET), TT.EDGE + TT.INSET)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        TierWheel(delta)
    end)
    scroll:SetScript("OnVerticalScroll", function()
        CullScrollContent()
    end)
    local track = CreateFrame("Frame", nil, scroll, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)
    else
        track:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(7)
    track:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", 7, 0)
    track:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", 7, 0)
    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(5)
    thumb:EnableMouse(true)
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
        thumb.__hov = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L5)
        for _, t in ipairs(thumb.__hov) do t:Hide() end
        thumb:SetScript("OnEnter", function(self)
            for _, t in ipairs(self.__hov) do t:Show() end
        end)
        thumb:SetScript("OnLeave", function(self)
            for _, t in ipairs(self.__hov) do t:Hide() end
        end)
    else
        local tx = thumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
    end
    thumb:SetPoint("TOP", track, "TOP", 0, -1)
    thumb:Hide()
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = TT.__v or 0
        self:SetScript("OnUpdate", function()
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = TT.child:GetHeight() - TT.scroll:GetHeight()
            TT.__v = math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll))
            TT.child:SetPoint("TOPLEFT", TT.scroll, "TOPLEFT", 0, TT.__v)
            CullScrollContent()
            UpdateScrollUI()
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    TT.sbarTrack, TT.sbarThumb = track, thumb
    local child = CreateFrame("Frame", nil, page)
    child:SetSize(TT.FULL_W + 2 * TT.OUTER_PAD, 10)
    child:SetPoint("TOPLEFT", scroll, "TOPLEFT", 0, 0)
    if scroll.SetScrollChild then scroll:SetScrollChild(child) end
    TT.scroll, TT.child = scroll, child
end

CullScrollContent = function()
    local scroll = TT.scroll
    if not scroll then return end
    local viewH = scroll.GetHeight and scroll:GetHeight()
    if type(viewH) ~= "number" then return end
    local vTop, vBot = (TT.__v or 0), (TT.__v or 0) + viewH
    local gen = TT.__renderGen
    local function cull(el)
        if not el or el.__cgen ~= gen then return end
        local cy, ch = el.__cy, el.__ch
        if type(cy) ~= "number" or type(ch) ~= "number" then return end
        local show = ((cy + ch) > vTop) and (cy < vBot)
        if show then
            el:Show()
        else
            el:Hide()
        end
    end
    for i = 1, TT.CARD_MAX do
        local c = TT.cards and TT.cards[i]
        if c then cull(c.frame) end
    end
    cull(TT.factorTitle)
    cull(TT.intro)
    if TT.factorRows then for i = 1, #TT.factorRows do cull(TT.factorRows[i]) end end
    if TT.noteRows then for i = 1, #TT.noteRows do cull(TT.noteRows[i]) end end
    if TT.rowPool then for i = 1, #TT.rowPool do cull(TT.rowPool[i]) end end
    if TT.chipPool then
        for i = 1, #TT.chipPool do
            local chip = TT.chipPool[i]
            if chip then cull(chip.frame) end
        end
    end
    if TT.scCards then
        for i = 1, TT.CARD_MAX do
            local c = TT.scCards[i]
            if c then cull(c.divider) end
        end
    end
    if ns.ClassCombatUI then ns.ClassCombatUI.Cull(gen, vTop, vBot) end
    if ns.ClassQuestUI then ns.ClassQuestUI.Cull(gen, vTop, vBot) end
end

UpdateScrollUI = function()
    local scroll, child = TT.scroll, TT.child
    if not (scroll and child and TT.sbarTrack) then return end
    local viewH, contentH = scroll.GetHeight and scroll:GetHeight(), child.GetHeight and child:GetHeight()
    if type(viewH) ~= "number" or type(contentH) ~= "number" then return end
    if contentH <= viewH + 2 then
        TT.sbarTrack:Hide()
        if TT.sbarThumb then TT.sbarThumb:Hide() end
        return
    end
    TT.sbarTrack:Show()
    TT.sbarTrack:SetFrameLevel(TT.scroll:GetFrameLevel() + 10)
    local trackH = TT.sbarTrack:GetHeight() - 2
    local maxScroll = contentH - viewH
    local frac = math.min(1, math.max(0, (TT.__v or 0) / maxScroll))
    local th = math.max(24, trackH * viewH / contentH)
    local thumb = TT.sbarThumb
    thumb:SetHeight(th)
    thumb:ClearAllPoints()
    thumb:SetPoint("TOP", TT.sbarTrack, "TOP", 0, -1 - frac * (trackH - th))
    thumb:Show()
end

TierWheel = function(delta)
    local maxScroll = math.max(0, (TT.child.GetHeight and TT.child:GetHeight() or 0)
                                  - (TT.scroll.GetHeight and TT.scroll:GetHeight() or 0))
    if type(maxScroll) ~= "number" then return end
    TT.__v = math.max(0, math.min(maxScroll, (TT.__v or 0) - delta * 48))
    TT.child:SetPoint("TOPLEFT", TT.scroll, "TOPLEFT", 0, TT.__v)
    CullScrollContent()
    UpdateScrollUI()
end

function TT.PlaceScroll(top)
    local scroll = TT.scroll
    if not scroll or not TT.page then return end
    scroll:ClearAllPoints()
    scroll:SetPoint("TOPLEFT", TT.page, "TOPLEFT", TT.RIGHT_X, -(top or TT.BODY_TOP))
    scroll:SetPoint("BOTTOMRIGHT", TT.page, "BOTTOMRIGHT",
                    -(TT.EDGE + TT.INSET), TT.EDGE + TT.INSET)
end

function TT.Build(page)
    if TT.built or TT.building then return end
    ns.OpenPerf.Begin("职业指南")
    TT.building = true
    ns.PhasedStart(15, coroutine.create(function()
    TT.page = page

    do
        local navCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
        local contentCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
        navCard:SetPoint("TOPLEFT", page, "TOPLEFT", TT.EDGE, -TT.CARD_TOP)
        navCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", TT.X0 - TT.INSET, TT.EDGE)
        contentCard:SetPoint("TOPLEFT", page, "TOPLEFT", TT.X0, -TT.CARD_TOP)
        contentCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -TT.EDGE, TT.EDGE)
        if ns.hui and ns.hui.SkinPopup then
            ns.hui.SkinPopup(navCard, 6)
            ns.hui.SkinPopup(contentCard, 6)
        else
            for _, f in ipairs({ navCard, contentCard }) do
                f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                                edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
                f:SetBackdropColor(1, 1, 1, 0.03)
                f:SetBackdropBorderColor(1, 1, 1, 0.05)
            end
        end
        TT.navCard, TT.contentCard = navCard, contentCard
    end
    coroutine.yield()

    BuildNav(page)
    BuildSubTabs(page)
    coroutine.yield()
    BuildScroll(page)
    coroutine.yield()

    local child = TT.child
    local rowHost = CreateFrame("Frame", nil, child)
    rowHost:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)
    TT.rowHost = rowHost
    TT.meta = MakeFS(page, 14, C_GREY, "LEFT")
    TT.meta:SetPoint("RIGHT", page, "TOPRIGHT", -(TT.EDGE + TT.INSET), -(TT.SUB_Y + TT.SUB_H / 2))
    TT.intro = MakeFS(TT.rowHost, 14, C_DIM, "LEFT")
    TT.intro:SetWidth(TT.CARD_W - 100)
    coroutine.yield()

    local rankHost = CreateFrame("Frame", nil, page)
    rankHost:SetAllPoints(page)
    rankHost:SetFrameLevel(TT.contentCard:GetFrameLevel() + 4)
    TT.rankHost = rankHost
    BuildCards(rankHost)
    coroutine.yield()
    BuildNotes(TT.rowHost)
    coroutine.yield()
    BuildSpecHero(page)
    BuildSecTabs(page)
    BuildSpecPool(child)
    coroutine.yield()

    TT.built = true
    TT.building = false
    ns.OpenPerf.Mark("就绪")

    do
        local cardLvl = TT.navCard:GetFrameLevel()
        TT.contentCard:SetFrameLevel(cardLvl)
        local tl = CreateFrame("Frame", nil, page)
        tl:SetFrameLevel(cardLvl + 2)
        for _, rg in ipairs({ page:GetRegions() }) do
            rg:SetParent(tl)
        end
        TT.textLayer = tl
        for _, fr in ipairs({ page:GetChildren() }) do
            if fr ~= TT.navCard and fr ~= TT.contentCard and fr ~= tl then
                fr:SetFrameLevel(math.max(fr:GetFrameLevel(), cardLvl + 2))
            end
        end
        if TT.rowHost then TT.rowHost:SetFrameLevel(cardLvl + 2) end
        for i = 1, TT.CARD_MAX do
            if TT.scCards[i] then TT.scCards[i].frame:SetFrameLevel(cardLvl + 2) end
        end
        if TT.chipPool then
            for i = 1, #TT.chipPool do
                if TT.chipPool[i] then TT.chipPool[i].frame:SetFrameLevel(cardLvl + 2) end
            end
        end
        if TT.specTopCard then TT.specTopCard:SetFrameLevel(cardLvl + 1) end
        local fixLvl = cardLvl + 7
        if TT.hero then TT.hero:SetFrameLevel(fixLvl) end
        if TT.textLayer then TT.textLayer:SetFrameLevel(fixLvl) end
        for _, bt in pairs(TT.specTabs or {}) do bt:SetFrameLevel(fixLvl) end
        for _, bt in pairs(TT.modeBtns or {}) do bt:SetFrameLevel(fixLvl) end
        for _, bt in pairs(TT.secTabs or {}) do bt:SetFrameLevel(fixLvl) end
        for _, bt in pairs(TT.subBtns or {}) do bt:SetFrameLevel(fixLvl) end
    end
    coroutine.yield()

    TT.Render()
    end))
end

function TT.PaintNav()
    local db = DB()
    local specMode = (db.nav == "spec") and (EnsureCG() ~= nil) or false
    local rankSel = not specMode
    SetOutline(TT.navBtn, rankSel, 1, 0.82, 0)
    TT.navBtn:GetFontString():SetTextColor(Unpack(rankSel and C_WHITE or C_DIM))
    if TT.classBtns then
        for cls, cb in pairs(TT.classBtns) do
            local sel = specMode and (cls == db.cls)
            SetClassBase(cb, sel)
            local cr, cg, cbc = ClassColor(cls)
            cb.__txt:SetTextColor(cr, cg, cbc)
            cb.__txt:SetAlpha(sel and 1 or 0.82)
            SetOutline(cb, sel, 1, 0.82, 0)
        end
    end
    for _, bt in pairs(TT.subBtns) do
        bt:SetShown(rankSel)
    end
    if TT.specTabs then
        for _, bt in pairs(TT.specTabs) do
            bt:Hide()
        end
        if specMode then
            local list = T.specs and T.specs[db.cls]
            local i = 0
            local x = TT.RIGHT_X + TT.SPEC_TITLE_X
            for _, sp in ipairs(list or {}) do
                if G.specs[db.cls] and G.specs[db.cls][sp.key] then
                    i = i + 1
                    local bt = TT.specTabs[i]
                    if bt then
                        bt.__specKey = sp.key
                        bt:SetText(sp.name)
                        local w = tonumber(bt:GetFontString():GetStringWidth()) or 0
                        w = math.max(TT.SPEC_BTN_W, w + 2 * TT.SPEC_BTN_PAD)
                        bt:SetWidth(w)
                        bt:ClearAllPoints()
                        bt:SetPoint("TOPLEFT", TT.page, "TOPLEFT", x, -TT.SPEC_BTN_Y)
                        x = x + w + TT.SPEC_BTN_GAP
                        bt:Show()
                        local sel = (sp.key == db.spec)
                        SetOutline(bt, sel, 1, 0.82, 0)
                        bt:GetFontString():SetTextColor(Unpack(sel and C_WHITE or C_DIM))
                    end
                end
            end
        end
    end
    if TT.modeBtns then
        for _, bt in pairs(TT.modeBtns) do bt:Hide() end
        if specMode then
            for _, bt in pairs(TT.modeBtns) do
                local sel = (bt.__modeKey == db.mode)
                SetOutline(bt, sel, 1, 0.82, 0)
                bt:GetFontString():SetTextColor(Unpack(sel and C_WHITE or C_DIM))
                bt:Show()
            end
        end
    end
    if TT.secTabs and not specMode then
        for i = 1, TT.SEC_TAB_MAX do
            if TT.secTabs[i] then TT.secTabs[i]:Hide() end
        end
    end
    return specMode
end

function TT.OpenSpec(cls, spec)
    G = EnsureCG()
    if not G then return end
    local db = DB()
    db.nav = "spec"
    db.cls = cls
    if spec then db.spec = spec end
    TT.RequestRender()
    ns.PlaySound(1)
end

function TT.HideRank()
    TT.meta:Hide()
    TT.intro:Hide()
    for i = 1, 5 do
        TT.cards[i].frame:Hide()
    end
    TT.factorTitle:Hide()
    for i = 1, 6 do TT.factorRows[i]:Hide() end
    for i = 1, 10 do TT.noteRows[i]:Hide() end
end

function TT.HideSpecContent()
    if TT.secTabs then
        for i = 1, TT.SEC_TAB_MAX do
            if TT.secTabs[i] then TT.secTabs[i]:Hide() end
        end
    end
    if TT.scCards then
        for i = 1, TT.CARD_MAX do
            if TT.scCards[i] then
                TT.scCards[i].frame:Hide()
                TT.scCards[i].divider:Hide()
            end
        end
    end
    if TT.rowPool then
        for i = 1, TT.ROW_MAX do
            if TT.rowPool[i] then TT.rowPool[i]:Hide() end
        end
    end
    if TT.chipPool then
        for i = 1, TT.CHIP_MAX do
            if TT.chipPool[i] then TT.chipPool[i].frame:Hide() end
        end
    end
end

function TT.HideSpec()
    if not TT.specTitle then return end
    if TT.specTopCard then TT.specTopCard:Hide() end
    if TT.topSep then TT.topSep:Hide() end
    if TT.hero then TT.hero:Hide() end
    if TT.heroGrade then TT.heroGrade:Hide() end
    if TT.specMeta then TT.specMeta:Hide() end
    if TT.secTabs then
        for i = 1, TT.SEC_TAB_MAX do
            if TT.secTabs[i] then TT.secTabs[i]:Hide() end
        end
    end
    if TT.modeBtns then
        for i = 1, #TT.MODE_KEYS do
            if TT.modeBtns[i] then TT.modeBtns[i]:Hide() end
        end
    end
    TT.HideSpecContent()
    if ns.ClassCombatUI then ns.ClassCombatUI.HideRows() end
    if ns.ClassQuestUI then ns.ClassQuestUI.Hide() end
end

local function PY()
    if coroutine.running and coroutine.running() then coroutine.yield() end
end

function TT.Render()
    if not TT.built then return end
    TT.__renderGen = (TT.__renderGen or 0) + 1
    local specMode = TT.PaintNav()
    TT.__mode = specMode and "spec" or "rank"
    PY()
    if specMode then
        TT.HideRank()
        local CU = ns.ClassCombatUI
        local mode = DB().mode
        local CQUI = ns.ClassQuestUI
        if CQUI then CQUI.Hide() end
        if mode == "rotation" and CU then
            TT.PlaceScroll(TT.MODE_TOP)
            TT.HideSpecContent()
            CU.RenderRotation()
        elseif mode == "macro" and CU then
            TT.PlaceScroll(TT.MODE_TOP)
            TT.HideSpecContent()
            CU.RenderMacro()
        elseif mode == "cq" and CQUI then
            TT.PlaceScroll(TT.MODE_TOP)
            TT.HideSpecContent()
            if CU then CU.HideRows() end
            CQUI.Render()
        else
            TT.PlaceScroll(TT.SEC_TOP)
            if CU then CU.HideRows() end
            RenderSpec()
        end
        TT.__v = 0
        TT.child:SetPoint("TOPLEFT", TT.scroll, "TOPLEFT", 0, 0)
        CullScrollContent()
        UpdateScrollUI()
    else
        TT.HideSpec()
        TT.RenderRank()
        TT.PlaceScroll(TT.__rankTop or TT.BODY_TOP)
        TT.__v = 0
        TT.child:SetPoint("TOPLEFT", TT.scroll, "TOPLEFT", 0, 0)
        CullScrollContent()
        UpdateScrollUI()
    end
end

function TT.RenderRank()
    TT.__renderGen = (TT.__renderGen or 0) + 1
    if not TT.built then return end
    local p = PageFor(DB().tab)
    local own = MobileCls()

    for k, bt in pairs(TT.subBtns) do
        local sel = (k == p.key)
        SetOutline(bt, sel, 1, 0.82, 0)
        bt:GetFontString():SetTextColor(Unpack(sel and C_WHITE or C_DIM))
    end

    TT.meta:SetText("")
    TT.meta:Hide()
    TT.intro:SetText(p.intro or "")
    local leadW = 100
    if TT.factorTitle and TT.factorTitle.GetStringWidth then
        local w = TT.factorTitle:GetStringWidth()
        if tonumber(w) then leadW = w + 20 end
    end
    TT.intro:SetWidth(math.max(160, TT.CARD_W - leadW))

    local y = 0

    local tiers = p.tiers or {}
    for i = 1, 5 do
        local ui = TT.cards[i]
        local tier = tiers[i]
        ui.frame:Hide()
        if i % 2 == 0 then PY() end
        if tier then
            local key = tier.key
            local specs = tier.specs or {}
            local col = TT.COLOR[key] or TT.COLOR.D
            local bc = ui.badgeColor
            bc[1], bc[2], bc[3], bc[4] = col[1], col[2], col[3], 1
            if ui.badgeRepaint then
                ui.badgeRepaint()
            elseif ui.badge.SetBackdropColor then
                ui.badge:SetBackdropColor(col[1], col[2], col[3], 1)
            end
            ui.letter:SetText(key)
            ui.letter:SetTextColor(TT.BADGE_TEXT[1], TT.BADGE_TEXT[2], TT.BADGE_TEXT[3])
            local rows = math.ceil(#specs / TT.GRID_COLS)
            local h = math.max(TT.EMPTY_H, rows * TT.CELL_H + 2 * TT.LIST_PAD)
            ui.frame:SetHeight(h)
            ui.frame:ClearAllPoints()
            ui.frame:SetPoint("TOPLEFT", TT.page, "TOPLEFT", TT.RIGHT_X, -(TT.BODY_TOP + y))
            ui.badge:SetHeight(h - 2 * TT.LIST_PAD)
            ui.badge:ClearAllPoints()
            ui.badge:SetPoint("TOPLEFT", ui.frame, "TOPLEFT", TT.LIST_PAD, -TT.LIST_PAD)
            if #specs == 0 then
                ui.empty:ClearAllPoints()
                ui.empty:SetPoint("LEFT", ui.badge, "RIGHT", 16, 0)
                ui.empty:Show()
            else
                ui.empty:Hide()
            end
            for c = 1, TT.GRID_COLS * TT.GRID_ROWS do
                local cell = ui.cells[c]
                local e = specs[c]
                if e then
                    local rec = SpecRec(e.class, e.spec)
                    cell.cls = e.class
                    cell.spec = e.spec
                    cell.rec = rec
                    cell.tierKey = key
                    cell.own = (e.class == own) and true or false
                    local gridCol = (c - 1) % TT.GRID_COLS
                    local gridRow = math.floor((c - 1) / TT.GRID_COLS)
                    cell:ClearAllPoints()
                    cell:SetPoint("TOPLEFT", ui.frame, "TOPLEFT",
                        TT.LIST_PAD + TT.BADGE_W + 16 + gridCol * ui.cellW,
                        -TT.LIST_PAD - gridRow * TT.CELL_H)
                    SetIcon(cell.icon, rec and rec.icon)
                    cell.name:SetText(rec and rec.name or "?")
                    local cr2, cg2, cb2 = ClassColor(e.class)
                    cell.name:SetTextColor(cr2, cg2, cb2)
                    cell:Show()
                    PaintCell(cell, cell.own, false)
                else
                    cell.cls, cell.spec, cell.rec, cell.tierKey = nil, nil, nil, nil
                    cell.own = false
                    cell:Hide()
                end
            end
            ui.frame:Show()
            y = y + h + TT.CARD_GAP
        end
    end

    TT.__rankTop = TT.BODY_TOP + y
    y = 8
    TT.factorTitle:ClearAllPoints()
    TT.factorTitle:SetPoint("TOPLEFT", TT.child, "TOPLEFT", 0, -y)
    TT.factorTitle.__cy, TT.factorTitle.__ch = y, FSHeight(TT.factorTitle)
    TT.factorTitle.__cgen = TT.__renderGen
    TT.intro:ClearAllPoints()
    TT.intro:SetPoint("LEFT", TT.factorTitle, "RIGHT", 16, 0)
    TT.intro.__cy, TT.intro.__ch = TT.factorTitle.__cy, FSHeight(TT.intro)
    TT.intro.__cgen = TT.__renderGen
    y = y + math.max(FSHeight(TT.factorTitle), FSHeight(TT.intro)) + 8

    local factors = p.factors or {}
    for i = 1, 6 do
        local row = TT.factorRows[i]
        local f = factors[i]
        if f then
            row:SetWidth(TT.CARD_W)
            row:SetText(format("|cffffd100%s|r  %s", f[1] or "", f[2] or ""))
            row:ClearAllPoints()
            row:SetPoint("TOPLEFT", TT.child, "TOPLEFT", 0, -y)
            row:Show()
            local rh = FSHeight(row)
            row.__cy, row.__ch = y, rh
            row.__cgen = TT.__renderGen
            y = y + rh + 5
        else
            row:Hide()
        end
    end

    y = y + 8
    local notes = p.notes or {}
    for i = 1, 10 do
        local row = TT.noteRows[i]
        local n = notes[i]
        if n then
            row:SetWidth(TT.CARD_W)
            row:SetText(n)
            row:ClearAllPoints()
            row:SetPoint("TOPLEFT", TT.child, "TOPLEFT", 0, -y)
            row:Show()
            local rh = FSHeight(row)
            row.__cy, row.__ch = y, rh
            row.__cgen = TT.__renderGen
            y = y + rh + 7
        else
            row:Hide()
        end
    end

    TT.child:SetHeight(y + 10)
end

function TT.RequestRender()
    if not TT.built then return end
    if not (ns.PaintJob and ns.IdleJobs) then
        TT.Render()
        return
    end
    if ns.PaintJob.Active("Tier") then
        TT.__pend = true
        return
    end
    ns.PaintJob.Run("Tier", function() TT.Render() end, function()
        if TT.__pend then
            TT.__pend = false
            TT.RequestRender()
        end
    end)
end

function TT.Refresh()
    if not TT.built then return end
    TT.RequestRender()
end

function TT.OnThemeChange()
    if not TT.built then return end
    TT.RequestRender()
end
