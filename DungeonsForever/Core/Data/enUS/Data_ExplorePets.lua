local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.ExplorePets = {
    [1] = {
        282047, "inv_pet_babycrocodile_toothy", "A", "party",
        1519, false, false, "Canals · Rare-elite drop",
        __display = 147381,
        {
            { t = "Kill the elite patrolling the canal, the Sewer Beast",
              m = { { "Sewer Beast", 1519, false, false } } },
            { t = "It has a chance to drop the Baby Crocolisk; it is very tanky, so bring a group" },
        },
    },
    [2] = {
        275682, "inv_maldraxxusslime", "H", "solo",
        1497, false, false, "Canals · Interactive",
        __display = 144879,
        {
            { t = "Buy a Nutritious Slime Sludge from the vendor Boyle",
              m = { { "Boyle", 1497, 56.2, 64.6 },
                    { "Nutritious Slime Sludge", 1497, 56.2, 64.6 } } },
            { t = "Jump into the canal and find the patrolling Excitable Slime",
              m = { { "Excitable Slime", 1497, false, false } } },
            { t = "Spam /dance at it until it dances back and offers you a quest" },
            { t = "Hand it the sludge to get the Excitable Slime. Afterwards /dance at the pet and it dances too" },
        },
    },
    [3] = {
        268109, "inv_frog2_blue", nil, "easy",
        16593, 51.8, 71.7, "Waterfall-top log · Interactive",
        __display = 6296,
        {
            { t = "Follow the road south across the field and jump onto the log at the top of the waterfall" },
            { t = "Target a Musical Gustjumper and use /sing; the flock vanishes",
              m = { { "Musical Gustjumper", 16593, 51.8, 71.7 } } },
            { t = "Click the frog that appears on the log to get the Musical Gustjumper" },
        },
    },
    [4] = {
        280456, "inv_inscription_pigment_bug04", nil, "easy",
        8, 25.0, 54.2, "Stonard · Quest reward",
        __display = 117132,
        {
            { t = "In Stonard, pick up the quest from Amaryllis Webb (requires level 25); she gives you the Entomology Starter Kit",
              m = { { "Stonard", 8, 25.0, 54.2 },
                    { "Amaryllis Webb", 8, 25.0, 54.2 },
                    { "Entomology Starter Kit", "item", 213565 } } },
            { t = "Head to the Venture Co. camp in northern Stranglethorn Vale and catch an Arbor Tarantula Sample on a tree stump",
              m = { { "Stranglethorn Vale", 33, 45.5, 19.6 },
                    { "Arbor Tarantula Sample", "item", 213566 } } },
            { t = "Go to the Kodo Graveyard in Desolace and catch a Flesh Picker Sample",
              m = { { "Desolace", 405, 53.3, 58.3 },
                    { "Flesh Picker Sample", "item", 213567 } } },
            { t = "Go to the farms in the Arathi Highlands and catch a Hay Weevil Sample",
              m = { { "Arathi Highlands", 45, 32.4, 28.5 },
                    { "Hay Weevil Sample", "item", 213568 } } },
            { t = "Collect all three samples and return to Stonard, hand them to Amaryllis Webb to receive the pet Weevil K. Neevil",
              m = { { "Stonard", 8, 25.0, 54.2 },
                    { "Amaryllis Webb", 8, 25.0, 54.2 },
                    { "Weevil K. Neevil", "item", 280456 } } },
        },
    },
}

ns.ExplorePetMeta = {
    updated = "2026-10-07",
}
