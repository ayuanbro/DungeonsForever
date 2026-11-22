local ns = _G.DF_NS or {}

ns.EnsureProfMoonwells = function()
    ns.EnsureProfMoonwells = function() return ns.ProfMoonwells end
    if ns.ProfMoonwells then return ns.ProfMoonwells end
ns.ProfMoonwells = {
    ["tailoring"] = {
        zones = {
            { map = 1450, fac = "B",
              name_zh = "月光林地", name_tw = "月光林地", name_en = "Moonglade",
              note_zh = "中立地区，安全首选", note_tw = "中立地區，安全首選", note_en = "Neutral ground, the safest first choice",
              list = {
                { x = 46.2, y = 45.3 },
                { x = 48.6, y = 33.0 },
                { x = 52.5, y = 41.5 },
              } },
            { map = 1440, fac = "B",
              name_zh = "灰谷", name_tw = "灰谷", name_en = "Ashenvale",
              note_zh = "争夺地区，碎木岗哨一带部落最常用", note_tw = "爭奪地區，碎木崗哨一帶部落最常用", note_en = "Contested; Horde players favor the Splintertree Post area",
              list = {
                { x = 60.2, y = 72.9, loc_zh = "碎木岗哨附近 · |cFFFF5C42部落推荐|r", loc_tw = "碎木崗哨附近 · |cFFFF5C42部落推薦|r", loc_en = "Near Splintertree Post · |cFFFF5C42Horde pick|r" },
                { x = 59.3, y = 60.0, loc_zh = "莱恩伍德营地", loc_tw = "萊恩伍德營地", loc_en = "Raynewood Retreat" },
                { x = 53.8, y = 46.0 },
              } },
            { map = 1438, fac = "A",
              name_zh = "泰达希尔", name_tw = "泰達希爾", name_en = "Teldrassil",
              note_zh = "联盟领地", note_tw = "聯盟領地", note_en = "Alliance territory",
              list = {
                { x = 56.0, y = 62.0, loc_zh = "多兰纳尔", loc_tw = "多蘭納爾", loc_en = "Dolanaar" },
                { x = 59.9, y = 33.1, loc_zh = "暗影谷", loc_tw = "暗影谷", loc_en = "Shadowglen" },
                { x = 63.4, y = 58.1, loc_zh = "星风村", loc_tw = "星風村", loc_en = "Starfall Village" },
                { x = 38.4, y = 34.1, loc_zh = "预言林地", loc_tw = "預言林地", loc_en = "Oracle Glade" },
                { x = 25.4, y = 64.8 },
                { x = 47.2, y = 63.5 },
              } },
            { map = 1457, fac = "A",
              name_zh = "达纳苏斯", name_tw = "達納蘇斯", name_en = "Darnassus",
              note_zh = "联盟主城", note_tw = "聯盟主城", note_en = "Alliance capital city",
              list = {
                { x = 39, y = 82, loc_zh = "月神殿", loc_tw = "月神殿", loc_en = "Temple of the Moon",
                  note_zh = "传送门出来就是", note_tw = "傳送門出來就是", note_en = "Right outside the portal" },
              } },
            { map = 1439, fac = "A",
              name_zh = "黑海岸", name_tw = "黑海岸", name_en = "Darkshore",
              note_zh = "联盟领地", note_tw = "聯盟領地", note_en = "Alliance territory",
              list = {
                { x = 37.8, y = 44.0, loc_zh = "奥伯丁", loc_tw = "奧伯丁", loc_en = "Auberdine" },
                { x = 82.3, y = 12.4 },
                { x = 84.5, y = 11.0 },
              } },
            { map = 1448, fac = "B",
              name_zh = "费伍德森林", name_tw = "費伍德森林", name_en = "Felwood",
              list = {
                { x = 35.1, y = 59.8 },
                { x = 32.3, y = 66.5,
                  note_zh = "腐化月亮井，任务《腐化之井》", note_tw = "腐化月亮井，任務《腐化之井》", note_en = "Corrupted moonwell, quest site" },
              } },
            { map = 1444, fac = "B",
              name_zh = "菲拉斯", name_tw = "菲拉斯", name_en = "Feralas",
              list = {
                { x = 46.0, y = 46.0, loc_zh = "羽月要塞", loc_tw = "羽月要塞", loc_en = "Feathermoon Stronghold",
                  note_zh = "联盟驻地", note_tw = "聯盟駐地", note_en = "Alliance stronghold" },
                { x = 58.0, y = 44.0, loc_zh = "厄运之门（北）", loc_tw = "厄運之門（北）", loc_en = "Dire Maul (North entrance)" },
                { x = 87.0, y = 44.0, loc_zh = "新塔拉纳尔", loc_tw = "新塔拉納爾", loc_en = "New Thalanaar" },
              } },
            { map = 1453, fac = "A",
              name_zh = "暴风城", name_tw = "暴風城", name_en = "Stormwind City",
              note_zh = "东部王国唯一", note_tw = "東部王國唯一", note_en = "The only one in the Eastern Kingdoms",
              list = {
                { x = 35.9, y = 65.7, loc_zh = "花园区", loc_tw = "花園區", loc_en = "The Park",
                  note_zh = "德鲁伊训练师旁", note_tw = "德魯伊訓練師旁", note_en = "Next to the druid trainer" },
              } },
            { map = 1446, fac = "B",
              name_zh = "希利苏斯", name_tw = "希利蘇斯", name_en = "Silithus",
              list = {
                { x = 49.0, y = 37.7, loc_zh = "塞纳里奥要塞", loc_tw = "塞納里奧要塞", loc_en = "Cenarion Hold" },
              } },
            { map = 1431, fac = "B",
              name_zh = "暮色森林", name_tw = "暮色森林", name_en = "Duskwood",
              list = {
                { x = 49.0, y = 33.0, loc_zh = "暮光林地", loc_tw = "暮光林地", loc_en = "Twilight Grove" },
              } },
            { map = 1447, fac = "B",
              name_zh = "艾萨拉", name_tw = "艾薩拉", name_en = "Azshara",
              list = {
                { x = 10.8, y = 74.7 },
                { x = 35.6, y = 49.9, loc_zh = "辛玛洛神殿", loc_tw = "辛瑪洛神殿", loc_en = "Temple of Zin-Malor",
                  note_zh = "神殿室内", note_tw = "神殿室內", note_en = "Inside the temple" },
              } },
        },
    },
}
    return ns.ProfMoonwells
end
