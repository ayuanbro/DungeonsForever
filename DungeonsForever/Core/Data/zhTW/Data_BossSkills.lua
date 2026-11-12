
local gl = (type(GetLocale) == "function") and GetLocale() or "zhCN"
if gl ~= "zhTW" then return end

local _, ns = ...
if type(ns.BossSkills) ~= "table" then return end

local __overlay = {
}
for k, v in pairs(__overlay) do ns.BossSkills[k] = v end
