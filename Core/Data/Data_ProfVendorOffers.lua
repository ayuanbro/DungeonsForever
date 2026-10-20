-- Verified Forever vendor shelves, inspected 2026-10-18.
-- Each row is { itemID, purchase bundle size }; no purchase prices are stored.
-- Wowhead NPC table: data-type="number" is the bundle size; parentheses in
-- data-type="quantity" are limited stock and are excluded from this table.
-- This catalogue establishes supply metadata only; pricing is not configured.
-- Source evidence and rejected limited rows: tests/data/vendor-price-reference.json.
local _, ns = ...

ns.ProfVendorOffers = {}
ns.ProfVendorOfferAudit = { verifiedAt = "2026-10-18", version = 3, sources = {} }

local function Shelf(npcID, name, faction, rows, limited, npcFactionID)
    local url = "https://www.wowhead.com/forever/npc=" .. npcID
    local loc = ns.ProfVendors and ns.ProfVendors[npcID]
    ns.ProfVendorOfferAudit.sources[#ns.ProfVendorOfferAudit.sources + 1] = {
        npcID = npcID, url = url, unlimitedCount = #rows, excludedLimited = limited,
    }
    for _, row in ipairs(rows) do
        local id = row[1]
        local offers = ns.ProfVendorOffers[id]
        if not offers then offers = {}; ns.ProfVendorOffers[id] = offers end
        offers[#offers + 1] = {
            itemID = id, npcID = npcID, npcName = name, faction = faction,
            npcFactionID = npcFactionID, unlimited = true, available = true,
            source = "wowhead-forever", url = url, verifiedAt = "2026-10-18",
            quantity = row[2], bundleSize = row[2], catalogueOnly = true,
            areaID = loc and loc[1], mapID = loc and loc[2],
            x = loc and loc[3], y = loc and loc[4],
        }
    end
end

-- Neutral general supplies: neither limited patterns nor future gathered
-- reagents are treated as an always-available purchasing source.
Shelf(12022, "Lorelae Wintersong", "N", {
    {2320, 1}, {2321, 1}, {2324, 1}, {2325, 1}, {2604, 1},
    {2678, 5}, {2692, 1}, {2880, 1}, {2901, 1}, {2928, 1},
    {3371, 5}, {3372, 5}, {3466, 1}, {3713, 1}, {3857, 1},
    {4289, 1}, {4291, 1}, {4340, 1}, {4341, 1}, {4342, 1},
    {4399, 1}, {4400, 1}, {5956, 1}, {6217, 1}, {6256, 1},
    {6530, 1}, {6532, 1}, {7005, 1}, {8343, 1}, {8925, 5},
}, {14483,16224,16243}, 609)

Shelf(2670, "Xizk Goodstitch", "N", {
    {2320, 1}, {2321, 1}, {2324, 1}, {2325, 1}, {2604, 1},
    {2605, 1}, {4291, 1}, {4340, 1}, {4341, 1}, {4342, 1},
    {6260, 1}, {6261, 1}, {8343, 1}, {10290, 1}, {14341, 1},
    {253665, 1}, {253668, 1},
}, {7087,14630,217258}, 21)

-- Unlimited reagents; all eight herb rows and the alchemy formula are limited.
Shelf(1313, "Maria Lumere", "A", {
    {3371, 5}, {3372, 5}, {8925, 5}, {18256, 5},
}, {765,785,2447,2449,2453,3355,3356,3357,9301}, 72)

-- Unlimited dyes/threads. Limited old patterns are deliberately absent.
Shelf(4168, "Elynna", "A", {
    {2320, 1}, {2321, 1}, {2324, 1}, {2325, 1}, {2604, 1},
    {2605, 1}, {4291, 1}, {4340, 1}, {4341, 1}, {4342, 1},
    {6260, 1}, {6261, 1}, {8343, 1}, {10290, 1}, {14341, 1},
    {253665, 1}, {253668, 1},
}, {6272,6275,10311}, 69)

Shelf(3133, "Herble Baubbletump", "N", {
    {2880, 1}, {2901, 1}, {3466, 1}, {3857, 1}, {4399, 1},
    {4400, 1}, {5956, 1}, {10647, 1}, {10648, 1},
}, {4357,4361,4363,4364,4371,4382,4389,4404})

Shelf(7854, "Jangdor Swiftstrider", "H", {
    {2320, 1}, {2321, 1}, {2325, 1}, {2604, 1}, {2605, 1},
    {4289, 1}, {4291, 1}, {4340, 1}, {4341, 1}, {4342, 1},
    {6260, 1}, {6261, 1}, {7005, 1}, {8343, 1}, {10290, 1},
    {14341, 1}, {252783, 1}, {252784, 1}, {252811, 1},
    {252812, 1}, {252942, 1},
}, {7451,8385,8409,15734,217271}, 81)

-- Dust and Lesser Magic Essence on both enchanting shelves are LIMITED.
-- Mote of Magic is a distinct Forever reagent, not Strange Dust.
Shelf(5158, "Tilli Thistlefuzz", "A", {
    {4470, 1}, {6217, 1}, {11291, 1}, {20752, 1}, {20753, 1},
    {20758, 1}, {22307, 1}, {247786, 1},
}, {6342,6349,10938,10940}, 54)

Shelf(3346, "Kithas", "H", {
    {4470, 1}, {6217, 1}, {11291, 1}, {20752, 1}, {20753, 1},
    {20758, 1}, {22307, 1}, {247786, 1},
}, {6342,6346,6349,10938,10940}, 76)

Shelf(5594, "Alchemist Pestlezugg", "N", {
    {3371, 5}, {3372, 5}, {8925, 5}, {18256, 5},
    {9303, 1}, {9304, 1}, {12958, 1},
}, {6057,9305}, 369)

-- Raw fish are limited even though the innkeeper's drinks are unlimited.
Shelf(6807, "Innkeeper Skindle", "N", {
    {159, 5}, {1179, 5}, {1205, 5}, {1645, 5},
    {1708, 5}, {8766, 5},
}, {4603,6289,6303,6308,6362,8959}, 21)

-- Confirmed by the item's Sold by table (Stock infinity, stack 1).
Shelf(2832, "Nixxrax Fillamug", "N", { {2596, 1} }, {}, 21)
ns.ProfVendorOffers[2596][1].url = "https://www.wowhead.com/forever/item=2596/skin-of-dwarven-stout"

Shelf(2622, "Sly Garrett", "N", {
    {2928, 1}, {2930, 1}, {3371, 5}, {3372, 5}, {5060, 1},
    {5140, 1}, {5173, 1}, {8923, 1}, {8924, 1}, {8925, 5},
}, {}, 21)

-- Forever's summoned Reagent Bot, full 65-row shelf (two list pages).
-- Availability of a summoned bot is not inferred from this catalogue: route
-- calculations require an explicit confirmed character access condition.
Shelf(242498, "Reagent Bot", "N", {
    {159, 5}, {2320, 1}, {2321, 1}, {2324, 1}, {2325, 1}, {2604, 1},
    {2605, 1}, {2678, 5}, {2692, 1}, {2880, 1}, {2901, 1}, {3466, 1},
    {3713, 1}, {3857, 1}, {4289, 1}, {4291, 1}, {4340, 1}, {4341, 1},
    {4342, 1}, {4399, 1}, {4400, 1}, {4470, 1}, {4471, 1},
    {4536, 5}, {5565, 1}, {5956, 1}, {6256, 1}, {6260, 1},
    {6261, 1}, {6529, 1}, {6530, 1}, {6532, 1}, {7005, 1}, {8343, 1},
    {10284, 1}, {10290, 1}, {10647, 1}, {10648, 1}, {11291, 1},
    {14341, 1}, {16583, 1}, {17020, 1}, {17021, 1}, {17026, 1},
    {17028, 1}, {17029, 1}, {17030, 1}, {17031, 1}, {17032, 1},
    {17033, 1}, {17034, 1}, {17035, 1}, {17036, 1}, {17037, 1},
    {17038, 1}, {18567, 1}, {21099, 1}, {21177, 20},
    {21219, 1}, {253665, 1}, {253668, 1}, {272941, 1}, {273636, 1},
}, {4357,4364})
for _, offers in pairs(ns.ProfVendorOffers) do
    for _, offer in ipairs(offers) do
        if offer.npcID == 242498 then offer.summoned = true end
    end
end

-- Permanent neutral alternative for elemental flux; item's Sold by table
-- explicitly confirms unlimited stock and a one-item purchase bundle.
Shelf(5411, "Krinkle Goodsteel", "N", { {18567, 1} }, {}, 369)
for _, offer in ipairs(ns.ProfVendorOffers[18567]) do
    if offer.npcID == 5411 then offer.url = "https://www.wowhead.com/forever/item=18567/elemental-flux" end
end

ns.ProfVendorOfferAudit.unverifiedAvailability = { 215369, 215370 }
ns.ProfVendorOfferAudit.notes = {
    "This catalogue stores suppliers, purchase bundles and availability conditions, with no purchase prices.",
    "Summoned suppliers require confirmed character access before they are available.",
    "NPC 263384 sells Gift of Galloping, not crafting reagents; not included.",
    "No unlimited-stock claim is inferred for herbs, raw fish or engineering parts.",
    "Unlisted reagent/vendor pairs are unknown, not proof that no vendor exists.",
}
