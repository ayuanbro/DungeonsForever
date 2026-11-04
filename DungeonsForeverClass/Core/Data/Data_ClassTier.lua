local ns = _G.DF_NS or {}

ns.ClassTier = {
    meta = {
        patch = "1.60.1",
        level = 60,
        updated = "2026/11/03",
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
            intro = "本页对无限服的输出专精排名，依据伤害、增益与生存价值。",
            tiers = {
                { key = "S", specs = { { class = "HUNTER", spec = "surv" }, { class = "WARLOCK", spec = "demo" }, { class = "WARLOCK", spec = "destro" }, { class = "PALADIN", spec = "ret" }, { class = "WARRIOR", spec = "fury" } } },
                { key = "A", specs = { { class = "HUNTER", spec = "mm" }, { class = "SHAMAN", spec = "enh" }, { class = "MAGE", spec = "fire" }, { class = "HUNTER", spec = "bm" }, { class = "MAGE", spec = "arcane" }, { class = "WARLOCK", spec = "affli" }, { class = "WARRIOR", spec = "arms" }, { class = "DRUID", spec = "feral" }, { class = "ROGUE", spec = "combat" } } },
                { key = "B", specs = { { class = "PRIEST", spec = "shadow" }, { class = "ROGUE", spec = "sub" }, { class = "DRUID", spec = "balance" }, { class = "ROGUE", spec = "assa" }, { class = "MAGE", spec = "frost" } } },
                { key = "C", specs = { { class = "SHAMAN", spec = "ele" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "输出强度", "为队伍贡献的伤害量。" },
                { "增益价值", "为队友与团队带来的增益。" },
                { "非增益价值", "难以量化但关键时刻有用，例如临时充当坦克。" },
                { "可堆叠性", "队伍愿意带几个同专精。" },
                { "生存价值", "权重较小，但活着才有输出。" },
            },
            notes = {
                "榜单来自推演与模拟，当前装备与法术系数信息有限，只作讨论，不必当真。",
                "所有输出专精都能打通全部内容，排在低档只是更吃力。",
                "S 档值得堆叠，A 档出场率高，B 档不优先但不差，C 档最弱、照样能玩。",
                "当前没有专精处于 D 档。",
            },
        },
        {
            key = "tank",
            intro = "本页对无限服的坦克专精排名，依据生存、功能性与输出。",
            tiers = {
                { key = "S", specs = { { class = "DRUID", spec = "feral" } } },
                { key = "A", specs = { { class = "WARRIOR", spec = "prot" }, { class = "PALADIN", spec = "prot" } } },
                { key = "B", specs = {} },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "主坦生存", "承受高伤害的能力：减伤、大招、耐久与自愈。" },
                { "副坦能力", "不扛怪时的输出，以及能给主坦与治疗的帮助。" },
                { "主坦伤害与仇恨", "履行主坦职责时的伤害与仇恨量。" },
                { "小怪与群拉", "群体仇恨与小怪阶段的生存。" },
                { "团队增益", "对整支团队的价值。" },
            },
            notes = {
                "任何坦克都能打通全部内容，排名只说明谁更省力。",
                "野性德最稳：护甲与有效生命值最高，不扛怪还能变豹输出，是最好的副坦。",
                "防战有最强防御大招，靠破甲与雷霆提供团队价值，几乎必带；防骑伤害与仇恨最高，但更吃装备、怕尖刺。",
                "荣誉提名：增强萨能当副本坦，但没有完整的坦克工具箱，别带去团本。",
            },
        },
        {
            key = "healer",
            intro = "本页对无限服的治疗专精排名，依据治疗与吸收、功能性与输出。",
            tiers = {
                { key = "S", specs = { { class = "SHAMAN", spec = "resto" } } },
                { key = "A", specs = { { class = "DRUID", spec = "resto" }, { class = "PRIEST", spec = "holy" } } },
                { key = "B", specs = { { class = "PRIEST", spec = "disc" } } },
                { key = "C", specs = { { class = "PALADIN", spec = "holy" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "治疗与吸收", "治疗或预防伤害的表现。" },
                { "法力效率", "治疗效率与缺蓝程度。" },
                { "大招覆盖", "应对高额伤害期的手段。" },
                { "团队增益", "对整支团队的增益与功能性。" },
                { "输出贡献", "战斗允许时能贡献的伤害。" },
            },
            notes = {
                "治疗之间差距很小、各有所长，这份榜单只是个基准。",
                "所有治疗都能打通全部内容。",
                "恢复萨 S：图腾功能性最强，治疗链与激流既能照顾坦又省蓝。",
                "恢复德 A：团刷产出最高，持续掉血的战斗最吃它。",
                "神圣牧 A 法力效率高；戒律牧 B 适合团刷压力小的场合；神圣骑 C 坦刷很稳，但综合产出偏弱。",
            },
        },
    },
}
