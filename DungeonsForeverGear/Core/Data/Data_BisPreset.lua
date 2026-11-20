local ns = _G.DF_NS or {}

ns.BisPreset = {
    { slug = "warrior", specs = {
        { key = "arms", label = "武器", presets = {
            { id = "pre", level = 60, items = { head = {12640}, neck = {22659}, shoulder = {272105}, back = {20068}, chest = {21997}, wrist = {21184}, hands = {272095}, waist = {272403}, legs = {22651}, feet = {21995}, finger = {275976}, finger2 = {19325}, trinket = {21181}, trinket2 = {260824}, main = {19169}, ranged = {22347} }, missingSlots = {}, incomplete = false },
        } },
        { key = "fury", label = "狂暴", presets = {
            { id = "pre", level = 60, items = { head = {12640}, neck = {18404}, shoulder = {272105}, back = {20073}, chest = {21997}, wrist = {19578}, hands = {272095}, waist = {272403}, legs = {279265}, feet = {21995}, finger = {272408}, finger2 = {19325}, trinket = {272437}, trinket2 = {270226}, main = {279259}, off = {19104}, ranged = {19107} }, missingSlots = {}, incomplete = false },
        } },
        { key = "prot", label = "防战", presets = {
            { id = "pre", level = 60, items = { head = {12640}, neck = {19159}, shoulder = {22001}, back = {18511}, chest = {12618}, wrist = {21996}, hands = {250552}, waist = {21994}, legs = {22000}, feet = {21995}, finger = {19325}, finger2 = {272408}, trinket = {272437}, trinket2 = {19024}, main = {250618}, off = {281637}, ranged = {22347} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "paladin", specs = {
        { key = "holy", label = "奶骑", presets = {
            { id = "pre", level = 60, items = { head = {12633}, neck = {20685}, shoulder = {12625}, back = {18510}, chest = {250601}, wrist = {250584}, hands = {250554}, waist = {250574}, legs = {250600}, feet = {250564}, trinket = {272439}, trinket2 = {19288}, main = {22383}, off = {279262}, ranged = {279248} }, missingSlots = {"finger","finger2"}, incomplete = false },
        } },
        { key = "prot", label = "防骑", presets = {
            { id = "pre", tab = "防御", level = 60, items = { head = {250597}, neck = {275736}, shoulder = {14552}, back = {18495}, chest = {226992}, wrist = {226985}, hands = {226990}, waist = {14620}, legs = {226988}, feet = {14621}, finger = {272409}, finger2 = {10795}, trinket = {14557}, trinket2 = {272440}, main = {22383}, off = {19321}, ranged = {23203} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "均衡", tab = "均衡", level = 60, items = { head = {250599}, neck = {19426}, shoulder = {226969}, back = {272411}, chest = {226992}, wrist = {226985}, hands = {226990}, waist = {272404}, legs = {226988}, feet = {226974}, finger = {272409}, finger2 = {22339}, trinket = {14557}, trinket2 = {272437}, main = {2243}, off = {19321}, ranged = {23203} }, missingSlots = {} },
            { id = "alt2", label = "进攻", tab = "进攻", level = 60, items = { head = {250599}, neck = {19426}, shoulder = {226969}, back = {272411}, chest = {226973}, wrist = {226970}, hands = {226975}, waist = {226971}, legs = {22753}, feet = {226974}, finger = {22433}, finger2 = {19325}, trinket = {20512}, trinket2 = {272437}, main = {871}, off = {1169}, ranged = {23203} }, missingSlots = {} },
            { id = "alt3", label = "廉价", tab = "廉价", level = 60, items = { head = {276071}, neck = {275736}, shoulder = {14552}, back = {18495}, chest = {14624}, wrist = {250583}, hands = {14622}, waist = {14620}, legs = {14623}, feet = {14621}, finger = {272409}, finger2 = {10795}, trinket = {20071}, trinket2 = {272440}, main = {22332}, off = {12602}, ranged = {272435} }, missingSlots = {} },
        } },
        { key = "ret", label = "惩戒", presets = {} },
    } },
    { slug = "hunter", specs = {
        { key = "bm", label = "兽王", presets = {
            { id = "pre", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {271956}, back = {13340}, chest = {252483}, wrist = {22011}, hands = {15063}, waist = {22232}, legs = {15062}, feet = {226881}, finger = {272408}, finger2 = {18500}, trinket = {13965}, trinket2 = {19120}, main = {250619}, ranged = {19107} }, missingSlots = {}, incomplete = false },
        } },
        { key = "mm", label = "射击", presets = {
            { id = "pre", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {271956}, back = {13340}, chest = {252483}, wrist = {22011}, hands = {15063}, waist = {272397}, legs = {15062}, feet = {13967}, finger = {272408}, finger2 = {18500}, trinket = {13965}, trinket2 = {270275}, main = {250619}, ranged = {19107} }, missingSlots = {}, incomplete = false },
        } },
        { key = "surv", label = "生存", presets = {
            { id = "pre", tab = "穿插射击", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {272106}, back = {13340}, chest = {252483}, wrist = {22011}, hands = {272099}, waist = {272397}, legs = {12903}, feet = {13967}, finger = {272408}, finger2 = {18500}, trinket = {22321}, trinket2 = {19120}, main = {13285}, ranged = {280020} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "全近战", tab = "全近战", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {272106}, back = {13340}, chest = {252483}, wrist = {18375}, hands = {15063}, waist = {272397}, legs = {15062}, feet = {22061}, finger = {272408}, finger2 = {13098}, trinket = {22321}, trinket2 = {19289}, main = {1728}, off = {18392}, ranged = {18323} }, missingSlots = {} },
        } },
    } },
    { slug = "rogue", specs = {
        { key = "assa", label = "奇袭", presets = {
            { id = "pre", level = 60, items = { head = {22005}, neck = {22150}, shoulder = {272105}, back = {21187}, chest = {22009}, shirt = {11840}, wrist = {22004}, hands = {21278}, waist = {272395}, legs = {22007}, feet = {18506}, finger = {19325}, finger2 = {21189}, trinket = {272437}, trinket2 = {19289}, main = {19324}, off = {19166}, ranged = {22347}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
        { key = "combat", label = "战斗", presets = {
            { id = "pre", level = 60, items = { head = {22005}, neck = {22150}, shoulder = {272105}, back = {21187}, chest = {22009}, shirt = {11840}, wrist = {22004}, hands = {21278}, waist = {272395}, legs = {22007}, feet = {18506}, finger = {19325}, finger2 = {21189}, trinket = {272437}, trinket2 = {19289}, main = {19324}, off = {22384}, ranged = {22347}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
        { key = "sub", label = "敏锐", presets = {
            { id = "pre", level = 60, items = { head = {22005}, neck = {22150}, shoulder = {272105}, back = {21187}, chest = {22009}, shirt = {11840}, wrist = {22004}, hands = {21278}, waist = {272395}, legs = {22007}, feet = {18506}, finger = {19325}, finger2 = {21189}, trinket = {272437}, trinket2 = {19289}, main = {22384}, off = {19166}, ranged = {22347}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "priest", specs = {
        { key = "disc", label = "戒律", presets = {} },
        { key = "holy", label = "神牧", presets = {
            { id = "pre", level = 60, items = { head = {260212}, neck = {1443}, shoulder = {14139}, back = {18510}, chest = {14154}, wrist = {13958}, hands = {12554}, waist = {19047}, legs = {18386}, feet = {13282}, finger = {16058}, finger2 = {22334}, trinket = {272439}, trinket2 = {18469}, main = {13360}, off = {15805}, ranged = {22254} }, missingSlots = {}, incomplete = false },
        } },
        { key = "shadow", label = "暗牧", presets = {
            { id = "pre", level = 60, items = { head = {22267}, neck = {22403}, shoulder = {226955}, back = {272411}, chest = {14136}, wrist = {13409}, hands = {14146}, waist = {18405}, legs = {10252}, feet = {10247}, finger = {12543}, finger2 = {22339}, trinket = {272438}, trinket2 = {13968}, main = {18372}, off = {18316}, ranged = {13396} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "shaman", specs = {
        { key = "ele", label = "元素", presets = {
            { id = "pre", level = 60, items = { head = {227002}, neck = {22403}, shoulder = {227003}, back = {272411}, chest = {280057}, wrist = {227001}, hands = {227006}, waist = {227008}, legs = {252486}, feet = {227007}, finger = {22339}, finger2 = {272406}, trinket = {272438}, trinket2 = {13968}, main = {20070}, off = {19315}, ranged = {23199} }, missingSlots = {}, incomplete = false },
        } },
        { key = "enh", label = "增强", presets = {
            { id = "pre", level = 60, items = { head = {227002}, neck = {15411}, shoulder = {227003}, back = {272411}, chest = {227024}, wrist = {227017}, hands = {227022}, waist = {227018}, legs = {252606}, feet = {14616}, finger = {19325}, finger2 = {272406}, trinket = {272437}, trinket2 = {13965}, main = {19323}, ranged = {23199} }, missingSlots = {}, incomplete = false },
        } },
        { key = "resto", label = "奶萨", presets = {
            { id = "pre", level = 60, items = { head = {260212}, neck = {18723}, shoulder = {14139}, back = {18510}, chest = {13346}, shirt = {11840}, wrist = {13969}, hands = {12554}, waist = {14553}, legs = {18386}, feet = {13282}, finger = {22334}, finger2 = {16058}, trinket = {272439}, trinket2 = {11819}, main = {13360}, off = {15805}, ranged = {249398}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "mage", specs = {
        { key = "arcane", label = "奥法", presets = {
            { id = "pre", level = 60, items = { head = {226935}, neck = {22403}, shoulder = {226936}, back = {272411}, chest = {14152}, wrist = {226929}, hands = {226930}, waist = {18405}, legs = {226933}, feet = {226931}, finger = {272406}, finger2 = {12543}, trinket = {13968}, trinket2 = {22268}, main = {22383}, off = {19315}, ranged = {13938} }, missingSlots = {}, incomplete = false },
        } },
        { key = "fire", label = "火法", presets = {
            { id = "pre", level = 60, items = { head = {226935}, neck = {22403}, shoulder = {226936}, back = {272411}, chest = {14152}, wrist = {226929}, hands = {226930}, waist = {11662}, legs = {226933}, feet = {226931}, finger = {272406}, finger2 = {22339}, trinket = {272438}, trinket2 = {13968}, main = {944}, ranged = {13938} }, missingSlots = {}, incomplete = false },
        } },
        { key = "frost", label = "冰法", presets = {
            { id = "pre", level = 60, items = { head = {226935}, neck = {22403}, shoulder = {226936}, back = {272411}, chest = {14152}, wrist = {226929}, hands = {226930}, waist = {18405}, legs = {226933}, feet = {226931}, finger = {272406}, finger2 = {12543}, trinket = {13968}, trinket2 = {22268}, main = {944}, ranged = {19108} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "warlock", specs = {
        { key = "affli", label = "痛苦", presets = {
            { id = "pre", tab = "现实最优", level = 60, items = { head = {22267}, neck = {18691}, shoulder = {14112}, back = {272411}, chest = {14136}, wrist = {13409}, hands = {18407}, waist = {10255}, legs = {22342}, feet = {10247}, finger = {22339}, finger2 = {12545}, trinket = {272438}, trinket2 = {18467}, main = {18534}, ranged = {13396} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "理论最优", tab = "理论最优", level = 60, items = { head = {22267}, neck = {18691}, shoulder = {19050}, back = {272411}, chest = {14153}, wrist = {19595}, hands = {18407}, waist = {18405}, legs = {22342}, feet = {10247}, finger = {22339}, finger2 = {12545}, trinket = {272438}, trinket2 = {18467}, main = {20220}, ranged = {13396} }, missingSlots = {} },
        } },
        { key = "demo", label = "恶魔", presets = {} },
        { key = "destro", label = "毁灭", presets = {
            { id = "pre", tab = "现实最优", level = 60, items = { head = {22267}, neck = {22403}, shoulder = {18681}, back = {272411}, chest = {280057}, wrist = {18497}, hands = {13253}, waist = {11662}, legs = {13170}, feet = {11822}, finger = {22339}, finger2 = {272406}, trinket = {272438}, trinket2 = {18467}, main = {18534}, ranged = {13938} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "理论最优", tab = "理论最优", level = 60, items = { head = {22267}, neck = {19426}, shoulder = {19050}, back = {272411}, chest = {14153}, wrist = {19595}, hands = {14146}, waist = {18405}, legs = {22747}, feet = {11822}, finger = {22339}, finger2 = {272406}, trinket = {272438}, trinket2 = {18467}, main = {20220}, ranged = {13938} }, missingSlots = {} },
        } },
    } },
    { slug = "druid", specs = {
        { key = "balance", label = "鸟德", presets = {
            { id = "pre", level = 60, items = { head = {22267}, neck = {19426}, shoulder = {226778}, back = {272411}, chest = {280057}, wrist = {13409}, hands = {13258}, waist = {18405}, legs = {252486}, feet = {226774}, finger = {272406}, finger2 = {12543}, trinket = {272438}, trinket2 = {13968}, main = {20070}, off = {19315}, ranged = {272430} }, missingSlots = {}, incomplete = false },
        } },
        { key = "cat", label = "猫德", presets = {
            { id = "pre", level = 60, items = { head = {12587}, neck = {19491}, shoulder = {15058}, back = {13340}, chest = {252484}, wrist = {270124}, hands = {21278}, waist = {272396}, legs = {15057}, feet = {12553}, finger = {272408}, finger2 = {19325}, trinket = {13965}, trinket2 = {280065}, main = {19323}, ranged = {220606} }, missingSlots = {}, incomplete = false },
        } },
        { key = "bear", label = "熊德", presets = {
            { id = "pre", level = 60, items = { head = {226801}, neck = {275736}, shoulder = {226798}, back = {272415}, chest = {226804}, wrist = {226796}, hands = {13258}, waist = {287040}, legs = {226799}, feet = {226803}, finger = {260216}, finger2 = {15855}, trinket = {272437}, trinket2 = {20071}, main = {18531}, ranged = {23198} }, missingSlots = {}, incomplete = false },
        } },
        { key = "resto", label = "奶德", presets = {
            { id = "pre", tab = "最佳选项", level = 60, items = { head = {252561}, neck = {18723}, shoulder = {14139}, back = {18510}, chest = {12462}, wrist = {13208}, hands = {226784}, waist = {14553}, legs = {16694}, feet = {226781}, finger = {272407}, finger2 = {16058}, trinket = {272439}, trinket2 = {18470}, main = {812}, ranged = {272429} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "简易", tab = "简易", level = 60, items = { head = {260212}, neck = {18723}, shoulder = {14139}, back = {272413}, chest = {13346}, wrist = {13208}, hands = {12554}, waist = {19047}, legs = {16694}, feet = {18507}, finger = {272407}, finger2 = {16058}, trinket = {272439}, trinket2 = {18470}, main = {13360}, off = {15805}, ranged = {272429} }, missingSlots = {} },
        } },
    } },
}

ns.BisSrcFix = {
    [18316] = "首领掉落|厄运之槌：东·普希林",
    [18873] = "商人|PvP 军需官",
    [23053] = "首领掉落|纳克萨玛斯·克尔苏加德",
    [220606] = "附魔（320）|专业制作",
    [260212] = "任务奖励|艾萨拉",
    [260216] = "任务奖励|黑喉要塞",
    [270124] = "任务奖励|厄运之槌",
    [270226] = "任务奖励|荆棘谷",
    [275976] = "商人|守望者",
    [280020] = "首领掉落|塑造者平台·雷蹄",
    [280057] = "首领掉落|黑喉要塞·狱牢头鬼",
    [280065] = "首领掉落|黑喉要塞·克劳伯特",
    [281637] = "任务奖励",
}

return nil
