# -*- coding: utf-8 -*-
"""奥妮克希亚的巢穴开门链（Data_DungeonQuests onyxias_lair 块 + Data_DungeonGuide 条目，2026-10-11 人工翻译）。

键 = 数据里的完整中文字符串；专有名词用官方英文名（与既有 EXACT 层口径一致）。
gen_enus_data.py 在手翻层之后并入 EXACT，优先级最高。
"""

FREE = {
    '尘泥沼泽 - 埃博斯塔夫的洞穴 56.8,87.4':
        'Dustwallow Marsh - Emberstrife\'s Cave 56.8,87.4',
    '凄凉之地 - 通往菲拉斯的大道':
        'Desolace - road toward Feralas',
    '暴风城 - 城门 70.4,85.6':
        'Stormwind City - main gates 70.4,85.6',

    '猎杀燃烧平原的黑龙人，向赫林迪斯·河角复命。':
        'Slay the black dragonkin in Burning Steepes and report back to Helendis Riverhorn.',
    '联盟开门链第一步。黑龙蛋、黑龙幼崽是非精英，黑龙人、黑翼龙人是 50-54 精英，建议组队；都集中在地图东部边缘一线。':
        'Alliance attunement step one. Black Broodlings and whelps are non-elite; Black Dragonspawn, Wyrmkin and Drakes are level 50-54 elites — bring a group. They are all strung along the eastern edge of the zone.',
    '把赫林迪斯·河角的信送到赤脊山湖畔镇的所罗门镇长手中。':
        'Deliver Helendis Riverhorn\'s letter to Magistrate Solomon in Lakeshire, Redridge Mountains.',
    '同名任务共五段，从湖畔镇一路辗转推进到暴风城。本段终点：湖畔镇市政厅（30,44）。':
        'Five quests share this name, moving step by step from Lakeshire to Stormwind City. This leg ends at the Lakeshire town hall (30,44).',
    '到黑石深渊监狱探视被囚的温德索尔元帅，把麦克斯韦尔元帅的信交给他。':
        'Visit Marshal Windsor in the Blackrock Depths jail and deliver Marshal Maxwell\'s letter to him.',
    '温德索尔在深渊监狱区右侧走廊尽头的牢房里。◎ 注意区分：麦克斯韦尔元帅在燃烧平原的摩根的岗哨，温德索尔元帅在深渊牢里。':
        'Windsor is in the cell at the end of the corridor on the right side of the BRD jail block. Do not mix the two up: Marshal Maxwell is at Morgan\'s Vigil in Burning Steepes, while Marshal Windsor is in the BRD jail.',
    '到暴风城门口找侍从罗威，召出雷吉纳德·温德索尔，护送他从城门走到暴风要塞。':
        'Find Squire Rowe at the gates of Stormwind City to summon Reginald Windsor, then escort him from the gates to Stormwind Keep.',
    '护送全程约 10 分钟；若别的队伍正在护送，温德索尔会说他暂时脱不开身，等几分钟就会现身。':
        'The escort takes about 10 minutes. If another party is already escorting him, Windsor says he is indisposed at the moment — wait a few minutes and he will show up.',
    '陪雷吉纳德·温德索尔行进到暴风要塞，击杀卡特拉娜·普瑞斯托现形后召出的精英龙人卫兵，向伯瓦尔·弗塔根公爵复命。':
        'March with Reginald Windsor to Stormwind Keep, defeat the elite dragonkin guards summoned when Lady Katrana Prestor reveals her true form, then report to Highlord Bolvar Fordragon.',
    '假面游行：普瑞斯托女男爵现出奥妮克希亚原形并召唤精英龙人卫兵，场边的卫兵 NPC 会帮忙抗怪，全清后交任务。':
        'The Great Masquerade: Lady Prestor reveals herself as Onyxia and summons elite dragonkin guards; the nearby guard NPCs help tank them. Turn in the quest once everything is defeated.',
    '带着龙眼碎片到冬泉谷南部的马兹索里尔洞穴深处，找伪装成人类的巨龙哈尔琳。':
        'Take the Fragment of the Dragon\'s Eye deep into the cave of Mazthoril in southern Winterspring to find Haleh, a dragon disguised as a humanoid.',
    '哈尔琳在洞穴尽头的传送符文处，踩上符文就会传到她身边。洞里精英龙人很多：组队清过去、盗贼潜行、或开疾跑直接冲，都能到她跟前。':
        'Haleh stands at the teleport runes at the end of the cave — step on the runes to reach her. The cave is stuffed with elite dragons: clear through with a group, stealth down, or sprint straight to her.',
    '到奥格瑞玛智慧谷找伊崔格谈话，再把他的话带给萨尔。':
        'Speak with Eitrigg in the Valley of Wisdom in Orgrimmar, then bring his words to Thrall.',
    '伊崔格在智慧谷（34.4,38.4），谈完直接回萨尔（31,38）交任务。':
        'Eitrigg is in the Valley of Wisdom (34.4,38.4); after talking to him, turn the quest in to Thrall (31,38).',
    '听萨尔讲完黑龙的故事，向他复命。':
        'Listen to Thrall\'s tale, then turn the quest in to him.',
    '纯对话任务，站着听完就行。':
        'A pure dialogue quest — just stand there and listen.',
    '到凄凉之地寻找部落的勇士雷克萨。':
        'Find Rexxar, champion of the Horde, in Desolace.',
    '雷克萨沿石爪山脉至菲拉斯的大道来回巡逻，中途会穿过科多兽墓地；找不到就问凄凉之地综合频道，或从菲拉斯沿路往北走最容易堵到他。':
        'Rexxar patrols back and forth along the road between Stonetalon Mountains and Feralas, cutting through the Kodo Graveyard midway. If you cannot find him, ask in Desolace general chat, or run north from Feralas — that is the easiest way to catch him.',
    '把雷克萨的嘱托送到西瘟疫之地乌瑟尔之墓附近的巫女麦兰达手中。':
        'Deliver Rexxar\'s testament to Myranda the Hag near Uther\'s Tomb in Western Plaguelands.',
    '麦兰达在西瘟疫之地（50,77），她会教你伪装成黑龙军团成员的办法。':
        'Myranda is in Western Plaguelands (50,77); she teaches you how to disguise yourself as a member of the Black Dragonflight.',
    '戴上龙族伪装护符，到尘泥沼泽最南端的洞穴里与埃博斯塔夫对话。':
        'Wear the Amulet of Draconic Subversion and speak with Emberstrife inside the cave at the southernmost tip of Dustwallow Marsh.',
    '进洞走到最深处先使用「龙族伪装护符」，再与埃博斯塔夫说话。':
        'Walk to the back of the cave, use the Amulet of Draconic Subversion first, then talk to Emberstrife.',
    '击杀冬泉谷马兹索里尔洞穴里的蓝龙斯克莱尔，取回头骨交给埃博斯塔夫。':
        'Kill Scryer, the blue dragon in the cave of Mazthoril in Winterspring, and bring his skull back to Emberstrife.',
    '「颅骨试炼」三场顺序随意、可以团杀；斯克莱尔在马兹索里尔洞穴深处（53.2,56），洞口在（57,50），要清不少精英龙人。◎ 三条龙都别忘摸头骨。':
        'The three Test of Skulls hunts can be done in any order and in a raid group. Scryer is deep in Mazthoril (53.2,56), cave entrance at (57,50) — expect to clear many elite dragonkin. Remember to loot all three dragon skulls.',
    '击杀悲伤沼泽的绿龙索姆努斯，取回头骨交给埃博斯塔夫。':
        'Kill Somnus, the green dragon in Swamp of Sorrows, and bring his skull back to Emberstrife.',
    '索姆努斯在地图东南部大范围巡逻（约 80,70 附近），先清一片区域等他路过。他有很强的击退，自然抗性很吃香。三场试炼顺序随意，记得摸头骨。':
        'Somnus patrols a wide area of the southeastern map (around 80,70) — clear a spot and wait for him to pass. He has a very strong knockback, and Nature resistance helps a lot. The tests can be done in any order; remember to loot the skull.',
    '击杀塔纳利斯时光洞穴外的青铜龙克罗纳利斯，取回头骨交给埃博斯塔夫。':
        'Kill Chronalis, the bronze dragon outside the Caverns of Time in Tanaris, and bring his skull back to Emberstrife.',
    '克罗纳利斯在时光洞穴门口（64.6,50.2）。三场试炼顺序随意、可以团杀，记得摸头骨。':
        'Chronalis is right outside the Caverns of Time (64.6,50.2). The tests can be done in any order and in a raid group; remember to loot the skull.',
    '击杀湿地的红龙阿克特罗兹，取回头骨交给埃博斯塔夫。':
        'Kill Axtroz, the red dragon in the Wetlands, and bring his skull back to Emberstrife.',
    '前三场颅骨试炼交完才会开放。阿克特罗兹在格瑞姆巴托附近巡逻（约 85,49），火焰免疫；想剥皮需要剥皮技能 310。':
        'Unlocks only after the first three Test of Skulls quests are turned in. Axtroz patrols near Grim Batol (around 85,49), is immune to fire, and requires 310 Skinning to skin.',
    '带着暗淡的龙火护符去凄凉之地找雷克萨。':
        'Take the Dull Drakefire Amulet to Rexxar in Desolace.',
    '任务描述让你回黑石塔找达基萨斯将军，但伪装护符在黑石塔里不生效——直接去凄凉之地找雷克萨（巡逻路线同「部落的勇士」）。':
        'The quest text sends you back to General Drakkisath in Blackrock Spire, but the disguise amulet does not work inside the Spire — go straight to Rexxar in Desolace instead (same patrol route as The Champion of the Horde).',

    '40 人的经典团本，唯一的首领是黑龙公主奥妮克希亚；进门不需要钥匙，但全团每名玩家的背包里都必须放着一枚龙火护符。':
        'A classic 40-player raid whose only boss is Onyxia the black dragon princess. No key is needed to enter, but every raider must carry a Drakefire Amulet in their bags.',
    '进门条件：每名团员都要把龙火护符放在背包里（放银行不算），团长有护符救不了没护符的队友——一人缺护符，全员进不去。':
        'Entry requirement: every raid member must have a Drakefire Amulet in their bags (the bank does not count). The raid leader having one does not cover anyone else — if one person lacks the amulet, nobody gets in.',
    '龙火护符由开门任务链产出，联盟与部落各有一条：联盟约 11 步、部落约 14 步，全程清单见「任务」页签。':
        'The Drakefire Amulet comes from the attunement quest chain, with separate Alliance and Horde paths: roughly 11 steps for Alliance and 14 for Horde. The full walkthrough is on the Quests tab.',
    '两条链的终点相同：进黑石塔上层击杀达基萨斯将军，取黑龙勇士之血向任务发布者换取护符。':
        'Both chains end the same way: kill General Drakkisath in Upper Blackrock Spire and trade the Blood of the Black Dragon Champion to the quest giver for the amulet.',
    '联盟链有两段护送（监狱风云、假面游行），失败可以重来；假面游行的精英龙人卫兵有场边卫兵 NPC 帮忙抗。':
        'The Alliance chain includes two escorts (Jail Break! and The Great Masquerade) that can be retried on failure; during the Masquerade the nearby guard NPCs help tank the elite dragonkin.',
    '部落链的「颅骨试炼」四条龙顺序随意、可以在团里杀，记得每条龙都摸头骨。':
        'The four Horde "Test of Skulls" dragons can be fought in any order and in a raid group — remember to loot every skull.',
    '副本在尘泥沼泽南部的岛洞里。部落开门链从荒芜之地卡加斯的高图斯起步，途经奥格瑞玛、凄凉之地、西瘟疫之地、尘泥沼泽，最后在黑石塔上层收尾。':
        'The lair is the island cave in southern Dustwallow Marsh. The Horde attunement chain starts with Warlord Goretooth in Kargath, Badlands, and runs through Orgrimmar, Desolace, Western Plaguelands and Dustwallow Marsh before finishing in Upper Blackrock Spire.',
    '副本在尘泥沼泽南部的岛洞里。联盟开门链从燃烧平原摩根的岗哨起步，途经赤脊山湖畔镇、暴风城、黑石深渊、冬泉谷，最后在黑石塔上层收尾。':
        'The lair is the island cave in southern Dustwallow Marsh. The Alliance attunement chain starts at Morgan\'s Vigil in Burning Steepes and runs through Lakeshire in Redridge Mountains, Stormwind City, Blackrock Depths and Winterspring before finishing in Upper Blackrock Spire.',

    '战斗分三阶段：100%~65% 地面缠斗、65%~40% 空中、40% 以下落地再战；二阶段最危险，全团爆发技能留到 65% 前压血，飞起前削掉越多血越好打。':
        'The fight has three phases: 100%-65% on the ground, 65%-40% in the air, then she lands below 40% and the fight resumes. Phase 2 is the deadliest — hold the raid\'s burst cooldowns to push her health before 65%; the more you burn before she takes off, the easier the fight.',
    '地面战永远站在侧面：正脸有龙息吐吸、尾巴有扫击击飞——被扫进蛋堆会引来一圈幼龙；站位同样避开她身后。':
        'Always fight from her sides on the ground: her front has a breath attack and her tail has Tail Sweep, which knocks players back — getting swept into the egg nest spawns a swarm of whelps. Avoid standing behind her as well.',
    '人手备几瓶特效火焰防护药水：二阶段的火球和三阶段地面裂缝喷出的岩浆都是火焰伤害，药水能实实在在吃掉一大块伤害。':
        'Bring a few Greater Fire Protection Potions for everyone: the Phase 2 Fireballs and the lava pulsing from the cracked floor in Phase 3 are all fire damage, and the potion absorbs a real chunk of it.',
    '奥妮克希亚卫士巡逻队':
        'Onyxian Warder patrols',
    '通往巢穴的路上散布着几组卫士巡逻队，最致命的技能是火焰新星——范围火焰伤害。常规做法是坦克把卫士拉住背对人群，近战等它放出第一轮火焰新星再进场输出，能省下大量治疗压力。':
        'Several Warder patrols are spread along the path to the lair; their deadliest ability is Fire Nova, an area-of-effect fire blast. The standard play is to have the tank pull the Warder facing away from the raid, and have melee wait out the first Fire Nova before moving in — this saves the healers a lot of pressure.',
    '整场战斗分三个阶段。一阶段（100%~65%，地面）：站位是第一要务——站侧面打，太靠近尾巴会被扫击击飞进蛋堆、引来一群幼龙，正脸有吐吸，坦克开怪后把龙头慢慢转向入口、自己背贴后墙定位（防翼击把坦克拍飞全场），定位完成前输出一律克制、保命大招全留到二阶段。二阶段（65%~40%，空中）：最危险的一段，她升空后飞到巢穴周围八个方位之一，周期性对随机玩家丢火球——全场彼此拉开 8 码以上分散站位；她「深呼吸」预警一出，全团立刻跑向她面向方向两侧的安全区，反应慢半拍就是团灭级伤害，特效火焰防护药水在这里非常值。三阶段（40% 以下，落地）：落地回房间中央，站位要求同一阶段——她重新定位前严禁提前开怪；新增恐惧咆哮，坦克靠狂暴之怒免疫、或依赖萨满的战栗图腾与牧师的防护恐惧；幼龙会零星刷出来捣乱，交给副坦克全部接住再 AOE 清掉；地面裂缝开始周期性喷发岩浆，踩上去就吃火焰伤害，注意脚下走位。':
        'The fight has three phases. Phase 1 (100%-65%, ground): positioning comes first — fight from her sides; standing too close to the tail risks Tail Sweep knocking you into the egg nest and spawning a swarm of whelps, and her front has a breath attack. After the pull the tank slowly turns her head toward the entrance and positions himself against the back wall (so Wing Buffet cannot knock him across the room). Until she is positioned, all damage stays light and every major cooldown is saved for Phase 2. Phase 2 (65%-40%, air): the most dangerous segment. She takes off and flies to one of eight spots around the lair, periodically throwing Fireballs at random players — spread out at least 8 yards from each other. As soon as the "taking a deep breath" warning appears, everyone runs to the safe zones on the sides of wherever she is facing; a slow reaction means raid-wiping damage. Greater Fire Protection Potions are worth a lot here. Phase 3 (below 40%, landed): she lands in the center of the room with the same positioning rules as Phase 1 — do not attack before she is repositioned. She gains Bellowing Roar (a fear): tanks counter it with Berserker Rage, or rely on Shaman Tremor Totems and Priest Fear Ward. Whelps spawn occasionally — have the off-tank pick them all up and AoE them down. The cracked floor starts pulsing lava every few seconds; watch your step to avoid the fire damage.',
}
