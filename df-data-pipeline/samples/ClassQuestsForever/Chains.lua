-- The class quest chains: which quests make up each card in the journal, in the order
-- the game gives them. Built by hand from Wowhead's quest series, quest givers, zones,
-- levels and race lists (see tools/build_data.py's draft output).
--
--   key       unique id (saved in SavedVariables: don't rename lightly)
--   title     the card's name
--   steps     quest IDs in order; { a, b } = copies of one quest (per race/start), any one counts
--   group     versions of one quest (one per home city or race): shown as one card
--   races     who the chain is for, when its quests don't say (Wowhead often lists none)
--   faction   "A" or "H" when its quests don't all say (else the other faction sees it too)
--   shared    quest IDs this chain shares with another chain of the class (no faction,
--             done by both sides' Skyborne); every other quest is on exactly one chain
--   after     quest ID(s) that must be done first (all); afterAny = one of them
--   reward    { spell = id } shown as the main reward (its icon is the card icon)
--   minLevel  for quests that "require level 1" but belong later (item/object starts)
--   cat       "leveling" (default) or "endgame"
--   extra     only shown while one of its quests is in the log (lead-ins, lost-item replacements)
--   note      a line shown under the title in the detail view (e.g. a prerequisite not in the data)
--   section   journal section of its own instead of the level one (one questline over several cards)
--   anyOrder  step numbers done in any order, all of them needed (e.g. two items for one quest)
--   choice    { a, b }: the copy done in step a (a choice the game offers) picks the copy of
--             step b with the same position, e.g. which shard decides which orb
--   art       preferred talent background for the card art (Interface\TalentFrame\<art>-...);
--             UI/Style.lua mixes in other crops, race scenes of the start zone and the
--             class's other trees so pictures repeat as little as possible
--   artTitle  name of the card's own image (Art/, tools/art_subjects.py) when it differs from
--             the title, e.g. a group version with its own story under the shared card name
local _, CQF = ...
CQF.Chains = {}

local SKYBORNE = { 95, 96 }

-- ---------------------------------------------------------------------------
CQF.Chains.WARRIOR = {
    { key = "war_intro_sky", title = "The Warrior's Path", races = SKYBORNE, steps = { 92532 }, extra = true },

    -- level 10: Defensive Stance, one version per home city, then that trainer's weapon;
    -- the Skyborne learn it from The Skybreaker Bulwark alone (no weapon quests after it)
    { key = "war_skybreaker", title = "Defensive Stance", artTitle = "The Skybreaker Bulwark", group = "war_stance",
      reward = { spell = 71 }, races = SKYBORNE, note = "Also teaches Sunder Armor and Taunt.", art = "WarriorProtection",
      steps = { 94003 } },
    { key = "war_stance_sw", title = "Defensive Stance", group = "war_stance", reward = { spell = 71 }, races = { 1, 3, 4, 7 }, art = "WarriorProtection",
      steps = { 1638, 1639, 1640, 1665 } },
    { key = "war_stance_if", title = "Defensive Stance", group = "war_stance", reward = { spell = 71 }, races = { 1, 3, 4, 7 }, art = "WarriorProtection",
      steps = { 1679, 1678 } },
    { key = "war_stance_darn", title = "Defensive Stance", group = "war_stance", reward = { spell = 71 }, races = { 1, 3, 4, 7 }, art = "WarriorProtection",
      steps = { 1684, 1683 } },
    { key = "war_stance_uc", title = "Defensive Stance", group = "war_stance", reward = { spell = 71 }, races = { 2, 5, 6, 8 }, art = "WarriorProtection",
      steps = { 1818, 1819 } },
    { key = "war_stance_barrens", title = "Defensive Stance", group = "war_stance", reward = { spell = 71 }, races = { 2, 5, 6, 8 }, art = "WarriorProtection",
      steps = { 1505, 1498 } },
    { key = "war_weapon_sw", title = "Dead-tooth Jack", steps = { 1666, 1667 }, after = 1665, races = { 1, 3, 4, 7 }, art = "WarriorArms" },
    { key = "war_weapon_if", title = "Grey Iron Weapons", steps = { 1680, 1681, 1682 }, after = 1678, races = { 1, 3, 4, 7 }, art = "WarriorArms" },
    { key = "war_weapon_darn", title = "Weapons of Elunite", steps = { 1686, 1692, 1693 }, after = 1683, races = { 1, 3, 4, 7 }, art = "WarriorArms" },
    { key = "war_weapon_uc", title = "Heirloom Weapon", steps = { 1820, 1821, 1822 }, after = 1819, races = { 2, 5, 6, 8 }, art = "WarriorArms" },
    { key = "war_weapon_barrens", title = "Forged Steel", steps = { 1502, 1503 }, after = 1498, races = { 2, 5, 6, 8 }, art = "WarriorArms" },

    -- level 20: Brutal Armor (Horde), Fire Hardened Mail and the racial armor (Alliance);
    -- Furen's Armor (1782, not on Wowhead's class list) ends Fire Hardened Mail and opens
    -- the racial armor (QuestieDB)
    { key = "war_brutal", title = "Brutal Armor", steps = { 1823, 1824, 1825, 1838 }, art = "WarriorArms" },
    { key = "war_brutal_hauberk", title = "Brutal Hauberk", steps = { 1848 }, after = 1838, art = "WarriorArms" },
    { key = "war_brutal_gauntlets", title = "Brutal Gauntlets", steps = { 1839, 1842, 1843 }, after = 1838, art = "WarriorArms" },
    { key = "war_brutal_helm", title = "Brutal Helm", steps = { 1840, 1844, 1845 }, after = 1838, art = "WarriorArms" },
    { key = "war_brutal_legs", title = "Brutal Legguards", steps = { 1841, 1846, 1847 }, after = 1838, art = "WarriorArms" },
    { key = "war_firemail", title = "Fire Hardened Mail", steps = { 1698, 1699, 1702, 1701, 1782 }, art = "WarriorArms" },
    { key = "war_armor_human", title = "Grimand's Armor", steps = { 1700, 1705, 1706 }, after = 1782, races = { 1 }, art = "WarriorArms" },
    { key = "war_armor_nelf", title = "Mathiel's Armor", steps = { 1703, 1710, 1711 }, after = 1782, races = { 4 }, art = "WarriorArms" },
    { key = "war_armor_dwarf", title = "Klockmort's Creation", steps = { 1704, 1708, 1709 }, after = 1782, races = { 3, 7 }, art = "WarriorArms" },

    -- level 30: Berserker Stance, then the Whirlwind weapons
    { key = "war_berserker", title = "Berserker Stance", reward = { spell = 2458 }, steps = { 1718, 1719 }, art = "WarriorFury" },
    { key = "war_whirlwind", title = "Whirlwind Weapon", steps = { 1791, 1712, 1713, 1792 }, after = 1719, art = "WarriorFury" },
    { key = "war_exile", title = "Essence of the Exile", steps = { 1714 }, extra = true },

    -- level 50
    { key = "war_kinship", title = "Warrior Kinship", steps = { 8417, 8423, 8424, 8425 }, art = "WarriorFury" },
}

-- ---------------------------------------------------------------------------
CQF.Chains.PALADIN = {
    -- after Deathknell's starter The Mindless Ones (364, every class; QuestieDB). The
    -- level-1 A Difficult Path (98601, a talk with the trainer, no reward) is left out.
    { key = "pal_intro_ud", title = "Rediscovering the Light", races = { 5 }, after = 364, steps = { 90902 } },

    -- Forever's Undead paladins, Tirisfal Glades
    -- prerequisites from QuestieDB (2026-10-16); Wowhead's series boxes for these are
    -- wrong (they put A Second Home before Rediscovering the Light, and Murlocs after it)
    { key = "pal_ud_terms", title = "Coming to Terms", steps = { 91208 }, after = 90902, races = { 5 }, art = "PaladinHoly", extra = true },
    { key = "pal_ud_training", title = "Continue Your Training", steps = { 91209 }, races = { 5 }, art = "PaladinProtection", extra = true },
    { key = "pal_ud_murlocs", title = "Murlocs at the Gates", steps = { 91285, 91294 }, races = { 5 }, art = "PaladinCombat" },
    { key = "pal_ud_home", title = "A Second Home", steps = { 91282 }, races = { 5 }, art = "PaladinHoly", extra = true },
    { key = "pal_ud_repairs", title = "Making Repairs", steps = { 91316 }, after = 91294, races = { 5 }, art = "PaladinProtection" },
    { key = "pal_ud_tarnished", title = "The Tarnished", steps = { 91317, 95803 }, after = 91294, races = { 5 }, art = "PaladinHoly", extra = true },
    { key = "pal_ud_redemption", title = "Redemption", reward = { spell = 7328 }, races = { 5 }, art = "PaladinHoly",
      steps = { 94427, 94434, 94435, 94436, 94438, 94440, 94441 } },
    { key = "pal_ud_silverpine", title = "Diplomatic Incident", races = { 5 }, art = "PaladinCombat",
      steps = { 91858, 91859, 91860, 91861, 91862 }, extra = true },
    { key = "pal_ud_debt", title = "The Debt", steps = { 95034 }, after = 91862, races = { 5 }, art = "PaladinCombat", extra = true },
    { key = "pal_ud_wrath", title = "The Windshaper's Wrath", steps = { 96204 }, after = 91862, races = { 5 }, art = "PaladinCombat", extra = true },
    { key = "pal_ud_moonsilver", title = "The Moonsilver Blade", steps = { 95036, 95111, 95125, 95126 }, after = 91862, art = "PaladinCombat" },
    { key = "pal_ud_korgem", title = "Seeking the Kor Gem", steps = { 95042 }, after = 95036, art = "PaladinCombat" },
    { key = "pal_ud_fireeye", title = "Old Fire-Eye", steps = { 95140 }, after = 91862, races = { 5 }, art = "PaladinCombat" },

    -- level 12: Redemption (Human, Dwarf)
    -- the first step from the paladin trainer himself or a Tome of Divinity sent by another
    -- trainer - one of them (QuestieDB exclusiveTo), all leading to the second step
    { key = "pal_redemption_human", title = "Redemption", artTitle = "Tome of Divinity", reward = { spell = 7328 }, races = { 1 }, art = "PaladinHoly",
      steps = { { 1641, 2998, 3681 }, 1642, 1643, 1644, 1780, 1781, 1786, 1787, 1788 } },
    { key = "pal_redemption_dwarf", title = "Redemption", artTitle = "Tome of Divinity", reward = { spell = 7328 }, races = { 3 }, art = "PaladinHoly",
      steps = { { 1645, 2997, 2999, 3000 }, 1646, 1647, 1648, 1778, 1779, 1783, 1784, 1785 } },
    { key = "pal_symbol_dwarf", title = "The Symbol of Life", steps = { 1789 }, extra = true },
    { key = "pal_symbol_human", title = "The Symbol of Life", steps = { 1790 }, extra = true },

    -- level 20: Verigan's Fist
    { key = "pal_verigan", title = "Verigan's Fist", races = { 1, 3 }, art = "PaladinCombat",
      steps = { { 1793, 1794 }, 1649, 1650, 1651, 1652, 1653, 1654, 1806 } },
    { key = "pal_bailor", title = "Bailor's Ore Shipment", steps = { 1655 }, after = 1653, art = "PaladinCombat" },
    { key = "pal_korgem", title = "Seeking the Kor Gem", steps = { 1442 }, after = 1653, art = "PaladinCombat" },

    -- level 22
    { key = "pal_artifact", title = "A Strange Artifact", art = "PaladinHoly",
      steps = { 78088, 78089, 78090, 78091, 78092, 78093 } },

    -- level 40: the Warhorse
    { key = "pal_warhorse", title = "Summon Warhorse", reward = { spell = 13819 }, art = "PaladinProtection",
      steps = { { 4485, 4486 }, 1661 } },

    -- level 50
    { key = "pal_mightstone", title = "Forging the Mightstone", art = "PaladinHoly", steps = { 8415, 8414, 8416, 8418 } },

    -- level 60: the Charger
    { key = "pal_charger_1", title = "Lord Grayson Shadowbreaker", section = "Charger Questlines", cat = "endgame", art = "PaladinProtection",
      steps = { { 7638, 7670 }, 7637, 7639, 7640 } },
    { key = "pal_charger_2", title = "Collection of Goods", section = "Charger Questlines", cat = "endgame", after = 7640, art = "PaladinProtection",
      steps = { 7641, 7642 } },
    { key = "pal_horsefeed", title = "Manna-Enriched Horse Feed", section = "Charger Questlines", cat = "endgame", afterAny = { 7638, 7670 }, steps = { 7645 } },
    { key = "pal_grimand", title = "Grimand's Finest Work", section = "Charger Questlines", cat = "endgame", after = 7642, steps = { 7648 } },
    { key = "pal_charger", title = "Summon Charger", section = "Charger Questlines", reward = { spell = 23214 }, cat = "endgame", after = 7642, art = "PaladinProtection",
      steps = { 7643, 7644, 7646, 7647 } },
    { key = "pal_ossuary", title = "Again Into the Great Ossuary", steps = { 7666 }, extra = true },
}

-- ---------------------------------------------------------------------------
CQF.Chains.HUNTER = {
    { key = "hun_intro_sky", title = "The Way of the Hunter", races = SKYBORNE, steps = { 92482 }, extra = true },

    -- level 10: the first pet, a version per starting area
    { key = "hun_pet_tauren", title = "Taming the Beast", group = "hun_pet", reward = { spell = 1515 }, art = "HunterBeastMastery",
      steps = { { 6065, 6066, 6067 }, 6061, 6087, 6088, 6089 } },
    { key = "hun_pet_orc", title = "Taming the Beast", group = "hun_pet", reward = { spell = 1515 }, art = "HunterBeastMastery",
      steps = { { 6068, 6069, 6070 }, 6062, 6083, 6082, 6081 } },
    { key = "hun_pet_nelf", title = "Taming the Beast", group = "hun_pet", reward = { spell = 1515 }, art = "HunterBeastMastery",
      steps = { { 6071, 6072, 6073, 6721, 6722 }, 6063, 6101, 6102, 6103 } },
    { key = "hun_pet_dwarf", title = "Taming the Beast", group = "hun_pet", reward = { spell = 1515 }, art = "HunterBeastMastery",
      steps = { { 6074, 6075, 6076 }, 6064, 6084, 6085, 6086 } },
    { key = "hun_pet_sky", title = "Taming the Beast", group = "hun_pet", reward = { spell = 1515 }, races = SKYBORNE, art = "HunterBeastMastery",
      steps = { 94007, 94978, 94979, 94013, 94050 } },
    -- Forever's Human hunters (Wowhead lists Dwarf and Night Elf, who have their own versions)
    { key = "hun_pet_elwynn", title = "Taming the Beast", group = "hun_pet", reward = { spell = 1515 }, races = { 1 }, art = "HunterBeastMastery",
      steps = { 94792, 94863, 94864, 94793 } },

    -- level 50 and 60
    { key = "hun_charm", title = "The Hunter's Charm", art = "HunterSurvival", steps = { 8151, 8153, 8231, 8232 } },
    -- after The Ancient Leaf the other four in any order (QuestieDB, confirmed in game)
    { key = "hun_rhokdelar", title = "Rhok'delar", cat = "endgame", anyOrder = { 2, 3, 4, 5 }, art = "HunterMarksmanship",
      steps = { 7632, 7633, 7634, 7635, 7636 } },
}

-- ---------------------------------------------------------------------------
CQF.Chains.ROGUE = {
    { key = "rog_intro_sky", title = "At Home in the Shadows", races = SKYBORNE, steps = { 92483 }, extra = true },

    -- level 10, a version per home
    { key = "rog10_human", title = "Blade of Cunning", artTitle = "Snatch and Grab", group = "rog10", art = "RogueSubtlety", steps = { 2205, 2206 } },
    { key = "rog10_dwarf", title = "Blade of Cunning", artTitle = "Onin's Report", group = "rog10", art = "RogueSubtlety", steps = { 2218, 2238, 2239 } },
    { key = "rog10_nelf", title = "Blade of Cunning", artTitle = "Destiny Calls", group = "rog10", art = "RogueSubtlety", steps = { 2241, 2242 } },
    { key = "rog10_orc", title = "Blade of Cunning", artTitle = "The Shattered Hand", group = "rog10", art = "RogueSubtlety", steps = { 1859, 1963, 1858 } },
    { key = "rog10_undead", title = "Blade of Cunning", artTitle = "The Deathstalkers", group = "rog10", art = "RogueSubtlety", steps = { 1885, 1886, 1898, 1899, 1978 } },

    -- level 16
    { key = "rog16_human", title = "Alther's Mill", group = "rog16", art = "RogueCombat", steps = { 2300, 2281, 2282 } },
    { key = "rog16_dwarf", title = "Kingly Shakedown", group = "rog16", art = "RogueCombat", steps = { 2299, 2298 } },
    { key = "rog16_nelf", title = "Erion's Behest", group = "rog16", art = "RogueCombat", steps = { 2259, 2260 } },
    { key = "rog16_undead", title = "Tools of the Trade", group = "rog16", art = "RogueCombat", steps = { 1998, 1999 } },
    { key = "rog16_horde", title = "Plundering the Plunderers", group = "rog16", art = "RogueCombat",
      steps = { { 2378, 2380 }, 2379, 2382, 2381 } },

    -- level 20: poisons
    { key = "rog_poisons_a", title = "Poisons", reward = { spell = 2842 }, art = "RogueAssassination",
      steps = { 2360, 2359, 2607, 2608, 2609 } },
    { key = "rog_poisons_h", title = "Poisons", reward = { spell = 2842 }, art = "RogueAssassination",
      steps = { 2460, 2458, 2478, 2479, 2480 } },

    -- the Dead Drop (item and object starts, so the level is the quests' own)
    { key = "rog_xelthos", title = "The Horn of Xelthos", minLevel = 20, art = "RogueSubtlety", steps = { 78261, 78307 } },
    { key = "rog_lockpicks", title = "Goblin Lockpicks", minLevel = 20, after = 78261, art = "RogueSubtlety", steps = { 78270 } },
    { key = "rog_bhossca", title = "The Eye of Bhossca", after = 78307, art = "RogueSubtlety", steps = { 78676, 78699 } },

    -- level 24: Ravenholdt and the Syndicate
    { key = "rog_ravenholdt", title = "The Manor, Ravenholdt", art = "RogueCombat", steps = { 6681, 96779 } },
    { key = "rog_sting", title = "The Syndicate Sting", after = 96779, art = "RogueCombat", steps = { 96783, 96784, 96785, 96786 } },
    { key = "rog_bigidea", title = "What's the Big Idea?", after = 96779, art = "RogueCombat", steps = { 96781, 96782 } },
    { key = "rog_emblems", title = "Syndicate Emblems", steps = { 6701 }, extra = true },

    -- level 50
    { key = "rog_azurekey", title = "The Azure Key", art = "RogueAssassination", steps = { 8233, 8234, 8235, 8236 } },
    { key = "rog_junkboxes", title = "Junkboxes Needed", steps = { 8249 }, extra = true },
}

-- ---------------------------------------------------------------------------
CQF.Chains.PRIEST = {
    -- level 5: the robe, one per race
    { key = "pri_robe_nelf", title = "Garments of the Moon", group = "pri_robe", art = "PriestHoly", steps = { 5622, 5621 } },
    { key = "pri_robe_human", title = "Garments of the Light", group = "pri_robe", art = "PriestHoly", steps = { 5623, 5624 } },
    { key = "pri_robe_dwarf", title = "Garments of the Light", group = "pri_robe", art = "PriestHoly", steps = { 5626, 5625 } },
    { key = "pri_robe_troll", title = "Garments of Spirituality", group = "pri_robe", art = "PriestShadow", steps = { 5649, 5648 } },
    { key = "pri_robe_undead", title = "Garments of Darkness", group = "pri_robe", art = "PriestShadow", steps = { 5651, 5650 } },

    -- level 10: racial spells; each trainer has a copy that sends you home
    { key = "pri_starshards", title = "Starshards", artTitle = "Stars of Elune", reward = { spell = 10797 }, art = "PriestDiscipline",
      steps = { { 5628, 5629, 5630, 5631, 5632, 5633 }, 5627 } },
    { key = "pri_desperate", title = "Desperate Prayer", reward = { spell = 13908 }, art = "PriestHoly",
      steps = { { 5634, 5635, 5636, 5637, 5638, 5639, 5640 } } },
    { key = "pri_hex", title = "Hex of Weakness", reward = { spell = 9035 }, art = "PriestShadow",
      steps = { { 5652, 5654, 5655, 5656, 5657 } } },
    { key = "pri_touch", title = "Touch of Weakness", reward = { spell = 2652 }, art = "PriestShadow",
      steps = { { 5658, 5660, 5661, 5662, 5663 } } },
    { key = "pri_divinegrace", title = "Divine Grace", art = "PriestHoly",
      steps = { { 94773, 94774, 94775, 94776, 94777, 94778, 94779 } } },
    { key = "pri_confounding", title = "Confounding Flash", art = "PriestDiscipline",
      steps = { { 94817, 94821, 94822, 94823, 94824, 94825, 94826 } } },

    -- level 20
    { key = "pri_chastise", title = "Chastise", art = "PriestHoly", steps = { { 5641, 5645, 5647 } } },
    { key = "pri_shadowguard", title = "Shadowguard", reward = { spell = 18137 }, art = "PriestShadow", steps = { { 5642, 5643, 5680 } } },
    { key = "pri_darksacrifice", title = "Dark Sacrifice", art = "PriestShadow", steps = { { 5644, 5646, 5679 } } },
    { key = "pri_elunesgrace", title = "Elune's Grace", reward = { spell = 2651 }, art = "PriestDiscipline", steps = { { 5672, 5673, 5674, 5675 } } },
    { key = "pri_feedback", title = "Feedback", artTitle = "Arcane Feedback", reward = { spell = 13896 }, art = "PriestDiscipline", steps = { { 5676, 5677, 5678 } } },
    { key = "pri_contingency", title = "Contingency Plan", art = "PriestDiscipline", steps = { { 94818, 94819, 94820 } } },

    -- level 35 (the scroll starts the quest); no item or spell reward, so only while in the log
    { key = "pri_trollscroll", title = "The Troll Scroll", minLevel = 32, art = "PriestShadow", steps = { 79731 }, extra = true },

    -- level 50 and 60
    { key = "pri_cenarion", title = "Cenarion Aid", art = "PriestHoly", steps = { 8254, 8255, 8256, 8257 } },
    { key = "pri_balance", title = "The Balance of Light and Shadow", cat = "endgame", art = "PriestDiscipline", steps = { 7622 } },
    { key = "pri_warning", title = "A Warning", cat = "endgame", art = "PriestDiscipline", steps = { 7621 } },
}

-- ---------------------------------------------------------------------------
CQF.Chains.SHAMAN = {
    { key = "sha_intro_sky", title = "Embracing the Elements", races = SKYBORNE, steps = { 92484 }, extra = true },

    -- level 4: Earth
    { key = "sha_earth_orc", title = "Call of Earth", group = "sha_earth", races = { 2, 8 }, art = "ShamanEnhancement", steps = { 1516, 1517, 1518 } },
    { key = "sha_earth_tauren", title = "Call of Earth", group = "sha_earth", races = { 6 }, art = "ShamanEnhancement", steps = { 1519, 1520, 1521 } },
    { key = "sha_earth_dwarf", title = "Call of Earth", group = "sha_earth", art = "ShamanEnhancement", steps = { 94373, 94374, 94375 } },
    -- a level-10 lead from the Ironforge / Dun Morogh trainers to Teo Hammerstorm, for
    -- dwarves who skipped it at level 4 (as the first step it showed "opens at level 10")
    { key = "sha_earth_lead_dwarf", title = "Call of Earth", steps = { 96243 }, extra = true },
    -- the Skyborne's (Horde), Zephras Isle (confirmed in game); Wowhead wrongly lists them
    -- for druids too and gives Tauren/Troll as races - the races here override that
    { key = "sha_earth_sky", title = "Call of Earth", group = "sha_earth", faction = "H", races = SKYBORNE, art = "ShamanEnhancement",
      steps = { 92466, 92467, 92468 } },
    { key = "sha_sapta_earth", title = "Earth Sapta", steps = { { 1462, 1463, 94472 } }, extra = true },

    -- level 10: Fire
    { key = "sha_fire_horde", title = "Call of Fire", group = "sha_fire", art = "ShamanElementalCombat",
      steps = { { 1522, 1523, 2983, 2984 }, 1524, 1525, 1526, 1527 } },
    { key = "sha_fire_dwarf", title = "Call of Fire", group = "sha_fire", art = "ShamanElementalCombat",
      steps = { 94449, 94465, 94466, 94467, 94468 } },
    -- the offering (97244) sits between 97243 and 97245 (QuestieDB); its own art kept
    { key = "sha_fire_sky", title = "Call of Fire", artTitle = "Call of Fire: the Offering", group = "sha_fire", races = SKYBORNE,
      art = "ShamanElementalCombat", steps = { 98517, 97243, 97244, 97245, 97257 } },
    { key = "sha_sapta_fire", title = "Fire Sapta", steps = { { 1464, 94473 } }, extra = true },

    -- level 20: Water
    { key = "sha_water_horde", title = "Call of Water", group = "sha_water", art = "ShamanRestoration",
      steps = { { 1528, 1529, 2985, 2986 }, 1530, 1535, 1536, 1534, 220, 63, 100, 96 } },
    -- Tiev Mordune's: for those who failed to speak to the Minor Manifestation of Water
    { key = "sha_water_retry", title = "Call of Water", faction = "H", steps = { 1103 }, extra = true },
    { key = "sha_water_dwarf", title = "Call of Water", group = "sha_water", art = "ShamanRestoration",
      steps = { 94494, 94495, 94497, 94499, 94500, 94501, 94502, 94503, 94505 } },
    { key = "sha_sapta_water", title = "Water Sapta", steps = { { 972, 94616 } }, extra = true },

    -- level 30: Air, then the storm
    { key = "sha_air_horde", title = "Call of Air", group = "sha_air", art = "ShamanElementalCombat", steps = { { 1531, 1532 } } },
    { key = "sha_air_dwarf", title = "Call of Air", group = "sha_air", art = "ShamanElementalCombat", steps = { 94789 } },
    { key = "sha_air_sky", title = "Call of Air", group = "sha_air", races = SKYBORNE, art = "ShamanElementalCombat", steps = { 96136 } },
    { key = "sha_storm_horde", title = "The Tempest's Weapons", faction = "H", afterAny = { 1531, 1532 }, art = "ShamanEnhancement",
      steps = { 79360, 79364, 79361, 79366, 79442 } },
    { key = "sha_wings", title = "With Wind Beneath Your Wings", after = 79360, art = "ShamanEnhancement", steps = { 79365 } },
    { key = "sha_storm_dwarf", title = "The Tempest's Weapons", faction = "A", after = 94789, art = "ShamanEnhancement",
      steps = { 96264, 79358, 96135, 96016 } },

    -- level 50 and 58
    -- Elemental Mastery (Thunder Bluff) or Mastering the Elements (Orgrimmar) starts it, one or
    -- the other (QuestieDB exclusiveTo)
    { key = "sha_mastery", title = "Da Voodoo", artTitle = "Elemental Mastery", art = "ShamanElementalCombat", steps = { { 8410, 8411 }, 8412, 8413 } },
    { key = "sha_darkreaver", title = "The Darkreaver Menace", cat = "endgame", art = "ShamanEnhancement",
      steps = { 7667, { 7668, 8258 }, 8259 } },
    { key = "sha_ossuary", title = "Again Into the Great Ossuary", steps = { 7669 }, extra = true },
}

-- ---------------------------------------------------------------------------
CQF.Chains.MAGE = {
    { key = "mag_intro_sky", title = "A Student of the Arcane", races = SKYBORNE, steps = { 92481 }, extra = true },

    -- level 10, a version per home
    { key = "mag10_sw", title = "Mirror Lake", group = "mag10", races = { 1 }, art = "MageArcane", steps = { 1860, 1861 } },
    { key = "mag10_if", title = "Mage-tastic Gizmonitor", group = "mag10", races = { 7 }, art = "MageArcane", steps = { 1879, 1880 } },
    { key = "mag10_uc", title = "The Balnir Farmstead", group = "mag10", races = { 5 }, art = "MageArcane", steps = { 1881, 1882 } },
    { key = "mag10_troll", title = "Ju-Ju Heaps", group = "mag10", races = { 2, 8 }, art = "MageArcane", steps = { 1883, 1884 } },
    { key = "mag10_sky", title = "Boughs in the Wind", group = "mag10", races = SKYBORNE, art = "MageArcane", steps = { 93791, 93797 } },

    -- level 15 and 26: the robes
    { key = "mag_robe15_a", title = "Manaweave Robe", art = "MageFire", steps = { 1919, 1920, 1921, 1941 } },
    { key = "mag_robe15_h", title = "Spellfire Robes", art = "MageFire", steps = { 1959, 1960, 1961, 1962 } },
    { key = "mag_robe26_a", title = "Astral Knot Garment", art = "MageFrost", steps = { 1939, 1938, 1940, 1942 } },
    { key = "mag_robe26_h", title = "Nether-lace Garment", art = "MageFrost", steps = { 1943, 1944, 1945, 1946 } },
    -- needs any one of 40 library book quests turned in first (QuestieDB; any class, so not here)
    { key = "mag_research", title = "Research Access", minLevel = 17, note = "Needs one book turned in to the library first",
      art = "MageArcane", steps = { 97286 } },

    -- level 30 and 35: the wand and the orb
    -- after Journey to the Marsh two branches (Hidden Secrets..Rituals of Power, and Items
    -- of Power), both needed for Mage's Wand (QuestieDB)
    { key = "mag_wand", title = "Mage's Wand", anyOrder = { 2, 3, 4, 5 }, art = "MageFire", steps = { 1947, 1949, 1950, 1951, 1948, 1952 } },
    { key = "mag_orb", title = "Celestial Power", art = "MageArcane", steps = { 1953, 1954, 1955, 1956, 1957, 1958 } },

    -- level 50 and 60
    { key = "mag_magecraft", title = "Magecraft", art = "MageFrost", steps = { 8250, 8251, 8252, 8253 } },
    -- Dire Maul: Lorekeeper Lydros (not on Wowhead's class list; corrections.json extraIds)
    { key = "mag_refreshment", title = "Arcane Refreshment", reward = { spell = 10140 }, cat = "endgame", art = "MageFrost", steps = { 7463 } },
    { key = "mag_krellian", title = "Polymorph: Pig", artTitle = "Fragmented Magic", reward = { spell = 28272 }, art = "MageArcane", steps = { 9362, 9364 } },
}

-- ---------------------------------------------------------------------------
CQF.Chains.WARLOCK = {
    -- the starting zones (the Imp)
    { key = "wlk_imp_undead", title = "Summon Imp", artTitle = "Piercing the Veil", group = "wlk_imp", reward = { spell = 688 }, races = { 5 }, art = "WarlockSummoning", steps = { 1470 } },
    { key = "wlk_imp_orc", title = "Summon Imp", artTitle = "Vile Familiars", group = "wlk_imp", reward = { spell = 688 }, races = { 2, 8 }, art = "WarlockSummoning", steps = { 1485, 1499 } },
    { key = "wlk_imp_human", title = "Summon Imp", artTitle = "The Stolen Tome", group = "wlk_imp", reward = { spell = 688 }, races = { 1 }, art = "WarlockSummoning", steps = { 1598 } },
    { key = "wlk_imp_gnome", title = "Summon Imp", artTitle = "Beginnings", group = "wlk_imp", reward = { spell = 688 }, races = { 7 }, art = "WarlockSummoning", steps = { 1599 } },

    -- level 10: the Voidwalker
    { key = "wlk_void_uc", title = "Summon Voidwalker", group = "wlk_void", reward = { spell = 697 }, races = { 5 }, art = "WarlockSummoning",
      steps = { 1478, 1473, 1471 } },
    { key = "wlk_void_org", title = "Summon Voidwalker", group = "wlk_void", reward = { spell = 697 }, races = { 2, 8 }, art = "WarlockSummoning",
      steps = { 1506, 1501, 1504 } },
    { key = "wlk_void_sw", title = "Summon Voidwalker", group = "wlk_void", reward = { spell = 697 }, art = "WarlockSummoning",
      steps = { { 1685, 1715 }, 1688, 1689 } },

    -- level 20: the Succubus (Forever gives the 2021 versions)
    -- level 20: after Devourer of Souls come two lines, both can be done: the Succubus
    -- (Classic's) and the Incubus (Forever's). The Horde takes one city's (Undercity and
    -- Orgrimmar exclude each other); the Alliance starts with Devourer of Souls or Gakin's
    -- Summons (QuestieDB exclusiveTo). The Incubus line has Devourer as its prerequisite.
    { key = "wlk_succ_uc", title = "Summon Succubus", group = "wlk_succ", reward = { spell = 712 }, races = { 5 }, art = "WarlockSummoning",
      steps = { 1472, 1476, 1474 } },
    { key = "wlk_succ_org", title = "Summon Succubus", group = "wlk_succ", reward = { spell = 712 }, races = { 2, 8 }, art = "WarlockSummoning",
      steps = { 1507, 1508, 1509, 1510, 1511, 1515, 1512, 1513 } },
    { key = "wlk_succ_sw", title = "Summon Succubus", group = "wlk_succ", reward = { spell = 712 }, art = "WarlockSummoning",
      steps = { { 1716, 1717 }, 1738, 1739 } },
    { key = "wlk_incu_uc", title = "Summon Incubus", group = "wlk_incu", reward = { spell = 713 }, races = { 5 }, after = 1472,
      art = "WarlockSummoning", steps = { 65593, 65597 } },
    { key = "wlk_incu_org", title = "Summon Incubus", group = "wlk_incu", reward = { spell = 713 }, races = { 2, 8 }, after = 1507,
      art = "WarlockSummoning", steps = { 65601, 65610, 65604 } },
    { key = "wlk_incu_sw", title = "Summon Incubus", group = "wlk_incu", reward = { spell = 713 }, afterAny = { 1716, 1717 },
      art = "WarlockSummoning", steps = { 65602, 65603 } },
    { key = "wlk_soranruk", title = "The Orb of Soran'ruk", art = "WarlockDestruction", steps = { 1740 } },
    -- after A Noble Brew (335, 336: Alliance, any class) for Zardeth of the Black Claw
    { key = "wlk_servedwell", title = "You Have Served Us Well", after = 336, art = "WarlockCurses", steps = { 397 } },

    -- level 30: the Felhunter
    { key = "wlk_felhunter", title = "Summon Felhunter", reward = { spell = 691 }, art = "WarlockSummoning",
      steps = { { 1798, 2996, 3001 }, { 1758, 1801 }, { 1802, 1803 }, { 1804, 1805 }, 1795 } },

    -- level 31 and 35: Menara Voidrender's robe and orb
    { key = "wlk_robe", title = "Enchanted Gold Bloodrobe", art = "WarlockCurses",
      steps = { { 4736, 4737, 4738, 4739 }, 1796, 4781, 4782, 4783, 4784, 4786 } },
    { key = "wlk_goldthread", title = "Fine Gold Thread", steps = { 4785 }, extra = true },
    -- Menara's acolytes offer a choice of shard (step 3); it decides the orb (step 6):
    -- Felhound -> Orb of Dar'Orahil, Infernal -> Orb of Noh'Orahil (QuestieDB prerequisites)
    { key = "wlk_orb", title = "The Orb of Orahil", art = "WarlockDestruction", choice = { 3, 6 },
      steps = { { 4965, 4967, 4968, 4969 }, 1799, { 4962, 4963 }, 4961, 4976, { 4964, 4975 } } },

    -- level 40: the Felsteed
    { key = "wlk_felsteed", title = "Summon Felsteed", reward = { spell = 5784 }, art = "WarlockSummoning",
      steps = { { 3631, 4487, 4488, 4489 }, 4490 } },

    -- level 50
    { key = "wlk_kroshius", title = "Inferno", artTitle = "Kroshius' Infernal Core", reward = { spell = 1122 }, art = "WarlockDestruction", steps = { 7601, 7602, 7603 } },
    -- Impsy's: An Imp's Request (from the city trainers) or Hot and Itchy (from Impsy himself)
    -- start it - one or the other (QuestieDB exclusiveTo), both lead to The Wrong Stuff
    { key = "wlk_imp_request", title = "Trolls of a Feather", art = "WarlockCurses", steps = { { 8419, 8420 }, 8421, 8422 } },

    -- level 60: the Dreadsteed
    { key = "wlk_doomguard", title = "Ritual of Doom", artTitle = "The Prison's Bindings", reward = { spell = 18540 }, anyOrder = { 1, 2 }, cat = "endgame", art = "WarlockDestruction", steps = { 7581, 7582, 7583 } },
    { key = "wlk_dread_1", title = "Mor'zul Bloodbringer", section = "Dreadsteed Questlines", cat = "endgame", art = "WarlockSummoning", steps = { 7562, 7563, 7564 } },
    { key = "wlk_dread_2", title = "Lord Banehollow", section = "Dreadsteed Questlines", cat = "endgame", after = 7564, art = "WarlockSummoning", steps = { 7623, 7624, 7625, 7629 } },
    { key = "wlk_bell", title = "Bell of Dethmoora", section = "Dreadsteed Questlines", cat = "endgame", after = 7564, steps = { 7626 } },
    { key = "wlk_wheel", title = "Wheel of the Black March", section = "Dreadsteed Questlines", cat = "endgame", after = 7564, steps = { 7627 } },
    { key = "wlk_candle", title = "Doomsday Candle", section = "Dreadsteed Questlines", cat = "endgame", after = 7564, steps = { 7628 } },
    { key = "wlk_arcanite", title = "Arcanite", section = "Dreadsteed Questlines", cat = "endgame", after = { 7626, 7627, 7628 }, steps = { 7630 } },
    { key = "wlk_dreadsteed", title = "Summon Dreadsteed", section = "Dreadsteed Questlines", reward = { spell = 23161 }, cat = "endgame", art = "WarlockSummoning",
      after = { 7626, 7627, 7628, 7629, 7630 }, steps = { 7631 } },
}

-- ---------------------------------------------------------------------------
CQF.Chains.DRUID = {
    { key = "dru_intro_sky", title = "A Student of Nature", races = SKYBORNE, steps = { 92485 }, extra = true },

    -- level 10: Bear Form
    { key = "dru_bear_a", title = "Bear Form", group = "dru_bear", reward = { spell = 5487 }, art = "DruidFeralCombat",
      steps = { { 5923, 5924, 5925 }, 5921, 5929, 5931, 6001 } },
    { key = "dru_bear_h", title = "Bear Form", group = "dru_bear", reward = { spell = 5487 }, art = "DruidFeralCombat",
      steps = { { 5926, 5927, 5928 }, 5922, 5930, 5932, 6002 } },
    { key = "dru_bear_sky", title = "Bear Form", artTitle = "The Great Ursera Spirit", group = "dru_bear", reward = { spell = 5487 }, races = SKYBORNE,
      art = "DruidFeralCombat", steps = { 94006, 94638 } },

    -- Skyborne druids train with their faction's Night Elf / Tauren druids. Wowhead lists
    -- only Tauren on the Thunder Bluff quests; QuestieDB has the Windshapers (96) on the
    -- Cat Form start and end there and on the Horde Bear Form copies, so the Horde chains
    -- name both races (Windshaper Aquatic Form / Cure Poison not yet seen in game).

    -- level 14: Cure Poison
    { key = "dru_cure_a", title = "Cure Poison", artTitle = "Power over Poison", reward = { spell = 8946 }, art = "DruidRestoration",
      faction = "A", races = { 4, 95 }, steps = { 6121, 6122, 6123, 6124, 6125 } },
    { key = "dru_cure_h", title = "Cure Poison", artTitle = "Power over Poison", reward = { spell = 8946 }, art = "DruidRestoration",
      faction = "H", races = { 6, 96 }, steps = { 6126, 6127, 6128, 6129, 6130 } },

    -- level 16: Aquatic Form
    { key = "dru_aquatic_a", title = "Aquatic Form", reward = { spell = 1066 }, art = "DruidBalance",
      faction = "A", races = { 4, 95 }, steps = { 26, 29, 272, 5061 } },
    { key = "dru_aquatic_h", title = "Aquatic Form", reward = { spell = 1066 }, art = "DruidBalance",
      faction = "H", races = { 6, 96 }, steps = { 27, 28, 30, 31 } },

    -- level 20: Cat Form (Forever's). The Skyborne meet the Windborne cat spirit, quests
    -- with no faction that both sides' Skyborne share (`shared`, see tools/validate.py).
    { key = "dru_cat_a", title = "Cat Form", reward = { spell = 768 }, art = "DruidFeralCombat",
      faction = "A", races = { 4, 95 }, steps = { 98393, { 98394, 98341 }, { 98396, 98404 }, { 98731, 98738 }, 98397 } },
    { key = "dru_cat_h", title = "Cat Form", reward = { spell = 768 }, art = "DruidFeralCombat",
      faction = "H", races = { 6, 96 }, shared = { 98341, 98404, 98738 },
      steps = { 98340, { 98405, 98341 }, { 98342, 98404 }, { 98739, 98738 }, 98362 } },

    -- level 50
    { key = "dru_torwa", title = "Torwa Pathfinder", art = "DruidRestoration", steps = { 9063, 9052, 9051, 9053 } },
}
