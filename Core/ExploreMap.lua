local ADDON_NAME, ns = ...
local EG = ns.ExploreModule
if not EG then return end
local DG = ns.DungeonModule
local L = ns.L
local BOOKS = ns.ExploreBooks
local SETS = ns.ExploreBookSet
local AMap = ns.AreaMap or {}
local UNVER = ns.ExploreUnverIDs or {}

local SET_ORDER = { 1, 35, 45, 60 }
local CONTINENT_PENALTY = 20000
local UPDATE_TICK = 0.1

local BOOK_ICON = "Interface\\Icons\\INV_Misc_Book_09"
local DIAL_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\route_dial"
local DART_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\route_arrow"
local GRAVE_TEX = "Interface\\RaidFrame\\Raid-Icon-Rez"
local GRAVE_OWN_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\SpiritPin"
local GRAVE_DISC_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc"
local GRAVE_RING_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\CheckRing"
local GRAVE_SIZE = 22
local GRAVE_DOT = 0.38
local GRAVE_DOT_IN = 0.30
local SIDE_COL = {
    [0] = { 1.00, 0.84, 0.08 },
    [1] = { 0.16, 0.55, 1.00 },
    [2] = { 0.94, 0.14, 0.10 },
}
local SIDE_TXT = { [0] = "共用", [1] = "联盟", [2] = "部落" }
ns.SideColor = SIDE_COL

local route, skipped, routeOn = {}, {}, false
local manualOff = false
local manualTrack
local tracker
local updateTrackerFn
local settingsFrame
local pins, pinPool = {}, {}
local graves, gravePool = {}, {}
local lines, linePool = {}, {}
local meLineLn

local DEF_CFG = {
    connect = "near",
    autoRecalc = true,
    showUnver = false,
    autoRoute = false,
    bookMode = "manual",
    pinSize = 14,
    showNum = true,
    showPins = false,
    showLines = false,
    showMeLine = true,
    showGrave = false,
    graveStyle = "native",
    lineW = 2,
    showCompass = true,
    lockPos = false,
    hudScale = 1,
}
local function cfg()
    local db = ns.DB and ns.DB()
    if not db then return DEF_CFG end
    db.explore = db.explore or {}
    local s = db.explore.mapCfg
    if not s then
        s = {}
        db.explore.mapCfg = s
    end
    for k, v in pairs(DEF_CFG) do
        if s[k] == nil then s[k] = v end
    end
    s.gravePx = nil
    s.gravePinSize = nil
    return s
end

local function uiMapOf(areaID)
    return areaID and AMap[areaID] or nil
end

local function alive(mapID)
    if not mapID then return false end
    if not (C_Map and C_Map.GetMapInfo) then return true end
    local ok, mi = pcall(C_Map.GetMapInfo, mapID)
    return ok and mi ~= nil
end

local function worldPos(mapID, x, y)
    if not mapID or not (C_Map and C_Map.GetWorldPosFromMapPos and CreateVector2D) then
        return nil
    end
    local ok, cont, pos = pcall(C_Map.GetWorldPosFromMapPos, mapID, CreateVector2D(x, y))
    if ok and cont and pos then return cont, pos.x, pos.y end
    return nil
end

local function playerPos()
    if not (C_Map and C_Map.GetBestMapForUnit and C_Map.GetPlayerMapPosition) then
        return nil
    end
    local ok, m = pcall(C_Map.GetBestMapForUnit, "player")
    if not ok or not m or not alive(m) then return nil end
    local ok2, p = pcall(C_Map.GetPlayerMapPosition, m, "player")
    if not ok2 or not p or p.x == 0 and p.y == 0 then return nil end
    return worldPos(m, p.x, p.y)
end

local function topParent(mapID)
    local guard = 0
    while mapID and guard < 8 do
        guard = guard + 1
        if not (C_Map and C_Map.GetMapInfo) then return mapID end
        local ok, info = pcall(C_Map.GetMapInfo, mapID)
        if not ok or not info or not info.parentMapID or info.parentMapID <= 0 then
            return mapID
        end
        mapID = info.parentMapID
    end
    return mapID
end

local function project(uiMap, x, y, disp)
    if not uiMap or not disp then return nil end
    if uiMap == disp then return x, y end
    if topParent(uiMap) ~= topParent(disp) then return nil end
    if not (C_Map and C_Map.GetMapRectOnMap) then return nil end
    local ok, left, right, top, bottom = pcall(C_Map.GetMapRectOnMap, uiMap, disp)
    if not ok or not left or right == left then return nil end
    return left + x * (right - left), top + y * (bottom - top)
end

local function countDone()
    local n = 0
    for _, rec in ipairs(BOOKS or {}) do
        if EG.IsBookFound(rec[1]) then n = n + 1 end
    end
    return n
end

local function stepOfRec(rec)
    if not rec then return nil end
    if type(rec[3]) == "number" and type(rec[4]) == "number" then
        local s = { rec = rec, area = rec[2], x = rec[3] / 100, y = rec[4] / 100 }
        s.cont, s.wx, s.wy = worldPos(uiMapOf(s.area), s.x, s.y)
        return s
    end
    local alt = rec[7]
    if type(alt) == "table" then
        for _, a in ipairs(alt) do
            if type(a[2]) == "number" and type(a[3]) == "number" then
                local s = { rec = rec, alt = true, area = a[1],
                    x = a[2] / 100, y = a[3] / 100 }
                s.cont, s.wx, s.wy = worldPos(uiMapOf(s.area), s.x, s.y)
                return s
            end
        end
    end
    return nil
end

local function bookSet(id)
    return (SETS and SETS[id]) or 1
end

local function buildCandidates()
    local cands = {}
    local includeUnver = cfg().showUnver == true
    for i, rec in ipairs(BOOKS or {}) do
        local id = rec[1]
        if UNVER[id] and not includeUnver then
        elseif not EG.IsBookFound(id) and not skipped[id] then
            local set = bookSet(id)
            if type(rec[3]) == "number" and type(rec[4]) == "number" then
                cands[#cands + 1] = { rec = rec, set = set,
                    area = rec[2], x = rec[3] / 100, y = rec[4] / 100 }
            end
            local alt = rec[7]
            if type(alt) == "table" then
                for _, a in ipairs(alt) do
                    if type(a[2]) == "number" and type(a[3]) == "number" then
                        cands[#cands + 1] = { rec = rec, set = set, alt = true,
                            area = a[1], x = a[2] / 100, y = a[3] / 100 }
                    end
                end
            end
        end
    end
    for _, c in ipairs(cands) do
        c.cont, c.wx, c.wy = worldPos(uiMapOf(c.area), c.x, c.y)
    end
    return cands
end

local function costOf(a, b)
    if a.wx and b.wx then
        local d = math.sqrt((a.wx - b.wx) ^ 2 + (a.wy - b.wy) ^ 2)
        if a.cont ~= b.cont then d = d + CONTINENT_PENALTY end
        return d
    end
    return (b.area or 0) * 10000 + b.x * 100 + b.y
end

local function planOrder(bucket)
    local path, used = {}, {}
    for _, c in ipairs(bucket) do
        if not used[c.rec] then
            used[c.rec] = true
            path[#path + 1] = c
        end
    end
    return path
end

local function planArea(bucket, start)
    local path, used = {}, {}
    local groups = {}
    for _, c in ipairs(bucket) do
        groups[c.area] = groups[c.area] or {}
        local g = groups[c.area]
        g[#g + 1] = c
    end
    local cur = start
    while true do
        local bestG, bestD
        for area, g in pairs(groups) do
            local gmin
            for _, c in ipairs(g) do
                if not used[c.rec] then
                    local d = costOf(cur, c)
                    if not gmin or d < gmin then gmin = d end
                end
            end
            if gmin and (not bestD or gmin < bestD) then
                bestG, bestD = area, gmin
            end
        end
        if not bestG then break end
        local g = groups[bestG]
        groups[bestG] = nil
        while true do
            local best, bestD
            for _, c in ipairs(g) do
                if not used[c.rec] then
                    local d = costOf(cur, c)
                    if not bestD or d < bestD then best, bestD = c, d end
                end
            end
            if not best then break end
            used[best.rec] = true
            path[#path + 1] = best
            cur = best
        end
    end
    return path
end

local function planNear(bucket, start)
    local path, used = {}, {}
    local cur = start
    while true do
        local best, bestD
        for _, c in ipairs(bucket) do
            if not used[c.rec] then
                local d = costOf(cur, c)
                if not bestD or d < bestD then best, bestD = c, d end
            end
        end
        if not best then break end
        used[best.rec] = true
        path[#path + 1] = best
        cur = best
    end
    local n = #path
    if n > 2 and start.wx and path[1].wx then
        local improved, guard = true, 0
        while improved and guard < 50 do
            improved = false
            guard = guard + 1
            for i = 1, n - 1 do
                for j = i + 1, n do
                    local a = (i == 1) and start or path[i - 1]
                    local b, c, d = path[i], path[j], path[j + 1]
                    local before = costOf(a, b) + (d and costOf(c, d) or 0)
                    local after = costOf(a, c) + (d and costOf(b, d) or 0)
                    if after < before - 0.5 then
                        local lo, hi = i, j
                        while lo < hi do
                            path[lo], path[hi] = path[hi], path[lo]
                            lo = lo + 1
                            hi = hi - 1
                        end
                        improved = true
                    end
                end
            end
        end
    end
    return path
end

local function BuildRoute()
    for i = #route, 1, -1 do route[i] = nil end
    local cands = buildCandidates()
    local mode = cfg().connect or "near"
    local cont, px, py = playerPos()
    local start = { cont = cont, wx = px, wy = py, area = 0, x = 0, y = 0 }
    for _, setID in ipairs(SET_ORDER) do
        local bucket = {}
        for _, c in ipairs(cands) do
            if c.set == setID then bucket[#bucket + 1] = c end
        end
        local path
        if mode == "order" then
            path = planOrder(bucket)
        elseif mode == "area" then
            path = planArea(bucket, start)
        else
            path = planNear(bucket, start)
        end
        for _, st in ipairs(path) do
            route[#route + 1] = st
            start = st
        end
    end
    return route
end

ns.ExploreMapPlanRoute = BuildRoute

local function RouteStepOf(rec, area, x, y)
    if not routeOn then return nil end
    for i, s in ipairs(route) do
        if s.rec == rec and s.area == area
            and math.abs(s.x - x) < 0.0005 and math.abs(s.y - y) < 0.0005 then
            return i
        end
    end
end

local function releaseLines()
    for i = #lines, 1, -1 do
        lines[i]:Hide()
        linePool[#linePool + 1] = lines[i]
        lines[i] = nil
    end
end

local function drawLine(canvas, x1, y1, x2, y2, thick, col)
    local ln = linePool[#linePool]
    if ln then linePool[#linePool] = nil else
        local ok, l = pcall(canvas.CreateLine, canvas, nil, "OVERLAY")
        if not ok or not l then return end
        ln = l
    end
    pcall(ln.SetColorTexture, ln,
        col and col[1] or 0.3, col and col[2] or 0.8,
        col and col[3] or 1, col and col[4] or 0.8)
    pcall(ln.SetThickness, ln, thick or 2)
    pcall(ln.SetStartPoint, ln, "TOPLEFT", canvas, x1, -y1)
    pcall(ln.SetEndPoint, ln, "TOPLEFT", canvas, x2, -y2)
    ln:Show()
    lines[#lines + 1] = ln
    return ln
end

local C_ME_LINE = { 1, 0.82, 0.24, 0.95 }
local function waypointMatches(s2)
    if not (C_Map and C_Map.GetUserWaypoint) then return true end
    local ok, wp = pcall(C_Map.GetUserWaypoint)
    if not ok or not wp then return false end
    local wmid = wp.mapID or wp.uiMapID
    local pos = wp.position
    local wx = pos and pos.x or wp.x
    local wy = pos and pos.y or wp.y
    if not wmid or type(wx) ~= "number" or type(wy) ~= "number" then return true end
    if wmid ~= uiMapOf(s2.area) then return false end
    return math.abs(wx - s2.x) < 0.0005 and math.abs(wy - s2.y) < 0.0005
end
local function meLineTarget()
    local s2
    if (cfg().bookMode or "manual") == "auto" then
        s2 = route[1]
    else
        s2 = manualTrack and not EG.IsBookFound(manualTrack[1]) and stepOfRec(manualTrack) or nil
    end
    if not s2 then return nil end
    if not waypointMatches(s2) then return nil end
    return s2
end
local function meLineMove()
    local ln = meLineLn
    if not ln then return end
    if not (WorldMapFrame and WorldMapFrame.IsShown and WorldMapFrame:IsShown()) then return end
    local s2 = meLineTarget()
    local okm, mm = false, nil
    if C_Map and C_Map.GetBestMapForUnit then
        okm, mm = pcall(C_Map.GetBestMapForUnit, "player")
    end
    if not (s2 and okm and mm and alive(mm)) then ln:Hide() return end
    local okp, pp = pcall(C_Map.GetPlayerMapPosition, mm, "player")
    if not okp or not pp or (pp.x == 0 and pp.y == 0) then ln:Hide() return end
    local okd, disp = pcall(WorldMapFrame.GetMapID, WorldMapFrame)
    local okc, canvas = pcall(WorldMapFrame.GetCanvas, WorldMapFrame)
    if not okd or not disp or not okc or not canvas then ln:Hide() return end
    if ln.GetParent and ln:GetParent() ~= canvas then ln:Hide() return end
    local okW, w = pcall(canvas.GetWidth, canvas)
    local okH, h = pcall(canvas.GetHeight, canvas)
    w = (okW and type(w) == "number" and w > 0 and w) or 700
    h = (okH and type(h) == "number" and h > 0 and h) or 500
    local pux, puy = project(mm, pp.x, pp.y, disp)
    local tux, tuy = project(uiMapOf(s2.area), s2.x, s2.y, disp)
    if not (pux and tux) then ln:Hide() return end
    pcall(ln.SetStartPoint, ln, "TOPLEFT", canvas, pux * w, -puy * h)
    pcall(ln.SetEndPoint, ln, "TOPLEFT", canvas, tux * w, -tuy * h)
    ln:Show()
end

local function pinTip(pin)
    if not GameTooltip then return end
    GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
    local rec = pin.rec
    local nm = DG and DG.ItemName and DG.ItemName(rec[1]) or rec[1]
    GameTooltip:AddLine(tostring(nm), 1, 0.82, 0.24)
    GameTooltip:AddLine(format("%s  (%.1f, %.1f)",
        tostring(EG.ZoneName(rec[2], rec[2])), rec[3] or 0, rec[4] or 0), 1, 1, 1)
    if UNVER[rec[1]] then
        GameTooltip:AddLine(L["待确认"], 0.9, 0.6, 0.3)
    end
    local step = pin.step
    if step then
        GameTooltip:AddLine(format(L["路线第%d站"], step), 0.4, 0.8, 1)
    end
    GameTooltip:AddLine(format(L["收集 %d/%d"], countDone(), #(BOOKS or {})), 0.7, 0.7, 0.7)
    if (cfg().bookMode or "manual") == "manual" then
        GameTooltip:AddLine(L["点击追踪此书"], 0.5, 1, 0.5)
    end
    GameTooltip:AddLine(L["Shift+点击打卡"], 0.5, 1, 0.5)
    GameTooltip:Show()
end

local function pinAcquire(canvas)
    local p = pinPool[#pinPool]
    if p then pinPool[#pinPool] = nil else
        p = CreateFrame("Button", nil, canvas)
        p.tex = p:CreateTexture(nil, "OVERLAY")
        p.tex:SetAllPoints()
        p.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        p.badge = p:CreateFontString(nil, "OVERLAY", "NumberFontNormal")
        p.badge:SetPoint("BOTTOMRIGHT", 3, -1)
        p:RegisterForClicks("LeftButtonUp")
        p:SetScript("OnEnter", pinTip)
        p:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
        p:SetScript("OnClick", function(self)
            if IsShiftKeyDown() and self.rec then
                if GameTooltip then GameTooltip:Hide() end
                EG.ToggleBookFound(self.rec[1])
            elseif self.rec and (cfg().bookMode or "manual") == "manual" then
                manualTrack = self.rec
                if updateTrackerFn then updateTrackerFn() end
                if GameTooltip then GameTooltip:Hide() end
            end
        end)
    end
    p:SetParent(canvas)
    p.tex:SetDesaturated(false)
    p.tex:SetAlpha(1)
    return p
end

local function releasePins()
    for i = #pins, 1, -1 do
        local p = pins[i]
        p:Hide()
        p:ClearAllPoints()
        pins[i] = nil
        pinPool[#pinPool + 1] = p
    end
end

local function graveTip(self)
    if not GameTooltip then return end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    GameTooltip:SetText(L["灵魂医者"], 0.72, 0.92, 1)
    if self.gzone and self.gzone ~= "" then
        GameTooltip:AddLine(self.gzone, 0.7, 0.7, 0.7)
    end
    local col = SIDE_COL[self.gside or 0] or SIDE_COL[0]
    GameTooltip:AddLine(L[SIDE_TXT[self.gside or 0]], col[1], col[2], col[3])
    GameTooltip:Show()
end

local function graveAcquire(canvas)
    local p = gravePool[#gravePool]
    if p then gravePool[#gravePool] = nil else
        p = CreateFrame("Button", nil, canvas)
        p.__grave = true
        p.disc = p:CreateTexture(nil, "OVERLAY")
        p.disc:SetDrawLayer("OVERLAY", -2)
        p.disc:SetAllPoints()
        p.disc:SetTexture(GRAVE_DISC_TEX)
        p.disc:SetVertexColor(0.05, 0.05, 0.06, 0.88)
        p.disc:Hide()
        p.ring = p:CreateTexture(nil, "OVERLAY")
        p.ring:SetDrawLayer("OVERLAY", -1)
        p.ring:SetAllPoints()
        p.ring:SetTexture(GRAVE_RING_TEX)
        p.ring:SetVertexColor(0.78, 0.74, 0.62, 0.9)
        p.ring:Hide()
        p.tex = p:CreateTexture(nil, "OVERLAY")
        p.tex:SetDrawLayer("OVERLAY", 0)
        p.tex:SetPoint("CENTER", p, "CENTER", 0, 0)
        p.tex:SetSize(22, 22)
        p.tex:SetTexture(GRAVE_TEX)
        p.dotEdge = p:CreateTexture(nil, "OVERLAY")
        p.dotEdge:SetDrawLayer("OVERLAY", 1)
        p.dotEdge:SetTexture(GRAVE_DISC_TEX)
        p.dotEdge:SetVertexColor(0.03, 0.03, 0.04, 0.92)
        p.dot = p:CreateTexture(nil, "OVERLAY")
        p.dot:SetDrawLayer("OVERLAY", 2)
        p.dot:SetTexture(GRAVE_DISC_TEX)
        p:RegisterForClicks("LeftButtonUp")
        p:SetScript("OnEnter", graveTip)
        p:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    end
    p:SetParent(canvas)
    p.tex:SetAlpha(1)
    return p
end

local function releaseGraves()
    for i = #graves, 1, -1 do
        local p = graves[i]
        p:Hide()
        p:ClearAllPoints()
        graves[i] = nil
        gravePool[#gravePool + 1] = p
    end
end

local function mapScale()
    local sc = WorldMapFrame.ScrollContainer
    if sc and sc.GetCanvasScale then
        local ok, v = pcall(sc.GetCanvasScale, sc)
        if ok and type(v) == "number" and v > 0 then return v end
    end
    return 1
end

local graveFitMap = {}

local function graveFit(disp, scale)
    local v = graveFitMap[disp]
    if not v or scale < v then
        v = scale
        graveFitMap[disp] = v
    end
    return v
end

function ns.ExploreMapRefresh()
    if ns.MapWorldModule and ns.MapWorldModule.Active and ns.MapWorldModule.Active() then
        releasePins()
        releaseGraves()
        releaseLines()
        return
    end
    if not (WorldMapFrame and WorldMapFrame.IsShown and WorldMapFrame:IsShown()
            and WorldMapFrame.GetMapID) then return end
    if routeOn and cfg().autoRecalc ~= false and route[1]
            and EG.IsBookFound(route[1].rec[1]) then
        BuildRoute()
        if tracker then updateTrackerFn() end
    end
    releasePins()
    releaseGraves()
    releaseLines()
    local okID, disp = pcall(WorldMapFrame.GetMapID, WorldMapFrame)
    if not okID or not disp or not alive(disp) then return end
    local okC, canvas = pcall(WorldMapFrame.GetCanvas, WorldMapFrame)
    if not okC or not canvas then return end
    local okW, w = pcall(canvas.GetWidth, canvas)
    local okH, h = pcall(canvas.GetHeight, canvas)
    w = (okW and type(w) == "number" and w > 0 and w) or 700
    h = (okH and type(h) == "number" and h > 0 and h) or 500
    local c = cfg()
    local scale = mapScale()
    local size = (c.pinSize or 20) / scale

    if c.showPins == true then
        for _, rec in ipairs(BOOKS or {}) do
        local isUnver = UNVER[rec[1]] == true
        if not EG.IsBookFound(rec[1]) and not (isUnver and not c.showUnver) then
            local locs = {}
            if type(rec[3]) == "number" and type(rec[4]) == "number" then
                locs[#locs + 1] = { rec[2], rec[3] / 100, rec[4] / 100 }
            end
            local alt = rec[7]
            if type(alt) == "table" then
                for _, a in ipairs(alt) do
                    if type(a[2]) == "number" and type(a[3]) == "number" then
                        locs[#locs + 1] = { a[1], a[2] / 100, a[3] / 100 }
                    end
                end
            end
            for _, loc in ipairs(locs) do
                local ui = uiMapOf(loc[1])
                local x, y = project(ui, loc[2], loc[3], disp)
                if x then
                    local p = pinAcquire(canvas)
                    p.rec, p.step = rec, RouteStepOf(rec, loc[1], loc[2], loc[3])
                    p.badge:SetText(p.step and tostring(p.step) or "")
                    p.badge:SetShown(c.showNum ~= false)
                    p.badge:SetScale(1 / scale)
                    local ic = DG and DG.ItemIcon and DG.ItemIcon(rec[1])
                    p.tex:SetTexture(type(ic) == "string" and ic or BOOK_ICON)
                    if isUnver then
                        pcall(p.tex.SetDesaturated, p.tex, true)
                        p.tex:SetAlpha(0.55)
                    end
                    p:SetSize(size, size)
                    p:SetPoint("CENTER", canvas, "TOPLEFT", x * w, -y * h)
                    p:SetFrameLevel(canvas:GetFrameLevel() + 20)
                    p:Show()
                    pins[#pins + 1] = p
                end
            end
        end
    end
    end

    if c.showGrave == true then
        local flat = ns.GravePos[disp]
        if type(flat) == "table" then
            local fit = graveFit(disp, scale)
            local zoom = scale / fit
            if zoom > 2 then zoom = 2 end
            local gsize = GRAVE_SIZE * zoom / scale
            local zone
            if C_Map and C_Map.GetMapInfo then
                local okm, mi = pcall(C_Map.GetMapInfo, disp)
                if okm and mi then zone = mi.name end
            end
            for i = 1, #flat - 2, 3 do
                local p = graveAcquire(canvas)
                p.gzone, p.gmap = zone, disp
                local side = flat[i + 2] or 0
                p.gside = side
                p:SetSize(gsize, gsize)
                local st = c.graveStyle
                local circle = (st == "circle")
                if circle or st == "custom" then
                    p.tex:SetTexture(GRAVE_OWN_TEX)
                else
                    p.tex:SetTexture(GRAVE_TEX)
                end
                p.tex:SetSize(circle and gsize * 0.68 or gsize, circle and gsize * 0.68 or gsize)
                p.disc:SetShown(circle)
                p.ring:SetShown(circle)
                local col = SIDE_COL[side] or SIDE_COL[0]
                local ds = gsize * GRAVE_DOT
                local di = ds * GRAVE_DOT_IN
                p.dot:SetVertexColor(col[1], col[2], col[3], 1)
                p.dot:SetSize(ds, ds)
                p.dot:ClearAllPoints()
                p.dot:SetPoint("CENTER", p, "TOPRIGHT", -di, -di)
                p.dotEdge:SetSize(ds * 1.42, ds * 1.42)
                p.dotEdge:ClearAllPoints()
                p.dotEdge:SetPoint("CENTER", p, "TOPRIGHT", -di, -di)
                p:SetPoint("CENTER", canvas, "TOPLEFT", flat[i] / 100 * w, -flat[i + 1] / 100 * h)
                p:SetFrameLevel(canvas:GetFrameLevel() + 7005)
                p:Show()
                graves[#graves + 1] = p
            end
        end
    end

    if routeOn and c.showLines == true and c.showPins == true then
        local lw = c.lineW or 2
        local prevX, prevY
        for _, s in ipairs(route) do
            local x, y = project(uiMapOf(s.area), s.x, s.y, disp)
            if x and prevX then
                drawLine(canvas, prevX * w, prevY * h, x * w, y * h, lw / scale)
            end
            prevX, prevY = x, y
        end
    end

    meLineLn = nil
    if c.showMeLine ~= false then
        local s2 = meLineTarget()
        local okm, mm = false, nil
        if C_Map and C_Map.GetBestMapForUnit then
            okm, mm = pcall(C_Map.GetBestMapForUnit, "player")
        end
        if s2 and okm and mm and alive(mm) then
            local okp, pp = pcall(C_Map.GetPlayerMapPosition, mm, "player")
            if okp and pp and (pp.x ~= 0 or pp.y ~= 0) then
                local pux, puy = project(mm, pp.x, pp.y, disp)
                local tux, tuy = project(uiMapOf(s2.area), s2.x, s2.y, disp)
                if pux and tux then
                    meLineLn = drawLine(canvas, pux * w, puy * h, tux * w, tuy * h,
                        (c.lineW or 2) + 0.5, C_ME_LINE)
                end
            end
        end
    end
end

local function fmtName(rec)
    local nm = DG and DG.ItemName and DG.ItemName(rec[1])
    return tostring(nm or rec[1])
end

local function updateTracker()
    if not tracker then return end
    local done, total = countDone(), #(BOOKS or {})
    tracker.prog:SetText(format("%d/%d", done, total))
    local s
    if (cfg().bookMode or "manual") == "auto" then
        s = route[1]
    elseif manualTrack then
        if EG.IsBookFound(manualTrack[1]) then
            manualTrack = nil
        else
            s = stepOfRec(manualTrack)
        end
    end
    if not s then
        tracker.name:SetText((cfg().bookMode or "manual") == "auto"
            and L["路线完成"] or L["点击图钉选择书籍"])
        tracker.where:SetText("")
        tracker.dist:SetText("")
        tracker.fill:SetWidth(0.001)
        tracker.needle:Hide()
        return
    end
    local rec = s.rec
    tracker.name:SetText(fmtName(rec))
    local zone = tostring(EG.ZoneName(s.area, s.area))
    if s.alt then
        tracker.where:SetText(format("%s (%.1f, %.1f) · %s",
            zone, s.x * 100, s.y * 100, L["另一位置"]))
    else
        tracker.where:SetText(format("%s (%.1f, %.1f)", zone, s.x * 100, s.y * 100))
    end
    local cont, px, py = playerPos()
    if cont and cont == s.cont then
        local dx, dy = s.wx - px, s.wy - py
        tracker.dist:SetText(format(L["%d 码"], math.floor(math.sqrt(dx * dx + dy * dy))))
        local okF, facing = pcall(GetPlayerFacing)
        if okF and facing then
            tracker.needle:SetRotation(math.atan2(dy, dx) - facing)
            if tracker.dial:IsShown() then tracker.needle:Show() end
        else
            tracker.needle:Hide()
        end
    else
        tracker.dist:SetText(L["其他大陆"])
        tracker.needle:Hide()
    end
    local bgw = tracker.barBG:GetWidth()
    if type(bgw) ~= "number" or bgw <= 0 or bgw ~= bgw then bgw = 240 end
    tracker.fill:SetWidth(math.max((total > 0) and (bgw * done / total) or 0, 0.001))
    if settingsFrame and settingsFrame.IsShown and settingsFrame:IsShown()
        and settingsFrame.syncCoord then
        settingsFrame.syncCoord()
    end
end
updateTrackerFn = updateTracker

local function mkBtn(parent, text, w)
    local b = CreateFrame("Button", nil, parent, "BackdropTemplate")
    b:SetSize(w or 46, 20)
    b:EnableMouse(true)
    local fs = b:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    fs:SetAllPoints()
    fs:SetText(text)
    b:SetFontString(fs)
    if ns.hui and ns.hui.SkinButton then
        ns.hui.SkinButton(b)
        fs:SetFont(ns.FONT, 13, "")
    else
        b.bg = b:CreateTexture(nil, "BACKGROUND")
        b.bg:SetAllPoints()
        b.bg:SetColorTexture(1, 1, 1, 0.06)
    end
    return b
end

local function saveTrackerPos(self)
    local db = ns.DB and ns.DB()
    if not db then return end
    local p, _, rp, x, y = self:GetPoint()
    db.explore = db.explore or {}
    db.explore.routePos = { p, rp, x, y }
end

local function relayoutTracker(f)
    if not f then return end
    local show = cfg().showCompass ~= false
    f.dial:SetShown(show)
    f.needle:SetShown(show)
    if show then
        f:SetWidth(320)
        f.name:SetPoint("TOPLEFT", f.dial, "TOPRIGHT", 8, 0)
        f.where:SetPoint("TOPLEFT", f.dial, "TOPRIGHT", 8, -16)
    else
        f:SetWidth(268)
        f.name:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -10)
        f.where:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -26)
    end
end

local function applySettings()
    if tracker then
        tracker:SetScale(cfg().hudScale or 1)
        tracker:SetMovable(cfg().lockPos ~= true)
        relayoutTracker(tracker)
    end
    ns.ExploreMapRefresh()
end

local function recalcAll()
    BuildRoute()
    if updateTrackerFn then updateTrackerFn() end
    ns.ExploreMapRefresh()
end

local C_TXT  = { 0.88, 0.88, 0.88 }
local C_WHT  = { 0.95, 0.96, 0.98 }
local C_GOLD = { 1, 0.82, 0 }

local function setFs(parent, size, col)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    local flags = (ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE")) or "OUTLINE"
    fs:SetFont(ns.FONT, size, flags)
    fs:SetTextColor(col[1], col[2], col[3])
    return fs
end

local function mkToggleRow(content, y, label, get, set, enabledFn)
    local tg = CreateFrame("CheckButton", nil, content)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg.label = setFs(content, 14, C_TXT)
    tg.label:SetJustifyH("LEFT")
    tg.label:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 7)
    tg.label:SetText(label)
    tg:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 10)
    tg:SetChecked(get() and true or false)
    tg:SetScript("OnClick", function(self)
        if enabledFn and not enabledFn() then return end
        set(not (get() and true))
        self:SetChecked(get() and true or false)
        ns.PlaySound(1)
    end)
    tg.sync = function()
        tg:SetChecked(get() and true or false)
        local on = not enabledFn or enabledFn()
        tg:SetAlpha(on and 1 or 0.4)
        tg.label:SetAlpha(on and 1 or 0.45)
    end
    tg:sync()
    return tg
end

local function mkCyclerRow(content, y, label, items, get, set)
    local lab = setFs(content, 14, C_TXT)
    lab:SetJustifyH("LEFT")
    lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 7)
    lab:SetText(label)
    local b = mkBtn(content, "", 74)
    b:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 10)
    b.sync = function()
        local v = get()
        for _, it in ipairs(items) do
            if it.v == v then b:SetText(it.t) return end
        end
        b:SetText(items[1].t)
    end
    b:SetScript("OnClick", function()
        local idx, v = 1, get()
        for i, it in ipairs(items) do
            if it.v == v then idx = i break end
        end
        set(items[idx % #items + 1].v)
        b:sync()
        ns.PlaySound(1)
    end)
    b:sync()
    return b
end

local function mkDropdownRow(content, y, label, items, get, set, onChange)
    local lab = setFs(content, 14, C_TXT)
    lab:SetJustifyH("LEFT")
    lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 7)
    lab:SetText(label)
    local b = mkBtn(content, "", 74)
    b:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 10)
    local function curItem()
        local v = get()
        for _, it in ipairs(items) do
            if it.v == v then return it end
        end
        return items[1]
    end
    b.sync = function() b:SetText(curItem().t) end
    b:SetScript("OnClick", function()
        local cur = get()
        local menu = {}
        for _, it in ipairs(items) do
            menu[#menu + 1] = {
                text = (it.v == cur and "● " or "") .. it.t,
                func = function()
                    set(it.v)
                    b:sync()
                    ns.PlaySound(1)
                    if onChange then onChange() end
                end,
            }
        end
        ns.hui.ShowMenu(menu, { owner = b })
    end)
    b:sync()
    return b
end

local function mkStepperRow(content, y, label, minv, maxv, step, get, set, fmt)
    local lab = setFs(content, 14, C_TXT)
    lab:SetJustifyH("LEFT")
    lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 7)
    lab:SetText(label)
    local plus = mkBtn(content, "+", 20)
    plus:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 10)
    local minus = mkBtn(content, "-", 20)
    minus:SetPoint("TOPRIGHT", plus, "TOPLEFT", -4, 0)
    local val = setFs(content, 13, C_TXT)
    val:SetJustifyH("RIGHT")
    val:SetPoint("RIGHT", minus, "LEFT", -6, 0)
    val:SetPoint("LEFT", lab, "RIGHT", 6, 0)
    local function clamp(v)
        v = math.floor(v + 0.5)
        return math.max(minv, math.min(maxv, v))
    end
    local function bump(dir)
        set(clamp(get() + dir * step))
        val:SetText(fmt(get()))
        recalcAll()
    end
    plus:SetScript("OnClick", function() bump(1) end)
    minus:SetScript("OnClick", function() bump(-1) end)
    val:SetText(fmt(get()))
    local row = {
        sync = function() val:SetText(fmt(get())) end,
        minus = minus, plus = plus,
    }
    return row
end

local function createSettings()
    local host = ns.MainFrame or UIParent
    local f = CreateFrame("Frame", "DFExploreMapSettings", host, "BackdropTemplate")
    f:SetFrameLevel(512)
    f:SetFrameStrata("HIGH")
    f:EnableMouse(true)
    f:SetScript("OnMouseWheel", function() end)
    f:SetWidth(220)
    if host ~= UIParent then
        f:SetPoint("TOPLEFT", host, "TOPRIGHT", 4, 0)
        f:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", 4, 0)
    else
        f:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
        f:SetHeight(600)
    end
    f:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(f, 8, "both", ns.hui.layer.L0) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(f) end

    local title = setFs(f, 16, C_WHT)
    title:SetPoint("TOPLEFT", f, "TOPLEFT", 16, -8)
    title:SetJustifyH("LEFT")
    title:SetText(L["地图设置"])
    local syncers = {}
    local resetB = mkBtn(f, L["重置"], 52)
    resetB:SetPoint("TOPRIGHT", f, "TOPRIGHT", -12, -10)
    resetB:SetScript("OnClick", function()
        ns.PlaySound(1)
        local db = ns.DB and ns.DB()
        if db and db.explore and db.explore.mapCfg then
            local c = db.explore.mapCfg
            for k in pairs(c) do c[k] = nil end
        end
        cfg()
        for _, fn in ipairs(syncers) do fn() end
        applySettings()
        if f.syncCoord then f.syncCoord() end
    end)

    local scroll = CreateFrame("ScrollFrame", nil, f)
    scroll:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -34)
    scroll:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -12, 12)
    local content = CreateFrame("Frame", nil, scroll)
    content:SetWidth(196)
    content:SetHeight(10)
    scroll:SetScrollChild(content)
    scroll:EnableMouseWheel(true)
    content:EnableMouseWheel(true)
    local function wheel(self, delta)
        local maxr = self:GetVerticalScrollRange() or 0
        if maxr <= 0 then return end
        local cur = (self:GetVerticalScroll() or 0) - delta * 28
        self:SetVerticalScroll(math.max(0, math.min(maxr, cur)))
    end
    scroll:SetScript("OnMouseWheel", wheel)
    content:SetScript("OnMouseWheel", wheel)

    local y = -2
    local function hdr(text)
        local fs = setFs(content, 14, C_WHT)
        fs:SetJustifyH("LEFT")
        fs:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y)
        fs:SetText(text)
        y = y - 26
    end

    hdr(L["路线"])
    do
        local dd = mkDropdownRow(content, y, L["连接方式"], {
            { v = "near", t = L["就近串联"] },
            { v = "area", t = L["按区域分堆"] },
            { v = "order", t = L["数据表顺序"] },
        }, function() return cfg().connect or "near" end,
            function(v) cfg().connect = v end, recalcAll)
        syncers[#syncers + 1] = function() dd:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["打卡后自动重算"],
            function() return cfg().autoRecalc ~= false end,
            function(v) cfg().autoRecalc = v recalcAll() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["包含存疑书籍"],
            function() return cfg().showUnver == true end,
            function(v) cfg().showUnver = v recalcAll() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["开图自动亮路线"],
            function() return cfg().autoRoute == true end,
            function(v) cfg().autoRoute = v end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end

    hdr(L["地图"])
    local syncShowLineRow
    do
        local tg = mkToggleRow(content, y, L["显示图钉"],
            function() return cfg().showPins == true end,
            function(v)
                cfg().showPins = v
                recalcAll()
                if syncShowLineRow then syncShowLineRow() end
            end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["图钉编号"],
            function() return cfg().showNum ~= false end,
            function(v) cfg().showNum = v recalcAll() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local row = mkStepperRow(content, y, L["图钉大小"], 14, 32, 2,
            function() return cfg().pinSize or 14 end,
            function(v) cfg().pinSize = v end,
            function(v) return tostring(v) end)
        syncers[#syncers + 1] = function() row:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["显示连线"],
            function() return cfg().showLines == true end,
            function(v) cfg().showLines = v recalcAll() end,
            function() return cfg().showPins == true end)
        syncShowLineRow = function() tg:sync() end
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["到目标连线"],
            function() return cfg().showMeLine ~= false end,
            function(v) cfg().showMeLine = v recalcAll() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local cy = mkCyclerRow(content, y, L["连线粗细"], {
            { v = 1.5, t = L["细"] }, { v = 2, t = L["中"] }, { v = 3, t = L["粗"] },
        }, function() return cfg().lineW or 2 end,
            function(v) cfg().lineW = v recalcAll() end)
        syncers[#syncers + 1] = function() cy:sync() end
        y = y - 24
    end

    hdr(L["找书HUD"])
    do
        local dd = mkDropdownRow(content, y, L["书籍显示"], {
            { v = "manual", t = L["手动选书"] },
            { v = "auto", t = L["自动跟随"] },
        }, function() return cfg().bookMode or "manual" end,
            function(v) cfg().bookMode = v end,
            function()
                recalcAll()
                if f.syncCoord then f.syncCoord() end
            end)
        syncers[#syncers + 1] = function() dd:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["显示罗盘"],
            function() return cfg().showCompass ~= false end,
            function(v) cfg().showCompass = v relayoutTracker(tracker) end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local tg = mkToggleRow(content, y, L["锁定位置"],
            function() return cfg().lockPos == true end,
            function(v) cfg().lockPos = v applySettings() end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    do
        local row = mkStepperRow(content, y, L["界面缩放"], 75, 150, 5,
            function() return math.floor((cfg().hudScale or 1) * 100 + 0.5) end,
            function(v) cfg().hudScale = v / 100 applySettings() end,
            function(v) return v .. "%" end)
        syncers[#syncers + 1] = function() row:sync() end
        y = y - 24
    end

    hdr(L["进度数据"])
    do
        local lab = setFs(content, 14, C_TXT)
        lab:SetJustifyH("LEFT")
        lab:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 7)
        lab:SetText(L["下一站坐标"])
        local eb = CreateFrame("EditBox", nil, content)
        eb:SetSize(118, 20)
        eb:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 10)
        eb:SetAutoFocus(false)
        eb:EnableMouse(true)
        eb:SetTextInsets(8, 8, 0, 0)
        if ns.hui and ns.hui.BuildRoundedBG and ns.hui.BuildRoundBorder then
            ns.hui.BuildRoundedBG(eb, 8, { 1, 1, 1, 0.05 }, "both", false, nil, true)
            ns.hui.BuildRoundBorder(eb, 8, { 0.40, 0.43, 0.50 })
        end
        if eb.SetFont then pcall(eb.SetFont, eb, ns.FONT, 13, "OUTLINE") end
        eb:SetTextColor(0.90, 0.90, 0.90)
        eb:SetJustifyH("LEFT")
        eb:SetScript("OnEscapePressed", function(s) s:ClearFocus() end)
        eb:SetScript("OnEnterPressed", function(s) s:ClearFocus() end)
        eb:SetScript("OnEditFocusGained", function(s)
            s:HighlightText()
            s:SetCursorPosition(#s:GetText())
        end)
        eb:SetScript("OnEditFocusLost", function(s) s:SetCursorPosition(0) end)
        f.syncCoord = function()
            if eb.HasFocus and eb:HasFocus() then return end
            local s2
            if (cfg().bookMode or "manual") == "auto" then
                s2 = route[1]
            elseif manualTrack then
                s2 = stepOfRec(manualTrack)
            end
            if s2 then
                eb:SetText(format("%.1f, %.1f  %s",
                    s2.x * 100, s2.y * 100, tostring(EG.ZoneName(s2.area, s2.area))))
            else
                eb:SetText(L["暂无目标"])
            end
            eb:SetCursorPosition(0)
        end
        f.syncCoord()
        y = y - 30
    end

    content:SetHeight(math.max(-y + 8, 40))
    f.syncAll = function()
        for _, fn in ipairs(syncers) do fn() end
        if f.syncCoord then f.syncCoord() end
    end
    f:SetScript("OnShow", function()
        if f.syncAll then f:syncAll() end
    end)
    f:SetScript("OnHide", function() if GameTooltip then GameTooltip:Hide() end end)
    return f
end

function ns.ExploreMapConfigPopup()
    return (settingsFrame and settingsFrame.IsShown and settingsFrame:IsShown()) and settingsFrame or nil
end

local function qbReanchor()
    if ns.QuickBar and ns.QuickBar.Reanchor then pcall(ns.QuickBar.Reanchor, ns.QuickBar) end
end

function ns.CloseExploreMapSettings()
    if settingsFrame and settingsFrame.IsShown and settingsFrame:IsShown() then
        settingsFrame:Hide()
        qbReanchor()
    end
end

function ns.ExploreMapSettingsToggle()
    if settingsFrame and settingsFrame.IsShown and settingsFrame:IsShown() then
        settingsFrame:Hide()
        qbReanchor()
        return
    end
    if not settingsFrame then
        settingsFrame = createSettings()
        if ns.QuickBar and ns.QuickBar.HookSettings then
            pcall(ns.QuickBar.HookSettings, ns.QuickBar)
        end
    end
    if ns.CloseSettings then pcall(ns.CloseSettings) end
    if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then
        pcall(ns.LootFilterUI.CloseConfig, ns.LootFilterUI)
    end
    if settingsFrame.syncAll then settingsFrame:syncAll() end
    settingsFrame:Show()
    qbReanchor()
end

local function createTracker()
    local f = CreateFrame("Frame", "DFExploreRouteTracker", UIParent, "BackdropTemplate")
    f:SetSize(320, 64)
    f:SetBackdrop({
        bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
        insets = { left = 2, right = 2, top = 2, bottom = 2 },
    })
    if ns.hui and ns.hui.SkinPopup and ns.huiTheme == "hui" then
        ns.hui.SkinPopup(f, 8, "both", nil, nil, nil, nil, nil, nil, true)
    else
        f:SetBackdropColor(0, 0, 0, 0.78)
        f:SetBackdropBorderColor(0.94, 0.71, 0.24, 0.35)
        if ns.hui and ns.hui.RoundCorner then pcall(ns.hui.RoundCorner, f, 8) end
    end
    f:SetMovable(cfg().lockPos ~= true)
    f:EnableMouse(true)
    f:RegisterForDrag("LeftButton")
    f:SetClampedToScreen(true)
    f:SetScale(cfg().hudScale or 1)
    f:SetScript("OnDragStart", f.StartMoving)
    f:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        pcall(saveTrackerPos, self)
    end)
    local pos = ns.DB and ns.DB() and ns.DB().explore and ns.DB().explore.routePos
    if pos then
        f:SetPoint(pos[1], UIParent, pos[2], pos[3], pos[4])
    else
        f:SetPoint("TOP", UIParent, "TOP", 0, -140)
    end

    f.dial = f:CreateTexture(nil, "ARTWORK")
    f.dial:SetSize(40, 40)
    f.dial:SetPoint("TOPLEFT", 12, -8)
    f.dial:SetTexture(DIAL_TEX)
    f.needle = f:CreateTexture(nil, "OVERLAY")
    f.needle:SetAllPoints(f.dial)
    f.needle:SetTexture(DART_TEX)

    f.name = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    f.name:SetPoint("TOPLEFT", f.dial, "TOPRIGHT", 8, 0)
    f.name:SetPoint("RIGHT", f, "RIGHT", -46, 0)
    f.name:SetJustifyH("LEFT")
    f.name:SetWordWrap(false)

    f.prog = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    f.prog:SetPoint("TOPRIGHT", f, "TOPRIGHT", -10, -11)
    f.prog:SetJustifyH("RIGHT")
    f.prog:SetTextColor(0.94, 0.71, 0.24, 1)

    f.where = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    f.where:SetPoint("TOPLEFT", f.dial, "TOPRIGHT", 8, -16)
    f.where:SetPoint("RIGHT", f, "RIGHT", -10, 0)
    f.where:SetJustifyH("LEFT")
    f.where:SetWordWrap(false)

    f.dist = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    f.dist:SetPoint("TOPLEFT", f.dial, "BOTTOMLEFT", 2, 3)
    f.dist:SetJustifyH("LEFT")

    f.barBG = f:CreateTexture(nil, "BORDER")
    f.barBG:SetPoint("BOTTOMLEFT", 72, 6)
    f.barBG:SetPoint("RIGHT", f, "RIGHT", -10, 0)
    f.barBG:SetHeight(7)
    f.barBG:SetColorTexture(0.086, 0.086, 0.086, 1)
    if ns.hui and ns.hui.AddRepaint and ns.huiTheme == "hui" then
        ns.hui.AddRepaint(f, function()
            local L0 = ns.hui.layer and ns.hui.layer.L0
            if L0 then f.barBG:SetColorTexture(L0[1], L0[2], L0[3], 1) end
        end)
    end
    f.fill = f:CreateTexture(nil, "OVERLAY")
    f.fill:SetPoint("LEFT", f.barBG, "LEFT", 0, 0)
    f.fill:SetHeight(7)
    f.fill:SetWidth(0.001)
    f.fill:SetColorTexture(0.94, 0.71, 0.24, 1)

    local hover = CreateFrame("Frame", nil, f, "BackdropTemplate")
    hover:SetSize(52, 82)
    hover:SetPoint("LEFT", f, "RIGHT", 2, 0)
    hover:SetFrameLevel(f:GetFrameLevel() + 8)
    hover:SetBackdrop({
        bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
        insets = { left = 2, right = 2, top = 2, bottom = 2 },
    })
    if ns.hui and ns.hui.SkinPopup and ns.huiTheme == "hui" then
        ns.hui.SkinPopup(hover, 8, "both", nil, nil, nil, nil, nil, nil, true)
    else
        hover:SetBackdropColor(0, 0, 0, 0.78)
        hover:SetBackdropBorderColor(0.94, 0.71, 0.24, 0.25)
        if ns.hui and ns.hui.RoundCorner then pcall(ns.hui.RoundCorner, hover, 8) end
    end
    hover:Hide()
    local skip = mkBtn(hover, L["跳过"], 44)
    skip:SetPoint("TOP", 0, -6)
    skip:SetScript("OnClick", function()
        if route[1] then skipped[route[1].rec[1]] = true end
        BuildRoute()
        updateTracker()
        ns.ExploreMapRefresh()
    end)
    local recalc = mkBtn(hover, L["重算"], 44)
    recalc:SetPoint("TOP", skip, "BOTTOM", 0, -6)
    recalc:SetScript("OnClick", function()
        for k in pairs(skipped) do skipped[k] = nil end
        BuildRoute()
        updateTracker()
        ns.ExploreMapRefresh()
    end)
    local close = mkBtn(hover, L["关闭"], 44)
    close:SetPoint("TOP", recalc, "BOTTOM", 0, -6)
    close:SetScript("OnClick", function()
        manualOff = true
        ns.ExploreMapToggle(false)
    end)
    local hideToken = 0
    local function cancelHide() hideToken = hideToken + 1 end
    local function scheduleHide()
        hideToken = hideToken + 1
        local my = hideToken
        if not (C_Timer and C_Timer.After) then
            if type(MouseIsOver) ~= "function" or not (MouseIsOver(f) or MouseIsOver(hover)) then
                hover:Hide()
            end
            return
        end
        C_Timer.After(2.5, function()
            if hideToken ~= my then return end
            if type(MouseIsOver) == "function" and (MouseIsOver(f) or MouseIsOver(hover)) then return end
            hover:Hide()
        end)
    end
    f:SetScript("OnEnter", function() cancelHide() hover:Show() end)
    hover:SetScript("OnEnter", function() cancelHide() hover:Show() end)
    f:SetScript("OnLeave", scheduleHide)
    hover:SetScript("OnLeave", scheduleHide)

    local elapsed = 0
    f:SetScript("OnUpdate", function(_, e)
        elapsed = elapsed + e
        if elapsed < UPDATE_TICK then return end
        elapsed = 0
        updateTracker()
    end)
    relayoutTracker(f)
    return f
end

function ns.ExploreMapOn()
    return routeOn
end

function ns.ExploreGraveOn()
    return cfg().showGrave == true
end

function ns.ExploreGraveSet(v)
    cfg().showGrave = v and true or false
    ns.ExploreMapRefresh()
    return cfg().showGrave
end

function ns.ExploreGraveToggle()
    return ns.ExploreGraveSet(not cfg().showGrave)
end

function ns.ExploreGraveStyle()
    local v = cfg().graveStyle
    if v ~= "circle" and v ~= "custom" then v = "native" end
    return v
end

function ns.ExploreGraveStyleSet(v)
    if v ~= "circle" and v ~= "custom" then v = "native" end
    cfg().graveStyle = v
    ns.ExploreMapRefresh()
    return v
end

function ns.ExploreMapTrackBook(rec)
    if (cfg().bookMode or "manual") ~= "manual" then return end
    manualTrack = rec
    if updateTrackerFn then updateTrackerFn() end
end

function ns.ExploreMapToggle(force)
    if force == nil then force = not routeOn end
    routeOn = force and true or false
    if routeOn then
        manualOff = false
        BuildRoute()
        tracker = tracker or createTracker()
        tracker:Show()
        updateTracker()
    else
        for k in pairs(skipped) do skipped[k] = nil end
        if tracker then tracker:Hide() end
    end
    if EG.built then pcall(EG.Render) end
end

local function Init()
    if not WorldMapFrame then return end
    if hooksecurefunc then
        pcall(hooksecurefunc, WorldMapFrame, "OnMapChanged", function()
            ns.ExploreMapRefresh()
        end)
        if WorldMapFrame.OnCanvasScaleChanged then
            pcall(hooksecurefunc, WorldMapFrame, "OnCanvasScaleChanged", function()
                ns.ExploreMapRefresh()
            end)
        end
    end
    local tickAcc = 0
    local ticker = CreateFrame("Frame")
    ticker:SetScript("OnUpdate", function(_, e)
        tickAcc = tickAcc + e
        if tickAcc < 0.2 then return end
        tickAcc = 0
        meLineMove()
    end)
    if WorldMapFrame.HookScript then
        pcall(WorldMapFrame.HookScript, WorldMapFrame, "OnShow", function()
            ns.ExploreMapRefresh()
            if cfg().autoRoute and not routeOn and not manualOff then
                ns.ExploreMapToggle(true)
            end
        end)
    end
end

local boot = CreateFrame("Frame")
pcall(boot.RegisterEvent, boot, "PLAYER_LOGIN")
boot:SetScript("OnEvent", function()
    C_Timer.After(0, function()
        Init()
        if routeOn then
            BuildRoute()
            tracker = tracker or createTracker()
            tracker:Show()
            updateTracker()
        end
    end)
end)
