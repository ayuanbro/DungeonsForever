local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.BossSkills = {
    onyxias_lair = {
        ["Onyxia"] = {
            { "", "", 15847, "inv_misc_monsterscales_05" },
            { "", "", 18500, "inv_misc_monsterscales_14" },
            { "", "", 18392, "spell_fire_flamebolt" },
            { "", "", 17086, "spell_fire_fire" },
            { "", "", 14100, "ability_devour" },
        },
    },
    hall_of_thanes = {
        ["Faldrim Anvilmar"] = {
            { "", "", 26048, "spell_shadow_unholyfrenzy" },
            { "", "", 1292602, "achievement_bg_killingblow_startingrock" },
        },
        ["Magmatus"] = {
            { "", "", 1293228, "spell_fire_incinerate" },
        },
        ["Plunder"] = {
            { "", "", 10101, "inv_gauntlets_05" },
        },
        ["Durgen Dirgehammer"] = {
            { "", "", 26070, "spell_shadow_possession" },
            { "", "", 12054, "ability_gouge" },
        },
    },
    ragefire_chasm = {
        ["Oggleflint"] = {
            { "", "", 15496, "ability_warrior_cleave" },
        },
        ["Taragaman the Hungerer"] = {
            { "", "", 11970, "spell_fire_sealoffire" },
            { "", "", 18072, "inv_gauntlets_05" },
        },
        ["Jergosh the Invoker"] = {
            { "", "", 18267, "spell_shadow_curseofmannoroth" },
            { "", "", 20800, "spell_fire_immolation" },
        },
        ["Bazzalan"] = {
            { "", "", 14873, "spell_shadow_ritualofsacrifice" },
            { "", "", 2818, "ability_rogue_dualweild" },
        },
    },
    ruins_of_lordaeron = {
        ["The Baron"] = {
            { "", "", 17307, "inv_gauntlets_05" },
        },
        ["Witherfang"] = {
            { "", "", 3358, "spell_nature_nullifypoison" },
        },
        ["The Abandoned"] = {
            { "", "", 1220855, "spell_frost_frostnova" },
            { "", "", 1266011, "spell_shadow_lifedrain02" },
        },
        ["Bjork"] = {
            { "", "", 1301635, "spell_shadow_antimagicshell" },
        },
        ["Rath'mael"] = {
            { "", "", 1279983, "spell_fire_selfdestruct" },
        },
        ["Viktor the Vile"] = {
            { "", "", 3358, "spell_nature_nullifypoison" },
        },
    },
    wailing_caverns = {
        ["Lord Cobrahn"] = {
            { "", "", 5187, "spell_nature_healingtouch" },
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 8040, "spell_nature_sleep" },
            { "", "", 7965, "spell_nature_guardianward" },
        },
        ["Lady Anacondra"] = {
            { "", "", 5187, "spell_nature_healingtouch" },
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 700, "spell_nature_sleep" },
            { "", "", 8148, "spell_nature_thorns" },
        },
        ["Kresh"] = {
            { "", "", 13496, "spell_frost_stun" },
        },
        ["Lord Pythas"] = {
            { "", "", 5187, "spell_nature_healingtouch" },
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 700, "spell_nature_sleep" },
            { "", "", 8147, "spell_nature_thunderclap" },
        },
        ["Skum"] = {
            { "", "", 6254, "spell_nature_chainlightning" },
        },
        ["Lord Serpentis"] = {
            { "", "", 5187, "spell_nature_healingtouch" },
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 700, "spell_nature_sleep" },
        },
        ["Verdan the Everliving"] = {
            { "", "", 8142, "spell_nature_earthquake" },
        },
        ["Mutanus the Devourer"] = {
            { "", "", 8150, "spell_nature_thunderclap" },
            { "", "", 7399, "ability_physical_taunt" },
            { "", "", 7967, "spell_nature_sleep" },
        },
    },
    the_deadmines = {
        ["Rhahk'Zor"] = {
            { "", "", 6304, "inv_gauntlets_05" },
        },
        ["Miner Johnson"] = {
            { "", "", 12097, "spell_shadow_vampiricaura" },
        },
        ["Sneed"] = {
            { "", "", 3603, "ability_racial_cannibalize" },
            { "", "", 7399, "ability_physical_taunt" },
            { "", "", 6713, "ability_warrior_disarm" },
        },
        ["Sneed's Shredder"] = {
            { "", "", 3603, "ability_racial_cannibalize" },
            { "", "", 7399, "ability_physical_taunt" },
            { "", "", 6713, "ability_warrior_disarm" },
        },
        ["Gilnid"] = {
            { "", "", 3605, "ability_repair" },
            { "", "", 5213, "spell_fire_fireball" },
        },
        ["Mr. Smite"] = {
            { "", "", 674, "ability_dualwield" },
            { "", "", 6264, "ability_meleedamage" },
            { "", "", 6435, "inv_gauntlets_05" },
            { "", "", 6432, "ability_warstomp" },
            { "", "", 3391, "ability_ghoulfrenzy" },
        },
        ["Captain Greenskin"] = {
            { "", "", 15496, "ability_warrior_cleave" },
            { "", "", 5208, "ability_poisons" },
        },
        ["Edwin VanCleef"] = {
            { "", "", 674, "ability_dualwield" },
            { "", "", 853, "spell_holy_sealofmight" },
            { "", "", 3391, "ability_ghoulfrenzy" },
        },
        ["Cookie"] = {
            { "", "", 6306, "inv_drink_06" },
            { "", "", 5174, "spell_holy_heal" },
        },
    },
    shadowfang_keep = {
        ["Rethilgore"] = {
            { "", "", 7295, "spell_shadow_lifedrain02" },
        },
        ["Fel Steed / Shadow Charger"] = {
            { "", "", 7139, "ability_warstomp" },
        },
        ["Razorclaw the Butcher"] = {
            { "", "", 7485, "spell_shadow_siphonmana" },
        },
        ["Baron Silverlaine"] = {
            { "", "", 7068, "spell_shadow_gathershadows" },
        },
        ["Commander Springvale"] = {
            { "", "", 5588, "spell_holy_sealofmight" },
            { "", "", 1026, "spell_holy_holybolt" },
        },
        ["Odo the Blindwatcher"] = {
            { "", "", 7481, "ability_bullrush" },
        },
        ["Deathsworn Captain"] = {
            { "", "", 15496, "ability_warrior_cleave" },
            { "", "", 9080, "ability_shockwave" },
        },
        ["Fenrus the Devourer"] = {
            { "", "", 7125, "spell_nature_corrosivebreath" },
        },
        ["Wolf Master Nandos"] = {
            { "", "", 7487, "spell_shadow_chilltouch" },
            { "", "", 7489, "spell_shadow_chilltouch" },
            { "", "", 7488, "spell_shadow_chilltouch" },
        },
        ["Archmage Arugal"] = {
            { "", "", 7621, "spell_shadow_gathershadows" },
            { "", "", 7587, "spell_shadow_antishadow" },
            { "", "", 7803, "spell_lightning_lightningbolt01" },
            { "", "", 22709, "spell_shadow_shadowbolt" },
        },
    },
    excavation_wetlands = {
        ["Saltspine"] = {
            { "", "", 3604, "ability_criticalstrike" },
            { "", "", 1316382, "spell_shadow_mindsteal" },
        },
        ["Shadetooth"] = {
            { "", "", 12054, "ability_gouge" },
            { "", "", 14100, "ability_devour" },
            { "", "", 18501, "spell_shadow_unholyfrenzy" },
        },
        ["Relic Guardian"] = {
            { "", "", 15588, "spell_nature_thunderclap" },
        },
    },
    blackfathom_deeps = {
        ["Ghamoo-ra"] = {
            { "", "", 5568, "spell_nature_natureswrath" },
        },
        ["Lady Sarevess"] = {
            { "", "", 8435, "spell_nature_chainlightning" },
            { "", "", 865, "spell_frost_frostnova" },
            { "", "", 6660, "ability_marksmanship" },
            { "", "", 246, "spell_nature_slow" },
        },
        ["Gelihast"] = {
            { "", "", 6533, "ability_ensnare" },
        },
        ["Twilight Lord Kelris"] = {
            { "", "", 15587, "spell_shadow_unholyfrenzy" },
            { "", "", 8399, "spell_nature_sleep" },
        },
        ["Aku'mai"] = {
            { "", "", 1715 },
            { "", "", 2974 },
            { "", "", 3490, "spell_shadow_unholyfrenzy" },
            { "", "", 3815, "spell_nature_regenerate" },
        },
    },
    the_stockade = {
        ["Kam Deepfury"] = {
            { "", "", 7164, "ability_warrior_defensivestance" },
            { "", "", 3419, "spell_fire_firearmor" },
            { "", "", 8242, "ability_warrior_shieldbash" },
        },
        ["Targorr the Dread"] = {
            { "", "", 674, "ability_dualwield" },
            { "", "", 8599, "spell_shadow_unholyfrenzy" },
            { "", "", 3391, "ability_ghoulfrenzy" },
        },
        ["Hamhock"] = {
            { "", "", 6742, "spell_nature_bloodlust" },
            { "", "", 421, "spell_nature_chainlightning" },
        },
        ["Bazil Thredd"] = {
            { "", "", 9128, "ability_warrior_battleshout" },
            { "", "", 674, "ability_dualwield" },
            { "", "", 7964, "ability_hibernation" },
        },
        ["Dextren Ward"] = {
            { "", "", 7165, "ability_warrior_offensivestance" },
            { "", "", 5246, "ability_golemthunderclap" },
            { "", "", 11976, "ability_rogue_ambush" },
        },
        ["Bruegal Ironknuckle"] = {
            { "", "", 13496, "spell_frost_stun" },
        },
    },
    city_of_dalaran = {
        ["Atrexis the Grave Knight"] = {
            { "", "", 6713, "ability_warrior_disarm" },
            { "", "", 1303266, "spell_shadow_raisedead" },
            { "", "", 1303264, "spell_shadow_unholyfrenzy" },
            { "", "", 3391, "ability_ghoulfrenzy" },
            { "", "", 12057, "ability_rogue_ambush" },
        },
        ["Lyn the Ignored"] = {
            { "", "", 17228, "spell_shadow_shadowbolt" },
            { "", "", 1304473, "spell_shadow_antishadow" },
            { "", "", 1303266, "spell_shadow_raisedead" },
        },
        ["Arcane Anomaly"] = {
            { "", "", 1241501, "ability_mage_arcanesurge" },
            { "", "", 15230, "spell_arcane_starfire" },
        },
        ["Arcanic Enigma"] = {
            { "", "", 1240869, "spell_nature_wispsplode" },
            { "", "", 1224125, "spell_holy_silence" },
            { "", "", 1304455, "spell_holy_mindsooth" },
        },
        ["Unstable Sentinel"] = {
            { "", "", 1241329, "spell_arcane_blast" },
        },
        ["Mana Devourer"] = {
            { "", "", 1240738, "ability_druid_twilightswrath" },
            { "", "", 1240750, "spell_shadow_chilltouch" },
        },
        ["Fel Ancient"] = {
            { "", "", 22994, "spell_nature_stranglevines" },
            { "", "", 1240706, "spell_fire_felflamering" },
        },
        ["Shade of the Archmage"] = {
            { "", "", 1303598, "spell_nature_doublepolymorph2" },
            { "", "", 1303599, "spell_nature_purge" },
            { "", "", 15230, "spell_arcane_starfire" },
            { "", "", 28450, "spell_nature_wispsplode" },
            { "", "", 1241515, "ability_mage_netherwindpresence" },
        },
    },
    gnomeregan = {
        ["Electrocutioner 6000"] = {
            { "", "", 11085, "spell_nature_chainlightning" },
            { "", "", 11082, "spell_nature_chainlightning" },
            { "", "", 11084, "spell_nature_wispheal" },
        },
        ["Crowd Pummeler 9-60"] = {
            { "", "", 8374, "ability_warrior_cleave" },
            { "", "", 10887, "inv_gauntlets_04" },
            { "", "", 5568, "spell_nature_natureswrath" },
        },
        ["Dark Iron Ambassador"] = {
            { "", "", 184, "spell_fire_immolation" },
            { "", "", 9053, "spell_fire_flamebolt" },
            { "", "", 10870, "spell_fire_fire" },
        },
        ["Mekgineer Thermaplugg"] = {
            { "", "", 7915, "inv_misc_foot_kodo" },
            { "", "", 11130, "inv_gauntlets_05" },
        },
    },
    razorfen_kraul = {
        ["Aggem Thorncurse"] = {
            { "", "", 8286, "spell_magic_polymorphpig" },
        },
        ["Death Speaker Jargba"] = {
            { "", "", 14515, "spell_shadow_shadowworddominate" },
            { "", "", 9613, "spell_shadow_shadowbolt" },
        },
        ["Roogug"] = {
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 8270, "spell_nature_earthquake" },
        },
        ["Overlord Ramtusk"] = {
            { "", "", 8259, "inv_spear_05" },
            { "", "", 15548, "spell_nature_thunderclap" },
        },
        ["Agathelos the Raging"] = {
            { "", "", 8260, "ability_warstomp" },
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
        },
        ["Blind Hunter"] = {
            { "", "", 8281, "spell_shadow_teleport" },
            { "", "", 3242, "ability_ghoulfrenzy" },
        },
        ["Charlga Razorflank"] = {
            { "", "", 8292, "spell_nature_chainlightning" },
            { "", "", 8361, "spell_holy_holybolt" },
            { "", "", 6077, "spell_holy_renew" },
        },
        ["Earthcaller Halmgar"] = {
            { "", "", 2484, "spell_nature_strengthofearthtotem02" },
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 8270, "spell_nature_earthquake" },
        },
    },
    sm_graveyard = {
        ["Interrogator Vishas"] = {
            { "", "", 9034, "spell_fire_immolation" },
        },
        ["Azshir the Sleepless"] = {
            { "", "", 5137, "spell_shadow_chilltouch" },
            { "", "", 9373, "spell_shadow_lifedrain02" },
            { "", "", 7399, "ability_physical_taunt" },
        },
        ["Fallen Champion"] = {
            { "", "", 7369, "ability_warrior_cleave" },
            { "", "", 7366, "ability_racial_avatar" },
            { "", "", 15496, "ability_warrior_cleave" },
        },
        ["Ironspine"] = {
            { "", "", 3815, "spell_nature_regenerate" },
            { "", "", 21007, "spell_shadow_curseofmannoroth" },
        },
        ["Bloodmage Thalnos"] = {
            { "", "", 9613, "spell_shadow_shadowbolt" },
            { "", "", 8814, "spell_fire_selfdestruct" },
            { "", "", 12470, "spell_fire_sealoffire" },
        },
    },
    sm_library = {
        ["Houndmaster Loksey"] = {
            { "", "", 12824, "spell_nature_polymorph" },
            { "", "", 6742, "spell_nature_bloodlust" },
            { "", "", 4304, "ability_meleedamage" },
            { "", "", 11549, "ability_warrior_battleshout" },
        },
        ["Arcanist Doan"] = {
            { "", "", 9435, "spell_fire_selfdestruct" },
            { "", "", 1449, "spell_nature_wispsplode" },
            { "", "", 30225, "spell_holy_silence" },
            { "", "", 9438, "spell_holy_divineintervention" },
            { "", "", 9433, "spell_nature_wispsplode" },
            { "", "", 13323, "spell_nature_polymorph" },
            { "", "", 8988, "spell_holy_silence" },
        },
    },
    sm_armory = {
        ["Herod"] = {
            { "", "", 1680, "ability_whirlwind" },
            { "", "", 22540, "ability_warrior_cleave" },
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 8260, "ability_warstomp" },
            { "", "", 8989, "ability_whirlwind" },
        },
    },
    razorfen_downs = {
        ["Tuten'kash"] = {
            { "", "", 12255, "spell_nature_drowsy" },
            { "", "", 12254, "spell_shadow_requiem" },
            { "", "", 12252, "ability_ensnare" },
        },
        ["Mordresh Fire Eye"] = {
            { "", "", 12470, "spell_fire_sealoffire" },
            { "", "", 12466, "spell_fire_flamebolt" },
        },
        ["Glutton"] = {
            { "", "", 12627, "spell_nature_abolishmagic" },
            { "", "", 12795, "spell_shadow_unholyfrenzy" },
        },
        ["Ragglesnout"] = {
            { "", "", 7645, "spell_shadow_shadowworddominate" },
            { "", "", 10892, "spell_shadow_shadowwordpain" },
            { "", "", 11659, "spell_shadow_shadowbolt" },
            { "", "", 12039, "spell_holy_heal" },
        },
        ["Amnennar the Coldbringer"] = {
            { "", "", 13009, "ability_kick" },
            { "", "", 15531, "spell_frost_frostnova" },
            { "", "", 15530, "spell_frost_frostbolt02" },
            { "", "", 12642, "spell_shadow_summonvoidwalker" },
        },
        ["Plaguemaw the Rotting"] = {
            { "", "", 12946, "spell_shadow_callofbone" },
            { "", "", 12947, "spell_shadow_requiem" },
        },
    },
    sm_cathedral = {
        ["High Inquisitor Fairbanks"] = {
            { "", "", 16098, "spell_shadow_ritualofsacrifice" },
            { "", "", 6213, "spell_shadow_possession" },
            { "", "", 700, "spell_nature_sleep" },
            { "", "", 17, "spell_holy_powerwordshield" },
            { "", "", 6064, "spell_holy_heal02" },
            { "", "", 8282, "spell_shadow_ritualofsacrifice" },
            { "", "", 12039, "spell_holy_heal" },
            { "", "", 11647, "spell_holy_powerwordshield" },
            { "", "", 8399, "spell_nature_sleep" },
        },
        ["Scarlet Commander Mograine"] = {
            { "", "", 853, "spell_holy_sealofmight" },
            { "", "", 642, "spell_holy_divineintervention" },
            { "", "", 8990, "spell_holy_auraoflight" },
            { "", "", 14518, "spell_holy_holysmite" },
            { "", "", 9257, "spell_holy_layonhands" },
        },
        ["High Inquisitor Whitemane"] = {
            { "", "", 25054, "spell_holy_holysmite" },
            { "", "", 700, "spell_nature_sleep" },
            { "", "", 9232, "spell_holy_resurrection" },
            { "", "", 2054, "spell_holy_heal" },
            { "", "", 9481, "spell_holy_holysmite" },
            { "", "", 12039, "spell_holy_heal" },
            { "", "", 9256, "spell_nature_sleep" },
            { "", "", 22187, "spell_holy_powerwordshield" },
        },
    },
    uldaman = {
        ["Baelog"] = {
            { "", "", 20252, "ability_rogue_sprint" },
            { "", "", 8242, "ability_warrior_shieldbash" },
        },
        ["Revelosh"] = {
            { "", "", 16033, "spell_nature_chainlightning" },
            { "", "", 9532, "spell_nature_lightning" },
        },
        ["Ironaya"] = {
            { "", "", 8374, "ability_warrior_cleave" },
            { "", "", 45, "ability_bullrush" },
            { "", "", 18670, "inv_gauntlets_05" },
        },
        ["Obsidian Sentinel"] = {
            { "", "", 10072, "spell_shadow_burningspirit" },
            { "", "", 10061, "spell_shadow_teleport" },
        },
        ["Ancient Stone Keeper"] = {
            { "", "", 10094, "spell_nature_earthbind" },
        },
        ["Galgann Firehammer"] = {
            { "", "", 15039, "spell_fire_flameshock" },
            { "", "", 9482, "spell_fire_fireball" },
            { "", "", 3356, "spell_fire_fireball" },
            { "", "", 11970, "spell_fire_sealoffire" },
        },
        ["Grimlok"] = {
            { "", "", 7289, "spell_shadow_antishadow" },
            { "", "", 9532, "spell_nature_lightning" },
            { "", "", 8292, "spell_nature_chainlightning" },
            { "", "", 6742, "spell_nature_bloodlust" },
        },
        ["Archaedas"] = {
            { "", "", 6524, "spell_nature_earthquake" },
            { "", "", 10252, "spell_nature_earthquake" },
            { "", "", 10258, "spell_nature_earthquake" },
        },
    },
    zul_farrak = {
        ["Antu'sul"] = {
            { "", "", 8376, "spell_nature_naturetouchdecay" },
            { "", "", 11899, "spell_holy_layonhands" },
            { "", "", 11894, "classic_temp" },
            { "", "", 11895, "spell_holy_heal02" },
        },
        ["Theka the Martyr"] = {
            { "", "", 8600, "spell_nature_nullifydisease" },
            { "", "", 11089, "spell_shadow_antishadow" },
        },
        ["Witch Doctor Zum'rah"] = {
            { "", "", 12491, "spell_nature_magicimmunity" },
            { "", "", 12739, "spell_shadow_shadowbolt" },
            { "", "", 15245, "spell_shadow_shadowbolt" },
            { "", "", 11086, "spell_totem_wardofdraining" },
        },
        ["Nekrum Gutchewer"] = {
            { "", "", 12039, "spell_holy_heal" },
            { "", "", 13704, "spell_shadow_psychicscream" },
            { "", "", 8362, "spell_holy_renew" },
            { "", "", 15537, "spell_shadow_shadowbolt" },
        },
        ["Shadowpriest Sezz'ziz"] = {
            { "", "", 12039, "spell_holy_heal" },
            { "", "", 13704, "spell_shadow_psychicscream" },
            { "", "", 8362, "spell_holy_renew" },
            { "", "", 15537, "spell_shadow_shadowbolt" },
        },
        ["Sergeant Bly"] = {
            { "", "", 12170, "ability_warrior_revenge" },
            { "", "", 11972, "ability_warrior_shieldbash" },
        },
        ["Hydromancer Velratha"] = {
            { "", "", 12491, "spell_nature_magicimmunity" },
            { "", "", 12739, "spell_shadow_shadowbolt" },
            { "", "", 15245, "spell_shadow_shadowbolt" },
            { "", "", 11086, "spell_totem_wardofdraining" },
        },
        ["Gahz'rilla"] = {
            { "", "", 11836, "spell_frost_glacier" },
            { "", "", 11902, "ability_devour" },
            { "", "", 11131, "spell_frost_frostbolt02" },
        },
        ["Chief Ukorz Sandscalp"] = {
            { "", "", 11837, "ability_warrior_cleave" },
            { "", "", 15496, "ability_warrior_cleave" },
            { "", "", 7366, "ability_racial_avatar" },
        },
        ["Zerillis"] = {
            { "", "", 12551, "spell_ice_magicdamage" },
            { "", "", 6533, "ability_ensnare" },
            { "", "", 15547, "ability_marksmanship" },
        },
    },
    maraudon = {
        ["Noxxion"] = {
            { "", "", 21687, "spell_nature_corrosivebreath" },
            { "", "", 18072, "inv_gauntlets_05" },
        },
        ["Razorlash"] = {
            { "", "", 15284, "ability_warrior_cleave" },
            { "", "", 15976, "ability_gouge" },
        },
        ["Lord Vyletongue"] = {
            { "", "", 14443, "ability_upgrademoonglaive" },
            { "", "", 7964, "ability_hibernation" },
            { "", "", 1953, "spell_arcane_blink" },
        },
        ["Meshlok the Harvester"] = {
            { "", "", 11876, "ability_bullrush" },
            { "", "", 15501, "spell_nature_earthshock" },
            { "", "", 13446, "ability_rogue_ambush" },
        },
        ["Celebras the Cursed"] = {
            { "", "", 9739, "spell_nature_lightning" },
            { "", "", 6913, "spell_nature_forceofnature" },
            { "", "", 12747, "spell_nature_stranglevines" },
            { "", "", 21793, "spell_nature_tranquility" },
        },
        ["Landslide"] = {
            { "", "", 5568, "spell_nature_natureswrath" },
            { "", "", 10101, "inv_gauntlets_05" },
        },
        ["Tinkerer Gizlock"] = {
            { "", "", 13183, "spell_fire_incinerate" },
            { "", "", 6660, "ability_marksmanship" },
            { "", "", 8858, "spell_fire_selfdestruct" },
        },
        ["Rotgrip"] = {
            { "", "", 15976, "ability_gouge" },
            { "", "", 16495, "ability_backstab" },
        },
        ["Princess Theradras"] = {
            { "", "", 21868, "spell_nature_cyclone" },
            { "", "", 21869, "ability_golemthunderclap" },
            { "", "", 9483, "ability_throw" },
            { "", "", 6346, "spell_holy_excorcism" },
            { "", "", 18499, "spell_nature_ancestralguardian" },
            { "", "", 8143, "spell_nature_tremortotem" },
        },
    },
    sunken_temple = {
        ["Avatar of Hakkar"] = {
            { "", "", 12888, "spell_shadow_shadowworddominate" },
            { "", "", 12889, "spell_shadow_curseoftounges" },
            { "", "", 25852, "ability_criticalstrike" },
            { "", "", 10896, "spell_shadow_shadowwordpain" },
        },
        ["Dreamscythe"] = {
            { "", "", 12533, "spell_nature_acid_01" },
            { "", "", 12882, "spell_nature_earthbind" },
        },
        ["Weaver"] = {
            { "", "", 12533, "spell_nature_acid_01" },
            { "", "", 12882, "spell_nature_earthbind" },
        },
        ["Hazzas"] = {
            { "", "", 12533, "spell_nature_acid_01" },
            { "", "", 12882, "spell_nature_earthbind" },
        },
        ["Morphaz"] = {
            { "", "", 12533, "spell_nature_acid_01" },
            { "", "", 12882, "spell_nature_earthbind" },
        },
        ["Shade of Eranikus"] = {
            { "", "", 16740, "ability_bullrush" },
            { "", "", 12890, "spell_shadow_cripple" },
            { "", "", 3391, "ability_ghoulfrenzy" },
            { "", "", 12533, "spell_nature_acid_01" },
            { "", "", 10941, "spell_magic_lesserinvisibilty" },
            { "", "", 1038, "spell_holy_sealofsalvation" },
            { "", "", 11303, "ability_rogue_feint" },
        },
    },
    blackrock_depths = {
        ["Lord Roccor"] = {
            { "", "", 13728, "spell_nature_earthshock" },
            { "", "", 13729, "spell_fire_flameshock" },
        },
        ["High Interrogator Gerstahn"] = {
            { "", "", 13704, "spell_shadow_psychicscream" },
            { "", "", 18499, "spell_nature_ancestralguardian" },
            { "", "", 14032, "spell_shadow_shadowwordpain" },
            { "", "", 14033, "spell_shadow_manaburn" },
            { "", "", 12040, "spell_shadow_antishadow" },
        },
        ["Houndmaster Grebmar"] = {
            { "", "", 21049, "spell_nature_bloodlust" },
            { "", "", 13730, "ability_warrior_warcry" },
            { "", "", 15615, "inv_gauntlets_04" },
        },
        ["Ring of Law: Gorosh the Dervish"] = {
            { "", "", 15589, "ability_whirlwind" },
            { "", "", 15708, "ability_warrior_savageblow" },
            { "", "", 21049, "spell_nature_bloodlust" },
        },
        ["Ring of Law: Grizzle"] = {
            { "", "", 13728, "spell_nature_earthshock" },
            { "", "", 6524, "spell_nature_earthquake" },
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
        },
        ["Ring of Law: Eviscerator"] = {
            { "", "", 28599, "spell_shadow_shadowbolt" },
            { "", "", 16874, "spell_shadow_antishadow" },
            { "", "", 7121, "spell_shadow_antimagicshell" },
            { "", "", 16095, "ability_gouge" },
        },
        ["Ring of Law: Ok'thor the Breaker"] = {
            { "", "", 14621, "spell_nature_polymorph" },
            { "", "", 26192, "spell_nature_wispsplode" },
            { "", "", 25055, "spell_arcane_starfire" },
            { "", "", 13747, "spell_nature_slow" },
        },
        ["Ring of Law: Anub'shiah"] = {
            { "", "", 15470, "spell_shadow_curseoftounges" },
            { "", "", 15471, "spell_nature_earthbind" },
            { "", "", 15472, "spell_shadow_shadowbolt" },
            { "", "", 12493, "spell_shadow_curseofmannoroth" },
            { "", "", 13787, "spell_shadow_ragingscream" },
        },
        ["Ring of Law: Hedrum the Creeper"] = {
            { "", "", 15475, "spell_nature_corrosivebreath" },
            { "", "", 3609, "ability_poisonsting" },
            { "", "", 15474, "ability_ensnare" },
        },
        ["Pyromancer Loregrain"] = {
            { "", "", 15038, "spell_fire_searingtotem" },
            { "", "", 15095, "spell_fire_fire" },
            { "", "", 15616, "spell_fire_flameshock" },
            { "", "", 15041, "spell_fire_firearmor" },
        },
        ["Warder Stilgiss"] = {
            { "", "", 12675, "spell_frost_frostbolt02" },
            { "", "", 15044, "spell_frost_frostward" },
            { "", "", 12674, "spell_frost_frostnova" },
            { "", "", 12556, "spell_frost_frostarmor02" },
        },
        ["Verek"] = {
            { "", "", 12675, "spell_frost_frostbolt02" },
            { "", "", 15044, "spell_frost_frostward" },
            { "", "", 12674, "spell_frost_frostnova" },
            { "", "", 12556, "spell_frost_frostarmor02" },
        },
        ["Fineous Darkvire"] = {
            { "", "", 8258, "spell_holy_devotionaura" },
            { "", "", 15493, "spell_holy_holybolt" },
            { "", "", 13953, "ability_thunderbolt" },
            { "", "", 11978, "ability_kick" },
            { "", "", 15346, "spell_holy_sealofwrath" },
        },
        ["Lord Incendius"] = {
            { "", "", 26977, "spell_fire_lavaspawn" },
            { "", "", 13900, "spell_fire_firebolt" },
            { "", "", 13899, "spell_fire_selfdestruct" },
            { "", "", 14099, "inv_gauntlets_05" },
        },
        ["Bael'Gar"] = {
            { "", "", 13880, "spell_fire_immolation" },
            { "", "", 13895, "spell_fire_lavaspawn" },
        },
        ["General Angerforge"] = {
            { "", "", 15572, "ability_warrior_sunder" },
        },
        ["Golem Lord Argelmach"] = {
            { "", "", 15305, "spell_nature_chainlightning" },
            { "", "", 15507, "spell_nature_lightningshield" },
            { "", "", 15605, "spell_nature_wispheal" },
        },
        ["Phalanx"] = {
            { "", "", 14099, "inv_gauntlets_05" },
            { "", "", 15588, "spell_nature_thunderclap" },
            { "", "", 15285, "spell_fire_flamebolt" },
        },
        ["Ambassador Flamelash"] = {
            { "", "", 13489, "spell_fire_fire" },
            { "", "", 14744, "spell_fire_fire" },
        },
        ["Panzor the Invincible"] = {
            { "", "", 9941, "spell_shadow_teleport" },
        },
        ["Magmus"] = {
            { "", "", 13900, "spell_fire_firebolt" },
            { "", "", 24375, "ability_bullrush" },
        },
        ["Emperor Dagran Thaurissan"] = {
            { "", "", 17492, "spell_fire_fireball" },
            { "", "", 15636, "spell_fire_incinerate" },
            { "", "", 15642, "spell_holy_auraoflight" },
        },
    },
    dire_maul_east = {
        ["Pusillin"] = {
            { "", "", 17145, "spell_holy_excorcism_02" },
            { "", "", 14145, "spell_fire_fireball" },
            { "", "", 15242, "spell_fire_flamebolt" },
            { "", "", 22735, "inv_misc_food_55" },
            { "", "", 1769, "ability_kick" },
            { "", "", 2139, "spell_frost_iceshock" },
        },
        ["Zevrim Thornhoof"] = {
            { "", "", 22478, "spell_shadow_shadowwordpain" },
            { "", "", 22651, "spell_shadow_antimagicshell" },
            { "", "", 10894, "spell_shadow_shadowwordpain" },
        },
        ["Hydrospawn"] = {
            { "", "", 22419, "ability_warrior_disarm" },
            { "", "", 22420, "spell_shadow_demonbreath" },
            { "", "", 22421, "spell_frost_summonwaterelemental" },
            { "", "", 22714, "spell_frost_chillingblast" },
            { "", "", 22715, "spell_frost_chillingblast" },
        },
        ["Lethtendris"] = {
            { "", "", 22709, "spell_shadow_shadowbolt" },
            { "", "", 14887, "spell_shadow_shadowbolt" },
            { "", "", 20787, "spell_fire_immolation" },
            { "", "", 13338, "spell_shadow_curseoftounges" },
            { "", "", 16247, "spell_shadow_antishadow" },
            { "", "", 22710, "spell_nature_strength" },
        },
        ["Alzzin the Wildshaper"] = {
            { "", "", 22661, "ability_creature_poison_03" },
            { "", "", 22662, "spell_nature_nullifydisease" },
            { "", "", 22128, "spell_nature_thorns" },
            { "", "", 22691, "ability_warrior_disarm" },
            { "", "", 10101, "inv_gauntlets_05" },
            { "", "", 7948, "spell_nature_rejuvenation" },
            { "", "", 22660, "spell_nature_spiritwolf" },
            { "", "", 22689, "ability_druid_disembowel" },
            { "", "", 19319, "ability_racial_cannibalize" },
            { "", "", 11599, "ability_warrior_sunder" },
            { "", "", 11198, "ability_warrior_riposte" },
            { "", "", 768, "ability_druid_catform" },
        },
    },
    lower_blackrock_spire = {
        ["Highlord Omokk"] = {
            { "", "", 5532, "ability_warrior_cleave" },
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 18945, "inv_gauntlets_05" },
        },
        ["Shadow Hunter Vosh'gajin"] = {
            { "", "", 8282, "spell_shadow_ritualofsacrifice" },
            { "", "", 22566, "spell_nature_polymorph" },
        },
        ["War Master Voone"] = {
            { "", "", 5532, "ability_warrior_cleave" },
        },
        ["Mother Smolderweb"] = {
            { "", "", 16104, "spell_shadow_teleport" },
            { "", "", 16468, "ability_creature_poison_02" },
        },
        ["Urok Doomhowl"] = {
            { "", "", 16508, "ability_golemthunderclap" },
            { "", "", 13443, "ability_gouge" },
            { "", "", 13446, "ability_rogue_ambush" },
        },
        ["Halycon"] = {
            { "", "", 13443, "ability_gouge" },
            { "", "", 3391, "ability_ghoulfrenzy" },
        },
        ["Gizrul the Slavener"] = {
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 20539, "ability_backstab" },
            { "", "", 16128, "spell_shadow_callofbone" },
        },
        ["Overlord Wyrmthalak"] = {
            { "", "", 19983, "ability_warrior_cleave" },
            { "", "", 23511, "ability_warrior_warcry" },
            { "", "", 25322, "ability_devour" },
        },
    },
    dire_maul_north = {
        ["Guard Mol'dar"] = {
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 10101, "inv_gauntlets_05" },
            { "", "", 11972, "ability_warrior_shieldbash" },
            { "", "", 15749, "ability_warrior_charge" },
            { "", "", 15580, "ability_rogue_ambush" },
        },
        ["Stomper Kreeg"] = {
            { "", "", 22833, "inv_drink_05" },
            { "", "", 22835, "spell_shadow_sacrificialshield" },
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 16740, "ability_bullrush" },
            { "", "", 15577, "ability_whirlwind" },
        },
        ["Guard Fengus"] = {
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 10101, "inv_gauntlets_05" },
            { "", "", 11972, "ability_warrior_shieldbash" },
            { "", "", 15749, "ability_warrior_charge" },
            { "", "", 15580, "ability_rogue_ambush" },
        },
        ["Guard Slip'kik"] = {
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 10101, "inv_gauntlets_05" },
            { "", "", 11972, "ability_warrior_shieldbash" },
            { "", "", 15749, "ability_warrior_charge" },
            { "", "", 15580, "ability_rogue_ambush" },
        },
        ["Captain Kromcrush"] = {
            { "", "", 22860, "ability_bullrush" },
            { "", "", 8599, "spell_shadow_unholyfrenzy" },
            { "", "", 19134, "ability_golemthunderclap" },
            { "", "", 22859, "ability_warrior_savageblow" },
            { "", "", 22857, "ability_warrior_challange" },
        },
        ["Cho'Rush the Observer"] = {
            { "", "", 17194, "spell_shadow_unholyfrenzy" },
            { "", "", 22884, "spell_shadow_psychicscream" },
            { "", "", 17139, "spell_holy_powerwordshield" },
            { "", "", 11642, "spell_holy_heal" },
        },
        ["King Gordok"] = {
            { "", "", 22886, "ability_warrior_charge" },
            { "", "", 15708, "ability_warrior_savageblow" },
            { "", "", 15572, "ability_warrior_sunder" },
            { "", "", 16727, "ability_bullrush" },
        },
    },
    dire_maul_west = {
        ["Tendris Warpwood"] = {
            { "", "", 22994, "spell_nature_stranglevines" },
            { "", "", 22924, "spell_nature_earthquake" },
            { "", "", 5568, "spell_nature_natureswrath" },
            { "", "", 22916, "inv_gauntlets_05" },
        },
        ["Illyanna Ravenoak"] = {
            { "", "", 20904, "inv_spear_07" },
            { "", "", 22914, "spell_frost_stun" },
            { "", "", 22910, "spell_fire_flameshock" },
            { "", "", 22908, "ability_marksmanship" },
        },
        ["Magister Kalendris"] = {
            { "", "", 7645, "spell_shadow_shadowworddominate" },
            { "", "", 15587, "spell_shadow_unholyfrenzy" },
            { "", "", 22919, "spell_shadow_siphonmana" },
            { "", "", 15654, "spell_shadow_shadowwordpain" },
            { "", "", 22917, "spell_shadow_summonvoidwalker" },
        },
        ["Tsu'zee"] = {
            { "", "", 15657, "ability_backstab" },
            { "", "", 21060, "spell_shadow_mindsteal" },
            { "", "", 12540, "ability_gouge" },
            { "", "", 15667, "spell_shadow_ritualofsacrifice" },
        },
        ["Immol'thar"] = {
            { "", "", 8269, "spell_shadow_unholyfrenzy" },
            { "", "", 22899, "spell_shadow_detectinvisibility" },
            { "", "", 16128, "spell_shadow_callofbone" },
            { "", "", 22950, "spell_arcane_portalironforge" },
            { "", "", 5568, "spell_nature_natureswrath" },
        },
        ["Prince Tortheldrin"] = {
            { "", "", 22920, "spell_shadow_deathpact" },
            { "", "", 20537, "spell_frost_iceshock" },
            { "", "", 22995, "spell_arcane_portalironforge" },
            { "", "", 15589, "ability_whirlwind" },
        },
        ["Lord Hel'nurath"] = {
            { "", "", 20812, "spell_shadow_cripple" },
            { "", "", 22665, "spell_shadow_shadowbolt" },
        },
    },
    scholomance = {
        ["Blood Steward of Kirtonos"] = {
            { "", "", 22371, "spell_nature_drowsy" },
            { "", "", 11708, "spell_shadow_curseofmannoroth" },
            { "", "", 3609, "ability_poisonsting" },
        },
        ["Kirtonos the Herald"] = {
            { "", "", 22371, "spell_nature_drowsy" },
            { "", "", 11708, "spell_shadow_curseofmannoroth" },
            { "", "", 3609, "ability_poisonsting" },
        },
        ["Jandice Barov"] = {
            { "", "", 8282, "spell_shadow_ritualofsacrifice" },
            { "", "", 18647, "spell_shadow_cripple" },
        },
        ["Rattlegore"] = {
            { "", "", 18945, "inv_gauntlets_05" },
            { "", "", 15580, "ability_rogue_ambush" },
            { "", "", 11876, "ability_bullrush" },
            { "", "", 11597, "ability_warrior_sunder" },
            { "", "", 11198, "ability_warrior_riposte" },
        },
        ["Marduk Blackpool"] = {
            { "", "", 11609, "ability_warrior_cleave" },
            { "", "", 17695, "spell_shadow_unholystrength" },
            { "", "", 12040, "spell_shadow_antishadow" },
        },
        ["Vectus"] = {
            { "", "", 13021, "spell_holy_excorcism_02" },
            { "", "", 10216, "spell_fire_selfdestruct" },
        },
        ["Ras Frostwhisper"] = {
            { "", "", 18099, "spell_frost_frostnova" },
            { "", "", 18100, "spell_frost_frostarmor02" },
            { "", "", 6215, "spell_shadow_possession" },
            { "", "", 16350, "spell_frost_glacier" },
            { "", "", 8398, "spell_frost_frostbolt02" },
        },
        ["Instructor Malicia"] = {
            { "", "", 5137, "spell_shadow_chilltouch" },
            { "", "", 25311, "spell_shadow_abominationexplosion" },
            { "", "", 6064, "spell_holy_heal02" },
            { "", "", 25315, "spell_holy_renew" },
            { "", "", 6146, "spell_nature_slow" },
        },
        ["Doctor Theolen Krastinov"] = {
            { "", "", 11130, "inv_gauntlets_05" },
            { "", "", 11574, "ability_gouge" },
        },
        ["Lorekeeper Polkelt"] = {
            { "", "", 8245, "spell_nature_acid_01" },
            { "", "", 5413, "spell_holy_harmundeadaura" },
            { "", "", 3586, "spell_holy_harmundeadaura" },
        },
        ["The Ravenian"] = {
            { "", "", 20569, "ability_warrior_cleave" },
            { "", "", 11130, "inv_gauntlets_05" },
            { "", "", 25174, "ability_warrior_sunder" },
            { "", "", 5568, "spell_nature_natureswrath" },
        },
        ["Lord Alexei Barov"] = {
            { "", "", 25309, "spell_fire_immolation" },
            { "", "", 28340, "spell_shadow_unholystrength" },
            { "", "", 17820, "spell_shadow_gathershadows" },
            { "", "", 10955, "spell_nature_slow" },
            { "", "", 10326, "spell_holy_turnundead" },
        },
        ["Lady Illucia Barov"] = {
            { "", "", 11713, "spell_shadow_curseofsargeras" },
            { "", "", 14515, "spell_shadow_shadowworddominate" },
            { "", "", 6215, "spell_shadow_possession" },
            { "", "", 12528, "spell_holy_silence" },
            { "", "", 17289, "spell_shadow_shadowbolt" },
        },
        ["Darkmaster Gandling"] = {
            { "", "", 25346, "spell_nature_starfall" },
            { "", "", 18702, "spell_shadow_antishadow" },
            { "", "", 12040, "spell_shadow_antishadow" },
            { "", "", 17802, "spell_shadow_shadowbolt" },
        },
    },
    stratholme_main = {
        ["Skul"] = {
            { "", "", 15230, "spell_arcane_starfire" },
            { "", "", 15499, "spell_frost_frostshock" },
            { "", "", 16799, "spell_frost_frostbolt02" },
        },
        ["Hearthsinger Forresten"] = {
            { "", "", 16798, "spell_shadow_soothingkiss" },
            { "", "", 14443, "ability_upgrademoonglaive" },
        },
        ["Postmaster Malown"] = {
            { "", "", 7713, "spell_shadow_possession" },
            { "", "", 6253, "inv_gauntlets_05" },
            { "", "", 13338, "spell_shadow_curseoftounges" },
            { "", "", 12741, "spell_shadow_curseofmannoroth" },
            { "", "", 12542, "spell_shadow_possession" },
        },
        ["Timmy the Cruel"] = {
            { "", "", 17470, "ability_ghoulfrenzy" },
            { "", "", 8599, "spell_shadow_unholyfrenzy" },
        },
        ["Malor the Zealous"] = {
            { "", "", 17233, "spell_holy_layonhands" },
        },
        ["Archivist Galford"] = {
            { "", "", 17293, "spell_nature_cyclone" },
            { "", "", 17366, "spell_fire_sealoffire" },
        },
        ["Balnazzar"] = {
            { "", "", 17405, "spell_shadow_shadowworddominate" },
            { "", "", 13704, "spell_shadow_psychicscream" },
            { "", "", 15587, "spell_shadow_unholyfrenzy" },
            { "", "", 17399, "spell_shadow_shadowbolt" },
            { "", "", 15970, "spell_nature_sleep" },
        },
    },
    stratholme_service = {
        ["Magistrate Barthilas"] = {
            { "", "", 16793, "spell_shadow_chilltouch" },
            { "", "", 10887, "inv_gauntlets_04" },
            { "", "", 16791, "spell_shadow_unholyfrenzy" },
            { "", "", 14099, "inv_gauntlets_05" },
        },
        ["Stonespine"] = {
            { "", "", 14331, "ability_gouge" },
        },
        ["Baroness Anastari"] = {
            { "", "", 16867, "spell_nature_drowsy" },
            { "", "", 16868, "spell_shadow_shadowbolt" },
            { "", "", 17244, "spell_shadow_charm" },
            { "", "", 18327, "spell_holy_silence" },
        },
        ["Nerub'enkan"] = {
            { "", "", 16418, "spell_shadow_carrionswarm" },
            { "", "", 4962, "spell_nature_earthbind" },
            { "", "", 6016, "spell_shadow_vampiricaura" },
            { "", "", 17235, "spell_shadow_contagion" },
        },
        ["Maleki the Pallid"] = {
            { "", "", 17620, "spell_shadow_lifedrain02" },
            { "", "", 13322, "spell_frost_frostbolt02" },
            { "", "", 16869, "spell_frost_glacier" },
        },
        ["Ramstein the Gorger"] = {
            { "", "", 17687, "ability_ghoulfrenzy" },
            { "", "", 17307, "inv_gauntlets_05" },
            { "", "", 5568, "spell_nature_natureswrath" },
        },
        ["Baron Rivendare"] = {
            { "", "", 15496, "ability_warrior_cleave" },
            { "", "", 16856, "ability_warrior_savageblow" },
            { "", "", 17393, "spell_shadow_shadowbolt" },
            { "", "", 17467, "spell_shadow_unholystrength" },
        },
    },
}
