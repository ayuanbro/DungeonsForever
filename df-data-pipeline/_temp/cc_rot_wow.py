# -*- coding: utf-8 -*-
"""窝窝头 WoW Forever 各专精输出循环（单体 / AOE 两列）。由 gen_rot_wowhead.py 生成。"""

ROT = {
    'WARRIOR': {
        'arms': {
            'note': '按重要程度排序的优先级表。雷霆一击排这么高，是因为它大幅降低敌人攻击速度：练级时覆盖更久，副本里还能救坦克。英勇打击常被滥用，尤其低等级怒气不足时——它耗怒，而且下一刀不产怒。',
            'st': [
                ('Battle Shout', 'Cast before engaging, and maintain it throughout the fight', '开怪前挂上，整场保持。'),
                ('Rend', 'Cast and maintaing it throughout the fight', '流血，目标活得久就一直挂着。'),
                ('Overpower', 'Cast', '一亮就用（敌人闪避了你的攻击）。'),
                ('Thunder Clap', 'Cast to maintain the debuff', '挂着别断：敌人会打得更慢。'),
                ('Sunder Armor', 'Cast and maintain 5 stacks on the target', '开场叠一两层（目标血量过半就别叠了）。'),
                ('穿刺打击', 'Cast', '叠好破甲之后的主力输出'),
                ('Slam', 'Cast if you just swung and you are not tanking the mob', '紧接在普攻之后（下一刀快到了就先跳过）。'),
                ('Victory Rush', 'Cast', '击杀之后用：白送一击还带回血。'),
                ('Heroic Strike', 'Cast if Rage allows for it', '只在怒气有富余时用。'),
            ],
            'aoe': [
                ('Battle Shout', 'Cast before engaging, and maintain it throughout the fight', '开怪前挂上，整场保持。'),
                ('Rend', 'Cast and maintain it on all targets', '流血，目标活得久就一直挂着。'),
                ('Thunder Clap', 'Cast', '挂着别断：敌人会打得更慢。'),
                ('Sweeping Strikes', 'Cast once you have 压制 ready', '两个敌人扎堆、并且攒了怒气时开。'),
                ('Overpower', 'Cast', '一亮就用（敌人闪避了你的攻击）。'),
                ('Sunder Armor', 'Cast and maintain 5 stacks on the target', '开场叠一两层（目标血量过半就别叠了）。'),
                ('Cleave', 'Cast if rage allows for it', '两个以上敌人贴在一起时用。'),
                ('Victory Rush', 'Cast', '击杀之后用：白送一击还带回血。'),
            ],
        },
        'fury': {
            'note': '',
            'st': [
                ('Overpower', 'Use', '一亮就用（敌人闪避了你的攻击）。'),
                ('Sunder Armor', 'Use if the target is above 70% HP', '目标血量高于七成时叠。'),
                ('Execute', 'Use', '怒气够就用来收尾'),
                ('Heroic Strike', 'Use or 顺劈斩', '用来花掉多余的怒气。'),
                ('Execute', 'Use', '怒气够就用来收尾'),
            ],
            'aoe': [
            ],
        },
        'prot': {
            'note': '本表是技能优先级；坦克的循环取决于当下正在发生什么，没有写死的顺序，宽松照用即可。队里只有你一个战士时，优先维持战斗怒吼。别忘了反击风暴：多目标时伤害极高，持续期间换成双手武器还能显著提高它的伤害。',
            'st': [
                ('Charge', 'Cast as you engage', '用它进场：从战斗姿态（二十五级拿到先锋前）。'),
                ('Bloodrage', 'Cast', '开场就开：白送的怒气。'),
                ('Shield Block', 'Cast', '多用：减伤，还能点亮复仇。'),
                ('Revenge', 'Cast', '一亮就用。'),
                ('Thunder Clap', 'Cast', '多个敌人时用：造仇恨，还让他们打得更慢。'),
                ('Demoralizing Shout', 'Cast', '让他们打得更软（近战敌人）；十月初补丁后还会给命中目标加一些仇恨。'),
                ('Sunder Armor', 'Cast if in a group environment. Maintain 5 stacks on bosses', '组队和打首领时叠满五层（beta 上仇恨很低）。'),
                ('Rend', "Cast if you're already high on threat", '仇恨已经稳住之后再挂。'),
                ('Sunder Armor', 'Cast 英勇打击 if you have spare rage and the boss has 5 stacks', '组队和打首领时叠满五层（beta 上仇恨很低）。'),
            ],
            'aoe': [
                ('Charge', 'Cast as you engage', '用它进场：从战斗姿态（二十五级拿到先锋前）。'),
                ('Bloodrage', 'Cast', '开场就开：白送的怒气。'),
                ('Thunder Clap', 'Cast', '多个敌人时用：造仇恨，还让他们打得更慢。'),
                ('Shield Block', 'Cast', '多用：减伤，还能点亮复仇。'),
                ('Revenge', 'Cast', '一亮就用。'),
                ('Demoralizing Shout', 'Cast', '让他们打得更软（近战敌人）；十月初补丁后还会给命中目标加一些仇恨。'),
                ('Rend', 'Cast on different targets', '仇恨已经稳住之后再挂。'),
                ('Cleave', 'Cast with excess rage', '怒气有富余时用'),
            ],
        },
    },
    'PALADIN': {
        'holy': {
            'note': '光环要一直开着（虔诚光环或惩罚光环），也别忘了给自己和队友挂力量祝福或智慧祝福。',
            'st': [
                ('Seal of Righteousness', 'Maintain', '要输出就保持一个圣印挂着。'),
                ('Judgement', 'Use', '冷却好了就用。'),
                ('Holy Strike', 'Use', '冷却好了就用。'),
                ('Exorcism', 'If the enemy is an undead or demon, use', '目标是亡灵或恶魔时用它'),
                ('Holy Shock', 'Use', '救急用的瞬发治疗。'),
                ('Consecration', 'Cast', '伤害很高，但非常费蓝。'),
                ('Judgement', 'Use with 光明圣印 to apply Judgment of Light on an enemy. You can replace your Seal afterward to do more damage, but remember that using 审判 will replace the currently active one', '冷却好了就用。'),
                ('Holy Shock', 'Use', '救急用的瞬发治疗。'),
                ('Flash of Light', 'Cast to quickly and cheaply heal someone, or use 圣光术 for a slower, more expensive heal that heals for much more, depending on the situation', '二十级起的主力治疗。'),
            ],
            'aoe': [
            ],
        },
        'prot': {
            'note': '开打前把正义之怒和光环挂好，靠圣印与审判建立仇恨；多目标优先奉献，单体省蓝。',
            'st': [
                ('Seal of Fury', 'Cast before engaging, and maintain it throughout the fight', '开怪前挂上，整场保持。'),
                ('Judgement', 'Cast', '冷却好了就用。'),
                ('Exorcism', 'Cast if Undead or Demon', '打亡灵和恶魔时用。'),
                ('Holy Strike', 'Cast', '冷却好了就用。'),
                ('Consecration', 'Cast if mana allows for it', '多个敌人时优先放；单个敌人蓝够再放。'),
            ],
            'aoe': [
                ('Seal of Fury', 'Cast before engaging, and maintain it throughout the fight', '开怪前挂上，整场保持。'),
                ('Consecration', 'Cast', '多个敌人时优先放；单个敌人蓝够再放。'),
                ('Judgement', 'Cast', '冷却好了就用。'),
                ('Exorcism', 'Cast if Undead or Demon', '打亡灵和恶魔时用。'),
                ('Holy Strike', 'Cast', '冷却好了就用。'),
            ],
        },
        'ret': {
            'note': '30 级阶段的循环非常简单、也很直观：基本就是技能冷却好了就放。',
            'st': [
                ('十字军审判', 'Optional: If the mob will survive moderately long, be sure to apply with your first 审判 to increase Holy damage', '可选：目标能活一会儿的话，第一次审判就挂上它，提高神圣伤害'),
                ('Seal of Command', 'Activate your primary seal - and refresh when it expires. Use for slower 2-handed weapons, generally at least 3.0 speed or slower, and use 正义圣印 for everything else', '只在武器慢、且没有命中特效时替掉正义圣印。'),
                ('Judgement', "on cooldown. This can be macro'd together with 神圣打击", '冷却好了就用。'),
                ('Holy Strike', 'on cooldown', '冷却好了就用。'),
                ('Consecration', 'For multiple enemies: Drop a on the ground; not worth using against a single enemy generally due to mana constraints', '只在多个敌人时用（很费蓝）。'),
                ('Exorcism', 'Cast on cooldown if the enemy is Undead or Demon', '打亡灵和恶魔时冷却好就用。'),
                ('Hammer of Justice', 'any particularly dangerous enemies', '把危险的敌人晕住。'),
            ],
            'aoe': [
            ],
        },
    },
    'HUNTER': {
        'bm': {
            'note': '拿到召唤雄鹰之前：单体用瞄准射击、多目标用多重射击，奥术射击冷却好就用。有了召唤雄鹰之后按下面的基本循环。',
            'st': [
                ("Hunter's Mark", 'Put on your target if you have the time for it', '开怪前先给目标上标记：全队远程伤害提高。'),
                ('Serpent Sting', 'Use and refresh when needed', '宠物咬到目标之后再挂，跳完就补。'),
                ('Summon Hawk', 'Use', '冷却好就召：始终保证场上有两只鹰。'),
                ('Aimed Shot', 'Use (single target) or 多重射击 (multi-target)', '冷却好就用（单体目标）。'),
                ('Summon Hawk', 'Use', '冷却好就召：始终保证场上有两只鹰。'),
                ('Aimed Shot', 'Use (single target) or 多重射击 (multi-target)', '冷却好就用（单体目标）。'),
                ('Arcane Shot', 'Use', '法力有富余时补一发。'),
                ('Aimed Shot', 'Use (single target) or 多重射击 (multi-target)', '冷却好就用（单体目标）。'),
            ],
            'aoe': [
            ],
        },
        'mm': {
            'note': '之后就是：奥术射击和瞄准射击（单体）或多重射击（多目标）冷却好了就用。',
            'st': [
                ("Hunter's Mark", 'Put on your target if you have the time for it', '开怪前先给目标上标记：全队远程伤害提高。'),
                ('Serpent Sting', 'Use', '宠物咬到目标之后再挂，跳完就补。'),
            ],
            'aoe': [
            ],
        },
        'surv': {
            'note': '进近战范围就排队猛禽一击；近战时优先顺序是猫鼬撕咬 > 陆行鸟踢击 > 反击。想拉开距离补远程技能（奥术射击、毒蛇钉刺、瞄准射击）时，用陆行鸟踢击的加速跑出去，等猛禽一击和猫鼬撕咬冷却差不多转好再回去。',
            'st': [
                ("Hunter's Mark", 'Put on your target', '开怪前先给目标上标记：全队远程伤害提高。'),
                ('Serpent Sting', 'Use', '开打就挂上，跳完就补。'),
            ],
            'aoe': [
            ],
        },
    },
    'ROGUE': {
        'assa': {
            'note': '',
            'st': [
                ('Mutilate', 'Use as your builder when you are at or below 3 Combo Points. You never want to cast a 毁伤 at 4+ Combo Points', '学到之后就是主力攒星技能（天赋）。'),
                ('Slice and Dice', 'Maintain', '目标活得久，就在五星时开。'),
                ('Expose Armor', 'if your group is physical heavy and the mob will live long enough to benefit from the debuff', '队伍物理输出多、战斗又拉得长时用。'),
                ('Eviscerate', 'Use any excess Combo Points on on low armor enemies and 割裂 on high armor enemies', '切割已经挂着时，五星用它。'),
                ('Slice and Dice', 'Else, just keep spamming your builder while refreshing as close to .1s remaining as possible', '目标活得久，就在五星时开。'),
            ],
            'aoe': [
            ],
        },
        'combat': {
            'note': '',
            'st': [
                ('Backstab', 'Use for dagger builds and 邪恶攻击 for non-dagger builds', '拿匕首在背后时，替掉影袭。'),
                ('Slice and Dice', 'Maintain', '全程保持；快结束时立刻补。'),
                ('Expose Armor', 'if your group is physical heavy and the mob will live long enough to benefit from the debuff', '队伍物理输出多、战斗又拉得长时用。'),
                ('Blade Flurry', 'Use with high Energy any time multiple enemies are present or when fighting a boss', '多目标或打首领、能量高时用'),
                ('Eviscerate', 'Use any excess Combo Points on on low armor enemies or 割裂 on high armor enemies', '切割已经挂着时，五星用它。'),
                ('Slice and Dice', 'Else, just keep spamming your builder while refreshing as close to .1s remaining as possible', '全程保持；快结束时立刻补。'),
            ],
            'aoe': [
            ],
        },
        'sub': {
            'note': '',
            'st': [
                ('Stealth', 'Always use 绞喉 from', '潜行摸过去，别被看见。'),
                ('Slice and Dice', 'Maintain', '全程保持；快结束时立刻补。'),
                ('Vanish', 'Utilize both and 伺机待发 to reapply your 绞喉 after it has fully run its course', '配合伺机待发，等绞喉跳完再补一次'),
                ('Expose Armor', 'if your group is physical heavy and the mob will live long enough to benefit from the debuff', '队伍物理输出多、战斗又拉得长时用。'),
                ('Eviscerate', 'Use any excess Combo Points on on low armor enemies and 割裂 on high armor enemies', '切割已经挂着时，五星用它。'),
                ('Slice and Dice', 'Else, just keep spamming your builder while refreshing as close to .1s remaining as possible', '全程保持；快结束时立刻补。'),
            ],
            'aoe': [
            ],
        },
    },
    'PRIEST': {
        'disc': {
            'note': '副本里要照看好几条血条，但注意力主要放在坦克身上——早期副本里的群体伤害很少。',
            'st': [
                ('Power Word: Fortitude', 'Keep major buffs active ( and 心灵之火)', '全程常驻'),
                ('Power Word: Shield', 'Before combat, cast', '开怪前先套；组队时给坦克。'),
                ('Holy Fire', 'Begin combat by casting (if you are level 20), or 惩击 otherwise', '用它起手（二十级前用惩击）。'),
                ('Mind Blast', 'Cast , then 暗言术：痛', '起手之后接一发。'),
                ('Mind Blast', 'Use Wand attacks until the enemy is defeated. If they have a lot of health, then you can cast again as it comes back off cooldown', '起手之后接一发。'),
                ('Renew', 'If worried about your health, keep a active', '挂坦克；担心自己血量时也挂自己。'),
                ('Power Word: Fortitude', 'Keep major buffs active ( and 心灵之火)', '全程常驻'),
                ('Power Word: Shield', 'Before combat, cast', '开怪前先套；组队时给坦克。'),
                ('Smite', 'Begin combat by casting ; otherwise', '还没学到神圣之火之前用它起手。'),
                ('Penance', 'Cast , then 暗言术：痛', '先放它，再挂暗言术：痛'),
                ('Mind Blast', 'Use Wand attacks until the enemy is defeated. If they have a lot of health, then you can cast too', '起手之后接一发。'),
                ('Renew', 'If worried about your health, keep a active', '挂坦克；担心自己血量时也挂自己。'),
                ('Renew', 'Keep on the Tank', '挂坦克；担心自己血量时也挂自己。'),
                ('Heal', 'Use as your primary heal', '组队时的主力治疗。'),
                ('Flash Heal', 'Use if someone is in imminent danger', '只在有人快死时用（很费蓝）。'),
                ('法术', 'When the party is healthy, Wand trash to buy yourself time to regenerate mana. （ \u200b#371806） the "five second rule" we discussed earlier, and try to give yourself a clear window to regain mana', '队伍血线健康时用魔杖点小怪，给自己留出回蓝窗口（就是前面说的五秒规则）'),
            ],
            'aoe': [
            ],
        },
        'holy': {
            'note': '注意力几乎都在坦克身上；这些副本里的群体伤害很少。',
            'st': [
                ('Power Word: Fortitude', 'Keep and 心灵之火 up', '全程常驻'),
                ('Power Word: Shield', 'Before combat, cast', '开怪前先套；组队时给坦克。'),
                ('Holy Fire', 'Open with', '用它起手（二十级前用惩击）。'),
                ('Mind Blast', 'Cast , then 暗言术：痛', '起手之后接一发。'),
                ('Mind Blast', 'Wand until the mob dies. Recast if it comes back up and the mob still has a lot of health', '起手之后接一发。'),
                ('Renew', 'Keep on yourself if the mob is hitting hard', '挂在坦克身上一直保持。'),
                ('Power Word: Fortitude', 'Keep and 心灵之火 up', '全程常驻'),
                ('Power Word: Shield', 'Before combat, cast', '开怪前先套；组队时给坦克。'),
                ('Smite', 'Open with', '还没学到神圣之火之前用它起手。'),
                ('Mind Blast', 'Cast once you have it, then 暗言术：痛', '起手之后接一发。'),
                ('Renew', 'Keep on yourself if the mob is hitting hard', '挂在坦克身上一直保持。'),
                ('Renew', 'Keep on the Tank', '挂在坦克身上一直保持。'),
                ('Heal', 'is the heal you live on', '组队时的主力治疗。'),
                ('Flash Heal', 'if someone is about to die', '只在有人快死时用。'),
                ('Binding Heal', 'When you and the Tank are both hurt', '你和坦克都掉血时'),
                ('Prayer of Healing', 'Only when most of the party is low. It is a 3-second cast, and it dumps mana', '只在全队都掉血严重时用；读条 3 秒、非常费蓝'),
            ],
            'aoe': [
            ],
        },
        'shadow': {
            'note': '30 级暗牧输出比较直接：噬灵瘟疫在点出噬灵传染之前非常费蓝，敌人本来就掉得快的话可以跳过。精神鞭笞在这个等级伤害不比魔杖高多少，但会重置五秒规则；而且它是引导技能、会被攻击推条——蓝不缺时再放心用。副本里尽量给所有敌人挂暗言术：痛并及时补，心灵震爆理想状态是冷却好就用，但这个等级可能同时撞上蓝量和仇恨问题。',
            'st': [
                ('Power Word: Fortitude', 'Make sure your major buffs are active, like and 心灵之火. Undead players should also maintain 虚弱之触', '全程常驻'),
                ('Power Word: Shield', '(Optional) Before combat, cast', '开怪前先套盾。'),
                ('Mind Blast', 'Begin combat by casting', '起手之后接一发；目标活得久就再补。'),
                ('Shadow Word: Pain', 'Cast', '持续伤害；组队时法力够就给多个目标都挂。'),
                ('Devouring Plague', 'Cast , if available', '能放就放'),
                ('Mind Flay', '(Optional) Cast', '天赋：痛和心灵震爆之后接；注意蓝量。'),
            ],
            'aoe': [
            ],
        },
    },
    'SHAMAN': {
        'ele': {
            'note': '',
            'st': [
                ('Strength of Earth Totem', 'Drop for your group', '开怪前先把图腾插好。'),
                ('Lightning Bolt', 'Use to attack targets at range', '用它开怪，也用来填充。'),
                ('Searing Totem', 'Drop against a single target or 熔岩图腾 against multiple targets', '最后一个图腾，开怪前一秒插。'),
                ('节能施法', 'Use procs on 火焰新星 as much as possible, as it costs a significant amount of Mana but is also our hardest-hitting spell', '触发时尽量打火焰新星——很费蓝，但也是伤害最高的'),
                ('Fire Nova', 'Use against multiple targets', '三个以上敌人时冷却好就用。'),
                ('Flame Shock', 'Alternate between and 地震术', '紧接其后挂；目标活得久就补。'),
            ],
            'aoe': [
            ],
        },
        'enh': {
            'note': '',
            'st': [
                ('Lightning Bolt', 'Enhancement Shamans are mostly reliant on their auto attacks. You will be using your shocks or to pull enemies to you and then usually preserve mana by not casting anything besides an occasional 风暴打击 to fish for 强化风暴打击 procs. You should keep your 闪电之盾 up between pulls, just to optimize your passive damage while also still using some leftover mana', '用它开怪；之后省蓝，靠武器打。'),
                ('Searing Totem', 'When you are in dungeons or fighting multiple enemies, you should focus on dropping your and using 火焰新星 as much as possible, until you either risk pulling threat or run out of mana', '多个敌人、或者打副本时插。'),
            ],
            'aoe': [
            ],
        },
        'resto': {
            'note': '',
            'st': [
                ('Strength of Earth Totem', 'Drop support totems, such as (with 元素的召唤 if dropping 2+ Totems at once or in a pre-pull situation) for your group', '给队伍的辅助图腾。'),
                ('Healing Wave', 'Heal deeply injured targets with , especially the tank!', '谁掉血严重就治谁，尤其是坦克。'),
                ('Searing Totem', "Drop and use 火焰新星 on cooldown until low on mana against multiple targets if there isn't significant incoming damage", '多个敌人、而且自己挨打不多时插。'),
            ],
            'aoe': [
            ],
        },
    },
    'MAGE': {
        'arcane': {
            'note': '循环很基础：单体先叠奥术冲击再放飞弹；多目标预读烈焰风暴后一直刷魔爆术。',
            'st': [
                ('Arcane Blast', "(never above 2 stacks unless it's a boss)", '最多叠 2 层（打首领另说）'),
                ('Arcane Missiles', "Use if Missile Barrage proc'ed", '奥术冲击之后用，或者飞弹触发亮起时用。'),
                ('Arcane Blast', "If you didn't get Missile Barrage after 2-3 s, Fire Blast instead to reset the stacks", '最多叠 2 层（打首领另说）'),
                ('Flamestrike', 'Pre-Cast (high mana cost option)', '多个敌人扎堆时用。'),
                ('Arcane Explosion', 'Spam', '多个敌人贴身时用。'),
            ],
            'aoe': [
            ],
        },
        'fire': {
            'note': '循环很基础：单体预读炎爆术接火球术填充；多目标预读烈焰风暴后一直刷魔爆术。',
            'st': [
                ('Scorch', "x5 if it's a high health target", '目标血厚就叠满 5 层'),
                ('Fireball', 'Cast', '主要填充法术'),
                ('Pyroblast', 'Once 热力迸发 is stacked, cast', '用它起手。'),
                ('Flamestrike', 'Pre-Cast (high mana cost option)', '多个敌人：先放它。'),
                ('Arcane Explosion', 'Spam', '多个敌人贴身时用。'),
            ],
            'aoe': [
            ],
        },
        'frost': {
            'note': '循环很基础：单体以寒冰箭为主；多目标预读烈焰风暴后一直刷魔爆术。',
            'st': [
                ('Frostbolt', '', '主力法术，一直用到目标快死'),
                ('Flamestrike', 'Pre-Cast (high mana cost option)', '预读（高耗蓝备选）'),
                ('Blizzard', "If the mobs are already grouped up and won't die before the cast is done, cast", '三个以上敌人。'),
                ('Arcane Explosion', 'Otherwise spam', '三个以上敌人，扛不满一个暴风雪、或者必须移动时用。'),
            ],
            'aoe': [
            ],
        },
    },
    'WARLOCK': {
        'affli': {
            'note': '这个等级的伤害来自 DOT 加吸取生命。点了痛苦天赋之后，吸取生命比丢魔杖强，还能把生命分流付出的血补回来。DOT 要先挂——它们需要时间跳。单拉用恐惧来回倒；想练得快可以一次拉两只。',
            'st': [
                ('Summon Succubus', 'Send in', '让恶魔先上（二十级前用小鬼或虚空行者）。'),
                ('Corruption', 'and 痛苦灾祸', '痛苦灾祸之后挂。'),
                ('Drain Life', 'until the mob dies', '需要回血时用。'),
                ('Corruption', 'First mob: , 痛苦灾祸 and 生命虹吸, then 恐惧术 it', '痛苦灾祸之后挂。'),
                ('Summon Succubus', 'Second mob: send in and apply the same DoTs', '让恶魔先上（二十级前用小鬼或虚空行者）。'),
                ('Fear', '吸取生命 the second mob. Re- the first whenever Fear ends', '第二只吸生命；恐惧一断就给第一只补恐惧'),
                ('Life Tap', 'Low on mana: cast instead of Drain Life. Drain Life heals the health back', '血量安全时用生命换法力。'),
            ],
            'aoe': [
            ],
        },
        'demo': {
            'note': '这个等级魅魔是主要输出，靠恶魔印记能把怪拉住一整场。你要做的是保持印记，并用吸取生命填空——它能把生命分流的血补回来。还没有恶魔印记之前魅魔拉不住怪：先挂腐蚀术和痛苦灾祸，再吸取生命，做好被怪打一会儿的准备。',
            'st': [
                ('Summon Succubus', 'Send in', '让恶魔先上（二十级前用小鬼或虚空行者）。'),
                ('Corruption', '+ 痛苦灾祸 the mob has a lot of health', '痛苦灾祸之后挂。'),
                ('Searing Pain', 'to brand the mob', '给目标上印记'),
                ('Drain Life', 'for the rest of the fight', '之后整场保持'),
                ('Searing Pain', 'Recast whenever the brand drops, roughly every 6 seconds', '印记一掉就补，大约每 6 秒一次'),
                ('Life Tap', 'Low on mana: cast instead of Drain Life', '血量安全时用生命换法力。'),
            ],
            'aoe': [
            ],
        },
        'destro': {
            'note': '这个等级的伤害来自 DOT 加一个填充法术。开怪有两种方式，到能暗影灼烧收尾时伤害差不多，用哪种取决于怪离你多远：近就默认近距离起手，需要边风筝边打下几只就用远程起手。收尾阶段默认丢魔杖，蓝有富余就打暗影箭；做任务时吸取生命也是好选择（魔杖差时尤其好），它吸回来的血正好补上生命分流的代价。',
            'st': [
                ('Bane of Agony', '腐蚀术 and 献祭. The DoTs let your pet keep aggro while you set up', '持续伤害。'),
                ('Shadow Bolt', 'until the mob turns to you', '主要填充法术'),
                ('Shadow Bolt', 'followed by 献祭 while the mob runs to you', '主要填充法术'),
                ('Bane of Agony', "Once it reaches melee, switch to instant casts so you don't suffer pushback: , plus 腐蚀术 if you have 5/5 强化腐蚀术", '持续伤害。'),
                ('Immolate', '燃烧 just before runs out, so you lose as little of the DoT as possible', '你的主力持续伤害。'),
                ('Shadowburn', '暗影灼烧 as the killing blow, once the mob is at or below one hit', '收尾用（碎片会退还）。'),
            ],
            'aoe': [
            ],
        },
    },
    'DRUID': {
        'balance': {
            'note': '法熊循环：远程起手后主要靠月火与星火术，被贴上就切熊形态顶住。',
            'st': [
                ('愤怒', 'Pull with', '用它开怪'),
                ('Entangling Roots', 'Cast to hold the enemy at range', '别让它贴上来；挣脱了就再缠一次。'),
                ('Starfire', 'Cast twice', '连放两次'),
                ('愤怒', 'Cast , then follow with two more 星火术', '先放它，再接两发星火术'),
                ('愤怒', 'Repeat the and 星火术 cycle until the enemy dies', '重复它和星火术的循环直到目标倒下'),
                ('愤怒', 'Opening with banks 日月之蚀 charges, so each pair of 星火术 that follows casts faster. If the enemy breaks free of 纠缠根须, stop your current cast and reapply 纠缠根须 before continuing. A 星火术 pushed back by melee hits costs you more time than the recast', '先放它攒日月之蚀，后面每对星火术都会更快。缠绕被挣脱就先断当前读条补缠绕——被近战推掉的星火术比重放更亏'),
                ('Insect Swarm', 'Pull with', '月火之后挂（天赋，二十五级）。'),
                ('Moonfire', 'Apply', '起手之后挂：每个敌人都挂一个。'),
                ('Rejuvenation', 'Cast on yourself as they close in', '需要时给自己挂，或者两次开怪之间挂。'),
                ('Thorns', 'Let the pack hit you, cleaving them with while you keep your dots and 回春术 running', '让怪打你，一边用它顺劈一边维持 DOT 和回春术'),
                ('Moonfire', "Pull up to three or four enemies with . (If you will naturally pull more, there is no need to cast 月火术 on all targets; it's better to get more hots onto yourself before going into 熊形态)", '起手之后挂：每个敌人都挂一个。'),
                ('Rejuvenation', 'Cast (or 愈合 if you have time) on yourself while they run to you', '需要时给自己挂，或者两次开怪之间挂。'),
                ('Bear Form', 'Shift into', '变形进熊形态'),
                ('Demoralizing Roar', 'Cast to reduce their damage', '放它降低它们的伤害'),
                ('横扫', 'until everything is dead', '一直用到全部清完'),
                ('Enrage', 'Use to generate extra rage for more 横扫, particularly at the start of a pull when your rage is low', '用它攒怒气多打横扫，尤其是开怪怒气低的时候'),
            ],
            'aoe': [
            ],
        },
        'feral': {
            'note': '野性德 DPS 的核心是尽量维持流血不断，同时保证变形之力冷却好了就用。',
            'st': [
                ('变形之力', 'if you will not waste any Energy, should always be under 50 Energy when used, and 节能施法 is not active', '不会浪费能量时用：能量要低于 50、而且节能施法没触发'),
                ('Rip', "if you have 4/5 combo-points and the target will live for 6 seconds or longer. Never apply if it's already active. Prioritize 5 combo-points if the target lives long enough", '目标能活六秒以上时，四到五星开。'),
                ('Swipe', "if the target will live for 6 seconds or longer. Never apply if it's already active", '目标能活 6 秒以上时用；已经挂着就别补'),
                ('Faerie Fire', "if it's not active and you won't waste Energy", '没挂着、而且不会浪费能量时用'),
                ('Shred', "as long as it doesn't affect the uptime of the previous abilities", '在敌人背后时的主力攒星技能；触发清晰预兆时用。'),
                ('Claw', 'if you can not 撕碎 due to positional requirement', '绕不到背后时的主力攒星技能。'),
                ('Faerie Fire', "if you can't press anything else to get a chance of a 节能施法 proc", '没别的可按时，用它赌一下节能施法'),
            ],
            'aoe': [
            ],
        },
        'resto': {
            'note': '恢复德的治疗很灵活，很多种打法都能有效治住队伍。可以自己试试不同等级的直接治疗、或者少维持一个 HOT，看哪种手感更适合你。',
            'st': [
                ('Thorns', 'Keep up on the tank', '给坦克上：帮忙拉仇恨。'),
                ('Rejuvenation', 'Keep up on the tank and anyone you expect to take damage', '战斗中挂在坦克身上。'),
                ('Insect Swarm', 'DPS for Deep Balance: everything, 纠缠根须 a few mobs away from the tank', '深平衡输出：什么都打，把离坦克远的那几只缠住'),
                ('愤怒', 'DPS for Deep Restoration: Spam or shift to 猎豹形态 for better mana regen', '深恢复输出：一直刷它，或者切猎豹形态回蓝更快'),
                ('Regrowth', 'When a direct heal is needed, start with to get the HoT up. Then use low ranks of 治疗之触 to fill the gaps', '坦克需要直接治疗时用。'),
                ('Swiftmend', 'If a life is in danger, use to pick them up. Even if a HoT is not up yet, 回春术 -> 迅捷治愈 is a 1.0s save', '有人危险就用它救人；就算没有 HOT，回春术接迅捷治愈也是一秒的救命组合'),
                ('Swiftmend', 'If is on cooldown or we do not have 1.0s to spare, cast 自然迅捷 with a max rank 治疗之触', '它在冷却、或者没有 1 秒可以等，就开自然迅捷配满级治疗之触'),
                ('Tranquility', 'When the emergency is party-wide, like too many enemies were pulled and threat is a mess, cast to keep everyone alive', '全队告急时用（比如拉太多、仇恨乱成一团），靠它把所有人保下来'),
            ],
            'aoe': [
            ],
        },
    },
}
