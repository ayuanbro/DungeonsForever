
if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end

local _, ns = ...
if type(ns.BossSkills) ~= "table" then return end

local __overlay = {
}
for k, v in pairs(__overlay) do ns.BossSkills[k] = v end
