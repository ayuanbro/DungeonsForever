local ns = _G.DF_NS or {}

local L = ns.L
local format = string.format
local floor = math.floor
local max = math.max
local min = math.min

local Host = ns.ProfHost
if not Host then return end

local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local SetButtonSelected = Host.SetButtonSelected
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

FV.QCOL = 196
FV.QGAP = GUTTER
FV.QDET = FV.RW - 28 - FV.QCOL - GUTTER
FV.QBAR = 7
FV.QTXT = FV.QDET - FV.QBAR - 8
FV.QTOP = 40
FV.QROW_H = 40
FV.QROW_PITCH = 42
FV.QROW_W = FV.QCOL - FV.QBAR
FV.QHEAD_H = 22
FV.QST_H = (ns.hui and ns.hui.ChipH and ns.hui.ChipH(14)) or 13.7
FV.QTIERS = { "buy", "fr", "ho" }
FV.QTIER_W = { 80, 56, 56 }

local QT_LABEL = { buy = L["中立 → 友善"], fr = L["友善"], ho = L["尊敬"] }
local QT_BTN = { buy = L["中立"], fr = L["友善"], ho = L["尊敬"] }
local QT_COLOR = { buy = STANDINGS[4].color, fr = STANDINGS[5].color, ho = STANDINGS[6].color }
local QSIDE_TXT = { both = L["双阵营"], ally = L["联盟"], horde = L["部落"] }
local Q_STATE_TXT = {
    done = L["你已完成此任务。"],
    ready = L["你已完成任务目标，回去交付吧。"],
    active = L["你已接取此任务，尚未完成。"],
    todo = L["你还没有接取此任务。"],
    rep = L["可重复任务，可反复完成。"],
}
local TAB_DEF = {
    { key = "reward", text = L["奖励"] },
    { key = "quest", text = L["任务"] },
}
local Q_GREEN = { 0x6F / 255, 0xBF / 255, 0x5A / 255 }
local Q_RED = { 0xC7 / 255, 0x4A / 255, 0x3C / 255 }
local Q_PIN = "Interface\\AddOns\\DungeonsForever\\Media\\Pins\\EntryPin"
local Q_ROWSEL = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\DF_RowSelGradFac"
local Q_INK_DIM = "|cff9a9a9a"
local Q_INK_GREY = "|cff8c8c8c"
local Q_INK_GOLD = "|cffffd100"
local Q_END = "|r"

local function Cfg()
    local db = ns.FactionDB()
    db.factions = db.factions or {}
    local c = db.factions
    if c.ally == nil then c.ally = true end
    if c.enemy == nil then c.enemy = false end
    if c.neutral == nil then c.neutral = true end
    if c.search == nil then c.search = "" end
    if type(c.fav) ~= "table" then c.fav = {} end
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
    if C_Map and C_Map.SetUserWaypoint and _G.CreateVector2D
        and (not C_Map.CanSetUserWaypointOnMap or C_Map.CanSetUserWaypointOnMap(mapID)) then
        local wp = { uiMapID = mapID, position = _G.CreateVector2D(qx / 100, qy / 100) }
        pcall(C_Map.SetUserWaypoint, wp)
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

function FV:SyncFav()
    local fb = FV.favBtn
    if not fb then return end
    local x = FacBySel(Cfg().sel)
    local on = (x and Cfg().fav[x.id]) and true or false
    fb:SetText(on and L["已收藏"] or L["收藏"])
    SetButtonSelected(fb, on, "tab")
end

function FV:ToggleFav()
    local x = FacBySel(Cfg().sel)
    if not x then return end
    local c = Cfg()
    if c.fav[x.id] then c.fav[x.id] = nil else c.fav[x.id] = true end
    ns.PlaySound(1)
    FV:SyncFav()
    FV:PaintList()
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
    if not HasRewards(x) then
        local qs = type(ns.FactionQuests) == "table" and ns.FactionQuests[x.id]
        if not (type(qs) == "table" and #qs > 0) then return false end
    end
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
    if ns.hui and ns.hui.MakeSolidChip then
        local f = ns.hui.MakeSolidChip(parent, nil, ns.hui.ChipH(14))
        f.txt = f.t
        f.__border = f.__chipBorder
        return f
    end
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
    local pad = (ns.hui and ns.hui.CHIP_S_PAD) or 5
    local minw = (ns.hui and ns.hui.CHIP_S_MIN_W) or 24
    f:SetWidth(math.max(tw + pad * 2, minw))
    if f.__chipFill and ns.hui and ns.hui.PaintSolidFill and ns.hui.ChipSolidBase then
        local ink = color or { 0.64, 0.61, 0.55 }
        ns.hui.PaintSolidFill(f.__chipFill, ns.hui.ChipSolidBase(ink))
        if f.__chipBorder then
            for _, t in ipairs(f.__chipBorder) do
                t:SetVertexColor(ink[1], ink[2], ink[3])
                t:SetAlpha(1)
            end
        end
        f.txt:SetTextColor(1, 1, 1)
        return
    end
    if f.__border and color then
        for _, t in ipairs(f.__border) do t:SetVertexColor(color[1], color[2], color[3]) end
    end
    if color then
        f.txt:SetTextColor(color[1], color[2], color[3])
    else
        f.txt:SetTextColor(Unpack(C_TEXT))
    end
end

FV.WIN_BUF = 3
FV.ROW_PITCH = FV.ROW_H + FV.LIST_GAP
FV.ROW_INIT = 8

local function MakeRow(parent)
    local r = CreateFrame("Button", nil, parent)
    r:SetSize(FV.LROW_W, FV.ROW_H)
    if HUI and ns.hui.HuiCardFX then
        ns.hui.HuiCardFX(r, 6, 2)
    end
    r.name = MakeFS(r, 14, C_TEXT, "LEFT")
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -2)
    r.name:SetWidth(FV.LROW_W - 60)
    r.name:SetWordWrap(false)
    r.sub = MakeFS(r, 12, C_GREY, "LEFT")
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -22)
    r.sub:SetWordWrap(false)
    r.badge = MakeFS(r, 14, C_TEXT, "RIGHT")
    r.badge:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -11)
    r:EnableMouse(true)
    r:SetScript("OnEnter", function(self)
        if self.__huiCard and ns.hui.HuiCardState and not self.__selActive then
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
        FV:SelectFaction(self.__fid)
    end)
    r:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(FV.lScroll, FV.lChild, delta)
        FV:CullLeft()
    end)
    r:Hide()
    return r
end

local function QuestListOf(fid)
    local all = type(ns.FactionQuests) == "table" and ns.FactionQuests[fid] or nil
    if type(all) ~= "table" then return nil end
    return all
end

local function NpcInfo(nid)
    local n = type(ns.FactionNpcs) == "table" and ns.FactionNpcs[nid] or nil
    return type(n) == "table" and n or nil
end

local function NpcName(nid)
    local n = NpcInfo(nid)
    if n and type(n.name) == "string" and n.name ~= "" then return n.name end
    return format(L["NPC #%d"], nid or 0)
end

local function NpcLoc(nid)
    local n = NpcInfo(nid)
    if not n then return nil end
    if type(n.x) == "number" and type(n.y) == "number" then
        return { type(n.map) == "number" and n.map or 1443, n.x, n.y }
    end
    return nil
end

local function QNameByID(id)
    if id and DG and DG.QuestName then
        local ok, nm = pcall(DG.QuestName, id)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return format(L["任务 #%d"], id or 0)
end

local function QName(q)
    local id = (type(q.id) == "table") and (q.id[1] or q.id[2]) or nil
    return QNameByID(id)
end

local function FindQuest(list, qid)
    if not (type(list) == "table" and type(qid) == "number") then return nil end
    for _, q in ipairs(list) do
        local ids = q.id
        if type(ids) == "table" then
            for _, id in ipairs(ids) do
                if id == qid then return q end
            end
        end
    end
    return nil
end

local function QStateOf(qid)
    if qid and DG and DG.QuestBadgeState then
        local ok, st = pcall(DG.QuestBadgeState, qid)
        if ok and type(st) == "string" then return st end
    end
    return "todo"
end

local function QStateCol(st)
    if DG and DG.QStateColor then
        local ok, c = pcall(DG.QStateColor, st)
        if ok and type(c) == "table" and type(c[1]) == "number" then return c end
    end
    return C_GREY
end

local Q_TEX_DISC = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc"
local Q_TEX_TICK = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckMark"
local Q_TEX_IN = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkTurnIn"
local Q_TEX_ASK = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkAsk"
local Q_TEX_EXCL = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkExcl"

local function QBadgeSpec(st)
    local g = DG or {}
    if st == "done" then return g.Q_OV_DONE, Q_TEX_TICK, { 0.043, 0.239, 0.102 } end
    if st == "ready" then return g.Q_OV_READY, Q_TEX_IN, { 0.020, 0.180, 0.172 } end
    if st == "active" then return g.Q_OV_ACT, Q_TEX_ASK, { 0.227, 0.165, 0 } end
    if st == "rep" then return g.Q_OV_REP, Q_TEX_ASK, { 0.18, 0.14, 0.26 } end
    return g.Q_OV_TODO, Q_TEX_EXCL, { 0.102, 0.102, 0.102 }
end

local function QuestXP(qid)
    local idx
    if C_QuestLog and C_QuestLog.GetLogIndexForQuestID then
        local ok, v = pcall(C_QuestLog.GetLogIndexForQuestID, qid)
        if ok and type(v) == "number" then idx = v end
    end
    if not idx and type(GetQuestLogIndexByID) == "function" then
        local ok, v = pcall(GetQuestLogIndexByID, qid)
        if ok and type(v) == "number" then idx = v end
    end
    if type(idx) == "number" and idx > 0 and type(GetQuestLogRewardXP) == "function" then
        local ok, xp = pcall(GetQuestLogRewardXP, idx)
        if ok and type(xp) == "number" then return xp end
    end
    return nil
end

local function FacNameByID(fid)
    local d = FacData(fid)
    if d and type(d.name) == "string" and d.name ~= "" then return d.name end
    if type(GetFactionInfoByID) == "function" then
        local ok, nm = pcall(GetFactionInfoByID, fid)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    local x = FacBySel(fid)
    if x then return FacName(x) end
    return format("#%d", fid or 0)
end

local function TxtH(fs, fallback)
    if not fs then return fallback or 20 end
    local h = fs.GetStringHeight and fs:GetStringHeight() or 0
    if type(h) ~= "number" or h <= 0 then h = fallback or 20 end
    return h
end

local function Hex(c)
    if DG and DG.Hex then return DG.Hex(c) end
    return format("|cff%02x%02x%02x", floor(c[1] * 255), floor(c[2] * 255), floor(c[3] * 255))
end

local function StageOf(list)
    local d = ns.FactionDB()
    local st = d.fqstage
    if st ~= "buy" and st ~= "fr" and st ~= "ho" then st = "buy" end
    if type(list) == "table" then
        local hit = 0
        for _, q in ipairs(list) do
            if q.tier == st then hit = hit + 1 end
        end
        if hit == 0 then
            for _, key in ipairs(FV.QTIERS) do
                for _, q in ipairs(list) do
                    if q.tier == key then st = key hit = 1 break end
                end
                if hit > 0 then break end
            end
        end
    end
    d.fqstage = st
    return st
end

local function SelQuestOf(fid, list, stage)
    if type(list) ~= "table" then return nil end
    local d = ns.FactionDB()
    d.fqsel = d.fqsel or {}
    local want = d.fqsel[fid]
    local first
    for _, q in ipairs(list) do
        if q.tier == stage then
            if not first then first = q end
            local ids = q.id
            if want and type(ids) == "table" then
                for _, id in ipairs(ids) do
                    if id == want then return q end
                end
            end
        end
    end
    if first then
        d.fqsel[fid] = first.id[1]
        return first
    end
    return nil
end

local function MakeScrollBar(sc, ch, host)
    local bar = CreateFrame("Frame", nil, host, "BackdropTemplate")
    if HUI and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(bar, 3, ns.hui.layer.L2)
    else
        bar:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        bar:SetBackdropColor(0, 0, 0, 0.25)
        bar:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    bar:SetWidth(FV.QBAR)
    bar:SetPoint("TOPRIGHT", sc, "TOPRIGHT", 0, -2)
    bar:SetPoint("BOTTOMRIGHT", sc, "BOTTOMRIGHT", 0, 2)
    bar:SetFrameLevel((sc:GetFrameLevel() or 0) + 10)
    bar:Hide()
    local thumb = CreateFrame("Button", nil, bar)
    thumb:SetWidth(5)
    thumb:EnableMouse(true)
    local tp
    if HUI and ns.hui.BuildCapsule then
        tp = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
    else
        local tx = thumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
        tp = { tx }
    end
    thumb:SetScript("OnEnter", function()
        local c5 = ns.hui and ns.hui.layer and ns.hui.layer.L5
        if not (tp and c5) then return end
        for _, t in ipairs(tp) do t:SetVertexColor(c5[1], c5[2], c5[3]) end
    end)
    thumb:SetScript("OnLeave", function()
        local c4 = ns.hui and ns.hui.layer and ns.hui.layer.L4
        if not (tp and c4) then return end
        for _, t in ipairs(tp) do t:SetVertexColor(c4[1], c4[2], c4[3]) end
    end)
    thumb:SetPoint("TOP", bar, "TOP", 0, -1)
    local function Update()
        if not sc:IsShown() then bar:Hide() return end
        local viewH = tonumber(sc.GetHeight and sc:GetHeight())
        local contentH = tonumber(ch.GetHeight and ch:GetHeight())
        if not (viewH and contentH) or contentH <= viewH + 2 or viewH <= 0 then
            bar:Hide()
            return
        end
        bar:Show()
        local trackH = bar:GetHeight() - 2
        local maxScroll = contentH - viewH
        local v = tonumber(sc.GetVerticalScroll and sc:GetVerticalScroll()) or 0
        local frac = min(1, max(0, v / maxScroll))
        local th = max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", bar, "TOP", 0, -1 - frac * (trackH - th))
    end
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent.GetEffectiveScale and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = tonumber(sc.GetVerticalScroll and sc:GetVerticalScroll()) or 0
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = bar:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local contentH = tonumber(ch.GetHeight()) or 0
            local viewH = tonumber(sc:GetHeight()) or 0
            local maxScroll = contentH - viewH
            if maxScroll <= 0 then return end
            sc:SetVerticalScroll(min(maxScroll, max(0, sc0 + (cy0 - cy) / span * maxScroll)))
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    return bar, Update
end

local function MakeMapBtn(parent)
    local bt = NewButton(parent, L["地图"], 68, 24, 14)
    local t = bt:CreateTexture(nil, "OVERLAY")
    t:SetTexture(Q_PIN)
    t:SetSize(12, 12)
    t:SetPoint("LEFT", bt, "LEFT", 4, 0)
    local fs = bt:GetFontString()
    if fs then
        fs:ClearAllPoints()
        fs:SetPoint("TOPLEFT", bt, "TOPLEFT", 18, 0)
        fs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)
        fs:SetJustifyH("CENTER")
    end
    return bt
end

local function MakeQRow(parent)
    local r = CreateFrame("Button", nil, parent)
    r:SetSize(FV.QROW_W, FV.QROW_H)
    if HUI and ns.hui.HuiCardFX then
        ns.hui.HuiCardFX(r, 6, 2)
    end
    r.stDisc = r:CreateTexture(nil, "ARTWORK")
    r.stDisc:SetSize(FV.QST_H, FV.QST_H)
    r.stDisc:SetPoint("RIGHT", r, "RIGHT", -8, 0)
    r.stDisc:SetTexture(Q_TEX_DISC)
    r.stGlyph = r:CreateTexture(nil, "OVERLAY")
    r.stGlyph:SetAllPoints(r.stDisc)
    r.name = MakeFS(r, 14, C_TEXT, "LEFT")
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 12, -5)
    r.name:SetWidth(FV.QROW_W - 12 - FV.QST_H - 14)
    r.name:SetWordWrap(false)
    r.sub = MakeFS(r, 12, C_GREY, "LEFT")
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 12, -24)
    r.sub:SetWidth(FV.QROW_W - 12 - FV.QST_H - 14)
    r.sub:SetWordWrap(false)
    r:EnableMouse(true)
    r:SetScript("OnEnter", function(self)
        if self.__huiCard and ns.hui.HuiCardState and not self.__selActive then
            ns.hui.HuiCardState(self, "hover")
            self.__hst = "hover"
        end
        if self.__tip and SetTip then SetTip(self, self.__tip) end
    end)
    r:SetScript("OnLeave", function(self)
        if self.__huiCard and ns.hui.HuiCardState and not self.__selActive then
            ns.hui.HuiCardState(self, "norm")
            self.__hst = "norm"
        end
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function(self)
        if not self.__qid then return end
        ns.PlaySound(1)
        FV:SelectQuest(self.__qid)
    end)
    r:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(FV.qScroll, FV.qChild, delta)
        FV:PaintQuestList()
    end)
    r:Hide()
    return r
end

local function MakeQNpc(parent)
    local f = CreateFrame("Button", nil, parent)
    f:SetSize(FV.QTXT, 24)
    f:EnableMouse(true)
    f:EnableMouseWheel(true)
    f:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(FV.qdScroll, FV.qdChild, delta)
        FV:CullQuestDetail()
    end)
    f.fs = MakeFS(f, 14, C_TEXT, "LEFT")
    f.fs:SetPoint("TOPLEFT", f, "TOPLEFT", 0, 0)
    f.fs:SetWordWrap(false)
    f.btn = MakeMapBtn(f)
    f.btn:SetPoint("TOPRIGHT", f, "TOPRIGHT", 0, 0)
    f.btn:SetScript("OnClick", function(self)
        local row = self:GetParent()
        FV:MarkNpc(row.__npc, row.__loc)
    end)
    f.btn:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:AddLine(L["在地图上标记该 NPC"], 1, 0.82, 0)
        GameTooltip:Show()
    end)
    f.btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    f:Hide()
    return f
end

local function MakeQPre(parent)
    local f = CreateFrame("Button", nil, parent)
    f:SetSize(FV.QTXT, 30)
    if HUI and ns.hui.HuiCardFX then
        ns.hui.HuiCardFX(f, 6, 2)
    end
    f:EnableMouse(true)
    f:EnableMouseWheel(true)
    f:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(FV.qdScroll, FV.qdChild, delta)
        FV:CullQuestDetail()
    end)
    f.txt = MakeFS(f, 14, C_GOLD, "LEFT")
    f.txt:SetPoint("LEFT", f, "LEFT", 10, 0)
    f.txt:SetWordWrap(false)
    f:SetScript("OnEnter", function(self)
        if self.__huiCard and ns.hui.HuiCardState then
            ns.hui.HuiCardState(self, "hover")
            self.__hst = "hover"
        end
    end)
    f:SetScript("OnLeave", function(self)
        if self.__huiCard and ns.hui.HuiCardState then
            ns.hui.HuiCardState(self, "norm")
            self.__hst = "norm"
        end
    end)
    f:SetScript("OnClick", function(self)
        if not self.__qid then return end
        ns.PlaySound(1)
        FV:SelectQuest(self.__qid)
    end)
    f:Hide()
    return f
end

local function MakeQGoal(parent)
    local f = CreateFrame("Frame", nil, parent)
    f:SetSize(FV.QTXT, 20)
    f.dot = f:CreateTexture(nil, "ARTWORK")
    f.dot:SetSize(4, 4)
    f.dot:SetPoint("TOPLEFT", f, "TOPLEFT", 1, -8)
    f.dot:SetColorTexture(0.55, 0.55, 0.55, 1)
    f.txt = MakeFS(f, 14, C_TEXT, "LEFT")
    f.txt:SetPoint("TOPLEFT", f, "TOPLEFT", 10, 0)
    f.txt:SetWidth(FV.QTXT - 12)
    f.txt:SetWordWrap(false)
    f:Hide()
    return f
end

local function MakeQItem(parent)
    local cd = CreateFrame("Button", nil, parent)
    cd:SetSize(FV.QTXT, 44)
    if HUI and ns.hui.HuiCardFX then
        ns.hui.HuiCardFX(cd, 12, 2)
    end
    cd.iconTex = cd:CreateTexture(nil, "ARTWORK")
    cd.iconTex:SetSize(32, 32)
    cd.iconTex:SetPoint("LEFT", cd, "LEFT", 6, 0)
    cd.iconTex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if HUI and ns.hui.RoundIcon then ns.hui.RoundIcon(cd.iconTex) end
    cd.name = MakeFS(cd, 14, C_TEXT, "LEFT")
    cd.name:SetPoint("TOPLEFT", cd, "TOPLEFT", 46, -6)
    cd.name:SetWidth(FV.QTXT - 54)
    cd.name:SetWordWrap(false)
    cd.meta = MakeFS(cd, 12, C_GREY, "LEFT")
    cd.meta:SetPoint("TOPLEFT", cd, "TOPLEFT", 46, -26)
    cd.meta:SetWordWrap(false)
    cd:EnableMouse(true)
    cd:EnableMouseWheel(true)
    cd:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(FV.qdScroll, FV.qdChild, delta)
        FV:CullQuestDetail()
    end)
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
    cd:Hide()
    return cd
end

function FV:MarkNpc(nid, loc)
    if type(loc) ~= "table" then return end
    local mapID, qx, qy = loc[1], loc[2], loc[3]
    if type(mapID) ~= "number" or type(qx) ~= "number" or type(qy) ~= "number" then return end
    if C_Map and C_Map.SetUserWaypoint and _G.CreateVector2D then
        local wp = { uiMapID = mapID, position = _G.CreateVector2D(qx / 100, qy / 100) }
        pcall(C_Map.SetUserWaypoint, wp)
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

function FV:PaintQItem(cd, id)
    cd.__id = id
    local nm, ok
    if DG and DG.ItemName then nm, ok = DG.ItemName(id) end
    if ok then
        local budget = cd.__nameW or (FV.QTXT - 54)
        cd.name:SetText((DG and DG.FitText and DG.FitText(nm, 14, budget)) or nm)
        if DG and DG.QColor and DG.QualOf then
            local qr, qg, qb = DG.QColor(DG.QualOf(id))
            if qr then cd.name:SetTextColor(qr, qg, qb) end
        end
    else
        cd.name:SetText(format(L["物品 #%d"], id or 0))
        cd.name:SetTextColor(Unpack(C_GREY))
        if DG and DG.RequestItem then DG.RequestItem(id) end
    end
    cd.meta:SetText((DG and DG.ItemMeta and DG.ItemMeta(id)) or "")
    if DG and DG.ItemIcon then cd.iconTex:SetTexture(DG.ItemIcon(id)) end
    if ns.hui and ns.hui.SetIconRing then
        local qq = (DG and DG.QualOf) and DG.QualOf(id) or nil
        ns.hui.SetIconRing(cd.iconTex, qq and { ns.hui.QColor(qq) } or nil)
    end
end

FV.Build = function(page)
    if FV.built or FV.building then return end
    FV.building = true
    ns.FactionPhased(25, coroutine.create(function()
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
    eb:SetFont(ns.FONT, 11, "")
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

    local fb = NewButton(leftCard, (ns.SYM.tri .. " ") .. L["筛选"], 88, 24, 14)
    fb:SetPoint("TOPRIGHT", leftCard, "TOPRIGHT", -FV.PAD, -10)
    SetButtonSelected(fb, false)
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
        bt.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckRing")
        bt.disc = boxF:CreateTexture(nil, "ARTWORK")
        bt.disc:SetAllPoints()
        bt.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc")
        bt.tick = boxF:CreateTexture(nil, "OVERLAY")
        bt.tick:SetAllPoints()
        bt.tick:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckMark")
        bt.label = MakeFS(bt, 14, C_TEXT, "LEFT")
        bt.label:SetPoint("LEFT", boxF, "RIGHT", 7, 0)
        bt.label:SetText(opt.text)
        bt:SetScript("OnClick", function()
            ns.PlaySound(1)
            local c = Cfg()
            c[opt.key] = not c[opt.key]
            FV:SyncPopup()
            FV.RequestRender()
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
    scroll:HookScript("OnVerticalScroll", function()
        FV:PaintList()
    end)
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
            FV:PaintList()
        end)
    end)
    vthumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    vthumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    coroutine.yield()

    FV.rows = {}
    for i = 1, FV.ROW_INIT do
        FV.rows[i] = MakeRow(child)
        if i % 4 == 0 then coroutine.yield() end
    end
    coroutine.yield()
    FV:SyncPopup()
    FV:PaintList()
    coroutine.yield()

    FV.tabs = {}
    for i, def in ipairs(TAB_DEF) do
        local bt = NewButton(rightCard, def.text, 60, 24, 14)
        bt:SetPoint("TOPLEFT", rightCard, "TOPLEFT", 14 + (i - 1) * 68, -8)
        bt.__key = def.key
        bt:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            FV:SetTab(self.__key)
        end)
        FV.tabs[i] = bt
        coroutine.yield()
    end

    local dScroll = CreateFrame("ScrollFrame", nil, rightCard)
    dScroll:SetPoint("TOPLEFT", rightCard, "TOPLEFT", 0, -FV.QTOP)
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
    FV.dIcon:SetSize(16, 16)
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

    local qPage = CreateFrame("Frame", nil, rightCard)
    qPage:SetPoint("TOPLEFT", rightCard, "TOPLEFT", 14, -FV.QTOP)
    qPage:SetPoint("BOTTOMRIGHT", rightCard, "BOTTOMRIGHT", -14, 12)
    qPage:Hide()
    FV.qPage = qPage

    FV.stageBtns = {}
    local sx = 0
    for i, key in ipairs(FV.QTIERS) do
        local bt = NewButton(qPage, QT_BTN[key], FV.QTIER_W[i], 24, 12)
        bt:SetPoint("TOPLEFT", qPage, "TOPLEFT", sx, 0)
        bt.__huiKeepTextColor = true
        bt.__key = key
        bt:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            FV:SetStage(self.__key)
        end)
        FV.stageBtns[i] = bt
        sx = sx + FV.QTIER_W[i] + 2
        coroutine.yield()
    end

    local qScroll = CreateFrame("ScrollFrame", nil, qPage)
    qScroll:SetPoint("TOPLEFT", qPage, "TOPLEFT", 0, -28)
    qScroll:SetPoint("BOTTOMRIGHT", qPage, "BOTTOMLEFT", FV.QCOL, 0)
    qScroll:EnableMouseWheel(true)
    qScroll:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(qScroll, FV.qChild, delta)
        FV:PaintQuestList()
    end)
    local qChild = CreateFrame("Frame", nil, qScroll)
    qChild:SetSize(FV.QROW_W, 10)
    qScroll:SetScrollChild(qChild)
    qScroll:HookScript("OnVerticalScroll", function() FV:PaintQuestList() end)
    FV.qScroll, FV.qChild = qScroll, qChild
    coroutine.yield()

    local dqScroll = CreateFrame("ScrollFrame", nil, qPage)
    dqScroll:SetPoint("TOPLEFT", qPage, "TOPLEFT", FV.QCOL + FV.QGAP, 0)
    dqScroll:SetPoint("BOTTOMRIGHT", qPage, "BOTTOMRIGHT", -FV.QBAR, 0)
    dqScroll:EnableMouseWheel(true)
    dqScroll:SetScript("OnMouseWheel", function(_, delta)
        WheelTo(dqScroll, FV.qdChild, delta)
        FV:CullQuestDetail()
    end)
    local dqChild = CreateFrame("Frame", nil, dqScroll)
    dqChild:SetSize(FV.QTXT, 10)
    dqScroll:SetScrollChild(dqChild)
    dqScroll:HookScript("OnVerticalScroll", function() FV:CullQuestDetail() end)
    FV.qdScroll, FV.qdChild = dqScroll, dqChild
    coroutine.yield()

    FV.qlBar, FV.UpdateQlBar = MakeScrollBar(qScroll, qChild, qPage)
    FV.qdBar, FV.UpdateQdBar = MakeScrollBar(dqScroll, dqChild, qPage)
    coroutine.yield()

    local head = CreateFrame("Frame", nil, qChild)
    head:SetSize(FV.QROW_W, FV.QHEAD_H)
    head.lab = MakeFS(head, 13, C_TEXT, "LEFT")
    head.lab:SetPoint("LEFT", head, "LEFT", 0, 0)
    head.lab:SetWordWrap(false)
    head.line = head:CreateTexture(nil, "ARTWORK")
    head.line:SetHeight(1)
    head:Hide()
    FV.qHead = head

    FV.qEmpty = MakeFS(qChild, 14, C_GREY, "LEFT")
    FV.qEmpty:SetPoint("TOPLEFT", qChild, "TOPLEFT", 0, 0)
    FV.qEmpty:SetText(L["本阵营暂无任务数据"])
    FV.qEmpty:Hide()
    coroutine.yield()

    FV.qdName = MakeFS(dqChild, 16, C_GOLD, "LEFT")
    FV.qdName:SetWordWrap(false)
    FV.qdSub = MakeFS(dqChild, 14, C_GREY, "LEFT")
    FV.qdSub:SetWordWrap(false)
    FV.qdChip = {}
    for i = 1, 3 do
        local ch = MakeChip(dqChild)
        ch:Hide()
        FV.qdChip[i] = ch
    end
    coroutine.yield()

    FV.qdNpc = {}
    for i = 1, 4 do
        FV.qdNpc[i] = MakeQNpc(dqChild)
        coroutine.yield()
    end

    FV.qdPre = {}
    for i = 1, 3 do
        FV.qdPre[i] = MakeQPre(dqChild)
    end

    FV.qdLab = {}
    for i = 1, 8 do
        local f = MakeFS(dqChild, 14, C_TEXT, "LEFT")
        f:SetWordWrap(false)
        f:Hide()
        FV.qdLab[i] = f
    end
    coroutine.yield()

    FV.qdObj = MakeFS(dqChild, 14, C_TEXT, "LEFT")
    FV.qdObj:Hide()
    FV.qdDesc = MakeFS(dqChild, 14, C_GREY, "LEFT")
    FV.qdDesc:Hide()

    FV.qdGoal = {}
    for i = 1, 4 do
        FV.qdGoal[i] = MakeQGoal(dqChild)
    end
    FV.qdItem = {}
    for i = 1, 3 do
        FV.qdItem[i] = MakeQItem(dqChild)
        coroutine.yield()
    end
    FV.qdGain = {}
    for i = 1, 4 do
        local f = MakeFS(dqChild, 14, C_TEXT, "LEFT")
        f:SetWordWrap(false)
        f:Hide()
        FV.qdGain[i] = f
    end
    FV.qdSep = CreateFrame("Frame", nil, dqChild)
    FV.qdSep:SetSize(FV.QTXT, 1)
    local sline = FV.qdSep:CreateTexture(nil, "BACKGROUND")
    sline:SetAllPoints(FV.qdSep)
    sline:SetColorTexture(0x1B / 255, 0x20 / 255, 0x29 / 255, 1)
    FV.qdSep:Hide()
    FV.qdState = MakeFS(dqChild, 14, C_GREY, "LEFT")
    FV.qdState:Hide()
    FV.qRows = {}
    coroutine.yield()

    local qb = NewButton(rightCard, L["军需官位置"], 104, 24, 14)
    qb:SetPoint("TOPRIGHT", rightCard, "TOPRIGHT", -14, -8)
    local qfs = qb:GetFontString()
    local qt = qb:CreateTexture(nil, "OVERLAY")
    qt:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Pins\\EntryPin")
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

    local fb = NewButton(rightCard, L["收藏"], 78, 24, 14)
    fb:SetPoint("TOPRIGHT", rightCard, "TOPRIGHT", -14 - 104 - 6, -8)
    fb.__huiKeepTextColor = true
    fb:SetScript("OnClick", function() FV:ToggleFav() end)
    fb:SetScript("OnEnter", function(self)
        if GameTooltip then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:AddLine(L["点击：收藏该阵营并置顶显示"], 1, 0.82, 0)
            GameTooltip:Show()
        end
    end)
    fb:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    FV.favBtn = fb

    FV.built = true
    FV.building = false
    FV:SyncTabShown()
    FV:PaintTab()
    FV:SyncFav()
    if FV:Tab() == "quest" then
        FV:PaintQuestList()
        FV:PaintQuestDetail()
    else
        FV:PaintDetail()
    end
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

function FV:CullQuestList()
    if not FV.qCull then return end
    Cull(FV.qScroll, FV.qCull)
    if FV.UpdateQlBar then FV.UpdateQlBar() end
end

function FV:CullQuestDetail()
    if not FV.qdCull then return end
    Cull(FV.qdScroll, FV.qdCull)
    if FV.UpdateQdBar then FV.UpdateQdBar() end
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
            local st = (MouseOverSafe(f) and not f.__selActive) and "hover" or "norm"
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
        FV.filterBtn:SetText((ns.SYM.tri .. " ") .. L["筛选"])
    else
        FV.filterBtn:SetText((ns.SYM.tri .. " ") .. L["筛选"] .. " " .. n)
    end
end

function FV:Tab()
    local d = ns.FactionDB()
    return (d.ftab == "quest") and "quest" or "reward"
end

function FV:SyncTabShown()
    local k = FV:Tab()
    if FV.dScroll then FV.dScroll:SetShown(k == "reward") end
    if FV.qPage then FV.qPage:SetShown(k == "quest") end
end

function FV:PaintTab()
    if not FV.tabs then return end
    local k = FV:Tab()
    for _, bt in ipairs(FV.tabs) do
        SetButtonSelected(bt, bt.__key == k, "tab")
    end
end

function FV:SelectFaction(fid)
    Cfg().sel = fid
    local tab = FV:Tab()
    if tab == "quest" then FV:WarmQuests(fid) end
    FV:SyncFav()
    FV:PaintTab()
    FV:PaintList()
    if tab == "quest" then
        FV:PaintQuestList()
        FV:PaintQuestDetail()
    else
        FV:PaintDetail()
    end
end

function FV:SetTab(key)
    local d = ns.FactionDB()
    d.ftab = (key == "quest") and "quest" or "reward"
    FV:SyncTabShown()
    if FV:Tab() == "quest" then FV:WarmQuests(Cfg().sel) end
    FV.RequestRender()
end

function FV:SetStage(key)
    if key ~= "buy" and key ~= "fr" and key ~= "ho" then key = "buy" end
    local d = ns.FactionDB()
    d.fqstage = key
    local fid = Cfg().sel
    local list = QuestListOf(fid)
    d.fqsel = d.fqsel or {}
    if type(list) == "table" then
        for _, q in ipairs(list) do
            if q.tier == key then
                d.fqsel[fid] = q.id[1]
                break
            end
        end
    end
    if FV.qScroll and FV.qScroll.SetVerticalScroll then FV.qScroll:SetVerticalScroll(0) end
    FV:PaintQuestList()
    FV:PaintQuestDetail()
end

function FV:SelectQuest(qid)
    local fid = Cfg().sel
    local list = QuestListOf(fid)
    local q = FindQuest(list, qid)
    if not q then return end
    local d = ns.FactionDB()
    d.fqsel = d.fqsel or {}
    d.fqsel[fid] = qid
    d.fqstage = q.tier
    FV:PaintQuestList()
    FV:PaintQuestDetail()
end

function FV:WarmQuests(fid)
    if not fid then return end
    local list = QuestListOf(fid)
    if type(list) ~= "table" then return end
    FV.__qWarm = FV.__qWarm or {}
    if FV.__qWarm[fid] then return end
    FV.__qWarm[fid] = true
    local miss = false
    if DG and DG.QuestName then
        for _, q in ipairs(list) do
            for _, id in ipairs(q.id or {}) do
                local ok, nm, has = pcall(DG.QuestName, id)
                if not (ok and has) then miss = true end
            end
        end
    end
    if miss and C_Timer and C_Timer.NewTimer then
        C_Timer.NewTimer(1.2, function()
            if FV.built then FV.RequestRender() end
        end)
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
    local list = {}
    local rest = {}
    for _, x in ipairs(FD) do
        if PassFilter(x, pside, c) then
            if c.fav[x.id] then list[#list + 1] = x else rest[#rest + 1] = x end
        end
    end
    for i = 1, #rest do list[#list + 1] = rest[i] end
    local pitch = FV.ROW_PITCH
    local n = #list
    local totalH = n * pitch
    FV.lChild:SetHeight(max(10, totalH + 10))

    local viewH = tonumber(FV.lScroll.GetHeight and FV.lScroll:GetHeight()) or 0
    if viewH <= 0 then viewH = 420 end
    local __mx = totalH + 10 - viewH
    local __v = tonumber(FV.lScroll.GetVerticalScroll and FV.lScroll:GetVerticalScroll()) or 0
    if __mx < 0 then __mx = 0 end
    if __v > __mx then
        __v = __mx
        FV.lScroll:SetVerticalScroll(__mx)
    end
    if __v < 0 then __v = 0 end

    local lo = math.floor(__v / pitch) + 1 - FV.WIN_BUF
    local hi = math.ceil((__v + viewH) / pitch) + 1 + FV.WIN_BUF
    if lo < 1 then lo = 1 end
    if n > 0 and lo > n then lo = n end
    if hi > n then hi = n end
    if hi < lo then hi = lo end

    for i = 1, #FV.rows do
        local r = FV.rows[i]
        r.__active = false
        r:Hide()
    end

    if n > 0 then
        local slot = 0
        for idx = lo, hi do
            slot = slot + 1
            local r = FV.rows[slot]
            if not r then
                r = MakeRow(FV.lChild)
                FV.rows[slot] = r
            end
            local x = list[idx]
            local y = (idx - 1) * pitch
            r.__active = true
            r.__vtop = y
            r.__vh = FV.ROW_H
            r.__fid = x.id
            r.name:SetText((c.fav[x.id] and Q_INK_GOLD .. "★ " .. Q_END or "") .. FacName(x))
            local __lv = LiveValue(x.id) or x.start
            local __ti = StandingIdx(__lv)
            local __sc = STANDINGS[__ti].color
            r.name:SetTextColor(__sc[1], __sc[2], __sc[3])
            r.sub:SetText(STANDINGS[__ti].label .. " " .. NumStr(__lv - STANDINGS[__ti].bottom)
                .. "/" .. NumStr(STANDINGS[__ti].span))
            r.badge:SetText(SideText(x.side))
            local sel = (c.sel == x.id)
            r.__selActive = sel and true or nil
            if HUI and r.__huiCard and ns.hui.HuiCardState then
                ns.hui.HuiCardState(r, "norm")
                r.__hst = "norm"
            end
            if not (HUI and ns.hui.PaintRowSelect and ns.hui.PaintRowSelect(r, sel, "Interface\\AddOns\\DungeonsForever\\Media\\Common\\DF_RowSelGradFac")) then
                if sel then
                    SetButtonSelected(r, false)
                end
            end
            r.__tip = FacName(x) .. "\n" .. SIDE_INFO[x.side].text .. " · " .. L["起始声望"] .. " " .. NumStr(x.start)
                .. ((c.fav[x.id] and "\n" .. Q_INK_GOLD .. L["已收藏"] .. Q_END) or "")
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", FV.lChild, "TOPLEFT", 0, -y)
            r:Show()
            FV.lCull[#FV.lCull + 1] = r
            if slot % 4 == 0 then PY() end
        end
    end

    local selX = FacBySel(c.sel)
    if n > 0 and not (selX and PassFilter(selX, pside, c)) then
        c.sel = list[1].id
    end
    FV:CullLeft()
    if FV.UpdateLeftBar then FV.UpdateLeftBar() end
end

local function CostOf(x, key, id)
    local c = (type(x) == "table") and x.cost
    if type(c) ~= "table" then return nil end
    local item, n = c.item, c[key]
    if type(c.prices) == "table" then
        local p = type(id) == "number" and c.prices[id]
        if type(p) == "number" and p > 0 then n = p end
    end
    if type(item) == "number" and type(n) == "number" and n > 0 then return item, n end
    return nil
end

function FV:PaintRewardCard(f, id, fam, key)
    f.__id = id
    f.__fam = fam
    f.__key = key
    local nm, ok
    if DG and DG.ItemName then nm, ok = DG.ItemName(id) end
    if ok then
        local budget = f.__nameW or 200
        f.name:SetText(DG.FitText and DG.FitText(nm, 14, budget) or nm)
        if DG.QColor and DG.QualOf then
            local qr, qg, qb = DG.QColor(DG.QualOf(id))
            if qr then f.name:SetTextColor(qr, qg, qb) end
        end
    else
        f.name:SetText(format(L["物品 #%d"], id or 0))
        f.name:SetTextColor(Unpack(C_GREY))
        if DG and DG.RequestItem then DG.RequestItem(id) end
    end
    local cItem, cNum = CostOf(fam, key, id)
    if cItem then
        if DG and DG.RequestItem then DG.RequestItem(cItem) end
        f.priceTex:ClearAllPoints()
        f.priceTex:SetPoint("TOPLEFT", f, "TOPLEFT", 46, -24)
        f.priceTex:SetTexture((DG and DG.ItemIcon and DG.ItemIcon(cItem)) or nil)
        f.priceTex:Show()
        f.meta:ClearAllPoints()
        f.meta:SetPoint("TOPLEFT", f.priceTex, "TOPRIGHT", 3, 0)
        f.meta:SetText(format("%d", cNum))
        f.meta:SetTextColor(Unpack(GOLD))
    else
        f.priceTex:Hide()
        f.meta:ClearAllPoints()
        f.meta:SetPoint("TOPLEFT", f, "TOPLEFT", 46, -26)
        local meta = ""
        if DG and DG.ItemMeta then meta = DG.ItemMeta(id) or "" end
        f.meta:SetText(type(meta) == "string" and meta or "")
        f.meta:SetTextColor(Unpack(C_GREY))
    end
    if DG and DG.ItemIcon then
        f.iconTex:SetTexture(DG.ItemIcon(id))
    end
    if ns.hui and ns.hui.SetIconRing then
        local qq = (DG and DG.QualOf) and DG.QualOf(id) or nil
        ns.hui.SetIconRing(f.iconTex, qq and { ns.hui.QColor(qq) } or nil)
    end
end

function FV.OnItemData(itemID)
    if not FV.built then return end
    for _, f in ipairs(FV.rCards or {}) do
        if f:IsShown() then
            if f.__id == itemID then
                FV:PaintRewardCard(f, itemID, f.__fam, f.__key)
            elseif CostOf(f.__fam, f.__key, f.__id) == itemID then
                FV:PaintRewardCard(f, f.__id, f.__fam, f.__key)
            end
        end
    end
    for _, f in ipairs(FV.qdItem or {}) do
        if f:IsShown() and f.__id == itemID then
            FV:PaintQItem(f, itemID)
        end
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
    local y = 0

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
    FV.dIcon.__vh = 16
    FV.dCull[#FV.dCull + 1] = FV.dIcon

    FV.dTitle:ClearAllPoints()
    FV.dTitle:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", (info.icon and 38 or 14), -(y - 1))
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
    FV.barTrack:SetPoint("TOPLEFT", FV.dChild, "TOPLEFT", barX, -(y - 0.2))
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
                    cd.name:SetPoint("TOPLEFT", cd, "TOPLEFT", 46, -6)
                    cd.name:SetWidth(cardW - 53)
                    cd.name:SetWordWrap(false)
                    cd.meta = MakeFS(cd, 12, C_GREY, "LEFT")
                    cd.meta:SetPoint("TOPLEFT", cd, "TOPLEFT", 46, -26)
                    cd.meta:SetWordWrap(false)
                    cd.priceTex = cd:CreateTexture(nil, "ARTWORK")
                    cd.priceTex:SetSize(13, 13)
                    cd.priceTex:Hide()
                    cd.__nameW = cardW - 53
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
                FV:PaintRewardCard(cd, id, x, key)
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

function FV:PaintQuestList()
    if not FV.qRows then return end
    local fid = Cfg().sel
    local list = QuestListOf(fid)
    local stage = StageOf(list)
    local cull = {}
    FV.qCull = cull

    for _, bt in ipairs(FV.stageBtns or {}) do
        local n = 0
        if type(list) == "table" then
            for _, q in ipairs(list) do
                if q.tier == bt.__key then n = n + 1 end
            end
        end
        bt:SetText(format("%s |cff5a6274%d|r", QT_BTN[bt.__key], n))
        local on = (bt.__key == stage)
        SetButtonSelected(bt, on, "tab")
        local fs = bt.GetFontString and bt:GetFontString()
        if fs then
            if on then
                fs:SetTextColor(1, 1, 1)
            else
                local col = QT_COLOR[bt.__key]
                fs:SetTextColor(col[1], col[2], col[3])
            end
        end
    end

    for i = 1, #FV.qRows do
        local r = FV.qRows[i]
        r.__active = false
        r:Hide()
    end
    FV.qHead.__active = false
    FV.qHead:Hide()
    FV.qEmpty:Hide()

    if type(list) ~= "table" then
        FV.qEmpty:ClearAllPoints()
        FV.qEmpty:SetPoint("TOPLEFT", FV.qChild, "TOPLEFT", 0, 0)
        FV.qEmpty:Show()
        FV.qChild:SetHeight(24)
        FV:CullQuestList()
        return
    end

    local rows = {}
    for _, q in ipairs(list) do
        if q.tier == stage then rows[#rows + 1] = q end
    end
    local cur = SelQuestOf(fid, list, stage)
    local y = 0

    local head = FV.qHead
    local hcol = QT_COLOR[stage]
    head:ClearAllPoints()
    head:SetPoint("TOPLEFT", FV.qChild, "TOPLEFT", 0, 0)
    head.lab:SetText(QT_LABEL[stage])
    head.lab:SetTextColor(hcol[1], hcol[2], hcol[3])
    head.line:ClearAllPoints()
    head.line:SetPoint("LEFT", head.lab, "RIGHT", 6, 0)
    head.line:SetPoint("RIGHT", head, "RIGHT", 0, 0)
    head.line:SetColorTexture(hcol[1], hcol[2], hcol[3], 0.5)
    head:Show()
    head.__active = true
    head.__vtop = 0
    head.__vh = FV.QHEAD_H
    cull[#cull + 1] = head
    y = FV.QHEAD_H + 4

    local n = #rows
    if n == 0 then
        FV.qEmpty:ClearAllPoints()
        FV.qEmpty:SetPoint("TOPLEFT", FV.qChild, "TOPLEFT", 0, -y)
        FV.qEmpty:Show()
    end

    for i, q in ipairs(rows) do
        local r = FV.qRows[i]
        if not r then
            r = MakeQRow(FV.qChild)
            FV.qRows[i] = r
        end
        local qid = q.id[1]
        local sel = false
        if cur then
            for _, id in ipairs(cur.id or {}) do
                if id == qid then sel = true end
            end
        end
        local own
        for _, rr in ipairs(q.rep or {}) do
            if rr[1] == fid then own = rr[2] break end
        end
        r.__qid = qid
        r.__selActive = sel or nil
        r.name:SetText(QName(q))
        if sel then
            r.name:SetTextColor(1, 1, 1)
        elseif own and own > 0 and not q.rp then
            r.name:SetTextColor(Unpack(C_TEXT))
        else
            r.name:SetTextColor(Unpack(C_GREY))
        end
        local bits = {}
        if own then bits[#bits + 1] = format("%s%d", own > 0 and "+" or "", own) end
        if q.lv then bits[#bits + 1] = format("L%d", q.lv) end
        if q.rp then bits[#bits + 1] = L["可重复"] end
        r.sub:SetText(table.concat(bits, " · "))
        local dc, gtex, gc = QBadgeSpec(QStateOf(qid))
        r.stDisc:SetVertexColor(dc[1], dc[2], dc[3], 1)
        r.stGlyph:SetTexture(gtex)
        r.stGlyph:SetVertexColor(gc[1], gc[2], gc[3], 1)
        if HUI and r.__huiCard and ns.hui.HuiCardState then
            ns.hui.HuiCardState(r, "norm")
            r.__hst = "norm"
        end
        if HUI and ns.hui.PaintRowSelect then
            ns.hui.PaintRowSelect(r, sel, Q_ROWSEL)
        end
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", FV.qChild, "TOPLEFT", 0, -y)
        r:Show()
        r.__active = true
        r.__vtop = y
        r.__vh = FV.QROW_H
        cull[#cull + 1] = r
        y = y + FV.QROW_PITCH
        if i % 6 == 0 then PY() end
    end

    FV.qChild:SetHeight(max(10, y + 4))
    local viewH = tonumber(FV.qScroll.GetHeight and FV.qScroll:GetHeight()) or 0
    local maxScroll = FV.qChild:GetHeight() - viewH
    if maxScroll < 0 then maxScroll = 0 end
    local v = tonumber(FV.qScroll.GetVerticalScroll and FV.qScroll:GetVerticalScroll()) or 0
    if v > maxScroll and FV.qScroll.SetVerticalScroll then FV.qScroll:SetVerticalScroll(maxScroll) end
    FV:CullQuestList()
end

function FV:PaintQuestDetail()
    if not FV.qdName then return end
    local child = FV.qdChild
    local fid = Cfg().sel
    local list = QuestListOf(fid)
    local stage = StageOf(list)
    local q = SelQuestOf(fid, list, stage)
    local W = FV.QTXT
    local cull = {}
    FV.qdCull = cull
    local y = 0
    local nChip, nNpc, nPre, nLab, nGoal, nItem, nGain = 0, 0, 0, 0, 0, 0, 0

    for _, pool in ipairs({ FV.qdChip, FV.qdNpc, FV.qdPre, FV.qdLab, FV.qdGoal, FV.qdItem, FV.qdGain }) do
        for _, f in ipairs(pool) do
            f.__active = false
            f:Hide()
        end
    end
    for _, f in ipairs({ FV.qdName, FV.qdSub, FV.qdObj, FV.qdDesc, FV.qdSep, FV.qdState }) do
        f.__active = false
        f:Hide()
    end

    local function put(f, h)
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -y)
        f:Show()
        f.__active = true
        f.__vtop = y
        f.__vh = h
        cull[#cull + 1] = f
        y = y + h
    end

    local function gap(h)
        y = y + h
    end

    local function sect(text)
        gap(8)
        nLab = nLab + 1
        local f = FV.qdLab[nLab]
        if not f then return end
        f:SetText(text)
        f:SetTextColor(Unpack(C_TEXT))
        f:SetWidth(W)
        put(f, 20)
    end

    if not q then
        FV.qdName:SetText(L["点左侧任务查看详情"])
        FV.qdName:SetTextColor(Unpack(C_GREY))
        FV.qdName:SetWidth(W)
        put(FV.qdName, 24)
        child:SetHeight(60)
        FV:CullQuestDetail()
        return
    end

    local qid = q.id[1]
    FV.qdName:SetText(QName(q))
    FV.qdName:SetTextColor(Unpack(C_GOLD))
    FV.qdName:SetWidth(W)
    put(FV.qdName, 22)

    local sub = {}
    if q.lv then sub[#sub + 1] = format(L["等级 %d"], q.lv) end
    if q.req then sub[#sub + 1] = format(L["需要 %d"], q.req) end
    if q.side and QSIDE_TXT[q.side] then sub[#sub + 1] = QSIDE_TXT[q.side] end
    FV.qdSub:SetText(table.concat(sub, "   ·   "))
    FV.qdSub:SetWidth(W)
    put(FV.qdSub, 20)

    local chipY = y + 2
    local chipX = 0
    local function addChip(text, color)
        nChip = nChip + 1
        local f = FV.qdChip[nChip]
        if not f then return end
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", child, "TOPLEFT", chipX, -chipY)
        PaintChip(f, text, color)
        f:Show()
        f.__active = true
        f.__vtop = chipY
        f.__vh = 18
        cull[#cull + 1] = f
        chipX = chipX + f:GetWidth() + 6
    end
    for _, rr in ipairs(q.rep or {}) do
        local delta = rr[2] or 0
        local txt = format("%s%s %s", delta > 0 and "+" or "", NumStr(delta), FacNameByID(rr[1]))
        addChip(txt, delta >= 0 and Q_GREEN or Q_RED)
    end
    if q.rp then addChip(L["可重复"], Q_GREEN) end
    if nChip > 0 then y = chipY + 20 end

    local function addNpcRow(label, nid)
        nNpc = nNpc + 1
        local f = FV.qdNpc[nNpc]
        if not f then return end
        local loc = NpcLoc(nid)
        local info = NpcInfo(nid)
        local txt = Q_INK_GREY .. label .. Q_END .. Q_INK_GOLD .. NpcName(nid) .. Q_END
        if loc then
            txt = txt .. format(" %s%.1f, %.1f%s", Q_INK_DIM, loc[2], loc[3], Q_END)
        elseif info and type(info.place) == "string" and info.place ~= "" then
            txt = txt .. " " .. Q_INK_DIM .. info.place .. Q_END
        end
        f.__npc = nid
        f.__loc = loc
        f.fs:SetText(txt)
        f.fs:SetWidth(loc and (W - 74) or W)
        f.btn:SetShown(loc and true or false)
        put(f, 24)
    end

    local sN = 0
    for _, nid in ipairs(q.start or {}) do
        if sN < 2 then
            addNpcRow(sN == 0 and L["起始："] or "", nid)
            sN = sN + 1
        end
    end
    local eN = 0
    for _, nid in ipairs(q.finish or {}) do
        if eN < 2 then
            addNpcRow(eN == 0 and L["结束："] or "", nid)
            eN = eN + 1
        end
    end

    local pres = q.pre
    if type(pres) == "table" and #pres > 0 then
        sect(L["前置任务"])
        for _, pid in ipairs(pres) do
            if nPre < 3 then
                nPre = nPre + 1
                local f = FV.qdPre[nPre]
                f.__qid = pid
                f.txt:SetText(format(L["《%s》"], QNameByID(pid)))
                f.txt:SetWidth(W - 20)
                put(f, 30)
                gap(6)
            end
        end
    end

    if type(q.obj) == "string" and q.obj ~= "" then
        sect(L["目标"])
        FV.qdObj:SetWidth(W)
        FV.qdObj:SetText(q.obj)
        put(FV.qdObj, TxtH(FV.qdObj, 20))
    end

    local goals = q.goals
    if type(goals) == "table" and #goals > 0 then
        sect(L["任务要求"])
        for _, g in ipairs(goals) do
            if nGoal < 4 then
                nGoal = nGoal + 1
                local f = FV.qdGoal[nGoal]
                local nm = g[1] or ""
                local gn = tonumber(g[2]) or 0
                if gn > 0 then
                    f.txt:SetText(format("%s%s%s ×%d", Q_INK_GOLD, nm, Q_END, gn))
                else
                    f.txt:SetText(Q_INK_GOLD .. nm .. Q_END)
                end
                put(f, 20)
            end
        end
    end

    if type(q.desc) == "string" and q.desc ~= "" then
        sect(L["任务说明"])
        FV.qdDesc:SetWidth(W)
        FV.qdDesc:SetText(q.desc)
        put(FV.qdDesc, TxtH(FV.qdDesc, 20))
    end

    local rw = q.reward
    if type(rw) == "table" and #rw > 0 then
        sect(format(L["任务奖励（%d 选 1）"], #rw))
        for _, id in ipairs(rw) do
            if nItem < 3 then
                nItem = nItem + 1
                local c = FV.qdItem[nItem]
                FV:PaintQItem(c, id)
                if c.__huiCard and ns.hui.HuiCardState then
                    ns.hui.HuiCardState(c, "norm")
                    c.__hst = "norm"
                end
                put(c, 44)
                gap(6)
            end
        end
    end

    sect(L["收获"])
    for _, rr in ipairs(q.rep or {}) do
        if nGain < 4 then
            nGain = nGain + 1
            local f = FV.qdGain[nGain]
            local delta = rr[2] or 0
            local col = delta >= 0 and Q_GREEN or Q_RED
            f:SetText(format("%s%s %s %s%s%s", Q_INK_GREY, FacNameByID(rr[1]), L["声望"],
                Hex(col), format("%s%s", delta > 0 and "+" or "", NumStr(delta)), Q_END))
            put(f, 20)
        end
    end
    if nGain < 4 then
        nGain = nGain + 1
        local f = FV.qdGain[nGain]
        local xp = QuestXP(qid)
        if xp then
            f:SetText(format("%s%s %s%s%s", Q_INK_GREY, L["经验值"], Q_INK_GOLD, NumStr(xp), Q_END))
        else
            f:SetText(format("%s%s %s—%s %s%s%s", Q_INK_GREY, L["经验值"], Q_INK_DIM, Q_END,
                Q_INK_GREY, L["接取后按客户端显示"], Q_END))
        end
        put(f, 20)
    end

    gap(10)
    FV.qdSep:ClearAllPoints()
    FV.qdSep:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -y)
    FV.qdSep:Show()
    FV.qdSep.__active = true
    FV.qdSep.__vtop = y
    FV.qdSep.__vh = 1
    cull[#cull + 1] = FV.qdSep
    y = y + 9

    local st = QStateOf(qid)
    FV.qdState:SetText(Q_STATE_TXT[st] or Q_STATE_TXT.todo)
    FV.qdState:SetTextColor(Unpack(QStateCol(st)))
    FV.qdState:SetWidth(W)
    put(FV.qdState, 20)

    child:SetHeight(max(10, y + 12))
    if FV.__lastQSel ~= qid then
        FV.__lastQSel = qid
        if FV.qdScroll and FV.qdScroll.SetVerticalScroll then FV.qdScroll:SetVerticalScroll(0) end
    end
    FV:CullQuestDetail()
end

function FV.RequestRender()
    if not FV.built then return end
    local function paint()
        FV:PaintTab()
        FV:PaintList()
        if FV:Tab() == "quest" then
            FV:PaintQuestList()
            FV:PaintQuestDetail()
        else
            FV:PaintDetail()
        end
    end
    if not (ns.FactionPaint and ns.FactionIdle) then
        paint()
        return
    end
    if ns.FactionPaint.Active("Factions") then
        FV.__pend = true
        return
    end
    ns.FactionPaint.Run("Factions", paint, function()
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
    FV:SyncTabShown()
    if FV:Tab() == "quest" then FV:WarmQuests(c.sel) end
    FV.RequestRender()
end

function FV.Refresh()
    if not FV.built then return end
    FV.RequestRender()
end
