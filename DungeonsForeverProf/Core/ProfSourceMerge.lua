local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local M = { DataSchema = 2 }
ns.ProfSourceMerge = M
if type(gns) == "table" and gns ~= ns then
    gns.ProfSourceMerge = M
end

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function ZoneName(areaID)
    if type(areaID) ~= "number" or areaID <= 0 then return "" end
    local DS = getDS()
    if DS and type(DS.RawText) == "function" then
        local raw = DS.RawText("zone", areaID)
        if type(raw) == "string" and raw ~= "" then return raw end
    end
    if type(_G.C_Map) == "table" and type(_G.C_Map.GetAreaInfo) == "function" then
        local ok, nm = pcall(_G.C_Map.GetAreaInfo, areaID)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    if DS and type(DS.ZoneName) == "function" then
        return DS.ZoneName(areaID)
    end
    return ""
end

local function copyList(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local v = raw[i]
        if type(v) == "table" then
            local cp = {}
            for k, val in pairs(v) do
                if type(val) == "table" then
                    local sub = {}
                    for sk, sv in pairs(val) do
                        if type(sv) == "table" then
                            local sub2 = {}
                            for s2k, s2v in pairs(sv) do sub2[s2k] = s2v end
                            sub[sk] = sub2
                        else
                            sub[sk] = sv
                        end
                    end
                    cp[k] = sub
                else
                    cp[k] = val
                end
            end
            out[#out + 1] = cp
        else
            out[#out + 1] = v
        end
    end
    return out
end

local function copyCurrencies(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local c = raw[i]
        if type(c) == "table" then
            local cid = tonumber(c.currencyID or c.id)
            local amt = tonumber(c.amount ~= nil and c.amount or c.count) or 0
            if cid and cid > 0 then
                out[#out + 1] = {
                    currencyID = cid,
                    amount = amt,
                    id = cid,
                    count = amt,
                }
            end
        end
    end
    return out
end

local function copyCostItems(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local it = raw[i]
        if type(it) == "table" then
            local iid = tonumber(it.itemID or it.id)
            local cnt = tonumber(it.count ~= nil and it.count or it.amount) or 1
            if iid and iid > 0 then
                out[#out + 1] = {
                    itemID = iid,
                    count = cnt,
                    id = iid,
                }
            end
        end
    end
    return out
end

local function normalizeSide(f)
    if f == "A" or f == "Alliance" then return "a" end
    if f == "H" or f == "Horde" then return "h" end
    if f == "N" or f == "Neutral" then return "n" end
    return nil
end

local function vendorEntry(o, DS)
    local npcID = tonumber(o.npcID or o.id)
    local npc = npcID and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
    local npcName = npcID and type(DS.NpcName) == "function" and DS.NpcName(npcID) or nil
    local spawns = npc and copyList(npc.spawns) or {}
    local firstArea = type(spawns[1]) == "table" and spawns[1].areaID or o.areaID or o.area
    local zone = firstArea and ZoneName(firstArea) or ""
    local currencies = copyCurrencies(o.currencies)
    local costItems = copyCostItems(o.costItems)
    local hasExt = (#currencies > 0 or #costItems > 0 or o.hasExtendedCost == true)
    local bundle = o.bundleSize or o.quantity or 1
    local price = o.priceCopper ~= nil and o.priceCopper or o.price
    local stock = o.maxStock ~= nil and o.maxStock or o.stock
    return {
        id = npcID,
        npcID = npcID,
        name = npcName,
        optionIndex = o.optionIndex,
        faction = npc and npc.faction or o.faction,
        side = normalizeSide(npc and npc.faction or o.faction),
        price = price,
        priceCopper = price,
        quantity = bundle,
        bundleSize = bundle,
        stock = stock,
        maxStock = stock,
        priceVerified = o.priceVerified == true,
        currencies = currencies,
        costItems = costItems,
        hasExtendedCost = hasExt,
        cur = (#currencies > 0 and currencies[1].currencyID) or 0,
        amt = (#currencies > 0 and currencies[1].amount) or 0,
        conditions = copyList(o.conditions),
        accessConditions = npc and copyList(npc.accessConditions) or {},
        spawns = spawns,
        area = firstArea,
        areaID = firstArea,
        zone = (zone ~= "" and zone) or nil,
    }
end

local function dropEntry(d, DS)
    local npcID = tonumber(d.npcID or d.id)
    local npc = npcID and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
    local npcName = npcID and type(DS.NpcName) == "function" and DS.NpcName(npcID) or d.npc
    local areaID = d.areaID or d.area
    local zone = areaID and ZoneName(areaID) or ""
    return {
        id = npcID,
        npcID = npcID,
        npc = npcName,
        chance = d.dropRatePct ~= nil and d.dropRatePct or d.pct,
        dropRatePct = d.dropRatePct ~= nil and d.dropRatePct or d.pct,
        sampleCount = d.sampleCount,
        avgStack = d.avgStack,
        minLevel = d.minLevel,
        maxLevel = d.maxLevel,
        area = areaID,
        areaID = areaID,
        zone = (zone ~= "" and zone) or nil,
        isWorldDrop = d.isWorldDrop == true,
        faction = npc and npc.faction or nil,
        classification = npc and npc.classification or nil,
    }
end

local function extraEntry(e, DS)
    local out = {
        itemID = e.itemID,
        sourceKind = e.sourceKind,
        targetType = e.targetType,
        targetID = e.targetID,
        dropRatePct = e.dropRatePct,
        chance = e.dropRatePct,
        sampleCount = e.sampleCount,
        avgStack = e.avgStack,
    }
    if e.targetType == "npc" and type(e.targetID) == "number" then
        local npc = type(DS.Npc) == "function" and DS.Npc(e.targetID) or nil
        out.npcID = e.targetID
        out.targetName = type(DS.NpcName) == "function" and DS.NpcName(e.targetID) or nil
        out.faction = npc and npc.faction or nil
        out.spawns = npc and copyList(npc.spawns) or {}
        local areaID = type(out.spawns[1]) == "table" and out.spawns[1].areaID or nil
        out.areaID = areaID
        local z = areaID and ZoneName(areaID) or ""
        if z ~= "" then out.zone = z end
    elseif e.targetType == "object" and type(e.targetID) == "number" then
        local obj = type(DS.Object) == "function" and DS.Object(e.targetID) or nil
        out.objectID = e.targetID
        out.targetName = type(DS.ObjectName) == "function" and DS.ObjectName(e.targetID) or nil
        out.objectType = obj and obj.objectType or nil
        out.reqSkill = obj and obj.reqSkill or nil
        out.areaIDs = obj and copyList(obj.areaIDs) or {}
        local areaID = out.areaIDs[1]
        out.areaID = areaID
        local z = areaID and ZoneName(areaID) or ""
        if z ~= "" then out.zone = z end
    elseif e.targetType == "zone" and type(e.targetID) == "number" then
        local zObj = type(DS.Zone) == "function" and DS.Zone(e.targetID) or nil
        local z = ZoneName(e.targetID)
        out.areaID = e.targetID
        out.targetName = (z ~= "" and z) or nil
        out.zone = out.targetName
        out.uiMapID = zObj and zObj.uiMapID or nil
        out.parentAreaID = zObj and zObj.parentAreaID or nil
        out.isCapital = zObj and zObj.isCapital or nil
        out.faction = zObj and zObj.faction or nil
    elseif e.targetType == "item" and type(e.targetID) == "number" then
        local it = type(DS.Item) == "function" and DS.Item(e.targetID) or nil
        out.containerItemID = e.targetID
        out.targetName = type(DS.ItemName) == "function" and DS.ItemName(e.targetID) or nil
        out.quality = it and it.quality or nil
        out.bindType = it and it.bindType or nil
    end
    return out
end

function M.SourceOf(itemID)
    if type(itemID) ~= "number" or itemID <= 0 then return nil end
    local DS = getDS()
    if not DS then return nil end

    local vo = type(DS.VendorOffers) == "function" and DS.VendorOffers(itemID) or nil
    local drops = type(DS.Drops) == "function" and DS.Drops(itemID) or nil
    local extras = type(DS.ExtraSources) == "function" and DS.ExtraSources(itemID) or nil

    local hasVo = type(vo) == "table" and type(vo.offers) == "table" and #vo.offers > 0
    local hasDrops = type(drops) == "table" and #drops > 0
    local hasExtras = type(extras) == "table" and #extras > 0
    if not hasVo and not hasDrops and not hasExtras then return nil end

    local out = {
        commonVendorCount = type(vo) == "table" and vo.commonVendorCount or nil,
        vendors = {},
        drops = {},
        extraSources = {},
    }
    if hasVo then
        for i = 1, #vo.offers do
            local o = vo.offers[i]
            if type(o) == "table" then
                out.vendors[#out.vendors + 1] = vendorEntry(o, DS)
            end
        end
    end
    if hasDrops then
        for i = 1, #drops do
            local d = drops[i]
            if type(d) == "table" then
                local entry = dropEntry(d, DS)
                if entry.isWorldDrop then out.worldDrop = true end
                out.drops[#out.drops + 1] = entry
            end
        end
    end
    if hasExtras then
        for i = 1, #extras do
            local e = extras[i]
            if type(e) == "table" then
                out.extraSources[#out.extraSources + 1] = extraEntry(e, DS)
            end
        end
    end
    return out
end

function M.VendorsOf(itemID)
    local src = M.SourceOf(itemID)
    if type(src) == "table" and type(src.vendors) == "table" and #src.vendors > 0 then
        return src.vendors
    end
    return nil
end

function M.Fill(row)
    if type(row) ~= "table" then return nil end
    local existing = row[14] or row.source
    if type(existing) == "table" and existing.__srcDone then return existing end
    local f = row[13]
    local fid = (type(f) == "table" and f[1])
        or row.formula
        or row.formulaID
        or row.teachingItemID
        or row.outputItemID
        or row.itemID
    if type(fid) ~= "number" or fid <= 0 then return existing end
    local src = M.SourceOf(fid)
    if type(src) ~= "table" then return existing end
    if getmetatable(row) == false then
        return src
    end
    src.__srcDone = true
    if row[13] ~= nil or row[14] ~= nil then
        row[14] = src
    else
        row.source = src
    end
    return src
end

local function vendorList(src)
    if type(src) ~= "table" then return nil end
    local vs = src.vendors or src.v or src.offers
    if type(vs) ~= "table" then return nil end
    return vs
end

local function dropList(src)
    if type(src) ~= "table" then return nil end
    local ds = src.drops or src.d
    if type(ds) ~= "table" then return nil end
    return ds
end

function M.Primary(src)
    if type(src) ~= "table" then return nil end
    local vs = vendorList(src)
    if vs then
        local gold, currency = false, false
        for i = 1, #vs do
            local v = vs[i]
            if type(v) == "table" then
                local price = tonumber(v.priceCopper ~= nil and v.priceCopper or v.price) or 0
                local cur = tonumber(v.cur) or 0
                if v.hasExtendedCost or #(v.currencies or {}) > 0 or #(v.costItems or {}) > 0 then
                    currency = true
                elseif price > 0 or (price == 0 and v.priceVerified) then
                    gold = true
                elseif cur ~= 0 then
                    currency = true
                end
            end
        end
        if gold then return "vendor" end
        if currency then return "currency" end
    end
    local ds = dropList(src)
    if ds and #ds > 0 then return "drop" end
    if src.worldDrop then return "drop" end
    local qs = src.quests
    if type(qs) == "table" and #qs > 0 then return "quest" end
    if src.questOnly then return "quest" end
    local es = src.extraSources
    if type(es) == "table" and #es > 0 and type(es[1]) == "table" and type(es[1].sourceKind) == "string" then
        return es[1].sourceKind
    end
    return nil
end

function M.CurrencyCount(src)
    local vs = vendorList(src)
    local n = 0
    if not vs then return n end
    for i = 1, #vs do
        local v = vs[i]
        if type(v) == "table" and (v.hasExtendedCost or (tonumber(v.cur) or 0) ~= 0
            or #(v.currencies or {}) > 0 or #(v.costItems or {}) > 0) then
            n = n + 1
        end
    end
    return n
end
