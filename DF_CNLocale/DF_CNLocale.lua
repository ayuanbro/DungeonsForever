local boot = CreateFrame("Frame")
boot:RegisterEvent("ADDON_LOADED")
boot:SetScript("OnEvent", function(self, event, name)
    if name ~= "DF_CNLocale" then return end
    self:UnregisterEvent("ADDON_LOADED")
    if type(GetLocale) ~= "function" then return end
    if GetLocale() == "zhCN" then
        DF_CN_FORCE = nil
        return
    end
    if DF_CN_FORCE ~= true then return end
    GetLocale = function() return "zhCN" end
    DF_CN_FORCE_ACTIVE = true
end)
