local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local M = {}
ns.ProfMigrate = M

local STAMP = "1.9.32->pr10"

function M.Run()
    local prof = ns.ProfDB().prof
    if type(prof) ~= "table" then return 0, 0 end
    if prof.migratedFrom == STAMP then return 0, 0 end
    local dropped, flipped = 0, 0
    if prof.planSkel ~= nil then
        prof.planSkel = nil
        dropped = dropped + 1
    end
    if prof.planPrev ~= nil then
        prof.planPrev = nil
        dropped = dropped + 1
    end
    for key, entry in pairs(prof.track or {}) do
        if type(entry) == "table" and entry.version ~= 1 then
            prof.track[key] = nil
            dropped = dropped + 1
        end
    end
    local order = ns.ProfData and ns.ProfData.order or {}
    prof.professionSettings = prof.professionSettings or {}
    for _, slug in ipairs(order) do
        local fixed = (slug == "first-aid" or slug == "poisons")
        local settings = prof.professionSettings[slug]
        if type(settings) ~= "table" then
            settings = {}
            prof.professionSettings[slug] = settings
        end
        if settings.autoRoute == nil and not fixed then
            settings.autoRoute = true
            flipped = flipped + 1
        end
        if settings.autoScheme == nil then settings.autoScheme = "cheapest" end
    end
    prof.migratedFrom = STAMP
    return dropped, flipped
end

local watch = type(CreateFrame) == "function" and CreateFrame("Frame") or nil
if watch then
    watch:RegisterEvent("PLAYER_LOGIN")
    watch:SetScript("OnEvent", function(self)
        self:UnregisterEvent("PLAYER_LOGIN")
        M.Run()
    end)
end
