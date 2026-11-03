local ns = _G.DF_NS or {}

local NAME = "DungeonsForeverProfDB"
local booted = false

local function mergeMissing(dst, src)
    for k, v in pairs(src) do
        if dst[k] == nil then dst[k] = v end
    end
end

local function adopt(db, legacy)
    if type(legacy) ~= "table" then return end
    local old = legacy.prof
    if type(old) == "table" then
        if type(db.prof) ~= "table" then
            db.prof = old
        else
            mergeMissing(db.prof, old)
        end
    end
    local audit = legacy.profAudit
    if type(audit) == "table" then
        if type(db.profAudit) ~= "table" then
            db.profAudit = audit
        else
            mergeMissing(db.profAudit, audit)
        end
    end
    legacy.prof = nil
    legacy.profAudit = nil
    legacy.profMoved = true
end

function ns.ProfDB()
    local db = _G[NAME]
    if type(db) ~= "table" then
        db = {}
        _G[NAME] = db
    end
    if not booted then
        booted = true
        adopt(db, _G.DungeonsForeverDB)
    end
    if type(db.prof) ~= "table" then db.prof = {} end
    return db
end
