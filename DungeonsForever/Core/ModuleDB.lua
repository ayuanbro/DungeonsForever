local _, ns = ...

local function mergeMissing(dst, src)
    for k, v in pairs(src) do
        if dst[k] == nil then dst[k] = v end
    end
end

local booted = {}

function ns.ModuleDB(svName, legacyKeys, primary)
    local db = _G[svName]
    if type(db) ~= "table" then
        db = {}
        _G[svName] = db
    end
    if not booted[svName] then
        booted[svName] = true
        local legacy = _G.DungeonsForeverDB
        if type(legacy) == "table" and type(legacyKeys) == "table" then
            for i = 1, #legacyKeys do
                local k = legacyKeys[i]
                local old = legacy[k]
                if type(old) == "table" then
                    if type(db[k]) ~= "table" then
                        db[k] = old
                    else
                        mergeMissing(db[k], old)
                    end
                elseif old ~= nil and db[k] == nil then
                    db[k] = old
                end
                legacy[k] = nil
            end
        end
        if type(legacy) == "table" then
            legacy[svName .. "Moved"] = true
        end
    end
    if primary and type(db[primary]) ~= "table" then db[primary] = {} end
    return db
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
