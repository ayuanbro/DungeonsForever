local _, ns = ...

if not ns.IsTitan then return end

local NP = {}
ns.NativeTalentPage = NP

local L = ns.L
local TD = ns.TalentTrees
local TP = ns.TalentPlans

local MAX_PT = 51
local COLW, GX, TOP = 303, 41, 50
local GRID_Y, ROW_STEP, NODE_SIZE = 200, 60, 40
local LIST_W, LIST_ROW, LIST_STEP = 220, 22, 25
local PLAN_ROWS, SKILL_ROWS = 7, 6

local U0, U1, V0, V1 = 0.00049, 0.99951, 0.00049, 0.57520

local ART = {
    warrior = 'Interface\\TalentFrame\\TalentBackgroundWarrior',
    paladin = 'Interface\\TalentFrame\\TalentBackgroundPaladin',
    hunter = 'Interface\\TalentFrame\\TalentBackgroundHunter',
    rogue = 'Interface\\TalentFrame\\TalentBackgroundRogue',
    priest = 'Interface\\TalentFrame\\TalentBackgroundPriest',
    shaman = 'Interface\\TalentFrames\\TalentBackgroundShaman',
    mage = 'Interface\\TalentFrame\\TalentBackgroundMage',
    warlock = 'Interface\\TalentFrame\\TalentBackgroundWarlock',
    druid = 'Interface\\TalentFrame\\TalentBackgroundDruid',
}

local NODE_ART = {
    learned = 'talents-node-square-yellow',
    available = 'talents-node-square-green',
    locked = 'talents-node-square-locked',
    disabled = 'talents-node-square-gray',
}

local WHITE = 'Interface\\Buttons\\WHITE8x8'
local BRAND = 'Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever'
local TAB_LOGO = '|TInterface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp:17:17:0:0:128:128:0:128:0:128|t '

local CT, Traits = _G.C_ClassTalents, _G.C_Traits

local body, strip, planTitle, planRows, skillTitle, skillRows
local headers, nodes = {}, {}
local applyBtn, resetBtn

local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local t = DungeonsForeverDB.talentSim
    if not t then
        t = {}
        DungeonsForeverDB.talentSim = t
    end
    if not t.builds then t.builds = {} end
    return t
end

local function ClassKey()
    local _, token = UnitClass('player')
    local key = token and string.lower(token)
    if key and TD and TD[string.upper(token)] then return key end
    return nil
end

local function Data()
    local cls = NP.cls
    return cls and TD and TD[string.upper(cls)]
end

local function Plans()
    local cls = NP.cls
    return cls and TP and TP[string.upper(cls)]
end

local function MaxPoints()
    local lv = UnitLevel('player') or 0
    return math.min(MAX_PT, math.max(0, lv - 9))
end

local function TreeSpent(t)
    local s = 0
    local p = NP.pts and NP.pts[t]
    if p then
        for _, v in pairs(p) do s = s + v end
    end
    return s
end

local function TotalSpent()
    return TreeSpent(1) + TreeSpent(2) + TreeSpent(3)
end

local function GateOK(t, row)
    if row <= 1 then return true end
    return TreeSpent(t) >= (row - 1) * 5
end

local function NodeOf(t, i)
    local d = Data()
    local tree = d and d.trees and d.trees[t]
    return tree and tree.nodes and tree.nodes[i]
end

local Refresh

local function NewText(parent, size, r, g, b, anchor)
    local fs = parent:CreateFontString(nil, 'OVERLAY', 'GameFontNormal')
    fs:SetFont(ns.FONT, size, '')
    fs:SetJustifyH(anchor or 'LEFT')
    fs:SetTextColor(r, g, b)
    return fs
end

local function BuildBackground(b)
    local d = Data()
    local art = d and ART[d.key] or ART.rogue
    for i = 1, 4 do
        local t = b:CreateTexture(nil, 'OVERLAY', nil, 1)
        t:SetPoint('TOPLEFT', b, 'TOPLEFT', (i - 1) * COLW, 0)
        t:SetSize(COLW, 595)
        t:SetTexture(art)
        local a, c = U0 + (U1 - U0) * (i - 1) / 3, U0 + (U1 - U0) * i / 3
        if i == 4 then
            t:SetTexCoord(c, a, V0, V1)
            t:SetVertexColor(0.62, 0.62, 0.62, 1)
        else
            t:SetTexCoord(a, c, V0, V1)
        end
    end
    for i = 1, 3 do
        local dv = b:CreateTexture(nil, 'OVERLAY', nil, 3)
        dv:SetAtlas('Talents-divider-vertical-c60')
        dv:SetSize(2, 468)
        dv:SetPoint('TOPLEFT', b, 'TOPLEFT', i * COLW - 1, -88)
    end
    local bl = b:CreateTexture(nil, 'OVERLAY', nil, 4)
    bl:SetAtlas('Talents-divider-left-c60')
    bl:SetSize(591, 56)
    bl:SetPoint('TOPLEFT', b, 'TOPLEFT', 15, 0)
    local br = b:CreateTexture(nil, 'OVERLAY', nil, 4)
    br:SetAtlas('Talents-divider-right-c60')
    br:SetSize(595, 56)
    br:SetPoint('TOPLEFT', b, 'TOPLEFT', 606, 0)
    local bd = b:CreateTexture(nil, 'OVERLAY', nil, 6)
    bd:SetAtlas('Talents-inner-frame-c60')
    bd:SetPoint('TOPLEFT', b, 'TOPLEFT', -2, -4)
    bd:SetSize(1216, 603)
end

local function BuildHeader(idx, icon, name, withPoints)
    local h = CreateFrame('Frame', nil, body, 'ClassTalentTreeHeaderTemplate')
    h:SetPoint('TOPLEFT', body, 'TOPLEFT', (idx - 1) * COLW + GX + 21, -72)
    h.Icon:SetTexture(icon)
    h.Name:SetText(name)
    h.Divider:ClearAllPoints()
    h.Divider:SetPoint('TOPLEFT', body, 'TOPLEFT', (idx - 1) * COLW + 18, -76)
    h.Divider:SetSize(266, 48)
    if not withPoints then
        h.MainRing:Hide()
        h.TextBackground:Hide()
        h.Text:Hide()
    else
        h.Text:SetText('0')
    end
    h:Show()
    headers[idx] = h
    return h
end

local function BuildNode(t, i, nd)
    local b = CreateFrame('Button', nil, body)
    b:SetSize(NODE_SIZE, NODE_SIZE)
    b:SetPoint('TOPLEFT', body, 'TOPLEFT',
        (t - 1) * COLW + GX + (nd.col - 1) * ROW_STEP,
        -(GRID_Y + (nd.row - 1) * ROW_STEP - TOP))
    b:RegisterForClicks('LeftButtonUp', 'RightButtonUp')

    local shadow = b:CreateTexture(nil, 'BACKGROUND')
    shadow:SetAtlas('talents-node-square-shadow')
    shadow:SetSize(78, 78)
    shadow:SetPoint('CENTER')

    local icon = b:CreateTexture(nil, 'ARTWORK')
    icon:SetSize(34, 34)
    icon:SetPoint('CENTER')
    icon:SetTexture('Interface\\Icons\\' .. tostring(nd.icon))
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)

    local ring = b:CreateTexture(nil, 'OVERLAY')
    ring:SetAtlas(NODE_ART.locked)
    ring:SetSize(NODE_SIZE, NODE_SIZE)
    ring:SetPoint('CENTER')

    local hl = b:CreateTexture(nil, 'HIGHLIGHT')
    hl:SetTexture(WHITE)
    hl:SetVertexColor(1, 1, 1, 0.12)
    hl:SetAllPoints()

    local rk = b:CreateFontString(nil, 'OVERLAY')
    rk:SetFont(ns.FONT, 16, 'OUTLINE, THICKOUTLINE')
    rk:SetJustifyH('CENTER')
    rk:SetTextColor(0.10, 1.00, 0.10)
    rk:SetPoint('BOTTOM', b, 'BOTTOM', 11, 4)

    local plus = b:CreateTexture(nil, 'OVERLAY', nil, 2)
    plus:SetAtlas('talents-icon-learnableplus')
    plus:SetSize(19, 18)
    plus:SetPoint('BOTTOMLEFT', b, 'BOTTOMLEFT', -3, -3)
    plus:Hide()

    b.nd = nd
    b.tree = t
    b.idx = i
    b.ring = ring
    b.rank = rk
    b.plus = plus
    b.icon = icon

    b:SetScript('OnClick', function(self, button)
        local pts = NP.pts[self.tree]
        local cur = pts[self.idx] or 0
        if button == 'RightButton' then
            if cur > 0 then
                pts[self.idx] = cur - 1
                if pts[self.idx] <= 0 then pts[self.idx] = nil end
                Refresh()
            end
            return
        end
        if cur >= self.nd.max then return end
        if not GateOK(self.tree, self.nd.row) then return end
        if TotalSpent() >= MaxPoints() then return end
        pts[self.idx] = cur + 1
        Refresh()
    end)

    b:SetScript('OnEnter', function(self)
        GameTooltip:SetOwner(self, 'ANCHOR_RIGHT')
        GameTooltip:ClearLines()
        local p = (NP.pts[self.tree] or {})[self.idx] or 0
        GameTooltip:AddLine(self.nd.n, 1, 0.82, 0)
        GameTooltip:AddLine(string.format(L['第%d行第%d列'], self.nd.row, self.nd.col), 0.7, 0.75, 0.82)
        if self.nd.passive then GameTooltip:AddLine(L['被动'], 0.55, 0.78, 1) end
        local di = math.min(math.max(p, 1), #self.nd.desc)
        if self.nd.desc[di] then
            GameTooltip:AddLine(self.nd.desc[di], 0.9, 0.92, 0.96, true)
        end
        if p < self.nd.max and self.nd.desc[p + 1] then
            GameTooltip:AddLine(string.format(L['下一级：%s'], self.nd.desc[p + 1]), 0.6, 0.65, 0.75, true)
        end
        if p == 0 and not GateOK(self.tree, self.nd.row) then
            GameTooltip:AddLine(string.format(L['需本系再投入 %d 点'], (self.nd.row - 1) * 5 - TreeSpent(self.tree)), 0.95, 0.45, 0.4, true)
        end
        GameTooltip:Show()
    end)
    b:SetScript('OnLeave', function() GameTooltip:Hide() end)

    return b
end

local function BuildNodes()
    local d = Data()
    if not d then return end
    for t = 1, 3 do
        nodes[t] = {}
        local list = d.trees[t] and d.trees[t].nodes or {}
        for i = 1, #list do
            local nd = list[i]
            if nd.row and nd.col then
                nodes[t][i] = BuildNode(t, i, nd)
            end
        end
    end
end

local function BuildList(parent, y, rows)
    local out = {}
    for i = 1, rows do
        local r = CreateFrame('Frame', nil, parent)
        r:SetSize(LIST_W, LIST_ROW)
        r:SetPoint('TOPLEFT', parent, 'TOPLEFT', 3 * COLW + GX, -(y + (i - 1) * LIST_STEP - TOP))
        local bg = r:CreateTexture(nil, 'BACKGROUND')
        bg:SetAllPoints()
        bg:SetTexture(WHITE)
        bg:SetVertexColor(1, 1, 1, 0.05)
        r.ic = r:CreateTexture(nil, 'ARTWORK')
        r.ic:SetSize(16, 16)
        r.ic:SetPoint('LEFT', r, 'LEFT', 3, 0)
        r.ic:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        r.lv = NewText(r, 14, 0.62, 0.68, 0.78, 'LEFT')
        r.lv:SetPoint('LEFT', r, 'LEFT', 22, 0)
        r.lv:SetWidth(48)
        r.nm = NewText(r, 14, 0.92, 0.92, 0.92, 'LEFT')
        r.nm:SetPoint('LEFT', r, 'LEFT', 72, 0)
        r.nm:SetWidth(106)
        r.nm:SetWordWrap(false)
        r.rk = NewText(r, 14, 1, 1, 1, 'RIGHT')
        r.rk:SetPoint('RIGHT', r, 'RIGHT', -4, 0)
        out[i] = r
    end
    return out
end

local function BuildLists()
    planTitle = NewText(body, 14, 1, 0.82, 0, 'LEFT')
    planTitle:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX - 2, -(GRID_Y - 18 - TOP))
    planTitle:SetText(L['加点计划'])

    planRows = BuildList(body, GRID_Y, PLAN_ROWS)

    local sep = body:CreateTexture(nil, 'OVERLAY')
    sep:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX, -(GRID_Y + PLAN_ROWS * LIST_STEP + 8 - TOP))
    sep:SetSize(LIST_W, 1)
    sep:SetTexture(WHITE)
    sep:SetVertexColor(1, 1, 1, 0.14)

    skillTitle = NewText(body, 14, 1, 0.82, 0, 'LEFT')
    skillTitle:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX - 2, -(GRID_Y + PLAN_ROWS * LIST_STEP + 20 - TOP))
    skillTitle:SetText(L['可学习的技能'])

    skillRows = BuildList(body, GRID_Y + PLAN_ROWS * LIST_STEP + 40, SKILL_ROWS)
end

local function MakeButton(parent, w, text, x, y)
    local b = CreateFrame('Button', nil, parent, 'UIPanelButtonNoTooltipTemplate')
    b:SetSize(w, 22)
    b:SetPoint('TOPLEFT', parent, 'TOPLEFT', x, y)
    b:SetText(text)
    return b
end

local function PlanList()
    local plans = Plans() or {}
    local out = {}
    for i = 1, #plans do
        out[#out + 1] = { label = plans[i].name or string.format(L['方案%d'], i), plan = plans[i], idx = i }
    end
    local bl = DB().builds[NP.cls] or {}
    for i = 1, #bl do
        out[#out + 1] = { label = bl[i].name, alloc = bl[i].alloc, idx = #plans + i }
    end
    return out
end

local function ApplyAlloc(alloc)
    NP.pts = { {}, {}, {} }
    if type(alloc) ~= 'table' then return end
    for t = 1, 3 do
        local src = alloc[t] or {}
        for i, v in pairs(src) do
            local nd = NodeOf(t, i)
            local r = tonumber(v) or 0
            if nd and r > 0 then
                NP.pts[t][i] = math.min(r, nd.max)
            end
        end
    end
end

local function Encode()
    local segs = { '', '', '' }
    for t = 1, 3 do
        local pts = NP.pts[t]
        local maxI = 0
        for i in pairs(pts) do if i > maxI then maxI = i end end
        local parts = {}
        for i = 1, maxI do parts[i] = tostring(pts[i] or 0) end
        while #parts > 0 and parts[#parts] == '0' do parts[#parts] = nil end
        segs[t] = table.concat(parts)
    end
    return segs[1] .. '-' .. segs[2] .. '-' .. segs[3]
end

local function Decode(str)
    local segs = { strsplit('-', tostring(str or '')) }
    local alloc = { {}, {}, {} }
    for t = 1, 3 do
        local s = tostring(segs[t] or '')
        for i = 1, #s do
            local d = tonumber(s:sub(i, i))
            if d and d > 0 then alloc[t][i] = d end
        end
    end
    return alloc
end

local function SeqOf(plan)
    if plan and plan.seq then return plan.seq end
    local plans = Plans() or {}
    local first = plans[1]
    return first and first.seq
end

local function PendingSeq()
    local seq = SeqOf(NP.plan)
    local out = {}
    if not seq then return out end
    local need = {}
    local k = 0
    local curLv = (UnitLevel and UnitLevel('player')) or 0
    local baseSpent = TotalSpent()
    for i = 1, #seq do
        local it = seq[i]
        local nd = NodeOf(it[1], it[2])
        if nd then
            local key = it[1] * 100 + it[2]
            local n = (need[key] or 0) + 1
            need[key] = n
            local have = (NP.pts[it[1]] or {})[it[2]] or 0
            if n > have then
                k = k + 1
                local lv = math.max(curLv, baseSpent + k + 9)
                out[#out + 1] = { t = it[1], i = it[2], nd = nd, lv = lv, target = n,
                    over = lv > 60, first = n == 1 }
            end
        end
    end
    return out
end

local function CurrencyParts()
    local T = NP.frame
    local cd = T and T.ClassCurrencyDisplay
    if not cd then return nil, nil end
    local label
    local regs = { cd:GetRegions() }
    for i = 1, #regs do
        local r = regs[i]
        if r.GetObjectType and r:GetObjectType() == 'FontString' then label = r break end
    end
    local amount
    local kids = { cd:GetChildren() }
    for i = 1, #kids do
        local r2 = { kids[i]:GetRegions() }
        for j = 1, #r2 do
            local r = r2[j]
            if r.GetObjectType and r:GetObjectType() == 'FontString' then amount = r break end
        end
        if amount then break end
    end
    return label, amount
end

local function CurrencyCard(on)
    local T = NP.frame
    if not (T and T.ClassCurrencyDisplay) then return end
    local label, amount = CurrencyParts()
    if not label then return end
    if not NP.curOrig then NP.curOrig = label:GetText() end
    if on then
        label:SetText(L['已投入天赋'])
        if amount then amount:SetText(TotalSpent()) end
    else
        if NP.curOrig then label:SetText(NP.curOrig) end
        if T.RefreshClassCurrencyDisplay then T:RefreshClassCurrencyDisplay() end
    end
end

local function UpdateLists()
    local pending = PendingSeq()
    for i = 1, PLAN_ROWS do
        local row = planRows[i]
        local p = pending[i]
        if p then
            row.ic:SetTexture('Interface\\Icons\\' .. tostring(p.nd.icon))
            row.lv:SetText(tostring(p.lv))
            row.nm:SetText(p.nd.n)
            if p.over then
                row.rk:SetText(L['点不够'])
            else
                local have = (NP.pts[p.t] or {})[p.i] or 0
                row.rk:SetText(have .. '/' .. p.nd.max)
            end
            row:Show()
        else
            row:Hide()
        end
    end
    if planTitle then
        planTitle:SetText(string.format(L['实时 · %d 点'], TotalSpent()))
    end

    local shown = 0
    for k = 1, #pending do
        local p = pending[k]
        if shown < SKILL_ROWS and p.first and not p.nd.passive then
            shown = shown + 1
            local row = skillRows[shown]
            row.ic:SetTexture('Interface\\Icons\\' .. tostring(p.nd.icon))
            row.lv:SetText(tostring(p.lv))
            row.nm:SetText(p.nd.n)
            row.rk:SetText('')
            row:Show()
        end
    end
    for i = shown + 1, SKILL_ROWS do skillRows[i]:Hide() end

    if skillTitle then
        skillTitle:SetText(shown > 0 and L['可学习的技能'] or L['暂无新的主动技能'])
    end
end

Refresh = function()
    if not body then return end
    local unspent = MaxPoints() - TotalSpent()
    for t = 1, 3 do
        local d = Data()
        local tree = d and d.trees[t]
        if headers[t] then
            headers[t].Name:SetText(tree and tree.name or '')
            headers[t].Text:SetText(TreeSpent(t))
            headers[t].Icon:SetTexture('Interface\\Icons\\' .. tostring(tree and tree.icon or 'INV_Misc_QuestionMark'))
        end
        local list = nodes[t] or {}
        for i = 1, #list do
            local b = list[i]
            if b then
                local p = (NP.pts[t] or {})[i] or 0
                local gate = GateOK(t, b.nd.row)
                local state
                if p > 0 then
                    if p >= b.nd.max then
                        state = 'max'
                    elseif unspent > 0 and gate then
                        state = 'selectable'
                    else
                        state = 'normal'
                    end
                else
                    state = gate and unspent > 0 and 'selectable' or 'locked'
                end
                if p > 0 then
                    b.rank:SetText(p)
                    b.rank:Show()
                else
                    b.rank:Hide()
                end
                if state == 'selectable' then
                    b.rank:SetTextColor(0.10, 1.00, 0.10)
                    b.ring:SetAtlas(NODE_ART.available)
                elseif state == 'locked' then
                    b.rank:SetTextColor(0.50, 0.50, 0.50)
                    b.ring:SetAtlas(NODE_ART.locked)
                else
                    b.rank:SetTextColor(1.00, 0.82, 0.00)
                    b.ring:SetAtlas(NODE_ART.learned)
                end
                b.icon:SetDesaturated(state == 'locked')
                b.plus:SetShown(state == 'selectable' and p < b.nd.max)
            end
        end
    end
    if planTitle then
        planTitle:SetText(string.format(L['剩余 %d / %d 点 · %s'], MaxPoints() - TotalSpent(), MaxPoints(),
            NP.plan and NP.plan.name or L['自定义']))
    end
    UpdateLists()
    CurrencyCard(true)
end

local function LiveRead()
    if type(CT) ~= 'table' or type(Traits) ~= 'table' then return nil end
    local ok, configID = pcall(CT.GetActiveConfigID)
    if not ok or not configID then return nil end
    local ok2, ci = pcall(Traits.GetConfigInfo, configID)
    if not ok2 or type(ci) ~= 'table' or not ci.treeIDs or not ci.treeIDs[1] then return nil end
    local ok3, list = pcall(Traits.GetTreeNodes, ci.treeIDs[1])
    if not ok3 or type(list) ~= 'table' or #list == 0 then return nil end
    local byName, spent = {}, 0
    for _, nodeID in ipairs(list) do
        local ok4, n = pcall(Traits.GetNodeInfo, configID, nodeID)
        if ok4 and type(n) == 'table' then
            spent = spent + (tonumber(n.ranksPurchased) or 0)
            local eid = n.entryIDs and n.entryIDs[1]
            if eid then
                local ok5, entry = pcall(Traits.GetEntryInfo, configID, eid)
                if ok5 and type(entry) == 'table' and entry.definitionID then
                    local ok6, def = pcall(Traits.GetDefinitionInfo, entry.definitionID)
                    if ok6 and type(def) == 'table' then
                        local name = def.overrideName
                        if not name and def.spellID and C_Spell and C_Spell.GetSpellInfo then
                            local ok7, sp = pcall(C_Spell.GetSpellInfo, def.spellID)
                            if ok7 and type(sp) == 'table' then name = sp.name end
                        end
                        if name and not byName[name] then
                            byName[name] = { id = nodeID, rank = tonumber(n.ranksPurchased) or 0 }
                        end
                    end
                end
            end
        end
    end
    return { configID = configID, byName = byName, spent = spent }
end

NP.LiveRead = LiveRead

function NP.SyncFromLive()
    local read = LiveRead()
    if not read then return false end
    local d = Data()
    if not d then return false end
    NP.pts = { {}, {}, {} }
    for t = 1, 3 do
        local list = d.trees[t].nodes
        for i = 1, #list do
            local live = read.byName[list[i].n]
            if live and live.rank > 0 then
                NP.pts[t][i] = live.rank
            end
        end
    end
    return true
end

local function DoApply(read, queue, cap)
    local purchased, failed = 0, nil
    for _, it in ipairs(queue) do
        if purchased >= cap then break end
        local live = read.byName[it.nd.n]
        if live then
            local left = it.want - live.rank
            for _ = 1, left do
                if purchased >= cap then break end
                local ok, r = pcall(Traits.PurchaseRank, read.configID, live.id)
                if not ok or r == false then
                    failed = it.nd.n
                    break
                end
                purchased = purchased + 1
            end
        end
        if failed then break end
    end
    if failed then
        pcall(Traits.RollbackConfig, read.configID)
        print('|cffff5040[天赋]|r ' .. string.format(L['学习 %s 失败（已回滚）'], failed))
        return
    end
    local ok, r = pcall(Traits.CommitConfig, read.configID)
    if not ok or r == false then
        pcall(Traits.RollbackConfig, read.configID)
        print('|cffff5040[天赋]|r ' .. L['提交失败（已回滚）'])
        return
    end
    print('|cff46bf72[天赋]|r ' .. string.format(L['已应用到角色，本次 %d 点'], purchased))
    NP.SyncFromLive()
    Refresh()
end

function NP.ApplyLive()
    local read = LiveRead()
    if not read then
        print('|cff46bf72[天赋]|r ' .. L['拿不到角色天赋配置（先打开一次游戏内天赋界面）'])
        return
    end
    local queue, planned = {}, 0
    local seq = SeqOf(NP.plan)
    local seen = {}
    if seq then
        for _, it in ipairs(seq) do
            local nd = NodeOf(it[1], it[2])
            local key = nd and (it[1] .. ':' .. it[2])
            if nd and key and not seen[key] then
                seen[key] = true
                local want = (NP.pts[it[1]] or {})[it[2]] or 0
                local live = read.byName[nd.n]
                local have = live and live.rank or 0
                if want > have then
                    queue[#queue + 1] = { nd = nd, want = want }
                    planned = planned + (want - have)
                end
            end
        end
    end
    for t = 1, 3 do
        local d = Data()
        local list = d and d.trees[t].nodes or {}
        for i = 1, #list do
            local key = t .. ':' .. i
            if not seen[key] then
                seen[key] = true
                local want = (NP.pts[t] or {})[i] or 0
                local live = read.byName[list[i].n]
                local have = live and live.rank or 0
                if want > have then
                    queue[#queue + 1] = { nd = list[i], want = want }
                    planned = planned + (want - have)
                end
            end
        end
    end
    if planned <= 0 then
        print('|cff46bf72[天赋]|r ' .. L['当前方案与角色天赋一致，没有需要学习的点'])
        return
    end
    local cap = MaxPoints() - read.spent
    if cap <= 0 then
        print('|cff46bf72[天赋]|r ' .. L['当前没有可用的天赋点'])
        return
    end
    local n = math.min(planned, cap)
    local msg = string.format(L['将向角色学习 %d 点天赋（可用 %d / 计划 %d）。'], n, cap, planned)
    if n < planned then
        msg = msg .. '\n' .. string.format(L['其余 %d 点需升级后再点「一键加点」。'], planned - n)
    end
    StaticPopupDialogs['DF_TALENT_SIM_APPLY'] = {
        text = msg,
        button1 = L['确定'],
        button2 = L['取消'],
        OnShow = function(self)
            if ns.SkinPopupFont then ns.SkinPopupFont(self) end
        end,
        OnAccept = function() DoApply(read, queue, n) end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show('DF_TALENT_SIM_APPLY')
end

local function ShowPlanMenu(anchor)
    local menu = MenuUtil and MenuUtil.CreateContextMenu and nil
    local rows = PlanList()
    if NP.planMenu then NP.planMenu:Hide() end
    local f = CreateFrame('Frame', nil, UIParent, 'BackdropTemplate')
    f:SetSize(300, math.max(24, #rows * 24) + 12)
    f:SetPoint('TOPLEFT', anchor, 'BOTTOMLEFT', 0, -2)
    f:SetFrameStrata('FULLSCREEN_DIALOG')
    f:SetBackdrop({ bgFile = WHITE, edgeFile = WHITE, edgeSize = 1 })
    f:SetBackdropColor(0.05, 0.05, 0.06, 0.96)
    f:SetBackdropBorderColor(0.7, 0.6, 0.3, 1)
    for i = 1, #rows do
        local r = CreateFrame('Button', nil, f)
        r:SetSize(288, 22)
        r:SetPoint('TOPLEFT', f, 'TOPLEFT', 6, -(6 + (i - 1) * 24))
        r:SetHighlightTexture(WHITE, 'ADD')
        local hl = r:GetHighlightTexture()
        hl:SetVertexColor(1, 1, 1, 0.1)
        local fs = NewText(r, 13, 0.92, 0.92, 0.92, 'LEFT')
        fs:SetPoint('LEFT', r, 'LEFT', 4, 0)
        fs:SetText(rows[i].label)
        local alloc = rows[i].alloc or (rows[i].plan and rows[i].plan.alloc)
        r:SetScript('OnClick', function()
            NP.plan = rows[i].plan or { name = rows[i].label, alloc = alloc }
            ApplyAlloc(alloc)
            f:Hide()
            Refresh()
        end)
    end
    f:EnableMouse(true)
    f:SetScript('OnHide', function() NP.planMenu = nil end)
    NP.planMenu = f
    f:Show()
end

local function ImportDialog()
    StaticPopupDialogs['DF_TALENT_SIM_IMPORT'] = {
        text = L['粘贴天赋串（形如 05-2505-123）：'],
        button1 = L['确定'],
        button2 = L['取消'],
        hasEditBox = true,
        editBoxWidth = 280,
        maxLetters = 240,
        OnShow = function(self)
            if ns.SkinPopupFont then ns.SkinPopupFont(self) end
        end,
        OnAccept = function(self)
            local e = self.EditBox or self.editBox
            local str = e and e:GetText() or ''
            if str ~= '' then
                ApplyAlloc(Decode(str))
                NP.plan = { name = L['导入方案'] }
                Refresh()
            end
        end,
    }
    StaticPopup_Show('DF_TALENT_SIM_IMPORT')
end

local function ExportBox()
    StaticPopupDialogs['DF_TALENT_SIM_EXPORT'] = {
        text = L['当前天赋串（可直接复制）：'],
        button1 = L['关闭'],
        hasEditBox = true,
        editBoxWidth = 280,
        OnShow = function(self)
            if ns.SkinPopupFont then ns.SkinPopupFont(self) end
            local e = self.EditBox or self.editBox
            if e then
                e:SetText(Encode())
                e:HighlightText()
                e:SetFocus()
            end
        end,
        EditBoxOnEscapePressed = function(self) self:GetParent():Hide() end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show('DF_TALENT_SIM_EXPORT')
end

local function SaveBuild()
    StaticPopupDialogs['DF_TALENT_SIM_SAVE'] = {
        text = L['输入方案名'],
        button1 = L['确定'],
        button2 = L['取消'],
        hasEditBox = true,
        editBoxWidth = 240,
        maxLetters = 24,
        OnShow = function(self)
            if ns.SkinPopupFont then ns.SkinPopupFont(self) end
            local e = self.EditBox or self.editBox
            if e then e:SetText(L['我的方案']) end
        end,
        OnAccept = function(self)
            local e = self.EditBox or self.editBox
            local name = e and e:GetText() or ''
            if name == '' then return end
            local cls = NP.cls
            if not cls then return end
            local db = DB()
            db.builds[cls] = db.builds[cls] or {}
            local list = db.builds[cls]
            local alloc = { {}, {}, {} }
            for t = 1, 3 do
                for i, v in pairs(NP.pts[t]) do alloc[t][i] = v end
            end
            list[#list + 1] = { name = name, alloc = alloc }
            print('|cff46bf72[天赋]|r ' .. string.format(L['已保存方案「%s」'], name))
        end,
    }
    StaticPopup_Show('DF_TALENT_SIM_SAVE')
end

local function BuildStrip()
    strip = CreateFrame('Frame', nil, body)
    strip:SetPoint('TOPLEFT', body, 'TOPLEFT', 0, -(66 - TOP))
    strip:SetSize(760, 22)
    strip:SetFrameLevel(1012)

    local bPlan = MakeButton(strip, 96, L['方案'], 40, 0)
    bPlan:SetScript('OnClick', function(self) ShowPlanMenu(self) end)

    local bSave = MakeButton(strip, 96, L['保存'], 144, 0)
    bSave:SetScript('OnClick', function() SaveBuild() end)

    local bImp = MakeButton(strip, 96, L['导入'], 248, 0)
    bImp:SetScript('OnClick', function() ImportDialog() end)

    local bExp = MakeButton(strip, 96, L['导出'], 352, 0)
    bExp:SetScript('OnClick', function() ExportBox() end)

    local bGet = MakeButton(strip, 110, L['获取当前天赋'], 456, 0)
    bGet:SetScript('OnClick', function()
        if NP.SyncFromLive() then
            NP.seeded = true
            Refresh()
            print('|cff46bf72[天赋]|r ' .. L['已读取角色当前天赋'])
        else
            print('|cff46bf72[天赋]|r ' .. L['读取失败（先打开一次游戏内天赋界面）'])
        end
    end)

end

local function BuildApplyButton(T)
    applyBtn = CreateFrame('Button', nil, T, 'UIPanelButtonNoTooltipTemplate')
    applyBtn:SetSize(164, 22)
    applyBtn:SetPoint('TOPLEFT', T, 'TOPLEFT', 524, -651)
    applyBtn:SetFrameLevel(1013)
    applyBtn:SetText(L['一键加点'])
    applyBtn:SetScript('OnClick', function() NP.ApplyLive() end)
    applyBtn:Hide()

    resetBtn = CreateFrame('Button', 'DungeonsForeverTalentReset', T)
    resetBtn:SetSize(25, 25)
    resetBtn:SetPoint('TOPLEFT', T, 'TOPLEFT', 702, -650)
    resetBtn:SetFrameLevel(1013)
    local ic = resetBtn:CreateTexture(nil, 'ARTWORK')
    ic:SetAtlas('talents-button-undo')
    ic:SetSize(21, 20)
    ic:SetPoint('CENTER')
    local hl = resetBtn:CreateTexture(nil, 'HIGHLIGHT')
    hl:SetAtlas('talents-button-undo')
    hl:SetSize(21, 20)
    hl:SetPoint('CENTER')
    hl:SetBlendMode('ADD')
    resetBtn:SetScript('OnClick', function()
        NP.pts = { {}, {}, {} }
        NP.seeded = true
        Refresh()
    end)
    resetBtn:SetScript('OnEnter', function(self)
        GameTooltip:SetOwner(self, 'ANCHOR_RIGHT')
        GameTooltip:SetText(L['重置模拟加点'], 1, 1, 1)
        GameTooltip:Show()
    end)
    resetBtn:SetScript('OnLeave', function() GameTooltip:Hide() end)
    resetBtn:Hide()
end

local function ApplyState(on)
    local T = NP.frame
    if not (T and body) then return end
    local tab = T.TabSystem and T.TabSystem.tabs[NP.tabID]
    if on then
        if not NP.pts then NP.pts = { {}, {}, {} } end
        if not NP.seeded then
            NP.seeded = NP.SyncFromLive() or true
        end
        body:Show()
        if applyBtn then applyBtn:Show() end
        if resetBtn then resetBtn:Show() end
        if T.SetDisabledOverlayShown then T:SetDisabledOverlayShown(false) end
        if T.ActiveSpec then T.ActiveSpec:Hide() end
        if T.ButtonsParent then T.ButtonsParent:Hide() end
        if T.ApplyButton then T.ApplyButton:Hide() end
        if T.ResetButton then T.ResetButton:Hide() end
        if T.UndoButton then T.UndoButton:Hide() end
        if T.treeHeaders then
            for i = 1, #T.treeHeaders do T.treeHeaders[i]:Hide() end
        end
        if tab and tab.SetIsActive then tab:SetIsActive(true) end
    else
        body:Hide()
        if applyBtn then applyBtn:Hide() end
        if resetBtn then resetBtn:Hide() end
        if T.ButtonsParent then T.ButtonsParent:Show() end
        if T.ApplyButton then T.ApplyButton:Show() end
        if T.ActiveSpec then T.ActiveSpec:Show() end
        if T.treeHeaders then
            for i = 1, #T.treeHeaders do T.treeHeaders[i]:Show() end
        end
        if tab and tab.SetIsActive then tab:SetIsActive(false) end
        CurrencyCard(false)
    end
end

NP.ApplyState = ApplyState

function NP.SyncShow()
    local T = NP.frame
    if not (T and body) then return end
    local on = T:GetTab() == NP.tabID
    ApplyState(on)
    if on then Refresh() end
end

function NP.Build(T)
    if body then return end
    NP.frame = T
    NP.cls = ClassKey()
    if not NP.cls or not Data() then return end
    NP.pts = { {}, {}, {} }
    NP.plan = (Plans() or {})[1]

    body = CreateFrame('Frame', 'DungeonsForeverTalentPage', T)
    body:SetSize(1212, 595)
    body:SetPoint('TOPLEFT', T, 'TOPLEFT', 0, -TOP)
    body:SetFrameLevel(1000)
    body:Hide()

    BuildBackground(body)

    local d = Data()
    for t = 1, 3 do
        local tree = d.trees[t]
        BuildHeader(t, 'Interface\\Icons\\' .. tostring(tree.icon), tree.name or '', true)
    end
    BuildHeader(4, BRAND, L['加点计划'], false)

    BuildNodes()
    BuildLists()
    BuildStrip()
    BuildApplyButton(T)

    if T.ClassCurrencyDisplay then T.ClassCurrencyDisplay:SetFrameLevel(1100) end

    if not NP.guard then
        local g = CreateFrame('Frame')
        g:RegisterEvent('PLAYER_TALENT_UPDATE')
        g:RegisterEvent('TRAIT_CONFIG_UPDATED')
        g:RegisterEvent('TRAIT_CONFIG_CREATED')
        g:RegisterEvent('SPELLS_CHANGED')
        g:RegisterEvent('PLAYER_LEVEL_UP')
        g:SetScript('OnEvent', function()
            if NP.frame and body and NP.frame:GetTab() == NP.tabID then
                ApplyState(true)
                Refresh()
            end
        end)
        NP.guard = g
        if hooksecurefunc then
            hooksecurefunc(T, 'RefreshTreeHeaders', function()
                if NP.frame and body and NP.frame:GetTab() == NP.tabID then ApplyState(true) end
            end)
            hooksecurefunc(T, 'InitializeActiveSpec', function()
                if NP.frame and body and NP.frame:GetTab() == NP.tabID then ApplyState(true) end
            end)
            if T.ClassCurrencyDisplay then
                hooksecurefunc(T.ClassCurrencyDisplay, 'SetAmount', function()
                    if NP.frame and body and NP.frame:GetTab() == NP.tabID then CurrencyCard(true) end
                end)
            end
        end
    end

    if not NP.hooked then
        NP.hooked = true
        local ts = T.TabSystem
        if ts and ts.SetTabSelectedCallback then
            ts:SetTabSelectedCallback(function(tabID, isUserAction)
                ClassTalentsFrameMixin.SetTab(T, tabID, isUserAction)
                NP.SyncShow()
            end)
        end
        if hooksecurefunc then
            hooksecurefunc(T, 'SetTab', function() NP.SyncShow() end)
        end
    end

    NP.SyncShow()
end

local function TabLabel()
    return TAB_LOGO .. L['天赋模拟']
end

local function Init()
    local T = _G.PlayerSpellsFrame and _G.PlayerSpellsFrame.TalentsFrame
    if not T then return false end
    if not body then NP.Build(T) end
    if not body then return false end
    if not NP.tabID then
        local ts = T.TabSystem
        if ts and #ts.tabs == 2 then
            NP.tabID = T:AddNamedTab(TabLabel())
        elseif ts and #ts.tabs >= 3 then
            NP.tabID = 3
        end
    end
    if NP.tabID then
        local ts = T.TabSystem
        local tab = ts and ts.tabs[NP.tabID]
        if tab and type(tab.tabText) == 'string' and not tab.tabText:find('|T', 1, true) then
            tab.tabText = TabLabel()
            if tab.UpdateTabText then tab:UpdateTabText() end
            if tab.UpdateTabWidth then tab:UpdateTabWidth() end
            if ts.MarkDirty then ts:MarkDirty() end
        end
    end
    NP.SyncShow()
    return NP.tabID ~= nil
end

NP.Init = Init

ns.Init(function()
    if IsLoggedIn and IsLoggedIn() then Init() end
    if EventUtil and EventUtil.ContinueOnAddOnLoaded then
        EventUtil.ContinueOnAddOnLoaded('Blizzard_PlayerSpells', function() Init() end)
    end
    local boot = CreateFrame('Frame')
    boot:RegisterEvent('PLAYER_ENTERING_WORLD')
    boot:SetScript('OnEvent', function(self)
        self:UnregisterEvent('PLAYER_ENTERING_WORLD')
        Init()
        if C_Timer and C_Timer.After then
            C_Timer.After(1.0, function() Init() end)
            C_Timer.After(3.0, function() Init() end)
        end
    end)
end)
