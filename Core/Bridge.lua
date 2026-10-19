local addonName, addon = ...

DungeonsForeverDB = DungeonsForeverDB or {}
DungeonsForeverDB.libHUI = DungeonsForeverDB.libHUI or {}

addon.db = DungeonsForeverDB.libHUI
addon.db.settings = addon.db.settings or {}

local f = CreateFrame("Frame")
f:RegisterEvent("ADDON_LOADED")
f:SetScript("OnEvent", function(self, event, name)
    C_Timer.After(0, function()
        if name ~= addonName then return end
        self:UnregisterEvent("ADDON_LOADED")
        DungeonsForeverDB = DungeonsForeverDB or {}
        DungeonsForeverDB.libHUI = DungeonsForeverDB.libHUI or {}
        addon.db = DungeonsForeverDB.libHUI
        addon.db.settings = addon.db.settings or {}
    end)
end)
