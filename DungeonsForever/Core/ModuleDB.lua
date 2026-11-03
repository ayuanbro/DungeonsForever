local _, ns = ...

local function mergeMissing(dst, src)
    for k, v in pairs(src) do
        if dst[k] == nil then dst[k] = v end
    end
end

local last = {}

local function sync(svName)
    local g = _G[svName]
    if type(g) ~= "table" then
        g = {}
        _G[svName] = g
    end
    local prev = last[svName]
    if prev and prev ~= g then
        mergeMissing(g, prev)
    end
    last[svName] = g
    return g
end

local function promote(svName, legacyKeys, db)
    local legacy = _G.DungeonsForeverDB
    if type(legacy) ~= "table" or type(legacyKeys) ~= "table" then return end
    local hit = false
    for i = 1, #legacyKeys do
        local k = legacyKeys[i]
        local old = legacy[k]
        if old ~= nil then
            hit = true
            if type(old) == "table" then
                if type(db[k]) ~= "table" then
                    db[k] = old
                else
                    mergeMissing(db[k], old)
                end
            elseif db[k] == nil then
                db[k] = old
            end
        end
    end
    if hit then
        for i = 1, #legacyKeys do legacy[legacyKeys[i]] = nil end
        legacy[svName .. "Moved"] = true
    end
end

function ns.ModuleDB(svName, legacyKeys, primary)
    return function()
        local db = sync(svName)
        promote(svName, legacyKeys, db)
        if primary and type(db[primary]) ~= "table" then db[primary] = {} end
        return db
    end
end

function ns.ModuleDBKeys(svName, keys)
    local db = _G[svName]
    if type(db) ~= "table" then return false end
    if type(keys) ~= "table" then return true end
    for i = 1, #keys do
        if db[keys[i]] ~= nil then return true end
    end
    return false
end
