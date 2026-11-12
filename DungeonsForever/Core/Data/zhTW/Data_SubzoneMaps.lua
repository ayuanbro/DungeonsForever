local _, ns = ...
local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

ns.SubzoneWing = {
    [36] = { ["哥布林鍛造廠"] = "the_deadmines", ["船桅室"] = "the_deadmines", ["鐵甲灣"] = "the_deadmines" },
    [43] = { ["毒牙深淵"] = "wailing_caverns", ["永生峭壁"] = "wailing_caverns", ["激流溪谷"] = "wailing_caverns", ["狂風裂口"] = "wailing_caverns", ["美夢石"] = "wailing_caverns" },
    [48] = { ["月光神殿密室"] = "blackfathom_deeps", ["月光神殿廢墟"] = "blackfathom_deeps", ["水下廟宇"] = "blackfathom_deeps", ["遺忘之池"] = "blackfathom_deeps", ["阿庫麥爾的巢穴"] = "blackfathom_deeps", ["阿斯卡之池"] = "blackfathom_deeps" },
    [70] = { ["一號挖掘場"] = "uldaman", ["三號挖掘場"] = "uldaman", ["二號挖掘場"] = "uldaman", ["卡茲格羅斯的王座"] = "uldaman", ["地圖室"] = "uldaman", ["守護者大廳"] = "uldaman", ["工匠大廳"] = "uldaman", ["石窖"] = "uldaman", ["神殿大廳"] = "uldaman", ["艾卡莫克洞穴"] = "uldaman" },
    [90] = { ["宿舍"] = "gnomeregan", ["工匠議會"] = "gnomeregan", ["工程實驗室"] = "gnomeregan", ["清潔區"] = "gnomeregan", ["發射台"] = "gnomeregan", ["發條小徑"] = "gnomeregan", ["齒輪大廳"] = "gnomeregan" },
    [109] = { ["墮神聖地"] = "sunken_temple", ["天選者之巢"] = "sunken_temple", ["拋棄之池"] = "sunken_temple", ["毒蛇大廳"] = "sunken_temple", ["沉睡者之廳"] = "sunken_temple", ["獻祭坑"] = "sunken_temple", ["詛咒大廳"] = "sunken_temple" },
    [129] = { ["召喚者之廳"] = "razorfen_downs", ["白骨之堆"] = "razorfen_downs", ["荊棘螺旋"] = "razorfen_downs", ["謀殺者圍欄"] = "razorfen_downs" },
    [189] = { ["勇士大廳"] = "sm_armory", ["十字軍武器庫"] = "sm_armory", ["十字軍禮拜堂"] = "sm_cathedral", ["圖書館"] = "sm_library", ["大門廊"] = "sm_armory", ["孤寂迴廊"] = "sm_graveyard", ["懺悔室"] = "sm_graveyard", ["教堂花園"] = "sm_cathedral", ["榮耀之墓"] = "sm_graveyard", ["步兵武器庫"] = "sm_armory", ["獵手迴廊"] = "sm_library", ["珍寶陳列室"] = "sm_library", ["訓練場"] = "sm_armory" },
    [229] = { ["倉庫"] = "lower_blackrock_spire", ["哈雷肯之巢"] = "lower_blackrock_spire", ["塔薩洛爾"] = "lower_blackrock_spire", ["孵化間"] = "upper_blackrock_spire", ["尖塔王座"] = "upper_blackrock_spire", ["戰鬥之廳"] = "lower_blackrock_spire", ["摩多姆"] = "lower_blackrock_spire", ["熔爐"] = "upper_blackrock_spire", ["禁錮大廳"] = "upper_blackrock_spire", ["蛛網隧道"] = "lower_blackrock_spire", ["霍德瑪爾城"] = "lower_blackrock_spire", ["黑石塔"] = "lower_blackrock_spire", ["黑石競技場"] = "upper_blackrock_spire", ["龍塔大廳"] = "upper_blackrock_spire" },
    [230] = { ["召喚師之墓"] = "blackrock_depths", ["工匠大廳"] = "blackrock_depths", ["帝王之座"] = "blackrock_depths", ["影爐城"] = "blackrock_depths", ["東部兵營"] = "blackrock_depths", ["澆鑄間"] = "blackrock_depths", ["熔火之橋"] = "blackrock_depths", ["禁閉室"] = "blackrock_depths", ["秩序大廳"] = "blackrock_depths", ["秩序競技場"] = "blackrock_depths", ["索瑞森神殿"] = "blackrock_depths", ["製造廠"] = "blackrock_depths", ["西部兵營"] = "blackrock_depths", ["講學廳"] = "blackrock_depths", ["鐵之大廳"] = "blackrock_depths", ["魔法之廳"] = "blackrock_depths", ["黑鐵大道"] = "blackrock_depths", ["黑鐵寶庫"] = "blackrock_depths", ["黑鐵酒吧"] = "blackrock_depths" },
    [289] = { ["召喚之廳"] = "scholomance", ["實驗室"] = "scholomance", ["屍骨儲藏所"] = "scholomance", ["巫師會所"] = "scholomance", ["巴羅夫家族寶庫"] = "scholomance", ["掠奪者靈堂"] = "scholomance", ["暗影墓穴"] = "scholomance", ["秘密大廳"] = "scholomance", ["觀察室"] = "scholomance", ["譴責大廳"] = "scholomance", ["遺骨之穴"] = "scholomance", ["院長的書房"] = "scholomance" },
    [329] = { ["十字軍廣場"] = "stratholme_main", ["國王廣場"] = "stratholme_main", ["屠宰房"] = "stratholme_service", ["屠殺廣場"] = "stratholme_service", ["市場區"] = "stratholme_main", ["物資庫"] = "stratholme_main", ["節日小道"] = "stratholme_main", ["聖光大廳"] = "stratholme_main", ["血色十字軍堡壘"] = "stratholme_main", ["街巷"] = "stratholme_service", ["赤色王座"] = "stratholme_main", ["長者廣場"] = "stratholme_service", ["阿隆索斯教堂"] = "stratholme_service" },
    [349] = { ["地歌瀑布"] = "maraudon", ["札爾塔之墓"] = "maraudon", ["毒水瀑布"] = "maraudon", ["毒水谷"] = "maraudon", ["毒菇洞穴"] = "maraudon", ["草藤之座"] = "maraudon", ["邪惡洞穴"] = "maraudon" },
    [389] = { ["暗影裂口"] = "ragefire_chasm" },
}

ns.SubzoneLayer = {
    blackfathom_deeps = { ["月光神殿密室"] = 2, ["月光神殿廢墟"] = 2, ["水下廟宇"] = 1, ["遺忘之池"] = 3, ["阿庫麥爾的巢穴"] = 2, ["阿斯卡之池"] = 1 },
    blackrock_depths = { ["召喚師之墓"] = 2, ["工匠大廳"] = 1, ["帝王之座"] = 2, ["影爐城"] = 2, ["東部兵營"] = 2, ["澆鑄間"] = 2, ["熔火之橋"] = 2, ["禁閉室"] = 1, ["秩序大廳"] = 1, ["秩序競技場"] = 1, ["索瑞森神殿"] = 2, ["製造廠"] = 2, ["西部兵營"] = 2, ["講學廳"] = 2, ["鐵之大廳"] = 2, ["魔法之廳"] = 2, ["黑鐵大道"] = 1, ["黑鐵寶庫"] = 2, ["黑鐵酒吧"] = 2 },
    dire_maul_east = { ["巨槌競技場"] = 5 },
    gnomeregan = { ["宿舍"] = 2, ["工匠議會"] = 4, ["工程實驗室"] = 3, ["清潔區"] = 1, ["發射台"] = 3, ["發條小徑"] = 1, ["齒輪大廳"] = 1 },
    lower_blackrock_spire = { ["倉庫"] = 5, ["哈雷肯之巢"] = 5, ["塔薩洛爾"] = 1, ["戰鬥之廳"] = 6, ["摩多姆"] = 3, ["蛛網隧道"] = 2, ["霍德瑪爾城"] = 3, ["黑石塔"] = 4 },
    maraudon = { ["地歌瀑布"] = 2, ["札爾塔之墓"] = 2, ["毒水瀑布"] = 1, ["毒水谷"] = 1, ["毒菇洞穴"] = 1, ["草藤之座"] = 1, ["邪惡洞穴"] = 1 },
    scholomance = { ["召喚之廳"] = 2, ["實驗室"] = 4, ["屍骨儲藏所"] = 3, ["巫師會所"] = 3, ["巴羅夫家族寶庫"] = 4, ["掠奪者靈堂"] = 4, ["暗影墓穴"] = 4, ["秘密大廳"] = 3, ["觀察室"] = 2, ["譴責大廳"] = 3, ["遺骨之穴"] = 1, ["院長的書房"] = 4 },
    sm_armory = { ["勇士大廳"] = 1, ["十字軍武器庫"] = 1, ["大門廊"] = 1, ["步兵武器庫"] = 1, ["訓練場"] = 1 },
    sm_cathedral = { ["十字軍禮拜堂"] = 1, ["教堂花園"] = 1 },
    sm_graveyard = { ["孤寂迴廊"] = 1, ["懺悔室"] = 1, ["榮耀之墓"] = 1 },
    sm_library = { ["圖書館"] = 1, ["獵手迴廊"] = 1, ["珍寶陳列室"] = 1 },
    stratholme_main = { ["十字軍廣場"] = 1, ["國王廣場"] = 1, ["市場區"] = 1, ["物資庫"] = 1, ["節日小道"] = 1, ["聖光大廳"] = 1, ["血色十字軍堡壘"] = 1, ["赤色王座"] = 1 },
    the_deadmines = { ["哥布林鍛造廠"] = 2, ["船桅室"] = 1, ["鐵甲灣"] = 2 },
    uldaman = { ["一號挖掘場"] = 1, ["三號挖掘場"] = 1, ["二號挖掘場"] = 1, ["卡茲格羅斯的王座"] = 2, ["地圖室"] = 1, ["守護者大廳"] = 1, ["工匠大廳"] = 2, ["石窖"] = 1, ["神殿大廳"] = 1, ["艾卡莫克洞穴"] = 1 },
    wailing_caverns = { ["毒牙深淵"] = 1, ["永生峭壁"] = 1, ["激流溪谷"] = 1, ["狂風裂口"] = 1, ["美夢石"] = 1 },
}
