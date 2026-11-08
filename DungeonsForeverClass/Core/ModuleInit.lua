local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Class")
if P then
    ns.ClassIdle = P.Idle
    ns.ClassPaint = P.Paint
    ns.ClassStep = P.Step
    ns.ClassPhased = P.Phased
end

ns.ClassDB = ns.ModuleDB("DungeonsForeverClassDB", { "tier", "talent", "talentSim" })

function ns.TalentBuildStore()
    local cdb = ns.ClassDB()
    local ts = cdb.talentSim
    if not ts then
        ts = {}
        cdb.talentSim = ts
    end
    local legacy = cdb.talent and cdb.talent.builds
    if legacy then
        local cur = ts.builds
        if cur == nil then
            ts.builds = legacy
        elseif cur ~= legacy then
            for cls, list in pairs(legacy) do
                local dst = cur[cls]
                if dst == nil then
                    cur[cls] = list
                else
                    for _, b in ipairs(list) do dst[#dst + 1] = b end
                end
            end
        end
        cdb.talent.builds = ts.builds
    end
    if not ts.builds then ts.builds = {} end
    local rename = nil
    for k, list in pairs(ts.builds) do
        if type(k) == "string" and string.lower(k) ~= k then
            rename = rename or {}
            rename[k] = string.lower(k)
        end
    end
    if rename then
        for k, lk in pairs(rename) do
            local list = ts.builds[k]
            ts.builds[k] = nil
            local dst = ts.builds[lk]
            if dst == nil then
                ts.builds[lk] = list
            elseif dst ~= list then
                for _, b in ipairs(list) do dst[#dst + 1] = b end
            end
        end
    end
    return ts
end
