local ns = _G.DF_NS or {}
local Host = ns.ProfHost
if not Host then return end

local L = ns.L
local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local SetTip = Host.SetTip
local Unpack = Host.Unpack
local C_GOLD, C_GREEN, C_GREY = Host.C_GOLD, Host.C_GREEN, Host.C_GREY
local C_WHITE, C_TEXT = Host.C_WHITE, Host.C_TEXT
local CONTENT_W = Host.CONTENT_W or 936
local CONTENT_H = Host.CONTENT_H or 640
local PAGE_INSET = Host.PAGE_INSET or 12
local hui = ns.hui
local GUT = (DG and DG.GUTTER) or 8

local X = PAGE_INSET
local W = CONTENT_W - 2 * X
local SEARCH_H = 84
local LIST_W = 372
local DETAIL_W = W - LIST_W - GUT
local TOP = GUT
local BODY_TOP = TOP + SEARCH_H + GUT
local BODY_H = CONTENT_H - BODY_TOP - PAGE_INSET
local PAD = 12
local ROW_H = 44
local ROW_GAP = 2
local EB_H = 36
local SEG_H = 24
local SEG_W = 66
local SEG_GAP = 8
local MAX_ROWS = 200

local C_SUB = C_GREY or { 0.62, 0.65, 0.70 }
local C_MAIN = C_TEXT or { 0.88, 0.90, 0.94 }
local C_TITLE = C_WHITE or { 1, 1, 1 }

local INK_DONE = { 0.27, 0.72, 0.44 }
local INK_ACT = { 0.36, 0.62, 0.92 }
local INK_NEUTRAL = { 0.42, 0.45, 0.52 }
local INK_KIND = { 0.45, 0.62, 0.86 }

local KIND_ORDER = { "quest", "npc", "object", "item" }
local TAB_KINDS = { "quest", "npc", "item" }

local QS = {}
ns.QuestSearchModule = QS

local function QDB()
    local ql = _G.QuestieLoader
    local m = type(ql) == "table" and ql._modules
    local db = type(m) == "table" and m.QuestieDB
    if type(db) == "table" then return db end
    return nil
end

local function QSEARCH()
    local ql = _G.QuestieLoader
    local m = type(ql) == "table" and ql._modules
    local s = type(m) == "table" and m.QuestieSearch
    if type(s) == "table" then return s end
    return nil
end

local function ZDB()
    local ql = _G.QuestieLoader
    local m = type(ql) == "table" and ql._modules
    local db = type(m) == "table" and m.ZoneDB
    if type(db) == "table" then return db end
    return nil
end

local function KindText(kind)
    if kind == "npc" then return L["NPC"] end
    if kind == "object" then return L["物体"] end
    if kind == "item" then return L["物品"] end
    return L["任务"]
end

local NCACHE = {}

local function QueryFn(kind)
    local DB = QDB()
    if not DB then return nil end
    if kind == "npc" then return DB.QueryNPCSingle end
    if kind == "object" then return DB.QueryObjectSingle end
    if kind == "item" then return DB.QueryItemSingle end
    return DB.QueryQuestSingle
end

local function NameOf(id, kind)
    local key = kind .. ":" .. id
    local hit = NCACHE[key]
    if hit ~= nil then
        if hit == false then return nil end
        return hit
    end
    local name
    local fn = QueryFn(kind)
    if type(fn) == "function" then
        local ok, v = pcall(fn, id, "name")
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    NCACHE[key] = name or false
    return name
end

local function FieldOf(id, kind, field)
    local fn = QueryFn(kind)
    if type(fn) ~= "function" then return nil end
    local ok, v = pcall(fn, id, field)
    if ok then return v end
    return nil
end

local function QuestRec(id)
    local DB = QDB()
    if not DB or type(DB.GetQuest) ~= "function" then return nil end
    local ok, v = pcall(DB.GetQuest, id)
    if ok and type(v) == "table" then return v end
    return nil
end

local function QuestLevelOf(id)
    local lv = tonumber(FieldOf(id, "quest", "level")) or 0
    if lv > 0 then return lv end
    if DG and type(DG.QuestLevel) == "function" then
        local ok, v = pcall(DG.QuestLevel, id)
        if ok then lv = tonumber(v) or 0 end
    end
    return lv
end

local ZONE_NAME = {}

local function ZoneName(zone)
    local z = tonumber(zone) or 0
    if z <= 0 then return nil end
    local hit = ZONE_NAME[z]
    if hit ~= nil then
        if hit == false then return nil end
        return hit
    end
    local name
    if C_Map and C_Map.GetAreaInfo then
        local ok, v = pcall(C_Map.GetAreaInfo, z)
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    ZONE_NAME[z] = name or false
    return name
end

local function SpawnsOf(id, kind)
    local out = {}
    if kind == "quest" or kind == "item" then return out end
    local sp = FieldOf(id, kind, "spawns")
    if type(sp) ~= "table" then return out end
    for z, list in pairs(sp) do
        local zid = tonumber(z)
        if zid and type(list) == "table" then
            for i = 1, #list do
                local p = list[i]
                if type(p) == "table" and type(p[1]) == "number" and type(p[2]) == "number"
                    and p[1] >= 0 and p[2] >= 0 then
                    out[#out + 1] = { zone = zid, x = p[1], y = p[2] }
                end
            end
        end
    end
    table.sort(out, function(a, b)
        if a.zone ~= b.zone then return a.zone < b.zone end
        return a.x < b.x
    end)
    return out
end

local function MapJump(id, kind, zone, x, y)
    if not (DG and type(DG.MarkNPC) == "function") then return end
    if type(x) ~= "number" or type(y) ~= "number" or type(zone) ~= "number" then return end
    local mapID = zone
    local Z = ZDB()
    if Z and type(Z.GetUiMapIdByAreaId) == "function" then
        local ok, v = pcall(Z.GetUiMapIdByAreaId, Z, zone)
        if ok and type(v) == "number" then mapID = v end
    end
    local npcId = (kind == "npc" or kind == "object") and id or 0
    pcall(DG.MarkNPC, npcId, { mapID, x, y, "" })
end

local QSTATE = {}

local function RefreshStatus()
    QSTATE = {}
end

local function StatusOf(id)
    local hit = QSTATE[id]
    if hit ~= nil then return hit end
    local done
    local q = _G.Questie
    local c = q and q.db and q.db.char and q.db.char.complete
    if type(c) == "table" and c[id] then done = true end
    local api = _G.C_QuestLog
    if type(api) == "table" and type(api.IsQuestFlaggedCompleted) == "function" then
        local ok, r = pcall(api.IsQuestFlaggedCompleted, id)
        if ok and r then done = true end
    end
    if done then
        QSTATE[id] = "done"
        return "done"
    end
    if type(api) == "table" and type(api.IsOnQuest) == "function" then
        local ok, r = pcall(api.IsOnQuest, id)
        if ok and r then
            QSTATE[id] = "act"
            return "act"
        end
    end
    QSTATE[id] = "todo"
    return "todo"
end

local RES = { quest = {}, npc = {}, object = {}, item = {} }
local COUNT = { quest = 0, npc = 0, object = 0, item = 0 }

local function ResetRes()
    RES = { quest = {}, npc = {}, object = {}, item = {} }
    COUNT = { quest = 0, npc = 0, object = 0, item = 0 }
end

local function SortIds(ids, kind)
    table.sort(ids, function(a, b)
        if kind == "quest" then
            local la = QuestLevelOf(a)
            local lb = QuestLevelOf(b)
            if la ~= lb then return la < lb end
        end
        local na, nb = NameOf(a, kind) or "", NameOf(b, kind) or ""
        if na ~= nb then return na < nb end
        return a < b
    end)
end

function QS.DoSearch(text)
    local S = QSEARCH()
    if not S then return false end
    ResetRes()
    local ok, res = pcall(function()
        if tonumber(text) ~= nil then return S:ByID(text) end
        return S:ByName(text)
    end)
    if not ok or type(res) ~= "table" then return false end
    for _, kind in ipairs(KIND_ORDER) do
        local ids = {}
        local src = res[kind]
        if type(src) == "table" then
            for id in pairs(src) do
                if type(id) == "number" then ids[#ids + 1] = id end
            end
        end
        if #ids > 0 then SortIds(ids, kind) end
        RES[kind] = ids
        COUNT[kind] = #ids
    end
    return true
end

function QS.SearchState()
    if QSEARCH() then return "ready" end
    return "idle"
end

local function Card(parent, x, y, w, h)
    local f = CreateFrame("Frame", nil, parent, "BackdropTemplate")
    f:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    f:SetSize(w, h)
    if hui and hui.SkinPopup and hui.layer then
        pcall(hui.SkinPopup, f, 6, nil, hui.layer.L1)
    else
        f:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        f:SetBackdropColor(0x10 / 255, 0x13 / 255, 0x1A / 255, 1)
        f:SetBackdropBorderColor(1, 1, 1, 0.10)
    end
    return f
end

local function TextWidth(fs, fallback)
    local w
    if fs and fs.GetStringWidth then w = fs:GetStringWidth() end
    if type(w) == "number" and w > 4 then return w end
    return fallback
end

local function TabRow(parent, x, y, defs, onPick)
    local host = CreateFrame("Frame", nil, parent)
    host:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    host:SetSize(SEG_W * #defs + SEG_GAP * (#defs - 1), SEG_H)
    local btns = {}
    for _, d in ipairs(defs) do
        local bt = NewButton(host, d.text, SEG_W, SEG_H, 14)
        bt:SetPushedTextOffset(0, 0)
        bt:SetScript("OnClick", function()
            ns.PlaySound(1)
            onPick(d.key)
        end)
        btns[#btns + 1] = bt
        d.button = bt
    end
    local api = { host = host, defs = defs, btns = btns }
    api.layout = function()
        local prev, total = nil, 0
        for i, d in ipairs(defs) do
            local bt = d.button
            local tw = TextWidth(bt:GetFontString(), #d.text * 14)
            local w = math.max(SEG_W, math.ceil(tw + 18))
            bt:SetSize(w, SEG_H)
            bt:ClearAllPoints()
            if prev then
                bt:SetPoint("LEFT", prev, "RIGHT", SEG_GAP, 0)
            else
                bt:SetPoint("TOPLEFT", host, "TOPLEFT", 0, 0)
            end
            total = total + w + (i > 1 and SEG_GAP or 0)
            prev = bt
        end
        host:SetWidth(total > 0 and total or SEG_W)
    end
    api.paint = function(key)
        for _, d in ipairs(defs) do
            local n = COUNT[d.key] or 0
            local text = d.text
            if n > 0 then text = text .. " (" .. n .. ")" end
            local bt = d.button
            local cur = bt.GetText and bt:GetText()
            if cur ~= text then bt:SetText(text) end
            if ns.hui and ns.hui.SetButtonSelected then
                ns.hui.SetButtonSelected(bt, d.key == key, "main")
            end
        end
        api.layout()
    end
    api.layout()
    return api
end

local ROWS = {}
local DET = {}

local function RowSub(rec)
    if rec.kind == "quest" then
        local lv = QuestLevelOf(rec.id)
        local lvTxt = L["等级 ?"]
        if lv > 0 then lvTxt = string.format(L["等级 %d"], lv) end
        local zone = ZoneName(FieldOf(rec.id, "quest", "zoneOrSort"))
        local s = lvTxt
        if zone then s = s .. " · " .. zone end
        return s
    end
    if rec.kind == "item" then
        local q = tonumber(FieldOf(rec.id, "item", "quality")) or 0
        local il = tonumber(FieldOf(rec.id, "item", "itemLevel")) or 0
        local s = L["物品"]
        if il > 0 then s = string.format(L["物品等级 %d"], il) end
        if q > 0 then s = s .. " · " .. string.format(L["品质 %d"], q) end
        return s
    end
    local pts = SpawnsOf(rec.id, rec.kind)
    if #pts > 0 then
        local zn = ZoneName(pts[1].zone) or L["未知区域"]
        if #pts > 1 then return zn .. string.format(L[" · %d 处刷新"], #pts) end
        return zn
    end
    return L["没有收录刷新位置"]
end

local function RowChip(rec)
    if rec.kind ~= "quest" then return KindText(rec.kind), INK_KIND end
    local st = StatusOf(rec.id)
    if st == "done" then return L["已完成"], INK_DONE end
    if st == "act" then return L["进行中"], INK_ACT end
    return nil
end

local QUEST_TAG = {
    [1] = { L["组队"], { 0.16, 0.52, 0.26 } },
    [21] = { L["职业"], { 0.64, 0.61, 0.55 } },
    [41] = { "PvP", { 0.78, 0.14, 0.12 } },
    [62] = { L["团队"], { 0.42, 0.26, 0.60 } },
    [81] = { L["地下城"], { 0.20, 0.45, 0.55 } },
    [82] = { L["世界事件"], { 0.20, 0.50, 0.62 } },
    [83] = { L["传奇"], { 0.85, 0.42, 0.10 } },
    [84] = { L["护送"], { 0.45, 0.35, 0.62 } },
    [85] = { L["英雄"], { 0.78, 0.60, 0.10 } },
    [88] = { L["团队"], { 0.42, 0.26, 0.60 } },
    [89] = { L["团队"], { 0.42, 0.26, 0.60 } },
    [98] = { L["场景"], { 0.30, 0.42, 0.55 } },
}

local TAG_CACHE = {}

local function QuestTagOf(qid)
    local hit = TAG_CACHE[qid]
    if hit ~= nil then
        if hit == false then return nil end
        return hit[1], hit[2], hit[3]
    end
    local tag
    local DB = QDB()
    if DB and type(DB.GetQuestTagInfo) == "function" then
        local ok, v = pcall(DB.GetQuestTagInfo, qid)
        if ok then
            if type(v) == "table" then
                tag = tonumber(v.tagID) or tonumber(v[1])
            else
                tag = tonumber(v)
            end
        end
    end
    if not tag then
        local cq = _G.C_QuestLog
        if type(cq) == "table" and type(cq.GetQuestTagInfo) == "function" then
            local ok, v = pcall(cq.GetQuestTagInfo, qid)
            if ok and type(v) == "table" then tag = tonumber(v.tagID) end
        end
    end
    local style = tag and QUEST_TAG[tag] or nil
    if not style then
        TAG_CACHE[qid] = false
        return nil
    end
    TAG_CACHE[qid] = { style[1], style[2], tag }
    return style[1], style[2], tag
end

local ROW_TAG_SHOW = { [81] = true, [84] = true, [82] = true }

local function RowTagChip(rec)
    if rec.kind ~= "quest" then return nil end
    local text, ink, tag = QuestTagOf(rec.id)
    if not text or not ROW_TAG_SHOW[tag] then return nil end
    return text, ink
end

local function RowPaint(r, rec, selected)
    r.rec = rec
    r.name:SetText(NameOf(rec.id, rec.kind) or string.format(L["条目 #%d"], rec.id))
    r.sub:SetText(RowSub(rec))
    local chipText, ink = RowChip(rec)
    local tagText, tagInk = RowTagChip(rec)
    local rw = r:GetWidth() or (LIST_W - 2 * PAD - 10)
    local tw = rw - 20
    local right = 10
    if chipText then
        if hui and hui.PaintSolidChip then
            pcall(hui.PaintSolidChip, r.chip, chipText, ink)
        end
        r.chip:ClearAllPoints()
        r.chip:SetPoint("RIGHT", r, "RIGHT", -right, r.chip.__dy or 1)
        r.chip:Show()
        local cw = r.chip:GetWidth() or 40
        tw = tw - cw - 6
        right = right + cw + 5
    else
        r.chip:Hide()
    end
    if tagText then
        if hui and hui.PaintSolidChip then
            pcall(hui.PaintSolidChip, r.tchip, tagText, tagInk)
        end
        r.tchip:ClearAllPoints()
        r.tchip:SetPoint("RIGHT", r, "RIGHT", -right, r.tchip.__dy or 1)
        r.tchip:Show()
        local cw2 = r.tchip:GetWidth() or 40
        tw = tw - cw2 - 6
    else
        r.tchip:Hide()
    end
    if tw < 60 then tw = 60 end
    r.name:SetWidth(tw)
    r.sub:SetWidth(tw)
    if hui and hui.PaintRowSelect then
        pcall(hui.PaintRowSelect, r, selected and true or false)
    end
    r.name:SetTextColor(Unpack(selected and C_TITLE or C_MAIN))
end

local function MakeSolidChipOn(parent, lvl, dy)
    if hui and hui.MakeSolidChip and hui.ChipH then
        local c = hui.MakeSolidChip(parent, lvl, hui.ChipH(14))
        c.__dy = dy or 1
        return c
    end
    local c = CreateFrame("Frame", nil, parent)
    c:SetSize(48, 16)
    c.t = c:CreateFontString()
    c.t:SetAllPoints()
    c.__dy = 0
    return c
end

local function MakeRow(parent)
    local r = CreateFrame("Button", nil, parent, "BackdropTemplate")
    r:SetSize(LIST_W - 2 * PAD - 10, ROW_H)
    r:SetFrameLevel((parent:GetFrameLevel() or 1) + 1)
    if hui and hui.BuildRoundedBG and hui.layer then
        local fill, border = hui.BuildRoundedBG(r, 6, hui.layer.L2, "both", true, 1)
        r.__huiCard = { fill = fill, border = border }
    else
        r:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        r:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
    end
    r.name = MakeFS(r, 14, C_MAIN, "LEFT")
    r.name:SetWordWrap(false)
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -6)
    r.name:SetWidth(LIST_W - 2 * PAD - 30 - 76)
    r.sub = MakeFS(r, 12, C_SUB, "LEFT")
    r.sub:SetWordWrap(false)
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -26)
    r.sub:SetWidth(LIST_W - 2 * PAD - 30 - 76)
    local cdy = (hui and hui.ChipDY and hui.ChipDY(14)) or 1
    r.chip = MakeSolidChipOn(r, (r:GetFrameLevel() or 1) + 2, cdy)
    r.chip:SetPoint("RIGHT", r, "RIGHT", -10, cdy)
    r.tchip = MakeSolidChipOn(r, (r:GetFrameLevel() or 1) + 2, cdy)
    r.tchip:SetPoint("RIGHT", r, "RIGHT", -10, cdy)
    r.tchip:Hide()
    r:SetScript("OnClick", function()
        QS.sel = r.rec
        QS.PaintList()
        QS.PaintDetail()
    end)
    r:SetScript("OnEnter", function()
        if not (QS.sel and r.rec and QS.sel.id == r.rec.id) then r.name:SetTextColor(1, 1, 1) end
    end)
    r:SetScript("OnLeave", function()
        if not (QS.sel and r.rec and QS.sel.id == r.rec.id) then r.name:SetTextColor(Unpack(C_MAIN)) end
    end)
    return r
end

local function HiddenFrom(list, from)
    for i = from, #list do
        list[i]:Hide()
    end
end

function QS.SyncScrollBar()
    local bar = QS.bar
    if not bar then return end
    local viewH = QS.listScroll:GetHeight()
    local contentH = QS.listChild:GetHeight()
    if type(viewH) ~= "number" or type(contentH) ~= "number" or viewH <= 0 then
        bar.track:Hide()
        return
    end
    if contentH <= viewH + 2 then
        bar.track:Hide()
        return
    end
    local trackH = bar.track:GetHeight()
    if type(trackH) ~= "number" or trackH <= 0 then return end
    bar.track:Show()
    local th = math.max(24, trackH * viewH / contentH)
    local v = QS.listScroll:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    local maxV = contentH - viewH
    local frac = 0
    if maxV > 0 then frac = v / maxV end
    if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
    bar.thumb:SetHeight(th)
    bar.thumb:ClearAllPoints()
    bar.thumb:SetPoint("TOP", bar.track, "TOP", 0, -1 - frac * (trackH - th))
end

local function BuildSearchCard(page)
    local card = Card(page, X, -TOP, W, SEARCH_H)
    QS.searchCard = card

    local eb = ns.CreateEditBox(card, W - 16)
    eb:SetSize(W - 16, EB_H)
    eb:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -8)
    if ns.FONT then pcall(eb.SetFont, eb, ns.FONT, 14, "") end
    pcall(eb.SetTextColor, eb, 0.95, 0.96, 0.98)
    pcall(eb.SetTextInsets, eb, 14, 14, 0, 0)
    if eb.SetJustifyV then pcall(eb.SetJustifyV, eb, "MIDDLE") end
    QS.eb = eb

    local ph = MakeFS(eb, 14, C_SUB, "LEFT")
    ph:SetPoint("LEFT", eb, "LEFT", 16, 0)
    ph:SetText(L["搜索任务、NPC 或物品的名称与编号"])
    QS.ph = ph

    eb:SetScript("OnTextChanged", function(self)
        local t = self:GetText() or ""
        QS.text = t
        if #t > 0 then ph:Hide() else ph:Show() end
        QS.Request()
    end)
    eb:SetScript("OnEscapePressed", function(self)
        self:SetText("")
        self:ClearFocus()
    end)

    QS.tab = TabRow(card, 8, -52, {
        { key = "quest", text = L["任务"] },
        { key = "npc", text = L["NPC"] },
        { key = "item", text = L["物品"] },
    }, function(key)
        QS.kind = key
        QS.tab.paint(key)
        QS.sel = nil
        QS.PaintList()
        QS.PaintDetail()
    end)

    QS.tabNote = MakeFS(card, 12, C_SUB, "LEFT")
    QS.tabNote:SetPoint("LEFT", QS.tab.host, "RIGHT", 12, 0)
    QS.tabNote:SetText(L["仅作为 Quest 数据库搜索入口"])
end

local function BuildListCard(page)
    local card = Card(page, X, -BODY_TOP, LIST_W, BODY_H)
    QS.listCard = card
    QS.listHead = MakeFS(card, 14, C_SUB, "LEFT")
    QS.listHead:SetPoint("TOPLEFT", card, "TOPLEFT", PAD, -6)
    QS.listHead:SetText(L["搜索"])

    local scroll = CreateFrame("ScrollFrame", nil, card)
    scroll:SetPoint("TOPLEFT", card, "TOPLEFT", PAD, -(PAD + 14))
    scroll:SetSize(LIST_W - 2 * PAD - 10, BODY_H - (PAD + 14) - PAD)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(self, delta)
        local cur = self:GetVerticalScroll() or 0
        if type(cur) ~= "number" then cur = 0 end
        self:SetVerticalScroll(math.max(0, cur - delta * 60))
    end)
    QS.listScroll = scroll
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(scroll:GetWidth(), 1)
    scroll:SetScrollChild(child)
    QS.listChild = child

    local bar = CreateFrame("Frame", nil, card)
    bar:SetPoint("TOPRIGHT", card, "TOPRIGHT", -1, -(PAD + 14))
    bar:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -1, PAD)
    bar:SetWidth(7)
    bar:SetFrameLevel((scroll:GetFrameLevel() or 1) + 10)
    local track = CreateFrame("Frame", nil, bar)
    track:SetAllPoints()
    if hui and hui.BuildRoundedBG and hui.layer then
        pcall(hui.BuildRoundedBG, track, 3, hui.layer.L2, "both", true, 1)
    else
        track:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        track:SetBackdropColor(0, 0, 0, 0.25)
    end
    local thumb = CreateFrame("Frame", nil, bar)
    thumb:SetWidth(5)
    thumb:SetHeight(24)
    if hui and hui.BuildRoundedBG and hui.layer then
        pcall(hui.BuildRoundedBG, thumb, 2, hui.layer.L4, "both", true, 1)
    else
        thumb:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        thumb:SetBackdropColor(1, 1, 1, 0.3)
    end
    thumb:SetPoint("TOP", track, "TOP", 0, -1)
    bar.track, bar.thumb = track, thumb
    QS.bar = bar
    track:Hide()

    scroll:SetScript("OnVerticalScroll", function() QS.SyncScrollBar() end)
    thumb:EnableMouse(true)
    thumb:SetScript("OnMouseDown", function(self)
        local _, cy = GetCursorPosition()
        local scale = UIParent:GetEffectiveScale() or 1
        self.__y0 = cy / scale
        local s0 = QS.listScroll:GetVerticalScroll() or 0
        if type(s0) ~= "number" then s0 = 0 end
        self.__s0 = s0
        self:SetScript("OnUpdate", function(f)
            local _, y = GetCursorPosition()
            y = y / scale
            local trackH = bar.track:GetHeight() or 1
            local th = f:GetHeight() or 24
            local span = trackH - th
            if span <= 0 then return end
            local contentH = QS.listChild:GetHeight() or 1
            local viewH = QS.listScroll:GetHeight() or 1
            local maxV = contentH - viewH
            if maxV <= 0 then return end
            local d = (f.__y0 - y) / span * maxV
            local v = f.__s0 + d
            if v < 0 then v = 0 elseif v > maxV then v = maxV end
            QS.listScroll:SetVerticalScroll(v)
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
end

local function LayoutChips()
    local x = 0
    for i = 1, #DET.chips do
        local c = DET.chips[i]
        if c:IsShown() then
            c:ClearAllPoints()
            c:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD + x, -58)
            local w = c:GetWidth() or 0
            if type(w) ~= "number" or w <= 0 then w = 40 end
            x = x + w + 6
        end
    end
end

local R = { y = -86, hi = 0, bi = 0, ri = 0, ci = 0 }
local HEX_DIM = "|cff9a9a9a"
local HEX_GOLD = "|cffffd100"
local HEX_GREY = "|cff8c8c8c"

local function IdList(v)
    local out = {}
    if type(v) == "table" then
        for _, x in pairs(v) do
            local n = tonumber(x)
            if n and n > 0 then out[#out + 1] = n end
        end
        table.sort(out)
    end
    return out
end

local function QuestNameOf(qid)
    local nm = NameOf(qid, "quest")
    if type(nm) ~= "string" or nm == "" then return string.format(L["条目 #%d"], qid) end
    return nm
end

local function QuestIdList(id, kind, key)
    local out = {}
    local v = FieldOf(id, kind, key)
    if type(v) ~= "table" then return out end
    for _, x in pairs(v) do
        local qid = tonumber(x)
        if qid and qid > 0 then out[#out + 1] = qid end
    end
    table.sort(out)
    return out
end

local function QLIB()
    local ql = _G.QuestieLoader
    local m = type(ql) == "table" and ql._modules
    local lib = type(m) == "table" and m.QuestieLib
    if type(lib) == "table" then return lib end
    return nil
end

local function RaceStr(mask)
    local n = tonumber(mask) or 0
    if n == 0 then return nil end
    local lib = QLIB()
    if lib and type(lib.GetRaceString) == "function" then
        local ok, v = pcall(lib.GetRaceString, lib, n)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return nil
end

local function ClassStr(mask)
    local n = tonumber(mask) or 0
    if n == 0 then return nil end
    local lib = QLIB()
    if lib and type(lib.GetClassString) == "function" then
        local ok, v = pcall(lib.GetClassString, lib, n)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return nil
end

local function DiffText(qLevel, need)
    local ql = tonumber(qLevel) or 0
    local minLv = tonumber(need) or 0
    if ql <= 0 then ql = minLv end
    if ql <= 0 then return "" end
    if minLv <= 0 then minLv = 1 end
    local gray
    if ql <= 4 then
        gray = ql + 5
    elseif ql <= 13 then
        gray = ql + 6
    elseif ql <= 22 then
        gray = ql + 7
    elseif ql <= 31 then
        gray = ql + 8
    elseif ql <= 40 then
        gray = ql + 9
    elseif ql <= 49 then
        gray = ql + 10
    elseif ql <= 58 then
        gray = ql + 11
    else
        gray = ql + 12
    end
    local red = minLv
    local orange = ql - 4
    local yellow = ql - 2
    local green = ql + 3
    if yellow < minLv then yellow = minLv end
    if orange < minLv then orange = minLv end
    if orange == yellow then orange = nil end
    if orange == nil or red == orange then red = nil end
    if green < minLv then green = minLv end
    if gray < minLv then gray = minLv end
    local parts = {}
    if red then parts[#parts + 1] = "|cFFFF1A1A" .. red .. "|r" end
    if orange then parts[#parts + 1] = "|cFFFF8040" .. orange .. "|r" end
    parts[#parts + 1] = "|cFFFFFF00" .. yellow .. "|r"
    if green then parts[#parts + 1] = "|cFF40C040" .. green .. "|r" end
    if gray then parts[#parts + 1] = "|cFFC0C0C0" .. gray .. "|r" end
    return table.concat(parts, "  ")
end

local function InkHex(c)
    if DG and type(DG.Hex) == "function" and type(c) == "table" then
        local ok, v = pcall(DG.Hex, c)
        if ok and type(v) == "string" then return v end
    end
    return HEX_GOLD
end

local function NpcRow(i)
    local r = DET.npcRows[i]
    if r then return r end
    r = CreateFrame("Button", nil, DET.child)
    r:SetSize(DETAIL_W - 2 * PAD, 26)
    r:SetFrameLevel((DET.child:GetFrameLevel() or 1) + 2)
    r.name = MakeFS(r, 14, C_MAIN, "LEFT")
    r.name:SetWordWrap(false)
    r.name:SetPoint("LEFT", r, "LEFT", 0, 0)
    r.name:SetWidth(210)
    r.pos = MakeFS(r, 12, C_SUB, "LEFT")
    r.pos:SetWordWrap(false)
    r.pos:SetPoint("LEFT", r.name, "RIGHT", 10, 0)
    r.btn = NewButton(r, L["地图"], 56, 24, 14)
    r.btn:SetPoint("RIGHT", r, "RIGHT", 0, 0)
    if r.btn.SetPushedTextOffset then r.btn:SetPushedTextOffset(0, 0) end
    r.btn:SetScript("OnClick", function()
        if r.zoneId and r.x then MapJump(r.linkId, r.linkKind, r.zoneId, r.x, r.y) end
    end)
    if SetTip then SetTip(r.btn, L["在世界地图标记该位置"]) end
    r:SetScript("OnClick", function()
        if r.onClick then
            r.onClick()
            return
        end
        if r.linkId and r.linkKind then QS.GoTo(r.linkId, r.linkKind) end
    end)
    r:SetScript("OnEnter", function()
        if (r.linkId or r.onClick) and r.ink and r.hoverOK ~= false then r.name:SetTextColor(1, 1, 1) end
    end)
    r:SetScript("OnLeave", function()
        if r.ink then r.name:SetTextColor(Unpack(r.ink)) end
    end)
    DET.npcRows[i] = r
    return r
end

local CARD_H = 38
local CARD_GAP = 4

local function CardOf(i)
    local r = DET.cards[i]
    if r then return r end
    r = CreateFrame("Button", nil, DET.child, "BackdropTemplate")
    r:SetSize(DETAIL_W - 2 * PAD, CARD_H)
    r:SetFrameLevel((DET.child:GetFrameLevel() or 1) + 2)
    r:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    if hui and type(hui.HuiCardFX) == "function" and hui.HuiCardFX(r, 10, 2) then
        r.__fx = true
    else
        r:SetBackdropColor(1, 1, 1, (DG and DG.LOOT_CARD_BG) or 0.03)
        r:SetBackdropBorderColor(1, 1, 1, (DG and DG.LOOT_CARD_EDGE) or 0.05)
    end
    r:EnableMouse(true)
    r:EnableMouseWheel(true)
    r:SetScript("OnMouseWheel", function(_, delta)
        local cur = DET.scroll:GetVerticalScroll() or 0
        if type(cur) ~= "number" then cur = 0 end
        DET.scroll:SetVerticalScroll(math.max(0, cur - delta * 60))
    end)
    r:SetScript("OnEnter", function(self)
        if self.__fx and hui and type(hui.HuiCardState) == "function" then
            hui.HuiCardState(self, "hover")
        else
            self:SetBackdropColor(1, 1, 1, (DG and DG.LOOT_CARD_BG_HOVER) or 0.09)
            self:SetBackdropBorderColor(1, 1, 1, (DG and DG.LOOT_CARD_EDGE_HOVER) or 0.18)
        end
        if self.ink then self.name:SetTextColor(1, 1, 1) end
    end)
    r:SetScript("OnLeave", function(self)
        if self.__fx and hui and type(hui.HuiCardState) == "function" then
            hui.HuiCardState(self, "norm")
        else
            self:SetBackdropColor(1, 1, 1, (DG and DG.LOOT_CARD_BG) or 0.03)
            self:SetBackdropBorderColor(1, 1, 1, (DG and DG.LOOT_CARD_EDGE) or 0.05)
        end
        if self.ink then self.name:SetTextColor(Unpack(self.ink)) end
    end)
    r:SetScript("OnClick", function(self)
        if self.qid then QS.GoTo(self.qid, "quest") end
    end)
    r.name = MakeFS(r, 14, C_MAIN, "LEFT")
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -4)
    r.name:SetWordWrap(false)
    r.st = MakeFS(r, 13, C_SUB, "RIGHT")
    r.st:SetPoint("TOPRIGHT", r, "TOPRIGHT", -10, -5)
    r.st:SetJustifyH("RIGHT")
    r.st:SetWordWrap(false)
    r.sub = MakeFS(r, 12, C_SUB, "LEFT")
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 10, -22)
    r.sub:SetWordWrap(false)
    DET.cards[i] = r
    return r
end

local function QuestCardRow(qid, ind)
    R.ci = R.ci + 1
    local r = CardOf(R.ci)
    ind = ind or 0
    local w = DETAIL_W - 2 * PAD - ind
    r:SetSize(w, CARD_H)
    r.qid = qid
    local st = StatusOf(qid)
    local tag, ink = "", C_MAIN
    if st == "done" then
        tag, ink = L["已完成"], INK_DONE
    elseif st == "act" then
        tag, ink = L["进行中"], INK_ACT
    end
    r.ink = ink
    r.name:SetText(QuestNameOf(qid) .. HEX_DIM .. " #" .. qid .. "|r")
    local nw = r.name:GetStringWidth()
    if type(nw) ~= "number" or nw <= 0 then nw = 80 end
    if nw > w - 120 then nw = w - 120 end
    r.name:SetWidth(nw + 6)
    r.name:SetTextColor(Unpack(ink))
    r.st:SetText(tag)
    r.st:SetTextColor(Unpack(ink))

    local sub = ""
    local qr = QuestRec(qid)
    local stN = qr and qr.Starts
    local firstNpc = type(stN) == "table" and IdList(stN.NPC)[1] or nil
    if firstNpc then
        local p = SpawnsOf(firstNpc, "npc")[1]
        if p then
            sub = (ZoneName(p.zone) or "") .. string.format(" %.1f,%.1f", p.x, p.y)
        end
    end
    if sub == "" then sub = ZoneName(FieldOf(qid, "quest", "zoneOrSort")) or L["未知区域"] end
    local needLv = tonumber(FieldOf(qid, "quest", "requiredLevel")) or 0
    if needLv > 0 then sub = sub .. " · " .. string.format(L["%d 级可接"], needLv) end
    r.sub:SetText(sub)

    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD + ind, R.y)
    r:Show()
    R.y = R.y - CARD_H - CARD_GAP
end

local function Head(title, onClick)
    R.hi = R.hi + 1
    if R.hi + R.bi + R.ri > 1 then R.y = R.y - 6 end
    local h = DET.heads[R.hi]
    if not h then
        h = MakeFS(DET.child, 14, C_GOLD, "LEFT")
        h:SetWidth(DETAIL_W - 2 * PAD - 8)
        DET.heads[R.hi] = h
    end
    h:ClearAllPoints()
    h:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD, R.y)
    h:SetText(title)
    if onClick then
        h:EnableMouse(true)
        h:SetScript("OnMouseUp", onClick)
        h:SetTextColor(Unpack(C_GOLD))
    else
        h:EnableMouse(false)
        h:SetScript("OnMouseUp", nil)
        h:SetTextColor(Unpack(C_GOLD))
    end
    h:Show()
    R.y = R.y - 20
    return h
end

local function Body(txt, ink, gap)
    R.bi = R.bi + 1
    local b = DET.bodies[R.bi]
    if not b then
        b = MakeFS(DET.child, 14, C_MAIN, "LEFT")
        b:SetWidth(DETAIL_W - 2 * PAD - 8)
        b:SetWordWrap(true)
        b:SetJustifyH("LEFT")
        DET.bodies[R.bi] = b
    end
    b:ClearAllPoints()
    b:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD, R.y)
    b:SetText(txt)
    b:SetTextColor(Unpack(ink or C_MAIN))
    b:Show()
    local h = b:GetStringHeight()
    if type(h) ~= "number" or h < 14 then h = 20 end
    R.y = R.y - h - (gap or 8)
end

local function Line(o)
    R.ri = R.ri + 1
    local r = NpcRow(R.ri)
    local ind = o.indent or 0
    local right = o.map and 66 or 0
    r.linkId, r.linkKind = o.id, o.kind
    r.onClick = o.onClick
    r.hoverOK = o.plain ~= false
    r.zoneId, r.x, r.y = o.zone, o.x, o.y
    local avail = DETAIL_W - 2 * PAD - ind - right - 6
    r.name:ClearAllPoints()
    r.name:SetPoint("LEFT", r, "LEFT", ind, 0)
    r.name:SetText(o.text or "")
    local nw = r.name:GetStringWidth()
    if type(nw) ~= "number" or nw <= 0 then nw = 60 end
    local reserve = (o.sub and o.sub ~= "") and 90 or 0
    if nw > avail - reserve then nw = math.max(60, avail - reserve) end
    r.name:SetWidth(nw + 4)
    r.ink = o.ink or C_MAIN
    r.name:SetTextColor(Unpack(r.ink))
    r.pos:ClearAllPoints()
    r.pos:SetPoint("LEFT", r.name, "RIGHT", 8, 0)
    r.pos:SetText(o.sub or "")
    r.pos:SetTextColor(Unpack(o.subInk or C_SUB))
    r.pos:SetWidth(math.max(10, avail - nw - 8))
    if o.map then r.btn:Show() else r.btn:Hide() end
    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD, R.y)
    r:Show()
    R.y = R.y - 26
end

local function QuestLinkLine(qid, indent)
    local tag, ink = "", C_MAIN
    local st = StatusOf(qid)
    if st == "done" then
        tag, ink = L["已完成"], INK_DONE
    elseif st == "act" then
        tag, ink = L["进行中"], INK_ACT
    end
    Line({
        id = qid, kind = "quest", ink = INK_KIND, indent = indent or 0, plain = false,
        text = QuestNameOf(qid) .. HEX_DIM .. " #" .. qid .. "|r",
        sub = tag, subInk = ink,
    })
end

local ALSO_OPEN = {}

local function AlsoList(id, kind, curId, key, field)
    local all = IdList(FieldOf(id, kind, field))
    local keep = {}
    for i = 1, #all do
        if all[i] ~= curId then keep[#keep + 1] = all[i] end
    end
    if #keep == 0 then return end
    local tag = kind .. ":" .. id .. ":" .. field
    local open = ALSO_OPEN[tag] == true
    local hint = open and L["点击收起"] or L["点击展开"]
    Line({
        ink = C_SUB, indent = 16,
        text = L[key] .. string.format(L[" · %d 个"], #keep) .. " · " .. hint,
        onClick = function()
            ALSO_OPEN[tag] = not open
            QS.PaintDetail()
        end,
    })
    if not open then return end
    local n = math.min(#keep, 8)
    for i = 1, n do
        QuestLinkLine(keep[i], 16)
    end
    if #keep > n then
        Line({ text = string.format(L["另有 %d 个任务"], #keep - n), ink = C_SUB, indent = 16 })
    end
end

local function Begin(top)
    R.y = top or -86
    R.hi, R.bi, R.ri, R.ci = 0, 0, 0, 0
end

local function End()
    for i = R.hi + 1, #DET.heads do DET.heads[i]:Hide() end
    for i = R.bi + 1, #DET.bodies do DET.bodies[i]:Hide() end
    HiddenFrom(DET.npcRows, R.ri + 1)
    for i = R.ci + 1, #(DET.cards or {}) do DET.cards[i]:Hide() end
    DET.child:SetHeight(math.max(200, -R.y + PAD))
    DET.scroll:SetVerticalScroll(0)
end

local function DetChip(i, text, ink)
    local c = DET.chips[i]
    if not c then return end
    if not text or text == "" then
        c:Hide()
        return
    end
    if hui and hui.PaintSolidChip then
        pcall(hui.PaintSolidChip, c, text, ink)
    elseif c.t then
        c.t:SetText(text)
    end
    c:Show()
end

local function TextOf(v)
    if type(v) == "string" then return v end
    if type(v) == "table" then
        local lines = {}
        for i = 1, #v do
            local s = v[i]
            if type(s) == "string" and s ~= "" then lines[#lines + 1] = s end
        end
        return table.concat(lines, "\n")
    end
    return ""
end

local function NpcFriendly(npcId)
    local g = _G.QuestieDB
    if type(g) ~= "table" or type(g.IsFriendlyToPlayer) ~= "function" then return true end
    local f = FieldOf(npcId, "npc", "friendlyToFaction")
    if f == nil then return true end
    local ok, r = pcall(g.IsFriendlyToPlayer, f)
    if ok then return r and true or false end
    return true
end

local function NpcLevelOf(id)
    local lv = tonumber(FieldOf(id, "npc", "level")) or 0
    if lv > 0 then return lv end
    return tonumber(FieldOf(id, "npc", "minLevel")) or 0
end

local function SourceRow(id, kind, level)
    local pts = SpawnsOf(id, kind)
    if #pts == 0 then return nil end
    local nm = NameOf(id, kind)
    if type(nm) ~= "string" or nm == "" then nm = string.format(L["条目 #%d"], id) end
    if type(level) == "number" and level > 0 then nm = string.format("[%d] %s", level, nm) end
    local p = pts[1]
    return { id = id, kind = kind, name = nm, zone = p.zone, x = p.x, y = p.y }
end

local function ItemSources(id)
    local groups = {}
    local function push(title, kind, ids)
        local rows = {}
        local list = {}
        if type(ids) == "table" then
            for _, v in pairs(ids) do
                local n = tonumber(v)
                if n and n > 0 then list[#list + 1] = n end
            end
            table.sort(list)
            for i = 1, #list do
                local sid = list[i]
                local lv = 0
                if kind == "npc" then lv = NpcLevelOf(sid) end
                local r = SourceRow(sid, kind, lv)
                if r then rows[#rows + 1] = r end
            end
        end
        table.sort(rows, function(a, b) return a.name < b.name end)
        groups[#groups + 1] = { title = title, rows = rows }
    end
    push(L["掉落 NPC"], "npc", FieldOf(id, "item", "npcDrops"))
    push(L["掉落物体"], "object", FieldOf(id, "item", "objectDrops"))
    local vendors = FieldOf(id, "item", "vendors")
    local kept = {}
    if type(vendors) == "table" then
        for _, v in pairs(vendors) do
            local n = tonumber(v)
            if n and n > 0 and NpcFriendly(n) then kept[#kept + 1] = n end
        end
        if #kept == 0 then kept = vendors end
    end
    push(L["供应商"], "npc", kept)
    return groups
end

local TITLE_CHIP_TOP = -12

local function PaintTitleTag(rec)
    for i = 1, #(DET.titleTags or {}) do DET.titleTags[i]:Hide() end
    if not (rec and rec.kind == "quest") then return end
    local text, ink = QuestTagOf(rec.id)
    if not text then return end
    local c = DET.titleTags[1]
    if not c then return end
    if hui and hui.PaintSolidChip then
        pcall(hui.PaintSolidChip, c, text, ink)
    elseif c.t then
        c.t:SetText(text)
    end
    local tw = DET.title:GetStringWidth()
    if type(tw) ~= "number" or tw <= 0 then tw = 80 end
    local maxX = DETAIL_W - 2 * PAD - 8
    local x = PAD + math.min(tw, maxX) + 8
    local cw = c:GetWidth() or 40
    if type(cw) ~= "number" or cw <= 0 then cw = 40 end
    if x + cw > DETAIL_W - PAD then x = DETAIL_W - PAD - cw end
    if x < PAD then x = PAD end
    local th = DET.title:GetHeight()
    if type(th) ~= "number" or th <= 0 then th = 22 end
    local ch = c:GetHeight() or hui.ChipH and hui.ChipH(14) or 14
    if type(ch) ~= "number" or ch <= 0 then ch = 14 end
    local y = TITLE_CHIP_TOP - (th - ch) / 2
    c:ClearAllPoints()
    c:SetPoint("TOPLEFT", DET.child, "TOPLEFT", x, y)
    c:Show()
end

local function ResetDetail()
    DET.title:SetText(L["选择一个条目"])
    DET.title:SetTextColor(Unpack(C_TITLE))
    for i = 1, #(DET.titleTags or {}) do DET.titleTags[i]:Hide() end
    DET.meta:SetText("")
    for i = 1, #DET.heads do DET.heads[i]:Hide() end
    for i = 1, #DET.bodies do DET.bodies[i]:Hide() end
    if DET.itemIcon then DET.itemIcon:Hide() end
    if DET.itemBtn then DET.itemBtn:Hide() end
    if DET.itemName then DET.itemName:Hide() end
    HiddenFrom(DET.npcRows, 1)
    for i = 1, #(DET.cards or {}) do DET.cards[i]:Hide() end
    DET.note:SetText(L["左侧输入关键词，点任意一条结果查看详情与位置"])
    DET.note:Show()
    DET.child:SetHeight(160)
    DET.scroll:SetVerticalScroll(0)
end

local function PaintQuestDetail(rec)
    local id = rec.id
    local st = StatusOf(id)
    local stTxt, stInk = L["未接取"], INK_NEUTRAL
    if st == "done" then
        stTxt, stInk = L["已完成"], INK_DONE
    elseif st == "act" then
        stTxt, stInk = L["进行中"], C_GOLD
    end

    DET.meta:SetText("")
    LayoutChips()

    local qrec = QuestRec(id) or {}
    local apiDesc, apiObjs = "", ""
    if DG then
        if type(DG.QuestObjectives) == "function" then
            local ok, v = pcall(DG.QuestObjectives, id)
            if ok then apiObjs = TextOf(v) end
        end
        if type(DG.QuestDescription) == "function" then
            local ok, v = pcall(DG.QuestDescription, id)
            if ok then apiDesc = TextOf(v) end
        end
        if type(DG.AskQuestData) == "function" then pcall(DG.AskQuestData, id) end
    end

    local lv = QuestLevelOf(id)
    local needLv = tonumber(FieldOf(id, "quest", "requiredLevel")) or 0

    local descText = TextOf(qrec.Description)
    if descText == "" then descText = apiDesc end

    local dbObj = TextOf(qrec.objectivesText)
    local objText = apiObjs
    if objText == "" then objText = dbObj end
    if objText == descText then objText = "" end
    if objText == "" and descText == "" then objText = L["客户端未收录这个任务的目标文本"] end

    Begin(-64)

    Body(HEX_GREY .. L["状态："] .. "|r" .. InkHex(stInk) .. stTxt .. "|r", C_MAIN, 4)

    local lvHex = HEX_GOLD
    if DG and type(DG.DifficultyColor) == "function" and type(DG.Hex) == "function" and lv > 0 then
        local c = DG.DifficultyColor(lv)
        if c then lvHex = DG.Hex(c) end
    end
    local lvSeg
    if needLv > 0 then
        lvSeg = HEX_GOLD .. string.format(L["%d 级可接"], needLv) .. "|r"
    else
        lvSeg = HEX_GREY .. L["不限"] .. "|r"
    end
    if lv > 0 then
        lvSeg = lvSeg .. " · " .. lvHex .. string.format(L["任务等级 Lv%s"], tostring(lv)) .. "|r"
    end
    Body(HEX_GREY .. L["可接等级"] .. "：|r" .. lvSeg, C_MAIN, 4)

    local diff = DiffText(lv, needLv)
    if diff ~= "" then
        Body(HEX_GREY .. L["任务难度"] .. "：|r" .. diff, C_MAIN, 4)
    end

    local fac, facInk = L["双阵营共有"], nil
    local rmask = tonumber(qrec.requiredRaces) or 0
    local DBX = QDB()
    local rk = DBX and type(DBX.raceKeys) == "table" and DBX.raceKeys or nil
    if rmask > 0 then
        if rk and rk.ALL_ALLIANCE and rmask == rk.ALL_ALLIANCE then
            fac, facInk = L["联盟专属"], DG and DG.C_FAC_A or nil
        elseif rk and rk.ALL_HORDE and rmask == rk.ALL_HORDE then
            fac, facInk = L["部落专属"], DG and DG.C_FAC_H or nil
        else
            local rs = RaceStr(rmask)
            if rs then fac = rs end
        end
    end
    local facTxt = fac
    if facInk then facTxt = InkHex(facInk) .. fac .. "|r" end
    Body(HEX_GREY .. L["阵营"] .. "：|r" .. facTxt, C_MAIN, 4)

    local cls = ClassStr(qrec.requiredClasses)
    if cls then
        Body(HEX_GREY .. L["职业"] .. "：|r" .. cls, C_MAIN, 4)
    end
    if qrec.IsRepeatable then
        Body(HEX_GREY .. L["可重复"] .. "|r", C_MAIN, 4)
    end

    local stRec = qrec.Starts
    local sNpc = IdList(stRec and stRec.NPC)
    local sObj = IdList(stRec and stRec.GameObject)
    local sItem = IdList(stRec and stRec.Item)
    local fNpc, fObj = {}, {}
    local fiRec = qrec.Finisher
    if type(fiRec) == "table" then
        fNpc = IdList(fiRec.NPC)
        fObj = IdList(fiRec.GameObject)
    end
    if #sNpc == 0 and #sObj == 0 and #sItem == 0 then
        local s1 = FieldOf(id, "quest", "startedBy")
        if type(s1) == "table" then sNpc = IdList(s1[1]) end
    end
    if #fNpc == 0 and #fObj == 0 then
        local f1 = FieldOf(id, "quest", "finishedBy")
        if type(f1) == "table" then fNpc = IdList(f1[1]) end
    end

    local function PlaceRow(label, pid, pk)
        local nm = NameOf(pid, pk) or string.format(L["条目 #%d"], pid)
        local pts = SpawnsOf(pid, pk)
        local p = pts[1]
        local tail
        if p then
            tail = HEX_DIM .. " #" .. pid .. " · " .. (ZoneName(p.zone) or "")
                .. string.format(" %.1f,%.1f", p.x, p.y) .. "|r"
        else
            tail = HEX_DIM .. " #" .. pid .. " · " .. L["没有收录刷新位置"] .. "|r"
        end
        Line({
            id = pid, kind = pk, ink = C_MAIN, plain = false,
            text = HEX_GREY .. label .. "|r" .. HEX_GOLD .. nm .. "|r" .. tail,
            zone = p and p.zone, x = p and p.x, y = p and p.y, map = p ~= nil,
        })
    end

    if #sNpc + #sObj + #sItem + #fNpc + #fObj == 0 then
        Body(HEX_GREY .. L["起始："] .. "|r" .. L["客户端未收录"], C_MAIN, 4)
    end
    for i = 1, math.min(#sNpc, 4) do
        PlaceRow(L["起始："], sNpc[i], "npc")
        AlsoList(sNpc[i], "npc", id, "此 NPC 还可以开启以下任务", "questStarts")
    end
    for i = 1, math.min(#sObj, 4) do
        PlaceRow(L["起始："], sObj[i], "object")
        AlsoList(sObj[i], "object", id, "此物体还可以开启以下任务", "questStarts")
    end
    for i = 1, math.min(#sItem, 4) do
        local iid = sItem[i]
        local inm = NameOf(iid, "item") or string.format(L["条目 #%d"], iid)
        Line({
            id = iid, kind = "item", ink = C_MAIN, plain = false,
            text = HEX_GREY .. L["起始："] .. "|r" .. HEX_GOLD .. inm .. "|r"
                .. HEX_DIM .. " #" .. iid .. "|r",
        })
    end
    for i = 1, math.min(#fNpc, 4) do
        PlaceRow(L["结束："], fNpc[i], "npc")
        AlsoList(fNpc[i], "npc", id, "此 NPC 还可以交付以下任务", "questEnds")
    end
    for i = 1, math.min(#fObj, 4) do
        PlaceRow(L["结束："], fObj[i], "object")
        AlsoList(fObj[i], "object", id, "此物体还可以交付以下任务", "questEnds")
    end

    local preOne = IdList(qrec.preQuestSingle)
    local preAll = IdList(qrec.preQuestGroup)
    if #preOne + #preAll > 0 then
        Head(L["前置任务"])
        for i = 1, math.min(#preOne, 8) do QuestCardRow(preOne[i], 0) end
        if #preAll > 0 then
            if #preOne > 0 then Line({ text = L["需全部完成"], ink = C_SUB }) end
            for i = 1, math.min(#preAll, 8) do QuestCardRow(preAll[i], 0) end
        end
    end

    local fol = {}
    local nq = tonumber(qrec.nextQuestInChain) or 0
    if nq > 0 then fol[#fol + 1] = nq end
    local kids = IdList(qrec.childQuests)
    for i = 1, #kids do
        local dup = false
        for j = 1, #fol do
            if fol[j] == kids[i] then dup = true end
        end
        if not dup then fol[#fol + 1] = kids[i] end
    end
    if #fol > 0 then
        Head(L["后续任务"])
        for i = 1, math.min(#fol, 8) do QuestCardRow(fol[i], 0) end
    end

    if descText ~= "" then
        Head(L["任务说明"])
        Body(descText)
    end
    if objText ~= "" then
        Head(L["任务需求"])
        Body(objText)
    end

    End()
end

local function PlaceInfoText(id, kind)
    local parts = {}
    if kind == "npc" then
        local mn = tonumber(FieldOf(id, "npc", "minLevel")) or 0
        local mx = tonumber(FieldOf(id, "npc", "maxLevel")) or 0
        if mn > 0 then
            if mx > mn then
                parts[#parts + 1] = string.format(L["等级 %d - %d"], mn, mx)
            else
                parts[#parts + 1] = string.format(L["等级 %d"], mn)
            end
        end
        local mh = tonumber(FieldOf(id, "npc", "minLevelHealth")) or 0
        local xh = tonumber(FieldOf(id, "npc", "maxLevelHealth")) or 0
        if mh > 0 then
            if xh > mh then
                parts[#parts + 1] = L["生命"] .. string.format(" %d - %d", mh, xh)
            else
                parts[#parts + 1] = L["生命"] .. string.format(" %d", mh)
            end
        end
        local fa = FieldOf(id, "npc", "friendlyToFaction")
        local txt = L["未收录"]
        if fa == "AH" then
            txt = L["双方阵营"]
        elseif fa == "A" then
            txt = L["联盟"]
        elseif fa == "H" then
            txt = L["部落"]
        end
        parts[#parts + 1] = L["阵营"] .. "：" .. txt
    end
    return table.concat(parts, " · ")
end

local function PaintPlaceDetail(rec)
    local id, kind = rec.id, rec.kind
    local pts = SpawnsOf(id, kind)

    local zoneTxt = L["未知区域"]
    if #pts > 0 then zoneTxt = ZoneName(pts[1].zone) or zoneTxt end
    local meta = KindText(kind) .. " · " .. zoneTxt
    if #pts > 0 then meta = meta .. string.format(L[" · %d 处刷新"], #pts) end
    meta = meta .. " · " .. string.format(L["编号 %d"], id)
    DET.meta:SetText(meta)

    DetChip(1, nil, nil)
    LayoutChips()

    Begin()

    local infoTxt = PlaceInfoText(id, kind)
    if infoTxt ~= "" then Body(infoTxt, C_SUB) end

    if #pts == 0 then
        Head(L["刷新位置"] .. "：" .. L["没有收录刷新位置"])
    else
        Head(L["刷新位置"])
    end
    for i = 1, math.min(#pts, 10) do
        local p = pts[i]
        Line({
            id = id, kind = kind, ink = C_MAIN,
            text = ZoneName(p.zone) or L["未知区域"],
            sub = string.format("%.1f, %.1f", p.x, p.y),
            zone = p.zone, x = p.x, y = p.y, map = true,
        })
    end

    local starts = QuestIdList(id, kind, "questStarts")
    local ends = QuestIdList(id, kind, "questEnds")
    if #starts > 0 then
        Head(L["起始的任务"] .. string.format(L[" · %d 个"], #starts))
        for i = 1, math.min(#starts, 8) do QuestLinkLine(starts[i], 0) end
    else
        Head(L["起始的任务"] .. " · " .. L["客户端未收录"])
    end
    if #ends > 0 then
        Head(L["可交付的任务"] .. string.format(L[" · %d 个"], #ends))
        for i = 1, math.min(#ends, 8) do QuestLinkLine(ends[i], 0) end
    else
        Head(L["可交付的任务"] .. " · " .. L["客户端未收录"])
    end

    End()
end

local ICON_SZ = 34

local function ScheduleItemRepaint(id)
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    DET.itemWait = (DET.itemWait or 0) + 1
    local n = DET.itemWait
    local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    local function check(tries)
        if DET.itemId ~= id or n ~= DET.itemWait then return end
        local ok, nm = false, nil
        if type(gi) == "function" then ok, nm = pcall(gi, id) end
        if ok and type(nm) == "string" and nm ~= "" then
            if QS.sel and QS.sel.kind == "item" and QS.sel.id == id then QS.PaintDetail() end
            return
        end
        if DG and type(DG.RequestItem) == "function" then pcall(DG.RequestItem, id) end
        if tries > 0 then C_Timer.After(0.4, function() check(tries - 1) end) end
    end
    C_Timer.After(0.4, function() check(10) end)
end

local function ItemIcon(id)
    local f = C_Item and C_Item.GetItemIconByID
    if type(f) == "function" then
        local ok, v = pcall(f, id)
        if ok and v ~= nil and v ~= "" then return v end
    end
    local info = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(info) == "function" then
        local ok, v = pcall(info, id)
        if ok and v ~= nil and v ~= "" then return v end
    end
    return nil
end

local function ItemTip(self, id)
    if not id then return end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    local link = DG and type(DG.ItemLink) == "function" and select(2, pcall(DG.ItemLink, id)) or nil
    local hl = (type(link) == "string" and link ~= "") and link or ("item:" .. tostring(id) .. ":0:0:0:0:0:0:0")
    GameTooltip:ClearLines()
    local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, hl)
    if not ok and GameTooltip.SetItemByID then
        pcall(GameTooltip.SetItemByID, GameTooltip, id)
    end
    GameTooltip:Show()
    if hui and type(hui.SkinGameTooltip) == "function" then pcall(hui.SkinGameTooltip, GameTooltip) end
    if DG and type(DG.RequestItem) == "function" then pcall(DG.RequestItem, id) end
end

local function PaintItemDetail(rec)
    local id = rec.id
    local il = tonumber(FieldOf(id, "item", "itemLevel")) or 0
    local rl = tonumber(FieldOf(id, "item", "requiredLevel")) or 0
    local q = 0
    local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    local okC, iname, _, cq, cil, crl = pcall(gi, id)
    if okC then
        q = tonumber(cq) or 0
        local v = tonumber(cil)
        if v and v > 0 then il = v end
        v = tonumber(crl)
        if v and v > 0 then rl = v end
    end
    local icon = ItemIcon(id)
    if not icon then icon = "Interface\\Icons\\INV_Misc_QuestionMark" end

    local meta = L["物品"]
    if il > 0 then meta = string.format(L["物品等级 %d"], il) end
    if q > 0 then meta = meta .. " · " .. string.format(L["品质 %d"], q) end
    if rl > 0 then meta = meta .. string.format(L[" · 需 %d 级"], rl) end
    meta = meta .. " · " .. string.format(L["编号 %d"], id)
    DET.meta:SetText(meta)

    DetChip(1, nil, nil)
    LayoutChips()

    local link
    if DG and type(DG.ItemLink) == "function" then
        local ok, v = pcall(DG.ItemLink, id)
        if ok and type(v) == "string" and v ~= "" then link = v end
    end
    local name = NameOf(id, "item") or string.format(L["条目 #%d"], id)

    if not DET.itemIcon then
        DET.itemIcon = DET.child:CreateTexture(nil, "ARTWORK")
        DET.itemIcon:SetSize(ICON_SZ, ICON_SZ)
        DET.itemBtn = CreateFrame("Button", nil, DET.child)
        DET.itemBtn:SetSize(ICON_SZ, ICON_SZ)
        DET.itemBtn:SetFrameLevel((DET.child:GetFrameLevel() or 1) + 3)
        DET.itemBtn:EnableMouseWheel(true)
        DET.itemBtn:SetScript("OnEnter", function(self) ItemTip(self, DET.itemId) end)
        DET.itemBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)
        DET.itemBtn:SetScript("OnMouseWheel", function(self, delta)
            local cur = DET.scroll:GetVerticalScroll() or 0
            if type(cur) ~= "number" then cur = 0 end
            DET.scroll:SetVerticalScroll(math.max(0, cur - delta * 60))
        end)
        DET.itemName = MakeFS(DET.child, 14, C_MAIN, "LEFT")
        DET.itemName:SetWordWrap(true)
        DET.itemName:SetJustifyH("LEFT")
    end
    DET.itemId = id
    DET.itemIcon:SetTexture(icon)
    DET.itemIcon:ClearAllPoints()
    DET.itemIcon:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD, -86)
    DET.itemIcon:Show()

    DET.itemName:ClearAllPoints()
    DET.itemName:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD + ICON_SZ + 10, -96)
    DET.itemName:SetWidth(DETAIL_W - 2 * PAD - ICON_SZ - 18)
    local cacheOK = okC and type(iname) == "string" and iname ~= ""
    local text
    if cacheOK then
        text = link or iname
    elseif name then
        text = name
    else
        text = string.format(L["条目 #%d"], id)
    end
    DET.itemName:SetText(text)
    DET.itemName:SetTextColor(Unpack(C_MAIN))
    DET.itemName:Show()

    local tw = DET.itemName:GetStringWidth()
    if type(tw) ~= "number" or tw < 40 then tw = 40 end
    DET.itemBtn:ClearAllPoints()
    DET.itemBtn:SetPoint("TOPLEFT", DET.child, "TOPLEFT", PAD, -86)
    DET.itemBtn:SetSize(ICON_SZ + 10 + math.min(tw, DETAIL_W - 2 * PAD - ICON_SZ - 18), ICON_SZ)
    DET.itemBtn:Show()

    if not cacheOK then
        if DG and type(DG.RequestItem) == "function" then pcall(DG.RequestItem, id) end
        ScheduleItemRepaint(id)
    end

    Begin()
    R.y = -86 - ICON_SZ - 14
    local groups = ItemSources(id)
    for i = 1, #groups do
        local g = groups[i]
        if #g.rows == 0 then
            Head(g.title .. " · " .. L["客户端未收录"])
        else
            local tag = "src:" .. id .. ":" .. g.title
            local open = ALSO_OPEN[tag] == true
            local foldable = #g.rows > 2
            local shown = #g.rows
            if foldable and not open then shown = 2 end
            if foldable then
                local hint = open and L["点击收起"] or L["点击展开"]
                Head(g.title .. string.format(L[" · %d 个"], #g.rows) .. " · " .. hint, function()
                    ALSO_OPEN[tag] = not open
                    QS.PaintDetail()
                end)
            else
                Head(g.title .. string.format(L[" · %d 个"], #g.rows))
            end
            for j = 1, shown do
                local src = g.rows[j]
                local sub = string.format("%s %.1f, %.1f · ", ZoneName(src.zone) or "", src.x, src.y)
                    .. string.format(L["编号 %d"], src.id)
                Line({
                    id = src.id, kind = src.kind, text = src.name, sub = sub, ink = C_MAIN,
                    zone = src.zone, x = src.x, y = src.y, map = true,
                })
            end
        end
    end
    End()
end

local function StartWatch()
    if DET.watch then return end
    local f = CreateFrame("Frame")
    f.t = 0
    f:SetScript("OnUpdate", function(self, el)
        self.t = self.t + (el or 0)
        if self.t < 0.5 then return end
        self.t = 0
        local rec = QS.sel
        if not rec or rec.kind ~= "quest" or not rec.id then return end
        if not (DG and type(DG.QuestDataSig) == "function") then return end
        local ok, sig = pcall(DG.QuestDataSig, rec.id)
        if not ok or sig == nil then return end
        if DET.sig ~= nil and sig ~= DET.sig then
            DET.sig = sig
            QS.PaintDetail()
        end
    end)
    DET.watch = f
end

function QS.PaintDetail()
    if not DET.card then return end
    local rec = QS.sel
    for i = 1, #DET.chips do DET.chips[i]:Hide() end
    if not rec then
        DET.sig = nil
        ResetDetail()
        return
    end
    DET.note:Hide()
    local nmTxt = NameOf(rec.id, rec.kind) or string.format(L["条目 #%d"], rec.id)
    if rec.kind == "quest" then
        nmTxt = nmTxt .. HEX_DIM .. " #" .. rec.id .. "|r"
    end
    DET.title:SetText(nmTxt)
    DET.title:SetTextColor(Unpack(rec.kind == "quest" and C_GOLD or C_TITLE))
    PaintTitleTag(rec)
    for i = 1, #DET.heads do DET.heads[i]:Hide() end
    for i = 1, #DET.bodies do DET.bodies[i]:Hide() end
    if DET.itemIcon then DET.itemIcon:Hide() end
    if DET.itemBtn then DET.itemBtn:Hide() end
    if DET.itemName then DET.itemName:Hide() end
    for i = 1, #(DET.cards or {}) do DET.cards[i]:Hide() end
    if rec.kind == "quest" then
        if DG and type(DG.QuestDataSig) == "function" then
            local ok, sig = pcall(DG.QuestDataSig, rec.id)
            DET.sig = ok and sig or nil
            StartWatch()
        end
        PaintQuestDetail(rec)
    elseif rec.kind == "item" then
        DET.sig = nil
        PaintItemDetail(rec)
    else
        DET.sig = nil
        PaintPlaceDetail(rec)
    end
end

function QS.GoTo(id, kind)
    if not id or not kind then return end
    QS.sel = { id = id, kind = kind }
    if ns.PlaySound then pcall(ns.PlaySound, 1) end
    QS.PaintList()
    QS.PaintDetail()
end

local function BuildDetailCard(page)
    local card = Card(page, X + LIST_W + GUT, -BODY_TOP, DETAIL_W, BODY_H)
    DET.card = card
    local scroll = CreateFrame("ScrollFrame", nil, card)
    scroll:SetPoint("TOPLEFT", card, "TOPLEFT", 0, 0)
    scroll:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -8, 0)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(self, delta)
        local cur = self:GetVerticalScroll() or 0
        if type(cur) ~= "number" then cur = 0 end
        self:SetVerticalScroll(math.max(0, cur - delta * 60))
    end)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(DETAIL_W - 2 * PAD, 240)
    scroll:SetScrollChild(child)
    DET.scroll, DET.child = scroll, child

    DET.title = MakeFS(child, 18, C_TITLE, "LEFT")
    DET.title:SetPoint("TOPLEFT", child, "TOPLEFT", PAD, -12)
    DET.title:SetWidth(DETAIL_W - 2 * PAD - 8)
    DET.title:SetWordWrap(false)

    DET.titleTags = {}
    for i = 1, 2 do
        local c = MakeSolidChipOn(child, (child:GetFrameLevel() or 1) + 2, 0)
        c:Hide()
        DET.titleTags[i] = c
    end

    DET.meta = MakeFS(child, 12, C_SUB, "LEFT")
    DET.meta:SetPoint("TOPLEFT", child, "TOPLEFT", PAD, -38)
    DET.meta:SetWidth(DETAIL_W - 2 * PAD - 8)
    DET.meta:SetWordWrap(false)

    DET.chips = {}
    for i = 1, 2 do
        local c
        if hui and hui.MakeSolidChip and hui.ChipH then
            c = hui.MakeSolidChip(child, (child:GetFrameLevel() or 1) + 2, hui.ChipH(14))
        else
            c = CreateFrame("Frame", nil, child)
            c:SetSize(56, 16)
            c.t = c:CreateFontString()
            c.t:SetAllPoints()
        end
        c:Hide()
        DET.chips[i] = c
    end

    DET.heads = {}
    for i = 1, 8 do
        local h = MakeFS(child, 14, C_GOLD, "LEFT")
        h:SetPoint("TOPLEFT", child, "TOPLEFT", PAD, -86)
        h:SetWidth(DETAIL_W - 2 * PAD - 8)
        h:Hide()
        DET.heads[i] = h
    end

    DET.bodies = {}
    for i = 1, 8 do
        local b = MakeFS(child, 14, C_MAIN, "LEFT")
        b:SetPoint("TOPLEFT", child, "TOPLEFT", PAD, -108)
        b:SetWidth(DETAIL_W - 2 * PAD - 8)
        b:SetWordWrap(true)
        b:SetJustifyH("LEFT")
        b:Hide()
        DET.bodies[i] = b
    end

    DET.npcRows = {}
    DET.cards = {}

    DET.note = MakeFS(child, 14, C_SUB, "LEFT")
    DET.note:SetPoint("TOPLEFT", child, "TOPLEFT", PAD, -120)
    DET.note:SetWidth(DETAIL_W - 2 * PAD - 8)
    DET.note:SetWordWrap(true)
    DET.note:SetText(L["左侧输入关键词，点任意一条结果查看详情与位置"])
end

local REQ_GEN = 0

function QS.Request()
    REQ_GEN = REQ_GEN + 1
    local gen = REQ_GEN
    if _G.C_Timer and _G.C_Timer.After then
        _G.C_Timer.After(0.16, function()
            if gen ~= REQ_GEN then return end
            QS.Apply()
            QS.PaintList()
        end)
    else
        QS.Apply()
        QS.PaintList()
    end
end

function QS.Apply()
    local text = QS.text or ""
    if text == QS.lastQuery then return end
    QS.lastQuery = text
    NCACHE = {}
    TAG_CACHE = {}
    RefreshStatus()
    if #text == 0 then
        ResetRes()
    else
        QS.DoSearch(text)
    end
    QS.sel = nil
    if QS.kind == "object" or COUNT[QS.kind] == 0 then
        QS.kind = "quest"
        for _, k in ipairs(TAB_KINDS) do
            if COUNT[k] > 0 then
                QS.kind = k
                break
            end
        end
    end
    if QS.tab then QS.tab.paint(QS.kind or "quest") end
end

function QS.ListNote()
    if QS.emptyNote then return QS.emptyNote end
    local note = MakeFS(QS.listScroll, 14, C_SUB, "CENTER")
    note:SetWordWrap(true)
    note:SetWidth(LIST_W - 2 * PAD - 30)
    note:SetPoint("TOP", QS.listScroll, "TOP", 0, -50)
    note:SetJustifyH("CENTER")
    QS.emptyNote = note
    return note
end

function QS.PaintList()
    if not QS.listCard then return end
    local kind = QS.kind or "quest"
    local total = COUNT[kind] or 0
    local text = QS.text or ""
    local ready = QS.SearchState() == "ready"

    if #text == 0 or not ready then
        QS.listHead:SetText(L["搜索"])
    else
        QS.listHead:SetText(KindText(kind) .. " · " .. string.format(L["共 %d 条结果"], total))
    end

    local ids = RES[kind] or {}
    local shown = math.min(#ids, MAX_ROWS)
    if #text == 0 or shown == 0 then
        HiddenFrom(ROWS, 1)
        local note = QS.ListNote()
        if #text == 0 then
            note:SetText(L["输入任务、NPC 或物品的名称或编号开始搜索"])
        elseif not ready then
            note:SetText(L["正在准备任务数据…"])
        else
            note:SetText(L["没有符合条件的条目"])
        end
        note:Show()
        QS.listChild:SetHeight(1)
        QS.listScroll:SetVerticalScroll(0)
        QS.SyncScrollBar()
        return
    end

    if QS.emptyNote then QS.emptyNote:Hide() end
    local rowW = QS.listScroll:GetWidth() or (LIST_W - 2 * PAD - 10)
    for i = 1, shown do
        local r = ROWS[i]
        if not r then
            r = MakeRow(QS.listChild)
            ROWS[i] = r
        end
        local rec = { id = ids[i], kind = kind }
        r:SetSize(rowW, ROW_H)
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", QS.listChild, "TOPLEFT", 0, -((i - 1) * (ROW_H + ROW_GAP)))
        RowPaint(r, rec, QS.sel and QS.sel.id == rec.id and QS.sel.kind == rec.kind)
        r:Show()
    end
    HiddenFrom(ROWS, shown + 1)
    QS.listChild:SetHeight(math.max(1, shown * (ROW_H + ROW_GAP) - ROW_GAP))
    QS.SyncScrollBar()
end

function QS.Build(parent)
    if QS.page then return QS.page end
    local page = CreateFrame("Frame", nil, parent)
    page:SetAllPoints(parent)
    QS.page = page
    QS.text = ""
    QS.lastQuery = nil
    QS.kind = "quest"
    QS.sel = nil
    ResetRes()
    BuildSearchCard(page)
    BuildListCard(page)
    BuildDetailCard(page)
    if QS.tab then QS.tab.paint(QS.kind or "quest") end
    page:SetScript("OnShow", function()
        RefreshStatus()
        QS.Apply()
        QS.PaintList()
        QS.PaintDetail()
    end)
    return page
end

function QS.Open()
    if not QS.page then return end
    if not QS.page:IsShown() then QS.page:Show() end
    RefreshStatus()
    QS.Apply()
    QS.PaintList()
    QS.PaintDetail()
end

function QS.Refresh()
    if not QS.page then return end
    RefreshStatus()
    QS.Apply()
    QS.PaintList()
    if QS.sel then QS.PaintDetail() end
end
