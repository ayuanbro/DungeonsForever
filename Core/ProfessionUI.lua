local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local SetOutline, SetButtonSelected, Unpack = Host.SetOutline, Host.SetButtonSelected, Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local C_HELP = { 0.58, 0.64, 0.74 }
local CONTENT_W = Host.CONTENT_W
local PAGE_INSET, ROW_CLASS = Host.PAGE_INSET, Host.ROW_CLASS
local FALLBACK_ICON = Host.FALLBACK_ICON

local D  = ns.ProfData
local R
local function RGet(k)
    if not R then
        R = ns.ProfRecipes
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

function PD.AuctionatorStatusText()
    local bridge = ns.AuctionBridge
    local status = bridge and bridge.Status and bridge.Status()
    local state = status and status.state
    if state == "missing" then return L["未安装 Auctionator"] end
    if state == "disabled" then return L["Auctionator 已安装但未启用，请启用后重载界面。"] end
    if state == "loading" or (not state and not (RA and RA.Available and RA.Available())) then
        return L["Auctionator 正在初始化"]
    end
    return L["暂无有效拍卖行价格；请扫描或更新价格。"]
end

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
PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = PD.CARD_TOP + 8, 24, 76, 84
PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 8
PD.BODY_BOT = PD.CARD_INSET + 8
PD.FAC_ICON = {
    a = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    h = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}
PD.TOOL_H, PD.TOOL_GAP, PD.TOOL_W = 24, 8, 72
PD.TOOL_BODY_GAP = 8
PD.ROW_H, PD.ROW_H1, PD.TEXT_H = 34, 24, 24

PD.SETTING_DEF = { greyPassed = true, hlCurrent = true }
PD.SETTING_DEF.autoRoute = false
PD.SETTING_DEF.autoOnlyAH = true
PD.SETTING_DEF.autoLearnedOnly = false
PD.SETTING_DEF.autoBuyLimitedFormulas = false
PD.SETTING_DEF.autoSkipUnpricedFormulas = true
PD.SETTING_DEF.autoScheme = "cheapest"
PD.SETTING_DEF.autoSecondaryLeveling = false
PD.SETTING_DEF.solverRoute = false
PD.SETTING_DEF.recoveryEnabled = false
PD.SETTING_DEF.recoveryFeePercent = 5
PD.SETTING_DEF.autoCraftTools = true
PD.RECOVERY_FEES = { 0, 5, 10, 15, 20 }

PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }
PD.SETTING_DEF.autoFromCurrent = true
PD.SETTING_TOG_MAX = 16
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

function PD.CookingRoute()
    local db = ProfDB()
    if db.cookingDefaultSeed == nil then
        db.cookingDefaultSeed = true
        db.cookingRoute = "fishing"
    end
    return db.cookingRoute or "fishing"
end

function PD.CookingFishingMode(slug)
    return (slug or PD.cur) == "cooking" and PD.CookingRoute() == "fishing"
end

function PD.SetCookingRoute(mode)
    mode = (mode == "fishing") and "fishing" or "standard"
    if PD.CookingRoute() == mode then return end
    ProfDB().cookingRoute = mode
    if mode == "fishing" then
        PD.StopSolverRoute()
        PD.solverKey = nil
    end
    PD.exclusionsOpen, PD.partnerPicker = false, nil
    PD.autoSnapshot, PD.autoSnapshotSlug = nil, nil
    PD.FlushPolicies()
    PD.LvRecalc()
    if PD.scroll then PD.scroll:SetVerticalScroll(0) end
    ns.PlaySound(1)
end

function PD.SetRouteScheme(key)
    if type(key) ~= "string" or key == "" then return end
    local wasFishing = PD.CookingFishingMode()
    if wasFishing then ProfDB().cookingRoute = "standard" end
    if ProfDB().autoScheme == key and not wasFishing then return end
    ProfDB().autoScheme = key
    if RA then
        if RA.Recalculate and RA.OptionsFor then
            local learned = PD.ProfLearned and PD.ProfLearned() or {}
            local lv = learned[PD.cur] and learned[PD.cur].cur
            RA.Recalculate(PD.cur, RA.OptionsFor(PD.cur, lv))
        elseif RA.Invalidate then
            RA.Invalidate()
        end
    end
    PD.RequestRender()
    if PD.scroll then PD.scroll:SetVerticalScroll(0) end
    ns.PlaySound(1)
end

function PD.ShowSchemeMenu(owner)
    local order = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    if #order == 0 then
        PD.CycleRouteScheme()
        return
    end
    if not (ns.hui and ns.hui.ShowMenu) then
        PD.CycleRouteScheme()
        return
    end
    local fishing = PD.CookingFishingMode()
    local cur = PD.SettingRaw("autoScheme")
    local items = {}
    if PD.cur == "cooking" then
        items[#items + 1] = {
            text = L["钓鱼路线"],
            checked = fishing,
            color = fishing and { 1, 0.82, 0 } or { 0.95, 0.8, 0.45 },
            func = function() PD.SetCookingRoute("fishing") end,
        }
    end
    for _, sk in ipairs(order) do
        local on = (not fishing) and (sk == cur)
        items[#items + 1] = {
            text = (RA.SchemeLabel and RA.SchemeLabel(sk)) or sk,
            checked = on,
            color = on and { 1, 0.82, 0 } or nil,
            func = function() PD.SetRouteScheme(sk) end,
        }
    end
    ns.hui.ShowMenu(items, { owner = owner, anchor = owner })
end

function PD.CycleRouteScheme()
    if PD.CookingFishingMode() then return end
    local order = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    if #order == 0 then return end
    local current, nextIndex = PD.SettingRaw("autoScheme"), 1
    for i, key in ipairs(order) do
        if key == current then nextIndex = (i % #order) + 1; break end
    end
    ProfDB().autoScheme = order[nextIndex]
    if RA then
        if RA.Recalculate and RA.OptionsFor then
            local learned = PD.ProfLearned and PD.ProfLearned() or {}
            local current = learned[PD.cur] and learned[PD.cur].cur
            RA.Recalculate(PD.cur, RA.OptionsFor(PD.cur, current))
        elseif RA.Invalidate then
            RA.Invalidate()
        end
    end
    PD.RequestRender()
    ns.PlaySound(1)
end

function PD.ProfRecalc()
    if RA then
        if RA.Recalculate and RA.OptionsFor then
            local learned = PD.ProfLearned and PD.ProfLearned() or {}
            local lv = learned[PD.cur] and learned[PD.cur].cur
            RA.Recalculate(PD.cur, RA.OptionsFor(PD.cur, lv))
        elseif RA.Invalidate then
            RA.Invalidate()
        end
    end
    PD.RequestRender()
    ns.PlaySound(1)
end

function PD.SetRecoveryEnabled(on)
    on = on and true or false
    if PD.Setting("recoveryEnabled") == on then return end
    ProfDB().recoveryEnabled = on
    PD.ProfRecalc()
end

function PD.SetRecoveryFee(pct)
    pct = tonumber(pct)
    if not pct or pct < 0 or pct > 100 then return end
    pct = math.floor(pct)
    if tonumber(PD.SettingRaw("recoveryFeePercent")) == pct then return end
    ProfDB().recoveryFeePercent = pct
    PD.ProfRecalc()
end

function PD.EngChoiceLabel(value)
    local key = value or "none"
    if key == "goblin" then return L["地精工程学"] end
    if key == "gnomish" then return L["侏儒工程学"] end
    return L["不指定"]
end

function PD.SetEngChoice(value)
    local G = ns.ProfGates
    if not (G and G.SetPlannedChoice) then return end
    if G.GetPlannedChoice() == value then return end
    if not G.SetPlannedChoice(value) then return end
    PD.ProfRecalc()
end

function PD.ShowEngChoiceMenu(owner)
    local G = ns.ProfGates
    if not (G and G.GetPlannedChoice and ns.hui and ns.hui.ShowMenu) then return end
    local cur = G.GetPlannedChoice()
    local items = {}
    for _, opt in ipairs({ "none", "goblin", "gnomish" }) do
        local checked = cur == opt
        items[#items + 1] = {
            text = PD.EngChoiceLabel(opt),
            checked = checked,
            color = checked and { 1, 0.82, 0 } or nil,
            func = function() PD.SetEngChoice(opt) end,
        }
    end
    ns.hui.ShowMenu(items, { owner = owner, anchor = owner })
end

function PD.ShowRecoveryFeeMenu(owner)
    if not (ns.hui and ns.hui.ShowMenu) then return end
    local cur = tonumber(PD.SettingRaw("recoveryFeePercent")) or 5
    local items = {}
    for _, pct in ipairs(PD.RECOVERY_FEES) do
        items[#items + 1] = {
            text = format(L["手续费 %d%%"], pct),
            checked = (pct == cur),
            color = (pct == cur) and { 1, 0.82, 0 } or nil,
            func = function() PD.SetRecoveryFee(pct) end,
        }
    end
    items[#items + 1] = {
        text = L["自定义…"],
        func = function() PD.ShowRecoveryFeeInput() end,
    }
    ns.hui.ShowMenu(items, { owner = owner, anchor = owner })
end

local feeForm

local function BuildFeeForm()
    local f = CreateFrame("Frame", "DungeonsForeverFeeForm", UIParent)
    f:SetFrameStrata("FULLSCREEN_DIALOG")
    f:SetToplevel(true)
    f:SetClampedToScreen(true)
    f:EnableMouse(true)
    f:SetSize(300, 172)
    f:SetPoint("CENTER", UIParent, "CENTER", 0, 60)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(f, 8, ns.hui.layer.L4, "both", true, 1)
    end
    local title = MakeFS(f, 14, { 1, 0.82, 0 })
    title:SetPoint("TOPLEFT", f, "TOPLEFT", 16, -14)
    title:SetText(L["回血手续费"])
    local hint = MakeFS(f, 14, { 0.7, 0.7, 0.7 }, "LEFT")
    hint:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -6)
    hint:SetWidth(268)
    hint:SetWordWrap(true)
    hint:SetText(L["0–25 之间的整数，拍卖行卖出时扣掉的佣金比例"])
    local eb = ns.CreateEditBox(f, 72)
    eb:SetPoint("TOPLEFT", hint, "BOTTOMLEFT", 0, -10)
    eb:SetNumeric(true)
    eb:SetMaxLetters(2)
    eb:SetJustifyH("CENTER")
    eb:SetTextColor(1, 0.82, 0)
    f.eb = eb
    local okBtn = NewButton(f, L["确定"], 64, 24, 14)
    okBtn:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -16, 14)
    SetButtonSelected(okBtn, false)
    local cancelBtn = NewButton(f, L["取消"], 64, 24, 14)
    cancelBtn:SetPoint("RIGHT", okBtn, "LEFT", -8, 0)
    local function closeForm() f:Hide() end
    local function submit()
        local v = tonumber(eb:GetText())
        closeForm()
        if not v then return end
        v = math.floor(v)
        if v < 0 then v = 0 elseif v > 25 then v = 25 end
        PD.SetRecoveryFee(v)
        PD.RequestRender()
    end
    okBtn:SetScript("OnClick", function() submit() end)
    cancelBtn:SetScript("OnClick", function() closeForm() end)
    eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() submit() end)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() closeForm() end)
    if UISpecialFrames then
        local listed = false
        for i = 1, #UISpecialFrames do
            if UISpecialFrames[i] == "DungeonsForeverFeeForm" then listed = true break end
        end
        if not listed then tinsert(UISpecialFrames, "DungeonsForeverFeeForm") end
    end
    return f
end

function PD.ShowRecoveryFeeInput()
    if not feeForm then feeForm = BuildFeeForm() end
    local eb = feeForm.eb
    feeForm:Show()
    eb:SetText(tostring(tonumber(PD.SettingRaw("recoveryFeePercent")) or 5))
    eb:SetFocus()
    eb:SetCursorPosition(#eb:GetText(), 0)
end

function PD.SetAutoCraftTools(on)
    on = on and true or false
    if PD.Setting("autoCraftTools") == on then return end
    ProfDB().autoCraftTools = on
    PD.ProfRecalc()
end

function PD.RecoveryMoney(v)
    if type(v) ~= "number" or v == 0 then return RA.MoneyStr(0, "copper") end
    return RA.MoneyStr(v, "copper")
end

local MONEY_GOLD = "|TInterface\\MoneyFrame\\UI-GoldIcon:0|t"
local MONEY_SILVER = "|TInterface\\MoneyFrame\\UI-SilverIcon:0|t"
local MONEY_COPPER = "|TInterface\\MoneyFrame\\UI-CopperIcon:0|t"

function PD.MoneyBrief(v)
    v = tonumber(v) or 0
    if v < 0 then return "-" .. PD.MoneyBrief(-v) end
    v = math.floor(v + 0.5)
    local g = math.floor(v / 10000)
    local s = math.floor((v % 10000) / 100)
    local c = v % 100
    if g > 0 then
        return format("%d%s%d%s%d%s", g, MONEY_GOLD, s, MONEY_SILVER, c, MONEY_COPPER)
    end
    if s > 0 then return format("%d%s%d%s", s, MONEY_SILVER, c, MONEY_COPPER) end
    return format("%d%s", c, MONEY_COPPER)
end

function PD.GatherMode(slug)
    if slug ~= "mining" then return "gather" end
    if not (LV and type(LV.mining) == "table") then return "gather" end
        return (ProfDB().gatherMode == "smelt") and "smelt" or "gather"
end
function PD.IsGatherRoute()
    return PD.GATHER_SLUGS[PD.cur] and not (PD.cur == "mining" and PD.GatherMode("mining") == "smelt")
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
PD.LV_STEP_X, PD.LV_STEP_W, PD.LV_RNG_X = 6, 34, 52
PD.LV_ICON_X = PD.LV_RNG_X + 90 + PD.TBL_RNG_GAP
PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP
PD.LV_CNT_W = 78
PD.LV_COST_W, PD.LV_COST_R = 88, 6
PD.LV_COUNT_R = 110
PD.LV_MAT_X = 0
PD.LV_NAME_FIXW = 141
PD.LV_MAT_W = 220
PD.LV_MAT_RIGHT = 0
PD.LV_COL_GAP = 16
PD.LV_NAME_W = PD.TBL_NAME_MIN
PD.REC_COST_W = 88
PD.REC_AH_W = 88

PD.GR_LV_X = 6
PD.GR_LOC_X = 88
PD.GR_ICON_W = 20

PD.ROW_CAP = 300
PD.ROW_POOL_CAP = 32
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
PD.shopGroup = false
PD.toolKey = nil
PD.perkOpen = {}
PD.rows, PD.toolBtns = {}, {}
PD.specs = nil
PD.fold = {}
PD.fishAreaOpen = {}

function PD.FoldOn(key)
    return (key and PD.fold[key]) and true or false
end

function PD.ToggleFold(key)
    if not key then return end
    PD.fold[key] = (not PD.fold[key]) or false
    if PD.Render then PD.Render() end
end

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
    local function one(r)
        if r.__noHover then
            if r.__hlOn then PD.SetRowHover(r, false) end
        else
            local over = (r.IsMouseOver and r:IsMouseOver()) and true or false
            if over ~= r.__hlOn then PD.SetRowHover(r, over) end
        end
    end
    for _, r in pairs(PD.rows) do one(r) end
    if PD.sideRows then
        for _, r in pairs(PD.sideRows) do one(r) end
    end
    if PD.ixRoot and PD.ixRoot:IsVisible() then
        for i = 1, #(PD.ixCards or {}) do
            local c = PD.ixCards[i]
            local over = (c.IsMouseOver and c:IsMouseOver()) and true or false
            if over ~= c.__hlOn then PD.SetCardHover(c, over) end
        end
    end
end

PD.PILL_CAP_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\HUIPillCap"
PD.PILL_CAP_W = 5

function PD.MakePill(parent, col, cr)
    local f = CreateFrame("Frame", nil, parent)
    col = col or ((ns.hui and ns.hui.layer and ns.hui.layer.L2) or { 0.11, 0.11, 0.12, 1 })
    local a = col[4] or 1
    local cw = cr or PD.PILL_CAP_W
    f.capL = f:CreateTexture(nil, "BACKGROUND")
    f.capL:SetTexture(PD.PILL_CAP_TEX)
    f.capL:SetTexCoord(0, 0.5, 0, 1)
    f.capL:SetVertexColor(col[1], col[2], col[3], a)
    f.capL:SetWidth(cw)
    f.capL:SetPoint("TOPLEFT", f, "TOPLEFT", 0, 0)
    f.capL:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 0, 0)
    f.capR = f:CreateTexture(nil, "BACKGROUND")
    f.capR:SetTexture(PD.PILL_CAP_TEX)
    f.capR:SetTexCoord(0.5, 1, 0, 1)
    f.capR:SetVertexColor(col[1], col[2], col[3], a)
    f.capR:SetWidth(cw)
    f.capR:SetPoint("TOPRIGHT", f, "TOPRIGHT", 0, 0)
    f.capR:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", 0, 0)
    f.mid = f:CreateTexture(nil, "BACKGROUND")
    f.mid:SetColorTexture(col[1], col[2], col[3], a)
    f.mid:SetPoint("TOPLEFT", f.capL, "TOPRIGHT", 0, 0)
    f.mid:SetPoint("BOTTOMRIGHT", f.capR, "BOTTOMLEFT", 0, 0)
    return f
end

function PD.SegButtons(r)
    local list = r.segBtns
    if list then return list end
    list = {}
    for k = 1, 4 do
        local sb = NewButton(r, "", 60, 20, 12)
        SetButtonSelected(sb, false)
        sb:SetScript("OnClick", function(self)
            if self.__segKey and PD.onTool then PD.onTool(self.__segKey) end
            ns.PlaySound(1)
        end)
        sb:Hide()
        list[k] = sb
    end
    r.segBtns = list
    return list
end

function PD.Row(i)
    local r = PD.rows[i]
    if r then return r end
    r = CreateFrame("Button", nil, PD.child, "BackdropTemplate")
    r:RegisterForClicks("LeftButtonUp", "RightButtonUp")
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
    r.segBtns = false
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
    r.__costZone = CreateFrame("Button", nil, r)
    r.__costZone:Hide()
    PD.WireTipZone(r.__costZone, r)
    r.__cardBg = CreateFrame("Frame", nil, r)
    r.__cardBg:Hide()
    r.__cardBg.__pieces = ns.hui.BuildRoundedBG(r.__cardBg, 6, { 1, 1, 1 }, "both", false, nil, true)
    r.__cardTx = MakeFS(r.__cardBg, 10, C_TEXT, "LEFT")
    r.__cardTx:SetText("")
    r.__cardTx:SetWordWrap(false)
    r.__cardTx:Hide()
    for _, f in ipairs({ r.a, r.b, r.c, r.c2, r.d, r.e, r.f }) do f:SetWordWrap(false) end
    r.tagChip = PD.MakePill(r, (ns.hui and ns.hui.layer and ns.hui.layer.L2) or nil, 4)
    r.tagChip:SetFrameLevel((r:GetFrameLevel() or 0) + 1)
    r.tagChip:Hide()
    r.tagBg = r.tagChip
    r.tagFs = MakeFS(r.tagChip, 10, { 0.42, 0.94, 0.62 }, "CENTER")
    r.tagFs:SetText("")
    r.tagFs:SetPoint("CENTER", r.tagChip, "CENTER", 0, 0)
    r.tagFs:Hide()
    local arrowTex = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\arrow.tga"
    r.foldArrD = r:CreateTexture(nil, "ARTWORK")
    r.foldArrD:SetSize(10, 10)
    r.foldArrD:SetTexture(arrowTex)
    r.foldArrD:SetRotation(math.pi)
    r.foldArrU = r:CreateTexture(nil, "ARTWORK")
    r.foldArrU:SetSize(10, 10)
    r.foldArrU:SetTexture(arrowTex)
    r.foldArrD:Hide()
    r.foldArrU:Hide()
    r.foldZone = CreateFrame("Button", nil, r)
    r.foldZone:RegisterForClicks("LeftButtonUp")
    r.foldZone:SetScript("OnClick", function(self)
        if self.__key and PD.ToggleFold then PD.ToggleFold(self.__key) end
    end)
    r.foldZone:SetScript("OnEnter", function(self)
        PD.SetRowHover(r, true)
        if self.__key then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(L["点击折叠 / 展开该组"], 1, 1, 1, true)
            GameTooltip:Show()
            PD.UnifyTipFont(14)
        end
    end)
    r.foldZone:SetScript("OnLeave", function()
        PD.SetRowHover(r, false)
        GameTooltip:Hide()
    end)
    r.foldZone:Hide()
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
        if not self.__noHover then PD.SetRowHover(self, true) end
        if self.__noTip then return end
        PD.hoverRow = self
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
            PD.UnifyTipFont(14)
        elseif self.__it then
            local extra = self.__tipExtra
            if type(extra) == "function" then extra = extra() end
            DG.ShowItemTip(self, self.__it, extra, self.__tipTitle)
        end
    end)
    r:SetScript("OnLeave", function(self)
        PD.SetRowHover(self, false)
        if PD.hoverRow == self then PD.hoverRow = nil end
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function(self, button)
        if button == "RightButton" and not self.__routePolicy then return end
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
    local cnt, staleJ = 0, nil
    local nCur = PD.curN or 0
    for j = 1, PD.ROW_CAP do
        if PD.rows[j] then
            cnt = cnt + 1
            if not staleJ and j > nCur then staleJ = j end
        end
    end
    if staleJ then
        local rr = PD.rows[staleJ]
        PD.rows[staleJ] = nil
        PD.rows[idx] = rr
        if PD.WipeRow then PD.WipeRow(rr) end
        return rr
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
        if spec and spec.kind ~= "gap" and not spec.__fixed and type(spec.__gtop) == "number" then
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
        if spec and spec.kind ~= "gap" and not spec.__fixed and type(spec.__gtop) == "number" then
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

function PD.SideRow(idx)
    PD.sideRows = PD.sideRows or {}
    local r = PD.sideRows[idx]
    if r then return r end
    if not PD.side then return nil end
    local keepChild, keepRows = PD.child, PD.rows
    PD.child, PD.rows = PD.side, {}
    local ok, made = pcall(PD.Row, idx)
    PD.child, PD.rows = keepChild, keepRows
    if not ok or not made then return nil end
    r = made
    r:SetFrameLevel((PD.side:GetFrameLevel() or 0) + 3)
    r:SetSize(PD.RIGHT_W, PD.ROW_H)
    PD.sideRows[idx] = r
    return r
end

function PD.PaintSide(list)
    PD.sideRows = PD.sideRows or {}
    local used = {}
    for k = 1, #list do
        local spec = list[k]
        local r = PD.SideRow(k)
        if r then
            used[k] = true
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", PD.side, "TOPLEFT", spec.__gx, -spec.__gtop)
            r:SetSize(spec.__gw, spec.__gh)
            r:Show()
            PD.BindRow(r, spec, spec.__gh)
        end
    end
    for idx, rr in pairs(PD.sideRows) do
        if not used[idx] then PD.WipeRow(rr) end
    end
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
    local gTop, gBot
    local sideFix = (PD.sideFixed and PD.side) and true or false
    if PD.side then PD.side:SetShown(sideFix) end
    local sideSpecs = {}
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
        local span = (spec.span == true) or (grid and spec.kind ~= "row" and not spec.noSpan)
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
                if spec.fcol then
                    col = spec.fcol
                elseif spec.col == 2 then
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
            if spec.kind == "exgrid" then
                w = w - 14
            elseif spec.wpad then
                w = w - spec.wpad
            end
            if spec.kind == "row" and col and not spec.sec and not PD.noZebra then
                zc[col] = zc[col] + 1
                spec.z = (zc[col] % 2 == 0)
            else
                spec.z = nil
            end
            spec.__fixed = (sideFix and col == 2) and true or nil
            spec.__gx, spec.__gw, spec.__gtop, spec.__gh = x, w, top, h
            if grid and not span then
                if not gTop or top < gTop then gTop = top end
                if not gBot or (top + h) > gBot then gBot = top + h end
            end
            if spec.__fixed then
                sideSpecs[#sideSpecs + 1] = spec
                if r and r.IsShown and r:IsShown() then r:Hide() end
            elseif (not vis) or ((top + h) > vTop and top < vBot) then
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
    if PD.gridSep then
        if grid and PD.gridSepOn and gTop and gBot and (gBot - gTop) > 24 then
            local sx = PD.LIST_PAD + PD.GRID_LW + PD.COL_GAP / 2
            PD.gridSep:ClearAllPoints()
            PD.gridSep:SetPoint("TOPLEFT", PD.child, "TOPLEFT", sx, -(gTop + 6))
            PD.gridSep:SetHeight(gBot - gTop - 12)
            PD.gridSep:Show()
        else
            PD.gridSep:Hide()
        end
    end
    for i, rr in pairs(PD.rows) do
        if i > n then
            if rr.IsShown and rr:IsShown() then PD.WipeRow(rr) else rr:Hide() end
        end
    end
    if sideFix then
        PD.PaintSide(sideSpecs)
    elseif PD.sideRows then
        for _, rr in pairs(PD.sideRows) do PD.WipeRow(rr) end
    end
    if PD.secCards then
        for i = 1, #PD.secCards do PD.secCards[i]:Hide() end
        for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end
        if PD.sideCards then
            for i = 1, #PD.sideCards do PD.sideCards[i]:Hide() end
        end
    end
    if PD.hasSecs then
        local ciP, ciG = 0, 0
        local ciS = 0
        for s = 1, (PD.secCount or 0) do
            local b = bb[s]
            if b then
                local gold = bgold[s] and true or false
                local idx, pool, holder
                if gold and sideFix then
                    ciS = ciS + 1
                    idx = ciS
                    pool = PD.sideCards
                    holder = PD.side
                elseif gold then
                    ciG = ciG + 1
                    idx = ciG
                    pool = PD.secGoldCards
                    holder = PD.child
                else
                    ciP = ciP + 1
                    idx = ciP
                    pool = PD.secCards
                    holder = PD.child
                end
                local c = pool and pool[idx]
                if c then
                    local padL = PD.secPadL or PD.SEC_PAD_X
                    c:ClearAllPoints()
                    c:SetPoint("TOPLEFT", holder, "TOPLEFT",
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
    local extraH = h1 - math.max(y[1], y[2])
    if sideFix then
        PD.child:SetHeight(y[1] + extraH + 10)
    else
        PD.child:SetHeight(math.max(h1, y[2]) + 10)
    end
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
    r.e:SetWidth(0)
    if r.__costZone then r.__costZone:Hide() end
    r.__spec = spec
    r.__z = spec.z and true or false
    r.__noHover = spec.noHover and true or false
    PD.SetRowHover(r, (not r.__noHover) and r.IsMouseOver and r:IsMouseOver())
    r.__it = spec.it
    r.__noTip = spec.noTip
    r.__lines = spec.lines
    r.__mkLines = spec.mkLines
    r.__linesFirst = spec.linesFirst
    r.__act = spec.act
    r.__routePolicy = spec.lvstep and spec.act and true or nil
    r.__tipTitle = spec.tipTitle
    r.__tipExtra = spec.tipExtra
    r.__named = false
    r.h1:Hide(); r.h2:Hide(); r.h3:Hide(); r.h4:Hide(); r.h5:Hide(); r.h6:Hide()
    if r.__toolBadge then r.__toolBadge:Hide() end
    if r.__roleBadge then r.__roleBadge:Hide() end
    if type(r.segBtns) == "table" then
        for _, sb in pairs(r.segBtns) do sb:Hide() end
    end
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
        local auxFs = 14
        local fl = ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE"
        local _, bfs = r.b:GetFont()
        local wb = auxFs
        if bfs ~= wb then r.b:SetFont(ns.FONT, wb, fl) end
        local _, cfs = r.c:GetFont()
        local wc = auxFs
        if cfs ~= wc then r.c:SetFont(ns.FONT, wc, fl) end
    end
    PD.ClearMats(r)
    PD.ClearMatSegs(r)
    if spec._matsPending then PD.FinishSpecMats(spec) end
    PD.RowBorder(r, spec.cur)
    r.tagFs:Hide()
    r.tagChip:Hide()
    if r.foldArrD then r.foldArrD:Hide() end
    if r.foldArrU then r.foldArrU:Hide() end
    if r.foldZone then r.foldZone:Hide() end
    if r.__skchip then r.__skchip:Hide() end
    if r.__subLinks then
        for k = 1, #r.__subLinks do r.__subLinks[k]:Hide() end
    end
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
    if r.__ex then
        for _, c in pairs(r.__ex) do c:Hide() end
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
        if spec.foldKey and r.foldZone and r.foldArrD then
            local key = spec.foldKey
            local open = not PD.FoldOn(key)
            local ax, ay = 6, 0
            if itemID or iconName then ax = 32 end
            for _, at in ipairs({ r.foldArrD, r.foldArrU }) do
                at:SetVertexColor(C_WHITE[1], C_WHITE[2], C_WHITE[3], 0.8)
                at:ClearAllPoints()
                at:SetPoint("LEFT", r, "LEFT", ax, ay)
                at:Show()
            end
            r.foldArrD:SetShown(open)
            r.foldArrU:SetShown(not open)
            r.a:ClearAllPoints()
            r.a:SetPoint("LEFT", r, "LEFT", ax + 14, 0)
            r.foldZone.__key = key
            r.foldZone:ClearAllPoints()
            r.foldZone:SetPoint("TOPLEFT", r, "TOPLEFT", ax - 4, 2)
            r.foldZone:SetPoint("BOTTOMRIGHT", r.a, "BOTTOMRIGHT", 4, -2)
            r.foldZone:SetFrameLevel((r:GetFrameLevel() or 0) + 2)
            r.foldZone:Show()
        end
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
        if spec.suffix and spec.suffix ~= "" then
            r.c2:SetTextColor(Unpack(C_GREY))
            r.c2:SetText(spec.suffix)
            r.c2:ClearAllPoints()
            r.c2:SetWordWrap(false)
            r.c2:SetPoint("LEFT", r.a, "RIGHT", 10, 0)
        end
        if spec.segs then
            local segs = PD.SegButtons(r)
            local prev
            for k = 1, 4 do
                local bt = segs[k]
                local seg = spec.segs[k]
                if seg then
                    local w = select(1, PD.ToolSize(seg.text))
                    bt:SetSize(w, 20)
                    bt:ClearAllPoints()
                    bt:SetPoint("LEFT", prev or r.a, "RIGHT", prev and 6 or 12, 0)
                    bt:SetText(seg.text)
                    SetButtonSelected(bt, seg.on and true or false)
                    bt:GetFontString():SetTextColor(Unpack(seg.on and C_WHITE or C_GREY))
                    bt.__segKey = seg.key
                    bt:Show()
                    prev = bt
                else
                    bt:Hide()
                end
            end
        elseif type(r.segBtns) == "table" then
            for _, sb in pairs(r.segBtns) do sb:Hide() end
        end
        if spec.tag then
            PD.PaintTag(r, spec.tag)
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
        local columns = {
            {r.a, L["步骤"], "LEFT", PD.LV_STEP_X},
            {r.d, L["等级范围"], "LEFT", PD.LV_RNG_X},
            {r.e, L["配方"], "LEFT", PD.LV_NAME_X},
            {r.b, L["材料"], "LEFT", PD.LV_MAT_X},
            {r.c, L["制作次数"], "RIGHT", -PD.LV_COUNT_R},
            {r.c2, L["成本"], "RIGHT", -PD.LV_COST_R},
        }
        for _, column in ipairs(columns) do
            local text = column[1]
            text:SetTextColor(Unpack(C_GREY))
            text:SetFont(ns.FONT, 12, hout)
            text:SetText(column[2])
            text:ClearAllPoints()
            text:SetPoint(column[3], r, column[3], column[4], 0)
        end
        r.f:SetText("")
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

    if spec.kind == "exgrid" then
        local list = spec.cards or {}
        local gap, ch, cols = 6, 44, 3
        local W = tonumber(spec.__gw) or 400
        local cw = math.max(120, math.floor((W - gap * (cols - 1)) / cols))
        for k = 1, #list do
            local d = list[k]
            local c = PD.ExCard(r, k)
            c:Show()
            local rowi = math.floor((k - 1) / cols)
            local coli = (k - 1) % cols
            c:ClearAllPoints()
            c:SetPoint("TOPLEFT", r, "TOPLEFT", coli * (cw + gap), -rowi * (ch + gap))
            c:SetSize(cw, ch)
            if d.it then
                c.ic:Show()
                c.ic:SetSize(24, 24)
                SetIcon(c.ic, DG.ItemIcon(d.it))
            else
                c.ic:Hide()
            end
            c.nm:SetText(d.name or "")
            c.st:SetText(d.modeText or "")
            c.st:SetTextColor(Unpack(d.color or C_GREY))
            c.src:SetText(d.src or "")
            c.z.__tipLines = d.tips
            c.z.__it = nil
            c.z.__act = d.act
        end
        local extra = #list + 1
        while r.__ex and r.__ex[extra] do
            r.__ex[extra]:Hide()
            extra = extra + 1
        end
        r.a:SetText(""); r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        r.dv:SetText(""); r.dv:Hide()
        if r.icon then r.icon:Hide() end
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
        local colors = spec.passed and C_DIM or C_TEXT
        r.a:SetTextColor(Unpack(colors))
        r.d:SetTextColor(Unpack(colors))
        r.e:SetTextColor(Unpack(spec.passed and C_DIM or C_GOLD))
        r.c:SetTextColor(Unpack(spec.passed and C_DIM or C_GOLD))
        r.c2:SetTextColor(Unpack(spec.passed and C_DIM or C_GOLD))
        r.a:SetText(tostring(spec.stepIndex or ""))
        r.d:SetText(spec.rng or "")
        r.d:SetFont(ns.FONT, PD.LV_FS, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        r.e:SetText(spec.text or "")
        r.b:SetText("")
        r.c:SetText(spec.cnt or "")
        r.c2:SetText(spec.cost or "")
        r.f:SetText("")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", PD.LV_STEP_X, 0)
        r.d:ClearAllPoints()
        r.d:SetPoint("LEFT", r, "LEFT", PD.LV_RNG_X, PD.TBL_NAME_DY)
        r.e:ClearAllPoints()
        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)
        r.e:SetWidth(PD.LV_NAME_W)
        r.c2:ClearAllPoints()
        r.c2:SetPoint("RIGHT", r, "RIGHT", -PD.LV_COST_R, 0)
        local whyFs = r.__costWhy
        if spec.costWhyShort then
            if not whyFs then
                whyFs = r:CreateFontString(nil, "OVERLAY")
                whyFs:SetFont(ns.FONT, 12, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
                whyFs:SetJustifyH("RIGHT")
                whyFs:SetWordWrap(false)
                r.__costWhy = whyFs
            end
            whyFs:SetText(spec.costWhyShort)
            whyFs:SetTextColor(0.72, 0.72, 0.72)
            whyFs:ClearAllPoints()
            whyFs:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -PD.LV_COST_R, 3)
            whyFs:Show()
            r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.LV_COST_R, -5)
        elseif whyFs then
            whyFs:Hide()
        end
        r.c:ClearAllPoints()
        r.c:SetPoint("RIGHT", r, "RIGHT", -PD.LV_COUNT_R, 0)
        local nw = math.min(r.e:GetStringWidth() or 0, PD.LV_NAME_W)
        local chipX = PD.LV_NAME_X + nw
        local function placeChip(key, item, startX)
            local bd = r[key]
            local base = startX or chipX
            if not item then
                if bd then bd:Hide() end
                return base
            end
            local cardStyle = true
            if not bd then
                bd = DG.MakeBadge(r, item.bg)
                bd:SetFrameLevel((r:GetFrameLevel() or 0) + 2)
                r[key] = bd
            end
            if bd.__wantCol ~= item.bg then
                bd.__wantCol = item.bg
                DG.BadgeTint(bd, item.bg)
            end
            bd.lab:SetText(item.text)
            local fs = cardStyle and 10 or DG.Q_BADGE_FS
            if bd.__fs ~= fs then
                bd.lab:SetFont(ns.FONT, fs, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
                bd.__fs = fs
            end
            local pad = cardStyle and PD.CARD_PAD or DG.Q_BADGE_PAD
            local w = (bd.lab:GetStringWidth() or 16) + pad * 2
            local bh
            if cardStyle then
                local th = bd.lab:GetStringHeight() or 0
                if th <= 0 then th = 12 end
                bh = 2 * (math.floor(th / 2) + 1)
            else
                bh = DG.Q_BADGE_H
            end
            local x = base + DG.Q_BADGE_GAP
            if x + w > PD.LV_MAT_X - DG.Q_BADGE_GAP then
                bd:Hide()
                return base
            end
            bd:SetSize(w, bh)
            bd:ClearAllPoints()
            bd:SetPoint("TOPLEFT", r, "TOPLEFT", x,
                -(PD.TBL_H - bh) / 2 + PD.TBL_NAME_DY)
            bd:Show()
            return x + w
        end
        local chipEnd
        if spec.toolChip then
            chipEnd = placeChip("__toolBadge", spec.toolChip, chipX)
        else
            chipEnd = placeChip("__toolBadge", nil, chipX)
        end
        placeChip("__roleBadge", spec.roleChip, chipEnd)
        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)
        r.icon:ClearAllPoints()
        r.icon:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)
        r.icon:SetDesaturated(spec.passed and true or false)
        if spec.sbVals then PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)
        else PD.HideSkillBar(r) end
        PD.PaintCard(r, spec.card)
        local iz = PD.IconZone(r)
        iz.__it = itemID and { itemID } or nil
        iz.__tipLines = nil
        iz.__act = spec.act and function(zone, button)
            if button == "LeftButton" and IsShiftKeyDown and IsShiftKeyDown() then DG.ItemShiftClick(zone, button)
            else spec.act(zone, button) end
        end or nil
        iz.__tipExtra = spec.tipExtra
        iz:ClearAllPoints()
        iz:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)
        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)
        iz:SetShown(itemID and true or false)
        r.__cardZone:SetFrameLevel(iz:GetFrameLevel() + 1)
        PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed, PD.LV_MAT_RIGHT)
        local costZone = r.__costZone
        if costZone then
            costZone.__tipLines = {{L["成本"] .. ": " .. (spec.cost or "")},
                {L["成本为本步骤新增采购；已在中间产物步骤计入的费用不重复计入。"], 0.7, 0.7, 0.7}}
            if spec.costWhy then
                costZone.__tipLines[#costZone.__tipLines + 1] = {spec.costWhy, 0.95, 0.75, 0.4}
            end
            costZone.__it, costZone.__act = nil, nil
            costZone:ClearAllPoints()
            costZone:SetPoint("RIGHT", r, "RIGHT", -PD.LV_COST_R, 0)
            costZone:SetSize(PD.LV_COST_W + 8, h)
            costZone:SetShown(spec.cost and spec.cost ~= "" or false)
        end
        return
    end

    local padL = showIcon and ((iconName and not itemID) and 28 or 32) or 6
    if r.__costWhy then r.__costWhy:Hide() end
    PD.HideSkillBar(r)
    PD.PaintCard(r, nil)
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
        local dfsW = 14
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
        vz.__tipLines = spec.vlines or PD.VendorLines(spec.src, spec.qItem)
        vz.__act = spec.dact or PD.VendorAct(spec.src)
        vz:ClearAllPoints()
        vz:SetPoint("TOPLEFT", r.dv, "TOPLEFT", 0, 1)
        vz:SetPoint("BOTTOMRIGHT", r.dv, "BOTTOMRIGHT", 0, -1)
        vz:Show()
    end
    if spec.tag then
        PD.PaintTag(r, spec.tag)
    end
    if spec.chip and spec.chip.text and spec.chip.text ~= "" then
        local chip = PD.SkillChip(r)
        chip.fs:SetText(spec.chip.text)
        chip.fs:SetTextColor(Unpack(spec.chip.color or { 0.80, 0.84, 0.90 }))
        chip:SetHeight(16)
        chip:SetWidth(chip.fs:GetStringWidth() + 8)
        chip:ClearAllPoints()
        local anchor = (spec.tag and r.tagChip:IsShown()) and r.tagChip or r.a
        chip:SetPoint("LEFT", anchor, "RIGHT", 6, 0)
        chip:SetFrameLevel((r:GetFrameLevel() or 0) + 2)
        chip:Show()
    end
    local links = spec.links
    if (not links) and spec.subLink then links = { spec.subLink } end
    if links and #links > 0 then
        local x = padL
        for k = 1, #links do
            local lk = links[k]
            if lk and lk.text and lk.text ~= "" then
                local z = PD.SubLinkAt(r, k)
                z:ClearAllPoints()
                z:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", x, 3)
                local lw
                if lk.chip then
                    z.fs:Hide()
                    z.__tipLines = nil
                    z.__act = nil
                    z:EnableMouse(false)
                    local chip = PD.SubChip(z)
                    chip.fs:SetText(lk.text)
                    chip.fs:SetTextColor(Unpack(lk.color or { 0.68, 0.72, 0.78 }))
                    chip:SetHeight(16)
                    chip:SetWidth(chip.fs:GetStringWidth() + 8)
                    chip:ClearAllPoints()
                    chip:SetPoint("LEFT", z, "LEFT", 0, 0)
                    chip:SetFrameLevel((r:GetFrameLevel() or 0) + 2)
                    chip:Show()
                    lw = chip:GetWidth()
                else
                    z:EnableMouse(true)
                    if z.__chip then z.__chip:Hide() end
                    z.fs:Show()
                    z.fs:SetText(lk.text)
                    z.fs:SetTextColor(Unpack(lk.color or { 0.98, 0.82, 0.35 }))
                    z.__tipLines = lk.lines
                    z.__act = lk.act or function() end
                    lw = z.fs:GetStringWidth()
                end
                z:SetSize(lw + 4, 16)
                z:Show()
                x = x + lw + (lk.chip and 12 or 14)
            end
        end
        if h > PD.ROW_H1 then
            local rightW = 0
            if spec.right2 and spec.right2 ~= "" then
                rightW = (r.d:GetStringWidth() or 0) + 10
            end
            local avail = (r:GetWidth() or 0) - x - rightW - 6
            local subTxt = r.b:GetText() or ""
            if avail > 40 then
                r.b:SetText(PD.Fit(subTxt, 11, avail))
            else
                r.b:SetText("")
            end
            r.b:ClearAllPoints()
            r.b:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", x, 4)
        end
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
        PD.UnifyTipFont(14)
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
                PD.UnifyTipFont(14)
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
    local d = ns.EnsureProfTrainers()[PD.cur]
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
                            PD.UnifyTipFont(14)
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
    ns.PhasedStart(36, coroutine.create(function()
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
        bt.__huiKeepTextColor = true
        SetButtonSelected(bt, false)
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
        local bt = NewButton(page, def.text, PD.SUB_W, PD.SUB_H, 14)
        SetButtonSelected(bt, false)
        bt:Hide()
        bt:SetScript("OnClick", function() PD.SetTab(def.key) end)
        PD.subBtns[def.key] = bt
    end
    coroutine.yield()

    PD.trFacBtns = {}
    for i = 1, 2 do
        local k = (i == 1) and "A" or "H"
        local bt = NewButton(page, k == "A" and L["联盟"] or L["部落"], 64, PD.SUB_H, 14)
        bt.__huiKeepTextColor = true
        SetButtonSelected(bt, false)
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

    local gear = NewButton(page, "", PD.SUB_H, PD.SUB_H, 14)
    gear.__huiKeepTextColor = true
    SetButtonSelected(gear, false)
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
    if ns.hui and ns.hui.SetButtonFrameless then ns.hui.SetButtonFrameless(gear, true) end
    coroutine.yield()

    PD.setToggles = {}
    PD.toolBtns = {}

    for i = 1, PD.TOOL_MAX do
        local bt = NewButton(page, "", PD.TOOL_W, PD.TOOL_H, 14)
        bt.__huiKeepTextColor = true
        SetButtonSelected(bt, false)
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            if self.__key and PD.onTool then PD.onTool(self.__key) end
            ns.PlaySound(1)
        end)
        PD.toolBtns[i] = bt
    end
    coroutine.yield()

    PD.LV_TILE_H, PD.LV_TILE_GAP = 64, 8
    PD.SET_CARD_W, PD.SET_CHIP_H, PD.SET_CHIP_GAP = 500, 24, 6
    PD.RES_MIN_W = 262
    PD.HUD_W, PD.IMP_W = 96, 110

    local hudBtn = NewButton(page, "", PD.HUD_W, PD.TOOL_H, 14)
    SetButtonSelected(hudBtn, false)
    hudBtn:Hide()
    PD.hudBtn = hudBtn
    coroutine.yield()

    local impBtn = NewButton(page, L["一键导入购物清单"], PD.IMP_W, PD.TOOL_H, 14)
    SetButtonSelected(impBtn, false)
    impBtn:Hide()
    PD.impBtn = impBtn
    coroutine.yield()
    local actDiv = CreateFrame("Frame", nil, page)
    actDiv:SetFrameLevel(page:GetFrameLevel() + 60)
    actDiv:SetSize(1, 16)
    local actDivTex = actDiv:CreateTexture(nil, "ARTWORK")
    actDivTex:SetAllPoints()
    actDivTex:SetColorTexture(1, 1, 1, 0.14)
    actDiv:Hide()
    PD.actDiv = actDiv
    coroutine.yield()
    local setCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
    setCard:SetSize(PD.SET_CARD_W, PD.LV_TILE_H)
    ns.hui.BuildRoundedBG(setCard, 8, ns.hui.layer.L1, "both", true, 1)
    setCard:Hide()
    PD.setCard = setCard
    coroutine.yield()
    PD.lvTiles = {}
    PD.chipOrder = { "mode", "scheme", "solver", "excl", "target" }
    for _, td in ipairs({
        { key = "mode",   text = L["模式"] },
        { key = "scheme", text = L["路线方案"] },
        { key = "solver", text = L["精确方案"] },
        { key = "excl",   text = L["排除"] },
        { key = "target", text = L["目标等级"] },
    }) do
        local tf = CreateFrame("Button", nil, setCard, "BackdropTemplate")
        tf:SetSize(90, PD.SET_CHIP_H)
        local _, bord = ns.hui.BuildRoundedBG(tf, 6, ns.hui.layer.L2, "both", true, 1)
        tf.__border = bord or {}
        if ns.hui and ns.hui.BuildCapsule then
            tf.__hov = ns.hui.BuildCapsule(tf, 6, ns.hui.layer.L4, 1, 2) or {}
            for _, t in ipairs(tf.__hov) do t:Hide() end
        end
        tf:Hide()
        tf.label = MakeFS(tf, 14, C_GREY, "LEFT")
        tf.label:SetWordWrap(false)
        tf.label:SetText(td.text)
        tf.label:SetPoint("BOTTOMLEFT", tf, "TOPLEFT", 2, 3)
        tf.val = MakeFS(tf, 16, C_WHITE, "CENTER")
        tf.val:SetWordWrap(false)
        tf.val:SetPoint("CENTER", tf, "CENTER", 0, 0)
        tf:EnableMouseWheel(true)
        tf:SetScript("OnMouseWheel", function(self, delta)
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        PD.lvTiles[td.key] = tf
    end
    local resCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
    resCard:SetSize(240, PD.LV_TILE_H)
    resCard:EnableMouse(true)
    resCard:EnableMouseWheel(true)
    resCard:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
    ns.hui.BuildRoundedBG(resCard, 8, ns.hui.layer.L1, "both", true, 1)
    resCard.label = MakeFS(resCard, 14, C_GREY, "LEFT")
    resCard.label:SetWordWrap(false)
    resCard.label:SetPoint("TOPLEFT", resCard, "TOPLEFT", 14, -6)
    resCard.val = MakeFS(resCard, 18, C_GOLD, "LEFT")
    resCard.val:SetWordWrap(false)
    resCard.val:SetPoint("TOPLEFT", resCard, "TOPLEFT", 14, -24)
    resCard.sub = MakeFS(resCard, 12, C_GREY, "LEFT")
    resCard.sub:SetWordWrap(false)
    resCard.sub:SetPoint("BOTTOMLEFT", resCard, "BOTTOMLEFT", 14, 5)
    resCard.sub:Hide()
    resCard.badge = CreateFrame("Frame", nil, resCard, "BackdropTemplate")
    local _, bb = ns.hui.BuildRoundedBG(resCard.badge, 4, ns.hui.layer.L3, "both", true, 1)
    resCard.badge.__border = bb or {}
    resCard.badge:SetHeight(14)
    resCard.badge:SetPoint("TOPRIGHT", resCard, "TOPRIGHT", -14, -8)
    resCard.badge.fs = MakeFS(resCard.badge, 12, C_GREY, "CENTER")
    resCard.badge.fs:SetWordWrap(false)
    resCard.badge.fs:SetPoint("CENTER", resCard.badge, "CENTER", 0, 0)
    resCard.badge:Hide()
    resCard:Hide()
    PD.lvTiles.cost = resCard
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
    PD.lvTiles.scheme:SetScript("OnClick", function(self) PD.ShowSchemeMenu(self) end)
    PD.lvTiles.solver:SetScript("OnClick", function()
        if PD.CookingFishingMode() then return end
        local on = not PD.Setting("solverRoute")
        ProfDB().solverRoute = on
        if on then ProfDB().autoRoute = true end
        if PD.StopSolverRoute then PD.StopSolverRoute() end
        PD.solverKey = nil
        PD.solverPaintRes = nil
        PD.autoSnapshot = nil
        PD.autoSnapshotSlug = nil
        if PD.ProcureClear then PD.ProcureClear() end
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    PD.lvTiles.excl:SetScript("OnClick", function()
        PD.exclusionsOpen = not PD.exclusionsOpen
        PD.partnerPicker = nil
        if not PD.exclusionsOpen then PD.FlushPolicies() end
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    function PD.SetBadge(text, r, g, b)
        local f = PD.lvTiles and PD.lvTiles.cost and PD.lvTiles.cost.badge
        if not f then return end
        if not text or text == "" then f:Hide() return end
        f.fs:SetText(text)
        f.fs:SetTextColor(r or 0.95, g or 0.75, b or 0.4, 1)
        f:SetWidth(math.max(30, math.ceil(f.fs:GetStringWidth() or 20) + 8))
        f:Show()
    end
    function PD.SetSub(text)
        local card = PD.lvTiles and PD.lvTiles.cost
        local f = card and card.sub
        if not f then return end
        if not text or text == "" then f:Hide() return end
        f:SetText(text)
        local w = math.max(60, (card:GetWidth() or 240) - 28)
        if (f:GetStringWidth() or 0) > w then f:SetText(PD.Fit(text, 12, w)) end
        f:Show()
    end
    function PD.PlaceCards(n)
        local set = PD.setCard
        local res = PD.lvTiles and PD.lvTiles.cost
        if not (set and res and n and n > 0) then return end
        local totalW = PD.RIGHT_W - PD.LIST_PAD
        local setW
        if n >= 4 then
            setW = math.min(PD.SET_CARD_W, totalW - PD.RES_MIN_W - PD.LV_TILE_GAP)
        else
            setW = 24 + n * 130 + (n - 1) * PD.SET_CHIP_GAP
        end
        local resW = totalW - setW - PD.LV_TILE_GAP
        set:SetSize(setW, PD.LV_TILE_H)
        set:ClearAllPoints()
        set:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X, -PD.BODY_TOP)
        set:Show()
        res:SetSize(resW, PD.LV_TILE_H)
        res:ClearAllPoints()
        res:SetPoint("TOPLEFT", set, "TOPLEFT", setW + PD.LV_TILE_GAP, 0)
        res:Show()
        local cw = math.floor((setW - 24 - (n - 1) * PD.SET_CHIP_GAP) / n)
        local x = 12
        for _, key in ipairs(PD.chipOrder) do
            local tf = PD.lvTiles[key]
            if tf.__use then
                tf:SetSize(cw, PD.SET_CHIP_H)
                tf:ClearAllPoints()
                tf:SetPoint("TOPLEFT", set, "TOPLEFT", x, -28)
                local vtxt = (tf.val and tf.val:GetText()) or ""
                local vfs = 16
                if vtxt ~= "" and PD.TextW(vtxt, 16) > cw - 10 then vfs = 14 end
                if tf.__vfs ~= vfs then
                    tf.__vfs = vfs
                    tf.val:SetFont(ns.FONT, vfs,
                        ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
                end
                tf:Show()
                x = x + cw + PD.SET_CHIP_GAP
            else
                tf:Hide()
            end
        end
    end
    do
        local tf = PD.lvTiles.target
        local eb = CreateFrame("EditBox", nil, tf, "BackdropTemplate")
        local _, ebBord = ns.hui.BuildRoundedBG(eb, 6, ns.hui.layer.L3, "both", true, 1)
        eb.__border = ebBord or {}
        PD.PaintTileBorder(eb, { 1, 1, 1, 0.10 })
        eb:SetSize(60, 20)
        eb:SetPoint("CENTER", tf, "CENTER", 0, 0)
        eb:SetFont(ns.FONT, 14, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
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
    local gsep = child:CreateTexture(nil, "ARTWORK")
    gsep:SetColorTexture(1, 1, 1, 0.12)
    gsep:SetWidth(1)
    gsep:Hide()
    PD.gridSep = gsep
    hooksecurefunc(scroll, "SetVerticalScroll", function(_, v) PD.__scrollV = v end)
    coroutine.yield()

    local side = CreateFrame("Frame", nil, page)
    side:SetPoint("TOPLEFT", scroll, "TOPLEFT", 0, 0)
    side:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", 0, 0)
    side:SetFrameLevel((scroll:GetFrameLevel() or 0) + 20)
    side:Hide()
    PD.side = side
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
        elseif PD.tab == "recipe" or PD.tab == "leveling" then
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
        hp.icon = hp:CreateTexture(nil, "ARTWORK")
        hp.icon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\HelpIcon")
        hp.icon:SetSize(14, 14)
        hp.icon:SetPoint("CENTER")
        hp.icon:SetVertexColor(C_HELP[1], C_HELP[2], C_HELP[3])
        hp:SetScript("OnEnter", function(self)
            self.icon:SetVertexColor(1, 0.82, 0)
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
            PD.UnifyTipFont(14)
        end)
        hp:SetScript("OnLeave", function(self)
            self.icon:SetVertexColor(C_HELP[1], C_HELP[2], C_HELP[3])
            GameTooltip:Hide()
        end)
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
    PD.sideCards = {}
    for i = 1, PD.SEC_CARD_MAX do
        local c = CreateFrame("Frame", nil, PD.side)
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L3, "both", true, 1)
        c:Hide()
        PD.sideCards[i] = c
    end
    coroutine.yield()

    PD.built = true
    PD.building = false
    if PD.wantOpen then
        PD.wantOpen = nil
        PD.EnsureCur()
        PD.RequestRender()
    end
    end))
end

local NAV_SKILL_SLUG = {
    [171] = "alchemy",     [164] = "blacksmithing", [333] = "enchanting",
    [202] = "engineering", [165] = "leatherworking", [197] = "tailoring",
    [186] = "mining",      [182] = "herbalism",     [393] = "skinning",
    [185] = "cooking",     [356] = "fishing",       [129] = "first-aid",
}

local learnedMemo, learnedT
function PD.ProfLearned(cached)
    local now = cached and GetTime and GetTime() or nil
    if now and learnedMemo and (now - (learnedT or 0)) < 0.5 then return learnedMemo end
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
    if now then learnedMemo, learnedT = out, now end
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
        SetButtonSelected(bt, sel)
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
    local TRD = ns.EnsureProfTrainers()[slug]
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
                SetButtonSelected(bt, sel)
                local sfs = bt:GetFontString()
                if sfs then
                    if sel then
                        sfs:SetTextColor(1, 1, 1, 1)
                    else
                        sfs:SetTextColor(Unpack(C_GREY))
                    end
                end
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
            SetButtonSelected(PD.setGear, PD.setOpen and true or false)
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
                    SetButtonSelected(bt, sel)
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
        if PD.tab == "leveling" and not PD.setOpen and not PD.IsGatherRoute() then
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
    local need = PD.TextW(text, 14) + PD.TOOL_PADX
    local w = math.ceil(math.max(PD.TOOL_MIN_W, math.min(PD.TOOL_MAX_W, need)))
    local shown = text
    if need > PD.TOOL_MAX_W then shown = PD.Fit(text, 14, PD.TOOL_MAX_W - PD.TOOL_PADX) end
    return w, shown
end

function PD.PaintTool(list, handler, yoff)
    PD.onTool = handler
    list = list or {}
    yoff = yoff or 0
    local _T0, _MK = PD.__pfT0, PD.__pfMark
    local _AD = PD.__pfAdd
    local n = math.min(#list, PD.TOOL_MAX)
    local wid, txt, rxs = {}, {}, {}
    for i = 1, n do
        local def = list[i]
        if def.icon then
            wid[i] = PD.TOOL_H
            txt[i] = ""
        elseif def.plain then
            wid[i] = math.ceil(PD.TextW(def.text, 14)) + 6
            txt[i] = def.text
        else
            wid[i], txt[i] = PD.ToolSize(def.text)
        end
    end
    local rightTotal = 0
    for i = 1, n do
        if list[i].align == "right" then
            rightTotal = rightTotal + wid[i] + (list[i].gap or PD.TOOL_GAP)
        end
    end
    local leftLim = PD.RIGHT_W - (PD.SearchReserve() or 0) - rightTotal
    if rightTotal > 0 and (leftLim < 160 or rightTotal > PD.RIGHT_W * 0.62) then
        rightTotal = 0
        leftLim = PD.RIGHT_W - (PD.SearchReserve() or 0)
    end
    local rcur = PD.RIGHT_W - rightTotal
    for i = 1, n do
        if rightTotal > 0 and list[i].align == "right" then
            rxs[i] = rcur
            rcur = rcur + wid[i] + (list[i].gap or PD.TOOL_GAP)
        end
    end
    local x, row = 0, 0
    local xEnd = 0
    for i = 1, PD.TOOL_MAX do
        local bt = PD.toolBtns[i]
        local def = (i <= n) and list[i] or nil
        if def then
            local w, text = wid[i], txt[i]
            if rxs[i] then
                row = 0
                x = rxs[i]
            elseif x > 0 and x + w > leftLim then
                row = row + 1; x = 0
            end
            local key = "1|" .. w .. "|" .. x .. "|" .. row .. "|"
                        .. tostring(def.on) .. "|" .. tostring(def.primary) .. "|"
                        .. tostring(def.tone) .. "|" .. text .. "|" .. tostring(def.right)
                        .. "|" .. tostring(def.icon) .. "|" .. tostring(def.glow)
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
                if def.tip then
                    bt.__tipLines = def.tip
                    if not bt.__tipHooked then
                        bt.__tipHooked = true
                        bt:HookScript("OnEnter", function(self)
                            local lines = self.__tipLines
                            if not lines or #lines == 0 then return end
                            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                            GameTooltip:ClearLines()
                            for _, ln in ipairs(lines) do
                                if ln[1] and ln[1] ~= "" then
                                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                                end
                            end
                            GameTooltip:Show()
                            PD.UnifyTipFont(14)
                        end)
                        bt:HookScript("OnLeave", function() GameTooltip:Hide() end)
                    end
                elseif not def.icon then
                    bt.__tipLines = nil
                end
                if def.icon then
                    bt:EnableMouse(true)
                    SetOutline(bt, false, 1, 0.82, 0)
                elseif def.plain then
                    bt:EnableMouse(false)
                    SetOutline(bt, false, 1, 0.82, 0)
                    bt:GetFontString():SetTextColor(Unpack(def.color or C_WHITE))
                else
                    bt:EnableMouse(true)
                    SetOutline(bt, false, 1, 0.82, 0)
                    local hot = (def.on or def.primary) and true or false
                    SetButtonSelected(bt, hot, "main")
                    local bfs = bt:GetFontString()
                    if hot then
                        bfs:SetTextColor(1, 1, 1, 1)
                    elseif def.tone == "blue" then
                        bfs:SetTextColor(0.37, 0.66, 0.83, 1)
                    else
                        bfs:SetTextColor(Unpack(C_GREY))
                    end
                end
                if def.glow then
                    PD.GlowBorder(bt)
                elseif bt.__glowOn then
                    PD.GlowBorder(bt, false)
                end
                if _MK then _MK("闸-文本", _m0) end
                _m0 = _T0 and _T0()
                bt:Show()
                if _MK then _MK("闸-显示", _m0) end
                if _MK then _MK("闸-合计", _g0) end
            end
            bt.__key = def.key
            bt.__row = row
            if def.icon then
                if bt.__warn then bt.__warn:Hide(); bt.__warn.__tipLines = nil end
                if bt.__rightFs then bt.__rightFs:Hide() end
                local ic = bt.__icon
                if not ic then
                    ic = bt:CreateTexture(nil, "ARTWORK")
                    ic:SetSize(18, 18)
                    ic:SetPoint("CENTER", bt, "CENTER", 0, 0)
                    bt.__icon = ic
                    bt:SetScript("OnEnter", function(self)
                        local lines = self.__tipLines
                        if not lines or #lines == 0 then return end
                        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                        GameTooltip:ClearLines()
                        for _, ln in ipairs(lines) do
                            if ln[1] and ln[1] ~= "" then
                                GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                            end
                        end
                        GameTooltip:Show()
                        PD.UnifyTipFont(14)
                    end)
                    bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
                end
                ic:SetTexture(def.icon)
                ic:SetVertexColor(Unpack(def.iconColor or C_WHITE))
                ic:Show()
                bt.__tipLines = def.tip
                if ns.hui and ns.hui.SetButtonFrameless then ns.hui.SetButtonFrameless(bt, true) end
            else
                if bt.__icon then bt.__icon:Hide() end
                bt.__tipLines = nil
                if ns.hui and ns.hui.SetButtonFrameless then ns.hui.SetButtonFrameless(bt, false) end
            end
            if def.plain then
                local wz = PD.WarnChip(bt, true)
                local anchor, gap = bt, 8
                if def.warn and def.warn[1] then
                    wz:ClearAllPoints()
                    wz:SetPoint("LEFT", bt, "RIGHT", 2, 0)
                    wz.__tipLines = def.warn
                    wz:Show()
                    anchor, gap = wz, 6
                else
                    wz:Hide(); wz.__tipLines = nil
                end
                if def.right then
                    local rf = bt.__rightFs
                    if not rf then
                        rf = MakeFS(bt, 11, C_GREY, "LEFT")
                        rf:SetWordWrap(false)
                        bt.__rightFs = rf
                    end
                    rf:ClearAllPoints()
                    rf:SetPoint("LEFT", anchor, "RIGHT", gap, 0)
                    rf:SetText(def.right)
                    rf:Show()
                elseif bt.__rightFs then
                    bt.__rightFs:Hide()
                end
            elseif bt.__warn then
                bt.__warn:Hide(); bt.__warn.__tipLines = nil
            end
            if not rxs[i] then
                x = x + w + (def.gap or PD.TOOL_GAP)
                xEnd = x
            end
        else
            if bt.__ptk ~= "0" then bt.__ptk = "0"; bt:Hide() end
            if bt.__rightFs then bt.__rightFs:Hide() end
            if bt.__warn then bt.__warn:Hide(); bt.__warn.__tipLines = nil end
            if bt.__icon then bt.__icon:Hide() end
            bt.__tipLines = nil
            bt.__key = nil
        end
    end
    for i = 1, n do
        local def = list[i]
        local bt = PD.toolBtns[i]
        if def and def.plain and def.right and bt.__rightFs then
            local rf = bt.__rightFs
            local nb
            if PD.hudBtn and PD.hudBtn:IsShown() then
                nb = PD.hudBtn
            else
                for j = i + 1, n do
                    local b2 = PD.toolBtns[j]
                    if b2.__row == bt.__row then nb = b2; break end
                end
            end
            rf:ClearAllPoints()
            if nb then
                rf:SetPoint("RIGHT", nb, "LEFT", -10, 0)
            else
                rf:SetPoint("LEFT", bt, "RIGHT", 8, 0)
            end
        end
    end
    local actBase = PD.RIGHT_W - rightTotal
    if xEnd > actBase then actBase = xEnd end
    PD.actX = actBase
    local actRow, ax, placedCount = 0, actBase, 0
    local function placeAction(btn, want)
        if not (btn and btn:IsShown()) then return end
        local bw = btn:GetWidth() or want
        local try = ax - bw
        if placedCount > 0 or rightTotal > 0 then try = try - PD.TOOL_GAP end
        if try < xEnd + PD.TOOL_GAP then
            actRow = actRow + 1
            ax = PD.RIGHT_W
            placedCount = 0
            try = ax - bw
        end
        ax = try
        placedCount = placedCount + 1
        btn:ClearAllPoints()
        btn:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + ax,
                     -(PD.BODY_TOP + yoff + actRow * (PD.TOOL_H + PD.TOOL_GAP)))
    end
    placeAction(PD.hudBtn, PD.HUD_W)
    placeAction(PD.impBtn, PD.IMP_W)
    if PD.actDiv then
        if rightTotal > 0 and ax > 24 then
            PD.actDiv:ClearAllPoints()
            PD.actDiv:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + ax - 10,
                               -(PD.BODY_TOP + yoff + actRow * (PD.TOOL_H + PD.TOOL_GAP)
                                 + (PD.TOOL_H - 16) / 2))
            PD.actDiv:Show()
        else
            PD.actDiv:Hide()
        end
    end
    local rows = (n > 0) and (row + 1) or 0
    rows = rows + actRow
    if rows == 0 and ((PD.hudBtn and PD.hudBtn:IsShown()) or (PD.impBtn and PD.impBtn:IsShown())) then
        rows = 1
    end
    PD.toolRows = rows
    return (rows > 0) and (rows * (PD.TOOL_H + PD.TOOL_GAP) + PD.TOOL_BODY_GAP) or 0
end

function PD.PaintToolProgress(text, frac)
    local rf = PD.__progFs
    if not rf then
        local holder = CreateFrame("Frame", nil, PD.page)
        holder:SetFrameLevel(PD.page:GetFrameLevel() + 100)
        holder:SetSize(400, PD.SUB_H)
        rf = MakeFS(holder, 14, C_WHITE, "RIGHT")
        rf:SetWordWrap(false)
        rf:SetPoint("RIGHT", holder, "RIGHT", 0, 0)
        PD.__progFs = rf
        PD.__progHolder = holder
    end
    if text and text ~= "" then
        local holder = PD.__progHolder
        holder:ClearAllPoints()
        if PD.setGear then
            holder:SetPoint("RIGHT", PD.setGear, "LEFT", -8, 0)
        else
            holder:SetPoint("RIGHT", PD.page, "RIGHT", -(PD.LIST_PAD + 40), -(PD.SUB_Y + PD.SUB_H / 2))
        end
        rf:SetText(text)
        rf:Show()
        holder:Show()
    else
        PD.__progHolder:Hide()
    end
    PD.PaintToolBar(frac)
end

function PD.PaintToolBar(frac)
    local bar = PD.__progBar
    if not bar then
        local holder = PD.__progHolder
        if not holder then return end
        bar = CreateFrame("Frame", nil, holder)
        bar:SetSize(120, 6)
        bar:SetPoint("RIGHT", PD.__progFs, "LEFT", -8, 0)
        local bg = bar:CreateTexture(nil, "BACKGROUND")
        bg:SetAllPoints()
        bg:SetColorTexture(0, 0, 0, 0.72)
        local fill = bar:CreateTexture(nil, "ARTWORK")
        fill:SetPoint("LEFT", bar, "LEFT", 1, 0)
        fill:SetSize(1, 4)
        fill:SetColorTexture(0.93, 0.76, 0.32, 1)
        PD.__progBar = bar
        PD.__progFill = fill
    end
    if type(frac) ~= "number" then bar:Hide(); return end
    if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
    local w = bar:GetWidth()
    if not w or w < 1 then w = 120 end
    local fillW = math.max(1, math.floor((w - 2) * frac + 0.5))
    PD.__progFill:SetSize(fillW, 4)
    if not PD.__progHolder or not PD.__progHolder:IsShown() then bar:Hide() else bar:Show() end
end

function PD.PaintToolStale(text)
    local rf = PD.__staleFs
    if not rf then
        local holder = CreateFrame("Frame", nil, PD.page)
        holder:SetFrameLevel(PD.page:GetFrameLevel() + 100)
        holder:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT", 0, 0)
        holder:SetSize(300, 20)
        rf = MakeFS(holder, 12, C_GOLD, "RIGHT")
        rf:SetWordWrap(false)
        rf:SetPoint("RIGHT", holder, "RIGHT", 0, 0)
        PD.__staleFs = rf
        PD.__staleHolder = holder
    end
    if text and text ~= "" and PD.setGear and PD.setGear:IsShown() then
        local holder = PD.__staleHolder
        holder:ClearAllPoints()
        holder:SetPoint("RIGHT", PD.setGear, "LEFT", -8, 0)
        rf:SetText(text)
        rf:Show()
        holder:Show()
    else
        PD.__staleHolder:Hide()
    end
end

function PD.UnifyTipFont(size)
    local n = (GameTooltip.NumLines and GameTooltip:NumLines()) or 0
    if n <= 0 then return end
    local base = _G["GameTooltipTextLeft1"]
    local path, sz, flags
    if base and base.GetFont then path, sz, flags = base:GetFont() end
    if not path then return end
    local want = tonumber(size) or tonumber(sz) or 13
    flags = flags or ""
    local sum0 = 0
    for i = 1, n do
        local l = _G["GameTooltipTextLeft" .. i]
        if l and l.GetStringHeight then sum0 = sum0 + (l:GetStringHeight() or 0) end
    end
    for i = 1, n do
        local l = _G["GameTooltipTextLeft" .. i]
        if l and l.SetFont then l:SetFont(path, want, flags) end
        local rr = _G["GameTooltipTextRight" .. i]
        if rr and rr.SetFont then rr:SetFont(path, want, flags) end
    end
    local maxW = 0
    for i = 1, n do
        local l = _G["GameTooltipTextLeft" .. i]
        if l and l.SetText and l.SetWidth then
            l:SetWidth(4000)
            l:SetText(l:GetText())
            maxW = math.max(maxW, l:GetStringWidth() or 0)
        end
    end
    maxW = math.min(maxW, 460)
    local sum1 = 0
    for i = 1, n do
        local l = _G["GameTooltipTextLeft" .. i]
        if l then
            l:SetWidth(maxW)
            l:SetText(l:GetText())
            sum1 = sum1 + (l:GetStringHeight() or 0)
        end
    end
    if GameTooltip.SetWidth and GameTooltip.SetHeight and maxW > 0 then
        local pad = (GameTooltip:GetHeight() or 0) - sum0
        GameTooltip:SetWidth(maxW + 20)
        GameTooltip:SetHeight(sum1 + pad)
    end
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
        PD.UnifyTipFont(14)
    end)
    tf:SetScript("OnLeave", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Hide() end end
        GameTooltip:Hide()
    end)
end

function PD.PaintGatherTiles()
    local tiles = PD.lvTiles
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "scheme", "solver", "excl", "target" }) do
            tiles[k].__use = false
            tiles[k]:Hide()
        end
        if PD.setCard then PD.setCard:Hide() end
        tiles.cost:Hide()
        return 0
    end
    tiles.solver.__use, tiles.excl.__use, tiles.target.__use = false, false, false
    tiles.mode.__use, tiles.scheme.__use = true, true
    tiles.mode:SetScript("OnClick", nil)
    tiles.scheme:SetScript("OnClick", nil)
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
    if PD.cur == "fishing" and curLv then
        local guide = ns.ProfFishingRoutes
        for index, step in ipairs(guide and guide.fishingSteps or {}) do
            if curLv >= step.from and (curLv < step.to or (index == #guide.fishingSteps and curLv == step.to)) then
                prog = format(L["%d - %d"], step.from, step.to)
                break
            end
        end
    end
    tiles.mode.label:SetText(L["当前技能"])
    tiles.mode.val:SetText(curLv and tostring(curLv) or L["未学"])
    PD.TipTile(tiles.mode, { { L["读取角色当前的专业技能值"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
    tiles.scheme.label:SetText(L["路线进度"])
    local smelt = PD.GatherMode("mining") == "smelt"
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
    PD.PaintTileBorder(tiles.scheme, { 1, 1, 1, 0.10 })
    tiles.cost.label:SetText(L["路线范围"])
    tiles.cost.val:SetText("1 - 300")
    tiles.cost.val:SetTextColor(Unpack(C_WHITE))
    PD.SetBadge(nil)
    PD.SetSub(nil)
    PD.TipTile(tiles.cost, { { L["静态推荐路线（全程显示）：按资料整理的采集区间推进，不含价格与概率，无需价格插件"], 0.7, 0.7, 0.7 } })
    PD.PlaceCards(2)
    return PD.LV_TILE_H + 8
end

function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    if PD.IsGatherRoute() then return PD.PaintGatherTiles() end
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "scheme", "solver", "excl", "target" }) do
            tiles[k].__use = false
            tiles[k]:Hide()
        end
        if PD.setCard then PD.setCard:Hide() end
        tiles.cost:Hide()
        return 0
    end
    for _, k in ipairs({ "mode", "scheme", "solver", "excl", "target" }) do tiles[k].__use = true end
    local s = PD.lvSummary or {}
    local fishRoute = PD.CookingFishingMode()
    local v = PD.LvTarget()
    local auto = s.auto and true or false
    local warnAuto = s.autoSetting and (not s.ahOK or s.feasible == false)
    local fixedOnly = (PD.cur == "poisons")
    tiles.solver.__use = ((not fishRoute) and (not fixedOnly) and ns.ProfSolverRun) and true or false
    if fixedOnly then
        tiles.mode:SetScript("OnClick", nil)
    else
        tiles.mode:SetScript("OnClick", function()
            if PD.CookingFishingMode() then
                PD.SetCookingRoute("standard")
                return
            end
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
        tiles.mode.label:SetText(L["模式"])
        tiles.mode.val:SetText(fishRoute and L["纯钓鱼"] or (auto and L["自动计算"] or L["固定路线"]))
        tiles.mode.val:SetTextColor(Unpack(C_WHITE))
        PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
        local modeLines = {
            { fishRoute and L["鱼类自行钓取；其他材料只使用不限量商人货物。"]
                   or auto and L["自动计算：比较采购、自制与配方依赖"]
                   or L["固定路线：按资料整理的分段练法逐段冲技能"], 1, 0.82, 0 },
            { fishRoute and L["点击返回普通路线"] or L["点击在固定 / 自动之间切换"], 0.7, 0.7, 0.7 },
        }
        if warnAuto then
            modeLines[#modeLines + 1] = { L["计算结果尚不完整，请查看路线中的缺价或配方提示。"],
                                          0.95, 0.75, 0.4 }
        end
        TipOn(tiles.mode, modeLines)
    end
    local sch = s.scheme or "cheapest"
    tiles.scheme.label:SetText(L["路线方案"])
    tiles.scheme.val:SetText(fishRoute and L["钓鱼路线"] or ((RA and RA.SchemeLabel) and RA.SchemeLabel(sch) or L["最省钱"]))
    if fixedOnly then
        tiles.scheme:SetScript("OnClick", nil)
    else
        tiles.scheme:SetScript("OnClick", function() PD.ShowSchemeMenu(tiles.scheme) end)
    end
    tiles.scheme.val:SetTextColor(Unpack(C_WHITE))
    local schemeDesc = {
        cheapest = L["比较采购、自制与图纸支出"],
        matcost = L["只按材料价选配方"],
        crafts = L["升点率高优先，同分取便宜"],
        optim = L["不查拍卖行，按商人价粗算"],
    }
    local schemeLines = {}
    local sorder = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    for _, sk in ipairs(sorder) do
        local curK = (sk == sch)
        local nm = (RA and RA.SchemeLabel) and RA.SchemeLabel(sk) or sk
        local head = curK and "|cffffd100" or "|cffffffff"
        schemeLines[#schemeLines + 1] = {
            head .. nm .. "|r|cff8f8f8f：|r|cffb3b3b3" .. (schemeDesc[sk] or "") .. "|r",
            1, 1, 1,
        }
    end
    if fishRoute then
        schemeLines = {
            {L["1–225 参考烹饪指南；之后优先容易钓取的鱼。"], 1, 0.82, 0},
            {L["鱼类自行钓取；其他材料只使用不限量商人货物。"], 0.7, 0.7, 0.7},
            {L["鱼类不计金币成本；图纸仍按实际采购来源计费。"], 0.7, 0.7, 0.7},
            {L["点击可切换到其他路线方案"], 0.7, 0.7, 0.7},
        }
    else
        schemeLines[#schemeLines + 1] = { L["点击选择路线方案"], 0.7, 0.7, 0.7 }
    end
    TipOn(tiles.scheme, schemeLines)
    if tiles.solver.__use then
        local SR = ns.ProfSolverRun
        local running = SR and SR.Running and SR.Running()
        local son = PD.Setting("solverRoute")
        local sv = L["关"]
        if running then
            local frac = PD.solverFrac or 0
            sv = format(L["计算中 %d%%"], math.floor(frac * 100 + 0.5))
        elseif son then
            sv = L["开"]
        end
        tiles.solver.val:SetText(sv)
        tiles.solver.val:SetTextColor(Unpack((son or running) and C_WHITE or C_GREY))
        PD.PaintTileBorder(tiles.solver, { 1, 1, 1, 0.10 })
        local hint
        if running then
            hint = L["正在计算，点击可关闭"]
        elseif son then
            hint = L["已开启，点击可关闭"]
        else
            hint = L["已关闭，点击可开启"]
        end
        TipOn(tiles.solver, {
            { L["精确方案：逐档比较配方组合，较慢但更省"], 1, 0.82, 0 },
            { hint, 0.7, 0.7, 0.7 },
            { L["开启后会自动切到自动计算模式"], 0.7, 0.7, 0.7 },
        })
    end
    do
        local banR, banM = PD.CountBans()
        local nBan = banR + banM
        tiles.excl.val:SetText(nBan > 0 and format(L["%d 项"], nBan) or L["无"])
        tiles.excl.val:SetTextColor(Unpack(nBan > 0 and C_WHITE or C_GREY))
        PD.PaintTileBorder(tiles.excl, { 1, 1, 1, 0.10 })
        local lines = { { L["图样 / 材料使用管理"], 1, 0.82, 0 } }
        if banR > 0 then lines[#lines + 1] = { format(L["已禁用图样：%d"], banR), 0.88, 0.42, 0.38 } end
        if banM > 0 then lines[#lines + 1] = { format(L["已禁用材料：%d"], banM), 0.88, 0.42, 0.38 } end
        if nBan == 0 then lines[#lines + 1] = { L["点击管理不使用的图样与材料"], 0.7, 0.7, 0.7 } end
        TipOn(tiles.excl, lines)
    end
    tiles.cost.label:SetText(s.partial and L["已计算支出"] or L["预计总花费"])
    local costLines
    if s.status == "selection_required" or s.status == "recalculate_required" then
        tiles.cost.val:SetText(L["—"])
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = {{PD.PlanStatusText(s), 0.95, 0.75, 0.4}}
    elseif s.scheme == "optim" then
        tiles.cost.val:SetText(RA.MoneyStr(s.total or 0, "copper"))
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { L["乐观计数：花费按商人购买价或卖店价值粗算，不是拍卖行行情"], 0.7, 0.7, 0.7 } }
    elseif s.priced and s.total then
        tiles.cost.val:SetText(PD.PlanCostText(s))
        tiles.cost.val:SetTextColor(Unpack(C_GOLD))
        costLines = {}
        if s.recipes then
            costLines[#costLines + 1] = { format(L["配方 %d 种 · %d 次制作"], s.recipes, s.crafts or 0) }
            costLines[#costLines + 1] = { format(L["商人直售 %s"], RA.MoneyStr(s.vendorTotal or 0)), 0.7, 0.7, 0.7 }
        else
            costLines[#costLines + 1] = { format(L["材料 %d 种"], s.matsN or 0) }
        end
    else
        tiles.cost.val:SetText(L["—"])
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { PD.AuctionatorStatusText(), 0.7, 0.7, 0.7 } }
    end
    if (s.np or 0) > 0 then
        costLines[#costLines + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], s.np),
                                      0.95, 0.75, 0.4 }
    end
    if type(s.recoveryTotal) == "number" and s.recoveryTotal > 0 then
        local net = s.netTotal or ((s.total or 0) - s.recoveryTotal)
        costLines[#costLines + 1] = { format(L["预计回血 %s · 净成本 %s"],
            PD.RecoveryMoney(s.recoveryTotal), PD.RecoveryMoney(net)), 0.55, 0.85, 0.6 }
        if s.recoveryFeePercent then
            costLines[#costLines + 1] = { format(L["按 %d%% 手续费折算，剩余产物假设全部成交"], s.recoveryFeePercent),
                                          0.7, 0.7, 0.7 }
        end
        if (s.recoveryMissing or 0) > 0 then
            costLines[#costLines + 1] = { format(L["其中 %d 种产物售价未知，未计回血"], s.recoveryMissing),
                                          0.95, 0.75, 0.4 }
        end
    end
    if s.planVersion == 2 then
        if s.completeCost == false then costLines[#costLines + 1] = { L["采购价格或图纸现货尚未全部核实，当前金额是已知支出。"], 0.95, 0.75, 0.4 } end
    end
    tiles.target.label:SetText(L["目标等级"])
    tiles.target.val:SetText(v >= 300 and L["全程"] or tostring(v))
    tiles.target.val:SetTextColor(Unpack(C_WHITE))
    TipOn(tiles.target, { { L["每专业独立记忆；300 = 全程。点击修改"], 0.7, 0.7, 0.7 } })
    local snapBadge, br, bg, bb
    if s.planVersion == 2 then
        if s.completeCost == false then snapBadge, br, bg, bb = L["资料不全"], 0.95, 0.75, 0.4
        elseif (s.np or 0) > 0 then snapBadge, br, bg, bb = L["含无价材料"], 0.95, 0.75, 0.4
        else snapBadge, br, bg, bb = L["已核实"], 0.55, 0.85, 0.6 end
    elseif s.scheme == "optim" then
        snapBadge, br, bg, bb = L["乐观计数"], 0.85, 0.82, 0.72
    elseif s.priced then
        snapBadge, br, bg, bb = L["价格快照"], 0.55, 0.85, 0.6
    else
        snapBadge, br, bg, bb = L["无价格"], 0.95, 0.75, 0.4
    end
    PD.SetBadge(snapBadge, br, bg, bb)
    local atxt
    if s.planVersion == 2 then
        atxt = PD.PlanStatusText(s)
    elseif s.scheme == "optim" then
        atxt = L["乐观计数 · 不依赖价格插件"]
    elseif s.priced and snapDays then
        atxt = (snapDays <= 0) and L["今天Auctionator"]
               or format(L["%d 天前Auctionator"], snapDays)
    elseif s.priced and snapSec then
        atxt = PD.SnapshotSecText(snapSec)
    elseif s.priced then
        atxt = L["快照年龄未知Auctionator"]
    end
    local details = { { atxt or PD.AuctionatorStatusText(), 0.7, 0.7, 0.7 } }
    if snapSec and snapDays then
        details[#details + 1] = { format(L["上次扫描： %s"], PD.SnapshotSecText(snapSec)), 0.7, 0.7, 0.7 }
    end
    local progress = PD.PlanProgressText(s)
    if progress then details[#details + 1] = { progress, 0.7, 0.7, 0.7 } end
    local cached = PD.PlanCacheText(s)
    if cached then details[#details + 1] = { cached, 0.95, 0.75, 0.4 } end
    if s.budgetLimited then details[#details + 1] = { L["已完成本轮计算，当前结果尚未证明最优。"], 0.95, 0.75, 0.4 } end
    if s.quotesRefreshed then details[#details + 1] = { L["数量或费率已更新，本轮数字已按最新价格重算。"], 0.7, 0.7, 0.7 } end
    for _, ln in ipairs(details) do costLines[#costLines + 1] = ln end
    TipOn(tiles.cost, costLines)
    if fixedOnly then tiles.scheme.__use = false end
    local n = 0
    for _, k in ipairs(PD.chipOrder) do
        if tiles[k].__use then n = n + 1 end
    end
    PD.PlaceCards(n > 0 and n or 1)
    if type(s.recoveryTotal) == "number" and s.recoveryTotal > 0 then
        local recNet = s.netTotal or ((s.total or 0) - s.recoveryTotal)
        PD.SetSub(format(L["回血 %s · 净 %s"], PD.MoneyBrief(s.recoveryTotal), PD.MoneyBrief(recNet)))
    else
        PD.SetSub(nil)
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

function PD.VendorName(v)
    if not v then return "?" end
    local id = v.id or v.npcID
    local cn = id and ns.ProfVendorNames and ns.ProfVendorNames[id] or nil
    if cn and cn ~= "" then return cn end
    local rec = v.name and ns.ProfDropNpcs and ns.ProfDropNpcs[v.name] or nil
    if rec and rec[1] and rec[1] ~= "" then return rec[1] end
    return tostring(v.name or "?")
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

function PD.MapName(uiMap, fallback)
    if uiMap and C_Map and C_Map.GetMapInfo then
        local ok, mi = pcall(C_Map.GetMapInfo, uiMap)
        if ok and type(mi) == "table" and mi.name and mi.name ~= "" then return mi.name end
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
    z:RegisterForClicks("LeftButtonUp", "RightButtonUp")
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
                PD.UnifyTipFont(14)
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

function PD.PaintTag(r, tag)
    local chip, fs = r.tagChip, r.tagFs
    fs:SetTextColor(Unpack(tag.color or { 0.42, 0.94, 0.62 }))
    fs:SetText(tag.text or "")
    chip:SetSize(fs:GetStringWidth() + 10, 15)
    chip:ClearAllPoints()
    chip:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 8, 0)
    chip:Show()
    fs:Show()
end

function PD.SkillChip(r)
    if r.__skchip then return r.__skchip end
    local f = CreateFrame("Frame", nil, r)
    f:SetFrameLevel((r:GetFrameLevel() or 0) + 2)
    ns.hui.BuildRoundedBG(f, 4, ns.hui.layer.L2, "both", true, 1)
    local fs = MakeFS(f, 10, C_TEXT, "CENTER")
    fs:SetPoint("LEFT", f, "LEFT", 4, 0)
    fs:SetPoint("RIGHT", f, "RIGHT", -4, 0)
    fs:SetPoint("TOP", f, "TOP", 0, -2)
    fs:SetPoint("BOTTOM", f, "BOTTOM", 0, 2)
    f.fs = fs
    f:Hide()
    r.__skchip = f
    return f
end

function PD.SubChip(z)
    if z.__chip then return z.__chip end
    local f = CreateFrame("Frame", nil, z)
    ns.hui.BuildRoundedBG(f, 4, ns.hui.layer.L2, "both", true, 1)
    local fs = MakeFS(f, 10, C_TEXT, "CENTER")
    fs:SetPoint("LEFT", f, "LEFT", 4, 0)
    fs:SetPoint("RIGHT", f, "RIGHT", -4, 0)
    fs:SetPoint("TOP", f, "TOP", 0, -2)
    fs:SetPoint("BOTTOM", f, "BOTTOM", 0, 2)
    f.fs = fs
    f:Hide()
    z.__chip = f
    return f
end

function PD.SubLinkAt(r, k)
    r.__subLinks = r.__subLinks or {}
    local z = r.__subLinks[k]
    if z then return z end
    z = CreateFrame("Button", nil, r)
    z:SetFrameLevel((r:GetFrameLevel() or 0) + 2)
    z:SetHeight(16)
    PD.WireTipZone(z, r)
    local fs = MakeFS(z, 11, C_GOLD, "LEFT")
    fs:SetWordWrap(false)
    fs:SetPoint("LEFT", z, "LEFT", 0, 0)
    fs:SetPoint("RIGHT", z, "RIGHT", 0, 0)
    z.fs = fs
    z:Hide()
    r.__subLinks[k] = z
    return z
end

function PD.SubLink(r)
    return PD.SubLinkAt(r, 1)
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
    if z.RegisterForClicks and not z.__clicksWired then
        z.__clicksWired = true
        z:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    end
    z:SetScript("OnEnter", function(self)
        if not self.__noHover then PD.SetRowHover(r, true) end
        if self.__it then PD.hoverRow = self end
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
            PD.UnifyTipFont(14)
        elseif self.__it and DG.ShowItemTip then
            local extra = self.__tipExtra
            if type(extra) == "function" then extra = extra() end
            DG.ShowItemTip(self, self.__it, extra)
        end
    end)
    z:SetScript("OnLeave", function(self)
        if not self.__noHover then PD.SetRowHover(r, false) end
        if PD.hoverRow == self then PD.hoverRow = nil end
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

function PD.ExCard(r, k)
    r.__ex = r.__ex or {}
    local c = r.__ex[k]
    if c then return c end
    local base = tonumber(r.GetFrameLevel and r:GetFrameLevel()) or 0
    c = CreateFrame("Frame", nil, r)
    c:SetFrameLevel(base + 2)
    ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
    local ic = c:CreateTexture(nil, "ARTWORK", nil, 2)
    ic:SetSize(24, 24)
    ic:SetPoint("LEFT", c, "LEFT", 8, 0)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
    local nm = MakeFS(c, 14, C_TEXT, "LEFT")
    nm:SetWordWrap(false)
    nm:SetPoint("TOPLEFT", c, "TOPLEFT", 38, -4)
    nm:SetPoint("RIGHT", c, "RIGHT", -76, 0)
    local st = MakeFS(c, 14, C_GREY, "RIGHT")
    st:SetPoint("TOPRIGHT", c, "TOPRIGHT", -7, -4)
    local src = MakeFS(c, 14, C_GREY, "LEFT")
    src:SetWordWrap(false)
    src:SetPoint("BOTTOMLEFT", c, "BOTTOMLEFT", 38, 4)
    src:SetPoint("RIGHT", c, "RIGHT", -8, 0)
    local z = CreateFrame("Button", nil, c)
    z:SetFrameLevel(base + 3)
    z:SetPoint("TOPLEFT", c, "TOPLEFT", 0, 0)
    z:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", 0, 0)
    PD.WireTipZone(z, r)
    z.__noHover = true
    c.ic, c.nm, c.st, c.src, c.z = ic, nm, st, src, z
    r.__ex[k] = c
    return c
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
    both    = { 0.13, 0.44, 0.42 },
}
PD.CARD_INK = {
    trainer = { 0.81, 0.85, 0.89 },
    drop    = { 0.91, 0.86, 1.00 },
    vendor  = { 1.00, 0.91, 0.66 },
    both    = { 0.72, 0.97, 0.92 },
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
    local x, w = PD.LV_RNG_X or 6, PD.LV_CARD_FIXW
    tx:ClearAllPoints()
    tx:SetPoint("CENTER", r, "LEFT", x + w / 2, PD.SB_DY)
    local col = PD.CARD_COL[card.kind] or PD.CARD_COL.trainer
    tx:SetTextColor(Unpack(PD.CARD_INK[card.kind] or PD.CARD_INK.trainer))
    tx:SetText(card.text or "")
    tx:Show()
    local th = tx:GetStringHeight()
    if (th or 0) <= 0 then th = 12 end
    local half = math.floor(th / 2) + 1
    bg:ClearAllPoints()
    bg:SetPoint("TOPLEFT", r, "LEFT", x, PD.SB_DY + half)
    bg:SetPoint("BOTTOMRIGHT", r, "LEFT", x + w, PD.SB_DY - half)
    for _, tex in ipairs(bg.__pieces or {}) do
        tex:SetVertexColor(col[1], col[2], col[3])
        tex:SetAlpha(1)
    end
    bg:Show()
    z.__tipLines = card.lines
    z.__act = card.act
    z.__it = card.fid and { card.fid } or nil
    z:ClearAllPoints()
    z:SetPoint("TOPLEFT", r, "LEFT", x, PD.SB_DY + half + 1)
    z:SetPoint("BOTTOMRIGHT", r, "LEFT", x + w, PD.SB_DY - half - 1)
    z:Show()
end

local TRAINER_CARD = {
    kind = "trainer", text = L["训练师"],
    lines = { { L["向训练师学习"], 0.81, 0.85, 0.89 } },
}

PD.CARD_FIXW = nil
function PD.CardFixW()
    if not PD.CARD_FIXW then
        PD.CARD_FIXW = math.ceil(math.max(
            PD.TextW(L["训练师"], 10),
            PD.TextW(L["世界掉落图纸"], 10),
            PD.TextW(L["商人出售图纸"], 10),
            PD.TextW(L["掉落&商人图纸"], 10))) + 2 * PD.CARD_PAD
    end
    return PD.CARD_FIXW
end

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
    local vl = PD.VendorLines(src, fid)
    for i = 1, #vl do lines[#lines + 1] = vl[i] end
    local ahLine = PD.FormulaAuctionLine(fid)
    if ahLine then lines[#lines + 1] = ahLine end
    local kind = (hasDrop and hasVendor and "both") or (hasVendor and "vendor") or "drop"
    local text = (kind == "both" and L["掉落&商人图纸"])
        or (kind == "vendor" and L["商人出售图纸"])
        or L["世界掉落图纸"]
    return {
        kind = kind,
        text = text, fid = fid, lines = lines,
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
    if r.__ex then
        for _, c in pairs(r.__ex) do c:Hide() end
    end
    if r.__pct then r.__pct:Hide() end
    if r.__warn then r.__warn:Hide(); r.__warn.__tipLines = nil end
    if r.sep then r.sep:Hide() end
    if r.tagFs then r.tagFs:Hide() end
    if r.tagBg then r.tagBg:Hide() end
    if r.dv then r.dv:SetText(""); r.dv:Hide() end
    if r.__sbBg then PD.HideSkillBar(r) end
    if r.__cardZone then PD.PaintCard(r, nil) end
    if r.__costZone then r.__costZone:Hide() end
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

function PD.PaintMats(r, blocks, cut, grey, rightX)
    local n = blocks and #blocks or 0
    local W = PD.LV_ROW_W or PD.COL_LW
    local right = (rightX and rightX > 0) and rightX or (W - PD.TBL_MAT_RPAD)
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
    if s.skill then
        out[#out + 1] = { text = format(L["技能 %s"], tostring(s.skill)), kind = "skill" }
    end
    if s.drops and #s.drops > 0 then
        out[#out + 1] = { text = format(L["掉落 %d 处"], #s.drops), kind = "drop" }
    end
    if s.vendors and #s.vendors > 0 then
        local vs = PD.VendorListOf(s)
        if #vs > 1 then
            out[#out + 1] = { text = format(L["商人：%s 等 %d 人"], PD.VendorName(vs[1]), #vs), vendor = true }
        elseif #vs == 1 then
            local v = vs[1]
            out[#out + 1] = { text = format(L["商人：%s"], PD.VendorName(v)), vendor = true }
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

function PD.FormulaOffersByNpc(fid)
    if not fid then return nil end
    local S = ns.ProfSupply
    local list = S and S.DisplayList and S.DisplayList(fid) or nil
    if type(list) ~= "table" then return nil end
    local map = {}
    for _, o in ipairs(list) do
        if o.npcID then
            local cur = map[o.npcID]
            if not cur then
                map[o.npcID] = o
            elseif (cur.currencyID or 0) > 0 and (o.currencyID or 0) == 0 then
                map[o.npcID] = o
            end
        end
    end
    return map
end

function PD.VendorLines(s, fid)
    local out = {}
    if not (s and s.vendors and #s.vendors > 0) then return out end
    local vs = PD.VendorListOf(s)
    if #vs == 0 then return out end
    local offers = PD.FormulaOffersByNpc(fid)
    for i = 1, #vs do
        local v = vs[i]
        if v and (v.name or v.zone) then
            local nm = format(L["商人：%s"], PD.VendorName(v))
            if v.zone and v.zone ~= "" then nm = nm .. " · " .. tostring(v.zone) end
            local o = offers and offers[v.id or v.npcID]
            if not o and ((v.price or 0) > 0 or (v.cur or 0) > 0) then
                o = { price = v.price or 0, currencyID = v.cur or 0,
                      currencyAmount = v.amt or 0, quantity = 1 }
            end
            if o then nm = nm .. " · " .. PD.FormulaCostText(o) end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    local ents = PD.VendorEntries(s)
    if #ents == 1 then
        out[#out + 1] = { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 }
    elseif #ents > 1 then
        out[#out + 1] = { L["点击：选择要标记的 NPC"], 1, 0.82, 0 }
    end
    return out
end

function PD.FormulaCostText(offer)
    if type(offer) ~= "table" then return L["价格未知"] end
    local parts = {}
    local curID = tonumber(offer.currencyID) or 0
    if curID > 0 then
        local name, icon
        if C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo then
            local ok, info = pcall(C_CurrencyInfo.GetCurrencyInfo, curID)
            if ok and type(info) == "table" then name, icon = info.name, info.iconFileID end
        end
        if not name then
            local inm = DG.ItemName(curID)
            if inm then name, icon = inm, DG.ItemIcon and DG.ItemIcon(curID) end
        end
        if not name then name = format(L["通货 #%d"], curID) end
        local amt = tonumber(offer.currencyAmount) or 0
        parts[#parts + 1] = (icon and format("|T%s:14:14|t", icon) or "") .. name .. " ×" .. tostring(amt)
    elseif (tonumber(offer.price) or 0) > 0 then
        parts[#parts + 1] = RA.MoneyStr(offer.price, "copper")
    end
    local qty = tonumber(offer.quantity) or 0
    if qty > 1 then parts[#parts + 1] = format(L["每组 %d 件"], qty) end
    if #parts == 0 then return L["价格未知"] end
    return table.concat(parts, " · ")
end

function PD.FormulaAuctionLine(fid)
    if not fid then return nil end
    local RAmod = ns.ProfRouteAuto
    local p = RAmod and RAmod.AHPriceOf and RAmod.AHPriceOf(fid)
    if type(p) ~= "number" or p <= 0 then return nil end
    return { format(L["拍卖行：%s"], RAmod.MoneyStr(p, "copper")), 0.72, 0.72, 0.88 }
end

function PD.VendorEntries(s)
    local out = {}
    local vs = PD.VendorListOf(s)
    for i = 1, #vs do
        local v = vs[i]
        local loc = v.id and ns.ProfVendors and ns.ProfVendors[v.id] or nil
        if not loc and v.id then
            local ls = ns.EnsureProfNPCLocs()[v.id]
            if type(ls) == "table" then loc = ls[1] end
        end
        if not loc and v.name then
            local rec = ns.ProfDropNpcs and ns.ProfDropNpcs[v.name] or nil
            if rec and rec[2] and type(rec[3]) == "number" and type(rec[4]) == "number" then
                loc = { nil, rec[2], rec[3], rec[4] }
            end
        end
        if loc then
            local zone = v.zone
            if not zone or zone == "" then zone = PD.MapName(loc[2], PD.CampZoneName(loc[1], "")) end
            out[#out + 1] = { loc = loc, name = PD.VendorName(v), zone = zone }
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

function PD.DropName(dd)
    if not dd then return "?" end
    local rec = dd.npc and ns.ProfDropNpcs and ns.ProfDropNpcs[dd.npc] or nil
    if rec and rec[1] and rec[1] ~= "" then return rec[1] end
    return tostring(dd.npc or "?")
end

function PD.DropZone(dd, uiMap)
    if dd and dd.zone and dd.zone ~= "" then return dd.zone end
    local z = uiMap and PD.MapName(uiMap, nil) or nil
    return z or ""
end

function PD.DropEntries(s)
    local out, seen = {}, {}
    if not (s and s.drops) then return out end
    for _, dd in ipairs(s.drops) do
        local rec = dd.npc and ns.ProfDropNpcs and ns.ProfDropNpcs[dd.npc] or nil
        local ui, x, y = rec and rec[2], rec and rec[3], rec and rec[4]
        if not ui then
            local locs = dd.id and ns.EnsureProfNPCLocs()[dd.id] or nil
            local l0 = locs and locs[1]
            if l0 then ui, x, y = l0[2] or l0[1], l0[3], l0[4] end
        end
        if ui and type(x) == "number" and type(y) == "number" and x > 0 and y > 0 then
            local key = tostring(dd.npc or "?") .. "|" .. tostring(ui)
            if not seen[key] then
                seen[key] = true
                out[#out + 1] = {
                    loc = { nil, ui, x, y },
                    name = PD.DropName(dd),
                    zone = PD.DropZone(dd, ui),
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
    local out, seen = {}, {}
    if not (s and s.drops and #s.drops > 0) then return out end
    local ents = PD.DropEntries(s)
    local located = {}
    for i = 1, #ents do located[ents[i].name] = true end
    for i = 1, math.min(#s.drops, 8) do
        local dd = s.drops[i]
        if dd and (dd.npc or dd.zone) then
            local nm = PD.DropName(dd)
            local key = nm .. "|" .. tostring(dd.zone or "")
            if not seen[key] then
                seen[key] = true
                local line = format(L["掉落：%s"], nm)
                local zn = PD.DropZone(dd, nil)
                if zn ~= "" then line = line .. " · " .. zn end
                if dd.chance then
                    local pct = dd.chance
                    if pct > 0 and pct <= 1 then pct = pct * 100 end
                    pct = math.floor(pct + 0.5)
                    if pct > 100 then pct = 100 end
                    line = line .. format(L[" · %d%%"], pct)
                end
                if not located[nm] then line = line .. " · " .. L["暂无坐标"] end
                out[#out + 1] = { line, 0.75, 0.75, 0.75 }
            end
        end
    end
    if #s.drops > 8 then
        out[#out + 1] = { format(L["…等 %d 处"], #s.drops), 0.6, 0.6, 0.6 }
    end
    if #ents == 1 then
        out[#out + 1] = { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 }
    elseif #ents > 1 then
        out[#out + 1] = { L["点击：选择要标记的 NPC"], 1, 0.82, 0 }
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

function PD.RecipeData(row, kind, slug)
    local E = ns.ProfEconomy
    if E and E.Normalize then
        local resolved = E.Normalize(row, slug or PD.cur, kind or "rows")
        if resolved then return resolved end
    end
    local r
    if kind == "enchants" then
        r = {spell=row[14], item=row[15], count=1, mats=row[9], learn=row[5], yellow=row[6], green=row[7], grey=row[8]}
    elseif kind == "crafted" then
        r = {spell=row[1], item=row[2], count=row[3], mats=row[8], learn=row[4], yellow=row[5], green=row[6], grey=row[7]}
    else
        r = {spell=row[1], item=row[2], count=row[3], mats=row[12], learn=row[7], yellow=row[8], green=row[9], grey=row[10]}
    end
    if E and E.ResolveRecipe then return E.ResolveRecipe(r, slug or PD.cur) end
    r.dataSource = "catalogue"
    r.clientPending = type(r.mats) ~= "table" or (r.item and not r.count)
    return r
end

function PD.RecipeOutputText(r)
    local lo, hi = r and tonumber(r.outputMin), r and tonumber(r.outputMax)
    if r and r.variableOutput and lo and hi and lo > 0 and hi > lo then
        return format(L["每次产量：%d–%d；按最低产量计算，实际多产可减少后续材料需求。"], lo, hi)
    end
    if r and r.variableOutput and r.outputBasis=="reference" then
        return format(L["随机产量范围暂未读取；按已有资料每次 %d 件估算。"], r.count or r[3] or 1)
    end
end

function PD.RecipeSourceLines(lines, r)
    lines = lines or {}
    if r and r.clientUnavailable then
        lines[#lines + 1] = {L["客户端已确认不可用"], 0.95, 0.75, 0.4}
        lines[#lines + 1] = {L["此记录仅供查阅，不参与自动路线。"], 0.95, 0.75, 0.4}
    end
    local output = PD.RecipeOutputText(r)
    if output then lines[#lines + 1] = {output, 0.65, 0.75, 0.85} end
    return lines
end

function PD.RecipeVisible(spell, slug)
    local E = ns.ProfEconomy
    if E and E.ResolveRecipe then
        local resolved = E.ResolveRecipe({spell=spell}, slug or PD.cur)
        return not resolved.clientUnavailable
    end
    return true
end

function PD.EnchantSpec(en)
    local resolved = PD.RecipeData(en, "enchants")
    local original = en
    en = {}; for key, value in pairs(original) do en[key] = value end
    en[9] = resolved.mats
    if resolved.item then en[15] = resolved.item end
    en[5], en[6], en[7], en[8] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
    local clientPending = resolved.clientPending
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
    local acqEn = (hasVendor and #drEn == 0) and L["商人售卖"] or L["世界掉落"]
    local base = en[10] and (L["图纸"] .. " · " .. acqEn) or L["训练师"]
    local dpre, dval, dact, vlines
    if hasVendor then
        dpre = base
        if #vsEn > 1 then
            dval = format(L["商人：%s 等 %d 人"], tostring(vsEn[1] and vsEn[1].name or "?"), #vsEn)
        else
            dval = format(L["商人：%s"], tostring(vsEn[1] and vsEn[1].name or "?"))
        end
        dact = PD.VendorAct(en[10])
        vlines = PD.VendorLines(en[10], (type(en[15]) == "number") and en[15] or nil)
    elseif #drEn > 0 then
        dpre = base
        dval = format(L["掉落 %d 处"], #drEn)
        dact = PD.DropAct(en[10])
        vlines = PD.DropLines(en[10])
    end
    local lines = PD.RecipeSourceLines({ { en[1] or "" } }, resolved)
    if en[4] and en[4] ~= "" then lines[#lines + 1] = { en[4] } end
    if en[10] then lines[#lines + 1] = { PD.SourceText(en[10]) or "", 0.7, 0.7, 0.7 } end
    if vlines then
        for _, ln in ipairs(vlines) do lines[#lines + 1] = ln end
    end
    local ahLine = (type(en[15]) == "number") and PD.FormulaAuctionLine(en[15]) or nil
    if ahLine then lines[#lines + 1] = ahLine end
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
        mats = clientPending and L["客户端数据待读取"] or matCol,
        matSegs = matSg,
        right = not (en[5] or en[6] or en[7] or en[8])
                and format("%s · %s", format(L["学 %s"], tostring(en[5])),
                           PD.TierText(en[6], en[7], en[8])) or nil,
        right2 = clientPending and L["客户端数据待读取"] or (resolved.clientUnavailable and L["客户端已确认不可用"]) or ((not dval) and base or nil),
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
                   and function() return PD.RecipeSourceLines(PD.PriceTipLines(en[15], en[9]), resolved) end or nil,
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
PD.VENDOR_SHOW_MAX = 2

function PD.VendorSideText(side)
    if side == "A" or side == "a" then return L["联盟"] end
    if side == "H" or side == "h" then return L["部落"] end
    return L["中立"]
end

function PD.MyVendorSide()
    local f = UnitFactionGroup and UnitFactionGroup("player")
    if f == "Alliance" then return "a" end
    if f == "Horde" then return "h" end
    return nil
end

function PD.VendorSideOf(o)
    if type(o) ~= "table" then return "n" end
    local t = ns.ProfVendorSide
    local s = type(t) == "table" and t[o.npcID] or nil
    if type(s) ~= "string" or s == "" then s = o.side end
    if type(s) ~= "string" then return "n" end
    s = string.lower(s)
    if s == "a" or s == "h" then return s end
    return "n"
end

function PD.CurrencyOf(curID)
    if type(curID) ~= "number" or curID <= 0 then return nil end
    local cache = PD.__curCache
    if not cache then cache = {} PD.__curCache = cache end
    local hit = cache[curID]
    if hit then
        if hit == false then return nil end
        return hit[1], hit[2]
    end
    local r = C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo and C_CurrencyInfo.GetCurrencyInfo(curID)
    local nm = type(r) == "table" and r.name or nil
    if type(nm) ~= "string" or nm == "" then
        cache[curID] = false
        return nil
    end
    local icon = type(r.iconFileID) == "number" and r.iconFileID > 0 and r.iconFileID or nil
    cache[curID] = { nm, icon }
    return nm, icon
end

function PD.VendorItemName(itemID)
    if type(itemID) ~= "number" or itemID <= 0 then return nil end
    if C_Item and C_Item.GetItemNameByID then
        local ok, v = pcall(C_Item.GetItemNameByID, itemID)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    if C_Item and C_Item.GetItemInfo then
        local ok, v = pcall(C_Item.GetItemInfo, itemID)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    local tbl = ns.ProfItemNames
    local nm = type(tbl) == "table" and tbl[itemID] or nil
    if type(nm) == "string" and nm ~= "" then return nm end
    return nil
end

local VENDOR_SIDES = { "A", "H", "N" }

function PD.VendorOffersOf(itemID)
    if type(itemID) ~= "number" then return nil end
    local out, seen = {}, {}
    local function add(npcID, name, area, side, price, cur, amt, pack, stock)
        if type(npcID) ~= "number" or seen[npcID] then return end
        seen[npcID] = true
        out[#out + 1] = { npcID = npcID, name = name, area = area, side = side,
                          price = price, cur = cur, amt = amt, pack = pack, stock = stock }
    end
    local src = ns.EnsureProfSources()[itemID]
    local vs = type(src) == "table" and src.v or nil
    if type(vs) ~= "table" or #vs == 0 then
        local fid = ns.ProfMakeSrc and ns.ProfMakeSrc[itemID]
        local psrc = fid and ns.EnsureProfSources()[fid] or nil
        vs = type(psrc) == "table" and psrc.v or nil
    end
    if type(vs) == "table" then
        for i = 1, #vs do
            local v = vs[i]
            if type(v) == "table" and type(v.id) == "number" then
                add(v.id, v.name, v.area, v.side, v.price, v.cur, v.amt, v.pack, v.stock)
            end
        end
    end
    local sup = ns.EnsureProfMaterialSupply()[itemID]
    if type(sup) == "table" and #sup >= 8 then
        for i = 1, #sup - 7, 8 do
            local cost = sup[i + 1]
            add(sup[i], nil, sup[i + 4], VENDOR_SIDES[sup[i + 3]] or "N",
                type(cost) == "number" and cost or nil, sup[i + 6], sup[i + 7],
                sup[i + 5], sup[i + 2])
        end
    end
    if #out == 0 then return nil end
    return out
end

function PD.VendorBlockLines(lines, itemID)
    local C_NM, C_MT, C_PR = { 0.92, 0.94, 0.98 }, { 0.63, 0.65, 0.70 }, { 0.55, 0.85, 0.60 }
    local list = PD.VendorOffersOf(itemID)
    if not list then
        lines[#lines + 1] = { format(L["商人：%s"], "—"), Unpack(C_MT) }
        return
    end
    local mine = PD.MyVendorSide()
    if mine then
        local keep, other = {}, 0
        for i = 1, #list do
            local s = PD.VendorSideOf(list[i])
            if s == "n" or s == mine then
                keep[#keep + 1] = list[i]
            else
                other = other + 1
            end
        end
        list = keep
        if #list == 0 then
            lines[#lines + 1] = { format(L["商人：%s"], other > 0 and L["对方阵营专属"] or "—"), Unpack(C_MT) }
            return
        end
    end
    local shown = math.min(#list, PD.VENDOR_SHOW_MAX or 2)
    for i = 1, shown do
        local o = list[i]
        local nm = PD.VendorName(o)
        if type(nm) ~= "string" or nm == "" or nm == "?" then nm = L["位置未收录的商人"] end
        lines[#lines + 1] = { format(L["商人：%s"], nm), Unpack(C_NM) }
        local zone = o.area and PD.CampZoneName(o.area) or nil
        local stbl = ns.ProfVendorSide
        local side = (type(stbl) == "table" and stbl[o.npcID]) or o.side
        local head = PD.VendorSideText(side)
        if type(zone) == "string" and zone ~= "" then head = head .. " · " .. zone end
        lines[#lines + 1] = { head, Unpack(C_MT) }
        local ptxt, isCur
        if o.cur and o.amt then
            local cnm, cicon = PD.CurrencyOf(o.cur)
            if cnm then
                isCur = true
                ptxt = tostring(o.amt)
                if cicon then
                    ptxt = ptxt .. " |T" .. cicon .. ":12:12:0:0:64:64:4:60:4:60|t"
                end
                ptxt = ptxt .. " " .. cnm
            else
                local iname = PD.VendorItemName(o.cur)
                if iname then ptxt = iname .. " ×" .. tostring(o.amt) end
            end
        end
        if not ptxt and type(o.price) == "number" and o.price > 0 then
            ptxt = RA.MoneyStr(o.price, "copper")
        end
        if ptxt then
            if not isCur and type(o.pack) == "number" and o.pack > 1 then
                ptxt = ptxt .. " · " .. format(L["每组 %d 件"], o.pack)
            end
            lines[#lines + 1] = { format(L["价格：%s"], ptxt), Unpack(C_PR) }
        end
    end
    if #list > shown then
        local names = {}
        for i = shown + 1, math.min(#list, shown + 3) do
            local nm = PD.VendorName(list[i])
            if type(nm) == "string" and nm ~= "" and nm ~= "?" then names[#names + 1] = nm end
        end
        local txt = format(L["另有 %d 处"], #list - shown)
        if #names > 0 then txt = txt .. " · " .. table.concat(names, "、") end
        lines[#lines + 1] = { txt, Unpack(C_MT) }
    end
end

function PD.DropPctText(pct)
    if type(pct) ~= "number" or pct <= 0 then return nil end
    local q = pct <= 1 and pct * 100 or pct
    local ip = math.floor(q + 0.5)
    if ip >= 1 then return format(L["%d%%"], ip) end
    return L["<1%"]
end

function PD.DropNPCText(e)
    local t = ns.ProfDropNames
    local nm = type(t) == "table" and type(e.id) == "number" and t[e.id] or nil
    if type(nm) ~= "string" or nm == "" then nm = e.npc end
    if type(nm) ~= "string" or nm == "" then nm = L["未知怪物"] end
    return nm
end

function PD.DropRowsOf(itemID)
    local srcs = ns.EnsureProfSources()
    local e = srcs[itemID]
    local d = type(e) == "table" and e.d or nil
    if type(d) ~= "table" or #d == 0 then
        local fid = ns.ProfMakeSrc and ns.ProfMakeSrc[itemID]
        local fe = fid and srcs[fid]
        d = type(fe) == "table" and fe.d or nil
    end
    if type(d) ~= "table" or #d == 0 then return nil end
    local out, seen = {}, {}
    for i = 1, #d do
        local dd = d[i]
        if type(dd) == "table" and (dd.npc or dd.area) then
            local nm = PD.DropNPCText(dd)
            local key = nm .. "|" .. tostring(dd.area or "")
            if not seen[key] then
                seen[key] = true
                out[#out + 1] = { name = nm, area = dd.area, pct = dd.pct }
            end
        end
    end
    if #out == 0 then return nil end
    table.sort(out, function(a, b) return (a.pct or 0) > (b.pct or 0) end)
    return out
end

function PD.DropBlockLines(lines, itemID)
    local C_DR = { 0.72, 0.72, 0.76 }
    local list = PD.DropRowsOf(itemID)
    if not list then return end
    local shown = math.min(#list, PD.DROP_SHOW_MAX or 2)
    for i = 1, shown do
        local o = list[i]
        local txt = format(L["掉落：%s"], o.name)
        local zone = o.area and PD.CampZoneName(o.area) or nil
        if type(zone) == "string" and zone ~= "" then txt = txt .. " · " .. zone end
        local pt = PD.DropPctText(o.pct)
        if pt then txt = txt .. " · " .. pt end
        lines[#lines + 1] = { txt, Unpack(C_DR) }
    end
    if #list > shown then
        lines[#lines + 1] = { format(L["…等 %d 处"], #list - shown), Unpack(C_DR) }
    end
end

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
    PD.VendorBlockLines(lines, itemID)
    PD.DropBlockLines(lines, itemID)
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
    { "耐力提高(%d+)点", "耐力" },
    { "法术强度提高(%d+)点", "法术强度" },
    { "攻击强度提高(%d+)点", "攻击强度" },
    { "防御技能提高(%d+)点", "防御技能" },
    { "防御值提高(%d+)点", "防御技能" },
    { "防御提高(%d+)点", "防御技能" },
    { "护甲值提高(%d+)点", "护甲" },
    { "护甲提高(%d+)点", "护甲" },
}
PD.__kitEff = {}
function PD.KitEffectOf(itemID)
    if type(itemID) ~= "number" then return nil end
    local cached = PD.__kitEff[itemID]
    if cached ~= nil then
        if cached == false then return nil end
        return cached
    end
    if type(C_TooltipInfo) ~= "table" or type(C_TooltipInfo.GetItemByID) ~= "function" then
        PD.__kitEff[itemID] = false
        return nil
    end
    local ok, data = pcall(C_TooltipInfo.GetItemByID, itemID)
    local text, pending, count = nil, false, 0
    if ok and type(data) == "table" and type(data.lines) == "table" then
        count = #data.lines
        local useLine
        for i = 1, count do
            local ln = data.lines[i]
            local t = type(ln) == "table" and ln.leftText or nil
            if type(t) == "string" then
                if t:find("正在获取") or t:find("Loading item") then
                    pending = true
                elseif t:find("^使用：") or t:find("^Use:") then
                    useLine = useLine or t
                elseif (not useLine) and (t:find("永久性") or t:find("Permanently")) then
                    useLine = t
                end
            end
        end
        text = useLine
    end
    if text then
        PD.__kitEff[itemID] = text
        return text
    end
    if pending or count <= 1 then
        if DG and DG.RequestItem then DG.RequestItem(itemID) end
        return nil
    end
    PD.__kitEff[itemID] = false
    return nil
end
function PD.KitSub(sub, desc, itemID)
    if not sub or not sub:find("^永久附着") then return sub end
    if (type(desc) ~= "string" or desc == "") and itemID then desc = PD.KitEffectOf(itemID) end
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
    local catalogue = r
    if ns.ProfSourceMerge then ns.ProfSourceMerge.Fill(catalogue) end
    local meta = ns.ProfRecipeMeta and ns.ProfRecipeMeta[r[1]]
    local runtime = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r[1]]
    local resolved = PD.RecipeData(r, "rows")
    r = {}
    for key, value in pairs(catalogue) do r[key] = value end
    r[2], r[3], r[12] = resolved.item, resolved.count, resolved.mats
    r[7], r[8], r[9], r[10] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
    local clientPending = resolved.clientPending
    local station = meta and ({ forge = L["熔炉"], blackForge = L["黑铁熔炉"], moltenFoundry = L["熔火铸造厂"] })[meta.station]
    local vs = (r[14] and PD.VendorListOf(r[14])) or {}
    local hasVendor = #vs > 0
    local hasDrop = r[14] and r[14].drops and #r[14].drops > 0 and true or false
    local acq = (hasVendor and not hasDrop) and L["商人售卖"] or L["世界掉落"]
    local base
    if clientPending then
        base = L["客户端数据待读取"]
    elseif resolved.clientUnavailable then
        base = L["客户端已确认不可用"]
    elseif r[13] then
        base = L["图纸"] .. " · " .. acq
    else
        base = L["训练师"]
    end
    local dpre, dval
    if hasVendor then
        dpre = base
        if #vs > 1 then
            dval = format(L["商人：%s 等 %d 人"], PD.VendorName(vs[1]), #vs)
        else
            dval = format(L["商人：%s"], PD.VendorName(vs[1]))
        end
        local vfid = type(r[13]) == "table" and r[13][1] or nil
        local vmap = vfid and PD.FormulaOffersByNpc and PD.FormulaOffersByNpc(vfid) or nil
        local vcost = vmap and (vs[1].id or vs[1].npcID) and vmap[vs[1].id or vs[1].npcID] or nil
        if vcost then dval = dval .. " · " .. PD.FormulaCostText(vcost) end
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
        tipExtra = function()
            local lines = PD.RecipeSourceLines(PD.PriceTipLines(r[2], r[12]), resolved)
            if station then lines[#lines + 1] = { format(L["制作场地：%s"], station), 0.7, 0.7, 0.7 } end
            if clientPending then lines[#lines + 1] = { L["请打开对应专业或商人面板读取数据"], 0.95, 0.75, 0.4 } end
            if meta and meta.outputConflict and resolved.outputConflict and not (runtime and runtime.count) then
                lines[#lines + 1] = { L["参考产量存在冲突；当前按目录值显示，客户端读取后覆盖。"], 0.95, 0.75, 0.4 }
                lines[#lines + 1] = { format(L["目录产量 %d · 法术详情产量 %d"], meta.listedCount, meta.detailCount), 0.7, 0.7, 0.7 }
            elseif runtime and runtime.count and not resolved.variableOutput then
                lines[#lines + 1] = { format(L["客户端每次产量：%d"], runtime.count), 0.55, 0.85, 0.6 }
            end
            if meta and meta.availabilityUnknown and not resolved.clientAvailable then lines[#lines + 1] = { L["学习方式尚未确认；已学习后才参与计算。"], 0.95, 0.75, 0.4 } end
            return lines
        end,
        sub = station or PD.KitSub(tostring(r[5] or ""), r[6], r[2]),
        mats = clientPending and L["客户端数据待读取"] or nil,
        right = not ((r[7] or r[8] or r[9] or r[10]))
                and format("%s · %s", format(L["学 %s"], tostring(r[7])),
                           PD.TierText(r[8], r[9], r[10])) or nil,
        right2 = (not dval) and base or nil,
        src = r[14],
        vlines = hasVendor and PD.VendorLines(r[14], type(r[13]) == "table" and r[13][1] or nil) or nil,
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
            local eff = (type(r[6]) == "string" and r[6] ~= "") and r[6] or PD.KitEffectOf(r[2])
            if eff then lines[#lines + 1] = { eff } end
            local mt = PD.MatText(r[12], 4)
            lines[#lines + 1] = { format(L["材料：%s"], mt ~= "" and mt or L["无"]) }
            lines[#lines + 1] = { format(L["技能：学 %s · %s"], tostring(r[7]),
                                         PD.TierText(r[8], r[9], r[10])) }
            if r[15] and #r[15] > 0 then
                lines[#lines + 1] = { format(L["改版前材料：%s"], PD.MatText(r[15])), 0.9, 0.7, 0.4 }
            end
            if hasVendor then
                local fid = type(r[13]) == "table" and r[13][1] or nil
                for _, ln in ipairs(PD.VendorLines(r[14], fid)) do lines[#lines + 1] = ln end
                local ahLine = PD.FormulaAuctionLine(fid)
                if ahLine then lines[#lines + 1] = ahLine end
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
    local resolved = PD.RecipeData(c, "crafted")
    local original = c
    c = {}; for key, value in pairs(original) do c[key] = value end
    c[8], c[3], c[2] = resolved.mats, resolved.count, resolved.item
    c[4], c[5], c[6], c[7] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
    local clientPending = resolved.clientPending
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
        mats = clientPending and L["客户端数据待读取"] or matCol,
        matSegs = matSg,
        right = not (c[4] or c[5] or green or c[7])
                and format("%s · %s", format(L["学 %s"], tostring(c[4])),
                           PD.TierText(c[5], green, c[7])) or nil,
        right2 = clientPending and L["客户端数据待读取"] or (resolved.clientUnavailable and L["客户端已确认不可用"]) or base,
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(c[4]),
        gapVal = (ah and total) and (ah - total) or nil,
        sbdiff = (c[4] or c[5] or green or c[7]) and { c[4], c[5], green, c[7] } or nil,
        tipExtra = function() return PD.RecipeSourceLines(PD.PriceTipLines(c[2], c[8]), resolved) end,
        lines = {
            { format(L["材料：%s"], clientPending and L["客户端数据待读取"] or (mats ~= "" and mats or L["无"])) },
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

PD.__favorBuyMemo = {}

function PD.RowIsFavorBuy(r)
    local fid = r[13] and r[13][1]
    if not fid then return false end
    local flat = ns.EnsureProfFormulaOffers()[fid]
    if not flat then return false end
    for j = 1, #flat, 8 do
        if tonumber(flat[j + 6]) == 3402 then return true end
    end
    return false
end

local function FavorBuyCount(d)
    local m = PD.__favorBuyMemo
    local n = m[d]
    if n then return n end
    n = 0
    for _, r in ipairs(d.rows or {}) do
        if PD.RowIsFavorBuy(r) then n = n + 1 end
    end
    m[d] = n
    return n
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
    local fb = d.rows and FavorBuyCount(d) or 0
    if fb > 0 then
        tool[#tool + 1] = { key = "__favorbuy", text = format(L["商人兑换 %d"], fb),
                            on = on("__favorbuy") }
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
    return tool, function(k)
        PD.toolKey = k
        if PD.scroll then PD.scroll:SetVerticalScroll(0) end
        PD.RequestRender()
    end
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
            if PD.RecipeVisible(e[14]) then out[#out + 1] = PD.EnchantSpec(e) end
            if #out >= cap then break end
        end
        return out
    end
    if d.enchants and #d.enchants > 0 and not (d.rows and #d.rows > 0)
       and key ~= "__crafted" and key ~= "__favor" and key ~= "__favorbuy" and key ~= "__rest" then
        local want
        if key ~= "all" then want = tostring(key) end
        for _, e in ipairs(d.enchants or {}) do
            local g = tostring(e[3] or "")
            if g == "" then g = L["其他"] end
            if ((not want) or g == want) and PD.RecipeVisible(e[14]) then
                out[#out + 1] = PD.EnchantSpec(e)
                if #out >= cap then break end
            end
        end
        return out
    end
    if key == "__crafted" then
        for _, c in ipairs(d.crafted or {}) do
            if PD.RecipeVisible(c[1]) then out[#out + 1] = PD.CraftedSpec(c) end
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
    if key == "__favorbuy" then
        for _, r in ipairs(d.rows or {}) do
            if PD.RowIsFavorBuy(r) then
                out[#out + 1] = PD.RecipeSpec(r)
                if #out >= cap then break end
            end
        end
        return out
    end
    local fk = PD.EffKeyFilter(d)
    local __ri = 0
    local __tGate = debugprofilestop and debugprofilestop() or 0
    for _, r in ipairs(d.rows or {}) do
        __ri = __ri + 1
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                out[#out + 1] = PD.RecipeSpec(r)
                if #out >= cap then break end
            end
        end
        if coroutine.running and coroutine.running()
           and debugprofilestop and (debugprofilestop() - __tGate) >= 3 then
            __tGate = debugprofilestop()
            coroutine.yield()
        end
    end
    return out
end

function PD.RawHit(r, q)
    if not PD.RecipeVisible(r[1]) then return false end
    if not q or q == "" then return true end
    local nm = PD.ItemName(r[2])
    if nm and nm ~= "" and string.find(string.lower(tostring(nm)), q, 1, true) then
        return true
    end
    local sub = tostring(r[5] or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    local resolved = PD.RecipeData(r, "rows")
    for _, m in ipairs(resolved.mats or {}) do
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
                    local sw = PD.TextW(PD.KitSub(tostring(r[5] or ""), r[6], r[2]), 11) + (r[11] and PD.RECIPE_BADGE_W or 0)
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

function PD.FishingAreaName(area)
    if not area then return L["无数据"] end
    local name = area.name
    if not name and area.zoneID and DG.ZoneName then name = DG.ZoneName(area.zoneID) end
    name = name and (L[name] or name) or L["无数据"]
    return name
end

function PD.FishingAreaDetail(area, extra)
    local parts = {}
    if area.minSkill then parts[#parts + 1] = format(L["最低钓鱼技能 %d"], area.minSkill) end
    local safe = area.noGetaway or area.avoidGetaway
    if safe then parts[#parts + 1] = format(L["不脱钩技能 %d（含加成）"], safe) end
    if area.note then parts[#parts + 1] = L[area.note] or area.note end
    if extra and extra ~= "" then parts[#parts + 1] = L[extra] or extra end
    return table.concat(parts, " · ")
end

function PD.ShowFishingArea(area)
    if not area then return end
    local mapID = area.mapID or (ns.AreaMap and ns.AreaMap[area.zoneID])
    if not mapID then return end
    if type(area.x) == "number" and type(area.y) == "number" then
        PD.MarkMapPoint(mapID, area.x, area.y)
    elseif C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    elseif WorldMapFrame and WorldMapFrame.SetMapID then
        if WorldMapFrame.Show then pcall(WorldMapFrame.Show, WorldMapFrame) end
        pcall(WorldMapFrame.SetMapID, WorldMapFrame, mapID)
    end
end

function PD.RowsFishAreas(rows, fish, areas, col, tkey)
    local names, combined, seen, notes, ids = {}, {}, {}, {}, {}
    local function addArea(area, note)
        if type(area) ~= "table" then return end
        local key = tostring(area.zoneID or area.mapID or area.name) .. ":" .. tostring(area.name or "")
        if note and area.zoneID and not notes[area.zoneID] then notes[area.zoneID] = note end
        if not seen[key] then seen[key] = true; combined[#combined + 1] = area end
    end
    for _, entry in ipairs(fish or {}) do
        local id = entry.id or entry[1]
        if id then
            ids[#ids + 1] = tostring(id)
            local nm, known = DG.ItemName(id)
            if not known then
                PD.__itemNamePending = true
                if DG.RequestItem then DG.RequestItem(id) end
            end
            names[#names + 1] = format("%s ×%s", nm, tostring(entry.count or entry.need or entry[2] or 0))
        end
        for _, area in ipairs(entry.areas or {}) do addArea(area, entry.note) end
    end
    for _, area in ipairs(areas or {}) do addArea(area) end
    local akey = tkey or ("fishareas:" .. table.concat(ids, ","))
    local open
    if #ids > 0 then open = PD.fishAreaOpen[akey] == true else open = true end
    if #names > 0 then
        local canFold = #combined > 0
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H1, fs = 14, col = col,
            text = format(L["自行钓取：%s"], table.concat(names, "、")),
            nameColor = {0.42, 0.84, 0.95},
            right = canFold and (open and L["收起钓鱼区"] or L["展开钓鱼区"]) or nil,
            rightColor = canFold and C_GREY or nil,
            act = canFold and function()
                if PD.fishAreaOpen[akey] then PD.fishAreaOpen[akey] = nil else PD.fishAreaOpen[akey] = true end
                PD.RequestRender()
            end or nil,
        }
    end
    if open then
        for _, area in ipairs(combined) do
            local selected = area
            local mapID = selected.mapID or (ns.AreaMap and ns.AreaMap[selected.zoneID])
            local detail = PD.FishingAreaDetail(selected, notes[selected.zoneID])
            rows[#rows + 1] = {
                kind = "row", h = detail ~= "" and PD.ROW_H or PD.ROW_H1, fs = 14, col = col,
                text = format(L["钓鱼区域：%s"], PD.FishingAreaName(selected)), sub = detail,
                right = mapID and L["点击地图"] or nil,
                lines = {{PD.FishingAreaName(selected)}, {detail, 0.7, 0.7, 0.7},
                    {L["钓鱼加成包含鱼竿、鱼饵和装备；达到不脱钩技能更稳定。"], 0.7, 0.7, 0.7}},
                act = mapID and function() PD.ShowFishingArea(selected) end or nil,
            }
        end
    end
end

function PD.OnItemData()
    if not (PD.built and ns.PageVisible(PD.page)) then return end
    if not PD.__itemNamePending then return end
    if PD.__nameRepaint then return end
    PD.__nameRepaint = true
    C_Timer.After(0.25, function()
        PD.__nameRepaint = nil
        if PD.__itemNamePending and ns.PageVisible(PD.page) then
            PD.__itemNamePending = nil
            PD.RequestRender()
        end
    end)
end

function PD.RowsFishingLevelRoute(rows, curLv)
    local guide = ns.ProfFishingRoutes
    local steps = guide and guide.fishingSteps
    if not steps or #steps == 0 then return false end
    PushHead(rows, L["钓鱼升级路线（优先推荐水域）"])
    PushText(rows, L["成功钓获鱼类可提升技能；技能越高，通常需要更多次成功钓获。"], 11, C_GREY)
    PushText(rows, L["推荐按鱼类与技能选择水域；可留在低级水域练满，无需到点强制换区。"], 11, C_GREY)
    PushText(rows, L["钓鱼加成包含鱼竿、鱼饵和装备；达到不脱钩技能更稳定。"], 11, C_GREY)
    PushGap(rows)
    for index, step in ipairs(steps) do
        local lo, hi = step.from or step[1], step.to or step[2]
        local active = curLv and curLv >= lo and (curLv < hi or (index == #steps and curLv == hi))
        local fish = {}
        for _, id in ipairs(step.fishIDs or {}) do
            local nm, known = DG.ItemName(id)
            if not known then
                PD.__itemNamePending = true
                if DG.RequestItem then DG.RequestItem(id) end
            end
            fish[#fish + 1] = nm
        end
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H, text = format(L["%d – %d"], lo, hi),
            sub = #fish > 0 and table.concat(fish, "、") or nil,
            nameColor = active and {0.4, 0.9, 0.45} or nil,
            right = active and L["◆ 推荐当前就练这一档"] or nil,
        }
        if step.note then PushText(rows, L[step.note] or step.note, 11, C_GREY) end
        PD.RowsFishAreas(rows, nil, step.areas)
        PushGap(rows, 4)
    end
    return true
end

function PD.RowsGatherRoute(rows)
    local slug = PD.cur
    local g = GA and (GA[slug] or (slug == "fishing" and GA.fishing))
    if not g or #g == 0 then return end
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[slug] and _learned[slug].cur or nil
    local GR_GREEN = { 0.4, 0.9, 0.45 }

    if PD.GatherMode(slug) == "smelt" then
        PD.RowsLeveling(rows)
        return
    end
    if slug == "fishing" then
        if PD.RowsFishingLevelRoute(rows, curLv) then return end
        PushHead(rows, format(L["钓鱼升级路线（%d 处水域）"], #g))
        PushText(rows, L["成功钓获鱼类可提升技能；技能越高，通常需要更多次成功钓获。"], 11, C_GREY)
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
        local cp = {}
        for k, v in pairs(st) do cp[k] = v end
        cp[2], cp[4], cp._clip = nb, st.checkpoint and 0 or nq, isClip or nil
        out[#out + 1] = cp
    end
    return out, clipped
end

local function FixedShopData(target)
    local lv = LV[PD.cur]
    local steps, clipped = ClipFixedSteps(lv.steps or {}, target)
    if RA and RA.SummarizeSteps then
        local sum = RA.SummarizeSteps(steps, PD.cur,
                                      { learnedOnly = PD.Setting("autoLearnedOnly"), target = target })
        if sum then
            sum.mode = "fixed"
            sum.target = target
            sum.clipped = clipped
            return sum
        end
    end
    return { mode = "fixed", target = target, mats = {}, clientPending = true,
             steps = lv.steps or {}, priced = false }
end

local function CountUnpriced(sum)
    local n = 0
    for _, e in ipairs(sum.mats or {}) do if e.unpriced then n = n + 1 end end
    return n
end

function PD.SnapshotSecText(sec)
    if not sec then return nil end
    if sec < 60 then return L["刚刚Auctionator"] end
    if sec < 90 * 60 then
        return format(L["%d 分钟前Auctionator"], math.max(1, math.floor(sec / 60 + 0.5)))
    end
    if sec < 24 * 3600 then
        return format(L["%d 小时前Auctionator"], math.max(1, math.floor(sec / 3600 + 0.5)))
    end
    return format(L["%d 天前Auctionator"], math.floor(sec / 86400 + 0.5))
end

function PD.PlanStatusParts(plan)
    if not plan then return L["正在计算升级路线…"] end
    if plan.scheme == "fishing" and not plan.partial and plan.status == "complete" then return L["纯钓鱼路线已生成"] end
    if plan.optimal and plan.supplyComplete ~= false then return L["当前价格与期望模型内最优"] end
    if plan.partial then
        return format(L["已计算至%d"], plan.plannedTo or plan.start or 1), L["后续路线待补全"]
    end
    if plan.pricePending and PD.PlanHasSteps(plan) then return L["参考路线已生成；材料价格待补全"] end
    if plan.feasible == false and PD.PlanHasSteps(plan) then
        return L["可先完成已计算步骤；后续路线待补全"]
    end
    local status = {
        searching = L["后台优化中"], paused = L["优化已停止"],
        stopped = L["优化已停止"], infeasible = L["当前限制下没有可行路线"],
        incomplete = L["资料或价格不完整"], complete = L["当前找到的最低支出"],
        error = L["计算发生错误，请重新计算。"],
        selection_required = L["请选择搭配的主专业"],
        recalculate_required = L["搭配专业已更改，点击重新计算应用。"],
    }
    return status[plan.status] or L["正在计算升级路线…"]
end

function PD.PlanStatusText(plan)
    local a, b = PD.PlanStatusParts(plan)
    if b then return a .. " " .. b end
    return a
end

function PD.PlanProgressText(plan)
    if not plan or plan.expanded == nil then return nil end
    if plan.expanded == 0 and plan.initialTotal == nil then return nil end
    if plan.initialTotal == nil then return format(L["仍在优化：已比较 %d 种组合"], plan.expanded or 0) end
    local savings = plan.savings
    if savings == nil and plan.initialTotal and plan.total then
        savings = math.max(0, plan.initialTotal - plan.total)
    end
    return format(L["仍在优化：已比较 %d 种组合，较初始方案节省 %s"], plan.expanded or 0, RA.MoneyStr(savings or 0))
end

function PD.PlanCacheText(plan)
    if plan and plan.stale then return L["已保存路线；数据或设置已变化，点击重新计算更新。"] end
end

function PD.PlanSupplyParts(plan)
    local unknown = plan and tonumber(plan.auctionSupplyUnknown)
    if not (unknown and unknown > 0) then return nil end
    local head = format(L["有 %d 种拍卖行物品数量未知，暂按价格估算；请在拍卖师处执行一次完整扫描后重新计算。"], unknown)
    local names, seen, count = {}, {}, 0
    for _, list in ipairs({plan.mats or {}, plan.formulas or {}}) do
        for _, entry in ipairs(list) do
            local id = tonumber(entry.id or entry[1])
            local auction = entry.source == "ah" or entry.source == "auction"
            if auction and not entry.vendor and not entry.known and id and not seen[id]
                and entry.supplyObserved ~= true and tonumber(entry.availableCount) == nil then
                seen[id] = true; count = count + 1
                if #names < 3 then
                    local name, loaded = PD.ItemName(id)
                    if not name or name == "" or loaded == false then name = "#" .. tostring(id) end
                    names[#names + 1] = name
                end
            end
        end
    end
    local detail
    if count > #names then
        detail = format(L["数量未知物品：%s，另有 %d 种（详见购物清单）。"], table.concat(names, " / "), count - #names)
    elseif #names > 0 then
        detail = format(L["数量未知物品：%s。"], table.concat(names, " / "))
    end
    return head, detail
end

function PD.PlanSupplyText(plan)
    local head, detail = PD.PlanSupplyParts(plan)
    if not head then return nil end
    if detail then return head .. " " .. detail end
    return head
end

function PD.AuctionSupplyText(entry)
    if entry.vendor or entry.source == "vendor" or entry.source == "npc" then return end
    local source = entry.source or entry.sourceType
    if source ~= "ah" and source ~= "auction" then return end
    local available = tonumber(entry.availableCount)
    if available then
        local need = entry.count or entry.need or entry[2] or 0
        if entry.supplySource == "auctionator-update" then
            return format(L["扫描汇总估计：%d 件；本路线购买 %d 件。"], available, need)
        end
        if available < need then
            return format(L["拍卖行已读取数量不足：可购 %d 件，需要 %d 件。"], available, need)
        end
        if entry.supplyComplete == false then
            return format(L["拍卖行已读取：%d 件（结果未全部读取）；本路线购买 %d 件。"], available, need)
        end
        return format(L["拍卖行数量快照：%d 件；本路线购买 %d 件。"], available, need)
    end
    if entry.supplyObserved == false then return L["拍卖行可购数量未知，当前仅按价格估算。"] end
end

function PD.AuctionObservationText(observedAt)
    local stamp = tonumber(observedAt)
    if not stamp or stamp ~= stamp or stamp < 1000000000 or stamp == math.huge then
        return L["观测时间未知"]
    end
    if type(date) == "function" then
        local ok, value = pcall(date, "%Y-%m-%d %H:%M", stamp)
        if ok and type(value) == "string" then return value end
    end
    return tostring(math.floor(stamp))
end

function PD.AuctionSupplyLines(entry)
    local source = entry.source or entry.sourceType
    local auction = not entry.vendor and (source == "ah" or source == "auction")
    local lines = {}
    local function add(text, warn)
        lines[#lines + 1] = {text, warn and 0.95 or 0.7, warn and 0.75 or 0.7, warn and 0.4 or 0.7}
    end
    if auction then
        local text = PD.AuctionSupplyText(entry)
        if text then add(text) end
        if tonumber(entry.availableCount) then
            add(format(L["数量观测：%s"], PD.AuctionObservationText(entry.supplyObservedAt)))
            if entry.supplySource == "client-auction-results" then
                add(L["数量来源：客户端拍卖结果"])
            elseif entry.supplySource == "auctionator-update" then
                add(L["数量来源：Auctionator 最近更新（扫描汇总估计）"])
            else
                add(L["数量来源：旧路线记录（范围未核实）"])
            end
            if entry.supplyComplete == true then
                add(L["扫描范围：完整结果"])
            elseif entry.supplyComplete == false and entry.supplySource ~= "auctionator-update" then
                add(L["扫描范围：部分结果，仅代表已读取数量"])
            else
                add(L["扫描范围：未核实"])
            end
            add(entry.supplyOwnerExcluded == true and L["已排除本人拍卖"] or L["是否包含本人拍卖：未核实"])
            local stamp = tonumber(entry.supplyObservedAt)
            local now = type(time) == "function" and time() or nil
            if stamp and stamp >= 1000000000 and now and now - stamp > 2 * 86400 then
                add(L["数据较旧（超过两天）；仍按保存数量规划，请扫描后更新。"], true)
            end
            add(L["最近观测数量不保证当前仍在售，也不保证全部可按最低价格购买。"])
            if type(entry.supplyObservedPrice) == "number" then
                add(format(L["数量观测时最低单价：%s"], RA.MoneyStr(entry.supplyObservedPrice, "copper")))
            end
        elseif entry.supplyObserved == false then
            add(L["请在拍卖师处执行一次完整扫描，以保存最近数量。"], true)
        end
        local history = tonumber(entry.supplyHistoryQuantity)
        if history and history >= 0 then
            add(format(L["Auctionator 当日最高数量：%d（仅供参考，不限制路线）"], history))
            add(format(L["历史数量日期：%s"], PD.AuctionObservationText(entry.supplyHistoryObservedAt)))
        end
    end
    if auction or type(entry.ahPrice) == "number" then
        add(format(L["拍卖行价格观测：%s"], PD.AuctionObservationText(entry.priceObservedAt)))
    end
    return lines
end

function PD.PlanHasSteps(plan)
    return plan and type(plan.steps) == "table" and #plan.steps > 0 or false
end

function PD.CopyRecoverySummary(src)
    local s = PD.lvSummary
    if not s or not src then return end
    s.recoveryTotal = src.recoveryTotal
    s.netTotal = src.netTotal
    s.recoveryMissing = src.recoveryMissing
    s.recoveryOptimized = src.recoveryOptimized
    s.recoveryAssumesAllSold = src.recoveryAssumesAllSold
    s.recoveryFeePercent = src.recoverySnapshot and src.recoverySnapshot.feePercent or nil
    s.saleOutputs = src.saleOutputs
    s.purchaseTotal = src.purchaseTotal or src.total
end

function PD.RecoverySummaryText(src)
    if not src then return nil end
    local rec = src.recoveryTotal
    if type(rec) ~= "number" then return nil end
    local fee = src.recoverySnapshot and src.recoverySnapshot.feePercent
    local net = src.netTotal or ((src.purchaseTotal or src.total or 0) - rec)
    local text = format(L["预计回血 %s · 净成本 %s"], PD.RecoveryMoney(rec), PD.RecoveryMoney(net))
    if fee then text = text .. format(L["（已扣 %d%% 手续费）"], fee) end
    return text
end

function PD.StepRecoveryText(st)
    if type(st) ~= "table" then return nil end
    local rec = st.recoveryTotal
    if type(rec) ~= "number" or rec <= 0 then return nil end
    local net = st.netTotal or ((st.attributedCost or 0) - rec)
    return format(L["本步回血 %s · 净 %s"], PD.RecoveryMoney(rec), PD.RecoveryMoney(net))
end

function PD.StepCostLines(st)
    if type(st) ~= "table" then return nil end
    local lines = {}
    if type(st.productionCost) == "number" then
        lines[#lines + 1] = { format(L["实际制作成本：%s"], PD.RecoveryMoney(st.productionCost)), 0.75, 0.75, 0.75 }
    end
    if (st.transferredCost or 0) > 0 then
        lines[#lines + 1] = { format(L["转入下游成本：%s"], PD.RecoveryMoney(st.transferredCost)), 0.75, 0.75, 0.75 }
    end
    if type(st.attributedCost) == "number" then
        lines[#lines + 1] = { format(L["最终归属成本：%s"], PD.RecoveryMoney(st.attributedCost)), 0.85, 0.85, 0.85 }
    end
    if (st.recoveryTotal or 0) > 0 then
        lines[#lines + 1] = { format(L["自身剩余产物预计回血：%s"], PD.RecoveryMoney(st.recoveryTotal)), 0.55, 0.85, 0.6 }
    end
    if (st.transferredCost or 0) > 0 then
        lines[#lines + 1] = { L["已投入下游的中间产物不重复计算销售收入。"], 0.7, 0.7, 0.7 }
    end
    if type(st.saleCount) == "number" and st.saleCount > 0 then
        lines[#lines + 1] = { format(L["最终可出售 %d 件：制材自然余量 %d；额外升级产物 %d。"],
            st.saleCount, st.naturalRemainder or 0, st.levelingRemainder or 0), 0.75, 0.75, 0.75 }
    end
    local outs = st.recoveryOutputs
    if type(outs) == "table" then
        for _, o in ipairs(outs) do
            local n = tonumber(o.count) or 0
            if n > 0 then
                local channel = o.missing and L["售价缺失，未计回血"]
                    or (o.source == "ah" and L["推荐拍卖（扣手续费）"] or L["推荐卖给 NPC"])
                lines[#lines + 1] = { format(L["%s ×%d · %s · 净单价 %s · 预计回血 %s"],
                    DG.ItemName(o.id) or ("#" .. tostring(o.id)), n, channel,
                    o.missing and L["价格未知"] or PD.RecoveryMoney(o.unit or 0),
                    o.missing and L["价格未知"] or PD.RecoveryMoney(o.revenue or 0)), 0.7, 0.7, 0.7 }
            end
        end
    end
    if #lines == 0 then return nil end
    return lines
end

function PD.PlanCostText(plan)
    if plan.completeCost==false and (plan.total or 0)==0 then return L["材料价格待补全"] end
    return (plan.completeCost==false and "≥" or "")..RA.MoneyStr(plan.total or 0,"copper")
end

function PD.CopyPlanSummary(plan)
    if not plan or plan.planVersion ~= 2 then return end
    local s = PD.lvSummary or {}
    for _, key in ipairs({"planVersion", "status", "optimal", "feasible", "completeCost",
                           "revision", "partial", "plannedTo", "targetReached", "start", "target",
                           "expanded", "improvements", "initialTotal", "savings", "searchComplete", "budgetLimited",
                           "stale", "cached", "settingsChanged", "referencePrices", "pricePending", "referenceRoute",
                           "auctionSupplyUnknown", "auctionSupplyObserved", "supplyComplete",
                           "formulasTotal", "formulaTotal", "formulaComplete", "formulaBlocked"}) do s[key] = plan[key] end
    s.ahOK = true
    s.priced = plan.total ~= nil and plan.feasible ~= false
    PD.lvSummary = s
end

function PD.StepRecipe(st)
    if st.recipe then
        local live = {}
        for key, value in pairs(st.recipe) do live[key] = value end
        live.makes = live.item
        return live
    end
    local slug = st.profession or PD.cur
    local data = RGet(slug)
    for _, rec in ipairs(data and data.rows or {}) do
        if rec[1] == st[3] then
            local resolved = PD.RecipeData(rec, "rows", slug)
            local live = {}
            for key, value in pairs(rec) do live[key] = value end
            live[12], live[3], live[2] = resolved.mats, resolved.count, resolved.item
            live[7], live[8], live[9], live[10] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
            live.clientPending, live.dataSource = resolved.clientPending, resolved.dataSource
            live.outputMin, live.outputMax, live.variableOutput = resolved.outputMin, resolved.outputMax, resolved.variableOutput
            live.outputBasis = resolved.outputBasis
            return live
        end
    end
    for _, kind in ipairs({"crafted", "enchants"}) do
        for _, rec in ipairs(data and data[kind] or {}) do
            if (kind == "enchants" and rec[14] or rec[1]) == st[3] then
                local resolved = PD.RecipeData(rec, kind, slug)
                resolved.makes = resolved.item
                return resolved
            end
        end
    end
    local leveling = LV and LV[slug]
    local rec = leveling and leveling.rinfo and leveling.rinfo[st[3]]
    if rec then
        local live = {}
        for key, value in pairs(rec) do live[key] = value end
        live.spell, live.item, live.count = st[3], live.makes, live.count or 1
        local E = ns.ProfEconomy
        if E and E.ResolveRecipe then live = E.ResolveRecipe(live, slug) end
        live.makes = live.item
        return live
    end
end
function PD.StepIsMaterial(st)
    local tags = st.tags or {}
    local leveling = tags.leveling or st.role == "level" or st.role == "both"
    local material = tags.material or st.role == "material" or st.role == "both"
    if not leveling and not material then material = st.reason == "material" end
    return material and true or false
end
function PD.StepRole(st)
    if st.checkpoint or st[3] == 0 then return L["实地采矿"] end
    local tags = st.tags or {}
    local leveling = tags.leveling or st.role == "level" or st.role == "both"
    local material = PD.StepIsMaterial(st)
    if not leveling and not material then leveling = true end
    if leveling and material then return L["升级&中间产物"] end
    return material and L["中间产物"] or L["升级"]
end

function PD.StepRange(st)
    return format(L["%s – %s"], tostring(st[1]), tostring(st[2]))
end

function PD.PurchaseSource(entry)
    if entry.vendor or entry.source == "vendor" or entry.source == "npc" then return L["NPC购买"] end
    return L["拍卖行"]
end
function PD.PurchasePriceHint(entry)
    if entry.reference then return L["参考报价（实际报价可能因声望而异；客户端实测优先）"] end
end
function PD.StepName(st)
    return (st.checkpoint or st[3] == 0) and L["实地采矿"] or SpellName(st[3])
end

function PD.PolicyMode(profession, spell)
    local E = ns.ProfEconomy
    local policies = E and E.GetPolicies and E.GetPolicies(PD.cur, true) or {}
    local pro = policies[profession]
    return type(pro) == "table" and (pro[spell] or pro[tostring(spell)]) or policies[profession .. ":" .. spell]
end

function PD.ChangeRecipePolicy(profession, spell, forceBan, apply)
    local E = ns.ProfEconomy
    if not (E and E.SetPolicy) then return end
    local mode = PD.PolicyMode(profession, spell)
    local nextMode
    if forceBan or mode == nil then nextMode = "ban"
    elseif mode == "ban" then nextMode = nil end
    E.SetPolicy(PD.cur, profession, spell, nextMode, true)
    PD.policyDirty = PD.policyDirty or {}
    if apply then
        PD.policyDirty[PD.cur] = nil
        if E.ApplyPolicies then E.ApplyPolicies(PD.cur) end
        PD.LvRecalc()
    else
        PD.policyDirty[PD.cur] = true
    end
    PD.RequestRender()
end

function PD.FlushPolicies()
    local E = ns.ProfEconomy
    if PD.policyDirty and PD.policyDirty[PD.cur] then
        PD.policyDirty[PD.cur] = nil
        if E and E.ApplyPolicies then E.ApplyPolicies(PD.cur) end
        PD.LvRecalc()
    end
end

function PD.CountBans()
    local E = ns.ProfEconomy
    local n = 0
    if E and E.GetPolicies then
        for _, mode in pairs(E.GetPolicies(PD.cur, true)) do
            if mode == "ban" then n = n + 1 end
        end
    end
    local mdb = ProfDB().matBan
    local m = 0
    if mdb then
        for _ in pairs(mdb[PD.cur] or {}) do m = m + 1 end
    end
    return n, m
end

function PD.ExclusionEntries()
    local E = ns.ProfEconomy
    local recipe, material, seen, meta = {}, {}, {}, {}
    local steps = PD.autoSnapshotSlug == PD.cur and PD.autoSnapshot and PD.autoSnapshot.steps or {}
    for _, st in ipairs(steps) do
        if st[3] and st[3] ~= 0 then
            local key = (st.profession or PD.cur) .. ":" .. st[3]
            if PD.StepRole(st) == L["中间产物"] then
                meta[key] = meta[key] or { material = true }
            elseif not meta[key] then
                meta[key] = { reason = st.reason }
            end
        end
    end
    local function add(profession, spell)
        if not spell or spell == 0 then return end
        local key = profession .. ":" .. spell
        if seen[key] then return end
        seen[key] = true
        local m = meta[key]
        local bucket = (m and m.material) and material or recipe
        bucket[#bucket + 1] = { profession, spell, m and m.reason or nil }
    end
    for _, st in ipairs(steps) do add(st.profession or PD.cur, st[3]) end
    for profession, policies in pairs(E and E.GetPolicies and E.GetPolicies(PD.cur, true) or {}) do
        if type(policies) == "table" then for spell in pairs(policies) do add(profession, tonumber(spell)) end
        elseif type(profession) == "string" then
            local pro, spell = profession:match("^([^:]+):(%d+)$")
            if pro then add(pro, tonumber(spell)) end
        end
    end
    local function sortAll(t)
        table.sort(t, function(a, b) return a[1] == b[1] and a[2] < b[2] or a[1] < b[1] end)
    end
    sortAll(recipe)
    sortAll(material)
    local reg = PD.exReg
    if not reg or reg.slug ~= PD.cur then reg = { slug = PD.cur, map = {} }; PD.exReg = reg end
    for _, e in ipairs(recipe) do
        local key = e[1] .. ":" .. e[2]
        local old = reg.map[key]
        if old then old[3] = e[3] else reg.map[key] = { e[1], e[2], e[3] } end
    end
    local stable = {}
    for _, e in pairs(reg.map) do stable[#stable + 1] = e end
    return stable, material
end

local function MatBanMap()
    local db = ProfDB()
    db.matBan = db.matBan or {}
    db.matBan[PD.cur] = db.matBan[PD.cur] or {}
    return db.matBan[PD.cur]
end

local function MatRecipesUsing(itemId)
    local out = {}
    local rr = RGet(PD.cur)
    if rr and rr.rows then
        for _, r in ipairs(rr.rows) do
            local mats = r[12] or r[8]
            if type(mats) == "table" then
                for _, m in ipairs(mats) do
                    if type(m) == "table" and (m[1] == itemId or m.id == itemId) then
                        out[#out + 1] = r[1]
                        break
                    end
                end
            end
        end
    end
    return out
end

local function SetMatBan(itemId, ban)
    local E = ns.ProfEconomy
    if not (E and E.SetPolicy) then return end
    local map = MatBanMap()
    local spells = MatRecipesUsing(itemId)
    if ban then
        map[itemId] = spells
        for _, spell in ipairs(spells) do E.SetPolicy(PD.cur, PD.cur, spell, "ban", true) end
    else
        map[itemId] = nil
        for _, spell in ipairs(spells) do
            if PD.PolicyMode(PD.cur, spell) == "ban" then
                local still = false
                for _, mspells in pairs(map) do
                    if type(mspells) == "table" then
                        for _, s2 in ipairs(mspells) do
                            if s2 == spell then still = true break end
                        end
                    end
                    if still then break end
                end
                if not still then E.SetPolicy(PD.cur, PD.cur, spell, nil, true) end
            end
        end
    end
    PD.policyDirty = PD.policyDirty or {}
    PD.policyDirty[PD.cur] = true
end

function PD.RowsExclusions(rows)
    local EX_OK = { 0.56, 0.80, 0.42 }
    local EX_WARN = { 0.90, 0.74, 0.36 }
    local EX_BAD = { 0.90, 0.50, 0.50 }
    PD.exSub = PD.exSub or "recipe"
    local isMaterial = PD.exSub == "material"
    PushHead(rows, isMaterial and L["管理排除 · 材料"] or L["管理排除 · 图样"])
    rows[#rows].right = L["左键切换允许或禁止；右键直接禁止"]
    rows[#rows].h = 26
    rows[#rows].noHover = true
    rows[#rows].wpad = 14
    local recipeList, materialList = PD.ExclusionEntries()
    local splan = PD.autoSnapshotSlug == PD.cur and PD.autoSnapshot or nil
    local matCount = (splan and splan.mats) and #splan.mats or #materialList
    local segs = {
        { text = format(L["图样 %d"], #recipeList), on = PD.exSub ~= "material", key = "ex_sub_recipe" },
        { text = format(L["材料 %d"], matCount), on = PD.exSub == "material", key = "ex_sub_material" },
        { text = L["全部恢复"], key = "restore_all" },
    }
    if splan and splan.status == "searching" then
        segs[#segs + 1] = { text = L["停止优化"], key = "stop_search" }
    end
    rows[#rows].segs = segs
    local wait = {}
    local function want(id)
        if not id then return end
        local gi = C_Item and C_Item.GetItemInfo
        if gi and gi(id) then return end
        if C_Item and C_Item.RequestLoadItemDataByID then pcall(C_Item.RequestLoadItemDataByID, id) end
        wait[#wait + 1] = id
    end
    local cards = {}
    if isMaterial then
        local plan = PD.autoSnapshotSlug == PD.cur and PD.autoSnapshot or nil
        local mats = plan and plan.mats or nil
        if mats then
            for _, e in ipairs(mats) do
                local id, n = e.id or e[1], e.count or e[2] or 0
                want(id)
                local src = PD.PurchaseSource(e)
                local banned = MatBanMap()[id] and true or false
                local tips = { { DG.ItemName(id), 1, 0.82, 0.4 },
                               { format(L["需要：%d"], e.need or n) } }
                if e.unpriced then
                    tips[#tips + 1] = { PD.UnpriceWhy(e, id), 0.95, 0.75, 0.4 }
                else
                    tips[#tips + 1] = { format(L["约 %s"], RA.MoneyStr(e.cost, "copper")), 1, 0.82, 0 }
                end
                tips[#tips + 1] = { src, 0.7, 0.7, 0.7 }
                tips[#tips + 1] = { L["禁止使用：不用任何需要该材料的配方。"], 0.7, 0.7, 0.7 }
                cards[#cards + 1] = {
                    name = DG.ItemName(id),
                    it = id,
                    src = src .. " · " .. format("×%d", n),
                    modeText = banned and L["禁止"] or L["允许"],
                    color = banned and EX_BAD or EX_OK,
                    tips = tips,
                    act = function(_, button)
                        if button == "RightButton" then
                            if not banned then SetMatBan(id, true) end
                        else
                            SetMatBan(id, not banned)
                        end
                    end,
                }
            end
            if #cards == 0 then
                PushText(rows, L["没有需要准备的材料。"], 12, C_GREY)
            end
        else
            PushText(rows, L["先计算一条路线，再点击路线配方设置排除。"], 12, C_GREY)
        end
        PD.notReady = (#wait > 0) and wait or nil
        if PD.notReady and not PD.sweeping then PD.ScheduleSweep() end
        if #cards > 0 then
            local ch, gap, cols = 44, 6, 3
            local gridRows = math.ceil(#cards / cols)
            rows[#rows + 1] = {
                kind = "exgrid", span = true, noHover = true,
                h = gridRows * ch + (gridRows - 1) * gap,
                cards = cards,
            }
        end
        return
    end
    if #recipeList == 0 then
        PushText(rows, L["先计算一条路线，再点击路线配方设置排除。"], 12, C_GREY)
        return
    end
    local function recipeInfo(profession, spell)
        local rr = RGet(profession)
        if rr and rr.rows then
            for _, r in ipairs(rr.rows) do
                if r[1] == spell then return r end
            end
        end
        local lv = LV and LV[profession]
        return lv and lv.rinfo and lv.rinfo[spell] or nil
    end
    local function spellItem(rec)
        if not rec then return nil end
        if rec[2] then return rec[2] end
        if rec.makes or rec.item then return rec.makes or rec.item end
        return nil
    end
    local infos = {}
    for _, entry in ipairs(recipeList) do
        local profession, spell = entry[1], entry[2]
        local rec = recipeInfo(profession, spell)
        local ri = nil
        if rec and (rec.mats or rec.learn) then ri = rec; rec = nil end
        local learn = (ri and ri.learn) or (rec and rec[7]) or nil
        infos[#infos + 1] = { profession = profession, spell = spell, reason = entry[3],
                              rec = rec, ri = ri, learn = tonumber(learn) }
    end
    table.sort(infos, function(a, b)
        local la, lb = a.learn or 9999, b.learn or 9999
        if la ~= lb then return la < lb end
        return a.profession == b.profession and a.spell < b.spell or a.profession < b.profession
    end)
    for _, info in ipairs(infos) do
        local profession, spell = info.profession, info.spell
        local mode = PD.PolicyMode(profession, spell)
        local rec, ri = info.rec, info.ri
        local item = spellItem(rec) or spellItem(ri)
        want(item)
        local src
        if profession ~= PD.cur then
            local pro = D.pro[profession]
            src = (pro and pro.name or profession) .. " · "
                  .. (info.reason == "secondary" and L["联合升级"] or L["制作材料"])
        elseif rec then
            src = PD.LevelSrc(rec)
        elseif ri then
            src = ri.trainer and L["向训练师学习"] or nil
        end
        if rec and rec.clientPending then src = L["客户端数据待读取"] end
        cards[#cards + 1] = {
            name = SpellName(spell),
            it = item,
            src = src,
            modeText = mode == "ban" and L["禁止"] or L["允许"],
            color = (mode == "ban" and EX_BAD) or EX_OK,
            tips = { { SpellName(spell), 1, 0.82, 0.4 },
                     { L["完全禁止制作：可用购买或其他配方替代产物。"] },
                     { L["左键切换允许或禁止；右键直接禁止。"], 0.7, 0.7, 0.7 } },
            act = function(_, button)
                PD.ChangeRecipePolicy(profession, spell, button == "RightButton", false)
            end,
        }
    end
    PD.notReady = (#wait > 0) and wait or nil
    if PD.notReady and not PD.sweeping then PD.ScheduleSweep() end
    local ch, gap, cols = 44, 6, 3
    local gridRows = math.ceil(#cards / cols)
    rows[#rows + 1] = {
        kind = "exgrid", span = true, noHover = true,
        h = gridRows * ch + (gridRows - 1) * gap,
        cards = cards,
    }
end

function PD.RoutePairContext()
    local E = ns.ProfEconomy
    if not (E and E.RouteContext) then return nil end
    local learned = PD.ProfLearned and PD.ProfLearned() or {}
    local current = learned[PD.cur] and learned[PD.cur].cur
    local opts = {
        start = current,
        allowSecondaryLeveling = PD.Setting("autoSecondaryLeveling"),
        secondaryProfession = E.GetRoutePartner and E.GetRoutePartner(PD.cur) or nil,
    }
    return E.RouteContext(PD.cur, opts, E.Professions and E.Professions() or nil)
end

function PD.SpecQuestGoal(slug)
    local G = ns.ProfGates
    if not (G and G.SpecializationContext) then return nil end
    local slot = slug or PD.cur
    if slot ~= "engineering" then return nil end
    local target = (PD.LvTarget and PD.LvTarget()) or 0
    local ok, ctx = pcall(G.SpecializationContext, { profession = slot, target = target })
    if not ok or type(ctx) ~= "table" then return nil end
    local goal = ctx.goals and ctx.goals[1]
    if goal and goal.level == nil and type(ctx.level) == "number" then goal.level = ctx.level end
    return goal, ctx
end

function PD.SpecQuestBranch(goal)
    if goal and goal.choice == "goblin" then return L["地精工程学"] end
    return L["侏儒工程学"]
end

function PD.SpecQuestWhere(goal)
    local nm = tostring(goal.npcName or "?")
    local map = (goal.mapID and PD.MapName(goal.mapID, nil)) or ""
    local sub = tostring(goal.zone or "")
    local place = map
    if sub ~= "" then place = (map ~= "" and (map .. "-" .. sub)) or sub end
    local coords = ""
    if type(goal.x) == "number" and type(goal.y) == "number" then
        coords = format(" %.1f, %.1f", goal.x, goal.y)
    end
    if place ~= "" then return format("%s(%s%s)", nm, place, coords) end
    return nm .. coords
end

function PD.SpecQuestState(goal)
    local p = (goal and goal.questProgress) or {}
    if p.completed then return L["任务已完成"], 0.62, 0.62, 0.62 end
    if p.readyForTurnIn then return L["任务可交付"], 0.45, 0.92, 0.55 end
    if p.inLog then return L["任务已接取"], 0.98, 0.82, 0.42 end
    return L["任务未接取"], 0.74, 0.74, 0.74
end

function PD.SpecQuestLines(goal)
    local out = {}
    out[#out + 1] = { format(L["%s入门任务"], PD.SpecQuestBranch(goal)), 1, 0.82, 0.35 }
    if goal.questName and goal.questName ~= "" then
        out[#out + 1] = { format(L["任务名：%s"], "《" .. tostring(goal.questName) .. "》"), 0.82, 0.82, 0.82 }
    end
    out[#out + 1] = { format(L["接取地点：%s"], PD.SpecQuestWhere(goal)), 0.75, 0.75, 0.75 }
    local mats = {}
    for _, input in ipairs(goal.inputs or {}) do
        local nm = DG.ItemName(input[1]) or ("#" .. tostring(input[1]))
        mats[#mats + 1] = format("%s ×%d", nm, input[2] or 1)
    end
    if #mats > 0 then
        out[#out + 1] = { format(L["需要材料：%s"], table.concat(mats, "、")), 0.75, 0.75, 0.75 }
    end
    local state, r, g, b = PD.SpecQuestState(goal)
    out[#out + 1] = { state, r, g, b }
    if goal.blockedReason == "specializationLevelRequired" then
        out[#out + 1] = { format(L["专业点数达到 %d 后才能接取（当前 %d）。"],
            goal.minSkill or 0, goal.level or 0), 0.98, 0.62, 0.4 }
    elseif goal.blockedReason == "specializationQuestAlreadyCompleted" then
        out[#out + 1] = { L["本分支入门任务已完成，但专精能力尚未学会。"], 0.98, 0.62, 0.4 }
    elseif goal.blockedReason == "specializationQuestDisabled" then
        out[#out + 1] = { L["该任务当前不可用。"], 0.98, 0.62, 0.4 }
    elseif not (goal.questProgress and (goal.questProgress.completed or goal.questProgress.inLog)) then
        out[#out + 1] = { L["先在对应导师处完成前置任务，再接取本任务。"], 0.7, 0.7, 0.7 }
    end
    return out
end

function PD.RowsSpecQuest(rows)
    local goal = PD.SpecQuestGoal(PD.cur)
    if not goal then return end
    local branch = PD.SpecQuestBranch(goal)
    local state, r, g, b = PD.SpecQuestState(goal)
    local primary = goal.questName and goal.questName ~= ""
                    and ("《" .. tostring(goal.questName) .. "》") or branch
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H, col = 1,
        text = format(L["专精入门任务：%s"], primary),
        sub = PD.SpecQuestWhere(goal),
        lines = PD.SpecQuestLines(goal),
        right = state,
        rightColor = { r, g, b },
        act = function() PD.MarkMapPoint(goal.mapID, goal.x, goal.y) end,
    }
    PushGap(rows, 4)
end

function PD.RowsRoutePartner(rows, context)
    if not context then return end
    local first = #rows + 1
    local function spanRows()
        for index = first, #rows do rows[index].span = true end
    end
    if context.unlearned and PD.Setting("autoLearnedOnly") then
        PushText(rows, L["此专业尚未学习，已忽略「仅使用已学习的配方」。"], 11, C_GREY)
    end
    if not context.requiresPartner then spanRows(); return end
    local E, target = ns.ProfEconomy, PD.cur
    local learned = PD.ProfLearned and PD.ProfLearned() or {}
    local function skillText(slug)
        local actual = learned[slug]
        if actual then
            return format(L["已学 · 技能 %d/%d"], actual.cur or 1, actual.max or actual.cur or 1)
        end
        return L["未学 · 从 1 开始"]
    end
    local selected = context.partnerValid and context.partner or nil
    local pro = selected and D.pro[selected]
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H, col = 1,
        text = selected and format(L["搭配专业：%s"], pro and pro.name or selected)
                        or L["请选择搭配的主专业"],
        icon = pro and pro.icon,
        sub = selected and skillText(selected) or L["未学专业开启联合升级时，请先选择另一个主专业。"],
        right = selected and L["点击更改"] or nil,
        act = function()
            if PD.partnerPicker == target then PD.partnerPicker = nil
            else PD.partnerPicker = target end
            PD.exclusionsOpen = false
            PD.FlushPolicies()
            PD.RequestRender()
        end,
    }
    if not selected or PD.partnerPicker == target then
        PushText(rows, L["仅使用目标专业和所选专业计算；选择后点击「重新计算」。"], 11, C_GREY)
        for _, slug in ipairs(E and E.PartnerCandidates and E.PartnerCandidates(target) or {}) do
            local candidate, partner = D.pro[slug], slug
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1,
                text = candidate and candidate.name or partner,
                icon = candidate and candidate.icon,
                sub = skillText(partner),
                right = selected == partner and L["已选择"] or L["选择"],
                act = function()
                    if E and E.SetRoutePartner then E.SetRoutePartner(target, partner) end
                    PD.partnerUIRevision = (PD.partnerUIRevision or 0) + 1
                    PD.partnerPicker = nil
                    PD.exclusionsOpen = false
                    PD.solverSig = nil
                    PD.autoSnapshot = nil
                    PD.FlushPolicies()
                    PD.RequestRender()
                end,
            }
        end
    end
    PushGap(rows, 4)
    spanRows()
end

function PD.PlanDiagnostics(add, plan)
    local groups, order, seen = {}, {}, {}
    local hasSteps = PD.PlanHasSteps(plan)
    local branchOnly = {excluded=true, notLearned=true, cooldown=true,
        cooldownUnknown=true, availabilityUnknown=true, clientUnavailable=true,
        professionMissing=true, skillRequired=true, materialUnavailable=true,
        formulaUnavailable=true, auctionSupplyLimited=true,
        levelGap=true, clientDataPending=true, outputConflict=true,
        characterLevelRequired=true, batchDependency=true, batchSkillGap=true}
    local function add(diagnostic, blocking)
        local key = type(diagnostic) == "table" and diagnostic.code or tostring(diagnostic)
        if not key then return end
        if hasSteps and not blocking and branchOnly[key] then return end
        if not hasSteps and plan.feasible and (key == "excluded"
           or key == "notLearned" or key == "cooldown" or key == "availabilityUnknown") then return end
        local identity = key
        if type(diagnostic) == "table" then
            for _, field in ipairs({"recipe", "spell", "item", "profession", "detail"}) do
                identity = identity .. ":" .. tostring(diagnostic[field] or "")
            end
        end
        if seen[identity] then return end
        seen[identity] = true
        local group = groups[key]
        if group then group.count = group.count + 1
        else groups[key] = {diagnostic = diagnostic, count = 1}; order[#order + 1] = key end
    end
    local blockers = plan.blockingDiagnostics or {}
    if hasSteps or #blockers == 0 then
        for _, diagnostic in ipairs(plan.diagnostics or {}) do add(diagnostic) end
    end
    for _, diagnostic in ipairs(blockers) do add(diagnostic, true) end
    local priority = {solverError=1, characterLevelRequired=2, professionMissing=3,
        vendorPriceUnknown=4, materialPriceUnknown=4, vendorEstimate=4, vendorQuoteChanged=4, materialUnavailable=5, levelGap=6, clientDataPending=7, outputConflict=8,
        excluded=8, notLearned=9}
    table.sort(order, function(a,b)
        local pa, pb = priority[a] or 20, priority[b] or 20
        return pa == pb and a < b or pa < pb
    end)
    local shown = 0
    for _, key in ipairs(order) do
        if shown >= 5 then break end
        local group = groups[key]
        local diagnostic = group.diagnostic
        local E = ns.ProfEconomy
        local message = E and E.DiagnosticText and E.DiagnosticText(diagnostic)
                     or (type(diagnostic) == "string" and diagnostic or (type(diagnostic) == "table" and diagnostic.message))
        if message then
            if group.count > 1 then message = format(L["%s（同类 %d 项）"], message, group.count) end
            if add then add(message, 0.95, 0.75, 0.4) end
            shown = shown + 1
        end
    end
    if #order > shown and add then
        add(format(L["另有 %d 类限制；调整设置后重新计算。"], #order - shown), 0.72, 0.72, 0.72)
    end
end

function PD.SolverText()
    local SR = ns.ProfSolverRun
    if not SR or not SR.Running() then return nil end
    local st = SR.State()
    if st.phase == "seed" then
        return format(L["正在推演 %d/%d"], st.seedSkill or 1, st.target or 300)
    elseif st.phase == "search" then
        local pct = 0
        if (st.cpuLimitMs or 0) > 0 then
            pct = math.floor((st.cpuUsed or 0) * 100 / st.cpuLimitMs + 0.5)
        end
        if pct > 100 then pct = 100 end
        return format(L["正在优化 %d%%"], pct)
    end
    return L["正在准备数据"]
end

function PD.WindowShown()
    local mf = _G.DungeonsForever_MainFrame
    return (mf and mf.IsShown and mf:IsShown()) and true or false
end

function PD.StopSolverRoute()
    local SR = ns.ProfSolverRun
    local aborting = (SR and SR.Running and SR.Running() and not PD.solverDone) and true or false
    if aborting then PD.autoExact = nil end
    if SR then SR.Stop() end
    PD.solverFrac = nil
    PD.solverSig = nil
    PD.solverRetry = nil
    PD.solverDone = false
    PD.solverPaintRes = nil
    PD.solverPaintKey = nil
end

function PD.StartSolverRoute(opts, key)
    local SR = ns.ProfSolverRun
    if not SR or not opts then return end
    if opts.cpuLimitMs == nil then opts.cpuLimitMs = 8000 end
    PD.solverSlug = PD.cur
    PD.solverKey = key
    PD.solverSig = key
    PD.solverDone = false
    PD.solverFrac = 0
    SR.Start(PD.cur, opts, {
        onProgress = function(j, st)
            PD.solverFrac = st and st.fraction or nil
            if not PD.WindowShown() then
                if not PD.__solverStopPend then
                    PD.__solverStopPend = true
                    C_Timer.After(0, function()
                        PD.__solverStopPend = nil
                        if not PD.WindowShown() then PD.StopSolverRoute() end
                    end)
                end
                return
            end
            if not (PD.built and PD.page and PD.page:IsShown()) then return end
            PD.PaintToolProgress(PD.SolverText(), PD.solverFrac)
            if j and j.result then
                local paintKey = tostring(j.result)
                if paintKey ~= PD.solverPaintKey then
                    PD.solverPaintKey = paintKey
                    PD.solverPaintRes = nil
                    if not PD.__solverPend then
                        PD.__solverPend = true
                        C_Timer.After(0.25, function()
                            PD.__solverPend = nil
                            if PD.built and PD.page and PD.page:IsShown() then PD.RequestRender() end
                        end)
                    end
                end
            end
        end,
        onDone = function(j)
            PD.solverDone = true
            PD.solverFrac = nil
            local res = j and (j.result or j.best) or nil
            local usable = res and res.planVersion == 2 and #(res.steps or {}) > 0
            local mine = PD.solverSlug == PD.cur
            if usable and mine then
                res.exact = true
                PD.autoSnapshot = res
                PD.autoSnapshotSlug = PD.cur
                PD.autoKey = PD.solverKey
                PD.autoExact = true
                if PD.exactFailed then PD.exactFailed[PD.solverKey or ""] = nil end
                PD.solverFallback = nil
            elseif mine then
                PD.exactFailed = PD.exactFailed or {}
                PD.exactFailed[PD.solverKey or ""] = true
                PD.autoExact = false
                if RA and RA.Get and PD.WindowShown() then
                    local r2 = RA.Get(PD.cur, opts)
                    if r2 then
                        PD.autoSnapshot = r2
                        PD.autoSnapshotSlug = PD.cur
                        PD.autoKey = PD.solverKey
                        PD.solverFallback = true
                    end
                end
            end
            if PD.built and PD.page and PD.page:IsShown() then PD.RequestRender() end
        end,
    })
end

function PD.BuildLvOpts(slug, current)
    local fish = PD.CookingFishingMode(slug)
    local pair = (not fish) and PD.RoutePairContext() or nil
    local lv = tonumber(current)
    return {
        start = (PD.Setting("autoFromCurrent") and lv) and math.max(1, lv) or 1,
        onlyAH = PD.Setting("autoOnlyAH"),
        learnedOnly = PD.Setting("autoLearnedOnly"),
        target = PD.LvTarget(),
        scheme = fish and "fishing" or PD.SettingRaw("autoScheme"),
        allowSecondaryLeveling = PD.Setting("autoSecondaryLeveling"),
        secondaryProfession = pair and pair.partner or nil,
        executionInventory = ns.ProfTrack and ns.ProfTrack.ContinueInventory
            and ns.ProfTrack.ContinueInventory(slug) or nil,
    }
end

function PD.PlanKeyOf(slug, opts)
    slug = slug or PD.cur
    if not (RA and RA.PlanSig) then return nil end
    return tostring(slug) .. "@" .. RA.PlanSig(slug, opts or {})
end

function PD.ClearPlanCache()
    PD.StopSolverRoute()
    PD.autoSnapshot, PD.autoSnapshotSlug = nil, nil
    PD.autoKey, PD.autoExact = nil, nil
    if PD.exactFailed then
        local n = 0
        for _ in pairs(PD.exactFailed) do n = n + 1 end
        if n > 8 then PD.exactFailed = {} end
    end
    PD.solverPaintRes, PD.solverFrac = nil, nil
end

function PD.RecalcNeeded()
    local slug = PD.cur
    if not slug or slug == "__index" or slug == "poisons" then return false end
    if PD.GATHER_SLUGS and PD.GATHER_SLUGS[slug] then return false end
    if PD.forceExact then return false end
    local SR = ns.ProfSolverRun
    if SR and SR.Running and SR.Running(PD.cur) then return false end
    if not PD.Setting("autoRoute") and not PD.Setting("solverRoute") and not PD.autoSnapshot then return false end
    local learned = PD.ProfLearned and PD.ProfLearned(true) or {}
    local key = PD.PlanKeyOf(slug, PD.BuildLvOpts(slug, learned[slug] and learned[slug].cur))
    if not key then return false end
    if PD.autoSnapshotSlug ~= slug or not PD.autoSnapshot then return true end
    if PD.autoKey and PD.autoKey ~= key then return true end
    return not PD.autoExact
end

local GLOW_PERIOD = 2.2
local GLOW_STEPS = 30
local GLOW_BORDER_MAX = 0.9
local GLOW_BG_LO = 0.52
local GLOW_BG_HI = 0.86

local function GlowCapPaint(bt, k)
    local cap = bt.__huiCap
    if not cap or not cap[1] then return end
    local layer = ns.hui and ns.hui.layer
    local base = (layer and layer.L2) or { 0x16 / 255, 0x1A / 255, 0x22 / 255 }
    local acc = (layer and layer.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
    local cr = base[1] + (acc[1] - base[1]) * k
    local cg = base[2] + (acc[2] - base[2]) * k
    local cb = base[3] + (acc[3] - base[3]) * k
    local tr = math.min(1, cr * 1.17)
    local tg = math.min(1, cg * 1.17)
    local tb = math.min(1, cb * 1.17)
    local br = math.min(1, cr * 0.86)
    local bg = math.min(1, cg * 0.86)
    local bb = math.min(1, cb * 0.86)
    local f = cap.__huiFrame
    local cs = cap.__huiCorner or 6
    local h = (f and f.GetHeight and f:GetHeight()) or 0
    local kk = (h > cs * 2) and (cs / h) or 0.25
    for i = 1, 7 do
        local tex = cap[i]
        if tex then
            local y0, y1
            if i == 3 or i == 4 or i == 6 then
                y0, y1 = 1 - kk, 1
            elseif i == 7 then
                y0, y1 = kk, 1 - kk
            else
                y0, y1 = 0, kk
            end
            local r0 = tr + (br - tr) * y0
            local g0 = tg + (bg - tg) * y0
            local b0 = tb + (bb - tb) * y0
            local r1 = tr + (br - tr) * y1
            local g1 = tg + (bg - tg) * y1
            local b1 = tb + (bb - tb) * y1
            tex:SetGradient("VERTICAL", CreateColor(r1, g1, b1), CreateColor(r0, g0, b0))
            tex:SetAlpha(1)
        end
    end
end

function PD.GlowBorder(bt, on)
    if not bt then return end
    local hui = ns.hui
    local acc = (hui and hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
    local dr = acc[1]
    local dg = acc[2]
    local db = acc[3]
    local function paint(mix)
        local r = dr + (1 - dr) * mix
        local g = dg + (1 - dg) * mix
        local b = db + (1 - db) * mix
        local ring = bt.__ring
        if ring then
            for i = 1, #ring do ring[i]:SetVertexColor(r, g, b) end
        end
        local cov = bt.__ringCover
        if cov then
            for i = 1, #cov do cov[i]:SetVertexColor(r, g, b) end
        end
    end
    local fs = bt:GetFontString()
    if fs then
        if on == false then
            fs:SetShadowOffset(0, 0)
            fs:SetShadowColor(0, 0, 0, 0)
        else
            fs:SetShadowOffset(1, -1)
            fs:SetShadowColor(0, 0, 0, 0.85)
        end
    end
    if on == false then
        bt.__glowOn = nil
        bt.__glowQ = nil
        if bt.__huiSelected then paint(0) end
        if bt.__huiCap and bt.__huiCap.__huiRepaint then bt.__huiCap.__huiRepaint() end
        return
    end
    bt.__glowOn = true
    bt.__glowQ = nil
    if bt.__glowHook then return end
    bt.__glowHook = true
    bt.__glowT = 0
    bt:HookScript("OnUpdate", function(self, el)
        if not self.__glowOn then return end
        local t = (self.__glowT or 0) + el
        if t > GLOW_PERIOD then t = t - GLOW_PERIOD end
        self.__glowT = t
        local p = 0.5 - 0.5 * math.cos(t * 2 * math.pi / GLOW_PERIOD)
        local q = math.floor(GLOW_STEPS * p + 0.5)
        if q == self.__glowQ then return end
        self.__glowQ = q
        local f = q / GLOW_STEPS
        paint(GLOW_BORDER_MAX * f)
        if not self.__huiHover and not self.__huiPress then
            GlowCapPaint(self, GLOW_BG_LO + (GLOW_BG_HI - GLOW_BG_LO) * f)
        end
    end)
end

function PD.LvRecalc()
    if not PD.cur or PD.cur == "__index" or PD.cur == "poisons" then return end
    if PD.GATHER_SLUGS and PD.GATHER_SLUGS[PD.cur] then return end
    PD.ClearPlanCache()
    if RA then
        if RA.Recalculate then
            local learned = PD.ProfLearned and PD.ProfLearned() or {}
            local lv = learned[PD.cur] and learned[PD.cur].cur
            RA.Recalculate(PD.cur, RA.OptionsFor and RA.OptionsFor(PD.cur, lv) or nil)
        elseif RA.Invalidate then
            RA.Invalidate()
        end
    end
    if PD.RequestRender then PD.RequestRender() end
end

function PD.UnpriceHours(age)
    local h = tonumber(age) or 0
    if h <= 0 then return 0 end
    return math.floor(h + 0.5)
end

function PD.UnpriceShort(entry)
    local code = entry and (entry.unpricedReason or entry.reason)
    local age = entry and (entry.unpricedAge or entry.age)
    local mats = entry and entry.unpricedMats
    if code == "stale" then
        return format(L["价格未知·超时%d小时"], PD.UnpriceHours(age))
    elseif code == "norec" then
        return L["价格未知·无扫描记录"]
    elseif code == "novendor" then
        return L["价格未知·无直售价"]
    elseif code == "noapi" then
        return L["价格未知·无价格源"]
    elseif mats and #mats > 0 then
        return format(L["价格未知·缺 %d 项"], #mats)
    end
    return L["价格未知"]
end

function PD.UnpriceMatsText(entry)
    local mats = entry and entry.unpricedMats
    if not mats or #mats == 0 then return nil end
    local sep = L["、"] or "、"
    local names, shown = {}, 0
    for i = 1, #mats do
        if shown >= 3 then break end
        local id = mats[i]
        local nm, ok = DG.ItemName(id)
        if not ok then
            if DG.RequestItem then DG.RequestItem(id) end
            nm = format(L["物品 %d"], id)
        end
        names[#names + 1] = nm
        shown = shown + 1
    end
    local text = table.concat(names, sep)
    if #mats > shown then text = text .. format(L[" 等 %d 项"], #mats) end
    return text
end

function PD.UnpriceWhy(entry, itemID)
    local matsText = PD.UnpriceMatsText(entry)
    if matsText then
        return format(L["价格未知：该步骤缺少 %s 的价格。"], matsText)
    end
    local code = entry and (entry.unpricedReason or entry.reason)
    local age = entry and (entry.unpricedAge or entry.age)
    local id = itemID or (entry and (entry.id or entry.unpricedMat))
    local who = (id and DG.ItemName(id)) or "?"
    local maxStale = (RA and RA.MaxStale) and RA.MaxStale() or 2
    if code == "stale" then
        return format(L["价格未知：%s 的拍卖行报价是 %d 小时前的数据，超过 %d 小时阈值，已按无价处理。"],
            tostring(who), PD.UnpriceHours(age), maxStale)
    elseif code == "norec" then
        return format(L["价格未知：%s 在拍卖行没有任何扫描记录，也没有商人直售价。"], tostring(who))
    elseif code == "novendor" then
        return format(L["价格未知：%s 为商人直售，但目前没有可靠的直售报价。"], tostring(who))
    elseif code == "noapi" then
        return L["价格未知：没有可用的拍卖行价格数据源，无法取价。"]
    end
    return L["价格未知：该步骤有材料无法取价。"]
end

function PD.UnpriceWhyShort(entry)
    local code = entry and (entry.unpricedReason or entry.reason)
    local age = entry and (entry.unpricedAge or entry.age)
    if code == "stale" then
        return format(L["超时 %d 小时"], PD.UnpriceHours(age))
    elseif code == "norec" then
        return L["拍卖行无记录"]
    elseif code == "novendor" then
        return L["无商人直售价"]
    elseif code == "noapi" then
        return L["无价格数据源"]
    elseif entry and entry.unpricedMats and #entry.unpricedMats > 0 then
        return format(L["价格未知·缺 %d 项"], #entry.unpricedMats)
    end
    return nil
end

local function TrackRunOf(slug)
    local T = ns.ProfTrack
    if not T then return nil end
    local run = T.GetRun(slug)
    if run and run.status == "active" then return run end
    return nil
end

local function TrackStepsFor(slug, steps)
    local T = ns.ProfTrack
    if not T then return nil end
    local run = TrackRunOf(slug)
    if not run then return nil end
    local mine = run.steps
    if type(mine) ~= "table" or type(steps) ~= "table" or #steps == 0 or #mine == 0 then return nil end
    if #mine == #steps then
        local same = true
        for i = 1, #steps do
            if steps[i][3] ~= mine[i].spell then same = false break end
        end
        if same then return run, T.ProgressAll(slug) end
    end
    if not (T.Rebase and T.Rebase(run, steps)) then return nil end
    return run, T.ProgressAll(slug)
end

function PD.RowsCraftLog(rows)
    local T = ns.ProfTrack
    PushHead(rows, L["制作记录"])
    PushGap(rows, 4)
    if not T or not T.Summary then
        PushText(rows, L["未启用制作追踪。"], 14, C_GREY)
        return
    end
    local sum = T.Summary(PD.cur)
    if not sum then
        PushText(rows, L["本角色还没有任何制作记录。"], 14, C_TEXT)
        PushGap(rows, 4)
        PushText(rows, L["在「路线」页点「开始追踪」后，这里会记录每一步实际做了几次、产出多少。"], 14, C_GREY)
        return
    end
    local stText, stColor
    if sum.stale then
        if sum.staleReason == "specialization" then
            stText, stColor = L["专精计划已变化，需重新开始追踪"], { 0.95, 0.55, 0.45 }
        else
            stText, stColor = L["技能值变动，需重新开始追踪"], { 0.95, 0.55, 0.45 }
        end
    elseif sum.finished or sum.status == "done" then
        stText, stColor = L["已完成"], { 0.49, 0.82, 0.63 }
    else
        stText, stColor = L["追踪中"], C_GOLD
    end
    local total = sum.total or 0
    local idx = math.min(sum.current or 1, total)
    PushText(rows, format(L["%s · 第 %d/%d 步 · 技能 %s→%s"], stText, idx, total,
                          tostring(sum.startSkill or "—"), tostring(sum.target or "—")), 14, stColor)
    PushText(rows, format(L["已做 %d 次 · 计划 %d 次"], sum.casts or 0, sum.planned or 0), 14, C_TEXT)
    PushGap(rows, 8)
    local list = T.RecipeTotals(PD.cur)
    if #list == 0 then
        PushText(rows, L["还没有可统计的制作。"], 14, C_GREY)
    else
        PushHead(rows, L["按配方汇总"], 1)
        for _, e in ipairs(list) do
            local name = PD.StepName({ 0, 0, e.spell })
            if (type(name) ~= "string" or name == "") and e.item then name = PD.ItemName(e.item) end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1,
                it = e.item and { e.item } or nil,
                text = name or tostring(e.spell or ""),
                right = format(L["%d 次"], e.casts),
                right2 = format(L["%d 件"], e.out),
                noTip = true,
            }
        end
    end
    local hist = T.History(PD.cur)
    local past = {}
    for _, run in ipairs(hist) do
        if run.status ~= "active" then past[#past + 1] = run end
        if #past >= 5 then break end
    end
    if #past > 0 then
        PushGap(rows, 8)
        PushHead(rows, L["历史记录"], 1)
        for _, run in ipairs(past) do
            local n = 0
            for _ in ipairs(run.steps or {}) do n = n + 1 end
            local tag = run.status == "done" and L["已完成"]
                        or (run.status == "stale" and L["技能值变动"] or L["已归档"])
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1, noTip = true,
                text = format(L["%d 步 · 技能 %s→%s"], n, tostring(run.startSkill or "—"),
                              tostring(run.target or "—")),
                right = tag,
                rightColor = C_GREY,
            }
        end
    end
end

function PD.RowsLeveling(rows)
    if PD.autoPage == "log" then
        PD.lvSummary, PD.lvRouteHead = nil, nil
        PD.RowsCraftLog(rows)
        return
    end
    local lv = LV[PD.cur]
    if not lv then PD.lvSummary = nil; PD.lvRouteHead = nil; PD.warnNotes = nil return end
    PD.lvRouteHead = nil
    local notes = {}
    local function note(text, r, g, b)
        if text and text ~= "" then
            notes[#notes + 1] = { text, r or 0.72, g or 0.72, b or 0.72 }
        end
    end
    PD.warnNotes = notes

    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil
    local greyOn = PD.Setting("greyPassed")

    local fishRoute = PD.CookingFishingMode and PD.CookingFishingMode() or false
    local scheme = fishRoute and "fishing" or PD.SettingRaw("autoScheme")
    local pairContext = (not fishRoute) and PD.RoutePairContext() or nil
    local needPartner = (pairContext and pairContext.requiresPartner) and true or false
    local smeltRoute = (PD.cur == "mining") and PD.GatherMode("mining") == "smelt"
    local autoOn = (not smeltRoute) and (needPartner or (PD.WindowShown() and (PD.cur ~= "poisons") and (fishRoute or PD.Setting("autoRoute") or PD.Setting("solverRoute")) and RA
                    and (fishRoute or scheme == "cheapest" or scheme == "optim" or RA.Available()) and true or false))
    local target = PD.LvTarget()
    if fishRoute then
        note(L["鱼类自行钓取；其他材料只使用不限量商人货物。"])
        note(L["鱼类不计金币成本；图纸仍按实际采购来源计费。"])
        note(L["鱼类为待钓数量；未达区域门槛时，先提升钓鱼技能或使用加成。"])
        note(L["钓鱼区域和概率为经典服指南参考；Forever 客户端能读取的配方字段优先。"])
        if target > 225 then note(L["225 以上须先解锁大师级烹饪；蚌肉大餐任务另需非鱼材料，不属于本路线的制作材料。"]) end
    end
    local res
    local planKey
    PD.lvOpts = nil
    if autoOn then
        local opts = PD.BuildLvOpts(PD.cur, curLv)
        opts.target = target
        PD.lvOpts = opts
        planKey = PD.PlanKeyOf(PD.cur, opts)
        local SR = ns.ProfSolverRun
        local wantExact = (PD.Setting("solverRoute") or needPartner or PD.forceExact) and true or false
        PD.forceExact = nil
        if SR and not fishRoute and wantExact then
            local running = SR.Running and SR.Running(PD.cur) or false
            if running and PD.solverSig ~= planKey then
                PD.StopSolverRoute()
                running = false
            end
            local exactOk = PD.autoExact and PD.autoSnapshot and planKey and PD.autoKey == planKey
            if running then
                res = SR.Result()
                if res then res.exact = true end
            elseif exactOk then
                res = PD.autoSnapshot
            elseif (not PD.autoSnapshot or PD.autoSnapshotSlug ~= PD.cur)
                   and not (PD.exactFailed and PD.exactFailed[planKey]) then
                PD.StartSolverRoute(opts, planKey)
                res = SR.Result()
                if res then res.exact = true end
            else
                res = RA.Get(PD.cur, opts)
            end
        elseif not needPartner then
            if PD.autoExact and PD.autoSnapshotSlug == PD.cur and planKey and PD.autoKey == planKey then
                res = PD.autoSnapshot
            else
                res = RA.Get(PD.cur, opts)
            end
        end
        if res and res.planVersion ~= 2 and not res.priced and scheme ~= "optim" then res = nil end
    end
    local auto = (autoOn and res) and true or false
    if res then
        PD.autoSnapshot, PD.autoSnapshotSlug = res, PD.cur
        PD.autoKey = planKey
        PD.autoExact = res.exact == true
    end
    PD.RowsRoutePartner(rows, pairContext)
    PD.RowsSpecQuest(rows)
    if pairContext and pairContext.requiresPartner and not pairContext.partnerValid then
        PD.lvSummary = {target = target, auto = true, autoSetting = true, scheme = scheme, ahOK = true}
        PD.CopyPlanSummary(res)
        return
    end
    if res and (res.status == "selection_required" or res.status == "recalculate_required") then
        PD.lvSummary = {target = target, auto = true, autoSetting = true, scheme = scheme, ahOK = true}
        PD.CopyPlanSummary(res)
        PushText(rows, PD.PlanStatusText(res), 12, {0.95, 0.75, 0.4})
        return
    end
    if PD.exclusionsOpen and autoOn then
        PD.lvSummary = {target = target, auto = autoOn, autoSetting = fishRoute or PD.Setting("autoRoute"), total = res and res.total,
                        scheme = auto and res.scheme or nil,
                        priced = auto or false,
                        snapshotAge = auto and res.snapshotAge or nil,
                        snapshotDays = auto and res.snapshotDays or nil,
                        np = auto and CountUnpriced(res) or 0}
        PD.CopyPlanSummary(res)
        PD.RowsExclusions(rows)
        return
    end
    if autoOn and (scheme == "cheapest" or fishRoute) and not PD.PlanHasSteps(res) then
        PD.lvSummary = {target = target, auto = true, autoSetting = true, scheme = scheme, ahOK = true,
                        total = res and res.total, priced = res and res.total ~= nil}
        PD.CopyPlanSummary(res)
        PushHead(rows, res and PD.PlanStatusText(res) or L["正在计算升级路线…"])
        local progress = PD.PlanProgressText(res)
        if progress then PushText(rows, progress, 11, C_GREY) end
        PD.lvRouteHead = { progress = L["正在快速计算适合路线"] }
        if res then PD.PlanDiagnostics(note, res) end
        return
    end

    if PD.autoPage == "shop" then
        local data = auto and res or FixedShopData(target)
        PD.lvSummary = {
            target = target, auto = auto,
            scheme = auto and res.scheme or nil,
            autoSetting = fishRoute or PD.Setting("autoRoute"),
            ahOK = fishRoute or ((RA and RA.Available()) and true or false),
            priced = (data.priced and true) or false,
            total = data.total, snapshotAge = data.snapshotAge,
            snapshotDays = data.snapshotDays,
            matsN = #(data.mats or {}), np = CountUnpriced(data),
        }
        PD.CopyPlanSummary(res)
        PD.lvShopData = data
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
    local recRaw = { [PD.cur] = recOf }
    local function RawRow(slug, spell)
        local m = recRaw[slug]
        if not m then
            m = {}
            local d = RGet(slug)
            for _, r in ipairs(d and d.rows or {}) do m[r[1]] = r end
            recRaw[slug] = m
        end
        local r = m[spell]
        if r and (r.mats or r.learn) then return nil end
        return r
    end

    local steps, clipped
    if auto then
        steps = res.steps
    else
        steps, clipped = ClipFixedSteps(lv.steps or {}, target)
    end
    local fixedSum = (not auto) and RA and RA.SummarizeSteps(steps, PD.cur,
                          { learnedOnly = PD.Setting("autoLearnedOnly"), target = target }) or nil
    local trackRun, trackAll = TrackStepsFor(PD.cur, steps)

    PD.lvSummary = {
        target = target, auto = auto,
        scheme = auto and res.scheme or nil,
        autoSetting = fishRoute or PD.Setting("autoRoute"),
        ahOK = fishRoute or ((RA and RA.Available()) and true or false),
        priced = auto or ((fixedSum and fixedSum.priced) and true or false),
        total = auto and res.total or (fixedSum and fixedSum.total),
        snapshotAge = auto and res.snapshotAge or (fixedSum and fixedSum.snapshotAge),
        snapshotDays = auto and res.snapshotDays or (fixedSum and fixedSum.snapshotDays),
        recipes = auto and #res.steps or nil,
        crafts = auto and (res.crafts or 0) or nil,
        vendorTotal = auto and res.vendorTotal or (fixedSum and fixedSum.vendorTotal),
        referencePrices = auto and res.referencePrices or (fixedSum and fixedSum.referencePrices),
        matsN = (not auto) and fixedSum and #(fixedSum.mats or {}) or nil,
        np = auto and CountUnpriced(res) or (fixedSum and CountUnpriced(fixedSum)) or 0,
    }
    PD.CopyRecoverySummary(auto and res or fixedSum)
    if PD.autoPage == "recovery" then
        PD.RowsRecoveryDetail(rows, auto and res or fixedSum)
        return
    end
    PD.CopyPlanSummary(res)
    local shownSum = auto and res or fixedSum
    if shownSum and (shownSum.specBlocked or 0) > 0 and not (shownSum.blockedSteps and #shownSum.blockedSteps > 0) then
        note(format(L["已按本角色专精过滤 %d 个无法学习的配方"], shownSum.specBlocked), 0.72, 0.72, 0.72)
    end
    if shownSum and shownSum.blockedSteps and #shownSum.blockedSteps > 0 then
        local names, seen = {}, {}
        for _, b in ipairs(shownSum.blockedSteps) do
            local label = tostring(b.reason or "")
            if label ~= "" and not seen[label] then
                seen[label] = true
                names[#names + 1] = label
            end
        end
        if #names > 0 then
            local ranges = {}
            for i, b in ipairs(shownSum.blockedSteps) do
                if i > 3 then break end
                ranges[#ranges + 1] = format("%d–%d", b.from or 0, b.to or 0)
            end
            note(format(L["有 %d 个步骤受专精限制（%s）：%s"], #shownSum.blockedSteps,
                table.concat(names, " / "), table.concat(ranges, "、")), 0.95, 0.75, 0.4)
        end
    end
    do
        local G = ns.ProfGates
        local goal = G and G.SpecGoal(PD.cur, target)
        if goal and not PD.SpecQuestGoal(PD.cur) then
            note(format(L["工程学 200 级起需先完成地精/侏儒专精任务：%s（%s）"],
                tostring(goal.questName or ""), tostring(goal.zone or "")), 0.95, 0.75, 0.4)
        end
    end
    local cntOf, costOf, cardOf, whyOf, whyLong, chipOf, roleChipOf = {}, {}, {}, {}, {}, {}, {}
    local rngW = PD.TextW(L["等级范围"], PD.LV_FS)
    local cntW = PD.TextW(L["制作次数"], PD.LV_FS)
    local costW = PD.TextW(L["成本"], PD.LV_FS)
    local stepW = PD.TextW(L["步骤"], PD.LV_FS)
    local cardNeed = 0
    for index, st in ipairs(steps or {}) do
        local rec = PD.StepRecipe(st) or recOf[st[3]]
        if not rec and rin then rec = rin[st[3]] end
        local riM
        if rec and (rec.mats or rec.learn) then riM = rec; rec = nil end
        local yellow = (rec and tonumber(rec[8])) or (riM and tonumber(riM.yellow))
        local certain = yellow and st[2] <= yellow
        local count = certain and format(L["%d 次制作"], st[4] or 0)
                              or format(L["~%s 次制作"], tostring(st[4] or 0))
        local cost = ""
        if auto or fixedSum then
            if st.unpriced or st.cost == nil then
                cost = L["价格未知"]
                whyOf[st] = PD.UnpriceWhyShort(st)
                whyLong[st] = PD.UnpriceWhy(st)
            else
                cost = (st.est and "≈" or "") .. RA.MoneyStr(st.cost)
            end
        end
        if clipped and st._clip then count = count .. format(L[" · 按目标 %d 折算"], target) end
        if st.checkpoint or st[3] == 0 then count, cost = L["实地采矿"], "" end
        local tp = trackAll and trackAll.steps[index]
        if tp and tp.casts > 0 and not (st.checkpoint or st[3] == 0) then
            count = format("%d/%d", tp.casts, st[4] or 0)
        end
        cntOf[st], costOf[st] = count, cost
        rngW = math.max(rngW, PD.TextW(PD.StepRange(st), PD.LV_FS))
        cntW = math.max(cntW, PD.TextW(count, PD.LV_FS))
        costW = math.max(costW, PD.TextW(cost, PD.LV_FS))
        stepW = math.max(stepW, PD.TextW(tostring(st.stepIndex or st.index or index), PD.LV_FS))
        local cd = PD.CardOf(RawRow(st.profession or PD.cur, st[3]) or rec,
                             riM or (rin and rin[st[3]] or nil))
        if cd then
            local lines = {}
            for k = 1, #cd.lines do lines[k] = cd.lines[k] end
            cd = { kind = cd.kind, text = cd.text, fid = cd.fid, lines = lines, act = cd.act }
        end
        cardOf[st] = cd
        if cd then
            cardNeed = math.max(cardNeed, PD.TextW(cd.text, 10) + 2 * PD.CARD_PAD)
        end
        if PD.StepIsMaterial(st) then
            roleChipOf[st] = { text = L["中间产物"], bg = DG.Q_BADGE_MID_BG }
            if cd then
                cd.lines[#cd.lines + 1] = { PD.StepRole(st), 0.62, 0.80, 0.95 }
            end
        end
        if st.tool and st.toolItem then
            local owned = PD.ToolOwned(st.toolItem)
            chipOf[st] = owned and { text = L["已拥有"], bg = DG.Q_BADGE_SHARE_BG }
                or st.toolBop and { text = L["BoP 制作"], bg = DG.Q_BADGE_PRE_BG }
                or { text = L["可购买"], bg = DG.Q_BADGE_BUY_BG }
            if cd then
                cd.lines[#cd.lines + 1] = {
                    owned and L["工具：已在背包或银行中，无需再次制作。"]
                    or st.toolBop and L["工具：拾取绑定，无法购买，须自行制作。"]
                    or L["工具：可购买或制作，制成后保留使用，不会消耗。"],
                    0.58, 0.86, 1 }
            end
        end
        local output = PD.RecipeOutputText(riM or rec)
        if output and cd then cd.lines[#cd.lines + 1] = {output, 0.65, 0.75, 0.85} end
        if cd and (st.checkpoint or st[3] == 0) then
            cd.lines[#cd.lines+1] = {L["达到目标技能后重新计算"]}
        end
    end
    local rowW = PD.RIGHT_W - 2 * PD.LIST_PAD
    PD.LV_ROW_W = rowW
    PD.LV_STEP_W = math.ceil(stepW)
    PD.LV_RNG_X = PD.LV_STEP_X + PD.LV_STEP_W + PD.LV_COL_GAP
    PD.LV_CARD_FIXW = math.ceil(math.max(cardNeed, PD.CardFixW()))
    PD.LV_ICON_X = PD.LV_RNG_X + math.ceil(math.max(rngW, PD.LV_CARD_FIXW)) + PD.TBL_RNG_GAP
    PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP
    PD.LV_CNT_W, PD.LV_COST_W = math.ceil(cntW), math.ceil(costW)
    PD.LV_COST_R = PD.TBL_MAT_RPAD
    PD.LV_COUNT_R = PD.LV_COST_R + PD.LV_COST_W + PD.LV_COL_GAP
    local nameEnd = rowW - PD.LV_COUNT_R - PD.LV_CNT_W - PD.LV_COL_GAP
    local matFloor = PD.TBL_ICON + PD.TBL_MARK_W + PD.TBL_BLK_GAP
    local cap = math.max(PD.TBL_NAME_MIN, nameEnd - PD.LV_NAME_X - PD.TBL_NAME_GAP - matFloor)
    PD.LV_NAME_W = math.min(PD.LV_NAME_FIXW, cap)
    PD.LV_MAT_X = PD.LV_NAME_X + PD.LV_NAME_W + PD.TBL_NAME_GAP
    PD.LV_MAT_W = math.max(0, nameEnd - PD.LV_MAT_X)
    PD.LV_MAT_RIGHT = nameEnd

    local function FitName(s)
        return PD.Fit(s, PD.LV_FS, PD.LV_NAME_W)
    end
    local function FitR(s) return PD.Fit(s, 13, PD.COL_RW - 66) end

    if autoOn and not auto then
        PushHead(rows, L["自动路线不可用"])
        rows[#rows].suffix = PD.AuctionatorStatusText()
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
            for _, w in ipairs(warn) do
                note(w[1], w[2], w[3], w[4])
            end
            local progress
            if res.planVersion == 2 then
                if res.status == "searching" or res.status == "incomplete" then
                    progress = PD.PlanProgressText(res) or L["正在快速计算适合路线"]
                elseif (res.status == "complete" or res.optimal) and res.expanded then
                    progress = format(L["优化结束：已比较 %d 种组合"], res.expanded)
                end
            end
            PD.lvRouteHead = { progress = progress }
            PushGap(rows, 4)
        else
            local warn = {}
            if PD.cur == "mining" then
                note(L["固定路线的制作次数来自参考指南；材料和产量优先读取客户端，缺失时使用参考资料。"])
            end
            if fixedSum and not fixedSum.priced then
                warn[#warn + 1] = { PD.AuctionatorStatusText(), 0.7, 0.7, 0.7 }
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
            for _, w in ipairs(warn) do note(w[1], w[2], w[3], w[4]) end
            rows[#rows + 1] = { kind = "head", text = format(L["1 → %d 分段路线"], target) }
            PushGap(rows, 4)
        end
        rows[#rows + 1] = { kind = "lvhead", h = 18, col = 1, noTip = true }
        for index, st in ipairs(steps) do
            local rec = PD.StepRecipe(st) or recOf[st[3]]
            local ri = nil
            if rec and (rec.mats or rec.learn) then
                ri = rec
                rec = nil
            elseif not rec then
                ri = rin and rin[st[3]] or nil
            end
            local mats = (rec and rec[12]) or (ri and ri.mats) or {}
            local blocks, _, cut = PD.PackMats(mats, PD.LV_MAT_W)
            local nm = PD.StepName(st)
            local src = PD.LevelSrc(rec)
            if not rec and ri then
                src = ri.trainer and L["向训练师学习"] or nil
            end
            if st.profession and st.profession ~= PD.cur then
                local pro = D.pro[st.profession]
                src = (pro and pro.name or st.profession) .. " · " .. (st.reason == "secondary" and L["联合升级"] or L["制作材料"])
            elseif st.reason == "material" then src = L["制作材料"] end
            if st.checkpoint or st[3] == 0 then src = L["不预先计入尚未采到的矿石"] end
            if (rec and rec.clientPending) or (ri and ri.clientPending) then src = L["客户端数据待读取"] end
            local segLo = tonumber(st[1])
            local segHi = tonumber(st[2])
            local stepLv = _learned and _learned[st.profession or PD.cur]
            local actualLv = stepLv and stepLv.cur or curLv
            local over = (actualLv ~= nil and segHi ~= nil and segHi < actualLv) or nil
            local passed = (greyOn and over) or nil
            rows[#rows + 1] = {
                kind = "row", h = PD.TBL_H, col = 1, lvstep = true,
                passed = passed, over = over,
                trackCur = (trackAll and trackAll.current == index) and true or nil,
                it = (rec and rec[2]) and { rec[2] }
                     or ((ri and ri.makes) and { ri.makes } or nil),
                icon = ((not rec) and ri and not ri.makes) and SpellIcon(st[3]) or nil,
                tipExtra = (rec and rec[2])
                           and function() return PD.PriceTipLines(rec[2], rec[12]) end
                           or ((ri and ri.makes and ri.mats)
                               and function() return PD.PriceTipLines(ri.makes, ri.mats) end
                               or nil),
                noTip = true,
                stepIndex = st.stepIndex or st.index or index,
                rng = PD.StepRange(st),
                text = FitName(nm),
                src = src,
                cnt = cntOf[st] or format(L["~%s 次制作"], tostring(st[4])),
                cost = costOf[st] or "",
                costWhy = whyLong[st],
                costWhyShort = whyOf[st],
                role = PD.StepRole(st),
                toolChip = chipOf[st],
                roleChip = roleChipOf[st],
                _mats = mats,
                blocks = blocks, matCut = cut,
                sbVals = (rec and (rec[7] or rec[8] or rec[9] or rec[10]))
                         and { rec[7], rec[8], rec[9], rec[10] }
                         or (ri and (ri.yellow or ri.grey))
                            and { ri.learn, ri.yellow, ri.green, ri.grey } or nil,
                sbLo = segLo, sbHi = segHi,
                card = cardOf[st],
                act = auto and st[3] ~= 0 and function(_, button)
                    local profession = st.profession or PD.cur
                    if button == "RightButton" then PD.ChangeRecipePolicy(profession, st[3], true)
                    else PD.exclusionsOpen = true; PD.RequestRender() end
                end or nil,
            }
            local recText = PD.StepRecoveryText(st)
            local costLines = PD.StepCostLines(st)
            if recText or costLines then
                local baseTip = rows[#rows].tipExtra
                rows[#rows].tipExtra = function()
                    local lines = {}
                    if baseTip then
                        local extra = baseTip()
                        for _, line in ipairs(extra or {}) do lines[#lines + 1] = line end
                    end
                    if recText then lines[#lines + 1] = { recText, 0.55, 0.85, 0.6 } end
                    for _, line in ipairs(costLines or {}) do lines[#lines + 1] = line end
                    return lines
                end
            end
            if fishRoute then
                PD.RowsFishAreas(rows, st.fishing or st.fishMaterials, st.fishingAreas, 1)
            end
        end
    end
    if trackAll then
        for _, spec in ipairs(rows) do
            if spec.trackCur then spec.cur = true; break end
        end
    elseif PD.Setting("hlCurrent") and curLv ~= nil then
        for _, spec in ipairs(rows) do
            if spec.lvstep and spec.over == nil then
                spec.cur = true
                break
            end
        end
    end
    if res and res.planVersion == 2 then PD.PlanDiagnostics(note, res) end
end

function PD.FormulaStockText(entry)
    if entry.unlimited and entry.limited then return L["商人库存：固定售卖及限量刷新"] end
    if entry.unlimited then return L["商人库存：固定售卖（不限量）"] end
    if entry.limited then return L["商人库存：限量刷新"] end
    if entry.stockUnknown or #(entry.vendorOffers or {}) > 0
       or (entry.sources and #(entry.sources.vendors or {}) > 0) then
        return L["商人库存：性质尚未核实"]
    end
end

function PD.ToolOwned(itemID)
    local G = ns.ProfGates
    return (G and G.ToolOwned and G.ToolOwned(itemID)) or false
end

function PD.FormulaStockChip(entry)
    if entry.unlimited and entry.limited then
        return { text = L["不限量+限量"], color = { 0.98, 0.82, 0.45 } }
    end
    if entry.unlimited then
        return { text = L["不限量"], color = { 0.55, 0.90, 0.62 } }
    end
    if entry.limited then
        return { text = L["限量刷新"], color = { 0.98, 0.82, 0.45 } }
    end
    if entry.stockUnknown or #(entry.vendorOffers or {}) > 0
       or (entry.sources and #(entry.sources.vendors or {}) > 0) then
        return { text = L["库存未知"], color = { 0.68, 0.72, 0.78 } }
    end
end

function PD.RowsFormulaShop(rows, data, foldKey)
    local formulas = data.formulas or {}
    PushHead(rows, format(L["图纸（%d 种）"], #formulas), 1)
    if foldKey then
        rows[#rows].foldKey = foldKey
        if PD.FoldOn(foldKey) then return end
    end
    if #formulas == 0 then
        PushText(rows, L["没有需要购买的图纸。"], 11, C_GREY, 1)
        return
    end
    local function money(value)
        return type(value) == "number" and RA.MoneyStr(value, "copper") or L["价格未知"]
    end
    local function sourceRow(text, lines, act)
        rows[#rows + 1] = {kind = "row", h = PD.ROW_H1, col = 1, fs = 11,
            text = text, lines = lines, act = act}
    end
    for _, entry in ipairs(formulas) do
        local id, count = entry.id, entry.count or 1
        if entry.recipe and ns.ProfSourceMerge then ns.ProfSourceMerge.Fill(entry.recipe) end
        local src = entry.sources or (entry.recipe and entry.recipe.source) or {}
        local drops = src.drops or {}
        local dropEnts = PD.DropEntries(src)
        local hasLoc = #dropEnts > 0
        local chipText = src.skill and format(L["技能 %s"], tostring(src.skill)) or nil
        local links = {}
        if #drops > 0 then
            local stext = format(L["掉落 %d 处"], #drops)
            if not hasLoc then stext = stext .. " · " .. L["暂无坐标"] end
            links[#links + 1] = {
                text = stext,
                lines = PD.DropLines(src),
                color = hasLoc and { 0.98, 0.82, 0.35 } or { 0.62, 0.62, 0.62 },
                act = hasLoc and PD.DropAct(src) or function() end,
            }
        else
            links[#links + 1] = { text = L["掉落未知"], color = { 0.62, 0.62, 0.62 },
                                  act = function() end }
        end
        local vendors = PD.VendorListOf(src)
        if #vendors > 0 then
            local vEnts = PD.VendorEntries(src)
            local vtext = format(L["商人 %d 处"], #vendors)
            if #vEnts == 0 then vtext = vtext .. " · " .. L["暂无坐标"] end
            links[#links + 1] = {
                text = vtext,
                lines = PD.VendorLines(src, entry.id),
                color = (#vEnts > 0) and { 0.58, 0.86, 1 } or { 0.62, 0.62, 0.62 },
                act = (#vEnts > 0) and PD.VendorAct(src) or function() end,
            }
        end
        local stockChip = PD.FormulaStockChip(entry)
        local stockInline = stockChip ~= nil and #vendors > 0
        if stockInline then
            links[#links + 1] = { text = stockChip.text, chip = true, color = stockChip.color }
        end
        local priceLine = format(L["拍卖行：%s · NPC：%s"], money(entry.ahPrice), money(entry.vendorPrice))
        local stock = PD.FormulaStockText(entry)
        local lines = {{priceLine}, {format(L["需要：%d"], count)}}
        for _, line in ipairs(PD.AuctionSupplyLines(entry)) do lines[#lines + 1] = line end
        if stock then lines[#lines + 1] = {stock, 0.95, 0.75, 0.4} end
        if entry.limited then lines[#lines + 1] = {L["限量商人报价仅作参考，不能保证到访时有货。"], 0.95, 0.75, 0.4} end
        if entry.blocked or entry.usable == false then
            if entry.reason == "formulaLimited" then
                lines[#lines + 1] = {L["此图纸只有限量或库存未核实的商人货源，且拍卖行没有报价；未计入采购。可在设置开启「允许采购限量图样」。"], 1, 0.5, 0.4}
            elseif entry.reason == "formulaUnknownSource" then
                lines[#lines + 1] = {L["此图纸没有可核实的购买报价（无拍卖行报价、无商人售价信息）；已按「不使用未知来源的图纸」设置排除。"], 1, 0.5, 0.4}
            else
                lines[#lines + 1] = {L["此图纸尚未取得且没有可靠购买来源；固定路线仅供参考。"], 1, 0.5, 0.4}
            end
        end
        for _, offer in ipairs(entry.vendorOffers or {}) do
            local quantity = offer.quantity or offer.bundleSize or 1
            local unit = offer.unit or (type(offer.price) == "number" and offer.price / quantity)
            local name = offer.name or offer.npcName
            if not name then
                for _, vendor in ipairs(PD.VendorListOf(src)) do
                    if vendor.id == offer.npcID then name = vendor.name; break end
                end
            end
            name = name or (offer.npcID and format(L["商人 NPC #%d"], offer.npcID)) or L["商人"]
            local limited=offer.limited or offer.unlimited==false or offer.stockStatus=="limited"
                or type(offer.stock)=="number" and offer.stock>=0
            local stockText = offer.unlimited and L["固定售卖（不限量）"]
                or (limited and L["限量刷新"] or L["库存性质尚未核实"])
            local priceText = ((offer.currencyID or 0) > 0) and PD.FormulaCostText(offer) or money(unit)
            lines[#lines + 1] = {format(L["%s：%s · %s"], name, priceText, stockText), 0.7, 0.7, 0.7}
        end
        local selected = entry.source or entry.sourceType
        local tag = selected == "vendor" and L["NPC购买"]
            or ((selected == "ah" or selected == "auction") and L["拍卖行"] or L["尚无购买来源"])
        local priced = not (entry.unpriced or type(entry.cost) ~= "number")
        rows[#rows + 1] = {kind = "row", h = PD.ROW_H, col = 1, it = id and {id} or nil,
            text = PD.Fit(id and DG.ItemName(id) or L["未知图纸"], 13, (PD.splitLW or PD.COL_LW) - 130),
            chip = chipText and {text = chipText} or nil,
            links = links,
            tag = {text = tag}, right = format("×%d", count),
            right2 = priced and money(entry.cost) or priceLine,
            lines = lines, tipExtra = function() return lines end}
        if stock and not stockInline then PushText(rows, stock, 11, C_GREY, 1) end
        if entry.limited then PushText(rows, L["限量商人报价仅作参考，不能保证到访时有货。"], 11, C_GREY, 1) end
        local parts = PD.SourceParts(src)
        for _, part in ipairs(parts) do
            if not part.vendor and part.kind ~= "skill" and part.kind ~= "drop" then
                sourceRow(part.text, {{part.text}})
            end
        end
        if entry.questOnly then sourceRow(L["仅任务来源"], {{L["仅任务来源"]}}) end
        for _,quest in ipairs(src.quests or {}) do
            local title=quest.name or (quest.id and ("#"..quest.id)) or L["任务"]
            local drop={drops={{id=quest.npcID,npc=quest.npc or title,zone=quest.zone}}}
            local entries=PD.DropEntries(drop)
            local act=quest.loc and function() PD.MarkVendorLoc(quest.loc) end
                or (#entries>0 and PD.DropAct(drop) or nil)
            sourceRow(format(L["任务：%s"],title).." · "..(act and L["点击定位"] or L["暂无坐标"]),
                {{title}},act)
        end
        if entry.blocked or entry.usable == false then
            PushText(rows, L["此图纸尚未取得且没有可靠购买来源；固定路线仅供参考。"], 11, {1, 0.5, 0.4}, 1)
        end
    end
end

local function TripFaction()
    if type(UnitFactionGroup) ~= "function" then return nil end
    local ok, eng = pcall(UnitFactionGroup, "player")
    if not ok then return nil end
    if eng == "Alliance" then return "A" end
    if eng == "Horde" then return "H" end
    return nil
end

local function TripBestOffer(id, mine)
    local src = ns.ProfVendorOffers
    if type(src) ~= "table" or not id then return nil end
    local list = src[id]
    if type(list) ~= "table" then return nil end
    local best
    for i = 1, #list do
        local o = list[i]
        local side = o.faction
        if side == nil or side == "N" or mine == nil or side == mine then
            local q = o.quantity or 1
            local unit = (o.price or 0) / q
            if not best or unit < best.unit then
                best = { npcID = o.npcID, unit = unit, quantity = q }
            end
        end
    end
    return best
end

function PD.TripGroups(data)
    local mine = TripFaction()
    local seen, order, ah = {}, {}, {}
    for _, e in ipairs(data.mats or {}) do
        local id = e.id or e[1]
        local n = e.count or e[2] or 0
        local off = TripBestOffer(id, mine)
        local npc
        if e.source ~= "ah" and e.source ~= "auction" then
            npc = e.npcID or (off and off.npcID)
        end
        if npc and id then
            local g = seen[npc]
            if not g then
                g = { npcID = npc, items = {}, total = 0 }
                seen[npc] = g
                order[#order + 1] = g
            end
            local unit = e.unit or (off and off.unit)
            local cost = e.cost or (unit and unit * n) or nil
            g.items[#g.items + 1] = { id = id, n = n, unit = unit, cost = cost,
                                      unpriced = e.unpriced, source = e.source }
            g.total = g.total + (cost or 0)
        else
            ah[#ah + 1] = e
        end
    end
    table.sort(order, function(a, b)
        if a.total ~= b.total then return a.total > b.total end
        return (a.npcID or 0) < (b.npcID or 0)
    end)
    return order, ah
end

local function TripMapName(loc)
    if type(loc) ~= "table" then return "" end
    local mid = loc[2]
    if mid and C_Map and C_Map.GetMapInfo then
        local ok, mi = pcall(C_Map.GetMapInfo, mid)
        if ok and type(mi) == "table" and mi.name and mi.name ~= "" then return mi.name end
    end
    return PD.CampZoneName(loc[1], "")
end

local PROCURE_FRAME_MS = 10
local PROCURE_SLICE_MS = 3

local function TripDemands(data)
    local d, n = {}, 0
    for _, e in ipairs((data and data.mats) or {}) do
        local id = e.id or e[1]
        local c = e.count or e[2] or 0
        if type(id) == "number" and id > 0 and type(c) == "number" and c > 0 then
            c = math.floor(c)
            if c > 0 then
                d[id] = (d[id] or 0) + c
                n = n + c
            end
        end
    end
    return d, n
end

local function TripDemandSig(d)
    local ids = {}
    for id in pairs(d) do ids[#ids + 1] = id end
    table.sort(ids)
    local parts = {}
    for i = 1, #ids do parts[i] = ids[i] .. ":" .. d[ids[i]] end
    return table.concat(parts, ",")
end

function PD.TripKey(data)
    local d, n = TripDemands(data)
    if n <= 0 then return nil end
    return tostring(PD.cur) .. "|" .. TripDemandSig(d)
end

function PD.ProcureBusy()
    return PD.procureJob ~= nil
end

function PD.ProcureText()
    local st = PD.procureJob
    if not st then return nil end
    if st.phase == "search" then return L["正在比较商人与拍卖行"] end
    return L["正在整理价格数据"]
end

function PD.ProcureStop()
    PD.procureJob = nil
    PD.procureFrac = nil
end

function PD.ProcureClear()
    PD.procureJob = nil
    PD.procureFrac = nil
    PD.procureRes = nil
    PD.procureKey = nil
    PD.procureView = false
end

function PD.ProcureActive(data)
    if PD.procureJob then return nil end
    if not PD.procureView or not PD.procureRes then return nil end
    if PD.procureKey ~= PD.TripKey(data) then
        PD.procureView = false
        return nil
    end
    return PD.procureRes
end

function PD.ProcureStart(data)
    local E = ns.ProfEconomy
    local S = ns.ProfRouteSolver
    local J = ns.IdleJobs
    local slug = PD.cur
    if not (E and S and J) then return end
    if PD.procureJob then return end
    if type(slug) ~= "string" or slug == "__index" or slug == "poisons" then return end
    local demands, n = TripDemands(data)
    if n <= 0 then return end
    local key = tostring(slug) .. "|" .. TripDemandSig(demands)
    if PD.procureKey == key and PD.procureRes then PD.procureView = true; PD.RequestRender(); return end
    PD.ProcureClear()
    PD.procureKey = key
    local opts = {}
    if type(PD.lvOpts) == "table" then
        for k, v in pairs(PD.lvOpts) do opts[k] = v end
    end
    opts.snapshot = nil
    if opts.target == nil then opts.target = 300 end
    if type(opts.professions) ~= "table" then
        opts.professions = (E.Professions and E.Professions()) or {}
    end
    if not opts.professions[slug] then opts.professions[slug] = { cur = 1, max = 300 } end
    local st = { phase = "capture" }
    PD.procureJob = st
    PD.procureFrac = 0
    st.co = coroutine.create(function()
        local snap = E.Capture(slug, opts, function()
            if debugprofilestop() > (st.deadline or 0) then coroutine.yield("work") end
        end)
        st.phase = "search"
        return S.NewProcurementJob(snap, demands, { cpuLimitMs = 2000 })
    end)
    J.Add(function()
        if PD.procureJob ~= st then return true end
        st.deadline = debugprofilestop() + PROCURE_FRAME_MS
        while true do
            if st.job then
                if S.Run(st.job, PROCURE_SLICE_MS) then
                    local res = st.job.result
                    if not res then res = S.Result(st.job, st.job.best, st.job.status) end
                    PD.procureJob = nil
                    PD.procureFrac = nil
                    PD.procureRes = (res and res.feasible and #(res.mats or {}) > 0) and res or nil
                    PD.procureView = PD.procureRes ~= nil
                    if PD.built and PD.page and PD.page:IsShown() then PD.RequestRender() end
                    return true
                end
            else
                local ok, out = coroutine.resume(st.co)
                if not ok then
                    PD.procureJob = nil
                    PD.procureFrac = nil
                    PD.procureRes = nil
                    PD.procureView = false
                    if PD.built and PD.page and PD.page:IsShown() then PD.RequestRender() end
                    return true
                end
                if coroutine.status(st.co) == "dead" then st.job = out end
            end
            if debugprofilestop() >= st.deadline then break end
        end
        if st.painted ~= st.phase then
            st.painted = st.phase
            if PD.built and PD.page and PD.page:IsShown() then PD.RequestRender() end
        end
        return false
    end)
end

function PD.PushTripOptimized(rows, res, data)
    local seen, order, ah = {}, {}, {}
    for _, e in ipairs(res.mats or {}) do
        if e.source == "vendor" and e.npcID then
            local g = seen[e.npcID]
            if not g then
                g = { npcID = e.npcID, items = {}, total = 0 }
                seen[e.npcID] = g
                order[#order + 1] = g
            end
            g.items[#g.items + 1] = e
            g.total = g.total + (e.cost or 0)
        else
            ah[#ah + 1] = e
        end
    end
    table.sort(order, function(a, b)
        if a.total ~= b.total then return a.total > b.total end
        return (a.npcID or 0) < (b.npcID or 0)
    end)
    PushHead(rows, format(L["材料（%d 种）· 优化买法"], #(res.mats or {})), 1)
    PushText(rows, format(L["商人处 %s · 拍卖行 %s；商人按整包数量计入，点击条目在地图上标出该商人。"],
        RA.MoneyStr(res.vendorTotal or 0, "copper"), RA.MoneyStr(res.ahTotal or 0, "copper")), 11, C_GREY, 1)
    for _, g in ipairs(order) do
        local name = (ns.ProfVendorNames and ns.ProfVendorNames[g.npcID]) or L["位置未收录的商人"]
        local loc = ns.ProfVendors and ns.ProfVendors[g.npcID]
        local hasLoc = type(loc) == "table"
        PushHead(rows, name, 1)
        rows[#rows].right = hasLoc and format("%s %.1f, %.1f", TripMapName(loc), loc[3] or 0, loc[4] or 0)
                               or L["位置未收录"]
        rows[#rows].suffix = format(L["%d 种 · %s"], #g.items, RA.MoneyStr(g.total or 0, "copper"))
        if hasLoc then
            local locH = loc
            rows[#rows].act = function() PD.MarkVendorLoc(locH) end
        end
        for _, it in ipairs(g.items) do
            local cnt = it.count or it[2] or 0
            local costText = it.cost and RA.MoneyStr(it.cost, "copper") or L["价格未知"]
            local extra = {}
            if (it.bundleSize or 1) > 1 and it.bundlePrice then
                extra[1] = { format(L["每组 %d 件 %s"], it.bundleSize,
                    RA.MoneyStr(it.bundlePrice, "copper")), 0.7, 0.7, 0.7 }
            end
            extra[#extra + 1] = { format(L["小计：%s"], costText), 1, 0.82, 0 }
            local before = #rows
            PD.ShopMatRow(rows, { id = it.id, count = cnt, need = cnt, unit = it.unit,
                                  cost = it.cost, unpriced = it.unpriced,
                                  vendor = true, source = "vendor", npcID = g.npcID,
                                  bundleSize = it.bundleSize }, data or {}, true, extra)
            local row = rows[before + 1]
            if row and (it.bundleSize or 1) > 1 then
                row.sub = format(L["每包 %d 件"], it.bundleSize)
            end
            if row and hasLoc then
                local loc0 = loc
                row.act = function() PD.MarkVendorLoc(loc0) end
            end
        end
    end
    if #ah > 0 then
        PushHead(rows, format(L["拍卖行（%d 种）"], #ah), 1)
        rows[#rows].right = RA.MoneyStr(res.ahTotal or 0, "copper")
        for _, e in ipairs(ah) do
            local before = #rows
            PD.ShopMatRow(rows, e, data or {}, true,
                { { L["比价后从拍卖行购买更划算。"], 0.7, 0.7, 0.7 } })
            local row = rows[before + 1]
            if row then row.tag = { text = L["拍卖行"] } end
        end
    end
end

function PD.PushTripGroups(rows, data)
    local opt = PD.ProcureActive(data)
    if opt then
        if PD.lvSummary then
            PD.lvSummary.total = opt.total
            PD.lvSummary.priced = true
            PD.lvSummary.matsN = #(opt.mats or {})
        end
        PD.PushTripOptimized(rows, opt, data)
        return opt.total
    end
    local groups, ah = PD.TripGroups(data)
    local money = 0
    for _, g in ipairs(groups) do money = money + (g.total or 0) end
    PushHead(rows, format(L["材料（%d 种）· 按商人采购"], #(data.mats or {})), 1)
    rows[#rows].right = format(L["%d 位商人 · %s"], #groups, RA.MoneyStr(money, "copper"))
    local hint = L["同一种材料有多家货源时取当前最便宜的一家；点击条目在地图上标出该商人。"]
    if PD.ProcureBusy() then
        hint = (PD.ProcureText() or "") .. " · " .. hint
    end
    PushText(rows, hint, 11, C_GREY, 1)
    for _, g in ipairs(groups) do
        local name = (ns.ProfVendorNames and ns.ProfVendorNames[g.npcID]) or L["位置未收录的商人"]
        local loc = ns.ProfVendors and ns.ProfVendors[g.npcID]
        local hasLoc = type(loc) == "table"
        PushHead(rows, name, 1)
        rows[#rows].right = hasLoc and format("%s %.1f, %.1f", TripMapName(loc), loc[3] or 0, loc[4] or 0)
                               or L["位置未收录"]
        rows[#rows].suffix = format(L["%d 种 · %s"], #g.items, RA.MoneyStr(g.total or 0, "copper"))
        if hasLoc then
            local locH = loc
            rows[#rows].act = function() PD.MarkVendorLoc(locH) end
        end
        for _, it in ipairs(g.items) do
            local cnt = it.n or 0
            local extra = {}
            if it.bundleSize and it.bundleSize > 1 then
                extra[1] = { format(L["每组 %d 件"], it.bundleSize), 0.7, 0.7, 0.7 }
            end
            local before = #rows
            PD.ShopMatRow(rows, { id = it.id, count = cnt, need = cnt, unit = it.unit,
                                  cost = it.cost, unpriced = it.unpriced,
                                  vendor = true, source = "vendor", npcID = g.npcID,
                                  bundleSize = it.bundleSize }, data, true, extra)
            local row = rows[before + 1]
            if row and hasLoc then
                local loc0 = loc
                row.act = function() PD.MarkVendorLoc(loc0) end
            end
        end
    end
    if #ah > 0 then
        local ahMoney = 0
        for _, e in ipairs(ah) do ahMoney = ahMoney + (e.cost or 0) end
        PushHead(rows, format(L["拍卖行（%d 种）"], #ah), 1)
        rows[#rows].right = RA.MoneyStr(ahMoney, "copper")
        for _, e in ipairs(ah) do
            local before = #rows
            PD.ShopMatRow(rows, e, data, true,
                { { L["没有商人直售货源，需要从拍卖行购买。"], 0.7, 0.7, 0.7 } })
            local row = rows[before + 1]
            if row then row.tag = { text = L["拍卖行"] } end
        end
    end
    return nil
end

function PD.ShopMatSeg(data, id)
    local fa = (data.firstAt or {})[id]
    if not fa then return nil end
    for _, st in ipairs(data.executionSteps or data.steps or {}) do
        if st[1] <= fa and fa <= st[2] then return st end
    end
    return nil
end

function PD.ShopMatRow(rows, e, data, priced, extraTip)
    local lw = PD.splitLW or PD.COL_LW
    local id, n = e.id or e[1], e.count or e[2]
    local seg = PD.ShopMatSeg(data, id)
    local sub
    if seg then sub = format(L["首用于 %d–%d 段"], seg[1], seg[2]) end
    local right, right2
    if priced and not e.unpriced then
        right = format(L["×%d · %s"], n or 0, RA.MoneyStr(e.unit, "copper"))
        right2 = RA.MoneyStr(e.cost, "copper")
    else
        right = format("×%d", n or 0)
        right2 = e.unpriced and PD.UnpriceShort(e) or nil
    end
    local tip = { { format(L["需要：%d"], e.need or n or 0) },
                  e.unpriced
                      and { PD.UnpriceWhy(e, id), 0.95, 0.75, 0.4 }
                      or { format(L["约 %s"], RA.MoneyStr(e.cost, "copper")), 1, 0.82, 0 },
                  { sub or "", 0.7, 0.7, 0.7 } }
    for _, line in ipairs(PD.AuctionSupplyLines(e)) do tip[#tip + 1] = line end
    if e.have then
        tip[#tip + 1] = { format(L["背包已有 %d 件，已从采购数量中扣除。"], e.have), 0.42, 0.94, 0.62 }
    end
    if extraTip then
        for _, line in ipairs(extraTip) do tip[#tip + 1] = line end
    end
    if e.vendor then
        tip[#tip + 1] = { L["商人直售（军需官处直购，无需拍卖行）"], 0.42, 0.94, 0.62 }
        if e.npcID then tip[#tip + 1] = { format(L["商人 NPC #%d"], e.npcID), 0.7, 0.7, 0.7 } end
        if e.bundleSize then tip[#tip + 1] = { format(L["每组 %d 件"], e.bundleSize), 0.7, 0.7, 0.7 } end
        local priceHint = PD.PurchasePriceHint(e)
        if priceHint then tip[#tip + 1] = { priceHint, 0.95, 0.75, 0.4 } end
    end
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H, col = 1, it = { id },
        text = PD.Fit(DG.ItemName(id), 13, lw - 130),
        sub = sub,
        tag = { text = e.tool and L["工具"] or e.spec and L["专精任务"] or PD.PurchaseSource(e) },
        right = right,
        right2 = right2,
        lines = tip,
    }
    if e.spec then
        tip[#tip + 1] = { L["这是专精任务要交的材料，只在到达门槛时消耗一次。"], 0.95, 0.75, 0.4 }
    end
    if e.tool then
        tip[#tip + 1] = { L["这是路线所需的工具，购买或制成后保留使用，不会消耗。"], 0.58, 0.86, 1 }
    end
end

function PD.RowsRecoveryDetail(rows, src)
    local lw = PD.COL_LW
    local outs = (src and src.saleOutputs) or {}
    PD.recDetailSrc = src
    local rec = tonumber(src and src.recoveryTotal) or 0
    local fee = src and src.recoverySnapshot and src.recoverySnapshot.feePercent or nil
    local net = src and (tonumber(src.netTotal) or ((src.purchaseTotal or src.total or 0) - rec)) or 0
    PushHead(rows, L["预计回血明细"], 1)
    rows[#rows].segs = { { key = "rec_fee", text = format(L["手续费 %d%%"], fee or 5) },
                         { key = "rec_scan", text = L["扫描数量"] } }
    PushText(rows, format(L["预计回血 %s · 净成本 %s"], PD.RecoveryMoney(rec), PD.RecoveryMoney(net)), 16, C_GOLD, 1)
    if fee then
        if src.recoveryAssumesAllSold then
            PushText(rows, format(L["按 %d%% 手续费折算，剩余产物假设全部成交"], fee), 12, C_GREY, 1)
        else
            PushText(rows, format(L["按 %d%% 手续费折算，超出售数量的部分按卖店价计"], fee), 12, C_GREY, 1)
        end
    else
        PushText(rows, L["手续费未知，售价按卖店价估算"], 12, C_GREY, 1)
    end
    do
        local newest, nQuota = nil, 0
        for _, q in pairs(src and src.recoverySnapshot and src.recoverySnapshot.quotes or {}) do
            if q.supplyReliable and tonumber(q.quantity) then
                nQuota = nQuota + 1
                local t = tonumber(q.observedAt) or 0
                if t > (newest or 0) then newest = t end
            end
        end
        if newest and newest > 0 then
            PushText(rows, format(L["数量观测于 %s（%d 种有可售上限）"],
                PD.AuctionObservationText(newest), nQuota), 12, C_GREY, 1)
        end
    end
    if #outs == 0 then
        PushGap(rows, 6, 1)
        PushText(rows, L["当前路线没有可出售的剩余产物。"], 12, C_GREY, 1)
        return
    end
    local sell, unknown = {}, {}
    for _, o in ipairs(outs) do
        local unit = tonumber(o.unit) or 0
        if o.missing or unit <= 0 then
            unknown[#unknown + 1] = o
        else
            sell[#sell + 1] = o
        end
    end
    table.sort(sell, function(a, b)
        local ra, rb = tonumber(a.revenue) or 0, tonumber(b.revenue) or 0
        if ra ~= rb then return ra > rb end
        return (tonumber(b.count) or 0) > (tonumber(a.count) or 0)
    end)
    if #sell > 0 then
        PushGap(rows, 8, 1)
        PushHead(rows, format(L["可出售（%d 种）"], #sell), 1)
        rows[#rows].foldKey = "rec_sell"
        if not PD.FoldOn("rec_sell") then
            for _, o in ipairs(sell) do
                local unit = tonumber(o.unit) or 0
                local n = tonumber(o.count) or 0
                local revenue = tonumber(o.revenue) or 0
                local ah = o.source == "ah"
                rows[#rows + 1] = {
                    kind = "row", h = PD.ROW_H, col = 1, it = { o.id },
                    text = PD.Fit(DG.ItemName(o.id), 13, lw - 150),
                    sub = format(L["×%d · 单价 %s"], n, RA.MoneyStr(unit, "copper")),
                    tag = { text = ah and L["拍卖行"] or L["卖店"] },
                    right = RA.MoneyStr(revenue, "copper"),
                    lines = {
                        { format(L["%d 件 · 单价 %s"], n, RA.MoneyStr(unit, "copper")) },
                        ah and { L["按拍卖行净价估算（已扣手续费）"], 0.42, 0.94, 0.62 }
                           or { L["按卖店价估算"], 0.7, 0.7, 0.7 },
                        { format(L["收入 %s"], RA.MoneyStr(revenue, "copper")), 1, 0.82, 0 },
                    },
                }
                if ah and tonumber(o.quantity) then
                    local tipLines = rows[#rows].lines
                    table.insert(tipLines, #tipLines,
                        { format(L["观测可售 %d 件（超出部分按卖店价）"], tonumber(o.quantity)), 0.7, 0.7, 0.7 })
                end
            end
        end
    end
    if #unknown > 0 then
        PushGap(rows, 6, 1)
        PushHead(rows, format(L["售价未知（%d 种）"], #unknown), 1)
        rows[#rows].foldKey = "rec_unknown"
        if not PD.FoldOn("rec_unknown") then
            for _, o in ipairs(unknown) do
                local n = tonumber(o.count) or 0
                rows[#rows + 1] = {
                    kind = "row", h = PD.ROW_H, col = 1, it = { o.id },
                    text = PD.Fit(DG.ItemName(o.id), 13, lw - 150),
                    sub = format(L["×%d"], n),
                    tag = { text = L["未知"] },
                    right = L["—"],
                    lines = {
                        { format(L["%d 件"], n) },
                        { L["查不到拍卖行价与卖店价，这部分没有计入预计回血。"], 0.95, 0.75, 0.4 },
                    },
                }
            end
        end
    end
end

function PD.RowsAutoShop(rows, data)
    local mode = data.mode or "auto"
    local mats = data.mats or {}
    local priced = (data.planVersion == 2 and data.total ~= nil and data.feasible ~= false) or (data.priced and true) or false
    local opt = PD.shopGroup and PD.ProcureActive(data) or nil
    local total = opt and opt.total or data.total

    local title
    if mode == "auto" then
        title = L["购物清单（自动路线）"]
    else
        title = format(L["购物清单（固定路线 1–%d）"], data.target or 300)
    end
    PushHead(rows, title, 1)
    local segs = { { key = "shop_group", text = L["按商人采购"], on = PD.shopGroup } }
    if PD.shopGroup then
        if PD.ProcureBusy() then
            segs[2] = { key = "procure_cancel", text = L["取消优化"] }
        elseif PD.procureView then
            segs[2] = { key = "procure_clear", text = L["还原分组"] }
        else
            segs[2] = { key = "procure_go", text = L["优化买法"] }
        end
    end
    rows[#rows].segs = segs
    if #mats == 0 and #(data.fishMaterials or {}) == 0 then PushText(rows, L["没有需要准备的材料。"], 12, C_GREY, 1) end
    if #(data.fishMaterials or {}) > 0 then
        PushHead(rows, L["自行钓取（不计入采购）"], 1)
        rows[#rows].foldKey = "shop_fish"
        if not PD.FoldOn("shop_fish") then
            PushText(rows, L["鱼类不计金币成本；图纸仍按实际采购来源计费。"], 11, C_GREY, 1)
            for _, fish in ipairs(data.fishMaterials) do PD.RowsFishAreas(rows, {fish}, nil, 1) end
            PushGap(rows, 4, 1)
        end
    end
    local sup = ns.ProfFollow and ns.ProfFollow.SupplementNeeds and ns.ProfFollow.SupplementNeeds(PD.cur)
    if sup then
        local parts = {}
        for i = 1, math.min(3, #sup.items) do
            local it = sup.items[i]
            local nm = DG.ItemName(it.id)
            parts[#parts + 1] = format("%s ×%d", nm or ("#" .. tostring(it.id)), it.lack)
        end
        PushText(rows, format(L["当前步骤还需：%s"], table.concat(parts, "、")), 12, { 0.95, 0.75, 0.4 }, 1)
    end
    if PD.shopGroup then
        if #mats > 0 then PD.PushTripGroups(rows, data) end
    else
    PushHead(rows, format(L["材料（%d 种）"], #mats), 1)
    rows[#rows].foldKey = "shop_mats"
    if not PD.FoldOn("shop_mats") then
    for _, e in ipairs(mats) do PD.ShopMatRow(rows, e, data, priced) end
    end
    end
    if data.formulas then PD.RowsFormulaShop(rows, data, "shop_formulas") end

    local totalN = 0
    for _, e in ipairs(mats) do totalN = totalN + (e.count or e[2] or 0) end
    local snapSec, snapDays = data.snapshotAge, data.snapshotDays
    local tip = {}
    local function note(text, r, g, b)
        if text and text ~= "" then
            tip[#tip + 1] = { text, r or 0.72, g or 0.72, b or 0.72 }
        end
    end
    PushGap(rows, 8, 2)
    PushHead(rows, L["总共需要"], 2)
    rows[#rows].warn = tip
    if priced then
        PushText(rows, PD.PlanCostText({ completeCost = opt and opt.completeCost or data.completeCost, total = total }), 20, C_GOLD, 2)
    else
        PushText(rows, PD.AuctionatorStatusText(), 14, C_GREY, 2)
    end
    PushText(rows, format(L["共 %d 种材料 · 合计 %d 件"], #mats, totalN), 14, C_GREY, 2)
    if #(data.fishMaterials or {}) > 0 then
        local totalFish = 0
        for _, fish in ipairs(data.fishMaterials) do totalFish = totalFish + (fish.count or fish.need or 0) end
        PushText(rows, format(L["另需自行钓取 %d 种鱼 · 合计 %d 条"], #data.fishMaterials, totalFish), 14, C_GREY, 2)
    end
    if #(data.formulas or {}) > 0 then
        PushText(rows, format(L["另需 %d 种未学图纸"], #data.formulas), 14, C_GREY, 2)
        local formulaTotal = data.formulasTotal or data.formulaTotal
        if type(formulaTotal) == "number" then
            local amount=data.formulaComplete==false and (formulaTotal==0 and L["价格未知"] or ("≥"..RA.MoneyStr(formulaTotal,"copper")))
                or RA.MoneyStr(formulaTotal,"copper")
            PushText(rows, format(L["图纸支出：%s"], amount), 14, C_GREY, 2)
        end
        if data.formulaComplete == false or data.formulaBlocked then
            note(L["图纸获取尚未全部确认；当前总额只包含已知支出。"], 0.95, 0.75, 0.4)
        end
    end
    if data.referencePrices then note(L["含商人参考报价，实际报价可能因声望而异。"]) end
    local vendorOnly = #mats > 0 or #(data.formulas or {}) > 0
    for _, entry in ipairs(mats) do
        if not (entry.vendor or entry.source == "vendor" or entry.source == "npc") then vendorOnly = false; break end
    end
    for _, entry in ipairs(data.formulas or {}) do
        if entry.source ~= "vendor" and entry.source ~= "npc" then vendorOnly = false; break end
    end
    local atxt
    if data.planVersion == 2 then
        atxt = PD.PlanStatusText(data)
    elseif vendorOnly then
    elseif snapDays then
        atxt = (snapDays <= 0) and L["价格快照：今天（Auctionator）"]
               or format(L["价格快照 %d 天前（Auctionator）"], snapDays)
    elseif snapSec then
        if snapSec < 60 then
            atxt = L["价格快照：刚刚（Auctionator）"]
        elseif snapSec < 90 * 60 then
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(snapSec / 60 + 0.5)))
        elseif snapSec < 48 * 3600 then
            atxt = format(L["价格快照 %d 小时前（Auctionator）"], math.max(1, math.floor(snapSec / 3600 + 0.5)))
        else
            atxt = format(L["价格快照 %d 天前（Auctionator）"], math.floor(snapSec / 86400 + 0.5))
        end
    else
        atxt = L["价格快照年龄未知（Auctionator）"]
    end
    if atxt then note(atxt) end
    local progress = PD.PlanProgressText(data)
    if progress then note(progress) end
    local supply = PD.PlanSupplyText(data)
    if supply then note(supply) end
    local cached = PD.PlanCacheText(data)
    if cached then note(cached, 0.95, 0.75, 0.4) end
    if priced then
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2, fs = 14,
                            text = L["拍卖行购入"],
                            right = RA.MoneyStr((opt and opt.ahTotal or data.ahTotal) or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2, fs = 14,
                            text = L["商人直售购入"],
                            right = RA.MoneyStr((opt and opt.vendorTotal or data.vendorTotal) or 0, "copper") }
        if data.completeCost == false then
            note(L["采购价格或图纸现货尚未全部核实，当前金额是已知支出。"], 0.95, 0.75, 0.4)
        end
        local np = CountUnpriced(data)
        if np > 0 then
            note(format(L["含无价材料 %d 种：总花费为估算下限"], np), 0.95, 0.75, 0.4)
        end
    end
    PD.hasSecs = true
    local goldSec = 1
    for i = #rows, 1, -1 do
        local sp = rows[i]
        if sp.kind == "gap" and sp.col == 2 and sp.h <= 4 then
            sp.sec = goldSec
            sp.goldSec = true
        elseif sp.kind ~= "gap" and sp.col == 2 then
            sp.sec = goldSec
            sp.goldSec = true
        else
            break
        end
    end
    PD.secCount = goldSec

    if priced then
        PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
        PushHead(rows, L["产物收益"], 2)
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["产物丢拍卖行收益"],
                            right = RA.MoneyStr(data.productAH or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["直接卖给NPC收益"],
                            right = RA.MoneyStr(data.productNPC or 0, "copper") }
        local net = (total or 0) - (data.productAH or 0)
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
                sp.sec = goldSec + 1
                sp.goldSec = true
            elseif sp.kind ~= "gap" and sp.col == 2 then
                sp.sec = goldSec + 1
                sp.goldSec = true
            else
                break
            end
        end
        PD.secCount = goldSec + 1
    end
end

function PD.LevelTool()
    local fishRoute = PD.CookingFishingMode and PD.CookingFishingMode() or false
    local onLog = PD.autoPage == "log"
    local onRec = PD.autoPage == "recovery"
    local list = {
        { key = "page_route", text = L["路线"],     on = PD.autoPage ~= "shop" and not onLog and not onRec },
        { key = "page_shop",  text = L["购物清单"], on = PD.autoPage == "shop" },
        { key = "page_log",   text = L["制作记录"], on = onLog },
        { key = "page_rec",   text = L["回血"],     on = onRec },
    }
    if not onLog and not onRec and PD.autoPage ~= "shop" then
        local snap = (PD.autoSnapshotSlug == PD.cur) and PD.autoSnapshot or nil
        local head, detail = PD.PlanSupplyParts(snap)
        local tip = {}
        if head then tip[#tip + 1] = { head, 0.95, 0.75, 0.4 } end
        if detail then tip[#tip + 1] = { detail, 0.85, 0.85, 0.85 } end
        for _, ln in ipairs(PD.warnNotes or {}) do tip[#tip + 1] = ln end
        if #tip > 0 then
            list[#list + 1] = { key = "supply_warn",
                                icon = "Interface\\AddOns\\DungeonsForever\\Media\\WarnTri",
                                iconColor = { 1, 1, 1 }, tip = tip }
        end
    end
    if PD.cur ~= "poisons" then
        if fishRoute or PD.Setting("autoRoute") then
            local pairContext = not fishRoute and PD.RoutePairContext() or nil
            if pairContext and pairContext.requiresPartner then
                list[#list + 1] = {key = "partner", align = "right",
                                   text = L["搭配专业"], on = PD.partnerPicker == PD.cur}
            end
        end
        if PD.cur == "mining" then
            list[#list + 1] = {key = "gather_mode", align = "right", text = L["切换到采集路线"]}
        end
    end
    if ns.ProfTrack then
        local trackRun = TrackRunOf(PD.cur)
        if trackRun then
            local total = #(trackRun.steps or {})
            local cur = math.min(trackRun.currentIndex or 1, total)
            list[#list + 1] = { key = "track", align = "right", on = true, tone = "blue",
                                text = format(L["追踪 %d/%d"], cur, total) }
        else
            list[#list + 1] = { key = "track", align = "right", tone = "blue", text = L["开始追踪"] }
        end
    end
    if PD.cur ~= "poisons" then
        local need = PD.RecalcNeeded()
        local rec = { key = "recalc", align = "right", primary = true, glow = need, text = L["重新计算"] }
        if PD.policyDirty and PD.policyDirty[PD.cur] then
            rec.text = L["重新计算（应用排除）"]
        end
        if need then
            local why = (PD.autoSnapshot and PD.autoExact) and L["拍卖行价格或设置已更新，点击重新计算。"]
                or L["当前为快速方案，点击按精确方案重新计算。"]
            rec.tip = { { rec.text, 1, 0.82, 0 }, { why, 0.85, 0.85, 0.85 } }
        end
        list[#list + 1] = rec
    end
    return list, function(k)
        if k == "page_route" then
            PD.autoPage = "route"
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "page_shop" then
            PD.autoPage = "shop"
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "page_log" then
            PD.autoPage = "log"
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "page_rec" then
            PD.autoPage = "recovery"
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "supply_warn" then
            PD.autoPage = "shop"
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "rec_fee" then
            PD.ShowRecoveryFeeInput()
        elseif k == "rec_scan" then
            local AB = ns.AuctionBridge
            local src2 = PD.recDetailSrc
            local ids, seen = {}, {}
            for _, o in ipairs(src2 and src2.saleOutputs or {}) do
                if o.id and not seen[o.id] then seen[o.id] = true; ids[#ids + 1] = o.id end
            end
            for _, m in ipairs(src2 and src2.mats or {}) do
                local mid = m.id or m[1]
                if mid and not seen[mid] then seen[mid] = true; ids[#ids + 1] = mid end
            end
            if AB and AB.StartSupplyScan and AB.StartSupplyScan(ids, function()
                local R = ns.ProfRecovery
                if R and R.Invalidate then R.Invalidate() end
                PD.RequestRender()
            end) then
                PD.RequestRender()
            end
        elseif k == "shop_group" then
            PD.shopGroup = not PD.shopGroup
            if not PD.shopGroup then PD.ProcureClear() end
            PD.RequestRender()
        elseif k == "procure_go" then
            PD.ProcureStart(PD.lvShopData)
        elseif k == "procure_cancel" then
            PD.ProcureStop()
        elseif k == "procure_clear" then
            PD.ProcureClear()
        elseif k == "solver_toggle" then
            local on = not PD.Setting("solverRoute")
            ProfDB().solverRoute = on
            ProfDB().autoRoute = true
            PD.StopSolverRoute()
            PD.solverKey = nil
            PD.solverPaintRes = nil
            PD.autoSnapshot = nil
            PD.autoSnapshotSlug = nil
            PD.ProcureClear()
            PD.RequestRender()
        elseif k == "solver_cancel" then
            local SR = ns.ProfSolverRun
            if SR then SR.Stop() end
            ProfDB().solverRoute = false
            ProfDB().autoRoute = true
            PD.StopSolverRoute()
            PD.solverPaintRes = nil
            PD.solverFrac = nil
            PD.autoSnapshot = nil
            PD.autoSnapshotSlug = nil
            PD.ProcureClear()
            PD.RequestRender()
        elseif k == "recalc" then
            PD.exclusionsOpen = false
            PD.ProcureClear()
            PD.ClearPlanCache()
            local E = ns.ProfEconomy
            if E and E.ApplyPolicies then E.ApplyPolicies(PD.cur) end
            if RA and RA.Invalidate then RA.Invalidate() end
            if PD.policyDirty then PD.policyDirty[PD.cur] = nil end
            PD.forceExact = true
            PD.RequestRender()
            ns.PlaySound(1)
        elseif k == "exclusions" then
            PD.exclusionsOpen = not PD.exclusionsOpen
            PD.partnerPicker = nil
            if not PD.exclusionsOpen then PD.FlushPolicies() end
        elseif k == "ex_sub_recipe" then
            PD.exSub = "recipe"
        elseif k == "ex_sub_material" then
            PD.exSub = "material"
        elseif k == "partner" then
            if PD.partnerPicker == PD.cur then PD.partnerPicker = nil
            else PD.partnerPicker = PD.cur end
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "restore_all" then
            local E = ns.ProfEconomy
            if E and E.ResetPolicies then E.ResetPolicies(PD.cur) end
            PD.policyDirty = PD.policyDirty or {}; PD.policyDirty[PD.cur] = true
            PD.exReg = nil
            local mdb = ProfDB()
            if mdb.matBan then mdb.matBan[PD.cur] = nil end
        elseif k == "stop_search" then
            if RA and RA.Cancel then RA.Cancel(PD.cur) end
        elseif k == "gather_mode" then
            ProfDB().gatherMode = "gather"
            PD.exclusionsOpen = false
            PD.FlushPolicies()
        elseif k == "track" then
            local T = ns.ProfTrack
            local res = PD.autoSnapshot
            if T and res and PD.autoSnapshotSlug == PD.cur and T.Extract(res) then
                T.Restart(PD.cur, res)
            end
        end
        PD.RequestRender()
    end
end

PD.SET_ROW_H = 24
PD.SET_MORE = "›"
PD.SET_GRP_COLOR = { 0.60, 0.66, 0.76 }
PD.SET_GROUPS = {
    { L["显示"], { "greyPassed", "hlCurrent" }, 1 },
    { L["路线"], { "autoRoute", "autoFromCurrent", "autoSecondaryLeveling" }, 1 },
    { L["采购与配方"], { "autoLearnedOnly", "autoOnlyAH", "autoBuyLimitedFormulas", "autoSkipUnpricedFormulas" }, 2 },
    { L["收益与工具"], { "recoveryEnabled", "recoveryFee", "autoCraftTools", "engChoice" }, 2 },
}

function PD.RowsSettings(rows)
    PD.noZebra = true
    PD.gridSepOn = true
    PushHead(rows, L["升级页设置"])
    PushGap(rows, 6)
    PushText(rows, L["这里的开关只作用于「升级」页签里的制作路线（升级路线表），不影响其他页签。"], 14, C_GREY)
    local defs = {
        { k = "greyPassed", name = L["已过段落灰显"],
          desc = L["上限低于当前技能的段落（如 42 级时的 1~15）整行灰显"],
          d1 = L["开启后：段名、出处、数量文字变暗，配方与材料图标去饱和，不再作为下一个要关注的制作目标；"],
          d2 = L["关闭后：所有段落恢复常规配色，不做灰显处理。"] },
        { k = "hlCurrent", name = L["当前段落高亮"],
          desc = L["上下限跨着当前技能的段落（如下一个要练的 15~58）加一圈主题色外框"],
          d1 = L["开启后：下一个要练的段落四周显示一圈主题绿描边，一眼定位当前制作路线；外框只是描边，不影响行内容与点击。"],
          d2 = L["关闭后：不显示外框，该段落样式与其他行一致。"] },
        { k = "autoRoute", name = L["自动计算路线（材料采购）"],
          desc = L["关闭显示固定参考路线；开启比较商人、拍卖行和自制材料。"],
          d1 = L["不使用背包或银行库存，只计算路线需要采购的材料。"],
          d2 = L["路线与购物清单在「升级」页签顶部的按钮切换。"] },
        { k = "autoOnlyAH", name = L["只使用拍卖行可购材料的配方"],
          desc = L["材料在拍卖行/商人都查不到价格时，该配方不参与计算（商人直售材料不受限）"],
          d1 = L["开启：路线更可靠，但可能出现无配方可用的缺口区间。"],
          d2 = L["关闭：可查看含缺价材料的方案，但不会把未知费用计为零。"] },
        { k = "autoLearnedOnly", name = L["仅使用已学习的配方"],
          desc = L["只在本角色已学会的配方中挑选；未学专业不受此限制。"],
          d1 = L["开启：路线里的每一段都能立刻开做。"],
          d2 = L["关闭：允许使用未学配方，计入材料与所需图纸采购成本。"] },
        { k = "autoBuyLimitedFormulas", name = L["允许采购限量图样"],
          desc = L["限量刷新或库存未核实的商人图样是否按有货参与计算。"],
          d1 = L["开启：这类图样计入路线与采购；商人报价仅作参考，到访时可能无货。"],
          d2 = L["关闭（默认）：只有限量或未核实货源、且拍卖行没有报价的图样不进采购清单，相应配方退回固定参考路线。"] },
        { k = "autoSkipUnpricedFormulas", name = L["不使用未知来源的图纸"],
          desc = L["世界掉落图纸无拍卖行报价、商人图样无商人售价信息时，相应配方不参与升级路线。"],
          d1 = L["开启（默认）：来源价格无法核实的图纸不进路线，对应配方退回其他方案或固定参考路线。"],
          d2 = L["关闭：未知来源图纸照常参与计算，图纸费用按未知处理。"] },
        { k = "autoFromCurrent", name = L["从当前技能开始计算"],
          desc = L["开启 = 只算当前技能到 300 的路线；关闭 = 从 1 全量重算整条路线（预估全程花费）"],
          d1 = L["开启：适合练级中途打开手册直接照着做。"],
          d2 = L["关闭：查看从零开始的最优路线与总花费。"] },
        { k = "autoSecondaryLeveling", name = L["允许联合升级另一主专业"],
          desc = L["总支出更低时，将另一主专业升到制作所需材料的最低等级。"],
          d1 = L["默认关闭：仍可使用另一主专业当前能制作的材料。"],
          d2 = L["开启后计入另一专业所需的材料费用，最高 300；查看未学专业时需先选择搭配主专业。"] },
        { k = "recoveryEnabled", name = L["回血模式"],
          desc = L["把「搓完卖掉能收回多少」计入路线决策，比较采购支出减去剩余产物预计收入。"],
          d1 = L["开启：精确方案按净成本挑选配方；其他方案仍按采购支出选，但会显示预计回血。"],
          d2 = L["关闭：只看采购支出，同时仍显示预计回血与净成本供参考。"] },
        { k = "autoCraftTools", name = L["自动备齐专业工具"],
          desc = L["把附魔棒、炼金石、扳手这类必须自备的工具排进路线。"],
          d1 = L["开启：在工具可用等级插入一次制作，产出的工具计入保留物品、不按可出售计算。"],
          d2 = L["关闭：路线不含工具制作，需要你自己准备。"] },
    }
    local byKey = {}
    for _, d in ipairs(defs) do byKey[d.k] = d end
    local cheapest = (PD.SettingRaw("autoScheme") == "cheapest")
    local function allowed(k)
        if PD.cur == "poisons" then return k == "greyPassed" or k == "hlCurrent" end
        if cheapest and k == "autoOnlyAH" then return false end
        return true
    end
    local G = ns.ProfGates
    local engOK = (PD.cur == "engineering") and (G and G.GetPlannedChoice) and true or false
    local fee = tonumber(PD.SettingRaw("recoveryFeePercent")) or 5

    local function pushTextCol(text, fs, color, col)
        for _, ln in ipairs(PD.Wrap(text, fs, ColTextW(col))) do
            rows[#rows + 1] = { kind = "text", text = ln, fs = fs, color = color,
                                col = col, fcol = col, noSpan = true }
        end
    end
    local function pushGapCol(h, col)
        rows[#rows + 1] = { kind = "gap", h = h, col = col, fcol = col, noSpan = true }
    end
    local function pushToggle(d, col)
        rows[#rows + 1] = {
            kind = "row", h = PD.SET_ROW_H, col = col, fcol = col, fs = 14,
            text = d.name,
            togKey = d.k,
            help = { { d.name }, { d.desc, 0.7, 0.7, 0.7 }, { d.d1, 0.7, 0.7, 0.7 }, { d.d2, 0.7, 0.7, 0.7 } },
        }
    end
    local function pushFee(col)
        rows[#rows + 1] = {
            kind = "row", h = PD.SET_ROW_H, col = col, fcol = col, fs = 14,
            text = L["回血手续费"],
            right = format("%d%%  %s", fee, PD.SET_MORE),
            act = function(row) PD.ShowRecoveryFeeMenu(row) end,
            help = { { L["回血手续费"], 1, 1, 1 },
                     { L["拍卖行卖出时扣掉的佣金比例，只影响预计回血与净成本，不影响采购价。"], 0.7, 0.7, 0.7 },
                     { format(L["当前 %d%%；点这一行选择或自定义。"], fee), 0.7, 0.7, 0.7 },
                     { L["默认 5%，常用 0 / 5 / 10 / 15 / 20，也可输入 0–25 之间的整数。"], 0.7, 0.7, 0.7 } },
        }
    end
    local function pushEng(col)
        local planned = G.GetPlannedChoice()
        local lines = {
            { L["工程专精计划"], 1, 1, 1 },
            { L["计划学习的工程专精分支，只影响路线编排，不会改变已学专精。"], 0.7, 0.7, 0.7 },
            { L["选定分支后，路线会按该分支安排专精任务与所需材料。"], 0.7, 0.7, 0.7 },
        }
        local actual = G.EngineeringChoice()
        if actual == "conflict" then
            lines[#lines + 1] = { L["当前已同时学会地精与侏儒专精，需先重置其中一支。"], 0.88, 0.42, 0.38 }
        elseif planned ~= "none" and actual ~= "unknown" and actual ~= "none" and actual ~= planned then
            lines[#lines + 1] = { format(L["已学专精与计划不一致：已学%s。"], PD.EngChoiceLabel(actual)), 0.88, 0.42, 0.38 }
        end
        rows[#rows + 1] = {
            kind = "row", h = PD.SET_ROW_H, col = col, fcol = col, fs = 14,
            text = L["工程专精计划"],
            right = PD.EngChoiceLabel(planned) .. "  " .. PD.SET_MORE,
            act = function(row) PD.ShowEngChoiceMenu(row) end,
            help = lines,
        }
    end

    for _, grp in ipairs(PD.SET_GROUPS) do
        local gcol = (grp[3] == 2) and 2 or 1
        local items = {}
        for _, key in ipairs(grp[2]) do
            local kk = key
            if kk == "recoveryFee" then
                items[#items + 1] = pushFee
            elseif kk == "engChoice" then
                if engOK then items[#items + 1] = pushEng end
            elseif byKey[kk] and allowed(kk) then
                local d = byKey[kk]
                items[#items + 1] = function(col) pushToggle(d, col) end
            end
        end
        if #items > 0 then
            pushGapCol(10, gcol)
            pushTextCol(grp[1], 14, PD.SET_GRP_COLOR, gcol)
            pushGapCol(6, gcol)
            for i = 1, #items do
                items[i](gcol)
                if i < #items then pushGapCol(6, gcol) end
            end
        end
    end
end

function PD.PlaceSettingsToggles(rows)
    local n = math.min(#(rows or {}), PD.ROW_CAP)
    local ti, hi = 0, 0
    for i = 1, n do
        local spec = rows[i]
        local rr = PD.rows[i]
        if PD.setOpen and rr then
            rr.a:SetWidth(0)
            if spec.togKey then rr.a:SetWordWrap(false) end
            if spec.togKey then
                ti = ti + 1
                local tg = PD.setToggles[ti]
                tg:ClearAllPoints()
                tg:SetPoint("RIGHT", rr, "RIGHT", -8, 0)
                tg:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
                tg:SetChecked(PD.Setting(spec.togKey))
                tg.__key = spec.togKey
                tg:Show()
            end
            if spec.help then
                hi = hi + 1
                local hp = PD.setHelps[hi]
                if hp then
                    hp:ClearAllPoints()
                    hp:SetPoint("LEFT", rr.a, "RIGHT", 6, 0)
                    hp:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
                    hp.__tip = spec.help
                    hp.icon:SetVertexColor(C_HELP[1], C_HELP[2], C_HELP[3])
                    hp:Show()
                end
            end
        end
    end
    for j = ti + 1, #PD.setToggles do PD.setToggles[j]:Hide() end
    for j = hi + 1, #PD.setHelps do PD.setHelps[j]:Hide() end
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
        return PD.AuctionatorStatusText()
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

local function CraftMapSlug(map, slug)
    local d = R[slug]
    if type(d) ~= "table" or type(d.rows) ~= "table" then return end
    for _, rec in ipairs(d.rows) do
        local resolved = PD.RecipeData(rec, "rows", slug)
        local iid = resolved.item
        if not resolved.clientUnavailable and type(iid) == "number" and resolved.count and type(resolved.mats) == "table" and #resolved.mats > 0
           and not map[iid] then
            local live = {}
            for k, v in pairs(rec) do live[k] = v end
            live[2], live[3], live[12] = iid, resolved.count, resolved.mats
            map[iid] = { rec = live, slug = slug }
        end
    end
end

local function CraftAllMap()
    if PD.craftAllFull and PD.craftAll then return PD.craftAll end
    if not R then RGet(nil) end
    local map = PD.craftAll or {}
    PD.craftAll = map
    for slug in pairs(R) do CraftMapSlug(map, slug) end
    local rest = {}
    for _, slug in ipairs(ns.ProfRecipeKeys or {}) do
        if rawget(R, slug) == nil then rest[#rest + 1] = slug end
    end
    if #rest == 0 then
        PD.craftAllFull = true
        return map
    end
    if not (C_Timer and C_Timer.After) then
        for i = 1, #rest do
            local _ = R[rest[i]]
            CraftMapSlug(map, rest[i])
        end
        PD.craftAllFull = true
        return map
    end
    if not PD.craftAllPend then
        PD.craftAllPend = true
        local function step()
            local nextSlug
            for _, slug in ipairs(ns.ProfRecipeKeys or {}) do
                if rawget(R, slug) == nil then nextSlug = slug; break end
            end
            if not nextSlug then
                PD.craftAllPend = nil
                PD.craftAllFull = true
                if PD.built and ns.PageVisible(PD.page) then PD.RequestRender() end
                return
            end
            local _ = R[nextSlug]
            local m = PD.craftAll
            if m then CraftMapSlug(m, nextSlug) end
            C_Timer.After(0, step)
        end
        C_Timer.After(0, step)
    end
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
    PD.sideFixed = false
    PD.noZebra = false
    PD.gridSepOn = false
    PD.secPadL = nil
    PD.splitLW, PD.splitRW = nil, nil
    PD.hideDivider = false
    PD.secCount = 0
    PD.__pendRows = {}
    do
        local pk = tostring(PD.cur) .. "|" .. tostring(PD.tab) .. "|"
                   .. tostring(PD.autoPage) .. "|" .. tostring(PD.setOpen) .. "|" .. tostring(PD.exclusionsOpen)
                   .. "|" .. tostring(PD.exSub) .. "|" .. tostring(PD.partnerPicker) .. "|" .. tostring(PD.partnerUIRevision)
                   .. "|" .. tostring(PD.shopGroup)
        if pk ~= PD.__pageKey then
            PD.__pageKey = pk
            for _, rr in pairs(PD.rows) do PD.WipeRow(rr) end
            if PD.sideRows then
                for _, rr in pairs(PD.sideRows) do PD.WipeRow(rr) end
            end
            if PD.secCards then
                for i = 1, #PD.secCards do PD.secCards[i]:Hide() end
                for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end
            end
        end
    end

    if PD.setOpen then
        PD.gridSplit = true
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
        if PD.IsGatherRoute() then
            PD.lvSplit = false
            PD.gridSplit = false
            PD.autoPage = nil
            PD.RowsGatherRoute(rows)
        else
        tool, handler = PD.LevelTool()
        if PD.autoPage == "shop" and not PD.exclusionsOpen then
            PD.lvSplit = true
            PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.SHOP_SPLIT)
            PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
            PD.sideFixed = true
        else
            PD.lvSplit = false
        end
        PD.RowsLeveling(rows)
        end
    else
        PD.RowsOverview(rows)
    end

    local headText = tool and PD.lvRouteHead and PD.lvRouteHead.progress or nil
    local solverText = PD.SolverText()
    if solverText then headText = solverText end
    PD.PaintToolProgress(headText, PD.solverFrac)
    do
        local stale
        if tool and PD.tab == "leveling" and PD.autoSnapshotSlug == PD.cur
           and PD.autoSnapshot and PD.autoSnapshot.stale then
            stale = PD.PlanCacheText(PD.autoSnapshot)
        end
        PD.PaintToolStale(stale)
    end

    local toolH
    if PD.tab == "leveling" and not PD.setOpen then
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 8) - 8
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
    local sig = table.concat({
        tostring(PD.tab), tostring(PD.cur), tostring(PD.exclusionsOpen),
        tostring(PD.exSub), tostring(PD.autoPage), tostring(PD.setOpen),
        tostring(PD.splitLW),
        PD.searchBox and PD.searchBox:IsShown() and PD.searchBox.eb
        and PD.searchBox.eb:GetText() or "",
    }, "|")
    local keepV = (PD.__scrollSig == sig) and PD.__scrollV or 0
    PD.__scrollSig = sig
    PD.scroll:SetVerticalScroll(keepV)
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
            local t0 = debugprofilestop and debugprofilestop() or 0
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
                if debugprofilestop and (debugprofilestop() - t0) >= 6 then break end
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
    if type(slug) ~= "string" then return end
    ns.OpenPerf.Begin("专业·" .. tostring(slug))
    PD.HideVendorPick()
    if slug ~= PD.cur then
        PD.ClearPlanCache()
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

local function HookTrack()
    if PD.__trackHooked then return end
    local T = ns.ProfTrack
    if not T or not T.OnChanged then return end
    PD.__trackHooked = true
    T.OnChanged(function()
        if not PD.built then return end
        if PD.__trackPend then return end
        PD.__trackPend = true
        local function go()
            PD.__trackPend = nil
            if ns.PageVisible(PD.page) then PD.RequestRender() end
        end
        if C_Timer and C_Timer.After then C_Timer.After(0.25, go) else go() end
    end)
end

local RD_MIN_MS = 350
function PD.RequestRender()
    HookTrack()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    if ns.PaintJob and ns.IdleJobs and ns.PaintJob.Active("Profession") then
        PD.__pend = true
        return
    end
    local now = debugprofilestop and debugprofilestop() or nil
    if now then
        local wait = PD.__rdLast and (PD.__rdLast + RD_MIN_MS - now) or 0
        if wait > 0 and C_Timer and C_Timer.After then
            if not PD.__rdWait then
                PD.__rdWait = true
                C_Timer.After(wait / 1000, function()
                    PD.__rdWait = nil
                    PD.RequestRender()
                end)
            end
            return
        end
        PD.__rdLast = now
    end
    if not (ns.PaintJob and ns.IdleJobs) then
        PD.Render()
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

if RA and RA.OnPlanChanged then
    RA.OnPlanChanged(function(slug, plan)
        PD.craftAll = nil
        PD.craftAllFull = nil
        if type(slug) == "table" then plan = slug; slug = plan.slug end
        if slug == PD.cur and plan then PD.autoSnapshot = plan; PD.autoSnapshotSlug = slug end
        if PD.built and ns.PageVisible(PD.page)
           and (slug == nil or slug == PD.cur) then PD.RequestRender() end
    end)
end
if RA and RA.OnPricesChanged then
    RA.OnPricesChanged(function()
        local pf = ns.ProfFollow
        if pf and pf.InvalidateRoute then pcall(pf.InvalidateRoute) end
        PD.ClearPlanCache()
        if PD.built and ns.PageVisible(PD.page) then
            PD.RequestRender()
        end
    end)
end
