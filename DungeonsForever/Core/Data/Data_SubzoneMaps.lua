local _, ns = ...

ns.SubzoneWing = {
    [36] = { ["地精锻造厂"] = "the_deadmines", ["船桅室"] = "the_deadmines", ["铁甲湾"] = "the_deadmines" },
    [43] = { ["毒牙深渊"] = "wailing_caverns", ["永生峭壁"] = "wailing_caverns", ["激流溪谷"] = "wailing_caverns", ["狂风裂口"] = "wailing_caverns", ["美梦石"] = "wailing_caverns" },
    [48] = { ["月神圣地密室"] = "blackfathom_deeps", ["月神圣地废墟"] = "blackfathom_deeps", ["水下庙宇"] = "blackfathom_deeps", ["遗忘之池"] = "blackfathom_deeps", ["阿库麦尔的巢穴"] = "blackfathom_deeps", ["阿斯卡之池"] = "blackfathom_deeps" },
    [70] = { ["一号挖掘场"] = "uldaman", ["三号挖掘场"] = "uldaman", ["二号挖掘场"] = "uldaman", ["卡兹格罗斯的王座"] = "uldaman", ["地图厅"] = "uldaman", ["守护者大厅"] = "uldaman", ["工匠大厅"] = "uldaman", ["石窖"] = "uldaman", ["神殿大厅"] = "uldaman", ["艾卡默克洞穴"] = "uldaman" },
    [90] = { ["发射台"] = "gnomeregan", ["发条小径"] = "gnomeregan", ["宿舍"] = "gnomeregan", ["工匠议会"] = "gnomeregan", ["工程实验室"] = "gnomeregan", ["清洁区"] = "gnomeregan", ["齿轮大厅"] = "gnomeregan" },
    [109] = { ["堕神圣地"] = "sunken_temple", ["天选者之巢"] = "sunken_temple", ["抛弃之池"] = "sunken_temple", ["毒蛇大厅"] = "sunken_temple", ["沉睡者之厅"] = "sunken_temple", ["牺牲之池"] = "sunken_temple", ["诅咒大厅"] = "sunken_temple" },
    [129] = { ["召唤者之厅"] = "razorfen_downs", ["白骨之堆"] = "razorfen_downs", ["荆棘螺旋"] = "razorfen_downs", ["谋杀者围栏"] = "razorfen_downs" },
    [189] = { ["勇士大厅"] = "sm_armory", ["十字军武器库"] = "sm_armory", ["十字军礼拜堂"] = "sm_cathedral", ["图书馆"] = "sm_library", ["大门廊"] = "sm_armory", ["忏悔室"] = "sm_graveyard", ["教堂花园"] = "sm_cathedral", ["步兵武器库"] = "sm_armory", ["猎手回廊"] = "sm_library", ["珍宝陈列室"] = "sm_library", ["荣耀之墓"] = "sm_graveyard", ["训练场"] = "sm_armory", ["遗忘回廊"] = "sm_graveyard" },
    [229] = { ["仓库"] = "lower_blackrock_spire", ["哈雷肯之巢"] = "lower_blackrock_spire", ["塔萨洛尔"] = "lower_blackrock_spire", ["孵化间"] = "upper_blackrock_spire", ["尖塔王座"] = "upper_blackrock_spire", ["战斗之厅"] = "lower_blackrock_spire", ["摩多姆"] = "lower_blackrock_spire", ["熔炉"] = "upper_blackrock_spire", ["禁锢之厅"] = "upper_blackrock_spire", ["蛛网隧道"] = "lower_blackrock_spire", ["霍德玛尔城"] = "lower_blackrock_spire", ["黑石塔"] = "lower_blackrock_spire", ["黑石竞技场"] = "upper_blackrock_spire", ["龙塔大厅"] = "upper_blackrock_spire" },
    [230] = { ["东区兵营"] = "blackrock_depths", ["制造厂"] = "blackrock_depths", ["召唤者之墓"] = "blackrock_depths", ["工艺之厅"] = "blackrock_depths", ["帝王之座"] = "blackrock_depths", ["暗炉城"] = "blackrock_depths", ["浇铸间"] = "blackrock_depths", ["熔火之桥"] = "blackrock_depths", ["禁闭室"] = "blackrock_depths", ["秩序大厅"] = "blackrock_depths", ["秩序竞技场"] = "blackrock_depths", ["索瑞森神殿"] = "blackrock_depths", ["西区兵营"] = "blackrock_depths", ["讲学厅"] = "blackrock_depths", ["钢铁大厅"] = "blackrock_depths", ["魔法之厅"] = "blackrock_depths", ["黑色宝库"] = "blackrock_depths", ["黑铁大道"] = "blackrock_depths", ["黑铁酒吧"] = "blackrock_depths" },
    [429] = { ["扭木广场"] = "dire_maul_east", ["纽木广场"] = "dire_maul_east", ["艾德雷斯神殿"] = "dire_maul_east", ["密径"] = "dire_maul_east", ["戈多克议会"] = "dire_maul_north", ["中心花园"] = "dire_maul_west", ["上层精灵庭院"] = "dire_maul_west", ["伊莫塔尔的牢笼"] = "dire_maul_west" },
    [289] = { ["召唤大厅"] = "scholomance", ["实验室"] = "scholomance", ["尸骨储藏所"] = "scholomance", ["巫师会所"] = "scholomance", ["巴罗夫家族宝库"] = "scholomance", ["掠夺者灵堂"] = "scholomance", ["暗影墓穴"] = "scholomance", ["秘密之厅"] = "scholomance", ["观察室"] = "scholomance", ["谴责之厅"] = "scholomance", ["遗骨之穴"] = "scholomance", ["院长的书房"] = "scholomance" },
    [329] = { ["十字军广场"] = "stratholme_main", ["国王广场"] = "stratholme_main", ["圣光大厅"] = "stratholme_main", ["屠宰房"] = "stratholme_service", ["屠杀广场"] = "stratholme_service", ["市场"] = "stratholme_main", ["步兵武器库"] = "stratholme_main", ["节日小道"] = "stratholme_main", ["血色十字军堡垒"] = "stratholme_main", ["街巷"] = "stratholme_service", ["赤红王座"] = "stratholme_main", ["长者广场"] = "stratholme_service", ["阿隆索斯礼拜堂"] = "stratholme_service" },
    [349] = { ["地歌瀑布"] = "maraudon", ["扎尔塔之墓"] = "maraudon", ["毒水瀑布"] = "maraudon", ["毒水谷"] = "maraudon", ["毒菇洞穴"] = "maraudon", ["草藤之座"] = "maraudon", ["邪恶洞穴"] = "maraudon" },
    [389] = { ["暗影裂口"] = "ragefire_chasm" },
}

ns.SubzoneLayer = {
    blackfathom_deeps = { ["月神圣地密室"] = 2, ["月神圣地废墟"] = 2, ["水下庙宇"] = 1, ["遗忘之池"] = 3, ["阿库麦尔的巢穴"] = 2, ["阿斯卡之池"] = 1 },
    blackrock_depths = { ["东区兵营"] = 2, ["制造厂"] = 2, ["召唤者之墓"] = 2, ["工艺之厅"] = 1, ["帝王之座"] = 2, ["暗炉城"] = 2, ["浇铸间"] = 2, ["熔火之桥"] = 2, ["禁闭室"] = 1, ["秩序大厅"] = 1, ["秩序竞技场"] = 1, ["索瑞森神殿"] = 2, ["西区兵营"] = 2, ["讲学厅"] = 2, ["钢铁大厅"] = 2, ["魔法之厅"] = 2, ["黑色宝库"] = 2, ["黑铁大道"] = 1, ["黑铁酒吧"] = 2 },
    dire_maul_east = { ["巨槌竞技场"] = 5 },
    gnomeregan = { ["发射台"] = 3, ["发条小径"] = 1, ["宿舍"] = 2, ["工匠议会"] = 4, ["工程实验室"] = 3, ["清洁区"] = 1, ["齿轮大厅"] = 1 },
    lower_blackrock_spire = { ["仓库"] = 5, ["哈雷肯之巢"] = 5, ["塔萨洛尔"] = 1, ["战斗之厅"] = 6, ["摩多姆"] = 3, ["蛛网隧道"] = 2, ["霍德玛尔城"] = 3, ["黑石塔"] = 4 },
    maraudon = { ["地歌瀑布"] = 2, ["扎尔塔之墓"] = 2, ["毒水瀑布"] = 1, ["毒水谷"] = 1, ["毒菇洞穴"] = 1, ["草藤之座"] = 1, ["邪恶洞穴"] = 1 },
    scholomance = { ["召唤大厅"] = 2, ["实验室"] = 4, ["尸骨储藏所"] = 3, ["巫师会所"] = 3, ["巴罗夫家族宝库"] = 4, ["掠夺者灵堂"] = 4, ["暗影墓穴"] = 4, ["秘密之厅"] = 3, ["观察室"] = 2, ["谴责之厅"] = 3, ["遗骨之穴"] = 1, ["院长的书房"] = 4 },
    sm_armory = { ["勇士大厅"] = 1, ["十字军武器库"] = 1, ["大门廊"] = 1, ["步兵武器库"] = 1, ["训练场"] = 1 },
    sm_cathedral = { ["十字军礼拜堂"] = 1, ["教堂花园"] = 1 },
    sm_graveyard = { ["忏悔室"] = 1, ["荣耀之墓"] = 1, ["遗忘回廊"] = 1 },
    sm_library = { ["图书馆"] = 1, ["猎手回廊"] = 1, ["珍宝陈列室"] = 1 },
    stratholme_main = { ["十字军广场"] = 1, ["国王广场"] = 1, ["圣光大厅"] = 1, ["市场"] = 1, ["步兵武器库"] = 1, ["节日小道"] = 1, ["血色十字军堡垒"] = 1, ["赤红王座"] = 1 },
    the_deadmines = { ["地精锻造厂"] = 2, ["船桅室"] = 1, ["铁甲湾"] = 2 },
    uldaman = { ["一号挖掘场"] = 1, ["三号挖掘场"] = 1, ["二号挖掘场"] = 1, ["卡兹格罗斯的王座"] = 2, ["地图厅"] = 1, ["守护者大厅"] = 1, ["工匠大厅"] = 2, ["石窖"] = 1, ["神殿大厅"] = 1, ["艾卡默克洞穴"] = 1 },
    wailing_caverns = { ["毒牙深渊"] = 1, ["永生峭壁"] = 1, ["激流溪谷"] = 1, ["狂风裂口"] = 1, ["美梦石"] = 1 },
}
