local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

local NP = {}
NP.viewMode = 'live'
ns.NativeTalentPage = NP

local L = ns.L
local TD = ns.TalentTrees
local TP = ns.TalentPlans

local MAX_PT = 51
local COLW, GX, TOP = 303, 41, 50
local GRID_Y, ROW_STEP, NODE_SIZE = 200, 60, 40
local BODY_W, BODY_H = 1212, 595
local LIST_W, LIST_ROW, LIST_STEP = 220, 22, 25
local LIST_DROP = 20
local BRAND_LIFT = 5
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
local applyBtn, resetBtn, viewBtn, seqBtn, planHeader, skillHeader
local needCard, needAmount
local LinkOK, LinkBlockName
local badgeLayer
local skinFacade, skinBtns = nil, {}
local skinRegistered = false

local euiBG = { 0.05, 0.05, 0.06, 0.62 }

local function SkinButtonEUI(b)
    if not b or b.__dfSkin then return end
    b.__dfSkin = true
    for _, k in ipairs({ 'Left', 'Middle', 'Right', 'LeftSeparator', 'RightSeparator' }) do
        local r = b[k]
        if r and r.SetAlpha then r:SetAlpha(0) end
    end
    for _, g in ipairs({ 'GetNormalTexture', 'GetPushedTexture', 'GetDisabledTexture', 'GetHighlightTexture' }) do
        local fn = b[g]
        local t = fn and fn(b)
        if t and t.SetAlpha then t:SetAlpha(0) end
    end
    local bg = b:CreateTexture(nil, 'BACKGROUND')
    bg:SetColorTexture(euiBG[1], euiBG[2], euiBG[3], euiBG[4])
    bg:SetAllPoints()
    b.__dfBg = bg
    local hl = b:CreateTexture(nil, 'HIGHLIGHT')
    hl:SetColorTexture(1, 1, 1, 0.10)
    hl:SetAllPoints()
    local PP = _G.EllesmereUI and _G.EllesmereUI.PanelPP
    if PP and PP.CreateBorder then
        pcall(PP.CreateBorder, b, 0.30, 0.30, 0.30, 0.85, 1, 'OVERLAY', 7)
    end
end

local function TrySkinRegister()
    if skinRegistered then return true end
    local E = _G.EllesmereUI
    if not (E and E.RegisterSkin) then return false end
    skinRegistered = true
    E.RegisterSkin('DungeonsForeverTalent', function(S)
        skinFacade = S
        if S.GetPanelColor then
            local ok, r, g, bl, a = pcall(S.GetPanelColor)
            if ok and tonumber(r) and tonumber(g) and tonumber(bl) then
                euiBG = { r, g, bl, tonumber(a) or 0.62 }
            end
        end
        for i = 1, #skinBtns do
            local b = skinBtns[i]
            if b then
                SkinButtonEUI(b)
                if b.__dfBg then b.__dfBg:SetColorTexture(euiBG[1], euiBG[2], euiBG[3], euiBG[4]) end
            end
        end
    end)
    return true
end

local function Skinnable(b)
    if not b then return b end
    if TrySkinRegister() then SkinButtonEUI(b) end
    skinBtns[#skinBtns + 1] = b
    if b.__dfBg then b.__dfBg:SetColorTexture(euiBG[1], euiBG[2], euiBG[3], euiBG[4]) end
    return b
end

local function DB()
    local t = ns.ClassDB().talentSim
    if not t then
        t = {}
        ns.ClassDB().talentSim = t
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

local function SimSig()
    local out = {}
    for t = 1, 3 do
        local ks = {}
        for i, v in pairs(NP.pts[t] or {}) do
            local n = tonumber(v) or 0
            if n > 0 then ks[#ks + 1] = i .. ':' .. n end
        end
        table.sort(ks)
        out[t] = table.concat(ks, ',')
    end
    return table.concat(out, '|')
end

local function SaveSim()
    if not NP.cls or not NP.pts then return end
    local sig = SimSig()
    if NP.simSig == sig then return end
    NP.simSig = sig
    local pts = { {}, {}, {} }
    for t = 1, 3 do
        for i, v in pairs(NP.pts[t] or {}) do
            local n = tonumber(v) or 0
            if n > 0 then pts[t][i] = n end
        end
    end
    DB().sim = { cls = NP.cls, pts = pts, pi = NP.planIdx, view = NP.viewMode }
end

local function RestoreSim()
    local s = DB().sim
    if type(s) ~= 'table' or s.cls ~= NP.cls then return false end
    if s.pi then
        local pl = Plans() or {}
        if pl[s.pi] then NP.plan = pl[s.pi] end
    end
    if s.view then NP.viewMode = s.view end
    if type(s.pts) ~= 'table' then return false end
    local pts, any = { {}, {}, {} }, false
    for t = 1, 3 do
        for i, v in pairs(s.pts[t] or {}) do
            local n = tonumber(v) or 0
            if n > 0 then
                pts[t][i] = n
                any = true
            end
        end
    end
    if not any then return false end
    NP.pts = pts
    return true
end

local function MaxPoints()
    return MAX_PT
end

local POINT_START_SPELL = 1225474

local function StartLv()
    local plv = (UnitLevel and UnitLevel('player')) or 0
    local now = (GetTime and GetTime()) or 0
    local c = NP.startLv
    if c and c.plv == plv and (now - c.at) < 10 then return c.v end
    local v = 10
    if IsPlayerSpell and IsPlayerSpell(POINT_START_SPELL) then
        local tx
        if C_Spell and C_Spell.GetSpellDescription then
            local ok, d = pcall(C_Spell.GetSpellDescription, POINT_START_SPELL)
            if ok and type(d) == 'string' then tx = d end
        end
        if not tx and C_TooltipInfo and C_TooltipInfo.GetSpellByID then
            local ok, data = pcall(C_TooltipInfo.GetSpellByID, POINT_START_SPELL)
            if ok and type(data) == 'table' and data.lines then
                for i = 1, #data.lines do
                    local t2 = data.lines[i] and data.lines[i].leftText
                    if t2 and t2 ~= '' and t2 ~= '被动' then tx = t2 end
                end
            end
        end
        local n = tx and (tx:match('从(%d+)级开始') or tx:match('[Ll]evel%s*(%d+)'))
        if n then v = tonumber(n) or 10 end
    end
    if v < 1 or v > 10 then v = 10 end
    NP.startLv = { plv = plv, at = now, v = v }
    return v
end

local function LivePoints()
    local lv = UnitLevel('player') or 0
    return math.min(MAX_PT, math.max(0, lv - (StartLv() - 1)))
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

local function RowAbove(t)
    local d = Data()
    local tree = d and d.trees and d.trees[t]
    local out = {}
    if not tree then return out end
    local per = {}
    for i = 1, #tree.nodes do
        local nd = tree.nodes[i]
        local p = (NP.pts[t] or {})[i] or 0
        if p > 0 then per[nd.row] = (per[nd.row] or 0) + p end
    end
    local cum = 0
    for r = 1, 8 do
        out[r] = cum
        cum = cum + (per[r] or 0)
    end
    return out
end

local function GateOK(t, row, above)
    if row <= 1 then return true end
    above = above or RowAbove(t)
    return (above[row] or 0) >= (row - 1) * 5
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

local function TipBegin(owner, anchor)
    GameTooltip:SetOwner(owner, anchor or 'ANCHOR_RIGHT')
    if ns.hui and ns.hui.ShowNativeTip then
        pcall(ns.hui.ShowNativeTip, GameTooltip)
    end
end

local function BuildBackground(b)
    local d = Data()
    local art = d and ART[d.key] or ART.rogue
    for i = 1, 4 do
        local t = b:CreateTexture(nil, 'OVERLAY', nil, 1)
        t:SetPoint('TOPLEFT', b, 'TOPLEFT', (i - 1) * COLW, 0)
        t:SetSize(COLW, BODY_H)
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
    bd:SetPoint('TOPLEFT', b, 'TOPLEFT', -2, 4)
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

    if not badgeLayer then
        badgeLayer = CreateFrame('Frame', nil, body)
        badgeLayer:SetAllPoints(body)
        badgeLayer:SetFrameLevel(body:GetFrameLevel() + 8)
    end
    local badgeBg = badgeLayer:CreateTexture(nil, 'OVERLAY')
    badgeBg:SetTexture(WHITE)
    badgeBg:SetVertexColor(0, 0, 0, 0.72)
    badgeBg:SetPoint('BOTTOM', b, 'TOP', 0, 3)
    badgeBg:SetSize(22, 12)
    badgeBg:Hide()

    local badge = badgeLayer:CreateFontString(nil, 'OVERLAY', nil, 1)
    badge:SetFont('Fonts\\ARKai_T.ttf', 11, 'OUTLINE')
    badge:SetTextColor(0.10, 1.00, 0.10)
    badge:SetPoint('BOTTOM', badgeBg, 'BOTTOM', 0, 1)
    badge:Hide()
    b.badge, b.badgeBg = badge, badgeBg
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
        local blocker = LinkBlockName and LinkBlockName(self.tree, self.idx)
        if blocker then
            print('|cff46bf72[天赋]|r ' .. string.format(L['需先点满 %s'], blocker))
            return
        end
        if not GateOK(self.tree, self.nd.row) then
            local need = (self.nd.row - 1) * 5
            local have = RowAbove(self.tree)[self.nd.row] or 0
            print('|cff46bf72[天赋]|r ' .. string.format(L['本系第 %d 行需先投入 %d 点，还差 %d 点'], self.nd.row, need, need - have))
            return
        end
        if TotalSpent() >= MaxPoints() then
            print('|cff46bf72[天赋]|r ' .. string.format(L['模拟已满 %d 点'], MaxPoints()))
            return
        end
        pts[self.idx] = cur + 1
        Refresh()
    end)

    b:SetScript('OnEnter', function(self)
        TipBegin(self, 'ANCHOR_RIGHT')
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
        local blocker = LinkBlockName and LinkBlockName(self.tree, self.idx)
        if blocker then
            GameTooltip:AddLine(string.format(L['需先点满 %s'], blocker), 0.95, 0.45, 0.4, true)
        elseif not GateOK(self.tree, self.nd.row) then
            local need = (self.nd.row - 1) * 5
            local have = RowAbove(self.tree)[self.nd.row] or 0
            GameTooltip:AddLine(string.format(L['需本系再投入 %d 点'], need - have), 0.95, 0.45, 0.4, true)
        end
        GameTooltip:Show()
    end)
    b:SetScript('OnLeave', function() GameTooltip:Hide() end)

    return b
end

local nodeStates = { {}, {}, {} }
local edgeLayer, edgeObjs, edgeList, edgeIn

local function SyncEdges()
    edgeList, edgeIn = {}, { {}, {}, {} }
    NP.edgeList, NP.edgeIn = edgeList, edgeIn
    if type(CT) ~= 'table' or type(Traits) ~= 'table' then return end
    local d = Data()
    if not d then return end
    local ok, cfg = pcall(CT.GetActiveConfigID)
    if not ok or not cfg then return end
    local ok2, ci = pcall(Traits.GetConfigInfo, cfg)
    if not ok2 or type(ci) ~= 'table' or type(ci.treeIDs) ~= 'table' or not ci.treeIDs[1] then return end
    local ok3, list = pcall(Traits.GetTreeNodes, ci.treeIDs[1])
    if not ok3 or type(list) ~= 'table' then return end
    local byName = {}
    for t = 1, 3 do
        local nodeList = d.trees[t] and d.trees[t].nodes or {}
        for i = 1, #nodeList do byName[nodeList[i].n] = { t = t, i = i } end
    end
    local cache = {}
    local function nameOf(nodeID)
        local hit = cache[nodeID]
        if hit ~= nil then return hit or nil end
        local out = false
        local okn, info = pcall(Traits.GetNodeInfo, cfg, nodeID)
        if okn and type(info) == 'table' and info.entryIDs and info.entryIDs[1] then
            local oke, ent = pcall(Traits.GetEntryInfo, cfg, info.entryIDs[1])
            if oke and type(ent) == 'table' and ent.definitionID then
                local okd, def = pcall(Traits.GetDefinitionInfo, ent.definitionID)
                if okd and type(def) == 'table' and def.spellID then
                    local oks, sp = pcall(C_Spell.GetSpellInfo, def.spellID)
                    if oks and type(sp) == 'table' and sp.name then out = sp.name end
                end
            end
        end
        cache[nodeID] = out
        return out or nil
    end
    for _, nid in ipairs(list) do
        local okn, info = pcall(Traits.GetNodeInfo, cfg, nid)
        if okn and type(info) == 'table' and info.visibleEdges then
            local a = byName[nameOf(nid) or '']
            if a then
                for _, e in ipairs(info.visibleEdges) do
                    local b = byName[nameOf(e.targetNode) or '']
                    if b and b.t == a.t then
                        edgeList[#edgeList + 1] = { t = a.t, from = a.i, to = b.i }
                        local ins = edgeIn[a.t][b.i]
                        if not ins then
                            ins = {}
                            edgeIn[a.t][b.i] = ins
                        end
                        ins[#ins + 1] = a.i
                    end
                end
            end
        end
    end
end

local function ApplyEdgeAtlas(obj, on)
    local ign = _G.TextureKitConstants and _G.TextureKitConstants.IgnoreAtlasSize or 1
    pcall(obj.line.SetAtlas, obj.line, on and 'talents-arrow-line-yellow' or 'talents-arrow-line-gray', ign)
    pcall(obj.arrow.SetAtlas, obj.arrow, on and 'talents-arrow-head-yellow' or 'talents-arrow-head-gray')
end

local function UpdateEdgeStates()
    if not edgeList or not edgeObjs or #edgeObjs == 0 then return end
    for k = 1, #edgeList do
        local e = edgeList[k]
        local obj = edgeObjs[k]
        local st = nodeStates[e.t] and nodeStates[e.t][e.to]
        if obj and obj.line then
            ApplyEdgeAtlas(obj, st ~= nil and st ~= 'locked')
        end
    end
end

local function DrawEdges()
    if not edgeList then return end
    if not edgeLayer then
        edgeLayer = CreateFrame('Frame', nil, body)
        edgeLayer:SetAllPoints(body)
        edgeLayer:SetFrameLevel(body:GetFrameLevel() + 5)
    end
    edgeObjs = edgeObjs or {}
    local idx = 0
    for k = 1, #edgeList do
        local e = edgeList[k]
        local fromBtn = nodes[e.t] and nodes[e.t][e.from]
        local toBtn = nodes[e.t] and nodes[e.t][e.to]
        if fromBtn and toBtn then
            idx = idx + 1
            local obj = edgeObjs[idx]
            if not obj then
                obj = CreateFrame('Frame', nil, edgeLayer)
                obj:SetAllPoints(edgeLayer)
                obj.line = obj:CreateLine()
                obj.line:SetThickness(6)
                obj.arrow = obj:CreateTexture(nil, 'OVERLAY', nil, 2)
                obj.arrow:SetSize(12, 12)
                edgeObjs[idx] = obj
            end
            local scx, scy = fromBtn:GetCenter()
            local tcx, tcy = toBtn:GetCenter()
            local angle = math.atan2((scy or 0) - (tcy or 0), (scx or 0) - (tcx or 0))
            local xo = (toBtn:GetWidth() / 2) * math.cos(angle)
            local yo = (toBtn:GetHeight() / 2) * math.sin(angle)
            local sxo = -(fromBtn:GetWidth() / 2) * math.cos(angle)
            local syo = -(fromBtn:GetHeight() / 2) * math.sin(angle)
            obj.line:SetStartPoint('CENTER', fromBtn, sxo, syo)
            obj.line:SetEndPoint('CENTER', toBtn, xo, yo)
            obj.arrow:SetPoint('CENTER', toBtn, 'CENTER', xo, yo)
            obj.arrow:SetRotation(angle - math.pi / 2)
            obj:Show()
        end
    end
    for i = idx + 1, #edgeObjs do edgeObjs[i]:Hide() end
    UpdateEdgeStates()
end

LinkOK = function(t, i)
    local ins = edgeIn and edgeIn[t] and edgeIn[t][i]
    if not ins then return true end
    local d = Data()
    local list = d and d.trees[t] and d.trees[t].nodes
    if not list then return true end
    for k = 1, #ins do
        local nd = list[ins[k]]
        if nd and ((NP.pts[t] or {})[ins[k]] or 0) < nd.max then return false end
    end
    return true
end

LinkBlockName = function(t, i)
    local ins = edgeIn and edgeIn[t] and edgeIn[t][i]
    if not ins then return nil end
    local d = Data()
    local list = d and d.trees[t] and d.trees[t].nodes
    if not list then return nil end
    for k = 1, #ins do
        local nd = list[ins[k]]
        if nd and ((NP.pts[t] or {})[ins[k]] or 0) < nd.max then return nd.n end
    end
    return nil
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
    SyncEdges()
    DrawEdges()
end

local function BuildList(parent, y, rows, mode)
    local out = {}
    local plan = mode ~= 'skill'
    for i = 1, rows do
        local r = CreateFrame('Frame', nil, parent)
        r:SetSize(LIST_W, LIST_ROW)
        r:SetPoint('TOPLEFT', parent, 'TOPLEFT', 3 * COLW + GX, -(y + (i - 1) * LIST_STEP - TOP))
        local bg = r:CreateTexture(nil, 'BACKGROUND')
        bg:SetAllPoints()
        bg:SetTexture(WHITE)
        bg:SetVertexColor(1, 1, 1, 0.05)
        r.ic = r:CreateTexture(nil, 'ARTWORK')
        r.ic:SetPoint('LEFT', r, 'LEFT', plan and 18 or 3, 0)
        r.ic:SetSize(16, 16)
        r.ic:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        if plan then
            r.seq = NewText(r, 14, 0.72, 0.76, 0.82, 'LEFT')
            r.seq:SetPoint('LEFT', r, 'LEFT', -2, 0)
            r.seq:SetWidth(16)
        end
        r.nm = NewText(r, 14, 0.92, 0.92, 0.92, 'LEFT')
        r.nm:SetPoint('LEFT', r, 'LEFT', plan and 38 or 22, 0)
        r.nm:SetWidth(plan and 80 or 92)
        r.nm:SetWordWrap(false)
        r.lv = NewText(r, 14, 0.62, 0.68, 0.78, 'RIGHT')
        r.lv:SetPoint('RIGHT', r, 'RIGHT', plan and -66 or -62, 0)
        r.lv:SetWidth(30)
        r.rk = NewText(r, 14, 1, 1, 1, 'RIGHT')
        r.rk:SetPoint('RIGHT', r, 'RIGHT', -4, 0)
        out[i] = r
    end
    return out
end

local function BuildHeaderRow(y, cols)
    local out = {}
    for i = 1, #cols do
        local c = cols[i]
        local t = NewText(body, 14, 0.55, 0.58, 0.62, (c.right or c.rx) and 'RIGHT' or 'LEFT')
        if c.rx then
            t:SetPoint('TOPRIGHT', body, 'TOPLEFT', 3 * COLW + GX + c.rx, -(y - TOP))
        elseif c.right then
            t:SetPoint('TOPRIGHT', body, 'TOPLEFT', 3 * COLW + GX + LIST_W - 4, -(y - TOP))
        else
            t:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX + c.x, -(y - TOP))
        end
        t:SetText(c.text)
        out[#out + 1] = t
    end
    return out
end

local function PlanName()
    local p = NP.plan
    if p and p.name and p.name ~= '' then return p.name end
    return string.format(L['方案%d'], NP.planIdx or 1)
end

local function BuildLists()
    planTitle = NewText(body, 14, 1, 0.82, 0, 'LEFT')
    planTitle:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX - 2, -(GRID_Y - 45 + LIST_DROP - TOP))
    planTitle:SetText(L['加点计划'])

    planHeader = BuildHeaderRow(GRID_Y - 15 + LIST_DROP, {
        { x = -2, text = L['序号'] },
        { x = 38, text = L['天赋'] },
        { rx = LIST_W - 66, text = L['等级'] },
        { right = true, text = L['进度'] },
    })

    viewBtn = CreateFrame('Button', 'DungeonsForeverTalentViewBtn', body, 'UIPanelButtonNoTooltipTemplate')
    viewBtn:SetSize(56, 18)
    viewBtn:SetPoint('RIGHT', body, 'TOPLEFT', 3 * COLW + GX + LIST_W, -(GRID_Y - 37 + LIST_DROP - TOP))
    viewBtn:SetText(L['实时'])
    Skinnable(viewBtn)
    viewBtn:SetScript('OnClick', function()
        NP.viewMode = (NP.viewMode == 'plan') and 'live' or 'plan'
        Refresh()
    end)
    viewBtn:SetScript('OnEnter', function(self)
        TipBegin(self, 'ANCHOR_RIGHT')
        GameTooltip:SetText(L['加点计划视图'], 1, 1, 1)
        GameTooltip:AddLine(L['实时：从当前进度继续'], 0.9, 0.9, 0.9, true)
        GameTooltip:AddLine(L['总览：按等级从头列出'], 0.9, 0.9, 0.9, true)
        GameTooltip:Show()
    end)
    viewBtn:SetScript('OnLeave', function() GameTooltip:Hide() end)

    planRows = BuildList(body, GRID_Y + LIST_DROP, PLAN_ROWS, 'plan')

    local sep = body:CreateTexture(nil, 'OVERLAY')
    sep:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX, -(GRID_Y + PLAN_ROWS * LIST_STEP + 8 + LIST_DROP - TOP))
    sep:SetSize(LIST_W, 1)
    sep:SetTexture(WHITE)
    sep:SetVertexColor(1, 1, 1, 0.14)

    skillTitle = NewText(body, 14, 1, 0.82, 0, 'LEFT')
    skillTitle:SetPoint('TOPLEFT', body, 'TOPLEFT', 3 * COLW + GX - 2, -(GRID_Y + PLAN_ROWS * LIST_STEP + 17 + LIST_DROP - TOP))
    skillTitle:SetText(L['可学习的技能'])

    skillHeader = BuildHeaderRow(GRID_Y + PLAN_ROWS * LIST_STEP + 35 + LIST_DROP, {
        { x = 22, text = L['技能'] },
        { rx = LIST_W - 62, text = L['技能等级'] },
        { right = true, text = L['人物等级'] },
    })

    skillRows = BuildList(body, GRID_Y + PLAN_ROWS * LIST_STEP + 55 + LIST_DROP, SKILL_ROWS, 'skill')
end

local function MakeButton(parent, w, text, x, y)
    local b = CreateFrame('Button', nil, parent, 'UIPanelButtonNoTooltipTemplate')
    b:SetSize(w, 22)
    b:SetPoint('TOPLEFT', parent, 'TOPLEFT', x, y)
    b:SetText(text)
    return Skinnable(b)
end

local function PlanList()
    local plans = Plans() or {}
    local out = {}
    for i = 1, #plans do
        local p = plans[i]
        out[#out + 1] = { label = p.name or string.format(L['方案%d'], i), plan = p, idx = i }
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

local function SeqFromAlloc(alloc)
    local d = Data()
    if not (alloc and d) then return nil end
    local order = {}
    for t = 1, 3 do
        local pts = 0
        for _, v in pairs(alloc[t] or {}) do pts = pts + (tonumber(v) or 0) end
        order[#order + 1] = { t = t, pts = pts }
    end
    table.sort(order, function(a, b)
        if a.pts ~= b.pts then return a.pts > b.pts end
        return a.t < b.t
    end)
    local out, stuck = {}, {}
    for _, item in ipairs(order) do
        local t = item.t
        local tree = d.trees[t]
        local nodes = tree and tree.nodes or {}
        local want, have, rowPts, left = {}, {}, {}, 0
        for i = 1, #nodes do
            want[i] = tonumber((alloc[t] or {})[i]) or 0
            have[i] = 0
            left = left + want[i]
        end
        local function above(row)
            local n = 0
            for r = 1, row - 1 do n = n + (rowPts[r] or 0) end
            return n
        end
        while left > 0 do
            local pick
            for i = 1, #nodes do
                local nd = nodes[i]
                if have[i] < want[i] and above(nd.row) >= (nd.row - 1) * 5 then
                    pick = i
                    break
                end
            end
            if not pick then break end
            have[pick] = have[pick] + 1
            rowPts[nodes[pick].row] = (rowPts[nodes[pick].row] or 0) + 1
            left = left - 1
            out[#out + 1] = { t, pick }
        end
        for i = 1, #nodes do
            for _ = have[i] + 1, want[i] do stuck[#stuck + 1] = { t, i } end
        end
    end
    table.sort(stuck, function(a, b)
        if a[1] ~= b[1] then return a[1] < b[1] end
        return a[2] < b[2]
    end)
    for i = 1, #stuck do out[#out + 1] = stuck[i] end
    return #out > 0 and out or nil
end

local function SeqOf(plan)
    if plan and plan.seq then return plan.seq end
    if plan and plan.alloc then
        if NP.seqFor == plan and NP.seqCache then return NP.seqCache end
        local s = SeqFromAlloc(plan.alloc)
        if s then
            NP.seqFor, NP.seqCache = plan, s
            return s
        end
    end
    local plans = Plans() or {}
    local first = plans[1]
    if not first then return nil end
    if first.seq then return first.seq end
    return SeqFromAlloc(first.alloc)
end

local function PendingSeq(base)
    local seq = SeqOf(NP.plan)
    local out = {}
    if not seq then return out end
    local need = {}
    local k = 0
    local have = (base and base.have) or NP.pts
    local baseSpent = (base and base.spent) or TotalSpent()
    local capLv = (base and base.lv) or 60
    local overview = NP.viewMode == 'plan' or (base and base.all) or false
    local early, late = {}, {}
    local baseLvOff = StartLv() - 1
    for i = 1, #seq do
        local it = seq[i]
        local nd = NodeOf(it[1], it[2])
        if nd then
            local key = it[1] * 100 + it[2]
            local n = (need[key] or 0) + 1
            need[key] = n
            local cur = (have[it[1]] or {})[it[2]] or 0
            if overview or n > cur then
                k = k + 1
                local lv = baseLvOff + (overview and k or (baseSpent + k))
                local item = { t = it[1], i = it[2], nd = nd, lv = lv, target = n,
                    have = cur, over = lv > capLv, first = n == 1 }
                if overview or not item.over then
                    early[#early + 1] = item
                else
                    late[#late + 1] = item
                end
            end
        end
    end
    for i = 1, #early do out[#out + 1] = early[i] end
    for i = 1, #late do out[#out + 1] = late[i] end
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

local function BuildNeedCard()
    local T = NP.frame
    local cd = T and T.ClassCurrencyDisplay
    if not cd or needCard then return end
    local f = CreateFrame('Frame', 'DungeonsForeverTalentNeedCard', cd)
    f:SetSize(157, 45)
    f:SetPoint('RIGHT', cd, 'LEFT', -10, 0)
    f:SetFrameLevel(cd:GetFrameLevel())

    local bg = f:CreateTexture(nil, 'BACKGROUND')
    bg:SetAtlas('Talents-Square-Box-c60')
    bg:SetSize(125, 45)
    bg:SetPoint('RIGHT', f, 'RIGHT', 0, 0)

    local label = f:CreateFontString(nil, 'OVERLAY')
    label:SetFont('Fonts\\ARKai_T.ttf', 15, '')
    label:SetTextColor(1, 1, 1)
    label:SetText(L['等级'])
    label:SetPoint('RIGHT', f, 'RIGHT', -60, 0)

    local box = CreateFrame('Frame', nil, f)
    box:SetSize(48, 36)
    box:SetPoint('RIGHT', f, 'RIGHT', -4, 0)
    box:SetFrameLevel(f:GetFrameLevel() + 1)

    needAmount = box:CreateFontString(nil, 'OVERLAY')
    needAmount:SetFont('Fonts\\ARKai_T.ttf', 32, '')
    needAmount:SetTextColor(0.10, 1.00, 0.10)
    needAmount:SetPoint('CENTER')
    needAmount:SetText('0')

    f:EnableMouse(true)
    f:SetScript('OnEnter', function(self)
        TipBegin(self, 'ANCHOR_LEFT')
        GameTooltip:SetText(L['等级'], 1, 1, 1)
        GameTooltip:AddLine(string.format(L['角色 %d 级起每级 1 点：需要等级 = 已投入点数 + %d'], StartLv(), StartLv() - 1), 0.9, 0.9, 0.9, true)
        GameTooltip:Show()
    end)
    f:SetScript('OnLeave', function() GameTooltip:Hide() end)

    f:Hide()
    needCard = f
end

local function CurrencyCard(on)
    local T = NP.frame
    if not (T and T.ClassCurrencyDisplay) then return end
    BuildNeedCard()
    local label, amount = CurrencyParts()
    if not label then return end
    if not NP.curOrig then NP.curOrig = label:GetText() end
    if on then
        label:SetText(L['已投入天赋'])
        if amount then amount:SetText(TotalSpent()) end
        if needCard then
            local spent = TotalSpent()
            needCard:SetShown(spent > 0)
            if needAmount then needAmount:SetText(StartLv() - 1 + spent) end
        end
    else
        if NP.curOrig then label:SetText(NP.curOrig) end
        if needCard then needCard:Hide() end
        if T.RefreshClassCurrencyDisplay then T:RefreshClassCurrencyDisplay() end
    end
end

local function SeqMap(pending)
    local map = { {}, {}, {} }
    for i = 1, #pending do
        local p = pending[i]
        local m = map[p.t]
        local list = m[p.i]
        if not list then
            list = {}
            m[p.i] = list
        end
        list[#list + 1] = i
    end
    return map
end

local function SeqText(list)
    if not list or #list == 0 then return nil end
    local parts = {}
    local i = 1
    while i <= #list do
        local j = i
        local same = true
        while j < #list and (list[j + 1] == list[j] + 1 or list[j + 1] == list[j]) do
            if list[j + 1] ~= list[j] then same = false end
            j = j + 1
        end
        if j > i and not same then
            parts[#parts + 1] = list[i] .. '-' .. list[j]
        else
            parts[#parts + 1] = tostring(list[i])
        end
        i = j + 1
    end
    return table.concat(parts, ',')
end

local function NativeSpellName(btn)
    local ok, sid = pcall(btn.GetSpellID, btn)
    if not ok or not sid then return nil end
    local ok2, sp = pcall(C_Spell.GetSpellInfo, sid)
    if ok2 and type(sp) == 'table' then return sp.name end
    return nil
end

local function BuildSeqMap()
    if NP.seqOn == nil then NP.seqOn = DB().seqOn ~= false end
    if not NP.seqOn or not NP.cls then
        NP.seqMap = nil
        return nil
    end
    NP.seqMap = SeqMap(PendingSeq({ all = true }))
    return NP.seqMap
end

local function SeqLayer()
    local PF = _G.PlayerSpellsFrame
    local TF = PF and PF.TalentsFrame
    if not TF then return nil end
    local L = NP.seqLayer
    if L and L:GetParent() == TF then return L end
    L = CreateFrame('Frame', nil, TF)
    L:SetAllPoints(TF)
    L:SetFrameLevel((TF:GetFrameLevel() or 100) + 1600)
    NP.seqLayer = L
    return L
end

local function SeqBadge(btn)
    local L = SeqLayer()
    if not L then return nil, nil end
    local fs, bg = btn.__dfSeq, btn.__dfSeqBg
    if fs and fs:GetParent() == L then return fs, bg end
    if fs then
        fs:Hide()
        bg:Hide()
    end
    bg = L:CreateTexture(nil, 'OVERLAY')
    bg:SetColorTexture(0, 0, 0, 0.72)
    bg:SetSize(26, 12)
    bg:SetPoint('BOTTOM', btn, 'TOP', 0, 2)
    fs = L:CreateFontString(nil, 'OVERLAY')
    local font = (GameFontNormalSmall and GameFontNormalSmall:GetFont()) or STANDARD_TEXT_FONT
    fs:SetFont(font, 10, 'OUTLINE')
    fs:SetPoint('CENTER', bg, 'CENTER', 0, 0)
    fs:SetTextColor(0.55, 0.95, 0.55)
    fs:Hide()
    bg:Hide()
    btn.__dfSeq, btn.__dfSeqBg = fs, bg
    return fs, bg
end

local function RefreshNativeSeq()
    local PF = _G.PlayerSpellsFrame
    local TF = PF and PF.TalentsFrame
    local map = TF and TF.nodeIDToButton
    local byName = NP.byName
    if not (map and byName) then return end
    local nos = NP.seqMap
    if not nos then nos = BuildSeqMap() end
    local L = SeqLayer()
    if L then
        local T = NP.frame
        local mine = (T and body and T:GetTab() == NP.tabID) and true or false
        L:SetShown(not mine)
        local peak = (TF:GetFrameLevel() or 100) + 1600
        for _, btn in pairs(map) do
            local lv = btn:GetFrameLevel()
            if lv and lv + 10 > peak then peak = lv + 10 end
        end
        if L:GetFrameLevel() ~= peak then L:SetFrameLevel(peak) end
    end
    for _, btn in pairs(map) do
        local fs, bg = SeqBadge(btn)
        local txt
        if nos and fs then
            local pos = byName[NativeSpellName(btn) or '']
            if pos then
                local list = nos[pos.t] and nos[pos.t][pos.i]
                if list and #list > 0 then txt = SeqText(list) end
            end
        end
        if txt then
            fs:SetText(txt)
            bg:SetWidth(math.max(20, fs:GetStringWidth() + 6))
            fs:Show()
            bg:Show()
        elseif fs then
            fs:Hide()
            bg:Hide()
        end
    end
end

local function HookNativeTalents()
    local PF = _G.PlayerSpellsFrame
    local TF = PF and PF.TalentsFrame
    if TF and not TF.__dfSeqHook then
        TF.__dfSeqHook = true
        TF:HookScript('OnShow', function() RefreshNativeSeq() end)
    end
    RefreshNativeSeq()
    return TF and TF.__dfSeqHook and true or false
end

local function NativeSeqWatch()
    if NP.seqWatch then return end
    local f = CreateFrame('Frame')
    NP.seqWatch = f
    local acc, tries = 0, 0
    f:SetScript('OnUpdate', function(self, dt)
        acc = acc + (dt or 0)
        if acc < 0.3 then return end
        acc = 0
        tries = tries + 1
        if HookNativeTalents() or tries > 60 then
            NP.seqWatch = nil
            self:SetScript('OnUpdate', nil)
        end
    end)
end

local function LiveCached()
    local now = (GetTime and GetTime()) or 0
    local c = NP.liveCache
    if c and (now - c.at) < 1.0 then return c.read end
    local read = NP.LiveRead and NP.LiveRead() or nil
    NP.liveCache = { at = now, read = read }
    return read
end

local function LiveBase()
    if NP.viewMode == 'plan' then return nil end
    local read = LiveCached()
    if not read then return nil end
    local c = NP.liveBaseCache
    if c and c.read == read then return c.base end
    local d = Data()
    local have = { {}, {}, {} }
    for t = 1, 3 do
        local list = d and d.trees[t] and d.trees[t].nodes or {}
        for i = 1, #list do
            local live = read.byName[list[i].n]
            if live and (live.rank or 0) > 0 then
                have[t][i] = live.rank
            end
        end
    end
    local base = {
        have = have,
        spent = read.spent or 0,
        lv = (UnitLevel and UnitLevel('player')) or 60,
    }
    NP.liveBaseCache = { read = read, base = base }
    return base
end

local function OutOfPlan()
    local alloc = NP.plan and NP.plan.alloc
    if not alloc then return {} end
    local read = LiveCached()
    if not read then return {} end
    local d = Data()
    local out = {}
    for t = 1, 3 do
        local tree = d and d.trees[t]
        local list = tree and tree.nodes or {}
        for i = 1, #list do
            local nd = list[i]
            local live = read.byName[nd.n]
            local have = (live and live.rank) or 0
            local want = tonumber((alloc[t] or {})[i]) or 0
            if have > want then
                out[#out + 1] = { t = t, i = i, nd = nd, extra = have - want }
            end
        end
    end
    return out
end

local function SpellAvail()
    local lv = (UnitLevel and UnitLevel('player')) or 0
    local c = NP.spellAvail
    if c and c.lv == lv then return c.list end
    local st = ns.SpellTraining
    local groups = st and st.Rows and st.Rows()
    local list = (groups and groups.available) or {}
    NP.spellAvail = { lv = lv, list = list }
    return list
end

local function UpdateLists()
    local base = LiveBase()
    local pending = PendingSeq(base)
    local oop = base and OutOfPlan() or {}
    local shownRows = 0
    for i = 1, #oop do
        if shownRows >= PLAN_ROWS then break end
        shownRows = shownRows + 1
        local row = planRows[shownRows]
        local it = oop[i]
        if row.seq then row.seq:SetText('◇') end
        row.ic:SetTexture('Interface\\Icons\\' .. tostring(it.nd.icon))
        row.ic:SetDesaturated(true)
        row.lv:SetText('')
        row.nm:SetText(it.nd.n)
        row.rk:SetText(string.format(L['方案外 ×%d'], it.extra))
        row.rk:SetTextColor(1.00, 0.62, 0.32)
        row.nm:SetTextColor(1.00, 0.82, 0.45)
        row:Show()
    end
    local seqNo = 0
    for i = 1, #pending do
        if shownRows >= PLAN_ROWS then break end
        shownRows = shownRows + 1
        seqNo = seqNo + 1
        local row = planRows[shownRows]
        local p = pending[i]
        if row.seq then row.seq:SetText(tostring(seqNo)) end
        row.ic:SetDesaturated(false)
        row.ic:SetTexture('Interface\\Icons\\' .. tostring(p.nd.icon))
        if NP.viewMode == 'plan' or p.over then
            row.lv:SetText(tostring(p.lv))
        else
            row.lv:SetText('')
        end
        row.nm:SetTextColor(0.92, 0.92, 0.92)
        row.nm:SetText(p.nd.n)
        row.rk:SetTextColor(1, 1, 1)
        if p.over then
            row.rk:SetText(L['点不够'])
        else
            row.rk:SetText(p.have .. '/' .. p.nd.max)
        end
        row:Show()
    end
    if shownRows == 0 and NP.viewMode ~= 'plan' then
        local row = planRows[1]
        if row.seq then row.seq:SetText('') end
        row.ic:SetTexture('')
        row.ic:SetDesaturated(false)
        row.lv:SetText('')
        row.nm:SetTextColor(0.55, 0.58, 0.62)
        row.nm:SetText(L['与当前方案一致'])
        row.rk:SetTextColor(0.55, 0.58, 0.62)
        row.rk:SetText('')
        row:Show()
        shownRows = 1
    end
    for i = shownRows + 1, PLAN_ROWS do planRows[i]:Hide() end
    if planTitle then
        planTitle:SetText(PlanName())
    end
    if viewBtn then viewBtn:SetText(NP.viewMode == 'plan' and L['总览'] or L['实时']) end

    local avail = SpellAvail()
    for i = 1, SKILL_ROWS do
        local row = skillRows[i]
        local sp = avail[i]
        if sp then
            local icon = tostring(sp.icon or '')
            if icon == '' then
                icon = 'Interface\\Icons\\INV_Misc_QuestionMark'
            elseif icon:sub(1, 9) ~= 'Interface' then
                icon = 'Interface\\Icons\\' .. icon
            end
            row.ic:SetTexture(icon)
            row.lv:SetText(tostring(sp.rank or 1))
            row.nm:SetText(sp.name or '')
            row.rk:SetText(sp.learn and tostring(sp.learn) or '')
            row:Show()
        else
            row:Hide()
        end
    end

    if skillTitle then
        skillTitle:SetText(#avail > 0 and L['可学习的技能'] or L['暂无可学习的技能'])
    end
    RefreshNativeSeq()
end

Refresh = function()
    if not body then return end
    local unspent = MaxPoints() - TotalSpent()
    local pending = PendingSeq()
    local smap = BuildSeqMap()
    for t = 1, 3 do
        local d = Data()
        local tree = d and d.trees[t]
        local above = RowAbove(t)
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
                local gate = GateOK(t, b.nd.row, above) and LinkOK(t, i)
                local state
                if not gate then
                    state = 'locked'
                elseif p >= b.nd.max then
                    state = 'max'
                elseif unspent > 0 then
                    state = 'selectable'
                elseif p > 0 then
                    state = 'normal'
                else
                    state = 'locked'
                end
                nodeStates[t][i] = state
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
                if b.badge and b.badgeBg then
                    local txt = smap and smap[t] and smap[t][i] and SeqText(smap[t][i])
                    if txt then
                        b.badge:SetText(txt)
                        b.badgeBg:SetWidth(math.max(20, b.badge:GetStringWidth() + 6))
                        b.badge:Show()
                        b.badgeBg:Show()
                    else
                        b.badge:Hide()
                        b.badgeBg:Hide()
                    end
                end
            end
        end
    end
    UpdateEdgeStates()
    UpdateLists()
    CurrencyCard(true)
    SaveSim()
    HookNativeTalents()
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
    local cap = LivePoints() - read.spent
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
    local f = CreateFrame('Frame', 'DungeonsForeverTalentPlanMenu', UIParent, 'BackdropTemplate')
    f:SetSize(352, math.max(24, #rows * 24) + 12)
    f:SetPoint('TOPLEFT', anchor, 'BOTTOMLEFT', 0, -2)
    f:SetFrameStrata('FULLSCREEN_DIALOG')
    f:SetFrameLevel(200)
    f:SetBackdrop({ bgFile = WHITE, edgeFile = WHITE, edgeSize = 1 })
    f:SetBackdropColor(0.05, 0.05, 0.06, 0.96)
    f:SetBackdropBorderColor(0.7, 0.6, 0.3, 1)

    local catcher = CreateFrame('Frame', nil, UIParent)
    catcher:SetAllPoints(UIParent)
    catcher:SetFrameStrata('FULLSCREEN_DIALOG')
    catcher:SetFrameLevel(199)
    catcher:EnableMouse(true)
    catcher:SetScript('OnMouseDown', function() f:Hide() end)
    NP.planCatcher = catcher
    local d = Data()
    for i = 1, #rows do
        local r = CreateFrame('Button', nil, f)
        r:SetSize(340, 24)
        r:SetPoint('TOPLEFT', f, 'TOPLEFT', 6, -(6 + (i - 1) * 24))
        r:SetHighlightTexture(WHITE, 'ADD')
        local hl = r:GetHighlightTexture()
        hl:SetVertexColor(1, 1, 1, 0.1)
        local fs = NewText(r, 14, 0.92, 0.92, 0.92, 'LEFT')
        fs:SetPoint('LEFT', r, 'LEFT', 3, 0)
        fs:SetWidth(76)
        fs:SetJustifyH('LEFT')
        fs:SetWordWrap(false)
        fs:SetText(rows[i].label)
        local alloc = rows[i].alloc or (rows[i].plan and rows[i].plan.alloc) or {}
        local total, x = 0, 120
        for t = 1, 3 do
            local tree = d and d.trees[t]
            local pts = 0
            for _, v in pairs(alloc[t] or {}) do pts = pts + v end
            total = total + pts
            if tree then
                local ic = r:CreateTexture(nil, 'ARTWORK')
                ic:SetSize(14, 14)
                ic:SetPoint('LEFT', r, 'LEFT', x, 0)
                ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                ic:SetTexture('Interface\\Icons\\' .. tostring(tree.icon))
                local pv = NewText(r, 14, 1, 0.82, 0, 'LEFT')
                pv:SetPoint('LEFT', r, 'LEFT', x + 16, 0)
                pv:SetText(pts)
            end
            if t < 3 then
                local sl = NewText(r, 14, 0.62, 0.68, 0.78, 'LEFT')
                sl:SetPoint('LEFT', r, 'LEFT', x + 30, 0)
                sl:SetText('/')
            end
            x = x + 40
        end
        local lv = NewText(r, 14, 0.62, 0.68, 0.78, 'RIGHT')
        lv:SetPoint('RIGHT', r, 'RIGHT', -2, 0)
        lv:SetText(string.format(L['需要等级 %d'], total + StartLv() - 1))
        r:SetScript('OnClick', function()
            NP.plan = rows[i].plan or { name = rows[i].label, alloc = alloc }
            NP.planIdx = rows[i].idx
            ApplyAlloc(alloc)
            f:Hide()
            Refresh()
        end)
    end
    f:EnableMouse(true)
    f:SetScript('OnHide', function()
        catcher:Hide()
        NP.planMenu = nil
        NP.planCatcher = nil
    end)
    if UISpecialFrames then
        local nm = f:GetName()
        local found = false
        for i = 1, #UISpecialFrames do
            if UISpecialFrames[i] == nm then found = true break end
        end
        if not found then UISpecialFrames[#UISpecialFrames + 1] = nm end
    end
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

    if NP.seqOn == nil then NP.seqOn = DB().seqOn ~= false end
    seqBtn = CreateFrame('Button', 'DungeonsForeverTalentSeqBtn', strip, 'UIPanelButtonNoTooltipTemplate')
    seqBtn:SetSize(124, 22)
    seqBtn:SetPoint('TOPLEFT', strip, 'TOPLEFT', 574, 0)
    seqBtn:SetText(NP.seqOn and L['加点顺序显示:开'] or L['加点顺序显示:关'])
    Skinnable(seqBtn)
    seqBtn:SetScript('OnClick', function()
        NP.seqOn = not NP.seqOn
        DB().seqOn = NP.seqOn
        if seqBtn then
            seqBtn:SetText(NP.seqOn and L['加点顺序显示:开'] or L['加点顺序显示:关'])
        end
        Refresh()
    end)

end

local function BuildApplyButton(T)
    applyBtn = Skinnable(CreateFrame('Button', nil, T, 'UIPanelButtonNoTooltipTemplate'))
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
        TipBegin(self, 'ANCHOR_RIGHT')
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
        if NP.seqLayer then NP.seqLayer:Hide() end
        if applyBtn then applyBtn:Show() end
        if viewBtn then viewBtn:Show() end
        if seqBtn then seqBtn:Show() end
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
        if NP.seqLayer then NP.seqLayer:Show() end
        if applyBtn then applyBtn:Hide() end
        if viewBtn then viewBtn:Hide() end
        if seqBtn then seqBtn:Hide() end
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
    NP.planIdx = 1
    if RestoreSim() then NP.seeded = true end

    body = CreateFrame('Frame', 'DungeonsForeverTalentPage', T)
    body:SetSize(BODY_W, BODY_H)
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
    if headers[4] and headers[4].Icon then
        headers[4].Icon:ClearAllPoints()
        headers[4].Icon:SetPoint('CENTER', headers[4], 'CENTER', -3, 3 + BRAND_LIFT)
    end

    BuildNodes()
    NP.byName = {}
    for t = 1, 3 do
        local list = d.trees[t] and d.trees[t].nodes or {}
        for i = 1, #list do
            if list[i].n then NP.byName[list[i].n] = { t = t, i = i } end
        end
    end
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
            NP.seqMap = nil
            if NP.frame and body and NP.frame:GetTab() == NP.tabID then
                ApplyState(true)
                Refresh()
            end
            HookNativeTalents()
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
            hooksecurefunc(T, 'SetTab', function()
                NP.SyncShow()
                HookNativeTalents()
            end)
        end
    end

    NP.SyncShow()
    BuildSeqMap()
    HookNativeTalents()
    NativeSeqWatch()
end

local function TabLabel()
    return TAB_LOGO .. L['天赋模拟']
end

local function Init()
    TrySkinRegister()
    if ns.TalentEnhOn and not ns.TalentEnhOn() then return false end
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
    TrySkinRegister()
    local reg = CreateFrame('Frame')
    reg:RegisterEvent('PLAYER_LOGIN')
    reg:RegisterEvent('ADDON_LOADED')
    reg:SetScript('OnEvent', function(self)
        if TrySkinRegister() then
            self:UnregisterEvent('PLAYER_LOGIN')
            self:UnregisterEvent('ADDON_LOADED')
        end
    end)

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
