local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

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
            intro = "本頁依據傷害輸出與為隊伍帶來的價值，對無限服的輸出專精進行排名。",
            tiers = {
                { key = "S", specs = { { class = "HUNTER", spec = "bm" }, { class = "HUNTER", spec = "mm" }, { class = "HUNTER", spec = "surv" }, { class = "WARLOCK", spec = "demo" }, { class = "WARLOCK", spec = "affli" }, { class = "WARLOCK", spec = "destro" }, { class = "SHAMAN", spec = "enh" } } },
                { key = "A", specs = { { class = "MAGE", spec = "arcane" }, { class = "MAGE", spec = "fire" }, { class = "MAGE", spec = "frost" }, { class = "PALADIN", spec = "ret" }, { class = "WARRIOR", spec = "arms" }, { class = "WARRIOR", spec = "fury" }, { class = "ROGUE", spec = "sub" }, { class = "ROGUE", spec = "assa" }, { class = "ROGUE", spec = "combat" } } },
                { key = "B", specs = { { class = "DRUID", spec = "feral" }, { class = "SHAMAN", spec = "ele" } } },
                { key = "C", specs = { { class = "PRIEST", spec = "shadow" }, { class = "DRUID", spec = "balance" } } },
                { key = "D", specs = {} },
            },
            factors = {
                { "輸出強度", "該專精為隊伍貢獻的傷害量。" },
                { "增益價值", "該專精為隊友帶來的增益。" },
                { "非增益價值", "更難量化的價值，例如在危急時臨時充當坦克。" },
                { "生存價值", "權重較小的一項，但倒下的輸出等於沒有輸出；預設就能打得更安全，也意味着能更長時間黏在目標身上。" },
            },
            notes = {
                "在此等級段，各專精之間的差距很小（少數例外除外），因此分檔更多代表職業，而不一定代表單個專精。",
                "本排行基於當前測試版本，且嚴格限定在等級上限 30 的範圍內；一切都還可能調整，本頁會隨之更新。",
                "請謹慎看待這份榜單：它只是一次關於「哪些專精更有價值」的討論，不該用來決定你玩哪個專精，也不該用來決定讓公會裏的人玩哪個專精。",
                "需要注意的是，即便你的專精排得比預期低，無限服的所有輸出專精都能打通全部內容，只是會比高排名專精更喫力一些。",
                "實際表現因人、因場合而異。最明顯的例子是法師與術士：在這個等級段它們擁有全遊戲最高的群體傷害，但如果隊伍一次只拉 2 到 3 只怪，法師的優勢就會被大幅掩蓋；獵人在這種環境下極強，但群體傷害較弱。",
                "總體而言，除法師與術士這兩個特例，等級 30 的物理輸出表現最好。法系大體還能跟上，但主要靠高價值的持續傷害效果或群體傷害大招，其餘時間基本在丟魔杖。",
                "平衡德在墊底位置比較特殊，因為它沒有任何丟魔杖的輸出手段，不過它能給坦克上一個高法術強度的荊棘術作為補償。",
            },
        },
        {
            key = "tank",
            intro = "本頁依據單體與群體拉怪能力，以及為隊伍提供的增益、減益、大招等價值，對無限服的坦克專精進行排名。",
            tiers = {
                { key = "S", specs = { { class = "PALADIN", spec = "prot" } } },
                { key = "A", specs = { { class = "WARRIOR", spec = "prot" }, { class = "DRUID", spec = "feral" } } },
                { key = "B", specs = {} },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "生存能力", "作為主坦承受高傷害的能力，包括減傷技能、大招、整體耐久與自我維持手段。" },
                { "傷害與仇恨", "在保證生存、履行主坦職責的前提下，該專精能打出的傷害與能建立的仇恨量。" },
                { "小怪與群拉", "主要看群體仇恨的建立能力與小怪階段的生存能力。" },
                { "團隊增益", "該專精對整支隊伍有幫助的價值。" },
            },
            notes = {
                "每個坦克都有比別的坦克更擅長或更喫力的場景，排名高並不代表它在所有方面都強。但在等級 30，群體仇恨與群體傷害的價值遠高於滿級階段，這會讓榜單產生偏移。",
                "榮譽提名：增強薩具備一定的坦克支援能力，但沒有完整的坦克工具箱。作為地下城坦克完全夠用、甚至不錯，但帶薩滿坦去打更難的內容並不明智。",
                "本排行基於當前測試版本，且嚴格限定在等級上限 30 的範圍內；一切都還可能調整，本頁會隨之更新。",
                "請謹慎看待這份榜單：它只是一次關於「哪些專精更有價值」的討論，不該用來決定你玩哪個專精，也不該用來決定讓公會裏的人玩哪個專精。",
                "如上所述，分檔時考慮了不少方面，但某個坦克實際好不好用，還取決於你在打什麼內容、隊伍或團隊需要什麼。",
                "話雖如此，無限服的所有內容用任何坦克專精都能通關。每個坦克都有自己的定位；若某個坦克變得不好用，通常也會拿到調整，被拉回與其他坦克相近的水平。",
                "保護聖騎在等級 30 格外突出：它能用上二級奉獻，懲罰光環隨法術強度成長，再加上盾牌專精這類天賦，法力顧慮基本消除，它從不缺仇恨，多數時候都能穩定待在傷害榜首位；新到手的 30 級大招聖殿騎士壁壘，在前期也比其他坦克的大招價值更高。",
                "防護戰士與野性德的表現同樣不差。戰士通過復仇這類技能擁有更高的仇恨係數，如今還能在防禦姿態下使用雷霆一擊；盾牌格擋不耗怒氣、冷卻又短，讓他們體感更紮實——畢竟其他坦克還沒有同等工具。",
                "德魯伊可以自己上荊棘術，這在等級 30 傷害很高，也有能提升揮擊傷害的天賦——揮擊目前雖不喫攻擊強度加成，但官方已確認後續測試版本會補上；即便沒有攻強加成，靠野性本能與野蠻暴怒這類天賦，它依然能打出可觀的傷害。野德在等級 30 還能用上原始之咬與獸群領袖，價值巨大。",
            },
        },
        {
            key = "healer",
            intro = "本頁依據治療與吸收輸出、功能性與整體表現，對無限服的治療專精進行排名。",
            tiers = {
                { key = "S", specs = { { class = "PRIEST", spec = "disc" }, { class = "PRIEST", spec = "holy" } } },
                { key = "A", specs = { { class = "SHAMAN", spec = "resto" }, { class = "DRUID", spec = "resto" } } },
                { key = "B", specs = { { class = "PALADIN", spec = "holy" } } },
                { key = "C", specs = {} },
                { key = "D", specs = {} },
            },
            factors = {
                { "治療與吸收", "該專精在治療或預防傷害方面的表現，也就是坦克與團隊會承受的那部分傷害。" },
                { "法力效率", "該專精治療時的效率，以及有多容易遇到法力不足。" },
                { "大招覆蓋", "該專精應對高額傷害期或其他棘手情況的大招。" },
                { "團隊增益", "該專精對整支隊伍有幫助的增益與功能性。" },
                { "輸出貢獻", "在戰鬥允許的前提下，該專精能為團隊貢獻多少傷害。" },
            },
            notes = {
                "本排行基於當前測試版本，且嚴格限定在等級上限 30 的範圍內；一切都還可能調整，本頁會隨之更新。",
                "請謹慎看待這份榜單：它只是一次關於「哪些專精更有價值」的討論，不該用來決定你玩哪個專精，也不該用來決定讓公會裏的人玩哪個專精。",
                "需要注意，即便你的專精排得比預期低，無限服的所有治療專精都能打通全部內容。",
                "這份榜單想給出各治療專精強度的一個基準認知。值得一提的是，本次治療之間的平衡比以往版本接近得多，不同首領與環境下各有所長。",
                "如上所述，分檔時考慮了不少方面，但治療實際好不好用，取決於你的團隊是在刷已通關的團本，還是在首次推進。",
                "所有治療專精在測試服的表現都不錯，但各自工具箱的差異影響了排名。牧師整體表現良好，點出魔杖專精後可以在不消耗法力、也不打斷 5 秒回藍規則的情況下打出相當可觀的傷害；它法力效率高、產出也強，真言術：盾在關頭時刻同樣關鍵——尤其它現在不再阻止戰士與德魯伊產生怒氣。",
                "恢復薩是紮實的治療者，它帶來的圖騰也很有價值，但在拿到風怒圖騰之前，它缺少其他治療免費提供的那部分傷害；話雖如此，薩滿用灼熱圖騰與火焰新星同樣能打出不錯的傷害。在等級 30 它法力效率很高，能讓隊伍保持節奏而不必停下回藍；還可以順便下增強系點出強化風暴打擊與精神敏銳（配合傳承系統拿到的額外天賦點），讓它既能輕鬆應付野外，又是一個能打出有競爭力傷害的強力治療。",
                "恢復德之所以突出有兩個主要原因：一是它擁有非常全面的工具箱，持續性治療強勁、法力回覆高；二是在當前法術強度成長下，給坦克上的荊棘術價值極高。",
                "神聖騎擁有懲罰光環，作用與荊棘術類似。不過在等級 30，它的治療產出與法力回覆都略低於其他治療，靠大量增益與功能性來補足。",
            },
        },
    },
}
