-- NPC procurement uses only the generated schema2 item/NPC records.
-- Location data is for map display; it never establishes stock or prices.
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
    local offer={itemID=itemID,npcID=npcID,npcName=raw.name_en,name=raw.name_en,
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
    return Offers(itemID,context,"material")
end

function Prices.GetSuppliers(itemID,context)
    return Offers(itemID,context,"supplier")
end

function Prices.GetPrice(itemID,context)
    local offers=Prices.GetOffers(itemID,context)
    return offers[1] and offers[1].unit or nil
end

function Prices.GetFormulaOffers(itemID,context)
    return Offers(itemID,context,"formula")
end
