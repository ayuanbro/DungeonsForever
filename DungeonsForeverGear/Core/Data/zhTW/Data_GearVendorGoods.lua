local gl = (type(DF_Locale) == 'function') and DF_Locale() or 'zhCN'
if gl ~= 'zhTW' then return end

local ns = _G.DF_NS or {}

ns.EnsureGearVendorGoods = function()
    ns.EnsureGearVendorGoods = function() return ns.GearVendorGoods end
    if ns.GearVendorGoods then return ns.GearVendorGoods end
    ns.GearVendorGoods = {
    [227853] = {
        name = "皮克斯‧希吉克斯",
        tag = "安德麥商人",
        zone = 33,
        cur = { 3469, "黯淡的幽坑城真幣" },
        groups = {
            { "cloth", "布甲腰帶", { {272393,100}, {272394,100} } },
            { "leather", "皮甲腰帶", { {272395,100}, {272396,100}, {272398,100}, {272401,100} } },
            { "mail", "鎖甲腰帶", { {272397,100}, {272399,100}, {272402,100}, {272410,100} } },
            { "plate", "板甲腰帶", { {272403,100}, {272404,100}, {272405,100} } },
            { "ring", "戒指", { {272406,75}, {272406,{272407,1}}, {272407,75}, {272408,75}, {272409,75} } },
            { "back", "披風", { {272411,75}, {272413,75}, {272414,75}, {272415,75} } },
            { "trinket", "飾品", { {272437,125}, {272438,125}, {272439,125}, {272440,125} } },
            { "relic", "聖物", { {228175,15}, {228176,15}, {272427,50}, {272428,50}, {272429,50}, {272430,50}, {272431,50}, {272432,50}, {272433,50}, {272434,50}, {272435,50}, {272436,50} } },
        },
    },
    }
    return ns.GearVendorGoods
end
