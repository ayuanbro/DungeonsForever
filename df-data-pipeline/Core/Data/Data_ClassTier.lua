local _, ns = ...

ns.ClassTier = {
    meta = {
        patch = "1.60.1",
        level = 30,
        updated = "2026/10/06",
    },

    specs = {
        WARRIOR = {
            { key = "arms", name = "武器", nameEn = "Arms", icon = "Interface\\Icons\\ability_warrior_savageblow" },
            { key = "fury", name = "狂怒", nameEn = "Fury", icon = "Interface\\Icons\\ability_warrior_innerrage" },
            { key = "prot", name = "防护", nameEn = "Protection", icon = "Interface\\Icons\\ability_warrior_defensivestance" },
        },
        PALADIN = {
            { key = "holy", name = "神圣", nameEn = "Holy", icon = "Interface\\Icons\\Spell_Holy_HolyBolt" },
            { key = "prot", name = "防护", nameEn = "Protection", icon = "Interface\\Icons\\Spell_Holy_DevotionAura" },
            { key = "ret", name = "惩戒", nameEn = "Retribution", icon = "Interface\\Icons\\Spell_Holy_AuraOfLight" },
        },
        HUNTER = {
            { key = "bm", name = "兽王", nameEn = "Beast Mastery", icon = "Interface\\Icons\\Ability_Hunter_BeastTaming" },
            { key = "mm", name = "射击", nameEn = "Marksmanship", icon = "Interface\\Icons\\Ability_Marksmanship" },
            { key = "surv", name = "生存", nameEn = "Survival", icon = "Interface\\Icons\\Ability_Hunter_SwiftStrike" },
        },
        ROGUE = {
            { key = "assa", name = "奇袭", nameEn = "Assassination", icon = "Interface\\Icons\\ability_rogue_eviscerate" },
            { key = "combat", name = "战斗", nameEn = "Combat", icon = "Interface\\Icons\\ability_backstab" },
            { key = "sub", name = "敏锐", nameEn = "Subtlety", icon = "Interface\\Icons\\ability_stealth" },
        },
        PRIEST = {
            { key = "disc", name = "戒律", nameEn = "Discipline", icon = "Interface\\Icons\\spell_holy_wordfortitude" },
            { key = "holy", name = "神圣", nameEn = "Holy", icon = "Interface\\Icons\\spell_holy_guardianspirit" },
            { key = "shadow", name = "暗影", nameEn = "Shadow", icon = "Interface\\Icons\\spell_shadow_shadowwordpain" },
        },
        SHAMAN = {
            { key = "ele", name = "元素", nameEn = "Elemental", icon = "Interface\\Icons\\spell_nature_lightning" },
            { key = "enh", name = "增强", nameEn = "Enhancement", icon = "Interface\\Icons\\spell_nature_lightningshield" },
            { key = "resto", name = "恢复", nameEn = "Restoration", icon = "Interface\\Icons\\Spell_Nature_HealingWaveGreater" },
        },
        MAGE = {
            { key = "arcane", name = "奥术", nameEn = "Arcane", icon = "Interface\\Icons\\inv_misc_rune_03" },
            { key = "fire", name = "火焰", nameEn = "Fire", icon = "Interface\\Icons\\spell_fire_firebolt02" },
            { key = "frost", name = "冰霜", nameEn = "Frost", icon = "Interface\\Icons\\spell_frost_frostbolt02" },
        },
        WARLOCK = {
            { key = "affli", name = "痛苦", nameEn = "Affliction", icon = "Interface\\Icons\\spell_shadow_deathcoil" },
            { key = "demo", name = "恶魔", nameEn = "Demonology", icon = "Interface\\Icons\\spell_shadow_metamorphosis" },
            { key = "destro", name = "毁灭", nameEn = "Destruction", icon = "Interface\\Icons\\spell_shadow_rainoffire" },
        },
        DRUID = {
            { key = "balance", name = "平衡", nameEn = "Balance", icon = "Interface\\Icons\\spell_nature_starfall" },
            { key = "feral", name = "野性", nameEn = "Feral", icon = "Interface\\Icons\\ability_racial_bearform" },
            { key = "resto", name = "恢复", nameEn = "Restoration", icon = "Interface\\Icons\\Spell_Nature_HealingTouch" },
        },
    },

    pages = {
        {
            key = "dps",
            intro = "本页依据伤害输出与为队伍带来的价值，对无限服的输出专精进行排名。",
            tiers = {
                { key = "S", specs = { { class = "HUNTER", spec = "bm" }, { class = "HUNTER", spec = "mm" }, { class = "HUNTER", spec = "surv" }, { class = "WARLOCK", spec = "demo" }, { class = "WARLOCK", spec = "affli" }, { class = "WARLOCK", spec = "destro" }, { class = "SHAMAN", spec = "enh" } } },
                { key = "A", specs = { { class = "MAGE", spec = "arcane" }, { class = "MAGE", spec = "fire" }, { class = "MAGE", spec = "frost" }, { class = "PALADIN", spec = "ret" }, { class = "WARRIOR", spec = "arms" }, { class = "WARRIOR", spec = "fury" }, { class = "ROGUE", spec = "sub" }, { class = "ROGUE", spec = "assa" }, { class = "ROGUE", spec = "combat" } } },
                { key = "B", specs = { { class = "DRUID", spec = "feral" }, { class = "SHAMAN", spec = "ele" } } },
                { key = "C", specs = { { class = "PRIEST", spec = "shadow" }, { class = "DRUID", spec = "balance" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "输出强度", "该专精为队伍贡献的伤害量。" },
                { "增益价值", "该专精为队友带来的增益。" },
                { "非增益价值", "更难量化的价值，例如在危急时临时充当坦克。" },
                { "生存价值", "权重较小的一项，但倒下的输出等于没有输出；默认就能打得更安全，也意味着能更长时间黏在目标身上。" },
            },
            notes = {
                "在此等级段，各专精之间的差距很小（少数例外除外），因此分档更多代表职业，而不一定代表单个专精。",
                "本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。",
                "请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。",
                "需要注意的是，即便你的专精排得比预期低，无限服的所有输出专精都能打通全部内容，只是会比高排名专精更吃力一些。",
                "实际表现因人、因场合而异。最明显的例子是法师与术士：在这个等级段它们拥有全游戏最高的群体伤害，但如果队伍一次只拉 2 到 3 只怪，法师的优势就会被大幅掩盖；猎人在这种环境下极强，但群体伤害较弱。",
                "总体而言，除法师与术士这两个特例，等级 30 的物理输出表现最好。法系大体还能跟上，但主要靠高价值的持续伤害效果或群体伤害大招，其余时间基本在丢魔杖。",
                "平衡德在垫底位置比较特殊，因为它没有任何丢魔杖的输出手段，不过它能给坦克上一个高法术强度的荆棘术作为补偿。",
            },
        },
        {
            key = "tank",
            intro = "本页依据单体与群体拉怪能力，以及为队伍提供的增益、减益、大招等价值，对无限服的坦克专精进行排名。",
            tiers = {
                { key = "S", specs = { { class = "PALADIN", spec = "prot" } } },
                { key = "A", specs = { { class = "WARRIOR", spec = "prot" }, { class = "DRUID", spec = "feral" } } },
                { key = "B", specs = {} },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "生存能力", "作为主坦承受高伤害的能力，包括减伤技能、大招、整体耐久与自我维持手段。" },
                { "伤害与仇恨", "在保证生存、履行主坦职责的前提下，该专精能打出的伤害与能建立的仇恨量。" },
                { "小怪与群拉", "主要看群体仇恨的建立能力与小怪阶段的生存能力。" },
                { "团队增益", "该专精对整支队伍有帮助的价值。" },
            },
            notes = {
                "每个坦克都有比别的坦克更擅长或更吃力的场景，排名高并不代表它在所有方面都强。但在等级 30，群体仇恨与群体伤害的价值远高于满级阶段，这会让榜单产生偏移。",
                "荣誉提名：增强萨具备一定的坦克支援能力，但没有完整的坦克工具箱。作为地下城坦克完全够用、甚至不错，但带萨满坦去打更难的内容并不明智。",
                "本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。",
                "请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。",
                "如上所述，分档时考虑了不少方面，但某个坦克实际好不好用，还取决于你在打什么内容、队伍或团队需要什么。",
                "话虽如此，无限服的所有内容用任何坦克专精都能通关。每个坦克都有自己的定位；若某个坦克变得不好用，通常也会拿到调整，被拉回与其他坦克相近的水平。",
                "保护圣骑在等级 30 格外突出：它能用上二级奉献，惩罚光环随法术强度成长，再加上盾牌专精这类天赋，法力顾虑基本消除，它从不缺仇恨，多数时候都能稳定待在伤害榜首位；新到手的 30 级大招圣殿骑士壁垒，在前期也比其他坦克的大招价值更高。",
                "防护战士与野性德的表现同样不差。战士通过复仇这类技能拥有更高的仇恨系数，如今还能在防御姿态下使用雷霆一击；盾牌格挡不耗怒气、冷却又短，让他们体感更扎实——毕竟其他坦克还没有同等工具。",
                "德鲁伊可以自己上荆棘术，这在等级 30 伤害很高，也有能提升挥击伤害的天赋——挥击目前虽不吃攻击强度加成，但官方已确认后续测试版本会补上；即便没有攻强加成，靠野性本能与野蛮暴怒这类天赋，它依然能打出可观的伤害。野德在等级 30 还能用上原始之咬与兽群领袖，价值巨大。",
            },
        },
        {
            key = "healer",
            intro = "本页依据治疗与吸收输出、功能性与整体表现，对无限服的治疗专精进行排名。",
            tiers = {
                { key = "S", specs = { { class = "PRIEST", spec = "disc" }, { class = "PRIEST", spec = "holy" } } },
                { key = "A", specs = { { class = "SHAMAN", spec = "resto" }, { class = "DRUID", spec = "resto" } } },
                { key = "B", specs = { { class = "PALADIN", spec = "holy" } } },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "治疗与吸收", "该专精在治疗或预防伤害方面的表现，也就是坦克与团队会承受的那部分伤害。" },
                { "法力效率", "该专精治疗时的效率，以及有多容易遇到法力不足。" },
                { "大招覆盖", "该专精应对高额伤害期或其他棘手情况的大招。" },
                { "团队增益", "该专精对整支队伍有帮助的增益与功能性。" },
                { "输出贡献", "在战斗允许的前提下，该专精能为团队贡献多少伤害。" },
            },
            notes = {
                "本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。",
                "请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。",
                "需要注意，即便你的专精排得比预期低，无限服的所有治疗专精都能打通全部内容。",
                "这份榜单想给出各治疗专精强度的一个基准认知。值得一提的是，本次治疗之间的平衡比以往版本接近得多，不同首领与环境下各有所长。",
                "如上所述，分档时考虑了不少方面，但治疗实际好不好用，取决于你的团队是在刷已通关的团本，还是在首次推进。",
                "所有治疗专精在测试服的表现都不错，但各自工具箱的差异影响了排名。牧师整体表现良好，点出魔杖专精后可以在不消耗法力、也不打断 5 秒回蓝规则的情况下打出相当可观的伤害；它法力效率高、产出也强，真言术：盾在关头时刻同样关键——尤其它现在不再阻止战士与德鲁伊产生怒气。",
                "恢复萨是扎实的治疗者，它带来的图腾也很有价值，但在拿到风怒图腾之前，它缺少其他治疗免费提供的那部分伤害；话虽如此，萨满用灼热图腾与火焰新星同样能打出不错的伤害。在等级 30 它法力效率很高，能让队伍保持节奏而不必停下回蓝；还可以顺便下增强系点出强化风暴打击与精神敏锐（配合传承系统拿到的额外天赋点），让它既能轻松应付野外，又是一个能打出有竞争力伤害的强力治疗。",
                "恢复德之所以突出有两个主要原因：一是它拥有非常全面的工具箱，持续性治疗强劲、法力回复高；二是在当前法术强度成长下，给坦克上的荆棘术价值极高。",
                "神圣骑拥有惩罚光环，作用与荆棘术类似。不过在等级 30，它的治疗产出与法力回复都略低于其他治疗，靠大量增益与功能性来补足。",
            },
        },
    },
}
