local _, ns = ...

local format = string.format
local floor = math.floor
local ceil = math.ceil
local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local SetButtonSelected = Host.SetButtonSelected
local SetTip = Host.SetTip
local Unpack = Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local PAGE_INSET = Host.PAGE_INSET
local CONTENT_W = Host.CONTENT_W

local RD = ns.PvPRankData
local SD = ns.PvPSetData
local HD = ns.PvPHonorData
if type(RD) ~= "table" or type(SD) ~= "table" or type(HD) ~= "table" then return end

local PV = {}
ns.PvPModule = PV

PV.X = PAGE_INSET
PV.W = CONTENT_W - 2 * PAGE_INSET
PV.HEAD_TOP, PV.HEAD_PAD, PV.HEAD_H = 8, 12, 88
PV.TITLE_Y, PV.NOTE_Y = 8, 34
PV.TAB_Y, PV.TAB_W, PV.TAB_H, PV.TAB_STEP = 58, 76, 24, 84
PV.TOP = 104
PV.VIEW_H = 532
PV.WEEK_PAD = 8
PV.WEEK_CARD_W = PV.W - 2 * PV.WEEK_PAD
PV.HEAD_ART = 131883
PV.HEAD_TEX = { 0.0, 1.0, 0.36, 0.455 }
PV.FAC_ICON = {
    a = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    h = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}

PV.ROW_H = 30
PV.ROW_GAP = 4
PV.CHIP = 26
PV.CARD_H = 44
PV.CARD_ICON = 32
PV.CARD_TX = 6 + PV.CARD_ICON + 5
PV.CARD_COLS = 2
PV.REP_COLS = 4
PV.CARD_GAP = 8
PV.SETS_LIST_W = 252
PV.SETS_DET_X = PV.SETS_LIST_W + 24
PV.MARK_TOP = 8
PV.MARK_ICON = 26
PV.MARK_PAD_X = 8
PV.MARK_PAD_Y = 4
PV.MARK_TXT_GAP = 8
PV.MARK_RANK_H = 16
PV.MARK_RANK_DY = 2
PV.MARK_IN_H = PV.MARK_ICON + PV.MARK_PAD_Y * 2
PV.MARK_STEP_GAP = 8
PV.MARK_ARROW = 16
PV.MARK_ARROW_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\PvPRankArrow.tga"
PV.MARK_AVAIL = PV.W - PV.SETS_DET_X - 12
PV.MARK_IN_W = floor((PV.MARK_AVAIL - 7 * PV.MARK_STEP_GAP) / 8)
PV.MARK_ARROW_DX = PV.MARK_IN_W + (PV.MARK_STEP_GAP - PV.MARK_ARROW) / 2
PV.MARK_ARROW_DY = -(PV.MARK_IN_H / 2 - PV.MARK_ARROW / 2)
PV.CARD_W = floor((PV.W - 24 - PV.CARD_GAP) / PV.CARD_COLS)
PV.CHIP_MAX = 40
PV.CARD_MAX = 100

local CLASS_ICON_DIR = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_"
local CLASS_ICON_FILE = {
    WARRIOR = "Warrior", PALADIN = "Paladin", HUNTER = "Hunter", ROGUE = "Rogue",
    PRIEST = "Priest", SHAMAN = "Shaman", MAGE = "Mage", WARLOCK = "Warlock", DRUID = "Druid",
}

local RANK_NAMES = {
    { a = L["列兵"], h = L["侦察兵"] },
    { a = L["下士"], h = L["步兵"] },
    { a = L["中士"], h = L["中士"] },
    { a = L["军士长"], h = L["高阶军士"] },
    { a = L["士官长"], h = L["一等军士长"] },
    { a = L["骑士"], h = L["石头守卫"] },
    { a = L["骑士中尉"], h = L["血卫士"] },
    { a = L["骑士队长"], h = L["军团士兵"] },
    { a = L["护卫骑士"], h = L["百夫长"] },
    { a = L["少校"], h = L["勇士"] },
    { a = L["司令"], h = L["中将"] },
    { a = L["统帅"], h = L["将军"] },
    { a = L["元帅"], h = L["督军"] },
    { a = L["大元帅"], h = L["高阶督军"] },
}

local SPEC_LABEL = {
    all = L["所有专精"], holy = L["神圣"], retri = L["惩戒"], shadow = L["暗影"],
    holydisc = L["神圣和戒律"], enhance = L["增强"], resto = L["恢复"], ele = L["元素"],
    feral = L["野性战斗"], balance = L["平衡"],
}

local FIELD_LABEL = {
    spear = L["暗矛群岛"], ab = L["阿拉希盆地"], wsg = L["战歌峡谷"], av = L["奥特兰克山谷"],
}

local TASK_TEXTS = {
    L["完成 3 场战歌峡谷 / 阿拉希盆地 / 暗矛群岛战斗"],
    L["赢得一场任意战场战斗"],
    L["在战歌峡谷 / 阿拉希盆地 / 暗矛群岛击杀 25 次"],
    L["在奥特兰克山谷击杀 200 次"],
    L["在古拉巴什竞技场击杀 25 次"],
    L["赢得 10 场决斗"],
}

local LEGACY_TEXTS = {
    L["达到军衔 3 / 7 / 10 / 13 / 14（各 1 点，共 5 点）"],
    L["在四个战场阵营声望达到崇拜（各 1 点，共 4 点）"],
    L["荣誉之地第 4 / 7 / 10 周任务（各 1 点，共 3 点，跨赛季持续开放）"],
}

local LiveState

local function fmtN(n)
    local s = tostring(floor((n or 0) + 0.5))
    repeat
        local k
        s, k = s:gsub("^(%d+)(%d%d%d)", "%1,%2")
    until not k or k == 0
    return s
end

local function CalcCP(rank, progress)
    if rank <= 1 then return 0 end
    return (HD.cpCeiling[rank] - HD.cpFloor[rank]) * (progress or 1) + HD.cpFloor[rank]
end

local function CalcPredictedRank(inputRank, cp)
    local rank, prog
    for k = 1, #HD.cpCeiling do
        if cp >= HD.cpFloor[k] and k <= inputRank then
            rank = k
            prog = (cp - HD.cpFloor[k]) / (HD.cpCeiling[k] - HD.cpFloor[k])
            if k >= 14 then
                rank, prog = 14, 0
            end
        else
            return rank, prog
        end
    end
    return rank, prog
end

local function MaxHonorNeeded(rank, honor)
    if rank == 0 then rank = 1 end
    local need
    if rank <= 6 then
        need = HD.cpFloor[rank] * HD.honorRatio[rank]
    elseif rank <= 10 then
        need = 45000 + (HD.cpFloor[rank] - 20000) * HD.honorRatio[rank]
    else
        need = 175000 + (HD.cpFloor[rank] - 40000) * HD.honorRatio[rank]
    end
    return need, need - (honor or 0)
end

local function CPGain(rank, objectiveRank, currentCP)
    if rank == 0 then rank = 1 end
    local newCP, bonus = 0, 0
    local buckets = objectiveRank - rank
    for key = rank + 1, objectiveRank do
        local gained = 0
        if key ~= 1 then
            gained = (HD.cpFloor[key] - HD.cpFloor[key - 1]) * HD.rankChangeFactor[key]
        end
        if key == rank + 1 then
            if rank == 9 then
                gained = 3000
            elseif rank == 11 then
                gained = 2500
            end
            local span = HD.cpFloor[key] - HD.cpFloor[key - 1]
            local withCeiling = span * (1 - ((currentCP - HD.cpFloor[key - 1]) / span))
            if withCeiling < gained then gained = withCeiling end
            if (rank == 6 and buckets == 4) or (rank == 7 and buckets >= 3)
                or (rank == 8 and (buckets == 2 or buckets == 3))
                or (rank == 9 and buckets >= 3) or (rank == 10 and buckets >= 2) then
                bonus = 500
            elseif rank == 8 and buckets == 4 then
                bonus = 1000
            end
        end
        newCP = newCP + gained
    end
    return newCP, bonus
end

local function Scenarios(rank, honor, progress)
    local options = {}
    local currentCP = CalcCP(rank, ceil(progress * 1000) / 1000)
    local situations = { "0", "+1", "+2", "+3", "+4" }
    for num = 1, 5 do
        if rank + num - 1 <= 14 then
            local situation = situations[num]
            local need, remains = MaxHonorNeeded(rank + num - 1, honor)
            local gainCP, bonus = CPGain(rank, rank + num - 1, currentCP)
            local totalNewCP
            if gainCP == 0 then
                totalNewCP = HD.cpFloor[rank + num - 1]
            else
                totalNewCP = currentCP + gainCP
            end
            totalNewCP = totalNewCP + (bonus or 0)
            local newRank, newProg = CalcPredictedRank(rank + 4, totalNewCP)
            if num == 1 and rank + 1 <= 14 then
                situation = "!!"
                local g2 = CPGain(rank, rank + 1, HD.cpFloor[rank + 1], currentCP)
                local cp2
                if g2 == 0 then
                    cp2 = HD.cpFloor[rank + 1]
                else
                    cp2 = currentCP + g2
                end
                newRank, newProg = CalcPredictedRank(rank + 4, cp2)
            end
            options[#options + 1] = {
                situation = situation, need = need, remains = remains,
                rank = newRank or 0, rankProgress = newProg or 0,
            }
        end
    end
    return options
end

local function SimplePath(rank, progress, goal)
    local total, weeks = 0, 0
    local curRank, curProg = rank, progress
    local firstNeed, firstRank, firstProg
    while weeks < 20 do
        local opts = Scenarios(curRank, 0, curProg)
        local doneT, doneO
        for _, o in ipairs(opts) do
            if o.rank >= goal then
                local t = total + (o.need or 0)
                if not doneT or t < doneT then doneT, doneO = t, o end
            end
        end
        if doneT then
            if weeks == 0 then
                firstNeed, firstRank, firstProg = doneO.need, doneO.rank, doneO.rankProgress
            end
            return doneT, weeks + 1, firstNeed, firstRank, firstProg
        end
        if curRank >= 14 then break end
        local best, bestRank, bestProg
        for _, o in ipairs(opts) do
            if o.rank > (bestRank or -1)
                or (o.rank == bestRank and (o.rankProgress or 0) > (bestProg or -1)) then
                best, bestRank, bestProg = o, o.rank, o.rankProgress
            end
        end
        if not best then break end
        if best.rank == curRank and (best.rankProgress or 0) <= curProg then break end
        if weeks == 0 then
            firstNeed, firstRank, firstProg = best.need, best.rank, best.rankProgress
        end
        total = total + (best.need or 0)
        curRank, curProg = best.rank, best.rankProgress
        weeks = weeks + 1
    end
    return total, weeks, firstNeed, firstRank, firstProg
end

local TAB_DEFS = {
    { key = "ranks", text = L["军衔"] },
    { key = "week",  text = L["本周"] },
    { key = "rep",   text = L["声望"] },
    { key = "sets",  text = L["套装"] },
}

local REP_DEFS = {
    { key = "spear", text = L["暗矛群岛"] },
    { key = "honor", text = L["荣誉之地"] },
}

local BATTLE_BGS = {
    { key = "ab",  label = L["阿拉希盆地"] },
    { key = "wsg", label = L["战歌峡谷"] },
    { key = "av",  label = L["奥特兰克山谷"] },
}
local BATTLE_META = {
    ab = {
        A = L["阿拉索联军正试图为暴风城夺回阿拉希盆地。"],
        H = L["污染者试图为部落夺取阿拉希盆地的重要资源。"],
    },
    wsg = {
        A = L["灰谷地区坚定的守卫者，目前正与战歌氏族在战歌峡谷中激烈交战。"],
        H = L["战歌氏族是最具攻击性的兽人氏族，目前正与暗夜精灵的银翼哨兵部队在战歌峡谷中激烈地交战中。"],
        ach = L["达到崇拜解锁成就「战歌峡谷主宰」"],
    },
    av = {
        A = L["一群在奥特兰克山谷建立了永久居所的矮人，正与霜狼氏族的兽人激烈交战中。"],
        H = L["霜狼氏族正在努力将雷矛探险队赶出奥特兰克山谷。"],
        ach = L["达到崇拜解锁成就「奥特兰克山谷主宰」"],
    },
}
local STANDING_LABEL = {
    friendly = L["友善"], honored = L["尊敬"], revered = L["崇敬"], exalted = L["崇拜"],
}
local BATTLE_KEYS = { ab = true, wsg = true, av = true }

local function MyFaction()
    if type(UnitFactionGroup) == "function" then
        local f = UnitFactionGroup("player")
        if f == "Horde" then return "H" end
    end
    return "A"
end

local function FSHeight(fs, fallback)
    local h = fs and fs.GetStringHeight and fs:GetStringHeight()
    if type(h) == "number" and h > 0 then return h end
    return fallback or 18
end

local function TextW(fs)
    local w = fs and fs.GetUnboundedStringWidth and fs:GetUnboundedStringWidth()
    if type(w) == "number" and w > 0 then return w end
    return 100
end

local function ItemIcon(id)
    if id and Host.DG and Host.DG.ItemIcon then return Host.DG.ItemIcon(id) end
    return Host.FALLBACK_ICON
end

local function ForwardWheel(f)
    f:EnableMouse(true)
    f:SetScript("OnMouseWheel", function(_, delta)
        if Host.DG and Host.DG.WheelScroll then
            Host.DG.WheelScroll(PV.scroll, PV.child, delta)
        end
    end)
end

function PV.NewChip(parent)
    local f = CreateFrame("Button", nil, parent)
    f:SetSize(PV.CHIP, PV.CHIP)
    local it = f:CreateTexture(nil, "ARTWORK")
    it:SetAllPoints(f)
    it:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(it) end
    f.iconTex = it
    f.hover = f:CreateTexture(nil, "OVERLAY")
    f.hover:SetAllPoints(f)
    f.hover:SetColorTexture(1, 1, 1, 0.08)
    f.hover:Hide()
    f:SetScript("OnEnter", function(self)
        self.hover:Show()
        if self.__id and Host.DG and Host.DG.ShowItemTip then
            Host.DG.ShowItemTip(self, { self.__id })
        end
    end)
    f:SetScript("OnLeave", function(self)
        self.hover:Hide()
        GameTooltip:Hide()
    end)
    f:SetScript("OnClick", function(self, button)
        if Host.DG and Host.DG.ItemShiftClick then Host.DG.ItemShiftClick(self, button) end
    end)
    ForwardWheel(f)
    return f
end

function PV.NewCard(parent)
    local f = CreateFrame("Button", nil, parent)
    f:SetSize(PV.CARD_W, PV.CARD_H)
    local layer = ns.hui and ns.hui.layer
    if ns.hui and ns.hui.BuildRoundedBG and layer then
        ns.hui.BuildRoundedBG(f, 4, layer.L2, "both", true, 1)
    else
        f.edge = f:CreateTexture(nil, "BACKGROUND")
        f.edge:SetAllPoints(f)
        f.edge:SetColorTexture(1, 1, 1, 0.10)
        f.bg = f:CreateTexture(nil, "BACKGROUND", nil, 1)
        f.bg:SetPoint("TOPLEFT", f, "TOPLEFT", 1, -1)
        f.bg:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -1, 1)
        f.bg:SetColorTexture(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
    end
    local it = f:CreateTexture(nil, "ARTWORK")
    it:SetSize(PV.CARD_ICON, PV.CARD_ICON)
    it:SetPoint("LEFT", f, "LEFT", 6, 0)
    it:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(it) end
    f.iconTex = it
    f.name = MakeFS(f, 14, C_TEXT, "LEFT")
    f.name:SetPoint("TOPLEFT", f, "TOPLEFT", PV.CARD_TX, -4)
    f.name:SetWidth(PV.CARD_W - PV.CARD_TX - 7)
    f.name:SetWordWrap(false)
    f.meta = MakeFS(f, 11, C_GREY, "LEFT")
    f.meta:SetPoint("TOPLEFT", f, "TOPLEFT", PV.CARD_TX, -23)
    f.meta:SetWordWrap(false)
    f.hover = f:CreateTexture(nil, "OVERLAY")
    f.hover:SetAllPoints(f)
    f.hover:SetColorTexture(1, 1, 1, 0.06)
    f.hover:Hide()
    f:SetScript("OnEnter", function(self)
        self.hover:Show()
        if self.__id and Host.DG and Host.DG.ShowItemTip then
            Host.DG.ShowItemTip(self, { self.__id })
        end
    end)
    f:SetScript("OnLeave", function(self)
        self.hover:Hide()
        GameTooltip:Hide()
    end)
    f:SetScript("OnClick", function(self, button)
        if Host.DG and Host.DG.ItemShiftClick then Host.DG.ItemShiftClick(self, button) end
    end)
    ForwardWheel(f)
    return f
end

function PV.PaintCard(f, id)
    f.__id = id
    local nm, ok
    if Host.DG and Host.DG.ItemName then nm, ok = Host.DG.ItemName(id) end
    local txt = (ok and nm) or format(L["物品 #%d"], id or 0)
    if Host.DG and Host.DG.FitText then
        txt = Host.DG.FitText(txt, 14, f.name.__pw or (PV.CARD_W - PV.CARD_TX - 7))
    end
    f.name:SetText(txt)
    f.meta:SetText("")
    if ok then
        if Host.DG.QColor and Host.DG.QualOf then
            local qr, qg, qb = Host.DG.QColor(Host.DG.QualOf(id))
            if qr then f.name:SetTextColor(qr, qg, qb) end
        end
        if Host.DG and Host.DG.ItemMeta then
            local meta = Host.DG.ItemMeta(id)
            if type(meta) == "string" and meta ~= "" then f.meta:SetText(meta) end
        end
    else
        f.name:SetTextColor(Unpack(C_GREY))
        if Host.DG and Host.DG.RequestItem then Host.DG.RequestItem(id) end
    end
    f.iconTex:SetTexture(ItemIcon(id))
end

function PV.OnItemData(itemID)
    if not PV.built then return end
    for i = 1, PV.CHIP_MAX do
        local c = PV.chips[i]
        if c and c.__id == itemID and c:IsShown() then
            c.iconTex:SetTexture(ItemIcon(itemID))
        end
    end
    for i = 1, PV.CARD_MAX do
        local f = PV.cards[i]
        if f and f.__id == itemID and f:IsShown() then PV.PaintCard(f, itemID) end
    end
end

function PV.Build(page)
    if PV.built or PV.building then return end
    PV.building = true
    ns.PhasedStart(60, coroutine.create(function()
    PV.page = page
    PV.tabs = {}
    PV.chips = {}
    PV.cards = {}
    PV.rankRows = {}
    PV.capRows = {}
    PV.setRows = {}
    PV.weekBf = {}
    PV.taskRows = {}
    PV.legacyRows = {}
    PV.markChips = {}
    PV.repBtns = {}
    PV.battleBtns = {}
    PV.spRows = {}
    PV.goalBtns = {}
    PV.simBtns = {}
    PV.mileTicks = {}
    PV.mileLabels = {}
    PV.labels = {}
    PV.faction = MyFaction()
    PV.selSet = 1
    PV.selRep = "spear"
    PV.goal = 14
    PV.simRank = nil
    coroutine.yield()

    local headCard = CreateFrame("Frame", nil, page)
    headCard:SetSize(PV.W, PV.HEAD_H)
    headCard:SetPoint("TOPLEFT", page, "TOPLEFT", PV.X, -PV.HEAD_TOP)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(headCard, 6, ns.hui.layer.L1, "both", false)
        if ns.hui.BuildRoundBorder then
            ns.hui.BuildRoundBorder(headCard, 6, ns.hui.CARD_BORDER, headCard, "OVERLAY", "both", 1)
        end
    else
        headCard.edge = headCard:CreateTexture(nil, "BACKGROUND")
        headCard.edge:SetAllPoints(headCard)
        headCard.edge:SetColorTexture(1, 1, 1, 0.10)
        headCard.bg = headCard:CreateTexture(nil, "BACKGROUND", nil, 1)
        headCard.bg:SetPoint("TOPLEFT", headCard, "TOPLEFT", 1, -1)
        headCard.bg:SetPoint("BOTTOMRIGHT", headCard, "BOTTOMRIGHT", -1, 1)
        headCard.bg:SetColorTexture(0x10 / 255, 0x13 / 255, 0x1A / 255, 1)
    end
    headCard.art = headCard:CreateTexture(nil, "BACKGROUND")
    headCard.art:SetDrawLayer("BACKGROUND", 2)
    headCard.art:SetAllPoints(headCard)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(headCard.art) end
    headCard.art:SetTexture(PV.HEAD_ART)
    headCard.art:SetTexCoord(PV.HEAD_TEX[1], PV.HEAD_TEX[2], PV.HEAD_TEX[3], PV.HEAD_TEX[4])
    headCard.dim = headCard:CreateTexture(nil, "ARTWORK")
    headCard.dim:SetAllPoints(headCard)
    headCard.dim:SetColorTexture(0, 0, 0, 0.45)
    PV.headCard = headCard
    PV.headUI = CreateFrame("Frame", nil, headCard)
    PV.headUI:SetAllPoints(headCard)

    local title = MakeFS(PV.headUI, 16, C_WHITE, "LEFT")
    title:SetPoint("TOPLEFT", PV.headUI, "TOPLEFT", PV.HEAD_PAD, -PV.TITLE_Y)
    title:SetText(L["PvP"])
    local count = MakeFS(PV.headUI, 14, C_GREY, "RIGHT")
    count:SetPoint("TOPRIGHT", PV.headUI, "TOPRIGHT", -PV.HEAD_PAD, -PV.TITLE_Y)
    count:SetText(format(L["共 14 级军衔 · 每阵营 15 套 · 更新于 %s"], SD.updated))
    local note = MakeFS(PV.headUI, 14, C_GREY, "LEFT")
    note:SetPoint("TOPLEFT", PV.headUI, "TOPLEFT", PV.HEAD_PAD, -PV.NOTE_Y)
    note:SetText(L["军衔点数来自战场与加基森 PvP 任务，荣誉另来自荣誉击杀（上限 25,000）"])
    PV.title, PV.count, PV.note = title, count, note

    for i, def in ipairs(TAB_DEFS) do
        local bt = NewButton(headCard, def.text, PV.TAB_W, PV.TAB_H, 14)
        bt:SetPoint("TOPLEFT", headCard, "TOPLEFT", PV.HEAD_PAD + (i - 1) * PV.TAB_STEP, -PV.TAB_Y)
        SetButtonSelected(bt, def.key == (PV.cur or "ranks"))
        bt:SetScript("OnClick", function() PV.SetTab(def.key) end)
        PV.tabs[def.key] = bt
    end
    coroutine.yield()

    local scroll = CreateFrame("ScrollFrame", nil, page)
    scroll:SetPoint("TOPLEFT", page, "TOPLEFT", PV.X, -PV.TOP)
    scroll:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -4, PV.X)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        if Host.DG and Host.DG.WheelScroll then
            Host.DG.WheelScroll(PV.scroll, PV.child, delta)
        end
    end)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(PV.W, 10)
    scroll:SetScrollChild(child)
    PV.scroll, PV.child = scroll, child
    coroutine.yield()
    local function NewRoundCard(w, h, inner)
        local f = CreateFrame("Frame", nil, child)
        f:SetSize(w, h)
        local layer = ns.hui and ns.hui.layer
        local r1, g1, b1 = 0x10, 0x13, 0x1A
        if inner then r1, g1, b1 = 0x16, 0x1A, 0x22 end
        if ns.hui and ns.hui.BuildRoundedBG and layer then
            ns.hui.BuildRoundedBG(f, 4, inner and layer.L2 or layer.L1, "both", true, 1)
        else
            f.edge = f:CreateTexture(nil, "BACKGROUND")
            f.edge:SetAllPoints(f)
            f.edge:SetColorTexture(1, 1, 1, 0.10)
            f.bg = f:CreateTexture(nil, "BACKGROUND", nil, 1)
            f.bg:SetPoint("TOPLEFT", f, "TOPLEFT", 1, -1)
            f.bg:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -1, 1)
            f.bg:SetColorTexture(r1 / 255, g1 / 255, b1 / 255, 1)
        end
        return f
    end
    PV.rankCard = NewRoundCard(500, 532)
    PV.capCard = NewRoundCard(PV.W - 512, 532)
    PV.weekBig = NewRoundCard(PV.W, 100)
    PV.weekCard1 = NewRoundCard(PV.WEEK_CARD_W, 100, true)
    PV.weekCard2 = NewRoundCard(PV.WEEK_CARD_W, 100, true)
    PV.repCard = NewRoundCard(PV.W, 100)
    PV.setsLeftCard = NewRoundCard(PV.SETS_LIST_W, 100)
    PV.setsRightCard = NewRoundCard(PV.W - 264, 100)
    coroutine.yield()
    local baseLvl = (child.GetFrameLevel and type(child:GetFrameLevel()) == "number") and child:GetFrameLevel() or 0
    if baseLvl > 0 then
        for _, f in ipairs({ PV.weekCard1, PV.weekCard2, PV.repCard, PV.setsLeftCard, PV.setsRightCard }) do
            if f.SetFrameLevel then f:SetFrameLevel(baseLvl - 1) end
        end
        if baseLvl > 2 and PV.weekBig.SetFrameLevel then PV.weekBig:SetFrameLevel(baseLvl - 2) end
    end
    coroutine.yield()
    PV.rankUI = CreateFrame("Frame", nil, PV.rankCard)
    PV.rankUI:SetAllPoints(PV.rankCard)
    PV.capUI = CreateFrame("Frame", nil, PV.capCard)
    PV.capUI:SetAllPoints(PV.capCard)

    for i = 1, PV.CHIP_MAX do
        PV.chips[i] = PV.NewChip(child)
        PV.chips[i]:Hide()
    end
    coroutine.yield()

    for i = 1, 14 do
        local r = CreateFrame("Button", nil, child)
        r:SetSize(476, 34)
        r.zebra = PV.rankCard:CreateTexture(nil, "BACKGROUND", nil, 2)
        r.zebra:SetAllPoints(r)
        r.zebra:SetColorTexture(1, 1, 1, 0.06)
        r.zebra:SetShown(i % 2 == 0)
        r.badge = r:CreateTexture(nil, "ARTWORK")
        r.badge:SetSize(24, 24)
        r.badge:SetPoint("TOPLEFT", r, "TOPLEFT", 0, -5)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.badge) end
        r.name = MakeFS(r, 14, C_GOLD, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 32, -9)
        r.name:SetWidth(152)
        r.name:SetWordWrap(false)
        r.pts = MakeFS(r, 14, C_TEXT, "RIGHT")
        r.pts:SetPoint("TOPRIGHT", r, "TOPLEFT", 210, -9)
        r.cum = MakeFS(r, 14, C_GREY, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", 280, -9)
        r.more = MakeFS(r, 14, C_GREY, "LEFT")
        r.more:SetPoint("TOPLEFT", r, "TOPLEFT", 378, -11)
        r.more:SetWordWrap(false)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        ForwardWheel(r)
        PV.rankRows[i] = r
        if i % 2 == 0 then coroutine.yield() end
    end

    PV.rankHead = {
        lvl = MakeFS(PV.rankUI, 14, C_GOLD, "LEFT"),
        pts = MakeFS(PV.rankUI, 14, C_GOLD, "RIGHT"),
        cum = MakeFS(PV.rankUI, 14, C_GOLD, "RIGHT"),
        week = MakeFS(PV.rankUI, 14, C_GOLD, "RIGHT"),
        rew = MakeFS(PV.rankUI, 14, C_GOLD, "LEFT"),
    }
    PV.rankHead.lvl:SetText(L["等级"])
    PV.rankHead.pts:SetText(L["点数"])
    PV.rankHead.cum:SetText(L["累计"])
    PV.rankHead.week:SetText(L["最早解锁"])
    PV.rankHead.rew:SetText(L["奖励"])
    PV.rankBadge = child:CreateTexture(nil, "ARTWORK")
    PV.rankBadge:SetSize(24, 24)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(PV.rankBadge) end
    coroutine.yield()

    local capColW = floor((PV.WEEK_CARD_W - 24) / 2) - 16
    for i = 1, 10 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(capColW, 30)
        r.week = MakeFS(r, 12, C_TEXT, "LEFT")
        r.week:SetPoint("TOPLEFT", r, "TOPLEFT", 4, -7)
        r.rank = MakeFS(r, 12, C_GOLD, "LEFT")
        r.rank:SetPoint("TOPLEFT", r, "TOPLEFT", 64, -7)
        r.barBG = r:CreateTexture(nil, "BACKGROUND")
        r.barBG:SetPoint("TOPLEFT", r, "TOPLEFT", 106, -9)
        r.barBG:SetSize(120, 10)
        r.bar = r:CreateTexture(nil, "ARTWORK")
        r.bar:SetPoint("TOPLEFT", r.barBG, "TOPLEFT", 0, 0)
        r.bar:SetHeight(10)
        r.bar:SetColorTexture(0.27, 0.75, 0.45, 0.85)
        r.cum = MakeFS(r, 12, C_TEXT, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", capColW - 36, -7)
        r.inc = MakeFS(r, 12, C_GREY, "RIGHT")
        r.inc:SetPoint("TOPRIGHT", r, "TOPLEFT", capColW - 4, -7)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 2, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -2, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        PV.capRows[i] = r
    end
    coroutine.yield()
    PV.wkRows = {}
    for i = 1, 10 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(400, 44)
        r.zebra = PV.capCard:CreateTexture(nil, "BACKGROUND", nil, 2)
        r.zebra:SetAllPoints(r)
        r.zebra:SetColorTexture(1, 1, 1, 0.06)
        r.zebra:SetShown(i % 2 == 0)
        r.week = MakeFS(r, 14, C_GREY, "LEFT")
        r.week:SetPoint("TOPLEFT", r, "TOPLEFT", 0, -13)
        r.week:SetWordWrap(false)
        r.badge = r:CreateTexture(nil, "ARTWORK")
        r.badge:SetSize(20, 20)
        r.badge:SetPoint("TOPLEFT", r, "TOPLEFT", 62, -12)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.badge) end
        r.rank = MakeFS(r, 14, C_GOLD, "LEFT")
        r.rank:SetPoint("TOPLEFT", r, "TOPLEFT", 88, -13)
        r.rank:SetWordWrap(false)
        r.cum = MakeFS(r, 14, C_TEXT, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", 292, -13)
        r.inc = MakeFS(r, 14, C_GREY, "RIGHT")
        r.inc:SetPoint("TOPRIGHT", r, "TOPLEFT", 368, -13)
        r.inc:SetTextColor(0.27, 0.75, 0.45, 1)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        ForwardWheel(r)
        PV.wkRows[i] = r
        if i % 2 == 0 then coroutine.yield() end
    end

    PV.capHead = {
        week = MakeFS(PV.capUI, 14, C_GREY, "LEFT"),
        rank = MakeFS(PV.capUI, 14, C_GREY, "LEFT"),
        cum = MakeFS(PV.capUI, 14, C_GREY, "RIGHT"),
        inc = MakeFS(PV.capUI, 14, C_GREY, "RIGHT"),
    }
    PV.capHead.week:SetText(L["周"])
    PV.capHead.rank:SetText(L["达到军衔"])
    PV.capHead.cum:SetText(L["累计上限"])
    PV.capHead.inc:SetText(L["本周增量"])
    PV.capNote = MakeFS(PV.capUI, 14, C_GREY, "LEFT")
    PV.capNote:SetWidth(400)
    PV.capNote:SetWordWrap(false)
    PV.labels.capNote = PV.capNote
    coroutine.yield()

    for i = 1, #SD.sets do
        local bt = CreateFrame("Button", nil, child)
        bt:SetSize(228, PV.ROW_H)
        local ic = bt:CreateTexture(nil, "ARTWORK")
        ic:SetSize(20, 20)
        ic:SetPoint("TOPLEFT", bt, "TOPLEFT", 8, -5)
        ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
        bt.iconTex = ic
        bt.name = MakeFS(bt, 14, C_TEXT, "LEFT")
        bt.name:SetPoint("TOPLEFT", bt, "TOPLEFT", 36, -6)
        bt.name:SetWordWrap(false)
        bt.count = MakeFS(bt, 11, C_GREY, "RIGHT")
        bt.count:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -8, -8)
        local hlayer = ns.hui and ns.hui.layer
        if ns.hui and ns.hui.BuildRoundedBG and hlayer then
            local fill, border = ns.hui.BuildRoundedBG(bt, 6, hlayer.L2, "both", true, 1)
            bt.__huiCard = { fill = fill, border = border }
            if ns.hui.BuildCapsule then
                local hp = ns.hui.BuildCapsule(bt, 6, hlayer.L4, 1, 2)
                for _, t in ipairs(hp) do t:Hide() end
                bt.__hov = hp
            end
        else
            bt.bg = bt:CreateTexture(nil, "BACKGROUND")
            bt.bg:SetAllPoints(bt)
            bt.bg:SetColorTexture(1, 1, 1, 0.04)
        end
        bt.hover = bt:CreateTexture(nil, "OVERLAY")
        bt.hover:SetAllPoints(bt)
        bt.hover:SetColorTexture(1, 1, 1, 0.06)
        bt.hover:Hide()
        bt:SetScript("OnEnter", function(self)
            if self.__hov then
                for _, t in ipairs(self.__hov) do t:Show() end
            elseif self.hover then
                self.hover:Show()
            end
        end)
        bt:SetScript("OnLeave", function(self)
            if self.__hov then
                for _, t in ipairs(self.__hov) do t:Hide() end
            elseif self.hover then
                self.hover:Hide()
            end
        end)
        bt.__idx = i
        bt:SetScript("OnClick", function(self)
            PV.selSet = self.__idx
            PV.RenderSets()
        end)
        ForwardWheel(bt)
        PV.setRows[i] = bt
        if i % 4 == 0 then coroutine.yield() end
    end

    PV.markArrows = {}
    for i = 1, 8 do
        local m = RD.marks[i]
        local bt = CreateFrame("Button", nil, child)
        bt:SetSize(PV.MARK_IN_W, PV.MARK_IN_H)
        local ic = bt:CreateTexture(nil, "ARTWORK")
        ic:SetSize(PV.MARK_ICON, PV.MARK_ICON)
        ic:SetPoint("TOPLEFT", bt, "TOPLEFT", PV.MARK_PAD_X, -PV.MARK_PAD_Y)
        ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
        bt.iconTex = ic
        bt.rank = MakeFS(bt, 14, C_GOLD, "LEFT")
        bt.rank:SetPoint("TOPLEFT", bt, "TOPLEFT",
            PV.MARK_PAD_X + PV.MARK_ICON + PV.MARK_TXT_GAP,
            -((PV.MARK_IN_H - PV.MARK_RANK_H) / 2 + PV.MARK_RANK_DY))
        bt.__id = m.id
        ForwardWheel(bt)
        local hlayer = ns.hui and ns.hui.layer
        if ns.hui and ns.hui.BuildRoundedBG and hlayer then
            local fill, border = ns.hui.BuildRoundedBG(bt, 6, hlayer.L2, "both", true, 1)
            bt.__huiCard = { fill = fill, border = border }
            if ns.hui.BuildCapsule then
                local hp = ns.hui.BuildCapsule(bt, 6, hlayer.L4, 1, 2)
                for _, t in ipairs(hp) do t:Hide() end
                bt.__hov = hp
            end
        else
            bt.bg = bt:CreateTexture(nil, "BACKGROUND")
            bt.bg:SetAllPoints(bt)
            bt.bg:SetColorTexture(1, 1, 1, 0.04)
        end
        bt:SetScript("OnEnter", function(self)
            if self.__hov then
                for _, t in ipairs(self.__hov) do t:Show() end
            elseif self.bg then
                self.bg:SetColorTexture(1, 1, 1, 0.10)
            end
            if Host.DG and Host.DG.ShowItemTip then
                Host.DG.ShowItemTip(self, { self.__id })
            end
        end)
        bt:SetScript("OnLeave", function(self)
            if self.__hov then
                for _, t in ipairs(self.__hov) do t:Hide() end
            elseif self.bg then
                self.bg:SetColorTexture(1, 1, 1, 0.04)
            end
            GameTooltip:Hide()
        end)
        PV.markChips[i] = bt
    end
    local arHost = CreateFrame("Frame", nil, child)
    local markBaseLvl = (child.GetFrameLevel and type(child:GetFrameLevel()) == "number")
        and child:GetFrameLevel() or 0
    if markBaseLvl > 0 and arHost.SetFrameLevel then arHost:SetFrameLevel(markBaseLvl + 1) end
    for i = 1, 7 do
        local ar = arHost:CreateTexture(nil, "ARTWORK")
        ar:SetSize(PV.MARK_ARROW, PV.MARK_ARROW)
        ar:SetTexture(PV.MARK_ARROW_TEX)
        ar:SetVertexColor(Unpack(C_GOLD))
        ar:Hide()
        PV.markArrows[i] = ar
    end
    coroutine.yield()

    for i = 1, 2 do
        local bt = NewButton(headCard, i == 1 and L["联盟"] or L["部落"], PV.TAB_W, PV.TAB_H, 14)
        local bfs = bt:GetFontString()
        if bfs then
            if i == 1 then
                bfs:SetTextColor(0.40, 0.62, 1.00, 1)
            else
                bfs:SetTextColor(1.00, 0.36, 0.26, 1)
            end
            bfs:ClearAllPoints()
            bfs:SetPoint("TOPLEFT", bt, "TOPLEFT", 7 + 16 + 3, 0)
            bfs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)
            bfs:SetJustifyH("CENTER")
        end
        local bic = bt:CreateTexture(nil, "OVERLAY")
        bic:SetTexture(i == 1 and PV.FAC_ICON.a or PV.FAC_ICON.h)
        bic:SetSize(16, 16)
        bic:SetPoint("LEFT", bt, "LEFT", 7, 0)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bic) end
        bt.__fac = (i == 1) and "A" or "H"
        bt:SetScript("OnClick", function(self)
            PV.faction = self.__fac
            PV.Render()
        end)
        PV["facBtn" .. i] = bt
    end
    coroutine.yield()

    for i, rec in ipairs(RD.battlefields) do
        local bt = NewButton(child, FIELD_LABEL[rec.key] or rec.key, 148, 24, 12)
        bt.__bf = rec
        bt:SetScript("OnEnter", function(self)
            local d = self.__bf
            local cta = (d.cta > 0) and format(L["召唤轮换 %d"], d.cta) or L["不在轮换"]
            if SetTip then
                SetTip(self, format("%s · %s · %s",
                    format(L["%d–%d 级"], d.minLevel, d.maxLevel),
                    format(L["%d 对 %d"], d.size, d.size), cta))
            end
        end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        ForwardWheel(bt)
        PV.weekBf[i] = bt
    end
    coroutine.yield()

    for i, def in ipairs(REP_DEFS) do
        local bt = NewButton(child, def.text, 120, 24, 12)
        bt.__rep = def.key
        bt:SetScript("OnClick", function(self)
            PV.selRep = self.__rep
            PV.Render()
        end)
        PV.repBtns[i] = bt
    end
    coroutine.yield()

    for i, bg in ipairs(BATTLE_BGS) do
        local bt = NewButton(child, bg.label, 120, 24, 12)
        bt.__rep = bg.key
        bt:SetScript("OnClick", function(self)
            PV.selRep = self.__rep
            PV.Render()
        end)
        PV.battleBtns[i] = bt
    end
    coroutine.yield()

    for i = 1, #TASK_TEXTS do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(PV.W - 24, 24)
        r.dot = MakeFS(r, 14, C_GOLD, "LEFT")
        r.dot:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -4)
        r.dot:SetText("·")
        r.txt = MakeFS(r, 14, C_TEXT, "LEFT")
        r.txt:SetPoint("TOPLEFT", r, "TOPLEFT", 28, -4)
        r.txt:SetText(TASK_TEXTS[i])
        PV.taskRows[i] = r
    end
    coroutine.yield()

    for i = 1, #LEGACY_TEXTS do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(PV.W - 24, 24)
        r.dot = MakeFS(r, 14, C_GOLD, "LEFT")
        r.dot:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -4)
        r.dot:SetText("·")
        r.txt = MakeFS(r, 14, C_TEXT, "LEFT")
        r.txt:SetPoint("TOPLEFT", r, "TOPLEFT", 28, -4)
        r.txt:SetText(LEGACY_TEXTS[i])
        PV.legacyRows[i] = r
    end
    coroutine.yield()

    local secSpecs = {
        { key = "ranksHead", fs = 14, col = C_GOLD },
        { key = "ranksFoot", fs = 11, col = C_GREY },
        { key = "capsFoot",  fs = 11, col = C_GREY },
        { key = "weekCaps",  fs = 14, col = C_GOLD },
        { key = "setsMarks", fs = 14, col = C_GOLD },
        { key = "setsBlue",  fs = 14, col = C_GOLD },
        { key = "setsEpic",  fs = 14, col = C_GOLD },
        { key = "setsNote",  fs = 11, col = C_GREY },
        { key = "bfHead",    fs = 14, col = C_GOLD },
        { key = "bfFoot",    fs = 11, col = C_GREY },
        { key = "taskHead",  fs = 14, col = C_GOLD },
        { key = "legHead",   fs = 14, col = C_GOLD },
        { key = "spHead",    fs = 14, col = C_GOLD },
        { key = "spRule",    fs = 14, col = C_TEXT },
        { key = "spNote",    fs = 11, col = C_GREY },
        { key = "sprHead",   fs = 14, col = C_GOLD },
        { key = "sprState",  fs = 14, col = C_TEXT },
        { key = "sprMile",   fs = 14, col = C_GOLD },
        { key = "sprScene",  fs = 14, col = C_GOLD },
        { key = "sprGoal",   fs = 14, col = C_TEXT },
        { key = "sprSim",    fs = 14, col = C_TEXT },
        { key = "sprPath1",  fs = 14, col = C_GOLD },
        { key = "sprPath2",  fs = 14, col = C_TEXT },
        { key = "sprNote",   fs = 11, col = C_GREY },
        { key = "setDetailName", fs = 16, col = C_WHITE },
        { key = "setDetailSpec", fs = 14, col = C_GREY },
    }
    for i = 1, 3 do
        secSpecs[#secSpecs + 1] = { key = "bHead" .. i, fs = 14, col = C_GOLD }
        secSpecs[#secSpecs + 1] = { key = "bRule" .. i, fs = 14, col = C_TEXT }
        secSpecs[#secSpecs + 1] = { key = "bDesc" .. i, fs = 14, col = C_GREY, wrap = true }
        secSpecs[#secSpecs + 1] = { key = "bAch" .. i, fs = 14, col = C_TEXT }
    end
    for i = 1, 4 do
        secSpecs[#secSpecs + 1] = { key = "bSec" .. i, fs = 14, col = C_GOLD }
    end
    for _, sp in ipairs(secSpecs) do
        local fs = MakeFS(child, sp.fs, sp.col, "LEFT")
        if sp.fs == 11 or sp.wrap then
            fs:SetWordWrap(true)
            fs:SetWidth(PV.W - 32)
        end
        PV.labels[sp.key] = fs
    end
    coroutine.yield()

    PV.cur = "ranks"
    PV.RenderRanks()
    coroutine.yield()

    for i = 1, PV.CARD_MAX do
        PV.cards[i] = PV.NewCard(child)
        PV.cards[i]:Hide()
        if i % 14 == 0 then coroutine.yield() end
    end
    coroutine.yield()
    PV.setDetailIcon = child:CreateTexture(nil, "ARTWORK")
    PV.setDetailIcon:SetSize(24, 24)
    PV.setDetailIcon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(PV.setDetailIcon) end

    if SetTip then
        SetTip(PV.title, L["军衔不会衰减：没有任何东西会扣点数，等级是一条只增不减的进度条"])
    end

    PV.badge = child:CreateTexture(nil, "ARTWORK")
    PV.badge:SetSize(40, 40)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(PV.badge) end

    PV.mileBG = child:CreateTexture(nil, "BACKGROUND")
    PV.mileBG:SetColorTexture(1, 1, 1, 0.08)
    PV.mileRed = child:CreateTexture(nil, "ARTWORK")
    PV.mileRed:SetColorTexture(0.85, 0.3, 0.25, 0.5)
    PV.mileMark = child:CreateTexture(nil, "OVERLAY")
    PV.mileMark:SetColorTexture(1, 0.82, 0, 0.95)
    coroutine.yield()
    for i = 1, 4 do
        PV.mileTicks[i] = child:CreateTexture(nil, "OVERLAY")
        PV.mileTicks[i]:SetColorTexture(1, 1, 1, 0.35)
        PV.mileLabels[i] = MakeFS(child, 11, C_GREY, "CENTER")
    end
    coroutine.yield()

    for i = 1, 5 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(PV.W - 24, 26)
        r.sit = MakeFS(r, 14, C_GOLD, "LEFT")
        r.sit:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -4)
        r.need = MakeFS(r, 14, C_TEXT, "RIGHT")
        r.need:SetPoint("TOPRIGHT", r, "TOPLEFT", 330, -4)
        r.rem = MakeFS(r, 14, C_GREY, "RIGHT")
        r.rem:SetPoint("TOPRIGHT", r, "TOPLEFT", 460, -4)
        r.res = MakeFS(r, 14, C_TEXT, "RIGHT")
        r.res:SetPoint("TOPRIGHT", r, "TOPLEFT", 690, -4)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 4, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -4, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        ForwardWheel(r)
        PV.spRows[i] = r
    end
    coroutine.yield()

    for i = 1, 13 do
        local bt = NewButton(child, format("R%d", i + 1), 34, 22, 11)
        bt.__goal = i + 1
        bt:SetScript("OnClick", function(self)
            PV.goal = self.__goal
            PV.Render()
        end)
        PV.goalBtns[i] = bt
    end
    coroutine.yield()
    for i = 1, 14 do
        local bt = NewButton(child, format("R%d", i), 34, 22, 11)
        bt.__sim = i
        bt:SetScript("OnClick", function(self)
            if PV.simRank == self.__sim then
                PV.simRank = nil
            else
                PV.simRank = self.__sim
            end
            PV.Render()
        end)
        PV.simBtns[i] = bt
    end

    coroutine.yield()
    PV.built = true
    PV.building = false
    end))
end

local function PY()
    if coroutine.running and coroutine.running() then coroutine.yield() end
end

function PV.RequestRender()
    if not PV.built then return end
    if not (ns.PaintJob and ns.IdleJobs) then
        PV.Render()
        return
    end
    if ns.PaintJob.Active("PvP") then
        PV.__pend = true
        return
    end
    ns.PaintJob.Run("PvP", function() PV.Render() end, function()
        if PV.__pend then
            PV.__pend = false
            PV.RequestRender()
        end
    end)
end

function PV.SetTab(key)
    if not PV.built then return end
    local ok
    for _, def in ipairs(TAB_DEFS) do
        if def.key == key then ok = true end
    end
    if not ok then key = "ranks" end
    PV.cur = key
    for _, def in ipairs(TAB_DEFS) do
        local bt = PV.tabs[def.key]
        if bt then SetButtonSelected(bt, def.key == key) end
    end
    PV.RequestRender()
end

function PV.Open()
    if PV.built then PV.RequestRender() end
end

function PV.Refresh()
    if PV.built then PV.RequestRender() end
end

local function HideAll()
    for i = 1, PV.CHIP_MAX do PV.chips[i]:Hide() end
    for i = 1, PV.CARD_MAX do PV.cards[i]:Hide() end
    for i = 1, 14 do PV.rankRows[i]:Hide() end
    for i = 1, 10 do PV.capRows[i]:Hide() end
    for i = 1, 10 do PV.wkRows[i]:Hide() end
    PV.rankCard:Hide()
    PV.capCard:Hide()
    PV.weekBig:Hide()
    PV.weekCard1:Hide()
    PV.weekCard2:Hide()
    PV.repCard:Hide()
    PV.setsLeftCard:Hide()
    PV.setsRightCard:Hide()
    for i = 1, #SD.sets do PV.setRows[i]:Hide() end
    for i = 1, 8 do PV.markChips[i]:Hide() end
    for i = 1, 7 do PV.markArrows[i]:Hide() end
    for i = 1, #RD.battlefields do PV.weekBf[i]:Hide() end
    for i = 1, #REP_DEFS do PV.repBtns[i]:Hide() end
    for i = 1, #BATTLE_BGS do PV.battleBtns[i]:Hide() end
    for i = 1, #TASK_TEXTS do PV.taskRows[i]:Hide() end
    for i = 1, #LEGACY_TEXTS do PV.legacyRows[i]:Hide() end
    for k in pairs(PV.labels) do PV.labels[k]:Hide() end
    PV.setDetailIcon:Hide()
    PV.facBtn1:Hide()
    PV.facBtn2:Hide()
    for i = 1, 5 do PV.spRows[i]:Hide() end
    PV.badge:Hide()
    PV.rankBadge:Hide()
    for _, fs in pairs(PV.rankHead or {}) do fs:Hide() end
    for _, fs in pairs(PV.capHead or {}) do fs:Hide() end
    PV.mileBG:Hide()
    PV.mileRed:Hide()
    PV.mileMark:Hide()
    for i = 1, 4 do
        PV.mileTicks[i]:Hide()
        PV.mileLabels[i]:Hide()
    end
    for i = 1, 13 do PV.goalBtns[i]:Hide() end
    for i = 1, 14 do PV.simBtns[i]:Hide() end
end

function PV.Render()
    if not PV.built then return end
    HideAll()
    if PV.cur == "week" then
        PV.RenderWeek()
    elseif PV.cur == "rep" then
        PV.RenderRep()
    elseif PV.cur == "sets" then
        PV.RenderSets()
    else
        PV.RenderRanks()
    end
end

function PV.RenderRanks()
    local LW, RH = 500, 28
    local function T(k) return L[k] or k end
    PV.rankCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, 0)
    PV.capCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", LW + 12, 0)
    PV.rankCard:Show()
    PV.capCard:Show()
    PY()
    local head = PV.labels.ranksHead
    head:SetPoint("TOPLEFT", PV.rankCard, "TOPLEFT", 12, -8)
    head:SetParent(PV.rankUI)
    head:SetText(T("军衔阶梯"))
    head:Show()
    if SetTip then
        SetTip(head, L["达到军衔后，在暴风城的勇士大厅 / 奥格瑞玛的传说大厅购买奖励；点数按赛季累计，升级不消耗"])
    end
    PV.facBtn1:ClearAllPoints()
    PV.facBtn1:SetPoint("TOPRIGHT", PV.headCard, "TOPRIGHT", -PV.HEAD_PAD, -PV.TAB_Y)
    PV.facBtn2:ClearAllPoints()
    PV.facBtn2:SetPoint("TOPRIGHT", PV.facBtn1, "TOPLEFT", -8, 0)
    PV.facBtn1:Show()
    PV.facBtn2:Show()
    SetButtonSelected(PV.facBtn1, PV.faction == "A")
    SetButtonSelected(PV.facBtn2, PV.faction == "H")
    local lv, lp = LiveState()
    if lv and lv >= 1 then
        PV.rankBadge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", lv))
        PV.rankBadge:SetPoint("TOPRIGHT", PV.rankCard, "TOPRIGHT", -12, -4)
        PV.rankBadge:Show()
        if SetTip then
            SetTip(PV.rankBadge, format(L["当前军衔：R%d · %.0f%%"], lv, (lp or 0) * 100))
        end
    end
    local rh = PV.rankHead
    rh.lvl:SetText(L["军衔"])
    rh.lvl:SetPoint("TOPLEFT", PV.rankCard, "TOPLEFT", 12, -(RH + 5))
    rh.pts:SetPoint("TOPRIGHT", PV.rankCard, "TOPLEFT", 222, -(RH + 5))
    rh.cum:SetPoint("TOPRIGHT", PV.rankCard, "TOPLEFT", 292, -(RH + 5))
    rh.rew:SetPoint("TOPLEFT", PV.rankCard, "TOPLEFT", 304, -(RH + 5))
    for _, fs in pairs(rh) do fs:Show() end
    rh.week:Hide()
    local y0 = RH + 26
    local cursor = 1
    for i = 1, 14 do
        local rec = RD.ranks[i]
        local row = PV.rankRows[i]
        local nm = RANK_NAMES[i]
        row.badge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", i))
        row.name:SetText(PV.faction == "H" and nm.h or nm.a)
        if i == 14 then
            row.name:SetTextColor(1, 0.5, 0, 1)
        else
            row.name:SetTextColor(Unpack(C_GOLD))
        end
        row.pts:SetText(format("%d", rec.pts))
        row.cum:SetText(format("%d", rec.cum))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 12, -(y0 + (i - 1) * 34))
        row:Show()
        if i % 2 == 0 then PY() end
        local all = {}
        local own = (PV.faction == "H") and rec.h or rec.a
        for _, id in ipairs(own) do all[#all + 1] = id end
        for _, id in ipairs(rec.s) do all[#all + 1] = id end
        local shown = math.min(#all, 3)
        for k = 1, shown do
            local chip = PV.chips[cursor]
            cursor = cursor + 1
            chip.__id = all[k]
            chip.iconTex:SetTexture(ItemIcon(all[k]))
            chip:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                304 + (k - 1) * (PV.CHIP + 4), -(y0 + (i - 1) * 34 + 4))
            chip:Show()
            if Host.DG and Host.DG.RequestItem then Host.DG.RequestItem(all[k]) end
            chip:SetParent(row)
        end
        if #all > 3 then
            row.more:SetText(format("+%d", #all - 3))
            row.more:Show()
        else
            row.more:Hide()
        end
        if i % 4 == 0 then PY() end
    end
    local capHead = PV.labels.weekCaps
    capHead:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 12, -8)
    capHead:SetParent(PV.capUI)
    capHead:SetText(T("每周上限"))
    capHead:Show()
    PV.capNote:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 12, -(RH + 2))
    PV.capNote:SetText(T("荣誉逐周累计，第 10 周封顶大元帅；增量为本周需打满的荣誉"))
    PV.capNote:Show()
    local ch = PV.capHead
    ch.week:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 12, -(RH + 24))
    ch.rank:SetPoint("TOPLEFT", PV.capCard, "TOPLEFT", 74, -(RH + 24))
    ch.cum:SetPoint("TOPRIGHT", PV.capCard, "TOPLEFT", 304, -(RH + 24))
    ch.inc:SetPoint("TOPRIGHT", PV.capCard, "TOPLEFT", 380, -(RH + 24))
    for _, fs in pairs(ch) do fs:Show() end
    PY()
    for i = 1, 10 do
        local rec = RD.caps[i]
        local row = PV.wkRows[i]
        local nm = RANK_NAMES[rec.rank]
        row.week:SetText(format(L["第 %d 周"], i))
        row.badge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", rec.rank))
        row.rank:SetText(format("R%d %s", rec.rank, PV.faction == "H" and nm.h or nm.a))
        row.cum:SetText(format("%d", rec.cum))
        row.inc:SetText(format("+%d", rec.inc))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 512 + 12, -(RH + 46 + (i - 1) * 44))
        row:Show()
        if i % 2 == 0 then PY() end
    end
    PV.child:SetHeight(532)
end

function PV.RenderSets()
    local rx = PV.SETS_LIST_W + 12
    local rw = PV.W - rx
    local detX = PV.SETS_DET_X
    PV.setsLeftCard:ClearAllPoints()
    PV.setsLeftCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, 0)
    PV.setsLeftCard:Show()
    PV.setsRightCard:ClearAllPoints()
    PV.setsRightCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", rx, 0)
    PV.setsRightCard:Show()

    local y = 12
    for i = 1, #SD.sets do
        local rec = SD.sets[i]
        local row = PV.setRows[i]
        local file = CLASS_ICON_FILE[rec.class]
        if file then
            row.iconTex:SetTexture(CLASS_ICON_DIR .. file)
        else
            row.iconTex:SetTexture(Host.FALLBACK_ICON)
        end
        row.name:SetText(format("%s · %s",
            (LOCALIZED_CLASS_NAMES_MALE and LOCALIZED_CLASS_NAMES_MALE[rec.class]) or rec.class,
            SPEC_LABEL[rec.spec] or rec.spec))
        row.count:SetText(format("%d", #(rec.blue.A) + #(rec.epic.A)))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 12,
            -(y + (i - 1) * (PV.ROW_H + PV.ROW_GAP)))
        row.name:SetTextColor(Unpack((PV.selSet == i) and C_GOLD or C_TEXT))
        SetButtonSelected(row, PV.selSet == i)
        row:Show()
        if i % 4 == 0 then PY() end
    end
    local n = #SD.sets
    local listBottom = y + n * PV.ROW_H + (n - 1) * PV.ROW_GAP + 12
    PV.setsLeftCard:SetHeight(math.max(listBottom, PV.VIEW_H))

    local mx = detX
    for i = 1, 8 do
        local m = RD.marks[i]
        local chip = PV.markChips[i]
        chip.iconTex:SetTexture(ItemIcon(m.id))
        chip.rank:SetText(format("R%d", m.rank))
        chip:SetPoint("TOPLEFT", PV.child, "TOPLEFT", mx, -PV.MARK_TOP)
        chip:Show()
        if i < 8 then
            local ar = PV.markArrows[i]
            ar:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                mx + PV.MARK_ARROW_DX, -PV.MARK_TOP + PV.MARK_ARROW_DY)
            ar:Show()
        end
        mx = mx + PV.MARK_IN_W + PV.MARK_STEP_GAP
    end
    PV.facBtn2:ClearAllPoints()
    PV.facBtn2:SetPoint("TOPRIGHT", PV.facBtn1, "TOPLEFT", -8, 0)
    PV.facBtn2:Show()
    PV.facBtn1:ClearAllPoints()
    PV.facBtn1:SetPoint("TOPRIGHT", PV.headCard, "TOPRIGHT", -PV.HEAD_PAD, -PV.TAB_Y)
    PV.facBtn1:Show()
    SetButtonSelected(PV.facBtn1, PV.faction == "A")
    SetButtonSelected(PV.facBtn2, PV.faction == "H")

    local selRec = SD.sets[PV.selSet] or SD.sets[1]
    local selRowY = PV.MARK_TOP + PV.MARK_IN_H + PV.CARD_GAP

    local dIcon = PV.setDetailIcon
    local file = CLASS_ICON_FILE[selRec.class]
    dIcon:SetTexture(file and (CLASS_ICON_DIR .. file) or Host.FALLBACK_ICON)
    dIcon:SetPoint("TOPLEFT", PV.child, "TOPLEFT", detX, -(selRowY + 4))
    dIcon:Show()
    local dName = PV.labels.setDetailName
    dName:SetPoint("TOPLEFT", PV.child, "TOPLEFT", detX + 32, -(selRowY + 2))
    dName:SetText((LOCALIZED_CLASS_NAMES_MALE and LOCALIZED_CLASS_NAMES_MALE[selRec.class]) or selRec.class)
    dName:Show()
    local dSpec = PV.labels.setDetailSpec
    dSpec:SetPoint("TOPLEFT", PV.child, "TOPLEFT", detX + 32 + TextW(dName) + 12, -(selRowY + 5))
    dSpec:SetText(SPEC_LABEL[selRec.spec] or selRec.spec)
    dSpec:Show()

    local cy = selRowY + 34
    local innerW = rw - 24
    local cardW = floor((innerW - 16 - PV.CARD_GAP) / PV.CARD_COLS)
    local groups = {
        { key = "setsBlue", offset = 0, label = L["蓝色 · 装等60 · 55 级荣誉直购，不需要军衔"], ids = selRec.blue[PV.faction] },
        { key = "setsEpic", offset = 6,
          label = L["史诗 · 装等65 · 60 级 + 蓝装 + 对应部位无畏印记"], ids = selRec.epic[PV.faction] },
    }
    for _, g in ipairs(groups) do
        local lb = PV.labels[g.key]
        lb:SetPoint("TOPLEFT", PV.child, "TOPLEFT", detX, -cy)
        lb:SetText(g.label)
        lb:Show()
        cy = cy + 24
        for k = 1, 6 do
            local card = PV.cards[g.offset + k]
            card:SetWidth(cardW)
            card.name:SetWidth(cardW - PV.CARD_TX - 7)
            card.name.__pw = cardW - PV.CARD_TX - 7
            PV.PaintCard(card, g.ids[k])
            local col = (k - 1) % PV.CARD_COLS
            local rowi = floor((k - 1) / PV.CARD_COLS)
            card:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                detX + 8 + col * (cardW + PV.CARD_GAP), -(cy + rowi * (PV.CARD_H + 8)))
            card:Show()
        end
        cy = cy + 3 * (PV.CARD_H + 8) + 8
    end

    local note = PV.labels.setsNote
    local noteH = FSHeight(note, 14)
    note:SetPoint("TOPLEFT", PV.child, "TOPLEFT", detX, -(cy + 4))
    note:SetWidth(innerW - 8)
    note:SetText(L["印记门槛：手腕 / 腰部 R8 · 脚 R9 · 手 R10 · 腿 / 肩 R12 · 胸 / 头 R13；每套另有非套装的护腕与腰带"])
    note:Show()
    local rightBottom = cy + 4 + noteH + 12
    PV.setsRightCard:SetHeight(math.max(rightBottom, PV.VIEW_H))
    PV.child:SetHeight(math.max(listBottom, rightBottom, PV.VIEW_H))
end

function PV.RenderHonorBody(y)
    local taskHead = PV.labels.taskHead
    taskHead:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    taskHead:SetText(L["荣誉之地 · 每赛季 10 个每周任务（给荣誉与等级点数，已知目标）"])
    taskHead:Show()
    y = y + 26
    for i = 1, #TASK_TEXTS do
        PV.taskRows[i]:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 12, -y)
        PV.taskRows[i]:Show()
        y = y + 24
    end
    y = y + 8
    local legHead = PV.labels.legHead
    legHead:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    legHead:SetText(L["传承点数 · PvP 侧共 12 点"])
    legHead:Show()
    y = y + 26
    for i = 1, #LEGACY_TEXTS do
        PV.legacyRows[i]:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 12, -y)
        PV.legacyRows[i]:Show()
        y = y + 24
    end
    return y + 4
end

function PV.RenderRep()
    PV.repCard:ClearAllPoints()
    PV.repCard:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, 0)
    PV.repCard:Show()
    local y = 12
    PV.facBtn1:ClearAllPoints()
    PV.facBtn1:SetPoint("TOPRIGHT", PV.headCard, "TOPRIGHT", -PV.HEAD_PAD, -PV.TAB_Y)
    PV.facBtn2:ClearAllPoints()
    PV.facBtn2:SetPoint("TOPRIGHT", PV.facBtn1, "TOPLEFT", -8, 0)
    PV.facBtn1:Show()
    PV.facBtn2:Show()
    SetButtonSelected(PV.facBtn1, PV.faction == "A")
    SetButtonSelected(PV.facBtn2, PV.faction == "H")
    local row = {
        { btn = PV.repBtns[1], key = "spear" },
    }
    for i, bg in ipairs(BATTLE_BGS) do
        row[#row + 1] = { btn = PV.battleBtns[i], key = bg.key }
    end
    row[#row + 1] = { btn = PV.repBtns[2], key = "honor" }
    for i, d in ipairs(row) do
        d.btn:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 12 + (i - 1) * 126, -y)
        SetButtonSelected(d.btn, PV.selRep == d.key)
        d.btn:Show()
    end
    y = y + 30
    if PV.selRep == "honor" then
        y = PV.RenderHonorBody(y)
    elseif BATTLE_KEYS[PV.selRep] then
        y = PV.RenderBattleBody(y)
    else
        y = PV.RenderSpearBody(y)
    end
    PV.repCard:SetHeight(math.max(y + 12, PV.VIEW_H))
    PV.child:SetHeight(math.max(y + 12 + 8, PV.VIEW_H))
end

function PV.RenderBattleBody(y)
    local innerW = PV.W - 24
    local cardW = floor((innerW - 16 - PV.CARD_GAP) / PV.REP_COLS)

    local selKey = PV.selRep or "ab"
    local bg, bi
    for i, b in ipairs(BATTLE_BGS) do
        if b.key == selKey then bg, bi = b, i break end
    end
    bg = bg or BATTLE_BGS[1]
    local meta = BATTLE_META[bg.key]
    local bfByKey = {}
    for _, b in ipairs(RD.battlefields) do bfByKey[b.key] = b end
    local cursor = 1

    local head = PV.labels["bHead" .. bi]
    head:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    head:SetText(bg.label)
    head:Show()
    y = y + 26
    local bf = bfByKey[bg.key]
    local rule = PV.labels["bRule" .. bi]
    rule:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    rule:SetText(format(L["%d 对 %d · %d–%d 级"], bf.size, bf.size, bf.minLevel, bf.maxLevel))
    rule:Show()
    y = y + 24
    local desc = PV.labels["bDesc" .. bi]
    desc:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    desc:SetText(meta[PV.faction] or "")
    desc:Show()
    y = y + FSHeight(desc, 14) + 8
    local items = SD.battle and SD.battle[bg.key]
    if items then
        for si, st in ipairs({ "friendly", "honored", "revered", "exalted" }) do
            local side = items[st]
            local ids = side and (side[PV.faction] or side.A)
            if ids and #ids > 0 then
                local lb = PV.labels["bSec" .. si]
                lb:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
                lb:SetText(format(L["%s · %d 件"], STANDING_LABEL[st], #ids))
                lb:Show()
                y = y + 26
                for k, id in ipairs(ids) do
                    local card = PV.cards[cursor]
                    cursor = cursor + 1
                    card:SetWidth(cardW)
                    card.name:SetWidth(cardW - PV.CARD_TX - 7)
                    card.name.__pw = cardW - PV.CARD_TX - 7
                    PV.PaintCard(card, id)
                    local col = (k - 1) % PV.REP_COLS
                    local rowi = floor((k - 1) / PV.REP_COLS)
                    card:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                        20 + col * (cardW + PV.CARD_GAP), -(y + rowi * (PV.CARD_H + 8)))
                    card:Show()
                end
                y = y + ceil(#ids / PV.REP_COLS) * (PV.CARD_H + 8) + 10
            end
        end
    else
        local ach = PV.labels["bAch" .. bi]
        ach:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
        ach:SetText(meta.ach or "")
        ach:Show()
        y = y + 24
    end
    return y
end

function PV.RenderSpearBody(y)
    local head = PV.labels.spHead
    head:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    head:SetText(L["暗矛群岛 · 新战场"])
    head:Show()
    y = y + 26
    local rule = PV.labels.spRule
    rule:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    rule:SetText(format("%s · %s", L["15 对 15 · 30–60 级"], L["四个据点加中立旗帜，先到 2,000 分获胜"]))
    rule:Show()
    y = y + 24
    local note = PV.labels.spNote
    note:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
    note:SetText(L["排队：主城战场军官 / 贫瘠之地北方城堡（传送门直达商旅海岸）· 声望：塞拉摩远征军 / 暗矛突袭者 · 30–39 级 3 枚奖章换 30 点荣誉与声望，崇拜送战袍"])
    note:Show()
    y = y + FSHeight(note, 14) + 12
    local cardW = floor((PV.W - 24 - 16 - PV.CARD_GAP) / PV.REP_COLS)
    local cursor = 1
    for si, st in ipairs({ "friendly", "honored", "revered", "exalted" }) do
        local side = SD.spear and SD.spear[st]
        local ids = side and (side[PV.faction] or side.A)
        if ids and #ids > 0 then
            local lb = PV.labels["bSec" .. si]
            lb:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 16, -y)
            lb:SetText(format(L["%s · %d 件"], STANDING_LABEL[st], #ids))
            lb:Show()
            y = y + 26
            for k, id in ipairs(ids) do
                local card = PV.cards[cursor]
                cursor = cursor + 1
                card:SetWidth(cardW)
                card.name:SetWidth(cardW - PV.CARD_TX - 7)
                card.name.__pw = cardW - PV.CARD_TX - 7
                PV.PaintCard(card, id)
                local col = (k - 1) % PV.REP_COLS
                local rowi = floor((k - 1) / PV.REP_COLS)
                card:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                    20 + col * (cardW + PV.CARD_GAP), -(y + rowi * (PV.CARD_H + 8)))
                card:Show()
            end
            y = y + ceil(#ids / PV.REP_COLS) * (PV.CARD_H + 8) + 10
        end
    end
    return y
end

LiveState = function()
    local rank, prog, honor, hk = 0, 0, 0, 0
    if type(UnitPVPRank) == "function" and type(GetPVPRankInfo) == "function" then
        local pvpr = UnitPVPRank("player")
        if type(pvpr) == "number" and pvpr > 0 then
            local _, r = GetPVPRankInfo(pvpr)
            if type(r) == "number" then rank = r end
        end
    end
    if type(GetPVPRankProgress) == "function" then
        local p = GetPVPRankProgress()
        if type(p) == "number" then prog = p end
    end
    if type(GetPVPThisWeekStats) == "function" then
        local k, hon = GetPVPThisWeekStats()
        hk = k or 0
        honor = hon or 0
    end
    return rank, prog, honor, hk
end

function PV.RenderWeek()
    local IW = PV.WEEK_CARD_W - 24
    local liveRank, liveProg, honor, hk = LiveState()
    local rank = PV.simRank or liveRank
    local prog = PV.simRank and 0 or liveProg
    if rank == 0 then rank = 1 end

    PV.weekBig:ClearAllPoints()
    PV.weekBig:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, 0)
    PV.weekBig:Show()
    PV.weekCard1:ClearAllPoints()
    PV.weekCard1:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD, -PV.WEEK_PAD)
    PV.weekCard1:Show()
    local y = PV.WEEK_PAD + 12

    local head = PV.labels.sprHead
    head:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -y)
    head:SetText(format("%s · %s", L["本周荣誉"], L["每周结算模型"]))
    head:Show()
    y = y + 26

    PV.badge:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -(y + 4))
    if rank >= 1 then
        PV.badge:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", rank))
        PV.badge:Show()
    end
    local st = PV.labels.sprState
    st:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 66, -y)
    local line1 = (rank >= 2)
        and format(L["军衔 %d · 进度 %.1f%%"], rank, prog * 100)
        or L["军衔 1 及以下无需荣誉：本周 15 次荣誉击杀即可晋级"]
    local line2 = format(L["本周荣誉 %s · 荣誉击杀 %d"], fmtN(honor), hk)
    if PV.simRank then
        line2 = line2 .. " · " .. format(L["模拟中：从 R%d 0%% 起跑（再点一次取消）"], PV.simRank)
    end
    if type(GetSecondsUntilWeeklyReset) == "function" then
        local s = GetSecondsUntilWeeklyReset() or 0
        if s > 0 then
            line2 = line2 .. " · " .. format(L["距每周重置 %d 天 %02d 小时"],
                floor(s / 86400), floor((s % 86400) / 3600))
        end
    end
    st:SetText(line1 .. "\n" .. line2)
    st:Show()
    y = y + 50

    if rank >= 2 and HD.milestones[rank] then
        local mh = PV.labels.sprMile
        mh:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -y)
        mh:SetText(format(L["本周荣誉里程碑（军衔 %d）"], rank))
        mh:Show()
        y = y + 26
        local ms = HD.milestones[rank]
        local bw = IW - 8
        local lastM = ms[#ms]
        PV.mileBG:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -(y + 4))
        PV.mileBG:SetWidth(bw)
        PV.mileBG:SetHeight(12)
        PV.mileBG:Show()
        local x1 = PV.WEEK_PAD + 16 + bw * ms[1] / lastM
        PV.mileRed:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -(y + 4))
        PV.mileRed:SetWidth(math.max(x1 - (PV.WEEK_PAD + 16), 1))
        PV.mileRed:SetHeight(12)
        PV.mileRed:Show()
        for i, m in ipairs(ms) do
            local tx = PV.WEEK_PAD + 16 + bw * m / lastM
            PV.mileTicks[i]:SetPoint("TOPLEFT", PV.child, "TOPLEFT", tx - 1, -(y + 2))
            PV.mileTicks[i]:SetWidth(2)
            PV.mileTicks[i]:SetHeight(16)
            PV.mileTicks[i]:Show()
            local lb = PV.mileLabels[i]
            lb:SetText(fmtN(m))
            lb:SetPoint("TOPLEFT", PV.child, "TOPLEFT",
                math.min(math.max(tx - 32, PV.WEEK_PAD + 16), PV.WEEK_PAD + 16 + IW - 64), -(y + 20))
            lb:Show()
        end
        local mx = PV.WEEK_PAD + 16 + bw * math.min(honor, lastM) / lastM
        PV.mileMark:SetPoint("TOPLEFT", PV.child, "TOPLEFT", mx - 1, -y)
        PV.mileMark:SetWidth(2)
        PV.mileMark:SetHeight(20)
        PV.mileMark:Show()
        y = y + 44
    end

    local gl = PV.labels.sprGoal
    gl:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -(y + 4))
    gl:SetText(L["冲刺目标"])
    gl:Show()
    for i = 1, 13 do
        local bt = PV.goalBtns[i]
        bt:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 122 + (i - 1) * 36, -y)
        SetButtonSelected(bt, PV.goal == i + 1)
        bt:Show()
    end
    y = y + 30

    local sl = PV.labels.sprSim
    sl:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -(y + 4))
    sl:SetText(L["起点模拟 0%"])
    sl:Show()
    for i = 1, 14 do
        local bt = PV.simBtns[i]
        bt:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 122 + (i - 1) * 36, -y)
        SetButtonSelected(bt, PV.simRank == i)
        bt:Show()
    end
    y = y + 32

    local goal = PV.goal or 14
    local start = PV.simRank or rank
    local startProg = PV.simRank and 0 or prog
    local p1 = PV.labels.sprPath1
    local p2 = PV.labels.sprPath2
    p1:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -y)
    if start >= goal then
        p1:SetText(L["已达该军衔"])
        p2:SetText("")
    else
        local total, weeks, fNeed, fRank, fProg = SimplePath(start, startProg, goal)
        if weeks == 0 or not fNeed then
            p1:SetText(L["路径卡住：当前进度无法继续推进"])
            p2:SetText("")
        else
            p1:SetText(format(L["达到 %s：约 %d 周 · 共 %s 荣誉"],
                format("R%d", goal), weeks, fmtN(total)))
            p2:SetText(format(L["本周先打 %s 荣誉 → 重置后 %s"],
                fmtN(fNeed), format("R%d · %.0f%%", fRank, (fProg or 0) * 100)))
        end
    end
    p1:Show()
    p2:SetPoint("TOPLEFT", p1, "TOPRIGHT", 12, 0)
    p2:Show()
    y = y + 28
    PV.weekCard1:SetHeight(y + 12 - PV.WEEK_PAD)
    local h1 = y + 12 - PV.WEEK_PAD

    local card2Top = PV.WEEK_PAD + h1 + PV.WEEK_PAD
    PV.weekCard2:ClearAllPoints()
    PV.weekCard2:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD, -card2Top)
    PV.weekCard2:Show()
    y = card2Top + 12

    local capsHead = PV.labels.weekCaps
    capsHead:SetParent(PV.child)
    capsHead:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -y)
    capsHead:SetText(L["周上限 · 按赛季累计点数"])
    capsHead:Show()
    y = y + 26
    local maxCum = RD.caps[10].cum
    local halfW = floor(IW / 2) - 16
    for i = 1, 10 do
        local rec = RD.caps[i]
        local row = PV.capRows[i]
        local col = (i - 1) % 2
        local rowi = floor((i - 1) / 2)
        row.week:SetText(format(L["第 %d 周"], i))
        row.rank:SetText(format("R%d", rec.rank))
        row.bar:SetWidth(floor(120 * rec.cum / maxCum))
        row.cum:SetText(format("%d", rec.cum))
        row.inc:SetText(format("+%d", rec.inc))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 12 + col * (halfW + 32), -(y + rowi * 30))
        row:Show()
    end
    y = y + 5 * 30
    local cfoot = PV.labels.capsFoot
    local cfootH = FSHeight(cfoot, 14)
    cfoot:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.WEEK_PAD + 16, -(y + 6))
    cfoot:SetText(L["等级 4 和 10 永远不是某周的上限；第 7 周一次跳两级（等级 11 与黑色战争坐骑）；上限按赛季累计点数计算，晚开始可直接冲级"])
    cfoot:Show()
    local h2 = y + 6 + cfootH + 12 - card2Top
    h2 = math.max(h2, PV.VIEW_H - card2Top - PV.WEEK_PAD)
    PV.weekCard2:SetHeight(h2)
    local bigH = math.max(card2Top + h2 + PV.WEEK_PAD, PV.VIEW_H)
    PV.weekBig:SetHeight(bigH)
    PV.child:SetHeight(bigH)
end
