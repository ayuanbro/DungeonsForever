local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

local LP = {}
ns.LegacyPage = LP

local L = ns.L
local Traits = _G.C_Traits
local Plans = ns.LegacyPlans

local WHITE = 'Interface\\Buttons\\WHITE8x8'
local BRAND = 'Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever'
local FH = 'Fonts\\ARKai_T.ttf'
local FN = 'Fonts\\ARHei.ttf'

local PAGE_W, BODY_H, PAGE_H = 775, 441, 492
local SEASON_CAP = 16
local COLW, CGAP, LEFT0 = 240, 12, 15
local CELL, CELL_Y, NODE, GRID_TOP, GRID_X = 60, 70, 44, 176, 15
local EMB, EMB_RING, BADGE = 78, 84, 36
local CARD_W, CARD_H, CARD_X, CARD_Y = 67, 66, 35, -120
local ICON_W, ICON_H = 54, 53
local ROW_Y, ROW_H = -464, 21
local HEAD_LINE, DIV_H = 134, 284
local PLATE_TEX = 130871
local NS = NODE / 40
local LINE_END = 24 * NS
local LINE_W, HEAD_W, HEAD_H = 7, 17, 15

local TREE_ATLAS = { 'UI-Legacy-Tree-Professions', 'UI-Legacy-Tree-Adventure', 'UI-Legacy-Tree-Progression' }
local TREE_NAME = { '专业', '冒险', '充裕' }

local ART_FULL = 'talents-node-square-yellow'
local ART_OPEN = 'talents-node-square-green'
local ART_LOCK = 'talents-node-square-locked'
local ART_NONE = 'talents-node-square-gray'

local LINE_ON = 'talents-arrow-line-yellow'
local LINE_OFF = 'talents-arrow-line-gray'
local HEAD_ON = 'talents-arrow-head-yellow'
local HEAD_OFF = 'talents-arrow-head-gray'

local LINKS = {
    { { 3300, 1750, 4200, 1750 }, { 2400, 2650, 3300, 2650 }, { 4200, 2650, 5100, 2650 } },
    { { 2400, 1750, 3150, 1800 }, { 3300, 2650, 4200, 2650 }, { 4200, 1750, 5100, 1750 } },
    { { 2400, 2650, 4200, 2650 }, { 2400, 1750, 3300, 1750 }, { 4200, 1750, 5100, 1750 } },
}

local GOLD = { 1.00, 0.82, 0.00 }
local GREEN = { 0.30, 0.95, 0.35 }
local GREY = { 0.62, 0.64, 0.68 }
local DIM = { 0.42, 0.44, 0.48 }
local RED = { 1.00, 0.35, 0.30 }
local WHITE_TXT = { 1.00, 1.00, 1.00 }
local PLATE_BG = { 0.055, 0.045, 0.035, 0.95 }
local PLATE_EDGE = { 0.42, 0.34, 0.20, 0.85 }

local host, card, page, Model
local cols, nodes, strip = {}, {}, {}
local linkObjs, byNode = {}, {}
local presetIdx = 1
local built = false
local ticking

local BuildStrip
local BuildLinks
local Refresh
local Emblem

local function FS(parent, size, color, font)
    local f = parent:CreateFontString(nil, 'OVERLAY')
    local ok = pcall(f.SetFont, f, font or FH, size, '')
    if not ok and ns.FONT then pcall(f.SetFont, f, ns.FONT, size, '') end
    f:SetTextColor(color[1], color[2], color[3])
    return f
end

local function Tex(parent, layer, art, w, h)
    local t = parent:CreateTexture(nil, layer)
    if art then t:SetAtlas(art) end
    t:SetSize(w, h)
    return t
end

local function Snap(v)
    return math.floor(v * 2 + 0.5) / 2
end

local function GetCID()
    local tp = host and host.TreePage and host.TreePage.LegacyTreeTraitPanel
    if tp and tp.GetConfigID then
        local ok, cid = pcall(tp.GetConfigID, tp)
        if ok and cid then return cid end
    end
    local ok2, list = pcall(Traits.GetConfigsByType, 3)
    if ok2 and type(list) == 'table' and list[1] then return list[1] end
    return nil
end

local function CardAtlas(idx)
    local panel = host and host.TreePage and host.TreePage.LegacyTreeSelectionPanel
    local b = panel and panel.treeButtons and panel.treeButtons[idx]
    if b then
        local ok, regs = pcall(function() return { b:GetRegions() } end)
        if ok and regs then
            for i = 1, #regs do
                local r = regs[i]
                local a = r.GetAtlas and r:GetAtlas()
                if a and string.find(a, 'UI-Legacy-Tree-', 1, true) then return a end
            end
        end
    end
    return TREE_ATLAS[idx] or TREE_ATLAS[1]
end

local function BuildModel()
    if type(Traits) ~= 'table' then return nil end
    local cid = GetCID()
    if not cid then return nil end
    local okc, ci = pcall(Traits.GetConfigInfo, cid)
    if not okc or type(ci) ~= 'table' or type(ci.treeIDs) ~= 'table' then return nil end

    local m = { cid = cid, trees = {}, entCache = {}, byNode = {}, avail = 0 }
    local ti = 0
    for i = 1, #ci.treeIDs do
        local tid = ci.treeIDs[i]
        local okl, list = pcall(Traits.GetTreeNodes, tid)
        if okl and type(list) == 'table' and #list > 0 and ti < 3 then
            ti = ti + 1
            local tree = { id = tid, idx = ti, nodes = {}, spent = 0, cap = 0 }
            for k = 1, #list do
                local nid = list[k]
                local okn, ni = pcall(Traits.GetNodeInfo, cid, nid)
                if okn and type(ni) == 'table' then
                    local nd = {}
                    nd.nid = nid
                    nd.posX = tonumber(ni.posX) or 0
                    nd.posY = tonumber(ni.posY) or 0
                    nd.max = tonumber(ni.maxRanks) or 0
                    nd.cur = tonumber(ni.ranksPurchased) or 0
                    nd.cx = Snap((nd.posX - 2400) / 900)
                    nd.cy = Snap((nd.posY - 850) / 900)
                    nd.req = 0
                    local conds = ni.conditionIDs
                    if type(conds) == 'table' then
                        for c = 1, #conds do
                            local okcd, cd = pcall(Traits.GetConditionInfo, cid, conds[c])
                            if okcd and type(cd) == 'table' then
                                local need = tonumber(cd.spentAmountRequired) or 0
                                if need > nd.req then nd.req = need end
                            end
                        end
                    end
                    local ae = ni.activeEntry
                    nd.entry = type(ae) == 'table' and ae.entryID or nil
                    if nd.entry then
                        local hit = m.entCache[nd.entry]
                        if hit == nil then
                            hit = false
                            local oke, e = pcall(Traits.GetEntryInfo, cid, nd.entry)
                            if oke and type(e) == 'table' and e.definitionID then
                                local okd, d = pcall(Traits.GetDefinitionInfo, e.definitionID)
                                if okd and type(d) == 'table' and d.spellID then
                                    local sp = C_Spell.GetSpellInfo(d.spellID)
                                    local ic
                                    if C_Spell.GetSpellTexture then ic = C_Spell.GetSpellTexture(d.spellID) end
                                    if not ic and type(sp) == 'table' then ic = sp.iconID end
                                    hit = { spell = d.spellID, name = (type(sp) == 'table' and sp.name) or '', icon = ic }
                                end
                            end
                            m.entCache[nd.entry] = hit
                        end
                        if hit then
                            nd.spell = hit.spell
                            nd.name = hit.name
                            nd.icon = hit.icon
                        end
                    end
                    if not nd.name or nd.name == '' then nd.name = L['未知'] end
                    tree.nodes[#tree.nodes + 1] = nd
                    tree.cap = tree.cap + nd.max
                    tree.spent = tree.spent + nd.cur
                end
            end
            table.sort(tree.nodes, function(a, b)
                if a.posY ~= b.posY then return a.posY < b.posY end
                return a.posX < b.posX
            end)
            local rowSeq, lastCy, perRow = 0, nil, 0
            for k = 1, #tree.nodes do
                local nd = tree.nodes[k]
                if lastCy == nil or nd.cy ~= lastCy then
                    lastCy = nd.cy
                    rowSeq = rowSeq + 1
                    perRow = 0
                end
                perRow = perRow + 1
                nd.row = rowSeq
                nd.col = perRow
            end
            m.trees[ti] = tree
            for k = 1, #tree.nodes do
                local nd = tree.nodes[k]
                nd.t = ti
                m.byNode[nd.nid] = nd
            end
        end
    end
    if #m.trees == 0 then return nil end

    local okcur, cur = pcall(Traits.GetTreeCurrencyInfo, cid, m.trees[1].id, false)
    if okcur and type(cur) == 'table' and type(cur[1]) == 'table' then
        m.avail = tonumber(cur[1].quantity) or 0
        m.total = tonumber(cur[1].maxQuantity) or m.avail
    end
    return m
end

local function NodeAt(m, t, row, col)
    local tree = m and m.trees[t]
    if not tree then return nil end
    for i = 1, #tree.nodes do
        local nd = tree.nodes[i]
        if nd.row == row and nd.col == col then return nd end
    end
    return nil
end

local function FindNode(m, it)
    if it.nid and m.byNode then
        local nd = m.byNode[it.nid]
        if nd then return nd end
    end
    return NodeAt(m, it.tree or it[1], it.row or it[2], it.col or it[3])
end

local function Preset()
    local list = Plans or {}
    return list[presetIdx] or list[1]
end

local function MapPreset(m, p)
    local map, cum, total = {}, {}, 0
    if not p then return map, cum, total end
    for i = 1, #p.seq do
        local it = p.seq[i]
        local nd = FindNode(m, it)
        if nd then
            local want = math.min(it.rank or it[4], nd.max)
            if want > 0 then
                map[nd.nid] = { rank = want, order = i }
                local need = want - nd.cur
                if need > 0 then total = total + need end
                cum[nd.nid] = total
            end
        end
    end
    return map, cum, total
end

local function NodeState(rec, cur)
    if not rec or rec <= 0 then
        if cur > 0 then return 'over' end
        return 'none'
    end
    if cur >= rec then return 'done' end
    return 'todo'
end

local function ShowTip(b)
    local nd = b.nd
    GameTooltip:SetOwner(b, 'ANCHOR_RIGHT')
    GameTooltip:SetText(nd.name, 1, 0.82, 0)
    local desc
    if nd.spell and C_Spell.GetSpellDescription then desc = C_Spell.GetSpellDescription(nd.spell) end
    if type(desc) == 'string' and desc ~= '' then
        GameTooltip:AddLine(desc, 1, 1, 1, true)
    end
    local rec = b.rec or 0
    GameTooltip:AddLine(' ')
    if rec > 0 then
        local color = (b.state == 'done') and GOLD or GREEN
        GameTooltip:AddLine(string.format(L['推荐 %d/%d'], rec, nd.max), color[1], color[2], color[3])
        if b.order then
            GameTooltip:AddLine(string.format(L['推荐顺位 第%d位'], b.order), 0.65, 0.70, 0.78)
        end
    else
        GameTooltip:AddLine(L['非推荐节点'], GREY[1], GREY[2], GREY[3])
    end
    GameTooltip:AddLine(string.format(L['已投 %d/%d'], nd.cur, nd.max), 0.75, 0.78, 0.84)
    if b.gate then
        GameTooltip:AddLine(string.format(L['需本树先投入 %d 点'], b.gate), RED[1], RED[2], RED[3], true)
    end
    if b.over then
        GameTooltip:AddLine(string.format(L['点数不足，还需 %d 点'], b.over), RED[1], RED[2], RED[3], true)
    end
    if nd.name == L['未知'] then
        GameTooltip:AddLine(L['该节点尚未开放'], GREY[1], GREY[2], GREY[3], true)
    end
    if ns.hui and ns.hui.ShowNativeTip then pcall(ns.hui.ShowNativeTip, GameTooltip) end
    GameTooltip:Show()
end

local function BuildNode(parent, nd)
    local b = CreateFrame('Button', nil, parent)
    b:SetSize(NODE, NODE)
    b:SetPoint('TOPLEFT', parent, 'TOPLEFT',
        LEFT0 + (nd.t - 1) * (COLW + CGAP) + GRID_X + nd.cx * CELL,
        -(GRID_TOP + nd.cy * CELL_Y))
    b:RegisterForClicks('LeftButtonUp', 'RightButtonUp')

    b.bg = Tex(b, 'BACKGROUND', ART_NONE, NODE, NODE)
    b.bg:SetPoint('CENTER')

    b.icon = b:CreateTexture(nil, 'ARTWORK')
    b.icon:SetSize(NODE * 0.78, NODE * 0.78)
    b.icon:SetPoint('CENTER')
    if nd.icon then b.icon:SetTexture(nd.icon) end
    b.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)

    b.ring = Tex(b, 'OVERLAY', ART_LOCK, NODE, NODE)
    b.ring:SetPoint('CENTER')

    b.plate = Tex(b, 'OVERLAY', nil, NODE * 0.86 + 2, NODE * 0.40 + 2)
    b.plate:SetTexture(PLATE_TEX)
    b.plate:SetVertexColor(PLATE_EDGE[1], PLATE_EDGE[2], PLATE_EDGE[3], PLATE_EDGE[4])
    b.plate:SetPoint('BOTTOMRIGHT', b, 'BOTTOMRIGHT', NODE * 0.10, -NODE * 0.10)
    b.plate:SetDrawLayer('OVERLAY', 1)

    b.plateIn = Tex(b, 'OVERLAY', nil, NODE * 0.86, NODE * 0.40)
    b.plateIn:SetTexture(WHITE)
    b.plateIn:SetVertexColor(0.05, 0.04, 0.04, 0.97)
    b.plateIn:SetPoint('CENTER', b.plate, 'CENTER', 0, 0)
    b.plateIn:SetDrawLayer('OVERLAY', 2)

    b.rank = FS(b, 13, WHITE_TXT, FN)
    b.rank:SetDrawLayer('OVERLAY', 3)
    b.rank:SetPoint('RIGHT', b.plateIn, 'RIGHT', -2, 0)
    b.rank:SetJustifyH('RIGHT')
    b.rank:SetShadowColor(0, 0, 0, 1)
    b.rank:SetShadowOffset(1, -1)

    b.nd = nd
    b:SetScript('OnEnter', ShowTip)
    b:SetScript('OnLeave', function() GameTooltip:Hide() end)
    b:SetScript('OnClick', function(self) ShowTip(self) end)
    return b
end

local function BuildColumn(t)
    local c = { root = CreateFrame('Frame', nil, page) }
    c.root:SetSize(COLW, BODY_H - GRID_TOP)
    c.root:SetPoint('TOPLEFT', page, 'TOPLEFT', LEFT0 + (t - 1) * (COLW + CGAP), -22)

    local ICON_Y = 12
    local badgeY = ICON_Y + EMB - BADGE / 2

    c.art = Tex(c.root, 'ARTWORK', nil, EMB, EMB)
    c.art:SetPoint('TOP', c.root, 'TOP', 0, -ICON_Y)
    pcall(c.art.SetAtlas, c.art, CardAtlas(t))

    c.ring = Tex(c.root, 'OVERLAY', 'Legacy-Tree-Frame-Card-Ring', EMB_RING, EMB_RING)
    c.ring:SetPoint('TOP', c.root, 'TOP', 0, -(ICON_Y - 4))

    c.badge = CreateFrame('Frame', nil, c.root)
    c.badge:SetSize(BADGE, BADGE)
    c.badge:SetPoint('TOP', c.root, 'TOP', 0, -badgeY)

    c.disc = c.badge:CreateTexture(nil, 'ARTWORK')
    c.disc:SetTexture(130924)
    c.disc:SetVertexColor(0.05, 0.04, 0.03, 0.96)
    c.disc:SetAllPoints()

    c.badgeRing = c.badge:CreateTexture(nil, 'OVERLAY')
    c.badgeRing:SetAtlas('Legacy-Tree-Frame-Card-Ring')
    c.badgeRing:SetSize(BADGE + 6, BADGE + 6)
    c.badgeRing:SetPoint('CENTER')

    c.total = FS(c.badge, 14, WHITE_TXT, FN)
    c.total:SetPoint('CENTER', c.badge, 'CENTER', 0, 0)
    c.total:SetJustifyH('CENTER')
    c.total:SetShadowColor(0, 0, 0, 1)
    c.total:SetShadowOffset(1, -1)

    c.name = FS(c.root, 16, { 0.91, 0.79, 0.54 })
    c.name:SetPoint('TOP', c.root, 'TOP', 0, 14)
    c.name:SetJustifyH('CENTER')
    c.name:SetText(L[TREE_NAME[t]] or TREE_NAME[t])

    c.line = c.root:CreateTexture(nil, 'ARTWORK', nil, 1)
    c.line:SetTexture(WHITE)
    c.line:SetVertexColor(0.79, 0.64, 0.29, 0.32)
    c.line:SetSize(COLW - 20, 1)
    c.line:SetPoint('TOPLEFT', c.root, 'TOPLEFT', 10, -HEAD_LINE)

    if t < 3 then
        local dg = c.root:CreateTexture(nil, 'ARTWORK', nil, 1)
        dg:SetTexture(WHITE)
        dg:SetVertexColor(0.79, 0.64, 0.29, 0.09)
        dg:SetSize(7, DIV_H)
        dg:SetPoint('TOPLEFT', c.root, 'TOPLEFT', COLW + CGAP / 2 - 3.5, -HEAD_LINE)

        local dv = c.root:CreateTexture(nil, 'ARTWORK', nil, 2)
        dv:SetTexture(WHITE)
        dv:SetVertexColor(0.86, 0.70, 0.36, 0.55)
        dv:SetSize(1, DIV_H)
        dv:SetPoint('TOPLEFT', c.root, 'TOPLEFT', COLW + CGAP / 2 - 0.5, -HEAD_LINE)
    end

    cols[t] = c
    return c
end

local function BuildPage()
    local tp = host.TreePage.LegacyTreeTraitPanel
    page = CreateFrame('Frame', 'DungeonsForeverLegacyPage', tp)
    page:SetSize(PAGE_W, PAGE_H)
    page:SetPoint('TOPLEFT', tp, 'TOPLEFT', 0, -55)
    page:SetFrameLevel((tp:GetFrameLevel() or 100) + 1200)
    page:EnableMouse(true)

    local under = page:CreateTexture(nil, 'BACKGROUND', nil, -8)
    under:SetTexture(WHITE)
    under:SetVertexColor(0.115, 0.092, 0.075, 1)
    under:SetSize(PAGE_W, PAGE_H)
    under:SetPoint('TOPLEFT', page, 'TOPLEFT', 0, 0)

    local base = page:CreateTexture(nil, 'BACKGROUND')
    base:SetSize(PAGE_W, PAGE_H)
    base:SetPoint('TOPLEFT', page, 'TOPLEFT', 0, 0)
    base:SetTexture('Interface\\FrameGeneral\\UI-Background-Rock')
    base:SetTexCoord(0.05, 0.95, 0.05, 0.95)
    base:SetVertexColor(0.50, 0.43, 0.35, 0.50)

    local edge = page:CreateTexture(nil, 'BORDER')
    edge:SetTexture(WHITE)
    edge:SetVertexColor(0.79, 0.64, 0.29, 0.22)
    edge:SetSize(PAGE_W, 1)
    edge:SetPoint('TOPLEFT', page, 'TOPLEFT', 0, 0)

    page:Hide()

    for t = 1, 3 do
        BuildColumn(t)
        nodes[t] = {}
        local list = Model.trees[t] and Model.trees[t].nodes or {}
        for i = 1, #list do
            local b = BuildNode(page, list[i])
            nodes[t][#nodes[t] + 1] = b
            byNode[list[i].nid] = b
        end
    end
    BuildLinks()
    BuildStrip()
end

local function NodeCenter(nd)
    local x = LEFT0 + (nd.t - 1) * (COLW + CGAP) + GRID_X + nd.cx * CELL + NODE / 2 - PAGE_W / 2
    local y = PAGE_H / 2 - (GRID_TOP + nd.cy * CELL_Y + NODE / 2)
    return x, y
end

BuildLinks = function()
    linkObjs = {}
    for t = 1, 3 do
        local tree = Model.trees[t]
        local set = LINKS[t]
        if tree and set then
            local byPos = {}
            for i = 1, #tree.nodes do
                local nd = tree.nodes[i]
                byPos[nd.posX .. ':' .. nd.posY] = nd
            end
            for i = 1, #set do
                local it = set[i]
                local a = byPos[it[1] .. ':' .. it[2]]
                local b = byPos[it[3] .. ':' .. it[4]]
                if a and b then
                    local x1, y1 = NodeCenter(a)
                    local x2, y2 = NodeCenter(b)
                    local dx, dy = x2 - x1, y2 - y1
                    local len = math.sqrt(dx * dx + dy * dy)
                    if len > 1 then
                        local ux, uy = dx / len, dy / len
                        local r = NODE / 2 + 1
                        local sx, sy = x1 + ux * r, y1 + uy * r
                        local ex, ey = x2 - ux * LINE_END, y2 - uy * LINE_END
                        local mx, my = (sx + ex) / 2, (sy + ey) / 2
                        local slen = math.sqrt((ex - sx) * (ex - sx) + (ey - sy) * (ey - sy))
                        local ang = math.atan2(dy, dx)
                        local obj = { a = byNode[a.nid], b = byNode[b.nid] }
                        obj.line = page:CreateTexture(nil, 'ARTWORK')
                        obj.line:SetSize(slen, LINE_W)
                        obj.line:SetPoint('CENTER', page, 'CENTER', mx, my)
                        obj.line:SetRotation(ang)
                        obj.head = page:CreateTexture(nil, 'OVERLAY')
                        obj.head:SetSize(HEAD_W, HEAD_H)
                        obj.head:SetPoint('CENTER', page, 'CENTER', ex, ey)
                        obj.head:SetRotation(ang + math.pi / 2)
                        linkObjs[#linkObjs + 1] = obj
                    end
                end
            end
        end
    end
    LP.linkObjs = linkObjs
end

local function PaintLinks()
    for i = 1, #linkObjs do
        local o = linkObjs[i]
        local a, b = o.a, o.b
        local dim = (a and a.over) or (b and b.over)
        local on = a and a.nd and (a.nd.cur or 0) > 0
        local stem, head, tint = LINE_OFF, HEAD_OFF, 1
        if dim then
            stem, head, tint = LINE_OFF, HEAD_OFF, 0.42
        elseif on then
            stem, head, tint = LINE_ON, HEAD_ON, 1
        end
        pcall(o.line.SetAtlas, o.line, stem)
        pcall(o.line.SetVertexColor, o.line, tint, tint, tint, 1)
        pcall(o.head.SetAtlas, o.head, head)
        pcall(o.head.SetVertexColor, o.head, tint, tint, tint, 1)
    end
end

BuildStrip = function()
    local w = strip

    w.title = FS(page, 13, { 0.91, 0.79, 0.54 })
    w.title:SetPoint('TOPLEFT', page, 'TOPLEFT', LEFT0, ROW_Y - 4)
    w.title:SetText(L['推荐方案'])

    w.tabs = {}
    local list = Plans or {}
    for i = 1, #list do
        local b = CreateFrame('Button', nil, page, 'UIPanelButtonTemplate')
        b:SetSize(84, ROW_H)
        b:SetPoint('TOPLEFT', page, 'TOPLEFT', LEFT0 + 58 + (i - 1) * 90, ROW_Y)
        b:SetText(L[list[i].label] or list[i].label)
        b:SetScript('OnClick', function()
            presetIdx = i
            local db = ns.ClassDB and ns.ClassDB().legacy
            if db then db.preset = i end
            Refresh()
        end)
        w.tabs[i] = b
    end

    w.status = FS(page, 12, GREY)
    w.status:SetPoint('TOPRIGHT', page, 'TOPLEFT', PAGE_W - LEFT0 - 158, ROW_Y - 4)
    w.status:SetJustifyH('RIGHT')
    w.status:SetWidth(256)
    w.status:SetWordWrap(false)

    w.apply = CreateFrame('Button', nil, page, 'UIPanelButtonTemplate')
    w.apply:SetSize(148, ROW_H)
    w.apply:SetPoint('TOPRIGHT', page, 'TOPLEFT', PAGE_W - LEFT0, ROW_Y)
    w.apply:SetText(L['按方案加点'])
    w.apply:SetScript('OnClick', function() LP.Apply() end)
end

Refresh = function()
    if not (page and page:IsShown()) then return end
    local m = BuildModel()
    if not m then return end
    Model = m
    local p = Preset()
    local curMode = (p ~= nil and p.key == 'cur')
    local map, cum, total = MapPreset(m, p)
    local spent = 0
    for t = 1, 3 do
        spent = spent + ((m.trees[t] and m.trees[t].spent) or 0)
    end
    local left = math.max(0, SEASON_CAP - spent)

    for t = 1, 3 do
        local tree = m.trees[t]
        local c = cols[t]
        if tree and c then
            local recSum = 0
            for i = 1, #tree.nodes do
                local r = map[tree.nodes[i].nid]
                if r then recSum = recSum + r.rank end
            end
            if c.total then
                if curMode then
                    c.total:SetText(tostring(tree.spent))
                else
                    c.total:SetText(tostring(recSum))
                end
            end
            c.root:Show()
        elseif c then
            c.root:Hide()
        end
    end

    for t = 1, 3 do
        local tree = m.trees[t]
        local list = nodes[t] or {}
        for i = 1, #list do
            local b = list[i]
            local nd = b.nd
            local r = tree and map[nd.nid] or nil
            local rec = r and r.rank or 0
            local st
            if curMode then
                if nd.cur <= 0 then
                    st = 'none'
                elseif nd.cur >= nd.max then
                    st = 'over'
                else
                    st = 'todo'
                end
            else
                st = NodeState(rec, nd.cur)
                if st == 'over' then st = 'none' end
            end
            b.rec = rec
            b.state = st
            b.order = r and r.order or nil
            b.gate = (tree and nd.req > tree.spent) and nd.req or nil
            local cval = cum[nd.nid]
            b.over = (not curMode) and (cval and cval > left) and (cval - left) or nil

            if curMode then
                b.rank:SetText(nd.cur .. '/' .. nd.max)
            else
                b.rank:SetText(rec .. '/' .. nd.max)
            end

            if st == 'todo' then
                if b.over then
                    b.rank:SetTextColor(0.98, 0.62, 0.32)
                else
                    b.rank:SetTextColor(WHITE_TXT[1], WHITE_TXT[2], WHITE_TXT[3])
                end
                b.bg:SetAtlas(ART_OPEN)
                b.ring:SetAtlas(ART_OPEN)
                b.icon:SetDesaturated(b.gate ~= nil)
                b.icon:SetAlpha(b.gate and 0.55 or 1)
            elseif st == 'done' then
                b.rank:SetTextColor(GREEN[1], GREEN[2], GREEN[3])
                b.bg:SetAtlas(ART_FULL)
                b.ring:SetAtlas(ART_FULL)
                b.icon:SetDesaturated(false)
                b.icon:SetAlpha(1)
            elseif st == 'over' then
                b.rank:SetTextColor(WHITE_TXT[1], WHITE_TXT[2], WHITE_TXT[3])
                b.bg:SetAtlas(ART_FULL)
                b.ring:SetAtlas(ART_FULL)
                b.icon:SetDesaturated(false)
                b.icon:SetAlpha(1)
            else
                b.rank:SetTextColor(0.72, 0.72, 0.72)
                b.bg:SetAtlas(ART_NONE)
                b.ring:SetAtlas(ART_LOCK)
                b.icon:SetDesaturated(true)
                b.icon:SetAlpha(0.38)
            end
        end
    end

    PaintLinks()

    if strip.status then
        if curMode then
            strip.status:SetText(string.format(L['上限 %d · 已投 %d · 可投 %d'], SEASON_CAP, spent, left))
        else
            strip.status:SetText(string.format(L['上限 %d · 可投 %d · 方案还需 %d'], SEASON_CAP, left, total))
        end
    end
    if strip.apply then strip.apply:SetShown(not curMode) end
    for i = 1, #(strip.tabs or {}) do
        local b = strip.tabs[i]
        local on = (i == presetIdx)
        local fs = b.GetFontString and b:GetFontString()
        if fs and fs.SetTextColor then
            if on then
                fs:SetTextColor(1, 0.88, 0.42)
            else
                fs:SetTextColor(0.60, 0.58, 0.54)
            end
        end
        b:SetAlpha(on and 1 or 0.45)
    end
    Emblem(true)
end

LP.Refresh = Refresh

local function UpdateCardState(on)
    if not card then return end
    if card.glow then card.glow:SetAlpha(on and 1 or 0) end
end

Emblem = function(on)
    local tp = host and host.TreePage and host.TreePage.LegacyTreeTraitPanel
    if not tp then return end
    if LP.nativeHide == nil then
        LP.nativeHide = {}
        local function collect(parent)
            if not parent then return end
            for _, c in ipairs({ parent:GetChildren() }) do
                if c ~= page and c ~= card and c.GetObjectType then
                    local ot = c:GetObjectType()
                    local w = math.floor(c:GetWidth() or 0)
                    local h = math.floor(c:GetHeight() or 0)
                    if (ot == 'CheckButton' and w == 109)
                        or (ot == 'Button' and (w == 164 or (w >= 20 and w <= 30 and h <= 30))) then
                        LP.nativeHide[#LP.nativeHide + 1] = { obj = c, shown = c:IsShown() }
                    end
                end
            end
        end
        collect(tp)
        collect(host and host.TreePage)
        collect(host)
    end
    for i = 1, #LP.nativeHide do
        local it = LP.nativeHide[i]
        local o = it.obj
        if o and o.SetShown then
            if not it.hooked then
                it.hooked = true
                pcall(o.HookScript, o, 'OnShow', function(self)
                    if page and page:IsShown() then self:Hide() end
                end)
            end
            if on then
                o:Hide()
            elseif it.shown then
                o:Show()
            end
        end
    end
end

function LP.Toggle(on)
    if not page then return end
    if on == nil then on = not page:IsShown() end
    GameTooltip:Hide()
    if on then
        page:Show()
        Refresh()
    else
        page:Hide()
    end
    Emblem(on)
    UpdateCardState(on)
end

local function HookCards(panel)
    if not (panel and panel.treeButtons) then return end
    for i = 1, #panel.treeButtons do
        local b = panel.treeButtons[i]
        if b and not b.__dfLegacyCard then
            b.__dfLegacyCard = true
            b:HookScript('OnClick', function() LP.Toggle(false) end)
        end
    end
end

local function BuildCard()
    local tp = host.TreePage
    card = CreateFrame('Button', 'DungeonsForeverLegacyCard', tp)
    card:SetSize(CARD_W, CARD_H)
    card:SetPoint('TOPLEFT', tp, 'TOPLEFT', CARD_X, CARD_Y)
    card:SetFrameLevel((tp:GetFrameLevel() or 100) + 12)

    card.card = Tex(card, 'BACKGROUND', 'Legacy-Tree-Frame-Card', 142, 93)
    card.card:SetPoint('CENTER')

    card.glow = Tex(card, 'BACKGROUND', 'Legacy-Tree-Frame-Card-Glow', 95, 76)
    card.glow:SetPoint('RIGHT', card.card, 'RIGHT', -10, 0)
    card.glow:SetAlpha(0)

    card.icon = card:CreateTexture(nil, 'ARTWORK')
    card.icon:SetSize(ICON_W, ICON_H)
    card.icon:SetPoint('CENTER')
    card.icon:SetTexture(BRAND)

    local okm, mask = pcall(function() return card:CreateMaskTexture() end)
    if okm and mask then
        pcall(mask.SetTexture, mask, 130924)
        pcall(mask.SetSize, mask, ICON_W, ICON_H)
        pcall(mask.SetPoint, mask, 'CENTER')
        if card.icon.AddMaskTexture then
            pcall(card.icon.AddMaskTexture, card.icon, mask)
        end
        card.mask = mask
    end

    card.ring = Tex(card, 'OVERLAY', 'Legacy-Tree-Frame-Card-Ring', 70, 70)
    card.ring:SetPoint('CENTER')

    local hl = card:CreateTexture(nil, 'HIGHLIGHT')
    hl:SetAtlas('Legacy-Tree-Frame-Card-Ring')
    hl:SetSize(70, 70)
    hl:SetPoint('TOPLEFT', card, 'TOPLEFT', 0, 0)
    hl:SetBlendMode('ADD')
    hl:SetAlpha(0.5)

    card:SetScript('OnClick', function() LP.Toggle() end)
    card:SetScript('OnEnter', function(self)
        GameTooltip:SetOwner(self, 'ANCHOR_RIGHT')
        GameTooltip:SetText(L['传承推荐加点'], 1, 0.82, 0)
        GameTooltip:AddLine(L['三棵树并排展示推荐方案，点开后再点一次收起'], 0.9, 0.9, 0.9, true)
        if ns.hui and ns.hui.ShowNativeTip then pcall(ns.hui.ShowNativeTip, GameTooltip) end
        GameTooltip:Show()
    end)
    card:SetScript('OnLeave', function()
        GameTooltip:Hide()
        UpdateCardState(page and page:IsShown())
    end)
end

local function DoApply(m, p, cap)
    local got, purchased = {}, 0
    for _ = 1, 200 do
        local moved = false
        for i = 1, #p.seq do
            if purchased >= cap then break end
            local it = p.seq[i]
            local nd = FindNode(m, it)
            if nd then
                local eff = math.max(nd.cur, got[nd.nid] or 0)
                local want = math.min(it.rank or it[4], nd.max)
                if eff < want then
                    local okn, ni = pcall(Traits.GetNodeInfo, m.cid, nd.nid)
                    if okn and type(ni) == 'table' then
                        local eid = type(ni.activeEntry) == 'table' and ni.activeEntry.entryID or nil
                        local okc, can = pcall(Traits.CanPurchaseRank, m.cid, nd.nid, eid)
                        if okc and can then
                            local okp, r = pcall(Traits.PurchaseRank, m.cid, nd.nid)
                            if okp and r ~= false then
                                got[nd.nid] = eff + 1
                                purchased = purchased + 1
                                moved = true
                            end
                        end
                    end
                end
            end
        end
        if purchased >= cap or not moved then break end
    end
    if purchased <= 0 then
        print('|cff46bf72[传承]|r ' .. L['没有可以投入的点数'])
        return 0
    end
    local okc, r = pcall(Traits.CommitConfig, m.cid)
    if not okc or r == false then
        pcall(Traits.RollbackConfig, m.cid)
        print('|cffff5040[传承]|r ' .. L['提交失败，已回滚'])
        return 0
    end
    print('|cff46bf72[传承]|r ' .. string.format(L['已按推荐投入 %d 点'], purchased))
    Refresh()
    return purchased
end

function LP.Apply()
    local m = BuildModel()
    if not m then
        print('|cff46bf72[传承]|r ' .. L['读不到传承配置'])
        return
    end
    local p = Preset()
    if not p then return end
    local _, _, total = MapPreset(m, p)
    if total <= 0 then
        print('|cff46bf72[传承]|r ' .. L['当前方案已经达成'])
        return
    end
    local spent = 0
    for t = 1, 3 do
        spent = spent + ((m.trees[t] and m.trees[t].spent) or 0)
    end
    local left = math.max(0, SEASON_CAP - spent)
    local spend = math.min(total, left)
    if spend <= 0 then
        print('|cff46bf72[传承]|r ' .. L['本赛季点数已经用满'])
        return
    end
    local msg = string.format(L['将按推荐顺序投入 %d 点（本赛季上限 %d 点，已投 %d 点，方案共需 %d 点）。'], spend, SEASON_CAP, spent, total)
        .. '\n' .. L['传承点数投入后不可退还，确定继续？']
    StaticPopupDialogs['DF_LEGACY_PRESET_APPLY'] = {
        text = msg,
        button1 = L['确定'],
        button2 = L['取消'],
        OnShow = function(self)
            if ns.SkinPopupFont then ns.SkinPopupFont(self) end
        end,
        OnAccept = function() DoApply(m, p, spend) end,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        preferredIndex = 3,
    }
    StaticPopup_Show('DF_LEGACY_PRESET_APPLY')
end

local function Ensure()
    if not host then return false end
    local tp = host.TreePage
    if not tp or not tp.LegacyTreeSelectionPanel then return false end
    HookCards(tp.LegacyTreeSelectionPanel)
    if built and card and page and card:GetParent() == tp
        and page:GetParent() == tp.LegacyTreeTraitPanel then return true end
    Model = BuildModel()
    if not Model then return false end
    if page then pcall(page.Hide, page) end
    if card then pcall(card.Hide, card) end
    BuildCard()
    BuildPage()
    built = true
    return true
end

local function Watch(f)
    if ticking then return end
    ticking = CreateFrame('Frame')
    local acc, tries = 0, 0
    ticking:SetScript('OnUpdate', function(self, dt)
        acc = acc + (dt or 0)
        if acc < 0.25 then return end
        acc = 0
        tries = tries + 1
        if Ensure() or tries > 80 or not f:IsShown() then
            ticking = nil
            self:SetScript('OnUpdate', nil)
            if page then LP.Toggle(false) end
        end
    end)
end

function LP.Attach(frame)
    host = frame
    local db = ns.ClassDB and ns.ClassDB().legacy
    if db and type(db.preset) == 'number' and Plans and Plans[db.preset] then
        presetIdx = db.preset
    end
    if not frame.__dfLegacyHook then
        frame.__dfLegacyHook = true
        frame:HookScript('OnShow', function()
            if not Ensure() then Watch(frame) end
            if page then LP.Toggle(false) end
        end)
        frame:HookScript('OnHide', function()
            if page then LP.Toggle(false) end
        end)
    end
    return Ensure()
end

local function TryAttach()
    if type(Traits) ~= 'table' then return false end
    local f = _G.LegacySystemFrame
    if not f and C_AddOns and C_AddOns.LoadAddOn then
        pcall(C_AddOns.LoadAddOn, 'Blizzard_LegacySystem')
        f = _G.LegacySystemFrame
    end
    if not f then return false end
    return LP.Attach(f)
end

ns.Init(function()
    local guard = CreateFrame('Frame')
    local events = { 'TRAIT_CONFIG_UPDATED', 'TRAIT_CONFIG_CREATED', 'PLAYER_TALENT_UPDATE',
        'CURRENCY_DISPLAY_UPDATE', 'PLAYER_LEVEL_UP' }
    for i = 1, #events do pcall(guard.RegisterEvent, guard, events[i]) end
    guard:SetScript('OnEvent', function()
        if page and page:IsShown() then Refresh() end
    end)

    local boot = CreateFrame('Frame')
    boot:RegisterEvent('PLAYER_LOGIN')
    boot:RegisterEvent('PLAYER_ENTERING_WORLD')
    boot:RegisterEvent('ADDON_LOADED')
    boot:SetScript('OnEvent', function(self, event, arg1)
        if event == 'ADDON_LOADED' and arg1 ~= 'Blizzard_LegacySystem' then return end
        TryAttach()
    end)

    if IsLoggedIn and IsLoggedIn() then TryAttach() end
end)
