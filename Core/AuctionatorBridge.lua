local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local AB = {}
ns.AuctionBridge = AB

local CALLER = "DungeonsForever"

local format = string.format

local function Say(msg)
    local frame = DEFAULT_CHAT_FRAME
    if frame and frame.AddMessage then
        frame:AddMessage("|cffffd100" .. msg .. "|r")
    end
end

function AB.Available()
    return type(Auctionator) == "table"
        and type(Auctionator.API) == "table"
        and type(Auctionator.API.v1) == "table"
        and type(Auctionator.API.v1.CreateShoppingList) == "function"
end

function AB.ListName(profName)
    return format(L["[DF] %s购物清单"], profName or "?")
end

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

function AB.ExportString(listName, items)
    local parts = { listName }
    for _, e in ipairs(items) do
        if type(e) == "table" and type(e.name) == "string" and e.name ~= "" then
            parts[#parts + 1] = AB.SearchString(e.name, e.need)
        end
    end
    return table.concat(parts, "^")
end

local POPUP = "DungeonsForever_AuctionImport"
local pendingImportText = ""
function AB.ShowCopy(text)
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
    StaticPopup_Show(POPUP)
end

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
    AB.ShowCopy(AB.ExportString(listName, items))
    Say(L["未检测到 Auctionator，请在 Auctionator → 购物清单 → 导入 中粘贴"])
end

local SUPPLY_MAX_AGE = 172800
local SUPPLY_RETRY = 2
local SUPPLY_TIMEOUT = 6

local supplyFrame, supplyQueue, supplyCur, supplyTimer, supplyDone
local supplyRetry, supplyRevision = 0, 0

local function ProfDB()
    return DungeonsForeverDB and DungeonsForeverDB.prof
end

local function SupplyStore()
    local db = ProfDB()
    if not db then return nil end
    db.auctionSupply = db.auctionSupply or {}
    return db.auctionSupply
end

function AB.SupplyRevision()
    return supplyRevision
end

function AB.GetAuctionSupply(id, live)
    if type(id) ~= "number" or id <= 0 then return nil end
    local store = SupplyStore()
    local rec = store and store[id] or nil
    if type(rec) ~= "table" then return nil end
    return {
        quantity = tonumber(rec.q),
        observedAt = tonumber(rec.t) or 0,
        complete = rec.c == true,
        ownerExcluded = rec.ox == true,
        source = rec.s or "client-auction-results",
        market = tonumber(rec.p),
    }
end

function AB.SupplyFresh(id)
    local rec = AB.GetAuctionSupply(id)
    if not rec or not rec.complete or not rec.ownerExcluded then return nil end
    if rec.source ~= "client-auction-results" then return nil end
    if type(rec.quantity) ~= "number" then return nil end
    local now = (type(time) == "function") and time() or 0
    if rec.observedAt <= 0 or now - rec.observedAt > SUPPLY_MAX_AGE then return nil end
    return rec
end

function AB.SupplyEstimate(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local A = Auctionator
    if type(A) ~= "table" or type(A.Database) ~= "table" then return nil end
    local db = A.Database.db
    if type(db) ~= "table" then return nil end
    local entry = db[tostring(id)]
    if type(entry) ~= "table" then return nil end
    local scanDay = nil
    if type(A.Constants) == "table" and tonumber(A.Constants.SCAN_DAY_0) then
        scanDay = math.floor(((time and time() or 0) - A.Constants.SCAN_DAY_0) / 86400)
    end
    local qty, day = nil, nil
    if type(entry.a) == "table" then
        if scanDay and entry.a[tostring(scanDay)] then
            qty, day = tonumber(entry.a[tostring(scanDay)]), scanDay
        else
            for d, v in pairs(entry.a) do
                local dv = tonumber(d)
                if dv and (day == nil or dv > day) and tonumber(v) then
                    qty, day = tonumber(v), dv
                end
            end
        end
    end
    if qty == nil then return nil end
    local observedAt = (day and A.Constants.SCAN_DAY_0) and day * 86400 + A.Constants.SCAN_DAY_0 or nil
    return {
        quantity = qty,
        observedAt = observedAt or 0,
        complete = false,
        ownerExcluded = false,
        source = "auctionator-update",
        market = tonumber(entry.m),
    }
end

local function SupplyWrite(id, qty, price)
    local store = SupplyStore()
    if not store then return end
    store[id] = {
        q = qty, p = price, t = (time and time()) or 0,
        c = true, ox = true, s = "client-auction-results",
    }
    supplyRevision = supplyRevision + 1
end

local function SupplyAbort(msg)
    if supplyTimer then supplyTimer:Cancel(); supplyTimer = nil end
    supplyQueue, supplyCur, supplyDone = nil, nil, nil
    supplyRetry = 0
    if supplyFrame then supplyFrame:UnregisterAllEvents() end
    if msg then Say(msg) end
end

local function SupplySorts()
    local order = (type(Enum) == "table" and type(Enum.AuctionHouseSortOrder) == "table")
        and Enum.AuctionHouseSortOrder.Price or 0
    return { { sortOrder = order, reverseSort = false } }
end

local function SupplyHarvest()
    local id, key, isCommodity = supplyCur.id, supplyCur.key, supplyCur.commodity
    local qty, price, complete = 0, nil, false
    if isCommodity then
        complete = C_AuctionHouse.HasFullCommoditySearchResults(id) and true or false
        local n = C_AuctionHouse.GetNumCommoditySearchResults(id)
        for i = 1, n do
            local info = C_AuctionHouse.GetCommoditySearchResultInfo(id, i)
            if type(info) == "table" and info.containsOwnerItem ~= true then
                qty = qty + (tonumber(info.quantity) or 0)
                local unit = tonumber(info.unitPrice) or 0
                if unit > 0 and (price == nil or unit < price) then price = unit end
            end
        end
    else
        complete = key and C_AuctionHouse.HasFullItemSearchResults(key) and true or false
        if key then
            local n = C_AuctionHouse.GetNumItemSearchResults(key)
            for i = 1, n do
                local info = C_AuctionHouse.GetItemSearchResultInfo(key, i)
                if type(info) == "table" and info.containsOwnerItem ~= true then
                    qty = qty + (tonumber(info.quantity) or 0)
                    local buyout = tonumber(info.buyoutPrice) or 0
                    if buyout > 0 and (price == nil or buyout < price) then price = buyout end
                end
            end
        end
    end
    return qty, price, complete
end

local SupplySend
local function SupplyNext()
    supplyRetry = 0
    if supplyTimer then supplyTimer:Cancel(); supplyTimer = nil end
    local nextID = #supplyQueue > 0 and table.remove(supplyQueue, 1) or nil
    if not nextID then
        local done = supplyDone
        SupplyAbort()
        if done then done() end
        return
    end
    local status = C_AuctionHouse.GetItemCommodityStatus(nextID)
    if status == nil then
        if supplyCur.waiting == nextID then
            supplyCur.waiting = nil
            SupplyNext()
            return
        end
        supplyCur.waiting = nextID
        table.insert(supplyQueue, nextID)
        supplyTimer = C_Timer.NewTimer(0.5, SupplyNext)
        return
    end
    local key = C_AuctionHouse.MakeItemKey(nextID)
    if not key or not C_AuctionHouse.GetItemKeyInfo(key) then
        SupplyNext()
        return
    end
    supplyCur = { id = nextID, key = key, commodity = status == 1 }
    if not C_AuctionHouse.IsThrottledMessageSystemReady() then
        supplyTimer = C_Timer.NewTimer(0.4, function() SupplySend() end)
        return
    end
    SupplySend()
end

SupplySend = function()
    if not supplyCur or not supplyCur.id then return end
    C_AuctionHouse.SendSearchQuery(supplyCur.key, SupplySorts(), true)
    if supplyTimer then supplyTimer:Cancel() end
    supplyTimer = C_Timer.NewTimer(SUPPLY_TIMEOUT, function()
        supplyRetry = supplyRetry + 1
        if supplyRetry > SUPPLY_RETRY then
            SupplyNext()
        else
            SupplySend()
        end
    end)
end

local function SupplyAccept()
    local qty, price = SupplyHarvest()
    SupplyWrite(supplyCur.id, qty, price)
    SupplyNext()
end

local function SupplyOnEvent(_, event, arg1)
    if event == "AUCTION_HOUSE_CLOSED" then
        SupplyAbort(L["拍卖行已关闭，数量扫描中止。"])
        return
    end
    if not supplyCur then return end
    if event == "AUCTION_HOUSE_SEARCH_RESULTS_UPDATED" then
        if supplyCur.commodity and arg1 == supplyCur.id then
            if not C_AuctionHouse.HasFullCommoditySearchResults(supplyCur.id) then
                C_AuctionHouse.RequestMoreCommoditySearchResults(supplyCur.id)
            else
                SupplyAccept()
            end
        elseif not supplyCur.commodity and type(arg1) == "table" and arg1.itemID == supplyCur.id then
            if not C_AuctionHouse.HasFullItemSearchResults(arg1) then
                C_AuctionHouse.RequestMoreItemSearchResults(arg1)
            else
                SupplyAccept()
            end
        end
    elseif event == "AUCTION_HOUSE_SEARCH_RESULTS_INCREMENTAL" then
        if supplyCur.commodity then
            if C_AuctionHouse.HasFullCommoditySearchResults(supplyCur.id) then SupplyAccept() end
        elseif supplyCur.key and C_AuctionHouse.HasFullItemSearchResults(supplyCur.key) then
            SupplyAccept()
        end
    end
end

function AB.SupplyScanActive()
    return supplyQueue ~= nil
end

function AB.StartSupplyScan(ids, onDone)
    if not (type(C_AuctionHouse) == "table" and C_AuctionHouse.SendSearchQuery) then
        Say(L["当前客户端没有拍卖行查询接口，无法扫描数量。"])
        return false
    end
    local ah = AuctionHouseFrame
    if not (type(ah) == "table" and ah.IsShown and ah:IsShown()) then
        Say(L["请先打开拍卖行，再点一次扫描。"])
        return false
    end
    if supplyQueue then Say(L["数量扫描进行中。"]) return true end
    local queue = {}
    local seen = {}
    for _, id in ipairs(ids or {}) do
        if type(id) == "number" and id > 0 and not seen[id] then
            seen[id] = true
            queue[#queue + 1] = id
        end
    end
    if #queue == 0 then Say(L["没有需要扫描的物品。"]) return false end
    if not supplyFrame then
        supplyFrame = CreateFrame("Frame")
        supplyFrame:SetScript("OnEvent", SupplyOnEvent)
    end
    supplyQueue = queue
    supplyDone = onDone
    supplyFrame:RegisterEvent("AUCTION_HOUSE_CLOSED")
    supplyFrame:RegisterEvent("AUCTION_HOUSE_SEARCH_RESULTS_UPDATED")
    supplyFrame:RegisterEvent("AUCTION_HOUSE_SEARCH_RESULTS_INCREMENTAL")
    supplyCur = {}
    Say(format(L["开始扫描拍卖行数量（%d 种）…"], #queue))
    SupplyNext()
    return true
end
