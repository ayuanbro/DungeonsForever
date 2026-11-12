local _, ns = ...

local LFG_ID = {
    wailing_caverns = 796,
    scholomance = 797,
    ragefire_chasm = 798,
    the_deadmines = 799,
    shadowfang_keep = 800,
    blackfathom_deeps = 801,
    the_stockade = 802,
    gnomeregan = 803,
    razorfen_kraul = 804,
    sm_graveyard = 805,
    razorfen_downs = 806,
    uldaman = 807,
    zul_farrak = 808,
    maraudon = 809,
    sunken_temple = 810,
    blackrock_depths = 811,
    lower_blackrock_spire = 812,
    dire_maul_east = 813,
    dire_maul_west = 814,
    dire_maul_north = 815,
    stratholme_main = 816,
    sm_armory = 827,
    sm_cathedral = 828,
    sm_library = 829,
    upper_blackrock_spire = 837,
    stratholme_service = 1603,
    shapers_terrace = 1978,
    blackmaw_hold = 1979,
    alcaz_prison = 1980,
    excavation_wetlands = 1981,
    ruins_of_lordaeron = 1982,
    city_of_dalaran = 1983,
    hall_of_thanes = 1984,
    the_drowned_city = 1985,
    kroldok_stronghold = 1986,
}

ns.DungeonLFGID = LFG_ID

local function apply()
    local list = ns.DungeonData and ns.DungeonData.dungeons
    if not list then return 0 end
    if not (C_LFGList and C_LFGList.GetActivityInfoTable) then return 0 end
    local changed = 0
    for i = 1, #list do
        local d = list[i]
        local lfg = d and LFG_ID[d.id]
        if lfg then
            local ok, info = pcall(C_LFGList.GetActivityInfoTable, lfg)
            if ok and type(info) == "table" then
                local lo, hi = info.minLevelSuggestion, info.maxLevelSuggestion
                if type(lo) == "number" and type(hi) == "number" and lo > 0 and hi >= lo and (d.levelMin ~= lo or d.levelMax ~= hi) then
                    d.levelMin, d.levelMax = lo, hi
                    changed = changed + 1
                end
            end
        end
    end
    return changed
end

function ns.SyncDungeonLevels()
    local n = apply()
    if n > 0 then
        local U = ns.DungeonUI
        if U then
            U.dungeonListLevel = -1
            if U.dungeonBuilt then pcall(U.UpdateDungeons, U) end
        end
    end
    return n
end

ns.Init(function() ns.SyncDungeonLevels() end)

local f = CreateFrame("Frame")
pcall(f.RegisterEvent, f, "PLAYER_ENTERING_WORLD")
pcall(f.RegisterEvent, f, "LFG_LIST_AVAILABLE_ACTIVITY_UPDATE")
pcall(f.RegisterEvent, f, "LFG_LIST_ENTRY_CREATED")
f:SetScript("OnEvent", function() ns.SyncDungeonLevels() end)
