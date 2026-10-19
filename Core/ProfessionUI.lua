local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local MakeOutline = Host.MakeOutline
local SetOutline, Unpack = Host.SetOutline, Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local CONTENT_W = Host.CONTENT_W
local PAGE_INSET, ROW_CLASS = Host.PAGE_INSET, Host.ROW_CLASS
local FALLBACK_ICON = Host.FALLBACK_ICON

local D  = ns.ProfData
local R
local function RGet(k)
    if not R then
        local fn = ns.EnsureProfRecipes
        R = type(fn) == "function" and fn() or nil
        ns.OpenPerf.Mark("数据")
    end
    return R and R[k] or nil
end
local LV = ns.ProfLeveling
local GA = ns.ProfGathering
local RA = ns.ProfRouteAuto
local CD = ns.CratesData

if CD and D.pro and not D.pro.crates then
    D.order[#D.order + 1] = "crates"
    D.pro.crates = {
        name = L["板条箱"],
        icon = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\CrateNav",
        kind = "crates",
        section = "crates",
    }
end

local PD = {}
ns.ProfModule = PD

PD.CARD_INSET = PAGE_INSET
PD.CARD_TOP = 8
PD.NAV_PAD = 8
PD.NAV_X, PD.NAV_TOP = PD.CARD_INSET + PD.NAV_PAD, PD.CARD_TOP + PD.NAV_PAD
PD.NAV_W = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 184 or 148
PD.NAV_FS, PD.NAV_ICON = 16, 20
PD.NAV_ITEM_H, PD.NAV_GROUP_H, PD.NAV_GAP = 26, 22, 3
PD.NAV_LV_FS = 14
PD.CARD_NAV_R = PD.CARD_INSET + PD.NAV_W + 2 * PD.NAV_PAD
PD.RIGHT_X = PD.CARD_NAV_R + (DG.GUTTER or 8) + 8
PD.RIGHT_W = CONTENT_W - PD.RIGHT_X - PD.CARD_INSET
PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = PD.CARD_TOP + 8, 22, 70, 78
PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 8
PD.BODY_BOT = PD.CARD_INSET + 8
PD.FAC_ICON = {
    a = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    h = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}
PD.TOOL_H, PD.TOOL_GAP, PD.TOOL_W = 22, 8, 72
PD.TOOL_BODY_GAP = 8
PD.ROW_H, PD.ROW_H1, PD.TEXT_H = 34, 24, 24

PD.SETTING_DEF = { greyPassed = true, hlCurrent = true }
PD.SETTING_DEF.autoRoute = false
PD.SETTING_DEF.autoOnlyAH = true
PD.SETTING_DEF.autoNoFormula = true
PD.SETTING_DEF.autoLearnedOnly = false
PD.SETTING_DEF.autoScheme = "cheapest"

PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }
PD.SETTING_DEF.autoFromCurrent = true
PD.SETTING_TOG_MAX = 4
PD.SETTING_TOG_MAX = 4 + 5
local function ProfDB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
    return DungeonsForeverDB.prof
end

local function RememberLast()
    if PD.cur and PD.cur ~= "__index" then
        local db = ProfDB()
        db.lastSlug = PD.cur
        db.lastTab = PD.tab
    end
end
function PD.Setting(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] and true or false end
    return v and true or false
end

function PD.SettingRaw(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] end
    return v
end

local SMELT_TBL = {
    { 2840, 1 }, { 3576, 65 }, { 2841, 75 }, { 2842, 75 }, { 3575, 125 },
    { 3859, 155 }, { 3577, 155 }, { 3860, 175 }, { 6037, 210 },
    { 12359, 230 }, { 11371, 230 }, { 12360, 275 }, { 17771, 300 },
}
function PD.GatherMode(slug)
    if slug ~= "mining" then return "gather" end
        return (ProfDB().gatherMode == "smelt") and "smelt" or "gather"
end

function PD.LvTarget()
    if not PD.cur then return 300 end
    local db = ProfDB()
    local v = tonumber(db.lvTarget and db.lvTarget[PD.cur])
    if not v then return 300 end
    return math.max(1, math.min(300, math.floor(v)))
end

PD.LIST_PAD = 8
PD.COL_GAP = 12
local LV_SPLIT = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 0.75 or 0.80
PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)
PD.COL_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.COL_LW

PD.SHOP_SPLIT = 0.62
PD.SEC_CARD_MAX = 8
PD.SEC_PAD = 4
PD.SEC_PAD_X = 8
PD.SEC_IN = 8
PD.SEC_GAP = 8
PD.OV_GUT = PD.SEC_GAP + 2 * PD.SEC_PAD

PD.GRID_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) / 2)
PD.GRID_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.GRID_LW

PD.IX_COLS = 3
PD.IX_GAP = 8
PD.IX_COLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - (PD.IX_COLS - 1) * PD.IX_GAP) / PD.IX_COLS)
PD.IX_CARD_H = 46
PD.IX_ICON = 24
PD.IX_HEAD_H = 18
PD.IX_ROWW_GAP = 8
PD.IX_GROUP_GAP = 10

PD.MAT_FS = 13
PD.MAT_ICON_PX = 16
PD.MAT_ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD
PD.MAT_RIGHT_RESERVE = 132
PD.MAT_TAIL_MIN = 14
PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)
PD.MAT_W = PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8

PD.RECIPE_NAME_MIN, PD.RECIPE_NAME_MAX = 100, math.floor(PD.MAT_ROW_W * 0.16)
PD.RECIPE_NAME_PAD = 16
PD.RECIPE_BADGE_W = 26
PD.RECIPE_PADL = 32
PD.SEARCH_EB_W, PD.SEARCH_W = 150, 180
PD.SEARCH_RESERVED = 190

PD.LV_FS = 13
PD.TBL_ICON = 27.6
PD.TBL_H = 42
PD.TBL_RNG_GAP = 12
PD.TBL_NAME_GAP = 8
PD.TBL_MAT_CNT_FS = 14
PD.TBL_BLK_GAP = 8
PD.TBL_MAT_RPAD = 6
PD.TBL_CNT_GAP = 8
PD.TBL_MARK_W = 16
PD.TBL_NAME_MIN, PD.TBL_NAME_MAX = 88, 150
PD.TBL_BLK_MAX = 5
PD.TBL_NAME_DY, PD.TBL_SRC_DY = 7, -8
PD.TBL_MAT_CNT_DY = -8
PD.ZEBRA_A = 0.045
PD.LV_ICON_X = 6 + 71 + PD.TBL_RNG_GAP
PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP
PD.LV_CNT_W = 78
PD.LV_CNT_R = PD.TBL_MAT_RPAD + 240 + PD.TBL_CNT_GAP
PD.LV_UNIT_W, PD.LV_TOT_W = 0, 0
PD.LV_UNIT_R, PD.LV_CNT2_R = PD.LV_CNT_R, PD.LV_CNT_R
PD.LV_COL_GAP = 16
PD.LV_NAME_W = PD.TBL_NAME_MIN
PD.REC_COST_W = 88
PD.REC_AH_W = 88
PD.LV_MAT_W = 240

PD.GR_LV_X = 6
PD.GR_LOC_X = 88
PD.GR_ICON_W = 20

PD.ROW_CAP = 300
PD.ROW_POOL_CAP = 140
PD.TOOL_MAX = 20

PD.TEXT_W = PD.RIGHT_W - 46

DG.PROF_SUBTABS = {
    { key = "overview", text = L["总览"] },
    { key = "trainer",  text = L["训练师"] },
    { key = "recipe",   text = L["配方"] },
    { key = "gather",   text = L["采集"] },
    { key = "leveling", text = L["升级"] },
    { key = "crate",    text = L["板条箱"] },
    { key = "writ",     text = L["工匠文书"] },
}

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

local function SpellIcon(id)
    if not id then return nil end
    if C_Spell and C_Spell.GetSpellInfo then
        local info = C_Spell.GetSpellInfo(id)
        if info and info.iconID then return info.iconID end
    end
    if type(GetSpellInfo) == "function" then
        return select(3, GetSpellInfo(id))
    end
    return nil
end

DG.ZoneName = function(id)
    if type(id) ~= "number" then return L["无数据"] end
    local m = C_Map
    local fn = m and m.GetAreaInfo
    if type(fn) == "function" then
        local ok, nm = pcall(fn, id)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return format(L["区域 #%d"], id)
end

local CharStep = ns.hui.CharStep

local _twMemo, _twN = {}, 0
PD.TextW = function(text, fs)
    if type(text) ~= "string" or fs == nil then return ns.hui.TextW(text, fs) end
    local m = _twMemo[fs]
    if not m then m = {}; _twMemo[fs] = m end
    local w = m[text]
    if w ~= nil then return w end
    w = ns.hui.TextW(text, fs)
    if _twN >= 8192 then
        _twMemo, _twN = {}, 0
        m = {}
        _twMemo[fs] = m
    end
    m[text] = w
    _twN = _twN + 1
    return w
end

PD.Fit = function(text, fs, width)
    if PD.TextW(text, fs) <= width then return text end
    return ns.hui.Fit(text, fs, width)
end

local PD_MEMO_POS_CAP = 32768
local _nmPos, _nmPosN = {}, 0
local _nmNeg, _nmN = {}, 0
local _icPos, _icPosN = {}, 0
local _icNeg, _icN = {}, 0
function PD.ResetItemNameMemo(hard)
    _nmNeg, _nmN = {}, 0
    _icNeg, _icN = {}, 0
    if hard then _nmPos, _nmPosN, _icPos, _icPosN = {}, 0, {}, 0 end
end
function PD.ItemName(id)
    if id == nil then return L["暂时没有客户端数据"], false end
    local hit = _nmPos[id]
    if hit ~= nil then return hit, true end
    if _nmNeg[id] then return L["暂时没有客户端数据"], false end
    local nm, got = DG.ItemName(id)
    if got then
        if _nmPosN >= PD_MEMO_POS_CAP then _nmPos, _nmPosN = {}, 0 end
        _nmPos[id], _nmPosN = nm, _nmPosN + 1
        return nm, true
    end
    if _nmN >= 8192 then _nmNeg, _nmN = {}, 0 end
    _nmNeg[id], _nmN = true, _nmN + 1
    return nm, false
end

function PD.ItemIcon(id)
    if id == nil then return FALLBACK_ICON end
    local hit = _icPos[id]
    if hit ~= nil then return hit end
    if _icNeg[id] then return FALLBACK_ICON end
    local tex = DG.ItemIcon(id)
    if tex ~= FALLBACK_ICON then
        if _icPosN >= PD_MEMO_POS_CAP then _icPos, _icPosN = {}, 0 end
        _icPos[id], _icPosN = tex, _icPosN + 1
        return tex
    end
    if _icN >= 8192 then _icNeg, _icN = {}, 0 end
    _icNeg[id], _icN = true, _icN + 1
    return tex
end

PD.Wrap = function(text, fs, width)
    local out = {}
    if type(text) ~= "string" or text == "" or not width then return out end
    local toks, pos = {}, 1
    while true do
        local s, e = string.find(text, "|T.-|t", pos)
        if not s then
            toks[#toks + 1] = { t = string.sub(text, pos) }
            break
        end
        if s > pos then toks[#toks + 1] = { t = string.sub(text, pos, s - 1) } end
        toks[#toks + 1] = { t = string.sub(text, s, e), icon = true }
        pos = e + 1
    end
    local line, w = "", 0
    for _, tk in ipairs(toks) do
        if tk.icon then
            local cw = fs + 2
            if w + cw > width and line ~= "" then
                out[#out + 1] = line
                line, w = "", 0
            end
            line, w = line .. tk.t, w + cw
        else
            local i, n = 1, #tk.t
            while i <= n do
                local ch, step, k = CharStep(tk.t, i)
                local cw = k * fs
                if w + cw > width and line ~= "" then
                    out[#out + 1] = line
                    line, w = "", 0
                end
                line = line .. ch
                w = w + cw
                i = i + step
            end
        end
    end
    if line ~= "" then out[#out + 1] = line end
    return out
end

PD.TIER_HEX = { "|cffffd100", "|cff40d940", "|cff8c8c8c" }
PD.TierText = function(a, b, c)
    return format("%s%s|r/%s%s|r/%s%s|r",
                  PD.TIER_HEX[1], tostring(a),
                  PD.TIER_HEX[2], tostring(b),
                  PD.TIER_HEX[3], tostring(c))
end

local function ColTextW(col)
    if col == 2 then
        if PD.gridSplit then return PD.GRID_RW end
        if PD.lvSplit then return PD.splitRW or PD.COL_RW end
        return PD.COL_RW
    end
    if col == 1 then
        if PD.gridSplit then return PD.GRID_LW end
        if PD.lvSplit then return PD.splitLW or PD.COL_LW end
        return PD.COL_LW
    end
    return PD.TEXT_W
end

local function PushText(rows, text, fs, color, col)
    for _, ln in ipairs(PD.Wrap(text, fs or 12, ColTextW(col))) do
        rows[#rows + 1] = { kind = "text", text = ln, fs = fs or 12, color = color, col = col }
    end
end

local function PushHead(rows, text, col, fs)
    rows[#rows + 1] = { kind = "head", text = text, col = col, fs = fs }
end

local function PushGap(rows, h, col)
    rows[#rows + 1] = { kind = "gap", h = h or 8, col = col }
end

local function MarkSec(rows, a, b, n)
    for i = a, b do
        if rows[i].kind ~= "gap" then rows[i].sec = n end
    end
end

PD.cur = nil
PD.tab = "overview"
PD.campView = "a"
PD.autoPage = "route"
PD.toolKey = nil
PD.perkOpen = {}
PD.rows, PD.toolBtns = {}, {}
PD.specs = nil

PD.__pendRows = {}
PD.ROW_SYNC_MAX = 20
PD.SYNC_ROWS_BUF = 6
function PD.SyncRows()
    local h = 0
    local sf = PD.scroll
    if sf and type(sf.GetHeight) == "function" then
        local ok, v = pcall(sf.GetHeight, sf)
        if ok and type(v) == "number" then h = v end
    end
    if h <= 0 then h = 420 end
    local per = PD.ROW_H1 or PD.ROW_H or 20
    if type(per) ~= "number" or per <= 0 then per = 20 end
    return math.ceil(h / per) + PD.SYNC_ROWS_BUF
end

function PD.SetRowHover(r, on)
    on = on and true or false
    r.__hlOn = on
    if on then
        if ns.hui and ns.hui.layer then
            local c4 = ns.hui.layer.L4
            r:SetBackdropColor(c4[1], c4[2], c4[3], c4[4] or 1)
        else
            r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
        end
        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
    elseif r.__z then
        r:SetBackdropColor(1, 1, 1, PD.ZEBRA_A)
        r:SetBackdropBorderColor(1, 1, 1, 0)
    else
        r:SetBackdropColor(1, 1, 1, 0)
        r:SetBackdropBorderColor(1, 1, 1, 0)
    end
end

function PD.SyncHover()
    if not PD.rows then return end
    for _, r in pairs(PD.rows) do
        local over = (r.IsMouseOver and r:IsMouseOver()) and true or false
        if over ~= r.__hlOn then PD.SetRowHover(r, over) end
    end
    if PD.ixRoot and PD.ixRoot:IsVisible() then
        for i = 1, #(PD.ixCards or {}) do
            local c = PD.ixCards[i]
            local over = (c.IsMouseOver and c:IsMouseOver()) and true or false
            if over ~= c.__hlOn then PD.SetCardHover(c, over) end
        end
    end
end

function PD.Row(i)
    local r = PD.rows[i]
    if r then return r end
    r = CreateFrame("Button", nil, PD.child, "BackdropTemplate")
    r:SetWidth(PD.RIGHT_W)
    r:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
    })
    r.__hlOn = false
    PD.SetRowHover(r, false)
    r:EnableMouse(true)
    r.icon = r:CreateTexture(nil, "ARTWORK")
    r.icon:SetSize(20, 20)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.icon2 = r:CreateTexture(nil, "ARTWORK")
    r.icon2:SetSize(14, 14)
    r.icon2:Hide()
    r.icon3 = r:CreateTexture(nil, "ARTWORK")
    r.icon3:SetSize(14, 14)
    r.icon3:Hide()
    r.hsOwn = CreateFrame("Button", nil, r)
    r.hsOwn:EnableMouse(true)
    r.hsOwn:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsOwn:Hide()
    r.hsTot = CreateFrame("Button", nil, r)
    r.hsTot:EnableMouse(true)
    r.hsTot:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsTot:Hide()
    r.hsCraft = CreateFrame("Button", nil, r)
    r.hsCraft:EnableMouse(true)
    r.hsCraft:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsCraft:Hide()
    r.icon4 = r:CreateTexture(nil, "ARTWORK")
    r.icon4:SetSize(14, 14)
    r.icon4:Hide()
    r.hsGap = CreateFrame("Button", nil, r)
    r.hsGap:EnableMouse(true)
    r.hsGap:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsGap:Hide()
    r.gic = {}
    for k = 1, 6 do
        local g = r:CreateTexture(nil, "ARTWORK")
        g:SetSize(20, 20)
        g:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(g) end
        g:Hide()
        r.gic[k] = g
    end
    r.blk = {}
    r.a = MakeFS(r, 13, C_TEXT, "LEFT")
    r.b = MakeFS(r, 11, C_GREY, "LEFT")
    r.c = MakeFS(r, 12, C_GOLD, "RIGHT")
    r.c2 = MakeFS(r, 12, C_GOLD, "RIGHT")
    r.d = MakeFS(r, 11, C_GREY, "RIGHT")
    r.e = MakeFS(r, 13, C_GOLD, "LEFT")
    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
    r.h1 = MakeFS(r, 16, C_GREY, "LEFT")
    r.h2 = MakeFS(r, 16, C_GREY, "LEFT")
    r.h3 = MakeFS(r, 16, C_GREY, "RIGHT")
    r.h4 = MakeFS(r, 16, C_GREY, "RIGHT")
    r.h5 = MakeFS(r, 16, C_GREY, "RIGHT")
    r.h6 = MakeFS(r, 16, C_GREY, "LEFT")
    r.mn = {}
    r.mz = {}
    r.mcnt = {}
    r.dv = MakeFS(r, 11, C_GREY, "RIGHT")
    r.dv:SetText("")
    r.dv:SetWordWrap(false)
    r.dv:Hide()
    r.__sbBg, r.__sbTx = {}, {}
    for k = 1, 4 do
        local bg = r:CreateTexture(nil, "ARTWORK")
        bg:SetColorTexture(1, 1, 1, 1)
        bg:Hide()
        r.__sbBg[k] = bg
        local tx = MakeFS(r, PD.SB_FS, C_WHITE, "CENTER")
        tx:SetText("")
        tx:SetWordWrap(false)
        tx:Hide()
        r.__sbTx[k] = tx
    end
    r.__sbPin = {}
    for k = 1, 2 do
        local p = r:CreateTexture(nil, "OVERLAY")
        p:SetWidth(2)
        p:SetColorTexture(1, 1, 1, 0.9)
        p:Hide()
        r.__sbPin[k] = p
    end
    r.__cardZone = CreateFrame("Button", nil, r)
    r.__cardZone:Hide()
    PD.WireTipZone(r.__cardZone, r)
    r.__cardBg = CreateFrame("Frame", nil, r)
    r.__cardBg:Hide()
    r.__cardBg.__pieces = ns.hui.BuildRoundedBG(r.__cardBg, 4, { 1, 1, 1 }, "both", false, nil, true)
    r.__cardTx = MakeFS(r.__cardBg, 10, C_TEXT, "LEFT")
    r.__cardTx:SetText("")
    r.__cardTx:SetWordWrap(false)
    r.__cardTx:Hide()
    for _, f in ipairs({ r.a, r.b, r.c, r.c2, r.d, r.e, r.f }) do f:SetWordWrap(false) end
    r.tagBg = r:CreateTexture(nil, "BORDER")
    r.tagBg:SetColorTexture(0.30, 0.75, 0.45, 0.16)
    r.tagBg:Hide()
    r.tagFs = MakeFS(r, 10, { 0.42, 0.94, 0.62 }, "LEFT")
    r.tagFs:SetText("")
    r.tagFs:Hide()
    r.sep = r:CreateTexture(nil, "BACKGROUND")
    r.sep:SetHeight(1)
    r.sep:SetColorTexture(1, 1, 1, 0.055)
    r.bT = r:CreateTexture(nil, "BORDER")
    r.bT:SetHeight(1)
    r.bT:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
    r.bT:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)
    r.bB = r:CreateTexture(nil, "BORDER")
    r.bB:SetHeight(1)
    r.bB:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.bB:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    r.bL = r:CreateTexture(nil, "BORDER")
    r.bL:SetWidth(1)
    r.bL:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
    r.bL:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.bR = r:CreateTexture(nil, "BORDER")
    r.bR:SetWidth(1)
    r.bR:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)
    r.bR:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    r:SetScript("OnEnter", function(self)
        PD.SetRowHover(self, true)
        if self.__noTip then return end
        if self.__lines == nil and self.__mkLines then
            self.__lines = self.__mkLines()
            self.__mkLines = nil
        end
        if self.__lines and (self.__linesFirst or not self.__it) then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(self.__lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        elseif self.__it then
            local extra = self.__tipExtra
            if type(extra) == "function" then extra = extra() end
            DG.ShowItemTip(self, self.__it, extra, self.__tipTitle)
        end
    end)
    r:SetScript("OnLeave", function(self)
        PD.SetRowHover(self, false)
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function(self, button)
        if button == "LeftButton" and self.__it
           and type(IsShiftKeyDown) == "function" and IsShiftKeyDown() then
            DG.ItemShiftClick(self, button)
            return
        end
        if self.__act then self.__act(self, button) end
        ns.PlaySound(1)
    end)
    r:EnableMouseWheel(true)
    r:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
    PD.rows[i] = r
    return r
end

function PD.RowHeight(spec)
    if spec.h then return spec.h end
    if spec.kind == "gap" then return 6 end
    if spec.kind == "text" or spec.kind == "head" then return PD.TEXT_H end
    return PD.ROW_H
end

PD.StealRowFrame = function(idx)
    if not PD.visMode then return nil end
    local sc = PD.scroll
    if not (sc and sc.GetVerticalScroll and sc.GetHeight) then return nil end
    local v = sc:GetVerticalScroll()
    local vh = sc:GetHeight()
    if type(v) ~= "number" or type(vh) ~= "number" or vh <= 0 then return nil end
    local vT, vB = v - 40, v + vh + 160
    local cnt = 0
    for j = 1, PD.ROW_CAP do
        if PD.rows[j] then cnt = cnt + 1 end
    end
    if cnt < (PD.ROW_POOL_CAP or 140) then return nil end
    local bestJ, bestD, nilJ
    for j = 1, PD.ROW_CAP do
        local rr = PD.rows[j]
        if rr then
            local gt = rr.__top
            if type(gt) ~= "number" then
                if not nilJ then nilJ = j end
            else
                local d
                if gt < vT then d = vT - gt
                elseif gt > vB then d = gt - vB
                else d = -1 end
                if d > vh and d > (bestD or 0) then bestJ, bestD = j, d end
            end
        end
    end
    local j = bestJ or nilJ
    if not j then return nil end
    local rr = PD.rows[j]
    PD.rows[j] = nil
    PD.rows[idx] = rr
    if PD.WipeRow then PD.WipeRow(rr) end
    return rr
end

function PD.RealizePendingRow(e)
    if not e then return end
    if e.gen and e.gen ~= PD.__rowGen then return end
    local r = PD.rows[e.idx]
    if not r then
        r = PD.StealRowFrame(e.idx)
        if not r then
            local ok, made = pcall(PD.Row, e.idx)
            if not ok or not made then return end
            r = made
        end
    end
    if e.gap then
        r:Hide()
        return
    end
    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", e.x, -e.top)
    r.__top = e.top
    r:SetSize(e.w, e.h)
    r:Show()
    PD.BindRow(r, e.spec, e.h)
end

function PD.BuildPendRows()
    local list = PD.__pendRows
    if not list then
        PD.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    local t0 = DG.__nowMs()
    local left = DG.LOOT_ROW_FRAME_CAP
    while #list > 0 and left > 0 do
        PD.RealizePendingRow(table.remove(list, 1))
        DG.Gate.Advance(1)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
    end
    if #list > 0 then
        DG.PushStep(PD.BuildPendRows)
    else
        DG.Gate.Finish()
        if PD.DEMO_SAVE then PD.EndGateDemo() end
    end
end

function PD.FlushPendingRows()
    local n = #PD.__pendRows
    if n == 0 then
        DG.Gate.Finish()
        return
    end
    if n < PD.ROW_SYNC_MAX then
        for k = 1, n do PD.RealizePendingRow(PD.__pendRows[k]) end
        PD.__pendRows = {}
        DG.Gate.Finish()
        if PD.DEMO_SAVE then PD.EndGateDemo() end
        return
    end
    DG.Gate.Begin(n)
    DG.PushStep(PD.BuildPendRows)
    DG.RunSteps()
end

function PD.CullRows()
    local sc = PD.scroll
    if not (sc and PD.visMode and PD.curRows) then return end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll()
    if type(v) ~= "number" then return end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return end
    local gt = sc.GetTop and sc:GetTop()
    if type(gt) ~= "number" then return end
    local vT, vB = v - 40, v + viewH + 160
    local rows, n = PD.curRows, PD.curN
    for i = 1, n do
        local spec = rows[i]
        if spec and spec.kind ~= "gap" and type(spec.__gtop) == "number" then
            local r = PD.rows[i]
            if (spec.__gtop + spec.__gh) > vT and spec.__gtop < vB then
                if r and r.__spec == spec and r.IsShown and not r:IsShown() then
                    r:Show()
                end
            elseif r and r.IsShown and r:IsShown() then
                r:Hide()
            end
        end
    end
    if PD.__cullTimer or not (C_Timer and C_Timer.NewTimer) then return end
    PD.__cullSeq = (PD.__cullSeq or 0) + 1
    local seq = PD.__cullSeq
    PD.__cullTimer = C_Timer.NewTimer(0.08, function()
        PD.__cullTimer = nil
        if not (PD.visMode and PD.curRows) then return end
        if seq ~= PD.__cullSeq then
            PD.CullRows()
            return
        end
        local need = true
        local sc = PD.scroll
        if sc and sc.GetVerticalScroll and sc.GetHeight then
            local v, vh = sc:GetVerticalScroll(), sc:GetHeight()
            if type(v) == "number" and type(vh) == "number" and vh > 0 then
                local lv = PD.__settleV
                if type(lv) == "number" and math.abs(v - lv) < vh * 0.3
                   and GetTime and (GetTime() - (PD.__lastSettle or 0)) < 1.5 then
                    need = false
                end
                if need then PD.__settleV = v end
            end
        end
        if need then
            if GetTime then PD.__lastSettle = GetTime() end
            PD.CullRowsSettle()
        else
            PD.CullRows()
        end
    end)
end

function PD.CullRowsSettle()
    local sc = PD.scroll
    if not (sc and PD.visMode and PD.curRows) then return end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll()
    if type(v) ~= "number" then return end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return end
    local vT, vB = v - 40, v + viewH + 160
    local rows, n = PD.curRows, PD.curN
    local pend = PD.__pendRows
    for i = 1, n do
        local spec = rows[i]
        if spec and spec.kind ~= "gap" and type(spec.__gtop) == "number" then
            local r = PD.rows[i]
            if (spec.__gtop + spec.__gh) > vT and spec.__gtop < vB then
                if not (r and r.__spec == spec) then
                    pend[#pend + 1] = { idx = i, spec = spec, x = spec.__gx,
                                        w = spec.__gw, top = spec.__gtop, h = spec.__gh,
                                        gen = PD.__rowGen }
                end
            end
        end
    end
    PD.FlushPendingRows()
end

function PD.PaintRows(rows)
    local y = { 0, PD.hasSecs and PD.SEC_PAD or 0 }
    local bb = {}
    local bgold = {}
    local zc = { 0, 0 }
    local n = #rows
    local truncated = 0
    if n > PD.ROW_CAP then truncated = n - PD.ROW_CAP; n = PD.ROW_CAP end
    local grid = PD.gridSplit and true or false
    local ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD
    local syncN = PD.SyncRows()
    local vis, vTop, vBot = false, 0, 0
    do
        local sc = PD.scroll
        if sc and sc.GetVerticalScroll and sc.GetHeight and sc.GetTop then
            local v = sc:GetVerticalScroll()
            local vh = sc:GetHeight()
            local gt = sc:GetTop()
            if type(v) == "number" and type(vh) == "number" and vh > 0
               and type(gt) == "number" then
                vis = true
                vTop, vBot = v - 40, v + vh + 160
            end
        end
    end
    PD.visMode = vis
    PD.curRows, PD.curN = rows, n
    PD.__rowGen = (PD.__rowGen or 0) + 1
    local gen = PD.__rowGen
    for i = 1, n do
        local spec = rows[i]
        local h = PD.RowHeight(spec)
        local r = PD.rows[i]
        if spec.sec then
            local nxt
            for j = i + 1, n do
                local s2 = rows[j]
                if s2.kind ~= "gap" then nxt = s2 break end
            end
            spec._lastInSec = not (nxt and nxt.sec == spec.sec)
        end
        local span = (grid and spec.kind ~= "row") or spec.span == true
        if spec.kind == "gap" then
            if vis then
                if r and r.IsShown and r:IsShown() then r:Hide() end
            elseif r then
                r:Hide()
            else
                PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true, gen = gen }
            end
            if span then
                local ny = math.max(y[1], y[2]) + h
                y[1], y[2] = ny, ny
            else
                local col = (spec.col == 2) and 2 or 1
                y[col] = y[col] + h
            end
        else
            local col, x, w, top
            if span then
                top = math.max(y[1], y[2])
                x, w = PD.LIST_PAD, ROW_W
            else
                if spec.col == 2 then
                    col = 2
                elseif grid then
                    col = (y[2] < y[1]) and 2 or 1
                else
                    col = 1
                end
                top = y[col]
                if PD.lvSplit then
                    local lw = PD.splitLW or PD.COL_LW
                    local rw = PD.splitRW or PD.COL_RW
                    x = (col == 2) and (PD.LIST_PAD + lw + PD.OV_GUT) or PD.LIST_PAD
                    w = (col == 2) and rw or lw
                elseif grid then
                    x = (col == 2) and (PD.LIST_PAD + PD.GRID_LW + PD.COL_GAP) or PD.LIST_PAD
                    w = (col == 2) and PD.GRID_RW or PD.GRID_LW
                else
                    x, w = PD.LIST_PAD, ROW_W
                end
            end
            if spec.sec and spec.sec > 0 then
                w = w - PD.SEC_IN
            end
            if spec.kind == "row" and col and not spec.sec then
                zc[col] = zc[col] + 1
                spec.z = (zc[col] % 2 == 0)
            else
                spec.z = nil
            end
            spec.__gx, spec.__gw, spec.__gtop, spec.__gh = x, w, top, h
            if (not vis) or ((top + h) > vTop and top < vBot) then
                if r and ((not vis) or i <= syncN) then
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", x, -top)
                    r:SetSize(w, h)
                    r:Show()
                    PD.BindRow(r, spec, h)
                else
                    PD.__pendRows[#PD.__pendRows + 1] =
                        { idx = i, spec = spec, x = x, w = w, top = top, h = h, gen = gen }
                end
            elseif r and r.IsShown and r:IsShown() then
                r:Hide()
            end
            if spec.sec then
                local b = bb[spec.sec]
                if spec.goldSec then bgold[spec.sec] = true end
                if not b then
                    bb[spec.sec] = { x0 = x, y0 = top, x1 = x + w, y1 = top + h }
                else
                    b.x0 = math.min(b.x0, x)
                    b.y0 = math.min(b.y0, top)
                    b.x1 = math.max(b.x1, x + w)
                    b.y1 = math.max(b.y1, top + h)
                end
            end
            if span then
                y[1], y[2] = top + h + 2, top + h + 2
            else
                y[col] = top + h + 2
            end
        end
    end
    for i, rr in pairs(PD.rows) do
        if i > n then
            if rr.IsShown and rr:IsShown() then PD.WipeRow(rr) else rr:Hide() end
        end
    end
    if PD.secCards then
        for i = 1, #PD.secCards do PD.secCards[i]:Hide() end
        for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end
    end
    if PD.hasSecs then
        local ciP, ciG = 0, 0
        for s = 1, (PD.secCount or 0) do
            local b = bb[s]
            if b then
                local gold = bgold[s] and true or false
                local idx
                if gold then ciG = ciG + 1; idx = ciG else ciP = ciP + 1; idx = ciP end
                local c = (gold and PD.secGoldCards or PD.secCards)[idx]
                if c then
                    local padL = PD.secPadL or PD.SEC_PAD_X
                    c:ClearAllPoints()
                    c:SetPoint("TOPLEFT", PD.child, "TOPLEFT",
                               b.x0 - padL, -(b.y0 - PD.SEC_PAD))
                    c:SetSize((b.x1 - b.x0) + padL + PD.SEC_PAD_X,
                              (b.y1 - b.y0) + 2 * PD.SEC_PAD)
                    c:Show()
                end
            end
        end
    end
    local h1 = math.max(y[1], y[2])
    if PD.wantIndexGrid and PD.ixRoot then
        PD.placeIndexGrid(h1)
        h1 = h1 + (PD.ixGridH or 0) + 8
    elseif PD.ixRoot then
        PD.ixRoot:Hide()
    end
    if PD.wantBonusTable and PD.bonusTable then
        PD.placeBonusTable(h1)
        if PD.bonusTitleNote then
            PD.bonusTitleNote:ClearAllPoints()
            PD.bonusTitleNote:SetPoint("TOPRIGHT", PD.child, "TOPRIGHT",
                                       -PD.LIST_PAD, -(h1 - 19))
            PD.bonusTitleNote:Show()
        end
        h1 = h1 + (PD.bonusTableH or 0) + 2 * PD.SEC_PAD + 8
    elseif PD.bonusTable then
        if PD.bonusTitleNote then PD.bonusTitleNote:Hide() end
        PD.bonusTable:Hide()
        if PD.bonusCard then PD.bonusCard:Hide() end
    end
    if PD.wantTrainerBoard and PD.trainerBoard then
        PD.placeTrainerBoard(h1)
        h1 = h1 + (PD.trainerBoardH or 0) + 2 * PD.SEC_PAD + 8
    elseif PD.trainerBoard then
        PD.trainerCard:Hide()
    end
    PD.child:SetHeight(math.max(h1, y[2]) + 10)
    if PD.UpdateVScroll then PD.UpdateVScroll() end
    PD.FlushPendingRows()
    return truncated
end

function PD.RowBorder(r, on)
    local show = on and true or false
    r.bT:SetShown(show)
    r.bB:SetShown(show)
    r.bL:SetShown(show)
    r.bR:SetShown(show)
    if not show then return end
    local cr, cg, cb = PD.NavAccent()
    r.bT:SetColorTexture(cr, cg, cb, 0.95)
    r.bB:SetColorTexture(cr, cg, cb, 0.95)
    r.bL:SetColorTexture(cr, cg, cb, 0.95)
    r.bR:SetColorTexture(cr, cg, cb, 0.95)
end

function PD.BindRow(r, spec, h)
    r.__spec = spec
    r.__z = spec.z and true or false
    PD.SetRowHover(r, r.IsMouseOver and r:IsMouseOver())
    r.__it = spec.it
    r.__noTip = spec.noTip
    r.__lines = spec.lines
    r.__mkLines = spec.mkLines
    r.__linesFirst = spec.linesFirst
    r.__act = spec.act
    r.__tipTitle = spec.tipTitle
    r.__tipExtra = spec.tipExtra
    r.__named = false
    r.h1:Hide(); r.h2:Hide(); r.h3:Hide(); r.h4:Hide(); r.h5:Hide(); r.h6:Hide()
    PD.PaintDiffBar(r, nil)
    do
        local wantFs = spec.fs or (spec.kind == "head" and 16 or 13)
        local _, curFs = r.a:GetFont()
        if curFs ~= wantFs then
            r.a:SetFont(ns.FONT, wantFs,
                        ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        end
    end
    do
        local auxFs = (spec.fs == 14) and 14 or nil
        local fl = ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE"
        local _, bfs = r.b:GetFont()
        local wb = auxFs or 11
        if bfs ~= wb then r.b:SetFont(ns.FONT, wb, fl) end
        local _, cfs = r.c:GetFont()
        local wc = auxFs or 12
        if cfs ~= wc then r.c:SetFont(ns.FONT, wc, fl) end
    end
    PD.ClearMats(r)
    PD.ClearMatSegs(r)
    if spec._matsPending then PD.FinishSpecMats(spec) end
    PD.RowBorder(r, spec.cur)
    r.tagFs:Hide()
    r.tagBg:Hide()
    r.icon2:Hide()
    r.icon3:Hide()
    r.icon4:Hide()
    r.hsOwn:Hide()
    r.hsTot:Hide()
    r.hsCraft:Hide()
    r.hsGap:Hide()
    do
        local _, dfs = r.d:GetFont()
        if dfs ~= 11 then
            r.d:SetFont(ns.FONT, 11, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        end
    end

    local iconName = spec.icon
    local itemID = spec.it and spec.it[1]
    local showIcon = (spec.kind == "row" or spec.kind == "head") and (itemID or iconName) and true or false
    r.icon:SetShown(showIcon)
    if r.__iconZone then r.__iconZone:Hide() end
    if r.__vs then
        for _, c in ipairs(r.__vs.cards) do c:Hide() end
        for _, z in ipairs(r.__vs.zones) do z:Hide() end
    end
    if r.__pct then r.__pct:Hide() end
    if showIcon then
        r.icon:SetSize(20, 20)
        r.icon:ClearAllPoints()
        r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -math.floor((h - 20) / 2))
        SetIcon(r.icon, iconName or DG.ItemIcon(itemID))
    end

    if spec.kind == "head" then
        r.a:SetTextColor(Unpack(C_WHITE))
        r.a:SetText(spec.text or "")
        r.a:ClearAllPoints()
        if itemID or iconName then
            r.icon:SetSize(20, 20)
            r.icon:ClearAllPoints()
            r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
            SetIcon(r.icon, iconName or DG.ItemIcon(itemID))
            r.a:SetPoint("LEFT", r.icon, "RIGHT", 6, 0)
        else
            r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        end
        r.b:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        if spec.right and spec.right ~= "" then
            r.c:SetTextColor(Unpack(C_GREY))
            r.c:SetText(spec.right)
            r.c:ClearAllPoints()
            r.c:SetWordWrap(false)
            r.c:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        else
            r.c:SetText("")
        end
        r.c2:SetText("")
        if spec.tag then
            r.tagFs:SetTextColor(Unpack(spec.tag.color or { 0.42, 0.94, 0.62 }))
            r.tagFs:SetText(spec.tag.text or "")
            r.tagFs:ClearAllPoints()
            r.tagFs:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 6, 0)
            r.tagBg:ClearAllPoints()
            r.tagBg:SetPoint("TOPLEFT", r.tagFs, "TOPLEFT", -4, 1)
            r.tagBg:SetPoint("BOTTOMRIGHT", r.tagFs, "BOTTOMRIGHT", 4, -1)
            r.tagFs:Show()
            r.tagBg:Show()
        end
        if r.__warn then
            r.__warn:Hide()
            r.__warn.__tipLines = nil
        end
        if spec.warn and spec.warn[1] then
            local wz = PD.WarnChip(r)
            wz:ClearAllPoints()
            wz:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 8, 0)
            wz.__tipLines = spec.warn
            wz:Show()
        end
        r.sep:Hide()
        return
    end
    if spec.kind == "rechead" then
        r.h1:SetText(L["配方"])
        r.h1:ClearAllPoints()
        r.h1:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.h1:Show()
        r.h2:SetText(L["材料"])
        r.h2:ClearAllPoints()
        r.h2:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        r.h2:Show()
        r.h3:SetText(L["拍卖"])
        r.h3:ClearAllPoints()
        r.h3:SetPoint("RIGHT", r, "RIGHT", -(6 + PD.DiffBarW() + PD.REC_COST_W), 0)
        r.h3:Show()
        r.h4:SetText(L["制作成本"])
        r.h4:ClearAllPoints()
        r.h4:SetPoint("RIGHT", r, "RIGHT", -(6 + PD.DiffBarW()), 0)
        r.h4:Show()
        r.h5:SetText(L["难度"])
        r.h5:ClearAllPoints()
        r.h5:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        r.h5:Show()
        local SORT = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon"
        local X_ahR = -(6 + PD.DiffBarW() + PD.REC_COST_W)
        local function _act(col)
            return function()
                if PD.recipeSort ~= col then
                    PD.recipeSort, PD.recipeSortDesc = col, false
                elseif not PD.recipeSortDesc then
                    PD.recipeSortDesc = true
                else
                    PD.recipeSort, PD.recipeSortDesc = nil, false
                end
                PD.RequestRender()
            end
        end
        local function _ic(tex, on)
            SetIcon(tex, SORT)
            tex:SetSize(14, 14)
            if on then tex:SetVertexColor(1, 0.82, 0, 1)
            else tex:SetVertexColor(0.55, 0.57, 0.62, 1) end
            tex:SetShown(true)
        end
        local function _hc(fs, on)
            if on then fs:SetTextColor(1, 0.82, 0, 1)
            else fs:SetTextColor(Unpack(C_GREY)) end
        end
        local onAh = PD.recipeSort == "ah"
        _ic(r.icon, onAh)
        r.icon:SetPoint("RIGHT", r.h3, "LEFT", -3, 0)
        _hc(r.h3, onAh)
        r.hsTot:ClearAllPoints()
        r.hsTot:SetPoint("TOPRIGHT", r, "TOPRIGHT", X_ahR, 0)
        r.hsTot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", X_ahR, 0)
        r.hsTot:SetWidth(48)
        r.hsTot.__act = _act("ah")
        r.hsTot:Show()
        local onGap = PD.recipeSort == "gap"
        _ic(r.icon4, onGap)
        r.h6:SetText(L["差价"])
        r.h6:ClearAllPoints()
        r.h6:SetPoint("RIGHT", r, "RIGHT", X_ahR - 58, 0)
        _hc(r.h6, onGap)
        r.h6:Show()
        r.icon4:SetPoint("RIGHT", r.h6, "LEFT", -2, 0)
        r.hsGap:ClearAllPoints()
        r.hsGap:SetPoint("TOPRIGHT", r, "TOPRIGHT", X_ahR - 58, 0)
        r.hsGap:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", X_ahR - 58, 0)
        r.hsGap:SetWidth(58)
        r.hsGap.__act = _act("gap")
        r.hsGap:Show()
        local onCost = PD.recipeSort == "cost"
        _ic(r.icon2, onCost)
        r.icon2:SetPoint("RIGHT", r.h4, "LEFT", -3, 0)
        _hc(r.h4, onCost)
        r.hsOwn:ClearAllPoints()
        r.hsOwn:SetPoint("TOPRIGHT", r, "TOPRIGHT", -(6 + PD.DiffBarW()), 0)
        r.hsOwn:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -(6 + PD.DiffBarW()), 0)
        r.hsOwn:SetWidth(60)
        r.hsOwn.__act = _act("cost")
        r.hsOwn:Show()
        local onDiff = PD.recipeSort == "diff"
        _ic(r.icon3, onDiff)
        r.icon3:SetPoint("RIGHT", r.h5, "LEFT", -3, 0)
        _hc(r.h5, onDiff)
        r.hsCraft:ClearAllPoints()
        r.hsCraft:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, 0)
        r.hsCraft:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 0)
        r.hsCraft:SetWidth(40)
        r.hsCraft.__act = _act("diff")
        r.hsCraft:Show()
        r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText(""); r.dv:SetText(""); r.dv:Hide()
        r.sep:Hide()
        return
    end
    if spec.kind == "text" then
        r.a:SetTextColor(Unpack(spec.color or C_TEXT))
        r.a:SetText(spec.text or "")
        r.a:ClearAllPoints()
        if spec.center then
            r.a:SetPoint("CENTER", r, "CENTER", 0, 0)
        else
            r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        end
        r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        r.sep:Hide()
        return
    end
    r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    r.sep:Hide()

    if spec.kind == "lvhead" then
        local hout = ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE"
        r.f:SetText("")
        r.a:SetTextColor(Unpack(C_GREY))
        r.a:SetFont(ns.FONT, 12, hout)
        r.a:SetText(L["段落"])
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.e:SetTextColor(Unpack(C_GREY))
        r.e:SetFont(ns.FONT, 12, hout)
        r.e:SetText(L["配方"])
        r.e:ClearAllPoints()
        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, 0)
        r.b:SetTextColor(Unpack(C_GREY))
        r.b:SetFont(ns.FONT, 12, hout)
        r.b:SetText(L["材料"])
        r.b:ClearAllPoints()
        r.b:SetPoint("RIGHT", r, "RIGHT", -PD.TBL_MAT_RPAD, 0)
        r.c:SetText(L["制作次数"])
        r.d:SetText(L["单次花费"])
        r.c2:SetText(L["总花费"])
        r.c:SetTextColor(Unpack(C_GREY))
        r.d:SetTextColor(Unpack(C_GREY))
        r.c2:SetTextColor(Unpack(C_GREY))
        r.c:ClearAllPoints()
        r.c:SetPoint("RIGHT", r, "RIGHT", -PD.LV_CNT2_R, 0)
        r.d:ClearAllPoints()
        r.d:SetPoint("RIGHT", r, "RIGHT", -PD.LV_UNIT_R, 0)
        r.c2:ClearAllPoints()
        r.c2:SetPoint("RIGHT", r, "RIGHT", -PD.LV_CNT_R, 0)
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    if spec.kind == "colhead" then
        r.a:SetTextColor(Unpack(C_GREY))
        r.a:SetText(spec.text or "")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.c:SetTextColor(Unpack(C_GREY))
        r.c:SetText(spec.right or "")
        r.c:ClearAllPoints()
        r.c:SetWordWrap(false)
        if spec.craftAct then
            r.c:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -4)
        else
            r.c:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        end
        r.c2:SetText("")
        r.icon:SetSize(14, 14)
        r.icon:ClearAllPoints()
        r.icon2:SetSize(14, 14)
        r.icon2:ClearAllPoints()
        if spec.ownAct then
            r.c2:SetTextColor(Unpack(C_GREY))
            r.c2:SetText(spec.ownRight or "")
            r.c2:ClearAllPoints()
            r.c2:SetWordWrap(false)
            if spec.craftAct then
                r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.OwnR(), -4)
            else
                r.c2:SetPoint("RIGHT", r, "RIGHT", -PD.OwnR(), 0)
            end
            SetIcon(r.icon2, "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
            r.icon2:SetPoint("RIGHT", r.c2, "LEFT", -4, 0)
            if spec.ownOn then
                r.icon2:SetVertexColor(1, 0.82, 0, 1)
            else
                r.icon2:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
            r.icon2:SetShown(true)
            r.hsOwn:ClearAllPoints()
            r.hsOwn:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.OwnR(), 0)
            r.hsOwn:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -PD.OwnR(), 0)
            r.hsOwn:SetWidth(92)
            r.hsOwn.__act = spec.ownAct
            r.hsOwn:Show()
        else
            r.hsOwn:Hide()
        end
        if spec.act then
            SetIcon(r.icon, "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
            r.icon:SetPoint("RIGHT", r.c, "LEFT", -4, 0)
            if spec.sortOn then
                r.icon:SetVertexColor(1, 0.82, 0, 1)
            else
                r.icon:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
            r.icon:SetShown(true)
            r.hsTot:ClearAllPoints()
            r.hsTot:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, 0)
            if spec.craftAct then
                r.hsTot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 17)
            else
                r.hsTot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 0)
            end
            r.hsTot:SetWidth(92)
            r.hsTot.__act = spec.act
            r.hsTot:Show()
        else
            r.hsTot:Hide()
        end
        r.b:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        if spec.craftAct then
            r.d:SetTextColor(Unpack(C_GREY))
            do
                local _, dfs = r.d:GetFont()
                if dfs ~= 12 then
                    r.d:SetFont(ns.FONT, 12, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
                end
            end
            r.d:SetText(spec.craftRight or "")
            r.d:ClearAllPoints()
            r.d:SetWordWrap(false)
            r.d:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
            SetIcon(r.icon3, "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
            r.icon3:SetSize(14, 14)
            r.icon3:ClearAllPoints()
            r.icon3:SetPoint("RIGHT", r.d, "LEFT", -4, 0)
            if spec.craftOn then
                r.icon3:SetVertexColor(1, 0.82, 0, 1)
            else
                r.icon3:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
            r.icon3:SetShown(true)
            r.hsCraft:ClearAllPoints()
            r.hsCraft:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -17)
            r.hsCraft:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 0)
            r.hsCraft:SetWidth(92)
            r.hsCraft.__act = spec.craftAct
            r.hsCraft:Show()
        else
            r.hsCraft:Hide()
        end
        r.dv:Hide()
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    if spec.kind == "vs" then
        local vs = PD.VsBlock(r)
        local W = tonumber(spec.vw) or tonumber(PD.splitRW) or 160
        local cw = math.max(40, math.floor((W - 8) / 2))
        for k = 1, 2 do
            local d = spec.cards and spec.cards[k] or nil
            local c, z = vs.cards[k], vs.zones[k]
            if d then
                c:ClearAllPoints()
                if k == 1 then
                    c:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
                else
                    c:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)
                end
                c:SetSize(cw, h)
                c.lab:SetText(d.lab or "")
                c.lab:SetTextColor(Unpack(d.win and C_WHITE or C_GREY))
                local pc = d.win and { 0.42, 0.94, 0.62 } or (d.priceOk and C_TEXT or C_GREY)
                c.price:SetTextColor(Unpack(pc))
                c.price:SetText(d.price or "—")
                c.nm:SetTextColor(Unpack(d.dim and C_GREY or C_TEXT))
                c.nm:SetText(d.name or "")
                if d.it then
                    c.ic:SetSize(22, 22)
                    SetIcon(c.ic, DG.ItemIcon(d.it))
                    c.ic:Show()
                else
                    c.ic:Hide()
                end
                if d.win then
                    c.badgeFs:SetText(L["最省"])
                    c.badge:Show()
                else
                    c.badge:Hide()
                end
                c:Show()
                z:ClearAllPoints()
                z:SetPoint("TOPLEFT", c, "TOPLEFT", 0, 0)
                z:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", 0, 0)
                z.__tipLines = nil
                z.__tipExtra = d.tipExtra
                z.__act = nil
                z.__it = d.it and { d.it } or nil
                z:Show()
            else
                c:Hide()
                z:Hide()
            end
        end
        r.a:SetText(""); r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        r.dv:SetText(""); r.dv:Hide()
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    if spec.gr3 then
        r.a:SetTextColor(Unpack(C_GOLD))
        r.a:SetText(spec.lv or "")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", PD.GR_LV_X, 0)
        r.b:SetTextColor(Unpack(C_TEXT))
        r.b:SetText(spec.loc or "")
        r.b:ClearAllPoints()
        r.b:SetPoint("LEFT", r, "LEFT", PD.GR_LOC_X, 0)
        r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.f:SetText("")
        r.dv:Hide()
        local gcol = spec.nameColor
        if not gcol and spec.qItem then
            local gq = PD.QualCached(spec.qItem)
            if gq then gcol = { DG.QColor(gq) } end
        end
        if spec.icons then
            r.e:SetText("")
            r.icon:Hide()
            for k = 1, #r.gic do
                local g, id = r.gic[k], spec.icons[k]
                if id then
                    g:Show()
                    g:ClearAllPoints()
                    if k == 1 then
                        g:SetPoint("RIGHT", r, "RIGHT", -6, 0)
                    else
                        g:SetPoint("RIGHT", r.gic[k - 1], "LEFT", -4, 0)
                    end
                    SetIcon(g, DG.ItemIcon(id))
                else
                    g:Hide()
                end
            end
        else
            r.e:SetText(spec.text or "")
            r.e:SetTextColor(Unpack(gcol or C_TEXT))
            r.e:ClearAllPoints()
            r.e:SetPoint("RIGHT", r, "RIGHT", -6, 0)
            r.icon:SetSize(PD.GR_ICON_W, PD.GR_ICON_W)
            r.icon:ClearAllPoints()
            r.icon:SetPoint("RIGHT", r.e, "LEFT", -6, 0)
            SetIcon(r.icon, iconName or DG.ItemIcon(itemID))
        end
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    if spec.lvstep then
        if spec.passed then
            r.a:SetTextColor(Unpack(C_DIM))
            r.e:SetTextColor(Unpack(C_DIM))
            r.b:SetTextColor(Unpack(C_DIM))
            r.c:SetTextColor(Unpack(C_DIM))
            r.c2:SetTextColor(Unpack(C_DIM))
            r.d:SetTextColor(Unpack(C_DIM))
        else
            r.a:SetTextColor(Unpack(C_TEXT))
            r.e:SetTextColor(Unpack(C_GOLD))
            r.b:SetTextColor(Unpack(C_GREY))
            r.c:SetTextColor(Unpack(C_GOLD))
            r.c2:SetTextColor(Unpack(C_GOLD))
            r.d:SetTextColor(Unpack(C_GREY))
        end
        r.a:SetText(spec.rng or "")
        r.e:SetText(spec.text or "")
        r.b:SetText("")
        r.c:SetText(spec.cnt or "")
        r.c2:SetText(spec.tot or "")
        r.d:SetText(spec.unit or "")
        r.f:SetText("")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", 6, PD.TBL_NAME_DY)
        r.e:ClearAllPoints()
        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)
        r.b:ClearAllPoints()
        r.b:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_SRC_DY)
        r.c2:ClearAllPoints()
        r.c2:SetPoint("RIGHT", r, "RIGHT", -PD.LV_CNT_R, 0)
        r.d:ClearAllPoints()
        r.d:SetPoint("RIGHT", r, "RIGHT", -PD.LV_UNIT_R, 0)
        r.c:ClearAllPoints()
        r.c:SetPoint("RIGHT", r, "RIGHT", -PD.LV_CNT2_R, 0)
        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)
        r.icon:ClearAllPoints()
        r.icon:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)
        r.icon:SetDesaturated(spec.passed and true or false)
        if spec.sbVals then
            PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)
        else
            PD.HideSkillBar(r)
        end
        PD.PaintCard(r, spec.card)
        local iz = PD.IconZone(r)
        iz.__it = itemID and { itemID } or nil
        iz.__tipLines = nil
        iz.__act = nil
        iz.__tipExtra = spec.tipExtra
        iz:ClearAllPoints()
        iz:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)
        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)
        iz:SetShown(itemID and true or false)
        r.__cardZone:SetFrameLevel(iz:GetFrameLevel() + 1)
        PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed)
        return
    end

    local padL = showIcon and ((iconName and not itemID) and 28 or 32) or 6
    local ncol = spec.nameColor
    if not ncol and spec.qItem then
        local q = PD.QualCached(spec.qItem)
        if q then ncol = { DG.QColor(q) } end
    end
    r.a:SetTextColor(Unpack(ncol or C_TEXT))
    r.a:SetText(spec.text or "")
    r.b:SetText((spec.is_new and L[" |cff40d940新|r"] .. " " or "") .. (spec.sub or ""))
    r.c:SetText(spec.right or "")
    r.c:SetTextColor(Unpack(spec.rightColor or C_GOLD))
    r.d:SetText(spec.right2 or "")
    if spec.right2 and spec.right2 ~= "" then
        local dfsW = (spec.fs == 14) and 14 or 12
        local _, dfs = r.d:GetFont()
        if dfs ~= dfsW then
            r.d:SetFont(ns.FONT, dfsW, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        end
    end
    if spec.right2Color then
        r.d:SetTextColor(Unpack(spec.right2Color))
    end
    r.e:SetText("")
    if spec.rightOwn and h > PD.ROW_H1 then
        r.c2:SetText(spec.rightOwn)
        r.c2:SetTextColor(Unpack(spec.rightOwnColor or C_TEXT))
        r.c2:ClearAllPoints()
        r.c2:SetWordWrap(false)
        r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.OwnR(), -4)
    else
        r.c2:SetText("")
    end
    r.f:SetTextColor(Unpack(spec.matColor or C_TEXT))
    if not spec.matSegs then r.f:SetText(spec.mats or "") end
    r.a:ClearAllPoints()
    r.c:ClearAllPoints()
    r.f:ClearAllPoints()
    if h <= PD.ROW_H1 then
        r.a:SetPoint("LEFT", r, "LEFT", padL, 0)
        r.b:SetText("")
        r.c:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        r.d:SetText("")
        r.f:SetText("")
    else
        r.a:SetPoint("TOPLEFT", r, "TOPLEFT", padL, -4)
        r.b:ClearAllPoints()
        r.b:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", padL, 4)
        r.c:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -4)
        r.d:ClearAllPoints()
        r.d:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
        r.f:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end
    end
    if h > PD.ROW_H1 and (spec.sbdiff or spec.costStr or spec.ahStr) then
        PD.PaintDiffBar(r, spec.sbdiff)
        if spec.costStr then
            r.e:SetText(spec.costStr)
            r.e:SetTextColor(Unpack(C_GOLD))
            r.e:ClearAllPoints()
            r.e:SetPoint("TOPRIGHT", r, "TOPRIGHT", -(6 + PD.DiffBarW()), -4)
            r.e:SetWordWrap(false)
        end
        if spec.ahStr then
            r.c2:SetText(spec.ahStr)
            r.c2:SetTextColor(Unpack(C_TEXT))
            r.c2:ClearAllPoints()
            r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -(6 + PD.DiffBarW() + PD.REC_COST_W), -4)
            r.c2:SetWordWrap(false)
        end
        if spec.pct then
            local chip = PD.PctChip(r)
            chip.fs:SetText(spec.pct.text)
            chip.fs:SetTextColor(Unpack(spec.pct.color))
            chip:ClearAllPoints()
            chip:SetPoint("TOPRIGHT", r.c2, "BOTTOMRIGHT", 0, -1)
            chip:SetHeight(15)
            chip:SetWidth(chip.fs:GetStringWidth() + 8)
            chip:SetFrameLevel(r:GetFrameLevel() + 2)
            chip:Show()
        elseif r.__pct then
            r.__pct:Hide()
        end
    end
    if spec.dval and h > PD.ROW_H1 then
        r.d:SetText(spec.dpre or "")
        r.dv:SetText(spec.dval)
        r.dv:SetTextColor(Unpack(C_GREY))
        r.dv:ClearAllPoints()
        r.dv:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
        r.dv:Show()
        r.d:ClearAllPoints()
        r.d:SetPoint("RIGHT", r.dv, "LEFT", 0, 0)
        local vz = PD.IconZone(r)
        vz.__it = nil
        vz.__tipLines = spec.vlines or PD.VendorLines(spec.src)
        vz.__act = spec.dact or PD.VendorAct(spec.src)
        vz:ClearAllPoints()
        vz:SetPoint("TOPLEFT", r.dv, "TOPLEFT", 0, 1)
        vz:SetPoint("BOTTOMRIGHT", r.dv, "BOTTOMRIGHT", 0, -1)
        vz:Show()
    end
    if spec.tag then
        r.tagFs:SetTextColor(Unpack(spec.tag.color or { 0.42, 0.94, 0.62 }))
        r.tagFs:SetText(spec.tag.text or "")
        r.tagFs:ClearAllPoints()
        r.tagFs:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 6, 0)
        r.tagBg:ClearAllPoints()
        r.tagBg:SetPoint("TOPLEFT", r.tagFs, "TOPLEFT", -4, 1)
        r.tagBg:SetPoint("BOTTOMRIGHT", r.tagFs, "BOTTOMRIGHT", 4, -1)
        r.tagFs:Show()
        r.tagBg:Show()
    end
end

PD.BT_COL1 = 88
PD.BT_W_LAST = 236
PD.BT_H_HEAD = 28
PD.BT_LINE_H = 19
PD.BT_ROW_MIN = 34

function PD.BuildBonusTable(parent)
    local card = CreateFrame("Frame", nil, parent)
    PD.bonusCard = card
    ns.hui.BuildRoundedBG(card, 6, ns.hui.layer.L2, "both", true, 1)
    card:Hide()
    local root = CreateFrame("Frame", nil, card)
    PD.bonusTable = root
    local W = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.SEC_IN
    root:SetSize(W, 10)
    PD.BT_W = W
    PD.BT_COLW = math.floor((W - PD.BT_COL1 - PD.BT_W_LAST) / 3)

    local heads = { L["专业"], format(L["技能 %d"], 20), format(L["技能 %d"], 140),
                    format(L["技能 %d"], 300), L["职业版对照 / 其他功能"] }
    for j, txt in ipairs(heads) do
        local fs = MakeFS(root, 14, C_GOLD, "LEFT")
        local x = (j == 1) and 0 or (PD.BT_COL1 + (j - 2) * PD.BT_COLW)
        fs:SetPoint("TOPLEFT", root, "TOPLEFT", x, -5)
        fs:SetText(txt)
    end
    local tipBtn = CreateFrame("Button", nil, root)
    tipBtn:EnableMouse(true)
    tipBtn:SetSize(PD.BT_W_LAST - 6, PD.BT_H_HEAD - 2)
    tipBtn:SetPoint("TOPLEFT", root, "TOPLEFT", PD.BT_COL1 + 3 * PD.BT_COLW, -2)
    tipBtn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["职业版对照 / 其他功能"], 1, 0.82, 0)
        GameTooltip:AddLine(L["数值以 60 级为基准、随等级成长 —— 游戏内低等级看到的数字更小属正常缩放。"],
                            1, 1, 1, true)
        GameTooltip:Show()
    end)
    tipBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    local rule = root:CreateTexture(nil, "ARTWORK")
    rule:SetHeight(1)
    if ns.hui and ns.hui.layer then
        local dv = ns.hui.layer.DIV
        rule:SetColorTexture(dv[1], dv[2], dv[3], dv[4] or 1)
    else
        rule:SetColorTexture(1, 0.75, 0.35, 0.35)
    end
    rule:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -PD.BT_H_HEAD + 3)
    rule:SetPoint("RIGHT", root, "RIGHT", 0, 0)

    root.__rows = {}
    for k = 1, #(D.order or {}) do
        local r = CreateFrame("Button", nil, root)
        r:EnableMouse(true)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.icon:SetSize(15, 15)
        r.icon:SetPoint("LEFT", r, "LEFT", 0, 0)
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetWordWrap(false)
        r.name:SetPoint("LEFT", r, "LEFT", 21, 0)
        r.cells = {}
        for j = 1, 3 do
            local fs = MakeFS(r, 14, C_TEXT, "LEFT")
            fs:SetWordWrap(true)
            fs:SetWidth(PD.BT_COLW - 6)
            fs:SetPoint("TOPLEFT", r, "TOPLEFT", PD.BT_COL1 + (j - 1) * PD.BT_COLW, -7)
            r.cells[j] = fs
        end
        local cx = PD.BT_COL1 + 3 * PD.BT_COLW
        r.cmp1 = MakeFS(r, 14, C_GREY, "LEFT")
        r.cmp1:SetWordWrap(true)
        r.cmp1:SetWidth(PD.BT_W_LAST - 10)
        r.cmp1:SetPoint("TOPLEFT", r, "TOPLEFT", cx, -7)
        r.cmp2 = MakeFS(r, 14, C_TEXT, "LEFT")
        r.cmp2:SetWordWrap(true)
        r.cmp2:SetWidth(PD.BT_W_LAST - 10)
        r.cmp2:SetPoint("TOPLEFT", r, "TOPLEFT", cx, -26)
        r.sep = r:CreateTexture(nil, "OVERLAY")
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.08)
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
        r.sep:SetPoint("RIGHT", r, "RIGHT", 0, 0)
        r.hl = r:CreateTexture(nil, "BACKGROUND")
        r.hl:SetAllPoints()
        if ns.hui and ns.hui.layer then
            local c4 = ns.hui.layer.L4
            r.hl:SetColorTexture(c4[1], c4[2], c4[3], c4[4] or 1)
        else
            r.hl:SetColorTexture(1, 1, 1, 0.04)
        end
        r.hl:Hide()
        r:SetScript("OnEnter", function(self)
            self.hl:Show()
            if self.__lines and #self.__lines > 0 then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                for _, ln in ipairs(self.__lines) do
                    if ln[1] and ln[1] ~= "" then
                        GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                    end
                end
                GameTooltip:Show()
            end
        end)
        r:SetScript("OnLeave", function(self)
            self.hl:Hide()
            GameTooltip:Hide()
        end)
        root.__rows[k] = r
    end
    root:Hide()
    card:Hide()
end

local function btLines(fs, est)
    if fs.GetNumLines then
        local n = fs:GetNumLines()
        if type(n) == "number" and n > 0 then return n end
    end
    return est
end

function PD.FillBonusTable()
    local root = PD.bonusTable
    if not root then
        return
    end
    local used = 0
    local yCur = -PD.BT_H_HEAD
    local lastUsed = nil
    for _, slug in ipairs(D.order or {}) do
        local p = D.pro[slug]
        local camp = (p and p.camp) or {}
        local r = root.__rows[used + 1]
        if r and #camp > 0 then
            local t1, t2, t3, caps = {}, {}, {}, {}
            local buffTxt, cmpName = "", ""
            for _, c in ipairs(camp) do
                local lv = c[4] or 0
                local bucket, tag
                if lv == 20 then
                    bucket = t1
                elseif lv == 140 then
                    bucket = t2
                elseif lv == 300 then
                    bucket = t3
                elseif lv < 140 then
                    bucket, tag = t1, format("(%d)", lv)
                else
                    bucket, tag = t3, format("(%d)", lv)
                end
                bucket[#bucket + 1] = (c[2] or "?") .. (tag or "")
                if c[6] and c[6] ~= "" and buffTxt == "" then
                    buffTxt = c[6]
                    cmpName = c[9] or ""
                end
                if c[10] and c[10] ~= "" then caps[#caps + 1] = c[10] end
            end
            SetIcon(r.icon, p.icon)
            r.name:SetText(p.name or slug)
            r.cells[1]:SetText(table.concat(t1, "、"))
            r.cells[2]:SetText(table.concat(t2, "、"))
            r.cells[3]:SetText(table.concat(t3, "、"))
            if buffTxt ~= "" then
                r.cmp1:SetText(cmpName ~= "" and cmpName or L["营地增益"])
                r.cmp1:SetTextColor(Unpack(C_GREY))
                r.cmp2:SetText(format("|cff7fdc7f%s|r", buffTxt))
            elseif #caps > 0 then
                r.cmp1:SetText(L["功能"])
                r.cmp2:SetText(format("|cff7fdc7f%s|r", format(L["营火容量 %s"], table.concat(caps, "/"))))
            else
                r.cmp1:SetText(L["功能"])
                r.cmp2:SetText(format("|cff9a958a%s|r", camp[1][5] or ""))
            end
            local lines = {}
            for _, c in ipairs(camp) do
                lines[#lines + 1] = { c[2] or "?", 1, 0.82, 0 }
                if c[5] and c[5] ~= "" then
                    lines[#lines + 1] = { c[5], 0.88, 0.88, 0.88 }
                end
                if c[6] and c[6] ~= "" then
                    lines[#lines + 1] = { format(L["增益：%s"], c[6]), 0.5, 0.9, 0.5 }
                end
                if c[11] and #c[11] > 0 then
                    lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(c[11])), 0.7, 0.7, 0.7 }
                end
                if c[12] and c[12][1] then
                    lines[#lines + 1] = { format(L["图纸：%s"], DG.ItemName(c[12][1])) }
                end
            end
            r.__lines = lines
            local plain = (r.cmp2:GetText():gsub("|cff%x%x%x%x%x%x", ""))
            plain = (plain:gsub("|r", ""))
            local need = btLines(r.cmp1, 1) + btLines(r.cmp2, #PD.Wrap(plain, 14, PD.BT_W_LAST - 10))
            for j = 1, 3 do
                local n = btLines(r.cells[j], #PD.Wrap(r.cells[j]:GetText(), 14, PD.BT_COLW - 6))
                if n > need then need = n end
            end
            local rowH = math.max(PD.BT_ROW_MIN, need * PD.BT_LINE_H + 10)
            r:SetPoint("TOPLEFT", root, "TOPLEFT", 0, yCur)
            r:SetSize(PD.BT_W, rowH)
            r.sep:Show()
            r:Show()
            yCur = yCur - rowH
            lastUsed = r
            used = used + 1
        elseif r then
            r:Hide()
        end
    end
    if lastUsed then lastUsed.sep:Hide() end
    for i = used + 1, #root.__rows do
        local r = root.__rows[i]
        if r then r:Hide() end
    end
    PD.bonusTableH = -yCur
    root:SetHeight(PD.bonusTableH)
end

function PD.placeBonusTable(y)
    PD.FillBonusTable()
    PD.bonusCard:ClearAllPoints()
    PD.bonusCard:SetPoint("TOPLEFT", PD.child, "TOPLEFT", 0, -y)
    PD.bonusCard:SetSize(PD.RIGHT_W - PD.SEC_PAD_X, (PD.bonusTableH or 0) + 2 * PD.SEC_PAD)
    PD.bonusCard:Show()
    PD.bonusTable:ClearAllPoints()
    PD.bonusTable:SetPoint("TOPLEFT", PD.bonusCard, "TOPLEFT", PD.LIST_PAD, -PD.SEC_PAD)
    PD.bonusTable:Show()
end

local TR_RANK_COLOR = { { 0.36, 0.79, 0.65 }, { 0.94, 0.62, 0.15 },
                        { 0.85, 0.35, 0.19 }, { 0.64, 0.18, 0.18 } }

function PD.BuildTrainerBoard(parent)
    local card = CreateFrame("Frame", nil, parent)
    PD.trainerCard = card
    ns.hui.BuildRoundedBG(card, 6, ns.hui.layer.L2, "both", true, 1)
    card:Hide()
    local root = CreateFrame("Frame", nil, card)
    PD.trainerBoard = root
    root:SetSize(PD.RIGHT_W - 2 * PD.LIST_PAD, 10)
    root.__chips = {}
    root.__fs = {}
end

local function TrRngLow(rng)
    return tonumber(rng:match("^(%d+)")) or 0
end

local function TrNameOf(t)
    local loc = (GetLocale() == "zhTW") and t.tw or t.zh
    return (loc and loc ~= "") and loc or t.en
end

local TR_ZONE_CACHE = {}
local function TrZoneOf(t)
    local cached = TR_ZONE_CACHE[t.map]
    if cached ~= nil then return cached or nil end
    local nm
    if C_Map and C_Map.GetMapInfo then
        local ok, info = pcall(C_Map.GetMapInfo, t.map)
        if ok and info then nm = info.name end
    end
    TR_ZONE_CACHE[t.map] = nm or false
    return nm
end

local function TrLocOf(t)
    local loc = GetLocale()
    if loc == "enUS" then return t.loc_en end
    local zh = (loc == "zhTW") and t.loc_tw or t.loc_zh
    if not zh then return t.loc_en end
    local sub = zh:match("^(.-) · ")
    if not sub then return zh end
    local zone = TrZoneOf(t)
    if not zone then return zh end
    return sub .. " · " .. zone
end

function PD.FillTrainerBoard()
    local root = PD.trainerBoard
    if not root then return 0 end
    local d = ns.ProfTrainers and ns.ProfTrainers[PD.cur]
    if not (d and d.list and #d.list > 0) then
        for _, c in ipairs(root.__chips) do c:Hide() end
        for _, f in pairs(root.__fs) do f:Hide() end
        return 0
    end
    local fac = PD.trFac or "all"
    local rngs, seen = {}, {}
    for _, t in ipairs(d.list) do
        local r = t.rng or "?"
        if not seen[r] then seen[r] = true; rngs[#rngs + 1] = r end
    end
    table.sort(rngs, function(a, b) return TrRngLow(a) < TrRngLow(b) end)
    local COLS = #rngs
    if COLS == 0 then return 0 end
    local W = PD.RIGHT_W - PD.SEC_PAD_X - 2 * PD.LIST_PAD
    local GAP = 8
    local COL_W = math.floor((W - (COLS - 1) * GAP) / COLS)
    if root.__bands then
        for i = COLS + 1, #root.__bands do root.__bands[i]:Hide() end
    end
    for _, f in pairs(root.__fs) do f:Hide() end
    for _, c in ipairs(root.__chips) do c:Hide() end
    local chipN, fsN = 0, 0
    local maxH = 0
    for ci, rng in ipairs(rngs) do
        local x0 = (ci - 1) * (COL_W + GAP)
        local rk = d.ranks and d.ranks[ci]
        local rc = TR_RANK_COLOR[ci] or TR_RANK_COLOR[#TR_RANK_COLOR]
        fsN = fsN + 1
        local h1 = root.__fs[fsN]
        if not h1 then h1 = MakeFS(root, 14, C_GOLD, "LEFT"); root.__fs[fsN] = h1 end
        h1:ClearAllPoints()
        h1:SetPoint("TOPLEFT", root, "TOPLEFT", x0, 0)
        local rkName = rk and (GetLocale() == "zhTW" and rk.tw or rk.zh) or nil
        h1:SetText((rkName and (rkName .. " ") or "") .. rng)
        h1:Show()
        fsN = fsN + 1
        local h2 = root.__fs[fsN]
        if not h2 then h2 = MakeFS(root, 13, C_GREY, "LEFT"); root.__fs[fsN] = h2 end
        h2:ClearAllPoints()
        h2:SetPoint("TOPLEFT", root, "TOPLEFT", x0, -22)
        if rk and (rk.sk or rk.lv) then
            h2:SetText(format("%s %s · %s %s", L["进阶"],
                rk.sk and tostring(rk.sk) or "-", L["角色等级"],
                rk.lv and tostring(rk.lv) or "-"))
        elseif rk and rk.cap then
            h2:SetText(format(L["上限 %d"], rk.cap))
        else
            h2:SetText("")
        end
        h2:Show()
        root.__bands = root.__bands or {}
        local band = root.__bands[ci]
        if not band then
            band = root:CreateTexture(nil, "ARTWORK")
            root.__bands[ci] = band
        end
        band:SetHeight(2)
        band:SetColorTexture(rc[1], rc[2], rc[3], 0.9)
        band:ClearAllPoints()
        band:SetPoint("TOPLEFT", root, "TOPLEFT", x0, -40)
        band:SetPoint("RIGHT", root, "TOPLEFT", x0 + COL_W, -40)
        band:Show()
        local yCur = -46
        for _, g in ipairs({ "A", "H", "B" }) do
            if fac == "all" or fac == g or g == "B" then
                local rows = {}
                for _, t in ipairs(d.list) do
                    if (t.rng or "?") == rng and (t.fac == g or (g == "B" and t.fac == "B"))
                        and (fac == "all" or fac == t.fac or t.fac == "B") then
                        rows[#rows + 1] = t
                    end
                end
                if #rows > 0 then
                    for _, t in ipairs(rows) do
                        chipN = chipN + 1
                        local c = root.__chips[chipN]
                        if not c then
                            c = CreateFrame("Button", nil, root)
                            c:EnableMouse(true)
                            root.__chips[chipN] = c
                            if ns.hui.HuiCardFX then ns.hui.HuiCardFX(c, 6, 3) end
                            c.n = MakeFS(c, 14, { 1, 1, 1 }, "LEFT")
                            c.l = MakeFS(c, 13, C_GREY, "LEFT")
                            c.xy = MakeFS(c, 13, { 0.71, 0.83, 0.96 }, "RIGHT")
                        end
                        if c.__huiCard then ns.hui.HuiCardState(c, "norm") end
                        c:SetSize(COL_W, 34)
                        c:ClearAllPoints()
                        c:SetPoint("TOPLEFT", root, "TOPLEFT", x0, yCur)
                        c.n:ClearAllPoints()
                        c.n:SetPoint("TOPLEFT", c, "TOPLEFT", 8, -4)
                        c.n:SetText(TrNameOf(t))
                        c.n:Show()
                        c.l:ClearAllPoints()
                        c.l:SetPoint("TOPLEFT", c, "TOPLEFT", 8, -20)
                        c.l:SetText(TrLocOf(t) or "")
                        c.l:Show()
                        c.xy:ClearAllPoints()
                        c.xy:SetPoint("TOPRIGHT", c, "TOPRIGHT", -8, -10)
                        c.xy:SetText(format("%g, %g", t.x, t.y))
                        c.xy:Show()
                        c.__tr = t
                        c:SetScript("OnClick", function()
                            PD.MarkVendorLoc({ nil, t.map, t.x, t.y })
                        end)
                        c:SetScript("OnEnter", function(self)
                            if self.__huiCard then ns.hui.HuiCardState(self, "hover") end
                            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                            GameTooltip:ClearLines()
                            GameTooltip:AddLine(t.en, 1, 0.82, 0)
                            local loc2 = TrLocOf(t)
                            if loc2 and loc2 ~= "" then GameTooltip:AddLine(loc2, 1, 1, 1) end
                            if t.note and t.note ~= "" then
                                GameTooltip:AddLine(t.note, 0.7, 0.7, 0.7)
                            end
                            GameTooltip:AddLine(L["点击：在地图上标记该 NPC"], 1, 0.82, 0)
                            GameTooltip:Show()
                        end)
                        c:SetScript("OnLeave", function(self)
                            if self.__huiCard then ns.hui.HuiCardState(self, "norm") end
                            GameTooltip:Hide()
                        end)
                        c:Show()
                        yCur = yCur - 38
                    end
                    yCur = yCur - 6
                end
            end
        end
        local colH = -yCur
        if colH > maxH then maxH = colH end
    end
    PD.trainerBoardH = maxH
    return maxH
end

function PD.placeTrainerBoard(y)
    local h = PD.FillTrainerBoard()
    if h <= 0 then
        if PD.trainerCard then PD.trainerCard:Hide() end
        PD.trainerBoardH = 0
        return
    end
    PD.trainerCard:ClearAllPoints()
    PD.trainerCard:SetPoint("TOPLEFT", PD.child, "TOPLEFT", 0, -y)
    PD.trainerCard:SetSize(PD.RIGHT_W - PD.SEC_PAD_X, h + 2 * PD.SEC_PAD)
    PD.trainerCard:Show()
    PD.trainerBoard:ClearAllPoints()
    PD.trainerBoard:SetPoint("TOPLEFT", PD.trainerCard, "TOPLEFT", PD.LIST_PAD, -PD.SEC_PAD)
    PD.trainerBoard:SetSize(PD.RIGHT_W - 2 * PD.LIST_PAD, h)
    PD.trainerBoard:Show()
end

local function ixCardSub(slug, p)
    if slug == "camping" then
        local n = 0
        for _, q in ipairs(D.order or {}) do
            local q2 = D.pro[q]
            if q2 and q2.camp then n = n + #q2.camp end
        end
        return format(L["物件 %d · 职业加成"], n)
    end
    if p.section == "gathering" then
        local g = GA and GA[slug]
        if slug == "skinning" then
            return format(L["档次 %d"], g and #g or 0)
        end
        return format(L["节点 %d"], g and #g or 0)
    end
    if slug == "fishing" then
        local g = GA and GA.fishing
        return format(L["区域 %d"], g and #g or 0)
    end
    return format(L["配方 %d 条"], p.recipes or 0)
end

local function ixGroupOf(p)
    if p.section == "crafting" then return 1 end
    if p.section == "gathering" then return 2 end
    if p.section == "camping" then return 4 end
    return 3
end

local IX_GROUP_LABELS

function PD.SetCardHover(c, on)
    on = on and true or false
    c.__hlOn = on
    if c.__hov then
        for _, t in ipairs(c.__hov) do t:SetShown(on) end
    elseif on then
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
        if c.__ixLearned then
            local r, g, b = PD.NavAccent()
            c:SetBackdropBorderColor(r, g, b, DG.LOOT_CARD_EDGE_HOVER)
        else
            c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
        end
    else
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        if c.__ixLearned then
            local r, g, b = PD.NavAccent()
            c:SetBackdropBorderColor(r, g, b, DG.LOOT_CARD_EDGE)
        else
            c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
        end
    end
end

function PD.BuildIndexGrid(parent)
    IX_GROUP_LABELS = {
        L["制造专业 —— 每个角色选两个主要专业"],
        L["采集专业 —— 为制造专业提供材料"],
        L["次要专业 —— 每个角色三个都能学"],
        L["营地系统"],
    }
    local w = PD.RIGHT_W - 2 * PD.LIST_PAD
    local root = CreateFrame("Frame", nil, parent)
    root:SetSize(w, 10)
    PD.ixRoot = root

    PD.ixHeads = {}
    for gi = 1, 4 do
        local fs = MakeFS(root, 12, C_GOLD, "LEFT")
        fs:SetText(IX_GROUP_LABELS[gi])
        PD.ixHeads[gi] = fs
    end

    PD.ixCards = {}
    local byGroup = { {}, {}, {}, {} }
    for _, slug in ipairs(D.order or {}) do
        local p = D.pro[slug]
        if p then
            local gi = ixGroupOf(p)
            local c = CreateFrame("Button", nil, root, "BackdropTemplate")
            if ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG and ns.hui.BuildCapsule then
                local _, bord = ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
                c.__ixBorder = bord
                c.__hov = ns.hui.BuildCapsule(c, 6, ns.hui.layer.L4, 1, 2)
                for _, ht in ipairs(c.__hov) do ht:Hide() end
            else
                c:SetBackdrop({
                    bgFile = "Interface\\Buttons\\WHITE8x8",
                    edgeFile = "Interface\\Buttons\\WHITE8x8",
                    edgeSize = 1,
                })
            end
            PD.SetCardHover(c, false)
            c:EnableMouse(true)            c.icon = c:CreateTexture(nil, "ARTWORK")
            c.icon:SetSize(PD.IX_ICON, PD.IX_ICON)
            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(c.icon) end
            c.icon:SetPoint("LEFT", c, "LEFT", 7, 0)
            SetIcon(c.icon, p.icon)
            c.name = MakeFS(c, 16, C_TEXT, "LEFT")
            c.name:SetWordWrap(false)
            c.name:SetPoint("TOPLEFT", c, "TOPLEFT", PD.IX_ICON + 13, -4)
            c.name:SetText(p.name or slug)
            c.sub = MakeFS(c, 14, C_GREY, "LEFT")
            c.sub:SetWordWrap(false)
            c.sub:SetPoint("BOTTOMLEFT", c, "BOTTOMLEFT", PD.IX_ICON + 13, 3)
            c.sub:SetText(ixCardSub(slug, p))
            c.__slug = slug
            c.lv = MakeFS(c, 12, C_TEXT, "RIGHT")
            c.lv:SetPoint("TOPRIGHT", c, "TOPRIGHT", -7, -5)
            c.lv:Hide()
            c:SetScript("OnEnter", function(self) PD.SetCardHover(self, true) end)
            c:SetScript("OnLeave", function(self) PD.SetCardHover(self, false) end)
            c:SetScript("OnClick", function(self)
                ns.PlaySound(1)
                if slug == "camping" then
                    PD.Show("camping")
                    PD.campView = "bonus"
                else
                    PD.Show(slug)
                end
            end)
            c:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(PD.scroll, PD.child, delta)
            end)
            byGroup[gi][#byGroup[gi] + 1] = c
            PD.ixCards[#PD.ixCards + 1] = c
        end
    end

    PD.ixNote = MakeFS(root, 10, C_GREY, "CENTER")
    PD.ixNote:SetText(L["营地档位对照表 →「营地系统」"])

    local y = 0
    for gi = 1, 4 do
        local head = PD.ixHeads[gi]
        head:ClearAllPoints()
        head:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -y)
        y = y + PD.IX_HEAD_H
        local cards = byGroup[gi]
        local rows = math.ceil(#cards / PD.IX_COLS)
        for k, c in ipairs(cards) do
            local row = math.floor((k - 1) / PD.IX_COLS)
            local col = (k - 1) % PD.IX_COLS
            c:ClearAllPoints()
            c:SetPoint("TOPLEFT", root, "TOPLEFT",
                       col * (PD.IX_COLW + PD.IX_GAP), -(y + row * (PD.IX_CARD_H + PD.IX_ROWW_GAP)))
            c:SetSize(PD.IX_COLW, PD.IX_CARD_H)
        end
        if gi == 4 then
            PD.ixNote:ClearAllPoints()
            PD.ixNote:SetPoint("LEFT", root, "LEFT",
                               PD.IX_COLW + PD.IX_GAP + 8, -(y + math.floor(PD.IX_CARD_H / 2)))
        end
        y = y + rows * PD.IX_CARD_H + (rows - 1) * PD.IX_ROWW_GAP + PD.IX_GROUP_GAP
    end
    PD.ixGridH = y
    root:SetHeight(y)
    root:Hide()
end

function PD.placeIndexGrid(y)
    PD.ixRoot:ClearAllPoints()
    PD.ixRoot:SetPoint("TOPLEFT", PD.child, "TOPLEFT", PD.LIST_PAD, -y)
    PD.ixRoot:SetHeight(PD.ixGridH or 10)
    PD.ixRoot:Show()
    PD.PaintIndexCards()
end

local IX_EDGE_NORM_A = 0.10
function PD.PaintIndexCards()
    local learned = PD.ProfLearned()
    for _, c in ipairs(PD.ixCards or {}) do
        local lv = c.__slug and learned[c.__slug] or nil
        local key = lv and (lv.cur .. "/" .. lv.max) or ""
        if c.__ixKey ~= key then
            c.__ixKey = key
            c.__ixLearned = lv and true or false
            local r, g, b = PD.NavAccent()
            if lv then
                c.name:SetTextColor(r, g, b, 1)
                c.lv:SetText(format("%d/%d", lv.cur, lv.max))
                c.lv:SetTextColor(r, g, b, 1)
                c.lv:Show()
            else
                c.name:SetTextColor(Unpack(C_TEXT))
                c.lv:Hide()
            end
            if c.__ixBorder then
                for _, t in ipairs(c.__ixBorder) do
                    if lv then
                        t:SetVertexColor(r, g, b)
                        t:SetAlpha(1)
                    else
                        t:SetVertexColor(1, 1, 1)
                        t:SetAlpha(IX_EDGE_NORM_A)
                    end
                end
            elseif c.SetBackdropBorderColor then
                if lv then
                    c:SetBackdropBorderColor(r, g, b, 1)
                else
                    c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
                end
            end
        end
    end
end

function PD.MakeCard(f)
    local c = CreateFrame("Frame", nil, f, "BackdropTemplate")
    if ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L1, "both", true, 1)
    else
        c:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
    end
    return c
end

function PD.Build(page)
    if PD.built or PD.building then return end
    PD.building = true
    PD.rows, PD.toolBtns, PD.setToggles = {}, {}, {}
    PD.perkOpen, PD.__pendRows = {}, {}
    ns.PhasedStart(26, coroutine.create(function()
    PD.page = page
    if not PD.trFac then
        if UnitFactionGroup and UnitFactionGroup("player") == "Horde" then
            PD.trFac = "H"
        else
            PD.trFac = "A"
        end
    end
    page:HookScript("OnHide", function() PD.HideVendorPick() end)
    PD.navKey = {}
    coroutine.yield()

    PD.navCard = PD.MakeCard(page)
    PD.navCard:SetPoint("TOPLEFT", page, "TOPLEFT", PD.CARD_INSET, -PD.CARD_TOP)
    PD.navCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT",
                        PD.CARD_NAV_R, PD.CARD_INSET)
    PD.listCard = PD.MakeCard(page)
    PD.navLabelHost = CreateFrame("Frame", nil, page)
    do
        local ok, lv = pcall(PD.navCard.GetFrameLevel, PD.navCard)
        PD.navLabelHost:SetFrameLevel((ok and type(lv) == "number" and lv or 0) + 2)
    end
    coroutine.yield()

    PD.nav = {}
    local navY = 0
    local function navEntry(key, text, icon)
        local bt = NewButton(page, text, PD.NAV_W, PD.NAV_ITEM_H, PD.NAV_FS)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", PD.NAV_X, -(PD.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + PD.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        MakeOutline(bt, 1, 0.82, 0)
        SetOutline(bt, false, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt.__name = text
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetSize(PD.NAV_ICON, PD.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        SetIcon(bt.__icon, icon)
        bt.__lv = MakeFS(bt, PD.NAV_LV_FS, C_GREY, "RIGHT")
        bt.__lv:SetPoint("RIGHT", bt, "RIGHT", -6, 0)
        bt.__lv:Hide()
        bt:SetScript("OnClick", function() PD.Show(key) end)
        PD.nav[#PD.nav + 1] = bt
        PD.navKey[key] = bt
        navY = navY + PD.NAV_ITEM_H + PD.NAV_GAP
        return bt
    end

    PD.navOrder = {}
    for _, g in ipairs({ { kind = "primary", label = L["主专业"] },
                         { kind = "secondary", label = L["次专业"] },
                         { kind = "system", label = L["营地系统"] },
                         { kind = "crates", label = L["声望"] } }) do
        local list = {}
        for _, slug in ipairs(D.order or {}) do
            local p = D.pro[slug]
            if p and p.kind == g.kind then list[#list + 1] = slug end
        end
        if #list > 0 then
            navY = navY + 4
            local lab = MakeFS(PD.navLabelHost, 11, C_GREY, "LEFT")
            lab:SetPoint("TOPLEFT", page, "TOPLEFT", PD.NAV_X + 5,
                         -(PD.NAV_TOP + navY + 6))
            lab:SetText(g.label)
            navY = navY + PD.NAV_GROUP_H
            for _, slug in ipairs(list) do
                local p = D.pro[slug]
                navEntry(slug, p.name or slug, p.icon)
                PD.navOrder[#PD.navOrder + 1] = slug
            end
        end
    end

    coroutine.yield()
    ns.hui.OnThemeChange(function() if PD.built then pcall(PD.PickNav) end end)

    PD.subBtns = {}
    for _, def in ipairs(DG.PROF_SUBTABS) do
        local bt = NewButton(page, def.text, PD.SUB_W, PD.SUB_H, 13)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt:Hide()
        bt:SetScript("OnClick", function() PD.SetTab(def.key) end)
        PD.subBtns[def.key] = bt
    end
    coroutine.yield()

    PD.trFacBtns = {}
    for i = 1, 2 do
        local k = (i == 1) and "A" or "H"
        local bt = NewButton(page, k == "A" and L["联盟"] or L["部落"], 64, PD.SUB_H, 13)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        local bfs = bt:GetFontString()
        if bfs then
            bfs:ClearAllPoints()
            bfs:SetPoint("LEFT", bt, "LEFT", 26, 0)
            bfs:SetJustifyH("LEFT")
            if k == "A" then
                bfs:SetTextColor(0.40, 0.62, 1.00, 1)
            else
                bfs:SetTextColor(1.00, 0.36, 0.26, 1)
            end
        end
        local bic = bt:CreateTexture(nil, "OVERLAY")
        bic:SetTexture(k == "A" and PD.FAC_ICON.a or PD.FAC_ICON.h)
        bic:SetSize(16, 16)
        bic:SetPoint("LEFT", bt, "LEFT", 7, 0)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bic) end
        bt:Hide()
        bt:SetScript("OnClick", function()
            if PD.trFac ~= k then
                PD.trFac = k
                PD.RequestRender()
                ns.PlaySound(1)
            end
        end)
        PD.trFacBtns[k] = bt
    end
    coroutine.yield()

    local gear = NewButton(page, "", PD.SUB_H, PD.SUB_H, 13)
    MakeOutline(gear, 1, 0.82, 0)
    gear.__huiKeepTextColor = true
    gear.__icon = gear:CreateTexture(nil, "ARTWORK")
    gear.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(gear.__icon) end
    gear.__icon:SetSize(14, 14)
    gear.__icon:SetPoint("CENTER", gear, "CENTER", 0, 0)
    SetIcon(gear.__icon, ns.SET_ICON)
    gear:SetPoint("TOPRIGHT", page, "TOPLEFT",
                  PD.RIGHT_X + PD.RIGHT_W - PD.LIST_PAD, -PD.SUB_Y)
    gear:SetScript("OnClick", function()
        PD.setOpen = not PD.setOpen
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    PD.setGear = gear
    coroutine.yield()

    PD.setToggles = {}
    PD.toolBtns = {}

    for i = 1, PD.TOOL_MAX do
        local bt = NewButton(page, "", PD.TOOL_W, PD.TOOL_H, 12)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            if self.__key and PD.onTool then PD.onTool(self.__key) end
            ns.PlaySound(1)
        end)
        PD.toolBtns[i] = bt
    end
    coroutine.yield()

    PD.LV_TILE_H, PD.LV_TILE_GAP = 38, 8

    local hudBtn = NewButton(page, "", 120, PD.SUB_H, 13)
    MakeOutline(hudBtn, 1, 0.82, 0)
    hudBtn.__huiKeepTextColor = true
    hudBtn:Hide()
    hudBtn:SetPoint("TOPRIGHT", page, "TOPRIGHT",
                    -(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP + PD.LV_TILE_H + 8))
    PD.hudBtn = hudBtn
    coroutine.yield()

    local impBtn = NewButton(page, L["一键导入购物清单"], 110, PD.SUB_H, 13)
    MakeOutline(impBtn, 1, 0.82, 0)
    impBtn.__huiKeepTextColor = true
    impBtn:Hide()
    impBtn:SetPoint("TOPRIGHT", hudBtn, "TOPLEFT", -8, 0)
    PD.impBtn = impBtn
    coroutine.yield()
    PD.lvTiles = {}
    for _, td in ipairs({
        { key = "mode",   w = 200 },
        { key = "scheme", w = 150 },
        { key = "cost",   w = 250 },
        { key = "target", w = 150 },
        { key = "snap",   w = 0 },
    }) do
        local tf = CreateFrame("Button", nil, page, "BackdropTemplate")
        tf:SetSize(td.w, PD.LV_TILE_H)
        local _, bord = ns.hui.BuildRoundedBG(tf, 6, ns.hui.layer.L2, "both", true, 1)
        tf.__border = bord or {}
        if ns.hui and ns.hui.BuildCapsule then
            tf.__hov = ns.hui.BuildCapsule(tf, 8, ns.hui.layer.L4, 1, 2) or {}
            for _, t in ipairs(tf.__hov) do t:Hide() end
        end
        tf:Hide()
        tf.label = MakeFS(tf, 11, C_GREY, "LEFT")
        tf.label:SetPoint("TOPLEFT", tf, "TOPLEFT", 10, -6)
        tf.val = MakeFS(tf, 14, C_WHITE, "LEFT")
        tf.val:SetPoint("BOTTOMLEFT", tf, "BOTTOMLEFT", 10, 6)
        tf:EnableMouseWheel(true)
        tf:SetScript("OnMouseWheel", function(self, delta)
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        PD.lvTiles[td.key] = tf
    end
    coroutine.yield()
    function PD.PaintTileBorder(f, c)
        for _, tex in ipairs(f.__border or {}) do
            if tex.__huiBorderStrip then
                tex:SetColorTexture(c[1], c[2], c[3], 1)
                tex:SetAlpha(c[4] or 1)
            else
                tex:SetVertexColor(c[1], c[2], c[3])
                tex:SetAlpha(c[4] or 1)
            end
        end
    end
    PD.lvTiles.mode:SetScript("OnClick", function()
        local on = not PD.Setting("autoRoute")
        ProfDB().autoRoute = on
        if not on and RA then RA.Invalidate() end
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    PD.lvTiles.scheme:SetScript("OnClick", function()
        local order = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
        local cur = PD.SettingRaw("autoScheme")
        local n = #order
        local ni = 1
        for i, k in ipairs(order) do
            if k == cur then ni = (i % n) + 1 break end
        end
        ProfDB().autoScheme = order[ni]
        if RA then RA.Invalidate() end
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    do
        local tf = PD.lvTiles.target
        local eb = CreateFrame("EditBox", nil, tf, "BackdropTemplate")
        local _, ebBord = ns.hui.BuildRoundedBG(eb, 6, ns.hui.layer.L3, "both", true, 1)
        eb.__border = ebBord or {}
        PD.PaintTileBorder(eb, { 1, 0.82, 0, 0.9 })
        eb:SetSize(64, 20)
        eb:SetPoint("BOTTOMLEFT", tf, "BOTTOMLEFT", 9, 5)
        eb:SetFont(ns.FONT, 13, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        eb:SetTextColor(1, 0.82, 0)
        eb:SetJustifyH("CENTER")
        eb:SetAutoFocus(false)
        eb:SetTextInsets(4, 4, 0, 0)
        eb:SetNumeric(true)
        eb:Hide()
        tf.eb = eb
        local function CloseTarget()
            PD.tgtEditing = nil
            eb:Hide()
            tf.val:Show()
        end
        local function ApplyTarget()
            if not PD.cur or not PD.tgtEditing then CloseTarget() return end
            local v = tonumber(eb:GetText()) or 300
            v = math.max(1, math.min(300, math.floor(v)))
            local db = ProfDB()
            db.lvTarget = db.lvTarget or {}
            local old = tonumber(db.lvTarget[PD.cur]) or 300
            CloseTarget()
            if old == v then return end
            if v >= 300 then db.lvTarget[PD.cur] = nil else db.lvTarget[PD.cur] = v end
            if RA then RA.Invalidate() end
            local _pf = ns.ProfFollow
            if _pf and _pf.RefreshRoute then pcall(_pf.RefreshRoute, PD.cur) end
            PD.RequestRender()
        end
        local cancelled = nil
        eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
        eb:SetScript("OnEscapePressed", function(self)
            cancelled = true
            CloseTarget()
            self:ClearFocus()
        end)
        eb:SetScript("OnEditFocusLost", function()
            if cancelled then cancelled = nil return end
            ApplyTarget()
        end)
        tf:SetScript("OnClick", function()
            if PD.tgtEditing then return end
            local v = PD.LvTarget()
            eb:SetText(v >= 300 and "" or tostring(v))
            PD.tgtEditing = true
            tf.val:Hide()
            eb:Show()
            eb:SetFocus()
            ns.PlaySound(1)
        end)
    end
    coroutine.yield()

    local sb = CreateFrame("Frame", nil, page)
    sb:SetSize(PD.SEARCH_W, PD.TOOL_H)
    sb:Hide()
    sb.label = MakeFS(sb, 12, C_GREY, "LEFT")
    sb.label:SetText(L["搜索"])
    sb.label:SetPoint("LEFT", sb, "LEFT", 0, 0)
    local seb = CreateFrame("EditBox", nil, sb, "BackdropTemplate")
    local _, sebBord = ns.hui.BuildRoundedBG(seb, 6, ns.hui.layer.L2, "both", true, 1)
    seb.__border = sebBord or {}
    PD.PaintTileBorder(seb, { 1, 1, 1, 0.10 })
    seb:SetSize(PD.SEARCH_EB_W, PD.TOOL_H)
    seb:SetPoint("RIGHT", sb, "RIGHT", 0, 0)
    sb.label:ClearAllPoints()
    sb.label:SetPoint("RIGHT", seb, "LEFT", -8, 0)
    seb:SetFont(ns.FONT, 12, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
    seb:SetTextColor(1, 1, 1, 1)
    seb:SetJustifyH("LEFT")
    seb:SetAutoFocus(false)
    seb:SetTextInsets(5, 5, 0, 0)
    seb:SetMaxLetters(40)
    seb.ph = MakeFS(seb, 11, C_GREY, "LEFT")
    seb.ph:SetText(L["配方名 / 材料名"])
    seb.ph:SetPoint("LEFT", seb, "LEFT", 6, 0)
    seb.ph:Hide()
    local function SyncPh()
        local t = seb:GetText()
        if (t == nil or t == "") and not seb:HasFocus() then
            seb.ph:Show()
        else
            seb.ph:Hide()
        end
    end
    seb:SetScript("OnTextChanged", function(self)
        SyncPh()
        local t = string.lower(tostring(self:GetText() or ""))
        if t == (PD.searchQ or "") then return end
        PD.searchQ = t
        PD.RequestRender()
    end)
    seb:SetScript("OnEscapePressed", function(self)
        if self:GetText() ~= "" then self:SetText("") end
        self:ClearFocus()
        SyncPh()
    end)
    seb:SetScript("OnEnterPressed", function(self)
        self:ClearFocus()
        SyncPh()
        ns.PlaySound(1)
    end)
    seb:SetScript("OnEditFocusGained", function() seb.ph:Hide() end)
    seb:SetScript("OnEditFocusLost", function() SyncPh() end)
    sb.eb = seb
    PD.searchBox = sb
    coroutine.yield()

    local divider = page:CreateTexture(nil, "BORDER")
    divider:SetColorTexture(1, 1, 1, 0.12)
    divider:SetWidth(1)
    divider:Hide()
    PD.divider = divider
    coroutine.yield()

    local scroll = CreateFrame("ScrollFrame", nil, page)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(PD.RIGHT_W, 10)
    scroll:SetScrollChild(child)
    PD.scroll, PD.child = scroll, child
    coroutine.yield()

    local track = CreateFrame("Frame", nil, page, "BackdropTemplate")
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
    track:SetWidth(9)
    track:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", -1, -2)
    track:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", -1, 2)
    track:SetFrameLevel((scroll:GetFrameLevel() or 0) + 10)
    track:Hide()
    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(6)
    thumb:EnableMouse(true)
    local tp = nil
    local tx = nil
    if ns.hui and ns.hui.BuildCapsule then
        tp = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
    else
        tx = thumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
    end
    thumb:SetScript("OnEnter", function()
        if tp then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(tp) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    thumb:SetScript("OnLeave", function()
        if tp then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(tp) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    thumb:SetPoint("TOP", track, "TOP", 0, -1)
    coroutine.yield()
    function PD.UpdateVScroll()
        local sc, ch = PD.scroll, PD.child
        if not (sc and ch) then return end
        if PD.setOpen then track:Hide() return end
        if PD.lvSplit then
            if not PD.divider then track:Hide() return end
            track:ClearAllPoints()
            track:SetPoint("TOPLEFT", PD.divider, "TOPLEFT", -4, -2)
            track:SetPoint("BOTTOMLEFT", PD.divider, "BOTTOMLEFT", -4, 2)
        elseif PD.tab == "recipe" then
            track:ClearAllPoints()
            track:SetPoint("TOPRIGHT", sc, "TOPRIGHT", -1, -2)
            track:SetPoint("BOTTOMRIGHT", sc, "BOTTOMRIGHT", -1, 2)
        else
            track:Hide()
            return
        end
        local viewH = sc:GetHeight()
        local contentH = ch:GetHeight()
        if contentH <= viewH + 2 or viewH <= 0 then track:Hide() return end
        track:Show()
        local trackH = track:GetHeight() - 2
        local maxScroll = contentH - viewH
        local vpos = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
        if type(vpos) ~= "number" then vpos = 0 end
        local frac = math.min(1, math.max(0, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    end
    scroll:SetScript("OnVerticalScroll", function()
        PD.UpdateVScroll()
        if PD.CullRows then PD.CullRows() end
    end)
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = PD.scroll:GetVerticalScroll()
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = PD.child:GetHeight() - PD.scroll:GetHeight()
            PD.scroll:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    coroutine.yield()

    local hlAcc = 0
    child:SetScript("OnUpdate", function(_, el)
        hlAcc = hlAcc + el
        if hlAcc < 0.1 then return end
        hlAcc = 0
        PD.SyncHover()
    end)
    coroutine.yield()

    PD.BuildBonusTable(child)
    coroutine.yield()
    PD.BuildTrainerBoard(child)
    coroutine.yield()

    for i = 1, PD.SETTING_TOG_MAX do
        local tg = CreateFrame("CheckButton", nil, child)
        tg:SetSize(36, 20)
        tg:EnableMouse(true)
        ns.hui.ReskinToggle(tg)
        tg:SetScript("OnClick", function(self)
            if self.__key then
                ProfDB()[self.__key] = not PD.Setting(self.__key)
                self:SetChecked(PD.Setting(self.__key))
                if string.sub(self.__key, 1, 4) == "auto" and RA then
                    RA.Invalidate()
                end
            end
            PD.RequestRender()
            ns.PlaySound(1)
        end)
        PD.setToggles[i] = tg
    end
    coroutine.yield()

    PD.setHelps = {}
    for i = 1, PD.SETTING_TOG_MAX do
        local hp = CreateFrame("Button", nil, child)
        hp:SetSize(16, 16)
        hp.text = MakeFS(hp, 12, C_GOLD, "CENTER")
        hp.text:SetAllPoints()
        hp.text:SetText("?")
        hp:SetScript("OnEnter", function(self)
            local ln = self.__tip
            if not ln then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, t in ipairs(ln) do
                if t[1] and t[1] ~= "" then
                    GameTooltip:AddLine(t[1], t[2] or 1, t[3] or 1, t[4] or 1, true)
                end
            end
            GameTooltip:Show()
        end)
        hp:SetScript("OnLeave", function() GameTooltip:Hide() end)
        hp:EnableMouseWheel(true)
        hp:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        hp:Hide()
        PD.setHelps[i] = hp
    end
    coroutine.yield()

    PD.bonusTitleNote = MakeFS(child, 14, C_GREY, "RIGHT")
    PD.bonusTitleNote:SetText(
        L["营地增益不与同类职业增益叠加、效果略低于职业版（如王者祝福 10% → 营地 8%）。"])
    PD.bonusTitleNote:Hide()
    coroutine.yield()

    PD.BuildIndexGrid(child)
    coroutine.yield()

    PD.secCards = {}
    for i = 1, PD.SEC_CARD_MAX do
        local c = CreateFrame("Frame", nil, child)
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
        c:Hide()
        PD.secCards[i] = c
    end
    coroutine.yield()
    PD.secGoldCards = {}
    for i = 1, PD.SEC_CARD_MAX do
        local c = CreateFrame("Frame", nil, child)
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L3, "both", true, 1)
        c:Hide()
        PD.secGoldCards[i] = c
    end
    coroutine.yield()

    PD.ver = MakeFS(page, 11, C_GREY, "LEFT")
    PD.ver:SetPoint("BOTTOMLEFT", page, "BOTTOMLEFT", 10, 4)
    PD.built = true
    PD.building = false
    if PD.wantOpen then
        PD.wantOpen = nil
        PD.EnsureCur()
        PD.RequestRender()
    end
    PD.ver:SetText(format(L["专业数据 build %s · %s"],
                          tostring(D.build or "?"), tostring(D.updated or "?")))
    end))
end

local NAV_SKILL_SLUG = {
    [171] = "alchemy",     [164] = "blacksmithing", [333] = "enchanting",
    [202] = "engineering", [165] = "leatherworking", [197] = "tailoring",
    [186] = "mining",      [182] = "herbalism",     [393] = "skinning",
    [185] = "cooking",     [356] = "fishing",       [129] = "first-aid",
}

function PD.ProfLearned()
    local out = {}
    if type(GetProfessions) ~= "function" then return out end
    local ok, a, b, c, d, e, f = pcall(GetProfessions)
    if not ok then return out end
    local slots = { a, b, c, d, e, f }
    for i = 1, 6 do
        local idx = slots[i]
        if idx then
            local oki, _, _, cur, mx, _, _, sid = pcall(GetProfessionInfo, idx)
            local slug = NAV_SKILL_SLUG[sid]
            if oki and slug and cur and mx then
                out[slug] = { cur = tonumber(cur) or 0, max = tonumber(mx) or 0 }
            end
        end
    end
    return out
end

local function NavAccent()
    local a = ns.hui and ns.hui.ACCENT
    if a then return a[1], a[2], a[3] end
    return 0x46 / 255, 0xbf / 255, 0x72 / 255
end
PD.NavAccent = NavAccent

function PD.PickNav()
    local learned = PD.ProfLearned()
    local function paint(bt, sel, lv)
        local key = (sel and "1" or "0") .. "|" .. (lv and (lv.cur .. "/" .. lv.max) or "")
        if bt.__pnKey == key then return end
        bt.__pnKey = key
        SetOutline(bt, sel, 1, 0.82, 0)
        if lv then
            if sel then
                bt:GetFontString():SetTextColor(Unpack(C_GOLD))
            else
                bt:GetFontString():SetTextColor(NavAccent())
            end
            bt.__lv:SetText(format("%d/%d", lv.cur, lv.max))
            bt.__lv:SetTextColor(NavAccent())
            bt.__lv:Show()
        else
            bt.__lv:Hide()
            bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_DIM))
        end
        bt.__icon:SetDesaturated(not sel and not lv)
    end
    for _, slug in ipairs(PD.navOrder or {}) do
        local bt = PD.navKey[slug]
        if bt then paint(bt, slug == PD.cur, learned[slug]) end
    end
    local nbt = PD.navKey and PD.navKey.crates
    if nbt and not nbt.__itemIconDone and CD and CD.crates and CD.crates[1] then
        local tex = DG.ItemIcon(CD.crates[1].id)
        if tex and tex ~= FALLBACK_ICON then
            SetIcon(nbt.__icon, tex)
            nbt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            nbt.__itemIconDone = true
        end
    end
end

function PD.TabsFor(slug)
    if slug == "__index" then return { "overview" } end
    if slug == "crates" then return { "crate", "writ" } end
    local p = D.pro[slug]
    local out = { "overview" }
    if slug == "poisons" then out = {} end
    if not p then return out end
    local TRD = ns.ProfTrainers and ns.ProfTrainers[slug]
    if TRD and TRD.list and #TRD.list > 0 then out[#out + 1] = "trainer" end
    local r = RGet(slug)
    if r and ((r.rows and #r.rows > 0) or (r.enchants and #r.enchants > 0)
              or (r.crafted and #r.crafted > 0)) then
        out[#out + 1] = "recipe"
    end
    if GA and (GA[slug] or (slug == "fishing" and GA.fishing)) then out[#out + 1] = "gather" end
    if (LV and LV[slug]) or (PD.GATHER_SLUGS and PD.GATHER_SLUGS[slug]) then out[#out + 1] = "leveling" end
    return out
end

function PD.PickTabs()
    local tabs = PD.TabsFor(PD.cur)
    PD.avail = {}
    for _, t in ipairs(tabs) do PD.avail[t] = true end
    if not PD.avail[PD.tab] then PD.tab = tabs[1] or "overview" end
    local shown = 0
    for _, def in ipairs(DG.PROF_SUBTABS) do
        local bt = PD.subBtns[def.key]
        local on = PD.avail[def.key] and true or false
        local txt = def.text
        local sel = (not PD.setOpen) and (def.key == PD.tab)
        local key = (on and "1" or "0") .. "|" .. shown .. "|"
                    .. (sel and "1" or "0") .. "|" .. txt
        if bt.__ptKey ~= key then
            bt.__ptKey = key
            bt:SetShown(on)
            if on then
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                            PD.RIGHT_X + shown * PD.SUB_STEP, -PD.SUB_Y)
                bt:SetText(def.text)
                SetOutline(bt, sel, 1, 0.82, 0)
                bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_GREY))
            end
        end
        if on then shown = shown + 1 end
    end
    if PD.setGear then
        local gon = (PD.tab == "leveling")
        if PD.setGear.__shown ~= gon then
            PD.setGear.__shown = gon
            PD.setGear:SetShown(gon)
        end
        if gon then
            SetOutline(PD.setGear, PD.setOpen and true or false, 1, 0.82, 0)
            local gc = PD.setOpen and ns.SET_ICON_ON or ns.SET_ICON_IDLE
            PD.setGear.__icon:SetVertexColor(gc[1], gc[2], gc[3])
        end
    end
    if PD.trFacBtns then
        local ton = (PD.tab == "trainer") and (not PD.setOpen)
        for _, k in ipairs({ "H", "A" }) do
            local bt = PD.trFacBtns[k]
            local sel = (PD.trFac == k)
            local key = (ton and "1" or "0") .. "|" .. (sel and "1" or "0")
            if bt.__trKey ~= key then
                bt.__trKey = key
                bt:SetShown(ton)
                if ton then
                    bt:ClearAllPoints()
                    local kx = (k == "H") and 0 or 1
                    bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                                PD.RIGHT_X + PD.RIGHT_W - PD.LIST_PAD - 64 - kx * 72,
                                -PD.SUB_Y)
                    SetOutline(bt, sel, 1, 0.82, 0)
                    local bf = bt:GetFontString()
                    if bf then
                        if sel then
                            if k == "A" then
                                bf:SetTextColor(0.40, 0.62, 1.00, 1)
                            else
                                bf:SetTextColor(1.00, 0.36, 0.26, 1)
                            end
                        else
                            bf:SetTextColor(0.55, 0.55, 0.55, 1)
                        end
                    end
                end
            end
        end
    end
    local pf = ns.ProfFollow
    if pf and pf.PaintButton and PD.hudBtn then
        if PD.tab == "leveling" and not PD.setOpen then
            pcall(pf.PaintButton, PD.hudBtn, PD.cur)
        else
            PD.hudBtn:Hide()
        end
    end
    if pf and pf.PaintImportBtn and PD.impBtn then
        pcall(pf.PaintImportBtn, PD.impBtn, PD.cur)
    end
    if PD.impBtn then
        local wantImp = PD.tab == "leveling" and PD.autoPage == "shop"
                        and (not PD.setOpen) and PD.cur ~= nil and PD.cur ~= "__index"
                        and LV[PD.cur] ~= nil and LV[PD.cur].steps ~= nil
        PD.impBtn:SetShown(wantImp and true or false)
    end
end

PD.TOOL_MIN_W, PD.TOOL_MAX_W = 56, 200
PD.TOOL_PADX = 18

function PD.ToolSize(text)
    local need = PD.TextW(text, 12) + PD.TOOL_PADX
    local w = math.ceil(math.max(PD.TOOL_MIN_W, math.min(PD.TOOL_MAX_W, need)))
    local shown = text
    if need > PD.TOOL_MAX_W then shown = PD.Fit(text, 12, PD.TOOL_MAX_W - PD.TOOL_PADX) end
    return w, shown
end

function PD.PaintTool(list, handler, yoff)
    PD.onTool = handler
    list = list or {}
    yoff = yoff or 0
    local _T0, _MK = PD.__pfT0, PD.__pfMark
    local _AD = PD.__pfAdd
    local n = math.min(#list, PD.TOOL_MAX)
    local x, row = 0, 0
    for i = 1, PD.TOOL_MAX do
        local bt = PD.toolBtns[i]
        local def = (i <= n) and list[i] or nil
        if def then
            local w, text
            if def.plain then
                w = math.ceil(PD.TextW(def.text, 12)) + 6
                text = def.text
            else
                w, text = PD.ToolSize(def.text)
            end
            local lim = PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)
            if x > 0 and x + w > lim then row = row + 1; x = 0 end
            local key = "1|" .. w .. "|" .. x .. "|" .. row .. "|"
                        .. tostring(def.on) .. "|" .. text
            if bt.__ptk ~= key then
                bt.__ptk = key
                local _m0 = _T0 and _T0()
                local _g0 = _m0
                if _AD then _AD("闸-已显", bt:IsShown() and 1 or 0) end
                bt:SetSize(w, PD.TOOL_H)
                if _MK then _MK("闸-尺寸", _m0) end
                _m0 = _T0 and _T0()
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                            -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))
                if _MK then _MK("闸-锚点", _m0) end
                _m0 = _T0 and _T0()
                bt:SetText(text)
                if def.plain then
                    bt:EnableMouse(false)
                    SetOutline(bt, false, 1, 0.82, 0)
                    bt:GetFontString():SetTextColor(Unpack(C_WHITE))
                else
                    bt:EnableMouse(true)
                    SetOutline(bt, def.on and true or false, 1, 0.82, 0)
                    bt:GetFontString():SetTextColor(Unpack(def.on and C_GOLD or C_GREY))
                end
                if _MK then _MK("闸-文本", _m0) end
                _m0 = _T0 and _T0()
                bt:Show()
                if _MK then _MK("闸-显示", _m0) end
                if _MK then _MK("闸-合计", _g0) end
            end
            bt.__key = def.key
            if def.plain then
                local wz = PD.WarnChip(bt, true)
                if def.warn and def.warn[1] then
                    wz:ClearAllPoints()
                    wz:SetPoint("LEFT", bt, "RIGHT", 2, 0)
                    wz.__tipLines = def.warn
                    wz:Show()
                else
                    wz:Hide(); wz.__tipLines = nil
                end
            elseif bt.__warn then
                bt.__warn:Hide(); bt.__warn.__tipLines = nil
            end
            x = x + w + (def.gap or PD.TOOL_GAP)
        else
            if bt.__ptk ~= "0" then bt.__ptk = "0"; bt:Hide() end
            bt.__key = nil
        end
    end
    local rows = (n > 0) and (row + 1) or 0
    PD.toolRows = rows
    return (rows > 0) and (rows * (PD.TOOL_H + PD.TOOL_GAP) + PD.TOOL_BODY_GAP) or 0
end

function PD.TipTile(tf, lines)
    tf:SetScript("OnEnter", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Show() end end
        GameTooltip:SetOwner(tf, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        for _, ln in ipairs(lines) do
            if ln[1] and ln[1] ~= "" then
                GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
            end
        end
        GameTooltip:Show()
    end)
    tf:SetScript("OnLeave", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Hide() end end
        GameTooltip:Hide()
    end)
end

function PD.PaintGatherTiles()
    local tiles = PD.lvTiles
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "snap", "target", "scheme", "cost", "mode" }) do tiles[k]:Hide() end
        return 0
    end
    tiles.snap:Hide()
    tiles.mode:SetScript("OnClick", nil)
    tiles.scheme:SetScript("OnClick", nil)
    tiles.cost:SetScript("OnClick", nil)
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil
    local g = GA and (GA[PD.cur] or (PD.cur == "fishing" and GA.fishing))
    local prog = "-"
    if g and #g > 0 and curLv then
        for i, t in ipairs(g) do
            local lo, hi
            if PD.cur == "fishing" then
                lo = t[2]
                hi = (g[i + 1] and g[i + 1][2] or lo + 1) - 1
                if hi < lo then hi = lo end
            elseif PD.cur == "skinning" then
                lo, hi = t[1][1], t[1][2]
            else
                lo = t[2]
                hi = (g[i + 1] and g[i + 1][2] or 301) - 1
                if hi < lo then hi = lo end
            end
            if curLv >= lo and curLv <= hi then
                prog = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo)
                break
            end
        end
    end
    tiles.mode.label:SetText(L["当前技能"])
    tiles.mode.val:SetText(curLv and tostring(curLv) or L["未学"])
    PD.TipTile(tiles.mode, { { L["读取角色当前的专业技能值"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
    tiles.scheme.label:SetText(L["路线进度"])
    local smelt = PD.GatherMode(PD.cur) == "smelt"
    if smelt and curLv then
        for i, t in ipairs(SMELT_TBL) do
            local lo = t[2]
            local hi = (SMELT_TBL[i + 1] and SMELT_TBL[i + 1][2] or 301) - 1
            if hi < lo then hi = lo end
            if curLv >= lo and curLv <= hi then
                prog = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo)
                break
            end
        end
    end
    tiles.scheme.val:SetText((PD.cur == "mining") and
        ((smelt and L["熔炼"] or L["采集"]) .. " " .. prog) or prog)
    if PD.cur == "mining" then
        tiles.scheme:SetScript("OnClick", function()
            ProfDB().gatherMode = smelt and "gather" or "smelt"
            PD.RequestRender()
            ns.PlaySound(1)
        end)
    else
        tiles.scheme:SetScript("OnClick", nil)
    end
    PD.TipTile(tiles.scheme, (PD.cur == "mining") and {
        { L["点击切换：采集 ⇄ 熔炼"], 0.9, 0.78, 0.35 },
        { smelt and L["列表中绿色高亮行 = 当前技能可练的熔炼区间"]
            or L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 },
    } or { { L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.scheme, (PD.cur == "mining") and { 1, 0.82, 0, 0.55 } or { 1, 1, 1, 0.10 })
    tiles.cost.label:SetText(L["路线范围"])
    tiles.cost.val:SetText("1 - 300")
    PD.TipTile(tiles.cost, { { L["静态推荐路线（全程显示）：按资料整理的采集区间推进，不含价格与概率，无需价格插件"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.cost, { 1, 1, 1, 0.10 })
    local tw = math.floor((PD.RIGHT_W - PD.LIST_PAD - 4 * PD.LV_TILE_GAP) / 5)
    local x = PD.RIGHT_X
    for _, k in ipairs({ "mode", "scheme", "cost" }) do
        local tf = tiles[k]
        tf:SetWidth(tw)
        tf:ClearAllPoints()
        tf:SetPoint("TOPLEFT", PD.page, "TOPLEFT", x, -PD.BODY_TOP)
        x = x + tf:GetWidth() + PD.LV_TILE_GAP
        tf:Show()
    end
    return PD.LV_TILE_H + 8
end

function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    if PD.GATHER_SLUGS[PD.cur] then return PD.PaintGatherTiles() end
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "scheme", "cost", "target", "snap" }) do tiles[k]:Hide() end
        return 0
    end
    local s = PD.lvSummary or {}
    local v = PD.LvTarget()
    local auto = s.auto and true or false
    local warnAuto = s.autoSetting and not s.ahOK
    local fixedOnly = (PD.cur == "poisons")
    if fixedOnly then
        tiles.mode:SetScript("OnClick", nil)
    else
        tiles.mode:SetScript("OnClick", function()
            local on = not PD.Setting("autoRoute")
            ProfDB().autoRoute = on
            if not on and RA then RA.Invalidate() end
            PD.RequestRender()
            ns.PlaySound(1)
        end)
    end
    local snapSec, snapDays = s.snapshotAge, s.snapshotDays
    local TipOn = PD.TipTile
    if fixedOnly then
        tiles.mode.label:SetText(L["模式"])
        tiles.mode.val:SetText(L["固定路线"])
        tiles.mode.val:SetTextColor(Unpack(C_WHITE))
        PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
        TipOn(tiles.mode, { { L["固定路线：按资料整理的分段练法逐段冲技能"], 0.7, 0.7, 0.7 } })
    else
        tiles.mode.label:SetText(L["模式 · 点击切换"])
        tiles.mode.val:SetText(auto and L["自动计算"] or L["固定路线"])
        tiles.mode.val:SetTextColor(Unpack(auto and C_GOLD or C_WHITE))
        if warnAuto then
            PD.PaintTileBorder(tiles.mode, { 0.95, 0.75, 0.4, 0.9 })
        else
            PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
        end
        local modeLines = {
            { auto and L["自动计算：按当前路线方案逐点择优（在「路线方案」卡切换）"]
                   or L["固定路线：按资料整理的分段练法逐段冲技能"], 1, 0.82, 0 },
            { L["点击在固定 / 自动之间切换"], 0.7, 0.7, 0.7 },
        }
        if warnAuto then
            modeLines[#modeLines + 1] = { L["自动路线需要 Auctionator 的价格数据：请安装 Auctionator 并完成一次拍卖行扫描；当前显示固定路线。"],
                                          0.95, 0.75, 0.4 }
        end
        TipOn(tiles.mode, modeLines)
    end
    local sch = s.scheme or "cheapest"
    tiles.scheme.label:SetText(L["路线方案 · 点击切换"])
    tiles.scheme.val:SetText((RA and RA.SchemeLabel) and RA.SchemeLabel(sch) or L["最省钱"])
    tiles.scheme.val:SetTextColor(Unpack(C_WHITE))
    local schemeDesc = {
        cheapest = L["最省钱：材料价 + 图纸价按升点概率摊到每一点，选期望花费最低的配方"],
        matcost = L["材料成本：只按材料价选配方（不含图纸价）"],
        crafts = L["次数最少：优先升点率高的配方，同分取便宜"],
        optim = L["乐观计数：材料不看市价，一律按卖店价值折算；次数固定按做一次涨一点统计、只是下限；快变黄前 25 点的配方也纳入可选；带冷却的转化配方和资料未收录的材料不进路线"],
    }
    local schemeLines = {}
    local sorder = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    for _, sk in ipairs(sorder) do
        local curK = (sk == sch)
        schemeLines[#schemeLines + 1] = { schemeDesc[sk] or sk,
                                          curK and 1 or 0.62, curK and 0.82 or 0.62,
                                          curK and 0 or 0.62 }
    end
    TipOn(tiles.scheme, schemeLines)
    tiles.cost.label:SetText(format(L["1 → %d 预计总花费"], s.target or v))
    local costLines
    if s.scheme == "optim" then
        tiles.cost.val:SetText(RA.MoneyStr(s.total or 0, "copper"))
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { L["乐观计数：花费按卖店价值粗算，不是拍卖行行情"], 0.7, 0.7, 0.7 } }
    elseif s.priced and s.total then
        tiles.cost.val:SetText(RA.MoneyStr(s.total, "copper"))
        tiles.cost.val:SetTextColor(Unpack(C_GOLD))
        costLines = {}
        if s.recipes then
            costLines[#costLines + 1] = { format(L["配方 %d 种 · %d 次制作"], s.recipes, s.crafts or 0) }
            costLines[#costLines + 1] = { format(L["商人直售 %s · 图纸 %s"],
                                                 RA.MoneyStr(s.vendorTotal or 0),
                                                 RA.MoneyStr(s.formulasTotal or 0)), 0.7, 0.7, 0.7 }
        else
            costLines[#costLines + 1] = { format(L["材料 %d 种"], s.matsN or 0) }
        end
    else
        tiles.cost.val:SetText(L["—"])
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"], 0.7, 0.7, 0.7 } }
    end
    if (s.np or 0) > 0 then
        costLines[#costLines + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], s.np),
                                      0.95, 0.75, 0.4 }
    end
    TipOn(tiles.cost, costLines)
    tiles.target.label:SetText(L["目标等级 · 点击修改"])
    tiles.target.val:SetText(v >= 300 and L["全程"] or tostring(v))
    tiles.target.val:SetTextColor(Unpack(C_WHITE))
    TipOn(tiles.target, { { L["每专业独立记忆；300 = 全程。点击修改"], 0.7, 0.7, 0.7 } })
    tiles.snap.label:SetText(L["价格快照"])
    local atxt
    if s.scheme == "optim" then
        atxt = L["乐观计数 · 不依赖价格插件"]
    elseif s.priced and snapSec then
        if snapSec < 60 then
            atxt = L["刚刚Auctionator"]
        elseif snapSec < 90 * 60 then
            atxt = format(L["%d 分钟前Auctionator"], math.max(1, math.floor(snapSec / 60 + 0.5)))
        elseif snapSec < 24 * 3600 then
            atxt = format(L["%d 小时前Auctionator"], math.max(1, math.floor(snapSec / 3600 + 0.5)))
        else
            atxt = format(L["%d 天前Auctionator"], math.floor(snapSec / 86400 + 0.5))
        end
    elseif s.priced and snapDays then
        atxt = (snapDays <= 0) and L["今天Auctionator"]
               or format(L["%d 天前Auctionator"], snapDays)
    elseif s.priced then
        atxt = L["快照年龄未知Auctionator"]
    end
    if atxt then
        tiles.snap.val:SetText(atxt)
        tiles.snap.val:SetTextColor(0.55, 0.85, 0.6, 1)
        TipOn(tiles.snap, { { atxt, 0.7, 0.7, 0.7 } })
    else
        tiles.snap.val:SetText(L["未接入 Auctionator"])
        tiles.snap.val:SetTextColor(0.95, 0.75, 0.4, 1)
        TipOn(tiles.snap, { { L["安装 Auctionator 并完成一次拍卖行扫描后，这里显示价格快照年龄。"],
                              0.7, 0.7, 0.7 } })
    end
    local layout = { "mode", "scheme", "cost", "target", "snap" }
    if fixedOnly then
        layout = { "mode", "cost", "target", "snap" }
        tiles.scheme:Hide()
    end
    local n = #layout
    local usable = PD.RIGHT_W - PD.LIST_PAD - (n - 1) * PD.LV_TILE_GAP
    local tw = math.floor(usable / n)
    local x = PD.RIGHT_X
    for i, k in ipairs(layout) do
        local tf = tiles[k]
        if i == n then
            tf:SetWidth(usable - (n - 1) * tw)
        else
            tf:SetWidth(tw)
        end
        tf:ClearAllPoints()
        tf:SetPoint("TOPLEFT", PD.page, "TOPLEFT", x, -PD.BODY_TOP)
        x = x + tf:GetWidth() + PD.LV_TILE_GAP
        tf:Show()
    end
    return PD.LV_TILE_H + 8
end

function PD.Layout(toolH)
    local top = PD.BODY_TOP + (toolH or 0)
    local bot = PD.BODY_BOT
    PD.scroll:ClearAllPoints()
    PD.scroll:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X, -top)
    PD.scroll:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT", -PD.CARD_INSET, bot)
    PD.listCard:ClearAllPoints()
    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                         PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_TOP)
    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",
                         -PD.CARD_INSET, PD.CARD_INSET)
    PD.listCard:Show()
    local splitW
    if PD.lvSplit then splitW = PD.splitLW or PD.COL_LW
    elseif PD.gridSplit then splitW = PD.GRID_LW end
    if splitW and not PD.hideDivider then
        local gut = PD.lvSplit and PD.OV_GUT or PD.COL_GAP
        local mx = PD.RIGHT_X + PD.LIST_PAD + splitW + gut / 2
        PD.divider:ClearAllPoints()
        PD.divider:SetPoint("TOPLEFT", PD.page, "TOPLEFT", mx, -top)
        PD.divider:SetPoint("BOTTOMLEFT", PD.page, "BOTTOMLEFT", mx, bot)
        PD.divider:Show()
    else
        PD.divider:Hide()
    end
end

PD.SWEEP_AT = { 0.5, 1.5, 4, 9 }

function PD.SweepNames()
    if PD.sweeping or not PD.notReady then return end
    PD.sweeping = true
    local got = false
    for _, id in ipairs(PD.notReady) do
        local _, ok = DG.ItemName(id)
        if ok then got = true; break end
    end
    PD.notReady = nil
    if got then
        if RA then RA.Invalidate() end
        PD.RequestRender()
    end
    PD.sweeping = false
end

function PD.ScheduleSweep()
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    for _, t in ipairs(PD.SWEEP_AT) do
        C_Timer.After(t, function() PD.SweepNames() end)
    end
end

local C_ALLIANCE = { 0.40, 0.80, 0.94 }
local C_HORDE = { 1.00, 0.30, 0.25 }

function PD.RowsComprOverview(rows)
    local EM = ns.ExploreModule
    local tiers = EM and EM.BM_TIERS or nil
    PushGap(rows, 4, 1)
    if tiers and #tiers > 0 then
        PushHead(rows, L["提升技能"], 1)
        PushText(rows, L["未翻译的卷轴有四种，每一种需要的理解技能等级都更高。一种卷轴变灰之后就不会再提升技能：在技能到达它变灰的等级之前，换成下一种。"], 14)
        for _, t in ipairs(tiers) do
            local names = {}
            for _, id in ipairs(t.unc or {}) do
                names[#names + 1] = tostring(DG.ItemName(id) or "?")
            end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, fs = 14,
                text = t.tier,
                sub = table.concat(names, ", "),
                right = format("%s %d · %s %d", L["可破译于"], t.req or 0, L["变灰于"], t.gray or 0),
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
    local bundle = EM and EM.BM_BUNDLE or nil
    if bundle and #bundle > 0 then
        PushHead(rows, L["「一捆卷轴」开出率（17 捆样本）"], 1)
        for _, b in ipairs(bundle) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, it = { b[1] }, qItem = b[1], fs = 14,
                text = PD.ItemName(b[1]),
                right = format("%d%%", b[2] or 0),
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
end

function PD.RowsOverview(rows)
    local p = D.pro[PD.cur]
    if not p then return end
    if PD.cur == "comprehension" then
        PD.RowsComprOverview(rows)
        return
    end
    PushGap(rows, 4, 1)

    local miles = p.miles or {}
    local hasPerks = p.perks and #p.perks > 0
    if #miles > 0 or hasPerks then
        PushHead(rows, L["传承"], 1)
        for _, m in ipairs(miles) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, fs = 14, text = m[1] or "?",
                right = format(L["技能 %d · %d 点"], m[2] or 0, m[3] or 0),
            }
        end
        if #miles > 0 and hasPerks then PushGap(rows, 4, 1) end
        for _, pid in ipairs(p.perks or {}) do
            local pk = D.perks[pid]
            if pk then
                local open = PD.perkOpen[pid]
                local lines = { { pk[6] or "" } }
                if pk[8] then
                    for _, u in ipairs(pk[8]) do lines[#lines + 1] = { u, 0.9, 0.7, 0.4 } end
                end
                rows[#rows + 1] = {
                    kind = "row", col = 1, icon = pk[2], text = pk[1] or "?",
                    sub = (pk[6] or ""):sub(1, 90),
                    right = format(L["满级 %s"], tostring(pk[4])),
                    right2 = open and L["收起逐级文本"]
                                      or format(L["展开 %d 级文本"], #(pk[5] or {})),
                    lines = lines,
                    act = function()
                        PD.perkOpen[pid] = not PD.perkOpen[pid]
                        PD.RequestRender()
                    end,
                }
                if open and pk[5] then
                    for i, t in ipairs(pk[5]) do
                        rows[#rows + 1] = { kind = "text", col = 1,
                                            text = format("%d. %s", i, t), color = C_TEXT }
                    end
                end
            end
        end
        PushGap(rows, PD.OV_GUT, 1)
    end

    local lv = LV[PD.cur]
    local hasCampObjs = p.camp and #p.camp > 0
    local hasCampPts = lv and (lv.camps or lv.vendor) and true or false
    if hasCampObjs or hasCampPts then
        PushHead(rows, L["营地"], 1)
        for _, c in ipairs(p.camp or {}) do
            local lines = {}
            local function Add(label, v)
                if v and v ~= "" then lines[#lines + 1] = { label .. "：" .. v } end
            end
            Add(L["角色"], c[7])
            Add(L["增益"], c[6])
            Add(L["取代"], c[8])
            Add(L["互斥"], c[9])
            Add(L["容量"], c[10])
            if c[11] and #c[11] > 0 then
                lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(c[11])), 0.7, 0.7, 0.7 }
            end
            if c[12] and c[12][1] then
                lines[#lines + 1] = { format(L["图纸：%s"], DG.ItemName(c[12][1])) }
            end
            rows[#rows + 1] = {
                kind = "row", col = 1, icon = c[3],
                text = c[2] or "?",
                sub = c[5] or "",
                right = format(L["技能 %d"], c[4] or 0),
                lines = lines,
            }
        end
        if hasCampObjs and hasCampPts then PushGap(rows, 4, 1) end
        for _, side in ipairs({ "a", "h" }) do
            local fc = (side == "a") and C_ALLIANCE or C_HORDE
            local camp = lv and lv.camps and lv.camps[side]
            local vd = lv and lv.vendor and lv.vendor[side]
            if vd then
                local loc = tostring(vd[3] or "")
                if camp then
                    loc = format("%s · %s · %s", tostring(camp[1] or ""),
                                 PD.CampZoneName(camp[6], tostring(camp[2] or "")),
                                 tostring(camp[3] or ""))
                end
                local lines = {
                    { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 },
                    { format("%.1f, %.1f", vd[5] or 0, vd[6] or 0), 0.75, 0.75, 0.75 },
                }
                if camp then
                    lines[#lines + 1] = {
                        format(L["营地位置 %.1f, %.1f"], camp[4] or 0, camp[5] or 0),
                        0.75, 0.75, 0.75,
                    }
                end
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc, icon = PD.FAC_ICON[side],
                    text = format(L["军需官 · %s"], tostring(vd[1])),
                    sub = loc,
                    right = format("%.1f, %.1f", vd[5] or 0, vd[6] or 0),
                    lines = lines,
                    act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,
                }
            elseif camp then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc,
                    text = format(L["营地 · %s"], camp[3] or "?"),
                    sub = format("%s · %s", PD.CampZoneName(camp[6], tostring(camp[2] or "")), tostring(camp[1] or "")),
                    right = format("%.1f, %.1f", camp[4] or 0, camp[5] or 0),
                    lines = {
                        { L["点击：在地图上标记此位置"], 1, 0.82, 0 },
                        { format("%s %.1f, %.1f", tostring(camp[2] or ""), camp[4] or 0, camp[5] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(camp[6], camp[4], camp[5]) end,
                }
            end
        end
        PushGap(rows, PD.OV_GUT, 1)
    end

    if p.steps and #p.steps > 0 then
        PushHead(rows, p.steps_title or L["怎么开始"], 1)
        if p.steps_note then PushText(rows, p.steps_note, 14, C_GREY, 1) end
        for i, st in ipairs(p.steps) do
            rows[#rows + 1] = {
                kind = "row", col = 1,
                text = format("%d. %s", i, st[1] or ""), sub = st[2] or "",
                lines = { { st[1] or "" }, { st[2] or "", 0.85, 0.85, 0.85 } },
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
    if p.racials and #p.racials > 0 then
        PushHead(rows, L["种族相关"], 1)
        for _, rc in ipairs(p.racials) do PushText(rows, "· " .. (rc[3] or ""), 14, nil, 1) end
        PushGap(rows, PD.OV_GUT, 1)
    end

    if PD.cur == "camping" and PD.campView == "bonus" then
        PushHead(rows, L["全部专业的营地物件档位对照"], nil, 16)
        rows[#rows].noSec = true
    end

    local secN = 0
    for _, sp in ipairs(rows) do
        if sp.kind == "head" and not sp.noSec then
            secN = secN + 1
            sp.sec = secN
        elseif sp.kind ~= "gap" then
            sp.sec = secN
        end
    end
    PD.secCount = secN
end

local CAMP_AREA_MAP = ns.AreaMap or {}

local function MapIDAlive(mapID)
    if not mapID then return false end
    if not (C_Map and C_Map.GetMapInfo) then return true end
    local ok, mi = pcall(C_Map.GetMapInfo, mapID)
    return ok and mi ~= nil
end

function PD.MarkMapPoint(mapID, x, y)
    if not MapIDAlive(mapID) then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该位置的地图"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint then
        local pok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, (x or 0) / 100, (y or 0) / 100)
        if pok and pt then
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

function PD.MarkCampPoint(areaID, x, y)
    local mapID = areaID and CAMP_AREA_MAP[areaID] or nil
    if not MapIDAlive(mapID) then
        mapID = nil
        if areaID and C_Map and C_Map.GetMapInfoFromAreaID then
            local ok, mi = pcall(C_Map.GetMapInfoFromAreaID, areaID)
            mapID = ok and mi and mi.mapID or nil
        end
        if not MapIDAlive(mapID) then mapID = nil end
    end
    PD.MarkMapPoint(mapID, x, y)
end

function PD.MarkVendorLoc(loc)
    if not loc then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["该商人的位置暂未收录"], 1, 0.4, 0.4)
        end
        return
    end
    local mapID = loc[2]
    if not MapIDAlive(mapID) then
        mapID = loc[1] and CAMP_AREA_MAP[loc[1]] or nil
    end
    PD.MarkMapPoint(mapID, loc[3], loc[4])
end

function PD.VendorListOf(src)
    local all = (src and src.vendors) or {}
    if #all == 0 then return all end
    local f
    if UnitFactionGroup then
        local ok, eng = pcall(UnitFactionGroup, "player")
        if ok and eng == "Alliance" then
            f = "a"
        elseif ok and eng == "Horde" then
            f = "h"
        end
    end
    if not f then return all end
    local out, known = {}, false
    for i = 1, #all do
        local v = all[i]
        if v.side then
            known = true
            if v.side == f then out[#out + 1] = v end
        else
            out[#out + 1] = v
        end
    end
    if not known then return all end
    return out
end

function PD.VendorLocOf(src)
    local vs = PD.VendorListOf(src)
    if not vs then return nil end
    for _, v in ipairs(vs) do
        if v.id and ns.ProfVendors and ns.ProfVendors[v.id] then
            return ns.ProfVendors[v.id], v.name
        end
    end
    return nil
end

function PD.CampZoneName(areaID, fallback)
    local f = C_Map and C_Map.GetMapInfoFromAreaID
    if f and areaID then
        local ok, mi = pcall(f, areaID)
        if ok and mi and mi.name and mi.name ~= "" then return mi.name end
    end
    local g = C_Map and C_Map.GetAreaInfo
    if g and areaID then
        local ok, name = pcall(g, areaID)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    return fallback
end

function PD.MatIconTex(id, px)
    px = px or 14
    local ic = PD.ItemIcon(id)
    if type(ic) == "number" then
        return format("|T%d:%d:%d|t", ic, px, px)
    end
    return format("|TInterface\\Icons\\%s:%d:%d|t", tostring(ic or FALLBACK_ICON), px, px)
end

function PD.MatCol(list, fs, budget)
    if not list or #list == 0 then return "", 0, 0, nil end
    local gap, px = 0, PD.MAT_ICON_PX
    local out, w, n, segs = {}, 0, 0, {}
    for i = 1, #list do
        local m = list[i]
        local name = PD.ItemName(m[1])
        local cw = px + PD.TextW(name, fs)
        if n > 0 and w + gap + cw > budget then
            local avail = budget - w - gap - px
            if avail >= PD.MAT_TAIL_MIN then
                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)
                out[#out + 1] = piece2
                segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece2 }
            else
                out[#out + 1] = "…"
                segs[#segs + 1] = { text = "…" }
            end
            break
        end
        if n == 0 and cw > budget then
            name = PD.Fit(name, fs, budget - px)
            cw = px + PD.TextW(name, fs)
        end
        local piece = PD.MatIconTex(m[1], px) .. name
        out[#out + 1] = piece
        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }
        w = w + (n > 0 and gap or 0) + cw
        n = n + 1
    end
    return table.concat(out, ""), w, n, segs
end

function PD.MatText(list, maxN)
    if not list or #list == 0 then return "" end
    local t = {}
    for i, m in ipairs(list) do
        if maxN and i > maxN then t[#t + 1] = "…"; break end
        t[#t + 1] = format("%d×%s%s", m[2] or 1, PD.MatIconTex(m[1]), DG.ItemName(m[1]))
    end
    return table.concat(t, "  ")
end

function PD.IconZone(r)
    if r.__iconZone then return r.__iconZone end
    local z = CreateFrame("Button", nil, r)
    PD.WireTipZone(z, r)
    r.__iconZone = z
    return z
end

function PD.WarnChip(r, plainTip)
    if r.__warn then return r.__warn end
    local z = CreateFrame("Button", nil, r)
    z:SetSize(26, 20)
    if plainTip then
        z:SetScript("OnEnter", function(self)
            local lines = self.__tipLines
            if lines and lines[1] then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                for _, ln in ipairs(lines) do
                    if ln[1] and ln[1] ~= "" then
                        GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                    end
                end
                GameTooltip:Show()
            end
        end)
        z:SetScript("OnLeave", function() GameTooltip:Hide() end)
    else
        PD.WireTipZone(z, r)
    end
    local tex = z:CreateTexture(nil, "OVERLAY", nil, 2)
    tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\WarnTri")
    tex:SetSize(18, 18)
    tex:SetPoint("CENTER", z, "CENTER", 0, 0)
    r.__warn = z
    return z
end

function PD.PctChip(r)
    if r.__pct then return r.__pct end
    local f = CreateFrame("Frame", nil, r)
    ns.hui.BuildRoundedBG(f, 4, ns.hui.layer.L2, "both", true, 1)
    local fs = MakeFS(f, 10, C_TEXT, "CENTER")
    fs:SetPoint("LEFT", f, "LEFT", 4, 0)
    fs:SetPoint("RIGHT", f, "RIGHT", -4, 0)
    fs:SetPoint("TOP", f, "TOP", 0, -2)
    fs:SetPoint("BOTTOM", f, "BOTTOM", 0, 2)
    f.fs = fs
    r.__pct = f
    return f
end

function PD.VsBlock(r)
    if r.__vs then return r.__vs end
    local base = tonumber(r.GetFrameLevel and r:GetFrameLevel()) or 0
    local cards, zones = {}, {}
    for k = 1, 2 do
        local c = CreateFrame("Frame", nil, r)
        c:SetFrameLevel(base + 2)
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
        local host = CreateFrame("Frame", nil, c)
        host:SetFrameLevel(base + 3)
        host:SetPoint("TOPLEFT", c, "TOPLEFT", 0, 0)
        host:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", 0, 0)
        local lab = MakeFS(host, 12, C_GREY, "LEFT")
        lab:SetPoint("TOPLEFT", host, "TOPLEFT", 8, -4)
        local ic = host:CreateTexture(nil, "OVERLAY", nil, 2)
        ic:SetSize(22, 22)
        ic:SetPoint("BOTTOMLEFT", host, "BOTTOMLEFT", 8, 6)
        ic:Hide()
        local nm = MakeFS(host, 12, C_TEXT, "LEFT")
        nm:SetWordWrap(false)
        nm:SetPoint("LEFT", ic, "RIGHT", 5, 0)
        nm:SetPoint("RIGHT", host, "RIGHT", -8, 0)
        local price = MakeFS(host, 14, C_GOLD, "RIGHT")
        price:SetPoint("TOPRIGHT", host, "TOPRIGHT", -8, -8)
        c.lab, c.ic, c.nm, c.price, c.host = lab, ic, nm, price, host
        local bd = CreateFrame("Frame", nil, host)
        bd:SetFrameLevel(base + 5)
        ns.hui.BuildRoundedBG(bd, 4, ns.hui.layer.L4, "both", true, 1)
        local bdFs = MakeFS(bd, 10, { 0.42, 0.94, 0.62 }, "CENTER")
        bdFs:SetPoint("CENTER", bd, "CENTER", 0, 0)
        bd:SetSize(32, 14)
        bd:SetPoint("TOPRIGHT", host, "TOPRIGHT", -4, 9)
        bd:Hide()
        c.badge, c.badgeFs = bd, bdFs
        cards[k] = c
        local z = CreateFrame("Button", nil, r)
        z:SetFrameLevel(base + 4)
        PD.WireTipZone(z, r)
        zones[k] = z
    end
    r.__vs = { cards = cards, zones = zones }
    return r.__vs
end

function PD.WireTipZone(z, r)
    z:EnableMouseWheel(true)
    z:SetScript("OnEnter", function(self)
        PD.SetRowHover(r, true)
        local lines = self.__tipLines
        if lines then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        elseif self.__it and DG.ShowItemTip then
            local extra = self.__tipExtra
            if type(extra) == "function" then extra = extra() end
            DG.ShowItemTip(self, self.__it, extra)
        end
    end)
    z:SetScript("OnLeave", function(self)
        PD.SetRowHover(r, false)
        GameTooltip:Hide()
    end)
    z:SetScript("OnClick", function(self, button)
        if self.__act then
            self.__act(self, button)
            return
        end
        DG.ItemShiftClick(self, button)
    end)
    z:SetScript("OnMouseWheel", function(self, delta)
        PD.HideVendorPick()
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
end

function PD.MatSeg(r, i)
    if i == 1 then return r.f end
    local fs = r.mn[i]
    if not fs then
        fs = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
        fs:SetWordWrap(false)
        r.mn[i] = fs
    end
    return fs
end

function PD.MatZone(r, i)
    local z = r.mz[i]
    if not z then
        z = CreateFrame("Button", nil, r)
        PD.WireTipZone(z, r)
        r.mz[i] = z
    end
    return z
end

function PD.MatCnt(r, i)
    r.mcnt = r.mcnt or {}
    local c = r.mcnt[i]
    if not c then
        c = MakeFS(r, 10, C_WHITE, "RIGHT")
        local f, s = c:GetFont()
        c:SetFont(f, s, "OUTLINE")
        c:SetShadowColor(0, 0, 0, 1)
        c:SetShadowOffset(1, -1)
        c:SetWordWrap(false)
        r.mcnt[i] = c
    end
    return c
end

function PD.ClearMatSegs(r)
    if r.f then r.f:SetText("") end
    if r.mn then
        for _, fs in pairs(r.mn) do
            fs:SetText("")
            fs:Hide()
        end
    end
    if r.mz then
        for j = 1, #r.mz do r.mz[j]:Hide() end
    end
    if r.mcnt then
        for _, c in pairs(r.mcnt) do
            c:SetText("")
            c:Hide()
        end
    end
    if r.dv then r.dv:SetText(""); r.dv:Hide() end
end

local _qCache = {}
function PD.QualCached(id)
    if id == nil then return nil end
    local v = _qCache[id]
    if v == nil then
        v = DG.QualOf(id)
        if v ~= nil then _qCache[id] = v end
    end
    return v
end

function PD.PaintMatSegs(r, segs, color)
    local col = color or C_TEXT
    local prev
    for i = 1, #segs do
        local fs = PD.MatSeg(r, i)
        local scol = col
        if segs[i].id then
            local q = PD.QualCached(segs[i].id)
            if q then scol = { DG.QColor(q) } end
        end
        fs:SetTextColor(Unpack(scol))
        fs:SetText(segs[i].text or "")
        fs:ClearAllPoints()
        if i == 1 then
            fs:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        else
            fs:SetPoint("LEFT", prev, "RIGHT", 0, 0)
        end
        fs:Show()
        prev = fs
        local z = PD.MatZone(r, i)
        if segs[i].id then
            z.__it = { segs[i].id }
            z.__tipLines = nil
            z.__act = nil
            z:ClearAllPoints()
            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)
            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)
            z:Show()
            local c = PD.MatCnt(r, i)
            c:SetText(tostring(segs[i].cnt or 1))
            c:ClearAllPoints()
            c:SetPoint("BOTTOMRIGHT", fs, "BOTTOMLEFT", PD.MAT_ICON_PX - 1, 1)
            c:Show()
        else
            z:Hide()
            if r.mcnt and r.mcnt[i] then r.mcnt[i]:Hide() end
        end
    end
end

PD.SB_H  = 12
PD.SB_DY = -8
PD.SB_FS = 11
PD.SB_EDGE = 4
PD.CARD_PAD, PD.CARD_GAP = 3, 6
PD.LV_CARD_FIXW = 44
PD.SB_COL = {
    { 1.00, 0.50, 0.25 },
    { 1.00, 0.82, 0.00 },
    { 0.25, 0.75, 0.25 },
    { 0.55, 0.58, 0.64 },
}
PD.SB_INK = {
    { 0.10, 0.06, 0.02 },
    { 0.12, 0.09, 0.00 },
    { 0.04, 0.12, 0.03 },
    { 1.00, 1.00, 1.00 },
}
PD.CARD_COL = {
    trainer = { 0.29, 0.33, 0.40 },
    drop    = { 0.42, 0.27, 0.66 },
    vendor  = { 0.54, 0.42, 0.12 },
}
PD.CARD_INK = {
    trainer = { 0.81, 0.85, 0.89 },
    drop    = { 0.91, 0.86, 1.00 },
    vendor  = { 1.00, 0.91, 0.66 },
}

function PD.LvTier(skill, learn, yellow, green, grey)
    if not skill then return nil end
    if not (learn or yellow or green or grey) then return nil end
    if grey and skill >= grey then return 4 end
    if green and skill >= green then return 3 end
    if yellow and skill >= yellow then return 2 end
    return 1
end

function PD.SBValPos(skill, learn, yellow, green, grey, up)
    if not skill or type(learn) ~= "number" then return nil end
    if up then
        local thr = { learn, yellow, green, grey }
        local k = nil
        for j = 1, 4 do
            if type(thr[j]) == "number" and skill <= thr[j] then k = j break end
        end
        if not k then return 0.75 end
        while k < 4 and thr[k + 1] == thr[k] do k = k + 1 end
        return (k - 1) / 4
    end
    local t = PD.LvTier(skill, learn, yellow, green, grey)
    if not t then return nil end
    return (t - 1) / 4
end

function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)
    local seg = PD.LV_NAME_W / 4
    local a1, a2 = dim and 0.35 or 1, dim and 0.55 or 1
    for k = 1, 4 do
        local bg, tx = r.__sbBg[k], r.__sbTx[k]
        bg:ClearAllPoints()
        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)
        bg:SetSize(seg, PD.SB_H)
        bg:SetColorTexture(Unpack(PD.SB_COL[k]))
        bg:SetAlpha(a1)
        bg:Show()
        tx:ClearAllPoints()
        tx:SetPoint("CENTER", bg, "CENTER", 0, 0)
        tx:SetTextColor(Unpack(PD.SB_INK[k]))
        tx:SetAlpha(a2)
        tx:SetText(vals[k] and tostring(vals[k]) or "")
        tx:Show()
    end
    local lvs = { lvLo, lvHi }
    local xa = PD.SBValPos(lvs[1], vals[1], vals[2], vals[3], vals[4], false)
    local xb = PD.SBValPos(lvs[2], vals[1], vals[2], vals[3], vals[4], true)
    if xa and xb and xb < xa then xb = xa end
    for k = 1, 2 do
        local p = r.__sbPin[k]
        local x = (k == 1) and xa or xb
        if x then
            p:ClearAllPoints()
            p:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)
            p:SetSize(2, PD.SB_H + 6)
            p:SetAlpha(dim and 0.35 or 1)
            p:Show()
        else
            p:Hide()
        end
    end
end

function PD.HideSkillBar(r)
    for k = 1, 4 do
        r.__sbBg[k]:Hide()
        r.__sbTx[k]:SetText("")
        r.__sbTx[k]:Hide()
    end
    for k = 1, 2 do r.__sbPin[k]:Hide() end
end

function PD.PaintCard(r, card)
    local z, bg, tx = r.__cardZone, r.__cardBg, r.__cardTx
    if not card then
        z:Hide()
        bg:Hide()
        tx:SetText("")
        tx:Hide()
        z.__tipLines, z.__act, z.__it = nil, nil, nil
        return
    end
    local w = PD.LV_CARD_FIXW
    tx:ClearAllPoints()
    tx:SetPoint("CENTER", r, "LEFT", 6 + w / 2, PD.SB_DY)
    local col = PD.CARD_COL[card.kind] or PD.CARD_COL.trainer
    tx:SetTextColor(Unpack(PD.CARD_INK[card.kind] or PD.CARD_INK.trainer))
    tx:SetText(card.text or "")
    tx:Show()
    local th = tx:GetStringHeight()
    if (th or 0) <= 0 then th = 12 end
    local half = math.floor(th / 2) + 1
    bg:ClearAllPoints()
    bg:SetPoint("TOPLEFT", r, "LEFT", 6, PD.SB_DY + half)
    bg:SetPoint("BOTTOMRIGHT", r, "LEFT", 6 + w, PD.SB_DY - half)
    for _, tex in ipairs(bg.__pieces or {}) do
        tex:SetVertexColor(col[1], col[2], col[3])
        tex:SetAlpha(1)
    end
    bg:Show()
    z.__tipLines = card.lines
    z.__act = card.act
    z.__it = card.fid and { card.fid } or nil
    z:ClearAllPoints()
    z:SetPoint("TOPLEFT", r, "LEFT", 6, PD.SB_DY + half + 1)
    z:SetPoint("BOTTOMRIGHT", r, "LEFT", 6 + w, PD.SB_DY - half - 1)
    z:Show()
end

local TRAINER_CARD = {
    kind = "trainer", text = L["训练师"],
    lines = { { L["向训练师学习"], 0.81, 0.85, 0.89 } },
}

function PD.CardOf(rec, ri)
    if not rec then
        return (ri and ri.trainer) and TRAINER_CARD or nil
    end
    local fid = rec[13] and rec[13][1]
    if not fid then return TRAINER_CARD end
    local src = rec[14]
    local hasDrop = src and src.drops and #src.drops > 0
    local hasVendor = src and src.vendors and #src.vendors > 0
    local lines = { { format(L["图纸：%s"], DG.ItemName(fid)), 1, 0.82, 0.35 } }
    if hasDrop then
        lines[#lines + 1] = { format(L["掉落 %d 处"], #src.drops), 0.75, 0.75, 0.75 }
        local dl = PD.DropLines(src)
        for i = 1, #dl do lines[#lines + 1] = dl[i] end
    end
    local vl = PD.VendorLines(src)
    for i = 1, #vl do lines[#lines + 1] = vl[i] end
    return {
        kind = hasDrop and "drop" or (hasVendor and "vendor" or "drop"),
        text = L["图纸"], fid = fid, lines = lines,
        act = hasVendor and PD.VendorAct(src) or nil,
    }
end

function PD.RowBlk(r, j)
    local b = r.blk[j]
    if b then return b end
    b = {}
    b.ic = r:CreateTexture(nil, "ARTWORK")
    b.ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(b.ic) end
    b.ic:SetSize(PD.TBL_ICON, PD.TBL_ICON)
    b.nm = MakeFS(r, 12, C_TEXT, "LEFT")
    b.ct = MakeFS(r, PD.TBL_MAT_CNT_FS, C_GOLD, "LEFT")
    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, "THICKOUTLINE")
    b.ct:SetShadowColor(0, 0, 0, 1)
    b.ct:SetShadowOffset(1, -1)
    b.nm:SetWordWrap(false)
    b.ct:SetWordWrap(false)
    b.zone = CreateFrame("Button", nil, r)
    b.zone:Hide()
    PD.WireTipZone(b.zone, r)
    r.blk[j] = b
    return b
end

function PD.ClearMats(r)
    for j = 1, #r.blk do
        local b = r.blk[j]
        b.ic:Hide()
        b.nm:Hide()
        b.ct:Hide()
        if b.zone then b.zone:Hide() end
    end
end

function PD.WipeRow(r)
    if not r then return end
    r.__spec = nil
    PD.ClearMats(r); PD.ClearMatSegs(r)
    if r.icon then r.icon:Hide() end
    if r.gic then for _, g in ipairs(r.gic) do g:Hide() end end
    local iz = r.__iconZone; if iz then iz:Hide() end
    if r.__vs then
        for _, c in ipairs(r.__vs.cards) do c:Hide() end
        for _, z in ipairs(r.__vs.zones) do z:Hide() end
    end
    if r.__pct then r.__pct:Hide() end
    if r.__warn then r.__warn:Hide(); r.__warn.__tipLines = nil end
    if r.sep then r.sep:Hide() end
    if r.tagFs then r.tagFs:Hide() end
    if r.tagBg then r.tagBg:Hide() end
    if r.dv then r.dv:SetText(""); r.dv:Hide() end
    if r.__sbBg then PD.HideSkillBar(r) end
    if r.__cardZone then PD.PaintCard(r, nil) end
    if r.a then r.a:SetText("") end
    if r.b then r.b:SetText("") end
    if r.c then r.c:SetText("") end
    if r.d then r.d:SetText("") end
    if r.e then r.e:SetText("") end
    r:Hide()
end

function PD.PackMats(list, budget)
    local out, total, n = {}, 0, 0
    if not list or #list == 0 or not budget or budget <= 0 then return out, 0, false end
    for i = 1, #list do
        if n >= PD.TBL_BLK_MAX then break end
        local cnt = list[i][2] or 1
        local w = math.max(PD.TBL_ICON, PD.TextW(format("%d", cnt), PD.TBL_MAT_CNT_FS))
        local step = w + ((n > 0) and PD.TBL_BLK_GAP or 0)
        if total + step + PD.TBL_MARK_W > budget then
            return out, total, true
        end
        total = total + step
        out[#out + 1] = { id = list[i][1], cnt = cnt, w = w }
        n = n + 1
    end
    return out, total, n < #list
end

function PD.PaintMats(r, blocks, cut, grey)
    local n = blocks and #blocks or 0
    local W = PD.LV_ROW_W or PD.COL_LW
    local right = W - PD.TBL_MAT_RPAD
    if cut then
        local b = PD.RowBlk(r, n + 1)
        b.ic:Hide()
        b.ct:SetText("")
        b.ct:Hide()
        b.nm:SetTextColor(Unpack(grey and C_DIM or C_TEXT))
        b.nm:SetText("…")
        b.nm:ClearAllPoints()
        b.nm:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_NAME_DY)
        b.nm:Show()
        b.zone:Hide()
        right = right - PD.TBL_MARK_W - PD.TBL_BLK_GAP
    end
    for k = n, 1, -1 do
        local blk = blocks[k]
        local b = PD.RowBlk(r, k)
        SetIcon(b.ic, DG.ItemIcon(blk.id))
        b.ic:SetDesaturated(grey and true or false)
        b.ic:ClearAllPoints()
        b.ic:SetPoint("RIGHT", r, "RIGHT", -(W - right), 0)
        b.nm:Hide()
        b.ct:SetTextColor(Unpack(grey and C_DIM or C_GOLD))
        b.ct:SetText(format("%d", blk.cnt))
        b.ct:ClearAllPoints()
        b.ct:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_MAT_CNT_DY)
        b.zone.__it = { blk.id }
        b.zone:ClearAllPoints()
        b.zone:SetPoint("RIGHT", r, "RIGHT", -(W - right), 0)
        b.zone:SetSize(PD.TBL_ICON, PD.TBL_ICON)
        b.ic:Show(); b.ct:Show(); b.zone:Show()
        right = right - blk.w - PD.TBL_BLK_GAP
    end
    for k = n + (cut and 1 or 0) + 1, #r.blk do
        local b = r.blk[k]
        b.ic:Hide(); b.nm:Hide(); b.ct:Hide(); b.zone:Hide()
    end
end

function PD.LevelSrc(rec)
    if not rec then return nil, nil end
    local src = rec[14]
    local fid = rec[13] and rec[13][1]
    if not fid then return L["向训练师学习"], nil end
    local detail
    if src and src.drops and #src.drops > 0 then
        detail = format(L["图纸：%s · 掉落 %d 处"], DG.ItemName(fid), #src.drops)
    end
    return L["需图纸 · 商人出售"], detail
end

function PD.SourceParts(s)
    local out = {}
    if not s then return out end
    if s.skill then out[#out + 1] = { text = format(L["技能 %s"], tostring(s.skill)) } end
    if s.drops and #s.drops > 0 then
        out[#out + 1] = { text = format(L["掉落 %d 处"], #s.drops) }
    end
    if s.vendors and #s.vendors > 0 then
        local vs = PD.VendorListOf(s)
        if #vs > 1 then
            out[#out + 1] = { text = format(L["商人：%s 等 %d 人"], (vs[1] and vs[1].name) or "?", #vs), vendor = true }
        elseif #vs == 1 then
            local v = vs[1]
            out[#out + 1] = { text = format(L["商人：%s"], (v and v.name) or "?"), vendor = true }
        end
    end
    return out
end

function PD.SourceText(s)
    local p = PD.SourceParts(s)
    if #p == 0 then return nil end
    local t = {}
    for i = 1, #p do t[i] = p[i].text end
    return table.concat(t, " · ")
end

function PD.VendorLines(s)
    local out = {}
    if not (s and s.vendors and #s.vendors > 0) then return out end
    local vs = PD.VendorListOf(s)
    if #vs == 0 then return out end
    for i = 1, #vs do
        local v = vs[i]
        if v and (v.name or v.zone) then
            local nm = format(L["商人：%s"], tostring(v.name or "?"))
            if v.zone and v.zone ~= "" then nm = nm .. " · " .. tostring(v.zone) end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    local loc = PD.VendorLocOf(s)
    if loc then
        out[#out + 1] = { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 }
    end
    return out
end

function PD.DropLines(s)
    local out = {}
    if not (s and s.drops and #s.drops > 0) then return out end
    for i = 1, #s.drops do
        local dd = s.drops[i]
        if dd and (dd.npc or dd.zone) then
            local nm = format(L["掉落：%s"], tostring(dd.npc or "?"))
            if dd.zone and dd.zone ~= "" then nm = nm .. " · " .. tostring(dd.zone) end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    return out
end

function PD.VendorEntries(s)
    local out = {}
    local vs = PD.VendorListOf(s)
    for i = 1, #vs do
        local v = vs[i]
        if v.id and ns.ProfVendors and ns.ProfVendors[v.id] then
            out[#out + 1] = { loc = ns.ProfVendors[v.id], name = v.name, zone = v.zone }
        end
    end
    return out
end

function PD.VendorAct(s)
    return function(zone)
        local ents = PD.VendorEntries(s)
        if #ents == 0 then
            PD.MarkVendorLoc(nil)
        elseif #ents == 1 then
            PD.HideVendorPick()
            PD.MarkVendorLoc(ents[1].loc)
        else
            PD.VendorPickToggle(zone, ents)
        end
    end
end

function PD.DropEntries(s)
    local out = {}
    if not (s and s.drops) then return out end
    for _, dd in ipairs(s.drops) do
        local locs = dd.id and ns.ProfNPCLocs and ns.ProfNPCLocs[dd.id] or nil
        if locs then
            for _, loc in ipairs(locs) do
                out[#out + 1] = {
                    loc = loc,
                    name = tostring(dd.npc or "?"),
                    zone = PD.CampZoneName(loc[1], tostring(dd.zone or "")),
                }
            end
        end
    end
    return out
end

function PD.DropAct(s)
    return function(zone)
        local ents = PD.DropEntries(s)
        if #ents == 0 then
            PD.MarkVendorLoc(nil)
        elseif #ents == 1 then
            PD.HideVendorPick()
            PD.MarkVendorLoc(ents[1].loc)
        else
            PD.HideVendorPick()
            PD.VendorPickToggle(zone, ents, L["选择要标记的 NPC"])
        end
    end
end

function PD.DropLines(s)
    local out = {}
    if not (s and s.drops and #s.drops > 0) then return out end
    for i = 1, math.min(#s.drops, 8) do
        local dd = s.drops[i]
        if dd and (dd.npc or dd.zone) then
            local nm = format(L["掉落：%s"], tostring(dd.npc or "?"))
            if dd.zone and dd.zone ~= "" then nm = nm .. " · " .. tostring(dd.zone) end
            if dd.chance then
                nm = nm .. format(L[" · %d%%"], math.floor(dd.chance * 100 + 0.5))
            end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    if #s.drops > 8 then
        out[#out + 1] = { format(L["…等 %d 处"], #s.drops), 0.6, 0.6, 0.6 }
    end
    if #PD.DropEntries(s) > 0 then
        out[#out + 1] = { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 }
    end
    return out
end

local PICK_W, PICK_ROW_H, PICK_GAP, PICK_PAD = 210, 24, 2, 6

function PD.HideVendorPick()
    local pick = PD.vendorPick
    if not pick then return end
    if pick:IsShown() then pick:Hide() end
    if pick.__shield then pick.__shield:Hide() end
end

function PD.VendorPickToggle(zone, ents, title)
    local pick = PD.vendorPick
    if pick and pick:IsShown() and pick.__zone == zone then
        pick:Hide()
        return
    end
    if not (ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG) then
        PD.MarkVendorLoc(ents[1].loc)
        return
    end
    if not pick then
        pick = CreateFrame("Button", nil, PD.page, "BackdropTemplate")
        pick:EnableMouse(true)
        pick:SetFrameLevel(515)
        local shield = CreateFrame("Frame", nil, PD.page)
        shield:EnableMouse(true)
        shield:EnableMouseWheel(true)
        shield:SetAllPoints(PD.page)
        shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)
        shield:SetScript("OnMouseWheel", function(self, delta)
            PD.HideVendorPick()
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        pick.__shield = shield
        ns.hui.BuildRoundedBG(pick, 6, ns.hui.layer.L3, "both", true, 1)
        pick.title = MakeFS(pick, 11, C_GOLD, "LEFT")
        pick.title:SetPoint("TOPLEFT", pick, "TOPLEFT", PICK_PAD + 4, -PICK_PAD)
        pick.__rows = {}
        PD.vendorPick = pick
    end
    local rows = pick.__rows
    for k = 1, #ents do
        local e = ents[k]
        local r = rows[k]
        if not r then
            r = CreateFrame("Button", nil, pick, "BackdropTemplate")
            r:SetHeight(PICK_ROW_H)
            r.txt = MakeFS(r, 11, C_TEXT, "LEFT")
            r.txt:SetWordWrap(false)
            r.txt:SetPoint("LEFT", r, "LEFT", 6, 0)
            r.txt:SetPoint("RIGHT", r, "RIGHT", -6, 0)
            if ns.hui.BuildCapsule then
                r.__hov = ns.hui.BuildCapsule(r, 4, ns.hui.layer.L5, 0, 2)
                for _, ht in ipairs(r.__hov) do ht:Hide() end
            end
            r:SetScript("OnEnter", function(self)
                if self.__hov then
                    for _, ht in ipairs(self.__hov) do ht:Show() end
                end
            end)
            r:SetScript("OnLeave", function(self)
                if self.__hov then
                    for _, ht in ipairs(self.__hov) do ht:Hide() end
                end
            end)
            rows[k] = r
        end
        r.txt:SetText(e.zone and e.zone ~= ""
                      and (tostring(e.name or "?") .. " · " .. tostring(e.zone))
                      or tostring(e.name or "?"))
        r:SetScript("OnClick", function()
            PD.HideVendorPick()
            PD.MarkVendorLoc(e.loc)
        end)
        r:ClearAllPoints()
        if k == 1 then
            r:SetPoint("TOPLEFT", pick, "TOPLEFT", PICK_PAD, -(PICK_PAD + 18))
        else
            r:SetPoint("TOPLEFT", rows[k - 1], "BOTTOMLEFT", 0, -PICK_GAP)
        end
        r:SetPoint("RIGHT", pick, "RIGHT", -PICK_PAD, 0)
        r:Show()
    end
    for k = #ents + 1, #rows do
        rows[k]:Hide()
    end
    pick:SetWidth(PICK_W)
    pick:SetHeight(PICK_PAD + 18 + #ents * PICK_ROW_H + (#ents - 1) * PICK_GAP + PICK_PAD)
    pick.title:SetText(title or L["选择要标记的商人"])
    pick:ClearAllPoints()
    pick:SetPoint("TOPRIGHT", zone, "BOTTOMRIGHT", 0, -4)
    if pick.__shield then
        pick.__shield:SetFrameLevel(pick:GetFrameLevel() - 1)
        pick.__shield:Show()
    end
    pick:Show()
end

function PD.EnchantSpec(en)
    local matCol, _, _, matSg = PD.MatCol(en[9], PD.MAT_FS, PD.MAT_W)
    local costStr, total, unpriced, ah
    if en[9] and #en[9] > 0 then
        total, unpriced = RA.MatListCost(en[9])
        if total <= 0 or unpriced >= #en[9] then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if en[15] then
        ah = RA.AHPriceOf and RA.AHPriceOf(en[15])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    else
        ahStr = "—"
    end
    local spec
    if en[13] and #en[13] > 0 then
        local t = {}
        for _, b in ipairs(en[13]) do t[#t + 1] = b[3] or "" end
        spec = table.concat(t, " / ")
    end
    local vsEn = (en[10] and PD.VendorListOf(en[10])) or {}
    local hasVendor = #vsEn > 0
    local drEn = (en[10] and en[10].drops) or {}
    local base = en[10] and L["图纸"] or L["训练师"]
    local dpre, dval, dact, vlines
    if hasVendor then
        dpre = base
        if #vsEn > 1 then
            dval = format(L["商人：%s 等 %d 人"], tostring(vsEn[1] and vsEn[1].name or "?"), #vsEn)
        else
            dval = format(L["商人：%s"], tostring(vsEn[1] and vsEn[1].name or "?"))
        end
        dact = PD.VendorAct(en[10])
        vlines = PD.VendorLines(en[10])
    elseif #drEn > 0 then
        dpre = base
        dval = format(L["掉落 %d 处"], #drEn)
        dact = PD.DropAct(en[10])
        vlines = PD.DropLines(en[10])
    end
    local lines = { { en[1] or "" } }
    if en[4] and en[4] ~= "" then lines[#lines + 1] = { en[4] } end
    if en[10] then lines[#lines + 1] = { PD.SourceText(en[10]) or "", 0.7, 0.7, 0.7 } end
    if vlines then
        for _, ln in ipairs(vlines) do lines[#lines + 1] = ln end
    end
    if en[9] and #en[9] > 0 then
        lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(en[9])), 0.7, 0.7, 0.7 }
    end
    if spec then lines[#lines + 1] = { format(L["适用：%s"], spec), 0.6, 0.9, 0.6 } end
    return {
        kind = "row", is_new = en[11], _mats = en[9],
        icon = SpellIcon(en[14]),
        qItem = (type(en[15]) == "number") and en[15] or nil,
        text = en[2] or en[1] or "?",
        sub = table.concat({ tostring(en[3] or ""), tostring(en[4] or ""),
                             spec or "" }, " · "),
        mats = matCol,
        matSegs = matSg,
        right = not (en[5] or en[6] or en[7] or en[8])
                and format("%s · %s", format(L["学 %s"], tostring(en[5])),
                           PD.TierText(en[6], en[7], en[8])) or nil,
        right2 = en[12] and L["Season of Discovery"] or ((not dval) and base or nil),
        src = en[10],
        dpre = dpre,
        dval = dval,
        dact = dact,
        vlines = vlines,
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(en[5]),
        gapVal = (ah and total) and (ah - total) or nil,
        sbdiff = (en[5] or en[6] or en[7] or en[8]) and { en[5], en[6], en[7], en[8] } or nil,
        tipExtra = ((type(en[15]) == "number") and en[15])
                   and function() return PD.PriceTipLines(en[15], en[9]) end or nil,
        lines = lines,
        act = dact,
    }
end

function PD.SearchReserve()
    if PD.tab == "recipe" and not PD.setOpen then return PD.SEARCH_RESERVED end
    return 0
end

function PD.SearchHit(s)
    local q = PD.searchQ
    if not q or q == "" then return true end
    local name = tostring(s.text or "")
    if name ~= "" and string.find(string.lower(name), q, 1, true) then return true end
    local sub = tostring(s.sub or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    for _, m in ipairs(s._mats or {}) do
        local nm = tostring(PD.ItemName(m[1]) or "")
        if nm ~= "" and string.find(string.lower(nm), q, 1, true) then return true end
    end
    return false
end

function PD.SearchFilter(list)
    local q = PD.searchQ
    if not q or q == "" then return list end
    local f = {}
    for _, s in ipairs(list) do
        if PD.SearchHit(s) then f[#f + 1] = s end
    end
    return f
end

function PD.FinishSpecMats(s)
    if s and s._mats then
        s._matsPending = nil
        local sg
        s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)
        s.matSegs = sg
    end
    return s
end

function PD.FitRecipeCols(list, maxW)
    if maxW == nil then
        maxW = 0
        for _, s in ipairs(list) do
            local w = PD.TextW(s.text or "", 13)
            local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)
            if sw > w then w = sw end
            if w > maxW then maxW = w end
        end
    end
    local nameW = math.floor(math.max(PD.RECIPE_NAME_MIN,
                   math.min(PD.RECIPE_NAME_MAX, maxW + 6)))
    PD.RECIPE_NAME_W = nameW
    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD
    PD.MAT_W = PD.MAT_ROW_W - (6 + PD.DiffBarW() + PD.REC_AH_W + PD.REC_COST_W) - PD.MAT_X - 8
    local keep = PD.SyncRows()
    local idx = 0
    for _, s in ipairs(list) do
        idx = idx + 1
        if s._mats then
            if idx <= keep then
                PD.FinishSpecMats(s)
            else
                s._matsPending = true
            end
        end
        if s.text and s.text ~= "" then
            s.text = PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,
                                                 (PD.RECIPE_NAME_W or 0) - 6))
        end
    end
end

local function DiffSegW()
    return (PD.TextW and PD.TextW("000", PD.SB_FS) or 24) + 3
end
function PD.DiffBarW()
    return DiffSegW() * 4 + 6
end

function PD.PaintDiffBar(r, vals)
    if not vals then
        if r.__dbBg then
            for k = 1, 4 do r.__dbBg[k]:Hide() r.__dbTx[k]:Hide() end
        end
        return
    end
    r.__dbBg = r.__dbBg or {}
    r.__dbTx = r.__dbTx or {}
    local seg = DiffSegW()
    local col = PD.SB_COL or { { 1, .5, .2 }, { 1, .9, .2 }, { .4, 1, .3 }, { .55, .55, .55 } }
    local ink = PD.SB_INK or { { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 }, { 1, 1, 1 } }
    local right = 6
    for k = 4, 1, -1 do
        local bg = r.__dbBg[k]
        if not bg then
            bg = r:CreateTexture(nil, "ARTWORK")
            bg:SetColorTexture(1, 1, 1, 1)
            bg:Hide()
            r.__dbBg[k] = bg
            local tx = MakeFS(r, PD.SB_FS, C_WHITE, "CENTER")
            tx:SetText("")
            tx:SetWordWrap(false)
            tx:Hide()
            r.__dbTx[k] = tx
        end
        bg:ClearAllPoints()
        bg:SetPoint("TOPRIGHT", r, "TOPRIGHT", -right, -4)
        bg:SetSize(seg, PD.SB_H)
        bg:SetColorTexture(col[k][1], col[k][2], col[k][3], 0.95)
        bg:Show()
        local tx = r.__dbTx[k]
        tx:ClearAllPoints()
        tx:SetPoint("CENTER", bg, "CENTER", 0, 0)
        tx:SetTextColor(ink[k][1], ink[k][2], ink[k][3])
        tx:SetText(vals[k] and tostring(vals[k]) or "")
        tx:Show()
        right = right + seg
    end
end

local TIP_RED = { 1, 0.3, 0.25 }
function PD.PriceTipLines(itemID, mats)
    local lines = {}
    if not itemID then return lines end
    local ah = RA.AHPriceOf and RA.AHPriceOf(itemID) or nil
    local sell = RA.NPCSellPriceOf and RA.NPCSellPriceOf(itemID) or nil
    local cost, unpriced, nMats
    if mats and #mats > 0 then
        cost, unpriced = RA.MatListCost(mats)
        nMats = #mats
    end
    lines[#lines + 1] = { format(L["拍卖: %s"], ah and RA.MoneyStr(ah, "copper") or "—") }
    lines[#lines + 1] = { format(L["卖店: %s"], sell and RA.MoneyStr(sell, "copper") or "—") }
    local costTxt = "—"
    local approx = false
    if cost and nMats then
        if cost <= 0 or unpriced >= nMats then
            costTxt = "—"
        else
            approx = unpriced > 0
            costTxt = (approx and "≈" or "") .. RA.MoneyStr(cost, "copper")
        end
    end
    lines[#lines + 1] = { format(L["成本: %s"], costTxt) }
    if ah and cost and nMats and cost > 0 then
        local pre = approx and "≈" or ""
        local diff = ah - cost
        local net = math.floor(ah * 0.95) - cost
        local l4 = format(L["差价: %s"], pre .. RA.MoneyStr(diff, "copper"))
        local l5 = format(L["AH5%%: %s"], pre .. RA.MoneyStr(net, "copper"))
        if diff < 0 then
            lines[#lines + 1] = { l4, unpack(TIP_RED) }
        else
            lines[#lines + 1] = { l4 }
        end
        if net < 0 then
            lines[#lines + 1] = { l5, unpack(TIP_RED) }
        else
            lines[#lines + 1] = { l5 }
        end
    end
    return lines
end

local AH_PCT_RED = { 1, 0.32, 0.28 }
local AH_PCT_GREEN = { 0.36, 0.85, 0.55 }
function PD.AhPct(ah, cost)
    if not ah or not cost or cost <= 0 then return nil end
    local v = math.floor((ah - cost) / cost * 100 + 0.5)
    if v == 0 then return { text = "0%", color = { 0.75, 0.75, 0.75 } } end
    if v > 0 then return { text = "+" .. v .. "%", color = AH_PCT_RED } end
    return { text = tostring(v) .. "%", color = AH_PCT_GREEN }
end

PD.KIT_STAT_PATS = {
    { "Stamina value by (%d+)", "耐力" },
    { "Spell Power value by (%d+)", "法术强度" },
    { "Attack Power value by (%d+)", "攻击强度" },
    { "Defense Skill by (%d+)", "防御技能" },
    { "[Aa]rmor value by (%d+)", "护甲" },
    { "defense value.-by (%d+)", "防御技能" },
}
function PD.KitSub(sub, desc)
    if not sub or not sub:find("^永久附着") then return sub end
    local found = {}
    if desc and desc ~= "" then
        for _, it in ipairs(PD.KIT_STAT_PATS) do
            local v = desc:match(it[1])
            if v then
                found[#found + 1] = { pos = desc:find(it[1]), txt = L[it[2]] .. "+" .. v }
            end
        end
    end
    if #found == 0 then return sub end
    table.sort(found, function(a, b) return a.pos < b.pos end)
    local parts = {}
    local lv = sub:match("，(%d+)%s*[级級]")
    if lv then parts[#parts + 1] = format(L["要求%d级"], tonumber(lv)) end
    for _, f in ipairs(found) do parts[#parts + 1] = f.txt end
    return table.concat(parts, " ")
end

function PD.RecipeSpec(r)
    local vs = (r[14] and PD.VendorListOf(r[14])) or {}
    local hasVendor = #vs > 0
    local base = r[13] and L["图纸"] or L["训练师"]
    local dpre, dval
    if hasVendor then
        dpre = base
        if #vs > 1 then
            dval = format(L["商人：%s 等 %d 人"], tostring(vs[1] and vs[1].name or "?"), #vs)
        else
            dval = format(L["商人：%s"], tostring(vs[1] and vs[1].name or "?"))
        end
    end
    local costStr, total, unpriced, ah
    if r[12] and #r[12] > 0 then
        total, unpriced = RA.MatListCost(r[12])
        if total <= 0 or unpriced >= #r[12] then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if r[2] and RA.AHPriceOf then
        ah = RA.AHPriceOf(r[2])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    end
    return {
        kind = "row", is_new = r[11], it = { r[2] }, qItem = r[2], row = r, _mats = r[12],
        text = PD.ItemName(r[2]),
        tipExtra = function() return PD.PriceTipLines(r[2], r[12]) end,
        sub = PD.KitSub(tostring(r[5] or ""), r[6]),
        mats = nil,
        right = not ((r[7] or r[8] or r[9] or r[10]))
                and format("%s · %s", format(L["学 %s"], tostring(r[7])),
                           PD.TierText(r[8], r[9], r[10])) or nil,
        right2 = (not dval) and base or nil,
        src = r[14],
        dpre = dpre,
        dval = dval,
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(r[7]),
        gapVal = (ah and total) and (ah - total) or nil,
        sbdiff = (r[7] or r[8] or r[9] or r[10]) and { r[7], r[8], r[9], r[10] } or nil,
        mkLines = function()
            local lines = {}
            if r[6] and r[6] ~= "" then lines[#lines + 1] = { r[6] } end
            local mt = PD.MatText(r[12], 4)
            lines[#lines + 1] = { format(L["材料：%s"], mt ~= "" and mt or L["无"]) }
            lines[#lines + 1] = { format(L["技能：学 %s · %s"], tostring(r[7]),
                                         PD.TierText(r[8], r[9], r[10])) }
            if r[15] and #r[15] > 0 then
                lines[#lines + 1] = { format(L["改版前材料：%s"], PD.MatText(r[15])), 0.9, 0.7, 0.4 }
            end
            if hasVendor then
                for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
            end
            if r[16] and r[16] ~= "" then
                lines[#lines + 1] = { format(L["套装：%s"], r[16]), 0.64, 0.21, 0.93 }
            end
            if r[17] and r[17] ~= "" then
                lines[#lines + 1] = { format(L["护甲类型：%s"], r[17]), 0.7, 0.7, 0.7 }
            end
            return lines
        end,
        act = hasVendor and PD.VendorAct(r[14]) or nil,
    }
end

function PD.CraftedSpec(c)
    local mats = PD.MatText(c[8], 4)
    local matCol, _, _, matSg = PD.MatCol(c[8], PD.MAT_FS, PD.MAT_W)
    local green = c[6]
    if not green and c[5] and c[7] then
        green = math.floor((c[5] + c[7]) / 2)
    end
    local fid = tonumber(c[9])
    local base = nil
    if fid then
        base = L["图纸"]
    else
        local LV = ns.ProfLeveling and ns.ProfLeveling[PD.cur]
        local ri = LV and LV.rinfo and LV.rinfo[c[1]]
        if ri and ri.trainer then
            base = L["训练师"]
        else
            local learn = LV and LV.learn
            if learn then
                for _, id in ipairs(learn) do
                    if id == c[1] then base = L["训练师"] break end
                end
            end
        end
    end
    local costStr, total, unpriced, ah
    if c[8] and #c[8] > 0 then
        total, unpriced = RA.MatListCost(c[8])
        if total <= 0 or unpriced >= #c[8] then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if c[2] and RA.AHPriceOf then
        ah = RA.AHPriceOf(c[2])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    end
    return {
        kind = "row", is_new = c[10], it = { c[2] }, qItem = c[2], _mats = c[8], craft = c,
        text = DG.ItemName(c[2]),
        sub = "",
        mats = matCol,
        matSegs = matSg,
        right = not (c[4] or c[5] or green or c[7])
                and format("%s · %s", format(L["学 %s"], tostring(c[4])),
                           PD.TierText(c[5], green, c[7])) or nil,
        right2 = base or "",
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(c[4]),
        gapVal = (ah and total) and (ah - total) or nil,
        sbdiff = (c[4] or c[5] or green or c[7]) and { c[4], c[5], green, c[7] } or nil,
        tipExtra = function() return PD.PriceTipLines(c[2], c[8]) end,
        lines = {
            { format(L["材料：%s"], mats ~= "" and mats or L["无"]) },
            fid and { format(L["图纸：%s"], DG.ItemName(fid)), 1, 0.82, 0.35 } or nil,
        },
    }
end

function PD.FavorSpec(f, d)
    local out = f[5] and DG.ItemName(f[5])
    local reward = (out and out ~= "" and out) or f[4] or ""
    local mats = nil
    if d and d.rows then
        local want = f[5] or f[1]
        for _, r in ipairs(d.rows) do
            if r[2] == want then
                if r[12] and #r[12] > 0 then mats = r[12] end
                break
            end
        end
    end
    if (not mats) and d and d.crafted then
        local want = f[5] or f[1]
        for _, c in ipairs(d.crafted) do
            if c[8] and #c[8] > 0 and (c[2] == want or c[9] == tostring(f[1])) then
                mats = c[8]
                break
            end
        end
    end
    local costStr
    if mats then
        local total, unpriced = RA.MatListCost(mats)
        if total <= 0 or unpriced >= #mats then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if RA.AHPriceOf then
        local ah = RA.AHPriceOf(f[5] or f[1])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    end
    return {
        kind = "row", it = { f[1] }, qItem = f[1], _mats = mats,
        text = DG.ItemName(f[1]),
        right = format(L["技能 %s"], tostring(f[2])),
        right2 = format(L["商人青睐 %s"], tostring(f[3])),
        costStr = costStr,
        ahStr = ahStr,
        tipExtra = function() return PD.PriceTipLines(f[1], mats) end,
        lines = { { format(L["交出：%s"], DG.ItemName(f[1])) },
                  { (reward ~= "" and format(L["换得：%s"], reward))
                    or format(L["换得：%s"], tostring(f[4])), 1, 0.82, 0 },
                  { format(L["所需：技能 %s · 商人青睐 %s"], tostring(f[2]), tostring(f[3])),
                    0.7, 0.7, 0.7 } },
    }
end

function PD.RecipeTool(d)
    if not d then return {}, nil end
    local tool = {}
    local function on(k) return PD.toolKey == k end
    if d.rows and #d.rows > 0 then
        tool[#tool + 1] = { key = "all", text = format(L["全部 %d"], #d.rows), on = on("all") }
        for _, g in ipairs(d.groups or {}) do
            tool[#tool + 1] = { key = g[1], text = format("%s %d", g[2] or g[1], g[4] or 0),
                                on = on(g[1]) }
        end
    end
    if d.enchants and #d.enchants > 0 then
        if d.rows and #d.rows > 0 then
            tool[#tool + 1] = { key = "__enchant", text = format(L["附魔 %d"], #d.enchants),
                                on = on("__enchant") }
        else
            local gc, og = {}, {}
            for _, e in ipairs(d.enchants) do
                local g = tostring(e[3] or "")
                if g == "" then g = L["其他"] end
                if not gc[g] then gc[g] = 0; og[#og + 1] = g end
                gc[g] = gc[g] + 1
            end
            tool[#tool + 1] = { key = "all", text = format(L["全部 %d"], #d.enchants), on = on("all") }
            for _, g in ipairs(og) do
                tool[#tool + 1] = { key = g, text = format("%s %d", g, gc[g]), on = on(g) }
            end
        end
    end
    if d.crafted and #d.crafted > 0 then
        tool[#tool + 1] = { key = "__crafted", text = format(L["可制造 %d"], #d.crafted),
                            on = on("__crafted") }
    end
    if d.favor and #d.favor > 0 then
        tool[#tool + 1] = { key = "__favor", text = format(L["商人兑换 %d"], #d.favor),
                            on = on("__favor") }
    end
    if #tool > PD.TOOL_MAX then
        local keep = PD.TOOL_MAX - 1
        local rest = 0
        for i = keep + 1, #tool do rest = rest + 1 end
        for i = #tool, keep + 1, -1 do table.remove(tool, i) end
        tool[#tool + 1] = { key = "__rest", text = format(L["其他 %d"], rest), on = on("__rest") }
    end
    local valid = false
    for _, t in ipairs(tool) do if t.on then valid = true end end
    if not valid then
        PD.toolKey = tool[1] and tool[1].key or "all"
        if tool[1] then tool[1].on = true end
    end
    return tool, function(k) PD.toolKey = k; PD.RequestRender() end
end

function PD.RecipeList(limit, q)
    local d = RGet(PD.cur)
    local out = {}
    if not d then return out end
    local key = PD.toolKey
    local cap = limit or PD.ROW_CAP
    if cap < 1 then return out end
    if key == "__enchant" then
        for _, e in ipairs(d.enchants or {}) do
            out[#out + 1] = PD.EnchantSpec(e)
            if #out >= cap then break end
        end
        return out
    end
    if d.enchants and #d.enchants > 0 and not (d.rows and #d.rows > 0)
       and key ~= "__crafted" and key ~= "__favor" and key ~= "__rest" then
        local want
        if key ~= "all" then want = tostring(key) end
        for _, e in ipairs(d.enchants or {}) do
            local g = tostring(e[3] or "")
            if g == "" then g = L["其他"] end
            if (not want) or g == want then
                out[#out + 1] = PD.EnchantSpec(e)
                if #out >= cap then break end
            end
        end
        return out
    end
    if key == "__crafted" then
        for _, c in ipairs(d.crafted or {}) do
            out[#out + 1] = PD.CraftedSpec(c)
            if #out >= cap then break end
        end
        return out
    end
    if key == "__favor" then
        for _, f in ipairs(d.favor or {}) do
            out[#out + 1] = PD.FavorSpec(f, d)
            if #out >= cap then break end
        end
        return out
    end
    local fk = PD.EffKeyFilter(d)
    local __ri = 0
    for _, r in ipairs(d.rows or {}) do
        __ri = __ri + 1
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                out[#out + 1] = PD.RecipeSpec(r)
                if #out >= cap then break end
            end
        end
        if __ri % 32 == 0 and coroutine.running and coroutine.running() then coroutine.yield() end
    end
    return out
end

function PD.RawHit(r, q)
    if not q or q == "" then return true end
    local nm = PD.ItemName(r[2])
    if nm and nm ~= "" and string.find(string.lower(tostring(nm)), q, 1, true) then
        return true
    end
    local sub = tostring(r[5] or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    for _, m in ipairs(r[12] or {}) do
        local mn = PD.ItemName(m[1])
        if mn and mn ~= "" and string.find(string.lower(tostring(mn)), q, 1, true) then
            return true
        end
    end
    return false
end

function PD.EffKeyFilter(d)
    local key = PD.toolKey
    if not key or key == "all" then return nil end
    for _, r in ipairs(d.rows or {}) do
        if r[4] == key then return key end
    end
    return nil
end

function PD.ScanRecipe()
    local d = RGet(PD.cur)
    if not d then return 0, 0 end
    local key = PD.toolKey
    if key == "__enchant" or key == "__crafted" or key == "__favor" then
        return nil
    end
    if not (d.rows and #d.rows > 0) then return nil end
    local q = (PD.searchQ and PD.searchQ ~= "") and PD.searchQ or nil
    local fk = PD.EffKeyFilter(d)

    local n, maxW = 0, 0
    for _, r in ipairs(d.rows or {}) do
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                n = n + 1
                if n <= PD.ROW_CAP then
                    local nm = PD.ItemName(r[2])
                    local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0
                    local sw = PD.TextW(PD.KitSub(tostring(r[5] or ""), r[6]), 11) + (r[11] and PD.RECIPE_BADGE_W or 0)
                    if sw > w then w = sw end
                    if w > maxW then maxW = w end
                end
            end
        end
    end
    return n, maxW
end

function PD.RowsRecipe(rows)
    local d = RGet(PD.cur)
    if not d then return end
    local realN, maxW = PD.ScanRecipe()
    local list
    if realN then
        list = PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)
    else
        list = PD.SearchFilter(PD.RecipeList())
        realN, maxW = #list, nil
    end
    if PD.recipeSort then
        local kf = ({ ah = "ahVal", cost = "costVal", diff = "diffVal", gap = "gapVal" })[PD.recipeSort]
        if kf then
            local desc = PD.recipeSortDesc
            table.sort(list, function(a, b)
                local ka, kb = a[kf], b[kf]
                if ka and kb then
                    if desc then return ka > kb end
                    return ka < kb
                end
                if ka or kb then return ka ~= nil end
                return false
            end)
        end
    end
    PD.FitRecipeCols(list, maxW)
    if realN == 0 and PD.searchQ and PD.searchQ ~= "" then
        PushGap(rows)
        PushText(rows, format(L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"],
                              PD.searchQ), 12, C_GOLD)
        return
    end
    local trunc = 0
    if realN > PD.ROW_CAP then trunc = realN - PD.ROW_CAP end
    if realN > 0 then
        rows[#rows + 1] = { kind = "rechead", h = 26, col = 1, noTip = true }
    end
    for i = 1, #list do rows[#rows + 1] = list[i] end
    if trunc > 0 then
        PushGap(rows)
        PushText(rows, format(
            L["列表只画前 %d 条，还有 %d 条没显示 —— 用上方分类缩小范围。"],
            PD.ROW_CAP, trunc), 12, C_GOLD)
    end
end

function PD.ZoneText(list, maxN)
    if not list or #list == 0 then return L["无数据"] end
    local t = {}
    for i, z in ipairs(list) do
        if maxN and i > maxN then t[#t + 1] = "…"; break end
        t[#t + 1] = format("%s(%d)", DG.ZoneName(z[1]), z[2] or 0)
    end
    return table.concat(t, "  ")
end

DG.FISH_FIELD_LABEL = {
    L["所需技能"], L["技能加成"], L["持续（分钟）"], L["等级"],
    L["学会后解锁"], L["标注新增"], L["可作为钓具"], L["需求"],
}
DG.FISH_GROUPS = {
    { key = "spells", text = L["钓鱼法术"] },
    { key = "lures",  text = L["鱼饵"] },
    { key = "food",   text = L["钓鱼食物"] },
    { key = "items",  text = L["钓鱼物品"] },
    { key = "titles", text = L["钓鱼称号"] },
}

function PD.RowsFishing(rows)
    local p = D.pro.fishing
    local zones = GA and GA.fishing
    if zones and #zones > 0 then
        PushHead(rows, format(L["可钓区域（%d 处）"], #zones))
        for _, z in ipairs(zones) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, text = DG.ZoneName(z[1]),
                right = format(L["技能 %s"], tostring(z[2])),
            }
        end
        PushGap(rows)
    end

    if p and p.ranks and #p.ranks > 0 then
        PushHead(rows, L["技能等级（怎么把上限提上去）"])
        for _, rk in ipairs(p.ranks) do
            local note = rk[3] or ""
            local book = rk[4]
            if book then note = note:gsub("{book}", (DG.ItemName(book))) end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1,
                it = book and { book } or nil,
                text = rk[1] or "?", right = format(L["技能 %s"], tostring(rk[2])),
                lines = { { rk[1] or "" }, { note } },
            }
            if note ~= "" then PushText(rows, "· " .. note, 11, C_GREY) end
        end
        PushGap(rows)
    end

    if not (p and p.fishing) then return end
    for _, grp in ipairs(DG.FISH_GROUPS) do
        local list = p.fishing[grp.key]
        if list and #list > 0 then
            PushHead(rows, format(L["%s（%d 条）"], grp.text, #list))
            local isSpell = (grp.key == "spells")
            local isTitle = (grp.key == "titles")
            for _, e in ipairs(list) do
                local id, icon, sub = e[1], e[3], e[5]
                local nm
                if isSpell then
                    nm = SpellName(id)
                elseif not isTitle then
                    nm = DG.ItemName(id)
                end
                if type(nm) ~= "string" or nm == "" then nm = e[2] end
                local lines = {}
                if e[4] and e[4] ~= "" then lines[#lines + 1] = { e[4] } end
                if sub and sub ~= "" then lines[#lines + 1] = { sub, 0.7, 0.7, 0.7 } end
                for i = 6, 13 do
                    local v = e[i]
                    if v ~= nil and v ~= false and v ~= 0 and v ~= "" then
                        if type(v) == "table" then
                            local t = {}
                            for _, x in ipairs(v) do t[#t + 1] = tostring(x) end
                            v = table.concat(t, " / ")
                        end
                        if v ~= "" then
                            lines[#lines + 1] = { format("%s：%s",
                                DG.FISH_FIELD_LABEL[i - 5], tostring(v)), 0.6, 0.9, 0.6 }
                        end
                    end
                end
                rows[#rows + 1] = {
                    kind = "row", is_new = e[11],
                    it = (id and not isSpell and not isTitle) and { id } or nil,
                    icon = (icon ~= "" and icon) or nil,
                    text = nm or (id and format(L["法术 #%d"], id)) or "?",
                    sub = sub or "", right = (e[6] and format(L["技能 %s"], tostring(e[6]))) or "",
                    right2 = e[9] and format(L["等级 %s"], tostring(e[9])) or "",
                    lines = lines,
                }
            end
            PushGap(rows)
        end
    end
end

function PD.RowsGather(rows)
    if PD.cur == "fishing" then
        PD.RowsFishing(rows)
        return
    end
    local g = GA and GA[PD.cur]
    if not g then return end
    if PD.cur == "skinning" then
        PushHead(rows, L["剥皮档次（等级区间 → 产出 → 分布）"])
        for _, t in ipairs(g) do
            local items = {}
            for _, id in ipairs(t[2] or {}) do items[#items + 1] = DG.ItemName(id) end
            rows[#rows + 1] = {
                kind = "row",
                text = format(L["等级 %s - %s"], tostring(t[1][1]), tostring(t[1][2])),
                sub = table.concat(items, "  "),
                right2 = PD.ZoneText(t[3], 3),
                lines = { { format(L["产出：%s"], table.concat(items, "  ")) },
                          { format(L["分布：%s"], PD.ZoneText(t[3])) } },
            }
        end
        return
    end
    PushHead(rows, L["节点表（所需技能 → 产出 → 分布）"])
    for _, n in ipairs(g) do
        local head = n[1] and n[1][1]
        local items = {}
        for _, id in ipairs(n[1] or {}) do items[#items + 1] = DG.ItemName(id) end
        local nm, got = DG.ItemName(head)
        if not got then nm = head and format(L["物品 #%d"], head) or "?" end
        rows[#rows + 1] = {
            kind = "row", it = head and { head } or nil, text = nm,
            sub = table.concat(items, "  "),
            right = format(L["技能 %d"], n[2] or 0),
            right2 = PD.ZoneText(n[3], 3),
            lines = { { format(L["产出：%s"], table.concat(items, "  ")) },
                      { format(L["分布：%s"], PD.ZoneText(n[3])) } },
        }
    end
end

function PD.RowsGatherRoute(rows)
    local slug = PD.cur
    local g = GA and (GA[slug] or (slug == "fishing" and GA.fishing))
    if not g or #g == 0 then return end
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[slug] and _learned[slug].cur or nil
    local GR_GREEN = { 0.4, 0.9, 0.45 }

    if PD.GatherMode(slug) == "smelt" then
        PushHead(rows, L["熔炼升级路线（全程）"])
        if curLv then
            PushText(rows, format(L["当前技能 %d，绿色为可练区间：练到下一档再换锭。"], curLv), 11, C_GREY)
        else
            PushText(rows, L["未学到该专业，先找训练师学习；学习后这里显示当前位置。"], 11, C_GREY)
        end
        PushGap(rows)
        for i, t in ipairs(SMELT_TBL) do
            local lo = t[2]
            local hi = (SMELT_TBL[i + 1] and SMELT_TBL[i + 1][2] or 301) - 1
            if hi < lo then hi = lo end
            local active = curLv and curLv >= lo and curLv <= hi
            local nm = DG.ItemName(t[1])
            if not (type(nm) == "string" and nm ~= "") then nm = format(L["物品 #%d"], t[1]) end
            local rng = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo)
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, gr3 = true,
                it = { t[1] }, qItem = t[1],
                lv = rng,
                text = nm,
                nameColor = (active and GR_GREEN) or nil,
            }
        end
        return
    end
    if slug == "fishing" then
        PushHead(rows, format(L["钓鱼升级路线（%d 处水域）"], #g))
        PushText(rows, L["按技能门槛分档推进：下竿必涨，到下一档门槛就换区域。"], 11, C_GREY)
        PushGap(rows)
        local bands = {}
        for _, ed in ipairs(g) do
            local b = bands[#bands]
            if b and b[1] == ed[2] then b[2][#b[2] + 1] = ed[1]
            else bands[#bands + 1] = { ed[2], { ed[1] } } end
        end
        for bi, band in ipairs(bands) do
            local nxt = bands[bi + 1]
            local active = curLv and curLv >= band[1] and (not nxt or curLv < nxt[1])
            local names = {}
            for _, zid in ipairs(band[2]) do
                names[#names + 1] = DG.ZoneName(zid) or format("#%d", zid)
            end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1,
                text = format(L["技能 %d 起"], band[1]),
                sub = table.concat(names, "、"),
                nameColor = active and { 0.4, 0.9, 0.45 } or nil,
                lines = { { active and L["◆ 推荐当前就练这一档"] or
                    (nxt and format(L["练到 %d 换下一档"], nxt[1]) or L["练满为止"]),
                    0.62, 0.62, 0.62 } },
            }
        end
        return
    end

    PushHead(rows, L["采集升级路线（全程）"])
    if curLv then
        PushText(rows, format(L["当前技能 %d，绿色为推荐段：采到区间上缘再换下一段。"], curLv), 11, C_GREY)
    else
        PushText(rows, L["未学到该专业，先找训练师学习；学习后这里显示当前位置。"], 11, C_GREY)
    end
    PushGap(rows)
    local function GrSameSeg(a, b)
        if #a ~= #b then return false end
        for k = 1, #a do if a[k] ~= b[k] then return false end end
        return true
    end
    local SKIN_SKILL = { [1] = { 1, 1 }, [11] = { 10, 100 }, [21] = { 105, 150 }, [31] = { 155, 200 }, [41] = { 205, 250 }, [51] = { 255, 300 } }
    local gi = 1
    local HERB_GRP = { { 1, 50 }, { 50, 100 }, { 100, 150 }, { 150, 205 }, { 205, 230 }, { 230, 270 }, { 270, 300 } }
    local MINE_GRP = { { 1, 65 }, { 65, 125 }, { 125, 175 }, { 175, 245 }, { 245, 300 } }
    if slug == "herbalism" or slug == "mining" then
        local grp = (slug == "herbalism") and HERB_GRP or MINE_GRP
        local function GrpOf(s)
            local cur
            for _, rg in ipairs(grp) do
                if rg[1] <= s then cur = rg else break end
            end
            return cur or grp[1]
        end
        local merged = {}
        for _, t in ipairs(g) do
            local last = merged[#merged]
            if last and last[5] == GrpOf(t[2]) then
                local seen = {}
                for _, id in ipairs(last[1]) do seen[id] = true end
                for _, id in ipairs(t[1]) do
                    if not seen[id] then last[1][#last[1] + 1] = id end
                end
                local zs = {}
                for _, z in ipairs(last[3]) do zs[z[1]] = math.max(zs[z[1]] or 0, z[2]) end
                for _, z in ipairs(t[3]) do zs[z[1]] = math.max(zs[z[1]] or 0, z[2]) end
                local zl = {}
                for zid, cnt in pairs(zs) do zl[#zl + 1] = { zid, cnt } end
                table.sort(zl, function(a, b) return a[2] > b[2] end)
                for k = #zl, 7, -1 do zl[k] = nil end
                last[3] = zl
                last[4] = true
            else
                merged[#merged + 1] = { t[1], t[2], t[3], nil, GrpOf(t[2]) }
            end
        end
        g = merged
    end
    while gi <= #g do
        local t = g[gi]
        local lo, hi, ids, zones
        if slug == "skinning" then
            local rng = SKIN_SKILL[t[1][1]] or { t[1][1], t[1][2] }
            lo, hi, ids, zones = rng[1], rng[2], t[2], t[3]
        else
            lo, ids, zones = t[2], t[1], t[3]
            if t[5] then
                lo, hi = t[5][1], t[5][2]
            else
                hi = (g[gi + 1] and g[gi + 1][2] or 301) - 1
                if hi < lo then hi = lo end
            end
        end
        while not t[5] and g[gi + 1] do
            local nx = g[gi + 1]
            if not (GrSameSeg(ids, (slug == "skinning") and nx[2] or nx[1])
                    and PD.ZoneText(zones) == PD.ZoneText(nx[3])) then break end
            if slug == "skinning" then
                if nx[1][1] ~= t[1][2] + 1 then break end
                hi = (SKIN_SKILL[nx[1][1]] or { nil, nx[1][2] })[2]
            else
                hi = (g[gi + 2] and g[gi + 2][2] or 301) - 1
                if hi < lo then hi = lo end
            end
            gi = gi + 1
        end
        local active = curLv and curLv >= lo and curLv <= hi
        local headId = ids[1]
        local nm
        if t[4] then
            local nms = {}
            for _, id in ipairs(ids) do
                local on = DG.ItemName(id)
                nms[#nms + 1] = (type(on) == "string" and on ~= "") and on or format(L["物品 #%d"], id)
            end
            nm = table.concat(nms, "、")
        else
            nm = DG.ItemName(headId)
            if not (type(nm) == "string" and nm ~= "") then nm = format(L["物品 #%d"], headId) end
        end
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H1, gr3 = true,
            it = { headId }, qItem = headId,
            lv = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),
            loc = format(L["大多在 %s"], PD.ZoneText(zones)),
            text = nm,
            icons = (slug == "herbalism" or slug == "mining") and ids or nil,
            nameColor = active and GR_GREEN or nil,
        }
        gi = gi + 1
    end
end

local function ClipFixedSteps(steps, target)
    if not target or target >= 300 then
        return steps, false
    end
    local out, clipped = {}, false
    for _, st in ipairs(steps or {}) do
        local a, b = st[1], st[2]
        if a > target then break end
        local nb, nq = math.min(b, target), st[4] or 0
        local isClip = b > target
        if isClip then
            nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))
            clipped = true
        end
        out[#out + 1] = { a, nb, st[3], nq, _clip = isClip or nil }
    end
    return out, clipped
end

local function FixedShopData(target)
    local lv = LV[PD.cur]
    local steps, clipped = ClipFixedSteps(lv.steps or {}, target)
    if RA and RA.SummarizeSteps then
        local sum = RA.SummarizeSteps(steps, PD.cur,
                                      { learnedOnly = PD.Setting("autoLearnedOnly") })
        if sum then
            sum.mode = "fixed"
            sum.target = target
            sum.clipped = clipped
            return sum
        end
    end
    return { mode = "fixed", target = target, mats = lv.shopping or {},
             steps = lv.steps or {}, priced = false }
end

local function CountUnpriced(sum)
    local n = 0
    for _, e in ipairs(sum.mats or {}) do if e.unpriced then n = n + 1 end end
    for _, f in ipairs(sum.formulas or {}) do if f.unpriced then n = n + 1 end end
    return n
end

function PD.RowsLeveling(rows)
    local lv = LV[PD.cur]
    if not lv then PD.lvSummary = nil; PD.lvRouteHead = nil return end
    PD.lvRouteHead = nil

    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil
    local greyOn = PD.Setting("greyPassed")

    local scheme = PD.SettingRaw("autoScheme")
    local autoOn = (PD.cur ~= "poisons") and PD.Setting("autoRoute") and RA
                    and (scheme == "optim" or RA.Available()) and true or false
    local target = PD.LvTarget()
    local res
    if autoOn then
        local opts = {
            start = (PD.Setting("autoFromCurrent") and curLv) and math.max(1, curLv) or 1,
            onlyAH = PD.Setting("autoOnlyAH"),
            noFormula = PD.Setting("autoNoFormula"),
            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = target,
            scheme = scheme,
        }
        res = RA.Get(PD.cur, opts)
        if res and not res.priced and scheme ~= "optim" then res = nil end
    end
    local auto = (autoOn and res) and true or false

    if PD.autoPage == "shop" then
        local data = auto and res or FixedShopData(target)
        PD.lvSummary = {
            target = target, auto = auto,
            scheme = auto and res.scheme or nil,
            autoSetting = PD.Setting("autoRoute"),
            ahOK = (RA and RA.Available()) and true or false,
            priced = (data.priced and true) or false,
            total = data.total, snapshotAge = data.snapshotAge,
            snapshotDays = data.snapshotDays,
            matsN = #(data.mats or {}), np = CountUnpriced(data),
        }
        PD.RowsAutoShop(rows, data)
        return
    end

    local recOf = {}
    local rr = RGet(PD.cur)
    if rr and rr.rows then
        for _, r in ipairs(rr.rows) do recOf[r[1]] = r end
    end
    local rin = lv.rinfo
    for spell, ri in pairs(rin or {}) do
        if not recOf[spell] then recOf[spell] = ri end
    end

    local steps, clipped
    if auto then
        steps = res.steps
    else
        steps, clipped = ClipFixedSteps(lv.steps or {}, target)
    end
    local fixedSum = (not auto) and RA and RA.SummarizeSteps(steps, PD.cur,
                          { learnedOnly = PD.Setting("autoLearnedOnly") }) or nil

    PD.lvSummary = {
        target = target, auto = auto,
        scheme = auto and res.scheme or nil,
        autoSetting = PD.Setting("autoRoute"),
        ahOK = (RA and RA.Available()) and true or false,
        priced = auto or ((fixedSum and fixedSum.priced) and true or false),
        total = auto and res.total or (fixedSum and fixedSum.total),
        snapshotAge = auto and res.snapshotAge or (fixedSum and fixedSum.snapshotAge),
        snapshotDays = auto and res.snapshotDays or (fixedSum and fixedSum.snapshotDays),
        recipes = auto and #res.steps or nil,
        crafts = auto and (res.crafts or 0) or nil,
        vendorTotal = auto and res.vendorTotal or (fixedSum and fixedSum.vendorTotal),
        formulasTotal = auto and res.formulasTotal or (fixedSum and fixedSum.formulasTotal),
        matsN = (not auto) and fixedSum and #(fixedSum.mats or {}) or nil,
        np = auto and CountUnpriced(res) or (fixedSum and CountUnpriced(fixedSum)) or 0,
    }

    local cntOf, unitOf, totOf = {}, {}, {}
    local cardOf = {}
    local rngW, nameW, cntW, unitW, totW, matNeed, cardNeed = 0, 0, 0, 0, 0, 0, 0
    for _, st in ipairs(steps or {}) do
        local rec = recOf[st[3]]
        if not rec and rin then rec = rin[st[3]] end
        local riM
        if rec and rec.mats then riM = rec; rec = nil end
        local _ye = (rec and tonumber(rec[8])) or (riM and tonumber(riM.yellow))
        local det = (_ye and st[2] <= _ye) or false
        local priced = auto or fixedSum
        local cntStr = det and format(L["%d 次制作"], st[4] or 0)
                       or format(L["~%s 次制作"], tostring(st[4]))
        local unitStr, totStr = "", ""
        if priced then
            local crafts = math.max(1, st[4] or 1)
            if st.unpriced or (st.cost or 0) <= 0 then
                if not det then cntStr = format(L["≈%d 次制作"], st[4] or 0) end
                totStr = L["价格未知"]
            elseif st.est then
                if not det then cntStr = format(L["≈%d 次制作"], st[4] or 0) end
                unitStr = "≈" .. RA.MoneyStr(math.ceil((st.cost or 0) / crafts))
                totStr = "≈" .. RA.MoneyStr(st.cost)
            else
                if not det then cntStr = format(L["~%d 次制作"], st[4] or 0) end
                unitStr = RA.MoneyStr(math.ceil((st.cost or 0) / crafts))
                totStr = RA.MoneyStr(st.cost)
            end
            if clipped and st._clip then
                cntStr = cntStr .. format(L[" · 按目标 %d 折算"], target)
            end
        end
        cntOf[st] = cntStr
        unitOf[st] = unitStr
        totOf[st] = totStr
        local w = PD.TextW(format(L["%s – %s"], tostring(st[1]), tostring(st[2])), PD.LV_FS)
        if w > rngW then rngW = w end
        local nw = PD.TextW(SpellName(st[3]), PD.LV_FS)
        if nw > nameW then nameW = nw end
        local cw = PD.TextW(cntStr, PD.LV_FS)
        if cw > cntW then cntW = cw end
        local uw = unitStr ~= "" and PD.TextW(unitStr, 11) or 0
        if uw > unitW then unitW = uw end
        local tw = totStr ~= "" and PD.TextW(totStr, PD.LV_FS) or 0
        if tw > totW then totW = tw end
        local _, mw = PD.PackMats((rec and rec[12]) or (riM and riM.mats) or {}, 1e9)
        if mw + PD.TBL_MARK_W > matNeed then matNeed = mw + PD.TBL_MARK_W end
        local cd = PD.CardOf(rec, riM or (rin and rin[st[3]] or nil))
        cardOf[st] = cd
        if cd then
            local cwd = PD.TextW(cd.text, 10) + 2 * PD.CARD_PAD
            if cwd > cardNeed then cardNeed = cwd end
        end
    end
    local rowW = PD.RIGHT_W - 2 * PD.LIST_PAD
    PD.LV_ROW_W = rowW
    PD.LV_ICON_X = 6 + math.ceil(rngW) + PD.TBL_RNG_GAP
    PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP
    if auto or fixedSum then
        local hw = PD.TextW(L["制作次数"], PD.LV_FS)
        if hw > cntW then cntW = hw end
        hw = PD.TextW(L["单次花费"], 11)
        if hw > unitW then unitW = hw end
        hw = PD.TextW(L["总花费"], PD.LV_FS)
        if hw > totW then totW = hw end
    end
    PD.LV_CNT_W = math.max(40, math.ceil(cntW))
    PD.LV_UNIT_W = math.ceil(unitW)
    PD.LV_TOT_W = math.ceil(totW)
    PD.LV_CARD_FIXW = math.ceil(cardNeed)
    local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP
                  - PD.LV_CNT_W - PD.LV_UNIT_W - PD.LV_TOT_W
                  - PD.TBL_CNT_GAP - 2 * PD.LV_COL_GAP
    PD.LV_NAME_W = math.min(PD.TBL_NAME_MAX, math.max(PD.TBL_NAME_MIN, math.ceil(nameW)))
    if avail - PD.LV_NAME_W < matNeed then
        PD.LV_NAME_W = math.max(PD.TBL_NAME_MIN, avail - matNeed)
    end
    PD.LV_MAT_W = avail - PD.LV_NAME_W
    PD.LV_CNT_R = PD.TBL_MAT_RPAD + PD.LV_MAT_W + PD.TBL_CNT_GAP
    PD.LV_UNIT_R = PD.LV_CNT_R + PD.LV_TOT_W + PD.LV_COL_GAP
    PD.LV_CNT2_R = PD.LV_UNIT_R + PD.LV_UNIT_W + PD.LV_COL_GAP

    local function FitName(s)
        return PD.Fit(s, PD.LV_FS, PD.LV_NAME_W)
    end
    local function FitR(s) return PD.Fit(s, 13, PD.COL_RW - 66) end

    if autoOn and not auto then
        PushHead(rows, L["自动路线不可用"])
        PushText(rows, L["自动路线需要 Auctionator 的价格数据：请安装 Auctionator 并完成一次拍卖行扫描；当前显示固定路线。"],
                 12, C_GREY)
        PushGap(rows, 4)
    end

    if steps and #steps > 0 then
        if auto then
            local warn = {}
            for _, st in ipairs(res.steps or {}) do
                if st.est then
                    warn[#warn + 1] = { format(L["缺口 %d–%d 已按估价回填（配方含无价材料，花费为下限）"],
                                          st[1], st[2]), 0.95, 0.75, 0.4 }
                end
            end
            for _, g in ipairs(res.gaps or {}) do
                warn[#warn + 1] = { format(L["缺口：%d–%d 无符合筛选的配方（可放宽设置重算）"], g[1], g[2]),
                                    0.95, 0.55, 0.45 }
            end
            local np = CountUnpriced(res)
            if np > 0 then
                warn[#warn + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], np), 0.95, 0.75, 0.4 }
            end
            PD.lvRouteHead = {
                text = format(L["1 → %d 自动路线（按拍卖行价格）"], target),
                warn = (#warn > 0) and warn or nil,
            }
            PushGap(rows, 4)
        else
            local warn = {}
            if fixedSum and not fixedSum.priced then
                warn[#warn + 1] = { L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"], 0.7, 0.7, 0.7 }
            elseif fixedSum then
                local np = CountUnpriced(fixedSum)
                if np > 0 then
                    warn[#warn + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], np), 0.95, 0.75, 0.4 }
                end
            end
            if clipped then
                warn[#warn + 1] = { format(L["目标 %d 之后的段落已省略，跨目标段的制作数量按比例折算。"], target),
                                    0.7, 0.7, 0.7 }
            end
            local hd = { kind = "head", text = format(L["1 → %d 分段路线"], target) }
            if #warn > 0 then hd.warn = warn end
            rows[#rows + 1] = hd
            PushGap(rows, 4)
        end
        if auto or fixedSum then
            rows[#rows + 1] = { kind = "lvhead", h = 18, col = 1, noTip = true }
        end
        for _, st in ipairs(steps) do
            local rec = recOf[st[3]]
            local ri = nil
            if rec and rec.mats then
                ri = rec
                rec = nil
            elseif not rec then
                ri = rin and rin[st[3]] or nil
            end
            local mats = (rec and rec[12]) or (ri and ri.mats) or {}
            local nm = SpellName(st[3])
            local src = PD.LevelSrc(rec)
            if not rec and ri then
                src = ri.trainer and L["向训练师学习"] or nil
            end
            local blocks, _, cut = PD.PackMats(mats, PD.LV_MAT_W)
            local segLo = tonumber(st[1])
            local segHi = tonumber(st[2])
            local over = (curLv ~= nil and segHi ~= nil and segHi < curLv) or nil
            local passed = (greyOn and over) or nil
            rows[#rows + 1] = {
                kind = "row", h = PD.TBL_H, col = 1, lvstep = true,
                passed = passed, over = over,
                it = (rec and rec[2]) and { rec[2] }
                     or ((ri and ri.makes) and { ri.makes } or nil),
                icon = ((not rec) and ri and not ri.makes) and SpellIcon(st[3]) or nil,
                tipExtra = (rec and rec[2])
                           and function() return PD.PriceTipLines(rec[2], rec[12]) end
                           or ((ri and ri.makes and ri.mats)
                               and function() return PD.PriceTipLines(ri.makes, ri.mats) end
                               or nil),
                noTip = true,
                rng = format(L["%s – %s"], tostring(st[1]), tostring(st[2])),
                text = FitName(nm),
                src = src,
                cnt = cntOf[st] or format(L["~%s 次制作"], tostring(st[4])),
                unit = unitOf[st] or "",
                tot = totOf[st] or "",
                blocks = blocks, matCut = cut,
                _mats = mats,
                sbVals = (rec and (rec[7] or rec[8] or rec[9] or rec[10]))
                         and { rec[7], rec[8], rec[9], rec[10] }
                         or (ri and (ri.yellow or ri.grey))
                            and { ri.learn, ri.yellow, ri.green, ri.grey } or nil,
                sbLo = segLo, sbHi = segHi,
                card = cardOf[st],
            }
        end
    end
    if PD.Setting("hlCurrent") and curLv ~= nil then
        for _, spec in ipairs(rows) do
            if spec.lvstep and spec.over == nil then
                spec.cur = true
                break
            end
        end
    end
end

function PD.RowsAutoShop(rows, data)
    local mode = data.mode or "auto"
    local mats = data.mats or {}
    local lw = PD.splitLW or PD.COL_LW
    local priced = data.priced and true or false

    local title
    if mode == "auto" then
        title = L["购物清单（自动路线）"]
    else
        title = format(L["购物清单（固定路线 1–%d）"], data.target or 300)
    end
    if #mats == 0 then
        PushHead(rows, title, 1)
        PushText(rows, L["没有需要准备的材料。"], 12, C_GREY, 1)
        return
    end

    PushHead(rows, title, 1)
    PushHead(rows, format(L["材料（%d 种）"], #mats), 1)
    local firstAt = data.firstAt or {}
    for _, e in ipairs(mats) do
        local id, n = e[1], e[2]
        local fa = firstAt[id]
        local seg
        if fa then
            for _, st in ipairs(data.steps or {}) do
                if st[1] <= fa and fa <= st[2] then seg = st break end
            end
        end
        local sub
        if seg then sub = format(L["首用于 %d–%d 段"], seg[1], seg[2]) end
        local tag = e.vendor and { text = L["直售"] } or nil
        local right, right2
        if priced and not e.unpriced then
            right = format(L["×%d · %s"], n or 0, RA.MoneyStr(e.unit, "copper"))
            right2 = RA.MoneyStr(e.cost, "copper")
        else
            right = format("×%d", n or 0)
            right2 = e.unpriced and L["价格未知"] or nil
        end
        local tip = { { format(L["需要：%d"], n or 0) },
                      e.unpriced
                          and { L["价格未知（Auctionator 无记录）"], 0.95, 0.75, 0.4 }
                          or { format(L["约 %s"], RA.MoneyStr(e.cost, "copper")), 1, 0.82, 0 },
                      { sub or "", 0.7, 0.7, 0.7 } }
        if e.vendor then
            tip[#tip + 1] = { L["商人直售（军需官处直购，无需拍卖行）"], 0.42, 0.94, 0.62 }
        end
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H, col = 1, it = { id },
            text = PD.Fit(DG.ItemName(id), 13, lw - 130),
            sub = sub,
            tag = tag,
            right = right,
            right2 = right2,
            lines = tip,
        }
    end

    local fl = data.formulas or {}
    if #fl > 0 then
        PushGap(rows, 8, 1)
        PushHead(rows, format(L["图纸（一次性）（%d 个）"], #fl), 1)
        for _, f in ipairs(fl) do
            local sub
            if f.spell then sub = format(L["配方：%s"], SpellName(f.spell)) end
            if f.vendor then
                sub = sub and (sub .. L[" · 商人可购"]) or L["商人可购"]
            end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1, it = { f.id },
                text = PD.Fit(DG.ItemName(f.id) or L["未知图纸"], 13, lw - 130),
                sub = sub,
                right = "×1",
                right2 = (priced and not f.unpriced) and RA.MoneyStr(f.cost, "copper") or L["价格未知"],
                lines = { { L["图纸只买一次，已计入合计"], 1, 0.82, 0 },
                          f.unpriced
                              and { L["价格未知（Auctionator 无记录）"], 0.95, 0.75, 0.4 }
                              or { format(L["约 %s"], RA.MoneyStr(f.cost, "copper")), 1, 0.82, 0 } },
            }
        end
    end

    local totalN = 0
    for _, e in ipairs(mats) do totalN = totalN + (e[2] or 0) end
    local snapSec, snapDays = data.snapshotAge, data.snapshotDays
    PushGap(rows, 8, 2)
    PushHead(rows, L["总共需要"], 2)
    if priced then
        PushText(rows, RA.MoneyStr(data.total, "copper"), 20, C_GOLD, 2)
    else
        PushText(rows, L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"], 12, C_GREY, 2)
    end
    PushText(rows, format(L["共 %d 种材料 · 合计 %d 件"], #mats, totalN), 11, C_GREY, 2)
    local atxt
    if snapSec then
        if snapSec < 60 then
            atxt = L["价格快照：刚刚（Auctionator）"]
        elseif snapSec < 90 * 60 then
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(snapSec / 60 + 0.5)))
        elseif snapSec < 48 * 3600 then
            atxt = format(L["价格快照 %d 小时前（Auctionator）"], math.max(1, math.floor(snapSec / 3600 + 0.5)))
        else
            atxt = format(L["价格快照 %d 天前（Auctionator）"], math.floor(snapSec / 86400 + 0.5))
        end
    elseif snapDays then
        atxt = (snapDays <= 0) and L["价格快照：今天（Auctionator）"]
               or format(L["价格快照 %d 天前（Auctionator）"], snapDays)
    else
        atxt = L["价格快照年龄未知（Auctionator）"]
    end
    PushText(rows, atxt, 11, C_GREY, 2)
    if priced then
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["拍卖行购入"], right = RA.MoneyStr(data.ahTotal or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["图纸购入"], right = RA.MoneyStr(data.formulasTotal or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["商人直售购入"], right = RA.MoneyStr(data.vendorTotal or 0, "copper") }
        local np = CountUnpriced(data)
        if np > 0 then
            PushText(rows, format(L["含无价材料 %d 种：总花费为估算下限"], np), 11,
                     { 0.95, 0.75, 0.4 }, 2)
        end
    end
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H1, col = 2,
        text = L["一键导入 Auctionator →"],
        lines = { { L["点击在 Auctionator 生成购物清单；同名清单会被覆盖"], 1, 0.82, 0 } },
        act = function() PD.ShopImport(data) end,
    }
    PD.hasSecs = true
    for i = #rows, 1, -1 do
        local sp = rows[i]
        if sp.kind == "gap" and sp.col == 2 and sp.h <= 4 then
            sp.sec = 1
            sp.goldSec = true
        elseif sp.kind ~= "gap" and sp.col == 2 then
            sp.sec = 1
            sp.goldSec = true
        else
            break
        end
    end
    PD.secCount = 1

    if priced then
        PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
        PushHead(rows, L["产物收益"], 2)
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["产物丢拍卖行收益"],
                            right = RA.MoneyStr(data.productAH or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["直接卖给NPC收益"],
                            right = RA.MoneyStr(data.productNPC or 0, "copper") }
        local net = (data.total or 0) - (data.productAH or 0)
        if net >= 0 then
            rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                                text = L["净花费（产物丢拍卖行）"],
                                right = RA.MoneyStr(net, "copper") }
        else
            rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                                text = L["净花费（产物丢拍卖行）"],
                                right = format(L["净赚 %s"], RA.MoneyStr(-net, "copper")) }
        end
        if data.productPartial then
            PushText(rows, L["部分产物无拍卖行价格：收益为估算下限"], 11,
                     { 0.95, 0.75, 0.4 }, 2)
        end
        PushGap(rows, 2, 2)
        for i = #rows, 1, -1 do
            local sp = rows[i]
            if sp.kind == "gap" and sp.col == 2 and sp.h <= 4 then
                sp.sec = 2
                sp.goldSec = true
            elseif sp.kind ~= "gap" and sp.col == 2 then
                sp.sec = 2
                sp.goldSec = true
            else
                break
            end
        end
        PD.secCount = 2
    end
end

function PD.ShopImport(data)
    local AB = ns.AuctionBridge
    if not (AB and AB.DoImport) then return end
    local p = D.pro[PD.cur]
    local items = {}
    for _, e in ipairs(data.mats or {}) do
        local nm = DG.ItemName(e[1])
        if nm then items[#items + 1] = { name = nm, need = e[2] } end
    end
    for _, f in ipairs(data.formulas or {}) do
        local nm = DG.ItemName(f.id)
        if nm then items[#items + 1] = { name = nm, need = 1 } end
    end
    AB.DoImport(p and p.name or "?", items)
end

function PD.LevelTool()
    local list = {
        { key = "page_route", text = L["路线"],     on = PD.autoPage ~= "shop" },
        { key = "page_shop",  text = L["购物清单"], on = PD.autoPage == "shop" },
        { key = "recalc",     text = L["重新计算"] },
    }
    if PD.cur == "poisons" then
        local keep = {}
        for _, b in ipairs(list) do
            if b.key ~= "recalc" then keep[#keep + 1] = b end
        end
        list = keep
    end
    return list, function(k)
        if k == "page_route" then
            PD.autoPage = "route"
        elseif k == "page_shop" then
            PD.autoPage = "shop"
        elseif k == "recalc" then
            if RA then RA.Invalidate() end
        end
        PD.RequestRender()
    end
end

function PD.RowsSettings(rows)
    PushHead(rows, L["升级页设置"])
    PushGap(rows, 2)
    PushText(rows, L["这里的开关只作用于「升级」页签里的制作路线（升级路线表），不影响其他页签。"], 11, C_GREY)
    PushGap(rows, 4)
    local defs = {
        { k = "greyPassed", name = L["已过段落灰显"],
          desc = L["上限低于当前技能的段落（如 42 级时的 1~15）整行灰显"],
          d1 = L["开启后：段名、出处、数量文字变暗，配方与材料图标去饱和，不再作为下一个要关注的制作目标；"],
          d2 = L["关闭后：所有段落恢复常规配色，不做灰显处理。"] },
        { k = "hlCurrent", name = L["当前段落高亮"],
          desc = L["上下限跨着当前技能的段落（如下一个要练的 15~58）加一圈主题色外框"],
          d1 = L["开启后：下一个要练的段落四周显示一圈主题绿描边，一眼定位当前制作路线；外框只是描边，不影响行内容与点击。"],
          d2 = L["关闭后：不显示外框，该段落样式与其他行一致。"] },
        { k = "autoRoute", name = L["自动计算路线（按拍卖行价格）"],
          desc = L["关闭 = 显示固定路线；开启 = 依据 Auctionator 价格计算最省钱的制作路线"],
          d1 = L["需要安装 Auctionator 并完成一次拍卖行扫描；不可用时自动回落固定路线。"],
          d2 = L["路线与购物清单在「升级」页签顶部的按钮切换。"] },
        { k = "autoOnlyAH", name = L["只使用拍卖行可购材料的配方"],
          desc = L["材料在拍卖行/商人都查不到价格时，该配方不参与计算（商人直售材料不受限）"],
          d1 = L["开启：路线更可靠，但可能出现无配方可用的缺口区间。"],
          d2 = L["关闭：缺口区间会改用无价材料的配方补位，花费按已知价格估算（行内打 ? 标记）。"] },
        { k = "autoNoFormula", name = L["排除需要图纸的配方"],
          desc = L["跳过掉落图纸类配方；图纸可从商人购买的配方仍会使用"],
          d1 = L["开启：只使用训练师直学与商人图纸配方，开荒最稳。"],
          d2 = L["关闭：掉落图纸配方也会参与，可能更便宜但要自己刷图纸。"] },
        { k = "autoLearnedOnly", name = L["仅使用已学习的配方"],
          desc = L["只在本角色已学会的配方中挑选"],
          d1 = L["开启：路线里的每一段都能立刻开做。"],
          d2 = L["关闭：按「学会全部候选配方」的理想情况计算。"] },
        { k = "autoFromCurrent", name = L["从当前技能开始计算"],
          desc = L["开启 = 只算当前技能到 300 的路线；关闭 = 从 1 全量重算整条路线（预估全程花费）"],
          d1 = L["开启：适合练级中途打开手册直接照着做。"],
          d2 = L["关闭：查看从零开始的最优路线与总花费。"] },
    }
    if PD.cur == "poisons" then
        local keep = { greyPassed = true, hlCurrent = true }
        local filt = {}
        for _, d in ipairs(defs) do
            if keep[d.k] then filt[#filt + 1] = d end
        end
        defs = filt
    end
    for _, d in ipairs(defs) do
        rows[#rows + 1] = {
            kind = "row", h = 40, col = 1,
            text = d.name,
            togKey = d.k,
            help = { { d.name }, { d.desc, 0.7, 0.7, 0.7 }, { d.d1, 0.7, 0.7, 0.7 }, { d.d2, 0.7, 0.7, 0.7 } },
        }
        PushGap(rows, 6)
    end
end

function PD.PlaceSettingsToggles(rows)
    local n = math.min(#(rows or {}), PD.ROW_CAP)
    local ti = 0
    for i = 1, n do
        local spec = rows[i]
        local rr = PD.rows[i]
        if PD.setOpen and spec.togKey and rr then
            ti = ti + 1
            local tg = PD.setToggles[ti]
            tg:ClearAllPoints()
            tg:SetPoint("RIGHT", rr, "RIGHT", -8, 0)
            tg:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
            tg:SetChecked(PD.Setting(spec.togKey))
            tg.__key = spec.togKey
            tg:Show()
            local hp = PD.setHelps[ti]
            if hp then
                hp:ClearAllPoints()
                hp:SetPoint("LEFT", rr.a, "RIGHT", 6, -1)
                hp:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
                hp.__tip = spec.help
                hp:SetShown(spec.help and true or false)
            end
        end
    end
    for j = ti + 1, #PD.setToggles do PD.setToggles[j]:Hide() end
    for j = ti + 1, #PD.setHelps do PD.setHelps[j]:Hide() end
end

PD.CRATE_SPLIT = 0.60
PD.CRATE_OWN_R = 100
PD.OWN_SHIFT = 0.08
function PD.OwnR()
    local lw = tonumber(PD.splitLW) or tonumber(PD.COL_LW) or 0
    return PD.CRATE_OWN_R + math.floor(lw * PD.OWN_SHIFT)
end
PD.crateSel = nil
PD.writSel = nil
PD.crateSort = "total"
PD.writSort = "total"
PD.plunderSel = nil
PD.plunderSort = "cost"
PD.recipeSort = nil
PD.recipeSortDesc = false

local PLUNDER_CATS = {
    ingot = L["锭与石材"], herb = L["草药"], leather = L["皮革"],
    enchant = L["附魔材料"], potion = L["药水与药剂"], food = L["食物"],
    bandage = L["绷带"], device = L["炸弹与装置"], gear = L["武器与护甲"],
    other = L["其他"], mismatch = L["数据不一致"],
}

local CRATE_TIERS = { L["学徒"], L["熟练"], L["专家"], L["工匠"] }
local CRATE_GREEN = { 0.25, 0.85, 0.25 }

local function CrateOptCost(itemId, qty)
    local p = RA.AHPriceOf and RA.AHPriceOf(itemId) or nil
    if not p then return nil end
    return p * (qty or 1)
end

local function CrateSnapText()
    if not (RA.HasPriceData and RA.HasPriceData()) then
        return L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"]
    end
    local sec = RA.SnapshotAge and RA.SnapshotAge() or nil
    if not sec then return L["价格快照年龄未知（Auctionator）"] end
    if sec >= 48 * 3600 then
        return L["价格快照数据过期，距离上次扫描超过 2 天上限，需要重新扫描"]
    end
    if sec < 60 then return L["价格快照：刚刚（Auctionator）"] end
    if sec < 90 * 60 then
        return format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(sec / 60 + 0.5)))
    end
    if sec < 48 * 3600 then
        return format(L["价格快照 %d 小时前（Auctionator）"], math.max(1, math.floor(sec / 3600 + 0.5)))
    end
    return format(L["价格快照 %d 天前（Auctionator）"], math.floor(sec / 86400 + 0.5))
end

local function CrateMetaRow(rows, label, val, valOk, fs)
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = fs,
        text = label,
        right = valOk and RA.MoneyStr(val) or "—",
        rightColor = valOk and C_TEXT or C_GREY,
    }
end

function PD.CrateRows(rows)
    local list = CD.crates or {}
    if not PD.crateSel and list[1] then PD.crateSel = list[1].id end
    local sel = PD.crateSel
    local owns, bests = {}, {}
    for i, c in ipairs(list) do
        local own = RA.AHPriceOf and RA.AHPriceOf(c.id) or nil
        local mat
        for _, o in ipairs(c.opts or {}) do
            local v = CrateOptCost(o[1], o[2])
            if v and (not mat or v < mat) then mat = v end
        end
        owns[i] = own
        bests[i] = (own and mat) and (own + mat) or nil
    end
    local mode = PD.crateSort
    local order = {}
    for i = 1, #list do order[i] = i end
    if mode then
        local key = (mode == "own") and owns or bests
        table.sort(order, function(a, b)
            local ca, cb = key[a], key[b]
            if ca and cb then return ca < cb end
            if ca or cb then return ca ~= nil end
            return (list[a].id or 0) < (list[b].id or 0)
        end)
    end
    rows[#rows + 1] = { kind = "colhead", col = 1, h = PD.TEXT_H,
                        text = L["名称"], right = L["总价格"], ownRight = L["自身价格"],
                        sortOn = (mode == "total"), ownOn = (mode == "own"),
                        act = function()
                            PD.crateSort = (mode ~= "total") and "total" or nil
                            PD.RequestRender()
                        end,
                        ownAct = function()
                            PD.crateSort = (mode ~= "own") and "own" or nil
                            PD.RequestRender()
                        end }
    for _, i in ipairs(order) do
        local c = list[i]
        rows[#rows + 1] = {
            kind = "row", col = 1, h = PD.ROW_H,
            it = { c.id }, qItem = c.id,
            text = PD.ItemName(c.id),
            sub = CRATE_TIERS[c.tier] or "?",
            right = bests[i] and RA.MoneyStr(bests[i]) or "",
            rightOwn = owns[i] and RA.MoneyStr(owns[i]) or "",
            rightOwnColor = C_TEXT,
            cur = (c.id == sel),
            act = function()
                if PD.crateSel ~= c.id then PD.crateSel = c.id; PD.RequestRender() end
            end,
        }
    end
    local sc
    for _, c in ipairs(list) do if c.id == sel then sc = c break end end
    if not sc then return end
    PD.secPadL = 0
    local secH = #rows + 1
    rows[#rows + 1] = {
        kind = "head", col = 2, h = 28, fs = 16,
        it = { sc.id },
        text = PD.ItemName(sc.id),
    }
    local favTxt = sc.favor and format(L["青睐 +%d"], sc.favor) or L["青睐未验证"]
    PushText(rows, favTxt .. format(L[" · 需等级 %d"], sc.level or 0), 12, C_GREY, 2)
    MarkSec(rows, secH, #rows, 1)
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secO = #rows + 1
    PushHead(rows, L["凑法（任满其一）"], 2)
    local opts, cheapest, cheapestOpt = {}, nil, nil
    for _, o in ipairs(sc.opts or {}) do opts[#opts + 1] = o end
    for _, o in ipairs(opts) do
        local v = CrateOptCost(o[1], o[2])
        if v and (not cheapest or v < cheapest) then cheapest, cheapestOpt = v, o end
    end
    table.sort(opts, function(a, b)
        local ca, cb = CrateOptCost(a[1], a[2]), CrateOptCost(b[1], b[2])
        if ca and cb then return ca < cb end
        if ca or cb then return ca ~= nil end
        return a[1] < b[1]
    end)
    for _, o in ipairs(opts) do
        local v = CrateOptCost(o[1], o[2])
        local isBest = cheapestOpt and o[1] == cheapestOpt[1] and o[2] == cheapestOpt[2]
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
            it = { o[1] }, qItem = o[1],
            text = PD.ItemName(o[1]) .. " ×" .. (o[2] or 1),
            tag = isBest and { text = L["最省"], color = CRATE_GREEN } or nil,
            right = v and RA.MoneyStr(v) or "—",
            rightColor = isBest and CRATE_GREEN or (v and C_TEXT or C_GREY),
            tipExtra = function() return PD.PriceTipLines(o[1]) end,
        }
    end
    MarkSec(rows, secO, #rows, 2)
    local own = RA.AHPriceOf and RA.AHPriceOf(sc.id) or nil
    if not cheapestOpt and opts[1] then cheapestOpt = opts[1] end
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secS = #rows + 1
    PushHead(rows, L["总结"], 2)
    CrateMetaRow(rows, L["自身成本"], own, own, 14)
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
        text = cheapestOpt and format(L["购买 %s"],
                 PD.MatIconTex(cheapestOpt[1], 14) .. " " .. PD.ItemName(cheapestOpt[1])
                 .. " ×" .. (cheapestOpt[2] or 1)) or "—",
        right = cheapest and RA.MoneyStr(cheapest) or "—",
        rightColor = cheapest and CRATE_GREEN or C_GREY,
        tipExtra = cheapestOpt and function() return PD.PriceTipLines(cheapestOpt[1]) end or nil,
    }
    local total = (own and cheapest) and (own + cheapest) or nil
    CrateMetaRow(rows, L["合计"], total, total, 14)
    if total and (sc.favor or 0) > 0 then
        CrateMetaRow(rows, L["每点青睐的最低成本"], total / sc.favor, true, 14)
    end
    MarkSec(rows, secS, #rows, 3)
    PD.hasSecs = true
    PD.secCount = 3
    PushText(rows, CrateSnapText(), 11, C_GREY, 2)
end

local function CraftAllMap()
    if PD.craftAll and next(PD.craftAll) then return PD.craftAll end
    if not R then RGet(nil) end
    local map = {}
    for slug, d in pairs(R or {}) do
        if type(d) == "table" and type(d.rows) == "table" then
            for _, rec in ipairs(d.rows) do
                local iid = rec[2]
                if type(iid) == "number" and type(rec[12]) == "table" and #rec[12] > 0
                   and not map[iid] then
                    map[iid] = { rec = rec, slug = slug }
                end
            end
        end
    end
    if next(map) then PD.craftAll = map end
    return map
end

local function WritBadge(cinfo, learned)
    if not cinfo then return nil end
    if RA.SpellKnown and RA.SpellKnown(cinfo.rec[1]) then
        return { text = L["已学"], color = { 1, 0.82, 0 } }
    end
    if learned[cinfo.slug] then
        return { text = L["本专业"] }
    end
    local p = D.pro and D.pro[cinfo.slug]
    return { text = p and p.name or cinfo.slug, color = { 0.55, 0.57, 0.62 } }
end

function PD.WritRows(rows)
    PD.secPadL = 0
    local list = CD.writs or {}
    local order, owns, priced, craftT, pcts = {}, {}, {}, {}, {}
    local craftMap = CraftAllMap()
    for i = 1, #list do
        order[i] = i
        local wid = list[i].item or list[i].target
        local own = RA.AHPriceOf and RA.AHPriceOf(wid) or nil
        local mu = RA.AHPriceOf and RA.AHPriceOf(list[i].target) or nil
        owns[i] = own
        priced[i] = (own and mu) and (own + mu * (list[i].qty or 1)) or nil
        local ci = craftMap[list[i].target]
        local csum, ok
        if ci and ci.rec then
            csum, ok = 0, true
            for _, m in ipairs(ci.rec[12]) do
                local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
                if p then csum = csum + p * (m[2] or 1) else ok = false end
            end
        end
        craftT[i] = (own and ok) and math.floor(own + csum * (list[i].qty or 1) / (ci.rec[3] or 1) + 0.5) or nil
        if craftT[i] and priced[i] and priced[i] > 0 then
            local d = math.floor((craftT[i] - priced[i]) / priced[i] * 100 + 0.5)
            if d > 0 then
                pcts[i] = { text = format("+%d%%", d), color = TIP_RED }
            elseif d < 0 then
                pcts[i] = { text = format("%d%%", d), color = { 0.42, 0.94, 0.62 } }
            else
                pcts[i] = { text = "0%", color = C_GREY }
            end
        end
    end
    local learned = PD.ProfLearned()
    local mode = PD.writSort
    table.sort(order, function(a, b)
        local wa, wb = list[a], list[b]
        if mode then
            local key = priced
            if mode == "own" then key = owns elseif mode == "craft" then key = craftT end
            local ca, cb = key[a], key[b]
            if ca and cb then return ca < cb end
            if ca or cb then return ca ~= nil end
            return (wa.target or 0) < (wb.target or 0)
        end
        if (wa.rep or 0) ~= (wb.rep or 0) then return (wa.rep or 0) > (wb.rep or 0) end
        local ca, cb = priced[a], priced[b]
        if ca and cb then return ca < cb end
        if ca or cb then return ca ~= nil end
        return (wa.target or 0) < (wb.target or 0)
    end)
    if not PD.writSel and list[order[1]] then
        PD.writSel = list[order[1]].quest or list[order[1]].target
    end
    local sel = PD.writSel
    rows[#rows + 1] = { kind = "colhead", col = 1, h = PD.ROW_H,
                        text = L["工匠文书"], right = L["拍卖总价"], craftRight = L["制造总价"],
                        ownRight = L["自身价格"],
                        sortOn = (mode == "total"), craftOn = (mode == "craft"), ownOn = (mode == "own"),
                        act = function()
                            PD.writSort = (mode ~= "total") and "total" or nil
                            PD.RequestRender()
                        end,
                        craftAct = function()
                            PD.writSort = (mode ~= "craft") and "craft" or nil
                            PD.RequestRender()
                        end,
                        ownAct = function()
                            PD.writSort = (mode ~= "own") and "own" or nil
                            PD.RequestRender()
                        end }
    for _, i in ipairs(order) do
        local w = list[i]
        local wid = w.item or w.target
        local craft = craftMap[w.target]
        local tag = craft and WritBadge(craft, learned) or nil
        rows[#rows + 1] = {
            kind = "row", col = 1, h = PD.ROW_H,
            it = { wid }, qItem = wid,
            text = PD.ItemName(wid),
            sub = format(L["声望 +%d"], w.rep or 0),
            tag = tag,
            right = priced[i] and RA.MoneyStr(priced[i]) or "",
            right2 = craftT[i] and RA.MoneyStr(craftT[i]) or "",
            right2Color = C_GOLD,
            pct = pcts[i],
            rightOwn = owns[i] and RA.MoneyStr(owns[i]) or "",
            rightOwnColor = C_TEXT,
            cur = ((w.quest or w.target) == sel),
            act = function()
                local key = w.quest or w.target
                if sel ~= key then PD.writSel = key; PD.RequestRender() end
            end,
        }
    end
    local sw
    for _, i in ipairs(order) do
        local w = list[i]
        if (w.quest or w.target) == sel then sw = w break end
    end
    if not sw then return end
    local wid = sw.item or sw.target
    local wu = RA.AHPriceOf and RA.AHPriceOf(wid) or nil
    local u = RA.AHPriceOf and RA.AHPriceOf(sw.target) or nil
    local buyAll = u and u * (sw.qty or 1) or nil
    local cinfo = craftMap[sw.target]
    local craft = cinfo and cinfo.rec or nil
    local craftSum, allPriced, craftCost
    if craft then
        craftSum, allPriced = 0, true
        for _, m in ipairs(craft[12]) do
            local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
            if p then craftSum = craftSum + p * (m[2] or 1) else allPriced = false end
        end
        craftCost = allPriced and math.floor(craftSum * math.ceil((sw.qty or 1) / (craft[3] or 1)) + 0.5) or nil
    end
    local secH = #rows + 1
    rows[#rows + 1] = {
        kind = "head", col = 2, h = 28, fs = 16,
        it = { wid },
        text = PD.ItemName(wid),
        tag = cinfo and WritBadge(cinfo, learned) or nil,
    }
    PushText(rows, format(L["声望 +%d · 需等级 %d"], sw.rep or 0, sw.level or 0), 12, C_GREY, 2)
    MarkSec(rows, secH, #rows, 1)
    PushGap(rows, PD.SEC_GAP + 2, 2)
    local cards = {
        { lab = L["直接买齐"], it = sw.target, priceOk = buyAll and true or false,
          name = format(L["%s ×%d"], PD.ItemName(sw.target), sw.qty or 1),
          price = buyAll and RA.MoneyStr(buyAll) or "—",
          tipExtra = function() return PD.PriceTipLines(sw.target) end },
        nil,
    }
    if craft then
        local yn = craft[3] or 1
        cards[2] = {
            lab = L["自己制造"], it = craft[2], priceOk = craftCost and true or false,
            name = yn > 1 and format(L["%s ×%d"], PD.ItemName(craft[2]), yn) or PD.ItemName(craft[2]),
            price = craftCost and RA.MoneyStr(craftCost) or "—",
            tipExtra = function() return PD.PriceTipLines(craft[2]) end,
        }
    else
        cards[2] = { lab = L["自己制造"], name = L["未登记配方"], dim = true }
    end
    if craftCost and buyAll then
        if craftCost < buyAll then
            cards[2].win = true
        elseif craftCost > buyAll then
            cards[1].win = true
        end
    end
    rows[#rows + 1] = { kind = "vs", col = 2, h = 52, vw = PD.splitRW, cards = cards }
    if craft and #craft[12] > 0 then
        PushGap(rows, PD.SEC_GAP + 2, 2)
        local secA = #rows + 1
        rows[#rows + 1] = { kind = "head", col = 2,
                            text = L["自己制造材料明细"], right = L["制造一次"] }
        for _, m in ipairs(craft[12]) do
            local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
            rows[#rows + 1] = {
                kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
                it = { m[1] }, qItem = m[1],
                text = PD.ItemName(m[1]) .. " ×" .. (m[2] or 1),
                right = p and RA.MoneyStr(p * (m[2] or 1)) or "",
                rightColor = p and C_TEXT or C_GREY,
                tipExtra = function() return PD.PriceTipLines(m[1]) end,
            }
        end
        CrateMetaRow(rows, L["制造一次的成本"], craftSum, allPriced, 14)
        local batches = math.ceil((sw.qty or 1) / (craft[3] or 1))
        CrateMetaRow(rows, L["制造上交所需物的成本"],
                     allPriced and math.floor(craftSum * batches + 0.5) or nil, allPriced, 14)
        MarkSec(rows, secA, #rows, 2)
    end
    local buyTotal = (wu and u) and (wu + u * (sw.qty or 1)) or nil
    local craftTotal = (wu and craftCost) and (wu + craftCost) or nil
    local lowest
    if buyTotal and craftTotal then
        lowest = math.min(buyTotal, craftTotal)
    else
        lowest = buyTotal or craftTotal
    end
    local cheapest = (buyTotal and craftTotal and craftTotal < buyTotal) and "craft"
                    or (buyTotal and craftTotal and buyTotal < craftTotal) and "buy" or nil
    local repUnit = (lowest and (sw.rep or 0) > 0) and (lowest / sw.rep) or nil
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secB = #rows + 1
    PushHead(rows, L["成本汇总"], 2)
    CrateMetaRow(rows, L["文书自身成本"], wu, wu, 14)
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
        text = L["直接买齐总成本"],
        right = buyTotal and RA.MoneyStr(buyTotal) or "—",
        rightColor = buyTotal and (cheapest == "buy" and { 0.42, 0.94, 0.62 } or C_TEXT) or C_GREY,
    }
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
        text = L["自己制造总成本"],
        right = craftTotal and RA.MoneyStr(craftTotal) or "—",
        rightColor = craftTotal and (cheapest == "craft" and { 0.42, 0.94, 0.62 } or C_TEXT) or C_GREY,
    }
    MarkSec(rows, secB, #rows, 3)
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secC = #rows + 1
    PushHead(rows, L["总结"], 2)
    if cheapest == "buy" then
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
            text = L["直接买便宜"],
            right = RA.MoneyStr(craftTotal - buyTotal),
            rightColor = { 0.42, 0.94, 0.62 },
        }
    elseif cheapest == "craft" then
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
            text = L["自己造省"],
            right = RA.MoneyStr(buyTotal - craftTotal),
            rightColor = { 0.42, 0.94, 0.62 },
        }
    end
    CrateMetaRow(rows, L["每点声望最低成本"], repUnit, repUnit, 14)
    MarkSec(rows, secC, #rows, 4)
    PD.hasSecs = true
    PD.secCount = 4
    PushGap(rows, 6, 2)
    PushText(rows, CrateSnapText(), 11, C_GREY, 2)
end

function PD.PlunderRows(rows)
    local list = (ns.PlunderData and ns.PlunderData.goods) or {}
    if not PD.plunderSel and list[1] then PD.plunderSel = list[1].id end
    local sel = PD.plunderSel
    local costs = {}
    for i, g in ipairs(list) do
        local sum, ok = 0, true
        for _, m in ipairs(g.mats or {}) do
            local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
            if p then sum = sum + p * (m[2] or 1) else ok = false end
        end
        costs[i] = ok and sum or nil
    end
    local mode = PD.plunderSort
    local order = {}
    for i = 1, #list do order[i] = i end
    if mode then
        table.sort(order, function(a, b)
            local ca, cb = costs[a], costs[b]
            if ca and cb then return ca < cb end
            if ca or cb then return ca ~= nil end
            return (list[a].id or 0) < (list[b].id or 0)
        end)
    end
    rows[#rows + 1] = { kind = "colhead", col = 1, h = PD.TEXT_H,
                        text = L["名称"], right = L["装填成本"],
                        sortOn = (mode == "cost"),
                        act = function()
                            PD.plunderSort = (mode ~= "cost") and "cost" or nil
                            PD.RequestRender()
                        end }
    for _, i in ipairs(order) do
        local g = list[i]
        rows[#rows + 1] = {
            kind = "row", col = 1, h = PD.ROW_H,
            it = { g.id }, qItem = g.id,
            text = PD.ItemName(g.id),
            sub = PLUNDER_CATS[g.cat] or g.cat or "",
            right = costs[i] and RA.MoneyStr(costs[i]) or "",
            cur = (g.id == sel),
            act = function()
                if PD.plunderSel ~= g.id then PD.plunderSel = g.id; PD.RequestRender() end
            end,
        }
    end
    local sg
    for _, g in ipairs(list) do if g.id == sel then sg = g break end end
    if not sg then return end
    PushHead(rows, PD.ItemName(sg.id), 2, 16)
    local meta = PLUNDER_CATS[sg.cat] or sg.cat or "—"
    meta = meta .. " · " .. format(L["物品等级 %d"], sg.band or 0)
    PushText(rows, meta, 12, C_GREY, 2)
    PushGap(rows, 6, 2)
    PushHead(rows, L["装填材料"], 2)
    local sum, ok = 0, true
    for _, m in ipairs(sg.mats or {}) do
        local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
        if p then sum = sum + p * (m[2] or 1) else ok = false end
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1,
            it = { m[1] }, qItem = m[1],
            text = PD.ItemName(m[1]) .. " ×" .. (m[2] or 1),
            right = p and RA.MoneyStr(p * (m[2] or 1)) or "—",
            rightColor = p and C_TEXT or C_GREY,
            tipExtra = function() return PD.PriceTipLines(m[1]) end,
        }
    end
    PushGap(rows, 6, 2)
    CrateMetaRow(rows, L["装填成本"], ok and sum or nil, ok)
    PushText(rows, CrateSnapText(), 11, C_GREY, 2)
end

function PD.RowsCrates(rows)
    if not CD then
        PushText(rows, L["暂时没有客户端数据"], 12, C_GREY)
        return
    end
    PD.lvSplit = true
    PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.CRATE_SPLIT)
    PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
    if PD.tab == "writ" then
        PD.WritRows(rows)
    elseif PD.tab == "plunder" then
        PD.PlunderRows(rows)
    else
        PD.CrateRows(rows)
    end
end

function PD.Render()
    if not (PD.built and PD.page) or not PD.cur then return end
    PD.ResetItemNameMemo()
    PD.lvRouteHead = nil
    PD.PickNav()
    PD.PickTabs()
    RememberLast()

    local rows = {}
    local tool, handler = {}, nil
    PD.lvSplit = false
    PD.gridSplit = false
    PD.wantIndexGrid = false
    PD.wantBonusTable = false
    PD.wantTrainerBoard = false
    PD.hasSecs = false
    PD.secPadL = nil
    PD.splitLW, PD.splitRW = nil, nil
    PD.hideDivider = false
    PD.secCount = 0
    PD.__pendRows = {}
    do
        local pk = tostring(PD.cur) .. "|" .. tostring(PD.tab) .. "|"
                   .. tostring(PD.autoPage) .. "|" .. tostring(PD.setOpen)
        if pk ~= PD.__pageKey then
            PD.__pageKey = pk
            for _, rr in pairs(PD.rows) do PD.WipeRow(rr) end
            if PD.secCards then
                for i = 1, #PD.secCards do PD.secCards[i]:Hide() end
                for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end
            end
        end
    end

    if PD.setOpen then
        PD.RowsSettings(rows)
    elseif PD.tab == "overview" then
        PD.lvSplit = false
        PD.wantIndexGrid = (PD.cur == "__index")
        PD.hasSecs = true
        PD.hideDivider = true
        if PD.cur == "camping" then
            PD.campView = "bonus"
            PD.wantBonusTable = true
        end
        PD.RowsOverview(rows)
    elseif PD.tab == "trainer" then
        PD.wantTrainerBoard = true
    elseif PD.tab == "recipe" then
        tool, handler = PD.RecipeTool(RGet(PD.cur))
        PD.RowsRecipe(rows)
    elseif PD.tab == "crate" or PD.tab == "plunder" or PD.tab == "writ" then
        PD.RowsCrates(rows)
    elseif PD.tab == "gather" then
        PD.gridSplit = (PD.cur == "fishing")
        PD.RowsGather(rows)
    elseif PD.tab == "leveling" then
        if PD.GATHER_SLUGS[PD.cur] then
            PD.lvSplit = false
            PD.gridSplit = false
            PD.autoPage = nil
            PD.RowsGatherRoute(rows)
        else
        tool, handler = PD.LevelTool()
        if PD.autoPage == "shop" then
            PD.lvSplit = true
            PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.SHOP_SPLIT)
            PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
        else
            PD.lvSplit = false
        end
        PD.RowsLeveling(rows)
        end
    else
        PD.RowsOverview(rows)
    end

    if tool and PD.lvRouteHead then
        tool[#tool + 1] = { key = "route_head", plain = true,
                            text = PD.lvRouteHead.text, warn = PD.lvRouteHead.warn }
    end

    local toolH
    if PD.tab == "leveling" and not PD.setOpen then
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 8)
    else
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler)
    end
    PD.Layout(toolH)

    if PD.searchBox then
        if PD.tab == "recipe" and not PD.setOpen then
            PD.searchBox:ClearAllPoints()
            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",
                                  -(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP))
            PD.searchBox:Show()
        else
            PD.searchBox:Hide()
        end
    end

    PD.specs = rows
    PD.curRows, PD.visMode = nil, false
    PD.scroll:SetVerticalScroll(0)
    PD.truncated = PD.PaintRows(rows)
    ns.OpenPerf.Mark("首屏")
    PD.PlaceSettingsToggles(rows)
    PD.scroll:Show()
    PD.RequestRows(rows)
    PD.WarmNames()
    if PD.UpdateVScroll then PD.UpdateVScroll() end
end

local _warmTok = 0
local PD_WARM_PER_FRAME = 96
function PD.WarmId(id)
    if not id then return end
    local _, got = PD.ItemName(id)
    if got then return end
    if C_Item and C_Item.RequestLoadItemDataByID then
        pcall(C_Item.RequestLoadItemDataByID, id)
    end
    local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(gi) == "function" then pcall(gi, id) end
end
function PD.WarmNames()
    local d = RGet(PD.cur)
    local all = d and d.rows
    if type(all) ~= "table" or #all == 0 then return end
    if not (C_Timer and C_Timer.After) then return end
    _warmTok = _warmTok + 1
    local tok = _warmTok
    local i, n = 0, math.min(#all, PD.ROW_CAP)
    local function feed()
        if tok ~= _warmTok then return end
        if DG.stepping then C_Timer.After(0, feed) return end
        local ok = pcall(function()
            local budget = PD_WARM_PER_FRAME
            while i < n and budget > 0 do
                i = i + 1
                local r = all[i]
                if r then
                    PD.WarmId(r[2])
                    local ms = r[12]
                    if ms then
                        for k = 1, #ms do PD.WarmId(ms[k] and ms[k][1]) end
                    end
                end
                budget = budget - 1
            end
        end)
        if not ok then return end
        if i < n then C_Timer.After(0, feed) end
    end
    C_Timer.After(0, feed)
end

function PD.RequestRows(rows)
    if not DG.ItemName then return end
    local wait = {}
    local seen = {}
    local function want(id)
        if not id or seen[id] then return end
        seen[id] = true
        local hasName = select(2, PD.ItemName(id))
        if hasName then return end
        if C_Item and C_Item.RequestLoadItemDataByID then
            pcall(C_Item.RequestLoadItemDataByID, id)
        end
        local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
        if type(gi) == "function" then pcall(gi, id) end
        wait[#wait + 1] = id
    end
    local n = math.min(#rows, PD.ROW_CAP)
    for i = 1, n do
        local spec = rows[i]
        if spec.it then want(spec.it[1]) end
        for _, m in ipairs(spec._mats or {}) do want(m[1]) end
    end
    PD.notReady = (#wait > 0) and wait or nil
    if PD.notReady and not PD.sweeping then PD.ScheduleSweep() end
end

function PD.Show(slug)
    ns.OpenPerf.Begin("专业·" .. tostring(slug))
    PD.HideVendorPick()
    if slug ~= PD.cur then
        PD.cur = slug
        PD.toolKey = nil
        PD.campView = "a"
        PD.tab = "overview"
        PD.setOpen = false
        PD.searchQ = nil
        if PD.searchBox then PD.searchBox.eb:SetText("") end
    end
    if not PD.built then
        PD.wantOpen = true
    end
    PD.RequestRender()
end

function PD.SetTab(key)
    PD.setOpen = false
    if not (PD.avail and PD.avail[key]) then return end
    PD.tab = key
    PD.RequestRender()
end

function PD.DefaultSlug()
    local learned = PD.ProfLearned()
    local fallback
    for _, slug in ipairs(PD.navOrder or {}) do
        local p = D.pro[slug]
        if p and not fallback then fallback = slug end
        if learned[slug] and p and p.kind == "primary" then return slug end
    end
    for _, slug in ipairs(PD.navOrder or {}) do
        if learned[slug] then return slug end
    end
    return fallback
end

function PD.EnsureCur()
    if PD.cur and PD.cur ~= "__index" then return end
    local db = ProfDB()
    local slug = db.lastSlug
    if not (slug and D.pro[slug]) then slug = PD.DefaultSlug() end
    if slug then
        PD.cur = slug
        PD.toolKey = nil
        PD.tab = (type(db.lastTab) == "string") and db.lastTab or "overview"
        PD.setOpen = false
    end
end

function PD.RequestRender()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    if not (ns.PaintJob and ns.IdleJobs) then
        PD.Render()
        return
    end
    if ns.PaintJob.Active("Profession") then
        PD.__pend = true
        return
    end
    ns.PaintJob.Run("Profession", function() PD.Render() end, function()
        if PD.__pend then
            PD.__pend = false
            PD.RequestRender()
        end
    end)
end

function PD.Open()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    PD.EnsureCur()
    PD.RequestRender()
end

function PD.Refresh()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    PD.EnsureCur()
    PD.RequestRender()
end

PD.DEMO_SAVE = nil

function PD.StartGateDemo()
    if PD.DEMO_SAVE then PD.EndGateDemo() end
    PD.DEMO_SAVE = {
        syncMax  = PD.ROW_SYNC_MAX,
        minSteps = DG.Gate.minSteps,
        rowCap   = DG.LOOT_ROW_FRAME_CAP,
    }
    PD.ROW_SYNC_MAX       = 0
    DG.Gate.minSteps      = 0
    DG.LOOT_ROW_FRAME_CAP = 2
    for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
    PD.rows = {}
    PD.RequestRender()
end

function PD.EndGateDemo()
    local s = PD.DEMO_SAVE
    PD.DEMO_SAVE = nil
    if not s then return end
    PD.ROW_SYNC_MAX       = s.syncMax
    DG.Gate.minSteps      = s.minSteps
    DG.LOOT_ROW_FRAME_CAP = s.rowCap
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgate"
    SlashCmdList["DUNGEONSFOREVERPROFGATE"] = function()
        if PD.DEMO_SAVE then
            PD.EndGateDemo()
            print("|cff46bf72[无限副本手册]|r " .. L["已还原。"])
            return
        end
        if not PD.built or not PD.cur then
            print("|cff46bf72[无限副本手册]|r "
                  .. L["先打开一个专业的配方页，再运行这个命令。"])
            return
        end
        PD.StartGateDemo()
        print("|cff46bf72[无限副本手册]|r "
              .. L["演示：每帧只建 2 行，进度条会走完一遍。"])
    end
end

PD.PERF     = false
PD.PERF_MIN = 6

local pfUnpack = unpack
if not pfUnpack and type(table) == "table" then pfUnpack = table.unpack end
if not pfUnpack then pfUnpack = function(t) return t[1] end end

local PF_DEPTH, PF_MS, PF_N, PF_WHERE = 0, nil, nil, ""
local PF_TAIL = nil
local PF_SCAN = nil
local PF_SUB, PF_SET = nil, nil
local PF_SKIN0 = nil
local PF_TB0 = nil
local PF_STR0 = nil
local PF_STRM0 = nil
local PF_STRS0 = nil
local PF_ORDER = { "导航", "数据", "工具P", "工具R", "工具L", "信息卡",
                   "布局", "铺行", "开关", "请求" }
local PF_KIND  = { "量宽", "量宽调用", "取名", "取名(引擎)", "发包", "完整预热", "建行", "上数据" }

local function pfNow()
    if type(debugprofilestop) == "function" then return debugprofilestop() end
    if type(GetTime) == "function" then return GetTime() * 1000 end
    return 0
end

local function pfOut(s) print("|cff46bf72[DF性能]|r " .. s) end

function PD.__pfT0()
    if not PF_SUB then return nil end
    return pfNow()
end

function PD.__pfMark(tag, t0)
    if not PF_SUB or not t0 then return end
    local dt = pfNow() - t0
    local e = PF_SUB[tag]
    if e then e[1] = e[1] + 1; e[2] = e[2] + dt
    else PF_SUB[tag] = { 1, dt } end
end

function PD.__pfAdd(tag, n)
    if not PF_SUB or not n then return end
    local e = PF_SUB[tag]
    if e then e[1] = e[1] + n else PF_SUB[tag] = { n, 0 } end
end

local function pfBegin(where)
    PF_DEPTH = PF_DEPTH + 1
    if PF_DEPTH == 1 then
        PF_MS, PF_N = {}, {}
        PF_SUB, PF_SET = {}, {}
        PF_SKIN0 = (ns.hui and ns.hui.__skinBuilds) or 0
        PF_TB0 = (ns.hui and ns.hui.__tryBuilds) or 0
        local _st = ns.hui and ns.hui.__stripStat
        if _st then
            local a, b, c = _st()
            PF_STR0, PF_STRM0, PF_STRS0 = a or 0, b or 0, c or 0
        else
            PF_STR0, PF_STRM0, PF_STRS0 = 0, 0, 0
        end
        PF_WHERE = where or ""
        local t = PF_TAIL
        if t then
            PF_TAIL = nil
            pfOut(string.format("  └ 顺上一次的分帧段：%d 帧 / %.1fms / %d 行",
                                t.frames, t.ms, t.rows))
        end
    end
end

local function pfTick(tag, t0)
    if PF_MS then PF_MS[tag] = (PF_MS[tag] or 0) + (pfNow() - t0) end
end

local function pfHit(tag, dt)
    if not PF_N then return end
    local e = PF_N[tag]
    if e then e[1] = e[1] + 1; e[2] = e[2] + (dt or 0)
    else PF_N[tag] = { 1, dt or 0 } end
end

local function pfEnd()
    PF_DEPTH = PF_DEPTH - 1
    if PF_DEPTH > 0 then return end
    local ms, n, where = PF_MS, PF_N, PF_WHERE
    PF_MS, PF_N = nil, nil
    if not ms then return end
    local total, other = 0, 0
    local floor = (PD.PERF == "all") and -1 or 0.05
    local parts, seen = {}, {}
    for _, k in ipairs(PF_ORDER) do
        seen[k] = true
        local v = ms[k]
        if v and v >= floor then
            total = total + v
            parts[#parts + 1] = string.format("%s %.1f", k, v)
        end
    end
    for k, v in pairs(ms) do
        if not seen[k] and k ~= "入口" then other = other + v end
    end
    local entry = ms["入口"]
    local grand = entry or (total + other)

    if PD.PERF == "scan" then
        PF_SCAN = PF_SCAN or {}
        PF_SCAN[#PF_SCAN + 1] = { where ~= "" and where or "?", grand, entry }
        return
    end
    if PD.PERF ~= "all" and grand < (PD.PERF_MIN or 6) then return end

    local head = string.format("%.1fms  %s", grand, where ~= "" and where or "?")
    if other >= 0.05 then head = head .. string.format("  （未归类 %.1f）", other) end
    pfOut(head)
    if #parts > 0 then pfOut("  └ " .. table.concat(parts, " · ")) end
    local cnt = {}
    for _, k in ipairs(PF_KIND) do
        local e = n[k]
        if e then cnt[#cnt + 1] = string.format("%s %d次/%.1fms", k, e[1], e[2]) end
    end
    if #cnt > 0 then pfOut("  └ " .. table.concat(cnt, " · ")) end
    local sub = {}
    for _, k in ipairs({ "扫描", "建spec", "列宽材料", "材料串", "单条spec",
                        "工具尺寸", "搜索预留" }) do
        local e = PF_SUB and PF_SUB[k]
        if e then sub[#sub + 1] = string.format("%s %d次/%.1f", k, e[1], e[2]) end
    end
    if #sub > 0 then pfOut("  └ 细分（已含在上面某一段里，不相加）：" .. table.concat(sub, " · ")) end
    local st = {}
    for _, k in ipairs({ "SetText", "SetTextColor", "SetPoint", "SetSize",
                        "SetShown", "Show", "Hide" }) do
        local e = PF_SET and PF_SET[k]
        if e then st[#st + 1] = string.format("%s %d次", k, e[1]) end
    end
    if #st > 0 then pfOut("  └ setter 调用：" .. table.concat(st, " · ")) end
    local sk = ((ns.hui and ns.hui.__skinBuilds) or 0) - (PF_SKIN0 or 0)
    local tb = ((ns.hui and ns.hui.__tryBuilds) or 0) - (PF_TB0 or 0)
    pfOut(string.format("  └ 皮按钮帧：建 %d 次 · TryBuild 调用 %d 次（rev14）", sk, tb))
    local zg = PF_SUB and PF_SUB["闸-合计"]
    if zg then
        local seg, hit = {}, 0
        for _, kv in ipairs({ { "闸-尺寸", "尺寸" }, { "闸-锚点", "锚点" },
                              { "闸-文本", "文本" }, { "闸-显示", "显示" } }) do
            local e = PF_SUB[kv[1]]
            if e then
                seg[#seg + 1] = string.format("%s %.1f", kv[2], e[2])
                hit = e[1]
            end
        end
        pfOut(string.format("  └ 工具闸门（已含在「工具P」里）：%d 开 / %.1fms = %s（其中已显 %d）",
                            hit, zg[2], table.concat(seg, " + "),
                            (PF_SUB["闸-已显"] and PF_SUB["闸-已显"][1]) or 0))
    end
    local stn, stms, stscan = 0, 0, 0
    if ns.hui and ns.hui.__stripStat then stn, stms, stscan = ns.hui.__stripStat() end
    pfOut(string.format("  └ 皮条纹复算：%d 次 / %.1fms / 共扫 %d 条（rev15）",
                        stn - (PF_STR0 or 0), stms - (PF_STRM0 or 0), stscan - (PF_STRS0 or 0)))
end

local function pfTime(t, key, tag)
    if type(t) ~= "table" then return end
    local fn = t[key]
    if type(fn) ~= "function" then return end
    t[key] = function(...)
        if not PD.PERF then return fn(...) end
        local t0 = pfNow()
        local r = { fn(...) }
        pfTick(tag or key, t0)
        return pfUnpack(r)
    end
end

local function pfCount(t, key, tag)
    if type(t) ~= "table" then return end
    local fn = t[key]
    if type(fn) ~= "function" then return end
    t[key] = function(...)
        if not PD.PERF then return fn(...) end
        local t0 = pfNow()
        local r = { fn(...) }
        pfHit(tag or key, pfNow() - t0)
        return pfUnpack(r)
    end
end

local function pfWhere()
    local who = PD.cur or "?"
    local bt = PD.navKey and PD.navKey[who]
    if bt and type(bt.GetText) == "function" then
        local s = bt:GetText()
        if type(s) == "string" and s ~= "" then who = s end
    end
    return string.format("「%s·%s」", tostring(who),
                         PD.setOpen and "设置" or tostring(PD.tab or "?"))
end

local function pfEntry(key, label)
    local fn = PD[key]
    if type(fn) ~= "function" then return end
    PD[key] = function(...)
        if not PD.PERF then return fn(...) end
        pfBegin(label)
        local t0 = pfNow()
        local r = { fn(...) }
        if PF_DEPTH == 1 then
            pfTick("入口", t0)
            PF_WHERE = label .. " " .. pfWhere()
        end
        pfEnd()
        return pfUnpack(r)
    end
end

local function pfSub(t, key, tag)
    if type(t) ~= "table" then return end
    local fn = t[key]
    if type(fn) ~= "function" then return end
    t[key] = function(...)
        if not PD.PERF or not PF_SUB then return fn(...) end
        local t0 = pfNow()
        local r = { fn(...) }
        local e = PF_SUB[tag]
        if e then e[1] = e[1] + 1; e[2] = e[2] + (pfNow() - t0)
        else PF_SUB[tag] = { 1, pfNow() - t0 } end
        return pfUnpack(r)
    end
end
pfSub(PD, "ScanRecipe",    "扫描")
pfSub(PD, "RecipeList",    "建spec")
pfSub(PD, "FitRecipeCols", "列宽材料")
pfSub(PD, "MatCol",        "材料串")
pfSub(PD, "RecipeSpec",    "单条spec")
pfSub(PD, "ToolSize",      "工具尺寸")
pfSub(PD, "SearchReserve", "搜索预留")

local function pfWrapSetter(obj, meth)
    if type(obj) ~= "table" then return end
    local fn = obj[meth]
    if type(fn) ~= "function" or obj["__dfw" .. meth] then return end
    obj["__dfw" .. meth] = true
    obj[meth] = function(self, ...)
        if PF_SET then
            local e = PF_SET[meth]
            if e then e[1] = e[1] + 1 else PF_SET[meth] = { 1 } end
        end
        return fn(self, ...)
    end
end
local function pfWrapEl(f)
    if type(f) ~= "table" then return end
    pfWrapSetter(f, "SetText")
    pfWrapSetter(f, "SetPoint")
    pfWrapSetter(f, "SetSize")
    pfWrapSetter(f, "SetShown")
    pfWrapSetter(f, "Show")
    pfWrapSetter(f, "Hide")
    if type(f.GetFontString) == "function" then
        local ok, gs = pcall(f.GetFontString, f)
        if ok then
            pfWrapSetter(gs, "SetText")
            pfWrapSetter(gs, "SetTextColor")
        end
    end
end
local function pfWrapAll()
    for _, bt in pairs(PD.toolBtns or {}) do pfWrapEl(bt) end
    for _, bt in pairs(PD.subBtns or {}) do pfWrapEl(bt) end
    for _, bt in pairs(PD.navKey or {}) do pfWrapEl(bt) end
    local rows = PD.rows or {}
    for i = 1, #rows do
        local r = rows[i]
        if type(r) == "table" then
            for _, k in ipairs({ "a", "b", "c", "d", "e", "f", "dv", "tagFs" }) do
                pfWrapSetter(r[k], "SetText")
                pfWrapSetter(r[k], "SetTextColor")
            end
            for _, fs in pairs(r.mn or {}) do pfWrapSetter(fs, "SetText") end
        end
    end
end

do
    local raw = PD.Render
    PD.Render = function(...)
        if not PD.PERF then return raw(...) end
        pfWrapAll()
        pfBegin(PF_DEPTH == 0 and pfWhere() or nil)
        local ok, e = pcall(raw, ...)
        pfEnd()
        if not ok then error(e, 0) end
    end
end

do
    local raw = PD.BuildPendRows
    if type(raw) == "function" then
        PD.BuildPendRows = function()
            if not PD.PERF then return raw() end
            local t0 = pfNow()
            local before = #(PD.__pendRows or {})
            local ok, e = pcall(raw)
            local after = #(PD.__pendRows or {})
            local t = PF_TAIL
            if not t then t = { frames = 0, ms = 0, rows = 0 }; PF_TAIL = t end
            t.frames = t.frames + 1
            t.ms = t.ms + (pfNow() - t0)
            if before > after then t.rows = t.rows + (before - after) end
            if not ok then error(e, 0) end
        end
    end
end

pfTime(PD, "PickNav",   "导航")
pfTime(PD, "PickTabs",  "导航")
pfTime(PD, "RowsRecipe",   "数据")
pfTime(PD, "RowsOverview", "数据")
pfTime(PD, "RowsGather",   "数据")
pfTime(PD, "RowsFishing",  "数据")
pfTime(PD, "RowsLeveling", "数据")
pfTime(PD, "RowsAutoShop", "数据")
pfTime(PD, "RowsCamp",     "数据")
pfTime(PD, "RowsLegacy",   "数据")
pfTime(PD, "RowsNotes",    "数据")
pfTime(PD, "RowsSettings", "数据")
pfTime(PD, "PaintLvTiles", "信息卡")
pfTime(PD, "PaintTool",    "工具P")
pfTime(PD, "RecipeTool",   "工具R")
pfTime(PD, "LevelTool",    "工具L")
pfTime(PD, "Layout",      "布局")
pfTime(PD, "PaintRows",   "铺行")
pfTime(PD, "PlaceSettingsToggles", "开关")
pfTime(PD, "RequestRows", "请求")

pfCount(ns.hui, "TextW",   "量宽")
pfCount(PD, "TextW",       "量宽调用")
pfCount(PD, "ItemName",    "取名")
pfCount(DG, "ItemInfo",    "取名(引擎)")
pfCount(DG, "RequestItem", "完整预热")
if type(C_Item) == "table" then
    pfCount(C_Item, "RequestLoadItemDataByID", "发包")
end
pfCount(PD, "Row",         "建行")
pfCount(PD, "BindRow",     "上数据")

pfEntry("Show",       "切专业")
pfEntry("SetTab",     "点页签")
pfEntry("Open",       "打开")
pfEntry("Refresh",    "刷新")
pfEntry("SweepNames", "物品到货重渲")

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFPERF1 = "/dfprofperf"
    SlashCmdList["DUNGEONSFOREVERPROFPERF"] = function(msg)
        msg = string.lower(tostring(msg or ""))
        msg = msg:gsub("^%s+", ""):gsub("%s+$", "")
        PF_DEPTH, PF_MS, PF_N, PF_TAIL = 0, nil, nil, nil
        if msg == "all" then
            PD.PERF = "all"
            pfOut("已开启：全部打印（含很快的）。/dfprofperf off 关闭。")
            return
        end
        if msg == "off" then
            PD.PERF = false
            pfOut("已关闭。")
            return
        end
        if msg == "rep" then
            if not (PD.built and PD.page) then
                pfOut("先打开专业页（/df zy）再 rep。")
                return
            end
            local save, saveMin = PD.PERF, PD.PERF_MIN
            PD.PERF, PD.PERF_MIN = "all", 0
            for i = 1, 3 do
                pfOut("  ---- 第 " .. i .. " 次 ----")
                PD.Render()
            end
            PD.PERF, PD.PERF_MIN = save, saveMin
            pfOut("rep 完成（第 1 次含建帧，后两次是热路径）。")
            return
        end
        if msg == "scan" then
            if not (PD.built and PD.page) then
                pfOut("先打开专业页（/df zy）再 scan。")
                return
            end
            local save = PD.PERF
            PD.PERF = "scan"
            PF_SCAN = {}
            local n = 0
            for _, slug in ipairs(PD.navOrder or {}) do
                local r = RGet(slug)
                if r and ((r.rows and #r.rows > 0) or (r.enchants and #r.enchants > 0)
                          or (r.crafted and #r.crafted > 0)) then
                    PD.Show(slug)
                    PD.SetTab("recipe")
                    n = n + 1
                end
            end
            PD.PERF = save
            local list = PF_SCAN or {}
            table.sort(list, function(a, b) return a[2] > b[2] end)
            pfOut(string.format("扫描完成：%d 个专业 / %d 次渲染，按耗时排序 ——", n, #list))
            for i = 1, math.min(#list, 30) do
                pfOut(string.format("  %2d. %-26s %.1fms", i, list[i][1], list[i][2]))
            end
            return
        end
        if msg == "bench" then
            if not (PD.built and PD.page) then
                pfOut("先打开专业页（/df zy）再 bench。")
                return
            end
            local save = PD.PERF
            PD.PERF = false
            local f = CreateFrame("Button", nil, PD.page)
            f:SetSize(160, 22)
            f:SetPoint("TOPLEFT", PD.page, "TOPLEFT", 0, 0)
            local fsb = f:CreateFontString()
            fsb:SetAllPoints()
            fsb:SetFont(ns.FONT, 12, "OUTLINE")
            f:SetFontString(fsb)
            f:Show()
            local N = 400
            local togg = true
            local function bench(name, fn)
                fn() fn()
                local t0 = pfNow()
                for _ = 1, N do fn() end
                pfOut(string.format("  ▸ %-16s %7.2f µs/次", name, (pfNow() - t0) / N * 1000))
            end
            pfOut(string.format("setter 单价（各 %d 次；这是实机真实引擎调用）：", N))
            bench("SetText 中文", function() fsb:SetText("全部 511 条配方") end)
            bench("SetText 空串", function() fsb:SetText("") end)
            bench("SetTextColor", function() fsb:SetTextColor(1, 0.82, 0) end)
            bench("SetShown 切换", function() togg = not togg; f:SetShown(togg) end)
            bench("Clear+SetPoint", function()
                f:ClearAllPoints()
                f:SetPoint("TOPLEFT", PD.page, "TOPLEFT", 0, 0)
            end)
            bench("SetSize", function() f:SetSize(160, 22) end)
            bench("Show", function() f:Show() end)
            bench("Hide", function() f:Hide() end)
            f:Hide()
            PD.PERF = save
            pfOut("bench 完成 —— 把上面这组单价发我，配合「细分 / setter 调用」两行即可定位下一刀。")
            return
        end
        if PD.PERF then
            PD.PERF = false
            pfOut("已关闭。")
        else
            PD.PERF = true
            pfOut(string.format("已开启：只打慢过 %dms 的。点几下配方页即可；"
                                .. "/dfprofperf all 连快的也打，scan 挨个专业跑一遍。",
                                PD.PERF_MIN or 6))
        end
    end
end

function PD.AuditRows(all)
    if not (PD.built and PD.page) then
        pfOut("先打开专业页（/df zy）再 /dfprofrows。")
        return
    end
    local buf = {}
    local function out(s) buf[#buf + 1] = s; pfOut(s) end
    local function sink(s) buf[#buf + 1] = s end
    local specN = #(PD.specs or {})
    local idxOf, idxs = {}, {}
    local nPool, nShown = 0, 0
    for i, rr in pairs(PD.rows or {}) do
        idxOf[rr] = i
        idxs[#idxs + 1] = i
        nPool = nPool + 1
        if rr.IsShown and rr:IsShown() then nShown = nShown + 1 end
    end
    table.sort(idxs)
    out(string.format("页面 cur=%s tab=%s 子页=%s 设置页=%s",
                        tostring(PD.cur), tostring(PD.tab),
                        tostring(PD.autoPage), tostring(PD.setOpen)))
    out(string.format("行池 %d 帧 / 显示中 %d / 本页 spec %d",
                        nPool, nShown, specN))
    local nSec, nSecG = 0, 0
    if PD.secCards then
        for _, c in ipairs(PD.secCards) do if c.IsShown and c:IsShown() then nSec = nSec + 1 end end
    end
    if PD.secGoldCards then
        for _, c in ipairs(PD.secGoldCards) do if c.IsShown and c:IsShown() then nSecG = nSecG + 1 end end
    end
    out(string.format("段落卡 可见 %d / 金卡 可见 %d", nSec, nSecG))
    local known = {}
    if PD.secCards then for _, c in ipairs(PD.secCards) do known[c] = true end end
    if PD.secGoldCards then for _, c in ipairs(PD.secGoldCards) do known[c] = true end end
    if PD.setToggles then for _, c in ipairs(PD.setToggles) do known[c] = true end end
    if PD.setHelps then for _, c in ipairs(PD.setHelps) do known[c] = true end end

    local function texts(r)
        local t = {}
        for _, k in ipairs({ "e", "a", "b", "c", "d", "f", "dv" }) do
            local fs = r[k]
            if fs and fs.GetText then
                local ok, v = pcall(fs.GetText, fs)
                if ok and v and v ~= "" then
                    t[#t + 1] = k .. "=" .. tostring(v)
                end
            end
        end
        return table.concat(t, " | ")
    end
    local function shown(f)
        return (f and f.IsShown and f:IsShown()) and true or false
    end
    local function shape(r)
        local nblk = 0
        for j = 1, #(r.blk or {}) do
            local b = r.blk[j]
            if b.ic and shown(b.ic) then nblk = nblk + 1 end
        end
        local nmn, nmz = 0, 0
        for j, mfs in pairs(r.mn or {}) do if shown(mfs) then nmn = nmn + 1 end end
        for j = 1, #(r.mz or {}) do if shown(r.mz[j]) then nmz = nmz + 1 end end
        return string.format("材料块=%d 分段字串=%d 分段热区=%d %s",
                             nblk, nmn, nmz, shown(r.dv) and "商人半段○" or "商人半段-")
    end

    local bad = 0
    for _, i in ipairs(idxs) do
        local r = PD.rows[i]
        if shown(r) and not (PD.specs and PD.specs[i]) then
            bad = bad + 1
            out(string.format("  [越界行] idx=%d (%s) %s", i, shape(r), texts(r)))
        end
    end

    local function isRowLike(f)
        return (f.a or f.mn or f.blk) and true or false
    end
    local nOrphan = 0
    local function scan(f, where)
        if not (f and type(f.GetChildren) == "function") then return end
        local ok, kids = pcall(function() return { f:GetChildren() } end)
        if not ok or type(kids) ~= "table" then return end
        for _, ch in ipairs(kids) do
            if ch ~= f and type(ch) == "table" and shown(ch)
               and isRowLike(ch) and not idxOf[ch] and not known[ch] then
                nOrphan = nOrphan + 1
                out(string.format("  [孤儿帧] %s @%s %sx%s %s", tostring(where),
                                    tostring(rawget(ch, "__name")),
                                    tostring(ch.GetWidth and ch:GetWidth()),
                                    tostring(ch.GetHeight and ch:GetHeight()),
                                    texts(ch)))
            end
        end
    end
    scan(PD.child, "child")
    scan(PD.page, "page")

    local nMisc = 0
    local function geom(f)
        local l, b = -1, -1
        pcall(function() l = math.floor((f:GetLeft() or 0) + 0.5) end)
        pcall(function() b = math.floor((f:GetBottom() or 0) + 0.5) end)
        return l, b
    end
    local function scanMisc(f, where)
        if not (f and type(f.GetChildren) == "function") then return end
        local ok, kids = pcall(function() return { f:GetChildren() } end)
        if not ok or type(kids) ~= "table" then return end
        for _, ch in ipairs(kids) do
            if ch ~= f and type(ch) == "table" and shown(ch)
               and not idxOf[ch] and not known[ch] then
                nMisc = nMisc + 1
                if nMisc <= 20 then
                    local l, b = geom(ch)
                    out(string.format("  [杂帧] %s @%s x=%d y=%d %s %s",
                                        tostring(where),
                                        tostring(rawget(ch, "__name")),
                                        l, b, shape(ch), texts(ch)))
                end
            end
        end
    end
    scanMisc(PD.child, "child")

    if all then
        for _, i in ipairs(idxs) do
            local r = PD.rows[i]
            local sp = PD.specs and PD.specs[i]
            if shown(r) then
                local stxt = ""
                if sp then
                    stxt = tostring(sp.text or sp.sub or "")
                    if #stxt > 26 then stxt = stxt:sub(1, 26) .. "…" end
                end
                local l = geom(r)
                sink(string.format("  行 idx=%d kind=%s spec[%s] x=%d %s || %s", i,
                                   tostring(sp and sp.kind), stxt, l,
                                   shape(r), texts(r)))
            end
        end
    end
    out(string.format("结论：越界行 %d / 孤儿帧 %d / 杂帧 %d ⇒ %s", bad, nOrphan, nMisc,
                      (bad + nOrphan + nMisc == 0) and "干净" or "★ 有残留，见上面几行"))
    out("全量已存档（profAudit），/reload 后游戏外直接读文件，无需复制。")
    if type(DungeonsForeverDB) == "table" then
        DungeonsForeverDB.profAudit = {
            t = date("%Y-%m-%d %H:%M:%S"),
            page = tostring(PD.cur) .. "/" .. tostring(PD.tab) .. "/" .. tostring(PD.autoPage),
            n = #buf,
            lines = buf,
        }
    end
end

function PD.CensusText()
    if not (PD.built and PD.page) then
        pfOut("先打开专业页再普查。")
        return
    end
    local buf = {}
    local function sink(s) buf[#buf + 1] = s end
    local idxOf = {}
    for i, rr in pairs(PD.rows or {}) do idxOf[rr] = i end
    local n = 0
    local function coords(f)
        local l, b = -1, -1
        pcall(function() l = math.floor((f:GetLeft() or 0) + 0.5) end)
        pcall(function() b = math.floor((f:GetBottom() or 0) + 0.5) end)
        return l, b
    end
    local function fieldOf(r, fs)
        if fs == r.f then return "f" end
        if fs == r.dv then return "dv" end
        for _, k in ipairs({ "a", "b", "c", "d", "e" }) do
            if fs == r[k] then return k end
        end
        if fs == r.tagFs then return "tag" end
        for j, mfs in pairs(r.mn or {}) do
            if fs == mfs then return "mn[" .. j .. "]" end
        end
        for j = 1, #(r.blk or {}) do
            local b = r.blk[j]
            if fs == b.nm then return "blk[" .. j .. "].nm" end
            if fs == b.ct then return "blk[" .. j .. "].ct" end
        end
        return "?"
    end
    local function auditRow(r, idx)
        local rs = "行#" .. idx .. "(" .. (r.IsShown and r:IsShown() and "显示" or "自身隐藏") .. ")"
        local ok, regions = pcall(function() return { r:GetRegions() } end)
        if not (ok and type(regions) == "table") then return end
        for _, fs in ipairs(regions) do
            if type(fs) == "table" and fs.GetText and fs.IsVisible and fs:IsVisible() then
                local ok2, t = pcall(fs.GetText, fs)
                if ok2 and t and t ~= "" then
                    n = n + 1
                    if n <= 4000 then
                        local l, b = coords(fs)
                        sink(string.format("  [字串] %s.%s x=%d y=%d %s", rs,
                                           fieldOf(r, fs), l, b,
                                           (tostring(t):gsub("|", "¦"))))
                    end
                end
            end
        end
    end
    local function walk(f, path, depth)
        if depth > 8 then return end
        local ok, regions = pcall(function() return { f:GetRegions() } end)
        if ok and type(regions) == "table" then
            for _, r in ipairs(regions) do
                if type(r) == "table" and r.GetText and r.IsVisible and r:IsVisible() then
                    local ok2, t = pcall(r.GetText, r)
                    if ok2 and t and t ~= "" then
                        n = n + 1
                        if n <= 4000 then
                            local l, b = coords(r)
                            sink(string.format("  [字串] %s x=%d y=%d %s", path, l, b,
                                               (tostring(t):gsub("|", "¦"))))
                        end
                    end
                end
            end
        end
        local okk, kids = pcall(function() return { f:GetChildren() } end)
        if okk and type(kids) == "table" then
            for _, ch in ipairs(kids) do
                if type(ch) == "table" and ch.IsVisible and ch:IsVisible() then
                    if idxOf[ch] then
                        auditRow(ch, idxOf[ch])
                    else
                        walk(ch, path .. ">" .. tostring(rawget(ch, "__name") or "?"), depth + 1)
                    end
                end
            end
        end
    end
    walk(PD.page, "page", 0)
    sink(string.format("普查：实际可见的非空字串 %d 条", n))
    if type(DungeonsForeverDB) == "table" then
        DungeonsForeverDB.profAudit = {
            t = date("%Y-%m-%d %H:%M:%S"),
            page = tostring(PD.cur) .. "/" .. tostring(PD.tab) .. "/" .. tostring(PD.autoPage),
            n = #buf,
            lines = buf,
        }
    end
    pfOut(string.format("全文本普查完成：%d 条可见字串，已存档（/reload 后游戏外读）。", n))
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFROWS1 = "/dfprofrows"
    SlashCmdList["DUNGEONSFOREVERPROFROWS"] = function(msg)
        local m = string.lower(tostring(msg or "")):gsub("^%s+", ""):gsub("%s+$", "")
        if m == "hide" then
            if PD.page and PD.page.Hide then
                PD.page:Hide()
                pfOut("专业面板已整体隐藏（画面别动）。残留还在 ⇒ 不在面板里；"
                      .. "跟着消失 ⇒ 在面板里。/dfprofrows show 恢复。")
            end
            return
        end
        if m == "show" then
            if PD.page and PD.page.Show then
                PD.page:Show()
                pfOut("专业面板已恢复。")
            end
            return
        end
        if m == "text" then
            PD.CensusText()
            return
        end
        PD.AuditRows(m == "all")
    end
end

if RA.OnPricesChanged then
    RA.OnPricesChanged(function()
        if PD.built and ns.PageVisible(PD.page) then
            PD.RequestRender()
        end
    end)
end
