local _, ns = ...

if not ns.IsTitan then return end

local WM = {}
ns.WeaponMasters = WM

local function Knows(id)
    if ns.SpellTraining and ns.SpellTraining.Knows then
        return ns.SpellTraining.Knows(id) and true or false
    end
    local ok, known = pcall(function()
        if C_SpellBook and C_SpellBook.IsSpellKnownOrInSpellBook then
            return C_SpellBook.IsSpellKnownOrInSpellBook(id, Enum and Enum.SpellBookSpellBank and Enum.SpellBookSpellBank.Player or 0)
        end
        return C_SpellBook and C_SpellBook.IsSpellKnown and C_SpellBook.IsSpellKnown(id, 0) or false
    end)
    return ok and known or false
end

local function SpellName(id)
    if C_Spell and C_Spell.GetSpellName then
        local ok, name = pcall(C_Spell.GetSpellName, id)
        if ok and name then return name end
    end
    if GetSpellInfo then
        local ok, name = pcall(GetSpellInfo, id)
        if ok and name then return name end
    end
    return ""
end

local function SpellTexture(id)
    if C_Spell and C_Spell.GetSpellTexture then
        local ok, tex = pcall(C_Spell.GetSpellTexture, id)
        if ok and tex then return tex end
    end
    if GetSpellTexture then
        local ok, tex = pcall(GetSpellTexture, id)
        if ok and tex then return tex end
    end
    return "Interface\\Icons\\INV_Misc_QuestionMark"
end

local function ZoneName(zoneId)
    if C_Map and C_Map.GetAreaInfo then
        local ok, name = pcall(C_Map.GetAreaInfo, zoneId)
        if ok and name then return name end
    end
    return nil
end

local GROUP_ORDER = {
    { key = "available", name = "可学" },
    { key = "notlevel",  name = "等级不够" },
    { key = "known",     name = "已学", known = true },
}

function WM.Rows()
    local data = ns.WeaponTraining
    if not data or not data.skills then return nil end
    local cls = select(2, UnitClass("player"))
    local faction = UnitFactionGroup("player")
    local lvl = UnitLevel("player") or 0
    local groups = { available = {}, notlevel = {}, known = {} }
    for _, id in ipairs(data.order or {}) do
        local sk = data.skills[id]
        if sk and sk.classes and sk.classes[cls] then
            local trainers = {}
            for _, tr in ipairs(sk.trainers or {}) do
                if tr.faction == faction then
                    trainers[#trainers + 1] = {
                        npc = tr.npc,
                        name = tr.name,
                        x = tr.x,
                        y = tr.y,
                        uiMapId = data.zones and data.zones[tr.zoneId] or nil,
                        zoneName = ZoneName(tr.zoneId),
                    }
                end
            end
            local row = {
                id = id,
                name = SpellName(id),
                icon = SpellTexture(id),
                level = sk.level,
                trainers = trainers,
            }
            if Knows(id) then
                row.known = true
                groups.known[#groups.known + 1] = row
            elseif sk.level and lvl < sk.level then
                groups.notlevel[#groups.notlevel + 1] = row
            else
                groups.available[#groups.available + 1] = row
            end
        end
    end
    return groups
end

WM.GROUP_ORDER = GROUP_ORDER

function WM.MarkNPC(tr)
    local ver = select(4, GetBuildInfo()) or 0
    if ver < 16000 or ver > 16999 then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, ns.L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)
        end
        return
    end
    if not (tr and tr.uiMapId and tr.x and tr.y) then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, ns.L["未收录该训练师的地图位置"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint
        and (not C_Map.CanSetUserWaypointOnMap or C_Map.CanSetUserWaypointOnMap(tr.uiMapId)) then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates, tr.uiMapId, tr.x / 100, tr.y / 100)
        if ok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, tr.uiMapId)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, tr.uiMapId)
    end
end
