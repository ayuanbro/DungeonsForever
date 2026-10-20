-- =============================================================================
-- DungeonsForever · 购物清单导出桥接
-- 把插件内购物清单经拍卖行插件的官方公开 API 推送为其购物清单；
-- 未安装时降级为可复制的导入串弹窗。只对无限服加载。
-- =============================================================================

local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local AB = {}
ns.AuctionBridge = AB

local CALLER = "DungeonsForever"

local format = string.format

-- 聊天框反馈（浅金色正文，与本插件其他提示同风格）
local function Say(msg)
    local frame = DEFAULT_CHAT_FRAME
    if frame and frame.AddMessage then
        frame:AddMessage("|cffffd100" .. msg .. "|r")
    end
end

-- v341 的 API 在文件加载时就存在，价格数据库要等 PLAYER_LOGIN；
-- 不能把初始化中的 nil 报价缓存为「未安装」或「没有行情」。
local function AddonMetadata(addon)
    local api = C_AddOns and C_AddOns.GetAddOnMetadata or GetAddOnMetadata
    if type(api) == "function" then
        local ok, version = pcall(api, addon or "Auctionator", "Version")
        if ok then return version end
    end
end

function AB.Status()
    local a = type(Auctionator) == "table" and Auctionator or nil
    local api = a and type(a.API) == "table" and type(a.API.v1) == "table" and a.API.v1 or nil
    local version = AddonMetadata()
    local installed = a ~= nil or version ~= nil
    local disabled = false
    if installed then
        local name = type(UnitName) == "function" and UnitName("player") or nil
        local fn = C_AddOns and C_AddOns.GetAddOnEnableState
        local ok, enabled
        if type(fn) == "function" then ok, enabled = pcall(fn, "Auctionator", name)
        elseif type(GetAddOnEnableState) == "function" then ok, enabled = pcall(GetAddOnEnableState, name, "Auctionator") end
        disabled = ok and enabled == 0 or false
    end
    -- Current Auctionator exposes State.Loaded only after Database has been built.
    -- Older integrations without State/Database retain their public API contract.
    local initialized = a and (type(a.Database) == "table" or
        (type(a.State) == "table" and a.State.Loaded == true) or
        (a.State == nil and a.Database == nil))
    local priceReady = initialized and api and type(api.GetAuctionPriceByItemID) == "function" or false
    local shoppingReady = api and type(api.CreateShoppingList) == "function" and
        (a.Shopping == nil or type(a.Shopping.ListManager) == "table") or false
    return {installed = installed, version = version or (a and a.State and a.State.CurrentVersion),
        priceReady = not not priceReady, shoppingReady = not not shoppingReady,
        state = priceReady and "ready" or (disabled and "disabled" or (installed and "loading" or "missing"))}
end

function AB.Available() return AB.Status().shoppingReady end
function AB.PriceReady() return AB.Status().priceReady end

local watchers, lastStatus, registeredAPI = {}, nil, nil
local queued, pendingReason, retries = false, nil, 0
local CaptureLegacy, InstallSupplyHooks
function AB.OnChanged(fn) if type(fn) == "function" then watchers[#watchers + 1] = fn end end

local function Notify(status, reason)
    -- Readiness/reload is not new market evidence and must not stale saved routes.
    if (reason == "prices" or reason == "supply") and ns.ProfRouteAuto and ns.ProfRouteAuto.Invalidate then
        ns.ProfRouteAuto.Invalidate(reason)
    end
    for _, fn in ipairs(watchers) do pcall(fn, status, reason) end
end

local function DeferredRefresh(reason)
    if reason == "prices" or reason == "supply" or pendingReason == nil then pendingReason = reason end
    if queued then return end
    queued = true
    local function run()
        local why = pendingReason
        queued, pendingReason = false, nil
        AB.Refresh(why)
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, run) else run() end
end

function AB.Refresh(reason)
    if InstallSupplyHooks then InstallSupplyHooks() end
    local status = AB.Status()
    local fingerprint = table.concat({status.state, tostring(status.priceReady), tostring(status.shoppingReady), tostring(status.version)}, ":")
    local changed = lastStatus ~= fingerprint
    lastStatus = fingerprint
    local a = type(Auctionator) == "table" and Auctionator or nil
    local api = a and a.API and a.API.v1
    -- Use Auctionator's public price-change subscription, when this AH variant
    -- provides it. Secure post-hooks observe quantities separately; we never
    -- write to Auctionator's files or database.
    if api and type(api.RegisterForDBUpdate) == "function" and registeredAPI ~= api.RegisterForDBUpdate then
        local fn = api.RegisterForDBUpdate
        local ok = pcall(fn, CALLER, function()
            -- Full scan temporarily unregisters other list-update listeners;
            -- this public callback runs while the full client list is readable.
            if CaptureLegacy then CaptureLegacy(true) end
            DeferredRefresh("prices")
        end)
        if ok then registeredAPI = fn end
    end
    if changed or reason == "prices" or reason == "supply" then Notify(status, reason or "readiness") end
    if status.installed and status.state == "loading" and retries < 20 and C_Timer and type(C_Timer.After) == "function" then
        retries = retries + 1
        C_Timer.After(0.25, function() AB.Refresh("readiness") end)
    end
    return status
end

-- Latest observations belong to our SavedVariables, never Auctionator's daily
-- maximum. No code here requests auction searches.
local supply, supplyRevision, wholeMarket = {}, 0, nil
local legacyQuery, hookedLegacy, captureSerial = nil, false, 0
local SUPPLY_VERSION, OLD_AFTER = 2, 2 * 86400
local hookedDatabases = setmetatable({}, {__mode = "k"})
local databaseHookState, databaseHookError = "waiting", nil
local function Now()
    if type(time) == "function" then return time() end
    if type(GetServerTime) == "function" then return GetServerTime() end
    return 0
end
local function Quantity(value)
    return type(value) == "number" and value >= 0 and value < math.huge and value == math.floor(value)
end
local function Store()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local root = DungeonsForeverDB.auctionSupply
    if type(root) ~= "table" or root.version ~= SUPPLY_VERSION then
        -- Uptime timestamps from old versions cannot survive another login.
        root = {version = SUPPLY_VERSION, sequence = 0, markets = {}}
        DungeonsForeverDB.auctionSupply = root
    end
    root.markets = type(root.markets) == "table" and root.markets or {}
    return root
end
local function NextSequence()
    local root = Store()
    root.sequence = (tonumber(root.sequence) or 0) + 1
    supplyRevision = root.sequence
    return root.sequence
end
local function MarketKey()
    local a = type(Auctionator) == "table" and Auctionator
    local fn = a and a.Variables and a.Variables.GetConnectedRealmRoot
    local realm
    if type(fn) == "function" then local ok, key = pcall(fn); if ok and type(key) == "string" and key ~= "" then realm = key end end
    if not realm then
        realm = (type(GetRealmName) == "function" and GetRealmName() or "?") .. " " ..
            (type(UnitFactionGroup) == "function" and UnitFactionGroup("player") or "?")
    end
    local build = type(GetBuildInfo) == "function" and select(4, GetBuildInfo()) or "?"
    return tostring(build) .. ":" .. realm
end
local function CharacterKey()
    local guid = type(UnitGUID) == "function" and UnitGUID("player")
    if guid then return guid end
    local name = type(UnitName) == "function" and UnitName("player") or "?"
    return name .. "-" .. (type(GetRealmName) == "function" and GetRealmName() or "?")
end
local function Market()
    local root, key = Store(), MarketKey()
    local market = root.markets[key]
    if type(market) ~= "table" then market = {items = {}, characters = {}, prices = {}}; root.markets[key] = market end
    market.items = type(market.items) == "table" and market.items or {}
    market.characters = type(market.characters) == "table" and market.characters or {}
    market.prices = type(market.prices) == "table" and market.prices or {}
    local char = CharacterKey()
    if type(market.characters[char]) ~= "table" then market.characters[char] = {items = {}} end
    if type(market.characters[char].items) ~= "table" then market.characters[char].items = {} end
    return market, market.characters[char], key
end
local function Fresh(e)
    -- Age is presentation metadata, never an availability/deletion policy.
    return type(e) == "table" and e.schemaVersion == SUPPLY_VERSION and Quantity(e.quantity)
        and type(e.observedAt) == "number" and e.observedAt > 0
end
local function ItemID(link)
    return type(link) == "string" and tonumber(link:match("item:(%d+)")) or nil
end
local function ItemName(id)
    local fn = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(fn) == "function" then local ok, name = pcall(fn, id); if ok then return name end end
end
local function Own(owner)
    if owner == "player" then return true end
    if type(owner) ~= "string" then return false end
    local name, realm
    if type(UnitFullName) == "function" then name, realm = UnitFullName("player") end
    if not name and type(UnitName) == "function" then name, realm = UnitName("player") end
    if owner == name then return true end
    return realm and realm ~= "" and owner == name .. "-" .. realm or false
end
local function CopySupply(e, compact)
    local out = {}; for k, v in pairs(e) do if k ~= "lots" then out[k] = v end end
    if not compact then
        out.lots = {}
        for i, lot in ipairs(e.lots or {}) do
            local copy = {}; for k, v in pairs(lot) do copy[k] = v end; out.lots[i] = copy
        end
    end
    return out
end
local function PublishSupply(entries, full, batch, coverage)
    local observedAt, revision = Now(), NextSequence()
    local _, character, key = Market()
    batch = batch or revision
    local serial, cursor, items = captureSerial, nil, full and {} or nil
    local function chunk()
        if serial ~= captureSerial or key ~= MarketKey() then return end
        local processed = 0
        local id, e = next(entries, cursor)
        while id do
            cursor = id
            if coverage ~= nil then e.complete = coverage end
            -- Partial owned/bid-only rows cannot prove sold out. Don't remove
            -- keys during next() traversal; simply decline to publish them.
            if e.quantity > 0 or e.complete then
                e.observedAt, e.source, e.revision = observedAt, "client-auction-results", revision
                e.schemaVersion, e.market, e.batch, e.ownerExcluded = SUPPLY_VERSION, key, batch, true
                supply[id] = e
                character.items[id] = CopySupply(e, true)
                if items then items[id] = true end
            end
            processed = processed + 1
            id, e = next(entries, cursor)
            if id and (full or coverage ~= nil) and processed >= 150 and C_Timer and type(C_Timer.After) == "function" then
                DeferredRefresh("supply")
                C_Timer.After(0, chunk)
                return
            end
        end
        if full then
            -- Only a completely published scan may establish absent IDs zero.
            wholeMarket = {observedAt = observedAt, items = items, revision = revision,
                market = key, batch = batch, schemaVersion = SUPPLY_VERSION}
            character.full = wholeMarket
        end
        DeferredRefresh("supply")
    end
    chunk()
end
local function ClearSupply()
    -- Starting a new session resets query/lot state, not saved observations.
    supply, wholeMarket, legacyQuery = {}, nil, nil
    captureSerial = captureSerial + 1
end
function AB.SupplyRevision() return tonumber(Store().sequence) or supplyRevision end
function AB.GetAuctionSupply(id, compact)
    id = tonumber(id); if not Quantity(id) or id <= 0 then return nil end
    local market, character, key = Market()
    local e, shared = character.items[id], market.items[id]
    if not Fresh(e) or (Fresh(shared) and (shared.revision or 0) > (e.revision or 0)
        and not (shared.batch == e.batch and shared.source == "auctionator-update"
            and e.rawQuantity == shared.quantity)) then e = shared end
    local full = character.full
    if type(full) == "table" and full.schemaVersion == SUPPLY_VERSION and full.market == key
        and type(full.observedAt) == "number" and full.observedAt > 0 and type(full.items) == "table"
        and not full.items[id] and (not Fresh(e) or (e.revision or 0) <= full.revision) then
        e = {quantity = 0, complete = true, ownerExcluded = true, schemaVersion = SUPPLY_VERSION,
            observedAt = full.observedAt, source = "client-auction-results", revision = full.revision,
            market = key, batch = full.batch}
    end
    if not Fresh(e) then return nil end
    local live = supply[id]
    if not compact and Fresh(live) and live.revision == e.revision and live.market == key then e = live end
    local out = CopySupply(e, compact)
    out.old = Now() - e.observedAt > OLD_AFTER
    return out
end
function AB.GetAuctionPriceObservedAt(id)
    local market = Market()
    local p = market.prices[tonumber(id)]
    return type(p) == "table" and p.observedAt or nil
end
function AB.GetAuctionSupplyHistory(id)
    id = tonumber(id); if not Quantity(id) or id <= 0 then return end
    local a = type(Auctionator) == "table" and Auctionator
    local db = a and a.Database
    if type(db) ~= "table" or type(db.GetPriceHistory) ~= "function" then return end
    local ok, rows = pcall(db.GetPriceHistory, db, tostring(id))
    if not ok or type(rows) ~= "table" then return end
    local best, newest
    for _, row in ipairs(rows) do
        if type(row) == "table" then
            local day = tonumber(row.rawDay)
            if Quantity(row.available) and Quantity(day) and (not newest or day > newest) then best, newest = row, day end
        end
    end
    if not best then return end
    local zero = a.Constants and a.Constants.SCAN_DAY_0
    return {quantity = best.available, observedAt = type(zero) == "number" and zero + newest * 86400 or nil,
        observedDay = newest, source = "auctionator-daily-maximum"}
end
local function AddLot(entries, id, quantity, buyout, extra)
    if not id or id <= 0 or not quantity or quantity <= 0 or not buyout or buyout <= 0 then return end
    local e = entries[id]
    if not e then e = {quantity = 0, lots = {}, complete = false}; entries[id] = e end
    local lot = {quantity = quantity, buyout = buyout, unitPrice = buyout / quantity}
    for k, v in pairs(extra or {}) do lot[k] = v end
    e.quantity = e.quantity + quantity; e.lots[#e.lots + 1] = lot
    if not e.observedPrice or lot.unitPrice < e.observedPrice then e.observedPrice = lot.unitPrice end
end
local function Unfiltered(q)
    return not q.usable and (q.min == nil or q.min == 0) and
        (q.max == nil or q.max == 0) and (q.quality == nil or q.quality == -1) and
        (q.filters == nil or (type(q.filters) == "table" and next(q.filters) == nil))
end
local function QueryFingerprint(v)
    if type(v) ~= "table" then return tostring(v) end
    local out = {}; for k, value in pairs(v) do out[#out + 1] = tostring(k) .. "=" .. QueryFingerprint(value) end
    table.sort(out); return table.concat(out, ",")
end
local function ObserveQuery(name, min, max, page, usable, quality, getAll, exact, filters)
    local q = {name = name or "", min = min, max = max, page = tonumber(page) or 0,
        usable = usable, quality = quality, all = getAll, exact = exact, filters = filters}
    q.fingerprint = QueryFingerprint({q.name, tostring(min), tostring(max), tostring(usable), tostring(quality), tostring(getAll), tostring(exact), filters or {}})
    if q.page > 0 and legacyQuery and q.fingerprint == legacyQuery.fingerprint then
        q.pages, q.ids, q.batch = legacyQuery.pages, legacyQuery.ids, legacyQuery.batch
    else q.pages, q.ids, q.batch = {}, {}, NextSequence() end
    legacyQuery = q; captureSerial = captureSerial + 1
end
local function CommitLegacy(q, page, count, total, entries, valid)
    if q ~= legacyQuery then return end
    q.pages[page] = {count = count, entries = entries, valid = valid}
    local merged, rows, allValid = {}, 0, true
    if q.all then
        -- getAll is one client result list already collected in chunks.
        -- Reuse it instead of synchronously copying every auction again.
        merged, rows, allValid = entries, count, valid
    else
        for _, p in pairs(q.pages) do
            rows = rows + p.count; allValid = allValid and p.valid
            for id, e in pairs(p.entries) do
                q.ids[id] = true
                if not merged[id] then merged[id] = {quantity = 0, lots = {}, complete = false, rawQuantity = 0} end
                for _, lot in ipairs(e.lots) do AddLot(merged, id, lot.quantity, lot.buyout, {stack = true}) end
                merged[id].rawQuantity = merged[id].rawQuantity + (e.rawQuantity or 0)
                if e.rawPrice and (not merged[id].rawPrice or e.rawPrice < merged[id].rawPrice) then merged[id].rawPrice = e.rawPrice end
            end
        end
    end
    local complete = allValid and total ~= nil and rows >= total and Unfiltered(q)
    if not q.all then
        -- A page gap cannot be filled by repeated updates of another page.
        for i = 0, page do if not q.pages[i] then complete = false end end
    end
    if not q.all then
        for id in pairs(q.ids) do
            merged[id] = merged[id] or {quantity = 0, lots = {}}
            merged[id].complete = complete
        end
    end
    if complete and q.exact and q.name ~= "" then
        -- A completed empty exact search can prove zero only when the client
        -- can resolve that name to an item ID. Unsearched IDs remain unknown.
        local fn = C_Item and C_Item.GetItemInfo or GetItemInfo
        if type(fn) == "function" then
            local ok, name, link = pcall(fn, q.name); local id = ok and ItemID(link)
            if id and name == q.name then merged[id] = merged[id] or {quantity = 0, lots = {}, complete = true} end
        end
        -- q.ids already covers every identity seen in this query's pages.
        -- Do not enumerate the full market and load thousands of item names
        -- merely to establish that one exact query is empty.
        for id in pairs(q.ids) do
            if ItemName(id) == q.name and not merged[id] then merged[id] = {quantity = 0, lots = {}, complete = true} end
        end
    end
    -- A filtered query cannot invalidate an older complete observation.
    if not Unfiltered(q) then
        for id in pairs(merged) do if Fresh(supply[id]) and supply[id].complete then merged[id] = nil end end
    end
    if q.all and complete then q.fullCaptured = true end
    if next(merged) or (complete and q.name == "") then
        local coverage
        if q.all then coverage = complete end
        PublishSupply(merged, complete and q.name == "", q.batch, coverage)
    end
end
CaptureLegacy = function(fullOnly)
    local q = legacyQuery
    if not q or (fullOnly and (not q.all or q.fullCaptured))
        or type(GetNumAuctionItems) ~= "function" or type(GetAuctionItemInfo) ~= "function" then return end
    local ok, count, total = pcall(GetNumAuctionItems, "list")
    if not ok or type(count) ~= "number" then return end
    local first = 1
    if q.all and count > 0 then
        -- Installed Auctionator's normal scan loops 1..count, whereas its
        -- getAll reader starts at zero. Detect the actual client's origin;
        -- unavailable / invalid index zero keeps the regular one-based range.
        local function ValidIndex(i)
            local got, info = pcall(function() return {GetAuctionItemInfo("list", i)} end)
            return got and info[1] and tonumber(info[3]) and tonumber(info[3]) > 0 and
                tonumber(info[17]) and tonumber(info[17]) > 0
        end
        -- Some implementations accept zero as an alias of the first row;
        -- an equally valid row at count identifies the one-based range.
        if ValidIndex(0) and not ValidIndex(count) then first = 0 end
    end
    local last = first + count - 1
    captureSerial = captureSerial + 1; local serial, index, entries, valid = captureSerial, first, {}, true
    local function chunk()
        if serial ~= captureSerial or legacyQuery ~= q then return end
        local stop = math.min(last, index + 149)
        for i = index, stop do
            local info = {GetAuctionItemInfo("list", i)}
            local id = tonumber(info[17])
            if not id and type(GetAuctionItemLink) == "function" then id = ItemID(GetAuctionItemLink("list", i)) end
            if not id or not info[1] or info[14] == nil then valid = false
            elseif not Own(info[14]) and info[16] ~= 1 then
                AddLot(entries, id, tonumber(info[3]), tonumber(info[10]), {stack = true})
            end
            -- Known rows without buyout or owned by the player still identify
            -- the searched item, and can establish zero buyable quantity.
            if id and not entries[id] then entries[id] = {quantity = 0, lots = {}, complete = false} end
            if id and Quantity(tonumber(info[3])) and tonumber(info[10]) and tonumber(info[10]) > 0 then
                entries[id].rawQuantity = (entries[id].rawQuantity or 0) + tonumber(info[3])
                if tonumber(info[3]) > 0 then
                    local rawPrice = math.ceil(tonumber(info[10]) / tonumber(info[3]))
                    if not entries[id].rawPrice or rawPrice < entries[id].rawPrice then entries[id].rawPrice = rawPrice end
                end
            end
        end
        index = stop + 1
        if index <= last and C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0, chunk)
        elseif index <= last then chunk()
        else CommitLegacy(q, q.page, count, tonumber(total), entries, valid) end
    end
    chunk()
end
local function CaptureModern(event, key)
    local ah = C_AuctionHouse
    if type(ah) ~= "table" then return end
    local commodity = event == "COMMODITY_SEARCH_RESULTS_UPDATED"
    local id = commodity and tonumber(key) or (type(key) == "table" and tonumber(key.itemID))
    if not id then return end
    local countFn = commodity and ah.GetNumCommoditySearchResults or ah.GetNumItemSearchResults
    local resultFn = commodity and ah.GetCommoditySearchResultInfo or ah.GetItemSearchResultInfo
    local fullFn = commodity and ah.HasFullCommoditySearchResults or ah.HasFullItemSearchResults
    if type(countFn) ~= "function" or type(resultFn) ~= "function" then return end
    if type(ah.HasSearchResults) == "function" then
        local searchKey = commodity and type(ah.MakeItemKey) == "function" and ah.MakeItemKey(id) or key
        local ok, has = pcall(ah.HasSearchResults, searchKey); if not ok or not has then return end
    end
    local ok, count = pcall(countFn, key); if not ok or type(count) ~= "number" then return end
    local entries, valid = {[id] = {quantity = 0, lots = {}, complete = false}}, true
    for i = 1, count do
        local got, row = pcall(resultFn, key, i)
        if not got or type(row) ~= "table" then valid = false
        elseif commodity then
            local quantity = tonumber(row.quantity)
            -- This field is supplied by modern clients for account-owned
            -- commodity units; do not pretend those are purchasable.
            if quantity then quantity = quantity - (tonumber(row.numOwnerItems) or 0) end
            AddLot(entries, id, quantity, quantity and row.unitPrice and row.unitPrice * quantity, {stack = false})
        elseif not row.containsOwnerItem and not row.containsAccountItem then
            AddLot(entries, id, tonumber(row.quantity), tonumber(row.buyoutAmount), {stack = true, auctionID = row.auctionID})
        end
    end
    local complete = false
    if type(fullFn) == "function" then local got, full = pcall(fullFn, key); complete = got and full == true and valid end
    -- An equipment variant search covers only that item key, not every item
    -- with the same base ID. Reagents / formulas normally use the zero key.
    local variant = not commodity and ((tonumber(key.itemSuffix) or 0) ~= 0 or (tonumber(key.itemLevel) or 0) ~= 0 or
        (tonumber(key.battlePetSpeciesID) or 0) ~= 0)
    if variant then complete = false end
    entries[id].complete = complete
    if not variant or not (Fresh(supply[id]) and supply[id].complete) then PublishSupply(entries) end
end
local function ObservePrice(db, state, dbKey, price, available)
    if type(Auctionator) ~= "table" or Auctionator.Database ~= db then return end
    -- Variant aliases describe the same auction rows; only the base item key
    -- can be used for a reagent's finite quantity budget.
    if type(dbKey) ~= "string" or not dbKey:match("^[1-9]%d*$") then return end
    local id, now = tonumber(dbKey), Now()
    if not Quantity(id) or now <= 0 then return end
    local market, _, key = Market()
    if type(price) == "number" and price > 0 and price < math.huge then
        market.prices[id] = {price = price, observedAt = now}
        DeferredRefresh("prices")
    end
    -- Price-only reports do not erase quantity or refresh its timestamp.
    if not Quantity(available) or available == 0 then return end
    local batch
    local context = state.scan
    if context and context.market == key and context.groups and context.groups[dbKey] then
        local expected = context.expected[dbKey]
        if not expected then
            local client, rows = supply[id], context.groups[dbKey]
            if Fresh(client) and client.market == key and client.batch == context.batch
                and Quantity(client.rawQuantity) and client.rawPrice then
                expected = {quantity = client.rawQuantity, price = client.rawPrice}
            elseif #rows <= 150 then
                local n, minimum = 0, math.huge
                for _, row in ipairs(rows) do
                    if not Quantity(row.available) or type(row.price) ~= "number" then n = -1; break end
                    n, minimum = n + row.available, math.min(minimum, row.price)
                end
                expected = {quantity = n, price = minimum}
            end
            -- Don't repeat Auctionator's unbounded aggregation for a huge
            -- single-item group. Until client evidence arrives it stays an
            -- independent, explicitly incomplete estimate.
            if expected then context.expected[dbKey] = expected end
        end
        -- Auctionator's overlapping ticker batches can report a boundary key
        -- twice. Repeated matching writes still belong to the same scan.
        if expected and expected.quantity == available and expected.price == price then batch = context.batch end
    end
    local revision = NextSequence()
    market.items[id] = {quantity = available, observedPrice = price, observedAt = now,
        source = "auctionator-update", complete = false, ownerExcluded = false,
        market = key, batch = batch or revision, revision = revision, schemaVersion = SUPPLY_VERSION}
    DeferredRefresh("supply")
    -- Don't retain a full scan's raw group table after its ticker has finished.
    if context and not context.cleanupQueued and C_Timer and type(C_Timer.After) == "function" then
        context.cleanupQueued = true
        C_Timer.After(0, function()
            context.cleanupQueued = nil
            if state.scan ~= context then return end
            local ticker = db.ticker
            if not ticker or (type(ticker.IsCancelled) == "function" and ticker:IsCancelled()) then state.scan = nil end
        end)
    end
end
local function InstallDatabaseHooks()
    local a = type(Auctionator) == "table" and Auctionator
    local db = a and a.Database
    if type(db) ~= "table" then databaseHookState = a and "initializing" or "missing"; return end
    if type(db.SetPrice) ~= "function" or type(hooksecurefunc) ~= "function" then databaseHookState = "unsupported"; return end
    local state = hookedDatabases[db]
    if not state then state = {}; hookedDatabases[db] = state end
    if state.method ~= db.SetPrice then
        state.error = nil
        local ok = pcall(hooksecurefunc, db, "SetPrice", function(self, dbKey, price, available)
            if state.error then return end
            local got, err = pcall(ObservePrice, self, state, dbKey, price, available)
            if not got then databaseHookState, state.error, databaseHookError = "error", tostring(err), tostring(err) end
        end)
        if not ok then databaseHookState = "unsupported"; return end
        -- hooksecurefunc may change the method reference on the table.
        state.method = db.SetPrice
    end
    -- Current Auctionator writes scan groups asynchronously. Tagging that
    -- operation makes filtered client evidence win only within this scan;
    -- a later purchase report gets its own batch and can replace older stock.
    if type(db.ProcessScan) == "function" and state.processMethod ~= db.ProcessScan then
        local ok = pcall(hooksecurefunc, db, "ProcessScan", function(self, groups)
            if state.error then return end
            local got, err = pcall(function()
                if type(Auctionator) ~= "table" or Auctionator.Database ~= self or type(groups) ~= "table" then return end
                local _, _, key = Market()
                state.scan = {groups = groups, expected = {}, market = key,
                    batch = legacyQuery and legacyQuery.batch or NextSequence()}
            end)
            if not got then databaseHookState, state.error, databaseHookError = "error", tostring(err), tostring(err) end
        end)
        if ok then state.processMethod = db.ProcessScan end
    end
    databaseHookState = state.error and "error" or "listening"
end
function AB.SupplyStatus()
    local market, character = Market()
    local shared, own, latest = 0, 0, 0
    for _, entry in pairs(market.items) do
        if Fresh(entry) then shared = shared + 1; latest = math.max(latest, entry.observedAt) end
    end
    for _, entry in pairs(character.items) do
        if Fresh(entry) then own = own + 1; latest = math.max(latest, entry.observedAt) end
    end
    return {hook = databaseHookState, schemaVersion = SUPPLY_VERSION,
        market = MarketKey(), revision = AB.SupplyRevision(), passive = true, persistent = true,
        lastError = databaseHookError, addonVersion = AddonMetadata("DungeonsForever"),
        queryHook = hookedLegacy, queryActive = legacyQuery ~= nil,
        sharedRecords = shared, characterRecords = own, latestObservedAt = latest > 0 and latest or nil,
        fullScanObservedAt = character.full and character.full.observedAt}
end
InstallSupplyHooks = function()
    InstallDatabaseHooks()
    if not hookedLegacy and type(hooksecurefunc) == "function" and type(QueryAuctionItems) == "function" then
        local ok = pcall(hooksecurefunc, "QueryAuctionItems", ObserveQuery); hookedLegacy = ok
    end
end

if type(CreateFrame) == "function" then
    local frame = CreateFrame("Frame")
    for _, event in ipairs({"ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "AUCTION_HOUSE_CLOSED", "AUCTION_HOUSE_SHOW",
        "AUCTION_ITEM_LIST_UPDATE", "ITEM_SEARCH_RESULTS_UPDATED", "COMMODITY_SEARCH_RESULTS_UPDATED"}) do
        pcall(frame.RegisterEvent, frame, event)
    end
    frame:SetScript("OnEvent", function(_, event, addon)
        if event == "AUCTION_HOUSE_SHOW" then
            -- Other SHOW listeners (Auctionator / Blizzard) may already have
            -- started a query. Clearing it here loses the incoming result's
            -- identity, including complete empty queries. CLOSED resets the
            -- previous session; keep any query just observed before this event.
            InstallSupplyHooks(); return
        end
        if event == "AUCTION_HOUSE_CLOSED" then ClearSupply() end
        if event == "AUCTION_ITEM_LIST_UPDATE" then CaptureLegacy(); return end
        if event == "ITEM_SEARCH_RESULTS_UPDATED" or event == "COMMODITY_SEARCH_RESULTS_UPDATED" then CaptureModern(event, addon); return end
        if event == "ADDON_LOADED" and addon ~= "Auctionator" and addon ~= "DungeonsForever" and addon ~= "Blizzard_AuctionUI" and addon ~= "Blizzard_AuctionHouseUI" then return end
        if event == "ADDON_LOADED" or event == "PLAYER_LOGIN" then retries = 0 end
        -- Next frame, after every addon's PLAYER_LOGIN handler has run.
        DeferredRefresh("readiness")
    end)
end
InstallSupplyHooks()
if type(ns.Init) == "function" then ns.Init(function() DeferredRefresh("readiness") end) end

if type(SlashCmdList) == "table" then
    SLASH_DFUNGEONSAUCTION1 = "/dfauction"
    SlashCmdList.DFUNGEONSAUCTION = function(message)
        AB.Refresh("readiness")
        local status = AB.SupplyStatus()
        Say(format("DungeonsForever %s; Auctionator %s; quantity hook=%s; schema=%s; market=%s; revision=%s",
            tostring(status.addonVersion or "?"), tostring(AddonMetadata() or "?"),
            status.hook, status.schemaVersion, status.market, status.revision))
        Say(format("query hook=%s; active=%s; shared=%d; character=%d; latest=%s; full scan=%s",
            tostring(status.queryHook), tostring(status.queryActive), status.sharedRecords, status.characterRecords,
            tostring(status.latestObservedAt or "unknown"), tostring(status.fullScanObservedAt or "unknown")))
        local ids, seen = {}, {}
        for text in tostring(message or ""):gmatch("%d+") do
            local id = tonumber(text)
            if id and id > 0 and not seen[id] and #ids < 12 then ids[#ids + 1] = id; seen[id] = true end
        end
        local plan = ns.ProfModule and ns.ProfModule.autoSnapshot
        if #ids == 0 and plan then
            for _, list in ipairs({plan.mats or {}, plan.formulas or {}}) do
                for _, entry in ipairs(list) do
                    local id = tonumber(entry.id or entry[1])
                    if id and not seen[id] and not entry.known and #ids < 12
                        and (entry.source == "ah" or entry.source == "auction") then
                        ids[#ids + 1] = id; seen[id] = true
                    end
                end
            end
        end
        for _, id in ipairs(ids) do
            local entry = AB.GetAuctionSupply(id, true)
            Say(format("item=%d; quantity=%s; source=%s; complete=%s; observed=%s", id,
                tostring(entry and entry.quantity or "unknown"), tostring(entry and entry.source or "none"),
                tostring(entry and entry.complete or false), tostring(entry and entry.observedAt or "unknown")))
        end
        if status.lastError then Say(status.lastError) end
    end
end

-- 清单名：[DF] 前缀便于在拍卖行插件的清单列表里一眼认出本插件推的清单
function AB.ListName(profName)
    return format(L["[DF] %s购物清单"], profName or "?")
end

-- 条目搜索串：精确匹配（双引号包裹）+ 数量（末位字段）。
--   目标插件存储格式 = 14 字段 `;` 分隔（queryString;…;tier;expansion;quantity），
--   tier 缺省占位 "#"；有 API 时走 ConvertToSearchString（官方拼装，零格式风险），
--   无 API（降级导出串）时按同一契约 strjoin 手拼。
function AB.SearchString(name, need)
    local quoted = "\"" .. (name or "") .. "\""
    local hasNeed = (type(need) == "number" and need > 0) and true or false
    if AB.Available() and type(Auctionator.API.v1.ConvertToSearchString) == "function" then
        local term = { searchString = name, isExact = true }
        if hasNeed then term.quantity = need end
        local ok, s = pcall(Auctionator.API.v1.ConvertToSearchString, CALLER, term)
        if ok and type(s) == "string" and s ~= "" then return s end
    end
    if hasNeed then
        return strjoin(";", quoted, "", "", "", "", "", "", "", "", "", "", "#", "", tostring(need))
    end
    return quoted
end

-- 调公开 API 建清单；成功 true。只收合法名字，空名跳过（不中断整单）
function AB.Import(listName, items)
    if not AB.Available() then return false, "Auctionator not available" end
    local strings = {}
    for _, e in ipairs(items) do
        if type(e) == "table" and type(e.name) == "string" and e.name ~= "" then
            strings[#strings + 1] = AB.SearchString(e.name, e.need)
        end
    end
    local ok, err = pcall(Auctionator.API.v1.CreateShoppingList, CALLER, listName, strings)
    if ok then return true end
    return false, err
end

-- 降级导出串：拍卖行插件原生批量导入格式「清单名^物品1^物品2」（单行一条清单）
function AB.ExportString(listName, items)
    local parts = { listName }
    for _, e in ipairs(items) do
        if type(e) == "table" and type(e.name) == "string" and e.name ~= "" then
            parts[#parts + 1] = AB.SearchString(e.name, e.need)
        end
    end
    return table.concat(parts, "^")
end

-- 降级弹窗：全选可复制（同 DungeonUI ShowSourceURL 的 StaticPopup 口径）
local POPUP = "DungeonsForever_AuctionImport"
local pendingImportText = ""
function AB.ShowCopy(text, message)
    pendingImportText = text or ""
    if not StaticPopupDialogs[POPUP] then
        StaticPopupDialogs[POPUP] = {
            text = L["未检测到 Auctionator，请复制以下导入串"],
            button1 = L["关闭"],
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
            hasEditBox = true,
            editBoxWidth = 320,
            OnShow = function(self)
                local edit = self.EditBox or self.editBox
                edit:SetText(pendingImportText)
                edit:HighlightText()
                edit:SetFocus()
            end,
            EditBoxOnEnterPressed = function(self)
                self:GetParent():Hide()
            end,
            EditBoxOnEscapePressed = function(self)
                self:GetParent():Hide()
            end,
        }
    end
    StaticPopupDialogs[POPUP].text = message or L["未检测到 Auctionator，请复制以下导入串"]
    StaticPopup_Show(POPUP)
end

-- 一键导入主入口（ProfFollow 两个按钮共用）
function AB.DoImport(profName, items)
    if not (type(items) == "table" and #items > 0) then
        Say(L["购物清单为空，没有可导入的物品"])
        return
    end
    local listName = AB.ListName(profName)
    if AB.Available() then
        local ok, err = AB.Import(listName, items)
        if ok then
            Say(format(L["已导入 Auctionator：%s（共 %d 种）"], listName, #items))
        else
            Say(L["导入失败："] .. tostring(err or "?"))
        end
        return
    end
    local status = AB.Refresh("readiness")
    if status.installed then
        local message = status.state == "disabled" and L["Auctionator 已安装但未启用，请启用后重载界面。"]
            or L["Auctionator 正在初始化，请稍后重试；也可复制以下导入串。"]
        AB.ShowCopy(AB.ExportString(listName, items), message)
        Say(message)
    else
        AB.ShowCopy(AB.ExportString(listName, items))
        Say(L["未检测到 Auctionator，请在 Auctionator → 购物清单 → 导入 中粘贴"])
    end
end
