local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local EB = {}
ns.EasyBridge = EB

local API_NS = "EasyAuctionAPI"
local CACHE_TTL = 2
local LIST_LIMIT = 200

local floor, huge = math.floor, math.huge
local pairs, type, tonumber, tostring = pairs, type, tonumber, tostring
local match = string.match
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

local function API()
    local api = _G[API_NS]
    if type(api) ~= "table" or type(api.IsReady) ~= "function" then return nil end
    local ok, ready = pcall(api.IsReady)
    if not ok or ready ~= true then return nil end
    return api
end

local infoAt, infoValue

local function MarketInfo(api)
    if type(api.GetMarketInfo) ~= "function" then return nil end
    local now = Now()
    if infoValue and now - infoAt < CACHE_TTL then return infoValue end
    local ok, info = pcall(api.GetMarketInfo)
    if not ok or type(info) ~= "table" then info = nil end
    infoAt, infoValue = now, info
    return info
end

local function RecordOf(api, id)
    if type(api.GetRecord) ~= "function" then return nil end
    local ok, item = pcall(api.GetRecord, id)
    if ok and type(item) == "table" then return item, true end
    if type(api.ResolveItemKey) ~= "function" then return nil end
    local okKey, key = pcall(api.ResolveItemKey, id)
    if not okKey or type(key) ~= "string" or key == "" then return nil end
    ok, item = pcall(api.GetRecord, key)
    if ok and type(item) == "table" then return item, false end
    return nil
end

function EB.Record(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local api = API()
    if not api then return nil end
    local item, exact = RecordOf(api, id)
    if type(item) ~= "table" then return nil end
    local status = item.bookStatus
    local complete = exact == true and (status == "fresh" or status == "empty")
    local stamp
    if complete then
        stamp = Int(item.bookUpdated, 0) or Int(item.seen, 0) or Int(item.updated, 0)
    else
        stamp = Int(item.seen, 0) or Int(item.updated, 0) or Int(item.bookUpdated, 0)
    end
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
    local info = MarketInfo(api)
    local scope = type(info) == "table" and info.scope or nil
    return {
        q = quantity,
        p = Num(item.min, 1) or Num(item.rivalMin, 1) or Num(item.market, 1) or Num(item.price, 1),
        t = stamp,
        c = complete == true,
        ox = false,
        s = "client-auction-results",
        v = 1,
        mk = "ea:" .. tostring(scope),
        ob = "EasyAuction",
        method = "easyauction-api",
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
    local api = API()
    if not api then return false end
    local info = MarketInfo(api)
    if type(info) ~= "table" then return false end
    local count = Int(info.itemCount, 0)
    if count then return count > 0 end
    return true
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
    local api = API()
    if not api then return nil end
    local info = MarketInfo(api)
    if type(info) ~= "table" then return nil end
    local scope = tostring(info.scope)
    local now = Now()
    if snapshotValue and snapshotValue.marketKey == "ea:" .. scope
        and now - snapshotAt < CACHE_TTL then return snapshotValue end
    local stamp = Int(info.scanObservedAt, 0) or Int(info.updatedAt, 0)
    if not stamp or stamp <= 0 then return nil end
    local now2 = Now()
    local expired = stamp > now2 or (now2 - stamp) > MaxAge()
    local value = {
        status = expired and "expired" or "available",
        observedAt = stamp,
        marketKey = "ea:" .. scope,
        expiresAt = stamp + MaxAge(),
        source = "easyauction",
    }
    snapshotAt, snapshotValue = now, value
    return value
end

function EB.AuctionCut()
    local api = API()
    if not api or type(api.GetSettings) ~= "function" then return nil end
    local ok, settings = pcall(api.GetSettings)
    if not ok or type(settings) ~= "table" then return nil end
    local cut = Num(settings.auctionCut, 0)
    if not cut or cut > 1 then return nil end
    return cut * 100
end

function EB.Invalidate()
    infoAt, infoValue = nil, nil
    snapshotAt, snapshotValue = nil, nil
end

local function ListAPI()
    local api = API()
    if type(api) ~= "table" then return nil end
    if type(api.GetShoppingLists) ~= "function" or type(api.CreateShoppingList) ~= "function"
        or type(api.SetShoppingListItem) ~= "function" then
        return nil
    end
    return api
end

function EB.CanLists()
    local api = ListAPI()
    if not api then return false end
    local ok, lists = pcall(api.GetShoppingLists)
    return ok and type(lists) == "table"
end

local function FindList(api, name)
    local ok, lists = pcall(api.GetShoppingLists)
    if not ok or type(lists) ~= "table" then return nil end
    local temporary
    for index = 1, #lists do
        local list = lists[index]
        if type(list) == "table" and list.name == name and Int(list.id, 1) then
            if not list.temporary then return list, false end
            if not temporary then temporary = list end
        end
    end
    return temporary, true
end

function EB.ReplaceList(name, items)
    local api = ListAPI()
    if not api then return false, "storeUnavailable" end
    if type(name) ~= "string" or name == "" then return false, "badName" end
    if type(items) ~= "table" or #items == 0 then return false, "empty" end
    local entries = {}
    for index = 1, #items do
        local entry = items[index]
        if type(entry) == "table" then
            local id = Int(entry.id, 1)
            local need = Int(entry.need, 1)
            if id and need then entries[#entries + 1] = { id = id, need = need, name = entry.name } end
        end
    end
    if #entries == 0 then return false, "noItem" end
    local list, temporary = FindList(api, name)
    if list and temporary then
        if type(api.DeleteTemporaryShoppingList) == "function" then
            pcall(api.DeleteTemporaryShoppingList, list.id)
        end
        list = nil
    end
    if list then
        local wanted = {}
        for index = 1, #entries do wanted[entries[index].id] = true end
        if type(list.items) == "table" then
            for key in pairs(list.items) do
                local id = tonumber(match(key, "^(%d+):"))
                if id and not wanted[id] then pcall(api.SetShoppingListItem, list.id, key, 0) end
            end
        end
    else
        local ok, id = pcall(api.CreateShoppingList, name)
        if not ok or not Int(id, 1) then return false, "createFailed" end
        list = { id = id }
    end
    local written = 0
    for index = 1, #entries do
        local entry = entries[index]
        local entryName = type(entry.name) == "string" and entry.name or nil
        local ok = pcall(api.SetShoppingListItem, list.id, entry.id, entry.need, nil, entryName)
        if ok then written = written + 1 end
    end
    if written == 0 then return false, "noItem" end
    return true, nil, written
end

local function EscapeName(text)
    if type(text) ~= "string" or text == "" then return nil end
    if not match(text, "[^%z\1-\31\127]") then return nil end
    return (text:gsub("[%%|%c]", function(value) return string.format("%%%02X", string.byte(value)) end))
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
