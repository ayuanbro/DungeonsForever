local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local L = ns.L

local A = {}
ns.BagArrow = A

local cache, queued = {}, {}
local pumping = false
local cooling = false

local function DB()
    local db = ns.GearDB()
    local s = db.gear
    if type(s) ~= "table" then
        s = {}
        db.gear = s
    end
    local a = s.arrow
    if type(a) ~= "table" then
        a = {}
        s.arrow = a
    end
    return a
end

local function MinPct()
    local v = tonumber(DB().min)
    if not v or v < 0 or v > 999 then v = 1 end
    return v
end

function A.On()
    return DB().on ~= false
end

local function BtnRefresh()
    local B = _G.Baganator
    if type(B) ~= "table" or type(B.API) ~= "table" then return end
    local fn = B.API.RequestItemButtonsRefresh
    if type(fn) ~= "function" then return end
    local R = B.Constants and B.Constants.RefreshReason
    local reason = R and R.ItemWidgets
    pcall(fn, reason and { reason } or nil)
end

function A.Refresh()
    cache = {}
    queued = {}
    BtnRefresh()
end

function A.Revalidate()
    if cooling then return end
    cooling = true
    if C_Timer and C_Timer.After then
        C_Timer.After(0.2, function()
            cooling = false
            A.Refresh()
        end)
    else
        cooling = false
        A.Refresh()
    end
end

function A.SetOn(v)
    DB().on = v and true or false
    A.Refresh()
end

function A.Scope()
    local s = DB().scope
    if s == "all" or s == "manual" then return s end
    return "spec"
end

function A.CycleScope()
    local s = A.Scope()
    DB().scope = (s == "spec" and "manual") or (s == "manual" and "all") or "spec"
    A.Refresh()
    return DB().scope
end

function A.Decide(id, link)
    local BG = ns.BisModule
    if not (BG and BG.ScoreVsBisAll) then return nil end
    local rows = BG.ScoreVsBisAll(id, link)
    if type(rows) ~= "table" or #rows == 0 then return false end
    local scope = A.Scope()
    local pick
    if scope == "all" then
        for i = 1, #rows do
            local r = rows[i]
            if type(r.pct) == "number" and (not pick or r.pct > pick.pct) then pick = r end
        end
    else
        local want
        if scope == "manual" then
            want = BG.tspec
        else
            want = BG.DetectSpec and BG.DetectSpec() or nil
        end
        if want then
            for i = 1, #rows do
                if rows[i].key == want then pick = rows[i] break end
            end
        end
        if not pick then return false end
    end
    if not pick or type(pick.pct) ~= "number" then return false end
    return pick.pct >= MinPct()
end

local function Eval(link)
    local id = tonumber(string.match(link or "", "item:(%d+)"))
    if not id then return false end
    local inst = C_Item and C_Item.GetItemInfoInstant
    if type(inst) == "function" then
        local ok, _, _, _, _, _, clsID = pcall(inst, id)
        if ok and type(clsID) == "number" and clsID ~= 2 and clsID ~= 4 then return false end
    end
    local BG = ns.BisModule
    if not (BG and BG.ScoreVsBisAll) then return nil end
    local prev = BG.scanBudget
    BG.scanBudget = 2
    local ok, res = pcall(A.Decide, id, link)
    BG.scanBudget = prev
    if not ok then return false end
    return res
end

local function Pump()
    if pumping then return end
    pumping = true
    local function step()
        local n = 0
        for link in pairs(queued) do
            queued[link] = nil
            cache[link] = Eval(link)
            n = n + 1
            if n >= 20 then break end
        end
        if next(queued) then
            if C_Timer and C_Timer.After then
                C_Timer.After(0, step)
            else
                pumping = false
            end
        else
            pumping = false
            BtnRefresh()
        end
    end
    if C_Timer and C_Timer.After then
        C_Timer.After(0, step)
    else
        step()
    end
end

local function Should(_, details)
    if not A.On() then return false end
    local link = type(details) == "table" and details.itemLink or nil
    if type(link) ~= "string" then return false end
    local v = cache[link]
    if v ~= nil then return v end
    if not queued[link] then
        queued[link] = true
        Pump()
    end
    return false
end

function A.Register()
    if A.registered then return true end
    local B = _G.Baganator
    if type(B) ~= "table" or type(B.API) ~= "table" then return false end
    local fn = B.API.RegisterCornerWidget
    if type(fn) ~= "function" then return false end
    local ok = pcall(fn, L["背包提升箭头"], "dfbis", Should, function(itemButton)
        local tex = itemButton:CreateTexture(nil, "OVERLAY")
        tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\ArrowUp")
        tex:SetSize(16, 16)
        return tex
    end, { corner = "top_right", priority = 1 })
    if ok then A.registered = true end
    return ok
end

local ev = CreateFrame("Frame")
ev:RegisterEvent("BAG_UPDATE_DELAYED")
ev:RegisterEvent("PLAYER_EQUIPMENT_CHANGED")
ev:RegisterEvent("PLAYER_LEVEL_UP")
ev:RegisterEvent("TRAIT_CONFIG_UPDATED")
ev:RegisterEvent("TRAIT_CONFIG_CREATED")
ev:RegisterEvent("ACTIVE_TALENT_GROUP_CHANGED")
ev:RegisterEvent("PLAYER_TALENT_UPDATE")
ev:RegisterEvent("PLAYER_SPECIALIZATION_CHANGED")
ev:RegisterEvent("CHARACTER_POINTS_CHANGED")
ev:RegisterEvent("PLAYER_ENTERING_WORLD")
ev:SetScript("OnEvent", function(_, event)
    if event ~= "BAG_UPDATE_DELAYED" and event ~= "PLAYER_EQUIPMENT_CHANGED" then
        local BG = ns.BisModule
        if BG and BG.InvalidateSpec then BG.InvalidateSpec() end
    end
    A.Revalidate()
end)

local boot = CreateFrame("Frame")
boot:RegisterEvent("PLAYER_LOGIN")
boot:SetScript("OnEvent", function(self)
    self:UnregisterEvent("PLAYER_LOGIN")
    if A.Register() then
        A.Refresh()
    elseif C_Timer and C_Timer.After then
        C_Timer.After(5, function()
            if A.Register() then A.Refresh() end
        end)
    end
end)

if A.Register() then A.Revalidate() end

if ns.OnItemData then
    ns.OnItemData(function() A.Revalidate() end)
end
