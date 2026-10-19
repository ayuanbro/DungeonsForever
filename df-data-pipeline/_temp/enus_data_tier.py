# -*- coding: utf-8 -*-
"""Data_ClassTier.lua 专用英文对照表（2026-09-29）。

为什么单开一份而不进全局 EXACT：同一个中文词在本文件里是专精名，在别处是物品类型
或法术派系，全局表会串味 ——
  · 「武器」全局作物品类型 Weapon，这里必须是战士专精 Arms；
  · 「痛苦」全局作 Shadow（旧档特定上下文），这里必须是术士专精 Affliction。
故整表按文件覆盖（gen_enus_data.py 的 FILE_SPECIFIC），优先级高于 EXACT。

英文一律取原页原文（专精名与暴雪客户端英文一致，句子为原站英文全文）。
"""

TIER = {
    # ── 专精目录（键为数据里的 name 字段）──
    '武器': 'Arms', '狂怒': 'Fury', '防护': 'Protection',
    '神圣': 'Holy', '惩戒': 'Retribution',
    '兽王': 'Beast Mastery', '射击': 'Marksmanship', '生存': 'Survival',
    '奇袭': 'Assassination', '战斗': 'Combat', '敏锐': 'Subtlety',
    '戒律': 'Discipline', '暗影': 'Shadow',
    '元素': 'Elemental', '增强': 'Enhancement', '恢复': 'Restoration',
    '奥术': 'Arcane', '火焰': 'Fire', '冰霜': 'Frost',
    '痛苦': 'Affliction', '恶魔': 'Demonology', '毁灭': 'Destruction',
    '平衡': 'Balance', '野性': 'Feral',

    # ── 页首说明 ──
    '本页依据伤害输出与为队伍带来的价值，对无限服的输出专精进行排名。':
        'This page will rank the DPS specializations in WoW: Forever, based on their damage output and the notable utility they bring to the party.',
    '本页依据单体与群体拉怪能力，以及为队伍提供的增益、减益、大招等价值，对无限服的坦克专精进行排名。':
        'This page will rank the Tank specializations in WoW: Forever based on their single-target and AoE tanking capabilities, as well as their utility for the party, including buffs, debuffs, cooldowns, and more.',
    '本页依据治疗与吸收输出、功能性与整体表现，对无限服的治疗专精进行排名。':
        'This page will rank the Healer specializations in WoW: Forever, based on their healing and absorption output, utility, and overall performance.',

    # ── 排名依据 · 输出 ──
    '输出强度': 'Offensive Throughput',
    '该专精为队伍贡献的伤害量。':
        'Simply how much damage the spec contributes to the group.',
    '增益价值': 'Buff Utility',
    '该专精为队友带来的增益。':
        'What your spec brings to the group that benefits your fellow teammates.',
    '非增益价值': 'Non-Buff Utility',
    '更难量化的价值，例如在危急时临时充当坦克。':
        'Less tangible utility, such as the ability to off-tank in a dire situation.',
    '生存价值': 'Defensive Utility',
    '权重较小的一项，但倒下的输出等于没有输出；默认就能打得更安全，也意味着能更长时间黏在目标身上。':
        'This is a smaller consideration, but a dead DPS is a bad DPS. Having a toolkit that allows you to play safe by default will also allow you to have higher uptime on the target.',

    # ── 排名依据 · 坦克 ──
    '生存能力': 'Survivability',
    '作为主坦承受高伤害的能力，包括减伤技能、大招、整体耐久与自我维持手段。':
        "This includes the specialization's ability to survive high damage as a Main Tank, such as damage-reduction abilities, cooldowns, overall durability, and potential self-sustain.",
    '伤害与仇恨': 'Damage & Threat',
    '在保证生存、履行主坦职责的前提下，该专精能打出的伤害与能建立的仇恨量。':
        'This takes into account how much damage a specialization can deal and the amount of threat it can generate while still focusing on staying alive and main-tanking.',
    '小怪与群拉': 'Trash & Adds',
    '主要看群体仇恨的建立能力与小怪阶段的生存能力。':
        'This focuses mainly on AoE threat generation and survivability.',
    '团队增益': 'Group Utility',
    '该专精对整支队伍有帮助的价值。':
        'This encompasses the utility a specialization has that helps the party overall.',

    # ── 排名依据 · 治疗 ──
    '治疗与吸收': 'Healing/Absorption',
    '该专精在治疗或预防伤害方面的表现，也就是坦克与团队会承受的那部分伤害。':
        'This includes the performance of a specialization when either healing or preventing damage, the Tanks and raid group will take.',
    '法力效率': 'Mana Efficiency',
    '该专精治疗时的效率，以及有多容易遇到法力不足。':
        'This takes into account the efficiency of a specialization when healing and how often they may run into Mana issues.',
    '大招覆盖': 'Cooldowns',
    '该专精应对高额伤害期或其他棘手情况的大招。':
        'This looks at the cooldowns each specialization has for dealing with periods of high incoming damage or other problematic areas.',
    '该专精对整支队伍有帮助的增益与功能性。':
        'This encompasses the buffs and utility a specialization has that helps the party overall.',
    '输出贡献': 'Offensive Utility',
    '在战斗允许的前提下，该专精能为团队贡献多少伤害。':
        'This looks at how much damage the spec brings to their raid if the encounter allows for it.',

    # ── 说明与免责 · 三页共用 ──
    '本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。':
        'This tier list is based on the current beta build of the game and is strictly limited to level 30; everything is still subject to change, and this guide will be updated accordingly.',
    "请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。":
        "This list must be taken with a huge grain of salt. It's designed to be an interesting discussion of what we think will make certain specs valuable, but it should not be used to decide which spec you're going to play or which specs you'll make the players in your guild play!",

    # ── 输出页 ──
    '在此等级段，各专精之间的差距很小（少数例外除外），因此分档更多代表职业，而不一定代表单个专精。':
        "Note: At this level bracket, there is very little variance between the specs (bar a few outliers), so a spec's placement is a representation of the class, not necessarily the individual spec.",
    '需要注意的是，即便你的专精排得比预期低，无限服的所有输出专精都能打通全部内容，只是会比高排名专精更吃力一些。':
        'It is important to note, if your chosen specialization is in a lower tier than expected, all of the DPS can clear all of the content offered in WoW: Forever; it may simply be more challenging than if you were playing a higher-ranked specialization.',
    '实际表现因人、因场合而异。最明显的例子是法师与术士：在这个等级段它们拥有全游戏最高的群体伤害，但如果队伍一次只拉 2 到 3 只怪，法师的优势就会被大幅掩盖；猎人在这种环境下极强，但群体伤害较弱。':
        "It's worth noting that your mileage will vary greatly from player to player and situation to situation. A clear example of this is the Mage's and Warlock's ability to output by far the highest AOE damage in the game during these early levels, but if your group does not pull more than 2-3 mobs at a time, then the Mage will be greatly outshone. Hunter is incredibly strong in those types of environments, but is less adept at AOE damage.",
    '总体而言，除法师与术士这两个特例，等级 30 的物理输出表现最好。法系大体还能跟上，但主要靠高价值的持续伤害效果或群体伤害大招，其余时间基本在丢魔杖。':
        'Overall, physical DPS performs the best at level 30 outside of the two outlier classes. Casters can still keep up for the most part, but mostly through using high-value damage-over-time effects or AOE cooldowns, and then wanding for the bulk of the dungeon.',
    '平衡德在垫底位置比较特殊，因为它没有任何丢魔杖的输出手段，不过它能给坦克上一个高法术强度的荆棘术作为补偿。':
        "Balance Druid is a bit of an outlier at the bottom, as they don't have any wanding option, but bring a high spell power Thorns on the tank to compensate.",

    # ── 坦克页 ──
    '每个坦克都有比别的坦克更擅长或更吃力的场景，排名高并不代表它在所有方面都强。但在等级 30，群体仇恨与群体伤害的价值远高于满级阶段，这会让榜单产生偏移。':
        'Note: Each tank will have aspects that they are better or worse at dealing with than other tanks. A high ranking does not automatically mean a tank will be particularly adept in all aspects of the game. But at level 30, the value of AOE threat and damage is a lot higher than it might be at the end-game, which skews the tier list.',
    '荣誉提名：增强萨具备一定的坦克支援能力，但没有完整的坦克工具箱。作为地下城坦克完全够用、甚至不错，但带萨满坦去打更难的内容并不明智。':
        "Honorary mention: Enhancement Shamans do have tanking support, but don't have a full-fledged tank toolkit. They will be perfectly fine to bring as a dungeon tank, but bringing a Shaman tank to more difficult content will be ill-advised.",
    '如上所述，分档时考虑了不少方面，但某个坦克实际好不好用，还取决于你在打什么内容、队伍或团队需要什么。':
        "As we mentioned above, a number of points were considered when assigning each specialization its overall rank, but the actual usage of certain tanks will differ depending on what type of content you're engaging in and what your party or raid might need.",
    '话虽如此，无限服的所有内容用任何坦克专精都能通关。每个坦克都有自己的定位；若某个坦克变得不好用，通常也会拿到调整，被拉回与其他坦克相近的水平。':
        'With that being said, you can clear all content in WoW: Forever with any tank specialization. Each tank will have their own niche, and if a particular tank becomes unviable, they will likely receive changes to bring them closer to the other tanks.',
    '保护圣骑在等级 30 格外突出：它能用上二级奉献，惩罚光环随法术强度成长，再加上盾牌专精这类天赋，法力顾虑基本消除，它从不缺仇恨，多数时候都能稳定待在伤害榜首位；新到手的 30 级大招圣殿骑士壁垒，在前期也比其他坦克的大招价值更高。':
        "Protection Paladin stands out as a pick at level 30 as they get access to rank 2 of Consecration. With Retribution Aura scaling with spell power and mana concerns being all but eliminated as the Paladin gets access to more talent points like Shield Specialization, they never struggle with threat and most often stake their spot at the top of the damage meters. Their new level 30 cooldown Templar's Bulwark also has a lot higher value in the early levels compared to the other tanks.",
    '防护战士与野性德的表现同样不差。战士通过复仇这类技能拥有更高的仇恨系数，如今还能在防御姿态下使用雷霆一击；盾牌格挡不耗怒气、冷却又短，让他们体感更扎实——毕竟其他坦克还没有同等工具。':
        "Protection Warriors and Feral Druids perform perfectly fine as well, however. Warriors have increased threat modifiers through spells like Revenge and can now use Thunder Clap in Defensive Stance. Because Shield Block is rage neutral with a rather low cooldown, they can feel sturdier as the other tanks haven't quite got the equivalent tools yet.",
    '德鲁伊可以自己上荆棘术，这在等级 30 伤害很高，也有能提升挥击伤害的天赋——挥击目前虽不吃攻击强度加成，但官方已确认后续测试版本会补上；即便没有攻强加成，靠野性本能与野蛮暴怒这类天赋，它依然能打出可观的伤害。野德在等级 30 还能用上原始之咬与兽群领袖，价值巨大。':
        "Druids can bring their own Thorns, which deals a lot of damage at level 30, and have access to talents that increase the damage of Swipe. While Swipe doesn't scale with Attack Power yet, it is confirmed to be coming in a future build of the beta. Even without attack power modifiers, it can still deal solid damage through talents like Feral Instinct and Savage Fury. Feral Druids also have access to Primal Bite and Leader of the Pack at level 30, which is enormously valuable.",

    # ── 治疗页 ──
    '需要注意，即便你的专精排得比预期低，无限服的所有治疗专精都能打通全部内容。':
        'It is important to note that if your chosen specialization is in a lower tier than expected, all of the healers can clear all of the content offered in WoW: Forever.',
    '这份榜单想给出各治疗专精强度的一个基准认知。值得一提的是，本次治疗之间的平衡比以往版本接近得多，不同首领与环境下各有所长。':
        "This list aims to give a baseline understanding of the power levels of each healer, but it's worth mentioning that the healer balancing is much closer than in previous iterations, and healers will excel on different encounters and environments.",
    '如上所述，分档时考虑了不少方面，但治疗实际好不好用，取决于你的团队是在刷已通关的团本，还是在首次推进。':
        'As we mentioned above, several points were considered when assigning each specialization its overall rank, but the actual usage of certain Healers will differ depending on whether your raid group is farming a raid or progressing it for the first time.',
    '所有治疗专精在测试服的表现都不错，但各自工具箱的差异影响了排名。牧师整体表现良好，点出魔杖专精后可以在不消耗法力、也不打断 5 秒回蓝规则的情况下打出相当可观的伤害；它法力效率高、产出也强，真言术：盾在关头时刻同样关键——尤其它现在不再阻止战士与德鲁伊产生怒气。':
        "Every healing spec is performing well on the beta, but there are some differences in each healer's toolkit that impacts their standing in the rankings. Priest is doing well all around, and by picking up Wand Specialization, they can output very viable damage without using any mana or interrupting the 5-second rule when it comes to mana regeneration. They are mana efficient and have strong output; Power Word: Shield can also come in very clutch, particularly with it no longer preventing rage generation for Warriors and Druids.",
    '恢复萨是扎实的治疗者，它带来的图腾也很有价值，但在拿到风怒图腾之前，它缺少其他治疗免费提供的那部分伤害；话虽如此，萨满用灼热图腾与火焰新星同样能打出不错的伤害。在等级 30 它法力效率很高，能让队伍保持节奏而不必停下回蓝；还可以顺便下增强系点出强化风暴打击与精神敏锐（配合传承系统拿到的额外天赋点），让它既能轻松应付野外，又是一个能打出有竞争力伤害的强力治疗。':
        "Restoration Shaman is a solid healer, and the totems they bring are certainly valuable, but before you get access to Windfury Totem, the additional free damage that the other healers bring isn't there. With that said, Shamans can certainly get some good damage out by using Searing Totem and Fire Nova. At level 30, they are very mana efficient and allow the group to go at a solid pace without having to stop for mana. You can now also very comfortably go down the Enhancement tree to pick up Improved Stormstrike and Mental Quickness (once you get additional talent points through the legacy system), which allows the shaman to easily deal with the open world while being a strong healer, and a healer who can output competitive damage.",
    '恢复德之所以突出有两个主要原因：一是它拥有非常全面的工具箱，持续性治疗强劲、法力回复高；二是在当前法术强度成长下，给坦克上的荆棘术价值极高。':
        'The Restoration Druid sticks out for two primary reasons: First, they have a very rounded toolkit with strong sustained healing and high mana regeneration, but secondly, bringing Thorns to the tank is such a valuable buff with the current spell power scaling of the buff.',
    '神圣骑拥有惩罚光环，作用与荆棘术类似。不过在等级 30，它的治疗产出与法力回复都略低于其他治疗，靠大量增益与功能性来补足。':
        'Holy Paladin bring Retribution Aura, which fills a similar role to Thorns. At level 30, their healing throughput and mana regeneration are slightly lower than the other healers, but they bring a lot of buffs and utility to make up for that.',
}
