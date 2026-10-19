local _, ns = ...

local VDB = {}
ns.VendorPriceDB = VDB

local function Table()
    local db = ns.DB()
    if type(db.vendorPrices) ~= "table" then
        db.vendorPrices = {}
    end
    return db.vendorPrices
end

local function Scan()
    if not GetMerchantNumItems or not GetMerchantItemInfo then return 0 end
    local num = GetMerchantNumItems()
    if type(num) ~= "number" or num <= 0 then return 0 end

    local tab = Table()
    local now = time()
    local fresh = 0
    for i = 1, num do
        local ok, name, _, price, quantity, _, _, _, currencyID =
            pcall(GetMerchantItemInfo, i)
        if ok and price and price > 0 and not (currencyID and currencyID > 0) then
            local link = GetMerchantItemLink and GetMerchantItemLink(i)
            local id = link and tonumber(link:match("item:(%d+)"))
            if id then
                local q = tonumber(quantity) or 1
                if q < 1 then q = 1 end
                local unit = math.floor(price / q + 0.5)
                local old = tab[id]
                if not old then
                    tab[id] = { p = unit, t = now }
                    fresh = fresh + 1
                elseif old.p ~= unit then
                    old.p = unit
                    old.t = now
                end
            end
        end
    end
    return fresh
end

do
    local f = CreateFrame("Frame")
    f:RegisterEvent("MERCHANT_SHOW")
    f:RegisterEvent("MERCHANT_UPDATE")
    f:SetScript("OnEvent", function(_, event)
        C_Timer.After(0, function()
        pcall(Scan)
        end)
    end)
end

function VDB.GetPrice(itemID)
    if type(itemID) ~= "number" then return nil end
    local rec = Table()[itemID]
    if type(rec) == "table" and type(rec.p) == "number" and rec.p > 0 then
        return rec.p
    end
    local s = rawget(ns, "VendorPriceSeed")
    if type(s) == "table" then
        local p = s[itemID]
        if type(p) == "number" and p > 0 then return p end
    end
    return nil
end

function VDB.Count()
    local n = 0
    for _ in pairs(Table()) do n = n + 1 end
    return n
end

function VDB.Scan()
    return Scan()
end
