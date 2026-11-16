local real = type(GetLocale) == "function" and GetLocale or function() return "enUS" end
_G.DF_REAL_LOCALE = real

if type(_G.DF_Locale) ~= "function" then
    _G.DF_Locale = function()
        if rawget(_G, "DF_CN_FORCE") == true then return "zhCN" end
        return real()
    end
end

local boot = CreateFrame("Frame")
boot:RegisterEvent("ADDON_LOADED")
boot:SetScript("OnEvent", function(self, _, name)
    if name ~= "DF_CNLocale" then return end
    self:UnregisterEvent("ADDON_LOADED")
    if real() == "zhCN" then DF_CN_FORCE = nil end
end)
