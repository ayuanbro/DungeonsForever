local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

local _, ns = ...

if (type(GetLocale) == "function") and GetLocale() ~= "zhCN" then return end

ns.NameOverrides = {
    spell = {
        [1279399] = "召喚軍馬",
        [1296534] = "召喚被遺忘者戰馬",
    },
    item = {
        [286756] = "鬼靈狼群",
        [286727] = "緋紅雄雞",
        [286724] = "翠綠海龜",
        [98550] = "繁花古樹",
        [275818] = "夭夭",
        [229368] = "古鰭爾",
    },
}
