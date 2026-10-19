# -*- coding: utf-8 -*-
"""enUS 数据层翻译表（任务侧）：Data_DungeonQuests 自由文本手译 + 补充名 + 文件级覆写。

- 名字主体来自 enus_data_names.py（wowhead 官方英文名，脚本生成）；
- 本表收：任务目标 / 备注句 / 起始物品串 / 名字表没覆盖到的 NPC·物品名；
- FILE_EXACT 按文件覆写（「东部王国」在任务里是任务名，在 NPCLoc 里是地名）。
错译直接改本表重跑 gen_enus_data.py，禁手改产物。
"""

FILE_EXACT = {
    'Data_DungeonQuests.lua': {
        '东部王国': 'The Royal Rescue',   # quest 4003；NPCLoc 的地名走 ZONES 表
    },
}

QUESTS = {
    # ── 起始物品 / 特殊串 ──
    '由物品[血染的信件]起始': 'Starts from the item [Bloodstained Letter]',
    '由物品[洛丹伦纹章]起始': 'Starts from the item [Crest of Lordaeron]',
    '由物品[染血的徽记]起始': 'Starts from the item [Bloodstained Insignia]',
    '由物品[憎恶的头颅]起始': "Starts from the item [Abomination's Head]",
    '由物品[小卷轴]起始': 'Starts from the item [Small Scroll]',
    '由物品[揉皱的纸条]起始': 'Starts from the item [Crumpled Note]',
    '由物品[又钝又平的精灵之刃]起始': 'Starts from the item [Dull and Flat Elven Blade]',
    '掉落 - 见注释': 'Drops - see notes',
    '奥达曼内随机掉落': 'Random drop inside Uldaman',
    '诺莫瑞根随机掉落': 'Random drop in Gnomeregan',
    '通灵学院瘟疫龙崽随机掉落': 'Random drop from Plaguebats in Scholomance',
    '从脏兮兮的戒指清洁后获得': 'Obtained by cleaning the Grimy Ring',
    '奥达曼 副本入口地图）。': 'Uldaman (dungeon-entrance map).',
    'Gnomeregan - 清洁区': 'Gnomeregan - The Clean Zone',
    '注：2041 不是必须，不接也能直接接这个任务。':
        'Note: quest 2041 is not required — this quest can be taken directly.',
    '菌类孢子 → 药剂师扎玛': 'Serpentbloom → Apothecary Zamah',
    # ── 怒焰裂谷 ──
    '把「谅解条约」交给铁炉堡的国王麦格尼·铜须':
        'Take the "Treaty of Understanding" to King Magni Bronzebeard in Ironforge',
    '打完尾王后拾取「谅解条约」，拾取即开启本任务。': 'After defeating the final boss, loot the "Treaty of Understanding" — looting it starts this quest.',
    '鬼魅随从': 'Wandering Servant',
    '到怒焰裂谷搜寻玛尔·恐怖图腾的尸体和他留下的东西。':
        'Search Ragefire Chasm for the corpse of Maur Grimtotem and what he left behind.',
    '玛尔·恐怖图腾在副本内。拿到背包后带回雷霆崖交给拉哈罗。':
        'Maur Grimtotem is inside the dungeon. Bring the satchel back to Rahauro in Thunder Bluff.',
    '前往奥格瑞玛的怒焰裂谷，杀 8 个怒焰穴居人和 8 个怒焰萨满祭司，回雷霆崖向拉哈罗复命。':
        'Enter Ragefire Chasm in Orgrimmar, kill 8 Ragefire Troggs and 8 Ragefire Shamans, then report back to Rahauro in Thunder Bluff.',
    '进门就能看到穴居人。': 'The troggs are visible right after the entrance.',
    '寻找背包': 'Finding the Satchel',
    '把《暗影法术研究》和《扭曲虚空的魔法》两本书交给幽暗城的瓦里玛萨斯。':
        'Bring the two books "Studies in Shadow Magic" and "Magic of the Twisting Nether" to Varimathras in the Undercity.',
    '两本书都由燃刃信徒和燃刃术士掉落。':
        'Both books drop from Shadowcult Zealots and Shadowcult Warlocks.',
    '杀死巴扎兰和祈求者耶戈什，回奥格瑞玛见萨尔。':
        'Kill Bazzalan and Jergosh the Invoker, then report back to Thrall in Orgrimmar.',
    '巴扎兰在副本内，祈求者耶戈什在副本内。':
        'Bazzalan is inside the dungeon, and so is Jergosh the Invoker.',
    '进入怒焰裂谷杀死饥饿者塔拉加曼，把他的心脏交给奥格瑞玛的尼尔鲁·火刃。':
        'Enter Ragefire Chasm and kill Taragaman the Hungerer, then bring his heart to Arnak Fireblade in Orgrimmar.',
    '塔拉加曼在副本内。': 'Taragaman the Hungerer is inside the dungeon.',
    # ── 影牙 / 死亡矿井 ──
    '死亡守卫克里斯托夫': 'Death Guard Christoph',
    '集齐考布莱恩、安娜科德拉、皮萨斯、瑟芬迪斯四颗宝石，交给雷霆崖的纳拉·蛮鬃。':
        'Gather the four gems from Coblebrain, Lady Anacondra, Pisath and Sephendis, then hand them to Nara Wildmane in Thunder Bluff.',
    '系列始于哈缪尔·符文图腾（雷霆崖 - 长者高地 78,28）。四名掉宝石的德鲁伊分散在副本内的四个房间。':
        "The chain starts with Hamuul Runetotem (Thunder Bluff - Elder Rise 78,28). The four druids who drop the gems are spread across the four rooms of the dungeon.",
    '哀嚎洞穴的纳尔帕克想要 20 张变异皮革。':
        'Nalpak of the Wailing Caverns wants 20 Mutated Hides.',
    '副本内外所有变异怪都可能掉皮革。纳尔帕克在入口上方的山顶洞穴里。':
        'All the mutated creatures inside and outside the dungeon can drop the hides. Nalpak is in the cave on the hilltop above the entrance.',
    '迅猛龙角': 'Raptor Horn',
    '收集 6 份哀嚎香精，交给棘齿城的麦伯克·米希瑞克斯。':
        'Collect 6 Wailing Essences and bring them to Mebok Mizzyrix in Ratchet.',
    '前置同样在麦伯克·米希瑞克斯处接。香精由软浆怪掉落。':
        'The prerequisite is also taken from Mebok Mizzyrix. The essences drop from the ooze creatures.',
    '从哀嚎洞穴里的疯狂的马格利什手中取回一瓶 99 年波尔多陈酿，交给棘齿城的比戈弗兹。':
        "Retrieve a bottle of 99-Year Old Port from Mad Maglish inside the Wailing Caverns and bring it to Crane Operator Bigglefuzz in Ratchet.",
    '进洞后右转，马格利什就待在凹进去的洞里。':
        "Turn right after entering the cave — Mad Maglish is holed up in a recessed alcove.",
    '为雷霆崖的药剂师扎玛收集 10 朵毒蛇花。':
        'Gather 10 Serpentblooms for Apothecary Zamah in Thunder Bluff.',
    '前置任务找药剂师赫布瑞姆接（贫瘠之地 - 十字路口 51,30）。副本前的山洞和副本内都能采到；学了草药学开追踪会在小地图上显示。':
        "The prerequisite quest is taken from Apothecary Helbrim (The Barrens - The Crossroads 51,30). The flowers can be picked in the cave before the dungeon and inside it; with Herbalism tracking learned they show on the minimap.",
    '替哀嚎洞穴的厄布鲁清剿：杀 7 只变异破坏者、7 只剧毒飞蛇、7 只变异蹒跚者、7 只变异尖牙风蛇。':
        'Clear out the Wailing Caverns for Ebru: kill 7 Mutated Destroyers, 7 Venomfangs, 7 Mutated Shamblers and 7 Mutated Fangwind Serpents.',
    '厄布鲁也在入口上方的山顶洞穴里。':
        'Ebru is also in the cave on the hilltop above the entrance.',
    '发光的碎片掉落自（『吞噬者』穆坦努斯）':
        "The Glowing Shard drops from (Mutanus the Devourer)",
    '去棘齿城打听这块噩梦碎片的更多信息。':
        'Ask around in Ratchet for more information about this Nightmare Shard.',
    # ── 死亡矿井 + 爆破链 ──
    '从月溪镇收集 8 份可疑的工业补给品。补给品箱不在镇上街头，在通往死亡矿井入口的建筑内，沿路下到洞穴中即可找到。':
        'Collect 8 Suspicious Industrial Supplies from Moonbrook. The crates are not on the town streets — they are inside the building leading to the Deadmines entrance, down the path into the cave.',
    '毒素调查链的一环：几处矿井的样本都查过了，线索都指向月溪镇下方的死亡矿井。到月溪镇收集补给品，回阿尔巴·晴月处交任务后开启爆炸物筹备段。前导环「测井」的两个采样点：莫尔森农场 46.2,38.3、詹森农庄 56.7,18.7。':
        "Part of the toxin investigation chain: samples from several mines have been checked and all point to the Deadmines beneath Moonbrook. Collect the supplies in Moonbrook, turn the quest in to Alba Fairmoon, and the explosive-preparation stage opens. Two sampling points of the leading \"Well Logging\" step: Molson Farm 46.2,38.3 and Jensen Farmstead 56.7,18.7.",
    '找到深藏于死亡矿井中的熔炉，在旁安放强效炸药；随后在死亡矿井出口与阿尔巴·晴月会合。':
        'Find the furnace deep inside the Deadmines and place the Powerful Blasting Charge beside it; then rendezvous with Alba Fairmoon at the Deadmines exit.',
    '本链的副本段：进本前炸药已由爆炸物筹备段（斯普莱特 → 贾斯伯·菲尔）备齐。安放炸药后从副本出口出来，到月溪镇后方的山丘与阿尔巴·晴月会合。':
        "The dungeon stage of this chain: the charge is prepared before you enter by the explosive-preparation stage (Sprocket → Jasper Fel). After placing the charge, exit the dungeon and meet Alba Fairmoon on the hill behind Moonbrook.",
    '使用遥控起爆器，引爆安放在熔炉旁的炸药。':
        'Use the remote detonator to set off the charge placed beside the furnace.',
    '「爆破死亡矿井」的收尾环：与月溪镇后方山丘的阿尔巴·晴月会合后，使用起爆器收尾。':
        'The closing step of "Demolition of the Deadmines": after rendezvousing with Alba Fairmoon on the hill behind Moonbrook, finish it off with the detonator.',
    '击杀艾德温·范克里夫，把他的头颅带回去交给格里安·斯托曼。':
        'Kill Edwin VanCleef and bring his head back to Marshal Gryan Stoutmantle.',
    '整个系列从格里安·斯托曼（西部荒野 - 哨兵岭 56,47）开始。范克里夫是死亡矿井的最终 首领，在船的最上层。':
        "The whole chain starts with Marshal Gryan Stoutmantle (Westfall - Sentinel Hill 56,47). VanCleef is the final boss of the Deadmines, on the top deck of the ship.",
    '收集 4 张矿业工会会员卡，交给暴风城的维尔德·蓟草。':
        'Collect 4 Miners\' Union Membership Cards and bring them to Wilder Thistlenettle in Stormwind City.',
    '会员卡由副本入口附近的亡灵掉落。':
        'The cards drop from the undead near the dungeon entrance.',
    '收集 10 条红色丝质面罩，交给哨兵岭哨塔的哨兵瑞尔。':
        'Collect 10 Red Silk Bandanas and bring them to Scout Riell in the watchtower of Sentinel Hill.',
    '副本内外的矿工都会掉面罩。要先完成「护送迪菲亚叛徒」才会开放这个任务。':
        'The miners inside and outside the dungeon all drop bandanas. You must complete "The Defias Traitor" escort first before this quest opens.',
    '取回探险者协会徽章，交给暴风城的维尔德·蓟草。':
        "Retrieve the Explorer's League badge and bring it to Wilder Thistlenettle in Stormwind City.",
    '徽章由副本入口处的工头希斯奈特掉落。':
        "The badge drops from Foreman Thistlenetting at the dungeon entrance.",
    '从死亡矿井带回小型高能发动机，交给暴风城矮人区的沉默的舒尼。':
        "Retrieve the Compact High-Energy Engine from the Deadmines and bring it to Shoni the Shilent in the Dwarven District of Stormwind City.",
    '这个任务可以直接接，也可以先做诺恩（铁炉堡 - 侏儒区 69,50）给的引导任务。发动机由斯尼德的伐木机掉落。':
        "This quest can be taken directly, or you can first do the intro quest from Nogg (Ironforge - Tinker Town 69,50). The engine drops from Sneed's Shredder.",
    '未寄出的信掉落自（艾德温·范克里夫）':
        'The Unsent Letter drops from (Edwin VanCleef)',
    '搜查艾德温·范克里夫的尸体，找到一封没来得及寄出的信——收信人是暴风城石工协会的巴隆斯·阿历克斯顿。':
        "Search Edwin VanCleef's body for a letter that was never sent — it is addressed to Baros Alexston of the Stonemasons' Guild in Stormwind City.",
    '巴隆斯·阿历克斯顿在暴风城大教堂旁（58,49）。':
        "Baros Alexston is next to the Cathedral in Stormwind City (58,49).",
    '按乔丹的武器材料单备齐白石橡木、精炼矿石、乔丹的铁锤和科尔宝石，回铁炉堡见乔丹·斯迪威尔。':
        "Gather the materials on Jordan's weapon list — White Stone Oak, Refined Ore, Jordan's Hammer and the Kol Gem — and return to Jordan Stilwell in Ironforge.",
    '材料明细点开 [乔丹的武器材料单] 可以看到。':
        "Click [Jordan's Weapon Materials List] to see the details.",
    '把乌尔之书带给幽暗城炼金区的看守者贝尔杜加。':
        "Bring the Book of Ur to Keeper Bel'dugur in the Apothecarium of the Undercity.",
    '进门左手边就能拿到书。': 'The book can be picked up on the left just inside the entrance.',
    '杀死阿鲁高，把他的头带给瑟伯切尔的达拉尔·道恩维沃尔。':
        'Kill Arugal and bring his head to Dalar Dawnweaver at the Sepulcher.',
    '阿鲁高在副本内。': 'Arugal is inside the dungeon.',
    '找到亡灵哨兵阿达曼特和亡灵哨兵文森特。':
        'Find Sentinel Adamant and Sentinel Vincent.',
    '阿达曼特在副本内；文森特进庭院后右手边。':
        'Adamant is inside the dungeon; Vincent is on the right after entering the courtyard.',
    # ── 黑暗深渊 / 剃刀 ──
    '集齐 3 块索兰鲁克宝珠碎片和 1 块大碎片，交给贫瘠之地的杜安·卡汉。':
        "Collect 3 Shards of Solanruk's Orb and 1 Large Shard, and bring them to Duane Kahan in the Barrens.",
    '仅术士可接！碎片打黑暗深渊的暮光侍僧；大碎片去影牙城堡打影牙魔魂狼人。':
        'Warlock only! The shards drop from Twilight Acolytes in Blackfathom Deeps; the large shard drops from the Shadowfang Moonrunner wolves in Shadowfang Keep.',
    '把洛迦里斯手稿带给铁炉堡的葛利·硬骨。':
        "Bring the Lorgalis Manuscript to Gerrig Bonegrip in Ironforge.",
    '手稿泡在副本内一处水洼里。':
        'The manuscript is soaking in a pool inside the dungeon.',
    '收集 20 颗阿库麦尔蓝宝石，交给灰谷的耶努萨克雷。':
        "Collect 20 Aku'mai Sapphires and bring them to Je'neu Sancrea in Ashenvale.",
    '前置《帮助耶努萨克雷》可在苏纳曼（石爪山脉 - 烈日石居 47,64）接。蓝宝石长在通往黑暗深渊入口那条通道的洞壁上。':
        "The prerequisite \"Helping Je'neu Sancrea\" can be taken from Sunaman (Stonetalon Mountains - Sun Rock Retreat 47,64). The sapphires grow on the cave walls along the passage leading to the Blackfathom Deeps entrance.",
    '潮湿的便笺': 'A Damp Note',
    '把潮湿的便笺交给灰谷的耶努萨克雷；随后杀掉黑暗深渊的洛古斯·杰特并向他复命。':
        "Deliver the Damp Note to Je'neu Sancrea in Ashenvale; then kill Lorgus Jett in Blackfathom Deeps and report back.",
    '便笺由黑暗深渊的海潮祭司掉落（约 5%）。耶努萨克雷在灰谷 - 佐拉姆加前哨站（11,33）。洛古斯·杰特在副本内。':
        "The note drops from the Tide Priests of Blackfathom Deeps (about 5%). Je'neu Sancrea is at Zoram'gar Outpost in Ashenvale (11,33). Lorgus Jett is inside the dungeon.",
    '进入黑色深渊寻找银月守卫塞尔瑞德。':
        'Enter Blackfathom Deeps and find Argent Guard Thaelrid.',
    '塞尔瑞德在副本内。': 'Thaelrid is inside the dungeon.',
    '取回梦游者克尔里斯的头颅，交给达纳苏斯的哨兵塞尔高姆。':
        "Retrieve the head of Sleepwalker Kerlis and bring it to Sentinel Selgolm in Darnassus.",
    '克尔里斯在副本内；塞尔高姆（达纳苏斯 - 工匠区 55,24）。小心：点燃克尔里斯旁边的火焰会触发敌人增援。':
        "Kerlis is inside the dungeon; Selgolm is at (Darnassus - Craftsmen's Terrace 55,24). Careful: lighting the brazier next to Kerlis triggers enemy reinforcements.",
    '为奥伯丁的戈沙拉·夜语收集 8 块堕落者的脑干。':
        "Collect 8 Corrupted Brainstems for Gershala Nightwhisper in Auberdine.",
    '前置可找阿古斯·夜语接（暴风城 - 花园 36,67）。副本内外所有纳迦都掉脑干。':
        "The prerequisite can be taken from Argus Nightwhisper (Stormwind City - The Park 36,67). All naga inside and outside the dungeon drop the brainstems.",
    '把梦游者克尔里斯的头颅带回雷霆崖交给巴珊娜·符文图腾。':
        'Bring the head of Sleepwalker Kerlis back to Bashana Runetotem in Thunder Bluff.',
    '克尔里斯在副本内；巴珊娜·符文图腾在雷霆崖 - 长者高地（70,33）。小心：点燃克尔里斯身旁的火焰会引来敌人。':
        "Kerlis is inside the dungeon; Bashana Runetotem is at Thunder Bluff - Elder Rise (70,33). Careful: lighting the brazier beside Kerlis attracts enemies.",
    '收集 10 个暮光坠饰，交给达纳苏斯的银月守卫玛纳杜斯。':
        'Collect 10 Twilight Pendants and bring them to Argent Guard Manados in Darnassus.',
    '暮光之锤的敌人个个都掉坠饰。':
        'Every Twilight Hammer enemy drops the pendants.',
    '把深渊之核交给灰谷佐拉姆加前哨站的耶努萨克雷。':
        "Bring the Core of the Deeps to Je'neu Sancrea at Zoram'gar Outpost in Ashenvale.",
    '深渊之核在副本内的水域里。拿到后阿奎尼斯男爵会出现并攻击你，他掉一件任务物品，也一并带给耶努萨克雷。':
        "The Core of the Deeps is in the waters inside the dungeon. Once you take it, Baron Aquanis appears and attacks you — he drops a quest item; bring that to Je'neu Sancrea as well.",
    '杀死巴基尔·斯瑞德，把头颅带给典狱官塞尔沃特。':
        'Kill Bazil Thredd and bring his head to Warden Thelwater.',
    '前置见死亡矿井的「迪菲亚兄弟会」系列。巴基尔·斯瑞德在副本内。':
        'See the "Defias Brotherhood" chain of the Deadmines for the prerequisite. Bazil Thredd is inside the dungeon.',
    '杀死迪克斯特·瓦德，把他的手带回去给夜色镇的米尔斯迪普议员作证明。':
        "Kill Dexter Ward and bring his hand back to Councilman Millstipe of Darkshire as proof.",
    '迪克斯特·瓦德在副本内。': 'Dexter Ward is inside the dungeon.',
    '把卡姆·深怒的头颅交给丹莫德的莫特雷·加玛森。':
        "Bring the head of Kam Deepfury to Motley Garmason in Dun Modr.",
    '前置任务同样找莫特雷·加玛森接。卡姆·深怒在副本内。':
        'The prerequisite is also taken from Motley Garmason. Kam Deepfury is inside the dungeon.',
    '把塔格尔的头颅带给湖畔镇的卫兵伯尔顿。':
        'Bring the head of Targorr to Guard Berton in Lakeshire.',
    '塔格尔在副本内。': 'Targorr is inside the dungeon.',
    '替暴风城典狱官塞尔沃特清点监狱：杀 10 名迪菲亚囚徒、8 名迪菲亚罪犯、8 名迪菲亚叛军。':
        'Take stock of the Stockade for Warden Thelwater of Stormwind: kill 10 Defias Convicts, 8 Defias Criminals and 8 Defias Insurgents.',
    '任务由副本外的典狱官发放。': 'The quest is issued by the warden outside the dungeon.',
    '收集 10 条红色毛纺面罩，交给暴风城的尼科瓦·拉斯克。':
        'Collect 10 Red Wool Bandanas and bring them to Nikova Raskol in Stormwind City.',
    # ── 诺莫瑞根 ──
    '等斯库提把地精传送器调好。': 'Wait while Scooty fixes the goblin teleporter.',
    '前置可从索维克（奥格瑞玛 - 荣誉谷 75,25）接。完成后就能使用藏宝海湾的传送器。':
        "The prerequisite can be taken from Sovik (Orgrimmar - Valley of Honor 75,25). After completing it you can use the Booty Bay teleporter.",
    '把尖端机器人的存储器核心交给铁炉堡的工匠大师欧沃斯巴克。':
        "Bring the Storage Core of Techbot to Tinkmaster Overspark in Ironforge.",
    '前置可从萨尔努修士接（暴风城 - 教堂广场 51,48）。尖端机器人在进副本前、后门附近。':
        "The prerequisite can be taken from Brother Sarno (Stormwind City - Cathedral Square 51,48). Techbot is near the back door before entering the dungeon.",
    '用空铅瓶从辐射入侵者或辐射抢劫者身上收集放射尘，装满后交给卡拉诺斯的奥齐·电环。':
        "Use the Empty Lead Vial to collect Irradiated Dust from Irradiated Invaders or Irradiated Pillagers, fill it, and bring it to Ozzie Togglevolt in Kharanos.",
    '前置可从诺恩接（铁炉堡 - 侏儒区 69,50）。取样方法：对活着的辐射入侵者/抢劫者使用空铅瓶。':
        "The prerequisite can be taken from Nogg (Ironforge - Tinker Town 69,50). Sampling method: use the Empty Lead Vial on a living Irradiated Invader/Pillager.",
    '收集 24 副机械内胆，交给暴风城的舒尼。':
        'Collect 24 Mechanical Gizzards and bring them to Shoni in Stormwind City.',
    '所有机器人都掉内胆。': 'All the robots drop gizzards.',
    '到诺莫瑞根收集高强度辐射尘（极不稳定、会很快分解），并把沉重的铅瓶一并交还奥齐。':
        "Collect High-Efficiency Irradiated Dust in Gnomeregan (highly unstable, it decays quickly) and return the Heavy Lead Vial to Ozzie as well.",
    '取样方法：对活着的辐射泥浆怪、辐射潜伏者、辐射水元素使用沉重的铅瓶。':
        'Sampling method: use the Heavy Lead Vial on living Irradiated Oozes, Irradiated Creepers or Irradiated Water Elementals.',
    '把克努比护送到出口，然后回藏宝海湾向斯库提汇报。':
        'Escort Kernobee to the exit, then report back to Scooty in Booty Bay.',
    '护送任务。斯库提在荆棘谷 - 藏宝海湾（27,77）。':
        'Escort quest. Scooty is in Stranglethorn Vale - Booty Bay (27,77).',
    '收集 12 个基础模组，交给铁炉堡的科劳莫特·钢尺。':
        'Collect 12 Basic Modules and bring them to Klockmort Spannerspan in Ironforge.',
    '前置可从玛希尔接（达纳苏斯 - 战士区 59,45）。诺莫瑞根的所有敌人都可能掉。':
        "The prerequisite can be taken from Mahir (Darnassus - Warriors' Terrace 59,45). All enemies in Gnomeregan can drop them.",
    '从诺莫瑞根取回钻探设备蓝图和麦克尼尔的保险箱密码，交给奥格瑞玛的诺格。':
        "Retrieve the drilling rig blueprints and the combination to Mekgineer's Safe from Gnomeregan and bring them to Nogg in Orgrimmar.",
    '麦克尼尔·瑟玛普拉格是诺莫瑞根最终 首领。战斗中记得按他旁边的按钮，阻止他丢炸弹。':
        "Mekgineer Thermaplugg is the final boss of Gnomeregan. During the fight, remember to press the button beside him to stop him throwing bombs.",
    '进入诺莫瑞根击杀麦克尼尔·瑟玛普拉格，完成后向大工匠梅卡托克报告。':
        'Enter Gnomeregan and kill Mekgineer Thermaplugg, then report to High Tinker Mekkatorque.',
    '他是最终 首领。战斗中要按他旁边的按钮阻止他丢炸弹。':
        'He is the final boss. During the fight, press the button beside him to stop him throwing bombs.',
    '把彩色穿孔卡片交给铁炉堡的大机械师卡斯派普。':
        'Bring the Colorful Punch Cards to Master Mechanic Castpipe in Ironforge.',
    '前置可从加克希姆·尘链接（石爪山脉 59,67），非必需。白卡随机掉落。四台终端位置：进副本前后门附近一台，副本内、、 各一台。':
        'The prerequisite can be taken from Jaxxim Dustchain (Stonetalon Mountains 59,67), but it is optional. The white card drops randomly. Locations of the four terminals: one near the back door before the entrance, and one each inside the dungeon.',
    '把脏兮兮的物品放进超级清洁器 5200 型，投三枚银币启动机器。':
        'Put grimy items into the Super Cleaner 5200, insert three silver coins to start the machine.',
    '所有「脏兮兮的」物品都可以重复做这个任务。':
        'This quest is repeatable with all "grimy" items.',
    '想办法把脏兮兮的戒指弄干净。': 'Figure out how to get the Grimy Ring cleaned.',
    '用清洁器 5200 型清洗即可，机器在副本内。':
        'Just clean it with the Super Cleaner 5200 — the machine is inside the dungeon.',
    '这枚戒指你可以留下，也可以按内侧刻的名字找到失主。':
        'You may keep the ring, or find its owner by the name engraved inside.',
    '交给塔瓦斯德·基瑟尔（铁炉堡 - 秘法区 36,3）。奖励戒指属性随机。':
        "Bring it to Talvash del Kissel (Ironforge - Mystic Ward 36,3). The reward ring's stats are random.",
    '交给诺格（奥格瑞玛 - 荣誉谷 75,25）。奖励戒指属性随机。':
        "Bring it to Nogg (Orgrimmar - Valley of Honor 75,25). The reward ring's stats are random.",
    '凑齐开孔的箱子、地鼠指挥棒和《地鼠指挥手册》；在剃刀沼泽用箱子召唤地鼠并驱使它搜出蓝叶薯；最后把指挥棒、箱子和 10 块蓝叶薯一起交给棘齿城的麦伯克·米希瑞克斯。':
        'Gather the Opened Chest, the Gopher Cane and the "Gopher Command Manual"; use the chest in Razorfen Kraul to summon the gopher and make it sniff out the Blueleaf Tubers; finally bring the cane, the chest and 10 Blueleaf Tubers to Mebok Mizzyrix in Ratchet.',
    '箱子和手册都能在麦伯克·米希瑞克斯附近找到。':
        'Both the chest and the manual can be found near Mebok Mizzyrix.',
    # ── 战士职业 / 剃刀 ──
    '为暴风城的弗伦·长须收集指定材料。':
        'Gather the specified materials for Frun Longbeard in Stormwind City.',
    '仅战士可接！燃素从鲁古格获取；烧焦的蜘蛛牙出自湿地蜘蛛，烧焦的奇美拉角、光滑的奇美拉角分别出自石爪山脉的奇美拉幼崽和雌奇美拉。':
        'Warrior only! Phlogiston comes from Rukhug; Scorched Spider Fangs from the Wetlands spiders, and Scorched Chimaera Horns / Smooth Chimaera Horns from the chimaera cubs and females of the Stonetalon Mountains.',
    '为索恩格瑞姆收集 15 根烟雾铁锭、10 份蓝铜粉、10 块铁锭和 1 瓶燃素。':
        'Collect 15 Smoky Iron Ingots, 10 Azurite Powders, 10 Iron Bars and 1 vial of Phlogiston for Thorngrimr.',
    '仅战士可接！燃素从鲁古格获取。交付后他会接着给后续任务。':
        'Warrior only! Phlogiston comes from Rukhug. After turning in, he will offer the follow-up quest.',
    '护送进口商威利克斯逃出剃刀沼泽。':
        'Escort Willix the Importer out of Razorfen Kraul.',
    '把他一路护送到入口，任务在他本人处交付领奖。':
        'Escort him all the way to the entrance; the quest is turned in to him personally for the reward.',
    '找回塔莎拉的坠饰并交还给达纳苏斯的塔莎拉·静水。':
        "Retrieve Thalara's Pendant and return it to Thalara Fallowbrook in Darnassus.",
    '坠饰为随机掉落。交回地点：塔莎拉·静水（达纳苏斯 - 贸易区 69,67）。':
        "The pendant is a random drop. Turn-in location: Thalara Fallowbrook (Darnassus - Trade District 69,67).",
    '把卡尔加·刺肋的徽章交给萨兰纳尔的法芬德尔。':
        "Bring Calgar Spinegouge's badge to Falfindel Waywarder in Sarannar.",
    '徽章由卡尔加·刺肋掉落。': "The badge drops from Calgar Spinegouge.",
    '把卡尔加·刺肋的心脏交给雷霆崖的奥尔德·石塔。':
        "Bring Calgar Spinegouge's heart to Auld Stonespire in Thunder Bluff.",
    '卡尔加·刺肋在副本内。': 'Calgar Spinegouge is inside the dungeon.',
    '替幽暗城的大药剂师法拉尼尔收集一份沼泽蝙蝠的粪便。':
        'Collect a sample of Marsh Bat guano for Master Apothecary Faranell of the Undercity.',
    '副本里任何蝙蝠都会掉。': 'Any bat in the dungeon drops it.',
    '把沃瑞尔·森加斯的结婚戒指还给塔伦米尔的莫尼卡·森古特斯。':
        "Return Vorrel Sengutz's wedding ring to Monika Sengutz in Tarren Mill.",
    '戒指在血色修道院墓地区前部的沃瑞尔·森加斯身上；南茜（奥特兰克山脉 31,32）也持有任务相关物品。':
        "The ring is on Vorrel Sengutz in the front part of the Scarlet Monastery Graveyard; Nancy (Alterac Mountains 31,32) also holds a quest-related item.",
    '找回《亡灵的起源》，交给幽暗城的帕科瓦·芬塔拉斯。':
        'Recover "The Origins of the Undead" and bring it to Parqual Fintallas in the Undercity.',
    '系列始于多恩·平原行者（千针石林 53,41）。书在血色修道院图书馆。':
        "The chain starts with Dorn Plainstalker (Thousand Needles 53,41). The book is in the Scarlet Monastery Library.",
    '从血色修道院取回《堕落者纲要》，交给雷霆崖的圣者图希克。':
        'Retrieve "Compendium of the Fallen" from the Scarlet Monastery and bring it to Sage Truthseeker in Thunder Bluff.',
    '书在图书馆区。被遗忘者因剧情原因接不了这个任务。':
        'The book is in the Library area. The Forsaken cannot take this quest for story reasons.',
    '从修道院取回《泰坦神话》，交给铁炉堡的图书馆员麦伊·苍尘。':
        'Retrieve "Mythology of the Titans" from the Monastery and bring it to Librarian Mae Paledust in Ironforge.',
    '书在图书馆里奥法师杜安房间之前、左侧走廊的地板上。':
        "The book is on the floor of the left corridor, before Arcanist Doan's room in the Library.",
    '替幽暗城的大药剂师法拉尼尔收集 20 颗狂热之心。':
        'Collect 20 Hearts of Zeal for Master Apothecary Faranell of the Undercity.',
    '血色修道院里所有怪物都有几率掉。':
        'Every mob in the Scarlet Monastery has a chance to drop them.',
    '把《能量仪祭》交给尘泥沼泽的塔贝萨。':
        'Bring "Rituals of Power" to Tabetha in Dustwallow Marsh.',
    '法师职业任务。书在血色修道院图书馆、奥法师杜安房间之前左侧走廊的地板上。':
        "Mage class quest. The book is in the Scarlet Monastery Library, on the floor of the left corridor before Arcanist Doan's room.",
    '击杀大检察官怀特迈恩、血色十字军指挥官莫格莱尼、勇士赫洛德和驯犬者洛克希，回幽暗城向瓦里玛萨斯复命。':
        'Kill High Inquisitor Whitemane, Scarlet Commander Mograine, Herod the Champion and Houndmaster Loksey, then report back to Varimathras in the Undercity.',
    '怀特迈恩与莫格莱尼在教堂区，赫洛德在军械库，洛克希在图书馆。':
        'Whitemane and Mograine are in the Cathedral, Herod in the Armory, Loksey in the Library.',
    '击杀大检察官怀特迈恩、指挥官莫格莱尼、勇士赫洛德和驯犬者洛克希，回南海镇向莱雷恩复命。':
        'Kill High Inquisitor Whitemane, Commander Mograine, Herod the Champion and Houndmaster Loksey, then report back to Raleigh the Devout in Southshore.',
    '系列始于克罗雷修士（暴风城 - 大教堂 52,43），也可从凄凉之地尼耶尔前哨站的血色十字军使者处直接接。三个目标位置：教堂（怀特迈恩、莫格莱尼）、军械库（赫洛德）、图书馆（洛克希）。':
        "The chain starts with Brother Crowley (Stormwind City - Cathedral District 52,43); it can also be taken directly from the Scarlet Crusade emissary at Nijel's Point in Desolace. The three targets: Cathedral (Whitemane, Mograine), Armory (Herod), Library (Loksey).",
    '把玛克林大使的头颅带给幽暗城的瓦里玛萨斯。':
        "Bring Ambassador Marquin's head to Varimathras in the Undercity.",
    '前置由剃刀沼泽的最终 首领 给出。玛克林大使在进副本前的空地上（贫瘠之地 - 剃刀高地 48,92）。':
        'The prerequisite is given by the final boss of Razorfen Kraul. Ambassador Marquin is in the open area before the dungeon (The Barrens - Razorfen Downs 48,92).',
    '杀 8 个剃刀沼泽护卫者、8 个剃刀沼泽织棘者和 8 个亡首教徒，向剃刀高地入口处的麦雷姆·月歌复命。':
        'Kill 8 Razorfen Guardians, 8 Razorfen Weavers and 8 Death Cultists, then report to Myriam Moonsinger at the Razorfen Downs entrance.',
    '这三种怪都在进副本前经过的路上。':
        'All three of these mobs are on the path you take before entering the dungeon.',
    '陪奔尼斯特拉兹到剃刀高地的野猪人神像处，在他仪式封印神像时保护他。':
        'Accompany Belnistrasz to the quillboar idol in Razorfen Downs and protect him while his ritual seals it.',
    '接受协助后仪式期间会不断刷怪攻击他，保证他不倒；完成后在神像前交付领奖。':
        'Once you agree to help, waves of mobs will attack him throughout the ritual — keep him alive; when it is done, turn the quest in at the idol for the reward.',
    '替安德鲁·布隆奈尔击杀寒冰之王亚门纳尔，带回他的头骨。':
        "Kill Amnennar the Coldbringer for Andrew Brownell and bring back his skull.",
    '寒冰之王亚门纳尔是剃刀高地的最终 首领。':
        'Amnennar the Coldbringer is the final boss of Razorfen Downs.',
    '替大主教本尼迪塔斯击杀剃刀高地的寒冰之王亚门纳尔。':
        'Kill Amnennar the Coldbringer of Razorfen Downs for Archbishop Benedictus.',
    '他是剃刀高地的最终 首领。': 'He is the final boss of Razorfen Downs.',
    # ── 奥达曼 ──
    '为千针石林的普兹克收集 4 块精铁矿石。':
        'Collect 4 refined iron ore for Pozzik of the Thousand Needles.',
    '前置完成后的可重复任务，只给少量金钱，无声望经验。矿石可在奥达曼内采矿获得，也能从玩家处买。':
        'Repeatable after the prerequisite; gives only a little money, no reputation or experience. The ore can be mined inside Uldaman or bought from other players.',
    '收集 4 个雕纹石罐，交给洛克莫丹的勘察员基恩萨·铁环。':
        'Collect 4 Carved Stone Urns and bring them to Prospector Ironband of Loch Modan.',
    '系列始于勘察员塔伯斯·雷矛（铁炉堡 - 探险者大厅 74,12）。石罐散落在副本前的山洞里。':
        "The chain starts with Prospector Tabor Stormpike (Ironforge - Hall of Explorers 74,12). The urns are scattered in the cave before the dungeon.",
    '把雷乌纳石板带给迷失者塞尔杜林。':
        "Bring the Rewuna Stone Tablet to Theldurin the Lost.",
    '石板在洞穴北端通道尽头。':
        'The tablet is at the end of the passage in the north end of the cave.',
    '为荒芜之地的里格弗兹收集 8 块德提亚姆能量石和 8 块安纳洛姆能量石。':
        'Collect 8 Detiam Power Stones and 8 Annalom Power Stones for Rigglefuzz of the Badlands.',
    '副本内外的暗炉系敌人都掉能量石。':
        'The Shadowforge enemies inside and outside the dungeon all drop the power stones.',
    '血帆海盗': 'Bloodsail Buccaneers',
    '到奥达曼北部大厅找到克罗姆·粗臂的箱子，取出里面的财物，带回铁炉堡交给他。':
        "Find Krom Stoutarm's Chest in the northern hall of Uldaman, take the treasure inside, and bring it back to him in Ironforge.",
    '财物在进副本前的洞穴里，北面第一条通道东南角尽头。':
        "The treasure is in the cave before the dungeon, at the end of the first passage to the southeast in the north.",
    '从奥达曼南部大厅的箱子里找回加勒特的家族宝藏，交给幽暗城的帕特里克·加瑞特。':
        "Recover Garrett's family treasure from the chest in the southern hall of Uldaman and bring it to Patrick Garrett in the Undercity.",
    '宝藏进副本前就能拿到，在南部通道尽头。':
        'The treasure can be reached before entering the dungeon, at the end of the southern passage.',
    '进入奥达曼找到铁趾格雷兹。':
        'Enter Uldaman and find Hammertoe Grez.',
    '系列始于一张弄皱的地图（荒芜之地 53,33）。铁趾格雷兹在副本入口附近。':
        'The chain starts with a crumpled map (Badlands 53,33). Hammertoe Grez is near the dungeon entrance.',
    '找回铁趾的护符，交给奥达曼的铁趾格雷兹。':
        "Retrieve Hammertoe's amulet and bring it to Hammertoe Grez in Uldaman.",
    '护符由马格雷甘·深影掉落。':
        'The amulet drops from Magregan Deepshadow.',
    '找到意志石板，交给铁炉堡的顾问贝尔格拉姆。':
        'Find the Tablet of Resolve and bring it to Advisor Belgrum in Ironforge.',
    '石板在副本内。': 'The tablet is inside the dungeon.',
    '驱除魔鬼': 'Exorcism',
    '找到一个黑曜石能量源，交给尘泥沼泽的塔贝萨。':
        'Find an Obsidian Power Source and bring it to Tabetha in Dustwallow Marsh.',
    '仅法师可做！能量源由黑曜石哨兵掉落。':
        'Mage only! The power source drops from the Obsidian Sentinel.',
    '读完巴尔洛戈的日记、探明密室，回铁炉堡向勘察员塔伯斯·雷矛汇报。':
        'Read Baelog\'s diary, uncover the hidden chamber, then report back to Prospector Tabor Stormpike in Ironforge.',
    '采到 12 颗紫色蘑菇，带回塞尔萨玛交给加克。':
        'Collect 12 Purple Lotuses and bring them back to Ghak Healtouch in Thelsamar.',
    '蘑菇散落在副本各处；学了草药学并开启草药追踪的话，小地图上会直接标出来。前置任务同样在这名 NPC 处接。':
        'The mushrooms are scattered throughout the dungeon; with Herbalism and Find Herbs enabled they are marked directly on the minimap. The prerequisite is taken from the same NPC.',
    '收集 12 颗紫色蘑菇，交给卡加斯的加卡尔。':
        'Collect 12 Purple Lotuses and bring them to Jarkal Mossmeld in Kargath.',
    '前置同样在加卡尔处接。蘑菇散落副本各处；开草药追踪的小地图会直接标出。':
        'The prerequisite is also taken from Jarkal Mossmeld. The mushrooms are scattered throughout the dungeon; Find Herbs marks them on the minimap.',
    '查清破碎项链的来历，评估它的价值。':
        'Find out the history of the Broken Necklace and assess its value.',
    '把项链带给铁炉堡的塔瓦斯德·基瑟尔（铁炉堡 - 秘法区 36,3）。':
        "Bring the necklace to Talvash del Kissel in Ironforge (Ironforge - Mystic Ward 36,3).",
    '到奥达曼寻找塔瓦斯的魔法项链——死去的圣骑士是最后一个持有者。':
        "Search Uldaman for Talvash's magic necklace — a dead paladin was its last holder.",
    '那名圣骑士在副本内。': 'The paladin is inside the dungeon.',
    '塔瓦斯德的占卜之碗': "Talvash's Divining Bowl",
    '从奥达曼最强的石人身上取得能量源，交给铁炉堡的塔瓦斯德。':
        "Take the power source from the strongest stone golem of Uldaman and bring it to Talvash in Ironforge.",
    '破碎项链的能量源由阿扎达斯掉落。':
        "The necklace's power source drops from Archaedas.",
    '在奥达曼挖掘场找一条珍贵的项链（可能已损坏），交给奥格瑞玛的德兰·杜佛斯。':
        'Look for a valuable necklace (possibly damaged) at the Uldaman excavation and bring it to Dran Droffers in Orgrimmar.',
    '项链是副本内随机掉落。': 'The necklace is a random drop inside the dungeon.',
    '到奥达曼寻找与宝石有关的线索。':
        'Search Uldaman for clues about the gems.',
    '在荒芜之地卡加斯哨所找一个能翻译圣骑士日记的人。':
        'Find someone at Kargath Outpost in the Badlands who can translate the paladin\'s journal.',
    '人选是加卡尔（荒芜之地 - 卡加斯 2,46）；把项链借给他即可完成翻译。':
        "The person is Jarkal Mossmeld (Badlands - Kargath 2,46); lending him the necklace completes the translation.",
    '从奥达曼取回项链上的红宝石、黄宝石、蓝宝石和能量源，交给卡加斯的加卡尔。红宝石在暗铁矮人设防区，黄宝石在石腭怪区的一只瓮里，蓝宝石在石腭怪首领格瑞姆洛克手中，能量源在奥达曼最强的生物身上。':
        "Retrieve the necklace's ruby, topaz, sapphire and power source from Uldaman and bring them to Jarkal Mossmeld in Kargath. The ruby is in the Dark Iron defense area, the topaz in an urn in the trogg area, the sapphire held by the trogg leader Grimlok, and the power source on the strongest creature of Uldaman.",
    '宝石位置： 显眼的石罐、 暗影熔炉地窖、 格瑞姆洛克。开暗影熔炉地窖会刷怪，注意。':
        'Gem locations: Conspicuous Urn, Shadowforge Vault, Grimlok. Opening the Shadowforge Vault spawns mobs — be careful.',
    '在奥达曼查明红宝石、蓝宝石、黄宝石的下落，用塔瓦斯德给的占卜之瓶向他反馈。':
        "Find out where the ruby, sapphire and topaz are in Uldaman, then report back to Talvash using the divining vial he gave you.",
    '宝石分别在副本内的显眼石罐、暗影熔炉地窖，以及格瑞姆洛克身上。注意：打开暗影熔炉地窖会刷怪。':
        'The gems are respectively in the Conspicuous Urn and the Shadowforge Vault inside the dungeon, and on Grimlok. Note: opening the Shadowforge Vault spawns mobs.',
    '向石头守护者了解古代知识，随后激活诺甘农圆盘；再把迷你版诺甘农圆盘带回铁炉堡探险者协会。':
        "Learn ancient knowledge from the Stone Watcher, then activate the Norgannon Disc; bring the Miniaturized Disc of Norgannon back to the Explorer's League in Ironforge.",
    '白金圆盘': 'The Platinum Disc',
    '把探水棒交给加基森的首席工程师沙克斯·比格维兹。':
        'Bring the Dowsing Rod to Chief Engineer Bilgewhizzle in Gadgetzan.',
    '探水棒来自布莱中士。要先把神庙的百人斩事件打完、击败布莱中士才能拿到。':
        'The Dowsing Rod comes from Sergeant Bly. You must first finish the gauntlet event in the temple and defeat Sergeant Bly to get it.',
    '把加兹瑞拉的鳞片交给闪光平原的维兹尔·铜栓。':
        "Bring Gahz'rilla's scale to Wizzle Brassbolts on the Shimmering Flats.",
    '前置可从科罗莫特·钢尺（铁炉堡 - 侏儒区 68,46）接，但非必需。在副本内的斗兽场敲锣即可召唤加兹瑞拉——无限服已不需要祖尔法拉克之槌。':
        "The prerequisite can be taken from Klockmort Spannerspan (Ironforge - Tinker Town 68,46), but it is optional. Ring the gong in the dungeon's arena to summon Gahz'rilla — the Forever server no longer requires the Mallet of Zul'Farrak.",
    '把深渊皇冠交给尘泥沼泽的塔贝萨。':
        'Bring the Crown of the Deeps to Tabetha in Dustwallow Marsh.',
    '前置来自彬克（铁炉堡 25,8）。皇冠由水占师维蕾萨掉落。':
        "The prerequisite comes from Bink (Ironforge 25,8). The crown drops from Hydromancer Velratha.",
    '给加基森的特兰雷克带去 5 个完整的圣甲虫壳。':
        'Bring 5 intact Scarab Shells to Tran\'rek in Gadgetzan.',
    '前置始于克拉兹克（荆棘谷 - 藏宝海湾 25,77）。所有圣甲虫都掉壳， 一带数量最集中。':
        'The chain starts with Krazek (Stranglethorn Vale - Booty Bay 25,77). All scarabs drop the shells; the scarab swarm area has the highest concentration.',
    '加德林大师': 'Master Gadrin',
    '阅读塞卡石板，弄清枯木巨魔蜘蛛之神的名字，回加德林大师处汇报。':
        'Read the Seca Stone Tablet to learn the name of the spider god of the Witherbark trolls, then report back to Master Gadrin.',
    '任务始于辛特兰巨魔村庄的毒液瓶系列。石板在副本内。':
        'The quest starts from the Venom Vial chain in the troll village of the Hinterlands. The tablet is inside the dungeon.',
    '把耐克鲁姆的徽章交给诅咒之地的萨迪斯·格希德。':
        "Bring Nekrum's medallion to Thadius Grimshade in the Blasted Lands.",
    '系列始于狮鹫管理员沙拉克·鹰斧（辛特兰 - 蛮锤城堡 9,44）。耐克鲁姆在副本内。':
        'The chain starts with Gryphon Master Talonaxe (The Hinterlands - Wildhammer Keep 9,44). Nekrum is inside the dungeon.',
    '收集 20 瓶巨魔调和剂，交给加基森的特伦顿·轻锤。':
        'Collect 20 bottles of Troll Temper and bring them to Trenton Lighthammer in Gadgetzan.',
    '所有巨魔都可能掉调和剂。': 'All the trolls can drop the temper.',
    '把第一、第二块摩沙鲁石板交给塔纳利斯的叶基亚。':
        "Bring the first and second Mosh'aru Tablets to Yeh'kinya in Tanaris.",
    '前置同样在叶基亚处接。石板分别由殉教者塞卡和水占师维蕾萨掉落。':
        "The prerequisite is also taken from Yeh'kinya. The tablets drop from Martyr Seka and Hydromancer Velratha respectively.",
    '从玛拉顿收集 10 块暗影残片，交给奥格瑞玛的尤塞尔奈。':
        'Collect 10 Shadow Shards from Maraudon and bring them to Uthel\'nay in Orgrimmar.',
    '残片出自副本外的暗影碎片巡游者和暗影碎片击碎者。':
        'The shards come from the Shadow Shard Prowlers and Shadow Shard Splitters outside the dungeon.',
    '从玛拉顿收集 10 块暗影残片，交给尘泥沼泽塞拉摩岛的大法师特沃什。':
        'Collect 10 Shadow Shards from Maraudon and bring them to Archmage Tervosh on Theramore Isle in Dustwallow Marsh.',
    '阅读《贱民的指引》，从玛拉顿取回联合坠饰，交给凄凉之地南部的半人马贱民。':
        'Read "The Pariah\'s Instructions", retrieve the Uniting Charm from Maraudon, and bring it to the Centaur Pariah in southern Desolace.',
    '《贱民的指引》里提到 5 个可汗。':
        '"The Pariah\'s Instructions" mentions 5 khans.',
    '替凄凉之地的维洛收集 25 个瑟莱德丝水晶雕像。':
        'Collect 25 Theradras Crystal Statues for Willow of Desolace.',
    '玛拉顿里大多数敌人都会掉雕像。':
        'Most enemies in Maraudon drop the statues.',
    '用天蓝水瓶在玛拉顿的橙色水晶池装水，浇在维利斯塔姆藤蔓上引出堕落的诺克赛恩幼体；治疗 8 株植物并杀掉幼体，回葬影村向瓦克·战痕复命。':
        "Fill the Azure Vial at the orange crystal pools of Maraudon and pour it on the Vile Stem vines to draw out the Corrupted Noxxion Scions; heal 8 plants and kill the scion, then report back to Vark Battlescar in Shadowprey Village.",
    '任意橙色水池都能装水；藤蔓长在橙色或紫色区域。':
        'Any orange pool can be used to fill the vial; the vines grow in the orange or purple areas.',
    '用天蓝水瓶在玛拉顿的橙色水晶池装水，浇在维利斯塔姆藤蔓上引出堕落的诺克赛恩幼体；治疗 8 株植物并杀掉幼体，回尼耶尔前哨站向塔琳德莉亚复命。':
        "Fill the Azure Vial at the orange crystal pools of Maraudon and pour it on the Vile Stem vines to draw out the Corrupted Noxxion Scions; heal 8 plants and kill the scion, then report back to Talendria at Nijel's Point.",
    '找回塞雷布拉斯节杖的两个部件——塞雷布拉斯魔棒和塞雷布拉斯钻石——然后设法与塞雷布拉斯对话。':
        "Recover the two parts of the Scepter of Celebras — Celebras's Wand and the Celebras Diamond — then find a way to speak with Celebras.",
    '凯雯德拉就在进副本前的橙色区域起点。魔棒来自诺克塞恩，钻石来自维利塔恩。塞雷布拉斯在副本内，要先击败他才能对话。':
        "Cavindra is right at the start of the orange area before the dungeon. The wand comes from Noxxion, the diamond from Vel'tarn. Celebras is inside the dungeon — you must defeat him before you can speak with him.",
    '帮助赎罪的塞雷布拉斯制作塞雷布拉斯节杖，仪式完成后与他再谈一次。':
        'Help Celebras the Redeemed craft the Scepter of Celebras; talk with him once more after the ritual is complete.',
    '节杖由塞雷布拉斯亲手制作；仪式结束后与他对话即可。':
        'The scepter is crafted by Celebras himself; just talk to him after the ritual.',
    '杀死瑟莱德丝公主，回凄凉之地葬影村附近向瑟琳德拉复命。':
        'Kill Princess Theradras, then report back to Selendra near Shadowprey Village in Desolace.',
    '瑟莱德丝公主在副本内。': 'Princess Theradras is inside the dungeon.',
    '杀死瑟莱德丝公主，回凄凉之地尼耶尔前哨站向守护者玛兰迪斯复命。':
        "Kill Princess Theradras, then report back to Keeper Marandis at Nijel's Point in Desolace.",
    '到月光林地找到雷姆洛斯，把生命之种交给他。':
        'Find Remulos in Moonglade and give him the Seed of Life.',
    '杀死公主后扎尔塔的灵魂会出现。雷姆洛斯在月光林地 - 雷姆洛斯神殿（36,41）。':
        "Zaetar's spirit appears after the princess is killed. Remulos is at Moonglade - Temple of Remulos (36,41).",
    '收集 20 个哈卡神像，交给斯通纳德的费泽鲁尔。':
        "Collect 20 Hakkari idols and bring them to Fel'zerul in Stonard.",
    '神庙内所有敌人都会掉神像。':
        'All enemies inside the temple drop the idols.',
    '带回迦玛兰的头，交给辛特兰的阿塔莱流放者。':
        "Bring back the head of Jammal'an and give it to the Atal'ai Exile in the Hinterlands.",
    '迦玛兰在副本内。': "Jammal'an is inside the dungeon.",
    '把装满的哈卡之卵交给塔纳利斯的叶基亚。':
        "Bring the filled Hakkar egg to Yeh'kinya in Tanaris.",
    '系列始于《尖啸者的灵魂》（同在本副本接）。到副本内的祭坛使用哈卡之卵触发事件；刷出的敌人部分掉哈卡莱之血，用它熄灭不灭火焰，全部熄灭后哈卡化身降临。':
        "The chain starts with \"The Souls of the Screechers\" (taken at this same dungeon). Use the Hakkar egg at the altar inside the dungeon to trigger the event; some of the spawned enemies drop Hakkari Blood — use it to douse the Eternal Flames. When all are out, the Avatar of Hakkar descends.",
    '为暴风城的布罗哈恩·铁桶收集 10 块阿塔莱石板。':
        "Collect 10 Atal'ai Tablets for Brohann Caskbelly in Stormwind City.",
    '在本处接前置。石板在神庙内外随处可见。':
        'Take the prerequisite here. The tablets are found everywhere inside and outside the temple.',
    '到塔纳利斯找到玛尔冯·瑞文斯克。':
        'Find Marvon Rivetseeker in Tanaris.',
    '位置 52,45。': 'Location 52,45.',
    '进入悲伤沼泽的沉没神庙，找到哈卡祭坛。':
        'Enter the Sunken Temple in the Swamp of Sorrows and find the Altar of Hakkar.',
    '祭坛在图中。': 'The altar is on the map.',
    '进入沉没神庙，破解雕像群隐藏的秘密。':
        'Enter the Sunken Temple and solve the hidden secret of the statue cluster.',
    '雕像群在副本内，按顺序逐个开启。':
        'The statue cluster is inside the dungeon; activate them one by one in order.',
    '收集 5 份阿塔莱之雾，回安戈洛环形山向穆尔金复命。':
        "Collect 5 Atal'ai Mists and report back to Mugen in Un'Goro Crater.",
    '前置《穆尔金和拉瑞安》始于穆尔金（安戈洛环形山 - 马绍尔营地 42,9）。神庙深渊潜伏者、黑暗虫、融合软泥怪都掉。':
        "The prerequisite \"Mugen and Larion\" starts with Mugen (Un'Goro Crater - Marshall's Refuge 42,9). The temple's Deep Lurkers, Dark Creepers and Fused Oozes all drop it.",
    '收集 5 份阿塔莱之雾，送到马绍尔营地的拉瑞安那里。':
        "Collect 5 Atal'ai Mists and deliver them to Larion at Marshall's Refuge.",
    '前置《拉瑞安和穆尔金》始于拉瑞安（安戈洛环形山 45,8）。神庙深渊潜伏者、黑暗虫、软泥怪都掉。':
        "The prerequisite \"Larion and Mugen\" starts with Larion (Un'Goro Crater 45,8). The temple's Deep Lurkers, Dark Creepers and oozes all drop it.",
    '伊兰尼库斯精华掉落自（伊兰尼库斯的阴影）':
        'The Essence of Eranikus drops from (the Shade of Eranikus)',
    '把伊兰尼库斯精华放进沉没神庙里他巢穴旁的精华之泉。':
        'Place the Essence of Eranikus into the Essence Font beside his lair in the Sunken Temple.',
    '精华由伊兰尼库斯的阴影掉落，精华之泉就在他旁边。':
        'The essence drops from the Shade of Eranikus; the Essence Font is right beside him.',
    '把摩弗拉斯的牙齿交给艾萨拉的奥汀克——他住在埃达拉斯废墟东北的悬崖顶上。':
        'Bring the tooth of Morphras to Ointink of Azshara — he lives on the cliff top northeast of the Edalas ruins.',
    '猎人职业任务。摩弗拉斯在副本内。':
        'Hunter class quest. Morphras is inside the dungeon.',
    '把碧蓝钥匙交给乔拉齐·拉文霍德公爵。':
        'Bring the Cerulean Key to Duke Jorach Ravenholdt.',
    '盗贼职业任务。钥匙由摩弗拉斯掉落。乔拉齐·拉文霍德公爵在奥特兰克山谷 - 拉文霍德（86,79）。':
        'Rogue class quest. The key drops from Morphras. Duke Jorach Ravenholdt is at Alterac Valley - Ravenholdt Manor (86,79).',
    '大法师克希雷姆，摩弗拉斯': 'Archmage Xylem, Morphras',
    '从摩弗拉斯身上取回奥术碎片，回大法师克希雷姆处复命。':
        'Retrieve the Arcane Shard from Morphras and report back to Archmage Xylem.',
    '法师职业任务。摩弗拉斯在副本内。':
        'Mage class quest. Morphras is inside the dungeon.',
    '前往沉没的阿塔哈卡神庙杀死绿龙摩弗拉斯，把他的血液交给费伍德森林的格雷塔·苔蹄。':
        "Go to the Sunken Temple of Atal'Hakkar, kill the green dragon Morphras, and bring his blood to Greta Mosshoof in Felwood.",
    '牧师职业任务。摩弗拉斯在副本内。格雷塔·苔蹄在费伍德森林 - 翡翠圣地（51,82）。':
        "Priest class quest. Morphras is inside the dungeon. Greta Mosshoof is at Felwood - Emerald Sanctuary (51,82).",
    '把巫毒羽毛交给捕风者巴斯拉。':
        'Bring the Voodoo Feathers to Basha Windcaller.',
    '萨满职业任务。6 个小巨魔每只掉一根。':
        'Shaman class quest. Each of the 6 lesser trolls drops one.',
    '把巫毒羽毛带给阿什拉姆·瓦罗菲斯特。':
        'Bring the Voodoo Feathers to Ashlam Valorfist.',
    '圣骑士职业任务。6 个小巨魔每只掉一根。':
        'Paladin class quest. Each of the 6 lesser trolls drops one.',
    '到沉没的神庙从巨魔身上收集 6 支巫毒羽毛。':
        'Collect 6 Voodoo Feathers from the trolls in the Sunken Temple.',
    '术士职业任务。6 个小巨魔每只掉一根。':
        'Warlock class quest. Each of the 6 lesser trolls drops one.',
    '把从沉没神庙巨魔身上得到的巫毒羽毛交给部落英雄的灵魂。':
        'Bring the Voodoo Feathers taken from the trolls of the Sunken Temple to the Spirit of the Fallen Hero.',
    '战士职业任务。6 个小巨魔每只掉一根。':
        'Warrior class quest. Each of the 6 lesser trolls drops one.',
    '从沉没神庙底部的守卫身上取得一些腐烂藤蔓，交给托尔瓦·寻路者。':
        'Take some Rotting Vines from the guards at the bottom of the Sunken Temple and bring them to Torwa Pathfinder.',
    '鬼魂之杯的塞娜尼·雷心要你找齐他要的材料。':
        'Senani Thunderheart of the Chalice of Spirits wants you to gather the materials he needs.',
    '采矿 230 以上才能接；做完后学会熔炼黑铁矿石。材料：2 个 [红宝石]、20 个 [金锭]、10 个 [真银锭]。之后带 [黑铁矿石] 到黑熔炉即可熔炼。':
        'Requires Mining 230 to take; after completing it you learn Smelt Dark Iron. Materials: 2 [Star Rubies], 20 [Gold Bars], 10 [Truesilver Bars]. Afterwards bring [Dark Iron Ore] to the Black Forge to smelt it.',
    '击杀弗诺斯·达克维尔夺回战锤「铁胆」，再把铁胆之锤放到索瑞森神殿弗兰克罗恩·铸铁的雕像上。':
        'Kill Vornus Darkvale to reclaim the warhammer "Ironheart", then place the Hammer of Ironheart on the statue of Franclorn Forgewright in the Thaurissan shrine.',

    # ---- 洛丹伦废墟（新增任务注释）----
    '起始在副本外（银松森林 44.6,42.8）；交任务也找塔比莎·织心本人，进本前先接、出本后顺路交。':
        'Starts outside the dungeon (Silverpine Forest 44.6,42.8); the turn-in is with Tabitha Heartweaver herself, so pick it up before heading in and hand it in on the way back.',
    '起始在副本内（拉斯玛尔附近拾取「血染的信件」）；交任务要回暴风城找孤儿监护员奈丁加尔，跨地图回程，别漏交。':
        'Starts inside the dungeon (loot the "Bloodstained Letter" near Rath\'Mael); the turn-in is back in Stormwind City with Orphan Matron Nightingale — a cross-zone trip, so do not forget it.',
    '起始在副本外（幽暗城 · 炼金房 57.8,89.8）；交任务找同一个 NPC，出本后回炼金房交。':
        'Starts outside the dungeon (Undercity - The Apothecarium 57.8,89.8); the turn-in is the same NPC, so return to the Apothecarium after the run.',
    '起始在副本外（提瑞斯法林地 · 布瑞尔 65.2,60.2）；目标就是尾王拉斯玛尔，打完出本回布瑞尔交。':
        "Starts outside the dungeon (Tirisfal Glades - Brill 65.2,60.2); the target is the final boss Rath'Mael, so hand it in back at Brill once you are done.",
    '起始在副本内（「洛丹伦纹章」在副本里有多处刷新点，拾取即开启）；交任务要回暴风城找德娜·肯尼迪。':
        'Starts inside the dungeon (the "Crest of Lordaeron" spawns at several points in the instance — looting one starts the quest); the turn-in is back in Stormwind City with Lady Dena Kennedy.',
    '起始在副本内（「染血的徽记」由副本里的亡灵小怪掉落，拾取即开启）；要凑齐 10 枚，清怪时留意；交任务回暴风城找马库斯·乔纳森将军。': 'Starts inside the dungeon (the "Bloodied Insignia" drops from the undead trash — looting one starts the quest); you need 10 of them, so keep an eye out while clearing; the turn-in is back in Stormwind City with General Marcus Jonathan.',
    '起始在副本内（「洛丹伦纹章」在副本里有多处刷新点，拾取即开启）；交任务回幽暗城找奥兰·斯内克威瑟。':
        'Starts inside the dungeon (the "Crest of Lordaeron" spawns at several points in the instance — looting one starts the quest); the turn-in is back in Undercity with Oran Snakewrithe.',
    '起始在副本外（幽暗城 · 炼金房 47.0,72.6）；毒株要从 boss 枯牙身上取，属必经 boss，不用额外绕路。':
        'Starts outside the dungeon (Undercity - The Apothecarium 47.0,72.6); the strain is taken from the boss Witherfang, which you have to kill anyway — no detour needed.',
    '起始在副本门口的图曼上尉（联盟军需官，对部落敌对）；目标要取男爵的头颅，打完男爵别急着走；交任务也找他本人。':
        "Starts at Captain Truman just inside the dungeon entrance (an Alliance quartermaster, hostile to the Horde); the objective is the Head of the Baron, so don't leave right after The Baron dies; the turn-in is with him as well.",
    '起始在副本内（男爵掉落的「憎恶的头颅」，拾取即开启）；交任务回幽暗城找大药剂师法拉尼尔。':
        'Starts inside the dungeon (the "Abomination\'s Head" dropped by The Baron — looting it starts the quest); the turn-in is back in Undercity with Master Apothecary Faranell.',
}



