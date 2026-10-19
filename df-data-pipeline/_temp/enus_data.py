# -*- coding: utf-8 -*-
"""enUS 数据层翻译表：地名 / 副本名 / boss 名 / 令牌 / 类别 / 模式规则 / 精确串。

纪律：校对错译直接改本表重跑 gen_enus_data.py，禁手改产物。
跨文件对查键（副本名、boss 名、类别）共用同一张表，改一处全局一致。
"""
import re

# ── 地名 / 主城（跨文件共用）────────────────────────────────────────────────
ZONES = {
    '东瘟疫之地': 'Eastern Plaguelands', '西瘟疫之地': 'Western Plaguelands',
    '丹莫罗': 'Dun Morogh', '凄凉之地': 'Desolace', '塔纳利斯': 'Tanaris',
    '悲伤沼泽': 'Swamp of Sorrows', '提瑞斯法林地': 'Tirisfal Glades',
    '暴风城': 'Stormwind City', '铁炉堡': 'Ironforge', '奥格瑞玛': 'Orgrimmar',
    '雷霆崖': 'Thunder Bluff', '幽暗城': 'Undercity', '达拉然城': 'City of Dalaran',
    '灰谷': 'Ashenvale', '荒芜之地': 'Badlands', '菲拉斯': 'Feralas',
    '西部荒野': 'Westfall', '贫瘠之地': 'The Barrens', '银松森林': 'Silverpine Forest',
    '赤脊山': 'Redridge Mountains', '湿地': 'Wetlands', '尘泥沼泽': 'Dustwallow Marsh',
    '荆棘谷': 'Stranglethorn Vale', '希尔斯布莱德': 'Hillsbrad',
    '希尔斯布莱德丘陵': 'Hillsbrad Foothills', '洛克莫丹': 'Loch Modan',
    '石爪山脉': 'Stonetalon Mountains', '艾萨拉': 'Azshara',
    '安戈洛环形山': "Un'Goro Crater", '奥特兰克山脉': 'Alterac Mountains',
    '黑石山': 'Blackrock Mountain', '洛丹伦废墟': 'Ruins of Lordaeron',
    '洛丹伦废城': 'Ruins of Lordaeron', '希利苏斯': 'Silithus',
    '诅咒之地': 'Blasted Lands',
    # 2026-09-25 enUS 补齐（NPCLoc / 任务 giverLoc 用）
    '暮色森林': 'Duskwood', '东部王国': 'Eastern Kingdoms', '千针石林': 'Thousand Needles',
    '杜隆塔尔': 'Durotar', '血色修道院': 'Scarlet Monastery', '达纳苏斯': 'Darnassus',
    '辛特兰': 'The Hinterlands', '灼热峡谷': 'Searing Gorge', '黑海岸': 'Darkshore',
    '燃烧平原': 'Burning Steppes', '费伍德森林': 'Felwood', '冬泉谷': 'Winterspring',
    '斯坦索姆': 'Stratholme', '月光林地': 'Moonglade', '艾尔文森林': 'Elwynn Forest',
    '厄运之槌': 'Dire Maul', '奥特兰克山谷': 'Alterac Valley',
}

# ── 子区域 / 城内区（任务 giverLoc「区 - 子区 坐标」规则用，跨文件共用）──────
SUBZONES = {
    # 奥格瑞玛
    '智慧谷': 'Valley of Wisdom', '荣誉谷': 'Valley of Honor', '精神谷': 'Valley of Spirits',
    '暗影裂口': 'Cleft of Shadow', '暗巷区': 'Rogue Quarter',
    # 雷霆崖 / 幽暗城
    '长者高地': 'Elder Rise', '灵魂高地': 'Spirit Rise',
    '皇家区': 'Royal Quarter', '炼金房': 'The Apothecarium', '炼金区': 'The Apothecarium',
    '魔法区': 'Magic Quarter', '军事区': 'The War Quarter',
    # 暴风城 / 铁炉堡 / 达纳苏斯
    '矮人区': 'Dwarven District', '侏儒区': 'Tinker Town', '秘法区': 'Mystic Ward',
    '探险者大厅': 'Hall of Explorers', '荒弃的洞穴': 'The Forlorn Cavern',
    '工匠区': "Craftsmen's Terrace", '战士区': "Warriors' Terrace", '贸易区': 'Trade District',
    '花园': 'The Park', '旧城区': 'Old Town', '监狱': 'The Stockade',
    '光明大教堂': 'Cathedral of Light', '大教堂': 'Cathedral District', '暴风要塞': 'Stormwind Keep',
    # 镇 / 营地
    '哨兵岭': 'Sentinel Hill', '月溪镇': 'Moonbrook', '塞尔萨玛': 'Thelsamar',
    '卡拉诺斯': 'Kharanos', '卡加斯': 'Kargath', '烈焰峰': 'Flame Crest',
    '摩根的岗哨': "Morgan's Vigil", '葬影村': 'Shadowprey Village',
    '尼耶尔前哨站': "Nijel's Point", '圣光之愿礼拜堂': "Light's Hope Chapel",
    '寒风营地': 'Chillwind Camp', '凯尔达隆': 'Caer Darrow', '亡灵壁垒': 'The Bulwark',
    '热砂港': 'Steamwheedle Port', '加基森': 'Gadgetzan', '闪光平原': 'Shimmering Flats',
    '沙漠赛道': 'Mirage Raceway', '羽月要塞': 'Feathermoon Stronghold',
    '莫沙彻营地': 'Camp Mojache', '森金村': "Sen'jin Village", '藏宝海湾': 'Booty Bay',
    '棘齿城': 'Ratchet', '十字路口': 'The Crossroads', '哀嚎洞穴': 'Wailing Caverns',
    '剃刀高地': 'Razorfen Downs', '剃刀沼泽': 'Razorfen Kraul',
    '瑟伯切尔': 'The Sepulcher', '拉文霍德': 'Ravenholdt Manor', '永望镇': 'Everlook',
    '永夜港': 'Nighthaven', '雷姆洛斯神殿': 'Temple of Remulos',
    '马绍尔营地': "Marshall's Refuge", '守望堡': 'Nethergarde Keep',
    '腐烂之痕': 'The Tainted Scar', '斯通纳德': 'Stonard', '塞拉摩岛': 'Theramore Isle',
    '夜色镇': 'Darkshire', '南海镇': 'Southshore', '塔伦米尔': 'Tarren Mill',
    '丹莫德': 'Dun Modr', '铁环挖掘场': "Ironband's Excavation", '湖畔镇': 'Lakeshire',
    '翡翠圣地': 'Emerald Sanctuary', '蛮锤城堡': 'Wildhammer Keep',
    '烈日石居': 'Sun Rock Retreat', '佐拉姆加前哨站': "Zoram'gar Outpost",
    '奥伯丁': 'Auberdine', '时光之穴': 'Caverns of Time',
    # 副本分区（giverLoc 用）
    '墓地': 'Graveyard', '图书馆': 'Library', '军械库': 'Armory',
    '清洁区': 'Clean Zone',   # 诺莫瑞根
    '斯坦索姆': 'Stratholme', '黑石山': 'Blackrock Mountain', '玛拉顿': 'Maraudon',
    # 未知音译（无限服自定义点，wowhead 无对应区名）
    '萨兰纳尔': 'Sarannar', '拉瑞斯小亭': 'The Lariss Pavilion',
    '月溪镇后方山丘': 'the hill behind Moonbrook', '教堂广场': 'Cathedral Square',
}

# ── 副本名（Data_Dungeons 卡墙 + DungeonLoot 来源 + BIS 来源共用）────────────
DUNGEONS = {
    '怒焰裂谷': 'Ragefire Chasm', '死亡矿井': 'The Deadmines',
    '哀嚎洞穴': 'Wailing Caverns', '监狱': 'The Stockade',
    '影牙城堡': 'Shadowfang Keep', '黑暗深渊': 'Blackfathom Deeps',
    '诺莫瑞根': 'Gnomeregan', '剃刀沼泽': 'Razorfen Kraul',
    '剃刀高地': 'Razorfen Downs', '血色修道院：军械库': 'Scarlet Monastery: Armory',
    '血色修道院：图书馆': 'Scarlet Monastery: Library',
    '血色修道院：墓地': 'Scarlet Monastery: Graveyard',
    '血色修道院：大教堂': 'Scarlet Monastery: Cathedral',
    '奥达曼': 'Uldaman', '玛拉顿': 'Maraudon',
    '沉没的神庙': "The Temple of Atal'Hakkar", '沉没之城': 'The Sunken City',
    '厄运之槌：东': 'Dire Maul: East', '厄运之槌：北': 'Dire Maul: North',
    '厄运之槌：西': 'Dire Maul: West', '通灵学院': 'Scholomance',
    '斯坦索姆：正门': 'Stratholme: Main Gate', '斯坦索姆：侧门': 'Stratholme: Service Entrance',
    '黑石塔下层': 'Lower Blackrock Spire', '黑石塔上层': 'Upper Blackrock Spire',
    '黑石深渊': 'Blackrock Depths', '领主大厅': 'Hall of Lords',
    '奥卡兹监狱': 'Prison of Alcaz', '奥卡兹岛，尘泥沼泽': 'Alcaz Island, Dustwallow Marsh',
    '铁炉堡地下，丹莫罗': 'Under Ironforge, Dun Morogh',
    '湿地，维尔加挖掘场上方': 'Wetlands, above the Verga excavation site',
    '挖掘场：湿地': 'Excavation site: Wetlands',
    '艾萨拉的大门之后': 'Beyond the gates of Azshara',
    '荆棘谷近海': 'Off the coast of Stranglethorn',
    '河谷林地（新区域）': 'Riverveil Woods (new zone)',
    '塑造者平台': "The Shaper's Terrace", '克罗多克要塞': 'Krodedor Keep',
    '黑喉要塞': 'Blackthroat Keep',
}

# ── boss / 掉落来源名（DungeonLoot + BIS + Dungeons 共用）────────────────────
BOSSES = {
    '七贤之箱': 'Cache of the Seven', '不可宽恕者': 'The Unforgiven',
    '不稳定的哨兵': 'Unstable Sentinel', '主宰拉姆塔斯': 'Overlord Ramtastis',
    '乌克兹·沙顶': 'Ukkez Sandtop', '乌尔之书': 'Book of Ur', '乌洛克': 'Urok',
    '乔丹的铁锤': "Jordan's Hammer", '亡语者贾格巴': 'Deathspeaker Jargba',
    '亨利·斯特恩': 'Henri Stern', '伊兰尼库斯的阴影': 'Shade of Eranikus',
    '伊森迪奥斯': 'Incendis', '伊琳娜·暗木': 'Illyanna Ravenoak',
    '伊莫塔尔': "Immol'thar", '伊露希亚·巴罗夫': 'Illucia Barov',
    '传令官基尔图诺斯': 'Kirtonos the Herald', '傀儡统帅阿格曼奇': 'Puppetmaster Aggemancur',
    '克罗卡斯': 'Captain Kromcrush', '克雷什': 'Kresh', '兰斯利德': 'Lancelid',
    '典狱官斯迪尔基斯': 'Warden Stilgiss', '军需官兹格雷斯': 'Quartermaster Zigris',
    '剃刀沼泽刺鬃守卫': 'Razorfen Bristleback Guard',
    '加兹瑞拉': "Gahz'rilla", '加加恩·火锤': 'Gargan Firehammer',
    '加摩拉': 'Ghamoo-ra', '博学者普克尔特': 'Lorekeeper Pokult',
    '卡姆·深怒': 'Kam Deepfury', '卡尔加·刺肋': 'Calgar Spinegouge',
    '可怕的塔格尔': 'Targorr the Dread', '哈姆霍克': 'Hamhock',
    '巴基尔·斯瑞德': 'Bazil Thredd', '洛古斯·杰特': 'Lorgus Jett',
    '鲁古格': 'Roogug', '洛丹伦上尉': 'Lordaeron Captain',
    '卡雷迪斯镇长': 'Mayor Caredis', '卫兵摩尔达': "Guard Mol'dar",
    '卫兵斯里基克': "Guard Slip'kik", '卫兵杜格瑞普': 'Guard Duglurk',
    '卫兵芬古斯': 'Guard Fengus', '变异精灵龙': 'Mutated Faerie Dragon',
    '古代的石头看守者': 'Ancient Stone Keeper', '古拉鲁克': 'Gularuk',
    '可悲的奥戈姆': 'Pitiful Ogom', '吞咽者拉姆斯登': 'Swallower Ramsden',
    '吞噬者穆坦努斯': 'Mutanus the Devourer', '吞噬者芬鲁斯': 'Devourer Finrus',
    '哈卡的化身': 'Avatar of Hakkar', '哈卡的后代': 'Spawn of Hakkar',
    '哈扎斯': 'Hazzas', '哈雷肯': 'Hareken', '唤地者哈穆加': 'Earthcaller Halmgar',
    '图特卡什': 'Tutakash', '埃瑞克': 'Eric', '基尔图诺斯的卫士': "Kiltruuk's Guard",
    '基尔尼格': 'Kilnig', '墓穴骑士阿特雷克西斯': 'Tomb Knight Atrexis',
    '奥术谜团': 'Arcanic Enigma', '迪克斯特·瓦德': 'Dextren Ward',
    '大检察官怀特迈恩': 'High Inquisitor Whitemane',
    '大检察官法尔班克斯': 'High Inquisitor Fairbanks',
    '大法师之影': "Archmage's Shade", '大法师阿鲁高': 'Archmage Arugal',
    '大酋长雷德·黑手': 'Warchief Rend Blackhand', '奈鲁布恩坎': "Nerub'enkan",
    '奥兹恩': 'Ozien', '奥拉夫': 'Olaf', '奥术异常体': 'Arcane Aberration',
    '奥格弗林特': 'Oggleflint', '奥法师杜安': 'Arcanist Doan',
    '奥妮克希亚': 'Onyxia',
    '奴役者基兹鲁尔': 'Kizrul the Enslaver', '安图苏尔': "Antu'sul",
    '安娜丝塔丽男爵夫人': 'Baroness Anastari', '安娜科德拉': 'Lady Anacondra',
    '安格弗将军': 'General Angerforge', '审讯员韦沙斯': 'Interrogator Vishas',
    '审讯官格斯塔恩': 'Interrogator Gerstahn', '寒冰之王亚门纳尔': 'Amnennar the Coldbringer',
    '尖石屠夫': 'Sharpstone Butcher', '尖石统帅': 'Sharpstone Overlord',
    '尖石首席法师': 'Sharpstone Chief Mage', '屠夫拉佐克劳': 'Butcher Lazzaklau',
    '工匠吉兹洛克': 'Tinkerer Gizlock', '巫医祖穆拉恩': "Witch Doctor Zum'rah",
    '巴尔洛戈': 'Ballog', '巴尔洛戈的箱子': "Ballog's Chest", '巴扎兰': 'Bazzalan',
    '巴瑟拉斯镇长': 'Mayor Barthilas', '巴纳扎尔': 'Balnazzar',
    '布莱中士': 'Sergeant Bly', '布鲁高·铁拳': 'Brugal Ironfist',
    '席瓦莱恩男爵': 'Baron Silverlaine', '库尔克': 'Kulk',
    '弗莱拉斯大使': 'Ambassador Flamelash', '弗诺斯·达克维尔': 'Vornus Darkvale',
    '弗雷斯特恩': 'Frestain', '德姆塞卡尔': 'Demsekkar', '德拉维沃尔': 'Draviwol',
    '悲惨的提米': 'Wretched Timmy', '意志石板': 'Tablet of Resolve',
    '戈多克大王': 'King Gordok', '托塞德林王子': 'Prince Tortheldrin',
    '拉克佐': 'Lakzo', '拉戈斯诺特': 'Ragnosnaut', '拉文尼亚': 'Lavinia',
    '拉斯玛尔': 'Rasmal', '指挥官斯普林瓦尔': 'Commander Springvale',
    '指挥官沃恩': 'Commander Vohn', '控火师罗格雷恩': 'Pyromaster Rogrean',
    '摩弗拉斯': 'Morvhras', '收割者麦什洛克': 'Reaper Mishlock',
    '斯卡姆': 'Skum', '斯坦索姆信使': 'Stratholme Courier', '斯尼德': 'Sneed',
    '斯尼德的伐木机': "Sneed's Shredder", '斯库尔': 'Shriek',
    '无名先知': 'Nameless Prophet', '无敌的潘佐尔': 'Invincible Panzor',
    '显眼的骨灰罐': 'Conspicuous Urn', '普兰德': 'Pland', '普希林': 'Pusillin',
    '暗影猎手沃什加斯': 'Shadow Hunter Washgus', '暗影祭司塞瑟斯': 'Shadow Priest Sarvis',
    '暗炉宝箱': 'Shadowforge Chest', '暗齿': 'Darkbite',
    '暴怒的阿迦赛罗斯': 'Enraged Agathelos', '暴食者': 'The Glutton', '曲奇': 'Cookie',
    '机械师瑟玛普拉格': 'Mekgineer Thermaplugg', '杉达尔·沙掠者': 'Sandarr Dunereaver',
    '杜安的保险箱': "Doan's Chest", '杜尔根·挽歌之锤': 'Durgan Elegyhammer',
    '杰德': 'Jed', '枯牙': 'Rot Fang', '格瑞姆洛克': 'Grimlok', '格里哈斯特': 'Grihast',
    '格鲁比斯': 'Grubbis', '档案管理员加尔福特': 'Archivist Galford',
    '梦游者克尔里斯': 'Sleepwalker Kerlis', '欧莫克大王': 'King Omokk',
    '死亡之誓': 'Deathsworn', '死亡骑士达克雷尔': 'Death Knight Darkreaver',
    '死灵勇士': 'Necro Champion', '殉教者塞卡': 'Martyr Seka', '比斯巨兽': 'The Beast',
    '比约克': 'Bjork', '水占师维蕾萨': 'Hydromancer Velratha', '水晶之牙': 'Crystal Fang',
    '永生者沃尔丹': 'Vuldan the Eternal', '永醒的艾希尔': 'Echir the Ever-awake',
    '沙怒刽子手': 'Sandfury Executioner', '法力元素': 'Mana Element',
    '法力吞噬者': 'Mana Devourer', '法力幽灵': 'Mana Phantom',
    '法尔德里姆·安威玛尔': 'Faldrim Anvimar', '法拉克斯': 'Farrax',
    '泽雷利斯': 'Zerillis', '洛特格里普': 'Rotgrip', '洛考尔': 'Lokcor',
    '海多斯博恩': 'Hydosborn', '温格': 'Wing', '火眼莫德雷斯': 'Fire-Eye Modres',
    '灰尘怨灵': 'Dust Wraith', '炮手威利': 'Cannoneer Wiley',
    '烈焰卫士艾博希尔': 'Ebohir the Flamewarden', '烟网蛛后': 'Queen of the Smokeweb',
    '燃烧地狱卫士': 'Burning Felguard', '特迪斯·扭木': 'Tendris Warpwood',
    '狂热的玛洛尔': 'Zealous Maro', '狼王南杜斯': 'Wolf Master Nandos',
    '玛拉多斯': 'Marados', '玛格姆斯': 'Magmus', '玛格拉': 'Magra',
    '玛格玛图斯': 'Magmatus', '班诺克·巨斧': 'Bannok Grimaxe',
    '瑞文戴尔男爵': 'Baron Rivendare', '瑟尔林·卡斯迪诺夫教授': 'Doctor Theolen Krastinov',
    '瑟拉吉斯': 'Seragis', '瑟芬迪斯': 'Sephendis', '瑟莱德丝公主': 'Princess Theradras',
    '瑟雷姆·刺蹄': 'Serem Spinehoof', '电刑器6000型': 'Electrocutioner 6000',
    '男爵': 'Baron', '皮萨斯': 'Pisas', '盐脊': 'Saltspine', '盖尔克': 'Gelk',
    '盖斯': 'Gath', '盲眼守卫奥杜': 'Odu the Blind Guard', '盲眼猎手': 'Blind Hunter',
    '石脊': 'Stonegrip', '矿工约翰森': 'Miner Johnson', '祈求者耶戈什': 'Jergosh the Invoker',
    '科技机器人': 'Tech Bot', '竞技场：修行者高罗什': 'Arena: Gorosh',
    '竞技场：格里兹尔': 'Arena: Grizzle', '竞技场：爬行者赫杜姆': 'Arena: Heddum',
    '竞技场：破坏者奥科索尔': 'Arena: Oksothor', '竞技场：腕眼者': 'Arena: Wrist-Eye',
    '竞技场：阿努希尔': 'Arena: Anuhsir', '粘性辐射尘': 'Sticky Radiated Dust',
    '索拉卡·火冠': 'Sorakan Firecrown', '红衣铸锤师': 'Crimson Hammerer',
    '维克图斯': 'Vectus', '维利塔恩': "Vel'tarn", '维姆萨拉克': 'Vimsalak',
    '维雷克': 'Verek', '绿皮船长': 'Captain Greenskin', '群体打击者9-60': 'Crowd Pummeler 9-60',
    '考布莱恩': 'Colbain', '耐克鲁姆': 'Nekrum Gutchewer', '腐烂的普雷莫尔': 'Rotting Premlor',
    '艾德温·范克里夫': 'Edwin VanCleef', '艾隆纳亚': 'Ironaya', '苍白的玛勒基': 'Pale Maleki',
    '苏斯': 'Suss', '莱斯·霜语': 'Ras Frostwhisper', '萨利维丝': 'Salivas',
    '蕾瑟塔蒂丝': 'Retherathis', '血法师萨尔诺斯': 'Bloodmage Sarnos',
    '血色十字军指挥官莫格莱尼': 'Scarlet Commander Mograine', '血骨傀儡': 'Bloodbone Golem',
    '被无视的琳': 'Ignored Lynn', '被诅咒的塞雷布拉斯': 'Cursed Serebras',
    '被遗弃者': 'The Abandoned', '观察者克鲁什': 'Observer Krush', '詹迪斯·巴罗夫': 'Jandice Barov',
    '讲师玛丽希亚': 'Instructor Mariah', '诺克赛恩': 'Noxxion',
    '诺特·希姆加克的储物箱': "Nott Shimjak's Stash", '贝尔加': 'Belga', '贡品': 'Tribute',
    '赫尔努拉斯': 'Hernuras', '赫洛德': 'Herod', '践踏者克雷格': 'Trampler Craig',
    '辛德拉圣职者': "Shen'dralar Priest", '达基萨斯将军': 'General Drakkisath',
    '达格兰·索瑞森大帝': 'Emperor Dagran Thaurissan', '迪菲亚火药': 'Defias Powder',
    '遗物守护者': 'Relic Keeper', '邪恶战马 / 暗影战马': 'Evil / Shadow Warhorse',
    '邪恶的维克托': 'Viktor the Vile', '邪能古树': 'Fel Ancient', '邮差马龙': 'Postman Malon',
    '重拳先生': 'Mr. Smite', '铁炉堡公主茉艾拉·铜须': 'Princess Moira Bronzebeard',
    '铁脊死灵': 'Ironspine Necro', '锐刺鞭笞者': 'Barbed Lasher',
    '阳台的小头目': 'Balcony Miniboss', '阿塔拉利恩': "Atal'alarion",
    '阿奎尼斯男爵': 'Baron Aquanis', '阿库麦尔': "Aku'mai", '阿扎达斯': 'Archaedas',
    '阿格姆': 'Aggem', '阿雷克斯·巴罗夫': 'Alexei Barov', '阿鲁高的虚空行者': "Arugal's Voidwalker",
    '雷希戈尔': 'Rehigor', '霍克·巴什古德': 'Hok Bashgud', '预言者迦玛兰': 'Seer Jammalan',
    '塞沃尔': 'Sever', '瑟克恩': 'Scorn',
    '饥饿者塔拉加曼': 'Taragaman the Hungerer', '马杜克·布莱克波尔': 'Marduk Blackpoole',
    '驯犬者格雷布玛尔': 'Houndmaster Grebmar', '驯犬者洛克希': 'Houndmaster Loksey',
    '高地惊魂': 'Highland Terror', '鲁维罗什': 'Revelosh', '黑暗宝箱': 'Dark Chest',
    '黑暗石板': 'Dark Tablet', '黑暗院长加丁': 'Darkmaster Gandling',
    '黑曜石哨兵': 'Obsidian Sentinel', '黑衣守卫铸剑师': 'Black Guard Swordsmith',
    '黑铁大师': 'Dark Iron Master', '黑铁酒吧': 'The Grim Guzzler',
    '伯德雷': 'Baldray',
}

# ── 令牌 / 类别 / 学派 / 组织 ───────────────────────────────────────────────
TOKENS = {
    '稀有': 'Rare', '任务召唤': 'Quest summon', '图纸': 'Pattern',
    '小怪': 'Trash mobs', '副本内任意敌人': 'Any enemy in the dungeon',
    '宝箱或物件': 'Chest or object', '男爵': 'Baron', '楼梯入口': 'Stairway', '集合石入口': 'Meeting Stone',
    '军需官': 'Quartermaster', '三岔口': 'The Crossroads', '十字路口外': 'Outside the Crossroads',
    '杜隆塔尔补给与后勤': 'Durotar Supply & Logistics',
    '银色黎明': 'Argent Dawn', '诺莫瑞根流亡者': 'Gnomeregan Exiles',
    '暗矛巨魔': 'Darkspear Trolls', '辛德拉': "Shen'dralar", '辛德拉古灵': "Shen'dralar",
    # 配方类别（工具条动态取自数据，翻译即生效）
    '布甲': 'Cloth', '皮甲': 'Leather', '皮革': 'Leather', '锁甲': 'Mail',
    '板甲': 'Plate', '护腕': 'Bracers', '手套': 'Gloves', '武器': 'Weapon',
    '胸甲': 'Chest', '衬衣': 'Shirt', '披风': 'Cloak', '靴子': 'Boots', '靴': 'Boots',
    '护腿': 'Leggings',
    '盾牌': 'Shield', '饰品': 'Trinket', '双手武器': 'Two-Hand',
    '神圣': 'Holy', '冰霜': 'Frost', '痛苦': 'Shadow', '恢复': 'Restoration',
    '增强': 'Enhancement', '防护': 'Protection', '元素': 'Elemental', '敏捷': 'Agility',
    # BIS 部位值（BisUI ENCH_SLOTS 走 ns.DL 对查，译值必须与 gen_enus.py EN 字典逐字一致）
    '颈部': 'Neck', '背部': 'Back', '胸部': 'Chest', '手腕': 'Wrists',
    '手部': 'Hands', '脚': 'Feet', '主手': 'Main Hand', '副手': 'Off Hand',
    '副手：盾牌': 'Off Hand: Shield', '手部、腿部': 'Hands, Legs',
    '主手、副手': 'Main Hand, Off Hand', '远程': 'Ranged',
    # 职业值（DungeonUI QCLASS_TOKEN 走 ns.DL 对查，同样必须一致）
    '战士': 'Warrior', '圣骑士': 'Paladin', '猎人': 'Hunter', '盗贼': 'Rogue',
    '牧师': 'Priest', '萨满': 'Shaman', '法师': 'Mage', '术士': 'Warlock',
    '德鲁伊': 'Druid', '萨满祭司': 'Shaman',
    # 专业页工具条类别（Data_Professions 动态键）
    '工程学': 'Engineering', '工程学认证': 'Engineering Certification',
    '工程学学徒': 'Engineering Apprentice', '工程学专家': 'Engineering Expert',
    '工程学大师': 'Engineering Master', '制皮': 'Leatherworking',
    '其他': 'Other', '急救': 'First Aid', '急救包': 'First Aid Kit',
}

# 段级 glossary（合成标签内部的术语替换）
GLOSS = {
    '布甲': 'Cloth', '皮甲': 'Leather', '锁甲': 'Mail', '板甲': 'Plate',
    '头盔': 'Helm', '护肩': 'Shoulders', '护腕': 'Bracers', '手套': 'Gloves',
    '胸甲': 'Chest', '腰带': 'Belt', '腿部': 'Legs', '靴子': 'Boots',
    # 2026-09-25 enUS 补齐（ProfRecipes 布甲靴/护腿 合成标签）
    '靴': 'Boots', '护腿': 'Leggings',
    '衬衣': 'Shirt', '披风': 'Cloak', '盾牌': 'Shield', '武器': 'Weapon',
    '，': ', ', ' 级': ' Lv', '级': ' Lv',
}

# ── 正则规则（精确表未命中时逐条尝试）────────────────────────────────────────
ATTR = {'力量': 'Strength', '敏捷': 'Agility', '耐力': 'Stamina', '智力': 'Intellect',
        '精神': 'Spirit', '所有属性': 'All stats', '攻击强度': 'Attack Power',
        '法术强度': 'Spell Power', '武器伤害': 'Weapon damage', '防御': 'Defense',
        # 2026-09-25 enUS 补齐（附魔效果 / ProfRecipes 效果标签）
        '全属性': 'All stats', '抗性': 'Resistance', '全抗性': 'All Resistances',
        '暗影抗性': 'Shadow Resistance', '火焰抗性': 'Fire Resistance',
        '冰霜抗性': 'Frost Resistance', '自然抗性': 'Nature Resistance',
        '奥术抗性': 'Arcane Resistance', '神圣抗性': 'Holy Resistance',
        '屠兽': 'Beast Slaying', '屠魔': 'Demon Slaying', '元素杀手': 'Elemental Slayer',
        '采药': 'Herbalism', '采矿': 'Mining', '剥皮': 'Skinning', '钓鱼': 'Fishing',
        '威胁': 'Threat', '躲闪': 'Dodge', '格挡': 'Block', '急速': 'Haste',
        '治疗能量': 'Healing Power', '偏斜': 'Deflection', '吸收': 'Absorption',
        '防护': 'Protection', '打击': 'Striking', '冲击': 'Impact', '属性': 'Stats',
        '骑术': 'Riding'}
ATTR_CLS = ''.join(ATTR)

# 附魔名（附魔X - 效果）与效果标签的前缀/基词
ENCH_SLOT = {'胸甲': 'Chest', '护腕': 'Bracer', '手套': 'Gloves', '靴子': 'Boots',
             '披风': 'Cloak', '武器': 'Weapon', '盾牌': 'Shield'}
ENCH_PRE = {'': '', '初级': 'Minor ', '次级': 'Lesser ', '强效': 'Greater ',
            '超强': 'Major ', '强力': 'Major '}
ENCH_BASE = {'力量': 'Strength', '敏捷': 'Agility', '耐力': 'Stamina',
             '智力': 'Intellect', '精神': 'Spirit', '状态': 'Stats',
             '偏斜': 'Deflection', '吸收': 'Absorption', '防护': 'Protection',
             '治疗能量': 'Healing Power', '屠兽': 'Beast Slaying',
             '抗性': 'Resistance', '打击': 'Striking', '冲击': 'Impact',
             '暗影抗性': 'Shadow Resistance', '火焰抗性': 'Fire Resistance',
             '冰霜抗性': 'Frost Resistance', '自然抗性': 'Nature Resistance',
             '格挡': 'Block', '急速': 'Haste', '防御': 'Defense',
             '元素杀手': 'Elemental Slayer'}
STAT = {}
for _p, _pe in ENCH_PRE.items():
    for _b, _be in ENCH_BASE.items():
        STAT[_p + _b] = _pe + _be

# 武器/装备类别（ProfRecipes「类别，N 级」合成标签）
WCAT = {'单手锤': 'One-Handed Mace', '单手斧': 'One-Handed Axe',
        '单手剑': 'One-Handed Sword', '单手指匕': 'One-Handed Dagger',
        '单手拳套': 'Fist Weapon', '双手剑': 'Two-Handed Sword',
        '双手斧': 'Two-Handed Axe', '双手锤': 'Two-Handed Mace',
        '双手长兵器': 'Polearm', '主手锤': 'Main Hand Mace',
        '主手剑': 'Main Hand Sword', '主手拳套': 'Main Hand Fist',
        '主手杂项': 'Main Hand Misc', '远程火枪': 'Ranged Gun',
        '副手盾牌': 'Off-Hand Shield', '饰品': 'Trinket', '弹药': 'Ammunition',
        '杂项': 'Miscellaneous', '任务': 'Quest', '项链': 'Neck'}
BAG = {'背包': 'Bag', '材料包': 'Material Pouch', '箭袋': 'Quiver',
       '弹药袋': 'Ammo Pouch', '附魔包': 'Enchanting Bag',
       '草药袋': 'Herb Bag', '灵魂袋': 'Soul Bag'}

# 地名合并查询（zone/subzone 兜底链）
LOOKUP = {}
for _src in (BOSSES, DUNGEONS, SUBZONES, ZONES):
    LOOKUP.update(_src)

RULES = [
    (re.compile(r'^(\d+) 级$'), lambda m: 'Lv %s' % m.group(1)),
    (re.compile(r'^稀有 · (\d+) 级$'), lambda m: 'Rare · Lv %s' % m.group(1)),
    (re.compile(r'^任务召唤 · (\d+) 级$'), lambda m: 'Quest summon · Lv %s' % m.group(1)),
    (re.compile(r'^经典旧世为([\d.]+)%$'), lambda m: 'Classic Era: %s%%' % m.group(1)),
    (re.compile(r'^经典旧世为(\d+)级任务，(\d+)级起可接$'),
     lambda m: 'Classic Era: level %s quest, available from %s' % (m.group(1), m.group(2))),
    (re.compile(r'^联盟、(\d+)级起$'), lambda m: 'Alliance, from level %s' % m.group(1)),
    (re.compile(r'^部落、(\d+)级起$'), lambda m: 'Horde, from level %s' % m.group(1)),
    (re.compile(r'^(联盟|部落)、经典旧世为(\d+)级任务，(\d+)级起可接$'),
     lambda m: '%s, Classic Era: level %s quest, available from %s'
               % ('Alliance' if m.group(1) == '联盟' else 'Horde', m.group(2), m.group(3))),
    (re.compile(r'^(.+?)、(联盟|部落)、(\d+)级起$'),
     lambda m: '%s, %s, from level %s'
               % (LOOKUP.get(m.group(1), m.group(1)),
                  'Alliance' if m.group(2) == '联盟' else 'Horde', m.group(3))),
    (re.compile(r'^([%s]+) \+(\d+%%?)$' % ATTR_CLS),
     lambda m: '%s +%s' % (ATTR.get(m.group(1), m.group(1)), m.group(2))),
    (re.compile(r'^([%s]+) \+(\d+)，护甲 \+(\d+)$' % ATTR_CLS),
     lambda m: '%s +%s, %s Armor' % (ATTR.get(m.group(1), m.group(1)), m.group(2), m.group(3))),
    (re.compile(r'^护甲 \+(\d+)$'), lambda m: '%s Armor' % m.group(1)),
    (re.compile(r'^所有属性 \+(\d+)$'), lambda m: 'All stats +%s' % m.group(1)),
    (re.compile(r'^\+(\d+) 法术强度$'), lambda m: '+%s Spell Power' % m.group(1)),
    (re.compile(r'^武器伤害 \+(\d+)$'), lambda m: 'Weapon damage +%s' % m.group(1)),
    (re.compile(r'^防御 \+(\d+)$'), lambda m: 'Defense +%s' % m.group(1)),
    (re.compile(r'^冰霜法术伤害 \+(\d+)$'), lambda m: 'Frost Spell Damage +%s' % m.group(1)),
    (re.compile(r'^(奥术|火焰|冰霜|神圣|自然|暗影)伤害 \+(\d+)$'),
     lambda m: '%s Damage +%s'
               % ({'奥术': 'Arcane', '火焰': 'Fire', '冰霜': 'Frost',
                   '神圣': 'Holy', '自然': 'Nature', '暗影': 'Shadow'}[m.group(1)],
                  m.group(2))),
    (re.compile(r'^\+(\d+) (暗影|火焰|冰霜|自然|奥术|神圣|全)抗性$'),
     lambda m: '+%s %s' % (m.group(1), {'暗影': 'Shadow', '火焰': 'Fire', '冰霜': 'Frost',
                                        '自然': 'Nature', '奥术': 'Arcane', '神圣': 'Holy',
                                        '全': 'All'}[m.group(2)]
                           + (' Resistances' if m.group(2) == '全' else ' Resistance'))),
    (re.compile(r'^\+(\d+) (力量|敏捷|耐力|智力|精神)$'),
     lambda m: '+%s %s' % (m.group(1), ATTR[m.group(2)])),
    (re.compile(r'^\+(\d+) (力量|敏捷|耐力|智力|精神)，\+(\d+) (力量|敏捷|耐力|智力|精神)$'),
     lambda m: '+%s %s, +%s %s' % (m.group(1), ATTR[m.group(2)], m.group(3), ATTR[m.group(4)])),
    (re.compile(r'^治疗法术 \+(\d+)，伤害法术 \+(\d+)$'),
     lambda m: 'Healing +%s, Spell Damage +%s' % (m.group(1), m.group(2))),
    (re.compile(r'^治疗法术 \+(\d+)/伤害法术 \+(\d+)$'),
     lambda m: 'Healing +%s/Spell Damage +%s' % (m.group(1), m.group(2))),
    (re.compile(r'^治疗法术 \+(\d+)$'), lambda m: 'Healing +%s' % m.group(1)),
    (re.compile(r'^每 5 秒恢复 (\d+) 点法力。?$'),
     lambda m: 'Restores %s mana per 5 sec.' % m.group(1)),
    (re.compile(r'^每次命中时有 (\d+)%% 的几率获得 (\d+) 点伤害吸收。每 5 秒最多触发一次。$'),
     lambda m: 'Chance on hit: %s%% chance to gain %s absorption. At most once every 5 sec.'
               % (m.group(1), m.group(2))),
    (re.compile(r'^附魔(胸甲|护腕|手套|靴子|披风|武器|盾牌) - (.+)$'),
     lambda m: 'Enchant %s - %s' % (ENCH_SLOT[m.group(1)], STAT.get(m.group(2), m.group(2)))),
    (re.compile(r'^((?:初级|次级|强效|超强|强力)?(?:力量|敏捷|耐力|智力|精神|状态|偏斜|吸收|防护|治疗能量|屠兽|抗性|打击|冲击|暗影抗性|火焰抗性|冰霜抗性|自然抗性|格挡|急速|防御|元素杀手))$'),
     lambda m: STAT.get(m.group(1), m.group(1))),
    (re.compile(r'^(%s)，(\d+) 级$' % '|'.join(sorted(WCAT, key=len, reverse=True))),
     lambda m: '%s, Lv %s' % (WCAT[m.group(1)], m.group(2))),
    (re.compile(r'^(Cloth|Leather|Mail|Plate) (靴|护腿), Lv (\d+)$'),
     lambda m: '%s %s, Lv %s' % (m.group(1), {'靴': 'Boots', '护腿': 'Legs'}[m.group(2)], m.group(3))),
    (re.compile(r'^(\d+) 格(背包|材料包|箭袋|弹药袋|附魔包|草药袋|灵魂袋)(?:，(\d+) 级)?$'),
     lambda m: '%s-Slot %s%s' % (m.group(1), BAG[m.group(2)],
                                 (', Lv %s' % m.group(3)) if m.group(3) else '')),
    (re.compile(r'^(\d+) - (\d+) 伤害，(\d+) 级$'),
     lambda m: '%s - %s Damage, Lv %s' % (m.group(1), m.group(2), m.group(3))),
    (re.compile(r'^(.+?) - (.+?) 副本入口地图$'),
     lambda m: '%s - %s dungeon entrance map'
               % (LOOKUP.get(m.group(1), m.group(1)), LOOKUP.get(m.group(2), m.group(2)))),
    (re.compile(r'^([\u4e00-\u9fff]+?) 副本入口地图$'),
     lambda m: '%s dungeon entrance map' % LOOKUP.get(m.group(1), m.group(1))),
    (re.compile(r'^([\u4e00-\u9fff·]+?) 副本入口地图\[D\]$'),
     lambda m: '%s dungeon-entrance map [D]' % LOOKUP.get(m.group(1), m.group(1))),
    # giverLoc「区 - 子区 坐标」/「区 坐标」（坐标原样保留）
    (re.compile(r'^([\u4e00-\u9fff·]+?)(?:\s*-\s*([\u4e00-\u9fff·]+?))?\s+(\d{1,3}(?:\.\d+)?(?:\s*[,,]\s*\d{1,3}(?:\.\d+)?)?)$'),
     lambda m: '%s%s %s' % (LOOKUP.get(m.group(1), m.group(1)),
                            (' - ' + LOOKUP.get(m.group(2), m.group(2))) if m.group(2) else '',
                            m.group(3))),
    # 「区 - 子区」无坐标
    (re.compile(r'^([\u4e00-\u9fff·]+?)\s*-\s*([\u4e00-\u9fff·]+?)$'),
     lambda m: '%s - %s' % (LOOKUP.get(m.group(1), m.group(1)),
                            LOOKUP.get(m.group(2), m.group(2)))),
    # 裸地名兜底（燃烧平原 / 达纳苏斯 / 热砂港 这类无坐标 giverLoc）：
    # 只在 LOOKUP 命中才译，未命中原样返回，不会误伤其它纯中文串
    (re.compile(r'^[\u4e00-\u9fff·]{2,10}$'), lambda m: LOOKUP.get(m.group(0), m.group(0))),
    (re.compile(r'^([布皮锁板])(甲|革)(.+?)，(\d+) 级$'),
     lambda m: '%s %s, Lv %s' % (GLOSS.get(m.group(1) + m.group(2), ''), GLOSS.get(m.group(3), m.group(3)), m.group(4))),
]

# ── 精确串翻译（Explore / Entry / ProfLeveling / BIS / Quests 备注等）────────
EXACT = {
    # Data_DungeonQuests 备注
    '把这本典籍交给它的主人。': 'Turn this tome in to its owner.',
    '厄运之槌的所有几个副本的 首领 都可能掉落':
        'May drop from any of the bosses across the Dire Maul dungeons',
    '重要的材料': 'Vital Materials', '更多重要的材料': 'More Vital Materials',
    # Data_BIS 杂项
    '只有制作者能穿戴': 'Only the maker can wear this',
    '向训练师学习.': 'Learn from a trainer.',
    '（制皮 150）向训练师学习.': '(Leatherworking 150) Learn from a trainer.',
    '（制皮 80）图样由各主城的制皮供应商出售.':
        '(Leatherworking 80) Pattern sold by leatherworking suppliers in each capital.',
    '（工程学 180）设计图由Mazk Snipeshot（Stranglethorn Vale）出售.':
        '(Engineering 180) Schematic sold by Mazk Snipeshot (Stranglethorn Vale).',
    '不绑定：拍卖行最快': 'Not bound: auction house is the fastest source',
    '任务：Friend of the Library': 'Quest: Friend of the Library',
    '任务：Greater Friend of the Library': 'Quest: Greater Friend of the Library',
    '可选奖励，由幽暗城的Keeper Bel\'dugur给予':
        "Optional reward, granted by Keeper Bel'dugur in Undercity",
    'Nightveiled Rotheap，在湿地巡逻的怪物': 'Nightveiled Rotheap, a wandering mob in the Wetlands',
    '狮王休玛，贫瘠之地的稀有黑狮': 'Humar the Pridelord, the rare black lion of the Barrens',
    '移动速度略微提升': 'Slightly increased movement speed',
    '还不知道从哪里取得： 如果你知道请告诉我们': 'Source unknown yet — let us know if you find it',
    '配方来源还不清楚.': 'Recipe source still unclear.',
    '经典旧世的商人，未在Beta中确认': 'Classic Era vendor, not yet confirmed on the beta',
    '配方由Alynsia（Redridge Mountains） 和 Beneris（The Barrens）出售，价格120 商人青睐.':
        'Sold by Alynsia (Redridge Mountains) and Beneris (The Barrens) for 120 Commercial Favor.',
    '配方由Alynsia（Redridge Mountains） 和 Beneris（The Barrens）出售，价格45 商人青睐. 触发频率不在任何游戏文件里，也还没有人测过：列在这里是因为单手武器在这个技能点没有别的选择。':
        'Sold by Alynsia (Redridge Mountains) and Beneris (The Barrens) for 45 Commercial Favor. The proc rate is in no game file and untested: listed here because one-handers have no other option at this skill point.',
    '配方由Dalria（Ashenvale） 和 Kulwia（Stonetalon Mountains）出售.':
        'Sold by Dalria (Ashenvale) and Kulwia (Stonetalon Mountains).',
    '配方由Tilli Thistlefuzz（Dun Morogh）、Kithas（Orgrimmar） 和 Leo Sarn（Silverpine Forest）出售.':
        'Sold by Tilli Thistlefuzz (Dun Morogh), Kithas (Orgrimmar) and Leo Sarn (Silverpine Forest).',
    '重型护甲片': 'Heavy Armor Kit', '瞄准镜（+3 伤害）': 'Scope (+3 damage)',
    '每个步骤都在物品页面上': 'Every step is on the item page',
    '20级起': 'From level 20',
    '（该专精未收录时整条缺省）': '(whole entry omitted when the spec is not indexed)',
    # Data_Explore
    '搜索书籍': 'Search books', '主城': 'Capital', '低~高': 'Low–High',
    '交出第十本解锁项链奖励，交出第二十本解锁戒指奖励，交出第二十五本解锁三选一奖励（求真者之弓 / 阐明徽记 / 研究员的小夜灯 任选其一）。':
        'The 10th book unlocks the necklace reward, the 20th the ring reward, and the 25th a choice of three — Truthseeker\'s Bow, Crest of Elucidation, or Researcher\'s Night Light.',
    '在 10 本、20 本和 25 本时领奖': 'Claim at 10, 20 and 25 books',
    '交给你的图书馆员': 'Turn in to your librarian',
    '书不是怪物掉落：每本都从固定的物件拾取——书架、卷轴堆、桌上的书等。':
        'Books do not drop from mobs: each is looted from a fixed object — bookshelves, scroll piles, books on tables, etc.',
    '交书任务完成后，法师额外学会新专业「研究（Research）」。':
        'After the turn-in quest, mages additionally learn the new profession "Research".',
    '有个重要细节：每本书都有独立的任务，找到哪本就可以交哪本，不用攒够 10 本。':
        'One important detail: each book has its own quest — turn in whichever you find, no need to save up 10.',
    '每交一本可得一个理解魔符。联盟：暴风城·法师区 37.6, 80.8；部落：幽暗城·魔法区 73.4, 33.0。':
        'Each book turned in yields a Comprehension Sigil. Alliance: Stormwind Mage Quarter 37.6, 80.8; Horde: Undercity Magic Quarter 73.4, 33.0.',
    '这条任务线所有职业都能接，没有等级要求。身上要先带着一本书，图书馆员才会给你任务。':
        'Any class can take this quest line, no level requirement. You must carry a book before the librarian offers it.',
    '解锁技能「学习（Study）」：消耗轻羽毛制作一捆法术卷轴，1 小时冷却。':
        'Unlocks the "Study" skill: craft a bundle of scrolls from Light Feathers, 1 hr cooldown.',
    '需在图书馆内使用；理解（Comprehension）等级越高，卷轴产出越好。':
        'Must be used inside the library; the higher your Comprehension rank, the better the scroll output.',
    '注：当前 beta 重登后该专业可能消失，官方修复中。':
        'Note: on the current beta this profession may disappear after relogging; an official fix is pending.',
    # ProfLeveling / 营地 NPC
    '妮娜·神火': 'Nina Holyflame', '药剂师杜蕾尔': 'Apothecary Durel',
    '斯通德里·暗锤': 'Stonedeep Darkhammer', '戈尔马克': 'Gormark',
    '丹尼尔·缝歌': 'Daniel Stitchsong', '卡尔西·沙登': 'Kalsy Sandden',
    '吉姆贝克': 'Gimbek', '帕瓦妮': 'Pavani', '弗里茨·菲兹尔': 'Fritz Fitzel',
    '米文·暗织': 'Miren Darkweave', '艾琳西娅': 'Ilinthia', '贝内里斯': 'Beneris',
    '菲兹法斯': 'Fizfas', '阿扎贝克': 'Azabek',
    # ── 2026-09-25 enUS 数据层补齐 ──
    # Data_BIS
    '地下城小怪': 'Dungeon trash mobs',
    '邪恶的维克多': 'Viktor the Vile', '法德林·安威玛尔': 'Faldrim Anvimar',
    '杜根·挽锤': 'Duggan Wildhammer', '启示': 'Revelation', '洞悉': 'Insight',
    '智慧': 'Wisdom',
    # Data_ProfRecipes 附魔名 / 触发说明
    '炽热武器': 'Fiery Weapon', '冰寒': 'Icy Chill', '邪恶武器': 'Unholy Weapon',
    '生命偷取': 'Lifestealing', '十字军': 'Crusader', '寒冬之力': "Winter's Might",
    '莲花之爪': 'Lotus Claw', '法术爆破': 'Spell Blast',
    '奥术能量': 'Arcane Energy', '火焰能量': 'Fire Energy', '冰霜能量': 'Frost Energy',
    '神圣能量': 'Holy Energy', '自然能量': 'Nature Energy', '暗影能量': 'Shadow Energy',
    '强力法术强度': 'Major Spellpower', '强效法术强度': 'Greater Spellpower',
    '强力治疗能量': 'Major Healing Power',
    '施放法术时有几率获得「洞悉」，使精神提高 100%，持续 10 秒。':
        'Chance when casting a spell to gain "Insight", increasing Spirit by 100% for 10 sec.',
    '当你被招架或躲闪时触发「恢复」，为你恢复 5% 的最大生命值。每 10 秒最多触发一次。':
        'When you are parried or dodge, triggers "Recovery", restoring 5% of your maximum health. At most once every 10 sec.',
    '非持续性法术未造成暴击时有几率触发「启示」，使下一次施放的法术暴击几率提高 100%。暴击几率越高，「启示」的触发几率越低。':
        'Chance when a non-periodic spell fails to crit to trigger "Revelation", making your next spell 100% more likely to crit. The higher your crit chance, the lower the chance to trigger.',
    '略微提高移动速度。': 'Slightly increases movement speed.',
    '经常额外造成 40 点火焰伤害。': 'Frequently deals an additional 40 Fire damage.',
    '经常使目标寒冷，降低其移动速度与攻击速度。':
        'Frequently chills the target, reducing its movement and attack speed.',
    '经常对目标施加诅咒，降低其近战伤害。':
        'Frequently curses the target, reducing its melee damage.',
    '经常吸取敌人的生命并转移给持有者。':
        'Frequently drains life from the enemy and transfers it to the wielder.',
    '近战攻击时经常治疗 100 点生命，并使力量提高 100，持续 15 秒。':
        'Frequently heals 100 health on melee attack and increases Strength by 100 for 15 sec.',
    '有几率击晕恶魔并造成大量伤害。': 'Chance to stun demons and deal heavy damage.',
    '在海加尔山采集任何草药时，有小几率获得死亡莲花。':
        'Small chance to gather a Death Lotus when picking any herb in Mount Hyjal.',
    '使你的潜行效果相当于高 1 级。': 'Makes your stealth count as if 1 level higher.',
    '使佩戴者造成的威胁值降低 2%。': 'Reduces threat generated by the wearer by 2%.',
    '骑乘时提供少量移动速度加成。': 'Provides a small movement speed bonus while mounted.',
    # Data_ProfRecipes 类别
    '药水': 'Potions', '药剂': 'Elixirs', '合剂': 'Flasks', '转化': 'Transmutes',
    '油与其他': 'Oils and Misc', '营地物件': 'Camp Objects', '杂项': 'Miscellaneous',
    '单手武器': 'One-Handed Weapons', '头部': 'Head', '肩部': 'Shoulders',
    '项链': 'Neck', '弹药': 'Ammunition',
    '磨刀石、平衡石与砂轮': 'Sharpening Stones, Weightstones and Grindstones',
    '盾刺、链条与马刺': 'Shield Spikes, Chains and Spurs',
    '钥匙、符文棒与工具': 'Keys, Runed Rods and Tools',
    '炸弹与爆炸物': 'Bombs and Explosives', '饰品与器械': 'Trinkets and Devices',
    '护目镜与头盔': 'Goggles and Helmets', '其他装备': 'Other Equipment',
    '火枪与瞄准镜': 'Guns and Scopes',
    '烟花与玩具': 'Fireworks and Toys', '宠物与坐骑': 'Pets and Mounts', '零件': 'Parts',
    '护甲片': 'Armor Kits', '背包': 'Bags', '熟化皮革': 'Cured Leather',
    '布卷': 'Bolts of Cloth', '绷带': 'Bandages', '解毒剂与药水': 'Antidotes and Potions',
    '耐力与精神': 'Stamina and Spirit', '力量与攻击强度': 'Strength and Attack Power',
    '智力、法术强度与法力': 'Intellect, Spell Power and Mana',
    '其他增益': 'Other Buffs', '仅生命与法力': 'Health and Mana Only',
    # Data_ProfRecipes 套装分组名
    '祝福板甲': 'Blessed Plate', '帝王板甲': 'Imperial Plate',
    '血魂拥抱': 'Bloodsoul Embrace', '黑暗之魂': 'Dark Soul',
    '荣耀战甲': 'Glorious Battleplate', '荣耀板甲': 'Glorious Plate',
    '公正护甲': 'Justice Armor', '公正战甲': 'Justice Battleplate',
    '公正板甲': 'Justice Plate',
    '绿龙锁甲': 'Green Dragonscale', '蓝龙锁甲': 'Blue Dragonscale',
    '黑龙锁甲': 'Black Dragonscale', '铁羽护甲': 'Ironfeather Armor',
    '火山护甲': 'Volcanic Armor', '风暴护甲': 'Stormshroud Armor',
    '魔暴龙护甲': 'Devilsaur Armor', '血虎护甲': 'Blood Tiger Harness',
    '阴森缝合护甲': 'Grim Stitched Armor',
    '林地守护者法衣': 'Woodland Guardian Garb', '林地守护者·狂怒': 'Woodland Guardian: Fury',
    '林地守护者·日蚀': 'Woodland Guardian: Eclipse', '林地守护者·凶猛': 'Woodland Guardian: Ferocity',
    '原始蝙蝠皮': 'Primal Bat Hide',
    '唤灵者的愤怒': "Spiritcaller's Wrath", '唤灵者': 'Spiritcaller',
    '唤灵者的风暴': "Spiritcaller's Storm", '荒野追猎者护甲': 'Wilds Stalker Armor',
    '装饰靴': 'Fancy Boots', '装饰衬衣与长袍': 'Decorative Shirts and Robes',
    '装饰胸甲': 'Decorative Chest', '血藤外衣': 'Bloodvine Vest',
    '信念外衣': 'Faith Vest', '信念法衣': 'Faith Garb',
    '恶魔之心法衣': 'Demonheart Garb', '法力耀光法衣': 'Managlow Garb',
    # Data_ProfLeveling
    '艾泽拉斯商会': 'Azeroth Commerce Authority',
    # Data_Explore 书籍位置注记（40 本书）
    '阿祖拉之塔顶层楼梯口的矮桌上':
        "On a small table at the top of the stairs of the Tower of Azora",
    '探险者大厅后间中央的圆桌上':
        'On the round table in the center of the back room of the Hall of Explorers',
    '精神谷法师训练师屋外的塔佐石壁画上':
        "On the carved stone mural outside the mage trainer's hut in the Valley of Spirits",
    '布瑞尔药水店的书架上': 'On a bookshelf in the Brill potion shop',
    '主楼下层角落的书架上':
        'On a bookshelf in a corner of the lower floor of the main building',
    '安伯米尔市政厅主室左后方的书架上':
        'On a bookshelf at the left rear of the main hall of the Ambermill town hall',
    '玛塞斯特拉废墟中央楼梯平台上的卷轴堆':
        "On a scroll pile on the central stair landing of Maestra's Post ruins",
    '塞尔萨玛旅店二楼桌上（哨兵岭旅店 52.7,53.8 另有一本，同一本书只算一次，拿过一处另一处失效）':
        'On a table on the second floor of the Thelsamar inn (another copy in the Sentinel Hill inn at 52.7,53.8 — the same book counts once; looting one invalidates the other)',
    '哨兵岭旅店床铺间的桌上（与塞尔萨玛那本同一本书，二选一）':
        'On a table between the beds in the Sentinel Hill inn (same book as the Thelsamar one — either counts)',
    "莫格罗什要塞东北角最里面的蛮兵洞穴（Chok'sul 精英同洞）：进门抱左，第一个左转房间，3 个食人魔法师身后右侧":
        "In the innermost gnoll cave at the northeast corner of Mogrosh Stronghold (same cave as the elite Chok'sul): hug the left wall after entering, first left-turn room, right side behind the 3 gnoll mages",
    '月溪镇边黄顶小屋内的书架上':
        'On a bookshelf in the yellow-roofed hut on the edge of Moonbrook',
    '淤泥沼泽钻井平台顶上': 'On top of the drilling platform at the Sludge Fen',
    '棘齿城工程房车旁的箱子上': 'On a crate next to the engineering wagon in Ratchet',
    '甜水绿洲（46.0,36.5）进洞，靠哀嚎洞穴副本入口的迷雾洞穴里，传送门旁地上（洞穴地图 52.8,54.7）':
        'Enter the cave at the Lushwater Oasis (46.0,36.5); in the misty cave by the Wailing Caverns entrance, on the ground next to the portal (cave map 52.8,54.7)',
    '恐怖图腾岗哨小屋的木桶上': 'On a barrel in a hut at the Grimtotem Post',
    '暗色河滩的发光书本': 'The glowing book on the dark riverbank',
    '维尔加挖掘场的半埋陶瓮下':
        'Under a half-buried pottery urn at the Verga excavation site',
    '黑云峰顶最大的棚屋里（上山路径入口 31.0,36.0）':
        'In the largest hut at the top of Blackcloud Peak (uphill path entrance 31.0,36.0)',
    '绞刑场处的书本（斯通布拉德或塔伦米尔侧上山）':
        'The book at the gallows (climb from either the Stonewrought or Tarren Mill side)',
    '劈颅村帐篷外的卷轴堆': 'On a scroll pile outside a tent in the Skullsplitter village',
    '雷角堡垒大屋内的长凳上': 'On a bench inside the great hall of Thunderhorn Hold',
    '水晶矿洞入口右侧的木平台上，不用进矿坑':
        'On the wooden platform to the right of the Crystal Mine entrance — no need to enter the mine',
    '孤丘南侧的墓穴里（路径起点 56.0, 45.0）':
        'In the crypt on the south side of the solitary hill (path start 56.0, 45.0)',
    '女巫岭鱼人营地东侧的地上（湿透的书）':
        'On the ground east of the murloc camp on Witch Hill (a soaked book)',
    '法尔圣所的笼子里：先从旁边的失落者身上摸锈笼钥匙，再开笼取书':
        'In a cage at the Farral Sanctuary: pickpocket the Rusted Cage Key from the Lost One nearby, then open the cage and take the book',
    '沉没的神庙顶层，进团队副本入口前的房间里':
        'On the top level of the Sunken Temple, in the room before the raid entrance',
    '菲拉斯的梦魇之中': 'Within the Feralas Nightmare',
    '海盗楼内的书架上': "On a bookshelf inside the pirates' building",
    '辛特兰目标点地面上': 'On the ground at the marked spot in the Hinterlands',
    '灼热峡谷目标点地面上': 'On the ground at the marked spot in Searing Gorge',
    '诅咒之地目标点地面上': 'On the ground at the marked spot in Blasted Lands',
    '赫达瑞营地小屋旁的箱子上': 'On a crate beside a hut at the Hedari camp',
    '木喉要塞内部中段桥头旁': 'Beside the bridge midway inside Timbermaw Hold',
    '黑石深渊入口外侧的台地上（不要进副本）':
        'On the terrace outside the Blackrock Depths entrance (do not enter the dungeon)',
    '通灵学院城堡内右转上梯，桌上':
        'Inside the Scholomance castle, turn right and climb the ladder; on a table',
    '费尔斯通农场屋内': 'Inside the house at Felstone Farm',
    '铁穹堡 Franclorn Forgewright 的祭坛上（黑石深渊入口旁台地，无需进本）':
        'On the altar of the Iron Bastion where Franclorn Forgewright stands (terrace beside the Blackrock Depths entrance, no need to enter)',
    '圣光之愿礼拜堂内，后排左侧': "Inside Light's Hope Chapel, back row on the left",
    '去斯坦索姆入口的桥前，右侧桌上':
        'On a table on the right, before the bridge leading to the Stratholme entrance',
    '东瘟疫之地中央小湖边': 'Beside the small lake in central Eastern Plaguelands',
    '永望镇炼金供应商身后的货架上': 'On the shelf behind the Everlook alchemy supplier',
    '如何获得奖励': 'How to claim the rewards',
    '法师限定 · 研究（Research）': 'Mage only · Research',
}
