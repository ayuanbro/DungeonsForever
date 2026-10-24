# -*- coding: utf-8 -*-
"""纯文本备注/目标散文层（Data_DungeonQuests 自由文本，2026-09-25 人工翻译）。

键 = 数据里的完整中文字符串（与 _enus_hand4.txt 逐条对应）；
专有名词全部用官方英文名（fetch8~19 ID 级核实 + 既有 EXACT 既定译法）。
gen_enus_data.py 在 HAND 之后并入 EXACT，优先级最高。
"""

FREE = {
    '流程较长：先杀 4 个德鲁伊并完成护送，最终 首领『吞噬者』穆坦努斯才会出现；杀他拿到发光的碎片。之后回棘齿城找那个地精（做《什么什么平衡器》的那位）说话——他头上没有问号，要自己点他——再回哀嚎洞外的山顶找菲拉·古风。':
        'Long chain: kill the 4 druids and complete the escort first — only then will the final boss, Mutanus the Devourer, appear; kill him for the Glowing Shard. Then return to Ratchet and talk to that goblin (the one behind that "something-or-other Equalizer" quest) — he has no question mark over his head, click him yourself — then head back to the mountaintop outside Wailing Caverns to find Falla Sagewind.',
    '尼科瓦·拉斯克在旧城区一带走动；监狱里的敌人基本都会掉面罩。':
        'Nikova Raskov wanders around Old Town; nearly every enemy in the Stockade drops a mask.',
    '密室在副本内。开门流程：从鲁维罗什拿索尔之杖，从巴尔洛戈的箱子拿尼基夫徽章，合成史前法杖；再到两间房之间的地图室召唤艾隆纳亚，击败后进入密室。':
        'The Hidden Chamber is inside the instance. Opening procedure: get the Shaft of Tsol from Revelosh and the Gni\'kiv Medallion from Baelog\'s chest, combine them into the Staff of Prehistoria; then use it in the Map Room between the two halls to summon Ironaya — defeat her and enter the Hidden Chamber.',
    '到奥达曼找到巴尔洛戈。':
        'Find Baelog inside Uldaman.',
    '巴尔洛戈在副本内。':
        'Baelog is inside the instance.',
    '接任务后先与石头守护者旁的圆盘对话，再用白金圆盘取得缩小版，交给资深探险家麦格拉斯（铁炉堡 - 探险者大厅 69,18）。后续任务在旁边 NPC 处接。':
        'After taking the quest, first talk to the disc next to the Stone Watcher, then use the Platinum Disc to obtain the miniature version and hand it to High Explorer Magellas (Ironforge - Hall of Explorers 69,18). Follow-up quests are taken from the NPCs nearby.',
    '德鲁伊职业任务。藤蔓由召唤出的阿塔拉利恩掉落，需要先正确破解雕像群的秘密。':
        'Druid class quest. The vines drop from the summoned Atal\'alarion — you must first solve the secret of the statue cluster correctly.',
    '弗兰克罗恩在黑石中心、自己墓穴的上方——需要先死亡变成鬼魂才能与他对话，对话两次激活任务。弗诺斯·达克维尔在副本内，神殿在副本内。':
        'Franclorn Forgewright is at the center of Blackrock Mountain, above his own tomb — you must first die and become a ghost to talk to him; talk twice to activate the quest. Vornus Darkvale is inside the instance, and so is the shrine.',
    '需要超维度幽灵显形器才能看到伯德雷（从《寻找安泰恩》获得）。伊萨莉恩在副本内召唤。':
        'You need the Extraplanar Ghost Revealer to see Bodley (from "Finding Anthion"). Isalien is summoned inside the instance.',
    '修复这个陷阱。':
        'Repair the trap.',
    '可重复任务。修复需要 [瑟银零件] 和一瓶 [冰霜之油]。':
        'Repeatable. Repairing it requires a [Thorium Widget] and a vial of [Frost Oil].',
    '把 4 卷符文布、8 块硬甲皮、2 卷符文线和一份食人魔鞣酸交给被拴在厄运之槌戈多克食人魔区的诺特·希姆加克。':
        'Bring 4 Runecloth, 8 Rugged Leather, 2 Rune Thread and an Ogre Tannin to Nott Shimjak, who is chained up in the Gordok ogre area of Dire Maul.',
    '可重复任务。食人魔鞣酸在副本上层附近获取。':
        'Repeatable. The Ogre Tannin is obtained near the upper part of the instance.',
    '找到戈多克力量护手，交给厄运之槌的克罗卡斯。':
        'Find the Gauntlet of Gordok Might and bring it to Captain Kromcrush in Dire Maul.',
    '王子在厄运之槌西；力量护手在他附近的箱子里。交任务时也要带着「当国王真好」状态。':
        'The Prince is in Dire Maul West; the Gauntlet of Gordok Might is in the chest near him. You must also carry the "Good to be King" buff when turning in.',
    '替诺特找到食人魔镣铐钥匙。':
        'Find the ogre shackle key for Nott.',
    '可重复任务，副本里所有食人魔都可能掉。':
        'Repeatable; every ogre in the instance can drop it.',
    '到厄运之槌找到卡里尔·温萨鲁斯，向莫沙彻营地的先知科鲁拉克报告你查到的东西。':
        'Find Kariel Winthalus in Dire Maul, then report what you have learned to Sage Korolusk at Camp Mojache.',
    '卡里尔·温萨鲁斯在厄运之槌西区的图书馆。':
        'Kariel Winthalus is in the library of Dire Maul West.',
    '到厄运之槌找到卡里尔·温萨鲁斯，向羽月要塞的学者卢索恩·纹角报告你查到的东西。':
        'Find Kariel Winthalus in Dire Maul, then report what you have learned to Scholar Runethorn at Feathermoon Stronghold.',
    '击破维持伊莫塔尔监狱的五座水晶塔周围的守卫，削弱水晶塔能量让力场消散；进监狱杀掉中间的恶魔；最后在图书馆挑战托塞德林王子。完成后到庭院找辛德拉古灵。':
        'Kill the guards around the five crystal pylons that keep Immol\'thar imprisoned and drain the pylons until the force field collapses; enter the prison and kill the demon at its center; finally challenge Prince Tortheldrin in the library. When done, find the Shen\'dralar Ancient in the courtyard.',
    '水晶塔、伊莫塔尔、托塞德林王子都在副本内，水晶塔要先关闭':
        'The crystal pylons, Immol\'thar and Prince Tortheldrin are all inside the instance; the pylons must be shut down first.',
    '阅读莫苏尔的指南，召唤克索诺斯恐惧战马，击败它并控制它的灵魂。':
        "Read Mor'zul's instructions, summon the Dreadsteed of Xoroth, defeat it and bind its soul.",
    '术士史诗战马的最后一步：先关闭水晶塔、杀掉伊莫塔尔，然后才能召唤。备好 20 个以上灵魂碎片——维持法阵要持续消耗。杀掉战马后与马的灵魂对话完成任务。':
        "The final step of the warlock epic steed: shut down the crystal pylons and kill Immol'thar before you can summon. Bring at least 20 Soul Shards — maintaining the ritual circle consumes them continuously. After killing the steed, talk to its spirit to complete the quest.",
    '到通灵学院取回巴罗夫家族的四份地契（凯尔达隆、布瑞尔、塔伦米尔、南海镇），交回阿莱克斯·巴罗夫。':
        'Recover the four Barov family deeds from Scholomance (Caer Darrow, Brill, Tarren Mill and Southshore) and return them to Alexi Barov.',
    '地契位置：凯尔达隆、布瑞尔、塔伦米尔、南海镇。':
        'Deed locations: Caer Darrow, Brill, Tarren Mill and Southshore.',
    '到通灵学院取回巴罗夫家族的四份地契（凯尔达隆、布瑞尔、塔伦米尔、南海镇），交回维尔顿·巴罗夫。':
        'Recover the four Barov family deeds from Scholomance (Caer Darrow, Brill, Tarren Mill and Southshore) and return them to Weldon Barov.',
    '在通灵学院找到瑟尔林·卡斯迪诺夫教授，杀掉他并烧毁艾瓦·萨克霍夫与卢森·萨克霍夫的遗体，然后回艾瓦·萨克霍夫处复命。':
        'Find Doctor Theolen Krastinov in Scholomance, kill him and burn the remains of Eva Sarkhoff and Lucien Sarkhoff, then report back to Eva Sarkhoff.',
    '教授在副本内。':
        'The doctor is inside the instance.',
    '带无辜者之血回通灵学院，倒在门廊火盆下引出基尔图诺斯；勇敢迎战，别退缩。杀死他后回艾瓦·萨克霍夫处复命。':
        'Bring the Blood of Innocents back to Scholomance and pour it into the brazier on the porch to draw out Kirtonos the Herald; face him bravely and do not flinch. Kill him and report back to Eva Sarkhoff.',
    '门廊在副本内。':
        'The porch is inside the instance.',
    '在通灵学院击败詹迪斯·巴罗夫，从尸体上取得卡斯迪诺夫的恐惧之袋，交给艾瓦·萨克霍夫。':
        'Defeat Jandice Barov in Scholomance, take Krastinov\'s Bag of Horrors from her corpse and bring it to Eva Sarkhoff.',
    '詹迪斯·巴罗夫在副本内。':
        'Jandice Barov is inside the instance.',
    '击杀 20 只瘟疫龙崽，回圣光之愿礼拜堂向贝蒂娜·比格辛克复命。':
        "Kill 20 Plague Dragon Whelps and report back to Betina Bigglezink at Light's Hope Chapel.",
    '瘟疫龙崽在尸骨储藏所——去往血骨傀儡的大房间那片。':
        'The Plague Dragon Whelps are in the bone vault — the big chamber on the way to the Bloodbone Golem.',
    '把健康的龙鳞交给东瘟疫之地圣光之愿礼拜堂的贝蒂娜·比格辛克。':
        "Bring the Healthy Dragon Scale to Betina Bigglezink at Light's Hope Chapel in Eastern Plaguelands.",
    '健康的龙鳞由瘟疫龙崽掉落（约 8%）。贝蒂娜·比格辛克在东瘟疫之地 - 圣光之愿礼拜堂（76,54）。':
        "The Healthy Dragon Scale drops from Plague Dragon Whelps (about 8%). Betina Bigglezink is at Light's Hope Chapel, Eastern Plaguelands (76,54).",
    '把黎明先锋放到通灵学院的观察室，击败维克图斯后回贝蒂娜·比格辛克处复命。':
        "Place the Dawn's Gambit in the Viewing Room of Scholomance, defeat Vectus, then report back to Betina Bigglezink.",
    '前置「雏龙精华」始于丁奇·斯迪波尔（燃烧平原 - 烈焰峰 65,23）。观察室在副本内。':
        'The prerequisite "Wyrmheart" starts at Tinkee Steamboil (Burning Steppes - Flame Crest 65,23). The Viewing Room is inside the instance.',
    '在通灵学院找到莱斯·霜语，用禁锢灵魂的遗物破除他的亡灵外壳，成功后杀掉他，把头颅交给马杜克镇长。':
        'Find Ras Frostwhisper in Scholomance and use the Soulbound Keepsake to break his undead shell; once it works, kill him and bring his head to Magistrate Marduke.',
    '莱斯·霜语在副本内。':
        'Ras Frostwhisper is inside the instance.',
    '在通灵学院地下室的尸骨储藏所中心使用预言水晶球，击败召唤出的幽灵；死亡骑士达克雷尔现身后再击败他，把头颅交给奥格瑞玛智慧谷的萨格尼。':
        "Use the Divination Scryer at the center of the bone vault in Scholomance's basement and defeat the summoned ghosts; when Death Knight Darkreaver appears, defeat him too and take his head to Sagorne Creststrider in the Valley of Wisdom, Orgrimmar.",
    '萨满祭司专属任务，前置接自同一 NPC。达克雷尔在副本内召唤。':
        'Shaman-only quest; the prerequisite is taken from the same NPC. Darkreaver is summoned inside the instance.',
    '把瓶中的小鬼带到通灵学院的炼金实验室，等它造出羊皮纸后把瓶子还给戈瑟奇·邪眼。':
        'Take the imp in the bottle to the alchemy lab in Scholomance; once it produces the parchment, return the bottle to Gorzeeki Wildeyes.',
    '仅术士可接！炼金实验室在副本内。':
        'Warlocks only! The alchemy lab is inside the instance.',
    '到斯坦索姆杀死红衣铸锤师，把他的围裙交给莉莉丝。':
        'Kill the Crimson Hammerer in Stratholme and bring his apron to Lilith the Lithe.',
    '红衣铸锤师靠召唤出现。':
        'The Crimson Hammerer is summoned.',
    '在斯坦索姆找到黑衣守卫铸剑师并杀掉，把黑色卫士徽记交给亡灵杀手瑟里尔。':
        'Find and kill the Black Guard Swordsmith in Stratholme and bring the Black Guard Medallion to Seril Scourgebane.',
    '黑衣守卫铸剑师靠召唤出现。':
        'The Black Guard Swordsmith is summoned.',
    '到斯坦索姆的血色十字军堡垒找回名画「爱与家庭」——它藏在另一幅双月之画的后面——把画归还给提里奥·弗丁。':
        'Recover the famous painting "Of Love and Family" from the Scarlet Bastion in Stratholme — it is hidden behind another painting of twin moons — and return it to Tirion Fordring.',
    '前置从提里奥·弗丁处接（西瘟疫之地 7,43）。画在副本内。':
        'The prerequisite is taken from Tirion Fordring (Western Plaguelands 7,43). The painting is inside the instance.',
    '击杀瑞文戴尔男爵。':
        'Kill Baron Rivendare.',
    '先给奥里克斯 [信仰奖章]（奖章在副本内的玛洛尔保险箱里）；他会加入对抗男爵的战斗但会倒下。杀死男爵后与尸体对话完成任务。':
        "First give Aurius [Aurius' Reckoning] (the medallion is inside Malor's Strongbox in the instance); he will join the fight against the Baron but will fall. After killing the Baron, talk to his corpse to complete the quest.",
    '从斯坦索姆找回 20 个瘟疫肉块，交给贝蒂娜·比格辛克。':
        'Recover 20 Plagued Flesh Samples from Stratholme and bring them to Betina Bigglezink.',
    '斯坦索姆大部分敌人都会掉肉块，但掉率偏低。':
        'Most enemies in Stratholme drop the flesh samples, but the drop rate is low.',
    '到斯坦索姆探索通灵塔，找到新的天灾军团档案交给贝蒂娜·比格辛克。':
        'Search the ziggurats of Stratholme for the new Scourge archive and bring it to Betina Bigglezink.',
    '档案在、、 三座塔中的一座里。':
        'The archive is in one of the three towers.',
    '在斯坦索姆找到弗拉斯·希亚比的烟草店，取回一盒希亚比的烟草交给烟鬼拉鲁恩。':
        "Find Fras Siabi's tobacco shop in Stratholme, retrieve a box of Siabi's Tobacco and bring it to Smokey LaRue.",
    '烟草店在副本内；开盒的瞬间弗拉斯·希亚比会现身。':
        'The tobacco shop is inside the instance; Fras Siabi appears the moment you open the box.',
    '前往斯坦索姆，搜刮城中散落的补给箱，收集 5 瓶斯坦索姆圣水，回莱尼德·巴萨罗梅处复命。':
        'Head to Stratholme, loot the supply crates scattered around the city, collect 5 Stratholme Holy Water and report back to Leonid Barthalomew the Revered.',
    '圣水在城中各处的箱子里；部分是假箱，打开会钻出一堆虫子。':
        'The holy water is in crates all over the city; some are fakes that burst open with a swarm of bugs.',
    '在斯坦索姆找到血色十字军的档案管理员加尔福特，杀掉并烧毁血色十字军档案。':
        "Find the Scarlet crusade's Archivist Galford in Stratholme, kill him and burn the Scarlet Crusade archives.",
    '档案与档案管理员都在副本内。':
        'Both the archives and the archivist are inside the instance.',
    '把巴纳扎尔的头颅交给东瘟疫之地的尼古拉斯·瑟伦霍夫公爵。':
        "Bring Balnazzar's head to Duke Nicholas Zverenhoff in Eastern Plaguelands.",
    '公爵在东瘟疫之地 - 圣光之愿礼拜堂（76,52）。':
        "The duke is at Light's Hope Chapel, Eastern Plaguelands (76,52).",
    '到斯坦索姆击杀瑞文戴尔男爵，把头颅交给尼古拉斯·瑟伦霍夫公爵。':
        'Kill Baron Rivendare in Stratholme and bring his head to Duke Nicholas Zverenhoff.',
    '男爵在副本内。此任务有后续任务给奖励。':
        'The Baron is inside the instance. This quest has a follow-up that grants the reward.',
    '对斯坦索姆的鬼魂居民使用埃根的冲击器；灵魂脱离躯壳后再用一次，让它们彻底安息。解放 15 个永不安息的灵魂后回埃根处复命。':
        "Use Egan's Blaster on the ghostly residents of Stratholme; use it once more after their souls leave the bodies to put them to rest for good. Free 15 Restless Souls and report back to Egan.",
    '前置从护理者奥林处接（东瘟疫之地 - 圣光之愿礼拜堂 74,58）。鬼魂居民在城中到处游荡。':
        "The prerequisite is taken from Caretaker Alen (Eastern Plaguelands - Light's Hope Chapel 74,58). The ghostly residents wander all over the city.",
    '到斯坦索姆击杀吞咽者拉姆斯登，把头颅交给纳萨诺斯。':
        'Kill Ramstein the Gorger in Stratholme and bring his head to Nathanos.',
    '前置同样在纳萨诺斯处接。拉姆斯登在副本内。':
        'The prerequisite is likewise taken from Nathanos. Ramstein is inside the instance.',
    '到斯坦索姆找到米奈希尔的礼物，把巫妖生前的遗物放在那块邪恶的土地上。':
        "Find Menethil's Gift in Stratholme and place the lich's mortal remains on that evil ground.",
    '前置从马杜克镇长处接（西瘟疫之地 - 凯尔达隆 70,73）。标记在副本内。另见通灵学院的「巫妖莱斯·霜语」。':
        'The prerequisite is taken from Magistrate Marduke (Western Plaguelands - Caer Darrow 70,73). The marker is inside the instance. See also "The Lich, Ras Frostwhisper" of Scholomance.',
    '进入斯坦索姆，从瑞文戴尔男爵手中救出伊思达。':
        'Enter Stratholme and rescue Ysida Harmon from Baron Rivendare.',
    '伊思达·哈尔蒙就站在副本门口，需要超维度幽灵显形器才能看到他。前置：联盟找德莉亚娜（铁炉堡 43,52），部落找莫克瓦尔（奥格瑞玛 38,37）。这也是著名的「45 分钟瑞文戴尔」任务。':
        'Ysida Harmon stands right at the instance entrance; you need the Extraplanar Ghost Revealer to see her. Prerequisite: Alliance talks to Deliana (Ironforge 43,52), Horde to Mokvar (Orgrimmar 38,37). This is also the famous "45-minute Baron" run.',
    '在 15 个农夫被杀之前拯救 50 个农夫，完成后与艾瑞斯·哈文法谈谈。拯救进度可以看死亡布告。':
        'Save 50 farmers before 15 of them are killed, then talk to Eris Havenfire when done. The death notices show your rescue progress.',
    '见到艾瑞斯·哈文法并接任务需要神圣之眼（火焰之王的宝箱，熔火之心出）。完成后把神圣之眼、诺达希尔碎片和暗影之眼（诅咒之地/冬泉谷随机恶魔掉落）组合，得到牧师史诗法杖——祈福。':
        'You need the Eye of Divinity (from the chest of the Firelord in Molten Core) to meet Eris Havenfire and take the quest. On completion, combine the Eye of Divinity, the Splinter of Nordrassil and the Eye of Shadow (random demon drops in Blasted Lands / Winterspring) to obtain the priest epic staff — Benediction.',
    '塔纳利斯时光之穴的阿纳克洛斯要你前往斯坦索姆，在神圣之地上使用埃提耶什、守护者的传说之杖，击败被驱赶出来的生物后回他那里复命。':
        'Anachronos of the Caverns of Time in Tanaris wants you to travel to Stratholme, use Atiesh, Greatstaff of the Guardian on the hallowed ground, defeat the creatures driven out, then report back to him.',
    '召唤位置在副本内。巫妖王之怒资料片中无法再获得此任务；只有「召唤出埃提耶什」这一步仍可完成。':
        'The summoning spot is inside the instance. In the Wrath of the Lich King expansion this quest can no longer be obtained; only the "summon Atiesh" step remains completable.',
    '到黑石塔击杀大酋长雷德·黑手，带着他的头颅返回奥格瑞玛。':
        'Kill Warchief Rend Blackhand in Blackrock Spire and return to Orgrimmar with his head.',
    '雷德·黑手在副本内。':
        'Rend Blackhand is inside the instance.',
    '到黑石塔击杀达基萨斯将军，回麦克斯韦尔元帅处复命。':
        'Kill General Drakkisath in Blackrock Spire and report back to Marshal Maxwell.',
    '达基萨斯将军在副本内。':
        'General Drakkisath is inside the instance.',
    '到黑石塔击杀达基萨斯将军，把他的血交给罗卡鲁。':
        'Kill General Drakkisath in Blackrock Spire and bring his blood to Rokaro.',
    '奥妮克西亚前置的最后一步。达基萨斯将军在副本内。':
        'The final step of the Onyxia prerequisite chain. General Drakkisath is inside the instance.',
    '把艾博希尔之眼交给艾萨拉的海达克西斯公爵。':
        'Bring the Eye of Ebohir to Duke Hydraxis in Azshara.',
    '艾博希尔在副本内。3.0.8 补丁后无法再开启这条任务线；已接到的不受影响，仍可完成。':
        'Ebohir is inside the instance. This quest chain can no longer be started after patch 3.0.8; characters who already have it are unaffected and can still complete it.',
    '黑手的命令掉落自（副本入口地图）裂盾军需官。':
        "Blackhand's Command drops from the Scarshield Quartermaster (on the dungeon entrance map).",
    '真是头蠢兽人——找到那枚烙印，拿到达基萨斯徽记，才能使用命令宝珠。':
        "What a dim-witted orc — find the brand and obtain Drakkisath's Badge before you can use the Orb of Command.",
    '黑翼之巢的进门任务。裂盾军需官在黑石塔副本门口右侧附近；宝珠在达基萨斯将军身后。':
        'The Blackwing Lair attunement quest. The Scarshield Quartermaster is near the right side of the Blackrock Spire entrance; the orb is behind General Drakkisath.',
    '把黑暗石板交给卡加斯的暗法师薇薇安·拉格雷。':
        'Bring the Darkstone Tablet to Shadowmage Vivian Lagrave in Kargath.',
    '前置可从药剂师金格接（幽暗城 - 炼金房 50,68）。石板在烈焰之父的房间。':
        "The prerequisite can be taken from Apothecary Zinge (Undercity - Apothecarium 50,68). The tablet is in the Father Flame's room.",
    '黑铁地图（黑铁间谍掉落，丹莫罗 77,60）':
        'Dark Iron map (dropped by Dark Iron Spies, Dun Morogh 77,60)',
    '洛丹伦废城地下的亡灵废墟：6 个 boss、非线性流程，多数玩家的头几个副本之一。':
        'Undead ruins beneath the ruined city of Lordaeron: six bosses, a non-linear layout, and one of the first dungeons most players meet.',
    '非线性副本：6 个 boss 可以任意顺序挑战，漏掉某个 boss 不卡流程。':
        'Non-linear dungeon: the six bosses can be tackled in any order, and skipping one does not block progress.',
    '邪恶的维克托是隐藏 boss —— 在洛丹伦墓地旁、洛丹米尔眺望台西南建筑的烟囱处点燃炉火，先清 5 波小怪才会现身；beta 上偶尔不刷。':
        'Viktor the Vile is a hidden boss — light the fire in the chimney of the building southwest of Lordamere Overlook and clear five add waves before he appears; he sometimes fails to spawn on the beta.',
    '灵魂医者就在副本门口，团灭后跑尸路程很短。':
        'The Spirit Healer stands right outside the entrance, so the corpse run after a wipe is very short.',
    '任务在 17 级时仍显示为红色，但副本本身 17 级就能打通。':
        'The quests still show as red at level 17, but the dungeon itself is clearable at that level.',
    '怪物密度高，很容易连着拉到好几群；没有控制技能时低等级会比较吃力。':
        'Mob density is high and it is easy to pull several packs in a row; without crowd control, low levels will struggle.',
    '在幽暗城正上方的非副本区洛丹伦废墟就能找到入口（提瑞斯法林地，布瑞尔以南）。':
        'The entrance sits in the non-instanced Ruins of Lordaeron directly above the Undercity (Tirisfal Glades, south of Brill).',
    '暴风城法师塔有通往达拉然的传送门，解锁后可直接传送过去、跳过前面几步海路；':
        'Players with the Stormwind Mage Tower portal to Dalaran unlocked can teleport straight there and skip most of the sea voyage;',
    '从暴风城港口坐船到奥伯丁；':
        'Take the boat from Stormwind Harbor to Auberdine;',
    '在奥伯丁码头另一侧换船到米奈希尔港；':
        "on the far side of Auberdine's port, take the boat to Menethil Harbor;",
    '继续坐这班船到希尔斯布莱德丘陵的南海镇；':
        'stay on that boat until it reaches Southshore in Hillsbrad Foothills;',
    '沿路从南海镇走到希尔斯布莱德农场，再北上绕过达拉然；':
        'follow the road from Southshore to Hillsbrad Fields, then head north around Dalaran;',
    '往北游过银松森林的洛丹米尔湖，进入提瑞斯法林地；':
        'swim north across Lordamere Lake in Silverpine Forest into Tirisfal Glades;',
    '沿路走到洛丹伦废墟入口。':
        'follow the road to the Ruins of Lordaeron entrance.',
    '蛛魔区':
        'Spider wing',
    '入口一带的蛛魔成组分布、还会巡逻。单群不难，麻烦的是拉怪时连带把巡逻群也引过来 —— 多盯着点，往回收着拉。':
        'The spiders near the entrance come in packs and patrol. A single pack is easy; the trouble is pulling a patrolling pack along with it — keep an eye out and pull packs back toward you.',
    '骷髅士兵与女妖':
        'Skeletal Soldiers and Banshees',
    '骷髅士兵在男爵一带巡逻，女妖会沉默；成群时伤害很足。用眩晕类控制让这几群好处理不少。':
        'Skeletal Soldiers patrol near the Baron and the Banshees can silence; in groups they hit hard. Stun-type crowd control makes these packs much easier.',
    '血肉魔像':
        'Flesh Golems',
    '伤害很高，还会击飞并降低仇恨。拉它们时注意站位，别被击飞到旁边的怪群里 —— 它们巡逻的洛丹米尔眺望台周围小怪很多。':
        'They hit hard and have a knock-away that also reduces threat. Watch your positioning when you pull them so you are not knocked into another pack — the Lordamere Overlook they patrol is dense with trash.',
    '食尸鬼':
        'Ghouls',
    '3~4 只一组，近战挥砍很重，而且和其它怪群挨得很近，极易连环拉。别贪，一次拉太多坦克和治疗会顶不住。':
        'Packs of 3–4 with heavy melee swings, packed right next to other groups, so it is very easy to chain-pull. Do not get greedy — too many at once will overwhelm the tank and healer.',
    '在国王巷巡逻，坦克拉住打掉即可。身边带两只蛛魔，先把它们秒掉；有晕就晕，坦克中了吸血毒药记得驱散。':
        "Patrols King's Alley — a simple tank-and-spank. He brings two spiders, so kill those first, stun whenever you can, and dispel Leech Poison off the tank.",
    '伤害很高，只有击昏一个技能：高额瞬发伤害并降低仇恨。坦克不满血时可能被直接打死，尽量用晕打断它的施法。':
        'Hits hard and has only one ability, Knockout: heavy instant damage plus a threat drop. He can kill the tank outright if the tank is not at full health — stun him out of the cast whenever possible.',
    '隐藏 boss，位置在洛丹伦墓地旁、洛丹米尔眺望台西南建筑的烟囱里 —— 点燃炉火后先清 5 波小怪才会现身。它只有强力近战和吸血毒药，让坦克先建立仇恨。beta 上偶尔不刷。':
        'Hidden boss located in the chimney of the building southwest of Lordamere Overlook — light the fire and clear five add waves before he appears. He has only heavy melee and Leech Poison, so let the tank build aggro first. He sometimes fails to spawn on the beta.',
    '从洛丹米尔眺望台进市集街就能遇到。区域里的雕像会先触发 3 波小怪。它会冰霜新星、对近战命中者附加冰冷效果，并对坦克施放生命吸取 —— 在读条结束前打断或眩晕它。':
        'Found as soon as you enter Market Street from Lordamere Overlook. The statues in the area trigger three add waves first. He casts Frost Nova, applies a chill to anyone who lands melee hits on him, and casts Drain Life on the tank — interrupt or stun him before the cast finishes.',
    '只有一个很短的反魔法护盾，盾一破就是纯木桩，最好打的 boss。':
        'Has only a very short Anti-Magic Shell, and once it drops he is a plain tank-and-spank — the easiest boss here.',
    "只会烈焰风暴：他开始读条就往旁边挪 —— 落点永远是他起手时坦克所在的位置；用晕可以让他完全放不出来。":
        'Has only Flamestrike: start moving as soon as he begins the cast — it always lands where the tank stood when the cast started; a stun can stop him from casting it at all.',

# ── 领主大厅（hall_of_thanes）攻略（2026-09-30，wowhead 内容人工翻译）──
    '铁炉堡旧铁炉堡深处的矮人殿堂：4 个 boss、流程线性，联盟玩家的早期副本之一。':
        'A dwarven hall deep inside Old Ironforge beneath Ironforge: four bosses in a linear layout, and one of the early dungeons for Alliance players.',
    '副本就在铁炉堡王座厅后方的旧铁炉堡里，进门即本；灵魂医者也在副本门口，跑尸路程很短。':
        "The dungeon sits right inside Old Ironforge behind Ironforge's throne room — no walk to speak of, and the Spirit Healer is at the entrance too, so corpse runs are very short.",
    '黑铁工程师的炸弹在抬手投掷时就锁定了落点，看到起手就侧移，伤害可以 100% 躲掉。':
        'Dark Iron Engineer bombs lock their landing spot as soon as the throw starts — sidestep when you see the wind-up and the damage is 100% avoidable.',
    '小型石魔伤害极高、还会加速，尽量一次只拉一只；拉到多只时逐个击杀、别分散伤害。':
        'Lesser Stone Golems hit extremely hard and move faster — pull one at a time whenever possible; when you pull several, kill them one by one instead of splitting damage.',
    '最终房间「诸王圣物库」的宝库里放着任务物品，数量足够全队 5 人各自完成任务。':
        'The vaults in the final room, the Reliquary of Kings, hold enough quest items for all 5 party members to complete their quests.',
    '除《古老的怨恨》与《重要的传家宝》外，本副本任务全部为联盟专属。':
        'Except for An Ancient Grudge and Important Heirlooms, all dungeon quests are Alliance-exclusive.',
    '部落路线较长：从幽暗城出发，经银松森林、希尔斯布莱德丘陵、阿拉希高地进入湿地，再南下穿隧道到丹莫罗，进铁炉堡；副本入口在王座厅后方的旧铁炉堡。':
        'The Horde route is long: from Undercity through Silverpine Forest, Hillsbrad Foothills and Arathi Highlands into the Wetlands, then south through the tunnel into Dun Morogh and on to Ironforge; the dungeon entrance is in Old Ironforge behind the throne room.',
    '从暴风城坐地铁到铁炉堡；':
        'Take the tram from Stormwind to Ironforge;',
    '穿过铁炉堡大厅走到王座厅；':
        "Cross Ironforge's great hall to the throne room;",
    '王座厅后方的旧铁炉堡里就是副本入口。':
        'The dungeon entrance is in Old Ironforge behind the throne room.',
    '黑铁盗宝者与黑铁工程师':
        'Dark Iron Looter and Dark Iron Engineer',
    '开场的怪不难，走到黑铁一方才开始有挑战：盗宝者用匕首快速平砍，一次拉太多会很快打空坦克的血量；工程师会朝目标位置丢炸弹。别贪 —— 低等级时尤其如此；炸弹落点在起手时就定了，完全可以躲开。优先集火盗宝者，他们的伤害又快又致命。':
        "The intro mobs are not too serious, and the trash only gets challenging once you reach the Dark Iron side: Looters deal rapid dagger auto-attacks, and pulling too many at once drains the tank's health fast; Engineers throw bombs at a target location. Do not pull too many — especially at lower levels; the bomb location is locked as the throw starts and is fully avoidable. Focus down the Looters first — their damage is rapid and can be deadly.",
    '黑铁召唤师与烈焰助手':
        'Dark Iron Summoner and Fiery Assistant',
    '召唤师是法系怪，会读火球术并召唤烈焰助手。利用柱子或墙壁卡住视线，让它读不出法术、被迫跑向队伍。':
        'The Summoner is a caster-type mob that casts Fireballs and summons a Fiery Assistant. Use any pillar or wall to break line of sight, preventing the cast and forcing it to run toward the party.',
    '小型石魔':
        'Lesser Stone Golem',
    '伤害极高、移速还快。能一次拉一只就一次；拉到多只时逐个集火，别把伤害摊开。最后一批是召唤师、盗宝者加石魔的组合，建议用控场（如变形术）开局先定住一只，先杀石魔再杀盗宝者；肾击这类昏迷技能同样好用。':
        'They hit extremely hard and move faster. Pull one at a time if you can; when you pull several, focus them down one by one instead of spreading damage. The final pack is a Summoner, a Looter and a Stone Golem — we recommend crowd control (such as Polymorph) so only two are active at the start, killing the Stone Golem first and then the Looter; stuns like Kidney Shot help a lot too.',
    '在安威玛尔休憩地中央巡逻，是简单的坦克拉住打木桩。最要小心的是别让巡逻的他被杂怪顺手带进队伍：先清出一片区域，等他巡逻到你们这边再开怪。他会平砍并施放心灵冲击，还会给坦克上一个持续 10 分钟的安威玛尔诅咒。':
        "Patrols the center of Anvilmar's Rest and is a simple tank-and-spank fight. The main concern is accidentally pulling the boss along with trash as he patrols: clear out a section of the room and wait for him to patrol to your side before pulling. He auto-attacks and casts Mind Blast, and applies a 10-minute Curse of Anvilmar to the tank.",
    '身边带着一名黑铁召唤师，几个技能都很吃治疗。开怪时坦克先把 boss 拉离队伍、集火召唤师 —— boss 会周期性放出类似火焰新星的范围伤害；召唤师倒下后再全力打 boss。他还会对随机玩家施放燃烧。':
        'Accompanied by a Dark Iron Summoner, with a couple of abilities that really put a focus on healing. On pull the tank should drag the boss away from the party while the Summoner is focused — the boss periodically unleashes a Fire Nova-like area attack; once the Summoner is down, burn the boss. He also casts Combust on a random player.',
    '在走廊里巡逻，只有一个技能：击退。把 boss 拉到不会把人击退进其他怪堆的安全区域开怪，全队靠墙或站角落能进一步降低这个机制的风险。':
        "Patrols his hallway with only one ability: a Knockback. Pull the boss in a safe area where nobody gets knocked into other mobs, and have everyone stand against a wall or in a corner to further mitigate the mechanic.",
    '这里的最终头目，身边带着两只小型石魔，房间边缘还有盗宝者。开怪前先清掉所有盗宝者 —— boss 有范围恐惧和撕裂，坦克压力很大。石魔一只一只解决，用好眩晕与恐惧来减轻伤害。':
        'The final encounter here, accompanied by two Lesser Stone Golems with Looters around the edge of the room. Clear all the Looters before starting — the boss has an AoE Fear and a Rend, which is heavy damage on the tank. Take the golems out one by one and use stuns and fears to mitigate damage.',

    # ── 探索页 · 小动物（Data_ExplorePets，2026-10-01）──
    '运河 · 巡逻精英掉落': 'Canals · Rare-elite drop',
    '运河 · 互动获取': 'Canals · Interactive',
    '瀑布顶圆木 · 互动获取': 'Waterfall-top log · Interactive',
    '击杀运河里巡逻的精英「下水道鳄鱼」':
        'Kill the elite patrolling the canal, the Sewer Beast',
    '它有几率掉落「鳄鱼宝宝」；血量厚，建议组队前往':
        "It has a chance to drop the Baby Crocolisk; it is very tanky, so bring a group",
    '向商人「波伊尔」买一份「营养丰富的泥浆怪淤泥」':
        'Buy a Nutritious Slime Sludge from the vendor Boyle',
    '跳进运河，找到正在巡逻的「活泼软泥怪」':
        'Jump into the canal and find the patrolling Excitable Slime',
    '反复对它 /dance，直到它回舞并给出任务':
        'Spam /dance at it until it dances back and offers you a quest',
    '把淤泥交给它 → 获得「活泼软泥怪」。之后对它 /dance 宠物也会跳':
        'Hand it the sludge to get the Excitable Slime. Afterwards /dance at the pet and it dances too',
    '沿路向南穿过草地，跳到瀑布顶的圆木上':
        'Follow the road south across the field and jump onto the log at the top of the waterfall',
    '选中「音乐跃风蛙」使用 /sing，蛙群随即消失':
        'Target a Musical Gustjumper and use /sing; the flock vanishes',
    '点击圆木上出现的青蛙 → 获得「音乐跃风蛙」':
        'Click the frog that appears on the log to get the Musical Gustjumper',
    '下水道鳄鱼': 'Sewer Beast',
    '波伊尔': 'Boyle',
    '营养丰富的泥浆怪淤泥': 'Nutritious Slime Sludge',
    '活泼软泥怪': 'Excitable Slime',
    '音乐跃风蛙': 'Musical Gustjumper',
    # ── 探索页 · 小动物第 4 只（任务 93176「My Little Friends」奖励，2026-10-07）──
    '斯通纳德 · 任务获取': 'Stonard · Quest reward',
    '到斯通纳德找「阿玛丽斯·韦伯」接下任务（需 25 级），她会给你「昆虫学入门工具包」':
        'In Stonard, pick up the quest from Amaryllis Webb (requires level 25); she gives you the Entomology Starter Kit',
    '去荆棘谷北部的风险投资公司营地一带，在树桩上捕捉「树栖狼蛛样本」':
        'Head to the Venture Co. camp in northern Stranglethorn Vale and catch an Arbor Tarantula Sample on a tree stump',
    '去凄凉之地的科多兽坟场，捕捉「剔肉蝎样本」':
        'Go to the Kodo Graveyard in Desolace and catch a Flesh Picker Sample',
    '去阿拉希高地的三个农场一带，捕捉「干草象鼻虫样本」':
        'Go to the farms in the Arathi Highlands and catch a Hay Weevil Sample',
    '集齐三个样本，回斯通纳德交给「阿玛丽斯·韦伯」→ 获得宠物「维维尔·K·尼维尔」':
        'Collect all three samples and return to Stonard, hand them to Amaryllis Webb to receive the pet Weevil K. Neevil',
    '斯通纳德': 'Stonard',
    '阿玛丽斯·韦伯': 'Amaryllis Webb',
    '昆虫学入门工具包': 'Entomology Starter Kit',
    '荆棘谷': 'Stranglethorn Vale',
    '树栖狼蛛样本': 'Arbor Tarantula Sample',
    '凄凉之地': 'Desolace',
    '剔肉蝎样本': 'Flesh Picker Sample',
    '阿拉希高地': 'Arathi Highlands',
    '干草象鼻虫样本': 'Hay Weevil Sample',
    '维维尔·K·尼维尔': 'Weevil K. Neevil',
    # ==== 2026-10-07 · fc 全量核查：新增 3 条任务（92457/96774/8181）====
    '替达拉然城外的大法师莫德拉，击杀城内的觅索残迹（Seeking Remnant）×8、饱和残迹（Saturated Remnant）×8、法力回响（Mana Echo）×8。':
        'For Archmage Modera outside Dalaran, defeat 8 Seeking Remnants, 8 Saturated Remnants and 8 Mana Echoes inside the City of Dalaran.',
    '起始在副本外（大法师莫德拉的影像），开始并结束于同处。三种奥术元素怪都在达拉然城内：觅索残迹、饱和残迹、法力回响。精确坐标待实机核实。': 'Starts outside the instance (Image of Archmage Modera); start & end confirmed to be the same NPC. The three arcane elemental mobs are inside the City of Dalaran: Seeking Remnant, Saturated Remnant, Mana Echo. Exact coordinates pending in-game check.',
    # ==== 2026-10-08 · 达拉然城 7 条任务（fc 页 8 任务补齐）====
    '替暴风城的高阶巫师安多玛斯，消灭达拉然城内的奥术谜团（Arcanic Enigma）。':
        'Slay the Arcanic Enigma inside the City of Dalaran for High Sorcerer Andromath in Stormwind City.',
    '起始并结束于暴风城法师区的高阶巫师安多玛斯。奥术谜团是复苏之路上的精英怪，会沉默 10 秒并召唤奥术法力苗 —— 它与名单里「法力吞噬者/法力元素」占位的对应关系待实机确认。': "Starts and ends with High Sorcerer Andromath in Stormwind's Mage Quarter. The Arcanic Enigma is an elite mob in the city streets that silences for 10 seconds and summons Arcane Manalings — how it maps onto the 'Mana Devourer / Mana Elemental' placeholders in our boss list is pending in-game confirmation. ◎ ",
    '为达拉然城外的大法师莫德拉的影像，取回城内的奥术微粒。':
        'Recover the Arcane Mote inside the City of Dalaran for the Image of Archmage Modera outside the city.',
    '接取并交付都在副本外的大法师莫德拉的影像。前置：南海镇使者雅克的「令人不安的请求」（An Alarming Request）。接本任务即自动发放「达拉然下水道钥匙」。完成后回紫罗兰城堡找大法师塞林德拉（Archmage Celindra）接收尾任务「肯瑞托之友」。': 'Starts and ends at the Image of Archmage Modera outside the instance. Prerequisite: An Alarming Request from Emissary Jacques in Southshore. Taking this quest auto-grants the Dalaran Sewer Key. Afterwards take the follow-up Friend of the Kirin Tor to Archmage Celindra in the Violet Citadel.',
    '为暴风城的莎拉米尔，从达拉然城采回一朵注入邪能的花朵。':
        'Gather a Fel Infused Blossom from the City of Dalaran for Shylamiir in Stormwind City.',
    '起始并结束于暴风城法师区的莎拉米尔。注入邪能的花朵出自城内邪能植被，多半在邪能古树一带 —— 精确掉落来源待实机核实。': "Starts and ends with Shylamiir in Stormwind's Mage Quarter. The Fel Infused Blossom comes from fel vegetation in the city, most likely around the Fel Ancient — exact source pending in-game check.",
    '替塔伦米尔的梅里萨拉，击败达拉然城内的墓穴骑士阿特雷克西斯。':
        'Defeat Atrexis the Grave Knight inside the City of Dalaran for Melisara in Tarren Mill.',
    '起始并结束于塔伦米尔的梅里萨拉。阿特雷克西斯在下水道深处的仪式法阵，BlizzCon 试玩中他会缴械当前目标 —— 坦克被缴械期间注意减伤。': 'Starts and ends with Melisara in Tarren Mill. Atrexis the Grave Knight waits at the ritual circle deep in the sewers — see the guide page for the fight; in the BlizzCon playtest he disarmed the current target, so tanks should mind their mitigation while disarmed. ◎ ',
    '为幽暗城的马丁·费尔本，从达拉然城收集 6 枚开裂的哨兵核心。':
        'Collect 6 Cracked Sentry Cores from the City of Dalaran for Doctor Martin Felben in Undercity.',
    '起始并结束于幽暗城的马丁·费尔本。开裂的哨兵核心多半由城内奥术魔像/哨兵造型怪掉落 —— 精确来源待实机核实。': 'Starts and ends with Doctor Martin Felben in Undercity. The Cracked Sentry Core most likely drops from arcane construct/sentry-type mobs in the city — exact source pending in-game check.',
    '为塔伦米尔的大法师沃迪恩·伍德格莱尔，取回达拉然城内的奥术微粒。':
        'Recover the Arcane Mote inside the City of Dalaran for Magus Wordeen Voidglare in Tarren Mill.',
    '接取并交付都在塔伦米尔的大法师沃迪恩·伍德格莱尔。部落链：城市钥匙（拿钥匙）→ 血染的街道（Blood in the Streets，结束在莫德拉的影像处）→ 本任务 → 精明的谈判（交付在紫罗兰城堡大法师塞林德拉处）。接本任务即自动发放「达拉然下水道钥匙」。': 'Starts and ends with Magus Wordeen Voidglare in Tarren Mill. Horde chain: Key to the City (get the key) -> Blood in the Streets (ends at the Image of Archmage Modera) -> this quest -> Shrewd Negotiations (turn-in at Archmage Celindra in the Violet Citadel). Taking this quest auto-grants the Dalaran Sewer Key. ◎ ',
    '从达拉然城取回《达拉然的建立》，交给下水道入口附近的雷克西·铜钳。':
        'Retrieve the Founding of Dalaran from the City of Dalaran and bring it to Rexxie Copperclutch near the sewer entrance.',
    '发布者雷克西·铜钳守在下水道入口附近，确切位置待实机核实。《达拉然的建立》是队伍中每人都能拾取的任务物品 —— 一队人可各自完成。': 'The giver Rexxie Copperclutch waits near the sewer entrance — exact location pending in-game check. The Founding of Dalaran is a quest item every party member can loot — the whole group can each complete it.',
    '从沉没之城里「最有派头的牧师」身上取回上古古拉巴什神像，交给莫高雷的马祖空。':
        "Recover an Ancient Gurubashi Idol from the most impressive-looking priest in the Drowned City and bring it to Mazu'kon in Mulgore.",
    '起始在副本外（莫高雷 32.4,20.6，疑为雷霆崖）；神像由副本内牧师造型首领掉落。发布者 NPC ID 暂缺，待实机核实。': "Starts outside the instance (Mulgore 32.4,20.6 — probably Thunder Bluff); giver Mazu'kon, start & end are the same NPC; the idol drops from a priest-looking boss inside. ",
    '去塔纳利斯找叶基亚，当面质问哈卡之蛋的下落。':
        "Go to Yeh'kinya in Tanaris and demand to know what happened to the Hakkar egg.",
    '哈卡链收尾一环：热砂港的詹斯·铁靴（66.9,24）接，交任务在旁边的叶基亚（67,22.4）。链：尖啸者的灵魂→摩沙鲁的预言→…→失落的摩沙鲁石板→本任务。': "Final link of the Hakkar chain: start at Prospector Ironboot in Steamwheedle Port (66.9,24), turn in to Yeh'kinya right next to him (67,22.4). Chain: Screecher Spirits -> The Prophecy of Mosh'aru -> ... -> The Lost Tablets of Mosh'aru -> this quest. ",
}
