local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local EB = {}
ns.EasyBridge = EB

local DB_NAME = "EasyAuctionDB12"
local CACHE_TTL = 2
local INDEX_TTL = 30

local floor, huge = math.floor, math.huge
local pairs, next, type, tonumber, tostring = pairs, next, type, tonumber, tostring
local match, sub = string.match, string.sub
local time = time

local function Now()
    return (type(time) == "function") and time() or 0
end

local function Int(value, minimum)
    value = tonumber(value)
    if not value or value ~= value or value == huge or value == -huge then return nil end
    if value < minimum or value ~= floor(value) then return nil end
    return value
end

local function Num(value, minimum)
    value = tonumber(value)
    if not value or value ~= value or value == huge or value == -huge then return nil end
    if value < minimum then return nil end
    return value
end

local function MaxAge()
    local ra = ns.ProfRouteAuto
    if ra and ra.MaxAuctionSupplyAgeSeconds then
        local ok, value = pcall(ra.MaxAuctionSupplyAgeSeconds)
        if ok and type(value) == "number" and value > 0 then return value end
    end
    return 172800
end

local function Database()
    local db = _G[DB_NAME]
    if type(db) ~= "table" or type(db.scopes) ~= "table" then return nil end
    return db
end

local function ScopePrefix()
    local region = GetCurrentRegion and GetCurrentRegion() or nil
    local realm = GetRealmName and GetRealmName() or nil
    if type(region) ~= "number" or region <= 0 then return nil end
    if type(realm) ~= "string" or realm == "" then return nil end
    local faction = UnitFactionGroup and UnitFactionGroup("player") or nil
    if type(faction) ~= "string" or faction == "" then faction = "Neutral" end
    return tostring(region) .. ":" .. realm .. ":" .. faction
end

local function SelectMarket()
    local db = Database()
    if not db then return nil end
    local prefix = ScopePrefix()
    if not prefix then return nil end
    local size, head = #prefix, prefix .. ":"
    local best, bestKey, bestStamp, bestExact
    for key, market in pairs(db.scopes) do
        if type(key) == "string" and type(market) == "table" then
            local exact = key == prefix
            if exact or sub(key, 1, size + 1) == head then
                local stamp = Int(market.lastFullScanAt, 0) or 0
                if not best or stamp > bestStamp
                    or (stamp == bestStamp and exact and not bestExact) then
                    best, bestKey, bestStamp, bestExact = market, key, stamp, exact
                end
            end
        end
    end
    if best then return db, best, bestKey end
    return nil
end

local cacheAt, cacheDB, cacheMarket, cacheScope

local function Market()
    local now = Now()
    if cacheMarket and now - cacheAt < CACHE_TTL then
        return cacheDB, cacheMarket, cacheScope
    end
    local db, market, scope = SelectMarket()
    cacheAt, cacheDB, cacheMarket, cacheScope = now, db, market, scope
    return db, market, scope
end

local indexMarket, indexMap, indexAt

local function Index(market)
    local now = Now()
    if indexMarket == market and indexMap and now - indexAt < INDEX_TTL then return indexMap end
    local map = {}
    local items = market.items
    if type(items) == "table" then
        for key, item in pairs(items) do
            if type(key) == "string" and type(item) == "table" then
                local id = tonumber(match(key, "^(%d+):"))
                if id then
                    local list = map[id]
                    if not list then list = {}; map[id] = list end
                    list[#list + 1] = item
                end
            end
        end
    end
    indexMarket, indexMap, indexAt = market, map, now
    return map
end

local function FreshStamp(item)
    return Int(item.bookUpdated, 0) or Int(item.seen, 0) or Int(item.updated, 0)
end

local function ObservedStamp(item)
    return Int(item.seen, 0) or Int(item.updated, 0) or Int(item.bookUpdated, 0)
end

local function ItemFor(market, id)
    local items = market.items
    if type(items) ~= "table" then return nil, false end
    local exact = items[id .. ":0:0:0"]
    if type(exact) == "table" then return exact, true end
    local list = Index(market)[id]
    if type(list) ~= "table" or #list == 0 then return nil, false end
    local best, bestStamp
    for index = 1, #list do
        local item = list[index]
        local stamp = FreshStamp(item)
        if item.bookStatus == "fresh" and stamp and (not bestStamp or stamp > bestStamp) then
            best, bestStamp = item, stamp
        end
    end
    if best then return best, false end
    best, bestStamp = nil, nil
    for index = 1, #list do
        local item = list[index]
        local stamp = ObservedStamp(item)
        if stamp and (not bestStamp or stamp > bestStamp) then best, bestStamp = item, stamp end
    end
    return best, false
end

function EB.Record(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local _, market, scope = Market()
    if type(market) ~= "table" then return nil end
    local item, exact = ItemFor(market, id)
    if type(item) ~= "table" then return nil end
    local status = item.bookStatus
    local complete = exact == true and (status == "fresh" or status == "empty")
    local stamp = complete and FreshStamp(item) or ObservedStamp(item)
    if not stamp or stamp <= 0 then return nil end
    local quantity
    if status == "empty" and exact then
        quantity = 0
    elseif complete then
        quantity = Int(item.bookQuantity, 0)
        if quantity == nil then
            quantity = Int(item.quantity, 0)
            complete = false
        end
    else
        quantity = Int(item.quantity, 0) or Int(item.bookQuantity, 0)
    end
    if quantity == nil then return nil end
    return {
        q = quantity,
        p = Num(item.min, 1) or Num(item.rivalMin, 1) or Num(item.market, 1) or Num(item.last, 1),
        t = stamp,
        c = complete == true,
        ox = false,
        s = "client-auction-results",
        v = 1,
        mk = "ea:" .. tostring(scope),
        ob = "EasyAuction",
        method = "easyauction-db",
        ea = true,
    }
end

function EB.Status(id)
    local rec = EB.Record(id)
    if type(rec) ~= "table" then return nil end
    if rec.c ~= true then return "incomplete" end
    local now = Now()
    if rec.t > now then return "expired" end
    if now - rec.t > MaxAge() then return "expired" end
    return "verified"
end

function EB.Available()
    local ok, _, market = pcall(Market)
    if not ok or type(market) ~= "table" then return false end
    local items = market.items
    return type(items) == "table" and next(items) ~= nil
end

function EB.Price(id)
    local rec = EB.Record(id)
    return rec and rec.p or nil
end

function EB.ObservedAt(id)
    local rec = EB.Record(id)
    return rec and rec.t or nil
end

local snapshotAt, snapshotValue

function EB.Snapshot()
    local _, market, scope = Market()
    if type(market) ~= "table" then return nil end
    local now = Now()
    if snapshotValue and snapshotValue.marketKey == "ea:" .. tostring(scope)
        and now - snapshotAt < CACHE_TTL then return snapshotValue end
    local stamp = Int(market.lastFullScanAt, 0)
    if not stamp then
        for _, item in pairs(market.items or {}) do
            if type(item) == "table" and item.bookStatus == "fresh" then
                local value = FreshStamp(item)
                if value and value > 0 and (not stamp or value > stamp) then stamp = value end
            end
        end
    end
    if not stamp or stamp <= 0 then return nil end
    local now2 = Now()
    local expired = stamp > now2 or (now2 - stamp) > MaxAge()
    local value = {
        status = expired and "expired" or "available",
        observedAt = stamp,
        marketKey = "ea:" .. tostring(scope),
        expiresAt = stamp + MaxAge(),
        source = "easyauction",
    }
    snapshotAt, snapshotValue = now, value
    return value
end

function EB.AuctionCut()
    local db = Database()
    if not db then return nil end
    local settings = db.settings
    local prof = type(settings) == "table" and settings.professions
    local cut = type(prof) == "table" and Num(prof.auctionCut, 0) or nil
    if not cut or cut > 1 then return nil end
    return cut * 100
end

function EB.Invalidate()
    cacheAt, cacheDB, cacheMarket, cacheScope = nil, nil, nil, nil
    snapshotAt, snapshotValue = nil, nil
end

local LIST_NS = "EasyAuction12"
local LIST_LIMIT = 200

local function ListStore()
    local root = _G[LIST_NS]
    local store = type(root) == "table" and root.Store or nil
    if type(store) ~= "table" then return nil end
    if type(store.GetLists) ~= "function" or type(store.CreateList) ~= "function"
        or type(store.DeleteList) ~= "function" or type(store.SetListItem) ~= "function" then
        return nil
    end
    return root, store
end

function EB.CanLists()
    local _, store = ListStore()
    if not store then return false end
    local ok, lists = pcall(store.GetLists)
    return ok and type(lists) == "table"
end

local function FindList(store, name)
    local ok, lists = pcall(store.GetLists)
    if not ok or type(lists) ~= "table" then return nil end
    for index = 1, #lists do
        local list = lists[index]
        if type(list) == "table" and list.name == name then return list end
    end
    return nil
end

local function RefreshLists(root)
    local ui = type(root) == "table" and root.UI or nil
    if type(ui) == "table" and type(ui.Refresh) == "function" then pcall(ui.Refresh) end
end

local function EscapeName(text)
    if type(text) ~= "string" or text == "" then return nil end
    if not match(text, "[^%z\1-\31\127]") then return nil end
    return (text:gsub("[%%|%c]", function(value) return string.format("%%%02X", string.byte(value)) end))
end

function EB.ReplaceList(name, items)
    local root, store = ListStore()
    if not store then return false, "storeUnavailable" end
    if type(name) ~= "string" or name == "" then return false, "badName" end
    if type(items) ~= "table" or #items == 0 then return false, "empty" end
    local existing = FindList(store, name)
    if existing then pcall(store.DeleteList, existing.id) end
    local made, list = pcall(store.CreateList, name)
    if not made or type(list) ~= "table" then return false, "createFailed" end
    local written = 0
    for index = 1, #items do
        local entry = items[index]
        if type(entry) == "table" then
            local id = Int(entry.id, 1)
            local need = Int(entry.need, 1)
            if id and need then
                local key = { itemID = id, itemLevel = 0, itemSuffix = 0, battlePetSpeciesID = 0 }
                local ok = pcall(store.SetListItem, list.id, key, entry.name, need)
                if ok then written = written + 1 end
            end
        end
    end
    RefreshLists(root)
    if written == 0 then
        pcall(store.DeleteList, list.id)
        return false, "noItem"
    end
    return true, nil, written
end

function EB.ShareText(name, items)
    local safe = EscapeName(name)
    if not safe or type(items) ~= "table" then return nil end
    local lines = { "EA12|1|" .. safe }
    for index = 1, #items do
        local entry = items[index]
        if type(entry) == "table" then
            local id = Int(entry.id, 1)
            local need = Int(entry.need, 1)
            local itemName = EscapeName(entry.name)
            if id and need and itemName then
                lines[#lines + 1] = string.format("%d:0:0:0|%d|-|%s", id, need, itemName)
                if #lines > LIST_LIMIT + 1 then return nil end
            end
        end
    end
    if #lines <= 1 then return nil end
    return table.concat(lines, "\n")
end
