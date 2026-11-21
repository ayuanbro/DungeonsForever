local ns = _G.DF_NS or {}

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
CU.CARD_ICON = 32
CU.CARD_BTN_H = 24
CU.DET_W = 76
CU.MK_W = 114
CU.CP_W = 60
CU.MACRO_SUFFIX = " DF"
CU.CHIP_PAD = 3
CU.CHIP_Y = CU.CARD_PAD + 20
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

local function CursorKind()
    if type(GetCursorInfo) ~= "function" then return nil end
    local ok, kind = pcall(GetCursorInfo)
    if not ok then return nil end
    return kind
end

local function PickUpMacroSlot(slot)
    if type(PickupMacro) ~= "function" then return false end
    if type(ClearCursor) == "function" then pcall(ClearCursor) end
    if not pcall(PickupMacro, slot) then return false end
    local kind = CursorKind()
    if kind == nil then return true end
    return kind == "macro"
end

local function CreateMacroNamed(name, legacy, body, icon)
    if InCombat() then
        Notify(L["战斗状态无法创建宏"])
        return
    end
    if type(CreateMacro) ~= "function" then return end
    local iconArg = icon or "INV_Misc_QuestionMark"
    local slot
    local idx = MacroIndexOf(name)
    if idx == 0 and legacy and legacy ~= "" then
        idx = MacroIndexOf(legacy)
    end
    if idx > 0 and type(EditMacro) == "function" then
        local ok, res = pcall(EditMacro, idx, name, iconArg, body)
        if not ok then
            Notify(L["创建失败：角色宏已达上限"])
            return
        end
        if type(res) == "number" and res > 0 then slot = res else slot = idx end
    else
        local ok, res = pcall(CreateMacro, name, iconArg, body, true)
        if not ok then
            Notify(L["创建失败：角色宏已达上限"])
            return
        end
        if type(res) == "number" and res > 0 then slot = res end
    end
    local function drop()
        local live = MacroIndexOf(name)
        if live <= 0 and legacy and legacy ~= "" then live = MacroIndexOf(legacy) end
        if live > 0 then slot = live end
        if not slot or slot <= 0 then
            Notify(L["创建失败：角色宏已达上限"])
            return
        end
        if PickUpMacroSlot(slot) then
            Notify(format(L["宏已就绪：%s · 拖到动作条"], name))
        else
            Notify(format(L["宏已创建：%s · 用 /macro 拖到动作条"], name))
        end
    end
    if C_Timer and type(C_Timer.After) == "function" then
        C_Timer.After(0, drop)
    else
        drop()
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
        name:SetPoint("TOPLEFT", fr, "TOPLEFT", CU.CARD_PAD + CU.CARD_ICON + 8, -CU.CARD_PAD)
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
            CreateMacroNamed(mk.__macroName, mk.__legacy, mk.__body, mk.__icon)
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
    local tw = (w or TT.FULL_W) - CU.PAD * 2 - CU.ICON - 8
    if tw < 40 then tw = 40 end
    if fr.__c.SetWidth then fr.__c:SetWidth(tw) end
    if fr.__d.SetWidth then fr.__d:SetWidth(tw) end
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
    y = PutLabel(L["自上而下 = 优先级，用第一个就绪的"] .. L["，"] .. L["金色 = 以后才解锁"]
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
    fr.__mk.__icon = card.icon
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
        tip = format(L["还缺技能：%s"], table.concat(missing, L["、"]))
    end
    local icon
    local firstKey = (m.body or ""):match("{(.-)}")
    if firstKey then
        local ranks = Ranks(d, cls, firstKey)
        local tex = SpellIcon(KnownId(ranks) or BaseId(ranks))
        if tex and tex ~= FALLBACK_ICON then icon = tex end
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
        icon = icon,
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

local CB = ns.ClassBisUI or {}
ns.ClassBisUI = CB

local Host2 = ns.ProfHost
local MakeFS2, NewButton2 = Host2.MakeFS, Host2.NewButton
local GOLD, GREY, DIM, TXT = Host2.C_GOLD, Host2.C_GREY, Host2.C_DIM, Host2.C_TEXT

local function T(key, dflt)
    local v = L[key]
    if type(v) == "string" and v ~= "" then return v end
    return dflt
end

CB.MAX_SLOT = 17
CB.MAX_OPT = 18
CB.OPT_ROWS = 5
CB.OPT_MIN_H = 46
CB.OPT_MAX_H = 53
CB.BOX_MIN = 140
CB.TIER_F = 8
CB.KV_MAX = 7
CB.GAP = 8
CB.LABEL_W = 68
CB.MAT_PER_ROW = 2
CB.MAT_ROWS = 4
CB.MAT_MAX = CB.MAT_PER_ROW * CB.MAT_ROWS
CB.MAT_ROW_H = 26
CB.MAT_TEXT_DY = math.floor((CB.MAT_ROW_H - 12) / 2 + 0.5)
CB.MAT_GAP = 8
CB.MAT_ICON = 16
CB.MAT_NAME_X = 20
CB.MAT_CNT_W = 26
CB.TAG_GAP = 8
CB.LEFT_W = 420
CB.PIN_W = 56
CB.BTN_H = 24
CB.ICON = 32
CB.SEL_H = 24
CB.SEL_GAP = 8
CB.SEL_MAX = 6
CB.CELL_MIN = 40
local RIGHT_W = tonumber(TT.RIGHT_W) or 319
CB.RIGHT_W = RIGHT_W
CB.BOX_W = math.max(200, RIGHT_W - CB.LEFT_W - CB.GAP)
CB.MAT_X = 10 + CB.LABEL_W
CB.INNER_W = math.max(120, RIGHT_W - 10 - CB.LABEL_W - 10)
CB.BOX_IN_W = math.max(96, CB.BOX_W - 10 - CB.LABEL_W - 10)
CB.VAL_W = CB.BOX_IN_W
CB.MAT_W = math.max(96, math.floor((CB.BOX_IN_W - CB.MAT_GAP) / CB.MAT_PER_ROW) - 1)
CB.MAT_PITCH = CB.MAT_W + CB.MAT_GAP
CB.MAT_CNT_X = CB.MAT_W - CB.MAT_CNT_W - 3
CB.MAT_NAME_W = math.max(36, math.min(60, CB.MAT_CNT_X - CB.MAT_NAME_X - 2))
local CNT_GREY = { 0x8a / 255, 0x94 / 255, 0xa2 / 255 }
local TIMES = T("×", "×")

CB.TAG_INK = {
    b = { 0.86, 0.70, 1.00 }, q = { 1.00, 0.82, 0.36 },
    c = { 0.40, 0.95, 0.78 }, v = { 1.00, 0.58, 0.42 },
}
CB.TAG_INK_N = { 0.62, 0.62, 0.68 }
CB.QCOL = {
    [5] = { 1.00, 0.50, 0.00 }, [4] = { 0.64, 0.21, 0.93 },
    [3] = { 0.00, 0.44, 0.87 }, [2] = { 0.12, 1.00, 0.00 },
    [1] = { 1.00, 1.00, 1.00 }, [0] = { 0.62, 0.62, 0.62 },
}
CB.SLOT_ZH = {
    head = T("头部", "头部"), neck = T("颈部", "颈部"), shoulder = T("肩部", "肩部"),
    back = T("背部", "背部"), chest = T("胸部", "胸部"), wrist = T("手腕", "手腕"),
    hands = T("手部", "手部"), waist = T("腰部", "腰部"), legs = T("腿部", "腿部"),
    feet = T("脚", "脚"), finger = T("戒指", "戒指"), finger2 = T("戒指", "戒指"),
    trinket = T("饰品", "饰品"), trinket2 = T("饰品", "饰品"),
    ["two-hand"] = T("双手武器", "双手武器"), main = T("主手", "主手"),
    off = T("副手", "副手"), ranged = T("远程", "远程"),
}
CB.COL_L = { "head", "neck", "shoulder", "back", "chest", "wrist" }
CB.COL_W = { "main", "off", "ranged" }
CB.COL_R = { "hands", "waist", "legs", "feet", "finger", "finger2", "trinket", "trinket2" }
CB.SLOT_LEFT = {}
for _, k in ipairs(CB.COL_L) do CB.SLOT_LEFT[#CB.SLOT_LEFT + 1] = k end
for _, k in ipairs(CB.COL_W) do CB.SLOT_LEFT[#CB.SLOT_LEFT + 1] = k end
CB.SLOT_RIGHT = {}
for _, k in ipairs(CB.COL_R) do CB.SLOT_RIGHT[#CB.SLOT_RIGHT + 1] = k end
CB.KIND = { b = T("掉落", "掉落"), q = T("任务", "任务"), c = T("制造", "制造"),
            v = T("商人", "商人"), r = T("稀有", "稀有"), w = T("世界", "世界"),
            n = T("未知", "未知") }

CB.TIER_ZH = {
    T("最佳", "最佳"), T("优异", "优异"), T("良好", "良好"),
    T("备选", "备选"), T("其他", "其他"),
}
CB.TIER_INK = {
    { 0.95, 0.78, 0.35 }, { 0.72, 0.48, 0.95 }, { 0.35, 0.68, 1.00 },
    { 0.45, 0.85, 0.55 }, { 0.62, 0.62, 0.68 },
}

CB.SRC_CAT = {
    ["专业制作"] = "c", ["任务奖励"] = "q", ["商人"] = "v",
    ["世界掉落"] = "w", ["首领掉落"] = "b", ["任何敌人"] = "b",
    ["Tribute"] = "b", ["稀有"] = "b",
    -- 英文数据的来源前缀 / English source prefixes
    ["Crafted"] = "c", ["Quest reward"] = "q", ["Quest:"] = "q", ["Vendor"] = "v",
    ["World drop"] = "w", ["Boss drop"] = "b", ["Any enemy"] = "b", ["Rare spawn"] = "b", ["Rare"] = "b",
}

function CB.GearSrcRaw(id)
    local n = tonumber(id)
    if not n then return nil end
    local fix = ns.BisSrcFix
    if type(fix) == "table" then
        local v0 = fix[n]
        if type(v0) == "string" and v0 ~= "" then return v0 end
    end
    local src = nil
    if type(ns.EnsureGearSrc) == "function" then
        local ok, t = pcall(ns.EnsureGearSrc)
        if ok and type(t) == "table" then src = t end
    end
    if type(src) ~= "table" and type(ns.GearSrc) == "table" then src = ns.GearSrc end
    if type(src) == "table" then
        local v = src[n]
        if type(v) == "string" and v ~= "" then return v end
    end
    local gd = nil
    if type(ns.GearData) == "table" then gd = ns.GearData end
    if type(gd) == "table" and type(gd.items) == "table" then
        local v2 = gd.items[n]
        if type(v2) == "string" and v2 ~= "" then return v2 end
    end
    return nil
end

function CB.GearSrc(id)
    local raw = CB.GearSrcRaw(id)
    if type(raw) ~= "string" then return nil end
    local segs = {}
    for s in string.gmatch(raw .. "|", "([^|]*)|") do
        local t = s:gsub("^%s+", ""):gsub("%s+$", "")
        if t ~= "" then segs[#segs + 1] = t end
    end
    if #segs == 0 then return nil end
    local kind, detail = nil, nil
    for i = 1, #segs do
        local s = segs[i]
        local hit = nil
        if CB.SRC_CAT[s] then
            hit = s
        else
            for cat in pairs(CB.SRC_CAT) do
                if s:sub(1, #cat) == cat then hit = cat break end
            end
        end
        if hit then
            kind = CB.SRC_CAT[hit]
            local rest = s:sub(#hit + 1):gsub("^[·:：%s]+", "")
            if rest ~= "" then
                detail = (detail and (detail .. "|" .. rest)) or rest
            end
        else
            detail = (detail and (detail .. "|" .. s)) or s
        end
    end
    if kind == "b" and detail then
        local m1, m2 = detail:match("^(.-)·(.*)$")
        if m1 and m1 ~= "" then return "b", m1, (m2 or "") end
        return "b", detail, ""
    end
    if kind then return kind, detail or "", "" end
    if #segs == 2 then return "b", segs[2], segs[1] end
    return "n", segs[1], ""
end

local function QColor(q)
    local c = CB.QCOL[tonumber(q) or 0] or CB.QCOL[0]
    return c[1], c[2], c[3]
end

local SRC_TXT = {
    b = T("地下城", "地下城"), q = T("任务", "任务"), c = T("专业", "专业"),
    v = T("商人", "商人"), w = T("世界", "世界"), r = T("稀有", "稀有"),
}
local SRC_CHIP = {
    b = T("地下城", "地下城"), q = T("任务", "任务"), c = T("专业", "专业"),
    v = T("商人", "商人"), w = T("世界", "世界"), r = T("稀有", "稀有"),
}
local SRC_INK = {
    b = CB.QCOL[3], q = CB.TAG_INK.q, c = CB.QCOL[5],
    v = CB.QCOL[2], w = CB.QCOL[0], r = CB.QCOL[4],
}
local SRC_INK_N = CB.QCOL[0]

local function PaintSrcTag(bt, k)
    local txt = SRC_TXT[k] or T("未知", "未知")
    local ink = SRC_INK[k] or SRC_INK_N
    local hui = ns.hui
    if bt.tag and hui and hui.PaintSolidChip then
        hui.PaintSolidChip(bt.tag, txt, ink, nil, 12)
        bt.tag:ClearAllPoints()
        bt.tag:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -8, -8)
        bt.tag:Show()
        if bt.tagTxt then bt.tagTxt:Hide() end
    elseif bt.tagTxt then
        bt.tagTxt:SetText(txt)
        bt.tagTxt:SetTextColor(ink[1], ink[2], ink[3])
        bt.tagTxt:ClearAllPoints()
        bt.tagTxt:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -10, -8)
        bt.tagTxt:Show()
    end
end

local function Card(fr, r, base)
    if ns.hui and ns.hui.HuiCardFX then
        ns.hui.HuiCardFX(fr, r or 6, base or 2)
    else
        fr:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                         edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        fr:SetBackdropColor(1, 1, 1, 0.04)
        fr:SetBackdropBorderColor(1, 1, 1, 0.10)
    end
end

local function Ensure()
    if CB.built then return end
    local child = TT.child
    if not child then return end
    CB.built = true

    local fr = CreateFrame("Frame", nil, child)
    fr:SetWidth(TT.RIGHT_W)
    fr:Hide()
    CB.frame = fr
    CB.slotIdx = CB.slotIdx or 1
    CB.optIdx = CB.optIdx or 1

    CB.slots = {}
    for i = 1, CB.MAX_SLOT do
        local bt = CreateFrame("Button", nil, fr, "BackdropTemplate")
        bt:RegisterForClicks("LeftButtonUp")
        bt:Hide()
        Card(bt, 6, 2)
        bt.ic = bt:CreateTexture(nil, "ARTWORK")
        bt.ic:SetSize(CB.ICON, CB.ICON)
        bt.ic:SetPoint("LEFT", bt, "LEFT", 8, 0)
        bt.ic:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        bt.ic:SetTexture(FALLBACK_ICON)
        bt.nm = MakeFS2(bt, 14, TXT, "LEFT")
        bt.nm:SetWordWrap(false)
        bt.sub = MakeFS2(bt, 12, GREY, "LEFT")
        bt.sub:SetWordWrap(false)
        bt:SetScript("OnEnter", function(self)
            self.__hover = true
            CB.PaintState(self)
            CB.Tip(self, true)
        end)
        bt:SetScript("OnLeave", function(self)
            self.__hover = false
            CB.PaintState(self)
            CB.Tip(self, false)
        end)
        bt:SetScript("OnClick", function(self, button)
            if CB.ModClick(self, button) then return end
            if self.__idx then
                CB.slotIdx = self.__idx
                CB.optIdx = 1
                CB.Paint()
            end
        end)
        CB.slots[i] = bt
    end

    CB.selRow = CreateFrame("Frame", nil, fr)
    CB.selRow:SetSize(CB.LEFT_W, CB.SEL_H)
    CB.selRow:Hide()
    CB.selLb = MakeFS2(CB.selRow, 14, GREY, "LEFT")
    CB.selLb:SetPoint("LEFT", CB.selRow, "LEFT", 10, 0)
    CB.selLb:SetText(T("方案选择", "方案选择"))
    CB.selLb:Hide()
    CB.selBtns = {}
    for i = 1, CB.SEL_MAX do
        local bt = NewButton2(CB.selRow, "", 60, CB.SEL_H, 12)
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            local idx = self.__idx
            if not idx or idx == CB.presetIdx then return end
            CB.presetIdx = idx
            CB.slotIdx = 1
            CB.optIdx = 1
            CB.optFocus = nil
            CB.Paint()
        end)
        CB.selBtns[i] = bt
    end

    if not CB.optView then
        local v = CreateFrame("Frame", nil, fr)
        if v.SetClipsChildren then v:SetClipsChildren(true) end
        v:EnableMouseWheel(true)
        v:SetScript("OnMouseWheel", function(_, delta)
            if not CB.optWheel then return end
            CB.optWheel(delta)
        end)
        CB.optView = v
    end
    CB.opts = {}
    for i = 1, CB.MAX_OPT do
        local bt = CreateFrame("Button", nil, CB.optView, "BackdropTemplate")
        bt:RegisterForClicks("LeftButtonUp")
        bt:Hide()
        Card(bt, 6, 2)
        bt.rk = MakeFS2(bt, 11, DIM, "LEFT")
        bt.rk:SetPoint("LEFT", bt, "LEFT", 10, 0)
        bt.rk:SetWidth(34)
        bt.ic = bt:CreateTexture(nil, "ARTWORK")
        bt.ic:SetSize(CB.ICON, CB.ICON)
        bt.ic:SetPoint("LEFT", bt, "LEFT", 46, 0)
        bt.ic:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        bt.ic:SetTexture(FALLBACK_ICON)
        bt.nm = MakeFS2(bt, 14, TXT, "LEFT")
        bt.nm:SetWordWrap(false)
        bt.nm:SetPoint("TOPLEFT", bt, "TOPLEFT", 84, -13)
        bt.src = MakeFS2(bt, 12, GREY, "LEFT")
        bt.src:SetWordWrap(false)
        bt.src:SetPoint("TOPLEFT", bt, "TOPLEFT", 84, -33)
        bt.iv = MakeFS2(bt, 12, GREY, "RIGHT")
        bt.iv:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -10, 8)
        bt.tag = nil
        bt.tagTxt = MakeFS2(bt, 12, GREY, "RIGHT")
        bt.tagTxt:SetWordWrap(false)
        bt.tagTxt:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -10, -8)
        if ns.hui and ns.hui.MakeSolidChip and ns.hui.ChipH and ns.hui.PaintSolidChip then
            bt.tag = ns.hui.MakeSolidChip(bt, (bt:GetFrameLevel() or 1) + 2, ns.hui.ChipH(12))
        end
        bt:EnableMouseWheel(true)
        bt:SetScript("OnMouseWheel", function(_, delta)
            if not CB.optWheel then return end
            CB.optWheel(delta)
        end)
        bt:SetScript("OnEnter", function(self)
            self.__hover = true
            CB.PaintState(self)
            CB.Tip(self, true)
        end)
        bt:SetScript("OnLeave", function(self)
            self.__hover = false
            CB.PaintState(self)
            CB.Tip(self, false)
        end)
        bt:SetScript("OnClick", function(self, button)
            if CB.ModClick(self, button) then return end
            if self.__idx then
                CB.optIdx = self.__idx
                CB.optFocus = self.__idx
                CB.Paint()
            end
        end)
        CB.opts[i] = bt
    end

    local box = CreateFrame("Frame", nil, fr, "BackdropTemplate")
    box:SetPoint("BOTTOMLEFT", fr, "BOTTOMLEFT", 0, 0)
    box:SetPoint("BOTTOMRIGHT", fr, "BOTTOMRIGHT", 0, 0)
    Card(box, 6, 2)
    CB.box = box

    CB.boxLb = MakeFS2(box, 14, GREY, "LEFT")
    CB.boxLb:SetPoint("TOPLEFT", box, "TOPLEFT", 10, -10)
    CB.boxLb:SetText(T("来源", "来源"))
    CB.boxTitle = MakeFS2(box, 14, TXT, "LEFT")
    CB.boxTitle:SetWordWrap(false)
    CB.boxTitle:SetPoint("TOPLEFT", box, "TOPLEFT", CB.LABEL_W + 10, -10)
    CB.boxTag = MakeFS2(box, 14, TXT, "LEFT")
    CB.boxTag:SetPoint("LEFT", CB.boxTitle, "RIGHT", 8, 0)
    CB.boxChip = nil
    if ns.hui and ns.hui.MakeSolidChip and ns.hui.ChipH then
        CB.boxTag:Hide()
        CB.boxChip = ns.hui.MakeSolidChip(box, box:GetFrameLevel() + 2, ns.hui.ChipH(14))
    end
    CB.boxMeta = MakeFS2(box, 12, GREY, "LEFT")
    CB.boxMeta:SetWordWrap(false)
    local metaDY = 0
    if CB.boxChip and ns.hui and ns.hui.ChipDY then metaDY = -ns.hui.ChipDY(14) end
    CB.boxMeta:SetPoint("LEFT", CB.boxChip or CB.boxTag, "RIGHT", 8, metaDY)
    CB.boxMeta:SetPoint("RIGHT", box, "RIGHT", -10, 0)
    CB.boxMeta:SetJustifyH("LEFT")

    local bob = CreateFrame("Button", nil, box)
    bob:SetFrameLevel(box:GetFrameLevel() + 6)
    bob:EnableMouse(true)
    bob:Hide()
    bob:SetScript("OnClick", function(self)
        if self.__dz then CB.JumpBoss(self.__dz, self.__boss) end
    end)
    bob:SetScript("OnEnter", function(self)
        if self.__txt then self.__txt:SetTextColor(1.00, 0.72, 0.24) end
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(self.__boss or "", 1, 1, 1, true)
        GameTooltip:AddLine(T("点击在地图上查看该首领", "点击在地图上查看该首领"), 0.7, 0.7, 0.7, true)
        GameTooltip:Show()
    end)
    bob:SetScript("OnLeave", function(self)
        if self.__txt then self.__txt:SetTextColor(1.00, 0.86, 0.40) end
        if GameTooltip then GameTooltip:Hide() end
    end)
    CB.bossHit = bob

    CB.kv = {}
    for i = 1, CB.KV_MAX do
        local k = MakeFS2(box, 14, GREY, "LEFT")
        local v = MakeFS2(box, 14, TXT, "LEFT")
        v:SetWordWrap(false)
        v:SetWidth(CB.VAL_W)
        CB.kv[i] = { k = k, v = v }
    end

    CB.matLb = MakeFS2(box, 14, GREY, "LEFT")
    CB.matLb:SetText(T("材料", "材料"))
    CB.matLb:Hide()
    CB.matHost = CreateFrame("Frame", nil, box)
    CB.matHost:SetHeight(1)
    CB.mats = {}
    for i = 1, CB.MAT_MAX do
        local fr = CreateFrame("Frame", nil, CB.matHost)
        fr:SetSize(CB.MAT_W, CB.MAT_ROW_H)
        fr.ic = fr:CreateTexture(nil, "ARTWORK")
        fr.ic:SetSize(CB.MAT_ICON, CB.MAT_ICON)
        fr.ic:SetPoint("LEFT", fr, "LEFT", 0, 0)
        fr.ic:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        fr.ic:SetTexture(FALLBACK_ICON)
        fr.nm = MakeFS2(fr, 12, TXT, "LEFT")
        fr.nm:SetWordWrap(false)
        fr.nm:SetWidth(CB.MAT_NAME_W)
        fr.nm:SetPoint("LEFT", fr, "LEFT", CB.MAT_NAME_X, 0)
        fr.cnt = MakeFS2(fr, 12, CNT_GREY, "RIGHT")
        fr.cnt:SetWordWrap(false)
        fr.cnt:SetWidth(CB.MAT_CNT_W)
        fr.cnt:SetPoint("RIGHT", fr, "RIGHT", -3, 0)
        fr:EnableMouse(true)
        fr:SetScript("OnEnter", function(self) CB.MatTip(self, true) end)
        fr:SetScript("OnLeave", function(self) CB.MatTip(self, false) end)
        fr:Hide()
        CB.mats[i] = fr
    end

    CB.qrow = {}
    CB.pin = {}
    for i = 1, 2 do
        local fs = MakeFS2(box, 14, TXT, "LEFT")
        fs:SetWordWrap(false)
        CB.qrow[i] = fs
        local bt = NewButton2(box, T("地图", "地图"), CB.PIN_W, CB.BTN_H, 14)
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            if self.__mark then self.__mark() end
        end)
        CB.pin[i] = bt
    end

    CB.empty = CreateFrame("Frame", nil, fr, "BackdropTemplate")
    Card(CB.empty, 6, 2)
    CB.empty:SetFrameLevel((fr:GetFrameLevel() or 1) + 3)
    CB.empty:Hide()
    CB.emptyMain = MakeFS2(CB.empty, 14, TXT, "CENTER")
    CB.emptyMain:SetPoint("CENTER", CB.empty, "CENTER", 0, 10)
    CB.emptyMain:SetText(T("待补充", "待补充"))
    CB.emptySub = MakeFS2(CB.empty, 12, GREY, "CENTER")
    CB.emptySub:SetPoint("TOP", CB.emptyMain, "BOTTOM", 0, -6)
    CB.emptySub:SetText(T("该专精暂无方案", "该专精暂无方案"))

    CB.jump = NewButton2(box, "", 160, CB.BTN_H, 14)
    CB.jump:SetScript("OnClick", function(self)
        if self.__q then CB.JumpSearch(self.__q) end
    end)
end

function CB.JumpSearch(target)
    if type(target) ~= "table" then return end
    if ns.ModuleOn and not ns.ModuleOn("QuestSearch") then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame,
                  T("搜索模块未启用，暂时无法跳转", "搜索模块未启用，暂时无法跳转"), 1, 0.82, 0.35)
        end
        return
    end
    ns.OpenPage("QuestSearch")
    local QS = ns.QuestSearchModule
    if QS and QS.OpenAt then QS.OpenAt(target.id, target.kind, target.text) end
end

local function SlugOf(cls)
    return string.lower(tostring(cls or ""))
end

local function SpecList(slug)
    local d = ns.BisPre
    if not d or not d.classes then return nil end
    for _, c in ipairs(d.classes) do
        if c.slug == slug then return c.specs end
    end
    return nil
end

function CB.SlotUnion(slug)
    local u = {}
    local list = SpecList(slug)
    if not list then return u end
    for _, sp in ipairs(list) do
        for k, v in pairs(sp.slots or {}) do
            if type(v) == "table" and #v > 0 then u[k] = true end
        end
    end
    return u
end

local function SlotCols(sp, slug)
    local u = CB.SlotUnion(slug)
    local left, right = {}, {}
    for _, k in ipairs(CB.COL_L) do if u[k] then left[#left + 1] = k end end
    for _, k in ipairs(CB.COL_W) do if u[k] then left[#left + 1] = k end end
    for _, k in ipairs(CB.COL_R) do if u[k] then right[#right + 1] = k end end
    return left, right
end

CB.RESOLVED = {}

function CB.Resolvable(id)
    local n = tonumber(id)
    if not n then return false end
    local hit = CB.RESOLVED[n]
    if hit ~= nil then return hit end
    if not (C_Item and type(C_Item.GetItemInfoInstant) == "function") then return true end
    local ok, info = pcall(C_Item.GetItemInfoInstant, n)
    local live = (ok and info ~= nil) and true or false
    CB.RESOLVED[n] = live
    return live
end

function CB.ItemMeta(id)
    local n = tonumber(id)
    if not n then return 0, 0 end
    local ok, _, _, quality, ilvl = pcall(GetItemInfo, n)
    if ok then
        local q = tonumber(quality) or 0
        local lv = tonumber(ilvl) or 0
        if q > 0 or lv > 0 then return q, lv end
    end
    if C_Item and type(C_Item.GetItemQualityByID) == "function" then
        local ok2, q2 = pcall(C_Item.GetItemQualityByID, n)
        if ok2 then return tonumber(q2) or 0, 0 end
    end
    return 0, 0
end

function CB.PresetList(slug, key)
    local d = ns.BisPreset
    if type(d) ~= "table" then return nil end
    for i = 1, #d do
        local c = d[i]
        if type(c) == "table" and c.slug == slug and type(c.specs) == "table" then
            for j = 1, #c.specs do
                local sp = c.specs[j]
                if type(sp) == "table" and sp.key == key and type(sp.presets) == "table" then
                    return sp.presets
                end
            end
        end
    end
    return nil
end

function CB.RankList(slug, specKey, slotKey)
    local d = ns.BisRank
    if type(d) ~= "table" or type(slug) ~= "string" or type(slotKey) ~= "string" then return nil end
    local cls = d[slug]
    if type(cls) ~= "table" then return nil end
    local cands = { specKey }
    local m = CB.SPEC_ALIAS[slug]
    if type(m) == "table" then
        if m[specKey] then cands[#cands + 1] = m[specKey] end
        for k, v in pairs(m) do
            if v == specKey then cands[#cands + 1] = k end
        end
    end
    local seen = {}
    for i = 1, #cands do
        local sk = cands[i]
        if type(sk) == "string" and not seen[sk] then
            seen[sk] = true
            local sp = cls[sk]
            if type(sp) == "table" then
                local pool = sp[slotKey]
                if type(pool) == "table" and #pool > 0 then return pool end
            end
        end
    end
    return nil
end

CB.optFocus = nil
CB.optKey = nil
CB.SPEC_ALIAS = { druid = { feral = "cat" } }

function CB.WantKey(slug, want)
    if type(want) ~= "string" then return want end
    local m = CB.SPEC_ALIAS[slug]
    if type(m) == "table" and m[want] then return m[want] end
    return want
end

function CB.PresetLabel(preset)
    if type(preset) == "table" and type(preset.label) == "string" and preset.label ~= "" then
        return preset.label
    end
    return T("团本前推荐", "Pre-Raid Recommended")
end

function CB.PresetCols(preset)
    local u = {}
    if type(preset) == "table" then
        if type(preset.items) == "table" then
            for k in pairs(preset.items) do u[k] = true end
        end
        if type(preset.missingSlots) == "table" then
            for i = 1, #preset.missingSlots do u[preset.missingSlots[i]] = true end
        end
    end
    local left, right = {}, {}
    for _, k in ipairs(CB.COL_L) do if u[k] then left[#left + 1] = k end end
    for _, k in ipairs(CB.COL_W) do if u[k] then left[#left + 1] = k end end
    for _, k in ipairs(CB.COL_R) do if u[k] then right[#right + 1] = k end end
    return left, right
end


local function NameOf(id)
    local n = C_Item and C_Item.GetItemNameByID and C_Item.GetItemNameByID(id)
    if type(n) == "string" and n ~= "" then return n end
    local ok, n2 = pcall(GetItemInfo, id)
    if ok and type(n2) == "string" and n2 ~= "" then return n2 end
    return format("#%d", id)
end

local function ItemIcon(id)
    if id == nil then return FALLBACK_ICON end
    if C_Item and type(C_Item.GetItemIconByID) == "function" then
        local ok, ic = pcall(C_Item.GetItemIconByID, id)
        if ok and type(ic) == "number" and ic ~= 0 then return ic end
    end
    if type(GetItemIcon) == "function" then
        local ok, ic = pcall(GetItemIcon, id)
        if ok and type(ic) == "number" and ic ~= 0 then return ic end
    end
    return FALLBACK_ICON
end

local PROF_ZH = {
    alchemy = T("炼金", "炼金"), blacksmithing = T("锻造", "锻造"),
    enchanting = T("附魔", "附魔"), engineering = T("工程学", "工程学"),
    leatherworking = T("制皮", "制皮"), tailoring = T("裁缝", "裁缝"),
    cooking = T("烹饪", "烹饪"), poisons = T("毒药", "毒药"),
    comprehension = T("理解", "理解"), ["first-aid"] = T("急救", "急救"),
}
local PROF_SLUGS = {
    "alchemy", "blacksmithing", "enchanting", "engineering", "leatherworking",
    "tailoring", "cooking", "poisons", "comprehension", "first-aid",
}
local RECIPE_CACHE = {}

local function RecipeOf(itemID)
    local id = tonumber(itemID)
    if not id then return nil end
    local hit = RECIPE_CACHE[id]
    if hit ~= nil then
        if hit == false then return nil end
        return hit
    end
    local db = ns.ProfRecipes
    if type(db) ~= "table" then return nil end
    for i = 1, #PROF_SLUGS do
        local slug = PROF_SLUGS[i]
        local g = db[slug]
        local rows = (type(g) == "table") and g.rows or nil
        if type(rows) == "table" then
            for j = 1, #rows do
                local r = rows[j]
                if type(r) == "table" and tonumber(r[2]) == id then
                    local rec = { slug = slug, skill = tonumber(r[7]) or 0, mats = r[12] }
                    RECIPE_CACHE[id] = rec
                    return rec
                end
            end
        end
    end
    RECIPE_CACHE[id] = false
    return nil
end

local BOSS_NPC = {}

local function BossNpcOf(name)
    if type(name) ~= "string" or name == "" then return nil end
    local hit = BOSS_NPC[name]
    if hit ~= nil then
        if hit == false then return nil end
        return hit
    end
    local db = ns.DungeonLoot
    if type(db) ~= "table" then return nil end
    for _, list in pairs(db) do
        if type(list) == "table" then
            for i = 1, #list do
                local row = list[i]
                if type(row) == "table" and row[2] == name then
                    local npc = tonumber(row[4])
                    if npc then
                        BOSS_NPC[name] = npc
                        return npc
                    end
                end
            end
        end
    end
    BOSS_NPC[name] = false
    return nil
end

CB.BOSS_MAP = {}

function CB.BossMapOf(dz, name)
    if type(name) ~= "string" or name == "" then return nil end
    local key = tostring(dz or "") .. "\1" .. name
    local hit = CB.BOSS_MAP[key]
    if hit ~= nil then
        if hit == false then return nil end
        return hit[1], hit[2]
    end
    local db = ns.DungeonLoot
    if type(db) ~= "table" then return nil end
    local M = ns.MapModule
    local fb
    for slug, list in pairs(db) do
        if type(list) == "table" then
            for i = 1, #list do
                local row = list[i]
                if type(row) == "table" and row[2] == name and type(row[1]) == "string" then
                    if type(dz) == "string" and dz ~= "" then
                        local d = M and M.DetailOf and M.DetailOf(slug)
                        if d and d.name == dz then
                            CB.BOSS_MAP[key] = { slug, row[1] }
                            return slug, row[1]
                        end
                    end
                    fb = fb or { slug, row[1] }
                end
            end
        end
    end
    if fb then
        CB.BOSS_MAP[key] = fb
        return fb[1], fb[2]
    end
    CB.BOSS_MAP[key] = false
    return nil
end

function CB.JumpBoss(dz, name)
    local slug, en = CB.BossMapOf(dz, name)
    if not (slug and en) then return false end
    local U = ns.DungeonUI
    if U and U.SwitchSub then pcall(U.SwitchSub, U, "Dungeons") end
    local M = ns.MapModule
    if M and M.GotoDungeon then pcall(M.GotoDungeon, slug) end
    if M and M.Select and M.detailEn ~= en then pcall(M.Select, en) end
    if ns.PlaySound then pcall(ns.PlaySound, 1) end
    return true
end

function CB.Owned(id)
    if type(id) ~= "number" then return false end
    local ci = _G.C_Item
    if ci then
        if ci.IsEquippedItem then
            local ok, r = pcall(ci.IsEquippedItem, id)
            if ok and r then return true end
        end
        if ci.GetItemCount then
            local ok, n = pcall(ci.GetItemCount, id, true, false, false)
            if ok and (tonumber(n) or 0) > 0 then return true end
        end
    end
    return false
end

local function AHBridge()
    local RA = ns.ProfRouteAuto
    if type(RA) ~= "table" then return nil end
    return RA
end

local function AHOpen()
    local RA = AHBridge()
    if not (RA and RA.Available) then return false end
    local ok, v = pcall(RA.Available)
    return (ok and v) and true or false
end

local function Money(cu)
    local RA = AHBridge()
    if not (RA and RA.MoneyStr) then return nil end
    local v = tonumber(cu)
    if not v then return nil end
    local ok, s = pcall(RA.MoneyStr, v, "copper")
    if ok and type(s) == "string" and s ~= "" then return s end
    return nil
end

local function AHPriceOf(id)
    local RA = AHBridge()
    if not (RA and RA.AHPriceOf) then return nil end
    local ok, p = pcall(RA.AHPriceOf, id)
    if not ok then return nil end
    local v = tonumber(p)
    if v and v > 0 then return v end
    return nil
end

local function MatCost(mats)
    local RA = AHBridge()
    if not (RA and RA.MatListCost) then return nil, 0 end
    if type(mats) ~= "table" or #mats == 0 then return nil, 0 end
    local ok, total, unpriced = pcall(RA.MatListCost, mats)
    if not ok then return nil, 0 end
    return tonumber(total), tonumber(unpriced) or 0
end

local function MatCells(mats)
    local out = {}
    if type(mats) ~= "table" then return out end
    for i = 1, #mats do
        local m = mats[i]
        local id = (type(m) == "table") and tonumber(m[1]) or tonumber(m)
        if id and id > 0 then
            local cnt = (type(m) == "table") and (tonumber(m[2]) or 1) or 1
            out[#out + 1] = { id = id, cnt = cnt }
        end
    end
    return out
end

function CB.Hide()
    if CB.frame then CB.frame:Hide() end
end

function CB.Render()
    Ensure()
    local fr = CB.frame
    if not fr then return end
    local cls, want = TT.PaintHeader()
    if not cls then return end
    local slug = SlugOf(cls)
    local list = SpecList(slug)
    if not list then list = {} end
    CB.slug = slug
    local wantKey = CB.WantKey(slug, want)
    local pick
    for _, sp in ipairs(list) do
        if sp.key == wantKey then pick = sp.key end
    end
    if not pick then
        for _, sp in ipairs(list) do
            if sp.key == CB.skey then pick = sp.key end
        end
    end
    if pick ~= CB.skey then
        CB.skey = pick or list[1].key
        CB.optIdx = 1
        CB.optFocus = nil
        CB.presetIdx = 1
        CB.optScroll = 0
        CB.optAuto = true
    end
    if not CB.skey then CB.skey = list[1].key end
    CB.presetIdx = CB.presetIdx or 1

    local H = (Host2.CONTENT_H or 648) - TT.MODE_TOP - TT.EDGE - TT.INSET
    local W = TT.RIGHT_W
    fr:ClearAllPoints()
    fr:SetPoint("TOPLEFT", TT.child, "TOPLEFT", 0, 0)
    fr:SetSize(W, H)
    fr:Show()
    if TT.child then TT.child:SetHeight(H + 8) end

    CB.specY = 0
    CB.Paint()
end

function CB.PaintSel(fr, top, presets)
    local row = CB.selRow
    if not row then
        CB.selOn = false
        return
    end
    local n = (type(presets) == "table") and #presets or 0
    if n <= 0 then
        CB.selOn = false
        row:Hide()
        CB.selLb:Hide()
        for i = 1, CB.SEL_MAX do
            local bt = CB.selBtns[i]
            bt.__idx = nil
            bt.__sel = false
            bt:Hide()
        end
        return
    end
    CB.selOn = true
    row:ClearAllPoints()
    row:SetPoint("TOPLEFT", fr, "TOPLEFT", 0, -top)
    row:SetSize(CB.LEFT_W, CB.SEL_H)
    row:Show()
    CB.selLb:Show()
    local lbW = CB.selLb.GetStringWidth and tonumber(CB.selLb:GetStringWidth()) or nil
    if not lbW or lbW <= 0 then lbW = 56 end
    local avail = CB.LEFT_W - 10 - lbW - CB.SEL_GAP - (n - 1) * CB.SEL_GAP
    local maxW = math.floor(avail / n)
    if maxW < 56 then maxW = 56 end
    local prev = CB.selLb
    for i = 1, CB.SEL_MAX do
        local bt = CB.selBtns[i]
        if i <= n then
            local txt = CB.PresetLabel(presets[i])
            bt:SetWidth(CB.LEFT_W)
            bt:SetText(txt)
            local fs = bt.GetFontString and bt:GetFontString()
            local w = nil
            if fs and fs.GetStringWidth then w = tonumber(fs:GetStringWidth()) end
            if not w or w <= 0 then w = #txt * 12 end
            w = w + 20
            if w < 56 then w = 56 end
            if w > maxW then w = maxW end
            bt:SetWidth(w)
            bt:ClearAllPoints()
            bt:SetPoint("LEFT", prev, "RIGHT", CB.SEL_GAP, 0)
            prev = bt
            bt.__idx = i
            local on = (i == CB.presetIdx)
            bt.__sel = on
            SetButtonSelected(bt, on, "tab")
            bt:Show()
        else
            bt.__idx = nil
            bt.__sel = false
            bt:Hide()
        end
    end
end

function CB.Paint()
    local fr = CB.frame
    if not fr then return end
    local list = SpecList(CB.slug)
    local sp
    if list then
        for _, v in ipairs(list) do
            if v.key == CB.skey then sp = v end
        end
    end

    local W, top = TT.RIGHT_W, CB.specY
    local H = (Host2.CONTENT_H or 648) - TT.MODE_TOP - TT.EDGE - TT.INSET - top
    CB.slotIdx = CB.slotIdx or 1
    CB.optIdx = CB.optIdx or 1
    CB.presetIdx = CB.presetIdx or 1

    local presets = sp and CB.PresetList(CB.slug, sp.key) or nil
    local preset = nil
    if presets and #presets > 0 then
        if CB.presetIdx > #presets then CB.presetIdx = 1 end
        preset = presets[CB.presetIdx]
    end

    local hasAny = false
    if preset then
        if preset.incomplete ~= true and type(preset.items) == "table" then
            for _, ids in pairs(preset.items) do
                if type(ids) == "table" then
                    for i = 1, #ids do
                        if CB.Resolvable(ids[i]) then hasAny = true break end
                    end
                end
                if hasAny then break end
            end
        end
    end
    if CB.empty then
        if hasAny then
            CB.empty:Hide()
        else
            CB.empty:ClearAllPoints()
            CB.empty:SetPoint("TOPLEFT", fr, "TOPLEFT", 0, -top)
            CB.empty:SetPoint("BOTTOMRIGHT", fr, "BOTTOMRIGHT", 0, 0)
            CB.empty:Show()
        end
    end
    if not hasAny then
        if CB.selRow then CB.selRow:Hide() end
        for i = 1, CB.MAX_SLOT do
            local bt = CB.slots[i]
            bt.__idx = nil
            bt.__it = nil
            bt.__sel = false
            bt:Hide()
        end
        for i = 1, CB.MAX_OPT do
            local bt = CB.opts[i]
            bt.__idx = nil
            bt.__it = nil
            bt.__sel = false
            bt:Hide()
        end
        if CB.optView then CB.optView:Hide() end
        if CB.optMore then CB.optMore:Hide() end
        if CB.box then CB.box:Hide() end
        CB.optScroll = 0
        CB.__maxScroll = 0
        CB.optAuto = true
        return
    end

    CB.PaintSel(fr, top, presets)
    local left, right = CB.SLOT_LEFT, CB.SLOT_RIGHT
    local cells, cn = {}, 0
    local function push(k, col, row)
        cn = cn + 1
        cells[cn] = { k = k, col = col, row = row, idx = cn }
    end
    for i, k in ipairs(left) do push(k, 0, i) end
    for i, k in ipairs(right) do push(k, 1, i) end
    local n = cn
    if n == 0 then return end
    if CB.slotIdx > n then CB.slotIdx = 1 end
    do
        local function live(k)
            if preset and type(preset.items) == "table" then
                local ids = preset.items[k]
                if type(ids) == "table" then return CB.Resolvable(ids[1]) end
            end
            return false
        end
        local cur = cells[CB.slotIdx]
        if not (cur and live(cur.k)) then
            for i = 1, n do
                if live(cells[i].k) then CB.slotIdx = i break end
            end
        end
    end
    local nrow = math.max(#left, #right)
    local cellW = math.floor((CB.LEFT_W - CB.GAP) / 2)
    local gridTop = top
    if CB.selOn then gridTop = top + CB.SEL_H + CB.SEL_GAP end
    local gH = H - (gridTop - top)
    local cellH = math.floor((gH - (nrow - 1) * CB.GAP) / nrow)
    if cellH < CB.CELL_MIN then cellH = CB.CELL_MIN end
    local iconTop = math.floor((cellH - CB.ICON) / 2)
    local txtX = 8 + CB.ICON + 6
    local txtW = cellW - txtX - 6

    local byIdx = {}
    for _, c in ipairs(cells) do byIdx[c.idx] = c end
    local boxRow = {}

    for i = 1, CB.MAX_SLOT do
        local bt = CB.slots[i]
        local c = byIdx[i]
        local key = c and c.k
        if key then
            local it = nil
            if preset and type(preset.items) == "table" then
                local ids = preset.items[key]
                local id = (type(ids) == "table") and ids[1] or nil
                if id then
                    local q, lv = CB.ItemMeta(id)
                    local k2, pl2, bs2 = CB.GearSrc(id)
                    if k2 then
                        it = { id, k2, pl2 or "", bs2 or "", lv > 0 and lv or "", q }
                    else
                        it = { id, "n", "", "", lv > 0 and lv or "", q }
                    end
                end
            else
                it = nil
            end
            bt:ClearAllPoints()
            bt:SetSize(cellW, cellH)
            bt:SetPoint("TOPLEFT", fr, "TOPLEFT",
                        c.col * (cellW + CB.GAP), -gridTop - (c.row - 1) * (cellH + CB.GAP))
            local zh = CB.SLOT_ZH[key] or key
            bt.sub:ClearAllPoints()
            bt.sub:SetPoint("TOPLEFT", bt, "TOPLEFT", txtX, -(iconTop + 20))
            bt.sub:SetWidth(txtW)
            if it then
                local nm = NameOf(it[1])
                local cr, cg, cb = QColor(it[6])
                bt.nm:ClearAllPoints()
                bt.nm:SetPoint("TOPLEFT", bt, "TOPLEFT", txtX, -iconTop)
                bt.nm:SetWidth(txtW)
                bt.nm:SetText(nm)
                bt.nm:SetTextColor(cr, cg, cb)
                bt.sub:SetText(zh)
                bt.ic:SetTexture(ItemIcon(it[1]))
                bt.ic:SetAlpha(1)
                bt.__idx = i
                bt.__it = it
                boxRow[key] = it
            else
                bt.nm:ClearAllPoints()
                bt.nm:SetPoint("TOPLEFT", bt, "TOPLEFT", txtX, -iconTop)
                bt.nm:SetWidth(txtW)
                bt.nm:SetText(T("未收录", "未收录"))
                bt.nm:SetTextColor(GREY[1], GREY[2], GREY[3])
                bt.sub:SetText(zh)
                bt.ic:SetTexture(FALLBACK_ICON)
                bt.ic:SetAlpha(0.25)
                bt.__idx = nil
                bt.__it = nil
            end
            bt.__sel = (it ~= nil and i == CB.slotIdx)
            CB.PaintState(bt)
            bt:Show()
        else
            bt.__idx = nil
            bt.__it = nil
            bt.__sel = false
            bt:Hide()
        end
    end

    local rx = CB.LEFT_W + CB.GAP
    local rw = W - rx
    local key = (byIdx[CB.slotIdx] and byIdx[CB.slotIdx].k) or cells[1].k
    if CB.optKey ~= key then
        CB.optKey = key
        CB.optFocus = nil
        CB.optScroll = 0
        CB.optAuto = true
    end
    local zh = CB.SLOT_ZH[key] or key

    local list2 = {}
    local pool = sp.slots and sp.slots[key]
    local byId = {}
    if type(pool) == "table" then
        for i = 1, #pool do
            local r = pool[i]
            if type(r) == "table" and r[1] ~= nil then byId[r[1]] = r end
        end
    end
    local ranked = CB.RankList(CB.slug, CB.skey, key)
    if type(ranked) == "table" then
        for i = 1, #ranked do
            local r = ranked[i]
            local id = (type(r) == "table") and tonumber(r[1]) or nil
            if id and CB.Resolvable(id) then
                local rec = nil
                local row = byId[id]
                if type(row) == "table" then
                    rec = {}
                    for n = 1, 7 do rec[n] = row[n] end
                else
                    local q, lv = CB.ItemMeta(id)
                    local k2, pl2, bs2 = CB.GearSrc(id)
                    if k2 then
                        rec = { id, k2, pl2 or "", bs2 or "", lv > 0 and lv or "", q }
                    else
                        rec = { id, "n", "", "", lv > 0 and lv or "", q }
                    end
                end
                rec[CB.TIER_F] = tonumber(r[2]) or 5
                list2[#list2 + 1] = rec
            end
        end
    end
    if #list2 == 0 then
        local pids = (preset and type(preset.items) == "table") and preset.items[key] or nil
        if type(pids) == "table" then
            for i = 1, #pids do
                local id = pids[i]
                if id ~= nil then
                    local r = byId[id]
                    local rec
                    if type(r) == "table" then
                        rec = {}
                        for n = 1, 7 do rec[n] = r[n] end
                    else
                        local q, lv = CB.ItemMeta(id)
                        local k2, pl2, bs2 = CB.GearSrc(id)
                        if k2 then
                            rec = { id, k2, pl2 or "", bs2 or "", lv > 0 and lv or "", q }
                        else
                            rec = { id, "n", "", "", lv > 0 and lv or "", q }
                        end
                    end
                    rec[CB.TIER_F] = 1
                    list2[#list2 + 1] = rec
                end
            end
        end
    end
    if CB.optIdx > #list2 then CB.optIdx = 1 end
    local nopt = #list2
    local vis = math.min(nopt, CB.OPT_ROWS)
    if vis < 1 then vis = 1 end
    local hintH = (nopt > vis) and 16 or 0
    local avail = H - (gridTop - top) - CB.BOX_MIN - CB.GAP - hintH
    local optH = math.floor((avail - (vis - 1) * CB.GAP) / vis)
    if optH > CB.OPT_MAX_H then optH = CB.OPT_MAX_H end
    if optH < CB.OPT_MIN_H then optH = CB.OPT_MIN_H end
    local optTop2 = math.floor((optH - CB.ICON) / 2)
    local listH = vis * optH + (vis - 1) * CB.GAP
    local maxScroll = math.max(0, nopt - vis)
    if CB.optAuto then
        CB.optAuto = false
        CB.optIdx = 1
        local pids0 = (preset and type(preset.items) == "table") and preset.items[key] or nil
        local pid0 = (type(pids0) == "table") and tonumber(pids0[1]) or nil
        if pid0 then
            for i = 1, nopt do
                if list2[i] and tonumber(list2[i][1]) == pid0 then
                    CB.optIdx = i
                    break
                end
            end
        end
        if CB.optIdx > vis then CB.optScroll = CB.optIdx - vis end
    end
    CB.optScroll = CB.optScroll or 0
    if CB.optScroll > maxScroll then CB.optScroll = maxScroll end
    if CB.optScroll < 0 then CB.optScroll = 0 end
    CB.optWheel = function(delta)
        local m = CB.__maxScroll or 0
        local s = (CB.optScroll or 0) - (delta or 0)
        if s < 0 then s = 0 end
        if s > m then s = m end
        if s ~= CB.optScroll then
            CB.optScroll = s
            CB.Paint()
        end
    end
    CB.__maxScroll = maxScroll

    local srcH = H - (gridTop - top) - listH - hintH - CB.GAP
    if srcH < CB.BOX_MIN then srcH = CB.BOX_MIN end

    CB.optView:ClearAllPoints()
    CB.optView:SetPoint("TOPLEFT", fr, "TOPLEFT", rx, -gridTop)
    CB.optView:SetSize(rw, listH)
    CB.optView:Show()

    if not CB.optMore then
        CB.optMore = MakeFS2(fr, 11, DIM, "RIGHT")
    end
    CB.optMore:ClearAllPoints()
    CB.optMore:SetPoint("TOPRIGHT", CB.optView, "BOTTOMRIGHT", 0, -2)
    local left2 = maxScroll - (CB.optScroll or 0)
    if left2 > 0 then
        CB.optMore:SetText(format(T("还有 %d 件", "还有 %d 件"), left2))
        CB.optMore:Show()
    else
        CB.optMore:Hide()
    end

    CB.box:ClearAllPoints()
    CB.box:SetPoint("BOTTOMLEFT", fr, "BOTTOMLEFT", rx, 0)
    CB.box:SetPoint("BOTTOMRIGHT", fr, "BOTTOMRIGHT", 0, 0)
    CB.box:SetHeight(srcH)
    CB.box:Show()
    if CB.optFocus and not list2[CB.optFocus] then CB.optFocus = nil end
    for i = 1, CB.MAX_OPT do
        local bt = CB.opts[i]
        if not bt then break end
        local sidx = CB.optScroll + i
        local it = (i <= vis and sidx <= nopt) and list2[sidx] or nil
        if it then
            local nm = NameOf(it[1])
            local cr, cg, cb = QColor(it[6])
            local tier = tonumber(it[CB.TIER_F]) or 5
            bt.rk:SetText(CB.TIER_ZH[tier] or CB.TIER_ZH[5])
            local ink = CB.TIER_INK[tier] or CB.TIER_INK[5]
            bt.rk:SetTextColor(ink[1], ink[2], ink[3])
            bt.nm:ClearAllPoints()
            bt.nm:SetPoint("TOPLEFT", bt, "TOPLEFT", 84, -optTop2)
            bt.nm:SetText(nm)
            bt.nm:SetTextColor(cr, cg, cb)
            bt.src:ClearAllPoints()
            bt.src:SetPoint("TOPLEFT", bt, "TOPLEFT", 84, -(optTop2 + 20))
            bt.ic:SetTexture(ItemIcon(it[1]))
            bt.src:SetText(CB.SrcLine(it))
            local owned = CB.Owned(it[1])
            if owned then
                bt.iv:SetText(T("已拥有", "已拥有"))
                bt.iv:SetTextColor(0.42, 0.94, 0.62)
            else
                bt.iv:SetText(T("未拥有", "未拥有"))
                bt.iv:SetTextColor(GREY[1], GREY[2], GREY[3])
            end
            bt.iv:Show()
            local room = rw - 84 - 6
            local need = bt.src.GetStringWidth and bt.src:GetStringWidth() or 0
            if type(need) ~= "number" or need < 0 then need = 0 end
            local iw = bt.iv.GetStringWidth and bt.iv:GetStringWidth() or 0
            if type(iw) ~= "number" or iw < 0 then iw = 0 end
            local srcW = room
            if bt.iv:IsShown() then
                local narrowed = room - iw - 8
                if narrowed < 60 then narrowed = 60 end
                if need + 2 > narrowed and not owned then
                    bt.iv:Hide()
                else
                    srcW = narrowed
                end
            end
            if srcW < 60 then srcW = 60 end
            bt.src:SetWidth(srcW)
            PaintSrcTag(bt, it[2])
            bt:ClearAllPoints()
            bt:SetSize(rw, optH)
            bt:SetPoint("TOPLEFT", CB.optView, "TOPLEFT", 0, -(i - 1) * (optH + CB.GAP))
            bt.__idx = sidx
            bt.__it = it
            bt.__sel = (sidx == CB.optIdx)
            CB.PaintState(bt)
            bt:Show()
        else
            bt.__idx = nil
            bt.__it = nil
            bt.__sel = false
            bt:Hide()
        end
    end

    CB.PaintSrc((CB.optFocus and list2[CB.optFocus]) or list2[CB.optIdx] or boxRow[key], zh)

    if DG and DG.RequestItem then
        for i = 1, cn do
            local c = cells[i]
            local row = c and sp.slots[c.k]
            local it = row and row[1]
            if it and type(it[1]) == "number" then DG.RequestItem(it[1]) end
        end
        for i = 1, #list2 do
            local it = list2[i]
            if it and type(it[1]) == "number" then DG.RequestItem(it[1]) end
        end
    end
end

function CB.OnItemData(itemID)
    if not itemID then return end
    local fr = CB.frame
    if not (fr and fr:IsShown()) then return end
    local hit = false
    for i = 1, CB.MAX_SLOT do
        local bt = CB.slots[i]
        local it = bt and bt.__it
        if it and it[1] == itemID then hit = true break end
    end
    if not hit then
        for i = 1, CB.MAX_OPT do
            local bt = CB.opts[i]
            local it = bt and bt.IsShown and bt:IsShown() and bt.__it
            if it and it[1] == itemID then hit = true break end
        end
    end
    if not hit then return end
    if CB.__srcRepaint then return end
    CB.__srcRepaint = true
    if C_Timer and C_Timer.After then
        C_Timer.After(0.15, function()
            CB.__srcRepaint = nil
            local f2 = CB.frame
            if f2 and f2:IsShown() then pcall(CB.Paint, CB) end
        end)
    else
        CB.__srcRepaint = nil
    end
end

function CB.PaintState(bt)
    if not (ns.hui and ns.hui.HuiCardState) then return end
    ns.hui.HuiCardState(bt, (bt.__sel or bt.__hover) and "hover" or "norm")
end

function CB.Tip(bt, on)
    if not on then
        if GameTooltip then GameTooltip:Hide() end
        return
    end
    local it = bt.__it
    if not it then return end
    if DG and DG.ShowItemTip then
        pcall(DG.ShowItemTip, bt, it)
        return
    end
    if DG and DG.ShowItemTipBody then
        pcall(DG.ShowItemTipBody, bt, it)
        return
    end
    if not GameTooltip then return end
    GameTooltip:SetOwner(bt, "ANCHOR_RIGHT")
    if GameTooltip.SetHyperlink then
        pcall(GameTooltip.SetHyperlink, GameTooltip, "item:" .. tostring(it[1]))
    end
    GameTooltip:Show()
end

function CB.ModClick(bt, button)
    local it = bt.__it
    if not it then return false end
    if button and button ~= "LeftButton" then return false end
    local shift = type(IsShiftKeyDown) == "function" and IsShiftKeyDown()
    local ctrl = type(IsControlKeyDown) == "function" and IsControlKeyDown()
    if not shift and not ctrl then return false end
    if shift then
        if DG and DG.InsertItemLink then
            DG.InsertItemLink(it[1])
            return true
        end
        local link = "item:" .. tostring(it[1]) .. ":0:0:0:0:0:0:0"
        if type(ChatEdit_GetActiveWindow) == "function" and type(ChatEdit_InsertLink) == "function"
            and ChatEdit_GetActiveWindow() then
            ChatEdit_InsertLink(link)
        elseif type(ChatFrame_OpenChat) == "function" then
            ChatFrame_OpenChat(link)
        end
        return true
    end
    if DG and DG.TryOn then
        DG.TryOn(it[1])
        return true
    end
    if type(DressUpItemLink) == "function" then
        DressUpItemLink("item:" .. tostring(it[1]) .. ":0:0:0:0:0:0:0")
    end
    return true
end

function CB.SrcLine(it)
    local k = it[2]
    local p3, p4 = it[3], it[4]
    if (p3 == nil or p3 == "") and (p4 == nil or p4 == "") then
        local gk, gp, gb = CB.GearSrc(it[1])
        if gk ~= nil and gk == k then
            p3 = gp
            if gb ~= nil and gb ~= "" then p4 = gb end
        end
    end
    if k == "b" then
        if p4 and p4 ~= "" then return tostring(p3) .. " · " .. tostring(p4) end
        return tostring(p3 or "")
    elseif k == "q" then
        if it[7] and it[7][2] then return "《" .. tostring(it[7][2]) .. "》" end
        if p3 ~= nil and p3 ~= "" then return T("任务奖励", "任务奖励") .. " · " .. tostring(p3) end
        return tostring(CB.KIND.q)
    elseif k == "c" then
        if p3 ~= nil and p3 ~= "" then return tostring(p3) end
        return T("专业制造", "专业制造")
    end
    if p3 ~= nil and p3 ~= "" then return tostring(p3) end
    return tostring(CB.KIND[k] or CB.KIND.n or "")
end

function CB.PaintTag(k)
    local txt = SRC_CHIP[k] or CB.KIND[k] or CB.KIND.n
    local hui = ns.hui
    if CB.boxChip and hui and hui.PaintSolidChip then
        hui.PaintSolidChip(CB.boxChip, txt, CB.TAG_INK[k] or CB.TAG_INK_N)
        CB.boxChip:ClearAllPoints()
        CB.boxChip:SetPoint("LEFT", CB.boxTitle, "RIGHT", CB.TAG_GAP, hui.ChipDY(14))
        CB.boxChip:Show()
        CB.boxTag:Hide()
    else
        CB.boxTag:SetText(txt)
        CB.boxTag:Show()
    end
end

function CB.MatTip(fr, on)
    if not GameTooltip then return end
    if not on then
        local ok, owner = pcall(GameTooltip.GetOwner, GameTooltip)
        if not (ok and owner and owner ~= fr) then
            pcall(GameTooltip.Hide, GameTooltip)
        end
        return
    end
    local id = fr and fr.__id
    if not (type(id) == "number" and id > 0) then return end
    pcall(GameTooltip.SetOwner, GameTooltip, fr, "ANCHOR_RIGHT")
    pcall(GameTooltip.SetHyperlink, GameTooltip, "item:" .. tostring(id))
    pcall(GameTooltip.Show, GameTooltip)
end

local function FitTitle(metaTxt)
    local fs = CB.boxTitle
    if not fs then return end
    local cap = CB.BOX_IN_W
    local cw = 0
    if CB.boxChip and CB.boxChip:IsShown() then cw = CB.boxChip:GetWidth() or 0 end
    if type(cw) ~= "number" or cw <= 0 then cw = 0 end
    if cw > 0 then cap = cap - cw - CB.TAG_GAP end
    if cap < 80 then cap = 80 end
    local w = fs.GetStringWidth and fs:GetStringWidth() or 0
    if type(w) ~= "number" or w <= 0 then w = cap end
    w = w + 2
    if w > cap then w = cap end
    fs:SetWidth(w)
    CB.boxMeta:SetText("")
    CB.boxMeta:Hide()
    if type(metaTxt) ~= "string" or metaTxt == "" then return end
    local room = CB.BOX_IN_W - (w + CB.TAG_GAP + cw + 8)
    CB.boxMeta:SetText(metaTxt)
    local need = CB.boxMeta.GetStringWidth and CB.boxMeta:GetStringWidth() or 0
    if type(need) ~= "number" then need = 0 end
    if need > 0 and need <= room then
        CB.boxMeta:Show()
    else
        CB.boxMeta:SetText("")
    end
end

function CB.PaintSrc(it, zh)
    local box = CB.box
    if not it then
        box:Hide()
        return
    end
    box:Show()
    local k = it[2]
    local q = it[7]
    CB.PaintTag(k)
    CB.boxTitle:SetText(" ")
    CB.boxMeta:SetText("")
    CB.boxMeta:Hide()
    for i = 1, #CB.kv do
        local kv = CB.kv[i]
        kv.k:SetText(" ")
        kv.v:SetText(" ")
        kv.v:SetTextColor(TXT[1], TXT[2], TXT[3])
        kv.k:Hide()
        kv.v:Hide()
    end
    if CB.bossHit then CB.bossHit:Hide() end
    CB.matLb:Hide()
    for i = 1, #CB.mats do
        CB.mats[i].__id = nil
        CB.mats[i]:Hide()
    end
    for i = 1, 2 do CB.qrow[i]:SetText(" "); CB.qrow[i]:Hide(); CB.pin[i]:Hide() end
    CB.jump:Hide()
    CB.jump.__q = nil

    local place = (type(it[3]) == "string" and it[3] ~= "") and it[3] or ""
    local rows = {}
    local function KV(lb, val)
        if val ~= nil and val ~= "" then rows[#rows + 1] = { t = "kv", lb = lb, val = val } end
    end
    local function MATS(list)
        if #MatCells(list) > 0 then rows[#rows + 1] = { t = "mats", list = list } end
    end

    local isQuest = (k == "q" and q) and true or false
    if isQuest then
        CB.boxTitle:SetText("《" .. tostring(q[2] or "") .. "》")
        local meta = {}
        if q[3] and q[3] ~= "" then meta[#meta + 1] = "Lv" .. tostring(q[3]) end
        if q[4] and q[4] ~= "" then meta[#meta + 1] = tostring(q[4]) end
        FitTitle(#meta > 0 and table.concat(meta, " · ") or nil)
    else
        local ttl = place
        if k == "c" then
            ttl = T("专业制造", "专业制造")
        elseif k == "q" then
            ttl = T("任务奖励", "任务奖励")
        elseif ttl == "" then
            if k == "w" then
                ttl = T("世界掉落", "世界掉落")
            elseif k == "n" then
                ttl = T("掉落", "掉落")
            else
                ttl = CB.KIND[k] or CB.KIND.n
            end
        end
        CB.boxTitle:SetText(ttl)
        FitTitle(nil)
        if k == "q" then KV(T("地点", "地点"), place) end
        if k == "b" then
            KV(T("首领", "首领"), it[4] ~= "" and it[4] or T("该副本任意首领", "该副本任意首领"))
            if it[4] ~= "" then
                rows[#rows].boss = it[4]
            end
        end
        if k == "c" then
            local id = it[1]
            local open = AHOpen()
            local rec = RecipeOf(id)
            local total, unpriced = nil, 0
            if rec then
                local pz = PROF_ZH[rec.slug]
                local skill = tonumber(rec.skill) or 0
                if pz and pz ~= "" then
                    KV(T("专业", "专业"), format("%s · %s %d", pz, T("技能", "技能"), skill))
                end
                MATS(rec.mats)
                local costTxt = "—"
                if open then
                    total, unpriced = MatCost(rec.mats)
                    local matN = (type(rec.mats) == "table") and #rec.mats or 0
                    if total and (total > 0 or unpriced < matN) then
                        local s = Money(total)
                        if s then costTxt = (unpriced > 0 and "≈" or "") .. s end
                    end
                end
                KV(T("自造成本", "自造成本"), costTxt)
            end
            local ah = open and AHPriceOf(id) or nil
            KV(T("拍卖售价", "拍卖售价"), Money(ah) or "—")
            if ah and total and total > 0 then
                local diff = ah - total
                if diff >= 0 then
                    KV(T("差价", "差价"), "|cff40d959" .. T("省", "省") .. "|r " .. tostring(Money(diff) or ""))
                else
                    KV(T("差价", "差价"), "|cffe0685a" .. T("贵", "贵") .. "|r " .. tostring(Money(-diff) or ""))
                end
            end
        end
        if k ~= "c" then
            KV(T("部位", "部位"), zh)
        end
    end

    local TOP, ROW, QROW = 36, 26, 26
    local y0 = TOP

    if isQuest then
        local qid = q[1]
        local function Row(i, lb, nm, loc, isStart)
            local fs = CB.qrow[i]
            local txt = "|cff8a94a2" .. lb .. "：|r"
            if nm and nm ~= "" then
                txt = txt .. "|cffffd479" .. nm .. "|r"
                if loc and loc ~= "" then txt = txt .. "|cff5a6472 · |r|cff8a94a2" .. loc .. "|r" end
            else
                txt = txt .. "|cff5c6675" .. T("未记录", "未记录") .. "|r"
            end
            fs:SetText(txt)
            fs:ClearAllPoints()
            fs:SetPoint("TOPLEFT", box, "TOPLEFT", 10, -(y0 + (i - 1) * QROW))
            fs:SetWidth(math.max(80, box:GetWidth() - 78))
            fs:Show()
            local bt = CB.pin[i]
            if nm and nm ~= "" then
                bt:ClearAllPoints()
                bt:SetPoint("TOPRIGHT", box, "TOPRIGHT", -10, -(y0 + (i - 1) * QROW + 5))
                bt.__mark = function()
                    if not qid then return end
                    if isStart then
                        local sl = ns.DungeonQuestStartLoc and ns.DungeonQuestStartLoc[qid]
                        if sl then
                            DG.MarkNPC(tonumber(sl[1]), { tonumber(sl[3]), tonumber(sl[4]), tonumber(sl[5]) })
                            return
                        end
                    else
                        local en = ns.DungeonQuestEndNpc and ns.DungeonQuestEndNpc[qid]
                        if en then DG.MarkNPC(en) return end
                    end
                    if UIErrorsFrame and UIErrorsFrame.AddMessage then
                        pcall(UIErrorsFrame.AddMessage, UIErrorsFrame,
                              T("未收录该位置的地图，无法标记", "未收录该位置的地图"), 1, 0.4, 0.4)
                    end
                end
                bt:Show()
            end
        end
        Row(1, T("起始", "起始"), q[5], nil, true)
        Row(2, T("结束", "结束"), q[8], nil, false)
        CB.jump:SetText(T("在搜索中查看此任务", "在搜索中查看此任务"))
        CB.jump.__q = { id = tonumber(q[1]) or q[1], kind = "quest", text = q[2] }
    else
        local cap = CB.MAT_PER_ROW
        if cap < 1 then cap = 1 end
        local kvIdx, y = 0, y0
        for _, r in ipairs(rows) do
            if r.t == "mats" then
                local cells = MatCells(r.list)
                local n = #cells
                local maxCells = cap * CB.MAT_ROWS
                if maxCells > CB.MAT_MAX then maxCells = CB.MAT_MAX end
                if maxCells < 1 then maxCells = 1 end
                local vis, over = n, 0
                if n > maxCells then
                    vis = maxCells - 1
                    over = n - vis
                end
                local blocks = vis
                if over > 0 then blocks = vis + 1 end
                local lines = math.ceil(blocks / cap)
                if lines < 1 then lines = 1 end
                CB.matLb:ClearAllPoints()
                CB.matLb:SetPoint("LEFT", CB.mats[1].nm, "LEFT",
                                  -(CB.MAT_X + CB.MAT_NAME_X - 10), 0)
                CB.matLb:Show()
                for i = 1, CB.MAT_MAX do
                    local fr = CB.mats[i]
                    local cell = (i <= vis) and cells[i] or nil
                    local show = false
                    if cell then
                        fr.ic:Show()
                        fr.ic:SetTexture(ItemIcon(cell.id))
                        fr.nm:SetText(NameOf(cell.id))
                        if cell.cnt > 1 then
                            fr.cnt:SetText(TIMES .. tostring(cell.cnt))
                            fr.cnt:Show()
                        else
                            fr.cnt:SetText("")
                            fr.cnt:Hide()
                        end
                        fr.__id = cell.id
                        show = true
                    elseif over > 0 and i == vis + 1 then
                        fr.ic:Hide()
                        fr.nm:SetText("…+" .. tostring(over))
                        fr.cnt:SetText("")
                        fr.cnt:Hide()
                        fr.__id = nil
                        show = true
                    end
                    if show then
                        local cellW = CB.MAT_W
                        if i == blocks and (i - 1) % cap == 0 then
                            cellW = CB.MAT_W * 2 + CB.MAT_GAP
                        end
                        fr:SetWidth(cellW)
                        fr.nm:SetWidth(math.max(28, cellW - CB.MAT_NAME_X - CB.MAT_CNT_W - 5))
                        fr:ClearAllPoints()
                        fr:SetPoint("TOPLEFT", box, "TOPLEFT",
                                    CB.MAT_X + ((i - 1) % cap) * CB.MAT_PITCH,
                                    -(y + math.floor((i - 1) / cap) * CB.MAT_ROW_H
                                      - CB.MAT_TEXT_DY))
                        fr:Show()
                    else
                        fr.__id = nil
                        fr:Hide()
                    end
                end
                y = y + (lines - 1) * CB.MAT_ROW_H + ROW
            else
                kvIdx = kvIdx + 1
                local kv = CB.kv[kvIdx]
                if kv then
                    kv.k:SetText(r.lb)
                    kv.k:ClearAllPoints()
                    kv.k:SetPoint("TOPLEFT", box, "TOPLEFT", 10, -y)
                    kv.k:Show()
                    kv.v:SetText(r.val)
                    kv.v:ClearAllPoints()
                    kv.v:SetPoint("TOPLEFT", kv.k, "TOPLEFT", CB.LABEL_W, 0)
                    kv.v:SetWidth(CB.VAL_W)
                    kv.v:Show()
                    if r.boss then
                        local slug, en = CB.BossMapOf(place, r.boss)
                        if slug and en then
                            kv.v:SetTextColor(1.00, 0.86, 0.40)
                            local bob = CB.bossHit
                            bob.__dz = place
                            bob.__boss = r.boss
                            bob.__txt = kv.v
                            bob:ClearAllPoints()
                            bob:SetPoint("TOPLEFT", kv.v, "TOPLEFT", -2, 3)
                            local sw = kv.v.GetStringWidth and kv.v:GetStringWidth() or 60
                            if type(sw) ~= "number" or sw <= 0 then sw = 60 end
                            if sw > CB.BOX_IN_W then sw = CB.BOX_IN_W end
                            bob:SetSize(math.max(30, sw + 6), 18)
                            bob:Show()
                        end
                    end
                end
                y = y + ROW
            end
        end
        local boss = nil
        if k == "b" and type(it[4]) == "string" and it[4] ~= "" then
            boss = BossNpcOf(it[4])
        end
        if boss then
            CB.jump:SetText(T("在搜索中查看该首领", "在搜索中查看该首领"))
            CB.jump.__q = { id = boss, kind = "npc", text = it[4] }
        else
            CB.jump:SetText(k == "b" and T("在搜索中查看该首领", "在搜索中查看该首领")
                or T("在搜索中查看该物品", "在搜索中查看该物品"))
            CB.jump.__q = { id = it[1], kind = "item", text = NameOf(it[1]) }
        end
    end
    CB.jump:ClearAllPoints()
    CB.jump:SetPoint("BOTTOMLEFT", box, "BOTTOMLEFT", 10, 9)
    CB.jump:SetPoint("BOTTOMRIGHT", box, "BOTTOMRIGHT", -10, 9)
    CB.jump:Show()
end

