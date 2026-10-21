-- Materials require independently verified unlimited merchant supply. Formula
-- procurement/display continues to use its separate item/NPC records.
local _, ns = ...
local Prices = {}
ns.ProfItemPrices = Prices

local function Integer(value, minimum)
    return type(value)=="number" and value>=minimum and value<math.huge
        and value==math.floor(value)
end

local function Nonempty(value)
    return value~=nil and (type(value)~="string" or value:find("%S")~=nil)
end

local function NameText(value)
    if type(value)~="string" then return end
    value=value:match("^%s*(.-)%s*$")
    -- Stored display placeholders are not merchant names.
    if value=="" or value:match("^#%d+$") or value:lower():match("npc%s*#%d+$") then return end
    return value
end

local function LocalizedName(name,npcID,canonical)
    name=NameText(name) or NameText(canonical)
    local localized=name and ns.L and NameText(ns.L[name]) or name
    localized=localized or name
    local locale=type(GetLocale)=="function" and GetLocale()
    if localized then
        -- Keep a real source name when no client-language translation is known.
        -- The flag records missing localization without hiding the identity.
        return localized,(locale=="zhCN" or locale=="zhTW") and not localized:find("[\128-\255]") or nil
    end
    if npcID then
        local pattern=ns.L and ns.L["商人 NPC #%d"] or "商人 NPC #%d"
        return string.format(pattern,npcID),true
    end
end

local function Faction(value)
    if value=="Alliance" or value=="a" then return "A" end
    if value=="Horde" or value=="h" then return "H" end
    if value=="n" or value=="Neutral" then return "N" end
    return Nonempty(value) and value or nil
end

-- NPC reputation affiliation is separate from Alliance/Horde access. Its name
-- may be localized by the client even when the webpage only supplied English.
function Prices.GetNPCFaction(npcID)
    local record=ns.ProfVendorFactions and ns.ProfVendorFactions[npcID]
    if type(record)~="table" then return end
    local id=Integer(record.factionID,1) and record.factionID or nil
    local name
    if id then
        local api=C_Reputation and C_Reputation.GetFactionDataByID
        if type(api)=="function" then
            local ok,data=pcall(api,id)
            if ok and type(data)=="table" then name=NameText(data.name) end
        end
        if not name and type(GetFactionInfoByID)=="function" then
            local ok,value=pcall(GetFactionInfoByID,id)
            if ok then name=NameText(value) end
        end
    end
    local names=type(record.names)=="table" and record.names or {}
    local locale=type(GetLocale)=="function" and GetLocale() or "enUS"
    name=name or NameText(names[locale]) or NameText(names.enUS)
    return id,name
end

-- Some enchant catalogues omit the formula item while retaining its spell.
-- Reuse the exported client teaching relationship; pending specialization
-- requirements do not make that independent item -> spell identity unknown.
-- Multiple teaching items remain ambiguous rather than being chosen by name,
-- price, output/scroll ID, or NPC overlap.
function Prices.GetFormulaItemID(spellID,source)
    local explicit=type(source)=="table" and tonumber(source.formulaID)
    if Integer(explicit,1) then return explicit end
    if not Integer(spellID,1) then return end
    local meta=ns.ProfSpecializationsMeta
    local record=ns.ProfSpecializations and ns.ProfSpecializations[spellID]
    if type(meta)~="table" or meta.schemaVersion~=1 or not Nonempty(meta.targetBuild)
        or type(record)~="table" or type(GetBuildInfo)~="function" then return end
    local ok,version,build=pcall(GetBuildInfo)
    if not ok or not version or not build then return end
    local target=tostring(meta.targetBuild)
    if tostring(version)~=target and tostring(version).."."..tostring(build)~=target then return end
    if Nonempty(meta.hotfixBuild) and tostring(build)~=tostring(meta.hotfixBuild) then return end
    local found
    for _,route in ipairs(record.routes or {}) do
        local item=route.itemID
        local path=route.learningPath
        if route.kind=="item" and Integer(item,1) and route.sourceBuild==target
            and (not Nonempty(meta.hotfixBuild) or tostring(route.hotfixBuild)==tostring(meta.hotfixBuild))
            and type(path)=="string" and path:find("Item["..item.."].ClassID=9",1,true)
            and (path:find("SpellID="..spellID.."/TriggerType=6",1,true)
                or (path.." "):match("Effect=36/EffectTriggerSpell="..spellID.."%D")) then
            if found and found~=item then return end
            found=item
        end
    end
    return found
end

local function Quote(itemID, npcID, raw, item, context)
    if not Integer(npcID,1) or type(raw)~="table"
        or raw.npc_id~=nil and raw.npc_id~=npcID then return end
    local side=Faction(raw.side)
    local faction=Faction(context and context.faction or UnitFactionGroup and UnitFactionGroup("player"))
    if side and side~="N" and side~=faction then return end
    if context and context.npcAccess and context.npcAccess[npcID]==false then return end
    local extended=Nonempty(raw.currency_kind) or Nonempty(raw.currency_id) or Nonempty(raw.currency_amount)
    local stock=raw.stock
    local unlimited=stock==-1
    local limited=Integer(stock,0)
    local quantity=Integer(item.VendorStackCount,1) and item.VendorStackCount or nil
    local price=not extended and Integer(raw.cost_copper,0) and quantity and raw.cost_copper or nil
    local source=Nonempty(raw.price_source) and raw.price_source or nil
    local name,untranslated=LocalizedName(raw.name_en,npcID)
    local npcFactionID,npcFactionName=Prices.GetNPCFaction(npcID)
    local offer={itemID=itemID,npcID=npcID,npcName=name,name=name,
        npcNameCanonical=raw.name_en,npcNameUntranslated=untranslated,
        npcFactionID=npcFactionID,npcFactionName=npcFactionName,
        faction=side,areaID=raw.zone_id,quantity=quantity,bundleSize=quantity,
        unlimited=unlimited,limited=limited or nil,maxStock=limited and stock or nil,
        stockStatus=unlimited and "unlimited" or limited and "limited" or "unknown",
        stockUnknown=not unlimited and not limited or nil,
        available=stock~=0,purchasable=true,hasExtendedCost=extended or nil,
        currencyKind=raw.currency_kind,currencyID=raw.currency_id,currencyAmount=raw.currency_amount,
        price=price,unit=price and price/quantity or nil,priceUsable=price~=nil and stock~=0,
        priceSource=source,source=source or "Data_ProfItems",priceBasis="Data_ProfItems",
        reference=true,estimated=false,costText=raw.cost_text,
        availabilitySource="Data_ProfItems",availabilityVerified=Integer(stock,-1),
        url="https://www.wowhead.com/forever/npc="..npcID}
    local loc=ns.ProfVendors and ns.ProfVendors[npcID]
    if loc and (not offer.areaID or offer.areaID==loc[1]) then
        offer.areaID,offer.mapID,offer.x,offer.y=offer.areaID or loc[1],loc[2],loc[3],loc[4]
    elseif offer.areaID then
        offer.mapID=ns.AreaMap and ns.AreaMap[offer.areaID]
    end
    return offer
end

local function Offers(itemID, context, mode)
    local result={}
    local item=ns.ProfItems and ns.ProfItems[itemID]
    if type(item)~="table" or type(item.offers)~="table" then return result end
    for npcID,raw in pairs(item.offers) do
        local offer=Quote(itemID,npcID,raw,item,context)
        if offer and not offer.hasExtendedCost then
            if mode=="formula" or offer.unlimited and offer.available
                and (mode=="supplier" or offer.priceUsable) then
                result[#result+1]=offer
            end
        end
    end
    table.sort(result,function(a,b)
        local ap,bp=a.unit or math.huge,b.unit or math.huge
        if ap~=bp then return ap<bp end
        if a.quantity~=b.quantity then return (a.quantity or 1)<(b.quantity or 1) end
        return a.npcID<b.npcID
    end)
    return result
end

local MaterialRoles={profession_supply=true,trade_supply=true,reagent_supply=true,
    general_goods=true,cooking_supply=true,fishing_supply=true}
local MaterialPriceSources={wowhead_npc_bundle=true,client_base_bundle=true}

function Prices.GetOffers(itemID,context)
    local result={}
    local meta=ns.ProfMaterialSupplyMeta
    local item=ns.ProfMaterialSupply and ns.ProfMaterialSupply[itemID]
    if not Integer(itemID,1) or type(meta)~="table" or meta.schemaVersion~=1
        or type(meta.fingerprint)~="string" or not Nonempty(meta.fingerprint)
        or type(item)~="table" or type(item.offers)~="table" then return result end
    local faction=Faction(context and context.faction or UnitFactionGroup and UnitFactionGroup("player"))
    local accepted={}
    for npcID,raw in pairs(item.offers) do
        local side=type(raw)=="table" and Faction(raw.side) or nil
        if Integer(npcID,1) and type(raw)=="table" and raw.eligible==true
            and raw.stockState=="unlimited" and raw.costKind=="gold" and raw.access=="unconditional"
            and MaterialRoles[raw.role] and MaterialPriceSources[raw.priceSource]
            and (side=="N" or (side=="A" or side=="H") and side==faction)
            and not (context and context.npcAccess and context.npcAccess[npcID]==false)
            and Integer(raw.price,0) and Integer(raw.quantity,1)
            and type(raw.sourceURL)=="string" and Nonempty(raw.sourceURL)
            and type(raw.verifiedAt)=="string" and Nonempty(raw.verifiedAt)
            and type(raw.evidenceHash)=="string" and Nonempty(raw.evidenceHash)
            and not Nonempty(raw.currency_kind) and not Nonempty(raw.currency_id)
            and not Nonempty(raw.currency_amount) and not Nonempty(raw.currencyKind)
            and not Nonempty(raw.currencyID) and not Nonempty(raw.currencyAmount)
            and not raw.hasExtendedCost then
            -- Sort using private supplier IDs, then expose anonymous purchase
            -- records. UI needs bundle prices; identities remain audit data.
            accepted[#accepted+1]={npcID=npcID,raw=raw}
        end
    end
    table.sort(accepted,function(a,b)
        local au,bu=a.raw.price/a.raw.quantity,b.raw.price/b.raw.quantity
        if au~=bu then return au<bu end
        if a.raw.quantity~=b.raw.quantity then return a.raw.quantity<b.raw.quantity end
        return a.npcID<b.npcID
    end)
    local seen={}
    for _,entry in ipairs(accepted) do
        local raw=entry.raw
        seen[raw.price]=seen[raw.price] or {}
        seen[raw.price][raw.quantity]=seen[raw.price][raw.quantity] or {}
        local sources=seen[raw.price][raw.quantity]
        -- Once access is checked, identical unlimited bundles have identical
        -- purchasing capacity. Keep the first deterministic supplier proof,
        -- while preserving every distinct bundle/price/source alternative.
        if not sources[raw.priceSource] then
            sources[raw.priceSource]=true
            result[#result+1]={itemID=itemID,quantity=raw.quantity,bundleSize=raw.quantity,
                price=raw.price,unit=raw.price/raw.quantity,priceUsable=true,available=true,
                purchasable=true,unlimited=true,materialPrice=true,
                priceSource=raw.priceSource,source=raw.priceSource,priceBasis="Data_ProfMaterialSupply",
                evidenceHash=raw.evidenceHash,reference=true,estimated=false}
        end
    end
    return result
end

function Prices.GetSuppliers(itemID,context)
    return Prices.GetOffers(itemID,context)
end

function Prices.GetPrice(itemID,context)
    local offers=Prices.GetOffers(itemID,context)
    return offers[1] and offers[1].unit or nil
end

function Prices.GetFormulaOffers(itemID,context,source)
    local offers=Offers(itemID,context,"formula")
    -- The localized recipe catalogue supplies display names only. Match an
    -- already authorized supplier by NPC ID; catalogue stock/price/access never
    -- creates or changes a quotation.
    local names={}
    for _,vendor in ipairs(source and source.vendors or {}) do
        if vendor.id and Nonempty(vendor.name) then names[vendor.id]=vendor.name end
    end
    for _,offer in ipairs(offers) do
        local name=names[offer.npcID]
        if name then
            local localized,untranslated=LocalizedName(name,offer.npcID,offer.npcNameCanonical)
            offer.name,offer.npcName=localized,localized
            offer.npcNameUntranslated=untranslated
        end
    end
    return offers
end

local function DisplayInteger(value,minimum)
    local number=type(value)=="number" and value or type(value)=="string" and tonumber(value)
    return Integer(number,minimum) and number or nil
end

local function DisplayFaction(value)
    local side=Faction(value)
    return (side=="A" or side=="H" or side=="N") and side or nil
end

local function DisplayText(value)
    return type(value)=="string" and Nonempty(value) and value or nil
end

-- Source tooltips may describe exchanges and catalogue-only sellers. These
-- fresh display records never enter the copper quotation/procurement paths.
function Prices.GetFormulaDisplayOffers(itemID,context,source)
    local result={}
    itemID=DisplayInteger(itemID,1)
    if not itemID then return result end
    local item=ns.ProfItems and ns.ProfItems[itemID]
    local rawOffers=type(item)=="table" and item.offers
    local rawByID={}
    for key,raw in pairs(type(rawOffers)=="table" and rawOffers or {}) do
        local npcID=DisplayInteger(key,1)
        if npcID and type(raw)=="table"
            and (raw.npc_id==nil or DisplayInteger(raw.npc_id,1)==npcID) then
            rawByID[npcID]=raw
        end
    end
    local playerFaction=DisplayFaction(context and context.faction
        or UnitFactionGroup and UnitFactionGroup("player"))
    local seen={}
    local function append(npcID,vendor)
        if npcID and seen[npcID] then return end
        if npcID then seen[npcID]=true end
        local raw=npcID and rawByID[npcID] or nil
        local faction=DisplayFaction(raw and raw.side)
            or DisplayFaction(vendor and (vendor.side or vendor.faction))
        if playerFaction and faction and faction~="N" and faction~=playerFaction then return end
        if npcID and context and context.npcAccess and context.npcAccess[npcID]==false then return end
        local canonical=DisplayText(raw and raw.name_en)
        local name=DisplayText(vendor and vendor.name) or canonical
        local localized,untranslated=LocalizedName(name,npcID,canonical)
        if not DisplayText(localized) then
            localized=npcID and string.format(ns.L and ns.L["商人 NPC #%d"] or "商人 NPC #%d",npcID)
                or (ns.L and ns.L["商人"] or "商人")
            untranslated=true
        end
        local quantity=type(item)=="table" and DisplayInteger(item.VendorStackCount,1) or nil
        local extended=raw and (Nonempty(raw.currency_kind) or Nonempty(raw.currency_id)
            or Nonempty(raw.currency_amount))
        local kind=DisplayText(raw and raw.currency_kind)
        if kind then kind=kind:match("^%s*(.-)%s*$"):lower() end
        local offer={itemID=itemID,npcID=npcID,name=localized,npcName=localized,
            npcNameCanonical=canonical,npcNameUntranslated=untranslated,
            faction=faction,areaID=DisplayInteger(raw and raw.zone_id,1)
                or DisplayInteger(vendor and (vendor.areaID or vendor.zone_id),1),
            zone=DisplayText(vendor and vendor.zone),quantity=quantity,bundleSize=quantity,
            costCopper=DisplayInteger(raw and raw.cost_copper,0),
            costText=DisplayText(raw and raw.cost_text),currencyKind=kind,
            currencyID=DisplayInteger(raw and raw.currency_id,1),
            currencyAmount=DisplayInteger(raw and raw.currency_amount,0),
            hasExtendedCost=extended or nil,displayOnly=true,catalogueOnly=not raw or nil}
        offer.npcFactionID,offer.npcFactionName=Prices.GetNPCFaction(npcID)
        local loc=npcID and ns.ProfVendors and ns.ProfVendors[npcID]
        if type(loc)=="table" and (not offer.areaID or offer.areaID==loc[1]) then
            offer.areaID=offer.areaID or DisplayInteger(loc[1],1)
            offer.mapID,offer.x,offer.y=loc[2],loc[3],loc[4]
        elseif offer.areaID then
            offer.mapID=ns.AreaMap and ns.AreaMap[offer.areaID]
        end
        result[#result+1]=offer
    end
    for _,vendor in ipairs(source and source.vendors or {}) do
        if type(vendor)=="table" then
            local npcID=DisplayInteger(vendor.id,1)
            if npcID or vendor.id==nil and (DisplayText(vendor.name) or DisplayText(vendor.zone)) then
                append(npcID,vendor)
            end
        end
    end
    local remaining={}
    for npcID in pairs(rawByID) do remaining[#remaining+1]=npcID end
    table.sort(remaining)
    for _,npcID in ipairs(remaining) do append(npcID) end
    return result
end
