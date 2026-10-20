local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.ClassTier = {
    meta = {
        patch = "1.60.1",
        level = 30,
        updated = "2026/10/06",
    },

    specs = {
        WARRIOR = {
            { key = "arms", name = "Arms", nameEn = "Arms", icon = "Interface\\Icons\\ability_warrior_savageblow" },
            { key = "fury", name = "Fury", nameEn = "Fury", icon = "Interface\\Icons\\ability_warrior_innerrage" },
            { key = "prot", name = "Protection", nameEn = "Protection", icon = "Interface\\Icons\\ability_warrior_defensivestance" },
        },
        PALADIN = {
            { key = "holy", name = "Holy", nameEn = "Holy", icon = "Interface\\Icons\\Spell_Holy_HolyBolt" },
            { key = "prot", name = "Protection", nameEn = "Protection", icon = "Interface\\Icons\\Spell_Holy_DevotionAura" },
            { key = "ret", name = "Retribution", nameEn = "Retribution", icon = "Interface\\Icons\\Spell_Holy_AuraOfLight" },
        },
        HUNTER = {
            { key = "bm", name = "Beast Mastery", nameEn = "Beast Mastery", icon = "Interface\\Icons\\Ability_Hunter_BeastTaming" },
            { key = "mm", name = "Marksmanship", nameEn = "Marksmanship", icon = "Interface\\Icons\\Ability_Marksmanship" },
            { key = "surv", name = "Survival", nameEn = "Survival", icon = "Interface\\Icons\\Ability_Hunter_SwiftStrike" },
        },
        ROGUE = {
            { key = "assa", name = "Assassination", nameEn = "Assassination", icon = "Interface\\Icons\\ability_rogue_eviscerate" },
            { key = "combat", name = "Combat", nameEn = "Combat", icon = "Interface\\Icons\\ability_backstab" },
            { key = "sub", name = "Subtlety", nameEn = "Subtlety", icon = "Interface\\Icons\\ability_stealth" },
        },
        PRIEST = {
            { key = "disc", name = "Discipline", nameEn = "Discipline", icon = "Interface\\Icons\\spell_holy_wordfortitude" },
            { key = "holy", name = "Holy", nameEn = "Holy", icon = "Interface\\Icons\\spell_holy_guardianspirit" },
            { key = "shadow", name = "Shadow", nameEn = "Shadow", icon = "Interface\\Icons\\spell_shadow_shadowwordpain" },
        },
        SHAMAN = {
            { key = "ele", name = "Elemental", nameEn = "Elemental", icon = "Interface\\Icons\\spell_nature_lightning" },
            { key = "enh", name = "Enhancement", nameEn = "Enhancement", icon = "Interface\\Icons\\spell_nature_lightningshield" },
            { key = "resto", name = "Restoration", nameEn = "Restoration", icon = "Interface\\Icons\\Spell_Nature_HealingWaveGreater" },
        },
        MAGE = {
            { key = "arcane", name = "Arcane", nameEn = "Arcane", icon = "Interface\\Icons\\inv_misc_rune_03" },
            { key = "fire", name = "Fire", nameEn = "Fire", icon = "Interface\\Icons\\spell_fire_firebolt02" },
            { key = "frost", name = "Frost", nameEn = "Frost", icon = "Interface\\Icons\\spell_frost_frostbolt02" },
        },
        WARLOCK = {
            { key = "affli", name = "Affliction", nameEn = "Affliction", icon = "Interface\\Icons\\spell_shadow_deathcoil" },
            { key = "demo", name = "Demonology", nameEn = "Demonology", icon = "Interface\\Icons\\spell_shadow_metamorphosis" },
            { key = "destro", name = "Destruction", nameEn = "Destruction", icon = "Interface\\Icons\\spell_shadow_rainoffire" },
        },
        DRUID = {
            { key = "balance", name = "Balance", nameEn = "Balance", icon = "Interface\\Icons\\spell_nature_starfall" },
            { key = "feral", name = "Feral", nameEn = "Feral", icon = "Interface\\Icons\\ability_racial_bearform" },
            { key = "resto", name = "Restoration", nameEn = "Restoration", icon = "Interface\\Icons\\Spell_Nature_HealingTouch" },
        },
    },

    pages = {
        {
            key = "dps",
            intro = "This page will rank the DPS specializations in WoW: Forever, based on their damage output and the notable utility they bring to the party.",
            tiers = {
                { key = "S", specs = { { class = "HUNTER", spec = "bm" }, { class = "HUNTER", spec = "mm" }, { class = "HUNTER", spec = "surv" }, { class = "WARLOCK", spec = "demo" }, { class = "WARLOCK", spec = "affli" }, { class = "WARLOCK", spec = "destro" }, { class = "SHAMAN", spec = "enh" } } },
                { key = "A", specs = { { class = "MAGE", spec = "arcane" }, { class = "MAGE", spec = "fire" }, { class = "MAGE", spec = "frost" }, { class = "PALADIN", spec = "ret" }, { class = "WARRIOR", spec = "arms" }, { class = "WARRIOR", spec = "fury" }, { class = "ROGUE", spec = "sub" }, { class = "ROGUE", spec = "assa" }, { class = "ROGUE", spec = "combat" } } },
                { key = "B", specs = { { class = "DRUID", spec = "feral" }, { class = "SHAMAN", spec = "ele" } } },
                { key = "C", specs = { { class = "PRIEST", spec = "shadow" }, { class = "DRUID", spec = "balance" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "Offensive Throughput", "Simply how much damage the spec contributes to the group." },
                { "Buff Utility", "What your spec brings to the group that benefits your fellow teammates." },
                { "Non-Buff Utility", "Less tangible utility, such as the ability to off-tank in a dire situation." },
                { "Defensive Utility", "This is a smaller consideration, but a dead DPS is a bad DPS. Having a toolkit that allows you to play safe by default will also allow you to have higher uptime on the target." },
            },
            notes = {
                "Note: At this level bracket, there is very little variance between the specs (bar a few outliers), so a spec's placement is a representation of the class, not necessarily the individual spec.",
                "This tier list is based on the current beta build of the game and is strictly limited to level 30; everything is still subject to change, and this guide will be updated accordingly.",
                "This list must be taken with a huge grain of salt. It's designed to be an interesting discussion of what we think will make certain specs valuable, but it should not be used to decide which spec you're going to play or which specs you'll make the players in your guild play!",
                "It is important to note, if your chosen specialization is in a lower tier than expected, all of the DPS can clear all of the content offered in WoW: Forever; it may simply be more challenging than if you were playing a higher-ranked specialization.",
                "It's worth noting that your mileage will vary greatly from player to player and situation to situation. A clear example of this is the Mage's and Warlock's ability to output by far the highest AOE damage in the game during these early levels, but if your group does not pull more than 2-3 mobs at a time, then the Mage will be greatly outshone. Hunter is incredibly strong in those types of environments, but is less adept at AOE damage.",
                "Overall, physical DPS performs the best at level 30 outside of the two outlier classes. Casters can still keep up for the most part, but mostly through using high-value damage-over-time effects or AOE cooldowns, and then wanding for the bulk of the dungeon.",
                "Balance Druid is a bit of an outlier at the bottom, as they don't have any wanding option, but bring a high spell power Thorns on the tank to compensate.",
            },
        },
        {
            key = "tank",
            intro = "This page will rank the Tank specializations in WoW: Forever based on their single-target and AoE tanking capabilities, as well as their utility for the party, including buffs, debuffs, cooldowns, and more.",
            tiers = {
                { key = "S", specs = { { class = "PALADIN", spec = "prot" } } },
                { key = "A", specs = { { class = "WARRIOR", spec = "prot" }, { class = "DRUID", spec = "feral" } } },
                { key = "B", specs = {} },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "Survivability", "This includes the specialization's ability to survive high damage as a Main Tank, such as damage-reduction abilities, cooldowns, overall durability, and potential self-sustain." },
                { "Damage & Threat", "This takes into account how much damage a specialization can deal and the amount of threat it can generate while still focusing on staying alive and main-tanking." },
                { "Trash & Adds", "This focuses mainly on AoE threat generation and survivability." },
                { "Group Utility", "This encompasses the utility a specialization has that helps the party overall." },
            },
            notes = {
                "Note: Each tank will have aspects that they are better or worse at dealing with than other tanks. A high ranking does not automatically mean a tank will be particularly adept in all aspects of the game. But at level 30, the value of AOE threat and damage is a lot higher than it might be at the end-game, which skews the tier list.",
                "Honorary mention: Enhancement Shamans do have tanking support, but don't have a full-fledged tank toolkit. They will be perfectly fine to bring as a dungeon tank, but bringing a Shaman tank to more difficult content will be ill-advised.",
                "This tier list is based on the current beta build of the game and is strictly limited to level 30; everything is still subject to change, and this guide will be updated accordingly.",
                "This list must be taken with a huge grain of salt. It's designed to be an interesting discussion of what we think will make certain specs valuable, but it should not be used to decide which spec you're going to play or which specs you'll make the players in your guild play!",
                "As we mentioned above, a number of points were considered when assigning each specialization its overall rank, but the actual usage of certain tanks will differ depending on what type of content you're engaging in and what your party or raid might need.",
                "With that being said, you can clear all content in WoW: Forever with any tank specialization. Each tank will have their own niche, and if a particular tank becomes unviable, they will likely receive changes to bring them closer to the other tanks.",
                "Protection Paladin stands out as a pick at level 30 as they get access to rank 2 of Consecration. With Retribution Aura scaling with spell power and mana concerns being all but eliminated as the Paladin gets access to more talent points like Shield Specialization, they never struggle with threat and most often stake their spot at the top of the damage meters. Their new level 30 cooldown Templar's Bulwark also has a lot higher value in the early levels compared to the other tanks.",
                "Protection Warriors and Feral Druids perform perfectly fine as well, however. Warriors have increased threat modifiers through spells like Revenge and can now use Thunder Clap in Defensive Stance. Because Shield Block is rage neutral with a rather low cooldown, they can feel sturdier as the other tanks haven't quite got the equivalent tools yet.",
                "Druids can bring their own Thorns, which deals a lot of damage at level 30, and have access to talents that increase the damage of Swipe. While Swipe doesn't scale with Attack Power yet, it is confirmed to be coming in a future build of the beta. Even without attack power modifiers, it can still deal solid damage through talents like Feral Instinct and Savage Fury. Feral Druids also have access to Primal Bite and Leader of the Pack at level 30, which is enormously valuable.",
            },
        },
        {
            key = "healer",
            intro = "This page will rank the Healer specializations in WoW: Forever, based on their healing and absorption output, utility, and overall performance.",
            tiers = {
                { key = "S", specs = { { class = "PRIEST", spec = "disc" }, { class = "PRIEST", spec = "holy" } } },
                { key = "A", specs = { { class = "SHAMAN", spec = "resto" }, { class = "DRUID", spec = "resto" } } },
                { key = "B", specs = { { class = "PALADIN", spec = "holy" } } },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "Healing/Absorption", "This includes the performance of a specialization when either healing or preventing damage, the Tanks and raid group will take." },
                { "Mana Efficiency", "This takes into account the efficiency of a specialization when healing and how often they may run into Mana issues." },
                { "Cooldowns", "This looks at the cooldowns each specialization has for dealing with periods of high incoming damage or other problematic areas." },
                { "Group Utility", "This encompasses the buffs and utility a specialization has that helps the party overall." },
                { "Offensive Utility", "This looks at how much damage the spec brings to their raid if the encounter allows for it." },
            },
            notes = {
                "This tier list is based on the current beta build of the game and is strictly limited to level 30; everything is still subject to change, and this guide will be updated accordingly.",
                "This list must be taken with a huge grain of salt. It's designed to be an interesting discussion of what we think will make certain specs valuable, but it should not be used to decide which spec you're going to play or which specs you'll make the players in your guild play!",
                "It is important to note that if your chosen specialization is in a lower tier than expected, all of the healers can clear all of the content offered in WoW: Forever.",
                "This list aims to give a baseline understanding of the power levels of each healer, but it's worth mentioning that the healer balancing is much closer than in previous iterations, and healers will excel on different encounters and environments.",
                "As we mentioned above, several points were considered when assigning each specialization its overall rank, but the actual usage of certain Healers will differ depending on whether your raid group is farming a raid or progressing it for the first time.",
                "Every healing spec is performing well on the beta, but there are some differences in each healer's toolkit that impacts their standing in the rankings. Priest is doing well all around, and by picking up Wand Specialization, they can output very viable damage without using any mana or interrupting the 5-second rule when it comes to mana regeneration. They are mana efficient and have strong output; Power Word: Shield can also come in very clutch, particularly with it no longer preventing rage generation for Warriors and Druids.",
                "Restoration Shaman is a solid healer, and the totems they bring are certainly valuable, but before you get access to Windfury Totem, the additional free damage that the other healers bring isn't there. With that said, Shamans can certainly get some good damage out by using Searing Totem and Fire Nova. At level 30, they are very mana efficient and allow the group to go at a solid pace without having to stop for mana. You can now also very comfortably go down the Enhancement tree to pick up Improved Stormstrike and Mental Quickness (once you get additional talent points through the legacy system), which allows the shaman to easily deal with the open world while being a strong healer, and a healer who can output competitive damage.",
                "The Restoration Druid sticks out for two primary reasons: First, they have a very rounded toolkit with strong sustained healing and high mana regeneration, but secondly, bringing Thorns to the tank is such a valuable buff with the current spell power scaling of the buff.",
                "Holy Paladin bring Retribution Aura, which fills a similar role to Thorns. At level 30, their healing throughput and mana regeneration are slightly lower than the other healers, but they bring a lot of buffs and utility to make up for that.",
            },
        },
    },
}
