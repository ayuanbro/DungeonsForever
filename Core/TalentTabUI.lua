local _, ns = ...

local TT = ns.TierModule
if not TT then return end

local Host = ns.ProfHost
if not Host then return end

local format = string.format
local L = ns.L

local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local MakeOutline, SetOutline, SetButtonSelected, Unpack = Host.MakeOutline, Host.SetOutline, Host.SetButtonSelected, Host.Unpack
local C_GOLD, C_GREY, C_DIM, C_TEXT, C_WHITE = Host.C_GOLD, Host.C_GREY, Host.C_DIM, Host.C_TEXT, Host.C_WHITE

local TD = ns.TalentTrees
local TP = ns.TalentPlans

local UI = ns.TalentTabUI or {}
ns.TalentTabUI = UI

local Rebuild
local RelayoutPlan
local PlanMaxOff
local Refresh
local OpenPlanPop
local BuildRemainSeq
local UpdatePlanRows

local GAP = 8
local PAD = 10
local ICON = 30
local HEADER_H = 32
local NAV_H = 34
local ROW_H = 24
local MAX_PT = 51
local LINE_C = 0.58

local RANK_H, RANK_PAD, RANK_R = 14, 3, 4
local SEQ_MAX_W = 62
local SEQ_GREY = "|cff999999"
local SEQ_GREEN = "|cff4dff73"
local SEQ_SEP = "|cff808080, |r"
local BORDER_FULL = { 1.00, 0.82, 0.25 }
local BORDER_OPEN = { 0.62, 0.62, 0.62 }
local BORDER_LOCK = { 0.42, 0.42, 0.42 }

local function TalDB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local t = DungeonsForeverDB.talent
    if not t then
        t = {}
        DungeonsForeverDB.talent = t
    end
    return t
end

local function SeqOn()
    local t = TalDB()
    if t.seqOn == nil then t.seqOn = true end
    return t.seqOn
end

local function BuildsOf()
    local t = TalDB()
    t.builds = t.builds or {}
    t.builds[UI.cls] = t.builds[UI.cls] or {}
    return t.builds[UI.cls]
end

local function BodyH()
    local page = TT.page
    local ph = page and page.GetHeight and page:GetHeight() or 648
    return ph - TT.MODE_TOP - (TT.EDGE + TT.INSET)
end

local function PlateH()
    return BodyH() - NAV_H - GAP
end

local function ColW()
    return math.floor((TT.RIGHT_W - GAP * 3) / 4)
end

local function PlanW()
    return TT.RIGHT_W - ColW() * 3 - GAP * 3
end

local function ClassColorOf(cls)
    local c = RAID_CLASS_COLORS and RAID_CLASS_COLORS[cls]
    if c then return c.r, c.g, c.b end
    return 1, 0.82, 0
end

local function TreeSpent(t)
    local s = 0
    local pts = UI.mock and UI.mock.pts[t]
    if pts then
        for _, v in pairs(pts) do s = s + v end
    end
    return s
end

local function GateOK(t, row)
    if row <= 1 then return true end
    return TreeSpent(t) >= (row - 1) * 5
end

local function plate()
    local f = CreateFrame("Frame", nil, TT.page, "BackdropTemplate")
    f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                    edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
    if not (ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(f, nil, 2)) then
        f:SetBackdropColor(1, 1, 1, 0.04)
        f:SetBackdropBorderColor(1, 1, 1, 0.07)
    end
    f:Hide()
    return f
end

local function NodeTip(btn, tree, nd, p)
    GameTooltip:SetOwner(btn, "ANCHOR_BOTTOMRIGHT")
    GameTooltip:ClearLines()
    local cr, cg, cb = ClassColorOf(UI.cls)
    GameTooltip:AddLine(nd.n, cr, cg, cb)
    GameTooltip:AddLine(tree.name .. " · " .. format(L["第%d行第%d列"], nd.row, nd.col), 0.7, 0.75, 0.82)
    if nd.passive then
        GameTooltip:AddLine(L["被动"], 0.55, 0.78, 1)
    end
    local di = math.min(math.max(p, 1), #nd.desc)
    if nd.desc[di] then
        GameTooltip:AddLine(nd.desc[di], 0.9, 0.92, 0.96, true)
    end
    if p > 0 and p < nd.max and nd.desc[p + 1] then
        GameTooltip:AddLine(format("%s%d：%s", L["下一级"], p + 1, nd.desc[p + 1]), 0.6, 0.65, 0.75, true)
    end
    if p == 0 and not GateOK(tree.__ti, nd.row) then
        local need = (nd.row - 1) * 5 - TreeSpent(tree.__ti)
        GameTooltip:AddLine(format(L["需本系再投入 %d 点"], need), 0.95, 0.45, 0.4, true)
    end
    GameTooltip:AddLine(L["左键加点 · 右键减点"], 0.5, 0.55, 0.65)
    GameTooltip:Show()
end

local function HideTip()
    if GameTooltip then GameTooltip:Hide() end
end

local function BindResetBtn(rb)
    rb:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["重置本系天赋点"], 1, 0.82, 0)
        GameTooltip:Show()
    end)
    rb:SetScript("OnLeave", HideTip)
    rb:SetScript("OnClick", function()
        local t = rb.__tree
        if UI.mock and UI.mock.pts[t] then
            UI.mock.pts[t] = {}
            Refresh()
            ns.PlaySound(1)
        end
    end)
end

local function TakeLine(parent)
    UI.linePool = UI.linePool or {}
    local tex
    for _, t in ipairs(UI.linePool) do
        if not t.__inUse then tex = t break end
    end
    if not tex then
        tex = parent:CreateTexture(nil, "ARTWORK")
        tex:SetTexture("Interface\\Buttons\\WHITE8x8")
        UI.linePool[#UI.linePool + 1] = tex
    end
    tex.__inUse = true
    tex:Show()
    return tex
end

local FONT_BASE
local function Fnt(size)
    FONT_BASE = FONT_BASE or ns.FONT
    return FONT_BASE, size, ns.hui.FontFlags("OUTLINE")
end

local function MakeRankCard(parent)
    local f = CreateFrame("Frame", nil, parent)
    f:SetSize(RANK_PAD * 2 + 14, RANK_H)
    f:SetFrameLevel((parent:GetFrameLevel() or 0) + 2)
    if ns.hui and ns.hui.BuildRoundedBG then
        f.__fill = ns.hui.BuildRoundedBG(f, RANK_R, ns.hui.layer.L3, "both", true, 1)
    end
    f.fs = MakeFS(f, 12, C_WHITE, "CENTER")
    f.fs:SetPoint("CENTER", f, "CENTER", 0, 0)
    f:SetPoint("BOTTOMRIGHT", parent, "BOTTOMRIGHT", 3, -3)
    return f
end

local function SetRankCard(card, txt, color)
    if not card then return end
    card.fs:SetText(txt)
    local w = card.fs:GetStringWidth()
    if type(w) ~= "number" or w <= 0 then w = #txt * 7 end
    card:SetSize(math.floor(w + RANK_PAD * 2 + 0.5), RANK_H)
    if color then
        card.fs:SetTextColor(Unpack(color))
    else
        card.fs:SetTextColor(1, 1, 1, 1)
    end
end

local function SeqTextW(t, size)
    if ns.hui and ns.hui.TextW then return ns.hui.TextW(t, size) end
    return #t * size * 0.58
end

local function SeqRangeText(levels, spentOf)
    local seg, plain, i, n = {}, {}, 1, #levels
    while i <= n do
        local j = i
        while j < n and levels[j + 1] == levels[j] + 1 do j = j + 1 end
        local allSpent = true
        for k = i, j do
            if not spentOf(k) then
                allSpent = false
                break
            end
        end
        local t = (j > i) and (levels[i] .. "-" .. levels[j]) or tostring(levels[i])
        seg[#seg + 1] = (allSpent and SEQ_GREY or SEQ_GREEN) .. t .. "|r"
        plain[#plain + 1] = t
        i = j + 1
    end
    return table.concat(seg, SEQ_SEP), table.concat(plain, ", ")
end

local function PaintSeqBadge(slot, parent, txt, plain)
    local size = 12
    local w = SeqTextW(plain, size)
    if w + RANK_PAD * 2 > SEQ_MAX_W then
        size = 10
        w = SeqTextW(plain, size)
    end
    local body = txt
    if w + RANK_PAD * 2 > SEQ_MAX_W then
        local cut = plain
        if ns.hui and ns.hui.Fit then cut = ns.hui.Fit(plain, size, SEQ_MAX_W - RANK_PAD * 2) end
        body = SEQ_GREEN .. cut .. "|r"
        w = SeqTextW(cut, size)
    end
    local bw = math.floor(w + RANK_PAD * 2 + 0.5)
    if not slot then
        local f = CreateFrame("Frame", nil, parent)
        f:SetFrameLevel((parent:GetFrameLevel() or 0) + 1)
        if ns.hui and ns.hui.BuildRoundedBG then
            f.__fill = ns.hui.BuildRoundedBG(f, RANK_R, ns.hui.layer.L3, "both", true, 1)
        end
        local fs = MakeFS(f, size, C_WHITE, "CENTER")
        fs:SetAllPoints()
        fs:SetWordWrap(false)
        slot = { f = f, fs = fs }
    end
    slot.f:SetSize(bw, RANK_H)
    slot.fs:SetFont(Fnt(size))
    slot.fs:SetText(body)
    slot.f:ClearAllPoints()
    slot.f:SetPoint("BOTTOM", parent, "TOP", 0, 0)
    slot.f:Show()
    return slot
end

local function TakeNode(parent)
    UI.pool = UI.pool or {}
    local btn
    for _, b in ipairs(UI.pool) do
        if not b.__inUse then btn = b break end
    end
    if not btn then
        btn = CreateFrame("Button", nil, parent)
        btn:SetSize(ICON, ICON)
        btn.iconFrame = CreateFrame("Frame", nil, btn)
        btn.iconFrame:SetAllPoints()
        btn.iconFrame:SetFrameLevel((btn:GetFrameLevel() or 0))
        btn.iconTex = btn.iconFrame:CreateTexture(nil, "BACKGROUND")
        btn.iconTex:SetAllPoints()
        btn.iconTex:SetTexCoord(0.14, 0.86, 0.14, 0.86)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(btn.iconTex) end
        btn.borderTex = btn.iconFrame:CreateTexture(nil, "OVERLAY")
        btn.borderTex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\TalentBorder")
        btn.borderTex:SetSize(ICON + 4, ICON + 4)
        btn.borderTex:SetPoint("CENTER", btn, "CENTER", 0, 0)
        btn:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        btn.rankCard = MakeRankCard(btn)
        btn.rank = btn.rankCard.fs
        btn.seqFrame = CreateFrame("Frame", nil, btn)
        btn.seqFrame:SetFrameLevel((btn:GetFrameLevel() or 0) + 3)
        btn.seqFrame:SetPoint("CENTER", btn, "CENTER", 0, 0)
        btn.seqFrame:SetSize(ICON, ICON)
        btn.seqBadge = nil
        UI.pool[#UI.pool + 1] = btn
    end
    btn.__inUse = true
    btn:SetParent(parent)
    btn:Show()
    return btn
end

local function ResetNodes()
    for _, b in ipairs(UI.pool or {}) do
        b.__inUse = false
        b:Hide()
        SetButtonSelected(b, false)
    end
    for _, t in ipairs(UI.linePool or {}) do
        t.__inUse = false
        t:Hide()
    end
end

BuildRemainSeq = function()
    UI.remainSeq = nil
    UI.outOfPlan = nil
    UI.liveMode = false
    UI.staticSeq = false
    local data = TD and UI.cls and TD[UI.cls]
    local alloc = UI.planAlloc
    if not (data and alloc) then return end
    local read = UI.liveBase
    if not read or UI.planViewMode == "plan" then
        if UI.planSeq and #UI.planSeq > 0 then
            local seq, seqk, k = {}, {}, 0
            for _, pt in ipairs(UI.planSeq) do
                local t, ni = pt[1], pt[2]
                local tree = data.trees[t]
                local nd = tree and tree.nodes[ni]
                if nd and alloc[t] and alloc[t][ni] then
                    local key = t * 100 + ni
                    seqk[key] = (seqk[key] or 0) + 1
                    k = k + 1
                    seq[#seq + 1] = { t = t, ni = ni, nd = nd, rank = seqk[key], lv = 9 + k }
                end
            end
            UI.remainSeq = seq
            UI.staticSeq = #seq > 0 and true or false
        end
        return
    end
    UI.liveMode = true
    local real = { {}, {}, {} }
    local st = { 0, 0, 0 }
    local oop = {}
    for t = 1, 3 do
        local tree = data.trees[t]
        if tree then
            for ni, nd in ipairs(tree.nodes) do
                local live = read.byName[nd.n]
                if live and live.rank > 0 then
                    real[t][ni] = live.rank
                    st[t] = st[t] + live.rank
                    local pv = alloc[t] and alloc[t][ni] or 0
                    if live.rank > pv then
                        oop[#oop + 1] = { t = t, ni = ni, nd = nd, rem = live.rank - pv }
                    end
                end
            end
        end
    end
    local curLv = (UnitLevel and UnitLevel("player")) or 0
    local baseSpent = read.spent
    if UI.planSeq and #UI.planSeq > 0 then
        local seq, k = {}, 0
        local seqk = {}
        for _, pt in ipairs(UI.planSeq) do
            local t, ni = pt[1], pt[2]
            local tree = data.trees[t]
            local nd = tree and tree.nodes[ni]
            if nd and alloc[t] and alloc[t][ni] then
                local key = t * 100 + ni
                seqk[key] = (seqk[key] or 0) + 1
                local live = read.byName[nd.n]
                local realRank = live and live.rank or 0
                if seqk[key] > realRank then
                    k = k + 1
                    seq[#seq + 1] = {
                        t = t,
                        ni = ni,
                        nd = nd,
                        rank = math.max(realRank, seqk[key]),
                        lv = math.max(curLv, baseSpent + k + 9),
                        over = math.max(curLv, baseSpent + k + 9) > 60,
                    }
                end
            end
        end
        UI.remainSeq = seq
        UI.outOfPlan = oop
        return
    end
    local left = {}
    for t = 1, 3 do
        local tree = data.trees[t]
        local idxs = {}
        for ni in pairs(alloc[t] or {}) do
            local nd = tree and tree.nodes[ni]
            local live = nd and read.byName[nd.n]
            if nd and live then
                local rem = math.min((alloc[t][ni] or 0) - live.rank, live.max - live.rank)
                if rem > 0 then
                    idxs[#idxs + 1] = { ni = ni, nd = nd, rem = rem, base = live.rank }
                end
            end
        end
        table.sort(idxs, function(a, b)
            local A, B = a.nd, b.nd
            if A.row ~= B.row then return A.row < B.row end
            if A.col ~= B.col then return A.col < B.col end
            return a.ni < b.ni
        end)
        left[t] = idxs
    end
    local seq, k = {}, 0
    while true do
        local progressed = false
        for t = 1, 3 do
            local list = left[t]
            local i = 1
            while i <= #list do
                local it = list[i]
                if st[t] >= (it.nd.row - 1) * 5 then
                    while it.rem > 0 and st[t] >= (it.nd.row - 1) * 5 do
                        k = k + 1
                        seq[#seq + 1] = {
                            t = t,
                            ni = it.ni,
                            nd = it.nd,
                            rank = it.base + 1,
                            lv = math.max(curLv, baseSpent + k + 9),
                        over = math.max(curLv, baseSpent + k + 9) > 60,
                        }
                        it.base = it.base + 1
                        st[t] = st[t] + 1
                        it.rem = it.rem - 1
                    end
                    if it.rem <= 0 then
                        table.remove(list, i)
                    else
                        i = i + 1
                    end
                    progressed = true
                else
                    i = i + 1
                end
            end
        end
        if not progressed then break end
    end
    UI.remainSeq = seq
    UI.outOfPlan = oop
end

local function BuildSeqMap()
    if not (UI.seqOnNow and UI.planAlloc) then return nil end
    if (UI.liveMode or UI.staticSeq) and UI.remainSeq then
        local maps = { {}, {}, {} }
        for _, it in ipairs(UI.remainSeq) do
            if not it.over then
                local m = maps[it.t]
                local list = m[it.ni]
                if not list then list = {}; m[it.ni] = list end
                list[#list + 1] = it.lv
            end
        end
        return maps
    end
    local data = TD[UI.cls]
    if not data then return nil end
    local maps = {}
    local step = 0
    for t = 1, 3 do
        local m = {}
        local tree = data.trees[t]
        if tree then
            local idxs = {}
            for ni in pairs(UI.planAlloc[t] or {}) do
                if tree.nodes[ni] then idxs[#idxs + 1] = ni end
            end
            table.sort(idxs, function(a, b)
                local A, B = tree.nodes[a], tree.nodes[b]
                if A.row ~= B.row then return A.row < B.row end
                if A.col ~= B.col then return A.col < B.col end
                return a < b
            end)
            for _, ni in ipairs(idxs) do
                local p = UI.planAlloc[t][ni] or 0
                local list = {}
                for k = 1, p do list[k] = step + 9 + k end
                list.base = step
                step = step + p
                m[ni] = list
            end
        end
        maps[t] = m
    end
    return maps
end

Refresh = function()
    if not UI.built then return end
    local data = TD and UI.cls and TD[UI.cls]
    if not (data and UI.mock) then return end
    UI.seqOnNow = SeqOn()
    BuildRemainSeq()
    local maps = BuildSeqMap()
    local total = 0
    for t = 1, 3 do total = total + TreeSpent(t) end
    for t = 1, 3 do
        local tree = data.trees[t]
        if tree then
            UI.spentFs[t]:SetText(format("%d/%d", TreeSpent(t), MAX_PT))
        else
            UI.spentFs[t]:SetText("")
        end
    end
    local planTotal = 0
    if UI.planAlloc then
        for t = 1, 3 do
            for _, p in pairs(UI.planAlloc[t] or {}) do planTotal = planTotal + (p or 0) end
        end
    end
    if UI.liveMode and UI.remainSeq then
        local remain = #UI.remainSeq
        UI.totalFs:SetText(remain > 0 and format(L["剩余 %d 点"], remain) or "")
    else
        UI.totalFs:SetText(planTotal > 0 and format(L["共 %d 点"], planTotal) or "")
    end
    for t = 1, 3 do
        local tree = data.trees[t]
        if tree then
            for i, nd in ipairs(tree.nodes) do
                local btn = UI.nodeOf[t] and UI.nodeOf[t][i]
                if btn then
                    local pts = UI.mock.pts[t]
                    local p = pts[i] or 0
                    local locked = p == 0 and not GateOK(t, nd.row)
                    local nt = btn.iconTex
                    if nt and nt.SetDesaturated then nt:SetDesaturated(locked) end
                    btn:SetAlpha(locked and 0.55 or 1)
                    local border = locked and BORDER_LOCK or (p > 0 and BORDER_FULL or BORDER_OPEN)
                    if btn.borderTex then
                        btn.borderTex:SetVertexColor(border[1], border[2], border[3], 1)
                    end
                    SetRankCard(btn.rankCard, format("%d/%d", p, nd.max), locked and C_DIM or C_WHITE)
                    local seqs = maps and maps[t] and maps[t][i]
                    if seqs and #seqs > 0 then
                        local txt, plain
                        if UI.liveMode then
                            txt, plain = SeqRangeText(seqs, function() return false end)
                        else
                            local base = seqs.base or 0
                            txt, plain = SeqRangeText(seqs, function(k) return (base + k) <= total end)
                        end
                        btn.seqBadge = PaintSeqBadge(btn.seqBadge, btn.seqFrame, txt, plain)
                        btn.seqFrame:Show()
                    else
                        if btn.seqBadge then btn.seqBadge.f:Hide() end
                        btn.seqFrame:Hide()
                    end
                    local hl = UI.hl and UI.hl[1] == t and UI.hl[2] == i
                    SetButtonSelected(btn, hl)
                end
            end
        end
    end
    UpdatePlanRows()
end

local function CopyAlloc(alloc)
    local out = { {}, {}, {} }
    for t = 1, 3 do
        for ni, p in pairs(alloc[t] or {}) do out[t][ni] = p end
    end
    return out
end

local function ApplyPlan(alloc, selIdx, seq)
    UI.mock = { pts = CopyAlloc(alloc) }
    UI.planAlloc = CopyAlloc(alloc)
    UI.planSel = selIdx
    UI.planSeq = seq
end

local function ApplyPreset(idx)
    local plans = TP and TP[UI.cls]
    local it = plans and plans[idx]
    if not it then return end
    ApplyPlan(it.alloc, idx, it.seq)
end

OpenPlanPop = function()
    local data = TD and TD[UI.cls]
    if not (data and UI.planPop) then return end
    for _, f in ipairs({ UI.planPop:GetChildren() }) do f:Hide() end
    local rows = {}
    local plans = TP and TP[UI.cls] or {}
    for i = 1, #plans do
        rows[#rows + 1] = { label = plans[i].name or format(L["方案%d"], i), alloc = plans[i].alloc, seq = plans[i].seq, sel = i }
    end
    local bl = BuildsOf()
    for i = 1, #bl do
        rows[#rows + 1] = { label = bl[i].name, alloc = bl[i].alloc, blIdx = i }
    end
    local w = 352
    local y = 6
    for _, r in ipairs(rows) do
        local bt = CreateFrame("Button", nil, UI.planPop)
        bt:SetSize(w - 8, 24)
        bt:SetPoint("TOPLEFT", UI.planPop, "TOPLEFT", 4, -y)
        bt:SetHighlightTexture("Interface\\Buttons\\WHITE8x8", "ADD")
        local hl = bt:GetHighlightTexture()
        if hl then hl:SetAlpha(0.08) end
        local lb = MakeFS(bt, 14, C_TEXT, "LEFT")
        lb:SetPoint("LEFT", bt, "LEFT", 3, 0)
        lb:SetWidth(76)
        lb:SetJustifyH("LEFT")
        lb:SetText(r.label)
        local total = 0
        local x = 120
        for t = 1, 3 do
            local tree = data.trees[t]
            local pts = 0
            for _, v in pairs(r.alloc[t] or {}) do pts = pts + v end
            total = total + pts
            if tree then
                local ic = bt:CreateTexture(nil, "ARTWORK")
                ic:SetSize(14, 14)
                ic:SetPoint("TOPLEFT", bt, "TOPLEFT", x, -5)
                ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                ic:SetTexture("Interface\\Icons\\" .. tostring(tree.icon))
                local pv = MakeFS(bt, 14, C_GOLD, "LEFT")
                pv:SetPoint("LEFT", bt, "LEFT", x + 16, 0)
                pv:SetText(pts)
            end
            if t < 3 then
                local sl = MakeFS(bt, 14, C_DIM, "LEFT")
                sl:SetPoint("LEFT", bt, "LEFT", x + 30, 0)
                sl:SetText("/")
            end
            x = x + 40
        end
        local lv = MakeFS(bt, 14, C_DIM, "RIGHT")
        lv:SetPoint("RIGHT", bt, "RIGHT", -2, 0)
        lv:SetText(format(L["需要等级 %d"], total + 9))
        local selIdx = r.sel
        if r.blIdx then
            local del = CreateFrame("Button", nil, bt)
            del:SetSize(18, 18)
            del:SetPoint("TOPLEFT", bt, "TOPLEFT", 98, -3)
            del:SetNormalFontObject(GameFontNormalSmall)
            del:SetText("X")
            del:GetFontString():SetTextColor(1, 0.4, 0.35, 1)
            del:SetScript("OnClick", function()
                StaticPopupDialogs["DF_TALENT_BUILD_DEL"] = {
                    text = format(L["删除方案「%s」？"], r.label),
                    button1 = L["确定"],
                    button2 = L["取消"],
                    OnAccept = function()
                        local list = BuildsOf()
                        for bi = #list, 1, -1 do
                            if list[bi] == bl[r.blIdx] then table.remove(list, bi) end
                        end
                        OpenPlanPop()
                    end,
                    timeout = 0,
                    whileDead = true,
                    hideOnEscape = true,
                    preferredIndex = 3,
                }
                StaticPopup_Show("DF_TALENT_BUILD_DEL")
            end)
            local ren = CreateFrame("Button", nil, bt)
            ren:SetSize(18, 18)
            ren:SetPoint("TOPLEFT", bt, "TOPLEFT", 80, -3)
            ren:SetNormalFontObject(GameFontNormalSmall)
            ren:SetText("改")
            ren:GetFontString():SetTextColor(0.6, 0.8, 1, 1)
            ren:SetScript("OnClick", function()
                StaticPopupDialogs["DF_TALENT_BUILD_REN"] = {
                    text = L["输入新的方案名"],
                    button1 = L["确定"],
                    button2 = L["取消"],
                    hasEditBox = true,
                    editBoxWidth = 260,
                    maxLetters = 24,
                    OnShow = function(self)
                        local e = self.EditBox or self.editBox
                        e:SetText(r.label)
                        e:HighlightText()
                        e:SetFocus()
                    end,
                    OnAccept = function(self)
                        local e = self.EditBox or self.editBox
                        local nm = e:GetText()
                        nm = nm and nm:gsub("^%s+", ""):gsub("%s+$", "") or ""
                        if nm ~= "" then
                            bl[r.blIdx].name = nm
                            OpenPlanPop()
                        end
                    end,
                    EditBoxOnEnterPressed = function(self)
                        local p = self:GetParent()
                        p.button1:Click()
                    end,
                    EditBoxOnEscapePressed = function(self) self:GetParent():Hide() end,
                    timeout = 0,
                    whileDead = true,
                    hideOnEscape = true,
                    preferredIndex = 3,
                }
                StaticPopup_Show("DF_TALENT_BUILD_REN")
            end)
        end
        bt:SetScript("OnClick", function()
            ApplyPlan(r.alloc, selIdx, r.seq)
            UI.hl = nil
            UI.planOff = 0
            UI.planPop:Hide()
            Rebuild()
            ns.PlaySound(1)
        end)
        y = y + 26
    end
    UI.planPop:SetSize(w, y + 4)
    UI.planPop:ClearAllPoints()
    UI.planPop:SetPoint("TOPRIGHT", UI.loadBtn, "BOTTOMRIGHT", 2, -3)
    UI.planPop:Show()
end

local function EncodeMock()
    local data = TD and TD[UI.cls]
    if not (data and UI.mock) then return "" end
    local segs = {}
    for t = 1, 3 do
        local pts = UI.mock.pts[t]
        local maxI = 0
        for i in pairs(pts) do
            if i > maxI then maxI = i end
        end
        local parts = {}
        for i = 1, maxI do parts[i] = tostring(pts[i] or 0) end
        while #parts > 0 and parts[#parts] == "0" do parts[#parts] = nil end
        segs[t] = table.concat(parts)
    end
    return segs[1] .. "-" .. segs[2] .. "-" .. segs[3]
end

local function DecodeMock(code)
    local data = TD and TD[UI.cls]
    if not (data and code and code ~= "") then return false end
    local segs = { strsplit("-", code) }
    local pts = { {}, {}, {} }
    for t = 1, 3 do
        local s = tostring(segs[t] or "")
        local nodes = data.trees[t] and data.trees[t].nodes or {}
        for i = 1, #s do
            local d = tonumber(string.sub(s, i, i))
            local nd = nodes[i]
            if d and d > 0 and nd and d <= nd.max then
                pts[t][i] = d
            end
        end
    end
    UI.mock = { pts = pts }
    UI.planAlloc = nil
    UI.planSel = nil
    UI.hl = nil
    return true
end

local CT, Traits = _G.C_ClassTalents, _G.C_Traits

local function LAvailable()
    return type(CT) == "table" and type(Traits) == "table"
        and type(Traits.PurchaseRank) == "function"
        and type(Traits.CommitConfig) == "function"
end

local function SafeCall(fn, ...)
    if type(fn) ~= "function" then return nil end
    local r = { pcall(fn, ...) }
    if r[1] ~= true then return nil end
    return r[2]
end

local function ResolveEntry(configID, n)
    local out = {}
    local eid = n.entryIDs and n.entryIDs[1]
    if not eid then return out end
    local entry = SafeCall(Traits.GetEntryInfo, configID, eid)
    if type(entry) ~= "table" or not entry.definitionID then return out end
    local def = SafeCall(Traits.GetDefinitionInfo, entry.definitionID)
    if type(def) ~= "table" then return out end
    local sid = def.overriddenSpellID or def.spellID
    out.name = def.overrideName
    if sid and _G.C_Spell and type(_G.C_Spell.GetSpellInfo) == "function" then
        local sp = SafeCall(_G.C_Spell.GetSpellInfo, sid)
        if type(sp) == "table" and not out.name then out.name = sp.name end
    end
    return out
end

local function ReadLiveTalents()
    if not LAvailable() then return nil end
    local configID = SafeCall(CT.GetActiveConfigID)
    if not configID then return nil end
    local ci = SafeCall(Traits.GetConfigInfo, configID)
    local treeID = ci and ci.treeIDs and ci.treeIDs[1]
    if not treeID then return nil end
    local nodeIDs = SafeCall(Traits.GetTreeNodes, treeID)
    if type(nodeIDs) ~= "table" or #nodeIDs == 0 then return nil end
    local byName, spent = {}, 0
    for _, nodeID in ipairs(nodeIDs) do
        local n = SafeCall(Traits.GetNodeInfo, configID, nodeID)
        if type(n) == "table" then
            local rank = tonumber(n.ranksPurchased) or 0
            spent = spent + rank
            local e = ResolveEntry(configID, n)
            if e.name and not byName[e.name] then
                byName[e.name] = { id = nodeID, rank = rank, max = tonumber(n.maxRanks) or 0 }
            end
        end
    end
    return { configID = configID, byName = byName, spent = spent }
end

function UI.LiveApplyPlan()
    if not LAvailable() then
        print("|cff46bf72[天赋]|r " .. L["客户端天赋接口不可用"])
        return
    end
    if not UI.liveBase then
        UI.liveBase = ReadLiveTalents()
    end
    local read = UI.liveBase
    if not read then
        print("|cff46bf72[天赋]|r " .. L["拿不到天赋配置（先打开一次游戏内天赋界面）"])
        return
    end
    local savedView = UI.planViewMode
    UI.planViewMode = "live"
    BuildRemainSeq()
    UI.planViewMode = savedView
    local remain = UI.liveMode and UI.remainSeq or nil
    if not remain or #remain <= 0 then
        print("|cff46bf72[天赋]|r " .. L["没有待学习的点（方案与当前天赋一致）"])
        return
    end
    local planned = #remain
    local lv = (UnitLevel and UnitLevel("player")) or 0
    local keep = math.min(planned, 51 - read.spent, lv - 9 - read.spent)
    if keep <= 0 then
        print("|cff46bf72[天赋]|r " .. L["没有可应用的点（当前没有可用的天赋点）"])
        return
    end
    local lines, shown = {}, 0
    for _, it in ipairs(remain) do
        local last = lines[#lines]
        if last and last.nm == it.nd.n then
            last.n = last.n + 1
        else
            lines[#lines + 1] = { nm = it.nd.n, n = 1 }
        end
    end
    local rows = {}
    for _, r in ipairs(lines) do
        shown = shown + 1
        if shown <= 10 then
            rows[#rows + 1] = format(L["|cff46bf72学习|r %s ×%d"], r.nm, r.n)
        end
    end
    local text = L["确认将当前方案真实学习到角色天赋："] .. "\n"
        .. table.concat(rows, "\n")
        .. (shown > 10 and ("\n" .. L["……其余略"]) or "")
        .. format("\n\n" .. L["共 %d 点，当前可用 %d 点"], planned, keep)
    if keep < planned then
        text = text .. "\n" .. format(L["注意：本次只应用前 %d 点，其余需升级获得点数后再点「一键加点」。"], keep)
    end
    StaticPopupDialogs["DF_TALENT_LIVE_APPLY"] = {
        text = text,
        button1 = L["确定"],
        button2 = L["取消"],
        OnAccept = function()
            UI.LiveDoApply(read, remain, keep, planned)
        end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show("DF_TALENT_LIVE_APPLY")
end

function UI.LiveDoApply(read, remain, keep, planned)
    local done = 0
    local function fail(msg)
        if type(Traits.RollbackConfig) == "function" then
            SafeCall(Traits.RollbackConfig, read.configID)
        end
        print("|cffff5040[天赋]|r " .. msg .. L["（已回滚）"])
    end
    for _, it in ipairs(remain) do
        if done >= keep then break end
        local live = read.byName[it.nd.n]
        if live then
            local ok = SafeCall(Traits.PurchaseRank, read.configID, live.id)
            if ok == false then
                fail(format(L["学习 %s 失败"], it.nd.n))
                return
            end
            done = done + 1
        end
    end
    local committed = SafeCall(Traits.CommitConfig, read.configID)
    if committed == false then
        fail(L["提交失败"])
        return
    end
    if done < planned then
        print(format("|cff46bf72[天赋]|r " .. L["已应用（本次 %d / %d 点，其余需升级后再点）"], done, planned))
    else
        print("|cff46bf72[天赋]|r " .. L["已应用"])
    end
    UI.liveBase = ReadLiveTalents()
    UpdatePlanRows()
    Refresh()
end

local function ShowExport()
    UI.exportText = EncodeMock()
    if not StaticPopupDialogs["DF_TALENT_EXPORT"] then
        StaticPopupDialogs["DF_TALENT_EXPORT"] = {
            text = L["天赋方案串（复制分享）"],
            button1 = L["关闭"],
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
            hasEditBox = true,
            editBoxWidth = 320,
            OnShow = function(self)
                local e = self.EditBox or self.editBox
                e:SetText(UI.exportText or "")
                e:HighlightText()
                e:SetFocus()
            end,
            EditBoxOnEnterPressed = function(self) self:GetParent():Hide() end,
            EditBoxOnEscapePressed = function(self) self:GetParent():Hide() end,
        }
    end
    StaticPopup_Show("DF_TALENT_EXPORT")
end

local function ShowImport()
    if not StaticPopupDialogs["DF_TALENT_IMPORT"] then
        StaticPopupDialogs["DF_TALENT_IMPORT"] = {
            text = L["粘贴天赋方案串"],
            button1 = L["载入"],
            button2 = L["取消"],
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
            hasEditBox = true,
            editBoxWidth = 320,
            OnShow = function(self)
                local e = self.EditBox or self.editBox
                e:SetText("")
                e:SetFocus()
            end,
            EditBoxOnEnterPressed = function(self)
                local txt = self:GetText()
                self:GetParent():Hide()
                if DecodeMock(txt) then
                    UI.mockCls = UI.cls
                    Rebuild()
                end
            end,
            EditBoxOnEscapePressed = function(self) self:GetParent():Hide() end,
            OnAccept = function(self)
                local e = self.EditBox or self.editBox
                local txt = e:GetText()
                if DecodeMock(txt) then
                    UI.mockCls = UI.cls
                    Rebuild()
                end
            end,
        }
    end
    StaticPopup_Show("DF_TALENT_IMPORT")
end

local function TakePlanRow(parent)
    UI.planRowPool = UI.planRowPool or {}
    for _, b in ipairs(UI.planRowPool) do
        if not b.__inUse then return b end
    end
    local bt = CreateFrame("Button", nil, parent)
    bt:SetHighlightTexture("Interface\\Buttons\\WHITE8x8", "ADD")
    local ht = bt:GetHighlightTexture()
    if ht then ht:SetVertexColor(1, 1, 1, 0.07) end
    bt.num = MakeFS(bt, 14, C_DIM, "LEFT")
    bt.num:SetPoint("LEFT", bt, "LEFT", 4, 0)
    bt.num:SetWidth(24)
    bt.ic = bt:CreateTexture(nil, "ARTWORK")
    bt.ic:SetSize(16, 16)
    bt.ic:SetPoint("LEFT", bt, "LEFT", 30, 0)
    bt.ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    bt.nm = MakeFS(bt, 14, C_TEXT, "LEFT")
    bt.nm:SetPoint("LEFT", bt, "LEFT", 52, 0)
    bt.nm:SetJustifyH("LEFT")
    bt.vv = MakeFS(bt, 14, C_WHITE, "RIGHT")
    bt.vv:SetPoint("RIGHT", bt, "RIGHT", -4, 0)
    UI.planRowPool[#UI.planRowPool + 1] = bt
    return bt
end

local function BuildPlanRows(parent, w)
    for _, b in ipairs(UI.planRowPool or {}) do b.__inUse = false; b:Hide() end
    for _, b in ipairs(UI.planRows or {}) do b.__inUse = false; b:Hide() end
    UI.planRows = {}
    w = w - 2 * PAD
    if (UI.liveMode or UI.staticSeq) and UI.remainSeq then
        local y = 0
        for _, op in ipairs(UI.outOfPlan or {}) do
            local bt = TakePlanRow(parent)
            bt.__inUse = true
            bt:SetParent(parent)
            bt:SetSize(w - 4, ROW_H - 2)
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", parent, "TOPLEFT", 2, -(y))
            bt.num:SetText("◇")
            bt.ic:SetTexture("Interface\\Icons\\" .. op.nd.icon)
            bt.ic:SetDesaturated(true)
            bt.bg = bt.bg or bt:CreateTexture(nil, "BACKGROUND")
            bt.bg:SetAllPoints()
            bt.bg:SetColorTexture(1, 1, 1, 0.03)
            bt.bg:Show()
            bt.nm:SetWidth(w - 52 - 40)
            bt.nm:SetText(op.nd.n)
            bt.nm:SetTextColor(0.55, 0.55, 0.55, 1)
            bt.vv:SetText(format(L["方案外 ×%d"], op.rem))
            bt.vv:SetTextColor(0.55, 0.55, 0.55, 1)
            bt:SetScript("OnEnter", nil)
            bt:SetScript("OnLeave", nil)
            bt:SetScript("OnClick", nil)
            bt:Show()
            y = y + ROW_H
            UI.planRows[#UI.planRows + 1] = bt
        end
        for _, it in ipairs(UI.remainSeq) do
            local nd = it.nd
            local bt = TakePlanRow(parent)
            bt.__inUse = true
            bt:SetParent(parent)
            bt:SetSize(w - 4, ROW_H - 2)
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", parent, "TOPLEFT", 2, -(y))
            bt.num:SetText(it.over and "-" or tostring(it.lv))
            if bt.bg then bt.bg:Hide() end
            bt.ic:SetDesaturated(false)
            bt.ic:SetTexture("Interface\\Icons\\" .. nd.icon)
            bt.nm:SetWidth(w - 52 - 40)
            bt.nm:SetText(nd.n)
            bt.nm:SetTextColor(unpack(C_TEXT))
            if it.over then
                bt.vv:SetText(L["点不够"])
                bt.vv:SetTextColor(1, 0.45, 0.4, 1)
            else
                bt.vv:SetText(it.rank .. "/" .. nd.max)
                bt.vv:SetTextColor(unpack(C_WHITE))
            end
            bt:SetScript("OnEnter", function()
                bt.vv:SetTextColor(Unpack(C_GOLD))
                local node = UI.nodeOf[it.t] and UI.nodeOf[it.t][it.ni]
                if node then SetOutline(node, true, 1, 0.82, 0) end
            end)
            bt:SetScript("OnLeave", function()
                bt.vv:SetTextColor(Unpack(C_WHITE))
                Refresh()
            end)
            bt:SetScript("OnClick", function()
                UI.hl = { it.t, it.ni }
                Refresh()
            end)
            bt:Show()
            y = y + ROW_H
            UI.planRows[#UI.planRows + 1] = bt
        end
        RelayoutPlan()
        return
    end
    local alloc = UI.planAlloc
    local data = TD[UI.cls]
    if not (alloc and data) then return end
    local y = 0
    local step = 0
    for t = 1, 3 do
        local tree = data.trees[t]
        local idxs = {}
        for ni in pairs(alloc[t] or {}) do idxs[#idxs + 1] = ni end
        if tree then
            table.sort(idxs, function(a, b)
                local A, B = tree.nodes[a], tree.nodes[b]
                if A.row ~= B.row then return A.row < B.row end
                if A.col ~= B.col then return A.col < B.col end
                return a < b
            end)
        end
        for _, ni in ipairs(idxs) do
            local nd = tree and tree.nodes[ni]
            local p = alloc[t][ni]
            if nd and p and p > 0 then
                for k = 1, p do
                    step = step + 1
                    local bt = CreateFrame("Button", nil, parent)
                    bt:SetSize(w - 4, ROW_H - 2)
                    bt:SetPoint("TOPLEFT", parent, "TOPLEFT", 2, -(y))
                    bt:SetHighlightTexture("Interface\\Buttons\\WHITE8x8", "ADD")
                    local ht = bt:GetHighlightTexture()
                    if ht then ht:SetVertexColor(1, 1, 1, 0.07) end
                    local num = MakeFS(bt, 14, C_DIM, "LEFT")
                    num:SetPoint("LEFT", bt, "LEFT", 4, 0)
                    num:SetWidth(24)
                    num:SetText(tostring(step + 9))
                    local ic = bt:CreateTexture(nil, "ARTWORK")
                    ic:SetSize(16, 16)
                    ic:SetPoint("LEFT", bt, "LEFT", 30, 0)
                    ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                    ic:SetTexture("Interface\\Icons\\" .. nd.icon)
                    local nm = MakeFS(bt, 14, C_TEXT, "LEFT")
                    nm:SetPoint("LEFT", bt, "LEFT", 52, 0)
                    nm:SetWidth(w - 52 - 40)
                    nm:SetJustifyH("LEFT")
                    nm:SetText(nd.n)
                    local vv = MakeFS(bt, 14, C_WHITE, "RIGHT")
                    vv:SetPoint("RIGHT", bt, "RIGHT", -4, 0)
                    vv:SetText(k .. "/" .. nd.max)
                    bt:SetScript("OnEnter", function()
                        vv:SetTextColor(Unpack(C_GOLD))
                        local node = UI.nodeOf[t] and UI.nodeOf[t][ni]
                        if node then SetOutline(node, true, 1, 0.82, 0) end
                    end)
                    bt:SetScript("OnLeave", function()
                        vv:SetTextColor(Unpack(C_WHITE))
                        Refresh()
                    end)
                    bt:SetScript("OnClick", function()
                        UI.hl = { t, ni }
                        Refresh()
                    end)
                    y = y + ROW_H
                    UI.planRows[#UI.planRows + 1] = bt
                end
            end
        end
    end
    RelayoutPlan()
end

UpdatePlanRows = function()
    BuildRemainSeq()
    if UI.plist then
        BuildPlanRows(UI.plist, PlanW())
    end
end

local function PlanListTop()
    return HEADER_H - 2
end

local function PlanListGeom()
    local pw = PlanW()
    local listH = PlateH() - PlanListTop() - 8
    return pw, listH
end

PlanMaxOff = function()
    local _, listH = PlanListGeom()
    local n = #(UI.planRows or {})
    return math.max(0, n * ROW_H - listH)
end
RelayoutPlan = function()
    if not UI.plist then return end
    local pw, listH = PlanListGeom()
    UI.plist:ClearAllPoints()
    UI.plist:SetPoint("TOPLEFT", UI.plates[4], "TOPLEFT", PAD, -PlanListTop())
    UI.plist:SetSize(pw - 2 * PAD, listH)
    local off = UI.planOff or 0
    for i, row in ipairs(UI.planRows or {}) do
        local vy = (i - 1) * ROW_H - off
        if vy > -ROW_H and vy < listH then
            row:ClearAllPoints()
            row:SetPoint("TOPLEFT", UI.plist, "TOPLEFT", 0, -vy)
            row:Show()
        else
            row:Hide()
        end
    end
    local track, thumb = UI.planTrack, UI.planThumb
    if track and thumb then
        track:ClearAllPoints()
        track:SetPoint("TOPLEFT", UI.plates[4], "TOPRIGHT", -1, 0)
        track:SetPoint("BOTTOMLEFT", UI.plates[4], "BOTTOMRIGHT", -1, 0)
        local maxOff = PlanMaxOff()
        if maxOff <= 0 then
            track:Hide()
        else
            track:Show()
            local trackH = track:GetHeight() - 2
            local totalH = #(UI.planRows or {}) * ROW_H
            local frac = math.min(1, math.max(0, off / maxOff))
            local th = math.max(24, trackH * listH / math.max(1, totalH))
            thumb:SetHeight(th)
            thumb:ClearAllPoints()
            thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
        end
    end
end

local function Ensure()
    local child = TT.child
    if not child then return false end
    if UI.built and UI.host == child then return true end
    UI.host = child
    UI.built = true

    UI.plates = {}
    for i = 1, 4 do
        UI.plates[i] = plate()
    end
    UI.navPlate = plate()
    local sl = TT.scroll and TT.scroll.GetFrameLevel and TT.scroll:GetFrameLevel() or 1
    if type(sl) ~= "number" then sl = 1 end
    for i = 1, 4 do
        UI.plates[i]:SetFrameLevel(sl)
    end
    UI.navPlate:SetFrameLevel(sl)

    UI.treeHeads = {}
    UI.spentFs = {}
    UI.treeIcons = {}
    UI.resetBtns = {}
    for t = 1, 3 do
        local pl = UI.plates[t]
        local ic = pl:CreateTexture(nil, "ARTWORK")
        ic:SetSize(20, 20)
        ic:SetPoint("TOPLEFT", pl, "TOPLEFT", PAD, -6)
        ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        UI.treeIcons[t] = ic
        local nm = MakeFS(pl, 16, C_TEXT, "LEFT")
        nm:SetPoint("LEFT", ic, "RIGHT", 5, 0)
        UI.treeHeads[t] = nm
        local sp = MakeFS(pl, 14, C_GOLD)
        sp:SetPoint("TOPRIGHT", pl, "TOPRIGHT", -PAD - 22, -8)
        UI.spentFs[t] = sp
        local rb = NewButton(pl, nil, 19, 19, 14)
        rb:SetPoint("TOPRIGHT", pl, "TOPRIGHT", -PAD, -4)
        rb:SetNormalTexture("Interface\\AddOns\\DungeonsForever\\Media\\TalentReset")
        rb:SetHighlightTexture("Interface\\AddOns\\DungeonsForever\\Media\\TalentReset", "ADD")
        rb.__tree = t
        BindResetBtn(rb)
        UI.resetBtns[t] = rb
        local lineLayer = CreateFrame("Frame", nil, pl)
        lineLayer:SetFrameLevel(sl + 1)
        lineLayer:SetAllPoints()
        UI["lineLayer" .. t] = lineLayer
    end

    local p4 = UI.plates[4]
    local ph = MakeFS(p4, 16, C_TEXT, "LEFT")
    ph:SetPoint("TOPLEFT", p4, "TOPLEFT", PAD, -7)
    ph:SetText(L["加点计划"])
    UI.totalFs = MakeFS(p4, 14, C_DIM, "RIGHT")
    UI.totalFs:SetPoint("TOPRIGHT", p4, "TOPRIGHT", -PAD, -9)
    local dv = p4:CreateTexture(nil, "BORDER")
    dv:SetHeight(1)
    dv:SetPoint("TOPLEFT", p4, "TOPLEFT", PAD, -(HEADER_H - 4))
    dv:SetPoint("TOPRIGHT", p4, "TOPRIGHT", -PAD, -(HEADER_H - 4))
    dv:SetColorTexture(1, 1, 1, 0.10)
    UI.plist = CreateFrame("Frame", nil, p4)
    UI.plist:EnableMouseWheel(true)
    UI.plist:SetScript("OnMouseWheel", function(_, delta)
        local maxOff = PlanMaxOff()
        UI.planOff = math.max(0, math.min((UI.planOff or 0) - delta * 42, maxOff))
        RelayoutPlan()
    end)
    p4:EnableMouseWheel(true)
    p4:SetScript("OnMouseWheel", function(_, delta)
        local maxOff = PlanMaxOff()
        UI.planOff = math.max(0, math.min((UI.planOff or 0) - delta * 42, maxOff))
        RelayoutPlan()
    end)

    local track = CreateFrame("Frame", nil, p4, "BackdropTemplate")
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
    track:SetPoint("TOPLEFT", p4, "TOPRIGHT", -1, 0)
    track:SetPoint("BOTTOMLEFT", p4, "BOTTOMRIGHT", -1, 0)
    track:SetFrameLevel(sl + 15)
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
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local off0 = UI.planOff or 0
        self:SetScript("OnUpdate", function()
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxOff = PlanMaxOff()
            UI.planOff = math.min(maxOff, math.max(0, off0 + (cy0 - cy) / span * maxOff))
            RelayoutPlan()
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    UI.planTrack, UI.planThumb = track, thumb

    UI.planPop = plate()
    UI.planPop:SetFrameLevel(sl + 15)
    UI.planPop:Hide()

    UI.presetBtns = nil
    UI.actBtns = {}
    local function actBtn(label, onClick, size)
        local bt = NewButton(UI.navPlate, label, 64, 24, size or 14)
        bt:SetScript("OnClick", onClick)
        bt:Hide()
        UI.actBtns[#UI.actBtns + 1] = bt
        return bt
    end
    actBtn(L["清空模拟"], function()
        UI.mock = { pts = { {}, {}, {} } }
        Refresh()
        ns.PlaySound(1)
    end)
    UI.viewBtn = NewButton(p4, L["实时"], 64, 24, 14)
    UI.viewBtn:SetPoint("LEFT", ph, "RIGHT", 8, 0)
    UI.viewBtn:SetScript("OnClick", function()
        UI.planViewMode = UI.planViewMode == "plan" and "live" or "plan"
        UI.planOff = 0
        Refresh()
    end)
    UI.seqBtn = actBtn("", function()
        local t = TalDB()
        t.seqOn = not SeqOn()
        Refresh()
    end)
    local liveBtn = actBtn(L["一键加点"], function()
        UI.LiveApplyPlan()
    end, 14)
    liveBtn.__live = true
    actBtn(L["保存方案"], function()
        local bl = BuildsOf()
        bl[#bl + 1] = { name = format(L["我的方案%d"], #bl + 1), alloc = CopyAlloc(UI.mock.pts) }
        if #bl > 20 then table.remove(bl, 1) end
        ns.PlaySound(1)
    end)
    actBtn(L["载入方案"], function()
        if UI.planPop and UI.planPop:IsShown() then
            UI.planPop:Hide()
        else
            OpenPlanPop()
        end
    end)
    UI.loadBtn = UI.actBtns[#UI.actBtns]
    actBtn(L["导入"], function() ShowImport() end)
    actBtn(L["导出"], function() ShowExport() end)
    return true
end

local function LayoutPlates()
    local cw, pw = ColW(), PlanW()
    local bh = PlateH()
    local y = TT.MODE_TOP
    UI.navPlate:ClearAllPoints()
    UI.navPlate:SetPoint("TOPLEFT", TT.page, "TOPLEFT", TT.RIGHT_X, -y)
    UI.navPlate:SetSize(TT.RIGHT_W, NAV_H)
    UI.navPlate:Show()
    y = y + NAV_H + GAP
    UI.plateY = y
    for i = 1, 3 do
        local pl = UI.plates[i]
        pl:ClearAllPoints()
        pl:SetPoint("TOPLEFT", TT.page, "TOPLEFT", TT.RIGHT_X + (i - 1) * (cw + GAP), -y)
        pl:SetSize(cw, bh)
    end
    local pl = UI.plates[4]
    pl:ClearAllPoints()
    pl:SetPoint("TOPLEFT", TT.page, "TOPLEFT", TT.RIGHT_X + 3 * (cw + GAP), -y)
    pl:SetSize(pw, bh)
end

function UI.Hide()
    if UI.built then
        for i = 1, 4 do UI.plates[i]:Hide() end
        UI.navPlate:Hide()
        if UI.planPop then UI.planPop:Hide() end
        ResetNodes()
        HideTip()
    end
end

local function RenderNodes()
    local data = TD and UI.cls and TD[UI.cls]
    if not data then return end
    UI.nodeOf = {}
    local cw = ColW()
    local innerW = cw - 2 * PAD
    local gridTop = HEADER_H + 8
    local sl = UI.plates[1]:GetFrameLevel() or 1
    for t = 1, 3 do
        local tree = data.trees[t]
        UI.nodeOf[t] = {}
        if tree then
            tree.__ti = t
            local maxRow, maxCol = 1, 1
            for _, nd in ipairs(tree.nodes) do
                if nd.row > maxRow then maxRow = nd.row end
                if nd.col > maxCol then maxCol = nd.col end
            end
            local avail = PlateH() - gridTop - 8
            local pitch = 56
            if maxRow > 1 then
                pitch = math.floor((avail - ICON) / (maxRow - 1))
            end
            if pitch > 64 then pitch = 64 end
            if pitch < 44 then pitch = 44 end
            local step = maxCol > 1 and math.floor((innerW - ICON) / (maxCol - 1)) or 0
            local layer = UI["lineLayer" .. t]
            for i, nd in ipairs(tree.nodes) do
                local btn = TakeNode(UI.plates[t])
                btn:SetParent(UI.plates[t])
                local x = PAD + (maxCol > 1 and (nd.col - 1) * step or (innerW - ICON) / 2)
                local y = gridTop + (nd.row - 1) * pitch
                btn:ClearAllPoints()
                btn:SetPoint("TOPLEFT", UI.plates[t], "TOPLEFT", x, -y)
                btn:SetFrameLevel(sl + 2)
                btn.iconTex:SetTexture("Interface\\Icons\\" .. tostring(nd.icon))
                btn:SetScript("OnEnter", function(self) NodeTip(self, tree, nd, (UI.mock.pts[t][i] or 0)) end)
                btn:SetScript("OnLeave", HideTip)
                btn:SetScript("OnClick", function(_, key)
                    local pts = UI.mock.pts[t]
                    if key == "RightButton" then
                        if (pts[i] or 0) > 0 then
                            pts[i] = pts[i] - 1
                            if pts[i] == 0 then pts[i] = nil end
                        end
                    else
                        local p = pts[i] or 0
                        if p < nd.max and GateOK(t, nd.row) then
                            pts[i] = p + 1
                        end
                    end
                    HideTip()
                    Refresh()
                    NodeTip(btn, tree, nd, pts[i] or 0)
                end)
                UI.nodeOf[t][i] = btn
            end
            if layer then
                for i, nd in ipairs(tree.nodes) do
                    if nd.req and tree.nodes[nd.req] and UI.nodeOf[t][nd.req] then
                        local src = tree.nodes[nd.req]
                        local scx = PAD + (maxCol > 1 and (src.col - 1) * step or (innerW - ICON) / 2) + ICON / 2
                        local scy = gridTop + (src.row - 1) * pitch + ICON / 2
                        local tcx = PAD + (maxCol > 1 and (nd.col - 1) * step or (innerW - ICON) / 2) + ICON / 2
                        local tcy = gridTop + (nd.row - 1) * pitch + ICON / 2
                        local topY = scy + ICON / 2 + 3
                        local botY = tcy - ICON / 2 - 4
                        if botY - topY >= 4 then
                            local midY = math.floor((topY + botY) / 2)
                            local function bar(cx, cy, w, h)
                                local tex = TakeLine(layer)
                                tex:SetVertexColor(LINE_C, LINE_C, LINE_C, 0.9)
                                tex:ClearAllPoints()
                                tex:SetPoint("TOPLEFT", layer, "TOPLEFT", cx - w / 2, -cy)
                                tex:SetWidth(w)
                                tex:SetHeight(h)
                            end
                            if math.abs(scx - tcx) < 1 then
                                bar(scx, topY, 2, botY - topY)
                            else
                                bar(scx, topY, 2, midY - topY)
                                bar((scx + tcx) / 2, midY, math.abs(tcx - scx) + 2, 2)
                                bar(tcx, midY, 2, botY - midY)
                            end
                            local dot = TakeLine(layer)
                            dot:SetVertexColor(LINE_C + 0.06, LINE_C + 0.06, LINE_C + 0.06, 0.95)
                            dot:ClearAllPoints()
                            dot:SetPoint("TOPLEFT", layer, "TOPLEFT", tcx - 3, -(botY - 1))
                            dot:SetWidth(6)
                            dot:SetHeight(6)
                        end
                    end
                end
            end
        end
    end
end

Rebuild = function()
    local data = TD and UI.cls and TD[UI.cls]
    ResetNodes()
    UI.nodeOf = nil
    UI.planRows = nil
    if UI.plist then
        for _, f in ipairs({ UI.plist:GetChildren() }) do f:Hide() end
    end
    if not data then
        for i = 1, 4 do UI.plates[i]:Show() end
        UI.totalFs:SetText(L["该职业天赋数据待同步"])
        if UI.plist then UI.plist:Hide() end
        for _, bt in ipairs(UI.actBtns or {}) do bt:Hide() end
        return
    end
    if UI.plist then UI.plist:Show() end
    for t = 1, 3 do
        local tree = data.trees[t]
        if tree then
            UI.treeHeads[t]:SetText(tree.name)
            UI.treeHeads[t]:Show()
            local ic = UI.treeIcons[t]
            ic:SetTexture("Interface\\Icons\\" .. tostring(tree.icon))
            ic:Show()
            local rb = UI.resetBtns[t]
            rb.__tree = t
            rb:Show()
        else
            UI.treeHeads[t]:SetText("")
            UI.treeIcons[t]:Hide()
            UI.resetBtns[t]:Hide()
        end
    end
    local plans = TP and TP[UI.cls] or {}
    if UI.seqBtn then
        UI.seqBtn:SetText(SeqOn() and L["加点顺序显示:开"] or L["加点顺序显示:关"])
        SetButtonSelected(UI.seqBtn, SeqOn())
        local sf = UI.seqBtn:GetFontString()
        if sf then
            if SeqOn() then sf:SetTextColor(1, 1, 1, 1) else sf:SetTextColor(Unpack(C_GREY)) end
        end
    end
    if UI.viewBtn then
        UI.viewBtn:SetText(UI.planViewMode == "plan" and L["计划"] or L["实时"])
        SetButtonSelected(UI.viewBtn, UI.planViewMode == "plan")
        local vf = UI.viewBtn:GetFontString()
        if vf then
            if UI.planViewMode == "plan" then vf:SetTextColor(1, 1, 1, 1) else vf:SetTextColor(Unpack(C_GREY)) end
        end
    end
    local myCls = (UnitClass and select(2, UnitClass("player"))) or nil
    local liveBtn
    local x = PAD
    for i = #UI.actBtns, 1, -1 do
        local bt = UI.actBtns[i]
        if bt.__live then
            liveBtn = bt
            bt:Hide()
        else
            local label = bt:GetText() or ""
            local w = 56
            local fs = bt:GetFontString()
            if fs and fs.GetStringWidth and label ~= "" then
                w = math.max(34, fs:GetStringWidth() + 18)
            end
            bt:SetWidth(w)
            bt:ClearAllPoints()
            bt:SetPoint("TOPRIGHT", UI.navPlate, "TOPRIGHT", -x, -(NAV_H - 20) / 2)
            bt:Show()
            x = x + w + 8
        end
    end
    if liveBtn then
        if UI.cls == myCls then
            local fs = liveBtn:GetFontString()
            local w = 56
            if fs and fs.GetStringWidth then w = math.max(34, fs:GetStringWidth() + 18) end
            liveBtn:SetWidth(w)
            liveBtn:ClearAllPoints()
            liveBtn:SetPoint("TOPLEFT", UI.navPlate, "TOPLEFT", PAD, -(NAV_H - 20) / 2)
            liveBtn:Show()
        else
            liveBtn:Hide()
        end
    end
    if UI.seqBtn then
        SetButtonSelected(UI.seqBtn, SeqOn())
        local sfs = UI.seqBtn:GetFontString()
        if sfs then
            if SeqOn() then sfs:SetTextColor(1, 1, 1, 1) else sfs:SetTextColor(Unpack(C_GREY)) end
        end
    end
    if UI.viewBtn then
        SetButtonSelected(UI.viewBtn, UI.planViewMode == "plan")
        local vfs = UI.viewBtn:GetFontString()
        if vfs then
            if UI.planViewMode == "plan" then vfs:SetTextColor(1, 1, 1, 1) else vfs:SetTextColor(Unpack(C_GREY)) end
        end
    end
    RenderNodes()
    UpdatePlanRows()
    Refresh()
end

function UI.Render()
    if not TD then return end
    if not Ensure() then return end
    local cls = TT.PaintHeader()
    if not cls then return end
    UI.cls = cls
    TalDB()
    LayoutPlates()
    for i = 1, 4 do UI.plates[i]:Show() end
    local myKey = (UnitClass and select(2, UnitClass("player"))) or nil
    if not UI.mock or UI.mockCls ~= cls then
        UI.mockCls = cls
        ApplyPreset(1)
        UI.liveBase = (cls == myKey) and ReadLiveTalents() or nil
        UI.hl = nil
        UI.planOff = 0
    end
    if UI.viewBtn then
        UI.viewBtn:SetShown(cls == myKey)
    end
    Rebuild()
end
