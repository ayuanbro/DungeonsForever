local _, ns = ...
if type(ns) ~= "table" then return end
local Host = ns.ProfHost
if type(Host) ~= "table" then return end
local M = ns.MapModule
if type(M) ~= "table" then return end

local L = ns.L
local DG = Host.DG
local Unpack = Host.Unpack
local C_GREY = Host.C_GREY
local C_GOLD = Host.C_GOLD
local C_TEXT = Host.C_TEXT

local W = {}
ns.MapWorldModule = W

local pendingMap
-- 前向声明：W.Hide 在文件后段的 dropdownInit 之前就要用到它，
-- 原先 local 声明在使用点之后 200 多行，W.Hide 读到的是全局 nil。
local dropDown

local function inCombat()
    return type(InCombatLockdown) == "function" and InCombatLockdown() and true or false
end

local function euiMapSkin()
    local E = _G.EllesmereUI
    if not E then return false end
    if E.GetBlizzWindowStyle then
        local ok, s = pcall(E.GetBlizzWindowStyle, "worldmap")
        if ok and s and s ~= false then return true end
    end
    local db = _G.EllesmereUIDB
    return (db and db.reskinWorldMap) and true or false
end
W.EUIMapSkin = euiMapSkin

local function applyMap(id)
    if not id or not WorldMapFrame then return end
    if C_Map and C_Map.OpenWorldMap and WorldMapFrame:IsShown() then
        pcall(C_Map.OpenWorldMap, id)
        return
    end
    if WorldMapFrame.SetMapID then
        pcall(WorldMapFrame.SetMapID, WorldMapFrame, id)
    end
end

local function setMap(id)
    if not id then return end
    if inCombat() then
        pendingMap = id
        return
    end
    pendingMap = nil
    applyMap(id)
end


local regen = CreateFrame("Frame")
regen:RegisterEvent("PLAYER_REGEN_ENABLED")
regen:SetScript("OnEvent", function()
    local id = pendingMap
    pendingMap = nil
    if not (id and WorldMapFrame and WorldMapFrame:IsShown()) then return end
    applyMap(id)
    if W.pinProvider and W.pinProvider.RefreshAllData then pcall(W.pinProvider.RefreshAllData, W.pinProvider) end
end)

local function fontPath()
    return ns.FONT or STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF"
end

local function fontFlags()
    if ns.hui and ns.hui.FontFlags then
        local ok, f = pcall(ns.hui.FontFlags, "OUTLINE")
        if ok and type(f) == "string" then return f end
    end
    return "OUTLINE"
end

local FLAGS = fontFlags()
local PIN_FLAGS = "THICKOUTLINE"

local function makeFS(parent, size, color, justify)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    fs:SetFont(fontPath(), size, FLAGS)
    if color then fs:SetTextColor(Unpack(color)) end
    if justify then fs:SetJustifyH(justify) end
    return fs
end

local function makeBtn(parent, text, w, h, size)
    local bt
    if type(ns.CreateButton) == "function" then
        local ok, v = pcall(ns.CreateButton, parent)
        if ok then bt = v end
    end
    if not bt then bt = CreateFrame("Button", nil, parent) end
    bt:SetSize(w, h)
    if text then bt:SetText(text) end
    local fs = bt:GetFontString()
    if fs then fs:SetFont(fontPath(), size or 12, FLAGS) end
    return bt
end

local function navBar()
    if not WorldMapFrame then return nil end
    return WorldMapFrame.NavBar or WorldMapFrame
end

local function makeNativeBtn(parent, text, w, h)
    local bt = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    bt:SetSize(w, h)
    if text then bt:SetText(text) end
    return bt
end

local function ndBtn(bt)
    if not bt or not ns.NDuiOn or not ns.NDuiOn() then return bt end
    ns.NDuiReskin(bt)
    local fs = bt.GetFontString and bt:GetFontString()
    if fs then
        local ok, fn, size = pcall(fs.GetFont, fs)
        if ok and fn and size then pcall(fs.SetFont, fs, fn, size, "") end
    end
    return bt
end

local function leaSkin(bt, flat)
    if not bt or bt.__leaSkin then return bt end
    bt.__leaSkin = true
    pcall(bt.SetNormalTexture, bt, "")
    pcall(bt.SetPushedTexture, bt, "")
    pcall(bt.SetDisabledTexture, bt, "")
    pcall(bt.SetHighlightTexture, bt, nil)
    if flat then
        local okr, regs = pcall(function() return { bt:GetRegions() } end)
        if okr and type(regs) == "table" then
            for _, reg in ipairs(regs) do
                if reg.GetObjectType and reg:GetObjectType() == "Texture" then
                    reg:Hide()
                end
            end
        end
    end
    local fs = bt.GetFontString and bt:GetFontString()
    if fs then fs:SetTextColor(1, 0.82, 0) end
    if flat then return bt end
    local bg = bt:CreateTexture(nil, "BACKGROUND")
    bg:SetColorTexture(0.05, 0.05, 0.05, 0.92)
    bg:SetAllPoints()
    local function edge(p1, r1, p2, r2, horiz)
        local e = bt:CreateTexture(nil, "BORDER")
        e:SetColorTexture(0.3, 0.3, 0.3, 0.9)
        e:SetPoint(p1, bt, r1, 0, 0)
        e:SetPoint(p2, bt, r2, 0, 0)
        if horiz then
            e:SetHeight(1)
        else
            e:SetWidth(1)
        end
    end
    edge("TOPLEFT", "TOPLEFT", "TOPRIGHT", "TOPRIGHT", true)
    edge("BOTTOMLEFT", "BOTTOMLEFT", "BOTTOMRIGHT", "BOTTOMRIGHT", true)
    edge("TOPLEFT", "TOPLEFT", "BOTTOMLEFT", "BOTTOMLEFT", false)
    edge("TOPRIGHT", "TOPRIGHT", "BOTTOMRIGHT", "BOTTOMRIGHT", false)
    return bt
end

local LEA_ROW = 11
local LEA_TASK_X = 29
local LEA_ROUTE_L = 261

local function leaTitleFS(want)
    if not want or want == "" then return nil end
    if W.leaTitleKey == want then return W.leaTitleFS end
    local wmf = WorldMapFrame
    local found
    if wmf and wmf.GetChildren then
        local ok, kids = pcall(function() return { wmf:GetChildren() } end)
        if ok and type(kids) == "table" then
            for _, f in ipairs(kids) do
                if found then break end
                if type(f) == "table" and f.GetChildren then
                    local ok2, subs = pcall(function() return { f:GetChildren() } end)
                    if ok2 and type(subs) == "table" then
                        for _, sf in ipairs(subs) do
                            if found then break end
                            if type(sf) == "table" and sf.GetRegions then
                                local ok3, regs = pcall(function() return { sf:GetRegions() } end)
                                if ok3 and type(regs) == "table" then
                                    for _, reg in ipairs(regs) do
                                        if reg.GetObjectType and reg:GetObjectType() == "FontString" then
                                            local ok4, txt = pcall(reg.GetText, reg)
                                            if ok4 and txt and txt ~= "" and string.find(txt, want, 1, true) then
                                                found = reg
                                                break
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    W.leaTitleKey = want
    W.leaTitleFS = found
    return found
end

local function closeBtnAtlas()
    local cb = _G.WorldMapFrameCloseButton
    if not cb then return nil end
    local nt = cb.GetNormalTexture and cb:GetNormalTexture()
    if not nt then return nil end
    local ok, v = pcall(nt.GetAtlas, nt)
    if ok and v then return v end
    return nil
end

local function skinCloseStyle(bt)
    local atlas = closeBtnAtlas()
    if not atlas then return false end
    local K, E = 0.15, 4
    local function pc(l, r, t, b, layer)
        local x = bt:CreateTexture(nil, layer or "ARTWORK")
        x:SetAtlas(atlas)
        x:SetTexCoord(l, r, t, b)
        return x
    end
    local mid = pc(0.16, 0.22, 0.16, 0.84, "BACKGROUND")
    mid:SetPoint("TOPLEFT", bt, "TOPLEFT", E - 1, -(E - 1))
    mid:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -(E - 1), E - 1)
    local tl = pc(0, K, 0, K)
    tl:SetSize(E, E)
    tl:SetPoint("TOPLEFT", bt, "TOPLEFT", 0, 0)
    local tr = pc(1 - K, 1, 0, K)
    tr:SetSize(E, E)
    tr:SetPoint("TOPRIGHT", bt, "TOPRIGHT", 0, 0)
    local bl = pc(0, K, 1 - K, 1)
    bl:SetSize(E, E)
    bl:SetPoint("BOTTOMLEFT", bt, "BOTTOMLEFT", 0, 0)
    local br = pc(1 - K, 1, 1 - K, 1)
    br:SetSize(E, E)
    br:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", 0, 0)
    local et = pc(K, 1 - K, 0, K)
    et:SetHeight(E)
    et:SetPoint("TOPLEFT", bt, "TOPLEFT", E, 0)
    et:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -E, 0)
    local eb = pc(K, 1 - K, 1 - K, 1)
    eb:SetHeight(E)
    eb:SetPoint("BOTTOMLEFT", bt, "BOTTOMLEFT", E, 0)
    eb:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -E, 0)
    local el = pc(0, K, K, 1 - K)
    el:SetWidth(E)
    el:SetPoint("TOPLEFT", bt, "TOPLEFT", 0, -E)
    el:SetPoint("BOTTOMLEFT", bt, "BOTTOMLEFT", 0, E)
    local er = pc(1 - K, 1, K, 1 - K)
    er:SetWidth(E)
    er:SetPoint("TOPRIGHT", bt, "TOPRIGHT", 0, -E)
    er:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", 0, E)
    local hl = bt:CreateTexture(nil, "HIGHLIGHT")
    hl:SetAtlas("RedButton-Highlight")
    hl:SetBlendMode("ADD")
    hl:SetAllPoints(bt)
    return true
end

local function setPicked(bt, on)
    if not bt then return end
    local fs = bt:GetFontString()
    if not fs then return end
    if on then
        fs:SetTextColor(0.62, 0.62, 0.62)
    else
        fs:SetTextColor(1, 0.82, 0)
    end
end

local BTN_H, BTN_W, BTN_GAP = 22, 80, 6
local NAV_PAD_R, NAV_PAD_T = 7, 6
local PAD_X, PAD_Y = 20, 12
local FLOOR_H, FLOOR_GAP = 24, 4
local FLOOR_MIN_W, FLOOR_MAX_W = 84, 120
local MAX_PINS = M.MAX_PINS
local MAX_ROUTE = M.MAX_ROUTE_DOTS
local VIEW_LEVEL = 900
local syncNav

local function enabled()
    if ns.MapEntryOn and not ns.MapEntryOn() then return false end
    local d = DungeonsForeverDB
    local s = type(d) == "table" and d.dungeon or nil
    if type(s) ~= "table" then return true end
    return s.mapOnWorld ~= false
end

W.On = enabled

local function area()
    if not WorldMapFrame then return nil end
    return WorldMapFrame.ScrollContainer or WorldMapFrame
end

local function questPanel()
    if not WorldMapFrame then return nil end
    return WorldMapFrame.QuestLog or WorldMapFrame.QuestMapFrame
end

local function setLogPanel(shown)
    local q = questPanel()
    if not q or shown == q:IsShown() then return end
    local wmf = WorldMapFrame
    local done
    if wmf and type(wmf.SetQuestLogPanelShown) == "function" then
        local ok = pcall(wmf.SetQuestLogPanelShown, wmf, shown)
        done = ok and shown == q:IsShown()
    end
    if not done then
        if shown then q:Show() else q:Hide() end
    end
end

local leaOverlay

local function leaFind()
    if leaOverlay then return leaOverlay end
    local sc = area()
    if not (sc and sc.GetChildren) then return nil end
    for _, ch in ipairs({ sc:GetChildren() }) do
        if type(ch) == "table" and ch.bg and ch.levelMenu
            and type(ch.canvas) == "table" and ch.canvas.art then
            leaOverlay = ch
            if type(hooksecurefunc) == "function" then
                hooksecurefunc(ch, "Show", function()
                    if W.Active() then ch:Hide() end
                end)
            end
            return leaOverlay
        end
    end
    return nil
end

local function leaSuppress()
    if not W.Active() then return end
    local ov = leaFind()
    if ov and ov:IsShown() then ov:Hide() end
end

local function leaIconRows()
    local wmf = WorldMapFrame
    if not (wmf and wmf.GetCanvas) then return nil end
    local ok, canvas = pcall(wmf.GetCanvas, wmf)
    if not (ok and canvas and canvas.GetChildren) then return nil end
    local out
    for _, ch in ipairs({ canvas:GetChildren() }) do
        local d = type(ch) == "table" and ch.data
        if type(ch) == "table" and ch.isLeaMapsPin and type(d) == "table"
            and not ch.__dfSup and (not ch.IsShown or ch:IsShown()) then
            local k = d[1]
            if k == "Dungeon" or k == "Raid" or k == "Dunraid" then
                local x, y = tonumber(d[2]), tonumber(d[3])
                if x and y then
                    out = out or {}
                    out[#out + 1] = { x = x, y = y }
                end
            end
        end
    end
    return out
end

local function dropLeaDupes(rows)
    local icons = leaIconRows()
    if not (icons and type(rows) == "table" and #rows > 0) then return rows end
    local out
    for i = 1, #rows do
        local r = rows[i]
        local hit
        for j = 1, #icons do
            local dx, dy = icons[j].x - r.x, icons[j].y - r.y
            if dx * dx + dy * dy <= 64 then hit = true break end
        end
        if not hit then
            out = out or {}
            out[#out + 1] = r
        end
    end
    return out or rows
end

local leaLastSig

local function leaIconSig()
    local icons = leaIconRows()
    if not (icons and #icons > 0) then return "" end
    local t = {}
    for i = 1, #icons do
        t[#t + 1] = string.format("%d:%d", icons[i].x * 10, icons[i].y * 10)
    end
    table.sort(t)
    return table.concat(t, ";")
end

local function areaOffset()
    local sc, wmf = area(), WorldMapFrame
    if not (sc and wmf) or sc == wmf then return 0, 0 end
    local ox = (sc:GetLeft() or 0) - (wmf:GetLeft() or 0)
    local oy = (wmf:GetTop() or 0) - (sc:GetTop() or 0)
    if type(ox) ~= "number" or type(oy) ~= "number" then return 0, 0 end
    return ox, oy
end


local function mapAreaSize()
    local a = area()
    if not a then return 0, 0 end
    local aw, ah = a:GetWidth(), a:GetHeight()
    if type(aw) ~= "number" or type(ah) ~= "number" then return 0, 0 end
    return aw, ah
end

local function mapTable()
    local IM = ns.InstanceMap
    if type(IM) ~= "table" then return nil end
    return IM
end

local function nameKey(s)
    if type(s) ~= "string" then return nil end
    local t = s:gsub("[%s%p]", "")
    return t:lower()
end

local NAME_MAP

local function nameIndex()
    if NAME_MAP then return NAME_MAP end
    local out = {}
    local IM = mapTable()
    local extra = IM and IM.name
    if type(extra) == "table" then
        for k, id in pairs(extra) do
            local kk = nameKey(k)
            if kk and type(id) == "string" and out[kk] == nil then out[kk] = id end
        end
    end
    local list = ns.DungeonData and ns.DungeonData.dungeons
    if type(list) == "table" then
        for i = 1, #list do
            local d = list[i]
            local k1 = nameKey(d.name)
            local k2 = nameKey(d.nameEn)
            if k1 and out[k1] == nil then out[k1] = d.id end
            if k2 and out[k2] == nil then out[k2] = d.id end
        end
    end
    NAME_MAP = out
    return out
end

local function purgeLearn()
    local db = DungeonsForeverDB
    local s = type(db) == "table" and db.dungeon
    if type(s) == "table" and s.instLearn ~= nil then s.instLearn = nil end
end

local function worldMapID()
    if not (WorldMapFrame and WorldMapFrame.GetMapID) then return nil end
    local ok, v = pcall(WorldMapFrame.GetMapID, WorldMapFrame)
    if not ok then return nil end
    return tonumber(v)
end

local function instanceInfo()
    if type(GetInstanceInfo) ~= "function" then return nil end
    local ok, nm, itype, dIdx, dName, maxP, pvp, inInst, instID = pcall(GetInstanceInfo)
    if not ok then return nil end
    return {
        name = nm, kind = itype, diffIdx = dIdx, diffName = dName,
        maxPlayers = maxP, pvp = pvp, inInstance = inInst,
        instID = tonumber(instID),
    }
end

local function zoneText()
    if type(GetRealZoneText) == "function" then
        local ok, v = pcall(GetRealZoneText)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    if type(GetZoneText) == "function" then
        local ok, v = pcall(GetZoneText)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return nil
end

local function hasArt(id)
    if not id then return false end
    if M.LayersFor(id) then return true end
    if M.CustomFor(id) then return true end
    return false
end

local function subZoneText()
    if type(GetSubZoneText) == "function" then
        local ok, v = pcall(GetSubZoneText)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    if type(GetMinimapZoneText) == "function" then
        local ok, v = pcall(GetMinimapZoneText)
        if ok and type(v) == "string" and v ~= "" then
            local zn = zoneText()
            if not zn or nameKey(v) ~= nameKey(zn) then return v end
        end
    end
    return nil
end

local function zoneAreaId()
    local tbl = M.ZONE_AREA
    if type(tbl) ~= "table" then return nil end
    local st = subZoneText()
    if not st or st == "" then return nil end
    for i = 1, #tbl do
        local r = tbl[i]
        if r and hasArt(r.id) then
            if type(r.sub) == "table" then
                for k = 1, #r.sub do
                    if r.sub[k] == st then return r.id end
                end
            end
            if type(r.mark) == "table" then
                for k = 1, #r.mark do
                    if st:find(r.mark[k], 1, true) then return r.id end
                end
            end
        end
    end
    return nil
end

local function detailOf(id)
    local list = ns.DungeonData and ns.DungeonData.dungeons
    if type(list) ~= "table" then return nil end
    for i = 1, #list do
        if list[i].id == id then return list[i] end
    end
    return nil
end

local function inInstance()
    if type(IsInInstance) == "function" then
        local ok, a, b = pcall(IsInInstance)
        if ok and b then return a and true or false end
    end
    local info = instanceInfo()
    if info and info.instID and info.instID > 0 then return true end
    return false
end

local function sameArt(a, b)
    local A = M.ART
    if not (a and b and A and A[a] and A[b]) then return false end
    return A[a][1] == A[b][1]
end

local function instStamp()
    if not inInstance() then return nil end
    local info = instanceInfo()
    if not info then return nil end
    if not (info.instID or info.name) then return nil end
    return tostring(info.instID or "") .. "|" .. tostring(info.name or "")
end

function W.Resolve()
    if not enabled() then return nil end
    local IM = mapTable()
    local cur = hasArt(M.curId) and M.curId or nil
    if not inInstance() then
        local aid = zoneAreaId()
        if aid then
            if cur and sameArt(cur, aid) then return cur, "cur" end
            return aid, "area"
        end
        local zn = zoneText()
        local oid = zn and nameIndex()[nameKey(zn)]
        if not hasArt(oid) and zn and M.NamePrefixFor then oid = M.NamePrefixFor(zn) end
        if hasArt(oid) and M.OUTSIDE_LAYER and M.OUTSIDE_LAYER[oid] then
            if cur and sameArt(cur, oid) then return cur, "cur" end
            return oid, "zone"
        end
        return nil
    end
    local info = instanceInfo()
    local instID = info and info.instID
    local szn = subZoneText()
    local sk = szn and nameKey(szn) or nil
    if sk and instID and type(M.INSTANCE_SUBZONE) == "table" then
        local row = M.INSTANCE_SUBZONE[instID]
        local sid = type(row) == "table" and row[sk] or nil
        if sid and hasArt(sid) then
            if cur == sid then return cur, "cur" end
            return sid, "sub"
        end
    end
    if instID and IM and type(IM.inst) == "table" then
        local id = IM.inst[instID]
        if hasArt(id) then
            if cur and sameArt(cur, id) then return cur, "cur" end
            return id, "inst"
        end
    end
    local names = { info and info.name, zoneText() }
    for i = 1, #names do
        local nm = names[i]
        if nm and nm ~= "" then
            local id = nameIndex()[nameKey(nm)]
            if not hasArt(id) and M.NamePrefixFor then id = M.NamePrefixFor(nm) end
            if hasArt(id) then
                if cur and sameArt(cur, id) then return cur, "cur" end
                return id, "name"
            end
        end
    end
    local mapID = worldMapID()
    if mapID and IM and type(IM.map) == "table" then
        local id = IM.map[mapID]
        if hasArt(id) then
            if cur and sameArt(cur, id) then return cur, "cur" end
            return id, "map"
        end
    end
    if cur and W.curStamp and W.curStamp == instStamp() then return cur, "cur" end
    return nil
end

local function subZoneKey()
    local s = subZoneText()
    if type(s) ~= "string" or s == "" then return nil end
    return nameKey(s)
end

function W.SubzoneLayerFor(id)
    local tbl = M.SUBZONE_LAYER
    if not (id and type(tbl) == "table" and type(tbl[id]) == "table") then return nil end
    local sk = subZoneKey()
    if not sk then return nil end
    local idx = tbl[id][sk]
    if type(idx) ~= "number" then return nil end
    return idx
end

function W.ResolveCandidates()
    if not enabled() then return nil end
    local zn
    if inInstance() then
        local info = instanceInfo()
        zn = info and info.name
    end
    zn = zn or zoneText()
    if not zn or zn == "" then return nil end
    local zk = nameKey(zn)
    if not zk or zk == "" then return nil end
    local list = ns.DungeonData and ns.DungeonData.dungeons
    if type(list) ~= "table" then return nil end
    local out = {}
    for i = 1, #list do
        local d = list[i]
        if hasArt(d.id) then
            local k1, k2 = nameKey(d.name), nameKey(d.nameEn)
            if (k1 and #k1 >= #zk and k1:sub(1, #zk) == zk)
                or (k2 and #k2 >= #zk and k2:sub(1, #zk) == zk) then
                out[#out + 1] = { id = d.id, name = d.name }
            end
        end
    end
    if #out == 0 then return nil end
    local sk = subZoneKey()
    local sinfo = inInstance() and instanceInfo() or nil
    local srow = (sinfo and sinfo.instID and type(M.INSTANCE_SUBZONE) == "table") and M.INSTANCE_SUBZONE[sinfo.instID] or nil
    if sk and type(srow) == "table" then
        local pick = srow[sk]
        if pick then
            for i = 1, #out do
                if out[i].id == pick then return { out[i] } end
            end
        end
    end
    if #out == 1 then return out end
    if sk and #out > 1 then
        local pick = {}
        for i = 1, #out do
            local suf = out[i].name:match("[：:]%s*([^%s：:]+)%s*$")
                or out[i].nameEn:match(":%s*([^%s:]+)%s*$")
            local skk = suf and nameKey(suf)
            if skk and skk ~= "" and (sk == skk or sk:find(skk, 1, true) or skk:find(sk, 1, true)) then
                pick[#pick + 1] = out[i]
            end
        end
        if #pick == 1 then return pick end
    end
    return out
end

local function floorNumAt(id, idx)
    if not (id and idx) then return nil end
    if M.LayersFor(id) then return M.FloorNumAt(id, idx) end
    if M.CustomFor(id) then return 1 end
    return nil
end

local function floorText(id, idx)
    local layers = M.LayersFor(id)
    if not layers then
        return string.format(L["第 %d 层"], 1), 1
    end
    local fn = M.FloorNumAt(id, idx) or idx
    local txt = M.FloorName and M.FloorName(id, fn) or nil
    return (txt or string.format(L["第 %d 层"], fn)), fn
end

local function paintArt(view, id, idx, cw, ch)
    local lay = M.Layout(cw, ch)
    local path = M.PathAt(id, idx)
    local fixRow = id and M.TILE_FIX and M.TILE_FIX[id]
    local fixTile = fixRow and fixRow[M.ArtIdx(id, idx)]
    local cpath, cv1 = M.CustomFloorFor(id, idx)
    if not cpath then cpath, cv1 = M.CustomFor(id) end
    if not cv1 then cv1 = 1 end
    for i = 1, M.N do view.tiles[i]:Hide() end
    view.custom:Hide()
    if cpath then
        view.custom:SetTexture(cpath)
        view.custom:SetTexCoord(0, 1, 0, cv1)
        view.custom:ClearAllPoints()
        view.custom:SetPoint("TOPLEFT", view.canvas, "TOPLEFT", 0, 0)
        view.custom:SetSize(cw, ch)
        view.custom:Show()
    elseif path then
        for i = 1, #lay do
            local p = lay[i]
            local t = view.tiles[p.n]
            t:SetTexture((fixTile and fixTile[p.n]) or (path .. p.n))
            t:SetTexCoord(p.u0, p.u1, p.v0, p.v1)
            t:ClearAllPoints()
            t:SetPoint("TOPLEFT", view.canvas, "TOPLEFT", p.x, -p.y)
            t:SetSize(p.w, p.h)
            t:Show()
        end
    end
end

local function paintArea(view, id, fn, cw, ch)
    local host = view.canvas
    if not (host and ns.AreaDraw) then return end
    local items = fn and ns.AreaVec and ns.AreaVec.dun and ns.AreaVec.dun[id] and ns.AreaVec.dun[id][fn]
    if items then
        ns.AreaDraw.Paint(host, cw, ch, items, 1, 1, 1, { base = 3 })
    else
        ns.AreaDraw.Clear(host)
    end
end

local function smoothPts(src)
    local n = #src
    if n < 3 then return src end
    local out = { { src[1][1], src[1][2] } }
    for i = 1, n - 1 do
        local p, q = src[i], src[i + 1]
        out[#out + 1] = { 0.72 * p[1] + 0.28 * q[1], 0.72 * p[2] + 0.28 * q[2] }
        out[#out + 1] = { 0.28 * p[1] + 0.72 * q[1], 0.28 * p[2] + 0.72 * q[2] }
    end
    out[#out + 1] = { src[n][1], src[n][2] }
    return out
end

local function routeDot(view, x, y, cr, cg, cb, si)
    local i = (view.routeUsed or 0) + 1
    local e = view.routePool[i]
    if not e then
        e = {
            o = view.route:CreateTexture(nil, "ARTWORK"),
            c = view.route:CreateTexture(nil, "ARTWORK"),
        }
        e.o:SetTexture(M.ROUTE_DOT_TEX)
        e.o:SetDrawLayer("ARTWORK", 0)
        e.c:SetTexture(M.ROUTE_DOT_TEX)
        e.c:SetDrawLayer("ARTWORK", 1)
        e.o:Hide()
        e.c:Hide()
        view.routePool[i] = e
    end
    view.routeUsed = i
    local uk = view.__uiK or 1
    local edge = (M.routeThin and M.ROUTE_THIN_EDGE or M.ROUTE_DOT_EDGE) * uk
    local core = (M.routeThin and M.ROUTE_THIN_DOT or M.ROUTE_DOT) * uk
    e.si = si
    e.bedge, e.bcore = edge, core
    e.br, e.bg, e.bb = cr, cg, cb
    e.o:SetSize(edge, edge)
    e.o:ClearAllPoints()
    e.o:SetPoint("CENTER", view.route, "TOPLEFT", x, -y)
    e.o:SetVertexColor(0.05, 0.04, 0.03, 1)
    e.o:Show()
    e.c:SetSize(core, core)
    e.c:ClearAllPoints()
    e.c:SetPoint("CENTER", view.route, "TOPLEFT", x, -y)
    e.c:SetVertexColor(cr, cg, cb)
    e.c:SetAlpha(1)
    e.c:Show()
end

local function paintSegWorld(view, si, on)
    local used = view.routeUsed or 0
    for i = 1, used do
        local e = view.routePool[i]
        if e and e.si == si and e.bedge then
            if on then
                e.o:SetSize(e.bedge * 1.5, e.bedge * 1.5)
                e.c:SetSize(e.bcore * 1.6, e.bcore * 1.6)
                e.c:SetVertexColor(math.min(1, e.br * 1.28 + 0.16),
                                   math.min(1, e.bg * 1.28 + 0.16),
                                   math.min(1, e.bb * 1.28 + 0.16))
            else
                e.o:SetSize(e.bedge, e.bedge)
                e.c:SetSize(e.bcore, e.bcore)
                e.c:SetVertexColor(e.br, e.bg, e.bb)
            end
        end
    end
end

local function syncRoute(view, id, floor, cw, ch)
    local used = view.routeUsed or 0
    local n = 0
    local hv = M.NewSegHover(view.route, function(si, on) paintSegWorld(view, si, on) end)
    if hv.seg then hv:Set(nil) end
    view.routeUsed = 0
    if id and floor and M.RouteOn(id) and not M.routeOff then
        local segs = ns.DungeonRoute and ns.DungeonRoute[id] and ns.DungeonRoute[id][floor]
        if type(segs) == "table" and #segs > 0 then
            local arr, total, dsh = {}, 0, {}
            for si = 1, #segs do
                if M.routeHidden[M.RouteSegKey(id, floor, si)] then
                    arr[si] = nil
                else
                    local src = segs[si].pts
                    local dst = {}
                    for i = 1, #src do
                        dst[i] = { (src[i][1] / 100) * cw, (src[i][2] / 100) * ch }
                    end
                    dst = smoothPts(dst)
                    for i = 2, #dst do
                        total = total + math.sqrt((dst[i][1] - dst[i - 1][1]) ^ 2
                            + (dst[i][2] - dst[i - 1][2]) ^ 2)
                    end
                    arr[si] = dst
                    if segs[si].dash then dsh[si] = true end
                end
            end
            local step = M.ROUTE_STEP
            local cap = MAX_ROUTE * 0.95
            if total > 0 and total / step > cap then
                step = total / cap
            end
            local acc = 0
            local full = false
            for si = 1, #segs do
                if full then break end
                local pts = arr[si]
                if pts then
                    local dash = dsh[si]
                    local period = M.ROUTE_DASH_ON + M.ROUTE_DASH_OFF
                    local sd = 0
                    for i = 2, #pts do
                        if full then break end
                        local a, b = pts[i - 1], pts[i]
                        local dx, dy = b[1] - a[1], b[2] - a[2]
                        local d = math.sqrt(dx * dx + dy * dy)
                        if d > 0.01 then
                            local k = math.max(1, math.ceil(d / step))
                            local du = d / k
                            for j = 1, k do
                                if n >= MAX_ROUTE then
                                    full = true
                                    break
                                end
                                local u = (j - 0.5) / k
                                local ds = sd + du * (j - 0.5)
                                if (not dash) or (ds % (M.ROUTE_DASH_ON + M.ROUTE_DASH_OFF) < M.ROUTE_DASH_ON) then
                                    n = n + 1
                                    local t = (total > 0) and ((acc + d * u) / total) or 0
                                    local cr, cg, cb = M.RouteColor(t)
                                    routeDot(view, a[1] + dx * u, a[2] + dy * u, cr, cg, cb, si)
                                end
                            end
                            sd = sd + d
                        end
                        acc = acc + d
                    end
                end
            end
            hv:Build(view.route, arr, #segs)
        end
    end
    if n == 0 then hv:HideAll() end
    for i = n + 1, used do
        local e = view.routePool[i]
        if e then
            e.o:Hide()
            e.c:Hide()
        end
    end
    local rsegs = id and floor and ns.DungeonRoute and ns.DungeonRoute[id] and ns.DungeonRoute[id][floor]
    local nb = M.SyncNoBadges(view.route, "world", cw, ch, M.SegNoItems(id, floor, rsegs, cw, ch, function(i)
        return M.routeOff or M.routeHidden[M.RouteSegKey(id, floor, i)]
    end), view.__uiK)
    view.route:SetShown(n > 0 or (nb or 0) > 0)
end

local function pinList(id, floor)
    local list
    local bosses = M.PinsFor(id, floor)
    if bosses then
        list = {}
        for i = 1, #bosses do list[#list + 1] = bosses[i] end
    end
    local ex = M.ExtraPinsFor(id, floor)
    if ex then
        list = list or {}
        for i = 1, #ex do list[#list + 1] = ex[i] end
    end
    local nts = M.NotePinsFor(id, floor)
    if nts then
        list = list or {}
        for i = 1, #nts do list[#list + 1] = nts[i] end
    end
    if list and #list > 0 and (M.hideBossPins or M.hideQuestPins or M.hideNotePins) then
        local keep = {}
        for i = 1, #list do
            local p = list[i]
            local k = p.kind or "boss"
            local hide = (M.hideBossPins and (k == "boss" or k == "rare"))
                or (M.hideQuestPins and (k == "icon"
                    or (k == "quest" and DG.QuestState(p.id) == "todo")))
                or (M.hideNotePins and k == "note")
            if not hide then keep[#keep + 1] = p end
        end
        list = keep
    end
    return list
end

local function syncPins(view, id, floor, cw, ch)
    local MWm = ns.MapWindowModule
    view.__mini = (MWm and MWm.IsMiniView and MWm.IsMiniView(view)) and true or nil
    local list = id and floor and pinList(id, floor) or nil
    local n = 0
    local lockedPre, preBlock = {}, {}
    if list and #list > 0 and M.QuestPinsOn() then
        for i = 1, #list do
            local p = list[i]
            if (p.kind or "") == "quest" and p.id then
                local row = DG.QuestRowByID and DG.QuestRowByID(p.id)
                local pre = row and row[9]
                if type(pre) == "table" then
                    for j = 1, #pre do
                        local seg = pre[j]
                        if DG.QuestState(seg) ~= "done" then
                            lockedPre[p.id] = seg
                            preBlock[seg] = p.id
                            break
                        end
                    end
                end
            end
        end
    end
    if list then
        for i = 1, #list do
            if i > MAX_PINS then break end
            local p = list[i]
            local bt = view.pinBtns[i]
            local kind = p.kind or "boss"
            local ps = M.PinScale() * (view.__uiK or 1)
            local dim = (kind == "boss") and M.RareBoss(id, p.en) or false
            bt:SetAlpha(dim and 0.5 or 1)
            bt.nm:SetAlpha(dim and 0.5 or 1)
            local skip
            n = i
            bt.__kind, bt.__p = kind, p
            bt.__dfView = view
            bt.__en, bt.__zh = p.en, p.zh
            if bt.entry then bt.entry:Hide() end
            if bt.rim then bt.rim:Hide() end
            if bt.sym then bt.sym:Hide() end
            if kind == "note" or kind == "quest" or kind == "icon" then
                bt:SetFrameLevel(view.pins:GetFrameLevel() + 2)
            else
                bt:SetFrameLevel(view.pins:GetFrameLevel())
            end
            bt.__qState, bt.__qPre, bt.__qPreOf, bt.__qNeedLv = nil, nil, nil, nil
            M.PinPoint(bt, p, cw, ch)
            local nm, cr, cg, cb
            if kind == "boss" then
                nm = p.zh or p.en or ""
                cr, cg, cb = M.BossColor(id, p.en)
            elseif kind == "quest" or kind == "icon" or kind == "prev" or kind == "next"
                or kind == "entrance" then
                nm = ""
                cr, cg, cb = Host.Unpack(C_GOLD)
            elseif kind == "dungeon" then
                nm = ""
                cr, cg, cb = Host.Unpack(C_GOLD)
            elseif kind == "object" then
                nm = DG.ItemName(p.id)
                cr, cg, cb = Host.Unpack(C_TEXT)
            elseif kind == "note" then
                nm, cr, cg, cb = "", 1, 1, 1
            else
                nm = p.name or ""
                cr, cg, cb = 0.72, 0.76, 0.85
            end
            if kind == "quest" then
                local st = DG.QuestState(p.id)
                local qrow = DG.QuestRowByID and DG.QuestRowByID(p.id)
                local needLv = (type(qrow) == "table") and qrow[3] or nil
                bt.__qNeedLv = needLv
                bt.__av:Hide()
                if st == "todo" then
                    if needLv and (UnitLevel("player") or 0) < needLv then
                        M.PaintQuestPin(bt, "lv", 1)
                        bt.__qState = "lv"
                    elseif lockedPre[p.id] then
                        M.PaintQuestPin(bt, "locked", 1)
                        bt.__qState, bt.__qPre = "locked", lockedPre[p.id]
                    elseif preBlock[p.id] then
                        M.PaintQuestPin(bt, "pre", 1)
                        bt.__qState, bt.__qPreOf = "pre", preBlock[p.id]
                    else
                        M.PaintQuestPin(bt, "avail", 1)
                        bt.__qState = "avail"
                    end
                else
                    if M.hideOtherPins then
                        skip = true
                    else
                        M.PaintQuestPin(bt, st, (st == "done" or st == "active") and 0.45 or 1)
                        bt.__qState = st
                    end
                end
            elseif kind == "entrance" then
                bt.dot:Hide()
                bt.entry:Show()
                bt.__av:Hide()
            elseif kind == "dungeon" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_DOOR_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "icon" then
                M.PaintQuestPin(bt, "avail", 1)
                bt.__av:Hide()
            elseif kind == "prev" or kind == "next" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture((kind == "prev") and M.PIN_STAIR_UP_TEX or M.PIN_STAIR_DN_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "object" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(DG.ItemIcon(p.id))
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "rare" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_BOSS_TEX)
                bt.dot:SetVertexColor(cr, cg, cb)
                bt.__av:Hide()
            elseif kind == "note" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_NOTE_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            else
                bt.dot:Hide()
                bt.__av:Show()
                local isSel = (M.detailEn == p.en) or false
                M.PaintBossPin(bt.__av, M.BossPinDisplay(id, p.en), cr, cg, cb,
                    (isSel and M.PIN_SIZE or M.PIN_MIN) * ps)
            end
            local sel = (kind == "boss") and (M.detailEn == p.en) or false
            if kind == "boss" and not sel then nm = "" end
            bt.nm:SetText(nm or "")
            if bt.__glow then
                local g = M.PIN_GLOW_GAIN
                bt.__glow:SetVertexColor(cr * g, cg * g, cb * g)
                bt.__glow:SetShown(sel)
            end
            if bt.__ring then
                if M.hoverQuestId and kind == "quest" and p.id == M.hoverQuestId then
                    local c = M.PIN_HL_RING_RGB
                    bt.__ring:SetVertexColor(c[1], c[2], c[3])
                    bt.__ring:Show()
                elseif bt == M.pulseBtn and (M.pulseUntil or 0) > GetTime() then
                    bt.__ring:Show()
                else
                    bt.__ring:Hide()
                end
            end
            bt.nm:ClearAllPoints()
            bt.nm:SetPoint("TOP", bt.dot, "BOTTOM", 0, -2)
            bt.nm:SetJustifyH("CENTER")
            local fpath = bt.nm:GetFont()
            if type(fpath) ~= "string" then fpath = ns.FONT or STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF" end
            bt.nm:SetFont(fpath, math.floor(((sel and 14 or 12) * ps) + 0.5), PIN_FLAGS)
            bt.nm:SetTextColor(cr, cg, cb)
            bt.dot:ClearAllPoints()
            bt.dot:SetPoint("CENTER", bt, "CENTER", 0, 0)
            local dsz
            if kind == "note" then
                dsz = M.NOTE_SIZE
            elseif kind == "prev" or kind == "next" then
                dsz = M.STAIR_SIZE
            elseif kind == "dungeon" then
                dsz = M.PIN_MIN * 1.35
            elseif kind == "quest" or kind == "icon" then
                dsz = M.PIN_QUEST_SIZE
            else
                dsz = sel and M.PIN_SIZE or M.PIN_MIN
            end
            bt.dot:SetSize(dsz * ps, dsz * ps)
            local bsz = dsz + 8
            bt:SetSize(bsz * ps, bsz * ps)
            if skip then
                bt.nm:SetText("")
                bt:Hide()
            else
                bt:Show()
            end
        end
    end
    for i = n + 1, MAX_PINS do
        local bt = view.pinBtns[i]
        if bt then
            bt:Hide()
            bt.nm:SetText("")
        end
    end
    view.pins:SetShown(n > 0)
    local hb = M.pulseBtn
    if hb and hb.__ring and (M.pulseUntil or 0) > GetTime()
        and hb:GetParent() == view.pins and hb:IsShown() then
        hb.__ring:Show()
    end
    M.RefreshPulse(view)
    M.ResolvePendingArrive(view)
end

local function syncBar(view, id, layers, idx)
    local panel = view.floorPanel
    local n = layers and #layers or 0
    if n <= 1 then
        for i = 1, M.MAX_LAYERS do view.floorBtns[i]:Hide() end
        panel:Hide()
        return
    end
    local wmax = FLOOR_MIN_W
    for i = 1, n do
        local bt = view.floorBtns[i]
        local txt = floorText(id, i)
        bt:SetText(txt)
        local fs = bt:GetFontString()
        local tw = fs and fs:GetStringWidth() or 0
        if tw + 24 > wmax then wmax = tw + 24 end
    end
    if wmax > FLOOR_MAX_W then wmax = FLOOR_MAX_W end
    wmax = math.ceil(wmax)
    local gap = FLOOR_GAP
    local ch = view.canvas:GetHeight() or 0
    if ch > 0 and (n * (FLOOR_H + gap) > ch * 0.7) then gap = 2 end
    local step = FLOOR_H + gap
    for i = 1, n do
        local bt = view.floorBtns[i]
        bt:SetSize(wmax, FLOOR_H)
        bt:ClearAllPoints()
        bt:SetPoint("TOPLEFT", panel, "TOPLEFT", 5, -(5 + (n - i) * step))
        Host.SetButtonSelected(bt, i == idx)
        bt:Show()
    end
    for i = n + 1, M.MAX_LAYERS do view.floorBtns[i]:Hide() end
    panel:SetSize(wmax + 10, n * step - gap + 10)
    panel:Show()
end

local function syncButtons(view, id)
    local rb, pb = view.routeBtn, view.pinBtn
    local floor = id and floorNumAt(id, M.curLayer or 1)
    local vis, tot = 0, 0
    if id and floor then vis, tot = M.RouteVisibleCount(id, floor) end
    rb:SetText(L["路线显示"])
    setPicked(rb, (tot > 0) and (vis < tot))
    rb:SetShown(M.HasRoute(id) and true or false)
    local any = M.HasKindPins(id, "boss") or M.HasKindPins(id, "quest")
        or M.HasKindPins(id, "note") or M.HasKindPins(id, "stairs")
    local dim = (M.hideBossPins and M.HasKindPins(id, "boss"))
        or (M.hideQuestPins and M.HasHiddenQuestPins(id))
        or (M.hideNotePins and M.HasKindPins(id, "note"))
        or (M.hideOtherPins and (M.HasStatePins(id, "done") or M.HasStatePins(id, "active"))) or false
    pb:SetText(L["图钉显示"])
    setPicked(pb, dim)
    pb:SetShown(any and true or false)
    local rsb = view.routeSetBtn
    if rsb then
        rsb:SetShown(M.HasRoute(id) and true or false)
    end
end

local navTail

local function navTailLeft()
    if navTail and navTail:IsShown() then return navTail:GetLeft() end
    navTail = nil
    if not WorldMapFrame then return nil end
    for _, ch in ipairs({ WorldMapFrame:GetChildren() }) do
        if ch and ch:IsShown() and ch.GetObjectType and ch:GetObjectType() == "Button" then
            for _, reg in ipairs({ ch:GetRegions() }) do
                if reg.GetAtlas then
                    local ok, a = pcall(reg.GetAtlas, reg)
                    if ok and a == "common-dropdown-a-button" then
                        navTail = ch
                        return ch:GetLeft()
                    end
                end
            end
        end
    end
    return nil
end

local function ensureAreaBtn()
    if W.areaBtn or not WorldMapFrame then return W.areaBtn end
    local nav = navBar()
    if not nav then return nil end
    local areaBtn = makeNativeBtn(nav, L["复活区域"], BTN_W, BTN_H)
    areaBtn:SetFrameLevel(nav:GetFrameLevel() + 8)
    ndBtn(areaBtn)
    areaBtn:SetScript("OnClick", function(self)
        local on
        if ns.ExploreAreaToggle then on = ns.ExploreAreaToggle() end
        setPicked(self, not on)
    end)
    areaBtn:SetScript("OnEnter", function(self)
        GameTooltip:ClearLines()
        GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
        local tex = M.LOGO_TEX
            or "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp"
        GameTooltip:AddLine("|T" .. tex .. ":18|t " .. L["复活区域"], 1, 0.82, 0, true)
        GameTooltip:AddLine(L["在世界地图上显示各复活点的覆盖范围。"], 0.75, 0.75, 0.75, true)
        GameTooltip:Show()
    end)
    areaBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    setPicked(areaBtn, not (ns.ExploreAreaOn and ns.ExploreAreaOn()))
    W.areaBtn = areaBtn
    return areaBtn
end

local function syncAreaBtn()
    local ab = ensureAreaBtn()
    if not ab then return end
    if W.leaUI then leaSkin(ab) end
    setPicked(ab, not (ns.ExploreAreaOn and ns.ExploreAreaOn()))
    local lim = navTailLeft()
    local nav = navBar()
    local wmf = WorldMapFrame
    if lim and nav and wmf and wmf.GetLeft and wmf:GetLeft() and wmf:GetTop() then
        local dx = (lim - BTN_GAP) - wmf:GetLeft() - BTN_W
        local dy = (wmf:GetTop() - (nav:GetTop() or 0)) + NAV_PAD_T
        if ab.__dx ~= dx or ab.__dy ~= dy then
            ab.__dx, ab.__dy = dx, dy
            ab.__fb = nil
            ab:ClearAllPoints()
            ab:SetPoint("TOPLEFT", wmf, "TOPLEFT", dx, -dy)
        end
    elseif not ab.__fb then
        ab.__fb = true
        ab.__dx, ab.__dy = nil, nil
        ab:ClearAllPoints()
        ab:SetPoint("TOPRIGHT", nav or wmf, "TOPRIGHT", -(NAV_PAD_R + BTN_W), -NAV_PAD_T)
    end
    if not (ns.ExploreGraveOn and ns.ExploreGraveOn()) then
        if ab:IsShown() then ab:Hide() end
    elseif W.Active() then
        if ab:IsShown() then ab:Hide() end
    else
        if not ab:IsShown() then ab:Show() end
    end
end

local function ensureOpenWinBtn()
    if W.openWinBtn or not WorldMapFrame then return W.openWinBtn end
    local nav = navBar()
    if not nav then return nil end
    local bt = makeNativeBtn(nav, L["副本地图"], BTN_W, BTN_H)
    bt:SetFrameLevel(nav:GetFrameLevel() + 8)
    ndBtn(bt)
    bt:SetScript("OnClick", function()
        local MWm = ns.MapWindowModule
        if not (MWm and MWm.Open) then return end
        local ok, id = pcall(W.Resolve)
        if ok and id then MWm.Open(id) end
    end)
    bt:SetScript("OnEnter", function(self)
        GameTooltip:ClearLines()
        GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
        local tex = M.LOGO_TEX
            or "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp"
        GameTooltip:AddLine("|T" .. tex .. ":18|t " .. L["副本地图"], 1, 0.82, 0, true)
        GameTooltip:AddLine(L["点击查看副本地图"], 0.75, 0.75, 0.75, true)
        GameTooltip:Show()
    end)
    bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
    bt:Hide()
    W.openWinBtn = bt
    return bt
end

local function syncOpenWinBtn()
    local bt = ensureOpenWinBtn()
    if not bt then return end
    local want = false
    if enabled() then
        local ok, id = pcall(W.Resolve)
        want = (ok and id) and true or false
    end
    if not want then
        if bt:IsShown() then bt:Hide() end
        return
    end
    local lim = navTailLeft()
    local nav = navBar()
    local wmf = WorldMapFrame
    if lim and nav and wmf and wmf.GetLeft and wmf:GetLeft() and wmf:GetTop() then
        local dx = (lim - BTN_GAP) - wmf:GetLeft() - BTN_W
        local dy = (wmf:GetTop() - (nav:GetTop() or 0)) + NAV_PAD_T
        if bt.__dx ~= dx or bt.__dy ~= dy then
            bt.__dx, bt.__dy = dx, dy
            bt.__fb = nil
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", wmf, "TOPLEFT", dx, -dy)
        end
    elseif not bt.__fb then
        bt.__fb = true
        bt.__dx, bt.__dy = nil, nil
        bt:ClearAllPoints()
        bt:SetPoint("TOPRIGHT", nav or wmf, "TOPRIGHT", -(NAV_PAD_R + BTN_W), -NAV_PAD_T)
    end
    if not bt:IsShown() then bt:Show() end
end

local CRUMB_X = 0
local CRUMB_PAD = 60

local function padFogBtn(box)
    local wm = _G.WorldMapFrame
    local bf = wm and wm.BorderFrame
    local tc = bf and bf.TitleContainer
    if not tc then return end
    for _, ch in ipairs({ tc:GetChildren() }) do
        if ch and ch.GetObjectType and ch:GetObjectType() == "CheckButton" then
            if not ch.__dfPad then
                ch.__dfPad = true
                ch:ClearAllPoints()
                ch:SetPoint("BOTTOMLEFT", box, "TOPLEFT", CRUMB_PAD, 0)
            end
        end
    end
end

local function shiftCrumb()
    local hb = _G.WorldMapFrameHomeButton
    if not hb then return end
    local box = hb:GetParent()
    if not (box and box.GetPoint and box.SetPoint) then return end
    local anchor, rel, relPoint, x, y = box:GetPoint(1)
    if anchor ~= "TOPLEFT" or type(x) ~= "number" then return end
    if x > CRUMB_X then
        pcall(box.SetPoint, box, anchor, rel, relPoint, CRUMB_X, y)
    end
    padFogBtn(box)
end

local function layout(view)
    shiftCrumb()
    local aw, ah = mapAreaSize()
    if aw <= 0 or ah <= 0 then return end
    local cw, ch, cx, cy = M.FitBox(aw, ah)
    view.cw, view.ch = cw, ch
    local ox, oy = areaOffset()
    if view.stage then
        view.stage:ClearAllPoints()
        view.stage:SetPoint("TOPLEFT", view, "TOPLEFT", ox + cx, -(oy + cy))
        view.stage:SetSize(cw, ch)
    end
    local ZM = ns.MapZoom
    local k = (ZM and ZM.k) or 1
    if ZM then
        local lx, ly = ZM.Limits(cw, ch)
        ZM.ClampTo(lx, ly)
    end
    local zx = (ZM and ZM.x) or 0
    local zy = (ZM and ZM.y) or 0
    local zw, zh = cw * k, ch * k
    view.zw, view.zh = zw, zh
    if view.canvas then
        view.canvas:ClearAllPoints()
        view.canvas:SetPoint("CENTER", view.stage, "CENTER", zx, zy)
        view.canvas:SetSize(zw, zh)
    end
    if view.route then
        view.route:ClearAllPoints()
        view.route:SetPoint("TOPLEFT", view.canvas, "TOPLEFT", 0, 0)
        view.route:SetSize(zw, zh)
    end
    if view.pins then
        view.pins:ClearAllPoints()
        view.pins:SetPoint("TOPLEFT", view.canvas, "TOPLEFT", 0, 0)
        view.pins:SetSize(zw, zh)
    end
    if view.bg then
        view.bg:ClearAllPoints()
        view.bg:SetPoint("TOPLEFT", view, "TOPLEFT", ox, -oy)
        view.bg:SetSize(aw, ah)
    end
    if view.side then
        local q = questPanel()
        local w = (q and q:GetWidth()) or 330
        local x = ox + cx + cw + 6
        local y = oy + cy
        local avail = (view:GetWidth() or 0) - x - 6
        view.sideAvail = avail
        if avail >= 120 then
            if w > avail then w = avail end
            view.sideL, view.sideT = x, y
            view.side:ClearAllPoints()
            view.side:SetPoint("TOPLEFT", view, "TOPLEFT", x, -y)
            view.side:SetSize(w, ch)
        else
            view.side:Hide()
        end
    end
    if view.taskBtn then
        if W.leaUI then
            pcall(view.taskBtn.SetBackdropColor, view.taskBtn, 0, 0, 0, 0)
            pcall(view.taskBtn.SetBackdropBorderColor, view.taskBtn, 0, 0, 0, 0)
            leaSkin(view.taskBtn, true)
        end
        view.taskBtn:ClearAllPoints()
        if W.leaUI then
            view.taskBtn:SetPoint("TOPRIGHT", area(), "TOPRIGHT", -LEA_TASK_X, LEA_ROW + 12)
        else
            local cb = _G.WorldMapFrameCloseButton
            if cb and cb:GetLeft() and cb:IsShown() then
                view.taskBtn:SetPoint("RIGHT", cb, "LEFT", -(cb:GetWidth() + 7), 0)
            elseif WorldMapFrame then
                view.taskBtn:SetPoint("TOPRIGHT", WorldMapFrame, "TOPRIGHT", -76, -8)
            else
                view.taskBtn:SetPoint("TOPRIGHT", view, "TOPRIGHT", -36, -12)
            end
        end
    end
    local nav = navBar()
    if view.block then
        local box = view.stage or view
        view.block:ClearAllPoints()
        view.block:SetPoint("TOPLEFT", box, "TOPLEFT", 0, 0)
        view.block:SetPoint("BOTTOMRIGHT", box, "BOTTOMRIGHT", 0, 0)
    end
    if nav then
        if W.leaUI then
            leaSkin(view.pinBtn)
            leaSkin(view.routeBtn)
            view.pinBtn:ClearAllPoints()
            view.pinBtn:SetPoint("RIGHT", view.taskBtn, "LEFT", -BTN_GAP, 0)
            view.routeBtn:ClearAllPoints()
            view.routeBtn:SetPoint("RIGHT", view.pinBtn, "LEFT", -BTN_GAP, 0)
        else
            local side = view.side
            local lim = navTailLeft()
            local sideL = (side and side:IsShown()) and side:GetLeft() or nil
            if lim and sideL and sideL < lim then lim = sideL end
            if not lim then lim = sideL end
            view.pinBtn:ClearAllPoints()
            if lim and view:GetLeft() and view:GetTop() then
                local dx = (lim - BTN_GAP) - view:GetLeft() - BTN_W
                local dy = (view:GetTop() - (nav:GetTop() or 0)) + NAV_PAD_T
                view.pinBtn:SetPoint("TOPLEFT", view, "TOPLEFT", dx, -dy)
            else
                view.pinBtn:SetPoint("TOPRIGHT", nav, "TOPRIGHT", -NAV_PAD_R, -NAV_PAD_T)
            end
            view.routeBtn:ClearAllPoints()
            view.routeBtn:SetPoint("RIGHT", view.pinBtn, "LEFT", -BTN_GAP, 0)
        end
        if W.areaBtn and W.areaBtn:IsShown() then W.areaBtn:Hide() end
    end
    view.floorPanel:ClearAllPoints()
    view.floorPanel:SetPoint("BOTTOMLEFT", view.stage or view.canvas, "BOTTOMLEFT", 0, 0)
end

local function cursorUI()
    local x, y = GetCursorPosition()
    local s = 1
    if UIParent and UIParent.GetEffectiveScale then
        s = UIParent:GetEffectiveScale() or 1
    end
    if not s or s <= 0 then s = 1 end
    return x / s, y / s
end

local function inStage()
    local view = W.view
    local st = view and view.stage
    if not st then return false end
    local l, r = st:GetLeft(), st:GetRight()
    local t, b = st:GetTop(), st:GetBottom()
    if not (l and r and t and b) then return false end
    local x, y = cursorUI()
    return x >= l and x <= r and y >= b and y <= t
end

function W.PanSync()
    local view = W.view
    local art = view and view.canvas
    local st = view and view.stage
    local ZM = ns.MapZoom
    if not (art and st and ZM) then return end
    art:ClearAllPoints()
    art:SetPoint("CENTER", st, "CENTER", ZM.x, ZM.y)
end

function W.ZoomAt(factor)
    local view = W.view
    local art = view and view.canvas
    local st = view and view.stage
    local ZM = ns.MapZoom
    if not (art and st and ZM) then return end
    local old = ZM.k
    local nk = old * factor
    if nk < ZM.min then nk = ZM.min end
    if nk > ZM.max then nk = ZM.max end
    if nk == old then return end
    local left, top = art:GetLeft(), art:GetTop()
    local w, h = art:GetWidth(), art:GetHeight()
    local vl, vt = st:GetLeft(), st:GetTop()
    local bw, bh = st:GetWidth(), st:GetHeight()
    if not (left and top and vl and vt and w and h and bw and bh) then return end
    if w <= 0 or h <= 0 or bw <= 0 or bh <= 0 then return end
    local cx, cy = cursorUI()
    local u = math.max(0, math.min(1, (cx - left) / w))
    local v = math.max(0, math.min(1, (top - cy) / h))
    local k = nk / old
    local nw, nh = w * k, h * k
    local nleft, ntop = cx - u * nw, cy + v * nh
    ZM.k = nk
    ZM.x = (nleft + nw / 2) - (vl + bw / 2)
    ZM.y = (ntop - nh / 2) - (vt - bh / 2)
    local mx, my = ZM.Limits(bw, bh)
    ZM.ClampTo(mx, my)
    W.Sync()
end

function W.ZoomWheel(delta)
    if not inStage() then return end
    W.movedAt = GetTime()
    W.ZoomAt((delta > 0) and 1.15 or (1 / 1.15))
end

local function dragWorld(self)
    local view = W.view
    local st = view and view.stage
    local ZM = ns.MapZoom
    if not (st and ZM) then return end
    if type(IsMouseButtonDown) ~= "function" or not IsMouseButtonDown("LeftButton") then
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
        M.SetHoverMouse(view.route, true)
        return
    end
    local x, y = cursorUI()
    local lx = self.__lx or x
    local ly = self.__ly or y
    self.__lx, self.__ly = x, y
    local dx, dy = x - lx, y - ly
    if dx == 0 and dy == 0 then return end
    local mx, my = ZM.Limits(st:GetWidth(), st:GetHeight())
    ZM.x, ZM.y = ZM.x + dx, ZM.y + dy
    ZM.ClampTo(mx, my)
    W.PanSync()
end

function W.BeginDrag()
    local view = W.view
    local block = view and view.block
    if not block then return end
    W.movedAt = GetTime()
    M.SetHoverMouse(view.route, false)
    block.__lx, block.__ly = cursorUI()
    block:SetScript("OnUpdate", dragWorld)
end

local function ensureWide()
    if not W.Active() or W.folded or M.sideTask or inCombat() then return end
    local wmf = WorldMapFrame
    local qp = questPanel()
    if not (wmf and wmf.minimizedWidth and wmf:IsShown() and qp) then return end
    if qp:IsShown() then return end
    if (wmf:GetWidth() or 0) > wmf.minimizedWidth + 2 then return end
    pcall(function()
        local extra = qp.GetPanelExtraWidth and qp:GetPanelExtraWidth() or 333
        SetUIPanelAttribute(wmf, "extraWidth", extra)
        wmf:SetWidth((wmf.minimizedWidth or 702) + (wmf.questLogWidth or 333))
        UpdateUIPanelPositions(wmf)
    end)
end

local function syncSpacer()
    local wmf = WorldMapFrame
    local spacer = wmf and wmf.TitleCanvasSpacerFrame
    if not (spacer and spacer.GetNumPoints) then return end
    local reserve
    if W.Active() then
        reserve = (wmf:GetWidth() or 0) > (wmf.minimizedWidth or 702) + 2
    else
        local q = questPanel()
        reserve = (q and q:IsShown()) and true or false
    end
    local want = reserve and (-3 - (wmf.questLogWidth or 333)) or -3
    local cur = -3
    local n = spacer:GetNumPoints() or 0
    for i = 1, n do
        local pt, _, _, x = spacer:GetPoint(i)
        if pt == "BOTTOMRIGHT" and type(x) == "number" then cur = x break end
    end
    ensureWide()
    if inCombat() or math.abs(cur - want) < 1 then return end
    pcall(spacer.SetPoint, spacer, "BOTTOMRIGHT", wmf, "TOPRIGHT", want, -67)
    if wmf.OnFrameSizeChanged then pcall(wmf.OnFrameSizeChanged, wmf) end
end

local function syncQuestCVar()
    if type(GetCVar) ~= "function" or type(SetCVar) ~= "function" then return end
    if W.qLogCVar == nil then return end
    local q = questPanel()
    local want = (q and q:IsShown()) and "1" or "0"
    local ok, cur = pcall(GetCVar, "questLogOpen")
    if ok and cur ~= want then pcall(SetCVar, "questLogOpen", want) end
end

local function panelWideWidth()
    local wmf = WorldMapFrame
    if not wmf then return 0 end
    return (wmf.minimizedWidth or 702) + (wmf.questLogWidth or 330)
end

local function syncPanelToggle()
    local wmf = WorldMapFrame
    local spt = wmf and wmf.SidePanelToggle
    if not spt then return end
    local q = questPanel()
    if spt.Refresh then pcall(spt.Refresh, spt) end
    if spt.OpenButton and spt.CloseButton and q then
        local showOpen
        if W.Active() then
            showOpen = (wmf:GetWidth() or 0) <= (wmf.minimizedWidth or 702) + 2
        else
            showOpen = not q:IsShown()
        end
        if showOpen then
            spt.OpenButton:Show()
            spt.CloseButton:Hide()
        else
            spt.OpenButton:Hide()
            spt.CloseButton:Show()
        end
    end
end

function W.ToggleSideTask()
    if inCombat() then return end
    local v = W.view
    if not (v and v:IsShown()) then return end
    local q = questPanel()
    if M.sideTask then
        W.ResetTask()
        if q and not q:IsShown() then
            local wmf = WorldMapFrame
            if wmf and (wmf:GetWidth() or 0) < panelWideWidth() - 2 then
                setLogPanel(true)
                q:Hide()
            end
        end
    else
        M.sideTask = true
        if q then
            W.qStrata = q:GetFrameStrata()
            W.qLevel = q:GetFrameLevel()
            q:SetFrameStrata("HIGH")
            q:SetFrameLevel(v:GetFrameLevel() + 5)
            setLogPanel(true)
        end
        if v.side then v.side:Hide() end
        if v.block then v.block:EnableMouse(false) end
    end
    syncPanelToggle()
    syncSpacer()
    syncQuestCVar()
    W.UpdateTaskBtn()
    C_Timer.After(0, function()
        if W.Active() then W.Sync() end
    end)
end

local function adoptPanelState()
    local view = W.view
    local q = questPanel()
    if not (view and q) then return end
    local shown = q:IsShown()
    if shown and not M.sideTask then
        q:Hide()
        syncPanelToggle()
        syncSpacer()
        syncQuestCVar()
        return
    end
    if shown then
        if not W.qStrata then
            W.qStrata = q:GetFrameStrata()
            W.qLevel = q:GetFrameLevel()
        end
        q:SetFrameStrata("HIGH")
        q:SetFrameLevel(view:GetFrameLevel() + 5)
    end
    if shown == (M.sideTask and true or false) then return end
    M.sideTask = shown or nil
    if shown then
        if view.side then view.side:Hide() end
        if view.block then view.block:EnableMouse(false) end
    else
        if W.qStrata then
            q:SetFrameStrata(W.qStrata)
            q:SetFrameLevel(W.qLevel or 0)
            W.qStrata, W.qLevel = nil, nil
        end
        if view.side then view.side:Show() end
        if view.block then view.block:EnableMouse(true) end
    end
    W.UpdateTaskBtn()
    syncPanelToggle()
    syncQuestCVar()
end

local function foldTogglePanel()
    if inCombat() then return end
    local wmf = WorldMapFrame
    local q = questPanel()
    local view = W.view
    if not (wmf and q and view) then return end
    local shown = q:IsShown()
    local wide = (wmf:GetWidth() or 0) > (wmf.minimizedWidth or 702) + 2
    if shown then
        W.foldPrevTask = true
        W.folded = true
        if W.qStrata then
            q:SetFrameStrata(W.qStrata)
            q:SetFrameLevel(W.qLevel or 0)
            W.qStrata, W.qLevel = nil, nil
        end
        setLogPanel(false)
        M.sideTask = nil
    elseif wide then
        W.foldPrevTask = nil
        W.folded = true
        pcall(function()
            SetUIPanelAttribute(wmf, "extraWidth", 0)
            wmf:SetWidth(wmf.minimizedWidth)
            UpdateUIPanelPositions(wmf)
        end)
        M.sideTask = nil
    else
        W.folded = nil
        if W.foldPrevTask then
            if not W.qStrata then
                W.qStrata = q:GetFrameStrata()
                W.qLevel = q:GetFrameLevel()
            end
            q:SetFrameStrata("HIGH")
            q:SetFrameLevel(view:GetFrameLevel() + 5)
            setLogPanel(true)
            M.sideTask = true
        else
            pcall(function()
                local extra = q.GetPanelExtraWidth and q:GetPanelExtraWidth() or 333
                SetUIPanelAttribute(wmf, "extraWidth", extra)
                wmf:SetWidth((wmf.minimizedWidth or 702) + (wmf.questLogWidth or 333))
                UpdateUIPanelPositions(wmf)
            end)
            M.sideTask = nil
        end
    end
    local nowShown = q:IsShown()
    local sideOn = (not nowShown) and ((wmf:GetWidth() or 0) > (wmf.minimizedWidth or 702) + 2)
    if view.side then view.side:SetShown(sideOn) end
    if view.block then view.block:EnableMouse(not nowShown) end
    W.UpdateTaskBtn()
    syncPanelToggle()
    syncSpacer()
    syncQuestCVar()
    C_Timer.After(0, function()
        if W.Active() then W.Sync() end
    end)
end

function W.Sync()
    if inCombat() then return end
    local view = W.view
    if not (view and view:IsShown()) then return end
    syncSpacer()
    local id = W.curId
    if not (id and hasArt(id)) then
        view:Hide()
        return
    end
    layout(view)
    local cw, ch = view.zw or 0, view.zh or 0
    if cw <= 0 or ch <= 0 then return end
    local layers = M.LayersFor(id)
    local idx = M.curLayer or 1
    if layers then
        if idx < 1 or idx > #layers then idx = 1 end
        M.curLayer = idx
    end
    local floor = floorNumAt(id, idx)
    paintArt(view, id, idx, cw, ch)
    paintArea(view, id, floor, cw, ch)
    syncRoute(view, id, floor, cw, ch)
    syncPins(view, id, floor, cw, ch)
    syncBar(view, id, layers, idx)
    syncButtons(view, id)
    syncNav(view)
    if view.side then
        M.SideHost = view
        M.SyncSide()
        if (view.sideAvail or 0) < 120 then view.side:Hide() end
    end
    W.UpdateTaskBtn()
end

function W.ResetTask()
    local was = M.sideTask
    M.sideTask = nil
    local q = questPanel()
    if q then
        if W.qStrata and not inCombat() then
            q:SetFrameStrata(W.qStrata)
            W.qStrata = nil
        end
        if W.qLevel and not inCombat() then
            q:SetFrameLevel(W.qLevel)
            W.qLevel = nil
        end
        if was then q:Hide() end
    end
    local v = W.view
    if v and v.side then v.side:SetShown(true) end
    if v and v.block then v.block:EnableMouse(true) end
end

function W.UpdateTaskBtn()
    local v = W.view
    local bt = v and v.taskBtn
    if not bt then return end
    bt:SetText(M.sideTask and L["首领"] or L["任务"])
    bt:SetShown(W.Active() and true or false)
end

local function hookPanelToggle()
    local wmf = WorldMapFrame
    local spt = wmf and wmf.SidePanelToggle
    if not (spt and spt.OpenButton and spt.CloseButton) then return end
    if spt.__dfToggleHook then return end
    spt.__dfToggleHook = true
    for _, b in ipairs({ spt.OpenButton, spt.CloseButton }) do
        local orig = b.GetScript and b:GetScript("OnClick") or nil
        if b.SetScript then
            b:SetScript("OnClick", function(bs, ...)
                if W.Active() then
                    local sk = _G.SOUNDKIT
                    if sk then pcall(PlaySound, sk.IG_MAINMENU_OPTION_CHECKBOX_ON) end
                    foldTogglePanel()
                    return
                end
                if orig then orig(bs, ...) end
            end)
        end
    end
end

function W.OpenDungeon(id)
    if not enabled() then return end
    if not (id and hasArt(id)) then return end
    local MWm = ns.MapWindowModule
    if MWm and MWm.Open then MWm.Open(id) end
end

function W.Show(id, why)
    W.OpenDungeon(id)
end

local function resetSideToggle()
    local wmf = WorldMapFrame
    local spt = wmf and wmf.SidePanelToggle
    if not (spt and W.sptStrata) then return end
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
    pcall(spt.SetFrameStrata, spt, W.sptStrata)
    pcall(spt.SetFrameLevel, spt, W.sptLevel or 1)
    W.sptStrata, W.sptLevel = nil, nil
end

function W.Hide()
    local view = W.view
    if not view then return end
    if ns.MapZoom then ns.MapZoom.Reset() end
    if view.routeBtn then view.routeBtn:Hide() end
    if view.pinBtn then view.pinBtn:Hide() end
    if view.taskBtn then view.taskBtn:Hide() end
    if W.navBtn then W.navBtn:Hide() end
    if dropDown then CloseDropDownMenus() end
    M.SideHost = nil
    W.ResetTask()
    if W.qWas ~= nil and not inCombat() then
        setLogPanel(W.qWas)
        local q = questPanel()
        local wmf = WorldMapFrame
        if q and not q:IsShown() and wmf and wmf.minimizedWidth
            and (wmf:GetWidth() or 0) > wmf.minimizedWidth + 2 and not inCombat() then
            pcall(function()
                SetUIPanelAttribute(wmf, "extraWidth", 0)
                wmf:SetWidth(wmf.minimizedWidth)
                UpdateUIPanelPositions(wmf)
            end)
        end
        W.qWas = nil
    end
    if ns.OpenMapBridge and ns.OpenMapBridge.Restore then pcall(ns.OpenMapBridge.Restore) end
    syncPanelToggle()
    resetSideToggle()
    W.folded = nil
    view:Hide()
    syncSpacer()
    if W.qLogCVar and not inCombat() then
        pcall(SetCVar, "questLogOpen", W.qLogCVar)
        W.qLogCVar = nil
    end
end

function W.Active()
    local view = W.view
    return (view and view:IsShown()) and true or false
end

function W.ExitWorld()
    if not W.Active() then return end
    W.pinned = W.curId
    W.pinnedMap = worldMapID()
    W.Hide()
    W.suppress = true
end

local function setLayer(i)
    local layers = M.LayersFor(W.curId)
    if not (layers and layers[i]) then return end
    if i == (M.curLayer or 1) then return end
    if ns.MapZoom then ns.MapZoom.Reset() end
    local d = M.curD
    if M.frame and M.frame:IsShown() and d and d.id == W.curId then
        M.SetLayer(i)
    else
        M.curLayer = i
    end
    W.Sync()
end

local function onFloorClick(self)
    local i = self.__idx
    if not i then return end
    if i == (M.curLayer or 1) then return end
    setLayer(i)
end

local function routeToggle(self, button)
    local id = W.curId
    if not id then return end
    if button == "RightButton" then
        M.ShowRouteMenu(self)
        return
    end
    local floor = floorNumAt(id, M.curLayer or 1)
    local vis, tot = 0, 0
    if floor then vis, tot = M.RouteVisibleCount(id, floor) end
    if M.routeOff or (tot > 0 and vis < tot) then
        M.routeOff = nil
        local segs = floor and ns.DungeonRoute and ns.DungeonRoute[id] and ns.DungeonRoute[id][floor]
        if type(segs) == "table" and #segs > 0 then
            for i = 1, #segs do
                M.routeHidden[M.RouteSegKey(id, floor, i)] = nil
            end
            M.SaveSegHidden(id, floor)
        end
    else
        M.routeOff = true
    end
    M.SaveMapFlags()
    W.Sync()
end

local NAV_H, NAV_Y, NAV_OVL, NAV_ARROW, NAV_MIN_W = 29, -2, 0, 20, 96
local PIN_ATLAS, PIN_ENTRY_SIZE, PIN_ENTRY_MAX = "dungeon", 22, 28

local ZONE_OF, ZONE_LIST, ZONE_NAME

local function zoneNameIndex()
    if ZONE_NAME then return ZONE_NAME end
    local out = {}
    for i = 1401, 3000 do
        local ok, info = pcall(C_Map.GetMapInfo, i)
        if ok and type(info) == "table" and type(info.name) == "string" then
            local k = nameKey(info.name)
            if k and out[k] == nil then out[k] = i end
        end
    end
    ZONE_NAME = out
    return out
end

local function zoneMapByText(txt)
    if type(txt) ~= "string" or txt == "" then return nil end
    local idx = zoneNameIndex()
    local nk = nameKey(txt)
    local hit = nk and idx[nk]
    if hit then return hit end
    local plain = txt:gsub("%b()", ""):gsub("%b（）", "")
    for seg in plain:gmatch("[^,，、]+") do
        hit = idx[nameKey(seg)]
        if hit then return hit end
    end
    if nk then
        local best, bestLen
        for k, id in pairs(idx) do
            if #k >= 3 and nk:sub(1, #k) == k and (not bestLen or #k > bestLen) then
                best, bestLen = id, #k
            end
        end
        if best then return best end
    end
    return nil
end

local function buildZoneIndex()
    if ZONE_OF then return end
    local of, list = {}, {}
    local IM = mapTable()
    local ds = ns.DungeonData and ns.DungeonData.dungeons
    for i = 1, #(ds or {}) do
        local d = ds[i]
        if not d.noList then
            local entry = ns.DungeonEntry and ns.DungeonEntry[d.id]
            local zid
            if type(entry) == "table" and type(entry[1]) == "number" then zid = entry[1] end
            if not zid and IM and type(IM.zone) == "table" then zid = IM.zone[d.id] end
            if not zid then zid = zoneMapByText(d.zone) end
            if zid and hasArt(d.id) then
                of[d.id] = zid
                local row = list[zid]
                if not row then
                    row = {}
                    list[zid] = row
                end
                row[#row + 1] = {
                    id = d.id, name = d.name,
                    x = type(entry) == "table" and tonumber(entry[2]) or nil,
                    y = type(entry) == "table" and tonumber(entry[3]) or nil,
                }
            end
        end
    end
    local zm = M.ZONE_MENU
    if type(zm) == "table" then
        for mid, ids in pairs(zm) do
            local old = list[mid] or {}
            local byId = {}
            for i = 1, #old do byId[old[i].id] = old[i] end
            local ax, ay
            for i = 1, #old do
                if old[i].x and old[i].y then ax, ay = old[i].x, old[i].y break end
            end
            local row, seen = {}, {}
            for i = 1, #ids do
                local did = ids[i]
                if hasArt(did) and not seen[did] then
                    local r = byId[did]
                    if not r then
                        local d = detailOf(did)
                        r = { id = did, name = (d and d.name) or did }
                    end
                    if ax and not (r.x and r.y) then r.x, r.y = ax, ay end
                    row[#row + 1] = r
                    seen[did] = true
                end
            end
            for i = 1, #old do
                if not seen[old[i].id] then
                    row[#row + 1] = old[i]
                    seen[old[i].id] = true
                end
            end
            list[mid] = row
        end
    end
    ZONE_OF, ZONE_LIST = of, list
end

function W.ZoneOf(id)
    buildZoneIndex()
    return (type(id) == "string") and ZONE_OF[id] or nil
end

function W.DungeonsIn(mapID)
    buildZoneIndex()
    return (type(mapID) == "number") and ZONE_LIST[mapID] or nil
end

function W.EntriesIn(mapID)
    local list = W.DungeonsIn(mapID)
    if not list then return nil end
    local out
    for i = 1, #list do
        local r = list[i]
        if r.x and r.y then
            out = out or {}
            out[#out + 1] = r
        end
    end
    return out
end

local DROP_COL = {
    rec = { 1, 0.82, 0 },
    now = { 0.74, 0.80, 0.90 },
    up = { 0.74, 0.72, 0.68 },
}

local function dropHex(c)
    return string.format("%02x%02x%02x",
        math.floor(c[1] * 255 + 0.5),
        math.floor(c[2] * 255 + 0.5),
        math.floor(c[3] * 255 + 0.5))
end

local function dropName(d)
    local full = detailOf(d.id) or d
    local dg = ns.DungeonDG
    local lv = (type(UnitLevel) == "function") and (UnitLevel("player") or 0) or 0
    local g = (dg and dg.GroupOf and full.levelMin) and dg.GroupOf(full, lv) or nil
    local c = g and DROP_COL[g]
    if not (c and d.name) then return d.name end
    return "|cff" .. dropHex(c) .. d.name .. "|r"
end

local function dropdownInit(_, level)
    local list = W.menuList
    local info = UIDropDownMenu_CreateInfo()
    if not (list and #list > 0) then
        info.text = L["本区域暂无副本"]
        info.disabled = true
        info.notCheckable = true
        UIDropDownMenu_AddButton(info, level)
        return
    end
    for i = 1, #list do
        local d = list[i]
        info = UIDropDownMenu_CreateInfo()
        info.text = dropName(d)
        info.checked = (d.id == W.curId) or nil
        info.func = function() W.OpenDungeon(d.id) end
        UIDropDownMenu_AddButton(info, level)
    end
end

local function ensureMenu()
    if dropDown then return dropDown end
    dropDown = CreateFrame("Frame", "DungeonsForeverDungeonDropDown", UIParent, "UIDropDownMenuTemplate")
    dropDown.displayMode = "MENU"
    dropDown.initialize = dropdownInit
    UIDropDownMenu_Initialize(dropDown, dropdownInit, "MENU")
    UIDropDownMenu_SetWidth(dropDown, 160)
    return dropDown
end

function W.OpenEntryMenu(ids, anchor)
    if type(ids) ~= "table" or #ids < 1 then return end
    if #ids == 1 then
        W.OpenDungeon(ids[1])
        return
    end
    local rows = {}
    for i = 1, #ids do
        local d = detailOf(ids[i])
        rows[i] = { id = ids[i], name = (d and d.name) or ids[i] }
    end
    ensureMenu()
    W.menuList = rows
    CloseDropDownMenus()
    ToggleDropDownMenu(1, nil, dropDown, anchor or UIParent, 0, 0)
end

local function styleNavBtn(bt)
    if not bt then return end
    for _, reg in ipairs({ bt:GetRegions() }) do
        if reg.GetObjectType and reg:GetObjectType() == "Texture" then
            local l, r = reg:GetTexCoord()
            l, r = l or 0, r or 0
            if math.abs(l - 0.633) < 0.01 and math.abs(r - 0.758) < 0.01 then
                reg:Hide()
            elseif math.abs(l - 0.002) < 0.01 and math.abs(r - 0.375) < 0.01 then
                reg:Show()
            end
        end
    end
end

function W.EnsureNav()
    if W.navBtn then return W.navBtn end
    local nav = navBar()
    if not nav then return nil end
    local bt = CreateFrame("Button", nil, nav, "NavButtonTemplate")
    bt.listFunc = function() return nil end
    bt:SetHeight(NAV_H)
    bt:SetFrameLevel(nav:GetFrameLevel() + 3)
    if type(bt.MenuArrowButton) == "table" then
        bt.MenuArrowButton:Hide()
        bt.MenuArrowButton:SetScript("OnClick", nil)
    end
    bt:SetScript("OnClick", function(self)
        ensureMenu()
        W.menuList = W.DungeonsIn((W.view and W.view:IsShown()) and W.zoneMap or worldMapID())
        CloseDropDownMenus()
        ToggleDropDownMenu(1, nil, dropDown, self, 0, 0)
    end)
    bt:Hide()
    W.navBtn = bt
    styleNavBtn(bt)
    if ns.NDuiNavButton then ns.NDuiNavButton(bt) end
    return bt
end

local function navRightLimit(view, nav)
    local limit
    local pb = view and view.pinBtn
    local rb = view and view.routeBtn
    if pb and pb:IsShown() then limit = pb:GetLeft() end
    if rb and rb:IsShown() then
        local l = rb:GetLeft()
        if not limit or (l and l < limit) then limit = l end
    end
    if not limit then limit = nav:GetRight() end
    return limit
end

local function lastCrumbRight(nav)
    local right, level, last
    local list = nav.navList
    for i = 1, #(list or {}) do
        local b = list[i]
        if b:IsShown() then
            local r = b:GetRight()
            if r and ((not right) or r > right) then
                right = r
                level = b:GetFrameLevel()
                last = b
            end
        end
    end
    return right, level, last
end

local function crumbTextWidth(bt)
    local fs = bt.text
    if type(fs) ~= "table" then fs = bt.label end
    if type(fs) ~= "table" and bt.GetFontString then fs = bt:GetFontString() end
    local w = (type(fs) == "table") and fs.GetStringWidth and fs:GetStringWidth() or nil
    return (type(w) == "number") and w or 60
end

local function hookCrumbs(nav)
    local list = nav and nav.navList
    if type(list) ~= "table" then return end
    for i = 1, #list do
        local b = list[i]
        if type(b) == "table" and not b.__dfCrumb and b.HookScript then
            b.__dfCrumb = true
            b:HookScript("OnClick", function()
                if W.Active() then W.ExitWorld() end
            end)
        end
    end
end

local function raiseSideToggle()
    if not enabled() then return end
    local wmf = WorldMapFrame
    local spt = wmf and wmf.SidePanelToggle
    if not spt then return end
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
    if W.sptStrata == nil then
        W.sptStrata = spt:GetFrameStrata()
        W.sptLevel = spt:GetFrameLevel()
    end
    if spt:GetFrameStrata() ~= "TOOLTIP" then pcall(spt.SetFrameStrata, spt, "TOOLTIP") end
    local lv = math.min((wmf:GetFrameLevel() or 0) + 3000, 9300)
    if (spt:GetFrameLevel() or 0) < lv then pcall(spt.SetFrameLevel, spt, lv) end
end

local function skinChrome()
    local S = W.__dfSkin
    if not (S and S.Button) then return end
    if not (W.EUIMapSkin and W.EUIMapSkin()) then return end
    local view = W.view
    for _, bt in ipairs({ view and view.routeBtn, view and view.pinBtn, W.areaBtn, W.navBtn }) do
        if bt and not bt.__dfSkinned then
            bt.__dfSkinned = true
            pcall(S.Button, bt)
        end
    end
end
W.skinChrome = skinChrome

if EllesmereUI and EllesmereUI.RegisterSkin then
    pcall(EllesmereUI.RegisterSkin, "DungeonsForever", function(S)
        W.__dfSkin = S
        pcall(skinChrome)
    end)
end

syncNav = function(view)
    local bt = W.EnsureNav()
    local nav = navBar()
    if not (bt and nav) then return end
    hookCrumbs(nav)
    local navDead = (not nav:IsShown()) or ((nav.GetAlpha and nav:GetAlpha()) or 1) <= 0
    local wantParent = navDead and WorldMapFrame or nav
    if bt:GetParent() ~= wantParent then bt:SetParent(wantParent) end
    W.leaUI = navDead and true or false
    local active = view and view:IsShown()
    local cover = view and view.crumbCover
    local zone = active and W.zoneMap or worldMapID()
    local list = zone and W.DungeonsIn(zone)
    if not (list and #list > 0) then
        bt:Hide()
        if cover then cover:Hide() end
        return
    end
    local name
    if active and W.curId and hasArt(W.curId) then
        local d = detailOf(W.curId)
        name = d and d.name
    end
    name = name or L["选择副本"]
    local fs = bt.text
    if type(fs) == "table" and fs.SetText then
        fs:SetText(name)
    elseif bt.SetText then
        pcall(bt.SetText, bt, name)
    end
    if navDead then
        local sc = area()
        leaSkin(bt, true)
        local w = crumbTextWidth(bt) + NAV_ARROW
        if w < NAV_MIN_W then w = NAV_MIN_W end
        bt:SetWidth(w)
        bt:ClearAllPoints()
        local placed
        if sc and sc.GetLeft and sc.GetRight then
            local want
            if C_Map and C_Map.GetMapInfo and WorldMapFrame.GetMapID then
                local okm, minfo = pcall(C_Map.GetMapInfo, WorldMapFrame:GetMapID())
                want = okm and minfo and minfo.name or nil
            end
            local fs = leaTitleFS(want)
            local fsR = fs and fs.GetRight and fs:GetRight() or nil
            local routeL = sc:GetRight() - LEA_ROUTE_L
            if fsR and fsR > sc:GetLeft() and routeL - fsR > w + 24 then
                local left = fsR + (routeL - fsR - w) / 2
                bt:SetPoint("TOPLEFT", sc, "TOPLEFT", left - sc:GetLeft(), LEA_ROW + 15)
                placed = true
            end
        end
        if not placed then
            bt:SetPoint("TOPRIGHT", sc or WorldMapFrame, "TOPRIGHT", -(LEA_ROUTE_L + 6), LEA_ROW + 15)
        end
        bt:SetFrameStrata("HIGH")
        bt:SetFrameLevel(math.min((WorldMapFrame:GetFrameLevel() or 0) + 3000, 9300))
        bt:Show()
        if cover then
            cover.__hover = nil
            if cover.hl then cover.hl:Hide() end
            cover:Hide()
        end
        return
    end
    local navLeft = nav:GetLeft() or 0
    local x = 0
    local crumbRight, crumbLevel, crumbLast = lastCrumbRight(nav)
    if crumbRight then x = math.max(0, (crumbRight - navLeft) - NAV_OVL) end
    local baseLevel = nav:GetFrameLevel()
    if bt:GetFrameStrata() ~= nav:GetFrameStrata() then bt:SetFrameStrata(nav:GetFrameStrata()) end
    local lv = (crumbLevel or (baseLevel + 1)) - 1
    if lv < baseLevel then lv = baseLevel end
    if bt:GetFrameLevel() ~= lv then bt:SetFrameLevel(lv) end
    local lim = navRightLimit(view, nav)
    local avail = (lim or 0) - 6 - (navLeft + x)
    if avail < 40 then avail = 40 end
    local w = crumbTextWidth(bt) + NAV_ARROW
    if w < NAV_MIN_W then w = NAV_MIN_W end
    if w > avail then w = avail end
    bt:SetWidth(w)
    bt:ClearAllPoints()
    bt:SetPoint("TOPLEFT", nav, "TOPLEFT", x, NAV_Y)
    bt:Show()
    if cover then
        local cx = crumbLast and crumbLast:GetLeft()
        local cy = crumbLast and crumbLast:GetTop()
        local cw = crumbLast and crumbLast:GetWidth()
        local ch = crumbLast and crumbLast:GetHeight()
        local navTop = nav:GetTop()
        if active and cx and cy and cw and ch and navTop then
            cover:ClearAllPoints()
            cover:SetPoint("TOPLEFT", nav, "TOPLEFT", cx - navLeft, cy - navTop)
            cover:SetSize(cw, ch)
            cover:Show()
            if cover.hl and not cover.__hover then cover.hl:Hide() end
        else
            cover.__hover = nil
            if cover.hl then cover.hl:Hide() end
            cover:Hide()
        end
    end
    skinChrome()
end

local entryPins, entryProvider = {}, nil

local function entryPin(i, canvas)
    local pin = entryPins[i]
    if pin then
        if pin:GetParent() ~= canvas then pin:SetParent(canvas) end
        return pin
    end
    pin = CreateFrame("Button", nil, canvas)
    pin:SetSize(PIN_ENTRY_SIZE, PIN_ENTRY_SIZE)
    pin.icon = pin:CreateTexture(nil, "ARTWORK")
    pin.icon:SetAllPoints()
    pin.icon:SetAtlas(PIN_ATLAS)
    pin.hl = pin:CreateTexture(nil, "OVERLAY")
    pin.hl:SetPoint("CENTER")
    pin.hl:SetSize(PIN_ENTRY_SIZE + 10, PIN_ENTRY_SIZE + 10)
    pin.hl:SetTexture(M.PIN_GLOW_TEX)
    pin.hl:SetBlendMode("ADD")
    pin.hl:SetVertexColor(1, 0.82, 0.2, 0.9)
    pin.hl:Hide()
    pin:SetScript("OnEnter", function(self)
        pin.hl:Show()
        local ids = self.__ids
        if not (ids and #ids > 0) then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        local names = {}
        for i = 1, #ids do
            local d = detailOf(ids[i])
            names[#names + 1] = (d and d.name) or ids[i]
        end
        if #names == 1 then
            GameTooltip:AddLine(names[1], 1, 0.82, 0)
        else
            for i = 1, #names do
                GameTooltip:AddLine(names[i], 1, 0.82, 0)
            end
        end
        local d1 = detailOf(ids[1])
        if d1 and d1.zone then GameTooltip:AddLine(d1.zone, 0.7, 0.7, 0.7) end
        GameTooltip:AddLine(#ids > 1 and L["点击选择副本"] or L["点击查看副本地图"], 0.6, 0.6, 0.6)
        GameTooltip:Show()
    end)
    pin:SetScript("OnLeave", function(self)
        pin.hl:Hide()
        GameTooltip:Hide()
    end)
    pin:SetScript("OnClick", function(self)
        local ids = self.__ids
        if not (ids and #ids > 0) then return end
        if #ids == 1 then
            W.OpenDungeon(ids[1])
            return
        end
        ensureMenu()
        W.menuList = self.__rows
        CloseDropDownMenus()
        ToggleDropDownMenu(1, nil, dropDown, self, 0, 0)
    end)
    pin:Hide()
    entryPins[i] = pin
    return pin
end

local function ArtTopLevel()
    local api = _G.OpenMapAPI
    if type(api) ~= "table" then return 0 end
    local ok, st = pcall(api.IsStitched)
    if not (ok and st) then return 0 end
    local ok2, top = pcall(api.ArtTopLevel)
    if ok2 and type(top) == "number" then return top + 4 end
    return 0
end

local function placeEntryPin(pin, canvas, row)
    local cs = canvas:GetScale() or 1
    local s = (cs > 0) and (1 / cs) or 1
    pin:SetScale(s)
    pin:ClearAllPoints()
    pin:SetPoint("CENTER", canvas, "TOPLEFT",
        canvas:GetWidth() * row.x / 100 / s, -canvas:GetHeight() * row.y / 100 / s)
end

local Provider = {}

function Provider:RemoveAllData()
    for i = 1, (self.shown or 0) do
        if entryPins[i] then entryPins[i]:Hide() end
    end
    self.shown = 0
end

local function CurMap(self)
    local wmf = _G.WorldMapFrame
    if wmf and wmf.GetMapID then
        local ok, id = pcall(wmf.GetMapID, wmf)
        if ok and type(id) == "number" and id > 0 then return wmf, id end
    end
    local m = self and self.GetMap and self:GetMap()
    return m, m and m.GetMapID and m:GetMapID()
end

local function StitchedRows(host)
    local api = _G.OpenMapAPI
    if type(api) ~= "table" or type(host) ~= "number" then return nil end
    if ArtTopLevel() <= 0 then return nil end
    local de = ns.DungeonEntry
    if type(de) ~= "table" then return nil end
    local out
    for id, e in pairs(de) do
        if type(e) == "table" and type(e[1]) == "number" and e[2] and e[3] and hasArt(id) then
            local oku, u, v = pcall(api.WorldFromMap, e[1], e[2] / 100, e[3] / 100)
            if oku and u then
                local okm, cx, cy = pcall(api.MapFromWorld, host, u, v)
                if okm and cx and cy and cx > -0.05 and cx < 1.05 and cy > -0.05 and cy < 1.05 then
                    out = out or {}
                    local d = detailOf(id)
                    out[#out + 1] = { id = id, name = (d and d.name) or id,
                                      x = cx * 100, y = cy * 100 }
                end
            end
        end
    end
    return out
end

local function leaClickTakeover()
    local sc = area()
    if not (sc and sc.HookScript) or sc.__dfLeaClick then return end
    sc.__dfLeaClick = true
    sc:HookScript("OnMouseUp", function(_, button)
        if button ~= "LeftButton" or W.Active() then return end
        if not enabled() then return end
        local map, mapID = CurMap(nil)
        if not (map and mapID) then return end
        local canvas = map.GetCanvas and map:GetCanvas()
        if not (canvas and canvas.GetLeft and canvas.GetEffectiveScale) then return end
        local cx, cy = GetCursorPosition()
        local L, T = canvas:GetLeft(), canvas:GetTop()
        local Wd, Hd = canvas:GetWidth(), canvas:GetHeight()
        local es = canvas:GetEffectiveScale()
        if not (L and T and Wd and Hd and Wd > 1 and Hd > 1 and es and es > 0) then return end
        local px = (cx - L) / (Wd * es) * 100
        local py = (T - cy) / (Hd * es) * 100
        local leaPin
        local okc, kids = pcall(function() return { canvas:GetChildren() } end)
        if okc and type(kids) == "table" then
            for _, ch in ipairs(kids) do
                local d = type(ch) == "table" and ch.data
                if type(ch) == "table" and ch.isLeaMapsPin and type(d) == "table"
                    and (not ch.IsShown or ch:IsShown()) then
                    local k = d[1]
                    if k == "Dungeon" or k == "Raid" or k == "Dunraid" then
                        local dx, dy = (tonumber(d[2]) or -999) - px, (tonumber(d[3]) or -999) - py
                        if dx * dx + dy * dy <= 25 then leaPin = true break end
                    end
                end
            end
        end
        if not leaPin then return end
        local ov = leaFind()
        if ov and ov:IsShown() then ov:Hide() end
        local rows = StitchedRows(mapID) or W.EntriesIn(mapID)
        local ids
        if rows and #rows > 0 then
            for i = 1, #rows do
                local r = rows[i]
                local dx, dy = r.x - px, r.y - py
                if dx * dx + dy * dy <= 64 then
                    ids = ids or {}
                    ids[#ids + 1] = r.id
                end
            end
        end
        if not ids then
            local list = W.DungeonsIn(mapID)
            if list and #list > 0 then
                for i = 1, #list do
                    ids = ids or {}
                    ids[#ids + 1] = list[i].id
                end
            end
        end
        if not ids then return end
        W.OpenEntryMenu(ids)
    end)
end

local function leaPinEntry(pin)
    local d = type(pin) == "table" and pin.data
    if type(d) ~= "table" then return nil end
    local k = d[1]
    if not (k == "Dungeon" or k == "Raid" or k == "Dunraid") then return nil end
    local x, y = tonumber(d[2]), tonumber(d[3])
    if not (x and y) then return nil end
    local wmf = _G.WorldMapFrame
    if not (wmf and wmf.GetMapID) then return nil end
    local ok, mapID = pcall(wmf.GetMapID, wmf)
    if not (ok and type(mapID) == "number") then return nil end
    local rows = W.EntriesIn(mapID)
    if not (rows and #rows > 0) then return nil end
    local best, bestD = nil, 25
    for i = 1, #rows do
        local r = rows[i]
        if r.x and r.y then
            local dx, dy = r.x - x, r.y - y
            local dd = dx * dx + dy * dy
            if dd <= bestD then best, bestD = r.id, dd end
        end
    end
    return best
end

function Provider:RefreshAllData()
    if inCombat() then return end
    self:RemoveAllData()
    self.groups = nil
    if not (ns.MapEntryOn and ns.MapEntryOn()) then return end
    local map, mapID = CurMap(self)
    local rows = StitchedRows(mapID) or (mapID and W.EntriesIn(mapID))
    if ns.OpenMapBridge then rows = ns.OpenMapBridge.Keep(rows) end
    rows = dropLeaDupes(rows)
    if not (rows and #rows > 0) then return end
    local canvas = map and map.GetCanvas and map:GetCanvas()
    if not canvas or (canvas:GetWidth() or 0) <= 1 then return end
    local groups, byKey = {}, {}
    for i = 1, #rows do
        local r = rows[i]
        local key = string.format("%.0f:%.0f", r.x, r.y)
        local g = byKey[key]
        if not g then
            g = { x = r.x, y = r.y, rows = {} }
            byKey[key] = g
            groups[#groups + 1] = g
        end
        g.rows[#g.rows + 1] = r
    end
    local level = 2000
    local ok, mgr = pcall(function() return map:GetPinFrameLevelsManager() end)
    if ok and mgr then
        local ok2, lv = pcall(function() return mgr:GetValidFrameLevel("PIN_FRAME_LEVEL_DUNGEON_ENTRANCE") end)
        if ok2 and type(lv) == "number" then level = lv end
    end
    level = math.max(level, ArtTopLevel())
    local n = math.min(#groups, PIN_ENTRY_MAX)
    for i = 1, n do
        local g = groups[i]
        local pin = entryPin(i, canvas)
        local ids = {}
        for k = 1, #g.rows do ids[k] = g.rows[k].id end
        pin.__ids = ids
        pin.__rows = g.rows
        pin:SetFrameStrata(canvas:GetFrameStrata())
        pin:SetFrameLevel(level)
        placeEntryPin(pin, canvas, g)
        pin:Show()
    end
    self.groups = groups
    self.shown = n
end

function Provider:Relayout()
    local map = CurMap(self)
    local canvas = map and map.GetCanvas and map:GetCanvas()
    if not (canvas and self.groups) then return end
    for i = 1, math.min(#self.groups, self.shown or 0) do
        placeEntryPin(entryPins[i], canvas, self.groups[i])
    end
end

function Provider:OnMapChanged()
    if inCombat() then return end
    self:RefreshAllData()
end

function Provider:OnCanvasScaleChanged() self:Relayout() end

function Provider:OnCanvasSizeChanged() self:RefreshAllData() end

function Provider:OnHide() self:RemoveAllData() end

local epSig

local function driveEntryPins()
    if not (entryProvider and WorldMapFrame) then return end
    if inCombat() then return end
    local map = CurMap(nil)
    if not (map and map.GetCanvas) then return end
    local lm = _G.WorldMapFrame
    local lid
    if lm and lm.GetMapID then
        local okid, id = pcall(lm.GetMapID, lm)
        if okid and type(id) == "number" and id > 0 then lid = id end
    end
    local cv = map:GetCanvas()
    local canvas = cv
    local mapID = lid or map:GetMapID()
    local cs = (canvas and canvas:GetScale()) or 0
    local cw = (canvas and canvas:GetWidth()) or 0
    local ch = (canvas and canvas:GetHeight()) or 0
    local sig = table.concat({
        tostring(mapID), tostring(cs), tostring(cw), tostring(ch),
        W.Active() and "1" or "0", tostring(ArtTopLevel()),
    }, "|")
    if sig == epSig then return end
    epSig = sig
    if W.Active() then entryProvider:RemoveAllData(); return end
    entryProvider:RefreshAllData()
end

W.RefreshPins = driveEntryPins

local leaSupAt = 0

local function leaSuppressPins()
    if not enabled() then return end
    local now = GetTime()
    if now - leaSupAt < 0.2 then return end
    leaSupAt = now
    local wmf = WorldMapFrame
    if not (wmf and wmf.GetCanvas) then return end
    local ok, canvas = pcall(wmf.GetCanvas, wmf)
    if not (ok and canvas and canvas.GetChildren) then return end
    local hid
    for _, ch in ipairs({ canvas:GetChildren() }) do
        if type(ch) == "table" and ch.isLeaMapsPin and leaPinEntry(ch) then
            if not ch.__dfSup then
                ch.__dfSup = true
                if ch.HookScript then
                    pcall(ch.HookScript, ch, "OnShow", function(p)
                        if leaPinEntry(p) then p:Hide() end
                    end)
                end
            end
            if ch:IsShown() then
                ch:Hide()
                hid = true
            end
        end
    end
    if hid then
        epSig = nil
        pcall(driveEntryPins)
    end
end

local function attachPins()
    if entryProvider or not WorldMapFrame then return end
    if type(CreateFromMixins) ~= "function" or type(MapCanvasDataProviderMixin) ~= "table" then return end
    local ok, p = pcall(function()
        return CreateFromMixins(MapCanvasDataProviderMixin, Provider)
    end)
    if not (ok and p) then return end
    entryProvider = p
    W.pinProvider = p
    if hooksecurefunc then
        pcall(hooksecurefunc, WorldMapFrame, "OnMapChanged", driveEntryPins)
        pcall(hooksecurefunc, WorldMapFrame, "OnCanvasScaleChanged", driveEntryPins)
    end
    if WorldMapFrame.HookScript then
        pcall(WorldMapFrame.HookScript, WorldMapFrame, "OnShow", driveEntryPins)
    end
    if WorldMapFrame.IsShown and WorldMapFrame:IsShown() then
        pcall(driveEntryPins)
    end
end

function W.ApplyEntryToggle()
    epSig = nil
    if entryProvider then
        entryProvider:RemoveAllData()
        entryProvider.groups = nil
    end
    if enabled() then
        W.suppress = nil
        if not W.hooked and W.Hook then pcall(W.Hook) end
        if W.watch and W.watchUpdate then
            pcall(W.watch.SetScript, W.watch, "OnUpdate", W.watchUpdate)
        end
        if W.__onShow and WorldMapFrame and WorldMapFrame:IsShown() then pcall(W.__onShow) end
    else
        W.pinned, W.pinnedMap = nil, nil
        if W.Active() then pcall(W.Hide) end
        W.suppress = true
        if W.watch then pcall(W.watch.SetScript, W.watch, "OnUpdate", nil) end
        if W.navBtn then W.navBtn:Hide() end
        local spt = WorldMapFrame and WorldMapFrame.SidePanelToggle
        if spt and W.sptStrata then
            pcall(spt.SetFrameStrata, spt, W.sptStrata)
            if W.sptLevel then pcall(spt.SetFrameLevel, spt, W.sptLevel) end
        end
    end
    driveEntryPins()
end

local function buildPinPool(view)
    local pins = view.pins
    local pinText = CreateFrame("Frame", nil, pins)
    pinText:SetAllPoints()
    pinText:SetFrameLevel(pins:GetFrameLevel() + 1)
    local btns = {}
    for i = 1, MAX_PINS do
        local bt = CreateFrame("Button", nil, pins)
        bt:SetSize(M.PIN_SIZE, M.PIN_SIZE)
        bt.__idx = i
        bt.nm = makeFS(pinText, 12, C_GOLD, "CENTER")
        bt.nm:SetFont(fontPath(), 12, PIN_FLAGS)
        bt.nm:SetShadowColor(0, 0, 0, 1)
        bt.nm:SetShadowOffset(1, -1)
        bt.dot = bt:CreateTexture(nil, "OVERLAY")
        bt.dot:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.dot:SetSize(M.PIN_SIZE, M.PIN_SIZE)
        bt.dot:SetTexture(M.PIN_BOSS_TEX)
        bt.dot:SetVertexColor(1, 0.82, 0)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.dot) end
        bt.rim = bt:CreateTexture(nil, "OVERLAY", nil, 1)
        bt.rim:SetAllPoints(bt.dot)
        bt.rim:SetTexture(M.PIN_QUEST_RIM_TEX)
        bt.rim:SetVertexColor(M.PIN_QUEST_RIM_RGB[1], M.PIN_QUEST_RIM_RGB[2], M.PIN_QUEST_RIM_RGB[3])
        bt.rim:Hide()
        bt.sym = bt:CreateTexture(nil, "OVERLAY", nil, 2)
        bt.sym:SetAllPoints(bt.dot)
        bt.sym:Hide()
        bt.entry = bt:CreateTexture(nil, "ARTWORK", nil, 2)
        bt.entry:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.entry:SetSize(M.PIN_SIZE * 0.62, M.PIN_SIZE * 0.62)
        bt.entry:SetTexture(M.PIN_DOOR_TEX)
        pcall(bt.entry.SetAtlas, bt.entry, "dungeon")
        bt.entry:Hide()
        bt.__glow = bt:CreateTexture(nil, "BACKGROUND", nil, -1)
        bt.__glow:SetTexture(M.PIN_GLOW_TEX)
        bt.__glow:SetBlendMode("ADD")
        bt.__glow:SetSize(M.PIN_SIZE * M.PIN_GLOW_K, M.PIN_SIZE * M.PIN_GLOW_K)
        bt.__glow:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.__glow:Hide()
        bt.__ring = bt:CreateTexture(nil, "BACKGROUND", nil, -2)
        bt.__ring:SetTexture(M.PIN_RING_TEX)
        bt.__ring:SetBlendMode("ADD")
        bt.__ring:SetVertexColor(M.PIN_RING_RGB[1], M.PIN_RING_RGB[2], M.PIN_RING_RGB[3])
        bt.__ring:SetSize(M.PIN_SIZE * M.PIN_RING_K, M.PIN_SIZE * M.PIN_RING_K)
        bt.__ring:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.__ring:Hide()
        bt.__av = CreateFrame("Frame", nil, bt)
        bt.__av:SetSize(M.PIN_MIN, M.PIN_MIN)
        bt.__av:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.__av:Hide()
        bt.nm:SetPoint("TOP", bt.dot, "BOTTOM", 0, -2)
        bt:SetScript("OnClick", function(self)
            local kind, p = self.__kind, self.__p
            if kind == "boss" and self.__dfView and self.__dfView.__mini then
                local MWm = ns.MapWindowModule
                if MWm and MWm.Restore then
                    MWm.Restore()
                    M.Select(p and p.en)
                    if MWm.Sync then MWm.Sync() end
                end
                return
            end
            W.arrive = nil
            if p and (kind == "prev" or kind == "next" or (kind == "entrance" and p.to)) then
                W.arrive = { from = M.CurFloorNum(), kind = kind, tox = p.tox, toy = p.toy }
            end
            local was = M.curLayer
            M.PinOnClick(self, true)
            W.Sync()
            local a = W.arrive
            if a and a.from and M.curLayer ~= was then
                M.ArriveAt(a.from, a.kind, a.tox, a.toy, self.__dfView or W.view)
            end
        end)
        bt:SetScript("OnEnter", function(self)
            M.PinOnEnter(self)
        end)
        bt:SetScript("OnLeave", function()
            M.PinOnLeave()
        end)
        bt:Hide()
        btns[i] = bt
    end
    view.pinBtns = btns
end

function W.Build()
    if W.view or not WorldMapFrame then return end
    local a = area()
    if not a then return end
    local view = CreateFrame("Frame", "DungeonsForeverMapOnWorld", WorldMapFrame)
    view:SetPoint("TOPLEFT", WorldMapFrame, "TOPLEFT")
    view:SetPoint("BOTTOMRIGHT", WorldMapFrame, "BOTTOMRIGHT")
    view:SetFrameStrata("HIGH")
    view:SetFrameLevel(VIEW_LEVEL)
    view:SetClipsChildren(true)
    view:Hide()
    W.view = view

    local block = CreateFrame("Button", nil, view)
    block:SetFrameLevel(view:GetFrameLevel() - 1)
    block:SetPoint("TOPLEFT", view, "TOPLEFT")
    block:SetSize(1, 1)
    block:RegisterForClicks("RightButtonUp")
    block:EnableMouseWheel(true)
    block:SetScript("OnMouseWheel", function(_, delta) W.ZoomWheel(delta) end)
    block:SetScript("OnMouseDown", function(self, button)
        if button ~= "LeftButton" then return end
        if not inStage() then return end
        W.movedAt = GetTime()
        M.SetHoverMouse(view.route, false)
        self.__lx, self.__ly = cursorUI()
        self:SetScript("OnUpdate", dragWorld)
    end)
    block:SetScript("OnMouseUp", function(self)
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
        M.SetHoverMouse(view.route, true)
    end)
    block:SetScript("OnHide", function(self)
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
        M.SetHoverMouse(view.route, true)
    end)
    block:SetScript("OnClick", function(_, button)
        if button == "RightButton" and W.ExitWorld then W.ExitWorld() end
    end)
    view.block = block

    local cover = CreateFrame("Button", nil, view)
    cover:SetHeight(NAV_H)
    cover:SetFrameLevel(view:GetFrameLevel() + 2)
    cover:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    local chl = cover:CreateTexture(nil, "OVERLAY")
    chl:SetAllPoints()
    chl:SetColorTexture(1, 1, 1, 0.10)
    chl:Hide()
    cover.hl = chl
    cover:SetScript("OnClick", function()
        if W.Active() then W.ExitWorld() end
    end)
    cover:SetScript("OnEnter", function(self)
        self.__hover = true
        if self.hl then self.hl:Show() end
    end)
    cover:SetScript("OnLeave", function(self)
        self.__hover = nil
        if self.hl then self.hl:Hide() end
    end)
    cover:Hide()
    view.crumbCover = cover

    view.bg = view:CreateTexture(nil, "BACKGROUND")
    view.bg:SetAllPoints()
    view.bg:SetColorTexture(0.05, 0.045, 0.03, 1)

    local stage = CreateFrame("Frame", nil, view)
    stage:SetSize(1, 1)
    stage:SetClipsChildren(true)
    stage:Show()
    view.stage = stage

    local canvas = CreateFrame("Frame", nil, stage)
    canvas:SetSize(1, 1)
    canvas:SetPoint("TOPLEFT", stage, "TOPLEFT", 0, 0)
    canvas:SetFrameLevel(stage:GetFrameLevel() + 1)
    view.canvas = canvas

    local tiles = {}
    for i = 1, M.N do
        local t = canvas:CreateTexture(nil, "ARTWORK")
        t:SetTexCoord(0, 1, 0, 1)
        t:Hide()
        tiles[i] = t
    end
    view.tiles = tiles

    local custom = canvas:CreateTexture(nil, "ARTWORK")
    custom:SetTexCoord(0, 1, 0, 1)
    custom:Hide()
    view.custom = custom

    local route = CreateFrame("Frame", nil, stage)
    route:SetSize(1, 1)
    route:SetPoint("TOPLEFT", stage, "TOPLEFT", 0, 0)
    route:SetFrameLevel(stage:GetFrameLevel() + 2)
    route:Hide()
    view.route = route
    view.routePool = {}
    view.routeUsed = 0

    local pins = CreateFrame("Frame", nil, stage)
    pins:SetSize(1, 1)
    pins:SetPoint("TOPLEFT", stage, "TOPLEFT", 0, 0)
    pins:SetFrameLevel(stage:GetFrameLevel() + 3)
    pins:Hide()
    view.pins = pins
    buildPinPool(view)

    local nav = navBar()
    local routeBtn = makeNativeBtn(UIParent, L["路线显示"], BTN_W, BTN_H)
    routeBtn:SetFrameStrata("HIGH")
    routeBtn:SetFrameLevel(950)
    routeBtn:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    routeBtn:SetScript("OnClick", routeToggle)
    routeBtn:Hide()
    ndBtn(routeBtn)
    view.routeBtn = routeBtn

    local pinBtn = makeNativeBtn(UIParent, L["图钉显示"], BTN_W, BTN_H)
    pinBtn:SetFrameStrata("HIGH")
    pinBtn:SetFrameLevel(950)
    pinBtn:SetScript("OnClick", function(self) M.ShowPinMenu(self) end)
    pinBtn:Hide()
    ndBtn(pinBtn)
    view.pinBtn = pinBtn

    ensureAreaBtn()

    local panel = CreateFrame("Frame", nil, view, "BackdropTemplate")
    panel:SetFrameStrata("TOOLTIP")
    panel:SetFrameLevel(100)
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(panel, 9, ns.hui.layer and ns.hui.layer.L1, "both", true, 1)
    else
        panel:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8X8",
            edgeFile = "Interface\\Buttons\\WHITE8X8",
            edgeSize = 1,
        })
        panel:SetBackdropColor(0, 0, 0, 0.6)
        panel:SetBackdropBorderColor(0.34, 0.28, 0.15, 0.85)
    end
    panel:Hide()
    view.floorPanel = panel

    local host = view
    local closeBtn = _G.WorldMapFrameCloseButton
    local cbH = (closeBtn and closeBtn:GetHeight()) or 24
    local taskBtn = CreateFrame("Button", nil, host, "BackdropTemplate")
    taskBtn:SetSize(60, cbH)
    taskBtn:SetFrameStrata("TOOLTIP")
    taskBtn:SetFrameLevel(100)
    local curFlags = FLAGS
    if ns.NDuiOn and ns.NDuiOn() then
        curFlags = ""
        ns.NDuiReskin(taskBtn)
    elseif not skinCloseStyle(taskBtn) then
        taskBtn:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8X8",
            edgeFile = "Interface\\Buttons\\WHITE8X8",
            edgeSize = 1,
        })
        taskBtn:SetBackdropColor(0.35, 0.05, 0.05, 1)
        taskBtn:SetBackdropBorderColor(0.55, 0.45, 0.2, 1)
    end
    local tfs = taskBtn:CreateFontString(nil, "OVERLAY")
    tfs:SetFont(fontPath(), 13, curFlags)
    tfs:SetTextColor(1, 0.82, 0)
    tfs:SetPoint("CENTER", taskBtn, "CENTER", 0, 0)
    taskBtn:SetFontString(tfs)
    taskBtn:SetText(L["任务"])
    taskBtn:SetScript("OnClick", function() W.ToggleSideTask() end)
    taskBtn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        local on = M.sideTask
        GameTooltip:AddLine(L[on and "首领" or "任务"], 1, 0.82, 0, true)
        GameTooltip:AddLine(L[on and "回到首领名单" or "显示任务日志"], 0.75, 0.75, 0.75, true)
        GameTooltip:Show()
    end)
    taskBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    taskBtn:Hide()
    view.taskBtn = taskBtn


    local btns = {}
    for i = 1, M.MAX_LAYERS do
        local bt = makeBtn(panel, "", FLOOR_MIN_W, FLOOR_H, 12)
        bt:SetFrameLevel(panel:GetFrameLevel() + 1)
        bt.__idx = i
        bt:SetScript("OnClick", onFloorClick)
        bt:Hide()
        btns[i] = bt
    end
    view.floorBtns = btns

    local q = questPanel()
    if q then
        local side = M.BuildSide(view, q:GetWidth(), q:GetHeight(), true, ns.hui and ns.hui.layer and ns.hui.layer.L0)
        side:SetFrameLevel(view:GetFrameLevel() + 4)
        view.side = side
    end
    skinChrome()
end

local lastSig, lastAW, lastAH, since

local function signature(id)
    local floor = id and floorNumAt(id, M.curLayer or 1)
    local vis, tot = 0, 0
    if id and floor then vis, tot = M.RouteVisibleCount(id, floor) end
    return table.concat({
        tostring(id), tostring(M.curLayer), tostring(M.detailEn),
        tostring(M.hideBossPins), tostring(M.hideQuestPins), tostring(M.hideNotePins),
        tostring(M.hideOtherPins),
        tostring(M.routeThin), tostring(M.routePalette), tostring(M.routeOff),
        tostring(vis), tostring(tot),
    }, "|")
end

local function autoPick()
    if inInstance() and not (ns.InstanceMapOn and ns.InstanceMapOn()) then
        W.pinned, W.pinnedMap = nil, nil
        return nil
    end
    if not inInstance() and euiMapSkin() then
        return nil
    end
    local id, why = W.Resolve()
    if not id then
        W.pinned, W.pinnedMap = nil, nil
        return nil
    end
    if W.pinned and W.pinned == id then return nil end
    W.pinned, W.pinnedMap = nil, nil
    return id, why
end

local function tick_()
    if not (WorldMapFrame and WorldMapFrame:IsShown()) then return end
    syncOpenWinBtn()
    leaSuppressPins()
    driveEntryPins()
    if not W.Active() then syncAreaBtn() end
end

local function mapPluginsOn()
    if type(ns.AddonLoaded) ~= "function" then return true end
    return (ns.AddonLoaded("Leatrix_Maps") or ns.AddonLoaded("OpenMap")) and true or false
end

local function onShow()
    if not W.hooked then return end
    if not enabled() then return end
    W.suppress = nil
end

local function watchUpdate(_, dt)
    since = (since or 0) + dt
    if since < 0.2 then return end
    since = 0
    tick_()
end

function W.Hook()
    if not enabled() then return end
    if W.hooked or not WorldMapFrame then return end
    W.hooked = true
    purgeLearn()
    W.__onShow = onShow
    local watch = CreateFrame("Frame", nil, WorldMapFrame)
    watch:SetAllPoints(WorldMapFrame)
    watch:SetScript("OnShow", onShow)
    watch:SetScript("OnUpdate", watchUpdate)
    W.watch = watch
    W.watchUpdate = watchUpdate
    attachPins()
    leaClickTakeover()
    if WorldMapFrame:IsShown() then onShow() end
end

function W.Dump()
    local info = instanceInfo()
    local mapID = worldMapID()
    local aw, ah = mapAreaSize()
    local id, why = W.Resolve()
    local lines = {
        "instanceName = " .. tostring(info and info.name),
        "instanceKind = " .. tostring(info and info.kind),
        "difficultyID = " .. tostring(info and info.diffIdx),
        "difficultyName = " .. tostring(info and info.diffName),
        "maxPlayers = " .. tostring(info and info.maxPlayers),
        "inInstance = " .. tostring(info and info.inInstance),
        "instanceID = " .. tostring(info and info.instID),
        "mapID = " .. tostring(mapID),
        "areaSize = " .. tostring(aw) .. " x " .. tostring(ah),
        "resolved = " .. tostring(id) .. "  (" .. tostring(why) .. ")",
        "mapModule = " .. tostring(M and "ok" or "missing"),
        "hasArt = " .. tostring(hasArt(id)),
        "layers = " .. tostring(M.LayersFor(id) and #M.LayersFor(id) or 0),
        "curLayer = " .. tostring(M.curLayer),
        "active = " .. tostring(W.Active()),
    }
    print("|cffe0c060DungeonsForever|r /dfmapdbg")
    for i = 1, #lines do print("  " .. lines[i]) end
    if info and info.instID and id then
        print("  |cff7fd0ff建议数据行|r:")
        print(string.format('    [%d] = "%s",', info.instID, id))
    end
    if mapID and id then
        print(string.format('    [%d] = "%s",', mapID, id))
    end
end

SLASH_DUNGEONSFOREVERMAPDBG1 = "/dfmapdbg"
SlashCmdList["DUNGEONSFOREVERMAPDBG"] = function()
    W.Dump()
end

local hookTries = 0
local function tryHook()
    if W.hooked then return end
    if not enabled() then return end
    if not WorldMapFrame then
        hookTries = hookTries + 1
        if hookTries <= 15 then C_Timer.After(1, tryHook) end
        return
    end
    W.Hook()
end

W.Render = {
    hasArt = hasArt,
    detailOf = detailOf,
    floorNumAt = floorNumAt,
    floorText = floorText,
    setPicked = setPicked,
    paintArt = paintArt,
    paintArea = paintArea,
    syncRoute = syncRoute,
    syncPins = syncPins,
    syncBar = syncBar,
    syncButtons = syncButtons,
    routeToggle = routeToggle,
    ndBtn = ndBtn,
    buildPinPool = buildPinPool,
}

tryHook()
