local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local AB = {}
ns.AuctionBridge = AB
if type(gns) == "table" and gns ~= ns then
    gns.AuctionBridge = AB
end

local CALLER = "DungeonsForever"
local format = string.format
local floor, ceil, min, max, huge = math.floor, math.ceil, math.min, math.max, math.huge

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getEasyBridge()
    return ns.EasyBridge or (type(gns) == "table" and gns.EasyBridge) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getL()
    return ns.L or (type(gns) == "table" and gns.L) or nil
end

local function getInit()
    return ns.Init or (type(gns) == "table" and gns.Init) or nil
end

local function getSkinPopupFont()
    return ns.SkinPopupFont or (type(gns) == "table" and gns.SkinPopupFont) or nil
end

local function tr(key)
    local L = getL()
    if type(L) == "table" then
        local ok, v = pcall(function() return L[key] end)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return key
end

local function Now()
    if type(_G.time) == "function" then
        local ok, v = pcall(_G.time)
        if ok and type(v) == "number" then return v end
    end
    if type(os) == "table" and type(os.time) == "function" then
        local ok, v = pcall(os.time)
        if ok and type(v) == "number" then return v end
    end
    return 0
end

local function cfgTbl(key)
    local cfg = getPricingCfg()
    local v = type(cfg) == "table" and cfg[key] or nil
    return type(v) == "table" and v or nil
end

local function SupplyMaxAge()
    local cfg = getPricingCfg()
    if type(cfg) == "table" and type(cfg.SUPPLY_MAX_AGE_SEC) == "number" and cfg.SUPPLY_MAX_AGE_SEC > 0 then
        return cfg.SUPPLY_MAX_AGE_SEC
    end
    local ra = getRouteAuto()
    if ra and type(ra.MaxAuctionSupplyAgeSeconds) == "function" then
        local ok, v = pcall(ra.MaxAuctionSupplyAgeSeconds)
        if ok and type(v) == "number" and v > 0 then return v end
    end
    return 172800
end

local function SnapshotVersion()
    local cfg = getPricingCfg()
    return (type(cfg) == "table" and type(cfg.SNAPSHOT_VERSION) == "number" and cfg.SNAPSHOT_VERSION) or 3
end

local function ScanSilentSec()
    local cfg = getPricingCfg()
    return (type(cfg) == "table" and type(cfg.SCAN_SILENT_SEC) == "number" and cfg.SCAN_SILENT_SEC > 0 and cfg.SCAN_SILENT_SEC) or 45
end

local function validNum(v)
    return type(v) == "number" and v == v and v ~= huge and v ~= -huge
end

function AB.AHCut()
    local auct = _G.Auctionator
    local constants = type(auct) == "table" and auct.Constants
    local factor = type(constants) == "table" and constants.AfterAHCut
    if validNum(factor) and factor >= 0 and factor <= 1 then
        return 1 - factor
    end
    local eb = getEasyBridge()
    if eb and type(eb.AuctionCut) == "function" then
        local ok, cut = pcall(eb.AuctionCut)
        if ok and validNum(cut) and cut >= 0 and cut <= 100 then
            return cut / 100
        end
    end
    local cfg = getPricingCfg()
    if type(cfg) == "table" and validNum(cfg.AH_CUT) and cfg.AH_CUT >= 0 and cfg.AH_CUT <= 1 then
        return cfg.AH_CUT
    end
    return 0.05
end

function AB.NetMultiplier()
    local auct = _G.Auctionator
    local constants = type(auct) == "table" and auct.Constants
    local factor = type(constants) == "table" and constants.AfterAHCut
    if validNum(factor) and factor >= 0 and factor <= 1 then
        return factor
    end
    local eb = getEasyBridge()
    if eb and type(eb.AuctionCut) == "function" then
        local ok, cut = pcall(eb.AuctionCut)
        if ok and validNum(cut) and cut >= 0 and cut <= 100 then
            return 1 - cut / 100
        end
    end
    local cfg = getPricingCfg()
    if type(cfg) == "table" and validNum(cfg.NET_MULTIPLIER) and cfg.NET_MULTIPLIER >= 0 and cfg.NET_MULTIPLIER <= 1 then
        return cfg.NET_MULTIPLIER
    end
    return 1 - AB.AHCut()
end

function AB.NetPrice(gross)
    if not validNum(gross) or gross < 0 then return nil end
    return floor(gross * AB.NetMultiplier() + 1e-9)
end

function AB.TrimFishingOrders(levels)
    if type(levels) ~= "table" or #levels == 0 then
        return {}, 0, 0, 0, 0
    end
    local rows = {}
    local rawTotal = 0
    for i = 1, #levels do
        local row = levels[i]
        local p = type(row) == "table" and (row[1] or row.price) or nil
        local q = type(row) == "table" and (row[2] or row.quantity or row.qty) or nil
        if validNum(p) and p > 0 and validNum(q) and q > 0 then
            local qi = floor(q)
            if qi > 0 then
                rows[#rows + 1] = { p, qi }
                rawTotal = rawTotal + qi
            end
        end
    end
    if #rows == 0 or rawTotal <= 0 then
        return {}, 0, 0, 0, 0
    end
    table.sort(rows, function(a, b) return a[1] < b[1] end)

    local ff = cfgTbl("FISHING_FILTER") or {}
    local startIdx = 1
    local remTotal = rawTotal
    local trimmedQty = 0
    local trimmedLots = 0
    if ff.enabled ~= false and rawTotal >= (ff.minTotalSupplyForTrim or 5) then
        local maxLots = ff.headMaxLotCount or 3
        local maxShare = ff.headMaxQtyShare or 0.05
        local cliffRatio = ff.cliffPriceRatio or 0.60
        while startIdx < #rows and trimmedLots < maxLots do
            local lot = rows[startIdx]
            local nextLot = rows[startIdx + 1]
            if (lot[2] / rawTotal) <= maxShare and (lot[1] / nextLot[1]) <= cliffRatio then
                remTotal = remTotal - lot[2]
                trimmedQty = trimmedQty + lot[2]
                startIdx = startIdx + 1
                trimmedLots = trimmedLots + 1
            else
                break
            end
        end
    end

    local denoised = {}
    for i = startIdx, #rows do
        denoised[#denoised + 1] = { rows[i][1], rows[i][2] }
    end
    return denoised, remTotal, trimmedQty, trimmedLots, rawTotal
end

function AB.RobustFloorPrice(levels, percentile)
    local denoised, remTotal, _, _, rawTotal = AB.TrimFishingOrders(levels)
    if #denoised == 0 or remTotal <= 0 then return nil end

    local rf = cfgTbl("ROBUST_FLOOR") or {}
    local minSupply = type(rf.minConfidenceSupply) == "number" and rf.minConfidenceSupply or 1
    if rawTotal < minSupply then return nil end

    local pct = type(rf.defaultPercentile) == "number" and rf.defaultPercentile or 0.125
    if validNum(percentile) and percentile > 0 and percentile < 1 then
        local lo = type(rf.percentileLow) == "number" and rf.percentileLow or 0.10
        local hi = type(rf.percentileHigh) == "number" and rf.percentileHigh or 0.15
        if lo > hi then lo, hi = hi, lo end
        pct = max(lo, min(hi, percentile))
    end

    local targetQty = max(1, ceil(remTotal * pct))
    local cum = 0
    local chosen = denoised[1][1]
    for i = 1, #denoised do
        cum = cum + denoised[i][2]
        if cum >= targetQty then
            chosen = denoised[i][1]
            break
        end
    end
    local floored = floor(chosen)
    if floored >= 1 then return floored end
    return chosen
end

local function Say(msg)
    local frame = _G.DEFAULT_CHAT_FRAME
    if type(frame) == "table" and type(frame.AddMessage) == "function" then
        frame:AddMessage("|cffffd100" .. msg .. "|r")
    end
end

function AB.Available()
    local a = _G.Auctionator
    return type(a) == "table"
        and type(a.API) == "table"
        and type(a.API.v1) == "table"
        and type(a.API.v1.CreateShoppingList) == "function"
end

function AB.ListName(profName)
    return format(tr("[DF] %s购物清单"), profName or "?")
end

function AB.SearchString(name, need)
    local quoted = "\"" .. (name or "") .. "\""
    local hasNeed = (type(need) == "number" and need > 0) and true or false
    local a = _G.Auctionator
    if AB.Available() and type(a.API.v1.ConvertToSearchString) == "function" then
        local term = { searchString = name, isExact = true }
        if hasNeed then term.quantity = need end
        local ok, s = pcall(a.API.v1.ConvertToSearchString, CALLER, term)
        if ok and type(s) == "string" and s ~= "" then return s end
    end
    if hasNeed then
        return table.concat({ quoted, "", "", "", "", "", "", "", "", "", "", "#", "", tostring(need) }, ";")
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
    local ok, err = pcall(_G.Auctionator.API.v1.CreateShoppingList, CALLER, listName, strings)
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
local pendingImportHint = nil

function AB.ShowCopy(text, hint)
    pendingImportText = text or ""
    pendingImportHint = hint
    local dialogs = _G.StaticPopupDialogs
    local showFn = _G.StaticPopup_Show
    if type(dialogs) ~= "table" or type(showFn) ~= "function" then
        return false
    end
    if not dialogs[POPUP] then
        dialogs[POPUP] = {
            text = tr("未检测到可写入的购物清单插件，请复制以下导入串"),
            button1 = tr("关闭"),
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
            hasEditBox = true,
            editBoxWidth = 320,
            OnShow = function(self)
                local label = self.text or (self.GetName and _G[(self:GetName() or "") .. "Text"])
                if label and pendingImportHint and label.SetText then label:SetText(pendingImportHint) end
                local edit = self.EditBox or self.editBox
                if edit then
                    edit:SetText(pendingImportText)
                    edit:HighlightText()
                    edit:SetFocus()
                end
                local skin = getSkinPopupFont()
                if type(skin) == "function" then skin(self) end
            end,
            EditBoxOnEnterPressed = function(self)
                local parent = self:GetParent()
                if parent and parent.Hide then parent:Hide() end
            end,
            EditBoxOnEscapePressed = function(self)
                local parent = self:GetParent()
                if parent and parent.Hide then parent:Hide() end
            end,
        }
    end
    showFn(POPUP)
    return true
end

local function NativeAuctionator()
    local a = _G.Auctionator
    return type(a) == "table"
        and a.EasyAuctionCompat == nil
        and type(a.API) == "table"
        and type(a.API.v1) == "table"
        and type(a.API.v1.CreateShoppingList) == "function"
end

function AB.DoImport(profName, items)
    if not (type(items) == "table" and #items > 0) then
        Say(tr("购物清单为空，没有可导入的物品"))
        return
    end
    local listName = AB.ListName(profName)
    if NativeAuctionator() then
        local ok, err = AB.Import(listName, items)
        if ok then
            Say(format(tr("已导入 Auctionator：%s（共 %d 种）"), listName, #items))
        else
            Say(tr("导入失败：") .. tostring(err or "?"))
        end
        return
    end
    local eb = getEasyBridge()
    if eb and eb.CanLists and eb.CanLists() then
        local ok, err, count = eb.ReplaceList(listName, items)
        if ok then
            Say(format(tr("已导入 EasyAuction：%s（共 %d 种）"), listName, count or #items))
            return
        end
        local text = eb.ShareText and eb.ShareText(listName, items)
        if text then
            AB.ShowCopy(text, tr("EasyAuction 清单写入失败，请复制以下分享码在 EasyAuction 中导入"))
            return
        end
        Say(tr("导入失败：") .. tostring(err or "?"))
        return
    end
    if eb and eb.ShareText and type(_G.EasyAuction12) == "table" then
        local text = eb.ShareText(listName, items)
        if text then
            AB.ShowCopy(text, tr("EasyAuction 清单写入失败，请复制以下分享码在 EasyAuction 中导入"))
            return
        end
    end
    AB.ShowCopy(AB.ExportString(listName, items), tr("未检测到 EasyAuction 或 Auctionator，请复制以下导入串"))
end

local function WholeNumber(n)
    return type(n) == "number" and n >= 0 and n < huge and n == floor(n)
end

local fallbackScanDB = {}
local function ScanDB()
    local db = getDB()
    if type(db) == "table" and type(db.Get) == "function" then
        local ok, root = pcall(db.Get)
        if ok and type(root) == "table" then
            if type(root.prof) ~= "table" then root.prof = {} end
            return root.prof
        end
    elseif type(db) == "function" then
        local ok, root = pcall(db)
        if ok and type(root) == "table" then
            if type(root.prof) ~= "table" then root.prof = {} end
            return root.prof
        end
    end
    return fallbackScanDB
end

local supplyRevision = 0
local supplyListeners = {}
local forcedUntil = 0

function AB.ForceExpiredWindow(seconds)
    local now = Now()
    forcedUntil = now + max(30, tonumber(seconds) or 180)
    supplyRevision = supplyRevision + 1
    return forcedUntil
end

function AB.ForceExpiredActive()
    return forcedUntil > 0 and Now() <= forcedUntil
end

function AB.ForceExpiredLeft()
    if not AB.ForceExpiredActive() then return 0 end
    return max(0, forcedUntil - Now())
end

local function MarketKey()
    local rules = _G.C_GameRules
    local enumTbl = _G.Enum
    local ids = type(enumTbl) == "table" and enumTbl.GameRule or nil
    local factionFn = _G.UnitFactionGroup
    local regionFn = _G.GetCurrentRegion
    local faction = type(factionFn) == "function" and factionFn("player") or nil
    local region = type(regionFn) == "function" and regionFn() or nil
    if not (type(rules) == "table" and type(rules.IsGameRuleActive) == "function" and type(ids) == "table"
        and WholeNumber(region) and region > 0 and (faction == "Alliance" or faction == "Horde")) then return nil end
    local bits = {}
    for _, name in ipairs({ "PvPRuleset", "RPRuleset", "HardcoreRuleset" }) do
        if ids[name] == nil then return nil end
        local ok, value = pcall(rules.IsGameRuleActive, ids[name])
        if not ok or type(value) ~= "boolean" then return nil end
        bits[#bits + 1] = value and "1" or "0"
    end
    return "rules:1:forever:" .. region .. ":" .. table.concat(bits) .. ":" .. faction
end

local function ObserverKey()
    local guidFn = _G.UnitGUID
    local nameFn = _G.UnitName
    local guid = type(guidFn) == "function" and guidFn("player") or nil
    local name = type(nameFn) == "function" and nameFn("player") or nil
    return tostring(guid or name or "")
end

function AB.OnChanged(fn)
    if type(fn) == "function" then supplyListeners[#supplyListeners + 1] = fn end
end

local function SupplyChanged(id)
    supplyRevision = supplyRevision + 1
    for _, fn in ipairs(supplyListeners) do pcall(fn, id, "supply") end
end

local denoisedCache = setmetatable({}, { __mode = "k" })

local function getDenoisedItem(batch, id)
    local item = type(batch) == "table" and type(batch.items) == "table" and batch.items[id] or nil
    if type(item) ~= "table" then return nil end
    if batch.dv ~= 1 or type(item.d) ~= "table" or not WholeNumber(item.q) or item.q <= 0 then
        return {
            p = item.p,
            quantity = item.q or 0,
            rawQuantity = item.q or 0,
            trimmedQuantity = 0,
            trimmedLots = 0,
            levels = {},
        }
    end
    local byId = denoisedCache[batch]
    if not byId then
        byId = {}
        denoisedCache[batch] = byId
    end
    local cached = byId[id]
    if cached then return cached end
    local levels, denoisedTotal, trimmedQty, trimmedLots = AB.TrimFishingOrders(item.d)
    local robust = AB.RobustFloorPrice(item.d)
    local price = (type(robust) == "number" and robust > 0) and robust or item.p
    cached = {
        p = price,
        quantity = denoisedTotal,
        rawQuantity = item.q,
        trimmedQuantity = trimmedQty,
        trimmedLots = trimmedLots,
        levels = levels,
    }
    byId[id] = cached
    return cached
end

local fullBatch, fullFailure, fullExpiryTimer, fullExpiryToken, replicateState
local restoredSnapshot = false
local currentMarket = false
local SelectMarket

local function StoreBatch(batch)
    local key = batch.mk or currentMarket
    if type(key) ~= "string" or key == "" then return end
    batch.mk = key
    local db = ScanDB()
    if db.auctionFullScans ~= nil and type(db.auctionFullScans) ~= "table" then return false end
    db.auctionFullScans = db.auctionFullScans or {}
    db.auctionFullScans[key] = batch
    return true
end

local function ReleaseFullBatch(reason, observation, snapshotStatus)
    if fullExpiryTimer then fullExpiryTimer:Cancel(); fullExpiryTimer = nil end
    fullExpiryToken = nil
    local batch = observation or fullBatch or fullFailure
    fullFailure = { v = SnapshotVersion(), failure = reason, snapshotStatus = snapshotStatus }
    if type(batch) == "table" then
        fullFailure.mk, fullFailure.ob, fullFailure.ox = batch.mk, batch.ob, batch.ox
        if WholeNumber(batch.t) and batch.t > 0 then fullFailure.t = batch.t end
        if reason == "expired" and type(batch.items) == "table" then
            local keep = {}
            for id, item in pairs(batch.items) do
                if WholeNumber(id) and id > 0 and type(item) == "table" then
                    local q = tonumber(item.q)
                    if q and q >= 0 and q == floor(q) then
                        local p = tonumber(item.p)
                        if p and p > 0 and p < huge then keep[id] = { q = q, p = p } else keep[id] = { q = q } end
                        keep[id].d = item.d
                        keep[id].failure = item.failure
                    end
                end
            end
            fullFailure.items = keep
            fullFailure.dv = batch.dv
        end
    end
    fullBatch = nil
    StoreBatch(fullFailure)
end

local function FullBatchFailure(batch)
    local key = MarketKey()
    if not key or batch.mk ~= key then return "unverified" end
    if batch.v ~= SnapshotVersion() or batch.c ~= true or type(batch.items) ~= "table" then return "incomplete" end
    local stamp = batch.t
    local now = Now()
    if not WholeNumber(stamp) or stamp <= 0 or stamp > now then return "incomplete" end
    if now - stamp > SupplyMaxAge() and not AB.ForceExpiredActive() then return "expired" end
end

local function ValidSavedBatch(batch)
    local now = Now()
    if type(batch) ~= "table" or batch.v ~= SnapshotVersion() or batch.c ~= true
        or batch.s ~= "client-auction-results" or type(batch.ox) ~= "boolean"
        or type(batch.mk) ~= "string" or batch.mk == "" or type(batch.ob) ~= "string" or batch.ob == ""
        or not WholeNumber(batch.t) or batch.t <= 0 or batch.t > now
        or not WholeNumber(batch.completedAt) or batch.completedAt < batch.t or batch.completedAt > now
        or not WholeNumber(batch.expected) or batch.received ~= batch.expected or type(batch.items) ~= "table" then return false end
    if batch.dv ~= nil and batch.dv ~= 1 then return false end
    local count = 0
    for id, item in pairs(batch.items) do
        if not WholeNumber(id) or id == 0 or type(item) ~= "table" or not WholeNumber(item.q)
            or item.failure ~= nil and item.failure ~= "incomplete"
            or item.p ~= nil and (type(item.p) ~= "number" or item.p ~= item.p or item.p <= 0 or item.p == huge)
            or item.q > 0 and item.p == nil then return false end
        if batch.dv == 1 then
            if type(item.d) ~= "table" then return false end
            local total, last = 0, 0
            local entries = 0
            for index in pairs(item.d) do
                if not WholeNumber(index) or index < 1 or index > #item.d then return false end
                entries = entries + 1
            end
            if entries ~= #item.d then return false end
            for _, level in ipairs(item.d) do
                if type(level) ~= "table" or type(level[1]) ~= "number" or level[1] ~= level[1]
                    or level[1] <= last or level[1] == huge or not WholeNumber(level[2]) or level[2] == 0 then return false end
                last = level[1]
                total = total + level[2]
            end
            if total ~= item.q then return false end
        end
        count = count + 1
    end
    return count <= batch.expected
end

local function PruneLegacyBatch(batch)
    if batch.dv ~= 1 or batch.mk ~= MarketKey() or not ValidSavedBatch(batch) then return end
    local db = ScanDB()
    local old = db.auctionFullScan
    if type(old) ~= "table" then return end
    local realm = _G.GetRealmName and _G.GetRealmName()
    local faction = _G.UnitFactionGroup and _G.UnitFactionGroup("player")
    local legacy = realm and faction and realm .. ":" .. faction
    if old.mk ~= batch.mk and old.mk ~= legacy then return end
    if type(db.auctionFullScans) == "table" and old.mk ~= batch.mk then db.auctionFullScans[old.mk] = nil end
    db.auctionFullScan = nil
end

local function OwnSnapshotStatus()
    if SelectMarket then SelectMarket() end
    local batch = fullBatch
    local failure = batch and FullBatchFailure(batch)
    if failure and failure ~= "unverified" then ReleaseFullBatch(failure); batch = nil end
    local meta = batch or fullFailure
    local forced = AB.ForceExpiredActive()
    local key = MarketKey()
    local matched = key and meta and meta.mk == key
    local staleUsable = forced and matched and meta.failure == "expired"
    local staleItems = type(meta) == "table" and meta.failure == "expired" and type(meta.items) == "table" and next(meta.items) ~= nil
    local status = batch and (failure == "unverified" and "mismatch" or "available")
        or meta and not matched and "mismatch"
        or staleUsable and "available"
        or meta and (meta.failure == "expired" and "expired" or meta.snapshotStatus == "missing" and "missing" or "invalid") or "missing"
    return {
        status = status,
        observedAt = meta and meta.t,
        marketKey = meta and meta.mk,
        expiresAt = meta and meta.t and meta.t + SupplyMaxAge(),
        forced = (forced and (matched and batch ~= nil or staleUsable)) or nil,
        canForce = (matched and not batch and meta.failure == "expired") or nil,
        staleIncomplete = (matched and meta.failure == "expired" and not staleItems) or nil,
        restored = restoredSnapshot,
        completedAt = batch and batch.completedAt,
    }
end

function AB.FullScanSnapshotStatus()
    local own = OwnSnapshotStatus()
    if own.status ~= "available" then
        local eb = getEasyBridge()
        local ea = eb and eb.Snapshot and eb.Snapshot()
        if type(ea) == "table" then
            if ea.status == "available" then return ea end
            if AB.ForceExpiredActive() then
                local forced = {}
                for key, value in pairs(ea) do forced[key] = value end
                forced.status, forced.forced = "available", true
                return forced
            end
            return ea
        end
    end
    return own
end

local function OwnRecord(id)
    if SelectMarket then SelectMarket() end
    local batch = fullBatch
    if batch then
        local failure = FullBatchFailure(batch)
        if failure == "unverified" then return { mk = batch.mk, ob = batch.ob, failure = failure } end
        if failure then ReleaseFullBatch(failure); batch = nil end
    end
    if not batch then
        if AB.ForceExpiredActive() and type(fullFailure) == "table" and fullFailure.mk == MarketKey() and fullFailure.failure == "expired"
            and type(fullFailure.items) == "table" and next(fullFailure.items) ~= nil then
            local item = fullFailure.items[id]
            local dEntry = item and getDenoisedItem(fullFailure, id)
            return {
                q = dEntry and dEntry.quantity or (item and item.q or 0),
                rawQuantity = dEntry and dEntry.rawQuantity or (item and item.q or 0),
                trimmedQuantity = dEntry and dEntry.trimmedQuantity or 0,
                p = dEntry and dEntry.p or (item and item.p),
                t = fullFailure.t,
                mk = fullFailure.mk,
                ob = fullFailure.ob,
                c = not (item and item.failure),
                failure = item and item.failure,
                ox = fullFailure.ox ~= false,
                s = "client-auction-results",
                v = SnapshotVersion(),
                method = "auctionator-full-scan",
            }
        end
        return fullFailure
    end
    if AB.ReplicateScanReady and AB.ReplicateScanReady() ~= true then
        return fullFailure or { mk = batch.mk, ob = batch.ob, failure = "unverified" }
    end
    local item = batch.items[id]
    if item ~= nil and type(item) ~= "table" then
        return { mk = batch.mk, ob = batch.ob, failure = "incomplete" }
    end
    if not item and batch.c ~= true then
        return { mk = batch.mk, ob = batch.ob, failure = "incomplete" }
    end
    local dEntry = item and getDenoisedItem(batch, id)
    return {
        q = dEntry and dEntry.quantity or (item and item.q or 0),
        rawQuantity = dEntry and dEntry.rawQuantity or (item and item.q or 0),
        trimmedQuantity = dEntry and dEntry.trimmedQuantity or 0,
        p = dEntry and dEntry.p or (item and item.p),
        t = batch.t,
        mk = batch.mk,
        ob = batch.ob,
        c = batch.c == true and not (item and item.failure),
        ox = batch.ox,
        s = "client-auction-results",
        v = SnapshotVersion(),
        failure = item and item.failure or batch.c ~= true and "incomplete" or nil,
        method = "auctionator-full-scan",
    }
end

local function SupplyRecord(id)
    local rec = OwnRecord(id)
    local eb = getEasyBridge()
    local ea = eb and eb.Record and eb.Record(id)
    if type(rec) == "table" and not rec.failure then
        if (tonumber(rec.q) or 0) == 0 and (tonumber(rec.rawQuantity) or 0) == 0 and type(ea) == "table"
            and (tonumber(ea.q) or 0) > 0
            and tonumber(ea.t) and tonumber(rec.t) and ea.t > rec.t then return ea end
        return rec
    end
    if type(ea) == "table" then return ea end
    return rec
end

function AB.SupplyRevision()
    local eb = getEasyBridge()
    local info = eb and eb.Snapshot and eb.Snapshot()
    if type(info) == "table" and tonumber(info.observedAt) then
        return supplyRevision + tonumber(info.observedAt)
    end
    return supplyRevision
end

function AB.GetAuctionSupplyStatus(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local rec = SupplyRecord(id)
    if type(rec) ~= "table" then return "unknown" end
    local now = Now()
    if rec.ea then
        if rec.failure then return rec.failure end
        if rec.c ~= true then return "incomplete" end
        local stamp = tonumber(rec.t)
        if not stamp or stamp <= 0 or stamp > now then return "expired" end
        if now - stamp > SupplyMaxAge() and not AB.ForceExpiredActive() then return "expired" end
        return "verified"
    end
    local qty, stamp = tonumber(rec.q), tonumber(rec.t)
    if rec.failure then return rec.failure end
    if not MarketKey() or rec.mk ~= MarketKey() then return "unverified" end
    if rec.c ~= true or type(rec.ox) ~= "boolean" or rec.s ~= "client-auction-results" then return "incomplete" end
    if not qty or qty < 0 or qty == huge or qty ~= floor(qty) then return "incomplete" end
    if not stamp or stamp ~= stamp or stamp <= 0 or stamp > now then return "expired" end
    if now - stamp > SupplyMaxAge() and not AB.ForceExpiredActive() then return "expired" end
    return "verified"
end

function AB.GetAuctionSupply(id, live)
    if AB.GetAuctionSupplyStatus(id) ~= "verified" then return nil end
    local rec = SupplyRecord(id)
    return {
        quantity = tonumber(rec.q),
        rawQuantity = tonumber(rec.rawQuantity ~= nil and rec.rawQuantity or rec.q),
        trimmedQuantity = tonumber(rec.trimmedQuantity) or 0,
        observedAt = tonumber(rec.t) or 0,
        complete = rec.c == true,
        ownerExcluded = rec.ox == true,
        source = rec.s or "client-auction-results",
        market = tonumber(rec.p),
        marketKey = rec.mk,
        observer = rec.ob,
        method = rec.method,
        schemaVersion = rec.v,
        forced = AB.ForceExpiredActive() or nil,
        expiresAt = max(tonumber(rec.t) or 0, AB.ForceExpiredActive() and Now() or 0) + SupplyMaxAge(),
    }
end

function AB.SupplyFresh(id)
    return AB.GetAuctionSupply(id)
end

function AB.GetAuctionDepth(id)
    if AB.GetAuctionSupplyStatus(id) ~= "verified" then return end
    local rec = SupplyRecord(id)
    if type(rec) == "table" and rec.ea then return end
    local batch = fullBatch or (AB.ForceExpiredActive() and fullFailure)
    if not batch or batch.dv ~= 1 then return end
    local item = type(batch.items) == "table" and batch.items[id] or nil
    local dEntry = item and getDenoisedItem(batch, id)
    local levels = {}
    for i, row in ipairs(dEntry and dEntry.levels or {}) do
        levels[i] = { row[1], row[2] }
    end
    return {
        levels = levels,
        quantity = dEntry and dEntry.quantity or 0,
        rawQuantity = item and item.q or 0,
        trimmedQuantity = dEntry and dEntry.trimmedQuantity or 0,
        trimmedLots = dEntry and dEntry.trimmedLots or 0,
        denoised = true,
        observedAt = batch.t,
        marketKey = batch.mk,
        version = 1,
    }
end

function AB.SupplyEstimate(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local A = _G.Auctionator
    if type(A) ~= "table" or type(A.Database) ~= "table" then return nil end
    local db = A.Database.db
    if type(db) ~= "table" then return nil end
    local entry = db[tostring(id)]
    if type(entry) ~= "table" then return nil end
    local scanDay = nil
    if type(A.Constants) == "table" and tonumber(A.Constants.SCAN_DAY_0) then
        scanDay = floor((Now() - A.Constants.SCAN_DAY_0) / 86400)
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
    local day0 = A.Constants and A.Constants.SCAN_DAY_0
    local observedAt = (day and day0) and day * 86400 + day0 or nil
    return {
        quantity = qty,
        observedAt = observedAt or 0,
        complete = false,
        ownerExcluded = false,
        source = "auctionator-update",
        market = tonumber(entry.m),
    }
end

function AB.GetAuctionSupplyHistory(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local A = _G.Auctionator
    if type(A) ~= "table" or type(A.Database) ~= "table" then return nil end
    local db = A.Database
    if type(db) ~= "table" or type(db.GetPriceHistory) ~= "function" then return nil end
    local ok, rows = pcall(db.GetPriceHistory, db, tostring(id))
    if not ok or type(rows) ~= "table" then return nil end
    local best, newest
    for _, row in ipairs(rows) do
        if type(row) == "table" then
            local day = tonumber(row.rawDay)
            local avail = tonumber(row.available)
            if avail and avail >= 0 and day and (newest == nil or day > newest) then
                best, newest = row, day
            end
        end
    end
    if not best or newest == nil then return nil end
    local day0 = type(A.Constants) == "table" and tonumber(A.Constants.SCAN_DAY_0) or nil
    return {
        quantity = tonumber(best.available),
        observedAt = day0 and (newest * 86400 + day0) or 0,
        complete = false,
        source = "auctionator-history",
    }
end

function AB.GetAuctionPriceObservedAt(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local rec = SupplyRecord(id)
    if type(rec) == "table" and (rec.ea or rec.mk == MarketKey()) and tonumber(rec.p) and rec.p > 0
        and tonumber(rec.t) and rec.t > 0 then return tonumber(rec.t) end
    local est = AB.SupplyEstimate(id)
    if type(est) == "table" and tonumber(est.observedAt) and est.observedAt > 0 then
        return tonumber(est.observedAt)
    end
    return nil
end

local fullBus, fullListener, fullEvents, fullRead, fullTimer, fullWatchdog
local fullGeneration = 0
local fullState = { status = "unavailable" }

local function StopFullImport()
    fullGeneration = fullGeneration + 1
    if fullTimer then fullTimer:Cancel(); fullTimer = nil end
    if fullWatchdog then fullWatchdog:Cancel(); fullWatchdog = nil end
    fullRead = nil
end

local function ScheduleFullExpiry()
    if fullExpiryTimer then fullExpiryTimer:Cancel(); fullExpiryTimer = nil end
    if not fullBatch then return end
    local failure = FullBatchFailure(fullBatch)
    if failure then
        if failure ~= "unverified" then ReleaseFullBatch(failure) end
        return
    end
    local ct = _G.C_Timer
    if not (type(ct) == "table" and type(ct.NewTimer) == "function") then return end
    local token = {}
    fullExpiryToken = token
    fullExpiryTimer = ct.NewTimer(max(1, fullBatch.t + SupplyMaxAge() + 1 - Now()), function()
        if fullExpiryToken ~= token then return end
        fullExpiryTimer = nil
        if not fullBatch then return end
        local failure2 = FullBatchFailure(fullBatch)
        if failure2 and failure2 ~= "unverified" then ReleaseFullBatch(failure2); SupplyChanged(nil)
        else ScheduleFullExpiry() end
    end)
end

function AB.FullScanStatus() return fullState end

local function ScanStatusChanged()
    for _, fn in ipairs(supplyListeners) do pcall(fn, nil, "scan-status") end
end

local function ImportFailed(status)
    StopFullImport()
    fullState = { status = status }
    if not fullBatch and not fullFailure then ReleaseFullBatch("incomplete", nil, "missing") end
    ScanStatusChanged()
end

local function ExpectedFullRows(scan)
    if scan.expected ~= nil then return end
    local ok, count, total
    if scan.modern then
        local ah = _G.C_AuctionHouse
        local fn = type(ah) == "table" and ah.GetNumReplicateItems
        if type(fn) == "function" then ok, count = pcall(fn) end
    elseif type(_G.GetNumAuctionItems) == "function" then
        ok, count, total = pcall(_G.GetNumAuctionItems, "list")
    end
    if ok and WholeNumber(count) and (total == nil or total == count) then
        scan.expected = count
        local now = Now()
        scan.observedAt = now > 0 and now or scan.startedAt
    end
end

local function FullRow(scan, row)
    if type(row) ~= "table" then scan.complete = false; return end
    local info = row.auctionInfo or row.replicateInfo
    if type(info) ~= "table" then scan.complete = false; return end
    local linkID = type(row.itemLink) == "string" and tonumber(row.itemLink:match("item:(%d+)"))
    local id = info[17]
    if not WholeNumber(id) or id == 0 then id = linkID end
    if not WholeNumber(id) or id == 0 or linkID and linkID ~= id then scan.complete = false; return end
    local item = scan.items[id]
    if not item then item = { q = 0 }; scan.items[id] = item end
    local qty = info[3]
    local classic = info[17] ~= nil or info[18] ~= nil or row.replicateInfo ~= nil
        or type(info[14]) == "string" or type(info[15]) == "string"
    local buyout = info[classic and 10 or 9]
    if not WholeNumber(qty) or type(buyout) ~= "number" or buyout ~= buyout
        or buyout < 0 or buyout == huge then item.failure = "incomplete"; return end
    if qty == 0 or buyout == 0 then return end
    local oldQty = item.q
    local newQty = oldQty + qty
    item.p = ((item.p or 0) * oldQty + buyout) / newQty
    item.q = newQty
    item.d = item.d or {}
    local unit = buyout / qty
    item.d[unit] = (item.d[unit] or 0) + qty
end

local function ImportFullRows(scan, rows)
    if type(rows) ~= "table" or scan.expected == nil then
        ImportFailed("incomplete")
        return
    end
    scan.items = {}
    scan.complete = true
    scan.index = 1
    local rowCount = 0
    for index in pairs(rows) do
        if not WholeNumber(index) or index < 1 then scan.complete = false end
        rowCount = rowCount + 1
    end
    if rowCount ~= scan.expected then scan.complete = false end
    fullState = { status = "processing", done = 0, total = scan.expected, startedAt = Now() }
    local lastDecile = 0
    local generation = fullGeneration
    local function Clock()
        if type(_G.debugprofilestop) == "function" then return _G.debugprofilestop() end
        if type(_G.GetTime) == "function" then return _G.GetTime() * 1000 end
        return 0
    end
    local function step()
        if generation ~= fullGeneration then return end
        fullTimer = nil
        if not scan.mk or scan.mk ~= MarketKey() then
            ImportFailed("unverified")
            return
        end
        local startAt = Clock()
        local index = scan.index
        local counter = 0
        while index <= scan.expected do
            FullRow(scan, rows[index])
            index = index + 1
            counter = counter + 1
            if counter >= 3000 then break end
            if counter % 64 == 0 and Clock() - startAt >= 8 then break end
        end
        scan.index = index
        fullState.done = index - 1
        local decile = scan.expected > 0 and floor((index - 1) / scan.expected * 10) or 10
        if decile ~= lastDecile then lastDecile = decile; ScanStatusChanged() end
        if scan.index <= scan.expected then
            local ct = _G.C_Timer
            if type(ct) == "table" and type(ct.NewTimer) == "function" then
                fullTimer = ct.NewTimer(0, step)
            else
                ImportFailed("unavailable")
            end
            return
        end
        local enabled, mode = AB.ObserveReplicateMode()
        if enabled ~= true or not mode then return end
        if mode.generation ~= scan.modeGeneration or mode.scanSerial ~= scan.scanSerial then
            ImportFailed("unverified")
            return
        end
        if not scan.complete then ImportFailed("incomplete"); return end
        if not scan.depthIDs then
            scan.depthIDs = {}
            scan.depthIndex = 1
            for id in pairs(scan.items) do scan.depthIDs[#scan.depthIDs + 1] = id end
        end
        local depthLast = min(scan.depthIndex + 799, #scan.depthIDs)
        for idx = scan.depthIndex, depthLast do
            local item = scan.items[scan.depthIDs[idx]]
            local prices, depth = {}, {}
            for price in pairs(item.d or {}) do prices[#prices + 1] = price end
            table.sort(prices)
            for _, price in ipairs(prices) do depth[#depth + 1] = { price, item.d[price] } end
            item.d = depth
            if item.q > 0 then
                local robust = AB.RobustFloorPrice(item.d)
                if type(robust) == "number" and robust > 0 then
                    item.p = robust
                elseif item.d[1] and type(item.d[1][1]) == "number" and item.d[1][1] > 0 then
                    item.p = item.d[1][1]
                end
            end
        end
        scan.depthIndex = depthLast + 1
        if scan.depthIndex <= #scan.depthIDs then
            local ct = _G.C_Timer
            if type(ct) == "table" and type(ct.NewTimer) == "function" then
                fullTimer = ct.NewTimer(0, step)
            else
                ImportFailed("unavailable")
            end
            return
        end
        local completedAt = Now()
        if completedAt < scan.observedAt then completedAt = scan.observedAt end
        local candidate = {
            items = scan.items,
            t = scan.observedAt,
            mk = scan.mk,
            ob = scan.ob,
            dv = 1,
            c = true,
            v = SnapshotVersion(),
            s = "client-auction-results",
            ox = false,
            completedAt = completedAt,
            expected = scan.expected,
            received = rowCount,
        }
        if not ValidSavedBatch(candidate) or not StoreBatch(candidate) then
            ImportFailed("incomplete")
            return
        end
        PruneLegacyBatch(candidate)
        fullBatch = candidate
        fullFailure = nil
        restoredSnapshot = false
        ScheduleFullExpiry()
        fullState.status = scan.complete and "complete" or "incomplete"
        fullState.observedAt = scan.observedAt
        fullRead = nil
        Say(format(tr("扫描数据已就绪（%d 种物品），可以重新计算路线了。"), #scan.depthIDs))
        SupplyChanged(nil)
    end
    local ct = _G.C_Timer
    if type(ct) == "table" and type(ct.NewTimer) == "function" then
        fullTimer = ct.NewTimer(0, step)
    else
        ImportFailed("unavailable")
    end
end

local function DisconnectFullScan()
    if fullBus and fullBus.Unregister then pcall(fullBus.Unregister, fullBus, fullListener, fullEvents) end
    fullBus, fullListener, fullEvents = nil, nil, nil
    StopFullImport()
end

function AB.ConnectAuctionatorStock()
    local enabled = AB.ReplicateScanEnabled()
    if enabled ~= true then
        if fullBus or fullRead or fullTimer then DisconnectFullScan() end
        fullState = { status = enabled == false and "summary" or "unavailable" }
        return false
    end
    local A = _G.Auctionator
    local bus = type(A) == "table" and A.EventBus
    local ev = type(A) == "table" and A.FullScan and A.FullScan.Events
    if type(bus) ~= "table" or type(bus.Register) ~= "function" or type(ev) ~= "table"
        or type(ev.ScanStart) ~= "string" or type(ev.ScanComplete) ~= "string"
        or type(ev.ScanProgress) ~= "string" or type(ev.ScanFailed) ~= "string" then return false end
    if fullBus == bus then return true end
    DisconnectFullScan()
    local listener = {}
    function listener:ReceiveEvent(event, data)
        if self ~= fullListener then return end
        local enabled2, mode = AB.ObserveReplicateMode()
        if enabled2 ~= true or self ~= fullListener then return end
        if event == ev.ScanStart then
            SelectMarket()
            if not MarketKey() then ImportFailed("unverified"); return end
            StopFullImport()
            mode.scanSerial = mode.scanSerial + 1
            fullRead = {
                startedAt = Now(),
                mk = MarketKey(),
                ob = ObserverKey(),
                modern = ev.ScanStart == "replicate_scan_start",
                modeGeneration = mode.generation,
                scanSerial = mode.scanSerial,
            }
            local token = fullRead
            fullState = { status = "scanning", pct = 0, startedAt = token.startedAt }
            local ct = _G.C_Timer
            if type(ct) == "table" and type(ct.NewTimer) == "function" then
                fullWatchdog = ct.NewTimer(ScanSilentSec(), function()
                    fullWatchdog = nil
                    if fullRead ~= token or token.gotRows then return end
                    if fullState.status ~= "scanning" then return end
                    StopFullImport()
                    fullState = { status = "noresponse", startedAt = token.startedAt }
                    ScanStatusChanged()
                end)
            end
            ScanStatusChanged()
        elseif event == ev.ScanProgress and fullRead and type(data) == "number" then
            if fullState.status == "scanning" then
                local before = floor((tonumber(fullState.pct) or 0) * 10)
                fullState.pct = data
                if floor(data * 10) ~= before then ScanStatusChanged() end
            end
            if data >= 0.2 then
                fullRead.gotRows = true
                if fullWatchdog then fullWatchdog:Cancel(); fullWatchdog = nil end
                ExpectedFullRows(fullRead)
            end
        elseif event == ev.ScanFailed then
            ImportFailed("failed")
        elseif event == ev.ScanComplete and fullRead and fullState.status == "scanning" then
            ImportFullRows(fullRead, data)
        end
    end
    local events = { ev.ScanStart, ev.ScanProgress, ev.ScanFailed, ev.ScanComplete }
    local ok = pcall(bus.Register, bus, listener, events)
    if not ok then return false end
    fullBus, fullListener, fullEvents = bus, listener, events
    fullState = { status = "ready" }
    return true
end

SelectMarket = function()
    local key = MarketKey()
    if currentMarket == key then return end
    StopFullImport()
    if fullExpiryTimer then fullExpiryTimer:Cancel(); fullExpiryTimer = nil end
    fullExpiryToken = nil
    forcedUntil = 0
    currentMarket = key
    fullBatch = nil
    fullFailure = nil
    restoredSnapshot = false
    fullState = { status = fullBus and "ready" or "unavailable" }
    local db = ScanDB()
    local saved = key and type(db.auctionFullScans) == "table" and db.auctionFullScans[key] or nil
    if saved == nil then saved = db.auctionFullScan end
    if saved == nil then return end
    restoredSnapshot = true
    if ValidSavedBatch(saved) then
        if key and type(db.auctionFullScans) == "table" and db.auctionFullScans[key] == saved then PruneLegacyBatch(saved) end
        fullBatch = saved
        ScheduleFullExpiry()
    elseif type(saved) == "table" and saved.v == SnapshotVersion() and saved.items == nil
        and saved.failure == "incomplete" and saved.snapshotStatus == "missing" then
        fullFailure = saved
    elseif type(saved) == "table" and saved.v == SnapshotVersion()
        and saved.failure == "expired" and WholeNumber(saved.t) and saved.t > 0
        and Now() - saved.t > SupplyMaxAge() then
        fullFailure = saved
    else
        ReleaseFullBatch("incomplete", saved)
    end
end

local function InitializeAuctionatorStock()
    local db = ScanDB()
    db.auctionReplicateGate = nil
    db.replicateRequiredAfter = nil
    SelectMarket()
    AB.ConnectAuctionatorStock()
    AB.ObserveReplicateMode()
    AB.HookReplicateModeSetting()
    if type(_G.CreateFrame) ~= "function" then return end
    local ok, frame = pcall(_G.CreateFrame, "Frame")
    if not ok or type(frame) ~= "table" then return end
    frame:RegisterEvent("ADDON_LOADED")
    frame:RegisterEvent("PLAYER_LOGIN")
    frame:SetScript("OnEvent", function(_, event, name)
        if event == "PLAYER_LOGIN" or name == "Auctionator" then
            AB.ConnectAuctionatorStock()
            AB.ObserveReplicateMode()
            AB.HookReplicateModeSetting()
        end
    end)
end

function AB.ReplicateScanEnabled()
    local a = _G.Auctionator
    local cfg = type(a) == "table" and a.Config
    if type(cfg) ~= "table"
        or type(cfg.Get) ~= "function"
        or type(cfg.Options) ~= "table"
        or type(cfg.Options.REPLICATE_SCAN) ~= "string" then
        return nil
    end
    local ok, enabled = pcall(cfg.Get, cfg.Options.REPLICATE_SCAN)
    if ok and type(enabled) == "boolean" then
        return enabled
    end
    return nil
end

local hookedModeConfig

function AB.ObserveReplicateMode()
    local enabled = AB.ReplicateScanEnabled()
    if enabled == nil then AB.ConnectAuctionatorStock(); return nil, nil end
    local state = replicateState
    local changed = false
    if not state then
        state = { enabled = enabled, generation = 1, scanSerial = 0 }
        replicateState = state
    elseif state.enabled ~= enabled then
        state.enabled = enabled
        state.generation = state.generation + 1
        StopFullImport()
        fullState = { status = "mode-changed" }
        changed = true
    end
    AB.ConnectAuctionatorStock()
    if changed then
        ScanStatusChanged()
        for _, fn in ipairs(supplyListeners) do pcall(fn, nil, "replicate-mode") end
    end
    return enabled, state
end

function AB.ReplicateScanReady()
    if AB.FullScanSnapshotStatus().status == "available" then return true end
    local eb = getEasyBridge()
    if eb and eb.Available and eb.Available() then return false, "easyauctionStale" end
    local enabled = AB.ObserveReplicateMode()
    if enabled == nil then return nil, "replicateModeUnknown" end
    if not enabled then return false, "replicateModeDisabled" end
    return false, "replicateScanRequired"
end

function AB.HookReplicateModeSetting()
    local a = _G.Auctionator
    local cfg = type(a) == "table" and a.Config
    if type(cfg) ~= "table" or type(cfg.Set) ~= "function" then return false end
    if cfg == hookedModeConfig then return true end
    if type(_G.hooksecurefunc) ~= "function" then return false end
    local ok = pcall(_G.hooksecurefunc, cfg, "Set", function(option)
        if cfg.Options and option == cfg.Options.REPLICATE_SCAN then
            AB.ObserveReplicateMode()
        end
    end)
    if ok then hookedModeConfig = cfg end
    return ok
end

function AB.ClearSavedScans()
    StopFullImport()
    local db = ScanDB()
    db.auctionFullScan = nil
    db.auctionFullScans = nil
    if fullExpiryTimer then fullExpiryTimer:Cancel(); fullExpiryTimer = nil end
    fullExpiryToken = nil
    forcedUntil = 0
    fullBatch = nil
    fullFailure = nil
    restoredSnapshot = false
    currentMarket = false
    SelectMarket()
    supplyRevision = supplyRevision + 1
    for _, fn in ipairs(supplyListeners) do pcall(fn, nil, "supply") end
    local ra = getRouteAuto()
    if ra and type(ra.NotifyPricesChanged) == "function" then pcall(ra.NotifyPricesChanged) end
    return true
end

local initFn = getInit()
if type(initFn) == "function" then
    initFn(InitializeAuctionatorStock)
else
    InitializeAuctionatorStock()
end
