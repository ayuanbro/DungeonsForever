# -*- coding: utf-8 -*-
"""enUS 数据层翻译表（任务侧第二段）：BRD/DM/Scholo/Strat/LBRS/UBRS 自由文本。
错译直接改本表重跑 gen_enus_data.py，禁手改产物。
"""

QUESTS2 = {
    # 2026-10-04 挖掘场：Wowhead 任务区新情报 + 任务页高分评论（玩家实测）并入注释
    '戴温随勘探队进了挖掘场，之后能在副本内他的遗体上接到后续任务。◎ 发布者在湖畔镇的马厩里——从飞行点过桥后左手边（玩家实测）。':
        'Daywin went into the excavation site with the prospecting crew; his body can be found inside the dungeon to pick up the follow-up quest. ◎ The quest giver is in the Lakeshire stables — on the left as you cross the bridge from the flight master (player-reported).',
    '迅猛龙皮由挖掘场的迅猛龙类掉落；前置是哈洛兰的「幼鳄鱼皮」，无需先做「日常供货」（玩家实测，与站点表格口径矛盾）。': 'Raptor hides drop from the raptors inside the dungeon. The prerequisite is Halloran\'s "Young Crocolisk Skin"; "Daily Delivery" is NOT required (player-reported, contradicts the site table).',
    '可怕的根核由副本内的高地惊魂掉落。◎ 前置：先完成菲茨西蒙斯大副的湿地四步链——绿色守卫者、践踏之足、火之禁忌、大地上的水泡，之后才会给接本任务。': 'The Dreadful Root Core drops from Highland Terrors inside the dungeon. ◎ Prerequisite: finish First Mate Fitzsimmons\' four-step Wetlands chain — The Greenwarden, Tramping Paws, Fire Taboo, Blisters on The Land — before this quest is offered.',
    '链从灰谷蓝纳（35.0,48.6）的「寻找凯特林」开始。': 'The chain starts with "Seeking Caitlin" from Pethnant the Silent in Ashenvale (35.0, 48.6).',
    '肉由副本内迅猛龙类掉落；发布者=烹饪训练师博尔斯坦（奥格瑞玛暗巷区，57.5,53.4）。': 'The meat drops from raptors inside the dungeon. Giver: cooking trainer Borstan (The Drag, Orgrimmar, 57.5, 53.4).',
    '龙喉急件由副本内龙喉单位掉落；发布者藏在入口区域旁的山丘里（已确认）。◎ 有玩家提示可先在落锤镇楼梯下的兽人（疑似扎鲁克）处接前置，待核实。': 'Dragonmaw Dispatch drops from Dragonmaw units inside the dungeon. The giver hides in the hills by the entrance area (confirmed). ◎ A player reports a possible prerequisite from the orc at the bottom of the stairs in Hammerfall (likely Zaruk) — unverified.',
    '打完尾王遗迹守卫者后拾取泰坦圣物，拾取即开启本任务；多名玩家证实（10/2）：上交时泰坦圣物不会归还。': 'Loot the Titan Relic from the last boss, the Ruins Guardian, to start this quest. Multiple players confirm (Oct 2): the relic is NOT returned on turn-in.',
    '「长者知识」的后续；圣物由尾王遗迹守卫者掉落。◎ beta 已知 bug（10/2-10/3 实测）：上交「长者知识」时圣物被吞、本任务无法完成，弃任务后也无法重接。': 'Follow-up to "Elder Knowledge"; the relic drops from the last boss, the Ruins Guardian. ◎ Known beta bug (Oct 2-3): turning in "Elder Knowledge" consumes the relic, making this quest impossible to complete — and it cannot be re-picked after abandoning.',
    '「运送失落的圣物」的后续，在勘察员维尔加处接续；圣物由尾王遗迹守卫者掉落。◎ 同系 bug（10/1-10/2 实测）：上交前一步丢失泰坦圣物，导致无法交付。': 'Follow-up to "Lost Relic Carry", continue at Prospector Whelgar; the relic drops from the last boss, the Ruins Guardian. ◎ Same bug family (Oct 1-2): the Titan Relic is lost on the previous turn-in, preventing completion.',
    '博尔斯坦':
        'Borstan',
    '奥格瑞玛 - 暗巷区 57.5,53.4':
        'Orgrimmar - The Drag 57.5,53.4',
    '湿地 - 挖掘场入口旁的山丘':
        'Wetlands - hills by the dungeon entrance',
    '到黑石山的采石场击杀征服者派隆，回桑德哈特处汇报。':
        'Kill Overlord Pyron at the quarry of Blackrock Mountain, then report back to Thunderheart.',
    '派隆是副本入口外的一只火元素精英。':
        'Pyron is a fire elemental elite just outside the dungeon entrance.',
    '进入黑石深渊找到并击杀伊森迪奥斯，向桑德哈特汇报。':
        'Enter Blackrock Depths, find and kill Incendis, then report back to Thunderheart.',
    '前置从塞娜尼·雷心处接。伊森迪奥斯在副本内。':
        'The prerequisite is taken from Senani Thunderheart. Incendis is inside the dungeon.',
    '进入黑石深渊找到指挥官哥沙克——草图上画着铁栏后的兽人，去类似监狱的地方找。':
        "Enter Blackrock Depths and find Commander Gor'shak — the sketch shows an orc behind iron bars, so look somewhere like a prison.",
    '前置来自桑德哈特（荒芜之地 - 卡加斯 3,48）；派隆就在副本入口前。哥沙克在副本内。监狱钥匙由审讯官格斯塔恩掉落；与他对话开启下一阶段时会刷怪。':
        "The prerequisite comes from Thunderheart (Badlands - Kargath 3,48); Pyron is right before the dungeon entrance. Gor'shak is inside the dungeon. The jail key drops from Interrogator Gerstahn; talking to him to open the next stage spawns mobs.",
    '击杀达格兰·索瑞森大帝，把铁炉堡公主茉艾拉·铜须从诅咒中解救出来。':
        'Kill Emperor Dagran Thaurissan and free Princess Moira Bronzebeard of Ironforge from her enchantment.',
    '先与卡兰·巨锤和萨尔交谈获得任务。达格兰在副本内。公主会治疗达格兰——千万别杀公主，记得打断她的治疗！':
        "Talk with Kharan Mustershammer and Thrall first to get the quest. Dagran is inside the dungeon. The princess heals Dagran — never kill the princess, remember to interrupt her healing!",
    '替军官高图斯清剿黑石深渊：15 个铁怒卫士、10 个铁怒狱卒、5 个铁怒步兵，完成后回去复命。':
        'Clear Blackrock Depths for Warlord Goretooth: kill 15 Rageforge Guards, 10 Rageforge Jailers and 5 Rageforge Footmen, then report back.',
    '这些矮人集中在黑石深渊前半段。高图斯在卡加斯瞭望塔顶（荒芜之地 5,47）。':
        'These dwarves are concentrated in the first half of Blackrock Depths. Goretooth is at the top of the Kargath watchtower (Badlands 5,47).',
    '把雷布里的头颅交给燃烧平原的尤卡·斯库比格特。':
        "Bring Ribbly's head to Yuka Screwspigot in the Burning Steppes.",
    '任务可直接接，前置从尤卡·斯库比格特（塔纳利斯 - 热砂港 67,23）处接。雷布里在副本内。':
        'The quest can be taken directly; the prerequisite comes from Yuka Screwspigot (Tanaris - Steamwheedle Port 67,23). Ribbly is inside the dungeon.',
    '击杀征服者派隆，向加琳达复命。':
        'Kill Overlord Pyron and report back to Jalinda Sprig.',
    '派隆是副本入口外的火元素精英':
        'Pyron is a fire elemental elite just outside the dungeon entrance.',
    '进入黑石深渊找到并击杀伊森迪奥斯。':
        'Enter Blackrock Depths, find and kill Incendis.',
    '前置在加琳达处接。伊森迪奥斯在副本内。':
        'The prerequisite is taken from Jalinda Sprig. Incendis is inside the dungeon.',
    '到黑石深渊收集 10 份元素精华——作战傀儡、傀儡制造者身上找找，薇薇安·拉格雷还提到了元素生物……':
        'Collect 10 elemental essences in Blackrock Depths — look on the war golems and golem makers; Vivian Lagrave also mentioned elementals...',
    '前置来自桑德哈特（荒芜之地 - 卡加斯 3,48）；派隆就在副本入口前。所有元素生物都可能掉精华。':
        'The prerequisite comes from Thunderheart (Badlands - Kargath 3,48); Pyron is right before the dungeon entrance. All elementals can drop the essences.',
    '替高图斯军阀清剿黑石深渊：10 个铁怒医师、10 个铁怒士兵、10 个铁怒军官，完成后回去复命。':
        'Clear Blackrock Depths for Warlord Goretooth: kill 10 Rageforge Medics, 10 Rageforge Soldiers and 10 Rageforge Officers, then report back.',
    '铁怒矮人在贝尔加附近。高图斯在卡加斯瞭望塔顶（荒芜之地 5,47）；系列始于雷克斯洛特（荒芜之地 - 卡加斯 5,47）。格拉克·洛克鲁布在燃烧平原（38,35）：把他打到 50% 血以下并绑定后开始护送（精英）。':
        'The Rageforge dwarves are near Belga. Goretooth is at the top of the Kargath watchtower (Badlands 5,47); the chain starts with Rexlot (Badlands - Kargath 5,47). Grark Lorkrub is in the Burning Steppes (38,35): bring him below 50% health and bind him to start the escort (elite).',
    '把山脉之心交给燃烧平原的麦克斯沃特·尤博格林。':
        'Bring the Heart of the Mountain to Maxwort Uberglint in the Burning Steppes.',
    '山脉之心在黑色宝库的宝箱里。要先清完黑色宝库的所有小宝箱、击败出现的 首领 才能拿到钥匙。':
        'The Heart of the Mountain is in the chest of the Black Vault. You must first clear all the small chests of the Black Vault and defeat the boss that appears to get the key.',
    '把遗失的雷酒秘方带回卡拉诺斯交给拉格纳·雷酒。':
        'Bring the Lost Thunderbrew Recipe back to Ragnar Thunderbrew in Kharanos.',
    '前置来自恩诺哈尔·雷酒（诅咒之地 - 守望堡 61,18）。摧毁雷霆啤酒桶会刷出守卫，秘方在其中一名守卫身上。':
        'The prerequisite comes from Ennohar Thunderbrew (Blasted Lands - Nethergarde Keep 61,18). Destroying the Thunderbrew kegs spawns guards; the recipe is on one of them.',
    '把遗失的雷酒秘方交给卡加斯的薇薇安·拉格雷。':
        'Bring the Lost Thunderbrew Recipe to Shadowmage Vivian Lagrave in Kargath.',
    '前置由药剂师金格给予（幽暗城 - 炼金房 50,68）。砸破酒桶刷出的守卫中有一人带着秘方。':
        'The prerequisite is given by Apothecary Ginge (Undercity - The Apothecarium 50,68). One of the guards spawned by smashing the kegs carries the recipe.',
    '把 4 份格罗姆之血、10 块巨型银矿和装满水的娜玛拉之瓶交给黑石深渊的娜玛拉小姐。':
        "Bring 4 Gromsbloods, 10 Large Silver Veins and Nagmara's filled bottle to Mistress Nagmara in Blackrock Depths.",
    '巨型银矿打艾萨拉的巨人；格罗姆之血可请草药学玩家帮忙；瓶子在安戈洛环形山葛拉卡温泉（31,50）装水。交付后可直接走后门，不必再杀法拉克斯。':
        "Mine the Large Silver Veins from the giants of Azshara; ask a herbalist player for the Gromsblood; fill the bottle at the Golakka Hot Springs in Un'Goro Crater (31,50). After turning in you can take the back door directly — no need to kill Farrax again.",
    '到黑石深渊找 20 个黑铁挎包，回奥拉留斯处复命。':
        'Find 20 Dark Iron satchels in Blackrock Depths, then report back to Oralius.',
    '所有黑铁矮人都可能掉挎包。':
        'All Dark Iron dwarves can drop the satchels.',
    '到黑石深渊找到卡兰·巨锤——国王说他在那里看守囚犯，去监狱附近找。':
        'Find Kharan Mustershammer in Blackrock Depths — the king says he is guarding prisoners there, so look near the jail.',
    '前置始于皇家历史学家阿克瑟努斯（铁炉堡 38,55）。卡兰·巨锤在副本内。':
        'The chain starts with Royal Historian Archesonus (Ironforge 38,55). Kharan Mustershammer is inside the dungeon.',
    '重返黑石深渊，从达格兰·索瑞森大帝手中救出铁炉堡公主茉艾拉·铜须。':
        'Return to Blackrock Depths and rescue Princess Moira Bronzebeard of Ironforge from Emperor Dagran Thaurissan.',
    '公主在副本内。战斗中她会治疗达格兰，尽量打断，但绝不能让她死，否则任务失败。救出后还要回铁炉堡向麦格尼·铜须复命。':
        'The princess is inside the dungeon. During the fight she heals Dagran — interrupt it when you can, but never let her die or the quest fails. After the rescue, return to Magni Bronzebeard in Ironforge to report.',
    '进入黑石深渊击杀贝尔加，用特殊黑龙皮从尸体上采集烈焰精华，交给塞勒斯·萨雷芬图斯。':
        'Enter Blackrock Depths and kill Belga, use the special black dragonhide to harvest the Fire Essence from the corpse, and bring it to Cyrus Therepentous.',
    '系列始于卡拉然·温布雷（灼热峡谷 39,38）。贝尔加在副本内。':
        'The chain starts with Karan Ravenwind (Searing Gorge 39,38). Belga is inside the dungeon.',
    '击杀傀儡统帅阿格曼奇并把头交给鲁特维尔，同时从护卫它的傀儡身上收集 10 块完整的元素核心。':
        'Kill Puppetmaster Aggemancur and bring his head to Lotwil Veriatus; also collect 10 Intact Elemental Cores from the golems guarding him.',
    '前置来自圣者塞朵拉·穆瓦丹尼（荒芜之地 - 卡加斯 3,47）。阿格曼奇在副本内。':
        'The prerequisite comes from Sage Sedola Muwadanni (Badlands - Kargath 3,47). Aggemancur is inside the dungeon.',
    '进入黑石深渊击杀安格弗将军，完成后向军官高图斯复命。':
        'Enter Blackrock Depths and kill General Angerforge, then report back to Warlord Goretooth.',
    '安格弗将军在副本内。注意：他的生命低于 30% 时会召唤增援！':
        'General Angerforge is inside the dungeon. Note: he summons reinforcements below 30% health!',
    '进入黑石深渊，在通往熔火之心的传送门附近找一块熔火碎片，带回黑石山交给洛索斯·天痕。':
        'Enter Blackrock Depths, find a Molten Fragment near the portal to the Molten Core, and bring it back to Lothos Riftwaker at Blackrock Mountain.',
    '完成后即可用洛索斯·天痕旁的传送石直接进入熔火之心。熔火碎片在副本内。':
        'After completing this you can use the teleport stone beside Lothos Riftwaker to enter the Molten Core directly. The fragment is inside the dungeon.',
    '前往黑石深渊竞技场，在被裁决者格里斯通宣判时把挑衅旗帜插到中央；杀死瑟尔伦和他的战士们，带着第一块瓦萨拉克护符回东瘟疫之地交给安希恩·哈莫。':
        'Go to the Blackrock Depths arena and plant the taunting banner in the center while Adjudicator Griston passes judgment; kill Thalren and his warriors, then bring the first Vasalak Amulet back to Anhein Hamo in the Eastern Plaguelands.',
    '后续任务因职业而异。': 'The follow-up quest differs by class.',
    '如果愿意接受萨弗隆的设计图，就把瑟银兄弟会契约交给罗克图斯·暗契。':
        'If you want the Sulfuron designs, hand the Thorium Brotherhood Covenant to Rocktus Darkpact.',
    '签契约需要萨弗隆铁锭——熔火之心的焚化者古雷曼格掉落。':
        'Signing the covenant requires a Sulfuron Ingot — dropped by Golemagg the Incinerator of the Molten Core.',
    '掉落自科林·烈酒': 'Drops from Coren Direbrew',
    "把科林的烈酒交给铁炉堡附近美酒节营地的埃菲库格·铁桶。":
        "Bring Coren's Brew to Epikug Ironkeg at the Brewfest camp near Ironforge.",
    '仅美酒节期间可接，任务物品每角色限取一次。埃菲库格·铁桶在美酒节营地（丹莫罗 47,39）。':
        'Available only during Brewfest; the quest item can be taken once per character. Epikug Ironkeg is at the Brewfest camp (Dun Morogh 47,39).',
    '到厄运之槌找到小鬼普希林，用任何手段拿回埃斯托尔迪的咒术之书。':
        "Find the imp Pusillin in Dire Maul and retrieve Azj'Tordin's grimoire by any means.",
    '普希林在厄运之槌东；一对话就跑，追一段距离后它会停下并可以被攻击。它还掉月牙钥匙——厄运之槌北区和西区的门钥匙。':
        'Pusillin is in Dire Maul: East; it runs as soon as you talk to it — chase it a stretch and it will stop and become attackable. It also drops the Crescent Key — the door key for Dire Maul North and West.',
    '把蕾瑟塔蒂丝的网交给菲拉斯羽月要塞的拉托尼库斯·月矛。':
        "Bring Lethtendris's Web to Latronicus Moonspear at Feathermoon Stronghold in Feralas.",
    '蕾瑟塔蒂丝在厄运之槌东。前置可从铁炉堡的信使考雷·落锤处接。':
        'Lethtendris is in Dire Maul: East. The prerequisite can be taken from the courier Koley Foghammer in Ironforge.',
    '把蕾瑟塔蒂丝的网交给菲拉斯莫沙彻营地的塔罗·刺蹄。':
        "Bring Lethtendris's Web to Talo Thornhoof at Camp Mojache in Feralas.",
    '蕾瑟塔蒂丝在厄运之槌东。前置接自奥格瑞玛的公告员高拉克。':
        'Lethtendris is in Dire Maul: East. The prerequisite is taken from Herald Golarak in Orgrimmar.',
    '迦罗娜：潜行与诡计研究': 'Garona: A Study on Stealth and Treachery',
    '盗贼职业饰品任务。交给博学者基尔达斯（厄运之槌西 - 图书馆）。':
        'Rogue class trinket quest. Bring it to Lorekeeper Kildas (Dire Maul: West - the Library).',
    '束缚之影': 'The Bound Shade',
    '术士职业饰品任务。交给博学者麦库斯（厄运之槌西 - 图书馆）。':
        'Warlock class trinket quest. Bring it to Lorekeeper Mykos (Dire Maul: West - the Library).',
    '奥法师的食谱': "The Arcanist's Cookbook",
    '法师职业饰品任务。交给博学者基尔达斯（厄运之槌西 - 图书馆）。':
        'Mage class trinket quest. Bring it to Lorekeeper Kildas (Dire Maul: West - the Library).',
    '圣光之力': 'The Power of the Light',
    '圣骑士职业饰品任务。交给博学者麦库斯（厄运之槌西 - 图书馆）。':
        'Paladin class trinket quest. Bring it to Lorekeeper Mykos (Dire Maul: West - the Library).',
    '你与冰霜震击': 'You and Frost Shock',
    '萨满祭司职业饰品任务。交给博学者亚沃（厄运之槌西 - 图书馆）。':
        'Shaman class trinket quest. Bring it to Lorekeeper Yavo (Dire Maul: West - the Library).',
    '最伟大的猎手': 'The Greatest Hunter',
    '猎人职业饰品任务。交给博学者麦库斯（厄运之槌西 - 图书馆）。':
        'Hunter class trinket quest. Bring it to Lorekeeper Mykos (Dire Maul: West - the Library).',
    '光明不会告诉你的事情': 'What the Light Never Tells You',
    '牧师职业饰品任务。交给博学者亚沃（厄运之槌西 - 图书馆）。':
        'Priest class trinket quest. Bring it to Lorekeeper Yavo (Dire Maul: West - the Library).',
    '翡翠梦境': 'The Emerald Dream',
    '德鲁伊职业饰品任务。交给博学者亚沃（厄运之槌西 - 图书馆）。':
        'Druid class trinket quest. Bring it to Lorekeeper Yavo (Dire Maul: West - the Library).',
    '防御宝典': 'The Tome of Defense',
    '战士职业饰品任务。交给博学者基尔达斯（厄运之槌西 - 图书馆）。':
        'Warrior class trinket quest. Bring it to Lorekeeper Kildas (Dire Maul: West - the Library).',
    '在厄运之槌找到魔藤并采集一块碎片（必须先干掉奥兹恩），用净化之匣封印后交给月光林地永夜港的拉比恩·萨图纳。':
        'Find the warped vine in Dire Maul and collect a fragment (you must kill Ozien first), seal it with the Purification Cask, and bring it to Rabine Saturna at Nighthaven in Moonglade.',
    '奥兹恩在厄运之槌东区。净化之匣在希利苏斯（62,54）。前置同样来自拉比恩·萨图纳。':
        'Ozien is in Dire Maul: East. The Purification Cask is in Silithus (62,54). The prerequisite also comes from Rabine Saturna.',
    '厄运之槌 西，图书馆': 'Dire Maul: West, the Library',
    '厄运之槌 西，（上层）': 'Dire Maul: West (upper level)',
    '厄运之槌 北，': 'Dire Maul: North,',
    '回图书馆找到辛德拉的宝藏，领取你的奖励吧！':
        "Return to the Library to find the Shen'dralar treasure and claim your reward!",
    '宝藏就在图书馆的梯子下面。': 'The treasure is under the ladder in the Library.',
    '获取免费的酒。': 'Get free booze.',
    '和克雷格对话即可同时接取并交付；注意要带着「当国王真好」这个状态。':
        "Talk to Trampler Craig to take and turn in at once; make sure you carry the 'Good to be King' buff.",
    '安泰恩的奇怪请求': "Anthion's Strange Request",
    '用召唤火盆召出伊萨利恩的灵魂并杀掉她，把火盆和瓦塔拉克饰品左瓣还给伯德雷。':
        "Use the summoning brazier to call out Isalien's spirit and kill her; return the brazier and the left half of the Vatalak Trinket to Bodley.",
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。伊萨利恩在副本内召唤。':
        "You need the Extraplanar Ghost Revealer to see Bodley (from 'Finding Anthion'). Isalien is summoned inside the dungeon.",
    '用召唤火盆召出伊萨莉恩的灵魂并杀掉他，把火盆和瓦塔拉克公爵的饰品还给伯德雷。':
        "Use the summoning brazier to call out Isalien's spirit and kill it; return the brazier and Duke Vatalak's trinket to Bodley.",
    '用召唤火盆召出莫尔·灰蹄的灵魂并杀掉他，把火盆和瓦塔拉克饰品左瓣带回黑石山交给伯德雷。':
        "Use the summoning brazier to call out Mor Grayhoof's spirit and kill him; bring the brazier and the left half of the Vatalak Trinket back to Bodley at Blackrock Mountain.",
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。莫尔·灰蹄在副本内召唤。':
        "You need the Extraplanar Ghost Revealer to see Bodley (from 'Finding Anthion'). Mor Grayhoof is summoned inside the dungeon.",
    '在比斯巨兽的房间用召唤火盆召出瓦塔拉克公爵，杀死后对尸体使用瓦塔拉克的饰品，再把饰品还给瓦塔拉克公爵之魂。':
        "Use the summoning brazier in the Beast's room to call out Duke Vatalak; after killing him, use the Vatalak Trinket on the corpse, then return the trinket to the Spirit of Duke Vatalak.",
    '最后的准备': 'The Final Preparation',
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。瓦塔拉克公爵在副本内召唤；奖励向伯德雷领取。':
        "You need the Extraplanar Ghost Revealer to see Bodley (from 'Finding Anthion'). Duke Vatalak is summoned inside the dungeon; claim the reward from Bodley.",
    '用召唤火盆召出库尔莫克的灵魂并杀掉他，把火盆和瓦塔拉克饰品左瓣还给黑石山的伯德雷。':
        "Use the summoning brazier to call out Kormok's spirit and kill him; return the brazier and the left half of the Vatalak Trinket to Bodley at Blackrock Mountain.",
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。库尔莫克在副本内。':
        "You need the Extraplanar Ghost Revealer to see Bodley (from 'Finding Anthion'). Kormok is inside the dungeon.",
    '用召唤火盆召出库尔莫克的灵魂并杀掉他，把火盆和瓦塔拉克公爵的饰品还给黑石山的伯德雷。':
        "Use the summoning brazier to call out Kormok's spirit and kill him; return the brazier and Duke Vatalak's trinket to Bodley at Blackrock Mountain.",
    '用召唤火盆召出亚雷恩和索托斯的灵魂并杀掉他们，把火盆和瓦塔拉克饰品左瓣还给黑石山的伯德雷。':
        "Use the summoning brazier to call out the spirits of Jarien and Sothos and kill them; return the brazier and the left half of the Vatalak Trinket to Bodley at Blackrock Mountain.",
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。两人在副本内召唤。':
        "You need the Extraplanar Ghost Revealer to see Bodley (from 'Finding Anthion'). The two are summoned inside the dungeon.",
    '用召唤火盆召出亚雷恩和索托斯的灵魂并杀掉他们，把火盆和瓦塔拉克公爵的饰品还给黑石山的伯德雷。':
        "Use the summoning brazier to call out the spirits of Jarien and Sothos and kill them; return the brazier and Duke Vatalak's trinket to Bodley at Blackrock Mountain.",
    '瓦塔拉克饰品的右瓣': 'The Right Half of the Vatalak Trinket',
    '从黑石塔的兽人身上收集 40 副黑石护腕，连同 1 瓶超级能量合剂一起交给黑石山的伯德雷。':
        'Collect 40 Blackrock bracers from the orcs of Blackrock Spire and hand them, together with 1 Super Energy Potion, to Bodley at Blackrock Mountain.',
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。护腕由黑石塔兽人掉落；超级能量合剂是炼金制品。':
        "You need the Extraplanar Ghost Revealer to see Bodley (from 'Finding Anthion'). The bracers drop from Blackrock Spire orcs; the Super Energy Potion is an alchemy product.",
    '把急速圣典、1 块原始黑钻石、2 份大块魔光碎片和 2 份英雄之血交给厄运之槌的博学者莱德罗斯，换取一份急速秘药。':
        'Hand the Libram of Rapidity, 1 Primal Black Diamond, 2 Large Brilliant Shards and 2 Blood of Heroes to Lorekeeper Lydros in Dire Maul for a Quickening Elixir.',
    '无前置，但精灵的传说任务要先完成才能接。圣典随机掉落、可交易。英雄之血在东西瘟疫之地地面随机刷新，拾取绑定。':
        'No prerequisite, but the "Elven Legends" quest must be completed first. The libram drops randomly and is tradeable. Blood of Heroes spawns randomly on the ground in the Eastern and Western Plaguelands, picked up bound.',
    '把防护圣典、1 块原始黑钻石、2 份大块魔光碎片和 1 份磨损的憎恶缝合线交给厄运之槌的博学者莱德罗斯，换取一份防护秘药。':
        'Hand the Libram of Protection, 1 Primal Black Diamond, 2 Large Brilliant Shards and 1 Frayed Abomination Stitching to Lorekeeper Lydros in Dire Maul for a Protection Elixir.',
    '无前置，但精灵的传说任务要先完成才能接。圣典在厄运之槌随机掉落、可交易，拍卖行能买到。磨损的憎恶缝合线由斯坦索姆的吞咽者拉姆斯登、缝补憎恶、泼毒者、喷胆者随机掉落，拾取绑定。':
        'No prerequisite, but the "Elven Legends" quest must be completed first. The libram drops randomly in Dire Maul and is tradeable on the auction house. Frayed Abomination Stitching drops randomly from Swallower Ramsden, Patched Abominations, Venom Belchers and Gall Sprayers in Stratholme, picked up bound.',
    '把专注圣典、1 块原始黑钻石、4 份大块魔光碎片和 2 张暗影之皮交给厄运之槌的博学者莱德罗斯，换取一份专注秘药。':
        'Hand the Libram of Focus, 1 Primal Black Diamond, 4 Large Brilliant Shards and 2 Shadowhide Pelts to Lorekeeper Lydros in Dire Maul for a Focus Elixir.',
    '无前置，但精灵的传说任务要先完成才能接。圣典随机掉落、可交易。暗影之皮由通灵学院的复活的构造体和复活的骷髅守卫随机掉落，拾取绑定。':
        'No prerequisite, but the "Elven Legends" quest must be completed first. The libram drops randomly and is tradeable. Shadowhide Pelts drop randomly from the Reanimated Constructs and Resurrected Skeleton Guards of Scholomance, picked up bound.',
    '到厄运之槌扭木广场，从荒野萨特身上取 15 份萨特之血，交给腐烂之痕的戴奥。':
        'Go to the Warpwood Quarter of Dire Maul, take 15 Satyr Blood from the wild satyrs, and bring them to the withered Dio of the Tainted Scar.',
    '术士召唤末日守卫任务线，相关任务都从衰老的戴奥处接。走厄运之槌东的「后门」进最方便（菲拉斯 - 拉瑞斯小亭 77,37），需要月牙钥匙开门。':
        'This is the warlock doom guard summoning line — all related quests are taken from the withered Dio. The easiest way in is the "back door" of Dire Maul: East (Feralas - The Lariss Pavilion 77,37); it requires the Crescent Key.',
    '把第五、第六块摩沙鲁石板交给塔纳利斯的勘查员詹斯·铁靴。':
        "Bring the fifth and sixth Mosh'aru Tablets to Prospector Ironboot in Tanaris.",
    '石板在副本内两处位置附近。奖励来自《面对叶基亚》；叶基亚就在詹斯·铁靴旁边。':
        "The tablets are near two spots inside the dungeon. The reward comes from 'Facing Yeh'kinya'; Yeh'kinya is right beside Prospector Ironboot.",
    '到黑石塔杀死暗影猎手沃什加斯，把蛇石交给基尔拉姆。':
        'Kill Shadow Hunter Washgus in Blackrock Spire and bring the Serpent Stone to Kilram.',
    '沃什加斯在副本内。': 'Washgus is inside the dungeon.',
    '到黑石塔摧毁座狼的源头——赫林迪斯临别喊出的「哈雷肯」，兽人语里就是「座狼」。':
        'Destroy the source of the worgs in Blackrock Spire — "Hareken", the word Helendis shouted as a farewell, means "worg" in orcish.',
    '哈雷肯在副本内。': 'Hareken is inside the dungeon.',
    '杀死血斧座狼的领袖哈雷肯。': 'Kill Hareken, the leader of the Bloodaxe worgs.',
    '到黑石塔捕捉血斧座狼幼崽：用笼子收服这些小家伙，把笼中的幼崽交给基布雷尔。':
        'Trap the Bloodaxe worg pups in Blackrock Spire: use the cage to subdue the little ones and bring the caged pup to Kibler.',
    '座狼幼崽在副本内。': 'The worg pups are inside the dungeon.',
    '到黑石塔替基布雷尔收集 15 枚尖塔蜘蛛卵。':
        'Collect 15 Spirestone Spider Eggs for Kibler in Blackrock Spire.',
    '蜘蛛卵在副本内。': 'The spider eggs are inside the dungeon.',
    '在黑石塔中心找到烟网蛛后，与她战斗让她向你体内注入毒汁；有能力就顺手杀了她。中毒后回狼狈不堪的约翰那里，让他把「蛛后的乳汁」抽出来。':
        'Find the Queen of the Smokeweb at the heart of Blackrock Spire and fight her so she injects venom into you; kill her too if you can. Once poisoned, return to Ragged John and have him draw out the "Queen\'s Milk".',
    '烟网蛛后在副本内。注意：中途解毒会导致任务失败。':
        'The Queen of the Smokeweb is inside the dungeon. Note: cleansing the poison midway fails the quest.',
    '阅读瓦罗什的卷轴并把瓦罗什的蟑螂还给他。':
        "Read Warosh's scroll and return Warosh's cockroach to him.",
    '流程：先杀乌洛克拿头颅；长矛在副本内，用它召唤（召唤前会刷几群食人魔，可用长矛攻击）。':
        'Sequence: kill Urok first for the head; the spear is inside the dungeon — use it for the summoning (several ogre waves spawn before the summon, and the spear can attack them).',
    '击杀欧莫克大王、指挥官沃恩和维姆萨拉克，找到重要的黑石文件，向卡加斯的军官高图斯汇报。':
        "Kill King Omokk, Commander Vohn and Vimsalak, find the important Blackrock documents, and report to Warlord Goretooth in Kargath.",
    '位置：欧莫克大王、指挥官沃恩、维姆萨拉克。黑石文件在其中一名 首领 旁边。':
        'Locations: King Omokk, Commander Vohn, Vimsalak. The Blackrock documents are beside one of the bosses.',
    '到黑石塔查明比修的下落。': 'Find out what happened to Bijou in Blackrock Spire.',
    '比修在副本内。': 'Bijou is inside the dungeon.',
    '找回比修的装置还给她——她记得藏在城市最底层。':
        "Recover Bijou's device and return it to her — she remembers hiding it in the lowest level of the city.",
    '装置在通往烟网蛛后的路上。': 'The device is on the way to the Queen of the Smokeweb.',
    '找回比修的装置还给她。祝你好运！':
        "Recover Bijou's device and return it to her. Good luck!",
    '装置在通往烟网蛛后的路上。后续找麦克斯韦元帅（燃烧平原 - 摩根的岗哨 84,58）。':
        "The device is on the way to the Queen of the Smokeweb. Afterwards see Marshal Maxwell (Burning Steppes - Morgan's Vigil 84,58).",
    '与永望镇的玛雷弗斯·暗锤谈一谈。':
        'Talk with Marevus Darkhammer in Everlook.',
    '剥完比斯巨兽的皮后芬克·恩霍尔才会出现。玛雷弗斯·暗锤在冬泉谷 - 永望镇（61,38）。':
        'Fink Enhall only appears after the Beast has been skinned. Marevus Darkhammer is at Winterspring - Everlook (61,38).',
    '到黑石塔消灭指挥官沃恩、欧莫克大王和维姆萨拉克，回麦克斯韦尔元帅处复命。':
        'Eliminate Commander Vohn, King Omokk and Vimsalak in Blackrock Spire, then report back to Marshal Maxwell.',
    '位置：沃恩、欧莫克大王、维姆萨拉克。':
        'Locations: Vohn, King Omokk, Vimsalak.',
    '达基萨斯将军的命令掉落自（维姆萨拉克）':
        "General Drakkisath's Command drops from (Vimsalak)",
    '把达基萨斯将军的命令交给燃烧平原的麦克斯韦尔元帅。':
        "Bring General Drakkisath's Command to Marshal Maxwell in the Burning Steppes.",
    '麦克斯韦尔元帅在燃烧平原 - 摩根的岗哨（84,58）。':
        "Marshal Maxwell is at Burning Steppes - Morgan's Vigil (84,58).",
    '到黑石塔找到古拉鲁克，杀死后用血污长矛刺入尸体吸干灵魂炼成穿魂长矛；再找一块未铸造的符文覆饰胸甲，把两样都交给冬泉谷的罗拉克斯。':
        'Find Gularuk in Blackrock Spire; after killing him, thrust the Bloodstained Spear into the corpse to drain its soul and forge the Soulpiercer; then find an unforged Runed Breastplate and bring both to Lorax in Winterspring.',
    '锻造任务。古拉鲁克在副本内。':
        'Blacksmithing quest. Gularuk is inside the dungeon.',
    '到黑石塔收集 20 颗黑色龙人的眼球，回巫女麦兰达处复命。':
        'Collect 20 Black Dragon Whelp eyes in Blackrock Spire, then report back to Myranda the Hag.',
    '黑龙系的敌人都会掉眼球。': 'All black dragonkin drop the eyes.',
    '世界上一定有人知道这副手套的来历。祝你好运！':
        'Someone in the world must know the origin of these gloves. Good luck!',
    '锻造任务。从人类残骸附近拿到板甲手套，交给玛雷弗斯·暗锤（冬泉谷 - 永望镇 61,39）。':
        'Blacksmithing quest. Take the plate gloves from near the human remains and bring them to Marevus Darkhammer (Winterspring - Everlook 61,39).',
    '在孵化间对一颗龙蛋使用龙蛋冷冻器初号机。':
        'Use the Egg Freezer Mark I on a dragon egg in the hatchery.',
    '龙蛋在烈焰之父的房间。': "The eggs are in the Father Flame's room.",
    '把电动采集模块和 8 颗龙蛋交给燃烧平原烈焰峰的丁奇·斯迪波尔。':
        'Bring the Electric Collection Module and 8 dragon eggs to Tinkee Steamboil at Flame Crest in the Burning Steppes.',
    '龙蛋都在烈焰之父的房间里。': "The eggs are all in the Father Flame's room.",
    '找齐三块命令宝石——燃棘宝钻、尖石宝钻、血斧宝钻——连同原始晋升印章一起交给维埃兰。':
        'Gather the three command gemstones — the Smolderthorn Gemstone, the Spirestone Gemstone and the Bloodaxe Gemstone — and bring them, together with the Unforged Seal of Ascension, to Vaelan.',
    '宝石来源：欧莫克大王、指挥官沃恩、维姆萨拉克。原始晋升印章由黑石塔小怪掉落。完成后即可拿到上层黑石塔的钥匙。':
        'Gem sources: King Omokk, Commander Vohn, Vimsalak. The Unforged Seal of Ascension drops from Blackrock Spire trash mobs. Completing this yields the key to Upper Blackrock Spire.',
    '把末日扣环交给燃烧平原的玛亚拉·布莱特文。':
        "Bring Doomrigger's Clasp to Mayara Brightwing in the Burning Steppes.",
    '前置可从雷明顿·瑞治维尔伯爵接（暴风城 - 暴风要塞 77,47）。扣环在烈焰之父房间的箱子里。':
        "The prerequisite can be taken from Lord Remington Ridgewell (Stormwind City - Stormwind Keep 77,47). The clasp is in the chest in the Father Flame's room.",
    '到冬泉谷找到哈尔琳，把奥比的鳞片交给她。':
        "Find Haleh in Winterspring and bring her Awbee's scale.",
    '奥比在竞技场旁的房间，蹲在一处凸台上。哈尔琳在冬泉谷（54,51）；从洞穴最里面的传送符文站上去就能到她身边。':
        'Awbee is in the room beside the arena, crouching on a ledge. Haleh is in Winterspring (54,51); take the teleport rune at the very back of the cave to reach her.',
    '在比斯巨兽的房间': 'In the room of the Beast',
    # ==== 2026-10-07 · fc 全量核查：新增 3 条任务地点 ====
    '奥特兰克山脉 - 达拉然城副本外': 'Alterac Mountains - outside the City of Dalaran entrance',
    '莫高雷 32.4,20.6': 'Mulgore 32.4,20.6',
    # ==== 2026-10-08 · 达拉然城 7 条任务（fc 页 8 任务补齐）====
    '暴风城 - 法师区': 'Stormwind City - Mage Quarter',
    '希尔斯布莱德丘陵 - 塔伦米尔': 'Hillsbrad Foothills - Tarren Mill',
    '幽暗城 - 炼金区': 'Undercity - The Apothecarium',
    '奥特兰克山脉 - 达拉然城下水道入口附近': 'Alterac Mountains - near the Dalaran sewer entrance',
}


# ===== 2026-10-04 全任务评论精选（方案 1 全量采纳）：注释注释新稿 =====
QUESTS2B = {
    '蘑菇（品红菌盖）散落在进本前的洞穴里（不在副本内），多在火堆旁和帐篷后面；学了草药学开追踪会在小地图上标出。前置任务同样在这名 NPC 处接。': "The Magenta Fungus Caps are scattered in the cave BEFORE the instance (not inside), mostly by campfires and behind tents; with Herbalism tracking on they show up on the minimap. The prerequisite quest is taken from the same NPC.",
    '徽章由副本入口处的工头希斯奈特掉落。◎ 单刷建议 23 级以上：精英伤害高且会连锁拉怪，任务目标怪与旁边一只小怪联动。':
        "Badges drop from Foreman Thistlenettle right by the dungeon entrance. ◎ For solo runs wait until level 23 or so: the elites hit hard and chain-pull, and the quest mob is linked to another add.",
    '会员卡由副本入口附近的亡灵掉落。◎ 会员卡掉率很低且不共享（各拾各的），实测耗时较长，做好心理准备。':
        "Union cards drop from the undead near the dungeon entrance. ◎ The drop rate is very low and they are NOT shared among the group (everyone loots their own) — expect a long grind.",
    '塔格尔在副本内。塔格尔通常刷在中央区右手第一间或左手第二间牢房，偶尔刷在左右两翼之间最北端的牢房。':
        "Targorr is inside the dungeon. He usually spawns in the first cell on the right or the second cell on the left of the central wing; rarely, in the northernmost cell between the two wings.",
    '系列始于哈缪尔·符文图腾（雷霆崖 - 长者高地 78,28）。四名掉宝石的德鲁伊分散在副本内的四个房间。◎ 宝石人人有份：四名首领每位都会为队伍里每名有任务的玩家掉一颗。':
        "The chain starts with Hamuul Runetotem (Thunder Bluff - Elder Rise 78,28). The four gem-dropping druids are spread across four separate chambers inside the dungeon. ◎ The gems are for everyone: each of the four leaders drops one gem for every party member on the quest.",
    '手稿泡在副本内一处水洼里。手稿在海龟王房间的水池区——进门右手边的水下凹龛箱子里，有 1-2 只纳迦看守（可单拉）。':
        "The manuscript lies in a pool inside the dungeon — in the water area of the turtle-king room: an underwater alcove chest on the right as you enter, guarded by 1-2 naga (single-pullable).",
    '书在芬鲁斯（巨狼）房间的书架上——进房间左手边第一个书架下层，蓝色书本。◎ 拾取后约 10 秒重生，全队每人都能拿到（不共享）。◎ 杀死芬鲁斯后他会召唤 4 只虚空行者（非精英但伤害不低，盗贼/野德可提前脱战隐身）。':
        "The book is on the bookshelf in Fenrus' (the great worg) room — bottom shelf of the first bookcase on the left as you enter, a blue book. ◎ It respawns after about 10 seconds, so every party member can loot one (not shared). ◎ When Fenrus dies he summons 4 Voidwalkers (non-elite but they hit hard; rogues/cats can drop combat early with Vanish/Prowl).",
    '阿达曼特在副本内；文森特进庭院后右手边。第一段要先释放被囚的死灵看守，他才会开门放队伍进庭院；第二人在进门时就能看到阿鲁高折磨他，绕过去解救即可。':
        "Deathstalker Adamant is inside the dungeon; Deathstalker Vincent is to the right after entering the courtyard. For the first part you must release the imprisoned deathstalker before the courtyard door opens; the second one can be seen tormented by Arugal right as you enter — work your way around to free him.",
    '只有副本最西侧、尾王卡尔加·刺肋前一厅的穴居蝙蝠会掉（掉率很高），要穿过大半个副本才能遇到它们。':
        "Only the Kraul Bats in the far-west chamber (just before the last boss, Charlga Razorflank) drop the guano — with a very high drop rate — and you must fight through most of the dungeon to reach them.",
    '石板在副本内，就在加加恩·火锤身旁。':
        "The tablet is inside the dungeon, right beside Galgann Firehammer.",
    '护送时离他太远或太近都会判失败。进本右手穿过野猪区即到威利克斯，无需清任何首领。':
        "The escort fails if you get too far ahead of him or fall too far behind. Turn right from the entrance through the boar area to reach Willix — no bosses need to be cleared.",
    '系列始于多恩·平原行者（千针石林 53,41）。书在血色修道院图书馆：宝库画廊进门左手第一间房的桌上（摊开的书）。':
        "The chain starts with Dorn Plainstalker (Thousand Needles 53,41). The book is in the Scarlet Monastery Library: an open book on the table in the first room on the left as you enter the Gallery of Treasures.",
    '塞尔瑞德在副本内。塞尔瑞德在海龟池西南侧的水下。':
        "Thaelrid is inside the dungeon. He is underwater on the southwest side of the turtle pool.",
    '暮光之锤的敌人个个都掉坠饰。◎ 玩家报告当前版本结算会把 3 件奖励一起给（疑似 bug）。':
        "Every Twilight's Hammer enemy in the dungeon drops a pendant. ◎ Players report the current turn-in awards all 3 reward items at once (likely a bug).",
    '可一趟连做，推荐路线：先北（贡品，备好食人魔套装材料与坏陷阱）→ 西（杀伊莫塔尔）→ 图书馆（杀托塞德林王子）→ 回北出门时向芬古斯交任务。':
        "Doable in one run. Recommended route: North first (tribute run — bring the ogre-suit materials and the broken trap) → West (kill Immol'thar) → Library (kill Prince Tortheldrin) → back to North, turn in to Fengus on the way out.",
    '迦玛兰在副本内。要先清掉阳台上的一圈幽灵（守结界的亡灵巨魔）才能开打迦玛兰。':
        "Jammal'an is inside the dungeon. You must first clear the ring of ghosts on the balconies (the undead trolls holding his barrier) before he can be engaged.",
    '在本处接前置。石板进本前就能拿满：门口大厅水下中央 1 块、两侧桌上各 1 块，约 8 分钟刷新，等一等即可凑齐全队。':
        "Take the prerequisite here. The tablets can all be looted BEFORE the instance: 1 underwater in the center of the entrance hall and 1 on each of the two side tables, respawning about every 8 minutes — wait a bit and even a full group gets theirs.",
    '仅战士可接！燃素从鲁古格获取；烧焦的蜘蛛牙出自湿地蜘蛛，烧焦的奇美拉角、光滑的奇美拉角分别出自石爪山脉的奇美拉幼崽和雌奇美拉。鲁古格位置：进副本第一个左转，绕过弯道上藤桥，过了桥他就在右手边。':
        "Warrior only! The phosphorus comes from Roogug; Scorched Spider Fangs from Wetlands spiders, and Charred and Sleek Chimera Horns from chimera cubs and females in Stonetalon Mountains. Roogug location: take the first left inside the dungeon, follow the curve over the vine bridge — he is right there on the other side.",
    '仅法师可做！能量源由黑曜石哨兵掉落。黑曜石哨兵就在后门里——从荒芜之地的后门（67,44）进去第一眼就能看到，没有小怪护卫。':
        "Mage only! The power source drops from the Obsidian Sentinel. The sentinel is right inside the back door — enter from the Badlands back entrance (67,44) and it is the first thing you see, with no guarding adds.",
    '那名圣骑士在副本内：遗体在守护者大厅（第一个「8」字形区域）的西北角，头顶黄问号、无需搜索互动。':
        "The paladin is inside the dungeon: the body is in the northwest corner of the Hall of the Keepers (the first sideways-'8' shaped area), marked with a yellow '?' — no searching required.",
    '杀掉阿扎达斯后进入其身后的宝库，点底座上的圆盘接任务；听召唤出的幽灵讲完全部故事后，再点一次圆盘拿到缩小版——漏了这步就得重跑一趟。回雷霆崖交任务（NPC 在 35,47 附近）。':
        "After killing Archaedas, walk into the vault behind him and click the disc on the pedestal to accept the quest; after listening to the summoned ghost's full story, click the disc AGAIN to receive the miniature — miss this step and you have to run the dungeon again. Turn in at Thunder Bluff (NPC around 35,47).",
    '那名圣骑士在副本内：进本后一直右手贴墙走就能到遗体处。':
        "The paladin is inside the dungeon: enter and keep hugging the wall on your right — it leads straight to the body.",
    '巴尔洛戈在副本内。引导任务：若已接受或完成《隐藏的密室》，本任务将无法完成。':
        "Ballog is inside the dungeon. Breadcrumb quest: it cannot be completed if you have already accepted or completed 'The Hidden Chamber'.",
    '副本内外的暗炉系敌人都掉能量石。不用进副本——在进本前的挖掘场打暗炉矮人就能攒齐。':
        "Dark Iron enemies inside and outside the dungeon drop the power stones. No need to enter the dungeon — killing the Dark Iron dwarves at the dig site outside the entrance is enough.",
    '前置可从索维克（奥格瑞玛 - 荣誉谷 75,25）接。完成后就能使用藏宝海湾的传送器。◎ 哥布林转发器用完可以丢掉，丢了再找斯库提说一声就能再领一个。':
        "The prerequisite is from Sovik (Orgrimmar - Valley of Honor 75,25). Completing it lets you use the Booty Bay teleporter. ◎ The goblin transponder can be discarded after use; if you lose it, just tell Scooty and you get another.",
    '前置始于克拉兹克（荆棘谷 - 藏宝海湾 25,77），非必需、可直接接。所有圣甲虫都掉壳，圣甲虫大厅一带数量最集中。':
        "The optional prerequisite starts with Krazek (Stranglethorn Vale - Booty Bay 25,77) — not required, the quest can be taken directly. Every scarab drops a shell; the scarab hall has the densest concentration.",
    '护送任务。斯库提在荆棘谷 - 藏宝海湾（27,77）。护送终点是副本正门（送到门口即可，不用穿出去）；小侏儒不会主动引怪，潜行职业全程潜行也能做。':
        "Escort quest. Scooty is in Stranglethorn Vale - Booty Bay (27,77). The escort ends at the dungeon's FRONT entrance (deliver him to the door; no need to go through); the little gnome won't pull adds on his own, so stealth classes can do the whole quest while stealthed.",
    '前置可从加克希姆·尘链接（石爪山脉 59,67），非必需。读卡接力：白卡出自副本外上层的流动精英，插进副本外的读卡器；每台读卡器都会给出下一台需要的卡，沿途顺路拿科技机器人的脑。':
        "The optional prerequisite is from Gaxim Rustfizzle (Stonetalon Mountains 59,67). Punch-card relay: the White Punch Card drops from the wandering elites on the upper level outside the instance; insert it into the card reader outside the instance, and each reader gives you the card for the next one — grab Techbot's brain along the way.",
    '任务始于辛特兰巨魔村庄的毒液瓶系列。石板在副本内。潜行职业可以直接摸到石板前阅读完成，不用杀殉教者塞卡；甲虫是中立生物，别用 AOE 惊动它们。':
        "The chain begins with the Vial series from the troll village in the Hinterlands. The tablet is inside the dungeon. Stealth classes can sneak straight to the tablet and finish reading it without fighting Theka the Martyr; the scarabs are neutral — just avoid AOE.",
    '系列始于狮鹫管理员沙拉克·鹰斧（辛特兰 - 蛮锤城堡 9,44）。耐克鲁姆在副本内：释放布莱后从大阶梯涌上的最后一波敌人里出现。':
        "The chain starts with the gryphon master at Aerie Peak, Hinterlands (9,44). Nekrum is inside the dungeon: he spawns in the final wave that comes up the great stairs after Bly is freed.",
    '祭坛在图中。进本右手下楼梯到「污秽之坑」，哈卡祭坛就在那里。':
        "The altar is on the map. Inside the dungeon take the right-hand stairs down into the 'Pit of Refuse' — the Altar of Hakkar is right there.",
    '雕像群在副本内，开启顺序：南 → 北 → 西南 → 东南 → 西北 → 东北。':
        "The statues are inside the dungeon; activate them in this order: South → North → Southwest → Southeast → Northwest → Northeast.",
    '这不是护送任务本体——先完成它，之后才会开放真正的护送任务《扑灭圣火之仪》。确保全队都完成本任务后再进护送段，否则没完成的人拿不到后续。':
        "This is not the escort quest itself — complete this one first, and only then the real escort quest 'Extinguishing the Idol' becomes available. Make sure EVERYONE in the party finishes this quest before starting the escort segment, or those who haven't will miss the follow-up.",
    '他是剃刀高地的最终首领。★ 本任务不可共享，队里每个人都要自己接。':
        "He is the final boss of Razorfen Downs. ★ This quest cannot be shared — everyone in the party must pick it up for themselves.",
    '系列始于卡拉然·温布雷（灼热峡谷 39,38）。贝尔加在副本内。别忘了站在贝尔加尸体上使用背包里的蜕皮物品，容易顺手漏掉。':
        "The chain starts with Kharan Mighthammer (Burning Steppes 39,38). Bael'Gar is inside the dungeon. Don't forget to use the molt item from your bags while standing on Bael'Gar's corpse — it's easy to miss.",
    '前置由药剂师金格给予（幽暗城 - 炼金房 50,68）。砸破酒桶刷出的守卫中每名都掉秘方（全队各拿各的）；团灭的话酒桶消失，需重置副本再来。':
        "The prerequisite is given by Apothecary Zinge (Undercity - The Apothecarium 50,68). After smashing the barrels Hurley shows up with elite guards, and EVERY spawned guard drops a recipe (one per party member); if you wipe, the barrels despawn and the instance must be reset to try again.",
    '前置《穆尔金和拉瑞安》始于穆尔金（安戈洛环形山 - 马绍尔营地 42,9）。神庙深渊潜伏者、黑暗虫、融合软泥怪都掉。必须进副本打——本外的软泥怪不掉。进本右手下楼梯即到潜伏者/软泥怪区。':
        "The prerequisite 'Muigin and Larion' starts with Muigin (Un'Goro Crater - Marshal's Refuge 42,9). Temple deep lurkers, dark crawlers and fused oozes all drop it. You MUST go inside the instance — the oozes outside don't drop it. Take the right-hand stairs down inside the entrance to reach the lurker/ooze area.",
    '前置《拉瑞安和穆尔金》始于拉瑞安（安戈洛环形山 45,8）。神庙深渊潜伏者、黑暗虫、软泥怪都掉。必须进副本打——本外的软泥怪不掉。进本右手下楼梯即到潜伏者/软泥怪区。':
        "The prerequisite 'Larion and Muigin' starts with Larion (Un'Goro Crater 45,8). Temple deep lurkers, dark crawlers and oozes all drop it. You MUST go inside the instance — the oozes outside don't drop it. Take the right-hand stairs down inside the entrance to reach the lurker/ooze area.",
    '温德索尔元帅被关在副本内的牢房里（钥匙由审讯官格斯塔恩掉落）。交完本任务没有直接后续：回深渊继续清怪，直到刷出「揉皱的便条」开启下一段任务。':
        "Marshal Windsor is held in a cell inside the dungeon (the key drops from High Interrogator Gerstahn). There is no immediate follow-up after turning this in: go back into BRD and keep killing mobs until 'A Crumpled Up Note' drops to continue the chain.",
    '「揉皱的便条」在深渊内随机掉落。温德索尔元帅在深渊的监狱里——别搞混：麦克斯韦尔元帅在燃烧平原的摩根的岗哨。':
        "'A Crumpled Up Note' drops randomly inside BRD. Marshal Windsor is in the BRD prison — don't mix the two up: Marshal Maxwell is at Morgan's Vigil in the Burning Steppes.",
    '越狱（护送温德索尔）前确保全队都已交掉前序任务，否则有人拿不到进度。完成后出本前必须先和温德索尔对话，直接跑出副本就得重跑一遍。':
        "Before starting the Jail Break (the Windsor escort), make sure everyone in the party has turned in the previous quest, or some members won't get credit. After completing it you MUST talk to Windsor before leaving the dungeon — running straight out means doing it all over again.",
    '龙蛋在烈焰之父的房间。冻蛋后别去点蛋，直接用背包里的装置；打完达基萨斯将军后可以直接跳下龙蛋房单独补做。':
        "The eggs are in the Father Flame's room. After freezing an egg do NOT click it — use the device from your backpack; after killing General Drakkisath you can jump straight down to the rookery and finish it separately.",
    '龙蛋都在烈焰之父的房间里。冻住蛋后靠近使用背包里的装置即可（不用点蛋）；团里没人管的话，打完将军跳下龙蛋房可单独补做。':
        "The eggs are all in the Father Flame's room. After freezing an egg, get close and use the device from your backpack (don't click the egg); if the raid won't wait, jump down to the rookery after the General to finish it solo.",
    '在龙下方的水中使用未铸造的印章开启铸印事件。事件一次只出 1 枚可拾取的锻造印章，且龙有 3 小时冷却——一晚只能做一个人。':
        "Use the Unforged Seal in the water below the dragon to start the forging event. Each event yields only ONE lootable forged seal, and the dragon has a 3-hour cooldown — only one person can do it per night.",
    '前置可从雷明顿·瑞治维尔伯爵接（暴风城 - 暴风要塞 77,47）。扣环在烈焰之父房间的箱子里。箱子约 20 秒刷新一次，多人可轮流开。':
        "The prerequisite can be taken from Lord Remington Ridgewell (Stormwind City - Stormwind Keep 77,47). The clasp is in the chest in the Father Flame's room. The chest respawns about every 20 seconds, so multiple party members can open it in turn.",
    '前置可从药剂师金格接（幽暗城 - 炼金房 50,68）。石板在上层黑石塔的龙蛋房（孵化场）。':
        "The prerequisite can be taken from Apothecary Zinge (Undercity - The Apothecarium 50,68). The tablet is in the UBRS rookery (the hatchery).",
    '第 5 块石板在暗影猎手沃什加斯的房间，第 6 块在战争大师沃恩的房间。奖励来自《面对叶基亚》；叶基亚就在詹斯·铁靴旁边。':
        "The 5th tablet is in Shadow Hunter Vosh'gajin's room, the 6th in War Master Voone's room. The reward comes from 'Facing Yeh'kinya'; Yeh'kinya is right beside Prospector Ironboot.",
    '蜘蛛卵在副本内。拾卵时会随机刷出小蜘蛛，伤害高还带 AOE，留意。':
        "The spider eggs are inside the dungeon. Looting an egg can randomly spawn small spiders — they hit hard and have an AOE, watch out.",
    '流程：先杀乌洛克拿头颅；长矛在副本内，用它召唤（召唤前会刷几群食人魔，可用长矛攻击）。◎ 每次刷新只限 1 人交任务——交了之后他就变回食人魔形态，不再有黄问号。':
        "Flow: kill Omokk first for the head; the pike is inside the dungeon — use it to summon (several ogre packs spawn first; you can attack them with the pike). ◎ Only ONE person per spawn can turn this in — once turned in, he turns into his ogre form and no longer has the yellow '?'.",
    '锻造任务。古拉鲁克在副本内。需要锻造 270 才能接。':
        "Blacksmithing quest. Goraluk is inside the dungeon. Requires Blacksmithing 270 to pick up.",
    '档案小盒随机刷在奈鲁布恩坎、安娜丝塔丽、马勒基三座通灵塔中的一座里；盒子不会消失，全队每人都拿得到。':
        "The small box spawns randomly in ONE of the three ziggurats (Nerub'enkan, Baroness Anastari, Maleki); it does not disappear — every party member can loot it.",
    '烟草店在副本内：一路左转到底的死角、水井右侧，需清完沿途；开盒的瞬间弗拉斯·希亚比会现身。':
        "The tobacco shop is inside the dungeon: keep turning left to the dead end, to the right of the well — clear everything along the way. Fras Siabi appears the moment you open the box.",
    '圣水在城中各处的箱子里；部分是假箱，打开会钻出一堆虫子。矮人用「寻宝」能在小地图上标出真箱子。':
        "The holy water is in crates all over the city; some are fakes that burst into a swarm of bugs. Dwarves can use 'Find Treasure' to mark the real crates on the minimap.",
    '档案与档案管理员都在副本内。◎ 若同时在做《爱与家庭》：烧档案前先拿到画——画和档案会被一起烧掉。':
        "The archives and the Archivist are both inside the dungeon. ◎ If you are also doing 'Of Love And Family': grab the painting BEFORE burning the archives — the painting burns together with them.",
    '前置从护理者奥林处接（东瘟疫之地 - 圣光之愿礼拜堂 74,58）。鬼魂居民在城中到处游荡。冲击枪打中鬼魂约 10 秒后其身边会出现「不安的灵魂」，对它再补一枪即可拾取。':
        "The prerequisite is from Caretaker Alen (Eastern Plaguelands - Light's Hope Chapel 74,58). Ghostly citizens wander all over the city. About 10 seconds after zapping a ghost with the blaster, a 'Restless Soul' appears beside it — zap that one too and you can loot it.",
    '红衣铸锤师靠召唤出现：点击地上的「锻造计划书」羊皮纸触发。':
        "The Crimson Hammersmith is a triggered spawn: click the 'Blacksmithing Plans' parchment on the ground to trigger it.",
    '黑衣守卫铸剑师靠召唤出现：点击安娜丝塔丽之塔旁当铺边地上的「锻造计划书」触发。':
        "The Dark Iron Guardsmith is a triggered spawn: click the 'Blacksmithing Plans' parchment on the ground next to the pawn shop beside Anastari's ziggurat.",
    '地契位置：凯尔达隆在进门后的第一间大厅；南海镇=过桥后第一间大厅左角书桌上；塔伦米尔=幼龙房前房间的右角书桌；布瑞尔=莱斯·霜语所在的房间。':
        "Deed locations: Caer Darrow = in the first hall after entering; Southshore = on the desk in the left corner of the first large hall after crossing the bridge; Tarren Mill = on the desk in the right corner of the room before the whelps; Brill = in the room where Ras Frostwhisper is.",
    '教授死后看房间两侧的肉堆——伊娃·萨克霍夫夫妇的遗骸就在里面，清掉即完成。':
        "After the doctor dies, look at the piles of flesh on both sides of the room — the remains of Eva and Lucien Sarkhoff are inside; clear them to complete.",
    '门廊在副本内。无辜者之血在第一间房的魅魔身上 100% 掉落；若召唤的克尔托诺斯没开出想要的奖励，可放弃重接（需重置副本重新召唤）。':
        "The vestibule is inside the dungeon. The Blood of Innocents drops 100% from the succubus in the first room; if the summoned Kirtonos doesn't drop the reward you want, abandon and re-take the quest (the instance must be reset to summon again).",
    '前置从马杜克镇长处接（西瘟疫之地 - 凯尔达隆 70,73）。标记就是男爵房间地上的五芒星。另见通灵学院的「巫妖莱斯·霜语」。':
        "The prerequisite is from Magistrate Marduke (Western Plaguelands - Caer Darrow 70,73). The mark is the pentagram on the floor of the Baron's room. See also 'Lich Ras Frostwhisper' in Scholomance.",
    '詹迪斯·巴罗夫在副本内。分身只有本体有血条——开血条显示（V 键）或给本体上标记，只打有血条的那个。':
        "Jandice Barov is inside the dungeon. Only the real body has a health bar among the clones — turn on nameplates (V) or mark the real one, and only hit the one with the bar.",
    '要先完成《瘟疫龙崽》才会出现可采的健康龙鳞（否则看不见）。健康的龙鳞由瘟疫龙崽掉落（约 8%）。贝蒂娜·比格辛克在东瘟疫之地 - 圣光之愿礼拜堂（76,54）。':
        "You must complete 'Plagued Hatchlings' first, otherwise the lootable Healthy Dragon Scales won't appear. The scales drop from Plagued Hatchlings (about 8%). Betina Bigglezink is at Eastern Plaguelands - Light's Hope Chapel (76,54).",
    '玛尔·恐怖图腾在副本深处岔道右侧的高台上——沿路走到尽头 T 字口，靠右的坡道上去，高台左手边的小房间就是。':
        "Maur Grimtotem is on a raised ledge to the right of a fork deep in the dungeon — walk to the T junction at the end, take the right-hand path up the slope, and the small room on the left of the landing is where he is.",
    '前置从提里奥·弗丁处接（西瘟疫之地 7,43）。画在活人区档案室进门右手边。':
        "The prerequisite is from Tirion Fordring (Western Plaguelands 7,43). The painting is in the Archivist's room on the living side, on the right as you enter.",
    '前置由剃刀沼泽的最终首领给出。玛克林大使在进副本前的空地上（贫瘠之地 - 剃刀高地 48,92）。':
        "The prerequisite is given by Razorfen Kraul's final boss. Ambassador Malcin stands in the open ground before the dungeon entrance (The Barrens - Razorfen Downs 48,92).",
    '深渊之核在副本内的水域里。拿到后阿奎尼斯男爵会出现并攻击你，他掉一件任务物品，也一并带给耶努萨克雷。深渊之核在尾王前的大水池中央水下（不用进尾王的房间）。':
        "The Fathom Core is in the water inside the dungeon. Once you take it, Baron Aquanis will appear and attack — he drops a quest item; bring that to Je'neu Sancrea as well. The core is underwater in the center of the big pool before the last boss (no need to enter the boss's room).",
    '玛拉顿里大多数敌人都会掉雕像；无名先知掉率最高，且死后很快在原地附近重生，可速刷。':
        "Most enemies in Maraudon drop the figurine; the Nameless Prophet has the best drop rate and respawns nearby almost immediately after dying — great for fast farming.",
    '装水用副本外带橙色水晶的大水池（不是小仙女站的那个小池）；藤蔓在橙色区域，对花使用瓶子会召唤出花与元素，都杀掉后全队共享完成。':
        "Fill the vial at the big outdoor pool with orange crystals (not the small pool the dryad stands in); the vines are in the orange area — use the vial next to a flower to summon a flower and an elemental; kill both and the completion is shared by the whole group.",
    '节杖由塞雷布拉斯亲手制作；仪式结束后与他对话即可。杖丢了可以再杀塞雷布拉斯，与他对话选「我丢了节杖」重新领取。':
        "The scepter is crafted by Celebras himself; talk to him after the ritual. If you lose the scepter, kill Celebras again and choose 'I lost my scepter' in the dialog to get another.",
    '《贱民的指引》里提到 5 个可汗。无名先知掉落灵魂护符，用它可以显现出 5 个可汗。':
        "'The Pariah's Instructions' mentions the 5 khans. The Nameless Prophet drops the Amulet of Spirits, which is used to materialize the 5 khans.",
    '卡里尔·温萨鲁斯在厄运之槌西区的图书馆。骸骨在图书馆中央、博学者莱德罗斯旁边。':
        "Kariel Winthalus is in the Dire Maul West library. The skeleton is in the center of the library, next to Lorekeeper Lydros.",
    '卡里尔·温萨鲁斯在厄运之槌西区的图书馆。他的骸骨在图书馆中央、博学者莱德罗斯旁边。':
        "Kariel Winthalus is in the Dire Maul West library. His skeleton is in the center of the library, next to Lorekeeper Lydros.",
    '《屠龙纲要》（厄运之槌掉落、可交易）触发奎尔塞拉任务链：把书交给厄运之槌西图书馆的博学者，换取「又钝又平的精灵之刃」开始这段史诗武器任务。':
        "'Foror's Compendium of Dragon Slaying' (drops in Dire Maul, tradeable) triggers the Quel'Serrar quest chain: hand the book to the lorekeeper in the Dire Maul West library to receive the 'Dull and Flat Elven Blade' and begin this epic weapon quest.",
    '仅术士可接！炼金实验室就在莱斯·霜语所在的房间里。':
        "Warlock only! The alchemy lab is in the same room as Ras Frostwhisper.",
    '王子在厄运之槌西；力量护手在他附近的箱子里。推荐顺序：先北拿贡品、带着「当国王真好」状态 → 西杀王子开箱 → 回北交任务。':
        "The prince is in Dire Maul West; the strength gauntlets are in the chest near him. Recommended order: North first — do the tribute run and keep the 'Good to be King' buff → West to kill the prince and open the chest → back to North to turn in.",
    '战士职业任务。6 个小巨魔就是守住迦玛兰结界的亡灵巨魔——进本上楼梯右转那片（不是螺旋楼梯）。':
        "Warrior class quest. The 6 little trolls are the undead trolls holding Jammal'an's barrier — up the stairs and turn right as you enter (not the spiral staircase).",
    '战珠掉率：厄运之槌北约 1/10、黑下约 1/7（但黑下食人魔数量少得多）、厄运竞技场外约 1/50。':
        "Ogre Warbead drop rates: about 1/10 in Dire Maul North, 1/7 in LBRS (but far fewer ogres there), 1/50 outside the DM arena.",
    '暗影精华出自厄运之槌西的幽灵怪。':
        "The shadow essence drops from the ghosts in Dire Maul West.",
    '后续任务因职业而异。竞技场事件：听到喊话后把挑衅旗帜插在场地中央开打。◎ 宝箱必须由接任务的人第一个拾取，否则谁都拿不到饰品（玩家实测）。':
        "The follow-ups differ by class. Arena event: when the yell goes out, plant the Banner of Provocation in the center of the arena to start the fight. ◎ The chest MUST be looted first by the person on the quest, otherwise nobody can loot the trinket (player-reported).",
    '德鲁伊职业任务。藤蔓由召唤出的阿塔拉利恩掉落，需要先正确破解雕像群的秘密。雕像顺序按小地图钟点：6 点 → 12 点 → 8 点 → 4 点 → 10 点 → 2 点（点对了雕像会亮绿灯）。':
        "Druid class quest. The vines drop from the summoned Atal'alarion; you must first solve the statue puzzle correctly. Statue order by minimap clock: 6 → 12 → 8 → 4 → 10 → 2 (correct hits light the statues green).",
    '毒素调查链的一环：几处矿井的样本都查过了，线索都指向月溪镇下方的死亡矿井。到月溪镇收集补给品，回阿尔巴·晴月处交任务后开启爆炸物筹备段。前导环「测井」的两个采样点：莫尔森农场 46.2,38.3、詹森农庄 56.7,18.7。◎ 补给箱就在通往死矿入口的洞穴里，月溪镇各建筑（包括月溪学校）里也散落着一些，不用打精英。':
        "Part of the toxin-investigation chain: samples from several mines all point to the Deadmines beneath Moonbrook. Collect supplies in Moonbrook and turn them in to Alba Fairmoon, which starts the explosives-materiel phase. Sample points of the prerequisite ring 'Log Test': Morlsen Farm 46.2,38.3 and Jensen Farm 56.7,18.7. ◎ The supply crates are in the cave on the way to the Deadmines entrance, and scattered in buildings all over Moonbrook (including the Moonbrook schoolhouse) — no elites need to be fought.",
    '本链的副本段：进本前炸药已由爆炸物筹备段（斯普莱特 → 贾斯伯·菲尔）备齐。安放炸药后从副本出口出来，到月溪镇后方的山丘与阿尔巴·晴月会合。◎ 熔炉即吉尔尼德所在的房间，靠近中央安放炸药；跑完这段别用炉石——从副本后门出去，在后门入口继续任务。':
        "The dungeon segment of the chain: before entering, the explosives are already prepared by the materiel phase (Sprite Jumpsprocket → Jasper Fel). After planting them, exit the dungeon and meet Alba Fairmoon on the hill behind Moonbrook. ◎ The forge is the room where Gilnid spawns — plant the explosives near the center; after this run do NOT hearth out: leave through the back door and continue the quest at the back entrance.",
    '起始在副本内（「洛丹伦纹章」在副本里有多处刷新点，拾取即开启）；交任务要回暴风城找德娜·肯尼迪。◎ 小地图上没有叹号提示，要自己找。已知刷新点：蜘蛛庭院旁的塔顶、被遗弃者旁的塔顶、蜘蛛庭院里女妖看守的门后、比约克庭院对面锁门房间的地面。':
        "Starts inside the dungeon (the 'Crest of Lordaeron' has multiple spawn points; looting one starts the quest); turn in back in Stormwind City with Lady Dena Kennedy. ◎ No '!' shows on the minimap — you have to search yourself. Known spawn points: top of the tower by the spider courtyard, top of the tower by The Abandoned, behind the door guarded by the banshee in the spider courtyard, and on the floor of the locked-door room across from Bjork's courtyard.",
    '图曼上尉（联盟军需官，对部落敌对）就在进本左手边；目标要取男爵的头颅，打完男爵别急着走；交任务也找他本人。':
        "Captain Truman (Alliance quartermaster, hostile to the Horde) is on the left as you enter the dungeon; the objective is the Baron's head — don't rush out after killing him; turn the quest in to Truman himself.",
    '在副本内戴温的遗体上直接接取。': "Starts on Dewin's corpse inside the dungeon.",
    '完成「灌木丛里的东西」后阿尔丁给的信物编草心（Reed-woven Heart）开启本任务。': "Started by the Reed-woven Heart, a token Aldin gives after completing the shrub-search quest.",
    '拾取泰坦圣物开启；联盟方交给维尔加挖掘场的勘察员维尔加。': "Started by looting the Titan Relic; the Alliance turn-in is Prospector Whelgar at Whelgar's Excavation Site.",
    '拾取开启：需先从丹莫罗东南角的黑铁矮人（约 77,60）身上拾取「黑铁地图」，交给大地先知法森后才接到本任务。':
        "Pick-up start: first loot the 'Dark Iron Map' from the Dark Iron dwarves in the southeast corner of Dun Morogh (about 77,60) and hand it to Earthseer Farsen — only then is this quest offered.",
    '一趟即可完成。目标 NPC 在高层王座（国王房间）左转进入的新增副本入口区。':
        "Easily completed in one run. The target NPC is in the newly added dungeon-entrance area to the LEFT of the High Seat (the king's room).",
    '任务在副本内接取并交付。':
        "The quest starts and ends inside the dungeon.",
    '任务物品散落在副本各处，外观并不统一，要把鼠标扫过墙边、椅子、桌子逐个搜；尾王金库后的房间最密集。':
        "The quest items are sprinkled all over the dungeon and don't all look the same — run your mouse over walls, chairs and tables to spot them; the room behind the last boss's vault has the highest concentration.",
    '起始在副本内（男爵掉落的「憎恶的头颅」，拾取即开启）；交任务回幽暗城找大药剂师法拉尼尔。◎ 头颅任务可共享（队友接受后头颅直接进包）。使用任务物品的位置：右侧楼梯上去的绿色软泥池边（炼金区旁的大蠕虫处）。':
        "Starts inside the dungeon (the 'Abomination's Head' dropped by The Baron — looting it starts the quest); turn in back in Undercity with Master Apothecary Faranell. ◎ The head quest can be shared (accepting puts the head straight into party members' bags). Use the quest item at the green ooze pool up the stairs to the right (by the big worm outside the Apothecarium).",
    '大法师奥尔韦克':
        'Magus Olvek',
    '萨鲁克':
        'Zaruk',
    '亡灵卫兵密探':
        'Deathstalker Agent',
    '从血色修道院取回《符文大师的失落魔法》，交给奥特兰克山脉的大法师奥尔韦克。':
        'Retrieve "The Lost Magic of the Runemasters" from the Scarlet Monastery and bring it to Magus Olvek in the Alterac Mountains.',
    '书在图书馆尾王奥法师杜安房间右侧的桌上（红色书）。':
        "The book is on the table on the right side of Arcanist Doan's chamber, the last boss of the Library — it's the red book.",
}
QUESTS2.update(QUESTS2B)
