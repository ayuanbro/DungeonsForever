local _, ns = ...

if not ns.LoadForeverPages then return end

local format = string.format
local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local TT = ns.TierModule
if not TT then return end

local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local SetButtonSelected = Host.SetButtonSelected
local C_GREY, C_DIM, C_TEXT = Host.C_GREY, Host.C_DIM, Host.C_TEXT
local FALLBACK_ICON = Host.FALLBACK_ICON

local CU = ns.ClassCombatUI or {}
ns.ClassCombatUI = CU

CU.ROW_MAX = 40
CU.CARD_MAX = 20
CU.LABEL_MAX = 8
CU.TOP_PAD = 8
CU.GAP = 8
CU.ROW_PAD_BOT = 10
CU.ICON = 22
CU.TOP = 19
CU.PAD = TT.CARD_PAD
CU.OK = { 0.25, 0.85, 0.35 }
CU.LATER = { 1.00, 0.82, 0.00 }
CU.WARN = { 0.90, 0.62, 0.28 }
CU.CODE = { 0.62, 0.88, 0.70 }

CU.CARD_COLS = 3
CU.CARD_GAP = 8
CU.CARD_PAD = 12
CU.CARD_ICON = 36
CU.CARD_BTN_H = 24
CU.DET_W = 76
CU.MK_W = 114
CU.CP_W = 60
CU.MACRO_SUFFIX = " DF"
CU.CHIP_PAD = 3
CU.CHIP_Y = CU.CARD_PAD + 24
CU.WHAT_Y = CU.CHIP_Y + 14 + 8

local TEXT_W = TT.FULL_W - CU.PAD * 2 - CU.ICON - 8
local CARD_W = math.floor((TT.FULL_W - (CU.CARD_COLS - 1) * CU.CARD_GAP) / CU.CARD_COLS)
local CARD_IN = CARD_W - 2 * CU.CARD_PAD
local CARD_BODY_W = CARD_IN - 16

local function Fnt(size)
    local base = ns.FONT or "Fonts\\FRIZQT__.TTF"
    local flags = "OUTLINE"
    if ns.hui and ns.hui.FontFlags then flags = ns.hui.FontFlags("OUTLINE") end
    return base, size, flags
end

local function FSHeight(fs)
    local h = fs.GetStringHeight and fs:GetStringHeight()
    return tonumber(h) or 14
end

local function Combat()
    local d = ns.EnsureClassCombat and ns.EnsureClassCombat() or ns.ClassCombat
    if type(d) ~= "table" then return nil end
    return d
end

local SpellIndex = {}

local function SpellRow(d, cls, name)
    local list = d and d.spells and d.spells[cls]
    if type(list) ~= "table" then return nil end
    local idx = SpellIndex[cls]
    if not idx or idx.__src ~= list then
        idx = { __src = list }
        for i = 1, #list do
            local row = list[i]
            if type(row) == "table" and type(row[1]) == "string" then idx[row[1]] = row end
        end
        SpellIndex[cls] = idx
    end
    return idx[name]
end

local function Ranks(d, cls, name)
    return SpellRow(d, cls, name)
end

local function KnownId(ranks)
    if type(ranks) ~= "table" then return nil end
    for i = #ranks, 3, -1 do
        local ok, known = pcall(IsPlayerSpell, ranks[i])
        if ok and known then return ranks[i] end
    end
    return nil
end

local function BaseId(ranks)
    if type(ranks) ~= "table" then return nil end
    return ranks[3]
end

local function SpellName(id)
    if not id then return nil end
    if C_Spell and C_Spell.GetSpellName then
        local ok, n = pcall(C_Spell.GetSpellName, id)
        if ok and type(n) == "string" and n ~= "" then return n end
    end
    if type(GetSpellInfo) == "function" then
        local ok, n = pcall(GetSpellInfo, id)
        if ok and type(n) == "string" and n ~= "" then return n end
    end
    return nil
end

local function SpellIcon(id)
    if not id then return FALLBACK_ICON end
    if C_Spell and C_Spell.GetSpellTexture then
        local ok, t = pcall(C_Spell.GetSpellTexture, id)
        if ok and t then return t end
    end
    if type(GetSpellInfo) == "function" then
        local ok, _, _, t = pcall(GetSpellInfo, id)
        if ok and t then return t end
    end
    return FALLBACK_ICON
end

local function Notify(msg)
    print("|cffffd100" .. L["宏命令"] .. "|r · " .. msg)
end

local function ResolveBody(d, cls, body)
    local missing, seen = {}, {}
    local out = body:gsub("{(.-)}", function(key)
        local chosen, anyKnown, firstKey, firstName
        for k in key:gmatch("[^|]+") do
            k = k:gsub("^%s+", ""):gsub("%s+$", "")
            local ranks = Ranks(d, cls, k)
            local known = KnownId(ranks)
            local nm = SpellName(known or BaseId(ranks)) or k
            firstKey = firstKey or k
            firstName = firstName or nm
            if known then
                chosen = nm
                anyKnown = true
                break
            end
            if not chosen and nm ~= k then chosen = nm end
        end
        if not chosen then chosen = firstName or key end
        if not anyKnown and not seen[firstKey or key] then
            seen[firstKey or key] = true
            missing[#missing + 1] = firstName or key
        end
        return chosen
    end)
    return out, missing
end

local function InCombat()
    return type(InCombatLockdown) == "function" and InCombatLockdown() and true or false
end

local function ShiftDown()
    return type(IsShiftKeyDown) == "function" and IsShiftKeyDown() and true or false
end

local function MacroIndexOf(name)
    if type(GetMacroIndexByName) ~= "function" then return 0 end
    local ok, i = pcall(GetMacroIndexByName, name)
    if ok and type(i) == "number" then return i end
    return 0
end

local function CreateMacroNamed(name, legacy, body)
    if InCombat() then
        Notify(L["战斗状态无法创建宏"])
        return
    end
    if type(CreateMacro) ~= "function" then return end
    local idx = MacroIndexOf(name)
    if idx == 0 and legacy and legacy ~= "" then
        idx = MacroIndexOf(legacy)
    end
    local ok
    if idx > 0 and type(EditMacro) == "function" then
        ok = pcall(EditMacro, idx, name, "INV_Misc_QuestionMark", body)
    else
        ok = pcall(CreateMacro, name, "INV_Misc_QuestionMark", body, true)
    end
    if ok then
        Notify(format(L["宏已创建：%s · 用 /macro 拖到动作条"], name))
    else
        Notify(L["创建失败：角色宏已达上限"])
    end
end

local function PickUpSpell(id)
    if not id then return end
    if InCombat() then
        Notify(L["战斗状态无法拣起法术"])
        return
    end
    if C_Spell and C_Spell.PickupSpell then
        pcall(C_Spell.PickupSpell, id)
    elseif type(PickupSpell) == "function" then
        pcall(PickupSpell, id)
    end
end

local function BuildCopy()
    if CU.copy then return CU.copy end
    local f = CreateFrame("Frame", nil, UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f:SetSize(430, 230)
    f:SetPoint("CENTER")
    f:SetFrameStrata("DIALOG")
    f:EnableMouse(true)
    if ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(f, 6, nil, ns.hui.layer.L1)
    elseif f.SetBackdrop then
        f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                        edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        f:SetBackdropColor(0.086, 0.102, 0.133, 1)
        f:SetBackdropBorderColor(1, 1, 1, 0.12)
    end
    local title = MakeFS(f, 16, C_GREY, "LEFT")
    title:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -12)
    f.title = title
    local box = CreateFrame("EditBox", nil, f)
    box:SetMultiLine(true)
    box:SetAutoFocus(false)
    box:SetWidth(402)
    box:SetHeight(150)
    box:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -34)
    local a, b, c = Fnt(14)
    if box.SetFont then box:SetFont(a, b, c) end
    box:SetScript("OnEscapePressed", function() f:Hide() end)
    box:SetScript("OnEditFocusGained", function(self) self:HighlightText() end)
    f.box = box
    local close = NewButton(f, L["关闭"], 84, CU.CARD_BTN_H, 14)
    do
        local fs = close:GetFontString()
        close:SetWidth(math.max(84, math.floor((fs and fs:GetStringWidth() or 40) + 24)))
    end
    close:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -14, 12)
    close:SetScript("OnClick", function() f:Hide() end)
    f:Hide()
    CU.copy = f
    return f
end

local function ShowCopy(name, body)
    local f = BuildCopy()
    f.title:SetText(name .. "   " .. L["Ctrl+C 复制"])
    f.box:SetText(body)
    f:Show()
    f.box:SetFocus()
    f.box:HighlightText()
end

local function BodyLines(body)
    local t = {}
    for line in (body or ""):gmatch("[^\n]+") do
        t[#t + 1] = line
    end
    return t
end

local function ShowExplain(owner, name, body, explain)
    if type(explain) ~= "table" or #explain == 0 then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(name or "", 1, 0.82, 0)
    GameTooltip:AddLine(L["宏命令详解"], 0.55, 0.62, 0.70)
    local lines = BodyLines(body)
    for i, cmd in ipairs(lines) do
        GameTooltip:AddLine("|cff9fe0b4" .. cmd .. "|r", 1, 1, 1, true)
        if explain[i] then
            GameTooltip:AddLine("    " .. explain[i], 0.92, 0.92, 0.92, true)
        end
    end
    GameTooltip:Show()
end

local function Skin(frame, radius, layer)
    if ns.hui and ns.hui.SkinPopup and layer then
        ns.hui.SkinPopup(frame, radius, nil, layer)
    end
end

local function Ensure()
    if CU.built then return end
    local child = TT.child
    if not child then return end
    CU.built = true

    CU.rows = {}
    for i = 1, CU.ROW_MAX do
        local fr = CreateFrame("Button", nil, child)
        fr:SetWidth(TT.FULL_W)
        fr:SetHeight(CU.TOP + 20)
        fr:RegisterForClicks("LeftButtonUp")
        fr:Hide()
        if ns.hui and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(fr, 6, 2)
        else
            fr.bg = fr:CreateTexture(nil, "BACKGROUND", nil, 2)
            fr.bg:SetAllPoints()
            fr.bg:SetColorTexture(1, 1, 1, 0.04)
        end
        local tile = CreateFrame("Frame", nil, fr)
        tile:SetSize(CU.ICON, CU.ICON)
        tile:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.PAD, -4)
        local tex = tile:CreateTexture(nil, "ARTWORK")
        tex:SetAllPoints()
        tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(tex) end
        local a = MakeFS(fr, 14, C_TEXT, "LEFT")
        a:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.PAD + CU.ICON + 8, -3)
        a:SetWordWrap(false)
        local b = MakeFS(fr, 12, C_GREY, "RIGHT")
        b:SetPoint("TOPRIGHT", fr, "TOPRIGHT", -CU.PAD, -4)
        b:SetWordWrap(false)
        local c = MakeFS(fr, 14, C_DIM, "LEFT")
        c:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.PAD + CU.ICON + 8, -CU.TOP)
        c:SetWordWrap(true)
        c:SetWidth(TEXT_W)
        local d = MakeFS(fr, 14, C_DIM, "LEFT")
        d:SetWordWrap(true)
        d:SetWidth(TEXT_W)
        fr.__tile, fr.__tex = tile, tex
        fr.__a, fr.__b, fr.__c, fr.__d = a, b, c, d
        fr:SetScript("OnEnter", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
            if self.__tipText then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(self.__tipText, 1, 1, 1, true)
                if self.__tipSub then
                    GameTooltip:AddLine(self.__tipSub, 0.7, 0.7, 0.7, true)
                end
                GameTooltip:Show()
            end
        end)
        fr:SetScript("OnLeave", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
            GameTooltip:Hide()
        end)
        fr:SetScript("OnClick", function(self)
            if self.__act then self.__act() end
        end)
        CU.rows[i] = fr
    end

    CU.cards = {}
    for i = 1, CU.CARD_MAX do
        local fr = CreateFrame("Button", nil, child)
        fr:SetWidth(CARD_W)
        fr:RegisterForClicks("LeftButtonUp")
        fr:Hide()
        if ns.hui and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(fr, 6, 2)
        else
            Skin(fr, 6, ns.hui and ns.hui.layer.L2)
        end
        local tile = CreateFrame("Frame", nil, fr)
        tile:SetSize(CU.CARD_ICON, CU.CARD_ICON)
        tile:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.CARD_PAD, -CU.CARD_PAD)
        local tex = tile:CreateTexture(nil, "ARTWORK")
        tex:SetAllPoints()
        tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(tex) end
        local name = MakeFS(fr, 14, C_TEXT, "LEFT")
        name:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.CARD_PAD + CU.CARD_ICON + 8, -(CU.CARD_PAD + 1))
        name:SetWordWrap(false)
        local det = NewButton(fr, L["详解"], CU.DET_W, CU.CARD_BTN_H, 14)
        TT.RoundButtonFill(det)
        SetButtonSelected(det, false)
        det:SetPoint("TOPRIGHT", fr, "TOPRIGHT", -CU.CARD_PAD, -CU.CARD_PAD)
        local chip = DG.MakeBadge(fr, ns.hui and ns.hui.layer.L3)
        chip:EnableMouse(true)
        local chipFS = chip.lab
        chip:SetScript("OnEnter", function(self)
            if not self.__tip then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(self.__tip, 0.90, 0.62, 0.28, true)
            GameTooltip:Show()
        end)
        chip:SetScript("OnLeave", function() GameTooltip:Hide() end)
        local what = MakeFS(fr, 14, C_TEXT, "LEFT")
        what:SetWordWrap(true)
        what:SetWidth(CARD_IN)
        local box = CreateFrame("Frame", nil, fr)
        box:Hide()
        Skin(box, 5, ns.hui and ns.hui.layer.L1)
        local body = MakeFS(box, 14, CU.CODE, "LEFT")
        body:SetPoint("TOPLEFT", box, "TOPLEFT", 8, -8)
        body:SetWordWrap(true)
        body:SetWidth(CARD_BODY_W)
        local mk = NewButton(fr, L["创建宏"], CU.MK_W, CU.CARD_BTN_H, 14)
        TT.RoundButtonFill(mk)
        SetButtonSelected(mk, false)
        mk:SetPoint("BOTTOMLEFT", fr, "BOTTOMLEFT", CU.CARD_PAD, CU.CARD_PAD)
        local cp = NewButton(fr, L["复制"], CU.CP_W, CU.CARD_BTN_H, 14)
        TT.RoundButtonFill(cp)
        SetButtonSelected(cp, false)
        cp:SetPoint("LEFT", mk, "RIGHT", 8, 0)
        det:SetScript("OnEnter", function(self)
            ShowExplain(self, self.__macroName, self.__macroBody, self.__explain)
        end)
        det:SetScript("OnLeave", function() GameTooltip:Hide() end)
        mk:SetScript("OnClick", function()
            CreateMacroNamed(mk.__macroName, mk.__legacy, mk.__body)
        end)
        cp:SetScript("OnClick", function()
            ShowCopy(cp.__macroName or "", cp.__macroBody or "")
        end)
        fr:SetScript("OnEnter", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
        end)
        fr:SetScript("OnLeave", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        end)
        fr:SetScript("OnClick", function()
            if ShiftDown() then ShowCopy(fr.__macroName or "", fr.__macroBody or "") end
        end)
        local function FitButton(bt, minw)
            local fs = bt:GetFontString()
            bt:SetWidth(math.max(minw, math.floor((fs and fs:GetStringWidth() or 40) + 24)))
        end
        FitButton(det, 64)
        FitButton(mk, 88)
        FitButton(cp, 48)
        fr.__tile, fr.__tex = tile, tex
        fr.__name, fr.__det, fr.__chip, fr.__chipFS = name, det, chip, chipFS
        fr.__what, fr.__box, fr.__bodyFS = what, box, body
        fr.__mk, fr.__cp = mk, cp
        CU.cards[i] = fr
    end

    CU.labels = {}
    for i = 1, CU.LABEL_MAX do
        local fs = MakeFS(child, 14, C_DIM, "LEFT")
        fs:SetWidth(TEXT_W + CU.ICON + 8)
        fs:SetWordWrap(true)
        fs:Hide()
        CU.labels[i] = fs
    end
end

local function Reset()
    CU.used, CU.labeled = 0, 0
    if CU.rows then
        for i = 1, CU.ROW_MAX do CU.rows[i]:Hide() end
    end
    if CU.cards then
        for i = 1, CU.CARD_MAX do CU.cards[i]:Hide() end
    end
    if CU.labels then
        for i = 1, CU.LABEL_MAX do CU.labels[i]:Hide() end
    end
end

local function PutLabel(text, color, y, x, w)
    CU.labeled = (CU.labeled or 0) + 1
    local fs = CU.labels[CU.labeled]
    if not fs then return y end
    local a, b, c = Fnt(14)
    if fs.SetFont then fs:SetFont(a, b, c) end
    if w then fs:SetWidth(w) end
    fs:SetText(text)
    fs:SetTextColor(color[1], color[2], color[3])
    fs:ClearAllPoints()
    fs:SetPoint("TOPLEFT", TT.child, "TOPLEFT", x or CU.PAD, -y)
    fs:Show()
    local h = FSHeight(fs)
    fs.__cy, fs.__ch, fs.__cgen = y, h, TT.__renderGen
    return y + h + CU.GAP
end

local function PutRow(item, x, w, y)
    CU.used = (CU.used or 0) + 1
    local fr = CU.rows[CU.used]
    if not fr then return y end
    if w then fr:SetWidth(w) end
    fr:ClearAllPoints()
    fr:SetPoint("TOPLEFT", TT.child, "TOPLEFT", x or 0, -y)
    fr.__a:SetText(item.a)
    fr.__a:SetTextColor(item.ac[1], item.ac[2], item.ac[3])
    fr.__b:SetText(item.b or "")
    fr.__b:SetTextColor(item.bc[1], item.bc[2], item.bc[3])
    if fr.__tex.SetTexture then fr.__tex:SetTexture(item.icon or FALLBACK_ICON) end
    fr.__c:SetText(item.c or "")
    fr.__c:SetTextColor(item.cc[1], item.cc[2], item.cc[3])
    fr.__d:SetText(item.d or "")
    fr.__d:SetTextColor((item.dc or C_DIM)[1], (item.dc or C_DIM)[2], (item.dc or C_DIM)[3])
    fr.__showD = (item.d ~= nil and item.d ~= "")
    fr.__tipText = item.tip
    fr.__tipSub = item.tipSub
    fr.__act = item.act
    fr:Show()
    local hc = FSHeight(fr.__c)
    local hd = 0
    if fr.__showD then
        fr.__d:ClearAllPoints()
        fr.__d:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.PAD + CU.ICON + 8, -(CU.TOP + hc + 2))
        fr.__d:Show()
        hd = FSHeight(fr.__d)
    else
        fr.__d:Hide()
    end
    local h = CU.TOP + hc + (hd > 0 and (2 + hd) or 0) + CU.ROW_PAD_BOT
    fr:SetHeight(h)
    fr.__cy, fr.__ch, fr.__cgen = y, h, TT.__renderGen
    return y + h + CU.GAP
end

local function Finish(y, cap)
    TT.child:SetHeight(y + CU.GAP)
    TT.overflowed = (CU.used or 0) > (cap or CU.ROW_MAX)
end

function CU.HideRows()
    if not CU.built then return end
    for i = 1, CU.ROW_MAX do
        if CU.rows[i] then CU.rows[i]:Hide() end
    end
    for i = 1, CU.CARD_MAX do
        if CU.cards[i] then CU.cards[i]:Hide() end
    end
    for i = 1, CU.LABEL_MAX do
        if CU.labels[i] then CU.labels[i]:Hide() end
    end
end

function CU.Cull(gen, vTop, vBot)
    if not CU.built then return end
    local viewH = vBot - vTop
    local function one(el)
        if not el or el.__cgen ~= gen then return end
        local cy, ch = el.__cy, el.__ch
        if type(cy) ~= "number" or type(ch) ~= "number" then return end
        local show = ((cy + ch) > vTop) and (cy < vBot)
        if show then el:Show() else el:Hide() end
    end
    for i = 1, CU.ROW_MAX do
        if CU.rows[i] then one(CU.rows[i]) end
    end
    for i = 1, CU.CARD_MAX do
        if CU.cards[i] then one(CU.cards[i]) end
    end
    for i = 1, CU.LABEL_MAX do
        if CU.labels[i] then one(CU.labels[i]) end
    end
end

local function SpellEntry(d, cls, e)
    local ranks = Ranks(d, cls, e.spell)
    local id = KnownId(ranks)
    local known = id ~= nil
    local shown = id or BaseId(ranks)
    return {
        a = SpellName(shown) or e.spell,
        ac = known and CU.OK or CU.LATER,
        b = known and L["已掌握"] or "",
        bc = known and CU.OK or CU.LATER,
        c = e.note or "",
        cc = C_DIM,
        dc = C_DIM,
        icon = SpellIcon(shown),
        tip = SpellName(shown) or e.spell,
        tipSub = e.note or "",
        act = function()
            if known then PickUpSpell(id) end
        end,
    }
end

function CU.RenderRotation()
    local cls, spec = TT.PaintHeader()
    if not cls then return end
    Ensure()
    if not CU.built then return end
    Reset()
    local d = Combat()
    local y = CU.TOP_PAD
    y = PutLabel(L["自上而下 = 优先级，用第一个就绪的"] .. "，" .. L["金色 = 以后才解锁"]
        .. " · " .. L["点击拣起放入动作条"], C_DIM, y, 0, TT.FULL_W - 2 * CU.PAD)
    y = y + CU.GAP
    local rot = d and d.rotation and d.rotation[cls] and d.rotation[cls][spec]
    if rot and rot.note and rot.note ~= "" then
        y = PutLabel(rot.note, C_DIM, y, 0, TT.FULL_W - 2 * CU.PAD)
        y = y + CU.GAP
    end
    local colW = math.floor((TT.FULL_W - CU.CARD_GAP) / 2)
    local colX = colW + CU.CARD_GAP
    local yHdr = PutLabel(L["单体目标"], C_TEXT, y, 0, colW)
    local yAoe = PutLabel(L["多目标"], C_TEXT, y, colX, colW)
    if not rot then
        yHdr = PutLabel(L["暂无输出循环数据"], C_GREY, yHdr, 0, colW)
        yAoe = PutLabel(L["暂无输出循环数据"], C_GREY, yAoe, colX, colW)
        Finish(math.max(yHdr, yAoe), CU.ROW_MAX)
        return
    end
    for _, e in ipairs(rot.st or {}) do
        yHdr = PutRow(SpellEntry(d, cls, e), 0, colW, yHdr)
    end
    local aoe = rot.aoe or {}
    if #aoe == 0 then
        yAoe = PutLabel(L["暂无 AOE 循环数据"], C_DIM, yAoe, colX, colW)
    else
        for _, e in ipairs(aoe) do
            yAoe = PutRow(SpellEntry(d, cls, e), colX, colW, yAoe)
        end
    end
    Finish(math.max(yHdr, yAoe), CU.ROW_MAX)
end

local function LayoutCard(fr, card, y)
    fr:Show()
    fr:SetWidth(CARD_W)
    fr.__tex:SetTexture(card.icon or FALLBACK_ICON)
    fr.__name:SetText(card.name)
    fr.__name:SetTextColor(card.color[1], card.color[2], card.color[3])
    fr.__name:SetWidth(CARD_IN - CU.CARD_ICON - 8 - CU.DET_W - 8)
    if card.state then
        fr.__chipFS:SetText(card.state)
        if DG.BadgeTint then DG.BadgeTint(fr.__chip, card.color) end
        local cw = tonumber(fr.__chipFS:GetStringWidth()) or 40
        fr.__chip:SetWidth(cw + 2 * CU.CHIP_PAD)
        fr.__chip:ClearAllPoints()
        fr.__chip:SetPoint("TOPLEFT", fr, "TOPLEFT",
            CU.CARD_PAD + CU.CARD_ICON + 8, -(CU.CHIP_Y))
        fr.__chip.__tip = card.tip
        fr.__chip:Show()
    else
        fr.__chip.__tip = nil
        fr.__chip:Hide()
    end
    fr.__what:SetText("|cffffd100" .. L["用途"] .. "|r " .. (card.what or ""))
    fr.__what:ClearAllPoints()
    fr.__what:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.CARD_PAD, -(CU.WHAT_Y))
    fr.__what:Show()
    local hw = FSHeight(fr.__what)
    local boxY = CU.WHAT_Y + hw + 8
    fr.__box:ClearAllPoints()
    fr.__box:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.CARD_PAD, -boxY)
    fr.__box:SetWidth(CARD_IN)
    fr.__bodyFS:SetText(card.body or "")
    fr.__bodyFS:Show()
    local hb = FSHeight(fr.__bodyFS)
    fr.__box:SetHeight(hb + 16)
    fr.__box:Show()
    fr:SetHeight(boxY + hb + 16 + 10 + CU.CARD_BTN_H + CU.CARD_PAD)
    fr.__det.__macroName, fr.__det.__explain = card.name, card.explain
    fr.__det.__macroBody = card.body
    fr.__macroName, fr.__macroBody = card.name, card.body
    fr.__mk.__macroName, fr.__mk.__legacy, fr.__mk.__body = card.full, card.legacy, card.body
    fr.__cp.__macroName, fr.__cp.__macroBody = card.name, card.body
    fr:ClearAllPoints()
    fr:SetPoint("TOPLEFT", TT.child, "TOPLEFT", (card.col - 1) * (CARD_W + CU.CARD_GAP), -y)
    fr.__cy, fr.__ch, fr.__cgen = y, fr:GetHeight() or 0, TT.__renderGen
    return fr
end

local function MacroCard(d, cls, m)
    local body, missing = ResolveBody(d, cls, m.body or "")
    local color, state, tip
    if #missing > 0 then
        color = CU.WARN
        state = L["还缺技能"]
        tip = format(L["还缺技能：%s"], table.concat(missing, "、"))
    end
    local icon
    local firstKey = (m.body or ""):match("{(.-)}")
    if firstKey then
        local ranks = Ranks(d, cls, firstKey)
        icon = SpellIcon(KnownId(ranks) or BaseId(ranks))
    end
    local nm = m.name or ""
    return {
        name = nm,
        full = nm .. CU.MACRO_SUFFIX,
        legacy = m.legacy,
        body = body,
        what = m.what or "",
        explain = m.explain,
        missing = missing,
        color = color or CU.OK,
        state = state,
        tip = tip,
        icon = icon or "Interface\\Icons\\INV_Misc_Note_01",
    }
end

function CU.RenderMacro()
    local cls = TT.PaintHeader()
    if not cls then return end
    Ensure()
    if not CU.built then return end
    Reset()
    local d = Combat()
    local y = CU.TOP_PAD
    local list = d and d.macros and d.macros[cls]
    if not list or #list == 0 then
        y = PutLabel(L["暂无宏数据"], C_GREY, y)
        Finish(y)
        return
    end
    local row = {}
    local function flush()
        if #row == 0 then return end
        local built, maxH = {}, 0
        for i, card in ipairs(row) do
            card.col = i
            local fr = LayoutCard(CU.cards[CU.used + 1], card, y)
            CU.used = (CU.used or 0) + 1
            built[i] = fr
            local h = fr:GetHeight() or 0
            if h > maxH then maxH = h end
        end
        for i = 1, #built do
            built[i]:SetHeight(maxH)
            built[i].__ch = maxH
        end
        y = y + maxH + CU.CARD_GAP
        row = {}
    end
    local col = 0
    for _, m in ipairs(list) do
        row[#row + 1] = MacroCard(d, cls, m)
        col = col + 1
        if col >= CU.CARD_COLS then
            col = 0
            flush()
        end
    end
    flush()
    Finish(y, CU.CARD_MAX)
end
