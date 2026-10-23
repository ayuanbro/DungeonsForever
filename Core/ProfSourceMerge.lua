local _, ns = ...

local M = {}
ns.ProfSourceMerge = M

local function ZoneName(area)
    if type(area) ~= "number" or area <= 0 then return "" end
    local txt = ns.ProfZoneText
    if type(txt) == "table" and txt[area] then return txt[area] end
    local am = ns.AreaMap
    local ui = type(am) == "table" and am[area] or nil
    if ui then
        local pd = ns.ProfModule
        if pd and pd.MapName then
            local nm = pd.MapName(ui)
            if type(nm) == "string" and nm ~= "" then return nm end
        end
    end
    if C_Map and C_Map.GetAreaInfo then
        local ok, nm = pcall(C_Map.GetAreaInfo, area)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return ""
end

local function VendorEntry(v)
    local zone = ZoneName(v.area)
    return {
        id = v.id,
        name = v.name,
        zone = (zone ~= "" and zone or nil),
        area = v.area,
        side = v.side,
        price = v.price,
        cur = v.cur,
        amt = v.amt,
        stock = v.stock,
    }
end

local function DropEntry(d)
    local zone = ZoneName(d.area)
    return {
        npc = d.npc,
        id = d.id,
        chance = d.pct,
        zone = (zone ~= "" and zone or nil),
        area = d.area,
    }
end

local function MergeVendor(byId, list, v)
    local e = byId[v.id]
    if type(e) ~= "table" then
        e = VendorEntry(v)
        byId[v.id] = e
        list[#list + 1] = e
        return e
    end
    if (tonumber(e.price) or 0) <= 0 and (v.price or 0) > 0 then e.price = v.price end
    if (tonumber(e.cur) or 0) <= 0 and (v.cur or 0) > 0 then
        e.cur = v.cur
        e.amt = v.amt
    end
    if e.stock == nil and v.stock ~= nil then e.stock = v.stock end
    if e.area == nil and v.area then e.area = v.area end
    if (e.zone == nil or e.zone == "") and v.area then
        local z = ZoneName(v.area)
        if z ~= "" then e.zone = z end
    end
    return e
end

local function MergeDrop(byName, list, d)
    local nm = d.npc
    local e = nm and byName[nm] or nil
    if type(e) ~= "table" then
        e = DropEntry(d)
        if nm then byName[nm] = e end
        list[#list + 1] = e
        return e
    end
    if e.id == nil and d.id then e.id = d.id end
    if (e.chance == nil or e.chance == 0) and (d.pct or 0) > 0 then e.chance = d.pct end
    if (e.zone == nil or e.zone == "") and d.area then
        local z = ZoneName(d.area)
        if z ~= "" then e.zone = z end
    end
    if e.area == nil and d.area then e.area = d.area end
    return e
end

function M.Fill(row)
    if type(row) ~= "table" then return nil end
    local s = row[14]
    if type(s) == "table" and s.__srcDone then return s end
    local f = row[13]
    local fid = type(f) == "table" and f[1] or nil
    local src = fid and ns.ProfSources and ns.ProfSources[fid] or nil
    if type(src) ~= "table" then return s end
    if type(s) ~= "table" then
        s = {}
        row[14] = s
    end
    s.__srcDone = true
    local vs = src.v
    if type(vs) == "table" and #vs > 0 then
        local list = s.vendors
        if type(list) ~= "table" then
            list = {}
            s.vendors = list
        end
        local byId = {}
        for i = 1, #list do
            local v = list[i]
            if type(v) == "table" and v.id then byId[v.id] = v end
        end
        for i = 1, #vs do
            local v = vs[i]
            if type(v) == "table" and v.id then MergeVendor(byId, list, v) end
        end
    end
    local ds = src.d
    if type(ds) == "table" and #ds > 0 then
        local list = s.drops
        if type(list) ~= "table" then
            list = {}
            s.drops = list
        end
        local byName = {}
        for i = 1, #list do
            local d = list[i]
            if type(d) == "table" then
                if d.npc then byName[d.npc] = d end
                if d.id then byName[d.id] = d end
            end
        end
        for i = 1, #ds do
            local d = ds[i]
            if type(d) == "table" and d.npc then MergeDrop(byName, list, d) end
        end
    end
    return s
end

function M.VendorsOf(fid)
    if type(fid) ~= "number" then return nil end
    local src = ns.ProfSources and ns.ProfSources[fid]
    if type(src) ~= "table" then return nil end
    return src.v
end
