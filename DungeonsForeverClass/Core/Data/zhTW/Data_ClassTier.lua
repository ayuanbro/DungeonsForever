local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

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
            { key = "prot", name = "防護", nameEn = "Protection", icon = "Interface\\Icons\\ability_warrior_defensivestance" },
        },
        PALADIN = {
            { key = "holy", name = "神聖", nameEn = "Holy", icon = "Interface\\Icons\\Spell_Holy_HolyBolt" },
            { key = "prot", name = "防護", nameEn = "Protection", icon = "Interface\\Icons\\Spell_Holy_DevotionAura" },
            { key = "ret", name = "懲戒", nameEn = "Retribution", icon = "Interface\\Icons\\Spell_Holy_AuraOfLight" },
        },
        HUNTER = {
            { key = "bm", name = "獸王", nameEn = "Beast Mastery", icon = "Interface\\Icons\\Ability_Hunter_BeastTaming" },
            { key = "mm", name = "射擊", nameEn = "Marksmanship", icon = "Interface\\Icons\\Ability_Marksmanship" },
            { key = "surv", name = "生存", nameEn = "Survival", icon = "Interface\\Icons\\Ability_Hunter_SwiftStrike" },
        },
        ROGUE = {
            { key = "assa", name = "奇襲", nameEn = "Assassination", icon = "Interface\\Icons\\ability_rogue_eviscerate" },
            { key = "combat", name = "戰鬥", nameEn = "Combat", icon = "Interface\\Icons\\ability_backstab" },
            { key = "sub", name = "敏銳", nameEn = "Subtlety", icon = "Interface\\Icons\\ability_stealth" },
        },
        PRIEST = {
            { key = "disc", name = "戒律", nameEn = "Discipline", icon = "Interface\\Icons\\spell_holy_wordfortitude" },
            { key = "holy", name = "神聖", nameEn = "Holy", icon = "Interface\\Icons\\spell_holy_guardianspirit" },
            { key = "shadow", name = "暗影", nameEn = "Shadow", icon = "Interface\\Icons\\spell_shadow_shadowwordpain" },
        },
        SHAMAN = {
            { key = "ele", name = "元素", nameEn = "Elemental", icon = "Interface\\Icons\\spell_nature_lightning" },
            { key = "enh", name = "增強", nameEn = "Enhancement", icon = "Interface\\Icons\\spell_nature_lightningshield" },
            { key = "resto", name = "恢復", nameEn = "Restoration", icon = "Interface\\Icons\\Spell_Nature_HealingWaveGreater" },
        },
        MAGE = {
            { key = "arcane", name = "奧術", nameEn = "Arcane", icon = "Interface\\Icons\\inv_misc_rune_03" },
            { key = "fire", name = "火焰", nameEn = "Fire", icon = "Interface\\Icons\\spell_fire_firebolt02" },
            { key = "frost", name = "冰霜", nameEn = "Frost", icon = "Interface\\Icons\\spell_frost_frostbolt02" },
        },
        WARLOCK = {
            { key = "affli", name = "痛苦", nameEn = "Affliction", icon = "Interface\\Icons\\spell_shadow_deathcoil" },
            { key = "demo", name = "惡魔", nameEn = "Demonology", icon = "Interface\\Icons\\spell_shadow_metamorphosis" },
            { key = "destro", name = "毀滅", nameEn = "Destruction", icon = "Interface\\Icons\\spell_shadow_rainoffire" },
        },
        DRUID = {
            { key = "balance", name = "平衡", nameEn = "Balance", icon = "Interface\\Icons\\spell_nature_starfall" },
            { key = "feral", name = "野性", nameEn = "Feral", icon = "Interface\\Icons\\ability_racial_bearform" },
            { key = "resto", name = "恢復", nameEn = "Restoration", icon = "Interface\\Icons\\Spell_Nature_HealingTouch" },
        },
    },

    pages = {
        {
            key = "dps",
            intro = "本頁對無限服的輸出專精排名，依據傷害、增益與生存價值。",
            tiers = {
                { key = "S", specs = { { class = "HUNTER", spec = "surv" }, { class = "WARLOCK", spec = "demo" }, { class = "WARLOCK", spec = "destro" }, { class = "PALADIN", spec = "ret" }, { class = "WARRIOR", spec = "fury" } } },
                { key = "A", specs = { { class = "HUNTER", spec = "mm" }, { class = "SHAMAN", spec = "enh" }, { class = "MAGE", spec = "fire" }, { class = "HUNTER", spec = "bm" }, { class = "MAGE", spec = "arcane" }, { class = "WARLOCK", spec = "affli" }, { class = "WARRIOR", spec = "arms" }, { class = "DRUID", spec = "feral" }, { class = "ROGUE", spec = "combat" } } },
                { key = "B", specs = { { class = "PRIEST", spec = "shadow" }, { class = "ROGUE", spec = "sub" }, { class = "DRUID", spec = "balance" }, { class = "ROGUE", spec = "assa" }, { class = "MAGE", spec = "frost" } } },
                { key = "C", specs = { { class = "SHAMAN", spec = "ele" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "輸出強度", "為隊伍貢獻的傷害量。" },
                { "增益價值", "為隊友與團隊帶來的增益。" },
                { "非增益價值", "難以量化但關鍵時刻有用，例如臨時充當坦克。" },
                { "可堆疊性", "隊伍願意帶幾個同專精。" },
                { "生存價值", "權重較小，但活着纔有輸出。" },
            },
            notes = {
                "榜單來自推演與模擬，當前裝備與法術係數資訊有限，只作討論，不必當真。",
                "所有輸出專精都能打通全部內容，排在低檔只是更喫力。",
                "S 檔值得堆疊，A 檔出場率高，B 檔不優先但不差，C 檔最弱、照樣能玩。",
                "當前沒有專精處於 D 檔。",
            },
        },
        {
            key = "tank",
            intro = "本頁對無限服的坦克專精排名，依據生存、功能性與輸出。",
            tiers = {
                { key = "S", specs = { { class = "DRUID", spec = "feral" } } },
                { key = "A", specs = { { class = "WARRIOR", spec = "prot" }, { class = "PALADIN", spec = "prot" } } },
                { key = "B", specs = {} },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "主坦生存", "承受高傷害的能力：減傷、大招、耐久與自愈。" },
                { "副坦能力", "不扛怪時的輸出，以及能給主坦與治療的幫助。" },
                { "主坦傷害與仇恨", "履行主坦職責時的傷害與仇恨量。" },
                { "小怪與群拉", "群體仇恨與小怪階段的生存。" },
                { "團隊增益", "對整支團隊的價值。" },
            },
            notes = {
                "任何坦克都能打通全部內容，排名只說明誰更省力。",
                "野性德最穩：護甲與有效生命值最高，不扛怪還能變豹輸出，是最好的副坦。",
                "防戰有最強防禦大招，靠破甲與雷霆提供團隊價值，幾乎必帶；防騎傷害與仇恨最高，但更喫裝備、怕尖刺。",
                "榮譽提名：增強薩能當副本坦，但沒有完整的坦克工具箱，別帶去團本。",
            },
        },
        {
            key = "healer",
            intro = "本頁對無限服的治療專精排名，依據治療與吸收、功能性與輸出。",
            tiers = {
                { key = "S", specs = { { class = "SHAMAN", spec = "resto" } } },
                { key = "A", specs = { { class = "DRUID", spec = "resto" }, { class = "PRIEST", spec = "holy" } } },
                { key = "B", specs = { { class = "PRIEST", spec = "disc" } } },
                { key = "C", specs = { { class = "PALADIN", spec = "holy" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "治療與吸收", "治療或預防傷害的表現。" },
                { "法力效率", "治療效率與缺藍程度。" },
                { "大招覆蓋", "應對高額傷害期的手段。" },
                { "團隊增益", "對整支團隊的增益與功能性。" },
                { "輸出貢獻", "戰鬥允許時能貢獻的傷害。" },
            },
            notes = {
                "治療之間差距很小、各有所長，這份榜單只是個基準。",
                "所有治療都能打通全部內容。",
                "恢復薩 S：圖騰功能性最強，治療鏈與激流既能照顧坦又省藍。",
                "恢復德 A：團刷產出最高，持續掉血的戰鬥最喫它。",
                "神聖牧 A 法力效率高；戒律牧 B 適合團刷壓力小的場合；神聖騎 C 坦刷很穩，但綜合產出偏弱。",
            },
        },
    },
}
