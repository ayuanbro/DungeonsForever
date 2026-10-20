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
local MakeOutline = Host.MakeOutline
local C_GOLD, C_GREEN = Host.C_GOLD, Host.C_GREEN
local C_GREY, C_DIM, C_TEXT, C_WHITE = Host.C_GREY, Host.C_DIM, Host.C_TEXT, Host.C_WHITE
local C_DARKGREY = { 0.30, 0.30, 0.30 }
local AddBtnIcon = Host.AddBtnIcon
local Unpack = Host.Unpack

local CQ = ns.ClassQuestUI or {}
ns.ClassQuestUI = CQ

local LIST_W = 300
local GAP = 8
local HEAD_H = 26
local ROW_H = 22
local TOP_Y = 0
local PAD = 8
local FB_H = 24
local FB_GAP = 8
local DET_X = 0
local DET_FS = 14
local HEAD_MAX = 64
local ROW_MAX = 220
local LAB_MAX = 40
local KV_MAX = 60
local TXT_MAX = 24
local NODE_MAX = 40
local CHIP_MAX = 40
local NPC_MAX = 16
local ROW_IND = 20

local C_DONE = { 0.25, 0.85, 0.35 }
local C_ACT = { 1.00, 0.82, 0.00 }
local C_TODO = { 0.58, 0.60, 0.63 }

local DOT_DONE = "Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc"
local DOT_SYM = {
    done = "Interface\\AddOns\\DungeonsForever\\Media\\CheckMark",
    active = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkAsk",
    todo = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkExcl",
}
local DOT_INK = {
    done = { 0.043, 0.239, 0.102 },
    active = { 0.227, 0.165, 0 },
    todo = { 0.102, 0.102, 0.102 },
}

local RACE_ZH = {
    [1] = "人类", [2] = "兽人", [3] = "矮人", [4] = "暗夜精灵",
    [5] = "亡灵", [6] = "牛头人", [7] = "侏儒", [8] = "巨魔",
    [9] = "地精", [10] = "血精灵", [11] = "德莱尼",
    [95] = "天裔", [96] = "天裔",
}

local FAC_TEX = {
    A = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    H = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}

local RACE_FAC = {
    [1] = "A", [3] = "A", [4] = "A", [7] = "A", [11] = "A",
    [2] = "H", [5] = "H", [6] = "H", [8] = "H", [9] = "H", [10] = "H",
}

local function StatusColor(st)
    if st == "done" then return C_DONE end
    if st == "active" then return C_ACT end
    return C_TODO
end

local function DetW()
    local full = TT.FULL_W or 748
    return full - LIST_W - GAP
end

local function ViewW() return LIST_W - PAD * 2 end
local function RowW() return ViewW() end
local function DetInnerW() return DetW() - PAD * 2 end
local function DetRowW() return DetInnerW() end

local function Fnt(size)
    local base = ns.FONT or "Fonts\\FRIZQT__.TTF"
    local flags = "OUTLINE"
    if ns.hui and ns.hui.FontFlags then flags = ns.hui.FontFlags("OUTLINE") end
    return base, size, flags
end

local function StepIDs(chain)
    local out = {}
    local function walk(s)
        if type(s) == "table" then
            for i = 1, #s do walk(s[i]) end
        elseif type(s) == "number" then
            out[#out + 1] = s
        end
    end
    walk(chain.steps)
    return out
end

local function Info(id)
    local t = ns.ClassQuestInfo
    return t and t[id] or nil
end

local function LvTxt(v)
    if not (v and v > 0) then return "" end
    return (format(L["%d 级"], v):gsub("%s+", ""))
end

local function QName(id)
    local q = Info(id)
    if not q then return format(L["任务 #%d"], id), false end
    local n = q.cn or q.n
    if n and n ~= "" then return n, (q.cn ~= nil) end
    return format(L["任务 #%d"], id), false
end

local function StartPts(q)
    local s = q.s
    if type(s) ~= "table" then return {} end
    if type(s[1]) == "table" then return s end
    return { s }
end

local function EndPt(q)
    local e = q.e
    if type(e) ~= "table" then return nil end
    if type(e[1]) == "table" then return e[1] end
    return e
end

local function ChainSide(chain)
    if chain.faction == "A" or chain.faction == "H" then return chain.faction end
    local a, h = false, false
    for _, id in ipairs(StepIDs(chain)) do
        local q = Info(id)
        if q then
            if q.f == "A" then a = true elseif q.f == "H" then h = true end
        end
    end
    if a and not h then return "A" end
    if h and not a then return "H" end
    if not (a or h) then
        local rs = chain.races
        if type(rs) == "table" and #rs > 0 then
            local ra, rh = false, false
            for i = 1, #rs do
                local f = RACE_FAC[rs[i]]
                if f == "A" then ra = true elseif f == "H" then rh = true end
            end
            if ra and not rh then return "A" end
            if rh and not ra then return "H" end
        end
    end
    return nil
end

local function ChainLevel(ids)
    local lv
    for _, id in ipairs(ids) do
        local q = Info(id)
        if q then
            local r = q.r or 0
            if r > 0 and (not lv or r < lv) then lv = r end
        end
    end
    return lv or 0
end

local function AnyActive(ids)
    for _, id in ipairs(ids) do
        if DG.QuestActive(id) then return true end
    end
    return false
end

local function AnyDone(ids)
    local n = 0
    for _, id in ipairs(ids) do
        if DG.QuestDone(id) then n = n + 1 end
    end
    return n
end

local function Build()
    local cls = CQ.cls
    local all = ns.ClassQuestChains and ns.ClassQuestChains[cls]
    if not all then return {} end
    local list = {}
    local raceSeen = {}
    for i = 1, #all do
        local c = all[i]
        local ids = StepIDs(c)
        if #ids > 0 then
            local cs = ChainSide(c)
            local rs = c.races
            if type(rs) == "table" then
                for k = 1, #rs do
                    if RACE_ZH[rs[k]] then raceSeen[rs[k]] = true end
                end
            end
            list[#list + 1] = {
                key = c.key or tostring(i),
                t = c.t or "",
                ids = ids,
                lv = ChainLevel(ids),
                side = cs,
                races = rs,
                group = c.group,
                note = c.note,
                spell = c.spell,
                order = i,
            }
        end
    end
    local opts = {}
    for id in pairs(raceSeen) do opts[#opts + 1] = id end
    table.sort(opts)
    CQ.raceOpts = opts
    table.sort(list, function(a, b)
        if a.lv ~= b.lv then return a.lv < b.lv end
        return a.order < b.order
    end)
    local gcount = {}
    for i = 1, #list do
        local g = list[i].group
        if g then gcount[g] = (gcount[g] or 0) + 1 end
    end
    for i = 1, #list do
        local r = list[i]
        if r.group and (gcount[r.group] or 0) > 1 then
            local q = Info(r.ids[1])
            local pts = q and StartPts(q) or {}
            local zone = pts[1] and pts[1][3] or nil
            if zone and zone ~= "" then
                r.t = r.t .. " · " .. zone
            end
        end
    end
    for i = 1, #list do
        list[i].n = i
        list[i].next = list[i + 1]
    end
    return list
end

local function RowState(r)
    local doneN = AnyDone(r.ids)
    if doneN >= #r.ids then return "done" end
    if doneN > 0 or AnyActive(r.ids) then return "active" end
    return "todo"
end

local function ApplyFilter(list)
    local f = CQ.filter
    local sd = CQ.side
    local rc = CQ.race
    local any = (f and f ~= "all") or (sd and sd ~= "all") or rc
    if not any then return list end
    local out = {}
    for i = 1, #list do
        local r = list[i]
        local keep = true
        if f and f ~= "all" and RowState(r) ~= f then keep = false end
        if keep and sd and sd ~= "all" and r.side and r.side ~= sd then keep = false end
        if keep and rc then
            local rs = r.races
            if type(rs) == "table" and #rs > 0 then
                local hit = false
                local rn = RACE_ZH[rc]
                for k = 1, #rs do
                    if rs[k] == rc or (rn and RACE_ZH[rs[k]] == rn) then hit = true break end
                end
                if not hit then keep = false end
            end
        end
        if keep then out[#out + 1] = r end
    end
    return out
end

local function StateLabel(k)
    if k == "todo" then return L["未接取"] end
    if k == "active" then return L["已接取"] end
    if k == "done" then return L["任务完成"] end
    return L["全部任务"]
end

local function SideLabel(k)
    if k == "A" then return L["联盟"] end
    if k == "H" then return L["部落"] end
    return L["全部阵营"]
end

local function RaceLabel(id)
    if not id then return L["全部种族"] end
    return RACE_ZH[id] or (L["种族"] .. tostring(id))
end

local function OwnInfo()
    if CQ.own then return CQ.own end
    local side
    if DG.PlayerSide then side = DG.PlayerSide() end
    local rid
    if UnitRace then
        local _, _, r = UnitRace("player")
        rid = r
    end
    CQ.own = { side = side, race = rid }
    return CQ.own
end

local function InitFilter()
    if CQ.inited then return end
    CQ.inited = true
    local own = OwnInfo()
    CQ.filter = "all"
    CQ.side = own.side or "all"
    CQ.raceAuto = true
end

local function AutoRace()
    if not CQ.raceAuto then return end
    local own = OwnInfo()
    CQ.race = nil
    if not own.race then return end
    for _, id in ipairs(CQ.raceOpts or {}) do
        if id == own.race then
            CQ.race = own.race
            return
        end
    end
end

local function Ensure()
    local child = TT.child
    if not child then return false end
    if CQ.built and CQ.host == child then return true end
    CQ.host = child
    CQ.built = true

    local page = TT.page

    local function plate()
        local f = CreateFrame("Frame", nil, page, "BackdropTemplate")
        f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                        edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        if not (ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(f, nil, 2)) then
            f:SetBackdropColor(1, 1, 1, 0.04)
            f:SetBackdropBorderColor(1, 1, 1, 0.07)
        end
        f:Hide()
        return f
    end
    CQ.cardL, CQ.cardR = plate(), plate()

    local fb = CreateFrame("Frame", nil, page)
    fb:SetHeight(FB_H)
    fb:Hide()
    CQ.fbar = fb

    local bw = math.floor((ViewW() - GAP * 2) / 3)
    local wArr = { bw, bw, ViewW() - bw * 2 - GAP * 2 }
    local function dropBtn(i, onMenu)
        local bt = NewButton(fb, "", wArr[i], FB_H, 14)
        if i == 1 then
            bt:SetPoint("TOPLEFT", fb, "TOPLEFT", 0, 0)
        else
            bt:SetPoint("LEFT", CQ.dropBtns[i - 1], "RIGHT", GAP, 0)
        end
        bt:SetScript("OnClick", function() onMenu(bt) end)
        CQ.dropBtns[i] = bt
        return bt
    end
    CQ.dropBtns = {}

    local function pick(kind, value)
        if kind == "race" then CQ.raceAuto = false end
        CQ[kind] = value
        CQ.ToTop()
        TT.RequestRender()
        ns.PlaySound(1)
    end

    dropBtn(1, function(bt)
        local items = {}
        local defs = {
            { key = "all", text = L["全部任务"] },
            { key = "todo", text = L["未接取"] },
            { key = "active", text = L["已接取"] },
            { key = "done", text = L["任务完成"] },
        }
        for _, d in ipairs(defs) do
            local dk = d.key
            items[#items + 1] = { text = d.text, func = function() pick("filter", dk) end }
        end
        if ns.hui and ns.hui.ShowMenu then ns.hui.ShowMenu(items, { owner = bt }) end
    end)

    dropBtn(2, function(bt)
        local items = {
            { text = L["全部阵营"], func = function() pick("side", "all") end },
            { text = L["联盟"], icon = FAC_TEX.A, color = DG.C_FAC_A, func = function() pick("side", "A") end },
            { text = L["部落"], icon = FAC_TEX.H, color = DG.C_FAC_H, func = function() pick("side", "H") end },
        }
        if ns.hui and ns.hui.ShowMenu then ns.hui.ShowMenu(items, { owner = bt }) end
    end)

    local sbt = CQ.dropBtns[2]
    if sbt then
        local fs = sbt:GetFontString()
        if fs then
            fs:ClearAllPoints()
            fs:SetPoint("TOPLEFT", sbt, "TOPLEFT", 0, 0)
            fs:SetPoint("BOTTOMRIGHT", sbt, "BOTTOMRIGHT", -2, 0)
            fs:SetJustifyH("CENTER")
        end
        local ic = sbt:CreateTexture(nil, "OVERLAY")
        ic:SetSize(16, 16)
        ic:SetPoint("RIGHT", sbt, "CENTER", 0, 0)
        ic:Hide()
        CQ.sideIcon = ic
    end

    dropBtn(3, function(bt)
        local items = { { text = L["全部种族"], func = function() pick("race", nil) end } }
        local seen = {}
        for _, id in ipairs(CQ.raceOpts or {}) do
            local rid = id
            local nm = RACE_ZH[rid] or (L["种族"] .. tostring(rid))
            if not seen[nm] then
                seen[nm] = true
                items[#items + 1] = {
                    text = nm,
                    func = function() pick("race", rid) end,
                }
            end
        end
        if ns.hui and ns.hui.ShowMenu then ns.hui.ShowMenu(items, { owner = bt }) end
    end)

    local ds = CreateFrame("ScrollFrame", nil, page)
    ds:EnableMouseWheel(true)
    ds:Hide()
    local dc = CreateFrame("Frame", nil, ds)
    dc:SetSize(DetInnerW(), 10)
    if ds.SetScrollChild then ds:SetScrollChild(dc) end
    ds:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(ds, dc, delta)
        CQ.UpdateDBar()
    end)
    ds:SetScript("OnVerticalScroll", function() CQ.UpdateDBar() end)
    CQ.dscroll, CQ.dchild = ds, dc
    CQ.dv = 0

    local dtrack = CreateFrame("Frame", nil, page)
    dtrack:SetWidth(7)
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(dtrack, 3, ns.hui.layer.L2)
    else
        dtrack:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                             edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        dtrack:SetBackdropColor(0, 0, 0, 0.25)
        dtrack:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    dtrack:Hide()
    local dthumb = CreateFrame("Button", nil, dtrack)
    dthumb:SetWidth(5)
    dthumb:EnableMouse(true)
    if ns.hui and ns.hui.BuildCapsule then
        local L4, L5 = ns.hui.layer.L4, ns.hui.layer.L5
        local tp = ns.hui.BuildCapsule(dthumb, 2, L4)
        local th = ns.hui.BuildCapsule(dthumb, 2, L5)
        for _, t in ipairs(th) do t:Hide() end
        dthumb:SetScript("OnEnter", function()
            for _, t in ipairs(tp) do t:Hide() end
            for _, t in ipairs(th) do t:Show() end
        end)
        dthumb:SetScript("OnLeave", function()
            for _, t in ipairs(th) do t:Hide() end
            for _, t in ipairs(tp) do t:Show() end
        end)
    else
        local tx = dthumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
    end
    dthumb:SetPoint("TOP", dtrack, "TOP", 0, -1)
    dthumb:Hide()
    dthumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = ds:GetVerticalScroll() or 0
        self:SetScript("OnUpdate", function()
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = dtrack:GetHeight() - 2
            local span = trackH - dthumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = math.max(0, dc:GetHeight() - ds:GetHeight())
            ds:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
            CQ.UpdateDBar()
        end)
    end)
    dthumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    dthumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    CQ.dtrack, CQ.dthumb = dtrack, dthumb

    CQ.heads = {}
    for i = 1, HEAD_MAX do
        local fr = CreateFrame("Button", nil, child)
        fr:SetSize(RowW(), HEAD_H)
        fr:RegisterForClicks("LeftButtonUp")
        if ns.hui and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(fr, 5, 3)
        end
        fr.arrow = MakeFS(fr, 14, C_DIM, "CENTER")
        fr.arrow:SetPoint("LEFT", fr, "LEFT", 9, 0)
        fr.arrow:SetWidth(10)
        fr.dot = fr:CreateTexture(nil, "ARTWORK")
        fr.dot:SetTexture(DOT_DONE)
        fr.dot:SetSize(10, 10)
        fr.dot:SetPoint("LEFT", fr, "LEFT", 21, 0)
        fr.sym = fr:CreateTexture(nil, "OVERLAY")
        fr.sym:SetAllPoints(fr.dot)
        fr.name = MakeFS(fr, 14, C_TEXT, "LEFT")
        fr.name:SetPoint("LEFT", fr, "LEFT", 34, 0)
        fr.name:SetWordWrap(false)
        fr.meta = MakeFS(fr, 14, C_GREY, "RIGHT")
        fr.meta:SetPoint("RIGHT", fr, "RIGHT", -6, 0)
        fr.meta:SetWordWrap(false)
        fr.lv = MakeFS(fr, 14, C_DIM, "RIGHT")
        fr.lv:SetPoint("RIGHT", fr.meta, "LEFT", -10, 0)
        fr.lv:SetWordWrap(false)
        fr:SetScript("OnEnter", function(self)
            if not self.__sel and ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
        end)
        fr:SetScript("OnLeave", function(self)
            if not self.__sel and ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        end)
        fr:SetScript("OnClick", function(self)
            if self.__act then self.__act() end
        end)
        fr:Hide()
        CQ.heads[i] = fr
    end

    CQ.rows = {}
    for i = 1, ROW_MAX do
        local fr = CreateFrame("Button", nil, child)
        fr:SetSize(RowW() - ROW_IND, ROW_H)
        fr:RegisterForClicks("LeftButtonUp")
        if ns.hui and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(fr, 5, 3)
        end
        fr.dot = fr:CreateTexture(nil, "ARTWORK")
        fr.dot:SetTexture(DOT_DONE)
        fr.dot:SetSize(8, 8)
        fr.dot:SetPoint("LEFT", fr, "LEFT", 17, 0)
        fr.sym = fr:CreateTexture(nil, "OVERLAY")
        fr.sym:SetAllPoints(fr.dot)
        fr.name = MakeFS(fr, 14, C_TEXT, "LEFT")
        fr.name:SetPoint("LEFT", fr, "LEFT", 30, 0)
        fr.name:SetWordWrap(false)
        fr.lv = MakeFS(fr, 14, C_DIM, "RIGHT")
        fr.lv:SetPoint("RIGHT", fr, "RIGHT", -6, 0)
        fr:SetScript("OnEnter", function(self)
            if not self.__sel and ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
        end)
        fr:SetScript("OnLeave", function(self)
            if not self.__sel and ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        end)
        fr:SetScript("OnClick", function(self)
            if self.__act then self.__act() end
        end)
        fr:Hide()
        CQ.rows[i] = fr
    end

    local detW = DetRowW()
    CQ.det = { lab = {}, kv = {}, txt = {}, node = {}, chip = {}, npc = {} }

    CQ.title = MakeFS(CQ.dchild, 16, C_GOLD, "LEFT")
    CQ.title:SetWordWrap(false)
    CQ.title:SetWidth(detW - 8)
    CQ.sub = MakeFS(CQ.dchild, DET_FS, C_GREY, "LEFT")
    CQ.sub:SetWordWrap(false)
    CQ.sub:SetWidth(detW - 4)
    return true
end

local function Hui(on, fr, st)
    if not (ns.hui and ns.hui.HuiCardState) then return end
    ns.hui.HuiCardState(fr, on and "hover" or (st or "norm"))
end

local function ResetRows()
    CQ.nHead, CQ.nRow = 0, 0
    for i = 1, HEAD_MAX do if CQ.heads[i] then CQ.heads[i]:Hide() end end
    for i = 1, ROW_MAX do if CQ.rows[i] then CQ.rows[i]:Hide() end end
end

local function TakeHead()
    CQ.nHead = CQ.nHead + 1
    local fr = CQ.heads[CQ.nHead]
    if fr then
        fr.arrow:Show()
        fr.dot:Show()
        fr.sym:Show()
        fr.name:Show()
        fr.meta:Show()
        fr.lv:Show()
    end
    return fr
end

local function TakeRow()
    CQ.nRow = CQ.nRow + 1
    local fr = CQ.rows[CQ.nRow]
    if fr then
        fr.dot:Show()
        fr.sym:Show()
        fr.name:Show()
        fr.lv:Show()
    end
    return fr
end

local function PutDot(tex, sym, st)
    local col = StatusColor(st)
    tex:SetVertexColor(col[1], col[2], col[3], 1)
    sym:SetTexture(DOT_SYM[st] or DOT_SYM.todo)
    local ink = DOT_INK[st] or DOT_INK.todo
    sym:SetVertexColor(ink[1], ink[2], ink[3], 1)
end

local function RowMark(r, st, col)
    if not (r and r.ic) then return end
    if st and col then
        r.ic:SetVertexColor(col[1], col[2], col[3], 1)
        r.icT:SetTexture(DOT_SYM[st] or DOT_SYM.todo)
        local ink = DOT_INK[st] or DOT_INK.todo
        r.icT:SetVertexColor(ink[1], ink[2], ink[3], 1)
        r.ic:Show()
        r.icT:Show()
    else
        r.ic:Hide()
        r.icT:Hide()
    end
end

local function DetReset()
    local pool = CQ.det
    pool.nLab, pool.nKv, pool.nTxt, pool.nNode, pool.nChip, pool.nNpc = 0, 0, 0, 0, 0, 0
    for i = 1, #pool.lab do pool.lab[i]:Hide() end
    for i = 1, #pool.kv do pool.kv[i]:Hide() end
    for i = 1, #pool.txt do pool.txt[i]:Hide() end
    for i = 1, #pool.node do pool.node[i]:Hide() end
    for i = 1, #pool.chip do pool.chip[i]:Hide() end
    for i = 1, #pool.npc do pool.npc[i]:Hide() end
end

local function TakeLab()
    local pool = CQ.det
    pool.nLab = pool.nLab + 1
    local f = pool.lab[pool.nLab]
    if not f then
        if pool.nLab > LAB_MAX then return nil end
        f = MakeFS(CQ.dchild, DET_FS, C_GREY, "LEFT")
        pool.lab[pool.nLab] = f
    end
    return f
end

local function TakeKv(wrapH)
    local pool = CQ.det
    pool.nKv = pool.nKv + 1
    local f = pool.kv[pool.nKv]
    if not f then
        if pool.nKv > KV_MAX then return nil end
        f = MakeFS(CQ.dchild, DET_FS, C_TEXT, "LEFT")
        pool.kv[pool.nKv] = f
    end
    f:SetWidth(DetRowW() - 8)
    if wrapH then f:SetWordWrap(true) else f:SetWordWrap(false) end
    return f
end

local function TakeTxt()
    local pool = CQ.det
    pool.nTxt = pool.nTxt + 1
    local f = pool.txt[pool.nTxt]
    if not f then
        if pool.nTxt > TXT_MAX then return nil end
        f = MakeFS(CQ.dchild, DET_FS, C_TEXT, "LEFT")
        pool.txt[pool.nTxt] = f
    end
    f:SetWidth(DetRowW() - 8)
    f:SetWordWrap(true)
    return f
end

local function TakeNode()
    local pool = CQ.det
    pool.nNode = pool.nNode + 1
    local r = pool.node[pool.nNode]
    if not r then
        if pool.nNode > NODE_MAX then return nil end
        r = CreateFrame("Button", nil, CQ.dchild, "BackdropTemplate")
        r:SetSize(DetRowW(), 38)
        r:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        if ns.hui and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(r, 5, 3)
        else
            r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG or 0.04)
            r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE or 0.10)
        end
        r.name = MakeFS(r, DET_FS, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -3)
        r.name:SetWidth(DetRowW() - 126)
        r.name:SetWordWrap(false)
        r.st = MakeFS(r, DET_FS, C_GREY, "RIGHT")
        r.st:SetPoint("TOPRIGHT", r, "TOPRIGHT", -26, -3)
        r.st:SetWordWrap(false)
        r.sub = MakeFS(r, DET_FS, C_GREY, "LEFT")
        r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -21)
        r.sub:SetWidth(DetRowW() - 18)
        r.sub:SetWordWrap(false)
        r.ic = r:CreateTexture(nil, "ARTWORK")
        r.ic:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        r.ic:SetSize(DG.Q_BADGE_H, DG.Q_BADGE_H)
        r.ic:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -4)
        r.ic:Hide()
        r.icT = r:CreateTexture(nil, "OVERLAY")
        r.icT:SetAllPoints(r.ic)
        r.icT:Hide()
        r:SetScript("OnEnter", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
        end)
        r:SetScript("OnLeave", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        end)
        r:SetScript("OnClick", function(self)
            if self.__act then self.__act() end
        end)
        pool.node[pool.nNode] = r
    end
    return r
end

local function SkillTip(owner, sid)
    if type(sid) ~= "number" then return end
    local GT = GameTooltip
    GT:SetOwner(owner, "ANCHOR_RIGHT")
    local shown = false
    if type(GT.SetSpellByID) == "function" then
        local ok = pcall(GT.SetSpellByID, GT, sid)
        local n = 0
        if type(GT.NumLines) == "function" then
            local ok2, v = pcall(GT.NumLines, GT)
            if ok2 and type(v) == "number" then n = v end
        end
        shown = ok and n > 0
    end
    if not shown then
        local nm
        if C_Spell and C_Spell.GetSpellName then
            local ok, v = pcall(C_Spell.GetSpellName, sid)
            if ok and type(v) == "string" and v ~= "" then nm = v end
        end
        GT:SetText(nm or format("#%d", sid), 1, 1, 1, 1, true)
        GT:AddLine(L["技能"], 0.6, 0.6, 0.6)
    end
    GT:Show()
end

local function TakeChip()
    local pool = CQ.det
    pool.nChip = pool.nChip + 1
    local r = pool.chip[pool.nChip]
    if not r then
        if pool.nChip > CHIP_MAX then return nil end
        r = CreateFrame("Button", nil, CQ.dchild)
        r:SetSize(DetRowW(), 44)
        r:EnableMouse(true)
        if ns.hui and ns.hui.HuiCardFX then ns.hui.HuiCardFX(r, 12, 3) end
        r:SetScript("OnEnter", function(self)
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
            if self.__it then
                if DG.ShowItemTip then DG.ShowItemTip(self, self.__it) end
            elseif self.__spell then
                SkillTip(self, self.__spell)
            end
        end)
        r:SetScript("OnLeave", function(self)
            GameTooltip:Hide()
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        end)
        r:SetScript("OnClick", function(self, button)
            if DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
        end)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.icon:SetSize(32, 32)
        r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.name = MakeFS(r, DET_FS, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 43, -4)
        r.name:SetWordWrap(false)
        r.sub = MakeFS(r, DET_FS, C_GREY, "LEFT")
        r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 43, -23)
        r.sub:SetWordWrap(false)
        pool.chip[pool.nChip] = r
    end
    return r
end

local function TakeNpc()
    local pool = CQ.det
    pool.nNpc = pool.nNpc + 1
    local f = pool.npc[pool.nNpc]
    if not f then
        if pool.nNpc > NPC_MAX then return nil end
        f = CreateFrame("Button", nil, CQ.dchild)
        f:SetSize(DetRowW(), 24)
        f:EnableMouse(true)
        f.fs = MakeFS(f, DET_FS, C_TEXT, "LEFT")
        f.fs:SetPoint("TOPLEFT", f, "TOPLEFT", 0, 0)
        f.fs:SetWordWrap(false)
        f.fs:SetWidth(DetRowW() - 76)
        local mb = NewButton(f, L["地图"], 62, 20, DET_FS)
        if AddBtnIcon then AddBtnIcon(mb, "EntryPin", 12, 4) end
        MakeOutline(mb, 1, 0.82, 0)
        if TT.RoundButtonFill then TT.RoundButtonFill(mb) end
        mb.__huiKeepTextColor = true
        mb:SetPoint("RIGHT", f.fs, "RIGHT", 74, 0)
        mb:SetScript("OnClick", function(self)
            local p = self:GetParent()
            if p.__npc and DG.MarkNPC then DG.MarkNPC(p.__npc, p.__loc) end
        end)
        mb:SetScript("OnEnter", function(self)
            local p = self:GetParent()
            if p.__npc and DG.ShowNpcTip then DG.ShowNpcTip(self, p.__npc, p.__loc) end
        end)
        mb:SetScript("OnLeave", function() GameTooltip:Hide() end)
        f.mark = mb
        pool.npc[pool.nNpc] = f
    end
    return f
end

local renderChain, renderQuest

local function putDet(fr, x, y, h)
    if not fr then return y end
    fr:ClearAllPoints()
    fr:SetPoint("TOPLEFT", CQ.dchild, "TOPLEFT", x, y)
    fr:Show()
    return y - h
end

local function DetHead(subTxt)
    CQ.title:ClearAllPoints()
    CQ.title:SetPoint("TOPLEFT", CQ.dchild, "TOPLEFT", DET_X, -(TOP_Y + 8))
    CQ.title:Show()
    CQ.sub:ClearAllPoints()
    CQ.sub:SetPoint("TOPLEFT", CQ.dchild, "TOPLEFT", DET_X, -(TOP_Y + 34))
    if subTxt and subTxt ~= "" then
        CQ.sub:SetText(subTxt)
        CQ.sub:Show()
    else
        CQ.sub:Hide()
    end
    return -(TOP_Y + 56)
end

local function AddLine(y, text, color, h)
    local f = TakeKv()
    if not f then return y end
    f:SetText(text)
    f:SetTextColor(Unpack(color or C_TEXT))
    return putDet(f, DET_X, y, h or 20)
end

local function AddNpc(y, label, name, npcID, loc, zone, x, yy)
    local f = TakeNpc()
    if not f then return y end
    local txt = DG.Hex(C_GREY) .. label .. "|r"
    if name and name ~= "" then
        txt = txt .. DG.Hex(C_GOLD) .. name .. "|r"
        if npcID then txt = txt .. format(" |cff9a9a9a#%d|r", npcID) end
    elseif npcID then
        txt = txt .. format("|cff9a9a9a#%d|r", npcID)
    end
    if zone and zone ~= "" then
        txt = txt .. " · " .. zone
        if x and yy then txt = txt .. format(" %.1f,%.1f", x, yy) end
    end
    f.fs:SetText(txt)
    f.fs:SetWidth(DetRowW() - 76)
    f.__npc = npcID
    f.__loc = loc
    if f.mark then
        if loc then f.mark:Show() else f.mark:Hide() end
    end
    return putDet(f, DET_X, y, 24)
end

local function SpellName(id)
    if type(id) ~= "number" then return nil end
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

local function ItemQual(iid)
    local q = DG.QualOf and DG.QualOf(iid)
    if type(q) == "number" and q >= 0 then return q end
    if C_Item and type(C_Item.GetItemInfo) == "function" then
        local ok, _, _, v = pcall(C_Item.GetItemInfo, iid)
        if ok and type(v) == "number" then return v end
    end
    if type(GetItemInfo) == "function" then
        local ok, _, _, v = pcall(GetItemInfo, iid)
        if ok and type(v) == "number" then return v end
    end
    return nil
end

local function ChipRow(y, items, spell)
    local detW = DetRowW()
    local ncol = 2
    local colW = math.floor((detW - GAP) / ncol)
    local step = 44 + GAP
    local nameW = colW - 43 - 6
    local n = 0
    local function place(r)
        n = n + 1
        r:SetSize(colW, 44)
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", CQ.dchild, "TOPLEFT",
            DET_X + (n - 1) % ncol * (colW + GAP),
            y - math.floor((n - 1) / ncol) * step)
        r:Show()
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "norm") end
    end
    if spell then
        local r = TakeChip()
        if r then
            r.__q, r.__it, r.__spell = nil, nil, spell
            local tex
            if C_Spell and C_Spell.GetSpellTexture then
                local ok, v = pcall(C_Spell.GetSpellTexture, spell)
                if ok and v then tex = v end
            end
            r.icon:SetTexture(tex or "Interface\\Icons\\INV_Misc_QuestionMark")
            local sn = SpellName(spell) or format("#%d", spell)
            if DG.FitText then sn = DG.FitText(sn, DET_FS, nameW) end
            r.name:SetText(sn)
            r.name:SetTextColor(Unpack(C_GOLD))
            r.name:SetWidth(nameW)
            r.sub:SetText(L["技能"])
            r.sub:Show()
            place(r)
        end
    end
    for _, iid in ipairs(items) do
        local r = TakeChip()
        if not r then break end
        r.__q = nil
        r.__spell = nil
        r.__it = { iid }
        r.icon:SetTexture(DG.ItemIcon(iid))
        local inm, iok = DG.ItemName(iid)
        if not iok and ns.ClassQuestItemName and ns.ClassQuestItemName[iid] then
            inm, iok = ns.ClassQuestItemName[iid], true
        end
        if DG.FitText then inm = DG.FitText(inm, DET_FS, nameW) end
        r.name:SetText(inm)
        r.name:SetWidth(nameW)
        local qr, qg, qb = DG.QColor(ItemQual(iid))
        if qr then
            r.name:SetTextColor(qr, qg, qb)
        else
            r.name:SetTextColor(Unpack(C_GREY))
        end
        local mt = DG.ItemMeta and DG.ItemMeta(iid) or ""
        r.sub:SetText(mt)
        r.sub:SetShown(mt ~= "")
        place(r)
    end
    for _, iid in ipairs(items) do
        if DG.RequestItem then
            local _, iok = DG.ItemName(iid)
            DG.RequestItem(iid, not iok)
        end
    end
    return y - math.ceil(n / ncol) * step
end

local function ChainTotal(chain)
    local items, seen, spell = {}, {}, nil
    if type(chain.spell) == "number" then spell = chain.spell end
    for _, id in ipairs(chain.ids) do
        local q = Info(id)
        if q then
            if type(q.items) == "table" then
                for _, iid in ipairs(q.items) do
                    if not seen[iid] then
                        seen[iid] = true
                        items[#items + 1] = iid
                    end
                end
            end
            if type(q.spells) == "table" then
                for _, sid in ipairs(q.spells) do
                    if not seen["s" .. sid] then
                        seen["s" .. sid] = true
                        spell = spell or sid
                    end
                end
            end
        end
    end
    return items, spell
end

renderChain = function(row, y)
    DetReset()
    CQ.title:SetText(row.t)
    CQ.title:SetTextColor(Unpack(C_GOLD))
    local sub = format(L["%d 级"], row.lv) .. " · " .. format(L["%d 步"], #row.ids)
    if row.side == "A" then
        sub = sub .. " · " .. DG.Hex(DG.C_FAC_A) .. L["联盟"] .. "|r"
    elseif row.side == "H" then
        sub = sub .. " · " .. DG.Hex(DG.C_FAC_H) .. L["部落"] .. "|r"
    else
        sub = sub .. " · " .. L["双阵营共有"]
    end
    y = DetHead(sub)

    if row.note and row.note ~= "" then
        local f = TakeTxt()
        if f then
            f:SetText(row.note)
            f:SetTextColor(Unpack(C_GREY))
            local h = f:GetStringHeight()
            y = putDet(f, DET_X, y, (type(h) == "number" and h or 18) + 4)
        end
    end

    local lab = TakeLab()
    if lab then
        lab:SetText(L["任务链"])
        lab:SetTextColor(Unpack(C_GREY))
        y = putDet(lab, DET_X, y - 2, 20)
    end

    for idx, id in ipairs(row.ids) do
        local r = TakeNode()
        if not r then break end
        local nm = QName(id)
        local st = DG.QuestState(id)
        local col = (st == "done" and C_GREEN) or (st == "active" and C_GOLD) or C_GREY
        r.name:SetText(format("%d. ", idx) .. nm)
        r.name:SetTextColor(Unpack(nm ~= "" and col or C_GREY))
        r.st:SetText((DG.Q_STATUS_TAG and DG.Q_STATUS_TAG[st]) or "")
        r.st:SetTextColor(Unpack(col))
        RowMark(r, nm ~= "" and st or nil, col)
        local q = Info(id)
        local pts = q and StartPts(q) or {}
        local sub2 = ""
        if pts[1] then
            sub2 = (pts[1][3] or "")
            if pts[1][2] and pts[1][2] ~= "" then
                sub2 = (sub2 ~= "" and (sub2 .. " · ") or "") .. pts[1][2]
            end
        end
        if q and q.r and q.r > 0 then
            sub2 = (sub2 ~= "" and (sub2 .. " · ") or "") .. format(L["%d 级可接"], q.r)
        end
        if sub2 == "" then sub2 = L["本表未收录起始信息"] end
        r.sub:SetText(sub2)
        r.__act = function()
            CQ.sel = { type = "quest", id = id, chain = row }
            TT.RequestRender()
        end
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", CQ.dchild, "TOPLEFT", DET_X, y)
        r:Show()
        y = y - 38
    end

    local items, spell = ChainTotal(row)
    if #items > 0 or spell then
        local l2 = TakeLab()
        if l2 then
            l2:SetText(L["本链总奖励"])
            l2:SetTextColor(Unpack(C_GREY))
            y = putDet(l2, DET_X, y - 2, 20)
        end
        y = ChipRow(y, items, spell)
    end
    return y
end

renderQuest = function(id, y)
    DetReset()
    local q = Info(id)
    local nm, ok = QName(id)
    CQ.title:SetText(nm .. (ok and format(" |cff9a9a9a#%d|r", id) or ""))
    CQ.title:SetTextColor(Unpack(ok and C_GOLD or C_GREY))

    local st = DG.QuestState(id)
    local col = (st == "done" and C_GREEN) or (st == "active" and C_GOLD) or C_GREY
    local sub = L["状态："] .. ((DG.Q_STATUS_TAG and DG.Q_STATUS_TAG[st]) or "")
    CQ.sub:SetTextColor(Unpack(ok and col or C_DARKGREY))
    y = DetHead(sub)

    if not q then
        local f = TakeTxt()
        if f then
            f:SetText(L["本表未收录这个任务的数据"])
            f:SetTextColor(Unpack(C_GREY))
            local h = f:GetStringHeight()
            y = putDet(f, DET_X, y, (type(h) == "number" and h or 18) + 4)
        end
        return y
    end

    if DG.RequestQuestRewardData then pcall(DG.RequestQuestRewardData, id) end

    local row
    if DG.QuestRowByID then
        local rok, rv = pcall(DG.QuestRowByID, id)
        if rok and type(rv) == "table" then row = rv end
    end

    local lvTxt = ""
    if q.r and q.r > 0 then
        lvTxt = DG.Hex(C_GOLD) .. format(L["%d 级可接"], q.r) .. "|r"
    end
    if q.l and q.l > 0 then
        local lc = DG.DifficultyColor(q.l)
        local seg = format(L["任务等级 Lv%s"], tostring(q.l))
        lvTxt = lvTxt .. (lvTxt ~= "" and " · " or "") .. (lc and DG.Hex(lc) .. seg .. "|r" or seg)
    end
    if lvTxt ~= "" then
        y = AddLine(y, DG.Hex(C_GREY) .. L["可接等级"] .. "：|r" .. lvTxt, C_TEXT, 24)
    end

    local diffTxt
    if row and type(row[13]) == "table" and #row[13] > 0 then
        local parts = {}
        for _, dd in ipairs(row[13]) do
            local dc = (DG.Q_DIFF_COLOR and DG.Q_DIFF_COLOR[dd[2]]) or C_GREY
            parts[#parts + 1] = DG.Hex(dc) .. tostring(dd[1]) .. "|r"
        end
        diffTxt = table.concat(parts, "  ")
    elseif C_QuestLog and C_QuestLog.GetQuestTagInfo then
        local tok, tag = pcall(C_QuestLog.GetQuestTagInfo, id)
        local tagn = tok and type(tag) == "table" and (tag.tagName or tag.questTag) or nil
        if tagn and tagn ~= "" then diffTxt = tostring(tagn) end
    end
    if diffTxt then
        y = AddLine(y, DG.Hex(C_GREY) .. L["任务难度"] .. "：|r" .. diffTxt, C_TEXT, 24)
    end

    local pts = StartPts(q)
    if #pts > 0 then
        for i = 1, #pts do
            local p = pts[i]
            local mid = p[6]
            local loc = mid and p[4] and p[5] and { mid, p[4], p[5] } or nil
            y = AddNpc(y, (i == 1) and L["起始："] or "", p[2], p[1], loc, p[3], p[4], p[5])
        end
    elseif q.s then
        y = AddLine(y, DG.Hex(C_GREY) .. L["起始："] .. "|r" .. L["本表未收录起始信息"], C_TEXT, 24)
    end

    local e = EndPt(q)
    if e then
        local mid = e[6]
        local loc = mid and e[4] and e[5] and { mid, e[4], e[5] } or nil
        y = AddNpc(y, L["结束："], e[2], e[1], loc, e[3], e[4], e[5])
    end

    local fac, facCol
    if q.f == "A" then
        fac, facCol = L["联盟专属"], DG.C_FAC_A
    elseif q.f == "H" then
        fac, facCol = L["部落专属"], DG.C_FAC_H
    else
        fac = L["双阵营共有"]
    end
    y = AddLine(y, DG.Hex(C_GREY) .. L["阵营"] .. "：|r"
        .. (facCol and DG.Hex(facCol) or "") .. fac .. (facCol and "|r" or ""), C_TEXT, 24)

    if type(q.races) == "table" and #q.races > 0 then
        local seen, names = {}, {}
        for _, rid in ipairs(q.races) do
            local rn = RACE_ZH[rid]
            if rn and not seen[rn] then
                seen[rn] = true
                names[#names + 1] = rn
            end
        end
        if #names > 0 then
            y = AddLine(y, DG.Hex(C_GREY) .. L["限定种族"] .. "：|r" .. table.concat(names, "、"), C_TEXT, 24)
        end
    end

    local chain = CQ.sel and CQ.sel.chain
    if chain then
        local idx
        for i = 1, #chain.ids do
            if chain.ids[i] == id then idx = i break end
        end
        if idx then
            y = AddLine(y, DG.Hex(C_GREY) .. L["链内进度"] .. "：|r"
                .. format(L["第 %d / %d 步"], idx, #chain.ids)
                .. " · " .. DG.Hex(C_GREY) .. chain.t .. "|r", C_TEXT, 24)
        end
    end
    y = y - 4

    local desc = (DG.QuestDescription and DG.QuestDescription(id)) or (row and row[20]) or q.desc
    if desc and desc ~= "" then
        local lab = TakeLab()
        if lab then
            lab:SetText(L["任务说明"])
            lab:SetTextColor(Unpack(C_GREY))
            y = putDet(lab, DET_X, y, 20)
        end
        local f = TakeTxt()
        if f then
            f:SetText(desc)
            f:SetTextColor(Unpack(C_TEXT))
            local h = f:GetStringHeight()
            y = putDet(f, DET_X, y, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    local note = (row and row[12]) or q.note
    if note and note ~= "" then
        local lab = TakeLab()
        if lab then
            lab:SetText(L["任务注释"])
            lab:SetTextColor(Unpack(C_GREY))
            y = putDet(lab, DET_X, y, 20)
        end
        local f = TakeTxt()
        if f then
            f:SetText(note)
            f:SetTextColor(Unpack(C_TEXT))
            local h = f:GetStringHeight()
            y = putDet(f, DET_X, y, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    local objTxt
    if DG.NeedObjectivesText then
        local ook, v = pcall(DG.NeedObjectivesText, id, nil)
        if ook then objTxt = v end
    end
    if objTxt and objTxt ~= "" then
        local lab = TakeLab()
        if lab then
            lab:SetText(L["任务需求"])
            lab:SetTextColor(Unpack(C_GREY))
            y = putDet(lab, DET_X, y, 20)
        end
        local f = TakeTxt()
        if f then
            f:SetText(objTxt)
            f:SetTextColor(Unpack(C_TEXT))
            local h = f:GetStringHeight()
            y = putDet(f, DET_X, y, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    if type(q.items) == "table" and #q.items > 0 then
        local lab = TakeLab()
        if lab then
            lab:SetText(L["任务奖励"])
            lab:SetTextColor(Unpack(C_GREY))
            y = putDet(lab, DET_X, y, 20)
        end
        y = ChipRow(y, q.items)
    end

    local segs = {}
    if DG.GainsSegs then
        local gok, g = pcall(DG.GainsSegs, { [1] = id })
        if gok and type(g) == "table" then
            for _, gs in ipairs(g) do segs[#segs + 1] = gs end
        end
    end
    if type(q.spells) == "table" then
        for _, sid in ipairs(q.spells) do
            segs[#segs + 1] = L["技能"] .. "：" .. (SpellName(sid) or format("#%d", sid))
        end
    end
    if #segs > 0 then
        local lab = TakeLab()
        if lab then
            lab:SetText(L["收获"])
            lab:SetTextColor(Unpack(C_GREY))
            y = putDet(lab, DET_X, y, 20)
        end
        local f = TakeTxt()
        if f then
            f:SetText(table.concat(segs, " · "))
            f:SetTextColor(Unpack(C_TEXT))
            local h = f:GetStringHeight()
            y = putDet(f, DET_X, y, (type(h) == "number" and h or 18) + 4)
            y = y - 2
        end
    end

    do
        local t = TakeTxt()
        if t then
            t:SetText(L["状态来自你自己的任务日志，交完任务这里会自动变。"])
            t:SetTextColor(Unpack(C_DARKGREY))
            y = putDet(t, DET_X, y, 22)
        end
    end

    return y
end

function CQ.ToTop()
    if TT.scroll then
        TT.scroll:SetVerticalScroll(0)
        TT.__v = 0
    end
    if CQ.dscroll then
        CQ.dscroll:SetVerticalScroll(0)
        CQ.UpdateDBar()
    end
end

function CQ.UpdateDBar()
    local ds, dc, track, thumb = CQ.dscroll, CQ.dchild, CQ.dtrack, CQ.dthumb
    if not (ds and dc and track and thumb) then return end
    local viewH = ds:GetHeight()
    local contentH = dc:GetHeight()
    if (not ds:IsShown()) or viewH <= 0 or contentH <= viewH + 2 then
        track:Hide()
        thumb:Hide()
        return
    end
    track:Show()
    local trackH = track:GetHeight() - 2
    local maxScroll = contentH - viewH
    local v = ds:GetVerticalScroll() or 0
    local frac = math.min(1, math.max(0, v / maxScroll))
    local th = math.max(24, trackH * viewH / contentH)
    thumb:SetHeight(th)
    thumb:ClearAllPoints()
    thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    thumb:Show()
end

local function Layout()
    local page = TT.page
    local scroll, ds = TT.scroll, CQ.dscroll
    if not (page and scroll and ds and CQ.cardL) then return end

    local right = TT.EDGE + TT.INSET
    local top = TT.MODE_TOP
    local bot = TT.EDGE + TT.INSET
    local detW = DetW()

    CQ.cardL:ClearAllPoints()
    CQ.cardL:SetPoint("TOPLEFT", page, "TOPLEFT", TT.RIGHT_X, -top)
    CQ.cardL:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", TT.RIGHT_X + LIST_W, bot)
    CQ.cardR:ClearAllPoints()
    CQ.cardR:SetPoint("TOPRIGHT", page, "TOPRIGHT", -right, -top)
    CQ.cardR:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -right, bot)
    CQ.cardR:SetWidth(detW)

    local sl = scroll:GetFrameLevel()
    if type(sl) ~= "number" then sl = 1 end
    CQ.cardL:SetFrameLevel(sl)
    CQ.cardR:SetFrameLevel(sl)
    CQ.cardL:Show()
    CQ.cardR:Show()

    CQ.fbar:ClearAllPoints()
    CQ.fbar:SetPoint("TOPLEFT", CQ.cardL, "TOPLEFT", PAD, -PAD)
    CQ.fbar:SetWidth(ViewW())
    CQ.fbar:SetFrameLevel(sl + 4)
    CQ.fbar:Show()

    scroll:ClearAllPoints()
    scroll:SetPoint("TOPLEFT", CQ.cardL, "TOPLEFT", PAD, -(PAD + FB_H + FB_GAP))
    scroll:SetPoint("BOTTOMRIGHT", CQ.cardL, "BOTTOMRIGHT", -PAD, PAD)

    ds:ClearAllPoints()
    ds:SetPoint("TOPLEFT", CQ.cardR, "TOPLEFT", PAD, -PAD)
    ds:SetPoint("BOTTOMRIGHT", CQ.cardR, "BOTTOMRIGHT", -PAD, PAD)
    ds:SetFrameLevel(sl + 2)
    ds:Show()

    CQ.dtrack:ClearAllPoints()
    CQ.dtrack:SetPoint("TOPRIGHT", ds, "TOPRIGHT", 7, 0)
    CQ.dtrack:SetPoint("BOTTOMRIGHT", ds, "BOTTOMRIGHT", 7, 0)
    CQ.dtrack:SetFrameLevel(sl + 14)

    local sb = CQ.dropBtns or {}
    local function setLbl(bt, text)
        if not (bt and bt.GetFontString) then return end
        local fs = bt:GetFontString()
        if fs then fs:SetText(text) end
    end
    setLbl(sb[1], StateLabel(CQ.filter))
    setLbl(sb[2], SideLabel(CQ.side))
    if sb[2] and sb[2].GetFontString then
        local fs = sb[2]:GetFontString()
        local fc = (CQ.side == "A" and DG.C_FAC_A) or (CQ.side == "H" and DG.C_FAC_H) or nil
        if fs then
            if fc then fs:SetTextColor(fc[1], fc[2], fc[3], 1)
            else fs:SetTextColor(Unpack(C_TEXT)) end
        end
        local tex = FAC_TEX[CQ.side or ""]
        if CQ.sideIcon then
            if tex then
                local tw = 0
                if fs and fs.GetStringWidth then
                    local ok, w = pcall(fs.GetStringWidth, fs)
                    if ok and type(w) == "number" then tw = w end
                end
                CQ.sideIcon:ClearAllPoints()
                CQ.sideIcon:SetPoint("RIGHT", sb[2], "CENTER", -(tw / 2) - 3, 0)
                CQ.sideIcon:SetTexture(tex)
                CQ.sideIcon:SetVertexColor(1, 1, 1, 1)
                CQ.sideIcon:Show()
            else
                CQ.sideIcon:Hide()
            end
        end
    end
    setLbl(sb[3], RaceLabel(CQ.race))
end

function CQ.Hide()
    if CQ.built then
        ResetRows()
        if CQ.title then CQ.title:Hide() end
        if CQ.sub then CQ.sub:Hide() end
        if CQ.cardL then CQ.cardL:Hide() end
        if CQ.cardR then CQ.cardR:Hide() end
        if CQ.fbar then CQ.fbar:Hide() end
        if CQ.dtrack then CQ.dtrack:Hide() end
        if CQ.dthumb then CQ.dthumb:Hide() end
        if CQ.dscroll then CQ.dscroll:Hide() end
        DetReset()
        TT.PlaceScroll(TT.MODE_TOP)
    end
    CQ.rowsDrawn = false
end

local function Placeholder(y)
    DetReset()
    local f = TakeTxt()
    if f then
        CQ.title:Hide()
        CQ.sub:Hide()
        f:SetText(L["点左侧任务查看详情"])
        f:SetTextColor(Unpack(C_GREY))
        y = putDet(f, DET_X, y, 24)
    end
    return y
end

function CQ.Render()
    CQ.cls = TT.PaintHeader()
    if not CQ.cls then return end
    if not Ensure() then return end
    if DG.BuildQuestSnap then DG.BuildQuestSnap() end
    Layout()

    InitFilter()
    local full = Build()
    AutoRace()
    local list = ApplyFilter(full)
    CQ.full, CQ.list = full, list

    ResetRows()
    DetReset()

    local sel = CQ.sel
    if not sel or (sel.type == "chain" and not sel.row) then
        if list[1] then
            sel = { type = "chain", row = list[1] }
            CQ.open = CQ.open or {}
            if not CQ.open[list[1].key] then CQ.open[list[1].key] = true end
            CQ.sel = sel
        end
    elseif sel.type == "chain" then
        local found
        for i = 1, #list do
            if list[i].key == sel.row.key then found = list[i] break end
        end
        if found then sel.row = found else found = list[1] end
        if not found then sel = nil else sel.row = found; CQ.sel = sel end
    end
    CQ.open = CQ.open or {}

    local y = -(TOP_Y)
    if #list == 0 then
        local fr = TakeHead()
        if fr then
            fr.arrow:SetText("")
            fr.dot:Hide()
            fr.sym:Hide()
            fr.name:SetText((#full > 0) and L["当前筛选下没有任务"] or L["暂无职业任务数据"])
            fr.name:SetTextColor(Unpack(C_GREY))
            fr.meta:SetText("")
            fr.lv:SetText("")
            fr.__act = nil
            fr.__sel = false
            fr:ClearAllPoints()
            fr:SetPoint("TOPLEFT", TT.child, "TOPLEFT", 0, y)
            fr:Show()
            Hui(false, fr)
            y = y - HEAD_H - 4
        end
    end

    for i = 1, #list do
        local row = list[i]
        local fr = TakeHead()
        if not fr then break end
        local isOpen = CQ.open[row.key] and true or false
        local isSel = (sel and sel.type == "chain" and sel.row.key == row.key) and true or false
        fr.arrow:SetText(isOpen and "-" or "+")
        fr.arrow:SetTextColor(Unpack(isOpen and C_GOLD or C_GREY))
        local doneN = AnyDone(row.ids)
        local st = (doneN >= #row.ids) and "done" or ((doneN > 0 or AnyActive(row.ids)) and "active" or "todo")
        PutDot(fr.dot, fr.sym, st)
        fr.name:SetText(row.t)
        fr.name:SetTextColor(Unpack((st == "done") and C_DONE or (isSel and C_GOLD or C_TEXT)))
        fr.name:SetWidth(RowW() - 34 - 52 - 46)
        fr.meta:SetText(format("%d/%d", doneN, #row.ids))
        fr.meta:SetTextColor(Unpack(C_DIM))
        fr.lv:SetText(LvTxt(row.lv))
        fr.lv:SetTextColor(Unpack(C_GREY))
        fr.__sel = isSel or isOpen
        Hui(fr.__sel, fr, isOpen and "hover" or nil)
        fr.__act = function()
            CQ.open[row.key] = not CQ.open[row.key]
            CQ.sel = { type = "chain", row = row }
            CQ.ToTop()
            TT.RequestRender()
        end
        fr:ClearAllPoints()
        fr:SetPoint("TOPLEFT", TT.child, "TOPLEFT", 0, y)
        fr:SetHeight(HEAD_H)
        fr.__cy, fr.__ch, fr.__cgen = -y, HEAD_H, TT.__renderGen
        fr:Show()
        y = y - HEAD_H - 3

        if isOpen then
            for j = 1, #row.ids do
                local qid = row.ids[j]
                local r = TakeRow()
                if not r then break end
                local qst = DG.QuestState(qid)
                PutDot(r.dot, r.sym, qst)
                local qn = QName(qid)
                local qsel = (sel and sel.type == "quest" and sel.id == qid) and true or false
                r.name:SetText(qn)
                r.name:SetTextColor(Unpack((qst == "done") and C_DONE or (qsel and C_GOLD or C_TEXT)))
                r.name:SetWidth(RowW() - ROW_IND - 30 - 46)
                local q = Info(qid)
                r.lv:SetText(LvTxt(q and q.r))
                r.lv:SetTextColor(Unpack(C_GREY))
                r.__sel = qsel
                Hui(qsel, r)
                r.__act = function()
                    CQ.sel = { type = "quest", id = qid, chain = row }
                    CQ.ToTop()
                    TT.RequestRender()
                end
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", TT.child, "TOPLEFT", ROW_IND, y)
                r:SetHeight(ROW_H)
                r.__cy, r.__ch, r.__cgen = -y, ROW_H, TT.__renderGen
                r:Show()
                y = y - ROW_H - 1
            end
            y = y - 4
        end
    end
    local yLeft = -y

    local yRight
    if sel and sel.type == "quest" then
        yRight = -renderQuest(sel.id, -(TOP_Y))
    elseif sel and sel.type == "chain" and sel.row then
        yRight = -renderChain(sel.row, -(TOP_Y))
    else
        yRight = -Placeholder(-(TOP_Y))
    end

    local h = math.max(yLeft, 40) + 12
    TT.child:SetHeight(h)
    TT.overflowed = CQ.nHead > HEAD_MAX or CQ.nRow > ROW_MAX

    if CQ.dchild then
        CQ.dchild:SetHeight(math.max(yRight, 40) + 12)
        CQ.UpdateDBar()
    end
end

function CQ.OnItemData(itemID)
    if not (CQ.built and CQ.sel) then return end
    local st = CQ.sel.type
    if st ~= "quest" and st ~= "chain" then return end
    if CQ.__itemT then return end
    CQ.__itemT = C_Timer and C_Timer.NewTimer(0.25, function()
        CQ.__itemT = nil
        local s = CQ.sel
        if s and (s.type == "quest" or s.type == "chain") then TT.RequestRender() end
    end) or nil
end

function CQ.Cull(gen, vTop, vBot)
    if not CQ.built then return end
    local function one(el)
        if not el or el.__cgen ~= gen then return end
        local cy, ch = el.__cy, el.__ch
        if type(cy) ~= "number" or type(ch) ~= "number" then return end
        if ((cy + ch) > vTop) and (cy < vBot) then el:Show() else el:Hide() end
    end
    for i = 1, HEAD_MAX do one(CQ.heads[i]) end
    for i = 1, ROW_MAX do one(CQ.rows[i]) end
end
