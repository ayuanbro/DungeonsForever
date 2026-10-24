local _, ns = ...

if not ns.LoadForeverPages then return end

local format = string.format
local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local MakeOutline = Host.MakeOutline
local SetOutline, SetButtonSelected, Unpack = Host.SetOutline, Host.SetButtonSelected, Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local C_GREEN = Host.C_GREEN
local FALLBACK_ICON = Host.FALLBACK_ICON
local PAGE_INSET = Host.PAGE_INSET

local MOUNTS = ns.CollectionMounts
if type(MOUNTS) ~= "table" or #MOUNTS == 0 then return end

local CG = {}
ns.CollectionModule = CG

local BT = BackdropTemplateMixin and "BackdropTemplate" or nil

local C_LINK = { 0.55, 0.78, 1.0 }
local C_ACCENT = { 0.27, 0.75, 0.45 }
local C_SEL_NAME = { 0.62, 0.95, 0.72 }

local RIDING_RANK = { [75] = L["初级骑术"], [150] = L["中级骑术"] }

local ItemInfo = C_Item and C_Item.GetItemInfo or GetItemInfo


local SUB_MOUNT, SUB_PET = "mount", "pet"

local SUB_TABS = {
    { id = SUB_MOUNT, label = L["坐骑"] },
    { id = SUB_PET,   label = L["宠物"] },
}

function CG.Pets()
    local seen, out = {}, {}
    local function add(t)
        if type(t) ~= "table" then return end
        for _, rec in ipairs(t) do
            local id = rec[1]
            if id and not seen[id] then
                seen[id] = true
                out[#out + 1] = rec
            end
        end
    end
    add(ns.ExplorePets)
    add(ns.CollectionPets)
    return out
end

local PET_FAC_TXT = { A = L["联盟限定"], H = L["部落限定"] }
local PET_FAC_COL = { A = { 0.45, 0.68, 0.98 }, H = { 0.95, 0.5, 0.45 } }
local PET_FAC_DUAL = L["双阵营"]
local PET_FAC_DUAL_COL = { 0.66, 0.70, 0.78 }
local PET_DIFF_TXT = {
    party = L["难度·组队"], solo = L["难度·单人"], easy = L["难度·简单"],
    store = L["商城"],
    unknown = L["待补充"],
    vendor = L["商人"],
    drop = L["掉落"],
    quest = L["任务"],
    craft = L["制造"],
    pick = L["扒窃"],
    world = L["互动"],
}
local PET_DIFF_COL = {
    party = { 0.88, 0.42, 0.42 },
    solo  = { 0.38, 0.80, 0.50 },
    easy  = { 0.38, 0.80, 0.50 },
    store = { 0.95, 0.72, 0.35 },
    unknown = { 0.60, 0.63, 0.68 },
    vendor = { 0.35, 0.78, 0.55 },
    drop   = { 0.88, 0.42, 0.42 },
    quest  = { 0.62, 0.55, 0.90 },
    craft  = { 0.38, 0.80, 0.75 },
    pick   = { 0.80, 0.62, 0.40 },
    world  = { 0.62, 0.55, 0.90 },
}

local GROUP_TXT = {
    job     = L["职业任务"],
    store   = L["商城"],
    legacy  = L["传承轨迹"],
    bmah    = L["黑市"],
    rep     = L["声望商人"],
    drop    = L["掉落"],
    unknown = L["待补充"],
}
local GROUP_COL = {
    job     = { 0.62, 0.55, 0.90 },
    store   = { 0.95, 0.72, 0.35 },
    legacy  = { 0.85, 0.62, 0.40 },
    bmah    = { 0.40, 0.82, 0.80 },
    rep     = { 0.35, 0.78, 0.55 },
    drop    = { 0.88, 0.42, 0.42 },
    unknown = { 0.60, 0.63, 0.68 },
}
local GROUP_ORDER = { "job", "store", "legacy", "bmah", "rep", "drop", "unknown" }

local FILTERS = {
    { id = "all",   label = L["全部"] },
    { id = "job",   label = L["任务"] },
    { id = "rep",   label = L["声望"] },
    { id = "store", label = L["商城"] },
    { id = "drop",  label = L["掉落"] },
    { id = "other", label = L["其他"] },
}
local FILTER_MATCH = {
    all   = nil,
    job   = { job = true },
    rep   = { rep = true },
    store = { store = true },
    drop  = { drop = true },
    other = { legacy = true, unknown = true, bmah = true },
}

local LIST_W   = 330
local ROW_H    = 42
local SEC_H    = 24
local PAD      = 8
local MODEL_H  = 480

local OVR = ns.NameOverrides

local function MountName(rec)
    if rec[2] == "spell" then
        local ok, nm = pcall(GetSpellInfo, rec[1])
        if ok and type(nm) == "string" and nm ~= "" then return nm, true end
        local o = OVR and OVR.spell and OVR.spell[rec[1]]
        if o then return o, true end
        return format(L["法术 #%d"], rec[1]), false
    end
    local nm, got = DG.ItemName(rec[1])
    if got then return nm, true end
    local o = OVR and OVR.item and OVR.item[rec[1]]
    if o then return o, true end
    return nm, false
end

local function MountIcon(rec)
    if rec[2] == "spell" then
        local ok, _, _, icon = pcall(GetSpellInfo, rec[1])
        if ok and (type(icon) == "string" or type(icon) == "number") then return icon end
    else
        local tex = DG.ItemIcon(rec[1])
        if type(tex) == "string" and tex ~= "" and tex ~= FALLBACK_ICON then return tex end
        if type(tex) == "number" then return tex end
    end
    if type(rec[3]) == "number" then return rec[3] end
    if type(rec[3]) == "string" and rec[3] ~= "" then
        return "Interface\\Icons\\" .. rec[3]
    end
    return FALLBACK_ICON
end

local function RecName(rec, isPet)
    if isPet then
        local nm, got = DG.ItemName(rec[1])
        if got then return nm, true end
        local o = OVR and OVR.item and OVR.item[rec[1]]
        if o then return o, true end
        return nm, false
    end
    return MountName(rec)
end

local function RecIcon(rec, isPet)
    if isPet then
        local tex = DG.ItemIcon(rec[1])
        if type(tex) == "string" and tex ~= "" and tex ~= FALLBACK_ICON then return tex end
        if type(tex) == "number" then return tex end
        if type(rec[2]) == "string" and rec[2] ~= "" then
            return "Interface\\Icons\\" .. rec[2]
        end
        return FALLBACK_ICON
    end
    return MountIcon(rec)
end

local function RecDisplay(rec, isPet)
    if isPet then return tonumber(rec.__display or rec[11]) end
    return tonumber(rec[6])
end

local function RecCam(rec, isPet)
    if isPet then return tonumber(rec.__cam or rec[12]) or 1 end
    return tonumber(rec[7]) or 1
end

local function CurrentList()
    if CG.sub == SUB_PET then
        local pets = CG.Pets() or {}
        local out = {}
        for _, rec in ipairs(pets) do out[#out + 1] = rec end
        return out
    end
    return MOUNTS
end

local function CurrentFilters()
    if CG.sub == SUB_PET then
        return {
            { id = "all", label = L["全部"] },
            { id = "A",   label = L["联盟"] },
            { id = "H",   label = L["部落"] },
            { id = "dual", label = L["双阵营"] },
        }
    end
    return FILTERS
end

local function AllNamesKnown()
    local isPet = CG.sub == SUB_PET
    for _, rec in ipairs(CurrentList()) do
        local _, got = RecName(rec, isPet)
        if not got then return false end
    end
    return true
end

local function ProbeNames()
    local isPet = CG.sub == SUB_PET
    local ok = true
    for _, rec in ipairs(CurrentList()) do
        local _, got = RecName(rec, isPet)
        if not got then
            ok = false
            if rec[2] ~= "spell" and DG.RequestItem then DG.RequestItem(rec[1]) end
        end
    end
    return ok
end

local function VisibleList()
    local match = FILTER_MATCH[CG.filter or "all"]
    local q = CG.search or ""
    local isPet = CG.sub == SUB_PET
    local out = {}
    for _, rec in ipairs(CurrentList()) do
        local pass = true
        if isPet then
            if CG.filter == "A" then pass = (rec[3] == "A")
            elseif CG.filter == "H" then pass = (rec[3] == "H")
            elseif CG.filter == "dual" then pass = (rec[3] == nil)
            end
        else
            pass = (match == nil) or (match[rec[4]] == true)
        end
        if pass and q ~= "" then
            local nm = RecName(rec, isPet)
            local hay = string.lower(tostring(nm)) .. " " .. tostring(rec[1])
            pass = hay:find(q, 1, true) ~= nil
        end
        if pass then out[#out + 1] = rec end
    end
    return out
end

local function Cardify(f, bgA, edA)
    if not f.SetBackdrop then return end
    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
        insets = { left = 1, right = 1, top = 1, bottom = 1 },
    })
    f:SetBackdropColor(1, 1, 1, bgA or 0.035)
    f:SetBackdropBorderColor(1, 1, 1, edA or 0.09)
end

local function TipOff()
    if GameTooltip then GameTooltip:Hide() end
end

local function ApplyCam(m)
    if m and m.SetCamDistanceScale then
        pcall(m.SetCamDistanceScale, m, m.__cam or 1)
    end
end

local function ProbeLoaded(m)
    local ok, v = pcall(m.GetDisplayInfo, m)
    return (ok and type(v) == "number" and v ~= 0) or false
end

function CG.SyncHint()
    local d = CG.detail
    if not d or not d.hintTxt then return end
    local cam = 1
    if d.model then cam = d.model.__cam or 1 end
    d.hintTxt:SetText(L["自动旋转 · 拖动旋转 · 滚轮缩放"] .. format(" · x%.1f", cam))
end

function CG.ZoneName(areaID)
    local EG = ns.ExploreModule
    if EG and EG.ZoneName then
        return EG.ZoneName(areaID, format(L["区域 #%d"], areaID or 0))
    end
    return format(L["区域 #%d"], areaID or 0)
end

function CG.MarkPoint(areaID, x, y)
    local EG = ns.ExploreModule
    if EG and EG.MarkPoint then EG.MarkPoint(areaID, x, y) end
end

function CG.PetStepsText(rec)
    local steps = rec[9]
    local parts = {}
    if type(steps) == "table" then
        for si, st in ipairs(steps) do
            local t = (type(st) == "table" and st.t) or st
            if t and t ~= "" then
                parts[#parts + 1] = format("%d. %s", si, tostring(t))
            end
        end
    end
    if #parts == 0 then
        return tostring(rec[8] or "")
    end
    return table.concat(parts, "\n")
end

local C_STEP_LINK = { 0.55, 0.78, 1.0 }
local C_STEP_LINK_HI = { 1, 0.82, 0 }
local STEP_H = 18

local function StepTip(owner, on, label, area, x, y)
    if not GameTooltip then return end
    if not on then
        if GameTooltip.Hide then pcall(GameTooltip.Hide, GameTooltip) end
        return
    end
    local has = type(x) == "number" and type(y) == "number"
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    if GameTooltip.ClearLines then GameTooltip:ClearLines() end
    GameTooltip:AddLine(label or "", 1, 1, 1, false)
    local zone = CG.ZoneName(area, area or "?")
    GameTooltip:AddLine(has and format("%s %.1f, %.1f", zone, x, y) or zone, 0.7, 0.75, 0.82, false)
    GameTooltip:AddLine(has and L["点击在世界地图标记"] or L["点击打开该区域地图"], 0.55, 0.78, 1, false)
    if GameTooltip.Show then GameTooltip:Show() end
end

local function StepSplit(t, marks)
    local segs, pos = {}, 1
    for _, mk in ipairs(marks or {}) do
        local s = t:find(mk[1], pos, true)
        if s then
            if s > pos then segs[#segs + 1] = { t:sub(pos, s - 1) } end
            segs[#segs + 1] = { t:sub(s, s + #mk[1] - 1), mk }
            pos = s + #mk[1]
        end
    end
    if pos <= #t then segs[#segs + 1] = { t:sub(pos) } end
    return segs
end

local function StepSeg(d, k)
    local sg = d.segs[k]
    if sg then return sg end
    sg = CreateFrame("Button", nil, d.panel)
    sg:SetHeight(STEP_H)
    local fs = MakeFS(sg, 13, C_TEXT, "LEFT")
    sg:SetFontString(fs)
    sg.tx = fs
    sg:SetScript("OnEnter", function(self)
        local m = self.__mark
        if not m then return end
        self.tx:SetTextColor(Unpack(C_STEP_LINK_HI))
        StepTip(self, true, m[1], m[2], m[3], m[4])
    end)
    sg:SetScript("OnLeave", function(self)
        if self.__mark then self.tx:SetTextColor(Unpack(C_STEP_LINK)) end
        StepTip(self, false)
    end)
    sg:SetScript("OnClick", function(self)
        local m = self.__mark
        if m and type(m[2]) == "number" then CG.MarkPoint(m[2], m[3], m[4]) end
    end)
    sg:Hide()
    d.segs[k] = sg
    return sg
end

local function PaintSteps(d, rec, topY, maxW)
    for _, sg in pairs(d.segs) do sg:Hide() end
    d.desc:Hide()
    local steps = rec[9]
    if type(steps) ~= "table" or #steps == 0 then
        d.desc:Show()
        d.desc:SetText(tostring(rec[8] or ""))
        return
    end
    local k, x, y = 0, 0, topY
    for si, st in ipairs(steps) do
        local t = (type(st) == "table" and st.t) or st
        if t and t ~= "" then
            local marks = (type(st) == "table" and type(st.m) == "table") and st.m or nil
            local segs = StepSplit(format("%d. %s", si, tostring(t)), marks)
            for _, s in ipairs(segs) do
                k = k + 1
                local sg = StepSeg(d, k)
                local txt, m = s[1], s[2]
                sg.__mark = m
                sg.tx:SetWordWrap(false)
                sg.tx:SetText(txt)
                local w = sg.tx:GetStringWidth()
                if type(w) ~= "number" or w <= 0 then w = 7 * #txt end
                local rows = 1
                if w > maxW then
                    if x > 0 then x, y = 0, y - STEP_H end
                    w, rows = maxW, math.ceil(w / maxW)
                    sg.tx:SetWidth(w)
                    sg.tx:SetWordWrap(true)
                end
                sg:SetWidth(w + 1)
                sg:SetHeight(STEP_H * rows)
                sg.tx:ClearAllPoints()
                sg.tx:SetPoint("LEFT", sg, "LEFT", 0, 0)
                if x > 0 and x + w > maxW then x, y = 0, y - STEP_H end
                sg:ClearAllPoints()
                sg:SetPoint("TOPLEFT", d.panel, "TOPLEFT", PAD + x, y)
                if m then
                    sg:EnableMouse(true)
                    sg.tx:SetTextColor(Unpack(C_STEP_LINK))
                else
                    sg:EnableMouse(false)
                    sg.tx:SetTextColor(Unpack(C_TEXT))
                end
                sg:Show()
                x = x + w
                if rows > 1 then x, y = 0, y - STEP_H * (rows - 1) end
            end
        end
    end
end

local function PaintRow(r, rec)
    if not r then return end
    if rec then
        r:Show()
        r.__rec = rec
        r.__pet = (CG.sub == SUB_PET) or nil
        r.icon:SetTexture(RecIcon(rec, r.__pet))
        local nm = RecName(rec, r.__pet)
        r.name:SetText(nm)
        if r.__pet then
            local fac, diff = rec[3], rec[4]
            local ftxt = fac and PET_FAC_TXT[fac] or PET_FAC_DUAL
            local fcol = (fac and PET_FAC_COL[fac]) or PET_FAC_DUAL_COL
            local dk = PET_DIFF_TXT[diff] and diff or "easy"
            r.src:SetText(format("%s · %s", ftxt, PET_DIFF_TXT[dk]))
            r.src:SetTextColor(Unpack(fcol))
        else
            local g = rec[4]
            r.src:SetText(GROUP_TXT[g] or g)
            r.src:SetTextColor(Unpack(GROUP_COL[g] or C_GREY))
        end
        local selOn = (CG.sel == rec)
        if not (ns.hui and ns.hui.PaintRowSelect and ns.hui.PaintRowSelect(r, selOn)) then
            SetOutline(r, selOn, Unpack(C_ACCENT))
        end
        if r.__hover and selOn then
            for _, t in ipairs(r.__hover) do t:Hide() end
        end
        r.name:SetTextColor(Unpack(selOn and C_SEL_NAME or C_TEXT))
    else
        r.__rec = nil
        r.__pet = nil
        r:Hide()
    end
end

    local function HideSrcRow(d)
        for _, sg in ipairs(d.srcSegs or {}) do sg:Hide() end
    end

    local function PaintMountSegs(d, segs, topY)
        local maxW = d.panel:GetWidth() - 2 * PAD
        local x, y = 0, topY
        for k, s in ipairs(segs) do
            local sg = d.srcSegs[k]
            if not sg then break end
            sg.__npcID = s[2] and s[2][2] or nil
            local t = s[1]
            sg.tx:SetText(t)
            local w = sg.tx:GetStringWidth()
            if type(w) ~= "number" or w <= 0 then w = 7 * #t end
            if x > 0 and x + w > maxW then x, y = 0, y - STEP_H end
            sg:SetWidth(w + 2)
            sg:ClearAllPoints()
            sg:SetPoint("TOPLEFT", d.panel, "TOPLEFT", PAD + x, y)
            sg.tx:SetTextColor(Unpack(sg.__npcID and C_STEP_LINK or C_TEXT))
            sg:EnableMouse(sg.__npcID ~= nil)
            sg:Show()
            x = x + w
        end
        for k = #segs + 1, #d.srcSegs do d.srcSegs[k]:Hide() end
    end

local function PaintDetail()
    local rec = CG.sel
    local d = CG.detail
    if not d then return end
    if not rec then
        d.empty:SetShown(true)
        d.model:Hide()
        d.modelIcon:Hide()
        d.name:SetText("")
        d.pill:Hide()
        d.desc:SetText("")
        HideSrcRow(d)
        if d.costRow then d.costRow:Hide() end
        for _, sg in pairs(d.segs) do sg:Hide() end
        for _, ac in ipairs(d.attrCards or {}) do ac:Hide() end
        return
    end
    d.empty:SetShown(false)

    local isPetSub = CG.sub == SUB_PET
    local disp = RecDisplay(rec, isPetSub)
    local useModel = disp ~= nil and disp > 0
        and type(d.model.SetDisplayInfo) == "function"
    d.modelIcon:SetShown(not useModel)
    if useModel then
        local m = d.model
        m.__auto = true
        m.__rot = m.__rot or 0
        m.__cam = RecCam(rec, isPetSub)
        m.__loaded = false
        m.__token = (m.__token or 0) + 1
        local tok = m.__token
        m:SetAlpha(0)
        m:Show()
        pcall(m.SetDisplayInfo, m, disp)
        ApplyCam(m)
        if C_Timer and C_Timer.After then
            for _, t in ipairs({ 0.2, 0.5, 1.0, 2.0 }) do
                C_Timer.After(t, function()
                    if m.__token ~= tok or not m:IsShown() then return end
                    ApplyCam(m)
                    if not m.__loaded and ProbeLoaded(m) then
                        m.__loaded = true
                        m:SetAlpha(1)
                    end
                end)
            end
            C_Timer.After(2.6, function()
                if m.__token == tok and m:IsShown() then m:SetAlpha(1) end
            end)
        else
            m:SetAlpha(1)
        end
    else
        d.model:Hide()
        d.modelIcon:SetTexture(RecIcon(rec, CG.sub == SUB_PET))
    end

    local isPet = CG.sub == SUB_PET
    if isPet then
        local fac, diff = rec[3], rec[4]
        local ftxt = fac and PET_FAC_TXT[fac] or PET_FAC_DUAL
        local fcol = (fac and PET_FAC_COL[fac]) or PET_FAC_DUAL_COL
        d.name:SetText(RecName(rec, true))
        d.pillTxt:SetText(ftxt)
        d.pillTxt:SetTextColor(Unpack(fcol))
        d.pill:Show()
        local dk = PET_DIFF_TXT[diff] and diff or "easy"
        if d.pill2 then
            d.pill2Txt:SetText(PET_DIFF_TXT[dk])
            d.pill2Txt:SetTextColor(Unpack(PET_DIFF_COL[dk]))
            d.pill2:Show()
        end
        local area, px, py = rec[5], rec[6], rec[7]
        local zone = CG.ZoneName(area)
        local hasMain = type(px) == "number" and type(py) == "number"
        if d.locChip then
            d.locChip:SetShown(hasMain)
            d.locChipTx:SetText(hasMain and format("%.1f, %.1f", px, py) or "")
            d.locChip.__area, d.locChip.__x, d.locChip.__y = area, px, py
            d.locChip.__label = zone
        end
        if d.zoneTx then
            local hasArea = type(area) == "number"
            d.zoneTx:SetShown(hasArea)
            if hasArea then
                d.zoneTx:SetText(zone)
                d.zoneTx.__area, d.zoneTx.__x, d.zoneTx.__y = area, px, py
                d.zoneTx.__label = zone
            end
        end
        if d.zoneHit then d.zoneHit:SetShown(type(area) == "number") end
        local baseY = -(8 + MODEL_H + 70)
        local cost = rec.cost
        if d.costRow then
            local okCost = (type(cost) == "number" and cost >= 0)
                or (type(cost) == "table" and type(cost[1]) == "number" and (cost[2] == "c" or cost[2] == "i"))
            d.costRow:SetShown(okCost)
            if okCost then
                baseY = -(8 + MODEL_H + 96)
                for _, ck in ipairs({ "g", "s", "c" }) do
                    d.coins[ck].tex:Hide()
                    d.coins[ck].fs:Hide()
                end
                d.curIcon:Hide()
                d.curTx:Hide()
                if type(cost) == "number" then
                    local COIN_TEX = {
                        g = "Interface\\MoneyFrame\\UI-GoldIcon",
                        s = "Interface\\MoneyFrame\\UI-SilverIcon",
                        c = "Interface\\MoneyFrame\\UI-CopperIcon",
                    }
                    local parts = {
                        { "g", math.floor(cost / 10000) },
                        { "s", math.floor((cost % 10000) / 100) },
                        { "c", cost % 100 },
                    }
                    local cx = 46
                    local any = false
                    for _, pr in ipairs(parts) do
                        if pr[2] > 0 then
                            any = true
                            local coin = d.coins[pr[1]]
                            coin.tex:SetTexture(COIN_TEX[pr[1]])
                            coin.tex:ClearAllPoints()
                            coin.tex:SetPoint("LEFT", d.costRow, "LEFT", cx, 0)
                            coin.tex:Show()
                            coin.fs:ClearAllPoints()
                            coin.fs:SetPoint("LEFT", coin.tex, "RIGHT", 3, 0)
                            coin.fs:SetText(pr[2])
                            coin.fs:Show()
                            cx = cx + 19 + coin.fs:GetStringWidth() + 8
                        end
                    end
                    if not any then
                        d.coins.c.tex:SetTexture(COIN_TEX.c)
                        d.coins.c.tex:ClearAllPoints()
                        d.coins.c.tex:SetPoint("LEFT", d.costRow, "LEFT", cx, 0)
                        d.coins.c.tex:Show()
                        d.coins.c.fs:ClearAllPoints()
                        d.coins.c.fs:SetPoint("LEFT", d.coins.c.tex, "RIGHT", 3, 0)
                        d.coins.c.fs:SetText(0)
                        d.coins.c.fs:Show()
                    end
                else
                    local amt, kind, id = cost[1], cost[2], cost[3]
                    d.curIcon:ClearAllPoints()
                    d.curIcon:SetPoint("LEFT", d.costRow, "LEFT", 46, 0)
                    local okIcon = false
                    if kind == "c" then
                        local ci = C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo
                            and C_CurrencyInfo.GetCurrencyInfo(id)
                        local fid = ci and ci.iconFileID
                        if fid then
                            d.curIcon:SetTexture(fid)
                            okIcon = true
                        end
                    else
                        local _, _, _, icon = ItemInfo(id)
                        if icon then
                            d.curIcon:SetTexture(icon)
                            okIcon = true
                        end
                    end
                    if not okIcon then
                        if cost[4] then
                            d.curIcon:SetTexture("Interface\\Icons\\" .. cost[4])
                        else
                            d.curIcon:SetTexture(FALLBACK_ICON)
                        end
                    end
                    d.curIcon:Show()
                    d.curTx:SetText(amt)
                    d.curTx:Show()
                end
            end
        end
        d.desc:ClearAllPoints()
        d.desc:SetPoint("TOPLEFT", d.panel, "TOPLEFT", PAD, baseY)
        d.desc:SetPoint("TOPRIGHT", d.panel, "TOPRIGHT", -PAD, baseY)
        PaintSteps(d, rec, baseY, d.panel:GetWidth() - 2 * PAD)
        local inExplore = false
        if type(ns.ExplorePets) == "table" then
            for _, p in ipairs(ns.ExplorePets) do
                if p[1] == rec[1] then inExplore = true break end
            end
        end
        if d.gotoBtn then d.gotoBtn:SetShown(inExplore) end
        HideSrcRow(d)
        for _, ac in ipairs(d.attrCards or {}) do ac:Hide() end
    else
        d.name:SetText(MountName(rec))
        local g = rec[4]
        local c = GROUP_COL[g] or C_GREY
        d.pillTxt:SetText(GROUP_TXT[g] or g)
        d.pillTxt:SetTextColor(Unpack(c))
        d.pill:Show()
        if d.pill2 then d.pill2:Hide() end
        if d.locChip then d.locChip:Hide() end
        if d.costRow then d.costRow:Hide() end
        if d.zoneTx then d.zoneTx:Hide() end
        if d.zoneHit then d.zoneHit:Hide() end
        for _, sg in pairs(d.segs) do sg:Hide() end
        local y = 8 + MODEL_H + 38
        local vals = {}
        if rec.riding and RIDING_RANK[rec.riding] then
            vals[#vals + 1] = { L["骑术"], RIDING_RANK[rec.riding] }
        end
        if rec.speed then
            vals[#vals + 1] = { L["速度"], "+" .. rec.speed .. "%" }
        end
        local t = rec.teach
        local prev = nil
        for k = 1, 2 do
            local ac = d.attrCards[k]
            local v = vals[k]
            ac:SetShown(v ~= nil)
            if v then
                ac.lab:SetText(v[1])
                ac.val:SetText(v[2])
                ac:ClearAllPoints()
                if prev then
                    ac:SetPoint("TOPLEFT", prev, "TOPRIGHT", 8, 0)
                else
                    ac:SetPoint("TOPLEFT", d.panel, "TOPLEFT", PAD, -y)
                end
                ac:SetWidth(math.max(ac.lab:GetStringWidth(), ac.val:GetStringWidth()) + 20)
                prev = ac
            end
        end
        local c3 = d.attrCards[3]
        c3:SetShown(t ~= nil)
        if t then
            local iid = rec[1]
            local nm, got = DG.ItemName(iid)
            if not nm or nm == "" then nm = "#" .. iid end
            if not got and DG.RequestItem then DG.RequestItem(iid) end
            local ok, _, qlink = pcall(ItemInfo, iid)
            c3.val:SetText((ok and type(qlink) == "string" and qlink) or nm)
            local tex = DG.ItemIcon(iid)
            if type(tex) ~= "string" and type(tex) ~= "number" then
                tex = (type(rec[3]) == "string" and rec[3] ~= "") and ("Interface\\Icons\\" .. rec[3]) or FALLBACK_ICON
            end
            c3.icon:SetTexture(tex)
            c3:ClearAllPoints()
            if prev then
                c3:SetPoint("TOPLEFT", prev, "TOPRIGHT", 8, 0)
            else
                c3:SetPoint("TOPLEFT", d.panel, "TOPLEFT", PAD, -y)
            end
            local w = 8 + 20 + 6 + c3.val:GetStringWidth() + 8
            c3:SetWidth(w + 6)
            prev = c3
        end
        if prev then y = y + 34 + 8 end
        local txt = tostring(rec[5] or "")
        local segs = nil
        local npcs = type(rec.npcs) == "table" and rec.npcs or nil
        if npcs and #npcs > 0 and txt ~= "" then
            local marks = {}
            for _, np in ipairs(npcs) do
                local nm = tostring(np[2] or "")
                if nm ~= "" then
                    local p1 = txt:find(nm, 1, true)
                    if p1 then marks[#marks + 1] = { p1, nm, np[1] } end
                end
            end
            table.sort(marks, function(a, b) return a[1] < b[1] end)
            for i, mk in ipairs(marks) do marks[i] = { mk[2], mk[3] } end
            if #marks > 0 then
                segs = StepSplit(txt, marks)
                if #segs > #d.srcSegs then segs = nil end
            end
        end
        d.desc:ClearAllPoints()
        d.desc:SetPoint("TOPLEFT", d.panel, "TOPLEFT", PAD, -y)
        d.desc:SetPoint("TOPRIGHT", d.panel, "TOPRIGHT", -PAD, -y)
        if segs then
            d.desc:Hide()
            PaintMountSegs(d, segs, -y)
        else
            HideSrcRow(d)
            d.desc:Show()
            d.desc:SetText(txt)
        end
        if d.gotoBtn then d.gotoBtn:Hide() end
    end
    CG.SyncHint()
end

local function PY()
    if coroutine.running and coroutine.running() then coroutine.yield() end
end

local function Paint()
    if not CG.built then return end
    if CG.PaintFilters then CG.PaintFilters() end
    local list = VisibleList()

    local selOK = false
    for _, rec in ipairs(list) do
        if rec == CG.sel then selOK = true break end
    end
    if not selOK then CG.sel = list[1] end

    local isPet = CG.sub == SUB_PET
    local byG, order = {}, {}
    if isPet then
        for _, rec in ipairs(list) do
            local g = rec[3] or "dual"
            if not byG[g] then byG[g] = {}; order[#order + 1] = g end
            byG[g][#byG[g] + 1] = rec
        end
    else
        for _, rec in ipairs(list) do
            local g = rec[4]
            byG[g] = byG[g] or {}
            byG[g][#byG[g] + 1] = rec
        end
        order = GROUP_ORDER
    end

    local function SecLabel(g, n)
        if isPet then
            local t = (g == "A" and L["联盟限定"]) or (g == "H" and L["部落限定"]) or L["双阵营"]
            return format("%s · %d", t, n)
        end
        return format("%s · %d", GROUP_TXT[g] or g, n)
    end

    local y = 0
    local ri, si = 0, 0
    for _, g in ipairs(order) do
        local arr = byG[g]
        if arr then
            si = si + 1
            if si > 1 then y = y - 8 end
            local hd = CG.secs[si]
            if hd then
                hd:ClearAllPoints()
                hd:SetPoint("TOPLEFT", CG.listChild, "TOPLEFT", 0, y)
                hd.txt:SetText(SecLabel(g, #arr))
                hd:Show()
            end
            y = y - SEC_H
            for _, rec in ipairs(arr) do
                ri = ri + 1
                local r = CG.rows[ri]
                PaintRow(r, rec)
                if r then
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", CG.listChild, "TOPLEFT", 0, y)
                    r:SetPoint("RIGHT", CG.listChild, "RIGHT", 0, 0)
                end
                y = y - (ROW_H + 8)
                if ri % 4 == 0 then PY() end
            end
        end
    end
    for i = si + 1, #CG.secs do CG.secs[i]:Hide() end
    for i = ri + 1, #CG.rows do
        local r = CG.rows[i]
        if r.__rec ~= nil then r.__rec = nil r:Hide() end
    end
    CG.listChild:SetHeight(-y)

    if CG.lastListSub ~= CG.sub then
        CG.lastListSub = CG.sub
        CG.listScroll:SetVerticalScroll(0)
    else
        local maxS = math.max(0, CG.listChild:GetHeight() - CG.listScroll:GetHeight())
        if CG.listScroll:GetVerticalScroll() > maxS then
            CG.listScroll:SetVerticalScroll(maxS)
        end
    end
    if CG.UpdateListScroll then CG.UpdateListScroll() end

    if CG.subBtns then
        for id, bt in pairs(CG.subBtns) do
            SetButtonSelected(bt, id == CG.sub)
        end
    end
    if CG.count then
        if CG.sub == SUB_PET then
            CG.count:SetText(format(L["当前 %d 只"], #list))
        else
            CG.count:SetText(format(L["当前 %d 匹"], #list))
        end
    end
    PaintDetail()
end

local function SweepNames()
    if not (C_Timer and C_Timer.After) then return end
    for _, d in ipairs({ 0.5, 2, 5, 10, 20 }) do
        C_Timer.After(d, function()
            if CG.built and CG.needNames and ns.PageVisible(CG.page) then
                CG.needNames = not ProbeNames()
                CG.RequestRender()
            end
        end)
    end
end

function CG.OnItemData(itemID)
    if not (CG.built and ns.PageVisible(CG.page)) then return end
    if not itemID then return end
    local hit = 0
    for i = 1, #(CG.rows or {}) do
        local r = CG.rows[i]
        local rec = r and r.__rec
        if rec and rec[1] == itemID then
            PaintRow(r, rec)
            hit = hit + 1
        end
    end
    if hit > 0 then
        if not AllNamesKnown() then return end
        CG.needNames = false
        return
    end
    if not CG.needNames or CG._itemRepaint then return end
    CG._itemRepaint = true
    if C_Timer and C_Timer.After then
        C_Timer.After(0.05, function()
            CG._itemRepaint = false
            if CG.built and CG.needNames and ns.PageVisible(CG.page) then
                CG.needNames = not ProbeNames()
                CG.RequestRender()
            end
        end)
    else
        CG._itemRepaint = false
    end
end

local function BuildListPanel(page)
    local p = CreateFrame("Frame", nil, page, BT)
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(p, 8, ns.hui.layer.L1, "both", true, 1)
    else
        Cardify(p, 0.05, 0.12)
    end
    p:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -8)
    p:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", PAGE_INSET + LIST_W, PAGE_INSET)

    CG.count = MakeFS(p, 12, C_DIM, "RIGHT")
    CG.count:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -8)

    CG.subBtns = {}
    local sx = PAD
    for _, t in ipairs(SUB_TABS) do
        local bt = NewButton(p, t.label, 52, 22, 14)
        bt:SetPoint("TOPLEFT", p, "TOPLEFT", sx, -7)
        bt.lbl = bt:GetFontString()
        SetButtonSelected(bt, false)
        bt:SetScript("OnClick", function()
            if CG.sub ~= t.id then
                CG.sub = t.id
                CG.filter = "all"
                CG.search = ""
                if CG.searchBox then CG.searchBox:SetText("") end
                CG.PaintFilters()
                CG.RequestRender(true)
                ns.PlaySound(1)
            end
        end)
        SetButtonSelected(bt, t.id == "mount")
        CG.subBtns[t.id] = bt
        sx = sx + 64
    end

    local sb = CreateFrame("Frame", nil, p, "BackdropTemplate")
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(sb, 5, ns.hui.layer.L2, "both", true, 1)
    else
        sb:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        sb:SetBackdropColor(0, 0, 0, 0.25)
        sb:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    sb:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -36)
    sb:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -36)
    sb:SetHeight(22)
    local eb = CreateFrame("EditBox", nil, sb)
    eb:SetAllPoints()
    eb:SetFontObject("GameFontHighlightSmall")
    eb:SetTextInsets(6, 6, 0, 0)
    eb:SetAutoFocus(false)
    eb:SetMaxLetters(30)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    local ph = MakeFS(sb, 12, C_DIM, "LEFT")
    ph:SetPoint("LEFT", sb, "LEFT", 8, 0)
    eb:SetScript("OnTextChanged", function(self)
        CG.search = string.lower(self:GetText() or "")
        ph:SetShown(self:GetText() == "")
        CG.RequestRender()
    end)
    CG.searchBox, CG.searchPH = eb, ph

    CG.filterBtns = {}
    for i = 1, #FILTERS do
        local bt = NewButton(p, "", 45, 22, 14)
        bt:SetPoint("TOPLEFT", p, "TOPLEFT", PAD + (i - 1) * 53, -66)
        bt.lbl = bt:GetFontString()
        SetButtonSelected(bt, false)
        bt:SetScript("OnClick", function()
            CG.filter = bt.__id
            CG.RequestRender()
            ns.PlaySound(1)
        end)
        CG.filterBtns[i] = bt
    end
    coroutine.yield()

    function CG.PaintFilters()
        local list = CurrentFilters()
        for i, bt in ipairs(CG.filterBtns) do
            local f = list[i]
            if f then
                local sel = (f.id == (CG.filter or "all"))
                bt.__id = f.id
                bt:SetText(f.label)
                SetButtonSelected(bt, sel)
                local fs = bt:GetFontString()
                if fs then
                    if sel then
                        fs:SetTextColor(1, 1, 1, 1)
                    else
                        fs:SetTextColor(Unpack(C_GREY))
                    end
                end
                bt:Show()
            else
                bt.__id = nil
                bt:Hide()
            end
        end
        if CG.searchPH then
            CG.searchPH:SetText(CG.sub == SUB_PET and L["搜索宠物…"] or L["搜索坐骑…"])
            CG.searchPH:SetShown((CG.searchBox and CG.searchBox:GetText() or "") == "")
        end
    end

    local scroll = CreateFrame("ScrollFrame", nil, p)
    scroll:EnableMouseWheel(true)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(LIST_W - 2 * PAD, 10)
    scroll:SetScrollChild(child)
    scroll:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -96)
    scroll:SetPoint("BOTTOMRIGHT", p, "BOTTOMRIGHT", -PAD, PAD)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(scroll, child, delta)
    end)
    CG.listScroll, CG.listChild = scroll, child

    local track = CreateFrame("Frame", nil, p, "BackdropTemplate")
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
    track:SetPoint("TOPRIGHT", p, "TOPRIGHT", -1, -96)
    track:SetPoint("BOTTOMRIGHT", p, "BOTTOMRIGHT", -1, PAD)
    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(5)
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

    function CG.UpdateListScroll()
        local viewH = scroll:GetHeight()
        local contentH = child:GetHeight()
        if contentH <= viewH + 2 then track:Hide() return end
        track:Show()
        local trackH = track:GetHeight() - 2
        local maxScroll = contentH - viewH
        local frac = math.min(1, math.max(0, scroll:GetVerticalScroll() / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    end
    scroll:SetScript("OnVerticalScroll", function() CG.UpdateListScroll() end)

    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = scroll:GetVerticalScroll()
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = child:GetHeight() - scroll:GetHeight()
            scroll:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    coroutine.yield()

    CG.secs = {}
    for i = 1, #GROUP_ORDER do
        local hd = CreateFrame("Frame", nil, child)
        hd:SetHeight(SEC_H)
        hd:SetWidth(LIST_W - 2 * PAD)
        hd.txt = MakeFS(hd, 12, C_DIM, "LEFT")
        hd.txt:SetPoint("LEFT", hd, "LEFT", 2, 0)
        hd:Hide()
        CG.secs[i] = hd
    end
    coroutine.yield()

    CG.rows = {}
    local maxRows = #MOUNTS
    do
        local pets = CG.Pets()
        if type(pets) == "table" and #pets > maxRows then maxRows = #pets end
    end
    for i = 1, maxRows do
        local r = CreateFrame("Button", nil, child, BT)
        r:SetHeight(ROW_H)
        r:SetWidth(LIST_W - 2 * PAD)
        if ns.hui and ns.hui.BuildRoundedBG then
            local fill, border = ns.hui.BuildRoundedBG(r, 6, ns.hui.layer.L2, "both", true, 1)
            r.__huiCard = { fill = fill, border = border }
        else
            Cardify(r)
        end
        r.__hover = nil
        if ns.hui and ns.hui.BuildCapsule then
            local hp = ns.hui.BuildCapsule(r, 6, ns.hui.layer.L4, 1, 2)
            for _, t in ipairs(hp) do t:Hide() end
            r.__hover = hp
        else
            r:SetHighlightTexture("Interface\\Buttons\\WHITE8x8")
            local hl = r:GetHighlightTexture()
            hl:SetColorTexture(1, 1, 1, 0.06)
        end
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(30, 30)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 44, -4)
        r.name:SetWidth(LIST_W - 2 * PAD - 44 - 4)
        r.name:SetWordWrap(false)
        r.src = MakeFS(r, 11, C_GREY, "LEFT")
        r.src:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 44, 5)
        r.src:SetWordWrap(false)
        MakeOutline(r, Unpack(C_ACCENT))
        r:SetScript("OnEnter", function(self)
            if self.__hover and not (self.__rec and self.__rec == CG.sel) then
                for _, t in ipairs(self.__hover) do t:Show() end
            end
            local rec = self.__rec
            if rec then DG.ShowItemTip(self, { rec[1] }) end
        end)
        r:SetScript("OnLeave", function()
            if r.__hover then
                for _, t in ipairs(r.__hover) do t:Hide() end
            end
            TipOff()
        end)
        r:SetScript("OnClick", function(self)
            if self.__rec then
                CG.sel = self.__rec
                CG.RequestRender()
                ns.PlaySound(1)
            end
        end)
        r:Hide()
        CG.rows[i] = r
        if i % 8 == 0 then coroutine.yield() end
    end
end

local function BuildDetailPanel(page)
    local p = CreateFrame("Frame", nil, page, BT)
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(p, 8, ns.hui.layer.L1, "both", true, 1)
    else
        Cardify(p, 0.05, 0.12)
    end
    p:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET + LIST_W + 8, -8)
    p:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -PAGE_INSET, PAGE_INSET)

    local vp = CreateFrame("Frame", nil, p, "BackdropTemplate")
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(vp, 6, ns.hui.layer.L0, "both", true, 1)
    else
        vp:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
            insets = { left = 1, right = 1, top = 1, bottom = 1 },
        })
        vp:SetBackdropColor(0, 0, 0, 0.30)
        vp:SetBackdropBorderColor(1, 1, 1, 0.10)
    end
    vp:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -8)
    vp:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -8)
    vp:SetHeight(MODEL_H)

    local hintBox = CreateFrame("Frame", nil, vp)
    hintBox:SetSize(1, 1)
    hintBox:SetPoint("BOTTOM", vp, "BOTTOM", 0, 6)
    hintBox:SetFrameLevel(vp:GetFrameLevel() + 4)
    local hint = MakeFS(hintBox, 11, C_DIM, "CENTER")
    hint:SetPoint("BOTTOM", hintBox, "BOTTOM", 0, 0)
    hint:SetText(L["自动旋转 · 拖动旋转 · 滚轮缩放"])

    local modelIcon = vp:CreateTexture(nil, "ARTWORK")
    modelIcon:SetSize(120, 120)
    modelIcon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(modelIcon) end
    modelIcon:SetPoint("CENTER", vp, "CENTER", 0, 14)
    modelIcon:Hide()

    local model = CreateFrame("PlayerModel", nil, vp)
    model:SetAllPoints(vp)
    model:SetFrameLevel(vp:GetFrameLevel() + 2)
    model:EnableMouse(true)
    model:EnableMouseWheel(true)
    model:RegisterForDrag("LeftButton")
    model:SetScript("OnMouseDown", function(self, button)
        if button == "LeftButton" then self.__auto = false end
    end)
    model:SetScript("OnDragStart", function(self)
        self.__drag = true
        self.__dragX = nil
    end)
    model:SetScript("OnDragStop", function(self)
        self.__drag = nil
        self.__dragX = nil
    end)
    model:SetScript("OnHide", function(self)
        self.__drag = nil
        self.__dragX = nil
    end)
    model:SetScript("OnMouseWheel", function(self, delta)
        self.__cam = self.__cam or 1
        self.__cam = self.__cam * (delta > 0 and (1 / 1.3) or 1.3)
        if self.__cam < 0.2 then self.__cam = 0.2 end
        if self.__cam > 40 then self.__cam = 40 end
        ApplyCam(self)
        CG.SyncHint()
    end)
    model:SetScript("OnUpdate", function(self, dt)
        local uiScale = UIParent and UIParent:GetEffectiveScale() or 1
        local rotating = false
        if self.__drag then
            local mx = select(1, GetCursorPosition())
            if mx then mx = mx / uiScale end
            if self.__dragX and mx then
                local dx = mx - self.__dragX
                if dx ~= 0 then
                    self.__rot = (self.__rot or 0) + dx * 0.02
                end
            end
            if mx then self.__dragX = mx end
            rotating = true
        elseif self.__auto then
            self.__rot = (self.__rot or 0) + dt * 0.7
            rotating = true
        end
        ApplyCam(self)
        if not self.__loaded and ProbeLoaded(self) then
            self.__loaded = true
            self:SetAlpha(1)
        end
        if not rotating then return end
        local rot = self.__rot
        if self.SetFacing then
            pcall(self.SetFacing, self, rot)
        elseif self.SetRotation then
            pcall(self.SetRotation, self, rot)
        end
        ApplyCam(self)
    end)
    coroutine.yield()

    local name = MakeFS(p, 18, C_WHITE, "LEFT")
    name:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -(8 + MODEL_H + 12))
    name:SetPoint("TOPRIGHT", p, "TOPRIGHT", -200, -(8 + MODEL_H + 12))
    name:SetWordWrap(false)

    local pill = CreateFrame("Frame", nil, p, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(pill, 11, ns.hui.layer.L3)
    else
        pill:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        pill:SetBackdropColor(0, 0, 0, 0.25)
    end
    pill:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -(8 + MODEL_H + 12))
    pill:SetSize(74, 22)
    local pillTxt = MakeFS(pill, 12, C_WHITE, "CENTER")
    pillTxt:SetPoint("CENTER", pill, "CENTER", 0, 0)

    local pill2 = CreateFrame("Frame", nil, p, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(pill2, 11, ns.hui.layer.L3)
    else
        pill2:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        pill2:SetBackdropColor(0, 0, 0, 0.25)
    end
    pill2:SetPoint("TOPRIGHT", pill, "TOPLEFT", -8, 0)
    pill2:SetSize(74, 22)
    local pill2Txt = MakeFS(pill2, 12, C_WHITE, "CENTER")
    pill2Txt:SetPoint("CENTER", pill2, "CENTER", 0, 0)
    pill2:Hide()

    local attrCards = {}
    for k = 1, 3 do
        local c = CreateFrame("Frame", nil, p, "BackdropTemplate")
        if ns.hui and ns.hui.BuildRoundedBG then
            ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2)
        else
            Cardify(c, 0.05, 0.10)
        end
        c:SetHeight(34)
        local lab = MakeFS(c, 11, C_DIM, "LEFT")
        lab:SetPoint("TOPLEFT", c, "TOPLEFT", 10, -6)
        local val = MakeFS(c, 13, C_WHITE, "LEFT")
        val:SetPoint("BOTTOMLEFT", c, "BOTTOMLEFT", 10, 6)
        val:SetWordWrap(false)
        c.lab, c.val = lab, val
        c:Hide()
        attrCards[k] = c
    end
    attrCards[3]:SetScript("OnEnter", function(self)
        local rec = CG.sel
        if not (rec and rec.teach and GameTooltip) then return end
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetItemByID(rec[1])
    end)
    attrCards[3]:SetScript("OnLeave", TipOff)
    do
        local c = attrCards[3]
        c.icon = c:CreateTexture(nil, "ARTWORK")
        c.icon:SetSize(20, 20)
        c.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        c.icon:SetPoint("LEFT", c, "LEFT", 8, 0)
        c.val:ClearAllPoints()
        c.val:SetPoint("LEFT", c.icon, "RIGHT", 6, 0)
        c.lab:Hide()
    end

    local zoneTx = MakeFS(p, 13, C_GREY, "LEFT")
    zoneTx:SetPoint("TOPLEFT", p, "TOPLEFT", PAD + 120, -(8 + MODEL_H + 42))
    zoneTx:SetPoint("TOPRIGHT", p, "TOPRIGHT", -110, -(8 + MODEL_H + 42))
    zoneTx:SetWordWrap(false)
    zoneTx:Hide()
    local zoneHit = CreateFrame("Button", nil, p)
    zoneHit:SetPoint("TOPLEFT", zoneTx, "TOPLEFT", 0, 2)
    zoneHit:SetPoint("BOTTOMRIGHT", zoneTx, "BOTTOMRIGHT", 0, -2)
    zoneHit:SetScript("OnClick", function()
        if zoneTx.__area then CG.MarkPoint(zoneTx.__area, zoneTx.__x, zoneTx.__y) end
    end)
    zoneHit:SetScript("OnEnter", function(self) zoneTx:SetTextColor(Unpack(C_LINK)) end)
    zoneHit:SetScript("OnLeave", function(self) zoneTx:SetTextColor(Unpack(C_GREY)) end)
    zoneHit:Hide()
    local locChip = CreateFrame("Button", nil, p, "BackdropTemplate")
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(locChip, 6, ns.hui.layer.L2, "both", false)
        if ns.hui.BuildRoundBorder then
            ns.hui.BuildRoundBorder(locChip, 6, { 0.55, 0.78, 1, 0.55 }, locChip, "BORDER", "both", 1)
        end
    else
        locChip:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        locChip:SetBackdropColor(0, 0, 0, 0.25)
        locChip:SetBackdropBorderColor(0.55, 0.78, 1, 0.35)
    end
    locChip:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -(8 + MODEL_H + 42))
    locChip:SetSize(84, 20)
    local locChipTx = MakeFS(locChip, 11, C_LINK, "CENTER")
    locChipTx:SetPoint("CENTER", locChip, "CENTER", 0, 0)
    locChip:Hide()
    locChip:SetScript("OnClick", function(self)
        if self.__area then CG.MarkPoint(self.__area, self.__x, self.__y) end
    end)
    coroutine.yield()

    local costRow = CreateFrame("Frame", nil, p)
    costRow:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -(8 + MODEL_H + 70))
    costRow:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -(8 + MODEL_H + 70))
    costRow:SetHeight(18)
    local costLab = MakeFS(costRow, 12, C_DIM, "LEFT")
    costLab:SetText(L["价格"])
    costLab:SetPoint("LEFT", costRow, "LEFT", 0, 0)
    local coins = {}
    for i, ck in ipairs({ "g", "s", "c" }) do
        local tex = costRow:CreateTexture(nil, "OVERLAY")
        tex:SetSize(16, 16)
        local fs = MakeFS(costRow, 13, C_WHITE, "LEFT")
        coins[ck] = { tex = tex, fs = fs }
    end
    local curIcon = costRow:CreateTexture(nil, "OVERLAY")
    curIcon:SetSize(18, 18)
    local curTx = MakeFS(costRow, 13, C_WHITE, "LEFT")
    curTx:SetPoint("LEFT", curIcon, "RIGHT", 4, 0)
    costRow:SetScript("OnEnter", function(self)
        local rec = CG.sel
        local cost = rec and rec.cost
        if not GameTooltip or type(cost) ~= "table" then return end
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        if cost[2] == "c" and C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo then
            GameTooltip:SetCurrencyByID(cost[3])
        elseif cost[2] == "i" then
            GameTooltip:SetItemByID(cost[3])
        end
    end)
    costRow:EnableMouse(true)
    costRow:SetScript("OnLeave", TipOff)
    costRow:Hide()
    coroutine.yield()

    local desc = MakeFS(p, 13, C_TEXT, "LEFT")
    desc:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -(8 + MODEL_H + 42))
    desc:SetPoint("TOPRIGHT", p, "TOPRIGHT", -PAD, -(8 + MODEL_H + 42))
    desc:SetJustifyV("TOP")

    local gotoBtn = CreateFrame("Button", nil, p)
    gotoBtn:SetPoint("TOPLEFT", p, "TOPLEFT", PAD, -(8 + MODEL_H + 42))
    gotoBtn:SetHeight(18)
    local gotoText = MakeFS(gotoBtn, 13, C_LINK, "LEFT")
    gotoText:SetPoint("TOPLEFT", gotoBtn, "TOPLEFT", 0, 0)
    gotoText:SetText(L["查看获取详情 →"])
    gotoBtn:SetWidth(gotoText:GetStringWidth() + 8)
    gotoBtn:SetScript("OnEnter", function(self) gotoText:SetTextColor(1, 1, 1) end)
    gotoBtn:SetScript("OnLeave", function(self) gotoText:SetTextColor(Unpack(C_LINK)) end)
    gotoBtn:SetScript("OnClick", function()
        local rec = CG.sel
        ns.OpenPage("Explore")
        local EG = ns.ExploreModule
        if EG and EG.ShowSub then
            EG.ShowSub("pets")
            if rec and EG.FocusPet then EG.FocusPet(rec[1]) end
        end
    end)
    gotoBtn:Hide()
    coroutine.yield()

    local srcSegs = {}
    for k = 1, 8 do
        local sg = CreateFrame("Button", nil, p)
        sg:SetHeight(STEP_H)
        local fs = MakeFS(sg, 13, C_STEP_LINK, "LEFT")
        sg:SetFontString(fs)
        sg.tx = fs
        sg:SetScript("OnEnter", function(self)
            if not self.__npcID then return end
            self.tx:SetTextColor(Unpack(C_STEP_LINK_HI))
            DG.ShowNpcTip(self, self.__npcID)
        end)
        sg:SetScript("OnLeave", function(self)
            self.tx:SetTextColor(Unpack(self.__npcID and C_STEP_LINK or C_TEXT))
            TipOff()
        end)
        sg:SetScript("OnClick", function(self)
            if self.__npcID then
                DG.MarkNPC(self.__npcID)
                ns.PlaySound(1)
            end
        end)
        sg:Hide()
        srcSegs[k] = sg
    end

    local empty = MakeFS(p, 14, C_DIM, "CENTER")
    empty:SetPoint("CENTER", vp, "CENTER", 0, 0)
    empty:SetText(L["没有匹配的条目"])
    empty:Hide()

    CG.detail = {
        panel = p, vp = vp, model = model, modelIcon = modelIcon,
        name = name, pill = pill, pillTxt = pillTxt,
        pill2 = pill2, pill2Txt = pill2Txt,
        attrCards = attrCards,
        zoneTx = zoneTx, zoneHit = zoneHit,
        locChip = locChip, locChipTx = locChipTx,
        costRow = costRow, costLab = costLab, coins = coins,
        curIcon = curIcon, curTx = curTx,
        gotoBtn = gotoBtn,
        desc = desc, empty = empty, hintTxt = hint,
        segs = {},
        srcSegs = srcSegs,
    }
end

function CG.Build(page)
    if CG.built or CG.building then return end
    CG.building = true
    ns.PhasedStart(34, coroutine.create(function()
    CG.page = page
    CG.sub = SUB_MOUNT
    CG.filter = "all"
    CG.search = ""
    BuildListPanel(page)
    coroutine.yield()
    BuildDetailPanel(page)
    coroutine.yield()
    CG.built = true
    CG.building = false
    if CG.PaintFilters then CG.PaintFilters() end
    CG.Render()
    end, function()
        CG.building = false
        CG.built = false
    end))
end

function CG.Open()
    if not CG.built then return end
    CG.RequestRender(true)
end

function CG.ShowSub(key)
    if not CG.built then return end
    if key ~= SUB_MOUNT and key ~= SUB_PET then key = SUB_MOUNT end
    if CG.sub ~= key then
        CG.sub = key
        CG.filter = "all"
        CG.search = ""
        if CG.searchBox then CG.searchBox:SetText("") end
        if CG.PaintFilters then CG.PaintFilters() end
    end
    CG.sel = nil
    CG.RequestRender(true)
end

function CG.Refresh()
    if not CG.built then return end
    CG.RequestRender()
end

CG.Render = Paint

function CG.RequestRender(sweep)
    if not CG.built then return end
    if sweep then CG.__sweepWant = true end
    if not (ns.PaintJob and ns.IdleJobs) then
        CG.Render()
        if CG.__sweepWant then
            CG.__sweepWant = false
            CG.needNames = not ProbeNames()
            SweepNames()
        end
        return
    end
    if ns.PaintJob.Active("Collection") then
        CG.__pend = true
        return
    end
    ns.PaintJob.Run("Collection", function() CG.Render() end, function()
        if CG.__sweepWant then
            CG.__sweepWant = false
            CG.needNames = not ProbeNames()
            SweepNames()
        end
        if CG.__pend then
            CG.__pend = false
            CG.RequestRender()
        end
    end)
end

return
