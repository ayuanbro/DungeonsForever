if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end

local ns = _G.DF_NS or {}

ns.ClassTier = {
    meta = {
        patch = "1.60.1",
        level = 60,
        updated = "2026/11/03",
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
            intro = "This page ranks the DPS specializations in WoW: Forever by damage, buffs, and survivability.",
            tiers = {
                { key = "S", specs = { { class = "HUNTER", spec = "surv" }, { class = "WARLOCK", spec = "demo" }, { class = "WARLOCK", spec = "destro" }, { class = "PALADIN", spec = "ret" }, { class = "WARRIOR", spec = "fury" } } },
                { key = "A", specs = { { class = "HUNTER", spec = "mm" }, { class = "SHAMAN", spec = "enh" }, { class = "MAGE", spec = "fire" }, { class = "HUNTER", spec = "bm" }, { class = "MAGE", spec = "arcane" }, { class = "WARLOCK", spec = "affli" }, { class = "WARRIOR", spec = "arms" }, { class = "DRUID", spec = "feral" }, { class = "ROGUE", spec = "combat" } } },
                { key = "B", specs = { { class = "PRIEST", spec = "shadow" }, { class = "ROGUE", spec = "sub" }, { class = "DRUID", spec = "balance" }, { class = "ROGUE", spec = "assa" }, { class = "MAGE", spec = "frost" } } },
                { key = "C", specs = { { class = "SHAMAN", spec = "ele" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "Offensive Throughput", "How much damage the spec adds to the group." },
                { "Buff Utility", "Buffs the spec brings to the party and raid." },
                { "Non-Buff Utility", "Harder to measure, but useful in a pinch, such as off-tanking." },
                { "Stackability", "How many of this spec a raid wants." },
                { "Defensive Utility", "A minor factor, but a dead DPS deals no damage." },
            },
            notes = {
                "Based on theorycrafting and simulation; gear and spell coefficient data is still limited, so take it as a discussion, not a verdict.",
                "Every DPS spec can clear all content; a lower tier only means it takes more effort.",
                "S is worth stacking, A sees plenty of play, B is not a priority but is not bad, and C is the weakest yet still playable.",
                "No spec is currently in D-tier.",
            },
        },
        {
            key = "tank",
            intro = "This page ranks the Tank specializations in WoW: Forever by survivability, utility, and damage.",
            tiers = {
                { key = "S", specs = { { class = "DRUID", spec = "feral" } } },
                { key = "A", specs = { { class = "WARRIOR", spec = "prot" }, { class = "PALADIN", spec = "prot" } } },
                { key = "B", specs = {} },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "Main Tank Survivability", "Surviving heavy damage: mitigation, cooldowns, durability, self-sustain." },
                { "Off-Tank Capability", "Damage while not tanking, plus help for the main tank and healers." },
                { "Main Tank Damage & Threat", "Damage and threat while main-tanking." },
                { "Trash & Adds", "AOE threat and survival during trash." },
                { "Raid Utility", "What the tank adds to the raid." },
            },
            notes = {
                "Any tank can clear all content; the ranking only says who has an easier time.",
                "Feral Druid is the steadiest: highest armor and effective health, and it can shift to Cat while not tanking, making it the best off-tank.",
                "Protection Warrior has the strongest defensive cooldowns and brings raid value through Sunder Armor and Thunder Clap, so it is nearly mandatory. Protection Paladin has the highest damage and threat, but needs gear and is vulnerable to spikes.",
                "Honorary mention: Enhancement Shaman works as a dungeon tank, but it lacks a full tank toolkit, so do not bring it to a raid.",
            },
        },
        {
            key = "healer",
            intro = "This page ranks the Healer specializations in WoW: Forever by healing and absorption, utility, and damage.",
            tiers = {
                { key = "S", specs = { { class = "SHAMAN", spec = "resto" } } },
                { key = "A", specs = { { class = "DRUID", spec = "resto" }, { class = "PRIEST", spec = "holy" } } },
                { key = "B", specs = { { class = "PRIEST", spec = "disc" } } },
                { key = "C", specs = { { class = "PALADIN", spec = "holy" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "Healing/Absorption", "Healing or preventing the damage the raid takes." },
                { "Mana Efficiency", "Healing efficiency and how often mana runs dry." },
                { "Cooldowns", "Tools for periods of heavy damage." },
                { "Raid Utility", "Buffs and utility the healer brings to the raid." },
                { "Offensive Utility", "Damage the healer adds when the fight allows." },
            },
            notes = {
                "Healers are very close and each excels somewhere; this list is only a baseline.",
                "Every healer can clear all content.",
                "Restoration Shaman is S: the best totem utility, with Chain Heal and Riptide covering the tank efficiently.",
                "Restoration Druid is A: the highest raid healing throughput, and it shines in fights with rot damage.",
                "Holy Priest is A with strong mana efficiency; Discipline is B and best when raid healing is light; Holy Paladin is C, steady on tank healing but weaker overall.",
            },
        },
    },
}
