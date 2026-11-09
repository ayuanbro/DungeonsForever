local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Class")
if P then
    ns.ClassIdle = P.Idle
    ns.ClassPaint = P.Paint
    ns.ClassStep = P.Step
    ns.ClassPhased = P.Phased
end

ns.ClassDB = ns.ModuleDB("DungeonsForeverClassDB", { "tier", "talent", "talentSim" })

local MAX_BUILDS = 40
local STORE_VER = 3
local ALLOC_SPAN = 32
local SCAN_MAX = 20000

ns.ClassMaxBuilds = MAX_BUILDS

local function SameBuild(x, y)
    if x == y then return true end
    if type(x) ~= "table" or type(y) ~= "table" then return false end
    if x.name ~= y.name then return false end
    local ax, ay = x.alloc, y.alloc
    if ax == ay then return true end
    if type(ax) ~= "table" or type(ay) ~= "table" then return false end
    for t = 1, 3 do
        local lx, ly = ax[t], ay[t]
        if lx ~= ly then
            if type(lx) ~= "table" or type(ly) ~= "table" then return false end
            for i = 1, ALLOC_SPAN do
                if lx[i] ~= ly[i] then return false end
            end
        end
    end
    return true
end

local function Normalize(list)
    if type(list) ~= "table" then return {}, 0 end
    local n = #list
    if n == 0 then return list, 0 end
    local scan = n
    if scan > SCAN_MAX then scan = SCAN_MAX end
    local out = {}
    for i = 1, scan do
        local b = list[i]
        if type(b) == "table" then
            local dup = false
            for j = 1, #out do
                if SameBuild(out[j], b) then
                    dup = true
                    break
                end
            end
            if not dup then
                out[#out + 1] = b
                if #out >= MAX_BUILDS then break end
            end
        end
    end
    return out, n - #out
end

function ns.TalentBuildStore()
    local cdb = ns.ClassDB()
    local ts = cdb.talentSim
    if not ts then
        ts = {}
        cdb.talentSim = ts
    end
    local legacy = cdb.talent and cdb.talent.builds
    local builds = ts.builds
    if not builds then
        builds = legacy or {}
        ts.builds = builds
    end
    if legacy and legacy ~= builds then
        for cls, list in pairs(legacy) do
            if type(list) == "table" then
                local dst = builds[cls]
                if dst == nil then
                    builds[cls] = list
                elseif dst ~= list then
                    for i = 1, #list do dst[#dst + 1] = list[i] end
                end
            end
        end
        ts.v = nil
    end
    if cdb.talent then cdb.talent.builds = nil end
    local overflow = false
    for cls, list in pairs(builds) do
        if type(list) == "table" and #list > MAX_BUILDS then
            overflow = true
            break
        end
    end
    if ts.v ~= STORE_VER or overflow then
        local dropped = 0
        for cls, list in pairs(builds) do
            local out, gone = Normalize(list)
            builds[cls] = out
            dropped = dropped + (gone or 0)
        end
        ts.v = STORE_VER
        if dropped > 0 and ns.L then
            print('|cff46bf72[职业]|r ' .. string.format(ns.L['已清理 %d 条重复的天赋方案'], dropped))
        end
    end
    local stale
    for k in pairs(builds) do
        if type(k) == "string" and string.lower(k) ~= k then
            stale = stale or {}
            stale[#stale + 1] = k
        end
    end
    if stale then
        for _, k in ipairs(stale) do
            local lk = string.lower(k)
            local list = builds[k]
            builds[k] = nil
            local dst = builds[lk]
            if dst == nil then
                builds[lk] = (Normalize(list))
            elseif dst ~= list and type(list) == "table" then
                for i = 1, #list do
                    if #dst < MAX_BUILDS then dst[#dst + 1] = list[i] end
                end
            end
        end
        ts.v = STORE_VER
    end
    return ts
end

ns.TalentBuildStore()
