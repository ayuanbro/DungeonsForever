local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

if (type(GetLocale) == "function") and GetLocale() ~= "zhCN" then return end

ns.NameOverrides = {
    spell = {
        [1279399] = "召唤军马",
        [1296534] = "召唤被遗忘者战马",
    },
    item = {
        [286756] = "鬼灵狼群",
        [286727] = "绯红雄鸡",
        [286724] = "翠绿海龟",
        [98550] = "繁花古树",
        [275818] = "夭夭",
        [229368] = "古鳍尔",
    },
}
