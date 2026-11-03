local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.ExploreBanner = {
    [1] = {
        278030, "inv_misc_token_scarletcrusade", nil, "party",
        85, false, false, "Scarlet Monastery · pick up the echoes from four graves, then use them on the four Library busts in order",
        {
            { h = "Collect the echoes · four graves, any order" },
            { t = "Arathi Highlands 62.2,54.5 north of Go'Shek Farm, among the graves right behind the barn; click the grave to loot the \"Arathi Echo\"",
              m = { { "Arathi Highlands 62.2,54.5", 45, 62.2, 54.5 }, { "Arathi Echo", "item", 215427 } } },
            { t = "Dustwallow Marsh 63.7,42.4 the small graveyard by the road north of Theramore (before the isle bridge); Alliance town, Horde mind the guards — click the grave to loot the \"Theramore Echo\"",
              m = { { "Dustwallow Marsh 63.7,42.4", 15, 63.7, 42.4 }, { "Theramore Echo", "item", 215428 } } },
            { t = "Swamp of Sorrows 16.8,53.8 Splinterspear Junction: the small wooden stick marked with a circle sits against a tree trunk, blended into the bark — walk round the tree; a spider stands next to it; click the stick to loot the \"Swamp Echo\"",
              m = { { "Swamp of Sorrows 16.8,53.8", 8, 16.8, 53.8 }, { "Swamp Echo", "item", 215425 } } },
            { t = "In the Scarlet Monastery Graveyard go to the far end: in the Forlorn Cloister at the back left corner a dead tree leans on the mausoleum's brick wall — the grave carved with chevrons is the only clickable one; click it to loot the \"Graveyard Echo\"",
              m = { { "the Scarlet Monastery Graveyard", 85, false, false }, { "Graveyard Echo", "item", 215426 } } },
            { h = "The Library · in order" },
            { t = "Scarlet Monastery Library: kill Houndmaster Loksey in the Huntsman's Cloister, head for Arcanist Doan, then turn right past the alcove that often holds a chest to enter the \"Gallery of Treasures\"",
              m = { { "Scarlet Monastery Library", 85, false, false } } },
            { t = "Stand right in front of a bust (within 5 yards) and a buff names it (an Elegy); count the busts from the end you enter — the Houndmaster Loksey side — and use the echoes in the order below (a wrong order resets the instance)" },
            { num = "①", t = "Warrior bust ← Swamp Echo (1st from the entrance; the buff is \"Elegy of the Warrior\")",
              m = { { "Swamp Echo", "item", 215425 } } },
            { num = "②", t = "Mage bust ← Arathi Echo (3rd from the entrance; the buff is \"Elegy of the Mage\")",
              m = { { "Arathi Echo", "item", 215427 } } },
            { num = "③", t = "Paladin bust ← Theramore Echo (4th from the entrance; the buff is \"Elegy of the Paladin\")",
              m = { { "Theramore Echo", "item", 215428 } } },
            { num = "④", t = "Priest bust ← Graveyard Echo (2nd from the entrance; the buff is \"Elegy of the Priest\")",
              m = { { "Graveyard Echo", "item", 215426 } } },
            { t = "Once all four busts light up the Scarlet Banner stands in the middle of the gallery — click it to loot; only one player per group gets it, so agree first on who takes it",
              m = { { "Scarlet Banner", "item", 278030 } } },
            { h = "Notes" },
            { n = true, t = "Why this order: the busts honour four archivists of the Monastery (Blake Godwyn, Primwell Skye, Janet Kaitway and William Powell), arranged by their years of service" },
            { n = true, t = "Each echo comes from the place where one of them died" },
            { n = true, t = "Using it requires a campfire nearby, outdoors and out of combat: 10 sec to raise, stands for 15 min, 1 hour cooldown" },
            { n = true, t = "Pure decoration with no stat bonus; it takes a campfire slot and starts the cooldown shared by all camp objects" },
        },
    },
}
