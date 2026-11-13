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

local TIP_WHITE = "|cffffffff"
local TIP_RED = "|cffff2020"
local TIP_NOISE = { ["法术 ID"] = true, ["图标 ID"] = true, ["Spell ID"] = true, ["Icon ID"] = true }

local function TipSpell(spid)
    local name
    local body = {}
    if not spid then return nil, body end
    if C_Spell and C_Spell.GetSpellInfo then
        local ok, info = pcall(C_Spell.GetSpellInfo, spid)
        if ok and type(info) == "table" then name = info.name end
    end
    if C_TooltipInfo and C_TooltipInfo.GetSpellByID then
        local ok, tt = pcall(C_TooltipInfo.GetSpellByID, spid)
        if ok and type(tt) == "table" and type(tt.lines) == "table" then
            local seen = false
            for _, ln in ipairs(tt.lines) do
                local t = ln and ln.leftText
                if t and t ~= "" and not TIP_NOISE[t] then
                    if not seen then
                        seen = true
                        name = name or t
                    else
                        body[#body + 1] = t
                    end
                end
            end
        end
    end
    return name, body
end

function ns.TalentTip(owner, nd, rank, treeName, need, noPre)
    if not owner or type(nd) ~= "table" then return end
    local L = ns.L or {}
    local name, body = TipSpell(nd.spid)
    rank = tonumber(rank) or 0
    local maxRank = tonumber(nd.max) or 0
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    if ns.hui and ns.hui.ShowNativeTip then pcall(ns.hui.ShowNativeTip, GameTooltip) end
    GameTooltip:ClearLines()
    GameTooltip:AddLine(name or nd.n or "", 1, 1, 1)
    GameTooltip:AddLine(string.format("%s %s%d|r/%d", L["等级"] or "等级", TIP_WHITE, rank, maxRank), 1, 1, 1)
    GameTooltip:AddLine(" ")
    if #body > 0 then
        for i = 1, #body do
            GameTooltip:AddLine(body[i], 1, 1, 1, true)
        end
    else
        if nd.passive then GameTooltip:AddLine(L["被动"] or "被动", 1, 1, 1) end
        local d = nd.desc
        local txt
        if type(d) == "table" then
            txt = d[math.min(math.max(rank, 1), #d)] or d[1]
        elseif type(d) == "string" then
            txt = d
        end
        if txt then GameTooltip:AddLine(txt, 1, 1, 1, true) end
    end
    if noPre then
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine(TIP_RED .. (L["需要所有前置天赋"] or "需要所有前置天赋") .. "|r", 1, 1, 1, true)
    elseif need and need > 0 then
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine(TIP_RED .. string.format(L["还需投入%d点天赋点数到%s天赋中"] or "还需投入%d点天赋点数到%s天赋中", need, treeName or "") .. "|r", 1, 1, 1, true)
    end
    GameTooltip:Show()
end
