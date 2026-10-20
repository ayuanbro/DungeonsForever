-- Materials use generated item-level client bundle prices. Only formula
-- procurement/display consults explicit NPC records and their access/stock.
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

local function LocalizedName(name,npcID)
    local localized=type(name)=="string" and ns.L and ns.L[name] or name
    local locale=type(GetLocale)=="function" and GetLocale()
    if (locale=="zhCN" or locale=="zhTW") and npcID
        and (type(localized)~="string" or not localized:find("[\128-\255]")) then
        local pattern=ns.L and ns.L["商人 NPC #%d"] or "商人 NPC #%d"
        return string.format(pattern,npcID),true
    end
    return localized
end

local function Faction(value)
    if value=="Alliance" or value=="a" then return "A" end
    if value=="Horde" or value=="h" then return "H" end
    if value=="n" or value=="Neutral" then return "N" end
    return Nonempty(value) and value or nil
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
    local offer={itemID=itemID,npcID=npcID,npcName=name,name=name,
        npcNameCanonical=raw.name_en,npcNameUntranslated=untranslated,
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

function Prices.GetOffers(itemID,context)
    local item=ns.ProfItems and ns.ProfItems[itemID]
    if type(item)~="table" or not Integer(item.cost_copper,0)
        or not Integer(item.VendorStackCount,1)
        or Nonempty(item.currency_kind) or Nonempty(item.currency_id)
        or Nonempty(item.currency_amount) then return {} end
    local quantity,price=item.VendorStackCount,item.cost_copper
    local source=type(item.price_source)=="string" and Nonempty(item.price_source)
        and item.price_source or "Data_ProfItems"
    -- unlimited is the shared procurement contract for an uncapped material
    -- quote, not an observation about any particular merchant's inventory.
    return {{itemID=itemID,quantity=quantity,bundleSize=quantity,price=price,unit=price/quantity,
        priceUsable=true,available=true,purchasable=true,unlimited=true,materialPrice=true,
        priceSource=source,source=source,priceBasis="Data_ProfItems",
        reference=true,estimated=false,costText=item.cost_text}}
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
            local localized,untranslated=LocalizedName(name,offer.npcID)
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
        local localized,untranslated=LocalizedName(name,npcID)
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
