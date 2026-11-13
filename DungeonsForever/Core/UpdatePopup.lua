local _, ns = ...

if not ns.IsTitan or not ns.IsForever then return end

local L = ns.L
local f = ns.MainFrame
if not f then return end
if not (ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG) then return end

local hui = ns.hui
local LAY = hui.layer

local VER
do
    local v
    if type(C_AddOns) == "table" and type(C_AddOns.GetAddOnMetadata) == "function" then
        v = C_AddOns.GetAddOnMetadata("DungeonsForever", "Version")
    end
    if (v == nil or v == "") and type(GetAddOnMetadata) == "function" then
        v = GetAddOnMetadata("DungeonsForever", "Version")
    end
    if type(v) == "string" and v ~= "" then VER = v end
end
if not VER then return end

local PW, PH = 920, 580
local PAD = 24
local LEFT_W = 240
local RIGHT_X = PAD + LEFT_W + 8
local CELL_GAP = 8
local CELL_COLS = 2
local CELL_W = math.floor((PW - RIGHT_X - PAD - (CELL_COLS - 1) * CELL_GAP) / CELL_COLS)
local CELL_H = 200
local CELL_STEP = CELL_H + CELL_GAP
local BOX_GAP = 8
local ROW_H = 17
local ROW_MAX = 7

local CELL_POS = {
    { x = 0, y = 0, w = CELL_W },
    { x = CELL_W + CELL_GAP, y = 0, w = CELL_W },
    { x = 0, y = CELL_STEP, w = CELL_W },
    { x = CELL_W + CELL_GAP, y = CELL_STEP, w = CELL_W },
}

local C_TITLE = { 0.95, 0.96, 0.98 }
local C_BODY = { 0.66, 0.68, 0.72 }
local C_HD = { 0.90, 0.92, 0.94 }
local C_DIM = { 0.557, 0.576, 0.612 }
local C_FAINT = { 0.50, 0.52, 0.56 }
local C_LINE = { 0.106, 0.125, 0.16 }

local function Cfg()
    local db = ns.DB and ns.DB()
    local ui = db and db.ui
    if not ui then return {} end
    local t = ui.tipIntro
    if type(t) ~= "table" then
        t = {}
        ui.tipIntro = t
    end
    return t
end

local function ShouldShow()
    local c = Cfg()
    if c.off then return false end
    return c.ver ~= VER
end

local popup = CreateFrame("Frame", "DungeonsForever_UpdatePopup", f, "BackdropTemplate")
popup:SetSize(PW, PH)
popup:SetPoint("CENTER", f, "CENTER", 0, 0)
popup:SetFrameLevel(970)
popup:EnableMouse(true)
hui.SkinPopup(popup, 10, nil, LAY.L1)
if hui.SkinShadow then hui.SkinShadow(popup, nil, nil, 10) end
popup:Hide()

local shade = CreateFrame("Frame", nil, f)
shade:SetAllPoints(f)
shade:SetFrameStrata("HIGH")
shade:SetFrameLevel(960)
shade:EnableMouse(true)
do
    local bg = shade:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    bg:SetTexture("Interface/Buttons/WHITE8X8")
    bg:SetVertexColor(0.012, 0.016, 0.028, 0.58)
end
shade:Hide()

local function SyncShade()
    if popup:IsShown() then
        if not shade:IsShown() then shade:Show() end
    elseif shade:IsShown() then
        shade:Hide()
    end
end

shade:SetScript("OnUpdate", function()
    if not popup:IsShown() then shade:Hide() end
end)

popup:HookScript("OnShow", SyncShade)
popup:HookScript("OnHide", SyncShade)

local hd = popup:CreateFontString(nil, "OVERLAY")
hd:SetFont(ns.FONT, 16, "")
hd:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -20)
hd:SetText(L["本次更新"])
hd:SetTextColor(C_TITLE[1], C_TITLE[2], C_TITLE[3])

local pill = hui.MakeSolidChip(popup, popup:GetFrameLevel() + 2, hui.ChipH(14))
pill:SetPoint("LEFT", hd, "RIGHT", 8, 0)
hui.PaintSolidChip(pill, "v" .. VER, { 1.00, 0.82, 0.36 })

local sub = popup:CreateFontString(nil, "OVERLAY")
sub:SetFont(ns.FONT, 14, "")
sub:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -46)
sub:SetWidth(560)
sub:SetJustifyH("LEFT")
sub:SetText(L["鼠标提示框新增三组信息：材料需求标记、板条箱与工匠文书的价格行、配方成本。"])
sub:SetTextColor(C_BODY[1], C_BODY[2], C_BODY[3])

do
    local line = popup:CreateTexture(nil, "ARTWORK")
    line:SetTexture("Interface/Buttons/WHITE8X8")
    line:SetVertexColor(C_LINE[1], C_LINE[2], C_LINE[3], 1)
    line:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -76)
    line:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -PAD, -76)
    line:SetHeight(1)
end

local UPDATES = {
    { L["需求标记"], L["材料被工匠文书、板条箱或暗月马戏团需要时，多一行金色标记，并带上地点或档次。"] },
    { L["价格行"], L["板条箱每档材料都标价，最省的整行标绿；工匠文书把买价与造价并排放在一起。"] },
    { L["配方成本"], L["配方材料逐项标价，末尾给总成本、成品价与扣掉 5% 手续费后的收益。"] },
}

for i = 1, #UPDATES do
    local card = CreateFrame("Frame", nil, popup, "BackdropTemplate")
    card:SetSize(LEFT_W, 96)
    card:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -96 - (i - 1) * 104)
    hui.BuildRoundedBG(card, 6, LAY.L2, "both", true)

    local ch = card:CreateFontString(nil, "OVERLAY")
    ch:SetFont(ns.FONT, 14, "")
    ch:SetPoint("TOPLEFT", card, "TOPLEFT", 12, -10)
    ch:SetText(UPDATES[i][1])
    ch:SetTextColor(C_HD[1], C_HD[2], C_HD[3])

    local cb = card:CreateFontString(nil, "OVERLAY")
    cb:SetFont(ns.FONT, 14, "")
    cb:SetPoint("TOPLEFT", card, "TOPLEFT", 12, -34)
    cb:SetWidth(LEFT_W - 24)
    cb:SetJustifyH("LEFT")
    cb:SetText(UPDATES[i][2])
    cb:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
end

do
    local line = popup:CreateTexture(nil, "ARTWORK")
    line:SetTexture("Interface/Buttons/WHITE8X8")
    line:SetVertexColor(C_LINE[1], C_LINE[2], C_LINE[3], 1)
    line:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -432)
    line:SetSize(LEFT_W, 1)
end

local ask = popup:CreateFontString(nil, "OVERLAY")
ask:SetFont(ns.FONT, 14, "")
ask:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -448)
ask:SetText(L["是否现在打开设置？"])
ask:SetTextColor(0.84, 0.86, 0.88)

local askSub = popup:CreateFontString(nil, "OVERLAY")
askSub:SetFont(ns.FONT, 14, "")
askSub:SetPoint("TOPLEFT", popup, "TOPLEFT", PAD, -472)
askSub:SetWidth(LEFT_W)
askSub:SetJustifyH("LEFT")
askSub:SetText(L["就在本窗口打开，可逐项开关；不开也不影响游戏。"])
askSub:SetTextColor(C_FAINT[1], C_FAINT[2], C_FAINT[3])

local C_GREEN = hui.ACCENT or { 0.275, 0.749, 0.447 }
local C_WARN = { 0.949, 0.325, 0.306 }

local function MulC(c, k)
    return { math.min(c[1] * k, 1), math.min(c[2] * k, 1), math.min(c[3] * k, 1) }
end

local function FillCapsule(bt, col)
    local caps = hui.BuildCapsule(bt, 6, col, 0, 5)
    for i = 1, #caps do caps[i]:SetDrawLayer("BACKGROUND", 5) end
    local lit = MulC(col, 1.18)
    local function tint(c)
        for i = 1, #caps do caps[i]:SetVertexColor(c[1], c[2], c[3]) end
    end
    tint(col)
    bt:HookScript("OnEnter", function(self)
        if self:IsEnabled() then tint(lit) end
    end)
    bt:HookScript("OnLeave", function() tint(col) end)
end

local function FillButton(text)
    local bt = ns.CreateButton(popup)
    bt:SetHeight(24)
    bt:SetPushedTextOffset(0, 0)
    bt.__huiKeepTextColor = true
    local fs = bt:GetFontString()
    if fs then fs:SetFont(ns.FONT, 14, "") end
    bt:SetText(text)
    local w = 0
    if fs then
        local ok, v = pcall(fs.GetStringWidth, fs)
        if ok and type(v) == "number" and v > 0 then w = v end
    end
    bt:SetWidth(math.max(112, math.floor(w + 20)))
    if fs then fs:SetTextColor(1, 1, 1) end
    return bt
end

local btOpen = FillButton(L["打开提示框设置"])
local btSkip = FillButton(L["不打开提示框设置"])
local btW = math.max(btOpen:GetWidth(), btSkip:GetWidth())
btOpen:SetWidth(btW)
btSkip:SetWidth(btW)
btOpen:SetPoint("BOTTOMLEFT", popup, "BOTTOMLEFT", PAD, PAD)
btSkip:SetPoint("LEFT", btOpen, "RIGHT", 8, 0)
FillCapsule(btOpen, C_GREEN)
FillCapsule(btSkip, C_WARN)

local cbNoTip = CreateFrame("CheckButton", nil, popup)
cbNoTip:SetSize(36, 20)
cbNoTip:EnableMouse(true)
if hui.ReskinToggle then hui.ReskinToggle(cbNoTip) end
cbNoTip:SetFrameLevel(popup:GetFrameLevel() + 6)
cbNoTip:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -PAD, PAD)

local lbNoTip = cbNoTip:CreateFontString(nil, "OVERLAY")
lbNoTip:SetFont(ns.FONT, 14, "")
lbNoTip:SetPoint("RIGHT", cbNoTip, "LEFT", -6, 0)
lbNoTip:SetText(L["下次不提醒"])
lbNoTip:SetTextColor(0.62, 0.64, 0.68)
do
    local lw = 0
    local ok, v = pcall(lbNoTip.GetStringWidth, lbNoTip)
    if ok and type(v) == "number" and v > 0 then lw = v end
    cbNoTip:SetHitRectInsets(-(math.floor(lw) + 8), 0, -6, -6)
end

local xb = CreateFrame("Button", nil, popup, "BackdropTemplate")
xb:SetSize(24, 24)
xb:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -14, -14)
if hui.SkinButton then hui.SkinButton(xb, { noFrame = true }) end
do
    local fs = xb:CreateFontString(nil, "OVERLAY")
    fs:SetFont(ns.FONT, 16, "")
    fs:SetPoint("CENTER")
    fs:SetText("\195\151")
    fs:SetTextColor(0.55, 0.58, 0.62)
end

local CELLS = {
    { hd = L["需求标记"], note = L["命中哪个就出哪行。"], n = 2 },
    { hd = L["板条箱"], note = L["按价从低到高排，最省整行标绿。"] },
    { hd = L["工匠文书"], note = L["拍卖行价与自造价并排对比。"] },
    { hd = L["配方"], note = L["材料逐项带价，末尾给总成本与净收益。"] },
}

local boxes = {}

for i = 1, #CELLS do
    local pos = CELL_POS[i]
    local slot = CreateFrame("Frame", nil, popup)
    slot:SetSize(pos.w, CELL_H)
    slot:SetPoint("TOPLEFT", popup, "TOPLEFT", RIGHT_X + pos.x, -96 - pos.y)

    local sh = slot:CreateFontString(nil, "OVERLAY")
    sh:SetFont(ns.FONT, 14, "")
    sh:SetPoint("TOPLEFT", slot, "TOPLEFT", 0, 0)
    sh:SetText(CELLS[i].hd)
    sh:SetTextColor(0.60, 0.63, 0.68)

    local prev
    for _ = 1, CELLS[i].n or 1 do
        local box = CreateFrame("Frame", nil, slot, "BackdropTemplate")
        box:SetWidth(pos.w)
        box:SetHeight(56)
        if prev then
            box:SetPoint("TOPLEFT", prev, "BOTTOMLEFT", 0, -BOX_GAP)
        else
            box:SetPoint("TOPLEFT", slot, "TOPLEFT", 0, -20)
        end
        hui.BuildRoundedBG(box, 8, LAY.L3, "both", true)
        boxes[#boxes + 1] = box
        prev = box
    end

    local note = slot:CreateFontString(nil, "OVERLAY")
    note:SetFont(ns.FONT, 14, "")
    note:SetPoint("TOPLEFT", prev, "BOTTOMLEFT", 0, -8)
    note:SetWidth(pos.w)
    note:SetJustifyH("LEFT")
    note:SetText(CELLS[i].note)
    note:SetTextColor(C_FAINT[1], C_FAINT[2], C_FAINT[3])
end

local function LineAt(box, i)
    box.__pool = box.__pool or {}
    local e = box.__pool[i]
    if not e then
        local l = box:CreateFontString(nil, "OVERLAY")
        l:SetFont(ns.FONT, 14, "")
        l:SetJustifyH("LEFT")
        local r = box:CreateFontString(nil, "OVERLAY")
        r:SetFont(ns.FONT, 14, "")
        r:SetJustifyH("RIGHT")
        e = { l = l, r = r }
        box.__pool[i] = e
    end
    return e
end

local function PaintTip(box, id, rows)
    local pool = box.__pool or {}
    for i = 1, #pool do
        pool[i].l:Hide()
        pool[i].r:Hide()
    end

    local n = 0
    if id then
        n = 1
        local e = LineAt(box, 1)
        local nm = tostring(id)
        local DG = ns.DungeonModule
        if DG and DG.ItemName then
            local ok, v = pcall(DG.ItemName, id)
            if ok and type(v) == "string" and v ~= "" then nm = v end
        end
        local r, g, b = 1, 1, 1
        if DG and DG.QualOf and DG.QColor then
            local okq, q = pcall(DG.QualOf, id)
            if okq and type(q) == "number" then
                local _, cr, cg, cb = pcall(DG.QColor, q)
                if type(cr) == "number" and type(cg) == "number" and type(cb) == "number" then
                    r, g, b = cr, cg, cb
                end
            end
        end
        e.l:ClearAllPoints()
        e.l:SetPoint("TOPLEFT", box, "TOPLEFT", 10, -9)
        e.l:SetText(nm)
        e.l:SetTextColor(r, g, b)
        e.l:Show()
        e.r:Hide()
    end

    local shown = 0
    if type(rows) == "table" then
        for i = 1, #rows do
            if shown >= ROW_MAX - 1 then break end
            local row = rows[i]
            if type(row) == "table" and type(row[1]) == "string" then
                shown = shown + 1
                n = n + 1
                local e = LineAt(box, n)
                local y = -30 - (shown - 1) * ROW_H
                e.l:ClearAllPoints()
                e.l:SetPoint("TOPLEFT", box, "TOPLEFT", 10, y)
                e.l:SetText(row[1])
                e.l:SetTextColor(row[2] or 1, row[3] or 1, row[4] or 1)
                e.l:Show()
                if type(row[7]) == "string" then
                    e.r:ClearAllPoints()
                    e.r:SetPoint("TOPRIGHT", box, "TOPRIGHT", -10, y)
                    e.r:SetText(row[7])
                    e.r:SetTextColor(row[8] or row[2] or 1, row[9] or row[3] or 1, row[10] or row[4] or 1)
                    e.r:Show()
                else
                    e.r:Hide()
                end
            end
        end
    end

    local total = shown
    if total == 0 then
        total = 1
        n = n + 1
        local e = LineAt(box, n)
        e.l:ClearAllPoints()
        e.l:SetPoint("TOPLEFT", box, "TOPLEFT", 10, -30)
        e.l:SetText(L["暂无可显示的价格"])
        e.l:SetTextColor(0.55, 0.55, 0.55)
        e.l:Show()
        e.r:Hide()
    end

    box:SetHeight(30 + total * ROW_H + 8)
end

local recipeCache
local pendingIds = {}

local function RowsHaveGap(rows)
    for i = 1, #rows do
        local r = rows[i]
        if type(r) == "table" and r[7] == "—" then return true end
    end
    return false
end

local function ItemNameOK(id)
    local PM = ns.ProfModule
    if not (PM and PM.ItemName) then return true end
    local ok, got = PM.ItemName(id)
    if ok and got then return true end
    if type(id) == "number" then pendingIds[#pendingIds + 1] = id end
    return false
end

local function PickNeed()
    local PM = ns.ProfModule
    if not (PM and PM.WritNeedLines and PM.CrateNeedLines) then return nil end
    local wr = (ns.CratesData and ns.CratesData.writs) or {}
    local fallback
    for i = 1, #wr do
        local w = wr[i]
        if type(w) == "table" and type(w.target) == "number" then
            local okw, wrows = pcall(PM.WritNeedLines, w.target)
            if okw and type(wrows) == "table" and #wrows > 0 then
                local rows = {}
                local okc, crows = pcall(PM.CrateNeedLines, w.target)
                if okc and type(crows) == "table" then
                    for k = 1, #crows do rows[#rows + 1] = crows[k] end
                end
                for k = 1, #wrows do rows[#rows + 1] = wrows[k] end
                local oz, zone = pcall(PM.WritZoneOf, w.target)
                if oz and type(zone) == "number" and ItemNameOK(w.target) then
                    return w.target, rows
                end
                if not fallback then fallback = { w.target, rows } end
            end
        end
    end
    if fallback then return fallback[1], fallback[2] end
    return nil
end

local function PickDarkmoon()
    local TL = ns.TipLines
    local DM = ns.Darkmoon
    if not (TL and TL.DarkmoonNeedRows) then return nil end
    if not (type(DM) == "table" and type(DM.LINES) == "table") then return nil end
    local function rowsOf(id)
        local ok, rows = pcall(TL.DarkmoonNeedRows, id)
        if ok and type(rows) == "table" and #rows > 0 then return rows end
        return nil
    end
    local prefer = 5134
    local cand = {}
    for i = 1, #DM.LINES do
        local ln = DM.LINES[i]
        if type(ln) == "table" and type(ln.mats) == "table" then
            for t = 1, #ln.mats do
                local id = ln.mats[t]
                if type(id) == "number" then cand[#cand + 1] = id end
            end
        end
    end
    local rows = rowsOf(prefer)
    if rows and ItemNameOK(prefer) then return prefer, rows end
    for i = 1, #cand do
        local id = cand[i]
        local r = rowsOf(id)
        if r then
            if ItemNameOK(id) then return id, r end
            if not rows then
                prefer = id
                rows = r
            end
        end
    end
    if rows then return prefer, rows end
    return nil
end

local function PickRecipe()
    if recipeCache then return recipeCache[1], recipeCache[2] end
    local PM = ns.ProfModule
    local RA = ns.ProfRouteAuto
    if not (PM and PM.PatternIndex and PM.PatternTipLines) then return nil end
    if ns.EnsureProfRecipes then pcall(ns.EnsureProfRecipes) end
    local ok, idx = pcall(PM.PatternIndex)
    if not ok or type(idx) ~= "table" then return nil end
    local cand = {}
    for id, e in pairs(idx) do
        if type(e) == "table" and e.pid == id and type(e.r) == "table" then
            local mats = e.r[12]
            local cnt = type(mats) == "table" and #mats or 0
            local ah = RA and RA.AHPriceOf and RA.AHPriceOf(e.r[2]) or nil
            if cnt >= 2 and cnt <= 3 and ah then
                local all, cost = true, 0
                for k = 1, cnt do
                    local mid = mats[k][1]
                    local mp = RA.MatPriceOf and RA.MatPriceOf(mid) or nil
                    if not mp then
                        all = false
                        break
                    end
                    cost = cost + mp * (mats[k][2] or 1)
                end
                if all and cost > 0 and math.floor(ah * 0.95) - cost > 0 then
                    cand[#cand + 1] = id
                end
            end
        end
    end
    table.sort(cand)
    local fallback
    local tried = 0
    for i = 1, #cand do
        if tried < 80 then
            local id = cand[i]
            local e = idx[id]
            local mats = e.r[12]
            local named = ItemNameOK(e.r[2])
            for k = 1, #mats do
                if not ItemNameOK(mats[k][1]) then named = false end
            end
            if named then
                local okr, rows = pcall(PM.PatternTipLines, id, nil)
                if okr and type(rows) == "table" and #rows > 0 then
                    recipeCache = { id, rows }
                    return id, rows
                end
            end
            if not fallback then
                local okr, rows = pcall(PM.PatternTipLines, id, nil)
                if okr and type(rows) == "table" and #rows > 0 then fallback = { id, rows } end
            end
            tried = tried + 1
        end
    end
    if fallback then
        recipeCache = fallback
        return fallback[1], fallback[2]
    end
    recipeCache = {}
    return nil
end

local function CrateNamesOK(c)
    local opts = c.opts
    if type(opts) ~= "table" then return true end
    local ok = true
    for i = 1, #opts do
        local o = opts[i]
        if type(o) == "table" and o[1] ~= nil and not ItemNameOK(o[1]) then ok = false end
    end
    return ok
end

local function CrateNeedBoth(c)
    if type(c.opts) ~= "table" or type(c.opts[1]) ~= "table" then return false end
    local PM = ns.ProfModule
    if not (PM and PM.WritNeedOf) then return false end
    local ok, tid = pcall(PM.WritNeedOf, c.opts[1][1])
    return ok and tid ~= nil
end

local function PickCrate()
    local PM = ns.ProfModule
    local CD = ns.CratesData
    local cr = CD and CD.crates
    if type(cr) ~= "table" then return nil end
    local first, firstNoGap, firstNamed
    if PM and PM.CrateTipLines then
        for i = 1, #cr do
            local c = cr[i]
            if type(c) == "table" and type(c.id) == "number" then
                local ok, rows = pcall(PM.CrateTipLines, c.id)
                if ok and type(rows) == "table" and #rows > 0 then
                    local named = ItemNameOK(c.id) and CrateNamesOK(c)
                    if named and not RowsHaveGap(rows) and CrateNeedBoth(c) then return c, rows end
                    if named and not firstNamed then firstNamed = { c, rows } end
                    if not RowsHaveGap(rows) and not firstNoGap then firstNoGap = { c, rows } end
                    if not first then first = { c, rows } end
                end
            end
        end
    end
    if firstNamed then return firstNamed[1], firstNamed[2] end
    if firstNoGap then return firstNoGap[1], firstNoGap[2] end
    if first then return first[1], first[2] end
    for i = 1, #cr do
        local c = cr[i]
        if type(c) == "table" and type(c.id) == "number" then return c, nil end
    end
    return nil
end

local function PickWrit()
    local PM = ns.ProfModule
    local CD = ns.CratesData
    local wr = CD and CD.writs
    if type(wr) ~= "table" then return nil end
    local first, firstNoGap, firstNamed
    if PM and PM.WritTipLines then
        for i = 1, #wr do
            local w = wr[i]
            if type(w) == "table" and type(w.item) == "number" then
                local ok, rows = pcall(PM.WritTipLines, w.item)
                if ok and type(rows) == "table" and #rows > 0 then
                    local named = ItemNameOK(w.item) and ItemNameOK(w.target)
                    if named and not RowsHaveGap(rows) then return w, rows end
                    if named and not firstNamed then firstNamed = { w, rows } end
                    if not RowsHaveGap(rows) and not firstNoGap then firstNoGap = { w, rows } end
                    if not first then first = { w, rows } end
                end
            end
        end
    end
    if firstNamed then return firstNamed[1], firstNamed[2] end
    if firstNoGap then return firstNoGap[1], firstNoGap[2] end
    if first then return first[1], first[2] end
    for i = 1, #wr do
        local w = wr[i]
        if type(w) == "table" and type(w.item) == "number" then return w, nil end
    end
    return nil
end

local refreshRetried

local function Refresh()
    pendingIds = {}
    local crate, crateRows = PickCrate()
    local writ, writRows = PickWrit()
    local pid, patternRows = PickRecipe()
    local needId, needRows = PickNeed()
    local dmId, dmRows = PickDarkmoon()

    PaintTip(boxes[1], needId, needRows)
    PaintTip(boxes[2], dmId, dmRows)
    PaintTip(boxes[3], crate and crate.id or nil, crateRows)
    PaintTip(boxes[4], writ and writ.item or nil, writRows)
    PaintTip(boxes[5], pid, patternRows)

    if not refreshRetried and #pendingIds > 0 then
        refreshRetried = true
        local req = C_Item and C_Item.RequestLoadItemDataByID
        if type(req) == "function" then
            for i = 1, #pendingIds do pcall(req, pendingIds[i]) end
        end
        if C_Timer and C_Timer.After then
            C_Timer.After(0.35, function()
                if popup:IsShown() then
                    recipeCache = nil
                    if ns.ProfModule and ns.ProfModule.ResetItemNameMemo then
                        pcall(ns.ProfModule.ResetItemNameMemo)
                    end
                    Refresh()
                end
            end)
        end
    end
end

local function MarkSeen()
    local c = Cfg()
    c.ver = VER
    c.off = (cbNoTip and cbNoTip:GetChecked()) and true or false
end

local function Close()
    MarkSeen()
    popup:Hide()
    SyncShade()
end

local function Dismiss()
    if cbNoTip and cbNoTip:GetChecked() then MarkSeen() end
    popup:Hide()
    SyncShade()
end

local function Open()
    if cbNoTip then cbNoTip:SetChecked(Cfg().remindBox ~= false) end
    refreshRetried = nil
    popup:Show()
    SyncShade()
    Refresh()
end

btOpen:SetScript("OnClick", function()
    ns.PlaySound(1)
    local c = ns.TipCfg()
    if not (c.global and true) then c.global = true end
    Close()
    if ns.OpenTipSettings then ns.OpenTipSettings() end
end)

btSkip:SetScript("OnClick", function()
    ns.PlaySound(1)
    local c = ns.TipCfg()
    c.need = false
    c.price = false
    c.matPrice = false
    if ns.TipLines and ns.TipLines.RefreshPreview then
        pcall(ns.TipLines.RefreshPreview)
    end
    Close()
end)

xb:SetScript("OnClick", function()
    ns.PlaySound(1)
    Dismiss()
end)

cbNoTip:SetScript("OnClick", function(self)
    ns.PlaySound(1)
    local on = self:GetChecked() and true or false
    self:SetChecked(on)
    Cfg().remindBox = on
end)

shade:SetScript("OnMouseDown", function()
    Dismiss()
end)

popup:HookScript("OnShow", function()
    if cbNoTip then cbNoTip:SetChecked(Cfg().remindBox ~= false) end
    SyncShade()
end)

popup:HookScript("OnHide", SyncShade)

function ns.ShowUpdatePopup()
    Open()
end

function ns.UpdatePopupClose()
    Dismiss()
end

ns.UpdatePopup = popup

function ns.UpdatePopupCheck()
    SyncShade()
    if popup:IsShown() then return end
    if not ShouldShow() then return end
    Open()
end

if type(hooksecurefunc) == "function" then
    hooksecurefunc(ns, "Open", function() ns.UpdatePopupCheck() end)
end

f:HookScript("OnShow", function()
    ns.UpdatePopupCheck()
    SyncShade()
end)

f:HookScript("OnHide", function()
    if popup:IsShown() then popup:Hide() end
    SyncShade()
end)
