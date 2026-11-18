local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local M = {}
ns.ProfMigrate = M

local STAMP = "1.9.32->pr10"
local PRICED_SCHEMES={cheapest=true,stable=true,matcost=true,crafts=true,optim=true}
function M.UpgradePricing()
    local prof=ns.ProfDB().prof
    if prof.pricingMigration==1 then return 0 end
    local count=0
    local function mark(plan)
        if type(plan)=="table" and plan.auctionDepthRevision~=1 and PRICED_SCHEMES[plan.scheme] then
            plan.pricingPolicyStale=true;plan.stale=true;plan.staleReason=plan.staleReason or "procurement-policy"
            count=count+1
        end
    end
    local plans=prof.routePlans
    for _,character in pairs(type(plans)=="table" and plans.characters or {}) do
        for _,record in pairs(type(character)=="table" and character.routes or {}) do
            if type(record)=="table" then mark(record.skeleton) end
        end
    end
    for _,character in pairs(prof.track or {}) do
        for _,run in pairs(type(character)=="table" and character.runs or {}) do
            if type(run)=="table" then mark(run.plan) end
        end
    end
    for _,entries in pairs(prof.routeHistory or {}) do
        for _,entry in pairs(type(entries)=="table" and entries or {}) do
            if type(entry)=="table" then mark(entry.skel) end
        end
    end
    prof.pricingMigration=1
    return count
end

function M.Run()
    M.UpgradePricing()
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
if type(IsLoggedIn)=="function" and IsLoggedIn() then M.UpgradePricing() end

local watch = type(CreateFrame) == "function" and CreateFrame("Frame") or nil
if watch then
    watch:RegisterEvent("PLAYER_LOGIN")
    watch:SetScript("OnEvent", function(self)
        self:UnregisterEvent("PLAYER_LOGIN")
        M.Run()
    end)
end
